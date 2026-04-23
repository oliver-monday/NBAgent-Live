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

## 2026-04-23 session handoff (S3 reframe + S4A ratchet engine)

### Where to catch up first (fresh-session reading order)

1. `CLAUDE.md` — auto-loaded, points to this doc
2. This file
3. `docs/STRATEGY4_SPEC.md` §5A — new ratchet section, load-bearing
4. `docs/STRATEGY1_SPEC.md` — kill record (2026-04-23)
5. Last ~3 entries of `docs/RESEARCH_LOG.md` — 2026-04-23 arc
6. `docs/ROADMAP_active.md` — very short; Phase 4a live-verify is
   the only substantive open thread
7. `engine/replay.py` module docstring — reconciliation between
   target-level and observed-price fill models (matters any time
   you touch S4A numbers)

### Just-completed

The session did three passes of S3 reframing plus engine work.
Full narrative in `docs/analysis_outputs/s3_reframed_extended_entry.md`
(Parts 1–15) and 2026-04-23 RESEARCH_LOG entry.

- S1 bilateral + S4B underdog hybrid both killed (separate analyses
  earlier same day). Specs: `STRATEGY1_SPEC.md`, `STRATEGY4_SPEC.md`
  §8.
- S3 reframed as $0.40–$0.75 extended entry tail of S4A. Passes 1
  and 2 found no config that beats the baseline $0.50–$0.75 band.
- Pass 3: **breakeven ratchet stop** validated. +$0.79/entry,
  +$579/yr pool-level on 404 games. Holdout 6/6 seeds positive.
- **Engine implementation:** `engine/position_manager.py`
  extended with ratchet state; `engine/replay.py` validates both
  `--ratchet 0.08` (default, recommended) and `--ratchet 0`
  (legacy baseline) modes PASS against expected numbers.
  `engine/live_runner.py` exposes `--ratchet 0.08` flag.

### Active / pending operator actions

- [ ] **Phase 4a live verification** — paper-trading engine is
  replay-validated but still "unverified live." First real
  session should run `python -m engine.live_runner --ratchet
  0.08` on an active game night and confirm the journal
  records align with expected signal firings. Until this
  happens, the engine is merged but unverified.
- [ ] **Multi-strategy simulation.** S4A (core+ratchet) and
  S3-filtered operate in overlapping price zones ($0.40–$0.75
  vs $0.40). Concurrent-position behavior has not been
  simulated. Needs scoping before Phase 4c (sizing/bankroll).
- [ ] **5.5–6.0 spread bucket outperformance** (+$6.17
  mean/$3,570 annual on n=37) remains an unresolved open
  question — structural sweet spot or small-sample noise?
  Answerable with existing 404-game dataset; not time-critical.

### Watchlist (check at session start)

- **Kalshi logger status** — runs locally (not GH Actions).
  `python3 -m analysis.logger_health_check` should show recent
  snapshots on today's games. If stale >2 min, logger needs
  restart (`caffeinate -dimsu` wrapper to prevent App Nap).
- **Forward-collection cron** — nightly 10:00 UTC, protects
  the ~60-day trade-tape retention cliff. Per-night audit at
  `data/wp_kalshi_paired/forward_runs/<date>.log`. Should run
  without intervention; check that yesterday's log is present
  and non-empty on game days.
- **Git state** — `git pull --ff-only`. Forward-collection cron
  auto-commits with `[skip ci]` each morning.

### Micro-state worth preserving

- **Engine uses target-level fills ($0.90 exactly), not
  observed overshoot price.** This is load-bearing for any
  comparison against older analyses. Historical:
  - `strategy4a_drawdown.md` baseline = $+2.83 mean / $+1,193
    annual (observed-price model).
  - `engine/replay.py --ratchet 0` = $+3.13 mean / $+1,320
    annual (target-level model, same 311 entries).
  - The $0.30/entry gap is the overshoot on target ticks; the
    engine model is more realistic for resting limit orders.
  - The "true ratchet incremental under consistent model" is
    +$579/yr ($1,899 − $1,320), NOT the +$706/yr the drawdown
    analysis reported (which compared target-level ratcheted
    vs observed-price baseline — apples-to-oranges).
  - Reconciliation documented at length in `engine/replay.py`
    module docstring.
- **Engine fee split:** maker on entry + target + ratchet_stop
  (all are resting limit orders), taker on full_stop (flash
  crash, no time to post). Live execution should match this
  model. Scenario B from the stop-execution study (resting
  NO buy at $0.60 with 60s taker fallback) is the recommended
  implementation for the $0.40 full stop.
- **Ratchet mechanic is one-way latch.** Once
  `highest_since_entry ≥ entry + $0.08` triggers, stop moves
  to `entry + $0.01` and stays there. Price falling back
  below the trigger does NOT un-latch.
- **`--ratchet` CLI semantics:** default is 0.08 on both
  `replay.py` and `live_runner.py`. `--ratchet 0` disables
  (legacy baseline). Any non-zero positive float works but
  only 0.08 and 0 have expected-numbers tables in replay's
  PASS/FAIL validator.
- **Replay dataset = 404-game `load_kalshi_games_all_spreads`**,
  not the old 171-game core. Old replays that expected
  166 entries / $+1,708 annual reflect the core-only dataset
  and should be treated as historical.
- **S3 graduation retraction** — STRATEGY3_SPEC.md §8 carries
  the canonical narrative. The filtered variant (+$578–$825/yr)
  is what's validated; the naive rule was retracted. Easy to
  lose track of when reading older RESEARCH_LOG entries.
- **S1 + S4B kill records** — both killed 2026-04-23. S1's
  prior +$5,603/yr estimate was a simulation design error
  (mutually exclusive outcomes combined in same P&L).
  S4B's prior +$1,105/yr collapsed to +$148/yr on the
  404-game revalidation. Any doc or script referencing
  positive S1/S4B EVs is stale.

### Known-stale references to watch for

- Anything quoting the old S4A alpha stack with S1 or S4B
  positive (pre-2026-04-23).
- Anything quoting $+2.83 baseline mean P&L for S4A without
  the target-level vs observed-price reconciliation.
- Anything calling S4A position management "baseline optimal"
  without also mentioning the ratchet overlay — the ratchet is
  a stop-management change, not a position-sizing change, but
  the "no position management helps" conclusion needed the
  §5A qualifier.

### Open questions pending operator direction

- **When to run first live paper-trading session.** Engine is
  green in replay; next game night with multiple tracked
  tickers is the natural trigger. Oliver to decide whether to
  schedule a dedicated observation session or let the cron /
  live_runner run unattended with journal review after.
- **Multi-strategy capital allocation.** S4A (ratcheted) and
  S3-filtered can both fire on the same game. Bankroll sizing
  spec not yet written. Deferrable until post-first-live-run,
  but blocks Phase 4c real-money deployment.

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
