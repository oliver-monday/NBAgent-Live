"""Timeout execution window analysis.

Measures whether NBA timeouts create favorable execution windows
on Kalshi by comparing volume, spread, price stability, and depth
in [T, T+90s] timeout windows vs bootstrapped baseline windows
from live-play periods.

Run:
    python -m analysis.timeout_execution_analysis
    python -m analysis.timeout_execution_analysis --games HOULAL
    python -m analysis.timeout_execution_analysis --games ORLDET
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.kalshi_trades_probe import (
    BASE_URL,
    _parse_ts,
    build_df,
    fetch_all_trades,
)
from scrapers.espn_scraper import save_game, scrape_game

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAP_DIR = REPO_ROOT / "data" / "orderbook_snapshots"
TRADES_DIR = REPO_ROOT / "data" / "kalshi_trades"
PBP_DIR = REPO_ROOT / "data" / "pbp"
REPORT_PATH = REPO_ROOT / "docs" / "analysis_outputs" / "timeout_execution_analysis.md"

WINDOW_SEC = 90
TIGHT_WINDOW_SEC = 60
BASELINE_N = 100
RUN_LOOKBACK_SEC = 120
RUN_THRESHOLD = 6  # net point differential

# Known game fixtures
GAMES = [
    {
        "slug": "HOULAL",
        "game_id": "401869190",
        "event_ticker": "KXNBAGAME-26APR18HOULAL",
        "snap_sources": ["2026-04-18.jsonl", "2026-04-19.jsonl"],
        "date": "2026-04-18",
        "label": "HOU@LAL",
    },
    {
        "slug": "ORLDET",
        "game_id": "401869193",
        "event_ticker": "KXNBAGAME-26APR19ORLDET",
        "snap_sources": [],  # per-game files discovered via glob
        "date": "2026-04-19",
        "label": "ORL@DET",
    },
]


# ---- Step 0: PBP availability --------------------------------------------

def ensure_pbp(game_id: str) -> Path:
    p = PBP_DIR / f"{game_id}.jsonl"
    if p.exists():
        return p
    print(f"  PBP missing for {game_id}; scraping...")
    data = scrape_game(game_id)
    if not data:
        raise RuntimeError(f"scrape_game({game_id}) returned None")
    save_game(data)
    return p


# ---- Step 1: ESPN PBP ----------------------------------------------------

def load_pbp(path: Path) -> list[dict]:
    plays = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                plays.append(json.loads(line))
    return plays


def is_timeout(play: dict) -> bool:
    t = play.get("type", {})
    if str(t.get("id")) == "16":
        return True
    return "timeout" in t.get("text", "").lower()


def extract_timeouts(plays: list[dict]) -> list[dict]:
    out = []
    for p in plays:
        if not is_timeout(p):
            continue
        wc = p.get("wallclock")
        if not wc:
            continue
        out.append({
            "wallclock": _parse_ts(wc),
            "period": p.get("period", {}).get("number"),
            "clock": p.get("clock", {}).get("displayValue"),
            "team_id": p.get("team", {}).get("id"),
            "type_text": p.get("type", {}).get("text"),
            "text": p.get("text"),
        })
    return out


def run_context(
    plays_df: pd.DataFrame, timeout_ts: datetime, lookback_sec: int,
) -> dict:
    """Sum scoring values by team in the lookback window before timeout."""
    lo = timeout_ts - timedelta(seconds=lookback_sec)
    window = plays_df[
        (plays_df["wallclock"] >= lo)
        & (plays_df["wallclock"] <= timeout_ts)
        & (plays_df["scoringPlay"] == True)  # noqa: E712
    ]
    by_team: dict[str, int] = {}
    for r in window.itertuples():
        tid = r.team_id
        if tid is None:
            continue
        by_team[tid] = by_team.get(tid, 0) + int(r.scoreValue or 0)
    if not by_team:
        return {"total_points": 0, "max_margin": 0, "is_run": False}
    scores = sorted(by_team.values(), reverse=True)
    top = scores[0]
    second = scores[1] if len(scores) > 1 else 0
    margin = top - second
    return {
        "total_points": sum(by_team.values()),
        "max_margin": margin,
        "is_run": margin >= RUN_THRESHOLD,
    }


def plays_to_df(plays: list[dict]) -> pd.DataFrame:
    rows = []
    for p in plays:
        wc = p.get("wallclock")
        if not wc:
            continue
        rows.append({
            "wallclock": _parse_ts(wc),
            "scoringPlay": bool(p.get("scoringPlay")),
            "scoreValue": p.get("scoreValue") or 0,
            "team_id": p.get("team", {}).get("id"),
            "type_text": p.get("type", {}).get("text"),
        })
    return pd.DataFrame(rows).sort_values("wallclock").reset_index(drop=True)


# ---- Step 2: Kalshi trade tape -------------------------------------------

def load_or_fetch_trades(event_ticker: str) -> pd.DataFrame:
    cache = TRADES_DIR / f"{event_ticker}.json"
    if cache.exists():
        with cache.open() as f:
            payload = json.load(f)
        trades = payload["trades"]
        print(f"  Loaded cached trades: {len(trades):,}")
    else:
        # Discover tickers from logger snapshots (same approach as probe).
        tickers = discover_tickers(event_ticker)
        if not tickers:
            raise RuntimeError(f"No tickers found for {event_ticker}")
        print(f"  Discovered tickers: {tickers}")
        trades = []
        for t in tickers:
            print(f"  Fetching trades for {t}...")
            chunk = fetch_all_trades(t)
            print(f"    → {len(chunk):,}")
            trades.extend(chunk)
        cache.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "event_ticker": event_ticker,
            "tickers": tickers,
            "trades": trades,
        }
        with cache.open("w") as f:
            json.dump(payload, f)
    return build_df(trades)


def discover_tickers(event_filter: str) -> list[str]:
    """Find market tickers for an event by scanning logger snapshots."""
    tickers: set[str] = set()
    for p in SNAP_DIR.glob("*.jsonl"):
        with p.open() as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = r.get("ticker", "")
                if event_filter in t:
                    tickers.add(t)
                    if len(tickers) >= 4:
                        break
        if len(tickers) >= 2:
            break
    return sorted(tickers)


# ---- Step 3: Logger snapshots --------------------------------------------

_SNAP_COLS = (
    "yes_bid_dollars", "yes_ask_dollars", "yes_bid_size_fp",
    "yes_ask_size_fp", "volume_fp",
)


def load_snapshots(event_ticker: str, snap_sources: list[str]) -> pd.DataFrame:
    rows = []
    paths = []
    # Pre-split date files
    for name in snap_sources:
        p = SNAP_DIR / name
        if p.exists():
            paths.append(p)
    # Per-game files
    paths.extend(SNAP_DIR.glob(f"{event_ticker}*.jsonl"))
    seen = set()
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        with p.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event_ticker not in r.get("ticker", ""):
                    continue
                rows.append(r)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    for c in _SNAP_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["mid"] = (df["yes_bid_dollars"] + df["yes_ask_dollars"]) / 2
    df["spread"] = df["yes_ask_dollars"] - df["yes_bid_dollars"]
    df["team"] = df["ticker"].str.rsplit("-", n=1).str[-1]
    df = df.drop_duplicates(subset=["ts", "ticker"])
    df = df.dropna(subset=["mid"]).sort_values("ts").reset_index(drop=True)
    return df


# ---- Step 4: Windows -----------------------------------------------------

@dataclass
class Window:
    start: datetime
    end: datetime
    label: str


def build_timeout_windows(
    timeouts: list[dict], width_sec: int,
) -> list[Window]:
    out = []
    for t in timeouts:
        start = t["wallclock"]
        out.append(Window(start, start + timedelta(seconds=width_sec), "timeout"))
    return out


def sample_baseline_windows(
    game_start: datetime,
    game_end: datetime,
    timeout_windows: list[Window],
    width_sec: int,
    n: int,
    rng: random.Random,
) -> list[Window]:
    """Sample N live-play windows not overlapping any timeout window."""
    span = (game_end - game_start).total_seconds() - width_sec
    if span <= 0:
        return []
    exclude = [(w.start.timestamp(), w.end.timestamp()) for w in timeout_windows]
    out: list[Window] = []
    attempts = 0
    max_attempts = n * 50
    while len(out) < n and attempts < max_attempts:
        attempts += 1
        offset = rng.random() * span
        start_ts = game_start.timestamp() + offset
        end_ts = start_ts + width_sec
        overlap = any(not (end_ts < lo or start_ts > hi) for lo, hi in exclude)
        if overlap:
            continue
        out.append(Window(
            datetime.fromtimestamp(start_ts, tz=timezone.utc),
            datetime.fromtimestamp(end_ts, tz=timezone.utc),
            "baseline",
        ))
    return out


# ---- Step 5: Measurements ------------------------------------------------

def measure_window(
    w: Window, trades: pd.DataFrame, snaps: pd.DataFrame,
) -> dict:
    """Compute all metrics for a single window."""
    t_mask = (trades["created_time"] >= w.start) & (trades["created_time"] <= w.end)
    sub_t = trades[t_mask]

    s_mask = (snaps["ts"] >= w.start) & (snaps["ts"] <= w.end)
    sub_s = snaps[s_mask]
    if sub_s.empty and not snaps.empty:
        midpoint = w.start + (w.end - w.start) / 2
        delta = (snaps["ts"] - midpoint).abs()
        nearest_idx = delta.idxmin()
        if delta.loc[nearest_idx] <= timedelta(seconds=30):
            sub_s = snaps.loc[[nearest_idx]]

    if sub_t.empty:
        price_range = 0.0
        price_std = 0.0
        mid_drift = 0.0
        contracts = 0.0
        mean_sz = float("nan")
    else:
        prices = sub_t["yes_price_dollars"]
        price_range = float(prices.max() - prices.min())
        price_std = float(prices.std(ddof=0)) if len(prices) > 1 else 0.0
        mid_drift = float(abs(prices.iloc[-1] - prices.iloc[0]))
        contracts = float(sub_t["count_fp"].sum())
        mean_sz = float(sub_t["count_fp"].mean())

    if sub_s.empty:
        mean_spread = float("nan")
        min_spread = float("nan")
        bid_depth = float("nan")
        ask_depth = float("nan")
    else:
        mean_spread = float(sub_s["spread"].mean())
        min_spread = float(sub_s["spread"].min())
        bid_depth = float(sub_s["yes_bid_size_fp"].mean())
        ask_depth = float(sub_s["yes_ask_size_fp"].mean())

    return {
        "trades": int(len(sub_t)),
        "contracts": contracts,
        "mean_size": mean_sz,
        "mean_spread": mean_spread,
        "min_spread": min_spread,
        "price_range": price_range,
        "price_std": price_std,
        "mid_drift": mid_drift,
        "bid_depth": bid_depth,
        "ask_depth": ask_depth,
    }


def summarize(metrics: list[dict]) -> dict:
    if not metrics:
        return {}
    df = pd.DataFrame(metrics)
    return {col: float(df[col].mean(skipna=True)) for col in df.columns}


# ---- Step 6/7: Aggregate & run-context -----------------------------------

def per_game_analysis(game: dict, rng: random.Random) -> dict:
    print(f"\n=== {game['label']} ({game['game_id']}) ===")

    pbp_path = ensure_pbp(game["game_id"])
    plays = load_pbp(pbp_path)
    timeouts = extract_timeouts(plays)
    plays_df = plays_to_df(plays)
    if plays_df.empty:
        raise RuntimeError("No plays with wallclock")
    game_start = plays_df["wallclock"].iloc[0]
    game_end = plays_df["wallclock"].iloc[-1]
    print(f"  PBP: {len(plays)} plays, {len(timeouts)} timeouts, "
          f"window {game_start} → {game_end}")

    trades = load_or_fetch_trades(game["event_ticker"])
    print(f"  Trades: {len(trades):,} ({trades['count_fp'].sum():,.0f} contracts)")

    snaps = load_snapshots(game["event_ticker"], game["snap_sources"])
    snaps_ingame = snaps[
        (snaps["ts"] >= game_start) & (snaps["ts"] <= game_end)
    ].reset_index(drop=True)
    print(f"  Snapshots: {len(snaps):,} total, {len(snaps_ingame):,} in-game")

    # Build windows
    to_windows = build_timeout_windows(timeouts, WINDOW_SEC)
    to_windows_tight = build_timeout_windows(timeouts, TIGHT_WINDOW_SEC)
    baseline_windows = sample_baseline_windows(
        game_start, game_end, to_windows, WINDOW_SEC, BASELINE_N, rng,
    )
    print(f"  Windows: {len(to_windows)} timeout (90s), "
          f"{len(baseline_windows)} baseline (90s)")

    # Measure all windows
    to_metrics = [measure_window(w, trades, snaps_ingame) for w in to_windows]
    to_tight_metrics = [
        measure_window(w, trades, snaps_ingame) for w in to_windows_tight
    ]
    base_metrics = [measure_window(w, trades, snaps_ingame) for w in baseline_windows]

    # Run-context split
    run_tags = []
    for t in timeouts:
        ctx = run_context(plays_df, t["wallclock"], RUN_LOOKBACK_SEC)
        run_tags.append(ctx)
    after_run = [m for m, c in zip(to_metrics, run_tags) if c["is_run"]]
    other_to = [m for m, c in zip(to_metrics, run_tags) if not c["is_run"]]

    # Per-timeout detail
    detail = []
    for t, m, c in zip(timeouts, to_metrics, run_tags):
        detail.append({**t, **m, **c})

    return {
        "game": game,
        "n_plays": len(plays),
        "n_timeouts": len(timeouts),
        "game_start": game_start,
        "game_end": game_end,
        "n_trades": len(trades),
        "n_snaps_ingame": len(snaps_ingame),
        "to_metrics": to_metrics,
        "to_tight_metrics": to_tight_metrics,
        "base_metrics": base_metrics,
        "after_run_metrics": after_run,
        "other_to_metrics": other_to,
        "timeout_detail": detail,
    }


# ---- Step 8: Reporting ---------------------------------------------------

METRIC_ORDER = [
    ("trades", "Trades per window", ".2f"),
    ("contracts", "Contracts per window", ",.0f"),
    ("mean_size", "Mean trade size", ",.1f"),
    ("mean_spread", "Mean spread ($)", ".4f"),
    ("price_range", "Price range ($)", ".4f"),
    ("price_std", "Price std ($)", ".4f"),
    ("mid_drift", "Mid drift ($)", ".4f"),
    ("bid_depth", "Mean bid depth (fp)", ",.0f"),
    ("ask_depth", "Mean ask depth (fp)", ",.0f"),
]


def fmt(val: float, spec: str) -> str:
    if val is None or (isinstance(val, float) and (np.isnan(val))):
        return "—"
    return format(val, spec)


def comparison_table(
    timeout_summary: dict, baseline_summary: dict, heading: str,
) -> list[str]:
    lines = [f"### {heading}", ""]
    lines.append("| Metric | Timeout (90s) | Baseline (90s) | Ratio |")
    lines.append("|---|---:|---:|---:|")
    for key, label, spec in METRIC_ORDER:
        t = timeout_summary.get(key)
        b = baseline_summary.get(key)
        if t is None or b is None:
            ratio_str = "—"
        elif not isinstance(b, float) or b == 0 or np.isnan(b) or np.isnan(t):
            ratio_str = "—"
        else:
            ratio_str = f"{t/b:.2f}"
        lines.append(
            f"| {label} | {fmt(t, spec)} | {fmt(b, spec)} | {ratio_str} |"
        )
    lines.append("")
    return lines


def build_report(per_game: list[dict]) -> str:
    md: list[str] = []
    md.append("# Timeout execution window analysis\n")
    md.append(
        f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n"
    )
    md.append(
        "Measures whether NBA timeouts create favorable execution windows "
        "on Kalshi by comparing volume, spread, price stability, and depth "
        f"in [T, T+{WINDOW_SEC}s] timeout windows against "
        f"{BASELINE_N} bootstrapped baseline windows per game (live-play "
        "periods not overlapping any timeout window).\n"
    )

    # Section 1: data summary
    md.append("## 1. Data summary\n")
    md.append("| Game | PBP plays | Timeouts | Trades | In-game snapshots |")
    md.append("|---|---:|---:|---:|---:|")
    for r in per_game:
        md.append(
            f"| {r['game']['label']} | {r['n_plays']:,} | "
            f"{r['n_timeouts']} | {r['n_trades']:,} | {r['n_snaps_ingame']:,} |"
        )
    md.append("")

    # Section 2: per-game tables
    md.append("## 2. Per-game timeout vs baseline\n")
    for r in per_game:
        to_sum = summarize(r["to_metrics"])
        base_sum = summarize(r["base_metrics"])
        md.extend(comparison_table(to_sum, base_sum, r["game"]["label"]))

    # Section 3: pooled
    md.append("## 3. Pooled comparison (both games)\n")
    pooled_to = [m for r in per_game for m in r["to_metrics"]]
    pooled_base = [m for r in per_game for m in r["base_metrics"]]
    pooled_tight = [m for r in per_game for m in r["to_tight_metrics"]]
    md.extend(comparison_table(
        summarize(pooled_to), summarize(pooled_base), "90-second windows",
    ))
    md.append(
        "Tight 60s variant (same baseline for comparison):\n"
    )
    md.extend(comparison_table(
        summarize(pooled_tight), summarize(pooled_base),
        "60-second timeout windows vs 90-second baseline",
    ))

    # Section 4: run-context split
    md.append("## 4. Run-context split\n")
    md.append(
        f"Run = one team outscored the other by ≥ {RUN_THRESHOLD} points "
        f"in the {RUN_LOOKBACK_SEC}s before the timeout.\n"
    )
    after_run = [m for r in per_game for m in r["after_run_metrics"]]
    other_to = [m for r in per_game for m in r["other_to_metrics"]]
    md.append(
        f"After-run timeouts (pooled): **{len(after_run)}**. "
        f"Other timeouts: **{len(other_to)}**.\n"
    )
    md.extend(comparison_table(
        summarize(after_run), summarize(pooled_base),
        "After-run timeouts vs baseline",
    ))
    md.extend(comparison_table(
        summarize(other_to), summarize(pooled_base),
        "Other timeouts vs baseline",
    ))

    # Section 5: verdict
    to_sum = summarize(pooled_to)
    base_sum = summarize(pooled_base)
    verdict = build_verdict(to_sum, base_sum, summarize(after_run))
    md.append("## 5. Verdict\n")
    md.append(verdict + "\n")

    # Section 6: implications
    md.append("## 6. Implication for Strategy 3 entry rule\n")
    md.append(build_implication(to_sum, base_sum) + "\n")

    # Appendix: per-timeout detail
    md.append("## Appendix — per-timeout detail\n")
    md.append(
        "| Game | Period | Clock | Type | Run? | Margin (2min) | "
        "Trades | Contracts | Mean spread |"
    )
    md.append("|---|---:|---|---|---|---:|---:|---:|---:|")
    for r in per_game:
        for d in r["timeout_detail"]:
            md.append(
                f"| {r['game']['label']} | Q{d['period']} | {d['clock']} | "
                f"{d['type_text']} | "
                f"{'✓' if d['is_run'] else '—'} | "
                f"{d['max_margin']} | "
                f"{d['trades']} | {d['contracts']:,.0f} | "
                f"{fmt(d['mean_spread'], '.4f')} |"
            )
    md.append("")
    return "\n".join(md)


def build_verdict(to_sum: dict, base_sum: dict, run_sum: dict) -> str:
    def ratio(k: str) -> float | None:
        t = to_sum.get(k)
        b = base_sum.get(k)
        if t is None or b is None or b == 0 or np.isnan(t) or np.isnan(b):
            return None
        return t / b

    vol_r = ratio("trades")
    sp_r = ratio("mean_spread")
    drift_r = ratio("mid_drift")
    depth_r = ratio("bid_depth")

    parts = []
    if vol_r is not None:
        direction = "concentrates" if vol_r > 1.1 else (
            "thins" if vol_r < 0.9 else "tracks baseline"
        )
        parts.append(f"volume {direction} in timeout windows ({vol_r:.2f}× baseline)")
    if sp_r is not None:
        direction = "tightens" if sp_r < 0.95 else (
            "widens" if sp_r > 1.05 else "is unchanged"
        )
        parts.append(f"spread {direction} ({sp_r:.2f}×)")
    if drift_r is not None:
        direction = "falls" if drift_r < 0.9 else (
            "rises" if drift_r > 1.1 else "is unchanged"
        )
        parts.append(f"mid-price drift {direction} ({drift_r:.2f}×)")
    if depth_r is not None:
        direction = "deepens" if depth_r > 1.1 else (
            "thins" if depth_r < 0.9 else "is unchanged"
        )
        parts.append(f"top-of-book depth {direction} ({depth_r:.2f}×)")

    core = "; ".join(parts) if parts else "no comparable metrics available"

    # Is the thesis supported?
    supports = 0
    tests = 0
    if drift_r is not None:
        tests += 1
        if drift_r < 1.0:
            supports += 1
    if sp_r is not None:
        tests += 1
        if sp_r < 1.0:
            supports += 1
    if depth_r is not None:
        tests += 1
        if depth_r > 1.0:
            supports += 1

    if tests == 0:
        stance = "Insufficient data to judge the timeout-execution thesis."
    elif supports == tests:
        stance = (
            "**Thesis supported:** timeouts look like measurably calmer "
            "execution windows than random live play across every tested "
            "dimension."
        )
    elif supports >= tests - 1 and tests >= 2:
        stance = (
            "**Thesis partially supported:** most dimensions point toward "
            "calmer execution in timeout windows, with at least one "
            "inconclusive or reversed signal."
        )
    else:
        stance = (
            "**Thesis not supported:** timeout windows do not appear "
            "measurably different from live-play baseline on the "
            "combination of metrics tested."
        )
    return f"Pooled across {len(per_game_count())} games: {core}. {stance}"


def per_game_count():
    # placeholder helper — returns global per_game count indirectly.
    # The actual count is rendered via len(PER_GAME_REFS) set in main().
    return PER_GAME_REFS


PER_GAME_REFS: list = []


def build_implication(to_sum: dict, base_sum: dict) -> str:
    def ratio(k: str) -> float | None:
        t = to_sum.get(k)
        b = base_sum.get(k)
        if t is None or b is None or b == 0 or np.isnan(t) or np.isnan(b):
            return None
        return t / b

    sp_r = ratio("mean_spread")
    drift_r = ratio("mid_drift")
    depth_r = ratio("bid_depth")
    vol_r = ratio("trades")

    lines = []
    if drift_r is not None and drift_r < 0.85:
        lines.append(
            "Resting a maker order during a timeout window is meaningfully "
            "less likely to have the book move away before the fill lands "
            "than during random live play."
        )
    if sp_r is not None and sp_r < 0.95:
        lines.append(
            "Spread tightens modestly during timeouts, so the maker price "
            "target is closer to the mid and the fill probability at a "
            "given offset is higher."
        )
    if depth_r is not None and depth_r > 1.1:
        lines.append(
            "Deeper resting bid size means the queue-position cost for "
            "a maker order is higher, but so is the odds of a clean fill "
            "without partial execution."
        )
    if vol_r is not None and vol_r > 1.2:
        lines.append(
            "Taker flow concentrates in timeout windows — maker orders "
            "resting at the inside have more opportunities to cross."
        )
    if not lines:
        lines.append(
            "The measured differences are small relative to sample noise "
            "at n=2 games. Treat as inconclusive and re-run once more "
            "playoff games accumulate."
        )
    return " ".join(lines)


# ---- Main ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=str, default=None,
                        help="Comma-separated slugs (HOULAL,ORLDET). "
                             "Default: all.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    selected = GAMES
    if args.games:
        want = {s.strip().upper() for s in args.games.split(",")}
        selected = [g for g in GAMES if g["slug"] in want]
        if not selected:
            raise SystemExit(f"No games matched {args.games}")

    per_game = []
    for g in selected:
        per_game.append(per_game_analysis(g, rng))

    global PER_GAME_REFS
    PER_GAME_REFS = per_game

    md = build_report(per_game)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md + "\n")
    print(f"\nReport written → {REPORT_PATH}")

    # Print pooled comparison to stdout
    print("\n=== Pooled comparison ===")
    pooled_to = [m for r in per_game for m in r["to_metrics"]]
    pooled_base = [m for r in per_game for m in r["base_metrics"]]
    to_sum = summarize(pooled_to)
    base_sum = summarize(pooled_base)
    for key, label, spec in METRIC_ORDER:
        t = to_sum.get(key)
        b = base_sum.get(key)
        ratio = (
            f"{t/b:.2f}" if (t is not None and b not in (None, 0)
                             and not np.isnan(t) and not np.isnan(b))
            else "—"
        )
        print(f"  {label:<26}  timeout={fmt(t, spec):>12}  "
              f"baseline={fmt(b, spec):>12}  ratio={ratio}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
