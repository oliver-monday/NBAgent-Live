# Team Profiles — Full-Season ESPN WP Validation
_Generated: 2026-04-23T06:46:06.766350+00:00_
Full-season profile on **1234 games** from the 2025-26 ESPN WP dataset (all 30 NBA teams). Companion to `team_profiles_playoff16.md` (404-game Kalshi dataset, playoff 16 only). Primary goal: validate the team-level S4A hit rate dispersion observed on Kalshi against a 3× sample via Spearman's rank correlation.

**Calibration caveat.** ESPN WP is systematically more reactive than Kalshi at the tails (+8.30pp at 0.20–0.40 WP, −2.73pp at 0.80–1.00 WP — from `wp_vs_kalshi_aggregate.md`). Absolute S4A hit rates, entry counts, and P&L on ESPN data are **NOT** directly comparable to Kalshi. The validation target is the **rank order** of team hit rates between the two datasets.

**Pooled ESPN S4A hit rate on this dataset:** 44.2%. Kalshi pooled was 52.4%. The gap reflects the ESPN reactivity — interpret Δ-vs-pooled at ESPN-pooled-level, not Kalshi-pooled.

## Section 1 — Team game counts and role distribution

★ = playoff 16. Sorted by game count.

| Team | ★ | Games | As fav | As dog | Fav % | Mean fav open | Mean dog open |
|---|---|---:|---:|---:|---:|---:|---:|
| GSW |  | 83 | 45 | 38 | 54.2% | 0.672 | 0.357 |
| NYK | ★ | 83 | 70 | 13 | 84.3% | 0.693 | 0.457 |
| CHA |  | 83 | 36 | 47 | 43.4% | 0.656 | 0.346 |
| ORL | ★ | 83 | 51 | 32 | 61.4% | 0.658 | 0.375 |
| MIA |  | 83 | 43 | 40 | 51.8% | 0.672 | 0.382 |
| PHI | ★ | 83 | 41 | 42 | 49.4% | 0.652 | 0.373 |
| SAS | ★ | 83 | 63 | 20 | 75.9% | 0.700 | 0.388 |
| PHX | ★ | 83 | 35 | 48 | 42.2% | 0.641 | 0.357 |
| POR | ★ | 83 | 30 | 53 | 36.1% | 0.642 | 0.337 |
| OKC | ★ | 82 | 80 | 2 | 97.6% | 0.776 | 0.355 |
| HOU | ★ | 82 | 72 | 10 | 87.8% | 0.692 | 0.418 |
| LAL | ★ | 82 | 50 | 32 | 61.0% | 0.663 | 0.384 |
| CLE | ★ | 82 | 69 | 13 | 84.1% | 0.708 | 0.442 |
| BKN |  | 82 | 8 | 74 | 9.8% | 0.579 | 0.265 |
| ATL | ★ | 82 | 47 | 35 | 57.3% | 0.674 | 0.415 |
| TOR | ★ | 82 | 49 | 33 | 59.8% | 0.640 | 0.366 |
| BOS | ★ | 82 | 60 | 22 | 73.2% | 0.688 | 0.416 |
| DET | ★ | 82 | 68 | 14 | 82.9% | 0.686 | 0.419 |
| MEM |  | 82 | 27 | 55 | 32.9% | 0.619 | 0.327 |
| NOP |  | 82 | 14 | 68 | 17.1% | 0.635 | 0.320 |
| MIL |  | 82 | 28 | 54 | 34.1% | 0.628 | 0.326 |
| WAS |  | 82 | 3 | 79 | 3.7% | 0.561 | 0.189 |
| UTA |  | 82 | 6 | 76 | 7.3% | 0.592 | 0.240 |
| LAC |  | 82 | 44 | 38 | 53.7% | 0.683 | 0.374 |
| DAL |  | 82 | 26 | 56 | 31.7% | 0.607 | 0.320 |
| SAC |  | 82 | 9 | 73 | 11.0% | 0.596 | 0.258 |
| MIN | ★ | 82 | 63 | 19 | 76.8% | 0.676 | 0.386 |
| IND |  | 82 | 12 | 70 | 14.6% | 0.638 | 0.295 |
| DEN | ★ | 82 | 60 | 22 | 73.2% | 0.686 | 0.363 |
| CHI |  | 81 | 25 | 56 | 30.9% | 0.602 | 0.321 |

## Section 2 — In-game volatility profiles (WP scale)

### 2A/B/C — Range, swings, $0.50 crossover (combined)

| Team | ★ | Role | Games | Mean range | Mean swings | Cross 0.50 % |
|---|---|---|---:|---:|---:|---:|
| GSW |  | fav | 45 | 0.624 | 16.18 | 75.6% |
| GSW |  | dog | 38 | 0.639 | 14.79 | 84.2% |
| NYK | ★ | fav | 70 | 0.570 | 13.14 | 68.6% |
| NYK | ★ | dog | 13 | 0.677 | 15.77 | 92.3% |
| CHA |  | fav | 36 | 0.552 | 12.72 | 63.9% |
| CHA |  | dog | 47 | 0.649 | 14.30 | 78.7% |
| ORL | ★ | fav | 51 | 0.650 | 16.61 | 80.4% |
| ORL | ★ | dog | 32 | 0.658 | 14.53 | 87.5% |
| MIA |  | fav | 43 | 0.574 | 13.42 | 62.8% |
| MIA |  | dog | 40 | 0.651 | 16.60 | 92.5% |
| PHI | ★ | fav | 41 | 0.633 | 16.10 | 75.6% |
| PHI | ★ | dog | 42 | 0.595 | 14.81 | 71.4% |
| SAS | ★ | fav | 63 | 0.545 | 11.73 | 52.4% |
| SAS | ★ | dog | 20 | 0.752 | 17.35 | 95.0% |
| PHX | ★ | fav | 35 | 0.593 | 13.40 | 68.6% |
| PHX | ★ | dog | 48 | 0.649 | 14.77 | 81.2% |
| POR | ★ | fav | 30 | 0.585 | 14.73 | 73.3% |
| POR | ★ | dog | 53 | 0.606 | 16.38 | 73.6% |
| OKC | ★ | fav | 80 | 0.497 | 12.34 | 48.8% |
| OKC | ★ | dog | 2 | 0.554 | 12.50 | 50.0% |
| HOU | ★ | fav | 72 | 0.591 | 15.22 | 69.4% |
| HOU | ★ | dog | 10 | 0.685 | 15.10 | 80.0% |
| LAL | ★ | fav | 50 | 0.598 | 13.28 | 72.0% |
| LAL | ★ | dog | 32 | 0.598 | 13.50 | 78.1% |
| CLE | ★ | fav | 69 | 0.605 | 14.10 | 69.6% |
| CLE | ★ | dog | 13 | 0.660 | 16.85 | 84.6% |
| BKN |  | fav | 8 | 0.607 | 11.12 | 75.0% |
| BKN |  | dog | 74 | 0.493 | 10.43 | 48.6% |
| ATL | ★ | fav | 47 | 0.585 | 12.68 | 66.0% |
| ATL | ★ | dog | 35 | 0.628 | 14.17 | 85.7% |
| TOR | ★ | fav | 49 | 0.596 | 13.31 | 75.5% |
| TOR | ★ | dog | 33 | 0.651 | 13.61 | 75.8% |
| BOS | ★ | fav | 60 | 0.568 | 12.28 | 65.0% |
| BOS | ★ | dog | 22 | 0.686 | 16.91 | 95.5% |
| DET | ★ | fav | 68 | 0.550 | 12.72 | 60.3% |
| DET | ★ | dog | 14 | 0.657 | 18.29 | 92.9% |
| MEM |  | fav | 27 | 0.680 | 18.78 | 88.9% |
| MEM |  | dog | 55 | 0.596 | 13.58 | 65.5% |
| NOP |  | fav | 14 | 0.580 | 13.07 | 57.1% |
| NOP |  | dog | 68 | 0.583 | 15.38 | 67.6% |
| MIL |  | fav | 28 | 0.609 | 15.96 | 85.7% |
| MIL |  | dog | 54 | 0.562 | 13.81 | 61.1% |
| WAS |  | fav | 3 | 0.736 | 13.67 | 100.0% |
| WAS |  | dog | 79 | 0.440 | 9.23 | 39.2% |
| UTA |  | fav | 6 | 0.591 | 9.67 | 83.3% |
| UTA |  | dog | 76 | 0.572 | 13.14 | 64.5% |
| LAC |  | fav | 44 | 0.585 | 13.16 | 70.5% |
| LAC |  | dog | 38 | 0.626 | 14.58 | 78.9% |
| DAL |  | fav | 26 | 0.645 | 17.62 | 76.9% |
| DAL |  | dog | 56 | 0.565 | 13.88 | 57.1% |
| SAC |  | fav | 9 | 0.651 | 23.00 | 88.9% |
| SAC |  | dog | 73 | 0.538 | 11.93 | 54.8% |
| MIN | ★ | fav | 63 | 0.627 | 13.65 | 74.6% |
| MIN | ★ | dog | 19 | 0.713 | 18.11 | 89.5% |
| IND |  | fav | 12 | 0.716 | 13.42 | 91.7% |
| IND |  | dog | 70 | 0.564 | 13.17 | 61.4% |
| DEN | ★ | fav | 60 | 0.606 | 14.38 | 71.7% |
| DEN | ★ | dog | 22 | 0.687 | 18.64 | 81.8% |
| CHI |  | fav | 25 | 0.672 | 16.76 | 84.0% |
| CHI |  | dog | 56 | 0.581 | 14.77 | 66.1% |

## Section 3 — Recovery and collapse profiles

### 3A. S4A hit rate per team (as favorite) — all 30 teams

Teams ranked by ESPN hit %. For the 16 playoff teams, the Kalshi rank from `team_profiles_playoff16.md` is shown for direct comparison. Δ vs pooled is relative to the ESPN pooled rate 44.2%.

| ESPN rank | Team | ★ | As-fav | S4A entries | Hit % | Mean P&L | Δ vs pooled | Kalshi rank | Rank Δ |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | BKN |  | 8 | 6 | 83.3% | $+18.02 | +39.1pp | — | — |
| 2 | SAS | ★ | 63 | 51 | 58.8% | $+2.47 | +14.6pp | 8 | +6 |
| 3 | OKC | ★ | 80 | 62 | 58.1% | $-1.19 | +13.8pp | 6 | +3 |
| 4 | NOP |  | 14 | 14 | 57.1% | $+2.71 | +12.9pp | — | — |
| 5 | BOS | ★ | 60 | 52 | 53.8% | $+1.60 | +9.6pp | 4 | -1 |
| 6 | TOR | ★ | 49 | 45 | 53.3% | $+0.24 | +9.1pp | 14 | +8 |
| 7 | MIA |  | 43 | 39 | 51.3% | $-2.11 | +7.0pp | — | — |
| 8 | UTA |  | 6 | 4 | 50.0% | $+2.57 | +5.8pp | — | — |
| 9 | DEN | ★ | 60 | 51 | 47.1% | $-2.14 | +2.8pp | 7 | -2 |
| 10 | PHX | ★ | 35 | 32 | 46.9% | $+0.78 | +2.6pp | 10 | +0 |
| 11 | HOU | ★ | 72 | 61 | 45.9% | $-3.04 | +1.7pp | 16 | +5 |
| 12 | POR | ★ | 30 | 24 | 45.8% | $+2.47 | +1.6pp | 5 | -7 |
| 13 | DET | ★ | 68 | 59 | 45.8% | $-3.47 | +1.5pp | 13 | +0 |
| 14 | IND |  | 12 | 11 | 45.5% | $-3.66 | +1.2pp | — | — |
| 15 | CLE | ★ | 69 | 62 | 45.2% | $-5.05 | +0.9pp | 3 | -12 |
| 16 | CHA |  | 36 | 27 | 44.4% | $-2.59 | +0.2pp | — | — |
| 17 | LAC |  | 44 | 36 | 44.4% | $-3.69 | +0.2pp | — | — |
| 18 | LAL | ★ | 50 | 40 | 42.5% | $-4.09 | -1.7pp | 15 | -3 |
| 19 | PHI | ★ | 41 | 38 | 39.5% | $-5.80 | -4.8pp | 9 | -10 |
| 20 | MIN | ★ | 63 | 60 | 38.3% | $-6.33 | -5.9pp | 12 | -8 |
| 21 | ATL | ★ | 47 | 42 | 38.1% | $-6.17 | -6.2pp | 2 | -19 |
| 22 | ORL | ★ | 51 | 48 | 37.5% | $-6.27 | -6.7pp | 11 | -11 |
| 23 | GSW |  | 45 | 43 | 37.2% | $-6.20 | -7.0pp | — | — |
| 24 | NYK | ★ | 70 | 58 | 32.8% | $-10.41 | -11.5pp | 1 | -23 |
| 25 | MEM |  | 27 | 25 | 32.0% | $-8.60 | -12.2pp | — | — |
| 26 | DAL |  | 26 | 23 | 30.4% | $-3.83 | -13.8pp | — | — |
| 27 | CHI |  | 25 | 24 | 29.2% | $-8.37 | -15.1pp | — | — |
| 28 | MIL |  | 28 | 22 | 27.3% | $-9.76 | -17.0pp | — | — |
| 29 | SAC |  | 9 | 8 | 25.0% | $-9.49 | -19.2pp | — | — |
| 30 | WAS |  | 3 | 2 | 0.0% | $-19.67 | -44.2pp | — | — |

### Spearman rank-order correlation (playoff 16)

ρ = **-0.106**, approx p-value = 0.6903. Verdict: **NOT VALIDATED (ρ < 0.3)**.

Teams ordered by Kalshi rank. ESPN rank is the team's position in the ESPN-pooled hit-rate ordering (1 = highest). For teams that did not fire any S4A entry on ESPN, rank is —.

| Kalshi rank | Team | Kalshi hit% | ESPN hit% | ESPN rank | Rank Δ (K-E) |
|---:|---|---:|---:|---:|---:|
| 13 | DET | 53.8% | 45.8% | 9 | +4 |
| 4 | BOS | 66.7% | 53.8% | 3 | +1 |
| 1 | NYK | 78.6% | 32.8% | 16 | -15 |
| 3 | CLE | 70.6% | 45.2% | 10 | -7 |
| 14 | TOR | 44.4% | 53.3% | 4 | +10 |
| 2 | ATL | 75.0% | 38.1% | 14 | -12 |
| 9 | PHI | 60.0% | 39.5% | 12 | -3 |
| 11 | ORL | 54.5% | 37.5% | 15 | -4 |
| 6 | OKC | 64.7% | 58.1% | 2 | +4 |
| 8 | SAS | 61.5% | 58.8% | 1 | +7 |
| 7 | DEN | 61.9% | 47.1% | 5 | +2 |
| 15 | LAL | 44.4% | 42.5% | 11 | +4 |
| 16 | HOU | 30.4% | 45.9% | 7 | +9 |
| 12 | MIN | 54.5% | 38.3% | 13 | -1 |
| 5 | POR | 66.7% | 45.8% | 8 | -3 |
| 10 | PHX | 56.2% | 46.9% | 6 | +4 |

#### 3A sub-split: home vs away (playoff teams only)

| Team | Venue | Entries | Hit % |
|---|---|---:|---:|
| DET | home | 35 | 40.0% |
| DET | away | 24 | 54.2% |
| BOS | home | 31 | 48.4% |
| BOS | away | 21 | 61.9% |
| NYK | home | 32 | 31.2% |
| NYK | away | 26 | 34.6% |
| CLE | home | 34 | 38.2% |
| CLE | away | 28 | 53.6% |
| TOR | home | 26 | 53.8% |
| TOR | away | 19 | 52.6% |
| ATL | home | 24 | 41.7% |
| ATL | away | 18 | 33.3% |
| PHI | home | 24 | 41.7% |
| PHI | away | 14 | 35.7% |
| ORL | home | 30 | 30.0% |
| ORL | away | 18 | 50.0% |
| OKC | home | 32 | 56.2% |
| OKC | away | 30 | 60.0% |
| SAS | home | 32 | 59.4% |
| SAS | away | 19 | 57.9% |
| DEN | home | 27 | 48.1% |
| DEN | away | 24 | 45.8% |
| LAL | home | 23 | 52.2% |
| LAL | away | 17 | 29.4% |
| HOU | home | 31 | 48.4% |
| HOU | away | 30 | 43.3% |
| MIN | home | 34 | 32.4% |
| MIN | away | 26 | 46.2% |
| POR | home | 12 | 58.3% |
| POR | away | 12 | 33.3% |
| PHX | home | 18 | 38.9% |
| PHX | away | 14 | 57.1% |

#### 3A sub-split: spread magnitude (playoff teams only)

| Team | Spread | Entries | Hit % |
|---|---|---:|---:|
| DET | small (1-3) | 17 | 35.3% |
| DET | medium (3.5-6) | 13 | 46.2% |
| DET | large (6.5+) | 25 | 52.0% |
| BOS | small (1-3) | 6 | 33.3% |
| BOS | medium (3.5-6) | 13 | 53.8% |
| BOS | large (6.5+) | 28 | 64.3% |
| NYK | small (1-3) | 11 | 0.0% |
| NYK | medium (3.5-6) | 16 | 18.8% |
| NYK | large (6.5+) | 26 | 53.8% |
| CLE | small (1-3) | 11 | 36.4% |
| CLE | medium (3.5-6) | 12 | 33.3% |
| CLE | large (6.5+) | 33 | 51.5% |
| TOR | small (1-3) | 14 | 28.6% |
| TOR | medium (3.5-6) | 8 | 62.5% |
| TOR | large (6.5+) | 20 | 70.0% |
| ATL | small (1-3) | 13 | 23.1% |
| ATL | medium (3.5-6) | 10 | 40.0% |
| ATL | large (6.5+) | 15 | 60.0% |
| PHI | small (1-3) | 14 | 28.6% |
| PHI | medium (3.5-6) | 12 | 25.0% |
| PHI | large (6.5+) | 10 | 70.0% |
| ORL | small (1-3) | 9 | 77.8% |
| ORL | medium (3.5-6) | 17 | 23.5% |
| ORL | large (6.5+) | 19 | 36.8% |
| OKC | small (1-3) | 2 | 0.0% |
| OKC | medium (3.5-6) | 6 | 66.7% |
| OKC | large (6.5+) | 47 | 59.6% |
| SAS | small (1-3) | 7 | 28.6% |
| SAS | medium (3.5-6) | 20 | 60.0% |
| SAS | large (6.5+) | 19 | 73.7% |
| DEN | small (1-3) | 11 | 27.3% |
| DEN | medium (3.5-6) | 8 | 37.5% |
| DEN | large (6.5+) | 26 | 57.7% |
| LAL | small (1-3) | 10 | 30.0% |
| LAL | medium (3.5-6) | 12 | 33.3% |
| LAL | large (6.5+) | 15 | 53.3% |
| HOU | small (1-3) | 11 | 27.3% |
| HOU | medium (3.5-6) | 13 | 46.2% |
| HOU | large (6.5+) | 32 | 53.1% |
| MIN | small (1-3) | 11 | 18.2% |
| MIN | medium (3.5-6) | 10 | 30.0% |
| MIN | large (6.5+) | 35 | 45.7% |
| POR | small (1-3) | 5 | 60.0% |
| POR | medium (3.5-6) | 6 | 50.0% |
| POR | large (6.5+) | 11 | 36.4% |
| PHX | small (1-3) | 7 | 28.6% |
| PHX | medium (3.5-6) | 7 | 28.6% |
| PHX | large (6.5+) | 14 | 71.4% |

### 3B. Collapse rate as favorite (fav WP drops ≤ 0.40)

| Team | ★ | As-fav games | Collapse % | Home % | Away % |
|---|---|---:|---:|---:|---:|
| GSW |  | 45 | 68.9% | 64.3% | 76.5% |
| NYK | ★ | 70 | 64.3% | 59.0% | 71.0% |
| CHA |  | 36 | 50.0% | 45.5% | 57.1% |
| ORL | ★ | 51 | 68.6% | 71.9% | 63.2% |
| MIA |  | 43 | 51.2% | 53.3% | 46.2% |
| PHI | ★ | 41 | 63.4% | 69.2% | 53.3% |
| SAS | ★ | 63 | 46.0% | 45.9% | 46.2% |
| PHX | ★ | 35 | 54.3% | 60.0% | 46.7% |
| POR | ★ | 30 | 56.7% | 50.0% | 64.3% |
| OKC | ★ | 80 | 43.8% | 40.5% | 47.4% |
| HOU | ★ | 72 | 55.6% | 48.7% | 63.6% |
| LAL | ★ | 50 | 60.0% | 50.0% | 72.7% |
| CLE | ★ | 69 | 56.5% | 57.9% | 54.8% |
| BKN |  | 8 | 50.0% | 42.9% | 100.0% |
| ATL | ★ | 47 | 63.8% | 60.7% | 68.4% |
| TOR | ★ | 49 | 53.1% | 51.7% | 55.0% |
| BOS | ★ | 60 | 48.3% | 48.6% | 47.8% |
| DET | ★ | 68 | 54.4% | 61.5% | 44.8% |
| MEM |  | 27 | 77.8% | 76.5% | 80.0% |
| NOP |  | 14 | 57.1% | 62.5% | 50.0% |
| MIL |  | 28 | 71.4% | 68.8% | 75.0% |
| WAS |  | 3 | 100.0% | 100.0% | 0.0% |
| UTA |  | 6 | 50.0% | 50.0% | 0.0% |
| LAC |  | 44 | 56.8% | 42.9% | 81.2% |
| DAL |  | 26 | 73.1% | 75.0% | 70.0% |
| SAC |  | 9 | 88.9% | 87.5% | 100.0% |
| MIN | ★ | 63 | 66.7% | 69.4% | 63.0% |
| IND |  | 12 | 75.0% | 71.4% | 80.0% |
| DEN | ★ | 60 | 60.0% | 53.1% | 67.9% |
| CHI |  | 25 | 72.0% | 64.3% | 81.8% |

### 3C. Upset rate as underdog

Pooled upset rate across all 30 teams: 31.3% (386/1234).

| Team | ★ | As-dog | Wins | Upset % | Home % | Away % | Δ vs pooled |
|---|---|---:|---:|---:|---:|---:|---:|
| GSW |  | 38 | 12 | 31.6% | 15.4% | 40.0% | +0.3pp |
| NYK | ★ | 13 | 4 | 30.8% | 50.0% | 27.3% | -0.5pp |
| CHA |  | 47 | 19 | 40.4% | 30.0% | 48.1% | +9.1pp |
| ORL | ★ | 32 | 10 | 31.2% | 30.0% | 31.8% | -0.0pp |
| MIA |  | 40 | 15 | 37.5% | 63.6% | 27.6% | +6.2pp |
| PHI | ★ | 42 | 18 | 42.9% | 31.2% | 50.0% | +11.6pp |
| SAS | ★ | 20 | 12 | 60.0% | 100.0% | 52.9% | +28.7pp |
| PHX | ★ | 48 | 19 | 39.6% | 59.1% | 23.1% | +8.3pp |
| POR | ★ | 53 | 20 | 37.7% | 44.0% | 32.1% | +6.5pp |
| OKC | ★ | 2 | 0 | 0.0% | 0.0% | 0.0% | -31.3pp |
| HOU | ★ | 10 | 4 | 40.0% | 50.0% | 37.5% | +8.7pp |
| LAL | ★ | 32 | 15 | 46.9% | 46.2% | 47.4% | +15.6pp |
| CLE | ★ | 13 | 4 | 30.8% | 33.3% | 30.0% | -0.5pp |
| BKN |  | 74 | 15 | 20.3% | 20.6% | 20.0% | -11.0pp |
| ATL | ★ | 35 | 14 | 40.0% | 38.5% | 40.9% | +8.7pp |
| TOR | ★ | 33 | 13 | 39.4% | 33.3% | 42.9% | +8.1pp |
| BOS | ★ | 22 | 11 | 50.0% | 75.0% | 44.4% | +18.7pp |
| DET | ★ | 14 | 10 | 71.4% | 50.0% | 75.0% | +40.1pp |
| MEM |  | 55 | 10 | 18.2% | 25.0% | 12.9% | -13.1pp |
| NOP |  | 68 | 15 | 22.1% | 30.3% | 14.3% | -9.2pp |
| MIL |  | 54 | 17 | 31.5% | 36.0% | 27.6% | +0.2pp |
| WAS |  | 79 | 17 | 21.5% | 28.9% | 14.6% | -9.8pp |
| UTA |  | 76 | 18 | 23.7% | 28.6% | 19.5% | -7.6pp |
| LAC |  | 38 | 14 | 36.8% | 42.9% | 33.3% | +5.6pp |
| DAL |  | 56 | 14 | 25.0% | 36.0% | 16.1% | -6.3pp |
| SAC |  | 73 | 16 | 21.9% | 27.3% | 17.5% | -9.4pp |
| MIN | ★ | 19 | 6 | 31.6% | 40.0% | 28.6% | +0.3pp |
| IND |  | 70 | 14 | 20.0% | 20.6% | 19.4% | -11.3pp |
| DEN | ★ | 22 | 12 | 54.5% | 44.4% | 61.5% | +23.3pp |
| CHI |  | 56 | 18 | 32.1% | 34.6% | 30.0% | +0.9pp |

### 3D. Underdog peak WP

| Team | ★ | As-dog games | Mean peak | Peak ≥ 0.50 % | Peak ≥ 0.65 % |
|---|---|---:|---:|---:|---:|
| GSW |  | 38 | 0.700 | 84.2% | 55.3% |
| NYK | ★ | 13 | 0.776 | 92.3% | 61.5% |
| CHA |  | 47 | 0.768 | 78.7% | 68.1% |
| ORL | ★ | 32 | 0.732 | 87.5% | 59.4% |
| MIA |  | 40 | 0.775 | 92.5% | 67.5% |
| PHI | ★ | 42 | 0.707 | 71.4% | 61.9% |
| SAS | ★ | 20 | 0.898 | 95.0% | 95.0% |
| PHX | ★ | 48 | 0.761 | 81.2% | 66.7% |
| POR | ★ | 53 | 0.692 | 73.6% | 58.5% |
| OKC | ★ | 2 | 0.560 | 50.0% | 50.0% |
| HOU | ★ | 10 | 0.827 | 80.0% | 70.0% |
| LAL | ★ | 32 | 0.711 | 78.1% | 53.1% |
| CLE | ★ | 13 | 0.740 | 84.6% | 53.8% |
| BKN |  | 74 | 0.550 | 48.6% | 35.1% |
| ATL | ★ | 35 | 0.747 | 85.7% | 54.3% |
| TOR | ★ | 33 | 0.736 | 75.8% | 57.6% |
| BOS | ★ | 22 | 0.839 | 95.5% | 86.4% |
| DET | ★ | 14 | 0.887 | 92.9% | 85.7% |
| MEM |  | 55 | 0.656 | 65.5% | 52.7% |
| NOP |  | 68 | 0.644 | 67.6% | 50.0% |
| MIL |  | 54 | 0.629 | 61.1% | 48.1% |
| WAS |  | 79 | 0.488 | 39.2% | 31.6% |
| UTA |  | 76 | 0.612 | 64.5% | 48.7% |
| LAC |  | 38 | 0.741 | 78.9% | 68.4% |
| DAL |  | 56 | 0.631 | 57.1% | 44.6% |
| SAC |  | 73 | 0.581 | 54.8% | 38.4% |
| MIN | ★ | 19 | 0.778 | 89.5% | 89.5% |
| IND |  | 70 | 0.611 | 61.4% | 42.9% |
| DEN | ★ | 22 | 0.807 | 81.8% | 77.3% |
| CHI |  | 56 | 0.646 | 66.1% | 48.2% |

## Section 4 — Period-specific S4A tendencies

| Team | ★ | Q1 n | Q1 hit% | Q2 n | Q2 hit% | Q3 n | Q3 hit% | Q4 n | Q4 hit% | Dom Q |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| GSW |  | 39 | 38.5% | 2 | 50.0% | 2 | 0.0% | 0 | — | Q1 |
| NYK | ★ | 52 | 26.9% | 4 | 75.0% | 2 | 100.0% | 0 | — | Q1 |
| CHA |  | 26 | 46.2% | 1 | 0.0% | 0 | — | 0 | — | Q1 |
| ORL | ★ | 43 | 32.6% | 2 | 100.0% | 1 | 100.0% | 1 | 100.0% | Q1 |
| MIA |  | 36 | 52.8% | 3 | 33.3% | 0 | — | 0 | — | Q1 |
| PHI | ★ | 26 | 42.3% | 8 | 37.5% | 1 | 0.0% | 3 | 33.3% | Q1 |
| SAS | ★ | 44 | 54.5% | 5 | 80.0% | 1 | 100.0% | 1 | 100.0% | Q1 |
| PHX | ★ | 29 | 48.3% | 3 | 33.3% | 0 | — | 0 | — | Q1 |
| POR | ★ | 22 | 40.9% | 2 | 100.0% | 0 | — | 0 | — | Q1 |
| OKC | ★ | 44 | 50.0% | 11 | 81.8% | 7 | 71.4% | 0 | — | Q1 |
| HOU | ★ | 50 | 48.0% | 6 | 50.0% | 4 | 25.0% | 1 | 0.0% | Q1 |
| LAL | ★ | 32 | 37.5% | 4 | 50.0% | 2 | 50.0% | 2 | 100.0% | Q1 |
| CLE | ★ | 48 | 39.6% | 9 | 66.7% | 2 | 50.0% | 3 | 66.7% | Q1 |
| BKN |  | 5 | 80.0% | 1 | 100.0% | 0 | — | 0 | — | Q1 |
| ATL | ★ | 34 | 32.4% | 5 | 60.0% | 2 | 50.0% | 1 | 100.0% | Q1 |
| TOR | ★ | 38 | 50.0% | 3 | 66.7% | 3 | 100.0% | 1 | 0.0% | Q1 |
| BOS | ★ | 45 | 51.1% | 4 | 75.0% | 1 | 0.0% | 2 | 100.0% | Q1 |
| DET | ★ | 50 | 46.0% | 5 | 40.0% | 2 | 50.0% | 2 | 50.0% | Q1 |
| MEM |  | 22 | 31.8% | 1 | 0.0% | 2 | 50.0% | 0 | — | Q1 |
| NOP |  | 12 | 50.0% | 1 | 100.0% | 1 | 100.0% | 0 | — | Q1 |
| MIL |  | 17 | 23.5% | 4 | 50.0% | 1 | 0.0% | 0 | — | Q1 |
| WAS |  | 2 | 0.0% | 0 | — | 0 | — | 0 | — | Q1 |
| UTA |  | 3 | 66.7% | 1 | 0.0% | 0 | — | 0 | — | Q1 |
| LAC |  | 30 | 36.7% | 3 | 66.7% | 3 | 100.0% | 0 | — | Q1 |
| DAL |  | 21 | 28.6% | 2 | 50.0% | 0 | — | 0 | — | Q1 |
| SAC |  | 7 | 14.3% | 0 | — | 1 | 100.0% | 0 | — | Q1 |
| MIN | ★ | 54 | 38.9% | 4 | 25.0% | 0 | — | 2 | 50.0% | Q1 |
| IND |  | 11 | 45.5% | 0 | — | 0 | — | 0 | — | Q1 |
| DEN | ★ | 39 | 46.2% | 10 | 60.0% | 1 | 0.0% | 1 | 0.0% | Q1 |
| CHI |  | 20 | 30.0% | 4 | 25.0% | 0 | — | 0 | — | Q1 |

## Section 5 — Summary scorecards

### 5A. S4A tier list (all 30 teams)

- **Tier 1** (≥60%), **Tier 2** (45-59%), **Tier 3** (<45%)

| Tier | Team | ★ | Entries | Hit % | Mean P&L |
|---|---|---|---:|---:|---:|
| Tier 1 | BKN |  | 6 | 83.3% | $+18.02 |
| Tier 2 | SAS | ★ | 51 | 58.8% | $+2.47 |
| Tier 2 | OKC | ★ | 62 | 58.1% | $-1.19 |
| Tier 2 | NOP |  | 14 | 57.1% | $+2.71 |
| Tier 2 | BOS | ★ | 52 | 53.8% | $+1.60 |
| Tier 2 | TOR | ★ | 45 | 53.3% | $+0.24 |
| Tier 2 | MIA |  | 39 | 51.3% | $-2.11 |
| Tier 2 | UTA |  | 4 | 50.0% | $+2.57 |
| Tier 2 | DEN | ★ | 51 | 47.1% | $-2.14 |
| Tier 2 | PHX | ★ | 32 | 46.9% | $+0.78 |
| Tier 2 | HOU | ★ | 61 | 45.9% | $-3.04 |
| Tier 2 | POR | ★ | 24 | 45.8% | $+2.47 |
| Tier 2 | DET | ★ | 59 | 45.8% | $-3.47 |
| Tier 2 | IND |  | 11 | 45.5% | $-3.66 |
| Tier 2 | CLE | ★ | 62 | 45.2% | $-5.05 |
| Tier 3 | CHA |  | 27 | 44.4% | $-2.59 |
| Tier 3 | LAC |  | 36 | 44.4% | $-3.69 |
| Tier 3 | LAL | ★ | 40 | 42.5% | $-4.09 |
| Tier 3 | PHI | ★ | 38 | 39.5% | $-5.80 |
| Tier 3 | MIN | ★ | 60 | 38.3% | $-6.33 |
| Tier 3 | ATL | ★ | 42 | 38.1% | $-6.17 |
| Tier 3 | ORL | ★ | 48 | 37.5% | $-6.27 |
| Tier 3 | GSW |  | 43 | 37.2% | $-6.20 |
| Tier 3 | NYK | ★ | 58 | 32.8% | $-10.41 |
| Tier 3 | MEM |  | 25 | 32.0% | $-8.60 |
| Tier 3 | DAL |  | 23 | 30.4% | $-3.83 |
| Tier 3 | CHI |  | 24 | 29.2% | $-8.37 |
| Tier 3 | MIL |  | 22 | 27.3% | $-9.76 |
| Tier 3 | SAC |  | 8 | 25.0% | $-9.49 |
| Tier 3 | WAS |  | 2 | 0.0% | $-19.67 |

### 5B. Sample-size CIs (95% Wilson)

Pooled ESPN hit rate: 44.2%. Significance is vs this ESPN-pooled rate.

| Team | ★ | Entries | Hit % | CI low | CI high | Significant vs pooled? |
|---|---|---:|---:|---:|---:|---|
| GSW |  | 43 | 37.2% | 24.4% | 52.1% | no |
| NYK | ★ | 58 | 32.8% | 22.1% | 45.6% | no |
| CHA |  | 27 | 44.4% | 27.6% | 62.7% | no |
| ORL | ★ | 48 | 37.5% | 25.2% | 51.6% | no |
| MIA |  | 39 | 51.3% | 36.2% | 66.1% | no |
| PHI | ★ | 38 | 39.5% | 25.6% | 55.3% | no |
| SAS | ★ | 51 | 58.8% | 45.2% | 71.2% | yes (above) |
| PHX | ★ | 32 | 46.9% | 30.9% | 63.6% | no |
| POR | ★ | 24 | 45.8% | 27.9% | 64.9% | no |
| OKC | ★ | 62 | 58.1% | 45.7% | 69.5% | yes (above) |
| HOU | ★ | 61 | 45.9% | 34.0% | 58.3% | no |
| LAL | ★ | 40 | 42.5% | 28.5% | 57.8% | no |
| CLE | ★ | 62 | 45.2% | 33.4% | 57.5% | no |
| BKN |  | 6 | 83.3% | 43.6% | 97.0% | no |
| ATL | ★ | 42 | 38.1% | 25.0% | 53.2% | no |
| TOR | ★ | 45 | 53.3% | 39.1% | 67.1% | no |
| BOS | ★ | 52 | 53.8% | 40.5% | 66.7% | no |
| DET | ★ | 59 | 45.8% | 33.7% | 58.3% | no |
| MEM |  | 25 | 32.0% | 17.2% | 51.6% | no |
| NOP |  | 14 | 57.1% | 32.6% | 78.6% | no |
| MIL |  | 22 | 27.3% | 13.2% | 48.2% | no |
| WAS |  | 2 | 0.0% | 0.0% | 65.8% | no |
| UTA |  | 4 | 50.0% | 15.0% | 85.0% | no |
| LAC |  | 36 | 44.4% | 29.5% | 60.4% | no |
| DAL |  | 23 | 30.4% | 15.6% | 50.9% | no |
| SAC |  | 8 | 25.0% | 7.1% | 59.1% | no |
| MIN | ★ | 60 | 38.3% | 27.1% | 51.0% | no |
| IND |  | 11 | 45.5% | 21.3% | 72.0% | no |
| DEN | ★ | 51 | 47.1% | 34.1% | 60.5% | no |
| CHI |  | 24 | 29.2% | 14.9% | 49.2% | no |

### 5C. If-we-filtered S4A aggregate EV

Only trades where the favorite team is in the specified universe. ESPN-scale P&L — not directly comparable to Kalshi.

| Universe | Games | Entries | Hit % | Mean P&L | Annual EV (ESPN-scale) |
|---|---:|---:|---:|---:|---:|
| All 30 teams (baseline) | 1234 | 1069 | 44.2% | $-3.54 | $-1,676 |
| Tier 1 only | 8 | 6 | 83.3% | $+18.02 | $+7,395 |
| Tier 3 excluded (= Tier 1 + 2) | 669 | 573 | 50.8% | $-0.96 | $-449 |

### 5D. Kalshi ↔ ESPN validation summary (playoff 16)

| Team | Kalshi hit% | ESPN hit% | Kalshi tier | ESPN tier | Tier match? |
|---|---:|---:|---|---|---|
| DET | 53.8% | 45.8% | Tier 2 | Tier 2 | yes |
| BOS | 66.7% | 53.8% | Tier 1 | Tier 2 | no |
| NYK | 78.6% | 32.8% | Tier 1 | Tier 3 | no |
| CLE | 70.6% | 45.2% | Tier 1 | Tier 2 | no |
| TOR | 44.4% | 53.3% | Tier 3 | Tier 2 | no |
| ATL | 75.0% | 38.1% | Tier 1 | Tier 3 | no |
| PHI | 60.0% | 39.5% | Tier 1 | Tier 3 | no |
| ORL | 54.5% | 37.5% | Tier 2 | Tier 3 | no |
| OKC | 64.7% | 58.1% | Tier 1 | Tier 2 | no |
| SAS | 61.5% | 58.8% | Tier 1 | Tier 2 | no |
| DEN | 61.9% | 47.1% | Tier 1 | Tier 2 | no |
| LAL | 44.4% | 42.5% | Tier 3 | Tier 3 | yes |
| HOU | 30.4% | 45.9% | Tier 3 | Tier 2 | no |
| MIN | 54.5% | 38.3% | Tier 2 | Tier 3 | no |
| POR | 66.7% | 45.8% | Tier 1 | Tier 2 | no |
| PHX | 56.2% | 46.9% | Tier 2 | Tier 2 | yes |

**Tier-match count:** 3/16 (18.8%).

**Spearman ρ (rank correlation):** -0.106 (p ≈ 0.6903).

**Verdict:** **NOT VALIDATED (ρ < 0.3)**.

**HOU significance check:** ESPN HOU hit rate 45.9% on 61 entries, 95% CI (34.0%, 58.3%) vs ESPN pooled 44.2%. HOU is statistically significantly below pooled: **no**.

## Section 6 — Data-driven pattern discovery

### 6A. Biggest outliers (all 30 teams, |Z| ≥ 1.5)

| Team | ★ | Metric | Value | Mean | Z | Direction |
|---|---|---|---:|---:|---:|---|
| SAC |  | mean_swings_fav | 23.000 | 14.295 | +3.33 | HIGH |
| DET | ★ | upset_pct | 71.429 | 35.496 | +2.85 | HIGH |
| WAS |  | mean_range_dog | 0.440 | 0.619 | -2.71 | LOW |
| SAC |  | collapse_pct | 88.889 | 60.608 | +2.65 | HIGH |
| WAS |  | mean_swings_dog | 9.228 | 14.771 | -2.56 | LOW |
| IND |  | mean_range_fav | 0.716 | 0.603 | +2.50 | HIGH |
| WAS |  | crossed_050_pct_dog | 39.241 | 75.355 | -2.47 | LOW |
| OKC | ★ | mean_range_fav | 0.497 | 0.603 | -2.35 | LOW |
| WAS |  | dog_mean_peak | 0.488 | 0.713 | -2.31 | LOW |
| OKC | ★ | crossed_050_pct_fav | 48.750 | 72.272 | -2.23 | LOW |
| SAS | ★ | mean_range_dog | 0.752 | 0.619 | +2.01 | HIGH |
| BKN |  | mean_swings_dog | 10.432 | 14.771 | -2.01 | LOW |
| SAS | ★ | upset_pct | 60.000 | 35.496 | +1.94 | HIGH |
| BKN |  | mean_range_dog | 0.493 | 0.619 | -1.91 | LOW |
| SAS | ★ | dog_mean_peak | 0.898 | 0.713 | +1.90 | HIGH |
| SAS | ★ | crossed_050_pct_fav | 52.381 | 72.272 | -1.88 | LOW |
| IND |  | crossed_050_pct_fav | 91.667 | 72.272 | +1.84 | HIGH |
| BKN |  | crossed_050_pct_dog | 48.649 | 75.355 | -1.83 | LOW |
| MIL |  | s4a_hit_pct | 27.273 | 43.391 | -1.81 | LOW |
| DET | ★ | dog_mean_peak | 0.887 | 0.713 | +1.79 | HIGH |
| DEN | ★ | mean_swings_dog | 18.636 | 14.771 | +1.79 | HIGH |
| UTA |  | mean_swings_fav | 9.667 | 14.295 | -1.77 | LOW |
| SAS | ★ | s4a_hit_pct | 58.824 | 43.391 | +1.73 | HIGH |
| MEM |  | mean_range_fav | 0.680 | 0.603 | +1.72 | HIGH |
| MEM |  | mean_swings_fav | 18.778 | 14.295 | +1.71 | HIGH |

### 6B. Personality clusters (all 30 teams)

| Team | ★ | Cluster |
|---|---|---|
| GSW |  | Volatile oscillator |
| NYK | ★ | Low-volatility favorite |
| CHA |  | Scrappy underdog |
| ORL | ★ | Volatile oscillator |
| MIA |  | Uncategorized |
| PHI | ★ | Volatile oscillator |
| SAS | ★ | Low-volatility favorite |
| PHX | ★ | Low-volatility favorite |
| POR | ★ | Uncategorized |
| OKC | ★ | Low-volatility favorite |
| HOU | ★ | Uncategorized |
| LAL | ★ | Scrappy underdog |
| CLE | ★ | Volatile oscillator |
| BKN |  | Steady dominator |
| ATL | ★ | Scrappy underdog |
| TOR | ★ | Low-volatility favorite |
| BOS | ★ | Low-volatility favorite |
| DET | ★ | Low-volatility favorite |
| MEM |  | Volatile oscillator |
| NOP |  | Low-volatility favorite |
| MIL |  | Volatile oscillator |
| WAS |  | Volatile oscillator |
| UTA |  | Low-volatility favorite |
| LAC |  | Scrappy underdog |
| DAL |  | Volatile oscillator |
| SAC |  | Volatile oscillator |
| MIN | ★ | Volatile oscillator |
| IND |  | Uncategorized |
| DEN | ★ | Volatile oscillator |
| CHI |  | Volatile oscillator |

Cluster counts: Volatile oscillator: 12, Low-volatility favorite: 9, Scrappy underdog: 4, Uncategorized: 4, Steady dominator: 1.

### 6C. Home-away asymmetry standouts

Teams with min 5 entries in each venue, sorted by |Δ|.

| Team | ★ | Home hit% | Away hit% | Δ | Home n | Away n |
|---|---|---:|---:|---:|---:|---:|
| LAC |  | 60.9% | 15.4% | +45.5pp | 23 | 13 |
| CHA |  | 55.6% | 22.2% | +33.3pp | 18 | 9 |
| POR | ★ | 58.3% | 33.3% | +25.0pp | 12 | 12 |
| DAL |  | 21.4% | 44.4% | -23.0pp | 14 | 9 |
| LAL | ★ | 52.2% | 29.4% | +22.8pp | 23 | 17 |
| CHI |  | 38.5% | 18.2% | +20.3pp | 13 | 11 |
| ORL | ★ | 30.0% | 50.0% | -20.0pp | 30 | 18 |
| MEM |  | 40.0% | 20.0% | +20.0pp | 15 | 10 |
| PHX | ★ | 38.9% | 57.1% | -18.3pp | 18 | 14 |
| NOP |  | 50.0% | 66.7% | -16.7pp | 8 | 6 |
| CLE | ★ | 38.2% | 53.6% | -15.3pp | 34 | 28 |
| DET | ★ | 40.0% | 54.2% | -14.2pp | 35 | 24 |

### 6D. Period-specific standouts (min 5 entries)

**Top 10 team × period by hit rate:**

| Team | ★ | Period | Entries | Hit % |
|---|---|---|---:|---:|
| OKC | ★ | Q2 | 11 | 81.8% |
| BKN |  | Q1 | 5 | 80.0% |
| SAS | ★ | Q2 | 5 | 80.0% |
| OKC | ★ | Q3 | 7 | 71.4% |
| CLE | ★ | Q2 | 9 | 66.7% |
| ATL | ★ | Q2 | 5 | 60.0% |
| DEN | ★ | Q2 | 10 | 60.0% |
| SAS | ★ | Q1 | 44 | 54.5% |
| MIA |  | Q1 | 36 | 52.8% |
| BOS | ★ | Q1 | 45 | 51.1% |

**Bottom 10 team × period by hit rate:**

| Team | ★ | Period | Entries | Hit % |
|---|---|---|---:|---:|
| PHI | ★ | Q2 | 8 | 37.5% |
| LAC |  | Q1 | 30 | 36.7% |
| ORL | ★ | Q1 | 43 | 32.6% |
| ATL | ★ | Q1 | 34 | 32.4% |
| MEM |  | Q1 | 22 | 31.8% |
| CHI |  | Q1 | 20 | 30.0% |
| DAL |  | Q1 | 21 | 28.6% |
| NYK | ★ | Q1 | 52 | 26.9% |
| MIL |  | Q1 | 17 | 23.5% |
| SAC |  | Q1 | 7 | 14.3% |

---

Validation analysis. Findings inform engine parameterization but do not constitute a new strategy.

