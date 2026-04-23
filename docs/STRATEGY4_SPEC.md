# Strategy 4 Spec — Dip-Recovery Swing Trading on Kalshi NBA Contracts

Living document. Consolidates all Strategy 4 findings into a
single actionable reference. Companion to `STRATEGY3_SPEC.md`.

**Evidence tiers:**
- **Kalshi-confirmed** — validated on real Kalshi paired data.
  Core dataset: 171 games (|spread| ≤ 6). Expanded dataset:
  404 games (all spreads). 30-second VWAP bins from historical
  trade tape paired with ESPN WP.
- **Holdout-consistent** — S4A has no fitted parameters
  (single hypothesized config), but train/test consistency
  confirmed: train +$3.19, test +$4.24 mean P&L (seed=42
  110/55 split).
- **Tested-and-rejected** — analyzed and found not to improve
  the strategy.

Last updated: 2026-04-22 (stop execution study incorporated).

---

## 1. Strategy thesis

Buy the pre-game favorite's YES contract during temporary
underdog runs, while the market still prices the favorite to
win ($0.50–$0.75 zone). Exit when the favorite reasserts
($0.90), explicitly before game resolution. Avoids late-game
collapse risk by never holding to the final whistle.

Distinct from Strategy 3: S3 enters at $0.40 (market losing
faith), S4 enters at $0.50–$0.75 (market still believes but
temporarily disrupted). S4 rides the favorite's natural buoy;
S3 bets against a potential collapse.

---

## 2. Operating parameters (Strategy 4A — Favorite side)

| Parameter | Value | Evidence |
|-----------|-------|----------|
| Entry trigger | Dip of ≥ $0.08 from 180-second trailing max | Kalshi-confirmed, best of 1,200-config sweep |
| Entry zone | $0.50–$0.75 (fav Kalshi VWAP) | Kalshi-confirmed |
| Exit target | $0.90 | Kalshi-confirmed, optimal per false-summit analysis |
| Stop-loss | $0.40 | Kalshi-confirmed, most sensitive parameter |
| Contract sizing | 100 contracts per position | Single tranche, no averaging |
| Position management | None (baseline optimal) | Tested-and-rejected: 17 avg-in/out configs all underperform |
| Re-entry | Allowed once per game after exit | 25.5% of entries are re-entries |
| Hold time | ~38 minutes median | Kalshi-confirmed |
| Competitive game filter | Uncapped (all spreads) | All 7 spread buckets positive EV on 404-game Kalshi dataset. See §7. |

### Fee assumptions (per `docs/FEES.md`)

| Execution | At $0.65 entry, 100 contracts |
|-----------|-------------------------------|
| Maker per leg | `ceil(0.0175 × 100 × 0.65 × 0.35)` = $0.40 |
| Maker round-trip | ~$0.80 |
| Taker per leg | `ceil(0.07 × 100 × 0.65 × 0.35)` = $1.60 |

Maker execution strongly preferred. Fee drag is minimal at
S4A's operating prices.

---

## 3. Entry rule

**Enter when the favorite's YES bid price has dropped ≥ $0.08
from its trailing 180-second maximum, and the current price
is in the $0.50–$0.75 range.**

The signal is purely price-based. No model dependency, no
external data feed beyond the Kalshi orderbook.

### What the trigger captures

The 180-second lookback and $0.08 dip threshold identify
temporary disruptions caused by underdog scoring runs. The
$0.50–$0.75 entry zone ensures the market still prices the
favorite as more likely than not to win — you're buying a
disruption, not a collapse.

### Sensitivity (from Part 2C)

| Parameter | Tested range | EV range | Sensitivity |
|-----------|-------------|----------|-------------|
| Lookback | 120–300s | $1,490–$1,886 | Low — all positive |
| Dip depth | $0.05–$0.20 | −$73 to +$1,886 | Moderate — $0.15+ is negative |
| Entry zone | Various bands | $852–$1,886 | Low — wide band ($0.50–$0.75) is best |
| Exit target | $0.80–$0.95 | $858–$1,886 | Moderate — $0.90 is optimal |
| Stop-loss | $0.40–$0.50 | $465–$1,886 | High — $0.40 is critical |

The $0.40 stop-loss is the most sensitive parameter. Moving
it to $0.45 cuts annual EV nearly in half. The wide entry
zone and flexible lookback suggest the signal captures a
robust pattern, not a fragile parameter fit.

---

## 4. Exit rule

**Exit when the favorite's YES bid price reaches $0.90.**

### False-summit analysis (from Part 1)

| Price level | Games reaching | Fav loss rate | Weighted loss rate |
|-------------|---------------|--------------|-------------------|
| $0.85 | 112 | 10.7% | 3.7% |
| $0.88 | 110 | 9.1% | 1.8% |
| $0.90 | 108 | 7.4% | 0.9% |
| $0.92 | 105 | 4.8% | 0.3% |
| $0.95 | 101 | 1.0% | 0.1% |

$0.90 sits at the knee of the curve — captures most of the
recovery while exiting before the rare-but-real reversals.
Waiting for $0.95 reduces annual EV ($1,256 vs $1,886)
because too many recoveries stall in the $0.90–$0.94 range.

### Stop-loss

**Exit at market if favorite price drops to $0.40.**

This is the "market has genuinely lost faith" threshold. Below
$0.40, the favorite is in S3 territory — a fundamentally
different and riskier regime.

### Stop-loss execution reality (from stop execution study)

Kalshi has no native stop-loss order type. The recommended
execution model for stops is a **resting NO buy at $0.60**
(economically equivalent to selling YES at $0.40), placed at
entry time for maximum queue priority.

**Gap-through risk (132 stop events, 404-game dataset):**

| Category | Definition | % of stops |
|----------|-----------|-----------|
| Clean cross | stop VWAP $0.38–$0.42 | 50.0% |
| Moderate gap | stop VWAP $0.34–$0.38 | 32.6% |
| Severe gap | stop VWAP < $0.34 | 17.4% |

73.5% of stops are flash crashes (price was above $0.45
just 60 seconds before the stop fires). Median dwell time
at the $0.38–$0.42 band is 0 bins — the price typically
blows through $0.40 rather than lingering.

**EV under execution scenarios (deltas are load-bearing):**

| Scenario | Annual EV | Δ vs baseline |
|----------|-----------|--------------|
| A — Baseline (stops at $0.40, maker) | +$1,410 | — |
| B — Maker NO-side resting + taker fallback | +$1,460 | +$49 |
| C — Taker stop at observed VWAP (worst case) | +$977 | −$433 |
| D — Hybrid (resting + 60s cancel fallback) | +$1,131 | −$279 |

**Break-even stop price: $0.312.** If average realized stop
price is worse than this, S4A is unprofitable. This provides
~$0.09 of margin below the $0.40 target — even with
gap-throughs, the strategy remains positive.

Note: absolute EVs here use pool-level annualization and
differ from §9's per-bucket-summed rollup. The deltas
between scenarios are the meaningful comparison.

**Recommended execution model: Scenario B.**
- At entry: place 100-contract resting NO buy at $0.60.
- If price gaps to ≤ $0.34 and resting order unfilled:
  cancel immediately, taker-sell YES at market.
- Consider $0.61–$0.62 NO ($0.38–$0.39 YES) for higher
  fill probability at small deterministic cost. Test in
  Phase 4b.

**Source:** `docs/analysis_outputs/strategy4_stop_execution.md`

### No resolution exposure

S4A explicitly does not hold to game end. Every position
exits via target ($0.90) or stop ($0.40). The Part 6 analysis
confirmed that the outcome distribution is bimodal — entries
either reach $0.90 (53%) or stop at $0.40 (47%) with almost
nothing in between. Partial-exit and hold-to-resolution
variants all underperform.

---

## 5. Position management: RESOLVED (baseline optimal)

Tested 17 configurations across averaging-in (6 configs),
averaging-out (7 configs), and combined (4 configs). All
underperform the simple 100-contract baseline.

**Why averaging-in fails:** Add-on fires 60–77% of the time
(price usually continues dropping after initial entry), but
the $0.40 stop means more contracts at risk on stops. Extra
loss exposure on the 47% that stop out outweighs the improved
basis on the 53% that hit. Best avg-in: $1,143/yr vs $1,886
baseline.

**Why averaging-out fails:** The P&L distribution is bimodal
(big win at $0.90 or big loss at $0.40, no middle ground).
Selling part of the position at $0.80 reduces winner size
without meaningfully converting stop-outs. Best avg-out:
$1,569/yr vs $1,886 baseline.

**Optimal execution:** Single limit buy, single limit sell at
$0.90, stop at $0.40. No ladder, no tranches.

---

## 6. Prior-weighting analysis: RESOLVED (not useful as filter)

Tested whether entries deeper below the pre-game Kalshi price
recover more reliably. Finding: **non-monotonic relationship.**

51% of S4A entries fire when the favorite is *above* their
pre-game price. These have the highest hit rate (62%) and
best P&L (+$4.32/entry). Entries $0.05–$0.10 below prior
are the weakest (34% hit rate).

**Interpretation:** S4A works not because of mean-reversion
to prior, but because competitive games produce temporary
swings and the favorite has a natural recovery tendency.
Entries above prior = favorite is outperforming expectations
and the dip is pure noise. Entries below prior = favorite is
genuinely underperforming and the dip may be continuation.

The dip-detection parameters ($0.08 from trailing max)
already capture the relevant signal without needing the prior
as an additional filter.

---

## 7. Period and spread effects

### By entry period

| Period | Entries | Hit% | Mean P&L |
|--------|---------|------|----------|
| Q1 | 47 | 47% | +$4.00 |
| Q2 | 49 | 47% | +$1.59 |
| Q3 | 27 | 67% | +$8.51 |
| Q4 | 37 | 59% | +$3.09 |

Q3 entries are best — consistent with the halftime-reset
pattern observed across multiple games (underdog keeps it
close through first half, favorite comes out strong after
halftime). All periods are positive.

### By pre-game spread (Kalshi-confirmed, 404-game expanded dataset)

| |Spread| | Games | Entries | Hit % | Mean P&L | Annual EV |
|----------|-------|---------|-------|----------|-----------|
| 1.0–2.0 | 36 | 29 | 51.7% | +$1.59 | +$702 |
| 2.5–3.5 | 69 | 71 | 47.9% | +$2.57 | +$1,446 |
| 4.0–5.0 | 31 | 29 | 48.3% | +$2.65 | +$1,357 |
| 5.5–6.0 | 35 | 37 | 64.9% | +$6.17 | +$3,570 |
| 6.5–8.0 | 46 | 43 | 58.1% | +$4.14 | +$2,116 |
| 8.5–10.0 | 38 | 36 | 58.3% | +$0.82 | +$425 |
| 10.5+ | 149 | 66 | 69.7% | +$4.55 | +$1,103 |

All 7 buckets are positive EV. Key patterns:

- Wider spreads produce higher hit rates (69.7% at 10.5+
  vs 47.9% at 2.5–3.5) but fewer entries per game (0.44
  vs 1.03). The favorite's natural buoy is strongest when
  the pre-game line gives them a larger anchor.
- The 5.5–6.0 bucket is the standout: +$6.17 mean P&L,
  64.9% hit rate, +$3,570 annual EV. This is nearly double
  the next-best bucket per entry. Sample is thin (n=37) —
  structural explanation vs small-sample noise is an open
  question.
- Expansion buckets (|spread| > 6) have 36–66 entries each.
  The directional finding (all positive) is robust; exact
  dollar figures per bucket are noisy at these sample sizes.

**Source:** `docs/analysis_outputs/strategy4_spread_expansion_kalshi.md`
(Part 8 Path B, 2026-04-21).

---

## 8. Strategy 4B — KILLED (2026-04-23)

Revalidated on the 404-game expanded dataset. Prior result
(+$1,105/yr on 168 games) collapsed to +$148/yr. Only 14 of
1,323 configs produced positive EV (1.1%). Best config earned
$0.19/entry — effectively zero after execution costs.

The resolution-lottery mechanic (12.6% underdog win rate on
held portion) that drove the prior result was abandoned by
the optimizer on the larger dataset. Best config uses pure
swing with $0.05 stop, zero hold-to-resolution.

3 of 7 spread buckets are negative EV. The 8.5–10.0 bucket
alone provides +$1,839 of +$148 total — consistent with
noise, not structure.

Full analysis: `docs/analysis_outputs/strategy4b_revalidation.md`.

---

## 9. Annual EV projection

At 100-contract sizing, maker-maker:

### S4A by spread universe

| Universe | Games | Entries | Annual EV | Evidence |
|----------|-------|---------|-----------|----------|
| |spread| ≤ 6 (core) | 171 | 166 | +$7,075 | Kalshi-confirmed, replay-validated |
| |spread| > 6 (expansion) | 233 | 145 | +$3,644 | Kalshi-confirmed, thin buckets |
| **All spreads** | **404** | **311** | **+$10,718** | **Bucket-level extrapolation** |

**Caveat:** the +$10,718 figure is the sum of per-bucket
annualized EV extrapolations, not a single pooled replay.
Expansion buckets have 36–66 entries each. The directional
finding (all buckets positive) is robust; the exact annual
dollar figure carries meaningful uncertainty. The core
|spread| ≤ 6 universe at +$7,075 is the most conservative
anchor.

### Combined alpha stack

| Strategy | Annual EV | Status |
|----------|-----------|--------|
| S4A dip-recovery (core, |spread| ≤ 6) | +$7,075 | Kalshi-confirmed |
| S4A dip-recovery (expansion, |spread| > 6) | +$3,644 | Kalshi-confirmed, thin samples |
| S3 filtered | +$578–$825 | Holdout-validated |
| ~~S1 bilateral~~ | ~~+$4,000–$5,600~~ | KILLED 2026-04-23 |
| ~~S4B underdog hybrid~~ | ~~+$1,105~~ | KILLED 2026-04-23 |
| **S4A (core) + S3** | **+$7,653–$7,900** | Conservative combined |
| **S4A (all) + S3** | **+$11,297–$11,544** | Full combined |

S1 and S4B both failed on the underdog side — no exit strategy
overcomes the low base rate (~12–18% win probability). The
remaining strategies operate exclusively on the favorite side.

---

## 10. Open questions

1. **5.5–6.0 bucket outperformance.** +$6.17 mean P&L on
   n=37 entries (64.9% hit) is the standout bucket — nearly
   double the next-best per-entry mean. Investigate whether
   this reflects a structural sweet spot (strong-enough
   favorite to recover reliably, close-enough game to
   generate dips) or small-sample noise. Answerable with
   the existing 404-game dataset.

2. **Expansion bucket sample sizes.** The |spread| > 6
   universe adds +$3,644/yr on 145 entries across 233 games,
   but individual buckets have 36–66 entries. As the forward
   collection cron accumulates more paired games, these
   estimates will tighten. Monitor per-bucket stability as
   data grows.

3. **Live execution dynamics — RESOLVED.** Three-part
   investigation (2026-04-22):
   - *Stop execution reality:* 50% clean crosses, 17.4%
     severe gaps, break-even stop price $0.312. Scenario B
     (NO-side resting order at $0.60) recommended.
   - *Params sweep ($0.58–$0.65 NO bid):* suggested $0.58
     NO / $0.30 fallback (+$492/yr vs baseline), but
     repriced existing stops only — blind to converted
     winners.
   - *Full sensitivity sweep ($0.35–$0.45 stop, 404 games):*
     refuted $0.42 (6 converted winners, net −$15/yr vs
     $0.40). Identified $0.35 as pooled optimum (+$227/yr
     vs $0.40) but curve is bimodal and 5/7 spread buckets
     disagree with the pooled optimum — consistent with
     noise, not structure.
   **Conclusion:** $0.40 stop confirmed robust on the
   expanded dataset. All 11 stop levels ($0.35–$0.45) are
   positive EV. No parameter change warranted. Remaining
   open: target-exit fill quality in live conditions
   (31.8% of targets gap past $0.90 — beneficial, monitor
   in paper trading).

4. **Playoff vs regular season.** All 404 paired games are
   predominantly regular season (Feb 20 – Apr 15, 2026). Playoff game
   dynamics (slower pace, tighter defense, more timeouts)
   may shift the parameters.

5. **S4B validation.** The underdog hybrid is promising but
   the 12.6% resolution-win rate on a held portion is a
   thin edge. Needs more games before deployment.

6. **Multi-strategy interaction.** S1, S3, and S4A operating
   simultaneously in the same game has not been simulated.
   Capital allocation across concurrent positions needs
   scoping.

---

## Supersedes

This is a new document. S4 findings were previously only
in `docs/analysis_outputs/strategy4_dip_recovery.md`
(analysis report) and session discussion threads.
