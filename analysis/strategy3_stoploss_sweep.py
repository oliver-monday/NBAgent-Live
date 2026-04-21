"""Strategy 3 stop-loss parameter sweep + position management simulation.

General-purpose replay engine: takes a 30s-bin Kalshi price
timeseries and a StrategyConfig, returns TradeOutcomes. Used to
sweep 20 stop-loss levels ($0.20–$0.39) plus a no-stop baseline
across all 165 competitive games' 422 entries. Also tests
averaging-in and partial-exit variants.

Run:
    python -m analysis.strategy3_stoploss_sweep \\
        --metadata data/wp_kalshi_paired/matched_games.csv

    python -m analysis.strategy3_stoploss_sweep \\
        --metadata data/wp_kalshi_paired/matched_games.csv \\
        --entry 0.40 --exit 0.50
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy3_stoploss_sweep.md"
)
SWEEP_CSV = PAIRED_DIR / "stoploss_sweep.csv"
BEST_CONFIG_CSV = PAIRED_DIR / "best_config_entries.csv"

TICKER_RE = re.compile(r"(KXNBAGAME-\d{2}[A-Z]{3}\d{2}[A-Z]{6})")
MAX_SPREAD_COMPETITIVE = 6.0
RESOLUTION_WIN_CUTOFF = 0.95
RESOLUTION_LOSS_CUTOFF = 0.05
TOTAL_CONTRACTS = 100
REG_SEASON_COMPETITIVE = 549


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def maker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1.0 - price) * 100) / 100


# ---- Dataclasses --------------------------------------------------------

@dataclass
class StrategyConfig:
    entry_threshold: float
    exit_threshold: float
    stop_loss: float | None = None
    avg_in_level: float | None = None
    avg_in_size_pct: float = 0.0   # fraction of total; remainder on avg-in
    partial_exit_level: float | None = None
    partial_exit_pct: float = 0.0


@dataclass
class TradeOutcome:
    game_ticker: str
    side: str
    entry_price: float
    entry_game_seconds: float
    entry_period: int | None
    exit_price: float
    exit_game_seconds: float
    exit_type: str
    contracts: int
    gross_pnl: float
    net_pnl: float
    hold_time_sec: float
    max_adverse_excursion: float
    max_favorable_excursion: float
    avg_in_triggered: bool
    avg_in_price: float | None
    effective_cost_basis: float
    would_have_completed_if_held: bool = False  # false-stop marker
    abs_spread: float | None = None


# ---- Replay engine ------------------------------------------------------

def replay(
    game_ticker: str, side: str,
    prices: np.ndarray, elapsed: np.ndarray, periods: np.ndarray,
    config: StrategyConfig,
) -> list[TradeOutcome]:
    """Replay one side's timeseries under the given config.

    Priority within a single bin: stop_loss > partial_exit > exit.
    After any exit, require price > entry_threshold at some bin
    before re-entry (prevents pathological same-bin re-entry after
    a stop-out).
    """
    out: list[TradeOutcome] = []
    n = len(prices)
    if n == 0:
        return out

    # State
    in_pos = False
    re_entry_gated = False  # True after exit until price recovers above entry_threshold
    entry_price = entry_elapsed = entry_period = None
    entry_time_idx = None
    held_contracts = 0
    cost_basis_cash = 0.0  # cumulative cost of current position in dollars
    cumulative_fees = 0.0   # fees paid so far on open legs
    mae = mfe = None
    avg_in_done = False
    avg_in_price = None
    partial_done = False
    realized_partial_pnl = 0.0  # net pnl from partial exit leg

    initial_size_pct = 1.0 - config.avg_in_size_pct if config.avg_in_level is not None else 1.0
    initial_size = max(1, int(round(TOTAL_CONTRACTS * initial_size_pct)))
    addon_size = TOTAL_CONTRACTS - initial_size

    last_price = float(prices[~np.isnan(prices)][-1]) if np.any(~np.isnan(prices)) else None

    for i in range(n):
        p = prices[i]
        if pd.isna(p):
            continue
        p = float(p)
        if not in_pos:
            if re_entry_gated:
                if p > config.entry_threshold:
                    re_entry_gated = False
                # even when gate releases, we only enter on next bin ≤ entry
                continue
            if p <= config.entry_threshold:
                # Enter initial tranche
                in_pos = True
                entry_price = p
                entry_elapsed = float(elapsed[i])
                entry_period = (
                    int(periods[i]) if not pd.isna(periods[i]) else None
                )
                entry_time_idx = i
                held_contracts = initial_size
                cost_basis_cash = p * initial_size
                cumulative_fees = maker_fee(initial_size, p)
                mae = p
                mfe = p
                avg_in_done = False
                avg_in_price = None
                partial_done = False
                realized_partial_pnl = 0.0
            continue

        # In position — update MAE/MFE
        if p < mae:
            mae = p
        if p > mfe:
            mfe = p

        # Check triggers in priority order
        # 1. Stop-loss
        if config.stop_loss is not None and p <= config.stop_loss:
            exit_fee = maker_fee(held_contracts, p)
            gross = (p * held_contracts) - cost_basis_cash
            net = gross - cumulative_fees - exit_fee + realized_partial_pnl
            hold = float(elapsed[i]) - entry_elapsed
            effective_basis = (
                cost_basis_cash / held_contracts if held_contracts > 0 else entry_price
            )
            out.append(TradeOutcome(
                game_ticker=game_ticker, side=side,
                entry_price=entry_price, entry_game_seconds=entry_elapsed,
                entry_period=entry_period, exit_price=p,
                exit_game_seconds=float(elapsed[i]),
                exit_type="stop_loss",
                contracts=held_contracts, gross_pnl=gross,
                net_pnl=net, hold_time_sec=hold,
                max_adverse_excursion=mae, max_favorable_excursion=mfe,
                avg_in_triggered=avg_in_done, avg_in_price=avg_in_price,
                effective_cost_basis=effective_basis,
                would_have_completed_if_held=_subsequent_reaches_exit(
                    prices, i + 1, config.exit_threshold,
                ),
            ))
            in_pos = False
            re_entry_gated = True
            continue

        # 2. Averaging-in (before partial exit; scaling in expects
        #    price is still below entry_threshold, and partial exit
        #    level is above entry_threshold)
        if (
            not avg_in_done
            and config.avg_in_level is not None
            and addon_size > 0
            and p <= config.avg_in_level
        ):
            avg_in_done = True
            avg_in_price = p
            cost_basis_cash += p * addon_size
            cumulative_fees += maker_fee(addon_size, p)
            held_contracts += addon_size
            # Continue loop — other triggers can fire next bin

        # 3. Partial exit
        if (
            not partial_done
            and config.partial_exit_level is not None
            and config.partial_exit_pct > 0
            and p >= config.partial_exit_level
        ):
            partial_qty = max(1, int(round(held_contracts * config.partial_exit_pct)))
            partial_qty = min(partial_qty, held_contracts)
            # Cost basis portion for the partial
            avg_basis = cost_basis_cash / held_contracts
            partial_cost = avg_basis * partial_qty
            partial_gross = (p * partial_qty) - partial_cost
            partial_fee = maker_fee(partial_qty, p)
            realized_partial_pnl += partial_gross - partial_fee
            # Remove partial from held position
            cost_basis_cash -= partial_cost
            held_contracts -= partial_qty
            partial_done = True
            if held_contracts == 0:
                # Partial exit consumed full position → record as partial_full
                hold = float(elapsed[i]) - entry_elapsed
                out.append(TradeOutcome(
                    game_ticker=game_ticker, side=side,
                    entry_price=entry_price,
                    entry_game_seconds=entry_elapsed,
                    entry_period=entry_period, exit_price=p,
                    exit_game_seconds=float(elapsed[i]),
                    exit_type="partial_full",
                    contracts=partial_qty,
                    gross_pnl=partial_gross,
                    net_pnl=realized_partial_pnl - cumulative_fees,
                    hold_time_sec=hold,
                    max_adverse_excursion=mae,
                    max_favorable_excursion=mfe,
                    avg_in_triggered=avg_in_done,
                    avg_in_price=avg_in_price,
                    effective_cost_basis=avg_basis,
                    would_have_completed_if_held=False,
                ))
                in_pos = False
                re_entry_gated = True
                continue

        # 4. Exit threshold
        if p >= config.exit_threshold:
            exit_fee = maker_fee(held_contracts, p)
            gross_remaining = (p * held_contracts) - cost_basis_cash
            # Total net for this entry: realized partial + remaining
            net = (
                realized_partial_pnl
                + gross_remaining
                - cumulative_fees
                - exit_fee
            )
            # Gross field reflects total (partial + remaining) for
            # interpretability.
            gross_total = realized_partial_pnl + gross_remaining + (
                cumulative_fees - cumulative_fees  # no op; keep structure
            )
            hold = float(elapsed[i]) - entry_elapsed
            effective_basis = cost_basis_cash / held_contracts if held_contracts > 0 else entry_price
            exit_label = "round_trip_partial" if partial_done else "round_trip"
            out.append(TradeOutcome(
                game_ticker=game_ticker, side=side,
                entry_price=entry_price, entry_game_seconds=entry_elapsed,
                entry_period=entry_period, exit_price=p,
                exit_game_seconds=float(elapsed[i]),
                exit_type=exit_label,
                contracts=held_contracts,
                gross_pnl=gross_total, net_pnl=net,
                hold_time_sec=hold,
                max_adverse_excursion=mae,
                max_favorable_excursion=mfe,
                avg_in_triggered=avg_in_done,
                avg_in_price=avg_in_price,
                effective_cost_basis=effective_basis,
                would_have_completed_if_held=True,
            ))
            in_pos = False
            re_entry_gated = True
            continue

    # End of timeseries: resolve
    if in_pos and last_price is not None:
        if last_price >= RESOLUTION_WIN_CUTOFF:
            resolution = 1.0
            exit_type = "resolution_win"
        elif last_price <= RESOLUTION_LOSS_CUTOFF:
            resolution = 0.0
            exit_type = "resolution_loss"
        else:
            resolution = float(last_price)
            exit_type = "resolution_mid"
        # Fees at resolution: $0 at settlement if clean 0/1; else maker at mid
        exit_fee = (
            maker_fee(held_contracts, resolution)
            if exit_type == "resolution_mid" else 0.0
        )
        gross_remaining = (resolution * held_contracts) - cost_basis_cash
        net = (
            realized_partial_pnl
            + gross_remaining
            - cumulative_fees
            - exit_fee
        )
        hold = float(elapsed[-1]) - entry_elapsed
        effective_basis = cost_basis_cash / held_contracts if held_contracts > 0 else entry_price
        out.append(TradeOutcome(
            game_ticker=game_ticker, side=side,
            entry_price=entry_price, entry_game_seconds=entry_elapsed,
            entry_period=entry_period, exit_price=float(last_price),
            exit_game_seconds=float(elapsed[-1]),
            exit_type=exit_type,
            contracts=held_contracts,
            gross_pnl=realized_partial_pnl + gross_remaining,
            net_pnl=net, hold_time_sec=hold,
            max_adverse_excursion=mae, max_favorable_excursion=mfe,
            avg_in_triggered=avg_in_done, avg_in_price=avg_in_price,
            effective_cost_basis=effective_basis,
            would_have_completed_if_held=False,
        ))
    return out


def _subsequent_reaches_exit(
    prices: np.ndarray, start_idx: int, exit_thr: float,
) -> bool:
    """Check if any price at or after start_idx reaches exit_thr."""
    if start_idx >= len(prices):
        return False
    for j in range(start_idx, len(prices)):
        p = prices[j]
        if pd.isna(p):
            continue
        if float(p) >= exit_thr:
            return True
    return False


# ---- Data loading -------------------------------------------------------

def load_metadata(path: Path) -> dict[str, dict]:
    df = pd.read_csv(path)
    out = {}
    for r in df.itertuples():
        out[str(r.kalshi_event_ticker)] = {
            "game_date": str(r.game_date),
            "abs_spread": float(r.abs_spread) if pd.notna(r.abs_spread) else None,
        }
    return out


def load_game_timeseries() -> list[dict]:
    """Return list of {ticker, ts_df} for each timeseries CSV."""
    games = []
    for p in sorted(PAIRED_DIR.glob("*_timeseries.csv")):
        m = TICKER_RE.match(p.stem)
        if not m:
            continue
        df = pd.read_csv(p)
        if df.empty:
            continue
        for c in ("game_seconds_elapsed", "period", "fav_kalshi_vwap"):
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(
            subset=["game_seconds_elapsed", "fav_kalshi_vwap"]
        ).sort_values("game_seconds_elapsed").reset_index(drop=True)
        games.append({"ticker": m.group(1), "ts": df})
    return games


def replay_all_games(
    games: list[dict], meta: dict[str, dict],
    config: StrategyConfig,
) -> list[TradeOutcome]:
    outcomes = []
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
            recs = replay(g["ticker"], side, prices, el, pr, config)
            for r in recs:
                r.abs_spread = m["abs_spread"]
            outcomes.extend(recs)
    return outcomes


# ---- Aggregation helpers ------------------------------------------------

def summarize(outcomes: list[TradeOutcome], n_games: int) -> dict:
    n = len(outcomes)
    if n == 0:
        return {
            "n": 0, "mean_pnl": float("nan"), "median_pnl": float("nan"),
            "win_rate": 0.0, "annual_ev": 0.0,
            "n_rt": 0, "n_stop": 0, "n_res_loss": 0, "n_res_win": 0,
            "n_res_mid": 0, "n_partial_full": 0, "false_stops_pct": 0.0,
            "max_single_loss": 0.0, "std_pnl": 0.0,
        }
    pnls = np.array([o.net_pnl for o in outcomes])
    mean_pnl = float(pnls.mean())
    entries_per_game = n / n_games if n_games else 0
    annual_ev = mean_pnl * entries_per_game * REG_SEASON_COMPETITIVE
    # False stops (stop-outs that would have reached exit if held)
    stops = [o for o in outcomes if o.exit_type == "stop_loss"]
    false_stops = [o for o in stops if o.would_have_completed_if_held]
    false_pct = 100 * len(false_stops) / len(stops) if stops else 0.0
    return {
        "n": n,
        "mean_pnl": mean_pnl,
        "median_pnl": float(np.median(pnls)),
        "std_pnl": float(pnls.std(ddof=1)) if n > 1 else 0.0,
        "win_rate": 100 * float((pnls > 0).mean()),
        "annual_ev": annual_ev,
        "entries_per_game": entries_per_game,
        "n_rt": sum(1 for o in outcomes if o.exit_type.startswith("round_trip")),
        "n_stop": len(stops),
        "n_res_loss": sum(1 for o in outcomes if o.exit_type == "resolution_loss"),
        "n_res_win": sum(1 for o in outcomes if o.exit_type == "resolution_win"),
        "n_res_mid": sum(1 for o in outcomes if o.exit_type == "resolution_mid"),
        "n_partial_full": sum(1 for o in outcomes if o.exit_type == "partial_full"),
        "false_stops_pct": false_pct,
        "max_single_loss": float(pnls.min()),
    }


# ---- Report sections ----------------------------------------------------

def part_1_sweep(
    md: list[str], games: list[dict], meta: dict[str, dict],
    entry_thr: float, exit_thr: float, n_games: int,
) -> tuple[float | None, list[dict]]:
    md.append("## Part 1 — Stop-loss parameter sweep\n")
    md.append(
        "Sweep stop-loss from $0.20 to $0.39 (plus no-stop baseline). "
        "For each level, replay all entries across "
        f"**{n_games} competitive games**.\n"
    )
    md.append(
        "| Stop-loss | Entries | RT | Stopped | Res loss | "
        "False stops | Mean P&L | Median P&L | Annual EV |"
    )
    md.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    levels: list[float | None] = [None] + [
        round(0.39 - 0.01 * i, 2) for i in range(20)
    ]
    rows = []
    for sl in levels:
        cfg = StrategyConfig(
            entry_threshold=entry_thr, exit_threshold=exit_thr,
            stop_loss=sl,
        )
        outcomes = replay_all_games(games, meta, cfg)
        s = summarize(outcomes, n_games)
        sl_label = "None" if sl is None else f"${sl:.2f}"
        md.append(
            f"| {sl_label} | {s['n']} | {s['n_rt']} | {s['n_stop']} | "
            f"{s['n_res_loss']} | {s['false_stops_pct']:.1f}% | "
            f"${s['mean_pnl']:+.2f} | ${s['median_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
        rows.append({
            "stop_loss": sl if sl is not None else "",
            **s,
        })
    md.append("")
    # Identify optimal + breakeven
    sweep_rows = [r for r in rows if r["n"] > 0]
    optimal = max(sweep_rows, key=lambda r: r["mean_pnl"])
    # Breakeven: lowest stop where mean_pnl ≥ 0
    breakeven = None
    for r in sorted(sweep_rows, key=lambda r: r["stop_loss"] if r["stop_loss"] != "" else -1):
        if r["stop_loss"] != "" and r["mean_pnl"] >= 0:
            breakeven = r
            break
    md.append("### Part 1 key metrics\n")
    opt_label = "None" if optimal["stop_loss"] == "" else f"${optimal['stop_loss']:.2f}"
    baseline = next(r for r in rows if r["stop_loss"] == "")
    md.append(f"- **Optimal stop-loss (max mean P&L): {opt_label}**")
    md.append(
        f"  - Mean P&L at optimum: **${optimal['mean_pnl']:+.2f}** "
        f"(vs ${baseline['mean_pnl']:+.2f} baseline)"
    )
    md.append(
        f"  - Annual EV at optimum: **${optimal['annual_ev']:+,.0f}** "
        f"(vs ${baseline['annual_ev']:+,.0f} baseline)"
    )
    md.append(
        f"  - False-stop rate at optimum: {optimal['false_stops_pct']:.1f}%"
    )
    md.append(f"  - Win rate at optimum: {optimal['win_rate']:.1f}%")
    if breakeven:
        md.append(
            f"- **Breakeven stop-loss (first level with mean P&L ≥ 0): "
            f"${breakeven['stop_loss']:.2f}** "
            f"(mean ${breakeven['mean_pnl']:+.2f})"
        )
    else:
        md.append("- **No breakeven stop-loss found in sweep range.**")
    md.append("")
    # Write sweep CSV
    pd.DataFrame(rows).to_csv(SWEEP_CSV, index=False)
    log(f"Sweep CSV → {SWEEP_CSV}")
    best_sl = optimal["stop_loss"] if optimal["stop_loss"] != "" else None
    return best_sl, rows


def part_2_avg_in(
    md: list[str], games: list[dict], meta: dict[str, dict],
    entry_thr: float, exit_thr: float, n_games: int,
    best_sl: float | None,
) -> None:
    md.append("## Part 2 — Averaging-in simulation\n")
    sl_label = "None" if best_sl is None else f"${best_sl:.2f}"
    md.append(
        f"Testing averaging-in with the optimal stop-loss from Part 1 "
        f"({sl_label}). Initial 50 contracts at entry; add 50 if "
        "price continues down.\n"
    )
    configs = [
        ("A (no avg-in)", StrategyConfig(
            entry_threshold=entry_thr, exit_threshold=exit_thr,
            stop_loss=best_sl,
        )),
        ("B (avg @$0.35)", StrategyConfig(
            entry_threshold=entry_thr, exit_threshold=exit_thr,
            stop_loss=best_sl, avg_in_level=0.35, avg_in_size_pct=0.5,
        )),
        ("C (avg @$0.30)", StrategyConfig(
            entry_threshold=entry_thr, exit_threshold=exit_thr,
            stop_loss=best_sl, avg_in_level=0.30, avg_in_size_pct=0.5,
        )),
    ]
    md.append(
        "| Config | Entries | Avg-in triggered | Mean basis | "
        "Mean P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    for label, cfg in configs:
        outs = replay_all_games(games, meta, cfg)
        s = summarize(outs, n_games)
        if outs:
            avg_in_pct = 100 * sum(1 for o in outs if o.avg_in_triggered) / len(outs)
            mean_basis = float(np.mean([o.effective_cost_basis for o in outs]))
        else:
            avg_in_pct = 0.0
            mean_basis = float("nan")
        avg_in_str = "—" if "no avg-in" in label else f"{avg_in_pct:.1f}%"
        md.append(
            f"| {label} | {s['n']} | {avg_in_str} | "
            f"${mean_basis:.4f} | ${s['mean_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
    md.append("")


def part_3_partial(
    md: list[str], games: list[dict], meta: dict[str, dict],
    entry_thr: float, exit_thr: float, n_games: int,
    best_sl: float | None,
) -> None:
    md.append("## Part 3 — Partial exit simulation\n")
    sl_label = "None" if best_sl is None else f"${best_sl:.2f}"
    md.append(
        f"Optimal stop-loss applied ({sl_label}). Config D = baseline "
        "(100 contracts, one exit at $0.50). Config E = 50c exit at "
        "$0.48, remaining 50c exit at $0.55.\n"
    )
    configs = [
        ("D (no partial)", StrategyConfig(
            entry_threshold=entry_thr, exit_threshold=exit_thr,
            stop_loss=best_sl,
        )),
        ("E (partial @$0.48, full @$0.55)", StrategyConfig(
            entry_threshold=entry_thr, exit_threshold=0.55,
            stop_loss=best_sl, partial_exit_level=0.48,
            partial_exit_pct=0.5,
        )),
    ]
    md.append(
        "| Config | Entries | Partial exits | Full exits | "
        "Mean P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    for label, cfg in configs:
        outs = replay_all_games(games, meta, cfg)
        s = summarize(outs, n_games)
        partials = sum(
            1 for o in outs
            if o.exit_type in ("round_trip_partial", "partial_full")
        )
        full_only = sum(
            1 for o in outs
            if o.exit_type == "round_trip"
        )
        md.append(
            f"| {label} | {s['n']} | {partials} | {full_only} | "
            f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |"
        )
    md.append("")


def part_4_best(
    md: list[str], games: list[dict], meta: dict[str, dict],
    entry_thr: float, exit_thr: float, n_games: int,
    best_sl: float | None, baseline_rows: list[dict],
) -> tuple[StrategyConfig, list[TradeOutcome]]:
    md.append("## Part 4 — Combined best strategy\n")
    md.append(
        "Grid-search over stop-loss × {avg-in off / $0.35 / $0.30} × "
        "{partial off / $0.48}.\n"
    )
    candidates = []
    for sl_opt in (best_sl,):
        for avg_in in (None, 0.35, 0.30):
            for partial in (None, 0.48):
                cfg = StrategyConfig(
                    entry_threshold=entry_thr,
                    exit_threshold=exit_thr if partial is None else 0.55,
                    stop_loss=sl_opt,
                    avg_in_level=avg_in,
                    avg_in_size_pct=0.5 if avg_in is not None else 0.0,
                    partial_exit_level=partial,
                    partial_exit_pct=0.5 if partial is not None else 0.0,
                )
                outs = replay_all_games(games, meta, cfg)
                s = summarize(outs, n_games)
                candidates.append({"cfg": cfg, "outs": outs, "s": s})
    # Pick best by mean pnl
    best = max(candidates, key=lambda c: c["s"]["mean_pnl"])
    c = best["cfg"]
    s = best["s"]
    md.append("### Best configuration found\n")
    md.append(
        f"- Entry: ${c.entry_threshold:.2f} "
        f"({int(TOTAL_CONTRACTS * (1 - c.avg_in_size_pct))} contracts initial)"
    )
    if c.avg_in_level is not None:
        md.append(
            f"- Average-in: ${c.avg_in_level:.2f} "
            f"({int(TOTAL_CONTRACTS * c.avg_in_size_pct)} contracts addon)"
        )
    else:
        md.append("- Average-in: none")
    if c.partial_exit_level is not None:
        md.append(
            f"- Partial exit: ${c.partial_exit_level:.2f} "
            f"({int(c.partial_exit_pct * 100)}% of position)"
        )
    else:
        md.append("- Partial exit: none")
    md.append(f"- Full exit: ${c.exit_threshold:.2f}")
    sl_label = "None" if c.stop_loss is None else f"${c.stop_loss:.2f}"
    md.append(f"- Stop-loss: {sl_label}")
    md.append("")
    md.append(f"**Performance on {n_games} competitive games:**\n")
    md.append(f"- Total entries: {s['n']}")
    md.append(f"- Win rate: {s['win_rate']:.1f}%")
    md.append(f"- Mean P&L per entry: ${s['mean_pnl']:+.2f}")
    md.append(f"- Median P&L per entry: ${s['median_pnl']:+.2f}")
    md.append(
        f"- Annual EV (549 games × entries/game × mean): "
        f"**${s['annual_ev']:+,.0f}**"
    )
    md.append(f"- Max single-entry loss: ${s['max_single_loss']:+.2f}")
    if s["std_pnl"] > 0:
        md.append(
            f"- Sharpe-like ratio: {s['mean_pnl'] / s['std_pnl']:.3f}"
        )
    md.append("")
    baseline = next(r for r in baseline_rows if r["stop_loss"] == "")
    md.append("### Comparison to naive (no stop, no scaling)\n")
    md.append(
        f"- EV improvement: ${s['annual_ev'] - baseline['annual_ev']:+,.0f}/year"
    )
    md.append(
        f"- Max loss: ${baseline['max_single_loss']:+.2f} → "
        f"${s['max_single_loss']:+.2f}"
    )
    md.append("")
    return c, best["outs"]


def part_5_context(
    md: list[str], games: list[dict], meta: dict[str, dict],
    entry_thr: float, exit_thr: float, n_games: int,
    best_sl: float | None,
) -> None:
    md.append("## Part 5 — Stop-loss by game context\n")
    cfg_sl = StrategyConfig(
        entry_threshold=entry_thr, exit_threshold=exit_thr,
        stop_loss=best_sl,
    )
    cfg_no = StrategyConfig(
        entry_threshold=entry_thr, exit_threshold=exit_thr,
        stop_loss=None,
    )
    with_outs = replay_all_games(games, meta, cfg_sl)
    no_outs = replay_all_games(games, meta, cfg_no)

    def _slice(outs, pred):
        return [o for o in outs if pred(o)]

    md.append("### By entry period\n")
    md.append(
        "| Entry Q | Entries | Win rate | Mean P&L (stop) | "
        "Mean P&L (no stop) | Stop helped? |"
    )
    md.append("|---|---:|---:|---:|---:|---|")
    for q_label, pred in (
        ("Q1", lambda o: o.entry_period == 1),
        ("Q2", lambda o: o.entry_period == 2),
        ("Q3", lambda o: o.entry_period == 3),
        ("Q4", lambda o: o.entry_period == 4),
        ("OT", lambda o: o.entry_period is not None and o.entry_period >= 5),
    ):
        w_sub = _slice(with_outs, pred)
        n_sub = _slice(no_outs, pred)
        if not w_sub:
            md.append(f"| {q_label} | 0 | — | — | — | — |")
            continue
        wr = 100 * float(np.mean([o.net_pnl > 0 for o in w_sub]))
        w_mean = float(np.mean([o.net_pnl for o in w_sub]))
        n_mean = float(np.mean([o.net_pnl for o in n_sub])) if n_sub else float("nan")
        helped = "yes" if (not np.isnan(n_mean) and w_mean > n_mean) else "no"
        md.append(
            f"| {q_label} | {len(w_sub)} | {wr:.1f}% | "
            f"${w_mean:+.2f} | ${n_mean:+.2f} | {helped} |"
        )
    md.append("")

    md.append("### By spread bucket\n")
    md.append(
        "| |Spread| | Entries | Win rate | Mean P&L (stop) | "
        "Mean P&L (no stop) | Stop helped? |"
    )
    md.append("|---|---:|---:|---:|---:|---|")
    for label, pred in (
        ("1-2", lambda o: o.abs_spread is not None and 1.0 <= o.abs_spread <= 2.0),
        ("2.5-3.5", lambda o: o.abs_spread is not None and 2.5 <= o.abs_spread <= 3.5),
        ("4-5", lambda o: o.abs_spread is not None and 4.0 <= o.abs_spread <= 5.0),
        ("5.5-6", lambda o: o.abs_spread is not None and 5.5 <= o.abs_spread <= 6.0),
    ):
        w_sub = _slice(with_outs, pred)
        n_sub = _slice(no_outs, pred)
        if not w_sub:
            md.append(f"| {label} | 0 | — | — | — | — |")
            continue
        wr = 100 * float(np.mean([o.net_pnl > 0 for o in w_sub]))
        w_mean = float(np.mean([o.net_pnl for o in w_sub]))
        n_mean = float(np.mean([o.net_pnl for o in n_sub])) if n_sub else float("nan")
        helped = "yes" if (not np.isnan(n_mean) and w_mean > n_mean) else "no"
        md.append(
            f"| {label} | {len(w_sub)} | {wr:.1f}% | "
            f"${w_mean:+.2f} | ${n_mean:+.2f} | {helped} |"
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

    # Count competitive games
    n_games = sum(
        1 for g in games
        if meta.get(g["ticker"]) is not None
        and meta[g["ticker"]]["abs_spread"] is not None
        and meta[g["ticker"]]["abs_spread"] <= MAX_SPREAD_COMPETITIVE
    )
    log(f"Competitive games: {n_games}")

    md: list[str] = []
    md.append("# Strategy 3 — Stop-Loss Sweep & Position Management\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "General-purpose replay engine over 165 competitive Kalshi "
        "games (|spread| ≤ 6). Sweeps stop-loss levels, averaging-in "
        "variants, and partial-exit variants. Identifies the "
        "configuration with highest mean P&L per entry and compares "
        "to the naive (no stop, no scaling) baseline.\n"
    )
    md.append(
        f"**Params:** entry=${args.entry:.2f}, "
        f"exit=${args.exit_:.2f}, "
        f"contracts per entry={TOTAL_CONTRACTS}, maker-maker fees.\n"
    )

    best_sl, sweep_rows = part_1_sweep(
        md, games, meta, args.entry, args.exit_, n_games,
    )
    part_2_avg_in(md, games, meta, args.entry, args.exit_, n_games, best_sl)
    part_3_partial(md, games, meta, args.entry, args.exit_, n_games, best_sl)
    best_cfg, best_outs = part_4_best(
        md, games, meta, args.entry, args.exit_, n_games, best_sl, sweep_rows,
    )
    part_5_context(md, games, meta, args.entry, args.exit_, n_games, best_sl)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md) + "\n")
    log(f"Report → {out_path}")

    # Best-config entries CSV
    pd.DataFrame([asdict(o) for o in best_outs]).to_csv(
        BEST_CONFIG_CSV, index=False,
    )
    log(f"Best-config entries CSV → {BEST_CONFIG_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
