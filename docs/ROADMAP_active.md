# Active Roadmap

## Phase 2 — ESPN ingest

- ~~PBP scraper per completed gameId → `data/pbp/{gameId}.jsonl`~~ ✓ Phase 2a
- ~~ESPN WP timeseries scraper per completed gameId → `data/espn_wp/{gameId}.jsonl`~~ ✓ Phase 2a
- 2025-26 season backfill — scrape all completed regular season + playoff games
- Multi-season backfill (2014-2024) — execute after 2025-26 pipeline validated
- Pre-game spread integration from external source

## Phase 3 — Analysis re-run on PBP foundation

- Replicate bilateral dip analysis on PBP granularity (sanity check vs minute-level)
- Add pre-game spread filter for ex-ante competitive universe
- Fit empirical WP model (logistic: margin × time_remaining × spread) — check if Stern residual survives

## Phase 4 — Live decision engine (speculative)

- Do not design until Phase 3 produces validated strategy spec
- Will read live Kalshi + live PBP, generate signals, alert for manual paper-trading first
