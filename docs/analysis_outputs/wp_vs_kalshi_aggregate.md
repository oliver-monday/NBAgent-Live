# WP vs Kalshi Paired Analysis — Cross-Game Aggregation

_Generated: 2026-04-21T00:06:52.474010+00:00_

## §A — Sample summary

- Games analyzed: **168**
- Date range: 2026-02-20 to 2026-04-15
- |Spread| distribution: mean 3.41, median 3.50, min 1.00, max 6.00
- Total 30s bins (in-game): 46,981 across 168 games
- Total scoring plays: 20,095 across 168 games

## §B — Delta by WP zone (pooled)

| WP zone | Mean Δ ± 95% CI | Median Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|---:|
| 0.00-0.20 | +4.61pp ±0.12pp | +3.37pp | 7,332 | 90% |
| 0.20-0.40 | +8.30pp ±0.22pp | +8.67pp | 6,130 | 87% |
| 0.40-0.60 | +4.09pp ±0.16pp | +4.72pp | 9,422 | 76% |
| 0.60-0.80 | -1.76pp ±0.12pp | -1.58pp | 9,799 | 38% |
| 0.80-1.00 | -2.73pp ±0.06pp | -1.53pp | 14,298 | 12% |

## §C — Convergence regression

| Subset | Slope | R² | p | n |
|---|---:|---:|---:|---:|
| Pooled | -0.000020/s | 0.090 | 0 | 46,981 |
| |spread| ≤ 3 | -0.000025/s | 0.118 | 0 | 20,998 |
| |spread| 3-6 | -0.000016/s | 0.071 | 0 | 25,089 |
| |spread| > 6 | — | — | — | 0 |

### Mean |Δ| by time remaining (pooled)

| Time remaining | Mean |Δ| | Median |Δ| | N |
|---|---:|---:|---:|
| > 36 min | 7.70pp | 6.45pp | 9,144 |
| 24-36 min | 6.61pp | 5.79pp | 10,845 |
| 12-24 min | 5.21pp | 4.09pp | 14,866 |
| 6-12 min | 3.65pp | 2.16pp | 5,972 |
| 3-6 min | 2.90pp | 0.96pp | 2,722 |
| 1-3 min | 2.47pp | 0.90pp | 1,631 |
| 0-1 min | 3.97pp | 0.90pp | 1,335 |

## §D — Scoring play reaction ratios (pooled)

Coverage: 18,918 / 20,095 plays.

### By score value

| Score value | n | Mean wp_delta | Mean Kalshi Δ | Ratio |
|---|---:|---:|---:|---:|
| 1-pt | 5,685 | -0.01pp | +0.01pp | -2.06× |
| 2-pt | 9,146 | +0.04pp | +0.02pp | 1.76× |
| 3-pt | 4,087 | -0.09pp | -0.04pp | 2.03× |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean Kalshi Δ | Ratio |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 2,739 | +0.20pp | -0.02pp | -8.02× |
| 0.20-0.40 | 2,478 | +0.19pp | -0.02pp | -8.06× |
| 0.40-0.60 | 4,231 | +0.01pp | -0.01pp | -0.76× |
| 0.60-0.80 | 4,362 | -0.14pp | +0.02pp | -6.14× |
| 0.80-1.00 | 5,108 | -0.11pp | +0.02pp | -4.33× |

## §E — Strategy 3 zone statistics

- Competitive games (|spread| ≤ 6): **165**; 156/165 (95%) entered S3 zone.
- Among those: mean zone time 2,991s (35.3% of in-game bins).
- Zone time ~ |spread| regression: slope -285.1 s/spread-pt, R² = 0.050, p = 0.00381, n = 165.

## §F — Delta stability at timeouts (pooled)

- Timeout windows: n = 7,175
- Non-timeout windows: n = 39,806
- Mean |Δ| in timeout windows: 5.37pp
- Mean |Δ| outside timeout windows: 5.54pp
- Mann-Whitney U test: U = 137140093, p = 8.49e-08.

## §G — Per-game summary table

| Ticker | Date | Spread | R² | Mean Δ | Final 2m |Δ| | Zone time % | n in-game |
|---|---|---:|---:|---:|---:|---:|---:|
| KXNBAGAME-26APR18HOULAL | — | — | 0.463 | +5.57pp | 0.83pp | 54.7% | 309 |
| KXNBAGAME-26APR19ORLDET | — | — | 0.000 | +6.65pp | 0.45pp | 50.8% | 299 |
| KXNBAGAME-26APR19PORSAS | — | — | 0.077 | +0.59pp | 0.90pp | 0.0% | 286 |
| KXNBAGAME-26FEB20CLECHA | 2026-02-20 | +5.5 | 0.005 | +2.39pp | 2.46pp | 22.4% | 281 |
| KXNBAGAME-26FEB20DENPOR | 2026-02-20 | -1.0 | 0.645 | +3.39pp | 0.91pp | 7.4% | 269 |
| KXNBAGAME-26FEB20INDWAS | 2026-02-20 | -1.0 | 0.882 | +14.29pp | 0.83pp | 49.4% | 259 |
| KXNBAGAME-26FEB20MIAATL | 2026-02-20 | +3.5 | 0.293 | -2.97pp | 0.92pp | 10.5% | 247 |
| KXNBAGAME-26FEB20MILNOP | 2026-02-20 | -4.0 | 0.002 | +3.24pp | 0.92pp | 67.1% | 255 |
| KXNBAGAME-26FEB20UTAMEM | 2026-02-20 | -2.5 | 0.595 | -6.21pp | 0.83pp | 43.5% | 269 |
| KXNBAGAME-26FEB21HOUNYK | 2026-02-21 | -4.0 | 0.089 | +1.89pp | 6.11pp | 28.5% | 302 |
| KXNBAGAME-26FEB21ORLPHX | 2026-02-21 | -3.5 | 0.223 | +7.17pp | 10.76pp | 51.2% | 344 |
| KXNBAGAME-26FEB21PHINOP | 2026-02-21 | +3.5 | 0.001 | +2.91pp | 0.92pp | 22.3% | 300 |
| KXNBAGAME-26FEB22ORLLAC | 2026-02-22 | -4.0 | 0.010 | +3.27pp | 6.57pp | 84.9% | 291 |
| KXNBAGAME-26FEB22PORPHX | 2026-02-22 | +3.5 | 0.669 | +3.14pp | 0.92pp | 34.4% | 247 |
| KXNBAGAME-26FEB23SACMEM | 2026-02-23 | -3.0 | 0.442 | -5.94pp | 1.07pp | 71.6% | 268 |
| KXNBAGAME-26FEB23SASDET | 2026-02-23 | -1.0 | 0.174 | -0.54pp | 0.80pp | 57.3% | 321 |
| KXNBAGAME-26FEB24BOSPHX | 2026-02-24 | +5.5 | 0.424 | +2.20pp | 0.93pp | 31.1% | 241 |
| KXNBAGAME-26FEB24DALBKN | 2026-02-24 | +1.5 | 0.625 | -9.25pp | 1.06pp | 22.6% | 270 |
| KXNBAGAME-26FEB24GSWNOP | 2026-02-24 | +1.0 | 0.030 | +2.50pp | 3.39pp | 33.2% | 289 |
| KXNBAGAME-26FEB24MIAMIL | 2026-02-24 | +6.0 | 0.045 | +4.29pp | 1.41pp | 44.4% | 268 |
| KXNBAGAME-26FEB24NYKCLE | 2026-02-24 | -4.0 | 0.151 | -0.15pp | 0.94pp | 6.6% | 304 |
| KXNBAGAME-26FEB24OKCTOR | 2026-02-24 | -2.0 | 0.088 | +5.11pp | 1.76pp | 32.5% | 280 |
| KXNBAGAME-26FEB24ORLLAL | 2026-02-24 | -5.0 | 0.109 | +4.45pp | 10.13pp | 15.8% | 278 |
| KXNBAGAME-26FEB25BOSDEN | 2026-02-25 | -3.5 | 0.011 | -0.12pp | 0.92pp | 75.0% | 276 |
| KXNBAGAME-26FEB25CLEMIL | 2026-02-25 | +3.5 | 0.110 | -6.06pp | 8.28pp | 65.4% | 257 |
| KXNBAGAME-26FEB25GSWMEM | 2026-02-25 | +4.0 | 0.594 | +1.79pp | 0.92pp | 7.8% | 255 |
| KXNBAGAME-26FEB25SASTOR | 2026-02-25 | +6.0 | 0.294 | +3.50pp | 8.49pp | 40.5% | 294 |
| KXNBAGAME-26FEB26HOUORL | 2026-02-26 | +2.5 | 0.012 | +2.75pp | 2.29pp | 46.9% | 286 |
| KXNBAGAME-26FEB26LALPHX | 2026-02-26 | +6.0 | 0.188 | +10.83pp | 4.85pp | 39.2% | 286 |
| KXNBAGAME-26FEB26MIAPHI | 2026-02-26 | -2.0 | 0.041 | -0.93pp | 2.92pp | 32.5% | 265 |
| KXNBAGAME-26FEB26PORCHI | 2026-02-26 | +4.5 | 0.410 | +2.32pp | 1.62pp | 47.3% | 277 |
| KXNBAGAME-26FEB27MEMDAL | 2026-02-27 | -4.0 | 0.759 | +5.89pp | 0.92pp | 21.1% | 261 |
| KXNBAGAME-26FEB28LALGSW | 2026-02-28 | +4.0 | 0.402 | +0.84pp | 0.92pp | 1.2% | 259 |
| KXNBAGAME-26MAR01DETORL | 2026-03-01 | +5.0 | 0.168 | +5.09pp | 0.73pp | 66.9% | 275 |
| KXNBAGAME-26MAR01MEMIND | 2026-03-01 | -1.0 | 0.031 | +4.19pp | 0.93pp | 51.0% | 259 |
| KXNBAGAME-26MAR01MILCHI | 2026-03-01 | +2.5 | 0.239 | +0.88pp | 0.92pp | 39.1% | 258 |
| KXNBAGAME-26MAR01MINDEN | 2026-03-01 | -3.0 | 0.088 | +5.80pp | 0.80pp | 50.7% | 282 |
| KXNBAGAME-26MAR01PORATL | 2026-03-01 | -6.0 | 0.627 | -2.30pp | 0.93pp | 0.7% | 270 |
| KXNBAGAME-26MAR02BOSMIL | 2026-03-02 | +2.5 | 0.778 | -5.14pp | 0.93pp | 19.3% | 244 |
| KXNBAGAME-26MAR02LACGSW | 2026-03-02 | +1.0 | 0.000 | +4.15pp | 0.92pp | 28.7% | 286 |
| KXNBAGAME-26MAR03DETCLE | 2026-03-03 | +2.5 | 0.189 | +7.21pp | 3.30pp | 66.0% | 282 |
| KXNBAGAME-26MAR03NYKTOR | 2026-03-03 | +2.5 | 0.116 | -4.35pp | 0.90pp | 28.3% | 272 |
| KXNBAGAME-26MAR04ATLMIL | 2026-03-04 | -1.0 | 0.012 | +4.03pp | 0.92pp | 31.1% | 267 |
| KXNBAGAME-26MAR04OKCNYK | 2026-03-04 | +4.0 | 0.023 | -0.68pp | 5.16pp | 19.4% | 299 |
| KXNBAGAME-26MAR05DETSAS | 2026-03-05 | -3.5 | 0.184 | -1.67pp | 0.80pp | 3.8% | 293 |
| KXNBAGAME-26MAR05LALDEN | 2026-03-05 | -5.5 | 0.533 | -7.21pp | 2.39pp | 3.1% | 286 |
| KXNBAGAME-26MAR05NOPSAC | 2026-03-05 | +5.5 | 0.614 | +3.78pp | 0.90pp | 29.1% | 268 |
| KXNBAGAME-26MAR05TORMIN | 2026-03-05 | -5.5 | 0.238 | +0.68pp | 0.89pp | 45.1% | 277 |
| KXNBAGAME-26MAR05UTAWAS | 2026-03-05 | -2.5 | 0.548 | +7.69pp | 0.80pp | 25.2% | 266 |
| KXNBAGAME-26MAR06NYKDEN | 2026-03-06 | +1.5 | 0.153 | -2.93pp | 0.91pp | 38.8% | 276 |
| KXNBAGAME-26MAR07LACMEM | 2026-03-07 | +5.5 | 0.523 | +15.48pp | 3.99pp | 35.2% | 298 |
| KXNBAGAME-26MAR08BOSCLE | 2026-03-08 | +1.5 | 0.627 | +13.23pp | 0.85pp | 0.0% | 287 |
| KXNBAGAME-26MAR08CHAPHX | 2026-03-08 | +4.5 | 0.050 | +3.50pp | 0.92pp | 47.0% | 281 |
| KXNBAGAME-26MAR08CHISAC | 2026-03-08 | +2.5 | 0.053 | +3.98pp | 0.84pp | 28.5% | 281 |
| KXNBAGAME-26MAR08DETMIA | 2026-03-08 | +1.5 | 0.693 | -8.70pp | 0.96pp | 0.0% | 217 |
| KXNBAGAME-26MAR08HOUSAS | 2026-03-08 | -5.5 | 0.248 | +0.26pp | 0.92pp | 3.7% | 296 |
| KXNBAGAME-26MAR08NYKLAL | 2026-03-08 | +2.5 | 0.018 | -12.78pp | 0.78pp | 25.2% | 306 |
| KXNBAGAME-26MAR08ORLMIL | 2026-03-08 | +3.5 | 0.320 | -0.68pp | 0.91pp | 0.0% | 266 |
| KXNBAGAME-26MAR09GSWUTA | 2026-03-09 | +5.5 | 0.240 | +5.81pp | 6.52pp | 58.8% | 284 |
| KXNBAGAME-26MAR09MEMBKN | 2026-03-09 | +1.5 | 0.478 | -4.81pp | 0.92pp | 34.5% | 264 |
| KXNBAGAME-26MAR09NYKLAC | 2026-03-09 | +2.5 | 0.256 | +7.97pp | 1.28pp | 38.0% | 303 |
| KXNBAGAME-26MAR10BOSSAS | 2026-03-10 | -3.5 | 0.025 | +4.33pp | 1.15pp | 47.4% | 285 |
| KXNBAGAME-26MAR10CHAPOR | 2026-03-10 | +2.5 | 0.018 | +1.44pp | 9.61pp | 35.2% | 281 |
| KXNBAGAME-26MAR10INDSAC | 2026-03-10 | -3.5 | 0.017 | +7.24pp | 2.00pp | 29.0% | 300 |
| KXNBAGAME-26MAR10MEMPHI | 2026-03-10 | -2.5 | 0.504 | +10.44pp | 0.68pp | 58.4% | 298 |
| KXNBAGAME-26MAR10MINLAL | 2026-03-10 | +2.5 | 0.002 | +0.77pp | 0.93pp | 44.4% | 286 |
| KXNBAGAME-26MAR10PHXMIL | 2026-03-10 | +1.5 | 0.036 | -0.49pp | 0.92pp | 71.3% | 261 |
| KXNBAGAME-26MAR10TORHOU | 2026-03-10 | -5.5 | 0.010 | -0.38pp | 0.92pp | 24.8% | 266 |
| KXNBAGAME-26MAR11CLEORL | 2026-03-11 | +3.5 | 0.011 | +1.38pp | 3.20pp | 71.2% | 306 |
| KXNBAGAME-26MAR11MINLAC | 2026-03-11 | -1.5 | 0.725 | -8.19pp | 0.96pp | 18.7% | 283 |
| KXNBAGAME-26MAR11TORNOP | 2026-03-11 | +2.5 | 0.011 | +7.83pp | 0.93pp | 58.7% | 271 |
| KXNBAGAME-26MAR12DALMEM | 2026-03-12 | +4.5 | 0.066 | +1.92pp | 0.91pp | 2.3% | 257 |
| KXNBAGAME-26MAR12DENSAS | 2026-03-12 | -5.5 | 0.397 | -7.05pp | 2.41pp | 20.0% | 295 |
| KXNBAGAME-26MAR13MINGSW | 2026-03-13 | +5.5 | 0.628 | +2.53pp | 0.89pp | 0.0% | 288 |
| KXNBAGAME-26MAR13PHXTOR | 2026-03-13 | -4.5 | 0.012 | +8.96pp | 4.19pp | 63.5% | 285 |
| KXNBAGAME-26MAR14CHASAS | 2026-03-14 | -5.5 | 0.234 | +1.12pp | 0.93pp | 0.0% | 280 |
| KXNBAGAME-26MAR14DENLAL | 2026-03-14 | +2.5 | 0.103 | +5.81pp | 7.25pp | 40.1% | 339 |
| KXNBAGAME-26MAR14ORLMIA | 2026-03-14 | -3.5 | 0.308 | +5.07pp | 6.96pp | 19.1% | 304 |
| KXNBAGAME-26MAR15DETTOR | 2026-03-15 | +3.5 | 0.001 | -1.27pp | 2.10pp | 47.7% | 285 |
| KXNBAGAME-26MAR15UTASAC | 2026-03-15 | -2.5 | 0.102 | +4.01pp | 4.53pp | 39.3% | 257 |
| KXNBAGAME-26MAR16LALHOU | 2026-03-16 | -2.5 | 0.007 | -6.90pp | 2.72pp | 81.2% | 282 |
| KXNBAGAME-26MAR16ORLATL | 2026-03-16 | -2.5 | 0.484 | -4.00pp | 0.82pp | 9.4% | 297 |
| KXNBAGAME-26MAR17MIACHA | 2026-03-17 | -3.5 | 0.229 | +1.41pp | 0.92pp | 30.8% | 286 |
| KXNBAGAME-26MAR17PHXMIN | 2026-03-17 | -3.5 | 0.100 | -2.50pp | 0.78pp | 65.3% | 285 |
| KXNBAGAME-26MAR18LACNOP | 2026-03-18 | -2.5 | 0.686 | +5.01pp | 0.94pp | 30.7% | 254 |
| KXNBAGAME-26MAR18LALHOU | 2026-03-18 | -2.5 | 0.019 | +1.96pp | 2.15pp | 56.6% | 295 |
| KXNBAGAME-26MAR19LACNOP | 2026-03-19 | -1.5 | 0.632 | +10.84pp | 1.69pp | 51.4% | 276 |
| KXNBAGAME-26MAR19LALMIA | 2026-03-19 | -3.5 | 0.001 | +0.11pp | 1.70pp | 14.3% | 293 |
| KXNBAGAME-26MAR19MILUTA | 2026-03-19 | +5.5 | 0.291 | +6.18pp | 0.92pp | 34.5% | 258 |
| KXNBAGAME-26MAR19ORLCHA | 2026-03-19 | -5.5 | 0.388 | -0.73pp | 0.93pp | 14.1% | 305 |
| KXNBAGAME-26MAR19PHISAC | 2026-03-19 | +2.5 | 0.640 | -5.71pp | 0.92pp | 17.2% | 273 |
| KXNBAGAME-26MAR20ATLHOU | 2026-03-20 | -3.5 | 0.330 | -0.74pp | 0.93pp | 15.0% | 267 |
| KXNBAGAME-26MAR20GSWDET | 2026-03-20 | -5.5 | 0.227 | -0.72pp | 0.91pp | 22.5% | 271 |
| KXNBAGAME-26MAR20PORMIN | 2026-03-20 | -2.5 | 0.078 | -7.29pp | 8.00pp | 55.1% | 285 |
| KXNBAGAME-26MAR21CLENOP | 2026-03-21 | +4.5 | 0.383 | -2.37pp | 2.78pp | 28.5% | 274 |
| KXNBAGAME-26MAR21LALORL | 2026-03-21 | +3.5 | 0.108 | +6.88pp | 8.17pp | 63.0% | 300 |
| KXNBAGAME-26MAR21MIAHOU | 2026-03-21 | -1.5 | 0.027 | +0.58pp | 13.01pp | 68.1% | 273 |
| KXNBAGAME-26MAR21PHIUTA | 2026-03-21 | +5.5 | 0.010 | +2.04pp | 1.45pp | 36.9% | 271 |
| KXNBAGAME-26MAR22TORPHX | 2026-03-22 | +2.5 | 0.842 | +8.76pp | 0.92pp | 24.7% | 255 |
| KXNBAGAME-26MAR23GSWDAL | 2026-03-23 | +1.5 | 0.330 | +6.99pp | 2.09pp | 51.0% | 343 |
| KXNBAGAME-26MAR23LALDET | 2026-03-23 | +1.5 | 0.223 | +14.09pp | 5.72pp | 64.0% | 286 |
| KXNBAGAME-26MAR23SASMIA | 2026-03-23 | +4.5 | 0.260 | -1.81pp | 0.92pp | 7.6% | 277 |
| KXNBAGAME-26MAR24DENPHX | 2026-03-24 | +5.5 | 0.211 | +5.72pp | 7.97pp | 35.8% | 299 |
| KXNBAGAME-26MAR25ATLDET | 2026-03-25 | -2.5 | 0.050 | -0.39pp | 10.52pp | 65.0% | 317 |
| KXNBAGAME-26MAR25CHIPHI | 2026-03-25 | -5.5 | 0.239 | -1.68pp | 0.92pp | 0.0% | 272 |
| KXNBAGAME-26MAR25HOUMIN | 2026-03-25 | +1.5 | 0.639 | +10.68pp | 4.44pp | 67.8% | 339 |
| KXNBAGAME-26MAR25MIACLE | 2026-03-25 | -2.5 | 0.100 | +1.30pp | 0.93pp | 36.9% | 271 |
| KXNBAGAME-26MAR25OKCBOS | 2026-03-25 | +2.5 | 0.404 | -3.04pp | 1.31pp | 45.6% | 281 |
| KXNBAGAME-26MAR25TORLAC | 2026-03-25 | -4.5 | 0.377 | -3.49pp | 0.95pp | 3.4% | 267 |
| KXNBAGAME-26MAR25WASUTA | 2026-03-25 | -4.5 | 0.442 | +3.53pp | 0.92pp | 18.1% | 260 |
| KXNBAGAME-26MAR26NOPDET | 2026-03-26 | -4.5 | 0.431 | -5.83pp | 0.93pp | 18.5% | 260 |
| KXNBAGAME-26MAR26NYKCHA | 2026-03-26 | -1.5 | 0.042 | -1.17pp | 0.76pp | 28.9% | 273 |
| KXNBAGAME-26MAR27ATLBOS | 2026-03-27 | -5.5 | 0.667 | +8.71pp | 1.03pp | 58.7% | 269 |
| KXNBAGAME-26MAR27MIACLE | 2026-03-27 | -5.5 | 0.628 | -2.57pp | 0.92pp | 0.0% | 297 |
| KXNBAGAME-26MAR28CHIMEM | 2026-03-28 | +3.5 | 0.005 | +9.08pp | 5.21pp | 55.8% | 303 |
| KXNBAGAME-26MAR28DETMIN | 2026-03-28 | -2.5 | 0.241 | +0.07pp | 0.92pp | 18.8% | 271 |
| KXNBAGAME-26MAR29BOSCHA | 2026-03-29 | +1.5 | 0.155 | -4.22pp | 0.92pp | 21.5% | 247 |
| KXNBAGAME-26MAR29HOUNOP | 2026-03-29 | +5.5 | 0.506 | +0.96pp | 0.92pp | 6.7% | 270 |
| KXNBAGAME-26MAR29ORLTOR | 2026-03-29 | -1.5 | 0.375 | -2.49pp | 0.95pp | 15.3% | 268 |
| KXNBAGAME-26MAR29SACBKN | 2026-03-29 | +1.5 | 0.566 | +3.42pp | 0.92pp | 3.8% | 262 |
| KXNBAGAME-26MAR30BOSATL | 2026-03-30 | -1.5 | 0.071 | +0.23pp | 0.90pp | 55.0% | 260 |
| KXNBAGAME-26MAR30PHIMIA | 2026-03-30 | +2.5 | 0.061 | +5.16pp | 0.92pp | 63.7% | 295 |
| KXNBAGAME-26MAR31CLELAL | 2026-03-31 | -2.5 | 0.648 | +1.91pp | 0.92pp | 30.0% | 267 |
| KXNBAGAME-26MAR31DALMIL | 2026-03-31 | +1.5 | 0.614 | +6.53pp | 0.92pp | 28.1% | 260 |
| KXNBAGAME-26MAR31NYKHOU | 2026-03-31 | -1.5 | 0.523 | -3.46pp | 0.92pp | 8.2% | 269 |
| KXNBAGAME-26MAR31PHXORL | 2026-03-31 | -2.5 | 0.072 | -2.76pp | 2.26pp | 29.5% | 319 |
| KXNBAGAME-26MAR31PORLAC | 2026-03-31 | -5.5 | 0.036 | +3.40pp | 0.83pp | 29.5% | 275 |
| KXNBAGAME-26MAR31TORDET | 2026-03-31 | -2.5 | 0.663 | -6.73pp | 0.82pp | 5.2% | 287 |
| KXNBAGAME-26APR01ATLORL | 2026-04-01 | +4.5 | 0.135 | -2.57pp | 0.92pp | 28.7% | 286 |
| KXNBAGAME-26APR01BOSMIA | 2026-04-01 | +4.5 | 0.371 | -1.16pp | 0.93pp | 12.8% | 265 |
| KXNBAGAME-26APR01INDCHI | 2026-04-01 | -4.5 | 0.515 | +6.31pp | 0.92pp | 31.0% | 252 |
| KXNBAGAME-26APR02MINDET | 2026-04-02 | -3.5 | 0.015 | +0.26pp | 2.99pp | 43.8% | 304 |
| KXNBAGAME-26APR02PHXCHA | 2026-04-02 | -5.5 | 0.181 | -0.40pp | 0.93pp | 33.8% | 260 |
| KXNBAGAME-26APR02SASLAC | 2026-04-02 | +3.5 | 0.720 | -7.26pp | 0.95pp | 18.6% | 280 |
| KXNBAGAME-26APR03MINPHI | 2026-04-03 | -2.5 | 0.477 | +7.37pp | 1.21pp | 62.9% | 272 |
| KXNBAGAME-26APR03NOPSAC | 2026-04-03 | +5.5 | 0.113 | -0.92pp | 5.26pp | 6.6% | 289 |
| KXNBAGAME-26APR04DETPHI | 2026-04-04 | +3.5 | 0.872 | -7.00pp | 0.93pp | 18.5% | 259 |
| KXNBAGAME-26APR04SASDEN | 2026-04-04 | +2.5 | 0.105 | -5.09pp | 3.10pp | 26.5% | 343 |
| KXNBAGAME-26APR05CHAMIN | 2026-04-05 | +2.5 | 0.025 | +2.66pp | 0.93pp | 36.3% | 267 |
| KXNBAGAME-26APR05HOUGSW | 2026-04-05 | +3.5 | 0.185 | +1.89pp | 8.15pp | 41.2% | 291 |
| KXNBAGAME-26APR05LALDAL | 2026-04-05 | +1.5 | 0.360 | -2.26pp | 1.36pp | 24.2% | 298 |
| KXNBAGAME-26APR05MEMMIL | 2026-04-05 | -5.5 | 0.451 | +7.06pp | 0.91pp | 5.7% | 263 |
| KXNBAGAME-26APR05ORLNOP | 2026-04-05 | +4.5 | 0.045 | +13.26pp | 3.99pp | 43.2% | 296 |
| KXNBAGAME-26APR05WASBKN | 2026-04-05 | -3.5 | 0.326 | -4.38pp | 2.59pp | 19.9% | 291 |
| KXNBAGAME-26APR06DETORL | 2026-04-06 | +2.5 | 0.727 | -7.22pp | 0.90pp | 33.4% | 293 |
| KXNBAGAME-26APR06NYKATL | 2026-04-06 | -1.5 | 0.119 | +3.71pp | 4.63pp | 76.2% | 290 |
| KXNBAGAME-26APR07CHABOS | 2026-04-07 | -4.5 | 0.414 | +11.38pp | 0.85pp | 74.0% | 269 |
| KXNBAGAME-26APR07HOUPHX | 2026-04-07 | -1.5 | 0.418 | -4.63pp | 0.85pp | 53.1% | 305 |
| KXNBAGAME-26APR07MIATOR | 2026-04-07 | -1.5 | 0.197 | -1.09pp | 0.93pp | 27.0% | 267 |
| KXNBAGAME-26APR07MILBKN | 2026-04-07 | +2.5 | 0.000 | +1.29pp | 4.71pp | 51.1% | 262 |
| KXNBAGAME-26APR08ATLCLE | 2026-04-08 | -1.5 | 0.000 | +2.85pp | 3.92pp | 38.7% | 282 |
| KXNBAGAME-26APR08PORSAS | 2026-04-08 | -3.5 | 0.908 | -11.14pp | 0.60pp | 17.7% | 271 |
| KXNBAGAME-26APR09BOSNYK | 2026-04-09 | -4.5 | 0.001 | +4.58pp | 6.79pp | 72.7% | 267 |
| KXNBAGAME-26APR09INDBKN | 2026-04-09 | +2.5 | 0.440 | -1.42pp | 0.93pp | 8.5% | 248 |
| KXNBAGAME-26APR09LALGSW | 2026-04-09 | -4.5 | 0.387 | +4.78pp | 0.91pp | 47.1% | 259 |
| KXNBAGAME-26APR09MIATOR | 2026-04-09 | -4.5 | 0.364 | +0.20pp | 0.96pp | 14.1% | 284 |
| KXNBAGAME-26APR09PHIHOU | 2026-04-09 | -3.5 | 0.223 | -1.41pp | 1.40pp | 0.0% | 268 |
| KXNBAGAME-26APR10DETCHA | 2026-04-10 | -5.5 | 0.319 | +11.12pp | 0.93pp | 71.2% | 278 |
| KXNBAGAME-26APR10LACPOR | 2026-04-10 | -1.5 | 0.127 | -1.96pp | 0.92pp | 46.5% | 273 |
| KXNBAGAME-26APR10MEMUTA | 2026-04-10 | -3.5 | 0.273 | -1.09pp | 0.92pp | 22.2% | 225 |
| KXNBAGAME-26APR10PHXLAL | 2026-04-10 | +2.5 | 0.578 | +3.71pp | 0.92pp | 21.0% | 281 |
| KXNBAGAME-26APR12ATLMIA | 2026-04-12 | -4.5 | 0.755 | +9.06pp | 0.94pp | 0.0% | 245 |
| KXNBAGAME-26APR12NOPMIN | 2026-04-12 | -5.5 | 0.802 | -5.72pp | 0.78pp | 4.8% | 290 |
| KXNBAGAME-26APR12PHXOKC | 2026-04-12 | -5.5 | 0.442 | +2.35pp | 0.93pp | 9.0% | 233 |
| KXNBAGAME-26APR14MIACHA | 2026-04-14 | -5.5 | 0.086 | +1.59pp | 9.04pp | 32.3% | 328 |
| KXNBAGAME-26APR14PORPHX | 2026-04-14 | -3.5 | 0.001 | +0.97pp | 6.25pp | 52.1% | 305 |
| KXNBAGAME-26APR15GSWLAC | 2026-04-15 | -5.5 | 0.035 | -3.83pp | 8.06pp | 8.9% | 305 |
| KXNBAGAME-26APR15ORLPHI | 2026-04-15 | -2.5 | 0.052 | -4.36pp | 1.01pp | 61.3% | 310 |

