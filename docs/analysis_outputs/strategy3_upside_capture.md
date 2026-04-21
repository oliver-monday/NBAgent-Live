# Strategy 3 — Upside Capture & Trailing Stops

_Generated: 2026-04-21T06:18:31.505312+00:00_

Extends the stop-loss sweep with resolution upside capture. Split positions: partial exit at $0.50, held remainder ride a trailing stop or resolution. 96-configuration grid search over {initial_stop × sell_pct × trailing_distance}.

**Params:** entry=$0.40, first_exit=$0.50, 100 contracts per entry, maker-maker fees.

## Part 1 — Scale-out ratio sweep

Initial stop $0.34 (optimum from prior sweep), trailing distance $0.05.

| Sell % | Entries | Partial exits | Trail outs | Held to win | Held to loss | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| 100% | 597 | 154 | 0 | 0 | 0 | $-1.27 | $-2,531 |
| 75% | 586 | 154 | 148 | 6 | 0 | $-1.16 | $-2,268 |
| 50% | 586 | 154 | 148 | 6 | 0 | $-1.20 | $-2,335 |
| 25% | 586 | 154 | 148 | 6 | 0 | $-1.23 | $-2,401 |
| 0% | 494 | 0 | 0 | 43 | 0 | $-0.92 | $-1,520 |

**Best sell %: 0% (mean P&L $-0.92)**

## Part 2 — Trailing stop distance sweep

Initial stop $0.34, scale-out 0%. Also tests 'no trailing stop' = hold remainder to resolution.

| Trail dist | Entries | Trail outs | Held to win | Held to loss | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|
| $0.03 | 494 | 0 | 43 | 0 | $-0.92 | $-1,520 |
| $0.05 | 494 | 0 | 43 | 0 | $-0.92 | $-1,520 |
| $0.07 | 494 | 0 | 43 | 0 | $-0.92 | $-1,520 |
| $0.10 | 494 | 0 | 43 | 0 | $-0.92 | $-1,520 |
| $0.15 | 494 | 0 | 43 | 0 | $-0.92 | $-1,520 |
| $0.20 | 494 | 0 | 43 | 0 | $-0.92 | $-1,520 |
| No trail | 494 | 0 | 43 | 0 | $-0.92 | $-1,520 |

**Best trailing distance: $0.03 (mean P&L $-0.92)**

## Part 3 — Initial stop-loss re-sweep with upside capture

Scale-out 0%, trailing $0.03.

| Stop | Entries | Scale-outs | Stopped | Trail outs | Res wins | Res losses | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| None | 249 | 0 | 0 | 0 | 84 | 165 | $-3.69 | $-3,056 |
| $0.20 | 311 | 0 | 240 | 0 | 71 | 0 | $-1.35 | $-1,398 |
| $0.22 | 323 | 0 | 254 | 0 | 69 | 0 | $-0.95 | $-1,019 |
| $0.24 | 338 | 0 | 271 | 0 | 67 | 0 | $-0.70 | $-790 |
| $0.26 | 362 | 0 | 298 | 0 | 64 | 0 | $-0.81 | $-971 |
| $0.28 | 384 | 0 | 324 | 0 | 60 | 0 | $-0.80 | $-1,021 |
| $0.30 | 418 | 0 | 363 | 0 | 55 | 0 | $-0.97 | $-1,343 |
| $0.32 | 450 | 0 | 401 | 0 | 49 | 0 | $-0.89 | $-1,330 |
| $0.34 | 494 | 0 | 451 | 0 | 43 | 0 | $-0.92 | $-1,520 |
| $0.36 | 560 | 0 | 526 | 0 | 34 | 0 | $-1.38 | $-2,573 |
| $0.38 | 650 | 0 | 625 | 0 | 25 | 0 | $-1.44 | $-3,114 |

**Best initial stop: $0.24 (mean P&L $-0.70)**

## Part 4 — Full grid search (96 configurations)

Sweeping: stop_loss ∈ {None, 0.30, 0.32, 0.34, 0.36, 0.38} × sell_pct ∈ {1.0, 0.75, 0.50, 0.25} × trailing_stop_distance ∈ {0.05, 0.10, 0.15, None}.

### Top 10 by mean P&L

| Rank | Stop | Sell % | Trail | Entries | Win rate | Mean P&L | Annual EV |
|---|---|---:|---|---:|---:|---:|---:|
| 1 | $0.34 | 25% | None | 433 | 16.6% | $-0.59 | $-852 |
| 2 | $0.34 | 50% | None | 433 | 16.9% | $-0.82 | $-1,174 |
| 3 | $0.34 | 25% | $0.15 | 547 | 24.9% | $-0.95 | $-1,720 |
| 4 | $0.32 | 25% | None | 393 | 18.1% | $-0.98 | $-1,278 |
| 5 | $0.34 | 50% | $0.15 | 547 | 28.3% | $-0.99 | $-1,796 |
| 6 | $0.34 | 25% | $0.10 | 571 | 27.8% | $-1.02 | $-1,946 |
| 7 | $0.34 | 75% | $0.15 | 547 | 28.9% | $-1.03 | $-1,871 |
| 8 | $0.34 | 50% | $0.10 | 571 | 28.5% | $-1.04 | $-1,968 |
| 9 | $0.34 | 75% | None | 433 | 21.9% | $-1.04 | $-1,496 |
| 10 | $0.32 | 25% | $0.10 | 536 | 31.9% | $-1.04 | $-1,855 |

### Top 10 by Sharpe-like ratio (mean / std)

| Rank | Stop | Sell % | Trail | Mean P&L | Std P&L | Sharpe |
|---|---|---:|---|---:|---:|---:|
| 1 | $0.34 | 25% | None | $-0.59 | $21.32 | -0.028 |
| 2 | $0.32 | 25% | None | $-0.98 | $23.21 | -0.042 |
| 3 | $0.34 | 50% | None | $-0.82 | $16.02 | -0.051 |
| 4 | $0.36 | 25% | None | $-1.05 | $18.46 | -0.057 |
| 5 | $0.30 | 25% | None | $-1.41 | $24.76 | -0.057 |
| 6 | $0.32 | 50% | None | $-1.12 | $17.49 | -0.064 |
| 7 | $0.34 | 25% | $0.15 | $-0.95 | $13.88 | -0.068 |
| 8 | $0.30 | 25% | $0.15 | $-1.14 | $16.50 | -0.069 |
| 9 | $0.32 | 25% | $0.15 | $-1.06 | $15.24 | -0.070 |
| 10 | None | 25% | $0.15 | $-2.14 | $30.29 | -0.071 |

## Part 5 — Best configuration detailed breakdown

### Best configuration

- Entry: $0.40 (100 contracts)
- Initial stop-loss: $0.34
- At first exit ($0.50): sell 25 contracts, hold 75
- Trailing stop on held remainder: None (hold to resolution)

### Outcome distribution

| Outcome | Count | % | Mean P&L | Median P&L |
|---|---:|---:|---:|---:|
| Full exit at first target | 0 | 0.0% | — | — |
| Stopped out (never reached first exit) | 324 | 74.8% | $-6.29 | $-6.43 |
| Partial exit + trailed out | 0 | 0.0% | — | — |
| Partial exit + held to win | 61 | 14.1% | $+49.16 | $+48.36 |
| Partial exit + held to loss | 48 | 11.1% | $-25.34 | $-25.95 |
| Held indeterminate | 0 | 0.0% | — | — |
| **ALL** | **433** | 100.0% | **$-0.59** | **$-6.28** |

### P&L distribution

| P&L bucket | Count | % |
|---|---:|---:|
| < -$30 | 0 | 0.0% |
| -$30 to -$20 | 48 | 11.1% |
| -$20 to -$10 | 29 | 6.7% |
| -$10 to $0 | 284 | 65.6% |
| $0 to $10 | 11 | 2.5% |
| $10 to $20 | 0 | 0.0% |
| $20 to $30 | 0 | 0.0% |
| $30 to $50 | 47 | 10.9% |
| > $50 | 14 | 3.2% |

### By entry period

| Entry Q | Entries | Win rate | Mean P&L |
|---|---:|---:|---:|
| Q1 | 191 | 16.8% | $-0.45 |
| Q2 | 86 | 19.8% | $+1.74 |
| Q3 | 65 | 12.3% | $-2.22 |
| Q4 | 84 | 17.9% | $-0.93 |
| OT | 7 | 0.0% | $-13.95 |

### By spread bucket

| |Spread| | Entries | Win rate | Mean P&L |
|---|---:|---:|---:|
| 1-2 | 90 | 16.7% | $-0.27 |
| 2.5-3.5 | 192 | 16.1% | $-0.21 |
| 4-5 | 63 | 15.9% | $-1.42 |
| 5.5-6 | 88 | 18.2% | $-1.17 |

### Risk metrics

| Metric | Value |
|---|---|
| Sharpe-like (mean/std) | -0.028 |
| Win rate (net > 0) | 16.6% |
| Mean winner | $+41.85 |
| Mean loser | $-9.06 |
| Win/loss ratio | 4.62× |
| Max single loss | $-27.87 |
| Max single win | $+58.06 |
| Kelly f* | -0.014 |

## Part 6 — Strategy evolution comparison

| Strategy | Mean P&L | Annual EV | Max loss | Sharpe |
|---|---:|---:|---:|---:|
| Naive (no stop, exit at $0.50) | −$4.22 | −$5,963 | −$40.39 | −0.16 |
| Best stop-loss only (prior sweep) | −$1.27 | −$2,531 | −$16.38 | −0.09 |
| Best stop + avg-in (prior sweep) | −$0.59 | −$1,175 | −$16.38 | — |
| **Best with upside capture** | **$-0.59** | **$-852** | **$-27.87** | **-0.03** |
| Bilateral only (guaranteed) | +$19.14 | +$1,608 | $0 | ∞ |

