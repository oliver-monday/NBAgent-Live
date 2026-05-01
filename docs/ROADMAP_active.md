# Active Roadmap

## Phase 2 — ESPN ingest

- Multi-season backfill (2014-2024) — execute after current-season
  analysis pipeline validates end-to-end and Phase 3B produces
  first paired findings. Low urgency.

## Phase 3 — COMPLETE (2026-04-21)

Phase 3B formal analysis complete. 168 games paired (165
competitive, |spread| ≤ 6). Three strategies validated,
one killed. Full arc in `ROADMAP_resolved.md`.

**Active alpha stack:**
- S4A dip-recovery with ratchet: +$1,899/yr pooled (404-game
  replay-validated, holdout 6/6, ratchet trigger +$0.08).
  Pre-ratchet per-bucket: +$7,075/yr core |spread|≤6,
  +$10,718/yr uncapped (all 7 spread buckets positive EV).
- Add-on tranche (second entry $0.40–$0.45): +$464/yr
  incremental, validated but **DEFERRED**.

**Killed strategies:**
- ~~S1 bilateral: KILLED 2026-04-23~~ (0/62 configs positive)
- ~~S3 filtered: KILLED 2026-04-23~~ (subsumed by S4A
  extended range; filters noise-fitted on 168 games)
- ~~S4B underdog hybrid: KILLED 2026-04-23~~ (+$148/yr on 404
  games, 1.1% of 1,323 configs positive)

**Deprioritized (no longer load-bearing):**
- §1.4 retirement analyses (answered by sportsbook backfill)
- Empirical WP model (answered by sportsbook consensus)

## Phase 4 — Live decision engine

**As of 2026-04-21: Phase 3B is complete, Phase 4a is unlocked.**
One validated strategy in paper-trading: S4A dip-recovery
with breakeven ratchet. S1, S3, S4B killed. See
`docs/KILL_CRITERIA_draft.md` §Project-level decisions.

- **Phase 4a S4A engine — IMPLEMENTED (2026-04-22).**
  Paper-trading engine: `engine/s4a_signal.py` (signal
  detector), `engine/position_manager.py` (state tracker),
  `engine/live_runner.py` (runtime). Replay-validated
  trade-for-trade against the authoritative offline
  simulator on the core 171-game dataset (|spread| ≤ 6,
  166 entries, 52.4% hit, +$1,708 annual EV). Spread
  expansion (Part 8 Path B, 404 games) shows all 7
  spread buckets positive EV (+$10,718/yr uncapped).
  Engine operates on all Kalshi-listed games with no
  spread filter — already trading the expanded universe.
  Status:
  unverified live (pending first paper-trading run).
  Design doc: `docs/PHASE4A_DESIGN.md`.
- **Phase 4a S4A ratchet — IMPLEMENTED (2026-04-23).**
  Breakeven ratchet stop added to engine. `PositionManager`
  extended with per-position `highest_since_entry`,
  `ratchet_triggered`, `effective_stop` state and maker/
  taker fee split (maker on entry/target/ratchet_stop,
  taker on full_stop). Target fills at $0.90 exactly.
  `--ratchet 0.08` CLI flag on both `engine/replay.py` and
  `engine/live_runner.py`; default is 0.08 (set to 0 to
  disable). Replay-validated at both modes:
  `--ratchet 0.08` → 358/149/88/121, hit 41.6%, mean
  $+3.92, annual $+1,899 (PASS vs Part 12);
  `--ratchet 0` → 311/179/132/0, hit 57.6%, mean $+3.13,
  annual $+1,320. Spec: `docs/STRATEGY4_SPEC.md` §5A.
  Status: unverified live (pending paper-trading session
  at `--ratchet 0.08`).
- **Phase 4a S1 engine — CANCELLED.** S1 bilateral killed
  2026-04-23. No engine module will be built. See
  `docs/STRATEGY1_SPEC.md` (kill record).

Rule-based trading bot. No LLM-in-the-loop, no live ML inference —
the "intelligence" lives entirely in rules derived from Phase 3
offline research; the runtime just evaluates conditions on current
state and fires predefined actions.

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
- **Phase 3B signal-inversion warning — RESOLVED (2026-04-21).**
  The earlier warning that Phase 3B might invert strategy signs
  turned out partially true: Strategy 2 was formally killed
  (−$18.40 blended on FanDuel data). Strategies 1, 3-filtered,
  and 4 all validated on the 168-game paired dataset. Phase 4a
  rule authoring has begun.

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
- **Forward-collection cron — LANDED (2026-04-21).** Nightly
  `forward_collection.yml` runs `analysis/forward_collect.py`
  at 10:00 UTC (03:00 PT) against yesterday's scoreboard,
  fetches ESPN PBP/WP + Kalshi trade tape for each completed
  game, writes per-game timeseries/plays under
  `data/wp_kalshi_paired/` and an audit log at
  `data/wp_kalshi_paired/forward_runs/<date>.log`. Weekly
  `forward_collection_weekly.yml` (Mon 11:00 UTC) refreshes
  `matched_games.csv` and aggregate summaries. Logger workflow
  schedule stripped — `workflow_dispatch` only. Watch items:
  first nightly run committing as expected; off-night log
  behavior; repo growth from committed paired data.
- **Forward-collection migrated to artifact-based architecture
  (2026-04-30).** Per-game CSVs now live in GH Actions
  artifacts (90-day retention) + Oliver's local Mac, not in
  the repo. Repo plateaus at ~60MB. Aggregate moved local
  via `scripts/sync_paired_data.sh` + manual
  `python -m analysis.wp_vs_kalshi_aggregate`. Supersedes the
  2026-04-28 "weekly hardened" entry — that fix unblocked the
  weekly but pushed 190MB into the repo with ongoing growth;
  the artifact migration fixes that. The empty-discovery
  defensive guard from 2026-04-28 stays in place as a safety
  net. Watch:
  - 2026-05-04: weekly succeeds with ticker_matcher only.
  - First nightly post-migration: artifact uploads, audit
    log commits, no per-game CSVs in commit diff.
  - First sync run by Oliver: `gh auth login` works,
    artifacts pull cleanly.
- **Paper trade journal review (2026-04-30).** First
  systematic comparison ran. Verdict: **BLOCK**. Two HIGH
  findings to diagnose before continuing accumulation:
  (1) 10 of 12 session_starts have no session_end (all
  observed ends carry `interrupted=true`); (2) 3 entries
  opened but 0 closes ever logged — engine has not
  observed a single entry-to-exit cycle. Entries that
  did fire are spec-compliant ($0.66, $0.71, $0.73).
  Re-review cadence: every 5 game-nights or on engine
  change. Tooling:
  `analysis/paper_journal_review.py`. Report:
  `docs/analysis_outputs/paper_journal_review.md`.
- **Paper-trade journal data-loss fix (2026-04-30).**
  Diagnosed the journal review v1 BLOCK as a writer
  durability bug, not an engine logic bug: terminal
  session_summary lines show 24 entries / 24 closes
  across the 8-night sample, vs 3 entries / 0 closes
  on disk. Root cause: line-buffered text-mode writes
  sitting in Python / kernel page cache without explicit
  fsync, lost when the long-running process gets
  suspended by macOS App Nap. Repo location
  (`~/Documents/`) compounds the risk surface
  (iCloud / Spotlight / Time Machine). Fixed:
  `Journal.append()` now flushes + fsyncs every record;
  empty-discovery path now emits a `session_end`;
  startup logs a WARNING if the journal path is in a
  default-iCloud-synced tree. Operator action: move
  the repo out of `~/Documents/` (recommended
  `~/Code/NBAgent-Live`) before the next paper-trading
  session. Watch:
  - Next paper-trading session: synthetic write test
    passes; live journal records match terminal.
  - Re-run paper journal review v2 after 3+ nights of
    post-fix data; verdict should move from BLOCK to
    CLEAN/CONCERNS.
- **S4A live performance variance (2026-04-30).**
  Terminal-derived 24-entry sample shows hit rate
  20.8% vs backtest 41.6%, mean P&L -$6.10 vs +$3.92.
  Within statistical noise at n=24 but worth tracking.
  Re-evaluate at n=50.
