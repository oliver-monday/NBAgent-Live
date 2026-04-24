# Resolved Roadmap

## 2026-04-23 — S4A engine ratchet implementation

Breakeven ratchet stop wired into the Phase 4a paper-trading
engine, replay-validated on the 404-game Kalshi pool.

- `engine/position_manager.py`: added `highest_since_entry`,
  `ratchet_triggered`, `effective_stop` per-position state;
  `_update_ratchet` helper; maker/taker fee split (maker on
  entry + target + ratchet_stop, taker on full_stop);
  `target_exit = 0.90` so target fills at the level exactly
  (not observed overshoot); `close_ratchet_stop` action type;
  `ratchet_events()` + `summary()` ratchet counts.
- `engine/live_runner.py`: `--ratchet 0.08` CLI flag,
  threaded into `PositionManager` construction; journal
  includes `ratchet_triggered` + `exit_type: ratchet_stop`
  fields.
- `engine/replay.py`: rewritten against the 404-game
  `load_kalshi_games_all_spreads` pool. `--ratchet` flag
  (default 0.08). `EXPECTED` targets for both modes with
  ±1 count / ±$0.02 mean / ±$10 annual tolerances.
  Reconciliation note on target-level vs observed-price
  fill models in module docstring.
- Validation (both modes PASS):
  - `--ratchet 0.08` → 358 entries, 149 target, 88 full
    stops, 121 ratchet stops, hit 41.62%, mean $+3.9153,
    annual $+1,898.59 (vs expected $+1,899; matches Part
    12 trade-for-trade).
  - `--ratchet 0` → 311 entries, 179 target, 132 full
    stops, 0 ratchet stops, hit 57.56%, mean $+3.1336,
    annual $+1,320.04.
- Docs: `docs/STRATEGY4_SPEC.md` §5A added, §2 ratchet row,
  §5 cross-ref, §9 ratcheted EV row; `docs/RESEARCH_LOG.md`
  2026-04-23 entry.

## 2026-04-23 — S3 reframed analysis (3 passes, Parts 1–15)

Three-pass investigation reframing S3 as the $0.40–$0.50 tail
of the S4A favorite-recovery curve. Output:
`docs/analysis_outputs/s3_reframed_extended_entry.md`
(Parts 1–15).

- **Pass 1 (Parts 1–6):** extend entry band down to $0.40.
  $0.45–$0.50 adds clean incremental EV; $0.40–$0.45 is
  volume without alpha.
- **Pass 2 (Parts 7–11):** 12 variants tested (dip depth,
  trailing window, re-entry rules, spread sub-buckets).
  None beats baseline; ridge is robust.
- **Pass 3 (Parts 12–15):** breakeven ratchet stop. At
  trigger +$0.08, converts 44 full stops into 121 small
  scratches, adds 47 new entries; mean P&L $+3.13 → $+3.92
  per entry, annual EV $+1,320 → $+1,899 (pool, 404
  games). Holdout 6/6 seeds positive.
- Ratchet implementation landed in the paper-trading engine
  same day (see entry above).

## 2026-04-23 — S3 standalone KILLED

S3 filters (WP momentum + fav + Q1/Q2) were noise-fitted on
168 games — unfiltered outperformed filtered on 404 games. The
$0.40 entry zone is subsumed by S4A's extended entry range
analysis. Resolution-hold exit is dominated by S4A-style $0.90
swing exits at every price level tested. No separate S3 engine
module will be built. Spec rewritten as kill record:
`docs/STRATEGY3_SPEC.md`.

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

## 2026-04-21 — Phase 3B formal: COMPLETE

168 games paired via ticker-matcher batch infrastructure (165
competitive, |spread| ≤ 6, dates 2026-02-20 → 2026-04-15).
Realized spread $0.01 median. Three strategies validated for
Phase 4a deployment:

- **S1 bilateral:** +$1,608/yr. Confirmed on Kalshi data.
- **S4A dip-recovery:** +$1,886/yr. Best single strategy.
  Spec: `docs/STRATEGY4_SPEC.md`.
- **S3 filtered:** +$578–$825/yr. Holdout-validated (4/6
  seeds). Spec: `docs/STRATEGY3_SPEC.md` §8.

Strategy 2 formally killed (−$18.40 blended net on FanDuel).
Strategy 3 naive rule retracted (−$4.57 true EV per entry).
Phase 4a unlocked.

## 2026-04-21 — Docs health check + cleanup

Seven files updated to resolve contradictions accumulated
during the rapid S3→S4 pivot session. STRATEGY3_SPEC.md §2/§6/§8
rewritten, KILL_CRITERIA S4 section added, THESIS.md updated to
four strategy layers, CLAUDE.md Phase 3B completion framing,
ROADMAP deduplication, THESIS_open_questions consolidated
resolution entry. SESSION_CONTEXT.md fully rewritten.

## 2026-04-22 — S4A halftime entry + spread expansion studies

Extended `analysis/strategy4_dip_recovery.py` with Part 7
(halftime entry) and Part 8 (spread expansion, ESPN-only
Path A). Full-season Kalshi trade tape backfill initiated
(uncapped ticker_matcher → batch trade tape pull for all
matchable games).

- **Part 7 result:** halftime entry is negative EV (−$323/yr
  standalone, drags combined strategy to +$1,121/yr vs S4A
  baseline +$1,886/yr). Do not add to Phase 4a ruleset.
  Report: `docs/analysis_outputs/strategy4_halftime_entry.md`.
- **Part 8 result (ESPN-only Path A):** pattern directionally
  strengthens at wider spreads (hit rate 42.5% → 58.0% from
  |spread| 6.5 → 10.5+), but ESPN proxy under-states Kalshi
  EV by ~$4,000/yr so absolute numbers are not actionable.
  Path B (Kalshi-confirmed) pending full-season backfill.
  Report: `docs/analysis_outputs/strategy4_spread_expansion.md`.
- **Full-season matched_games.csv expansion:** uncapped run
  matched 1,237 games (vs 168 before). ~1,069 new games queued
  for batch trade-tape pull; ~450–550 expected to land within
  the ~60-day Kalshi retention window.

New CLI entry points: `--part7`, `--part8` (mutually
exclusive with the default Parts 1–6 pipeline).

## 2026-04-22 — Phase 4a S4A paper-trading engine

Three-module engine build:

- `engine/s4a_signal.py` — pure signal detection (time-windowed
  trailing max with strict eviction to match pandas
  `rolling(6, min_periods=1)`, dip threshold, entry zone,
  exit target / stop). `Signal` enum: `entry / hold /
  exit_target / exit_stop / no_op`. No I/O.
- `engine/position_manager.py` — position state, risk
  enforcement (max 2 entries/game, max 4 concurrent), paper
  P&L net of maker fees per `docs/FEES.md`. End-of-game
  resolution replicates the offline `simulate_s4a` behavior
  (≥$0.95 → $1.00 no fee, ≤$0.05 → $0.00 no fee, else
  mid-price with exit fee). No I/O.
- `engine/live_runner.py` — Kalshi polling (30s interval,
  retry with backoff on 429), event-ticker grouping, favorite
  determination from opening prices (both sides > $0.05,
  higher bid locks), per-game `S4ASignalDetector` +
  `PositionManager`, JSONL journal under
  `data/paper_trades/YYYY-MM-DD.jsonl`. SIGINT/SIGTERM
  safe — flushes session summary + closes open positions
  at current quotes on exit.
- `engine/replay.py` — drives the 168-game paired dataset
  through the same detector + manager and compares
  trade-for-trade against the authoritative offline
  `analysis.strategy4_dip_recovery::simulate_s4a`.

**Replay PASS (2026-04-22, 171-game current dataset):**
166 entries / 87 target / 79 stop / 0 EOD / 52.41% hit /
+$3.2149 mean P&L / +$1,707.83 annual EV. Engine vs offline
delta: 0 entries, 0.00pp hit, $0.0000 mean, $0.00 annual
(trade-for-trade equivalence). The $178 drift from the
STRATEGY4_SPEC.md 165-game snapshot (+$1,886) is because
the dataset grew by 6 games during the full-season
backfill; both engine and offline agree on the new
numbers, so the drift is a dataset change, not a logic
change.

Design decisions (full rationale in `docs/PHASE4A_DESIGN.md`):

- Separate process from the logger (crash isolation; logger
  protects irreplaceable orderbook data).
- Favorite determined from Kalshi opening prices — no
  external sportsbook dependency.
- 100 contracts / max 1+1 re-entry / max 4 concurrent;
  no daily loss cap in paper mode (required for live).
- Skipped the originally-planned Phase 4a alert layer —
  alerts were ~200 lines that wouldn't carry forward into
  live trading. Paper-trading with morning journal review
  accomplishes the same validation with zero wasted code.

**Next:** first paper-trading run during live NBA games.
Morning review of the JSONL journal validates the engine
against what actually happened in Kalshi's markets
overnight.

## 2026-04-22 — S4A spread expansion Path B (Kalshi-confirmed)

Added `--path-b` to `analysis/strategy4_dip_recovery.py`
`--part8`. When enabled, the run loads all paired
timeseries CSVs from `data/wp_kalshi_paired/` (not just
|spread|≤6), uses `fav_kalshi_vwap` directly, and writes to
`docs/analysis_outputs/strategy4_spread_expansion_kalshi.md`
while preserving the ESPN-proxy Path A report at
`strategy4_spread_expansion.md`. Table 6 adds a Path A vs
Path B overlap comparison per bucket.

**Path B headline on 404 games (171 competitive + 233
expansion):** +$10,718/yr projected EV across all buckets
at competitive-rate scaling. Existing universe (|spread|≤6)
rolls up to +$7,075; expansion (|spread|>6) adds +$3,644.
Parity check on |spread|≤6 subset reproduces the engine
replay (166 entries / 52.4% / +$3.21 / +$1,708) exactly.

Path A (ESPN proxy) understated EV in every bucket,
dramatically at narrow spreads (1.0–2.0: ESPN 36.1% hit /
−$3.71 mean vs Kalshi 51.7% / +$1.59). Directional signal
from Path A ("pattern strengthens with spread") confirmed;
magnitude was wrong and sign was occasionally inverted.

Follow-ups (not yet scheduled):

- Refresh STRATEGY4_SPEC.md §2 to relax the |spread|≤6
  constraint. Defer until second playoff week of paper data.
- Re-examine `summarize_s4a`'s `COMP_FRACTION` scaling
  assumption for non-competitive buckets — the uniform
  ×0.445 factor across all spread bands is a convenient
  projection but not a physically accurate one for wider
  spreads.

## 2026-04-22 — Spread expansion incorporated into STRATEGY4_SPEC

Part 8 Path B findings (all 7 spread buckets positive EV on
404-game Kalshi dataset, +$10,718/yr uncapped) incorporated
into STRATEGY4_SPEC.md §2/§7/§9/§10, CLAUDE.md, and
ROADMAP_active.md. Competitive game filter expanded from
|spread| ≤ 6 to uncapped. Engine already operates without
spread filter — no code change needed.

## 2026-04-22 — Stop-loss execution reality study

New script `analysis/strategy4_stop_execution.py`. Analyzed
132 stop events across 404 Kalshi-confirmed games. 50% clean
crosses at $0.40, 32.6% moderate gaps ($0.34–$0.38), 17.4%
severe gaps (< $0.34). 73.5% are flash crashes. Break-even
stop price $0.312. Recommended Scenario B: resting NO buy at
$0.60 placed at entry time, taker fallback on severe gaps.
EV impact: Scenario B +$1,460/yr (vs $1,410 baseline, vs
$977 worst-case taker). Findings incorporated into
STRATEGY4_SPEC.md §4 and PHASE4A_DESIGN.md Decision 6.

## 2026-04-22 — Bucket 5.5–6.0 investigation

New script `analysis/strategy4_bucket_investigation.py`.
Deep dive on the |spread| 5.5–6.0 bucket's +$6.17 mean P&L
outperformance (n=37 entries, 28 distinct games). Leave-one-
out mean range $5.32–$7.55 (never negative). Bootstrap 95%
CI: −$2.90 to +$14.73, P(mean>0)=91.1%. Adjacent-bucket
comparison shows similar entry profiles but 16.6pp hit rate
advantage over 4.0–5.0 bucket. Verdict: inconclusive at
current sample size — positive and stable but can't confirm
structural vs noise. Revisit as data grows.

## 2026-04-22 — Stop params sweep + full sensitivity sweep

Two scripts closing the stop-level investigation:
- `analysis/strategy4_stop_params.py`: swept NO bid
  ($0.58–$0.65) × fallback ($0.30–$0.38) across 132 stop
  events. Found $0.58/$0.30 optimal (+$2,252/yr) but
  methodology only repriced existing stops.
- `analysis/strategy4_stop_sensitivity.py`: full S4A
  re-simulation at 11 stop levels ($0.35–$0.45) across
  404 games. Refuted $0.42 recommendation (6 converted
  winners, −$15/yr vs $0.40). Identified $0.35 as pooled
  optimum (+$227/yr) but bimodal curve and 5/7 bucket
  disagreement indicate noise. Conclusion: $0.40 confirmed
  robust, no parameter change.

## 2026-04-23 — S1 bilateral operational simulation

New script `analysis/strategy1_bilateral_sim.py`. Simulates
S1 bilateral position construction on the full 404-game Kalshi
paired dataset. Three entry policies (any-observation,
downward-crossing, warmup) × 14 asymmetric threshold pairs ×
per-game tick replay. Stranded-leg outcomes under 8 exit
strategies (hold-to-resolution, time-based abandonment at
5/10/15/20/30 min, price-based stops at $0.10/$0.15/$0.20).

Recommended operating point: Policy A (any observation ≤ $0.35)
at thresholds (X=0.20, Y=0.35) with T5 stranded exit.
Annual EV: +$5,603/yr (upper bound). 90 bilateral completions
(+$4,817) + 314 T5 exits (-$681) across 404 games. All 7
spread buckets positive EV.

Key structural finding: 100% of bilateral completions are
"collapse bilaterals" — leg 1 side has recovered to ≥$0.70
by the time leg 2 fills. Leg 2 is always insurance during
the other side's collapse. Mean insurance value +$4.36; 21%
of cases actually saved (leg 1 side lost).

Data approximation caveat: underdog price computed as
1 - fav_vwap (no actual underdog bid available in paired
pipeline). Real EV is est. 10-20% lower.

## 2026-04-23 — S1 bilateral follow-up investigations

New script `analysis/strategy1_bilateral_followup.py`. Three
investigations on the recommended S1 operating point:

1. Re-entry simulation (N=3, cooldown {1,10} × loss_cap
   {none,$10,$20}): structurally broken. Bilateral completion
   requires minimum 71 ticks (35.5 min) between legs; T5
   exits at 10 ticks. Re-entry produces zero bilateral
   completions — every additional entry is pure T5 churn.
   All 6 configs negative EV (-$2,595 to -$2,871/yr).

2. T5 exit P&L distribution: 32% profitable (mean +$2.88),
   68% losses (mean -$4.53). Entry price $0.10-$0.15 is
   sweetspot (53% profitable). Wide distribution (P10=-$8.62,
   P90=+$3.39) but portfolio-level aggregation works because
   bilateral wins (+$53.52 each) swamp T5 losses.

3. Blowout filter (≥$0.80/≥$0.75/≥$0.70): improves per-game
   EV but excluded games are themselves positive EV
   (+$5-6/game). Net effect: filtering costs $1,500-$2,900/yr
   in missed opportunities. Not recommended.

## 2026-04-23 — STRATEGY1_SPEC.md created

Living Strategy 1 rule specification. Consolidates bilateral
sim + follow-up findings. Recommended config: Policy A, (0.20,
0.35) thresholds, T5 stranded exit, single entry, no filter.
Annual EV +$4,000-$5,600/yr (conservative to upper bound).

## 2026-04-23 — S1 bilateral KILLED (corrected analysis)

New script `analysis/strategy1_swing_corrected.py`. Replaced
the flawed bilateral simulation with a single coherent state
machine per config. 62 exit strategy configs tested (profit
targets, fixed stops, trailing stops, time limits, and
combinations) on 404 games with entry at ≤$0.35.

**Result: 0 of 62 configs produced positive EV.** Best was
trailing stop -$0.08 at -$103/yr. Hold-to-resolution baseline
-$3,562/yr. The prior +$5,603/yr combined mutually exclusive
outcomes (T5 5-min exits AND 35+ min bilateral completions)
in the same P&L — a simulation design error.

Key insight: selling the underdog at $0.65 produces identical
gross to a bilateral ($0.20 + $0.35 = $0.55 cost vs $0.20
entry + $0.65 sell = $0.45 gross). The bilateral framing was
a theoretical distraction. The corrected swing-trade framing
confirmed no tradeable edge exists on the underdog side.

STRATEGY1_SPEC.md rewritten as kill record. Alpha stack
reduced to S4A + S3.

## 2026-04-23 — S4B underdog hybrid KILLED (revalidation)

New script `analysis/strategy4b_revalidation.py`. Full S4B
config sweep (1,323 configs: momentum + static × hybrid ×
stop variants) on 404 games. Prior result +$1,105/yr on 168
games collapsed to +$148/yr. Only 14 configs positive (1.1%).
Best config earned $0.19/entry — effectively zero.

The resolution-lottery mechanic that drove the prior result
(12.6% underdog win rate on held portion) was abandoned by
the optimizer on the larger dataset — best config uses pure
swing with $0.05 stop, zero positions held to resolution.

S4B is related to S1: a stranded S1 bilateral leg IS an
underdog swing trade. Both strategies fail for the same
reason — the underdog base rate is too low for any exit
strategy to overcome.

STRATEGY4_SPEC.md §8 (S4B section) should be updated to
reflect kill status in a future prompt.
