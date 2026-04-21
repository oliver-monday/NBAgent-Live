# WP vs Kalshi Paired Analysis: MIN @ DEN

**Date:** 2026-04-21  |  **ESPN ID:** 401869395  |  **Kalshi:** KXNBAGAME-26APR20MINDEN
**Final:** DEN 114 – MIN 119
**Pre-game spread:** -7.5  |  **Favorite:** DEN
**Pre-game ESPN WP (fav):** 71.6%
**Pre-game Kalshi (fav):** $0.7200
**Pre-game delta:** +0.4pp
**Kalshi trades:** 120,663 trades, 35,152,436 contracts
**Strategy 3 filter:** excluded from Strategy 3 universe  (|spread| 7.5)

## §1 — Pre-game snapshot

- Pre-game ESPN WP (fav): **71.6%** vs Kalshi (fav): **$0.7200**. Δ = **+0.4pp** (above ESPN).
- Compression pattern reference: prior work shows Kalshi +10-14pp above ESPN at low fav WP and −10-14pp below at high fav WP. This game's pre-game delta is near zero — consistent with a moderate favorite (compression shrinks as WP → 0.5).


## §2 — Delta across game time

**Overall:** mean Δ = -0.35pp, median -1.28pp, std 4.99pp, min -28.41pp, max +17.90pp, n=313.
**Direction:** Δ > 0 in 44% of buckets, Δ < 0 in 56%.

### By quarter

| Period | Mean Δ | Median Δ | Std Δ | N obs |
|---|---:|---:|---:|---:|
| Q1 | -2.44pp | -3.49pp | 2.44pp | 68 |
| Q2 | +0.38pp | +2.22pp | 3.93pp | 99 |
| Q3 | -0.46pp | -1.60pp | 3.73pp | 73 |
| Q4 | +0.74pp | +1.55pp | 7.76pp | 73 |
| All | -0.35pp | -1.28pp | 4.99pp | 313 |

### By WP zone (ESPN fav WP)

| WP zone | Mean Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|
| 0.00-0.20 | +1.94pp | 8 | 75% |
| 0.20-0.40 | +4.48pp | 15 | 73% |
| 0.40-0.60 | +1.98pp | 36 | 78% |
| 0.60-0.80 | +0.79pp | 146 | 61% |
| 0.80-1.00 | -3.50pp | 108 | 3% |


## §3 — Convergence analysis

| Time remaining | Mean |Δ| | Median |Δ| | N obs |
|---|---:|---:|---:|
| > 36 min | 3.19pp | 3.63pp | 63 |
| 24-36 min | 3.52pp | 3.07pp | 102 |
| 12-24 min | 3.36pp | 3.04pp | 68 |
| 6-12 min | 2.96pp | 1.63pp | 37 |
| 3-6 min | 5.75pp | 3.38pp | 23 |
| 1-3 min | 6.49pp | 5.45pp | 6 |
| 0-1 min | 10.27pp | 8.32pp | 12 |

**Regression:** |Δ| ~ elapsed_sec → slope 0.000010/s, R² = 0.057, p = 1.9e-05. Positive slope = divergence with game time.

**Final 2 minutes:** mean |Δ| = 8.84pp (n=17).


## §4 — Scoring play response comparison

Coverage: **123/123** (100%) scoring plays have Kalshi prices in both the ±5s-before and +3-to-15s-after windows.

### By score value

| Score value | n | Mean wp_delta (pp) | Mean Kalshi Δ (pp) | Mean reaction diff (pp) |
|---|---:|---:|---:|---:|
| 1-pt | 42 | +0.71pp | -0.02pp | +0.73pp |
| 2-pt | 52 | -0.82pp | -0.02pp | -0.80pp |
| 3-pt | 29 | +0.06pp | +0.41pp | -0.36pp |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean kalshi Δ | Mean diff |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 5 | +4.28pp | +2.80pp | +1.48pp |
| 0.20-0.40 | 3 | +4.27pp | +1.00pp | +3.27pp |
| 0.40-0.60 | 14 | -1.22pp | -0.50pp | -0.72pp |
| 0.60-0.80 | 57 | -0.04pp | +0.33pp | -0.38pp |
| 0.80-1.00 | 44 | -0.59pp | -0.43pp | -0.16pp |


## §5 — Strategy 3 zone mapping

Strategy 3 zone active for **1,500s** (16.0% of 30s buckets; zone = fav Kalshi VWAP in [$0.35, $0.65]).
While in-zone, fav ESPN WP ranged [0.28, 0.68] with mean 0.50.
ESPN WP entered the zone **3360s before** Kalshi VWAP.


## §6 — Timeout windows

Detected **12** timeout events.

| # | Period | Clock | Fav WP | Fav Kalshi | Δ | ±60s std |
|---|---:|---:|---:|---:|---:|---:|
| 1 | Q1 | 6:32 | 0.80 | 0.8009 | +0.09pp | 2.24pp |
| 2 | Q1 | 2:53 | 0.93 | 0.8835 | -4.25pp | 1.21pp |
| 3 | Q2 | 8:30 | 0.88 | 0.8416 | -3.64pp | 0.53pp |
| 4 | Q2 | 6:35 | 0.76 | 0.7669 | +0.79pp | 1.77pp |
| 5 | Q2 | 2:50 | 0.53 | 0.5869 | +5.79pp | 0.28pp |
| 6 | Q3 | 6:21 | 0.52 | 0.5954 | +7.84pp | 0.74pp |
| 7 | Q3 | 2:41 | 0.82 | 0.7915 | -3.05pp | 0.27pp |
| 8 | Q4 | 8:52 | 0.67 | 0.6630 | -0.30pp | 0.83pp |
| 9 | Q4 | 5:54 | 0.66 | 0.7289 | +6.99pp | 1.41pp |
| 10 | Q4 | 4:06 | 0.51 | 0.5156 | +0.16pp | 5.02pp |
| 11 | Q4 | 3:36 | 0.49 | 0.4264 | -6.36pp | 3.75pp |
| 12 | Q4 | 19.1 | 0.44 | 0.1773 | -26.67pp | 7.69pp |

**Summary:** mean Δ at timeout calls: -1.88pp vs overall mean Δ: -0.35pp. Timeouts sit near the overall delta.


## §7 — Key observations

- |Δ| narrowed from Q1 (2.44pp) to Q4 (0.74pp) — consistent with convergence hypothesis.
- Final-2-min |Δ| = 8.84pp — no tight convergence at end.
- Strategy 3 zone active for 1,500s (16.0% of in-game time).

