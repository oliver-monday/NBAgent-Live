# WP vs Kalshi Paired Analysis: TOR @ CLE

**Date:** 2026-04-20  |  **ESPN ID:** 401869369  |  **Kalshi:** KXNBAGAME-26APR20TORCLE
**Final:** CLE 115 – TOR 105
**Pre-game spread:** -9.5  |  **Favorite:** CLE
**Pre-game ESPN WP (fav):** 64.5%
**Pre-game Kalshi (fav):** $0.7900
**Pre-game delta:** +14.5pp
**Kalshi trades:** 33,396 trades, 11,866,133 contracts
**Strategy 3 filter:** excluded from Strategy 3 universe  (|spread| 9.5)

## §1 — Pre-game snapshot

- Pre-game ESPN WP (fav): **64.5%** vs Kalshi (fav): **$0.7900**. Δ = **+14.5pp** (above ESPN).
- Compression pattern reference: prior work shows Kalshi +10-14pp above ESPN at low fav WP and −10-14pp below at high fav WP. ⚠ **Direction reversed.** At fav WP 0.65 the compression pattern predicts Kalshi BELOW ESPN, but here Kalshi is above ESPN by 14.5pp. Possible retail-flow signature on a non-competitive line.


## §2 — Delta across game time

**Overall:** mean Δ = +4.53pp, median +4.79pp, std 3.47pp, min -1.00pp, max +13.97pp, n=289.
**Direction:** Δ > 0 in 85% of buckets, Δ < 0 in 15%.

### By quarter

| Period | Mean Δ | Median Δ | Std Δ | N obs |
|---|---:|---:|---:|---:|
| Q1 | +8.14pp | +7.89pp | 1.85pp | 48 |
| Q2 | +6.43pp | +6.73pp | 2.84pp | 64 |
| Q3 | +4.19pp | +4.27pp | 2.51pp | 99 |
| Q4 | +1.17pp | -0.18pp | 2.33pp | 78 |
| All | +4.53pp | +4.79pp | 3.47pp | 289 |

### By WP zone (ESPN fav WP)

| WP zone | Mean Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|
| 0.00-0.20 | — | 0 | — |
| 0.20-0.40 | — | 0 | — |
| 0.40-0.60 | — | 0 | — |
| 0.60-0.80 | +7.97pp | 108 | 100% |
| 0.80-1.00 | +2.47pp | 181 | 76% |


## §3 — Convergence analysis

| Time remaining | Mean |Δ| | Median |Δ| | N obs |
|---|---:|---:|---:|
| > 36 min | 8.15pp | 7.89pp | 47 |
| 24-36 min | 6.45pp | 6.74pp | 65 |
| 12-24 min | 4.20pp | 4.24pp | 98 |
| 6-12 min | 3.24pp | 2.91pp | 36 |
| 3-6 min | 0.84pp | 0.52pp | 21 |
| 1-3 min | 0.78pp | 0.80pp | 8 |
| 0-1 min | 0.85pp | 0.90pp | 11 |

**Regression:** |Δ| ~ elapsed_sec → slope -0.000032/s, R² = 0.606, p = 6.2e-60. Negative slope = convergence.

**Final 2 minutes:** mean |Δ| = 0.86pp (n=20).


## §4 — Scoring play response comparison

Coverage: **111/114** (97%) scoring plays have Kalshi prices in both the ±5s-before and +3-to-15s-after windows.

### By score value

| Score value | n | Mean wp_delta (pp) | Mean Kalshi Δ (pp) | Mean reaction diff (pp) |
|---|---:|---:|---:|---:|
| 1-pt | 27 | +0.33pp | +0.11pp | +0.21pp |
| 2-pt | 64 | -0.12pp | +0.05pp | -0.17pp |
| 3-pt | 20 | +1.17pp | +0.65pp | +0.52pp |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean kalshi Δ | Mean diff |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 0 | — | — | — |
| 0.20-0.40 | 0 | — | — | — |
| 0.40-0.60 | 0 | — | — | — |
| 0.60-0.80 | 34 | +0.65pp | +0.38pp | +0.27pp |
| 0.80-1.00 | 77 | +0.03pp | +0.08pp | -0.05pp |


## §5 — Strategy 3 zone mapping

_Game never entered Strategy 3 zone_ (fav Kalshi VWAP never in [$0.35, $0.65]). Expected for games with |spread| > 6.


## §6 — Timeout windows

Detected **11** timeout events.

| # | Period | Clock | Fav WP | Fav Kalshi | Δ | ±60s std |
|---|---:|---:|---:|---:|---:|---:|
| 1 | Q1 | 6:54 | 0.79 | 0.8641 | +7.51pp | 0.50pp |
| 2 | Q1 | 4:02 | 0.80 | 0.8791 | +8.41pp | 0.92pp |
| 3 | Q2 | 8:54 | 0.80 | 0.8746 | +7.46pp | 1.40pp |
| 4 | Q2 | 1:52 | 0.85 | 0.8643 | +1.33pp | 2.74pp |
| 5 | Q3 | 10:03 | 0.88 | 0.9141 | +3.61pp | 0.60pp |
| 6 | Q3 | 7:37 | 0.92 | 0.9415 | +2.25pp | 0.27pp |
| 7 | Q3 | 2:04 | 0.96 | 0.9584 | -0.36pp | 2.43pp |
| 8 | Q4 | 6:46 | 0.92 | 0.9194 | -0.26pp | 1.41pp |
| 9 | Q4 | 3:53 | 0.99 | 0.9898 | -0.52pp | 0.93pp |
| 10 | Q4 | 3:17 | 1.00 | 0.9900 | -0.70pp | 0.12pp |
| 11 | Q4 | 27.6 | 1.00 | 0.9900 | -0.80pp | 0.04pp |

**Summary:** mean Δ at timeout calls: +2.54pp vs overall mean Δ: +4.53pp. Timeouts sit near the overall delta.


## §7 — Key observations

- Pre-game gap of +14.5pp (Kalshi above ESPN). Consistent with compression band.
- |Δ| narrowed from Q1 (8.14pp) to Q4 (1.17pp) — consistent with convergence hypothesis.
- Near-perfect convergence in final 2 minutes (|Δ| = 0.86pp).
- No Strategy 3 zone activation — consistent with |spread| > 6 exclusion filter.

