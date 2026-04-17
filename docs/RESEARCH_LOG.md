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
