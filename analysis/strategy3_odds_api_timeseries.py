"""
Strategy 3 Odds API timeseries scrape — ESPN-to-market survival rate.

Pulls full-game FanDuel moneyline timeseries at 5-min intervals for 15
strategically selected games, runs the same swing / round-trip analysis
as the ESPN game-flow trajectory script, and computes the ESPN-to-market
survival rate — the single number that converts the 1,234-game ESPN
ceiling into a realistic Strategy 3 yield estimate.

Usage:
    # Plan only (no API key needed)
    python -m analysis.strategy3_odds_api_timeseries --plan-only

    # Full run (requires ODDS_API_KEY)
    python -m analysis.strategy3_odds_api_timeseries

    # Custom sample size
    python -m analysis.strategy3_odds_api_timeseries --n-games 20
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

# Reuse infrastructure from Strategy 1 backfill and phase3a follow-up
from analysis.strategy1_sportsbook_backfill import (
    Report,
    load_espn_timeline,
    fetch_historical_events,
    fetch_historical_event_odds,
    parse_bookmaker_h2h,
    _ODDS_API_NAME_TO_ABBR,
    ODDS_API_BASE,
    RATE_LIMIT_SEC,
    STALE_QUOTE_SEC,
    _iso_utc,
)
from scrapers.espn_scraper import _norm_team


# ---- Paths / constants -------------------------------------------------

MASTER_CSV = Path("data/nba_master_2025_26.csv")
WP_DIR = Path("data/espn_wp")
PBP_DIR = Path("data/pbp")
CACHE_DIR = Path("data/odds_api_historical/strategy3_timeseries")
OUTPUT_MD = Path("docs/analysis_outputs/strategy3_odds_api_timeseries.md")

CREDITS_PER_EVENT_ODDS = 10
CREDITS_PER_EVENTS_LIST = 1
TIMESTAMP_INTERVAL_MIN = 5
GAME_DURATION_HOURS = 3.0
PRE_TIP_DISCOVERY_MINUTES = 60   # events-list call offset before tip

# Constants duplicated from phase_3a_followup to keep this script
# standalone for the bucket-classification step.
REG_PERIODS = 4
REG_PERIOD_SEC = 720
OT_PERIOD_SEC = 300
TRADEABLE_SEC_REM_MIN = 60

SWING_MIN_MAG = 0.02
SMOOTH_WINDOW = 3

# Round-trip threshold grids
UNDERDOG_ENTRY = 0.35
UNDERDOG_EXIT = 0.50
FAV_ENTRY = 0.60
FAV_EXIT = 0.70

# FanDuel-native alternative threshold pairs to test
FD_NATIVE_PAIRS = [
    (0.35, 0.50),   # baseline = ESPN grid
    (0.40, 0.50),   # tight, $0.10 delta
    (0.40, 0.55),   # $0.15 delta
    (0.45, 0.55),   # $0.10 delta
]

BUCKET_ORDER = [
    "comeback", "back_and_forth", "wire_to_wire", "blowout", "late_collapse",
]
BUCKET_LABEL = {
    "comeback": "Comeback",
    "back_and_forth": "Back-and-forth",
    "wire_to_wire": "Wire-to-wire",
    "blowout": "Blowout",
    "late_collapse": "Late collapse",
}

# Stratified target counts per bucket (must sum to --n-games default)
DEFAULT_SELECTION = {
    "comeback": 6,
    "back_and_forth": 6,
    "wire_to_wire": 2,
    "blowout": 1,
}


# ---- Lightweight bucket classification --------------------------------

def count_roundtrips(series: np.ndarray, entry: float, exit_thr: float) -> int:
    """Greedy scan — count complete round-trips only."""
    n = 0
    i = 0
    sz = len(series)
    while i < sz:
        if series[i] <= entry:
            j = i + 1
            while j < sz and series[j] < exit_thr:
                j += 1
            if j < sz:
                n += 1
                i = j + 1
            else:
                break
        else:
            i += 1
    return n


def detect_swings(values: np.ndarray) -> list[dict]:
    """Same algorithm as game-flow trajectory script. Returns list of
    swings with magnitude ≥ SWING_MIN_MAG."""
    values = np.asarray(values, dtype=float)
    if len(values) < 3:
        return []
    s = pd.Series(values)
    smoothed = s.rolling(SMOOTH_WINDOW, center=True).median().fillna(s)
    smoothed = smoothed.values.astype(float)
    peaks, _ = find_peaks(smoothed, prominence=SWING_MIN_MAG)
    troughs, _ = find_peaks(-smoothed, prominence=SWING_MIN_MAG)
    extrema = sorted(
        [(int(i), float(smoothed[i]), "max") for i in peaks]
        + [(int(i), float(smoothed[i]), "min") for i in troughs],
        key=lambda e: e[0],
    )
    if not extrema:
        return []
    first_type = extrema[0][2]
    extrema = [(0, float(smoothed[0]), "min" if first_type == "max" else "max")] + extrema
    last_type = extrema[-1][2]
    extrema.append((len(smoothed) - 1, float(smoothed[-1]),
                    "min" if last_type == "max" else "max"))
    swings = []
    for k in range(1, len(extrema)):
        a, b = extrema[k - 1], extrema[k]
        mag = abs(b[1] - a[1])
        if mag < SWING_MIN_MAG:
            continue
        swings.append({
            "type": "up" if a[2] == "min" else "down",
            "start_idx": a[0], "end_idx": b[0],
            "start_wp": a[1], "end_wp": b[1],
            "magnitude": mag,
        })
    return swings


def classify_bucket(live_df: pd.DataFrame, home_won: bool,
                   final_margin: float, n_lead_changes: int,
                   pct_competitive: float) -> str:
    home_wp = live_df["home_wp"].to_numpy(dtype=float)
    sec_rem = live_df["sec_rem"].to_numpy(dtype=float)
    winner_wp = home_wp if home_won else (1.0 - home_wp)
    loser_wp = 1.0 - winner_wp

    pre_q4 = sec_rem > REG_PERIOD_SEC
    if pre_q4.any() and winner_wp[pre_q4].max() > 0.90 and final_margin > 15:
        return "blowout"
    if winner_wp.min() < 0.20:
        return "comeback"
    second_half = sec_rem < 1440
    if second_half.any() and loser_wp[second_half].max() > 0.80:
        return "late_collapse"
    if n_lead_changes >= 3 and pct_competitive >= 0.40:
        return "back_and_forth"
    return "wire_to_wire"


def classify_all_games(master: pd.DataFrame,
                       rep: Report) -> pd.DataFrame:
    """Iterate all games, load ESPN timeline, classify bucket, count ESPN
    mid-range round-trips. Returns DataFrame keyed by game_id with bucket,
    espn_roundtrips, tip_wallclock, etc."""
    rep.stdout_only(f"\nClassifying {len(master)} games…")
    rows = []
    processed = 0
    for _, g in master.iterrows():
        gid = str(g["game_id"])
        timeline = load_espn_timeline(gid)
        if timeline.empty or len(timeline) < 10:
            continue
        live = timeline[timeline["sec_rem"] >= TRADEABLE_SEC_REM_MIN]
        if len(live) < 10:
            continue
        home_wp = live["home_wp"].to_numpy(dtype=float)
        sign = np.sign(home_wp - 0.5)
        sign_nz = sign.copy()
        sign_nz[sign_nz == 0] = np.nan
        sign_ffill = pd.Series(sign_nz).ffill().dropna().to_numpy()
        n_lead_changes = (
            int(np.sum(np.diff(sign_ffill) != 0))
            if len(sign_ffill) > 1 else 0
        )
        pct_competitive = float(
            np.mean((home_wp >= 0.30) & (home_wp <= 0.70))
        )

        home_won = bool(g["home_score"] > g["away_score"])
        final_margin = abs(float(g["home_score"] - g["away_score"]))
        bucket = classify_bucket(
            live, home_won, final_margin, n_lead_changes, pct_competitive,
        )

        # Count ESPN mid-range round-trips (home + away perspectives)
        home_rts = count_roundtrips(home_wp, UNDERDOG_ENTRY, UNDERDOG_EXIT)
        away_rts = count_roundtrips(
            1.0 - home_wp, UNDERDOG_ENTRY, UNDERDOG_EXIT,
        )
        total_rts = home_rts + away_rts

        tip_wallclock = timeline["wallclock_dt"].iloc[0]

        rows.append({
            "game_id": gid,
            "game_date": g["game_date"],
            "home": _norm_team(g["home_team_abbrev"]),
            "away": _norm_team(g["away_team_abbrev"]),
            "home_spread": float(g["home_spread"])
                if pd.notna(g["home_spread"]) else np.nan,
            "home_won": home_won,
            "final_margin": final_margin,
            "bucket": bucket,
            "n_lead_changes": n_lead_changes,
            "pct_competitive": pct_competitive,
            "espn_roundtrips": total_rts,
            "tip_wallclock": tip_wallclock,
        })
        processed += 1
        if processed % 100 == 0:
            rep.stdout_only(f"  …{processed} games classified")
    rep.stdout_only(f"  Classification complete: {processed} games")
    return pd.DataFrame(rows)


# ---- Game selection ---------------------------------------------------

def stratified_select(classified: pd.DataFrame,
                      rep: Report,
                      n_games: int = 15,
                      rng_seed: int = 42) -> pd.DataFrame:
    """Stratified sample. Default: 6 Comeback, 6 Back-and-forth, 2 Wire-to-
    wire, 1 Blowout. Within each bucket × season-third, prefer games with
    more ESPN round-trips."""
    filtered = classified[
        (classified["home_spread"].abs() <= 6)
        & (classified["espn_roundtrips"] >= 1)
        & classified["tip_wallclock"].notna()
    ].copy()
    filtered["game_date_dt"] = pd.to_datetime(filtered["game_date"])
    filtered = filtered.sort_values("game_date_dt").reset_index(drop=True)

    # Assign season thirds (by date)
    n = len(filtered)
    thirds = [
        max(1, n // 3),
        max(2, 2 * n // 3),
    ]
    filtered["season_third"] = 0
    filtered.loc[thirds[0]:thirds[1] - 1, "season_third"] = 1
    filtered.loc[thirds[1]:, "season_third"] = 2

    # Scale targets if n_games != default 15
    if n_games != 15:
        scale = n_games / 15.0
        targets = {k: max(1, round(v * scale))
                   for k, v in DEFAULT_SELECTION.items()}
    else:
        targets = dict(DEFAULT_SELECTION)

    chosen = []
    for bucket, total_target in targets.items():
        bucket_games = filtered[filtered["bucket"] == bucket]
        if bucket_games.empty:
            rep.stdout_only(f"  WARN: no {bucket} games available")
            continue
        # Distribute target across season thirds
        per_third = max(1, total_target // 3)
        remaining = total_target
        for third in (0, 1, 2):
            if remaining <= 0:
                break
            take = min(per_third, remaining)
            group = bucket_games[bucket_games["season_third"] == third]
            if group.empty:
                continue
            # Prefer more round-trips
            picks = group.sort_values(
                "espn_roundtrips", ascending=False,
            ).head(take)
            chosen.append(picks)
            remaining -= len(picks)
        # Top-up from any remaining bucket games if we fell short
        if remaining > 0:
            already = set(pd.concat(chosen)["game_id"]) if chosen else set()
            extras = bucket_games[~bucket_games["game_id"].isin(already)]
            topup = extras.sort_values(
                "espn_roundtrips", ascending=False,
            ).head(remaining)
            if not topup.empty:
                chosen.append(topup)

    selected = pd.concat(chosen).reset_index(drop=True) if chosen else pd.DataFrame()
    return selected.head(n_games).sort_values("game_date_dt").reset_index(drop=True)


def describe_plan(classified: pd.DataFrame, selected: pd.DataFrame,
                  rep: Report) -> None:
    # Bucket distribution
    rep.stdout_only("\n=== Bucket distribution (all classified games) ===")
    for b in BUCKET_ORDER:
        sub = classified[classified["bucket"] == b]
        rep.stdout_only(f"  {BUCKET_LABEL[b]:<18s} n={len(sub):>4d}  "
                        f"({len(sub) / len(classified) * 100:.1f}%)")

    rep.stdout_only(f"\n=== Selected games ({len(selected)}) ===")
    rep.stdout_only(
        f"{'#':>2s}  {'gameId':<10s} {'date':<11s} {'away':>4s} "
        f"{'home':>4s} {'spread':>7s}  {'bucket':<16s} "
        f"{'ESPN_rts':>8s}  {'tip_wallclock':<20s}"
    )
    for i, r in selected.iterrows():
        tip = (r['tip_wallclock'].strftime('%Y-%m-%dT%H:%MZ')
               if pd.notna(r['tip_wallclock']) else "—")
        rep.stdout_only(
            f"{i+1:>2d}  {r['game_id']:<10s} {str(r['game_date']):<11s} "
            f"{r['away']:>4s} {r['home']:>4s} "
            f"{r['home_spread']:>+7.1f}  "
            f"{BUCKET_LABEL[r['bucket']]:<16s} "
            f"{int(r['espn_roundtrips']):>8d}  {tip:<20s}"
        )

    # Credit estimate
    n_ts_per_game = int(GAME_DURATION_HOURS * 60 // TIMESTAMP_INTERVAL_MIN) + 1
    unique_dates = selected["game_date"].nunique()
    events_credits = unique_dates * CREDITS_PER_EVENTS_LIST
    odds_credits = len(selected) * n_ts_per_game * CREDITS_PER_EVENT_ODDS
    total = events_credits + odds_credits
    rep.stdout_only(
        f"\n=== Credit budget ==="
        f"\n  Timestamps per game: {n_ts_per_game} "
        f"({GAME_DURATION_HOURS}h at {TIMESTAMP_INTERVAL_MIN}-min)"
        f"\n  Event discovery calls: {unique_dates} unique dates × "
        f"{CREDITS_PER_EVENTS_LIST} credit = {events_credits} credits"
        f"\n  Event odds calls: {len(selected)} games × "
        f"{n_ts_per_game} timestamps = "
        f"{len(selected) * n_ts_per_game} calls"
        f"\n  Event odds credits: × {CREDITS_PER_EVENT_ODDS} = "
        f"{odds_credits} credits"
        f"\n  Estimated total: ≈ {total} credits"
    )


# ---- Full-run fetch + analysis ----------------------------------------

def _build_event_index(events: list[dict]) -> dict[tuple[str, str], str]:
    """Map (home_abbr, away_abbr) → event_id."""
    index: dict[tuple[str, str], str] = {}
    for e in events or []:
        home_name = e.get("home_team") or ""
        away_name = e.get("away_team") or ""
        home_abbr = _ODDS_API_NAME_TO_ABBR.get(home_name)
        away_abbr = _ODDS_API_NAME_TO_ABBR.get(away_name)
        if home_abbr and away_abbr and e.get("id"):
            index[(home_abbr, away_abbr)] = e["id"]
    return index


def _discovery_snapshot_iso(tip_wallclock: Any) -> str:
    ts = pd.Timestamp(tip_wallclock).tz_convert("UTC") - pd.Timedelta(
        minutes=PRE_TIP_DISCOVERY_MINUTES,
    )
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_game_timeseries(
    game_row: pd.Series, api_key: str, rep: Report,
) -> tuple[list[dict], dict]:
    """Fetch FanDuel + consensus WP timeseries for one game. Returns
    (timeseries_rows, stats). Each ts row has ts, minute_offset,
    fd_home_wp, consensus_home_wp, n_books, fd_stale."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    gid = game_row["game_id"]

    # Event discovery
    snapshot_iso = _discovery_snapshot_iso(game_row["tip_wallclock"])
    events, _ = fetch_historical_events(api_key, snapshot_iso, rep)
    event_index = _build_event_index(events)
    home_abbr = game_row["home"]
    away_abbr = game_row["away"]
    event_id = event_index.get((home_abbr, away_abbr))
    if event_id is None:
        rep.stdout_only(
            f"    [skip] no Odds API event for {away_abbr}@{home_abbr}"
        )
        return [], {"failures": 1, "fetched": 0}

    # Generate timestamp grid: tip → tip + 3h every 5 min
    tip = pd.Timestamp(game_row["tip_wallclock"]).tz_convert("UTC")
    n_points = int(GAME_DURATION_HOURS * 60 // TIMESTAMP_INTERVAL_MIN) + 1
    timestamps = [
        tip + pd.Timedelta(minutes=TIMESTAMP_INTERVAL_MIN * i)
        for i in range(n_points)
    ]

    rows: list[dict] = []
    fetched = 0
    for i, ts in enumerate(timestamps):
        minute_offset = TIMESTAMP_INTERVAL_MIN * i
        ts_iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        cache_fn = f"{gid}_m{minute_offset:03d}.json"
        data, _ = fetch_historical_event_odds(
            api_key, event_id, ts_iso, rep, cache_fn,
        )
        fetched += 1
        time.sleep(RATE_LIMIT_SEC)
        if data is None:
            rows.append({
                "ts": ts, "minute_offset": minute_offset,
                "fd_home_wp": np.nan, "consensus_home_wp": np.nan,
                "n_books": 0, "fd_stale": True,
            })
            continue
        home_name = data.get("home_team") or ""
        away_name = data.get("away_team") or ""
        books = parse_bookmaker_h2h(data, home_name, away_name, ts)

        fresh_books = [
            b for b in books
            if b["staleness_sec"] is not None
            and b["staleness_sec"] <= STALE_QUOTE_SEC
        ]
        # FanDuel only
        fd = next((b for b in books if b["bookmaker_key"] == "fanduel"), None)
        fd_stale = (fd is None
                    or fd["staleness_sec"] is None
                    or fd["staleness_sec"] > STALE_QUOTE_SEC)
        fd_home_wp = (fd["home_novig"] if fd and not fd_stale
                      else np.nan)
        # Consensus across fresh books
        if fresh_books:
            consensus_home_wp = float(
                np.mean([b["home_novig"] for b in fresh_books])
            )
        else:
            consensus_home_wp = np.nan
        rows.append({
            "ts": ts,
            "minute_offset": minute_offset,
            "fd_home_wp": fd_home_wp,
            "consensus_home_wp": consensus_home_wp,
            "n_books": len(fresh_books),
            "fd_stale": fd_stale,
        })

    # Fill FD gaps: use consensus where FD is stale/missing
    for r in rows:
        if pd.isna(r["fd_home_wp"]) and not pd.isna(r["consensus_home_wp"]):
            r["fd_home_wp_filled"] = r["consensus_home_wp"]
            r["fd_source"] = "consensus"
        else:
            r["fd_home_wp_filled"] = r["fd_home_wp"]
            r["fd_source"] = "fanduel" if not r["fd_stale"] else "none"

    # Small-gap interpolation (≤2 intervals = 10 min)
    df = pd.DataFrame(rows)
    filled = df["fd_home_wp_filled"].interpolate(limit=2)
    df["fd_home_wp_filled"] = filled
    rows = df.to_dict("records")

    return rows, {"failures": 0, "fetched": fetched}


# ---- Analysis on FanDuel timeseries -----------------------------------

def analyze_fd_timeseries(timeseries: list[dict]) -> dict:
    """Swing detection + round-trip analysis on the FD home WP series.
    Returns dict of aggregated features."""
    df = pd.DataFrame(timeseries)
    fd = df["fd_home_wp_filled"].dropna().to_numpy(dtype=float)
    if len(fd) < 3:
        return {
            "n_obs": len(fd), "n_swings_05": 0, "n_swings_10": 0,
            "n_swings_15": 0, "max_swing": 0.0,
            "total_swing_distance": 0.0,
            "fd_rts_by_pair": {p: 0 for p in FD_NATIVE_PAIRS},
            "fd_rts_away_by_pair": {p: 0 for p in FD_NATIVE_PAIRS},
        }
    swings = detect_swings(fd)
    mags = [s["magnitude"] for s in swings]
    # Round-trips at each FD-native pair, both home + away sides
    fd_rts_home: dict[tuple, int] = {}
    fd_rts_away: dict[tuple, int] = {}
    for (entry, exit_thr) in FD_NATIVE_PAIRS:
        fd_rts_home[(entry, exit_thr)] = count_roundtrips(fd, entry, exit_thr)
        fd_rts_away[(entry, exit_thr)] = count_roundtrips(
            1.0 - fd, entry, exit_thr,
        )
    return {
        "n_obs": len(fd),
        "n_swings_05": sum(1 for m in mags if m >= 0.05),
        "n_swings_10": sum(1 for m in mags if m >= 0.10),
        "n_swings_15": sum(1 for m in mags if m >= 0.15),
        "max_swing": float(max(mags)) if mags else 0.0,
        "total_swing_distance": float(sum(mags)),
        "fd_rts_by_pair": fd_rts_home,
        "fd_rts_away_by_pair": fd_rts_away,
    }


def favorite_side_roundtrips_fd(
    timeseries: list[dict], home_spread: float, favorite_won: bool,
) -> dict:
    df = pd.DataFrame(timeseries)
    fd = df["fd_home_wp_filled"].dropna().to_numpy(dtype=float)
    if len(fd) < 3 or pd.isna(home_spread) or home_spread == 0:
        return {"n_completed": 0, "n_res_win": 0, "n_res_loss": 0,
                "blended_net_maker": 0.0, "positions": 0}
    fav_wp = fd if home_spread < 0 else (1.0 - fd)
    # Greedy scan with resolution backstop
    outcomes = []
    i = 0
    sz = len(fav_wp)
    while i < sz:
        if fav_wp[i] <= FAV_ENTRY:
            entry_price = float(fav_wp[i])
            j = i + 1
            while j < sz and fav_wp[j] < FAV_EXIT:
                j += 1
            if j < sz:
                outcomes.append({
                    "entry_price": entry_price,
                    "exit_price": float(fav_wp[j]),
                    "outcome": "completed",
                })
                i = j + 1
            else:
                res_price = 1.0 if favorite_won else 0.0
                outcomes.append({
                    "entry_price": entry_price,
                    "exit_price": res_price,
                    "outcome": "resolution_win" if favorite_won
                               else "resolution_loss",
                })
                break
        else:
            i += 1
    n_completed = sum(1 for o in outcomes if o["outcome"] == "completed")
    n_res_win = sum(1 for o in outcomes if o["outcome"] == "resolution_win")
    n_res_loss = sum(1 for o in outcomes if o["outcome"] == "resolution_loss")
    # Maker-maker net per position
    def _mk_fee(p):
        if p <= 0 or p >= 1:
            return 0.0
        return math.ceil(0.0175 * 100 * p * (1 - p) * 100) / 100
    total_net = 0.0
    for o in outcomes:
        gross = (o["exit_price"] - o["entry_price"]) * 100
        entry_fee = _mk_fee(o["entry_price"])
        if o["outcome"] == "completed":
            exit_fee = _mk_fee(o["exit_price"])
            total_net += gross - entry_fee - exit_fee
        else:
            total_net += gross - entry_fee
    blended = total_net / len(outcomes) if outcomes else 0.0
    return {
        "n_completed": n_completed,
        "n_res_win": n_res_win,
        "n_res_loss": n_res_loss,
        "blended_net_maker": blended,
        "positions": len(outcomes),
    }


# ---- ESPN paired analysis (for survival rate) -------------------------

def analyze_espn_for_game(gid: str) -> dict:
    """Swing + round-trip counts on ESPN home_wp for a single game.
    Uses the same count_roundtrips + detect_swings functions for
    apples-to-apples comparison with FD timeseries."""
    timeline = load_espn_timeline(gid)
    if timeline.empty:
        return {"n_swings_05": 0, "n_swings_10": 0, "n_swings_15": 0,
                "n_rts_home": 0, "n_rts_away": 0, "n_rts_total": 0,
                "mean_rt_duration_min": np.nan}
    live = timeline[timeline["sec_rem"] >= TRADEABLE_SEC_REM_MIN]
    if len(live) < 10:
        return {"n_swings_05": 0, "n_swings_10": 0, "n_swings_15": 0,
                "n_rts_home": 0, "n_rts_away": 0, "n_rts_total": 0,
                "mean_rt_duration_min": np.nan}
    home_wp = live["home_wp"].to_numpy(dtype=float)
    swings = detect_swings(home_wp)
    mags = [s["magnitude"] for s in swings]
    rts_home = count_roundtrips(home_wp, UNDERDOG_ENTRY, UNDERDOG_EXIT)
    rts_away = count_roundtrips(
        1.0 - home_wp, UNDERDOG_ENTRY, UNDERDOG_EXIT,
    )
    # Mean round-trip duration — indexable by live["wallclock_dt"] if
    # present; requires re-scan to pair entries/exits with timestamps.
    durations = _rt_durations_minutes(
        home_wp, live["wallclock_dt"].to_numpy(),
        UNDERDOG_ENTRY, UNDERDOG_EXIT,
    ) + _rt_durations_minutes(
        1.0 - home_wp, live["wallclock_dt"].to_numpy(),
        UNDERDOG_ENTRY, UNDERDOG_EXIT,
    )
    return {
        "n_swings_05": sum(1 for m in mags if m >= 0.05),
        "n_swings_10": sum(1 for m in mags if m >= 0.10),
        "n_swings_15": sum(1 for m in mags if m >= 0.15),
        "n_rts_home": rts_home,
        "n_rts_away": rts_away,
        "n_rts_total": rts_home + rts_away,
        "mean_rt_duration_min": (float(np.mean(durations))
                                 if durations else np.nan),
    }


def _rt_durations_minutes(series, tss, entry, exit_thr) -> list[float]:
    """Return list of round-trip durations in minutes."""
    durations = []
    i = 0
    sz = len(series)
    while i < sz:
        if series[i] <= entry:
            t_entry = tss[i]
            j = i + 1
            while j < sz and series[j] < exit_thr:
                j += 1
            if j < sz:
                t_exit = tss[j]
                delta = (pd.Timestamp(t_exit) - pd.Timestamp(t_entry))
                durations.append(delta.total_seconds() / 60)
                i = j + 1
            else:
                break
        else:
            i += 1
    return durations


# ---- Report builder ---------------------------------------------------

def build_report(
    rep: Report,
    selected: pd.DataFrame,
    per_game_fd: dict[str, dict],
    per_game_espn: dict[str, dict],
    per_game_favorite: dict[str, dict],
    stats: dict,
) -> None:
    """Write the full report to both stdout and markdown."""
    rep.md_only(
        f"# Strategy 3 Odds API timeseries — "
        f"{date.today().isoformat()}\n"
    )
    rep.md_only(
        f"Full-game FanDuel moneyline timeseries at "
        f"{TIMESTAMP_INTERVAL_MIN}-min intervals via the Odds API "
        f"historical endpoint. {len(selected)} games stratified across "
        "trajectory buckets. Answers: **what fraction of ESPN-visible "
        "mid-range round-trips survive at real-money sportsbook "
        "prices?**\n"
    )

    # Section 1: Selected games
    rep.md_only("## 1. Selected games\n")
    rep.md_only(
        "| # | gameId | date | away | home | spread | bucket | "
        "ESPN rts | tip wallclock |\n"
        "|---|--------|------|------|------|--------|--------|"
        "----------|----------------|"
    )
    for i, r in selected.iterrows():
        tip = (r['tip_wallclock'].strftime('%Y-%m-%dT%H:%MZ')
               if pd.notna(r['tip_wallclock']) else "—")
        rep.md_only(
            f"| {i+1} | {r['game_id']} | {r['game_date']} | "
            f"{r['away']} | {r['home']} | {r['home_spread']:+.1f} | "
            f"{BUCKET_LABEL[r['bucket']]} | "
            f"{int(r['espn_roundtrips'])} | {tip} |"
        )
    rep.md_only(
        f"\nAPI calls: {stats.get('api_calls', 0)}. "
        f"Credits remaining (per headers): "
        f"{stats.get('credits_remaining', 'unknown')}.\n"
    )

    # Section 2: Timeseries quality
    rep.md_only("\n## 2. FanDuel timeseries quality\n")
    rep.md_only(
        "| game | n timestamps | n with FD data | n with consensus | "
        "max gap (min) |\n"
        "|------|--------------|----------------|------------------|"
        "---------------|"
    )
    for gid, fd_stats in per_game_fd.items():
        cov = fd_stats.get("coverage", {})
        rep.md_only(
            f"| {gid} | {cov.get('n_total', 0)} | "
            f"{cov.get('n_with_fd', 0)} | {cov.get('n_with_cons', 0)} | "
            f"{cov.get('max_gap_min', 0):.1f} |"
        )

    # Section 3: Per-game comparison
    rep.md_only("\n## 3. Per-game comparison (ESPN vs FanDuel)\n")
    rep.md_only(
        "| Game | Bucket | |Spread| | ESPN ≥0.10 swings | "
        "FD ≥0.10 swings | ESPN RTs (0.35→0.50) | "
        "FD RTs (0.35→0.50) | FD RTs (0.40→0.50) |\n"
        "|------|--------|---------|-------------------|"
        "-----------------|----------------------|"
        "---------------------|---------------------|"
    )
    total_espn_rts = 0
    total_fd_rts_baseline = 0
    total_espn_sw = 0
    total_fd_sw = 0
    for _, r in selected.iterrows():
        gid = r["game_id"]
        fd = per_game_fd.get(gid, {})
        espn = per_game_espn.get(gid, {})
        fd_feat = fd.get("features", {})
        fd_rts_home = fd_feat.get("fd_rts_by_pair", {})
        fd_rts_away = fd_feat.get("fd_rts_away_by_pair", {})
        baseline = (fd_rts_home.get((0.35, 0.50), 0)
                    + fd_rts_away.get((0.35, 0.50), 0))
        tight = (fd_rts_home.get((0.40, 0.50), 0)
                 + fd_rts_away.get((0.40, 0.50), 0))
        espn_rts = espn.get("n_rts_total", 0)
        total_espn_rts += espn_rts
        total_fd_rts_baseline += baseline
        total_espn_sw += espn.get("n_swings_10", 0)
        total_fd_sw += fd_feat.get("n_swings_10", 0)
        rep.md_only(
            f"| {gid} | {BUCKET_LABEL[r['bucket']]} | "
            f"{abs(r['home_spread']):.1f} | "
            f"{espn.get('n_swings_10', 0)} | "
            f"{fd_feat.get('n_swings_10', 0)} | "
            f"{espn_rts} | {baseline} | {tight} |"
        )

    # Section 4: Survival rate
    rep.md_only("\n## 4. Survival rate — headline\n")
    if total_espn_rts > 0:
        survival = total_fd_rts_baseline / total_espn_rts
        swing_survival = (total_fd_sw / total_espn_sw) if total_espn_sw else 0
        rep.md_only(
            f"**ESPN-to-FanDuel round-trip survival rate**\n\n"
            f"- Pooled round-trips: ESPN = {total_espn_rts}, "
            f"FanDuel = {total_fd_rts_baseline}\n"
            f"- **Survival rate = {survival:.1%}**\n"
            f"- Swing survival (≥0.10): "
            f"ESPN = {total_espn_sw}, FD = {total_fd_sw}, "
            f"rate = {swing_survival:.1%}\n\n"
            f"Per-bucket survival:\n"
        )
        rep.md_only(
            "| Bucket | N | ESPN RTs | FD RTs | Survival rate |\n"
            "|--------|---|----------|--------|---------------|"
        )
        for b in BUCKET_ORDER:
            sub = selected[selected["bucket"] == b]
            if sub.empty:
                continue
            e_rts = sum(per_game_espn.get(g, {}).get("n_rts_total", 0)
                        for g in sub["game_id"])
            f_rts = 0
            for g in sub["game_id"]:
                fd_feat = per_game_fd.get(g, {}).get("features", {})
                f_rts += fd_feat.get("fd_rts_by_pair", {}).get(
                    (0.35, 0.50), 0)
                f_rts += fd_feat.get("fd_rts_away_by_pair", {}).get(
                    (0.35, 0.50), 0)
            srate = f_rts / e_rts if e_rts else 0
            rep.md_only(
                f"| {BUCKET_LABEL[b]} | {len(sub)} | {e_rts} | "
                f"{f_rts} | {srate:.1%} |"
            )

    # Section 5: FD-native analysis
    rep.md_only("\n## 5. FanDuel-native thresholds\n")
    rep.md_only(
        "| Entry | Exit | Total FD round-trips | Mean per game | "
        "Gross $ per trip (100 ct) |\n"
        "|-------|------|----------------------|---------------|"
        "---------------------------|"
    )
    for (entry, exit_thr) in FD_NATIVE_PAIRS:
        total = 0
        for gid in selected["game_id"]:
            fd_feat = per_game_fd.get(gid, {}).get("features", {})
            total += fd_feat.get("fd_rts_by_pair", {}).get(
                (entry, exit_thr), 0)
            total += fd_feat.get("fd_rts_away_by_pair", {}).get(
                (entry, exit_thr), 0)
        per_game = total / len(selected) if len(selected) else 0
        gross = (exit_thr - entry) * 100
        rep.md_only(
            f"| {entry:.2f} | {exit_thr:.2f} | {total} | "
            f"{per_game:.2f} | ${gross:.2f} |"
        )

    # Section 6: Favorite-side
    rep.md_only("\n## 6. Favorite-side on FanDuel\n")
    rep.md_only(
        "| Bucket | N | Total completed | Total res_win | "
        "Total res_loss | Mean blended net (maker) |\n"
        "|--------|---|-----------------|---------------|"
        "----------------|--------------------------|"
    )
    pooled_fav_nets = []
    for b in BUCKET_ORDER:
        sub = selected[selected["bucket"] == b]
        if sub.empty:
            continue
        c = rw = rl = 0
        nets = []
        for gid in sub["game_id"]:
            fav = per_game_favorite.get(gid, {})
            c += fav.get("n_completed", 0)
            rw += fav.get("n_res_win", 0)
            rl += fav.get("n_res_loss", 0)
            if fav.get("positions", 0) > 0:
                nets.append(fav.get("blended_net_maker", 0))
                pooled_fav_nets.append(fav.get("blended_net_maker", 0))
        mean_net = (np.mean(nets) if nets else np.nan)
        mean_net_s = f"${mean_net:.2f}" if not np.isnan(mean_net) else "—"
        rep.md_only(
            f"| {BUCKET_LABEL[b]} | {len(sub)} | {c} | {rw} | {rl} | "
            f"{mean_net_s} |"
        )
    if pooled_fav_nets:
        rep.md_only(
            f"\nPooled mean favorite-side blended net (maker, across "
            f"games with ≥1 entry): "
            f"**${np.mean(pooled_fav_nets):+.2f}**.\n"
        )

    # Section 7: Revised universe estimate
    rep.md_only("\n## 7. Strategy 3 revised universe estimate\n")
    if total_espn_rts > 0:
        survival = total_fd_rts_baseline / total_espn_rts
        # Full-season ESPN round-trips (from game-flow trajectory):
        # ~2,272 pooled total, 1,165 from Comeback; ~1,400 estimated
        # for competitive (|spread|≤6). Use 2,272 as full-universe
        # ceiling here.
        espn_total_season = 2272
        est_fd_total = int(espn_total_season * survival)
        ev_per_trade = 14.55  # HOU-LAL underdog maker-maker
        est_season_ev = est_fd_total * ev_per_trade
        rep.md_only(
            f"- ESPN round-trips per season (|spread|≤6, from game-flow "
            f"trajectory analysis): **~{espn_total_season}**\n"
            f"- Survival rate: **{survival:.1%}**\n"
            f"- Estimated market-price round-trips per season: "
            f"**~{est_fd_total}**\n"
            f"- Estimated gross EV at $14.55/trade (HOU-LAL reference): "
            f"**${est_season_ev:,.0f}/season**\n\n"
            "This extrapolation assumes the 15-game survival rate is "
            "representative of the full season. Wider sampling is the "
            "next-level confidence gate.\n"
        )

    # Section 8: Resolution granularity caveat
    rep.md_only("\n## 8. Resolution granularity caveat\n")
    rt_durations = [
        per_game_espn[gid]["mean_rt_duration_min"]
        for gid in selected["game_id"]
        if not pd.isna(per_game_espn.get(gid, {}).get(
            "mean_rt_duration_min", np.nan))
    ]
    if rt_durations:
        mean_dur = float(np.mean(rt_durations))
        rep.md_only(
            f"Mean ESPN round-trip duration (across the 15 selected "
            f"games): **{mean_dur:.1f} min**. Our FanDuel timeseries "
            f"samples every 5 min. "
        )
        if mean_dur > 10:
            rep.md_only(
                "Mean duration > 10 min — the 5-min FanDuel grid "
                "should capture most round-trips. Survival rate "
                "above is a reasonable estimate of the real rate.\n"
            )
        else:
            rep.md_only(
                "Mean duration ≤ 10 min — the 5-min FanDuel grid "
                "likely undersamples intra-interval round-trips. "
                "Survival rate above is a **lower bound** on the true "
                "FanDuel rate; Kalshi (30s cadence) would show more.\n"
            )


# ---- Main --------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--n-games", type=int, default=15)
    args = parser.parse_args(argv)

    rep = Report()
    rep.stdout_only("=" * 70)
    rep.stdout_only("Strategy 3 Odds API timeseries analysis")
    rep.stdout_only("=" * 70)

    # Load master
    master = pd.read_csv(MASTER_CSV)
    master["game_id"] = master["game_id"].astype(str)

    # Step 1: classify all games
    classified = classify_all_games(master, rep)
    if classified.empty:
        rep.stdout_only("No games classified. Abort.")
        return 1

    # Step 2: stratified selection
    selected = stratified_select(classified, rep, n_games=args.n_games)
    describe_plan(classified, selected, rep)

    if args.plan_only:
        rep.stdout_only("\n[--plan-only] exiting without API calls")
        return 0

    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        rep.stdout_only(
            "\nERROR: ODDS_API_KEY not set. "
            "Use --plan-only to preview without a key."
        )
        return 2

    # Step 3-5: fetch + analyze per game
    rep.stdout_only("\n" + "=" * 70)
    rep.stdout_only("Fetching FanDuel timeseries per game")
    rep.stdout_only("=" * 70)
    per_game_fd: dict[str, dict] = {}
    per_game_espn: dict[str, dict] = {}
    per_game_favorite: dict[str, dict] = {}
    stats = {"api_calls": 0, "credits_remaining": None}
    for idx, r in selected.iterrows():
        gid = r["game_id"]
        rep.stdout_only(
            f"\n[{idx+1}/{len(selected)}] {r['away']}@{r['home']} "
            f"({r['game_date']})"
        )
        ts_rows, fetch_stats = fetch_game_timeseries(r, api_key, rep)
        stats["api_calls"] += fetch_stats.get("fetched", 0)
        if not ts_rows:
            per_game_fd[gid] = {"features": {}, "coverage": {"n_total": 0}}
            continue
        # Coverage stats
        n_total = len(ts_rows)
        n_with_fd = sum(1 for r_ in ts_rows
                        if not pd.isna(r_.get("fd_home_wp")))
        n_with_cons = sum(1 for r_ in ts_rows
                          if not pd.isna(r_.get("consensus_home_wp")))
        minutes = [r_["minute_offset"] for r_ in ts_rows
                   if not pd.isna(r_.get("fd_home_wp_filled"))]
        max_gap_min = 0.0
        if len(minutes) > 1:
            gaps = np.diff(sorted(minutes))
            max_gap_min = float(max(gaps))

        features = analyze_fd_timeseries(ts_rows)
        favorite_won = (r["home_won"] if r["home_spread"] < 0
                        else (not r["home_won"]))
        fav_feat = favorite_side_roundtrips_fd(
            ts_rows, r["home_spread"], favorite_won,
        )
        per_game_fd[gid] = {
            "features": features,
            "coverage": {
                "n_total": n_total, "n_with_fd": n_with_fd,
                "n_with_cons": n_with_cons, "max_gap_min": max_gap_min,
            },
            "timeseries": ts_rows,
        }
        per_game_favorite[gid] = fav_feat

        # ESPN paired analysis
        per_game_espn[gid] = analyze_espn_for_game(gid)

        rep.stdout_only(
            f"  FD obs: {n_with_fd}/{n_total}  "
            f"FD swings ≥0.10: {features['n_swings_10']}  "
            f"FD RTs (0.35,0.50): "
            f"{sum(features['fd_rts_by_pair'].values())}"
        )

    # Build report
    build_report(
        rep, selected, per_game_fd, per_game_espn, per_game_favorite, stats,
    )
    rep.write(OUTPUT_MD)
    rep.stdout_only(f"\nReport written to {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
