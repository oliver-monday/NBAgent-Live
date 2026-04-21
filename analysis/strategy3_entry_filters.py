"""Strategy 3 entry-filter sweep.

Tests four entry filters on the Strategy 3 replay engine:
  A. Oscillation confirmation — price was recently above some level
  B. ESPN WP rate-of-change — fast drop in WP before the dip
  C. Favorite-side only — restrict to pre-game favorite
  D. Period restriction — Q1 only / Q1+Q2 / Q1+Q2+Q3

Individual filter sweeps (Part 1), combined grid (Part 3, 32 cfgs),
best-config detail (Part 4), evolution table (Part 5), and
filter diagnostic with precision/recall (Part 6).

Run:
    python -m analysis.strategy3_entry_filters \\
        --metadata data/wp_kalshi_paired/matched_games.csv
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

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
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy3_entry_filters.md"
)
SWEEP_CSV = PAIRED_DIR / "entry_filter_sweep.csv"
BEST_CSV = PAIRED_DIR / "best_filtered_entries.csv"

VWAP_BUCKET_SEC = 30


# ---- Filter + Exit configs ----------------------------------------------

@dataclass
class FilterConfig:
    # Oscillation (None = off)
    osc_lookback_sec: int | None = None
    osc_recent_high: float | None = None
    # WP momentum (None = off)
    wp_lookback_sec: int | None = None
    wp_drop_min: float | None = None
    # Favorite-side only
    fav_only: bool = False
    # Period restriction: None = all periods
    allowed_periods: set[int] | None = None


@dataclass
class ExitConfig:
    label: str
    entry_threshold: float = 0.40
    first_exit: float = 0.50
    initial_stop: float | None = 0.34
    sell_pct: float = 1.0                    # 1.0 = simple full exit
    trailing_stop_distance: float | None = None
    hold_to_resolution: bool = False         # if True, remainder rides to resolution


@dataclass
class Outcome:
    game_ticker: str
    side: str
    entry_price: float
    entry_elapsed: float
    entry_period: int | None
    exit_type: str
    contracts: int
    net_pnl: float
    gross_pnl: float
    hold_time_sec: float
    max_adverse: float
    max_favorable: float
    first_exit_price: float | None
    final_price: float
    abs_spread: float | None = None


@dataclass
class FilteredCandidate:
    game_ticker: str
    side: str
    entry_price: float
    entry_elapsed: float
    entry_period: int | None
    would_have_completed: bool
    abs_spread: float | None = None


SIMPLE_EXIT = ExitConfig(
    label="simple", sell_pct=1.0, initial_stop=0.34,
    trailing_stop_distance=None, hold_to_resolution=False,
)
UPSIDE_EXIT = ExitConfig(
    label="upside", sell_pct=0.25, initial_stop=0.34,
    trailing_stop_distance=None, hold_to_resolution=True,
)


# ---- Filter evaluation --------------------------------------------------

def _bins_for_seconds(sec: int) -> int:
    return max(1, int(round(sec / VWAP_BUCKET_SEC)))


def filter_passes(
    cfg: FilterConfig, prices_side: np.ndarray, wp_side: np.ndarray,
    periods: np.ndarray, elapsed: np.ndarray, idx: int,
    side: str, is_fav_side: bool,
) -> bool:
    # Favorite-side
    if cfg.fav_only and not is_fav_side:
        return False
    # Period
    if cfg.allowed_periods is not None:
        p = periods[idx]
        if pd.isna(p) or int(p) not in cfg.allowed_periods:
            return False
    # Oscillation: price was >= recent_high at some prior bin within lookback
    if cfg.osc_lookback_sec is not None and cfg.osc_recent_high is not None:
        lb_bins = _bins_for_seconds(cfg.osc_lookback_sec)
        start = max(0, idx - lb_bins)
        window = prices_side[start:idx]
        if len(window) == 0:
            return False
        window = window[~np.isnan(window)]
        if len(window) == 0 or np.max(window) < cfg.osc_recent_high:
            return False
    # WP momentum: WP at idx vs WP at (idx - wp_lookback)
    if cfg.wp_lookback_sec is not None and cfg.wp_drop_min is not None:
        lb_bins = _bins_for_seconds(cfg.wp_lookback_sec)
        prior = idx - lb_bins
        if prior < 0:
            return False
        wp_now = wp_side[idx]
        wp_past = wp_side[prior]
        if pd.isna(wp_now) or pd.isna(wp_past):
            return False
        if (wp_past - wp_now) < cfg.wp_drop_min:
            return False
    return True


# ---- Replay engine with filter -----------------------------------------

def replay_one_side(
    game_ticker: str, side: str,
    prices_side: np.ndarray, other_prices: np.ndarray,
    wp_side: np.ndarray, periods: np.ndarray, elapsed: np.ndarray,
    cfg_filter: FilterConfig, cfg_exit: ExitConfig,
    is_fav_side: bool, abs_spread: float | None,
    collect_filtered: bool = False,
) -> tuple[list[Outcome], list[FilteredCandidate]]:
    """One-side replay with entry-filter evaluation and exit config.

    Partial-exit state machine (same as upside_capture):
      WATCHING → IN_POSITION → (stopped | full_exit_scale | HOLDING)
      HOLDING → (trailed_out | resolution)
    """
    outs: list[Outcome] = []
    filt: list[FilteredCandidate] = []
    n = len(prices_side)
    if n == 0:
        return outs, filt

    last_price = (
        float(prices_side[~np.isnan(prices_side)][-1])
        if np.any(~np.isnan(prices_side)) else None
    )

    in_pos = False
    holding = False
    re_entry_gated = False

    entry_price = entry_elapsed = entry_period = None
    held = 0
    cost_cash = 0.0
    cum_fees = 0.0
    mae = mfe = None
    realized_partial = 0.0
    first_exit_price = None
    trail_stop = None
    mfe_since_partial = None
    partial_qty = 0

    for i in range(n):
        p = prices_side[i]
        if pd.isna(p):
            continue
        p = float(p)
        if not in_pos and not holding:
            if re_entry_gated:
                if p > cfg_exit.entry_threshold:
                    re_entry_gated = False
                continue
            if p <= cfg_exit.entry_threshold:
                # Candidate entry — check filter
                if not filter_passes(
                    cfg_filter, prices_side, wp_side, periods, elapsed,
                    i, side, is_fav_side,
                ):
                    if collect_filtered:
                        # Did this dip eventually reach exit threshold?
                        future = prices_side[i:]
                        future = future[~np.isnan(future)]
                        would = bool(
                            np.any(future >= cfg_exit.first_exit)
                        )
                        filt.append(FilteredCandidate(
                            game_ticker=game_ticker, side=side,
                            entry_price=p, entry_elapsed=float(elapsed[i]),
                            entry_period=(
                                int(periods[i]) if not pd.isna(periods[i]) else None
                            ),
                            would_have_completed=would,
                            abs_spread=abs_spread,
                        ))
                    # Gate re-entry (otherwise filter would refire each bin)
                    re_entry_gated = True
                    continue
                # Enter
                in_pos = True
                entry_price = p
                entry_elapsed = float(elapsed[i])
                entry_period = (
                    int(periods[i]) if not pd.isna(periods[i]) else None
                )
                held = TOTAL_CONTRACTS
                cost_cash = p * TOTAL_CONTRACTS
                cum_fees = maker_fee(TOTAL_CONTRACTS, p)
                mae = p
                mfe = p
                realized_partial = 0.0
                first_exit_price = None
                trail_stop = None
                mfe_since_partial = None
                partial_qty = 0
            continue

        # In position updates
        if p < mae:
            mae = p
        if p > mfe:
            mfe = p

        if in_pos and not holding:
            # Initial stop
            if cfg_exit.initial_stop is not None and p <= cfg_exit.initial_stop:
                exit_fee = maker_fee(held, p)
                gross = p * held - cost_cash
                net = gross - cum_fees - exit_fee
                hold = float(elapsed[i]) - entry_elapsed
                outs.append(Outcome(
                    game_ticker=game_ticker, side=side,
                    entry_price=entry_price, entry_elapsed=entry_elapsed,
                    entry_period=entry_period, exit_type="stopped_out",
                    contracts=held, net_pnl=net, gross_pnl=gross,
                    hold_time_sec=hold, max_adverse=mae,
                    max_favorable=mfe, first_exit_price=None,
                    final_price=p, abs_spread=abs_spread,
                ))
                in_pos = False
                re_entry_gated = True
                continue

            # First exit
            if p >= cfg_exit.first_exit and cfg_exit.sell_pct > 0:
                pq = max(1, int(round(held * cfg_exit.sell_pct)))
                pq = min(pq, held)
                basis_per_share = cost_cash / held
                part_cost = basis_per_share * pq
                part_gross = p * pq - part_cost
                part_fee = maker_fee(pq, p)
                realized_partial = part_gross - part_fee
                cost_cash -= part_cost
                held -= pq
                partial_qty = pq
                first_exit_price = p

                if held == 0:
                    hold = float(elapsed[i]) - entry_elapsed
                    net = realized_partial - cum_fees
                    outs.append(Outcome(
                        game_ticker=game_ticker, side=side,
                        entry_price=entry_price, entry_elapsed=entry_elapsed,
                        entry_period=entry_period,
                        exit_type="full_exit", contracts=pq,
                        net_pnl=net, gross_pnl=part_gross,
                        hold_time_sec=hold, max_adverse=mae,
                        max_favorable=mfe, first_exit_price=p,
                        final_price=p, abs_spread=abs_spread,
                    ))
                    in_pos = False
                    re_entry_gated = True
                    continue

                # Move to HOLDING
                holding = True
                in_pos = False
                if cfg_exit.trailing_stop_distance is not None:
                    trail_stop = p - cfg_exit.trailing_stop_distance
                    mfe_since_partial = p
                else:
                    trail_stop = None
                continue

        elif holding:
            if cfg_exit.trailing_stop_distance is not None:
                if mfe_since_partial is None or p > mfe_since_partial:
                    mfe_since_partial = p
                    cand = p - cfg_exit.trailing_stop_distance
                    if trail_stop is None or cand > trail_stop:
                        trail_stop = cand
                if trail_stop is not None and p <= trail_stop:
                    exit_fee = maker_fee(held, p)
                    gross_rem = p * held - cost_cash
                    net = realized_partial + gross_rem - cum_fees - exit_fee
                    hold = float(elapsed[i]) - entry_elapsed
                    outs.append(Outcome(
                        game_ticker=game_ticker, side=side,
                        entry_price=entry_price, entry_elapsed=entry_elapsed,
                        entry_period=entry_period,
                        exit_type="trailed_out",
                        contracts=partial_qty + held, net_pnl=net,
                        gross_pnl=realized_partial + gross_rem,
                        hold_time_sec=hold, max_adverse=mae,
                        max_favorable=mfe, first_exit_price=first_exit_price,
                        final_price=p, abs_spread=abs_spread,
                    ))
                    holding = False
                    re_entry_gated = True
                    continue

    # End-of-timeseries resolution
    if (in_pos or holding) and entry_price is not None and last_price is not None:
        if last_price >= RESOLUTION_WIN_CUTOFF:
            resolution = 1.0
            exit_type = "resolution_win"
        elif last_price <= RESOLUTION_LOSS_CUTOFF:
            resolution = 0.0
            exit_type = "resolution_loss"
        else:
            resolution = float(last_price)
            exit_type = "held_indeterminate"
        exit_fee = (
            maker_fee(held, resolution) if exit_type == "held_indeterminate"
            else 0.0
        )
        gross_rem = resolution * held - cost_cash
        net = realized_partial + gross_rem - cum_fees - exit_fee
        hold = float(elapsed[-1]) - entry_elapsed
        outs.append(Outcome(
            game_ticker=game_ticker, side=side,
            entry_price=entry_price, entry_elapsed=entry_elapsed,
            entry_period=entry_period, exit_type=exit_type,
            contracts=partial_qty + held,
            net_pnl=net, gross_pnl=realized_partial + gross_rem,
            hold_time_sec=hold, max_adverse=mae,
            max_favorable=mfe, first_exit_price=first_exit_price,
            final_price=float(last_price), abs_spread=abs_spread,
        ))
    return outs, filt


def replay_all(
    games: list[dict], meta: dict,
    cfg_filter: FilterConfig, cfg_exit: ExitConfig,
    collect_filtered: bool = False,
) -> tuple[list[Outcome], list[FilteredCandidate]]:
    outs: list[Outcome] = []
    filt: list[FilteredCandidate] = []
    for g in games:
        m = meta.get(g["ticker"])
        if m is None or m["abs_spread"] is None or m["abs_spread"] > MAX_SPREAD_COMPETITIVE:
            continue
        ts = g["ts"]
        fav = ts["fav_kalshi_vwap"].values.astype(float)
        dog = 1.0 - fav
        if "fav_wp_espn" in ts.columns:
            fav_wp = ts["fav_wp_espn"].values.astype(float)
        else:
            fav_wp = np.full(len(ts), np.nan)
        dog_wp = 1.0 - fav_wp
        el = ts["game_seconds_elapsed"].values.astype(float)
        pr = ts["period"].values
        # Fav side (is_fav_side=True)
        o1, f1 = replay_one_side(
            g["ticker"], "fav", fav, dog, fav_wp, pr, el,
            cfg_filter, cfg_exit,
            is_fav_side=True, abs_spread=m["abs_spread"],
            collect_filtered=collect_filtered,
        )
        # Dog side
        o2, f2 = replay_one_side(
            g["ticker"], "dog", dog, fav, dog_wp, pr, el,
            cfg_filter, cfg_exit,
            is_fav_side=False, abs_spread=m["abs_spread"],
            collect_filtered=collect_filtered,
        )
        outs.extend(o1)
        outs.extend(o2)
        filt.extend(f1)
        filt.extend(f2)
    return outs, filt


# ---- Summaries ----------------------------------------------------------

def summarize(outs: list[Outcome], n_games: int) -> dict:
    n = len(outs)
    if n == 0:
        return {"n": 0, "mean_pnl": float("nan"), "median_pnl": float("nan"),
                "std_pnl": 0.0, "win_rate": 0.0, "annual_ev": 0.0,
                "max_loss": 0.0, "max_win": 0.0, "counts": {}}
    pnls = np.array([o.net_pnl for o in outs])
    counts: dict[str, int] = {}
    for o in outs:
        counts[o.exit_type] = counts.get(o.exit_type, 0) + 1
    return {
        "n": n,
        "mean_pnl": float(pnls.mean()),
        "median_pnl": float(np.median(pnls)),
        "std_pnl": float(pnls.std(ddof=1)) if n > 1 else 0.0,
        "win_rate": 100 * float((pnls > 0).mean()),
        "annual_ev": float(pnls.mean()) * (n / n_games if n_games else 0) * REG_SEASON_COMPETITIVE,
        "entries_per_game": n / n_games if n_games else 0,
        "max_loss": float(pnls.min()),
        "max_win": float(pnls.max()),
        "counts": counts,
    }


def _cnt(counts: dict, *keys: str) -> int:
    return sum(counts.get(k, 0) for k in keys)


def _fail_rate(outs: list[Outcome]) -> float:
    if not outs:
        return 0.0
    losses = sum(1 for o in outs if o.net_pnl < 0)
    return 100 * losses / len(outs)


def _row_for_simple(
    label: str, s: dict, sweep_rows: list[dict], extra: dict | None = None,
) -> str:
    c = s["counts"]
    rt = _cnt(c, "full_exit", "round_trip")
    stopped = _cnt(c, "stopped_out")
    failed = _cnt(c, "stopped_out", "resolution_loss", "held_to_loss", "held_indeterminate")
    fr = _fail_rate_counts(s)
    row = {
        "label": label, "entries": s["n"],
        "completed_rt": rt, "failed": failed,
        "fail_rate": fr, "mean_pnl": s["mean_pnl"],
        "annual_ev": s["annual_ev"],
    }
    if extra:
        row.update(extra)
    sweep_rows.append(row)
    return (
        f"| {label} | {s['n']} | {rt} | {failed} | {fr:.1f}% | "
        f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |"
    )


def _fail_rate_counts(s: dict) -> float:
    # Use stop+resolution_loss as "failed" for diagnostic rows
    n = s["n"] or 1
    failed = (
        s["counts"].get("stopped_out", 0)
        + s["counts"].get("resolution_loss", 0)
    )
    return 100 * failed / n


# ---- Report sections ----------------------------------------------------

def render_simple_table_header(md: list[str]) -> None:
    md.append(
        "| Filter | Entries | Filtered out | Completed RT | Failed | "
        "Fail rate | Mean P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")


def part_1a_oscillation(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    entry: float, exit_: float,
) -> tuple[FilterConfig, dict, list[dict]]:
    md.append("## Part 1A — Oscillation confirmation\n")
    md.append(
        "Only enter if this side's Kalshi price was ≥ `recent_high` "
        "within the last `lookback` seconds. Simple exit "
        "(100% at $0.50, stop $0.34).\n"
    )
    render_simple_table_header(md)
    results: list[tuple[FilterConfig, dict]] = []
    sweep_rows: list[dict] = []
    baseline_outs, _ = replay_all(games, meta, FilterConfig(), SIMPLE_EXIT)
    s0 = summarize(baseline_outs, n_games)
    md.append(
        f"| No filter | {s0['n']} | 0 | {_cnt(s0['counts'],'full_exit','round_trip')} | "
        f"{_cnt(s0['counts'],'stopped_out','resolution_loss','held_to_loss')} | "
        f"{_fail_rate_counts(s0):.1f}% | ${s0['mean_pnl']:+.2f} | "
        f"${s0['annual_ev']:+,.0f} |"
    )
    sweep_rows.append({"part": "1A", "label": "No filter",
                       "mean_pnl": s0['mean_pnl'], "annual_ev": s0['annual_ev'],
                       "entries": s0['n'], "exit": "simple"})
    best = (FilterConfig(), s0)
    for lb in (120, 180, 300, 600, 900, 1200):
        for rh in (0.45, 0.48, 0.50, 0.55):
            cfg = FilterConfig(osc_lookback_sec=lb, osc_recent_high=rh)
            outs, filt = replay_all(games, meta, cfg, SIMPLE_EXIT)
            s = summarize(outs, n_games)
            n_filt = len(filt)
            rt = _cnt(s['counts'],'full_exit','round_trip')
            failed = _cnt(s['counts'],'stopped_out','resolution_loss','held_to_loss')
            md.append(
                f"| {lb//60} min / ${rh:.2f} | {s['n']} | {n_filt} | {rt} | "
                f"{failed} | {_fail_rate_counts(s):.1f}% | "
                f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |"
            )
            sweep_rows.append({
                "part": "1A", "label": f"osc_{lb}s_${rh:.2f}",
                "osc_lookback_sec": lb, "osc_recent_high": rh,
                "entries": s['n'], "mean_pnl": s['mean_pnl'],
                "annual_ev": s['annual_ev'], "exit": "simple",
            })
            results.append((cfg, s))
            if s["mean_pnl"] > best[1]["mean_pnl"]:
                best = (cfg, s)
    md.append("")
    md.append(
        f"**Best oscillation filter: lookback {best[0].osc_lookback_sec}s, "
        f"recent_high ${best[0].osc_recent_high:.2f} → mean P&L "
        f"${best[1]['mean_pnl']:+.2f}**\n"
    )
    return best[0], best[1], sweep_rows


def part_1b_wp(
    md: list[str], games: list[dict], meta: dict, n_games: int,
) -> tuple[FilterConfig, dict, list[dict]]:
    md.append("## Part 1B — ESPN WP rate-of-change\n")
    md.append(
        "Only enter if this side's ESPN WP dropped ≥ `drop` within "
        "the last `lookback` seconds. Simple exit.\n"
    )
    render_simple_table_header(md)
    baseline_outs, _ = replay_all(games, meta, FilterConfig(), SIMPLE_EXIT)
    s0 = summarize(baseline_outs, n_games)
    md.append(
        f"| No filter | {s0['n']} | 0 | {_cnt(s0['counts'],'full_exit','round_trip')} | "
        f"{_cnt(s0['counts'],'stopped_out','resolution_loss','held_to_loss')} | "
        f"{_fail_rate_counts(s0):.1f}% | ${s0['mean_pnl']:+.2f} | "
        f"${s0['annual_ev']:+,.0f} |"
    )
    sweep_rows: list[dict] = []
    best = (FilterConfig(), s0)
    for lb in (120, 180, 300):
        for drop in (0.03, 0.05, 0.08, 0.10):
            cfg = FilterConfig(wp_lookback_sec=lb, wp_drop_min=drop)
            outs, filt = replay_all(games, meta, cfg, SIMPLE_EXIT)
            s = summarize(outs, n_games)
            n_filt = len(filt)
            rt = _cnt(s['counts'],'full_exit','round_trip')
            failed = _cnt(s['counts'],'stopped_out','resolution_loss','held_to_loss')
            md.append(
                f"| {lb//60} min / {drop*100:.0f}pp | {s['n']} | {n_filt} | "
                f"{rt} | {failed} | {_fail_rate_counts(s):.1f}% | "
                f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |"
            )
            sweep_rows.append({
                "part": "1B", "label": f"wp_{lb}s_{int(drop*100)}pp",
                "wp_lookback_sec": lb, "wp_drop_min": drop,
                "entries": s['n'], "mean_pnl": s['mean_pnl'],
                "annual_ev": s['annual_ev'], "exit": "simple",
            })
            if s["mean_pnl"] > best[1]["mean_pnl"]:
                best = (cfg, s)
    md.append("")
    md.append(
        f"**Best WP-momentum filter: lookback {best[0].wp_lookback_sec}s, "
        f"drop ≥ {best[0].wp_drop_min*100:.0f}pp → mean P&L "
        f"${best[1]['mean_pnl']:+.2f}**\n"
    )
    return best[0], best[1], sweep_rows


def part_1c_fav(
    md: list[str], games: list[dict], meta: dict, n_games: int,
) -> tuple[FilterConfig, dict, list[dict]]:
    md.append("## Part 1C — Favorite-side only\n")
    render_simple_table_header(md)
    sweep_rows: list[dict] = []
    results = {}
    # Baseline (both sides)
    outs, _ = replay_all(games, meta, FilterConfig(), SIMPLE_EXIT)
    s0 = summarize(outs, n_games)
    md.append(
        f"| Both sides | {s0['n']} | 0 | {_cnt(s0['counts'],'full_exit','round_trip')} | "
        f"{_cnt(s0['counts'],'stopped_out','resolution_loss','held_to_loss')} | "
        f"{_fail_rate_counts(s0):.1f}% | ${s0['mean_pnl']:+.2f} | "
        f"${s0['annual_ev']:+,.0f} |"
    )
    results["both"] = (FilterConfig(), s0)
    # Fav only
    cfg_fav = FilterConfig(fav_only=True)
    outs_fav, _ = replay_all(games, meta, cfg_fav, SIMPLE_EXIT)
    s_fav = summarize(outs_fav, n_games)
    md.append(
        f"| Fav only | {s_fav['n']} | — | "
        f"{_cnt(s_fav['counts'],'full_exit','round_trip')} | "
        f"{_cnt(s_fav['counts'],'stopped_out','resolution_loss','held_to_loss')} | "
        f"{_fail_rate_counts(s_fav):.1f}% | ${s_fav['mean_pnl']:+.2f} | "
        f"${s_fav['annual_ev']:+,.0f} |"
    )
    results["fav"] = (cfg_fav, s_fav)
    sweep_rows.append({"part": "1C", "label": "fav_only", "entries": s_fav['n'],
                       "mean_pnl": s_fav['mean_pnl'], "annual_ev": s_fav['annual_ev'],
                       "exit": "simple"})
    # Dog only (fav_only=False with manual filter — reuse by overriding
    # in a separate quick filter via a predicate)
    dog_outs = _replay_dog_only(games, meta, SIMPLE_EXIT)
    s_dog = summarize(dog_outs, n_games)
    md.append(
        f"| Dog only | {s_dog['n']} | — | "
        f"{_cnt(s_dog['counts'],'full_exit','round_trip')} | "
        f"{_cnt(s_dog['counts'],'stopped_out','resolution_loss','held_to_loss')} | "
        f"{_fail_rate_counts(s_dog):.1f}% | ${s_dog['mean_pnl']:+.2f} | "
        f"${s_dog['annual_ev']:+,.0f} |"
    )
    sweep_rows.append({"part": "1C", "label": "dog_only", "entries": s_dog['n'],
                       "mean_pnl": s_dog['mean_pnl'], "annual_ev": s_dog['annual_ev'],
                       "exit": "simple"})
    md.append("")
    best_cfg = FilterConfig(fav_only=True)
    best_s = s_fav
    if s_dog["mean_pnl"] > s_fav["mean_pnl"]:
        # Dog-only isn't directly expressible in FilterConfig; keep fav_only
        # as the "best" and note the dog result in the table.
        md.append(
            f"Note: dog-only mean P&L (${s_dog['mean_pnl']:+.2f}) "
            f"exceeds fav-only (${s_fav['mean_pnl']:+.2f}) — "
            "worth investigating but not combinable with the current "
            "FilterConfig shape.\n"
        )
    md.append(
        f"**Favorite-side filter → mean P&L ${s_fav['mean_pnl']:+.2f} "
        f"(vs both-sides baseline ${s0['mean_pnl']:+.2f})**\n"
    )
    return best_cfg, best_s, sweep_rows


def _replay_dog_only(games, meta, cfg_exit):
    """Dog-only via ad-hoc predicate (not combinable in FilterConfig)."""
    outs = []
    for g in games:
        m = meta.get(g["ticker"])
        if m is None or m["abs_spread"] is None or m["abs_spread"] > MAX_SPREAD_COMPETITIVE:
            continue
        ts = g["ts"]
        fav = ts["fav_kalshi_vwap"].values.astype(float)
        dog = 1.0 - fav
        el = ts["game_seconds_elapsed"].values.astype(float)
        pr = ts["period"].values
        dog_wp = 1.0 - ts["fav_wp_espn"].values.astype(float)
        o, _ = replay_one_side(
            g["ticker"], "dog", dog, fav, dog_wp, pr, el,
            FilterConfig(), cfg_exit, is_fav_side=False,
            abs_spread=m["abs_spread"],
        )
        outs.extend(o)
    return outs


def part_1d_period(
    md: list[str], games: list[dict], meta: dict, n_games: int,
) -> tuple[FilterConfig, dict, list[dict]]:
    md.append("## Part 1D — Period restriction\n")
    render_simple_table_header(md)
    sweep_rows: list[dict] = []
    # Baseline
    outs, _ = replay_all(games, meta, FilterConfig(), SIMPLE_EXIT)
    s0 = summarize(outs, n_games)
    md.append(
        f"| All periods | {s0['n']} | 0 | {_cnt(s0['counts'],'full_exit','round_trip')} | "
        f"{_cnt(s0['counts'],'stopped_out','resolution_loss','held_to_loss')} | "
        f"{_fail_rate_counts(s0):.1f}% | ${s0['mean_pnl']:+.2f} | "
        f"${s0['annual_ev']:+,.0f} |"
    )
    best = (FilterConfig(), s0)
    for label, allowed in (
        ("Q1 only", {1}),
        ("Q1+Q2", {1, 2}),
        ("Q1+Q2+Q3", {1, 2, 3}),
    ):
        cfg = FilterConfig(allowed_periods=allowed)
        outs, filt = replay_all(games, meta, cfg, SIMPLE_EXIT)
        s = summarize(outs, n_games)
        n_filt = len(filt)
        rt = _cnt(s['counts'],'full_exit','round_trip')
        failed = _cnt(s['counts'],'stopped_out','resolution_loss','held_to_loss')
        md.append(
            f"| {label} | {s['n']} | {n_filt} | {rt} | {failed} | "
            f"{_fail_rate_counts(s):.1f}% | ${s['mean_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
        sweep_rows.append({
            "part": "1D", "label": label, "allowed_periods": sorted(allowed),
            "entries": s['n'], "mean_pnl": s['mean_pnl'],
            "annual_ev": s['annual_ev'], "exit": "simple",
        })
        if s["mean_pnl"] > best[1]["mean_pnl"]:
            best = (cfg, s)
    md.append("")
    if best[0].allowed_periods is None:
        label = "all periods"
    else:
        label = "Q" + "/".join(str(p) for p in sorted(best[0].allowed_periods))
    md.append(f"**Best period filter: {label} → mean P&L ${best[1]['mean_pnl']:+.2f}**\n")
    return best[0], best[1], sweep_rows


def part_2_best_each(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    best_osc: FilterConfig, best_wp: FilterConfig,
    best_fav: FilterConfig, best_period: FilterConfig,
) -> list[dict]:
    md.append("## Part 2 — Best individual filters with both exit strategies\n")
    md.append(
        "| Config | Filter | Entries | Mean P&L (simple) | Mean P&L (upside) | "
        "Annual EV (upside) |"
    )
    md.append("|---|---|---:|---:|---:|---:|")
    rows = []
    cfgs = [
        ("Baseline", FilterConfig(), "None"),
        ("Best oscillation",
         best_osc,
         f"osc {best_osc.osc_lookback_sec}s / ${best_osc.osc_recent_high}" if best_osc.osc_lookback_sec else "—"),
        ("Best WP momentum",
         best_wp,
         f"wp {best_wp.wp_lookback_sec}s / {int((best_wp.wp_drop_min or 0)*100)}pp" if best_wp.wp_lookback_sec else "—"),
        ("Best fav-only", best_fav, "fav_only=True" if best_fav.fav_only else "—"),
        ("Best period",
         best_period,
         "Q" + "/".join(str(p) for p in sorted(best_period.allowed_periods)) if best_period.allowed_periods else "—"),
    ]
    for label, cfg, fd in cfgs:
        o_s, _ = replay_all(games, meta, cfg, SIMPLE_EXIT)
        s_s = summarize(o_s, n_games)
        o_u, _ = replay_all(games, meta, cfg, UPSIDE_EXIT)
        s_u = summarize(o_u, n_games)
        md.append(
            f"| {label} | {fd} | {s_s['n']} | ${s_s['mean_pnl']:+.2f} | "
            f"${s_u['mean_pnl']:+.2f} | ${s_u['annual_ev']:+,.0f} |"
        )
        rows.append({
            "part": "2", "label": label, "filter_desc": fd,
            "entries": s_s["n"], "mean_pnl_simple": s_s["mean_pnl"],
            "mean_pnl_upside": s_u["mean_pnl"],
            "annual_ev_simple": s_s["annual_ev"],
            "annual_ev_upside": s_u["annual_ev"],
        })
    md.append("")
    return rows


def part_3_combined(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    best_osc: FilterConfig, best_wp: FilterConfig,
    best_fav: FilterConfig, best_period: FilterConfig,
) -> tuple[dict, list[dict]]:
    md.append("## Part 3 — Combined filter grid search\n")
    md.append(
        "2×2×2×2 = 16 filter combinations × 2 exit strategies = "
        "**32 configurations**. Sorted by mean P&L descending. "
        "Positive-EV rows (if any) bolded.\n"
    )
    md.append(
        "| # | Osc | WP | Fav | Period | Exit | Entries | Fail rate | "
        "Mean P&L | Annual EV |"
    )
    md.append("|---|:-:|:-:|:-:|:-:|:-:|---:|---:|---:|---:|")
    rows = []
    # Extract best params
    osc_on = best_osc
    wp_on = best_wp
    fav_on = best_fav
    per_on = best_period
    for osc_flag in (True, False):
        for wp_flag in (True, False):
            for fav_flag in (True, False):
                for per_flag in (True, False):
                    combo = FilterConfig(
                        osc_lookback_sec=osc_on.osc_lookback_sec if osc_flag else None,
                        osc_recent_high=osc_on.osc_recent_high if osc_flag else None,
                        wp_lookback_sec=wp_on.wp_lookback_sec if wp_flag else None,
                        wp_drop_min=wp_on.wp_drop_min if wp_flag else None,
                        fav_only=fav_on.fav_only if fav_flag else False,
                        allowed_periods=per_on.allowed_periods if per_flag else None,
                    )
                    for exit_cfg in (SIMPLE_EXIT, UPSIDE_EXIT):
                        outs, _ = replay_all(games, meta, combo, exit_cfg)
                        s = summarize(outs, n_games)
                        rows.append({
                            "osc": osc_flag, "wp": wp_flag,
                            "fav": fav_flag, "period": per_flag,
                            "exit": exit_cfg.label,
                            "entries": s["n"],
                            "fail_rate": _fail_rate_counts(s),
                            "mean_pnl": s["mean_pnl"],
                            "annual_ev": s["annual_ev"],
                            "std_pnl": s["std_pnl"],
                            "cfg_filter": combo,
                            "cfg_exit": exit_cfg,
                        })
    # Sort: drop NaN (zero-entry) configs to the bottom; within real
    # configs, highest mean P&L first.
    def _sort_key(r: dict) -> tuple[int, float]:
        bad = r["entries"] == 0 or np.isnan(r["mean_pnl"])
        return (1 if bad else 0, -r["mean_pnl"] if not bad else 0.0)
    rows.sort(key=_sort_key)
    for i, r in enumerate(rows, 1):
        def _mark(b: bool) -> str:
            return "✓" if b else "—"
        label = f"${r['mean_pnl']:+.2f}"
        if r['mean_pnl'] > 0:
            label = f"**${r['mean_pnl']:+.2f}**"
        annual = f"${r['annual_ev']:+,.0f}"
        if r['mean_pnl'] > 0:
            annual = f"**{annual}**"
        md.append(
            f"| {i} | {_mark(r['osc'])} | {_mark(r['wp'])} | "
            f"{_mark(r['fav'])} | {_mark(r['period'])} | "
            f"{r['exit']} | {r['entries']} | {r['fail_rate']:.1f}% | "
            f"{label} | {annual} |"
        )
    md.append("")
    best = rows[0]
    md.append(
        f"**Best combined: osc={best['osc']}, wp={best['wp']}, "
        f"fav={best['fav']}, period={best['period']}, "
        f"exit={best['exit']} → mean P&L ${best['mean_pnl']:+.2f}**\n"
    )
    n_positive = sum(1 for r in rows if r["mean_pnl"] > 0)
    md.append(
        f"Positive-EV configurations found: **{n_positive} of {len(rows)}**\n"
    )
    return best, rows


def part_4_detail(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    best_row: dict,
) -> list[Outcome]:
    md.append("## Part 4 — Best configuration detailed breakdown\n")
    cfg_f: FilterConfig = best_row["cfg_filter"]
    cfg_e: ExitConfig = best_row["cfg_exit"]
    md.append("### Best configuration\n")
    md.append(f"- Entry: ${cfg_e.entry_threshold:.2f} ({TOTAL_CONTRACTS} contracts)")
    md.append("- Filters:")
    md.append(
        f"  - Oscillation: "
        + ("on — lookback " + str(cfg_f.osc_lookback_sec) + "s, recent_high $"
           + f"{cfg_f.osc_recent_high:.2f}" if cfg_f.osc_lookback_sec else "off")
    )
    md.append(
        f"  - ESPN WP momentum: "
        + ("on — lookback " + str(cfg_f.wp_lookback_sec) + "s, drop ≥ "
           + f"{(cfg_f.wp_drop_min or 0)*100:.0f}pp" if cfg_f.wp_lookback_sec else "off")
    )
    md.append(f"  - Favorite-side only: {'yes' if cfg_f.fav_only else 'no'}")
    if cfg_f.allowed_periods is None:
        md.append("  - Period restriction: none")
    else:
        md.append(
            "  - Period restriction: Q"
            + "/".join(str(p) for p in sorted(cfg_f.allowed_periods))
        )
    md.append(f"- Exit strategy: {cfg_e.label}")
    sl = "None" if cfg_e.initial_stop is None else f"${cfg_e.initial_stop:.2f}"
    md.append(f"- Stop-loss: {sl}")
    md.append("")

    outs, filt = replay_all(games, meta, cfg_f, cfg_e, collect_filtered=True)
    s = summarize(outs, n_games)
    n = s["n"] or 1

    md.append("### Outcome distribution\n")
    md.append("| Outcome | Count | % | Mean P&L | Median P&L |")
    md.append("|---|---:|---:|---:|---:|")
    for label, keys in (
        ("Full exit (first target)", ("full_exit",)),
        ("Stopped out", ("stopped_out",)),
        ("Trailed out", ("trailed_out",)),
        ("Resolution win", ("resolution_win",)),
        ("Resolution loss", ("resolution_loss",)),
        ("Held indeterminate", ("held_indeterminate",)),
    ):
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
    buckets = [
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
    for label, pred in buckets:
        cnt = sum(1 for o in outs if pred(o.net_pnl))
        md.append(f"| {label} | {cnt} | {100*cnt/n:.1f}% |")
    md.append("")

    if cfg_f.allowed_periods is None:
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

    # Risk metrics
    md.append("### Risk metrics\n")
    pnls = np.array([o.net_pnl for o in outs]) if outs else np.array([])
    wins = pnls[pnls > 0] if len(pnls) else np.array([])
    losses = pnls[pnls < 0] if len(pnls) else np.array([])
    avg_w = float(wins.mean()) if len(wins) else float("nan")
    avg_l = float(losses.mean()) if len(losses) else float("nan")
    ratio = abs(avg_w / avg_l) if len(wins) and len(losses) and avg_l != 0 else float("nan")
    sharpe = s["mean_pnl"] / s["std_pnl"] if s["std_pnl"] > 0 else 0.0
    p = len(wins) / s["n"] if s["n"] else 0
    q = 1 - p
    f_star = (p * ratio - q) / ratio if ratio and not np.isnan(ratio) and ratio > 0 else 0.0
    md.append("| Metric | Value |")
    md.append("|---|---|")
    md.append(f"| Sharpe-like | {sharpe:.3f} |")
    md.append(f"| Win rate (net > 0) | {s['win_rate']:.1f}% |")
    md.append(f"| Mean winner | ${avg_w:+.2f} |")
    md.append(f"| Mean loser | ${avg_l:+.2f} |")
    if not np.isnan(ratio):
        md.append(f"| Win/loss ratio | {ratio:.2f}× |")
    md.append(f"| Max single loss | ${s['max_loss']:+.2f} |")
    md.append(f"| Max single win | ${s['max_win']:+.2f} |")
    md.append(f"| Kelly f* | {f_star:.3f} |")
    md.append("")
    return outs


def part_5_evolution(
    md: list[str], n_games: int, best_row: dict,
) -> None:
    md.append("## Part 5 — Full strategy evolution\n")
    md.append(
        "| Strategy | Entries/yr | Mean P&L | Annual EV | Max loss | Sharpe |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    md.append(
        "| 1. Naive (no stop, no filter) | ~1,404 | −$4.22 | −$5,963 | −$40 | −0.16 |"
    )
    md.append(
        "| 2. + Stop-loss @$0.34 | ~1,533 | −$1.27 | −$2,531 | −$16 | −0.09 |"
    )
    md.append(
        "| 3. + Upside capture (25/75) | ~1,112 | −$0.59 | −$852 | −$28 | −0.03 |"
    )
    entries_per_yr = best_row["entries"] * REG_SEASON_COMPETITIVE / n_games
    sharpe = (
        best_row["mean_pnl"] / best_row["std_pnl"]
        if best_row["std_pnl"] > 0 else 0.0
    )
    mn_label = f"${best_row['mean_pnl']:+.2f}"
    ev_label = f"${best_row['annual_ev']:+,.0f}"
    if best_row["mean_pnl"] > 0:
        mn_label = f"**{mn_label}**"
        ev_label = f"**{ev_label}**"
    md.append(
        f"| 4. + Entry filters (best combo) | ~{entries_per_yr:,.0f} | "
        f"{mn_label} | {ev_label} | — | {sharpe:.2f} |"
    )
    md.append(
        "| 5. Bilateral only | ~84 | +$19.14 | +$1,608 | $0 | ∞ |"
    )
    # Row 6: combined strategy = filtered Strategy 3 + bilateral
    combined_ev = best_row["annual_ev"] + 1608
    md.append(
        f"| 6. Best combo + bilateral | ~{entries_per_yr + 84:,.0f} | — | "
        f"${combined_ev:+,.0f} | — | — |"
    )
    md.append("")


def part_6_diagnostic(
    md: list[str], games: list[dict], meta: dict, n_games: int,
    best_row: dict,
) -> None:
    md.append("## Part 6 — Filter diagnostic: what gets rejected?\n")
    cfg_f: FilterConfig = best_row["cfg_filter"]
    cfg_e: ExitConfig = best_row["cfg_exit"]
    passed, filtered = replay_all(
        games, meta, cfg_f, cfg_e, collect_filtered=True,
    )
    n_passed = len(passed)
    n_filtered = len(filtered)
    total = n_passed + n_filtered
    if total == 0:
        md.append("_No candidate entries._\n")
        return
    filt_would_complete = sum(1 for f in filtered if f.would_have_completed)
    filt_would_fail = n_filtered - filt_would_complete

    # Of passed: how many reached first_exit at some point.
    # For simple exit: full_exit means we closed at first_exit.
    # For upside exit: full_exit, trailed_out, or resolution_win all
    # imply price reached ≥ first_exit during the hold.
    passed_completed = sum(
        1 for o in passed
        if o.exit_type in ("full_exit", "trailed_out", "resolution_win")
    )
    # Of passed: how many failed (any loss outcome)
    passed_failed = sum(
        1 for o in passed
        if o.exit_type in ("stopped_out", "resolution_loss",
                           "held_indeterminate")
    )

    md.append(
        f"Total candidate entries: **{total}**\n"
        f"- Passed filter: **{n_passed}** ({100*n_passed/total:.1f}%)\n"
        f"- Filtered out: **{n_filtered}** ({100*n_filtered/total:.1f}%)\n"
    )
    md.append("\nOf the filtered-out entries:")
    md.append(
        f"- Would have reached first exit (${cfg_e.first_exit:.2f}) if held: "
        f"**{filt_would_complete}** "
        f"({100 * filt_would_complete / max(1, n_filtered):.1f}%)"
    )
    md.append(
        f"- Would NOT have reached first exit: **{filt_would_fail}** "
        f"({100 * filt_would_fail / max(1, n_filtered):.1f}%) — correctly rejected\n"
    )
    # Precision: of entries we reject, how many were "bad" (would have failed)
    precision = 100 * filt_would_fail / n_filtered if n_filtered else 0.0
    # Recall: of "good" entries (would complete), how many did we keep
    total_good = passed_completed + filt_would_complete
    recall = (
        100 * passed_completed / total_good if total_good else 0.0
    )
    md.append(
        f"**Filter precision** (correctly rejected / total rejected): "
        f"{precision:.1f}%"
    )
    md.append(
        f"**Filter recall** (good entries kept / total good entries): "
        f"{recall:.1f}%"
    )
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
    md.append("# Strategy 3 — Entry Filter Sweep\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Tests entry-side filters on the Strategy 3 replay engine "
        "across 165 competitive games. Four filters: oscillation "
        "confirmation, ESPN WP rate-of-change, favorite-side only, "
        "and period restriction. Individual sweeps (Part 1), best-"
        "individual with both exits (Part 2), combined grid search "
        "(Part 3), best-config detail (Part 4), evolution table "
        "(Part 5), filter diagnostic (Part 6).\n"
    )

    all_sweep_rows: list[dict] = []

    best_osc_cfg, _, rows = part_1a_oscillation(
        md, games, meta, n_games, args.entry, args.exit_,
    )
    all_sweep_rows.extend(rows)
    best_wp_cfg, _, rows = part_1b_wp(md, games, meta, n_games)
    all_sweep_rows.extend(rows)
    best_fav_cfg, _, rows = part_1c_fav(md, games, meta, n_games)
    all_sweep_rows.extend(rows)
    best_period_cfg, _, rows = part_1d_period(md, games, meta, n_games)
    all_sweep_rows.extend(rows)

    rows_p2 = part_2_best_each(
        md, games, meta, n_games,
        best_osc_cfg, best_wp_cfg, best_fav_cfg, best_period_cfg,
    )
    all_sweep_rows.extend(rows_p2)

    best_row, grid_rows = part_3_combined(
        md, games, meta, n_games,
        best_osc_cfg, best_wp_cfg, best_fav_cfg, best_period_cfg,
    )
    for r in grid_rows:
        all_sweep_rows.append({
            "part": "3",
            "osc": r["osc"], "wp": r["wp"], "fav": r["fav"],
            "period": r["period"], "exit": r["exit"],
            "entries": r["entries"], "fail_rate": r["fail_rate"],
            "mean_pnl": r["mean_pnl"], "annual_ev": r["annual_ev"],
            "std_pnl": r["std_pnl"],
        })

    best_outs = part_4_detail(md, games, meta, n_games, best_row)
    part_5_evolution(md, n_games, best_row)
    part_6_diagnostic(md, games, meta, n_games, best_row)

    # Write sweep CSV
    pd.DataFrame(all_sweep_rows).to_csv(SWEEP_CSV, index=False)
    log(f"Sweep CSV → {SWEEP_CSV}")

    # Best entries CSV
    if best_outs:
        pd.DataFrame([asdict(o) for o in best_outs]).to_csv(
            BEST_CSV, index=False,
        )
        log(f"Best entries CSV → {BEST_CSV}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md) + "\n")
    log(f"Report → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
