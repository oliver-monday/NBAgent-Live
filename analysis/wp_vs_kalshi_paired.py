"""WP vs Kalshi paired analysis — per-game study.

Pairs ESPN win-probability timeseries with Kalshi historical trade
prices to study the relationship between the two across game time.
Favorite-centric reference frame. Produces a structured markdown
report, a continuous 30-second VWAP timeseries CSV, and an
event-driven scoring-play CSV.

Run:
    # Auto-resolve everything from team+date (preferred)
    python -m analysis.wp_vs_kalshi_paired --teams ORL@DET --date 2026-04-19

    # All games from a given date (loops over ESPN scoreboard)
    python -m analysis.wp_vs_kalshi_paired --date 2026-04-19 --all

    # Manual override path (legacy CLI)
    python -m analysis.wp_vs_kalshi_paired \\
        --espn-game-id 401869194 \\
        --kalshi-event-ticker KXNBAGAME-26APR19PORSAS \\
        --spread -10.5

    # Reuse cached API responses on any invocation
    python -m analysis.wp_vs_kalshi_paired --teams ORL@DET --date 2026-04-19 --cached
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

try:
    from scipy import stats as _scipy_stats  # type: ignore
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ---- Paths / constants --------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
REPORT_DIR = REPO_ROOT / "docs" / "analysis_outputs"

ESPN_SUMMARY_BASE = (
    "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
)
ESPN_SCOREBOARD_BASE = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
)
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

_MONTH_CODE = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]

REQUEST_TIMEOUT_SEC = 30
ESPN_SLEEP_SEC = 1.0
KALSHI_SLEEP_SEC = 0.25

# Game clock axis
Q_LEN_SEC = 720   # 12:00
OT_LEN_SEC = 300  # 5:00

# Bucket + match tolerances
VWAP_BUCKET_SEC = 30
TIMEOUT_FLANK_SEC = 60
SCORING_WINDOW_BEFORE_SEC = 5
SCORING_WINDOW_AFTER_MIN_SEC = 3
SCORING_WINDOW_AFTER_MAX_SEC = 15

# WP zone bands
WP_ZONES = [
    (0.00, 0.20, "0.00-0.20"),
    (0.20, 0.40, "0.20-0.40"),
    (0.40, 0.60, "0.40-0.60"),
    (0.60, 0.80, "0.60-0.80"),
    (0.80, 1.0001, "0.80-1.00"),
]

# Strategy 3 operating zone (favorite YES price bracket)
# Either fav in [0.35, 0.55] (underdog in [0.45, 0.65]) OR
# fav in [0.45, 0.65] (underdog in [0.35, 0.55]) — i.e., either side
# in the mid-range entry zone.
S3_FAV_LO = 0.35
S3_FAV_HI = 0.65

# Time-remaining buckets for convergence analysis (in minutes)
TR_BUCKETS = [
    (36 * 60, float("inf"), "> 36 min"),
    (24 * 60, 36 * 60, "24-36 min"),
    (12 * 60, 24 * 60, "12-24 min"),
    (6 * 60, 12 * 60, "6-12 min"),
    (3 * 60, 6 * 60, "3-6 min"),
    (1 * 60, 3 * 60, "1-3 min"),
    (0.0, 1 * 60, "0-1 min"),
]

# Copied from scrapers/espn_scraper.py — ESPN uses non-standard team
# abbreviations. Normalize to the standard NBA set.
_ABBR_NORM = {
    "GS": "GSW", "SA": "SAS", "NO": "NOP",
    "NY": "NYK", "UTAH": "UTA", "WSH": "WAS",
    "PHO": "PHX",
}


def _norm_team(abbr: str | None) -> str | None:
    if abbr is None:
        return None
    a = str(abbr).upper().strip()
    return _ABBR_NORM.get(a, a)


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


# ---- Data acquisition ---------------------------------------------------

def fetch_espn_summary(espn_game_id: str, cache_path: Path,
                      use_cached: bool) -> dict[str, Any]:
    if use_cached and cache_path.exists():
        log(f"Loading cached ESPN summary from {cache_path}")
        with cache_path.open() as f:
            return json.load(f)
    url = f"{ESPN_SUMMARY_BASE}?event={espn_game_id}"
    log(f"Fetching ESPN summary: {url}")
    r = requests.get(url, timeout=REQUEST_TIMEOUT_SEC)
    r.raise_for_status()
    data = r.json()
    time.sleep(ESPN_SLEEP_SEC)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w") as f:
        json.dump(data, f)
    log(f"Cached ESPN summary → {cache_path}")
    return data


def fetch_kalshi_tickers(event_ticker: str) -> list[str]:
    url = f"{KALSHI_BASE}/markets"
    log(f"Discovering Kalshi tickers for event: {event_ticker}")
    r = requests.get(
        url, params={"event_ticker": event_ticker, "limit": 50},
        timeout=REQUEST_TIMEOUT_SEC,
    )
    r.raise_for_status()
    markets = r.json().get("markets", [])
    tickers = sorted({m["ticker"] for m in markets if m.get("ticker")})
    log(f"Discovered tickers: {tickers}")
    return tickers


def fetch_all_trades_for_ticker(ticker: str) -> list[dict]:
    """Paginate /markets/trades for a single ticker.

    Pattern copied from analysis/kalshi_trades_probe.py. Note:
    /historical/trades returned empty for recent NBA markets on probe;
    /markets/trades returns the full tape.
    """
    url = f"{KALSHI_BASE}/markets/trades"
    all_trades: list[dict] = []
    cursor: str | None = None
    page = 0
    while True:
        params: dict[str, Any] = {"ticker": ticker, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SEC)
        r.raise_for_status()
        data = r.json()
        trades = data.get("trades", [])
        all_trades.extend(trades)
        page += 1
        cursor = data.get("cursor")
        if not cursor or not trades:
            break
        time.sleep(KALSHI_SLEEP_SEC)
    log(f"  {ticker}: {len(all_trades):,} trades across {page} page(s)")
    return all_trades


def fetch_kalshi_trades(event_ticker: str, cache_path: Path,
                        use_cached: bool) -> dict[str, Any]:
    if use_cached and cache_path.exists():
        log(f"Loading cached Kalshi trades from {cache_path}")
        with cache_path.open() as f:
            return json.load(f)
    tickers = fetch_kalshi_tickers(event_ticker)
    if not tickers:
        raise SystemExit(
            f"No Kalshi tickers found for event_ticker={event_ticker}"
        )
    all_trades: list[dict] = []
    for t in tickers:
        chunk = fetch_all_trades_for_ticker(t)
        all_trades.extend(chunk)
        time.sleep(KALSHI_SLEEP_SEC)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "event_ticker": event_ticker,
        "tickers": tickers,
        "trades": all_trades,
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w") as f:
        json.dump(payload, f)
    log(f"Cached Kalshi trades → {cache_path}")
    return payload


# ---- Auto-discovery resolvers -------------------------------------------

def _parse_date_arg(date_str: str | None) -> str:
    """Return YYYYMMDD for ESPN scoreboard. Default: today UTC."""
    if date_str is None:
        d = datetime.now(timezone.utc).date()
    else:
        # Accept YYYY-MM-DD or YYYYMMDD
        s = date_str.replace("-", "")
        d = datetime.strptime(s, "%Y%m%d").date()
    return d.strftime("%Y%m%d")


def kalshi_ticker_from_teams(
    away: str, home: str, date_yyyymmdd: str,
) -> str:
    """Deterministic Kalshi event ticker from date + teams.

    Convention: `KXNBAGAME-{YY}{MON}{DD}{AWAY}{HOME}` with month as
    three-letter uppercase code and team codes in ESPN-normalized form
    (HOU, LAL, POR, SAS, etc.).
    """
    yy = date_yyyymmdd[2:4]
    month_idx = int(date_yyyymmdd[4:6]) - 1
    mon = _MONTH_CODE[month_idx]
    dd = date_yyyymmdd[6:8]
    away_n = _norm_team(away) or away.upper()
    home_n = _norm_team(home) or home.upper()
    return f"KXNBAGAME-{yy}{mon}{dd}{away_n}{home_n}"


def scoreboard_games(date_yyyymmdd: str) -> list[dict]:
    """Return a list of {game_id, away, home, status} for a date."""
    url = f"{ESPN_SCOREBOARD_BASE}?dates={date_yyyymmdd}"
    log(f"Fetching scoreboard: {url}")
    r = requests.get(url, timeout=REQUEST_TIMEOUT_SEC)
    r.raise_for_status()
    data = r.json()
    out = []
    for ev in data.get("events", []):
        gid = ev.get("id")
        comps = (ev.get("competitions") or [{}])[0]
        teams = comps.get("competitors") or []
        away = home = None
        for c in teams:
            ab = _norm_team((c.get("team") or {}).get("abbreviation"))
            if c.get("homeAway") == "home":
                home = ab
            elif c.get("homeAway") == "away":
                away = ab
        status = (comps.get("status") or {}).get("type", {}).get("name", "")
        out.append({"game_id": gid, "away": away, "home": home,
                    "status": status})
    return out


def resolve_espn_game_id(
    away: str, home: str, date_yyyymmdd: str,
) -> tuple[str, str, str]:
    """Find the ESPN gameId for the matching team pair on the given date.

    Returns (game_id, canonical_away, canonical_home). If the user passed
    the teams in reversed home/away order, the returned tuple reflects
    ESPN's canonical ordering — downstream callers should use those for
    deriving Kalshi tickers, not the user's input.
    """
    away_n = _norm_team(away) or away.upper()
    home_n = _norm_team(home) or home.upper()
    games = scoreboard_games(date_yyyymmdd)
    for g in games:
        if g["away"] == away_n and g["home"] == home_n:
            return g["game_id"], g["away"], g["home"]
    # Unordered pair fallback: user may have typed reversed home/away.
    for g in games:
        pair = {g.get("away"), g.get("home")}
        if pair == {away_n, home_n}:
            log(
                f"Note: user input {away_n}@{home_n} doesn't match ESPN's "
                f"home/away ({g['away']}@{g['home']}). Using ESPN ordering."
            )
            return g["game_id"], g["away"], g["home"]
    raise SystemExit(
        f"No ESPN game found for {away_n}@{home_n} on {date_yyyymmdd}. "
        f"Scoreboard returned: "
        f"{[(g['game_id'], g['away'], g['home']) for g in games]}"
    )


def resolve_spread_from_summary(espn_data: dict) -> float | None:
    """Extract pre-game spread (home-centric) from ESPN `pickcenter`.

    ESPN `pickcenter[i].spread` is negative when the favorite wins by
    that many (favorite-centric); we translate it to home-centric to
    match our `--spread` convention (negative = home favored).
    """
    pc = espn_data.get("pickcenter") or []
    if not pc:
        return None
    entry = pc[0]
    spread_raw = entry.get("spread")
    if spread_raw is None:
        return None
    # Determine which side is favored. `awayTeamOdds.favorite` or
    # `homeTeamOdds.favorite` is the boolean marker.
    home_fav = bool((entry.get("homeTeamOdds") or {}).get("favorite"))
    away_fav = bool((entry.get("awayTeamOdds") or {}).get("favorite"))
    try:
        s = float(spread_raw)
    except (TypeError, ValueError):
        return None
    # ESPN's convention: `spread` field is the favorite's spread
    # (always negative). Convert to home-centric.
    if home_fav:
        return -abs(s)
    if away_fav:
        return abs(s)
    # Fall back to details string parsing ("DET -8.5", "ORL +8.5")
    details = entry.get("details") or ""
    parts = details.strip().split()
    if len(parts) >= 2:
        try:
            val = float(parts[1])
        except ValueError:
            return None
        # parts[0] is the favorite's abbreviation
        teams = espn_data.get("header", {}).get("competitions", [{}])[0].get(
            "competitors", [])
        home_abbr = None
        for c in teams:
            if c.get("homeAway") == "home":
                home_abbr = _norm_team((c.get("team") or {}).get("abbreviation"))
        fav_abbr = _norm_team(parts[0])
        return val if fav_abbr == home_abbr else -val
    return None


# ---- Parsing helpers ----------------------------------------------------

def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def parse_game_clock(clock_str: str | None) -> float | None:
    """Parse 'M:SS' or 'M:SS.t' into seconds remaining in the period."""
    if not clock_str:
        return None
    s = str(clock_str).strip()
    if ":" in s:
        parts = s.split(":")
        try:
            return int(parts[0]) * 60 + float(parts[1])
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def elapsed_from_period_clock(period: int, clock_sec: float | None) -> float | None:
    if period is None or clock_sec is None:
        return None
    p = int(period)
    if p <= 4:
        return (p - 1) * Q_LEN_SEC + (Q_LEN_SEC - clock_sec)
    return 4 * Q_LEN_SEC + (p - 5) * OT_LEN_SEC + (OT_LEN_SEC - clock_sec)


def total_game_length_sec(max_period: int) -> int:
    if max_period <= 4:
        return 4 * Q_LEN_SEC
    return 4 * Q_LEN_SEC + (max_period - 4) * OT_LEN_SEC


# ---- Favorite identification -------------------------------------------

def identify_favorite(
    metadata: dict, wp_entries: list[dict], spread: float | None,
) -> dict[str, Any]:
    """Return {fav_side: 'home'|'away', fav_team, dog_side, dog_team,
    pregame_fav_wp}."""
    teams = metadata.get("teams", [])
    home_team = metadata.get("home_team")
    away_team = metadata.get("away_team")
    pregame_home_wp = None
    if wp_entries:
        first = wp_entries[0]
        pregame_home_wp = float(first.get("homeWinPercentage", 0.5))
    if spread is not None:
        fav_side = "home" if spread < 0 else "away"
    else:
        if pregame_home_wp is None:
            fav_side = "home"
        else:
            fav_side = "home" if pregame_home_wp > 0.5 else "away"
    if fav_side == "home":
        fav_team, dog_team, dog_side = home_team, away_team, "away"
    else:
        fav_team, dog_team, dog_side = away_team, home_team, "home"
    pregame_fav_wp = None
    if pregame_home_wp is not None:
        pregame_fav_wp = (
            pregame_home_wp if fav_side == "home"
            else 1.0 - pregame_home_wp
        )
    return {
        "fav_side": fav_side,
        "fav_team": fav_team,
        "dog_side": dog_side,
        "dog_team": dog_team,
        "pregame_home_wp": pregame_home_wp,
        "pregame_fav_wp": pregame_fav_wp,
    }


def parse_metadata(espn_data: dict) -> dict[str, Any]:
    md: dict[str, Any] = {}
    header = espn_data.get("header") or {}
    comps = header.get("competitions") or []
    if not comps:
        return md
    comp = comps[0]
    md["date"] = comp.get("date")
    md["status"] = (comp.get("status") or {}).get("type", {}).get("name")
    teams = []
    for c in comp.get("competitors", []):
        t = c.get("team") or {}
        teams.append({
            "abbreviation": _norm_team(t.get("abbreviation")),
            "display_name": t.get("displayName"),
            "team_id": t.get("id"),
            "score": c.get("score"),
            "home_away": c.get("homeAway"),
            "winner": c.get("winner"),
        })
    md["teams"] = teams
    for t in teams:
        if t["home_away"] == "home":
            md["home_team"] = t["abbreviation"]
            md["home_score"] = t["score"]
        elif t["home_away"] == "away":
            md["away_team"] = t["abbreviation"]
            md["away_score"] = t["score"]
    return md


# ---- Ticker-side → favorite-side mapping --------------------------------

def map_ticker_to_side(tickers: list[str], home_team: str | None,
                       away_team: str | None) -> dict[str, str]:
    """Ticker suffix is the team abbreviation (e.g., ...-POR). Match
    against home/away abbreviations to decide which ticker is 'home'
    and which is 'away'."""
    out: dict[str, str] = {}
    for t in tickers:
        suffix = t.rsplit("-", 1)[-1]
        ab = _norm_team(suffix)
        if ab == home_team:
            out[t] = "home"
        elif ab == away_team:
            out[t] = "away"
        else:
            out[t] = "unknown"
    return out


# ---- Timeseries construction -------------------------------------------

def build_plays_df(plays: list[dict], fav_side: str) -> pd.DataFrame:
    """Return a DataFrame of plays with fav-centric fields."""
    rows = []
    for p in plays:
        wc = p.get("wallclock")
        if not wc:
            continue
        try:
            ts = _parse_iso(wc)
        except (ValueError, TypeError):
            continue
        period = (p.get("period") or {}).get("number")
        clock = (p.get("clock") or {}).get("displayValue")
        clock_sec = parse_game_clock(clock)
        elapsed = elapsed_from_period_clock(period, clock_sec)
        home_score = p.get("homeScore", 0) or 0
        away_score = p.get("awayScore", 0) or 0
        if fav_side == "home":
            fav_score, dog_score = home_score, away_score
        else:
            fav_score, dog_score = away_score, home_score
        rows.append({
            "play_id": p.get("id"),
            "sequence": int(p.get("sequenceNumber") or 0),
            "wallclock": ts,
            "period": int(period) if period is not None else None,
            "game_clock": clock,
            "game_clock_sec": clock_sec,
            "elapsed": elapsed,
            "home_score": home_score,
            "away_score": away_score,
            "fav_score": fav_score,
            "dog_score": dog_score,
            "score_margin": fav_score - dog_score,
            "play_type_id": str((p.get("type") or {}).get("id", "")),
            "play_type_text": (p.get("type") or {}).get("text", ""),
            "text": p.get("text", ""),
            "scoring_play": bool(p.get("scoringPlay")),
            "score_value": int(p.get("scoreValue") or 0),
            "team_id": (p.get("team") or {}).get("id"),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["wallclock", "sequence"]).reset_index(drop=True)


def join_wp_onto_plays(plays_df: pd.DataFrame, wp_entries: list[dict],
                      fav_side: str) -> pd.DataFrame:
    """Attach fav_wp to each play via playId."""
    if plays_df.empty:
        return plays_df
    wp_map = {}
    for w in wp_entries:
        pid = w.get("playId")
        if pid is None:
            continue
        home_wp = float(w.get("homeWinPercentage", float("nan")))
        tie_pct = float(w.get("tiePercentage", 0.0) or 0.0)
        if fav_side == "home":
            fav_wp = home_wp
        else:
            fav_wp = 1.0 - home_wp - tie_pct
        wp_map[pid] = fav_wp
    plays_df = plays_df.copy()
    plays_df["fav_wp"] = plays_df["play_id"].map(wp_map)
    return plays_df


def build_trades_df(payload: dict, ticker_sides: dict[str, str],
                    fav_side: str) -> pd.DataFrame:
    """Flatten the combined trade tape and add fav_yes_price column."""
    trades = payload.get("trades", [])
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["created_time"] = df["created_time"].map(_parse_iso)
    df["count_fp"] = df["count_fp"].astype(float)
    df["yes_price_dollars"] = df["yes_price_dollars"].astype(float)
    df["ticker_side"] = df["ticker"].map(ticker_sides).fillna("unknown")

    def _fav_price(row):
        if row["ticker_side"] == fav_side:
            return float(row["yes_price_dollars"])
        if row["ticker_side"] in ("home", "away"):
            return 1.0 - float(row["yes_price_dollars"])
        return float("nan")

    df["fav_yes_price"] = df.apply(_fav_price, axis=1)
    df = df.dropna(subset=["fav_yes_price"]).sort_values("created_time")
    return df.reset_index(drop=True)


def build_vwap_timeseries(trades_df: pd.DataFrame,
                          start_ts: datetime,
                          end_ts: datetime) -> pd.DataFrame:
    """Bin trades into 30-second buckets, compute VWAP etc., forward-fill
    empty buckets."""
    if trades_df.empty:
        return pd.DataFrame(columns=[
            "bucket_start", "kalshi_vwap", "kalshi_last",
            "kalshi_volume", "kalshi_trade_count",
        ])
    bin_start = start_ts.replace(microsecond=0)
    bin_start = bin_start - timedelta(
        seconds=bin_start.second % VWAP_BUCKET_SEC,
    )
    buckets: list[datetime] = []
    t = bin_start
    while t <= end_ts:
        buckets.append(t)
        t = t + timedelta(seconds=VWAP_BUCKET_SEC)
    bucket_idx = pd.DatetimeIndex(buckets, tz="UTC")
    delta = (trades_df["created_time"] - bin_start).dt.total_seconds()
    trades_df = trades_df.copy()
    trades_df["_bucket_idx"] = (delta // VWAP_BUCKET_SEC).astype(int)
    rows = []
    for idx, g in trades_df.groupby("_bucket_idx"):
        if idx < 0 or idx >= len(buckets):
            continue
        v = g["count_fp"].sum()
        vwap = (
            (g["fav_yes_price"] * g["count_fp"]).sum() / v if v > 0
            else g["fav_yes_price"].mean()
        )
        rows.append({
            "bucket_start": buckets[idx],
            "kalshi_vwap": float(vwap),
            "kalshi_last": float(g["fav_yes_price"].iloc[-1]),
            "kalshi_volume": float(v),
            "kalshi_trade_count": int(len(g)),
        })
    vw = pd.DataFrame(rows)
    full = pd.DataFrame({"bucket_start": bucket_idx})
    full = full.merge(vw, on="bucket_start", how="left")
    full["kalshi_vwap"] = full["kalshi_vwap"].ffill()
    full["kalshi_last"] = full["kalshi_last"].ffill()
    full["kalshi_volume"] = full["kalshi_volume"].fillna(0.0)
    full["kalshi_trade_count"] = full["kalshi_trade_count"].fillna(0).astype(int)
    return full


# ---- Timeout detection --------------------------------------------------

_TIMEOUT_TYPE_IDS = {"16", "52"}


def detect_timeouts(plays_df: pd.DataFrame, fav_side: str,
                    home_team: str | None,
                    away_team: str | None) -> list[dict]:
    if plays_df.empty:
        return []
    mask = (
        plays_df["play_type_text"].str.lower().str.contains(
            "timeout", na=False,
        )
        | plays_df["play_type_id"].isin(_TIMEOUT_TYPE_IDS)
    )
    out = []
    for p in plays_df[mask].itertuples():
        out.append({
            "wallclock": p.wallclock,
            "period": p.period,
            "game_clock": p.game_clock,
            "elapsed": p.elapsed,
            "play_type_text": p.play_type_text,
            "team_id": p.team_id,
            "fav_wp_at_call": p.fav_wp if hasattr(p, "fav_wp") else None,
        })
    return out


def attach_timeout_windows(
    ts_df: pd.DataFrame, timeouts: list[dict],
) -> pd.DataFrame:
    if ts_df.empty:
        return ts_df
    ts_df = ts_df.copy()
    ts_df["is_timeout_window"] = False
    if not timeouts:
        return ts_df
    flank = timedelta(seconds=TIMEOUT_FLANK_SEC)
    for to in timeouts:
        wc = to["wallclock"]
        mask = (
            (ts_df["bucket_start"] >= wc - flank)
            & (ts_df["bucket_start"] <= wc + flank)
        )
        ts_df.loc[mask, "is_timeout_window"] = True
    return ts_df


# ---- Merge ESPN context onto Kalshi 30s grid ---------------------------

def merge_espn_onto_ts(ts_df: pd.DataFrame,
                       plays_df: pd.DataFrame) -> pd.DataFrame:
    if ts_df.empty:
        return ts_df
    if plays_df.empty:
        for col in ("game_seconds_elapsed", "period", "game_clock",
                    "fav_score", "dog_score", "score_margin", "fav_wp"):
            ts_df[col] = np.nan
        return ts_df
    plays_sorted = plays_df.sort_values("wallclock").reset_index(drop=True)
    left = ts_df.rename(columns={"bucket_start": "ts"}).sort_values("ts")
    right = plays_sorted[[
        "wallclock", "elapsed", "period", "game_clock",
        "fav_score", "dog_score", "score_margin", "fav_wp",
    ]].rename(columns={"wallclock": "ts"})
    merged = pd.merge_asof(
        left, right, on="ts", direction="backward",
    )
    merged = merged.rename(columns={
        "ts": "bucket_start", "elapsed": "game_seconds_elapsed",
    })
    return merged


def build_timeseries_csv(merged: pd.DataFrame) -> pd.DataFrame:
    """Finalize the continuous timeseries DataFrame.

    Uses in-memory column names (`bucket_start`, `fav_wp`,
    `kalshi_vwap`, `kalshi_last`) — these are what section builders
    operate on. CSV writing renames to the public schema.
    """
    cols = [
        "bucket_start", "game_seconds_elapsed", "period", "game_clock",
        "fav_score", "dog_score", "score_margin",
        "fav_wp", "kalshi_vwap", "kalshi_last",
        "kalshi_volume", "kalshi_trade_count", "is_timeout_window",
    ]
    out = merged.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    out["delta"] = out["kalshi_vwap"] - out["fav_wp"]
    # Public-facing aliases so in-report and section builders can use
    # the prose names without renaming the canonical columns.
    out["bucket_start_utc"] = out["bucket_start"]
    out["fav_wp_espn"] = out["fav_wp"]
    out["fav_kalshi_vwap"] = out["kalshi_vwap"]
    out["fav_kalshi_last"] = out["kalshi_last"]
    return out


_CSV_COLUMNS = [
    "bucket_start_utc", "game_seconds_elapsed", "period", "game_clock",
    "fav_score", "dog_score", "score_margin",
    "fav_wp_espn", "fav_kalshi_vwap", "fav_kalshi_last", "delta",
    "kalshi_volume", "kalshi_trade_count", "is_timeout_window",
]


# ---- Scoring-play timeseries -------------------------------------------

def _price_in_window(
    trades_df: pd.DataFrame, center: datetime,
    lo_off: float, hi_off: float, pick: str,
) -> float | None:
    """Find a trade within [center + lo_off, center + hi_off] seconds.

    pick='last_before': largest wallclock in window (for lo_off < 0).
    pick='first_after': smallest wallclock in window (for hi_off > 0).
    """
    if trades_df.empty:
        return None
    lo = center + timedelta(seconds=lo_off)
    hi = center + timedelta(seconds=hi_off)
    mask = (trades_df["created_time"] >= lo) & (trades_df["created_time"] <= hi)
    sub = trades_df[mask]
    if sub.empty:
        return None
    if pick == "last_before":
        return float(sub.iloc[-1]["fav_yes_price"])
    return float(sub.iloc[0]["fav_yes_price"])


def build_scoring_plays_csv(
    plays_df: pd.DataFrame, trades_df: pd.DataFrame, fav_side: str,
) -> pd.DataFrame:
    if plays_df.empty:
        return pd.DataFrame()
    scoring = plays_df[plays_df["scoring_play"]].reset_index(drop=True)
    if scoring.empty:
        return pd.DataFrame()
    # Need fav_wp before and after — shift within sorted plays_df
    wp_series = plays_df["fav_wp"].reset_index(drop=True)
    plays_sorted = plays_df.reset_index(drop=True)
    rows = []
    for _, play in scoring.iterrows():
        seq = play["sequence"]
        this_idx = plays_sorted[
            plays_sorted["sequence"] == seq
        ].index
        if len(this_idx) == 0:
            continue
        i = int(this_idx[0])
        fav_wp_after = (
            wp_series.iloc[i] if not pd.isna(wp_series.iloc[i]) else None
        )
        prior_candidates = wp_series.iloc[:i].dropna()
        fav_wp_before = (
            float(prior_candidates.iloc[-1]) if len(prior_candidates)
            else None
        )
        wp_delta = (
            (fav_wp_after - fav_wp_before)
            if (fav_wp_after is not None and fav_wp_before is not None)
            else None
        )
        # Determine whether the favorite scored
        team_id = play.get("team_id")
        # Infer which side scored by comparing score changes to the
        # previous play (more reliable than team_id mapping).
        if i > 0:
            prev = plays_sorted.iloc[i - 1]
            home_scored = play["home_score"] > prev["home_score"]
            away_scored = play["away_score"] > prev["away_score"]
        else:
            home_scored = play["home_score"] > 0
            away_scored = play["away_score"] > 0
        if home_scored:
            scoring_side = "home"
        elif away_scored:
            scoring_side = "away"
        else:
            scoring_side = "unknown"
        scoring_team_is_fav = scoring_side == fav_side
        kalshi_before = _price_in_window(
            trades_df, play["wallclock"], -SCORING_WINDOW_BEFORE_SEC, 0,
            "last_before",
        )
        kalshi_after = _price_in_window(
            trades_df, play["wallclock"],
            SCORING_WINDOW_AFTER_MIN_SEC, SCORING_WINDOW_AFTER_MAX_SEC,
            "first_after",
        )
        kalshi_delta = (
            kalshi_after - kalshi_before
            if (kalshi_before is not None and kalshi_after is not None)
            else None
        )
        reaction_diff = (
            wp_delta - kalshi_delta
            if (wp_delta is not None and kalshi_delta is not None)
            else None
        )
        rows.append({
            "play_wallclock_utc": play["wallclock"],
            "game_seconds_elapsed": play["elapsed"],
            "period": play["period"],
            "game_clock": play["game_clock"],
            "play_text": play["text"],
            "score_value": play["score_value"],
            "scoring_team_is_fav": scoring_team_is_fav,
            "fav_score_after": play["fav_score"],
            "dog_score_after": play["dog_score"],
            "score_margin_after": play["score_margin"],
            "fav_wp_before": fav_wp_before,
            "fav_wp_after": fav_wp_after,
            "wp_delta": wp_delta,
            "kalshi_price_before": kalshi_before,
            "kalshi_price_after": kalshi_after,
            "kalshi_price_delta": kalshi_delta,
            "wp_vs_kalshi_reaction_diff": reaction_diff,
        })
    return pd.DataFrame(rows)


# ---- Analysis sections --------------------------------------------------

def _mean_std(vals: list[float]) -> tuple[float | None, ...]:
    clean = [v for v in vals if v is not None and not np.isnan(v)]
    if not clean:
        return None, None, None, None, None, 0
    return (
        float(np.mean(clean)),
        float(np.median(clean)),
        float(np.std(clean, ddof=0)),
        float(np.min(clean)),
        float(np.max(clean)),
        len(clean),
    )


def section_header(md: list[str], title: str) -> None:
    md.append(f"\n## {title}\n")


def section_0_header(
    md: list[str], espn_game_id: str, event_ticker: str, meta: dict,
    fav_info: dict, trades_df: pd.DataFrame, pregame_fav_kalshi: float | None,
    spread: float | None,
) -> None:
    date = (meta.get("date") or "")[:10]
    home = meta.get("home_team") or "?"
    away = meta.get("away_team") or "?"
    home_sc = meta.get("home_score") or "?"
    away_sc = meta.get("away_score") or "?"
    spread_str = f"{spread:+.1f}" if spread is not None else "—"
    fav_wp_pre = fav_info.get("pregame_fav_wp")
    fav_wp_str = f"{fav_wp_pre:.1%}" if fav_wp_pre is not None else "—"
    fav_kalshi_str = (
        f"${pregame_fav_kalshi:.4f}" if pregame_fav_kalshi is not None
        else "—"
    )
    delta_str = "—"
    if fav_wp_pre is not None and pregame_fav_kalshi is not None:
        delta_str = f"{(pregame_fav_kalshi - fav_wp_pre) * 100:+.1f}pp"
    total_trades = len(trades_df) if trades_df is not None else 0
    total_vol = (
        trades_df["count_fp"].sum() if trades_df is not None and not trades_df.empty
        else 0.0
    )
    abs_sp = abs(spread) if spread is not None else None
    if abs_sp is None:
        s3_filter = "unknown spread"
    elif abs_sp <= 6:
        s3_filter = "competitive (|spread| ≤ 6)"
    else:
        s3_filter = "excluded from Strategy 3 universe"
    md.append(f"# WP vs Kalshi Paired Analysis: {away} @ {home}")
    md.append("")
    md.append(f"**Date:** {date}  |  **ESPN ID:** {espn_game_id}  |  "
              f"**Kalshi:** {event_ticker}")
    md.append(f"**Final:** {home} {home_sc} – {away} {away_sc}")
    md.append(f"**Pre-game spread:** {spread_str}  |  "
              f"**Favorite:** {fav_info.get('fav_team') or '—'}")
    md.append(f"**Pre-game ESPN WP (fav):** {fav_wp_str}")
    md.append(f"**Pre-game Kalshi (fav):** {fav_kalshi_str}")
    md.append(f"**Pre-game delta:** {delta_str}")
    md.append(f"**Kalshi trades:** {total_trades:,} trades, "
              f"{total_vol:,.0f} contracts")
    md.append(
        f"**Strategy 3 filter:** {s3_filter}  (|spread| "
        f"{abs_sp if abs_sp is not None else '—'})"
    )


def section_1_pregame(
    md: list[str], fav_info: dict, pregame_fav_kalshi: float | None,
) -> None:
    section_header(md, "§1 — Pre-game snapshot")
    fav_wp = fav_info.get("pregame_fav_wp")
    if fav_wp is None:
        md.append("_Pre-game ESPN WP unavailable._\n")
        return
    if pregame_fav_kalshi is None:
        md.append(
            f"- Pre-game ESPN WP (fav): {fav_wp:.1%}. "
            "No Kalshi trade before tip-off — pre-game delta not "
            "measurable.\n"
        )
        return
    delta_pp = (pregame_fav_kalshi - fav_wp) * 100
    above_below = "above" if delta_pp > 0 else "below"
    md.append(
        f"- Pre-game ESPN WP (fav): **{fav_wp:.1%}** vs Kalshi "
        f"(fav): **${pregame_fav_kalshi:.4f}**. "
        f"Δ = **{delta_pp:+.1f}pp** ({above_below} ESPN)."
    )
    # Compression-pattern check. The Phase 3B finding is that Kalshi is
    # BELOW ESPN at high fav WP and ABOVE ESPN at low fav WP. Direction
    # matters — a +3.9pp delta at a heavy-favorite (high WP) is the
    # *reverse* of the expected compression, not a small confirming gap.
    expected_sign = -1 if fav_wp >= 0.5 else 1   # −: Kalshi < ESPN; +: >
    observed_sign = 1 if delta_pp > 0 else (-1 if delta_pp < 0 else 0)
    if abs(delta_pp) < 1.0:
        compression_note = (
            "This game's pre-game delta is near zero — consistent with a "
            "moderate favorite (compression shrinks as WP → 0.5)."
        )
    elif observed_sign == expected_sign and abs(delta_pp) <= 17:
        compression_note = (
            f"This game's pre-game delta ({delta_pp:+.1f}pp) is in the "
            "expected direction and within the ±10-17pp compression band."
        )
    elif observed_sign == expected_sign:
        compression_note = (
            f"This game's pre-game delta ({delta_pp:+.1f}pp) is in the "
            "expected direction but larger than the typical ±17pp "
            "compression band — worth flagging."
        )
    else:
        compression_note = (
            f"⚠ **Direction reversed.** At fav WP {fav_wp:.2f} the "
            "compression pattern predicts Kalshi "
            + ("BELOW" if expected_sign < 0 else "ABOVE")
            + f" ESPN, but here Kalshi is {above_below} ESPN by "
            f"{abs(delta_pp):.1f}pp. "
            "Possible retail-flow signature on a non-competitive line."
        )
    md.append(
        "- Compression pattern reference: prior work shows Kalshi "
        "+10-14pp above ESPN at low fav WP and −10-14pp below at high "
        f"fav WP. {compression_note}"
    )
    md.append("")


def section_2_delta_across_time(
    md: list[str], ts: pd.DataFrame,
) -> None:
    section_header(md, "§2 — Delta across game time")
    if ts.empty or ts["delta"].dropna().empty:
        md.append("_No overlap between Kalshi VWAP and ESPN WP._\n")
        return
    sub = ts.dropna(subset=["delta", "fav_wp_espn"])
    overall = _mean_std(sub["delta"].tolist())
    mean_, med_, std_, mn_, mx_, n_ = overall
    md.append(
        f"**Overall:** mean Δ = {mean_*100:+.2f}pp, "
        f"median {med_*100:+.2f}pp, std {std_*100:.2f}pp, "
        f"min {mn_*100:+.2f}pp, max {mx_*100:+.2f}pp, n={n_:,}."
    )
    frac_pos = float((sub["delta"] > 0).mean()) * 100
    frac_neg = float((sub["delta"] < 0).mean()) * 100
    md.append(
        f"**Direction:** Δ > 0 in {frac_pos:.0f}% of buckets, "
        f"Δ < 0 in {frac_neg:.0f}%.\n"
    )

    md.append("### By quarter")
    md.append("")
    md.append("| Period | Mean Δ | Median Δ | Std Δ | N obs |")
    md.append("|---|---:|---:|---:|---:|")
    for p in sorted([int(v) for v in sub["period"].dropna().unique()]):
        q = sub[sub["period"] == p]
        m, md_, sd, _, _, nn = _mean_std(q["delta"].tolist())
        plabel = f"Q{p}" if p <= 4 else f"OT{p-4}"
        md.append(
            f"| {plabel} | {m*100:+.2f}pp | {md_*100:+.2f}pp | "
            f"{sd*100:.2f}pp | {nn:,} |"
        )
    md.append(
        f"| All | {mean_*100:+.2f}pp | {med_*100:+.2f}pp | "
        f"{std_*100:.2f}pp | {n_:,} |"
    )
    md.append("")

    md.append("### By WP zone (ESPN fav WP)")
    md.append("")
    md.append("| WP zone | Mean Δ | N obs | Δ > 0 % |")
    md.append("|---|---:|---:|---:|")
    for lo, hi, label in WP_ZONES:
        zone = sub[(sub["fav_wp_espn"] >= lo) & (sub["fav_wp_espn"] < hi)]
        if zone.empty:
            md.append(f"| {label} | — | 0 | — |")
            continue
        m, _, _, _, _, nn = _mean_std(zone["delta"].tolist())
        pct_pos = float((zone["delta"] > 0).mean()) * 100
        md.append(
            f"| {label} | {m*100:+.2f}pp | {nn:,} | {pct_pos:.0f}% |"
        )
    md.append("")


def section_3_convergence(md: list[str], ts: pd.DataFrame,
                          max_period: int) -> None:
    section_header(md, "§3 — Convergence analysis")
    if ts.empty or ts["delta"].dropna().empty:
        md.append("_No data._\n")
        return
    total_len = total_game_length_sec(max_period)
    sub = ts.dropna(subset=["delta", "game_seconds_elapsed"]).copy()
    sub["time_remaining"] = total_len - sub["game_seconds_elapsed"]
    sub["abs_delta"] = sub["delta"].abs()

    md.append("| Time remaining | Mean |Δ| | Median |Δ| | N obs |")
    md.append("|---|---:|---:|---:|")
    for lo, hi, label in TR_BUCKETS:
        z = sub[(sub["time_remaining"] > lo) & (sub["time_remaining"] <= hi)]
        if z.empty:
            md.append(f"| {label} | — | — | 0 |")
            continue
        m, md_, _, _, _, nn = _mean_std(z["abs_delta"].tolist())
        md.append(
            f"| {label} | {m*100:.2f}pp | {md_*100:.2f}pp | {nn:,} |"
        )
    md.append("")

    # Regression
    x = sub["game_seconds_elapsed"].values
    y = sub["abs_delta"].values
    if len(x) >= 2:
        if _HAS_SCIPY:
            res = _scipy_stats.linregress(x, y)
            md.append(
                f"**Regression:** |Δ| ~ elapsed_sec → slope "
                f"{res.slope:.6f}/s, R² = {res.rvalue**2:.3f}, "
                f"p = {res.pvalue:.3g}. "
                + (
                    "Negative slope = convergence."
                    if res.slope < 0 else
                    "Positive slope = divergence with game time."
                )
            )
        else:
            slope, intercept = np.polyfit(x, y, 1)
            yhat = slope * x + intercept
            ss_res = np.sum((y - yhat) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2) or 1.0
            r2 = 1.0 - ss_res / ss_tot
            md.append(
                f"**Regression (numpy polyfit, no p-value):** slope "
                f"{slope:.6f}/s, R² = {r2:.3f}."
            )
    md.append("")

    # Final 2 min
    final2 = sub[sub["time_remaining"] <= 120]
    if not final2.empty:
        m, _, _, _, _, nn = _mean_std(final2["abs_delta"].tolist())
        md.append(
            f"**Final 2 minutes:** mean |Δ| = {m*100:.2f}pp "
            f"(n={nn})."
        )
    md.append("")


def section_4_scoring_response(md: list[str], sp: pd.DataFrame) -> None:
    section_header(md, "§4 — Scoring play response comparison")
    if sp.empty:
        md.append("_No scoring plays._\n")
        return
    covered = sp.dropna(subset=["wp_vs_kalshi_reaction_diff"])
    cov_rate = 100 * len(covered) / len(sp)
    md.append(
        f"Coverage: **{len(covered)}/{len(sp)}** "
        f"({cov_rate:.0f}%) scoring plays have Kalshi prices in both "
        "the ±5s-before and +3-to-15s-after windows.\n"
    )
    if covered.empty:
        md.append("_No Kalshi coverage around any scoring play; "
                  "sections below are empty._\n")
        return
    md.append("### By score value")
    md.append("")
    md.append(
        "| Score value | n | Mean wp_delta (pp) | Mean Kalshi Δ (pp) "
        "| Mean reaction diff (pp) |"
    )
    md.append("|---|---:|---:|---:|---:|")
    for sv in sorted(covered["score_value"].dropna().unique()):
        sub = covered[covered["score_value"] == sv]
        md.append(
            f"| {int(sv)}-pt | {len(sub)} | "
            f"{sub['wp_delta'].mean()*100:+.2f}pp | "
            f"{sub['kalshi_price_delta'].mean()*100:+.2f}pp | "
            f"{sub['wp_vs_kalshi_reaction_diff'].mean()*100:+.2f}pp |"
        )
    md.append("")
    md.append("### By WP zone at time of play")
    md.append("")
    md.append(
        "| WP zone | n | Mean wp_delta | Mean kalshi Δ | Mean diff |"
    )
    md.append("|---|---:|---:|---:|---:|")
    for lo, hi, label in WP_ZONES:
        sub = covered[
            (covered["fav_wp_before"] >= lo)
            & (covered["fav_wp_before"] < hi)
        ]
        if sub.empty:
            md.append(f"| {label} | 0 | — | — | — |")
            continue
        md.append(
            f"| {label} | {len(sub)} | "
            f"{sub['wp_delta'].mean()*100:+.2f}pp | "
            f"{sub['kalshi_price_delta'].mean()*100:+.2f}pp | "
            f"{sub['wp_vs_kalshi_reaction_diff'].mean()*100:+.2f}pp |"
        )
    md.append("")


def section_5_strategy3_zone(md: list[str], ts: pd.DataFrame) -> None:
    section_header(md, "§5 — Strategy 3 zone mapping")
    if ts.empty or ts["fav_kalshi_vwap"].dropna().empty:
        md.append("_No Kalshi VWAP data._\n")
        return
    # Restrict to in-game buckets only. Pre-game price-discovery trades
    # (sometimes days before tip) would otherwise inflate zone time and
    # produce nonsense "entered zone N days before" lead/lag numbers.
    sub = ts.dropna(subset=["fav_kalshi_vwap", "game_seconds_elapsed"])
    in_zone = sub[
        (sub["fav_kalshi_vwap"] >= S3_FAV_LO)
        & (sub["fav_kalshi_vwap"] <= S3_FAV_HI)
    ]
    pct = 100 * len(in_zone) / len(sub) if len(sub) else 0.0
    sec_in = len(in_zone) * VWAP_BUCKET_SEC
    if in_zone.empty:
        md.append(
            "_Game never entered Strategy 3 zone_ "
            f"(fav Kalshi VWAP never in [${S3_FAV_LO:.2f}, "
            f"${S3_FAV_HI:.2f}]). Expected for games with "
            "|spread| > 6.\n"
        )
        return
    md.append(
        f"Strategy 3 zone active for **{sec_in:,}s** "
        f"({pct:.1f}% of 30s buckets; zone = fav Kalshi VWAP in "
        f"[${S3_FAV_LO:.2f}, ${S3_FAV_HI:.2f}])."
    )
    wp_while_in = in_zone["fav_wp_espn"].dropna()
    if not wp_while_in.empty:
        md.append(
            f"While in-zone, fav ESPN WP ranged "
            f"[{wp_while_in.min():.2f}, {wp_while_in.max():.2f}] "
            f"with mean {wp_while_in.mean():.2f}."
        )
    # Lead/lag: find first moment either series entered the equivalent
    # zone and measure the gap.
    wp_in = sub[
        (sub["fav_wp_espn"] >= S3_FAV_LO)
        & (sub["fav_wp_espn"] <= S3_FAV_HI)
    ]
    if not wp_in.empty:
        first_wp = wp_in["bucket_start"].iloc[0]
        first_k = in_zone["bucket_start"].iloc[0]
        lead_sec = (first_k - first_wp).total_seconds()
        if lead_sec > 0:
            md.append(
                f"ESPN WP entered the zone **{lead_sec:.0f}s before** "
                "Kalshi VWAP."
            )
        elif lead_sec < 0:
            md.append(
                f"Kalshi VWAP entered the zone **{-lead_sec:.0f}s "
                "before** ESPN WP."
            )
        else:
            md.append("ESPN WP and Kalshi VWAP entered the zone "
                      "in the same 30s bucket.")
    md.append("")


def section_6_timeouts(md: list[str], ts: pd.DataFrame,
                       timeouts: list[dict]) -> None:
    section_header(md, "§6 — Timeout windows")
    if not timeouts:
        md.append("_No timeouts detected in PBP._\n")
        return
    md.append(f"Detected **{len(timeouts)}** timeout events.\n")
    md.append("| # | Period | Clock | Fav WP | Fav Kalshi | Δ | ±60s std |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    to_deltas = []
    for i, to in enumerate(timeouts, 1):
        wc = to["wallclock"]
        if not ts.empty:
            near = ts[
                (ts["bucket_start"] >= wc - timedelta(seconds=TIMEOUT_FLANK_SEC))
                & (ts["bucket_start"] <= wc + timedelta(seconds=TIMEOUT_FLANK_SEC))
            ]
        else:
            near = pd.DataFrame()
        mid = ts[ts["bucket_start"] <= wc].tail(1) if not ts.empty else pd.DataFrame()
        wp_at = None
        kalshi_at = None
        delta_at = None
        if not mid.empty:
            wp_at = mid["fav_wp_espn"].iloc[0]
            kalshi_at = mid["fav_kalshi_vwap"].iloc[0]
            if not pd.isna(wp_at) and not pd.isna(kalshi_at):
                delta_at = kalshi_at - wp_at
                to_deltas.append(delta_at)
        std_delta = None
        if not near.empty:
            d = near.dropna(subset=["delta"])["delta"]
            if len(d) > 1:
                std_delta = float(d.std(ddof=0))
        md.append(
            f"| {i} | Q{to['period']} | {to['game_clock']} | "
            f"{wp_at:.2f} | {kalshi_at:.4f} | "
            f"{delta_at*100:+.2f}pp | "
            f"{(std_delta*100 if std_delta is not None else 0):.2f}pp |"
            if wp_at is not None and kalshi_at is not None and delta_at is not None
            else
            f"| {i} | Q{to['period']} | {to['game_clock']} | — | — | — | — |"
        )
    md.append("")
    if to_deltas:
        mean_to = float(np.mean(to_deltas))
        overall_delta = ts["delta"].dropna() if not ts.empty else pd.Series([])
        overall_mean = float(overall_delta.mean()) if not overall_delta.empty else 0.0
        md.append(
            f"**Summary:** mean Δ at timeout calls: "
            f"{mean_to*100:+.2f}pp vs overall mean Δ: "
            f"{overall_mean*100:+.2f}pp. "
            + (
                "Timeouts sit near the overall delta."
                if abs(mean_to - overall_mean) < 0.02 else
                "Timeouts diverge from the overall delta."
            )
        )
    md.append("")


def section_7_key_observations(
    md: list[str], ts: pd.DataFrame, fav_info: dict,
    pregame_fav_kalshi: float | None, max_period: int,
) -> None:
    section_header(md, "§7 — Key observations")
    obs: list[str] = []
    fav_wp = fav_info.get("pregame_fav_wp")
    if fav_wp is not None and pregame_fav_kalshi is not None:
        delta = (pregame_fav_kalshi - fav_wp) * 100
        if abs(delta) > 5:
            direction = "above" if delta > 0 else "below"
            obs.append(
                f"- Pre-game gap of {delta:+.1f}pp "
                f"(Kalshi {direction} ESPN). "
                + (
                    "Consistent with compression band."
                    if abs(delta) <= 15 else
                    "Larger than the typical compression band."
                )
            )
    if not ts.empty:
        sub = ts.dropna(subset=["delta", "period"])
        if not sub.empty:
            q_means = sub.groupby("period")["delta"].mean().abs() * 100
            if 1 in q_means.index and 4 in q_means.index:
                if q_means[4] < q_means[1]:
                    obs.append(
                        f"- |Δ| narrowed from Q1 ({q_means[1]:.2f}pp) "
                        f"to Q4 ({q_means[4]:.2f}pp) — consistent with "
                        "convergence hypothesis."
                    )
                else:
                    obs.append(
                        f"- |Δ| did NOT narrow from Q1 "
                        f"({q_means[1]:.2f}pp) to Q4 ({q_means[4]:.2f}"
                        "pp) — convergence not observed on this game."
                    )
        total_len = total_game_length_sec(max_period)
        sub2 = sub.copy()
        sub2["tr"] = total_len - sub2["game_seconds_elapsed"]
        final2 = sub2[sub2["tr"] <= 120]
        if not final2.empty:
            mean_abs = final2["delta"].abs().mean() * 100
            if mean_abs < 2:
                obs.append(
                    f"- Near-perfect convergence in final 2 minutes "
                    f"(|Δ| = {mean_abs:.2f}pp)."
                )
            else:
                obs.append(
                    f"- Final-2-min |Δ| = {mean_abs:.2f}pp — no "
                    "tight convergence at end."
                )
    # Strategy 3 zone activity. Filter to in-game buckets only — same
    # rationale as §5 (pre-game price-discovery would otherwise dominate).
    if not ts.empty:
        sub = ts.dropna(subset=["fav_kalshi_vwap", "game_seconds_elapsed"])
        if not sub.empty:
            in_zone = sub[
                (sub["fav_kalshi_vwap"] >= S3_FAV_LO)
                & (sub["fav_kalshi_vwap"] <= S3_FAV_HI)
            ]
            if in_zone.empty:
                obs.append(
                    "- No Strategy 3 zone activation — consistent with "
                    "|spread| > 6 exclusion filter."
                )
            else:
                sec_in = len(in_zone) * VWAP_BUCKET_SEC
                pct = 100 * len(in_zone) / len(sub)
                obs.append(
                    f"- Strategy 3 zone active for {sec_in:,}s "
                    f"({pct:.1f}% of in-game time)."
                )
    if not obs:
        obs.append("- No notable patterns flagged at default thresholds.")
    md.extend(obs)
    md.append("")


# ---- Report assembly ----------------------------------------------------

def assemble_report(
    espn_game_id: str, event_ticker: str, meta: dict,
    fav_info: dict, trades_df: pd.DataFrame, ts: pd.DataFrame,
    sp: pd.DataFrame, timeouts: list[dict], max_period: int,
    pregame_fav_kalshi: float | None, spread: float | None,
) -> str:
    md: list[str] = []
    section_0_header(
        md, espn_game_id, event_ticker, meta, fav_info, trades_df,
        pregame_fav_kalshi, spread,
    )
    section_1_pregame(md, fav_info, pregame_fav_kalshi)
    section_2_delta_across_time(md, ts)
    section_3_convergence(md, ts, max_period)
    section_4_scoring_response(md, sp)
    section_5_strategy3_zone(md, ts)
    section_6_timeouts(md, ts, timeouts)
    section_7_key_observations(md, ts, fav_info, pregame_fav_kalshi,
                               max_period)
    return "\n".join(md) + "\n"


# ---- Pre-game Kalshi price ----------------------------------------------

def compute_pregame_fav_kalshi(
    trades_df: pd.DataFrame, first_play_wallclock: datetime | None,
) -> float | None:
    if trades_df.empty or first_play_wallclock is None:
        return None
    before = trades_df[trades_df["created_time"] < first_play_wallclock]
    if before.empty:
        # fall back to first trade overall
        return float(trades_df.iloc[0]["fav_yes_price"])
    return float(before.iloc[-1]["fav_yes_price"])


# ---- Main ---------------------------------------------------------------

def run_single_game(
    espn_game_id: str, event_ticker: str,
    spread: float | None, use_cached: bool,
    write_report: bool = True,
) -> dict:
    """Analyze a single game end-to-end.

    Returns a summary dict: {status, espn_game_id, event_ticker,
    n_wp_obs, n_trades, n_scoring_plays, error}.
    status is "ok" on success, "fail" on error.
    """
    PAIRED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "status": "fail", "espn_game_id": espn_game_id,
        "event_ticker": event_ticker, "n_wp_obs": 0,
        "n_trades": 0, "n_scoring_plays": 0, "error": None,
    }
    espn_cache = PAIRED_DIR / f"{espn_game_id}_espn.json"
    trades_cache = PAIRED_DIR / f"{event_ticker}_trades.json"

    espn_data = fetch_espn_summary(espn_game_id, espn_cache, use_cached)
    meta = parse_metadata(espn_data)
    plays = espn_data.get("plays") or []
    wp_entries = espn_data.get("winprobability") or []
    if not plays:
        raise SystemExit(f"ESPN returned no plays for {espn_game_id}")

    resolved_spread = spread
    if resolved_spread is None:
        auto = resolve_spread_from_summary(espn_data)
        if auto is not None:
            log(f"Auto-resolved spread from ESPN pickcenter: {auto:+.1f}")
            resolved_spread = auto

    fav_info = identify_favorite(meta, wp_entries, resolved_spread)
    log(f"Favorite: {fav_info['fav_team']} ({fav_info['fav_side']} side)")

    plays_df = build_plays_df(plays, fav_info["fav_side"])
    plays_df = join_wp_onto_plays(plays_df, wp_entries, fav_info["fav_side"])
    if plays_df.empty:
        raise SystemExit("No usable plays with wallclock timestamps")
    max_period = int(plays_df["period"].dropna().max() or 4)
    first_play_wc = plays_df["wallclock"].iloc[0]
    last_play_wc = plays_df["wallclock"].iloc[-1]

    trades_payload = fetch_kalshi_trades(event_ticker, trades_cache, use_cached)
    tickers = trades_payload.get("tickers", [])
    ticker_sides = map_ticker_to_side(
        tickers, meta.get("home_team"), meta.get("away_team"),
    )
    log(f"Ticker sides: {ticker_sides}")
    trades_df = build_trades_df(
        trades_payload, ticker_sides, fav_info["fav_side"],
    )
    log(f"Built trades DF: {len(trades_df):,} trades")

    ts_start = min(first_play_wc, trades_df["created_time"].min()) \
        if not trades_df.empty else first_play_wc
    ts_end = last_play_wc + timedelta(seconds=60)
    vw = build_vwap_timeseries(trades_df, ts_start, ts_end)
    timeouts_raw = detect_timeouts(
        plays_df, fav_info["fav_side"],
        meta.get("home_team"), meta.get("away_team"),
    )
    merged = merge_espn_onto_ts(vw, plays_df)
    merged = attach_timeout_windows(merged, timeouts_raw)
    ts_final = build_timeseries_csv(merged)

    sp_df = build_scoring_plays_csv(
        plays_df, trades_df, fav_info["fav_side"],
    )
    pregame_fav_kalshi = compute_pregame_fav_kalshi(trades_df, first_play_wc)

    ts_path = PAIRED_DIR / f"{event_ticker}_timeseries.csv"
    sp_path = PAIRED_DIR / f"{event_ticker}_scoring_plays.csv"
    ts_final[_CSV_COLUMNS].to_csv(ts_path, index=False)
    log(f"Timeseries CSV → {ts_path}")
    sp_df.to_csv(sp_path, index=False)
    log(f"Scoring plays CSV → {sp_path}")

    if write_report:
        report_path = REPORT_DIR / f"wp_vs_kalshi_{event_ticker}.md"
        md = assemble_report(
            espn_game_id, event_ticker, meta, fav_info,
            trades_df, ts_final, sp_df, timeouts_raw, max_period,
            pregame_fav_kalshi, resolved_spread,
        )
        report_path.write_text(md)
        log(f"Report → {report_path}")

    summary.update({
        "status": "ok",
        "n_wp_obs": int(len(ts_final)),
        "n_trades": int(len(trades_df)),
        "n_scoring_plays": int(len(sp_df)),
    })
    return summary


# Backward-compat alias — prior internal callers used this name.
run_one_game = run_single_game


def _parse_teams_arg(s: str) -> tuple[str, str]:
    """Parse 'AWAY@HOME' (case-insensitive). Also accepts 'AWAY-HOME'."""
    sep = "@" if "@" in s else ("-" if "-" in s else None)
    if sep is None:
        raise SystemExit(
            f"--teams must be AWAY@HOME (e.g., ORL@DET); got {s!r}"
        )
    away, home = s.split(sep, 1)
    return away.strip().upper(), home.strip().upper()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ESPN WP vs Kalshi paired per-game analysis.",
    )
    parser.add_argument(
        "--teams", type=str, default=None,
        help="Team pair in AWAY@HOME form (e.g., ORL@DET). With --date, "
             "auto-resolves ESPN game ID, Kalshi event ticker, and spread.",
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Game date (YYYY-MM-DD or YYYYMMDD). Default: today UTC. "
             "Used with --teams or --all.",
    )
    parser.add_argument(
        "--all", dest="run_all", action="store_true",
        help="Process every completed game on --date.",
    )
    parser.add_argument(
        "--espn-game-id", type=str, default=None,
        help="(Override) ESPN gameId. Takes precedence over --teams.",
    )
    parser.add_argument(
        "--kalshi-event-ticker", type=str, default=None,
        help="(Override) Kalshi event ticker. Takes precedence over --teams.",
    )
    parser.add_argument(
        "--spread", type=float, default=None,
        help="(Override) Pre-game spread, home-centric (negative = home "
             "favored). Otherwise resolved from ESPN pickcenter.",
    )
    parser.add_argument(
        "--cached", action="store_true",
        help="Skip ESPN/Kalshi fetches if caches exist.",
    )
    parser.add_argument(
        "--batch", type=str, default=None,
        help="Path to matched_games.csv (from ticker_matcher.py). "
             "Runs analysis on each row; auto-detects cache per-game; "
             "skips per-game markdown reports; resumes interrupted batches. "
             "Incompatible with --espn-game-id / --kalshi-event-ticker.",
    )
    parser.add_argument(
        "--min-date", type=str, default=None,
        help="Batch-mode filter: skip rows in matched_games.csv whose "
             "game_date is earlier than this YYYY-MM-DD. Use this to "
             "avoid Kalshi's ~60-day trade-tape retention cliff "
             "(typical value: 70 days before today, e.g. 2026-02-01).",
    )
    args = parser.parse_args()

    def _ok(rv: dict | int) -> int:
        # Normalize return values from run_single_game (dict) into
        # process exit codes for single-game dispatch modes.
        if isinstance(rv, dict):
            return 0 if rv.get("status") == "ok" else 1
        return int(rv)

    # --- Dispatch ---------------------------------------------------------
    # Mode 0: --batch — read CSV, loop, auto-cache.
    if args.batch:
        if args.espn_game_id or args.kalshi_event_ticker:
            parser.error(
                "--batch is incompatible with --espn-game-id / "
                "--kalshi-event-ticker."
            )
        return _run_batch(Path(args.batch), min_date=args.min_date)

    # Mode 1: full override — both game ID and event ticker explicit.
    if args.espn_game_id and args.kalshi_event_ticker and not args.run_all:
        return _ok(run_single_game(
            args.espn_game_id, args.kalshi_event_ticker,
            args.spread, args.cached,
        ))

    date_ymd = _parse_date_arg(args.date) if (args.date or args.run_all or args.teams) else None

    # Mode 2: --all — loop over scoreboard.
    if args.run_all:
        if date_ymd is None:
            date_ymd = _parse_date_arg(None)
        games = scoreboard_games(date_ymd)
        if not games:
            raise SystemExit(f"No games on scoreboard for {date_ymd}")
        rc = 0
        for g in games:
            if not g.get("away") or not g.get("home"):
                continue
            log(f"--- {g['away']}@{g['home']} ({g['game_id']}) ---")
            event_ticker = args.kalshi_event_ticker or kalshi_ticker_from_teams(
                g["away"], g["home"], date_ymd,
            )
            try:
                rc |= _ok(run_single_game(
                    g["game_id"], event_ticker, args.spread, args.cached,
                ))
            except SystemExit as e:
                log(f"SKIP {g['away']}@{g['home']}: {e}")
                continue
        return rc

    # Mode 3: --teams + --date resolution.
    if args.teams:
        if date_ymd is None:
            date_ymd = _parse_date_arg(None)
        user_away, user_home = _parse_teams_arg(args.teams)
        if args.espn_game_id:
            espn_game_id = args.espn_game_id
            canon_away, canon_home = user_away, user_home
        else:
            espn_game_id, canon_away, canon_home = resolve_espn_game_id(
                user_away, user_home, date_ymd,
            )
        event_ticker = args.kalshi_event_ticker or kalshi_ticker_from_teams(
            canon_away, canon_home, date_ymd,
        )
        log(
            f"Resolved: {canon_away}@{canon_home} on {date_ymd} → "
            f"espn_game_id={espn_game_id}, event_ticker={event_ticker}"
        )
        return _ok(run_single_game(
            espn_game_id, event_ticker, args.spread, args.cached,
        ))

    parser.error(
        "Provide one of: (--batch PATH) | (--teams [--date]) | "
        "(--all --date) | (--espn-game-id --kalshi-event-ticker)."
    )
    return 2


# ---- Batch mode ---------------------------------------------------------

def _run_batch(csv_path: Path, min_date: str | None = None) -> int:
    """Read matched_games.csv and run analysis on each row.

    Behavior per prompt:
      - Auto-cache: if both ESPN+trades caches exist for a game, fetches
        are skipped (equivalent to --cached).
      - No per-game markdown reports (paired CSVs + caches only).
      - time.sleep(2.0) between games.
      - Errors isolated per-game; batch continues.
      - Optional min_date (YYYY-MM-DD): skip rows with game_date earlier
        than this threshold — used to sidestep Kalshi's ~60-day trade-
        tape retention cliff, since older games return empty tapes and
        waste batch time.
    """
    if not csv_path.exists():
        raise SystemExit(f"Batch CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    required = {"espn_game_id", "kalshi_event_ticker", "home_spread"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Batch CSV missing columns: {missing}")

    if min_date is not None:
        if "game_date" not in df.columns:
            raise SystemExit(
                "--min-date requires a 'game_date' column in the batch CSV."
            )
        # Validate min_date format by attempting a parse.
        try:
            datetime.strptime(min_date, "%Y-%m-%d")
        except ValueError:
            raise SystemExit(
                f"--min-date must be YYYY-MM-DD, got: {min_date!r}"
            )
        before = len(df)
        df = df[df["game_date"].astype(str) >= min_date].reset_index(drop=True)
        log(
            f"--min-date {min_date}: kept {len(df)} / {before} rows "
            f"(dropped {before - len(df)} pre-cliff games)"
        )

    total = len(df)
    n_ok = n_cached = n_fail = 0
    t0 = time.monotonic()
    log(f"=== Batch start — {total} games from {csv_path.name} ===")
    for i, row in enumerate(df.itertuples(), 1):
        espn_id = str(row.espn_game_id)
        ticker = str(row.kalshi_event_ticker)
        spread = float(row.home_spread) if not pd.isna(row.home_spread) else None
        espn_cache = PAIRED_DIR / f"{espn_id}_espn.json"
        trades_cache = PAIRED_DIR / f"{ticker}_trades.json"
        ts_csv = PAIRED_DIR / f"{ticker}_timeseries.csv"
        sp_csv = PAIRED_DIR / f"{ticker}_scoring_plays.csv"
        use_cached = espn_cache.exists() and trades_cache.exists()
        game_t0 = time.monotonic()

        # If all outputs already exist AND both caches exist, treat as
        # already-complete and skip without work. Still logged to stdout
        # for operator visibility.
        if use_cached and ts_csv.exists() and sp_csv.exists():
            n_cached += 1
            print(f"[{i}/{total}] {ticker} — SKIP (cached)", flush=True)
            continue

        try:
            summary = run_single_game(
                espn_id, ticker, spread, use_cached, write_report=False,
            )
        except SystemExit as e:
            n_fail += 1
            print(
                f"[{i}/{total}] {ticker} — FAIL: {e}",
                flush=True,
            )
            time.sleep(2.0)
            continue
        except Exception as e:
            n_fail += 1
            print(
                f"[{i}/{total}] {ticker} — FAIL: {type(e).__name__}: {e}",
                flush=True,
            )
            time.sleep(2.0)
            continue

        elapsed = time.monotonic() - game_t0
        if summary.get("status") == "ok":
            n_ok += 1
            print(
                f"[{i}/{total}] {ticker} — OK "
                f"({summary['n_wp_obs']} WP obs, "
                f"{summary['n_trades']:,} trades) "
                f"[elapsed: {elapsed:.0f}s]",
                flush=True,
            )
        else:
            n_fail += 1
            print(
                f"[{i}/{total}] {ticker} — FAIL: "
                f"{summary.get('error')}",
                flush=True,
            )
        time.sleep(2.0)

    total_elapsed = time.monotonic() - t0
    mins, secs = divmod(int(total_elapsed), 60)
    print()
    print("=== Batch Complete ===")
    print(f"Total: {total} games")
    print(f"OK: {n_ok} | Cached: {n_cached} | Failed: {n_fail}")
    print(f"Paired CSVs in: {PAIRED_DIR}")
    print(f"Elapsed: {mins}m {secs}s")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
