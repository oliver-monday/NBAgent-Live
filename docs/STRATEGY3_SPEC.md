# Strategy 3 Spec — Swing Trading on Kalshi NBA Contracts

Living document. Phase 3's primary deliverable. Captures the
current best-guess rule set for Strategy 3, with each element
tagged by evidence source and confidence level.

**Evidence tiers:**
- **Kalshi-confirmed** — validated on real Kalshi orderbook/
  trade data (n=2 competitive games so far)
- **ESPN-scale** — supported by 1,234-game ESPN WP analysis;
  directional patterns expected to transfer, magnitudes will
  be smaller on Kalshi (+10-17pp compression at tails)
- **Hypothesized** — theoretically motivated, not yet tested
  at any scale

Last updated: 2026-04-20.

---

## 1. Operating parameters

| Parameter | Value | Evidence | Source |
|-----------|-------|----------|--------|
| Entry zone | $0.35-$0.55 (mid-range) | Kalshi-confirmed | HOU-LAL + ORL@DET oscillation analysis |
| Exit zone | Entry + $0.10-$0.15 | Kalshi-confirmed | 7 completed round-trips, median net $14-25 |
| Contract sizing | 100 contracts per position | Kalshi-confirmed | Trades probe: 100 contracts = 0.02% of 5-min bucket volume |
| Realized spread | $0.01 | Kalshi-confirmed | 5 games, all at $0.01 median |
| Top-of-book depth | ≥50k contracts 55% of time at mid ≤ $0.50 | Kalshi-confirmed | Pooled across 5 games |
| Hold time | 8-100 min (median ~30 min) | Kalshi-confirmed | HOU-LAL + ORL@DET round-trips |
| Competitive game filter | \|pre-game spread\| ≤ 6 | ESPN-scale | Standard filter across all analyses |

### Fee assumptions (per `docs/FEES.md`)

| Execution | Formula | At $0.40 entry, 100 contracts |
|-----------|---------|-------------------------------|
| Taker | `ceil(0.07 × C × P × (1-P))` | $1.68 per leg |
| Maker | `ceil(0.0175 × C × P × (1-P))` | $0.43 per leg |
| Round-trip taker-taker | 2 × taker | $3.36 |
| Round-trip maker-maker | 2 × maker | $0.86 |

Maker-maker execution is 4× cheaper. Strategy 3 economics
require maker execution on at least one leg.

---

## 2. Entry rule

### Primary signal (Kalshi-confirmed)

**Enter when a team's YES contract bid price drops to or below
the entry threshold ($0.40) during a competitive game.**

The signal is purely price-based. No model, no prediction, no
external data dependency beyond the Kalshi orderbook itself.

Evidence: 7 completed round-trips across 2 competitive Kalshi
games, all profitable at (0.40, 0.50) maker-maker. Entry
threshold validated against the oscillation pattern that
competitive NBA games naturally produce.

### Contextual modifiers

These refine entry decisions but are not required for the
signal to fire. Each is tagged with evidence strength.

#### A. Favor the pre-game favorite when both sides dip (ESPN-scale)

When both teams' contracts are in or near the entry zone,
prefer entering on the pre-game favorite's YES contract.

- Favorites who dip below $0.35 WP recover above $0.50 in
  76% of games vs 73% for underdogs. (Table 9 vs 10,
  ESPN scoring-run catalog.)
- Favorites recover ~1.5 minutes faster at every threshold
  (median 6.0 min vs 7.6 min at < 0.35).
- Recovery gap widens at deeper dips: 60% vs 54% at < 0.25.

**This is NOT the killed "favorite-side to resolution"
variant.** That held favorites to game end (−$18.40 blended
net). This is a swing-trade *preference* for which side to
enter, with the same exit discipline.

Confidence: ESPN-scale. The asymmetry direction should
transfer to Kalshi (same prior-anchoring mechanism), but
the magnitude may differ. Needs validation on ≥10 Kalshi
games.

#### B. Earlier in the game is better (ESPN-scale)

Q1 scoring runs reverse at 59% positive (3-min recovery).
Q4 runs reverse at only 44%. The prior-anchoring effect is
strongest early when the market still trusts the pre-game
line.

- Implication: be more willing to enter positions in Q1/Q2.
  Be more cautious in Q4 where runs are more likely to
  represent genuine separation.
- The prior takes roughly a full half to dissolve: underdog
  leads at end of Q1 convert to wins only 54% of the time;
  by end of Q3 it's 73%. (Table 8, ESPN scoring-run catalog.)

Confidence: ESPN-scale. Period effects should transfer.

#### C. Moderate runs are the sweet spot (ESPN-scale)

Scoring runs of 6-7 points produce the best post-run
recovery (53% positive at 3 min). Runs of 13+ points
recover at only 43%.

- Don't wait for a massive run. A 6-7 point deficit is
  enough to move the market and likely to reverse.
- Large runs (13+) more often represent genuine team
  quality separation, not mean-reverting variance.

Confidence: ESPN-scale. Effect size is modest (10pp
between best and worst bucket). Needs Kalshi validation.

---

## 3. Exit rule

### Primary exit (Kalshi-confirmed)

**Exit when the position's YES contract bid price rises to
or above the exit threshold ($0.50).**

Symmetric to entry: purely price-based. The $0.10 gross
swing at (0.40, 0.50) yields $10 gross on 100 contracts,
~$9.14 net maker-maker.

### Alternative exits

- **Wider grid (0.40, 0.55):** $15 gross, fewer completions
  but higher net per trip. ORL@DET produced 1 trip at this
  grid ($39.28 net). Trade-off: longer hold time (104 min
  observed).
- **Tighter grid (0.35, 0.45):** More frequent entries but
  entering at $0.35 means deeper dip required. ORL@DET:
  3 trips at this grid, $20.20 mean net.

The optimal grid is an open question for the graduation
evaluation at 10 games. Current recommendation: primary
grid (0.40, 0.50) with opportunistic wider exits when the
market moves favorably.

### Stop-loss / time exit (Hypothesized)

No stop-loss rule is currently specified. The ESPN max-
recovery data (89% of runs produce some positive recovery
within 5 min) suggests patience is rewarded. However,
the distribution has a long tail — some positions may
require 30+ minutes of hold time.

Open question: should a time-based exit (e.g., "exit at
market after 60 min if exit threshold not reached") be
added? Requires more Kalshi data to evaluate the trade-off
between patience and opportunity cost.

---

## 4. Execution preferences

### Timeout windows are execution opportunities (Kalshi-confirmed)

During NBA timeouts, the Kalshi orderbook shows:
- Bid depth 2.3× baseline
- Ask depth 1.8× baseline
- Spread at $0.01 floor (19 of 20 observed timeouts)
- Volume concentration 1.2-1.5× baseline

When a timeout coincides with the entry threshold being
met, prefer entering via a maker order during the dead
ball. The book is maximally receptive.

### Timeouts are NOT directional signals (ESPN-scale, confirmed)

Runs followed by timeouts recover at 51% vs 53% without
(Table 7, ESPN scoring-run catalog, n=6,210). Timeouts
do not predict recovery. The entry signal remains price-
based; the timeout is an execution quality enhancer, not
a trigger.

### Market reaction speed (Kalshi-confirmed, n=2)

Per-basket price impact on Kalshi:
- 3-pointer: +$0.04 immediate, 3.5s median reaction lag
- 2-pointer: +$0.017 immediate, 4.1s median lag
- Free throw: +$0.006, 19.9s median lag

Impact peaks in the $0.40-$0.50 zone ($0.024/play).
Execution budget is 3-4 seconds for reactive entries —
tight but nonzero. Maker orders bypass this constraint
entirely (order is already resting when the basket
happens).

### Maker execution is essential

Maker-maker round-trip fees are $0.86 vs $3.36 taker-taker
at $0.40 entry. At $0.10 gross swing, taker-taker nets
$6.64 (34% fee drag); maker-maker nets $9.14 (9% drag).
Strategy 3 is marginal on taker-taker and comfortable on
maker-maker. Prioritize resting limit orders.

---

## 5. Sizing constraint: RESOLVED

Kalshi trades probe (HOU-LAL, 93,838 trades, 29.2M
contracts): 100-contract orders are 0.02% of median 5-min
bucket volume. Strategy 3 zone ($0.35-$0.55) carries 40.8%
of total market volume. Even 1,000-contract orders are
well-absorbed. Sizing is not a constraint at any plausible
operating scale.

---

## 6. Universe estimates

| Metric | Value | Source |
|--------|-------|--------|
| Competitive games per regular season | 549 of 1,230 (~45%) | Master CSV, \|spread\| ≤ 6 |
| ESPN round-trips per season (0.35, 0.50) | ~2,272 | Game flow trajectories |
| ESPN-to-market survival rate | 30.4% | FanDuel timeseries (n=15) |
| Estimated market-price round-trips/season | ~689 | 2,272 × 30.4% |
| Scoring runs per competitive game | ~11 (at 6pt/3min) | ESPN scoring-run catalog |
| Post-run recovery rate (any positive, 5 min) | 89% | ESPN scoring-run catalog |
| Post-run recovery rate (positive at 3 min checkpoint) | 52% | ESPN scoring-run catalog |

### Annual EV projection (illustrative, not committed)

At 100-contract sizing, maker-maker, (0.40, 0.50) grid:
- ~689 round-trip opportunities per regular season
- Assume 50% execution rate (monitoring, missed games): ~345
- $9.14 net per trip (at $0.10 swing, maker-maker)
- **~$3,150 annual EV** on the conservative end

At wider grids and better execution rates, prior estimates
ranged to ~$9,600 (from Odds API timeseries analysis). The
true number depends on realized Kalshi round-trip frequency
and the grid chosen, both open questions for the graduation
evaluation.

---

## 7. Open questions (blocked on 10-game graduation data)

1. **Realized round-trip frequency on Kalshi at (0.40, 0.50).**
   Current: 2/5 games (40%). Need ≥10 competitive games.

2. **Optimal entry/exit grid.** (0.40, 0.50) vs (0.35, 0.45) vs
   (0.40, 0.55). Trade-off between frequency and per-trip
   profit. Graduation evaluation should compare all three.

3. **Favorite asymmetry on Kalshi.** ESPN shows 76% vs 73%
   recovery at < 0.35 (modest). Does this survive market
   compression? n=2 is not enough to tell.

4. **Period effects on Kalshi.** ESPN shows Q1 > Q4 for
   recovery. Does this hold at market prices?

5. **Time exit / stop-loss.** Should positions have a maximum
   hold time? Requires observing the distribution of hold
   times across ≥10 games.

6. **Playoff vs regular season.** Current data is playoff-only.
   Playoff games may be systematically more competitive (and
   thus more profitable) than regular season. Need regular-
   season data eventually.

---

## 8. Graduation status

**Progress: 2/10 competitive Kalshi games toward graduation.**

All 6 viability scorecard criteria currently pass (from
`docs/KILL_CRITERIA_draft.md` recalibrated thresholds):

| Criterion | Threshold | Current | Status |
|-----------|-----------|---------|--------|
| RT frequency at (0.40, 0.50) | ≥ 15% | 40% (2/5) | ✓ |
| Net per trip (median, maker) | ≥ $5 | $21.70 | ✓ |
| Realized spread (median) | ≤ $0.02 | $0.01 | ✓ |
| Depth (% ≥ 50k) | ≥ 50% | 55% | ✓ |
| Hold time (median) | ≥ 3 min | 49 min | ✓ |
| MAE (median, % of entry) | < 50% | 17.5% | ✓ |

Graduation at ≥10 competitive games triggers Phase 4a
(signal alerts for manual paper-trading).

---

## Supersedes

- `docs/strategy3_assessment.md` — historical snapshot from
  2026-04-19. That document remains as an archive of the
  state of knowledge at that time. This spec is the living
  document going forward.
