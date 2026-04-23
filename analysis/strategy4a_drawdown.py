"""S4A drawdown + capital-requirements analysis.

Builds the chronologically-ordered cumulative P&L curve from all
S4A entries across the 404-game Kalshi paired dataset. Answers:
max drawdown, longest losing streak, min starting capital to
never go negative, peak concurrent capital deployed.

Single-config only: STRATEGY4_SPEC.md §2 best config
(180s lookback, $0.08 dip, $0.50-$0.75 entry, $0.90 target,
$0.40 stop, 100 contracts). Fees: maker on entry + target exit,
taker on stop exit.

Run:
    python -m analysis.strategy4a_drawdown
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    CONTRACT_SIZE,
    S4AConfig,
    S4ATrade,
    _precompute_trailing_max,
    load_kalshi_games_all_spreads,
    simulate_s4a,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy4a_drawdown.md"
)

S4A_CFG = S4AConfig(
    lookback_sec=180, dip_depth=0.08,
    entry_lo=0.50, entry_hi=0.75,
    exit_target=0.90, stop_loss=0.40,
)

NIGHTLY_PNL_BUCKETS: list[tuple[str, float, float]] = [
    ("> +$50", 50, float("inf")),
    ("+$25 to +$50", 25, 50),
    ("+$0 to +$25", 0.0, 25),
    ("-$25 to $0", -25, 0.0),
    ("-$50 to -$25", -50, -25),
    ("< -$50", -float("inf"), -50),
]


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


def maker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1 - price) * 100) / 100


def taker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.07 * contracts * price * (1 - price) * 100) / 100


# ---- Trade enrichment with wallclock timestamps ----------------------

@dataclass
class EnrichedTrade:
    ticker: str
    entry_idx: int
    entry_price: float
    exit_idx: int
    exit_price: float
    exit_type: str
    entry_ts: datetime
    exit_ts: datetime
    entry_capital: float     # entry_price × 100
    net_pnl: float           # recomputed with maker/taker fee split
    abs_spread: float

    @property
    def is_win(self) -> bool:
        return self.net_pnl > 0


def _recompute_pnl(
    entry_price: float, exit_type: str, exit_price: float,
) -> float:
    """Maker on entry + target, taker on stop exit. Resolution cases
    use the trade's observed exit price with taker fee for mid and
    zero fee for clean win/loss."""
    entry_fee = maker_fee(CONTRACT_SIZE, entry_price)
    if exit_type == "target":
        exit_fee = maker_fee(CONTRACT_SIZE, exit_price)
    elif exit_type == "stop":
        exit_fee = taker_fee(CONTRACT_SIZE, exit_price)
    elif exit_type in ("resolution_win", "resolution_loss"):
        exit_fee = 0.0
    else:  # resolution_mid
        exit_fee = taker_fee(CONTRACT_SIZE, exit_price)
    return (exit_price - entry_price) * CONTRACT_SIZE - entry_fee - exit_fee


def enrich_trades(
    trades: list[S4ATrade], games: list[dict],
) -> list[EnrichedTrade]:
    ts_by_ticker = {g["ticker"]: g["ts"] for g in games}
    spread_by_ticker = {g["ticker"]: g["abs_spread"] for g in games}
    out: list[EnrichedTrade] = []
    missing_ts = 0
    for t in trades:
        ts_df = ts_by_ticker.get(t.ticker)
        if ts_df is None or "bucket_start_utc" not in ts_df.columns:
            missing_ts += 1
            continue
        try:
            entry_raw = str(ts_df["bucket_start_utc"].iloc[t.entry_idx])
            exit_raw = str(ts_df["bucket_start_utc"].iloc[t.exit_idx])
            entry_ts = pd.to_datetime(entry_raw, utc=True).to_pydatetime()
            exit_ts = pd.to_datetime(exit_raw, utc=True).to_pydatetime()
        except (IndexError, ValueError, TypeError):
            missing_ts += 1
            continue
        pnl = _recompute_pnl(t.entry_price, t.exit_type, t.exit_price)
        out.append(EnrichedTrade(
            ticker=t.ticker,
            entry_idx=t.entry_idx, entry_price=t.entry_price,
            exit_idx=t.exit_idx, exit_price=t.exit_price,
            exit_type=t.exit_type,
            entry_ts=entry_ts, exit_ts=exit_ts,
            entry_capital=t.entry_price * CONTRACT_SIZE,
            net_pnl=pnl,
            abs_spread=spread_by_ticker.get(t.ticker, 0.0),
        ))
    if missing_ts:
        log(f"  WARN: {missing_ts} trades missing timestamp data")
    return sorted(out, key=lambda x: x.entry_ts)


# ---- Section 2: running P&L ------------------------------------------

@dataclass
class RunningCurve:
    points: list[dict]          # {ts, pnl, cum, peak, drawdown}
    max_cum: float
    max_cum_ts: datetime
    min_cum: float
    min_cum_ts: datetime
    max_dd: float
    max_dd_peak: float
    max_dd_trough: float
    max_dd_peak_ts: datetime
    max_dd_trough_ts: datetime
    final_cum: float


def compute_running_curve(trades: list[EnrichedTrade]) -> RunningCurve:
    cum = 0.0
    peak = 0.0
    peak_ts = trades[0].entry_ts if trades else datetime.now(timezone.utc)
    max_dd = 0.0
    max_dd_peak = 0.0
    max_dd_trough = 0.0
    max_dd_peak_ts = peak_ts
    max_dd_trough_ts = peak_ts
    max_cum = 0.0
    max_cum_ts = peak_ts
    min_cum = 0.0
    min_cum_ts = peak_ts
    points: list[dict] = []
    for t in trades:
        cum += t.net_pnl
        if cum > peak:
            peak = cum
            peak_ts = t.entry_ts
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
            max_dd_peak = peak
            max_dd_trough = cum
            max_dd_peak_ts = peak_ts
            max_dd_trough_ts = t.entry_ts
        if cum > max_cum:
            max_cum = cum
            max_cum_ts = t.entry_ts
        if cum < min_cum:
            min_cum = cum
            min_cum_ts = t.entry_ts
        points.append({
            "ts": t.entry_ts, "pnl": t.net_pnl,
            "cum": cum, "peak": peak, "drawdown": dd,
        })
    return RunningCurve(
        points=points,
        max_cum=max_cum, max_cum_ts=max_cum_ts,
        min_cum=min_cum, min_cum_ts=min_cum_ts,
        max_dd=max_dd,
        max_dd_peak=max_dd_peak, max_dd_trough=max_dd_trough,
        max_dd_peak_ts=max_dd_peak_ts, max_dd_trough_ts=max_dd_trough_ts,
        final_cum=cum,
    )


# ---- Section 3: streaks ----------------------------------------------

@dataclass
class StreakStats:
    lengths_by_type: dict[str, list[int]]   # "W" / "L"
    longest_loss: int
    longest_loss_dollars: float
    longest_win: int
    longest_win_dollars: float


def compute_streaks(trades: list[EnrichedTrade]) -> StreakStats:
    lengths: dict[str, list[int]] = {"W": [], "L": []}
    cur_type: str | None = None
    cur_len = 0
    cur_dollars = 0.0
    longest_loss = 0
    longest_loss_dollars = 0.0
    longest_win = 0
    longest_win_dollars = 0.0
    for t in trades:
        this_type = "W" if t.is_win else "L"
        if cur_type is None:
            cur_type = this_type
            cur_len = 1
            cur_dollars = t.net_pnl
            continue
        if this_type == cur_type:
            cur_len += 1
            cur_dollars += t.net_pnl
        else:
            lengths[cur_type].append(cur_len)
            if cur_type == "L" and cur_len > longest_loss:
                longest_loss = cur_len
                longest_loss_dollars = cur_dollars
            elif cur_type == "W" and cur_len > longest_win:
                longest_win = cur_len
                longest_win_dollars = cur_dollars
            cur_type = this_type
            cur_len = 1
            cur_dollars = t.net_pnl
    # Final streak
    if cur_type is not None:
        lengths[cur_type].append(cur_len)
        if cur_type == "L" and cur_len > longest_loss:
            longest_loss = cur_len
            longest_loss_dollars = cur_dollars
        elif cur_type == "W" and cur_len > longest_win:
            longest_win = cur_len
            longest_win_dollars = cur_dollars
    return StreakStats(
        lengths_by_type=lengths,
        longest_loss=longest_loss,
        longest_loss_dollars=longest_loss_dollars,
        longest_win=longest_win,
        longest_win_dollars=longest_win_dollars,
    )


# ---- Section 4: capital requirements ---------------------------------

def peak_concurrent_capital(
    trades: list[EnrichedTrade],
) -> tuple[float, datetime, int]:
    """Sweep-line over (entry_ts, exit_ts) to find peak overlap.

    Returns (peak_capital, peak_ts, peak_concurrent_count).
    """
    events: list[tuple[datetime, int, float]] = []
    # +1 at entry, -1 at exit. Use (ts, priority, capital) — ties: close
    # before open to avoid double-counting at identical timestamps.
    for t in trades:
        events.append((t.entry_ts, 0, t.entry_capital))  # open
        events.append((t.exit_ts, -1, -t.entry_capital))  # close first
    # Sort: earlier ts first; on tie, closes (priority -1) before opens.
    events.sort(key=lambda e: (e[0], e[1]))
    running = 0.0
    running_count = 0
    peak = 0.0
    peak_ts = events[0][0] if events else datetime.now(timezone.utc)
    peak_count = 0
    for ts, priority, delta in events:
        if priority == 0:
            running += delta
            running_count += 1
        else:
            running += delta
            running_count -= 1
        if running > peak:
            peak = running
            peak_ts = ts
            peak_count = running_count
    return peak, peak_ts, peak_count


# ---- Section 5: nightly P&L ------------------------------------------

def nightly_pnl(
    trades: list[EnrichedTrade],
) -> dict[str, dict]:
    by_night: dict[str, list[EnrichedTrade]] = defaultdict(list)
    for t in trades:
        date = t.entry_ts.date().isoformat()
        by_night[date].append(t)
    out: dict[str, dict] = {}
    for date, nightly in by_night.items():
        pnls = [t.net_pnl for t in nightly]
        out[date] = {
            "n_entries": len(nightly),
            "net_pnl": float(sum(pnls)),
            "trades": nightly,
        }
    return out


# ---- Report rendering -------------------------------------------------

def render_report(
    n_games: int,
    trades: list[EnrichedTrade],
    curve: RunningCurve,
    streaks: StreakStats,
    peak_capital: float, peak_capital_ts: datetime, peak_concurrent: int,
    nightly: dict[str, dict],
) -> str:
    md: list[str] = []
    md.append("# Strategy 4A — Drawdown & Capital Requirements\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Chronologically-ordered cumulative P&L curve from all "
        f"**{len(trades)} S4A entries** across the **{n_games}-game "
        "Kalshi paired dataset**. Single config: "
        f"lookback {S4A_CFG.lookback_sec}s, dip ≥ "
        f"${S4A_CFG.dip_depth:.2f}, entry "
        f"${S4A_CFG.entry_lo:.2f}-${S4A_CFG.entry_hi:.2f}, "
        f"target ${S4A_CFG.exit_target:.2f}, stop "
        f"${S4A_CFG.stop_loss:.2f}, {CONTRACT_SIZE} contracts. "
        "Fees: maker on entry + target exit, taker on stop exit.\n"
    )

    # ---- Section 1 ---------------------------------------------------
    md.append("\n## Section 1 — Entry timeline\n")
    first_ts = trades[0].entry_ts
    last_ts = trades[-1].entry_ts
    per_night_counts = Counter(
        t.entry_ts.date().isoformat() for t in trades
    )
    busiest = max(per_night_counts.items(), key=lambda kv: kv[1])
    counts = list(per_night_counts.values())
    md.append(
        f"- Total entries: **{len(trades)}**\n"
        f"- Date range: {first_ts.date().isoformat()} → "
        f"{last_ts.date().isoformat()} "
        f"({(last_ts - first_ts).days + 1} calendar days)\n"
        f"- Nights with ≥1 entry: **{len(per_night_counts)}**\n"
        f"- Mean entries/active night: "
        f"{float(np.mean(counts)):.2f}\n"
        f"- Median entries/active night: "
        f"{int(np.median(counts))}\n"
        f"- P90 entries/night: "
        f"{int(np.quantile(counts, 0.90))}\n"
        f"- Busiest night: **{busiest[0]}** with "
        f"**{busiest[1]} entries**\n"
    )

    # ---- Section 2 ---------------------------------------------------
    md.append("\n## Section 2 — Running cumulative P&L\n")
    md.append(
        f"- Final cumulative P&L: **${curve.final_cum:+,.2f}**\n"
        f"- Max cumulative P&L: "
        f"${curve.max_cum:+,.2f} at "
        f"{curve.max_cum_ts.date().isoformat()}\n"
        f"- Min cumulative P&L: "
        f"${curve.min_cum:+,.2f} at "
        f"{curve.min_cum_ts.date().isoformat()}\n"
    )
    md.append(
        f"- **Max peak-to-trough drawdown: "
        f"${curve.max_dd:,.2f}**\n"
        f"  - Peak: ${curve.max_dd_peak:+,.2f} at "
        f"{curve.max_dd_peak_ts.date().isoformat()}\n"
        f"  - Trough: ${curve.max_dd_trough:+,.2f} at "
        f"{curve.max_dd_trough_ts.date().isoformat()}\n"
        f"  - Drawdown window: "
        f"{(curve.max_dd_trough_ts - curve.max_dd_peak_ts).days} "
        "days\n"
    )

    # ---- Section 3 ---------------------------------------------------
    md.append("\n## Section 3 — Win/loss streaks\n")
    loss_counts = Counter(streaks.lengths_by_type["L"])
    win_counts = Counter(streaks.lengths_by_type["W"])
    md.append(
        f"- **Longest losing streak: {streaks.longest_loss} "
        f"consecutive losses** (cumulative "
        f"${streaks.longest_loss_dollars:+,.2f})\n"
        f"- **Longest winning streak: {streaks.longest_win} "
        f"consecutive wins** (cumulative "
        f"${streaks.longest_win_dollars:+,.2f})\n"
        f"- Mean loss streak length: "
        f"{float(np.mean(streaks.lengths_by_type['L'])):.2f} "
        f"(n={len(streaks.lengths_by_type['L'])} streaks)\n"
        f"- Mean win streak length: "
        f"{float(np.mean(streaks.lengths_by_type['W'])):.2f} "
        f"(n={len(streaks.lengths_by_type['W'])} streaks)\n"
    )
    md.append("\n### Streak-length distribution\n\n")
    md.append(
        "| Streak length | Win streaks | Loss streaks |\n"
        "|---:|---:|---:|\n"
    )
    all_lengths = sorted(set(list(win_counts) + list(loss_counts)))
    for L in all_lengths:
        md.append(
            f"| {L} | {win_counts.get(L, 0)} | "
            f"{loss_counts.get(L, 0)} |\n"
        )

    # ---- Section 4 ---------------------------------------------------
    md.append("\n## Section 4 — Capital requirements\n")
    min_capital = abs(min(0.0, curve.min_cum))
    recommended = min_capital * 1.5
    capitals = [t.entry_capital for t in trades]
    runtime_days = (last_ts - first_ts).days + 1
    annualization = 365.0 / runtime_days if runtime_days else 1.0
    annual_pnl = curve.final_cum * annualization
    ret_on_rec = (
        annual_pnl / recommended * 100
        if recommended > 0 else float("inf")
    )
    ret_on_min = (
        annual_pnl / min_capital * 100
        if min_capital > 0 else float("inf")
    )
    md.append(
        f"- Minimum starting capital to never go negative: "
        f"**${min_capital:,.2f}**\n"
        f"  - Computed as |min cumulative P&L| = "
        f"|${curve.min_cum:+,.2f}|\n"
        f"- Recommended starting capital (×1.5 safety margin): "
        f"**${recommended:,.2f}**\n"
    )
    md.append(
        "\n### Capital deployed per entry (entry_price × 100)\n\n"
        "| Metric | Value |\n|---|---:|\n"
        f"| Mean | ${float(np.mean(capitals)):.2f} |\n"
        f"| Median | ${float(np.median(capitals)):.2f} |\n"
        f"| P90 | ${float(np.quantile(capitals, 0.90)):.2f} |\n"
        f"| Max | ${float(max(capitals)):.2f} |\n"
    )
    md.append(
        f"\n### Peak concurrent capital deployed\n\n"
        f"- **Peak capital at risk simultaneously: "
        f"${peak_capital:,.2f}**\n"
        f"- Occurred at: {peak_capital_ts.isoformat()}\n"
        f"- Concurrent positions at peak: {peak_concurrent}\n"
        "\n(Computed via sweep-line over trade entry/exit "
        "timestamps. Concurrency reflects trades with overlapping "
        "entry-to-exit windows.)\n"
    )
    md.append(
        "\n### Return on capital\n\n"
        f"- Dataset span: {runtime_days} calendar days "
        f"(annualization factor ×{annualization:.3f})\n"
        f"- Final P&L: ${curve.final_cum:+,.2f} → "
        f"annualized ~${annual_pnl:+,.2f}/yr\n"
        f"- Return on minimum capital: "
        f"**{ret_on_min:.1f}%/yr** "
        f"(${annual_pnl:+,.0f} / ${min_capital:,.0f})\n"
        f"- Return on recommended capital: "
        f"**{ret_on_rec:.1f}%/yr** "
        f"(${annual_pnl:+,.0f} / ${recommended:,.0f})\n"
    )

    # ---- Section 5 ---------------------------------------------------
    md.append("\n## Section 5 — Nightly P&L distribution\n")
    pnls = [v["net_pnl"] for v in nightly.values()]
    n_nights = len(nightly)
    md.append(
        f"- Active nights: {n_nights}\n"
        f"- Mean nightly P&L: ${float(np.mean(pnls)):+.2f}\n"
        f"- Median nightly P&L: ${float(np.median(pnls)):+.2f}\n"
    )
    worst_night = min(nightly.items(), key=lambda kv: kv[1]["net_pnl"])
    best_night = max(nightly.items(), key=lambda kv: kv[1]["net_pnl"])
    md.append(
        f"- **Worst night:** {worst_night[0]} at "
        f"${worst_night[1]['net_pnl']:+,.2f} "
        f"({worst_night[1]['n_entries']} entries)\n"
        f"- **Best night:** {best_night[0]} at "
        f"${best_night[1]['net_pnl']:+,.2f} "
        f"({best_night[1]['n_entries']} entries)\n"
    )
    md.append("\n### Nightly P&L histogram\n\n")
    md.append("| P&L bucket | Nights | % |\n|---|---:|---:|\n")
    arr = np.array(pnls)
    for lab, lo, hi in NIGHTLY_PNL_BUCKETS:
        mask = (arr >= lo) & (arr < hi)
        c = int(mask.sum())
        md.append(
            f"| {lab} | {c} | "
            f"{100 * c / max(1, n_nights):.1f}% |\n"
        )

    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading 404-game Kalshi paired dataset...")
    games = load_kalshi_games_all_spreads()
    log(f"  {len(games)} games loaded")

    log("Simulating S4A...")
    lb_bins = max(1, int(S4A_CFG.lookback_sec / BUCKET_SEC))
    precomp: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp[(g["ticker"], lb_bins)] = (
            _precompute_trailing_max(fav, lb_bins)
        )
    trades = simulate_s4a(games, S4A_CFG, precomp)
    log(f"  {len(trades)} raw S4A trades")

    log("Enriching trades with wallclock timestamps...")
    enriched = enrich_trades(trades, games)
    log(f"  {len(enriched)} trades with valid timestamps")
    if not enriched:
        log("FAIL: no enriched trades")
        return 2

    log("Computing running cumulative P&L curve...")
    curve = compute_running_curve(enriched)
    log(
        f"  final ${curve.final_cum:+,.2f}, "
        f"max DD ${curve.max_dd:,.2f}, "
        f"trough ${curve.min_cum:+,.2f}"
    )

    log("Computing streaks...")
    streaks = compute_streaks(enriched)
    log(
        f"  longest losing streak: {streaks.longest_loss} "
        f"(${streaks.longest_loss_dollars:+,.2f})"
    )

    log("Peak concurrent capital (sweep-line)...")
    peak_cap, peak_ts, peak_n = peak_concurrent_capital(enriched)
    log(
        f"  peak ${peak_cap:,.2f} at {peak_ts} ({peak_n} concurrent)"
    )

    log("Nightly P&L...")
    nightly = nightly_pnl(enriched)
    log(f"  {len(nightly)} active nights")

    log("Rendering report...")
    md = render_report(
        n_games=len(games), trades=enriched, curve=curve,
        streaks=streaks, peak_capital=peak_cap,
        peak_capital_ts=peak_ts, peak_concurrent=peak_n,
        nightly=nightly,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
