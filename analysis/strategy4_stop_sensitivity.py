"""S4A stop-level sensitivity — full re-simulation sweep.

Re-runs the complete S4A simulation at 11 stop-loss levels
($0.35-$0.45) across the full 404-game Kalshi-confirmed dataset.
Unlike `strategy4_stop_params.py` (which repriced existing stops
identified at stop=$0.40), this script re-simulates end-to-end so
entries that become NEW stops at tighter levels — or winners that
get converted to stops on their way up — are captured.

The headline question: does a tighter stop (e.g., $0.42 per the
params-sweep recommendation) convert enough target hits to stops
to offset the better exit price on existing stops?

Run:
    python -m analysis.strategy4_stop_sensitivity
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    COMP_FRACTION,
    REG_SEASON_GAMES,
    S4AConfig,
    S4ATrade,
    _precompute_trailing_max,
    load_kalshi_games_all_spreads,
    simulate_s4a,
    summarize_s4a,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy4_stop_sensitivity.md"
)

# Full 11-level sweep centered on $0.40 with $0.01 granularity.
STOP_LEVELS = [
    0.35, 0.36, 0.37, 0.38, 0.39,
    0.40, 0.41, 0.42, 0.43, 0.44, 0.45,
]
BASELINE_STOP = 0.40
COMPARISON_STOP = 0.42   # the stop level the params sweep pointed to

# S4A config held constant except stop_loss per-sweep.
def cfg_at(stop: float) -> S4AConfig:
    return S4AConfig(
        lookback_sec=180, dip_depth=0.08,
        entry_lo=0.50, entry_hi=0.75,
        exit_target=0.90, stop_loss=stop,
    )


SPREAD_BUCKETS: list[tuple[str, float, float]] = [
    ("1.0-2.0", 1.0, 2.0),
    ("2.5-3.5", 2.5, 3.5),
    ("4.0-5.0", 4.0, 5.0),
    ("5.5-6.0", 5.5, 6.0),
    ("6.5-8.0", 6.5, 8.0),
    ("8.5-10.0", 8.5, 10.0),
    ("10.5+", 10.5, float("inf")),
]


def bucket_for(abs_spread: float) -> str | None:
    for lab, lo, hi in SPREAD_BUCKETS:
        if lo <= abs_spread <= hi:
            return lab
    return None


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


# ---- Sweep core --------------------------------------------------------

@dataclass
class SweepRow:
    stop: float
    entries: int
    target_hits: int
    stops: int
    eod_held: int
    hit_pct: float
    mean_pnl: float
    total_pnl: float
    annual_ev: float
    trades: list[S4ATrade]


def run_sweep(
    games: list[dict],
    precomp_max: dict[tuple[str, int], np.ndarray],
) -> dict[float, SweepRow]:
    out: dict[float, SweepRow] = {}
    for stop in STOP_LEVELS:
        cfg = cfg_at(stop)
        trades = simulate_s4a(games, cfg, precomp_max)
        summary = summarize_s4a(trades, len(games))
        held = summary["n_res_win"] + summary["n_res_loss"] + summary["n_res_mid"]
        out[stop] = SweepRow(
            stop=stop,
            entries=summary["entries"],
            target_hits=summary["n_target"],
            stops=summary["n_stop"],
            eod_held=held,
            hit_pct=summary["hit_pct"],
            mean_pnl=summary["mean_pnl"],
            total_pnl=summary["entries"] * summary["mean_pnl"],
            annual_ev=summary["annual_ev"],
            trades=trades,
        )
    return out


# ---- Parity check ------------------------------------------------------

def parity_check(rows: dict[float, SweepRow]) -> tuple[bool, str]:
    r = rows[BASELINE_STOP]
    # Full 404-game dataset reference (from stop execution + Path B
    # pooled): 311 entries, hit ~57-58% (wider-spread buckets pull the
    # pooled hit rate above the 171-game competitive 52.4%), mean ~$3.
    # Tolerances lenient — this is a cross-version sanity check.
    entries_ok = 300 <= r.entries <= 325
    mean_ok = 2.80 <= r.mean_pnl <= 3.60
    hit_ok = 50.0 <= r.hit_pct <= 62.0
    ok = entries_ok and mean_ok and hit_ok
    note = (
        f"entries={r.entries}, hit={r.hit_pct:.1f}%, mean=${r.mean_pnl:+.2f} — "
        f"{'PASS' if ok else 'FAIL'}"
    )
    return ok, note


# ---- Entry-level cross reference ---------------------------------------

def entry_fingerprint(t: S4ATrade) -> tuple[str, int, float]:
    """Identifier that's stable for the first entry in a game across
    stop levels; for re-entries, the entry_idx differs and so does
    the fingerprint — which is correct, since re-entries ARE
    different events at different stop levels."""
    return (t.ticker, t.entry_idx, round(t.entry_price, 4))


def cross_reference(
    trades_a: list[S4ATrade], trades_b: list[S4ATrade],
) -> dict:
    """Match trades by (ticker, entry_idx, entry_price) across two
    simulations. Return counts of outcome changes."""
    a_by = {entry_fingerprint(t): t for t in trades_a}
    b_by = {entry_fingerprint(t): t for t in trades_b}
    common = set(a_by) & set(b_by)
    only_a = set(a_by) - set(b_by)
    only_b = set(b_by) - set(a_by)

    converted_target_to_stop = 0
    converted_stop_to_target = 0
    preserved_target = 0
    preserved_stop = 0
    pnl_delta_converted: list[float] = []
    for k in common:
        ta, tb = a_by[k], b_by[k]
        if ta.exit_type == "target" and tb.exit_type == "stop":
            converted_target_to_stop += 1
            pnl_delta_converted.append(tb.net_pnl - ta.net_pnl)
        elif ta.exit_type == "stop" and tb.exit_type == "target":
            converted_stop_to_target += 1
            pnl_delta_converted.append(tb.net_pnl - ta.net_pnl)
        elif ta.exit_type == "target" and tb.exit_type == "target":
            preserved_target += 1
        elif ta.exit_type == "stop" and tb.exit_type == "stop":
            preserved_stop += 1
    return {
        "n_common": len(common),
        "n_only_a": len(only_a),
        "n_only_b": len(only_b),
        "converted_target_to_stop": converted_target_to_stop,
        "converted_stop_to_target": converted_stop_to_target,
        "preserved_target": preserved_target,
        "preserved_stop": preserved_stop,
        "total_pnl_delta_from_converted": float(
            sum(pnl_delta_converted)
        ),
    }


# ---- Spread-bucket breakdown -------------------------------------------

def bucket_breakdown(
    trades: list[S4ATrade], games: list[dict],
    stop: float,
) -> dict[str, dict]:
    games_by_ticker = {g["ticker"]: g for g in games}
    bucket_games: dict[str, list[dict]] = {
        lab: [] for lab, _, _ in SPREAD_BUCKETS
    }
    for g in games:
        lab = bucket_for(g["abs_spread"])
        if lab is not None:
            bucket_games[lab].append(g)
    bucket_trades: dict[str, list[S4ATrade]] = {
        lab: [] for lab, _, _ in SPREAD_BUCKETS
    }
    for t in trades:
        g = games_by_ticker.get(t.ticker)
        if g is None:
            continue
        lab = bucket_for(g["abs_spread"])
        if lab is not None:
            bucket_trades[lab].append(t)

    out: dict[str, dict] = {}
    for lab, _, _ in SPREAD_BUCKETS:
        gs = bucket_games[lab]
        ts = bucket_trades[lab]
        if not gs:
            out[lab] = {"n_games": 0, "entries": 0, "annual_ev": 0.0}
            continue
        s = summarize_s4a(ts, len(gs))
        out[lab] = {
            "n_games": len(gs),
            "entries": s["entries"],
            "hit_pct": s["hit_pct"],
            "mean_pnl": s["mean_pnl"],
            "annual_ev": s["annual_ev"],
        }
    return out


# ---- Report rendering --------------------------------------------------

def render_report(
    n_games: int,
    rows: dict[float, SweepRow],
    parity_ok: bool, parity_note: str,
    games: list[dict],
) -> str:
    md: list[str] = []
    md.append(
        "# Strategy 4 — Stop-Level Sensitivity (Full 404-Game Sweep)\n"
    )
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Full re-simulation of S4A at {len(STOP_LEVELS)} stop-loss "
        f"levels (${STOP_LEVELS[0]:.2f}–${STOP_LEVELS[-1]:.2f}) "
        f"across the {n_games}-game Kalshi-confirmed dataset. "
        "Resolves the converted-winners question from the stop "
        "params sweep: does a tighter stop (e.g., $0.42) convert "
        "enough target hits to stops to offset the improved exit "
        "price?\n"
    )
    md.append(
        f"\nParity anchor at ${BASELINE_STOP:.2f}: {parity_note}.\n"
    )
    if not parity_ok:
        md.append(
            "\n**WARNING:** parity check FAILED. Results below may "
            "not be comparable to prior S4A analyses — investigate "
            "before trusting numbers.\n"
        )

    # Part 1 — core sweep
    md.append("\n## Part 1 — Core sweep table\n")
    md.append(
        "| Stop | Entries | Target | Stops | EOD held | Hit % | "
        "Mean P&L | Annual EV |\n"
        "|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    best_stop = max(rows, key=lambda s: rows[s].annual_ev)
    for stop in STOP_LEVELS:
        r = rows[stop]
        marker = ""
        if stop == BASELINE_STOP:
            marker = " _(baseline)_"
        if stop == best_stop:
            marker += " ★"
        md.append(
            f"| ${stop:.2f}{marker} | {r.entries} | {r.target_hits} | "
            f"{r.stops} | {r.eod_held} | {r.hit_pct:.1f}% | "
            f"${r.mean_pnl:+.2f} | ${r.annual_ev:+,.0f} |\n"
        )
    md.append(
        f"\n★ = peak cell. Best stop level: "
        f"**${best_stop:.2f}** at "
        f"${rows[best_stop].annual_ev:+,.0f}/yr "
        f"(baseline ${BASELINE_STOP:.2f}: "
        f"${rows[BASELINE_STOP].annual_ev:+,.0f}/yr, "
        f"Δ ${rows[best_stop].annual_ev - rows[BASELINE_STOP].annual_ev:+,.0f}).\n"
    )

    # Part 2 — marginal analysis via cross-reference
    md.append("\n## Part 2 — Marginal analysis (step-by-step)\n")
    md.append(
        "Each row reports the change from the previous (wider) stop "
        "to the current stop. Cross-reference identifies entries that "
        "appear in both simulations at the same "
        "`(ticker, entry_idx, entry_price)` and tracks how their "
        "outcome flipped.\n\n"
        "| Step | Entries now | Δ entries | Common | New stops (→stop) | Saved stops (→target) | Net EV Δ |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for i in range(1, len(STOP_LEVELS)):
        prev = STOP_LEVELS[i - 1]
        cur = STOP_LEVELS[i]
        a = rows[prev].trades
        b = rows[cur].trades
        xref = cross_reference(a, b)
        ev_delta = rows[cur].annual_ev - rows[prev].annual_ev
        md.append(
            f"| ${prev:.2f} → ${cur:.2f} | {rows[cur].entries} | "
            f"{rows[cur].entries - rows[prev].entries:+d} | "
            f"{xref['n_common']} | "
            f"{xref['converted_target_to_stop']} | "
            f"{xref['converted_stop_to_target']} | "
            f"${ev_delta:+,.0f} |\n"
        )
    md.append(
        "\nColumn notes: `Common` = entries that appear at both stop "
        "levels with identical `(ticker, entry_idx, entry_price)`. "
        "`New stops` = common entries that hit target at the wider "
        "stop but get stopped at the tighter stop. `Saved stops` = "
        "common entries that stopped at the wider stop but hit "
        "target at the tighter stop (rare — moving the stop tighter "
        "doesn't normally save stops).\n"
    )

    # Part 3 — the $0.42 question
    md.append("\n## Part 3 — The $0.42 question\n")
    xref = cross_reference(
        rows[BASELINE_STOP].trades, rows[COMPARISON_STOP].trades,
    )
    r40, r42 = rows[BASELINE_STOP], rows[COMPARISON_STOP]
    md.append(
        "Direct comparison of the params-sweep recommendation "
        f"(${COMPARISON_STOP:.2f}) against the current baseline "
        f"(${BASELINE_STOP:.2f}).\n\n"
        "| Metric | $0.40 baseline | $0.42 candidate |\n"
        "|---|---:|---:|\n"
        f"| Total entries | {r40.entries} | {r42.entries} |\n"
        f"| Target hits | {r40.target_hits} | {r42.target_hits} |\n"
        f"| Stops | {r40.stops} | {r42.stops} |\n"
        f"| Hit % | {r40.hit_pct:.1f}% | {r42.hit_pct:.1f}% |\n"
        f"| Mean P&L | ${r40.mean_pnl:+.2f} | ${r42.mean_pnl:+.2f} |\n"
        f"| Annual EV | ${r40.annual_ev:+,.0f} | ${r42.annual_ev:+,.0f} |\n"
    )
    md.append(
        "\n### Converted winners\n"
        f"- Common entries across both sims: {xref['n_common']}\n"
        f"- Target-hit at $0.40 but stopped-out at $0.42: "
        f"**{xref['converted_target_to_stop']} entries**\n"
        f"- Stopped at $0.40 but target-hit at $0.42: "
        f"{xref['converted_stop_to_target']} entries\n"
        f"- Preserved target across both: "
        f"{xref['preserved_target']}\n"
        f"- Preserved stop across both: "
        f"{xref['preserved_stop']}\n"
        f"- Total P&L delta from converted entries "
        "(sum of $0.42 P&L − $0.40 P&L, positive means "
        f"the tighter stop helps): "
        f"${xref['total_pnl_delta_from_converted']:+,.2f}\n"
    )
    ev_diff = r42.annual_ev - r40.annual_ev
    if xref["converted_target_to_stop"] > 0:
        md.append(
            "\n**Interpretation:** the params-sweep analysis assumed "
            f"all {r40.stops} existing stops would reprice at $0.42 "
            "with the same count. Full re-simulation reveals "
            f"**{xref['converted_target_to_stop']} target hits at "
            "$0.40 get converted to stops at $0.42**. These "
            "converted entries cost the strategy the full "
            "$0.40→$0.90 target run minus the $0.40→$0.42 stop "
            f"loss. Net annual EV change $0.40→$0.42: "
            f"${ev_diff:+,.0f}.\n"
        )
    else:
        md.append(
            "\n**Interpretation:** no target hits at $0.40 get "
            "converted to stops at $0.42 in this dataset. The "
            "params-sweep recommendation survives — tightening the "
            "stop to $0.42 improves exit price on existing stops "
            "without creating new losing entries. Net annual EV "
            f"change $0.40→$0.42: ${ev_diff:+,.0f}.\n"
        )

    # Part 4 — optimal stop level
    md.append("\n## Part 4 — Optimal stop level\n")
    best = rows[best_stop]
    md.append(
        f"On the full {n_games}-game dataset, the optimal stop is "
        f"**${best_stop:.2f}** at ${best.annual_ev:+,.0f}/yr.\n\n"
    )
    # Compare to STRATEGY4_SPEC Part 2C finding ($0.40 optimal on 165 games)
    md.append(
        f"Comparison to prior finding: STRATEGY4_SPEC.md §3 "
        "sensitivity table (Part 2C) had ${0.40} optimal on the "
        "165-game core dataset. This sweep uses the full 404-game "
        "expanded dataset and finer ($0.01) granularity.\n\n"
    )
    # Is the shift within noise? Rough heuristic: if best is within
    # $1/yr of baseline, it's noise.
    # Calculate a narrow band around the best.
    close_to_best = [
        s for s in STOP_LEVELS
        if rows[s].annual_ev >= best.annual_ev - 50
    ]
    md.append(
        "Stop levels within $50/yr of the peak:\n\n"
        "| Stop | Annual EV | Δ vs peak |\n"
        "|---:|---:|---:|\n"
    )
    for s in sorted(close_to_best):
        d = rows[s].annual_ev - best.annual_ev
        md.append(
            f"| ${s:.2f} | ${rows[s].annual_ev:+,.0f} | ${d:+,.0f} |\n"
        )
    if len(close_to_best) >= 3:
        md.append(
            "\nMultiple nearby stop levels are within $50/yr of the "
            "peak — the surface is relatively flat near the optimum. "
            "Treat the exact peak as indicative, not load-bearing.\n"
        )

    # Part 5 — spread bucket stability at top 3 stops
    md.append("\n## Part 5 — Spread-bucket stability (top 3 stops)\n")
    top3_stops = sorted(
        STOP_LEVELS, key=lambda s: -rows[s].annual_ev,
    )[:3]
    md.append(
        f"Top 3 stop levels by annual EV: "
        f"{', '.join(f'${s:.2f}' for s in top3_stops)}. "
        "Per-bucket breakdown below checks whether the optimal stop "
        "differs by spread regime.\n\n"
        "| Spread bucket | Games |"
    )
    for s in top3_stops:
        md.append(f" ${s:.2f} entries / EV |")
    md.append("\n|---|---:|")
    for _ in top3_stops:
        md.append("---:|")
    md.append("\n")
    # Precompute per-stop bucket breakdowns.
    bucket_by_stop = {
        s: bucket_breakdown(rows[s].trades, games, s) for s in top3_stops
    }
    for lab, _, _ in SPREAD_BUCKETS:
        # n_games is constant across stop levels
        n_b = bucket_by_stop[top3_stops[0]][lab]["n_games"]
        md.append(f"| {lab} | {n_b} |")
        for s in top3_stops:
            b = bucket_by_stop[s][lab]
            if b["entries"] == 0:
                md.append(" 0 / — |")
            else:
                md.append(
                    f" {b['entries']} / ${b['annual_ev']:+,.0f} |"
                )
        md.append("\n")

    # Per-bucket best stop
    md.append("\n### Per-bucket optimal stop\n")
    md.append(
        "For each bucket, which of the top 3 stops gives the highest "
        "annual EV?\n\n"
        "| Bucket | Optimal stop (of top 3) | EV at optimal |\n"
        "|---|---:|---:|\n"
    )
    per_bucket_best_different = 0
    overall_best = top3_stops[0]
    for lab, _, _ in SPREAD_BUCKETS:
        evs = {s: bucket_by_stop[s][lab]["annual_ev"] for s in top3_stops}
        best_s = max(evs, key=evs.get)
        md.append(
            f"| {lab} | ${best_s:.2f} | "
            f"${evs[best_s]:+,.0f} |\n"
        )
        if best_s != overall_best:
            per_bucket_best_different += 1
    if per_bucket_best_different > 0:
        md.append(
            f"\n_{per_bucket_best_different} of "
            f"{len(SPREAD_BUCKETS)} buckets prefer a stop level "
            "other than the overall optimum. Spread-conditional stop "
            "tuning is a possible future refinement._\n"
        )
    else:
        md.append(
            f"\n_All {len(SPREAD_BUCKETS)} buckets agree on "
            f"${overall_best:.2f} as the best stop. No spread-"
            "conditional stop tuning needed at current sample size._\n"
        )

    # Verdict
    md.append("\n## Verdict\n")
    baseline_ev = rows[BASELINE_STOP].annual_ev
    best_ev = rows[best_stop].annual_ev
    delta = best_ev - baseline_ev
    forty_two_ev = rows[COMPARISON_STOP].annual_ev
    forty_two_delta = forty_two_ev - baseline_ev
    converted_42 = cross_reference(
        rows[BASELINE_STOP].trades, rows[COMPARISON_STOP].trades,
    )["converted_target_to_stop"]

    md.append(
        f"\n**Optimal stop on full dataset:** **${best_stop:.2f}** "
        f"at ${best_ev:+,.0f}/yr, Δ ${delta:+,.0f} vs baseline "
        f"${BASELINE_STOP:.2f}.\n"
    )
    md.append(
        f"\n**$0.42 params-sweep recommendation:** "
        f"${forty_two_ev:+,.0f}/yr, Δ ${forty_two_delta:+,.0f} vs "
        f"baseline. "
        f"Converted winners (target→stop from tightening to $0.42): "
        f"**{converted_42}**.\n"
    )

    # Verdict narrative based on findings
    if best_stop == BASELINE_STOP:
        md.append(
            "\n**Recommendation:** keep stop at "
            f"${BASELINE_STOP:.2f}. Full re-simulation agrees with "
            "the current spec. The params-sweep signal from "
            f"strategy4_stop_params.md ($0.42 NO / $0.58 NO bid) was "
            "an artifact of the repricing model — when entries are "
            "re-simulated end-to-end, target hits at $0.40 get "
            f"converted to stops at $0.42 and the improvement "
            "disappears.\n"
        )
        md.append(
            "\n**No update to STRATEGY4_SPEC.md §4 warranted.** "
            "The current $0.40 stop (= $0.60 NO bid in "
            "PHASE4A_DESIGN.md Decision 6) remains the recommended "
            "operational level.\n"
        )
    elif best_stop == COMPARISON_STOP:
        md.append(
            "\n**Recommendation:** update stop from "
            f"${BASELINE_STOP:.2f} to ${best_stop:.2f}. The "
            f"{converted_42} converted winners are outweighed by "
            f"the ${delta:+,.0f}/yr net gain on the remainder. The "
            "params-sweep recommendation survives full simulation.\n"
        )
        md.append(
            f"\n**STRATEGY4_SPEC.md §4:** update stop to "
            f"${best_stop:.2f}. **PHASE4A_DESIGN.md Decision 6:** "
            f"update NO bid to ${1 - best_stop:.2f}.\n"
        )
    else:
        md.append(
            f"\n**Recommendation:** the optimal is ${best_stop:.2f}, "
            f"not ${BASELINE_STOP:.2f} (baseline) nor "
            f"${COMPARISON_STOP:.2f} (params-sweep candidate). "
            f"Update stop from ${BASELINE_STOP:.2f} to "
            f"${best_stop:.2f}.\n"
        )
        md.append(
            f"\n**STRATEGY4_SPEC.md §4:** update stop to "
            f"${best_stop:.2f}. **PHASE4A_DESIGN.md Decision 6:** "
            f"update NO bid to ${1 - best_stop:.2f}.\n"
        )

    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading 404-game Kalshi paired dataset...")
    games = load_kalshi_games_all_spreads()
    n_games = len(games)

    log("Precomputing trailing max (180s lookback)...")
    lookback_bins = max(1, int(180 / BUCKET_SEC))
    precomp_max: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp_max[(g["ticker"], lookback_bins)] = (
            _precompute_trailing_max(fav, lookback_bins)
        )

    log(f"Running full sweep across {len(STOP_LEVELS)} stop levels...")
    rows = run_sweep(games, precomp_max)

    parity_ok, parity_note = parity_check(rows)
    log(f"Parity check: {parity_note}")

    log("Rendering report...")
    md = render_report(
        n_games=n_games, rows=rows,
        parity_ok=parity_ok, parity_note=parity_note,
        games=games,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
