# ODDS_API_INTEGRATION.md — Research Design & Scope

Planning document for integrating The Odds API as a secondary data
source in NBAgent-Live. Written 2026-04-17 before any code or
data collection. Implementation queued for a subsequent session.

## Purpose

The Odds API provides live and historical US sportsbook pricing
(moneyline, spreads, totals, quarter markets) across ~12
bookmakers. Integrating it into NBAgent-Live gives us:

1. A **stronger consensus benchmark** for testing §1.1 (does
   Kalshi mirror market consensus?) than ESPN WP alone.
2. The **cleanest available test** of §1.4 (is ESPN WP
   spread-anchored, or is that property of pricing in general?)
   via live sportsbook spread evolution.
3. **Flow vs game-state disambiguation** for §6.6 — if Kalshi
   moves while sportsbooks don't, that's flow, not news.
4. A **"when to trust the proxy" gating signal** via cross-book
   variance. Tight consensus ⇒ Kalshi-vs-consensus comparison is
   meaningful; wide consensus ⇒ there is no "proxy" to trust.

The existing NBAgent project already has a paid subscription to
The Odds API. NBAgent is budgeted to consume ≤50% of the
20,000/month call cap, leaving ~10,000 credits/month available
for NBAgent-Live.

## What the API offers

Captured from vendor docs `https://the-odds-api.com/liveapi/guides/v4/`
on 2026-04-17. Verify before implementation in case vendor
details changed.

- **Live `/odds` endpoint:** returns all current games with
  bookmaker odds. 1 credit per market per region per call. A
  single call returns all NBA games at that moment.
- **Historical `/odds`:** snapshots at 5-minute intervals since
  September 2022. 10× multiplier on the live cost. Available
  only on paid plans.
- **Historical event odds:** single-event endpoint, includes
  quarter markets (`h2h_q1`, etc.) back to May 2023. Same 10×
  multiplier.
- **Scores endpoint:** live + up to 3 days of completed games.
  1 credit per call live, 2 credits with `daysFrom`. Useful as
  a sanity check that a game has started / finished.
- **US bookmakers:** FanDuel, DraftKings, BetMGM, Caesars,
  BetRivers, PointsBet, BetOnline, Bovada, William Hill,
  SugarHouse, Barstool (the vendor's list churns — treat this
  as approximate and build the scraper tolerant to
  additions/removals).

### Budget envelope

| Operation | Cost (credits) | Returns |
|---|---|---|
| Live `/odds`, `h2h,spreads`, `us` | 2 | all NBA games at that instant |
| Live `/odds`, `h2h,spreads,totals`, `us` | 3 | all NBA games at that instant |
| Historical `/odds`, same params, one timestamp | 20 or 30 | all NBA games at that instant |
| Historical event odds, 1 market, 1 region, one timestamp | 10 | one specific game |
| `/scores`, live only | 1 | all NBA games with scores |

Monthly cap: ~10,000 credits. Design below lands well under it.

## Three-stream design

### Stream A — Live polling during games

**What:** `/odds` endpoint at 5-minute cadence during active NBA
game windows. Markets: `h2h,spreads`. Region: `us`.

**Why:** Primary research data asset. Continuous paired
(Kalshi, ESPN, sportsbooks) observations during live play.
Enables every cross-source analysis listed in the Purpose
section.

**Budget:** A game window is ≈3 hours. 12 calls/hr × 2 credits
= 24 credits/hr per active window. All NBA games that night are
captured in the same calls, so the cost is per-window,
not per-game. Conservative playoff estimate:
30 game-windows × 72 credits/window ≈ 2,200 credits/month.

**Implementation:** new scraper
`scrapers/odds_api_live.py`, pattern-matched to
`logger/kalshi_logger.py` (long-lived process, idempotent JSONL
appends, periodic git commit). Writes to
`data/odds_api_live/{YYYY-MM-DD}.jsonl`.

### Stream B — Pre-tip snapshots

**What:** One `/odds` call ≈30 minutes before each NBA tip.

**Why:** Pairs with pre-tip Kalshi orderbook data already being
logged. Answers directly: "was Kalshi's pre-tip mid on
consensus?" Trivially cheap.

**Budget:** 2 credits per tip × ~100 playoff tips ≈ 200 credits.

**Implementation:** folded into Stream A's scraper — when it
detects a 30-minutes-to-tip window, fire one snapshot flagged
`snapshot_type: "pre_tip"`. Avoid a separate cron.

### Stream C — Targeted historical backfill

**What:** Historical event odds for specific research questions.
Not scheduled. Dispatched per analysis as needed.

**Why:** On-demand. We don't need historical backfill for its
own sake; only when a specific research dispatch requires it.
The vendor's archive going back to September 2022 (5-min
intervals) means data availability is not the constraint.

**Budget examples:**

- §1.4 focused test (20 games × 4 in-game moments × 10 credits
  × 1 market `spreads`): 800 credits.
- Tonight's GSW-PHX + CHA-ORL back-pair if we want them before
  the live scraper is in place (2 games × 6 moments × 10
  credits × 2 markets): 240 credits.
- Full 2025-26 regular-season moneyline at tip only —
  ~175 distinct game dates × 20 credits ≈ 3,500 credits.
  (Not 1,243 games × 20 credits, because `/odds` returns all
  games at a given timestamp. Batch by date.)

**Implementation:** ad-hoc scripts under
`analysis/` or `scrapers/historical/`, invoked per dispatch.

## Data shape and storage

- **Live snapshots:**
  `data/odds_api_live/{YYYY-MM-DD}.jsonl`. One row per
  (snapshot_ts, game_id, bookmaker, market, outcome). Sibling
  to `data/orderbook_snapshots/`.
- **Pre-tip snapshots:** same path, flagged with
  `snapshot_type: "pre_tip"`.
- **Historical backfills:**
  `data/odds_api_historical/{query_id}/`, self-describing per
  dispatch.
- **Committed vs gitignored:** Live and pre-tip committed
  (matches Kalshi orderbook pattern — data is part of the
  deliverable). Historical backfills committed for now; revisit
  if storage grows materially.

## Team/game identity alignment

Three naming conventions collide here:

- Odds API: full team names ("Golden State Warriors").
- Kalshi: team abbreviations in the ticker ("GSW").
- ESPN: its own shorthand ("GS").
- `data/nba_master_2025_26.csv` (NBAgent-inherited): standard
  NBA abbreviations.

**Resolution:** extend `scrapers/espn_scraper._norm_team` with
Odds-API-specific entries, OR factor out to
`scrapers/team_identity.py` if the mapping grows enough that a
single file is cleaner. Do not duplicate the mapping table. The
existing Phase 2b prompt established `_norm_team` as the
single source of truth; follow that convention.

**Game matching:** Odds API `id` is an opaque hash. Match on
`(home_team_normalized, away_team_normalized, commence_time)`
within a same-day window. Spot-check ≥5 matches on first run
before trusting the matcher at scale.

## Implementation phases

**Phase O1 — Live scraper MVP.** Build
`scrapers/odds_api_live.py` implementing Streams A + B. Deploy
as `.github/workflows/odds_api_live.yml` with schedule
bracketing the existing Kalshi logger blocks. First-run
verification against a known playoff night. 1–2 prompts.

**Phase O2 — Analysis harness.** Script that joins Odds API
live data + Kalshi orderbook + ESPN WP at matched timestamps
and produces cross-source tables (consensus mean, spread,
Kalshi-vs-consensus residual). One prompt.

**Phase O3 — First paired analysis.** Apply O2 harness to
whatever live data has accumulated. Produces the first §1.1
residual distribution, the first §6.6 flow-isolation
observation, the first cross-book variance characterization.
Needs ≥5 games' worth of data before it's meaningful. One
analysis prompt.

**Phase O4 — §1.4 focused historical test.** Stream C dispatch
targeting 20 games with |pre-game spread| ≥ 5, pulling in-game
spread evolution at 4 moments per game. Direct test of §1.4
against sportsbook pricing. One analysis prompt.

O1–O2 are infrastructure and can be done in parallel with
ongoing Kalshi data collection. O3–O4 are research and gated on
having data to analyze.

## Caveats and known issues

- **Moneyline ≠ no-vig probability.** Sportsbook h2h odds
  include a house margin (typically 4–5% vig on NBA). Convert
  both sides' implied probabilities to no-vig before comparing
  against Kalshi: `p_novig = p_raw / (p_home_raw + p_away_raw)`.
  The API does not do this for you. Cross-book consensus should
  be computed on no-vig values, not raw.
- **Live odds ≠ resting liquidity depth.** Sportsbook moneyline
  is "price at which the book is willing to take action" with
  an unstated bet-size ceiling. Depth is not directly
  queryable. Use Odds API for pricing signal only, not as a
  depth proxy for Kalshi.
- **Cross-book variance is itself the signal.** Report mean and
  spread across books, not just mean. Tight consensus ≠ wide
  consensus in what they tell you about Kalshi.
- **Quarter markets (`h2h_q1`, etc.) are thin.** Wider spreads,
  spottier coverage, fewer books. OK as supplementary;
  shouldn't be load-bearing.
- **Update cadence varies by bookmaker.** `last_update`
  timestamps in responses can be minutes-stale on slower books
  during dead periods. Check `last_update` before treating a
  snapshot as "live." Filter out quotes older than ~2 minutes
  at analysis time.
- **American vs decimal odds.** Pick one (prefer `american` by
  NBA handicapping convention) and document the choice in the
  scraper.
- **Bookmaker list churns.** Don't hardcode the US book list.
  Scraper should iterate whichever bookmakers appear in the
  response.
- **Rate limiting (HTTP 429).** Vendor rate-limits on burst
  traffic. 5-min cadence is safe, but historical backfills
  that blast through hundreds of timestamps should space
  requests.

## What's out of scope

- Non-NBA sports.
- Non-`us` regions (`us2`, `uk`, `eu`, `au`). Would double or
  quadruple the consensus basis but also double or quadruple
  the cost.
- Player props and alternate lines.
- Sportsbook bet placement automation. Data collection only.
- Cross-book arbitrage alerting.

## Open questions specific to this integration

Candidates for promotion into `docs/THESIS_open_questions.md`
§2 in a future dispatch. Logged here to avoid drift:

- **O-Q1:** How tight is cross-book consensus on NBA h2h during
  live play? p95 of cross-book spread at matched timestamps,
  stratified by game state (Q1/Q2/Q3/Q4, close/blowout). If
  tight (p95 < 3pp), Kalshi-vs-consensus comparison is
  meaningful. If wide, "consensus" is noisy and Stream A's
  signal degrades.
- **O-Q2:** Does Kalshi's pre-tip mid match the no-vig
  consensus? Test from Stream B data. If yes, §1.1 gets strong
  evidence at a clean moment (no game state to confuse). If no,
  Kalshi has its own pricing logic at tip that doesn't track
  sportsbook consensus.
- **O-Q3:** Are live sportsbook spreads prior-anchored the way
  ESPN WP appears to be? Direct testable with Stream C
  historical data. If yes, §1.4 generalizes across pricing
  systems (and Kalshi likely inherits the property). If no,
  ESPN's anchoring may be idiosyncratic to its model — and
  §1.4 is less dangerous for Kalshi-proxy use than feared.

## Cross-references

- `docs/THESIS_open_questions.md` §1.1 — Kalshi ≈ consensus.
  This integration provides the primary test vehicle.
- `docs/THESIS_open_questions.md` §1.4 — ESPN spread-anchoring.
  Stream C gives the cleanest available test.
- `docs/THESIS_open_questions.md` §2.1 — liquidity. This
  integration does NOT address liquidity directly.
- `docs/THESIS_open_questions.md` §6.6 — flow vs game-state.
  Stream A live polling disambiguates cleanly.
- `docs/FEES.md` — Kalshi fee envelope. Unrelated; sportsbook
  odds carry a separate vig structure that must be accounted
  for in cross-source EV comparisons.
- `docs/RESEARCH_LOG.md` 2026-04-16 pilot entry — original
  "Kalshi ≈ ESPN WP" framing (§1.1 motivation) that this
  integration upgrades.

## First-session implementation handoff

A fresh session picks up from Phase O1. Recommended starting
dispatch shape:

1. Re-read this doc, `docs/CLAUDE.md`, `logger/kalshi_logger.py`,
   and `scrapers/espn_scraper.py` for conventions.
2. Build `scrapers/odds_api_live.py` matching the Kalshi logger
   pattern (long-lived, idempotent, periodic commit,
   self-terminating on idle).
3. Add `.github/workflows/odds_api_live.yml` bracketing the
   Kalshi logger schedule.
4. `ODDS_API_KEY` goes into GitHub Actions secrets. Document in
   the workflow file and in this doc's caveats section when
   that's done.
5. Spot-check one game night's output. Verify 8+ bookmakers
   show up, consensus variance is measurable, timestamps align
   with Kalshi snapshots to within 30 seconds.

Do NOT build analysis infrastructure (O2+) in the same dispatch
as the MVP scraper (O1). Keep boundaries clean.

Do NOT extend the design to additional sports, regions, or
markets without an explicit scope-expansion dispatch that
updates this doc.
