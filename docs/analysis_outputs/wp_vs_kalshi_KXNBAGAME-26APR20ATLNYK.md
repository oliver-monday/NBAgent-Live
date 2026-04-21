# WP vs Kalshi Paired Analysis: ATL @ NYK

**Date:** 2026-04-21  |  **ESPN ID:** 401869387  |  **Kalshi:** KXNBAGAME-26APR20ATLNYK
**Final:** NYK 106 – ATL 107
**Pre-game spread:** -5.5  |  **Favorite:** NYK
**Pre-game ESPN WP (fav):** 71.9%
**Pre-game Kalshi (fav):** $0.6700
**Pre-game delta:** -4.9pp
**Kalshi trades:** 78,427 trades, 26,128,580 contracts
**Strategy 3 filter:** competitive (|spread| ≤ 6)  (|spread| 5.5)

## §1 — Pre-game snapshot

- Pre-game ESPN WP (fav): **71.9%** vs Kalshi (fav): **$0.6700**. Δ = **-4.9pp** (below ESPN).
- Compression pattern reference: prior work shows Kalshi +10-14pp above ESPN at low fav WP and −10-14pp below at high fav WP. This game's pre-game delta (-4.9pp) is in the expected direction and within the ±10-17pp compression band.


## §2 — Delta across game time

**Overall:** mean Δ = -3.67pp, median -4.50pp, std 4.04pp, min -17.28pp, max +26.92pp, n=315.
**Direction:** Δ > 0 in 9% of buckets, Δ < 0 in 91%.

### By quarter

| Period | Mean Δ | Median Δ | Std Δ | N obs |
|---|---:|---:|---:|---:|
| Q1 | -5.43pp | -5.67pp | 1.07pp | 77 |
| Q2 | -4.68pp | -4.80pp | 1.83pp | 101 |
| Q3 | -3.13pp | -2.94pp | 1.54pp | 66 |
| Q4 | -0.83pp | -1.63pp | 7.16pp | 71 |
| All | -3.67pp | -4.50pp | 4.04pp | 315 |

### By WP zone (ESPN fav WP)

| WP zone | Mean Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|
| 0.00-0.20 | -2.21pp | 8 | 50% |
| 0.20-0.40 | -0.75pp | 7 | 29% |
| 0.40-0.60 | +1.22pp | 8 | 75% |
| 0.60-0.80 | -3.86pp | 71 | 6% |
| 0.80-1.00 | -3.93pp | 221 | 5% |


## §3 — Convergence analysis

| Time remaining | Mean |Δ| | Median |Δ| | N obs |
|---|---:|---:|---:|
| > 36 min | 5.43pp | 5.69pp | 70 |
| 24-36 min | 4.69pp | 4.89pp | 76 |
| 12-24 min | 3.76pp | 4.23pp | 92 |
| 6-12 min | 2.37pp | 2.53pp | 38 |
| 3-6 min | 3.98pp | 4.04pp | 13 |
| 1-3 min | 7.16pp | 4.12pp | 12 |
| 0-1 min | 10.95pp | 9.47pp | 12 |

**Regression:** |Δ| ~ elapsed_sec → slope -0.000002/s, R² = 0.004, p = 0.258. Negative slope = convergence.

**Final 2 minutes:** mean |Δ| = 10.25pp (n=19).


## §4 — Scoring play response comparison

Coverage: **114/114** (100%) scoring plays have Kalshi prices in both the ±5s-before and +3-to-15s-after windows.

### By score value

| Score value | n | Mean wp_delta (pp) | Mean Kalshi Δ (pp) | Mean reaction diff (pp) |
|---|---:|---:|---:|---:|
| 1-pt | 35 | +0.24pp | -0.00pp | +0.24pp |
| 2-pt | 59 | -0.67pp | -0.90pp | +0.23pp |
| 3-pt | 20 | +1.58pp | +1.20pp | +0.38pp |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean kalshi Δ | Mean diff |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 2 | +4.10pp | +5.50pp | -1.40pp |
| 0.20-0.40 | 1 | +20.60pp | +15.00pp | +5.60pp |
| 0.40-0.60 | 3 | -9.53pp | -13.67pp | +4.13pp |
| 0.60-0.80 | 34 | +0.38pp | +0.12pp | +0.26pp |
| 0.80-1.00 | 74 | -0.17pp | -0.24pp | +0.07pp |


## §5 — Strategy 3 zone mapping

Strategy 3 zone active for **240s** (2.5% of 30s buckets; zone = fav Kalshi VWAP in [$0.35, $0.65]).
While in-zone, fav ESPN WP ranged [0.34, 0.60] with mean 0.46.
ESPN WP entered the zone **30s before** Kalshi VWAP.


## §6 — Timeout windows

Detected **11** timeout events.

| # | Period | Clock | Fav WP | Fav Kalshi | Δ | ±60s std |
|---|---:|---:|---:|---:|---:|---:|
| 1 | Q1 | 7:05 | 0.77 | 0.7327 | -3.53pp | 1.18pp |
| 2 | Q1 | 5:33 | 0.86 | 0.7957 | -6.43pp | 0.24pp |
| 3 | Q2 | 8:37 | 0.78 | 0.7000 | -7.60pp | 1.63pp |
| 4 | Q2 | 2:58 | 0.73 | 0.6673 | -6.37pp | 2.08pp |
| 5 | Q3 | 7:27 | 0.92 | 0.9041 | -1.29pp | 0.87pp |
| 6 | Q3 | 3:21 | 0.93 | 0.8776 | -5.44pp | 1.36pp |
| 7 | Q4 | 10:30 | 0.93 | 0.8922 | -3.78pp | 0.80pp |
| 8 | Q4 | 5:26 | 0.88 | 0.9076 | +3.06pp | 1.40pp |
| 9 | Q4 | 2:43 | 0.70 | 0.7040 | +0.20pp | 3.08pp |
| 10 | Q4 | 10.2 | 0.21 | 0.0462 | -16.78pp | 4.66pp |
| 11 | Q4 | 7.1 | 0.10 | 0.1057 | +0.67pp | 4.18pp |

**Summary:** mean Δ at timeout calls: -4.30pp vs overall mean Δ: -3.67pp. Timeouts sit near the overall delta.


## §7 — Key observations

- |Δ| narrowed from Q1 (5.43pp) to Q4 (0.83pp) — consistent with convergence hypothesis.
- Final-2-min |Δ| = 10.25pp — no tight convergence at end.
- Strategy 3 zone active for 240s (2.5% of in-game time).

