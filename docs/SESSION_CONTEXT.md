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
- Strategy specs → `docs/STRATEGY3_SPEC.md` / `docs/STRATEGY4_SPEC.md`

**Update cadence:** at the end of each session where substantive
work happened, or when the user signals "wrapping up." Add the
new handoff block at top; trim or remove stale blocks beneath.
Keep this doc under ~300 lines.

---

## 2026-04-21 session handoff (Phase 3B completion arc)

### Where to catch up first (fresh-session reading order)

1. `CLAUDE.md` — auto-loaded, points to this doc
2. This file (`docs/SESSION_CONTEXT.md`)
3. `docs/STRATEGY4_SPEC.md` — **newest; highest-EV strategy**
4. `docs/STRATEGY3_SPEC.md` — §8 has the retraction + filter
   validation narrative (entire previous graduation verdict was
   retracted, then filtered variant was validated)
5. `docs/ROADMAP_active.md` — what's open now (very short after
   this session's cleanup)
6. Last ~6 entries of `docs/RESEARCH_LOG.md` — dense 2026-04-21
   arc from failed-entry through holdout validation
7. Recent commits: `git log --oneline -25`

That's ~25 min of reading to get to 95% of session context.

### Just-completed (the Phase 3B completion arc)

This session did the entire Phase 3B formal arc in one continuous
working session, going from "2 usable paired Kalshi games" to
"168 paired games + three validated deployment-ready strategies."
Chronologically:

1. **Kalshi historical-trades endpoint probe** (HOU-LAL). Confirmed
   `/markets/trades` returns full tape for settled markets.
2. **Multi-game oscillation analysis on 4/19 R1G1** (n=4 games).
3. **Timeout execution analysis** (HOU-LAL + ORL@DET) — timeouts
   are execution windows not directional signals.
4. **ESPN scoring-run pattern catalog** (N=549 competitive).
5. **Per-game WP-vs-Kalshi paired analysis script**
   (`wp_vs_kalshi_paired.py`) with auto-resolvers for
   game-id / Kalshi-ticker / spread from team+date.
6. **Ticker matcher + batch mode + aggregation infrastructure**
   (`ticker_matcher.py`, `wp_vs_kalshi_aggregate.py`).
7. **165-game batch completed** (after discovering Kalshi's ~60-day
   trade-tape retention cliff — initial 100-game sample became 26
   viable, then expanded to the full 165 viable competitive games
   in the window).
8. **Strategy 3 graduation eval** — initially GRADUATED on 6
   criteria.
9. **Failed-entry analysis** — retracted that verdict: true EV
   −$4.57/entry counting held-to-loss outcomes.
10. **Stop-loss sweep** (21 levels) — best still −$1.27/entry.
11. **Upside-capture grid** (96 configs) — best still −$0.59/entry.
12. **Entry-filter sweep** (32 configs) — **first positive EV**,
    8 of 32 configs positive. Best +$3.41 mean / +$578 annual.
13. **Strategy 4 analysis landed** — false-summit, dip-recovery
    sweep (1,200 configs), run-capture sweep, cross-strategy
    comparison. S4A best: **+$1,886/yr** — higher than any
    other single strategy.
14. **Prior-weighting test for S4A** (Part 5) — null result,
    filter doesn't help.
15. **Position management test for S4A** (Part 6) — null result,
    baseline optimal across 17 tested variants.
16. **S3 holdout validation** — 110/55 train/test split, 6-seed
    stability. **VALIDATED: 4 of 6 seeds positive** on test.
    Test-set annual EV +$825.
17. **STRATEGY4_SPEC.md created** as living spec.
18. **End-of-session doc health check** (you are reading the
    output) — cleaned contradictions across 7 files, deduped
    ROADMAP_resolved entries, consolidated THESIS_open_questions
    resolution log, rewrote this file.

### Current Phase 4a-ready alpha stack

All three strategies operate in different price zones and can run
simultaneously without conflict.

| Strategy | Annual EV | Confidence |
|---|---:|---|
| S1 bilateral | +$1,608 | Confirmed, deployment-ready |
| S4A dip-recovery | +$1,886 | Confirmed, deployment-ready |
| S3 filtered | +$578–$825 | Holdout-validated (4/6 seeds) |
| S4B underdog hybrid | +$1,105 | Positive, needs more data |
| **Combined conservative** | **+$4,072–$4,319** | — |

Spec references:
- S1: THESIS.md §Four strategy layers / §1 (no standalone spec doc)
- S3 filtered: STRATEGY3_SPEC.md §8 + §2 (post-retraction)
- S4A / S4B: STRATEGY4_SPEC.md
- Phase 4a gating: KILL_CRITERIA_draft.md §Project-level decisions

### Active / pending

- [ ] **Phase 4a — signal alerts implementation.** Gated now
  unlocked per the three validated strategies. Needs:
  live ESPN PBP/WP polling (existing scraper is post-game
  only), live Kalshi bid-feed integration (logger already
  has this), and alert layer (push/SMS/Slack). See
  ROADMAP_active.md §Phase 4 components list.
- [ ] **Forward-collection discipline.** Kalshi retains trade
  tape only ~60 days. Any game we want to study retrospectively
  must be captured within ~50 days of settlement. Worth a cron
  that runs `ticker_matcher.py` on last-night's games and
  kicks `wp_vs_kalshi_paired.py --batch` for recent dates.
- [ ] **S4B underdog validation.** Currently +$1,105/yr but
  leans on ~13% hold-to-resolution win rate. Needs 2-3× more
  games to confirm. Defer to Phase 4a observation; don't
  deploy S4B first.
- [ ] **S3 filter tightness.** Best test-set config uses WP+fav+
  period+upside and produces only ~19 test entries per split.
  Wide CI on the EV estimate. Second-best config (osc+wp /
  upside) had more entries and also validated. Consider the
  osc+wp variant as a "more opportunities" alternative once
  more games accumulate.
- [ ] **Kalshi per-game files** continue to accumulate in
  `data/orderbook_snapshots/` as logger runs locally. These
  complement the retrospective 168-game paired dataset with
  live orderbook depth that the trade-tape endpoint doesn't
  expose.

### Watchlist (check at session start)

- **Kalshi logger status** — runs locally now (not GH Actions).
  Command: `python3 -m analysis.logger_health_check`. Should show
  recent snapshots on today's games. If stale >2 min, logger needs
  restart.
- **Trade-tape retention cliff** — ~60 days. If starting a session
  that touches any game older than that, trades are unreachable
  via `/markets/trades`. 168-game dataset in `data/wp_kalshi_paired/`
  is already snapshotted.
- **Git state** — `git pull --ff-only`. Oliver sometimes commits
  via GitHub Desktop between sessions. Logger's auto-commits also
  land on main every 5 min when active.

### Micro-state worth preserving

- **The ~60-day Kalshi trade-tape retention cliff** is the key
  infrastructure constraint. Discovered mid-session via empirical
  binary search (2026-02-20 has data, 2026-02-11 doesn't). 165 of
  the original 100-game competitive sample were viable after the
  cliff was applied; then we re-ran the matcher without `--sample`
  on the 60-day window to get 165 total.
- **The graduation verdict retraction** is easy to lose track of
  when reading older RESEARCH_LOG entries. STRATEGY3_SPEC.md §8
  now carries the canonical narrative; if another doc contradicts
  it, trust the spec.
- **Failed-entry analysis revealed the full EV accounting** that
  the graduation eval missed: 60.9% of entries complete at
  +$15.49, 39.1% held to loss at −$35.82. The losses outweighed
  wins 2.3× in magnitude, producing net −$4.57. This is the key
  mental model for why S3 naive fails and why entry filters
  matter.
- **S4A works because of the mirror principle.** S3 buys when the
  market has lost faith ($0.40 = 40% of those are right to be
  afraid). S4A buys the still-believed favorite during temporary
  disruptions ($0.50-$0.75 = 53% recover to $0.90). Different
  structural bet.
- **Prior-weighting filter for S4A was the expected hypothesis
  that failed.** Entries *above* pre-game prior actually have the
  highest hit rate (62% vs 34% for entries $0.05–$0.10 below).
  S4A's signal is "dip from trailing max," not "distance from
  pre-game anchor."
- **Position management for S4A is optimal at baseline.** 17
  averaging-in/out variants all underperform. Fee multiplication
  + partial-then-stop new loss mode + undersized wins all compound.
  Keep the Phase 4a execution spec simple: single limit buy,
  single limit sell or stop.
- **S1 + S3-filtered + S4A are in different price zones** — S1
  below $0.40 bilateral, S3 filtered at $0.40 entry with filters,
  S4A at $0.50–$0.75. A single game can trigger multiple strategies
  at different moments. Capital allocation across concurrent
  positions is not yet designed.
- **ORL@DET upset (4/19)** was the key canonical competitive game
  for early validation — DET favored, ORL won, both sides oscillated
  cleanly through the mid-range zone. The paired-analysis compression
  numbers were tightened significantly by including this game.

### Known stale content (now fixed in this cleanup)

The end-of-session audit found and fixed:
- STRATEGY3_SPEC.md §2, §6, §8 (graduation framing)
- KILL_CRITERIA_draft.md added S4 section + retraction note
- ROADMAP_active.md removed stale "n=4 usable" / "2/10
  graduation" framing
- THESIS.md added Strategy 4 layer, bumped S2 to formal kill
- CLAUDE.md replaced "2/10" with Phase 4a unlock framing
- ROADMAP_resolved.md deduped two 2026-04-20 "WP vs Kalshi
  script" entries
- THESIS_open_questions.md added consolidated 2026-04-21
  resolution log entry covering §1.1, §1.2, §1.3, §1.4, §2.2,
  §2.5, §6.5, §6.6, §3.1

### Open questions pending operator direction

- **How aggressively to start Phase 4a.** Live paper-trading
  alerts for S1 + S4A + S3-filtered can begin immediately; S4B
  should be observed but not acted on until more data. Oliver
  to decide: push all three now, or start with the two
  highest-confidence (S1 + S4A) and add S3-filtered after a
  forward-playoff sanity check?
- **Forward-collection cron.** Simple daily cron to
  ticker-match last night's games and batch-fetch their trade
  tapes + run `wp_vs_kalshi_paired.py` is a few hours of work.
  Should this be the first Phase 4a infrastructure build, or
  is it deferrable?
- **Multi-strategy capital allocation.** Never simulated. At
  100 contracts/strategy, three concurrent positions in the
  same game = 300 contracts exposed. Bankroll sizing spec
  needs scoping before Phase 4c.

### Session-health metrics

- Session duration: many turns, spanning the full Phase 3B arc
- Commits this session: ~40+ analysis scripts + doc updates
  (mostly uncommitted locally — Oliver commits via GitHub
  Desktop between sessions)
- Files created this session (analysis/): `ticker_matcher.py`,
  `wp_vs_kalshi_paired.py`, `wp_vs_kalshi_aggregate.py`,
  `strategy3_graduation_eval.py`, `strategy3_failed_entries.py`,
  `strategy3_stoploss_sweep.py`, `strategy3_upside_capture.py`,
  `strategy3_entry_filters.py`, `strategy3_holdout_validation.py`,
  `strategy4_dip_recovery.py`, `kalshi_trades_probe.py`,
  `strategy3_oscillation_multi.py`, `timeout_execution_analysis.py`,
  `scoring_run_trajectories.py`, `espn_scoring_run_catalog.py`
- Files created this session (docs/): `STRATEGY3_SPEC.md` (earlier
  session), `STRATEGY4_SPEC.md` (this session), plus numerous
  `docs/analysis_outputs/*.md` reports
- Data added: 168-game paired dataset in `data/wp_kalshi_paired/`
  (timeseries CSVs + scoring-plays CSVs + JSON caches per game
  + matched_games.csv + aggregate summaries)
- Analysis dataset covered at session end: 168 paired games (165
  competitive), ~47,000 in-game 30-second bins, ~20,000 scoring
  plays

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
