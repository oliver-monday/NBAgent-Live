"""S3 reframed — extended S4A entry range on 404-game dataset.

Tests whether pushing S4A's entry zone downward (from $0.50-$0.75
to $0.35-$0.50) with S4A-style exits (not resolution holds) adds
EV, using the full Kalshi paired dataset. Also retests the
original S3 filter entry at $0.40 with five exit variants, adds
a concurrent-tranche (averaging-down) simulation, and runs a
holdout validation conditional on any config clearing +$300/yr.

Every config is a single coherent state machine: one entry
condition, one target, one stop, end-of-game resolution at final
VWAP with maker fee. Fees: maker on entry + target exit, taker
on stop exit. 100 contracts per tranche. Single entry per game
(Part 3 allows a second tranche ONLY as an add-on to an open
S4A position, not a standalone re-entry).

Run:
    python -m analysis.s3_reframed_extended_entry
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    COMP_FRACTION,
    CONTRACT_SIZE,
    REG_SEASON_GAMES,
    RESOLUTION_LOSS_CUTOFF,
    RESOLUTION_WIN_CUTOFF,
    S4AConfig,
    S4ATrade,
    _precompute_trailing_max,
    load_kalshi_games_all_spreads,
    simulate_s4a,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "s3_reframed_extended_entry.md"
)

ANNUAL_SCALE = REG_SEASON_GAMES * COMP_FRACTION  # ≈ 547

# S4A baseline from STRATEGY4_SPEC §3
S4A_LOOKBACK_SEC = 180
S4A_DIP = 0.08
S4A_CFG_BASE = S4AConfig(
    lookback_sec=S4A_LOOKBACK_SEC, dip_depth=S4A_DIP,
    entry_lo=0.50, entry_hi=0.75,
    exit_target=0.90, stop_loss=0.40,
)

# Part 1 sweep
PART1_ENTRY_ZONES = [
    (0.35, 0.50),
    (0.35, 0.45),
    (0.38, 0.50),
    (0.40, 0.50),
    (0.40, 0.45),
]
PART1_EXIT_TARGETS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 0.90]
PART1_STOPS = [0.20, 0.25, 0.30, 0.34]

# Part 3 add-on sweep
PART3_ADDON_ZONE = (0.35, 0.50)
PART3_ADDON_TARGETS = [0.60, 0.70, 0.80, 0.90]
PART3_ADDON_STOPS = [0.25, 0.30, 0.34]

# Holdout validation
HOLDOUT_SEEDS = [42, 43, 44, 45, 46, 47]
HOLDOUT_TRAIN_FRAC = 270 / 404

# S3 filter constants
S3_WP_LOOKBACK_SEC = 120
S3_WP_DROP_MIN = 0.03
S3_ALLOWED_PERIODS = {1, 2}
S3_ENTRY_PRICE = 0.40


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


def maker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1 - price) * 100) / 100


def taker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.07 * contracts * price * (1 - price) * 100) / 100


def recompute_pnl(
    entry_price: float, exit_type: str, exit_price: float,
    contracts: int = CONTRACT_SIZE,
) -> float:
    """Maker on entry + target, taker on stop. Resolution mid uses
    taker, clean win/loss uses no exit fee."""
    entry_fee = maker_fee(contracts, entry_price)
    if exit_type == "target":
        exit_fee = maker_fee(contracts, exit_price)
    elif exit_type == "stop":
        exit_fee = taker_fee(contracts, exit_price)
    elif exit_type in ("resolution_win", "resolution_loss"):
        exit_fee = 0.0
    else:  # resolution_mid / end_of_game mid price
        exit_fee = maker_fee(contracts, exit_price)
    return (exit_price - entry_price) * contracts - entry_fee - exit_fee


# ---- Shared data prep --------------------------------------------------

@dataclass
class GamePack:
    """Wrapper with everything needed for Part 1-3 simulators."""
    ticker: str
    abs_spread: float
    ts: pd.DataFrame
    fav_series: np.ndarray
    wp_series: np.ndarray       # fav-side ESPN WP
    periods: np.ndarray
    n_ticks: int
    final_fav_vwap: float


def pack_games(games: list[dict]) -> list[GamePack]:
    out: list[GamePack] = []
    for g in games:
        ts = g["ts"]
        fav = ts["fav_kalshi_vwap"].values.astype(float)
        if "fav_wp_espn" in ts.columns:
            wp = ts["fav_wp_espn"].values.astype(float)
        else:
            wp = np.full(len(fav), np.nan)
        periods = (
            ts["period"].values.astype(float)
            if "period" in ts.columns
            else np.full(len(fav), np.nan)
        )
        out.append(GamePack(
            ticker=g["ticker"], abs_spread=g["abs_spread"], ts=ts,
            fav_series=fav, wp_series=wp, periods=periods,
            n_ticks=len(fav), final_fav_vwap=float(fav[-1]),
        ))
    return out


# ---- Part 1: extended entry-zone sweep -------------------------------

@dataclass
class ConfigResult:
    label: str
    entry_lo: float
    entry_hi: float
    exit_target: float
    stop_loss: float
    entries: int
    n_target: int
    n_stop: int
    n_eog: int
    mean_pnl: float
    median_pnl: float
    total_pnl: float
    annual_ev: float
    mean_winner: float = 0.0
    mean_loser: float = 0.0
    max_loss: float = 0.0
    hit_pct: float = 0.0
    trades: list[S4ATrade] = field(default_factory=list)
    pnls: list[float] = field(default_factory=list)


def _simulate_with_recompute(
    games: list[GamePack], precomp: dict, lookback_bins: int,
    entry_lo: float, entry_hi: float,
    exit_target: float, stop_loss: float,
) -> list[tuple[S4ATrade, float]]:
    """Run simulate_s4a with a given config and recompute P&L using
    the maker/taker fee split."""
    cfg = S4AConfig(
        lookback_sec=S4A_LOOKBACK_SEC, dip_depth=S4A_DIP,
        entry_lo=entry_lo, entry_hi=entry_hi,
        exit_target=exit_target, stop_loss=stop_loss,
    )
    # Pass games through as-is (simulate_s4a expects ticker + ts).
    games_arg = [
        {"ticker": g.ticker, "abs_spread": g.abs_spread, "ts": g.ts}
        for g in games
    ]
    trades = simulate_s4a(games_arg, cfg, precomp)
    enriched = []
    for t in trades:
        pnl = recompute_pnl(t.entry_price, t.exit_type, t.exit_price)
        enriched.append((t, pnl))
    return enriched


def _summarize(
    label: str, entry_lo: float, entry_hi: float,
    exit_target: float, stop_loss: float,
    enriched: list[tuple[S4ATrade, float]], n_games: int,
) -> ConfigResult:
    if not enriched:
        return ConfigResult(
            label=label, entry_lo=entry_lo, entry_hi=entry_hi,
            exit_target=exit_target, stop_loss=stop_loss,
            entries=0, n_target=0, n_stop=0, n_eog=0,
            mean_pnl=0.0, median_pnl=0.0, total_pnl=0.0,
            annual_ev=0.0,
        )
    trades = [t for t, _ in enriched]
    pnls = [p for _, p in enriched]
    n = len(pnls)
    n_target = sum(1 for t in trades if t.exit_type == "target")
    n_stop = sum(1 for t in trades if t.exit_type == "stop")
    n_eog = n - n_target - n_stop
    mean_pnl = float(np.mean(pnls))
    median_pnl = float(np.median(pnls))
    total_pnl = float(sum(pnls))
    entries_per_game = n / n_games if n_games else 0.0
    annual_ev = mean_pnl * entries_per_game * ANNUAL_SCALE
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    return ConfigResult(
        label=label, entry_lo=entry_lo, entry_hi=entry_hi,
        exit_target=exit_target, stop_loss=stop_loss,
        entries=n, n_target=n_target, n_stop=n_stop, n_eog=n_eog,
        mean_pnl=mean_pnl, median_pnl=median_pnl,
        total_pnl=total_pnl, annual_ev=annual_ev,
        mean_winner=float(np.mean(wins)) if wins else 0.0,
        mean_loser=float(np.mean(losses)) if losses else 0.0,
        max_loss=float(min(pnls)),
        hit_pct=100 * n_target / n,
        trades=trades, pnls=pnls,
    )


def run_part1(
    games: list[GamePack], precomp: dict,
) -> list[ConfigResult]:
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    results: list[ConfigResult] = []
    for (elo, ehi) in PART1_ENTRY_ZONES:
        for et in PART1_EXIT_TARGETS:
            for sl in PART1_STOPS:
                # Skip impossible configs (stop >= entry_lo would never
                # allow a position to open, stop > exit target is
                # structurally wrong).
                if sl >= elo:
                    continue
                if et <= ehi:
                    continue
                label = f"entry[{elo:.2f},{ehi:.2f}] tgt{et:.2f} stop{sl:.2f}"
                enriched = _simulate_with_recompute(
                    games, precomp, lb_bins, elo, ehi, et, sl,
                )
                results.append(_summarize(
                    label, elo, ehi, et, sl, enriched, len(games),
                ))
    return results


# ---- Part 2: S3 filter on 404 games ----------------------------------

@dataclass
class S3Entry:
    ticker: str
    entry_idx: int
    entry_price: float
    # Trajectory after entry
    series_after: np.ndarray


def _detect_s3_entries(
    games: list[GamePack], apply_filters: bool,
) -> list[S3Entry]:
    """Find first tick where fav_vwap ≤ 0.40 (plus S3 filters if
    apply_filters). One entry per game."""
    lb_bins = max(1, int(S3_WP_LOOKBACK_SEC / BUCKET_SEC))
    out: list[S3Entry] = []
    for g in games:
        for i in range(g.n_ticks):
            p = float(g.fav_series[i])
            if pd.isna(p) or p > S3_ENTRY_PRICE:
                continue
            if apply_filters:
                # Period check
                per = g.periods[i]
                if pd.isna(per) or int(per) not in S3_ALLOWED_PERIODS:
                    continue
                # WP drop check
                prior_idx = i - lb_bins
                if prior_idx < 0:
                    continue
                wp_now = g.wp_series[i]
                wp_past = g.wp_series[prior_idx]
                if pd.isna(wp_now) or pd.isna(wp_past):
                    continue
                if (wp_past - wp_now) < S3_WP_DROP_MIN:
                    continue
            out.append(S3Entry(
                ticker=g.ticker, entry_idx=i, entry_price=p,
                series_after=g.fav_series[i:].copy(),
            ))
            break
    return out


def _s3_exit_variant_pnl(
    entry: S3Entry, variant: str,
) -> tuple[str, float]:
    """Return (exit_type, pnl) under each exit variant."""
    series = entry.series_after
    entry_price = entry.entry_price
    n = len(series)

    def _final_resolution() -> tuple[float, str, float]:
        """Return (resolution_price, exit_type_tag, exit_fee)."""
        last = float(series[-1])
        if last >= RESOLUTION_WIN_CUTOFF:
            return 1.0, "resolution_win", 0.0
        if last <= RESOLUTION_LOSS_CUTOFF:
            return 0.0, "resolution_loss", 0.0
        return last, "resolution_mid", maker_fee(CONTRACT_SIZE, last)

    if variant == "a_s3_original":
        # Stop $0.34, sell 25% at $0.50, hold 75% to resolution.
        # Walk from i=1 onward.
        partial_taken = False
        partial_pnl = 0.0
        entry_fee_100 = maker_fee(CONTRACT_SIZE, entry_price)
        # Allocate entry fee pro-rata when splitting legs
        for i in range(1, n):
            p = float(series[i])
            if pd.isna(p):
                continue
            if not partial_taken and p >= 0.50:
                # Sell 25 contracts at 0.50 (maker)
                half = 25
                fee_in = maker_fee(half, entry_price)
                fee_out = maker_fee(half, 0.50)
                gross = (0.50 - entry_price) * half
                partial_pnl = gross - fee_in - fee_out
                partial_taken = True
                continue
            if p <= 0.34:
                # Stop all remaining contracts at 0.34 (taker)
                remaining = 75 if partial_taken else CONTRACT_SIZE
                fee_in = maker_fee(remaining, entry_price)
                fee_out = taker_fee(remaining, 0.34)
                gross = (0.34 - entry_price) * remaining
                return ("stop", partial_pnl + gross - fee_in - fee_out)
        # No stop triggered — remaining contracts settle at resolution
        remaining = 75 if partial_taken else CONTRACT_SIZE
        res_price, res_tag, res_fee = _final_resolution()
        fee_in = maker_fee(remaining, entry_price)
        gross = (res_price - entry_price) * remaining
        # Tag carries the held-portion outcome so hit_pct can count wins
        tag = (
            "resolution_win" if res_tag == "resolution_win"
            else "resolution_loss" if res_tag == "resolution_loss"
            else "resolution_mid"
        )
        return (tag, partial_pnl + gross - fee_in - res_fee)

    if variant in ("b_s4a", "c_0.70/0.30", "d_0.60/0.30"):
        target, stop = {
            "b_s4a": (0.90, 0.40),
            "c_0.70/0.30": (0.70, 0.30),
            "d_0.60/0.30": (0.60, 0.30),
        }[variant]
        for i in range(1, n):
            p = float(series[i])
            if pd.isna(p):
                continue
            if p >= target:
                return ("target", recompute_pnl(entry_price, "target", target))
            if p <= stop:
                return ("stop", recompute_pnl(entry_price, "stop", stop))
        # End of game — close at final VWAP with maker fee
        final = float(series[-1])
        return (
            "end_of_game",
            recompute_pnl(entry_price, "resolution_mid", final),
        )

    if variant == "e_hold":
        res_price, tag, _ = _final_resolution()
        entry_fee = maker_fee(CONTRACT_SIZE, entry_price)
        if tag == "resolution_mid":
            exit_fee = maker_fee(CONTRACT_SIZE, res_price)
        else:
            exit_fee = 0.0
        pnl = (res_price - entry_price) * CONTRACT_SIZE - entry_fee - exit_fee
        return (tag, pnl)

    raise ValueError(f"Unknown variant {variant}")


S3_VARIANTS = [
    ("a_s3_original", "S3 original (stop 0.34, 25% at 0.50, 75% hold)"),
    ("b_s4a", "S4A-style (target 0.90, stop 0.40)"),
    ("c_0.70/0.30", "target 0.70, stop 0.30"),
    ("d_0.60/0.30", "target 0.60, stop 0.30"),
    ("e_hold", "Hold to resolution (no stop/target)"),
]


def run_part2(
    games: list[GamePack], apply_filters: bool,
) -> dict[str, dict]:
    entries = _detect_s3_entries(games, apply_filters=apply_filters)
    results: dict[str, dict] = {}
    for key, label in S3_VARIANTS:
        pnls: list[float] = []
        exit_counts: Counter = Counter()
        for e in entries:
            exit_type, pnl = _s3_exit_variant_pnl(e, key)
            pnls.append(pnl)
            exit_counts[exit_type] += 1
        n = len(pnls)
        if n == 0:
            results[key] = {
                "label": label, "entries": 0, "mean_pnl": 0.0,
                "median_pnl": 0.0, "annual_ev": 0.0,
                "hit_pct": 0.0, "exits": {},
            }
            continue
        mean_pnl = float(np.mean(pnls))
        median_pnl = float(np.median(pnls))
        entries_per_game = n / len(games)
        annual_ev = mean_pnl * entries_per_game * ANNUAL_SCALE
        # "Hit" is reaching target (for variants b/c/d) OR resolution_win
        # (for variant e and a's hold portion).
        hit_keys = {
            "a_s3_original": {"resolution_win"},  # the held portion won
            "b_s4a": {"target"},
            "c_0.70/0.30": {"target"},
            "d_0.60/0.30": {"target"},
            "e_hold": {"resolution_win"},
        }.get(key, {"target"})
        hits = sum(c for k, c in exit_counts.items() if k in hit_keys)
        hit_pct = 100 * hits / n
        results[key] = {
            "label": label, "entries": n, "mean_pnl": mean_pnl,
            "median_pnl": median_pnl, "annual_ev": annual_ev,
            "hit_pct": hit_pct,
            "exits": dict(exit_counts),
        }
    return results


# ---- Part 3: concurrent add-on tranche -------------------------------

@dataclass
class DualTrancheTrade:
    ticker: str
    # Tranche 1 (S4A standard)
    t1_entry_price: float
    t1_exit_price: float
    t1_exit_type: str
    t1_pnl: float
    # Tranche 2 (add-on)
    t2_entry_price: float | None
    t2_exit_price: float | None
    t2_exit_type: str | None
    t2_pnl: float | None


def _simulate_dual_tranche(
    games: list[GamePack], precomp: dict, lb_bins: int,
    addon_target: float, addon_stop: float,
) -> list[DualTrancheTrade]:
    out: list[DualTrancheTrade] = []
    for g in games:
        prices = g.fav_series
        n = g.n_ticks
        tmax = precomp[(g.ticker, lb_bins)]
        t1_open = False
        t1_entry_idx = -1
        t1_entry_price = 0.0
        t2_open = False
        t2_entry_idx = -1
        t2_entry_price = 0.0
        t1_result: tuple[float, str, float] | None = None  # (exit_price, type, pnl)
        t2_result: tuple[float, str, float] | None = None
        for i in range(n):
            p = float(prices[i])
            if pd.isna(p):
                continue
            # Tranche 1 entry (S4A standard)
            if not t1_open and t1_result is None:
                if (
                    S4A_CFG_BASE.entry_lo <= p <= S4A_CFG_BASE.entry_hi
                    and (float(tmax[i]) - p) >= S4A_CFG_BASE.dip_depth
                ):
                    t1_open = True
                    t1_entry_idx = i
                    t1_entry_price = p
                    continue
            # Tranche 1 exit
            if t1_open:
                if p >= S4A_CFG_BASE.exit_target:
                    pnl = recompute_pnl(
                        t1_entry_price, "target",
                        S4A_CFG_BASE.exit_target,
                    )
                    t1_result = (S4A_CFG_BASE.exit_target, "target", pnl)
                    t1_open = False
                elif p <= S4A_CFG_BASE.stop_loss:
                    pnl = recompute_pnl(
                        t1_entry_price, "stop", S4A_CFG_BASE.stop_loss,
                    )
                    t1_result = (S4A_CFG_BASE.stop_loss, "stop", pnl)
                    t1_open = False
            # Tranche 2 entry (add-on) — only if tranche 1 still open
            if (
                t1_open and not t2_open and t2_result is None
                and PART3_ADDON_ZONE[0] <= p <= PART3_ADDON_ZONE[1]
                and (float(tmax[i]) - p) >= S4A_CFG_BASE.dip_depth
            ):
                t2_open = True
                t2_entry_idx = i
                t2_entry_price = p
                continue
            # Tranche 2 exit
            if t2_open:
                if p >= addon_target:
                    pnl = recompute_pnl(
                        t2_entry_price, "target", addon_target,
                    )
                    t2_result = (addon_target, "target", pnl)
                    t2_open = False
                elif p <= addon_stop:
                    pnl = recompute_pnl(
                        t2_entry_price, "stop", addon_stop,
                    )
                    t2_result = (addon_stop, "stop", pnl)
                    t2_open = False
        # End-of-game: close any open tranche at final price
        final = float(prices[-1])
        if t1_open and t1_result is None:
            pnl = recompute_pnl(
                t1_entry_price, "resolution_mid", final,
            )
            t1_result = (final, "end_of_game", pnl)
        if t2_open and t2_result is None:
            pnl = recompute_pnl(
                t2_entry_price, "resolution_mid", final,
            )
            t2_result = (final, "end_of_game", pnl)
        if t1_result is not None:
            t1_exit_price, t1_type, t1_pnl = t1_result
            if t2_result is not None:
                t2_ep, t2_type, t2_pnl = t2_result
            else:
                t2_ep, t2_type, t2_pnl = None, None, None
            out.append(DualTrancheTrade(
                ticker=g.ticker,
                t1_entry_price=t1_entry_price,
                t1_exit_price=t1_exit_price,
                t1_exit_type=t1_type, t1_pnl=t1_pnl,
                t2_entry_price=t2_entry_price if t2_result else None,
                t2_exit_price=t2_ep, t2_exit_type=t2_type,
                t2_pnl=t2_pnl,
            ))
    return out


def run_part3(
    games: list[GamePack], precomp: dict,
) -> list[dict]:
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    rows: list[dict] = []
    for target in PART3_ADDON_TARGETS:
        for stop in PART3_ADDON_STOPS:
            if stop >= target:
                continue
            trades = _simulate_dual_tranche(
                games, precomp, lb_bins, target, stop,
            )
            t1_pnls = [t.t1_pnl for t in trades]
            n_s4a = len(trades)
            addon_trades = [t for t in trades if t.t2_pnl is not None]
            t2_pnls = [t.t2_pnl for t in addon_trades]
            combined_pnls = [
                t.t1_pnl + (t.t2_pnl or 0.0) for t in trades
            ]
            addon_rate = 100 * len(addon_trades) / n_s4a if n_s4a else 0.0
            n_games = len(games)
            s4a_mean = float(np.mean(t1_pnls)) if t1_pnls else 0.0
            combined_mean = (
                float(np.mean(combined_pnls)) if combined_pnls else 0.0
            )
            t2_mean = float(np.mean(t2_pnls)) if t2_pnls else 0.0
            s4a_annual = s4a_mean * (n_s4a / n_games) * ANNUAL_SCALE
            combined_annual = (
                combined_mean * (n_s4a / n_games) * ANNUAL_SCALE
            )
            t2_annual = (
                t2_mean * (len(addon_trades) / n_games) * ANNUAL_SCALE
            )
            rows.append({
                "target": target, "stop": stop,
                "n_s4a": n_s4a, "n_addon": len(addon_trades),
                "addon_rate": addon_rate,
                "s4a_mean": s4a_mean, "s4a_annual": s4a_annual,
                "addon_mean": t2_mean, "addon_annual": t2_annual,
                "combined_mean": combined_mean,
                "combined_annual": combined_annual,
            })
    return rows


# ---- Part 4: holdout validation --------------------------------------

def _run_with_split(
    games: list[GamePack], precomp: dict, lb_bins: int,
    cfg: ConfigResult, train_idx: np.ndarray, test_idx: np.ndarray,
) -> tuple[float, float]:
    train_games = [games[i] for i in train_idx]
    test_games = [games[i] for i in test_idx]
    # Train results
    enriched_train = _simulate_with_recompute(
        train_games, precomp, lb_bins,
        cfg.entry_lo, cfg.entry_hi, cfg.exit_target, cfg.stop_loss,
    )
    enriched_test = _simulate_with_recompute(
        test_games, precomp, lb_bins,
        cfg.entry_lo, cfg.entry_hi, cfg.exit_target, cfg.stop_loss,
    )
    train_mean = (
        float(np.mean([p for _, p in enriched_train]))
        if enriched_train else 0.0
    )
    test_mean = (
        float(np.mean([p for _, p in enriched_test]))
        if enriched_test else 0.0
    )
    return train_mean, test_mean


def run_part4(
    games: list[GamePack], precomp: dict,
    top_configs: list[ConfigResult],
) -> dict:
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    n = len(games)
    n_train = int(HOLDOUT_TRAIN_FRAC * n)
    out: dict = {"configs": []}
    for cfg in top_configs:
        per_seed: list[dict] = []
        for seed in HOLDOUT_SEEDS:
            rng = np.random.default_rng(seed)
            perm = rng.permutation(n)
            train_idx = perm[:n_train]
            test_idx = perm[n_train:]
            train_mean, test_mean = _run_with_split(
                games, precomp, lb_bins, cfg, train_idx, test_idx,
            )
            per_seed.append({
                "seed": seed,
                "train_mean": train_mean,
                "test_mean": test_mean,
            })
        n_positive_test = sum(
            1 for s in per_seed if s["test_mean"] > 0
        )
        verdict = (
            "VALIDATED" if n_positive_test >= 4
            else "CURVE-FIT"
        )
        out["configs"].append({
            "label": cfg.label,
            "per_seed": per_seed,
            "n_positive_test": n_positive_test,
            "verdict": verdict,
        })
    return out


# ---- Part 7: ratchet + trailing stop on extended entries -------------

# Best entry zone from Part 1
PART7_ENTRY_LO = 0.40
PART7_ENTRY_HI = 0.45
PART7_TARGET = 0.90
PART7_BREAKEVEN_OFFSET = 0.01   # entry + $0.01 ≡ breakeven after fees
PART7_RATCHET_TRIGGERS = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
PART7_RATCHET_INITIAL_STOPS = [0.30, 0.34]
PART7_TRAIL_DISTANCES = [0.08, 0.10, 0.12, 0.15]
PART7_TRAIL_INITIAL_STOPS = [0.30, 0.34]


@dataclass
class ExtendedTrade:
    """One trade from the extended-entry simulator (ratchet or trail)."""
    ticker: str
    entry_idx: int
    entry_price: float
    exit_idx: int
    exit_price: float
    exit_type: str   # target / full_stop / ratchet_stop / trail_stop / end_of_game
    peak_since_entry: float
    pnl: float


def _simulate_extended_with_ratchet(
    games: list[GamePack], precomp: dict, lb_bins: int,
    ratchet_trigger: float, initial_stop: float,
) -> list[ExtendedTrade]:
    """Extended-range simulator with breakeven ratchet.

    Entry at [PART7_ENTRY_LO, PART7_ENTRY_HI] with ≥$0.08 dip.
    Initial stop at entry - initial_stop_delta (abs price threshold).
    Once peak_since_entry − entry_price ≥ ratchet_trigger, stop moves
    to entry_price + PART7_BREAKEVEN_OFFSET. Max 2 entries per game
    (matching simulate_s4a semantics).
    """
    out: list[ExtendedTrade] = []
    for g in games:
        prices = g.fav_series
        tmax = precomp[(g.ticker, lb_bins)]
        n = g.n_ticks
        in_pos = False
        entries_this_game = 0
        MAX_ENT = 2
        entry_idx = 0
        entry_price = 0.0
        peak = 0.0
        current_stop = 0.0
        ratchet_active = False
        i = 0
        while i < n:
            p = float(prices[i])
            if pd.isna(p):
                i += 1
                continue
            if not in_pos:
                if entries_this_game >= MAX_ENT:
                    break
                if (
                    PART7_ENTRY_LO <= p <= PART7_ENTRY_HI
                    and (float(tmax[i]) - p) >= S4A_DIP
                ):
                    in_pos = True
                    entry_idx = i
                    entry_price = p
                    peak = p
                    current_stop = initial_stop  # absolute price
                    ratchet_active = False
                    entries_this_game += 1
                i += 1
                continue
            # In position
            if p > peak:
                peak = p
            # Check ratchet activation
            if not ratchet_active and (peak - entry_price) >= ratchet_trigger:
                ratchet_active = True
                current_stop = max(
                    current_stop, entry_price + PART7_BREAKEVEN_OFFSET,
                )
            # Check exits
            if p >= PART7_TARGET:
                pnl = recompute_pnl(
                    entry_price, "target", PART7_TARGET,
                )
                out.append(ExtendedTrade(
                    ticker=g.ticker, entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=i, exit_price=PART7_TARGET,
                    exit_type="target", peak_since_entry=peak, pnl=pnl,
                ))
                in_pos = False
                i += 1
                continue
            if p <= current_stop:
                if ratchet_active:
                    # Breakeven stop — treat as planned exit (maker)
                    pnl = recompute_pnl(
                        entry_price, "target", current_stop,
                    )
                    exit_type = "ratchet_stop"
                else:
                    pnl = recompute_pnl(
                        entry_price, "stop", current_stop,
                    )
                    exit_type = "full_stop"
                out.append(ExtendedTrade(
                    ticker=g.ticker, entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=i, exit_price=current_stop,
                    exit_type=exit_type, peak_since_entry=peak, pnl=pnl,
                ))
                in_pos = False
                i += 1
                continue
            i += 1
        # End of game with open position → close at final price (maker)
        if in_pos:
            final = float(prices[-1])
            pnl = recompute_pnl(
                entry_price, "resolution_mid", final,
            )
            out.append(ExtendedTrade(
                ticker=g.ticker, entry_idx=entry_idx,
                entry_price=entry_price,
                exit_idx=n - 1, exit_price=final,
                exit_type="end_of_game",
                peak_since_entry=peak, pnl=pnl,
            ))
    return out


def _simulate_extended_with_trail(
    games: list[GamePack], precomp: dict, lb_bins: int,
    trail_distance: float, initial_stop: float,
) -> list[ExtendedTrade]:
    """Extended-range simulator with true trailing stop.

    Trailing stop = max(initial_stop, peak_since_entry - trail_distance).
    Once peak rises enough that trailing > initial, trailing becomes
    binding.
    """
    out: list[ExtendedTrade] = []
    for g in games:
        prices = g.fav_series
        tmax = precomp[(g.ticker, lb_bins)]
        n = g.n_ticks
        in_pos = False
        entries_this_game = 0
        MAX_ENT = 2
        entry_idx = 0
        entry_price = 0.0
        peak = 0.0
        current_stop = 0.0
        trailing_active = False
        i = 0
        while i < n:
            p = float(prices[i])
            if pd.isna(p):
                i += 1
                continue
            if not in_pos:
                if entries_this_game >= MAX_ENT:
                    break
                if (
                    PART7_ENTRY_LO <= p <= PART7_ENTRY_HI
                    and (float(tmax[i]) - p) >= S4A_DIP
                ):
                    in_pos = True
                    entry_idx = i
                    entry_price = p
                    peak = p
                    current_stop = initial_stop
                    trailing_active = False
                    entries_this_game += 1
                i += 1
                continue
            if p > peak:
                peak = p
            new_trail = peak - trail_distance
            if new_trail > current_stop:
                current_stop = new_trail
                trailing_active = True
            if p >= PART7_TARGET:
                pnl = recompute_pnl(entry_price, "target", PART7_TARGET)
                out.append(ExtendedTrade(
                    ticker=g.ticker, entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=i, exit_price=PART7_TARGET,
                    exit_type="target",
                    peak_since_entry=peak, pnl=pnl,
                ))
                in_pos = False
                i += 1
                continue
            if p <= current_stop:
                if trailing_active:
                    pnl = recompute_pnl(
                        entry_price, "target", current_stop,
                    )
                    exit_type = "trail_stop"
                else:
                    pnl = recompute_pnl(
                        entry_price, "stop", current_stop,
                    )
                    exit_type = "full_stop"
                out.append(ExtendedTrade(
                    ticker=g.ticker, entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=i, exit_price=current_stop,
                    exit_type=exit_type,
                    peak_since_entry=peak, pnl=pnl,
                ))
                in_pos = False
                i += 1
                continue
            i += 1
        if in_pos:
            final = float(prices[-1])
            pnl = recompute_pnl(entry_price, "resolution_mid", final)
            out.append(ExtendedTrade(
                ticker=g.ticker, entry_idx=entry_idx,
                entry_price=entry_price,
                exit_idx=n - 1, exit_price=final,
                exit_type="end_of_game",
                peak_since_entry=peak, pnl=pnl,
            ))
    return out


def _summarize_extended(
    label: str, trades: list[ExtendedTrade], n_games: int,
) -> dict:
    if not trades:
        return {
            "label": label, "entries": 0, "n_target": 0,
            "n_full_stop": 0, "n_ratchet_stop": 0,
            "n_trail_stop": 0, "n_end_of_game": 0,
            "hit_pct": 0.0, "mean_pnl": 0.0, "annual_ev": 0.0,
            "max_loss": 0.0,
        }
    exits = Counter(t.exit_type for t in trades)
    pnls = [t.net_pnl if False else t.pnl for t in trades]
    n = len(trades)
    mean_pnl = float(np.mean(pnls))
    annual_ev = mean_pnl * (n / n_games) * ANNUAL_SCALE
    return {
        "label": label, "entries": n,
        "n_target": exits.get("target", 0),
        "n_full_stop": exits.get("full_stop", 0),
        "n_ratchet_stop": exits.get("ratchet_stop", 0),
        "n_trail_stop": exits.get("trail_stop", 0),
        "n_end_of_game": exits.get("end_of_game", 0),
        "hit_pct": 100 * exits.get("target", 0) / n,
        "mean_pnl": mean_pnl,
        "annual_ev": annual_ev,
        "max_loss": float(min(pnls)),
    }


def run_part7(
    games: list[GamePack], precomp: dict,
) -> dict:
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    ratchet_rows: list[dict] = []
    for trigger in PART7_RATCHET_TRIGGERS:
        for istop in PART7_RATCHET_INITIAL_STOPS:
            label = (
                f"ratchet trigger+${trigger:.2f} / initial stop ${istop:.2f}"
            )
            trades = _simulate_extended_with_ratchet(
                games, precomp, lb_bins, trigger, istop,
            )
            row = _summarize_extended(label, trades, len(games))
            row["trigger"] = trigger
            row["initial_stop"] = istop
            row["trades"] = trades
            ratchet_rows.append(row)
    trail_rows: list[dict] = []
    for tdist in PART7_TRAIL_DISTANCES:
        for istop in PART7_TRAIL_INITIAL_STOPS:
            label = (
                f"trail ${tdist:.2f} / initial stop ${istop:.2f}"
            )
            trades = _simulate_extended_with_trail(
                games, precomp, lb_bins, tdist, istop,
            )
            row = _summarize_extended(label, trades, len(games))
            row["trail"] = tdist
            row["initial_stop"] = istop
            row["trades"] = trades
            trail_rows.append(row)
    return {"ratchet": ratchet_rows, "trail": trail_rows}


# ---- Part 8: holdout on add-on + best ratchet ------------------------

def _simulate_dual_tranche_time_gated(
    games: list[GamePack], precomp: dict, lb_bins: int,
    addon_target: float, addon_stop: float,
    time_gate_ticks: int | None = None,
    recovery_threshold: float | None = None,
) -> list[DualTrancheTrade]:
    """Dual-tranche simulator with optional time gate on the add-on.

    If time_gate_ticks is not None and the add-on has been open for
    ≥ time_gate_ticks ticks AND current price < entry + recovery_threshold,
    close the add-on at current price (taker fee).
    """
    out: list[DualTrancheTrade] = []
    for g in games:
        prices = g.fav_series
        n = g.n_ticks
        tmax = precomp[(g.ticker, lb_bins)]
        t1_open = False
        t1_entry_idx = -1
        t1_entry_price = 0.0
        t2_open = False
        t2_entry_idx = -1
        t2_entry_price = 0.0
        t1_result = None
        t2_result = None
        for i in range(n):
            p = float(prices[i])
            if pd.isna(p):
                continue
            # Tranche 1 entry
            if not t1_open and t1_result is None:
                if (
                    S4A_CFG_BASE.entry_lo <= p <= S4A_CFG_BASE.entry_hi
                    and (float(tmax[i]) - p) >= S4A_CFG_BASE.dip_depth
                ):
                    t1_open = True
                    t1_entry_idx = i
                    t1_entry_price = p
                    continue
            # Tranche 1 exits
            if t1_open:
                if p >= S4A_CFG_BASE.exit_target:
                    pnl = recompute_pnl(
                        t1_entry_price, "target",
                        S4A_CFG_BASE.exit_target,
                    )
                    t1_result = (S4A_CFG_BASE.exit_target, "target", pnl)
                    t1_open = False
                elif p <= S4A_CFG_BASE.stop_loss:
                    pnl = recompute_pnl(
                        t1_entry_price, "stop", S4A_CFG_BASE.stop_loss,
                    )
                    t1_result = (S4A_CFG_BASE.stop_loss, "stop", pnl)
                    t1_open = False
            # Tranche 2 entry (only if tranche 1 still open)
            if (
                t1_open and not t2_open and t2_result is None
                and PART3_ADDON_ZONE[0] <= p <= PART3_ADDON_ZONE[1]
                and (float(tmax[i]) - p) >= S4A_CFG_BASE.dip_depth
            ):
                t2_open = True
                t2_entry_idx = i
                t2_entry_price = p
                continue
            # Tranche 2 exits
            if t2_open:
                # Time-gate check (before target/stop) — forced exit
                if (
                    time_gate_ticks is not None
                    and recovery_threshold is not None
                    and (i - t2_entry_idx) >= time_gate_ticks
                    and p < (t2_entry_price + recovery_threshold)
                ):
                    # Forced close at market (taker)
                    pnl = recompute_pnl(t2_entry_price, "stop", p)
                    t2_result = (p, "time_gate", pnl)
                    t2_open = False
                elif p >= addon_target:
                    pnl = recompute_pnl(
                        t2_entry_price, "target", addon_target,
                    )
                    t2_result = (addon_target, "target", pnl)
                    t2_open = False
                elif p <= addon_stop:
                    pnl = recompute_pnl(
                        t2_entry_price, "stop", addon_stop,
                    )
                    t2_result = (addon_stop, "stop", pnl)
                    t2_open = False
        final = float(prices[-1])
        if t1_open and t1_result is None:
            pnl = recompute_pnl(t1_entry_price, "resolution_mid", final)
            t1_result = (final, "end_of_game", pnl)
        if t2_open and t2_result is None:
            pnl = recompute_pnl(t2_entry_price, "resolution_mid", final)
            t2_result = (final, "end_of_game", pnl)
        if t1_result is not None:
            t1_ep, t1_type, t1_pnl = t1_result
            if t2_result is not None:
                t2_ep, t2_type, t2_pnl = t2_result
            else:
                t2_ep, t2_type, t2_pnl = None, None, None
            out.append(DualTrancheTrade(
                ticker=g.ticker,
                t1_entry_price=t1_entry_price,
                t1_exit_price=t1_ep, t1_exit_type=t1_type, t1_pnl=t1_pnl,
                t2_entry_price=t2_entry_price if t2_result else None,
                t2_exit_price=t2_ep, t2_exit_type=t2_type, t2_pnl=t2_pnl,
            ))
    return out


def _addon_standalone_mean(trades: list[DualTrancheTrade]) -> float:
    """Return mean P&L of the add-on tranche only (t2), over add-on
    entries (t2 fired)."""
    addon_pnls = [t.t2_pnl for t in trades if t.t2_pnl is not None]
    return float(np.mean(addon_pnls)) if addon_pnls else 0.0


def run_part8(
    games: list[GamePack], precomp: dict,
    part7_results: dict,
    part1_best: ConfigResult,
) -> dict:
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    n = len(games)
    n_train = int(HOLDOUT_TRAIN_FRAC * n)
    # Part 8A: add-on holdout (target 0.90, stop 0.34)
    addon_per_seed: list[dict] = []
    for seed in HOLDOUT_SEEDS:
        rng = np.random.default_rng(seed)
        perm = rng.permutation(n)
        train_games = [games[i] for i in perm[:n_train]]
        test_games = [games[i] for i in perm[n_train:]]
        train_precomp = {
            (g.ticker, lb_bins): precomp[(g.ticker, lb_bins)]
            for g in train_games
        }
        test_precomp = {
            (g.ticker, lb_bins): precomp[(g.ticker, lb_bins)]
            for g in test_games
        }
        train_trades = _simulate_dual_tranche_time_gated(
            train_games, train_precomp, lb_bins,
            addon_target=0.90, addon_stop=0.34,
        )
        test_trades = _simulate_dual_tranche_time_gated(
            test_games, test_precomp, lb_bins,
            addon_target=0.90, addon_stop=0.34,
        )
        addon_per_seed.append({
            "seed": seed,
            "train_mean": _addon_standalone_mean(train_trades),
            "test_mean": _addon_standalone_mean(test_trades),
            "train_addon_n": sum(
                1 for t in train_trades if t.t2_pnl is not None
            ),
            "test_addon_n": sum(
                1 for t in test_trades if t.t2_pnl is not None
            ),
        })
    addon_n_positive = sum(
        1 for s in addon_per_seed if s["test_mean"] > 0
    )
    addon_verdict = (
        "VALIDATED" if addon_n_positive >= 4 else "CURVE-FIT"
    )

    # Part 8B: best ratchet holdout (if best ratchet beats $561 baseline)
    best_ratchet = max(
        part7_results["ratchet"], key=lambda r: r["annual_ev"],
    )
    baseline_annual = part1_best.annual_ev
    ratchet_per_seed: list[dict] | None = None
    ratchet_verdict: str | None = None
    if best_ratchet["annual_ev"] > baseline_annual:
        ratchet_per_seed = []
        trigger = best_ratchet["trigger"]
        istop = best_ratchet["initial_stop"]
        for seed in HOLDOUT_SEEDS:
            rng = np.random.default_rng(seed)
            perm = rng.permutation(n)
            train_games = [games[i] for i in perm[:n_train]]
            test_games = [games[i] for i in perm[n_train:]]
            train_precomp = {
                (g.ticker, lb_bins): precomp[(g.ticker, lb_bins)]
                for g in train_games
            }
            test_precomp = {
                (g.ticker, lb_bins): precomp[(g.ticker, lb_bins)]
                for g in test_games
            }
            train_trades = _simulate_extended_with_ratchet(
                train_games, train_precomp, lb_bins, trigger, istop,
            )
            test_trades = _simulate_extended_with_ratchet(
                test_games, test_precomp, lb_bins, trigger, istop,
            )
            train_mean = (
                float(np.mean([t.pnl for t in train_trades]))
                if train_trades else 0.0
            )
            test_mean = (
                float(np.mean([t.pnl for t in test_trades]))
                if test_trades else 0.0
            )
            ratchet_per_seed.append({
                "seed": seed,
                "train_mean": train_mean,
                "test_mean": test_mean,
                "train_n": len(train_trades),
                "test_n": len(test_trades),
            })
        n_positive = sum(
            1 for s in ratchet_per_seed if s["test_mean"] > 0
        )
        ratchet_verdict = (
            "VALIDATED" if n_positive >= 4 else "CURVE-FIT"
        )

    return {
        "addon": {
            "per_seed": addon_per_seed,
            "n_positive": addon_n_positive,
            "verdict": addon_verdict,
        },
        "ratchet": (
            {
                "best_ratchet": best_ratchet,
                "per_seed": ratchet_per_seed,
                "verdict": ratchet_verdict,
            }
            if ratchet_per_seed is not None else None
        ),
    }


# ---- Part 9: time-gated add-on --------------------------------------

PART9_TIME_GATES_MIN = [5, 8, 10, 15, 20, 30]   # minutes
PART9_TIME_GATE_TICKS = [m * 2 for m in PART9_TIME_GATES_MIN]
PART9_RECOVERY_THRESHOLDS = [0.05, 0.08, 0.10]


def _summarize_dual(
    trades: list[DualTrancheTrade], n_games: int,
) -> dict:
    n_s4a = len(trades)
    addon_trades = [t for t in trades if t.t2_pnl is not None]
    t1_pnls = [t.t1_pnl for t in trades]
    t2_pnls = [t.t2_pnl for t in addon_trades]
    combined_pnls = [t.t1_pnl + (t.t2_pnl or 0.0) for t in trades]
    t2_exit_counts: Counter = Counter(
        t.t2_exit_type for t in addon_trades
        if t.t2_exit_type is not None
    )
    s4a_mean = float(np.mean(t1_pnls)) if t1_pnls else 0.0
    combined_mean = float(np.mean(combined_pnls)) if combined_pnls else 0.0
    t2_mean = float(np.mean(t2_pnls)) if t2_pnls else 0.0
    s4a_annual = s4a_mean * (n_s4a / n_games) * ANNUAL_SCALE
    combined_annual = combined_mean * (n_s4a / n_games) * ANNUAL_SCALE
    t2_annual = (
        t2_mean * (len(addon_trades) / n_games) * ANNUAL_SCALE
    )
    return {
        "n_s4a": n_s4a, "n_addon": len(addon_trades),
        "s4a_mean": s4a_mean, "s4a_annual": s4a_annual,
        "combined_mean": combined_mean, "combined_annual": combined_annual,
        "addon_mean": t2_mean, "addon_annual": t2_annual,
        "t2_exits": dict(t2_exit_counts),
    }


def run_part9(
    games: list[GamePack], precomp: dict,
) -> list[dict]:
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    rows: list[dict] = []
    for mins, ticks in zip(PART9_TIME_GATES_MIN, PART9_TIME_GATE_TICKS):
        for thr in PART9_RECOVERY_THRESHOLDS:
            trades = _simulate_dual_tranche_time_gated(
                games, precomp, lb_bins,
                addon_target=0.90, addon_stop=0.34,
                time_gate_ticks=ticks, recovery_threshold=thr,
            )
            summary = _summarize_dual(trades, len(games))
            summary["gate_minutes"] = mins
            summary["recovery_threshold"] = thr
            rows.append(summary)
    return rows


# ---- Part 12: S4A standard with ratchet ------------------------------

PART12_RATCHET_TRIGGERS = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
RATCHET_OFFSET = 0.01   # entry + $0.01 ≡ breakeven after maker exit fee


@dataclass
class RatchetTrade:
    ticker: str
    entry_idx: int
    entry_price: float
    exit_idx: int
    exit_price: float
    exit_type: str   # target / full_stop / ratchet_stop / end_of_game
    peak_since_entry: float
    pnl: float
    is_reentry: bool = False


def _simulate_s4a_with_ratchet(
    games: list[GamePack], precomp: dict, lb_bins: int,
    ratchet_trigger: float,
) -> list[RatchetTrade]:
    """S4A standard (entry $0.50-$0.75, target $0.90, initial stop
    $0.40) with a breakeven ratchet. Once price rises ≥ ratchet_trigger
    above entry, stop moves to entry + RATCHET_OFFSET. Max 2 entries
    per game (consistent with simulate_s4a)."""
    out: list[RatchetTrade] = []
    for g in games:
        prices = g.fav_series
        tmax = precomp[(g.ticker, lb_bins)]
        n = g.n_ticks
        in_pos = False
        entries_this_game = 0
        MAX_ENT = 2
        entry_idx = 0
        entry_price = 0.0
        peak = 0.0
        current_stop = S4A_CFG_BASE.stop_loss
        ratchet_active = False
        i = 0
        while i < n:
            p = float(prices[i])
            if pd.isna(p):
                i += 1
                continue
            if not in_pos:
                if entries_this_game >= MAX_ENT:
                    break
                if (
                    S4A_CFG_BASE.entry_lo <= p <= S4A_CFG_BASE.entry_hi
                    and (float(tmax[i]) - p) >= S4A_CFG_BASE.dip_depth
                ):
                    in_pos = True
                    entry_idx = i
                    entry_price = p
                    peak = p
                    current_stop = S4A_CFG_BASE.stop_loss
                    ratchet_active = False
                    entries_this_game += 1
                i += 1
                continue
            if p > peak:
                peak = p
            if not ratchet_active and (peak - entry_price) >= ratchet_trigger:
                ratchet_active = True
                current_stop = max(
                    current_stop, entry_price + RATCHET_OFFSET,
                )
            if p >= S4A_CFG_BASE.exit_target:
                pnl = recompute_pnl(
                    entry_price, "target", S4A_CFG_BASE.exit_target,
                )
                out.append(RatchetTrade(
                    ticker=g.ticker, entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=i, exit_price=S4A_CFG_BASE.exit_target,
                    exit_type="target", peak_since_entry=peak, pnl=pnl,
                    is_reentry=(entries_this_game > 1),
                ))
                in_pos = False
                i += 1
                continue
            if p <= current_stop:
                if ratchet_active:
                    pnl = recompute_pnl(
                        entry_price, "target", current_stop,
                    )
                    exit_type = "ratchet_stop"
                else:
                    pnl = recompute_pnl(
                        entry_price, "stop", current_stop,
                    )
                    exit_type = "full_stop"
                out.append(RatchetTrade(
                    ticker=g.ticker, entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=i, exit_price=current_stop,
                    exit_type=exit_type,
                    peak_since_entry=peak, pnl=pnl,
                    is_reentry=(entries_this_game > 1),
                ))
                in_pos = False
                i += 1
                continue
            i += 1
        if in_pos:
            final = float(prices[-1])
            pnl = recompute_pnl(entry_price, "resolution_mid", final)
            out.append(RatchetTrade(
                ticker=g.ticker, entry_idx=entry_idx,
                entry_price=entry_price,
                exit_idx=n - 1, exit_price=final,
                exit_type="end_of_game",
                peak_since_entry=peak, pnl=pnl,
                is_reentry=(entries_this_game > 1),
            ))
    return out


def _summarize_ratchet_trades(
    trades: list[RatchetTrade], n_games: int,
) -> dict:
    if not trades:
        return {
            "entries": 0, "n_target": 0, "n_full_stop": 0,
            "n_ratchet_stop": 0, "n_end_of_game": 0,
            "hit_pct": 0.0, "ratchet_pct": 0.0,
            "mean_pnl": 0.0, "annual_ev": 0.0, "max_loss": 0.0,
        }
    exits = Counter(t.exit_type for t in trades)
    pnls = [t.pnl for t in trades]
    n = len(trades)
    n_target = exits.get("target", 0)
    n_ratchet = exits.get("ratchet_stop", 0)
    return {
        "entries": n,
        "n_target": n_target,
        "n_full_stop": exits.get("full_stop", 0),
        "n_ratchet_stop": n_ratchet,
        "n_end_of_game": exits.get("end_of_game", 0),
        "hit_pct": 100 * n_target / n,
        "ratchet_pct": 100 * n_ratchet / n,
        "mean_pnl": float(np.mean(pnls)),
        "annual_ev": float(np.mean(pnls)) * (n / n_games) * ANNUAL_SCALE,
        "max_loss": float(min(pnls)),
    }


def run_part12(
    games: list[GamePack], precomp: dict,
) -> list[dict]:
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    rows: list[dict] = []
    for trigger in PART12_RATCHET_TRIGGERS:
        trades = _simulate_s4a_with_ratchet(
            games, precomp, lb_bins, trigger,
        )
        row = _summarize_ratchet_trades(trades, len(games))
        row["trigger"] = trigger
        row["label"] = f"S4A+ratchet+${trigger:.2f}"
        row["trades"] = trades
        rows.append(row)
    return rows


# ---- Parts 13-14: dual-tranche with optional ratchet per tranche -----

def _simulate_dual_tranche_ratcheted(
    games: list[GamePack], precomp: dict, lb_bins: int,
    addon_target: float = 0.90, addon_stop: float = 0.34,
    s4a_ratchet_trigger: float | None = None,
    addon_ratchet_trigger: float | None = None,
) -> list[DualTrancheTrade]:
    """Dual-tranche simulator with optional per-tranche breakeven
    ratchet. Single S4A entry per game (no re-entry). Add-on fires
    only while S4A remains open."""
    out: list[DualTrancheTrade] = []
    for g in games:
        prices = g.fav_series
        n = g.n_ticks
        tmax = precomp[(g.ticker, lb_bins)]
        # S4A tranche state
        t1_open = False
        t1_done = False
        t1_entry_idx = -1
        t1_entry_price = 0.0
        t1_peak = 0.0
        t1_stop = S4A_CFG_BASE.stop_loss
        t1_ratchet_active = False
        t1_result: tuple[float, str, float] | None = None
        # Add-on tranche state
        t2_open = False
        t2_done = False
        t2_entry_idx = -1
        t2_entry_price = 0.0
        t2_peak = 0.0
        t2_stop = addon_stop
        t2_ratchet_active = False
        t2_result: tuple[float, str, float] | None = None
        for i in range(n):
            p = float(prices[i])
            if pd.isna(p):
                continue
            # ---- S4A tranche entry ----
            if not t1_open and not t1_done:
                if (
                    S4A_CFG_BASE.entry_lo <= p <= S4A_CFG_BASE.entry_hi
                    and (float(tmax[i]) - p) >= S4A_CFG_BASE.dip_depth
                ):
                    t1_open = True
                    t1_entry_idx = i
                    t1_entry_price = p
                    t1_peak = p
                    t1_stop = S4A_CFG_BASE.stop_loss
                    t1_ratchet_active = False
                    continue
            # ---- S4A tranche exits ----
            if t1_open:
                if p > t1_peak:
                    t1_peak = p
                if (
                    s4a_ratchet_trigger is not None
                    and not t1_ratchet_active
                    and (t1_peak - t1_entry_price) >= s4a_ratchet_trigger
                ):
                    t1_ratchet_active = True
                    t1_stop = max(
                        t1_stop, t1_entry_price + RATCHET_OFFSET,
                    )
                if p >= S4A_CFG_BASE.exit_target:
                    pnl = recompute_pnl(
                        t1_entry_price, "target",
                        S4A_CFG_BASE.exit_target,
                    )
                    t1_result = (
                        S4A_CFG_BASE.exit_target, "target", pnl,
                    )
                    t1_open = False
                    t1_done = True
                elif p <= t1_stop:
                    if t1_ratchet_active:
                        pnl = recompute_pnl(
                            t1_entry_price, "target", t1_stop,
                        )
                        t1_result = (t1_stop, "ratchet_stop", pnl)
                    else:
                        pnl = recompute_pnl(
                            t1_entry_price, "stop", t1_stop,
                        )
                        t1_result = (t1_stop, "stop", pnl)
                    t1_open = False
                    t1_done = True
            # ---- Add-on tranche entry ----
            # Requires S4A still open AND price in add-on zone AND dip
            if (
                t1_open and not t2_open and not t2_done
                and PART3_ADDON_ZONE[0] <= p <= PART3_ADDON_ZONE[1]
                and (float(tmax[i]) - p) >= S4A_CFG_BASE.dip_depth
            ):
                t2_open = True
                t2_entry_idx = i
                t2_entry_price = p
                t2_peak = p
                t2_stop = addon_stop
                t2_ratchet_active = False
                continue
            # ---- Add-on tranche exits ----
            if t2_open:
                if p > t2_peak:
                    t2_peak = p
                if (
                    addon_ratchet_trigger is not None
                    and not t2_ratchet_active
                    and (t2_peak - t2_entry_price) >= addon_ratchet_trigger
                ):
                    t2_ratchet_active = True
                    t2_stop = max(
                        t2_stop, t2_entry_price + RATCHET_OFFSET,
                    )
                if p >= addon_target:
                    pnl = recompute_pnl(
                        t2_entry_price, "target", addon_target,
                    )
                    t2_result = (addon_target, "target", pnl)
                    t2_open = False
                    t2_done = True
                elif p <= t2_stop:
                    if t2_ratchet_active:
                        pnl = recompute_pnl(
                            t2_entry_price, "target", t2_stop,
                        )
                        t2_result = (t2_stop, "ratchet_stop", pnl)
                    else:
                        pnl = recompute_pnl(
                            t2_entry_price, "stop", t2_stop,
                        )
                        t2_result = (t2_stop, "stop", pnl)
                    t2_open = False
                    t2_done = True
        # End-of-game close
        final = float(prices[-1])
        if t1_open and t1_result is None:
            pnl = recompute_pnl(t1_entry_price, "resolution_mid", final)
            t1_result = (final, "end_of_game", pnl)
        if t2_open and t2_result is None:
            pnl = recompute_pnl(t2_entry_price, "resolution_mid", final)
            t2_result = (final, "end_of_game", pnl)
        if t1_result is not None:
            t1_ep, t1_type, t1_pnl = t1_result
            if t2_result is not None:
                t2_ep, t2_type, t2_pnl = t2_result
            else:
                t2_ep, t2_type, t2_pnl = None, None, None
            out.append(DualTrancheTrade(
                ticker=g.ticker,
                t1_entry_price=t1_entry_price,
                t1_exit_price=t1_ep, t1_exit_type=t1_type, t1_pnl=t1_pnl,
                t2_entry_price=t2_entry_price if t2_result else None,
                t2_exit_price=t2_ep, t2_exit_type=t2_type, t2_pnl=t2_pnl,
            ))
    return out


def _summarize_dual_ratcheted(
    trades: list[DualTrancheTrade], n_games: int,
) -> dict:
    n_s4a = len(trades)
    addon_trades = [t for t in trades if t.t2_pnl is not None]
    t1_pnls = [t.t1_pnl for t in trades]
    t2_pnls = [t.t2_pnl for t in addon_trades]
    combined_pnls = [t.t1_pnl + (t.t2_pnl or 0.0) for t in trades]
    t1_exits = Counter(t.t1_exit_type for t in trades)
    t2_exits = Counter(
        t.t2_exit_type for t in addon_trades if t.t2_exit_type
    )
    if not t1_pnls:
        return {
            "n_s4a": 0, "n_addon": 0,
            "s4a_mean": 0.0, "s4a_annual": 0.0,
            "addon_mean": 0.0, "addon_annual": 0.0,
            "combined_mean": 0.0, "combined_annual": 0.0,
            "t1_exits": {}, "t2_exits": {},
        }
    s4a_mean = float(np.mean(t1_pnls))
    combined_mean = float(np.mean(combined_pnls))
    t2_mean = float(np.mean(t2_pnls)) if t2_pnls else 0.0
    s4a_annual = s4a_mean * (n_s4a / n_games) * ANNUAL_SCALE
    combined_annual = combined_mean * (n_s4a / n_games) * ANNUAL_SCALE
    t2_annual = (
        t2_mean * (len(addon_trades) / n_games) * ANNUAL_SCALE
    )
    return {
        "n_s4a": n_s4a, "n_addon": len(addon_trades),
        "s4a_mean": s4a_mean, "s4a_annual": s4a_annual,
        "addon_mean": t2_mean, "addon_annual": t2_annual,
        "combined_mean": combined_mean,
        "combined_annual": combined_annual,
        "t1_exits": dict(t1_exits), "t2_exits": dict(t2_exits),
    }


def run_part13(
    games: list[GamePack], precomp: dict,
) -> list[dict]:
    """S4A (no ratchet) + add-on with ratchet sweep."""
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    rows: list[dict] = []
    for trigger in PART12_RATCHET_TRIGGERS:
        trades = _simulate_dual_tranche_ratcheted(
            games, precomp, lb_bins,
            s4a_ratchet_trigger=None,
            addon_ratchet_trigger=trigger,
        )
        summary = _summarize_dual_ratcheted(trades, len(games))
        summary["trigger"] = trigger
        summary["label"] = f"addon+ratchet+${trigger:.2f}"
        rows.append(summary)
    return rows


def run_part14(
    games: list[GamePack], precomp: dict,
    part12_rows: list[dict], part13_rows: list[dict],
) -> list[dict]:
    """Full stack: both tranches ratcheted. Cartesian top-3 × top-3."""
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    top3_s4a = sorted(
        part12_rows, key=lambda r: -r["annual_ev"],
    )[:3]
    top3_addon = sorted(
        part13_rows, key=lambda r: -r["combined_annual"],
    )[:3]
    rows: list[dict] = []
    seen_pairs: set[tuple[float, float]] = set()
    for s4a_row in top3_s4a:
        for addon_row in top3_addon:
            s_trig = s4a_row["trigger"]
            a_trig = addon_row["trigger"]
            if (s_trig, a_trig) in seen_pairs:
                continue
            seen_pairs.add((s_trig, a_trig))
            trades = _simulate_dual_tranche_ratcheted(
                games, precomp, lb_bins,
                s4a_ratchet_trigger=s_trig,
                addon_ratchet_trigger=a_trig,
            )
            summary = _summarize_dual_ratcheted(trades, len(games))
            summary["s4a_trigger"] = s_trig
            summary["addon_trigger"] = a_trig
            summary["label"] = (
                f"S4A+${s_trig:.2f}/addon+${a_trig:.2f}"
            )
            rows.append(summary)
    # Also explicitly include same-trigger configs if both parts
    # picked the same best value (edge case: top-3 might not overlap).
    best_s4a_trig = top3_s4a[0]["trigger"]
    best_addon_trig = top3_addon[0]["trigger"]
    if (best_s4a_trig, best_addon_trig) not in seen_pairs:
        trades = _simulate_dual_tranche_ratcheted(
            games, precomp, lb_bins,
            s4a_ratchet_trigger=best_s4a_trig,
            addon_ratchet_trigger=best_addon_trig,
        )
        summary = _summarize_dual_ratcheted(trades, len(games))
        summary["s4a_trigger"] = best_s4a_trig
        summary["addon_trigger"] = best_addon_trig
        summary["label"] = (
            f"S4A+${best_s4a_trig:.2f}/addon+${best_addon_trig:.2f} (best/best)"
        )
        rows.append(summary)
    return rows


# ---- Part 15 holdout helpers ---------------------------------------

def _holdout_s4a_ratchet(
    games: list[GamePack], precomp: dict, lb_bins: int,
    trigger: float,
) -> list[dict]:
    """6-seed holdout for S4A-with-ratchet standalone."""
    n = len(games)
    n_train = int(HOLDOUT_TRAIN_FRAC * n)
    per_seed: list[dict] = []
    for seed in HOLDOUT_SEEDS:
        rng = np.random.default_rng(seed)
        perm = rng.permutation(n)
        train_g = [games[i] for i in perm[:n_train]]
        test_g = [games[i] for i in perm[n_train:]]
        train_pc = {
            (g.ticker, lb_bins): precomp[(g.ticker, lb_bins)]
            for g in train_g
        }
        test_pc = {
            (g.ticker, lb_bins): precomp[(g.ticker, lb_bins)]
            for g in test_g
        }
        train_trades = _simulate_s4a_with_ratchet(
            train_g, train_pc, lb_bins, trigger,
        )
        test_trades = _simulate_s4a_with_ratchet(
            test_g, test_pc, lb_bins, trigger,
        )
        train_mean = (
            float(np.mean([t.pnl for t in train_trades]))
            if train_trades else 0.0
        )
        test_mean = (
            float(np.mean([t.pnl for t in test_trades]))
            if test_trades else 0.0
        )
        per_seed.append({
            "seed": seed,
            "train_n": len(train_trades), "test_n": len(test_trades),
            "train_mean": train_mean, "test_mean": test_mean,
        })
    return per_seed


def _holdout_dual_ratchet(
    games: list[GamePack], precomp: dict, lb_bins: int,
    s4a_trigger: float | None, addon_trigger: float | None,
) -> list[dict]:
    """6-seed holdout for dual-tranche with given triggers."""
    n = len(games)
    n_train = int(HOLDOUT_TRAIN_FRAC * n)
    per_seed: list[dict] = []
    for seed in HOLDOUT_SEEDS:
        rng = np.random.default_rng(seed)
        perm = rng.permutation(n)
        train_g = [games[i] for i in perm[:n_train]]
        test_g = [games[i] for i in perm[n_train:]]
        train_pc = {
            (g.ticker, lb_bins): precomp[(g.ticker, lb_bins)]
            for g in train_g
        }
        test_pc = {
            (g.ticker, lb_bins): precomp[(g.ticker, lb_bins)]
            for g in test_g
        }
        train_trades = _simulate_dual_tranche_ratcheted(
            train_g, train_pc, lb_bins,
            s4a_ratchet_trigger=s4a_trigger,
            addon_ratchet_trigger=addon_trigger,
        )
        test_trades = _simulate_dual_tranche_ratcheted(
            test_g, test_pc, lb_bins,
            s4a_ratchet_trigger=s4a_trigger,
            addon_ratchet_trigger=addon_trigger,
        )
        train_combined = [
            t.t1_pnl + (t.t2_pnl or 0.0) for t in train_trades
        ]
        test_combined = [
            t.t1_pnl + (t.t2_pnl or 0.0) for t in test_trades
        ]
        per_seed.append({
            "seed": seed,
            "train_n": len(train_trades), "test_n": len(test_trades),
            "train_mean": (
                float(np.mean(train_combined)) if train_combined else 0.0
            ),
            "test_mean": (
                float(np.mean(test_combined)) if test_combined else 0.0
            ),
        })
    return per_seed


def run_part15(
    games: list[GamePack], precomp: dict,
    part12_rows: list[dict], part13_rows: list[dict],
    part14_rows: list[dict],
    s4a_baseline_annual: float,
) -> dict:
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    # Find the best config across Parts 12-14 by combined annual EV
    best_p12 = max(part12_rows, key=lambda r: r["annual_ev"])
    best_p13 = max(part13_rows, key=lambda r: r["combined_annual"])
    best_p14 = (
        max(part14_rows, key=lambda r: r["combined_annual"])
        if part14_rows else None
    )
    # Select the single highest combined annual EV across Part 13 and
    # Part 14 (since Part 12 is standalone S4A, not combined).
    dual_candidates = [
        ("part13_addon_only", best_p13, best_p13["combined_annual"]),
    ]
    if best_p14 is not None:
        dual_candidates.append(
            ("part14_full_stack", best_p14,
             best_p14["combined_annual"])
        )
    top_dual_key, top_dual_row, top_dual_annual = max(
        dual_candidates, key=lambda x: x[2],
    )
    dual_holdout = _holdout_dual_ratchet(
        games, precomp, lb_bins,
        s4a_trigger=top_dual_row.get("s4a_trigger"),
        addon_trigger=top_dual_row.get(
            "addon_trigger", top_dual_row.get("trigger"),
        ),
    )
    dual_positive = sum(1 for s in dual_holdout if s["test_mean"] > 0)
    dual_verdict = "VALIDATED" if dual_positive >= 4 else "CURVE-FIT"

    # S4A with ratchet: run holdout if it beats S4A no-ratchet baseline
    s4a_holdout: list[dict] | None = None
    s4a_verdict: str | None = None
    s4a_positive: int | None = None
    if best_p12["annual_ev"] > s4a_baseline_annual + 50:
        s4a_holdout = _holdout_s4a_ratchet(
            games, precomp, lb_bins, best_p12["trigger"],
        )
        s4a_positive = sum(1 for s in s4a_holdout if s["test_mean"] > 0)
        s4a_verdict = "VALIDATED" if s4a_positive >= 4 else "CURVE-FIT"

    return {
        "top_dual_key": top_dual_key,
        "top_dual_row": top_dual_row,
        "top_dual_annual": top_dual_annual,
        "dual_holdout": dual_holdout,
        "dual_positive": dual_positive,
        "dual_verdict": dual_verdict,
        "best_p12": best_p12,
        "s4a_holdout": s4a_holdout,
        "s4a_positive": s4a_positive,
        "s4a_verdict": s4a_verdict,
    }


# ---- Report rendering -------------------------------------------------

def render_report(
    n_games: int,
    part1_results: list[ConfigResult],
    part2_filtered: dict, part2_unfiltered: dict,
    part3_rows: list[dict], s4a_baseline_only: dict,
    part4_info: dict | None,
    s4a_baseline_cfg_result: ConfigResult,
    best_extended: ConfigResult,
    best_part2_filtered_key: str,
    best_part3_row: dict | None,
    verdict: str, verdict_detail: str,
    part7_results: dict | None = None,
    part8_results: dict | None = None,
    part9_rows: list[dict] | None = None,
    best_ratchet_row: dict | None = None,
    best_trail_row: dict | None = None,
    best_time_gate_row: dict | None = None,
    part11_verdict: str | None = None,
    part11_detail: str | None = None,
    part12_rows: list[dict] | None = None,
    part13_rows: list[dict] | None = None,
    part14_rows: list[dict] | None = None,
    part15_results: dict | None = None,
    final_verdict: str | None = None,
    final_detail: str | None = None,
) -> str:
    md: list[str] = []
    md.append("# S3 Reframed — Extended S4A Entry Range\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Full 404-game Kalshi paired dataset ({n_games} games). "
        "Tests whether pushing S4A's entry range downward "
        "($0.35-$0.50) with S4A-style exits adds EV, plus retests "
        "the original S3 filter with five exit variants and a "
        "concurrent-tranche (averaging-down) simulation.\n"
    )
    md.append(
        "\n**Fee model:** maker on entry + target exit, taker on "
        "stop exit. 100 contracts per tranche. No resolution hold "
        "except where explicitly called out (Part 2 variants a/e). "
        "End-of-game closes at final VWAP with maker fee.\n"
    )
    md.append(
        f"\n**Annualization:** mean P&L × entries/game × "
        f"{REG_SEASON_GAMES} × {COMP_FRACTION:.3f} ≈ "
        f"{ANNUAL_SCALE:.0f} effective entries/season.\n"
    )

    # ---- Part 1 ----
    md.append(
        "\n## Part 1 — Extended entry range × exit-target sweep\n"
    )
    md.append(
        f"{len(part1_results)} configs tested. Sweep: entry zones "
        f"× {len(PART1_EXIT_TARGETS)} targets × {len(PART1_STOPS)} "
        "stops. Skipped cells where stop ≥ entry_lo or target ≤ "
        "entry_hi (structurally invalid).\n\n"
    )
    positive = sum(1 for r in part1_results if r.annual_ev > 0)
    md.append(
        f"Positive EV configs: **{positive} of "
        f"{len(part1_results)}** "
        f"({100 * positive / max(1, len(part1_results)):.1f}%).\n\n"
    )
    # Table 1: top 20 by annual EV
    md.append("### Table 1 — Top 20 by annual EV\n\n")
    md.append(
        "| # | Config | Entries | Hit % | Mean P&L | Annual EV |\n"
        "|---:|---|---:|---:|---:|---:|\n"
    )
    sorted_p1 = sorted(part1_results, key=lambda r: -r.annual_ev)
    for i, r in enumerate(sorted_p1[:20], 1):
        md.append(
            f"| {i} | {r.label} | {r.entries} | "
            f"{r.hit_pct:.1f}% | ${r.mean_pnl:+.2f} | "
            f"${r.annual_ev:+,.0f} |\n"
        )
    # Table 1A: top 10 detail
    md.append("\n### Table 1A — Top 10 detail\n\n")
    md.append(
        "| # | Config | Entries | Target | Stop | EOG | Hit % | Mean P&L | Median P&L | Mean winner | Mean loser | Max loss |\n"
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for i, r in enumerate(sorted_p1[:10], 1):
        md.append(
            f"| {i} | {r.label} | {r.entries} | "
            f"{r.n_target} | {r.n_stop} | {r.n_eog} | "
            f"{r.hit_pct:.1f}% | ${r.mean_pnl:+.2f} | "
            f"${r.median_pnl:+.2f} | ${r.mean_winner:+.2f} | "
            f"${r.mean_loser:+.2f} | ${r.max_loss:+.2f} |\n"
        )

    # ---- Part 2 ----
    md.append("\n## Part 2 — S3 filter on 404 games, five exit variants\n")
    md.append(
        "**S3 filter:** fav Kalshi VWAP ≤ $0.40, Q1/Q2, ESPN WP "
        f"dropped ≥ {S3_WP_DROP_MIN*100:.0f}pp in last "
        f"{S3_WP_LOOKBACK_SEC}s. First qualifying tick per game is "
        "the entry. 100 contracts.\n"
    )
    md.append("\n### Table 2 — Filtered (full S3 filter)\n\n")
    md.append(
        "| Variant | Entries | Mean P&L | Median P&L | Hit % | Annual EV |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    for key, label in S3_VARIANTS:
        s = part2_filtered[key]
        md.append(
            f"| {label} | {s['entries']} | "
            f"${s['mean_pnl']:+.2f} | ${s['median_pnl']:+.2f} | "
            f"{s['hit_pct']:.1f}% | ${s['annual_ev']:+,.0f} |\n"
        )
    md.append("\n### Table 2B — Unfiltered (fav VWAP ≤ $0.40 only)\n\n")
    md.append(
        "| Variant | Entries | Mean P&L | Median P&L | Hit % | Annual EV |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    for key, label in S3_VARIANTS:
        s = part2_unfiltered[key]
        md.append(
            f"| {label} | {s['entries']} | "
            f"${s['mean_pnl']:+.2f} | ${s['median_pnl']:+.2f} | "
            f"{s['hit_pct']:.1f}% | ${s['annual_ev']:+,.0f} |\n"
        )

    # ---- Part 3 ----
    md.append(
        "\n## Part 3 — Concurrent tranche: S4A + add-on at $0.35-$0.50\n"
    )
    md.append(
        "S4A standard tranche opens first (entry $0.50-$0.75, exit "
        "$0.90, stop $0.40). If S4A remains open AND fav drops into "
        "$0.35-$0.50 with a ≥$0.08 dip from trailing 180s max, a "
        "second 100-contract tranche opens with its own independent "
        "target/stop.\n\n"
    )
    md.append("### Table 3 — Add-on configs (standalone add-on EV)\n\n")
    md.append(
        "| Target | Stop | S4A entries | Add-on entries | Add-on fire % | Add-on mean P&L | Add-on annual EV |\n"
        "|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for row in sorted(part3_rows, key=lambda r: -r["addon_annual"]):
        md.append(
            f"| ${row['target']:.2f} | ${row['stop']:.2f} | "
            f"{row['n_s4a']} | {row['n_addon']} | "
            f"{row['addon_rate']:.1f}% | "
            f"${row['addon_mean']:+.2f} | "
            f"${row['addon_annual']:+,.0f} |\n"
        )
    md.append(
        "\n### Table 3A — S4A-only vs S4A+add-on (best add-on config)\n\n"
    )
    if best_part3_row is not None:
        br = best_part3_row
        md.append(
            f"Best add-on config: target ${br['target']:.2f}, "
            f"stop ${br['stop']:.2f}.\n\n"
            "| Strategy | Entries counted per game | Mean P&L | Annual EV |\n"
            "|---|---|---:|---:|\n"
            f"| S4A-only (tranche 1) | 1 per S4A entry | "
            f"${br['s4a_mean']:+.2f} | ${br['s4a_annual']:+,.0f} |\n"
            f"| S4A + add-on (combined per S4A entry) | 1 per S4A entry, "
            f"add-on fires in {br['addon_rate']:.1f}% of them | "
            f"${br['combined_mean']:+.2f} | "
            f"${br['combined_annual']:+,.0f} |\n"
            f"| Δ (add-on effect) | — | "
            f"${br['combined_mean'] - br['s4a_mean']:+.2f} | "
            f"${br['combined_annual'] - br['s4a_annual']:+,.0f} |\n"
        )

    # ---- Part 4 ----
    md.append("\n## Part 4 — Holdout validation\n")
    if part4_info is None:
        md.append(
            "**Not run.** No Part 1/2/3 config cleared the "
            "+$300/yr annual EV threshold. Holdout validation is "
            "only run when there is a config plausibly worth "
            "shipping.\n"
        )
    else:
        md.append(
            f"Ran on top {len(part4_info['configs'])} Part 1 "
            "configs with 6-seed train/test splits (seeds 42-47, "
            f"train/test ≈ 270/134 at {HOLDOUT_TRAIN_FRAC:.2%} "
            "train fraction).\n\n"
        )
        for cfg_info in part4_info["configs"]:
            md.append(
                f"\n### {cfg_info['label']} — "
                f"verdict: **{cfg_info['verdict']}** "
                f"({cfg_info['n_positive_test']}/6 seeds positive on test)\n\n"
            )
            md.append(
                "| Seed | Train mean P&L | Test mean P&L |\n"
                "|---:|---:|---:|\n"
            )
            for ps in cfg_info["per_seed"]:
                md.append(
                    f"| {ps['seed']} | ${ps['train_mean']:+.2f} | "
                    f"${ps['test_mean']:+.2f} |\n"
                )

    # ---- Part 5 ----
    md.append("\n## Part 5 — Comparison to existing S4A\n")
    md.append(
        "| Config | Entries | Hit % | Mean P&L | Annual EV | Max single loss | Resolution exposure |\n"
        "|---|---:|---:|---:|---:|---:|---|\n"
    )
    # S4A standard baseline (config result)
    b = s4a_baseline_cfg_result
    md.append(
        f"| S4A standard [{S4A_CFG_BASE.entry_lo:.2f}-"
        f"{S4A_CFG_BASE.entry_hi:.2f}] tgt{S4A_CFG_BASE.exit_target:.2f} "
        f"stop{S4A_CFG_BASE.stop_loss:.2f} | "
        f"{b.entries} | {b.hit_pct:.1f}% | "
        f"${b.mean_pnl:+.2f} | ${b.annual_ev:+,.0f} | "
        f"${b.max_loss:+.2f} | no |\n"
    )
    # Best extended-entry
    md.append(
        f"| Best extended: {best_extended.label} | "
        f"{best_extended.entries} | {best_extended.hit_pct:.1f}% | "
        f"${best_extended.mean_pnl:+.2f} | "
        f"${best_extended.annual_ev:+,.0f} | "
        f"${best_extended.max_loss:+.2f} | no |\n"
    )
    # Best filtered S3 variant
    fs = part2_filtered[best_part2_filtered_key]
    md.append(
        f"| Best S3 filtered ({fs['label']}) | "
        f"{fs['entries']} | {fs['hit_pct']:.1f}% | "
        f"${fs['mean_pnl']:+.2f} | ${fs['annual_ev']:+,.0f} | — | "
        f"{'yes' if 'resolution' in best_part2_filtered_key else 'no'} |\n"
    )
    # S3 original (variant a_s3_original filtered)
    s3_orig = part2_filtered["a_s3_original"]
    md.append(
        f"| S3 original (a, filtered) | "
        f"{s3_orig['entries']} | {s3_orig['hit_pct']:.1f}% | "
        f"${s3_orig['mean_pnl']:+.2f} | "
        f"${s3_orig['annual_ev']:+,.0f} | — | yes (75%) |\n"
    )
    # Best Part 3 add-on standalone
    if best_part3_row is not None:
        br = best_part3_row
        md.append(
            f"| Best Part 3 add-on (target ${br['target']:.2f}, "
            f"stop ${br['stop']:.2f}) standalone | "
            f"{br['n_addon']} | — | "
            f"${br['addon_mean']:+.2f} | "
            f"${br['addon_annual']:+,.0f} | — | no |\n"
        )

    # ---- Part 6 ----
    md.append("\n## Part 6 — Verdict\n")
    md.append(f"\n**{verdict}**\n\n{verdict_detail}\n")

    # ============================================================
    # Follow-up: Parts 7-11 (appended below horizontal rule)
    # ============================================================
    if part7_results is None:
        return "".join(md) + "\n"

    md.append("\n---\n")
    md.append(
        "\n# Follow-up — Parts 7-11: Ratchet, Trailing, Add-on Holdout, Time Gate\n"
    )
    md.append(
        "_Follow-up run appended on "
        f"{datetime.now(timezone.utc).isoformat()}_\n"
    )
    md.append(
        "\nMotivation: Part 1's best standalone extended-range config "
        f"produced +${best_extended.annual_ev:+,.0f}/yr but "
        f"{100 * (best_extended.n_stop / max(1, best_extended.entries)):.0f}% "
        "of entries stopped out at the initial stop. Tests three "
        "mechanisms to reduce that drag: (7) ratchet / trailing stop, "
        "(8) holdout validation of the Part 3 add-on, (9) time-gated "
        "exit on the add-on. Part 10 refreshes the comparison table "
        "with the new configs; Part 11 revises the verdict.\n"
    )

    # ---- Part 7 ----
    md.append(
        "\n## Part 7 — Breakeven ratchet / trailing stop on extended entries\n"
    )
    md.append(
        f"Entry zone fixed at $0.40–$0.45 (Part 1 best). Target fixed "
        f"at $0.90. Sweeps test what happens when we convert stops "
        "on recovered-then-fell-back trajectories from full stop-outs "
        "into near-scratch exits.\n"
    )
    md.append("\n### Table 7A — Ratchet configs (12)\n\n")
    md.append(
        "| Config | Entries | Target | Full stop | Ratchet stop | EoG | Hit % | Mean P&L | Annual EV |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for r in sorted(
        part7_results["ratchet"], key=lambda r: -r["annual_ev"],
    ):
        md.append(
            f"| {r['label']} | {r['entries']} | "
            f"{r['n_target']} | {r['n_full_stop']} | "
            f"{r['n_ratchet_stop']} | {r['n_end_of_game']} | "
            f"{r['hit_pct']:.1f}% | ${r['mean_pnl']:+.2f} | "
            f"${r['annual_ev']:+,.0f} |\n"
        )

    md.append("\n### Table 7B — Trailing stop configs (8)\n\n")
    md.append(
        "| Config | Entries | Target | Full stop | Trail stop | EoG | Hit % | Mean P&L | Annual EV |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for r in sorted(
        part7_results["trail"], key=lambda r: -r["annual_ev"],
    ):
        md.append(
            f"| {r['label']} | {r['entries']} | "
            f"{r['n_target']} | {r['n_full_stop']} | "
            f"{r['n_trail_stop']} | {r['n_end_of_game']} | "
            f"{r['hit_pct']:.1f}% | ${r['mean_pnl']:+.2f} | "
            f"${r['annual_ev']:+,.0f} |\n"
        )

    md.append("\n### Table 7C — Best of each vs no-ratchet baseline\n\n")
    md.append(
        "| Config | Entries | Hit % | Mean P&L | Annual EV | Δ vs baseline |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    baseline_annual_p1 = best_extended.annual_ev
    md.append(
        f"| **Baseline** ({best_extended.label}) | "
        f"{best_extended.entries} | {best_extended.hit_pct:.1f}% | "
        f"${best_extended.mean_pnl:+.2f} | "
        f"${best_extended.annual_ev:+,.0f} | — |\n"
    )
    if best_ratchet_row is not None:
        md.append(
            f"| Best ratchet: {best_ratchet_row['label']} | "
            f"{best_ratchet_row['entries']} | "
            f"{best_ratchet_row['hit_pct']:.1f}% | "
            f"${best_ratchet_row['mean_pnl']:+.2f} | "
            f"${best_ratchet_row['annual_ev']:+,.0f} | "
            f"${best_ratchet_row['annual_ev'] - baseline_annual_p1:+,.0f} |\n"
        )
    if best_trail_row is not None:
        md.append(
            f"| Best trail: {best_trail_row['label']} | "
            f"{best_trail_row['entries']} | "
            f"{best_trail_row['hit_pct']:.1f}% | "
            f"${best_trail_row['mean_pnl']:+.2f} | "
            f"${best_trail_row['annual_ev']:+,.0f} | "
            f"${best_trail_row['annual_ev'] - baseline_annual_p1:+,.0f} |\n"
        )

    # ---- Part 8 ----
    if part8_results is not None:
        md.append("\n## Part 8 — Holdout validation\n")
        md.append("\n### Table 8A — Add-on tranche (target $0.90, stop $0.34)\n\n")
        md.append(
            f"6-seed train/test split ({HOLDOUT_TRAIN_FRAC:.0%} train). "
            "Add-on standalone mean P&L computed over the add-on "
            "entries (tranche-2 fires) only.\n\n"
            "| Seed | Train addon n | Train mean P&L | Test addon n | Test mean P&L |\n"
            "|---:|---:|---:|---:|---:|\n"
        )
        for s in part8_results["addon"]["per_seed"]:
            md.append(
                f"| {s['seed']} | {s['train_addon_n']} | "
                f"${s['train_mean']:+.2f} | {s['test_addon_n']} | "
                f"${s['test_mean']:+.2f} |\n"
            )
        md.append(
            f"\n**Add-on holdout verdict:** "
            f"**{part8_results['addon']['verdict']}** "
            f"({part8_results['addon']['n_positive']}/6 seeds "
            "positive on test).\n"
        )

        if part8_results.get("ratchet") is not None:
            rinfo = part8_results["ratchet"]
            br = rinfo["best_ratchet"]
            md.append(
                f"\n### Table 8B — Best ratchet ({br['label']})\n\n"
                f"6-seed train/test split. Best ratchet beat the "
                f"no-ratchet baseline at +${br['annual_ev']:+,.0f}/yr "
                f"(vs baseline +${baseline_annual_p1:+,.0f}/yr).\n\n"
                "| Seed | Train n | Train mean P&L | Test n | Test mean P&L |\n"
                "|---:|---:|---:|---:|---:|\n"
            )
            for s in rinfo["per_seed"]:
                md.append(
                    f"| {s['seed']} | {s['train_n']} | "
                    f"${s['train_mean']:+.2f} | {s['test_n']} | "
                    f"${s['test_mean']:+.2f} |\n"
                )
            n_pos = sum(
                1 for s in rinfo["per_seed"] if s["test_mean"] > 0
            )
            md.append(
                f"\n**Ratchet holdout verdict:** "
                f"**{rinfo['verdict']}** "
                f"({n_pos}/6 seeds positive on test).\n"
            )
        else:
            md.append(
                "\n_Ratchet holdout skipped — best ratchet config did "
                "not beat the no-ratchet baseline._\n"
            )

    # ---- Part 9 ----
    if part9_rows is not None:
        md.append("\n## Part 9 — Time-gated add-on tranche\n")
        md.append(
            "Add-on tranche (target $0.90, stop $0.34) with a forced "
            "close if the add-on has been open for ≥ N minutes AND "
            "price has not recovered to entry + recovery_threshold. "
            "Forced close uses taker fee.\n"
        )
        md.append("\n### Table 9A — Time-gate configs (18)\n\n")
        md.append(
            "| Gate (min) | Recovery thr | Add-on entries | Target | Stop | Time-gate exits | EoG | Add-on mean P&L | Combined annual EV | Δ vs ungated |\n"
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        )
        # Ungated baseline from Part 3
        ungated_combined = (
            best_part3_row["combined_annual"]
            if best_part3_row else 0.0
        )
        ungated_addon_annual = (
            best_part3_row["addon_annual"]
            if best_part3_row else 0.0
        )
        for row in sorted(
            part9_rows, key=lambda r: -r["combined_annual"],
        ):
            ex = row["t2_exits"]
            delta_combined = row["combined_annual"] - ungated_combined
            md.append(
                f"| {row['gate_minutes']} | "
                f"${row['recovery_threshold']:.2f} | "
                f"{row['n_addon']} | "
                f"{ex.get('target', 0)} | {ex.get('stop', 0)} | "
                f"{ex.get('time_gate', 0)} | "
                f"{ex.get('end_of_game', 0)} | "
                f"${row['addon_mean']:+.2f} | "
                f"${row['combined_annual']:+,.0f} | "
                f"${delta_combined:+,.0f} |\n"
            )
        md.append(
            "\n### Table 9B — Best time gate vs ungated baseline\n\n"
        )
        if best_time_gate_row is not None and best_part3_row is not None:
            md.append(
                "| Variant | Add-on entries | Add-on mean | Combined annual EV | Δ vs ungated |\n"
                "|---|---:|---:|---:|---:|\n"
                f"| Ungated (Part 3 best) | "
                f"{best_part3_row['n_addon']} | "
                f"${best_part3_row['addon_mean']:+.2f} | "
                f"${best_part3_row['combined_annual']:+,.0f} | — |\n"
                f"| Best time-gated ({best_time_gate_row['gate_minutes']}min / "
                f"+${best_time_gate_row['recovery_threshold']:.2f} recovery) | "
                f"{best_time_gate_row['n_addon']} | "
                f"${best_time_gate_row['addon_mean']:+.2f} | "
                f"${best_time_gate_row['combined_annual']:+,.0f} | "
                f"${best_time_gate_row['combined_annual'] - best_part3_row['combined_annual']:+,.0f} |\n"
            )

    # ---- Part 10 ----
    md.append("\n## Part 10 — Updated comparison (Parts 1-9)\n\n")
    md.append(
        "| Config | Entries | Hit % | Mean P&L | Annual EV | Max loss | Resolution? |\n"
        "|---|---:|---:|---:|---:|---:|---|\n"
    )
    b = s4a_baseline_cfg_result
    md.append(
        f"| S4A standard [{S4A_CFG_BASE.entry_lo:.2f}-"
        f"{S4A_CFG_BASE.entry_hi:.2f}] tgt{S4A_CFG_BASE.exit_target:.2f} "
        f"stop{S4A_CFG_BASE.stop_loss:.2f} | "
        f"{b.entries} | {b.hit_pct:.1f}% | "
        f"${b.mean_pnl:+.2f} | ${b.annual_ev:+,.0f} | "
        f"${b.max_loss:+.2f} | no |\n"
    )
    md.append(
        f"| Best extended standalone (Part 1) | "
        f"{best_extended.entries} | {best_extended.hit_pct:.1f}% | "
        f"${best_extended.mean_pnl:+.2f} | "
        f"${best_extended.annual_ev:+,.0f} | "
        f"${best_extended.max_loss:+.2f} | no |\n"
    )
    if best_ratchet_row is not None:
        md.append(
            f"| Best ratchet (Part 7): {best_ratchet_row['label']} | "
            f"{best_ratchet_row['entries']} | "
            f"{best_ratchet_row['hit_pct']:.1f}% | "
            f"${best_ratchet_row['mean_pnl']:+.2f} | "
            f"${best_ratchet_row['annual_ev']:+,.0f} | "
            f"${best_ratchet_row['max_loss']:+.2f} | no |\n"
        )
    if best_trail_row is not None:
        md.append(
            f"| Best trailing (Part 7): {best_trail_row['label']} | "
            f"{best_trail_row['entries']} | "
            f"{best_trail_row['hit_pct']:.1f}% | "
            f"${best_trail_row['mean_pnl']:+.2f} | "
            f"${best_trail_row['annual_ev']:+,.0f} | "
            f"${best_trail_row['max_loss']:+.2f} | no |\n"
        )
    if best_part3_row is not None:
        br = best_part3_row
        md.append(
            f"| S4A + add-on ungated (Part 3) combined | "
            f"{br['n_s4a']} (+{br['n_addon']} addon) | — | "
            f"${br['combined_mean']:+.2f} | "
            f"${br['combined_annual']:+,.0f} | — | no |\n"
        )
    if best_time_gate_row is not None:
        bt = best_time_gate_row
        md.append(
            f"| S4A + add-on time-gated (Part 9, "
            f"{bt['gate_minutes']}m/+${bt['recovery_threshold']:.2f}) "
            f"combined | "
            f"{bt['n_s4a']} (+{bt['n_addon']} addon) | — | "
            f"${bt['combined_mean']:+.2f} | "
            f"${bt['combined_annual']:+,.0f} | — | no |\n"
        )

    # ---- Part 11 ----
    md.append("\n## Part 11 — Updated verdict\n")
    if part11_verdict and part11_detail:
        md.append(f"\n**{part11_verdict}**\n\n{part11_detail}\n")

    # ============================================================
    # Follow-up #2: Parts 12-15 (ratchet on S4A + add-on + full stack)
    # ============================================================
    if part12_rows is None:
        return "".join(md) + "\n"

    md.append("\n---\n")
    md.append(
        "\n# Follow-up #2 — Parts 12-15: Ratchet on S4A Standard + Add-On\n"
    )
    md.append(
        "_Follow-up run appended on "
        f"{datetime.now(timezone.utc).isoformat()}_\n"
    )
    md.append(
        "\nPart 7's ratchet discovery (on EXTENDED entries, "
        "$0.40-$0.45) nearly doubled standalone EV. Parts 12-15 "
        "apply the same breakeven-ratchet mechanic to: (12) S4A's "
        "own standard entry zone $0.50-$0.75, (13) the add-on "
        "tranche from Part 3, (14) the full stack with both "
        "tranches ratcheted, (15) holdout validation of the "
        "winning config(s).\n"
    )

    # ---- Part 12 ----
    md.append("\n## Part 12 — Ratchet on S4A standard entries\n")
    md.append(
        "S4A baseline: entry $0.50-$0.75, target $0.90, initial "
        f"stop $0.40. S4A baseline (no ratchet): "
        f"{s4a_baseline_cfg_result.entries} entries, "
        f"{s4a_baseline_cfg_result.hit_pct:.1f}% hit, "
        f"${s4a_baseline_cfg_result.mean_pnl:+.2f} mean, "
        f"${s4a_baseline_cfg_result.annual_ev:+,.0f}/yr.\n"
    )
    md.append("\n### Table 12A — S4A ratchet configs (6)\n\n")
    md.append(
        "| Trigger | Entries | Target | Full stop | Ratchet stop | EoG | Hit % | Ratchet % | Mean P&L | Annual EV | Δ baseline |\n"
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    baseline_annual = s4a_baseline_cfg_result.annual_ev
    sorted_p12 = sorted(part12_rows, key=lambda r: -r["annual_ev"])
    for r in sorted_p12:
        delta = r["annual_ev"] - baseline_annual
        md.append(
            f"| +${r['trigger']:.2f} | {r['entries']} | "
            f"{r['n_target']} | {r['n_full_stop']} | "
            f"{r['n_ratchet_stop']} | {r['n_end_of_game']} | "
            f"{r['hit_pct']:.1f}% | {r['ratchet_pct']:.1f}% | "
            f"${r['mean_pnl']:+.2f} | "
            f"${r['annual_ev']:+,.0f} | "
            f"${delta:+,.0f} |\n"
        )
    md.append(
        f"| (baseline, no ratchet) | "
        f"{s4a_baseline_cfg_result.entries} | — | — | — | — | "
        f"{s4a_baseline_cfg_result.hit_pct:.1f}% | — | "
        f"${s4a_baseline_cfg_result.mean_pnl:+.2f} | "
        f"${baseline_annual:+,.0f} | — |\n"
    )

    # ---- Part 13 ----
    if part13_rows is not None:
        md.append("\n## Part 13 — Ratchet on add-on tranche only\n")
        md.append(
            "S4A has NO ratchet (baseline $0.40 stop). Add-on "
            "tranche enters in $0.40-$0.45 when S4A is open; "
            "target $0.90, initial stop $0.34, plus breakeven "
            "ratchet on the add-on.\n"
        )
        md.append("\n### Table 13A — Add-on ratchet configs (6)\n\n")
        md.append(
            "| Trigger | S4A n | Add-on n | Addon target | Addon full stop | Addon ratchet stop | Addon EoG | Addon mean | Combined annual EV | Δ ungated |\n"
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        )
        ungated_combined = (
            best_part3_row["combined_annual"]
            if best_part3_row else 0.0
        )
        sorted_p13 = sorted(
            part13_rows, key=lambda r: -r["combined_annual"],
        )
        for r in sorted_p13:
            t2x = r["t2_exits"]
            md.append(
                f"| +${r['trigger']:.2f} | {r['n_s4a']} | "
                f"{r['n_addon']} | "
                f"{t2x.get('target', 0)} | "
                f"{t2x.get('stop', 0)} | "
                f"{t2x.get('ratchet_stop', 0)} | "
                f"{t2x.get('end_of_game', 0)} | "
                f"${r['addon_mean']:+.2f} | "
                f"${r['combined_annual']:+,.0f} | "
                f"${r['combined_annual'] - ungated_combined:+,.0f} |\n"
            )
        if best_part3_row:
            md.append(
                f"| (ungated add-on, Part 3 baseline) | "
                f"{best_part3_row['n_s4a']} | "
                f"{best_part3_row['n_addon']} | — | — | — | — | "
                f"${best_part3_row['addon_mean']:+.2f} | "
                f"${best_part3_row['combined_annual']:+,.0f} | — |\n"
            )

    # ---- Part 14 ----
    if part14_rows is not None:
        md.append("\n## Part 14 — Full stack: both tranches ratcheted\n")
        md.append(
            "Top-3 S4A ratchet triggers × top-3 add-on ratchet "
            "triggers (Cartesian, deduped). Both tranches have "
            "independent ratchet state.\n"
        )
        md.append("\n### Table 14A — Combined configs\n\n")
        md.append(
            "| Config | S4A n | Add-on n | S4A mean | Add-on mean | Combined mean | Combined annual EV | Δ S4A-only | Δ ungated addon |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        )
        s4a_only_annual = baseline_annual
        ungated_combined = (
            best_part3_row["combined_annual"]
            if best_part3_row else 0.0
        )
        sorted_p14 = sorted(
            part14_rows, key=lambda r: -r["combined_annual"],
        )
        for r in sorted_p14:
            md.append(
                f"| {r['label']} | {r['n_s4a']} | {r['n_addon']} | "
                f"${r['s4a_mean']:+.2f} | "
                f"${r['addon_mean']:+.2f} | "
                f"${r['combined_mean']:+.2f} | "
                f"${r['combined_annual']:+,.0f} | "
                f"${r['combined_annual'] - s4a_only_annual:+,.0f} | "
                f"${r['combined_annual'] - ungated_combined:+,.0f} |\n"
            )
        md.append(
            f"| (S4A-only baseline) | "
            f"{s4a_baseline_cfg_result.entries} | 0 | "
            f"${s4a_baseline_cfg_result.mean_pnl:+.2f} | — | "
            f"${s4a_baseline_cfg_result.mean_pnl:+.2f} | "
            f"${s4a_only_annual:+,.0f} | — | — |\n"
        )
        if best_part3_row:
            md.append(
                f"| (S4A + ungated addon, Part 3 best) | "
                f"{best_part3_row['n_s4a']} | "
                f"{best_part3_row['n_addon']} | "
                f"${best_part3_row['s4a_mean']:+.2f} | "
                f"${best_part3_row['addon_mean']:+.2f} | "
                f"${best_part3_row['combined_mean']:+.2f} | "
                f"${best_part3_row['combined_annual']:+,.0f} | — | — |\n"
            )

    # ---- Part 15 ----
    if part15_results is not None:
        md.append("\n## Part 15 — Holdout validation + final comparison\n")
        md.append(
            "Holdout the top config by combined annual EV (Part 13 "
            "or Part 14, whichever is higher). Also holdout "
            "S4A-with-ratchet standalone if it materially beats "
            "the S4A no-ratchet baseline.\n"
        )
        dual_row = part15_results["top_dual_row"]
        dual_key = part15_results["top_dual_key"]
        md.append(
            f"\n### Table 15A — Top dual-tranche holdout "
            f"({dual_row.get('label', dual_key)})\n\n"
            "| Seed | Train n | Train mean P&L | Test n | Test mean P&L |\n"
            "|---:|---:|---:|---:|---:|\n"
        )
        for s in part15_results["dual_holdout"]:
            md.append(
                f"| {s['seed']} | {s['train_n']} | "
                f"${s['train_mean']:+.2f} | {s['test_n']} | "
                f"${s['test_mean']:+.2f} |\n"
            )
        md.append(
            f"\n**Dual-tranche holdout verdict:** "
            f"**{part15_results['dual_verdict']}** "
            f"({part15_results['dual_positive']}/6 seeds positive "
            "on test).\n"
        )
        if part15_results.get("s4a_holdout") is not None:
            best_p12 = part15_results["best_p12"]
            md.append(
                f"\n### Table 15B — S4A-with-ratchet standalone "
                f"(+${best_p12['trigger']:.2f} trigger)\n\n"
                "| Seed | Train n | Train mean P&L | Test n | Test mean P&L |\n"
                "|---:|---:|---:|---:|---:|\n"
            )
            for s in part15_results["s4a_holdout"]:
                md.append(
                    f"| {s['seed']} | {s['train_n']} | "
                    f"${s['train_mean']:+.2f} | {s['test_n']} | "
                    f"${s['test_mean']:+.2f} |\n"
                )
            md.append(
                f"\n**S4A-with-ratchet holdout verdict:** "
                f"**{part15_results['s4a_verdict']}** "
                f"({part15_results['s4a_positive']}/6 seeds "
                "positive on test).\n"
            )
        else:
            md.append(
                "\n_S4A-with-ratchet holdout skipped — best "
                "trigger did not materially beat the S4A no-ratchet "
                "baseline._\n"
            )

        # Final comparison
        md.append("\n### Final comparison — all key configs\n\n")
        md.append(
            "| Config | Entries | Hit % | Mean P&L | Annual EV | Max loss |\n"
            "|---|---:|---:|---:|---:|---:|\n"
        )
        b = s4a_baseline_cfg_result
        md.append(
            f"| S4A no-ratchet (baseline) | {b.entries} | "
            f"{b.hit_pct:.1f}% | ${b.mean_pnl:+.2f} | "
            f"${b.annual_ev:+,.0f} | ${b.max_loss:+.2f} |\n"
        )
        best_p12 = part15_results["best_p12"]
        md.append(
            f"| S4A with ratchet (best Part 12, "
            f"+${best_p12['trigger']:.2f}) | {best_p12['entries']} | "
            f"{best_p12['hit_pct']:.1f}% | "
            f"${best_p12['mean_pnl']:+.2f} | "
            f"${best_p12['annual_ev']:+,.0f} | "
            f"${best_p12['max_loss']:+.2f} |\n"
        )
        if best_part3_row:
            md.append(
                f"| S4A + add-on no-ratchet (Part 3 baseline) | "
                f"{best_part3_row['n_s4a']} "
                f"(+{best_part3_row['n_addon']} addon) | — | "
                f"${best_part3_row['combined_mean']:+.2f} | "
                f"${best_part3_row['combined_annual']:+,.0f} | — |\n"
            )
        md.append(
            f"| S4A + addon (top dual, {dual_row.get('label', '')}) | "
            f"{dual_row['n_s4a']} "
            f"(+{dual_row['n_addon']} addon) | — | "
            f"${dual_row['combined_mean']:+.2f} | "
            f"${dual_row['combined_annual']:+,.0f} | — |\n"
        )
        if best_ratchet_row is not None:
            md.append(
                f"| Extended standalone + ratchet (Part 7 best) | "
                f"{best_ratchet_row['entries']} | "
                f"{best_ratchet_row['hit_pct']:.1f}% | "
                f"${best_ratchet_row['mean_pnl']:+.2f} | "
                f"${best_ratchet_row['annual_ev']:+,.0f} | "
                f"${best_ratchet_row['max_loss']:+.2f} |\n"
            )

        # Final verdict
        md.append("\n### Final verdict (Parts 12-15 synthesis)\n")
        if final_verdict and final_detail:
            md.append(f"\n**{final_verdict}**\n\n{final_detail}\n")

    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading 404-game Kalshi paired dataset...")
    games_raw = load_kalshi_games_all_spreads()
    games = pack_games(games_raw)
    n_games = len(games)
    log(f"  {n_games} games loaded")

    log("Precomputing trailing max (180s → 6 bins)...")
    lb_bins = max(1, int(S4A_LOOKBACK_SEC / BUCKET_SEC))
    precomp: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        precomp[(g.ticker, lb_bins)] = _precompute_trailing_max(
            g.fav_series, lb_bins,
        )

    # S4A baseline (for sanity check + Part 5 comparison)
    log("Running S4A baseline (config result)...")
    enriched_base = _simulate_with_recompute(
        games, precomp, lb_bins,
        S4A_CFG_BASE.entry_lo, S4A_CFG_BASE.entry_hi,
        S4A_CFG_BASE.exit_target, S4A_CFG_BASE.stop_loss,
    )
    s4a_baseline = _summarize(
        "S4A standard", S4A_CFG_BASE.entry_lo, S4A_CFG_BASE.entry_hi,
        S4A_CFG_BASE.exit_target, S4A_CFG_BASE.stop_loss,
        enriched_base, n_games,
    )
    log(
        f"  S4A baseline: {s4a_baseline.entries} entries, "
        f"total P&L ${s4a_baseline.total_pnl:+,.2f}, "
        f"annual ${s4a_baseline.annual_ev:+,.0f}"
    )

    log("Part 1: extended entry-zone sweep...")
    part1_results = run_part1(games, precomp)
    sorted_p1 = sorted(part1_results, key=lambda r: -r.annual_ev)
    best_extended = sorted_p1[0]
    log(
        f"  {len(part1_results)} configs; best: {best_extended.label} → "
        f"${best_extended.annual_ev:+,.0f}/yr"
    )

    log("Part 2: S3 filter variants (filtered + unfiltered)...")
    part2_filtered = run_part2(games, apply_filters=True)
    part2_unfiltered = run_part2(games, apply_filters=False)
    best_p2_key = max(
        part2_filtered, key=lambda k: part2_filtered[k]["annual_ev"],
    )
    log(
        f"  best filtered variant: {part2_filtered[best_p2_key]['label']} "
        f"→ ${part2_filtered[best_p2_key]['annual_ev']:+,.0f}/yr"
    )

    log("Part 3: concurrent add-on tranche sweep...")
    part3_rows = run_part3(games, precomp)
    best_p3 = (
        max(part3_rows, key=lambda r: r["combined_annual"])
        if part3_rows else None
    )
    if best_p3:
        log(
            f"  best add-on: target ${best_p3['target']:.2f} / "
            f"stop ${best_p3['stop']:.2f}, "
            f"combined ${best_p3['combined_annual']:+,.0f}/yr "
            f"(Δ ${best_p3['combined_annual'] - best_p3['s4a_annual']:+,.0f})"
        )

    # Part 4 — conditional
    # Candidates: any config in Part 1 with annual EV >= +$300, also
    # best Part 2 filtered variant if >= +$300.
    threshold = 300
    candidates: list[ConfigResult] = [
        r for r in sorted_p1 if r.annual_ev >= threshold
    ][:3]
    part4_info: dict | None = None
    best_part2_annual = part2_filtered[best_p2_key]["annual_ev"]
    best_part3_annual_delta = (
        best_p3["combined_annual"] - best_p3["s4a_annual"]
        if best_p3 else 0.0
    )
    any_p1_cleared = len(candidates) > 0
    p2_cleared = best_part2_annual >= threshold
    p3_cleared = best_part3_annual_delta >= threshold
    if any_p1_cleared or p2_cleared or p3_cleared:
        log(
            "Part 4: holdout validation triggered "
            f"(Part 1 candidates: {len(candidates)}, "
            f"Part 2 best ≥threshold: {p2_cleared}, "
            f"Part 3 delta ≥threshold: {p3_cleared})..."
        )
        if candidates:
            part4_info = run_part4(games, precomp, candidates)
            log("  done.")
        else:
            part4_info = {"configs": []}
            log("  skipped — only Part 2/3 cleared; "
                "no Part 1 configs to hold out.")
    else:
        log(
            f"Part 4: skipped — no config cleared +${threshold}/yr "
            "threshold."
        )

    # Part 6: verdict
    if best_extended.annual_ev >= 1000:
        verdict = "BUILD"
        verdict_detail = (
            f"Best extended-entry config "
            f"({best_extended.label}) produces "
            f"${best_extended.annual_ev:+,.0f}/yr on the full "
            "404-game dataset, comfortably above the noise floor. "
        )
        if part4_info and part4_info.get("configs"):
            top_verdict = part4_info["configs"][0]["verdict"]
            verdict_detail += (
                f"Holdout validation: "
                f"{part4_info['configs'][0]['n_positive_test']}/6 "
                f"seeds positive on test → **{top_verdict}**. "
            )
        verdict_detail += (
            "Recommend building an extended-range module alongside "
            "S4A standard, sharing the same signal-detection "
            "infrastructure but with its own entry band and exit "
            "parameters."
        )
    elif best_extended.annual_ev >= 300 or best_part2_annual >= 300 or best_part3_annual_delta >= 300:
        verdict = "DEFER"
        verdict_detail = (
            "Directional signal exists but EV is marginal relative "
            "to the complexity of adding a second S4A-family module."
            f" Best extended-entry: ${best_extended.annual_ev:+,.0f}/yr."
            f" Best S3 filtered variant: ${best_part2_annual:+,.0f}/yr."
            " Revisit after the forward-collection cron adds more "
            "paired games; if the signal holds at 600+ games, the "
            "BUILD threshold becomes achievable."
        )
    else:
        verdict = "KILL"
        verdict_detail = (
            "No config across Part 1 (extended entry sweep), Part 2 "
            "(S3 filter variants), or Part 3 (concurrent add-on) "
            "produced annual EV above the +$300 noise floor. Best "
            f"extended-entry: ${best_extended.annual_ev:+,.0f}/yr. "
            f"Best S3 filtered: ${best_part2_annual:+,.0f}/yr. "
            f"Best Part 3 add-on Δ: ${best_part3_annual_delta:+,.0f}/yr. "
            "S3 as a separate engine module is not justified. The "
            "extended-range question is resolved: the $0.35-$0.50 "
            "zone does not contain tradeable edge distinct from "
            "S4A's existing $0.50-$0.75 zone."
        )

    log(f"Part 6 Verdict: {verdict}")

    # ============================================================
    # Follow-up: Parts 7-11
    # ============================================================
    log("Part 7: ratchet + trailing stop on extended entries...")
    part7_results = run_part7(games, precomp)
    best_ratchet_row = max(
        part7_results["ratchet"], key=lambda r: r["annual_ev"],
    )
    best_trail_row = max(
        part7_results["trail"], key=lambda r: r["annual_ev"],
    )
    log(
        f"  best ratchet: {best_ratchet_row['label']} → "
        f"${best_ratchet_row['annual_ev']:+,.0f}/yr "
        f"(Δ vs baseline ${best_ratchet_row['annual_ev'] - best_extended.annual_ev:+,.0f})"
    )
    log(
        f"  best trailing: {best_trail_row['label']} → "
        f"${best_trail_row['annual_ev']:+,.0f}/yr "
        f"(Δ vs baseline ${best_trail_row['annual_ev'] - best_extended.annual_ev:+,.0f})"
    )

    log("Part 8: holdout validation (add-on + best ratchet)...")
    part8_results = run_part8(games, precomp, part7_results, best_extended)
    log(
        f"  add-on holdout: {part8_results['addon']['verdict']} "
        f"({part8_results['addon']['n_positive']}/6 seeds positive)"
    )
    if part8_results.get("ratchet") is not None:
        log(
            f"  ratchet holdout: {part8_results['ratchet']['verdict']}"
        )

    log("Part 9: time-gated add-on sweep...")
    part9_rows = run_part9(games, precomp)
    best_time_gate_row = max(
        part9_rows, key=lambda r: r["combined_annual"],
    )
    log(
        f"  best time gate: {best_time_gate_row['gate_minutes']}min / "
        f"+${best_time_gate_row['recovery_threshold']:.2f} recovery → "
        f"combined ${best_time_gate_row['combined_annual']:+,.0f}/yr "
        f"(Δ vs ungated ${best_time_gate_row['combined_annual'] - best_p3['combined_annual']:+,.0f})"
    )

    # ---- Part 11 verdict synthesis -------------------------------
    # Add-on delta is internal to Part 3 (single-S4A-entry baseline),
    # since both Part 3 and Part 9 use the single-entry dual-tranche
    # simulator. Comparing to s4a_baseline.annual_ev (which allows
    # re-entries) would understate the add-on's incremental value.
    addon_delta_ungated = (
        best_p3["combined_annual"] - best_p3["s4a_annual"]
        if best_p3 else 0.0
    )
    addon_delta_gated = (
        best_time_gate_row["combined_annual"] - best_p3["s4a_annual"]
        if best_p3 else 0.0
    )
    ratchet_beats = best_ratchet_row["annual_ev"] > best_extended.annual_ev
    trail_beats = best_trail_row["annual_ev"] > best_extended.annual_ev
    addon_validated = part8_results["addon"]["verdict"] == "VALIDATED"
    ratchet_validated = (
        part8_results.get("ratchet") is not None
        and part8_results["ratchet"]["verdict"] == "VALIDATED"
    )
    time_gate_improves = addon_delta_gated > addon_delta_ungated
    best_addon_delta = max(addon_delta_ungated, addon_delta_gated)
    best_top_annual = max(
        best_extended.annual_ev,
        best_ratchet_row["annual_ev"],
        best_trail_row["annual_ev"],
    )

    if addon_validated and best_addon_delta >= 300:
        variant = "time-gated" if time_gate_improves else "ungated"
        part11_verdict = (
            f"BUILD ({variant} add-on tranche on S4A engine)"
        )
        if time_gate_improves:
            gate_desc = (
                f"{best_time_gate_row['gate_minutes']}min gate / "
                f"+${best_time_gate_row['recovery_threshold']:.2f} "
                "recovery"
            )
            combined = best_time_gate_row["combined_annual"]
        else:
            gate_desc = "no time gate (ungated outperforms)"
            combined = best_p3["combined_annual"]
        part11_detail = (
            "Holdout-validated add-on tranche on top of the existing "
            "S4A engine produces meaningful incremental EV "
            f"({part8_results['addon']['n_positive']}/6 seeds "
            "positive on test). Best variant: "
            f"{gate_desc}, target $0.90, stop $0.34. Combined "
            f"annual EV ${combined:+,.0f}/yr vs single-entry S4A "
            f"baseline ${best_p3['s4a_annual']:+,.0f}/yr → "
            f"**incremental ${best_addon_delta:+,.0f}/yr** from the "
            "add-on.\n\n"
            "Recommend implementing as a second entry band + "
            "independent tranche inside the existing S4A engine "
            "module; no separate S3 engine is justified. "
            "Standalone extended-range (Parts 1, 7) alone does not "
            "clear BUILD threshold — the add-on structure is where "
            "the value lives.\n\n"
            f"Time gate note: time-gated variants produced "
            f"combined ${best_time_gate_row['combined_annual']:+,.0f} "
            f"vs ungated ${best_p3['combined_annual']:+,.0f}. "
            + ("Use the time gate." if time_gate_improves else
               "Patience beats forcing early exits — keep the "
               "add-on ungated.")
        )
    elif best_top_annual >= 800 or (
        ratchet_beats and ratchet_validated
    ):
        part11_verdict = "DEFER"
        part11_detail = (
            "Some configs improve on Part 1's baseline but the "
            "marginal gain doesn't justify a full build yet. "
            f"Best ratchet: ${best_ratchet_row['annual_ev']:+,.0f}/yr "
            f"(Δ baseline "
            f"${best_ratchet_row['annual_ev'] - best_extended.annual_ev:+,.0f}). "
            f"Best trail: ${best_trail_row['annual_ev']:+,.0f}/yr "
            f"(Δ baseline "
            f"${best_trail_row['annual_ev'] - best_extended.annual_ev:+,.0f}). "
            f"Add-on holdout: {part8_results['addon']['verdict']} "
            f"({part8_results['addon']['n_positive']}/6). "
            "Revisit after forward-collection cron adds more paired "
            "games or if S4A paper-trading reveals stop-drag worse "
            "than simulated."
        )
    else:
        part11_verdict = "KILL"
        part11_detail = (
            "Ratchet, trailing stop, and time gate all fail to "
            "improve meaningfully on the Part 1 baseline or the "
            "Part 3 add-on. Add-on holdout verdict: "
            f"{part8_results['addon']['verdict']} "
            f"({part8_results['addon']['n_positive']}/6 seeds positive). "
            "No config across Parts 7-9 clears BUILD threshold "
            "incremental to the existing S4A engine. "
            "Recommend: do not extend the S4A engine with an "
            "S3-style module. The $0.35-$0.50 zone does not "
            "contain actionable edge."
        )

    log(f"Part 11 Verdict: {part11_verdict}")

    # ============================================================
    # Follow-up #2: Parts 12-15
    # ============================================================
    log("Part 12: S4A standard with ratchet (6 triggers)...")
    part12_rows = run_part12(games, precomp)
    best_p12 = max(part12_rows, key=lambda r: r["annual_ev"])
    log(
        f"  best S4A ratchet: +${best_p12['trigger']:.2f} → "
        f"${best_p12['annual_ev']:+,.0f}/yr "
        f"(Δ baseline "
        f"${best_p12['annual_ev'] - s4a_baseline.annual_ev:+,.0f})"
    )

    log("Part 13: add-on ratchet (6 triggers)...")
    part13_rows = run_part13(games, precomp)
    best_p13 = max(part13_rows, key=lambda r: r["combined_annual"])
    ungated_combined = (
        best_p3["combined_annual"] if best_p3 else 0.0
    )
    log(
        f"  best add-on ratchet: +${best_p13['trigger']:.2f} → "
        f"combined ${best_p13['combined_annual']:+,.0f}/yr "
        f"(Δ ungated ${best_p13['combined_annual'] - ungated_combined:+,.0f})"
    )

    log("Part 14: full stack (both ratcheted, top-3 × top-3)...")
    part14_rows = run_part14(games, precomp, part12_rows, part13_rows)
    best_p14 = (
        max(part14_rows, key=lambda r: r["combined_annual"])
        if part14_rows else None
    )
    if best_p14:
        log(
            f"  best full stack: {best_p14['label']} → "
            f"combined ${best_p14['combined_annual']:+,.0f}/yr"
        )

    log("Part 15: holdout validation on winning configs...")
    part15_results = run_part15(
        games, precomp, part12_rows, part13_rows, part14_rows,
        s4a_baseline.annual_ev,
    )
    log(
        f"  top dual ({part15_results['top_dual_row'].get('label', '')}) "
        f"holdout: {part15_results['dual_verdict']} "
        f"({part15_results['dual_positive']}/6 seeds)"
    )
    if part15_results.get("s4a_verdict"):
        log(
            f"  S4A-with-ratchet holdout: "
            f"{part15_results['s4a_verdict']} "
            f"({part15_results['s4a_positive']}/6 seeds)"
        )

    # ---- Final verdict synthesis (Parts 12-15) ----
    s4a_ratchet_improves = (
        best_p12["annual_ev"] > s4a_baseline.annual_ev + 50
    )
    s4a_ratchet_validated = (
        part15_results.get("s4a_verdict") == "VALIDATED"
    )
    top_dual_annual = part15_results["top_dual_annual"]
    s4a_only_annual = s4a_baseline.annual_ev
    dual_validated = part15_results["dual_verdict"] == "VALIDATED"

    # Decide final recommendation
    if (
        dual_validated
        and top_dual_annual - s4a_only_annual >= 300
    ):
        dual_row = part15_results["top_dual_row"]
        dual_key = part15_results["top_dual_key"]
        s_trig = dual_row.get("s4a_trigger")
        a_trig = dual_row.get("addon_trigger", dual_row.get("trigger"))
        if s_trig is not None:
            cfg_desc = (
                f"S4A ratchet +${s_trig:.2f}, add-on at "
                f"$0.40-$0.45 target $0.90 stop $0.34 with ratchet "
                f"+${a_trig:.2f}"
            )
        else:
            cfg_desc = (
                f"S4A no-ratchet, add-on at $0.40-$0.45 target "
                f"$0.90 stop $0.34 with ratchet +${a_trig:.2f}"
            )
        final_verdict = (
            "SHIP — ratcheted add-on on S4A engine"
        )
        final_detail = (
            f"Best config: {cfg_desc}. Holdout-validated "
            f"{part15_results['dual_positive']}/6 seeds positive "
            f"on test. Combined annual EV "
            f"${top_dual_annual:+,.0f}/yr vs S4A-only "
            f"${s4a_only_annual:+,.0f}/yr → **incremental "
            f"${top_dual_annual - s4a_only_annual:+,.0f}/yr**.\n\n"
            "Implementation path: extend the existing S4A engine "
            "module with (a) a breakeven ratchet parameter on the "
            "primary tranche, and (b) a secondary entry band at "
            "$0.40-$0.45 that opens a 100-contract tranche when "
            "S4A is already open and a dip trigger fires there. "
            "Each tranche has its own ratchet state. No separate "
            "S3 engine needed."
        )
        if s4a_ratchet_improves and s4a_ratchet_validated:
            final_detail += (
                f"\n\nAdditionally: S4A-with-ratchet standalone "
                f"at +${best_p12['trigger']:.2f} trigger also "
                f"holdout-validated "
                f"({part15_results['s4a_positive']}/6 seeds). "
                f"Standalone S4A-with-ratchet: "
                f"${best_p12['annual_ev']:+,.0f}/yr vs baseline "
                f"${s4a_only_annual:+,.0f}/yr. The ratchet on S4A "
                "standard is itself a zero-complexity win — one "
                "parameter, no new entry bands — and can ship "
                "independently if the add-on build is deferred."
            )
    elif s4a_ratchet_improves and s4a_ratchet_validated:
        final_verdict = (
            "SHIP (ratchet on S4A standard only; add-on deferred)"
        )
        final_detail = (
            f"S4A-with-ratchet at +${best_p12['trigger']:.2f} "
            f"trigger delivers "
            f"${best_p12['annual_ev']:+,.0f}/yr vs baseline "
            f"${s4a_only_annual:+,.0f}/yr → **incremental "
            f"${best_p12['annual_ev'] - s4a_only_annual:+,.0f}/yr**. "
            f"Holdout-validated ({part15_results['s4a_positive']}/6 "
            "seeds positive on test). Add-on tranche did not "
            "clear validation or EV threshold — deferred until "
            "more data accumulates.\n\n"
            "Implementation path: add a single ratchet parameter "
            "to the existing S4A engine's position manager. "
            "Trigger at +${best_p12['trigger']:.2f} above entry "
            "price moves stop to entry + $0.01. Zero additional "
            "tranche logic."
        )
    elif (
        dual_validated and top_dual_annual - s4a_only_annual >= 200
    ) or s4a_ratchet_improves:
        final_verdict = "DEFER"
        final_detail = (
            "Directional signal exists but the margin over the "
            "S4A baseline is too thin to justify engine changes "
            "given implementation complexity. "
            f"S4A-with-ratchet best: "
            f"${best_p12['annual_ev']:+,.0f}/yr "
            f"(Δ "
            f"${best_p12['annual_ev'] - s4a_only_annual:+,.0f}). "
            f"Top dual: "
            f"${top_dual_annual:+,.0f}/yr "
            f"(Δ ${top_dual_annual - s4a_only_annual:+,.0f}). "
            "Revisit as dataset grows."
        )
    else:
        final_verdict = "KILL"
        final_detail = (
            "Ratchet mechanics do not materially improve on the "
            "S4A baseline at either the standard entry zone or "
            "the add-on tranche on the 404-game dataset. "
            f"S4A baseline: ${s4a_only_annual:+,.0f}/yr. "
            f"Best ratchet variant: "
            f"${max(best_p12['annual_ev'], top_dual_annual):+,.0f}/yr. "
            "No engine change recommended."
        )
    log(f"Final verdict: {final_verdict}")

    # Part 2 unfiltered sanity (for Part 5 reference) — pass through
    s4a_baseline_only = {"total_pnl": s4a_baseline.total_pnl}

    log("Rendering report...")
    md = render_report(
        n_games=n_games, part1_results=part1_results,
        part2_filtered=part2_filtered,
        part2_unfiltered=part2_unfiltered,
        part3_rows=part3_rows,
        s4a_baseline_only=s4a_baseline_only,
        part4_info=part4_info,
        s4a_baseline_cfg_result=s4a_baseline,
        best_extended=best_extended,
        best_part2_filtered_key=best_p2_key,
        best_part3_row=best_p3,
        verdict=verdict, verdict_detail=verdict_detail,
        part7_results=part7_results,
        part8_results=part8_results,
        part9_rows=part9_rows,
        best_ratchet_row=best_ratchet_row,
        best_trail_row=best_trail_row,
        best_time_gate_row=best_time_gate_row,
        part11_verdict=part11_verdict,
        part11_detail=part11_detail,
        part12_rows=part12_rows,
        part13_rows=part13_rows,
        part14_rows=part14_rows,
        part15_results=part15_results,
        final_verdict=final_verdict,
        final_detail=final_detail,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
