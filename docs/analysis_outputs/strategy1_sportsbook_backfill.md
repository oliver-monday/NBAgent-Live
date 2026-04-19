# Strategy 1 sportsbook backfill — 2026-04-19

Targeted historical Odds API backfill at the exact moments of bilateral <0.20 dips identified from ESPN data. Each dip moment produces one sportsbook consensus observation per available bookmaker, no-vig normalized. The question answered: **do real-money sportsbooks agree with ESPN at the moments that drive Strategy 1's opportunity rate?**


=== A. Sample summary ===

## A. Sample summary

| Stat | Value |
|------|-------|
| Bilateral games in population | ~146 |
| Sample size | 30 |
| API calls made | 90 |
| Credits remaining (per headers) | 18720 |
| Bookmaker rows (total) | 408 |
| Bookmaker rows (fresh, last_update within 5 min) | 341 |
| Stale rows excluded from consensus | 67 |
| Failures | 1 |

=== B. Per-game dip comparison ===

## B. Per-game dip comparison

| gameId | date | away | home | spread | side | ESPN WP | SB consensus | residual (pp) | n_books |
|--------|------|------|------|--------|------|---------|--------------|---------------|---------|
| 401810344 | 2026-01-03 | CHA | CHI | -1.5 | home_dip | 0.001 | 0.161 | +15.98pp | 8 |
| 401810796 | 2026-03-10 | PHX | MIL | +1.5 | home_dip | 0.001 | 0.034 | +3.27pp | 3 |
| 401810752 | 2026-03-04 | ATL | MIL | -1.0 | home_dip | 0.001 | 0.051 | +4.99pp | 5 |
| 401810737 | 2026-03-02 | LAC | GSW | +1.0 | home_dip | 0.001 | 0.052 | +5.06pp | 2 |
| 401810726 | 2026-03-01 | MIN | DEN | -3.0 | home_dip | 0.001 | 0.113 | +11.18pp | 8 |
| 401810572 | 2026-02-03 | UTA | IND | +2.5 | home_dip | 0.001 | 0.073 | +7.21pp | 6 |
| 401810481 | 2026-01-21 | TOR | SAC | +5.5 | home_dip | 0.001 | 0.057 | +5.56pp | 5 |
| 401810441 | 2026-01-15 | CHA | LAL | -3.0 | home_dip | 0.001 | 0.046 | +4.49pp | 4 |
| 401810411 | 2026-01-11 | ATL | GSW | -6.0 | home_dip | 0.001 | 0.141 | +14.02pp | 5 |
| 401810311 | 2025-12-29 | CLE | SAS | -3.0 | home_dip | 0.001 | 0.080 | +7.88pp | 7 |
| 401810302 | 2025-12-29 | MIL | CHA | +3.5 | home_dip | 0.001 | 0.127 | +12.59pp | 6 |
| 401810286 | 2025-12-26 | LAC | POR | +2.5 | home_dip | 0.001 | 0.229 | +22.79pp | 2 |
| 401810190 | 2025-12-04 | UTA | BKN | +5.0 | home_dip | 0.001 | 0.206 | +20.45pp | 7 |
| 401810172 | 2025-12-01 | PHX | LAL | -5.0 | home_dip | 0.001 | 0.099 | +9.80pp | 8 |
| 401811012 | 2026-04-07 | HOU | PHX | -1.5 | home_dip | 0.001 | 0.074 | +7.31pp | 8 |
| 401809506 | 2025-10-31 | LAL | MEM | +2.0 | home_dip | 0.001 | 0.078 | +7.66pp | 6 |
| 401810072 | 2025-11-12 | CLE | MIA | -5.5 | home_dip | 0.001 | 0.050 | +4.95pp | 3 |
| 401809512 | 2025-11-07 | TOR | ATL | -2.0 | home_dip | 0.001 | 0.090 | +8.91pp | 3 |
| 401809964 | 2025-10-26 | CHA | WAS | -1.5 | home_dip | 0.001 | 0.084 | +8.32pp | 6 |
| 401810167 | 2025-12-01 | CHA | BKN | +4.5 | away_dip | 0.001 | 0.061 | +6.02pp | 6 |
| 401810783 | 2026-03-08 | CHA | PHX | +4.5 | away_dip | 0.001 | 0.074 | +7.31pp | 3 |
| 401810161 | 2025-11-30 | SAS | MIN | -5.0 | away_dip | 0.001 | 0.052 | +5.11pp | 2 |
| 401810667 | 2026-02-21 | PHI | NOP | +3.5 | away_dip | 0.001 | 0.077 | +7.65pp | 6 |
| 401809783 | 2025-11-14 | PHI | DET | -1.0 | away_dip | 0.001 | 0.126 | +12.49pp | 7 |
| 401810066 | 2025-11-11 | IND | UTA | +3.0 | away_dip | 0.001 | 0.029 | +2.78pp | 1 |
| 401809505 | 2025-10-31 | NYK | CHI | +5.0 | away_dip | 0.002 | 0.157 | +15.53pp | 3 |
| 401810595 | 2026-02-05 | PHI | LAL | -3.5 | away_dip | 0.003 | 0.114 | +11.09pp | 7 |
| 401810922 | 2026-03-27 | ATL | BOS | -5.5 | away_dip | 0.010 | 0.093 | +8.26pp | 6 |
| 401810671 | 2026-02-21 | HOU | NYK | -4.0 | home_dip | 0.013 | 0.087 | +7.41pp | 5 |
| 401810072 | 2025-11-12 | CLE | MIA | -5.5 | away_dip | 0.041 | 0.185 | +14.37pp | 8 |
| 401810737 | 2026-03-02 | LAC | GSW | +1.0 | away_dip | 0.069 | 0.210 | +14.08pp | 8 |
| 401809783 | 2025-11-14 | PHI | DET | -1.0 | home_dip | 0.069 | 0.193 | +12.40pp | 8 |
| 401811012 | 2026-04-07 | HOU | PHX | -1.5 | away_dip | 0.083 | 0.235 | +15.15pp | 8 |
| 401809506 | 2025-10-31 | LAL | MEM | +2.0 | away_dip | 0.098 | 0.213 | +11.53pp | 8 |
| 401810190 | 2025-12-04 | UTA | BKN | +5.0 | away_dip | 0.100 | 0.324 | +22.45pp | 8 |
| 401809512 | 2025-11-07 | TOR | ATL | -2.0 | away_dip | 0.102 | 0.270 | +16.80pp | 8 |
| 401810344 | 2026-01-03 | CHA | CHI | -1.5 | away_dip | 0.114 | 0.241 | +12.65pp | 8 |
| 401810286 | 2025-12-26 | LAC | POR | +2.5 | away_dip | 0.122 | 0.363 | +24.07pp | 7 |
| 401809964 | 2025-10-26 | CHA | WAS | -1.5 | away_dip | 0.122 | 0.245 | +12.29pp | 8 |
| 401810441 | 2026-01-15 | CHA | LAL | -3.0 | away_dip | 0.124 | 0.277 | +15.26pp | 7 |
| 401810311 | 2025-12-29 | CLE | SAS | -3.0 | away_dip | 0.134 | 0.245 | +11.11pp | 8 |
| 401810671 | 2026-02-21 | HOU | NYK | -4.0 | away_dip | 0.135 | 0.308 | +17.26pp | 8 |
| 401810667 | 2026-02-21 | PHI | NOP | +3.5 | home_dip | 0.135 | 0.253 | +11.80pp | 7 |
| 401810595 | 2026-02-05 | PHI | LAL | -3.5 | home_dip | 0.137 | 0.342 | +20.51pp | 5 |
| 401810752 | 2026-03-04 | ATL | MIL | -1.0 | away_dip | 0.158 | 0.250 | +9.15pp | 8 |
| 401810161 | 2025-11-30 | SAS | MIN | -5.0 | home_dip | 0.160 | 0.425 | +26.49pp | 3 |
| 401810922 | 2026-03-27 | ATL | BOS | -5.5 | home_dip | 0.161 | 0.427 | +26.57pp | 6 |
| 401810572 | 2026-02-03 | UTA | IND | +2.5 | away_dip | 0.162 | 0.467 | +30.52pp | 2 |
| 401810440 | 2026-01-15 | ATL | POR | +4.0 | home_dip | 0.163 | 0.277 | +11.36pp | 7 |
| 401810302 | 2025-12-29 | MIL | CHA | +3.5 | away_dip | 0.171 | 0.346 | +17.52pp | 7 |
| 401810172 | 2025-12-01 | PHX | LAL | -5.0 | away_dip | 0.175 | 0.262 | +8.65pp | 8 |
| 401810167 | 2025-12-01 | CHA | BKN | +4.5 | home_dip | 0.177 | 0.267 | +8.95pp | 7 |
| 401810726 | 2026-03-01 | MIN | DEN | -3.0 | away_dip | 0.180 | 0.328 | +14.79pp | 6 |
| 401810796 | 2026-03-10 | PHX | MIL | +1.5 | away_dip | 0.189 | 0.440 | +25.09pp | 6 |
| 401810783 | 2026-03-08 | CHA | PHX | +4.5 | home_dip | 0.189 | 0.274 | +8.54pp | 8 |
| 401810481 | 2026-01-21 | TOR | SAC | +5.5 | away_dip | 0.192 | 0.331 | +13.90pp | 6 |
| 401809505 | 2025-10-31 | NYK | CHI | +5.0 | home_dip | 0.194 | 0.370 | +17.62pp | 5 |

=== C. Pooled residual at dip moments ===

## C. Pooled residual at dip moments

| Stat | Value |
|------|-------|
| n (dip observations) | 57 |
| mean ESPN WP at dip | 0.0686 |
| mean SB consensus at dip | 0.1944 |
| mean residual (pp) | +12.58 |
| median residual (pp) | +11.53 |
| std | 0.0646 |

#### D. Residual stratified by ESPN WP bucket at dip

| bucket | n | mean ESPN | mean SB | residual (pp) |
|--------|---|-----------|---------|---------------|
| (-0.001, 0.05] | 30 | 0.003 | 0.097 | +9.35 |
| (0.05, 0.1] | 5 | 0.084 | 0.235 | +15.12 |
| (0.1, 0.15] | 9 | 0.125 | 0.283 | +15.75 |
| (0.15, 0.2] | 13 | 0.175 | 0.343 | +16.86 |

=== E. Cross-book variance at dip moments ===

## E. Cross-book variance at dip moments

| Stat | Value |
|------|-------|
| mean cross-book std (no-vig) | 0.0332 |
| p95 cross-book std | 0.0861 |
| mean overround (vig indicator) | 1.0549 |

=== F. Preliminary Strategy 1 assessment ===

## F. Preliminary Strategy 1 assessment

Sportsbooks show strong compression matching the Kalshi pattern (mean residual +12.58pp). Strategy 1's bilateral <0.20 opportunity rate on real-money markets is substantially lower than ESPN's 26.6% suggests. The bilateral opportunity may still exist at wider thresholds (e.g., <0.30 on sportsbook-implied WP), but per-trade gross profit shrinks and fee/spread drag becomes a larger share. Re-examine Strategy 1's graduation bar against the actual residual shape.
Sportsbooks show strong compression matching the Kalshi pattern (mean residual +12.58pp). Strategy 1's bilateral <0.20 opportunity rate on real-money markets is substantially lower than ESPN's 26.6% suggests. The bilateral opportunity may still exist at wider thresholds (e.g., <0.30 on sportsbook-implied WP), but per-trade gross profit shrinks and fee/spread drag becomes a larger share. Re-examine Strategy 1's graduation bar against the actual residual shape.

**Sample size note:** 30 games with two dip moments each ≈ 60 dip observations. A sample-based estimate; formal Strategy 1 conclusions require Phase 3B-scale validation once the Kalshi dataset grows.

## Failures

| game_id | reason | detail |
|---|---|---|
| 401810440 | no_bookmakers_parsed | moment=away_dip, matchup=ATL@POR |
