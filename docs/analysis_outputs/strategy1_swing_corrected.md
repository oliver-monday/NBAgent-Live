# Strategy 1 Corrected — Underdog Swing Trade Analysis
_Generated: 2026-04-23T05:19:32.726843+00:00_
**This analysis supersedes `strategy1_bilateral_sim.md`.** The prior script combined mutually exclusive outcomes — T5 exits at 5 minutes AND bilateral completions requiring 35+ minute holds — in the same P&L, implicitly assuming the engine can predict at minute 5 which entries will later complete. A live engine cannot do this. The $5,603/yr figure was operationally unachievable.

This analysis replaces the bilateral framing with a single coherent state machine per config. No config mixes incompatible outcomes; no config assumes future knowledge. Single entry per game. The bilateral-equivalence observation ($0.65 sell ≡ $0.20 + $0.35 bilateral buys, same gross) confirms a swing trade captures the same economics with simpler execution.

Dataset: **404 games** from the Kalshi-confirmed paired dataset (all spreads). `dog_vwap = 1 - fav_vwap` approximation carries forward — annual EV is an upper bound.

## Section 1 — Hold-to-resolution baseline
Enter at the first tick where either side's bid ≤ threshold (Policy A). Hold to game resolution. No exit management. This is the true Option A baseline.

| Entry threshold | Games entered | Mean entry | Win rate | Mean P&L | Annual EV |
|---:|---:|---:|---:|---:|---:|
| ≤ $0.15 | 404 | $0.125 | 9.2% | $-3.55 | $-1,942 |
| ≤ $0.20 | 404 | $0.159 | 11.4% | $-4.75 | $-2,600 |
| ≤ $0.25 | 404 | $0.190 | 12.9% | $-6.39 | $-3,498 |
| ≤ $0.30 | 404 | $0.218 | 14.9% | $-7.19 | $-3,937 |
| ≤ $0.35 | 404 | $0.238 | 17.6% | $-6.51 | $-3,562 |

## Section 2 — Exit strategy sweep
Entry fixed at threshold $0.35. Each config is a complete rule set with priority-ordered exits: target → stop → trail → time → resolution.

**Hold-to-resolution baseline at $0.35 threshold:** 404 entries, mean P&L $-6.51, annual EV $-3,562.

**Total sweep configs:** 62. Top 20 by annual EV:

| # | Config | Entries | Target | Stop | Trail | Time | Res | Mean P&L | Annual EV |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | D.trail -$0.08 | 404 | 0 | 0 | 359 | 0 | 45 | $-0.19 | $-103 |
| 2 | B.stop -$0.03 | 404 | 0 | 379 | 0 | 0 | 25 | $-0.39 | $-213 |
| 3 | B.stop -$0.05 | 404 | 0 | 354 | 0 | 0 | 50 | $-0.49 | $-270 |
| 4 | E.tgt+$0.30/trail-$0.08 | 404 | 30 | 0 | 330 | 0 | 44 | $-0.52 | $-286 |
| 5 | D.trail -$0.05 | 404 | 0 | 0 | 373 | 0 | 31 | $-0.71 | $-388 |
| 6 | D.trail -$0.10 | 404 | 0 | 0 | 345 | 0 | 59 | $-0.75 | $-410 |
| 7 | E.tgt+$0.30/trail-$0.05 | 404 | 10 | 0 | 363 | 0 | 31 | $-0.78 | $-427 |
| 8 | D.trail -$0.03 | 404 | 0 | 0 | 376 | 0 | 28 | $-0.85 | $-463 |
| 9 | E.tgt+$0.30/trail-$0.03 | 404 | 3 | 0 | 373 | 0 | 28 | $-0.85 | $-466 |
| 10 | E.tgt+$0.20/trail-$0.08 | 404 | 66 | 0 | 294 | 0 | 44 | $-0.94 | $-516 |
| 11 | E.tgt+$0.20/trail-$0.03 | 404 | 13 | 0 | 363 | 0 | 28 | $-0.98 | $-537 |
| 12 | E.tgt+$0.20/trail-$0.05 | 404 | 33 | 0 | 340 | 0 | 31 | $-1.01 | $-550 |
| 13 | C.tgt+$0.30/stop-$0.03 | 404 | 42 | 358 | 0 | 0 | 4 | $-1.01 | $-554 |
| 14 | E.tgt+$0.15/trail-$0.03 | 404 | 24 | 0 | 352 | 0 | 28 | $-1.13 | $-620 |
| 15 | C.tgt+$0.20/stop-$0.03 | 404 | 58 | 342 | 0 | 0 | 4 | $-1.16 | $-637 |
| 16 | C.tgt+$0.30/stop-$0.05 | 404 | 59 | 328 | 0 | 0 | 17 | $-1.26 | $-692 |
| 17 | E.tgt+$0.15/trail-$0.05 | 404 | 53 | 0 | 320 | 0 | 31 | $-1.29 | $-708 |
| 18 | E.tgt+$0.15/trail-$0.08 | 404 | 98 | 0 | 262 | 0 | 44 | $-1.32 | $-724 |
| 19 | C.tgt+$0.15/stop-$0.03 | 404 | 70 | 331 | 0 | 0 | 3 | $-1.35 | $-739 |
| 20 | E.tgt+$0.10/trail-$0.03 | 404 | 54 | 0 | 322 | 0 | 28 | $-1.37 | $-748 |

Across all 62 configs: **0 positive EV** (0.0%). Hold-to-resolution baseline $-3,562 ranks #58 in the sorted list.

## Section 3 — Price trajectory characterization
Observational analysis on the post-entry trajectory for each game that triggers Policy A at ≤ $0.35.

### 3A — Peak price reached

| Peak bucket | Count | % | Mean entry | Mean peak | Mean ticks to peak |
|---|---:|---:|---:|---:|---:|
| < $0.20 | 79 | 19.6% | $0.094 | $0.124 | 21 |
| $0.20-$0.30 | 40 | 9.9% | $0.176 | $0.250 | 49 |
| $0.30-$0.40 | 83 | 20.5% | $0.278 | $0.352 | 32 |
| $0.40-$0.50 | 50 | 12.4% | $0.275 | $0.452 | 59 |
| $0.50-$0.65 | 43 | 10.6% | $0.299 | $0.569 | 118 |
| $0.65-$0.80 | 19 | 4.7% | $0.287 | $0.720 | 217 |
| > $0.80 | 90 | 22.3% | $0.294 | $0.975 | 252 |

### 3B — Max drawdown before peak (for games reaching peak ≥ $0.50)

| Peak bucket | Count | Mean max drawdown | Median | P90 |
|---|---:|---:|---:|---:|
| $0.50-$0.65 | 43 | $0.082 | $0.068 | $0.197 |
| $0.65-$0.80 | 19 | $0.111 | $0.089 | $0.242 |
| > $0.80 | 90 | $0.099 | $0.080 | $0.233 |

### 3C — Near-miss analysis ($0.55-$0.64 peak, never reached $0.65)

**25** games peak in $0.55-$0.64 without reaching $0.65.

| Count | Mean entry | Mean peak | Mean P&L trail-$0.05 | Mean P&L trail-$0.08 |
|---:|---:|---:|---:|---:|
| 25 | $0.291 | $0.602 | $+24.03 | $+21.02 |

### 3D — Time to key levels (games that reach)

| Level | Games reaching | Median ticks | Median minutes |
|---|---:|---:|---:|
| $0.30 | 280 | 1 | 0.5 |
| $0.40 | 202 | 50 | 25.0 |
| $0.50 | 152 | 97 | 48.5 |
| $0.60 | 123 | 152 | 76.0 |
| $0.65 | 109 | 172 | 86.0 |
| $0.80 | 90 | 209 | 104.5 |

## Section 4 — Best config deep dive + spread/entry buckets

### Top 1: `D.trail -$0.08` (annual EV $-103)

**Exit type distribution:**

| Exit type | Count | % | Mean P&L |
|---|---:|---:|---:|
| trail | 359 | 88.9% | $+1.76 |
| resolution | 45 | 11.1% | $-15.75 |

**Spread-bucket breakdown:**

| |Spread| | Games | Entries | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|
| 1.0-2.0 | 36 | 36 | $+4.04 | $+2,213 |
| 2.5-3.5 | 69 | 69 | $-1.08 | $-590 |
| 4.0-5.0 | 31 | 31 | $-1.55 | $-848 |
| 5.5-6.0 | 35 | 35 | $+1.34 | $+732 |
| 6.5-8.0 | 46 | 46 | $-1.53 | $-839 |
| 8.5-10.0 | 38 | 38 | $+2.09 | $+1,146 |
| 10.5+ | 149 | 149 | $-1.04 | $-568 |

**Entry price band breakdown:**

| Entry band | Count | Mean P&L | Target hit % |
|---|---:|---:|---:|
| ≤ $0.10 | 59 | $-2.77 | 0.0% |
| $0.10-$0.15 | 53 | $+0.49 | 0.0% |
| $0.15-$0.20 | 35 | $-0.90 | 0.0% |
| $0.20-$0.25 | 39 | $+1.71 | 0.0% |
| $0.25-$0.30 | 37 | $+1.49 | 0.0% |
| $0.30-$0.35 | 181 | $-0.16 | 0.0% |

### Top 2: `B.stop -$0.03` (annual EV $-213)

**Exit type distribution:**

| Exit type | Count | % | Mean P&L |
|---|---:|---:|---:|
| stop | 379 | 93.8% | $-4.39 |
| resolution | 25 | 6.2% | $+60.26 |

**Spread-bucket breakdown:**

| |Spread| | Games | Entries | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|
| 1.0-2.0 | 36 | 36 | $+4.94 | $+2,705 |
| 2.5-3.5 | 69 | 69 | $-2.87 | $-1,570 |
| 4.0-5.0 | 31 | 31 | $-0.28 | $-155 |
| 5.5-6.0 | 35 | 35 | $+1.48 | $+810 |
| 6.5-8.0 | 46 | 46 | $-1.46 | $-798 |
| 8.5-10.0 | 38 | 38 | $-2.25 | $-1,229 |
| 10.5+ | 149 | 149 | $-0.19 | $-103 |

**Entry price band breakdown:**

| Entry band | Count | Mean P&L | Target hit % |
|---|---:|---:|---:|
| ≤ $0.10 | 59 | $-3.43 | 0.0% |
| $0.10-$0.15 | 53 | $+1.40 | 0.0% |
| $0.15-$0.20 | 35 | $+3.20 | 0.0% |
| $0.20-$0.25 | 39 | $-2.29 | 0.0% |
| $0.25-$0.30 | 37 | $-0.52 | 0.0% |
| $0.30-$0.35 | 181 | $-0.18 | 0.0% |

### Top 3: `B.stop -$0.05` (annual EV $-270)

**Exit type distribution:**

| Exit type | Count | % | Mean P&L |
|---|---:|---:|---:|
| stop | 354 | 87.6% | $-6.35 |
| resolution | 50 | 12.4% | $+40.99 |

**Spread-bucket breakdown:**

| |Spread| | Games | Entries | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|
| 1.0-2.0 | 36 | 36 | $+3.28 | $+1,792 |
| 2.5-3.5 | 69 | 69 | $-0.57 | $-312 |
| 4.0-5.0 | 31 | 31 | $+0.22 | $+119 |
| 5.5-6.0 | 35 | 35 | $+3.92 | $+2,145 |
| 6.5-8.0 | 46 | 46 | $-3.30 | $-1,807 |
| 8.5-10.0 | 38 | 38 | $-4.11 | $-2,249 |
| 10.5+ | 149 | 149 | $-0.76 | $-417 |

**Entry price band breakdown:**

| Entry band | Count | Mean P&L | Target hit % |
|---|---:|---:|---:|
| ≤ $0.10 | 59 | $-5.23 | 0.0% |
| $0.10-$0.15 | 53 | $+1.36 | 0.0% |
| $0.15-$0.20 | 35 | $+3.99 | 0.0% |
| $0.20-$0.25 | 39 | $-4.15 | 0.0% |
| $0.25-$0.30 | 37 | $-2.34 | 0.0% |
| $0.30-$0.35 | 181 | $+0.81 | 0.0% |

## Section 5 — Comparison to prior S1 estimates

| Metric | Prior bilateral sim (flawed) | Hold-to-resolution | Best swing config |
|---|---:|---:|---:|
| Framing | Bilateral arbitrage | Buy-and-hold | Underdog swing |
| Entry | Policy A, ≤$0.35 | Policy A, ≤$0.35 | Policy A, ≤$0.35 |
| Exit | T5 + bilateral (incompatible) | Resolution only | `D.trail -$0.08` |
| Annual EV | +$5,603 (invalid) | $-3,562 | $-103 |
| Logically consistent | NO | YES | YES |

### Bilateral-equivalence math

```
Bilateral:  buy at $0.20 + buy other side at $0.35 = $0.55 cost
            Resolution pays $1.00. Gross = $0.45.
Swing sell: buy at $0.20, sell at $0.65 = $0.45 gross.
            Identical economics, simpler execution.
```

The bilateral and swing framings are arithmetically equivalent when both legs clear and when the swing sells at the complementary price. The swing version is the correct engine-level abstraction: single position, single exit rule, no leg-1/leg-2 queue priority concerns, no partial-fill stranding.

