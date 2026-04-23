"""Replay validation — run the paper-trading engine against the
404-game Kalshi paired dataset. Supports the breakeven ratchet
(STRATEGY4_SPEC §5A) via the `--ratchet` CLI flag.

Two modes, both tested in this single script:

  --ratchet 0.08 (DEFAULT, recommended)
    Expected on the 404-game dataset:
      entries 358, target 149, full stops 88, ratchet stops 121,
      hit 41.6%, mean P&L +$3.92, annual EV +$1,899.
    Matches Part 12 of `docs/analysis_outputs/s3_reframed_extended_entry.md`
    trade-for-trade.

  --ratchet 0 (disable, legacy baseline)
    Expected on the 404-game dataset:
      entries 311, target 179, full stops 132, ratchet stops 0,
      hit 57.6%, mean P&L +$3.13, annual EV +$1,320.

    NOTE: the drawdown analysis
    (`docs/analysis_outputs/strategy4a_drawdown.md`) reported a
    baseline mean of +$2.83 / annual +$1,193 for the same 311
    entries. The $0.30 per-entry gap comes from exit-price
    modeling: the drawdown analysis used the *observed* price
    (which overshoots $0.90 on target ticks), while the engine
    fills at the *target level* (how a resting limit order
    actually fills). The engine's model is more realistic for
    paper-trading and is consistent with Part 12's +$3.92 number.
    The true ratchet incremental under a single consistent model
    is +$1,899 − $1,320 = +$579/yr, not the +$706 Δ the analysis
    reported (which compared target-level ratcheted against
    observed-price baseline).

Both modes use the maker/taker fee split (maker on entry + target +
ratchet_stop, taker on full-stop). No resolution holds — every
S4A entry exits via target, stop, ratchet_stop, or (rarely)
end-of-game at the final VWAP.

Tolerances for PASS/FAIL against the expected numbers above:
  - entries: ±1
  - target/stop/ratchet counts: ±1 each
  - mean P&L: ±$0.02
  - annual EV: ±$10

Run:
    python -m engine.replay                 # ratchet 0.08
    python -m engine.replay --ratchet 0     # baseline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    COMP_FRACTION,
    REG_SEASON_GAMES,
    load_kalshi_games_all_spreads,
)
from engine.position_manager import PositionManager
from engine.s4a_signal import S4ASignalDetector

ANNUAL_SCALE = REG_SEASON_GAMES * COMP_FRACTION  # ≈ 547

# Expected targets (from s3_reframed_extended_entry.md Part 12).
EXPECTED = {
    0.08: {
        "entries": 358, "n_target": 149,
        "n_stop": 88, "n_ratchet_stop": 121,
        "hit_pct": 41.6, "mean_pnl": 3.92, "annual_ev": 1899,
    },
    0.0: {
        # Target-level + maker/taker baseline. Differs from the
        # drawdown analysis's $+2.83 / $+1,193 (observed exit price);
        # see module docstring for the reconciliation.
        "entries": 311, "n_target": 179,
        "n_stop": 132, "n_ratchet_stop": 0,
        "hit_pct": 57.6, "mean_pnl": 3.13, "annual_ev": 1320,
    },
}


def log(msg: str) -> None:
    print(msg, flush=True)


def replay_one(
    game: dict, manager: PositionManager,
) -> None:
    """Drive one game's fav_kalshi_vwap through detector + manager.

    Uses synthetic timestamps (i × BUCKET_SEC) so the detector's
    time-windowed trailing max behaves identically to the offline
    sweep's pandas.rolling(window=6, min_periods=1) on 30s bins.
    """
    detector = S4ASignalDetector()
    ticker = game["ticker"]
    prices = game["ts"]["fav_kalshi_vwap"].tolist()
    if not prices:
        return
    last_price = 0.0
    last_ts = 0.0
    for i, p in enumerate(prices):
        try:
            price = float(p)
        except (TypeError, ValueError):
            continue
        if pd.isna(price):
            continue
        ts = i * BUCKET_SEC
        signal = detector.update(ts, price)
        action = manager.evaluate(ticker, ticker, signal, price, ts)
        if action.action == "open":
            detector.notify_entry()
        elif action.action in (
            "close_target", "close_stop",
            "close_ratchet_stop", "close_eod",
        ):
            detector.notify_exit()
        last_price = price
        last_ts = ts
    # End-of-game: close any still-open position at final price.
    eod = manager.end_of_game(ticker, last_price, last_ts)
    if eod is not None:
        detector.notify_exit()


def _check_tolerance(
    actual: float, expected: float, tol: float,
) -> tuple[bool, float]:
    delta = actual - expected
    return abs(delta) <= tol, delta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ratchet", type=float, default=0.08,
        help="Breakeven ratchet trigger (default 0.08). 0 disables.",
    )
    args = parser.parse_args(argv)

    ratchet = float(args.ratchet) if args.ratchet else 0.0
    ratchet_arg = ratchet if ratchet > 0 else None

    log(
        f"Replay config: ratchet_trigger="
        f"{'None (disabled)' if ratchet_arg is None else f'+${ratchet:.2f}'}"
    )

    log("Loading 404-game Kalshi paired dataset...")
    games = load_kalshi_games_all_spreads()
    n_games = len(games)
    log(f"Loaded {n_games} games.")
    if n_games == 0:
        log("FAIL: no games loaded.")
        return 2

    log("Running engine replay...")
    manager = PositionManager(ratchet_trigger=ratchet_arg)
    for g in games:
        replay_one(g, manager)
    s = manager.summary()

    n_entries = s["entries"]
    n_target = s["closed_target"]
    n_stop = s["closed_stop"]
    n_ratchet_stop = s["closed_ratchet_stop"]
    n_eod = s["closed_eod"]
    total_pnl = s["total_pnl"]
    # Mean P&L per entry (matches summarize_s4a convention).
    mean_pnl = total_pnl / n_entries if n_entries else 0.0
    # Hit % = target / entries (same convention as summarize_s4a).
    hit_pct = (100.0 * n_target / n_entries) if n_entries else 0.0
    entries_per_game = n_entries / n_games if n_games else 0.0
    annual_ev = mean_pnl * entries_per_game * ANNUAL_SCALE

    # Look up expected numbers for this ratchet setting.
    key = 0.08 if ratchet > 0 and abs(ratchet - 0.08) < 1e-9 else (
        0.0 if ratchet == 0.0 else None
    )
    exp = EXPECTED.get(key)

    log("")
    log("=== S4A Replay Validation ===")
    log(f"Dataset:  {n_games} games")
    log(
        f"Ratchet:  "
        f"{'disabled' if ratchet_arg is None else f'+${ratchet:.2f}'}"
    )
    log("")
    if exp is not None:
        log(
            f"| Metric          | Engine | Expected | Δ |"
        )
        log(f"|---|---|---|---|")
        log(
            f"| Entries         | {n_entries} "
            f"| {exp['entries']} | {n_entries - exp['entries']:+d} |"
        )
        log(
            f"| Target exits    | {n_target} "
            f"| {exp['n_target']} | {n_target - exp['n_target']:+d} |"
        )
        log(
            f"| Full stops      | {n_stop} "
            f"| {exp['n_stop']} | {n_stop - exp['n_stop']:+d} |"
        )
        log(
            f"| Ratchet stops   | {n_ratchet_stop} "
            f"| {exp['n_ratchet_stop']} "
            f"| {n_ratchet_stop - exp['n_ratchet_stop']:+d} |"
        )
        log(
            f"| EOD closes      | {n_eod} "
            f"| (varies) | — |"
        )
        log(
            f"| Hit rate (%)    | {hit_pct:.2f} "
            f"| {exp['hit_pct']:.2f} | "
            f"{hit_pct - exp['hit_pct']:+.2f} |"
        )
        log(
            f"| Mean P&L ($)    | {mean_pnl:+.4f} "
            f"| {exp['mean_pnl']:+.2f} | "
            f"{mean_pnl - exp['mean_pnl']:+.4f} |"
        )
        log(
            f"| Annual EV ($)   | {annual_ev:+,.2f} "
            f"| {exp['annual_ev']:+,} | "
            f"{annual_ev - exp['annual_ev']:+,.2f} |"
        )
        entries_ok, _ = _check_tolerance(
            n_entries, exp["entries"], 1,
        )
        mean_ok, mean_delta = _check_tolerance(
            mean_pnl, exp["mean_pnl"], 0.02,
        )
        annual_ok, annual_delta = _check_tolerance(
            annual_ev, exp["annual_ev"], 10.0,
        )
        target_ok, _ = _check_tolerance(
            n_target, exp["n_target"], 1,
        )
        stop_ok, _ = _check_tolerance(n_stop, exp["n_stop"], 1)
        ratchet_ok, _ = _check_tolerance(
            n_ratchet_stop, exp["n_ratchet_stop"], 1,
        )
        all_ok = (
            entries_ok and mean_ok and annual_ok
            and target_ok and stop_ok and ratchet_ok
        )
        log("")
        log(
            f"Tolerances: entries ±1, target/stop/ratchet ±1 each, "
            f"mean ±$0.02, annual ±$10"
        )
        log("")
        log(f"RESULT: {'PASS' if all_ok else 'FAIL'}")
        if s.get("ratchet_events"):
            log(f"Ratchet events fired: {s['ratchet_events']}")
        return 0 if all_ok else 1
    else:
        # No expected table for this ratchet value — just report.
        log(
            f"Entries: {n_entries}, target: {n_target}, "
            f"stop: {n_stop}, ratchet_stop: {n_ratchet_stop}, "
            f"eod: {n_eod}"
        )
        log(
            f"Hit rate: {hit_pct:.2f}%, mean P&L: ${mean_pnl:+.4f}, "
            f"annual EV: ${annual_ev:+,.2f}"
        )
        if s.get("ratchet_events"):
            log(f"Ratchet events fired: {s['ratchet_events']}")
        log("")
        log("No expected table for this ratchet setting — report only.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
