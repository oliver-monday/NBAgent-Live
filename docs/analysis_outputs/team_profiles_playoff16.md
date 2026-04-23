# Team-Level In-Game Profiles — 2025-26 Playoff 16
_Generated: 2026-04-23T06:28:55.787837+00:00_
Observational scouting report on **404 games** from the Kalshi-confirmed paired dataset. For each of the 16 teams in the 2025-26 NBA playoffs, characterizes in-game Kalshi price behavior as favorite and as underdog, then overlays S4A entry data to surface team-level hit rate dispersion.

**Teams:** DET, BOS, NYK, CLE, TOR, ATL, PHI, ORL, OKC, SAS, DEN, LAL, HOU, MIN, POR, PHX.

**Data approximation:** dog-side YES bid is computed as `1 − fav_kalshi_vwap` (same as prior analyses). No strategy simulation at the aggregate level — this is a profile, not a strategy test.

## Section 1 — Game counts and role distribution
| Team | Games | As fav | As dog | Fav % | Mean fav open | Mean dog open |
|---|---:|---:|---:|---:|---:|---:|
| ORL | 30 | 13 | 17 | 43.3% | $0.787 | $0.382 |
| DET | 29 | 23 | 6 | 79.3% | $0.713 | $0.393 |
| PHI | 29 | 16 | 13 | 55.2% | $0.685 | $0.225 |
| HOU | 28 | 24 | 4 | 85.7% | $0.713 | $0.393 |
| PHX | 28 | 14 | 14 | 50.0% | $0.719 | $0.338 |
| BOS | 27 | 20 | 7 | 74.1% | $0.765 | $0.357 |
| LAL | 27 | 16 | 11 | 59.3% | $0.730 | $0.414 |
| NYK | 26 | 19 | 7 | 73.1% | $0.739 | $0.370 |
| CLE | 26 | 21 | 5 | 80.8% | $0.765 | $0.297 |
| TOR | 26 | 16 | 10 | 61.5% | $0.718 | $0.341 |
| SAS | 26 | 25 | 1 | 96.2% | $0.747 | $0.476 |
| MIN | 26 | 16 | 10 | 61.5% | $0.695 | $0.320 |
| POR | 26 | 16 | 10 | 61.5% | $0.761 | $0.360 |
| ATL | 25 | 17 | 8 | 68.0% | $0.749 | $0.396 |
| OKC | 25 | 22 | 3 | 88.0% | $0.801 | $0.396 |
| DEN | 25 | 19 | 6 | 76.0% | $0.744 | $0.444 |

## Section 2 — In-game volatility profiles

### 2A. Price range (max − min) per game

| Team | Role | Games | Mean range | Median | P25 | P75 |
|---|---|---:|---:|---:|---:|---:|
| DET | fav | 23 | $0.410 | $0.427 | $0.117 | $0.585 |
| DET | dog | 6 | $0.611 | $0.676 | $0.532 | $0.686 |
| BOS | fav | 20 | $0.408 | $0.411 | $0.199 | $0.594 |
| BOS | dog | 7 | $0.654 | $0.622 | $0.548 | $0.722 |
| NYK | fav | 19 | $0.443 | $0.468 | $0.274 | $0.586 |
| NYK | dog | 7 | $0.453 | $0.444 | $0.360 | $0.539 |
| CLE | fav | 21 | $0.451 | $0.360 | $0.325 | $0.604 |
| CLE | dog | 5 | $0.516 | $0.533 | $0.288 | $0.614 |
| TOR | fav | 16 | $0.431 | $0.401 | $0.255 | $0.617 |
| TOR | dog | 10 | $0.519 | $0.461 | $0.386 | $0.629 |
| ATL | fav | 17 | $0.345 | $0.293 | $0.216 | $0.451 |
| ATL | dog | 8 | $0.548 | $0.593 | $0.466 | $0.649 |
| PHI | fav | 16 | $0.508 | $0.499 | $0.323 | $0.687 |
| PHI | dog | 13 | $0.414 | $0.337 | $0.186 | $0.607 |
| ORL | fav | 13 | $0.481 | $0.382 | $0.264 | $0.771 |
| ORL | dog | 17 | $0.640 | $0.580 | $0.510 | $0.810 |
| OKC | fav | 22 | $0.363 | $0.319 | $0.134 | $0.548 |
| OKC | dog | 3 | $0.531 | $0.462 | $0.458 | $0.570 |
| SAS | fav | 25 | $0.394 | $0.337 | $0.138 | $0.552 |
| SAS | dog | 1 | $0.643 | $0.643 | $0.643 | $0.643 |
| DEN | fav | 19 | $0.526 | $0.466 | $0.320 | $0.763 |
| DEN | dog | 6 | $0.738 | $0.694 | $0.638 | $0.873 |
| LAL | fav | 16 | $0.460 | $0.429 | $0.202 | $0.684 |
| LAL | dog | 11 | $0.556 | $0.541 | $0.460 | $0.712 |
| HOU | fav | 24 | $0.524 | $0.569 | $0.192 | $0.820 |
| HOU | dog | 4 | $0.633 | $0.611 | $0.373 | $0.871 |
| MIN | fav | 16 | $0.466 | $0.457 | $0.327 | $0.620 |
| MIN | dog | 10 | $0.645 | $0.608 | $0.517 | $0.828 |
| POR | fav | 16 | $0.391 | $0.399 | $0.160 | $0.561 |
| POR | dog | 10 | $0.620 | $0.655 | $0.444 | $0.802 |
| PHX | fav | 14 | $0.561 | $0.521 | $0.343 | $0.835 |
| PHX | dog | 14 | $0.623 | $0.600 | $0.516 | $0.743 |

### 2B. Mean $0.10+ swings per game

| Team | Role | Games | Mean swings | Median |
|---|---|---:|---:|---:|
| DET | fav | 23 | 4.65 | 3.0 |
| DET | dog | 6 | 6.67 | 4.0 |
| BOS | fav | 20 | 3.20 | 2.5 |
| BOS | dog | 7 | 9.14 | 8.0 |
| NYK | fav | 19 | 5.00 | 6.0 |
| NYK | dog | 7 | 5.86 | 5.0 |
| CLE | fav | 21 | 5.05 | 4.0 |
| CLE | dog | 5 | 7.20 | 4.0 |
| TOR | fav | 16 | 4.62 | 3.5 |
| TOR | dog | 10 | 7.40 | 6.5 |
| ATL | fav | 17 | 3.82 | 3.0 |
| ATL | dog | 8 | 7.00 | 6.5 |
| PHI | fav | 16 | 6.38 | 6.5 |
| PHI | dog | 13 | 4.38 | 3.0 |
| ORL | fav | 13 | 5.92 | 4.0 |
| ORL | dog | 17 | 8.18 | 7.0 |
| OKC | fav | 22 | 5.09 | 4.5 |
| OKC | dog | 3 | 6.33 | 7.0 |
| SAS | fav | 25 | 4.92 | 3.0 |
| SAS | dog | 1 | 9.00 | 9.0 |
| DEN | fav | 19 | 8.53 | 8.0 |
| DEN | dog | 6 | 9.83 | 12.0 |
| LAL | fav | 16 | 6.38 | 3.0 |
| LAL | dog | 11 | 6.27 | 5.0 |
| HOU | fav | 24 | 6.79 | 5.5 |
| HOU | dog | 4 | 6.25 | 6.0 |
| MIN | fav | 16 | 5.12 | 4.5 |
| MIN | dog | 10 | 8.20 | 7.0 |
| POR | fav | 16 | 4.00 | 3.5 |
| POR | dog | 10 | 8.40 | 6.5 |
| PHX | fav | 14 | 8.29 | 8.0 |
| PHX | dog | 14 | 7.07 | 6.0 |

### 2C. $0.50 crossover rate

| Team | Role | Games | Cross $0.50 % of games | Mean crossings/game |
|---|---|---:|---:|---:|
| DET | fav | 23 | 43.5% | 2.35 |
| DET | dog | 6 | 66.7% | 5.50 |
| BOS | fav | 20 | 45.0% | 2.75 |
| BOS | dog | 7 | 85.7% | 8.00 |
| NYK | fav | 19 | 47.4% | 2.79 |
| NYK | dog | 7 | 42.9% | 2.29 |
| CLE | fav | 21 | 33.3% | 2.10 |
| CLE | dog | 5 | 60.0% | 3.00 |
| TOR | fav | 16 | 37.5% | 2.25 |
| TOR | dog | 10 | 50.0% | 2.70 |
| ATL | fav | 17 | 23.5% | 2.06 |
| ATL | dog | 8 | 62.5% | 6.25 |
| PHI | fav | 16 | 50.0% | 3.75 |
| PHI | dog | 13 | 30.8% | 1.92 |
| ORL | fav | 13 | 46.2% | 2.00 |
| ORL | dog | 17 | 76.5% | 6.18 |
| OKC | fav | 22 | 31.8% | 1.64 |
| OKC | dog | 3 | 33.3% | 0.67 |
| SAS | fav | 25 | 28.0% | 1.64 |
| SAS | dog | 1 | 100.0% | 9.00 |
| DEN | fav | 19 | 47.4% | 4.00 |
| DEN | dog | 6 | 100.0% | 5.50 |
| LAL | fav | 16 | 43.8% | 3.19 |
| LAL | dog | 11 | 72.7% | 5.82 |
| HOU | fav | 24 | 54.2% | 5.25 |
| HOU | dog | 4 | 50.0% | 3.00 |
| MIN | fav | 16 | 37.5% | 3.00 |
| MIN | dog | 10 | 80.0% | 4.60 |
| POR | fav | 16 | 43.8% | 3.00 |
| POR | dog | 10 | 60.0% | 5.80 |
| PHX | fav | 14 | 57.1% | 5.00 |
| PHX | dog | 14 | 85.7% | 4.93 |

### 2D. As-favorite spread magnitude breakdown

| Team | Spread bucket | Games | Mean range | Mean swings | Mean peak |
|---|---|---:|---:|---:|---:|
| DET | small (1-3) | 6 | $0.491 | 7.00 | $0.598 |
| DET | medium (3.5-6) | 6 | $0.525 | 5.33 | $0.942 |
| DET | large (6.5+) | 11 | $0.303 | 3.00 | $0.990 |
| BOS | small (1-3) | 3 | $0.448 | 2.67 | $0.990 |
| BOS | medium (3.5-6) | 5 | $0.512 | 4.40 | $0.990 |
| BOS | large (6.5+) | 12 | $0.355 | 2.83 | $0.960 |
| NYK | small (1-3) | 4 | $0.583 | 5.50 | $0.772 |
| NYK | medium (3.5-6) | 3 | $0.778 | 7.33 | $0.892 |
| NYK | large (6.5+) | 12 | $0.312 | 4.25 | $0.990 |
| CLE | small (1-3) | 2 | $0.625 | 8.00 | $0.802 |
| CLE | medium (3.5-6) | 6 | $0.599 | 7.17 | $0.900 |
| CLE | large (6.5+) | 13 | $0.356 | 3.62 | $0.983 |
| TOR | small (1-3) | 5 | $0.594 | 5.00 | $0.790 |
| TOR | medium (3.5-6) | 2 | $0.659 | 8.00 | $0.990 |
| TOR | large (6.5+) | 9 | $0.290 | 3.67 | $0.981 |
| ATL | small (1-3) | 3 | $0.577 | 8.00 | $0.920 |
| ATL | medium (3.5-6) | 2 | $0.470 | 2.50 | $0.990 |
| ATL | large (6.5+) | 12 | $0.266 | 3.00 | $0.990 |
| PHI | small (1-3) | 7 | $0.610 | 8.43 | $0.896 |
| PHI | medium (3.5-6) | 3 | $0.559 | 6.67 | $0.941 |
| PHI | large (6.5+) | 6 | $0.362 | 3.83 | $0.990 |
| ORL | small (1-3) | 1 | $0.518 | 13.00 | $0.990 |
| ORL | medium (3.5-6) | 2 | $0.542 | 6.50 | $0.990 |
| ORL | large (6.5+) | 10 | $0.465 | 5.10 | $0.971 |
| OKC | small (1-3) | 1 | $0.737 | 6.00 | $0.747 |
| OKC | medium (3.5-6) | 2 | $0.621 | 6.00 | $0.847 |
| OKC | large (6.5+) | 19 | $0.316 | 4.95 | $0.990 |
| SAS | small (1-3) | 1 | $0.923 | 16.00 | $0.933 |
| SAS | medium (3.5-6) | 9 | $0.543 | 6.44 | $0.983 |
| SAS | large (6.5+) | 15 | $0.270 | 3.27 | $0.990 |
| DEN | small (1-3) | 2 | $0.838 | 15.50 | $0.848 |
| DEN | medium (3.5-6) | 4 | $0.578 | 11.75 | $0.950 |
| DEN | large (6.5+) | 13 | $0.463 | 6.46 | $0.981 |
| LAL | small (1-3) | 3 | $0.569 | 8.33 | $0.729 |
| LAL | medium (3.5-6) | 4 | $0.775 | 10.75 | $0.940 |
| LAL | large (6.5+) | 9 | $0.284 | 3.78 | $0.990 |
| HOU | small (1-3) | 6 | $0.776 | 11.00 | $0.894 |
| HOU | medium (3.5-6) | 6 | $0.473 | 5.33 | $0.990 |
| HOU | large (6.5+) | 12 | $0.423 | 5.42 | $0.955 |
| MIN | small (1-3) | 3 | $0.624 | 8.33 | $0.634 |
| MIN | medium (3.5-6) | 4 | $0.453 | 4.50 | $0.990 |
| MIN | large (6.5+) | 9 | $0.418 | 4.33 | $0.951 |
| POR | small (1-3) | 2 | $0.557 | 4.50 | $0.782 |
| POR | medium (3.5-6) | 2 | $0.527 | 6.00 | $0.990 |
| POR | large (6.5+) | 12 | $0.340 | 3.58 | $0.963 |
| PHX | small (1-3) | 3 | $0.703 | 7.67 | $0.798 |
| PHX | medium (3.5-6) | 2 | $0.873 | 16.00 | $0.951 |
| PHX | large (6.5+) | 9 | $0.445 | 6.78 | $0.964 |

### 2E. Opponent-quality split (playoff vs non-playoff opponent)

| Team | Opp type | Games | Mean range | Mean swings | S4A entries |
|---|---|---:|---:|---:|---:|
| DET | playoff | 17 | $0.560 | 7.29 | 11 |
| DET | non-playoff | 12 | $0.298 | 1.92 | 2 |
| BOS | playoff | 14 | $0.594 | 7.21 | 5 |
| BOS | non-playoff | 13 | $0.340 | 2.08 | 4 |
| NYK | playoff | 12 | $0.583 | 6.17 | 6 |
| NYK | non-playoff | 14 | $0.328 | 4.43 | 8 |
| CLE | playoff | 10 | $0.480 | 6.60 | 4 |
| CLE | non-playoff | 16 | $0.453 | 4.75 | 13 |
| TOR | playoff | 13 | $0.577 | 7.15 | 3 |
| TOR | non-playoff | 13 | $0.353 | 4.23 | 6 |
| ATL | playoff | 12 | $0.545 | 7.00 | 8 |
| ATL | non-playoff | 13 | $0.286 | 2.85 | 4 |
| PHI | playoff | 15 | $0.413 | 4.80 | 3 |
| PHI | non-playoff | 14 | $0.521 | 6.21 | 12 |
| ORL | playoff | 17 | $0.630 | 8.53 | 2 |
| ORL | non-playoff | 13 | $0.494 | 5.46 | 9 |
| OKC | playoff | 16 | $0.495 | 7.12 | 15 |
| OKC | non-playoff | 9 | $0.184 | 1.89 | 2 |
| SAS | playoff | 12 | $0.577 | 8.33 | 10 |
| SAS | non-playoff | 14 | $0.256 | 2.29 | 3 |
| DEN | playoff | 17 | $0.608 | 9.24 | 15 |
| DEN | non-playoff | 8 | $0.512 | 8.00 | 6 |
| LAL | playoff | 14 | $0.625 | 8.00 | 5 |
| LAL | non-playoff | 13 | $0.364 | 4.54 | 4 |
| HOU | playoff | 14 | $0.646 | 7.29 | 11 |
| HOU | non-playoff | 14 | $0.432 | 6.14 | 12 |
| MIN | playoff | 16 | $0.656 | 7.81 | 8 |
| MIN | non-playoff | 10 | $0.341 | 3.90 | 3 |
| POR | playoff | 11 | $0.598 | 7.09 | 3 |
| POR | non-playoff | 15 | $0.392 | 4.67 | 9 |
| PHX | playoff | 16 | $0.661 | 8.19 | 5 |
| PHX | non-playoff | 12 | $0.500 | 7.00 | 11 |

## Section 3 — Recovery and collapse profiles

### 3A. S4A hit rate per team (as favorite)

This is the headline table. Teams sorted by hit %. Δ is vs pooled 52.4%.

| Team | As-fav games | S4A entries | Hit $0.90 | Hit % | Mean P&L | Δ vs pooled |
|---|---:|---:|---:|---:|---:|---:|
| NYK | 19 | 14 | 11 | 78.6% | $+15.96 | +26.2pp |
| ATL | 17 | 12 | 9 | 75.0% | $+12.13 | +22.6pp |
| CLE | 21 | 17 | 12 | 70.6% | $+5.58 | +18.2pp |
| BOS | 20 | 9 | 6 | 66.7% | $+5.52 | +14.3pp |
| POR | 16 | 12 | 8 | 66.7% | $+10.02 | +14.3pp |
| OKC | 22 | 17 | 11 | 64.7% | $+6.72 | +12.3pp |
| DEN | 19 | 21 | 13 | 61.9% | $+5.33 | +9.5pp |
| SAS | 25 | 13 | 8 | 61.5% | $+1.21 | +9.1pp |
| PHI | 16 | 15 | 9 | 60.0% | $+8.58 | +7.6pp |
| PHX | 14 | 16 | 9 | 56.2% | $+2.22 | +3.9pp |
| ORL | 13 | 11 | 6 | 54.5% | $+2.04 | +2.1pp |
| MIN | 16 | 11 | 6 | 54.5% | $+5.83 | +2.1pp |
| DET | 23 | 13 | 7 | 53.8% | $+5.16 | +1.4pp |
| TOR | 16 | 9 | 4 | 44.4% | $-0.40 | -8.0pp |
| LAL | 16 | 9 | 4 | 44.4% | $-8.04 | -8.0pp |
| HOU | 24 | 23 | 7 | 30.4% | $-9.40 | -22.0pp |

#### 3A sub-split: home vs away

| Team | Venue | As-fav games | Entries | Hit % | Δ vs pooled |
|---|---|---:|---:|---:|---:|
| DET | home | 12 | 9 | 55.6% | +3.2pp |
| DET | away | 11 | 4 | 50.0% | -2.4pp |
| BOS | home | 12 | 7 | 57.1% | +4.7pp |
| BOS | away | 8 | 2 | 100.0% | +47.6pp |
| NYK | home | 9 | 8 | 62.5% | +10.1pp |
| NYK | away | 10 | 6 | 100.0% | +47.6pp |
| CLE | home | 10 | 6 | 66.7% | +14.3pp |
| CLE | away | 11 | 11 | 72.7% | +20.3pp |
| TOR | home | 9 | 6 | 50.0% | -2.4pp |
| TOR | away | 7 | 3 | 33.3% | -19.1pp |
| ATL | home | 14 | 11 | 72.7% | +20.3pp |
| ATL | away | 3 | 1 | 100.0% | +47.6pp |
| PHI | home | 9 | 9 | 66.7% | +14.3pp |
| PHI | away | 7 | 6 | 50.0% | -2.4pp |
| ORL | home | 7 | 7 | 57.1% | +4.7pp |
| ORL | away | 6 | 4 | 50.0% | -2.4pp |
| OKC | home | 12 | 13 | 61.5% | +9.1pp |
| OKC | away | 10 | 4 | 75.0% | +22.6pp |
| SAS | home | 14 | 9 | 55.6% | +3.2pp |
| SAS | away | 11 | 4 | 75.0% | +22.6pp |
| DEN | home | 13 | 13 | 61.5% | +9.1pp |
| DEN | away | 6 | 8 | 62.5% | +10.1pp |
| LAL | home | 10 | 6 | 50.0% | -2.4pp |
| LAL | away | 6 | 3 | 33.3% | -19.1pp |
| HOU | home | 16 | 15 | 26.7% | -25.7pp |
| HOU | away | 8 | 8 | 37.5% | -14.9pp |
| MIN | home | 10 | 8 | 50.0% | -2.4pp |
| MIN | away | 6 | 3 | 66.7% | +14.3pp |
| POR | home | 10 | 6 | 66.7% | +14.3pp |
| POR | away | 6 | 6 | 66.7% | +14.3pp |
| PHX | home | 8 | 10 | 40.0% | -12.4pp |
| PHX | away | 6 | 6 | 83.3% | +30.9pp |

#### 3A sub-split: spread magnitude

| Team | Spread bucket | As-fav games | Entries | Hit % |
|---|---|---:|---:|---:|
| DET | small (1-3) | 6 | 4 | 25.0% |
| DET | medium (3.5-6) | 6 | 5 | 80.0% |
| DET | large (6.5+) | 11 | 4 | 50.0% |
| BOS | medium (3.5-6) | 5 | 4 | 75.0% |
| BOS | large (6.5+) | 12 | 5 | 60.0% |
| NYK | small (1-3) | 4 | 1 | 100.0% |
| NYK | medium (3.5-6) | 3 | 5 | 40.0% |
| NYK | large (6.5+) | 12 | 8 | 100.0% |
| CLE | small (1-3) | 2 | 2 | 50.0% |
| CLE | medium (3.5-6) | 6 | 5 | 40.0% |
| CLE | large (6.5+) | 13 | 10 | 90.0% |
| TOR | small (1-3) | 5 | 4 | 25.0% |
| TOR | medium (3.5-6) | 2 | 2 | 50.0% |
| TOR | large (6.5+) | 9 | 3 | 66.7% |
| ATL | small (1-3) | 3 | 4 | 50.0% |
| ATL | medium (3.5-6) | 2 | 2 | 100.0% |
| ATL | large (6.5+) | 12 | 6 | 83.3% |
| PHI | small (1-3) | 7 | 9 | 55.6% |
| PHI | medium (3.5-6) | 3 | 2 | 50.0% |
| PHI | large (6.5+) | 6 | 4 | 75.0% |
| ORL | small (1-3) | 1 | 1 | 100.0% |
| ORL | medium (3.5-6) | 2 | 2 | 50.0% |
| ORL | large (6.5+) | 10 | 8 | 50.0% |
| OKC | small (1-3) | 1 | 1 | 0.0% |
| OKC | medium (3.5-6) | 2 | 3 | 66.7% |
| OKC | large (6.5+) | 19 | 13 | 69.2% |
| SAS | small (1-3) | 1 | 2 | 100.0% |
| SAS | medium (3.5-6) | 9 | 6 | 66.7% |
| SAS | large (6.5+) | 15 | 5 | 40.0% |
| DEN | small (1-3) | 2 | 3 | 66.7% |
| DEN | medium (3.5-6) | 4 | 7 | 71.4% |
| DEN | large (6.5+) | 13 | 11 | 54.5% |
| LAL | medium (3.5-6) | 4 | 5 | 20.0% |
| LAL | large (6.5+) | 9 | 4 | 75.0% |
| HOU | small (1-3) | 6 | 9 | 11.1% |
| HOU | medium (3.5-6) | 6 | 6 | 83.3% |
| HOU | large (6.5+) | 12 | 8 | 12.5% |
| MIN | small (1-3) | 3 | 2 | 0.0% |
| MIN | medium (3.5-6) | 4 | 4 | 75.0% |
| MIN | large (6.5+) | 9 | 5 | 60.0% |
| POR | small (1-3) | 2 | 1 | 100.0% |
| POR | medium (3.5-6) | 2 | 3 | 100.0% |
| POR | large (6.5+) | 12 | 8 | 50.0% |
| PHX | small (1-3) | 3 | 3 | 33.3% |
| PHX | medium (3.5-6) | 2 | 4 | 50.0% |
| PHX | large (6.5+) | 9 | 9 | 66.7% |

### 3B. As-favorite — collapse rate (price drops ≤ $0.40)

| Team | As-fav games | Collapse % | Home % | Away % |
|---|---:|---:|---:|---:|
| DET | 23 | 34.8% | 33.3% | 36.4% |
| BOS | 20 | 30.0% | 41.7% | 12.5% |
| NYK | 19 | 36.8% | 33.3% | 40.0% |
| CLE | 21 | 28.6% | 30.0% | 27.3% |
| TOR | 16 | 31.2% | 33.3% | 28.6% |
| ATL | 17 | 11.8% | 14.3% | 0.0% |
| PHI | 16 | 37.5% | 44.4% | 28.6% |
| ORL | 13 | 30.8% | 28.6% | 33.3% |
| OKC | 22 | 22.7% | 33.3% | 10.0% |
| SAS | 25 | 20.0% | 21.4% | 18.2% |
| DEN | 19 | 47.4% | 38.5% | 66.7% |
| LAL | 16 | 37.5% | 20.0% | 66.7% |
| HOU | 24 | 50.0% | 43.8% | 62.5% |
| MIN | 16 | 37.5% | 50.0% | 16.7% |
| POR | 16 | 18.8% | 20.0% | 16.7% |
| PHX | 14 | 50.0% | 62.5% | 33.3% |

### 3C. As-underdog — upset rate

Pooled upset rate across the 16 teams' underdog games: 34.8% (46/132).

| Team | As-dog games | Wins | Upset % | Home dog % | Away dog % | Δ vs pooled |
|---|---:|---:|---:|---:|---:|---:|
| DET | 6 | 4 | 66.7% | 100.0% | 60.0% | +31.8pp |
| BOS | 7 | 2 | 28.6% | 100.0% | 0.0% | -6.3pp |
| NYK | 7 | 1 | 14.3% | 0.0% | 20.0% | -20.6pp |
| CLE | 5 | 1 | 20.0% | 50.0% | 0.0% | -14.8pp |
| TOR | 10 | 1 | 10.0% | 33.3% | 0.0% | -24.8pp |
| ATL | 8 | 3 | 37.5% | 0.0% | 42.9% | +2.7pp |
| PHI | 13 | 3 | 23.1% | 25.0% | 22.2% | -11.8pp |
| ORL | 17 | 6 | 35.3% | 28.6% | 40.0% | +0.4pp |
| OKC | 3 | 1 | 33.3% | 0.0% | 33.3% | -1.5pp |
| SAS | 1 | 1 | 100.0% | 0.0% | 100.0% | +65.2pp |
| DEN | 6 | 3 | 50.0% | 50.0% | 50.0% | +15.2pp |
| LAL | 11 | 8 | 72.7% | 80.0% | 66.7% | +37.9pp |
| HOU | 4 | 1 | 25.0% | 0.0% | 25.0% | -9.8pp |
| MIN | 10 | 4 | 40.0% | 50.0% | 37.5% | +5.2pp |
| POR | 10 | 3 | 30.0% | 0.0% | 37.5% | -4.8pp |
| PHX | 14 | 4 | 28.6% | 50.0% | 12.5% | -6.3pp |

### 3D. As-underdog — peak price reached

| Team | As-dog games | Mean peak | Peak ≥ $0.50 % | Peak ≥ $0.65 % | Home peak | Away peak |
|---|---:|---:|---:|---:|---:|---:|
| DET | 6 | $0.854 | 83.3% | 83.3% | $0.990 | $0.826 |
| BOS | 7 | $0.706 | 85.7% | 42.9% | $0.990 | $0.593 |
| NYK | 7 | $0.493 | 42.9% | 14.3% | $0.364 | $0.545 |
| CLE | 5 | $0.599 | 60.0% | 40.0% | $0.602 | $0.598 |
| TOR | 10 | $0.558 | 50.0% | 20.0% | $0.829 | $0.442 |
| ATL | 8 | $0.674 | 62.5% | 50.0% | $0.435 | $0.708 |
| PHI | 13 | $0.454 | 30.8% | 23.1% | $0.445 | $0.457 |
| ORL | 17 | $0.748 | 76.5% | 52.9% | $0.787 | $0.720 |
| OKC | 3 | $0.642 | 33.3% | 33.3% | $0.000 | $0.642 |
| SAS | 1 | $0.990 | 100.0% | 100.0% | $0.000 | $0.990 |
| DEN | 6 | $0.837 | 100.0% | 83.3% | $0.824 | $0.844 |
| LAL | 11 | $0.790 | 72.7% | 72.7% | $0.812 | $0.771 |
| HOU | 4 | $0.676 | 50.0% | 50.0% | $0.000 | $0.676 |
| MIN | 10 | $0.698 | 80.0% | 50.0% | $0.746 | $0.686 |
| POR | 10 | $0.698 | 60.0% | 50.0% | $0.643 | $0.711 |
| PHX | 14 | $0.702 | 85.7% | 42.9% | $0.757 | $0.661 |

## Section 4 — Period-specific S4A tendencies (as favorite)
| Team | Q1 n | Q1 hit% | Q2 n | Q2 hit% | Q3 n | Q3 hit% | Q4 n | Q4 hit% | Dominant Q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DET | 4 | 75.0% | 6 | 50.0% | 0 | — | 2 | 0.0% | Q2 |
| BOS | 1 | 100.0% | 5 | 60.0% | 1 | 100.0% | 2 | 50.0% | Q2 |
| NYK | 5 | 60.0% | 4 | 75.0% | 1 | 100.0% | 4 | 100.0% | Q1 |
| CLE | 5 | 40.0% | 4 | 75.0% | 4 | 100.0% | 4 | 75.0% | Q1 |
| TOR | 5 | 60.0% | 4 | 25.0% | 0 | — | 0 | — | Q1 |
| ATL | 3 | 66.7% | 5 | 100.0% | 1 | 0.0% | 3 | 66.7% | Q2 |
| PHI | 3 | 66.7% | 5 | 40.0% | 3 | 66.7% | 4 | 75.0% | Q2 |
| ORL | 4 | 50.0% | 1 | 100.0% | 2 | 0.0% | 4 | 75.0% | Q1 |
| OKC | 4 | 50.0% | 4 | 50.0% | 3 | 100.0% | 6 | 66.7% | Q4 |
| SAS | 5 | 80.0% | 2 | 0.0% | 2 | 100.0% | 4 | 50.0% | Q1 |
| DEN | 2 | 0.0% | 7 | 57.1% | 5 | 60.0% | 7 | 85.7% | Q2 |
| LAL | 2 | 50.0% | 3 | 66.7% | 3 | 33.3% | 1 | 0.0% | Q2 |
| HOU | 5 | 20.0% | 5 | 60.0% | 7 | 42.9% | 5 | 0.0% | Q3 |
| MIN | 5 | 40.0% | 1 | 0.0% | 3 | 100.0% | 2 | 50.0% | Q1 |
| POR | 4 | 50.0% | 4 | 100.0% | 2 | 50.0% | 2 | 50.0% | Q1 |
| PHX | 4 | 25.0% | 4 | 25.0% | 4 | 100.0% | 4 | 75.0% | Q1 |

## Section 5 — Summary scorecards and actionable output

### 5A. S4A tier list

- **Tier 1** (strong buy): hit rate ≥ 60% (sig. above pooled 52.4%)
- **Tier 2** (neutral): hit rate 45-59%
- **Tier 3** (avoid): hit rate < 45%

| Tier | Team | S4A entries | Hit % | Mean P&L |
|---|---|---:|---:|---:|
| Tier 1 | NYK | 14 | 78.6% | $+15.96 |
| Tier 1 | ATL | 12 | 75.0% | $+12.13 |
| Tier 1 | CLE | 17 | 70.6% | $+5.58 |
| Tier 1 | BOS | 9 | 66.7% | $+5.52 |
| Tier 1 | POR | 12 | 66.7% | $+10.02 |
| Tier 1 | OKC | 17 | 64.7% | $+6.72 |
| Tier 1 | DEN | 21 | 61.9% | $+5.33 |
| Tier 1 | SAS | 13 | 61.5% | $+1.21 |
| Tier 1 | PHI | 15 | 60.0% | $+8.58 |
| Tier 2 | PHX | 16 | 56.2% | $+2.22 |
| Tier 2 | ORL | 11 | 54.5% | $+2.04 |
| Tier 2 | MIN | 11 | 54.5% | $+5.83 |
| Tier 2 | DET | 13 | 53.8% | $+5.16 |
| Tier 3 | TOR | 9 | 44.4% | $-0.40 |
| Tier 3 | LAL | 9 | 44.4% | $-8.04 |
| Tier 3 | HOU | 23 | 30.4% | $-9.40 |

### 5B. Sample size caveat (95% Wilson CI on hit rate)

| Team | Entries | Hit % | 95% CI low | 95% CI high | Significant vs pooled? |
|---|---:|---:|---:|---:|---|
| DET | 13 | 53.8% | 29.1% | 76.8% | no (CI spans pooled) |
| BOS | 9 | 66.7% | 35.4% | 87.9% | no (CI spans pooled) |
| NYK | 14 | 78.6% | 52.4% | 92.4% | yes (above pooled) |
| CLE | 17 | 70.6% | 46.9% | 86.7% | no (CI spans pooled) |
| TOR | 9 | 44.4% | 18.9% | 73.3% | no (CI spans pooled) |
| ATL | 12 | 75.0% | 46.8% | 91.1% | no (CI spans pooled) |
| PHI | 15 | 60.0% | 35.7% | 80.2% | no (CI spans pooled) |
| ORL | 11 | 54.5% | 28.0% | 78.7% | no (CI spans pooled) |
| OKC | 17 | 64.7% | 41.3% | 82.7% | no (CI spans pooled) |
| SAS | 13 | 61.5% | 35.5% | 82.3% | no (CI spans pooled) |
| DEN | 21 | 61.9% | 40.9% | 79.2% | no (CI spans pooled) |
| LAL | 9 | 44.4% | 18.9% | 73.3% | no (CI spans pooled) |
| HOU | 23 | 30.4% | 15.6% | 50.9% | yes (below pooled) |
| MIN | 11 | 54.5% | 28.0% | 78.7% | no (CI spans pooled) |
| POR | 12 | 66.7% | 39.1% | 86.2% | no (CI spans pooled) |
| PHX | 16 | 56.2% | 33.2% | 76.9% | no (CI spans pooled) |

### 5C. If-we-filtered S4A aggregate EV

Only trades where the favorite team belongs to the specified universe. Note: the 'baseline' row here is the subset of the 404-game dataset where the favorite is a playoff team (not the full 404-game aggregate).

| Universe | Games | Entries | Hit % | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|
| All 16 teams (baseline) | 297 | 222 | 58.6% | $+4.06 | $+1,661 |
| Tier 1 only | 175 | 130 | 66.9% | $+7.73 | $+3,141 |
| Tier 1 + 2 | 241 | 181 | 63.5% | $+6.59 | $+2,710 |
| Tier 3 excluded (= Tier 1 + 2) | 241 | 181 | 63.5% | $+6.59 | $+2,710 |

## Section 6 — Data-driven pattern discovery

### 6A. Biggest team-level outliers (|Z| ≥ 1.5)

| Team | Metric | Value | 16-team mean | Z-score | Direction |
|---|---|---:|---:|---:|---|
| HOU | s4a_hit_pct | 30.435 | 59.010 | -2.33 | LOW |
| LAL | upset_pct | 72.727 | 34.335 | +2.19 | HIGH |
| PHI | mean_swings_dog | 4.385 | 7.213 | -2.05 | LOW |
| DEN | mean_swings_fav | 8.526 | 5.485 | +2.04 | HIGH |
| ATL | crossed_050_pct_fav | 23.529 | 41.866 | -1.98 | LOW |
| PHI | mean_range_dog | 0.414 | 0.580 | -1.96 | LOW |
| PHI | dog_mean_peak | 0.454 | 0.675 | -1.94 | LOW |
| ATL | collapse_pct | 11.765 | 32.833 | -1.91 | LOW |
| DEN | mean_swings_dog | 9.833 | 7.213 | +1.90 | HIGH |
| PHX | mean_swings_fav | 8.286 | 5.485 | +1.88 | HIGH |
| DEN | mean_range_dog | 0.738 | 0.580 | +1.86 | HIGH |
| DET | upset_pct | 66.667 | 34.335 | +1.84 | HIGH |
| PHX | mean_range_fav | 0.561 | 0.448 | +1.84 | HIGH |
| DEN | crossed_050_pct_dog | 100.000 | 63.784 | +1.80 | HIGH |
| ATL | mean_range_fav | 0.345 | 0.448 | -1.66 | LOW |
| PHX | crossed_050_pct_fav | 57.143 | 41.866 | +1.65 | HIGH |
| PHI | crossed_050_pct_dog | 30.769 | 63.784 | -1.64 | LOW |
| NYK | s4a_hit_pct | 78.571 | 59.010 | +1.60 | HIGH |
| NYK | dog_mean_peak | 0.493 | 0.675 | -1.60 | LOW |
| DET | dog_mean_peak | 0.854 | 0.675 | +1.57 | HIGH |

### 6B. Team "personality" clusters

Rule-based clusters from favorite-side volatility + S4A hit + collapse + underdog upset rate. Thresholds use the 16-team medians on each dimension. "Uncategorized" means the team doesn't fit cleanly into any cluster.

| Team | Cluster |
|---|---|
| DET | Scrappy underdog |
| BOS | Steady dominator |
| NYK | Low-volatility favorite |
| CLE | Steady dominator |
| TOR | Low-volatility favorite |
| ATL | Steady dominator |
| PHI | Volatile oscillator |
| ORL | Volatile oscillator |
| OKC | Steady dominator |
| SAS | Steady dominator |
| DEN | Volatile oscillator |
| LAL | Volatile oscillator |
| HOU | Volatile oscillator |
| MIN | Volatile oscillator |
| POR | Steady dominator |
| PHX | Volatile oscillator |

Cluster counts: Volatile oscillator: 7, Steady dominator: 6, Low-volatility favorite: 2, Scrappy underdog: 1.

### 6C. Home-away asymmetry standouts

Teams with largest |hit-rate delta| between home-fav and away-fav S4A entries. Minimum 3 entries per venue.

| Team | Home-fav hit % | Away-fav hit % | Δ | Home n | Away n |
|---|---:|---:|---:|---:|---:|
| PHX | 40.0% | 83.3% | -43.3pp | 10 | 6 |
| NYK | 62.5% | 100.0% | -37.5pp | 8 | 6 |
| SAS | 55.6% | 75.0% | -19.4pp | 9 | 4 |
| PHI | 66.7% | 50.0% | +16.7pp | 9 | 6 |
| MIN | 50.0% | 66.7% | -16.7pp | 8 | 3 |
| TOR | 50.0% | 33.3% | +16.7pp | 6 | 3 |
| LAL | 50.0% | 33.3% | +16.7pp | 6 | 3 |
| OKC | 61.5% | 75.0% | -13.5pp | 13 | 4 |
| HOU | 26.7% | 37.5% | -10.8pp | 15 | 8 |
| ORL | 57.1% | 50.0% | +7.1pp | 7 | 4 |

### 6D. Period-specific standouts (min 3 entries)

**Top 5 team × period combinations by hit rate:**

| Team | Period | Entries | Hit % |
|---|---|---:|---:|
| NYK | Q4 | 4 | 100.0% |
| CLE | Q3 | 4 | 100.0% |
| ATL | Q2 | 5 | 100.0% |
| OKC | Q3 | 3 | 100.0% |
| MIN | Q3 | 3 | 100.0% |

**Bottom 5 team × period combinations by hit rate:**

| Team | Period | Entries | Hit % |
|---|---|---:|---:|
| TOR | Q2 | 4 | 25.0% |
| PHX | Q1 | 4 | 25.0% |
| PHX | Q2 | 4 | 25.0% |
| HOU | Q1 | 5 | 20.0% |
| HOU | Q4 | 5 | 0.0% |

---

**Report is observational.** Findings inform engine parameterization but do not constitute a new strategy. No STRATEGY_SPEC changes until findings are reviewed.

