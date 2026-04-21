# WP vs Kalshi Paired Analysis: HOU @ LAL

**Date:** 2026-04-19  |  **ESPN ID:** 401869190  |  **Kalshi:** KXNBAGAME-26APR18HOULAL
**Final:** LAL 107 – HOU 98
**Pre-game spread:** +2.5  |  **Favorite:** HOU
**Pre-game ESPN WP (fav):** 49.7%
**Pre-game Kalshi (fav):** $0.5700
**Pre-game delta:** +7.3pp
**Kalshi trades:** 93,838 trades, 29,207,909 contracts
**Strategy 3 filter:** competitive (|spread| ≤ 6)  (|spread| 2.5)

## §1 — Pre-game snapshot

- Pre-game ESPN WP (fav): **49.7%** vs Kalshi (fav): **$0.5700**. Δ = **+7.3pp** (above ESPN).
- Compression pattern reference: prior work shows Kalshi +10-14pp above ESPN at low fav WP and −10-14pp below at high fav WP. This game's pre-game delta (+7.3pp) is in the expected direction and within the ±10-17pp compression band.


## §2 — Delta across game time

**Overall:** mean Δ = +5.57pp, median +5.60pp, std 3.46pp, min -3.56pp, max +14.78pp, n=309.
**Direction:** Δ > 0 in 96% of buckets, Δ < 0 in 4%.

### By quarter

| Period | Mean Δ | Median Δ | Std Δ | N obs |
|---|---:|---:|---:|---:|
| Q1 | +8.83pp | +9.37pp | 2.50pp | 62 |
| Q2 | +6.41pp | +5.55pp | 2.06pp | 93 |
| Q3 | +5.64pp | +6.22pp | 2.68pp | 80 |
| Q4 | +1.70pp | +0.83pp | 2.59pp | 74 |
| All | +5.57pp | +5.60pp | 3.46pp | 309 |

### By WP zone (ESPN fav WP)

| WP zone | Mean Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|
| 0.00-0.20 | +3.60pp | 118 | 94% |
| 0.20-0.40 | +7.46pp | 118 | 100% |
| 0.40-0.60 | +5.70pp | 73 | 95% |
| 0.60-0.80 | — | 0 | — |
| 0.80-1.00 | — | 0 | — |


## §3 — Convergence analysis

| Time remaining | Mean |Δ| | Median |Δ| | N obs |
|---|---:|---:|---:|
| > 36 min | 9.02pp | 9.78pp | 55 |
| 24-36 min | 7.05pp | 7.40pp | 68 |
| 12-24 min | 5.58pp | 5.34pp | 104 |
| 6-12 min | 3.85pp | 3.16pp | 39 |
| 3-6 min | 0.64pp | 0.71pp | 19 |
| 1-3 min | 0.60pp | 0.60pp | 11 |
| 0-1 min | 0.85pp | 0.90pp | 6 |

**Regression:** |Δ| ~ elapsed_sec → slope -0.000029/s, R² = 0.463, p = 2.31e-43. Negative slope = convergence.

**Final 2 minutes:** mean |Δ| = 0.83pp (n=18).


## §4 — Scoring play response comparison

Coverage: **109/109** (100%) scoring plays have Kalshi prices in both the ±5s-before and +3-to-15s-after windows.

### By score value

| Score value | n | Mean wp_delta (pp) | Mean Kalshi Δ (pp) | Mean reaction diff (pp) |
|---|---:|---:|---:|---:|
| 1-pt | 34 | -0.01pp | -0.18pp | +0.17pp |
| 2-pt | 54 | -0.63pp | -0.28pp | -0.35pp |
| 3-pt | 21 | +0.52pp | +0.00pp | +0.52pp |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean kalshi Δ | Mean diff |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 46 | +0.15pp | -0.02pp | +0.17pp |
| 0.20-0.40 | 41 | -0.02pp | -0.27pp | +0.25pp |
| 0.40-0.60 | 22 | -1.32pp | -0.41pp | -0.91pp |
| 0.60-0.80 | 0 | — | — | — |
| 0.80-1.00 | 0 | — | — | — |


## §5 — Strategy 3 zone mapping

Strategy 3 zone active for **5,070s** (54.7% of 30s buckets; zone = fav Kalshi VWAP in [$0.35, $0.65]).
While in-zone, fav ESPN WP ranged [0.24, 0.56] with mean 0.38.
ESPN WP and Kalshi VWAP entered the zone in the same 30s bucket.


## §6 — Timeout windows

Detected **11** timeout events.

| # | Period | Clock | Fav WP | Fav Kalshi | Δ | ±60s std |
|---|---:|---:|---:|---:|---:|---:|
| 1 | Q1 | 6:11 | 0.36 | 0.4932 | +13.12pp | 1.81pp |
| 2 | Q1 | 2:52 | 0.41 | 0.4945 | +8.45pp | 0.81pp |
| 3 | Q2 | 6:22 | 0.28 | 0.3618 | +8.18pp | 1.61pp |
| 4 | Q2 | 4:35 | 0.25 | 0.3570 | +10.50pp | 1.23pp |
| 5 | Q3 | 6:09 | 0.36 | 0.3842 | +1.92pp | 2.10pp |
| 6 | Q3 | 4:02 | 0.18 | 0.2576 | +7.56pp | 0.73pp |
| 7 | Q3 | 1:08 | 0.13 | 0.1827 | +5.37pp | 0.47pp |
| 8 | Q4 | 7:57 | 0.04 | 0.0430 | +0.40pp | 1.20pp |
| 9 | Q4 | 5:50 | 0.01 | 0.0248 | +1.28pp | 0.30pp |
| 10 | Q4 | 3:22 | 0.01 | 0.0164 | +0.84pp | 0.71pp |
| 11 | Q4 | 15.8 | 0.00 | 0.0100 | +0.90pp | 0.13pp |

**Summary:** mean Δ at timeout calls: +5.32pp vs overall mean Δ: +5.57pp. Timeouts sit near the overall delta.


## §7 — Key observations

- Pre-game gap of +7.3pp (Kalshi above ESPN). Consistent with compression band.
- |Δ| narrowed from Q1 (8.83pp) to Q4 (1.70pp) — consistent with convergence hypothesis.
- Near-perfect convergence in final 2 minutes (|Δ| = 0.83pp).
- Strategy 3 zone active for 142,200s (32.3% of captured game time).

