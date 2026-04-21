# WP vs Kalshi Paired Analysis: POR @ SAS

**Date:** 2026-04-20  |  **ESPN ID:** 401869194  |  **Kalshi:** KXNBAGAME-26APR19PORSAS
**Final:** SAS 111 – POR 98
**Pre-game spread:** -11.5  |  **Favorite:** SAS
**Pre-game ESPN WP (fav):** 83.1%
**Pre-game Kalshi (fav):** $0.8700
**Pre-game delta:** +3.9pp
**Kalshi trades:** 50,838 trades, 21,720,939 contracts
**Strategy 3 filter:** excluded from Strategy 3 universe  (|spread| 11.5)

## §1 — Pre-game snapshot

- Pre-game ESPN WP (fav): **83.1%** vs Kalshi (fav): **$0.8700**. Δ = **+3.9pp** (above ESPN).
- Compression pattern reference: prior work shows Kalshi +10-14pp above ESPN at low fav WP and −10-14pp below at high fav WP. ⚠ **Direction reversed.** At fav WP 0.83 the compression pattern predicts Kalshi BELOW ESPN, but here Kalshi is above ESPN by 3.9pp. Possible retail-flow signature on a non-competitive line.


## §2 — Delta across game time

**Overall:** mean Δ = +0.59pp, median +0.01pp, std 1.63pp, min -1.85pp, max +8.27pp, n=286.
**Direction:** Δ > 0 in 50% of buckets, Δ < 0 in 50%.

### By quarter

| Period | Mean Δ | Median Δ | Std Δ | N obs |
|---|---:|---:|---:|---:|
| Q1 | +1.76pp | +1.48pp | 1.34pp | 60 |
| Q2 | +0.30pp | +0.12pp | 0.98pp | 94 |
| Q3 | +1.32pp | +0.17pp | 2.27pp | 62 |
| Q4 | -0.67pp | -0.80pp | 0.30pp | 70 |
| All | +0.59pp | +0.01pp | 1.63pp | 286 |

### By WP zone (ESPN fav WP)

| WP zone | Mean Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|
| 0.00-0.20 | — | 0 | — |
| 0.20-0.40 | — | 0 | — |
| 0.40-0.60 | — | 0 | — |
| 0.60-0.80 | +6.20pp | 4 | 100% |
| 0.80-1.00 | +0.51pp | 282 | 50% |


## §3 — Convergence analysis

| Time remaining | Mean |Δ| | Median |Δ| | N obs |
|---|---:|---:|---:|
| > 36 min | 1.93pp | 1.57pp | 54 |
| 24-36 min | 0.91pp | 0.68pp | 69 |
| 12-24 min | 1.40pp | 0.53pp | 86 |
| 6-12 min | 0.70pp | 0.80pp | 42 |
| 3-6 min | 0.54pp | 0.55pp | 20 |
| 1-3 min | 0.75pp | 0.75pp | 8 |
| 0-1 min | 0.90pp | 0.90pp | 5 |

**Regression:** |Δ| ~ elapsed_sec → slope -0.000005/s, R² = 0.077, p = 1.85e-06. Negative slope = convergence.

**Final 2 minutes:** mean |Δ| = 0.90pp (n=9).


## §4 — Scoring play response comparison

Coverage: **103/105** (98%) scoring plays have Kalshi prices in both the ±5s-before and +3-to-15s-after windows.

### By score value

| Score value | n | Mean wp_delta (pp) | Mean Kalshi Δ (pp) | Mean reaction diff (pp) |
|---|---:|---:|---:|---:|
| 1-pt | 25 | -0.03pp | +0.08pp | -0.11pp |
| 2-pt | 54 | +0.03pp | -0.04pp | +0.06pp |
| 3-pt | 24 | +0.39pp | +0.29pp | +0.10pp |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean kalshi Δ | Mean diff |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 0 | — | — | — |
| 0.20-0.40 | 0 | — | — | — |
| 0.40-0.60 | 0 | — | — | — |
| 0.60-0.80 | 1 | +1.80pp | +0.00pp | +1.80pp |
| 0.80-1.00 | 102 | +0.08pp | +0.07pp | +0.01pp |


## §5 — Strategy 3 zone mapping

_Game never entered Strategy 3 zone_ (fav Kalshi VWAP never in [$0.35, $0.65]). Expected for games with |spread| > 6.


## §6 — Timeout windows

Detected **10** timeout events.

| # | Period | Clock | Fav WP | Fav Kalshi | Δ | ±60s std |
|---|---:|---:|---:|---:|---:|---:|
| 1 | Q1 | 6:37 | 0.85 | 0.8615 | +1.25pp | 1.01pp |
| 2 | Q1 | 1:33 | 0.91 | 0.9218 | +0.78pp | 1.21pp |
| 3 | Q2 | 7:21 | 0.89 | 0.9083 | +1.93pp | 0.76pp |
| 4 | Q2 | 3:33 | 0.93 | 0.9486 | +1.66pp | 0.30pp |
| 5 | Q2 | 1:08 | 0.92 | 0.9263 | +0.43pp | 0.60pp |
| 6 | Q3 | 9:42 | 0.83 | 0.8584 | +3.14pp | 0.58pp |
| 7 | Q3 | 5:08 | 0.94 | 0.9330 | -0.90pp | 0.47pp |
| 8 | Q4 | 10:47 | 1.00 | 0.9900 | -0.60pp | 0.17pp |
| 9 | Q4 | 7:00 | 1.00 | 0.9900 | -0.80pp | 0.04pp |
| 10 | Q4 | 3:41 | 0.99 | 0.9888 | -0.22pp | 0.24pp |

**Summary:** mean Δ at timeout calls: +0.67pp vs overall mean Δ: +0.59pp. Timeouts sit near the overall delta.


## §7 — Key observations

- |Δ| narrowed from Q1 (1.76pp) to Q4 (0.67pp) — consistent with convergence hypothesis.
- Near-perfect convergence in final 2 minutes (|Δ| = 0.90pp).
- No Strategy 3 zone activation — consistent with |spread| > 6 exclusion filter.

