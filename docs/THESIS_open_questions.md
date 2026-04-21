# THESIS — Open Questions & Pressure Points

Companion to `THESIS.md`. This is a living document; its purpose is to
hold the load-bearing claims, unresolved questions, and structural
risks in the thesis *visibly* so they aren't quietly assumed away as
the project progresses.

Each item has:
- **Status** — whether evidence so far supports, contradicts, or is
  silent on the claim.
- **What retires it** — concrete criterion for marking resolved.

Items are retired by appending a dated resolution line, not by
deletion — the audit trail matters. When Phase 3 produces a
strategy spec, this document gets synthesized: surviving open items
either fold into the spec's caveats or graduate into the research
log as findings.

Last updated: 2026-04-21.

---

## 1. Load-bearing claims that need more evidence

### 1.1 Kalshi ≈ ESPN-style WP model

**Claim in thesis:** "NBA live-game win probability is priced tightly
on Kalshi — the market mirrors consensus WP models (ESPN-style margin
+ time) to within ~1pp."

**Status:** Weakly supported. Evidence is two observations from a
single game (4/15 GSW-LAC Play-In at 72-74 and 114-115, Kalshi within
~1pp of ESPN both times). This is suggestive, not settled.

**Why it matters:** The claim does double duty in the thesis. It
(a) justifies treating the pilot's Stern-vs-actual +9pp residual as a
proxy for Stern-vs-Kalshi residual, which is the basis for the
single-side mean-reversion strategy, and (b) makes "Kalshi mirrors
the consensus model" the reason the opportunity is structural rather
than informational. If Kalshi's MM is meaningfully better-calibrated
than ESPN at the tails — for example, floors quotes defensively
during wild swings — strategy 2's edge partially or fully evaporates,
and strategy 1's opportunity frequency drops.

**What retires it:** Phase 2 + early Phase 3. Pair logged Kalshi
snapshots with ESPN WP at matched game timestamps across a meaningful
sample (target: ≥50 competitive games, ≥10,000 paired observations,
stratified by game state bucket — early/mid/late, close/blowout,
regular/playoff). Report the Kalshi−ESPN residual distribution. The
~1pp claim graduates from hypothesis to finding if median |Δ| ≤ 2pp
and p95 |Δ| ≤ 5pp across all buckets. Tails matter more than the
median — a model that's tight at 40-60% WP but diverges at 5-15% WP
is the exact profile that would hide this issue.

**Update this section with dated evidence once data exists.**

**Result (2026-04-17) — Partially confirmed.** Phase 3A
calibration against the full 2025-26 ESPN WP dataset (see
`docs/RESEARCH_LOG.md` 2026-04-17 Phase 3A entry) showed residual
+2.6 to +3.3pp across WP 0.075–0.20 buckets — at the low end of
the "confirmed if +3 to +7pp" range. Strategy 2 edge against ESPN
survives but is thinner than predicted. The Kalshi residual —
which is what actually matters for Strategy 2 — is still blocked
on Phase 3B. See §1.4 (added 2026-04-17) for a structural
reframing: the +3pp residual may mask spread-heterogeneous
regimes, in which case Strategy 2's entry rule needs
spread-conditional stratification rather than a pooled threshold.

**Result (2026-04-19) — Denied as stated, reframed.** Phase 3B
smoke test (n=4 usable games, 2,304 paired observations) and
sportsbook backfill (57 dip moments, 341 fresh bookmaker
quotes) show Kalshi is systematically +10-14pp above ESPN at
low WP and −10-14pp below ESPN at high WP. Sportsbook consensus
matches Kalshi, not ESPN. The correct claim is "Kalshi ≈
sportsbook consensus" (supported), not "Kalshi ≈ ESPN"
(denied). ESPN's WP model is more reactive to game state than
any real-money market.

**Implications for downstream claims:**
- Strategy 2's +3pp ESPN residual does not transfer to Kalshi.
  Sportsbooks/Kalshi price those moments at +10-17pp above
  ESPN, well above actual win rates. Strategy 2 edge is
  negative on real-money markets.
- Strategy 1's bilateral rate needs sportsbook-calibrated
  thresholds. Recalibrated optimal: (0.25, 0.35) at 17.7%
  rate, EV $6.55/game — marginal but positive.
- The pilot's "within ~1pp" observations (4/15 GSW-LAC at
  72-74 and 114-115) were in the ~0.30-0.34 WP zone where
  the compression residual happens to be small. Not
  representative of the full WP range.

### 1.2 Pilot bilateral-dip frequencies are upper bounds

**Claim in thesis:** "Pilot frequency (2024-25 data): ~30% of
competitive games offered bilateral <$0.20 dips on both sides."

**Status:** Accurate as stated — but the reader should understand
these are Stern-implied WP crossings, not Kalshi price crossings.
They're a proxy that's only as good as 1.1 above.

**Why it matters:** If Kalshi's MM floors quotes at, say, $0.08 as
a defensive posture during late-game swings that Stern prices at
$0.03, the addressable bilateral opportunity rate at the $0.15
threshold could be materially lower than 30%. Fill-quality on any
individual opportunity is a separate question (covered under §2.1).

**What retires it:** Phase 3 re-runs the bilateral dip analysis
against actual logged Kalshi quotes. Report the rate gap:
*(Stern-implied bilateral <$0.15 rate) vs (Kalshi-bid bilateral
<$0.15 rate)*. Expected direction: Kalshi rate ≤ Stern rate. Size
of the gap is the interesting quantity.

### 1.3 "Mechanical edge" framing on bilateral convergence

**Claim in thesis:** Strategy 1's edge "doesn't depend on Kalshi
mispricing" and is "mechanical."

**Status:** True only if you can actually fill both legs at the
target prices. The mechanical part is the arithmetic
($0.15 + $0.15 = guaranteed $0.70); the non-mechanical parts are
(a) whether the price crosses your threshold on both sides in the
first place and (b) whether there's enough resting liquidity at
that price to fill a meaningful position. Both are Kalshi-MM
behavior questions, not arithmetic questions.

**Why it matters:** The thesis' cleanest strategy is rhetorically
positioned as edge-independent, which risks under-weighting how
much Kalshi MM behavior still drives outcomes. Thesis readers
(including future-us) should not mistake "guaranteed profit given
two fills at target prices" for "guaranteed profit."

**What retires it:** Restatement in Phase 3's strategy spec in
the form: "Bilateral convergence produces guaranteed profit
*conditional on* (i) opportunity rate ≥ X on bucket Y of games,
(ii) fillable notional ≥ $Z at target prices." Specific values
come from the logged data.

### 1.4 ESPN WP is spread-anchored, not purely game-state-driven

**Claim:** ESPN's WP model blends a pre-game prior (from the
opening spread / team-strength estimate) with in-game state
(margin + time remaining). The prior carries meaningful weight
throughout the game, not just pre-tip. When the score equalizes
during play, ESPN WP tends to mean-revert toward the opening-
line-implied probability rather than toward 50/50.

**Status:** Suggestive qualitative evidence from 4/15 GSW-LAC
Play-In (screenshots in project files). Opening line had GSW
+5.5ish (implied WP ≈ 30%). Two paired observations during the
game:

- 72-74 in the 3rd (~half the game played, competitive score):
  ESPN GSW 29.7%. Close to the opening prior despite meaningful
  game state.
- 114-115 with <3 min left, score tied: ESPN GSW 33.2%. Still
  anchored near the prior, not 50/50.

Also consistent with Phase 3A's Stern-vs-ESPN bilateral-rate gap.
Stern (Brownian bridge) has no prior; ESPN does; Stern produces
higher bilateral-dip rates at every threshold; the ~5-15pp gap is
roughly consistent with a prior-anchoring effect preventing
underdog WP from collapsing as deeply during opponent runs. A
mechanism-level explanation for a gap previously described only
phenomenologically.

**Why it matters:** Three downstream effects on the strategy spec.

1. *Unified explanation for the pilot-vs-3A gap.* Not just "ESPN
   is better at the tails" but specifically "ESPN's prior
   prevents underdog WP from collapsing as deeply on opponent
   runs." Implies Stern-era pilot bilateral rates are
   systematically inflated relative to what ESPN — and likely
   Kalshi, if §1.1 holds — would show. Haircut is
   mechanism-driven, not random noise.

2. *The +3pp calibration residual likely masks
   spread-heterogeneous regimes.* A pre-game favorite sitting at
   10% WP is in a deep-comeback situation where NBA's fat tails
   matter most (late-game fouling, 3-point barrages, one-
   possession scrambles). A pre-game underdog sitting at 10% WP
   is near their prior — no particular reason to expect a
   residual. Pooled across both regimes, the residual averages
   out to +3pp. Split by pre-game spread, it may be +6-8pp for
   favorites and ~0 for underdogs, or some other asymmetric
   pattern. Directly affects Strategy 2's entry rule: "buy any
   team at ≤$0.15" may need to become "buy a pre-game favorite
   at ≤$0.15," which is a much narrower signal.

3. *Strategy 3 exits target the opening line, not 50/50.* A
   5-point dog entered at $0.12 during an opponent run has a
   realistic exit target around $0.30-$0.35 (opening prior),
   not $0.50. Swing size ≈ $0.20, not $0.38. Materially affects
   sizing and which swings are worth capturing. The kill-
   criteria requirement of "median swing capture ≥ $0.10" was
   written before this reframing and may have been implicitly
   assuming swings-to-midline rather than swings-to-prior.

**What retires it:** Three concrete analyses off the existing
ESPN data, no new scraping required. Ideally run as a unit
before Phase 3B interpretation starts.

- *Residual by pre-game spread bucket.* Stratify the Phase 3A
  at-moment calibration residual table by pre-game spread (e.g.
  buckets: favorite by ≥6, favorite by 3-6, pick'em ±3, dog by
  3-6, dog by ≥6). Report the residual profile in each. §1.4
  confirmed if the +3pp concentrates in pre-game favorites at
  low WP; denied if residual is uniform across spread buckets.
- *Score-tied WP regression on opening spread.* At all score-
  tied moments with ≥5 min remaining, regress ESPN WP on
  pre-game spread. Slope quantifies the prior weight directly.
  §1.4 confirmed if slope is meaningfully >0 (e.g. 0.02+ per
  point of spread, which would mean a 5-point favorite shows
  ~10pp of prior weight at score-tied mid-game); denied if
  slope is near zero.
- *Post-dip mean-reversion target.* For all bilateral <0.20
  dip events in the Phase 3A set, measure where WP mean-
  reverts to (the local WP maximum following the dip, before
  the next meaningful score change or game resolution).
  Correlate with pre-game spread. §1.4 confirmed if
  mean-reversion target tracks opening-line-implied prob; denied
  if it tracks toward 0.50 regardless of spread.

**Relates to:** §1.1 (if Kalshi also anchors to spread,
Strategy 2's residual profile transfers cleanly; if Kalshi is
less prior-weighted than ESPN, Strategy 2's edge vs. Kalshi
could be *larger* than the ESPN residual suggests, though §6.5
cuts the other direction). §1.2 (pilot bilateral rates as upper
bounds — mechanism now specified). Strategy 2 kill criteria
(residual may need to be evaluated spread-conditionally).
Strategy 3 exit-target rules.

**Result (2026-04-19) — Direction reversed from hypothesis.**
The thesis hypothesized ESPN was prior-anchored (spread-
weighted). The sportsbook backfill shows the opposite: ESPN
swings *harder* than real-money markets with game state.
Kalshi and sportsbooks are the prior-anchored sources relative
to ESPN. Both compress toward 0.50 (or toward the pre-game
prior) compared to ESPN's more extreme model outputs.

The three §1.4 retirement analyses (residual by spread bucket,
score-tied regression, post-dip mean-reversion target) are
still runnable from existing ESPN data and would quantify
*ESPN's* anchoring behavior, but the strategy-relevant question
(how does Kalshi behave?) is now answered directly by the
sportsbook backfill: real-money markets compress relative to
ESPN, and the compression is large (+10-17pp at the tails).

**Status: partially retired.** The mechanism question (which
source is more prior-anchored?) is answered. The three sub-
analyses remain informative for understanding ESPN's model
specifically but are no longer load-bearing for strategy
decisions. Deprioritized.

---

## 2. Structural risks

### 2.1 Liquidity at extremes is the binding constraint

**Concern:** "Price crossed $0.20" and "you could have bought
meaningful size at $0.20" are different statements. Bilateral math
on $0.15 + $0.15 works beautifully at $100 notional and may not
exist at $10,000 notional if MM resting liquidity at those prices
is thin or asymmetric (the MM may show size on one side while
keeping the other thin precisely when the book is swinging).

**Status:** Phase 1 snapshot probe observed 82k/251k top-of-book
sizes on GSW-PHX ~24h pre-tip, but `liquidity_dollars: 0.0000` at
the same moment — suggesting `liquidity_dollars` measures something
other than naive top-of-book depth (possibly weighted by spread, or
only counting non-MM orders, or computed on a slower cadence). This
discrepancy needs resolution before we use either field as a
decision input.

**User-stated modifier:** Playoff liquidity will be meaningfully
higher than regular season. Fair — but the flip side is that
playoff findings won't extrapolate cleanly *down* to the bulk of
the regular season calendar, where most of any future strategy's
operating time would live. Need separate liquidity characterization
per game-type bucket.

**Why it matters:** This is the single biggest determinant of
whether this is a hobby-scale, career-scale, or uninvestable
endeavor. All three strategies degrade gracefully in the face of
thin liquidity — they just become *uninteresting at meaningful
notional*, which is the same thing as failure for anyone who would
like this project to be economically significant.

**What retires it:** Phase 3 produces, per strategy and per game
bucket (playoff vs regular season; closing-minutes vs mid-game;
top-N-market-cap teams vs bottom-N):

- Observed opportunity rate at target price thresholds (from 1.2).
- Distribution of resting size at price thresholds when
  opportunities occur, measured from full orderbook snapshots.
- Estimated fill quality for a target notional (what fraction of
  opportunities support $500 / $5,000 / $50,000 fills at the
  target price without blowing through levels).
- A notional-capacity number: the $N above which expected
  frequency × fill-adjusted EV stops clearing a pre-specified
  return threshold.

Reconcile `liquidity_dollars` vs orderbook depth empirically
— possibly by watching how the field behaves during active
trading on 4/17+ games.

### 2.2 Adversarial market-maker dynamics

**Concern:** Bilateral convergence is not a secret. Any serious
Kalshi MM has modeled what takers like us would do and priced
accordingly. The counterparty is not passive. If convergence
opportunities are routine, the MM's pricing during late-game swings
likely already incorporates defense against mechanical-edge takers
— for example, by widening spreads at extremes, pulling quotes
when volatility spikes, or setting floor prices above where a naive
model would quote.

You and the MM are, in a sense, both trading volatility — just from
different sides of the same table. The MM presumably makes money by
capturing spread and skewing quotes in its favor; you'd be trying to
front-run the oscillations it's pricing. The MM's edge is faster
data and a full population of takers to cross-subsidize from. Yours
would be... what, exactly? Worth having a clean answer before Phase
3, because "mechanical edge, no counterparty assumption needed"
isn't it.

**Status:** Unaddressed in thesis. Not refuted either — the CHA-MIA
observation you shared is real evidence that sub-$0.10 bilateral
fills were available, which means either (a) the MM doesn't fully
defend or (b) the MM does defend but occasional genuine mispricings
still slip through, especially during extreme volatility where the
MM itself may be widening out of risk.

**What retires it:** Qualitative analysis during Phase 3:
characterize MM behavior around extreme-WP events in logged data.
Do quotes widen or disappear? Do resting sizes shrink? Is there a
pattern where opportunities cluster during specific game states
(post-timeout, free-throw sequences, reviews) where the MM may be
updating more slowly? The answer shapes execution design — e.g., if
the MM pulls quotes during live play and restocks during stoppages,
stoppages are the entry window.

Write down the MM's assumed behavior model in one paragraph as
part of the Phase 3 spec. If we can't articulate what the MM is
doing and why we're allowed to extract value, the spec isn't done.

### 2.3 MM calibration improves over time

**Concern:** Kalshi NBA markets are relatively new. The MM's
pricing engine will accumulate data and improve with every season.
Strategies that backtest well on 2024-25 data may degrade on
2026-27 data not because the thesis was wrong but because the
counterparty got sharper. This is the standard decay clock in
prediction markets and algorithmic trading — edges in a new market
are strongest early and erode as participants calibrate.

**Status:** Unaddressed in thesis. Uniquely important here because
the project's forward-dated nature means we're validating on data
captured going forward, not on a static archive.

**What retires it:** This one doesn't fully retire — it becomes a
first-class monitoring metric if Phase 4 ever goes live. Track
rolling opportunity frequency and fill-adjusted EV over time. A
strategy that produces positive EV in month 1 and zero by month
12 is the expected shape, not a surprise. Build the monitoring
before any capital is deployed.

Also informs Phase 3 sampling: use the *most recent* logged data
as the held-out validation set, not a random split. A strategy
that worked on early Phase 1 data but not on later Phase 1 data
is already telling us something.

### 2.4 Playoff ≠ regular season generalization

**Concern:** Phase 1 capture begins during 2026 playoffs. Playoff
games differ from regular season games in ways that matter for this
thesis:
- Liquidity per market is higher (user-stated, plausible).
- Games are more competitive on average (selection: playoff teams).
- Stakes, fatigue patterns, rotation depth, foul-call tightness,
  and late-game coaching aggressiveness all differ from regular
  season baselines — any of which could shift the shape of
  within-game volatility, which is the asset being traded.
- Media coverage is denser, so the consensus WP model (ESPN) may
  itself be better-calibrated for playoff games than regular
  season ones.

**Status:** Unaddressed. Only flagged now because Phase 1 will
produce playoff data first and it would be easy to over-generalize.

**What retires it:** Plan a regular-season data capture window
explicitly (2026-27 season opener → present). Phase 3 stratifies
all analysis by playoff vs regular season. Do not pool them in
headline metrics.

### 2.5 Realized bid-ask spread at target entry prices

**Concern:** The `FEES.md` envelope (2026-04-17) showed that Kalshi
fees are manageable (2-6% of gross on Strategies 1 and 2;
fee-sensitive on Strategy 3 small swings but resolved by maker
execution). Doing that analysis surfaced that **bid-ask spread is
likely a larger drag than fees** at typical entry prices. On
KXNBAGAME the tick is $0.01. A one-tick spread on a 100-contract
round trip is $1 per leg — comparable to or larger than the fee
itself, and paid on *every* entry regardless of strategy.

The rough rule of thumb in `FEES.md` — budget one full tick of
spread per leg on top of fees — is a placeholder based on zero
observations. Realized spreads during live NBA games may be wider
during swings (when we'd want to trade) and tighter during quiet
stretches (when we wouldn't). This is the exact wrong direction
for the thesis: execution costs concentrate precisely at the moments
the strategies want to act.

**Status:** No data. Phase 1 logging captures full orderbook depth
which lets us compute this, but nothing has been analyzed yet.

**Why it matters:** Affects all three strategies but bites Strategy
3 hardest (round-trip pays spread twice). For Strategy 1, spread
on each leg directly narrows the combined-cost window before fees
flip the trade negative. For Strategy 2, half-spread on entry is
a hidden drag on break-even win rate.

**What retires it:** Phase 3 analysis output — realized spread
distribution at target entry prices, stratified by:

- Game state (pre-tip / 1st-3rd quarters / 4th quarter / OT /
  post-resolution-imminent)
- WP bucket (extreme low $0.05-0.15 / low $0.15-0.30 / mid
  $0.30-0.70 / high/extreme-high mirror)
- Market condition (quiet vs post-scoring-run, post-timeout vs
  live action)
- Playoff vs regular season

Report median, p75, p95 spread at each bucket. Integrate into
per-strategy EV calculations: Strategy 1 and 2 pay half-spread
per entry; Strategy 3 pays full spread per round trip (or zero
if executed maker-maker, though maker execution has its own
fill-rate question).

This is a Phase 3 deliverable; Phase 2 ESPN ingest doesn't
touch it.

### 2.6 Sizing and market impact at target order sizes

**Claim:** 100-contract orders at Strategy 3 entry prices
($0.35-$0.45) are small enough to be invisible in the flow
and will not trigger MM defensive behavior.

**Status: Confirmed.** Kalshi historical trades probe on
HOU-LAL (93,838 trades, 29.2M contracts) showed:
- 100 contracts = 66th percentile of trade sizes
- 0.02% of median in-game 5-min bucket volume (574k)
- Strategy 3 zone ($0.35-$0.55) carries 40.8% of volume
- Even 1,000-contract orders (top 5.7%) would be absorbed

**Retired 2026-04-20.** No further investigation needed at
100-contract sizing. Re-evaluate if scaling to 2,000+
contracts per order.

---

## 3. Process & hygiene items

### 3.1 Kill criteria aren't written down

**Concern:** `THESIS.md` says the project "fails responsibly if
Phase 3 shows all three strategies are unexploitable in practice,"
but defines no numeric threshold for that verdict. This risks
drift-through-refinement later — "it's close, let me just try one
more filter" — which is how research projects quietly fail to stop.

**What retires it:** Write concrete graduation and kill criteria
per strategy *now*, while we're not attached to any specific
outcome. Example skeleton (numbers TBD after a fees envelope exists
per 3.3):

- **Bilateral convergence graduates** if, on held-out Kalshi data,
  post-liquidity-adjusted bilateral <$0.80 combined-cost opportunity
  rate ≥ 15% of competitive games AND median fill-adjusted EV per
  opportunity ≥ $X per $100 notional.
- **Bilateral convergence killed** if either condition fails by
  a wide margin across playoff and regular season, or if fill
  analysis shows the strategy cannot absorb > $500 per
  opportunity before EV turns negative.
- *(Repeat for strategies 2 and 3.)*

These numbers should go in `THESIS.md` itself once drafted, not
just here.

### 3.2 Strategies 1, 2, 3 aren't fully orthogonal

**Observation:** Bilateral convergence (strategy 1) is a special
case of active management (strategy 3) where you happen to hold
both legs to resolution rather than sell the first one on
swing-back. The three-strategy framing is useful for separating
*edge mechanisms* (mechanical arithmetic / model residual /
volatility monetization), but the *research work* collapses — you
log the same data, run the same bucketed analyses, need the same
fill-quality modeling.

**Status:** Not a concern, just a note for work-planning.

**What retires it:** Phase 3 work plan explicitly treats the
analyses as shared infrastructure with strategy-specific decision
layers on top. Avoid triple-counting effort.

### 3.3 Fees and slippage aren't Phase 3 concerns

**Concern:** `THESIS.md` implicitly treats fees and slippage as
Phase 3 questions. They're not. Kalshi fees on $0.15-in / $1.00-out
single-side bets could be a material chunk of gross EV depending
on the fee schedule. The bid-ask spread at penny levels costs real
money per round trip, especially for active management (strategy
3, which round-trips positions).

**What retires it:** Pull Kalshi's current fee schedule and
document in `THESIS.md` (or a short `FEES.md` companion). Back-of-
envelope EV after fees and one tick of slippage per leg, applied to
the pilot's opportunity frequency numbers. If the envelope shows
the strategies are negative-EV after costs at plausible
opportunity sizes, that's information to have before Phase 3, not
after.

This is a ≤1-day task and should probably happen before the next
Phase 1 dispatch.

**Resolved 2026-04-17.** Kalshi fee schedule pulled and envelope
analysis completed in `FEES.md`. Finding: fees do not disqualify
any strategy at plausible notionals. Strategies 1 and 2 are
fee-insensitive (2-6% of gross). Strategy 3 is fee-sensitive on
small swings under taker-taker execution; maker-maker execution
(available on KXNBAGAME) resolves this. See `FEES.md` for detail.

### 3.4 Distinguish "opportunity existed" from "opportunity was tradeable"

**Concern:** Running through the doc, I notice the thesis mostly
uses "opportunity" in the sense of "price crossed a threshold." In
practice an opportunity requires: price crosses threshold + size
available at that price + the snapshot window catches it + execution
latency doesn't miss the fill window. The ratio of nominal
opportunities to actually-tradeable opportunities may be much less
than 1.

**What retires it:** Phase 3 reports both counts and the ratio
between them, per strategy. The ratio is itself a headline number
— if it's 0.9, great; if it's 0.2, the addressable market is
meaningfully smaller than the nominal frequency suggests.

---

## 4. Items the thesis gets right and should not drift on

Preserving these explicitly so future pressure to "simplify" doesn't
erode them:

- **Framing as volatility trading, not prediction.** This is the
  core intellectual move and it's correct. Resist reframings that
  smuggle prediction back in — e.g., "let's build a slightly
  better WP model to find mispricings" is the old failed frame
  dressed up.
- **Research-before-infrastructure.** The phase-gate structure is
  doing real work. Each phase has a concrete output that feeds
  the next phase's scope.
- **Honest failure-mode commitment.** The thesis' willingness to
  kill the project if Phase 3 fails is rare and worth defending.
- **Separation from NBAgent.** The two-repo split keeps the
  long-lived data-capture workflow from entangling with the
  retrospective analysis codebase. Do not merge them for
  "convenience" without a real architectural reason.

---

## 5. Motivating observations to preserve

Generative examples that led to the thesis. Worth keeping on file
so the project remembers what it's trying to capture:

- **4/14 CHA-MIA Play-In (user-observed live).** YES contracts on
  both teams available sub-$0.10 at multiple points in the second
  half. Game went to OT, CHA won 127-126. ESPN WP chart shows MIA
  peaked ~85% in the 4th quarter and still lost. This is the
  canonical bilateral-convergence example and the generative
  datum for the project.
- **4/15 GSW-LAC Play-In (Kalshi vs ESPN paired observations).**
  Two points in the game (72-74 and 114-115) where Kalshi and ESPN
  WPs agreed to within ~1pp. Thin evidence but directionally
  important — the claim it supports is §1.1 above.
- **2024-25 regular season pilot.** Stern-model bilateral <$0.20
  rate = 30% across competitive games. Upper-bound proxy for the
  Kalshi-price rate, per §1.2. Meaningful if Kalshi ≈ Stern tracks,
  less meaningful if it doesn't.

---

## 6. Pre-data hypotheses (written 2026-04-17, before Phase 3A)

Directional predictions about what Phase 3A analysis will show.
Recorded pre-data to prevent post-hoc rationalization. Each
hypothesis has a concrete confirmation/denial criterion tied to
Phase 3A output. Retire by appending a dated result line — do
not delete the original prediction.

### 6.1 ESPN calibration residual: smaller than Stern, still positive

**Prediction:** The +9pp residual at the tails (teams priced ≤10%
WP actually win ~20%) will shrink to +4-6pp when measured against
ESPN's own WP model instead of Stern. ESPN's model is better than
Stern at the extremes because it has play-type awareness and
game-state features, but it still underweights the true comeback
rate because modern NBA teams are *coached* to maximize variance
when trailing late (intentional fouling, 3-point shooting
strategies). This is a structural game feature that any
time-and-margin model will underestimate.

**Implication:** Strategy 2 survives but with thinner margins than
the pilot suggested. Still positive-EV after fees (per `FEES.md`,
fees shift break-even by <1pp), but less robust to noise.

**Confirmed if:** Residual is +3pp to +7pp across tail buckets
(WP ≤ 0.15) in Phase 3A Part 2 output.

**Denied if:** Residual is <+2pp (ESPN is well-calibrated at
extremes — the +9pp was a Stern artifact and Strategy 2's edge
against ESPN-style pricing evaporates) OR >+8pp (ESPN is worse
than Stern at extremes, which would be surprising and worth
investigating).

**Relates to:** §1.1, §1.2, Strategy 2 kill criteria.

### 6.2 Temporal clustering is the bilateral bottleneck

**Prediction:** ~15-20% of bilateral opportunities (both sides
below $0.20) have sub-3-minute separation between the two dips,
making them operationally untradeable for manual execution. The
pilot's 23-minute median separation is real, but the left tail
of the separation distribution matters more than the median for
determining the *actionable* bilateral rate.

**Implication:** The effective bilateral opportunity rate is
~80-85% of the nominal rate. If ESPN-based bilateral <$0.20 rate
is 25% of competitive games, the tradeable rate is ~20-21%.
Still well above the kill criterion (12%), but a meaningful
haircut.

**Confirmed if:** Phase 3A Part 1 separation analysis shows
15-25% of bilateral <$0.20 games have separation < 3 minutes.

**Denied if:** Separation is nearly always large (>95% have ≥5
min) — the two dips typically happen in different quarters, not
the same late-game sequence. This would be the good outcome.

**Relates to:** Strategy 1 kill criteria (criterion 1 requires
≥3 min separation).

**Result (2026-04-17) — Strongly denied in the good direction.**
Phase 3A measured 1.4% of bilateral <0.20 games at |spread|≤6 with
<3 min separation (prediction was 15–20%). Median separation 18.0
min of game clock; 97.3% ≥5 min. Temporal clustering is not the
bilateral bottleneck. Strategy 1's graduation criterion 1 is
comfortably satisfied on the separation dimension.

### 6.3 Home/away dip asymmetry: away dips are more common

**Prediction:** The away team's WP dips below $0.20 roughly 40%
more often than the home team's WP does, because road teams
trail more frequently and more deeply. However, bilateral rates
benefit only ~10% from this asymmetry because the home-side dip
is the bottleneck — home teams in competitive games rarely fall
to extreme lows except during genuine upset-in-progress
scenarios.

**Implication:** Game selection should slightly favor games where
the home team is a small underdog (spread +1 to +3) — these are
the games most likely to produce home-side dips, unlocking the
bilateral opportunity.

**Confirmed if:** Phase 3A Part 4 shows away-side single dip
rate is 30-50% higher than home-side; bilateral rate is only
5-15% higher than a symmetric model would predict.

**Denied if:** Dip rates are roughly symmetric. This would mean
home-court advantage doesn't meaningfully affect within-game WP
volatility at the extremes, which would be surprising.

**Result (2026-04-17) — Denied on the rate dimension; partially
supported on depth.** Phase 3A measured away dip rate 7–10%
higher than home (not ~40%). Crossing rates are close to
symmetric. However, dip *depth* is meaningfully asymmetric:
median min WP home 0.115 vs away 0.081. The home-underdog
game-selection implication the hypothesis gestured at deserves
revisiting with dip depth (not crossing rate) as the dimension of
interest — fold into the §1.4 retirement analyses rather than
maintaining a standalone follow-up. For Strategy 1 the finding is
neutral; for Strategy 2 the depth asymmetry is potentially
material (away-side extreme lows sit further into the residual
band than home-side ones).

### 6.4 Pace dominates talent for swing propensity

**Prediction:** Team-level bilateral dip rate correlates more
strongly with pace (possessions per 48 minutes) than with team
quality or record. High-pace teams (2025-26 examples: IND, ATL,
SAC-type profiles) create more possessions, more scoring events,
and more WP oscillation. Defensive slow-pace teams (CLE, NYK-
type profiles) produce smoother WP curves with fewer extreme
dips.

**Implication:** For game selection in Phase 4, "pace of both
teams" is a better filter than "quality of both teams." A
competitive game between two fast teams is worth monitoring over
a competitive game between two slow teams at the same spread.

**Confirmed if:** Phase 3A Part 3 top-5 swing-propensity teams
are disproportionately high-pace; bottom-5 are low-pace. A quick
correlation of bilateral rate vs regular-season pace (available
from NBA.com) confirms the relationship.

**Denied if:** The ranking is driven by something else — e.g.,
3-point attempt rate, bench depth, or late-game coaching
tendencies. Any of these would be interesting alternative
predictors.

**Result (2026-04-17) — Denied.** Phase 3A follow-up
(`docs/analysis_outputs/3a_followup_2026_04_17.md`) measured
Spearman ρ = +0.063 (p = 0.75) and Pearson r = +0.080 (p = 0.68)
across 29 teams (OKC excluded at n=8). Correlation is effectively
zero, and it survives including OKC (n=30: ρ = +0.071). The
Top-5 / Bottom-5 pattern observed in Phase 3A was noise. MIA
ranks #1 in pace and #18 in involvement; HOU ranks #29 in pace
and #5 in involvement; the ranked table contains no monotonic
signal. Retires the implied "favor high-pace matchups" game-
selection heuristic with no replacement heuristic falling out of
this data. Worth noting the Bottom-5 involvement rankings
(TOR/NYK/SAC/DET/BKN) skew toward lower-quality teams playing
games that don't flip — possibly a team-quality-variance signal
rather than pace — but the data here neither supports nor refutes
that hypothesis and it's not worth chasing absent a specific
reason to.

### 6.5 MM defense is weaker at extreme-low prices

**Prediction:** Kalshi's market maker defends less aggressively
at $0.05-$0.10 than at $0.20-$0.30. At extreme-low prices, the
MM faces high gamma risk (a single scoring run can move the
price $0.20 in seconds, blowing out any spread the MM was
capturing), making it economically unattractive to quote
tightly. If true, extreme-low-price opportunities are more
genuine and more exploitable than moderate-low-price ones.

**Implication:** Tighter entry thresholds ($0.10 rather than
$0.20) may paradoxically be *more* exploitable. The kill
criteria's ≤$0.20 entry threshold may be too generous — the
real action is at ≤$0.10.

**Cannot be tested in Phase 3A** — requires Kalshi orderbook
data from Phase 1. Test in Phase 3B by examining: at moments
when ESPN WP ≤ 0.10, is Kalshi's top-of-book resting size
thinner than at ESPN WP ≈ 0.20-0.30? If yes, the MM is pulling
back at extremes.

**Relates to:** §2.1 (liquidity), §2.2 (adversarial MM dynamics).

### 6.6 Betting flow creates exploitable non-game-state price moves

**Prediction:** Kalshi prices sometimes move between plays (when
the game state is static) due to order flow — a large order on
one side shifts the price even though nothing happened on the
court. This is noise from the thesis's perspective but creates
additional volatility. It's good for Strategy 3 (more swings to
trade) but complicates the ESPN-as-Kalshi-proxy assumption
(prices diverge from the WP model during flow-driven moves).

**Cannot be tested in Phase 3A** — requires paired Kalshi +
ESPN data at play-level resolution. Test in Phase 3B by looking
for Kalshi price changes during dead-ball periods where ESPN WP
is unchanged.

**Relates to:** §1.1 (Kalshi ≈ ESPN claim — flow-driven moves
are a source of Kalshi-ESPN divergence that isn't model error).

### 6.7 Sequential-opportunistic bilateral construction outperforms threshold scanning

**Prediction:** A modified bilateral strategy — buy one side
cheap when it dips, then actively seek the other side's dip
later — has a higher completion rate than the strict "both sides
below threshold in the same game" criterion. The difference is
entry logic: instead of scanning for games where both sides have
already dipped, you enter the first leg opportunistically and
then wait for the second. This increases the window for the
second leg (you don't need both to happen near-simultaneously)
and converts some single-dip games into bilateral opportunities.

**Implication:** The addressable opportunity rate may be higher
than the bilateral dip rate suggests, because you're
constructing bilateral positions across the game's natural
rhythm rather than waiting for a specific threshold pattern.

**Testable in Phase 3A** by modifying the bilateral analysis:
instead of "did both sides dip below X in this game?" ask "if
side A dipped below X, did side B subsequently dip below Y
(where Y can be higher than X because leg 1 is already
secured)?" For example: if away dips below $0.15, does home
subsequently dip below $0.25? Combined cost $0.40, guaranteed
$0.60 profit. This has lower per-trade profit but potentially
much higher frequency.

**Relates to:** §3.2 (strategies aren't fully orthogonal —
this is the bridge between Strategy 1 and Strategy 3).

**Result (2026-04-17) — Confirmed, and operationally larger than
the original framing.** Phase 3A follow-up
(`docs/analysis_outputs/3a_followup_2026_04_17.md`) tested three
bilateral definitions across a 10-pair threshold grid:

- *Strict symmetric* — both sides dip below X. Baseline.
- *Sequential operational* — side A dips below X at t1, side B
  dips below Y at t2 > t1. The definition this hypothesis
  originally proposed.
- *Asymmetric any-order* — both sides dip (one below X, one
  below Y) with no ordering constraint.

At |spread|≤6, (0.20, 0.30): strict 26.6%, sequential 34.2%,
asymmetric any-order 49.0%. At (0.15, 0.30): strict 17.1%,
sequential 24.4%, asymmetric any-order 47.5%. Aggregate EV per
competitive game (opportunity rate × taker-taker net per
trade) is ~60% higher for relaxed thresholds in the (0.15, 0.30)
/ (0.20, 0.30) neighborhood vs strict (0.20, 0.20).

**Methodology note, material for the eventual strategy spec.**
The hypothesis's "sequential" framing — requiring the tighter-X
leg to come first — is unnecessarily restrictive. A well-designed
policy ("enter whichever side dips below Y first, then enter the
other side if it dips below X, with appropriate hold-for-better
logic") captures close to the asymmetric any-order rate, not the
sequential rate. The operationally relevant addressable universe
is ~50% larger than the strict-bilateral frame suggested. The
~60% aggregate-EV estimate is pre-Phase-3B — liquidity and
spread haircuts still to apply — but the *ratio* between relaxed
and strict is relatively insensitive to those haircuts since
they scale both variants similarly.

Implication: Strategy 1's graduation is substantially less
suspect than the 3A strict-bilateral read suggested. Under the
operational definition at (0.20, 0.30) on |spread|≤6 games,
Phase 3B would need to deliver a ~75% liquidity haircut (from
49.0% nominal to <12% effective) to push Strategy 1 below the
graduation bar — a very high bar.

---

## Resolution log

Append dated entries as items are retired or new ones emerge. Do
not delete resolved items — strike through or mark resolved inline.

**2026-04-17 — §3.3 retired.** Kalshi fee schedule obtained and
envelope analysis completed in `FEES.md`. Fees do not disqualify
any strategy at plausible notionals. See §3.3 for inline resolution
note.

**2026-04-17 — §2.5 added.** Fees analysis surfaced bid-ask spread
as the likely dominant non-fee execution cost. New open item: Phase
3 must characterize realized spread distribution at target entry
prices from logged orderbook data.

**2026-04-17 — §1.4 added.** New load-bearing claim that ESPN WP
is spread-anchored (prior-weighted) rather than purely
game-state-driven. Motivated by qualitative observation from 4/15
GSW-LAC Play-In (GSW pinned near opening-line-implied 30% at
halftime AND at score-tied <3 min, no mean-reversion to 50/50) and
consistent with the Stern-vs-ESPN pilot-to-3A bilateral-rate gap.
Three retirement analyses listed; all runnable from existing ESPN
data before Phase 3B. Strategy 2 entry rule and Strategy 3 exit
rule may depend on the outcome.

**2026-04-17 — §6.1 retired (partially confirmed).** ESPN
calibration residual measured +2.6 to +3.3pp in the 7.5–20% WP
band — low end of the predicted +3 to +7pp range. Strategy 2 edge
against ESPN survives but thinner than predicted. Kalshi residual
still pending Phase 3B. See inline result line on §6.1.

**2026-04-17 — §6.2 retired (denied, good direction).** Only
1.4% of bilateral <0.20 games had <3 min separation (prediction:
15–20%). Temporal clustering is not the bilateral bottleneck.
See inline result line on §6.2.

**2026-04-17 — §6.3 retired (denied on rate, partially supported
on depth).** Away dip rate only 7–10% higher than home (not ~40%),
but dip depth asymmetric (median min WP home 0.115 vs away 0.081).
Depth-based game-selection implication folds into §1.4 analyses.
See inline result line on §6.3.

**2026-04-17 — §6.4 retired (denied).** Team pace vs bilateral
involvement Spearman ρ = +0.063 (p = 0.75). No correlation. The
3A Top-5 / Bottom-5 pattern was noise. Retires the implied
"favor high-pace matchups" heuristic with no replacement. See
inline result line on §6.4.

**2026-04-17 — §6.7 retired (confirmed, reframed larger).**
Sequential-opportunistic bilateral raises |spread|≤6 rate from
26.6% strict to 34.2% sequential to 49.0% asymmetric-any-order at
(0.20, 0.30). Aggregate EV per competitive game ~60% higher for
relaxed thresholds. Methodology note: asymmetric-any-order is
closer to the true operational rate than sequential. Strategy 1's
graduation is substantially less suspect. See inline result line
on §6.7.

**2026-04-19 — Strategy 2 preliminary kill signal.** The
+3pp ESPN-vs-actual residual at the tails (Phase 3A) does not
transfer to Kalshi/sportsbook pricing. Sportsbooks price
those same moments at +10-17pp above ESPN — well above the
~13% actual win rate. The relevant residual for Strategy 2
(actual_win_rate − Kalshi_mid) is negative at every
plausible calibration point. Formal kill pending Phase 3B
confirmation with ≥10 games of Kalshi-vs-actual resolution
data at the tails, but the direction is unambiguous.

**2026-04-19 — Strategy 3 favorite-side variant killed.**
FanDuel timeseries (n=15) showed pooled blended net of
−$18.40 per position. Resolution backstop fires into losses
~84% of the time at market prices. ESPN-based analysis was
misleading — the 15.8% resolution win rate reflects selection
bias (favorites that can't recover to 0.60 WP are
disproportionately losing). No further investigation.

**2026-04-20 — §2.6 added and immediately retired.** Kalshi
trades probe confirmed 100-contract orders are invisible in
HOU-LAL trade flow. Sizing is not a constraint.

**2026-04-21 — Phase 3B formal complete; open items resolved or
reframed.** The 168-game paired-analysis arc (168 games, 165
competitive) completed. Consolidated resolutions:

- **§1.1 Kalshi ≈ ESPN-style WP model** — fully resolved.
  Compression calibrated by WP zone on 46,981 in-game bins:
  Kalshi = ESPN + Δ where Δ = +4.6pp (0.0-0.2), +8.3pp
  (0.2-0.4), +4.1pp (0.4-0.6), −1.8pp (0.6-0.8), −2.7pp
  (0.8-1.0). Convergence slope −0.000020/s pooled, all
  p ≈ 0.
- **§1.2 Pilot bilateral-dip frequencies as upper bounds** —
  resolved. S1 bilateral calibrated at real Kalshi rates:
  +$1,608/yr on ~84 bilateral opportunities per regular
  season. Upper-bound haircut confirmed; the residual rate
  is sufficient for deployment.
- **§1.3 Mechanical edge framing** — resolved. S1 bilateral
  graduation on held-out data confirms the arithmetic edge
  holds at realistic fill rates.
- **§1.4 ESPN spread-anchoring** — fully retired. Direction
  was confirmed reversed (ESPN swings harder than Kalshi);
  the three retirement analyses are no longer load-bearing
  because the compression question is directly answered by
  §1.1's quantified zone calibration.
- **§2.2 Adversarial MM dynamics** — addressed. Trades probe
  and spread analysis show $0.01 spread floor held across
  all game states, depth is 2.3× during timeouts, no MM
  defensive widening observed at swing moments. Not a barrier
  to deployment.
- **§2.5 Realized bid-ask spread at target prices** —
  resolved. Median spread $0.01 at all mid-range entry
  prices on 165-game sample. Fee + spread envelope does not
  disqualify any strategy.
- **§6.5 MM defense at extreme-low prices** — resolved in
  the negative direction. Failed-entry analysis showed 39%
  of ≤$0.40 entries go to terminal decline; the MM is NOT
  pulling back at extremes, those dips carry genuine
  information 40% of the time. This is why S3 requires
  selective-entry filters to be positive-EV.
- **§6.6 Flow-driven non-game-state price moves** — partially
  resolved. 168-game paired dataset shows delta (Kalshi −
  ESPN) of 5.4pp in timeout windows vs 5.5pp outside,
  Mann-Whitney p = 8.5e-08. Small but definitive signal that
  timeouts are convergence micro-events; flow and game-state
  moves are distinguishable at scale.
- **§3.1 Kill criteria written** — fully resolved in
  `docs/KILL_CRITERIA_draft.md` with per-strategy graduate/kill
  conditions for S1, S2 (killed), S3 (naive killed, filtered
  validated), and S4 (graduated).

Outstanding open items after this pass: §2.1 (liquidity at
extremes remains partially open — fill-quality at 1k+ contract
sizes still untested), §2.3 (MM calibration decay over time,
by design a live-monitoring item not a Phase 3 item), §2.4
(playoff vs regular season — playoff games remain
under-represented; current 168-game dataset is regular-season
only), §3.4 (opportunity-existed vs tradeable — first-order
validated via the 30s-bin granularity, but sub-second fill
reality is a Phase 4a question).
