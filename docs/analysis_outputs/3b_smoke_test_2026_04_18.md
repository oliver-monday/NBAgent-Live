# Phase 3B smoke test — 2026-04-18

First paired Kalshi–ESPN analysis on n=2 games (CHA-ORL and GSW-PHX Play-In, 2026-04-17). **Not formal Phase 3B.** Joins Kalshi orderbook snapshots with ESPN WP at matched wallclock timestamps via as-of merge (300s backward tolerance).

## Data

- Kalshi: 26,190 snapshots across 16 tickers.
- ESPN games analyzed: 2.
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


======================================================================
A. Per-game summary

## A. Per-game summary

| Game | gameId | Home | Away | Final | Paired obs | Kalshi home range |
|------|--------|------|------|-------|-----------|-------------------|
| CHA@ORL | 401866758 | ORL | CHA | 90-121 | 624 | [0.415, 0.995] |
| GSW@PHX | 401866759 | PHX | GSW | 96-111 | 570 | [0.555, 0.995] |

======================================================================
B. Pooled residual distribution

## B. Pooled residual distribution

  n (paired obs)       1,194
  mean residual        +0.0004 (+0.04pp)
  median residual      +0.0005 (+0.05pp)
  std                  0.0908
  p5                   -0.1430 (-14.30pp)
  p25                  -0.0667 (-6.67pp)
  p75                  +0.0640 (+6.40pp)
  p95                  +0.1460 (+14.60pp)
  mean |residual|      0.0712 (7.12pp)
| Statistic | Value |
|-----------|-------|
| n (paired obs) | 1,194 |
| mean residual | +0.0004 (+0.04pp) |
| median residual | +0.0005 (+0.05pp) |
| std | 0.0908 |
| p5 | -0.1430 (-14.30pp) |
| p25 | -0.0667 (-6.67pp) |
| p75 | +0.0640 (+6.40pp) |
| p95 | +0.1460 (+14.60pp) |
| mean |residual| | 0.0712 (7.12pp) |

======================================================================
C. Residual stratified by ESPN WP bucket

## C. Residual stratified by ESPN WP bucket

Pooled home + away observations; each snapshot contributes one row per side. Bucket on the side's own ESPN WP; residual = `kalshi_mid_that_side - espn_wp_that_side`.


--- All pooled (both games, both sides) ---

#### All pooled (both games, both sides)

| bucket | n | mean ESPN | mean Kalshi | residual (pp) |
|--------|---|-----------|-------------|---------------|
| (-0.001, 0.025] | 247 | 0.005 | 0.020 | +1.52 |
| (0.025, 0.05] | 37 | 0.038 | 0.104 | +6.59 |
| (0.05, 0.075] | 45 | 0.063 | 0.163 | +10.01 |
| (0.075, 0.1] | 39 | 0.086 | 0.209 | +12.24 |
| (0.1, 0.125] | 60 | 0.113 | 0.254 | +14.02 |
| (0.125, 0.15] | 27 | 0.133 | 0.273 | +13.97 |
| (0.15, 0.2] | 53 | 0.169 | 0.296 | +12.77 |
| (0.2, 0.25] | 25 | 0.220 | 0.356 | +13.56 |
| (0.25, 0.35] | 36 | 0.269 | 0.380 | +11.10 |
| (0.35, 0.5] | 28 | 0.429 | 0.455 | +2.65 |
| (0.5, 0.65] | 28 | 0.571 | 0.551 | -2.01 |
| (0.65, 0.75] | 36 | 0.731 | 0.621 | -10.94 |
| (0.75, 0.85] | 78 | 0.815 | 0.685 | -12.97 |
| (0.85, 0.9] | 89 | 0.881 | 0.742 | -13.88 |
| (0.9, 0.925] | 39 | 0.915 | 0.795 | -12.03 |
| (0.925, 0.95] | 43 | 0.938 | 0.841 | -9.69 |
| (0.95, 0.975] | 37 | 0.962 | 0.895 | -6.70 |
| (0.975, 1.0] | 247 | 0.995 | 0.980 | -1.50 |

======================================================================
F. Preliminary §1.1 assessment

## F. Preliminary §1.1 assessment

**Kalshi is systematically less extreme than ESPN** (compression pattern — residual vs (ESPN WP − 0.5) correlation = -0.685; mean |residual| 7.12pp; median +0.05pp). At low ESPN WP (favorites' comeback moments), Kalshi prices the underdog *higher* than ESPN; at high ESPN WP, Kalshi prices the favorite *lower*. Equivalent statement: ESPN's WP swings harder with game state than Kalshi's. Directly consistent with §1.4-style priors mattering, but the direction is the opposite of what §1.4 predicts about ESPN — here it's ESPN that looks *more* game-state-reactive, not less. Material implication for Strategy 2: the +3pp ESPN-vs-actual residual at low WP does not transfer directly to Kalshi, because Kalshi's prices are already +10pp above ESPN in that zone. The relevant residual for Strategy 2 is (actual_win_rate − Kalshi_mid), which the current dataset can't estimate without more games that resolve at the tails.

**n=2 games is far below any threshold for definitive conclusions.** This smoke test validates the pipeline; formal §1.1 analysis requires ≥5-10 games per the Phase 3B scoping.

