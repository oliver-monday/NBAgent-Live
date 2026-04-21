# Strategy 4 — Dip-Recovery & Run-Capture Analysis

_Generated: 2026-04-21T09:52:29.516559+00:00_

Three-part analysis on 165 competitive games from the 168-game paired dataset. Part 1: false-summit analysis. Part 2: favorite dip-recovery sweep (1,200 configs). Part 3: underdog run-capture sweep (~200 configs). Part 4: cross-strategy comparison.

**Hypothesis:** buy favorite during temporary underdog runs at $0.50–$0.75, exit when favorite reasserts at $0.80–$0.95. Mirror for underdog side with static and momentum entries across $0.10–$0.35 bands.

## Part 1 — False-Summit Analysis

For each price level, fraction of games where the side reached that level and eventually *lost* (fav loses if final fav price ≤ 0.05; dog loses if final fav price ≥ 0.95). Lower loss rates = safer exit ceilings.

### Favorite side (n=165 competitive games)

| Price level | Games reaching | Eventual losses | Loss rate | Cum bins above | Weighted loss rate |
|---:|---:|---:|---:|---:|---:|
| $0.50 | 162 | 62 | 38.3% | 31349 | 22.5% |
| $0.52 | 160 | 60 | 37.5% | 30179 | 21.4% |
| $0.54 | 159 | 59 | 37.1% | 28795 | 20.1% |
| $0.56 | 155 | 55 | 35.5% | 27460 | 19.0% |
| $0.58 | 152 | 52 | 34.2% | 26135 | 17.9% |
| $0.60 | 151 | 51 | 33.8% | 24878 | 16.8% |
| $0.62 | 147 | 47 | 32.0% | 23389 | 15.5% |
| $0.64 | 145 | 45 | 31.0% | 21909 | 14.2% |
| $0.66 | 140 | 40 | 28.6% | 20507 | 13.0% |
| $0.68 | 136 | 36 | 26.5% | 19144 | 11.5% |
| $0.70 | 130 | 30 | 23.1% | 17885 | 10.0% |
| $0.72 | 126 | 26 | 20.6% | 16549 | 8.8% |
| $0.74 | 125 | 25 | 20.0% | 15431 | 8.0% |
| $0.76 | 119 | 19 | 16.0% | 14431 | 7.4% |
| $0.78 | 118 | 18 | 15.3% | 13350 | 6.3% |
| $0.80 | 114 | 14 | 12.3% | 12358 | 5.3% |
| $0.81 | 113 | 13 | 11.5% | 11768 | 5.0% |
| $0.82 | 113 | 13 | 11.5% | 11264 | 4.8% |
| $0.83 | 113 | 13 | 11.5% | 10770 | 4.4% |
| $0.84 | 113 | 13 | 11.5% | 10392 | 4.0% |
| $0.85 | 112 | 12 | 10.7% | 10040 | 3.7% |
| $0.86 | 111 | 11 | 9.9% | 9719 | 3.3% |
| $0.87 | 111 | 11 | 9.9% | 9304 | 3.0% |
| $0.88 | 110 | 10 | 9.1% | 8931 | 1.8% |
| $0.89 | 108 | 8 | 7.4% | 8443 | 1.6% |
| $0.90 | 108 | 8 | 7.4% | 8000 | 0.9% |
| $0.91 | 107 | 7 | 6.5% | 7671 | 0.5% |
| $0.92 | 105 | 5 | 4.8% | 7358 | 0.3% |
| $0.93 | 104 | 4 | 3.8% | 6946 | 0.2% |
| $0.94 | 102 | 2 | 2.0% | 6437 | 0.1% |
| $0.95 | 101 | 1 | 1.0% | 5895 | 0.1% |
| $0.96 | 101 | 1 | 1.0% | 5361 | 0.1% |
| $0.97 | 101 | 1 | 1.0% | 4819 | 0.1% |
| $0.98 | 101 | 1 | 1.0% | 4216 | 0.1% |
| $0.99 | 100 | 0 | 0.0% | 3146 | 0.0% |

### Underdog side (n=165 competitive games)

| Price level | Games reaching | Eventual losses | Loss rate | Cum bins above | Weighted loss rate |
|---:|---:|---:|---:|---:|---:|
| $0.50 | 122 | 57 | 46.7% | 14743 | 23.4% |
| $0.52 | 118 | 53 | 44.9% | 13680 | 21.5% |
| $0.54 | 112 | 47 | 42.0% | 12901 | 20.3% |
| $0.56 | 105 | 40 | 38.1% | 12088 | 18.8% |
| $0.58 | 100 | 35 | 35.0% | 11443 | 17.5% |
| $0.60 | 98 | 33 | 33.7% | 10811 | 16.4% |
| $0.62 | 92 | 27 | 29.3% | 10199 | 15.7% |
| $0.64 | 90 | 25 | 27.8% | 9631 | 15.0% |
| $0.66 | 87 | 22 | 25.3% | 9076 | 14.6% |
| $0.68 | 86 | 21 | 24.4% | 8582 | 14.3% |
| $0.70 | 86 | 21 | 24.4% | 8032 | 13.4% |
| $0.72 | 85 | 20 | 23.5% | 7491 | 11.9% |
| $0.74 | 83 | 18 | 21.7% | 6987 | 10.7% |
| $0.76 | 81 | 16 | 19.8% | 6455 | 9.1% |
| $0.78 | 81 | 16 | 19.8% | 5922 | 8.5% |
| $0.80 | 79 | 14 | 17.7% | 5438 | 7.3% |
| $0.81 | 79 | 14 | 17.7% | 5218 | 6.6% |
| $0.82 | 79 | 14 | 17.7% | 4963 | 6.0% |
| $0.83 | 79 | 14 | 17.7% | 4718 | 4.6% |
| $0.84 | 78 | 13 | 16.7% | 4500 | 4.1% |
| $0.85 | 76 | 11 | 14.5% | 4261 | 3.9% |
| $0.86 | 73 | 8 | 11.0% | 4092 | 3.8% |
| $0.87 | 72 | 7 | 9.7% | 3973 | 3.6% |
| $0.88 | 72 | 7 | 9.7% | 3827 | 3.4% |
| $0.89 | 71 | 6 | 8.5% | 3653 | 3.1% |
| $0.90 | 71 | 6 | 8.5% | 3515 | 3.0% |
| $0.91 | 71 | 6 | 8.5% | 3378 | 2.2% |
| $0.92 | 71 | 6 | 8.5% | 3248 | 1.8% |
| $0.93 | 71 | 6 | 8.5% | 3087 | 1.3% |
| $0.94 | 70 | 5 | 7.1% | 2916 | 0.8% |
| $0.95 | 68 | 3 | 4.4% | 2720 | 0.2% |
| $0.96 | 66 | 1 | 1.5% | 2514 | 0.1% |
| $0.97 | 65 | 0 | 0.0% | 2252 | 0.0% |
| $0.98 | 64 | 0 | 0.0% | 1982 | 0.0% |
| $0.99 | 64 | 0 | 0.0% | 1689 | 0.0% |

## Part 2 — Favorite Dip-Recovery (Strategy 4A)

Sweep 1,200 configurations. Entry fires on a dip from a trailing maximum within the specified zone, exit at target price or stop-loss. Unclosed positions resolve at game end.

### 2A — Top 20 configs by annual EV (favorite dip-recovery)

| Rank | Lookback | Dip | Entry zone | Exit | Stop | Entries | Hit% | Stop% | Held% | Mean P&L | Annual EV |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 180s | $0.08 | $0.50–$0.75 | $0.90 | $0.40 | 161 | 53% | 47% | 0% | $+3.53 | $+1,886 |
| 2 | 300s | $0.05 | $0.50–$0.75 | $0.90 | $0.40 | 198 | 50% | 50% | 0% | $+2.81 | $+1,844 |
| 3 | 180s | $0.05 | $0.50–$0.75 | $0.90 | $0.40 | 194 | 51% | 49% | 0% | $+2.86 | $+1,839 |
| 4 | 120s | $0.05 | $0.50–$0.75 | $0.90 | $0.40 | 188 | 51% | 49% | 0% | $+2.95 | $+1,838 |
| 5 | 300s | $0.08 | $0.50–$0.75 | $0.90 | $0.40 | 170 | 52% | 48% | 0% | $+3.25 | $+1,833 |
| 6 | 120s | $0.05 | $0.50–$0.75 | $0.85 | $0.40 | 203 | 57% | 43% | 0% | $+2.56 | $+1,721 |
| 7 | 180s | $0.05 | $0.50–$0.75 | $0.85 | $0.40 | 208 | 57% | 43% | 0% | $+2.26 | $+1,562 |
| 8 | 300s | $0.05 | $0.50–$0.75 | $0.85 | $0.40 | 212 | 56% | 44% | 0% | $+2.18 | $+1,533 |
| 9 | 120s | $0.08 | $0.50–$0.75 | $0.90 | $0.40 | 138 | 53% | 47% | 0% | $+3.25 | $+1,490 |
| 10 | 300s | $0.05 | $0.50–$0.60 | $0.95 | $0.40 | 164 | 37% | 63% | 0% | $+2.54 | $+1,384 |
| 11 | 300s | $0.05 | $0.50–$0.75 | $0.95 | $0.40 | 186 | 44% | 56% | 0% | $+2.16 | $+1,330 |
| 12 | 300s | $0.10 | $0.60–$0.70 | $0.90 | $0.40 | 91 | 60% | 40% | 0% | $+4.40 | $+1,327 |
| 13 | 180s | $0.08 | $0.55–$0.65 | $0.90 | $0.40 | 118 | 50% | 50% | 0% | $+3.36 | $+1,317 |
| 14 | 180s | $0.05 | $0.50–$0.60 | $0.90 | $0.40 | 161 | 40% | 60% | 0% | $+2.46 | $+1,316 |
| 15 | 300s | $0.05 | $0.50–$0.75 | $0.92 | $0.40 | 195 | 47% | 53% | 0% | $+1.99 | $+1,287 |
| 16 | 180s | $0.08 | $0.50–$0.75 | $0.92 | $0.40 | 157 | 48% | 52% | 0% | $+2.46 | $+1,279 |
| 17 | 300s | $0.08 | $0.50–$0.75 | $0.95 | $0.40 | 159 | 46% | 54% | 0% | $+2.41 | $+1,273 |
| 18 | 180s | $0.08 | $0.50–$0.75 | $0.95 | $0.40 | 150 | 46% | 54% | 0% | $+2.53 | $+1,256 |
| 19 | 300s | $0.08 | $0.50–$0.75 | $0.92 | $0.40 | 166 | 48% | 52% | 0% | $+2.26 | $+1,246 |
| 20 | 300s | $0.05 | $0.50–$0.60 | $0.90 | $0.40 | 168 | 40% | 60% | 0% | $+2.23 | $+1,245 |

### 2B — Best config detail

- Lookback: 180s
- Dip depth: $0.08
- Entry zone: $0.50–$0.75
- Exit target: $0.90
- Stop-loss: $0.40

#### Outcome distribution

| Outcome | Count | % | Mean P&L |
|---|---:|---:|---:|
| Hit target | 85 | 52.8% | $+27.74 |
| Stopped out | 76 | 47.2% | $-23.54 |
| Resolution win (held) | 0 | 0.0% | — |
| Resolution loss (held) | 0 | 0.0% | — |
| Resolution mid (held) | 0 | 0.0% | — |
| **ALL** | **161** | 100.0% | **$+3.53** |

#### P&L distribution

| Bucket | Count | % |
|---|---:|---:|
| < −$30 | 19 | 11.8% |
| −$30 to −$10 | 57 | 35.4% |
| −$10 to $0 | 0 | 0.0% |
| $0 to $10 | 0 | 0.0% |
| $10 to $20 | 16 | 9.9% |
| $20 to $30 | 38 | 23.6% |
| > $30 | 31 | 19.3% |

#### By entry period

| Period | Entries | Hit% | Stop% | Mean P&L |
|---|---:|---:|---:|---:|
| Q1 | 47 | 47% | 53% | $+4.00 |
| Q2 | 49 | 47% | 53% | $+1.59 |
| Q3 | 27 | 67% | 33% | $+8.51 |
| Q4 | 37 | 59% | 41% | $+3.09 |
| OT | 1 | 0% | 100% | $-41.13 |

#### By spread bucket

| |Spread| | Entries | Mean P&L |
|---|---:|---:|
| 1–2 | 28 | $+0.99 |
| 2.5–3.5 | 71 | $+2.57 |
| 4–5 | 26 | $+5.70 |
| 5.5–6 | 36 | $+5.85 |

**Mean hold time:** 76.0 bins × 30s = 38.0 minutes of game clock.

**Re-entries:** 41 of 161 total (25.5%).

### 2C — Sensitivity around best config

For each parameter, show how mean P&L changes when we vary only that parameter around the best config's value.

#### Vary Lookback

| Lookback | Entries | Mean P&L | Annual EV |
|---|---:|---:|---:|
| 120s | 138 | $+3.25 | $+1,490 |
| 180s | 161 | $+3.53 | $+1,886 |
| 300s | 170 | $+3.25 | $+1,833 |

#### Vary Dip depth

| Dip depth | Entries | Mean P&L | Annual EV |
|---|---:|---:|---:|
| $0.05 | 194 | $+2.86 | $+1,839 |
| $0.08 | 161 | $+3.53 | $+1,886 |
| $0.10 | 122 | $+2.95 | $+1,195 |
| $0.15 | 57 | $+0.96 | $+181 |
| $0.20 | 32 | $-0.69 | $-73 |

#### Vary Entry zone

| Entry zone | Entries | Mean P&L | Annual EV |
|---|---:|---:|---:|
| $0.50–$0.60 | 124 | $+2.07 | $+852 |
| $0.55–$0.65 | 118 | $+3.36 | $+1,317 |
| $0.60–$0.70 | 101 | $+3.18 | $+1,067 |
| $0.50–$0.75 | 161 | $+3.53 | $+1,886 |

#### Vary Exit target

| Exit target | Entries | Mean P&L | Annual EV |
|---|---:|---:|---:|
| $0.80 | 181 | $+1.43 | $+858 |
| $0.85 | 171 | $+1.99 | $+1,130 |
| $0.90 | 161 | $+3.53 | $+1,886 |
| $0.92 | 157 | $+2.46 | $+1,279 |
| $0.95 | 150 | $+2.53 | $+1,256 |

#### Vary Stop-loss

| Stop-loss | Entries | Mean P&L | Annual EV |
|---|---:|---:|---:|
| $0.40 | 161 | $+3.53 | $+1,886 |
| $0.45 | 166 | $+1.76 | $+968 |
| $0.48 | 172 | $+1.45 | $+826 |
| $0.50 | 180 | $+0.78 | $+465 |

## Part 3 — Underdog Run-Capture (Strategy 4B)

Entry detection on the underdog's Kalshi price. Static mode: buy in band, no momentum requirement. Momentum mode: buy in band only when price has risen ≥ run_size from trailing min.

### 3A — Top 20 underdog swing configs by annual EV

| Rank | Label | Entries | Hit% | Stop% | Held% | Mean P&L | Annual EV |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | mom $0.10-$0.20 run$0.05 lb120s +$0.10 | 71 | 46% | 54% | 0% | $+1.99 | $+469 |
| 2 | mom $0.25-$0.35 run$0.03 lb300s +$0.20 | 188 | 27% | 73% | 0% | $+0.74 | $+461 |
| 3 | mom $0.10-$0.20 run$0.05 lb120s +$0.15 | 70 | 37% | 63% | 0% | $+1.94 | $+451 |
| 4 | mom $0.10-$0.20 run$0.05 lb300s +$0.15 | 96 | 33% | 67% | 0% | $+1.20 | $+382 |
| 5 | mom $0.10-$0.20 run$0.05 lb300s +$0.10 | 99 | 42% | 58% | 0% | $+1.11 | $+364 |
| 6 | mom $0.10-$0.20 run$0.05 lb300s +$0.20 | 96 | 27% | 73% | 0% | $+1.08 | $+343 |
| 7 | mom $0.10-$0.20 run$0.05 lb180s +$0.10 | 88 | 42% | 58% | 0% | $+1.12 | $+328 |
| 8 | mom $0.10-$0.20 run$0.08 lb120s +$0.15 | 22 | 45% | 55% | 0% | $+3.95 | $+288 |
| 9 | mom $0.10-$0.20 run$0.05 lb180s +$0.15 | 86 | 33% | 67% | 0% | $+0.96 | $+272 |
| 10 | mom $0.10-$0.20 run$0.05 lb120s +$0.20 | 70 | 27% | 73% | 0% | $+1.08 | $+251 |
| 11 | mom $0.10-$0.20 run$0.08 lb120s +$0.10 | 22 | 50% | 50% | 0% | $+3.32 | $+242 |
| 12 | mom $0.10-$0.20 run$0.05 lb180s +$0.05 | 91 | 56% | 44% | 0% | $+0.77 | $+233 |
| 13 | mom $0.10-$0.20 run$0.05 lb300s +$0.05 | 105 | 55% | 45% | 0% | $+0.67 | $+232 |
| 14 | mom $0.10-$0.20 run$0.05 lb120s +$0.05 | 74 | 57% | 43% | 0% | $+0.92 | $+227 |
| 15 | mom $0.25-$0.35 run$0.03 lb180s +$0.20 | 183 | 26% | 74% | 0% | $+0.36 | $+219 |
| 16 | mom $0.25-$0.35 run$0.03 lb300s +$0.10 | 194 | 40% | 60% | 0% | $+0.30 | $+192 |
| 17 | mom $0.10-$0.20 run$0.08 lb180s +$0.10 | 36 | 44% | 56% | 0% | $+1.21 | $+144 |
| 18 | mom $0.10-$0.20 run$0.08 lb180s +$0.15 | 36 | 36% | 64% | 0% | $+1.06 | $+126 |
| 19 | mom $0.25-$0.35 run$0.03 lb180s +$0.10 | 189 | 40% | 60% | 0% | $+0.19 | $+121 |
| 20 | mom $0.25-$0.35 run$0.03 lb300s +$0.15 | 190 | 30% | 70% | 0% | $+0.12 | $+73 |

### 3B — Top 10 underdog hybrid configs

| Rank | Label | Entries | Hit% | Stop% | Held% | Mean P&L | Annual EV |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | mom $0.25-$0.35 run$0.03 lb300s +$0.20 [hybrid 50/50] | 182 | 0% | 71% | 29% | $+1.83 | $+1,105 |
| 2 | mom $0.10-$0.20 run$0.05 lb300s +$0.15 [hybrid 50/50] | 95 | 0% | 66% | 34% | $+1.25 | $+395 |
| 3 | mom $0.10-$0.20 run$0.05 lb300s +$0.20 [hybrid 50/50] | 95 | 0% | 73% | 27% | $+1.19 | $+376 |
| 4 | mom $0.10-$0.20 run$0.05 lb300s +$0.10 [hybrid 50/50] | 95 | 0% | 57% | 43% | $+1.14 | $+360 |
| 5 | mom $0.10-$0.20 run$0.08 lb120s +$0.15 [hybrid 50/50] | 22 | 0% | 55% | 45% | $+3.61 | $+263 |
| 6 | mom $0.10-$0.20 run$0.05 lb120s +$0.15 [hybrid 50/50] | 69 | 0% | 62% | 38% | $+1.13 | $+260 |
| 7 | mom $0.10-$0.20 run$0.05 lb120s +$0.10 [hybrid 50/50] | 69 | 0% | 55% | 45% | $+0.92 | $+211 |
| 8 | mom $0.10-$0.20 run$0.05 lb120s +$0.20 [hybrid 50/50] | 69 | 0% | 72% | 28% | $+0.70 | $+160 |
| 9 | mom $0.10-$0.20 run$0.05 lb180s +$0.15 [hybrid 50/50] | 85 | 0% | 67% | 33% | $+0.04 | $+11 |
| 10 | mom $0.10-$0.20 run$0.05 lb180s +$0.10 [hybrid 50/50] | 85 | 0% | 58% | 42% | $+0.02 | $+5 |

### 3C — Best underdog config detail

- mom $0.25-$0.35 run$0.03 lb300s +$0.20 [hybrid 50/50]
- Mode: momentum
- Entry band: $0.25–$0.35
- Exit offset: +$0.20; stop: −$0.05
- Hybrid (50% hold to resolution): True

#### Outcome distribution

| Exit type | Count | % | Mean P&L |
|---|---:|---:|---:|
| hybrid_resolution_win | 23 | 12.6% | $+46.69 |
| hybrid_stop_after_partial | 29 | 15.9% | $+6.24 |
| stop | 130 | 71.4% | $-7.09 |

### 3D — Resolution lottery math (underdog)

For each entry price band: what fraction of underdog entries resolve at $1.00 (underdog wins outright), and what's the mean resolution P&L if held from that band to the end?

| Entry band | Bin count | Dog-win rate | Mean resolution P&L |
|---|---:|---:|---:|
| $0.10–$0.15 | 2,038 | 14.4% | $+1.88 |
| $0.15–$0.20 | 2,320 | 12.5% | $-5.00 |
| $0.20–$0.25 | 2,595 | 18.8% | $-3.69 |
| $0.25–$0.30 | 2,930 | 21.7% | $-5.79 |
| $0.30–$0.35 | 3,325 | 33.2% | $+0.73 |

## Part 4 — Cross-Strategy Comparison

| Strategy | Entries/yr | Mean P&L | Annual EV | Max loss | Win rate |
|---|---:|---:|---:|---:|---:|
| S3 naive (baseline) | ~1,404 | −$4.22 | −$5,963 | −$40 | 26% |
| S3 best filtered | ~170 | +$3.41 | +$578 | −$28 | 22% |
| S1 bilateral | ~84 | +$19.14 | +$1,608 | $0 | 100% |
| **S4A best fav config** | ~533 | $+3.53 | $+1,886 | $-43.60 | 53% |
| **S4B best dog config** | ~603 | $+1.83 | $+1,105 | $-13.71 | 0% |
| **S4A + S4B + S3-filtered + S1** | — | — | $+5,178 | — | — |

## Part 5 — Prior-Weighting Analysis

Tests whether measuring entry price against the pre-game Kalshi price improves S4A. Thesis: entries deeper below the market's prior (pre-game) expectation should recover more reliably because the gap to mean-revert to is larger.

**Pre-game price definition:** last non-NaN fav_kalshi_vwap in the pre-tip region (where game_seconds_elapsed is NaN) of each game's raw timeseries. Falls back to the first live bin's price if no pre-tip bins exist.

### 5A — Dip-below-prior distribution (best S4A config)

Best S4A config: 180s lookback, $0.08 dip, $0.50–$0.75 entry, $0.90 exit, $0.40 stop.

| Dip below prior | Count | % of entries |
|---|---:|---:|
| < $0.00 (above prior) | 82 | 50.9% |
| $0.00–$0.05 | 35 | 21.7% |
| $0.05–$0.10 | 32 | 19.9% |
| $0.10–$0.15 | 11 | 6.8% |
| $0.15–$0.20 | 1 | 0.6% |
| $0.20–$0.25 | 0 | 0.0% |
| > $0.25 | 0 | 0.0% |

### 5B — Hit rate and P&L by dip-below-prior bin

| Dip below prior | Entries | Hit% | Stop% | Mean P&L | Median P&L |
|---|---:|---:|---:|---:|---:|
| < $0.00 (above prior) | 82 | 62% | 38% | $+4.32 | $+18.17 |
| $0.00–$0.05 | 35 | 49% | 51% | $+2.75 | $-12.90 |
| $0.05–$0.10 | 32 | 34% | 66% | $+0.14 | $-14.18 |
| $0.10–$0.15 | 11 | 55% | 45% | $+11.70 | $+30.15 |
| $0.15–$0.20 | 1 | 0% | 100% | $-14.63 | $-14.63 |
| $0.20–$0.25 | 0 | — | — | — | — |
| > $0.25 | 0 | — | — | — | — |

### 5C — Prior-filtered S4A sweep (best config)

Sweep `Min dip below prior` threshold. Apply `dip_below_prior >= threshold` filter to entries from the best S4A config. Post-hoc filter on detected entries.

| Dip below prior (min) | Entries | Hit% | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|
| ≥ $0.00 | 79 | 43% | $+2.72 | $+713 |
| ≥ $0.03 | 59 | 42% | $+3.16 | $+618 |
| ≥ $0.05 | 44 | 39% | $+2.69 | $+393 |
| ≥ $0.08 | 21 | 43% | $+6.67 | $+464 |
| ≥ $0.10 | 12 | 50% | $+9.50 | $+378 |
| ≥ $0.12 | 5 | 40% | $+4.88 | $+81 |
| ≥ $0.15 | 1 | 0% | $-14.63 | $-49 |
| ≥ $0.18 | 1 | 0% | $-14.63 | $-49 |
| ≥ $0.20 | 0 | 0% | $+0.00 | $+0 |

**Best prior-filter threshold (≥20 entries retained): $0.00** — mean P&L $+2.72, annual EV $+713.

### 5D — Best threshold (≥ $0.00) applied to top 5 S4A configs

| Rank | Config | Entries (unfilt) | Entries (filt) | Mean P&L (unfilt) | Mean P&L (filt) | Annual EV (filt) |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 180s / $0.08 / $0.50–$0.75 / $0.90 / $0.40 | 161 | 79 | $+3.53 | $+2.72 | $+713 |
| 2 | 300s / $0.05 / $0.50–$0.75 / $0.90 / $0.40 | 198 | 103 | $+2.81 | $+5.69 | $+1,943 |
| 3 | 180s / $0.05 / $0.50–$0.75 / $0.90 / $0.40 | 194 | 98 | $+2.86 | $+4.53 | $+1,472 |
| 4 | 120s / $0.05 / $0.50–$0.75 / $0.90 / $0.40 | 188 | 92 | $+2.95 | $+3.65 | $+1,114 |
| 5 | 300s / $0.08 / $0.50–$0.75 / $0.90 / $0.40 | 170 | 81 | $+3.25 | $+3.66 | $+984 |

### 5E — Underdog run-above-prior (best S4B config)

Best S4B config: mom $0.25-$0.35 run$0.03 lb300s +$0.20 [hybrid 50/50]. For each underdog entry, `run_above_prior = entry_price − pre_game_dog_price` where pre-game dog price = 1 − pre_game_fav_price.

| Run above prior | Entries | Hit% | Mean P&L |
|---|---:|---:|---:|
| < $0.00 (below prior) | 168 | 0% | $+1.81 |
| $0.00–$0.03 | 9 | 0% | $-3.83 |
| $0.03–$0.06 | 4 | 0% | $+4.92 |
| $0.06–$0.10 | 1 | 0% | $+43.51 |
| > $0.10 | 0 | — | — |

### 5F — Summary

- **Dip-below-prior vs hit rate/P&L (5B):** relationship is non-monotonic — effect is not a simple 'deeper dip = better recovery' story.
- **Best prior filter (5C):** ≥ $0.00. Annual EV $+713 (reduction of $+0 vs unfiltered baseline $+713). Retained 79 of 79 entries.
- **Cross-config consistency (5D):** see table above. If filtered mean P&L exceeds unfiltered mean P&L for all top-5 configs, the effect is robust across the config neighborhood.
- **Underdog run-above-prior (5E):** insufficient bin coverage to draw a conclusion.

## Part 6 — Position Management Study

Tests averaging-in and averaging-out overlays on the best S4A config (180s / $0.08 dip / $0.50–$0.75 entry / $0.90 exit / $0.40 stop). Baseline has 47% stop-out rate; can scaling convert some of those into smaller losses or partial wins?

### 6A — Averaging-in configs

| Config | Entries | Avg-in fired | Avg basis | Hit% | Stop% | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| Config A (baseline 100/100) | 161 | 0% | $0.6180 | 53% | 47% | $+3.53 | $+1,886 |
| Config B (50/50 add +$0.05) | 161 | 69% | $0.5939 | 53% | 47% | $+1.82 | $+971 |
| Config C (50/50 add +$0.08) | 161 | 60% | $0.5879 | 53% | 47% | $+2.14 | $+1,143 |
| Config D (50/50 add +$0.03) | 161 | 77% | $0.5990 | 53% | 47% | $+2.18 | $+1,166 |
| Config E (33/33/34 triple) | 161 | 69% | $0.5782 | 53% | 47% | $+1.05 | $+558 |
| Config F (25/75 conviction) | 161 | 69% | $0.5818 | 53% | 47% | $+0.96 | $+514 |

### 6B — Averaging-out configs

Fractional exits at ascending price targets. Stop applies to whatever remains held.

| Config | Entries | Full exit% | Partial+stop% | Full stop% | Mean P&L | Median P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| Config G (baseline 100 @ $0.90) | 161 | 53% | 0% | 47% | $+3.53 | $+17.48 | $+1,886 |
| Config H (50 @ $0.80 / 50 @ $0.90) | 161 | 53% | 7% | 40% | $+2.68 | $+12.03 | $+1,429 |
| Config I (50 @ $0.85 / 50 @ $0.95) | 150 | 46% | 9% | 45% | $+2.80 | $-4.61 | $+1,391 |
| Config J (50 @ $0.80 / 50 @ $0.95) | 150 | 46% | 13% | 41% | $+2.32 | $-2.22 | $+1,152 |
| Config K (33/33/34 ladder 0.80/0.90/0.95) | 150 | 46% | 13% | 41% | $+2.88 | $-0.05 | $+1,433 |
| Config L (25/50/25 pyramid 0.80/0.90/0.95) | 150 | 46% | 13% | 41% | $+3.15 | $+5.53 | $+1,569 |
| Config M (75 @ $0.85 / 25 @ $0.95) | 150 | 46% | 9% | 45% | $+2.92 | $+7.72 | $+1,454 |

### 6C — Combined averaging-in × averaging-out

| Config | Entries | Avg-in fired | Mean basis | Full exit% | Partial+stop% | Full stop% | Mean P&L | Median P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Config N (best × best: A baseline × G baseline) | 161 | 0% | $0.6180 | 53% | 0% | 47% | $+3.53 | $+17.48 | $+1,886 |
| Config O (B × H: 50/50 in +$0.05 × 50@0.80/50@0.90) | 156 | 74% | $0.5882 | 24% | 10% | 42% | $+0.82 | $+3.27 | $+423 |
| Config P (F × M: 25/75 conviction × 75@0.85/25@0.95) | 149 | 74% | $0.5696 | 21% | 10% | 44% | $+0.94 | $+3.50 | $+465 |
| Config Q (E × K: fully symmetric 33/33/34 × 33/33/34) | 147 | 76% | $0.5648 | 10% | 13% | 41% | $+0.78 | $+1.90 | $+380 |

### 6D — Best combined config detail: N best × best

**Config N (best × best: A baseline × G baseline)**

Entries: **161**, Mean P&L: **$+3.53**, Annual EV: **$+1,886**, Max loss: $-43.60.

#### Outcome distribution

| Outcome | Count | % | Mean P&L |
|---|---:|---:|---:|
| Full exit (all targets hit) | 85 | 52.8% | $+27.74 |
| Partial then stop | 0 | 0.0% | — |
| Full stop (no partial hit) | 76 | 47.2% | $-23.54 |
| Resolution win | 0 | 0.0% | — |
| Resolution loss | 0 | 0.0% | — |
| Resolution mid | 0 | 0.0% | — |

#### P&L distribution

| Bucket | Count | % |
|---|---:|---:|
| < −$30 | 19 | 11.8% |
| −$30 to −$10 | 57 | 35.4% |
| −$10 to $0 | 0 | 0.0% |
| $0 to $10 | 0 | 0.0% |
| $10 to $20 | 16 | 9.9% |
| $20 to $30 | 38 | 23.6% |
| > $30 | 31 | 19.3% |

#### By entry period

| Period | Entries | Hit% | Mean P&L |
|---|---:|---:|---:|
| Q1 | 47 | 47% | $+4.00 |
| Q2 | 49 | 47% | $+1.59 |
| Q3 | 27 | 67% | $+8.51 |
| Q4 | 37 | 59% | $+3.09 |
| OT | 1 | 0% | $-41.13 |

#### By spread bucket

| |Spread| | Entries | Mean P&L |
|---|---:|---:|
| 1–2 | 28 | $+0.99 |
| 2.5–3.5 | 71 | $+2.57 |
| 4–5 | 26 | $+5.70 |
| 5.5–6 | 36 | $+5.85 |

**Mean hold time:** 76.0 bins × 30s = 38.0 minutes of game clock.

#### Baseline vs best combined

| Metric | Baseline (A/G) | Best combined |
|---|---:|---:|
| Entries | 161 | 161 |
| Hit% | 52.8% | 52.8% |
| Stop% | 47.2% | 47.2% |
| Partial+stop% | 0.0% | 0.0% |
| Mean P&L | $+3.53 | $+3.53 |
| Annual EV | $+1,886 | $+1,886 |
| Max loss | $-43.60 | $-43.60 |

### 6E — Strategy evolution table (updated)

| Strategy | Entries/yr | Mean P&L | Annual EV | Max loss | Win rate |
|---|---:|---:|---:|---:|---:|
| S4A baseline (100 @ trigger, 100% @ $0.90) | ~533 | $+3.53 | $+1,886 | $-43.60 | 53% |
| S4A + best avg-in only (A baseline) | ~533 | $+3.53 | $+1,886 | $-43.60 | 53% |
| S4A + best avg-out only (G baseline) | ~533 | $+3.53 | $+1,886 | $-43.60 | 53% |
| **S4A best combined (N best × best)** | ~533 | **$+3.53** | **$+1,886** | $-43.60 | 53% |
| S1 bilateral | ~84 | +$19.14 | +$1,608 | $0 | 100% |
| **S4A best combined + S1 bilateral** | — | — | **$+3,494** | — | — |

