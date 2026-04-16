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

Last updated: 2026-04-17.

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
