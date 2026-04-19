# Game flow trajectory analysis — ESPN WP, 2025-26 season

Classifies 1,234 ESPN WP timeseries into five trajectory-shape buckets and characterizes swing + mid-range round-trip features per bucket. Answers: **which game shapes produce the mid-range oscillation that Strategy 3 needs?**

**ESPN caveat:** All magnitudes below are ESPN WP, which the Phase 3B sportsbook backfill established as +10-17pp more reactive than real-money markets at the tails. Absolute swing counts and round-trip rates are upper bounds on what Kalshi or FanDuel would show. The *relative ranking* across buckets should hold; the absolute yield will be smaller in production.

## Data

- Games processed: **1,234** / 1240 (skipped 0 games with <10 tradeable obs; 6 missing meta).
- Tradeable window: `sec_rem ≥ 60s`.
- Swing detection: `scipy.signal.find_peaks` with prominence = 0.02 on 3-point rolling-median-smoothed home_wp series.
- Mid-range round-trip grid: entry at side_wp ≤ 0.35, exit at side_wp ≥ 0.50. Summed across home + away perspectives.


## 1. Bucket distribution


### All games

| Bucket | N | % | Mean |spread| | Mean final margin |
|--------|---|---|----------------|-------------------|
| Blowout | 393 | 31.8% | 8.75 | 24.7 |
| Comeback | 324 | 26.3% | 6.15 | 6.0 |
| Late collapse | 0 | 0.0% | — | — |
| Back-and-forth | 228 | 18.5% | 5.19 | 8.4 |
| Wire-to-wire | 289 | 23.4% | 8.09 | 9.6 |
| **Total** | **1234** | — | — | — |

### |spread| ≤ 6

| Bucket | N | % | Mean |spread| | Mean final margin |
|--------|---|---|----------------|-------------------|
| Blowout | 144 | 26.2% | 3.52 | 24.3 |
| Comeback | 171 | 31.1% | 3.42 | 5.7 |
| Late collapse | 0 | 0.0% | — | — |
| Back-and-forth | 135 | 24.6% | 3.27 | 8.8 |
| Wire-to-wire | 99 | 18.0% | 3.50 | 9.5 |
| **Total** | **549** | — | — | — |

### Spread × bucket cross-tabulation

| Bucket | \|spread\|≤3 | \|spread\| 3-6 | \|spread\| 6-10 | \|spread\|>10 | No spread |
|--------|---------------|------------------|-------------------|------------------|-----------|
| Blowout | 67 | 77 | 79 | 143 | 27 |
| Comeback | 81 | 90 | 79 | 48 | 26 |
| Late collapse | 0 | 0 | 0 | 0 | 0 |
| Back-and-forth | 73 | 62 | 56 | 17 | 20 |
| Wire-to-wire | 42 | 57 | 82 | 82 | 26 |

## 2. Oscillation characteristics per bucket

| Bucket | N | Mean ≥0.10 | Mean ≥0.15 | Median max_swing | Mean total_swing | Mean lead_changes | Mean pct_competitive |
|--------|---|-----------|-----------|------------------|------------------|--------------------|----------------------|
| Blowout | 393 | 5.82 | 2.63 | 0.215 | 1.90 | 3.4 | 0.16 |
| Comeback | 324 | 19.93 | 10.76 | 0.403 | 5.70 | 16.2 | 0.48 |
| Late collapse | 0 | — | — | — | — | — | — |
| Back-and-forth | 228 | 18.82 | 9.57 | 0.326 | 5.34 | 20.4 | 0.60 |
| Wire-to-wire | 289 | 9.99 | 4.58 | 0.265 | 3.15 | 3.6 | 0.19 |

## 3. Mid-range swing analysis per bucket

Strategy 3 headline: these are the games where mid-range oscillation produces executable round-trips.


### All games

| Bucket | N | Mean midrange_swings | Mean midrange_roundtrips | % ≥1 roundtrip | % ≥2 roundtrips |
|--------|---|---------------------|------------------------|----------------|-----------------|
| Blowout | 393 | 2.07 | 0.42 | 28.0% | 10.9% |
| Comeback | 324 | 9.87 | 3.60 | 99.7% | 85.2% |
| Late collapse | 0 | — | — | — | — |
| Back-and-forth | 228 | 11.86 | 3.28 | 97.4% | 83.3% |
| Wire-to-wire | 289 | 2.69 | 0.66 | 43.9% | 16.3% |

### |spread| ≤ 6

| Bucket | N | Mean midrange_swings | Mean midrange_roundtrips | % ≥1 roundtrip | % ≥2 roundtrips |
|--------|---|---------------------|------------------------|----------------|-----------------|
| Blowout | 144 | 3.16 | 0.62 | 41.0% | 15.3% |
| Comeback | 171 | 10.17 | 3.57 | 99.4% | 86.5% |
| Late collapse | 0 | — | — | — | — |
| Back-and-forth | 135 | 11.75 | 3.05 | 96.3% | 79.3% |
| Wire-to-wire | 99 | 3.46 | 0.77 | 54.5% | 15.2% |

## 4. Pre-game spread as oscillation predictor

Spearman correlations between |pre-game spread| and oscillation features:

| Feature | Spearman ρ | p-value |
|---------|------------|---------|
| n_swings ≥ 0.10 | -0.341 | 0.0000 |
| total_swing_distance | -0.345 | 0.0000 |
| n_midrange_swings | -0.379 | 0.0000 |

### |spread| bucket breakdown

| Spread bucket | N | Mean swings ≥0.10 | Mean midrange_roundtrips | % with ≥1 midrange_roundtrip |
|---------------|---|-------------------|------------------------|-----------------------------|
| ≤3 | 263 | 14.98 | 2.17 | 76.0% |
| 3-6 | 286 | 14.75 | 2.16 | 74.5% |
| 6-10 | 296 | 13.53 | 1.98 | 64.2% |
| >10 | 290 | 8.25 | 1.01 | 37.6% |

## 5. OT games (reference)

N OT games: **55** (4.5% of processed).

| Feature | Mean | Median |
|---------|------|--------|
| n_swings ≥ 0.10 | 23.36 | 23.0 |
| n_midrange_swings | 11.67 | 10.0 |
| midrange_roundtrips | 5.33 | 5.0 |
| n_lead_changes | 20.6 | 17.0 |
| total_swing_distance | 6.85 | 6.86 |

% OT games with ≥1 midrange round-trip: **100.0%** (vs 63.4% across all games). Playoff series produce proportionally more OT games than regular season, so Strategy 3's playoff yield should run above baseline.


## 6. Strategy 3 target universe sizing

**All games, ≥1 midrange round-trip:** 782 / 1234 (63.4%)

**|spread| ≤ 6, ≥1 midrange round-trip:** 413 / 549 (75.2%)

**|spread| ≤ 3, ≥1 midrange round-trip:** 200 / 263 (76.0%)


### Round-trip contribution by bucket

| Bucket | N | Total round-trips | % of all round-trips | Mean per game |
|--------|---|-------------------|----------------------|---------------|
| Blowout | 393 | 166 | 7.3% | 0.42 |
| Comeback | 324 | 1165 | 51.3% | 3.60 |
| Back-and-forth | 228 | 748 | 33.0% | 3.28 |
| Wire-to-wire | 289 | 190 | 8.4% | 0.66 |

Most productive bucket: **Comeback** (1165 round-trips, 51.3% of total).

### Hypothetical: perfect pre-tip shape prediction

If we could predict pre-tip which games would fall into a **≥50% round-trip rate bucket**, we'd target 552 / 1234 games (44.7%) and capture 1913 / 2269 round-trips (84.3% of total, if total_rts>0). Buckets meeting the bar: Comeback, Back-and-forth.

Note: we cannot predict bucket pre-tip reliably. This is an upper-bound scenario. Pre-game spread alone is a weak predictor (see Section 4 Spearman correlations).

### Caveat — ESPN WP vs market prices

All round-trip counts above use ESPN WP as the signal. The Phase 3B sportsbook backfill established that real-money markets compress +10-17pp relative to ESPN at the tails: a $0.10 ESPN swing is typically a $0.05-$0.07 Kalshi swing. The round-trip threshold grid in this analysis (entry ≤ 0.35, exit ≥ 0.50) therefore implies a Kalshi-equivalent swing of maybe $0.10 gross minus spread rather than the full $0.15. The bucket-relative ranking should transfer (games where ESPN shows lots of swings will show more Kalshi swings than games where ESPN shows few), but the absolute yield will be smaller in production. Tier 3 Odds API sportsbook-timeseries backfill is the next validation step.

