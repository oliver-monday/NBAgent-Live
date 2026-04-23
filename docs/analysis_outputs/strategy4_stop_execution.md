# Strategy 4 — Stop-Loss Execution Reality
_Generated: 2026-04-22T00:18:05.985229+00:00_
Investigates the real-world execution dynamics of S4A's $0.40 stop-loss on Kalshi's binary orderbook. The $0.40 stop is the strategy's most sensitive parameter, and Kalshi has no native stop-loss order type. Analyzes gap-through risk, dwell time, descent velocity, and EV impact under four execution scenarios including the NO-side resting order strategy.

Dataset: 404 games from the Kalshi-confirmed paired timeseries. Raw trade tape consumed from the paired pipeline's existing on-disk cache where present; new API fetches cached under `data/stop_execution_cache/`.

## Part 1 — Stop event identification
- Total S4A entries: **311**
- Stop-loss events: **132** (42.4% of entries — compare STRATEGY4_SPEC.md's ~47% anchor)
- Non-stop exits (target / EOD): 179

## Part 2 — Gap-through analysis (30s VWAP)
| Category | Definition | Count | % |
|---|---|---:|---:|
| Clean cross | stop_vwap ∈ [$0.38, $0.42] | 66 | 50.0% |
| Moderate gap | stop_vwap ∈ [$0.34, $0.38) | 43 | 32.6% |
| Severe gap | stop_vwap < $0.34 | 23 | 17.4% |

Gap-size stats (pre_stop_vwap − stop_vwap): p25 $0.038, median $0.070, p75 $0.110, max $0.372.

### Gap-size histogram
| Bucket | Count | % |
|---|---:|---:|
| $0.00–0.02 | 11 | 8.3% |
| $0.02–0.04 | 24 | 18.2% |
| $0.04–0.06 | 23 | 17.4% |
| $0.06–0.08 | 22 | 16.7% |
| $0.08–0.10 | 12 | 9.1% |
| $0.10+ | 40 | 30.3% |

### 5 worst gap-throughs
| Game | \|Spread\| | Entry | Pre-stop | Stop VWAP | Gap | Entry gse |
|---|---:|---:|---:|---:|---:|---:|
| CHA @ POR | 2.5 | $0.656 | $0.742 | $0.370 | $0.372 | 2619 |
| GSW @ HOU | 8.5 | $0.532 | $0.638 | $0.321 | $0.316 | 2873 |
| HOU @ CHI | 8.5 | $0.530 | $0.583 | $0.272 | $0.311 | 2333 |
| PHI @ MIA | 2.5 | $0.518 | $0.458 | $0.195 | $0.263 | 2516 |
| DEN @ LAC | 4.5 | $0.613 | $0.552 | $0.329 | $0.223 | 627 |

## Part 3 — Dwell time near the stop level
- Median bins in $0.38–$0.42 at/after the stop: **0 bins (0s)**
- Median bins in $0.36–$0.44 approach+through window: **1 bins (30s)**

| Dwell at $0.38–$0.42 | Count | % |
|---|---:|---:|
| 0 (instant gap) | 66 | 50.0% |
| 1 bin (30s) | 32 | 24.2% |
| 2 bins (60s) | 13 | 9.8% |
| 3+ bins (90s+) | 21 | 15.9% |

## Part 4 — Descent velocity
| Category | Definition | Count | % |
|---|---|---:|---:|
| Gradual | price 120s before ≤ $0.48 | 21 | 15.9% |
| Rapid | price 120s before > $0.48, 60s before ≤ $0.45 | 14 | 10.6% |
| Flash crash | price 60s before > $0.45 | 97 | 73.5% |

Descent rate ($/sec, 300s window): p25 0.00040, median 0.00061, p75 0.00094.

## Part 5 — Raw trade tape analysis
Raw trades available for **112** of 132 stop events (84.8%).

### 5a — Volume at $0.38–$0.42 within ±5 min of stop
- Median trades at stop-level band: 0 (p25 0, p75 0)
- Median contracts at stop-level band: 0 (p25 0, p75 0)

### 5b — Trade-level gap at $0.40 threshold
- Stops with an observable threshold-crossing pair of trades: **1** / 50
- Gap seconds between last>$0.40 and first≤$0.40: p25 1.2s, median 1.2s, p75 1.2s, max 1.2s
- Crossings < 2s (genuine gap): 1 (100.0%)
- Crossings ≥ 5s (resting-order-friendly): 0 (0.0%)

### 5c — Taker-side flow within ±60s of threshold crossing
Aggregated across all stop events with raw data. `taker_side` = side that aggressed (hit a resting order). A YES price falling through $0.40 typically coincides with YES sellers lifting NO asks — in Kalshi's encoding that shows as **NO-side takers** (NO buyers crossing the book).

| taker_side | Trades | Contracts | Share (contracts) |
|---|---:|---:|---:|
| yes | 46 | 1,275 | 68.4% |
| no | 14 | 588 | 31.6% |
| unknown | 0 | 0 | 0.0% |

**Interpretation for the NO-side resting order strategy:** a resting NO buy at $0.60 fills when someone sells NO (= buys YES). That's trade flow where `taker_side == "yes"` (YES-buyer aggressor) OR passive NO asks being hit. The dominant taker side during a stop break tells us which direction the crossing is accumulating volume — if mostly NO-takers (NO buyers paying up to lift NO asks = YES sellers), our resting NO bid sits out of the way of the flow and needs the flow to reverse. If mostly YES-takers (YES buyers paying up), our resting NO bid is in the direct path of the opposite-side fills.

### 5d — Achievable stop price for a 100-contract taker
Walk the trade tape from the threshold crossing forward; sum the first 100 contracts at yes_price ≤ $0.40.

- Stops where ≥ 100 contracts were available within the ±5 min window: **2** / 50 (4.0%)
- Achievable VWAP across fills: p25 $0.245, median $0.300, p75 $0.370
- Average slippage vs $0.40: $0.107

## Part 6 — EV impact under execution scenarios
Non-stop trades (targets + EOD) keep their baseline P&L; only stop P&L is recomputed per scenario. Annualization is pool-level across all 404 games (mean pool P&L × pool entries-per-game × 1230 × 0.445), which differs from Part 8 Path B's per-bucket-summed rollup of +$10,718 — the **relative** deltas vs Scenario A are the load-bearing numbers here, not the absolute baseline.

| Scenario | Fill rate | Avg stop price | Avg slippage | Annual EV | Δ vs A |
|---|---:|---:|---:|---:|---:|
| **A** — Baseline (stops fill at $0.40 maker) | 100% | $0.400 | $+0.000 | $+1,410 | $+0 |
| **B** — Maker NO-side resting (+ taker fallback on fail) | 66% | $0.379 | $+0.021 | $+1,460 | $+49 |
| **C** — Taker stop at observed stop_vwap | 0% | $0.368 | $+0.032 | $+977 | $-433 |
| **D** — Hybrid: resting + 60s cancel fallback | 26% | $0.370 | $+0.030 | $+1,131 | $-279 |

**Break-even stop price (uniform taker exit, full S4A EV = 0):** $0.312. If realized average stop price is worse than this, S4A is unprofitable.

## Part 7 — Target exit reality check
- Target exits: **179**
- Exit price distribution: p25 $0.905, median $0.913, p75 $0.923, max $0.978
- Targets with exit_price > $0.92 (gap-through past the level): 57 (31.8%)
- Median bin-to-bin rise into the target (exit_price − prior_bin): $0.031

Selling into strength at $0.90 is natural maker behavior on a binary market; if a few target exits show prices meaningfully above $0.90, P&L math uses $0.90 (not the observed VWAP) since that's where the resting limit would have filled.


## Operational Recommendation

**Recommended execution model for the live engine: Scenario B (Maker NO-side resting (+ taker fallback on fail)).**

- **Expected annual EV:** $+1,460 (baseline $+1,410, taker-worst-case $+977).
- **Fill rate assumption:** 66% of stops fill at the maker price; the remainder fall back to taker at the observed stop VWAP.

**When to place the resting NO buy:** at entry time, place a 100-contract resting NO bid at $0.60 (= $0.40 YES stop). Keep it active as long as the position is open. The resting order costs nothing to keep on the book, and placing it pre-emptively — rather than waiting for price to approach — means the order has maximum queue priority if the market slides rather than gapping.

**Break-even stop price:** $0.312. If live execution produces realized stop prices meaningfully worse than this, S4A is unprofitable — monitor Phase 4a paper-trade fills against this threshold.

**Stop-level adjustment warranted:** 17.4% of stops gap past $0.34 (severe category). Consider placing the resting bid slightly above $0.60 NO (i.e., $0.61–$0.62 NO / $0.38–$0.39 YES) to increase fill probability at the cost of a small deterministic slippage. Simulate both in Phase 4b.

**Cancel-and-market fallback timing:** if the engine detects fav VWAP ≤ $0.34 (severe gap zone) AND the resting NO bid has not filled, cancel immediately and submit a 100-contract YES market sell. Don't wait 60 seconds — the severe-gap signal means price is collapsing and the slippage clock is running.
