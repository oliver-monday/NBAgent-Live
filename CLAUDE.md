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
     - **Phase 3B complete (2026-04-21):** 168 games paired
       via ticker-matcher batch infrastructure (165 competitive
       |spread|≤6). S1/S3-filtered/S4A/S4B all analyzed.
     - **Strategy 3 final state:** naive rule retracted
       (negative EV on full entries). Filtered variant
       (WP drop + fav + Q1/Q2 + upside exit) holdout-validated
       at +$578–$825/yr test-set EV. Spec:
       `docs/STRATEGY3_SPEC.md` §8.
     - **Strategy 4 confirmed:** Dip-recovery swing trading.
       +$1,886/yr (S4A fav, best config). Spec:
       `docs/STRATEGY4_SPEC.md`. Position management tested
       (baseline optimal). Prior-weighting tested (not useful).
       S4B underdog hybrid +$1,105/yr, needs more data.
     - **Phase 4a unlocked.** Three validated alpha sources
       (S1 +$1,608, S4A +$1,886, S3-filtered +$578–$825),
       combined ~$4,072–$4,319/yr.
   - Phase 3B formal COMPLETE (see above).
4. **Phase 4** — Live decision engine. Not scoped until
   Phase 3 produces a validated strategy spec.

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

`kalshi_logger.yml` runs three daily blocks (06:30 / 11:30 / 16:30 PT),
each capped at ~5h15m to stay under GitHub Actions' 6h job limit. The
process self-terminates after 15 min if no active NBA game markets are
found, so off-days cost almost nothing.

Data is committed back to the repo periodically (every 5 min by default).
`[skip ci]` is used in the commit message to avoid triggering other
workflows.

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
- `docs/STRATEGY3_SPEC.md` — **living Strategy 3 rule spec.**
  Current best-guess entry/exit rules, execution preferences,
  operating parameters, and graduation status. The primary
  deliverable of Phase 3. Supersedes `docs/strategy3_assessment.md`.
- `docs/STRATEGY4_SPEC.md` — **living Strategy 4 rule spec.**
  Dip-recovery swing trading: buy favorite during temporary
  underdog runs ($0.50–$0.75), exit at $0.90. Best single
  strategy by annual EV (+$1,886/yr). Includes false-summit
  exit analysis, prior-weighting results, position management
  conclusions.
- `docs/THESIS.md` — long-term project thesis and framing.
- `docs/RESEARCH_LOG.md` — current findings, what has and hasn't
  been validated yet.
- `docs/ROADMAP_active.md` — next phases.
- `docs/ROADMAP_resolved.md` — historical record of completed phases.
- `docs/ODDS_API_INTEGRATION.md` — planning doc for Odds API
  integration (Phase O).