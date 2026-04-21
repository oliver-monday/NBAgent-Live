# Strategy 3 — Stop-Loss Sweep & Position Management

_Generated: 2026-04-21T05:48:39.205218+00:00_

General-purpose replay engine over 165 competitive Kalshi games (|spread| ≤ 6). Sweeps stop-loss levels, averaging-in variants, and partial-exit variants. Identifies the configuration with highest mean P&L per entry and compares to the naive (no stop, no scaling) baseline.

**Params:** entry=$0.40, exit=$0.50, contracts per entry=100, maker-maker fees.

## Part 1 — Stop-loss parameter sweep

Sweep stop-loss from $0.20 to $0.39 (plus no-stop baseline). For each level, replay all entries across **165 competitive games**.

| Stop-loss | Entries | RT | Stopped | Res loss | False stops | Mean P&L | Median P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| None | 425 | 262 | 0 | 163 | 0.0% | $-4.22 | $+11.29 | $-5,963 |
| $0.39 | 745 | 71 | 674 | 0 | 61.4% | $-1.46 | $-2.03 | $-3,630 |
| $0.38 | 705 | 88 | 617 | 0 | 60.3% | $-1.53 | $-2.81 | $-3,593 |
| $0.37 | 681 | 107 | 574 | 0 | 58.2% | $-1.47 | $-3.48 | $-3,323 |
| $0.36 | 644 | 126 | 518 | 0 | 55.8% | $-1.41 | $-4.08 | $-3,018 |
| $0.35 | 619 | 136 | 483 | 0 | 53.6% | $-1.49 | $-4.61 | $-3,072 |
| $0.34 | 597 | 154 | 443 | 0 | 50.8% | $-1.27 | $-5.23 | $-2,531 |
| $0.33 | 579 | 163 | 416 | 0 | 49.0% | $-1.31 | $-6.03 | $-2,516 |
| $0.32 | 563 | 169 | 394 | 0 | 47.5% | $-1.47 | $-6.85 | $-2,747 |
| $0.31 | 556 | 178 | 378 | 0 | 46.8% | $-1.70 | $-7.44 | $-3,149 |
| $0.30 | 544 | 187 | 357 | 0 | 44.5% | $-1.65 | $-7.70 | $-2,989 |
| $0.29 | 531 | 193 | 338 | 0 | 41.7% | $-1.75 | $-8.40 | $-3,098 |
| $0.28 | 521 | 202 | 319 | 0 | 39.2% | $-1.59 | $-8.56 | $-2,748 |
| $0.27 | 510 | 206 | 304 | 0 | 37.5% | $-1.60 | $-9.19 | $-2,710 |
| $0.26 | 502 | 209 | 293 | 0 | 35.8% | $-1.87 | $-9.73 | $-3,129 |
| $0.25 | 494 | 214 | 280 | 0 | 33.6% | $-1.94 | $-9.45 | $-3,192 |
| $0.24 | 486 | 219 | 267 | 0 | 30.7% | $-1.87 | $-9.60 | $-3,025 |
| $0.23 | 483 | 221 | 262 | 0 | 29.8% | $-2.04 | $-10.21 | $-3,283 |
| $0.22 | 478 | 227 | 251 | 0 | 27.1% | $-1.96 | $-9.37 | $-3,120 |
| $0.21 | 471 | 229 | 242 | 0 | 25.2% | $-2.06 | $-8.03 | $-3,232 |
| $0.20 | 467 | 230 | 237 | 0 | 24.5% | $-2.39 | $-1.52 | $-3,709 |

### Part 1 key metrics

- **Optimal stop-loss (max mean P&L): $0.34**
  - Mean P&L at optimum: **$-1.27** (vs $-4.22 baseline)
  - Annual EV at optimum: **$-2,531** (vs $-5,963 baseline)
  - False-stop rate at optimum: 50.8%
  - Win rate at optimum: 28.1%
- **No breakeven stop-loss found in sweep range.**

## Part 2 — Averaging-in simulation

Testing averaging-in with the optimal stop-loss from Part 1 ($0.34). Initial 50 contracts at entry; add 50 if price continues down.

| Config | Entries | Avg-in triggered | Mean basis | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|
| A (no avg-in) | 597 | — | $0.3682 | $-1.27 | $-2,531 |
| B (avg @$0.35) | 597 | 26.3% | $0.3637 | $-0.59 | $-1,175 |
| C (avg @$0.30) | 597 | 0.0% | $0.3682 | $-0.64 | $-1,272 |

## Part 3 — Partial exit simulation

Optimal stop-loss applied ($0.34). Config D = baseline (100 contracts, one exit at $0.50). Config E = 50c exit at $0.48, remaining 50c exit at $0.55.

| Config | Entries | Partial exits | Full exits | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|
| D (no partial) | 597 | 0 | 154 | $-1.27 | $-2,531 |
| E (partial @$0.48, full @$0.55) | 552 | 109 | 0 | $-1.41 | $-2,589 |

## Part 4 — Combined best strategy

Grid-search over stop-loss × {avg-in off / $0.35 / $0.30} × {partial off / $0.48}.

### Best configuration found

- Entry: $0.40 (50 contracts initial)
- Average-in: $0.35 (50 contracts addon)
- Partial exit: none
- Full exit: $0.50
- Stop-loss: $0.34

**Performance on 165 competitive games:**

- Total entries: 597
- Win rate: 28.0%
- Mean P&L per entry: $-0.59
- Median P&L per entry: $-3.02
- Annual EV (549 games × entries/game × mean): **$-1,175**
- Max single-entry loss: $-16.38
- Sharpe-like ratio: -0.094

### Comparison to naive (no stop, no scaling)

- EV improvement: $+4,787/year
- Max loss: $-40.39 → $-16.38

## Part 5 — Stop-loss by game context

### By entry period

| Entry Q | Entries | Win rate | Mean P&L (stop) | Mean P&L (no stop) | Stop helped? |
|---|---:|---:|---:|---:|---|
| Q1 | 198 | 26.8% | $-1.18 | $-3.25 | yes |
| Q2 | 118 | 32.2% | $-0.58 | $-7.76 | yes |
| Q3 | 110 | 24.5% | $-2.19 | $-7.59 | yes |
| Q4 | 155 | 29.7% | $-1.16 | $-1.97 | yes |
| OT | 16 | 25.0% | $-2.35 | $-0.16 | no |

### By spread bucket

| |Spread| | Entries | Win rate | Mean P&L (stop) | Mean P&L (no stop) | Stop helped? |
|---|---:|---:|---:|---:|---|
| 1-2 | 133 | 32.3% | $-0.69 | $-2.81 | yes |
| 2.5-3.5 | 270 | 28.5% | $-1.16 | $-3.04 | yes |
| 4-5 | 88 | 28.4% | $-1.04 | $-7.65 | yes |
| 5.5-6 | 106 | 21.7% | $-2.48 | $-6.04 | yes |

