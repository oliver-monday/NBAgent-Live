# Strategy 3 Odds API timeseries — 2026-04-19

Full-game FanDuel moneyline timeseries at 5-min intervals via the Odds API historical endpoint. 15 games stratified across trajectory buckets. Answers: **what fraction of ESPN-visible mid-range round-trips survive at real-money sportsbook prices?**

## 1. Selected games

| # | gameId | date | away | home | spread | bucket | ESPN rts | tip wallclock |
|---|--------|------|------|------|--------|--------|----------|----------------|
| 1 | 401809968 | 2025-10-26 | LAL | SAC | -3.5 | Back-and-forth | 7 | 2025-10-27T01:10Z |
| 2 | 401809975 | 2025-10-27 | PHX | UTA | -1.0 | Wire-to-wire | 5 | 2025-10-28T01:11Z |
| 3 | 401809998 | 2025-11-01 | MIN | CHA | +4.5 | Blowout | 4 | 2025-11-01T22:10Z |
| 4 | 401810095 | 2025-11-16 | CHI | UTA | +4.5 | Comeback | 8 | 2025-11-17T01:11Z |
| 5 | 401810159 | 2025-11-30 | ATL | PHI | -2.0 | Comeback | 9 | 2025-11-30T23:11Z |
| 6 | 401810202 | 2025-12-05 | LAC | MEM | +2.0 | Back-and-forth | 7 | 2025-12-06T01:12Z |
| 7 | 401836806 | 2025-12-15 | HOU | DEN | +1.0 | Back-and-forth | 8 | 2025-12-16T02:42Z |
| 8 | 401810226 | 2025-12-18 | ATL | CHA | +4.5 | Wire-to-wire | 2 | 2025-12-19T00:11Z |
| 9 | 401810386 | 2026-01-08 | DAL | UTA | +5.0 | Comeback | 9 | 2026-01-09T02:11Z |
| 10 | 401810383 | 2026-01-08 | IND | CHA | -4.5 | Comeback | 8 | 2026-01-09T00:10Z |
| 11 | 401810581 | 2026-02-04 | DEN | NYK | -5.0 | Back-and-forth | 13 | 2026-02-05T00:13Z |
| 12 | 401810666 | 2026-02-21 | ORL | PHX | -3.5 | Comeback | 7 | 2026-02-21T22:10Z |
| 13 | 401810789 | 2026-03-09 | GSW | UTA | +5.5 | Back-and-forth | 9 | 2026-03-10T01:11Z |
| 14 | 401810906 | 2026-03-25 | ATL | DET | -2.5 | Back-and-forth | 9 | 2026-03-25T23:13Z |
| 15 | 401810998 | 2026-04-06 | NYK | ATL | -1.5 | Comeback | 7 | 2026-04-06T23:13Z |

API calls: 555. Credits remaining (per headers): None.


## 2. FanDuel timeseries quality

| game | n timestamps | n with FD data | n with consensus | max gap (min) |
|------|--------------|----------------|------------------|---------------|
| 401809968 | 37 | 1 | 8 | 40.0 |
| 401809975 | 37 | 31 | 32 | 5.0 |
| 401809998 | 37 | 23 | 26 | 5.0 |
| 401810095 | 37 | 37 | 37 | 5.0 |
| 401810159 | 37 | 37 | 37 | 5.0 |
| 401810202 | 37 | 25 | 25 | 5.0 |
| 401836806 | 37 | 33 | 37 | 5.0 |
| 401810226 | 37 | 27 | 30 | 5.0 |
| 401810386 | 37 | 25 | 26 | 5.0 |
| 401810383 | 37 | 4 | 13 | 10.0 |
| 401810581 | 37 | 33 | 37 | 5.0 |
| 401810666 | 37 | 18 | 35 | 5.0 |
| 401810789 | 37 | 30 | 30 | 5.0 |
| 401810906 | 37 | 33 | 34 | 5.0 |
| 401810998 | 37 | 28 | 30 | 5.0 |

## 3. Per-game comparison (ESPN vs FanDuel)

| Game | Bucket | |Spread| | ESPN ≥0.10 swings | FD ≥0.10 swings | ESPN RTs (0.35→0.50) | FD RTs (0.35→0.50) | FD RTs (0.40→0.50) |
|------|--------|---------|-------------------|-----------------|----------------------|---------------------|---------------------|
| 401809968 | Back-and-forth | 3.5 | 29 | 1 | 7 | 1 | 2 |
| 401809975 | Wire-to-wire | 1.0 | 19 | 5 | 5 | 2 | 2 |
| 401809998 | Blowout | 4.5 | 9 | 3 | 4 | 1 | 1 |
| 401810095 | Comeback | 4.5 | 29 | 2 | 8 | 2 | 2 |
| 401810159 | Comeback | 2.0 | 30 | 4 | 9 | 4 | 4 |
| 401810202 | Back-and-forth | 2.0 | 24 | 3 | 7 | 1 | 2 |
| 401836806 | Back-and-forth | 1.0 | 30 | 6 | 8 | 4 | 5 |
| 401810226 | Wire-to-wire | 4.5 | 17 | 6 | 2 | 1 | 2 |
| 401810386 | Comeback | 5.0 | 21 | 3 | 9 | 2 | 3 |
| 401810383 | Comeback | 4.5 | 30 | 3 | 8 | 1 | 3 |
| 401810581 | Back-and-forth | 5.0 | 32 | 6 | 13 | 4 | 4 |
| 401810666 | Comeback | 3.5 | 35 | 7 | 7 | 4 | 7 |
| 401810789 | Back-and-forth | 5.5 | 32 | 3 | 9 | 2 | 2 |
| 401810906 | Back-and-forth | 2.5 | 30 | 6 | 9 | 3 | 4 |
| 401810998 | Comeback | 1.5 | 22 | 3 | 7 | 2 | 3 |

## 4. Survival rate — headline

**ESPN-to-FanDuel round-trip survival rate**

- Pooled round-trips: ESPN = 112, FanDuel = 34
- **Survival rate = 30.4%**
- Swing survival (≥0.10): ESPN = 389, FD = 61, rate = 15.7%

Per-bucket survival:

| Bucket | N | ESPN RTs | FD RTs | Survival rate |
|--------|---|----------|--------|---------------|
| Comeback | 6 | 48 | 15 | 31.2% |
| Back-and-forth | 6 | 53 | 15 | 28.3% |
| Wire-to-wire | 2 | 7 | 3 | 42.9% |
| Blowout | 1 | 4 | 1 | 25.0% |

## 5. FanDuel-native thresholds

| Entry | Exit | Total FD round-trips | Mean per game | Gross $ per trip (100 ct) |
|-------|------|----------------------|---------------|---------------------------|
| 0.35 | 0.50 | 34 | 2.27 | $15.00 |
| 0.40 | 0.50 | 46 | 3.07 | $10.00 |
| 0.40 | 0.55 | 35 | 2.33 | $15.00 |
| 0.45 | 0.55 | 47 | 3.13 | $10.00 |

## 6. Favorite-side on FanDuel

| Bucket | N | Total completed | Total res_win | Total res_loss | Mean blended net (maker) |
|--------|---|-----------------|---------------|----------------|--------------------------|
| Comeback | 6 | 8 | 1 | 5 | $-5.11 |
| Back-and-forth | 6 | 4 | 0 | 5 | $-39.93 |
| Wire-to-wire | 2 | 3 | 1 | 1 | $-10.73 |
| Blowout | 1 | 1 | 0 | 0 | $15.78 |

Pooled mean favorite-side blended net (maker, across games with ≥1 entry): **$-18.40**.


## 7. Strategy 3 revised universe estimate

- ESPN round-trips per season (|spread|≤6, from game-flow trajectory analysis): **~2272**
- Survival rate: **30.4%**
- Estimated market-price round-trips per season: **~689**
- Estimated gross EV at $14.55/trade (HOU-LAL reference): **$10,025/season**

This extrapolation assumes the 15-game survival rate is representative of the full season. Wider sampling is the next-level confidence gate.


## 8. Resolution granularity caveat

Mean ESPN round-trip duration (across the 15 selected games): **12.7 min**. Our FanDuel timeseries samples every 5 min. 
Mean duration > 10 min — the 5-min FanDuel grid should capture most round-trips. Survival rate above is a reasonable estimate of the real rate.

