# Active Roadmap

## Phase 2 — ESPN ingest

- Multi-season backfill (2014-2024) — execute after current-season
  analysis pipeline validates end-to-end and Phase 3B produces
  first paired findings. Low urgency.

## Phase 3 — Analysis on ESPN WP foundation

- **Phase 3B** — paired Kalshi + ESPN analysis. Blocked on
  ≥5-10 games of live Kalshi data accumulation during 2026
  playoffs. Covers §1.1 Kalshi-vs-ESPN residual, §2.1 liquidity
  characterization, §2.5 realized spread distribution, §6.5 MM
  behavior at extremes, §6.6 flow isolation (Kalshi-only lens
  — Odds API provides a cleaner test of the same question in
  Phase O3).
- **§1.4 retirement analyses** — three spread-anchoring tests
  runnable from existing ESPN data, no Kalshi dependency. See
  `docs/THESIS_open_questions.md` §1.4. Potentially restructures
  Strategy 2's entry rule (spread-conditional residual) and
  Strategy 3's exit target (opening line vs 50/50).
- **Empirical WP model** — fit logistic on (margin,
  time_remaining, spread). Test whether the ESPN +3pp residual
  survives a properly fitted empirical model or is an artifact
  of ESPN's specific modeling choices. Lower priority than 3B
  and §1.4.

## Phase 4 — Live decision engine (speculative)

- Do not design until Phase 3B produces a validated strategy spec.
- Will read live Kalshi + live PBP, generate signals, alert for
  manual paper-trading first.

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
