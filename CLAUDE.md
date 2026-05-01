# CLAUDE.md — NBAgent-Live

Working context for AI agents operating in this repository.

## What this project is

NBAgent-Live is live Kalshi NBA orderbook data capture and live-trading
research. It is **orthogonal to** and **separate from** the sibling
NBAgent project (broader research codebase: Stern WP model, minute-level
retrospective analysis, bilateral dip study).

The split exists because:
- NBAgent is retrospective, using historical score data.
- NBAgent-Live needs to run continuously forward-in-time to log Kalshi
  prices that have no historical archive.
- Keeping them separate avoids entangling long-lived data-capture
  workflows with the analysis repo.

## Current phase: research

We are in research phase. **Do not build agent/frontend infrastructure
until research produces a validated strategy spec.** Progress:

1. **Phase 1** — Live Kalshi orderbook capture. Confirmed
   working. Running locally (GitHub Actions deactivated).
   Per-game file split landed 2026-04-19.
2. **Phase 2** — ESPN PBP + WP historical grounding. Complete
   for 2025-26 regular season (1,234 / 1,243 games usable).
3. **Phase 3** — Analysis.
   - Phase 3A done (ESPN-only bilateral + calibration).
   - Phase 3B smoke test done (n=4 usable paired games).
   - Sportsbook backfill done (57 dip observations).
   - Strategy 1 recalibrated: marginal ($6.55 EV/game).
   - Strategy 2 preliminary kill issued.
   - **Strategy 3 scoping — active priority:**
     - HOU-LAL deep dive (n=1 Kalshi): 5 mid-range
       round-trips, $14.55 net/trade maker-maker.
     - Game flow trajectories (N=1,234 ESPN): 75% of
       competitive games produce mid-range round-trips.
     - Odds API timeseries (n=15 FanDuel): 30.4% ESPN-to-
       market survival rate. ~689 market-price round-trips
       per season estimated.
     - Favorite-side analysis: killed (negative EV on
       market prices).
     - Multi-game Kalshi (4/19 R1G1, n=4): 1 competitive
       game (ORL@DET) confirmed oscillation pattern.
     - Kalshi historical trades probe: 93,838 trades on
       HOU-LAL. 100-contract orders are invisible (0.02%
       of 5-min bucket volume). Sizing is not a constraint.
     - **Phase 3B complete (2026-04-21):** 414 games paired
       via ticker-matcher batch infrastructure (full-season
       backfill, all spreads). S1/S3-filtered/S4A/S4B all
       analyzed. Spread expansion (Part 8 Path B): all 7
       spread buckets positive EV.
     - **Strategy 3: KILLED 2026-04-23.** Filters noise-fitted
       on 168 games; entry zone subsumed by S4A extended range.
       No engine module. Kill record: `docs/STRATEGY3_SPEC.md`.
     - **Strategy 4 confirmed:** Dip-recovery swing trading
       with breakeven ratchet (+$0.08 trigger). +$1,899/yr
       pooled (404-game replay-validated, holdout 6/6).
       Pre-ratchet per-bucket: +$7,075/yr core (|spread| ≤ 6),
       +$10,718/yr uncapped. S4B underdog hybrid killed
       2026-04-23. Spec: `docs/STRATEGY4_SPEC.md`.
     - **Phase 4a unlocked.** Single alpha source: S4A with
       ratchet (+$1,899/yr pooled). S1, S3, S4B all killed.
       Add-on tranche (+$464/yr) validated but deferred.
   - Phase 3B formal COMPLETE (see above).
4. **Phase 4** — Live decision engine. **Phase 4a unlocked
   2026-04-21.** Scoping in progress.

**Parallel track — Phase O:** Odds API integration partially
executed (sportsbook backfill + timeseries scrape consumed
~6,200 credits). Live scraper (Phase O1) deprioritized —
the backfill and timeseries answered the load-bearing questions.

See `docs/ROADMAP_active.md` for current open items.

## User profile

- **Oliver** is the sole owner and operator of this project.
- No direct coding experience; uses GitHub Desktop for all commits
  and pushes.
- **All code changes go through Claude Code prompts, including
  one-line edits, config changes, and workflow .yml tweaks. No
  exceptions.** If a change seems too small for a prompt, it still
  gets a prompt.
- Strong NBA domain knowledge — push back on stale basketball intel,
  but treat user-stated game facts as authoritative (see Ground
  Truth below).
- Prefers architecture discussion before Code prompts when decisions
  require judgment; proceeds directly to prompts when the path is
  clear. Flag when something needs his call vs when to proceed.
- Prefers surgical, file-scoped Code prompts with explicit
  DO NOT TOUCH lists, grep verification steps, and Docs Update
  sections that update both `ROADMAP_active.md` and
  `ROADMAP_resolved.md`.

## Repo structure

```
logger/                     Long-lived Kalshi polling process
scrapers/                   ESPN scraper + future data source scrapers
analysis/                   Analysis scripts (phase_3a_followup.py, etc.)
data/
  orderbook_snapshots/      Kalshi snapshots — committed, irreplaceable
  pbp/                      ESPN PBP — gitignored, regenerable (~35m)
  espn_wp/                  ESPN WP timeseries — gitignored, regenerable
  wp_kalshi_paired/         Audit logs + matched_games.csv committed;
                            per-game CSVs in GH artifacts (90d) + local
                            (sync via scripts/sync_paired_data.sh)
  nba_master_2025_26.csv    Game index with pre-game spreads (committed)
docs/
  THESIS.md                 Long-term project thesis and framing
  THESIS_open_questions.md  Open questions companion doc
  RESEARCH_LOG.md           Chronological findings — append, don't rewrite
  ROADMAP_active.md         What's open
  ROADMAP_resolved.md       What's done
  FEES.md                   Kalshi fee envelope analysis
  KILL_CRITERIA_draft.md    Strategy graduation / kill thresholds
  ODDS_API_INTEGRATION.md   Phase O planning doc
  analysis_outputs/         Generated analysis reports (committed)
.github/workflows/          Scheduled jobs
```

## Workflow layout

- **`kalshi_logger.yml`** — runs locally on Oliver's machine
  (not on GH Actions). The workflow file remains in-repo with
  `workflow_dispatch` only; scheduled runs were stripped
  2026-04-21 because GH Actions cron delays caused catastrophic
  game-coverage gaps. Data is committed back periodically
  (every 5 min by default) with `[skip ci]`.
- **`forward_collection.yml`** — nightly cron on GH Actions at
  10:00 UTC (03:00 PT). Runs `analysis/forward_collect.py`
  against yesterday's scoreboard, pulling ESPN PBP/WP + Kalshi
  trade tape for each settled game. Per-game CSVs
  (`*_timeseries.csv`, `*_scoring_plays.csv`) are uploaded as
  GH Actions artifacts (90-day retention), NOT committed to
  the repo. The audit log
  (`data/wp_kalshi_paired/forward_runs/<date>.log`) is
  committed nightly as a watchdog signal. Protects against
  Kalshi's ~60-day trade-tape retention cliff. Per-game data
  syncs to Oliver's Mac via `scripts/sync_paired_data.sh`.
- **`forward_collection_weekly.yml`** — Monday 11:00 UTC.
  Refreshes `matched_games.csv` only (`ticker_matcher`). The
  aggregate step (`wp_vs_kalshi_aggregate`) was moved local
  2026-04-30; Oliver runs it on demand against synced data.

## Key principles

- **Ground truth convention — two layers.**
  - *User-stated facts are authoritative.* Game results, current
    standings, player events, and any current-season facts Oliver
    states override internal model priors. If Oliver says a game
    ended a certain way, that's ground truth even if not yet
    scraped. Surface conflicts with prior assumptions explicitly
    rather than silently substituting.
  - *Research findings live in `docs/RESEARCH_LOG.md` with dates.*
    Don't overwrite prior entries — append. If a finding is
    superseded, write a new entry that explicitly references and
    supersedes the old one.

- **Agent status discipline.** When describing any agent, feature,
  or workflow, distinguish:
  - *Implemented* — code merged to repo
  - *Confirmed working* — successful production run logged and
    verified by Oliver
  - *Unverified* — merged but no confirmed successful run yet
  
  Never call a feature "operational" or claim a "first real run"
  based on code alone. If confirmation status is unknown, say so.
  Handoff notes written during a session are claims about code
  state, not production verification.
  
  Separately, roadmap hygiene: active work in
  `ROADMAP_active.md`, completed work moved to
  `ROADMAP_resolved.md` with a date stamp. Never leave completed
  items in the active file.

- **Code prompt standards.** Prompts dispatched to Claude Code
  must be:
  - Surgical and file-scoped with explicit DO NOT TOUCH lists
    (for greenfield bootstraps: "create only these files").
  - Include exact find/replace anchors or full file content where
    possible; avoid leaving implementation decisions ambiguous.
  - Include a Verification section with grep or command-line
    checks Code runs and reports back.
  - Include a Docs Update section that explicitly updates
    `ROADMAP_active.md` (removing completed item) and
    `ROADMAP_resolved.md` (adding dated entry). Both mandatory
    on every successful implementation.
  - Outputed to Oliver in Chat as a clean .md file, allowing for
    easy copy-pasting and local archiving.

- **No speculative building.** Do not design Phase 4 (live decision
  engine) code until Phase 3 produces a concrete strategy. Resist
  the urge to stub out interfaces "for later."

- **Confirm before risky actions.** Force pushes, workflow
  disables, destructive data rewrites — confirm with the user
  first even if the rest of the session has been autonomous.

## Kalshi API notes

- Market data endpoints are **unauthenticated** — no API key
  required to read orderbooks, market state, or event listings.
- Base URL: `https://api.elections.kalshi.com/trade-api/v2`
- Docs: https://docs.kalshi.com/
- The series ticker for NBA per-game markets is not fully stable;
  the logger probes a candidate list and falls back to event-title
  filtering. If discovery returns zero markets on a day we know
  games exist, the candidate list probably needs expanding — but
  confirm with a manual probe first.
- **Historical Trades endpoint** (`GET /markets/trades`
  with ticker filter) returns the complete trade tape for
  any market: trade_id, ticker, count_fp (contracts),
  yes_price_dollars, taker_side, created_time. Unauthenticated.
  Paginated (limit=1000, cursor). Confirmed working on
  HOU-LAL (93,838 trades, 29.2M contracts). Use for
  retroactive volume/execution analysis on any completed
  game. Note: the `/historical/trades` endpoint returned
  empty for recent NBA markets; `/markets/trades` with the
  same params works — documented in
  `analysis/kalshi_trades_probe.py`.

## Memory scope reminder

This Project has its own memory, separate from NBAgent. Do not
assume NBAgent-era memories (player whitelists, prop picks, model
internals, session handoffs) carry over. Treat this project's
memory as starting from the first session's context.

## Pointers

- **`docs/SESSION_CONTEXT.md` — READ FIRST.** Working-memory handoff
  doc: active mid-flight threads, pending operator actions, watchlist
  items for session start, micro-state nuance. Supplements (doesn't
  replace) RESEARCH_LOG / ROADMAP. Updated at end of each session.
- `docs/STRATEGY3_SPEC.md` — **Strategy 3 kill record.**
  Killed 2026-04-23. Entry zone subsumed by S4A extended
  range; filters noise-fitted. Original spec preserved
  below kill header for audit trail.
- `docs/STRATEGY4_SPEC.md` — **living Strategy 4 rule spec.**
  Dip-recovery swing trading with breakeven ratchet. Buy
  favorite during temporary underdog runs ($0.50–$0.75),
  exit at $0.90, ratchet stop at entry+$0.01 once price
  rises +$0.08 above entry. +$1,899/yr pooled replay-
  validated. Only active strategy in the alpha stack.
- `docs/STRATEGY1_SPEC.md` — **Strategy 1 kill record.**
  Bilateral convergence / underdog swing trade: killed
  2026-04-23. Zero positive-EV configs on 404-game dataset.
  Prior +$5,603/yr estimate was based on a simulation design
  error (mutually exclusive outcomes combined in same P&L).
- `docs/THESIS.md` — long-term project thesis and framing.
- `docs/RESEARCH_LOG.md` — current findings, what has and hasn't
  been validated yet.
- `docs/ROADMAP_active.md` — next phases.
- `docs/ROADMAP_resolved.md` — historical record of completed phases.
- `docs/ODDS_API_INTEGRATION.md` — planning doc for Odds API
  integration (Phase O).