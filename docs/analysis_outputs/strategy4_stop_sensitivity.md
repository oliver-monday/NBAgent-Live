# Strategy 4 — Stop-Level Sensitivity (Full 404-Game Sweep)
_Generated: 2026-04-22T23:27:40.155263+00:00_
Full re-simulation of S4A at 11 stop-loss levels ($0.35–$0.45) across the 404-game Kalshi-confirmed dataset. Resolves the converted-winners question from the stop params sweep: does a tighter stop (e.g., $0.42) convert enough target hits to stops to offset the improved exit price?

Parity anchor at $0.40: entries=311, hit=57.6%, mean=$+3.35 — PASS.

## Part 1 — Core sweep table
| Stop | Entries | Target | Stops | EOD held | Hit % | Mean P&L | Annual EV |
|---:|---:|---:|---:|---:|---:|---:|---:|
| $0.35 ★ | 298 | 187 | 111 | 0 | 62.8% | $+4.06 | $+1,637 |
| $0.36 | 300 | 185 | 115 | 0 | 61.7% | $+3.69 | $+1,498 |
| $0.37 | 304 | 184 | 120 | 0 | 60.5% | $+3.62 | $+1,490 |
| $0.38 | 306 | 181 | 125 | 0 | 59.2% | $+3.32 | $+1,375 |
| $0.39 | 309 | 180 | 129 | 0 | 58.3% | $+3.25 | $+1,361 |
| $0.40 _(baseline)_ | 311 | 179 | 132 | 0 | 57.6% | $+3.35 | $+1,410 |
| $0.41 | 311 | 178 | 133 | 0 | 57.2% | $+3.65 | $+1,537 |
| $0.42 | 315 | 175 | 140 | 0 | 55.6% | $+3.27 | $+1,395 |
| $0.43 | 317 | 172 | 145 | 0 | 54.3% | $+2.99 | $+1,283 |
| $0.44 | 319 | 170 | 149 | 0 | 53.3% | $+3.11 | $+1,344 |
| $0.45 | 321 | 165 | 156 | 0 | 51.4% | $+2.84 | $+1,235 |

★ = peak cell. Best stop level: **$0.35** at $+1,637/yr (baseline $0.40: $+1,410/yr, Δ $+227).

## Part 2 — Marginal analysis (step-by-step)
Each row reports the change from the previous (wider) stop to the current stop. Cross-reference identifies entries that appear in both simulations at the same `(ticker, entry_idx, entry_price)` and tracks how their outcome flipped.

| Step | Entries now | Δ entries | Common | New stops (→stop) | Saved stops (→target) | Net EV Δ |
|---|---:|---:|---:|---:|---:|---:|
| $0.35 → $0.36 | 300 | +2 | 297 | 3 | 0 | $-139 |
| $0.36 → $0.37 | 304 | +4 | 300 | 3 | 0 | $-9 |
| $0.37 → $0.38 | 306 | +2 | 303 | 3 | 0 | $-114 |
| $0.38 → $0.39 | 309 | +3 | 305 | 4 | 0 | $-15 |
| $0.39 → $0.40 | 311 | +2 | 309 | 3 | 0 | $+50 |
| $0.40 → $0.41 | 311 | +0 | 309 | 2 | 0 | $+127 |
| $0.41 → $0.42 | 315 | +4 | 310 | 4 | 0 | $-142 |
| $0.42 → $0.43 | 317 | +2 | 314 | 5 | 0 | $-112 |
| $0.43 → $0.44 | 319 | +2 | 314 | 3 | 0 | $+61 |
| $0.44 → $0.45 | 321 | +2 | 317 | 6 | 0 | $-110 |

Column notes: `Common` = entries that appear at both stop levels with identical `(ticker, entry_idx, entry_price)`. `New stops` = common entries that hit target at the wider stop but get stopped at the tighter stop. `Saved stops` = common entries that stopped at the wider stop but hit target at the tighter stop (rare — moving the stop tighter doesn't normally save stops).

## Part 3 — The $0.42 question
Direct comparison of the params-sweep recommendation ($0.42) against the current baseline ($0.40).

| Metric | $0.40 baseline | $0.42 candidate |
|---|---:|---:|
| Total entries | 311 | 315 |
| Target hits | 179 | 175 |
| Stops | 132 | 140 |
| Hit % | 57.6% | 55.6% |
| Mean P&L | $+3.35 | $+3.27 |
| Annual EV | $+1,410 | $+1,395 |

### Converted winners
- Common entries across both sims: 308
- Target-hit at $0.40 but stopped-out at $0.42: **6 entries**
- Stopped at $0.40 but target-hit at $0.42: 0 entries
- Preserved target across both: 172
- Preserved stop across both: 130
- Total P&L delta from converted entries (sum of $0.42 P&L − $0.40 P&L, positive means the tighter stop helps): $-299.85

**Interpretation:** the params-sweep analysis assumed all 132 existing stops would reprice at $0.42 with the same count. Full re-simulation reveals **6 target hits at $0.40 get converted to stops at $0.42**. These converted entries cost the strategy the full $0.40→$0.90 target run minus the $0.40→$0.42 stop loss. Net annual EV change $0.40→$0.42: $-15.

## Part 4 — Optimal stop level
On the full 404-game dataset, the optimal stop is **$0.35** at $+1,637/yr.

Comparison to prior finding: STRATEGY4_SPEC.md §3 sensitivity table (Part 2C) had ${0.40} optimal on the 165-game core dataset. This sweep uses the full 404-game expanded dataset and finer ($0.01) granularity.

Stop levels within $50/yr of the peak:

| Stop | Annual EV | Δ vs peak |
|---:|---:|---:|
| $0.35 | $+1,637 | $+0 |

## Part 5 — Spread-bucket stability (top 3 stops)
Top 3 stop levels by annual EV: $0.35, $0.41, $0.36. Per-bucket breakdown below checks whether the optimal stop differs by spread regime.

| Spread bucket | Games | $0.35 entries / EV | $0.41 entries / EV | $0.36 entries / EV |
|---|---:|---:|---:|---:|
| 1.0-2.0 | 36 | 27 / $+1,394 | 29 / $+749 | 27 / $+1,543 |
| 2.5-3.5 | 69 | 67 / $+781 | 71 / $+1,325 | 67 / $+825 |
| 4.0-5.0 | 31 | 27 / $+2,389 | 29 / $+1,775 | 27 / $+2,471 |
| 5.5-6.0 | 35 | 36 / $+3,890 | 37 / $+3,665 | 37 / $+3,621 |
| 6.5-8.0 | 46 | 42 / $+3,782 | 43 / $+2,572 | 42 / $+2,682 |
| 8.5-10.0 | 38 | 36 / $+318 | 36 / $+658 | 36 / $+431 |
| 10.5+ | 149 | 63 / $+1,080 | 66 / $+1,182 | 64 / $+1,005 |

### Per-bucket optimal stop
For each bucket, which of the top 3 stops gives the highest annual EV?

| Bucket | Optimal stop (of top 3) | EV at optimal |
|---|---:|---:|
| 1.0-2.0 | $0.36 | $+1,543 |
| 2.5-3.5 | $0.41 | $+1,325 |
| 4.0-5.0 | $0.36 | $+2,471 |
| 5.5-6.0 | $0.35 | $+3,890 |
| 6.5-8.0 | $0.35 | $+3,782 |
| 8.5-10.0 | $0.41 | $+658 |
| 10.5+ | $0.41 | $+1,182 |

_5 of 7 buckets prefer a stop level other than the overall optimum. Spread-conditional stop tuning is a possible future refinement._

## Verdict

**Optimal stop on full dataset:** **$0.35** at $+1,637/yr, Δ $+227 vs baseline $0.40.

**$0.42 params-sweep recommendation:** $+1,395/yr, Δ $-15 vs baseline. Converted winners (target→stop from tightening to $0.42): **6**.

**Recommendation:** the optimal is $0.35, not $0.40 (baseline) nor $0.42 (params-sweep candidate). Update stop from $0.40 to $0.35.

**STRATEGY4_SPEC.md §4:** update stop to $0.35. **PHASE4A_DESIGN.md Decision 6:** update NO bid to $0.65.

