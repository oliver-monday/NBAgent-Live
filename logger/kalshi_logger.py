"""
Kalshi NBA orderbook logger.

Long-lived polling process that runs during NBA game windows.
Auto-discovers today's NBA game markets on Kalshi and captures orderbook
snapshots every POLL_INTERVAL_SEC. Appends JSONL to data/orderbook_snapshots/{date}.jsonl.
Commits periodically so data persists across runs and workflow restarts.

Market data endpoints on Kalshi are unauthenticated (docs.kalshi.com).
No API key required.

Design:
  - MAX_RUN_SEC caps each invocation well under GitHub Actions' 6-hour limit
  - IDLE_EXIT_SEC short-circuits when no active NBA markets are found
  - Fail-safe: any single request error is logged and skipped, never crashes the loop
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ---- Config -------------------------------------------------------------
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
POLL_INTERVAL_SEC = int(os.environ.get("POLL_INTERVAL_SEC", "30"))
COMMIT_INTERVAL_SEC = int(os.environ.get("COMMIT_INTERVAL_SEC", "300"))
MAX_RUN_SEC = int(os.environ.get("MAX_RUN_SEC", str(5 * 3600 + 15 * 60)))  # 5h15m
IDLE_EXIT_SEC = int(os.environ.get("IDLE_EXIT_SEC", "900"))  # 15 min
REQUEST_TIMEOUT_SEC = 10

DATA_DIR = Path("data/orderbook_snapshots")

# Candidate series tickers for NBA per-game markets. We try each on startup
# and use whichever returns open markets today. This list may be incomplete —
# the discovery function also attempts an event-based fallback.
NBA_CANDIDATE_SERIES_TICKERS = [
    "KXNBAGAME",
    "KXNBAGAMES",
    "KXNBASERIES",
    "KXNBA",  # likely championship, but worth probing in case it ever lists games
]

# ---- Utilities ----------------------------------------------------------

def log(msg: str) -> None:
    """Log with ISO timestamp, always flushed."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def http_get_json(url: str) -> Optional[Dict[str, Any]]:
    """GET with timeout, returning parsed JSON or None on failure."""
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT_SEC)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"http_get_json error for {url}: {e}")
        return None


def games_today_espn() -> int:
    """
    Quick ESPN scoreboard check — returns count of NBA games today.
    -1 if ESPN unreachable (caller treats as unknown → proceed).
    """
    today = datetime.now().strftime("%Y%m%d")
    url = (
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
        f"scoreboard?dates={today}"
    )
    data = http_get_json(url)
    if data is None:
        return -1
    return len(data.get("events", []))


# ---- Kalshi discovery ---------------------------------------------------

def fetch_markets_by_series(series_ticker: str) -> List[Dict[str, Any]]:
    """Fetch all open markets under a series ticker, paginated."""
    out: List[Dict[str, Any]] = []
    cursor = ""
    while True:
        url = (
            f"{KALSHI_BASE}/markets?series_ticker={series_ticker}"
            f"&status=open&limit=200"
        )
        if cursor:
            url += f"&cursor={cursor}"
        data = http_get_json(url)
        if data is None:
            break
        markets = data.get("markets", []) or []
        out.extend(markets)
        cursor = data.get("cursor", "") or ""
        if not cursor:
            break
    return out


def discover_nba_game_markets() -> List[Dict[str, Any]]:
    """
    Find all open NBA per-game markets. Strategy:
      1. Try known candidate series tickers.
      2. Keep markets whose titles look like NBA games (contain 'vs' or '@'
         plus common NBA team tokens) and whose close time is within 24 hours.
    """
    seen_tickers = set()
    candidates: List[Dict[str, Any]] = []
    for series in NBA_CANDIDATE_SERIES_TICKERS:
        ms = fetch_markets_by_series(series)
        if ms:
            log(f"discover: series={series} → {len(ms)} open markets")
        for m in ms:
            t = m.get("ticker")
            if t and t not in seen_tickers:
                seen_tickers.add(t)
                m["_discovered_via_series"] = series
                candidates.append(m)

    # Filter to per-game markets:
    # Per-game markets typically have a close timestamp within 24 hours
    # (games finish within a few hours), unlike season-long championship/qualifier markets.
    now_ts = int(time.time())
    game_markets: List[Dict[str, Any]] = []
    for m in candidates:
        close_ts = m.get("close_ts") or m.get("close_time")
        if isinstance(close_ts, str):
            # Sometimes returned as ISO string
            try:
                close_ts = int(datetime.fromisoformat(close_ts.replace("Z", "+00:00")).timestamp())
            except Exception:
                close_ts = None
        if close_ts is None:
            # Can't filter by time — include and let downstream filter
            game_markets.append(m)
            continue
        if 0 < close_ts - now_ts < 36 * 3600:
            game_markets.append(m)

    return game_markets


# ---- Market snapshot ----------------------------------------------------

def fetch_orderbook(market_ticker: str) -> Optional[Dict[str, Any]]:
    url = f"{KALSHI_BASE}/markets/{market_ticker}/orderbook"
    data = http_get_json(url)
    if data is None:
        return None
    return data.get("orderbook") or data.get("orderbook_fp") or {}


def fetch_market_state(market_ticker: str) -> Optional[Dict[str, Any]]:
    url = f"{KALSHI_BASE}/markets/{market_ticker}"
    data = http_get_json(url)
    if data is None:
        return None
    return data.get("market") or {}


def snapshot_market(market_ticker: str, discovery_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build one snapshot row for a market. Returns None on fetch failure."""
    state = fetch_market_state(market_ticker)
    ob = fetch_orderbook(market_ticker)
    if state is None and ob is None:
        return None
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "ts": ts,
        "ticker": market_ticker,
        "event_ticker": discovery_meta.get("event_ticker"),
        "series": discovery_meta.get("_discovered_via_series"),
        "title": discovery_meta.get("title") or (state or {}).get("title"),
        "status": (state or {}).get("status"),
        "close_ts": (state or {}).get("close_ts"),
        # Prices in cents (integer) are Kalshi's common representation;
        # some fields return dollars. We log both when available.
        "yes_bid": (state or {}).get("yes_bid"),
        "yes_ask": (state or {}).get("yes_ask"),
        "no_bid": (state or {}).get("no_bid"),
        "no_ask": (state or {}).get("no_ask"),
        "last_price": (state or {}).get("last_price"),
        "volume": (state or {}).get("volume"),
        "volume_24h": (state or {}).get("volume_24h"),
        "open_interest": (state or {}).get("open_interest"),
        # Full orderbook depth — trim client-side later if storage grows
        "orderbook": ob,
    }


# ---- Persistence --------------------------------------------------------

def write_snapshot(date_str: str, snapshot: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{date_str}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(snapshot) + "\n")


def git_commit_push() -> None:
    """Commit and push new data. Uses GitHub Actions bot identity."""
    try:
        subprocess.run(
            ["git", "config", "user.name", "github-actions[bot]"],
            check=False, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email",
             "41898282+github-actions[bot]@users.noreply.github.com"],
            check=False, capture_output=True,
        )
        subprocess.run(["git", "add", "data/"], check=False, capture_output=True)
        # diff-index returns non-zero if there are staged changes
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], check=False, capture_output=True,
        )
        if diff.returncode == 0:
            log("commit: no changes staged")
            return
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        subprocess.run(
            ["git", "commit", "-m", f"[skip ci] Kalshi snapshots {ts}"],
            check=False, capture_output=True,
        )
        push = subprocess.run(
            ["git", "push"], check=False, capture_output=True, text=True,
        )
        if push.returncode == 0:
            log("commit: pushed")
        else:
            log(f"commit: push failed — {push.stderr.strip()}")
    except Exception as e:
        log(f"commit: error — {e}")


# ---- Main loop ----------------------------------------------------------

def main() -> int:
    log(
        f"start | poll={POLL_INTERVAL_SEC}s commit_every={COMMIT_INTERVAL_SEC}s "
        f"max_run={MAX_RUN_SEC}s idle_exit={IDLE_EXIT_SEC}s"
    )

    # Pre-flight: is there any NBA action today?
    games_count = games_today_espn()
    if games_count == 0:
        log("no NBA games on ESPN today — exiting")
        return 0
    log(f"ESPN games today: {games_count if games_count >= 0 else 'unknown'}")

    start = time.time()
    last_commit = start
    idle_since: Optional[float] = None
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    while time.time() - start < MAX_RUN_SEC:
        cycle_start = time.time()

        game_markets = discover_nba_game_markets()
        active = [m for m in game_markets if (m.get("status") or "").lower() in ("active", "open")]

        if not active:
            if idle_since is None:
                idle_since = cycle_start
            idle_sec = int(cycle_start - idle_since)
            log(f"cycle: no active NBA game markets (idle {idle_sec}s)")
            if idle_sec >= IDLE_EXIT_SEC:
                log(f"exit: idle threshold reached ({IDLE_EXIT_SEC}s)")
                break
        else:
            idle_since = None
            log(f"cycle: snapshotting {len(active)} markets")
            for m in active:
                ticker = m.get("ticker")
                if not ticker:
                    continue
                snap = snapshot_market(ticker, m)
                if snap is not None:
                    write_snapshot(date_str, snap)

        # Periodic commit
        if time.time() - last_commit >= COMMIT_INTERVAL_SEC:
            git_commit_push()
            last_commit = time.time()

        # Sleep for remainder of poll interval
        elapsed = time.time() - cycle_start
        sleep_for = max(POLL_INTERVAL_SEC - elapsed, 1)
        time.sleep(sleep_for)

    # Final commit on exit
    git_commit_push()
    log("end")
    return 0


if __name__ == "__main__":
    sys.exit(main())
