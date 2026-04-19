"""
Strategy 1 sportsbook backfill — bilateral dip validation.

For each bilateral <0.20 game identified from ESPN data, query The
Odds API's historical endpoints at the exact wallclock moments when
the two sides dipped. Produce a consensus sportsbook probability at
each dip and compare against ESPN's WP.

This is the load-bearing real-money test for Strategy 1. If
sportsbook consensus at dip moments tracks ESPN, the opportunity is
real on real-money markets. If it's compressed (like Kalshi appears
to be in the Phase 3B smoke test), Strategy 1's addressable universe
on sportsbooks is smaller than ESPN suggests.

Usage:
    python -m analysis.strategy1_sportsbook_backfill --plan-only
    python -m analysis.strategy1_sportsbook_backfill
    python -m analysis.strategy1_sportsbook_backfill --n-games 15

Requires ODDS_API_KEY in environment for full run. --plan-only needs
no API key.

Response-structure note: endpoints coded against The Odds API v4 docs
as of 2026-04-17 (see docs/ODDS_API_INTEGRATION.md). Parsing is
defensive — logs unexpected shape and skips the row. On first real
run, operator should spot-check the cached raw JSONs under
data/odds_api_historical/strategy1_backfill/ to confirm the assumed
structure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median, pstdev
from typing import Any

import numpy as np
import pandas as pd

# Reuse helpers and the Report class from phase_3a_followup
from analysis.phase_3a_followup import (
    Report,
    _BBREF_NAME_TO_ABBR,
    extract_period_num,
    parse_clock,
    sec_rem_in_period,
    elapsed_sec,
)
from scrapers.espn_scraper import _norm_team

MASTER_CSV = Path("data/nba_master_2025_26.csv")
WP_DIR = Path("data/espn_wp")
PBP_DIR = Path("data/pbp")
CACHE_DIR = Path("data/odds_api_historical/strategy1_backfill")
OUTPUT_MD = Path("docs/analysis_outputs/strategy1_sportsbook_backfill.md")

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
RATE_LIMIT_SEC = 1.0
REQUEST_TIMEOUT_SEC = 30
STALE_QUOTE_SEC = 300          # >5 min between quote last_update and target
CREDITS_PER_EVENT_ODDS = 10    # per docs/ODDS_API_INTEGRATION.md
CREDITS_PER_EVENTS_LIST = 1    # conservative estimate; actual billed via headers

DIP_BUCKETS = [0.0, 0.05, 0.10, 0.15, 0.20]

# Odds API uses full team names. Start from _BBREF_NAME_TO_ABBR (30 teams
# identical). Extend here if Odds API varies — add as observed.
_ODDS_API_NAME_TO_ABBR = dict(_BBREF_NAME_TO_ABBR)


# ---- Data loading (mirrors phase_3b_smoke_test conventions) -----------

def load_espn_timeline(game_id: str) -> pd.DataFrame:
    """Load ESPN WP + PBP, join on playId=id, return per-play timeline."""
    wp_path = WP_DIR / f"{game_id}.jsonl"
    pbp_path = PBP_DIR / f"{game_id}.jsonl"
    if not wp_path.exists() or wp_path.stat().st_size == 0:
        return pd.DataFrame()
    if not pbp_path.exists() or pbp_path.stat().st_size == 0:
        return pd.DataFrame()
    wp_rows = [json.loads(L) for L in wp_path.read_text().splitlines() if L.strip()]
    pbp_rows = [json.loads(L) for L in pbp_path.read_text().splitlines() if L.strip()]
    if not wp_rows or not pbp_rows:
        return pd.DataFrame()
    wp = pd.DataFrame(wp_rows)
    pbp = pd.DataFrame(pbp_rows)
    merged = wp.merge(
        pbp, left_on=["game_id", "playId"], right_on=["game_id", "id"],
        how="inner",
    )
    merged["wallclock_dt"] = pd.to_datetime(
        merged["wallclock"], utc=True, errors="coerce"
    )
    merged["home_wp"] = pd.to_numeric(merged["homeWinPercentage"], errors="coerce")
    merged["period_num"] = merged["period"].apply(extract_period_num)
    merged["clock_str"] = merged["clock"].apply(
        lambda c: c.get("displayValue") if isinstance(c, dict) else c
    )
    merged["clock_sec"] = merged["clock"].apply(parse_clock)
    merged["sec_rem"] = [
        sec_rem_in_period(p, c)
        for p, c in zip(merged["period_num"], merged["clock_sec"])
    ]
    merged = merged.dropna(
        subset=["wallclock_dt", "home_wp", "sec_rem"]
    ).sort_values("wallclock_dt").reset_index(drop=True)
    return merged[[
        "game_id", "wallclock_dt", "home_wp", "period_num",
        "clock_str", "sec_rem", "homeScore", "awayScore",
    ]]


# ---- Bilateral identification (mirrors Phase 3A logic) -----------------

def identify_bilaterals(
    master: pd.DataFrame,
    threshold: float = 0.20,
    max_abs_spread: float = 6.0,
    sec_rem_min: float = 60.0,
) -> pd.DataFrame:
    """Return one row per bilateral <threshold game at |spread|<=max_abs_spread.
    Columns: game_id, game_date, home, away, home_spread, min_home_wp,
    min_away_wp, home_dip_wallclock, away_dip_wallclock, scores at each dip."""
    rows = []
    competitive = master[master["home_spread"].abs() <= max_abs_spread]
    for _, g in competitive.iterrows():
        gid = str(g["game_id"])
        timeline = load_espn_timeline(gid)
        if timeline.empty:
            continue
        tradeable = timeline[timeline["sec_rem"] >= sec_rem_min]
        if tradeable.empty:
            continue
        tradeable = tradeable.copy()
        tradeable["away_wp"] = 1.0 - tradeable["home_wp"]
        h_idx = tradeable["home_wp"].idxmin()
        a_idx = tradeable["away_wp"].idxmin()
        h_row = tradeable.loc[h_idx]
        a_row = tradeable.loc[a_idx]
        if (float(h_row["home_wp"]) < threshold
                and float(a_row["away_wp"]) < threshold):
            rows.append({
                "game_id": gid,
                "game_date": g["game_date"],
                "home": _norm_team(g["home_team_abbrev"]),
                "away": _norm_team(g["away_team_abbrev"]),
                "home_spread": float(g["home_spread"]),
                "min_home_wp": float(h_row["home_wp"]),
                "min_away_wp": float(a_row["away_wp"]),
                "home_dip_wallclock": h_row["wallclock_dt"],
                "away_dip_wallclock": a_row["wallclock_dt"],
                "home_dip_score": f"{int(h_row['awayScore'])}-{int(h_row['homeScore'])}",
                "away_dip_score": f"{int(a_row['awayScore'])}-{int(a_row['homeScore'])}",
                "home_dip_period": h_row["period_num"],
                "home_dip_clock": h_row["clock_str"],
                "away_dip_period": a_row["period_num"],
                "away_dip_clock": a_row["clock_str"],
                "tip_wallclock": timeline["wallclock_dt"].iloc[0],
            })
    return pd.DataFrame(rows)


def stratified_sample(bilaterals: pd.DataFrame, n_target: int = 30,
                      rng_seed: int = 42) -> pd.DataFrame:
    """Stratify by season-third × spread bucket; prefer deeper dips."""
    if bilaterals.empty:
        return bilaterals
    b = bilaterals.copy()
    b["game_date_dt"] = pd.to_datetime(b["game_date"])
    b = b.sort_values("game_date_dt").reset_index(drop=True)
    n = len(b)
    third_edges = [n // 3, 2 * n // 3]
    b["season_third"] = 0
    b.loc[third_edges[0]:third_edges[1] - 1, "season_third"] = 1
    b.loc[third_edges[1]:, "season_third"] = 2
    b["spread_bucket"] = (b["home_spread"].abs() > 3.0).astype(int)  # 0 = tight, 1 = moderate
    b["deep_dip"] = b[["min_home_wp", "min_away_wp"]].min(axis=1)

    per_stratum_target = max(1, n_target // 6)
    chosen = []
    for third in (0, 1, 2):
        for spread_b in (0, 1):
            group = b[(b["season_third"] == third)
                      & (b["spread_bucket"] == spread_b)]
            picks = group.sort_values("deep_dip").head(per_stratum_target)
            chosen.append(picks)
    out = pd.concat(chosen).reset_index(drop=True)
    # If we fell short of n_target due to empty strata, top up with
    # remaining deep-dip games not yet selected.
    if len(out) < n_target:
        remaining = b[~b["game_id"].isin(set(out["game_id"]))]
        topup = remaining.sort_values("deep_dip").head(n_target - len(out))
        out = pd.concat([out, topup]).reset_index(drop=True)
    # If we overshot, drop from the densest strata deterministically.
    return out.head(n_target).reset_index(drop=True)


# ---- Odds API helpers --------------------------------------------------

def _get_json(
    url: str, params: dict, rep: Report,
) -> tuple[dict | list | None, dict[str, str]]:
    """HTTP GET with robust error handling. Returns (body, headers)."""
    import requests  # local import to avoid cost at --plan-only time
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SEC)
    except Exception as e:
        rep.stdout_only(f"    HTTP error: {e}")
        return None, {}
    headers = {k.lower(): v for k, v in r.headers.items()}
    if r.status_code != 200:
        rep.stdout_only(
            f"    HTTP {r.status_code}: {r.text[:200]}"
        )
        return None, headers
    try:
        return r.json(), headers
    except Exception as e:
        rep.stdout_only(f"    JSON parse error: {e}")
        return None, headers


def fetch_historical_events(
    api_key: str, snapshot_iso: str, rep: Report,
) -> tuple[list[dict], dict[str, str]]:
    """List historical NBA events at a given snapshot timestamp."""
    cache_key = snapshot_iso.replace(":", "").replace("-", "")[:15]
    cache_path = CACHE_DIR / f"events_{cache_key}.json"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        return cached.get("data", cached), cached.get("_headers", {})
    url = f"{ODDS_API_BASE}/historical/sports/basketball_nba/events/"
    params = {"apiKey": api_key, "date": snapshot_iso}
    body, headers = _get_json(url, params, rep)
    if body is None:
        return [], headers
    # Historical-events responses typically wrap data; accept either shape
    events = body if isinstance(body, list) else body.get("data", body)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(
        {"data": events, "_headers": {k: headers.get(k) for k in
                                       ("x-requests-remaining",
                                        "x-requests-used",
                                        "x-requests-last")}},
        default=str,
    ))
    return events if isinstance(events, list) else [], headers


def fetch_historical_event_odds(
    api_key: str, event_id: str, snapshot_iso: str, rep: Report,
    cache_filename: str,
) -> tuple[dict | None, dict[str, str]]:
    """Fetch h2h odds for a single event at a given snapshot timestamp."""
    cache_path = CACHE_DIR / cache_filename
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        return cached.get("data"), cached.get("_headers", {})
    url = (f"{ODDS_API_BASE}/historical/sports/basketball_nba/events/"
           f"{event_id}/odds")
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "date": snapshot_iso,
    }
    body, headers = _get_json(url, params, rep)
    if body is None:
        return None, headers
    # v4 historical event odds returns {timestamp, data: {...}, ...}
    data = body.get("data") if isinstance(body, dict) else body
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(
        {"data": data, "_headers": {k: headers.get(k) for k in
                                     ("x-requests-remaining",
                                      "x-requests-used",
                                      "x-requests-last")},
         "raw": body},
        default=str,
    ))
    return data, headers


def parse_bookmaker_h2h(
    data: dict, home_name: str, away_name: str, target_ts: datetime,
) -> list[dict]:
    """Extract per-bookmaker h2h decimal odds from an event-odds response.
    Returns one row per bookmaker with decimal odds + implied + no-vig +
    freshness info."""
    rows = []
    if not isinstance(data, dict):
        return rows
    bookmakers = data.get("bookmakers") or []
    for b in bookmakers:
        key = b.get("key")
        title = b.get("title", key)
        bk_last_update = b.get("last_update")
        try:
            bk_last_dt = datetime.fromisoformat(
                bk_last_update.replace("Z", "+00:00")
            ) if bk_last_update else None
        except (AttributeError, ValueError):
            bk_last_dt = None
        if bk_last_dt is None:
            staleness_sec = None
        else:
            staleness_sec = abs((target_ts - bk_last_dt).total_seconds())
        # Find h2h market
        home_dec = away_dec = None
        for m in b.get("markets", []) or []:
            if m.get("key") != "h2h":
                continue
            for o in m.get("outcomes", []) or []:
                name = o.get("name", "")
                price = o.get("price")
                if price is None:
                    continue
                try:
                    price_f = float(price)
                except (TypeError, ValueError):
                    continue
                if name == home_name:
                    home_dec = price_f
                elif name == away_name:
                    away_dec = price_f
        if home_dec is None or away_dec is None or home_dec <= 1 or away_dec <= 1:
            continue
        home_implied = 1.0 / home_dec
        away_implied = 1.0 / away_dec
        overround = home_implied + away_implied
        if overround <= 0:
            continue
        home_novig = home_implied / overround
        away_novig = away_implied / overround
        rows.append({
            "bookmaker_key": key, "bookmaker_title": title,
            "last_update": bk_last_update,
            "staleness_sec": staleness_sec,
            "home_decimal": home_dec, "away_decimal": away_dec,
            "home_implied": home_implied, "away_implied": away_implied,
            "overround": overround,
            "home_novig": home_novig, "away_novig": away_novig,
        })
    return rows


# ---- Reporting helpers -------------------------------------------------

def describe_plan(plan: pd.DataFrame, rep: Report, credit_budget: int) -> None:
    rep.stdout_only("")
    rep.stdout_only(f"=== Query Plan ({len(plan)} games) ===")
    rep.stdout_only(
        f"\n{'#':>2s}  {'gameId':<10s} {'date':<10s} {'away':<4s} {'home':<4s} "
        f"{'spread':>7s}  {'minH_wp':>7s} {'minA_wp':>7s}  "
        f"{'home_dip_wallclock':<20s}  {'away_dip_wallclock':<20s}"
    )
    for i, r in plan.iterrows():
        rep.stdout_only(
            f"{i+1:>2d}  {r['game_id']:<10s} {str(r['game_date']):<10s} "
            f"{r['away']:<4s} {r['home']:<4s} "
            f"{r['home_spread']:>+7.1f}  "
            f"{r['min_home_wp']:>7.3f} {r['min_away_wp']:>7.3f}  "
            f"{str(r['home_dip_wallclock'])[:19]:<20s}  "
            f"{str(r['away_dip_wallclock'])[:19]:<20s}"
        )

    unique_dates = plan["game_date"].nunique()
    event_odds_calls = 2 * len(plan)
    events_credits = unique_dates * CREDITS_PER_EVENTS_LIST
    odds_credits = event_odds_calls * CREDITS_PER_EVENT_ODDS
    total = events_credits + odds_credits
    rep.stdout_only(
        f"\nAPI calls needed:"
        f"\n  Event discovery: {unique_dates} unique dates × "
        f"{CREDITS_PER_EVENTS_LIST} credit ≈ {events_credits} credits"
        f"\n  Event odds:      {event_odds_calls} calls × "
        f"{CREDITS_PER_EVENT_ODDS} credits = {odds_credits} credits"
        f"\n  Estimated total: {total} credits"
    )
    if credit_budget:
        rep.stdout_only(f"  Monthly budget:  {credit_budget} credits "
                        f"(this run ≈ {total / credit_budget * 100:.1f}% of budget)")


def bucket_table(rep: Report, rows: list[dict], label: str) -> None:
    if not rows:
        rep.say(f"\n{label}: no data")
        return
    df = pd.DataFrame(rows).dropna(subset=["espn_wp", "sb_consensus", "residual"])
    if df.empty:
        rep.say(f"\n{label}: no paired data after filter")
        return
    df["bucket"] = pd.cut(df["espn_wp"], bins=DIP_BUCKETS,
                          include_lowest=True, right=True)
    agg = df.groupby("bucket", observed=True).agg(
        n=("residual", "size"),
        mean_espn=("espn_wp", "mean"),
        mean_sb=("sb_consensus", "mean"),
        mean_residual_pp=("residual", lambda x: x.mean() * 100),
    )
    rep.say("")
    rep.say(f"#### {label}\n")
    rep.stdout_only(
        f"{'bucket':<16s}  {'n':>4s}  {'mean ESPN':>10s}  "
        f"{'mean SB':>10s}  {'residual (pp)':>14s}"
    )
    rep.md_only(
        "| bucket | n | mean ESPN | mean SB | residual (pp) |\n"
        "|--------|---|-----------|---------|---------------|"
    )
    for idx, row in agg.iterrows():
        rep.stdout_only(
            f"{str(idx):<16s}  {int(row['n']):>4d}  "
            f"{row['mean_espn']:>10.3f}  {row['mean_sb']:>10.3f}  "
            f"{row['mean_residual_pp']:>+13.2f}"
        )
        rep.md_only(
            f"| {str(idx)} | {int(row['n'])} | {row['mean_espn']:.3f} | "
            f"{row['mean_sb']:.3f} | {row['mean_residual_pp']:+.2f} |"
        )


# ---- Orchestration -----------------------------------------------------

def run_backfill(
    plan: pd.DataFrame, api_key: str, rep: Report,
) -> tuple[list[dict], dict[str, int]]:
    """Execute API calls and build the per-(game, moment, bookmaker) table.
    Returns (rows, stats) where stats has credits/failures counters."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: discover events by snapshot date. Use tip_wallclock - 1h as
    # the discovery snapshot (events are usually listed hours before tip).
    rows_out: list[dict] = []
    failures: list[dict] = []
    calls = 0
    credits_remaining = None

    # Group queries by discovery-snapshot-iso to avoid duplicate events calls
    event_cache: dict[str, dict[tuple[str, str], str]] = {}
    #   keyed by snapshot_iso → {(home_abbr, away_abbr): event_id}

    for idx, pr in plan.iterrows():
        # One discovery snapshot per unique date suffices; use a fixed
        # time-of-day to keep the cache key stable.
        snapshot_iso = _discovery_snapshot_for(pr["tip_wallclock"])
        if snapshot_iso not in event_cache:
            rep.stdout_only(f"  [events] date={snapshot_iso}")
            events, headers = fetch_historical_events(
                api_key, snapshot_iso, rep,
            )
            calls += 1
            credits_remaining = headers.get("x-requests-remaining") or credits_remaining
            event_cache[snapshot_iso] = _build_event_index(events)
            time.sleep(RATE_LIMIT_SEC)

        index = event_cache[snapshot_iso]
        home_abbr, away_abbr = pr["home"], pr["away"]
        event_id = index.get((home_abbr, away_abbr))
        if event_id is None:
            rep.stdout_only(
                f"  [skip] no Odds API event for {away_abbr}@{home_abbr} "
                f"on {pr['game_date']}"
            )
            failures.append({
                "game_id": pr["game_id"],
                "reason": "event_not_found",
                "matchup": f"{away_abbr}@{home_abbr}",
                "date": pr["game_date"],
            })
            continue

        # Step 2: fetch odds at each dip moment
        for moment in ("home_dip", "away_dip"):
            wall = pr[f"{moment}_wallclock"]
            wall_iso = _iso_utc(wall)
            cache_fn = f"{pr['game_id']}_{moment}.json"
            rep.stdout_only(
                f"  [odds ] {pr['game_id']} {moment} @ {wall_iso}"
            )
            data, headers = fetch_historical_event_odds(
                api_key, event_id, wall_iso, rep, cache_fn,
            )
            calls += 1
            credits_remaining = headers.get("x-requests-remaining") or credits_remaining
            time.sleep(RATE_LIMIT_SEC)
            if data is None:
                failures.append({
                    "game_id": pr["game_id"],
                    "reason": "odds_fetch_failed",
                    "moment": moment,
                    "matchup": f"{away_abbr}@{home_abbr}",
                })
                continue
            home_name = data.get("home_team") or _abbr_to_name(home_abbr)
            away_name = data.get("away_team") or _abbr_to_name(away_abbr)
            parsed_books = parse_bookmaker_h2h(
                data, home_name, away_name,
                wall if isinstance(wall, datetime) else pd.Timestamp(wall).to_pydatetime(),
            )
            if not parsed_books:
                failures.append({
                    "game_id": pr["game_id"],
                    "reason": "no_bookmakers_parsed",
                    "moment": moment,
                    "matchup": f"{away_abbr}@{home_abbr}",
                })
                continue

            # ESPN WP at this moment — which side we're evaluating
            if moment == "home_dip":
                espn_wp_side = float(pr["min_home_wp"])
            else:
                espn_wp_side = float(pr["min_away_wp"])

            for b in parsed_books:
                stale = (b["staleness_sec"] is None
                         or b["staleness_sec"] > STALE_QUOTE_SEC)
                novig_side = (b["home_novig"] if moment == "home_dip"
                              else b["away_novig"])
                rows_out.append({
                    "game_id": pr["game_id"],
                    "date": str(pr["game_date"]),
                    "home": home_abbr, "away": away_abbr,
                    "home_spread": pr["home_spread"],
                    "moment": moment,
                    "bookmaker_key": b["bookmaker_key"],
                    "bookmaker_title": b["bookmaker_title"],
                    "home_decimal": b["home_decimal"],
                    "away_decimal": b["away_decimal"],
                    "home_novig": b["home_novig"],
                    "away_novig": b["away_novig"],
                    "overround": b["overround"],
                    "staleness_sec": b["staleness_sec"],
                    "stale": stale,
                    "espn_wp_side": espn_wp_side,
                    "sb_novig_side": novig_side,
                })

        if (idx + 1) % 5 == 0 and credits_remaining:
            rep.stdout_only(f"    credits remaining: {credits_remaining}")

    stats = {
        "api_calls": calls,
        "n_rows": len(rows_out),
        "n_failures": len(failures),
        "credits_remaining": credits_remaining,
    }
    return rows_out, stats, failures  # type: ignore[return-value]


def _iso_utc(ts: Any) -> str:
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return pd.Timestamp(ts).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _discovery_snapshot_for(tip_wallclock: Any) -> str:
    """Snapshot datetime for event-list query — one hour before tip."""
    ts = pd.Timestamp(tip_wallclock).tz_convert("UTC") - pd.Timedelta(hours=1)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_event_index(events: list[dict]) -> dict[tuple[str, str], str]:
    """Map (home_abbr, away_abbr) → event_id for NBA events returned by
    the historical events endpoint."""
    index: dict[tuple[str, str], str] = {}
    for e in events or []:
        home_name = e.get("home_team") or ""
        away_name = e.get("away_team") or ""
        home_abbr = _ODDS_API_NAME_TO_ABBR.get(home_name)
        away_abbr = _ODDS_API_NAME_TO_ABBR.get(away_name)
        if home_abbr and away_abbr and e.get("id"):
            index[(home_abbr, away_abbr)] = e["id"]
    return index


def _abbr_to_name(abbr: str) -> str:
    """Inverse of _ODDS_API_NAME_TO_ABBR for one team abbreviation."""
    for name, a in _ODDS_API_NAME_TO_ABBR.items():
        if a == abbr:
            return name
    return abbr


# ---- Analysis + report -------------------------------------------------

def analyze_and_report(
    rep: Report, rows: list[dict], stats: dict[str, int],
    failures: list[dict], sample_size: int, bilateral_count: int,
) -> None:
    rep.md_only(f"# Strategy 1 sportsbook backfill — {date.today().isoformat()}\n")
    rep.md_only(
        "Targeted historical Odds API backfill at the exact moments of "
        "bilateral <0.20 dips identified from ESPN data. Each dip moment "
        "produces one sportsbook consensus observation per available "
        "bookmaker, no-vig normalized. The question answered: **do "
        "real-money sportsbooks agree with ESPN at the moments that "
        "drive Strategy 1's opportunity rate?**\n"
    )

    # ---- A. Sample summary ----
    rep.say("\n=== A. Sample summary ===")
    rep.md_only("\n## A. Sample summary\n")
    fresh = [r for r in rows if not r.get("stale")]
    stale = len(rows) - len(fresh)
    stats_rows = [
        ("Bilateral games in population", f"~{bilateral_count}"),
        ("Sample size", str(sample_size)),
        ("API calls made", str(stats.get("api_calls", 0))),
        ("Credits remaining (per headers)",
         str(stats.get("credits_remaining") or "unknown")),
        ("Bookmaker rows (total)", str(len(rows))),
        ("Bookmaker rows (fresh, last_update within 5 min)", str(len(fresh))),
        ("Stale rows excluded from consensus", str(stale)),
        ("Failures", str(stats.get("n_failures", 0))),
    ]
    for k, v in stats_rows:
        rep.stdout_only(f"  {k:<42s}  {v}")
    rep.md_only("| Stat | Value |\n|------|-------|")
    for k, v in stats_rows:
        rep.md_only(f"| {k} | {v} |")

    if not fresh:
        rep.say("\nNo fresh bookmaker rows — cannot produce residuals.")
        return

    fresh_df = pd.DataFrame(fresh)

    # ---- Consensus per (game, moment) ----
    grp = fresh_df.groupby(["game_id", "moment"], as_index=False)
    consensus = grp.agg(
        date=("date", "first"),
        home=("home", "first"), away=("away", "first"),
        home_spread=("home_spread", "first"),
        espn_wp=("espn_wp_side", "first"),
        sb_consensus=("sb_novig_side", "median"),
        sb_mean=("sb_novig_side", "mean"),
        sb_std=("sb_novig_side", "std"),
        overround_mean=("overround", "mean"),
        n_books=("bookmaker_key", "nunique"),
    )
    consensus["residual"] = consensus["sb_consensus"] - consensus["espn_wp"]

    # ---- B. Per-game dip comparison table ----
    rep.say("\n=== B. Per-game dip comparison ===")
    rep.md_only("\n## B. Per-game dip comparison\n")
    rep.md_only(
        "| gameId | date | away | home | spread | side | ESPN WP | "
        "SB consensus | residual (pp) | n_books |\n"
        "|--------|------|------|------|--------|------|---------|"
        "--------------|---------------|---------|"
    )
    rep.stdout_only(
        f"{'gameId':<10s} {'date':<10s} {'away':>4s} {'home':>4s} "
        f"{'spread':>7s}  {'side':<9s} {'ESPN WP':>8s} "
        f"{'SB cons':>8s} {'resid':>7s}  {'n':>3s}"
    )
    for _, r in consensus.sort_values("espn_wp").iterrows():
        rep.stdout_only(
            f"{r['game_id']:<10s} {r['date']:<10s} {r['away']:>4s} "
            f"{r['home']:>4s} {r['home_spread']:>+7.1f}  "
            f"{r['moment']:<9s} {r['espn_wp']:>8.3f} {r['sb_consensus']:>8.3f} "
            f"{r['residual']*100:>+6.2f}pp {int(r['n_books']):>3d}"
        )
        rep.md_only(
            f"| {r['game_id']} | {r['date']} | {r['away']} | {r['home']} | "
            f"{r['home_spread']:+.1f} | {r['moment']} | "
            f"{r['espn_wp']:.3f} | {r['sb_consensus']:.3f} | "
            f"{r['residual']*100:+.2f}pp | {int(r['n_books'])} |"
        )

    # ---- C. Pooled residual ----
    rep.say("\n=== C. Pooled residual at dip moments ===")
    rep.md_only("\n## C. Pooled residual at dip moments\n")
    rvals = consensus["residual"].dropna()
    pooled_rows = [
        ("n (dip observations)", str(len(rvals))),
        ("mean ESPN WP at dip",
         f"{consensus['espn_wp'].mean():.4f}"),
        ("mean SB consensus at dip",
         f"{consensus['sb_consensus'].mean():.4f}"),
        ("mean residual (pp)", f"{rvals.mean()*100:+.2f}"),
        ("median residual (pp)", f"{rvals.median()*100:+.2f}"),
        ("std", f"{rvals.std():.4f}"),
    ]
    for k, v in pooled_rows:
        rep.stdout_only(f"  {k:<28s}  {v}")
    rep.md_only("| Stat | Value |\n|------|-------|")
    for k, v in pooled_rows:
        rep.md_only(f"| {k} | {v} |")

    # ---- D. Residual by ESPN WP bucket ----
    bucket_rows = consensus.rename(
        columns={"sb_consensus": "sb_consensus", "espn_wp": "espn_wp"}
    )[["espn_wp", "sb_consensus", "residual"]].to_dict("records")
    bucket_table(rep, bucket_rows, "D. Residual stratified by ESPN WP bucket at dip")

    # ---- E. Cross-book variance ----
    rep.say("\n=== E. Cross-book variance at dip moments ===")
    rep.md_only("\n## E. Cross-book variance at dip moments\n")
    stds = consensus["sb_std"].dropna()
    overrounds = consensus["overround_mean"].dropna()
    var_rows = [
        ("mean cross-book std (no-vig)",
         f"{stds.mean():.4f}" if len(stds) else "—"),
        ("p95 cross-book std",
         f"{stds.quantile(0.95):.4f}" if len(stds) else "—"),
        ("mean overround (vig indicator)",
         f"{overrounds.mean():.4f}" if len(overrounds) else "—"),
    ]
    for k, v in var_rows:
        rep.stdout_only(f"  {k:<32s}  {v}")
    rep.md_only("| Stat | Value |\n|------|-------|")
    for k, v in var_rows:
        rep.md_only(f"| {k} | {v} |")

    # ---- F. Preliminary assessment ----
    mean_res = rvals.mean()
    if mean_res <= 0.03:
        verdict = (
            "Sportsbooks track ESPN at bilateral dip moments. Strategy 1's "
            f"{bilateral_count}-game / 26.6% opportunity rate on ESPN data "
            "is a reasonable proxy for real-money markets. The Phase 3B "
            "Kalshi compression finding may be Kalshi-specific rather than "
            "a property of real-money pricing in general."
        )
    elif mean_res <= 0.08:
        verdict = (
            f"Sportsbooks show moderate compression vs ESPN at the tails "
            f"(mean residual {mean_res*100:+.2f}pp). Strategy 1's effective "
            "opportunity rate on real-money markets is lower than ESPN's "
            "26.6% but likely not zero. Recalibrate entry thresholds using "
            "sportsbook-implied WP rather than ESPN WP before any capital "
            "commitment."
        )
    else:
        verdict = (
            f"Sportsbooks show strong compression matching the Kalshi "
            f"pattern (mean residual {mean_res*100:+.2f}pp). Strategy 1's "
            "bilateral <0.20 opportunity rate on real-money markets is "
            "substantially lower than ESPN's 26.6% suggests. The bilateral "
            "opportunity may still exist at wider thresholds (e.g., <0.30 "
            "on sportsbook-implied WP), but per-trade gross profit shrinks "
            "and fee/spread drag becomes a larger share. Re-examine "
            "Strategy 1's graduation bar against the actual residual shape."
        )
    rep.say("\n=== F. Preliminary Strategy 1 assessment ===")
    rep.md_only("\n## F. Preliminary Strategy 1 assessment\n")
    rep.say(verdict)
    rep.md_only(verdict)
    rep.md_only(
        f"\n**Sample size note:** {sample_size} games with two dip "
        f"moments each ≈ {sample_size * 2} dip observations. A sample-based "
        "estimate; formal Strategy 1 conclusions require Phase 3B-scale "
        "validation once the Kalshi dataset grows."
    )

    if failures:
        rep.md_only("\n## Failures\n")
        rep.md_only("| game_id | reason | detail |\n|---|---|---|")
        for f in failures:
            detail = ", ".join(f"{k}={v}" for k, v in f.items()
                               if k not in ("game_id", "reason"))
            rep.md_only(f"| {f.get('game_id', '?')} | {f.get('reason', '?')}"
                        f" | {detail} |")


# ---- Main --------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n-games", type=int, default=30)
    p.add_argument("--plan-only", action="store_true")
    args = p.parse_args(argv)

    rep = Report()

    # Step 1: load master + identify bilaterals
    master = pd.read_csv(MASTER_CSV)
    master["game_id"] = master["game_id"].astype(str)
    rep.stdout_only("=" * 70)
    rep.stdout_only("Strategy 1 sportsbook backfill")
    rep.stdout_only("=" * 70)
    rep.stdout_only(f"\nLoading master + ESPN data, identifying bilaterals…")

    bilaterals = identify_bilaterals(master)
    rep.stdout_only(
        f"Bilateral <0.20 games at |spread|≤6: {len(bilaterals)}  "
        f"(Phase 3A baseline: 146)"
    )
    if abs(len(bilaterals) - 146) > 2:
        rep.stdout_only(
            f"  ⚠ count differs from Phase 3A by {len(bilaterals) - 146:+d}"
            "; investigate before trusting results"
        )

    # Step 2: stratified sample
    plan = stratified_sample(bilaterals, n_target=args.n_games)
    rep.stdout_only(f"\nStratified sample: {len(plan)} games")

    describe_plan(plan, rep, credit_budget=10000)

    if args.plan_only:
        rep.stdout_only("\n[--plan-only] exiting without API calls")
        return 0

    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        rep.stdout_only("\nERROR: ODDS_API_KEY not set. "
                        "Use --plan-only to preview without an API key.")
        return 2

    # Step 3: execute
    rep.stdout_only("\nExecuting Odds API backfill…")
    rows, stats, failures = run_backfill(plan, api_key, rep)

    # Step 4: analyze + write report
    analyze_and_report(
        rep, rows, stats, failures,
        sample_size=len(plan), bilateral_count=len(bilaterals),
    )

    rep.write(OUTPUT_MD)
    rep.stdout_only(f"\nReport written to {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
