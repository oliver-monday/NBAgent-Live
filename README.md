# NBAgent-Live

Live Kalshi NBA orderbook data capture and live-trading research.

This is a **separate project** from NBAgent. NBAgent is the broader research
codebase (Stern WP model, minute-level analysis, bilateral dip study).
NBAgent-Live is the narrower sibling focused on live market data and
eventual live decision-making.

## Purpose

Capture Kalshi per-game NBA market orderbook snapshots during games so that
future research has a historical record of live market pricing. Kalshi only
exposes current state via its public API — there is no historical archive,
so data must be logged forward.

## Repo layout

```
logger/                       Python polling process + helpers
data/orderbook_snapshots/     JSONL snapshots, one file per UTC date
docs/                         Research log, active/resolved roadmaps
.github/workflows/            Scheduled logger runs on GitHub Actions
```

## Current phase

Research phase. No agent/frontend infrastructure will be built until the
research produces a validated strategy spec. See
[docs/ROADMAP_active.md](docs/ROADMAP_active.md) for what's next and
[docs/RESEARCH_LOG.md](docs/RESEARCH_LOG.md) for current findings.

## For AI agents

See [CLAUDE.md](CLAUDE.md) for working-with-this-repo context.

## Data access

Kalshi market data endpoints are unauthenticated — no API key needed to
run the logger. The base URL is `https://api.elections.kalshi.com/trade-api/v2`
([Kalshi docs](https://docs.kalshi.com/)).
