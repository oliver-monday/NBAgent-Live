# Strategy 3 Assessment — NBAgent-Live

## 2026-04-19

Synthesizes all Strategy 3 findings to date. Frames the
graduate / kill / continue-collecting decision.

---

## 1. What Strategy 3 is

Buy a team's YES contract when its price dips during an
opponent's run. Sell when the price bounces back. Profit
comes from price oscillation, not directional prediction.
The strategy is agnostic to which team wins — it trades
the volatility that competitive NBA games naturally produce.

Operates on Kalshi's NBA per-game outcome contracts, which
allow free entry and exit (unlike sportsbook Cash Out Early).

---

## 2. Evidence assembled

| Source | What it tells us | n |
|--------|-----------------|---|
| HOU-LAL Kalshi orderbook (4/18) | Per-trade economics on real Kalshi data: $14.55 net maker-maker at (0.35, 0.50). Spread $0.01 median. Depth adequate. | 1 game, 5 completed trips |
| ESPN WP game flow trajectories | Upper bound on universe: 75% of \|spread\|≤6 games produce ≥1 mid-range round-trip. ~2,272 total round-trips/season. | 1,234 games |
| FanDuel Odds API timeseries | ESPN-to-market survival rate: **30.4%**. Market-price swings are real but smaller than ESPN suggests. | 15 games, 34 FD round-trips |
| Sportsbook backfill (4/19) | Kalshi ≈ sportsbook consensus. ESPN is the outlier (+10-17pp at tails). Compression is uniform across books. | 30 games, 341 quotes |
| Favorite-side analysis | Favorite-side swing trading is **negative EV** at market prices. Resolution backstop fires into losses 84% of the time. Kill. | 15 games (FD), 1,234 (ESPN) |

---

## 3. Strategy 3 economics — current best estimate

### Per-trade

| Metric | Value | Source |
|--------|-------|--------|
| Operating zone | Entry $0.35-0.45, exit entry + $0.10 to $0.15 | HOU-LAL + FD timeseries |
| Gross per round-trip | $10-15 (100 contracts) | Threshold arithmetic |
| Maker-maker fees | ~$1.50-1.80 per round-trip | FEES.md formula |
| Realized spread | $0.01 median (1 tick) | HOU-LAL Section 4 |
| Net per round-trip (maker-maker) | ~$8-13 | Gross − fees − spread |
| Reference net (HOU-LAL) | $14.55 mean | 5 completed trips |
| Hold time | 8-45 min (median ~23 min) | HOU-LAL Section 3B |
| Max adverse excursion | 11.6% median, 22.8% worst case | HOU-LAL Section 3C |

### Per-season projection

| Metric | Value | Derivation |
|--------|-------|-----------|
| ESPN round-trips (\|spread\|≤6) | ~2,272 | Game flow trajectory, N=1,234 |
| Survival rate (ESPN→market) | 30.4% | FD timeseries, n=15 |
| Estimated market-price round-trips | ~689/season | 2,272 × 0.304 |
| Estimated games with ≥1 trip | ~200-250/season | ~75% × 0.304 × 549 competitive games |
| Net EV per round-trip | ~$8-14 | Range from threshold analysis |
| **Estimated season EV (100 contracts)** | **$5,500-$9,600** | 689 × $8 to 689 × $14 |

### Sensitivity

| If survival rate is actually... | Season EV range |
|------|------|
| 20% (pessimistic) | $3,600-$6,400 |
| 30% (measured) | $5,500-$9,600 |
| 40% (optimistic) | $7,300-$12,800 |

At 100-contract sizing ($35-45 capital at risk per entry),
this implies ~$5K-$10K annual return on ~$5K peak deployed
capital — roughly 100-200% annualized return if all trips
are executed. Before liquidity haircuts and execution
imperfections.

---

## 4. What's validated

**Price oscillation exists on Kalshi.** HOU-LAL showed 10
swings ≥ $0.10 (5 per side), with $0.01 spreads and
adequate depth. Not a theoretical construct.

**Swings produce profitable round-trips at market prices.**
FanDuel timeseries across 15 games showed 34 completed
round-trips at the (0.35, 0.50) grid — 2.27 per game on
average. Real-money markets oscillate enough to trade.

**Hold times are human-tradeable.** 12.7 min mean
round-trip duration (ESPN, 15-game sample). Not HFT, not
requiring constant screen attention. Compatible with the
thesis's "informed trader during stoppages" model.

**Fee structure supports the strategy.** Maker-maker fees
are ~$1.50-1.80 per round-trip at mid-range prices. On
$10-15 gross swings, fees consume 12-18%. Spread adds
~$1. Total execution cost ~$2.50-3.00, leaving $7-12 net.
Viable.

**Game shape doesn't matter for targeting.** Survival rate
was uniform across Comeback (31%), Back-and-forth (28%),
and Wire-to-wire (43%) buckets. No need to predict game
type pre-tip. Filter on |spread| ≤ 6 and monitor.

---

## 5. What's NOT validated

**Kalshi-specific execution.** HOU-LAL is n=1. The $14.55
per-trade figure and the $0.01 spread come from a single
game. Kalshi's orderbook may behave differently from
FanDuel pricing in ways the Odds API proxy can't capture:
- Kalshi spread could widen during fast-moving game states
  (exactly when you'd want to trade)
- Fill rates on maker orders are unknown
- Depth at entry prices varies (HOU-LAL showed 50k+ depth
  77% of the time at mid ≤ $0.10, but only 37% at
  $0.25-$0.30)

**Multi-game Kalshi consistency.** One game is not a
pattern. Tonight's 4 playoff games (assuming logger
captured cleanly) will be the next real data points.
Need ≥10 Kalshi games with competitive game flow before
any confidence in per-trade economics.

**FanDuel-native threshold optimization.** The (0.40, 0.50)
pair showed 35% more FD round-trips than (0.35, 0.50). The
optimal Kalshi operating point might differ from both. Need
Kalshi data to calibrate.

**Position sizing impact.** All analysis assumes 100
contracts. At that size, market impact should be negligible
(top-of-book sizes were 50k-300k on HOU-LAL). But if
scaling to 500+ contracts, order flow could move the price
and attract MM attention (§2.2 adversarial dynamics).

**Stop-loss mechanics.** The greedy scan has no exit on
adverse moves. A real strategy needs a stop-loss rule —
"close at entry − $0.05" or similar — which would change
both the win rate and the per-trade P&L distribution.
Untested.

**Season-long edge stability.** Kalshi's MM calibration
may tighten over time (§2.3). 2025-26 regular season
pricing may not represent 2026-27 conditions. The measured
survival rate is backward-looking.

---

## 6. What's killed

**Favorite-side swing trading: KILL.** Pooled blended net
of −$18.40 per position on FanDuel data. The resolution
backstop (holding to game end when the favorite doesn't
recover) fires into losses ~84% of the time at market
prices. The bimodal "accidental win" outcome is too rare
to offset the concentrated losses. Not worth further
investigation.

**Extreme-price entries (≤$0.20): KILL for Strategy 3.**
HOU-LAL showed zero round-trips at the extreme grid. By
the time prices reach $0.15-$0.20, the game is typically
decided — no bounce-back. Extreme prices remain relevant
for Strategy 1 (bilateral convergence) but not for
swing trading.

---

## 7. Against the kill criteria

The kill criteria in `KILL_CRITERIA_draft.md` were written
before any data existed. Some thresholds were set in
extreme-price terms that no longer match Strategy 3's
actual operating zone. Assessment against the criteria
as written, plus a proposed recalibration:

| Criterion (as written) | Threshold | Observed | Verdict |
|---|---|---|---|
| Round-trip frequency ≥ 8% | ≥ 8% of competitive games | ~75% on ESPN, ~30% survival → ~23% on market prices | **Pass** |
| Median swing capture ≥ $0.10 | ≥ $0.10 | $0.10-$0.15 at (0.35-0.40, 0.50) | **Pass (marginal)** |
| Realized spread at entry ≤ $0.20 is < $0.03 | < $0.03 | $0.01 median (HOU-LAL, n=1) | **Pass (insufficient data)** |
| Maker fill rate ≥ 60% | ≥ 60% | **Unknown** — no fill data | **Cannot evaluate** |
| Median time-in-position ≥ 90 seconds | ≥ 90 sec | ~23 min median (HOU-LAL) | **Pass** |

**Kill criteria NOT triggered.** No criterion is in kill
territory. Two criteria (spread, fill rate) lack sufficient
data. The strategy is in **continue-collecting** status.

### Proposed recalibration of kill criteria

The original thresholds assumed extreme-price entry
(≤ $0.20) and $0.15+ swings. Actual operating zone is
$0.35-$0.45 entry with $0.10-$0.15 swings. Proposed
updates:

- **Round-trip frequency:** ≥ 15% of |spread|≤6 games
  at Kalshi-native thresholds (currently estimated at
  ~23% via FD proxy — above bar)
- **Swing capture:** ≥ $0.08 net per round-trip after
  fees and spread (maker-maker). Currently $8-14 on
  HOU-LAL — above bar.
- **Realized spread:** < $0.02 at mid-range prices
  ($0.35-$0.50). Currently $0.01 on n=1 — above bar
  but needs multi-game confirmation.
- **Maker fill rate:** ≥ 50% (relaxed from 60% given
  that taker-taker is still profitable at these swing
  sizes). **Cannot evaluate yet.**
- **Hold time:** ≥ 3 minutes median. Currently ~23 min
  — well above bar.

---

## 8. Decision framework

### Graduate to Phase 4a (signal alerts) if:

All of the following on ≥10 competitive Kalshi games:

1. ≥ 15% of games produce a completed round-trip at
   Kalshi-native (0.40, 0.50) or better thresholds
2. Median net per round-trip ≥ $5 (maker-maker, 100 ct)
3. Realized spread ≤ $0.02 at entry prices
4. Top-of-book depth ≥ 50 contracts at entry prices in
   ≥ 50% of entry-zone snapshots

### Continue collecting if:

Results are directionally positive but n < 10 competitive
Kalshi games. The 2026 playoffs provide ~80 games over
~6 weeks. At ~55% competitive rate and current logger
reliability, expect ~30-40 usable games by early June.

### Kill if:

On ≥10 Kalshi games:
- Round-trip frequency < 5% of competitive games, OR
- Median net per trip < $0 after fees and spread, OR
- Realized spread ≥ $0.03 at entry prices (indicating
  the book widens during the moments we'd trade), OR
- All round-trips complete in < 90 seconds (HFT
  territory, outside operating model)

---

## 9. What to do next

### Immediate (this week)

1. **Analyze tonight's 4 playoff games** from the Kalshi
   logger. Run the HOU-LAL oscillation script generalized
   to multi-game input. This moves n from 1 toward 5-7.
2. **Continue running logger** during all playoff games.
   Logger reliability is the binding constraint on data
   accumulation.

### Short-term (next 2-3 weeks)

3. **Accumulate ≥10 competitive Kalshi games.** ~3-4
   playoff games per night, ~55% competitive, so ~2
   usable games per night. ~5-7 nights to reach 10.
4. **Run formal Phase 3B** on the accumulated Kalshi
   data: pooled round-trip rates, spread distributions,
   depth analysis. This is the graduation test.
5. **Test stop-loss variants** on the accumulated data.
   Does "close at entry − $0.05" improve risk-adjusted
   returns?

### Medium-term (if Phase 3B passes)

6. **Phase 4a: signal alerts.** Build a rule-based
   monitor that flags entry/exit signals during live
   games. Operator decides manually whether to execute
   on Kalshi's web UI. Zero code path for real money.
7. **Paper trade for ≥20 games.** Track what would have
   happened if signals were executed. Compare against
   Phase 3B projections.

### Deferred

- Strategy 1 (bilateral): marginal at $6.55/game. May
  function as a supplement to Strategy 3 (bilateral
  setups that occur while monitoring for swings).
  Re-evaluate after Phase 3B.
- Strategy 2 (mean-reversion): dead. Formal kill
  pending Phase 3B but the direction is unambiguous.
- Multi-season ESPN backfill: useful for confidence
  intervals but not blocking any decision.
- Odds API live scraper (Phase O1): lower priority now
  that the sportsbook backfill answered §1.1 and the
  timeseries scrape provided survival rate.

---

## 10. Honest risk assessment

**This could still fail.** The most likely failure modes:

1. **Kalshi spread widens during swings.** HOU-LAL showed
   $0.01 but that's one game. If spread is $0.03 during
   the fast-moving moments when round-trips initiate, net
   per trip drops from $12 to $6 — marginal.

2. **Maker fill rate is low.** If resting orders at target
   entry prices get jumped or pulled before fill, you're
   forced into taker execution. Taker-taker fees are 4×
   maker-maker. At the (0.40, 0.50) grid: taker-taker
   net is ~$6 vs maker-maker ~$12. Still positive, but
   the economics halve.

3. **Logger reliability limits data accumulation.** Two
   games already lost (MIN-DEN, ATL-NYK on 4/18).
   Every missed game delays the graduation decision.
   Automation (launchd, VPS) would help.

4. **Kalshi MM adapts.** If a pattern of limit orders at
   $0.40 during scoring runs becomes detectable, the MM
   could widen spreads preemptively. Small sizing ($35-45
   per entry) is protective — well under the MM's
   attention threshold — but this risk grows with scale.

5. **The 30.4% survival rate has wide confidence
   intervals at n=15.** Binomial 95% CI is roughly
   18-46%. The low end (18%) would cut the season
   EV estimate to ~$3,300. Survivable but marginal.

None of these are kill signals yet. They're the questions
that more Kalshi data answers.
