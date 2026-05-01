# WP vs Kalshi Paired Analysis — Cross-Game Aggregation

_Generated: 2026-04-28T20:19:52.776230+00:00_

## §A — Sample summary

- Games analyzed: **420**
- Total 30s bins (in-game): 116,174 across 420 games
- Total scoring plays: 50,512 across 420 games

## §B — Delta by WP zone (pooled)

| WP zone | Mean Δ ± 95% CI | Median Δ | N obs | Δ > 0 % |
|---|---:|---:|---:|---:|
| 0.00-0.20 | +5.63pp ±0.13pp | +4.15pp | 9,908 | 91% |
| 0.20-0.40 | +11.40pp ±0.20pp | +11.05pp | 9,776 | 90% |
| 0.40-0.60 | +8.07pp ±0.14pp | +7.92pp | 16,256 | 84% |
| 0.60-0.80 | +2.93pp ±0.10pp | +2.55pp | 23,631 | 64% |
| 0.80-1.00 | -0.34pp ±0.03pp | -0.70pp | 56,603 | 36% |

## §C — Convergence regression

| Subset | Slope | R² | p | n |
|---|---:|---:|---:|---:|
| Pooled | -0.000020/s | 0.065 | 0 | 116,174 |
| |spread| ≤ 3 | — | — | — | 0 |
| |spread| 3-6 | — | — | — | 0 |
| |spread| > 6 | — | — | — | 0 |

### Mean |Δ| by time remaining (pooled)

| Time remaining | Mean |Δ| | Median |Δ| | N |
|---|---:|---:|---:|
| > 36 min | 7.54pp | 5.56pp | 22,555 |
| 24-36 min | 6.66pp | 4.62pp | 26,958 |
| 12-24 min | 5.00pp | 2.72pp | 36,789 |
| 6-12 min | 3.54pp | 1.22pp | 14,813 |
| 3-6 min | 3.03pp | 0.90pp | 6,724 |
| 1-3 min | 2.35pp | 0.90pp | 4,014 |
| 0-1 min | 3.88pp | 0.90pp | 3,159 |

## §D — Scoring play reaction ratios (pooled)

Coverage: 44,356 / 50,512 plays.

### By score value

| Score value | n | Mean wp_delta | Mean Kalshi Δ | Ratio |
|---|---:|---:|---:|---:|
| 1-pt | 13,182 | -0.00pp | +0.01pp | -0.19× |
| 2-pt | 21,379 | +0.07pp | +0.04pp | 1.81× |
| 3-pt | 9,795 | +0.01pp | +0.06pp | 0.17× |

### By WP zone at time of play

| WP zone | n | Mean wp_delta | Mean Kalshi Δ | Ratio |
|---|---:|---:|---:|---:|
| 0.00-0.20 | 3,787 | +0.27pp | +0.03pp | 10.35× |
| 0.20-0.40 | 3,918 | +0.28pp | +0.01pp | 22.64× |
| 0.40-0.60 | 7,175 | +0.09pp | +0.04pp | 2.49× |
| 0.60-0.80 | 10,587 | -0.00pp | +0.04pp | -0.07× |
| 0.80-1.00 | 18,889 | -0.07pp | +0.03pp | -1.96× |

## §E — Strategy 3 zone statistics


## §F — Delta stability at timeouts (pooled)

- Timeout windows: n = 17,635
- Non-timeout windows: n = 98,539
- Mean |Δ| in timeout windows: 5.34pp
- Mean |Δ| outside timeout windows: 5.43pp
- Mann-Whitney U test: U = 855025238, p = 0.000738.

## §G — Per-game summary table

| Ticker | Date | Spread | R² | Mean Δ | Final 2m |Δ| | Zone time % | n in-game |
|---|---|---:|---:|---:|---:|---:|---:|
| KXNBAGAME-26APR01ATLORL | — | — | 0.135 | -2.57pp | 0.92pp | 28.7% | 286 |
| KXNBAGAME-26APR01BOSMIA | — | — | 0.371 | -1.16pp | 0.93pp | 12.8% | 265 |
| KXNBAGAME-26APR01DENUTA | — | — | 0.009 | +0.64pp | 0.91pp | 0.0% | 268 |
| KXNBAGAME-26APR01INDCHI | — | — | 0.515 | +6.31pp | 0.92pp | 31.0% | 252 |
| KXNBAGAME-26APR01MILHOU | — | — | 0.574 | +4.48pp | 2.22pp | 0.0% | 258 |
| KXNBAGAME-26APR01NYKMEM | — | — | 0.055 | +0.78pp | 0.92pp | 0.0% | 276 |
| KXNBAGAME-26APR01PHIWAS | — | — | 0.026 | +0.98pp | 0.93pp | 0.0% | 248 |
| KXNBAGAME-26APR01SACTOR | — | — | 0.072 | +13.27pp | 7.75pp | 31.9% | 285 |
| KXNBAGAME-26APR01SASGSW | — | — | 0.387 | +1.42pp | 0.94pp | 0.0% | 290 |
| KXNBAGAME-26APR02CLEGSW | — | — | 0.002 | +7.35pp | 1.71pp | 6.4% | 282 |
| KXNBAGAME-26APR02LALOKC | — | — | 0.544 | -1.65pp | 0.91pp | 0.0% | 262 |
| KXNBAGAME-26APR02MINDET | — | — | 0.015 | +0.26pp | 2.99pp | 43.8% | 304 |
| KXNBAGAME-26APR02NOPPOR | — | — | 0.078 | +8.34pp | 0.87pp | 41.2% | 272 |
| KXNBAGAME-26APR02PHXCHA | — | — | 0.181 | -0.40pp | 0.93pp | 33.8% | 260 |
| KXNBAGAME-26APR02SASLAC | — | — | 0.720 | -7.26pp | 0.95pp | 18.6% | 280 |
| KXNBAGAME-26APR03ATLBKN | — | — | 0.406 | +1.52pp | 0.94pp | 0.0% | 262 |
| KXNBAGAME-26APR03BOSMIL | — | — | 0.222 | +0.41pp | 0.94pp | 0.0% | 255 |
| KXNBAGAME-26APR03CHINYK | — | — | 0.085 | -0.37pp | 0.92pp | 0.0% | 271 |
| KXNBAGAME-26APR03INDCHA | — | — | 0.145 | +0.13pp | 0.93pp | 0.0% | 251 |
| KXNBAGAME-26APR03MINPHI | — | — | 0.477 | +7.37pp | 1.21pp | 62.9% | 272 |
| KXNBAGAME-26APR03NOPSAC | — | — | 0.113 | -0.92pp | 5.26pp | 6.6% | 289 |
| KXNBAGAME-26APR03ORLDAL | — | — | 0.449 | +2.48pp | 0.89pp | 0.0% | 304 |
| KXNBAGAME-26APR03TORMEM | — | — | 0.552 | +4.03pp | 0.92pp | 0.0% | 293 |
| KXNBAGAME-26APR03UTAHOU | — | — | 0.368 | +0.48pp | 0.92pp | 0.0% | 259 |
| KXNBAGAME-26APR04DETPHI | — | — | 0.872 | -7.00pp | 0.93pp | 18.5% | 259 |
| KXNBAGAME-26APR04SASDEN | — | — | 0.105 | -5.09pp | 3.10pp | 26.5% | 343 |
| KXNBAGAME-26APR04WASMIA | — | — | 0.294 | +0.52pp | 0.91pp | 0.0% | 263 |
| KXNBAGAME-26APR05CHAMIN | — | — | 0.025 | +2.66pp | 0.93pp | 36.3% | 267 |
| KXNBAGAME-26APR05HOUGSW | — | — | 0.185 | +1.89pp | 8.15pp | 41.2% | 291 |
| KXNBAGAME-26APR05INDCLE | — | — | 0.299 | +10.40pp | 0.93pp | 0.0% | 263 |
| KXNBAGAME-26APR05LACSAC | — | — | 0.386 | +0.98pp | 0.94pp | 0.0% | 262 |
| KXNBAGAME-26APR05LALDAL | — | — | 0.360 | -2.26pp | 1.36pp | 24.2% | 298 |
| KXNBAGAME-26APR05MEMMIL | — | — | 0.451 | +7.06pp | 0.91pp | 5.7% | 263 |
| KXNBAGAME-26APR05ORLNOP | — | — | 0.045 | +13.26pp | 3.99pp | 43.2% | 296 |
| KXNBAGAME-26APR05PHXCHI | — | — | 0.544 | +7.07pp | 0.67pp | 0.0% | 274 |
| KXNBAGAME-26APR05TORBOS | — | — | 0.235 | +5.71pp | 0.93pp | 1.9% | 259 |
| KXNBAGAME-26APR05UTAOKC | — | — | 0.011 | -0.35pp | 0.93pp | 0.0% | 248 |
| KXNBAGAME-26APR05WASBKN | — | — | 0.326 | -4.38pp | 2.59pp | 19.9% | 291 |
| KXNBAGAME-26APR06CLEMEM | — | — | 0.615 | +8.83pp | 0.87pp | 12.4% | 259 |
| KXNBAGAME-26APR06DETORL | — | — | 0.727 | -7.22pp | 0.90pp | 33.4% | 293 |
| KXNBAGAME-26APR06NYKATL | — | — | 0.119 | +3.71pp | 4.63pp | 76.2% | 290 |
| KXNBAGAME-26APR06PHISAS | — | — | 0.123 | -4.16pp | 0.74pp | 0.0% | 282 |
| KXNBAGAME-26APR06PORDEN | — | — | 0.067 | +12.88pp | 1.56pp | 44.0% | 318 |
| KXNBAGAME-26APR07CHABOS | — | — | 0.414 | +11.38pp | 0.85pp | 74.0% | 269 |
| KXNBAGAME-26APR07CHIWAS | — | — | 0.428 | -1.33pp | 0.92pp | 1.5% | 273 |
| KXNBAGAME-26APR07DALLAC | — | — | 0.014 | +1.26pp | 0.92pp | 0.0% | 268 |
| KXNBAGAME-26APR07HOUPHX | — | — | 0.418 | -4.63pp | 0.85pp | 53.1% | 305 |
| KXNBAGAME-26APR07MIATOR | — | — | 0.197 | -1.09pp | 0.93pp | 27.0% | 267 |
| KXNBAGAME-26APR07MILBKN | — | — | 0.000 | +1.29pp | 4.71pp | 51.1% | 262 |
| KXNBAGAME-26APR07MININD | — | — | 0.417 | +1.77pp | 0.92pp | 0.0% | 265 |
| KXNBAGAME-26APR07OKCLAL | — | — | 0.600 | +3.67pp | 0.96pp | 0.0% | 263 |
| KXNBAGAME-26APR07SACGSW | — | — | 0.013 | +5.12pp | 4.94pp | 4.9% | 266 |
| KXNBAGAME-26APR07UTANOP | — | — | 0.224 | +0.14pp | 0.92pp | 45.8% | 251 |
| KXNBAGAME-26APR08ATLCLE | — | — | 0.000 | +2.85pp | 3.92pp | 38.7% | 282 |
| KXNBAGAME-26APR08DALPHX | — | — | 0.070 | +4.94pp | 5.18pp | 0.0% | 254 |
| KXNBAGAME-26APR08MEMDEN | — | — | 0.127 | +7.12pp | 0.94pp | 0.0% | 257 |
| KXNBAGAME-26APR08MILDET | — | — | 0.352 | +0.69pp | 0.93pp | 0.0% | 288 |
| KXNBAGAME-26APR08MINORL | — | — | 0.806 | +12.84pp | 0.92pp | 0.0% | 259 |
| KXNBAGAME-26APR08OKCLAC | — | — | 0.090 | -0.75pp | 0.94pp | 0.0% | 275 |
| KXNBAGAME-26APR08PORSAS | — | — | 0.908 | -11.14pp | 0.60pp | 17.7% | 271 |
| KXNBAGAME-26APR09BOSNYK | — | — | 0.001 | +4.58pp | 6.79pp | 72.7% | 267 |
| KXNBAGAME-26APR09CHIWAS | — | — | 0.152 | -1.62pp | 0.91pp | 0.0% | 266 |
| KXNBAGAME-26APR09INDBKN | — | — | 0.440 | -1.42pp | 0.93pp | 8.5% | 248 |
| KXNBAGAME-26APR09LALGSW | — | — | 0.387 | +4.78pp | 0.91pp | 47.1% | 259 |
| KXNBAGAME-26APR09MIATOR | — | — | 0.364 | +0.20pp | 0.96pp | 14.1% | 284 |
| KXNBAGAME-26APR09PHIHOU | — | — | 0.223 | -1.41pp | 1.40pp | 0.0% | 268 |
| KXNBAGAME-26APR10BKNMIL | — | — | 0.179 | +0.41pp | 0.92pp | 0.0% | 247 |
| KXNBAGAME-26APR10CLEATL | — | — | 0.743 | +7.67pp | 0.91pp | 0.0% | 277 |
| KXNBAGAME-26APR10DALSAS | — | — | 0.113 | +1.18pp | 0.92pp | 0.0% | 252 |
| KXNBAGAME-26APR10DETCHA | — | — | 0.319 | +11.12pp | 0.93pp | 71.2% | 278 |
| KXNBAGAME-26APR10GSWSAC | — | — | 0.079 | +12.97pp | 4.56pp | 36.1% | 294 |
| KXNBAGAME-26APR10LACPOR | — | — | 0.127 | -1.96pp | 0.92pp | 46.5% | 273 |
| KXNBAGAME-26APR10MEMUTA | — | — | 0.273 | -1.09pp | 0.92pp | 22.2% | 225 |
| KXNBAGAME-26APR10MIAWAS | — | — | 0.209 | +0.49pp | 0.93pp | 0.0% | 261 |
| KXNBAGAME-26APR10MINHOU | — | — | 0.587 | +11.88pp | 2.52pp | 1.7% | 289 |
| KXNBAGAME-26APR10NOPBOS | — | — | 0.326 | +0.64pp | 0.92pp | 0.0% | 258 |
| KXNBAGAME-26APR10OKCDEN | — | — | 0.722 | +11.90pp | 0.92pp | 15.6% | 244 |
| KXNBAGAME-26APR10ORLCHI | — | — | 0.789 | +7.22pp | 0.93pp | 0.0% | 259 |
| KXNBAGAME-26APR10PHIIND | — | — | 0.681 | +9.39pp | 0.90pp | 0.0% | 253 |
| KXNBAGAME-26APR10PHXLAL | — | — | 0.578 | +3.71pp | 0.92pp | 21.0% | 281 |
| KXNBAGAME-26APR10TORNYK | — | — | 0.242 | +0.31pp | 0.92pp | 0.0% | 266 |
| KXNBAGAME-26APR12ATLMIA | — | — | 0.755 | +9.06pp | 0.94pp | 0.0% | 245 |
| KXNBAGAME-26APR12BKNTOR | — | — | 0.552 | +2.22pp | 0.94pp | 0.0% | 269 |
| KXNBAGAME-26APR12CHANYK | — | — | 0.830 | +12.03pp | 0.93pp | 0.0% | 252 |
| KXNBAGAME-26APR12CHIDAL | — | — | 0.203 | -0.57pp | 0.94pp | 0.4% | 259 |
| KXNBAGAME-26APR12DETIND | — | — | 0.038 | -0.04pp | 0.67pp | 0.0% | 270 |
| KXNBAGAME-26APR12GSWLAC | — | — | 0.000 | -4.83pp | 1.18pp | 65.1% | 278 |
| KXNBAGAME-26APR12MEMHOU | — | — | 0.500 | -1.91pp | 0.93pp | 0.0% | 245 |
| KXNBAGAME-26APR12MILPHI | — | — | 0.331 | +7.98pp | 0.92pp | 0.0% | 254 |
| KXNBAGAME-26APR12NOPMIN | — | — | 0.802 | -5.72pp | 0.78pp | 4.8% | 290 |
| KXNBAGAME-26APR12ORLBOS | — | — | 0.746 | +25.40pp | 7.84pp | 5.5% | 307 |
| KXNBAGAME-26APR12PHXOKC | — | — | 0.442 | +2.35pp | 0.93pp | 9.0% | 233 |
| KXNBAGAME-26APR12SACPOR | — | — | 0.416 | +1.08pp | 0.92pp | 0.0% | 256 |
| KXNBAGAME-26APR12UTALAL | — | — | 0.407 | +0.64pp | 0.94pp | 0.0% | 261 |
| KXNBAGAME-26APR12WASCLE | — | — | 0.017 | -4.11pp | 0.91pp | 0.0% | 257 |
| KXNBAGAME-26APR14MIACHA | — | — | 0.086 | +1.59pp | 9.04pp | 32.3% | 328 |
| KXNBAGAME-26APR14PORPHX | — | — | 0.001 | +0.97pp | 6.25pp | 52.1% | 305 |
| KXNBAGAME-26APR15GSWLAC | — | — | 0.035 | -3.83pp | 8.06pp | 8.9% | 305 |
| KXNBAGAME-26APR15ORLPHI | — | — | 0.052 | -4.36pp | 1.01pp | 61.3% | 310 |
| KXNBAGAME-26APR18HOULAL | — | — | 0.463 | +5.57pp | 0.83pp | 54.7% | 309 |
| KXNBAGAME-26APR19ORLDET | — | — | 0.000 | +6.65pp | 0.45pp | 50.8% | 299 |
| KXNBAGAME-26APR19PORSAS | — | — | 0.077 | +0.59pp | 0.90pp | 0.0% | 286 |
| KXNBAGAME-26APR20ATLNYK | — | — | 0.004 | -3.67pp | 10.25pp | 2.5% | 315 |
| KXNBAGAME-26APR20MINDEN | — | — | 0.057 | -0.35pp | 8.84pp | 16.0% | 313 |
| KXNBAGAME-26APR20TORCLE | — | — | 0.606 | +4.53pp | 0.85pp | 0.0% | 289 |
| KXNBAGAME-26FEB19ATLPHI | — | — | 0.003 | +3.73pp | 0.98pp | 52.2% | 301 |
| KXNBAGAME-26FEB19BKNCLE | — | — | 0.050 | -0.26pp | 0.93pp | 0.0% | 258 |
| KXNBAGAME-26FEB19BOSGSW | — | — | 0.451 | +0.13pp | 0.78pp | 3.6% | 252 |
| KXNBAGAME-26FEB19DENLAC | — | — | 0.022 | +5.11pp | 6.79pp | 21.8% | 312 |
| KXNBAGAME-26FEB19DETNYK | — | — | 0.015 | +4.74pp | 0.94pp | 52.1% | 290 |
| KXNBAGAME-26FEB19HOUCHA | — | — | 0.438 | +7.01pp | 3.36pp | 68.8% | 266 |
| KXNBAGAME-26FEB19INDWAS | — | — | 0.519 | +6.18pp | 2.42pp | 54.3% | 267 |
| KXNBAGAME-26FEB19ORLSAC | — | — | 0.354 | +3.27pp | 0.92pp | 11.2% | 259 |
| KXNBAGAME-26FEB19PHXSAS | — | — | 0.114 | -0.74pp | 0.93pp | 0.0% | 242 |
| KXNBAGAME-26FEB19TORCHI | — | — | 0.279 | +2.55pp | 3.39pp | 1.4% | 292 |
| KXNBAGAME-26FEB20BKNOKC | — | — | 0.093 | -0.03pp | 0.92pp | 0.0% | 292 |
| KXNBAGAME-26FEB20CLECHA | — | — | 0.005 | +2.39pp | 2.46pp | 22.4% | 281 |
| KXNBAGAME-26FEB20DALMIN | — | — | 0.100 | +3.77pp | 1.61pp | 0.0% | 289 |
| KXNBAGAME-26FEB20DENPOR | — | — | 0.645 | +3.39pp | 0.91pp | 7.4% | 269 |
| KXNBAGAME-26FEB20INDWAS | — | — | 0.882 | +14.29pp | 0.83pp | 49.4% | 259 |
| KXNBAGAME-26FEB20LACLAL | — | — | 0.032 | +2.34pp | 6.04pp | 7.8% | 306 |
| KXNBAGAME-26FEB20MIAATL | — | — | 0.293 | -2.97pp | 0.92pp | 10.5% | 247 |
| KXNBAGAME-26FEB20MILNOP | — | — | 0.002 | +3.24pp | 0.92pp | 67.1% | 255 |
| KXNBAGAME-26FEB20UTAMEM | — | — | 0.595 | -6.21pp | 0.83pp | 43.5% | 269 |
| KXNBAGAME-26FEB21DETCHI | — | — | 0.448 | +1.84pp | 0.92pp | 0.0% | 263 |
| KXNBAGAME-26FEB21HOUNYK | — | — | 0.089 | +1.89pp | 6.11pp | 28.5% | 302 |
| KXNBAGAME-26FEB21MEMMIA | — | — | 0.817 | +8.05pp | 0.92pp | 0.0% | 274 |
| KXNBAGAME-26FEB21ORLPHX | — | — | 0.223 | +7.17pp | 10.76pp | 51.2% | 344 |
| KXNBAGAME-26FEB21PHINOP | — | — | 0.001 | +2.91pp | 0.92pp | 22.3% | 300 |
| KXNBAGAME-26FEB21SACSAS | — | — | 0.088 | +1.90pp | 0.93pp | 0.0% | 269 |
| KXNBAGAME-26FEB22BKNATL | — | — | 0.245 | +2.68pp | 3.98pp | 16.1% | 267 |
| KXNBAGAME-26FEB22BOSLAL | — | — | 0.129 | -8.15pp | 0.95pp | 38.5% | 286 |
| KXNBAGAME-26FEB22CHAWAS | — | — | 0.668 | -3.52pp | 0.93pp | 0.0% | 256 |
| KXNBAGAME-26FEB22CLEOKC | — | — | 0.556 | +14.78pp | 2.57pp | 54.8% | 294 |
| KXNBAGAME-26FEB22DALIND | — | — | 0.596 | -7.36pp | 3.29pp | 58.4% | 267 |
| KXNBAGAME-26FEB22DENGSW | — | — | 0.404 | +16.54pp | 0.86pp | 61.2% | 286 |
| KXNBAGAME-26FEB22NYKCHI | — | — | 0.001 | +2.28pp | 3.76pp | 16.3% | 270 |
| KXNBAGAME-26FEB22ORLLAC | — | — | 0.010 | +3.27pp | 6.57pp | 84.9% | 291 |
| KXNBAGAME-26FEB22PHIMIN | — | — | 0.045 | +8.05pp | 0.92pp | 45.5% | 275 |
| KXNBAGAME-26FEB22PORPHX | — | — | 0.669 | +3.14pp | 0.92pp | 34.4% | 247 |
| KXNBAGAME-26FEB22TORMIL | — | — | 0.541 | +1.95pp | 0.93pp | 29.7% | 279 |
| KXNBAGAME-26FEB23SACMEM | — | — | 0.442 | -5.94pp | 1.07pp | 71.6% | 268 |
| KXNBAGAME-26FEB23SASDET | — | — | 0.174 | -0.54pp | 0.80pp | 57.3% | 321 |
| KXNBAGAME-26FEB23UTAHOU | — | — | 0.163 | -0.13pp | 0.92pp | 0.0% | 264 |
| KXNBAGAME-26FEB24BOSPHX | — | — | 0.424 | +2.20pp | 0.93pp | 31.1% | 241 |
| KXNBAGAME-26FEB24CHACHI | — | — | 0.493 | +5.11pp | 0.94pp | 10.4% | 249 |
| KXNBAGAME-26FEB24DALBKN | — | — | 0.625 | -9.25pp | 1.06pp | 22.6% | 270 |
| KXNBAGAME-26FEB24GSWNOP | — | — | 0.030 | +2.50pp | 3.39pp | 33.2% | 289 |
| KXNBAGAME-26FEB24MIAMIL | — | — | 0.045 | +4.29pp | 1.41pp | 44.4% | 268 |
| KXNBAGAME-26FEB24MINPOR | — | — | 0.010 | -2.07pp | 0.97pp | 11.0% | 301 |
| KXNBAGAME-26FEB24NYKCLE | — | — | 0.151 | -0.15pp | 0.94pp | 6.6% | 304 |
| KXNBAGAME-26FEB24OKCTOR | — | — | 0.088 | +5.11pp | 1.76pp | 32.5% | 280 |
| KXNBAGAME-26FEB24ORLLAL | — | — | 0.109 | +4.45pp | 10.13pp | 15.8% | 278 |
| KXNBAGAME-26FEB24PHIIND | — | — | 0.656 | +7.87pp | 0.93pp | 0.0% | 272 |
| KXNBAGAME-26FEB24WASATL | — | — | 0.645 | -1.70pp | 0.92pp | 0.0% | 265 |
| KXNBAGAME-26FEB25BOSDEN | — | — | 0.011 | -0.12pp | 0.92pp | 75.0% | 276 |
| KXNBAGAME-26FEB25CLEMIL | — | — | 0.110 | -6.06pp | 8.28pp | 65.4% | 257 |
| KXNBAGAME-26FEB25GSWMEM | — | — | 0.594 | +1.79pp | 0.92pp | 7.8% | 255 |
| KXNBAGAME-26FEB25OKCDET | — | — | 0.474 | +8.17pp | 4.48pp | 10.4% | 288 |
| KXNBAGAME-26FEB25SACHOU | — | — | 0.117 | -0.13pp | 0.92pp | 0.0% | 248 |
| KXNBAGAME-26FEB25SASTOR | — | — | 0.294 | +3.50pp | 8.49pp | 40.5% | 294 |
| KXNBAGAME-26FEB26CHAIND | — | — | 0.609 | +4.16pp | 0.93pp | 0.0% | 259 |
| KXNBAGAME-26FEB26HOUORL | — | — | 0.012 | +2.75pp | 2.29pp | 46.9% | 286 |
| KXNBAGAME-26FEB26LALPHX | — | — | 0.188 | +10.83pp | 4.85pp | 39.2% | 286 |
| KXNBAGAME-26FEB26MIAPHI | — | — | 0.041 | -0.93pp | 2.92pp | 32.5% | 265 |
| KXNBAGAME-26FEB26MINLAC | — | — | 0.075 | +14.07pp | 5.13pp | 11.5% | 296 |
| KXNBAGAME-26FEB26NOPUTA | — | — | 0.265 | -0.48pp | 0.81pp | 4.0% | 274 |
| KXNBAGAME-26FEB26PORCHI | — | — | 0.410 | +2.32pp | 1.62pp | 47.3% | 277 |
| KXNBAGAME-26FEB26SACDAL | — | — | 0.006 | +2.20pp | 5.54pp | 31.7% | 268 |
| KXNBAGAME-26FEB26SASBKN | — | — | 0.033 | +0.59pp | 0.93pp | 0.0% | 258 |
| KXNBAGAME-26FEB26WASATL | — | — | 0.641 | -2.66pp | 0.92pp | 0.0% | 257 |
| KXNBAGAME-26FEB27BKNBOS | — | — | 0.447 | +1.73pp | 0.92pp | 0.0% | 266 |
| KXNBAGAME-26FEB27CLEDET | — | — | 0.563 | +13.78pp | 6.23pp | 30.2% | 398 |
| KXNBAGAME-26FEB27DENOKC | — | — | 0.023 | +4.97pp | 1.84pp | 67.9% | 349 |
| KXNBAGAME-26FEB27MEMDAL | — | — | 0.759 | +5.89pp | 0.92pp | 21.1% | 261 |
| KXNBAGAME-26FEB27NYKMIL | — | — | 0.464 | -2.03pp | 0.93pp | 0.0% | 252 |
| KXNBAGAME-26FEB28HOUMIA | — | — | 0.015 | +1.70pp | 0.71pp | 78.5% | 293 |
| KXNBAGAME-26FEB28LALGSW | — | — | 0.402 | +0.84pp | 0.92pp | 1.2% | 259 |
| KXNBAGAME-26FEB28NOPUTA | — | — | 0.359 | -1.84pp | 0.91pp | 0.0% | 287 |
| KXNBAGAME-26FEB28PORCHA | — | — | 0.355 | -1.60pp | 0.92pp | 0.0% | 273 |
| KXNBAGAME-26FEB28TORWAS | — | — | 0.482 | +7.14pp | 0.91pp | 0.0% | 276 |
| KXNBAGAME-26MAR01CLEBKN | — | — | 0.116 | +5.66pp | 7.48pp | 6.8% | 308 |
| KXNBAGAME-26MAR01DETORL | — | — | 0.168 | +5.09pp | 0.73pp | 66.9% | 275 |
| KXNBAGAME-26MAR01MEMIND | — | — | 0.031 | +4.19pp | 0.93pp | 51.0% | 259 |
| KXNBAGAME-26MAR01MILCHI | — | — | 0.239 | +0.88pp | 0.92pp | 39.1% | 258 |
| KXNBAGAME-26MAR01MINDEN | — | — | 0.088 | +5.80pp | 0.80pp | 50.7% | 282 |
| KXNBAGAME-26MAR01NOPLAC | — | — | 0.434 | -1.34pp | 0.92pp | 0.0% | 283 |
| KXNBAGAME-26MAR01OKCDAL | — | — | 0.386 | +1.86pp | 0.92pp | 0.0% | 248 |
| KXNBAGAME-26MAR01PHIBOS | — | — | 0.439 | +1.35pp | 0.84pp | 6.6% | 290 |
| KXNBAGAME-26MAR01PORATL | — | — | 0.627 | -2.30pp | 0.93pp | 0.7% | 270 |
| KXNBAGAME-26MAR01SACLAL | — | — | 0.273 | +1.32pp | 0.95pp | 0.0% | 265 |
| KXNBAGAME-26MAR01SASNYK | — | — | 0.023 | +6.55pp | 0.92pp | 22.9% | 292 |
| KXNBAGAME-26MAR02BOSMIL | — | — | 0.778 | -5.14pp | 0.93pp | 19.3% | 244 |
| KXNBAGAME-26MAR02DENUTA | — | — | 0.122 | +1.13pp | 8.45pp | 7.6% | 302 |
| KXNBAGAME-26MAR02HOUWAS | — | — | 0.337 | +0.81pp | 0.79pp | 0.0% | 277 |
| KXNBAGAME-26MAR02LACGSW | — | — | 0.000 | +4.15pp | 0.92pp | 28.7% | 286 |
| KXNBAGAME-26MAR03BKNMIA | — | — | 0.253 | +0.66pp | 0.92pp | 0.0% | 278 |
| KXNBAGAME-26MAR03DALCHA | — | — | 0.693 | +4.38pp | 0.92pp | 0.0% | 282 |
| KXNBAGAME-26MAR03DETCLE | — | — | 0.189 | +7.21pp | 3.30pp | 66.0% | 282 |
| KXNBAGAME-26MAR03MEMMIN | — | — | 0.601 | +20.04pp | 2.25pp | 0.0% | 282 |
| KXNBAGAME-26MAR03NOPLAL | — | — | 0.003 | +6.17pp | 1.18pp | 16.1% | 285 |
| KXNBAGAME-26MAR03NYKTOR | — | — | 0.116 | -4.35pp | 0.90pp | 28.3% | 272 |
| KXNBAGAME-26MAR03OKCCHI | — | — | 0.176 | +0.48pp | 0.94pp | 0.0% | 265 |
| KXNBAGAME-26MAR03PHXSAC | — | — | 0.271 | +1.79pp | 0.67pp | 4.5% | 266 |
| KXNBAGAME-26MAR03SASPHI | — | — | 0.357 | +0.72pp | 0.92pp | 0.0% | 280 |
| KXNBAGAME-26MAR03WASORL | — | — | 0.248 | +1.35pp | 0.92pp | 0.0% | 273 |
| KXNBAGAME-26MAR04ATLMIL | — | — | 0.012 | +4.03pp | 0.92pp | 31.1% | 267 |
| KXNBAGAME-26MAR04CHABOS | — | — | 0.764 | +7.47pp | 0.94pp | 23.7% | 253 |
| KXNBAGAME-26MAR04INDLAC | — | — | 0.219 | +0.67pp | 0.94pp | 0.0% | 288 |
| KXNBAGAME-26MAR04OKCNYK | — | — | 0.023 | -0.68pp | 5.16pp | 19.4% | 299 |
| KXNBAGAME-26MAR04PORMEM | — | — | 0.553 | +14.47pp | 0.63pp | 6.5% | 275 |
| KXNBAGAME-26MAR04UTAPHI | — | — | 0.130 | +1.62pp | 5.76pp | 15.0% | 267 |
| KXNBAGAME-26MAR05BKNMIA | — | — | 0.233 | +3.99pp | 0.93pp | 0.0% | 263 |
| KXNBAGAME-26MAR05CHIPHX | — | — | 0.379 | +17.28pp | 6.39pp | 54.4% | 285 |
| KXNBAGAME-26MAR05DALORL | — | — | 0.557 | +15.77pp | 7.59pp | 33.6% | 289 |
| KXNBAGAME-26MAR05DETSAS | — | — | 0.184 | -1.67pp | 0.80pp | 3.8% | 293 |
| KXNBAGAME-26MAR05GSWHOU | — | — | 0.609 | +14.89pp | 5.62pp | 44.2% | 321 |
| KXNBAGAME-26MAR05LALDEN | — | — | 0.533 | -7.21pp | 2.39pp | 3.1% | 286 |
| KXNBAGAME-26MAR05NOPSAC | — | — | 0.614 | +3.78pp | 0.90pp | 29.1% | 268 |
| KXNBAGAME-26MAR05TORMIN | — | — | 0.238 | +0.68pp | 0.89pp | 45.1% | 277 |
| KXNBAGAME-26MAR05UTAWAS | — | — | 0.548 | +7.69pp | 0.80pp | 25.2% | 266 |
| KXNBAGAME-26MAR06DALBOS | — | — | 0.621 | +7.84pp | 0.93pp | 0.0% | 259 |
| KXNBAGAME-26MAR06INDLAL | — | — | 0.497 | +1.84pp | 0.95pp | 0.0% | 270 |
| KXNBAGAME-26MAR06LACSAS | — | — | 0.323 | +13.21pp | 6.21pp | 25.5% | 290 |
| KXNBAGAME-26MAR06MIACHA | — | — | 0.007 | +2.68pp | 4.18pp | 9.4% | 277 |
| KXNBAGAME-26MAR06NOPPHX | — | — | 0.019 | +0.99pp | 8.28pp | 22.9% | 306 |
| KXNBAGAME-26MAR06NYKDEN | — | — | 0.153 | -2.93pp | 0.91pp | 38.8% | 276 |
| KXNBAGAME-26MAR06PORHOU | — | — | 0.100 | +2.22pp | 1.77pp | 40.2% | 271 |
| KXNBAGAME-26MAR07BKNDET | — | — | 0.075 | -0.06pp | 6.01pp | 1.7% | 300 |
| KXNBAGAME-26MAR07GSWOKC | — | — | 0.004 | +1.03pp | 4.08pp | 0.0% | 278 |
| KXNBAGAME-26MAR07LACMEM | — | — | 0.523 | +15.48pp | 3.99pp | 35.2% | 298 |
| KXNBAGAME-26MAR07ORLMIN | — | — | 0.007 | +3.97pp | 0.92pp | 21.0% | 291 |
| KXNBAGAME-26MAR07PHIATL | — | — | 0.501 | +7.57pp | 0.97pp | 56.3% | 279 |
| KXNBAGAME-26MAR07UTAMIL | — | — | 0.001 | -0.17pp | 0.57pp | 0.0% | 274 |
| KXNBAGAME-26MAR08BOSCLE | — | — | 0.627 | +13.23pp | 0.85pp | 0.0% | 287 |
| KXNBAGAME-26MAR08CHAPHX | — | — | 0.050 | +3.50pp | 0.92pp | 47.0% | 281 |
| KXNBAGAME-26MAR08CHISAC | — | — | 0.053 | +3.98pp | 0.84pp | 28.5% | 281 |
| KXNBAGAME-26MAR08DALTOR | — | — | 0.836 | +9.91pp | 0.94pp | 0.0% | 218 |
| KXNBAGAME-26MAR08DETMIA | — | — | 0.693 | -8.70pp | 0.96pp | 0.0% | 217 |
| KXNBAGAME-26MAR08HOUSAS | — | — | 0.248 | +0.26pp | 0.92pp | 3.7% | 296 |
| KXNBAGAME-26MAR08INDPOR | — | — | 0.592 | +3.50pp | 0.92pp | 0.0% | 269 |
| KXNBAGAME-26MAR08NYKLAL | — | — | 0.018 | -12.78pp | 0.78pp | 25.2% | 306 |
| KXNBAGAME-26MAR08ORLMIL | — | — | 0.320 | -0.68pp | 0.91pp | 0.0% | 266 |
| KXNBAGAME-26MAR08WASNOP | — | — | 0.407 | +4.69pp | 0.93pp | 0.0% | 188 |
| KXNBAGAME-26MAR09DENOKC | — | — | 0.003 | -3.42pp | 7.38pp | 60.3% | 300 |
| KXNBAGAME-26MAR09GSWUTA | — | — | 0.240 | +5.81pp | 6.52pp | 58.8% | 284 |
| KXNBAGAME-26MAR09MEMBKN | — | — | 0.478 | -4.81pp | 0.92pp | 34.5% | 264 |
| KXNBAGAME-26MAR09NYKLAC | — | — | 0.256 | +7.97pp | 1.28pp | 38.0% | 303 |
| KXNBAGAME-26MAR09PHICLE | — | — | 0.677 | +4.27pp | 0.92pp | 0.0% | 266 |
| KXNBAGAME-26MAR10BOSSAS | — | — | 0.025 | +4.33pp | 1.15pp | 47.4% | 285 |
| KXNBAGAME-26MAR10CHAPOR | — | — | 0.018 | +1.44pp | 9.61pp | 35.2% | 281 |
| KXNBAGAME-26MAR10CHIGSW | — | — | 0.158 | +3.48pp | 2.05pp | 33.7% | 303 |
| KXNBAGAME-26MAR10DALATL | — | — | 0.003 | +1.06pp | 0.86pp | 0.0% | 268 |
| KXNBAGAME-26MAR10DETBKN | — | — | 0.049 | -0.26pp | 0.92pp | 0.0% | 305 |
| KXNBAGAME-26MAR10INDSAC | — | — | 0.017 | +7.24pp | 2.00pp | 29.0% | 300 |
| KXNBAGAME-26MAR10MEMPHI | — | — | 0.504 | +10.44pp | 0.68pp | 58.4% | 298 |
| KXNBAGAME-26MAR10MINLAL | — | — | 0.002 | +0.77pp | 0.93pp | 44.4% | 286 |
| KXNBAGAME-26MAR10PHXMIL | — | — | 0.036 | -0.49pp | 0.92pp | 71.3% | 261 |
| KXNBAGAME-26MAR10TORHOU | — | — | 0.010 | -0.38pp | 0.92pp | 24.8% | 266 |
| KXNBAGAME-26MAR10WASMIA | — | — | 0.130 | +0.07pp | 0.91pp | 0.0% | 302 |
| KXNBAGAME-26MAR11CHASAC | — | — | 0.168 | +4.90pp | 0.74pp | 0.0% | 257 |
| KXNBAGAME-26MAR11CLEORL | — | — | 0.011 | +1.38pp | 3.20pp | 71.2% | 306 |
| KXNBAGAME-26MAR11HOUDEN | — | — | 0.553 | +1.93pp | 0.92pp | 2.3% | 262 |
| KXNBAGAME-26MAR11MINLAC | — | — | 0.725 | -8.19pp | 0.96pp | 18.7% | 283 |
| KXNBAGAME-26MAR11NYKUTA | — | — | 0.083 | +9.52pp | 0.92pp | 38.8% | 281 |
| KXNBAGAME-26MAR11TORNOP | — | — | 0.011 | +7.83pp | 0.93pp | 58.7% | 271 |
| KXNBAGAME-26MAR12BKNATL | — | — | 0.098 | +3.35pp | 0.91pp | 0.0% | 269 |
| KXNBAGAME-26MAR12BOSOKC | — | — | 0.009 | +11.58pp | 8.59pp | 35.3% | 289 |
| KXNBAGAME-26MAR12CHILAL | — | — | 0.308 | +3.90pp | 0.88pp | 0.0% | 274 |
| KXNBAGAME-26MAR12DALMEM | — | — | 0.066 | +1.92pp | 0.91pp | 2.3% | 257 |
| KXNBAGAME-26MAR12DENSAS | — | — | 0.397 | -7.05pp | 2.41pp | 20.0% | 295 |
| KXNBAGAME-26MAR12MILMIA | — | — | 0.009 | -3.33pp | 3.33pp | 0.7% | 275 |
| KXNBAGAME-26MAR12PHIDET | — | — | 0.387 | +1.04pp | 0.92pp | 0.0% | 270 |
| KXNBAGAME-26MAR12PHXIND | — | — | 0.650 | +4.68pp | 0.92pp | 0.0% | 272 |
| KXNBAGAME-26MAR12WASORL | — | — | 0.181 | +3.08pp | 5.78pp | 0.3% | 304 |
| KXNBAGAME-26MAR13CHILAC | — | — | 0.228 | +2.68pp | 0.58pp | 0.0% | 262 |
| KXNBAGAME-26MAR13CLEDAL | — | — | 0.410 | +1.74pp | 0.93pp | 0.0% | 266 |
| KXNBAGAME-26MAR13MEMDET | — | — | 0.711 | +5.79pp | 0.93pp | 0.0% | 263 |
| KXNBAGAME-26MAR13MINGSW | — | — | 0.628 | +2.53pp | 0.89pp | 0.0% | 288 |
| KXNBAGAME-26MAR13NOPHOU | — | — | 0.085 | -1.52pp | 7.37pp | 5.2% | 289 |
| KXNBAGAME-26MAR13NYKIND | — | — | 0.003 | +1.57pp | 0.70pp | 0.0% | 279 |
| KXNBAGAME-26MAR13PHXTOR | — | — | 0.012 | +8.96pp | 4.19pp | 63.5% | 285 |
| KXNBAGAME-26MAR13UTAPOR | — | — | 0.600 | +8.33pp | 0.90pp | 0.8% | 261 |
| KXNBAGAME-26MAR14BKNPHI | — | — | 0.026 | +0.39pp | 3.60pp | 1.4% | 277 |
| KXNBAGAME-26MAR14CHASAS | — | — | 0.234 | +1.12pp | 0.93pp | 0.0% | 280 |
| KXNBAGAME-26MAR14DENLAL | — | — | 0.103 | +5.81pp | 7.25pp | 40.1% | 339 |
| KXNBAGAME-26MAR14MILATL | — | — | 0.377 | +1.76pp | 0.93pp | 0.0% | 265 |
| KXNBAGAME-26MAR14ORLMIA | — | — | 0.308 | +5.07pp | 6.96pp | 19.1% | 304 |
| KXNBAGAME-26MAR14SACLAC | — | — | 0.007 | +8.56pp | 1.99pp | 28.9% | 284 |
| KXNBAGAME-26MAR14WASBOS | — | — | 0.264 | +0.54pp | 0.92pp | 0.0% | 247 |
| KXNBAGAME-26MAR15DALCLE | — | — | 0.063 | +11.20pp | 0.82pp | 16.6% | 265 |
| KXNBAGAME-26MAR15DETTOR | — | — | 0.001 | -1.27pp | 2.10pp | 47.7% | 285 |
| KXNBAGAME-26MAR15GSWNYK | — | — | 0.197 | +13.02pp | 6.04pp | 34.0% | 303 |
| KXNBAGAME-26MAR15INDMIL | — | — | 0.434 | +12.84pp | 0.90pp | 21.3% | 263 |
| KXNBAGAME-26MAR15MINOKC | — | — | 0.005 | +5.28pp | 0.92pp | 31.1% | 273 |
| KXNBAGAME-26MAR15PORPHI | — | — | 0.269 | +13.47pp | 3.39pp | 26.5% | 260 |
| KXNBAGAME-26MAR15UTASAC | — | — | 0.102 | +4.01pp | 4.53pp | 39.3% | 257 |
| KXNBAGAME-26MAR16DALNOP | — | — | 0.446 | +2.53pp | 0.92pp | 5.1% | 256 |
| KXNBAGAME-26MAR16GSWWAS | — | — | 0.141 | -2.27pp | 0.66pp | 0.0% | 283 |
| KXNBAGAME-26MAR16LALHOU | — | — | 0.007 | -6.90pp | 2.72pp | 81.2% | 282 |
| KXNBAGAME-26MAR16MEMCHI | — | — | 0.739 | +6.06pp | 0.92pp | 0.8% | 259 |
| KXNBAGAME-26MAR16ORLATL | — | — | 0.484 | -4.00pp | 0.82pp | 9.4% | 297 |
| KXNBAGAME-26MAR16PHXBOS | — | — | 0.444 | +7.10pp | 3.62pp | 7.8% | 293 |
| KXNBAGAME-26MAR16PORBKN | — | — | 0.433 | +0.81pp | 0.93pp | 0.0% | 275 |
| KXNBAGAME-26MAR16SASLAC | — | — | 0.681 | +11.51pp | 4.40pp | 17.0% | 306 |
| KXNBAGAME-26MAR17CLEMIL | — | — | 0.012 | +4.08pp | 1.94pp | 0.3% | 291 |
| KXNBAGAME-26MAR17DETWAS | — | — | 0.007 | -0.50pp | 0.92pp | 0.0% | 276 |
| KXNBAGAME-26MAR17INDNYK | — | — | 0.086 | +0.14pp | 0.93pp | 0.0% | 249 |
| KXNBAGAME-26MAR17MIACHA | — | — | 0.229 | +1.41pp | 0.92pp | 30.8% | 286 |
| KXNBAGAME-26MAR17OKCORL | — | — | 0.020 | +4.86pp | 0.60pp | 6.4% | 281 |
| KXNBAGAME-26MAR17PHIDEN | — | — | 0.285 | +0.20pp | 0.92pp | 0.0% | 276 |
| KXNBAGAME-26MAR17PHXMIN | — | — | 0.100 | -2.50pp | 0.78pp | 65.3% | 285 |
| KXNBAGAME-26MAR17SASSAC | — | — | 0.028 | -0.79pp | 0.94pp | 0.0% | 240 |
| KXNBAGAME-26MAR18ATLDAL | — | — | 0.444 | +1.01pp | 0.94pp | 0.0% | 260 |
| KXNBAGAME-26MAR18DENMEM | — | — | 0.040 | +19.93pp | 1.61pp | 19.3% | 285 |
| KXNBAGAME-26MAR18GSWBOS | — | — | 0.477 | +2.13pp | 0.92pp | 0.0% | 273 |
| KXNBAGAME-26MAR18LACNOP | — | — | 0.686 | +5.01pp | 0.94pp | 30.7% | 254 |
| KXNBAGAME-26MAR18LALHOU | — | — | 0.019 | +1.96pp | 2.15pp | 56.6% | 295 |
| KXNBAGAME-26MAR18OKCBKN | — | — | 0.305 | +0.02pp | 0.92pp | 0.0% | 268 |
| KXNBAGAME-26MAR18PORIND | — | — | 0.581 | +3.05pp | 1.89pp | 0.0% | 280 |
| KXNBAGAME-26MAR18TORCHI | — | — | 0.340 | -0.20pp | 0.92pp | 0.0% | 266 |
| KXNBAGAME-26MAR18UTAMIN | — | — | 0.273 | +0.07pp | 0.92pp | 0.0% | 282 |
| KXNBAGAME-26MAR19CLECHI | — | — | 0.007 | -0.39pp | 2.62pp | 0.0% | 309 |
| KXNBAGAME-26MAR19DETWAS | — | — | 0.023 | -1.51pp | 0.94pp | 0.0% | 272 |
| KXNBAGAME-26MAR19LACNOP | — | — | 0.632 | +10.84pp | 1.69pp | 51.4% | 276 |
| KXNBAGAME-26MAR19LALMIA | — | — | 0.001 | +0.11pp | 1.70pp | 14.3% | 293 |
| KXNBAGAME-26MAR19MILUTA | — | — | 0.291 | +6.18pp | 0.92pp | 34.5% | 258 |
| KXNBAGAME-26MAR19ORLCHA | — | — | 0.388 | -0.73pp | 0.93pp | 14.1% | 305 |
| KXNBAGAME-26MAR19PHISAC | — | — | 0.640 | -5.71pp | 0.92pp | 17.2% | 273 |
| KXNBAGAME-26MAR19PHXSAS | — | — | 0.001 | +12.77pp | 10.74pp | 41.9% | 279 |
| KXNBAGAME-26MAR20ATLHOU | — | — | 0.330 | -0.74pp | 0.93pp | 15.0% | 267 |
| KXNBAGAME-26MAR20BOSMEM | — | — | 0.141 | +16.25pp | 0.93pp | 9.6% | 270 |
| KXNBAGAME-26MAR20GSWDET | — | — | 0.227 | -0.72pp | 0.91pp | 22.5% | 271 |
| KXNBAGAME-26MAR20NYKBKN | — | — | 0.098 | +9.23pp | 6.42pp | 3.4% | 296 |
| KXNBAGAME-26MAR20PORMIN | — | — | 0.078 | -7.29pp | 8.00pp | 55.1% | 285 |
| KXNBAGAME-26MAR20TORDEN | — | — | 0.003 | +7.92pp | 5.22pp | 47.3% | 273 |
| KXNBAGAME-26MAR21CLENOP | — | — | 0.383 | -2.37pp | 2.78pp | 28.5% | 274 |
| KXNBAGAME-26MAR21GSWATL | — | — | 0.139 | +1.82pp | 0.93pp | 16.9% | 278 |
| KXNBAGAME-26MAR21INDSAS | — | — | 0.445 | +0.93pp | 0.93pp | 0.0% | 259 |
| KXNBAGAME-26MAR21LACDAL | — | — | 0.293 | +9.20pp | 0.56pp | 43.8% | 299 |
| KXNBAGAME-26MAR21LALORL | — | — | 0.108 | +6.88pp | 8.17pp | 63.0% | 300 |
| KXNBAGAME-26MAR21MEMCHA | — | — | 0.636 | +3.14pp | 0.94pp | 0.0% | 271 |
| KXNBAGAME-26MAR21MIAHOU | — | — | 0.027 | +0.58pp | 13.01pp | 68.1% | 273 |
| KXNBAGAME-26MAR21MILPHX | — | — | 0.006 | +9.27pp | 4.69pp | 31.1% | 280 |
| KXNBAGAME-26MAR21OKCWAS | — | — | 0.013 | +0.60pp | 0.92pp | 0.0% | 296 |
| KXNBAGAME-26MAR21PHIUTA | — | — | 0.010 | +2.04pp | 1.45pp | 36.9% | 271 |
| KXNBAGAME-26MAR22BKNSAC | — | — | 0.000 | +8.25pp | 9.45pp | 42.6% | 298 |
| KXNBAGAME-26MAR22MINBOS | — | — | 0.056 | +11.25pp | 0.92pp | 5.2% | 269 |
| KXNBAGAME-26MAR22PORDEN | — | — | 0.075 | +0.29pp | 0.92pp | 0.0% | 244 |
| KXNBAGAME-26MAR22TORPHX | — | — | 0.842 | +8.76pp | 0.92pp | 24.7% | 255 |
| KXNBAGAME-26MAR22WASNYK | — | — | 0.152 | -0.35pp | 0.92pp | 0.0% | 258 |
| KXNBAGAME-26MAR23BKNPOR | — | — | 0.522 | +1.72pp | 0.92pp | 0.0% | 283 |
| KXNBAGAME-26MAR23GSWDAL | — | — | 0.330 | +6.99pp | 2.09pp | 51.0% | 343 |
| KXNBAGAME-26MAR23HOUCHI | — | — | 0.195 | +18.83pp | 5.73pp | 38.5% | 283 |
| KXNBAGAME-26MAR23INDORL | — | — | 0.006 | +9.05pp | 6.15pp | 26.9% | 294 |
| KXNBAGAME-26MAR23LALDET | — | — | 0.223 | +14.09pp | 5.72pp | 64.0% | 286 |
| KXNBAGAME-26MAR23MEMATL | — | — | 0.477 | +1.73pp | 0.92pp | 0.0% | 262 |
| KXNBAGAME-26MAR23MILLAC | — | — | 0.396 | +0.45pp | 0.95pp | 0.0% | 256 |
| KXNBAGAME-26MAR23OKCPHI | — | — | 0.409 | +1.11pp | 0.93pp | 0.0% | 253 |
| KXNBAGAME-26MAR23SASMIA | — | — | 0.260 | -1.81pp | 0.92pp | 7.6% | 277 |
| KXNBAGAME-26MAR23TORUTA | — | — | 0.221 | -0.19pp | 0.91pp | 0.0% | 293 |
| KXNBAGAME-26MAR24DENPHX | — | — | 0.211 | +5.72pp | 7.97pp | 35.8% | 299 |
| KXNBAGAME-26MAR24NOPNYK | — | — | 0.015 | +0.39pp | 4.01pp | 6.5% | 275 |
| KXNBAGAME-26MAR24ORLCLE | — | — | 0.076 | +0.96pp | 4.09pp | 0.3% | 301 |
| KXNBAGAME-26MAR24SACCHA | — | — | 0.230 | +0.12pp | 0.95pp | 0.0% | 247 |
| KXNBAGAME-26MAR25ATLDET | — | — | 0.050 | -0.39pp | 10.52pp | 65.0% | 317 |
| KXNBAGAME-26MAR25BKNGSW | — | — | 0.021 | +10.32pp | 8.40pp | 46.2% | 301 |
| KXNBAGAME-26MAR25CHIPHI | — | — | 0.239 | -1.68pp | 0.92pp | 0.0% | 272 |
| KXNBAGAME-26MAR25DALDEN | — | — | 0.198 | +2.65pp | 1.22pp | 0.0% | 284 |
| KXNBAGAME-26MAR25HOUMIN | — | — | 0.639 | +10.68pp | 4.44pp | 67.8% | 339 |
| KXNBAGAME-26MAR25LALIND | — | — | 0.146 | +0.04pp | 1.15pp | 0.0% | 283 |
| KXNBAGAME-26MAR25MIACLE | — | — | 0.100 | +1.30pp | 0.93pp | 36.9% | 271 |
| KXNBAGAME-26MAR25MILPOR | — | — | 0.525 | +1.58pp | 0.92pp | 0.0% | 280 |
| KXNBAGAME-26MAR25OKCBOS | — | — | 0.404 | -3.04pp | 1.31pp | 45.6% | 281 |
| KXNBAGAME-26MAR25SASMEM | — | — | 0.181 | +0.83pp | 0.92pp | 0.0% | 257 |
| KXNBAGAME-26MAR25TORLAC | — | — | 0.377 | -3.49pp | 0.95pp | 3.4% | 267 |
| KXNBAGAME-26MAR25WASUTA | — | — | 0.442 | +3.53pp | 0.92pp | 18.1% | 260 |
| KXNBAGAME-26MAR26NOPDET | — | — | 0.431 | -5.83pp | 0.93pp | 18.5% | 260 |
| KXNBAGAME-26MAR26NYKCHA | — | — | 0.042 | -1.17pp | 0.76pp | 28.9% | 273 |
| KXNBAGAME-26MAR26SACORL | — | — | 0.186 | +5.25pp | 5.58pp | 0.0% | 277 |
| KXNBAGAME-26MAR27ATLBOS | — | — | 0.667 | +8.71pp | 1.03pp | 58.7% | 269 |
| KXNBAGAME-26MAR27BKNLAL | — | — | 0.022 | +4.14pp | 0.91pp | 0.0% | 283 |
| KXNBAGAME-26MAR27CHIOKC | — | — | 0.111 | +7.01pp | 0.92pp | 2.6% | 273 |
| KXNBAGAME-26MAR27DALPOR | — | — | 0.382 | +15.03pp | 3.58pp | 63.0% | 273 |
| KXNBAGAME-26MAR27HOUMEM | — | — | 0.677 | +9.25pp | 0.68pp | 0.0% | 251 |
| KXNBAGAME-26MAR27LACIND | — | — | 0.046 | +14.60pp | 8.03pp | 55.4% | 305 |
| KXNBAGAME-26MAR27MIACLE | — | — | 0.628 | -2.57pp | 0.92pp | 0.0% | 297 |
| KXNBAGAME-26MAR27NOPTOR | — | — | 0.272 | +0.60pp | 0.96pp | 0.0% | 270 |
| KXNBAGAME-26MAR27UTADEN | — | — | 0.377 | +9.30pp | 6.62pp | 19.1% | 267 |
| KXNBAGAME-26MAR27WASGSW | — | — | 0.107 | -0.30pp | 2.35pp | 11.4% | 273 |
| KXNBAGAME-26MAR28CHIMEM | — | — | 0.005 | +9.08pp | 5.21pp | 55.8% | 303 |
| KXNBAGAME-26MAR28DETMIN | — | — | 0.241 | +0.07pp | 0.92pp | 18.8% | 271 |
| KXNBAGAME-26MAR28PHICHA | — | — | 0.142 | +0.30pp | 5.14pp | 15.9% | 290 |
| KXNBAGAME-26MAR28SACATL | — | — | 0.098 | +1.60pp | 0.61pp | 0.0% | 259 |
| KXNBAGAME-26MAR28SASMIL | — | — | 0.428 | +0.93pp | 0.93pp | 0.0% | 252 |
| KXNBAGAME-26MAR28UTAPHX | — | — | 0.156 | -0.12pp | 0.92pp | 0.0% | 245 |
| KXNBAGAME-26MAR29BOSCHA | — | — | 0.155 | -4.22pp | 0.92pp | 21.5% | 247 |
| KXNBAGAME-26MAR29GSWDEN | — | — | 0.291 | +10.94pp | 0.91pp | 19.4% | 294 |
| KXNBAGAME-26MAR29HOUNOP | — | — | 0.506 | +0.96pp | 0.92pp | 6.7% | 270 |
| KXNBAGAME-26MAR29LACMIL | — | — | 0.687 | +2.72pp | 0.92pp | 0.0% | 275 |
| KXNBAGAME-26MAR29MIAIND | — | — | 0.000 | +9.27pp | 0.92pp | 19.1% | 257 |
| KXNBAGAME-26MAR29NYKOKC | — | — | 0.251 | +5.12pp | 0.81pp | 0.0% | 312 |
| KXNBAGAME-26MAR29ORLTOR | — | — | 0.375 | -2.49pp | 0.95pp | 15.3% | 268 |
| KXNBAGAME-26MAR29SACBKN | — | — | 0.566 | +3.42pp | 0.92pp | 3.8% | 262 |
| KXNBAGAME-26MAR29WASPOR | — | — | 0.132 | +0.60pp | 0.92pp | 0.0% | 275 |
| KXNBAGAME-26MAR30BOSATL | — | — | 0.071 | +0.23pp | 0.90pp | 55.0% | 260 |
| KXNBAGAME-26MAR30CHISAS | — | — | 0.646 | +2.30pp | 0.92pp | 0.0% | 268 |
| KXNBAGAME-26MAR30CLEUTA | — | — | 0.107 | +1.06pp | 0.60pp | 0.4% | 254 |
| KXNBAGAME-26MAR30DETOKC | — | — | 0.006 | +11.96pp | 6.58pp | 8.6% | 348 |
| KXNBAGAME-26MAR30MINDAL | — | — | 0.322 | +1.13pp | 0.92pp | 0.0% | 275 |
| KXNBAGAME-26MAR30PHIMIA | — | — | 0.061 | +5.16pp | 0.92pp | 63.7% | 295 |
| KXNBAGAME-26MAR30PHXMEM | — | — | 0.438 | +13.37pp | 0.92pp | 1.6% | 254 |
| KXNBAGAME-26MAR30WASLAL | — | — | 0.238 | -1.06pp | 0.94pp | 0.0% | 271 |
| KXNBAGAME-26MAR31CHABKN | — | — | 0.205 | +0.35pp | 0.92pp | 0.0% | 270 |
| KXNBAGAME-26MAR31CLELAL | — | — | 0.648 | +1.91pp | 0.92pp | 30.0% | 267 |
| KXNBAGAME-26MAR31DALMIL | — | — | 0.614 | +6.53pp | 0.92pp | 28.1% | 260 |
| KXNBAGAME-26MAR31NYKHOU | — | — | 0.523 | -3.46pp | 0.92pp | 8.2% | 269 |
| KXNBAGAME-26MAR31PHXORL | — | — | 0.072 | -2.76pp | 2.26pp | 29.5% | 319 |
| KXNBAGAME-26MAR31PORLAC | — | — | 0.036 | +3.40pp | 0.83pp | 29.5% | 275 |
| KXNBAGAME-26MAR31TORDET | — | — | 0.663 | -6.73pp | 0.82pp | 5.2% | 287 |

