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

Last updated: 2026-04-22.

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

## 8. Strategy 4B — Underdog side (secondary)

Best config: momentum entry $0.25–$0.35, run $0.03, lookback
300s, exit +$0.20, hybrid 50/50 hold-to-resolution.

| Metric | Value |
|--------|-------|
| Annual EV | +$1,105 |
| Entries | 182 |
| Mean P&L | +$1.83 |
| Resolution win rate (held portion) | 12.6% |

S4B is positive but more fragile than S4A. The hybrid
structure depends on the ~13% of held portions that resolve
to $1.00 (underdog wins). Pure swing P&L without the
resolution kicker is +$461/yr.

The resolution-lottery math (Part 3D) shows only the
$0.10–$0.15 entry band has positive hold-to-resolution EV.
S4B is not recommended for Phase 4 deployment until
validated with more data.

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
| S1 bilateral | +$1,608 | Confirmed, deployment-ready |
| S4A dip-recovery (core, |spread| ≤ 6) | +$7,075 | Kalshi-confirmed |
| S4A dip-recovery (expansion, |spread| > 6) | +$3,644 | Kalshi-confirmed, thin samples |
| S3 filtered (validated) | +$578–$825 | Validated via holdout |
| S4B underdog hybrid | +$1,105 | Positive but needs more data |
| **S1 + S4A (core) + S3** | **+$9,261–$9,508** | Conservative combined |
| **S1 + S4A (all) + S3** | **+$12,904–$13,151** | Full combined (noisy) |

These strategies operate in different price zones and should
not conflict: S1 catches bilateral dips below $0.40, S3
catches filtered single-side dips at $0.40 with specific
conditions, S4A catches favorite dips in the $0.50–$0.75
range. A single game could trigger multiple strategies at
different points.

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

3. **Live execution dynamics.** 30-second VWAP bins may mask
   sub-second price action. Real fills at the $0.40 stop
   especially may face slippage. The $0.08 dip threshold
   should provide buffer.

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
