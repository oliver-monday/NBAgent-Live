# Strategy 1 — KILLED (2026-04-23)

## Kill summary

Strategy 1 (bilateral convergence / underdog swing trade) was
killed after the corrected operational analysis showed **zero
positive-EV configurations** across 62 tested exit strategies
on the 404-game Kalshi paired dataset.

## What happened

### Phase 1: ESPN-calibrated estimate (+$1,608/yr)

`strategy1_recalibrated_bilateral.md` (2026-04-19) mapped ESPN
WP to sportsbook prices and estimated bilateral opportunity
rates. Best operating point (0.25, 0.35) at 17.7% opportunity
rate produced $6.55/game → +$1,608/yr. This estimate assumed
perfect bilateral capture and did not model stranded-leg risk.

### Phase 2: Operational simulation (+$5,603/yr — INVALID)

`strategy1_bilateral_sim.md` (2026-04-23) simulated tick-by-tick
bilateral construction with three entry policies. Found +$5,603/yr
at Policy A (0.20, 0.35) with T5 stranded exit.

**This result contained a fundamental design error.** It combined
T5 exits (sell after 5 minutes) with bilateral completions
(require 35+ minute holds) in the same P&L calculation. The sim
implicitly assumed the engine could know at minute 5 which entries
would later complete bilaterally — information a live engine
cannot have. The $5,603/yr figure was not operationally
achievable.

### Phase 3: Corrected analysis (-$103/yr — KILLED)

`strategy1_swing_corrected.md` (2026-04-23) replaced the
bilateral framing with a single coherent state machine per
config. Key insight: selling the underdog at $0.65 produces
identical economics to a bilateral ($0.20 + $0.35 = $0.55
cost, $1.00 resolution = $0.45 gross ≡ $0.20 entry, $0.65
sell = $0.45 gross). The bilateral was never the right
operational model.

Results: **0 of 62 configs produced positive EV.** Best was
trailing stop at $0.08 from peak at -$103/yr. Hold-to-
resolution baseline: -$3,562/yr. The base rate is fatal:
underdogs at $0.20 win ~12% of the time, and no exit strategy
overcomes that.

## Related: S4B underdog hybrid also killed

S4B (underdog swing trading, the closely related strategy)
was revalidated on the same 404-game dataset. Prior result
+$1,105/yr (168 games) collapsed to +$148/yr. Only 14 of
1,323 configs were positive (1.1%). Best config earned $0.19
per entry — effectively zero after execution costs.

## What this means

The underdog side of Kalshi NBA markets does not contain
tradeable edge at the price levels and exit strategies tested.
Underdogs are cheap because they usually lose, and no risk
management or swing-trade mechanic overcomes the base rate.

The alpha stack reduces to S4A (favorite dip-recovery) and
S3 (filtered favorite-side entry). Both operate on the
favorite side, where the natural recovery tendency provides
genuine edge.

## Analysis chain (chronological)

1. `docs/analysis_outputs/strategy1_recalibrated_bilateral.md` — ESPN-calibrated rates
2. `docs/analysis_outputs/strategy1_bilateral_sim.md` — operational sim (FLAWED)
3. `docs/analysis_outputs/strategy1_bilateral_followup.md` — re-entry/T5/filter investigations
4. `docs/analysis_outputs/strategy4b_revalidation.md` — S4B revalidation on 404 games
5. `docs/analysis_outputs/strategy1_swing_corrected.md` — corrected analysis (KILL)
