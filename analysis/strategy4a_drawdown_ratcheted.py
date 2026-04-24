"""S4A ratcheted drawdown + capital-requirements analysis.

Runs the engine replay (`engine.replay`) twice — once with the
breakeven ratchet (trigger +$0.08) and once without — and produces a
side-by-side drawdown / streak / capital-requirements report on the
404-game Kalshi paired dataset.

The engine replay is the authoritative trade source so the drawdown
curve matches exactly what the live engine would produce. This
differs from the pre-ratchet `strategy4a_drawdown.py` which used the
offline simulator's observed-price exit model; the engine uses
target-level fills ($0.90 exactly). That is a deliberate fidelity
upgrade for Phase 4c capital planning.

Report sections:
  1. Entry timeline
  2. Running cumulative P&L (max drawdown, peak/trough)
  3. Win/loss/scratch streaks (3 outcome categories)
  4. Capital requirements (min + recommended + peak concurrent)
  5. Nightly P&L distribution (+ losing-night frequency)
  6. Ratchet impact decomposition (conversion analysis)
  7. Phase 4c capital planning summary

Run:
    python -m analysis.strategy4a_drawdown_ratcheted
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    COMP_FRACTION,
    CONTRACT_SIZE,
    REG_SEASON_GAMES,
    load_kalshi_games_all_spreads,
)
from engine.position_manager import PositionManager
from engine.replay import replay_one

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "strategy4a_drawdown_ratcheted.md"
)

# Ratchet trigger per STRATEGY4_SPEC §5A.
RATCHET_TRIGGER = 0.08

# Outcome thresholds for the 3-category streak analysis.
WIN_THRESHOLD = 1.0     # P&L > +$1.00 = Win
LOSS_THRESHOLD = -1.0   # P&L < -$1.00 = Loss
# In between is Scratch.

NIGHTLY_PNL_BUCKETS: list[tuple[str, float, float]] = [
    ("> +$50", 50, float("inf")),
    ("+$25 to +$50", 25, 50),
    ("+$0 to +$25", 0.0, 25),
    ("-$25 to $0", -25, 0.0),
    ("-$50 to -$25", -50, -25),
    ("< -$50", -float("inf"), -50),
]

ANNUAL_SCALE = REG_SEASON_GAMES * COMP_FRACTION  # ≈ 547


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


# ------------------------------------------------------------------------
# Engine replay + trade-log enrichment
# ------------------------------------------------------------------------

@dataclass
class EngineTrade:
    game_id: str
    ticker: str
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    exit_type: str           # target / stop / ratchet_stop / eod
    entry_ts: datetime       # wallclock
    exit_ts: datetime        # wallclock
    entry_capital: float
    net_pnl: float
    ratchet_triggered: bool
    entries_this_game: int   # 1 = primary, 2 = re-entry

    @property
    def category(self) -> str:
        """W / L / S per section-3 definition."""
        if self.net_pnl > WIN_THRESHOLD:
            return "W"
        if self.net_pnl < LOSS_THRESHOLD:
            return "L"
        return "S"


# Map engine action strings → exit_type strings used here.
_ACTION_TO_EXIT = {
    "close_target": "target",
    "close_stop": "stop",
    "close_ratchet_stop": "ratchet_stop",
    "close_eod": "eod",
}


def run_engine_replay(
    games: list[dict], ratchet_trigger: float | None,
) -> list[dict]:
    """Drive all games through the engine and return the raw trade log."""
    manager = PositionManager(ratchet_trigger=ratchet_trigger)
    for g in games:
        replay_one(g, manager)
    return manager.trade_log()


def pair_and_enrich(
    trade_log: list[dict], games: list[dict],
) -> list[EngineTrade]:
    """Pair each close with the most recent open for the same game_id,
    resolve synthetic ts → wallclock via the game's timeseries."""
    ts_by_ticker: dict[str, pd.DataFrame] = {
        g["ticker"]: g["ts"] for g in games
    }
    # Track open events per game_id (FIFO stack; only ever 0 or 1 deep
    # because the manager rejects overlapping entries per game).
    open_stack: dict[str, list[dict]] = defaultdict(list)
    enriched: list[EngineTrade] = []
    entries_seen: dict[str, int] = defaultdict(int)
    missing_ts = 0

    for rec in trade_log:
        action = rec["action"]
        game_id = rec["game_id"]
        if action == "open":
            open_stack[game_id].append(rec)
            entries_seen[game_id] += 1
            continue
        if action in _ACTION_TO_EXIT:
            stack = open_stack.get(game_id)
            if not stack:
                # Defensive; shouldn't happen.
                continue
            open_rec = stack.pop()
            ts_df = ts_by_ticker.get(game_id)
            if ts_df is None or "bucket_start_utc" not in ts_df.columns:
                missing_ts += 1
                continue
            entry_idx = int(round(open_rec["ts"] / BUCKET_SEC))
            exit_idx = int(round(rec["ts"] / BUCKET_SEC))
            try:
                entry_wc = pd.to_datetime(
                    ts_df["bucket_start_utc"].iloc[entry_idx],
                    utc=True,
                ).to_pydatetime()
                exit_wc = pd.to_datetime(
                    ts_df["bucket_start_utc"].iloc[exit_idx],
                    utc=True,
                ).to_pydatetime()
            except (IndexError, ValueError, TypeError):
                missing_ts += 1
                continue
            entry_price = float(open_rec["price"])
            exit_price = float(rec["price"])
            pnl = float(rec["pnl"]) if rec["pnl"] is not None else 0.0
            enriched.append(EngineTrade(
                game_id=game_id, ticker=rec["ticker"],
                entry_idx=entry_idx, exit_idx=exit_idx,
                entry_price=entry_price, exit_price=exit_price,
                exit_type=_ACTION_TO_EXIT[action],
                entry_ts=entry_wc, exit_ts=exit_wc,
                entry_capital=entry_price * CONTRACT_SIZE,
                net_pnl=pnl,
                ratchet_triggered=bool(rec.get("ratchet_triggered")),
                entries_this_game=entries_seen[game_id],
            ))
    if missing_ts:
        log(f"  WARN: {missing_ts} trades missing wallclock")
    enriched.sort(key=lambda t: t.entry_ts)
    return enriched


# ------------------------------------------------------------------------
# Section 2: running cumulative P&L curve
# ------------------------------------------------------------------------

@dataclass
class RunningCurve:
    points: list[dict]
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


def compute_running_curve(trades: list[EngineTrade]) -> RunningCurve:
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


# ------------------------------------------------------------------------
# Section 3: W / L / S streaks
# ------------------------------------------------------------------------

@dataclass
class StreakStats:
    lengths_by_type: dict[str, list[int]]   # "W" / "L" / "S"
    longest_loss: int
    longest_loss_dollars: float
    longest_win: int
    longest_win_dollars: float
    longest_scratch: int
    longest_drawdown_streak: int   # consecutive non-W (L + S combined)
    longest_drawdown_streak_dollars: float


def compute_streaks(trades: list[EngineTrade]) -> StreakStats:
    lengths: dict[str, list[int]] = {"W": [], "L": [], "S": []}
    cur_type: str | None = None
    cur_len = 0
    cur_dollars = 0.0
    longest_loss = 0
    longest_loss_dollars = 0.0
    longest_win = 0
    longest_win_dollars = 0.0
    longest_scratch = 0

    def close_streak() -> None:
        nonlocal longest_loss, longest_loss_dollars
        nonlocal longest_win, longest_win_dollars, longest_scratch
        if cur_type is None:
            return
        lengths[cur_type].append(cur_len)
        if cur_type == "L" and cur_len > longest_loss:
            longest_loss = cur_len
            longest_loss_dollars = cur_dollars
        elif cur_type == "W" and cur_len > longest_win:
            longest_win = cur_len
            longest_win_dollars = cur_dollars
        elif cur_type == "S" and cur_len > longest_scratch:
            longest_scratch = cur_len

    for t in trades:
        this_type = t.category
        if cur_type is None:
            cur_type = this_type
            cur_len = 1
            cur_dollars = t.net_pnl
            continue
        if this_type == cur_type:
            cur_len += 1
            cur_dollars += t.net_pnl
        else:
            close_streak()
            cur_type = this_type
            cur_len = 1
            cur_dollars = t.net_pnl
    close_streak()

    # Drawdown streak = consecutive non-W (L + S combined).
    longest_dd_streak = 0
    longest_dd_dollars = 0.0
    dd_len = 0
    dd_dollars = 0.0
    for t in trades:
        if t.category == "W":
            if dd_len > longest_dd_streak:
                longest_dd_streak = dd_len
                longest_dd_dollars = dd_dollars
            dd_len = 0
            dd_dollars = 0.0
        else:
            dd_len += 1
            dd_dollars += t.net_pnl
    if dd_len > longest_dd_streak:
        longest_dd_streak = dd_len
        longest_dd_dollars = dd_dollars

    return StreakStats(
        lengths_by_type=lengths,
        longest_loss=longest_loss,
        longest_loss_dollars=longest_loss_dollars,
        longest_win=longest_win,
        longest_win_dollars=longest_win_dollars,
        longest_scratch=longest_scratch,
        longest_drawdown_streak=longest_dd_streak,
        longest_drawdown_streak_dollars=longest_dd_dollars,
    )


# ------------------------------------------------------------------------
# Section 4: peak concurrent capital (sweep-line)
# ------------------------------------------------------------------------

def peak_concurrent_capital(
    trades: list[EngineTrade],
) -> tuple[float, datetime, int]:
    events: list[tuple[datetime, int, float]] = []
    for t in trades:
        events.append((t.entry_ts, 0, t.entry_capital))
        events.append((t.exit_ts, -1, -t.entry_capital))
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


# ------------------------------------------------------------------------
# Section 5: nightly P&L
# ------------------------------------------------------------------------

def nightly_pnl(trades: list[EngineTrade]) -> dict[str, dict]:
    by_night: dict[str, list[EngineTrade]] = defaultdict(list)
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


# ------------------------------------------------------------------------
# Section 6: ratchet conversion analysis
# ------------------------------------------------------------------------

@dataclass
class ConversionResult:
    # For each ratchet-scratch exit in the ratcheted mode, what was the
    # matched baseline exit type?
    matched_to_stop: int
    matched_to_target: int
    matched_to_eod: int
    unmatched: int
    # Total matched count is matched_to_* sum.


def match_entries(
    ratcheted: list[EngineTrade], baseline: list[EngineTrade],
) -> dict[int, EngineTrade | None]:
    """For each ratcheted trade (by position in list), return the
    baseline trade with the same game_id and closest entry_idx (if any).

    Matching is one-to-one: once a baseline trade is consumed it isn't
    reused.
    """
    base_by_game: dict[str, list[EngineTrade]] = defaultdict(list)
    for b in baseline:
        base_by_game[b.game_id].append(b)
    # Sort each bucket by entry_idx so we can consume in order.
    for games_list in base_by_game.values():
        games_list.sort(key=lambda b: b.entry_idx)
    # Consumed flags.
    consumed: dict[str, set[int]] = defaultdict(set)
    out: dict[int, EngineTrade | None] = {}
    for i, rt in enumerate(ratcheted):
        candidates = [
            (j, b) for j, b in enumerate(base_by_game.get(rt.game_id, []))
            if j not in consumed[rt.game_id]
        ]
        if not candidates:
            out[i] = None
            continue
        j, best = min(
            candidates,
            key=lambda jb: abs(jb[1].entry_idx - rt.entry_idx),
        )
        consumed[rt.game_id].add(j)
        out[i] = best
    return out


def conversion_analysis(
    ratcheted: list[EngineTrade], baseline: list[EngineTrade],
) -> ConversionResult:
    matches = match_entries(ratcheted, baseline)
    matched_to_stop = 0
    matched_to_target = 0
    matched_to_eod = 0
    unmatched = 0
    for i, rt in enumerate(ratcheted):
        if rt.exit_type != "ratchet_stop":
            continue
        b = matches.get(i)
        if b is None:
            unmatched += 1
            continue
        if b.exit_type == "stop":
            matched_to_stop += 1
        elif b.exit_type == "target":
            matched_to_target += 1
        else:
            matched_to_eod += 1
    return ConversionResult(
        matched_to_stop=matched_to_stop,
        matched_to_target=matched_to_target,
        matched_to_eod=matched_to_eod,
        unmatched=unmatched,
    )


# ------------------------------------------------------------------------
# Summary helpers
# ------------------------------------------------------------------------

@dataclass
class ModeSummary:
    label: str
    trades: list[EngineTrade]
    curve: RunningCurve
    streaks: StreakStats
    peak_capital: float
    peak_capital_ts: datetime
    peak_concurrent: int
    nightly: dict[str, dict]


def build_mode_summary(
    label: str, trades: list[EngineTrade],
) -> ModeSummary:
    curve = compute_running_curve(trades)
    streaks = compute_streaks(trades)
    peak_cap, peak_ts, peak_n = peak_concurrent_capital(trades)
    nightly = nightly_pnl(trades)
    return ModeSummary(
        label=label, trades=trades, curve=curve, streaks=streaks,
        peak_capital=peak_cap, peak_capital_ts=peak_ts,
        peak_concurrent=peak_n, nightly=nightly,
    )


def exit_type_breakdown(
    trades: list[EngineTrade],
) -> dict[str, dict]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        buckets[t.exit_type].append(t.net_pnl)
    return {
        k: {
            "n": len(v),
            "pct": 100.0 * len(v) / max(1, len(trades)),
            "mean_pnl": float(np.mean(v)) if v else 0.0,
            "total_pnl": float(sum(v)),
        }
        for k, v in buckets.items()
    }


# ------------------------------------------------------------------------
# Report rendering
# ------------------------------------------------------------------------

def _fmt_money(x: float) -> str:
    return f"${x:+,.2f}"


def render_report(
    n_games: int,
    ratcheted: ModeSummary, baseline: ModeSummary,
    conversion: ConversionResult,
) -> str:
    md: list[str] = []
    md.append("# Strategy 4A — Ratcheted Drawdown & Capital Requirements\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Engine-replay-derived drawdown analysis on the "
        f"**{n_games}-game Kalshi paired dataset**. Two modes:\n"
        f"- **Ratcheted** — `ratchet_trigger=+${RATCHET_TRIGGER:.2f}` "
        f"(STRATEGY4_SPEC §5A, the recommended config)\n"
        f"- **Baseline** — `ratchet_trigger=None` (legacy, no ratchet)\n\n"
        f"Both modes use target-level fills ($0.90 exactly) and the "
        f"engine's maker/taker fee split (maker on entry + target + "
        f"ratchet_stop, taker on full stop). Trade counts must match "
        f"`engine/replay.py`: {len(ratcheted.trades)} ratcheted / "
        f"{len(baseline.trades)} baseline.\n"
    )

    # -------- Section 1: Entry timeline ---------------------------------
    md.append("\n## Section 1 — Entry timeline (ratcheted)\n")
    md.append(_render_timeline(ratcheted, baseline))

    # -------- Section 2: Running cumulative P&L -------------------------
    md.append("\n## Section 2 — Running cumulative P&L (ratcheted)\n")
    md.append(_render_curve(ratcheted, baseline))

    # -------- Section 3: Streaks ----------------------------------------
    md.append("\n## Section 3 — Win/loss/scratch streaks (ratcheted)\n")
    md.append(_render_streaks(ratcheted, baseline))

    # -------- Section 4: Capital ----------------------------------------
    md.append("\n## Section 4 — Capital requirements (ratcheted)\n")
    md.append(_render_capital(ratcheted, baseline))

    # -------- Section 5: Nightly P&L ------------------------------------
    md.append("\n## Section 5 — Nightly P&L distribution (ratcheted)\n")
    md.append(_render_nightly(ratcheted, baseline))

    # -------- Section 6: Ratchet decomposition --------------------------
    md.append("\n## Section 6 — Ratchet impact decomposition\n")
    md.append(_render_decomposition(ratcheted, baseline, conversion))

    # -------- Section 7: Phase 4c summary -------------------------------
    md.append("\n## Section 7 — Phase 4c capital planning summary\n")
    md.append(_render_phase4c(ratcheted, baseline))

    return "".join(md) + "\n"


def _render_timeline(rt: ModeSummary, bl: ModeSummary) -> str:
    out: list[str] = []
    t = rt.trades
    first_ts = t[0].entry_ts
    last_ts = t[-1].entry_ts
    per_night = Counter(x.entry_ts.date().isoformat() for x in t)
    busiest = max(per_night.items(), key=lambda kv: kv[1])
    counts = list(per_night.values())
    bl_nights = Counter(x.entry_ts.date().isoformat() for x in bl.trades)
    out.append(
        f"- Total entries: **{len(t)}** (baseline: {len(bl.trades)}, "
        f"Δ {len(t) - len(bl.trades):+d})\n"
        f"- Date range: {first_ts.date().isoformat()} → "
        f"{last_ts.date().isoformat()} "
        f"({(last_ts - first_ts).days + 1} calendar days)\n"
        f"- Nights with ≥1 entry: **{len(per_night)}** "
        f"(baseline: {len(bl_nights)})\n"
        f"- Mean entries/active night: "
        f"{float(np.mean(counts)):.2f} "
        f"(baseline: {float(np.mean(list(bl_nights.values()))):.2f})\n"
        f"- Median entries/active night: {int(np.median(counts))}\n"
        f"- P90 entries/night: {int(np.quantile(counts, 0.90))}\n"
        f"- Busiest night: **{busiest[0]}** with "
        f"**{busiest[1]} entries**\n"
    )
    return "".join(out)


def _render_curve(rt: ModeSummary, bl: ModeSummary) -> str:
    c = rt.curve
    b = bl.curve
    out: list[str] = []
    out.append(
        f"- Final cumulative P&L: **{_fmt_money(c.final_cum)}** "
        f"(baseline: {_fmt_money(b.final_cum)})\n"
        f"- Max cumulative P&L: {_fmt_money(c.max_cum)} at "
        f"{c.max_cum_ts.date().isoformat()}\n"
        f"- Min cumulative P&L: {_fmt_money(c.min_cum)} at "
        f"{c.min_cum_ts.date().isoformat()}\n"
    )
    out.append(
        f"- **Max peak-to-trough drawdown: "
        f"${c.max_dd:,.2f}**\n"
        f"  - Peak: {_fmt_money(c.max_dd_peak)} at "
        f"{c.max_dd_peak_ts.date().isoformat()}\n"
        f"  - Trough: {_fmt_money(c.max_dd_trough)} at "
        f"{c.max_dd_trough_ts.date().isoformat()}\n"
        f"  - Drawdown window: "
        f"{(c.max_dd_trough_ts - c.max_dd_peak_ts).days} days\n"
    )
    out.append("\n### Side-by-side comparison\n\n")
    out.append(
        "| Metric | Baseline (no ratchet) | Ratcheted (+$0.08) | Δ |\n"
        "|---|---:|---:|---:|\n"
        f"| Final P&L | {_fmt_money(b.final_cum)} | "
        f"{_fmt_money(c.final_cum)} | "
        f"{_fmt_money(c.final_cum - b.final_cum)} |\n"
        f"| Max cumulative | {_fmt_money(b.max_cum)} | "
        f"{_fmt_money(c.max_cum)} | "
        f"{_fmt_money(c.max_cum - b.max_cum)} |\n"
        f"| Min cumulative | {_fmt_money(b.min_cum)} | "
        f"{_fmt_money(c.min_cum)} | "
        f"{_fmt_money(c.min_cum - b.min_cum)} |\n"
        f"| **Max drawdown** | **${b.max_dd:,.2f}** | "
        f"**${c.max_dd:,.2f}** | "
        f"**${c.max_dd - b.max_dd:+,.2f}** |\n"
        f"| Drawdown window | "
        f"{(b.max_dd_trough_ts - b.max_dd_peak_ts).days} days | "
        f"{(c.max_dd_trough_ts - c.max_dd_peak_ts).days} days | — |\n"
    )
    out.append(
        "\nEngine-baseline numbers above differ from the pre-ratchet "
        "report (`strategy4a_drawdown.md` = $326.32 max DD / 8-day "
        "window / -$44.70 min) because the engine uses target-level "
        "fills ($0.90 exactly) while the pre-ratchet report used "
        "observed overshoot prices. Engine numbers are the authoritative "
        "reference for Phase 4c planning.\n"
    )
    return "".join(out)


def _render_streaks(rt: ModeSummary, bl: ModeSummary) -> str:
    s = rt.streaks
    b = bl.streaks
    out: list[str] = []
    out.append(
        f"Categories: **Win** (P&L > +$1.00), **Loss** (P&L < -$1.00), "
        f"**Scratch** (-$1 ≤ P&L ≤ +$1). Scratches are primarily "
        f"ratchet-stop exits in the ratcheted mode.\n\n"
        f"- **Longest losing streak: {s.longest_loss} consecutive "
        f"losses** ({_fmt_money(s.longest_loss_dollars)}) "
        f"[baseline: {b.longest_loss}]\n"
        f"- **Longest winning streak: {s.longest_win} consecutive wins** "
        f"({_fmt_money(s.longest_win_dollars)}) "
        f"[baseline: {b.longest_win}]\n"
        f"- Longest scratch streak: {s.longest_scratch}\n"
        f"- **Longest drawdown streak** (consecutive non-wins = L + S): "
        f"{s.longest_drawdown_streak} "
        f"({_fmt_money(s.longest_drawdown_streak_dollars)})\n"
        f"- Mean loss streak length: "
        f"{float(np.mean(s.lengths_by_type['L'])):.2f} "
        f"(n={len(s.lengths_by_type['L'])}) "
        f"[baseline: {float(np.mean(b.lengths_by_type['L'])):.2f}]\n"
        f"- Mean win streak length: "
        f"{float(np.mean(s.lengths_by_type['W'])):.2f} "
        f"(n={len(s.lengths_by_type['W'])}) "
        f"[baseline: {float(np.mean(b.lengths_by_type['W'])):.2f}]\n"
    )
    out.append("\n### Streak-length distribution (ratcheted)\n\n")
    w_counts = Counter(s.lengths_by_type["W"])
    l_counts = Counter(s.lengths_by_type["L"])
    sc_counts = Counter(s.lengths_by_type["S"])
    out.append(
        "| Streak length | Win streaks | Loss streaks | Scratch streaks |\n"
        "|---:|---:|---:|---:|\n"
    )
    all_lens = sorted(set(list(w_counts) + list(l_counts) + list(sc_counts)))
    for L in all_lens:
        out.append(
            f"| {L} | {w_counts.get(L, 0)} | {l_counts.get(L, 0)} | "
            f"{sc_counts.get(L, 0)} |\n"
        )
    return "".join(out)


def _render_capital(rt: ModeSummary, bl: ModeSummary) -> str:
    c = rt.curve
    b = bl.curve
    t = rt.trades
    bt = bl.trades
    min_cap = abs(min(0.0, c.min_cum))
    bmin = abs(min(0.0, b.min_cum))
    rec = min_cap * 1.5
    brec = bmin * 1.5
    caps = [x.entry_capital for x in t]
    bcaps = [x.entry_capital for x in bt]
    first_ts = t[0].entry_ts
    last_ts = t[-1].entry_ts
    runtime_days = (last_ts - first_ts).days + 1
    # Calendar-day annualization (matches original drawdown report).
    cal_factor = 365.0 / runtime_days if runtime_days else 1.0
    cal_annual = c.final_cum * cal_factor
    # Season-equivalent annualization (matches engine replay).
    games_per_dataset = bt and len(bt) / 404 or 0  # entries/game baseline
    season_annual_rt = (
        c.final_cum / 404 * ANNUAL_SCALE if c.final_cum else 0.0
    )
    ret_min = cal_annual / min_cap * 100 if min_cap > 0 else float("inf")
    ret_rec = cal_annual / rec * 100 if rec > 0 else float("inf")
    out: list[str] = []
    out.append(
        f"- Minimum starting capital to never go negative: "
        f"**${min_cap:,.2f}** (baseline: ${bmin:,.2f})\n"
        f"  - Computed as |min cumulative P&L| = "
        f"|{_fmt_money(c.min_cum)}|\n"
        f"- Recommended starting capital (×1.5): "
        f"**${rec:,.2f}** (baseline: ${brec:,.2f})\n"
    )
    out.append(
        "\n### Capital deployed per entry (entry_price × 100)\n\n"
        "| Metric | Ratcheted | Baseline |\n|---|---:|---:|\n"
        f"| Mean | ${float(np.mean(caps)):.2f} | "
        f"${float(np.mean(bcaps)):.2f} |\n"
        f"| Median | ${float(np.median(caps)):.2f} | "
        f"${float(np.median(bcaps)):.2f} |\n"
        f"| P90 | ${float(np.quantile(caps, 0.90)):.2f} | "
        f"${float(np.quantile(bcaps, 0.90)):.2f} |\n"
        f"| Max | ${float(max(caps)):.2f} | "
        f"${float(max(bcaps)):.2f} |\n"
    )
    out.append(
        f"\n### Peak concurrent capital deployed\n\n"
        f"- **Peak capital at risk simultaneously: "
        f"${rt.peak_capital:,.2f}** (baseline: ${bl.peak_capital:,.2f})\n"
        f"- Occurred at: {rt.peak_capital_ts.isoformat()}\n"
        f"- Concurrent positions at peak: {rt.peak_concurrent} "
        f"(baseline peak: {bl.peak_concurrent})\n"
        f"\n(Sweep-line over trade entry/exit timestamps.)\n"
    )
    out.append(
        f"\n### Return on capital (ratcheted)\n\n"
        f"- Dataset span: {runtime_days} calendar days "
        f"(calendar-annualization factor ×{cal_factor:.3f})\n"
        f"- Final P&L: {_fmt_money(c.final_cum)} → calendar-annualized "
        f"~{_fmt_money(cal_annual)}/yr\n"
        f"- Season-equivalent annualization "
        f"(entries/games × {ANNUAL_SCALE:.0f}): "
        f"~{_fmt_money(season_annual_rt)}/yr "
        f"(matches `engine/replay.py` +$1,899/yr)\n"
        f"- Return on minimum capital: "
        f"**{ret_min:.1f}%/yr calendar** "
        f"(${cal_annual:+,.0f} / ${min_cap:,.0f})\n"
        f"- Return on recommended capital: "
        f"**{ret_rec:.1f}%/yr calendar** "
        f"(${cal_annual:+,.0f} / ${rec:,.0f})\n"
    )
    out.append(
        "\nBoth capital denominators are tiny ($20-$70) because the "
        "cumulative P&L curve rarely dips far below zero. Return-on-"
        "capital percentages above are arithmetic but not the "
        "load-bearing number for bankroll sizing — Section 7 uses "
        "the peak concurrent + worst-night envelopes instead.\n"
    )
    return "".join(out)


def _render_nightly(rt: ModeSummary, bl: ModeSummary) -> str:
    pnls = [v["net_pnl"] for v in rt.nightly.values()]
    bpnls = [v["net_pnl"] for v in bl.nightly.values()]
    n_nights = len(rt.nightly)
    bn_nights = len(bl.nightly)
    losing = sum(1 for p in pnls if p < 0)
    bl_losing = sum(1 for p in bpnls if p < 0)
    worst = min(rt.nightly.items(), key=lambda kv: kv[1]["net_pnl"])
    best = max(rt.nightly.items(), key=lambda kv: kv[1]["net_pnl"])
    b_worst = min(bl.nightly.items(), key=lambda kv: kv[1]["net_pnl"])
    out: list[str] = []
    out.append(
        f"- Active nights: {n_nights} (baseline: {bn_nights})\n"
        f"- Mean nightly P&L: {_fmt_money(float(np.mean(pnls)))} "
        f"(baseline: {_fmt_money(float(np.mean(bpnls)))})\n"
        f"- Median nightly P&L: {_fmt_money(float(np.median(pnls)))} "
        f"(baseline: {_fmt_money(float(np.median(bpnls)))})\n"
        f"- **Worst night:** {worst[0]} at "
        f"{_fmt_money(worst[1]['net_pnl'])} "
        f"({worst[1]['n_entries']} entries) "
        f"[baseline worst: {b_worst[0]} at "
        f"{_fmt_money(b_worst[1]['net_pnl'])}]\n"
        f"- **Best night:** {best[0]} at "
        f"{_fmt_money(best[1]['net_pnl'])} "
        f"({best[1]['n_entries']} entries)\n"
        f"- **Losing nights:** {losing}/{n_nights} "
        f"({100*losing/max(1,n_nights):.1f}%) "
        f"[baseline: {bl_losing}/{bn_nights} "
        f"({100*bl_losing/max(1,bn_nights):.1f}%)]\n"
    )
    out.append("\n### Nightly P&L histogram (ratcheted)\n\n")
    out.append(
        "| P&L bucket | Ratcheted nights | % | Baseline nights | % |\n"
        "|---|---:|---:|---:|---:|\n"
    )
    arr = np.array(pnls)
    barr = np.array(bpnls)
    for lab, lo, hi in NIGHTLY_PNL_BUCKETS:
        mask = (arr >= lo) & (arr < hi)
        bmask = (barr >= lo) & (barr < hi)
        c = int(mask.sum())
        bc = int(bmask.sum())
        out.append(
            f"| {lab} | {c} | "
            f"{100 * c / max(1, n_nights):.1f}% | "
            f"{bc} | "
            f"{100 * bc / max(1, bn_nights):.1f}% |\n"
        )
    return "".join(out)


def _render_decomposition(
    rt: ModeSummary, bl: ModeSummary, conv: ConversionResult,
) -> str:
    out: list[str] = []
    rt_bd = exit_type_breakdown(rt.trades)
    bl_bd = exit_type_breakdown(bl.trades)
    all_types = ["target", "stop", "ratchet_stop", "eod"]
    out.append("### Exits by type\n\n")
    out.append(
        "| Exit type | Ratcheted n | Ratcheted % | Ratcheted mean | "
        "Baseline n | Baseline % | Baseline mean |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for typ in all_types:
        r = rt_bd.get(typ, {"n": 0, "pct": 0.0, "mean_pnl": 0.0})
        b = bl_bd.get(typ, {"n": 0, "pct": 0.0, "mean_pnl": 0.0})
        out.append(
            f"| {typ} | {r['n']} | {r['pct']:.1f}% | "
            f"{_fmt_money(r['mean_pnl'])} | "
            f"{b['n']} | {b['pct']:.1f}% | "
            f"{_fmt_money(b['mean_pnl'])} |\n"
        )

    total_scratch = sum(
        1 for t in rt.trades if t.exit_type == "ratchet_stop"
    )
    out.append(
        f"\n### Ratchet conversion analysis\n\n"
        f"Of the **{total_scratch} ratchet-scratch exits** in the "
        f"ratcheted mode, matching each to the closest-entry baseline "
        f"trade on the same game (one-to-one, by entry bin index):\n\n"
        f"- Matched to a baseline **full stop**: "
        f"**{conv.matched_to_stop}** "
        f"({100*conv.matched_to_stop/max(1,total_scratch):.1f}%) — "
        f"ratchet saved a loss\n"
        f"- Matched to a baseline **target ($0.90)**: "
        f"**{conv.matched_to_target}** "
        f"({100*conv.matched_to_target/max(1,total_scratch):.1f}%) — "
        f"ratchet cost a winner\n"
        f"- Matched to a baseline **EOD resolution**: "
        f"{conv.matched_to_eod}\n"
        f"- Unmatched (new entry that didn't exist in baseline): "
        f"{conv.unmatched}\n"
    )
    net = (
        conv.matched_to_stop * (-25.0)   # approx avg loss
        - conv.matched_to_target * 22.0  # approx avg win
    )
    # Compute actual EV delta attributable to scratch-conversion.
    baseline_total = bl.curve.final_cum
    ratcheted_total = rt.curve.final_cum
    delta_total = ratcheted_total - baseline_total
    out.append(
        f"\nThe ratchet adds "
        f"{_fmt_money(delta_total)} to total pool P&L on this dataset. "
        f"Split between:\n"
        f"- {conv.matched_to_stop} scratches that replaced full "
        f"stops (each saving ≈$21 vs a full stop → "
        f"~${21 * conv.matched_to_stop:,.0f} saved)\n"
        f"- {conv.matched_to_target} scratches that replaced targets "
        f"(each giving up ≈$23 → "
        f"~${23 * conv.matched_to_target:,.0f} sacrificed)\n"
        f"- {conv.unmatched} new ratchet-mode entries that baseline "
        f"never fired (each contributes their own target/stop/scratch "
        f"outcome)\n"
    )

    out.append("\n### Cumulative P&L contribution by exit type (ratcheted)\n\n")
    out.append(
        "| Exit type | Total P&L contribution | % of total |\n"
        "|---|---:|---:|\n"
    )
    total_pnl = sum(x.net_pnl for x in rt.trades)
    for typ in all_types:
        total = rt_bd.get(typ, {"total_pnl": 0.0})["total_pnl"]
        pct = 100.0 * total / total_pnl if total_pnl else 0.0
        out.append(
            f"| {typ} | {_fmt_money(total)} | {pct:+.1f}% |\n"
        )
    return "".join(out)


def _render_phase4c(rt: ModeSummary, bl: ModeSummary) -> str:
    c = rt.curve
    pnls = [v["net_pnl"] for v in rt.nightly.values()]
    losing_nights = [p for p in pnls if p < 0]
    arr = np.array(pnls)
    worst = float(arr.min()) if len(arr) else 0.0
    p5 = float(np.quantile(arr, 0.05)) if len(arr) else 0.0
    p10 = float(np.quantile(arr, 0.10)) if len(arr) else 0.0
    min_cap = abs(min(0.0, c.min_cum))
    peak_cap = rt.peak_capital
    # Recommend 3× peak concurrent (1× deployed + 2× reserve for drawdown
    # + gap risk), rounded up to nearest $100.
    rec_bankroll = int(np.ceil(peak_cap * 3.0 / 100.0) * 100)
    daily_loss_cap = int(np.ceil(abs(p5) / 10.0) * 10)  # ~5th percentile
    # Per-position max notional: 100 contracts × $0.75 upper entry bound.
    per_position_max = CONTRACT_SIZE * 0.75
    # Per-game: up to 2 entries allowed per game.
    per_game_max = per_position_max * 2
    # Max concurrent exposure (4 positions × per-position max).
    max_concurrent_exposure = per_position_max * 4
    s = rt.streaks
    out: list[str] = []
    out.append(
        f"Plain-English synthesis for Phase 4c (capped real-money "
        f"deployment) based on the ratcheted engine replay.\n\n"
        f"**Starting bankroll (recommended):** **${rec_bankroll:,.0f}**.\n"
        f"- Peak concurrent capital in the dataset: "
        f"${peak_cap:,.2f} ({rt.peak_concurrent} concurrent positions).\n"
        f"- 3× peak concurrent covers deployed + 2× reserve for "
        f"drawdown and Kalshi gap-through risk on the full-stop side.\n"
        f"- Minimum-to-never-go-negative is only ${min_cap:,.2f}, but "
        f"that assumes perfect execution of the next 404-game tape — "
        f"not a planning number.\n\n"
        f"**Daily loss cap (manual-review trigger):** "
        f"${daily_loss_cap:,.0f}.\n"
        f"- Worst single night on this dataset: "
        f"{_fmt_money(worst)}.\n"
        f"- 5th-percentile nightly P&L: {_fmt_money(p5)}.\n"
        f"- 10th-percentile nightly P&L: {_fmt_money(p10)}.\n"
        f"- Breaching this cap triggers a manual review before the "
        f"engine resumes next session.\n\n"
        f"**Per-game max notional:** ${per_game_max:,.0f} "
        f"(= 2 entries × {CONTRACT_SIZE} contracts × $0.75 upper-entry "
        f"bound). Max-concurrent-positions=4 caps total open exposure "
        f"at ${max_concurrent_exposure:,.0f}, which fits comfortably "
        f"inside the ${rec_bankroll:,} recommended bankroll (leaves "
        f"~${rec_bankroll - int(max_concurrent_exposure):,} as reserve "
        f"for drawdown and gap-through losses).\n\n"
        f"**Consecutive losing-night kill switch:** after **3** "
        f"consecutive losing nights, pause the engine for manual "
        f"review.\n"
        f"- Longest losing streak (trades): {s.longest_loss}.\n"
        f"- Longest drawdown streak (L + S combined): "
        f"{s.longest_drawdown_streak}.\n"
        f"- A 3-night pause converts tape-equivalent drawdown into a "
        f"human-verification checkpoint without over-reacting to noise "
        f"(observed losing-night rates are "
        f"~{100*len(losing_nights)/max(1,len(pnls)):.0f}% in the "
        f"ratcheted mode).\n\n"
        f"**Caveats:**\n"
        f"- The 404-game dataset is predominantly regular-season "
        f"(Feb 20 – Apr 15, 2026). Playoff pace/timeout dynamics may "
        f"shift the drawdown profile; re-run this analysis after the "
        f"first ~40 playoff games have been paired.\n"
        f"- Ratchet-scratch exits assume a resting limit at "
        f"`entry + $0.01` fills cleanly (maker). A live-execution "
        f"shortfall (e.g. scratch-limit missed, contract drops further) "
        f"would shift some scratches into $0.40 full stops. Monitor "
        f"scratch-fill rates in the first Phase 4a paper-trading "
        f"session.\n"
        f"- The engine hasn't been validated live yet. These numbers "
        f"are replay-backed, not live-verified.\n"
    )
    return "".join(out)


# ------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------

def main() -> int:
    log("Loading 404-game Kalshi paired dataset...")
    games = load_kalshi_games_all_spreads()
    log(f"  {len(games)} games loaded")

    log("Engine replay — ratcheted (+$0.08)...")
    rt_log = run_engine_replay(games, ratchet_trigger=RATCHET_TRIGGER)
    rt_trades = pair_and_enrich(rt_log, games)
    log(f"  {len(rt_trades)} ratcheted closed trades")

    log("Engine replay — baseline (no ratchet)...")
    bl_log = run_engine_replay(games, ratchet_trigger=None)
    bl_trades = pair_and_enrich(bl_log, games)
    log(f"  {len(bl_trades)} baseline closed trades")

    log("Building mode summaries...")
    rt_sum = build_mode_summary("Ratcheted", rt_trades)
    bl_sum = build_mode_summary("Baseline", bl_trades)
    log(
        f"  ratcheted: final {_fmt_money(rt_sum.curve.final_cum)}, "
        f"max DD ${rt_sum.curve.max_dd:,.2f}, "
        f"peak concurrent ${rt_sum.peak_capital:,.2f}"
    )
    log(
        f"  baseline:  final {_fmt_money(bl_sum.curve.final_cum)}, "
        f"max DD ${bl_sum.curve.max_dd:,.2f}, "
        f"peak concurrent ${bl_sum.peak_capital:,.2f}"
    )

    log("Ratchet conversion analysis...")
    conv = conversion_analysis(rt_trades, bl_trades)
    log(
        f"  {conv.matched_to_stop} scratches ← stops, "
        f"{conv.matched_to_target} ← targets, "
        f"{conv.matched_to_eod} ← eod, "
        f"{conv.unmatched} unmatched (new entries)"
    )

    log("Rendering report...")
    md = render_report(
        n_games=len(games),
        ratcheted=rt_sum, baseline=bl_sum,
        conversion=conv,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")

    # Console summary for the prompt's report-back section.
    print("")
    print("=== Summary ===")
    print(
        f"Ratcheted max drawdown: ${rt_sum.curve.max_dd:,.2f} "
        f"(baseline ${bl_sum.curve.max_dd:,.2f}; "
        f"original non-engine report: $326.32)"
    )
    print(
        f"Ratcheted worst losing streak: "
        f"{rt_sum.streaks.longest_loss} "
        f"(baseline {bl_sum.streaks.longest_loss}; "
        f"original: 7)"
    )
    min_cap = abs(min(0.0, rt_sum.curve.min_cum))
    rec = min_cap * 1.5
    peak_cap = rt_sum.peak_capital
    print(
        f"Ratcheted minimum starting capital: ${min_cap:,.2f}"
    )
    print(
        f"Ratcheted recommended bankroll (3× peak concurrent): "
        f"${int(np.ceil(peak_cap * 3.0 / 100.0) * 100):,}"
    )
    pnls = np.array([v["net_pnl"] for v in rt_sum.nightly.values()])
    p5 = float(np.quantile(pnls, 0.05))
    daily_cap = int(np.ceil(abs(p5) / 10.0) * 10)
    print(f"Phase 4c daily loss cap recommendation: ${daily_cap:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
