# Resolved Roadmap

## 2026-04-21 — Infrastructure: Forward-collection cron + logger schedule deprecation

Addresses the ~60-day Kalshi trade-tape retention cliff by
capturing each night's settled games within a day of settlement,
before the tape becomes unreachable. New pieces:

- `analysis/forward_collect.py` — orchestrator. Resolves
  yesterday (America/Los_Angeles) by default, calls
  `scoreboard_games` + `run_single_game` for each game (no
  pre-match CSV required — scoreboard drives discovery).
  Writes per-night audit log to
  `data/wp_kalshi_paired/forward_runs/<date>.log` always,
  including off-nights (explicit "no games" log so silent
  cron failures on real game days are visible).
- `.github/workflows/forward_collection.yml` — nightly cron at
  10:00 UTC (03:00 PT). Commits new paired data with
  `[skip ci]`. `workflow_dispatch` supports a `--date` input for
  backfills.
- `.github/workflows/forward_collection_weekly.yml` — Monday
  11:00 UTC refresh of cross-game indexes
  (`matched_games.csv` via `ticker_matcher.py` and aggregate
  summaries via `wp_vs_kalshi_aggregate.py`). Decoupled from
  nightly: nightly stays fast, weekly handles the growing-cost
  indexes.
- `.github/workflows/kalshi_logger.yml` — `schedule:` block
  stripped; `workflow_dispatch` retained. Logger runs locally
  now; GH Actions cron delay caused catastrophic game-coverage
  gaps during the research window.

Architecture note: the nightly path bypasses `matched_games.csv`
entirely — `wp_vs_kalshi_paired`'s `--all` mode resolves games
directly from ESPN's scoreboard, so `matched_games.csv` has been
repositioned as a weekly-refreshed index rather than a
nightly-updated canonical record.


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

## 2026-04-20 — Timeout execution window analysis

`analysis/timeout_execution_analysis.py`. Paired Kalshi
trade tape with ESPN PBP timeouts. Confirmed timeout windows
as favorable execution environments (2.3× depth, $0.01
spread floor, 1.5× volume). Confirmed NOT a directional
signal. 20 timeouts across HOU-LAL + ORL@DET.

## 2026-04-20 — Scoring-run trajectory analysis (Kalshi, n=2)

`analysis/scoring_run_trajectories.py`. Score-to-price
impact mapping: 3-pointer = $0.04/3.5s, 2-pointer =
$0.017/4.1s, impact peaks in $0.40-$0.50 zone. Post-
timeout price trajectory: null at fixed checkpoints (n=5
run-stopping timeouts, too thin to conclude). ESPN PBP
for ORL@DET (4/19) scraped as part of this analysis.

## 2026-04-20 — ESPN-scale scoring-run pattern catalog

`analysis/espn_scoring_run_catalog.py`. Full-season (549
competitive games) run detection, timeout association,
post-run WP recovery, prior degradation, favorite/underdog
asymmetry. Key findings: 89% of runs bounce back (max
recovery); 52% at fixed 3-min checkpoint. Favorites recover
3-6pp more often and ~1.5 min faster. Timeouts don't help
recovery (51% vs 53% without). Q1 best period for recovery
(59%). Prior dissolves over first half of game.

## 2026-04-20 — STRATEGY3_SPEC.md created

Living strategy spec document created. Consolidates all
Strategy 3 findings into a single entry-rule / exit-rule /
execution-preferences / graduation-status reference.
Supersedes `docs/strategy3_assessment.md` as the primary
spec document.

## 2026-04-20 — WP vs Kalshi paired analysis: script + four-game study

New analysis script `analysis/wp_vs_kalshi_paired.py`. Repeatable
per-game study pairing ESPN win probability timeseries with Kalshi
historical trade prices. Favorite-centric reference frame. 30s
VWAP bins + event-driven scoring-play alignment. Outputs structured
markdown report + paired CSVs for cross-game aggregation.

Validated on 4 games (POR@SAS, ORL@DET, HOU@LAL, MIA@CHA).
Six findings documented in RESEARCH_LOG. Key results: Kalshi
always compresses toward $0.50 vs ESPN (delta peaks at +9pp in
0.20-0.40 WP zone); convergence R² = 0.463 for competitive games
vs 0.000 for upsets; ESPN reacts 1.8-18× more per basket than
Kalshi depending on WP zone; zone entry lead direction depends
on game context (not always ESPN-first). OT thrillers diverge
rather than converge — Kalshi can't reprice fast enough in
final-possession games.

## 2026-04-20 — Ticker matcher + batch + aggregation infrastructure

Three-file build-out for scaled WP vs Kalshi analysis:
- `analysis/ticker_matcher.py`: matches ESPN game IDs to Kalshi
  event tickers via date + team parsing. Outputs joined CSV.
  Supports --max-spread and --sample filters.
- `analysis/wp_vs_kalshi_paired.py`: added --batch flag for
  multi-game runs. Auto-caches, skips per-game reports in batch
  mode, resumes interrupted batches. Single-game mode unchanged.
- `analysis/wp_vs_kalshi_aggregate.py`: pools paired CSVs across
  games. Sections: delta by WP zone with CIs, convergence by
  spread bucket, scoring-play reaction ratios, S3 zone stats,
  timeout delta stability, per-game summary table.

## 2026-04-21 — Strategy 3 spec update + graduation evaluation

Updated STRATEGY3_SPEC.md with production-grade calibration from
168-game WP vs Kalshi paired analysis: compression curve by WP zone
(+8.30pp in 0.20-0.40, −2.73pp in 0.80-1.00), convergence dynamics,
per-basket reaction confirmation. Added convergence-zone exit
preference (1–3 min remaining = optimal exit window). Updated
timeout evidence to Kalshi-confirmed (p=8.5e-08).

New script `analysis/strategy3_graduation_eval.py`: formal
graduation scorecard against KILL_CRITERIA thresholds. Runs
round-trip detection on 168-game paired timeseries at 5 grids.
Reports RT frequency, economics, hold time, entry period,
exit timing, bilateral entry frequency, and formal verdict.

## 2026-04-21 — Failed entry & worst-case distribution analysis

New script `analysis/strategy3_failed_entries.py`. Tracks every
entry event at the Strategy 3 threshold across 165 competitive
games. Measures completion rate, fail rate, true EV per entry
(including losses), MAE distribution, period and spread effects
on failure, and worst-case scenarios. Produces entry-level CSV
for downstream risk analysis.

Headline finding: true blended EV per entry is −$4.57 (60.9%
complete at +$15.49 mean, 39.1% fail at −$35.82 mean).
Graduation verdict is revised — the 100%-profitable-completed-
RT finding was a subset statistic; full-entry EV is negative.
Strategy 3 requires stop-loss or selective-entry refinement
before Phase 4a.

## 2026-04-21 — Stop-loss sweep & position management

New script `analysis/strategy3_stoploss_sweep.py`. General-purpose
replay engine parameterized by entry/exit/stop-loss/avg-in/partial-
exit configurations. Sweeps 20 stop-loss levels on 165 competitive
games (422 entries, 597 with re-entry under tighter stops). Tests
averaging-in and partial exit strategies. Reports optimal
configuration with annual EV, false-stop rate, and context
breakdowns.

Finding: no risk-management variant produces positive EV. Best
combined config (stop $0.34 + avg-in $0.35) is −$1,175 annual EV
vs −$5,963 baseline. Entry signal must be made selective
(period / spread / side filters) before Phase 4a can unlock.

## 2026-04-21 — Upside capture & trailing stop simulation

New script `analysis/strategy3_upside_capture.py`. Extended
replay engine with split positions: partial exit at first profit
target, trailing stop on held remainder, hold-to-resolution
option. 96-config grid search across initial stop × scale-out
ratio × trailing stop distance. Produces strategy comparison
table showing evolution from naive to optimized configuration.

Best configuration found: stop $0.34, sell 25% at $0.50, hold
75% to resolution, no trailing stop. Annual EV −$852 (vs −$5,963
naive, −$1,175 previous best). Still negative. Every variant of
risk-management and upside-capture mechanics tested is negative.
Selective entry filters are the next required research step
before Phase 4a can unlock.

## 2026-04-21 — Entry filter analysis

New script `analysis/strategy3_entry_filters.py`. Tests four
entry filters (oscillation lookback, ESPN WP momentum, favorite-
side, period restriction) individually and in combination on
165 competitive games. 32-config combined grid search with both
simple and upside-capture exit strategies. Filter diagnostic
measuring precision/recall on recoverable vs terminal dips.

**First positive-EV result in the Strategy 3 chain.** Eight
of 32 combined configurations are positive. Best by mean P&L:
WP(120s/3pp) + Fav + Period(Q1-Q2) + upside exit → +$3.41/entry,
+$578 annual EV, 21.6% win rate, 5.37× win/loss ratio. Best by
annual EV: WP + Period + upside → +$725 annual at 152 entries.
Combined with bilateral Strategy 1: **+$2,186 total annual EV**.
Phase 4a unlock path identified; selective-entry spec ready for
SESSION_CONTEXT handoff.

## 2026-04-21 — Strategy 4 dip-recovery analysis

New script `analysis/strategy4_dip_recovery.py`. Three-part
analysis on 165 competitive games from the 168-game paired
dataset. Part 1: false-summit analysis (at each price $0.50-$0.99,
what fraction of games that traded there had the favorite lose).
Part 2: favorite dip-recovery sweep (1,200 configs: lookback ×
dip depth × entry zone × exit target × stop-loss). Part 3:
underdog run-capture sweep (~160 swing + 10 hybrid configs:
momentum vs static entry, swing vs hybrid exit). Part 4:
cross-strategy comparison table (S1/S3/S4A/S4B).

Distinct from Strategy 3: entry at $0.50-$0.75 (not $0.40),
exit before resolution at $0.80-$0.95 (not $0.50), buying the
favorite's natural buoy during temporary underdog runs rather
than buying into genuine market doubt.

Runtime: ~11 seconds (precomputed trailing max/min per lookback,
then swept configs). Results pending review — RESEARCH_LOG entry
deferred per prompt.

## 2026-04-21 — Strategy 4 prior-weighting analysis

Extended `analysis/strategy4_dip_recovery.py` with Part 5:
prior-weighting / dip-below-prior analysis. Bins S4A entries
by gap between pre-game Kalshi price and entry price. Tests
prior-anchor thesis: entries deeper below the pre-game price
should recover more reliably. Sweeps min-dip-below-prior
filter across 9 thresholds, applies best filter to top 5
S4A configs, and briefly tests underdog-side mirror.

## 2026-04-21 — Strategy 4A position management study

Extended `analysis/strategy4_dip_recovery.py` with Part 6:
averaging-in/out analysis on best S4A config (180s / $0.08 /
$0.50–$0.75 / $0.90 / $0.40). Six averaging-in configs
(50/50 at various add-on depths, triple tranche, conviction
build), seven averaging-out configs (partial exits at $0.80–
$0.95 ladders), four combined configs. Tests whether position
management can convert some of the 47% stop-outs into smaller
losses or partial wins.

Null result: every variant underperformed the Config A/G
baseline. Best non-baseline combined config was −$1,463 worse.
Fee multiplication (each tranche pays its own maker fee),
undersized wins (add-on doesn't always fire, leaving 50-contract
positions), and new partial-then-stop loss mode compound to
erode EV. The Phase 4a operational spec remains 100 contracts
at initial trigger, one exit at $0.90 or stop at $0.40.

## 2026-04-21 — Strategy 3 holdout validation

New script `analysis/strategy3_holdout_validation.py`.
Train/test split (110/55 games, seed=42) of the S3 entry
filter grid search. 32 configs swept on train set, top
configs evaluated on held-out test set. 6-seed stability
analysis (seeds 42–47) to assess robustness. S4A best
config run on same split as consistency check. Produces
formal VALIDATED / CURVE-FIT verdict for S3 filtered
strategy.

**Result: VALIDATED (4 of 6 seeds).** Best test-set config
is wp+fav+period/upside exit at +$4.35/entry, +$825 annual
EV on held-out sample. The three top-by-train-P&L configs
all showed positive test-set mean P&L on seed=42.
S4A cross-reference shows strong consistency (train
+$3.19, test +$4.24). Combined projection S1 + S3 + S4A
= **$+4,667/year** on test-half estimates.

## 2026-04-21 — STRATEGY4_SPEC.md created

Living strategy spec document for Strategy 4. Consolidates
dip-recovery analysis (Parts 1–6), prior-weighting results,
position management conclusions, false-summit exit analysis,
period/spread effects, and annual EV projections into a single
actionable reference. Companion to STRATEGY3_SPEC.md. CLAUDE.md
pointers updated.
