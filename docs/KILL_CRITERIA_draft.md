# Kill Criteria — NBAgent-Live Strategy Graduation & Termination

Draft written 2026-04-17, before any Kalshi game-day data exists.
Intentionally written pre-data to avoid anchoring thresholds to
observed outcomes.

Addresses §3.1 of `THESIS_open_questions.md`. Once finalized, fold
into `THESIS.md` under Success Criteria.

---

## Measurement framework

All criteria are evaluated on **held-out Kalshi data** — games not
used to develop or tune the strategy. Minimum sample: 50 competitive
games with full Kalshi orderbook snapshots and matched ESPN WP data.
"Competitive" = pre-game spread ≤ 6 points, using the pre-game
spread from `data/nba_master_2025_26.csv` (integrated 2026-04-17).

"Opportunity" means: Kalshi bid price crossed the threshold AND
top-of-book resting size at that price ≥ the minimum fill size at
that moment. A price crossing with zero fillable size is not an
opportunity.

Fee assumptions per `FEES.md`: taker formula
`round_up(0.07 × C × P × (1-P))`, maker at 1/4 of taker. Spread
cost budgeted at one tick ($0.01) per leg unless realized spread
data supports a different number.

---

## Strategy 1: Bilateral convergence

### Graduates if ALL of:

1. **Opportunity rate ≥ 12%** of competitive games on held-out
   Kalshi data produce a bilateral opportunity where both sides'
   Kalshi bid prices dip below a combined cost of $0.80 at some
   point during the game, with the two dips separated by ≥ 3
   minutes of game time.

   *Rationale:* Stern-implied rate was 30% at <$0.40 combined
   (i.e. <$0.20 each side). Kalshi rate will be lower (§1.2).
   12% is a 60% haircut from the Stern proxy — enough room for
   MM defense and measurement noise while still producing
   ~1 opportunity per 8-game slate.

2. **Fillable size ≥ 50 contracts** ($50 notional per side at
   $0.10 entry, $500 at $0.10 × 100) at the bid price when the
   opportunity occurs, measured from top-of-book resting size in
   the orderbook snapshot closest to the dip.

   *Rationale:* 50 contracts at $0.15 = $7.50 risk per side.
   Below this, the strategy exists but is economically
   uninteresting — you can't deploy meaningful capital.

3. **Net profit per opportunity ≥ $5 per $100 notional** after
   fees and one-tick spread per leg.

   *Rationale:* At $0.15 + $0.15 entry (100 contracts each),
   gross profit = $70, fees ≈ $1.80, spread cost ≈ $2.00.
   Net ≈ $66.20 on $30 invested = $220 per $100 notional.
   This is a low bar. The real constraint is criteria 1 and 2.

### Killed if ANY of:

- Opportunity rate < 5% of competitive games. This means the
  Kalshi MM is defending effectively and bilateral fills at
  attractive combined prices are rare events, not a systematic
  pattern.
- Fillable size at target prices is consistently < 20 contracts
  across playoff AND regular season samples. The strategy
  exists in theory but can't absorb meaningful capital.
- Both-legs-in-same-game at combined cost < $0.90 occurs in
  fewer than 3 games across the entire held-out sample.
  The MM's floor pricing is too high for the arithmetic to
  work after costs.

### Post-recalibration update (2026-04-19)

The thresholds above were written in ESPN WP terms. Sportsbook
backfill (30 games, 57 dip observations) established that ESPN
WP diverges from real-money markets by +10-17pp at the tails.
Recalibrated analysis at sportsbook-denominated thresholds:

- **Opportunity rate at (0.25, 0.35) SB thresholds: 17.7%** of
  |spread|≤6 games (asymmetric-any-order). Down from 49% at
  ESPN (0.20, 0.30).
- **EV per competitive game: $6.55** (100 contracts, taker-
  taker, no spread cost). Down from $23.23 at ESPN thresholds.
- **Graduation bar (12% at strict bilateral)** was sized against
  ESPN-denominated strict bilateral (26.6%). At SB-calibrated
  strict (0.35, 0.35), the rate is 18.9% — above the 12% bar.
  However, the 12% bar was calibrated to a per-trade profit
  that is now thinner ($30 gross at (0.35, 0.35) vs $60+ at
  ESPN (0.20, 0.20)). The bar itself needs reconsideration
  against the recalibrated economics.

The existing kill criteria remain valid as *structure* (rate ×
fill × profit) but the specific numerical thresholds should be
re-anchored to sportsbook-denominated entry prices once Phase
3B provides realized Kalshi data at these price levels.

---

## Strategy 2: Single-side mean-reversion

### Graduates if ALL of:

1. **Kalshi-priced win rate residual ≥ +5pp** at the tails.
   Specifically: teams whose Kalshi bid was ≤ $0.15 at any point
   during a tradeable window (sec_rem ≥ 60) go on to win at a
   rate ≥ 5pp higher than their Kalshi bid price implied.

   *Rationale:* Stern residual was +9pp. We expect some of that
   to survive against Kalshi (Kalshi likely tracks ESPN/Stern
   per §1.1), but not all of it. +5pp is the threshold where
   post-fees EV is meaningfully positive: at $0.10 entry, a
   +5pp residual (15% actual vs 10% implied) yields ~$4.37
   EV per 100 contracts after fees.

2. **Sample size ≥ 200 observations** in the ≤$0.15 bucket
   across held-out games. The residual must be statistically
   distinguishable from zero at p < 0.05 (binomial test).

   *Rationale:* Small samples can show large residuals by
   chance. 200 observations at 15% actual win rate gives
   ~30 wins, enough to detect a 5pp residual with reasonable
   power.

3. **Fillable size ≥ 50 contracts** at the Kalshi bid price
   when the team is priced ≤ $0.15.

### Killed if ANY of:

- Residual against Kalshi is < +3pp across all time-remaining
  cuts. This means Kalshi's MM is better-calibrated than Stern
  at the tails, and the model-dependent edge doesn't exist
  against the actual counterparty.
- Residual exists but is concentrated in a single game-state
  bucket (e.g., only in the last 2 minutes, or only in OT)
  that produces fewer than 20 observations per season.
  An edge that fires 20 times per season at $10 per
  opportunity is not worth maintaining infrastructure for.
- Win rate at ≤ $0.10 Kalshi price is < 12%. The asymmetric
  payoff is real but not enough to overcome the cost of the
  ~88% loss rate after fees.

### Preliminary kill signal (2026-04-19)

Sportsbook backfill shows Kalshi/sportsbooks price underdog
moments at +10-17pp above ESPN. The +3pp ESPN-vs-actual residual
(Phase 3A) is entirely absorbed. Residual against Kalshi is
estimated at −7 to −14pp (negative edge). This meets the kill
criterion "Residual against Kalshi is < +3pp across all time-
remaining cuts" with substantial margin.

Formal kill deferred pending Phase 3B confirmation with ≥10
games of Kalshi-priced-moment resolution data. However, rescue
would require the sportsbook backfill to be fundamentally wrong
about the Kalshi-ESPN gap — unlikely given 30-game, 341-quote
concordance with 8+ independent sportsbooks.

---

## Strategy 3: Active management

### Graduates if ALL of:

1. **Round-trip opportunities ≥ 8%** of competitive games. A
   round-trip opportunity = a game where a team's Kalshi bid
   drops to ≤ $0.20 and subsequently rises to ≥ $0.35 (or
   vice versa) within the same game, with both prices showing
   fillable size ≥ 50 contracts.

   *Rationale:* $0.15 gross swing on 100 contracts = $15
   gross. Maker-maker fees ≈ $0.67, spread ≈ $0 (you're
   setting the price). Net ≈ $14.33. Needs to happen often
   enough to justify active monitoring.

2. **Maker fill rate ≥ 60%** during game stoppages (timeouts,
   free throws, quarter breaks). Limit orders resting during
   stoppages must actually get filled at least 60% of the
   time at the rested price before the book moves away.

   *Rationale:* Maker execution is critical for Strategy 3
   economics (per `FEES.md`). If resting orders consistently
   get jumped or the book moves before fill, the cost
   advantage of maker execution evaporates and taker-taker
   fees eat the small swings.

3. **Median swing capture ≥ $0.10** on completed round-trips
   in the held-out sample. If achievable swings are $0.05
   on average, fees and spread consume too much.

### Killed if ANY of:

- Round-trip frequency < 3% of competitive games. The
  monitoring burden (watching every game for rare signals)
  exceeds the payoff.
- Realized spread at entry prices (≤ $0.20) is ≥ $0.03
  during live game states. At 3 ticks of spread per leg,
  a $0.15 round-trip is break-even before fees. The cost
  structure doesn't support the strategy.
- Maker fill rate < 40%. Execution becomes unreliable enough
  that the strategy can't be systematized — it degrades to
  "get lucky sometimes."
- Median time-in-position from entry to profitable exit
  is < 90 seconds. This means the swings exist but move
  too fast for manual execution (the thesis explicitly
  rejects HFT; if the opportunity requires HFT-like speed,
  it's outside our operating model).

### Strategy 3 recalibration (2026-04-20)

The original thresholds assumed extreme-price entry (≤ $0.20)
and $0.15+ swings. Research established that the actual
operating zone is $0.35-$0.55 with $0.10-$0.15 swings.
Recalibrated criteria:

**Graduates if ALL of (on ≥10 competitive Kalshi games):**

1. **Round-trip frequency ≥ 15%** of |spread|≤6 games
   produce a completed round-trip at (0.40, 0.50) or
   better thresholds. Current: 2/2 competitive games
   (100%), but n=2 is not meaningful.
2. **Median net per round-trip ≥ $5** (maker-maker, 100
   contracts). Current: $21.70 pooled median (n=7 trips
   across 2 games).
3. **Realized spread ≤ $0.02** at mid-range entry prices.
   Current: $0.01 across 5 games.
4. **Depth ≥ 50 contracts** at entry prices in ≥50% of
   entry-zone snapshots. Current: 55% pooled.

**Killed if ANY of (on ≥10 competitive Kalshi games):**

- Round-trip frequency < 5%
- Median net per trip < $0
- Realized spread ≥ $0.03 at entry prices
- All round-trips complete in < 90 seconds

**Favorite-side variant: KILLED (2026-04-19).** Pooled
blended net −$18.40 on FanDuel data. Not revisitable.

### Sizing constraint: RESOLVED (2026-04-20)

Kalshi trades probe confirmed 100-contract orders are
invisible (0.02% of 5-min bucket volume). Sizing is not
a constraint at any plausible Strategy 3 scale. The
original "fillable size ≥ 50 contracts" criterion is
satisfied with substantial margin.

---

## Project-level decisions

### Continue to Phase 4 if:

At least one strategy graduates on held-out data. Phase 4
begins with paper-trading the graduated strategy on live
games using signal alerts, no real capital.

### Pause and reassess if:

All three strategies fall in a gray zone — none clearly
graduate, none clearly killed. This likely means the sample
is too small or the measurement framework needs refinement.
Extend Phase 1 data capture through the 2026 playoffs and
into the 2026-27 regular season. Re-evaluate with 3× the
data. Set a hard deadline: if gray-zone persists after 200
competitive games with full Kalshi data, treat as a kill.

### Kill the project if:

All three strategies are killed on held-out data, OR the
gray-zone deadline passes without graduation. Document the
findings in `RESEARCH_LOG.md`, archive the data, and close
the repo to active development. The data infrastructure and
thesis documentation are the deliverable.

No money is deployed in any scenario until a strategy has
been (a) graduated on held-out data, (b) paper-traded for
≥ 20 games with results consistent with the spec, and
(c) reviewed by the user with full context on risks.

---

## Calibration notes

These thresholds are first drafts. Two known sources of
miscalibration:

1. **Playoff vs regular season.** Phase 1 captures playoff
   data first. Playoff games are more competitive on average,
   which likely inflates opportunity rates relative to the
   regular-season baseline where most operating time would
   live. Graduation criteria should ultimately be met on
   *regular-season* held-out data, not just playoffs. For
   now, we evaluate on whatever data exists, but flag if
   results are playoff-only.

2. **Sample size vs precision.** 50 competitive games is the
   minimum for evaluation, not the target. At 50 games, a
   12% opportunity rate means ~6 bilateral opportunities.
   Confidence intervals are wide. The thresholds above are
   designed to be meaningful even at 50 games (a strategy
   that shows 0-1 opportunities in 50 games is clearly
   dead), but gray-zone outcomes are likely at this sample
   size. The 200-game reassessment window exists for this
   reason.

If Phase 1 data reveals that any threshold is obviously
miscalibrated (e.g., Kalshi prices never go below $0.20 in
any game, making the ≤$0.20 entry threshold moot), adjust
the specific number and note the change with a date. Do not
adjust thresholds to accommodate observed data without also
adjusting the rationale — that's the drift this document
exists to prevent.

---

## Retires

- `THESIS_open_questions.md` §3.1 — kill criteria now exist
  in draft form. Mark §3.1 resolved once these are reviewed
  by Oliver and folded into `THESIS.md`.
