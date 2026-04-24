"""Live (paper-trading) runner for the S4A engine.

The only module with network I/O. Polls Kalshi per-game markets every
POLL_INTERVAL_SEC, determines each game's favorite from opening prices
(no external spread dependency), feeds favorite bid prices through
S4ASignalDetector, and logs every tick + simulated trade to a JSONL
journal under data/paper_trades/.

No real orders are submitted — this is paper-trading only. Market-data
endpoints on Kalshi are unauthenticated, so no API key is needed.

Run:
    python -m engine.live_runner
    python -m engine.live_runner --max-run-sec 7200 --idle-exit-sec 600
"""

from __future__ import annotations

import argparse
import json
import random
import re
import signal as _signal
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from engine.position_manager import PositionManager, TradeAction
from engine.s4a_signal import S4ASignalDetector, Signal


# ---- Constants ---------------------------------------------------------

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
SERIES_CANDIDATES = [
    "KXNBAGAME",
    "KXNBAGAMES",
    "KXNBASERIES",
    "KXNBA",
]
POLL_INTERVAL_SEC = 30
SETTLE_THRESHOLD = 0.05           # ignore quotes below this (pre-tip penny grid)
REQUEST_TIMEOUT_SEC = 10
MAX_RETRIES = 3
BACKOFF_BASE_SEC = 0.5
# If the wall-clock gap between cycle starts exceeds this, emit a
# warning. Catches the macOS App Nap / suspend case where the Python
# process sleeps through multiple poll intervals — the warning appears
# once the loop resumes so the operator knows ticks were missed.
CYCLE_GAP_WARN_SEC = 60

REPO_ROOT = Path(__file__).resolve().parents[1]
JOURNAL_DIR = REPO_ROOT / "data" / "paper_trades"

PT = ZoneInfo("America/Los_Angeles")
ET = ZoneInfo("America/New_York")

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
_TICKER_DATE_RE = re.compile(r"^[A-Z]+-(\d{2})([A-Z]{3})(\d{2})")

# Per-event ticker suffix: the final hyphen-delimited segment is a team
# abbreviation that matches one half of the date+teams block immediately
# preceding it (e.g., KXNBAGAME-26APR17GSWPHX-PHX, teams=GSWPHX, side=PHX).
_SIDE_TICKER_RE = re.compile(r"^([A-Z]+-\d{2}[A-Z]{3}\d{2}[A-Z]{6})-([A-Z]{2,5})$")


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


# ---- HTTP helper -------------------------------------------------------

def _kalshi_get(path: str, params: dict | None = None) -> dict | None:
    """Single-attempt GET with one retry reserved for 429 rate limits.

    Rationale: we poll every POLL_INTERVAL_SEC (30s). A missed tick is
    recoverable — the next cycle tries again. The earlier multi-retry
    cascade (3 × 10s timeouts + backoff ≈ 31s) could stall the whole
    loop on a single slow upstream, which is worse than a missed tick.
    """
    url = f"{BASE_URL}{path}"
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SEC)
    except requests.RequestException as e:
        log(f"  GET {path} network error: {type(e).__name__}")
        return None
    if r.status_code == 429:
        sleep_for = BACKOFF_BASE_SEC + random.random() * 0.25
        log(f"  429 rate-limited on {path} — single retry after {sleep_for:.2f}s")
        time.sleep(sleep_for)
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SEC)
        except requests.RequestException as e:
            log(f"  GET {path} retry after 429 failed: {type(e).__name__}")
            return None
    try:
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        log(f"  GET {path} HTTP {r.status_code}: {e}")
        return None
    except ValueError as e:
        log(f"  GET {path} invalid JSON: {e}")
        return None


# ---- Parsing helpers ---------------------------------------------------

def parse_ticker_game_date(ticker: str | None) -> date | None:
    if not ticker:
        return None
    m = _TICKER_DATE_RE.match(ticker)
    if not m:
        return None
    yy, mon, dd = m.group(1), m.group(2), m.group(3)
    mon_num = _MONTHS.get(mon)
    if mon_num is None:
        return None
    try:
        return date(2000 + int(yy), mon_num, int(dd))
    except ValueError:
        return None


def parse_side_ticker(market_ticker: str) -> tuple[str, str, str, str] | None:
    """Parse 'KXNBAGAME-26APR17GSWPHX-PHX' into
    (event_ticker, side_team, away_team, home_team). Returns None for
    tickers that don't match the per-game side format.
    """
    m = _SIDE_TICKER_RE.match(market_ticker)
    if not m:
        return None
    event_ticker, side_team = m.group(1), m.group(2)
    # Event ticker tail holds AWY(3) + HOM(3)
    teams_block = event_ticker[-6:]
    away, home = teams_block[:3], teams_block[3:]
    return event_ticker, side_team, away, home


# ---- Discovery ---------------------------------------------------------

def discover_nba_markets(for_date: date | None = None) -> list[dict]:
    """Return one entry per NBA game scheduled for `for_date` (default:
    today ET, the timezone Kalshi uses for game-date prefixes).

    Each entry:
        {
          'event_ticker': str,
          'away_ticker':  str,
          'home_ticker':  str,
          'away_team':    str,
          'home_team':    str,
        }
    """
    target_date = for_date or datetime.now(ET).date()
    seen: set[str] = set()
    markets: list[dict] = []
    for series in SERIES_CANDIDATES:
        cursor = ""
        while True:
            params: dict[str, Any] = {
                "series_ticker": series, "status": "open", "limit": 200,
            }
            if cursor:
                params["cursor"] = cursor
            data = _kalshi_get("/markets", params)
            if data is None:
                break
            chunk = data.get("markets") or []
            for m in chunk:
                t = m.get("ticker")
                if t and t not in seen:
                    seen.add(t)
                    markets.append(m)
            cursor = data.get("cursor") or ""
            if not cursor:
                break

    # Group side markets by event_ticker.
    by_event: dict[str, dict] = {}
    for m in markets:
        ticker = m.get("ticker")
        parsed = parse_side_ticker(ticker) if ticker else None
        if parsed is None:
            continue
        event_ticker, side_team, away_team, home_team = parsed
        game_date = parse_ticker_game_date(ticker)
        if game_date is None or game_date != target_date:
            continue
        entry = by_event.setdefault(event_ticker, {
            "event_ticker": event_ticker,
            "away_team": away_team, "home_team": home_team,
            "away_ticker": None, "home_ticker": None,
        })
        if side_team == away_team:
            entry["away_ticker"] = ticker
        elif side_team == home_team:
            entry["home_ticker"] = ticker

    out = [
        e for e in by_event.values()
        if e["away_ticker"] and e["home_ticker"]
    ]
    log(
        f"Discovery: {len(markets)} open markets, "
        f"{len(out)} NBA games for {target_date.isoformat()}"
    )
    return out


def fetch_market_state(ticker: str) -> dict | None:
    data = _kalshi_get(f"/markets/{ticker}")
    if data is None:
        return None
    return data.get("market") or None


# ---- Per-game state ----------------------------------------------------

@dataclass
class GameContext:
    event_ticker: str
    away_team: str
    home_team: str
    away_ticker: str
    home_ticker: str

    fav_ticker: str | None = None
    fav_team: str | None = None
    fav_side: str | None = None        # "home" or "away"
    fav_locked_at: float | None = None
    fav_opening_price: float | None = None

    detector: S4ASignalDetector = field(default_factory=S4ASignalDetector)
    finished: bool = False             # market settled/closed

    @property
    def game_id(self) -> str:
        return f"{self.away_team}-at-{self.home_team}"


def _coerce_price(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def resolve_favorite(ctx: GameContext, now_ts: float) -> None:
    """Determine ctx.fav_* once BOTH sides quote > SETTLE_THRESHOLD."""
    if ctx.fav_ticker is not None:
        return
    away = fetch_market_state(ctx.away_ticker)
    home = fetch_market_state(ctx.home_ticker)
    if not away or not home:
        return
    a_bid = _coerce_price(away.get("yes_bid_dollars"))
    h_bid = _coerce_price(home.get("yes_bid_dollars"))
    if a_bid is None or h_bid is None:
        return
    if a_bid <= SETTLE_THRESHOLD or h_bid <= SETTLE_THRESHOLD:
        return
    if h_bid >= a_bid:
        ctx.fav_ticker = ctx.home_ticker
        ctx.fav_team = ctx.home_team
        ctx.fav_side = "home"
        ctx.fav_opening_price = h_bid
    else:
        ctx.fav_ticker = ctx.away_ticker
        ctx.fav_team = ctx.away_team
        ctx.fav_side = "away"
        ctx.fav_opening_price = a_bid
    ctx.fav_locked_at = now_ts
    log(
        f"Favorite locked: {ctx.fav_team} YES at ${ctx.fav_opening_price:.2f} "
        f"(home ${h_bid:.2f} vs away ${a_bid:.2f}) — "
        f"event {ctx.event_ticker}"
    )


# ---- Journal writer ----------------------------------------------------

@dataclass
class Journal:
    path: Path
    _fh: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", buffering=1)  # line-buffered

    def append(self, record: dict) -> None:
        self._fh.write(json.dumps(record) + "\n")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _tick_record(
    ctx: GameContext, fav_state: dict, signal: Signal,
    manager: PositionManager, ts: float,
) -> dict:
    fav_bid = _coerce_price(fav_state.get("yes_bid_dollars"))
    fav_ask = _coerce_price(fav_state.get("yes_ask_dollars"))
    pos_state = manager.game_state(ctx.game_id)
    return {
        "type": "tick",
        "ts": _iso(ts),
        "game_id": ctx.game_id,
        "event_ticker": ctx.event_ticker,
        "fav_ticker": ctx.fav_ticker,
        "fav_team": ctx.fav_team,
        "fav_bid": fav_bid,
        "fav_ask": fav_ask,
        "trailing_max": ctx.detector.trailing_max,
        "current_dip": ctx.detector.current_dip,
        "observation_count": ctx.detector.observation_count,
        "signal": signal.value,
        "position_status": pos_state["status"],
        "entries_this_game": pos_state["entries_this_game"],
        "active_positions": manager.active_count(),
        "market_status": fav_state.get("status"),
    }


def _trade_record(action: TradeAction) -> dict:
    pnl_after_fees = action.pnl  # PositionManager already nets fees
    return {
        "type": "trade",
        "ts": _iso(action.ts),
        "action": action.action,
        "game_id": action.game_id,
        "ticker": action.ticker,
        "price": action.price,
        "contracts": action.contracts,
        "entry_price": action.entry_price,
        "pnl": action.pnl,
        "pnl_after_fees": pnl_after_fees,
        "hold_seconds": action.hold_seconds,
        "reason": action.reason,
        "ratchet_triggered": action.ratchet_triggered,
    }


# ---- Session orchestration --------------------------------------------

def _is_finished_status(status: str | None) -> bool:
    if not status:
        return False
    return status.lower() in {"settled", "closed", "finalized", "determined"}


@dataclass
class Session:
    args: argparse.Namespace
    journal: Journal
    manager: PositionManager = field(default_factory=PositionManager)
    games: dict[str, GameContext] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    _interrupted: bool = False


def _install_signal_handlers(session: Session) -> None:
    def handler(signum, frame):  # noqa: ARG001
        log(f"Received signal {signum} — flagging shutdown")
        session._interrupted = True
    _signal.signal(_signal.SIGINT, handler)
    _signal.signal(_signal.SIGTERM, handler)


def run_session(args: argparse.Namespace) -> int:
    today_pt = datetime.now(PT).date().isoformat()
    journal_path = JOURNAL_DIR / f"{today_pt}.jsonl"
    journal = Journal(journal_path)
    log(f"Journal: {journal_path}")

    ratchet = getattr(args, "ratchet", 0.08)
    manager = PositionManager(
        ratchet_trigger=ratchet if ratchet and ratchet > 0 else None,
    )
    session = Session(args=args, journal=journal, manager=manager)
    _install_signal_handlers(session)
    log(
        f"PositionManager: ratchet_trigger={manager.ratchet_trigger} "
        f"(None = disabled)"
    )

    games = discover_nba_markets()
    if not games:
        log("No NBA games discovered. Exiting.")
        journal.append({
            "type": "session_start",
            "ts": _iso(time.time()),
            "games_found": 0,
        })
        journal.close()
        return 0

    for g in games:
        ctx = GameContext(
            event_ticker=g["event_ticker"],
            away_team=g["away_team"], home_team=g["home_team"],
            away_ticker=g["away_ticker"], home_ticker=g["home_ticker"],
        )
        session.games[ctx.game_id] = ctx

    journal.append({
        "type": "session_start",
        "ts": _iso(session.started_at),
        "games_found": len(session.games),
        "event_tickers": [ctx.event_ticker for ctx in session.games.values()],
        "config": {
            "poll_interval_sec": POLL_INTERVAL_SEC,
            "max_run_sec": args.max_run_sec,
            "idle_exit_sec": args.idle_exit_sec,
        },
    })

    try:
        _poll_loop(session)
    finally:
        # Final end-of-game sweep for any still-open positions (e.g. on SIGINT).
        for ctx in session.games.values():
            if session.manager.active_count() == 0:
                break
            final_state = fetch_market_state(ctx.fav_ticker) if ctx.fav_ticker else None
            final_price = (
                _coerce_price(final_state.get("yes_bid_dollars"))
                if final_state else None
            )
            if final_price is not None:
                action = session.manager.end_of_game(
                    ctx.game_id, final_price, time.time(),
                )
                if action is not None:
                    journal.append(_trade_record(action))

        summary = session.manager.summary()
        summary["runtime_sec"] = time.time() - session.started_at
        summary["interrupted"] = session._interrupted
        journal.append({
            "type": "session_end",
            "ts": _iso(time.time()),
            "summary": summary,
        })
        log(f"Session summary: {summary}")
        journal.close()

    return 0


def _poll_loop(session: Session) -> None:
    args = session.args
    cycle = 0
    last_cycle_start: float | None = None
    while True:
        if session._interrupted:
            log("Shutdown flagged — exiting poll loop.")
            return
        now = time.time()

        # Gap detector — catches macOS App Nap / suspend where the loop
        # slept through the poll interval. Surfaces once the loop
        # resumes so missed ticks are visible in stdout.
        if last_cycle_start is not None:
            gap = now - last_cycle_start
            if gap > CYCLE_GAP_WARN_SEC:
                log(
                    f"WARN: cycle gap {gap:.0f}s exceeds "
                    f"{CYCLE_GAP_WARN_SEC}s threshold "
                    f"(expected ~{POLL_INTERVAL_SEC}s). Process may have "
                    "been suspended (App Nap, clamshell sleep, network "
                    "hang). Ticks for the gap window are missing."
                )
        last_cycle_start = now
        cycle += 1

        if now - session.started_at > args.max_run_sec:
            log(
                f"max_run_sec {args.max_run_sec}s reached "
                f"({now - session.started_at:.0f}s elapsed). Exiting."
            )
            return

        active_any = False
        ticked = 0
        for ctx in session.games.values():
            if ctx.finished:
                continue
            active_any = True
            ticked += 1
            _tick_one_game(session, ctx, now)

        if not active_any:
            log("All games finished. Exiting.")
            return

        if now - session.last_active_at > args.idle_exit_sec:
            log(
                f"idle_exit_sec {args.idle_exit_sec}s exceeded — "
                "no active market activity. Exiting."
            )
            return

        # Heartbeat — one line per cycle so the terminal shows the
        # engine is alive without tailing the journal. Includes position
        # state + entries-to-date for at-a-glance session health.
        mgr_summary = session.manager.summary()
        log(
            f"cycle {cycle}: {ticked} games polled, "
            f"{mgr_summary['open_positions']} positions open, "
            f"{mgr_summary['entries']} entries / "
            f"{mgr_summary['closes']} closes / "
            f"${mgr_summary['total_pnl']:+.2f} net P&L so far"
        )

        time.sleep(POLL_INTERVAL_SEC)


def _tick_one_game(session: Session, ctx: GameContext, now: float) -> None:
    if ctx.fav_ticker is None:
        resolve_favorite(ctx, now)
        if ctx.fav_ticker is None:
            return  # still waiting for tip

    fav_state = fetch_market_state(ctx.fav_ticker)
    if fav_state is None:
        return

    fav_bid = _coerce_price(fav_state.get("yes_bid_dollars"))
    market_status = fav_state.get("status")

    if _is_finished_status(market_status):
        action = session.manager.end_of_game(
            ctx.game_id,
            fav_bid if fav_bid is not None else 0.0,
            now,
        )
        if action is not None:
            ctx.detector.notify_exit()
            session.journal.append(_trade_record(action))
        ctx.finished = True
        session.journal.append({
            "type": "game_finished",
            "ts": _iso(now),
            "game_id": ctx.game_id,
            "event_ticker": ctx.event_ticker,
            "status": market_status,
            "final_fav_bid": fav_bid,
        })
        session.last_active_at = now
        return

    if fav_bid is None or fav_bid <= SETTLE_THRESHOLD:
        # Price below settle threshold — could be pre-tip penny
        # grid OR a blowout where the favorite has collapsed.
        # Either way, no trading signals to emit. But the market
        # IS responding, so keep the idle timer alive to prevent
        # premature exit during blowouts (see 2026-04-24 DEN-MIN
        # incident: engine exited mid-Q4 because the favorite
        # sat at $0.02 for 15 minutes).
        session.last_active_at = now
        return

    signal = ctx.detector.update(now, fav_bid)
    action = session.manager.evaluate(
        ctx.game_id, ctx.fav_ticker, signal, fav_bid, now,
    )

    if action.action == "open":
        ctx.detector.notify_entry()
        session.journal.append(_trade_record(action))
    elif action.action in (
        "close_target", "close_stop", "close_ratchet_stop", "close_eod",
    ):
        ctx.detector.notify_exit()
        session.journal.append(_trade_record(action))

    session.journal.append(_tick_record(ctx, fav_state, signal, session.manager, now))
    session.last_active_at = now


# ---- Entry point -------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-run-sec", type=int, default=86400,
        help="Maximum runtime in seconds (default: 24h).",
    )
    parser.add_argument(
        "--idle-exit-sec", type=int, default=900,
        help="Exit after N seconds of no active-game activity "
             "(default: 900 = 15 min). Same semantics as the logger.",
    )
    parser.add_argument(
        "--ratchet", type=float, default=0.08,
        help="Breakeven ratchet trigger: once fav price rises this "
             "much above entry, stop moves to entry + $0.01. Default: "
             "0.08 (validated, +$706/yr incremental on 404-game "
             "Kalshi dataset). Pass 0 to disable.",
    )
    args = parser.parse_args(argv)
    return run_session(args)


if __name__ == "__main__":
    sys.exit(main())
