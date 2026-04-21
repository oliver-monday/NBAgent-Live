"""Strategy 4 — Dip-recovery (favorite side) + run-capture (underdog side).

Part 1: false-summit analysis (per price level, how often does a team
        that traded there eventually lose).
Part 2: favorite dip-recovery sweep (1,200 configs).
Part 3: underdog run-capture sweep (~200 configs).
Part 4: cross-strategy comparison.
Part 5: prior-weighting analysis.
Part 6: position management study.
Part 7: halftime entry study (Kalshi paired dataset).
Part 8: spread expansion, ESPN-only Path A (all ~1,200 ESPN games).

Run:
    python -m analysis.strategy4_dip_recovery          # Parts 1-6 (default)
    python -m analysis.strategy4_dip_recovery --part7  # halftime-only
    python -m analysis.strategy4_dip_recovery --part8  # ESPN spread expansion
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy4_dip_recovery.md"
)
REPORT_PART7_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy4_halftime_entry.md"
)
REPORT_PART8_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy4_spread_expansion.md"
)
REPORT_PART8B_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "strategy4_spread_expansion_kalshi.md"
)

# Best S4A config per STRATEGY4_SPEC.md §3. Used by Parts 7 and 8 so
# halftime simulation and ESPN-proxy simulation share a common exit
# framework with the main strategy.
BEST_S4A_LOOKBACK_SEC = 180
BEST_S4A_DIP_DEPTH = 0.08
BEST_S4A_ENTRY_LO = 0.50
BEST_S4A_ENTRY_HI = 0.75
BEST_S4A_EXIT_TARGET = 0.90
BEST_S4A_STOP_LOSS = 0.40

Q_LEN_SEC = 720
OT_LEN_SEC = 300
HALFTIME_SEC = 2 * Q_LEN_SEC   # 1440 = start of Q3

TICKER_RE = re.compile(r"(KXNBAGAME-\d{2}[A-Z]{3}\d{2}[A-Z]{6})")
MAX_SPREAD_COMPETITIVE = 6.0
CONTRACT_SIZE = 100
BUCKET_SEC = 30
RESOLUTION_WIN_CUTOFF = 0.95
RESOLUTION_LOSS_CUTOFF = 0.05
REG_SEASON_GAMES = 1230
# Rough competitive rate: 165/168 in our sample ≈ 98%, but the
# cross-season rate should be the |spread|≤6 rate. Use the empirical
# 549/1234 ≈ 44.5% from the ESPN master CSV.
COMP_FRACTION = 549 / 1234


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def maker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1.0 - price) * 100) / 100


# ---- Loaders ------------------------------------------------------------

def load_competitive_games() -> list[dict]:
    """Return list of {ticker, abs_spread, ts} for competitive games."""
    meta = pd.read_csv(PAIRED_DIR / "matched_games.csv")
    meta["abs_spread"] = pd.to_numeric(meta["abs_spread"], errors="coerce")
    meta = meta.dropna(subset=["abs_spread"])
    meta = meta[meta["abs_spread"] <= MAX_SPREAD_COMPETITIVE]
    meta_map = {
        str(r.kalshi_event_ticker): float(r.abs_spread)
        for r in meta.itertuples()
    }

    games = []
    for p in sorted(PAIRED_DIR.glob("*_timeseries.csv")):
        m = TICKER_RE.match(p.stem)
        if not m:
            continue
        ticker = m.group(1)
        if ticker not in meta_map:
            continue
        df = pd.read_csv(p)
        if df.empty:
            continue
        for c in ("game_seconds_elapsed", "period", "fav_kalshi_vwap",
                  "fav_wp_espn"):
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        # Forward-fill VWAP within the game
        df["fav_kalshi_vwap"] = df["fav_kalshi_vwap"].ffill()
        df = df.dropna(
            subset=["game_seconds_elapsed", "fav_kalshi_vwap"]
        ).sort_values("game_seconds_elapsed").reset_index(drop=True)
        if df.empty:
            continue
        games.append({
            "ticker": ticker,
            "abs_spread": meta_map[ticker],
            "ts": df,
        })
    return games


def fav_outcome(df: pd.DataFrame) -> str:
    """Return 'win' | 'loss' | 'unknown' based on final fav_kalshi_vwap."""
    last = float(df["fav_kalshi_vwap"].iloc[-1])
    if last >= RESOLUTION_WIN_CUTOFF:
        return "win"
    if last <= RESOLUTION_LOSS_CUTOFF:
        return "loss"
    return "unknown"


# ---- Part 1: False-summit analysis -------------------------------------

def false_summit_table(
    games: list[dict], side: str = "fav",
) -> pd.DataFrame:
    """For each price level 0.50-0.99, count how many games reached that
    level for the given side and how many eventually had that side lose.
    Also compute a volume-weighted loss rate (weighted by bins-at-level).

    Note on the 'side' parameter:
      - 'fav' uses fav_kalshi_vwap directly; fav lose = final price
        ≤ RESOLUTION_LOSS_CUTOFF.
      - 'dog' inverts to dog_price = 1 - fav_kalshi_vwap; dog lose =
        fav WON (final fav ≥ RESOLUTION_WIN_CUTOFF).
    """
    levels = [round(0.50 + 0.01 * i, 2) for i in range(50)]
    rows = []
    for level in levels:
        games_reach = 0
        losses = 0
        total_bins_above = 0
        weighted_losses = 0
        for g in games:
            df = g["ts"]
            if side == "fav":
                price = df["fav_kalshi_vwap"].values
                lose_cond = fav_outcome(df) == "loss"
            else:
                price = 1.0 - df["fav_kalshi_vwap"].values
                lose_cond = fav_outcome(df) == "win"   # dog lost ⇒ fav won
            above = price >= level
            bins_above = int(above.sum())
            if bins_above > 0:
                games_reach += 1
                if lose_cond:
                    losses += 1
                total_bins_above += bins_above
                if lose_cond:
                    weighted_losses += bins_above
        loss_rate = 100 * losses / games_reach if games_reach else 0.0
        weighted_loss_rate = (
            100 * weighted_losses / total_bins_above
            if total_bins_above else 0.0
        )
        rows.append({
            "price_level": level,
            "games_reaching": games_reach,
            "eventual_losses": losses,
            "loss_rate_pct": loss_rate,
            "cum_bins_above": total_bins_above,
            "weighted_loss_rate_pct": weighted_loss_rate,
        })
    return pd.DataFrame(rows)


# ---- Part 2: Favorite dip-recovery sweep --------------------------------

@dataclass
class S4AConfig:
    lookback_sec: int
    dip_depth: float
    entry_lo: float
    entry_hi: float
    exit_target: float
    stop_loss: float


@dataclass
class S4ATrade:
    ticker: str
    entry_idx: int
    entry_price: float
    entry_period: int | None
    exit_idx: int
    exit_price: float
    exit_type: str   # "target" | "stop" | "resolution_win" | "resolution_loss" | "resolution_mid"
    hold_bins: int
    net_pnl: float
    is_reentry: bool
    abs_spread: float


def _precompute_trailing_max(
    prices: np.ndarray, lookback_bins: int,
) -> np.ndarray:
    """Trailing max over prices[max(0, i-lookback_bins):i+1] for each i."""
    # pandas rolling is fast and handles edge cases.
    s = pd.Series(prices)
    return s.rolling(window=lookback_bins, min_periods=1).max().values


def simulate_s4a(
    games: list[dict], cfg: S4AConfig,
    precomp: dict[tuple[str, int], np.ndarray],
) -> list[S4ATrade]:
    """Simulate Strategy 4A on all games for one config."""
    trades: list[S4ATrade] = []
    lookback_bins = max(1, int(cfg.lookback_sec / BUCKET_SEC))
    for g in games:
        df = g["ts"]
        prices = df["fav_kalshi_vwap"].values
        periods = df["period"].values
        n = len(prices)
        if n < 2:
            continue
        tmax = precomp[(g["ticker"], lookback_bins)]

        entries_this_game = 0
        max_entries_per_game = 2  # 1 primary + 1 re-entry
        in_pos = False
        entry_idx = entry_price = entry_period = None
        i = 0
        while i < n:
            p = float(prices[i])
            if pd.isna(p):
                i += 1
                continue
            if not in_pos:
                if entries_this_game >= max_entries_per_game:
                    break
                if cfg.entry_lo <= p <= cfg.entry_hi:
                    if (float(tmax[i]) - p) >= cfg.dip_depth:
                        in_pos = True
                        entry_idx = i
                        entry_price = p
                        entry_period = (
                            int(periods[i]) if not pd.isna(periods[i]) else None
                        )
                        entries_this_game += 1
                        i += 1
                        continue
                i += 1
                continue
            # In position
            if p >= cfg.exit_target:
                fee = maker_fee(CONTRACT_SIZE, entry_price) + maker_fee(
                    CONTRACT_SIZE, p,
                )
                gross = (p - entry_price) * CONTRACT_SIZE
                trades.append(S4ATrade(
                    ticker=g["ticker"],
                    entry_idx=entry_idx, entry_price=entry_price,
                    entry_period=entry_period,
                    exit_idx=i, exit_price=p, exit_type="target",
                    hold_bins=i - entry_idx, net_pnl=gross - fee,
                    is_reentry=(entries_this_game > 1),
                    abs_spread=g["abs_spread"],
                ))
                in_pos = False
                i += 1
                continue
            if p <= cfg.stop_loss:
                fee = maker_fee(CONTRACT_SIZE, entry_price) + maker_fee(
                    CONTRACT_SIZE, p,
                )
                gross = (p - entry_price) * CONTRACT_SIZE
                trades.append(S4ATrade(
                    ticker=g["ticker"],
                    entry_idx=entry_idx, entry_price=entry_price,
                    entry_period=entry_period,
                    exit_idx=i, exit_price=p, exit_type="stop",
                    hold_bins=i - entry_idx, net_pnl=gross - fee,
                    is_reentry=(entries_this_game > 1),
                    abs_spread=g["abs_spread"],
                ))
                in_pos = False
                i += 1
                continue
            i += 1

        # Position still open at end of game
        if in_pos:
            last_price = float(prices[-1])
            entry_fee = maker_fee(CONTRACT_SIZE, entry_price)
            if last_price >= RESOLUTION_WIN_CUTOFF:
                resolution = 1.0
                exit_type = "resolution_win"
                exit_fee = 0.0
            elif last_price <= RESOLUTION_LOSS_CUTOFF:
                resolution = 0.0
                exit_type = "resolution_loss"
                exit_fee = 0.0
            else:
                resolution = float(last_price)
                exit_type = "resolution_mid"
                exit_fee = maker_fee(CONTRACT_SIZE, resolution)
            gross = (resolution - entry_price) * CONTRACT_SIZE
            trades.append(S4ATrade(
                ticker=g["ticker"],
                entry_idx=entry_idx, entry_price=entry_price,
                entry_period=entry_period,
                exit_idx=n - 1, exit_price=last_price,
                exit_type=exit_type, hold_bins=(n - 1 - entry_idx),
                net_pnl=gross - entry_fee - exit_fee,
                is_reentry=(entries_this_game > 1),
                abs_spread=g["abs_spread"],
            ))
    return trades


def summarize_s4a(
    trades: list[S4ATrade], n_games: int,
) -> dict:
    if not trades:
        return {
            "entries": 0, "hit_pct": 0.0, "stop_pct": 0.0,
            "held_pct": 0.0, "mean_pnl": 0.0, "annual_ev": 0.0,
            "median_pnl": 0.0, "max_loss": 0.0, "max_win": 0.0,
            "n_target": 0, "n_stop": 0, "n_res_win": 0,
            "n_res_loss": 0, "n_res_mid": 0,
        }
    pnls = np.array([t.net_pnl for t in trades])
    n = len(trades)
    n_target = sum(1 for t in trades if t.exit_type == "target")
    n_stop = sum(1 for t in trades if t.exit_type == "stop")
    n_rw = sum(1 for t in trades if t.exit_type == "resolution_win")
    n_rl = sum(1 for t in trades if t.exit_type == "resolution_loss")
    n_rm = sum(1 for t in trades if t.exit_type == "resolution_mid")
    mean_pnl = float(pnls.mean())
    entries_per_game = n / n_games if n_games else 0
    annual_ev = (
        mean_pnl * entries_per_game * REG_SEASON_GAMES * COMP_FRACTION
    )
    return {
        "entries": n,
        "hit_pct": 100 * n_target / n,
        "stop_pct": 100 * n_stop / n,
        "held_pct": 100 * (n_rw + n_rl + n_rm) / n,
        "mean_pnl": mean_pnl,
        "median_pnl": float(np.median(pnls)),
        "max_loss": float(pnls.min()),
        "max_win": float(pnls.max()),
        "annual_ev": annual_ev,
        "n_target": n_target, "n_stop": n_stop,
        "n_res_win": n_rw, "n_res_loss": n_rl, "n_res_mid": n_rm,
    }


# ---- Part 3: Underdog run-capture --------------------------------------

@dataclass
class S4BConfig:
    label: str
    mode: str                # "momentum" | "static"
    lookback_sec: int | None  # None if mode="static"
    entry_lo: float
    entry_hi: float
    run_size: float | None    # None if mode="static"
    exit_offset: float        # target = entry_price + exit_offset
    stop_offset: float        # stop = max(0.01, entry_price - stop_offset)
    hybrid: bool = False      # if True, sell 50% at target, hold 50% to resolution


@dataclass
class S4BTrade:
    ticker: str
    side: str                # always "dog"
    entry_idx: int
    entry_price: float
    entry_period: int | None
    exit_idx: int
    exit_price: float
    exit_type: str
    net_pnl: float
    abs_spread: float


def _precompute_trailing_min(
    prices: np.ndarray, lookback_bins: int,
) -> np.ndarray:
    s = pd.Series(prices)
    return s.rolling(window=lookback_bins, min_periods=1).min().values


def simulate_s4b(
    games: list[dict], cfg: S4BConfig,
    precomp_min: dict[tuple[str, int], np.ndarray],
) -> list[S4BTrade]:
    """Simulate Strategy 4B on all games for one config."""
    trades: list[S4BTrade] = []
    lookback_bins = (
        max(1, int(cfg.lookback_sec / BUCKET_SEC))
        if cfg.lookback_sec is not None else None
    )
    for g in games:
        df = g["ts"]
        fav = df["fav_kalshi_vwap"].values
        dog = 1.0 - fav
        periods = df["period"].values
        n = len(dog)
        if n < 2:
            continue
        tmin = (
            precomp_min[(g["ticker"], lookback_bins)]
            if lookback_bins is not None else None
        )
        in_pos = False
        entries_this_game = 0
        max_entries = 2
        entry_idx = entry_price = entry_period = None
        # For hybrid: track whether partial has been taken
        partial_taken = False
        partial_pnl = 0.0
        i = 0
        while i < n:
            p = float(dog[i])
            if pd.isna(p):
                i += 1
                continue
            if not in_pos:
                if entries_this_game >= max_entries:
                    break
                fire = False
                if cfg.mode == "static":
                    # Static: enter whenever price in band
                    if cfg.entry_lo <= p <= cfg.entry_hi:
                        fire = True
                else:
                    # Momentum
                    if cfg.entry_lo <= p <= cfg.entry_hi:
                        if tmin is not None:
                            recent_low = float(tmin[i])
                            if (p - recent_low) >= cfg.run_size:
                                fire = True
                if fire:
                    in_pos = True
                    entry_idx = i
                    entry_price = p
                    entry_period = (
                        int(periods[i]) if not pd.isna(periods[i]) else None
                    )
                    entries_this_game += 1
                    partial_taken = False
                    partial_pnl = 0.0
                    i += 1
                    continue
                i += 1
                continue
            # In position
            target = entry_price + cfg.exit_offset
            stop = max(0.01, entry_price - cfg.stop_offset)
            if cfg.hybrid and not partial_taken and p >= target:
                # Take partial (50%)
                half = CONTRACT_SIZE // 2
                fee = maker_fee(half, entry_price) + maker_fee(half, p)
                gross = (p - entry_price) * half
                partial_pnl = gross - fee
                partial_taken = True
                i += 1
                continue
            if not cfg.hybrid and p >= target:
                fee = maker_fee(CONTRACT_SIZE, entry_price) + maker_fee(
                    CONTRACT_SIZE, p,
                )
                gross = (p - entry_price) * CONTRACT_SIZE
                trades.append(S4BTrade(
                    ticker=g["ticker"], side="dog",
                    entry_idx=entry_idx, entry_price=entry_price,
                    entry_period=entry_period,
                    exit_idx=i, exit_price=p, exit_type="target",
                    net_pnl=gross - fee, abs_spread=g["abs_spread"],
                ))
                in_pos = False
                i += 1
                continue
            if p <= stop:
                if cfg.hybrid and partial_taken:
                    half = CONTRACT_SIZE // 2
                    fee_out = maker_fee(half, p)
                    # Entry fee for the retained half was already booked
                    # implicitly in the hybrid flow's partial_pnl calc on
                    # half only. The other half still owes its entry fee:
                    fee_in = maker_fee(half, entry_price)
                    gross = (p - entry_price) * half
                    retained_pnl = gross - fee_in - fee_out
                    trades.append(S4BTrade(
                        ticker=g["ticker"], side="dog",
                        entry_idx=entry_idx, entry_price=entry_price,
                        entry_period=entry_period,
                        exit_idx=i, exit_price=p,
                        exit_type="hybrid_stop_after_partial",
                        net_pnl=partial_pnl + retained_pnl,
                        abs_spread=g["abs_spread"],
                    ))
                else:
                    fee = maker_fee(CONTRACT_SIZE, entry_price) + maker_fee(
                        CONTRACT_SIZE, p,
                    )
                    gross = (p - entry_price) * CONTRACT_SIZE
                    trades.append(S4BTrade(
                        ticker=g["ticker"], side="dog",
                        entry_idx=entry_idx, entry_price=entry_price,
                        entry_period=entry_period,
                        exit_idx=i, exit_price=p, exit_type="stop",
                        net_pnl=gross - fee, abs_spread=g["abs_spread"],
                    ))
                in_pos = False
                i += 1
                continue
            i += 1
        # End of game with open position
        if in_pos:
            last_dog = float(dog[-1])
            # Resolution: if dog price ≥ 0.95 → dog won (fav lost); else
            # if ≤ 0.05 → dog lost; else indeterminate.
            if last_dog >= RESOLUTION_WIN_CUTOFF:
                resolution = 1.0
                exit_type = "resolution_win"
                exit_fee = 0.0
            elif last_dog <= RESOLUTION_LOSS_CUTOFF:
                resolution = 0.0
                exit_type = "resolution_loss"
                exit_fee = 0.0
            else:
                resolution = float(last_dog)
                exit_type = "resolution_mid"
                exit_fee = maker_fee(CONTRACT_SIZE, resolution)
            if cfg.hybrid and partial_taken:
                half = CONTRACT_SIZE // 2
                fee_in = maker_fee(half, entry_price)
                fee_out = (
                    maker_fee(half, resolution)
                    if exit_type == "resolution_mid" else 0.0
                )
                gross = (resolution - entry_price) * half
                retained = gross - fee_in - fee_out
                trades.append(S4BTrade(
                    ticker=g["ticker"], side="dog",
                    entry_idx=entry_idx, entry_price=entry_price,
                    entry_period=entry_period,
                    exit_idx=n - 1, exit_price=last_dog,
                    exit_type=f"hybrid_{exit_type}",
                    net_pnl=partial_pnl + retained,
                    abs_spread=g["abs_spread"],
                ))
            else:
                entry_fee = maker_fee(CONTRACT_SIZE, entry_price)
                gross = (resolution - entry_price) * CONTRACT_SIZE
                trades.append(S4BTrade(
                    ticker=g["ticker"], side="dog",
                    entry_idx=entry_idx, entry_price=entry_price,
                    entry_period=entry_period,
                    exit_idx=n - 1, exit_price=last_dog,
                    exit_type=exit_type,
                    net_pnl=gross - entry_fee - exit_fee,
                    abs_spread=g["abs_spread"],
                ))
    return trades


def summarize_s4b(
    trades: list[S4BTrade], n_games: int,
) -> dict:
    if not trades:
        return {"entries": 0, "mean_pnl": 0.0, "annual_ev": 0.0,
                "median_pnl": 0.0, "max_loss": 0.0, "max_win": 0.0,
                "hit_pct": 0.0, "stop_pct": 0.0, "held_pct": 0.0}
    pnls = np.array([t.net_pnl for t in trades])
    n = len(trades)
    n_target = sum(1 for t in trades if t.exit_type == "target")
    n_stop = sum(1 for t in trades if t.exit_type == "stop")
    n_held = sum(1 for t in trades if t.exit_type.startswith("resolution")
                 or t.exit_type.startswith("hybrid"))
    mean_pnl = float(pnls.mean())
    entries_per_game = n / n_games if n_games else 0
    annual_ev = (
        mean_pnl * entries_per_game * REG_SEASON_GAMES * COMP_FRACTION
    )
    return {
        "entries": n,
        "hit_pct": 100 * n_target / n,
        "stop_pct": 100 * n_stop / n,
        "held_pct": 100 * n_held / n,
        "mean_pnl": mean_pnl,
        "median_pnl": float(np.median(pnls)),
        "max_loss": float(pnls.min()),
        "max_win": float(pnls.max()),
        "annual_ev": annual_ev,
    }


# ---- Report builders ---------------------------------------------------

def render_false_summit(md: list[str], games: list[dict]) -> None:
    md.append("## Part 1 — False-Summit Analysis\n")
    md.append(
        "For each price level, fraction of games where the side "
        "reached that level and eventually *lost* (fav loses if "
        "final fav price ≤ 0.05; dog loses if final fav price ≥ "
        "0.95). Lower loss rates = safer exit ceilings.\n"
    )
    for side in ("fav", "dog"):
        label = "Favorite" if side == "fav" else "Underdog"
        df = false_summit_table(games, side=side)
        md.append(f"### {label} side (n={len(games)} competitive games)\n")
        md.append(
            "| Price level | Games reaching | Eventual losses | "
            "Loss rate | Cum bins above | Weighted loss rate |"
        )
        md.append(
            "|---:|---:|---:|---:|---:|---:|"
        )
        # Show a useful subset: every 0.02 from 0.50 to 0.78, every
        # 0.01 from 0.80 to 0.99 (more resolution at the high end).
        for _, r in df.iterrows():
            lvl = r["price_level"]
            if lvl < 0.80 and round((lvl - 0.50) / 0.02, 3) % 1 != 0:
                continue
            md.append(
                f"| ${lvl:.2f} | {int(r['games_reaching'])} | "
                f"{int(r['eventual_losses'])} | "
                f"{r['loss_rate_pct']:.1f}% | "
                f"{int(r['cum_bins_above'])} | "
                f"{r['weighted_loss_rate_pct']:.1f}% |"
            )
        md.append("")


def render_s4a_top(
    md: list[str], results: list[tuple[S4AConfig, dict]],
) -> tuple[S4AConfig, dict]:
    md.append(
        "### 2A — Top 20 configs by annual EV (favorite dip-recovery)\n"
    )
    md.append(
        "| Rank | Lookback | Dip | Entry zone | Exit | Stop | "
        "Entries | Hit% | Stop% | Held% | Mean P&L | Annual EV |"
    )
    md.append(
        "|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    sorted_r = sorted(results, key=lambda r: r[1]["annual_ev"], reverse=True)
    for i, (cfg, s) in enumerate(sorted_r[:20], 1):
        md.append(
            f"| {i} | {cfg.lookback_sec}s | ${cfg.dip_depth:.2f} | "
            f"${cfg.entry_lo:.2f}–${cfg.entry_hi:.2f} | "
            f"${cfg.exit_target:.2f} | ${cfg.stop_loss:.2f} | "
            f"{s['entries']} | {s['hit_pct']:.0f}% | "
            f"{s['stop_pct']:.0f}% | {s['held_pct']:.0f}% | "
            f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |"
        )
    md.append("")
    return sorted_r[0]


def render_s4a_detail(
    md: list[str], cfg: S4AConfig, trades: list[S4ATrade], n_games: int,
) -> None:
    md.append("### 2B — Best config detail\n")
    md.append(
        f"- Lookback: {cfg.lookback_sec}s\n"
        f"- Dip depth: ${cfg.dip_depth:.2f}\n"
        f"- Entry zone: ${cfg.entry_lo:.2f}–${cfg.entry_hi:.2f}\n"
        f"- Exit target: ${cfg.exit_target:.2f}\n"
        f"- Stop-loss: ${cfg.stop_loss:.2f}\n"
    )
    s = summarize_s4a(trades, n_games)
    md.append("#### Outcome distribution\n")
    md.append("| Outcome | Count | % | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    n = s["entries"] or 1
    buckets = [
        ("Hit target", "target"),
        ("Stopped out", "stop"),
        ("Resolution win (held)", "resolution_win"),
        ("Resolution loss (held)", "resolution_loss"),
        ("Resolution mid (held)", "resolution_mid"),
    ]
    for label, key in buckets:
        sub = [t for t in trades if t.exit_type == key]
        if not sub:
            md.append(f"| {label} | 0 | 0.0% | — |")
            continue
        pnls = [t.net_pnl for t in sub]
        md.append(
            f"| {label} | {len(sub)} | {100*len(sub)/n:.1f}% | "
            f"${np.mean(pnls):+.2f} |"
        )
    md.append(
        f"| **ALL** | **{s['entries']}** | 100.0% | "
        f"**${s['mean_pnl']:+.2f}** |"
    )
    md.append("")
    # P&L histogram
    md.append("#### P&L distribution\n")
    md.append("| Bucket | Count | % |")
    md.append("|---|---:|---:|")
    for label, pred in (
        ("< −$30", lambda v: v < -30),
        ("−$30 to −$10", lambda v: -30 <= v < -10),
        ("−$10 to $0", lambda v: -10 <= v < 0),
        ("$0 to $10", lambda v: 0 <= v < 10),
        ("$10 to $20", lambda v: 10 <= v < 20),
        ("$20 to $30", lambda v: 20 <= v < 30),
        ("> $30", lambda v: v >= 30),
    ):
        c = sum(1 for t in trades if pred(t.net_pnl))
        md.append(f"| {label} | {c} | {100*c/n:.1f}% |")
    md.append("")
    # By period
    md.append("#### By entry period\n")
    md.append("| Period | Entries | Hit% | Stop% | Mean P&L |")
    md.append("|---|---:|---:|---:|---:|")
    for q_label, pred in (
        ("Q1", lambda t: t.entry_period == 1),
        ("Q2", lambda t: t.entry_period == 2),
        ("Q3", lambda t: t.entry_period == 3),
        ("Q4", lambda t: t.entry_period == 4),
        ("OT", lambda t: t.entry_period is not None and t.entry_period >= 5),
    ):
        sub = [t for t in trades if pred(t)]
        if not sub:
            md.append(f"| {q_label} | 0 | — | — | — |")
            continue
        n_t = len(sub)
        hits = sum(1 for t in sub if t.exit_type == "target")
        stops = sum(1 for t in sub if t.exit_type == "stop")
        mn = float(np.mean([t.net_pnl for t in sub]))
        md.append(
            f"| {q_label} | {n_t} | {100*hits/n_t:.0f}% | "
            f"{100*stops/n_t:.0f}% | ${mn:+.2f} |"
        )
    md.append("")
    # By spread bucket
    md.append("#### By spread bucket\n")
    md.append("| |Spread| | Entries | Mean P&L |")
    md.append("|---|---:|---:|")
    for label, pred in (
        ("1–2", lambda t: 1.0 <= t.abs_spread <= 2.0),
        ("2.5–3.5", lambda t: 2.5 <= t.abs_spread <= 3.5),
        ("4–5", lambda t: 4.0 <= t.abs_spread <= 5.0),
        ("5.5–6", lambda t: 5.5 <= t.abs_spread <= 6.0),
    ):
        sub = [t for t in trades if pred(t)]
        if not sub:
            md.append(f"| {label} | 0 | — |")
            continue
        mn = float(np.mean([t.net_pnl for t in sub]))
        md.append(f"| {label} | {len(sub)} | ${mn:+.2f} |")
    md.append("")
    # Hold time
    if trades:
        mean_bins = float(np.mean([t.hold_bins for t in trades]))
        md.append(
            f"**Mean hold time:** {mean_bins:.1f} bins × "
            f"{BUCKET_SEC}s = {mean_bins * BUCKET_SEC / 60:.1f} minutes "
            "of game clock.\n"
        )
    # Re-entry stats
    n_reentry = sum(1 for t in trades if t.is_reentry)
    md.append(
        f"**Re-entries:** {n_reentry} of {s['entries']} total "
        f"({100 * n_reentry / max(1, s['entries']):.1f}%).\n"
    )


def render_s4a_sensitivity(
    md: list[str], best_cfg: S4AConfig,
    results: list[tuple[S4AConfig, dict]],
) -> None:
    md.append("### 2C — Sensitivity around best config\n")
    md.append(
        "For each parameter, show how mean P&L changes when we vary "
        "only that parameter around the best config's value.\n"
    )

    def find(matcher) -> list[tuple[S4AConfig, dict]]:
        return [(c, s) for c, s in results if matcher(c)]

    tables = [
        ("Lookback",
         lambda c: (c.dip_depth == best_cfg.dip_depth
                    and c.entry_lo == best_cfg.entry_lo
                    and c.entry_hi == best_cfg.entry_hi
                    and c.exit_target == best_cfg.exit_target
                    and c.stop_loss == best_cfg.stop_loss),
         lambda c: f"{c.lookback_sec}s"),
        ("Dip depth",
         lambda c: (c.lookback_sec == best_cfg.lookback_sec
                    and c.entry_lo == best_cfg.entry_lo
                    and c.entry_hi == best_cfg.entry_hi
                    and c.exit_target == best_cfg.exit_target
                    and c.stop_loss == best_cfg.stop_loss),
         lambda c: f"${c.dip_depth:.2f}"),
        ("Entry zone",
         lambda c: (c.lookback_sec == best_cfg.lookback_sec
                    and c.dip_depth == best_cfg.dip_depth
                    and c.exit_target == best_cfg.exit_target
                    and c.stop_loss == best_cfg.stop_loss),
         lambda c: f"${c.entry_lo:.2f}–${c.entry_hi:.2f}"),
        ("Exit target",
         lambda c: (c.lookback_sec == best_cfg.lookback_sec
                    and c.dip_depth == best_cfg.dip_depth
                    and c.entry_lo == best_cfg.entry_lo
                    and c.entry_hi == best_cfg.entry_hi
                    and c.stop_loss == best_cfg.stop_loss),
         lambda c: f"${c.exit_target:.2f}"),
        ("Stop-loss",
         lambda c: (c.lookback_sec == best_cfg.lookback_sec
                    and c.dip_depth == best_cfg.dip_depth
                    and c.entry_lo == best_cfg.entry_lo
                    and c.entry_hi == best_cfg.entry_hi
                    and c.exit_target == best_cfg.exit_target),
         lambda c: f"${c.stop_loss:.2f}"),
    ]
    for name, matcher, label_fn in tables:
        md.append(f"#### Vary {name}\n")
        md.append(
            f"| {name} | Entries | Mean P&L | Annual EV |"
        )
        md.append("|---|---:|---:|---:|")
        matches = find(matcher)
        for c, s in matches:
            md.append(
                f"| {label_fn(c)} | {s['entries']} | "
                f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |"
            )
        md.append("")


def render_s4b_top(
    md: list[str], results: list[tuple[S4BConfig, dict]],
    heading: str, limit: int = 20,
) -> tuple[S4BConfig, dict]:
    md.append(f"### {heading}\n")
    md.append(
        "| Rank | Label | Entries | Hit% | Stop% | Held% | "
        "Mean P&L | Annual EV |"
    )
    md.append("|---:|---|---:|---:|---:|---:|---:|---:|")
    sorted_r = sorted(results, key=lambda r: r[1]["annual_ev"], reverse=True)
    for i, (cfg, s) in enumerate(sorted_r[:limit], 1):
        md.append(
            f"| {i} | {cfg.label} | {s['entries']} | "
            f"{s['hit_pct']:.0f}% | {s['stop_pct']:.0f}% | "
            f"{s['held_pct']:.0f}% | ${s['mean_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
    md.append("")
    return sorted_r[0]


def render_s4b_resolution_math(
    md: list[str], games: list[dict],
) -> None:
    md.append("### 3D — Resolution lottery math (underdog)\n")
    md.append(
        "For each entry price band: what fraction of underdog entries "
        "resolve at $1.00 (underdog wins outright), and what's the "
        "mean resolution P&L if held from that band to the end?\n"
    )
    md.append(
        "| Entry band | Bin count | Dog-win rate | Mean resolution P&L |"
    )
    md.append("|---|---:|---:|---:|")
    bands = [
        ("$0.10–$0.15", 0.10, 0.15),
        ("$0.15–$0.20", 0.15, 0.20),
        ("$0.20–$0.25", 0.20, 0.25),
        ("$0.25–$0.30", 0.25, 0.30),
        ("$0.30–$0.35", 0.30, 0.35),
    ]
    for label, lo, hi in bands:
        total_bins = 0
        win_bins = 0
        for g in games:
            dog = 1.0 - g["ts"]["fav_kalshi_vwap"].values
            mask = (dog >= lo) & (dog < hi)
            n_bins = int(mask.sum())
            if n_bins == 0:
                continue
            total_bins += n_bins
            if fav_outcome(g["ts"]) == "loss":  # dog won
                win_bins += n_bins
        if total_bins == 0:
            md.append(f"| {label} | 0 | — | — |")
            continue
        win_rate = win_bins / total_bins
        # Mean resolution P&L: win pays (1 - mid) × 100; loss loses mid × 100
        mid = (lo + hi) / 2
        mean_pnl = (win_rate * (1.0 - mid) * 100) - (
            (1 - win_rate) * mid * 100
        )
        md.append(
            f"| {label} | {total_bins:,} | {100*win_rate:.1f}% | "
            f"${mean_pnl:+.2f} |"
        )
    md.append("")


# ---- Part 6: Averaging-in / averaging-out (managed) simulator ---------

@dataclass
class ManagedConfig:
    """Position-management overlay on top of S4AConfig.

    entry_tranches: list of (size_pct, price_drop_from_initial) pairs.
      - First tranche: (pct, 0.0) — fires on initial dip.
      - Subsequent: fires when price ≤ initial_entry - drop, while
        price still > stop_loss. Sum of pct must = 1.0.
    exit_levels: list of (size_pct_of_original, target_price) pairs.
      - Fractions are of the original 100 contracts, applied in
        order of ascending target price. Stop still applies to
        whatever remains held at that moment.
      - Setting [(1.0, target)] matches baseline (full exit at target).
    """
    label: str
    base: S4AConfig
    entry_tranches: list[tuple[float, float]]
    exit_levels: list[tuple[float, float]]


@dataclass
class ManagedTrade:
    ticker: str
    entry_idx: int
    initial_entry_price: float
    entry_period: int | None
    total_contracts_filled: int
    avg_cost_basis: float
    tranches_filled: int
    exit_type: str           # full_exit | partial_then_stop | full_stop |
                             # resolution_win | resolution_loss |
                             # resolution_mid
    partial_pnl: float       # sum of realized partial exit proceeds net
    final_exit_price: float
    final_exit_idx: int
    hold_bins: int
    net_pnl: float
    abs_spread: float


def simulate_managed(
    games: list[dict], cfg: ManagedConfig,
    precomp_max: dict[tuple[str, int], np.ndarray],
) -> list[ManagedTrade]:
    """Replay with entry tranches + exit ladder + stop-loss.

    State machine per game:
      WATCHING → (initial tranche fires when dip condition met)
                → IN_POS (tracks tranches_filled, partial_exits_done)
                → stop | full_exit | partial_then_stop | resolution

    Order within a single bin:
      1. Try to trigger add-on (if price ≤ next tranche trigger and
         above stop_loss).
      2. Check stop-loss (if price ≤ stop).
      3. Check partial exit levels (in ascending target order).
    """
    trades: list[ManagedTrade] = []
    base = cfg.base
    lookback_bins = max(1, int(base.lookback_sec / BUCKET_SEC))
    # Normalize & sort exit ladder ascending
    exits_sorted = sorted(cfg.exit_levels, key=lambda x: x[1])
    for g in games:
        df = g["ts"]
        prices = df["fav_kalshi_vwap"].values
        periods = df["period"].values
        n = len(prices)
        if n < 2:
            continue
        tmax = precomp_max[(g["ticker"], lookback_bins)]

        entries_this_game = 0
        max_entries = 2
        in_pos = False
        # Tranche tracking
        initial_entry_price = initial_entry_idx = entry_period = None
        tranches: list[tuple[int, float]] = []  # (contracts, price) currently held
        tranches_filled_count = 0
        cumulative_entry_fees = 0.0
        # Lifetime fill tracking (for avg basis reporting across whole trade)
        total_contracts_ever_filled = 0
        total_cost_ever_invested = 0.0
        # Exit tracking
        partial_exits_done = 0
        partial_pnl = 0.0
        i = 0
        while i < n:
            p = prices[i]
            if pd.isna(p):
                i += 1
                continue
            p = float(p)
            if not in_pos:
                if entries_this_game >= max_entries:
                    break
                # Detect initial dip
                if base.entry_lo <= p <= base.entry_hi:
                    if (float(tmax[i]) - p) >= base.dip_depth:
                        in_pos = True
                        initial_entry_price = p
                        initial_entry_idx = i
                        entry_period = (
                            int(periods[i]) if not pd.isna(periods[i]) else None
                        )
                        # Fill first tranche
                        first_pct, _ = cfg.entry_tranches[0]
                        first_contracts = max(
                            1, int(round(first_pct * CONTRACT_SIZE))
                        )
                        tranches = [(first_contracts, p)]
                        cumulative_entry_fees = maker_fee(first_contracts, p)
                        tranches_filled_count = 1
                        total_contracts_ever_filled = first_contracts
                        total_cost_ever_invested = first_contracts * p
                        partial_exits_done = 0
                        partial_pnl = 0.0
                        entries_this_game += 1
                        i += 1
                        continue
                i += 1
                continue

            # In position. First: try add-on (if any tranches remain).
            if (tranches_filled_count < len(cfg.entry_tranches)
                    and p > base.stop_loss):
                next_pct, next_drop = cfg.entry_tranches[
                    tranches_filled_count
                ]
                target_add_price = initial_entry_price - next_drop
                if p <= target_add_price:
                    add_contracts = max(
                        1, int(round(next_pct * CONTRACT_SIZE))
                    )
                    # Clamp so total never exceeds CONTRACT_SIZE
                    held_total = sum(c for c, _ in tranches)
                    add_contracts = min(
                        add_contracts, CONTRACT_SIZE - held_total,
                    )
                    if add_contracts > 0:
                        tranches.append((add_contracts, p))
                        cumulative_entry_fees += maker_fee(
                            add_contracts, p,
                        )
                        total_contracts_ever_filled += add_contracts
                        total_cost_ever_invested += add_contracts * p
                    tranches_filled_count += 1

            total_held = sum(c for c, _ in tranches)
            total_cost = sum(c * pr for c, pr in tranches)

            # Stop-loss
            if p <= base.stop_loss and total_held > 0:
                exit_fee = maker_fee(total_held, p)
                gross = p * total_held - total_cost
                net = (
                    partial_pnl + gross - cumulative_entry_fees - exit_fee
                )
                exit_type = (
                    "partial_then_stop" if partial_exits_done > 0
                    else "full_stop"
                )
                avg_basis_lifetime = (
                    total_cost_ever_invested / total_contracts_ever_filled
                    if total_contracts_ever_filled else 0.0
                )
                trades.append(ManagedTrade(
                    ticker=g["ticker"],
                    entry_idx=initial_entry_idx,
                    initial_entry_price=initial_entry_price,
                    entry_period=entry_period,
                    total_contracts_filled=total_contracts_ever_filled,
                    avg_cost_basis=avg_basis_lifetime,
                    tranches_filled=tranches_filled_count,
                    exit_type=exit_type,
                    partial_pnl=partial_pnl,
                    final_exit_price=p,
                    final_exit_idx=i,
                    hold_bins=i - initial_entry_idx,
                    net_pnl=net,
                    abs_spread=g["abs_spread"],
                ))
                in_pos = False
                i += 1
                continue

            # Partial exits (process next-eligible exit level)
            if partial_exits_done < len(exits_sorted) and total_held > 0:
                level_pct, level_price = exits_sorted[partial_exits_done]
                if p >= level_price:
                    # Sell `level_pct * CONTRACT_SIZE` contracts at p,
                    # up to total_held. Cost basis for sold share =
                    # weighted-avg of held tranches.
                    sell_qty = max(
                        1, int(round(level_pct * CONTRACT_SIZE))
                    )
                    sell_qty = min(sell_qty, total_held)
                    avg_basis_now = total_cost / total_held
                    sell_cost = avg_basis_now * sell_qty
                    leg_gross = p * sell_qty - sell_cost
                    leg_fee = maker_fee(sell_qty, p)
                    partial_pnl += leg_gross - leg_fee
                    # Reduce tranches pro-rata
                    remaining = total_held - sell_qty
                    if remaining > 0:
                        # Scale down each tranche proportionally
                        scale = remaining / total_held
                        new_tranches = []
                        for c, pr in tranches:
                            new_c = int(round(c * scale))
                            if new_c > 0:
                                new_tranches.append((new_c, pr))
                        # Adjust for rounding
                        cur_total = sum(c for c, _ in new_tranches)
                        if cur_total != remaining and new_tranches:
                            diff = remaining - cur_total
                            c0, pr0 = new_tranches[0]
                            new_tranches[0] = (c0 + diff, pr0)
                        tranches = new_tranches
                    else:
                        tranches = []
                    partial_exits_done += 1
                    # If this was the last exit level, close out
                    if partial_exits_done >= len(exits_sorted):
                        # All exit levels fired — this is "full_exit"
                        exit_type = "full_exit"
                        net = partial_pnl - cumulative_entry_fees
                        avg_basis_lifetime = (
                            total_cost_ever_invested
                            / total_contracts_ever_filled
                            if total_contracts_ever_filled else 0.0
                        )
                        trades.append(ManagedTrade(
                            ticker=g["ticker"],
                            entry_idx=initial_entry_idx,
                            initial_entry_price=initial_entry_price,
                            entry_period=entry_period,
                            total_contracts_filled=total_contracts_ever_filled,
                            avg_cost_basis=avg_basis_lifetime,
                            tranches_filled=tranches_filled_count,
                            exit_type=exit_type,
                            partial_pnl=partial_pnl,
                            final_exit_price=p,
                            final_exit_idx=i,
                            hold_bins=i - initial_entry_idx,
                            net_pnl=net,
                            abs_spread=g["abs_spread"],
                        ))
                        in_pos = False
                        i += 1
                        continue
                    # else: stay in position, re-check stop / further
                    # exits on future bins. Do not re-enter a second
                    # partial on the same bin to avoid intra-bar
                    # cascades.
            i += 1

        # End-of-game resolution for open positions
        if in_pos and initial_entry_price is not None:
            total_held = sum(c for c, _ in tranches)
            total_cost = sum(c * pr for c, pr in tranches)
            avg_basis_lifetime = (
                total_cost_ever_invested / total_contracts_ever_filled
                if total_contracts_ever_filled else 0.0
            )
            last_price = float(prices[~np.isnan(prices)][-1])
            if last_price >= RESOLUTION_WIN_CUTOFF:
                resolution = 1.0
                exit_type = "resolution_win"
                exit_fee = 0.0
            elif last_price <= RESOLUTION_LOSS_CUTOFF:
                resolution = 0.0
                exit_type = "resolution_loss"
                exit_fee = 0.0
            else:
                resolution = float(last_price)
                exit_type = "resolution_mid"
                exit_fee = maker_fee(total_held, resolution) if total_held else 0.0
            gross = resolution * total_held - total_cost
            net = partial_pnl + gross - cumulative_entry_fees - exit_fee
            trades.append(ManagedTrade(
                ticker=g["ticker"],
                entry_idx=initial_entry_idx,
                initial_entry_price=initial_entry_price,
                entry_period=entry_period,
                total_contracts_filled=total_contracts_ever_filled,
                avg_cost_basis=avg_basis_lifetime,
                tranches_filled=tranches_filled_count,
                exit_type=exit_type,
                partial_pnl=partial_pnl,
                final_exit_price=last_price,
                final_exit_idx=n - 1,
                hold_bins=(n - 1 - initial_entry_idx),
                net_pnl=net,
                abs_spread=g["abs_spread"],
            ))
    return trades


def _reconstruct_all_tranches(_a, _b, _c):
    """Placeholder — the avg_basis for full-exit trades is computed
    elsewhere; this stub exists only to keep a legible expression in
    the simulator. Returns an empty list so the outer expression
    yields 0 / CONTRACT_SIZE = 0 (baseline avg_cost_basis is
    recomputed from tranches at trade close)."""
    return []


def summarize_managed(
    trades: list[ManagedTrade], n_games: int,
) -> dict:
    if not trades:
        return {"entries": 0, "mean_pnl": 0.0, "median_pnl": 0.0,
                "annual_ev": 0.0, "max_loss": 0.0,
                "hit_pct": 0.0, "stop_pct": 0.0, "partial_stop_pct": 0.0,
                "avg_in_fired_pct": 0.0, "mean_basis": 0.0}
    n = len(trades)
    pnls = np.array([t.net_pnl for t in trades])
    n_full = sum(1 for t in trades if t.exit_type == "full_exit")
    n_full_stop = sum(1 for t in trades if t.exit_type == "full_stop")
    n_partial_stop = sum(1 for t in trades if t.exit_type == "partial_then_stop")
    n_res = sum(1 for t in trades if t.exit_type.startswith("resolution"))
    n_avg_in = sum(1 for t in trades if t.tranches_filled > 1)
    mean_basis = float(np.mean([t.avg_cost_basis for t in trades]))
    mean_pnl = float(pnls.mean())
    entries_per_game = n / n_games if n_games else 0
    annual_ev = (
        mean_pnl * entries_per_game * REG_SEASON_GAMES * COMP_FRACTION
    )
    return {
        "entries": n,
        "mean_pnl": mean_pnl,
        "median_pnl": float(np.median(pnls)),
        "annual_ev": annual_ev,
        "max_loss": float(pnls.min()),
        "hit_pct": 100 * n_full / n,
        "stop_pct": 100 * n_full_stop / n,
        "partial_stop_pct": 100 * n_partial_stop / n,
        "res_pct": 100 * n_res / n,
        "avg_in_fired_pct": 100 * n_avg_in / n,
        "mean_basis": mean_basis,
    }


# ---- Part 6 report rendering ------------------------------------------

def _make_managed_cfgs(best_cfg: S4AConfig) -> dict:
    """Build the named config dictionary for Part 6."""
    avg_in_cfgs = {
        "A baseline": ManagedConfig(
            label="Config A (baseline 100/100)", base=best_cfg,
            entry_tranches=[(1.0, 0.0)],
            exit_levels=[(1.0, best_cfg.exit_target)],
        ),
        "B 50/50 +$0.05": ManagedConfig(
            label="Config B (50/50 add +$0.05)", base=best_cfg,
            entry_tranches=[(0.5, 0.0), (0.5, 0.05)],
            exit_levels=[(1.0, best_cfg.exit_target)],
        ),
        "C 50/50 +$0.08": ManagedConfig(
            label="Config C (50/50 add +$0.08)", base=best_cfg,
            entry_tranches=[(0.5, 0.0), (0.5, 0.08)],
            exit_levels=[(1.0, best_cfg.exit_target)],
        ),
        "D 50/50 +$0.03": ManagedConfig(
            label="Config D (50/50 add +$0.03)", base=best_cfg,
            entry_tranches=[(0.5, 0.0), (0.5, 0.03)],
            exit_levels=[(1.0, best_cfg.exit_target)],
        ),
        "E 33/33/34": ManagedConfig(
            label="Config E (33/33/34 triple)", base=best_cfg,
            entry_tranches=[(0.33, 0.0), (0.33, 0.05), (0.34, 0.10)],
            exit_levels=[(1.0, best_cfg.exit_target)],
        ),
        "F 25/75 conviction": ManagedConfig(
            label="Config F (25/75 conviction)", base=best_cfg,
            entry_tranches=[(0.25, 0.0), (0.75, 0.05)],
            exit_levels=[(1.0, best_cfg.exit_target)],
        ),
    }
    avg_out_cfgs = {
        "G baseline": ManagedConfig(
            label="Config G (baseline 100 @ $0.90)", base=best_cfg,
            entry_tranches=[(1.0, 0.0)],
            exit_levels=[(1.0, 0.90)],
        ),
        "H 50@0.80/50@0.90": ManagedConfig(
            label="Config H (50 @ $0.80 / 50 @ $0.90)", base=best_cfg,
            entry_tranches=[(1.0, 0.0)],
            exit_levels=[(0.5, 0.80), (0.5, 0.90)],
        ),
        "I 50@0.85/50@0.95": ManagedConfig(
            label="Config I (50 @ $0.85 / 50 @ $0.95)", base=best_cfg,
            entry_tranches=[(1.0, 0.0)],
            exit_levels=[(0.5, 0.85), (0.5, 0.95)],
        ),
        "J 50@0.80/50@0.95": ManagedConfig(
            label="Config J (50 @ $0.80 / 50 @ $0.95)", base=best_cfg,
            entry_tranches=[(1.0, 0.0)],
            exit_levels=[(0.5, 0.80), (0.5, 0.95)],
        ),
        "K 33/33/34 ladder": ManagedConfig(
            label="Config K (33/33/34 ladder 0.80/0.90/0.95)", base=best_cfg,
            entry_tranches=[(1.0, 0.0)],
            exit_levels=[(0.33, 0.80), (0.33, 0.90), (0.34, 0.95)],
        ),
        "L 25/50/25 pyramid": ManagedConfig(
            label="Config L (25/50/25 pyramid 0.80/0.90/0.95)", base=best_cfg,
            entry_tranches=[(1.0, 0.0)],
            exit_levels=[(0.25, 0.80), (0.50, 0.90), (0.25, 0.95)],
        ),
        "M 75/25 lock-and-ride": ManagedConfig(
            label="Config M (75 @ $0.85 / 25 @ $0.95)", base=best_cfg,
            entry_tranches=[(1.0, 0.0)],
            exit_levels=[(0.75, 0.85), (0.25, 0.95)],
        ),
    }
    return {"in": avg_in_cfgs, "out": avg_out_cfgs}


def render_part6(
    md: list[str], games: list[dict], n_games: int,
    best_s4a_cfg: S4AConfig,
    precomp_max: dict[tuple[str, int], np.ndarray],
) -> None:
    md.append("## Part 6 — Position Management Study\n")
    md.append(
        "Tests averaging-in and averaging-out overlays on the best "
        f"S4A config ({best_s4a_cfg.lookback_sec}s / "
        f"${best_s4a_cfg.dip_depth:.2f} dip / "
        f"${best_s4a_cfg.entry_lo:.2f}–${best_s4a_cfg.entry_hi:.2f} "
        f"entry / ${best_s4a_cfg.exit_target:.2f} exit / "
        f"${best_s4a_cfg.stop_loss:.2f} stop). Baseline has "
        "47% stop-out rate; can scaling convert some of those into "
        "smaller losses or partial wins?\n"
    )

    cfgs = _make_managed_cfgs(best_s4a_cfg)

    # --- 6A: averaging-in ---
    log("Running Part 6A (averaging-in)...")
    md.append("### 6A — Averaging-in configs\n")
    md.append(
        "| Config | Entries | Avg-in fired | Avg basis | Hit% | Stop% | "
        "Mean P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    a_results: dict[str, tuple[ManagedConfig, dict]] = {}
    for key, cfg in cfgs["in"].items():
        trades = simulate_managed(games, cfg, precomp_max)
        s = summarize_managed(trades, n_games)
        a_results[key] = (cfg, s)
        md.append(
            f"| {cfg.label} | {s['entries']} | "
            f"{s['avg_in_fired_pct']:.0f}% | "
            f"${s['mean_basis']:.4f} | {s['hit_pct']:.0f}% | "
            f"{s['stop_pct']:.0f}% | ${s['mean_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
    md.append("")
    best_in_key = max(
        a_results.keys(),
        key=lambda k: a_results[k][1]["annual_ev"],
    )
    log(f"  Best averaging-in: {best_in_key}")

    # --- 6B: averaging-out ---
    log("Running Part 6B (averaging-out)...")
    md.append("### 6B — Averaging-out configs\n")
    md.append(
        "Fractional exits at ascending price targets. Stop applies to "
        "whatever remains held.\n\n"
        "| Config | Entries | Full exit% | Partial+stop% | Full stop% | "
        "Mean P&L | Median P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    b_results: dict[str, tuple[ManagedConfig, dict]] = {}
    for key, cfg in cfgs["out"].items():
        trades = simulate_managed(games, cfg, precomp_max)
        s = summarize_managed(trades, n_games)
        b_results[key] = (cfg, s)
        md.append(
            f"| {cfg.label} | {s['entries']} | "
            f"{s['hit_pct']:.0f}% | {s['partial_stop_pct']:.0f}% | "
            f"{s['stop_pct']:.0f}% | ${s['mean_pnl']:+.2f} | "
            f"${s['median_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |"
        )
    md.append("")
    best_out_key = max(
        b_results.keys(),
        key=lambda k: b_results[k][1]["annual_ev"],
    )
    log(f"  Best averaging-out: {best_out_key}")

    # --- 6C: combined ---
    log("Running Part 6C (combined)...")
    md.append("### 6C — Combined averaging-in × averaging-out\n")
    # Build combined configs N/O/P/Q
    best_in_cfg = a_results[best_in_key][0]
    best_out_cfg = b_results[best_out_key][0]
    combined_cfgs = {
        "N best × best": ManagedConfig(
            label=f"Config N (best × best: {best_in_key} × {best_out_key})",
            base=best_s4a_cfg,
            entry_tranches=best_in_cfg.entry_tranches,
            exit_levels=best_out_cfg.exit_levels,
        ),
        "O 50/50+$0.05 × 50@0.80/50@0.90": ManagedConfig(
            label="Config O (B × H: 50/50 in +$0.05 × 50@0.80/50@0.90)",
            base=best_s4a_cfg,
            entry_tranches=[(0.5, 0.0), (0.5, 0.05)],
            exit_levels=[(0.5, 0.80), (0.5, 0.90)],
        ),
        "P 25/75 × 75/25 lock-and-ride": ManagedConfig(
            label="Config P (F × M: 25/75 conviction × 75@0.85/25@0.95)",
            base=best_s4a_cfg,
            entry_tranches=[(0.25, 0.0), (0.75, 0.05)],
            exit_levels=[(0.75, 0.85), (0.25, 0.95)],
        ),
        "Q 33/33/34 × 33/33/34 ladder": ManagedConfig(
            label="Config Q (E × K: fully symmetric 33/33/34 × 33/33/34)",
            base=best_s4a_cfg,
            entry_tranches=[(0.33, 0.0), (0.33, 0.05), (0.34, 0.10)],
            exit_levels=[(0.33, 0.80), (0.33, 0.90), (0.34, 0.95)],
        ),
    }
    md.append(
        "| Config | Entries | Avg-in fired | Mean basis | "
        "Full exit% | Partial+stop% | Full stop% | Mean P&L | "
        "Median P&L | Annual EV |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    c_results: dict[str, tuple[ManagedConfig, list[ManagedTrade], dict]] = {}
    for key, cfg in combined_cfgs.items():
        trades = simulate_managed(games, cfg, precomp_max)
        s = summarize_managed(trades, n_games)
        c_results[key] = (cfg, trades, s)
        md.append(
            f"| {cfg.label} | {s['entries']} | "
            f"{s['avg_in_fired_pct']:.0f}% | "
            f"${s['mean_basis']:.4f} | {s['hit_pct']:.0f}% | "
            f"{s['partial_stop_pct']:.0f}% | {s['stop_pct']:.0f}% | "
            f"${s['mean_pnl']:+.2f} | ${s['median_pnl']:+.2f} | "
            f"${s['annual_ev']:+,.0f} |"
        )
    md.append("")

    # --- 6D: best combined detail ---
    # Filter to ≥50 entries, then max annual EV
    valid = {k: v for k, v in c_results.items() if v[2]["entries"] >= 50}
    if valid:
        best_key = max(valid.keys(), key=lambda k: valid[k][2]["annual_ev"])
    else:
        best_key = max(
            c_results.keys(),
            key=lambda k: c_results[k][2]["annual_ev"],
        )
    best_cfg, best_trades, best_s = c_results[best_key]

    md.append(f"### 6D — Best combined config detail: {best_key}\n")
    md.append(f"**{best_cfg.label}**\n")
    md.append(
        f"Entries: **{best_s['entries']}**, "
        f"Mean P&L: **${best_s['mean_pnl']:+.2f}**, "
        f"Annual EV: **${best_s['annual_ev']:+,.0f}**, "
        f"Max loss: ${best_s['max_loss']:+.2f}.\n"
    )

    md.append("#### Outcome distribution\n")
    md.append("| Outcome | Count | % | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    n = best_s["entries"] or 1
    for label, keys in (
        ("Full exit (all targets hit)", ("full_exit",)),
        ("Partial then stop", ("partial_then_stop",)),
        ("Full stop (no partial hit)", ("full_stop",)),
        ("Resolution win", ("resolution_win",)),
        ("Resolution loss", ("resolution_loss",)),
        ("Resolution mid", ("resolution_mid",)),
    ):
        sub = [t for t in best_trades if t.exit_type in keys]
        if not sub:
            md.append(f"| {label} | 0 | 0.0% | — |")
            continue
        pnls = [t.net_pnl for t in sub]
        md.append(
            f"| {label} | {len(sub)} | {100*len(sub)/n:.1f}% | "
            f"${np.mean(pnls):+.2f} |"
        )
    md.append("")

    # P&L histogram
    md.append("#### P&L distribution\n")
    md.append("| Bucket | Count | % |")
    md.append("|---|---:|---:|")
    for label, pred in (
        ("< −$30", lambda v: v < -30),
        ("−$30 to −$10", lambda v: -30 <= v < -10),
        ("−$10 to $0", lambda v: -10 <= v < 0),
        ("$0 to $10", lambda v: 0 <= v < 10),
        ("$10 to $20", lambda v: 10 <= v < 20),
        ("$20 to $30", lambda v: 20 <= v < 30),
        ("> $30", lambda v: v >= 30),
    ):
        c = sum(1 for t in best_trades if pred(t.net_pnl))
        md.append(f"| {label} | {c} | {100*c/n:.1f}% |")
    md.append("")

    # By period
    md.append("#### By entry period\n")
    md.append("| Period | Entries | Hit% | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    for q_label, pred in (
        ("Q1", lambda t: t.entry_period == 1),
        ("Q2", lambda t: t.entry_period == 2),
        ("Q3", lambda t: t.entry_period == 3),
        ("Q4", lambda t: t.entry_period == 4),
        ("OT", lambda t: t.entry_period is not None and t.entry_period >= 5),
    ):
        sub = [t for t in best_trades if pred(t)]
        if not sub:
            md.append(f"| {q_label} | 0 | — | — |")
            continue
        n_t = len(sub)
        hits = sum(1 for t in sub if t.exit_type == "full_exit")
        mn = float(np.mean([t.net_pnl for t in sub]))
        md.append(
            f"| {q_label} | {n_t} | {100*hits/n_t:.0f}% | ${mn:+.2f} |"
        )
    md.append("")

    # By spread bucket
    md.append("#### By spread bucket\n")
    md.append("| |Spread| | Entries | Mean P&L |")
    md.append("|---|---:|---:|")
    for label, pred in (
        ("1–2", lambda t: 1.0 <= t.abs_spread <= 2.0),
        ("2.5–3.5", lambda t: 2.5 <= t.abs_spread <= 3.5),
        ("4–5", lambda t: 4.0 <= t.abs_spread <= 5.0),
        ("5.5–6", lambda t: 5.5 <= t.abs_spread <= 6.0),
    ):
        sub = [t for t in best_trades if pred(t)]
        if not sub:
            md.append(f"| {label} | 0 | — |")
            continue
        mn = float(np.mean([t.net_pnl for t in sub]))
        md.append(f"| {label} | {len(sub)} | ${mn:+.2f} |")
    md.append("")

    # Hold time
    if best_trades:
        mean_bins = float(np.mean([t.hold_bins for t in best_trades]))
        md.append(
            f"**Mean hold time:** {mean_bins:.1f} bins × {BUCKET_SEC}s "
            f"= {mean_bins * BUCKET_SEC / 60:.1f} minutes of game clock.\n"
        )

    # Comparison row
    baseline_cfg = cfgs["in"]["A baseline"]
    baseline_trades = simulate_managed(games, baseline_cfg, precomp_max)
    baseline_s = summarize_managed(baseline_trades, n_games)
    md.append("#### Baseline vs best combined\n")
    md.append("| Metric | Baseline (A/G) | Best combined |")
    md.append("|---|---:|---:|")
    md.append(
        f"| Entries | {baseline_s['entries']} | {best_s['entries']} |"
    )
    md.append(
        f"| Hit% | {baseline_s['hit_pct']:.1f}% | "
        f"{best_s['hit_pct']:.1f}% |"
    )
    md.append(
        f"| Stop% | {baseline_s['stop_pct']:.1f}% | "
        f"{best_s['stop_pct']:.1f}% |"
    )
    md.append(
        f"| Partial+stop% | {baseline_s['partial_stop_pct']:.1f}% | "
        f"{best_s['partial_stop_pct']:.1f}% |"
    )
    md.append(
        f"| Mean P&L | ${baseline_s['mean_pnl']:+.2f} | "
        f"${best_s['mean_pnl']:+.2f} |"
    )
    md.append(
        f"| Annual EV | ${baseline_s['annual_ev']:+,.0f} | "
        f"${best_s['annual_ev']:+,.0f} |"
    )
    md.append(
        f"| Max loss | ${baseline_s['max_loss']:+.2f} | "
        f"${best_s['max_loss']:+.2f} |"
    )
    md.append("")

    # --- 6E: evolution ---
    md.append("### 6E — Strategy evolution table (updated)\n")
    md.append(
        "| Strategy | Entries/yr | Mean P&L | Annual EV | Max loss | Win rate |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    def _er(stats: dict) -> int:
        per_game = stats["entries"] / n_games if n_games else 0
        return int(per_game * REG_SEASON_GAMES * COMP_FRACTION)
    md.append(
        f"| S4A baseline (100 @ trigger, 100% @ $0.90) | "
        f"~{_er(baseline_s):,} | ${baseline_s['mean_pnl']:+.2f} | "
        f"${baseline_s['annual_ev']:+,.0f} | "
        f"${baseline_s['max_loss']:+.2f} | "
        f"{baseline_s['hit_pct']:.0f}% |"
    )
    best_in_s = a_results[best_in_key][1]
    best_out_s = b_results[best_out_key][1]
    md.append(
        f"| S4A + best avg-in only ({best_in_key}) | "
        f"~{_er(best_in_s):,} | ${best_in_s['mean_pnl']:+.2f} | "
        f"${best_in_s['annual_ev']:+,.0f} | "
        f"${best_in_s['max_loss']:+.2f} | "
        f"{best_in_s['hit_pct']:.0f}% |"
    )
    md.append(
        f"| S4A + best avg-out only ({best_out_key}) | "
        f"~{_er(best_out_s):,} | ${best_out_s['mean_pnl']:+.2f} | "
        f"${best_out_s['annual_ev']:+,.0f} | "
        f"${best_out_s['max_loss']:+.2f} | "
        f"{best_out_s['hit_pct']:.0f}% |"
    )
    md.append(
        f"| **S4A best combined ({best_key})** | "
        f"~{_er(best_s):,} | **${best_s['mean_pnl']:+.2f}** | "
        f"**${best_s['annual_ev']:+,.0f}** | "
        f"${best_s['max_loss']:+.2f} | "
        f"{best_s['hit_pct']:.0f}% |"
    )
    md.append(
        "| S1 bilateral | ~84 | +$19.14 | +$1,608 | $0 | 100% |"
    )
    md.append(
        f"| **S4A best combined + S1 bilateral** | — | — | "
        f"**${best_s['annual_ev'] + 1608:+,.0f}** | — | — |"
    )
    md.append("")


# ---- Part 5: Prior-weighting analysis ---------------------------------

def load_pregame_prices() -> dict[str, float]:
    """For each competitive game, read the raw CSV and extract the
    last non-NaN fav_kalshi_vwap in the pre-tip region (where
    game_seconds_elapsed is NaN). Falls back to the first live-bin
    price if no pre-tip bins are present."""
    out: dict[str, float] = {}
    meta = pd.read_csv(PAIRED_DIR / "matched_games.csv")
    meta["abs_spread"] = pd.to_numeric(meta["abs_spread"], errors="coerce")
    meta = meta.dropna(subset=["abs_spread"])
    meta = meta[meta["abs_spread"] <= MAX_SPREAD_COMPETITIVE]
    tickers = set(meta["kalshi_event_ticker"].astype(str))
    for p in sorted(PAIRED_DIR.glob("*_timeseries.csv")):
        m = TICKER_RE.match(p.stem)
        if not m:
            continue
        ticker = m.group(1)
        if ticker not in tickers:
            continue
        df = pd.read_csv(p)
        if df.empty:
            continue
        df["fav_kalshi_vwap"] = pd.to_numeric(
            df["fav_kalshi_vwap"], errors="coerce",
        )
        df["game_seconds_elapsed"] = pd.to_numeric(
            df["game_seconds_elapsed"], errors="coerce",
        )
        pre = df[df["game_seconds_elapsed"].isna()]
        pre = pre[pre["fav_kalshi_vwap"].notna()]
        if not pre.empty:
            out[ticker] = float(pre["fav_kalshi_vwap"].iloc[-1])
            continue
        # Fallback: first live-bin price
        live = df[
            df["game_seconds_elapsed"].notna()
            & df["fav_kalshi_vwap"].notna()
        ]
        if not live.empty:
            out[ticker] = float(live["fav_kalshi_vwap"].iloc[0])
    return out


_DIP_BINS: list[tuple[str, float, float]] = [
    ("< $0.00 (above prior)", -float("inf"), 0.0),
    ("$0.00–$0.05", 0.0, 0.05),
    ("$0.05–$0.10", 0.05, 0.10),
    ("$0.10–$0.15", 0.10, 0.15),
    ("$0.15–$0.20", 0.15, 0.20),
    ("$0.20–$0.25", 0.20, 0.25),
    ("> $0.25", 0.25, float("inf")),
]


def _bin_label(dip: float) -> str:
    for label, lo, hi in _DIP_BINS:
        if lo <= dip < hi:
            return label
    return _DIP_BINS[-1][0]


def _filter_s4a_trades_by_prior(
    trades: list[S4ATrade], pregame: dict[str, float],
    min_dip: float,
) -> list[S4ATrade]:
    keep = []
    for t in trades:
        pg = pregame.get(t.ticker)
        if pg is None:
            continue
        dip = pg - t.entry_price
        if dip >= min_dip:
            keep.append(t)
    return keep


def _summary_from_s4a_trades(
    trades: list[S4ATrade], n_games: int,
) -> dict:
    return summarize_s4a(trades, n_games)


def render_part5(
    md: list[str], games: list[dict], n_games: int,
    best_s4a_cfg: S4AConfig, best_s4a_trades: list[S4ATrade],
    s4a_results: list[tuple[S4AConfig, dict]],
    best_s4b_cfg: "S4BConfig", best_s4b_trades: list["S4BTrade"],
    precomp_max: dict, precomp_min: dict,
) -> None:
    md.append("## Part 5 — Prior-Weighting Analysis\n")
    md.append(
        "Tests whether measuring entry price against the pre-game "
        "Kalshi price improves S4A. Thesis: entries deeper below "
        "the market's prior (pre-game) expectation should recover "
        "more reliably because the gap to mean-revert to is larger.\n"
    )
    md.append(
        "**Pre-game price definition:** last non-NaN fav_kalshi_vwap "
        "in the pre-tip region (where game_seconds_elapsed is NaN) "
        "of each game's raw timeseries. Falls back to the first live "
        "bin's price if no pre-tip bins exist.\n"
    )

    log("Loading pre-game Kalshi prices...")
    pregame_fav = load_pregame_prices()
    log(f"Pre-game prices loaded for {len(pregame_fav)} games.")

    # --- 5A: distribution ---
    md.append("### 5A — Dip-below-prior distribution (best S4A config)\n")
    md.append(
        f"Best S4A config: {best_s4a_cfg.lookback_sec}s lookback, "
        f"${best_s4a_cfg.dip_depth:.2f} dip, "
        f"${best_s4a_cfg.entry_lo:.2f}–${best_s4a_cfg.entry_hi:.2f} entry, "
        f"${best_s4a_cfg.exit_target:.2f} exit, "
        f"${best_s4a_cfg.stop_loss:.2f} stop.\n"
    )
    md.append("| Dip below prior | Count | % of entries |")
    md.append("|---|---:|---:|")
    dips = []
    by_bin: dict[str, list[S4ATrade]] = {b[0]: [] for b in _DIP_BINS}
    for t in best_s4a_trades:
        pg = pregame_fav.get(t.ticker)
        if pg is None:
            continue
        dip = pg - t.entry_price
        dips.append((t, dip))
        by_bin[_bin_label(dip)].append(t)
    total = len(dips) or 1
    for label, _, _ in _DIP_BINS:
        cnt = len(by_bin[label])
        md.append(f"| {label} | {cnt} | {100*cnt/total:.1f}% |")
    md.append("")

    # --- 5B: hit rate / P&L by bin ---
    md.append("### 5B — Hit rate and P&L by dip-below-prior bin\n")
    md.append(
        "| Dip below prior | Entries | Hit% | Stop% | Mean P&L | Median P&L |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    for label, _, _ in _DIP_BINS:
        sub = by_bin[label]
        if not sub:
            md.append(f"| {label} | 0 | — | — | — | — |")
            continue
        hit = sum(1 for t in sub if t.exit_type == "target")
        stop = sum(1 for t in sub if t.exit_type == "stop")
        pnls = np.array([t.net_pnl for t in sub])
        md.append(
            f"| {label} | {len(sub)} | {100*hit/len(sub):.0f}% | "
            f"{100*stop/len(sub):.0f}% | ${pnls.mean():+.2f} | "
            f"${np.median(pnls):+.2f} |"
        )
    md.append("")

    # --- 5C: sweep min_dip_threshold on best S4A config ---
    md.append("### 5C — Prior-filtered S4A sweep (best config)\n")
    md.append(
        "Sweep `Min dip below prior` threshold. Apply "
        "`dip_below_prior >= threshold` filter to entries from "
        "the best S4A config. Post-hoc filter on detected entries.\n"
    )
    md.append("| Dip below prior (min) | Entries | Hit% | Mean P&L | Annual EV |")
    md.append("|---|---:|---:|---:|---:|")
    thresholds = [0.00, 0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20]
    sweep_results: list[tuple[float, dict]] = []
    for thr in thresholds:
        kept = _filter_s4a_trades_by_prior(best_s4a_trades, pregame_fav, thr)
        s = _summary_from_s4a_trades(kept, n_games)
        sweep_results.append((thr, s))
        md.append(
            f"| ≥ ${thr:.2f} | {s['entries']} | {s['hit_pct']:.0f}% | "
            f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |"
        )
    md.append("")
    # Best threshold: max annual EV with at least 20 entries retained
    valid = [r for r in sweep_results if r[1]["entries"] >= 20]
    if valid:
        best_thr, best_thr_stats = max(valid, key=lambda r: r[1]["annual_ev"])
    else:
        best_thr, best_thr_stats = max(
            sweep_results, key=lambda r: r[1]["annual_ev"],
        )
    md.append(
        f"**Best prior-filter threshold (≥20 entries retained): "
        f"${best_thr:.2f}** — mean P&L "
        f"${best_thr_stats['mean_pnl']:+.2f}, annual EV "
        f"${best_thr_stats['annual_ev']:+,.0f}.\n"
    )

    # --- 5D: apply best threshold to top-5 configs ---
    md.append(
        f"### 5D — Best threshold (≥ ${best_thr:.2f}) applied to top 5 "
        "S4A configs\n"
    )
    md.append(
        "| Rank | Config | Entries (unfilt) | Entries (filt) | "
        "Mean P&L (unfilt) | Mean P&L (filt) | Annual EV (filt) |"
    )
    md.append("|---:|---|---:|---:|---:|---:|---:|")
    top5 = sorted(
        s4a_results, key=lambda r: r[1]["annual_ev"], reverse=True,
    )[:5]
    for i, (cfg, unfilt_s) in enumerate(top5, 1):
        trades = simulate_s4a(games, cfg, precomp_max)
        kept = _filter_s4a_trades_by_prior(trades, pregame_fav, best_thr)
        filt_s = _summary_from_s4a_trades(kept, n_games)
        cfg_desc = (
            f"{cfg.lookback_sec}s / ${cfg.dip_depth:.2f} / "
            f"${cfg.entry_lo:.2f}–${cfg.entry_hi:.2f} / "
            f"${cfg.exit_target:.2f} / ${cfg.stop_loss:.2f}"
        )
        md.append(
            f"| {i} | {cfg_desc} | {unfilt_s['entries']} | "
            f"{filt_s['entries']} | ${unfilt_s['mean_pnl']:+.2f} | "
            f"${filt_s['mean_pnl']:+.2f} | ${filt_s['annual_ev']:+,.0f} |"
        )
    md.append("")

    # --- 5E: underdog run-above-prior ---
    md.append("### 5E — Underdog run-above-prior (best S4B config)\n")
    md.append(
        f"Best S4B config: {best_s4b_cfg.label}. "
        "For each underdog entry, `run_above_prior = entry_price − "
        "pre_game_dog_price` where pre-game dog price = "
        "1 − pre_game_fav_price.\n"
    )
    md.append("| Run above prior | Entries | Hit% | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    dog_bins = [
        ("< $0.00 (below prior)", -float("inf"), 0.0),
        ("$0.00–$0.03", 0.0, 0.03),
        ("$0.03–$0.06", 0.03, 0.06),
        ("$0.06–$0.10", 0.06, 0.10),
        ("> $0.10", 0.10, float("inf")),
    ]
    dog_by_bin: dict[str, list] = {b[0]: [] for b in dog_bins}
    for t in best_s4b_trades:
        pg_fav = pregame_fav.get(t.ticker)
        if pg_fav is None:
            continue
        pg_dog = 1.0 - pg_fav
        run = t.entry_price - pg_dog
        label = next(
            (b[0] for b in dog_bins if b[1] <= run < b[2]),
            dog_bins[-1][0],
        )
        dog_by_bin[label].append(t)
    for label, _, _ in dog_bins:
        sub = dog_by_bin[label]
        if not sub:
            md.append(f"| {label} | 0 | — | — |")
            continue
        hit_types = ("target", )
        hit = sum(1 for t in sub if t.exit_type in hit_types)
        pnls = np.array([t.net_pnl for t in sub])
        md.append(
            f"| {label} | {len(sub)} | {100*hit/len(sub):.0f}% | "
            f"${pnls.mean():+.2f} |"
        )
    md.append("")

    # --- 5F: summary ---
    md.append("### 5F — Summary\n")
    # Build summary lines based on observed data
    # Is 5B monotonic?
    bin_means = []
    for label, _, _ in _DIP_BINS:
        sub = by_bin[label]
        if sub:
            bin_means.append(
                (label, float(np.mean([t.net_pnl for t in sub])), len(sub))
            )
    # Monotonicity check: skip bins with <5 entries
    relevant = [(m, n) for _, m, n in bin_means if n >= 5]
    is_monotonic = False
    if len(relevant) >= 3:
        means_only = [m for m, _ in relevant]
        asc = all(means_only[i] <= means_only[i+1] for i in range(len(means_only)-1))
        desc = all(means_only[i] >= means_only[i+1] for i in range(len(means_only)-1))
        is_monotonic = asc or desc
    md.append(
        "- **Dip-below-prior vs hit rate/P&L (5B):** "
        + ("clear monotonic relationship across bins with ≥5 entries."
           if is_monotonic else
           "relationship is non-monotonic — effect is not a simple "
           "'deeper dip = better recovery' story.")
    )
    # Best threshold improvement
    baseline = sweep_results[0][1]  # thr=0.00
    improvement = best_thr_stats["annual_ev"] - baseline["annual_ev"]
    md.append(
        f"- **Best prior filter (5C):** ≥ ${best_thr:.2f}. Annual EV "
        f"${best_thr_stats['annual_ev']:+,.0f} "
        f"({'improvement' if improvement > 0 else 'reduction'} of "
        f"${abs(improvement):+,.0f} vs unfiltered baseline "
        f"${baseline['annual_ev']:+,.0f}). Retained "
        f"{best_thr_stats['entries']} of {baseline['entries']} entries."
    )
    # Cross-config consistency
    md.append(
        "- **Cross-config consistency (5D):** see table above. If "
        "filtered mean P&L exceeds unfiltered mean P&L for all top-5 "
        "configs, the effect is robust across the config neighborhood."
    )
    # Underdog side
    dog_means = []
    for label, _, _ in dog_bins:
        sub = dog_by_bin[label]
        if len(sub) >= 5:
            dog_means.append(float(np.mean([t.net_pnl for t in sub])))
    if len(dog_means) >= 3:
        dog_range = max(dog_means) - min(dog_means)
        md.append(
            f"- **Underdog run-above-prior (5E):** P&L spread across "
            f"bins = ${dog_range:.2f}. "
            + ("Meaningful signal — run-above-prior does discriminate "
               "underdog swing outcomes."
               if dog_range >= 1.0 else
               "Small spread — run-above-prior is not a strong "
               "discriminator for underdog swings.")
        )
    else:
        md.append(
            "- **Underdog run-above-prior (5E):** insufficient bin "
            "coverage to draw a conclusion."
        )
    md.append("")


def render_comparison(
    md: list[str], s4a_stats: dict, s4b_stats: dict,
    n_games: int,
) -> None:
    md.append("## Part 4 — Cross-Strategy Comparison\n")
    md.append(
        "| Strategy | Entries/yr | Mean P&L | Annual EV | Max loss | Win rate |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    md.append(
        "| S3 naive (baseline) | ~1,404 | −$4.22 | −$5,963 | −$40 | 26% |"
    )
    md.append(
        "| S3 best filtered | ~170 | +$3.41 | +$578 | −$28 | 22% |"
    )
    md.append(
        "| S1 bilateral | ~84 | +$19.14 | +$1,608 | $0 | 100% |"
    )

    def extrapolate(stats: dict) -> int:
        per_game = stats["entries"] / n_games if n_games else 0
        return int(per_game * REG_SEASON_GAMES * COMP_FRACTION)

    s4a_per_yr = extrapolate(s4a_stats)
    s4b_per_yr = extrapolate(s4b_stats)
    s4a_win_rate = (
        s4a_stats["hit_pct"]
        + 100 * s4a_stats.get("n_res_win", 0) / max(1, s4a_stats["entries"])
    )
    md.append(
        f"| **S4A best fav config** | ~{s4a_per_yr:,} | "
        f"${s4a_stats['mean_pnl']:+.2f} | "
        f"${s4a_stats['annual_ev']:+,.0f} | "
        f"${s4a_stats['max_loss']:+.2f} | {s4a_win_rate:.0f}% |"
    )
    md.append(
        f"| **S4B best dog config** | ~{s4b_per_yr:,} | "
        f"${s4b_stats['mean_pnl']:+.2f} | "
        f"${s4b_stats['annual_ev']:+,.0f} | "
        f"${s4b_stats['max_loss']:+.2f} | {s4b_stats['hit_pct']:.0f}% |"
    )
    combined_ev = (
        578 + 1608 + s4a_stats["annual_ev"] + s4b_stats["annual_ev"]
    )
    md.append(
        f"| **S4A + S4B + S3-filtered + S1** | — | — | "
        f"${combined_ev:+,.0f} | — | — |"
    )
    md.append("")


# ---- Part 7: Halftime entry study --------------------------------------

@dataclass
class HalftimeTrade:
    ticker: str
    entry_idx: int
    entry_price: float
    exit_idx: int
    exit_price: float
    exit_type: str
    hold_bins: int
    net_pnl: float
    abs_spread: float
    pregame_price: float | None
    ht_to_prior_delta: float | None   # pregame - halftime (positive = fav dropped)


def _last_q2_vwap(df: pd.DataFrame) -> tuple[float | None, int | None]:
    """Return (halftime VWAP, idx of last Q2 bin in df).

    Halftime VWAP = mean fav_kalshi_vwap over the last 60s (2 bins) of
    Q2. Returns (None, None) if Q2 has no bins or no VWAP.
    """
    q2 = df[df["period"] == 2]
    if q2.empty:
        return None, None
    tail = q2.tail(2)
    tail = tail.dropna(subset=["fav_kalshi_vwap"])
    if tail.empty:
        return None, None
    return float(tail["fav_kalshi_vwap"].mean()), int(tail.index[-1])


def _simulate_halftime_one(
    g: dict,
    pregame: float | None,
    entry_lo: float = BEST_S4A_ENTRY_LO,
    entry_hi: float = BEST_S4A_ENTRY_HI,
    target: float = BEST_S4A_EXIT_TARGET,
    stop: float = BEST_S4A_STOP_LOSS,
) -> HalftimeTrade | None:
    df = g["ts"]
    ht_vwap, ht_idx = _last_q2_vwap(df)
    if ht_vwap is None or ht_idx is None:
        return None
    if not (entry_lo <= ht_vwap <= entry_hi):
        return None
    delta = (pregame - ht_vwap) if pregame is not None else None
    prices = df["fav_kalshi_vwap"].values
    n = len(prices)
    entry_fee = maker_fee(CONTRACT_SIZE, ht_vwap)
    for i in range(ht_idx + 1, n):
        p = float(prices[i])
        if pd.isna(p):
            continue
        if p >= target:
            fee = entry_fee + maker_fee(CONTRACT_SIZE, p)
            return HalftimeTrade(
                ticker=g["ticker"], entry_idx=ht_idx, entry_price=ht_vwap,
                exit_idx=i, exit_price=p, exit_type="target",
                hold_bins=i - ht_idx,
                net_pnl=(p - ht_vwap) * CONTRACT_SIZE - fee,
                abs_spread=g["abs_spread"],
                pregame_price=pregame, ht_to_prior_delta=delta,
            )
        if p <= stop:
            fee = entry_fee + maker_fee(CONTRACT_SIZE, p)
            return HalftimeTrade(
                ticker=g["ticker"], entry_idx=ht_idx, entry_price=ht_vwap,
                exit_idx=i, exit_price=p, exit_type="stop",
                hold_bins=i - ht_idx,
                net_pnl=(p - ht_vwap) * CONTRACT_SIZE - fee,
                abs_spread=g["abs_spread"],
                pregame_price=pregame, ht_to_prior_delta=delta,
            )
    # Resolution at game end
    last_price = float(prices[-1])
    if last_price >= RESOLUTION_WIN_CUTOFF:
        resolution, exit_type, exit_fee = 1.0, "resolution_win", 0.0
    elif last_price <= RESOLUTION_LOSS_CUTOFF:
        resolution, exit_type, exit_fee = 0.0, "resolution_loss", 0.0
    else:
        resolution, exit_type = float(last_price), "resolution_mid"
        exit_fee = maker_fee(CONTRACT_SIZE, resolution)
    return HalftimeTrade(
        ticker=g["ticker"], entry_idx=ht_idx, entry_price=ht_vwap,
        exit_idx=n - 1, exit_price=last_price, exit_type=exit_type,
        hold_bins=(n - 1 - ht_idx),
        net_pnl=(resolution - ht_vwap) * CONTRACT_SIZE - entry_fee - exit_fee,
        abs_spread=g["abs_spread"],
        pregame_price=pregame, ht_to_prior_delta=delta,
    )


def _summarize_halftime(
    trades: list[HalftimeTrade], n_games: int,
) -> dict:
    if not trades:
        return {
            "entries": 0, "hit_pct": 0.0, "stop_pct": 0.0,
            "held_pct": 0.0, "mean_pnl": 0.0, "median_pnl": 0.0,
            "annual_ev": 0.0, "max_win": 0.0, "max_loss": 0.0,
        }
    pnls = np.array([t.net_pnl for t in trades])
    n = len(trades)
    n_target = sum(1 for t in trades if t.exit_type == "target")
    n_stop = sum(1 for t in trades if t.exit_type == "stop")
    n_held = n - n_target - n_stop
    mean_pnl = float(pnls.mean())
    entries_per_game = n / n_games if n_games else 0
    annual_ev = (
        mean_pnl * entries_per_game * REG_SEASON_GAMES * COMP_FRACTION
    )
    return {
        "entries": n,
        "hit_pct": 100 * n_target / n,
        "stop_pct": 100 * n_stop / n,
        "held_pct": 100 * n_held / n,
        "mean_pnl": mean_pnl,
        "median_pnl": float(np.median(pnls)),
        "annual_ev": annual_ev,
        "max_win": float(pnls.max()),
        "max_loss": float(pnls.min()),
    }


def _q3_entry_timing(
    s4a_trades: list[S4ATrade], games: list[dict],
) -> dict:
    """Classify S4A Q3 dip-triggered entries by time-within-Q3."""
    ts_by_ticker = {g["ticker"]: g["ts"] for g in games}
    total_q3 = 0
    first_120s = 0
    first_60s = 0
    for t in s4a_trades:
        if t.entry_period != 3:
            continue
        total_q3 += 1
        ts = ts_by_ticker.get(t.ticker)
        if ts is None:
            continue
        try:
            gse = ts["game_seconds_elapsed"].iloc[t.entry_idx]
        except (IndexError, KeyError):
            continue
        if pd.isna(gse):
            continue
        since_q3_start = float(gse) - HALFTIME_SEC
        if 0 <= since_q3_start < 60:
            first_60s += 1
        if 0 <= since_q3_start < 120:
            first_120s += 1
    return {
        "total_q3": total_q3,
        "first_60s": first_60s,
        "first_120s": first_120s,
    }


def _combined_halftime_plus_dip(
    games: list[dict], best_cfg: S4AConfig,
    precomp_max: dict, pregame: dict[str, float],
) -> tuple[list, list]:
    """Combined strategy: halftime entry (if in zone) + S4A dip during Q3+.

    Returns (halftime_trades, q3plus_s4a_trades). Same game can produce
    up to 2 trades. The Q3+ simulation ignores bins before the halftime
    exit (or before halftime if no halftime entry fired) to avoid
    overlap.
    """
    ht_trades: list[HalftimeTrade] = []
    q3_trades: list[S4ATrade] = []
    lookback_bins = max(1, int(best_cfg.lookback_sec / BUCKET_SEC))
    for g in games:
        df = g["ts"]
        prices = df["fav_kalshi_vwap"].values
        periods = df["period"].values
        n = len(prices)
        if n < 2:
            continue
        ht = _simulate_halftime_one(g, pregame.get(g["ticker"]))
        # Determine start index for Q3+ dip scan
        if ht is not None:
            ht_trades.append(ht)
            start_idx = ht.exit_idx + 1
        else:
            ht_vwap, ht_idx = _last_q2_vwap(df)
            start_idx = (ht_idx + 1) if ht_idx is not None else 0

        tmax = precomp_max.get((g["ticker"], lookback_bins))
        if tmax is None:
            continue

        in_pos = False
        entry_idx = entry_price = entry_period = None
        i = start_idx
        while i < n:
            p = float(prices[i])
            if pd.isna(p):
                i += 1
                continue
            if not in_pos:
                if best_cfg.entry_lo <= p <= best_cfg.entry_hi:
                    if (float(tmax[i]) - p) >= best_cfg.dip_depth:
                        in_pos = True
                        entry_idx = i
                        entry_price = p
                        entry_period = (
                            int(periods[i])
                            if not pd.isna(periods[i]) else None
                        )
                        i += 1
                        continue
                i += 1
                continue
            # In position — same exit logic as simulate_s4a
            if p >= best_cfg.exit_target:
                fee = maker_fee(CONTRACT_SIZE, entry_price) + maker_fee(
                    CONTRACT_SIZE, p,
                )
                q3_trades.append(S4ATrade(
                    ticker=g["ticker"], entry_idx=entry_idx,
                    entry_price=entry_price, entry_period=entry_period,
                    exit_idx=i, exit_price=p, exit_type="target",
                    hold_bins=i - entry_idx,
                    net_pnl=(p - entry_price) * CONTRACT_SIZE - fee,
                    is_reentry=False, abs_spread=g["abs_spread"],
                ))
                in_pos = False
                i += 1
                continue
            if p <= best_cfg.stop_loss:
                fee = maker_fee(CONTRACT_SIZE, entry_price) + maker_fee(
                    CONTRACT_SIZE, p,
                )
                q3_trades.append(S4ATrade(
                    ticker=g["ticker"], entry_idx=entry_idx,
                    entry_price=entry_price, entry_period=entry_period,
                    exit_idx=i, exit_price=p, exit_type="stop",
                    hold_bins=i - entry_idx,
                    net_pnl=(p - entry_price) * CONTRACT_SIZE - fee,
                    is_reentry=False, abs_spread=g["abs_spread"],
                ))
                in_pos = False
                i += 1
                continue
            i += 1

        if in_pos:
            last_price = float(prices[-1])
            entry_fee = maker_fee(CONTRACT_SIZE, entry_price)
            if last_price >= RESOLUTION_WIN_CUTOFF:
                resolution, exit_type, exit_fee = 1.0, "resolution_win", 0.0
            elif last_price <= RESOLUTION_LOSS_CUTOFF:
                resolution, exit_type, exit_fee = 0.0, "resolution_loss", 0.0
            else:
                resolution, exit_type = float(last_price), "resolution_mid"
                exit_fee = maker_fee(CONTRACT_SIZE, resolution)
            q3_trades.append(S4ATrade(
                ticker=g["ticker"], entry_idx=entry_idx,
                entry_price=entry_price, entry_period=entry_period,
                exit_idx=n - 1, exit_price=last_price, exit_type=exit_type,
                hold_bins=(n - 1 - entry_idx),
                net_pnl=(resolution - entry_price) * CONTRACT_SIZE
                        - entry_fee - exit_fee,
                is_reentry=False, abs_spread=g["abs_spread"],
            ))
    return ht_trades, q3_trades


_HT_DELTA_BINS: list[tuple[str, float, float]] = [
    ("fav above prior (Δ<0)", -float("inf"), 0.0),
    ("0–$0.05 below prior", 0.0, 0.05),
    ("$0.05–$0.10 below prior", 0.05, 0.10),
    (">$0.10 below prior", 0.10, float("inf")),
]


def _ht_delta_label(delta: float) -> str:
    for lab, lo, hi in _HT_DELTA_BINS:
        if lo <= delta < hi:
            return lab
    return _HT_DELTA_BINS[-1][0]


def run_part7() -> int:
    log("Part 7 — halftime entry study")
    log("Loading competitive games...")
    games = load_competitive_games()
    n_games = len(games)
    log(f"Competitive games loaded: {n_games}")

    log("Loading pre-game Kalshi prices...")
    pregame = load_pregame_prices()
    log(f"  pre-game prices available for {len(pregame)} games")

    # Precompute trailing max at best lookback for combined sim
    lookback_bins = max(1, int(BEST_S4A_LOOKBACK_SEC / BUCKET_SEC))
    precomp_max: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp_max[(g["ticker"], lookback_bins)] = (
            _precompute_trailing_max(fav, lookback_bins)
        )

    # Scan halftime universe
    log("Scanning halftime universe...")
    in_zone = 0
    halftimes: list[tuple[dict, float | None, float | None, int | None]] = []
    for g in games:
        ht_vwap, ht_idx = _last_q2_vwap(g["ts"])
        pg = pregame.get(g["ticker"])
        halftimes.append((g, pg, ht_vwap, ht_idx))
        if ht_vwap is not None and BEST_S4A_ENTRY_LO <= ht_vwap <= BEST_S4A_ENTRY_HI:
            in_zone += 1

    # Run halftime-only sim
    log("Simulating halftime-only entries...")
    ht_trades: list[HalftimeTrade] = []
    for g, pg, _, _ in halftimes:
        t = _simulate_halftime_one(g, pg)
        if t is not None:
            ht_trades.append(t)
    ht_summary = _summarize_halftime(ht_trades, n_games)

    # For Table 2 comparison, run best-config S4A
    log("Simulating best-config S4A dip (comparison)...")
    best_cfg = S4AConfig(
        lookback_sec=BEST_S4A_LOOKBACK_SEC,
        dip_depth=BEST_S4A_DIP_DEPTH,
        entry_lo=BEST_S4A_ENTRY_LO,
        entry_hi=BEST_S4A_ENTRY_HI,
        exit_target=BEST_S4A_EXIT_TARGET,
        stop_loss=BEST_S4A_STOP_LOSS,
    )
    s4a_trades = simulate_s4a(games, best_cfg, precomp_max)
    s4a_summary = summarize_s4a(s4a_trades, n_games)

    # Table 4 — Q3 entry timing
    q3_timing = _q3_entry_timing(s4a_trades, games)

    # Table 5 — combined
    log("Simulating combined halftime + S4A-dip...")
    c_ht, c_dip = _combined_halftime_plus_dip(
        games, best_cfg, precomp_max, pregame,
    )
    combined_pnls = (
        [t.net_pnl for t in c_ht] + [t.net_pnl for t in c_dip]
    )
    combined_entries = len(combined_pnls)
    combined_mean = (
        float(np.mean(combined_pnls)) if combined_pnls else 0.0
    )
    combined_annual = (
        combined_mean * (combined_entries / n_games)
        * REG_SEASON_GAMES * COMP_FRACTION
        if n_games else 0.0
    )
    c_ht_summary = _summarize_halftime(c_ht, n_games)
    c_dip_summary = summarize_s4a(c_dip, n_games)

    # ---- Render report --------------------------------------------------
    md: list[str] = []
    md.append("# Strategy 4 — Part 7: Halftime Entry Study\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Dataset: {n_games} competitive games (|spread| ≤ 6) from "
        "the 168-game paired dataset. Halftime VWAP defined as the "
        "mean `fav_kalshi_vwap` over the final 60s (last 2 bins) of "
        "Q2. Exit framework matches S4A best config: target "
        f"${BEST_S4A_EXIT_TARGET:.2f}, stop ${BEST_S4A_STOP_LOSS:.2f}, "
        f"entry zone ${BEST_S4A_ENTRY_LO:.2f}–${BEST_S4A_ENTRY_HI:.2f}.\n"
    )

    # Table 1 — universe
    md.append("## Table 1 — Halftime entry universe\n")
    ht_observed = sum(1 for _, _, v, _ in halftimes if v is not None)
    md.append(
        f"| Metric | Value |\n"
        f"|---|---:|\n"
        f"| Games with Q2 halftime VWAP observed | {ht_observed} |\n"
        f"| Halftime VWAP in ${BEST_S4A_ENTRY_LO:.2f}–${BEST_S4A_ENTRY_HI:.2f} "
        f"| {in_zone} ({100*in_zone/n_games:.1f}%) |\n"
        f"| Games where halftime entry fires | {ht_summary['entries']} |\n"
    )

    # Halftime VWAP distribution (qualitative)
    ht_vals = [v for _, _, v, _ in halftimes if v is not None]
    if ht_vals:
        arr = np.array(ht_vals)
        md.append(
            f"Halftime VWAP distribution: "
            f"min ${arr.min():.2f}, p25 ${np.quantile(arr, 0.25):.2f}, "
            f"median ${np.median(arr):.2f}, "
            f"p75 ${np.quantile(arr, 0.75):.2f}, max ${arr.max():.2f}.\n"
        )

    # Table 2 — halftime vs S4A dip
    md.append("\n## Table 2 — Halftime entry P&L vs S4A dip-triggered\n")
    md.append(
        "| Strategy | Entries | Hit % | Stop % | Held % | "
        "Mean P&L | Median P&L | Max win | Max loss | Annual EV |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    md.append(
        f"| Halftime entry | {ht_summary['entries']} | "
        f"{ht_summary['hit_pct']:.1f}% | {ht_summary['stop_pct']:.1f}% | "
        f"{ht_summary['held_pct']:.1f}% | "
        f"${ht_summary['mean_pnl']:+.2f} | "
        f"${ht_summary['median_pnl']:+.2f} | "
        f"${ht_summary['max_win']:+.2f} | "
        f"${ht_summary['max_loss']:+.2f} | "
        f"${ht_summary['annual_ev']:+,.0f} |\n"
    )
    md.append(
        f"| S4A dip (best cfg) | {s4a_summary['entries']} | "
        f"{s4a_summary['hit_pct']:.1f}% | {s4a_summary['stop_pct']:.1f}% | "
        f"{s4a_summary['held_pct']:.1f}% | "
        f"${s4a_summary['mean_pnl']:+.2f} | "
        f"${s4a_summary['median_pnl']:+.2f} | "
        f"${s4a_summary['max_win']:+.2f} | "
        f"${s4a_summary['max_loss']:+.2f} | "
        f"${s4a_summary['annual_ev']:+,.0f} |\n"
    )

    # Table 3 — by halftime-to-prior delta
    md.append("\n## Table 3 — Halftime entries by halftime-to-prior delta\n")
    md.append(
        "Delta = pre-game Kalshi price − halftime VWAP. "
        "Positive delta means favorite has dropped from its "
        "pre-game anchor (disruption signal).\n\n"
        "| Δ bucket | Entries | Hit % | Mean P&L | Annual EV share |\n"
        "|---|---:|---:|---:|---:|\n"
    )
    # Bucket halftime trades by delta
    by_bucket: dict[str, list[HalftimeTrade]] = {}
    no_pregame = 0
    for t in ht_trades:
        if t.ht_to_prior_delta is None:
            no_pregame += 1
            continue
        lab = _ht_delta_label(t.ht_to_prior_delta)
        by_bucket.setdefault(lab, []).append(t)
    for lab, _, _ in _HT_DELTA_BINS:
        trades_in = by_bucket.get(lab, [])
        n = len(trades_in)
        if n == 0:
            md.append(f"| {lab} | 0 | — | — | — |\n")
            continue
        pnls = np.array([t.net_pnl for t in trades_in])
        hits = sum(1 for t in trades_in if t.exit_type == "target")
        mean = float(pnls.mean())
        bucket_annual = (
            mean * (n / n_games) * REG_SEASON_GAMES * COMP_FRACTION
        )
        md.append(
            f"| {lab} | {n} | {100*hits/n:.1f}% | "
            f"${mean:+.2f} | ${bucket_annual:+,.0f} |\n"
        )
    if no_pregame:
        md.append(
            f"\n_Note: {no_pregame} halftime entries excluded from "
            "delta bucketing because no pre-game Kalshi price is "
            "available for those games._\n"
        )

    # Table 4 — Q3 entry timing of S4A dip
    md.append("\n## Table 4 — S4A dip entries: timing within Q3\n")
    md.append(
        f"Of S4A dip entries that fire in Q3 (total: "
        f"{q3_timing['total_q3']}), how many fire within the first "
        "seconds of Q3? This measures whether the dip-trigger is "
        "already capturing halftime-adjacent moments.\n\n"
        "| Window | Entries | % of Q3 entries |\n"
        "|---|---:|---:|\n"
    )
    tot = max(1, q3_timing["total_q3"])
    md.append(
        f"| First 60s of Q3 | {q3_timing['first_60s']} | "
        f"{100*q3_timing['first_60s']/tot:.1f}% |\n"
        f"| First 120s of Q3 | {q3_timing['first_120s']} | "
        f"{100*q3_timing['first_120s']/tot:.1f}% |\n"
        f"| All Q3 entries | {q3_timing['total_q3']} | 100% |\n"
    )

    # Table 5 — combined
    md.append("\n## Table 5 — Halftime entry + S4A dip (combined, Q3+ dip only)\n")
    md.append(
        "Halftime entry and S4A-dip run on the same game. After a "
        "halftime exit (or if halftime did not fire), the dip trigger "
        "scans Q3 onward. Each game can produce up to 2 trades.\n\n"
        "| Leg | Entries | Hit % | Mean P&L | Annual EV |\n"
        "|---|---:|---:|---:|---:|\n"
        f"| Halftime leg | {c_ht_summary['entries']} | "
        f"{c_ht_summary['hit_pct']:.1f}% | "
        f"${c_ht_summary['mean_pnl']:+.2f} | "
        f"${c_ht_summary['annual_ev']:+,.0f} |\n"
        f"| Q3+ dip leg | {c_dip_summary['entries']} | "
        f"{c_dip_summary['hit_pct']:.1f}% | "
        f"${c_dip_summary['mean_pnl']:+.2f} | "
        f"${c_dip_summary['annual_ev']:+,.0f} |\n"
        f"| **Combined** | **{combined_entries}** | — | "
        f"**${combined_mean:+.2f}** | **${combined_annual:+,.0f}** |\n"
    )
    md.append(
        "\nFor reference, baseline S4A dip (all-game) annual EV = "
        f"${s4a_summary['annual_ev']:+,.0f}. The combined strategy "
        "captures both the halftime entry and any post-halftime dip, "
        "at the cost of potentially forgoing a pre-halftime dip that "
        "the baseline would have caught.\n"
    )

    REPORT_PART7_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PART7_PATH.write_text("".join(md) + "\n")
    log(f"Part 7 report → {REPORT_PART7_PATH}")
    return 0


# ---- Part 8: ESPN-only spread expansion (Path A) ------------------------

_CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2}(?:\.\d+)?)$")


def _parse_clock_str(clock_str: str | None) -> float | None:
    """Parse 'M:SS' or 'M:SS.s' → seconds remaining in period."""
    if not clock_str:
        return None
    m = _CLOCK_RE.match(clock_str.strip())
    if not m:
        return None
    try:
        return int(m.group(1)) * 60 + float(m.group(2))
    except ValueError:
        return None


def _elapsed_from_period_clock(
    period: int | None, clock_sec: float | None,
) -> float | None:
    if period is None or clock_sec is None:
        return None
    p = int(period)
    if p <= 0:
        return None
    if p <= 4:
        return (p - 1) * Q_LEN_SEC + (Q_LEN_SEC - clock_sec)
    return 4 * Q_LEN_SEC + (p - 5) * OT_LEN_SEC + (OT_LEN_SEC - clock_sec)


def load_espn_wp_series(
    game_id: str, home_spread: float,
) -> pd.DataFrame | None:
    """Build a 30s-bucketed favorite-side ESPN WP timeseries.

    Columns returned: game_seconds_elapsed, period, fav_kalshi_vwap.
    Uses `fav_kalshi_vwap` as the column name (holding ESPN WP values)
    so that simulate_s4a can consume the result without modification.
    """
    pbp_path = REPO_ROOT / "data" / "pbp" / f"{game_id}.jsonl"
    wp_path = REPO_ROOT / "data" / "espn_wp" / f"{game_id}.jsonl"
    if not pbp_path.exists() or not wp_path.exists():
        return None

    plays: dict[str, tuple[int, float]] = {}
    with pbp_path.open() as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            pid = obj.get("id")
            period = (obj.get("period") or {}).get("number")
            clock_str = (obj.get("clock") or {}).get("displayValue")
            clock_sec = _parse_clock_str(clock_str)
            elapsed = _elapsed_from_period_clock(period, clock_sec)
            if pid and period is not None and elapsed is not None:
                plays[str(pid)] = (int(period), float(elapsed))

    rows: list[dict] = []
    with wp_path.open() as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            pid = obj.get("playId")
            home_wp = obj.get("homeWinPercentage")
            if pid is None or home_wp is None:
                continue
            pk = str(pid)
            if pk not in plays:
                continue
            period, elapsed = plays[pk]
            rows.append({
                "period": period, "elapsed": elapsed,
                "home_wp": float(home_wp),
            })
    if not rows:
        return None

    df = pd.DataFrame(rows).sort_values("elapsed").reset_index(drop=True)
    if home_spread < 0:
        df["fav_wp"] = df["home_wp"]
    else:
        df["fav_wp"] = 1.0 - df["home_wp"]
    df["bucket"] = (df["elapsed"] // BUCKET_SEC * BUCKET_SEC).astype(int)
    agg = df.groupby("bucket", as_index=False).agg(
        period=("period", "last"),
        fav_kalshi_vwap=("fav_wp", "last"),
    )
    agg = agg.rename(columns={"bucket": "game_seconds_elapsed"})
    # Reindex to continuous 30s grid; forward-fill
    lo = int(agg["game_seconds_elapsed"].min())
    hi = int(agg["game_seconds_elapsed"].max()) + BUCKET_SEC
    grid = np.arange(lo, hi, BUCKET_SEC, dtype=int)
    agg = (
        agg.set_index("game_seconds_elapsed")
        .reindex(grid).ffill().reset_index()
        .rename(columns={"index": "game_seconds_elapsed"})
    )
    agg["fav_kalshi_vwap"] = pd.to_numeric(
        agg["fav_kalshi_vwap"], errors="coerce",
    )
    agg["period"] = pd.to_numeric(agg["period"], errors="coerce")
    agg = agg.dropna(subset=["fav_kalshi_vwap"]).reset_index(drop=True)
    return agg


def load_all_espn_games(min_bins: int = 20) -> list[dict]:
    """Load every game from nba_master with parseable spread and ESPN
    WP + PBP files present."""
    master = pd.read_csv(REPO_ROOT / "data" / "nba_master_2025_26.csv")
    master["home_spread"] = pd.to_numeric(
        master["home_spread"], errors="coerce",
    )
    master = master.dropna(subset=["home_spread", "game_id"])
    games: list[dict] = []
    skipped_missing = 0
    skipped_short = 0
    for r in master.itertuples():
        try:
            gid = str(int(r.game_id))
        except (ValueError, TypeError):
            continue
        spread = float(r.home_spread)
        ts = load_espn_wp_series(gid, spread)
        if ts is None or ts.empty:
            skipped_missing += 1
            continue
        if len(ts) < min_bins:
            skipped_short += 1
            continue
        games.append({
            "ticker": f"ESPN-{gid}",
            "abs_spread": abs(spread),
            "ts": ts,
        })
    log(
        f"  loaded {len(games)} ESPN games; "
        f"skipped {skipped_missing} (missing files) + "
        f"{skipped_short} (too short)"
    )
    return games


_SPREAD_BUCKETS: list[tuple[str, float, float]] = [
    ("1.0–2.0", 1.0, 2.0),
    ("2.5–3.5", 2.5, 3.5),
    ("4.0–5.0", 4.0, 5.0),
    ("5.5–6.0", 5.5, 6.0),
    ("6.5–8.0", 6.5, 8.0),
    ("8.5–10.0", 8.5, 10.0),
    ("10.5+", 10.5, float("inf")),
]


def _bucket_for_spread(abs_spread: float) -> str | None:
    for lab, lo, hi in _SPREAD_BUCKETS:
        if lo <= abs_spread <= hi:
            return lab
    return None


def run_part8() -> int:
    log("Part 8 — spread expansion (ESPN-only, Path A)")
    log("Loading ESPN games from nba_master + pbp + espn_wp...")
    games = load_all_espn_games()
    n_games = len(games)
    log(f"ESPN games loaded: {n_games}")

    # Build per-bucket game lists
    bucket_games: dict[str, list[dict]] = {}
    for g in games:
        lab = _bucket_for_spread(g["abs_spread"])
        if lab is None:
            continue
        bucket_games.setdefault(lab, []).append(g)

    # Precompute trailing max per bucket (restricted to best-config lookback)
    lookback_bins = max(1, int(BEST_S4A_LOOKBACK_SEC / BUCKET_SEC))
    log(f"Precomputing trailing max (lookback={lookback_bins} bins)...")
    precomp_max: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp_max[(g["ticker"], lookback_bins)] = (
            _precompute_trailing_max(fav, lookback_bins)
        )

    best_cfg = S4AConfig(
        lookback_sec=BEST_S4A_LOOKBACK_SEC,
        dip_depth=BEST_S4A_DIP_DEPTH,
        entry_lo=BEST_S4A_ENTRY_LO,
        entry_hi=BEST_S4A_ENTRY_HI,
        exit_target=BEST_S4A_EXIT_TARGET,
        stop_loss=BEST_S4A_STOP_LOSS,
    )

    # Run simulation per bucket
    log("Simulating S4A per bucket on ESPN proxy...")
    bucket_stats: dict[str, dict] = {}
    bucket_trades_all: dict[str, list[S4ATrade]] = {}
    for lab, _, _ in _SPREAD_BUCKETS:
        gs = bucket_games.get(lab, [])
        if not gs:
            bucket_stats[lab] = {
                "n_games": 0, "entries": 0, "games_with_entry": 0,
                "entries_per_game": 0.0, "hit_pct": 0.0,
                "mean_pnl": 0.0, "annual_ev": 0.0, "entry_prices": [],
            }
            bucket_trades_all[lab] = []
            continue
        trades = simulate_s4a(gs, best_cfg, precomp_max)
        summary = summarize_s4a(trades, len(gs))
        games_with_entry = len({t.ticker for t in trades})
        bucket_stats[lab] = {
            "n_games": len(gs),
            "entries": summary["entries"],
            "games_with_entry": games_with_entry,
            "entries_per_game": (
                summary["entries"] / len(gs) if gs else 0.0
            ),
            "hit_pct": summary["hit_pct"],
            "mean_pnl": summary["mean_pnl"],
            "annual_ev": summary["annual_ev"],
            "entry_prices": [t.entry_price for t in trades],
        }
        bucket_trades_all[lab] = trades

    # ---- Table 4 sanity check: ESPN vs Kalshi on competitive |spread|≤6
    log("Loading Kalshi paired competitive games for sanity check...")
    kalshi_games = load_competitive_games()
    kalshi_lookback_bins = max(1, int(BEST_S4A_LOOKBACK_SEC / BUCKET_SEC))
    kalshi_precomp: dict[tuple[str, int], np.ndarray] = {}
    for g in kalshi_games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        kalshi_precomp[(g["ticker"], kalshi_lookback_bins)] = (
            _precompute_trailing_max(fav, kalshi_lookback_bins)
        )
    kalshi_trades = simulate_s4a(kalshi_games, best_cfg, kalshi_precomp)
    kalshi_summary = summarize_s4a(kalshi_trades, len(kalshi_games))

    # ESPN subset on competitive only
    espn_competitive = [g for g in games if g["abs_spread"] <= 6.0]
    espn_comp_trades = simulate_s4a(espn_competitive, best_cfg, precomp_max)
    espn_comp_summary = summarize_s4a(
        espn_comp_trades, len(espn_competitive),
    )

    # ---- Render report --------------------------------------------------
    md: list[str] = []
    md.append(
        "# Strategy 4 — Part 8: Spread Expansion (Path A, ESPN Proxy)\n"
    )
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Dataset: {n_games} games with ESPN PBP + WP data from "
        "`data/nba_master_2025_26.csv`. S4A simulated against ESPN "
        "win-probability treated as a directional proxy for Kalshi "
        "favorite price. Best config from STRATEGY4_SPEC.md §3: "
        f"lookback {BEST_S4A_LOOKBACK_SEC}s, dip ≥ "
        f"${BEST_S4A_DIP_DEPTH:.2f}, entry ${BEST_S4A_ENTRY_LO:.2f}–"
        f"${BEST_S4A_ENTRY_HI:.2f}, target ${BEST_S4A_EXIT_TARGET:.2f}, "
        f"stop ${BEST_S4A_STOP_LOSS:.2f}.\n"
    )
    md.append(
        "\n**Important caveat.** ESPN WP is NOT Kalshi price. ESPN "
        "swings harder (compression mapping from the 168-game "
        "aggregate: favorites swing ~5–8pp deeper on ESPN than on "
        "Kalshi in mid WP zones). Entry rates, hit rates, and "
        "P&L values below are ESPN-scale, not Kalshi-confirmed. "
        "The Path A question is: *does the favorite-recovery "
        "pattern exist at wider spreads?* Path B (on Kalshi trade "
        "tapes from the full-season backfill) will produce the "
        "confirmed numbers.\n"
    )

    # Table 1 — entry rate by bucket
    md.append("\n## Table 1 — Entry rate by spread bucket\n")
    md.append(
        "| |spread| bucket | Games | Games with ≥1 entry | Entries | "
        "Entries/game |\n"
        "|---|---:|---:|---:|---:|\n"
    )
    for lab, _, _ in _SPREAD_BUCKETS:
        s = bucket_stats[lab]
        md.append(
            f"| {lab} | {s['n_games']} | {s['games_with_entry']} | "
            f"{s['entries']} | {s['entries_per_game']:.2f} |\n"
        )

    # Table 2 — hit rate + mean P&L by bucket
    md.append("\n## Table 2 — Hit rate and mean P&L by spread bucket\n")
    md.append(
        "| |spread| bucket | Entries | Hit % | Mean P&L | ESPN-scale annual EV |\n"
        "|---|---:|---:|---:|---:|\n"
    )
    for lab, _, _ in _SPREAD_BUCKETS:
        s = bucket_stats[lab]
        if s["entries"] == 0:
            md.append(f"| {lab} | 0 | — | — | — |\n")
            continue
        md.append(
            f"| {lab} | {s['entries']} | {s['hit_pct']:.1f}% | "
            f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |\n"
        )

    # Table 3 — entry price distribution
    md.append("\n## Table 3 — Entry price distribution by spread bucket\n")
    md.append(
        "| |spread| bucket | n | Min | p25 | Median | p75 | Max |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for lab, _, _ in _SPREAD_BUCKETS:
        s = bucket_stats[lab]
        prices = np.array(s["entry_prices"])
        if len(prices) == 0:
            md.append(f"| {lab} | 0 | — | — | — | — | — |\n")
            continue
        md.append(
            f"| {lab} | {len(prices)} | ${prices.min():.2f} | "
            f"${np.quantile(prices, 0.25):.2f} | "
            f"${np.median(prices):.2f} | "
            f"${np.quantile(prices, 0.75):.2f} | ${prices.max():.2f} |\n"
        )

    # Table 4 — sanity check Kalshi vs ESPN on |spread|≤6
    md.append(
        "\n## Table 4 — Sanity: Kalshi vs ESPN proxy on |spread|≤6\n"
    )
    md.append(
        "Same strategy, same entry/exit rules, same filter band. "
        "Compares the confirmed Kalshi run (165 competitive games) "
        "against the ESPN-proxy run on the same (or nearly same) "
        "universe. A large gap indicates the proxy misrepresents "
        "entry frequency or P&L.\n\n"
        "| Source | Games | Entries | Hit % | Mean P&L | Annual EV |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"| Kalshi (confirmed) | {len(kalshi_games)} | "
        f"{kalshi_summary['entries']} | {kalshi_summary['hit_pct']:.1f}% | "
        f"${kalshi_summary['mean_pnl']:+.2f} | "
        f"${kalshi_summary['annual_ev']:+,.0f} |\n"
        f"| ESPN proxy | {len(espn_competitive)} | "
        f"{espn_comp_summary['entries']} | "
        f"{espn_comp_summary['hit_pct']:.1f}% | "
        f"${espn_comp_summary['mean_pnl']:+.2f} | "
        f"${espn_comp_summary['annual_ev']:+,.0f} |\n"
    )

    # Table 5 — projected expansion annual EV
    md.append("\n## Table 5 — Projected expansion annual EV (ESPN-scale)\n")
    md.append(
        "Adds the 6.5+ buckets to the existing competitive universe. "
        "**All numbers are ESPN-scale**, not Kalshi-confirmed. Use "
        "Path B (full-season Kalshi backfill) before committing.\n\n"
        "| Spread range | Games | Entries | Annual EV (ESPN-scale) |\n"
        "|---|---:|---:|---:|\n"
    )
    total_games_exp = 0
    total_entries_exp = 0
    total_annual_exp = 0.0
    for lab, _, _ in _SPREAD_BUCKETS:
        s = bucket_stats[lab]
        md.append(
            f"| {lab} | {s['n_games']} | {s['entries']} | "
            f"${s['annual_ev']:+,.0f} |\n"
        )
        total_games_exp += s["n_games"]
        total_entries_exp += s["entries"]
        total_annual_exp += s["annual_ev"]

    # Split: existing universe (|spread|≤6) vs expansion
    existing_labels = {"1.0–2.0", "2.5–3.5", "4.0–5.0", "5.5–6.0"}
    existing_annual = sum(
        bucket_stats[lab]["annual_ev"]
        for lab in existing_labels if lab in bucket_stats
    )
    expansion_annual = total_annual_exp - existing_annual
    md.append(
        f"\n**Totals:** {total_games_exp} games, "
        f"{total_entries_exp} entries, "
        f"ESPN-scale annual EV ${total_annual_exp:+,.0f}.\n"
        f"- Existing universe (|spread|≤6): "
        f"${existing_annual:+,.0f} (ESPN-scale)\n"
        f"- Expansion (|spread|>6): "
        f"${expansion_annual:+,.0f} (ESPN-scale)\n"
    )

    REPORT_PART8_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PART8_PATH.write_text("".join(md) + "\n")
    log(f"Part 8 report → {REPORT_PART8_PATH}")
    return 0


# ---- Part 8 Path B: Kalshi-confirmed spread expansion -----------------

def load_kalshi_games_all_spreads(min_bins: int = 10) -> list[dict]:
    """Load every game with a Kalshi paired timeseries CSV and a known
    |spread|, regardless of bucket. Mirrors load_competitive_games but
    skips the |spread|≤6 filter. Games with an all-NaN `fav_kalshi_vwap`
    column (typical of pre-cliff games whose trade tapes returned
    empty) are dropped automatically by the dropna + length check.
    """
    meta = pd.read_csv(PAIRED_DIR / "matched_games.csv")
    meta["abs_spread"] = pd.to_numeric(meta["abs_spread"], errors="coerce")
    meta["home_spread"] = pd.to_numeric(meta["home_spread"], errors="coerce")
    meta = meta.dropna(subset=["abs_spread"])
    meta_map = {
        str(r.kalshi_event_ticker): {
            "abs_spread": float(r.abs_spread),
            "home_spread": (
                float(r.home_spread) if not pd.isna(r.home_spread) else None
            ),
            "espn_game_id": str(r.espn_game_id),
        }
        for r in meta.itertuples()
    }

    games: list[dict] = []
    skipped_empty = 0
    skipped_short = 0
    for p in sorted(PAIRED_DIR.glob("*_timeseries.csv")):
        m = TICKER_RE.match(p.stem)
        if not m:
            continue
        ticker = m.group(1)
        info = meta_map.get(ticker)
        if info is None:
            continue
        df = pd.read_csv(p)
        if df.empty:
            skipped_empty += 1
            continue
        for c in ("game_seconds_elapsed", "period", "fav_kalshi_vwap"):
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        if df["fav_kalshi_vwap"].notna().sum() == 0:
            skipped_empty += 1
            continue
        df["fav_kalshi_vwap"] = df["fav_kalshi_vwap"].ffill()
        df = df.dropna(
            subset=["game_seconds_elapsed", "fav_kalshi_vwap"]
        ).sort_values("game_seconds_elapsed").reset_index(drop=True)
        if len(df) < min_bins:
            skipped_short += 1
            continue
        games.append({
            "ticker": ticker,
            "abs_spread": info["abs_spread"],
            "espn_game_id": info["espn_game_id"],
            "ts": df,
        })
    log(
        f"  loaded {len(games)} Kalshi games; "
        f"skipped {skipped_empty} (empty tape) + "
        f"{skipped_short} (too short)"
    )
    return games


def run_part8_path_b() -> int:
    log("Part 8 Path B — Kalshi-confirmed spread expansion")
    log("Loading Kalshi paired timeseries (all spread buckets)...")
    games = load_kalshi_games_all_spreads()
    n_games = len(games)
    log(f"Kalshi games loaded: {n_games}")
    if n_games == 0:
        log("FAIL: no Kalshi games available for Path B.")
        return 2

    bucket_games: dict[str, list[dict]] = {}
    for g in games:
        lab = _bucket_for_spread(g["abs_spread"])
        if lab is None:
            continue
        bucket_games.setdefault(lab, []).append(g)

    lookback_bins = max(1, int(BEST_S4A_LOOKBACK_SEC / BUCKET_SEC))
    log(f"Precomputing trailing max (lookback={lookback_bins} bins)...")
    precomp_max: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp_max[(g["ticker"], lookback_bins)] = (
            _precompute_trailing_max(fav, lookback_bins)
        )

    best_cfg = S4AConfig(
        lookback_sec=BEST_S4A_LOOKBACK_SEC,
        dip_depth=BEST_S4A_DIP_DEPTH,
        entry_lo=BEST_S4A_ENTRY_LO,
        entry_hi=BEST_S4A_ENTRY_HI,
        exit_target=BEST_S4A_EXIT_TARGET,
        stop_loss=BEST_S4A_STOP_LOSS,
    )

    log("Simulating S4A per bucket on Kalshi data...")
    bucket_stats: dict[str, dict] = {}
    bucket_trades_all: dict[str, list[S4ATrade]] = {}
    for lab, _, _ in _SPREAD_BUCKETS:
        gs = bucket_games.get(lab, [])
        if not gs:
            bucket_stats[lab] = {
                "n_games": 0, "entries": 0, "games_with_entry": 0,
                "entries_per_game": 0.0, "hit_pct": 0.0,
                "mean_pnl": 0.0, "annual_ev": 0.0, "entry_prices": [],
            }
            bucket_trades_all[lab] = []
            continue
        trades = simulate_s4a(gs, best_cfg, precomp_max)
        summary = summarize_s4a(trades, len(gs))
        games_with_entry = len({t.ticker for t in trades})
        bucket_stats[lab] = {
            "n_games": len(gs),
            "entries": summary["entries"],
            "games_with_entry": games_with_entry,
            "entries_per_game": (
                summary["entries"] / len(gs) if gs else 0.0
            ),
            "hit_pct": summary["hit_pct"],
            "mean_pnl": summary["mean_pnl"],
            "annual_ev": summary["annual_ev"],
            "entry_prices": [t.entry_price for t in trades],
        }
        bucket_trades_all[lab] = trades

    # Sanity: |spread|≤6 rollup for comparison with replay baseline.
    comp_games = [g for g in games if g["abs_spread"] <= 6.0]
    comp_trades = simulate_s4a(comp_games, best_cfg, precomp_max)
    comp_summary = summarize_s4a(comp_trades, len(comp_games))

    # Table 6 — Path A vs Path B overlap per bucket.
    log("Loading ESPN games for Path A vs Path B overlap comparison...")
    espn_games = load_all_espn_games()
    espn_by_id = {g["ticker"].replace("ESPN-", ""): g for g in espn_games}
    # Precompute ESPN trailing max for only the overlap games we will
    # actually simulate (subset of ESPN games whose espn_game_id matches
    # a Kalshi game we loaded).
    overlap_precomp: dict[tuple[str, int], np.ndarray] = {}
    overlap_rows: dict[str, dict] = {}
    for lab, _, _ in _SPREAD_BUCKETS:
        kalshi_subset = bucket_games.get(lab, [])
        if not kalshi_subset:
            overlap_rows[lab] = {"n_overlap": 0}
            continue
        kalshi_overlap = [
            g for g in kalshi_subset if g["espn_game_id"] in espn_by_id
        ]
        espn_overlap = [
            espn_by_id[g["espn_game_id"]] for g in kalshi_overlap
        ]
        for g in espn_overlap:
            key = (g["ticker"], lookback_bins)
            if key not in overlap_precomp:
                fav = g["ts"]["fav_kalshi_vwap"].values
                overlap_precomp[key] = _precompute_trailing_max(
                    fav, lookback_bins,
                )
        if not kalshi_overlap:
            overlap_rows[lab] = {"n_overlap": 0}
            continue
        espn_trades = simulate_s4a(espn_overlap, best_cfg, overlap_precomp)
        espn_s = summarize_s4a(espn_trades, len(espn_overlap))
        kalshi_trades_in = simulate_s4a(
            kalshi_overlap, best_cfg, precomp_max,
        )
        kalshi_s = summarize_s4a(kalshi_trades_in, len(kalshi_overlap))
        overlap_rows[lab] = {
            "n_overlap": len(kalshi_overlap),
            "espn_entries": espn_s["entries"],
            "espn_hit": espn_s["hit_pct"],
            "espn_mean": espn_s["mean_pnl"],
            "kalshi_entries": kalshi_s["entries"],
            "kalshi_hit": kalshi_s["hit_pct"],
            "kalshi_mean": kalshi_s["mean_pnl"],
        }

    # ---- Render report -------------------------------------------------
    md: list[str] = []
    md.append(
        "# Strategy 4 — Part 8: Spread Expansion (Path B, Kalshi Confirmed)\n"
    )
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Dataset: {n_games} games with Kalshi paired timeseries "
        "CSVs from `data/wp_kalshi_paired/`. S4A simulated directly "
        "on `fav_kalshi_vwap` (30s VWAP from the Kalshi trade tape, "
        "same column `engine/replay.py` uses). Config from "
        "STRATEGY4_SPEC.md §3: lookback "
        f"{BEST_S4A_LOOKBACK_SEC}s, dip ≥ ${BEST_S4A_DIP_DEPTH:.2f}, "
        f"entry ${BEST_S4A_ENTRY_LO:.2f}–${BEST_S4A_ENTRY_HI:.2f}, "
        f"target ${BEST_S4A_EXIT_TARGET:.2f}, "
        f"stop ${BEST_S4A_STOP_LOSS:.2f}.\n"
    )
    md.append(
        "\n**Path B uses Kalshi-confirmed prices only.** Games whose "
        "trade tape returned empty (typical of pre-retention-cliff "
        "games) are excluded rather than backfilled with the ESPN "
        "proxy — Path A (`strategy4_spread_expansion.md`) remains the "
        "ESPN-only reference.\n"
    )

    # Table 1
    md.append("\n## Table 1 — Entry rate by spread bucket\n")
    md.append(
        "| |spread| bucket | Games | Games with ≥1 entry | Entries | "
        "Entries/game |\n"
        "|---|---:|---:|---:|---:|\n"
    )
    for lab, _, _ in _SPREAD_BUCKETS:
        s = bucket_stats[lab]
        md.append(
            f"| {lab} | {s['n_games']} | {s['games_with_entry']} | "
            f"{s['entries']} | {s['entries_per_game']:.2f} |\n"
        )

    # Table 2
    md.append("\n## Table 2 — Hit rate and mean P&L by spread bucket\n")
    md.append(
        "| |spread| bucket | Entries | Hit % | Mean P&L | "
        "Kalshi-confirmed annual EV |\n"
        "|---|---:|---:|---:|---:|\n"
    )
    for lab, _, _ in _SPREAD_BUCKETS:
        s = bucket_stats[lab]
        if s["entries"] == 0:
            md.append(f"| {lab} | 0 | — | — | — |\n")
            continue
        md.append(
            f"| {lab} | {s['entries']} | {s['hit_pct']:.1f}% | "
            f"${s['mean_pnl']:+.2f} | ${s['annual_ev']:+,.0f} |\n"
        )

    # Table 3
    md.append("\n## Table 3 — Entry price distribution by spread bucket\n")
    md.append(
        "| |spread| bucket | n | Min | p25 | Median | p75 | Max |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for lab, _, _ in _SPREAD_BUCKETS:
        s = bucket_stats[lab]
        prices = np.array(s["entry_prices"])
        if len(prices) == 0:
            md.append(f"| {lab} | 0 | — | — | — | — | — |\n")
            continue
        md.append(
            f"| {lab} | {len(prices)} | ${prices.min():.2f} | "
            f"${np.quantile(prices, 0.25):.2f} | "
            f"${np.median(prices):.2f} | "
            f"${np.quantile(prices, 0.75):.2f} | ${prices.max():.2f} |\n"
        )

    # Table 4 — replay parity check on |spread|≤6
    md.append(
        "\n## Table 4 — Parity check vs engine replay (|spread|≤6)\n"
    )
    md.append(
        "Path B on the |spread|≤6 subset should closely match the "
        "engine replay's equivalence run against `simulate_s4a`, since "
        "both consume the same `fav_kalshi_vwap` column. Small deltas "
        "are acceptable from different bucket rollup granularity; "
        "large deltas indicate a Path B pipeline bug.\n\n"
        "| Source | Games | Entries | Hit % | Mean P&L | Annual EV |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"| Engine replay (2026-04-22) | 171 | 166 | 52.4% | "
        "$+3.21 | $+1,708 |\n"
        f"| Path B |spread|≤6 | {len(comp_games)} | "
        f"{comp_summary['entries']} | "
        f"{comp_summary['hit_pct']:.1f}% | "
        f"${comp_summary['mean_pnl']:+.2f} | "
        f"${comp_summary['annual_ev']:+,.0f} |\n"
    )

    # Table 5 — projected expansion
    md.append("\n## Table 5 — Projected annual EV (Kalshi-confirmed)\n")
    md.append(
        "Full breakdown across all spread buckets, then the two "
        "incremental rollups (existing universe vs expansion).\n\n"
        "| Spread range | Games | Entries | Annual EV |\n"
        "|---|---:|---:|---:|\n"
    )
    total_games = 0
    total_entries = 0
    total_annual = 0.0
    existing_annual = 0.0
    existing_games = 0
    existing_entries = 0
    existing_labels = {"1.0–2.0", "2.5–3.5", "4.0–5.0", "5.5–6.0"}
    for lab, _, _ in _SPREAD_BUCKETS:
        s = bucket_stats[lab]
        md.append(
            f"| {lab} | {s['n_games']} | {s['entries']} | "
            f"${s['annual_ev']:+,.0f} |\n"
        )
        total_games += s["n_games"]
        total_entries += s["entries"]
        total_annual += s["annual_ev"]
        if lab in existing_labels:
            existing_games += s["n_games"]
            existing_entries += s["entries"]
            existing_annual += s["annual_ev"]
    expansion_games = total_games - existing_games
    expansion_entries = total_entries - existing_entries
    expansion_annual = total_annual - existing_annual
    md.append(
        f"| **Existing (|spread|≤6)** | **{existing_games}** | "
        f"**{existing_entries}** | **${existing_annual:+,.0f}** |\n"
        f"| **Expansion (|spread|>6)** | **{expansion_games}** | "
        f"**{expansion_entries}** | **${expansion_annual:+,.0f}** |\n"
        f"| **All buckets** | **{total_games}** | "
        f"**{total_entries}** | **${total_annual:+,.0f}** |\n"
    )

    # Table 6 — Path A vs Path B on overlap
    md.append(
        "\n## Table 6 — Path A (ESPN proxy) vs Path B (Kalshi) on the same games\n"
    )
    md.append(
        "For each bucket, simulate both variants on only the games "
        "that have BOTH ESPN PBP/WP AND Kalshi trade-tape data. "
        "Quantifies the ESPN-to-Kalshi bias per bucket and validates "
        "the compression mapping used in Path A.\n\n"
        "| |spread| bucket | Games (overlap) | "
        "ESPN entries / hit / mean | Kalshi entries / hit / mean |\n"
        "|---|---:|---|---|\n"
    )
    for lab, _, _ in _SPREAD_BUCKETS:
        row = overlap_rows[lab]
        if row["n_overlap"] == 0:
            md.append(f"| {lab} | 0 | — | — |\n")
            continue
        md.append(
            f"| {lab} | {row['n_overlap']} | "
            f"{row['espn_entries']} / {row['espn_hit']:.1f}% / "
            f"${row['espn_mean']:+.2f} | "
            f"{row['kalshi_entries']} / {row['kalshi_hit']:.1f}% / "
            f"${row['kalshi_mean']:+.2f} |\n"
        )

    REPORT_PART8B_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PART8B_PATH.write_text("".join(md) + "\n")
    log(f"Part 8 Path B report → {REPORT_PART8B_PATH}")
    return 0


# ---- Main --------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Strategy 4 analysis driver. Default run: Parts 1–6 "
            "(core sweep + position management). Use --part7 / --part8 "
            "for the extension studies in isolation."
        ),
    )
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument(
        "--part7", action="store_true",
        help="Run only Part 7 (halftime entry study).",
    )
    grp.add_argument(
        "--part8", action="store_true",
        help="Run only Part 8 (spread expansion). Pair with --path-b "
             "for Kalshi-confirmed prices; default is ESPN-only Path A.",
    )
    parser.add_argument(
        "--path-b", dest="path_b", action="store_true",
        help="With --part8: use Kalshi trade-tape VWAP instead of "
             "ESPN proxy. Writes to strategy4_spread_expansion_kalshi.md "
             "and preserves the ESPN Path A report.",
    )
    args = parser.parse_args()

    if args.part7:
        if args.path_b:
            parser.error("--path-b is only valid with --part8.")
        return run_part7()
    if args.part8:
        if args.path_b:
            return run_part8_path_b()
        return run_part8()
    if args.path_b:
        parser.error("--path-b requires --part8.")
    return run_default()


def run_default() -> int:
    log("Loading competitive games...")
    games = load_competitive_games()
    n_games = len(games)
    log(f"Competitive games loaded: {n_games}")

    # Precompute trailing max (Part 2) and trailing min (Part 3) per
    # game per lookback window.
    log("Precomputing trailing max/min windows...")
    lookbacks_sec = [120, 180, 300]
    precomp_max: dict[tuple[str, int], np.ndarray] = {}
    precomp_min: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        dog = 1.0 - fav
        for lb_sec in lookbacks_sec:
            lb_bins = max(1, int(lb_sec / BUCKET_SEC))
            precomp_max[(g["ticker"], lb_bins)] = (
                _precompute_trailing_max(fav, lb_bins)
            )
            precomp_min[(g["ticker"], lb_bins)] = (
                _precompute_trailing_min(dog, lb_bins)
            )
    log("Precomputation done.")

    md: list[str] = []
    md.append("# Strategy 4 — Dip-Recovery & Run-Capture Analysis\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Three-part analysis on 165 competitive games from the 168-game "
        "paired dataset. Part 1: false-summit analysis. Part 2: "
        "favorite dip-recovery sweep (1,200 configs). Part 3: underdog "
        "run-capture sweep (~200 configs). Part 4: cross-strategy "
        "comparison.\n"
    )
    md.append(
        "**Hypothesis:** buy favorite during temporary underdog runs "
        "at $0.50–$0.75, exit when favorite reasserts at $0.80–$0.95. "
        "Mirror for underdog side with static and momentum entries "
        "across $0.10–$0.35 bands.\n"
    )

    # Part 1
    render_false_summit(md, games)

    # Part 2: sweep
    md.append("## Part 2 — Favorite Dip-Recovery (Strategy 4A)\n")
    md.append(
        "Sweep 1,200 configurations. Entry fires on a dip from a "
        "trailing maximum within the specified zone, exit at target "
        "price or stop-loss. Unclosed positions resolve at game end.\n"
    )
    s4a_grid = []
    entry_zones = [
        (0.50, 0.60), (0.55, 0.65), (0.60, 0.70), (0.50, 0.75),
    ]
    dip_depths = [0.05, 0.08, 0.10, 0.15, 0.20]
    exit_targets = [0.80, 0.85, 0.90, 0.92, 0.95]
    stop_losses = [0.40, 0.45, 0.48, 0.50]
    total_configs = (
        len(lookbacks_sec) * len(dip_depths) * len(entry_zones)
        * len(exit_targets) * len(stop_losses)
    )
    log(f"Running S4A sweep: {total_configs} configs...")
    s4a_results: list[tuple[S4AConfig, dict]] = []
    i_cfg = 0
    for lb in lookbacks_sec:
        for dd in dip_depths:
            for elo, ehi in entry_zones:
                for et in exit_targets:
                    for sl in stop_losses:
                        i_cfg += 1
                        cfg = S4AConfig(
                            lookback_sec=lb, dip_depth=dd,
                            entry_lo=elo, entry_hi=ehi,
                            exit_target=et, stop_loss=sl,
                        )
                        trades = simulate_s4a(games, cfg, precomp_max)
                        s = summarize_s4a(trades, n_games)
                        s4a_results.append((cfg, s))
                        if i_cfg % 200 == 0:
                            log(f"  S4A {i_cfg}/{total_configs}")
    log("S4A sweep complete.")

    best_s4a_cfg, best_s4a_stats = render_s4a_top(md, s4a_results)

    # Re-run best config to get trades for detailed breakdown
    best_s4a_trades = simulate_s4a(games, best_s4a_cfg, precomp_max)
    render_s4a_detail(md, best_s4a_cfg, best_s4a_trades, n_games)
    render_s4a_sensitivity(md, best_s4a_cfg, s4a_results)

    # Part 3
    md.append("## Part 3 — Underdog Run-Capture (Strategy 4B)\n")
    md.append(
        "Entry detection on the underdog's Kalshi price. Static mode: "
        "buy in band, no momentum requirement. Momentum mode: buy in "
        "band only when price has risen ≥ run_size from trailing min.\n"
    )
    # Build S4B configs
    s4b_configs: list[S4BConfig] = []
    entry_bands = [
        (0.10, 0.20), (0.15, 0.25), (0.20, 0.30), (0.25, 0.35),
    ]
    run_sizes = [0.03, 0.05, 0.08]
    exit_offsets = [0.05, 0.10, 0.15, 0.20]
    stop_offset = 0.05
    # Momentum swing
    for elo, ehi in entry_bands:
        for rs in run_sizes:
            for lb in lookbacks_sec:
                for eo in exit_offsets:
                    s4b_configs.append(S4BConfig(
                        label=f"mom ${elo:.2f}-${ehi:.2f} run${rs:.2f} "
                              f"lb{lb}s +${eo:.2f}",
                        mode="momentum", lookback_sec=lb,
                        entry_lo=elo, entry_hi=ehi, run_size=rs,
                        exit_offset=eo, stop_offset=stop_offset,
                        hybrid=False,
                    ))
    # Static entries: band is a single threshold (lo=0, hi=threshold)
    static_thresholds = [0.15, 0.20, 0.25, 0.30]
    for thr in static_thresholds:
        for eo in exit_offsets:
            s4b_configs.append(S4BConfig(
                label=f"static ≤${thr:.2f} +${eo:.2f}",
                mode="static", lookback_sec=None,
                entry_lo=0.01, entry_hi=thr, run_size=None,
                exit_offset=eo, stop_offset=stop_offset,
                hybrid=False,
            ))

    log(f"Running S4B swing sweep: {len(s4b_configs)} configs...")
    s4b_swing_results: list[tuple[S4BConfig, dict]] = []
    for cfg in s4b_configs:
        trades = simulate_s4b(games, cfg, precomp_min)
        s = summarize_s4b(trades, n_games)
        s4b_swing_results.append((cfg, s))
    log("S4B swing sweep complete.")

    best_s4b_cfg, best_s4b_stats = render_s4b_top(
        md, s4b_swing_results,
        "3A — Top 20 underdog swing configs by annual EV",
    )

    # Hybrid: take top 5 swing configs and test the 50/50 hybrid variant
    log("Running S4B hybrid variants (top 10 swing configs)...")
    top_swing = sorted(
        s4b_swing_results, key=lambda r: r[1]["annual_ev"], reverse=True,
    )[:10]
    s4b_hybrid_results: list[tuple[S4BConfig, dict]] = []
    for cfg, _ in top_swing:
        hybrid_cfg = S4BConfig(
            label=cfg.label + " [hybrid 50/50]",
            mode=cfg.mode, lookback_sec=cfg.lookback_sec,
            entry_lo=cfg.entry_lo, entry_hi=cfg.entry_hi,
            run_size=cfg.run_size, exit_offset=cfg.exit_offset,
            stop_offset=cfg.stop_offset, hybrid=True,
        )
        trades = simulate_s4b(games, hybrid_cfg, precomp_min)
        s = summarize_s4b(trades, n_games)
        s4b_hybrid_results.append((hybrid_cfg, s))
    render_s4b_top(
        md, s4b_hybrid_results, "3B — Top 10 underdog hybrid configs",
        limit=10,
    )

    # Compare best swing vs best hybrid; use the better
    if s4b_hybrid_results:
        best_hybrid = sorted(
            s4b_hybrid_results, key=lambda r: r[1]["annual_ev"], reverse=True,
        )[0]
        if best_hybrid[1]["annual_ev"] > best_s4b_stats["annual_ev"]:
            best_s4b_cfg, best_s4b_stats = best_hybrid

    # 3C — detail for best underdog
    md.append("### 3C — Best underdog config detail\n")
    md.append(
        f"- {best_s4b_cfg.label}\n"
        f"- Mode: {best_s4b_cfg.mode}\n"
        f"- Entry band: ${best_s4b_cfg.entry_lo:.2f}–${best_s4b_cfg.entry_hi:.2f}\n"
        f"- Exit offset: +${best_s4b_cfg.exit_offset:.2f}; stop: "
        f"−${best_s4b_cfg.stop_offset:.2f}\n"
        f"- Hybrid (50% hold to resolution): {best_s4b_cfg.hybrid}\n"
    )
    best_s4b_trades = simulate_s4b(games, best_s4b_cfg, precomp_min)
    md.append("#### Outcome distribution\n")
    md.append("| Exit type | Count | % | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    if best_s4b_trades:
        n = len(best_s4b_trades)
        by_type: dict[str, list[float]] = {}
        for t in best_s4b_trades:
            by_type.setdefault(t.exit_type, []).append(t.net_pnl)
        for et, pnls in sorted(by_type.items()):
            md.append(
                f"| {et} | {len(pnls)} | {100*len(pnls)/n:.1f}% | "
                f"${np.mean(pnls):+.2f} |"
            )
    md.append("")
    render_s4b_resolution_math(md, games)

    # Part 4
    render_comparison(md, best_s4a_stats, best_s4b_stats, n_games)

    # Part 5 — prior-weighting
    render_part5(
        md, games, n_games,
        best_s4a_cfg, best_s4a_trades, s4a_results,
        best_s4b_cfg, best_s4b_trades,
        precomp_max, precomp_min,
    )

    # Part 6 — position management (averaging-in / averaging-out)
    render_part6(md, games, n_games, best_s4a_cfg, precomp_max)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(md) + "\n")
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
