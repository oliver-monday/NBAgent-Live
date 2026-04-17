# Active Roadmap

## Phase 2 — ESPN ingest

- ~~PBP scraper per completed gameId → `data/pbp/{gameId}.jsonl`~~ ✓ Phase 2a
- ~~ESPN WP timeseries scraper per completed gameId → `data/espn_wp/{gameId}.jsonl`~~ ✓ Phase 2a
- ~~2025-26 season backfill utility~~ ✓ Phase 2b (utility built; full run pending)
- ~~Pre-game spread integration~~ ✓ Inherited from NBAgent via `nba_master_2025_26.csv`
- Full 2025-26 backfill execution — run `espn_backfill.py`, commit data
- Multi-season backfill (2014-2024) — execute after 2025-26 analysis validates approach

## Phase 3 — Analysis re-run on PBP foundation

- Replicate bilateral dip analysis on PBP granularity (sanity check vs minute-level)
- Add pre-game spread filter for ex-ante competitive universe
- Fit empirical WP model (logistic: margin × time_remaining × spread) — check if Stern residual survives

## Phase 4 — Live decision engine (speculative)

- Do not design until Phase 3 produces validated strategy spec
- Will read live Kalshi + live PBP, generate signals, alert for manual paper-trading first

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
