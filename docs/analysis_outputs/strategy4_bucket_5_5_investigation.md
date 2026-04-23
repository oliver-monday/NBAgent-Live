# Strategy 4 — Bucket 5.5–6.0 Investigation
_Generated: 2026-04-21T23:14:15.399251+00:00_
Investigates whether the |spread| 5.5–6.0 bucket's outperformance (+$6.17 mean P&L, 64.9% hit, n=37) reflects a structural edge or small-sample noise. Uses the 404-game Kalshi-confirmed dataset from Part 8 Path B.

## Part 1 — Parity check
`PARITY CHECK: PASS`

Sub-checks:
- 5.5-6.0: entries=37 (expected 37) OK
- 5.5-6.0: hit=64.9% (expected 64.9%) OK
- 5.5-6.0: mean=$+6.17 (expected $+6.17) OK

Full 7-bucket rollup (parity against Path B Table 2):

| |spread| bucket | Games | Entries | Hit % | Stop % | Mean P&L |
|---|---:|---:|---:|---:|---:|
| 1.0-2.0 | 36 | 29 | 51.7% | 48.3% | $+1.59 |
| 2.5-3.5 | 69 | 71 | 47.9% | 52.1% | $+2.57 |
| 4.0-5.0 | 31 | 29 | 48.3% | 51.7% | $+2.65 |
| 5.5-6.0 | 35 | 37 | 64.9% | 35.1% | $+6.17 |
| 6.5-8.0 | 46 | 43 | 58.1% | 41.9% | $+4.14 |
| 8.5-10.0 | 38 | 36 | 58.3% | 41.7% | $+0.82 |
| 10.5+ | 149 | 66 | 69.7% | 30.3% | $+4.55 |

## Part 2 — Entry-level detail for 5.5–6.0 bucket
All 37 entries, sorted by P&L descending:

| # | Game | \|Spread\| | Entry | Exit | Outcome | P&L | Entry period | Entry gse (s) | Hold (s) | Trail max | Dip depth | Re-entry |
|---:|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---|
| 1 | TOR @ MIN | 5.5 | $0.533 | $0.907 | target | $+36.85 | Q1 | 184 | 5400 | $0.630 | $0.097 | no |
| 2 | PHX @ CHA | 5.5 | $0.563 | $0.901 | target | $+33.18 | Q1 | 148 | 4260 | $0.651 | $0.088 | no |
| 3 | DEN @ PHX | 5.5 | $0.655 | $0.977 | target | $+31.72 | Q4 | 2818 | 300 | $0.877 | $0.222 | yes |
| 4 | MEM @ MIL | 5.5 | $0.613 | $0.920 | target | $+30.15 | Q1 | 131 | 1920 | $0.712 | $0.099 | no |
| 5 | NOP @ MIN | 5.5 | $0.617 | $0.923 | target | $+30.01 | Q1 | 452 | 5310 | $0.709 | $0.092 | no |
| 6 | GSW @ DET | 5.5 | $0.614 | $0.919 | target | $+29.95 | Q1 | 642 | 3510 | $0.703 | $0.088 | no |
| 7 | NOP @ SAC | 5.5 | $0.622 | $0.918 | target | $+28.98 | Q2 | 1106 | 2910 | $0.730 | $0.108 | no |
| 8 | POR @ ATL | 6.0 | $0.618 | $0.904 | target | $+27.99 | Q1 | 177 | 1110 | $0.706 | $0.088 | no |
| 9 | ORL @ CHA | 5.5 | $0.619 | $0.902 | target | $+27.71 | Q1 | 141 | 2730 | $0.701 | $0.082 | no |
| 10 | ATL @ BOS | 5.5 | $0.624 | $0.900 | target | $+27.03 | Q2 | 1159 | 3600 | $0.713 | $0.089 | no |
| 11 | PHI @ UTA | 5.5 | $0.646 | $0.919 | target | $+26.74 | Q1 | 285 | 6810 | $0.739 | $0.093 | no |
| 12 | LAL @ PHX | 6.0 | $0.638 | $0.904 | target | $+26.11 | Q2 | 882 | 3630 | $0.735 | $0.097 | no |
| 13 | CLE @ CHA | 5.5 | $0.662 | $0.924 | target | $+25.69 | Q3 | 1526 | 2700 | $0.768 | $0.106 | no |
| 14 | HOU @ NOP | 5.5 | $0.651 | $0.913 | target | $+25.67 | Q1 | 370 | 1770 | $0.752 | $0.101 | no |
| 15 | GSW @ LAC | 5.5 | $0.667 | $0.907 | target | $+23.48 | Q1 | 312 | 6270 | $0.775 | $0.108 | no |
| 16 | MIA @ CHA | 5.5 | $0.665 | $0.904 | target | $+23.31 | Q2 | 1395 | 2850 | $0.758 | $0.093 | no |
| 17 | LAL @ DEN | 5.5 | $0.668 | $0.905 | target | $+23.24 | Q2 | 1019 | 3630 | $0.755 | $0.087 | no |
| 18 | LAL @ DEN | 5.5 | $0.667 | $0.904 | target | $+23.09 | Q4 | 2458 | 330 | $0.779 | $0.112 | yes |
| 19 | MEM @ MIL | 5.5 | $0.698 | $0.910 | target | $+20.75 | Q3 | 1552 | 2370 | $0.801 | $0.103 | yes |
| 20 | TOR @ HOU | 5.5 | $0.726 | $0.933 | target | $+20.23 | Q3 | 1881 | 1410 | $0.828 | $0.102 | no |
| 21 | DEN @ SAS | 5.5 | $0.720 | $0.909 | target | $+18.46 | Q3 | 1701 | 1020 | $0.805 | $0.085 | no |
| 22 | BOS @ GSW | 6.0 | $0.721 | $0.904 | target | $+17.78 | Q1 | 720 | 660 | $0.810 | $0.089 | no |
| 23 | DEN @ PHX | 5.5 | $0.749 | $0.930 | target | $+17.58 | Q3 | 1868 | 2580 | $0.834 | $0.085 | no |
| 24 | NOP @ SAC | 5.5 | $0.747 | $0.902 | target | $+14.97 | Q3 | 1910 | 1350 | $0.833 | $0.085 | no |
| 25 | MIL @ UTA | 5.5 | $0.508 | $0.370 | stop | $-14.63 | Q1 | 506 | 1890 | $0.616 | $0.108 | no |
| 26 | DET @ CHA | 5.5 | $0.507 | $0.361 | stop | $-15.38 | Q1 | 659 | 5220 | $0.588 | $0.082 | no |
| 27 | MIA @ MIL | 6.0 | $0.583 | $0.396 | stop | $-19.51 | Q2 | 1403 | 4440 | $0.685 | $0.102 | no |
| 28 | GSW @ UTA | 5.5 | $0.647 | $0.384 | stop | $-27.15 | Q1 | 152 | 5550 | $0.728 | $0.081 | no |
| 29 | SAS @ TOR | 6.0 | $0.651 | $0.387 | stop | $-27.20 | Q2 | 884 | 3270 | $0.732 | $0.082 | no |
| 30 | PHX @ OKC | 5.5 | $0.621 | $0.350 | stop | $-27.91 | Q1 | 193 | 450 | $0.704 | $0.083 | no |
| 31 | LAC @ MEM | 5.5 | $0.670 | $0.377 | stop | $-30.09 | Q1 | 283 | 1020 | $0.750 | $0.080 | no |
| 32 | MIA @ CHA | 5.5 | $0.653 | $0.355 | stop | $-30.68 | Q4 | 2386 | 360 | $0.861 | $0.207 | yes |
| 33 | LAC @ MEM | 5.5 | $0.718 | $0.390 | stop | $-33.54 | Q3 | 2087 | 1830 | $0.806 | $0.088 | yes |
| 34 | DEN @ SAS | 5.5 | $0.724 | $0.360 | stop | $-37.18 | Q4 | 2303 | 780 | $0.904 | $0.179 | yes |
| 35 | LAL @ PHX | 6.0 | $0.749 | $0.381 | stop | $-37.51 | Q3 | 1957 | 1290 | $0.901 | $0.152 | yes |
| 36 | GSW @ LAC | 5.5 | $0.725 | $0.354 | stop | $-37.92 | Q4 | 2384 | 1260 | $0.851 | $0.125 | yes |
| 37 | NOP @ SAC | 5.5 | $0.734 | $0.305 | stop | $-43.60 | Q4 | 2622 | 420 | $0.883 | $0.150 | yes |

## Part 3 — Outlier sensitivity (leave-one-out)
- Leave-one-out mean range: **$+5.32 — $+7.55**
- Full-bucket mean: $+6.17
- Max single-entry swing: ±$1.38 (removing entry at index 2 in the P&L-sorted list)
- Entries to remove (starting from highest P&L) before bucket mean goes negative: **8 of 37**.

## Part 4 — Bootstrap 95% CI (10,000 resamples)
- Bootstrap mean: $+6.17
- 95% CI: ($-2.90, $+14.73)
- P(true mean > $0): 91.1%
- P(true mean > $2.57, adjacent 2.5–3.5 bucket null): 78.7%

## Part 5 — Comparison to adjacent buckets
| Metric | 4.0–5.0 | **5.5–6.0** | 6.5–8.0 |
|---|---|---|---|
| n | 29 | **37** | 43 |
| Entry price (p25 / med / p75) | $0.53 / $0.60 / $0.64 | **$0.62 / $0.65 / $0.72** | $0.59 / $0.66 / $0.69 |
| Dip depth (p25 / med / p75) | $0.085 / $0.094 / $0.116 | **$0.087 / $0.093 / $0.108** | $0.086 / $0.097 / $0.114 |
| Hold sec (p25 / med / p75) | 960 / 1920 / 3240 | **1110 / 2370 / 3630** | 765 / 2460 / 3540 |
| Entry period split | Q1: 34%, Q2: 34%, Q3: 10%, Q4: 21%, Q5: 0% | **Q1: 43%, Q2: 19%, Q3: 22%, Q4: 16%, Q5: 0%** | Q1: 26%, Q2: 33%, Q3: 21%, Q4: 19%, Q5: 2% |
| Re-entry rate | 24.1% | **24.3%** | 30.2% |
| Hit % / Stop % / Held % | 48.3% / 51.7% / 0.0% | **64.9% / 35.1% / 0.0%** | 58.1% / 41.9% / 0.0% |

## Part 6 — Game-level concentration
- Distinct games producing entries: **28**
- Games with 1 entry: 19
- Games with 2 entries (primary + re-entry): 9
- Games with at least one target hit ($0.90 exit): 21 (75.0% of games-with-entry)

## Verdict
- Bootstrap P(mean > $0): **91.1%** (not robust)
- Leave-one-out min mean: **$+5.32** (never goes negative)
- Max single-entry swing: **22%** of full mean (≤ 50% → stable)
- Profile divergent from adjacent buckets: **yes** (entry-price median Δ > $0.03 from at least one neighbor, or hit-rate Δ > 10pp from both neighbors)

**Inconclusive at current sample size.**

The 5.5–6.0 bucket is positive and stable on most tests, but the sample is small enough that a structural vs noise verdict isn't warranted. Revisit once the dataset grows via the forward-collection cron.

