"""Strategy 4B revalidation on the 404-game Kalshi paired dataset.

Answers three questions:

1. Does S4B's +$1,105/yr (168-game sample, |spread| ≤ 6) hold on
   the full 404-game dataset?
2. Which spread buckets contribute or destroy value?
3. Does S4B add incremental EV on top of S1 bilateral, or is the
   underdog-swing value already captured by S1's stranded-leg
   mechanics (since S1 Policy A enters every game on whichever
   side is ≤ $0.35, usually the underdog at tip-off)?

Reuses `simulate_s4b` / `summarize_s4b` from
`analysis.strategy4_dip_recovery` and `simulate_policy` from
`analysis.strategy1_bilateral_sim` so all three strategies share
identical entry/exit mechanics.

Run:
    python -m analysis.strategy4b_revalidation
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    CONTRACT_SIZE,
    COMP_FRACTION,
    REG_SEASON_GAMES,
    S4BConfig,
    S4BTrade,
    _precompute_trailing_min,
    load_kalshi_games_all_spreads,
    simulate_s4b,
    summarize_s4b,
)
from analysis.strategy1_bilateral_sim import (
    SPREAD_BUCKETS,
    bucket_for,
    prepare_games,
    simulate_policy,
    stranded_time_abandon_pnl,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "strategy4b_revalidation.md"
)

# Prior S4B result on 168 games (|spread| ≤ 6).
PRIOR_168_ANNUAL_EV = 1105
PRIOR_168_GAMES = 168
PRIOR_168_CONFIG_DESC = (
    "momentum, entry $0.25-$0.35, run $0.03, lookback 300s, "
    "exit +$0.20, hybrid 50/50"
)

# Sweep grids (prompt-specified).
MOMENTUM_ENTRY_LOS = [0.10, 0.15, 0.20, 0.25]
MOMENTUM_ENTRY_HIS = [0.25, 0.30, 0.35]
MOMENTUM_RUN_AMOUNTS = [0.03, 0.05]
MOMENTUM_LOOKBACKS = [180, 300]
EXIT_DELTAS = [0.10, 0.15, 0.20]
HYBRID_FRACS = [0.0, 0.5, 1.0]   # 0.0 = pure swing, 1.0 = pure hold
STOP_VARIANTS = [0.05, 0.10, 1.00]  # 1.00 = "no stop" (effective floor $0.01)
STATIC_THRESHOLDS = [0.15, 0.20, 0.25, 0.30, 0.35]

# S1 overlap parameters
S1_POLICY = "A"
S1_X = 0.20
S1_Y = 0.35
T5_TICKS = 10
OVERLAP_PRICE_WINDOW = 0.05
OVERLAP_TICK_WINDOW = 20


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


# ---- Sweep infrastructure ---------------------------------------------

@dataclass
class SweepResult:
    label: str
    cfg: S4BConfig
    hybrid_frac: float
    stop_variant: float          # nominal stop_offset label (0.05 / 0.10 / 1.00)
    entries: int
    n_target: int
    n_stop: int
    n_held: int
    n_res_win: int
    n_res_loss: int
    hit_pct: float
    mean_pnl: float
    total_pnl: float
    annual_ev: float
    trades: list[S4BTrade]


def _cfg_to_label(cfg: S4BConfig, hybrid_frac: float, stop_variant: float) -> str:
    if cfg.mode == "momentum":
        body = (
            f"mom ${cfg.entry_lo:.2f}-${cfg.entry_hi:.2f} "
            f"run${cfg.run_size:.2f} lb{cfg.lookback_sec}s "
            f"+${cfg.exit_offset:.2f}"
        )
    else:
        body = (
            f"static ≤${cfg.entry_hi:.2f} +${cfg.exit_offset:.2f}"
        )
    if hybrid_frac == 0.0:
        h = "swing"
    elif hybrid_frac == 0.5:
        h = "hybrid50"
    else:
        h = "hold"
    sv = "nostop" if stop_variant >= 1.0 else f"stop${stop_variant:.2f}"
    return f"{body} {h} {sv}"


def _build_config(
    mode: str,
    entry_lo: float, entry_hi: float,
    exit_delta: float, hybrid_frac: float, stop_variant: float,
    run_size: float | None = None, lookback_sec: int | None = None,
) -> S4BConfig:
    """Build an S4BConfig. Pure-hold (hybrid_frac=1.0) is modeled by
    setting exit_offset so high that target never fires; stop_variant
    of 1.0 sets stop so deep it never fires (effective floor $0.01)."""
    hybrid = (hybrid_frac == 0.5)
    if hybrid_frac == 1.0:
        # Pure hold: prevent target trigger by making exit unreachable.
        effective_exit = 1.00
    else:
        effective_exit = exit_delta
    return S4BConfig(
        label="",  # filled later
        mode=mode,
        lookback_sec=lookback_sec if mode == "momentum" else None,
        entry_lo=entry_lo, entry_hi=entry_hi,
        run_size=run_size if mode == "momentum" else None,
        exit_offset=effective_exit,
        stop_offset=stop_variant,
        hybrid=hybrid,
    )


def _evaluate_config(
    games: list[dict], cfg: S4BConfig,
    precomp_min: dict[tuple[str, int], np.ndarray],
    hybrid_frac: float, stop_variant: float,
) -> SweepResult:
    trades = simulate_s4b(games, cfg, precomp_min)
    summary = summarize_s4b(trades, len(games))
    # Classify trades beyond summarize_s4b's categories
    n_target = 0
    n_stop = 0
    n_held = 0
    n_res_win = 0
    n_res_loss = 0
    for t in trades:
        et = t.exit_type
        if "target" in et:
            n_target += 1
        elif "stop" in et:
            n_stop += 1
        if "resolution_win" in et:
            n_res_win += 1
        elif "resolution_loss" in et:
            n_res_loss += 1
        elif "resolution" in et:
            n_held += 1
    n_held = n_held + n_res_win + n_res_loss
    hit_pct = (100.0 * n_target / len(trades)) if trades else 0.0
    return SweepResult(
        label=_cfg_to_label(cfg, hybrid_frac, stop_variant),
        cfg=cfg, hybrid_frac=hybrid_frac, stop_variant=stop_variant,
        entries=len(trades),
        n_target=n_target, n_stop=n_stop, n_held=n_held,
        n_res_win=n_res_win, n_res_loss=n_res_loss,
        hit_pct=hit_pct,
        mean_pnl=summary.get("mean_pnl", 0.0),
        total_pnl=sum(t.net_pnl for t in trades),
        annual_ev=summary.get("annual_ev", 0.0),
        trades=trades,
    )


def run_sweep(
    games: list[dict],
    precomp_min: dict[tuple[str, int], np.ndarray],
) -> list[SweepResult]:
    results: list[SweepResult] = []
    # Momentum configs
    for entry_lo in MOMENTUM_ENTRY_LOS:
        for entry_hi in MOMENTUM_ENTRY_HIS:
            if entry_hi <= entry_lo:
                continue
            for rs in MOMENTUM_RUN_AMOUNTS:
                for lb in MOMENTUM_LOOKBACKS:
                    for ed in EXIT_DELTAS:
                        for hf in HYBRID_FRACS:
                            for sv in STOP_VARIANTS:
                                cfg = _build_config(
                                    "momentum", entry_lo, entry_hi,
                                    ed, hf, sv, run_size=rs, lookback_sec=lb,
                                )
                                results.append(_evaluate_config(
                                    games, cfg, precomp_min, hf, sv,
                                ))
    # Static configs
    for thr in STATIC_THRESHOLDS:
        for ed in EXIT_DELTAS:
            for hf in HYBRID_FRACS:
                for sv in STOP_VARIANTS:
                    cfg = _build_config(
                        "static", 0.01, thr, ed, hf, sv,
                    )
                    results.append(_evaluate_config(
                        games, cfg, precomp_min, hf, sv,
                    ))
    return results


# ---- 168-game subset comparison --------------------------------------

def _subset_to_spread(
    games: list[dict], max_spread: float,
) -> list[dict]:
    return [g for g in games if g["abs_spread"] <= max_spread]


def compare_168_vs_404(
    games_all: list[dict],
    best_cfg_result: SweepResult,
) -> dict:
    subset = _subset_to_spread(games_all, 6.0)
    # Reuse the same precomputed min (need to filter for subset tickers)
    lookbacks = (
        [best_cfg_result.cfg.lookback_sec]
        if best_cfg_result.cfg.lookback_sec is not None else []
    )
    precomp_min_subset: dict[tuple[str, int], np.ndarray] = {}
    for lb in lookbacks:
        lb_bins = max(1, int(lb / BUCKET_SEC))
        for g in subset:
            dog = 1.0 - g["ts"]["fav_kalshi_vwap"].values
            precomp_min_subset[(g["ticker"], lb_bins)] = (
                _precompute_trailing_min(dog, lb_bins)
            )
    res_subset = _evaluate_config(
        subset, best_cfg_result.cfg, precomp_min_subset,
        best_cfg_result.hybrid_frac, best_cfg_result.stop_variant,
    )
    return {
        "full_404": {
            "n_games": len(games_all), "result": best_cfg_result,
        },
        "subset_168_like": {
            "n_games": len(subset), "result": res_subset,
        },
    }


# ---- Spread bucket breakdown -----------------------------------------

def bucket_breakdown(
    games_all: list[dict], sweep_result: SweepResult,
    precomp_min: dict[tuple[str, int], np.ndarray],
) -> dict[str, dict]:
    bucket_games: dict[str, list[dict]] = {
        lab: [] for lab, _, _ in SPREAD_BUCKETS
    }
    for g in games_all:
        lab = bucket_for(g["abs_spread"])
        if lab is not None:
            bucket_games[lab].append(g)
    out: dict[str, dict] = {}
    for lab, _, _ in SPREAD_BUCKETS:
        gs = bucket_games[lab]
        if not gs:
            out[lab] = {
                "n_games": 0, "entries": 0,
                "n_target": 0, "n_stop": 0, "n_res_win": 0,
                "n_res_loss": 0, "mean_pnl": 0.0, "annual_ev": 0.0,
            }
            continue
        res = _evaluate_config(
            gs, sweep_result.cfg, precomp_min,
            sweep_result.hybrid_frac, sweep_result.stop_variant,
        )
        out[lab] = {
            "n_games": len(gs), "entries": res.entries,
            "n_target": res.n_target, "n_stop": res.n_stop,
            "n_res_win": res.n_res_win, "n_res_loss": res.n_res_loss,
            "mean_pnl": res.mean_pnl, "annual_ev": res.annual_ev,
        }
    return out


# ---- Section 4: S1 overlap analysis ----------------------------------

@dataclass
class S1LegRef:
    ticker: str
    leg1_side: str            # "fav" or "dog"
    leg1_tick: int
    leg1_price: float
    t5_pnl: float
    leg2_filled: bool


def build_s1_refs(
    ctxs, bilat_entries,
) -> dict[str, S1LegRef]:
    """Build a ticker → S1 leg reference for games where S1 fired.

    For games that completed a bilateral (leg2_filled=True), the S1
    T5 P&L is not the exit — the bilateral produces a different
    outcome. For fair comparison with S4B, we compute the T5 P&L
    anyway (what S1 WOULD HAVE earned if the bilateral hadn't
    completed). This lets us ask: is S4B's exit better than S1's
    T5 exit on the same entry?
    """
    out: dict[str, S1LegRef] = {}
    for e in bilat_entries:
        t5_pnl = stranded_time_abandon_pnl(e, T5_TICKS, e.winner)
        out[e.game_ticker] = S1LegRef(
            ticker=e.game_ticker, leg1_side=e.leg1_side,
            leg1_tick=e.leg1_tick, leg1_price=e.leg1_price,
            t5_pnl=t5_pnl, leg2_filled=e.leg2_filled,
        )
    return out


@dataclass
class OverlapStats:
    n_overlap: int
    n_s4b_only: int
    mean_s1_pnl_overlap: float
    mean_s4b_pnl_overlap: float
    mean_delta_overlap: float
    mean_s4b_pnl_only: float
    total_s4b_pnl_overlap: float
    total_s4b_pnl_only: float
    total_s1_pnl_overlap: float


def classify_s4b_vs_s1(
    s4b_trades: list[S4BTrade],
    s1_refs: dict[str, S1LegRef],
) -> OverlapStats:
    """For each S4B trade, decide whether it overlaps with S1's leg 1.

    Overlap iff: same game, S1 leg1 is on dog side, entry price within
    $0.05, entry tick within 20 ticks.
    """
    overlap_s1_pnls: list[float] = []
    overlap_s4b_pnls: list[float] = []
    only_s4b_pnls: list[float] = []
    for t in s4b_trades:
        s1 = s1_refs.get(t.ticker)
        if s1 is None or s1.leg1_side != "dog":
            only_s4b_pnls.append(t.net_pnl)
            continue
        price_close = abs(t.entry_price - s1.leg1_price) <= OVERLAP_PRICE_WINDOW
        tick_close = abs(t.entry_idx - s1.leg1_tick) <= OVERLAP_TICK_WINDOW
        if price_close and tick_close:
            overlap_s1_pnls.append(s1.t5_pnl)
            overlap_s4b_pnls.append(t.net_pnl)
        else:
            only_s4b_pnls.append(t.net_pnl)
    deltas = [
        s4b - s1 for s4b, s1 in zip(overlap_s4b_pnls, overlap_s1_pnls)
    ]
    return OverlapStats(
        n_overlap=len(overlap_s1_pnls),
        n_s4b_only=len(only_s4b_pnls),
        mean_s1_pnl_overlap=(
            float(np.mean(overlap_s1_pnls)) if overlap_s1_pnls else 0.0
        ),
        mean_s4b_pnl_overlap=(
            float(np.mean(overlap_s4b_pnls)) if overlap_s4b_pnls else 0.0
        ),
        mean_delta_overlap=(
            float(np.mean(deltas)) if deltas else 0.0
        ),
        mean_s4b_pnl_only=(
            float(np.mean(only_s4b_pnls)) if only_s4b_pnls else 0.0
        ),
        total_s4b_pnl_overlap=float(sum(overlap_s4b_pnls)),
        total_s4b_pnl_only=float(sum(only_s4b_pnls)),
        total_s1_pnl_overlap=float(sum(overlap_s1_pnls)),
    )


# ---- Report rendering --------------------------------------------------

def render_report(
    games: list[dict],
    all_results: list[SweepResult],
    best: SweepResult, top_10: list[SweepResult],
    comparison_168_404: dict,
    bucket_break: dict[str, dict[str, dict]],
    overlap: OverlapStats,
    s4b_trades: list[S4BTrade],
) -> str:
    md: list[str] = []
    md.append("# Strategy 4B Revalidation (404-Game Dataset)\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Full S4B config sweep on **{len(games)} games** from the "
        "Kalshi-confirmed paired dataset (all spreads). Prior S4B "
        f"result on {PRIOR_168_GAMES} games (|spread| ≤ 6) was "
        f"+${PRIOR_168_ANNUAL_EV}/yr with a fragile 12.6% resolution-"
        "win rate — this revalidation tests whether that holds on the "
        "larger dataset, adds stop-loss variants not in the original, "
        "breaks down by spread bucket, and quantifies overlap with S1 "
        "bilateral's stranded-leg mechanics.\n"
    )
    md.append(
        "\n**Data approximation (inherited from parent):** `dog_vwap` "
        "is computed as `1 - fav_kalshi_vwap`. Kalshi bid-ask spread "
        "(1-2c typical) is not modeled. Directional findings are "
        "robust; absolute EV should be read as an upper bound.\n"
    )

    # ---- Section 1 ----------------------------------------------
    md.append(
        "\n## Section 1 — S4B config sweep (momentum + static × "
        "hybrid × stop)\n"
    )
    md.append(
        f"Total configs tested: **{len(all_results)}**. Top 10 by "
        "annual EV:\n\n"
        "| # | Label | Entries | Target | Stop | Held | Res win | "
        "Res loss | Mean P&L | Annual EV |\n"
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for i, r in enumerate(top_10, 1):
        md.append(
            f"| {i} | {r.label} | {r.entries} | {r.n_target} | "
            f"{r.n_stop} | {r.n_held} | {r.n_res_win} | "
            f"{r.n_res_loss} | ${r.mean_pnl:+.2f} | "
            f"${r.annual_ev:+,.0f} |\n"
        )
    # Positive vs negative split
    positive = sum(1 for r in all_results if r.annual_ev > 0)
    neutral = sum(1 for r in all_results if abs(r.annual_ev) <= 50)
    md.append(
        f"\nAcross all {len(all_results)} configs: "
        f"**{positive} positive EV** ({100*positive/len(all_results):.1f}%), "
        f"**{len(all_results) - positive} non-positive**. "
        f"Near-breakeven (|annual EV| ≤ $50): {neutral}.\n"
    )

    # ---- Section 2 ----------------------------------------------
    md.append("\n## Section 2 — Best config deep dive\n")
    md.append(f"**Best config:** `{best.label}`\n\n")
    md.append(
        f"- Entries: {best.entries}\n"
        f"- Target (swing) exits: {best.n_target} "
        f"({100*best.n_target/max(1,best.entries):.1f}%)\n"
        f"- Stop exits: {best.n_stop} "
        f"({100*best.n_stop/max(1,best.entries):.1f}%)\n"
        f"- Held to resolution: {best.n_held} "
        f"({100*best.n_held/max(1,best.entries):.1f}%)\n"
        f"  - Resolution wins: {best.n_res_win}\n"
        f"  - Resolution losses: {best.n_res_loss}\n"
        f"- Mean P&L: ${best.mean_pnl:+.2f}\n"
        f"- Total P&L: ${best.total_pnl:+,.2f}\n"
        f"- Annual EV: ${best.annual_ev:+,.0f}\n"
    )

    # Hold-time distribution (entry_idx to exit_idx)
    hold_bins = [t.exit_idx - t.entry_idx for t in best.trades]
    if hold_bins:
        arr = np.array(hold_bins) * BUCKET_SEC  # seconds
        md.append(
            "\nHold time (seconds): "
            f"median {int(np.median(arr))}s, "
            f"P25 {int(np.quantile(arr, 0.25))}s, "
            f"P75 {int(np.quantile(arr, 0.75))}s, "
            f"max {int(arr.max())}s\n"
        )

    # Per-game entry count
    per_game = Counter(t.ticker for t in best.trades)
    md.append(
        f"\nPer-game entry distribution: "
        f"{sum(1 for v in per_game.values() if v == 1)} games with 1 entry, "
        f"{sum(1 for v in per_game.values() if v == 2)} games with 2 entries, "
        f"{len(games) - len(per_game)} games with 0 entries\n"
    )

    # 168 vs 404 comparison
    md.append("\n### 168-game subset vs full 404-game\n\n")
    sub = comparison_168_404["subset_168_like"]["result"]
    md.append(
        "| Metric | 168-game subset (|spread| ≤ 6) | Full 404-game |\n"
        "|---|---:|---:|\n"
        f"| Games | {comparison_168_404['subset_168_like']['n_games']} "
        f"| {comparison_168_404['full_404']['n_games']} |\n"
        f"| Entries | {sub.entries} | {best.entries} |\n"
        f"| Target exits | {sub.n_target} | {best.n_target} |\n"
        f"| Mean P&L | ${sub.mean_pnl:+.2f} | ${best.mean_pnl:+.2f} |\n"
        f"| Annual EV | ${sub.annual_ev:+,.0f} | "
        f"${best.annual_ev:+,.0f} |\n"
    )
    md.append(
        f"\nPrior published result (different config): "
        f"+${PRIOR_168_ANNUAL_EV}/yr on {PRIOR_168_GAMES} games with "
        f"{PRIOR_168_CONFIG_DESC}. The revalidation sweep may select "
        "a different 'best' config — direct comparison against the "
        "published number is heuristic, not strict.\n"
    )

    # ---- Section 3 ----------------------------------------------
    md.append("\n## Section 3 — Spread bucket breakdown (top 3 configs)\n")
    for i, r in enumerate(top_10[:3], 1):
        md.append(
            f"\n### Top {i}: `{r.label}` — annual EV "
            f"${r.annual_ev:+,.0f}\n\n"
            "| |Spread| | Games | Entries | Swing exits | Res wins | "
            "Res losses | Mean P&L | Annual EV |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|\n"
        )
        buckets = bucket_break.get(r.label, {})
        for lab, _, _ in SPREAD_BUCKETS:
            b = buckets.get(lab, {})
            if not b or b.get("entries", 0) == 0:
                md.append(
                    f"| {lab} | {b.get('n_games', 0)} | 0 | 0 | 0 | 0 "
                    "| — | $0 |\n"
                )
                continue
            flag = " ⚠" if b["annual_ev"] < 0 else ""
            md.append(
                f"| {lab} | {b['n_games']} | {b['entries']} | "
                f"{b['n_target']} | {b['n_res_win']} | "
                f"{b['n_res_loss']} | ${b['mean_pnl']:+.2f} | "
                f"${b['annual_ev']:+,.0f}{flag} |\n"
            )
        neg_buckets = [
            lab for lab in buckets
            if buckets[lab].get("annual_ev", 0) < 0
        ]
        if neg_buckets:
            md.append(
                f"\n_Negative-EV buckets: {', '.join(neg_buckets)}_\n"
            )

    # ---- Section 4 ----------------------------------------------
    md.append("\n## Section 4 — S1 overlap analysis\n")
    md.append(
        "S1 bilateral Policy A fires leg 1 on every game at the "
        "first tick where either side's YES bid ≤ $0.35 (typically "
        "the underdog at tip-off). S4B is always on the dog side at "
        "$0.10-$0.35 with a momentum trigger. Substantial overlap is "
        "possible. This section quantifies whether S4B adds "
        "incremental value or just repackages value S1 already "
        "captures.\n\n"
        "**Overlap definition:** S4B trade overlaps S1 iff same game, "
        f"S1 leg1 is on dog side, entry prices within "
        f"${OVERLAP_PRICE_WINDOW:.2f}, entry ticks within "
        f"{OVERLAP_TICK_WINDOW}. S1 P&L is its T5 exit P&L "
        "(what S1 earns on that leg — note: bilateral-completing S1 "
        "entries get a different actual exit; T5 P&L is used here as "
        "the counterfactual comparison to S4B's exit rule on the "
        "same entry).\n\n"
        "| Category | Count | Mean S1 P&L | Mean S4B P&L | Mean delta | Total S4B P&L |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    md.append(
        f"| Overlapping entries | {overlap.n_overlap} | "
        f"${overlap.mean_s1_pnl_overlap:+.2f} | "
        f"${overlap.mean_s4b_pnl_overlap:+.2f} | "
        f"${overlap.mean_delta_overlap:+.2f} | "
        f"${overlap.total_s4b_pnl_overlap:+,.2f} |\n"
        f"| S4B-only entries | {overlap.n_s4b_only} | n/a | "
        f"${overlap.mean_s4b_pnl_only:+.2f} | n/a | "
        f"${overlap.total_s4b_pnl_only:+,.2f} |\n"
        f"| **Combined S4B total** | "
        f"**{overlap.n_overlap + overlap.n_s4b_only}** | — | — | — | "
        f"**${overlap.total_s4b_pnl_overlap + overlap.total_s4b_pnl_only:+,.2f}** |\n"
    )
    total_s4b = overlap.total_s4b_pnl_overlap + overlap.total_s4b_pnl_only
    incremental_pnl = (
        overlap.total_s4b_pnl_only
        + (overlap.total_s4b_pnl_overlap - overlap.total_s1_pnl_overlap)
    )
    incremental_annual = (
        incremental_pnl / len(games)
        * REG_SEASON_GAMES * COMP_FRACTION
    )
    md.append(
        f"\n**Incremental value calculation (if running S4B on top "
        f"of S1):**\n"
        f"- S4B-only entries contribute full P&L: "
        f"${overlap.total_s4b_pnl_only:+,.2f}\n"
        f"- Overlapping entries contribute the delta vs S1's T5 "
        f"exit: ${overlap.total_s4b_pnl_overlap - overlap.total_s1_pnl_overlap:+,.2f}\n"
        f"- **Total incremental P&L: "
        f"${incremental_pnl:+,.2f}** on {len(games)} games → "
        f"**${incremental_annual:+,.0f}/yr incremental**\n"
    )
    md.append(
        f"\nFor reference, S4B standalone annual EV: "
        f"${best.annual_ev:+,.0f}/yr. Subtracting the S1-redundant "
        f"portion yields the incremental figure above.\n"
    )

    # ---- Section 5 ----------------------------------------------
    md.append("\n## Section 5 — Verdict and recommendation\n")

    # Does S4B survive revalidation?
    md.append("\n### 1. Does S4B survive revalidation?\n")
    if best.annual_ev >= PRIOR_168_ANNUAL_EV * 0.7:
        survive_label = "STABLE"
    elif best.annual_ev >= PRIOR_168_ANNUAL_EV * 0.3:
        survive_label = "DEGRADED"
    elif best.annual_ev > 0:
        survive_label = "WEAKENED"
    else:
        survive_label = "FAILED"
    md.append(
        f"- Best config annual EV: **${best.annual_ev:+,.0f}/yr** on "
        f"404 games (vs prior +${PRIOR_168_ANNUAL_EV}/yr on 168 "
        "games, different config).\n"
        f"- Verdict: **{survive_label}**.\n"
    )

    # Is S4B incremental to S1?
    md.append("\n### 2. Is S4B incremental to S1?\n")
    # Decision thresholds
    if incremental_annual >= 500 and overlap.n_s4b_only >= 20:
        incr_label = "INCREMENTAL"
        incr_note = (
            "S4B adds meaningful EV on top of S1. Build as separate "
            "engine module."
        )
    elif incremental_annual <= 100:
        incr_label = "SUBSTITUTIVE"
        incr_note = (
            "S4B's value is already captured by S1's stranded-leg "
            "mechanics. Do not build — running S4B alongside S1 adds "
            "little or negative incremental EV."
        )
    elif overlap.mean_delta_overlap > 1.0:
        incr_label = "COMPLEMENTARY"
        incr_note = (
            "S4B's exit rule is meaningfully better than S1's T5 exit "
            "on overlapping entries. Consider replacing T5 with "
            "S4B-style swing exits in S1's stranded-leg management, "
            "rather than building S4B as a separate module."
        )
    else:
        incr_label = "MARGINAL"
        incr_note = (
            "Incremental EV is small and the exit-rule delta is "
            "modest. S4B as a separate module is hard to justify."
        )
    md.append(
        f"- Overlap rate: **{overlap.n_overlap} / "
        f"{overlap.n_overlap + overlap.n_s4b_only} S4B entries "
        f"({100*overlap.n_overlap/max(1,overlap.n_overlap + overlap.n_s4b_only):.1f}%)** "
        f"overlap with S1 leg 1.\n"
        f"- S4B-only (purely incremental) entries: "
        f"{overlap.n_s4b_only}.\n"
        f"- Mean delta on overlapping entries: "
        f"**${overlap.mean_delta_overlap:+.2f}** "
        f"(S4B exit vs S1 T5 exit).\n"
        f"- Incremental annual EV: **${incremental_annual:+,.0f}/yr**.\n"
        f"- Verdict: **{incr_label}**. {incr_note}\n"
    )

    # Updated alpha stack
    md.append("\n### 3. Updated alpha stack\n")
    if incr_label == "INCREMENTAL":
        s4b_contribution = f"+${incremental_annual:,.0f}/yr"
        stack_note = (
            "S4B adds as a separate module alongside S1."
        )
    elif incr_label == "SUBSTITUTIVE":
        s4b_contribution = "$0 (already in S1)"
        stack_note = (
            "S4B is absorbed into S1. No separate module."
        )
    elif incr_label == "COMPLEMENTARY":
        s4b_contribution = (
            f"Replace S1 T5 with S4B exit → "
            f"+${overlap.mean_delta_overlap * overlap.n_overlap * (REG_SEASON_GAMES * COMP_FRACTION / len(games)):,.0f}/yr "
            "estimated lift on S1"
        )
        stack_note = (
            "S4B informs S1 exit design rather than running as its "
            "own module."
        )
    else:
        s4b_contribution = f"~+${incremental_annual:,.0f}/yr "
        "(marginal)"
        stack_note = (
            "S4B effect is marginal. Deferred — focus Phase 4a "
            "build on S1 + S4A."
        )
    md.append(
        "| Strategy | Annual EV contribution |\n"
        "|---|---:|\n"
        f"| S4A (core, |spread| ≤ 6) | +$7,075 |\n"
        f"| S4A (expansion, |spread| > 6) | +$3,644 |\n"
        f"| S1 bilateral | +$4,000-$5,600 |\n"
        f"| S3 filtered | +$578-$825 |\n"
        f"| **S4B (revalidated)** | **{s4b_contribution}** |\n"
    )
    md.append(f"\n{stack_note}\n")

    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading 404-game Kalshi paired dataset...")
    games = load_kalshi_games_all_spreads()
    log(f"  {len(games)} games loaded")

    log("Precomputing trailing-min series for momentum configs...")
    precomp_min: dict[tuple[str, int], np.ndarray] = {}
    for lb in MOMENTUM_LOOKBACKS:
        lb_bins = max(1, int(lb / BUCKET_SEC))
        for g in games:
            dog = 1.0 - g["ts"]["fav_kalshi_vwap"].values
            precomp_min[(g["ticker"], lb_bins)] = (
                _precompute_trailing_min(dog, lb_bins)
            )

    log(
        "Sweeping S4B configs (momentum × hybrid × stop + static)..."
    )
    all_results = run_sweep(games, precomp_min)
    log(f"  {len(all_results)} configs evaluated")

    all_results.sort(key=lambda r: -r.annual_ev)
    top_10 = all_results[:10]
    best = top_10[0]
    log(
        f"  best: {best.label} → ${best.annual_ev:+,.0f}/yr "
        f"({best.entries} entries, {best.n_target} targets)"
    )

    log("Comparing 168-game subset vs full 404-game...")
    comparison = compare_168_vs_404(games, best)

    log("Spread bucket breakdown for top 3 configs...")
    bucket_break: dict[str, dict[str, dict]] = {}
    for r in top_10[:3]:
        # Need the per-config precomp (shared since lookback fixed)
        bucket_break[r.label] = bucket_breakdown(games, r, precomp_min)

    log("Running S1 baseline for overlap analysis...")
    ctxs = prepare_games(games)
    s1_entries = simulate_policy(ctxs, S1_POLICY, S1_X, S1_Y)
    s1_refs = build_s1_refs(ctxs, s1_entries)
    log(f"  S1 entries: {len(s1_entries)} "
        f"({sum(1 for e in s1_entries if e.leg1_side == 'dog')} on dog side)")
    overlap = classify_s4b_vs_s1(best.trades, s1_refs)
    log(
        f"  overlap: {overlap.n_overlap} overlapping, "
        f"{overlap.n_s4b_only} S4B-only"
    )

    log("Rendering report...")
    md = render_report(
        games=games, all_results=all_results,
        best=best, top_10=top_10,
        comparison_168_404=comparison,
        bucket_break=bucket_break,
        overlap=overlap,
        s4b_trades=best.trades,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
