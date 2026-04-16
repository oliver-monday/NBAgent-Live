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
until research produces a validated strategy spec.** The near-term job is:

1. Capture live Kalshi orderbook data forward (Phase 1 — done).
2. Ingest ESPN PBP + WP for historical grounding (Phase 2).
3. Re-run the bilateral dip analysis on PBP foundation with Kalshi
   price data overlaid (Phase 3).
4. Only then consider a live decision engine (Phase 4).

See `docs/ROADMAP_active.md`.

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
logger/kalshi_logger.py     Long-lived polling process
logger/__init__.py          Package marker
data/orderbook_snapshots/   One JSONL file per UTC date, appended by logger
docs/RESEARCH_LOG.md        Chronological findings — append, don't rewrite
docs/ROADMAP_active.md      What's open
docs/ROADMAP_resolved.md    What's done
.github/workflows/          Scheduled logger invocations
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

## Memory scope reminder

This Project has its own memory, separate from NBAgent. Do not
assume NBAgent-era memories (player whitelists, prop picks, model
internals, session handoffs) carry over. Treat this project's
memory as starting from the first session's context.

## Pointers

- `docs/RESEARCH_LOG.md` — current findings, what has and hasn't
  been validated yet.
- `docs/ROADMAP_active.md` — next phases.
- `docs/ROADMAP_resolved.md` — historical record of completed phases.