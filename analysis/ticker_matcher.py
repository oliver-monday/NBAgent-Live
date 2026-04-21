"""ESPN ↔ Kalshi per-game ticker matcher.

Fetches all KXNBAGAME events from Kalshi's API, parses ticker
dates and team abbreviations, and matches them to ESPN game IDs
from nba_master_2025_26.csv. Outputs a joined CSV for batch
analysis.

Run:
    # Full match — all available games
    python -m analysis.ticker_matcher

    # Competitive only (|spread| ≤ 6)
    python -m analysis.ticker_matcher --max-spread 6

    # Random sample of N competitive games (for test batches)
    python -m analysis.ticker_matcher --max-spread 6 --sample 10

    # With seed for reproducibility
    python -m analysis.ticker_matcher --max-spread 6 --sample 10 --seed 42
"""

from __future__ import annotations

import argparse
import random
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from analysis.wp_vs_kalshi_paired import KALSHI_BASE, _norm_team

REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER_CSV = REPO_ROOT / "data" / "nba_master_2025_26.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "wp_kalshi_paired" / "matched_games.csv"

KALSHI_SLEEP_SEC = 0.3
REQUEST_TIMEOUT_SEC = 30

TICKER_RE = re.compile(r"KXNBAGAME-(\d{2})([A-Z]{3})(\d{2})([A-Z]{6})")
_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

# Known Kalshi abbreviation quirks. Observed tickers to date use
# standard NBA abbreviations (POR, SAS, ORL, DET, HOU, LAL, MIA, CHA,
# GSW, etc.), so this map is currently empty. Add entries here if a
# mismatch is discovered during matching.
_KALSHI_TEAM_NORM: dict[str, str] = {}


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def normalize_kalshi_team(abbr: str) -> str:
    a = abbr.upper().strip()
    return _KALSHI_TEAM_NORM.get(a, _norm_team(a) or a)


def fetch_all_events() -> list[dict]:
    events: list[dict] = []
    cursor: str | None = None
    pages = 0
    while True:
        url = f"{KALSHI_BASE}/events"
        params = {"series_ticker": "KXNBAGAME", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SEC)
        r.raise_for_status()
        data = r.json()
        chunk = data.get("events", [])
        events.extend(chunk)
        pages += 1
        cursor = data.get("cursor")
        if not cursor or not chunk:
            break
        time.sleep(KALSHI_SLEEP_SEC)
        if pages > 50:
            log(f"WARN: stopped pagination at {pages} pages")
            break
    log(f"Fetched {len(events):,} KXNBAGAME events across {pages} pages")
    return events


def parse_event_ticker(ticker: str) -> dict | None:
    m = TICKER_RE.match(ticker)
    if not m:
        return None
    yy, mon, dd, teams = m.groups()
    if mon not in _MONTHS:
        return None
    try:
        d = date(2000 + int(yy), _MONTHS[mon], int(dd))
    except ValueError:
        return None
    away = normalize_kalshi_team(teams[:3])
    home = normalize_kalshi_team(teams[3:])
    return {
        "event_ticker": ticker,
        "game_date": d.isoformat(),
        "away_team": away,
        "home_team": home,
    }


def build_kalshi_df(events: list[dict]) -> pd.DataFrame:
    rows = []
    for e in events:
        parsed = parse_event_ticker(e.get("event_ticker", ""))
        if parsed is not None:
            rows.append(parsed)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Dedup — keep first if same (date, away, home) appears multiple times
    before = len(df)
    df = df.drop_duplicates(subset=["game_date", "away_team", "home_team"])
    if len(df) < before:
        log(f"Deduplicated {before - len(df)} identical (date, teams) pairs")
    return df


def load_espn_master() -> pd.DataFrame:
    df = pd.read_csv(MASTER_CSV)
    df["game_id"] = df["game_id"].astype(int).astype(str)
    df["game_date"] = df["game_date"].astype(str)
    df["home_team_abbrev"] = df["home_team_abbrev"].map(
        lambda s: (_norm_team(s) or s) if pd.notna(s) else s
    )
    df["away_team_abbrev"] = df["away_team_abbrev"].map(
        lambda s: (_norm_team(s) or s) if pd.notna(s) else s
    )
    df["home_spread"] = pd.to_numeric(df["home_spread"], errors="coerce")
    return df[[
        "game_id", "game_date", "home_team_abbrev",
        "away_team_abbrev", "home_spread",
    ]]


def match_games(
    espn_df: pd.DataFrame, kalshi_df: pd.DataFrame,
) -> tuple[pd.DataFrame, int, int]:
    """Join on (date, away, home). Returns (matched_df, unmatched_espn,
    unmatched_kalshi)."""
    espn = espn_df.rename(columns={
        "game_id": "espn_game_id",
        "home_team_abbrev": "home_team",
        "away_team_abbrev": "away_team",
    })
    merged = espn.merge(
        kalshi_df, on=["game_date", "away_team", "home_team"],
        how="inner",
    )
    # Dedup defensively — if a Kalshi event somehow mapped to multiple
    # ESPN games (shouldn't happen), keep first.
    before = len(merged)
    merged = merged.drop_duplicates(subset=["event_ticker"], keep="first")
    if len(merged) < before:
        log(f"WARN: {before - len(merged)} duplicate Kalshi→ESPN matches dropped")

    matched_espn_ids = set(merged["espn_game_id"])
    matched_tickers = set(merged["event_ticker"])
    n_unm_espn = int((~espn["espn_game_id"].isin(matched_espn_ids)).sum())
    n_unm_kalshi = int((~kalshi_df["event_ticker"].isin(matched_tickers)).sum())

    merged["abs_spread"] = merged["home_spread"].abs()
    merged = merged[[
        "espn_game_id", "event_ticker", "game_date",
        "away_team", "home_team", "home_spread", "abs_spread",
    ]].rename(columns={"event_ticker": "kalshi_event_ticker"})
    merged = merged.sort_values(
        ["game_date", "espn_game_id"]
    ).reset_index(drop=True)
    return merged, n_unm_espn, n_unm_kalshi


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-spread", type=float, default=None)
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    log("Loading ESPN master CSV...")
    espn_df = load_espn_master()
    log(f"  ESPN games: {len(espn_df):,}")

    log("Fetching Kalshi KXNBAGAME events...")
    events = fetch_all_events()
    kalshi_df = build_kalshi_df(events)
    log(f"  Parsed Kalshi events: {len(kalshi_df):,}")

    matched, n_unm_espn, n_unm_kalshi = match_games(espn_df, kalshi_df)
    log(f"Matched: {len(matched):,}  "
        f"unmatched ESPN: {n_unm_espn:,}  "
        f"unmatched Kalshi: {n_unm_kalshi:,}")

    pre_filter = len(matched)
    if args.max_spread is not None:
        matched = matched[matched["abs_spread"] <= args.max_spread]
        log(f"After |spread| ≤ {args.max_spread}: {len(matched):,} games")

    if args.sample is not None and args.sample > 0:
        rng = random.Random(args.seed)
        if args.sample < len(matched):
            idx = rng.sample(range(len(matched)), args.sample)
            matched = matched.iloc[sorted(idx)].reset_index(drop=True)
        log(f"Sampled {len(matched):,} games (seed={args.seed})")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    matched.to_csv(out_path, index=False)

    # Summary
    print()
    print("=== Ticker Matcher Summary ===")
    print(f"ESPN games in master CSV: {len(espn_df):,}")
    print(f"Kalshi KXNBAGAME events fetched: {len(events):,}")
    print(f"Matched (date + teams): {pre_filter:,}")
    print(f"Unmatched ESPN games: {n_unm_espn:,}")
    print(f"Unmatched Kalshi events: {n_unm_kalshi:,}")
    print()
    print("After filters:")
    if args.max_spread is not None:
        print(f"  |spread| ≤ {args.max_spread}: {len(matched):,} games")
    if args.sample is not None:
        print(f"  Sample: {len(matched):,} games")
    print(f"\nOutput written to: {out_path}")

    if args.sample is not None:
        print("\nSelected games:")
        print(f"{'game_id':<10} {'ticker':<30} {'date':<12} {'teams':<10} {'spread':>7}")
        for r in matched.itertuples():
            teams = f"{r.away_team}@{r.home_team}"
            sp = (
                f"{r.home_spread:+.1f}" if pd.notna(r.home_spread) else "—"
            )
            print(
                f"{r.espn_game_id:<10} {r.kalshi_event_ticker:<30} "
                f"{r.game_date:<12} {teams:<10} {sp:>7}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
