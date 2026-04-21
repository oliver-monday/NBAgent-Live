# Strategy 3 — Holdout Validation

_Generated: 2026-04-21T10:02:16.359382+00:00_

Tests whether the positive-EV entry-filter configurations found by `strategy3_entry_filters.py` survive a train/test split. If the best train config produces positive mean P&L on held-out test games, filters are **validated**. If not, they are **curve-fit** and should be deprioritized.

## Part 1 — Train/Test Split

Games shuffled with `numpy.random.default_rng(seed=42)` then split 110/55. Split is at the game level so entries from the same game stay together.

| Split | Games | Entries (unfiltered, simple exit) | Date range |
|---|---:|---:|---|
| Train | 110 | 376 | 2026-02-20 → 2026-04-15 |
| Test | 55 | 221 | 2026-02-20 → 2026-04-14 |

## Part 2 — Train-set 32-config grid

Full filter × exit grid on the **train set only**. Sorted by mean P&L descending. Positive-EV rows bolded.

| # | Osc | WP | Fav | Period | Exit | Entries | Mean P&L | Annual EV |
|---|:-:|:-:|:-:|:-:|:-:|---:|---:|---:|
| 1 | — | ✓ | ✓ | ✓ | upside | 32 | **$+2.85** | **$+455** |
| 2 | ✓ | ✓ | — | — | upside | 31 | **$+1.55** | **$+240** |
| 3 | ✓ | — | — | — | upside | 34 | **$+1.47** | **$+250** |
| 4 | ✓ | — | — | — | simple | 41 | **$+0.78** | **$+160** |
| 5 | — | — | — | ✓ | upside | 190 | **$+0.14** | **$+136** |
| 6 | — | ✓ | — | ✓ | upside | 102 | **$+0.13** | **$+66** |
| 7 | ✓ | ✓ | — | — | simple | 35 | $-0.01 | $-2 |
| 8 | — | — | — | — | upside | 277 | $-0.18 | $-249 |
| 9 | — | ✓ | ✓ | ✓ | simple | 34 | $-0.24 | $-41 |
| 10 | ✓ | — | ✓ | — | simple | 21 | $-0.42 | $-44 |
| 11 | — | — | — | ✓ | simple | 219 | $-0.73 | $-794 |
| 12 | — | ✓ | — | ✓ | simple | 114 | $-0.74 | $-421 |
| 13 | — | — | ✓ | ✓ | simple | 51 | $-0.79 | $-202 |
| 14 | — | ✓ | — | — | upside | 178 | $-0.89 | $-793 |
| 15 | — | — | — | — | simple | 376 | $-1.39 | $-2,605 |
| 16 | ✓ | — | ✓ | — | upside | 18 | $-1.64 | $-147 |
| 17 | — | ✓ | — | — | simple | 229 | $-1.64 | $-1,876 |
| 18 | — | — | ✓ | ✓ | upside | 47 | $-1.76 | $-413 |
| 19 | ✓ | ✓ | ✓ | — | upside | 16 | $-2.30 | $-183 |
| 20 | — | — | ✓ | — | simple | 131 | $-2.31 | $-1,512 |
| 21 | — | ✓ | ✓ | — | upside | 77 | $-2.57 | $-988 |
| 22 | — | ✓ | ✓ | — | simple | 94 | $-2.98 | $-1,399 |
| 23 | — | — | ✓ | — | upside | 96 | $-3.12 | $-1,495 |
| 24 | ✓ | ✓ | ✓ | — | simple | 17 | $-4.21 | $-357 |
| 25 | ✓ | ✓ | ✓ | ✓ | simple | 0 | — | — |
| 26 | ✓ | ✓ | ✓ | ✓ | upside | 0 | — | — |
| 27 | ✓ | ✓ | — | ✓ | simple | 0 | — | — |
| 28 | ✓ | ✓ | — | ✓ | upside | 0 | — | — |
| 29 | ✓ | — | ✓ | ✓ | simple | 0 | — | — |
| 30 | ✓ | — | ✓ | ✓ | upside | 0 | — | — |
| 31 | ✓ | — | — | ✓ | simple | 0 | — | — |
| 32 | ✓ | — | — | ✓ | upside | 0 | — | — |

## Part 3 — Test-set evaluation (the verdict)

Top 3 candidate configs from train set (top-3 by mean P&L ∪ top-3 by annual EV). Each evaluated on the held-out **test set** with no re-fitting.

| Config | Train entries | Train mean P&L | Train annual EV | Test entries | Test mean P&L | Test annual EV | Verdict |
|---|---:|---:|---:|---:|---:|---:|:-:|
| wp+fav+period/upside | 32 | $+2.85 | $+455 | 19 | $+4.35 | $+825 | ✓ VALIDATED |
| osc+wp/upside | 31 | $+1.55 | $+240 | 26 | $+2.01 | $+523 | ✓ VALIDATED |
| osc/upside | 34 | $+1.47 | $+250 | 29 | $+0.14 | $+39 | ✓ VALIDATED |

### 3B — Test-set detail for best test config

**Config:** wp+fav+period / exit=upside

#### Outcome distribution (test set)

| Exit type | Count | % | Mean P&L |
|---|---:|---:|---:|
| resolution_loss | 1 | 5.3% | $-26.45 |
| resolution_win | 4 | 21.1% | $+49.21 |
| stopped_out | 14 | 73.7% | $-6.27 |

#### Test-set P&L distribution

| Bucket | Count | % |
|---|---:|---:|
| < −$30 | 0 | 0.0% |
| −$30 to −$10 | 3 | 15.8% |
| −$10 to $0 | 12 | 63.2% |
| $0 to $10 | 0 | 0.0% |
| $10 to $20 | 0 | 0.0% |
| $20 to $30 | 0 | 0.0% |
| > $30 | 4 | 21.1% |

#### Test-set by entry period

| Period | Entries | Win rate | Mean P&L |
|---|---:|---:|---:|
| Q1 | 10 | 10.0% | $-0.80 |
| Q2 | 9 | 33.3% | $+10.07 |
| Q3 | 0 | — | — |
| Q4 | 0 | — | — |
| OT | 0 | — | — |

#### Train vs test win rate

| Split | Entries | Win rate | Mean P&L |
|---|---:|---:|---:|
| Train | 32 | 21.9% | $+2.85 |
| Test | 19 | 21.1% | $+4.35 |

## Part 4 — Stability analysis (6 seeds)

For each seed: split → sweep train → pick best-by-mean-P&L config → evaluate on test. Counts how many seeds produce a validated test result.

| Seed | Best train config | Train entries | Train mean P&L | Test entries | Test mean P&L | Test annual EV | Validated? |
|---|---|---:|---:|---:|---:|---:|:-:|
| 42 | wp+fav+period/upside | 32 | $+2.85 | 19 | $+4.35 | $+825 | ✓ |
| 43 | osc/simple | 43 | $+2.47 | 31 | $-1.28 | $-396 | ✗ |
| 44 | osc+wp/simple | 40 | $+1.57 | 24 | $+1.18 | $+283 | ✓ |
| 45 | wp+fav+period/upside | 32 | $+4.17 | 19 | $+2.12 | $+403 | ✓ |
| 46 | osc+wp/upside | 39 | $+4.76 | 18 | $-4.73 | $-849 | ✗ |
| 47 | wp+fav+period/upside | 33 | $+4.23 | 18 | $+1.90 | $+342 | ✓ |

**Seeds validated: 4 / 6.**

≥ 4 of 6 seeds produced a positive test-set P&L — filters are **robust across splits**.

## Part 5 — S4A cross-reference on same split

Consistency check: S4A has no fitted parameters to validate (it's a single hypothesized config). Running it on train and test halves measures data-set homogeneity.

| Strategy | Train entries | Train mean P&L | Test entries | Test mean P&L | Consistent? |
|---|---:|---:|---:|---:|:-:|
| S3 best filter | 32 | $+2.85 | 19 | $+4.35 | ✓ |
| S4A best config | 108 | $+3.19 | 53 | $+4.24 | ✓ |

_Consistency tolerance: ±$5 mean-P&L gap between train and test._

## Part 6 — Final verdict

**Strategy 3 filtered: VALIDATED** (4 of 6 seeds validated)

- Recommended filter config: **wp+fav+period/upside**
- Test-set mean P&L: **$+4.35/entry**
- Test-set annual EV estimate: **$+825** (from held-out sample, not train)

### Combined annual-EV projection

| Strategy | Annual EV |
|---|---:|
| S1 bilateral | +$1,608 |
| S3 filtered (test-set estimate) | +$825 |
| S4A best config (test-set half) | $+2,234 |
| **Combined** | **$+4,667** |

