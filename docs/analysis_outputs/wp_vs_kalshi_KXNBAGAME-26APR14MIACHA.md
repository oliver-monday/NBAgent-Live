# WP vs Kalshi Paired Analysis: MIA @ CHA

**Date:** 2026-04-14  |  **ESPN ID:** 401866755  |  **Kalshi:** KXNBAGAME-26APR14MIACHA
**Final:** CHA 127 – MIA 126
**Pre-game spread:** -5.5  |  **Favorite:** CHA
**Pre-game ESPN WP (fav):** 72.6%
**Pre-game Kalshi (fav):** $0.6900
**Pre-game delta:** -3.6pp
**Kalshi trades:** 126,407 trades, 32,748,536 contracts
**Strategy 3 filter:** competitive (|spread| ≤ 6)  (|spread| 5.5)

## §1 — Pre-game snapshot

- Pre-game ESPN WP (fav): **72.6%** vs Kalshi (fav): **$0.6900**. Δ = **-3.6pp** (below ESPN).
- Compression pattern reference: prior work shows Kalshi +10-14pp above ESPN at low fav WP and −10-14pp below at high fav WP. This game's pre-game delta (-3.6pp) is in the expected direction and within the ±10-17pp compression band.


## §2 — Delta across game time

**Overall:** mean Δ = +1.59pp, median +1.16pp, std 7.14pp, min -14.71pp, max +67.63pp, n=328.
**Direction:** Δ > 0 in 57% of buckets, Δ < 0 in 43%.

### By quarter

| Period | Mean Δ | Median Δ | Std Δ | N obs |
|---|---:|---:|---:|---:|
| Q1 | -5.33pp | -5.75pp | 2.21pp | 56 |
| Q2 | -0.68pp | -0.43pp | 2.70pp | 63 |
| Q3 | +3.66pp | +3.12pp | 3.04pp | 82 |
| Q4 | +1.98pp | +1.10pp | 7.14pp | 84 |
| OT1 | +9.21pp | +7.57pp | 10.89pp | 43 |
| All | +1.59pp | +1.16pp | 7.14pp | 328 |

### By WP zone (ESPN fav WP)

| WP zone | Mean Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|
| 0.00-0.20 | +0.64pp | 23 | 61% |
| 0.20-0.40 | +10.54pp | 28 | 89% |
| 0.40-0.60 | +6.54pp | 46 | 89% |
| 0.60-0.80 | -0.44pp | 161 | 52% |
| 0.80-1.00 | -0.25pp | 70 | 31% |


## §3 — Convergence analysis

| Time remaining | Mean |Δ| | Median |Δ| | N obs |
|---|---:|---:|---:|
| > 36 min | 4.41pp | 4.41pp | 88 |
| 24-36 min | 2.84pp | 2.92pp | 84 |
| 12-24 min | 4.69pp | 2.75pp | 67 |
| 6-12 min | 7.78pp | 7.69pp | 22 |
| 3-6 min | 8.43pp | 8.27pp | 33 |
| 1-3 min | 9.22pp | 7.11pp | 8 |
| 0-1 min | 10.99pp | 7.69pp | 20 |

**Regression:** |Δ| ~ elapsed_sec → slope 0.000016/s, R² = 0.086, p = 6.85e-08. Positive slope = divergence with game time.

**Final 2 minutes:** mean |Δ| = 9.04pp (n=32).


## §4 — Scoring play response comparison

Coverage: **120/120** (100%) scoring plays have Kalshi prices in both the ±5s-before and +3-to-15s-after windows.

### By score value

| Score value | n | Mean wp_delta (pp) | Mean Kalshi Δ (pp) | Mean reaction diff (pp) |
|---|---:|---:|---:|---:|
| 1-pt | 21 | -0.81pp | -1.10pp | +0.28pp |
| 2-pt | 65 | +0.96pp | -0.49pp | +1.45pp |
| 3-pt | 34 | +0.81pp | -0.38pp | +1.19pp |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean kalshi Δ | Mean diff |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 8 | +9.25pp | +0.50pp | +8.75pp |
| 0.20-0.40 | 7 | +5.01pp | -1.57pp | +6.59pp |
| 0.40-0.60 | 24 | -0.40pp | -1.17pp | +0.76pp |
| 0.60-0.80 | 65 | -0.14pp | -0.31pp | +0.17pp |
| 0.80-1.00 | 16 | -1.11pp | -0.81pp | -0.29pp |


## §5 — Strategy 3 zone mapping

Strategy 3 zone active for **3,180s** (32.3% of 30s buckets; zone = fav Kalshi VWAP in [$0.35, $0.65]).
While in-zone, fav ESPN WP ranged [0.23, 0.67] with mean 0.51.
Kalshi VWAP entered the zone **2250s before** ESPN WP.


## §6 — Timeout windows

Detected **18** timeout events.

| # | Period | Clock | Fav WP | Fav Kalshi | Δ | ±60s std |
|---|---:|---:|---:|---:|---:|---:|
| 1 | Q1 | 8:52 | 0.74 | 0.6738 | -6.42pp | 2.98pp |
| 2 | Q1 | 4:50 | 0.79 | 0.7233 | -6.47pp | 0.74pp |
| 3 | Q2 | 10:58 | 0.78 | 0.7562 | -2.68pp | 1.96pp |
| 4 | Q2 | 5:30 | 0.65 | 0.6533 | +0.73pp | 0.40pp |
| 5 | Q3 | 8:25 | 0.61 | 0.6793 | +7.13pp | 1.67pp |
| 6 | Q3 | 4:30 | 0.46 | 0.5115 | +5.45pp | 2.44pp |
| 7 | Q3 | 1:28 | 0.80 | 0.7829 | -1.71pp | 1.78pp |
| 8 | Q4 | 10:00 | 0.89 | 0.8942 | +0.32pp | 0.29pp |
| 9 | Q4 | 7:25 | 0.37 | 0.4671 | +10.11pp | 0.44pp |
| 10 | Q4 | 5:08 | 0.45 | 0.4632 | +1.42pp | 5.30pp |
| 11 | Q4 | 28.0 | 0.12 | 0.0706 | -5.04pp | 1.56pp |
| 12 | Q4 | 18.6 | 0.25 | 0.1597 | -9.03pp | 5.62pp |
| 13 | Q4 | 12.9 | 0.10 | 0.1157 | +1.37pp | 3.37pp |
| 14 | Q4 | 10.8 | 0.52 | 0.3769 | -14.71pp | 1.42pp |
| 15 | Q5 | 1:33 | 0.85 | 0.9235 | +6.85pp | 9.17pp |
| 16 | Q5 | 48.1 | 0.88 | 0.9376 | +6.16pp | 1.91pp |
| 17 | Q5 | 26.0 | 0.91 | 0.9777 | +6.47pp | 2.67pp |
| 18 | Q5 | 8.7 | 0.23 | 0.3564 | +12.74pp | 4.11pp |

**Summary:** mean Δ at timeout calls: +0.71pp vs overall mean Δ: +1.59pp. Timeouts sit near the overall delta.


## §7 — Key observations

- |Δ| narrowed from Q1 (5.33pp) to Q4 (1.98pp) — consistent with convergence hypothesis.
- Final-2-min |Δ| = 9.04pp — no tight convergence at end.
- Strategy 3 zone active for 3,180s (32.3% of in-game time).

