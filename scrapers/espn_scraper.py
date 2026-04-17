"""
ESPN NBA game scraper — win probability timeseries + play-by-play.

Fetches ESPN's game summary endpoint for completed NBA games and writes:
  - data/espn_wp/{game_id}.jsonl   — one JSON line per WP observation
  - data/pbp/{game_id}.jsonl       — one JSON line per play event

ESPN's summary endpoint is unauthenticated and undocumented. Structure
observed 2026-04-17 against gameId 401866756 (GSW 126-121 LAC Play-In):

  winprobability: list of N entries, each:
    {homeWinPercentage: float 0-1, tiePercentage: float, playId: str}
  WP is home-team-centric. Away WP = 1 - homeWinPercentage - tiePercentage.
  playId links 1:1 to plays[].id for downstream joins.

  plays: list of N entries, each:
    {id, sequenceNumber, type: {id, text}, text, awayScore, homeScore,
     period: {number, displayValue}, clock: {displayValue},
     scoringPlay, scoreValue, shootingPlay, team: {id},
     wallclock, coordinate: {x, y}, pointsAttempted, shortDescription,
     participants: [...]}

  header.competitions[0]: game metadata — date, status, competitors
    with team.abbreviation, score, homeAway, winner.

Rate-limited: 1-second sleep between HTTP requests.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ---- Config -------------------------------------------------------------

ESPN_SUMMARY_BASE = (
    "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
)
ESPN_SCOREBOARD_BASE = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
)
REQUEST_TIMEOUT_SEC = 15
RATE_LIMIT_SEC = 1.0

WP_DIR = Path("data/espn_wp")
PBP_DIR = Path("data/pbp")


# ESPN uses non-standard team abbreviations. Normalize to the
# standard NBA set (matching nba_master_2025_26.csv and most
# other data sources) at parse time so downstream consumers
# never see the ESPN variants.
_ABBR_NORM = {
    "GS": "GSW", "SA": "SAS", "NO": "NOP",
    "NY": "NYK", "UTAH": "UTA", "WSH": "WAS",
    "PHO": "PHX",
}


def _norm_team(abbr: str) -> str:
    """Normalize ESPN team abbreviation to standard NBA abbreviation."""
    a = str(abbr).upper().strip()
    return _ABBR_NORM.get(a, a)


# ---- Utilities ----------------------------------------------------------

def log(msg: str) -> None:
    """Log with ISO timestamp, always flushed."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def _http_get_json(url: str) -> Optional[Dict[str, Any]]:
    """GET with timeout, returning parsed JSON or None on failure."""
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT_SEC)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"HTTP error for {url}: {e}")
        return None


# ---- Core functions -----------------------------------------------------

def scrape_game(game_id: str) -> Optional[Dict[str, Any]]:
    """Fetch ESPN summary for a single completed game.

    Returns dict with keys: game_id, metadata, wp, plays.
    Returns None on fetch failure or missing data.
    """
    url = f"{ESPN_SUMMARY_BASE}?event={game_id}"
    log(f"Fetching {url}")
    data = _http_get_json(url)
    if data is None:
        log(f"FAIL: could not fetch summary for {game_id}")
        return None

    # ---- Win probability ----
    wp = data.get("winprobability")
    if wp is None:
        log(f"WARN: no 'winprobability' key in summary for {game_id}")
        wp = []

    # ---- Plays ----
    plays = data.get("plays")
    if plays is None:
        log(f"WARN: no 'plays' key in summary for {game_id}")
        plays = []

    # ---- Metadata from header ----
    metadata: Dict[str, Any] = {"game_id": game_id}
    header = data.get("header")
    if header and isinstance(header, dict):
        comps = header.get("competitions", [])
        if comps:
            comp = comps[0]
            metadata["date"] = comp.get("date")
            status = comp.get("status", {})
            metadata["status_type"] = status.get("type", {}).get("name")
            metadata["status_description"] = status.get("type", {}).get("description")
            metadata["game_note"] = header.get("gameNote")

            teams = []
            for competitor in comp.get("competitors", []):
                team_info = competitor.get("team", {})
                raw_abbr = team_info.get("abbreviation")
                teams.append({
                    "abbreviation": _norm_team(raw_abbr) if raw_abbr else raw_abbr,
                    "display_name": team_info.get("displayName"),
                    "team_id": team_info.get("id"),
                    "score": competitor.get("score"),
                    "home_away": competitor.get("homeAway"),
                    "winner": competitor.get("winner"),
                })
            metadata["teams"] = teams

            # Identify home/away for WP interpretation
            for t in teams:
                if t["home_away"] == "home":
                    metadata["home_team"] = t["abbreviation"]
                elif t["home_away"] == "away":
                    metadata["away_team"] = t["abbreviation"]

    log(f"OK: {game_id} — {len(wp)} WP entries, {len(plays)} plays")
    return {
        "game_id": game_id,
        "metadata": metadata,
        "wp": wp,
        "plays": plays,
    }


def save_game(game_data: Dict[str, Any]) -> None:
    """Write WP and PBP to JSONL files. Overwrites if exists (idempotent)."""
    game_id = game_data["game_id"]

    # ---- Write WP ----
    WP_DIR.mkdir(parents=True, exist_ok=True)
    wp_path = WP_DIR / f"{game_id}.jsonl"
    with open(wp_path, "w") as f:
        for entry in game_data["wp"]:
            row = {"game_id": game_id}
            row.update(entry)
            f.write(json.dumps(row, default=str) + "\n")
    log(f"Wrote {len(game_data['wp'])} WP entries to {wp_path}")

    # ---- Write PBP ----
    PBP_DIR.mkdir(parents=True, exist_ok=True)
    pbp_path = PBP_DIR / f"{game_id}.jsonl"
    with open(pbp_path, "w") as f:
        for entry in game_data["plays"]:
            row = {"game_id": game_id}
            row.update(entry)
            f.write(json.dumps(row, default=str) + "\n")
    log(f"Wrote {len(game_data['plays'])} PBP entries to {pbp_path}")


def scrape_date(date_str: str) -> List[str]:
    """Fetch ESPN scoreboard for a date (YYYYMMDD) and return completed gameIds."""
    url = f"{ESPN_SCOREBOARD_BASE}?dates={date_str}"
    log(f"Fetching scoreboard for {date_str}")
    data = _http_get_json(url)
    if data is None:
        log(f"FAIL: could not fetch scoreboard for {date_str}")
        return []

    game_ids: List[str] = []
    for event in data.get("events", []):
        event_id = event.get("id")
        if not event_id:
            continue
        # Check if game is completed
        status = event.get("status", {})
        status_type = status.get("type", {}).get("name", "")
        if status_type.lower() in ("final", "status-final"):
            game_ids.append(event_id)
        elif status.get("type", {}).get("completed", False):
            game_ids.append(event_id)

    log(f"Scoreboard {date_str}: {len(game_ids)} completed games")
    return game_ids


# ---- CLI ----------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python -m scrapers.espn_scraper <gameId> [gameId ...]\n"
            "       python -m scrapers.espn_scraper --date YYYYMMDD",
            file=sys.stderr,
        )
        return 1

    # Collect gameIds — either from args or from --date
    game_ids: List[str] = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
            ids = scrape_date(date_str)
            game_ids.extend(ids)
            time.sleep(RATE_LIMIT_SEC)
            i += 2
        else:
            game_ids.append(sys.argv[i])
            i += 1

    if not game_ids:
        log("No gameIds to scrape")
        return 1

    failures = 0
    for idx, gid in enumerate(game_ids):
        if idx > 0:
            time.sleep(RATE_LIMIT_SEC)

        game_data = scrape_game(gid)
        if game_data is None:
            failures += 1
            continue

        save_game(game_data)

    log(f"Done: {len(game_ids) - failures}/{len(game_ids)} games scraped")
    if failures > 0:
        log(f"WARN: {failures} game(s) failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
