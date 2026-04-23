"""S4A stop-execution parameter sweep.

Sweeps the NO-side resting bid level and severe-gap fallback threshold
across the 132 S4A stop events identified by the stop execution study.
For each (NO_bid, fallback_threshold) cell, re-prices every stop's
P&L under the operational model described in PHASE4A_DESIGN.md
Decision 6 and reports full-strategy annual EV.

The NO-bid side is the primary knob: lower NO_bid (higher YES
equivalent) means earlier exit at a less-painful price but fewer
chances to actually fill. The fallback_threshold governs when the
engine cancels a stalled resting order and taker-exits on a severe
gap; a higher fallback fires more often and salvages more value
versus letting the VWAP drift to the bin's worst.

Interpretation note: the prompt's literal step 3 has the fallback
taker-exit at `stop_vwap`, which makes fallback P&L-inert. We
implement the *operational* interpretation instead — when the
engine detects VWAP ≤ fallback, it submits a market sell and fills
at approximately the fallback level (modeled as `fallback` exactly,
with taker fees). This matches the engine behavior described in
Decision 6 and makes the fallback parameter a meaningful knob.

Run:
    python -m analysis.strategy4_stop_params
"""

from __future__ import annotations

import math
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
    S4AConfig,
    S4ATrade,
    _precompute_trailing_max,
    load_kalshi_games_all_spreads,
    simulate_s4a,
)
from analysis.strategy4_stop_execution import (
    CFG,
    StopEvent,
    annotate_gaps,
    identify_stops,
    load_game_labels,
    taker_fee,
)
from analysis.strategy4_dip_recovery import maker_fee

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy4_stop_params.md"
)

NO_BIDS = [0.58, 0.59, 0.60, 0.61, 0.62, 0.63, 0.64, 0.65]
FALLBACKS = [0.30, 0.32, 0.34, 0.36, 0.38]
DEFAULT_NO_BID = 0.60
DEFAULT_FALLBACK = 0.34

BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 42


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


# ---- Per-stop repricing ------------------------------------------------

@dataclass
class RepricedStop:
    entry_price: float
    exit_price: float
    outcome: str        # maker_fill / taker_fallback / taker_unfilled
    pnl: float


def reprice_stop(
    ev: StopEvent, no_bid: float, fallback: float,
) -> RepricedStop:
    """Reprice one stop event under (no_bid, fallback).

    Outcomes (operational interpretation):
      - maker_fill:       fallback < stop_vwap ≤ yes_equiv.
                          Exit at yes_equiv, maker fees both legs.
      - taker_fallback:   stop_vwap ≤ fallback (severe gap, resting
                          order skipped). Exit at fallback, maker
                          entry + taker exit fees.
      - taker_unfilled:   stop_vwap > yes_equiv (VWAP didn't drop to
                          the resting bid). Exit at stop_vwap, maker
                          entry + taker exit fees.
    """
    yes_equiv = 1.0 - no_bid
    sv = ev.stop_vwap
    entry_fee = maker_fee(CONTRACT_SIZE, ev.entry_price)

    if sv <= fallback:
        exit_price = fallback
        exit_fee = taker_fee(CONTRACT_SIZE, exit_price)
        pnl = (exit_price - ev.entry_price) * CONTRACT_SIZE - entry_fee - exit_fee
        return RepricedStop(
            entry_price=ev.entry_price, exit_price=exit_price,
            outcome="taker_fallback", pnl=pnl,
        )
    if sv <= yes_equiv:
        exit_price = yes_equiv
        exit_fee = maker_fee(CONTRACT_SIZE, exit_price)
        pnl = (exit_price - ev.entry_price) * CONTRACT_SIZE - entry_fee - exit_fee
        return RepricedStop(
            entry_price=ev.entry_price, exit_price=exit_price,
            outcome="maker_fill", pnl=pnl,
        )
    exit_price = sv
    exit_fee = taker_fee(CONTRACT_SIZE, exit_price)
    pnl = (exit_price - ev.entry_price) * CONTRACT_SIZE - entry_fee - exit_fee
    return RepricedStop(
        entry_price=ev.entry_price, exit_price=exit_price,
        outcome="taker_unfilled", pnl=pnl,
    )


@dataclass
class CellResult:
    no_bid: float
    fallback: float
    yes_equiv: float
    maker_fills: int
    taker_fallbacks: int
    taker_unfilled: int
    avg_stop_price: float
    total_stop_pnl: float
    annual_ev: float
    per_stop: list[RepricedStop]


def evaluate_cell(
    no_bid: float, fallback: float, stops: list[StopEvent],
    non_stop_pnl: float, n_trades: int, n_games: int,
) -> CellResult | None:
    if fallback >= (1.0 - no_bid):
        return None
    reprices = [reprice_stop(ev, no_bid, fallback) for ev in stops]
    counts = Counter(r.outcome for r in reprices)
    exit_prices = [r.exit_price for r in reprices]
    stop_pnl = sum(r.pnl for r in reprices)
    total_pnl = non_stop_pnl + stop_pnl
    mean_pnl = total_pnl / n_trades if n_trades else 0.0
    epg = n_trades / n_games if n_games else 0.0
    annual_ev = mean_pnl * epg * REG_SEASON_GAMES * COMP_FRACTION
    return CellResult(
        no_bid=no_bid, fallback=fallback, yes_equiv=1.0 - no_bid,
        maker_fills=counts.get("maker_fill", 0),
        taker_fallbacks=counts.get("taker_fallback", 0),
        taker_unfilled=counts.get("taker_unfilled", 0),
        avg_stop_price=(
            float(np.mean(exit_prices)) if exit_prices else 0.0
        ),
        total_stop_pnl=stop_pnl, annual_ev=annual_ev,
        per_stop=reprices,
    )


# ---- Bootstrap ---------------------------------------------------------

def bootstrap_cell(
    stops: list[StopEvent], reprices: list[RepricedStop],
    non_stop_pnl: float, n_trades: int, n_games: int,
    n_iter: int, seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    pnls = np.array([r.pnl for r in reprices])
    n_stops = len(pnls)
    epg = n_trades / n_games if n_games else 0.0
    annual_scalar = epg * REG_SEASON_GAMES * COMP_FRACTION / max(1, n_trades)
    # bootstrap mean annual EV: for each resample, mean_pnl includes
    # non-stop (fixed) + bootstrapped stop contribution scaled.
    idx = rng.integers(0, n_stops, size=(n_iter, n_stops))
    boot_stop_totals = pnls[idx].sum(axis=1)
    totals = non_stop_pnl + boot_stop_totals
    means = totals / n_trades
    annual_evs = means * epg * REG_SEASON_GAMES * COMP_FRACTION
    return {
        "mean": float(annual_evs.mean()),
        "ci_lo": float(np.quantile(annual_evs, 0.025)),
        "ci_hi": float(np.quantile(annual_evs, 0.975)),
        "p_gt_zero": float((annual_evs > 0).mean()),
        "samples": annual_evs,
    }


# ---- Report rendering --------------------------------------------------

def fmt_price(p: float) -> str:
    return f"${p:.2f}"


def render_report(
    n_games: int, n_trades: int, stops: list[StopEvent],
    non_stop_pnl: float,
    all_cells: list[CellResult],
    baseline: CellResult,
    top3: list[CellResult],
    boots: dict[tuple[float, float], dict],
    baseline_boot: dict,
    marginal_nobid: list[tuple[float, CellResult, float, float]],
    marginal_fallback: list[tuple[float, CellResult, float]],
) -> str:
    md: list[str] = []
    md.append("# Strategy 4 — Stop Execution Parameter Sweep\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Sweeps the NO-side resting bid level "
        f"(${NO_BIDS[0]:.2f}–${NO_BIDS[-1]:.2f}) and severe-gap "
        f"fallback threshold (${FALLBACKS[0]:.2f}–"
        f"${FALLBACKS[-1]:.2f}) across "
        f"{len(stops)} S4A stop events from the 404-game "
        "Kalshi-confirmed dataset. Finds the "
        "(NO_bid, fallback_threshold) pair that maximizes annual "
        "EV under realistic execution.\n"
    )
    md.append(
        "\n**Interpretation note:** the fallback-fired case exits "
        "at the fallback price with taker fees (operational model: "
        "engine cancels the stalled resting order when VWAP crosses "
        "the fallback and market-sells at approximately that level). "
        "The prompt's literal reading had fallback exiting at "
        "`stop_vwap`, which makes fallback P&L-inert; this script "
        "implements the operational reading so the sweep yields a "
        "meaningful fallback axis.\n"
    )
    md.append(
        "\nDataset anchors: "
        f"{n_games} games, {n_trades} total entries, "
        f"{len(stops)} stops, non-stop P&L "
        f"${non_stop_pnl:+,.2f} (held constant across cells).\n"
    )

    # Part 1 — full grid
    md.append("\n## Part 1 — Full grid results\n")
    md.append(
        "Sorted by annual EV descending. Top 5 highlighted with bold.\n\n"
        "| # | NO_bid | YES equiv | Fallback | Maker | Fallback | Unfilled | Avg exit | Stop P&L | Annual EV |\n"
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    sorted_cells = sorted(
        all_cells, key=lambda c: -c.annual_ev,
    )
    for i, c in enumerate(sorted_cells, 1):
        bold = "**" if i <= 5 else ""
        md.append(
            f"| {bold}{i}{bold} | {bold}${c.no_bid:.2f}{bold} | "
            f"{bold}${c.yes_equiv:.2f}{bold} | "
            f"{bold}${c.fallback:.2f}{bold} | "
            f"{bold}{c.maker_fills}{bold} | "
            f"{bold}{c.taker_fallbacks}{bold} | "
            f"{bold}{c.taker_unfilled}{bold} | "
            f"{bold}${c.avg_stop_price:.3f}{bold} | "
            f"{bold}${c.total_stop_pnl:+,.2f}{bold} | "
            f"{bold}${c.annual_ev:+,.0f}{bold} |\n"
        )
    md.append(
        f"\n_Baseline Scenario B ($0.60 NO / $0.34 fallback) annual "
        f"EV: ${baseline.annual_ev:+,.0f}._\n"
    )

    # Part 2 — heatmap
    md.append("\n## Part 2 — Sensitivity heatmap\n")
    md.append(
        "Annual EV across the (NO_bid × fallback) surface. "
        "Blank cells skipped because fallback ≥ YES equivalent.\n\n"
        "| NO_bid \\ Fallback |"
    )
    for fb in FALLBACKS:
        md.append(f" ${fb:.2f} |")
    md.append("\n|---|")
    for _ in FALLBACKS:
        md.append("---:|")
    md.append("\n")
    cells_by_key = {(c.no_bid, c.fallback): c for c in all_cells}
    max_ev = max(c.annual_ev for c in all_cells)
    for nb in NO_BIDS:
        md.append(f"| ${nb:.2f} |")
        for fb in FALLBACKS:
            c = cells_by_key.get((nb, fb))
            if c is None:
                md.append(" — |")
            else:
                star = " ★" if c.annual_ev == max_ev else ""
                md.append(f" ${c.annual_ev:+,.0f}{star} |")
        md.append("\n")
    md.append("\n★ = peak cell.\n")

    # Part 3a — NO_bid marginal at fallback=$0.34
    md.append("\n## Part 3a — NO_bid marginal value at fallback=$0.34\n")
    md.append(
        "Walks NO_bid from "
        f"${NO_BIDS[0]:.2f}→${NO_BIDS[-1]:.2f} "
        "holding fallback fixed. Each step's Δ EV isolates the "
        "effect of moving the resting bid by one cent.\n\n"
        "| NO_bid | Maker fills | Avg exit | Annual EV | Δ EV vs prev | Marginal note |\n"
        "|---:|---:|---:|---:|---:|---|\n"
    )
    prev_ev = None
    for nb, cell, gained, delta_ev in marginal_nobid:
        note = ""
        if delta_ev is not None:
            if delta_ev < 0:
                note = "slippage exceeds marginal fill benefit"
            elif delta_ev > 0:
                note = "fills gained outweigh slippage"
            else:
                note = "break-even"
        md.append(
            f"| ${nb:.2f} | {cell.maker_fills} | "
            f"${cell.avg_stop_price:.3f} | "
            f"${cell.annual_ev:+,.0f} | "
            f"{'—' if delta_ev is None else f'${delta_ev:+,.0f}'} | "
            f"{note} |\n"
        )

    # Part 3b — fallback marginal at optimal NO_bid
    md.append("\n## Part 3b — Fallback marginal value at optimal NO_bid\n")
    if marginal_fallback:
        opt_nb = marginal_fallback[0][1].no_bid
        md.append(
            f"Walks fallback from ${FALLBACKS[0]:.2f}→"
            f"${FALLBACKS[-1]:.2f} holding NO_bid fixed at the "
            f"grid-optimal **${opt_nb:.2f}** (yes_equiv "
            f"${1 - opt_nb:.2f}).\n\n"
            "| Fallback | Taker fallbacks | Taker unfilled | Annual EV | Δ EV vs prev |\n"
            "|---:|---:|---:|---:|---:|\n"
        )
        for fb, cell, delta_ev in marginal_fallback:
            md.append(
                f"| ${fb:.2f} | {cell.taker_fallbacks} | "
                f"{cell.taker_unfilled} | "
                f"${cell.annual_ev:+,.0f} | "
                f"{'—' if delta_ev is None else f'${delta_ev:+,.0f}'} |\n"
            )

    # Part 4 — per-stop detail at optimal
    md.append("\n## Part 4 — Per-stop detail at top-EV configuration\n")
    opt = sorted_cells[0]
    md.append(
        f"Optimal cell: **NO_bid ${opt.no_bid:.2f} / fallback "
        f"${opt.fallback:.2f}** → annual EV "
        f"${opt.annual_ev:+,.0f}. All {len(opt.per_stop)} stops, "
        "sorted by P&L ascending (worst first).\n\n"
        "| # | Game | \\|Spread\\| | Entry | stop_vwap | Outcome | Exit price | P&L |\n"
        "|---:|---|---:|---:|---:|---|---:|---:|\n"
    )
    # We need game labels — pair stops with their repriced entries by index
    paired = list(zip(stops, opt.per_stop))
    paired.sort(key=lambda x: x[1].pnl)
    for i, (ev, r) in enumerate(paired, 1):
        md.append(
            f"| {i} | {ev.label} | {ev.abs_spread:.1f} | "
            f"${ev.entry_price:.3f} | ${ev.stop_vwap:.3f} | "
            f"{r.outcome} | ${r.exit_price:.3f} | ${r.pnl:+.2f} |\n"
        )

    # Part 5 — bootstrap robustness
    md.append("\n## Part 5 — Robustness check (bootstrap)\n")
    md.append(
        f"10,000 resamples (with replacement) of the {len(stops)} "
        "stops. Non-stop P&L held constant.\n\n"
        "| Cell (NO_bid / fallback) | Bootstrap mean | 95% CI | P(EV > 0) | P(beats baseline) |\n"
        "|---|---:|---|---:|---:|\n"
    )
    baseline_samples = baseline_boot.get("samples")
    for c in top3:
        key = (c.no_bid, c.fallback)
        b = boots[key]
        if baseline_samples is not None:
            diffs = b["samples"] - baseline_samples
            p_beats = float((diffs > 0).mean())
        else:
            p_beats = float("nan")
        md.append(
            f"| ${c.no_bid:.2f} / ${c.fallback:.2f} | "
            f"${b['mean']:+,.0f} | "
            f"(${b['ci_lo']:+,.0f}, ${b['ci_hi']:+,.0f}) | "
            f"{100 * b['p_gt_zero']:.1f}% | "
            f"{100 * p_beats:.1f}% |\n"
        )
    bb = baseline_boot
    md.append(
        f"\n_Baseline Scenario B reference: bootstrap mean "
        f"${bb['mean']:+,.0f}, "
        f"95% CI (${bb['ci_lo']:+,.0f}, ${bb['ci_hi']:+,.0f}), "
        f"P(EV>0) = {100 * bb['p_gt_zero']:.1f}%._\n"
    )

    # Recommendation
    opt_cell = sorted_cells[0]
    improves_over_baseline = opt_cell.annual_ev > baseline.annual_ev
    delta_vs_baseline = opt_cell.annual_ev - baseline.annual_ev
    key_top = (opt_cell.no_bid, opt_cell.fallback)
    opt_boot = boots[key_top]
    if baseline_samples is not None:
        p_robust = float((opt_boot["samples"] > baseline_samples).mean())
    else:
        p_robust = float("nan")

    md.append("\n## Recommendation\n")
    md.append(
        f"\n**Optimal cell:** NO_bid ${opt_cell.no_bid:.2f} / "
        f"fallback ${opt_cell.fallback:.2f} (YES equivalent "
        f"${opt_cell.yes_equiv:.2f}).\n"
        f"\n**Annual EV:** ${opt_cell.annual_ev:+,.0f} vs "
        f"baseline Scenario B ${baseline.annual_ev:+,.0f} "
        f"(Δ ${delta_vs_baseline:+,.0f}).\n"
        f"\n**Bootstrap robustness:** P(optimal beats baseline) = "
        f"{100 * p_robust:.1f}% across 10,000 resamples; 95% CI "
        f"(${opt_boot['ci_lo']:+,.0f}, ${opt_boot['ci_hi']:+,.0f}).\n"
    )
    if improves_over_baseline and p_robust >= 0.80:
        md.append(
            "\n**Verdict:** the optimal cell meaningfully beats the "
            "current Scenario B default and the bootstrap agrees. "
            "Recommend updating STRATEGY4_SPEC.md §4 and "
            "PHASE4A_DESIGN.md Decision 6 to the optimal values. "
            "Paper-test in Phase 4b to confirm against live fills "
            "before committing real capital to the change.\n"
        )
    elif improves_over_baseline and p_robust >= 0.60:
        md.append(
            "\n**Verdict:** the optimal cell nominally beats the "
            "current Scenario B default, but the bootstrap indicates "
            "the edge is not robust at the current sample size. "
            "Hold the $0.60 / $0.34 default; revisit after more "
            "stops accumulate via Phase 4a/4b paper trading.\n"
        )
    else:
        md.append(
            "\n**Verdict:** the sweep does not identify a "
            "meaningfully better cell than the current $0.60 / "
            "$0.34 baseline. No update to the specs is warranted. "
            "The current defaults are consistent with the data.\n"
        )

    # Note about the broader operational frame
    md.append(
        "\n**Operational framing:** the NO_bid axis trades earlier-but-"
        "shallower maker fills (higher NO_bid / lower YES equivalent) "
        "against bigger-but-later exits (lower NO_bid). The fallback "
        "axis limits downside on severe gaps by cutting losses when "
        "the VWAP crashes past the resting order. Under the "
        "operational interpretation, fallback is a risk-management "
        "knob whose benefit shows up as lifted stop P&L on the "
        "worst-outcome subset of stops.\n"
    )

    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading 404-game Kalshi paired dataset...")
    games = load_kalshi_games_all_spreads()
    n_games = len(games)

    log("Precomputing trailing max + running S4A sim...")
    lookback_bins = max(1, int(CFG.lookback_sec / BUCKET_SEC))
    precomp_max: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp_max[(g["ticker"], lookback_bins)] = (
            _precompute_trailing_max(fav, lookback_bins)
        )
    all_trades = simulate_s4a(games, CFG, precomp_max)
    labels = load_game_labels()
    stops, _summary, n_trades, n_stops = identify_stops(
        games, precomp_max, labels,
    )
    annotate_gaps(stops)
    log(f"  {n_trades} entries, {n_stops} stops")

    non_stop_pnl = sum(
        t.net_pnl for t in all_trades if t.exit_type != "stop"
    )
    log(f"  non-stop P&L (held constant): ${non_stop_pnl:+,.2f}")

    log("Evaluating parameter grid...")
    all_cells: list[CellResult] = []
    for nb in NO_BIDS:
        for fb in FALLBACKS:
            cell = evaluate_cell(
                nb, fb, stops, non_stop_pnl, n_trades, n_games,
            )
            if cell is not None:
                all_cells.append(cell)
    log(f"  {len(all_cells)} valid cells")

    baseline = next(
        (c for c in all_cells
         if c.no_bid == DEFAULT_NO_BID and c.fallback == DEFAULT_FALLBACK),
        None,
    )
    if baseline is None:
        log("FAIL: could not find baseline cell in grid.")
        return 2

    sorted_cells = sorted(all_cells, key=lambda c: -c.annual_ev)
    top3 = sorted_cells[:3]

    log("Bootstrap robustness for top-3 cells + baseline...")
    boots: dict[tuple[float, float], dict] = {}
    for c in top3:
        key = (c.no_bid, c.fallback)
        boots[key] = bootstrap_cell(
            stops, c.per_stop, non_stop_pnl, n_trades, n_games,
            BOOTSTRAP_N, BOOTSTRAP_SEED,
        )
    baseline_boot = bootstrap_cell(
        stops, baseline.per_stop, non_stop_pnl, n_trades, n_games,
        BOOTSTRAP_N, BOOTSTRAP_SEED,
    )

    log("Marginal analyses...")
    # 3a — NO_bid marginal at fallback = $0.34
    marginal_nobid: list[tuple[float, CellResult, float, float | None]] = []
    prev_ev = None
    for nb in NO_BIDS:
        cell = next(
            (c for c in all_cells
             if c.no_bid == nb and c.fallback == DEFAULT_FALLBACK),
            None,
        )
        if cell is None:
            continue
        prev_fills = marginal_nobid[-1][1].maker_fills if marginal_nobid else 0
        gained = cell.maker_fills - prev_fills
        delta_ev = None if prev_ev is None else cell.annual_ev - prev_ev
        marginal_nobid.append((nb, cell, gained, delta_ev))
        prev_ev = cell.annual_ev

    # 3b — fallback marginal at optimal NO_bid
    opt_nb = sorted_cells[0].no_bid
    marginal_fallback: list[tuple[float, CellResult, float | None]] = []
    prev_ev = None
    for fb in FALLBACKS:
        cell = next(
            (c for c in all_cells
             if c.no_bid == opt_nb and c.fallback == fb),
            None,
        )
        if cell is None:
            continue
        delta_ev = None if prev_ev is None else cell.annual_ev - prev_ev
        marginal_fallback.append((fb, cell, delta_ev))
        prev_ev = cell.annual_ev

    log("Rendering report...")
    md = render_report(
        n_games=n_games, n_trades=n_trades, stops=stops,
        non_stop_pnl=non_stop_pnl,
        all_cells=all_cells, baseline=baseline, top3=top3,
        boots=boots, baseline_boot=baseline_boot,
        marginal_nobid=marginal_nobid,
        marginal_fallback=marginal_fallback,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
