# NBAgent-Live — Thesis & Long-Term Framing

## Core thesis

NBA live-game win probability is priced tightly on Kalshi — the market
mirrors sportsbook consensus pricing closely — both Kalshi and sportsbooks
compress toward the pre-game prior relative to ESPN's more game-state-
reactive WP model, diverging from ESPN by 10-15pp at the tails but
tracking each other to within ~3pp (cross-book std),
updated continuously by algorithmic market makers. The naive
framing — "beat Kalshi's pricing" — treats this like a sportsbook
prop-market edge hunt, and it fails for the same reason it fails on
FanDuel moneylines: the market is efficient at the per-moment level.

The real opportunity is structural, not informational. NBA games
exhibit high within-game volatility (runs, momentum swings, late-game
leverage) that drives Kalshi contract prices to extremes ($0.05 to
$0.95) multiple times per competitive game. The opportunity is not to
predict which side wins, but to **trade the volatility itself** using
Kalshi's order book functionality — which, unlike sportsbook Cash
Out Early, allows entering and exiting positions at will.

This reframes the problem from prediction (hard, competitive, largely
priced in) to positional trading around known patterns of price
movement (tractable, underexplored in prediction-market contexts).

## Three strategy layers

### 1. Bilateral convergence (baseline)

In competitive games, both teams' contracts frequently dip below
extreme thresholds at different points during the game. Accumulating
YES positions on both sides at low prices locks in guaranteed profit
when their combined cost is under $1.00.

- Edge is **mechanical** — doesn't depend on Kalshi mispricing.
- Constraints are execution: liquidity at target prices, timing of
  sequential entries, order sizing.
- Pilot frequency (2024-25 data): ~30% of competitive games offered
  bilateral <$0.20 dips on both sides; median 23 min between the two
  opportunities.

### 2. Single-side mean-reversion

When one side dips to extreme low prices ($0.05–$0.15) in a game that
"should be close," buy and hold to resolution. Returns are asymmetric:
risk the $0.10 cost, payoff up to $1.00.

- Edge is **model-dependent** — requires Kalshi's price to be
  meaningfully below the true probability.
- Pilot data showed Stern-style WP models underestimate NBA recovery
  probability by ~9pp at the tails, and ESPN by ~3pp. However,
  sportsbook backfill (2026-04-19) established that Kalshi and
  sportsbooks price those moments at +10-17pp *above* ESPN — well
  above actual win rates. The model-dependent edge appears negative
  against real-money markets. **Preliminary kill signal issued; formal
  kill pending Phase 3B confirmation.**
- Validation requires paired (Kalshi price, game state) data — the
  core purpose of Phase 1's live logging.
- **Preliminary kill issued 2026-04-19.** Sportsbook backfill
  established that Kalshi/sportsbooks price underdog moments
  at +10-17pp above ESPN. The +3pp ESPN-vs-actual residual is
  entirely absorbed. Formal kill pending Phase 3B confirmation.

### 3. Active position management (swing trading)

Buy cheap during one team's run, sell when the market swings
back — without waiting for game resolution. Profits come from
price oscillation rather than directional accuracy.

- Edge **sidesteps the calibration question** — works regardless
  of whether Kalshi's model is well-calibrated, as long as prices
  swing enough to cover costs and spreads.
- **Operating zone is $0.35-$0.55** (mid-range competitive
  prices), not the extreme-price zone ($0.10-$0.20) originally
  hypothesized. Extreme prices indicate decided games with no
  bounce-back.
- **Per-trade economics validated on Kalshi (n=2 games):**
  $14-25 net per round-trip (maker-maker, 100 contracts).
  Hold times 8-100 min (median ~30 min). Spread $0.01.
- **Universe estimated at ~689 market-price round-trips per
  season** (from 30.4% ESPN-to-FanDuel survival rate applied
  to 2,272 ESPN round-trips in competitive games).
- **Favorite-side variant killed.** Negative EV at market
  prices (−$18.40 blended net on FanDuel data). Resolution
  backstop fires into losses 84% of the time.
- Highest ceiling of the three strategies, highest execution
  demands. Requires monitoring game flow well enough to time
  entries and exits.
- Natural complement to bilateral convergence — both exploit
  volatility, but swing trading monetizes partial swings that
  convergence misses.
- **Assessment document:** `docs/strategy3_assessment.md`.

## What this project is not

- **Not a sportsbook edge-hunting operation.** We're not trying to
  find mispriced moneylines or spread bets.
- **Not a win-probability model competition.** We're not trying to
  build a better WP model than ESPN or Kalshi's market maker. If
  our model is as good as theirs, that's sufficient.
- **Not a real-time HFT system.** NBA games have natural pauses
  (timeouts, free throws, reviews) that create seconds-long windows
  where order books settle. This is "informed trader during
  stoppages," not co-located servers competing on microseconds.
- **Not agentic.** No LLM-in-the-loop decisioning is planned. The
  eventual execution layer is rule-based signal generation informed
  by offline research, not real-time reasoning.

## Relationship to NBAgent

NBAgent (player props) and NBAgent-Live (game-outcome live trading)
are sister projects under a shared brand, with no operational
overlap:

- **Cadence.** NBAgent runs daily batches. NBAgent-Live runs
  continuously during game windows.
- **Data.** NBAgent optimizes for player-level granularity.
  NBAgent-Live optimizes for game-state and market-state
  granularity.
- **Edge source.** NBAgent exploits player-context gaps in
  sportsbook prop pricing. NBAgent-Live exploits volatility
  patterns in efficiently-priced game-outcome markets.
- **Execution.** NBAgent publishes picks. NBAgent-Live will
  eventually place orders.

Data may flow one-way from NBAgent (e.g., pre-game spreads, team
momentum) to NBAgent-Live in narrow cases. NBAgent-Live data does
not flow back.

## Phase progression

Each phase must validate before the next is scoped.

- **Phase 1 — Live data capture.** Log Kalshi orderbook every
  30s during NBA games. Only way to build the historical dataset
  Kalshi doesn't expose.
- **Phase 2 — Historical grounding.** Ingest ESPN PBP + WP per
  gameId. Provides event-level game state to pair with Kalshi
  snapshots and enables backtest replication at better granularity.
- **Phase 3 — Strategy validation.** Phase 3A (ESPN-only bilateral
  analysis, complete) established baseline rates. Phase 3B (paired
  Kalshi+ESPN, in progress) revealed ESPN diverges from real-money
  markets by +10-17pp at the tails. Sportsbook backfill confirmed
  Kalshi ≈ sportsbook consensus. Recalibrated bilateral analysis
  produced revised Strategy 1 operating point and preliminary
  Strategy 2 kill signal. Ongoing: accumulate Kalshi data for
  realized-spread measurement and Strategy 3 scoping.
- **Phase 4 — Live decision engine.** Only designed after Phase 3
  produces a validated spec. Note: ESPN PBP is post-game only; a
  live decision engine would need a real-time game-state source
  (live score feed, Kalshi price as proxy, or similar). Initial
  form is signal alerts for manual paper-trading.

## Success criteria

The project succeeds at the research stage if Phase 3 produces at
least one of the three strategies as validated: a reproducible,
liquidity-aware rule set with positive expected value after fees
and slippage, measured on held-out games.

It fails responsibly if Phase 3 shows all three strategies are
unexploitable in practice — whether because Kalshi's pricing is
better-calibrated than Stern-style models, liquidity at target
prices is too thin, or execution latency erodes edges. In either
outcome, the research is the deliverable. The logging
infrastructure from Phase 1 retains value as a public good / data
asset regardless of whether a live system is ever built.

## Guiding constraints

- **Research before infrastructure.** Do not build execution
  tooling until Phase 3 validates a strategy. Most sessions
  should be analyzing data, not building agents.
- **One validated phase at a time.** Multi-phase plans drift.
  Each phase has a concrete output; the next phase is scoped
  only after it lands.
- **Honest failure mode reporting.** If pilot numbers weaken on
  multi-season data, or if Kalshi pricing turns out to be better
  than Stern, say so plainly and update the thesis. The project's
  long-term value depends on knowing when to stop.
