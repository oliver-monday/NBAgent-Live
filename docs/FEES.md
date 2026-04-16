# FEES — Kalshi cost envelope for NBAgent-Live strategies

Back-of-envelope analysis of how Kalshi's fee schedule affects the
three candidate strategies in `THESIS.md`. Retires item 3.3 in
`THESIS_open_questions.md`.

**Scope.** Fees only. Bid-ask spread and depth impact are separate
costs not modeled here; see *What this doesn't cover* at the end.

**Source.** Kalshi public fee schedule (last updated Feb 5, 2026),
PDF archived on file. KXNBAGAME confirmed as standard fee multiplier
(1×) with maker fees enabled per
`https://kalshi.com/fee-schedule`.

Last updated: 2026-04-17.

---

## Kalshi's fee structure

**Taker fee** (orders immediately matched against resting liquidity):

    fees = round_up(0.07 × C × P × (1-P))

**Maker fee** (resting orders that later get filled):

    fees = round_up(0.0175 × C × P × (1-P))

Where `C` = number of contracts, `P` = price in dollars (0-1).
Fees round up to the next cent, which makes very small trades
fee-punitive (a 1-contract trade at any price pays at least $0.01).
At 100+ contract scale the rounding is <1% of the formula value.

Maker fee is exactly 1/4 of taker fee at the formula level. That
ratio holds to within rounding at any realistic trade size, so all
math below uses 4× as the taker/maker multiplier.

**Peak taker fee** is at `P = 0.50` where `P(1-P) = 0.25` maxes out:
$1.75 per 100 contracts. **Fees decline symmetrically toward the
extremes** — at `P = 0.10` or `P = 0.90` it's $0.63 per 100.

## Per-strategy envelope

All numbers at 100-contract notional unless stated. Round-trip
examples use taker on both legs unless labeled "maker-maker."

### Strategy 1: Bilateral convergence

Buy YES on both sides at low prices, hold to resolution, one side
pays $1.00.

| Entry prices | Gross profit | Fees (2 legs) | Net | Fees as % of gross |
|-----|------|-----|-----|-----|
| $0.10 + $0.10 | $80.00 | $1.26 | $78.74 | 1.6% |
| $0.15 + $0.15 | $70.00 | $1.80 | $68.20 | 2.6% |
| $0.20 + $0.20 | $60.00 | $2.24 | $57.76 | 3.7% |
| $0.25 + $0.25 | $50.00 | $2.64 | $47.36 | 5.3% |
| $0.40 + $0.40 | $20.00 | $3.36 | $16.64 | 16.8% |
| $0.47 + $0.47 | $6.00  | $3.48 | $2.52  | 58.0% |
| $0.49 + $0.49 | $2.00  | $3.48 | $-1.48 | loss  |

**Break-even ceiling.** Fees flip the strategy negative at combined
cost roughly $0.965 (taker-taker). Effective "you should only take
this trade" zone is combined cost ≤ ~$0.80, where fees stay under
~10% of gross.

**Maker-maker equivalents.** Fees drop to ~25% of the above; the
zone of meaningful economics extends to combined cost ~$0.95.

**Verdict.** Fees are **not a binding constraint** on bilateral
convergence at any realistic entry price. The canonical CHA-MIA
case (both sub-$0.10) loses ~1.6% of gross to fees. The binding
constraints are opportunity rate and fillable liquidity, not fee
drag.

### Strategy 2: Single-side mean-reversion

Buy YES at low price, hold to resolution. Asymmetric payoff: risk
entry cost, payoff up to $1.00.

At 100 contracts, entry at $0.10:

    Entry cost:          $10.63   (cost $10 + fee $0.63)
    Break-even win rate: 10.63%
    Stern-implied:       10.0%    (what pilot model says)
    Pilot residual:      +9pp     (actual vs Stern, n~40k obs)
    Implied actual rate: ~20%     (if residual holds vs Kalshi)

    EV per 100 contracts, assuming 20% true win rate:
      0.20 × ($100 - $10.63) + 0.80 × (-$10.63)
      = $17.87 - $8.50
      = $9.37

At entry $0.15:

    Entry cost:          $15.90
    Break-even win rate: 15.90%
    Stern-implied:       ~15%
    Implied actual:      ~24%
    EV per 100:          $8.10

**Verdict.** Fees shift break-even win rate by ~0.6pp at $0.10 entry
and ~0.9pp at $0.15 entry. This is **negligible compared to the
uncertainty** on the +9pp residual itself. If the residual exists
against Kalshi (§1.1 of `THESIS_open_questions.md`), fees don't
meaningfully change the EV. If it doesn't, fees are also irrelevant
because the strategy doesn't work regardless.

### Strategy 3: Active management

Buy cheap, sell on swing-back. Round-trip through the market. Fees
charged on both legs.

**Taker-taker, 100 contracts:**

| Round trip | Gross swing | Total fees | Net | Fees % |
|-----|-----|-----|-----|-----|
| $0.10 → $0.50 | $40 | $2.38 | $37.62 | 6.0% |
| $0.15 → $0.45 | $30 | $2.64 | $27.36 | 8.8% |
| $0.20 → $0.40 | $20 | $2.80 | $17.20 | 14.0% |
| $0.25 → $0.45 | $20 | $3.06 | $16.94 | 15.3% |
| $0.30 → $0.40 | $10 | $3.15 | $6.85  | 31.5% |
| $0.35 → $0.45 | $10 | $3.34 | $6.66  | 33.4% |

**Maker-maker, same cases:**

| Round trip | Gross swing | Total fees | Net | Fees % |
|-----|-----|-----|-----|-----|
| $0.10 → $0.50 | $40 | $0.61 | $39.39 | 1.5% |
| $0.15 → $0.45 | $30 | $0.67 | $29.33 | 2.2% |
| $0.20 → $0.40 | $20 | $0.72 | $19.28 | 3.6% |
| $0.25 → $0.45 | $20 | $0.79 | $19.21 | 4.0% |
| $0.30 → $0.40 | $10 | $0.82 | $9.18  | 8.2% |
| $0.35 → $0.45 | $10 | $0.87 | $9.13  | 8.7% |

**Verdict.** Fees are a **meaningful constraint** on taker-taker
active management, especially on small swings where they eat
30%+ of gross. Maker-maker execution is ~4× cheaper and moves all
the numbers back into acceptable range.

**Design implication for Strategy 3.** The execution spec should
prioritize resting limit orders during game stoppages
(timeouts, free throws, reviews, quarter breaks) over chasing
prices during live play. This is independently consistent with
the thesis' "informed trader during stoppages" framing — but now
there's a cost-side reason for it too, not just a latency reason.

Strategy 3 targeting only large swings ($0.20+ gross) is
tolerant of taker-taker execution if needed. Strategy 3
targeting small swings (<$0.15) essentially requires maker
execution to be economically viable.

## Summary

1. **Fees do not kill any strategy.** At plausible entry sizes and
   prices, no strategy is fee-constrained below its opportunity-
   rate or liquidity constraint.

2. **Strategies 1 and 2 are fee-insensitive.** Fees are 2-6% of
   gross — noise compared to uncertainty on the load-bearing
   claims (opportunity rate, win-rate residual).

3. **Strategy 3 is fee-sensitive on small swings.** Taker-taker
   round trips <$0.15 gross pay 30%+ in fees. Maker-maker
   execution is ~4× cheaper and mostly resolves this.

4. **Maker fees enabled on KXNBAGAME is a real structural
   advantage** worth exploiting, not an accounting detail. It
   substantially enlarges the set of economically viable
   Strategy 3 opportunities.

5. **Bid-ask spread is likely a larger drag than fees at typical
   entry sizes** (see below). Not modeled here; revisit with
   Phase 1 orderbook data.

## What this doesn't cover

These are separate cost components that matter for Phase 3
envelopes but can't be quantified from the fee schedule alone:

- **Bid-ask spread.** On KXNBAGAME the tick is $0.01. Realized
  spreads during live trading need to be measured from logged
  orderbook snapshots. A $0.01 spread on a 100-contract round
  trip is $1.00 per leg — comparable to or larger than the
  fee itself. Half-spread cost should be added to entry and exit
  when modeling Strategy 3 EV.
- **Depth impact.** Top-of-book size caps the notional you can
  transact at the displayed price. For larger orders, average
  fill price walks up the book. The 82k/251k top-of-book sizes
  observed on GSW-PHX pre-tip are meaningless for this because
  the pre-tip book is market-maker liquidity, not real trading
  demand. Phase 1 data will show realized depth during live
  games.
- **Funding drag.** ACH deposits/withdrawals are free. Debit
  card deposits carry up to 2% which would matter for capital
  rotation but not per-trade EV. Wire withdrawals require
  $500k+ minimum — not relevant at research scale.
- **Slippage from latency.** The workflow polls every 30s.
  Prices can move meaningfully between a signal and the fill.
  This is not a fee cost but an execution cost that compounds
  with the above.

Rough rule of thumb until Phase 1 data refines it: **budget
one full tick ($0.01) of spread per leg on top of fees**. For
a 100-contract round trip at $0.15 → $0.45 taker-taker, the
all-in cost estimate rises from $2.64 (fees only) to ~$4.64
(fees + 1 tick each leg) = 15.5% of gross. Maker-maker doesn't
pay the spread (you set the price) but does pay the fee, so
the equivalent number is closer to $0.67 = 2.2%.

## Retires

- `THESIS_open_questions.md` §3.3 — fees envelope exists and
  does not disqualify any strategy. Add dated entry to that
  doc's resolution log pointing here.

## Opens

- `THESIS_open_questions.md` acquires a new implicit sub-item
  under §2.1 (liquidity): **realized bid-ask spread distribution
  at target entry prices** becomes a Phase 3 analysis
  deliverable. The fee envelope shows spread is likely the
  dominant non-fee execution cost.
