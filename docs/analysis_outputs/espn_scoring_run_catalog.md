# ESPN-scale scoring-run pattern catalog

_Competitive filter: |spread| ≤ 6.0_

ESPN-WP-based characterization of scoring runs, timeout association, post-run trajectories, prior degradation, and favorite/underdog recovery asymmetry across the full 2025-26 regular season. Complements the n=2 Kalshi-level `scoring_run_trajectories.py` at 600× the sample size.

**ESPN caveat (important).** ESPN WP is more reactive than real-money markets at the tails (+10-17pp compression per Phase 3B sportsbook backfill). Absolute WP swing magnitudes here are upper bounds on Kalshi/sportsbook equivalents. Relative patterns (which runs, periods, magnitudes produce recovery) should transfer; absolute magnitudes will be smaller on Kalshi.

## Section 1 — Scoring-run frequency

### Table 1 — Run frequency by parameter set

| Params (margin, window) | Total runs | Runs/game | Games w/ ≥1 run | % of games |
|---|---:|---:|---:|---:|
| (6, 2min) | 5,375 | 9.79 | 549 | 100% |
| (6, 3min) | 6,210 | 11.31 | 549 | 100% |
| (8, 3min) | 3,316 | 6.04 | 546 | 99% |
| (8, 4min) | 3,919 | 7.14 | 549 | 100% |
| (10, 4min) | 2,023 | 3.68 | 516 | 94% |

## Section 2 — Timeout association

### Table 2 — Timeout association (primary: (6, 3))

| Context | n runs | % followed by timeout (≤ 90s) | % called by trailing team (of those) |
|---|---:|---:|---:|
| All runs | 6,210 | 36% | 66% |
| Favorite trailing | 2,947 | 36% | 63% |
| Underdog trailing | 3,263 | 36% | 69% |

## Section 3 — Post-run WP trajectory

### Table 3 — Post-run recovery, (6, 3) (n=6210)

| Metric | Mean | Median | % positive | n |
|---|---:|---:|---:|---:|
| Recovery @ 1 min | +0.0173 | +0.0050 | 55% | 6085 |
| Recovery @ 2 min | +0.0206 | +0.0050 | 54% | 5939 |
| Recovery @ 3 min | +0.0229 | +0.0040 | 52% | 5818 |
| Recovery @ 5 min | +0.0250 | +0.0030 | 52% | 5563 |
| Max recovery | +0.1200 | +0.0840 | 89% | 6210 |
| Time to max (s, median) | — | 138 | — | — |

### Sensitivity — (8, 3) (n=3316)

| Metric | Mean | Median | % positive | n |
|---|---:|---:|---:|---:|
| Recovery @ 1 min | +0.0152 | +0.0025 | 53% | 3236 |
| Recovery @ 2 min | +0.0165 | +0.0010 | 50% | 3149 |
| Recovery @ 3 min | +0.0173 | +0.0000 | 49% | 3079 |
| Recovery @ 5 min | +0.0187 | +0.0000 | 49% | 2939 |
| Max recovery | +0.1121 | +0.0750 | 88% | 3316 |
| Time to max (s, median) | — | 130 | — | — |

### Table 4 — Favorite trailing vs underdog trailing

| Group | n | Mean rec @ 3min | Median | % positive | Mean max rec |
|---|---:|---:|---:|---:|---:|
| Favorite trailing | 2947 | +0.0245 | +0.0080 | 54% | +0.1250 |
| Underdog trailing | 3263 | +0.0215 | +0.0010 | 50% | +0.1155 |
| All | 6210 | +0.0229 | +0.0040 | 52% | +0.1200 |

### Table 5 — Post-run recovery by period

| Group | n | Mean rec @ 3min | Median | % positive | Mean max rec |
|---|---:|---:|---:|---:|---:|
| Q1 | 1442 | +0.0262 | +0.0210 | 59% | +0.1217 |
| Q2 | 1540 | +0.0195 | +0.0060 | 54% | +0.1160 |
| Q3 | 1636 | +0.0169 | +0.0010 | 51% | +0.1221 |
| Q4 | 1561 | +0.0298 | +0.0000 | 44% | +0.1174 |
| OT | 31 | +0.1536 | +0.0410 | 56% | +0.2708 |

### Table 6 — Post-run recovery by run magnitude

| Group | n | Mean rec @ 3min | Median | % positive | Mean max rec |
|---|---:|---:|---:|---:|---:|
| 6-7 | 3509 | +0.0225 | +0.0050 | 53% | +0.1224 |
| 8-9 | 1613 | +0.0233 | +0.0040 | 52% | +0.1202 |
| 10-12 | 834 | +0.0234 | +0.0030 | 53% | +0.1151 |
| 13+ | 254 | +0.0250 | +0.0000 | 43% | +0.1027 |

### Table 7 — Post-run recovery: with vs without timeout

| Group | n | Mean rec @ 3min | Median | % positive | Mean max rec |
|---|---:|---:|---:|---:|---:|
| With timeout (≤ 90s) | 2208 | +0.0220 | +0.0010 | 51% | +0.1259 |
| No timeout | 4002 | +0.0234 | +0.0060 | 53% | +0.1168 |

## Section 4 — Prior degradation

### Table 8 — Underdog lead persistence

| Checkpoint | n games | n underdog leading | Mean UD WP (when leading) | Underdog wins (when leading) |
|---|---:|---:|---:|---:|
| End Q1 | 549 | 193 | 0.664 | 54% |
| Halftime | 549 | 234 | 0.742 | 63% |
| End Q3 | 549 | 230 | 0.815 | 73% |
| 6:00 Q4 | 549 | 232 | 0.862 | 79% |

## Section 5 — Favorite vs underdog dip recovery

### Table 9 — Favorite dip recovery

| Threshold | n games w/ crossing | % recover > 0.50 | Median time to recovery (min) | % favorite wins |
|---|---:|---:|---:|---:|
| < 0.45 | 451 | 91% | 1.9 | 50% |
| < 0.40 | 421 | 84% | 3.5 | 47% |
| < 0.35 | 383 | 76% | 6.0 | 41% |
| < 0.30 | 360 | 68% | 7.9 | 38% |
| < 0.25 | 340 | 60% | 9.0 | 34% |

### Table 10 — Underdog dip recovery

| Threshold | n games w/ crossing | % recover > 0.50 | Median time to recovery (min) | % underdog wins |
|---|---:|---:|---:|---:|
| < 0.45 | 535 | 84% | 4.7 | 39% |
| < 0.40 | 518 | 79% | 5.9 | 37% |
| < 0.35 | 495 | 73% | 7.6 | 35% |
| < 0.30 | 470 | 64% | 9.3 | 31% |
| < 0.25 | 442 | 54% | 11.2 | 27% |

## Section 6 — Synthesis

**1. Run frequency.** At the primary (margin ≥ 6, window ≤ 3 min) definition, 6,210 runs were detected across 549 competitive games (11.31 runs/game). See Table 1.

**2. Timeout association.** 36% of runs are followed by a timeout within 90 seconds of game time; of those, 66% are called by the trailing team. Timeouts are not a reliable marker of runs at ESPN scale. See Table 2.

**3. Trailing-team recovery.** At 3 min, the trailing team's WP recovers (goes positive) 52% of the time with a mean delta of +0.0229. Max recovery within 5 min is positive 89% of the time with mean magnitude +0.1200. Fixed 3-min checkpoint is not meaningfully above 50%. See Table 3.

**4. Favorite vs underdog recovery.** After being run on (primary params): favorite trailing recovers 54% vs underdog trailing 50% (% positive @ 3 min). After WP dips below 0.30: favorite recovers above 0.50 in 68% of games vs underdog 64%. See Tables 4, 9, 10.

**5. Strongest-recovery context.** Best-performing run magnitude bucket: **6-7** (53% positive @ 3 min). Best-performing period: **Q1** (59% positive). See Tables 5, 6.

**6. Timeouts and recovery.** Runs followed by a timeout recover at 51% vs 53% without (delta -3pp). Timeouts do not measurably improve recovery at this scale; runs reverse at similar rates regardless. See Table 7.

**7. Prior-acceptance inflection.** Underdog-leading-conversion rates: End Q1 54%, Halftime 63%, End Q3 73%, 6:00 Q4 79%. The inflection — where underdog-leads convert to wins at roughly the WP model's implied rate — is where the prior has fully dissolved. See Table 8.

**8. Strategy 3 implications.** The favorite/underdog recovery gap is thin at ESPN scale. Best absolute recovery context is **6-7-point runs ending in Q1** (53% positive @ 3 min). Combined with the Kalshi-level n=2 null at 3-min checkpoints, the entry rule should continue to use price-level triggers rather than run/timeout context, but prioritize games where the pre-game favorite falls behind — that's where the prior-anchoring mechanism has the largest WP-recovery signal on the ESPN side, and the same mechanism transfers to market prices with smaller magnitude. ESPN caveat: these magnitudes are upper bounds; Kalshi recovery will be 10-17pp smaller at the tails.

