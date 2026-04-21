# Strategy 3 — Entry Filter Sweep

_Generated: 2026-04-21T06:54:20.353859+00:00_

Tests entry-side filters on the Strategy 3 replay engine across 165 competitive games. Four filters: oscillation confirmation, ESPN WP rate-of-change, favorite-side only, and period restriction. Individual sweeps (Part 1), best-individual with both exits (Part 2), combined grid search (Part 3), best-config detail (Part 4), evolution table (Part 5), filter diagnostic (Part 6).

## Part 1A — Oscillation confirmation

Only enter if this side's Kalshi price was ≥ `recent_high` within the last `lookback` seconds. Simple exit (100% at $0.50, stop $0.34).

| Filter | Entries | Filtered out | Completed RT | Failed | Fail rate | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| No filter | 597 | 0 | 154 | 443 | 74.2% | $-1.27 | $-2,531 |
| 2 min / $0.45 | 297 | 0 | 80 | 217 | 73.1% | $-1.53 | $-1,513 |
| 2 min / $0.48 | 184 | 0 | 45 | 139 | 75.5% | $-1.49 | $-912 |
| 2 min / $0.50 | 132 | 0 | 35 | 97 | 73.5% | $-0.66 | $-289 |
| 2 min / $0.55 | 74 | 0 | 22 | 52 | 70.3% | $+0.90 | $+221 |
| 3 min / $0.45 | 329 | 0 | 88 | 241 | 73.3% | $-1.52 | $-1,668 |
| 3 min / $0.48 | 228 | 0 | 62 | 166 | 72.8% | $-1.13 | $-857 |
| 3 min / $0.50 | 171 | 0 | 48 | 123 | 71.9% | $-0.53 | $-303 |
| 3 min / $0.55 | 97 | 0 | 27 | 70 | 72.2% | $+0.16 | $+51 |
| 5 min / $0.45 | 364 | 0 | 92 | 272 | 74.7% | $-1.85 | $-2,246 |
| 5 min / $0.48 | 277 | 0 | 77 | 200 | 72.2% | $-1.25 | $-1,155 |
| 5 min / $0.50 | 217 | 0 | 59 | 158 | 72.8% | $-1.22 | $-883 |
| 5 min / $0.55 | 131 | 0 | 37 | 94 | 71.8% | $-0.64 | $-279 |
| 10 min / $0.45 | 398 | 0 | 101 | 297 | 74.6% | $-1.83 | $-2,428 |
| 10 min / $0.48 | 336 | 0 | 88 | 248 | 73.8% | $-1.50 | $-1,681 |
| 10 min / $0.50 | 289 | 0 | 75 | 214 | 74.0% | $-1.49 | $-1,430 |
| 10 min / $0.55 | 200 | 0 | 54 | 146 | 73.0% | $-1.12 | $-744 |
| 15 min / $0.45 | 412 | 0 | 106 | 306 | 74.3% | $-1.77 | $-2,431 |
| 15 min / $0.48 | 357 | 0 | 95 | 262 | 73.4% | $-1.41 | $-1,676 |
| 15 min / $0.50 | 316 | 0 | 81 | 235 | 74.4% | $-1.54 | $-1,615 |
| 15 min / $0.55 | 230 | 0 | 62 | 168 | 73.0% | $-1.15 | $-878 |
| 20 min / $0.45 | 418 | 0 | 109 | 309 | 73.9% | $-1.70 | $-2,366 |
| 20 min / $0.48 | 369 | 0 | 99 | 270 | 73.2% | $-1.42 | $-1,740 |
| 20 min / $0.50 | 337 | 0 | 89 | 248 | 73.6% | $-1.44 | $-1,615 |
| 20 min / $0.55 | 249 | 0 | 66 | 183 | 73.5% | $-1.38 | $-1,145 |

**Best oscillation filter: lookback 120s, recent_high $0.55 → mean P&L $+0.90**

## Part 1B — ESPN WP rate-of-change

Only enter if this side's ESPN WP dropped ≥ `drop` within the last `lookback` seconds. Simple exit.

| Filter | Entries | Filtered out | Completed RT | Failed | Fail rate | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| No filter | 597 | 0 | 154 | 443 | 74.2% | $-1.27 | $-2,531 |
| 2 min / 3pp | 372 | 0 | 104 | 268 | 72.0% | $-1.00 | $-1,233 |
| 2 min / 5pp | 328 | 0 | 91 | 237 | 72.3% | $-1.02 | $-1,116 |
| 2 min / 8pp | 249 | 0 | 66 | 183 | 73.5% | $-1.19 | $-989 |
| 2 min / 10pp | 187 | 0 | 41 | 146 | 78.1% | $-2.24 | $-1,391 |
| 3 min / 3pp | 352 | 0 | 96 | 256 | 72.7% | $-1.33 | $-1,552 |
| 3 min / 5pp | 320 | 0 | 90 | 230 | 71.9% | $-1.11 | $-1,183 |
| 3 min / 8pp | 258 | 0 | 73 | 185 | 71.7% | $-1.04 | $-890 |
| 3 min / 10pp | 217 | 0 | 60 | 157 | 72.4% | $-1.18 | $-854 |
| 5 min / 3pp | 357 | 0 | 93 | 264 | 73.9% | $-1.79 | $-2,126 |
| 5 min / 5pp | 324 | 0 | 85 | 239 | 73.8% | $-1.68 | $-1,813 |
| 5 min / 8pp | 269 | 0 | 71 | 198 | 73.6% | $-1.58 | $-1,418 |
| 5 min / 10pp | 233 | 0 | 64 | 169 | 72.5% | $-1.42 | $-1,101 |

**Best WP-momentum filter: lookback 120s, drop ≥ 3pp → mean P&L $-1.00**

## Part 1C — Favorite-side only

| Filter | Entries | Filtered out | Completed RT | Failed | Fail rate | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| Both sides | 597 | 0 | 154 | 443 | 74.2% | $-1.27 | $-2,531 |
| Fav only | 211 | — | 54 | 157 | 74.4% | $-1.99 | $-1,399 |
| Dog only | 386 | — | 100 | 286 | 74.1% | $-0.88 | $-1,131 |

Note: dog-only mean P&L ($-0.88) exceeds fav-only ($-1.99) — worth investigating but not combinable with the current FilterConfig shape.

**Favorite-side filter → mean P&L $-1.99 (vs both-sides baseline $-1.27)**

## Part 1D — Period restriction

| Filter | Entries | Filtered out | Completed RT | Failed | Fail rate | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| All periods | 597 | 0 | 154 | 443 | 74.2% | $-1.27 | $-2,531 |
| Q1 only | 198 | 0 | 45 | 153 | 77.3% | $-1.18 | $-777 |
| Q1+Q2 | 316 | 0 | 83 | 233 | 73.7% | $-0.96 | $-1,005 |
| Q1+Q2+Q3 | 427 | 0 | 109 | 318 | 74.5% | $-1.29 | $-1,836 |

**Best period filter: Q1/2 → mean P&L $-0.96**

## Part 2 — Best individual filters with both exit strategies

| Config | Filter | Entries | Mean P&L (simple) | Mean P&L (upside) | Annual EV (upside) |
|---|---|---:|---:|---:|---:|
| Baseline | None | 597 | $-1.27 | $-0.59 | $-852 |
| Best oscillation | osc 120s / $0.55 | 74 | $+0.90 | $+0.86 | $+180 |
| Best WP momentum | wp 120s / 3pp | 372 | $-1.00 | $-0.64 | $-605 |
| Best fav-only | fav_only=True | 211 | $-1.99 | $-2.50 | $-1,290 |
| Best period | Q1/2 | 316 | $-0.96 | $+0.23 | $+212 |

## Part 3 — Combined filter grid search

2×2×2×2 = 16 filter combinations × 2 exit strategies = **32 configurations**. Sorted by mean P&L descending. Positive-EV rows (if any) bolded.

| # | Osc | WP | Fav | Period | Exit | Entries | Fail rate | Mean P&L | Annual EV |
|---|:-:|:-:|:-:|:-:|:-:|---:|---:|---:|---:|
| 1 | — | ✓ | ✓ | ✓ | upside | 51 | 78.4% | **$+3.41** | **$+578** |
| 2 | ✓ | ✓ | — | — | upside | 57 | 80.7% | **$+1.76** | **$+334** |
| 3 | — | ✓ | — | ✓ | upside | 152 | 80.9% | **$+1.43** | **$+725** |
| 4 | ✓ | ✓ | — | — | simple | 64 | 70.3% | **$+1.43** | **$+304** |
| 5 | ✓ | — | — | — | simple | 74 | 70.3% | **$+0.90** | **$+221** |
| 6 | ✓ | — | — | — | upside | 63 | 81.0% | **$+0.86** | **$+180** |
| 7 | ✓ | — | ✓ | — | simple | 37 | 70.3% | **$+0.66** | **$+82** |
| 8 | — | — | — | ✓ | upside | 277 | 85.2% | **$+0.23** | **$+212** |
| 9 | — | — | — | — | upside | 433 | 85.9% | $-0.59 | $-852 |
| 10 | — | — | ✓ | ✓ | upside | 69 | 84.1% | $-0.60 | $-137 |
| 11 | — | ✓ | — | — | upside | 283 | 84.5% | $-0.64 | $-605 |
| 12 | — | ✓ | ✓ | ✓ | simple | 55 | 69.1% | $-0.76 | $-139 |
| 13 | — | ✓ | — | ✓ | simple | 168 | 69.0% | $-0.78 | $-434 |
| 14 | — | — | — | ✓ | simple | 316 | 73.7% | $-0.96 | $-1,005 |
| 15 | — | ✓ | — | — | simple | 372 | 72.0% | $-1.00 | $-1,233 |
| 16 | — | — | ✓ | ✓ | simple | 76 | 71.1% | $-1.11 | $-280 |
| 17 | ✓ | ✓ | ✓ | — | simple | 33 | 75.8% | $-1.16 | $-127 |
| 18 | — | — | — | — | simple | 597 | 74.2% | $-1.27 | $-2,531 |
| 19 | ✓ | — | ✓ | — | upside | 31 | 83.9% | $-1.83 | $-189 |
| 20 | — | ✓ | ✓ | — | upside | 124 | 86.3% | $-1.96 | $-811 |
| 21 | — | — | ✓ | — | simple | 211 | 74.4% | $-1.99 | $-1,399 |
| 22 | ✓ | ✓ | ✓ | — | upside | 29 | 86.2% | $-2.21 | $-213 |
| 23 | — | ✓ | ✓ | — | simple | 155 | 75.5% | $-2.23 | $-1,152 |
| 24 | — | — | ✓ | — | upside | 155 | 87.1% | $-2.50 | $-1,290 |
| 25 | ✓ | ✓ | ✓ | ✓ | simple | 0 | 0.0% | $+nan | $+0 |
| 26 | ✓ | ✓ | ✓ | ✓ | upside | 0 | 0.0% | $+nan | $+0 |
| 27 | ✓ | ✓ | — | ✓ | simple | 0 | 0.0% | $+nan | $+0 |
| 28 | ✓ | ✓ | — | ✓ | upside | 0 | 0.0% | $+nan | $+0 |
| 29 | ✓ | — | ✓ | ✓ | simple | 0 | 0.0% | $+nan | $+0 |
| 30 | ✓ | — | ✓ | ✓ | upside | 0 | 0.0% | $+nan | $+0 |
| 31 | ✓ | — | — | ✓ | simple | 0 | 0.0% | $+nan | $+0 |
| 32 | ✓ | — | — | ✓ | upside | 0 | 0.0% | $+nan | $+0 |

**Best combined: osc=False, wp=True, fav=True, period=True, exit=upside → mean P&L $+3.41**

Positive-EV configurations found: **8 of 32**

## Part 4 — Best configuration detailed breakdown

### Best configuration

- Entry: $0.40 (100 contracts)
- Filters:
  - Oscillation: off
  - ESPN WP momentum: on — lookback 120s, drop ≥ 3pp
  - Favorite-side only: yes
  - Period restriction: Q1/2
- Exit strategy: upside
- Stop-loss: $0.34

### Outcome distribution

| Outcome | Count | % | Mean P&L | Median P&L |
|---|---:|---:|---:|---:|
| Full exit (first target) | 0 | 0.0% | — | — |
| Stopped out | 35 | 68.6% | $-6.53 | $-6.48 |
| Trailed out | 0 | 0.0% | — | — |
| Resolution win | 11 | 21.6% | $+48.82 | $+48.48 |
| Resolution loss | 5 | 9.8% | $-26.96 | $-27.10 |
| Held indeterminate | 0 | 0.0% | — | — |
| **ALL** | **51** | 100.0% | **$+3.41** | **$-6.24** |

### P&L distribution

| P&L bucket | Count | % |
|---|---:|---:|
| < -$30 | 0 | 0.0% |
| -$30 to -$20 | 5 | 9.8% |
| -$20 to -$10 | 3 | 5.9% |
| -$10 to $0 | 32 | 62.7% |
| $0 to $10 | 0 | 0.0% |
| $10 to $20 | 0 | 0.0% |
| $20 to $30 | 0 | 0.0% |
| $30 to $50 | 9 | 17.6% |
| > $50 | 2 | 3.9% |

### By spread bucket

| |Spread| | Entries | Win rate | Mean P&L |
|---|---:|---:|---:|
| 1-2 | 13 | 38.5% | $+13.05 |
| 2.5-3.5 | 28 | 10.7% | $-2.21 |
| 4-5 | 6 | 16.7% | $-3.82 |
| 5.5-6 | 4 | 50.0% | $+22.23 |

### Risk metrics

| Metric | Value |
|---|---|
| Sharpe-like | 0.137 |
| Win rate (net > 0) | 21.6% |
| Mean winner | $+48.82 |
| Mean loser | $-9.08 |
| Win/loss ratio | 5.37× |
| Max single loss | $-27.87 |
| Max single win | $+50.86 |
| Kelly f* | 0.070 |

## Part 5 — Full strategy evolution

| Strategy | Entries/yr | Mean P&L | Annual EV | Max loss | Sharpe |
|---|---:|---:|---:|---:|---:|
| 1. Naive (no stop, no filter) | ~1,404 | −$4.22 | −$5,963 | −$40 | −0.16 |
| 2. + Stop-loss @$0.34 | ~1,533 | −$1.27 | −$2,531 | −$16 | −0.09 |
| 3. + Upside capture (25/75) | ~1,112 | −$0.59 | −$852 | −$28 | −0.03 |
| 4. + Entry filters (best combo) | ~170 | **$+3.41** | **$+578** | — | 0.14 |
| 5. Bilateral only | ~84 | +$19.14 | +$1,608 | $0 | ∞ |
| 6. Best combo + bilateral | ~254 | — | $+2,186 | — | — |

## Part 6 — Filter diagnostic: what gets rejected?

Total candidate entries: **850**
- Passed filter: **51** (6.0%)
- Filtered out: **799** (94.0%)


Of the filtered-out entries:
- Would have reached first exit ($0.50) if held: **515** (64.5%)
- Would NOT have reached first exit: **284** (35.5%) — correctly rejected

**Filter precision** (correctly rejected / total rejected): 35.5%
**Filter recall** (good entries kept / total good entries): 2.1%

