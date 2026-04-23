"""Strategy 1 corrected — underdog swing trade analysis.

Supersedes `analysis/strategy1_bilateral_sim.py`. The prior script's
$5,603/yr figure combined mutually exclusive outcomes (T5 exits at
5 min + bilateral completions at 35+ min in the same P&L) and thus
assumed future knowledge a live engine cannot have. This script
replaces the bilateral framing with a single-coherent-state-machine
underdog swing trade on the same 404-game Kalshi paired dataset.

Every config here is a complete rule set with priority-ordered exits:
target → stop → trailing stop → time limit → resolution. No config
mixes incompatible outcomes. Single entry per game. The
"bilateral equivalent" price ($0.65 sell ≡ bilateral buy at
$0.20+$0.35) confirms a swing trade captures the same economics with
simpler execution.

Run:
    python -m analysis.strategy1_swing_corrected
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from analysis.strategy1_bilateral_sim import (
    ANNUAL_SCALE_GAMES,
    CONTRACTS,
    GameCtx,
    SPREAD_BUCKETS,
    bucket_for,
    kalshi_fee,
    prepare_games,
)
from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    load_kalshi_games_all_spreads,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "strategy1_swing_corrected.md"
)

ENTRY_THRESHOLDS_SECTION1 = [0.15, 0.20, 0.25, 0.30, 0.35]
BASELINE_ENTRY_THRESHOLD = 0.35  # Sections 2-5

# Section 3 peak buckets
PEAK_BUCKETS: list[tuple[str, float, float]] = [
    ("< $0.20", 0.0, 0.20),
    ("$0.20-$0.30", 0.20, 0.30),
    ("$0.30-$0.40", 0.30, 0.40),
    ("$0.40-$0.50", 0.40, 0.50),
    ("$0.50-$0.65", 0.50, 0.65),
    ("$0.65-$0.80", 0.65, 0.80),
    ("> $0.80", 0.80, 1.00001),
]

ENTRY_PRICE_BANDS: list[tuple[str, float, float]] = [
    ("≤ $0.10", 0.0, 0.10),
    ("$0.10-$0.15", 0.10, 0.15),
    ("$0.15-$0.20", 0.15, 0.20),
    ("$0.20-$0.25", 0.20, 0.25),
    ("$0.25-$0.30", 0.25, 0.30),
    ("$0.30-$0.35", 0.30, 0.35),
]


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


# ---- Entry policy ------------------------------------------------------

@dataclass
class EntryRef:
    """First Policy A entry for a game at a given threshold."""
    ctx: GameCtx
    side: str          # "fav" or "dog"
    tick: int
    price: float

    @property
    def side_series(self) -> np.ndarray:
        return self.ctx.fav_series if self.side == "fav" else self.ctx.dog_series


def find_entry(ctx: GameCtx, threshold: float) -> EntryRef | None:
    """Return first tick where either side's bid ≤ threshold."""
    for i in range(ctx.n_ticks):
        fav_i = float(ctx.fav_series[i])
        dog_i = float(ctx.dog_series[i])
        if fav_i <= threshold or dog_i <= threshold:
            if fav_i <= threshold and dog_i <= threshold:
                # Tie (only possible at threshold ≥ 0.5). Pick lower.
                side = "fav" if fav_i <= dog_i else "dog"
                price = min(fav_i, dog_i)
            elif fav_i <= threshold:
                side = "fav"
                price = fav_i
            else:
                side = "dog"
                price = dog_i
            return EntryRef(ctx=ctx, side=side, tick=i, price=price)
    return None


# ---- Exit config + simulator ------------------------------------------

@dataclass
class ExitConfig:
    name: str
    profit_target: float | None = None          # absolute price
    profit_target_delta: float | None = None    # relative to entry
    stop_delta: float | None = None             # entry - delta = stop price
    trail_delta: float | None = None            # peak - delta = trail exit
    time_limit_ticks: int | None = None         # ticks after entry


@dataclass
class TradeOutcome:
    entry_ref: EntryRef
    exit_type: str          # target / stop / trail / time / resolution
    exit_tick: int
    exit_price: float
    pnl: float


def _entry_fee(entry_price: float) -> float:
    return kalshi_fee(CONTRACTS, entry_price, maker=True)


def _taker_exit(
    entry_ref: EntryRef, exit_price: float, exit_tick: int, exit_type: str,
) -> TradeOutcome:
    e_fee = _entry_fee(entry_ref.price)
    x_fee = kalshi_fee(CONTRACTS, exit_price, maker=False)
    pnl = (exit_price - entry_ref.price) * CONTRACTS - e_fee - x_fee
    return TradeOutcome(
        entry_ref=entry_ref, exit_type=exit_type,
        exit_tick=exit_tick, exit_price=exit_price, pnl=pnl,
    )


def _resolution_exit(entry_ref: EntryRef) -> TradeOutcome:
    payoff = 1.0 if entry_ref.side == entry_ref.ctx.winner else 0.0
    e_fee = _entry_fee(entry_ref.price)
    pnl = (payoff - entry_ref.price) * CONTRACTS - e_fee
    return TradeOutcome(
        entry_ref=entry_ref, exit_type="resolution",
        exit_tick=entry_ref.ctx.n_ticks - 1, exit_price=payoff, pnl=pnl,
    )


def simulate_exit(
    entry_ref: EntryRef, cfg: ExitConfig,
) -> TradeOutcome:
    """Walk the post-entry trajectory under a single state machine.

    Priority order at each tick after entry:
      1. Profit target (absolute or relative)
      2. Stop loss
      3. Trailing stop
      4. Time limit
      5. (End of series) Resolution
    """
    series = entry_ref.side_series
    entry_tick = entry_ref.tick
    entry_price = entry_ref.price
    n = len(series)
    peak = entry_price

    # Precompute fixed price levels
    if cfg.profit_target is not None:
        target_price = cfg.profit_target
    elif cfg.profit_target_delta is not None:
        target_price = entry_price + cfg.profit_target_delta
    else:
        target_price = None
    stop_price = (
        entry_price - cfg.stop_delta
        if cfg.stop_delta is not None else None
    )

    for i in range(entry_tick + 1, n):
        p = float(series[i])
        # Update peak (for trailing stop)
        if p > peak:
            peak = p

        # 1. Profit target
        if target_price is not None and p >= target_price:
            return _taker_exit(
                entry_ref, exit_price=target_price,
                exit_tick=i, exit_type="target",
            )
        # 2. Fixed stop
        if stop_price is not None and p <= stop_price:
            return _taker_exit(
                entry_ref, exit_price=stop_price,
                exit_tick=i, exit_type="stop",
            )
        # 3. Trailing stop
        if cfg.trail_delta is not None:
            trail_trigger = peak - cfg.trail_delta
            if peak > entry_price and p <= trail_trigger:
                return _taker_exit(
                    entry_ref, exit_price=trail_trigger,
                    exit_tick=i, exit_type="trail",
                )
        # 4. Time limit (hard stop at market)
        if cfg.time_limit_ticks is not None:
            if i - entry_tick >= cfg.time_limit_ticks:
                return _taker_exit(
                    entry_ref, exit_price=p,
                    exit_tick=i, exit_type="time",
                )

    # 5. Fell off the end without triggering — hold to resolution
    return _resolution_exit(entry_ref)


# ---- Aggregation helpers ----------------------------------------------

@dataclass
class ConfigResult:
    cfg: ExitConfig
    n_games_entered: int
    outcomes: list[TradeOutcome]
    exit_counts: dict[str, int] = field(default_factory=dict)
    exit_pnls_by_type: dict[str, list[float]] = field(default_factory=dict)

    @property
    def mean_pnl(self) -> float:
        if not self.outcomes:
            return 0.0
        return float(np.mean([o.pnl for o in self.outcomes]))

    @property
    def total_pnl(self) -> float:
        return float(sum(o.pnl for o in self.outcomes))

    @property
    def annual_ev(self) -> float:
        # EV per game × season scale. Uses total P&L over entered set /
        # total games (consistent with parent convention).
        return self.total_pnl / max(1, self.n_games_entered) * ANNUAL_SCALE_GAMES

    @property
    def entries(self) -> int:
        return len(self.outcomes)

    def post_init_derive(self) -> None:
        by_type: dict[str, list[float]] = {}
        for o in self.outcomes:
            by_type.setdefault(o.exit_type, []).append(o.pnl)
        self.exit_pnls_by_type = by_type
        self.exit_counts = {k: len(v) for k, v in by_type.items()}


def evaluate_config(
    ctxs: list[GameCtx], threshold: float, cfg: ExitConfig,
) -> ConfigResult:
    outcomes: list[TradeOutcome] = []
    for ctx in ctxs:
        entry = find_entry(ctx, threshold)
        if entry is None:
            continue
        outcomes.append(simulate_exit(entry, cfg))
    result = ConfigResult(
        cfg=cfg, n_games_entered=len(ctxs), outcomes=outcomes,
    )
    result.post_init_derive()
    return result


# ---- Section 1: hold-to-resolution baseline ---------------------------

def section1_baselines(ctxs: list[GameCtx]) -> list[dict]:
    rows: list[dict] = []
    for thr in ENTRY_THRESHOLDS_SECTION1:
        cfg = ExitConfig(name=f"hold-to-resolution (entry ≤ ${thr:.2f})")
        res = evaluate_config(ctxs, thr, cfg)
        entry_prices = [o.entry_ref.price for o in res.outcomes]
        wins = sum(1 for o in res.outcomes if o.exit_price == 1.0)
        rows.append({
            "threshold": thr,
            "n_entered": res.entries,
            "mean_entry_price": (
                float(np.mean(entry_prices)) if entry_prices else 0.0
            ),
            "win_rate": (
                100.0 * wins / res.entries if res.entries else 0.0
            ),
            "mean_pnl": res.mean_pnl,
            "annual_ev": res.annual_ev,
        })
    return rows


# ---- Section 2: exit strategy sweep -----------------------------------

def build_sweep_configs() -> list[ExitConfig]:
    configs: list[ExitConfig] = []
    # A. Profit target only
    for d in [0.05, 0.10, 0.15, 0.20, 0.30]:
        configs.append(ExitConfig(
            name=f"A.rel +${d:.2f}", profit_target_delta=d,
        ))
    for abs_t in [0.40, 0.50, 0.60, 0.65, 0.80]:
        configs.append(ExitConfig(
            name=f"A.abs ${abs_t:.2f}", profit_target=abs_t,
        ))
    # B. Fixed stop only
    for s in [0.03, 0.05, 0.08]:
        configs.append(ExitConfig(
            name=f"B.stop -${s:.2f}", stop_delta=s,
        ))
    # C. Profit target + fixed stop
    for d in [0.10, 0.15, 0.20, 0.30]:
        for s in [0.03, 0.05, 0.08]:
            configs.append(ExitConfig(
                name=f"C.tgt+${d:.2f}/stop-${s:.2f}",
                profit_target_delta=d, stop_delta=s,
            ))
    # D. Trailing stop only
    for t in [0.03, 0.05, 0.08, 0.10]:
        configs.append(ExitConfig(
            name=f"D.trail -${t:.2f}", trail_delta=t,
        ))
    # E. Trail + target
    for d in [0.10, 0.15, 0.20, 0.30]:
        for t in [0.03, 0.05, 0.08]:
            configs.append(ExitConfig(
                name=f"E.tgt+${d:.2f}/trail-${t:.2f}",
                profit_target_delta=d, trail_delta=t,
            ))
    # F. Time limit only
    for lim_ticks in [60, 120, 240, 360, 720]:
        mins = lim_ticks // 2
        configs.append(ExitConfig(
            name=f"F.time {mins}m", time_limit_ticks=lim_ticks,
        ))
    # G. Target + time limit
    for d in [0.10, 0.15, 0.20, 0.30]:
        for lim_ticks in [60, 120, 240, 360]:
            mins = lim_ticks // 2
            configs.append(ExitConfig(
                name=f"G.tgt+${d:.2f}/time {mins}m",
                profit_target_delta=d, time_limit_ticks=lim_ticks,
            ))
    return configs


# ---- Section 3: Price trajectory characterization --------------------

@dataclass
class TrajectoryFacts:
    peak_bucket: str
    entry_price: float
    peak_price: float
    ticks_to_peak: int
    min_before_peak: float
    drawdown_before_peak: float
    reached_065: bool


def characterize_trajectories(ctxs: list[GameCtx]) -> list[TrajectoryFacts]:
    out: list[TrajectoryFacts] = []
    for ctx in ctxs:
        entry = find_entry(ctx, BASELINE_ENTRY_THRESHOLD)
        if entry is None:
            continue
        series = entry.side_series
        post = series[entry.tick:]
        if len(post) < 2:
            continue
        peak_idx_rel = int(np.argmax(post))
        peak_price = float(post[peak_idx_rel])
        min_before_peak = float(post[: peak_idx_rel + 1].min())
        drawdown = max(0.0, entry.price - min_before_peak)
        bucket_lab = "> $0.80"
        for lab, lo, hi in PEAK_BUCKETS:
            if lo <= peak_price < hi:
                bucket_lab = lab
                break
        reached_065 = bool((post >= 0.65).any())
        out.append(TrajectoryFacts(
            peak_bucket=bucket_lab,
            entry_price=entry.price,
            peak_price=peak_price,
            ticks_to_peak=peak_idx_rel,
            min_before_peak=min_before_peak,
            drawdown_before_peak=drawdown,
            reached_065=reached_065,
        ))
    return out


def time_to_level(ctxs: list[GameCtx], level: float) -> list[int]:
    """For games that reach level at some tick after entry, record ticks
    from entry to first crossing. Games that never reach excluded."""
    out: list[int] = []
    for ctx in ctxs:
        entry = find_entry(ctx, BASELINE_ENTRY_THRESHOLD)
        if entry is None:
            continue
        series = entry.side_series
        n = len(series)
        for i in range(entry.tick + 1, n):
            if series[i] >= level:
                out.append(i - entry.tick)
                break
    return out


# ---- Section 4: bucket breakdown --------------------------------------

def spread_breakdown(
    ctxs: list[GameCtx], cfg: ExitConfig, threshold: float,
) -> dict[str, dict]:
    bucket_ctxs: dict[str, list[GameCtx]] = {
        lab: [] for lab, _, _ in SPREAD_BUCKETS
    }
    for c in ctxs:
        lab = bucket_for(c.abs_spread)
        if lab is not None:
            bucket_ctxs[lab].append(c)
    out: dict[str, dict] = {}
    for lab, _, _ in SPREAD_BUCKETS:
        gs = bucket_ctxs[lab]
        if not gs:
            out[lab] = {
                "n_games": 0, "entries": 0,
                "mean_pnl": 0.0, "annual_ev": 0.0,
            }
            continue
        res = evaluate_config(gs, threshold, cfg)
        out[lab] = {
            "n_games": len(gs), "entries": res.entries,
            "mean_pnl": res.mean_pnl,
            "annual_ev": res.annual_ev,
        }
    return out


def entry_band_breakdown(outcomes: list[TradeOutcome]) -> list[dict]:
    rows: list[dict] = []
    for lab, lo, hi in ENTRY_PRICE_BANDS:
        subset = [
            o for o in outcomes if lo <= o.entry_ref.price < hi
        ]
        if not subset:
            rows.append({
                "label": lab, "count": 0,
                "mean_pnl": 0.0, "target_pct": 0.0,
            })
            continue
        targets = sum(1 for o in subset if o.exit_type == "target")
        rows.append({
            "label": lab, "count": len(subset),
            "mean_pnl": float(np.mean([o.pnl for o in subset])),
            "target_pct": 100.0 * targets / len(subset),
        })
    return rows


# ---- Report rendering --------------------------------------------------

def render_report(
    n_games: int,
    baselines: list[dict],
    sweep_results: list[ConfigResult],
    hold_res_baseline: ConfigResult,
    trajectory_facts: list[TrajectoryFacts],
    time_to_levels: dict[float, list[int]],
    top3_breakdowns: list[tuple[ConfigResult, dict, list[dict]]],
    near_miss_trail_stats: dict,
) -> str:
    md: list[str] = []
    md.append("# Strategy 1 Corrected — Underdog Swing Trade Analysis\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "**This analysis supersedes "
        "`strategy1_bilateral_sim.md`.** The prior script combined "
        "mutually exclusive outcomes — T5 exits at 5 minutes AND "
        "bilateral completions requiring 35+ minute holds — in the "
        "same P&L, implicitly assuming the engine can predict at "
        "minute 5 which entries will later complete. A live engine "
        "cannot do this. The $5,603/yr figure was operationally "
        "unachievable.\n\n"
        "This analysis replaces the bilateral framing with a single "
        "coherent state machine per config. No config mixes "
        "incompatible outcomes; no config assumes future knowledge. "
        "Single entry per game. The bilateral-equivalence observation "
        "($0.65 sell ≡ $0.20 + $0.35 bilateral buys, same gross) "
        "confirms a swing trade captures the same economics with "
        "simpler execution.\n"
    )
    md.append(
        f"\nDataset: **{n_games} games** from the Kalshi-confirmed "
        "paired dataset (all spreads). `dog_vwap = 1 - fav_vwap` "
        "approximation carries forward — annual EV is an upper bound.\n"
    )

    # Section 1
    md.append("\n## Section 1 — Hold-to-resolution baseline\n")
    md.append(
        "Enter at the first tick where either side's bid ≤ threshold "
        "(Policy A). Hold to game resolution. No exit management. "
        "This is the true Option A baseline.\n\n"
        "| Entry threshold | Games entered | Mean entry | Win rate | Mean P&L | Annual EV |\n"
        "|---:|---:|---:|---:|---:|---:|\n"
    )
    for r in baselines:
        md.append(
            f"| ≤ ${r['threshold']:.2f} | {r['n_entered']} | "
            f"${r['mean_entry_price']:.3f} | "
            f"{r['win_rate']:.1f}% | "
            f"${r['mean_pnl']:+.2f} | "
            f"${r['annual_ev']:+,.0f} |\n"
        )

    # Section 2
    md.append("\n## Section 2 — Exit strategy sweep\n")
    md.append(
        f"Entry fixed at threshold $0.35. Each config is a complete "
        "rule set with priority-ordered exits: target → stop → "
        "trail → time → resolution.\n\n"
    )
    md.append(
        f"**Hold-to-resolution baseline at $0.35 threshold:** "
        f"{hold_res_baseline.entries} entries, "
        f"mean P&L ${hold_res_baseline.mean_pnl:+.2f}, "
        f"annual EV ${hold_res_baseline.annual_ev:+,.0f}.\n\n"
        f"**Total sweep configs:** {len(sweep_results)}. Top 20 by "
        "annual EV:\n\n"
    )
    md.append(
        "| # | Config | Entries | Target | Stop | Trail | Time | Res | Mean P&L | Annual EV |\n"
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    sorted_sweep = sorted(sweep_results, key=lambda r: -r.annual_ev)
    for i, r in enumerate(sorted_sweep[:20], 1):
        md.append(
            f"| {i} | {r.cfg.name} | {r.entries} | "
            f"{r.exit_counts.get('target', 0)} | "
            f"{r.exit_counts.get('stop', 0)} | "
            f"{r.exit_counts.get('trail', 0)} | "
            f"{r.exit_counts.get('time', 0)} | "
            f"{r.exit_counts.get('resolution', 0)} | "
            f"${r.mean_pnl:+.2f} | ${r.annual_ev:+,.0f} |\n"
        )
    positive = sum(1 for r in sweep_results if r.annual_ev > 0)
    md.append(
        f"\nAcross all {len(sweep_results)} configs: "
        f"**{positive} positive EV** "
        f"({100*positive/len(sweep_results):.1f}%). "
        f"Hold-to-resolution baseline "
        f"${hold_res_baseline.annual_ev:+,.0f} ranks "
        f"#{1 + sum(1 for r in sorted_sweep if r.annual_ev > hold_res_baseline.annual_ev)} "
        "in the sorted list.\n"
    )

    # Section 3
    md.append("\n## Section 3 — Price trajectory characterization\n")
    md.append(
        "Observational analysis on the post-entry trajectory for each "
        f"game that triggers Policy A at ≤ ${BASELINE_ENTRY_THRESHOLD:.2f}.\n"
    )

    # 3A: peak bucket
    md.append("\n### 3A — Peak price reached\n\n")
    md.append(
        "| Peak bucket | Count | % | Mean entry | Mean peak | "
        "Mean ticks to peak |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    total_traj = len(trajectory_facts)
    by_bucket: dict[str, list[TrajectoryFacts]] = {}
    for t in trajectory_facts:
        by_bucket.setdefault(t.peak_bucket, []).append(t)
    for lab, _, _ in PEAK_BUCKETS:
        bucket = by_bucket.get(lab, [])
        if not bucket:
            md.append(f"| {lab} | 0 | 0.0% | — | — | — |\n")
            continue
        c = len(bucket)
        md.append(
            f"| {lab} | {c} | {100 * c / max(1, total_traj):.1f}% | "
            f"${np.mean([t.entry_price for t in bucket]):.3f} | "
            f"${np.mean([t.peak_price for t in bucket]):.3f} | "
            f"{int(np.median([t.ticks_to_peak for t in bucket]))} |\n"
        )

    # 3B: drawdown before peak (for peak >= $0.50)
    md.append("\n### 3B — Max drawdown before peak (for games reaching peak ≥ $0.50)\n\n")
    md.append(
        "| Peak bucket | Count | Mean max drawdown | Median | P90 |\n"
        "|---|---:|---:|---:|---:|\n"
    )
    for lab in ["$0.50-$0.65", "$0.65-$0.80", "> $0.80"]:
        bucket = by_bucket.get(lab, [])
        if not bucket:
            md.append(f"| {lab} | 0 | — | — | — |\n")
            continue
        dd = [t.drawdown_before_peak for t in bucket]
        md.append(
            f"| {lab} | {len(bucket)} | "
            f"${np.mean(dd):.3f} | "
            f"${np.median(dd):.3f} | "
            f"${np.quantile(dd, 0.90):.3f} |\n"
        )

    # 3C: near-miss
    md.append("\n### 3C — Near-miss analysis ($0.55-$0.64 peak, never reached $0.65)\n\n")
    near_misses = [
        t for t in trajectory_facts
        if 0.55 <= t.peak_price < 0.65 and not t.reached_065
    ]
    md.append(
        f"**{len(near_misses)}** games peak in $0.55-$0.64 without "
        f"reaching $0.65.\n\n"
    )
    if near_misses:
        entries = [t.entry_price for t in near_misses]
        peaks = [t.peak_price for t in near_misses]
        # Captured by trail-$0.05 stop: peak - 0.05 - entry
        cap5 = [
            (t.peak_price - 0.05 - t.entry_price) * CONTRACTS
            - kalshi_fee(CONTRACTS, t.entry_price, maker=True)
            - kalshi_fee(CONTRACTS, t.peak_price - 0.05, maker=False)
            for t in near_misses
        ]
        cap8 = [
            (t.peak_price - 0.08 - t.entry_price) * CONTRACTS
            - kalshi_fee(CONTRACTS, t.entry_price, maker=True)
            - kalshi_fee(CONTRACTS, t.peak_price - 0.08, maker=False)
            for t in near_misses
        ]
        md.append(
            "| Count | Mean entry | Mean peak | Mean P&L trail-$0.05 | Mean P&L trail-$0.08 |\n"
            "|---:|---:|---:|---:|---:|\n"
            f"| {len(near_misses)} | "
            f"${np.mean(entries):.3f} | "
            f"${np.mean(peaks):.3f} | "
            f"${np.mean(cap5):+.2f} | "
            f"${np.mean(cap8):+.2f} |\n"
        )

    # 3D: time to levels
    md.append("\n### 3D — Time to key levels (games that reach)\n\n")
    md.append(
        "| Level | Games reaching | Median ticks | Median minutes |\n"
        "|---|---:|---:|---:|\n"
    )
    for level, ticks_list in time_to_levels.items():
        if not ticks_list:
            md.append(f"| ${level:.2f} | 0 | — | — |\n")
            continue
        med = int(np.median(ticks_list))
        md.append(
            f"| ${level:.2f} | {len(ticks_list)} | {med} | "
            f"{med * BUCKET_SEC / 60:.1f} |\n"
        )

    # Section 4
    md.append("\n## Section 4 — Best config deep dive + spread/entry buckets\n")
    for i, (res, spread_buckets, entry_bands) in enumerate(top3_breakdowns, 1):
        md.append(
            f"\n### Top {i}: `{res.cfg.name}` "
            f"(annual EV ${res.annual_ev:+,.0f})\n"
        )
        md.append("\n**Exit type distribution:**\n\n")
        md.append("| Exit type | Count | % | Mean P&L |\n|---|---:|---:|---:|\n")
        for et, cnt in sorted(
            res.exit_counts.items(), key=lambda kv: -kv[1],
        ):
            pnls = res.exit_pnls_by_type[et]
            md.append(
                f"| {et} | {cnt} | "
                f"{100 * cnt / res.entries:.1f}% | "
                f"${np.mean(pnls):+.2f} |\n"
            )
        md.append("\n**Spread-bucket breakdown:**\n\n")
        md.append(
            "| |Spread| | Games | Entries | Mean P&L | Annual EV |\n"
            "|---|---:|---:|---:|---:|\n"
        )
        for lab, _, _ in SPREAD_BUCKETS:
            b = spread_buckets.get(lab, {})
            if not b or b.get("entries", 0) == 0:
                md.append(
                    f"| {lab} | {b.get('n_games', 0)} | 0 | — | $0 |\n"
                )
                continue
            md.append(
                f"| {lab} | {b['n_games']} | {b['entries']} | "
                f"${b['mean_pnl']:+.2f} | "
                f"${b['annual_ev']:+,.0f} |\n"
            )
        md.append("\n**Entry price band breakdown:**\n\n")
        md.append(
            "| Entry band | Count | Mean P&L | Target hit % |\n"
            "|---|---:|---:|---:|\n"
        )
        for row in entry_bands:
            if row["count"] == 0:
                md.append(f"| {row['label']} | 0 | — | — |\n")
                continue
            md.append(
                f"| {row['label']} | {row['count']} | "
                f"${row['mean_pnl']:+.2f} | "
                f"{row['target_pct']:.1f}% |\n"
            )

    # Section 5
    md.append("\n## Section 5 — Comparison to prior S1 estimates\n\n")
    best = sorted_sweep[0]
    md.append(
        "| Metric | Prior bilateral sim (flawed) | Hold-to-resolution | Best swing config |\n"
        "|---|---:|---:|---:|\n"
        "| Framing | Bilateral arbitrage | Buy-and-hold | Underdog swing |\n"
        f"| Entry | Policy A, ≤$0.35 | Policy A, ≤$0.35 | Policy A, ≤$0.35 |\n"
        f"| Exit | T5 + bilateral (incompatible) | Resolution only | `{best.cfg.name}` |\n"
        f"| Annual EV | +$5,603 (invalid) | "
        f"${hold_res_baseline.annual_ev:+,.0f} | "
        f"${best.annual_ev:+,.0f} |\n"
        f"| Logically consistent | NO | YES | YES |\n"
    )
    md.append(
        "\n### Bilateral-equivalence math\n\n"
        "```\n"
        "Bilateral:  buy at $0.20 + buy other side at $0.35 = $0.55 cost\n"
        "            Resolution pays $1.00. Gross = $0.45.\n"
        "Swing sell: buy at $0.20, sell at $0.65 = $0.45 gross.\n"
        "            Identical economics, simpler execution.\n"
        "```\n"
        "\nThe bilateral and swing framings are arithmetically "
        "equivalent when both legs clear and when the swing sells at "
        "the complementary price. The swing version is the correct "
        "engine-level abstraction: single position, single exit rule, "
        "no leg-1/leg-2 queue priority concerns, no partial-fill "
        "stranding.\n"
    )

    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading Kalshi paired dataset (all spreads)...")
    games = load_kalshi_games_all_spreads()
    log(f"  {len(games)} games loaded")
    ctxs = prepare_games(games)
    log(f"  {len(ctxs)} games with resolvable outcome")

    log("Section 1: hold-to-resolution baselines...")
    baselines = section1_baselines(ctxs)
    for r in baselines:
        log(
            f"  ≤ ${r['threshold']:.2f}: {r['n_entered']} entries, "
            f"annual EV ${r['annual_ev']:+,.0f}"
        )

    log("Section 2: exit strategy sweep...")
    sweep_configs = build_sweep_configs()
    sweep_results: list[ConfigResult] = []
    for cfg in sweep_configs:
        sweep_results.append(evaluate_config(
            ctxs, BASELINE_ENTRY_THRESHOLD, cfg,
        ))
    log(f"  evaluated {len(sweep_results)} configs")
    sorted_sweep = sorted(sweep_results, key=lambda r: -r.annual_ev)
    best = sorted_sweep[0]
    log(
        f"  best: {best.cfg.name} → ${best.annual_ev:+,.0f}/yr "
        f"({best.entries} entries)"
    )

    # Hold-to-resolution baseline at 0.35 for direct comparison
    hold_baseline = evaluate_config(
        ctxs, BASELINE_ENTRY_THRESHOLD,
        ExitConfig(name="hold-to-resolution"),
    )

    log("Section 3: price trajectory characterization...")
    trajectory_facts = characterize_trajectories(ctxs)
    log(f"  {len(trajectory_facts)} trajectories")
    time_to_levels: dict[float, list[int]] = {}
    for level in [0.30, 0.40, 0.50, 0.60, 0.65, 0.80]:
        time_to_levels[level] = time_to_level(ctxs, level)
    # Near-miss trail stats computed inline in render

    log("Section 4: top 3 breakdowns...")
    top3_breakdowns: list[tuple[ConfigResult, dict, list[dict]]] = []
    for res in sorted_sweep[:3]:
        spread = spread_breakdown(
            ctxs, res.cfg, BASELINE_ENTRY_THRESHOLD,
        )
        entry_bands = entry_band_breakdown(res.outcomes)
        top3_breakdowns.append((res, spread, entry_bands))

    log("Rendering report...")
    md = render_report(
        n_games=len(ctxs), baselines=baselines,
        sweep_results=sweep_results,
        hold_res_baseline=hold_baseline,
        trajectory_facts=trajectory_facts,
        time_to_levels=time_to_levels,
        top3_breakdowns=top3_breakdowns,
        near_miss_trail_stats={},
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
