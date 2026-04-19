# Phase 3B smoke test — 2026-04-18

First paired Kalshi–ESPN analysis on n=2 games (CHA-ORL and GSW-PHX Play-In, 2026-04-17). **Not formal Phase 3B.** Joins Kalshi orderbook snapshots with ESPN WP at matched wallclock timestamps via as-of merge (300s backward tolerance).

## Data

- Kalshi: 33,476 snapshots across 20 tickers.
- ESPN games analyzed: 6.
- As-of merge tolerance: 300s backward.

## Per-game analysis


### 401866758 — CHA 90 @ ORL 121

- Market complement check (home mid + away mid vs 1.00): n=312, mean |dev|=0.0020, max |dev|=0.0200

**Screenshot cross-check — end of Q1:**

- Score: CHA 16 – ORL 38 (wallclock 2026-04-18 00:11:06+00:00)
- Kalshi ORL mid: `0.825`; Kalshi CHA mid: `0.175`
- ESPN ORL WP: `0.919`; ESPN CHA WP: `0.081`
- User-reported screenshots at Q1 end: Kalshi CHA ~17%, ESPN CHA ~8.6%.

**Per-game residual timeline (quarter boundaries):**

| moment | wallclock | ESPN home_wp | Kalshi home mid | Kalshi away mid |
|--------|-----------|--------------|-----------------|-----------------|
| start Q1 | 23:40:55 | 0.410 | 0.425 | 0.585 |
| end Q1 | 00:11:06 | 0.919 | 0.825 | 0.175 |
| start Q2 | 00:12:37 | 0.919 | 0.825 | 0.175 |
| end Q2 | 00:56:27 | 0.995 | 0.985 | 0.025 |
| start Q3 | 01:08:29 | 0.995 | 0.975 | 0.025 |
| end Q3 | 01:51:42 | 0.999 | 0.995 | 0.005 |
| start Q4 | 01:53:25 | 0.999 | 0.995 | 0.005 |
| end Q4 | 02:22:08 | 1.000 | 0.995 | 0.005 |

**Liquidity at extreme-low prices (kalshi_mid ≤ 0.20):** n=253, mean yes_bid_size_fp=105,589, median yes_bid_size_fp=53,888


### 401866759 — GSW 96 @ PHX 111

- Market complement check (home mid + away mid vs 1.00): n=285, mean |dev|=0.0027, max |dev|=0.0400

**Per-game residual timeline (quarter boundaries):**

| moment | wallclock | ESPN home_wp | Kalshi home mid | Kalshi away mid |
|--------|-----------|--------------|-----------------|-----------------|
| start Q1 | 02:18:05 | 0.629 | 0.575 | 0.435 |
| end Q1 | 02:45:09 | 0.937 | 0.815 | 0.195 |
| start Q2 | 02:48:02 | 0.937 | 0.815 | 0.185 |
| end Q2 | 03:21:33 | 0.749 | 0.635 | 0.375 |
| start Q3 | 03:34:52 | 0.749 | 0.625 | 0.375 |
| end Q3 | 04:08:23 | 0.898 | 0.785 | 0.210 |
| start Q4 | 04:11:28 | 0.898 | 0.765 | 0.235 |
| end Q4 | 04:47:52 | 1.000 | 0.995 | 0.005 |

**Liquidity at extreme-low prices (kalshi_mid ≤ 0.20):** n=89, mean yes_bid_size_fp=157,243, median yes_bid_size_fp=12,547


### 401869187 — TOR 113 @ CLE 126

- Market complement check (home mid + away mid vs 1.00): n=247, mean |dev|=0.0021, max |dev|=0.0300

**Per-game residual timeline (quarter boundaries):**

| moment | wallclock | ESPN home_wp | Kalshi home mid | Kalshi away mid |
|--------|-----------|--------------|-----------------|-----------------|
| start Q1 | 17:09:22 | 0.630 | 0.765 | 0.235 |
| end Q1 | 17:41:52 | 0.708 | 0.795 | 0.205 |
| start Q2 | 17:41:54 | 0.708 | 0.795 | 0.205 |
| end Q2 | 18:14:39 | 0.792 | 0.845 | 0.155 |
| start Q3 | 18:14:51 | 0.792 | 0.845 | 0.155 |
| end Q3 | 19:05:17 | 0.996 | 0.995 | 0.005 |
| start Q4 | 19:05:29 | 0.996 | 0.995 | 0.005 |
| end Q4 | 19:46:15 | 1.000 | 0.995 | 0.005 |

**Liquidity at extreme-low prices (kalshi_mid ≤ 0.20):** n=126, mean yes_bid_size_fp=85,707, median yes_bid_size_fp=45,309


### 401869188 — MIN 105 @ DEN 116


**Per-game residual timeline (quarter boundaries):**

| moment | wallclock | ESPN home_wp | Kalshi home mid | Kalshi away mid |
|--------|-----------|--------------|-----------------|-----------------|
| start Q1 | 19:41:36 | 0.708 | nan | nan |
| end Q1 | 20:15:08 | 0.408 | nan | nan |
| start Q2 | 20:18:17 | 0.408 | nan | nan |
| end Q2 | 20:48:34 | 0.658 | nan | nan |
| start Q3 | 21:03:57 | 0.658 | nan | nan |
| end Q3 | 21:35:15 | 0.958 | nan | nan |
| start Q4 | 21:38:34 | 0.958 | nan | nan |
| end Q4 | 22:15:01 | 1.000 | nan | nan |

### 401869189 — ATL 102 @ NYK 113

- Market complement check (home mid + away mid vs 1.00): n=23, mean |dev|=0.0000, max |dev|=0.0000

**Per-game residual timeline (quarter boundaries):**

| moment | wallclock | ESPN home_wp | Kalshi home mid | Kalshi away mid |
|--------|-----------|--------------|-----------------|-----------------|
| start Q1 | 22:18:41 | 0.728 | 0.995 | 0.005 |
| end Q1 | 22:44:08 | 0.820 | 0.995 | 0.005 |
| start Q2 | 22:47:07 | 0.820 | 0.995 | 0.005 |
| end Q2 | 23:18:38 | 0.723 | 0.995 | 0.005 |
| start Q3 | 23:33:53 | 0.723 | 0.995 | 0.005 |
| end Q3 | 00:11:37 | 0.914 | 0.995 | 0.005 |
| start Q4 | 00:14:27 | 0.914 | 0.995 | 0.005 |
| end Q4 | 00:50:41 | 1.000 | 0.995 | 0.005 |

**Liquidity at extreme-low prices (kalshi_mid ≤ 0.20):** n=23, mean yes_bid_size_fp=10,982, median yes_bid_size_fp=0


### 401869190 — HOU 98 @ LAL 107

- Market complement check (home mid + away mid vs 1.00): n=285, mean |dev|=0.0036, max |dev|=0.0300

**Per-game residual timeline (quarter boundaries):**

| moment | wallclock | ESPN home_wp | Kalshi home mid | Kalshi away mid |
|--------|-----------|--------------|-----------------|-----------------|
| start Q1 | 00:48:15 | 0.503 | 0.425 | 0.565 |
| end Q1 | 01:16:00 | 0.608 | 0.545 | 0.455 |
| start Q2 | 01:19:21 | 0.608 | 0.535 | 0.465 |
| end Q2 | 01:49:32 | 0.568 | 0.520 | 0.485 |
| start Q3 | 02:05:54 | 0.568 | 0.515 | 0.485 |
| end Q3 | 02:41:55 | 0.867 | 0.805 | 0.195 |
| start Q4 | 02:45:43 | 0.867 | 0.795 | 0.205 |
| end Q4 | 03:21:43 | 1.000 | 0.995 | 0.005 |

**Liquidity at extreme-low prices (kalshi_mid ≤ 0.20):** n=82, mean yes_bid_size_fp=237,581, median yes_bid_size_fp=20,952


======================================================================
A. Per-game summary

## A. Per-game summary

| Game | gameId | Home | Away | Final | Paired obs | Kalshi home range |
|------|--------|------|------|-------|-----------|-------------------|
| CHA@ORL | 401866758 | ORL | CHA | 90-121 | 624 | [0.415, 0.995] |
| GSW@PHX | 401866759 | PHX | GSW | 96-111 | 570 | [0.555, 0.995] |
| TOR@CLE | 401869187 | CLE | TOR | 113-126 | 494 | [0.665, 0.995] |
| MIN@DEN | 401869188 | DEN | MIN | 105-116 | 0 | — |
| ATL@NYK | 401869189 | NYK | ATL | 102-113 | 46 | [0.985, 0.995] |
| HOU@LAL | 401869190 | LAL | HOU | 98-107 | 570 | [0.405, 0.995] |

======================================================================
B. Pooled residual distribution

## B. Pooled residual distribution

  n (paired obs)       2,304
  mean residual        +0.0006 (+0.06pp)
  median residual      +0.0000 (+0.00pp)
  std                  0.0848
  p5                   -0.1390 (-13.90pp)
  p25                  -0.0590 (-5.90pp)
  p75                  +0.0600 (+6.00pp)
  p95                  +0.1390 (+13.90pp)
  mean |residual|      0.0655 (6.55pp)
| Statistic | Value |
|-----------|-------|
| n (paired obs) | 2,304 |
| mean residual | +0.0006 (+0.06pp) |
| median residual | +0.0000 (+0.00pp) |
| std | 0.0848 |
| p5 | -0.1390 (-13.90pp) |
| p25 | -0.0590 (-5.90pp) |
| p75 | +0.0600 (+6.00pp) |
| p95 | +0.1390 (+13.90pp) |
| mean |residual| | 0.0655 (6.55pp) |

======================================================================
C. Residual stratified by ESPN WP bucket

## C. Residual stratified by ESPN WP bucket

Pooled home + away observations; each snapshot contributes one row per side. Bucket on the side's own ESPN WP; residual = `kalshi_mid_that_side - espn_wp_that_side`.


--- All pooled (both games, both sides) ---

#### All pooled (both games, both sides)

| bucket | n | mean ESPN | mean Kalshi | residual (pp) |
|--------|---|-----------|-------------|---------------|
| (-0.001, 0.025] | 374 | 0.006 | 0.016 | +1.10 |
| (0.025, 0.05] | 82 | 0.036 | 0.069 | +3.26 |
| (0.05, 0.075] | 55 | 0.062 | 0.146 | +8.39 |
| (0.075, 0.1] | 48 | 0.087 | 0.186 | +9.95 |
| (0.1, 0.125] | 68 | 0.114 | 0.246 | +13.28 |
| (0.125, 0.15] | 47 | 0.133 | 0.242 | +10.85 |
| (0.15, 0.2] | 83 | 0.172 | 0.272 | +9.99 |
| (0.2, 0.25] | 59 | 0.224 | 0.298 | +7.36 |
| (0.25, 0.35] | 155 | 0.303 | 0.318 | +1.52 |
| (0.35, 0.5] | 181 | 0.416 | 0.406 | -0.96 |
| (0.5, 0.65] | 193 | 0.588 | 0.607 | +1.89 |
| (0.65, 0.75] | 144 | 0.702 | 0.678 | -2.38 |
| (0.75, 0.85] | 141 | 0.807 | 0.718 | -8.86 |
| (0.85, 0.9] | 117 | 0.879 | 0.757 | -12.19 |
| (0.9, 0.925] | 48 | 0.914 | 0.817 | -9.78 |
| (0.925, 0.95] | 53 | 0.938 | 0.857 | -8.07 |
| (0.95, 0.975] | 82 | 0.964 | 0.931 | -3.29 |
| (0.975, 1.0] | 374 | 0.994 | 0.984 | -1.08 |

======================================================================
F. Preliminary §1.1 assessment

## F. Preliminary §1.1 assessment

Kalshi and ESPN diverge (mean |residual| 6.55pp, median +0.00pp, residual-vs-(ESPN−0.5) correlation -0.463) without a pattern the current template recognizes. Inspect the bucket table in Section C for structure before interpreting.

**n=2 games is far below any threshold for definitive conclusions.** This smoke test validates the pipeline; formal §1.1 analysis requires ≥5-10 games per the Phase 3B scoping.

