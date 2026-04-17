"""
ESPN backfill utility — season-wide WP + PBP scraper.

Reads game IDs from `data/nba_master_2025_26.csv` (inherited from
NBAgent) and scrapes ESPN summary data for each one via
`scrapers.espn_scraper`. Idempotent: skips games whose WP file
already exists.

Usage:
    # Full season
    python -m scrapers.espn_backfill

    # Date range
    python -m scrapers.espn_backfill --start 2026-01-01 --end 2026-03-31

    # Competitive only (|home_spread| <= 6)
    python -m scrapers.espn_backfill --max-spread 6

    # Team filter (home or away)
    python -m scrapers.espn_backfill --team GSW --team LAC

Rate-limited at 1s between ESPN calls. Full-season run ≈ 25 min.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd

from scrapers.espn_scraper import (
    RATE_LIMIT_SEC,
    WP_DIR,
    PBP_DIR,
    log,
    save_game,
    scrape_game,
)

CSV_PATH = Path("data/nba_master_2025_26.csv")
PROGRESS_INTERVAL = 25


# ---- Helpers ------------------------------------------------------------

def _fmt_eta(seconds: float) -> str:
    """Format seconds as '20m 5s' or '1h 3m'."""
    seconds = int(max(seconds, 0))
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def load_games(
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_spread: Optional[float] = None,
    teams: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Load CSV and apply filters. Returns DataFrame sorted by game_date."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Game master CSV not found at {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    df["game_id"] = df["game_id"].astype(str)
    df["game_date"] = df["game_date"].astype(str)

    total = len(df)
    filters_applied = []

    if start is not None:
        df = df[df["game_date"] >= start]
        filters_applied.append(f"start>={start}")
    if end is not None:
        df = df[df["game_date"] <= end]
        filters_applied.append(f"end<={end}")
    if max_spread is not None:
        # NaN spreads are dropped when filtering by spread — if we can't
        # confirm competitiveness, we exclude it from a competitive filter.
        df = df[df["home_spread"].abs() <= max_spread]
        filters_applied.append(f"|spread|<={max_spread}")
    if teams:
        up = [t.upper() for t in teams]
        df = df[
            df["home_team_abbrev"].str.upper().isin(up)
            | df["away_team_abbrev"].str.upper().isin(up)
        ]
        filters_applied.append(f"teams={','.join(up)}")

    df = df.sort_values("game_date").reset_index(drop=True)
    log(
        f"CSV: {total} games total, {len(df)} after filters "
        f"({', '.join(filters_applied) if filters_applied else 'none'})"
    )
    return df


# ---- Backfill loop ------------------------------------------------------

def run_backfill(df: pd.DataFrame) -> int:
    """Iterate, scrape missing games, report progress. Returns exit code."""
    WP_DIR.mkdir(parents=True, exist_ok=True)
    PBP_DIR.mkdir(parents=True, exist_ok=True)

    total = len(df)
    if total == 0:
        log("No games to process after filtering.")
        return 0

    scraped = 0
    skipped = 0
    failures: List[dict] = []
    started_at = time.time()

    for idx, row in df.iterrows():
        game_id = row["game_id"]
        game_date = row["game_date"]
        matchup = f"{row.get('away_team_abbrev','?')} @ {row.get('home_team_abbrev','?')}"

        wp_path = WP_DIR / f"{game_id}.jsonl"
        if wp_path.exists():
            skipped += 1
        else:
            # Rate-limit before each real ESPN call (not before skips)
            if scraped > 0:
                time.sleep(RATE_LIMIT_SEC)

            try:
                game_data = scrape_game(game_id)
                if game_data is None:
                    failures.append({
                        "game_id": game_id, "date": game_date,
                        "matchup": matchup, "error": "scrape_game returned None",
                    })
                else:
                    save_game(game_data)
                    scraped += 1
            except Exception as e:
                failures.append({
                    "game_id": game_id, "date": game_date,
                    "matchup": matchup, "error": f"{type(e).__name__}: {e}",
                })
                log(f"FAIL {game_id} {game_date} {matchup}: {e}")

        # Progress line every PROGRESS_INTERVAL games (1-indexed)
        done = idx + 1
        if done % PROGRESS_INTERVAL == 0 or done == total:
            remaining_games = total - done
            # ETA estimates only the games we'd actually scrape (not skip).
            # Use the current scrape rate if we have any, else assume worst case.
            if scraped > 0:
                per_game = (time.time() - started_at) / done
            else:
                per_game = RATE_LIMIT_SEC
            eta_sec = remaining_games * per_game
            print(
                f"[{done:4d}/{total}] {game_date} | "
                f"scraped {scraped}, skipped {skipped}, failed {len(failures)} | "
                f"ETA: {_fmt_eta(eta_sec)}",
                flush=True,
            )

    # ---- Final summary ----
    dates = sorted(df["game_date"].unique())
    wp_total = len(list(WP_DIR.glob("*.jsonl")))
    pbp_total = len(list(PBP_DIR.glob("*.jsonl")))

    print()
    print("Backfill complete.")
    print(f"  Games in filter set: {total}")
    print(f"  Already existed (skipped): {skipped}")
    print(f"  Newly scraped: {scraped}")
    print(f"  Failed: {len(failures)}")
    if dates:
        print(f"  Date range processed: {dates[0]} through {dates[-1]}")
    print(f"  Total ESPN WP files on disk: {wp_total}")
    print(f"  Total PBP files on disk: {pbp_total}")

    if failures:
        print()
        print("Failed games (retry with: python -m scrapers.espn_scraper <id>):")
        for f in failures:
            print(f"  {f['game_id']}  {f['date']}  {f['matchup']}  ({f['error']})")
        return 1

    return 0


# ---- CLI ---------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill ESPN WP+PBP data for 2025-26 NBA games."
    )
    p.add_argument("--start", help="Filter: game_date >= YYYY-MM-DD")
    p.add_argument("--end", help="Filter: game_date <= YYYY-MM-DD")
    p.add_argument(
        "--max-spread", type=float,
        help="Filter: |home_spread| <= N (NaN spreads excluded)",
    )
    p.add_argument(
        "--team", action="append",
        help="Filter: only games with this team (home or away); repeatable",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    log(
        f"start | start={args.start} end={args.end} "
        f"max_spread={args.max_spread} teams={args.team}"
    )

    try:
        df = load_games(
            start=args.start, end=args.end,
            max_spread=args.max_spread, teams=args.team,
        )
    except FileNotFoundError as e:
        log(f"FATAL: {e}")
        return 2

    return run_backfill(df)


if __name__ == "__main__":
    sys.exit(main())
