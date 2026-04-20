# Resolved Roadmap

## 2026-04-16 — Phase 0: Repo bootstrap
Created NBAgent-Live repo structure: logger/, data/orderbook_snapshots/, docs/, .github/workflows/. Bootstrapped CLAUDE.md, README.md, RESEARCH_LOG.md seed.

## 2026-04-16 — Phase 1: Kalshi orderbook logger
Implemented `logger/kalshi_logger.py` — long-lived polling process that auto-discovers today's NBA game markets and logs orderbook snapshots every 30s to `data/orderbook_snapshots/{date}.jsonl`. Scheduled via `kalshi_logger.yml` in three daily blocks (morning, midday, evening) with self-termination on idle. Market data endpoints unauthenticated — no Kalshi account required.

## 2026-04-16 — Phase 1 fix: per-game market discovery filter

First verification of Phase 0+1 revealed the `discover_nba_game_markets` filter silently rejected every real per-game market. Root cause: `close_ts` for Kalshi playoff markets is set to the series-conclusion buffer (~2 weeks out), so the "close within 36h" window never matched. Replaced with a ticker-prefix date parser (`KXNBAGAME-YYMMMDD...` → game date in ET) accepting ±1 day of today ET. Phase 1 remains *implemented but unverified* — awaiting a first successful production block with snapshots committed before promoting to *confirmed working*.

## 2026-04-16 — Phase 1 fix: snapshot field names updated to current Kalshi API

Second Phase 1 verification pass revealed `snapshot_market` was reading legacy field names — every price / volume / OI field landed as null. Updated reads to current `*_dollars` / `*_fp` naming, kept raw string decimals (lossless; casting deferred to analysis), added `yes_bid_size_fp` / `yes_ask_size_fp` / `liquidity_dollars` / `open_time` / `updated_time`. Phase 1 remains *implemented but unverified in production* — the 4/17 Play-In slate (GSW-PHX, CHA-ORL) will be the first real shakedown.

## 2026-04-17 — Phase 1: First confirmed production run

Kalshi logger's first confirmed production run verified. Morning
block captured pre-tip orderbook data across 12 tickers (6
events: GSW-PHX and CHA-ORL for 2026-04-17, plus 4 events for
2026-04-18). 7,260 snapshots over 5 hours, 30s cadence
maintained with no gaps. Pre-tip volume ramp observed on
CHA-ORL (80% growth in 5h before tip) — qualitative evidence
for §6.6 in a clean no-game-state window. `liquidity_dollars`
field confirmed never populates (§2.1 open item partially
resolved: use orderbook depth / `*_size_fp` for liquidity
signal).

## 2026-04-17 — Phase 2a: ESPN scrapers

Built `scrapers/espn_scraper.py`. Produces per-gameId WP
timeseries and PBP from ESPN's game summary endpoint.
Verified on Play-In games (GSW-LAC 401866756, CHA-MIA
401866755). ESPN WP confirmed to match Kalshi screenshots to
within 1pp at both paired observations. Established
`_norm_team()` as single source of truth for ESPN→standard
abbreviation mapping.

## 2026-04-17 — Phase 2b: ESPN season backfill utility

Built `scrapers/espn_backfill.py`. Reads game IDs from
`data/nba_master_2025_26.csv`, scrapes WP + PBP per game.
Supports `--start` / `--end`, `--team`, `--max-spread`
filters. Idempotent skip logic.

## 2026-04-17 — Pre-game spread integration

Inherited `data/nba_master_2025_26.csv` from NBAgent (152 KB,
committed). Enables ex-ante competitive-game filtering by
|spread| rather than the noisy final-margin proxy. 1,135 /
1,243 games have pre-game spread data.

## 2026-04-17 — Full 2025-26 ESPN backfill execution

Ran `scrapers/espn_backfill.py` against the complete 2025-26
regular season. 1,243 / 1,243 games processed, 0 failures, ~35
min runtime. Output: 2,486 JSONL files (WP + PBP), 388 MB total.
Gitignored (regenerable in ~35 min from scratch). 9 games have
missing WP data (0.7%) — audit completed in Phase 3A follow-up
dispatch, classified benign.

## 2026-04-17 — Phase 3A: Bilateral dip analysis on ESPN WP

First analysis against the full 2025-26 dataset using ESPN WP
instead of Stern. Bilateral <0.20 rate: 26.6% at |spread|≤6
(vs Stern pilot 30% / 42.5% at margin≤10). ESPN residual +2.6
to +3.3pp in the 7.5-20% WP band (vs Stern pilot +9pp) —
Strategy 2 edge against ESPN is thinner than pilot suggested,
Kalshi residual still TBD in Phase 3B. Temporal separation
median 18 min, 97.3% ≥5 min (§6.2 denied in good direction).
Home/away crossing rates symmetric; depth asymmetric (§6.3
partial). See `docs/RESEARCH_LOG.md` 2026-04-17 Phase 3A entry.

## 2026-04-17 — Phase 3A follow-up: Pace (§6.4) + sequential bilateral (§6.7)

`analysis/phase_3a_followup.py` +
`docs/analysis_outputs/3a_followup_2026_04_17.md`. §6.4 denied:
Spearman ρ = +0.063 (p = 0.75) between team pace and bilateral
involvement. §6.7 confirmed and reframed: asymmetric any-order
bilateral rate hits 49% at (0.20, 0.30) on |spread|≤6, ~60%
higher aggregate EV/game than strict. Methodology note: the
"sequential" framing was unnecessarily restrictive; the
operational rate sits close to the asymmetric-any-order ceiling.
Strategy 1's addressable universe substantially larger than
strict-bilateral read suggested.

## 2026-04-17 — §6 retirements + 9-missing-games audit

Formal retirement lines added to `docs/THESIS_open_questions.md`
for §6.1 (partially confirmed), §6.2 (denied, good direction),
§6.3 (denied on rate, partial on depth), §6.4 (denied), §6.7
(confirmed, reframed larger). §6.5 and §6.6 remain open (blocked
on Phase 3B Kalshi data). 9-missing-games audit classified
benign (scattered across dates, no empty files, no scraper bug
— gaps are ESPN feed irregularities on individual games).

## 2026-04-17 — §1.4 added to open questions

New load-bearing claim added to `docs/THESIS_open_questions.md`:
ESPN WP is spread-anchored (prior-weighted) rather than purely
game-state-driven. Motivated by 4/15 GSW-LAC Play-In observation
(GSW pinned near opening-line-implied 30% throughout) and
consistent with the Stern-vs-ESPN bilateral-rate gap as a
mechanism-level explanation. Three retirement analyses listed;
runnable from existing ESPN data before Phase 3B.

## 2026-04-17 — Phase O planning: Odds API integration designed

`docs/ODDS_API_INTEGRATION.md` drafted. Three-stream
architecture (live polling during games + pre-tip snapshots +
targeted historical backfill). Budget ~2,400 credits/month on
~10,000/month envelope. First-session implementation handoff
documented. Implementation queued for a fresh session starting
with Phase O1 (live scraper MVP).

## 2026-04-18 — Phase 3B smoke test (n=2, then n=6)

First paired Kalshi-ESPN analysis. Identified Kalshi-ESPN
compression pattern (+10-14pp at WP tails). Pipeline validated:
as-of merge, complement check, screenshot cross-check. n=4
usable games (CHA-ORL, GSW-PHX, TOR-CLE, HOU-LAL). MIN-DEN
lost (logger gap), ATL-NYK unusable (stale pricing).

## 2026-04-19 — Sportsbook backfill (Strategy 1 focus)

Odds API historical backfill at bilateral dip moments. 30
games, 57 observations, 341 fresh bookmaker quotes. Established
ESPN as the outlier: sportsbooks match Kalshi compression
(+12.58pp mean residual vs ESPN). Reframed §1.1 from "Kalshi ≈
ESPN" to "Kalshi ≈ sportsbook consensus." Strategy 2
preliminary kill signal issued.

## 2026-04-19 — Strategy 1 recalibrated bilateral analysis

Re-ran bilateral rates at sportsbook-denominated thresholds
using 57-point calibration mapping. Optimal operating point:
(0.25, 0.35) at 17.7% rate, $6.55 EV/game — marginal but
positive. Down from ESPN-denominated $23.23/game (72%
reduction).

## 2026-04-19 — Logger updates

- MAX_RUN_SEC default changed from 5h15m to 24h for local-run
  convenience.
- Per-game JSONL file split (one file per Kalshi ticker).
- Health check script: analysis/logger_health_check.py.
- GitHub Actions workflow deactivated; logger runs locally.

## 2026-04-19 — Gitignore orderbook snapshots

Orderbook snapshot files removed from git tracking (backed up
to personal cloud storage). Reduces repo storage footprint.

## 2026-04-19 — Strategy 3 oscillation analysis: HOU-LAL

First Kalshi oscillation characterization. Mid-range
round-trips confirmed ($14.55/trade). Extreme-price grid
produces zero trips — operating zone reframed to $0.35-$0.55.
Favorite-side analysis added (positive on n=1 but later
killed by FanDuel data).

## 2026-04-19 — Game flow trajectory analysis (ESPN WP)

Classified 1,234 games into 5 trajectory buckets. 75% of
competitive games produce ≥1 mid-range round-trip. Comeback
and Back-and-forth carry 84% of round-trips. Pre-game spread
is a weak predictor (ρ ≈ -0.35). Favorite-side universe
sized (68% of games, +$4.34 blended EV but high variance).

## 2026-04-19 — Strategy 3 Odds API timeseries (n=15)

FanDuel moneyline at 5-min intervals for 15 games. ESPN-to-
market survival rate: 30.4%. Favorite-side killed (−$18.40
blended net on FD data). Revised universe: ~689 market-price
round-trips/season, ~$10K EV at 100-contract sizing.

## 2026-04-20 — Kalshi historical trades probe

Confirmed `/markets/trades` endpoint as a new unauthenticated
data source. HOU-LAL: 93,838 trades, 29.2M contracts.
100-contract orders are invisible in the flow (0.02% of
5-min bucket volume). Strategy 3 zone ($0.35-$0.55) carries
40.8% of total market volume.

## 2026-04-20 — Strategy 3 multi-game oscillation (4/19 R1G1)

4 games analyzed. ORL@DET (competitive): 21 swings ≥$0.10,
2 round-trips at (0.40,0.50). Three blowouts: zero round-
trips (expected for R1G1 seed matchups). Spread $0.01 across
all 4 games. Cumulative: 2/10 competitive games toward
graduation.
