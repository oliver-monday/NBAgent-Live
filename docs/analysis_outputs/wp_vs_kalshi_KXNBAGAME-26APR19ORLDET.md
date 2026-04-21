# WP vs Kalshi Paired Analysis: ORL @ DET

**Date:** 2026-04-19  |  **ESPN ID:** 401869193  |  **Kalshi:** KXNBAGAME-26APR19ORLDET
**Final:** DET 101 – ORL 112
**Pre-game spread:** -8.5  |  **Favorite:** DET
**Pre-game ESPN WP (fav):** 79.4%
**Pre-game Kalshi (fav):** $0.7900
**Pre-game delta:** -0.4pp
**Kalshi trades:** 94,149 trades, 31,175,267 contracts
**Strategy 3 filter:** excluded from Strategy 3 universe  (|spread| 8.5)

## §1 — Pre-game snapshot

- Pre-game ESPN WP (fav): **79.4%** vs Kalshi (fav): **$0.7900**. Δ = **-0.4pp** (below ESPN).
- Compression pattern reference: prior work shows Kalshi +10-14pp above ESPN at low fav WP and −10-14pp below at high fav WP. This game's pre-game delta is near zero — consistent with a moderate favorite (compression shrinks as WP → 0.5).


## §2 — Delta across game time

**Overall:** mean Δ = +6.65pp, median +5.71pp, std 5.10pp, min -4.89pp, max +20.95pp, n=299.
**Direction:** Δ > 0 in 90% of buckets, Δ < 0 in 10%.

### By quarter

| Period | Mean Δ | Median Δ | Std Δ | N obs |
|---|---:|---:|---:|---:|
| Q1 | +5.26pp | +5.42pp | 3.86pp | 63 |
| Q2 | +5.81pp | +5.34pp | 2.67pp | 99 |
| Q3 | +12.13pp | +12.50pp | 4.50pp | 71 |
| Q4 | +3.36pp | +1.75pp | 5.02pp | 66 |
| All | +6.65pp | +5.71pp | 5.10pp | 299 |

### By WP zone (ESPN fav WP)

| WP zone | Mean Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|
| 0.00-0.20 | +2.99pp | 48 | 62% |
| 0.20-0.40 | +12.14pp | 60 | 100% |
| 0.40-0.60 | +7.25pp | 119 | 99% |
| 0.60-0.80 | +3.54pp | 72 | 85% |
| 0.80-1.00 | — | 0 | — |


## §3 — Convergence analysis

| Time remaining | Mean |Δ| | Median |Δ| | N obs |
|---|---:|---:|---:|
| > 36 min | 5.48pp | 5.32pp | 57 |
| 24-36 min | 6.38pp | 7.11pp | 74 |
| 12-24 min | 9.80pp | 7.54pp | 96 |
| 6-12 min | 8.73pp | 9.90pp | 34 |
| 3-6 min | 2.55pp | 2.55pp | 21 |
| 1-3 min | 0.30pp | 0.30pp | 13 |
| 0-1 min | 0.55pp | 0.55pp | 2 |

**Regression:** |Δ| ~ elapsed_sec → slope 0.000001/s, R² = 0.000, p = 0.722. Positive slope = divergence with game time.

**Final 2 minutes:** mean |Δ| = 0.45pp (n=13).


## §4 — Scoring play response comparison

Coverage: **118/118** (100%) scoring plays have Kalshi prices in both the ±5s-before and +3-to-15s-after windows.

### By score value

| Score value | n | Mean wp_delta (pp) | Mean Kalshi Δ (pp) | Mean reaction diff (pp) |
|---|---:|---:|---:|---:|
| 1-pt | 43 | -0.20pp | +0.21pp | -0.40pp |
| 2-pt | 55 | -0.96pp | -0.75pp | -0.22pp |
| 3-pt | 20 | -0.18pp | -0.15pp | -0.03pp |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean kalshi Δ | Mean diff |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 14 | -0.84pp | -0.71pp | -0.13pp |
| 0.20-0.40 | 26 | -0.40pp | +0.23pp | -0.63pp |
| 0.40-0.60 | 43 | -0.59pp | -0.49pp | -0.10pp |
| 0.60-0.80 | 35 | -0.49pp | -0.29pp | -0.21pp |
| 0.80-1.00 | 0 | — | — | — |


## §5 — Strategy 3 zone mapping

Strategy 3 zone active for **4,560s** (50.8% of 30s buckets; zone = fav Kalshi VWAP in [$0.35, $0.65]).
While in-zone, fav ESPN WP ranged [0.18, 0.64] with mean 0.46.
ESPN WP entered the zone **240s before** Kalshi VWAP.


## §6 — Timeout windows

Detected **9** timeout events.

| # | Period | Clock | Fav WP | Fav Kalshi | Δ | ±60s std |
|---|---:|---:|---:|---:|---:|---:|
| 1 | Q1 | 8:27 | 0.62 | 0.6527 | +3.67pp | 2.59pp |
| 2 | Q1 | 3:06 | 0.53 | 0.6232 | +9.42pp | 2.57pp |
| 3 | Q2 | 6:16 | 0.56 | 0.6290 | +7.30pp | 0.78pp |
| 4 | Q2 | 3:34 | 0.63 | 0.6713 | +3.93pp | 0.10pp |
| 5 | Q3 | 9:35 | 0.32 | 0.4779 | +15.99pp | 1.61pp |
| 6 | Q3 | 7:45 | 0.57 | 0.6888 | +11.38pp | 2.40pp |
| 7 | Q3 | 3:43 | 0.32 | 0.4137 | +9.77pp | 2.52pp |
| 8 | Q4 | 8:15 | 0.38 | 0.3873 | +0.33pp | 4.95pp |
| 9 | Q4 | 3:45 | 0.19 | 0.1534 | -3.36pp | 3.95pp |

**Summary:** mean Δ at timeout calls: +6.49pp vs overall mean Δ: +6.65pp. Timeouts sit near the overall delta.


## §7 — Key observations

- |Δ| narrowed from Q1 (5.26pp) to Q4 (3.36pp) — consistent with convergence hypothesis.
- Near-perfect convergence in final 2 minutes (|Δ| = 0.45pp).
- Strategy 3 zone active for 4,560s (50.8% of in-game time).

