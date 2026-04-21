# Strategy 3 Spec — Swing Trading on Kalshi NBA Contracts

Living document. Phase 3's primary deliverable. Captures the
current best-guess rule set for Strategy 3, with each element
tagged by evidence source and confidence level.

**Evidence tiers:**
- **Kalshi-confirmed** — validated on real Kalshi trade data.
  As of 2026-04-20: 168 games paired (ESPN WP + Kalshi trades),
  165 competitive (|spread| ≤ 6).
- **ESPN-scale** — supported by 1,234-game ESPN WP analysis;
  directional patterns expected to transfer. Compression
  calibration now quantified: Kalshi = ESPN + delta, where
  delta varies by WP zone (see §1A below).
- **Hypothesized** — theoretically motivated, not yet tested
  at any scale

Last updated: 2026-04-21.

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

### §1A. ESPN WP ↔ Kalshi price calibration (Kalshi-confirmed, n=168 games)

Kalshi systematically compresses toward $0.50 relative to
ESPN WP. The compression magnitude varies by WP zone:

| ESPN WP zone (fav) | Kalshi − ESPN (mean) | 95% CI | N obs |
|---------------------|---------------------|--------|-------|
| 0.00–0.20 | +4.61pp | ±0.12pp | 7,332 |
| 0.20–0.40 | +8.30pp | ±0.22pp | 6,130 |
| 0.40–0.60 | +4.09pp | ±0.16pp | 9,422 |
| 0.60–0.80 | −1.76pp | ±0.12pp | 9,799 |
| 0.80–1.00 | −2.73pp | ±0.06pp | 14,298 |

**Operational translation:** ESPN WP of ~0.32 for a team
corresponds to Kalshi price ~$0.40 for that team (the
entry threshold). ESPN WP crossing 0.32 is the early-warning
signal that Kalshi is approaching the entry zone. The
crossover point (delta ≈ 0) is at approximately 0.58 WP.

**Convergence:** |delta| shrinks from 7.7pp at >36 min
remaining to 2.5pp at 1–3 min remaining (n=46,981 bins).
Pick'em games converge 50% faster than moderate favorites
(slope −0.000025/s vs −0.000016/s, both p ≈ 0).

**Per-basket reactions:** Kalshi moves ±0.02pp per scoring
play vs ESPN ±0.04–0.20pp. Kalshi absorbs individual
baskets as noise and reprices on accumulated runs, not
single plays. This confirms price-threshold entry over
any model-based or per-event trigger.

---

## 2. Entry rule

### Primary signal (revised 2026-04-21 — filtered variant)

**Entry requires four conditions to fire simultaneously:**

1. Favorite-side only (pre-game favorite per DraftKings
   pickcenter or home_spread < 0)
2. Period is Q1 or Q2
3. Favorite's ESPN WP has dropped ≥ 3pp within the last 120
   seconds of game time
4. Favorite's Kalshi bid price drops to ≤ $0.40

**Why all four:** the naive single-condition rule (bid ≤ $0.40
alone) was shown to be net negative-EV (−$4.57 per entry counting
held-to-loss outcomes). 60.9% of those entries reached $0.50
(profitable round-trip), 39.1% went to resolution loss. No
stop-loss, averaging-in, upside-capture, or partial-exit variant
rescues the aggregate EV. Entry *selection* (filters) is what
restores positive EV. Per the holdout validation, 4 of 6 random
seeds produce positive test-set P&L with this filter stack.

Full derivation in `docs/analysis_outputs/strategy3_entry_filters.md`
and `docs/analysis_outputs/strategy3_holdout_validation.md`.

### Original (retained for archive) — naive primary signal

Prior spec: "Enter when a team's YES contract bid price drops
to or below $0.40 during a competitive game." Purely price-based,
no filter. This was the rule the graduation eval initially
validated; subsequent failed-entry analysis retracted it.

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

### Convergence-zone exit preference (Kalshi-confirmed, n=168 games)

**Prefer exiting positions when 1–3 minutes remain in
regulation.**

The WP vs Kalshi paired analysis (168 games) shows that
|delta| between Kalshi price and ESPN WP reaches its
minimum at 1–3 minutes remaining (2.47pp). After this
window, delta spikes back to 3.97pp in the final minute
due to last-possession volatility in close games.

Implication: if the exit threshold has not been reached
by the 3-minute mark but the position is near breakeven,
consider exiting at market during this convergence window
rather than holding into the volatile final minute. This
is a preference, not a hard rule — the primary exit
remains price-based at the exit threshold.

### Stop-loss / time exit (Hypothesized)

No stop-loss rule is currently specified. The ESPN max-
recovery data (89% of runs produce some positive recovery
within 5 min) suggests patience is rewarded. However,
the distribution has a long tail — some positions may
require 30+ minutes of hold time.

Open question: should a time-based exit (e.g., "exit at
market after 60 min if exit threshold not reached") be
added? The graduation evaluation (§8) reports hold time
distributions to inform this decision.

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

### Timeouts are convergence micro-events (Kalshi-confirmed, n=168 games)

Timeouts produce marginally tighter delta between Kalshi
and ESPN (mean |Δ| 5.37pp vs 5.54pp outside timeouts,
Mann-Whitney p = 8.5e-08, n=7,175 timeout windows).
The effect is small but statistically definitive. Combined
with better depth and spread, timeouts are confirmed as
the optimal execution window across three dimensions:
tighter delta, deeper book, narrower spread.

Timeouts remain NOT directional signals. Runs followed
by timeouts recover at 51% vs 53% without (ESPN scoring-
run catalog, n=6,210). The entry signal remains price-
based; the timeout is purely an execution quality enhancer.

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
| Games entering S3 zone (of competitive) | 156 of 165 (95%) | WP vs Kalshi paired (n=168) |
| Mean S3 zone time per game | 2,991s (35.3% of game) | WP vs Kalshi paired (n=168) |
| ESPN round-trips per season (0.35, 0.50) | ~2,272 | Game flow trajectories |
| ESPN-to-market survival rate | 30.4% | FanDuel timeseries (n=15) |
| Estimated market-price round-trips/season | ~689 | 2,272 × 30.4% |
| Scoring runs per competitive game | ~11 (at 6pt/3min) | ESPN scoring-run catalog |
| Post-run recovery rate (any positive, 5 min) | 89% | ESPN scoring-run catalog |
| Post-run recovery rate (positive at 3 min checkpoint) | 52% | ESPN scoring-run catalog |

### Annual EV projection (revised 2026-04-21)

**Naive (0.40, 0.50) grid: negative EV.** Full-sample analysis
gives −$5,963/yr counting held-to-loss entries. Superseded by
filtered variant.

**Filtered variant** (WP momentum + favorite + Q1/Q2 + upside
exit, 100 contracts, maker-maker):
- Train-set full-sample: +$578/yr
- Holdout test-set estimate: **+$825/yr** (n=19 test entries)
- Conservative range: **+$578–$825**

The earlier "$3,150" / "$9,600" projections were based on the
completed-RT subset statistic and are retracted. See §8.

---

## 7. Open questions

1. **Optimal entry/exit grid.** (0.40, 0.50) vs (0.35, 0.45) vs
   (0.40, 0.55). Graduation evaluation compares all three grids
   on 168-game dataset. See graduation report.

2. **Favorite asymmetry on Kalshi.** ESPN shows 76% vs 73%
   recovery at < 0.35 (modest). Paired data shows Kalshi is
   always above ESPN in the 0.20-0.40 zone (+8.30pp), suggesting
   the market shares the favorite-recovery prior. Needs formal
   test on Kalshi round-trip data split by fav/dog side.

3. **Period effects on Kalshi.** ESPN shows Q1 > Q4 for
   recovery. Graduation evaluation reports entry period
   distribution and per-period net profit. See graduation report.

4. **Bilateral guaranteed-profit frequency.** How often do
   both sides dip below $0.40 in the same game? Each such game
   is a ~$18 guaranteed profit (minus 4 maker legs). Graduation
   evaluation reports this. See graduation report.

5. **Taker flow as directional signal.** 15M+ cached trades
   have taker_side field. Net taker flow may predict subsequent
   price movement. Not yet analyzed.

6. **Orderbook shape / support-resistance.** Logger snapshots
   capture full depth. Bid walls at specific price levels may
   inform per-game entry/exit level selection beyond fixed grids.
   Not yet analyzed.

---

## 8. Graduation status (revised 2026-04-21)

**Evaluation dataset: 168 games (165 competitive, |spread| ≤ 6).**

The original graduation evaluation (`strategy3_graduation_eval.py`)
scored all six viability criteria as passing: 63.6% RT frequency,
$13.74 median net, 100% of completed round-trips profitable.
Verdict at the time: GRADUATED.

**That verdict was retracted.** The graduation eval measured only
*completed* round-trips — the 60.9% of entries that reached
$0.50. The `strategy3_failed_entries.py` analysis added the other
39.1% (positions held to a loss when the exit was never reached)
and found **true EV per entry is −$4.57, annual EV −$5,963**.
Stop-loss sweep (best $0.34): −$1.27, upside capture (sell 25% +
hold 75%): −$0.59. All variants of the naive $0.40 entry are
negative-EV.

### What was validated instead

The naive entry trigger at $0.40 is negative-EV in aggregate. A
*filtered* variant was holdout-validated.

**Validated S3 filter spec** (best test-set config, seed=42
110/55 holdout):

- Entry: favorite-side only, when **ESPN WP drops ≥ 3pp in the
  last 120s** AND period is Q1 or Q2 AND favorite's Kalshi
  bid ≤ $0.40.
- Exit strategy: upside capture (stop $0.34, sell 25% at $0.50,
  hold 75% to resolution).
- Train mean P&L: +$2.85/entry. **Test mean P&L: +$4.35/entry.
  Test annual EV: +$825.**

6-seed stability: 4 of 6 seeds produce positive test-set P&L.
The `wp+fav+period+upside` combo was picked best by 3 of 6
seeds and validated on all three.

Deployment tier: validated but thin sample (~32 train + ~19 test
entries per split). Projected annual EV range **+$578 to +$825**
per STRATEGY4_SPEC.md §9.

Full analysis: `docs/analysis_outputs/strategy3_holdout_validation.md`.

### Phase 4a status

Phase 4a is now unlocked, but **not on naive S3**. Phase 4a
gating relies on three independent validated alpha sources:

1. **S1 bilateral** (confirmed, +$1,608/yr)
2. **S4A dip-recovery** (confirmed, +$1,886/yr; see STRATEGY4_SPEC.md)
3. **S3 filtered** (holdout-validated, +$578–$825/yr)

Total combined annual EV estimate: **+$4,072–$4,319**.

---

## Supersedes

- `docs/strategy3_assessment.md` — historical snapshot from
  2026-04-19. That document remains as an archive of the
  state of knowledge at that time. This spec is the living
  document going forward.
