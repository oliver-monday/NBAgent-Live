"""Replay validation — run the paper-trading engine against the Kalshi
paired dataset and verify it reproduces whatever the offline
`analysis.strategy4_dip_recovery::simulate_s4a` produces on the same
dataset. This is an *equivalence* test, not a regression against a
fixed snapshot: the engine must match the authoritative offline logic
trade-for-trade on the current dataset, independent of how many games
have accumulated since STRATEGY4_SPEC.md was written.

For context, the STRATEGY4_SPEC.md snapshot baseline (165-game dataset,
2026-04-21) was 161 entries, 52.8% hit, +$3.53 mean, +$1,886 annual EV.
The dataset grows as the forward-collection cron and full-season
backfill add games, so current-run numbers drift slightly from that
snapshot — that drift is meaningful and interesting; engine-vs-offline
divergence is NOT and indicates a bug.

Tolerances (report FAIL if exceeded):
  - entries:    Δ of 0 (exact match)
  - hit rate:   ±0.1pp
  - mean P&L:   ±$0.01
  - annual EV:  ±$1

Run:
    python -m engine.replay
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    COMP_FRACTION,
    REG_SEASON_GAMES,
    S4AConfig,
    _precompute_trailing_max,
    load_competitive_games,
    simulate_s4a,
    summarize_s4a,
)
from engine.position_manager import PositionManager
from engine.s4a_signal import S4ASignalDetector, Signal


REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
MATCHED_CSV = PAIRED_DIR / "matched_games.csv"

MAX_SPREAD_COMPETITIVE = 6.0

TICKER_RE = re.compile(r"(KXNBAGAME-\d{2}[A-Z]{3}\d{2}[A-Z]{6})")

# STRATEGY4_SPEC.md snapshot (2026-04-21, 165-game dataset). Shown for
# situational context — the PASS/FAIL gate is against the live offline
# re-run, not this snapshot.
SPEC_ENTRIES = 161
SPEC_HIT_PCT = 52.8
SPEC_MEAN_PNL = 3.53
SPEC_ANNUAL_EV = 1886


def log(msg: str) -> None:
    print(msg, flush=True)


def _load_games() -> list[dict]:
    """Delegate to analysis/strategy4_dip_recovery.py so the engine
    replay consumes the same preprocessing the offline sweep uses."""
    return load_competitive_games()


def replay_one(
    game: dict, manager: PositionManager,
) -> None:
    """Drive a single game's timeseries through detector + manager.

    Uses synthetic timestamps (`i * BUCKET_SEC`) so the detector's
    time-windowed trailing max behaves identically to pandas
    rolling(window=6, min_periods=1) used by the offline sweep.
    Bin-to-timestamp identity is key to matching +$1,886/yr — don't
    swap to `game_seconds_elapsed`, which has irregular gaps.
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
        elif action.action in ("close_target", "close_stop", "close_eod"):
            detector.notify_exit()
        last_price = price
        last_ts = ts

    # End-of-game resolution for any still-open position.
    eod = manager.end_of_game(ticker, last_price, last_ts)
    if eod is not None:
        detector.notify_exit()


def _run_offline_ground_truth(games: list[dict]) -> dict:
    """Run the authoritative offline simulator on the same dataset so
    we have a trade-for-trade reference for the engine output."""
    cfg = S4AConfig(
        lookback_sec=180, dip_depth=0.08,
        entry_lo=0.50, entry_hi=0.75,
        exit_target=0.90, stop_loss=0.40,
    )
    lookback_bins = max(1, int(cfg.lookback_sec / BUCKET_SEC))
    precomp: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp[(g["ticker"], lookback_bins)] = (
            _precompute_trailing_max(fav, lookback_bins)
        )
    trades = simulate_s4a(games, cfg, precomp)
    s = summarize_s4a(trades, len(games))
    n_target = s["n_target"]
    n_trades = s["entries"]
    hit_pct = (100.0 * n_target / n_trades) if n_trades else 0.0
    return {
        "entries": n_trades,
        "hit_pct": hit_pct,
        "mean_pnl": s["mean_pnl"],
        "annual_ev": s["annual_ev"],
        "n_target": n_target,
        "n_stop": s["n_stop"],
        "n_eod": s["n_res_win"] + s["n_res_loss"] + s["n_res_mid"],
    }


def main() -> int:
    log("Loading competitive dataset via analysis.load_competitive_games...")
    games = _load_games()
    n_games = len(games)
    log(f"Loaded {n_games} games (|spread| <= {MAX_SPREAD_COMPETITIVE}).")
    if n_games == 0:
        log("FAIL: no games loaded.")
        return 2

    log("Running offline ground-truth simulation...")
    offline = _run_offline_ground_truth(games)

    log("Running engine replay...")
    manager = PositionManager()
    for g in games:
        replay_one(g, manager)
    summary = manager.summary()
    n_entries = summary["entries"]
    total_pnl = summary["total_pnl"]
    mean_pnl = summary["mean_pnl"]
    closes = summary["closes"]
    # Mirror analysis/strategy4_dip_recovery.py::summarize_s4a: hit_pct
    # is n_target divided by total trades (entries), not by non-EOD closes.
    hit_pct = (100.0 * summary["closed_target"] / n_entries) if n_entries else 0.0
    entries_per_game = n_entries / n_games if n_games else 0.0
    annual_ev = mean_pnl * entries_per_game * REG_SEASON_GAMES * COMP_FRACTION

    # ---- Equivalence check: engine vs offline --------------------------

    entries_delta = n_entries - offline["entries"]
    hit_delta = hit_pct - offline["hit_pct"]
    mean_delta = mean_pnl - offline["mean_pnl"]
    annual_delta = annual_ev - offline["annual_ev"]

    entries_ok = entries_delta == 0
    hit_ok = abs(hit_delta) <= 0.1
    mean_ok = abs(mean_delta) <= 0.01
    annual_ok = abs(annual_delta) <= 1.0
    all_ok = entries_ok and hit_ok and mean_ok and annual_ok

    log("")
    log("=== S4A Replay Validation ===")
    log(f"Games replayed:     {n_games}")
    log("")
    log("| Metric          | Engine | Offline | Δ | Spec snapshot |")
    log("|---|---|---|---|---|")
    log(
        f"| Entries         | {n_entries} "
        f"| {offline['entries']} | {entries_delta:+d} "
        f"| {SPEC_ENTRIES} |"
    )
    log(
        f"| Hit rate (%)    | {hit_pct:.2f} "
        f"| {offline['hit_pct']:.2f} | {hit_delta:+.2f} "
        f"| {SPEC_HIT_PCT:.1f} |"
    )
    log(
        f"| Mean P&L ($)    | {mean_pnl:+.4f} "
        f"| {offline['mean_pnl']:+.4f} | {mean_delta:+.4f} "
        f"| {SPEC_MEAN_PNL:+.2f} |"
    )
    log(
        f"| Annual EV ($)   | {annual_ev:+,.2f} "
        f"| {offline['annual_ev']:+,.2f} | {annual_delta:+,.2f} "
        f"| {SPEC_ANNUAL_EV:+,} |"
    )
    log("")
    log(
        "Engine close breakdown: "
        f"target={summary['closed_target']}, "
        f"stop={summary['closed_stop']}, "
        f"eod={summary['closed_eod']}, "
        f"total_pnl=${total_pnl:+,.2f}"
    )
    log(
        "Offline close breakdown: "
        f"target={offline['n_target']}, "
        f"stop={offline['n_stop']}, "
        f"eod={offline['n_eod']}"
    )
    log("")
    log(
        "Tolerances (engine vs offline): "
        "entries Δ=0, hit ±0.1pp, mean ±$0.01, annual ±$1"
    )
    log("")
    log(
        "Spec snapshot (165-game dataset, 2026-04-21) shown for context "
        "only; current dataset may differ as games accumulate."
    )
    log("")
    log(f"RESULT: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
