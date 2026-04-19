# Strategy 1 recalibrated bilateral — 2026-04-19

Applies the 57-point ESPN→sportsbook calibration (from `docs/analysis_outputs/strategy1_sportsbook_backfill.md`) to the full 2025-26 ESPN dataset, then re-runs Phase 3A / §6.7 analyses at sportsbook-denominated thresholds to estimate Strategy 1's opportunity rate and EV on real-money markets. Question answered: **does Strategy 1 survive at sportsbook-realistic entry prices, and where is the optimal operating point?**

## A. Calibration mapping

Calibration built from 57 dip observations (32 unique ESPN WP values after aggregation to median SB consensus per value). Fitted with PchipInterpolator on [0, 0.5]; symmetry f(x) = 1 − f(1 − x) extends to [0.5, 1]. Running-max applied to anchor y-values to enforce strict monotonicity in the face of noisy backfill data.


--- Reference-point mapping ---

### Reference-point mapping

| ESPN WP | Mapped SB WP |
|---------|-------------|
| 0.00 | 0.0000 |
| 0.05 | 0.1947 |
| 0.10 | 0.3245 |
| 0.15 | 0.3421 |
| 0.20 | 0.4672 |
| 0.25 | 0.4683 |
| 0.30 | 0.4711 |
| 0.35 | 0.4757 |
| 0.40 | 0.4821 |
| 0.45 | 0.4902 |
| 0.50 | 0.5000 |

**Full ESPN dataset**: 602,167 observations across 1,234 games. Mapping applied independently to home and away sides; complement check on mapped values below.


======================================================================
B. Bilateral dip rates at sportsbook thresholds (sec_rem>=60)

## B. Bilateral dip rates at sportsbook thresholds (sec_rem >= 60)

SB threshold → ESPN-equivalent threshold (via inverse of calibration):

| SB threshold | ESPN-equiv |
|---|---|
| 0.45 | 0.162 |
| 0.40 | 0.159 |
| 0.35 | 0.158 |
| 0.30 | 0.099 |
| 0.25 | 0.099 |
| 0.20 | 0.055 |
| 0.15 | 0.002 |


| Threshold | All | |spread|<=6 | |spread|<=3 | margin<=10 | margin<=5 | OT |
|---|---|---|---|---|---|---|
| <0.45 |  17.7% (1240) |  19.7% (549) |  19.4% (263) |  29.2% (592) |  33.2% (304) |  58.2% (55) |
| <0.40 |  17.4% (1240) |  19.1% (549) |  19.0% (263) |  28.7% (592) |  32.9% (304) |  58.2% (55) |
| <0.35 |  17.2% (1240) |  18.9% (549) |  19.0% (263) |  28.4% (592) |  32.6% (304) |  58.2% (55) |
| <0.30 |   6.4% (1240) |   7.1% (549) |   7.2% (263) |  10.5% (592) |  12.8% (304) |  20.0% (55) |
| <0.25 |   6.4% (1240) |   7.1% (549) |   7.2% (263) |  10.5% (592) |  12.8% (304) |  20.0% (55) |
| <0.20 |   2.1% (1240) |   2.2% (549) |   1.5% (263) |   3.7% (592) |   4.6% (304) |   9.1% (55) |
| <0.15 |   0.0% (1240) |   0.0% (549) |   0.0% (263) |   0.0% (592) |   0.0% (304) |   0.0% (55) |

======================================================================
C. §6.7 asymmetric rates at sportsbook thresholds (|spread|<=6, N=549)

## C. §6.7 asymmetric rates at sportsbook thresholds (|spread| ≤ 6, N = 549)

| X | Y | Strict | Asymmetric | Sequential |
|---|---|--------|------------|------------|
| 0.35 | 0.35 | 18.9% (104/549) | 18.9% (104/549) | 18.9% (104/549) |
| 0.30 | 0.30 | 7.1% (39/549) | 7.1% (39/549) | 7.1% (39/549) |
| 0.25 | 0.25 | 7.1% (39/549) | 7.1% (39/549) | 7.1% (39/549) |
| 0.25 | 0.35 | 7.1% (39/549) | 17.7% (97/549) | 9.3% (51/549) |
| 0.25 | 0.40 | 7.1% (39/549) | 17.7% (97/549) | 9.3% (51/549) |
| 0.25 | 0.45 | 7.1% (39/549) | 18.2% (100/549) | 9.3% (51/549) |
| 0.30 | 0.35 | 7.1% (39/549) | 17.7% (97/549) | 9.3% (51/549) |
| 0.30 | 0.40 | 7.1% (39/549) | 17.7% (97/549) | 9.3% (51/549) |
| 0.30 | 0.45 | 7.1% (39/549) | 18.2% (100/549) | 9.3% (51/549) |
| 0.35 | 0.40 | 18.9% (104/549) | 19.1% (105/549) | 19.1% (105/549) |
| 0.35 | 0.45 | 18.9% (104/549) | 19.7% (108/549) | 19.1% (105/549) |

======================================================================
D. EV-after-fees at sportsbook entry prices (100 contracts/leg, taker-taker)

## D. EV-after-fees at sportsbook entry prices

100 contracts per leg, taker-taker fees (Kalshi formula from `docs/FEES.md`). `Net (no sprd)` uses fees only; `Net (−1¢ sprd)` adds one tick of spread per leg ($1/leg = $2/round-trip) as a sensitivity on §2.5. Opportunity rate is the asymmetric-any-order rate on |spread| ≤ 6 games.

| X | Y | Gross | Fees | Net (no sprd) | Net (−1¢ sprd) | Opp rate | EV/game | EV/game (−sprd) |
|---|---|-------|------|---------------|----------------|----------|---------|-----------------|
| 0.35 | 0.35 | $30.00 | $3.20 | $26.80 | $24.80 | 18.9% | $5.08 | $4.70 |
| 0.30 | 0.30 | $40.00 | $2.94 | $37.06 | $35.06 | 7.1% | $2.63 | $2.49 |
| 0.25 | 0.25 | $50.00 | $2.64 | $47.36 | $45.36 | 7.1% | $3.36 | $3.22 |
| 0.25 | 0.35 | $40.00 | $2.92 | $37.08 | $35.08 | 17.7% | $6.55 | $6.20 |
| 0.25 | 0.40 | $35.00 | $3.01 | $31.99 | $29.99 | 17.7% | $5.65 | $5.30 |
| 0.25 | 0.45 | $30.00 | $3.06 | $26.94 | $24.94 | 18.2% | $4.91 | $4.54 |
| 0.30 | 0.35 | $35.00 | $3.07 | $31.93 | $29.93 | 17.7% | $5.64 | $5.29 |
| 0.30 | 0.40 | $30.00 | $3.16 | $26.84 | $24.84 | 17.7% | $4.74 | $4.39 |
| 0.30 | 0.45 | $25.00 | $3.21 | $21.79 | $19.79 | 18.2% | $3.97 | $3.60 |
| 0.35 | 0.40 | $25.00 | $3.29 | $21.71 | $19.71 | 19.1% | $4.15 | $3.77 |
| 0.35 | 0.45 | $20.00 | $3.34 | $16.66 | $14.66 | 19.7% | $3.28 | $2.88 |

======================================================================
E. Optimal threshold identification (top 3 by EV/game)

## E. Optimal threshold identification

| Rank | X | Y | Opp rate | Net/trade | EV/game | EV/game (−sprd) |
|------|---|---|----------|-----------|---------|-----------------|
| 1 | 0.25 | 0.35 | 17.7% | $37.08 | $6.55 | $6.20 |
| 2 | 0.25 | 0.40 | 17.7% | $31.99 | $5.65 | $5.30 |
| 3 | 0.30 | 0.35 | 17.7% | $31.93 | $5.64 | $5.29 |

**Recommended operating point: (0.25, 0.35)** — balances opportunity rate (17.7%) against per-trade net ($37.08). Higher frequency pairs (wider Y) produce more EV/game but shrink per-trade margin; tighter pairs are more fee-efficient but hit less often. The ranking above is on EV/game (pre-spread); adding one tick of spread per leg (§2.5 sensitivity) reduces EV uniformly but doesn't change the ordering meaningfully.

======================================================================
F. Side-by-side with Phase 3A (ESPN-denominated)

## F. Side-by-side with Phase 3A

| Metric | ESPN-denominated (0.20, 0.30) | SB-calibrated (best pair) |
|---|---|---|
| Threshold pair | (0.20, 0.30) | (0.25, 0.35) |
| Opportunity rate (|spread|≤6) | 49.0% | 17.7% |
| Gross per trade | $50.00 | $40.00 |
| Net per trade (after fees) | $47.40 | $37.08 |
| EV per competitive game | $23.23 | $6.55 |
| EV per game (−1¢ spread) | $22.25 | $6.20 |

======================================================================
G. Preliminary verdict

## G. Preliminary verdict

**Strategy 1 survives recalibration but is marginal.** Best operating point (0.25, 0.35) produces $6.55/game pre-spread ($6.20/game after §2.5 one-tick spread). Proceed cautiously — liquidity haircuts from Phase 3B could push this below viability. Consider the spread sensitivity the more important of the two numbers: if realized spreads are wider than one tick (likely in extreme-price zones), EV erodes further.
**Strategy 1 survives recalibration but is marginal.** Best operating point (0.25, 0.35) produces $6.55/game pre-spread ($6.20/game after §2.5 one-tick spread). Proceed cautiously — liquidity haircuts from Phase 3B could push this below viability. Consider the spread sensitivity the more important of the two numbers: if realized spreads are wider than one tick (likely in extreme-price zones), EV erodes further.

**Sample-size caveats:**

- Calibration based on 57 dip observations across ~30 games. The mapping in the [0.20, 0.50] ESPN range has sparse direct calibration data — it's anchored at 0.5 and extrapolated monotonically from the [0, 0.20] fit.
- Symmetry assumption (f(x) = 1 − f(1 − x)) is imposed by construction and not independently validated. A bilateral-dip analysis happens to rely most heavily on x < 0.5, so this is low-impact for Strategy 1 but would matter more for Strategy 2 (single-side mean reversion) — revisit before reusing this mapping there.
- One-tick spread assumption is a placeholder until §2.5 has orderbook-measured spreads at these target entry prices.

