# NBAgent-Live — Research Log

## 2026-04-16 — Pilot analysis on 2024-25 regular season (session handoff)

**Data:** 1,230 games, 60,590 minute-by-minute score snapshots.
**WP model:** Stern-style Brownian bridge (σ²_final = 170, HCA = 3.5).

### Findings

**Opportunity frequency (bilateral dip rates, tradeable window sec_rem ≥ 60s):**

| Threshold | All games | Final margin ≤10 | Final margin ≤5 | OT games |
|-----------|-----------|------------------|-----------------|----------|
| <0.20     | 30.0%     | 42.5% (262)      | 48.9% (151)     | 63.3%    |
| <0.15     | 21.0%     | 30.8% (190)      | 34.0% (105)     | 53.3%    |
| <0.10     | 12.0%     | 18.5% (114)      | 20.1% (62)      | 41.7%    |

**Timing separation:** In bilateral <0.20 games, median dip separation = 23 min of game clock; 98% ≥5 min apart. Sequential entry viable.

**At-moment calibration (Stern model):** Teams priced at ~10% WP by Stern actually win ~21% of the time — a stable +9-10pp residual across time-remaining cuts, consistent with NBA having fatter tails than Brownian bridge predicts (fouling strategy, 3-point comebacks). Residual is against **my** model; measuring against Kalshi requires Kalshi price data.

**Kalshi ≈ ESPN WP evidence (2 data points, 4/15 GSW-LAC Play-In):**
- At 72-74: ESPN 29.7% / Kalshi 30% (Δ 0.3pp)
- At 114-115: ESPN 33.2% / Kalshi 34% (Δ 0.8pp)

Tight tracking. If this generalizes, **ESPN's WP timeseries becomes a usable historical proxy for Kalshi prices**, and the Stern residual likely represents real edge against Kalshi pricing too.

### Three candidate strategies

1. **Bilateral convergence** — buy both sides cheap (e.g. $0.15 each), guaranteed $0.70 profit. Mechanical edge, liquidity-dependent.
2. **Single-side mean-reversion** — buy a team at low price, hold to resolution. Model-dependent; needs Kalshi price data to validate.
3. **Active management** — buy cheap, sell on swing-back. Sidesteps calibration — profits from volatility regardless of direction.

### Open questions / next steps

1. **Kalshi live logging (in progress).** Phase 1 of this project. Highest priority — data can only be captured going forward.
2. **ESPN PBP + WP ingest.** Better foundation than minute-level. See Phase 2.
3. **Pre-game spread integration.** Remove survivorship bias in competitive-game filter.
4. **Multi-season backfill.** Confirm stability (2014-2023 data available).
5. **Cold-model probe.** Check whether residual survives a properly empirical WP model.

## 2026-04-16 — Kalshi market-data schema notes (Phase 1 probe)

Discovered while probing `KXNBAGAME-26APR17GSWPHX-PHX` pre-tip:

- **Field naming.** Kalshi's market-state endpoint now returns prices as string decimals under `*_dollars` suffixes (e.g. `yes_bid_dollars: "0.30"`), and volume / OI / sizes as fixed-point numerics under `*_fp` suffixes. Legacy integer-cents field names (`yes_bid`, `volume`, etc.) are gone. `close_ts` (epoch int) is also gone — only `close_time` (ISO string) is returned.
- **Orderbook shape.** Payload wrapper key is still `orderbook`. Inner structure is `{yes_dollars: [[price_str, size_str], ...], no_dollars: [[price_str, size_str], ...]}` with ~30 levels per side covering the full penny grid. Both price and size are string decimals in dollars.
- **Per-game market mirroring.** Each game lists *two* per-game tickers (e.g. `…GSWPHX-PHX` and `…GSWPHX-GSW`) — YES on each side. Same underlying event; we snapshot both. Redundant in steady state but cheap (~1.7 KB per snapshot).
- **Pre-tip liquidity floor.** Hours before tip, both sides of GSW-PHX orderbook sat at `$0.01 × $26,300` top-of-book with similar depth on the other extreme. This is resting market-maker liquidity at the penny grid boundaries, not real pricing. **Implication for Phase 3:** tradeable-window definitions must filter by game-has-started, not just time-remaining — pre-tip snapshots carry no pricing signal regardless of how early the block ran.
- **Snapshot size.** 1.7 KB per snapshot at 30-level depth. Full playoff run (~2 months, 4 markets × 30s poll) ≈ 1 GB. No action needed; revisit before any multi-season fanout.

## 2026-04-17 — Phase 3A: bilateral dip analysis on 2025-26 season (ESPN WP)

**Data:** 1,234 / 1,243 games with ESPN WP timeseries (9 missing —
see Open Items below). 599,250 WP rows, 600,220 PBP rows. 1,135
games have a pre-game spread from `nba_master_2025_26.csv`. 55 OT
games.
**WP source:** ESPN Analytics per-game WP feed (replaces Stern
Brownian bridge from the pilot).

### Bilateral dip rates (tradeable window sec_rem ≥ 60s)

| Threshold | All games    | \|spread\|≤6 | \|spread\|≤3 | margin≤10   | margin≤5    | OT          |
|-----------|--------------|--------------|--------------|-------------|-------------|-------------|
| <0.20     | 24.1% (1234) | 26.6% (549)  | 28.1% (263)  | 39.0% (592) | 45.4% (304) | 69.1% (55)  |
| <0.15     | 15.9%        | 17.1%        | 17.1%        | 25.8%       | 29.9%       | 56.4%       |
| <0.10     | 6.5%         | 7.3%         | 7.2%         | 10.5%       | 12.8%       | 20.0%       |

**Comparison with 2024-25 Stern pilot:**

- Pilot (Stern, 2024-25): 30.0% all / 42.5% margin≤10 at <0.20.
- This run (ESPN, 2025-26): 24.1% all / 39.0% margin≤10 at <0.20.
- Gap is ~5–15pp wide and roughly uniform across thresholds — ESPN
  is systematically tighter than Stern at all WP levels, not just
  at the tails. This is a slightly different claim than "ESPN is
  better at the tails specifically."

### Timing separation (|spread|≤6, bilateral <0.20, N=146)

- Median separation: 18.0 minutes of game clock.
- ≥5 min apart: 97.3%.
- <3 min apart: 1.4%.

Sequential entry remains viable. Temporal clustering is not the
bilateral bottleneck.

### At-moment calibration residual (ESPN WP vs actual, sec_rem ≥ 60)

| Bucket          | n       | mean WP | actual | residual |
|-----------------|---------|---------|--------|----------|
| (0.00, 0.025]   | 103,020 | 0.006   | 0.006  | +0.0pp   |
| (0.025, 0.05]   | 32,360  | 0.037   | 0.049  | +1.2pp   |
| (0.05, 0.075]   | 28,417  | 0.063   | 0.075  | +1.2pp   |
| (0.075, 0.10]   | 26,054  | 0.088   | 0.114  | +2.6pp   |
| (0.10, 0.125]   | 25,341  | 0.113   | 0.145  | +3.2pp   |
| (0.125, 0.15]   | 24,599  | 0.138   | 0.170  | +3.3pp   |
| (0.15, 0.20]    | 50,179  | 0.175   | 0.206  | +3.1pp   |
| (0.20, 0.25]    | 48,266  | 0.225   | 0.247  | +2.2pp   |
| (0.25, 0.35]    | 96,422  | 0.300   | 0.332  | +3.1pp   |
| (0.35, 0.50]    | 143,870 | 0.426   | 0.438  | +1.2pp   |

Residuals stable across sec_rem ≥ 60 / 180 / 300 cuts — not a
last-30-seconds garbage-time artifact.

**Shape observation:** ESPN is well-calibrated at the absolute
extremes (≤0.025 WP: residual 0.0pp). Residual peaks at +3.1 to
+3.3pp in the 7.5–20% WP band — exactly the Strategy 2 entry
window. Below 2.5% there is no model-residual edge to capture
regardless of MM behavior at those prices.

**Context for Stern pilot's +9pp residual:** ESPN absorbs roughly
two-thirds of the Stern-vs-actual residual at the tails. The
residual that matters for Strategy 2 is against Kalshi, not
ESPN — see Phase 3B dependency below.

### Team swing propensity (|spread|≤6, sec_rem ≥ 60)

Top 5 bilateral <0.20 involvement rate: WAS 41.7% (n=12, small
sample), SAS 39.5%, PHX 35.6%, DEN 34.4%, HOU 33.3%.

Bottom 5: TOR 18.8%, NYK 18.4%, SAC 16.1%, DET 14.0%, BKN 13.6%
(n=22).

Bottom 5 skews toward known slow-pace defensive profiles (TOR, NYK,
DET). Top 5 is less clean — a formal pace correlation is a
follow-up before declaring §6.4 settled.

### Home/away asymmetry (|spread|≤6, sec_rem ≥ 60, N=549)

| Threshold | Home dip rate | Away dip rate | Away/Home ratio |
|-----------|---------------|---------------|-----------------|
| <0.20     | 61.2%         | 65.4%         | 1.07×           |
| <0.15     | 55.0%         | 60.3%         | 1.10×           |
| <0.10     | 49.0%         | 52.6%         | 1.07×           |

Median min WP: Home 0.115, Away 0.081.

Crossing rates are close to symmetric (within 10%). Dip *depth* is
asymmetric — away teams dip meaningfully lower when they dip. For
Strategy 1 this is neutral (you need crossings, not depths). For
Strategy 2 it's potentially material: away-side extreme lows sit
further into the +3pp residual band than home-side ones.

### How pre-data hypotheses (THESIS_open_questions.md §6) fared

Summary only. Formal retirement lines will be added to the §6
resolution log in a subsequent dispatch, bundled with the pace
and sequential-opportunistic follow-up analyses so the §6 log
stays coherent.

- **§6.1 ESPN residual +4–6pp at tails** — Partially confirmed.
  Observed +2.6 to +3.3pp in the 7.5–20% WP band; at the low end
  of the "confirmed if +3 to +7pp" range. Strategy 2 edge
  survives against ESPN but is thinner than predicted.
- **§6.2 15–20% of bilaterals have <3 min separation** — Strongly
  denied in the good direction. Only 1.4% <3 min.
- **§6.3 Away dip rate ~40% higher than home** — Denied on rate
  (only 7–10% higher) but partially supported on depth (median
  min WP home 0.115 vs away 0.081). The implication about home-
  underdog game selection deserves a second look with depth as
  a dimension, not just crossing rate.
- **§6.4 Pace dominates swing propensity** — Mixed, pending
  formal pace correlation follow-up.
- **§6.5, §6.6** — Not testable from ESPN alone. Blocked on
  Phase 3B (Kalshi data).
- **§6.7 Sequential-opportunistic bilateral outperforms** — Not
  tested yet; this run used the strict same-game bilateral
  definition. Follow-up dispatch pending.

### Implications for strategy graduation

- **Strategy 1 (bilateral convergence):** 26.6% at |spread|≤6 is
  comfortably above the 12% kill-criteria graduation bar, and the
  timing-separation concern is resolved in the good direction.
  Remaining risks are all Phase 3B: fillable liquidity at target
  Kalshi prices, Kalshi-bid (not ESPN-implied) bilateral crossing
  rate, MM defense at extremes.
- **Strategy 2 (single-side mean-reversion):** Residual against
  ESPN is +3pp, not +9pp. If §1.1 holds strongly (Kalshi ≈ ESPN
  to within ~1pp), the Kalshi residual lands ~+3pp — below the
  +5pp graduation threshold in `KILL_CRITERIA_draft.md` but above
  the +3pp kill line. Gray zone. Phase 3B is now more
  load-bearing than anticipated. The +5pp graduation bar may
  warrant re-derivation from first-principles EV-after-costs
  rather than staying anchored to a Stern-haircut guess — a
  discussion to have before Phase 3B results land, not after.
- **Strategy 3 (active management):** Not tested by this
  analysis. Requires Kalshi price oscillation data from
  Phase 3B.

### Open items

- **9 missing games audit.** 1,243 in master → 1,234 with WP
  data. 0.7% of dataset. Probably benign (empty ESPN WP feed,
  postponed games, preseason bleed-through), but a silent
  zero-data case is exactly the shape a systematic scraper bug
  would take. Quick check: `find data/espn_wp -size 0 -o -size
  -200c` plus eyeball missing gameIds against
  `nba_master_2025_26.csv`. Do this before the §6 retirement
  dispatch so the coverage number cited there is clean.
- **Future analysis prompts should write to a file on disk**
  (e.g. `docs/analysis_outputs/`) rather than printing to
  stdout. The 3A report currently lives only in chat history;
  reproducing requires re-running the analysis.
- **Pace correlation** (§6.4) and **sequential-opportunistic
  bilateral** (§6.7) follow-ups pending next dispatch.

### Does not supersede

The 2026-04-16 pilot entry (Stern, 2024-25) stands as pilot-era
baseline. This entry reports new findings on different data
(2025-26 regular season) and a different WP model (ESPN). No
prior entry is retired or superseded.

## 2026-04-17 — Phase 3A follow-up: pace (§6.4), sequential bilateral (§6.7), missing-games audit

**Scope.** Closes the Phase 3A analysis arc:

1. Formal §6 retirement lines added to
   `docs/THESIS_open_questions.md` for §6.1, §6.2, §6.3 (from the
   Phase 3A entry), §6.4 and §6.7 (from the follow-up).
2. 9-missing-games audit — confirms whether the 1,234 / 1,243
   coverage number cited in the Phase 3A entry stands and whether
   the gap is benign.
3. This entry.

§6.5 and §6.6 remain open, blocked on Phase 3B (Kalshi data).

**Source analyses:** Phase 3A entry above; `docs/analysis_outputs/3a_followup_2026_04_17.md`.

### §6.4 pace correlation — denied

Team pace (2025-26 regular season, basketball-reference) vs
bilateral <0.20 involvement rate (|spread|≤6 subset):

- Primary (n=29, OKC excluded at n=8 competitive games):
  Spearman ρ = **+0.063** (p = 0.75), Pearson r = +0.080
  (p = 0.68).
- Including OKC (n=30): ρ = +0.071 (p = 0.71).

Effectively zero. The ranked table contains no monotonic pattern:
MIA ranks #1 in pace and #18 in involvement; HOU ranks #29 in
pace and #5 in involvement; BOS ranks #30 in pace and #10 in
involvement. The Top-5 / Bottom-5 cluster that prompted the
hypothesis was noise.

**Implication.** No pace-based game-selection heuristic falls out
of this data. The Bottom-5 involvement ranks (TOR / NYK / SAC /
DET / BKN) skew toward lower-quality teams in games that don't
flip — potentially a team-quality-variance signal — but the data
here doesn't support any specific replacement hypothesis. Not
worth chasing absent an independent reason to.

### §6.7 sequential-opportunistic bilateral — confirmed, reframed larger

Three bilateral definitions tested across a 10-pair threshold
grid (see follow-up MD for full table). Headline numbers at
|spread|≤6:

| (X, Y)       | Strict | Sequential | Asymmetric any-order |
|--------------|--------|------------|----------------------|
| (0.20, 0.20) | 26.6%  | 26.6%      | 26.6%                |
| (0.15, 0.15) | 17.1%  | 17.1%      | 17.1%                |
| (0.15, 0.30) | 17.1%  | 24.4%      | 47.5%                |
| (0.20, 0.30) | 26.6%  | 34.2%      | 49.0%                |
| (0.20, 0.35) | 26.6%  | 36.8%      | 58.5%                |

Aggregate EV per competitive game (opportunity rate × taker-
taker net per trade, from the FEES.md formula, no spread cost
yet):

- Strict (0.20, 0.20): 0.266 × $57.74 ≈ **$15.36 / game**
- Asymmetric (0.20, 0.30): 0.490 × $47.40 ≈ **$23.23 / game** (+51%)
- Asymmetric (0.15, 0.30): 0.475 × $52.63 ≈ **$25.00 / game** (+63%)
- Asymmetric (0.20, 0.35): 0.585 × $42.27 ≈ **$24.73 / game** (+61%)

**Methodology note.** The "sequential operational" definition the
hypothesis originally proposed — requiring the tighter-X leg to
come first — is more restrictive than the operationally relevant
policy. A well-designed policy entering the first leg on
whichever side dips below Y first, then seeking the other leg at
X, captures close to the asymmetric any-order rate. The real
operational rate for Strategy 1 sits between sequential and
asymmetric any-order, much closer to the ceiling. Future strategy
spec writing should not use the sequential-definition numbers as
the operational rate — they're a conservative floor.

**Implication.** Strategy 1's addressable universe is ~50% larger
than the strict-bilateral frame suggested. Under the operational
definition at (0.20, 0.30) on |spread|≤6 games, Phase 3B would
need to produce a ~75% liquidity haircut (from 49.0% nominal to
<12% effective) to push Strategy 1 below the kill-criteria
graduation bar — a high bar. Graduation probability meaningfully
up from the 3A read.

### 9-missing-games audit

**Audit flagged for investigation — open item NOT closed.**
`data/nba_master_2025_26.csv` contains 1,243 gameIds;
`data/espn_wp/` contains 1,243 WP files, of which **9 are empty
(0 bytes)**. Gap after the Phase 3A join is 9 games.

Findings diagnose the gap but flag a downstream idempotency bug:

- **4 of 9** are 2026-02-15 All-Star Rising Stars exhibitions
  (teams `STARS` / `STRIPES` / `WORLD`, gameIds 401838140-43).
  ESPN does not provide a WP feed for these exhibition formats.
  PBP scraped successfully (~75-82 KB each). **Benign.**
- **4 of 9** are postponed/cancelled games with score 0-0 and
  empty PBP files (401810384 CHI-MIA 2026-01-08, 401810499
  MIN-GSW 2026-01-24, 401810506 MEM-DEN 2026-01-25, 401810507
  MIL-DAL 2026-01-25). Games remain in the master CSV but were
  never played. **Benign.**
- **1 of 9** is a real completed game with missing WP feed:
  401810469 CHI 138 - LAC 110 on 2026-01-20. PBP present
  (242 KB, 514 plays); WP empty. Single ESPN WP feed gap — the
  kind of one-off the Phase 3A entry predicted. Not recoverable
  unless ESPN backfills its own WP data.

Missing gameIds:

| gameId    | date       | away    | home    | \|spread\| |
|-----------|------------|---------|---------|----------|
| 401810384 | 2026-01-08 | MIA     | CHI     | 7.0      |
| 401810469 | 2026-01-20 | LAC     | CHI     | 2.5      |
| 401810499 | 2026-01-24 | GSW     | MIN     | —        |
| 401810506 | 2026-01-25 | DEN     | MEM     | —        |
| 401810507 | 2026-01-25 | DAL     | MIL     | —        |
| 401838140 | 2026-02-15 | WORLD   | STARS   | —        |
| 401838141 | 2026-02-15 | STARS   | STRIPES | —        |
| 401838142 | 2026-02-15 | WORLD   | STRIPES | —        |
| 401838143 | 2026-02-15 | STARS   | STRIPES | —        |

Four games on 2026-02-15 share a date (triggers the
cluster-suspicious rule), but the cluster has a clean
explanation — all four are All-Star tournament games on the
same night, not a scraper-block pattern.

**Action — idempotency bug confirmed.** `scrapers/espn_backfill.py`
checks file existence only in its skip logic, not file size or
content. Empty WP files are treated as successful scrapes, so
re-running the backfill will NOT re-attempt 401810469 (the one
recoverable game if ESPN ever populates its WP feed for it).
Follow-up dispatch should change the skip predicate from
"`wp_path.exists()`" to "`wp_path.exists() and
wp_path.stat().st_size > 0`" (or equivalent), so transient
empty-result scrapes get retried on subsequent runs. The
exhibition-game and postponement-game empties would still
correctly short-circuit after one retry because ESPN's response
will remain empty for those — a cheap cost for a correctness win.

**Coverage conclusion.** The 1,234 / 1,243 Phase 3A coverage
cited above is accurate. The 9 missing games break down as 8
non-recoverable (exhibitions + postponements) and 1 ESPN-gap
(401810469). No systematic scraper failure; one backfill-
idempotency bug to fix in a separate dispatch. Open item remains
open pending the backfill fix.

### Implications for strategy graduation (rollup)

- **Strategy 1 (bilateral convergence):** graduation materially
  less suspect after §6.7's reframing. Phase 3B liquidity numbers
  remain load-bearing but the bar is now 75% haircut, not 54%.
- **Strategy 2 (single-side mean-reversion):** unchanged from the
  Phase 3A entry. Sits at +3pp residual vs ESPN; Kalshi residual
  still the load-bearing unknown; §1.4 spread-heterogeneity
  analysis may restructure the entry rule.
- **Strategy 3 (active management):** not addressed by this
  analysis. Requires Kalshi oscillation data from Phase 3B.

### Open items

- §1.4 retirement analyses (spread anchoring) — three sub-
  analyses listed in `THESIS_open_questions.md` §1.4. Runnable
  from existing ESPN data before Phase 3B.
- Kalshi logger first-run verification still pending — evening
  block 2026-04-17 was scheduled for GSW-PHX + CHA-ORL. Check
  `data/orderbook_snapshots/2026-04-17.jsonl` on main.
- Phase 3B scoping — deferred until Kalshi data accumulates
  (target: 10–20 games).
- `espn_backfill.py` skip-logic fix — detect empty WP files and
  re-attempt on subsequent runs. Small, surgical, deferred to
  its own dispatch.

### Does not supersede

The 2026-04-17 Phase 3A entry stands. This entry adds follow-up
findings and closes the three open items listed in that entry
(pace, sequential, missing-games audit).

## 2026-04-18 — Phase 3B smoke test: paired Kalshi-ESPN analysis (n=4 usable games)

**Data:** 6 games matched (CHA-ORL, GSW-PHX from 4/17; TOR-CLE,
MIN-DEN, ATL-NYK, HOU-LAL from 4/18). 4 produced usable paired
data (MIN-DEN: logger not running; ATL-NYK: stale pricing, only
46 obs at 0.995/0.005). 2,304 paired observations total via
as-of merge (300s backward tolerance) of Kalshi snapshots against
ESPN WP at matched wallclock timestamps.

### Key finding: Kalshi-ESPN compression

Kalshi is systematically less extreme than ESPN during live play.
Residual (Kalshi mid − ESPN WP) correlates with distance from
0.50: correlation = −0.463 at n=6 (−0.685 at n=2). Symmetric
and monotonic.

Stratified residual at n=4 usable games (pooled home + away):

| ESPN WP bucket | n | mean Kalshi | residual (pp) |
|----------------|---|-------------|---------------|
| (0.075, 0.10] | 48 | 0.186 | +9.95 |
| (0.10, 0.125] | 68 | 0.246 | +13.28 |
| (0.125, 0.15] | 47 | 0.242 | +10.85 |
| (0.15, 0.20] | 83 | 0.272 | +9.99 |
| (0.20, 0.25] | 59 | 0.298 | +7.36 |
| (0.25, 0.35] | 155 | 0.318 | +1.52 |
| (0.35, 0.50] | 181 | 0.406 | −0.96 |
| (0.75, 0.85] | 141 | 0.718 | −8.86 |
| (0.85, 0.90] | 117 | 0.757 | −12.19 |

Pattern moderated from n=2 (blowouts only) to n=4 (added one
competitive game, HOU-LAL). Middle-range buckets (0.25-0.50)
collapsed toward zero with competitive-game data. Tail compression
(+10-13pp at low WP) persisted.

### §2.1 liquidity first read

At Kalshi mid ≤ 0.20: mean `yes_bid_size_fp` ranged from 85k
(TOR-CLE) to 237k (HOU-LAL). Meaningful depth at Strategy 1/2
entry prices — not the "thin book at extremes" scenario.

### Pipeline validation

Market complement check (home mid + away mid) within 1 tick
(mean |dev| 0.002-0.004). Screenshot cross-check confirmed at
CHA-ORL Q1 break: Kalshi CHA 17% vs ESPN CHA 8.6% (user
screenshots matched to 0.5pp).

### Implications

- §1.1 (Kalshi ≈ ESPN): denied in-game at the tails, but the
  pilot's "within ~1pp" observations happened to land in a
  narrow bucket where the residual IS small (~0.50 WP zone).
- The relevant question became: is Kalshi the outlier, or is
  ESPN? → Answered by the sportsbook backfill (next entry).

### Does not supersede

The Phase 3A and 3A follow-up entries stand. This entry adds
the first paired Kalshi-ESPN analysis.

## 2026-04-19 — Sportsbook backfill: ESPN is the outlier, not Kalshi

**Data:** 30 bilateral <0.20 games (|spread|≤6) from the Phase
3A population of 146, stratified across season thirds and spread
buckets. 57 dip observations (2 per game, minus 1 failure). Each
observation: Odds API historical h2h at the exact wallclock
timestamp of the ESPN WP minimum, no-vig normalized across 1-8
US sportsbooks per snapshot. 341 fresh bookmaker quotes (67
stale excluded). ~600 API credits consumed.

### Key finding: sportsbooks match Kalshi, not ESPN

| ESPN WP bucket at dip | n | mean ESPN | mean SB | residual (pp) |
|----------------------|---|-----------|---------|---------------|
| (0, 0.05] | 30 | 0.003 | 0.097 | +9.35 |
| (0.05, 0.10] | 5 | 0.084 | 0.235 | +15.12 |
| (0.10, 0.15] | 9 | 0.125 | 0.283 | +15.75 |
| (0.15, 0.20] | 13 | 0.175 | 0.343 | +16.86 |

Pooled mean residual: +12.58pp (median +11.53pp). Sportsbooks
price the underdog +10-17pp above ESPN at the bilateral dip
moments — matching the Kalshi compression pattern to within
noise.

### What this settles

- **ESPN is the outlier.** Kalshi, FanDuel, DraftKings, BetMGM,
  Caesars, and the rest all agree with each other. ESPN's WP
  model swings harder with game state than every real-money
  market.
- **§1.1 reframed.** The correct claim is "Kalshi ≈ sportsbook
  consensus" (supported), not "Kalshi ≈ ESPN" (denied). The
  thesis's original framing was comparing against the wrong
  benchmark.
- **Strategy 2 is effectively dead.** The +3pp ESPN-vs-actual
  residual that was Strategy 2's basis gets absorbed entirely
  by the +10-17pp gap between ESPN and real-money markets.
  Sportsbooks/Kalshi price these moments at ~20-34%, well
  above the ~13% actual win rate. No positive residual to
  exploit.
- **Strategy 1 needs recalibration.** The 26.6% bilateral rate
  was measured on ESPN WP. Real-money markets show those same
  moments at substantially higher prices, meaning bilateral
  <$0.20 on Kalshi is much rarer than ESPN suggested.

### Cross-book consensus quality

Mean cross-book std: 0.033 (3.3pp). Mean overround: 1.055.
Sportsbooks agree tightly with each other at extreme game
states — the consensus signal is clean.

### Does not supersede

The Phase 3B smoke test entry stands. This entry identifies
which source is the outlier.

## 2026-04-19 — Strategy 1 recalibrated bilateral analysis

**Data:** Full 2025-26 ESPN dataset (1,234 games, 602,167 WP
observations), transformed via the 57-point ESPN→sportsbook
calibration mapping (PchipInterpolator, symmetric, anchored at
(0,0) and (0.5, 0.5)). Bilateral analysis and §6.7 asymmetric-
any-order re-run at sportsbook-denominated thresholds.

### Key finding: Strategy 1 survives but is marginal

Optimal operating point: (0.25, 0.35) sportsbook-denominated.

| Metric | ESPN (0.20, 0.30) | SB-calibrated (0.25, 0.35) |
|--------|-------------------|----------------------------|
| Opportunity rate (\|spread\|≤6) | 49.0% | 17.7% |
| Gross per trade | $50.00 | $40.00 |
| Net per trade (after fees) | $47.40 | $37.08 |
| EV per competitive game | $23.23 | $6.55 |
| EV per game (−1¢ spread) | — | $6.20 |

72% reduction in EV per game from recalibration. Strategy 1 is
not dead (positive EV at ~$6.55/game on 100-contract sizing),
but is marginal — liquidity haircuts and realized spreads from
Phase 3B data could push this below viability.

### Calibration mapping reference points

| ESPN WP | Mapped SB WP |
|---------|-------------|
| 0.05 | 0.195 |
| 0.10 | 0.325 |
| 0.15 | 0.342 |
| 0.20 | 0.467 |

### Caveat

The 0.10-0.15 ESPN range shows a plateau in the mapping (both
mapping to ~0.33-0.34 SB). This is likely interpolation
behavior from sparse calibration data in that range, not a real
feature of the pricing relationship. More backfill data would
smooth the curve but wouldn't change the directional finding.

### Open items

- Phase 3B formal (≥10 games of Kalshi data): test whether
  realized bilateral opportunities at (0.25, 0.35) match the
  17.7% rate, and measure realized spreads at those prices.
- Strategy 3 scoping: swing-trading analysis on accumulated
  Kalshi oscillation data. Increasingly the priority given
  Strategy 1's marginal status and Strategy 2's kill signal.

### Does not supersede

All prior entries stand. This entry recalibrates Strategy 1
using the sportsbook backfill finding.

## 2026-04-19 — Strategy 3 oscillation analysis: HOU-LAL deep dive (n=1)

**Data:** HOU-LAL 2026-04-18 Kalshi orderbook snapshots (30s
cadence, 277 snapshots per side over the 138-min live window
00:48 → 03:06 UTC 4/19). First oscillation characterization on
actual Kalshi data for Strategy 3 scoping.

### Swing activity

Detected via `scipy.signal.find_peaks` with prominence filtering
(robust to the many tick-identical plateaus at $0.01 bid/ask
granularity):

- **41 swings ≥ $0.02** total (22 HOU + 19 LAL).
- **10 swings ≥ $0.10** magnitude. Median magnitude of these
  larger swings: $0.200. Max: $0.230 (HOU final drop).
- Duration: median 8-10 min per swing; longest $0.20 swing ran
  26 min (01:42 → 02:08 UTC — HOU comeback from $0.325 to
  $0.525 while LAL fell $0.675 → $0.475).

Raw oscillation magnitude looks promising — 10 ≥$0.10 swings
in one 138-min game is plenty of raw material for a
swing-trading rule.

### Round-trip round-trips at entry ≤$0.30

**Zero complete round-trips** across all 12 entry × exit
threshold pairs tested (entries $0.15/$0.20/$0.25/$0.30 × exits
+$0.10/+$0.15/+$0.20). Reasons:

- HOU dipped below $0.30 only late (after 02:20 UTC) and never
  rebounded above $0.40 before settling at $0.005.
- LAL's live-window minimum mid was $0.405 — never entered the
  tested threshold range.

The HOU $0.17-$0.20 comeback (01:42 → 02:08) is a textbook
swing-trading opportunity — but it originated from a HOU mid of
$0.325, above the tested entry ceiling of $0.30. Follow-up
analysis should include wider entry thresholds
(e.g., up to $0.45) or a "buy the dip regardless of side"
asymmetric rule to capture symmetric swings.

### Spreads at Strategy 3 entry zones

| Bucket | n | Median spread | Mean spread / mid |
|--------|---|---------------|-------------------|
| ≤ $0.10 | 31 | $0.0100 | 29.4% |
| (0.15, 0.20] | 17 | $0.0100 | 5.7% |
| (0.20, 0.25] | 19 | $0.0100 | 4.9% |
| (0.25, 0.30] | 19 | $0.0100 | 4.0% |

Spread is tick-wide ($0.01) almost everywhere — max observed
$0.02 (two ticks). As a percentage of mid, the (0.15, 0.30]
zone sits at 4-6% — manageable for Strategy 3 economics. The
≤$0.10 zone is 29% spread-to-mid — too expensive to round-trip.

### Book depth at entry zones

Variable. `yes_bid_size_fp` ≥ 50,000 (kill-criteria fill-size
threshold) in:
- 77% of snapshots at mid ≤ $0.10
- 59% at (0.15, 0.20]
- 16% at (0.20, 0.25]  ⚠
- 37% at (0.25, 0.30]  ⚠

Only the extreme-low-price zone has reliably ≥50k depth. The
Strategy 3 entry zone around (0.20, 0.25] shows depth ≥50k in
only 16% of snapshots — meaningful depth concern worth watching
across more games.

### Viability scorecard (n=1, not statistically meaningful)

| Criterion | Threshold | Observed | Status |
|---|---|---|---|
| Round-trip frequency | ≥ 8% competitive games | n/a (n=1) | — |
| Swing magnitude (median ≥$0.10) | ≥ $0.10 capture | $0.200 | ✓ Pass |
| Realized spread at entry (median) | < $0.03 | $0.0100 | ✓ Pass |
| Book depth ≥ 50k (% at mid ≤$0.30) | ≥ 50% | 50% | ≈ Borderline |
| Hold time (median) | ≥ 90 seconds | no complete trips | — |

### Implications for Strategy 3

- **Oscillation activity is real.** 10 meaningful swings in 138
  min of live play validates the premise that Kalshi prices
  oscillate enough to swing-trade in principle.
- **Game shape matters.** HOU-LAL was a one-way-ish game (LAL
  won by 9, HOU's only meaningful comeback put it back to 52%
  but never above). Buy-deep-underdog-and-wait patterns produced
  zero fills. Need competitive back-and-forth games for the
  pattern to work.
- **Entry-threshold scope reconsideration.** The $0.15-$0.30
  entry range caught none of the actual game swings. The $0.17
  HOU comeback from $0.325 suggests threshold ceiling should
  probably rise to ~$0.45, OR the strategy should be
  reformulated as "buy the side that just dipped at least $0.10
  regardless of absolute price level."
- **Spread economics are manageable** in the middle-price zones
  ($0.15-$0.30). Depth is the larger unknown — 16% of (0.20,
  0.25] snapshots had <50k resting size.
- **n=1 is emphatically not enough.** Extend this analysis to
  the CHA-ORL / GSW-PHX 4/17 Play-Ins and to a handful of
  competitive regular-season games (once per-event-file logger
  data accumulates) before any Strategy 3 design decision.

### Methodology notes for future Strategy 3 analyses

- Tip-detection via volume rate failed twice on this n=1 case
  (pre-tip flow spikes produce false positives; logger gap
  boundaries produce edge artifacts). Script anchors on ESPN-
  verified tip time instead. Multi-game version needs a more
  robust detector — possibly "first sustained 10-min window
  with ≥200 fp/sec AND mid variance ≥ 0.005," or a simple
  ESPN-PBP-wallclock match.
- Swing detection initially used strict-inequality local
  extrema; failed on tick-granularity plateaus. Switched to
  `scipy.signal.find_peaks` with prominence filtering — works
  cleanly.

### Mid-range re-run (same session)

Original threshold grid ($0.15–$0.30 entry) produced zero
round-trips — swings happen in the competitive mid-range, not
at the extremes. Re-ran with entry $0.30–$0.45 / exit
entry+$0.10 to entry+$0.15.

**5 completed round-trips** across 8 mid-range pairs. Best
performers (pooled mean net maker-maker = **$14.55/trade**):

| Entry | Exit | Hold (min) | Net maker | MAE |
|-------|------|------------|-----------|-----|
| 0.35 | 0.45 | 23.0 | $13.16 | — |
| 0.35 | 0.50 | 41.0 | $17.16 | — |
| 0.40 | 0.50 | 45.5 | $12.14 | — |
| 0.45 | 0.55 |  8.0 | $12.13 | — |
| 0.45 | 0.60 | 20.0 | ≈$13   | — |

- **Mid-range round-trips exist and clear fees** on HOU-LAL.
  (0.35, 0.50) produced one 41-min hold at a clean $17.16 net
  maker-maker profit on 100 contracts.
- **Max adverse excursion (MAE) pooled across 5 trips:**
  median drawdown 11.6% of entry (≈ $0.04 on a $0.35-0.45 entry),
  max 22.8% of entry. Manageable — the worst trip required
  stomaching a ~$9 unrealized loss before the exit signal fired.
- **Hold times range 8–45 min.** Median ~23 min. Well above the
  90-second kill-criteria floor.
- **Scorecard verdict (mid-range rows, n=1):** ≥1 round-trip at
  (0.35, 0.50) ✓, pooled maker net > $0 ✓ ($14.55), median MAE
  < 50% of entry ✓ (11.6%). All three mid-range checks pass on
  n=1.

**One-line verdict:** mid-range swing trading looks mechanically
viable on HOU-LAL — positive-EV round-trips do exist at
realistic competitive-game entry prices, with manageable
drawdowns. This is a pipeline validation and a proof-of-concept,
not a graduation signal. Multi-game confirmation (≥5-10
competitive games) is the next gate.

### Does not supersede

All prior entries stand. This is the first Strategy 3-specific
analysis.
