"""S4A stop-loss execution reality investigation.

Characterizes the real-world execution dynamics of the $0.40 stop-loss
on Kalshi's binary orderbook. Kalshi has no native stop-loss order
type; the strategy must emulate stops with limit orders. This script
quantifies gap-through risk, dwell time at the stop level, descent
velocity, raw-trade-tape liquidity, and EV impact under four
execution scenarios including the NO-side resting order strategy.

Uses the same S4A simulation as
`analysis.strategy4_dip_recovery::simulate_s4a`, so stop events line
up trade-for-trade with the engine replay and Part 8 Path B.

Run:
    python -m analysis.strategy4_stop_execution
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    CONTRACT_SIZE,
    COMP_FRACTION,
    REG_SEASON_GAMES,
    S4AConfig,
    S4ATrade,
    _precompute_trailing_max,
    load_kalshi_games_all_spreads,
    maker_fee,
    simulate_s4a,
    summarize_s4a,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
MATCHED_CSV = PAIRED_DIR / "matched_games.csv"
MASTER_CSV = REPO_ROOT / "data" / "nba_master_2025_26.csv"
CACHE_DIR = REPO_ROOT / "data" / "stop_execution_cache"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy4_stop_execution.md"
)

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
REQUEST_TIMEOUT_SEC = 15
KALSHI_SLEEP_SEC = 0.25

CFG = S4AConfig(
    lookback_sec=180, dip_depth=0.08,
    entry_lo=0.50, entry_hi=0.75,
    exit_target=0.90, stop_loss=0.40,
)

TICKER_RE = re.compile(r"(KXNBAGAME-\d{2}[A-Z]{3}\d{2}[A-Z]{6})")


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


def taker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.07 * contracts * price * (1.0 - price) * 100) / 100


# ---- Metadata helpers --------------------------------------------------

def load_matched() -> pd.DataFrame:
    df = pd.read_csv(MATCHED_CSV)
    df["abs_spread"] = pd.to_numeric(df["abs_spread"], errors="coerce")
    return df


def load_game_labels() -> dict[str, str]:
    master = pd.read_csv(MASTER_CSV)
    out: dict[str, str] = {}
    for r in master.itertuples():
        try:
            gid = str(int(r.game_id))
        except (ValueError, TypeError):
            continue
        away = getattr(r, "away_team_abbrev", None)
        home = getattr(r, "home_team_abbrev", None)
        if away and home:
            out[gid] = f"{away} @ {home}"
    return out


def infer_fav_side_ticker(
    game: dict, data: dict | None = None,
) -> str | None:
    """Return the favorite-side market ticker for an event.

    Uses the trade-tape cache if available (preferred) or falls back to
    loading it from disk. Median yes_price is computed across ALL
    trades for each ticker (not a head slice — the cache layout happens
    to group trades by ticker, so a head slice sees only one side).
    """
    event_ticker = game["ticker"]
    if data is None:
        trades_path = PAIRED_DIR / f"{event_ticker}_trades.json"
        if not trades_path.exists():
            return None
        try:
            with trades_path.open() as f:
                data = json.load(f)
        except (ValueError, OSError):
            return None
    tickers: list[str] = data.get("tickers") or []
    if len(tickers) != 2:
        return None
    all_trades = data.get("trades") or []
    price_by_ticker: dict[str, list[float]] = {tk: [] for tk in tickers}
    for t in all_trades:
        tk = t.get("ticker")
        if tk not in price_by_ticker:
            continue
        yp = t.get("yes_price_dollars")
        if not yp:
            continue
        try:
            price_by_ticker[tk].append(float(yp))
        except (TypeError, ValueError):
            continue
    populated = {
        tk: ps for tk, ps in price_by_ticker.items() if ps
    }
    if len(populated) < 2:
        return None
    medians = {tk: float(np.median(ps)) for tk, ps in populated.items()}
    return max(medians, key=lambda k: medians[k])


# ---- Part 1: Stop event identification ---------------------------------

@dataclass
class StopEvent:
    ticker: str
    espn_game_id: str | None
    label: str
    abs_spread: float
    entry_price: float
    entry_idx: int
    entry_gse: float | None
    stop_idx: int
    stop_gse: float | None
    pre_stop_vwap: float | None   # last bin > 0.40 before stop
    stop_vwap: float              # first bin <= 0.40
    is_reentry: bool
    net_pnl: float
    # Populated below
    gap_size: float = 0.0
    gap_category: str = "unknown"   # clean / moderate / severe
    dwell_38_42_bins: int = 0
    dwell_36_44_bins: int = 0
    price_60s_before: float | None = None
    price_120s_before: float | None = None
    price_300s_before: float | None = None
    descent_per_sec: float | None = None
    descent_category: str = "unknown"   # gradual / rapid / flash_crash
    stop_wallclock: datetime | None = None


def identify_stops(
    games: list[dict],
    precomp_max: dict[tuple[str, int], np.ndarray],
    labels: dict[str, str],
) -> tuple[list[StopEvent], dict, int, int]:
    trades = simulate_s4a(games, CFG, precomp_max)
    summary = summarize_s4a(trades, len(games))
    games_by_ticker = {g["ticker"]: g for g in games}

    stop_events: list[StopEvent] = []
    for t in trades:
        if t.exit_type != "stop":
            continue
        g = games_by_ticker[t.ticker]
        ts_df = g["ts"]
        prices = ts_df["fav_kalshi_vwap"].values
        gse_series = ts_df["game_seconds_elapsed"]
        stop_idx = t.exit_idx
        stop_vwap = float(prices[stop_idx])
        pre_stop_vwap = (
            float(prices[stop_idx - 1]) if stop_idx > 0 else None
        )
        entry_gse = (
            float(gse_series.iloc[t.entry_idx])
            if 0 <= t.entry_idx < len(gse_series)
            and not pd.isna(gse_series.iloc[t.entry_idx]) else None
        )
        stop_gse = (
            float(gse_series.iloc[stop_idx])
            if 0 <= stop_idx < len(gse_series)
            and not pd.isna(gse_series.iloc[stop_idx]) else None
        )
        ev = StopEvent(
            ticker=t.ticker,
            espn_game_id=g.get("espn_game_id"),
            label=labels.get(str(g.get("espn_game_id", "")), "?"),
            abs_spread=t.abs_spread,
            entry_price=t.entry_price,
            entry_idx=t.entry_idx,
            entry_gse=entry_gse,
            stop_idx=stop_idx,
            stop_gse=stop_gse,
            pre_stop_vwap=pre_stop_vwap,
            stop_vwap=stop_vwap,
            is_reentry=t.is_reentry,
            net_pnl=t.net_pnl,
        )
        stop_events.append(ev)
    return stop_events, summary, len(trades), sum(
        1 for t in trades if t.exit_type == "stop"
    )


# ---- Part 2: Gap-through classification -------------------------------

GAP_BINS: list[tuple[str, float, float]] = [
    ("$0.00–0.02", 0.00, 0.02),
    ("$0.02–0.04", 0.02, 0.04),
    ("$0.04–0.06", 0.04, 0.06),
    ("$0.06–0.08", 0.06, 0.08),
    ("$0.08–0.10", 0.08, 0.10),
    ("$0.10+", 0.10, float("inf")),
]


def classify_gap(sv: float) -> str:
    """Clean / moderate / severe based on stop_vwap value."""
    if 0.38 <= sv <= 0.42:
        return "clean"
    if 0.34 <= sv < 0.38:
        return "moderate"
    if sv < 0.34:
        return "severe"
    # stop_vwap > 0.42 shouldn't happen by S4A's definition, but guard.
    return "clean"


def annotate_gaps(stops: list[StopEvent]) -> None:
    for ev in stops:
        pre = ev.pre_stop_vwap if ev.pre_stop_vwap is not None else ev.stop_vwap
        ev.gap_size = max(0.0, pre - ev.stop_vwap)
        ev.gap_category = classify_gap(ev.stop_vwap)


# ---- Part 3: Dwell time ------------------------------------------------

def compute_dwell(
    stops: list[StopEvent], games_by_ticker: dict[str, dict],
) -> None:
    """For each stop, count consecutive bins within ±$0.02 and ±$0.04 of
    $0.40 around the stop event."""
    for ev in stops:
        ts_df = games_by_ticker[ev.ticker]["ts"]
        prices = ts_df["fav_kalshi_vwap"].values
        n = len(prices)
        # Inner: $0.38–$0.42. Walk outward from stop_idx until price leaves.
        inner_count = 0
        outer_count = 0
        for i in range(ev.stop_idx, n):
            p = float(prices[i])
            if 0.38 <= p <= 0.42:
                inner_count += 1
            else:
                break
        # Also look backward from stop-1 for approach bins.
        outer_back = 0
        for i in range(ev.stop_idx - 1, -1, -1):
            p = float(prices[i])
            if 0.36 <= p <= 0.44:
                outer_back += 1
            else:
                break
        outer_count = outer_back + inner_count
        ev.dwell_38_42_bins = inner_count
        ev.dwell_36_44_bins = outer_count


# ---- Part 4: Descent velocity ------------------------------------------

def annotate_descent(
    stops: list[StopEvent], games_by_ticker: dict[str, dict],
) -> None:
    for ev in stops:
        ts_df = games_by_ticker[ev.ticker]["ts"]
        prices = ts_df["fav_kalshi_vwap"].values
        n = len(prices)

        def _safe(i: int) -> float | None:
            return float(prices[i]) if 0 <= i < n else None

        # 2 bins = 60s; 4 bins = 120s; 10 bins = 300s
        p60 = _safe(ev.stop_idx - 2)
        p120 = _safe(ev.stop_idx - 4)
        p300 = _safe(ev.stop_idx - 10)
        ev.price_60s_before = p60
        ev.price_120s_before = p120
        ev.price_300s_before = p300
        if p300 is not None:
            ev.descent_per_sec = (p300 - ev.stop_vwap) / 300.0

        # Classification per prompt:
        # Gradual:  price_120s <= 0.48
        # Rapid:    price_120s > 0.48 AND price_60s <= 0.45
        # Flash:    price_60s > 0.45
        if p60 is not None and p60 > 0.45:
            ev.descent_category = "flash_crash"
        elif p120 is not None and p120 > 0.48 and (p60 or 1.0) <= 0.45:
            ev.descent_category = "rapid"
        elif p120 is not None and p120 <= 0.48:
            ev.descent_category = "gradual"
        else:
            # Fallback: use whatever data we have.
            if p120 is not None and p120 > 0.48:
                ev.descent_category = "rapid"
            else:
                ev.descent_category = "gradual"


# ---- Part 5: Raw trade tape analysis ----------------------------------

def _fmt_dt(s: str) -> datetime | None:
    if not s:
        return None
    try:
        # Kalshi returns RFC3339 / ISO 8601 with Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _trades_path_for(ticker: str) -> Path:
    """Local cache path for the event's trade tape (from paired pipeline)."""
    return PAIRED_DIR / f"{ticker}_trades.json"


def _fresh_cache_path(ticker: str) -> Path:
    """Separate cache for trades fetched specifically by this script."""
    return CACHE_DIR / f"{ticker}.json"


def fetch_trade_tape(
    event_ticker: str, use_cached: bool = True,
) -> dict | None:
    """Load trade tape for an event. Prefer paired-pipeline cache, fall
    back to stop-execution cache, fall back to API fetch. Returns dict
    with keys: event_ticker, tickers, trades (list of dicts)."""
    # Prefer paired-pipeline cache (richer, already disk-resident).
    p = _trades_path_for(event_ticker)
    if p.exists():
        try:
            with p.open() as f:
                return json.load(f)
        except (ValueError, OSError):
            pass

    # Local script cache
    q = _fresh_cache_path(event_ticker)
    if use_cached and q.exists():
        try:
            with q.open() as f:
                return json.load(f)
        except (ValueError, OSError):
            pass

    # API fetch
    try:
        markets_url = f"{KALSHI_BASE}/markets"
        r = requests.get(
            markets_url,
            params={"event_ticker": event_ticker, "limit": 50},
            timeout=REQUEST_TIMEOUT_SEC,
        )
        r.raise_for_status()
        markets = r.json().get("markets", []) or []
        tickers = sorted({m["ticker"] for m in markets if m.get("ticker")})
        if not tickers:
            return None
        all_trades: list[dict] = []
        for tk in tickers:
            cursor: str | None = None
            while True:
                params: dict = {"ticker": tk, "limit": 1000}
                if cursor:
                    params["cursor"] = cursor
                rr = requests.get(
                    f"{KALSHI_BASE}/markets/trades",
                    params=params, timeout=REQUEST_TIMEOUT_SEC,
                )
                rr.raise_for_status()
                payload = rr.json()
                trades = payload.get("trades") or []
                all_trades.extend(trades)
                cursor = payload.get("cursor")
                if not cursor or not trades:
                    break
                time.sleep(KALSHI_SLEEP_SEC)
        if not all_trades:
            return None
        data = {
            "event_ticker": event_ticker,
            "tickers": tickers,
            "trades": all_trades,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with q.open("w") as f:
            json.dump(data, f)
        return data
    except requests.RequestException as e:
        log(f"  trade tape fetch failed for {event_ticker}: {e}")
        return None


@dataclass
class RawTradeAnalysis:
    event_ticker: str
    fav_ticker: str | None
    total_trades_in_window: int = 0
    trades_at_stop_level: int = 0
    contracts_at_stop_level: float = 0.0
    last_trade_above_040: dict | None = None
    first_trade_at_or_below_040: dict | None = None
    gap_seconds: float | None = None
    taker_side_counts_in_window: dict[str, int] = field(default_factory=dict)
    taker_contracts_in_window: dict[str, float] = field(default_factory=dict)
    achievable_stop_price: float | None = None
    achievable_contracts: float = 0.0


def analyze_raw_trades(
    ev: StopEvent, data: dict,
    fav_side_ticker: str | None,
    window_sec: int = 300,
) -> RawTradeAnalysis | None:
    """Analyze raw trades around the stop event.

    Window = ±`window_sec` around the stop bin's start time. If we
    don't have a wallclock for the stop bin (stop_gse is None), we
    can't align and return None.
    """
    rta = RawTradeAnalysis(
        event_ticker=ev.ticker, fav_ticker=fav_side_ticker,
    )
    if fav_side_ticker is None:
        return None
    # Derive the stop wallclock: we need the game's wallclock → gse
    # mapping. We approximate by using the bucket_start_utc column in the
    # timeseries CSV for the stop bin. Load the CSV directly.
    ts_csv = PAIRED_DIR / f"{ev.ticker}_timeseries.csv"
    if not ts_csv.exists():
        return None
    ts_df = pd.read_csv(ts_csv)
    if "bucket_start_utc" not in ts_df.columns:
        return None
    try:
        stop_wc_str = str(ts_df["bucket_start_utc"].iloc[ev.stop_idx])
    except (IndexError, KeyError):
        return None
    try:
        stop_wc = datetime.fromisoformat(stop_wc_str.replace("Z", "+00:00"))
    except ValueError:
        return None
    ev.stop_wallclock = stop_wc
    win_start = stop_wc - timedelta(seconds=window_sec)
    win_end = stop_wc + timedelta(seconds=window_sec)

    trades = data.get("trades") or []
    in_window: list[tuple[datetime, dict]] = []
    for t in trades:
        if t.get("ticker") != fav_side_ticker:
            continue
        dt = _fmt_dt(t.get("created_time"))
        if dt is None:
            continue
        if win_start <= dt <= win_end:
            in_window.append((dt, t))
    if not in_window:
        return rta
    in_window.sort(key=lambda x: x[0])
    rta.total_trades_in_window = len(in_window)

    # 5a — volume at stop level ($0.38–$0.42 YES inclusive)
    for dt, t in in_window:
        try:
            yp = float(t.get("yes_price_dollars", "0") or 0)
            cnt = float(t.get("count_fp", "0") or 0)
        except (TypeError, ValueError):
            continue
        if 0.38 <= yp <= 0.42:
            rta.trades_at_stop_level += 1
            rta.contracts_at_stop_level += cnt

    # 5b — trade-level gap at $0.40 threshold
    for dt, t in in_window:
        try:
            yp = float(t.get("yes_price_dollars", "0") or 0)
        except (TypeError, ValueError):
            continue
        if yp > 0.40:
            rta.last_trade_above_040 = {"ts": dt.isoformat(), **t}
        elif yp <= 0.40 and rta.first_trade_at_or_below_040 is None:
            rta.first_trade_at_or_below_040 = {"ts": dt.isoformat(), **t}
            if rta.last_trade_above_040 is not None:
                last_dt = _fmt_dt(rta.last_trade_above_040["ts"])
                if last_dt:
                    rta.gap_seconds = (dt - last_dt).total_seconds()
            # Keep scanning — don't break, we want later aggregates.

    # 5c — taker side flow within a tighter ±60s window around the
    # threshold crossing (if we have one) to characterize the moment
    # of the break.
    if rta.first_trade_at_or_below_040 is not None:
        cross_dt = _fmt_dt(rta.first_trade_at_or_below_040["ts"])
    else:
        cross_dt = stop_wc
    narrow_start = cross_dt - timedelta(seconds=60) if cross_dt else win_start
    narrow_end = cross_dt + timedelta(seconds=60) if cross_dt else win_end
    side_counts: Counter = Counter()
    side_contracts: Counter = Counter()
    for dt, t in in_window:
        if not (narrow_start <= dt <= narrow_end):
            continue
        side = t.get("taker_side") or "unknown"
        try:
            cnt = float(t.get("count_fp", "0") or 0)
        except (TypeError, ValueError):
            cnt = 0
        side_counts[side] += 1
        side_contracts[side] += cnt
    rta.taker_side_counts_in_window = dict(side_counts)
    rta.taker_contracts_in_window = dict(side_contracts)

    # 5d — achievable stop price for a 100-contract taker. Walk from
    # the threshold-crossing timestamp forward. The taker SELLS YES
    # (lifts YES bids / fills resting NO buys). We approximate the
    # achievable fill sequence by using trades at yes_price <= 0.40
    # in time order from the crossing.
    need = float(CONTRACT_SIZE)
    cum_cost = 0.0
    cum_filled = 0.0
    if cross_dt is not None:
        for dt, t in in_window:
            if dt < cross_dt:
                continue
            try:
                yp = float(t.get("yes_price_dollars", "0") or 0)
                cnt = float(t.get("count_fp", "0") or 0)
            except (TypeError, ValueError):
                continue
            if yp > 0.40:
                continue
            take = min(cnt, need - cum_filled)
            if take <= 0:
                continue
            cum_cost += take * yp
            cum_filled += take
            if cum_filled >= need:
                break
        if cum_filled > 0:
            rta.achievable_stop_price = cum_cost / cum_filled
            rta.achievable_contracts = cum_filled
    return rta


# ---- Part 6: EV impact under four scenarios ---------------------------

def recompute_pnl_from_stop_price(
    entry_price: float, stop_price: float, fee_fn,
) -> float:
    entry_fee = fee_fn(CONTRACT_SIZE, entry_price)
    exit_fee = fee_fn(CONTRACT_SIZE, stop_price)
    return (stop_price - entry_price) * CONTRACT_SIZE - entry_fee - exit_fee


def scenario_totals(
    all_trades: list[S4ATrade],
    stops: list[StopEvent],
    raw_by_event: dict[str, RawTradeAnalysis],
    n_games: int,
) -> dict[str, dict]:
    """Compute annual EV under Scenarios A-D.

    Non-stop trades (targets + EOD resolutions) use their existing
    net_pnl unchanged. Stops are recomputed per scenario.
    """
    # Build a lookup by (ticker, entry_idx) to substitute stop PnL.
    non_stop_pnl = sum(
        t.net_pnl for t in all_trades if t.exit_type != "stop"
    )
    n_trades = len(all_trades)

    results: dict[str, dict] = {}

    # --- Scenario A: baseline (current summarize_s4a numbers) ---
    stop_pnl_A = sum(ev.net_pnl for ev in stops)
    results["A"] = {
        "label": "Baseline (stops fill at $0.40 maker)",
        "stop_pnl": stop_pnl_A,
        "avg_slippage": 0.0,
        "avg_stop_price": 0.40,
        "fill_rate": 1.0,
    }

    # --- Scenario B: maker NO-side resting with gap-through fallback ---
    # Clean cross: fills at $0.40 maker. Moderate: 50% fill rate —
    # fills at $0.40 maker; non-fills fall back to taker at stop_vwap.
    # Severe: 0% fill; all take at stop_vwap.
    rng = np.random.default_rng(42)
    stop_pnl_B = 0.0
    slippages_B = []
    fills_B = 0
    for ev in stops:
        fallback_price = ev.stop_vwap
        if ev.gap_category == "clean":
            filled = True
            price = CFG.stop_loss
            fee_fn = maker_fee
        elif ev.gap_category == "moderate":
            filled = rng.random() < 0.5
            if filled:
                price = CFG.stop_loss
                fee_fn = maker_fee
            else:
                price = fallback_price
                fee_fn = taker_fee
        else:  # severe
            filled = False
            price = fallback_price
            fee_fn = taker_fee
        if filled:
            fills_B += 1
        pnl = recompute_pnl_from_stop_price(
            ev.entry_price, price, fee_fn,
        )
        stop_pnl_B += pnl
        slippages_B.append(CFG.stop_loss - price)
    results["B"] = {
        "label": "Maker NO-side resting (+ taker fallback on fail)",
        "stop_pnl": stop_pnl_B,
        "avg_slippage": float(np.mean(slippages_B)) if slippages_B else 0.0,
        "avg_stop_price": float(np.mean([
            CFG.stop_loss - s for s in slippages_B
        ])) if slippages_B else 0.40,
        "fill_rate": fills_B / len(stops) if stops else 0.0,
    }

    # --- Scenario C: taker stop (worst case) ---
    stop_pnl_C = 0.0
    slippages_C = []
    for ev in stops:
        price = ev.stop_vwap
        pnl = recompute_pnl_from_stop_price(
            ev.entry_price, price, taker_fee,
        )
        stop_pnl_C += pnl
        slippages_C.append(CFG.stop_loss - price)
    results["C"] = {
        "label": "Taker stop at observed stop_vwap",
        "stop_pnl": stop_pnl_C,
        "avg_slippage": float(np.mean(slippages_C)) if slippages_C else 0.0,
        "avg_stop_price": float(np.mean([
            CFG.stop_loss - s for s in slippages_C
        ])) if slippages_C else 0.40,
        "fill_rate": 0.0,
    }

    # --- Scenario D: hybrid — fill-within-60s from dwell data ---
    # Use dwell_38_42_bins >= 2 (60s or more in band) as proxy for
    # "resting order fills within 60s". Shorter dwell → fallback to
    # taker at stop_vwap.
    stop_pnl_D = 0.0
    slippages_D = []
    fills_D = 0
    for ev in stops:
        if ev.dwell_38_42_bins >= 2:
            price = CFG.stop_loss
            fee_fn = maker_fee
            fills_D += 1
        else:
            price = ev.stop_vwap
            fee_fn = taker_fee
        pnl = recompute_pnl_from_stop_price(
            ev.entry_price, price, fee_fn,
        )
        stop_pnl_D += pnl
        slippages_D.append(CFG.stop_loss - price)
    results["D"] = {
        "label": "Hybrid: resting + 60s cancel fallback",
        "stop_pnl": stop_pnl_D,
        "avg_slippage": float(np.mean(slippages_D)) if slippages_D else 0.0,
        "avg_stop_price": float(np.mean([
            CFG.stop_loss - s for s in slippages_D
        ])) if slippages_D else 0.40,
        "fill_rate": fills_D / len(stops) if stops else 0.0,
    }

    # Annualize each scenario
    for key in ("A", "B", "C", "D"):
        total_pnl = non_stop_pnl + results[key]["stop_pnl"]
        mean_pnl = total_pnl / n_trades if n_trades else 0.0
        entries_per_game = n_trades / n_games if n_games else 0.0
        annual_ev = (
            mean_pnl * entries_per_game * REG_SEASON_GAMES * COMP_FRACTION
        )
        results[key]["total_pnl"] = total_pnl
        results[key]["mean_pnl"] = mean_pnl
        results[key]["annual_ev"] = annual_ev

    return results


def break_even_stop_price(
    all_trades: list[S4ATrade], n_games: int,
) -> float | None:
    """Solve for the uniform taker-exit price that makes total S4A
    annual EV = 0. Non-stop trades keep their P&L. Binary search
    over stop prices $0.30 to $0.42 (below that EV is definitely
    negative; above that it approaches baseline)."""
    non_stop_pnl = sum(
        t.net_pnl for t in all_trades if t.exit_type != "stop"
    )
    stops = [t for t in all_trades if t.exit_type == "stop"]
    n_trades = len(all_trades)
    if not stops or n_trades == 0 or n_games == 0:
        return None

    def annual_at(price: float) -> float:
        stop_pnl = sum(
            recompute_pnl_from_stop_price(t.entry_price, price, taker_fee)
            for t in stops
        )
        total = non_stop_pnl + stop_pnl
        mean_pnl = total / n_trades
        eper = n_trades / n_games
        return mean_pnl * eper * REG_SEASON_GAMES * COMP_FRACTION

    lo, hi = 0.00, 0.42
    if annual_at(hi) <= 0:
        return hi
    if annual_at(lo) >= 0:
        return lo
    # Binary search (annual_at is monotonic increasing in price)
    for _ in range(60):
        mid = (lo + hi) / 2
        if annual_at(mid) >= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# ---- Part 7: Target exit reality check ---------------------------------

def analyze_targets(
    all_trades: list[S4ATrade],
    games_by_ticker: dict[str, dict],
) -> dict:
    targets = [t for t in all_trades if t.exit_type == "target"]
    if not targets:
        return {"n": 0}
    exit_prices = [t.exit_price for t in targets]
    # "gap-through on targets": how many have exit_price > 0.92?
    jumpers = [t for t in targets if t.exit_price > 0.92]
    pre_target_gaps: list[float] = []
    for t in targets:
        ts_df = games_by_ticker[t.ticker]["ts"]
        prices = ts_df["fav_kalshi_vwap"].values
        if t.exit_idx > 0:
            pre = float(prices[t.exit_idx - 1])
            pre_target_gaps.append(t.exit_price - pre)
    return {
        "n": len(targets),
        "exit_price_median": float(np.median(exit_prices)),
        "exit_price_p25": float(np.quantile(exit_prices, 0.25)),
        "exit_price_p75": float(np.quantile(exit_prices, 0.75)),
        "exit_price_max": float(np.max(exit_prices)),
        "n_above_92": len(jumpers),
        "pct_above_92": 100.0 * len(jumpers) / len(targets),
        "pre_target_gap_median": (
            float(np.median(pre_target_gaps)) if pre_target_gaps else 0.0
        ),
    }


# ---- Report rendering --------------------------------------------------

def pct(n: int, d: int) -> str:
    if d == 0:
        return "0.0%"
    return f"{100.0 * n / d:.1f}%"


def histogram_counts(
    values: list[float], bins: list[tuple[str, float, float]],
) -> list[tuple[str, int, float]]:
    arr = np.array(values)
    n = len(arr)
    out: list[tuple[str, int, float]] = []
    for lab, lo, hi in bins:
        mask = (arr >= lo) & (arr < hi)
        c = int(mask.sum())
        out.append((lab, c, 100.0 * c / n if n else 0.0))
    return out


def build_report(
    n_games: int, n_trades: int, n_stops: int,
    baseline_summary: dict,
    stops: list[StopEvent],
    raw_by_event: dict[str, RawTradeAnalysis],
    scenarios: dict[str, dict],
    break_even_price: float | None,
    target_stats: dict,
) -> str:
    md: list[str] = []
    md.append("# Strategy 4 — Stop-Loss Execution Reality\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Investigates the real-world execution dynamics of S4A's "
        "$0.40 stop-loss on Kalshi's binary orderbook. The $0.40 "
        "stop is the strategy's most sensitive parameter, and "
        "Kalshi has no native stop-loss order type. Analyzes "
        "gap-through risk, dwell time, descent velocity, and EV "
        "impact under four execution scenarios including the "
        "NO-side resting order strategy.\n"
    )
    md.append(
        f"\nDataset: {n_games} games from the Kalshi-confirmed "
        "paired timeseries. Raw trade tape consumed from the paired "
        "pipeline's existing on-disk cache where present; new "
        "API fetches cached under `data/stop_execution_cache/`.\n"
    )

    # Part 1
    md.append("\n## Part 1 — Stop event identification\n")
    md.append(
        f"- Total S4A entries: **{n_trades}**\n"
        f"- Stop-loss events: **{n_stops}** "
        f"({pct(n_stops, n_trades)} of entries — compare "
        "STRATEGY4_SPEC.md's ~47% anchor)\n"
        f"- Non-stop exits (target / EOD): "
        f"{n_trades - n_stops}\n"
    )

    # Part 2
    gap_counts = Counter(ev.gap_category for ev in stops)
    md.append("\n## Part 2 — Gap-through analysis (30s VWAP)\n")
    md.append(
        "| Category | Definition | Count | % |\n"
        "|---|---|---:|---:|\n"
        f"| Clean cross | stop_vwap ∈ [$0.38, $0.42] | "
        f"{gap_counts.get('clean', 0)} | "
        f"{pct(gap_counts.get('clean', 0), n_stops)} |\n"
        f"| Moderate gap | stop_vwap ∈ [$0.34, $0.38) | "
        f"{gap_counts.get('moderate', 0)} | "
        f"{pct(gap_counts.get('moderate', 0), n_stops)} |\n"
        f"| Severe gap | stop_vwap < $0.34 | "
        f"{gap_counts.get('severe', 0)} | "
        f"{pct(gap_counts.get('severe', 0), n_stops)} |\n"
    )
    gap_sizes = [ev.gap_size for ev in stops]
    if gap_sizes:
        md.append(
            f"\nGap-size stats (pre_stop_vwap − stop_vwap): "
            f"p25 ${np.quantile(gap_sizes, 0.25):.3f}, "
            f"median ${np.median(gap_sizes):.3f}, "
            f"p75 ${np.quantile(gap_sizes, 0.75):.3f}, "
            f"max ${max(gap_sizes):.3f}.\n"
        )
    md.append(
        "\n### Gap-size histogram\n"
        "| Bucket | Count | % |\n|---|---:|---:|\n"
    )
    for lab, c, p in histogram_counts(gap_sizes, GAP_BINS):
        md.append(f"| {lab} | {c} | {p:.1f}% |\n")
    md.append("\n### 5 worst gap-throughs\n")
    md.append(
        "| Game | \\|Spread\\| | Entry | Pre-stop | Stop VWAP | Gap | Entry gse |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    worst = sorted(stops, key=lambda e: -e.gap_size)[:5]
    for ev in worst:
        md.append(
            f"| {ev.label} | {ev.abs_spread:.1f} | "
            f"${ev.entry_price:.3f} | "
            f"${(ev.pre_stop_vwap or 0):.3f} | "
            f"${ev.stop_vwap:.3f} | "
            f"${ev.gap_size:.3f} | "
            f"{int(ev.entry_gse) if ev.entry_gse is not None else '—'} |\n"
        )

    # Part 3
    md.append("\n## Part 3 — Dwell time near the stop level\n")
    inner_dwells = [ev.dwell_38_42_bins for ev in stops]
    outer_dwells = [ev.dwell_36_44_bins for ev in stops]
    md.append(
        f"- Median bins in $0.38–$0.42 at/after the stop: "
        f"**{int(np.median(inner_dwells))} bins "
        f"({int(np.median(inner_dwells)) * BUCKET_SEC}s)**\n"
        f"- Median bins in $0.36–$0.44 approach+through window: "
        f"**{int(np.median(outer_dwells))} bins "
        f"({int(np.median(outer_dwells)) * BUCKET_SEC}s)**\n"
    )
    dwell_counts = Counter()
    for d in inner_dwells:
        if d == 0:
            dwell_counts["0 (instant gap)"] += 1
        elif d == 1:
            dwell_counts["1 bin (30s)"] += 1
        elif d == 2:
            dwell_counts["2 bins (60s)"] += 1
        else:
            dwell_counts["3+ bins (90s+)"] += 1
    md.append(
        "\n| Dwell at $0.38–$0.42 | Count | % |\n|---|---:|---:|\n"
    )
    for k in ("0 (instant gap)", "1 bin (30s)", "2 bins (60s)", "3+ bins (90s+)"):
        c = dwell_counts.get(k, 0)
        md.append(f"| {k} | {c} | {pct(c, n_stops)} |\n")

    # Part 4
    md.append("\n## Part 4 — Descent velocity\n")
    dcats = Counter(ev.descent_category for ev in stops)
    md.append(
        "| Category | Definition | Count | % |\n|---|---|---:|---:|\n"
        f"| Gradual | price 120s before ≤ $0.48 | "
        f"{dcats.get('gradual', 0)} | "
        f"{pct(dcats.get('gradual', 0), n_stops)} |\n"
        f"| Rapid | price 120s before > $0.48, 60s before ≤ $0.45 | "
        f"{dcats.get('rapid', 0)} | "
        f"{pct(dcats.get('rapid', 0), n_stops)} |\n"
        f"| Flash crash | price 60s before > $0.45 | "
        f"{dcats.get('flash_crash', 0)} | "
        f"{pct(dcats.get('flash_crash', 0), n_stops)} |\n"
    )
    rates = [
        ev.descent_per_sec for ev in stops
        if ev.descent_per_sec is not None
    ]
    if rates:
        md.append(
            f"\nDescent rate ($/sec, 300s window): "
            f"p25 {np.quantile(rates, 0.25):.5f}, "
            f"median {np.median(rates):.5f}, "
            f"p75 {np.quantile(rates, 0.75):.5f}.\n"
        )

    # Part 5
    md.append("\n## Part 5 — Raw trade tape analysis\n")
    avail = sum(1 for r in raw_by_event.values() if r is not None)
    md.append(
        f"Raw trades available for "
        f"**{avail}** of {n_stops} stop events "
        f"({pct(avail, n_stops)}).\n"
    )
    # 5a — volume at stop level
    valid = [
        r for r in raw_by_event.values()
        if r is not None and r.total_trades_in_window > 0
    ]
    if valid:
        vols = [r.contracts_at_stop_level for r in valid]
        cts = [r.trades_at_stop_level for r in valid]
        md.append(
            "\n### 5a — Volume at $0.38–$0.42 within ±5 min of stop\n"
            f"- Median trades at stop-level band: "
            f"{int(np.median(cts))} "
            f"(p25 {int(np.quantile(cts, 0.25))}, "
            f"p75 {int(np.quantile(cts, 0.75))})\n"
            f"- Median contracts at stop-level band: "
            f"{np.median(vols):.0f} "
            f"(p25 {np.quantile(vols, 0.25):.0f}, "
            f"p75 {np.quantile(vols, 0.75):.0f})\n"
        )
        # 5b — gap analysis
        gaps = [
            r.gap_seconds for r in valid
            if r.gap_seconds is not None
        ]
        if gaps:
            md.append(
                "\n### 5b — Trade-level gap at $0.40 threshold\n"
                f"- Stops with an observable threshold-crossing "
                f"pair of trades: **{len(gaps)}** / {len(valid)}\n"
                f"- Gap seconds between last>$0.40 and first≤$0.40: "
                f"p25 {np.quantile(gaps, 0.25):.1f}s, "
                f"median {np.median(gaps):.1f}s, "
                f"p75 {np.quantile(gaps, 0.75):.1f}s, "
                f"max {max(gaps):.1f}s\n"
                f"- Crossings < 2s (genuine gap): "
                f"{sum(1 for g in gaps if g < 2)} "
                f"({pct(sum(1 for g in gaps if g < 2), len(gaps))})\n"
                f"- Crossings ≥ 5s (resting-order-friendly): "
                f"{sum(1 for g in gaps if g >= 5)} "
                f"({pct(sum(1 for g in gaps if g >= 5), len(gaps))})\n"
            )
        # 5c — taker side flow
        all_side_counts: Counter = Counter()
        all_side_contracts: Counter = Counter()
        for r in valid:
            for k, v in r.taker_side_counts_in_window.items():
                all_side_counts[k] += v
            for k, v in r.taker_contracts_in_window.items():
                all_side_contracts[k] += v
        md.append(
            "\n### 5c — Taker-side flow within ±60s of threshold crossing\n"
            "Aggregated across all stop events with raw data. "
            "`taker_side` = side that aggressed (hit a resting order). "
            "A YES price falling through $0.40 typically coincides with "
            "YES sellers lifting NO asks — in Kalshi's encoding that "
            "shows as **NO-side takers** (NO buyers crossing the book).\n\n"
            "| taker_side | Trades | Contracts | Share (contracts) |\n"
            "|---|---:|---:|---:|\n"
        )
        tot_contracts = sum(all_side_contracts.values()) or 1.0
        for side in ("yes", "no", "unknown"):
            c = all_side_counts.get(side, 0)
            v = all_side_contracts.get(side, 0.0)
            md.append(
                f"| {side} | {c} | {int(v):,} | "
                f"{100.0 * v / tot_contracts:.1f}% |\n"
            )
        md.append(
            "\n**Interpretation for the NO-side resting order strategy:** "
            "a resting NO buy at $0.60 fills when someone sells NO "
            "(= buys YES). That's trade flow where `taker_side == \"yes\"` "
            "(YES-buyer aggressor) OR passive NO asks being hit. The "
            "dominant taker side during a stop break tells us which "
            "direction the crossing is accumulating volume — if mostly "
            "NO-takers (NO buyers paying up to lift NO asks = YES "
            "sellers), our resting NO bid sits out of the way of the "
            "flow and needs the flow to reverse. If mostly YES-takers "
            "(YES buyers paying up), our resting NO bid is in the "
            "direct path of the opposite-side fills.\n"
        )
        # 5d — achievable price
        achievables = [
            r.achievable_stop_price for r in valid
            if r.achievable_stop_price is not None
        ]
        fills_full = sum(
            1 for r in valid
            if r.achievable_stop_price is not None
            and r.achievable_contracts >= CONTRACT_SIZE
        )
        if achievables:
            md.append(
                "\n### 5d — Achievable stop price for a 100-contract taker\n"
                f"Walk the trade tape from the threshold crossing forward; "
                "sum the first 100 contracts at yes_price ≤ $0.40.\n\n"
                f"- Stops where ≥ 100 contracts were available within the "
                f"±5 min window: **{fills_full}** / {len(valid)} "
                f"({pct(fills_full, len(valid))})\n"
                f"- Achievable VWAP across fills: p25 "
                f"${np.quantile(achievables, 0.25):.3f}, median "
                f"${np.median(achievables):.3f}, p75 "
                f"${np.quantile(achievables, 0.75):.3f}\n"
                f"- Average slippage vs $0.40: "
                f"${0.40 - np.mean(achievables):.3f}\n"
            )

    # Part 6
    md.append("\n## Part 6 — EV impact under execution scenarios\n")
    md.append(
        "Non-stop trades (targets + EOD) keep their baseline P&L; "
        "only stop P&L is recomputed per scenario. Annualization is "
        "pool-level across all 404 games (mean pool P&L × pool "
        "entries-per-game × 1230 × 0.445), which differs from Part 8 "
        "Path B's per-bucket-summed rollup of +$10,718 — the "
        "**relative** deltas vs Scenario A are the load-bearing "
        "numbers here, not the absolute baseline.\n\n"
        "| Scenario | Fill rate | Avg stop price | Avg slippage | "
        "Annual EV | Δ vs A |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    baseline_annual = scenarios["A"]["annual_ev"]
    for key in ("A", "B", "C", "D"):
        s = scenarios[key]
        delta = s["annual_ev"] - baseline_annual
        md.append(
            f"| **{key}** — {s['label']} | "
            f"{100.0 * s['fill_rate']:.0f}% | "
            f"${s['avg_stop_price']:.3f} | "
            f"${s['avg_slippage']:+.3f} | "
            f"${s['annual_ev']:+,.0f} | "
            f"${delta:+,.0f} |\n"
        )
    if break_even_price is not None:
        md.append(
            f"\n**Break-even stop price (uniform taker exit, full S4A "
            f"EV = 0):** ${break_even_price:.3f}. If realized average "
            "stop price is worse than this, S4A is unprofitable.\n"
        )

    # Part 7
    md.append("\n## Part 7 — Target exit reality check\n")
    if target_stats.get("n", 0) > 0:
        md.append(
            f"- Target exits: **{target_stats['n']}**\n"
            f"- Exit price distribution: p25 "
            f"${target_stats['exit_price_p25']:.3f}, median "
            f"${target_stats['exit_price_median']:.3f}, p75 "
            f"${target_stats['exit_price_p75']:.3f}, max "
            f"${target_stats['exit_price_max']:.3f}\n"
            f"- Targets with exit_price > $0.92 (gap-through past "
            f"the level): {target_stats['n_above_92']} "
            f"({target_stats['pct_above_92']:.1f}%)\n"
            f"- Median bin-to-bin rise into the target "
            f"(exit_price − prior_bin): "
            f"${target_stats['pre_target_gap_median']:.3f}\n"
            "\nSelling into strength at $0.90 is natural maker "
            "behavior on a binary market; if a few target exits "
            "show prices meaningfully above $0.90, P&L math uses "
            "$0.90 (not the observed VWAP) since that's where the "
            "resting limit would have filled.\n"
        )
    else:
        md.append("- No target exits in the dataset.\n")

    return "".join(md) + "\n"


def operational_recommendation(
    scenarios: dict[str, dict],
    break_even: float | None,
    stops: list[StopEvent],
) -> str:
    baseline = scenarios["A"]["annual_ev"]
    d_ev = scenarios["D"]["annual_ev"]
    c_ev = scenarios["C"]["annual_ev"]
    b_ev = scenarios["B"]["annual_ev"]

    # Pick the recommended scenario as the best expected-to-be-achievable
    # (D hybrid) while noting C as worst case for risk framing.
    best_achievable = max(
        ("B", b_ev), ("D", d_ev), key=lambda x: x[1]
    )

    # Share of severe gaps — if high, need to adjust stop depth.
    severe_rate = 100.0 * sum(
        1 for ev in stops if ev.gap_category == "severe"
    ) / (len(stops) or 1)

    lines: list[str] = []
    lines.append("\n## Operational Recommendation\n")
    lines.append(
        "\n**Recommended execution model for the live engine: "
        f"Scenario {best_achievable[0]} "
        f"({scenarios[best_achievable[0]]['label']}).**\n"
    )
    lines.append(
        f"\n- **Expected annual EV:** "
        f"${best_achievable[1]:+,.0f} "
        f"(baseline ${baseline:+,.0f}, taker-worst-case "
        f"${c_ev:+,.0f}).\n"
        f"- **Fill rate assumption:** "
        f"{100.0 * scenarios[best_achievable[0]]['fill_rate']:.0f}% of "
        "stops fill at the maker price; the remainder fall back to "
        "taker at the observed stop VWAP.\n"
    )
    lines.append(
        "\n**When to place the resting NO buy:** at entry time, "
        "place a 100-contract resting NO bid at $0.60 (= $0.40 YES "
        "stop). Keep it active as long as the position is open. The "
        "resting order costs nothing to keep on the book, and placing "
        "it pre-emptively — rather than waiting for price to approach "
        "— means the order has maximum queue priority if the market "
        "slides rather than gapping.\n"
    )
    if break_even is not None:
        lines.append(
            "\n**Break-even stop price:** "
            f"${break_even:.3f}. If live execution produces realized "
            "stop prices meaningfully worse than this, S4A is "
            "unprofitable — monitor Phase 4a paper-trade fills "
            "against this threshold.\n"
        )
    if severe_rate >= 15.0:
        lines.append(
            f"\n**Stop-level adjustment warranted:** "
            f"{severe_rate:.1f}% of stops gap past $0.34 (severe "
            "category). Consider placing the resting bid slightly "
            "above $0.60 NO (i.e., $0.61–$0.62 NO / $0.38–$0.39 YES) "
            "to increase fill probability at the cost of a small "
            "deterministic slippage. Simulate both in Phase 4b.\n"
        )
    else:
        lines.append(
            f"\n**Stop level:** keep the resting bid at $0.60 NO "
            f"($0.40 YES). Severe-gap rate of {severe_rate:.1f}% is "
            "low enough that the taker fallback handles it cleanly "
            "without a depth adjustment.\n"
        )
    lines.append(
        "\n**Cancel-and-market fallback timing:** if the engine "
        "detects fav VWAP ≤ $0.34 (severe gap zone) AND the resting "
        "NO bid has not filled, cancel immediately and submit a "
        "100-contract YES market sell. Don't wait 60 seconds — the "
        "severe-gap signal means price is collapsing and the "
        "slippage clock is running.\n"
    )
    return "".join(lines)


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading 404-game Kalshi paired dataset...")
    games = load_kalshi_games_all_spreads()
    n_games = len(games)
    log(f"  loaded {n_games} games")

    log("Precomputing trailing max...")
    lookback_bins = max(1, int(CFG.lookback_sec / BUCKET_SEC))
    precomp_max: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp_max[(g["ticker"], lookback_bins)] = (
            _precompute_trailing_max(fav, lookback_bins)
        )

    log("Simulating S4A and identifying stops...")
    labels = load_game_labels()
    stops, summary, n_trades, n_stops = identify_stops(
        games, precomp_max, labels,
    )
    log(
        f"  {n_trades} total entries, {n_stops} stops "
        f"({100 * n_stops / max(1, n_trades):.1f}%)"
    )

    all_trades = simulate_s4a(games, CFG, precomp_max)

    log("Annotating gap categories + dwell + descent...")
    games_by_ticker = {g["ticker"]: g for g in games}
    annotate_gaps(stops)
    compute_dwell(stops, games_by_ticker)
    annotate_descent(stops, games_by_ticker)

    log(f"Walking raw trade tape for {n_stops} stop events...")
    raw_by_event: dict[str, RawTradeAnalysis] = {}
    fetched = cached = missing = 0
    for i, ev in enumerate(stops, 1):
        if i % 25 == 0:
            log(
                f"  raw-trade progress: {i}/{n_stops} "
                f"(cached={cached}, fetched={fetched}, missing={missing})"
            )
        data = fetch_trade_tape(ev.ticker, use_cached=True)
        if data is None:
            missing += 1
            raw_by_event[ev.ticker] = None  # type: ignore
            continue
        if (_trades_path_for(ev.ticker)).exists():
            cached += 1
        else:
            fetched += 1
        fav_side = infer_fav_side_ticker({"ticker": ev.ticker}, data=data)
        rta = analyze_raw_trades(ev, data, fav_side)
        raw_by_event[ev.ticker] = rta
    log(
        f"Raw-trade coverage: cached={cached}, fetched={fetched}, "
        f"missing={missing}"
    )

    log("Computing EV under 4 scenarios...")
    scenarios = scenario_totals(
        all_trades, stops, raw_by_event, n_games,
    )
    break_even = break_even_stop_price(all_trades, n_games)

    log("Target exit sanity check...")
    target_stats = analyze_targets(all_trades, games_by_ticker)

    log("Rendering report...")
    md = build_report(
        n_games=n_games, n_trades=n_trades, n_stops=n_stops,
        baseline_summary=summary, stops=stops,
        raw_by_event=raw_by_event, scenarios=scenarios,
        break_even_price=break_even, target_stats=target_stats,
    )
    md += operational_recommendation(scenarios, break_even, stops)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
