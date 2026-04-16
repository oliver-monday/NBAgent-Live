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

## Key principles carried over from NBAgent

- **Ground truth convention.** Validated findings live in
  `docs/RESEARCH_LOG.md` with dates. Don't overwrite prior entries —
  append. If a finding is superseded, write a new entry that explicitly
  references and supersedes the old one.
- **Agent status discipline.** Active work goes in `ROADMAP_active.md`.
  Completed work moves to `ROADMAP_resolved.md` with a date stamp.
  Never leave completed items in the active file.
- **No speculative building.** Do not design Phase 4 (live decision
  engine) code until Phase 3 produces a concrete strategy. Resist the
  urge to stub out interfaces "for later."
- **Confirm before risky actions.** Force pushes, workflow disables,
  destructive data rewrites — confirm with the user first even if the
  rest of the session has been autonomous.

## Kalshi API notes

- Market data endpoints are **unauthenticated** — no API key required to
  read orderbooks, market state, or event listings.
- Base URL: `https://api.elections.kalshi.com/trade-api/v2`
- Docs: https://docs.kalshi.com/
- The series ticker for NBA per-game markets is not fully stable; the
  logger probes a candidate list and falls back to event-title filtering.
  If discovery returns zero markets on a day we know games exist, the
  candidate list probably needs expanding — but confirm with a manual
  probe first.

## Pointers

- `docs/RESEARCH_LOG.md` — current findings, what has and hasn't been
  validated yet.
- `docs/ROADMAP_active.md` — next phases.
- `docs/ROADMAP_resolved.md` — historical record of completed phases.
