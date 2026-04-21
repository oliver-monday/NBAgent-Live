"""Nightly forward-collection driver.

Pulls yesterday's (America/Los_Angeles) settled NBA games through
the paired-analysis pipeline: ESPN PBP/WP + Kalshi trade tape →
per-game timeseries + scoring-plays CSVs + cached JSON payloads
under data/wp_kalshi_paired/. Protects against Kalshi's ~60-day
trade-tape retention cliff by capturing data within a day of
settlement.

A per-night audit log is written to
data/wp_kalshi_paired/forward_runs/<date>.log regardless of
whether any games were processed (useful for spotting silent
cron failures on days with confirmed games).

Run:
    # Yesterday in America/Los_Angeles (default for the nightly cron)
    python -m analysis.forward_collect

    # Explicit date override (YYYY-MM-DD)
    python -m analysis.forward_collect --date 2026-04-20
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from analysis.wp_vs_kalshi_paired import (
    kalshi_ticker_from_teams,
    run_single_game,
    scoreboard_games,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "data" / "wp_kalshi_paired" / "forward_runs"
PT = ZoneInfo("America/Los_Angeles")
PER_GAME_SLEEP_SEC = 2.0


def _yesterday_pt_iso() -> str:
    d = datetime.now(PT).date() - timedelta(days=1)
    return d.isoformat()


def _iso_to_yyyymmdd(iso: str) -> str:
    return iso.replace("-", "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date", type=str, default=None,
        help="Target date YYYY-MM-DD (default: yesterday in PT).",
    )
    args = parser.parse_args()

    target_iso = args.date or _yesterday_pt_iso()
    target_ymd = _iso_to_yyyymmdd(target_iso)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RUNS_DIR / f"{target_iso}.log"
    lines: list[str] = []

    def emit(msg: str) -> None:
        stamp = datetime.now(timezone.utc).isoformat()
        line = f"[{stamp}] {msg}"
        print(line, flush=True)
        lines.append(line)

    emit(f"Forward collection — target date {target_iso} (PT)")

    try:
        games = scoreboard_games(target_ymd)
    except Exception as e:
        emit(f"ERROR: scoreboard fetch failed: {type(e).__name__}: {e}")
        log_path.write_text("\n".join(lines) + "\n")
        return 1

    playable = [g for g in games if g.get("away") and g.get("home")]
    emit(
        f"Scoreboard returned {len(games)} events "
        f"({len(playable)} with both teams resolved)"
    )

    if not playable:
        emit("No games on scoreboard — off-night, exiting cleanly.")
        log_path.write_text("\n".join(lines) + "\n")
        return 0

    n_ok = 0
    n_fail = 0
    for g in playable:
        away, home, gid = g["away"], g["home"], g["game_id"]
        status = g.get("status", "")
        emit(f"--- {away}@{home} espn_id={gid} status={status} ---")
        try:
            ticker = kalshi_ticker_from_teams(away, home, target_ymd)
            summary = run_single_game(
                str(gid), ticker,
                spread=None, use_cached=False,
                write_report=False,
            )
            if summary.get("status") == "ok":
                n_ok += 1
                emit(
                    f"  OK ticker={ticker} "
                    f"wp_obs={summary.get('n_wp_obs')} "
                    f"trades={summary.get('n_trades'):,} "
                    f"scoring_plays={summary.get('n_scoring_plays')}"
                )
            else:
                n_fail += 1
                emit(
                    f"  FAIL ticker={ticker} "
                    f"error={summary.get('error')}"
                )
        except SystemExit as e:
            n_fail += 1
            emit(f"  SKIP: {e}")
        except Exception as e:
            n_fail += 1
            emit(f"  ERROR: {type(e).__name__}: {e}")
        time.sleep(PER_GAME_SLEEP_SEC)

    emit(
        f"Summary: {n_ok} ok, {n_fail} failed, "
        f"{len(playable)} attempted."
    )
    log_path.write_text("\n".join(lines) + "\n")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
