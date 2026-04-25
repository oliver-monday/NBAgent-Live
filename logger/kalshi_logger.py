"""
Kalshi NBA orderbook logger.

Long-lived polling process that runs during NBA game windows.
Auto-discovers today's NBA game markets on Kalshi and captures orderbook
snapshots every POLL_INTERVAL_SEC. Appends JSONL to
data/orderbook_snapshots/{event_ticker}.jsonl — one file per Kalshi
per-game event (both sides of the market share the file). Commits
periodically so data persists across runs and workflow restarts.

Market data endpoints on Kalshi are unauthenticated (docs.kalshi.com).
No API key required.

Design:
  - MAX_RUN_SEC caps each invocation (default 24h; override via env var)
  - IDLE_EXIT_SEC short-circuits when no active NBA markets are found
  - Fail-safe: any single request error is logged and skipped, never crashes the loop
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter

# ---- Config -------------------------------------------------------------
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
POLL_INTERVAL_SEC = int(os.environ.get("POLL_INTERVAL_SEC", "30"))
COMMIT_INTERVAL_SEC = int(os.environ.get("COMMIT_INTERVAL_SEC", "300"))
MAX_RUN_SEC = int(os.environ.get("MAX_RUN_SEC", str(24 * 3600)))  # 24h; override via env if needed
IDLE_EXIT_SEC = int(os.environ.get("IDLE_EXIT_SEC", "900"))  # 15 min
REQUEST_TIMEOUT_SEC = 10

# Cascade detection (Fix 2): if this many consecutive http_get_json calls
# within a single cycle fail, force a session reset + short backoff before
# continuing. Prevents the 2026-04-24 OKCPHX failure mode where a stale
# connection pool caused every market's snapshot to time out at 10s each.
CYCLE_FAILURE_CASCADE_THRESHOLD = 3
CYCLE_CASCADE_BACKOFF_SEC = 15

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

# Per-game market ticker format: <SERIES_PREFIX>-YYMMMDD<TEAMS>-<SIDE>
# Example: KXNBAGAME-26APR17GSWPHX-PHX  →  game date = 2026-04-17 (ET)
# Kalshi uses ET for the date prefix (NBA's scheduling timezone).
_TICKER_DATE_RE = re.compile(r"^[A-Z]+-(\d{2})([A-Z]{3})(\d{2})")
_MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
ET = ZoneInfo("America/New_York")


def parse_ticker_game_date(ticker: Optional[str]) -> Optional[date]:
    """Extract the game date from a Kalshi per-game market ticker.
    Returns None for tickers that don't match the per-game format
    (e.g. series markets, championship markets)."""
    if not ticker:
        return None
    m = _TICKER_DATE_RE.match(ticker)
    if not m:
        return None
    yy, mmm, dd = m.group(1), m.group(2), m.group(3)
    month = _MONTH_MAP.get(mmm)
    if month is None:
        return None
    try:
        return date(2000 + int(yy), month, int(dd))
    except ValueError:
        return None


# ---- Utilities ----------------------------------------------------------

def log(msg: str) -> None:
    """Log with ISO timestamp, always flushed."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


# ---- Managed HTTP session (Fix 1) ---------------------------------------
# Background: urllib3's connection pool keeps TCP sockets alive across
# requests. If a connection goes half-open (WiFi blip, laptop sleep/wake,
# Kalshi edge restart) the local socket doesn't know the remote end is
# dead; the next request picks that stale connection, sends the request,
# and blocks on the read until REQUEST_TIMEOUT_SEC fires. We own the
# Session so we can close it and recreate a fresh pool when we detect
# this failure mode. See 2026-04-24 OKCPHX incident log.

_session: Optional[requests.Session] = None
# Track consecutive failures across calls. `reset_http_session` zeroes this.
_consecutive_failures: int = 0


def _build_session() -> requests.Session:
    s = requests.Session()
    # Small, known pool. Matches single-threaded cycle loop; leaves
    # headroom for git push fetches etc. If we add concurrency later,
    # bump pool_maxsize.
    adapter = HTTPAdapter(pool_connections=4, pool_maxsize=8)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = _build_session()
    return _session


def reset_http_session(reason: str = "") -> None:
    """Close the current session and rebuild. Called after cascading
    failures to discard any stale/half-open connections. This is
    deliberately heavyweight (drops the keep-alive pool); use
    `_reset_failure_counter` instead when you only need to scope
    cascade detection to a new cycle window."""
    global _session, _consecutive_failures
    suffix = f" ({reason})" if reason else ""
    log(f"http: resetting session{suffix}")
    if _session is not None:
        try:
            _session.close()
        except Exception:
            pass
    _session = _build_session()
    _consecutive_failures = 0


def _reset_failure_counter() -> None:
    """Zero the cascade counter without dropping the connection pool.
    Called at cycle start so the cascade threshold is measured per
    cycle, while keep-alive connections survive across cycles."""
    global _consecutive_failures
    _consecutive_failures = 0


def consecutive_failures() -> int:
    """Number of http_get_json failures since the last success or reset."""
    return _consecutive_failures


def http_get_json(url: str) -> Optional[Dict[str, Any]]:
    """GET with timeout, returning parsed JSON or None on failure.

    On timeout or connection error, the managed session is reset on the
    spot — the next call gets a fresh TCP connection pool, which fixes
    the stale-half-open-connection failure mode observed 2026-04-24.
    Other errors (HTTPError, JSON decode) do not reset the session; they
    just return None. Updates `_consecutive_failures` for cycle-level
    cascade detection (Fix 2).
    """
    global _consecutive_failures
    try:
        r = _get_session().get(url, timeout=REQUEST_TIMEOUT_SEC)
        r.raise_for_status()
        _consecutive_failures = 0
        return r.json()
    except (requests.exceptions.Timeout,
            requests.exceptions.ConnectionError) as e:
        _consecutive_failures += 1
        log(f"http_get_json error for {url}: {e}")
        # A single stale connection poisons all subsequent reuse. Drop
        # the pool immediately; the next call rebuilds.
        reset_http_session(reason=f"after {type(e).__name__} on {url}")
        return None
    except Exception as e:
        _consecutive_failures += 1
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

    # Filter to per-game markets by parsing the game date from the ticker.
    # Kalshi playoff markets have close_time set to the series-conclusion
    # buffer (~2 weeks out), so close_ts is not usable as a "game is today"
    # signal. The ticker prefix (e.g. KXNBAGAME-26APR17GSWPHX-PHX) encodes
    # the game date in ET, which is the correct field.
    #
    # Accept tickers dated within ±1 day of today ET. The ±1 window covers:
    #   - today's games (primary case)
    #   - games that cross midnight ET (late West Coast tips)
    #   - early listings for tomorrow (pre-tip capture on morning block)
    today_et = datetime.now(ET).date()
    game_markets: List[Dict[str, Any]] = []
    for m in candidates:
        game_date = parse_ticker_game_date(m.get("ticker"))
        if game_date is None:
            continue
        if abs((game_date - today_et).days) <= 1:
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
    """Build one snapshot row for a market. Returns None on fetch failure.

    Prices are kept as raw string decimals in dollars (e.g. '0.67') — lossless;
    cast to Decimal/float downstream in analysis. Sizes and volumes use Kalshi's
    fixed-point numeric representation (`*_fp`), kept as-is.

    Orderbook payload shape (observed 2026-04-16):
      {"yes_dollars": [[price_str, size_str], ...],
       "no_dollars":  [[price_str, size_str], ...]}
    Depth ~30 levels per side across the penny grid.
    """
    state = fetch_market_state(market_ticker)
    ob = fetch_orderbook(market_ticker)
    if state is None and ob is None:
        return None
    s = state or {}
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "ts": ts,
        "ticker": market_ticker,
        "event_ticker": discovery_meta.get("event_ticker") or s.get("event_ticker"),
        "series": discovery_meta.get("_discovered_via_series"),
        "title": discovery_meta.get("title") or s.get("title"),
        "status": s.get("status"),
        # Timestamps — all ISO strings from the API
        "close_time": s.get("close_time"),
        "open_time": s.get("open_time"),
        "updated_time": s.get("updated_time"),
        # Prices — raw string decimals in dollars
        "yes_bid_dollars": s.get("yes_bid_dollars"),
        "yes_ask_dollars": s.get("yes_ask_dollars"),
        "no_bid_dollars": s.get("no_bid_dollars"),
        "no_ask_dollars": s.get("no_ask_dollars"),
        "last_price_dollars": s.get("last_price_dollars"),
        # Top-of-book sizes — fixed-point numeric. no_* mirrors included
        # speculatively; if they come back null we drop them in a followup.
        "yes_bid_size_fp": s.get("yes_bid_size_fp"),
        "yes_ask_size_fp": s.get("yes_ask_size_fp"),
        "no_bid_size_fp": s.get("no_bid_size_fp"),
        "no_ask_size_fp": s.get("no_ask_size_fp"),
        # Market-level liquidity / volume / OI
        "liquidity_dollars": s.get("liquidity_dollars"),
        "volume_fp": s.get("volume_fp"),
        "volume_24h_fp": s.get("volume_24h_fp"),
        "open_interest_fp": s.get("open_interest_fp"),
        # Full orderbook depth — trim client-side later if storage grows
        "orderbook": ob,
    }


# ---- Persistence --------------------------------------------------------

def write_snapshot(snapshot: Dict[str, Any]) -> None:
    """Append one snapshot to its per-event JSONL file.

    Files are named by the market's event_ticker so both sides of a
    game (home + away) land in the same file; analysis groups by the
    `ticker` field inside each row. Fallback to the individual ticker
    if event_ticker is missing (defensive — should not happen in
    normal operation)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    event_ticker = (
        snapshot.get("event_ticker")
        or snapshot.get("ticker")
        or "unknown"
    )
    path = DATA_DIR / f"{event_ticker}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(snapshot) + "\n")


def git_commit_push() -> None:
    """Commit and push new data. Uses GitHub Actions bot identity.

    Rebases on origin/main before each push attempt to avoid
    non-fast-forward rejections when other actors (developer commits,
    Claude Code, other workflows) land on main during this run. Retries
    the pull-rebase-push cycle up to 2 times; if all attempts fail,
    snapshots remain committed locally and the next cycle will retry.
    """
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
        # Pull-rebase then push, with one retry. --autostash protects
        # any uncommitted files (there shouldn't be any after the commit
        # above, but it's a safe no-op when the working tree is clean).
        for attempt in range(1, 3):
            pull = subprocess.run(
                ["git", "pull", "--rebase", "--autostash", "origin", "main"],
                check=False, capture_output=True, text=True,
            )
            if pull.returncode != 0:
                tail = (pull.stderr.strip().splitlines() or ["(no stderr)"])[-1]
                log(f"commit: pull --rebase failed (attempt {attempt}) — {tail}")
                continue
            push = subprocess.run(
                ["git", "push"], check=False, capture_output=True, text=True,
            )
            if push.returncode == 0:
                log("commit: pushed")
                return
            tail = (push.stderr.strip().splitlines() or ["(no stderr)"])[-1]
            log(f"commit: push failed (attempt {attempt}) — {tail}")
        log("commit: push failed after 2 attempts; "
            "snapshots committed locally, will retry next cycle")
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
            # Fix 2: per-cycle cascade detection. Zero the failure
            # counter at cycle start so "3 consecutive failures" is
            # measured within this cycle's snapshot loop. Keep the
            # connection pool warm — keep-alive across cycles is the
            # whole point of the managed Session.
            _reset_failure_counter()
            aborted = False
            for m in active:
                ticker = m.get("ticker")
                if not ticker:
                    continue
                snap = snapshot_market(ticker, m)
                if snap is not None:
                    write_snapshot(snap)
                # If N consecutive http_get_json calls have failed,
                # assume the network path is degraded (not a single
                # bad market). Back off briefly, rebuild the session
                # one more time, and skip the remaining markets this
                # cycle — the next cycle will re-discover and retry.
                if consecutive_failures() >= CYCLE_FAILURE_CASCADE_THRESHOLD:
                    log(
                        f"cycle: cascade of "
                        f"{consecutive_failures()} consecutive HTTP "
                        f"failures; backing off "
                        f"{CYCLE_CASCADE_BACKOFF_SEC}s and skipping "
                        f"remainder of cycle"
                    )
                    time.sleep(CYCLE_CASCADE_BACKOFF_SEC)
                    reset_http_session(reason="cycle cascade backoff")
                    aborted = True
                    break
            if aborted:
                log("cycle: aborted early due to cascade; "
                    "will retry on next cycle")

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
