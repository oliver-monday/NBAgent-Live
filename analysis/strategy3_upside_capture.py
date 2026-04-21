"""Strategy 3 upside capture + trailing stop analysis.

Extends the stop-loss sweep with resolution upside capture. Tests
scale-out ratios at the first exit (sell X% at $0.50, hold
remainder), trailing stop distances on the held remainder, and
held-to-resolution variants. Full grid search of
{initial stop × scale-out ratio × trailing stop distance}.

Run:
    python -m analysis.strategy3_upside_capture \\
        --metadata data/wp_kalshi_paired/matched_games.csv
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse loaders + fee + constants from the stop-loss sweep module.
from analysis.strategy3_stoploss_sweep import (
    MAX_SPREAD_COMPETITIVE,
    REG_SEASON_COMPETITIVE,
    RESOLUTION_LOSS_CUTOFF,
    RESOLUTION_WIN_CUTOFF,
    TOTAL_CONTRACTS,
    load_game_timeseries,
    load_metadata,
    log,
    maker_fee,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy3_upside_capture.md"
)
GRID_CSV = PAIRED_DIR / "upside_capture_grid.csv"
BEST_ENTRIES_CSV = PAIRED_DIR / "best_upside_entries.csv"


# ---- Dataclasses --------------------------------------------------------

@dataclass
class UpsideConfig:
    entry_threshold: float = 0.40
    first_exit: float = 0.50
    initial_stop: float | None = 0.34
    sell_pct: float = 1.0          # 1.0 = exit full at first exit; 0.0 = skip first exit
    trailing_stop_distance: float | None = 0.05  # None = hold to resolution
    trailing_stop_initial_offset: float = 0.05   # gap from first_exit for initial trail-stop level


@dataclass
class UpsideOutcome:
    game_ticker: str
    side: str
    entry_price: float
    entry_game_seconds: float
    entry_period: int | None
    first_exit_price: float | None     # None if never partially exited
    first_exit_game_seconds: float | None
    partial_qty: int
    remainder_qty: int
    final_exit_price: float             # price at which remainder (or full) closed
    final_exit_game_seconds: float
    exit_type: str                      # stopped_out_full | full_exit_scale_out
                                        # trailed_out | held_to_win | held_to_loss
                                        # held_indeterminate | resolution_loss_pre_exit
    contracts: int                      # partial_qty + remainder_qty
    gross_pnl: float
    net_pnl: float
    max_adverse_excursion: float
    max_favorable_excursion: float
    hold_time_sec: float
    abs_spread: float | None = None


# ---- Extended replay engine --------------------------------------------

def replay_upside(
    game_ticker: str, side: str,
    prices: np.ndarray, elapsed: np.ndarray, periods: np.ndarray,
    config: UpsideConfig,
) -> list[UpsideOutcome]:
    """One-side replay supporting partial exit + trailing stop on
    remainder + hold-to-resolution.

    State machine:
      WATCHING → IN_POSITION → (stopped_out_full | HOLDING_REMAINDER | full_exit)
      HOLDING_REMAINDER → (trailed_out | resolution)
    """
    out: list[UpsideOutcome] = []
    n = len(prices)
    if n == 0:
        return out

    # State
    in_pos = False
    holding_remainder = False
    re_entry_gated = False

    entry_price = entry_elapsed = entry_period = None
    held_contracts = 0
    cost_basis_cash = 0.0
    cumulative_fees = 0.0
    mae = mfe = None
    partial_qty_done = 0
    realized_partial_pnl = 0.0
    first_exit_price = None
    first_exit_elapsed = None
    trail_stop_level: float | None = None
    mfe_since_partial: float | None = None

    # last non-nan price for resolution fallback
    last_price = float(prices[~np.isnan(prices)][-1]) if np.any(~np.isnan(prices)) else None

    def _finalize_unfilled_entry(final_price: float, final_elapsed: float):
        """Handle end-of-timeseries for a position never exited."""
        if final_price >= RESOLUTION_WIN_CUTOFF:
            resolution = 1.0
            exit_type = "held_to_win"
        elif final_price <= RESOLUTION_LOSS_CUTOFF:
            resolution = 0.0
            exit_type = "held_to_loss"
        else:
            resolution = float(final_price)
            exit_type = "held_indeterminate"
        exit_fee = (
            maker_fee(held_contracts, resolution)
            if exit_type == "held_indeterminate" else 0.0
        )
        gross_remaining = resolution * held_contracts - cost_basis_cash_ptr[0]
        net = (
            realized_partial_pnl_ptr[0] + gross_remaining
            - cumulative_fees_ptr[0] - exit_fee
        )
        hold = final_elapsed - entry_elapsed_ptr[0]
        out.append(UpsideOutcome(
            game_ticker=game_ticker, side=side,
            entry_price=entry_price_ptr[0],
            entry_game_seconds=entry_elapsed_ptr[0],
            entry_period=entry_period_ptr[0],
            first_exit_price=first_exit_price_ptr[0],
            first_exit_game_seconds=first_exit_elapsed_ptr[0],
            partial_qty=partial_qty_ptr[0],
            remainder_qty=held_contracts,
            final_exit_price=float(final_price),
            final_exit_game_seconds=final_elapsed,
            exit_type=exit_type,
            contracts=partial_qty_ptr[0] + held_contracts,
            gross_pnl=realized_partial_pnl_ptr[0] + gross_remaining,
            net_pnl=net, hold_time_sec=hold,
            max_adverse_excursion=mae_ptr[0],
            max_favorable_excursion=mfe_ptr[0],
        ))

    # Use list pointers so the nested helper can mutate state. This is
    # simpler than reworking to methods for a single-purpose script.
    entry_price_ptr = [None]
    entry_elapsed_ptr = [None]
    entry_period_ptr = [None]
    cost_basis_cash_ptr = [0.0]
    cumulative_fees_ptr = [0.0]
    mae_ptr = [None]
    mfe_ptr = [None]
    realized_partial_pnl_ptr = [0.0]
    first_exit_price_ptr = [None]
    first_exit_elapsed_ptr = [None]
    partial_qty_ptr = [0]

    for i in range(n):
        p = prices[i]
        if pd.isna(p):
            continue
        p = float(p)
        if not in_pos and not holding_remainder:
            if re_entry_gated:
                if p > config.entry_threshold:
                    re_entry_gated = False
                continue
            if p <= config.entry_threshold:
                in_pos = True
                entry_price = p
                entry_price_ptr[0] = p
                entry_elapsed = float(elapsed[i])
                entry_elapsed_ptr[0] = entry_elapsed
                entry_period = (
                    int(periods[i]) if not pd.isna(periods[i]) else None
                )
                entry_period_ptr[0] = entry_period
                held_contracts = TOTAL_CONTRACTS
                cost_basis_cash = p * TOTAL_CONTRACTS
                cost_basis_cash_ptr[0] = cost_basis_cash
                cumulative_fees = maker_fee(TOTAL_CONTRACTS, p)
                cumulative_fees_ptr[0] = cumulative_fees
                mae = p
                mfe = p
                mae_ptr[0] = mae
                mfe_ptr[0] = mfe
                partial_qty_done = 0
                realized_partial_pnl = 0.0
                realized_partial_pnl_ptr[0] = 0.0
                first_exit_price = None
                first_exit_price_ptr[0] = None
                first_exit_elapsed = None
                first_exit_elapsed_ptr[0] = None
                trail_stop_level = None
                mfe_since_partial = None
            continue

        # Update MAE / MFE
        if p < mae:
            mae = p
            mae_ptr[0] = mae
        if p > mfe:
            mfe = p
            mfe_ptr[0] = mfe

        if in_pos and not holding_remainder:
            # Initial stop
            if config.initial_stop is not None and p <= config.initial_stop:
                exit_fee = maker_fee(held_contracts, p)
                gross = p * held_contracts - cost_basis_cash
                net = gross - cumulative_fees - exit_fee
                hold = float(elapsed[i]) - entry_elapsed
                out.append(UpsideOutcome(
                    game_ticker=game_ticker, side=side,
                    entry_price=entry_price,
                    entry_game_seconds=entry_elapsed,
                    entry_period=entry_period,
                    first_exit_price=None,
                    first_exit_game_seconds=None,
                    partial_qty=0,
                    remainder_qty=held_contracts,
                    final_exit_price=p,
                    final_exit_game_seconds=float(elapsed[i]),
                    exit_type="stopped_out_full",
                    contracts=held_contracts,
                    gross_pnl=gross, net_pnl=net,
                    max_adverse_excursion=mae,
                    max_favorable_excursion=mfe,
                    hold_time_sec=hold,
                ))
                in_pos = False
                re_entry_gated = True
                continue

            # First exit at first_exit threshold
            if p >= config.first_exit and config.sell_pct > 0:
                partial_qty = max(1, int(round(held_contracts * config.sell_pct)))
                partial_qty = min(partial_qty, held_contracts)
                cost_per_share = cost_basis_cash / held_contracts
                partial_cost = cost_per_share * partial_qty
                partial_gross = p * partial_qty - partial_cost
                partial_fee = maker_fee(partial_qty, p)
                realized_partial_pnl = partial_gross - partial_fee
                realized_partial_pnl_ptr[0] = realized_partial_pnl
                cost_basis_cash -= partial_cost
                cost_basis_cash_ptr[0] = cost_basis_cash
                held_contracts -= partial_qty
                partial_qty_done = partial_qty
                partial_qty_ptr[0] = partial_qty
                first_exit_price = p
                first_exit_price_ptr[0] = p
                first_exit_elapsed = float(elapsed[i])
                first_exit_elapsed_ptr[0] = first_exit_elapsed

                if held_contracts == 0:
                    # Pure scale-out (sell_pct = 1.0): record as full exit
                    hold = float(elapsed[i]) - entry_elapsed
                    net = realized_partial_pnl - cumulative_fees
                    out.append(UpsideOutcome(
                        game_ticker=game_ticker, side=side,
                        entry_price=entry_price,
                        entry_game_seconds=entry_elapsed,
                        entry_period=entry_period,
                        first_exit_price=p, first_exit_game_seconds=first_exit_elapsed,
                        partial_qty=partial_qty, remainder_qty=0,
                        final_exit_price=p, final_exit_game_seconds=float(elapsed[i]),
                        exit_type="full_exit_scale_out",
                        contracts=partial_qty,
                        gross_pnl=partial_gross,
                        net_pnl=net, hold_time_sec=hold,
                        max_adverse_excursion=mae,
                        max_favorable_excursion=mfe,
                    ))
                    in_pos = False
                    re_entry_gated = True
                    continue

                # Enter holding-remainder mode
                holding_remainder = True
                in_pos = False  # no longer in initial stop regime
                if config.trailing_stop_distance is not None:
                    # Initial trailing stop: max(first_exit - trail_dist,
                    # first_exit - trailing_stop_initial_offset)
                    trail_stop_level = p - config.trailing_stop_distance
                else:
                    trail_stop_level = None
                mfe_since_partial = p
                continue

            # sell_pct = 0 means hold everything to resolution — no
            # partial even when first_exit reached; fall through and
            # continue to end-of-game.

        elif holding_remainder:
            # Update trailing stop if we have one
            if config.trailing_stop_distance is not None:
                if mfe_since_partial is None or p > mfe_since_partial:
                    mfe_since_partial = p
                    candidate = p - config.trailing_stop_distance
                    if trail_stop_level is None or candidate > trail_stop_level:
                        trail_stop_level = candidate
                # Check for trail trigger
                if trail_stop_level is not None and p <= trail_stop_level:
                    # Exit remainder
                    exit_fee = maker_fee(held_contracts, p)
                    gross_remaining = p * held_contracts - cost_basis_cash
                    net = (
                        realized_partial_pnl + gross_remaining
                        - cumulative_fees - exit_fee
                    )
                    hold = float(elapsed[i]) - entry_elapsed
                    out.append(UpsideOutcome(
                        game_ticker=game_ticker, side=side,
                        entry_price=entry_price,
                        entry_game_seconds=entry_elapsed,
                        entry_period=entry_period,
                        first_exit_price=first_exit_price,
                        first_exit_game_seconds=first_exit_elapsed,
                        partial_qty=partial_qty_done,
                        remainder_qty=held_contracts,
                        final_exit_price=p,
                        final_exit_game_seconds=float(elapsed[i]),
                        exit_type="trailed_out",
                        contracts=partial_qty_done + held_contracts,
                        gross_pnl=realized_partial_pnl + gross_remaining,
                        net_pnl=net, hold_time_sec=hold,
                        max_adverse_excursion=mae,
                        max_favorable_excursion=mfe,
                    ))
                    holding_remainder = False
                    re_entry_gated = True
                    continue

    # End of timeseries
    if in_pos and entry_price is not None and last_price is not None:
        # Never reached first exit nor stopped out; resolve at end
        if last_price >= RESOLUTION_WIN_CUTOFF:
            resolution = 1.0
            exit_type = "resolution_win_no_partial"
        elif last_price <= RESOLUTION_LOSS_CUTOFF:
            resolution = 0.0
            exit_type = "resolution_loss"
        else:
            resolution = float(last_price)
            exit_type = "held_indeterminate"
        exit_fee = (
            maker_fee(held_contracts, resolution)
            if exit_type == "held_indeterminate" else 0.0
        )
        gross = resolution * held_contracts - cost_basis_cash
        net = gross - cumulative_fees - exit_fee
        hold = float(elapsed[-1]) - entry_elapsed
        out.append(UpsideOutcome(
            game_ticker=game_ticker, side=side,
            entry_price=entry_price,
            entry_game_seconds=entry_elapsed,
            entry_period=entry_period,
            first_exit_price=None, first_exit_game_seconds=None,
            partial_qty=0, remainder_qty=held_contracts,
            final_exit_price=float(last_price),
            final_exit_game_seconds=float(elapsed[-1]),
            exit_type=exit_type, contracts=held_contracts,
            gross_pnl=gross, net_pnl=net,
            max_adverse_excursion=mae, max_favorable_excursion=mfe,
            hold_time_sec=hold,
        ))
    elif holding_remainder and last_price is not None:
        if last_price >= RESOLUTION_WIN_CUTOFF:
            resolution = 1.0
            exit_type = "held_to_win"
        elif last_price <= RESOLUTION_LOSS_CUTOFF:
            resolution = 0.0
            exit_type = "held_to_loss"
        else:
            resolution = float(last_price)
            exit_type = "held_indeterminate"
        exit_fee = (
            maker_fee(held_contracts, resolution)
            if exit_type == "held_indeterminate" else 0.0
        )
        gross_remaining = resolution * held_contracts - cost_basis_cash
        net = (
            realized_partial_pnl + gross_remaining
            - cumulative_fees - exit_fee
        )
        hold = float(elapsed[-1]) - entry_elapsed
        out.append(UpsideOutcome(
            game_ticker=game_ticker, side=side,
            entry_price=entry_price,
            entry_game_seconds=entry_elapsed,
            entry_period=entry_period,
            first_exit_price=first_exit_price,
            first_exit_game_seconds=first_exit_elapsed,
            partial_qty=partial_qty_done, remainder_qty=held_contracts,
            final_exit_price=float(last_price),
            final_exit_game_seconds=float(elapsed[-1]),
            exit_type=exit_type,
            contracts=partial_qty_done + held_contracts,
            gross_pnl=realized_partial_pnl + gross_remaining,
            net_pnl=net, hold_time_sec=hold,
            max_adverse_excursion=mae, max_favorable_excursion=mfe,
        ))
    return out


def replay_all(
    games: list[dict], meta: dict[str, dict], config: UpsideConfig,
) -> list[UpsideOutcome]:
    outs: list[UpsideOutcome] = []
    for g in games:
        m = meta.get(g["ticker"])
        if m is None or m["abs_spread"] is None or m["abs_spread"] > MAX_SPREAD_COMPETITIVE:
            continue
        ts = g["ts"]
        fav = ts["fav_kalshi_vwap"].values.astype(float)
        dog = 1.0 - fav
        el = ts["game_seconds_elapsed"].values.astype(float)
        pr = ts["period"].values
        for side, prices in (("fav", fav), ("dog", dog)):
            recs = replay_upside(g["ticker"], side, prices, el, pr, config)
            for r in recs:
                r.abs_spread = m["abs_spread"]
            outs.extend(recs)
    return outs


# ---- Summaries ----------------------------------------------------------

def summarize(outs: list[UpsideOutcome], n_games: int) -> dict:
    n = len(outs)
    if n == 0:
        return {"n": 0, "mean_pnl": float("nan"), "annual_ev": 0.0,
                "median_pnl": float("nan"), "std_pnl": 0.0,
                "win_rate": 0.0, "max_loss": 0.0, "max_win": 0.0,
                "counts": {}}
    pnls = np.array([o.net_pnl for o in outs])
    counts: dict[str, int] = {}
    for o in outs:
        counts[o.exit_type] = counts.get(o.exit_type, 0) + 1
    mean = float(pnls.mean())
    std = float(pnls.std(ddof=1)) if n > 1 else 0.0
    return {
        "n": n,
        "mean_pnl": mean,
        "median_pnl": float(np.median(pnls)),
        "std_pnl": std,
        "win_rate": 100 * float((pnls > 0).mean()),
        "annual_ev": mean * (n / n_games if n_games else 0) * REG_SEASON_COMPETITIVE,
        "entries_per_game": n / n_games if n_games else 0,
        "max_loss": float(pnls.min()),
        "max_win": float(pnls.max()),
        "counts": counts,
    }


def _cnt(counts: dict, *keys: str) -> int:
    return sum(counts.get(k, 0) for k in keys)


# ---- Report parts -------------------------------------------------------

def part_1_scaleout(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    entry: float, first_exit: float,
) -> float:
    md.append("## Part 1 — Scale-out ratio sweep\n")
    md.append(
        "Initial stop $0.34 (optimum from prior sweep), trailing "
        "distance $0.05.\n"
    )
    md.append(
        "| Sell % | Entries | Partial exits | Trail outs | "
        "Held to win | Held to loss | Mean P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    best_pct = 1.0
    best_mean = -float("inf")
    for pct in (1.0, 0.75, 0.50, 0.25, 0.0):
        cfg = UpsideConfig(
            entry_threshold=entry, first_exit=first_exit,
            initial_stop=0.34, sell_pct=pct,
            trailing_stop_distance=0.05,
        )
        outs = replay_all(games, meta, cfg)
        s = summarize(outs, n_games)
        c = s["counts"]
        partials = _cnt(c, "full_exit_scale_out", "trailed_out",
                       "held_to_win", "held_to_loss", "held_indeterminate")
        trail = _cnt(c, "trailed_out")
        held_win = _cnt(c, "held_to_win", "resolution_win_no_partial")
        held_loss = _cnt(c, "held_to_loss", "resolution_loss")
        md.append(
            f"| {pct*100:.0f}% | {s['n']} | {partials} | {trail} | "
            f"{held_win} | {held_loss} | ${s['mean_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
        if s["mean_pnl"] > best_mean:
            best_mean = s["mean_pnl"]
            best_pct = pct
    md.append("")
    md.append(f"**Best sell %: {best_pct*100:.0f}% (mean P&L ${best_mean:+.2f})**\n")
    return best_pct


def part_2_trailing(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    entry: float, first_exit: float, best_pct: float,
) -> float | None:
    md.append("## Part 2 — Trailing stop distance sweep\n")
    md.append(
        f"Initial stop $0.34, scale-out {best_pct*100:.0f}%. "
        "Also tests 'no trailing stop' = hold remainder to resolution.\n"
    )
    md.append(
        "| Trail dist | Entries | Trail outs | Held to win | "
        "Held to loss | Mean P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    best_dist: float | None = 0.05
    best_mean = -float("inf")
    for dist in (0.03, 0.05, 0.07, 0.10, 0.15, 0.20, None):
        cfg = UpsideConfig(
            entry_threshold=entry, first_exit=first_exit,
            initial_stop=0.34, sell_pct=best_pct,
            trailing_stop_distance=dist,
        )
        outs = replay_all(games, meta, cfg)
        s = summarize(outs, n_games)
        c = s["counts"]
        trail = _cnt(c, "trailed_out")
        held_win = _cnt(c, "held_to_win", "resolution_win_no_partial")
        held_loss = _cnt(c, "held_to_loss", "resolution_loss")
        label = "No trail" if dist is None else f"${dist:.2f}"
        md.append(
            f"| {label} | {s['n']} | {trail} | {held_win} | "
            f"{held_loss} | ${s['mean_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
        if s["mean_pnl"] > best_mean:
            best_mean = s["mean_pnl"]
            best_dist = dist
    md.append("")
    label = "No trail" if best_dist is None else f"${best_dist:.2f}"
    md.append(
        f"**Best trailing distance: {label} (mean P&L ${best_mean:+.2f})**\n"
    )
    return best_dist


def part_3_stop_resweep(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    entry: float, first_exit: float, best_pct: float,
    best_dist: float | None,
) -> float | None:
    md.append("## Part 3 — Initial stop-loss re-sweep with upside capture\n")
    label_dist = "No trail" if best_dist is None else f"${best_dist:.2f}"
    md.append(
        f"Scale-out {best_pct*100:.0f}%, trailing {label_dist}.\n"
    )
    md.append(
        "| Stop | Entries | Scale-outs | Stopped | Trail outs | "
        "Res wins | Res losses | Mean P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    best_stop: float | None = None
    best_mean = -float("inf")
    levels: list[float | None] = [None] + [
        round(0.39 - 0.01 * i, 2) for i in range(0, 20, 2)
    ] + [0.20]
    levels = sorted(set(levels), key=lambda x: (x is None, x or 0))
    # Order: None first then 0.20…0.39
    ordered: list[float | None] = [None]
    ordered.extend([0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34, 0.36, 0.38])
    for sl in ordered:
        cfg = UpsideConfig(
            entry_threshold=entry, first_exit=first_exit,
            initial_stop=sl, sell_pct=best_pct,
            trailing_stop_distance=best_dist,
        )
        outs = replay_all(games, meta, cfg)
        s = summarize(outs, n_games)
        c = s["counts"]
        scale_out = _cnt(c, "full_exit_scale_out")
        stopped = _cnt(c, "stopped_out_full")
        trail = _cnt(c, "trailed_out")
        res_win = _cnt(c, "held_to_win", "resolution_win_no_partial")
        res_loss = _cnt(c, "held_to_loss", "resolution_loss")
        sl_label = "None" if sl is None else f"${sl:.2f}"
        md.append(
            f"| {sl_label} | {s['n']} | {scale_out} | {stopped} | "
            f"{trail} | {res_win} | {res_loss} | ${s['mean_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
        if s["mean_pnl"] > best_mean:
            best_mean = s["mean_pnl"]
            best_stop = sl
    md.append("")
    label = "None" if best_stop is None else f"${best_stop:.2f}"
    md.append(
        f"**Best initial stop: {label} (mean P&L ${best_mean:+.2f})**\n"
    )
    return best_stop


def part_4_grid(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    entry: float, first_exit: float,
) -> tuple[UpsideConfig, dict, int, list[dict]]:
    md.append("## Part 4 — Full grid search (96 configurations)\n")
    md.append(
        "Sweeping: stop_loss ∈ {None, 0.30, 0.32, 0.34, 0.36, 0.38} × "
        "sell_pct ∈ {1.0, 0.75, 0.50, 0.25} × "
        "trailing_stop_distance ∈ {0.05, 0.10, 0.15, None}.\n"
    )
    stops: list[float | None] = [None, 0.30, 0.32, 0.34, 0.36, 0.38]
    pcts = [1.0, 0.75, 0.50, 0.25]
    trails: list[float | None] = [0.05, 0.10, 0.15, None]
    results: list[dict] = []
    total = len(stops) * len(pcts) * len(trails)
    i_total = 0
    for sl in stops:
        for pct in pcts:
            for tr in trails:
                cfg = UpsideConfig(
                    entry_threshold=entry, first_exit=first_exit,
                    initial_stop=sl, sell_pct=pct,
                    trailing_stop_distance=tr,
                )
                outs = replay_all(games, meta, cfg)
                s = summarize(outs, n_games)
                sharpe = (
                    s["mean_pnl"] / s["std_pnl"] if s["std_pnl"] > 0 else 0.0
                )
                results.append({
                    "stop_loss": "" if sl is None else sl,
                    "sell_pct": pct,
                    "trail_dist": "" if tr is None else tr,
                    "entries": s["n"],
                    "mean_pnl": s["mean_pnl"],
                    "median_pnl": s["median_pnl"],
                    "std_pnl": s["std_pnl"],
                    "win_rate": s["win_rate"],
                    "annual_ev": s["annual_ev"],
                    "sharpe": sharpe,
                    "max_loss": s["max_loss"],
                    "max_win": s["max_win"],
                })
                i_total += 1
    log(f"Grid search complete: {i_total}/{total} configurations tested")
    # Write grid CSV
    pd.DataFrame(results).to_csv(GRID_CSV, index=False)
    log(f"Grid CSV → {GRID_CSV}")

    md.append("### Top 10 by mean P&L\n")
    md.append(
        "| Rank | Stop | Sell % | Trail | Entries | Win rate | "
        "Mean P&L | Annual EV |"
    )
    md.append("|---|---|---:|---|---:|---:|---:|---:|")
    by_mean = sorted(results, key=lambda r: r["mean_pnl"], reverse=True)
    for i, r in enumerate(by_mean[:10], 1):
        stop_s = "None" if r["stop_loss"] == "" else f"${r['stop_loss']:.2f}"
        trail_s = "None" if r["trail_dist"] == "" else f"${r['trail_dist']:.2f}"
        md.append(
            f"| {i} | {stop_s} | {r['sell_pct']*100:.0f}% | "
            f"{trail_s} | {r['entries']} | {r['win_rate']:.1f}% | "
            f"${r['mean_pnl']:+.2f} | ${r['annual_ev']:+,.0f} |"
        )
    md.append("")

    md.append("### Top 10 by Sharpe-like ratio (mean / std)\n")
    md.append(
        "| Rank | Stop | Sell % | Trail | Mean P&L | Std P&L | Sharpe |"
    )
    md.append("|---|---|---:|---|---:|---:|---:|")
    by_sharpe = sorted(results, key=lambda r: r["sharpe"], reverse=True)
    for i, r in enumerate(by_sharpe[:10], 1):
        stop_s = "None" if r["stop_loss"] == "" else f"${r['stop_loss']:.2f}"
        trail_s = "None" if r["trail_dist"] == "" else f"${r['trail_dist']:.2f}"
        md.append(
            f"| {i} | {stop_s} | {r['sell_pct']*100:.0f}% | "
            f"{trail_s} | ${r['mean_pnl']:+.2f} | ${r['std_pnl']:.2f} | "
            f"{r['sharpe']:.3f} |"
        )
    md.append("")

    # Best overall config (by mean P&L)
    top = by_mean[0]
    best_cfg = UpsideConfig(
        entry_threshold=entry, first_exit=first_exit,
        initial_stop=None if top["stop_loss"] == "" else top["stop_loss"],
        sell_pct=top["sell_pct"],
        trailing_stop_distance=None if top["trail_dist"] == "" else top["trail_dist"],
    )
    return best_cfg, top, total, results


def part_5_detailed(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    best_cfg: UpsideConfig,
) -> list[UpsideOutcome]:
    md.append("## Part 5 — Best configuration detailed breakdown\n")
    md.append("### Best configuration\n")
    md.append(f"- Entry: ${best_cfg.entry_threshold:.2f} ({TOTAL_CONTRACTS} contracts)")
    sl = "None" if best_cfg.initial_stop is None else f"${best_cfg.initial_stop:.2f}"
    md.append(f"- Initial stop-loss: {sl}")
    md.append(
        f"- At first exit (${best_cfg.first_exit:.2f}): sell "
        f"{int(round(best_cfg.sell_pct * TOTAL_CONTRACTS))} contracts, "
        f"hold {TOTAL_CONTRACTS - int(round(best_cfg.sell_pct * TOTAL_CONTRACTS))}"
    )
    trail = (
        "None (hold to resolution)" if best_cfg.trailing_stop_distance is None
        else f"${best_cfg.trailing_stop_distance:.2f} distance"
    )
    md.append(f"- Trailing stop on held remainder: {trail}")
    md.append("")

    outs = replay_all(games, meta, best_cfg)
    s = summarize(outs, n_games)

    md.append("### Outcome distribution\n")
    md.append("| Outcome | Count | % | Mean P&L | Median P&L |")
    md.append("|---|---:|---:|---:|---:|")
    buckets = [
        ("Full exit at first target", ("full_exit_scale_out",)),
        ("Stopped out (never reached first exit)",
         ("stopped_out_full",)),
        ("Partial exit + trailed out", ("trailed_out",)),
        ("Partial exit + held to win",
         ("held_to_win", "resolution_win_no_partial")),
        ("Partial exit + held to loss",
         ("held_to_loss", "resolution_loss")),
        ("Held indeterminate", ("held_indeterminate",)),
    ]
    n = s["n"] or 1
    for label, keys in buckets:
        sub = [o for o in outs if o.exit_type in keys]
        if not sub:
            md.append(f"| {label} | 0 | 0.0% | — | — |")
            continue
        pnls = [o.net_pnl for o in sub]
        md.append(
            f"| {label} | {len(sub)} | {100*len(sub)/n:.1f}% | "
            f"${np.mean(pnls):+.2f} | ${np.median(pnls):+.2f} |"
        )
    md.append(
        f"| **ALL** | **{s['n']}** | 100.0% | **${s['mean_pnl']:+.2f}** | "
        f"**${s['median_pnl']:+.2f}** |"
    )
    md.append("")

    md.append("### P&L distribution\n")
    md.append("| P&L bucket | Count | % |")
    md.append("|---|---:|---:|")
    edges = [
        ("< -$30", lambda v: v < -30),
        ("-$30 to -$20", lambda v: -30 <= v < -20),
        ("-$20 to -$10", lambda v: -20 <= v < -10),
        ("-$10 to $0", lambda v: -10 <= v < 0),
        ("$0 to $10", lambda v: 0 <= v < 10),
        ("$10 to $20", lambda v: 10 <= v < 20),
        ("$20 to $30", lambda v: 20 <= v < 30),
        ("$30 to $50", lambda v: 30 <= v < 50),
        ("> $50", lambda v: v >= 50),
    ]
    for label, pred in edges:
        cnt = sum(1 for o in outs if pred(o.net_pnl))
        md.append(f"| {label} | {cnt} | {100*cnt/n:.1f}% |")
    md.append("")

    md.append("### By entry period\n")
    md.append("| Entry Q | Entries | Win rate | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    for q_label, pred in (
        ("Q1", lambda o: o.entry_period == 1),
        ("Q2", lambda o: o.entry_period == 2),
        ("Q3", lambda o: o.entry_period == 3),
        ("Q4", lambda o: o.entry_period == 4),
        ("OT", lambda o: o.entry_period is not None and o.entry_period >= 5),
    ):
        sub = [o for o in outs if pred(o)]
        if not sub:
            md.append(f"| {q_label} | 0 | — | — |")
            continue
        wr = 100 * float(np.mean([o.net_pnl > 0 for o in sub]))
        mn = float(np.mean([o.net_pnl for o in sub]))
        md.append(f"| {q_label} | {len(sub)} | {wr:.1f}% | ${mn:+.2f} |")
    md.append("")

    md.append("### By spread bucket\n")
    md.append("| |Spread| | Entries | Win rate | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    for label, pred in (
        ("1-2", lambda o: o.abs_spread is not None and 1.0 <= o.abs_spread <= 2.0),
        ("2.5-3.5", lambda o: o.abs_spread is not None and 2.5 <= o.abs_spread <= 3.5),
        ("4-5", lambda o: o.abs_spread is not None and 4.0 <= o.abs_spread <= 5.0),
        ("5.5-6", lambda o: o.abs_spread is not None and 5.5 <= o.abs_spread <= 6.0),
    ):
        sub = [o for o in outs if pred(o)]
        if not sub:
            md.append(f"| {label} | 0 | — | — |")
            continue
        wr = 100 * float(np.mean([o.net_pnl > 0 for o in sub]))
        mn = float(np.mean([o.net_pnl for o in sub]))
        md.append(f"| {label} | {len(sub)} | {wr:.1f}% | ${mn:+.2f} |")
    md.append("")

    md.append("### Risk metrics\n")
    pnls = np.array([o.net_pnl for o in outs])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    avg_w = float(wins.mean()) if len(wins) else float("nan")
    avg_l = float(losses.mean()) if len(losses) else float("nan")
    ratio = abs(avg_w / avg_l) if len(wins) and len(losses) and avg_l != 0 else float("nan")
    sharpe = s["mean_pnl"] / s["std_pnl"] if s["std_pnl"] > 0 else 0.0
    p = len(wins) / s["n"] if s["n"] else 0
    q = 1 - p
    if ratio and not np.isnan(ratio) and ratio > 0:
        f_star = (p * ratio - q) / ratio
    else:
        f_star = 0.0
    md.append("| Metric | Value |")
    md.append("|---|---|")
    md.append(f"| Sharpe-like (mean/std) | {sharpe:.3f} |")
    md.append(f"| Win rate (net > 0) | {s['win_rate']:.1f}% |")
    md.append(f"| Mean winner | ${avg_w:+.2f} |")
    md.append(f"| Mean loser | ${avg_l:+.2f} |")
    if not np.isnan(ratio):
        md.append(f"| Win/loss ratio | {ratio:.2f}× |")
    md.append(f"| Max single loss | ${s['max_loss']:+.2f} |")
    md.append(f"| Max single win | ${s['max_win']:+.2f} |")
    md.append(f"| Kelly f* | {f_star:.3f} |")
    if f_star > 0:
        md.append(
            f"| At $1,000 bankroll | ${1000 * f_star:.2f} per entry |"
        )
    md.append("")
    return outs


def part_6_comparison(
    md: list[str], best_cfg: UpsideConfig, best_stats: dict,
) -> None:
    md.append("## Part 6 — Strategy evolution comparison\n")
    md.append("| Strategy | Mean P&L | Annual EV | Max loss | Sharpe |")
    md.append("|---|---:|---:|---:|---:|")
    md.append("| Naive (no stop, exit at $0.50) | −$4.22 | −$5,963 | −$40.39 | −0.16 |")
    md.append("| Best stop-loss only (prior sweep) | −$1.27 | −$2,531 | −$16.38 | −0.09 |")
    md.append("| Best stop + avg-in (prior sweep) | −$0.59 | −$1,175 | −$16.38 | — |")
    sharpe = (
        best_stats["mean_pnl"] / best_stats["std_pnl"]
        if best_stats["std_pnl"] > 0 else 0.0
    )
    md.append(
        f"| **Best with upside capture** | "
        f"**${best_stats['mean_pnl']:+.2f}** | "
        f"**${best_stats['annual_ev']:+,.0f}** | "
        f"**${best_stats['max_loss']:+.2f}** | "
        f"**{sharpe:.2f}** |"
    )
    md.append("| Bilateral only (guaranteed) | +$19.14 | +$1,608 | $0 | ∞ |")
    md.append("")


# ---- Main ---------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metadata", type=str,
        default=str(PAIRED_DIR / "matched_games.csv"),
    )
    parser.add_argument("--entry", type=float, default=0.40)
    parser.add_argument("--exit", dest="exit_", type=float, default=0.50)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    meta = load_metadata(Path(args.metadata))
    log(f"Metadata loaded for {len(meta)} games")
    games = load_game_timeseries()
    log(f"Loaded {len(games)} timeseries files")
    n_games = sum(
        1 for g in games
        if meta.get(g["ticker"]) is not None
        and meta[g["ticker"]]["abs_spread"] is not None
        and meta[g["ticker"]]["abs_spread"] <= MAX_SPREAD_COMPETITIVE
    )
    log(f"Competitive games: {n_games}")

    md: list[str] = []
    md.append("# Strategy 3 — Upside Capture & Trailing Stops\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Extends the stop-loss sweep with resolution upside capture. "
        "Split positions: partial exit at $0.50, held remainder ride "
        "a trailing stop or resolution. 96-configuration grid search "
        "over {initial_stop × sell_pct × trailing_distance}.\n"
    )
    md.append(
        f"**Params:** entry=${args.entry:.2f}, first_exit=${args.exit_:.2f}, "
        f"{TOTAL_CONTRACTS} contracts per entry, maker-maker fees.\n"
    )

    best_pct = part_1_scaleout(md, games, meta, n_games, args.entry, args.exit_)
    best_dist = part_2_trailing(
        md, games, meta, n_games, args.entry, args.exit_, best_pct,
    )
    part_3_stop_resweep(
        md, games, meta, n_games, args.entry, args.exit_, best_pct, best_dist,
    )
    best_cfg, best_row, total, _results = part_4_grid(
        md, games, meta, n_games, args.entry, args.exit_,
    )
    log(f"Grid total tested: {total}")
    best_outs = part_5_detailed(md, games, meta, n_games, best_cfg)
    best_stats = summarize(best_outs, n_games)
    part_6_comparison(md, best_cfg, best_stats)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md) + "\n")
    log(f"Report → {out}")

    # Best-config entries
    if best_outs:
        pd.DataFrame([asdict(o) for o in best_outs]).to_csv(
            BEST_ENTRIES_CSV, index=False,
        )
        log(f"Best-config entries CSV → {BEST_ENTRIES_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
