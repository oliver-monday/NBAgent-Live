# Active Roadmap

## Phase 2 — ESPN ingest

- Multi-season backfill (2014-2024) — execute after current-season
  analysis pipeline validates end-to-end and Phase 3B produces
  first paired findings. Low urgency.

## Phase 3 — Analysis on ESPN WP foundation + paired data

- **Phase 3B formal** — paired Kalshi + ESPN + sportsbook
  analysis on ≥10 games. Blocked on Kalshi data accumulation
  (currently n=4 usable). Covers: realized spread measurement
  at (0.25, 0.35) entry prices, Strategy 1 opportunity rate
  validation on Kalshi data, Strategy 3 oscillation
  characterization.
- **Strategy 3 scoping — active priority.** Swing-trading
  analysis on Kalshi price oscillation data. Living spec:
  `docs/STRATEGY3_SPEC.md`.
  - HOU-LAL deep dive (n=1): mid-range round-trips confirmed,
    $14.55/trade maker-maker. Operating zone is $0.35-$0.55.
  - Game flow trajectories (ESPN, N=1,234): 75% of competitive
    games produce ≥1 mid-range round-trip.
  - Odds API timeseries (n=15 FanDuel): 30.4% ESPN-to-market
    survival rate. ~689 market-price round-trips/season.
  - Favorite-side to resolution: **killed** (−$18.40 blended).
  - Multi-game Kalshi (4/19 R1G1, n=4): ORL@DET confirmed
    oscillation. 3 blowouts expected for R1G1 seeds.
  - Kalshi trades probe: sizing resolved (100 contracts
    invisible at 0.02% of bucket volume).
  - Timeout execution windows (HOU-LAL + ORL@DET): confirmed
    as execution quality enhancer (2.3× depth, $0.01 spread
    floor). NOT a directional signal.
  - Score-to-price impact (n=2 Kalshi): 3-pointer moves market
    $0.04 in 3.5s, impact peaks in $0.40-$0.50 zone.
  - ESPN scoring-run catalog (N=549 competitive games): 89% of
    runs produce some bounce-back. Favorites recover 3-6pp
    more often than underdogs. Q1 runs reverse most reliably
    (59%). Timeouts do not improve recovery rates.
  - **Graduation threshold: 10 competitive Kalshi games.
    Current progress: 2/10.** Continue accumulating via logger
    during playoff games.
  - Next: run `strategy3_oscillation_multi.py` on each night's
    games as they complete.
- **§1.4 retirement analyses** — three spread-anchoring tests.
  Deprioritized: the strategy-relevant question (how does
  Kalshi behave at the tails?) is now answered directly by
  the sportsbook backfill. Analyses remain informative for
  ESPN model understanding but are no longer load-bearing.
- **Empirical WP model** — deprioritized. The calibration
  question is now answered empirically via sportsbook
  consensus rather than model-fitting.

## Phase 4 — Live decision engine (speculative)

Rule-based trading bot. No LLM-in-the-loop, no live ML inference —
the "intelligence" lives entirely in rules derived from Phase 3
offline research; the runtime just evaluates conditions on current
state and fires predefined actions. Hard dependency on Phase 3B
producing a validated strategy spec — do not design until then.

### Core loop

Every N seconds (30s initially; could tighten in later stages):

1. **Ingest.** Read latest Kalshi orderbook snapshot + latest ESPN
   PBP/WP state for each tracked game.
2. **Evaluate.** Run the strategy rules against current state.
   Representative questions: *Is side X below price threshold? Is
   time-remaining in the tradeable window? Do we already hold a
   position on this game? Is liquidity sufficient at target size?*
3. **Decide.** Emit exactly one of `{no-op, open, add, trim, close}`
   per tracked game.
4. **Execute (or notify).** Submit orders to Kalshi's trading API
   in Phase 4c+; log the intended trade for manual review in
   Phase 4a/4b.
5. **Book-keep.** Update position state, PnL, daily and per-game
   risk counters.

Rules are the Python translation of whatever Phase 3 produces.
Illustrative example in today's vocabulary (not a committed rule —
for shape only): *"If away dips < $0.15 on a |spread|≤6 game with
sec_rem ≥ 60 AND top-of-book resting size ≥ $500 at target price,
open a 100-contract position; set a passive limit exit at $0.70
combined cost if the other side dips; close flat if neither leg
moves by game end minus 2 min."* That whole rule becomes ~30 lines
of code; the engine evaluates it every tick.

### Components (in dependency order)

1. **Live PBP / WP polling.** The existing `scrapers/espn_scraper.py`
   is post-game. Phase 4 needs the same endpoint polled every N
   seconds during live games. Small change — same endpoint, higher
   cadence, a separate process to avoid interfering with the
   backfill scraper.
2. **Rule engine + state tracker.** Python module holding
   positions, evaluating rules, emitting decisions
   (`no-op / open / add / trim / close`) per tracked game. Pure
   logic, unit-testable. First-cut size: ~500 lines per strategy.
3. **Kalshi trading API integration.** Authenticated endpoint,
   distinct from the unauthenticated market-data endpoints used
   by the Phase 1 logger. Needs: buy/sell orders, cancellation,
   fill notifications, position queries. New secret (API key);
   new operational risk surface.
4. **Risk layer.** Hardcoded caps at engine level: max notional
   per game, max daily loss, kill switch, position-size limits.
   Non-negotiable — trades violating these are blocked at the
   engine even if the rule set would open them. Must be provably
   unbypassable.
5. **Observability.** Every decision logged with inputs, rule
   evaluations, outcomes. Real-time PnL tracking. A dashboard is
   nice-to-have, not required for v1.
6. **Paper-trading harness.** Same logic path, no real orders.
   Runs for days/weeks against live data before real capital is
   ever deployed.

### Staged rollout

Each stage must graduate before the next begins. Graduation
criteria go into `docs/KILL_CRITERIA_draft.md` alongside the
existing per-strategy thresholds.

- **Phase 4a — Signal alerts.** Engine runs; when it would open a
  trade, sends a notification (push / SMS / email / Slack).
  Operator decides in real time whether to execute manually on
  Kalshi's web UI. Zero code path for real money. Validates the
  rules against live reality with no execution-layer exposure.
  Runs for at least one full playoff round. Output: alert log +
  operator action rate.
- **Phase 4b — Paper trading.** Engine simulates positions using
  real Kalshi fill prices; tracks fictional PnL. Still no real
  trades. Validates: *if it had executed, would results match
  Phase 3's projected EV?* Catches execution-reality vs projection
  gaps (e.g., "Phase 3 projected 50% fill rate at target price,
  production is 30%"). Runs 2-4 weeks.
- **Phase 4c — Live, capped.** Real capital, hard caps
  (first-cut ballpark: $100/game, $500/day), manual kill switch,
  mandatory nightly review. Two to three weeks here.
- **Phase 4d — Full deployment.** Only after 4c results match 4b
  projections within expected variance. Cap raises are additional
  graduation steps, not "full deployment" itself.

### Known risks (flagged for future design)

- **Execution latency vs stale alpha.** The 30s polling cadence is
  fine for signal generation but sometimes wrong for execution.
  Prices during live-game runs can move 5-10¢ within a single
  cycle. If the engine sees "YES CHA at $0.12, place order" at
  cycle T and the order lands at T+1s, the price may already be
  $0.14. Execution layer needs either limit-order patience (accept
  slower fills in exchange for price discipline) or explicit
  signal-freshness awareness (discard decisions whose inputs are
  stale relative to current mid). Interacts directly with §2.5
  (realized bid-ask spread at target entry prices).
- **Adversarial MM dynamics (§2.2) become material at execution
  time.** A market maker that sees a repeating pattern ("taker
  always enters at $0.15 on the way down") can widen spreads or
  pull quotes preemptively once the bot's signature is learned.
  Small size is protective — under the MM's attention threshold —
  but scaling notional in Phase 4c/4d re-opens the question.
  Engine should log enough signal-to-order timing data for
  MM-reaction analysis post-hoc.
- **Rules decay over time (§2.3).** Predicted to happen as Kalshi
  MM calibration sharpens. Whatever works in April 2026 may not
  work in April 2027. Phase 4 requires monitoring from day one:
  rolling opportunity frequency, rolling EV, per-week deltas. If
  edge is eroding, operator needs to know *before* capital is
  lost, not after. Build the monitoring before any money is on
  the line.
- **Phase 3B could invert strategy signs — cart and horse.** The
  n=2 / n=6 smoke tests have shown the pipeline works and
  produced interesting findings, but the headline "Kalshi is less
  extreme than ESPN" result potentially *inverts* Strategy 2's
  sign relative to the pilot's +3pp projection against ESPN.
  Formal Phase 3B at n≥10 games may show that the strategies we
  want to automate look meaningfully different from what the
  pilot suggested. Do not start Phase 4a rule authoring until
  Phase 3B lands.

### Operational note

Phase 4 runs on the same capture infrastructure as the live
logger (hosted VM per the Phase 1 migration off GitHub Actions —
see roadmap entry for that pivot once written). Capture + execute
coexist in one runtime; analysis and rule authoring stay on the
operator's laptop. Principle: *"VM captures, laptop analyzes, VM
executes once rules are locked."* Keeps the VM footprint minimal
and the analysis iteration loop fast.

## Phase O — Odds API integration (parallel track)

Secondary data source. Planning doc: `docs/ODDS_API_INTEGRATION.md`.
Sits alongside Phases 2 and 3 — not sequential with them. Pulls
US sportsbook pricing (moneyline, spreads) as a consensus
benchmark for §1.1, a cleaner test vehicle for §1.4, and a
flow-vs-game-state disambiguator for §6.6.

- Phase O1 — Live scraper MVP (`scrapers/odds_api_live.py`,
  `.github/workflows/odds_api_live.yml`). Streams A + B from
  the planning doc.
- Phase O2 — Analysis harness joining Odds API + Kalshi + ESPN
  at matched timestamps.
- Phase O3 — First paired analysis against accumulated live
  data. Gated on ≥5 games of Stream A data.
- Phase O4 — §1.4 focused historical test using Stream C
  backfill. 20 games × 4 in-game moments. ~800 credits.

## Infrastructure

- **Logger local-run reliability** — monitor for missed games.
  MIN-DEN (4/18) and ATL-NYK (4/18) lost due to logger gaps.
  Consider automation options (launchd on Mac, cheap VPS) once
  research phase stabilizes.
- **Per-game file split** — landed 2026-04-19. Monitor file
  sizes and git repo growth.
