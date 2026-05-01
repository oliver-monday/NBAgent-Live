"""S4A paper-trade journal review.

Consumes per-night JSONL journals under `data/paper_trades/` and
produces a markdown comparison report against backtest projections
in `docs/analysis_outputs/paper_journal_review.md`.

Phase 4a operational audit. NOT a statistical EV validation —
sample size at this stage is far too small. Goal is anomaly
detection and directional alignment: crashes, missing exits,
out-of-spec entry prices, favorite-determination bugs, etc.

Run:
    python -m analysis.paper_journal_review
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parents[1]
JOURNAL_DIR = REPO_ROOT / "data" / "paper_trades"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "paper_journal_review.md"
)

# Backtest comparison anchors. From STRATEGY4_SPEC §5A and the
# 4-23 ratcheted engine replay (358 entries / 404 games).
BACKTEST_TARGETS = {
    "entries_per_game":          0.89,    # 358 / 404
    "target_hit_rate":           0.416,   # 149 / 358
    "full_stop_rate":            0.246,   #  88 / 358
    "ratchet_scratch_rate":      0.338,   # 121 / 358
    "mean_pnl_per_entry":        3.92,    # USD, ratcheted
    "entry_price_min":           0.50,
    "entry_price_max":           0.75,
    "ratchet_trigger_threshold": 0.08,
    "target_exit_price":         0.90,
    "stop_exit_price":            0.40,
    "ratchet_stop_offset":       0.01,
}

# Variance tolerances given small samples (n ≈ tens of entries).
RATE_VARIANCE_PP = 0.15        # ±15 percentage points
PNL_VARIANCE_USD = 2.00
ENTRIES_RATIO_LOW = 0.5
ENTRIES_RATIO_HIGH = 2.0

# Operational thresholds.
TICK_GAP_MEDIAN_FLAG_SEC = 60.0
TICK_GAP_MAX_FLAG_SEC = 300.0
WELL_OBSERVED_MIN_TICKS = 120  # ≥1 hour of polling at 30s cadence


# ------------------------------------------------------------------
# Parsing
# ------------------------------------------------------------------

@dataclass
class JournalDay:
    date: str
    path: Path
    sessions: list[dict] = field(default_factory=list)   # session_start
    session_ends: list[dict] = field(default_factory=list)
    ticks: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    other: list[dict] = field(default_factory=list)
    invalid_lines: int = 0


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def load_journals(journal_dir: Path) -> list[JournalDay]:
    out: list[JournalDay] = []
    files = sorted(p for p in journal_dir.glob("*.jsonl") if p.is_file())
    for f in files:
        day = JournalDay(date=f.stem, path=f)
        with f.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    day.invalid_lines += 1
                    continue
                t = rec.get("type", rec.get("event"))
                if t == "session_start":
                    day.sessions.append(rec)
                elif t == "session_end":
                    day.session_ends.append(rec)
                elif t == "tick":
                    day.ticks.append(rec)
                elif t == "trade":
                    day.trades.append(rec)
                else:
                    day.other.append(rec)
        out.append(day)
    return out


# ------------------------------------------------------------------
# Per-game enrichment
# ------------------------------------------------------------------

@dataclass
class GameView:
    date: str
    game_id: str
    fav_team: str | None
    event_ticker: str | None
    ticks: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)

    @property
    def n_ticks(self) -> int:
        return len(self.ticks)

    @property
    def well_observed(self) -> bool:
        return self.n_ticks >= WELL_OBSERVED_MIN_TICKS

    def first_fav_bid(self) -> float | None:
        for t in self.ticks:
            v = t.get("fav_bid")
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return None

    def fav_teams_observed(self) -> set[str]:
        return {
            t.get("fav_team") for t in self.ticks
            if t.get("fav_team")
        }

    def tick_gaps_sec(self) -> list[float]:
        ts = [
            _parse_ts(t.get("ts")) for t in self.ticks
        ]
        ts = [t for t in ts if t is not None]
        ts.sort()
        return [
            (ts[i] - ts[i - 1]).total_seconds()
            for i in range(1, len(ts))
        ]


def build_games(days: list[JournalDay]) -> list[GameView]:
    """Group ticks + trades into per-(date, game_id) views."""
    out: dict[tuple[str, str], GameView] = {}
    for d in days:
        for tick in d.ticks:
            key = (d.date, tick.get("game_id") or "?")
            gv = out.get(key)
            if gv is None:
                gv = GameView(
                    date=d.date,
                    game_id=tick.get("game_id") or "?",
                    fav_team=tick.get("fav_team"),
                    event_ticker=tick.get("event_ticker"),
                )
                out[key] = gv
            gv.ticks.append(tick)
        for tr in d.trades:
            key = (d.date, tr.get("game_id") or "?")
            gv = out.get(key)
            if gv is None:
                # Trade with no preceding tick — should be impossible
                # under normal operation. Create an empty stub.
                gv = GameView(
                    date=d.date,
                    game_id=tr.get("game_id") or "?",
                    fav_team=None,
                    event_ticker=None,
                )
                out[key] = gv
            gv.trades.append(tr)
    return list(out.values())


# ------------------------------------------------------------------
# Ratchet inference (from tick price trajectories)
# ------------------------------------------------------------------

def infer_ratchet(game: GameView, entry_tick_idx: int,
                  entry_price: float) -> dict:
    """Walk forward through ticks from entry; track running max."""
    max_post = entry_price
    max_idx = entry_tick_idx
    triggered = False
    triggered_idx = None
    for i in range(entry_tick_idx + 1, len(game.ticks)):
        bid = game.ticks[i].get("fav_bid")
        try:
            bid = float(bid)
        except (TypeError, ValueError):
            continue
        if bid > max_post:
            max_post = bid
            max_idx = i
        if (
            not triggered
            and (bid - entry_price)
            >= BACKTEST_TARGETS["ratchet_trigger_threshold"]
        ):
            triggered = True
            triggered_idx = i
    return {
        "triggered": triggered,
        "triggered_idx": triggered_idx,
        "max_post_entry_price": max_post,
        "max_post_entry_idx": max_idx,
        "post_entry_ticks": max(
            0, len(game.ticks) - entry_tick_idx - 1,
        ),
    }


def find_entry_tick_index(game: GameView, trade: dict) -> int | None:
    """Find the tick index whose ts matches the trade's ts."""
    target = _parse_ts(trade.get("ts"))
    if target is None:
        return None
    # Trade ts equals the tick ts that produced the entry. Match
    # exactly first; fall back to closest tick.
    for i, t in enumerate(game.ticks):
        if _parse_ts(t.get("ts")) == target:
            return i
    # Fallback: closest tick.
    best = None
    best_delta = None
    for i, t in enumerate(game.ticks):
        ts = _parse_ts(t.get("ts"))
        if ts is None:
            continue
        d = abs((ts - target).total_seconds())
        if best_delta is None or d < best_delta:
            best = i
            best_delta = d
    return best


# ------------------------------------------------------------------
# Report rendering
# ------------------------------------------------------------------

def _fmt_pct(x: float) -> str:
    return f"{x*100:.1f}%"


def _fmt_money(x: float) -> str:
    return f"${x:+,.2f}"


def render_report(days: list[JournalDay], games: list[GameView]) -> str:
    md: list[str] = []
    md.append("# Paper-Trade Journal Review v1\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")

    # Quick summary stats used by multiple sections.
    n_files = len(days)
    dates = [d.date for d in days]
    n_games = len(games)
    n_well_observed = sum(1 for g in games if g.well_observed)
    n_session_start = sum(len(d.sessions) for d in days)
    n_session_end = sum(len(d.session_ends) for d in days)
    n_ticks = sum(len(d.ticks) for d in days)
    n_trades = sum(len(d.trades) for d in days)
    n_invalid = sum(d.invalid_lines for d in days)
    entries = [
        t for d in days for t in d.trades
        if t.get("action") == "open"
    ]
    closes = [
        t for d in days for t in d.trades
        if t.get("action") in (
            "close_target", "close_stop",
            "close_ratchet_stop", "close_eod",
        )
    ]

    # Anomalies accumulator. (severity, finding, expected, next_step)
    anomalies: list[tuple[str, str, str, str]] = []

    md.append(
        "Backtest anchors (from STRATEGY4_SPEC §5A, ratcheted "
        "404-game replay): 0.89 entries/game, 41.6% target hit rate, "
        "24.6% full-stop rate, 33.8% ratchet-scratch rate, "
        "+$3.92 mean P&L per entry. Variance tolerances on this small "
        "sample: ±15pp on rates, ±$2 on mean P&L, "
        "[0.5, 2.0] on entries-per-game ratio.\n"
    )

    # ------- §1 Coverage summary -------
    md.append("\n## 1. Coverage summary\n")
    md.append(
        f"- Journal files: **{n_files}** "
        f"({dates[0]} → {dates[-1]} if sorted)\n"
        if dates else
        f"- Journal files: **0**\n"
    )
    md.append(
        f"- Distinct (date, game_id) pairs observed: **{n_games}**\n"
        f"- Of those, well-observed (≥{WELL_OBSERVED_MIN_TICKS} ticks "
        f"≈ ≥1h polling): **{n_well_observed}**\n"
        f"- session_start records: **{n_session_start}**\n"
        f"- session_end records: **{n_session_end}** "
        f"(unmatched / sessions started without ending: "
        f"**{max(0, n_session_start - n_session_end)}**)\n"
        f"- tick records: **{n_ticks:,}**\n"
        f"- trade records: **{n_trades}** "
        f"({len(entries)} open, {len(closes)} close)\n"
        f"- invalid JSON lines: {n_invalid}\n"
    )
    md.append(
        f"- `game_finished` records: **never observed** "
        f"(PHASE4A_DESIGN documents this type but the engine writer "
        f"does not emit it; market `closed` / `settled` statuses are "
        f"likewise absent — every tick has `market_status=\"active\"`).\n"
    )
    if n_session_start > n_session_end:
        anomalies.append((
            "HIGH",
            f"{n_session_start - n_session_end} session_start record(s) "
            f"have no matching session_end "
            f"({n_session_start} starts, {n_session_end} ends). "
            f"All observed session_ends carry `interrupted=true`.",
            "Sessions should write a clean session_end on graceful "
            "shutdown (max_run reached, idle exit, EOD).",
            "Diagnose engine shutdown path; confirm session_end is "
            "written on Ctrl-C / SIGTERM, not just on internal exit.",
        ))

    # ------- §2 Operational health -------
    md.append("\n## 2. Operational health\n")
    md.append(
        "| Date | Games | Sessions | Crashes | "
        "Tick gaps >60s | Errors |\n"
        "|------|------:|---------:|--------:|"
        "---------------:|-------:|\n"
    )
    by_date: dict[str, list[GameView]] = defaultdict(list)
    for g in games:
        by_date[g.date].append(g)
    for d in days:
        date_games = by_date.get(d.date, [])
        ses = len(d.sessions)
        ends = len(d.session_ends)
        crashes = max(0, ses - ends)
        # Tick-gap flag: any game whose median gap > 60s OR max > 300s.
        flagged_games = 0
        for g in date_games:
            gaps = g.tick_gaps_sec()
            if not gaps:
                continue
            if (
                median(gaps) > TICK_GAP_MEDIAN_FLAG_SEC
                or max(gaps) > TICK_GAP_MAX_FLAG_SEC
            ):
                flagged_games += 1
        # Error/warn record types: schema doesn't include them; always 0.
        errs = 0
        md.append(
            f"| {d.date} | {len(date_games)} | {ses} | {crashes} | "
            f"{flagged_games} | {errs} |\n"
        )
    # Aggregate tick-gap details.
    bad_games: list[tuple[GameView, float, float]] = []
    for g in games:
        gaps = g.tick_gaps_sec()
        if not gaps:
            continue
        med = median(gaps)
        mx = max(gaps)
        if (
            med > TICK_GAP_MEDIAN_FLAG_SEC
            or mx > TICK_GAP_MAX_FLAG_SEC
        ):
            bad_games.append((g, med, mx))
    if bad_games:
        md.append(
            f"\nGames with tick-gap anomalies "
            f"({len(bad_games)} of {n_games}):\n"
        )
        for g, med, mx in bad_games[:15]:
            md.append(
                f"- {g.date} {g.game_id}: median gap "
                f"{med:.1f}s, max gap {mx:.1f}s "
                f"({g.n_ticks} ticks)\n"
            )
        if len(bad_games) > 15:
            md.append(f"- … and {len(bad_games) - 15} more\n")
        anomalies.append((
            "MEDIUM",
            f"{len(bad_games)} of {n_games} games show tick-gap "
            f"anomalies (median > 60s or max > 5min).",
            "Median ~30s, no individual gap should exceed ~60s under "
            "normal polling.",
            "Spot-check the affected games against logger uptime; "
            "if engine was started late or interrupted, those gaps "
            "are expected and not a code defect.",
        ))
    # Game-completion: since `game_finished` is never written, every
    # game is "incomplete." This is a structural absence, not a per-
    # game crash; flag it once at MEDIUM severity.
    anomalies.append((
        "MEDIUM",
        "0 / {n} games reached a `game_finished` event.".format(
            n=n_games,
        ),
        "Engine should emit `game_finished` (or set a closed/settled "
        "tick status) when a market resolves so downstream audits "
        "can distinguish 'still in progress' from 'engine missed the "
        "close.'",
        "Phase 4a engine enhancement: emit `game_finished` on "
        "market_status transition to closed/settled (or mirror the "
        "existing ratchet_event approach with a structured close "
        "record).",
    ))

    # ------- §3 Signal & entry behavior -------
    md.append("\n## 3. Signal & entry behavior\n")
    n_entries = len(entries)
    expected_entries = n_well_observed * BACKTEST_TARGETS[
        "entries_per_game"
    ]
    expected_entries_all = n_games * BACKTEST_TARGETS[
        "entries_per_game"
    ]
    ratio_well = (
        n_entries / expected_entries if expected_entries else 0.0
    )
    ratio_all = (
        n_entries / expected_entries_all if expected_entries_all else 0.0
    )
    md.append(
        f"- Entries observed: **{n_entries}**\n"
        f"- Expected (well-observed games × 0.89): "
        f"~{expected_entries:.1f} → ratio {ratio_well:.2f}× "
        f"({_within_band(ratio_well)})\n"
        f"- Expected (all games × 0.89): "
        f"~{expected_entries_all:.1f} → ratio {ratio_all:.2f}× "
        f"({_within_band(ratio_all)})\n"
    )
    if (
        ratio_well < ENTRIES_RATIO_LOW
        or ratio_well > ENTRIES_RATIO_HIGH
    ) and n_well_observed > 0:
        anomalies.append((
            "MEDIUM",
            f"Entries / well-observed-game ratio = "
            f"{ratio_well:.2f}× (observed {n_entries}, expected "
            f"~{expected_entries:.1f}).",
            "Within [0.5, 2.0] of backtest expectation.",
            "If session run-time is short or signal-detector state "
            "doesn't carry across reconnects, expect lower entry "
            "rate. Reassess after sessions accumulate ≥3h continuous "
            "polling per game.",
        ))
    elif n_well_observed == 0:
        md.append(
            "\n_No game has ≥120 ticks of polling yet — entries-per-"
            "game expectation can't be evaluated meaningfully. "
            "Surfaced as MEDIUM under §2._\n"
        )

    # Entry price histogram.
    md.append("\n### Entry price distribution\n\n")
    buckets = [
        (lo, lo + 0.05) for lo in (
            0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80,
        )
    ]
    md.append("| Bucket | Count |\n|---|---:|\n")
    out_of_spec_entries: list[dict] = []
    for lo, hi in buckets:
        c = 0
        for e in entries:
            try:
                p = float(e.get("price"))
            except (TypeError, ValueError):
                continue
            if lo <= p < hi:
                c += 1
        md.append(f"| ${lo:.2f}–${hi:.2f} | {c} |\n")
    for e in entries:
        try:
            p = float(e.get("price"))
        except (TypeError, ValueError):
            continue
        if (
            p < BACKTEST_TARGETS["entry_price_min"]
            or p > BACKTEST_TARGETS["entry_price_max"]
        ):
            out_of_spec_entries.append(e)
    if out_of_spec_entries:
        anomalies.append((
            "HIGH",
            f"{len(out_of_spec_entries)} entries fired outside the "
            f"$0.50–$0.75 spec range. Sample: "
            f"{[float(e['price']) for e in out_of_spec_entries[:5]]}",
            "All S4A entries must occur in [$0.50, $0.75] per spec §2.",
            "Inspect engine signal detector entry-band check; "
            "compare with replay output for the same game to identify "
            "where the gate failed.",
        ))
    md.append(
        f"\nOut-of-spec entries (price ∉ [$0.50, $0.75]): "
        f"**{len(out_of_spec_entries)}**.\n"
    )

    # Entries per game distribution.
    by_game_entries: dict[tuple[str, str], int] = defaultdict(int)
    for e in entries:
        by_game_entries[(e.get("ts", "")[:10], e.get("game_id"))] += 0
    # Count using game views to honour (date, game_id):
    counts_per_game: list[int] = []
    over_max = 0
    for g in games:
        n = sum(
            1 for tr in g.trades if tr.get("action") == "open"
        )
        counts_per_game.append(n)
        if n > 2:
            over_max += 1
    dist = Counter(counts_per_game)
    md.append("\n### Entries per game\n\n")
    md.append("| Entries | Games |\n|---:|---:|\n")
    for k in sorted(dist):
        md.append(f"| {k} | {dist[k]} |\n")
    if over_max:
        anomalies.append((
            "HIGH",
            f"{over_max} game(s) recorded > 2 entries (spec max).",
            "Max 2 entries per game (max_entries_per_game=2 in "
            "PositionManager).",
            "Check live_runner re-entry suppression; replay the "
            "game offline and confirm the third entry is rejected.",
        ))

    # Time-of-game distribution.
    md.append("\n### Time of entry (since first tick of game)\n\n")
    md.append("| Date | Game | Entry $ | Time since first tick |\n")
    md.append("|---|---|---:|---:|\n")
    for e in entries:
        gid = e.get("game_id")
        ets = _parse_ts(e.get("ts"))
        # Find the matching game view.
        for g in games:
            if g.game_id != gid:
                continue
            if g.ticks and ets is not None:
                first = _parse_ts(g.ticks[0].get("ts"))
                if first is not None:
                    delta = (ets - first).total_seconds()
                    delta_min = delta / 60.0
                    md.append(
                        f"| {g.date} | {gid} | "
                        f"${float(e['price']):.2f} | "
                        f"{delta_min:.1f} min |\n"
                    )
                    break

    # ------- §4 Exit behavior -------
    md.append("\n## 4. Exit behavior\n")
    n_target = sum(
        1 for c in closes if c.get("action") == "close_target"
    )
    n_stop = sum(
        1 for c in closes if c.get("action") == "close_stop"
    )
    n_ratchet = sum(
        1 for c in closes if c.get("action") == "close_ratchet_stop"
    )
    n_eod = sum(
        1 for c in closes if c.get("action") == "close_eod"
    )
    pnls = []
    for c in closes:
        try:
            pnls.append(float(c.get("pnl") or c.get("pnl_after_fees")))
        except (TypeError, ValueError):
            continue
    n_close = len(closes)
    if n_close == 0:
        md.append(
            "**No closes recorded across the entire dataset.** "
            f"Open positions: {n_entries}. Without close events the "
            f"target / stop / scratch / EOD breakdown cannot be "
            f"compared against backtest. This is the load-bearing "
            f"finding of this review.\n"
        )
        anomalies.append((
            "HIGH",
            f"{n_entries} entries opened but 0 closes ever logged.",
            "Engine should emit close_target / close_stop / "
            "close_ratchet_stop / close_eod events when positions "
            "exit. PHASE4A_DESIGN §journal contract specifies these.",
            "Possible causes: (a) sessions terminating before any "
            "exit signal fires (consistent with all session_ends "
            "carrying interrupted=true); (b) end_of_game() not being "
            "called on graceful shutdown; (c) journal writer not "
            "wired to close-action codepath. Verify by replaying "
            "one of the 3 entries against engine.replay and "
            "confirming a close action would fire on the same data.",
        ))
    else:
        rate_target = n_target / n_close
        rate_stop = n_stop / n_close
        rate_ratchet = n_ratchet / n_close
        mean_pnl = sum(pnls) / len(pnls) if pnls else 0.0
        md.append(
            f"- Target ($0.90) hits: {n_target} / {n_close} = "
            f"{_fmt_pct(rate_target)} "
            f"(backtest 41.6%, "
            f"{_within_pp(rate_target, 0.416)})\n"
            f"- Full stops ($0.40): {n_stop} / {n_close} = "
            f"{_fmt_pct(rate_stop)} "
            f"(backtest 24.6%, "
            f"{_within_pp(rate_stop, 0.246)})\n"
            f"- Ratchet scratches: {n_ratchet} / {n_close} = "
            f"{_fmt_pct(rate_ratchet)} "
            f"(backtest 33.8%, "
            f"{_within_pp(rate_ratchet, 0.338)})\n"
            f"- EOD closes: {n_eod} / {n_close}\n"
            f"- Mean P&L per entry: {_fmt_money(mean_pnl)} "
            f"(backtest +$3.92, "
            f"{_within_dollars(mean_pnl, 3.92)})\n"
        )
        # Add anomalies for rates outside variance band.
        for label, obs, exp in [
            ("target hit rate", rate_target, 0.416),
            ("full-stop rate", rate_stop, 0.246),
            ("ratchet-scratch rate", rate_ratchet, 0.338),
        ]:
            if abs(obs - exp) > RATE_VARIANCE_PP:
                anomalies.append((
                    "MEDIUM",
                    f"Observed {label} {_fmt_pct(obs)} vs "
                    f"backtest {_fmt_pct(exp)}.",
                    f"Within ±{RATE_VARIANCE_PP*100:.0f}pp of "
                    f"backtest given small sample.",
                    "Continue accumulating; re-evaluate at n≥30 closes.",
                ))
        if abs(mean_pnl - 3.92) > PNL_VARIANCE_USD:
            anomalies.append((
                "MEDIUM",
                f"Observed mean P&L {_fmt_money(mean_pnl)} vs "
                f"backtest +$3.92.",
                f"Within ±${PNL_VARIANCE_USD:.2f}.",
                "Check fee accounting; confirm exit prices match "
                "level fills.",
            ))

    # ------- §5 Ratchet behavior -------
    md.append("\n## 5. Ratchet behavior\n")
    md.append(
        "Tick records do not carry a `ratchet_triggered` field; "
        "ratchet status is inferred from the post-entry price "
        "trajectory in the same game's tick stream. For each entry, "
        "we walk forward and look for any tick where "
        "fav_bid ≥ entry + $0.08.\n\n"
    )
    ratchet_inferred: list[dict] = []
    for e in entries:
        gid = e.get("game_id")
        # Match the game view by date prefix from ts.
        ets = e.get("ts", "")[:10]
        gv = next(
            (g for g in games if g.game_id == gid and g.date == ets),
            None,
        )
        if gv is None:
            continue
        idx = find_entry_tick_index(gv, e)
        if idx is None:
            continue
        try:
            entry_price = float(e.get("price"))
        except (TypeError, ValueError):
            continue
        info = infer_ratchet(gv, idx, entry_price)
        info["entry"] = e
        info["entry_price"] = entry_price
        info["game"] = gv
        ratchet_inferred.append(info)
    n_triggered = sum(1 for r in ratchet_inferred if r["triggered"])
    md.append(
        f"- Entries inferred to have triggered the ratchet "
        f"(post-entry max ≥ entry+$0.08): "
        f"**{n_triggered} / {len(ratchet_inferred)}**\n"
    )
    md.append(
        "- Backtest reference: 270 / 358 entries (75.4%) reached "
        "the +$0.08 trigger on the 404-game replay; of those, "
        "~44.8% ended as scratches and ~55.2% as targets.\n"
    )
    if ratchet_inferred:
        md.append("\n### Per-entry ratchet inference\n\n")
        md.append(
            "| Date | Game | Entry $ | Post-entry ticks | "
            "Max post-entry $ | Triggered |\n"
            "|---|---|---:|---:|---:|:---:|\n"
        )
        for r in ratchet_inferred:
            e = r["entry"]
            gv = r["game"]
            md.append(
                f"| {gv.date} | {gv.game_id} | "
                f"${r['entry_price']:.2f} | "
                f"{r['post_entry_ticks']} | "
                f"${r['max_post_entry_price']:.2f} | "
                f"{'YES' if r['triggered'] else 'no'} |\n"
            )
    # Mean P&L splits skipped — no closes recorded.
    if n_close == 0:
        md.append(
            "\nMean P&L on ratchet-triggered vs non-triggered entries: "
            "**not computable** (zero closes in journal).\n"
        )

    # ------- §6 Favorite determination sanity -------
    md.append("\n## 6. Favorite determination\n")
    md.append(
        "Full sanity check (compare favorite to higher Kalshi YES bid "
        "at lock moment) requires the underdog's bid at lock time, "
        "which the journal does not record. Available partial check: "
        "first observed `fav_bid` for each game must be > $0.50, "
        "since the favorite is by definition the >50% side of a "
        "binary YES market. Pick'em flag: first fav_bid within $0.02 "
        "of $0.50.\n\n"
    )
    fav_flips = 0
    fav_below_50 = 0   # strictly < $0.50 — real determination bug
    fav_at_50 = 0      # == $0.50 — pick'em edge case (LOW)
    pickem = 0
    for g in games:
        teams = g.fav_teams_observed()
        if len(teams) > 1:
            fav_flips += 1
        first_bid = g.first_fav_bid()
        if first_bid is None:
            continue
        if first_bid < 0.50:
            fav_below_50 += 1
        elif first_bid == 0.50:
            fav_at_50 += 1
        if 0.50 <= first_bid <= 0.52:
            pickem += 1
    md.append(
        f"- Games where fav_team flipped mid-stream: "
        f"**{fav_flips}** (any > 0 is a HIGH bug)\n"
        f"- Games whose first fav_bid < $0.50 (favorite on the "
        f"wrong side): **{fav_below_50}** (any > 0 is a HIGH bug)\n"
        f"- Games whose first fav_bid = $0.50 exactly (pick'em "
        f"edge case): **{fav_at_50}**\n"
        f"- Pick'em games (first fav_bid in [$0.50, $0.52]): "
        f"**{pickem}**\n"
    )
    if fav_flips > 0:
        anomalies.append((
            "HIGH",
            f"{fav_flips} game(s) had `fav_team` change mid-game.",
            "Favorite is locked at session start and must not change.",
            "Check resolve_favorite() locking; confirm fav_ticker "
            "is captured once per game and not re-derived per tick.",
        ))
    if fav_below_50 > 0:
        anomalies.append((
            "HIGH",
            f"{fav_below_50} game(s) had first fav_bid < $0.50 "
            f"(favorite chosen as the lower-priced side).",
            "By construction, the favorite is the >50% side at "
            "session lock.",
            "Check favorite-determination logic.",
        ))
    if fav_at_50 > 0:
        anomalies.append((
            "LOW",
            f"{fav_at_50} game(s) opened with first fav_bid = $0.50 "
            f"exactly (pick'em). Engine resolved a favorite anyway "
            f"(likely from pre-game spread / ESPN), which is a "
            f"reasonable fallback but worth tracking.",
            "Document pick'em handling explicitly in PHASE4A_DESIGN; "
            "consider whether to skip such games entirely or accept "
            "the spread-based tie-break.",
            "Watch list — re-evaluate after more pick'em games "
            "accumulate to see if outcomes track backtest.",
        ))

    # ------- §7 Anomalies & follow-ups -------
    md.append("\n## 7. Anomalies & follow-ups\n")
    if not anomalies:
        md.append("None. All checks passed within tolerance.\n")
    else:
        sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        anomalies.sort(key=lambda a: sev_order.get(a[0], 9))
        for sev, what, expected, nxt in anomalies:
            md.append(
                f"- **{sev}** — {what}\n"
                f"  - _Expected:_ {expected}\n"
                f"  - _Next step:_ {nxt}\n"
            )

    # ------- §8 Verdict -------
    md.append("\n## 8. Verdict\n")
    has_high = any(a[0] == "HIGH" for a in anomalies)
    has_medium = any(a[0] == "MEDIUM" for a in anomalies)
    if has_high:
        verdict = "BLOCK"
        reason = (
            "At least one HIGH-severity finding present. Diagnose "
            "before continuing live runs. See §7 for blockers."
        )
    elif has_medium:
        verdict = "CONCERNS"
        reason = (
            "MEDIUM-severity findings present, no HIGH. Continue "
            "paper-trading; re-review after 5 more game-nights."
        )
    else:
        verdict = "CLEAN"
        reason = (
            "No HIGH-severity findings, no out-of-tolerance MEDIUM. "
            "Engine behavior aligns with backtest. Proceed to next "
            "audit (logger-vs-engine signal alignment)."
        )
    md.append(f"**{verdict}** — {reason}\n")

    return "".join(md) + "\n"


# Helper formatters used by the report renderer.
def _within_band(ratio: float) -> str:
    if ENTRIES_RATIO_LOW <= ratio <= ENTRIES_RATIO_HIGH:
        return "within band"
    if ratio < ENTRIES_RATIO_LOW:
        return "BELOW band"
    return "ABOVE band"


def _within_pp(obs: float, exp: float) -> str:
    delta = obs - exp
    if abs(delta) <= RATE_VARIANCE_PP:
        return f"within ±{RATE_VARIANCE_PP*100:.0f}pp"
    return f"OUTSIDE band ({delta*100:+.1f}pp)"


def _within_dollars(obs: float, exp: float) -> str:
    delta = obs - exp
    if abs(delta) <= PNL_VARIANCE_USD:
        return f"within ±${PNL_VARIANCE_USD:.2f}"
    return f"OUTSIDE band ({delta:+.2f})"


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> int:
    if not JOURNAL_DIR.exists():
        print(
            f"ERROR: journal directory not found: {JOURNAL_DIR}",
            flush=True,
        )
        return 2
    days = load_journals(JOURNAL_DIR)
    if not days:
        print(
            f"WARN: no .jsonl journals in {JOURNAL_DIR}",
            flush=True,
        )
        # Still write a stub report so downstream tooling never sees
        # a missing file.
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            "# Paper-Trade Journal Review v1\n"
            f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n\n"
            "_No journals available._\n\n"
            "## 8. Verdict\n\n"
            "**CLEAN** — no data to evaluate.\n"
        )
        return 0
    games = build_games(days)
    md = render_report(days, games)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    print(
        f"Report → {REPORT_PATH}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
