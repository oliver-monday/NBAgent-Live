# SESSION_CONTEXT.md

**Read this first when starting a new session.** Working-memory
handoff doc — captures transient state that doesn't belong in
permanent records but matters for continuity.

## Purpose and discipline

**Use this doc for:**
- Mid-flight work-threads not yet closed in `ROADMAP_resolved.md`
- Pending operator actions (things Oliver needs to run or decide)
- Short-lived watchlist items to check at session start
- Micro-state / contextual nuance from recent sessions that would take
  meaningful time to rediscover from code + docs

**Do NOT use this doc for:**
- Permanent findings → `docs/RESEARCH_LOG.md`
- Phase-level roadmap status → `docs/ROADMAP_active.md` /
  `docs/ROADMAP_resolved.md`
- Strategic framing → `docs/THESIS.md` /
  `docs/THESIS_open_questions.md`
- Analysis outputs → `docs/analysis_outputs/`

**Update cadence:** at the end of each session where substantive work
happened, or when the user signals "wrapping up." A session is
expected to add an "## YYYY-MM-DD session handoff" block to the top
and trim stale sections from prior blocks. Don't append forever —
this doc should stay under ~300 lines.

---

## 2026-04-19 session handoff (flagship Strategy 3 arc)

### Where to catch up first (fresh-session reading order)

1. `CLAUDE.md` — auto-loaded, points to this doc
2. This file (`docs/SESSION_CONTEXT.md`)
3. `docs/ROADMAP_active.md` — what's open right now
4. Last ~5 entries of `docs/RESEARCH_LOG.md` — most recent findings
5. Recent commits: `git log --oneline -20`

That's ~15 min of reading to get to 95% of session context.

### Just-completed (in roughly chronological order)

This session produced the full Strategy 3 validation arc:

- **Strategy 1 sportsbook backfill recalibration** — Established
  ESPN ⟂ real-money markets (+12.58pp compression). Strategy 1 at
  SB-denominated thresholds: best op point (0.25, 0.35), 17.7%
  opportunity rate, $6.55 EV/game (vs ESPN $23.23/game).
- **Strategy 2 preliminary kill signal** — Residual vs Kalshi is
  negative; ESPN-vs-actual residual absorbed by compression.
- **HOU-LAL deep dive (n=1)** — First real Kalshi oscillation
  characterization. Mid-range re-run (Section 3B) found $14.55 mean
  net maker-maker at (0.35, 0.50).
- **Favorite-side analysis** — HOU-LAL blended EV $33.25 at entry
  0.65 (no resolution outcomes, backstop unused). Game-flow sweep
  revealed the favorite-side backstop is *adversely selected*: 62
  wins vs 331 losses when held to resolution (84% loss rate).
- **Game-flow trajectory (N=1,234)** — 63.4% of all games produce
  ≥1 mid-range round-trip on ESPN WP; 75.2% at |spread|≤6.
  Comeback + BnF buckets contribute ~80% of yield.
- **Odds API timeseries script** — Built + plan-only verified.
  **Full run pending operator approval** (see below).

All of the above is already in RESEARCH_LOG and ROADMAP.

### Active / pending

- [ ] **Odds API timeseries full run** — `analysis/strategy3_odds_api_timeseries.py`.
  15 games, ~5,564 credits (≈55% of ~10k monthly budget). Oliver runs
  with `ODDS_API_KEY` in env. Plan-only output in git history. After
  run: write RESEARCH_LOG entry + ROADMAP sub-bullet with the real
  survival-rate numbers. The spec has a fill-in-later template.
- [ ] **Favorite-side hard-stop rule design** (deferred) — the 84%
  resolution-loss rate from the game-flow sweep suggests Strategy 3
  favorite-side needs either (a) a hard stop at entry − $0.05 or
  similar, or (b) a tighter entry threshold (e.g., 0.50 not 0.60).
  Not yet scoped.
- [ ] **§1.4 retirement analyses** — still listed in
  `THESIS_open_questions.md` as three runnable sub-analyses. Current
  status: deprioritized (the strategy question is answered by the
  sportsbook backfill; retirement analyses would only inform ESPN
  model mechanics).
- [ ] **Phase 3B formal** — paired Kalshi + ESPN analysis on ≥10
  games. Blocked on Kalshi data accumulation. Currently have n=4
  usable from Play-In (CHA-ORL, GSW-PHX, TOR-CLE, HOU-LAL).

### Watchlist (check at session start)

- **Kalshi logger status** — runs locally now (not GH Actions).
  Command: `python3 -m analysis.logger_health_check`. Should show
  recent snapshots on today's games. If stale >2 min, logger needs
  restart.
- **New per-event files** — `ls -la data/orderbook_snapshots/`.
  Files named `KXNBAGAME-YYMMMDD<AWAY><HOME>.jsonl` per game. Round 1
  playoff games being tracked.
- **Git state** — `git pull --ff-only`. Oliver sometimes commits
  via GitHub Desktop between sessions. Logger's auto-commits also
  land on main every 5 min when active.

### Micro-state worth preserving

- **Logger bug fixed mid-session** (commit `f79aa7b`): `git_commit_push()`
  now does `git pull --rebase --autostash` before push, with retry.
  Before the fix, any concurrent push to main (me via Claude Code,
  Oliver via Desktop) caused the logger's next push to fail
  permanently until runner restart. Now self-heals.
- **Snapshot data is gitignored** — `data/orderbook_snapshots/` added
  to `.gitignore` (commit `8e0c22c`). Logger's `git add data/` now
  silently skips snapshots. This is intentional (Oliver backs up
  externally). Analysis scripts that load snapshots work on local
  files only.
- **Per-event file format** — Logger writes one file per Kalshi
  event_ticker: `KXNBAGAME-26APR17CHAORL.jsonl` etc. Both home and
  away tickers land in the same file, distinguished by the `ticker`
  field. Switched from UTC-date split 2026-04-19. Some older data
  (4/17–4/18 games) still lives in date-based files
  (`2026-04-17.jsonl` etc.). Analysis scripts that need HOU-LAL data
  specifically load from the date files.
- **ESPN data files are gitignored** — `data/espn_wp/*.jsonl` and
  `data/pbp/*.jsonl`. Regenerable via
  `python -m scrapers.espn_backfill` in ~35 min. The single 401810469
  game (2026-01-20 CHI-LAC) has an empty WP file — ESPN feed gap,
  not a scraper bug. 9 total empty WP files (4 All-Star exhibitions,
  4 postponements, 1 real gap). `espn_backfill.py`'s skip logic
  treats empty files as successful, so re-run doesn't retry the gap
  game. Known small bug; not urgent to fix.
- **Tip detection in HOU-LAL script is ESPN-anchored**, not auto-
  detected. Volume-rate auto-detection had edge cases from pre-tip
  flow spikes + logger-gap boundaries on the specific HOU-LAL
  dataset. Multi-game Strategy 3 generalization needs a more robust
  detector (rough plan: "sustained 10-min window ≥100 fp/sec + mid
  variance threshold," or ESPN PBP wallclock-anchor).
- **`_BBREF_NAME_TO_ABBR` in `analysis/phase_3a_followup.py`** is the
  canonical name→abbrev map. `_ODDS_API_NAME_TO_ABBR` in Strategy 1
  backfill is a copy. `_ABBR_NORM` in `scrapers/espn_scraper.py` is
  for ESPN abbrev→standard (different shape — abbrev→abbrev, not
  name→abbrev).
- **ODDS_API_KEY is not in my shell env**. Oliver has it locally
  (`echo $ODDS_API_KEY` works for him, not me). Full Odds API runs
  always happen Oliver-side, never Claude-side.

### Open questions pending operator direction

- Should the Odds API timeseries scrape run now, or wait for more
  playoff games to accumulate first (so we can substitute recent
  games for older ones)?
- How hard should the favorite-side hard-stop design dispatch go?
  Cheap option: just add a `stop_at` parameter to
  `fav_trip_outcomes`. Elaborate option: explore the MAE-vs-exit
  tradeoff across a grid of stop-loss thresholds.
- Phase 4 scoping — the roadmap has the full framework documented
  (core loop, components, staged rollout) but nothing is active.
  Gated on Phase 3B producing a validated strategy spec. Current
  Strategy 1 at $6.55/game and Strategy 2 killed suggests we may
  actually be close to a Phase 4 go/no-go moment after Odds API
  timeseries validates the Strategy 3 survival rate.

### Session-health metrics

- Commits this session (rough count): ~25
- Files created: ~8 (mostly `analysis/strategy3_*.py` and their
  `docs/analysis_outputs/*.md` reports)
- Files modified: core docs all touched (RESEARCH_LOG, ROADMAP
  active/resolved, THESIS_open_questions, KILL_CRITERIA, CLAUDE.md)
- Analysis dataset covered: full 1,234-game 2025-26 regular season
  on ESPN, n=4 playoff games on Kalshi, n=30 games on Odds API
  historical (backfill), n=15 games pending on Odds API timeseries

---

## Template for future session blocks

Copy this block structure at the top of the file, above the most
recent entry. Trim or remove stale blocks as they age out.

```markdown
## YYYY-MM-DD session handoff (short label)

### Just-completed

- ...

### Active / pending

- [ ] ...

### Watchlist (check at session start)

- ...

### Micro-state worth preserving

- ...

### Open questions pending operator direction

- ...
```
