# NBAgent-Live — Research Log

## 2026-04-23 — S3 reframed as extended S4A entry range + breakeven ratchet validated

Three-pass investigation in `docs/analysis_outputs/s3_reframed_extended_entry.md`
(Parts 1–15). Reframed S3 not as "buy at $0.40 and hope" but
as the $0.40–$0.50 tail of the S4A favorite-recovery curve.

**Pass 1 (Parts 1–6):** extending the S4A entry band from
$0.50–$0.75 down to $0.40–$0.75 adds ~$500/yr on pooled EV
but the $0.40–$0.50 sub-band is marginal alone. $0.45–$0.50
is a clean incremental; $0.40–$0.45 adds volume without
alpha.

**Pass 2 (Parts 7–11):** tested 12 variants (dip depth,
trailing window, re-entry suppression, spread sub-buckets).
No variant beats the baseline $0.08 / 180s / same re-entry
rule. Robust parameter ridge confirmed.

**Pass 3 (Parts 12–15):** breakeven ratchet stop. Once the
favorite rises ≥ $0.08 above entry price, move the stop to
entry + $0.01. On the 404-game pool:

| Metric | No ratchet | Ratchet +$0.08 | Δ |
|--------|-----------|----------------|---|
| Entries | 311 | 358 | +47 |
| Target | 179 | 149 | −30 |
| Full stops | 132 | 88 | −44 |
| Ratchet scratches | — | 121 | +121 |
| Hit rate | 57.6% | 41.6% | −16.0 |
| Mean P&L | +$3.13 | +$3.92 | +$0.79 |
| Annual EV (pool) | +$1,320 | +$1,899 | +$579 |

Holdout: 6/6 seeds positive (42–47, 270/134 train/test).
Trigger sensitivity: +$0.05 through +$0.20 all positive;
+$0.08 optimal, curve shallow.

**Engine implementation:** `engine/position_manager.py`
extended with Position-level ratchet state, maker/taker fee
split (maker on entry/target/ratchet_stop, taker on
full_stop), target-level fills ($0.90 exactly). `engine/
replay.py` validates both modes PASS against expected
numbers:
- `--ratchet 0.08`: 358/149/88/121, hit 41.62%,
  mean $+3.9153, annual $+1,898.59 (vs expected $+1,899).
- `--ratchet 0`: 311/179/132/0, hit 57.56%, mean $+3.1336,
  annual $+1,320.04.

Baseline differs from the drawdown analysis's $+2.83/$+1,193
because the engine uses target-level fills ($0.90 exactly)
on target exits, not observed overshoot price — a more
realistic model for resting limit orders. Reconciliation
documented in `engine/replay.py` module docstring.

Spec updated: `docs/STRATEGY4_SPEC.md` §2 (ratchet row),
§5 note, new §5A, §9 annual EV table, "last updated" stamp.

## 2026-04-22 — Strategy 4 spread expansion Path B (Kalshi-confirmed)

Re-ran Part 8 on the Kalshi trade-tape data from the
full-season backfill (`--part8 --path-b`). 404 games across
all |spread| buckets have usable paired timeseries; 233 of
those are in the expansion zone (|spread|>6). Report:
`docs/analysis_outputs/strategy4_spread_expansion_kalshi.md`.

**Headline result: the favorite-recovery pattern holds across
every spread bucket on Kalshi-confirmed data. Path A's ESPN
proxy systematically under-predicted EV (and was outright
wrong-signed at narrow spreads).**

Path B per-bucket (hit % / mean P&L / scaled annual EV):

| Bucket | Games | Entries | Hit % | Mean | Annual EV |
|---|---:|---:|---:|---:|---:|
| 1.0–2.0 | 36 | 29 | 51.7% | +$1.59 | +$702 |
| 2.5–3.5 | 69 | 71 | 47.9% | +$2.57 | +$1,446 |
| 4.0–5.0 | 31 | 29 | 48.3% | +$2.65 | +$1,357 |
| 5.5–6.0 | 35 | 37 | 64.9% | +$6.17 | +$3,570 |
| 6.5–8.0 | 46 | 43 | 58.1% | +$4.14 | +$2,116 |
| 8.5–10.0 | 38 | 36 | 58.3% | +$0.82 | +$425 |
| 10.5+ | 149 | 66 | 69.7% | +$4.55 | +$1,103 |
| **Existing (≤6)** | **171** | **166** | **52.4%** | **+$3.21** | **+$1,708** |
| **Expansion (>6)** | **233** | **145** | **61.4%** | **+$3.26** | **+$3,644** |
| **All buckets** | **404** | **311** | **56.6%** | **+$3.24** | **+$10,718** |

(Annual EV scaling inherits the `summarize_s4a` convention of
`mean × entries/game × 0.445 × 1230` competitive-rate
projection. Bucket-level EV is directional — the across-bucket
comparison and the existing/expansion split are the load-bearing
numbers, not each cell's dollar figure.)

**Parity check:** Path B |spread|≤6 reproduces the engine replay
trade-for-trade (171 games, 166 entries, 52.4% hit, +$3.21 mean,
+$1,708 annual EV). Confirms the Path B pipeline is consuming
the same `fav_kalshi_vwap` column the engine uses.

**Path A vs Path B on overlap games (Table 6 of the report):**
the ESPN proxy understated P&L in every bucket, dramatically at
narrow spreads. At |spread|=1.0–2.0: ESPN 36.1% / −$3.71 vs
Kalshi 51.7% / +$1.59. At 5.5–6.0: ESPN 54.3% / +$2.19 vs
Kalshi 64.9% / +$6.17. The ESPN proxy fires more entries at
worse effective prices than Kalshi does — exactly as the
compression mapping predicts.

**Strategic takeaways:**

- **S4A EV at least doubles** once the expansion universe is
  included with Kalshi-confirmed pricing: headline ~+$1,886/yr
  on the 165-game competitive dataset becomes +$7,075
  (existing-universe Path B rollup) + $3,644 expansion ≈
  +$10,718/yr projected if the strategy were deployed across
  all spread buckets at competitive-rate scaling.
- **The 5.5–6.0 bucket is the single best cell** (+$3,570/yr)
  in the Path B breakdown, not a wider-spread bucket. The
  pattern strengthens with spread up to that point, then
  plateaus; 10.5+ is strong on hit rate (69.7%) but low on
  entry rate (0.44/game) so its annual EV is moderate.
- **Path A's strategic signal was right direction but wrong
  magnitude.** The "pattern strengthens at wider spreads"
  thesis from Path A is confirmed; the negative absolute
  numbers Path A produced were the ESPN proxy's fault, not
  the strategy's.
- **Next step for STRATEGY4_SPEC.md:** the |spread| ≤ 6
  constraint in §2 should be relaxed or removed. Add a section
  documenting per-bucket expected EV and position-sizing
  guidance for wider spreads. Defer actual spec update until
  after a second playoff week of paper-trading data
  accumulates.

## 2026-04-22 — Phase 4a S4A engine: replay validation

First runnable build of the S4A paper-trading engine
(`engine/s4a_signal.py`, `engine/position_manager.py`,
`engine/live_runner.py`) with a replay harness
(`engine/replay.py`) that drives the full Kalshi paired
dataset through the same detector + manager used by the
live runner, and compares trade-for-trade against the
authoritative offline simulator
(`analysis.strategy4_dip_recovery::simulate_s4a`).

**Replay PASS.** 171-game current dataset (grew from 165
during the in-flight full-season backfill). Engine and
offline agree on every number:

| Metric | Engine | Offline | Spec (snapshot) |
|---|---:|---:|---:|
| Entries | 166 | 166 | 161 |
| Hit rate | 52.41% | 52.41% | 52.8% |
| Mean P&L | +$3.2149 | +$3.2149 | +$3.53 |
| Annual EV | +$1,707.83 | +$1,707.83 | +$1,886 |

The drift vs STRATEGY4_SPEC.md (−$178 annual EV) is a
dataset change: 6 new games entered the paired dataset
between 2026-04-21 (spec) and the replay run, and both
engine and offline agree on the new population. When the
backfill completes and the ~60-day window stabilizes, the
STRATEGY4_SPEC.md headline number should be refreshed.

**Interpretation.** The engine faithfully reproduces the
offline logic to within float rounding:

- Trailing max: time-windowed deque with strict older-than
  eviction matches `pandas.rolling(6, min_periods=1)` for
  evenly-spaced 30s ticks (6 observations per window).
- Entry decision: `dip ≥ $0.08 AND entry_lo ≤ price ≤
  entry_hi` with position-open re-entry guarded by
  `entries_this_game < 2`.
- Exit: target $0.90 / stop $0.40, maker fee on both legs.
- End-of-game: ≥$0.95 → settle $1.00 no fee, ≤$0.05 →
  settle $0.00 no fee, else mid with fee.

Equivalence means the paper-trading engine will, in live
operation, produce the same decisions the offline sweep
identified — subject to live data quality (missed ticks,
bid-ask spread vs VWAP, execution latency). The paper
journal will surface any such gap during live runs.

**Next.** First live paper-trading session runs during
tonight's NBA slate. Morning review of
`data/paper_trades/YYYY-MM-DD.jsonl` against actual Kalshi
market moves is the operator's go/no-go for extending to
further paper sessions and then Phase 4b (simulated fills
at real Kalshi quotes) / Phase 4c (real money, capped).

## 2026-04-22 — Strategy 4 halftime entry study (Part 7)

Tested whether a halftime-triggered entry (favorite's Kalshi VWAP
in $0.50–$0.75 over the final 60s of Q2) extends S4A profitably.
165 competitive games; 54 (32.7%) produced a halftime entry.
Report: `docs/analysis_outputs/strategy4_halftime_entry.md`.

**Headline result: halftime entry is NOT profitable as an
extension or replacement for the S4A dip trigger.**

- Halftime-only: 54 entries, 42.6% hit, mean −$1.80, annual EV
  **−$323**. Compare S4A dip best config on the same universe:
  161 entries, 52.8% hit, +$3.53, +$1,886/yr.
- Combined (halftime entry + S4A dip in Q3+): 137 entries,
  +$2.47 mean, annual EV **+$1,121** — below baseline S4A's
  +$1,886 because the negative halftime leg drags overall
  performance and the post-halftime-only dip scan misses the
  pre-halftime dip entries that baseline S4A catches in
  Q1/Q2.
- Halftime-to-prior delta bucketing did NOT rescue the halftime
  signal. Even the "fav dropped ≥$0.10 from pre-game" bucket
  (the strongest disruption signal) ran at 30.0% hit and
  −$0.58 mean. The pre-game anchor is not the right reference
  frame for halftime entries. This mirrors the Part 5 finding
  that prior-weighting doesn't help S4A.
- Of 27 S4A dip-triggered entries that fire in Q3, only 2
  (7.4%) fire in the first 60s and 5 (18.5%) in the first
  120s — the existing S4A dip captures very few
  halftime-adjacent moments, so the two triggers are mostly
  disjoint in time. The halftime-triggered subset is where
  the losses concentrate.

**Interpretation.** Halftime is a known coordination point
where market microstructure likely tightens (bid-ask compresses,
MM re-anchors after the break). The 42.6% hit rate vs 52.8%
for dip-triggered suggests halftime entries lack the "recent
disruption" signal that makes the dip trigger work —
entering at a scheduled anchor point is statistically
similar to entering at a random Q2-end price, which is not
edge.

**Conclusion.** Do not add halftime entry to the Phase 4a
ruleset. Keep S4A as the dip-triggered variant per
STRATEGY4_SPEC §3.

## 2026-04-22 — Strategy 4 spread expansion Path A (Part 8, ESPN-only)

Simulated S4A on ESPN win-probability as a directional proxy
for Kalshi price across 1,135 games spanning all |spread|
buckets (1.0–10.5+). Purpose: detect whether the favorite-
recovery pattern exists beyond the existing |spread|≤6
universe before committing to the full-season Kalshi
backfill. Report:
`docs/analysis_outputs/strategy4_spread_expansion.md`.

**Headline result: the pattern DIRECTIONALLY appears to
strengthen at wider spreads on ESPN proxy — but the proxy
massively understates Kalshi EV, so these numbers cannot be
used for deployment sizing.**

- **Table 4 sanity gap:** on |spread|≤6 competitive games the
  Kalshi-confirmed S4A result is +$1,886/yr (52.8% hit, +$3.53
  mean). The ESPN proxy on the same spread band produced
  −$2,195/yr (37.8% hit, −$3.30 mean). Gap is ~$4,000/yr;
  the proxy is not calibrated for EV work.
- **Directional monotonicity within the expansion zone:**
  hit rate climbs from 42.5% (6.5–8.0) → 54.5% (8.5–10.0)
  → 58.0% (10.5+). Mean P&L flips from negative to positive
  (+$0.25 at 8.5–10.0, +$0.99 at 10.5+). Entry rate per game
  stays in the 0.84–1.34 range across all buckets.
- **Entry price distribution shifts up with spread:** median
  entry price rises from $0.60 at |spread|=1–2 to $0.71 at
  |spread|=10.5+. Bigger favorites rarely dip far below their
  pre-game anchor, so entries cluster in the upper half of
  the $0.50–$0.75 band.
- **ESPN-scale expansion EV:** −$2,227/yr across |spread|>6
  buckets combined (dominated by 6.5–8.0's −$2,852). The
  higher-spread buckets (8.5+) are modestly positive even on
  the proxy — which, given the proxy's ~$4,000/yr downward
  bias vs Kalshi, hints that Kalshi-confirmed numbers for
  those buckets could be meaningfully positive.

**Key caveat.** The ESPN-to-Kalshi compression is ~5–8pp
deeper in mid WP zones (favorites swing harder on ESPN).
This means ESPN triggers more entries at worse effective
entry prices. The directional signal — "pattern persists or
strengthens with spread" — is informative; the absolute P&L
numbers are not. Path B (Kalshi trade tape on the expanded
dataset) will produce the confirmed numbers once the
full-season backfill completes. Kalshi retention cliff
(~60 days) means only the 2026-02-20 → 2026-04-21 subset
will be retrievable for wider-spread games.

**Next step.** Oliver runs the full-season backfill
(`python -m analysis.wp_vs_kalshi_paired --batch
data/wp_kalshi_paired/matched_games.csv`, ~2–3 hours). After
it completes, a Path B analysis on the expanded Kalshi-paired
dataset will either confirm or refute the expansion thesis
with real trade-tape-derived P&L.

## 2026-04-22 — Full-season Kalshi ticker_matcher expansion

Regenerated `data/wp_kalshi_paired/matched_games.csv` with
the uncapped ticker_matcher (previously filtered to
|spread|≤6). New distribution across the 2025-26 season:

| |spread| bucket | Games |
|---|---:|
| ≤ 6 | 549 |
| 6 – 10 | 297 |
| > 10 | 290 |
| NaN | 101 |
| **Total** | **1,237** |

168 of these games are already cached in
`data/wp_kalshi_paired/`; the remaining ~1,069 are queued for
the batch trade-tape pull. Expected yield after the ~60-day
Kalshi retention cliff: roughly 450–550 of the uncached games
will return non-empty trade tapes. Backfill command:
`python -m analysis.wp_vs_kalshi_paired --batch
data/wp_kalshi_paired/matched_games.csv` (~2–3 hours).

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

### Favorite-side analysis (same session)

Added favorite-side round-trip scans to both HOU-LAL (Kalshi,
Section 3D/3E) and game flow trajectory (ESPN WP, Sections
7/8 behind `--include-favorite` flag). The favorite side has
a structurally different risk profile: a hold-to-resolution
backstop exists (if the favorite wins, an "out-of-the-money"
position at entry 0.60 still settles at $1.00 = +$40/100
contracts). The flip side: if the favorite loses, the position
settles at $0.00 = -$60/100 contracts.

**HOU-LAL favorite-side (LAL, 100 contracts, maker-maker):**

| Entry | n_total | n_completed | n_res_win | n_res_loss | Blended EV |
|-------|---------|-------------|-----------|------------|------------|
| 0.55 | 2 | 2 | 0 | 0 | $18.42 |
| 0.60 | 2 | 2 | 0 | 0 | $20.71 |
| 0.65 | 1 | 1 | 0 | 0 | **$33.25** |

Every LAL position at every tested entry rebounded within the
game window — zero resolution outcomes, zero MAE-triggered
losses. The backstop wasn't needed. Best-pair net $33.25 at
entry 0.65 exit 0.75 is about 2× the underdog-side (0.35, 0.50)
best net ($17.16) from Section 3B. n=1 game, so directionally
interesting but not dispositive.

**Game flow trajectory favorite-side sweep (ESPN WP, N=1,135
non-pickem games with ≥10 obs):**

- **Games with ≥1 completed favorite round-trip: 774 (68.2%)**
  on entry `fav_wp ≤ 0.60`, exit `fav_wp ≥ 0.70`
- **Resolution outcomes**: **62 wins vs 331 losses** — the
  backstop is *adversely selected*. When a position is held to
  resolution, the favorite loses **84%** of the time. This is
  the structural penalty of favorite-side strategy: positions
  that fail to rebound are selection-biased toward favorites
  who went on to lose.
- **Blended mean net (maker, pooled across 2,168 positions):
  $+4.34**. Positive but modest, with a fat left tail from the
  331 resolution losses at −$60 each.
- Comeback bucket remains the most productive shape; by
  construction, a "comeback" game has the favorite dipping
  deeply, so favorite-side entries trigger most often there.

**Net assessment of favorite-side strategy:**

- The *completed round-trip* fraction is profitable and
  frequent (68.2% coverage, positive mean net on completed).
- The *resolution backstop* is **a trap, not a rescue** at
  ESPN-WP thresholds: adverse selection makes resolution
  losses dominate resolution wins by 5.3×.
- Real operational strategy would need either (a) a hard stop
  rule that exits at a loss rather than allowing the
  resolution settlement, or (b) a tighter entry threshold
  that reduces adverse selection (e.g., only enter when
  favorite's WP dips below 0.50, implying a more meaningful
  comeback is in progress rather than a late-game grind).
- ESPN compression caveat applies: a favorite at ESPN 0.60 is
  roughly Kalshi 0.55 in market price terms. The entry /exit
  thresholds shift on Kalshi, and the resolution-win / loss
  ratio likely changes too — this analysis is an upper bound
  for the favorite-side universe, not a production signal.
  Tier 3 Odds API sportsbook-timeseries backfill is the
  validation gate.

### Does not supersede

All prior entries stand. This is the first Strategy 3-specific
analysis.

## 2026-04-19 — Game flow trajectory analysis (ESPN WP, N=1,234)

**Data:** Full 2025-26 regular season ESPN WP timeseries
(1,234 games, tradeable window `sec_rem ≥ 60`). Classified into
5 trajectory-shape buckets and characterized swing + mid-range
round-trip features per bucket. See
`docs/analysis_outputs/strategy3_game_flow_trajectories.md`.

### Bucket distribution

| Bucket | N | % | Mean \|spread\| | Mean final margin |
|--------|---|---|----------------|-------------------|
| Blowout | 393 | 31.8% | 6.6 | 24.7 |
| Comeback | 324 | 26.3% | 4.9 | 6.0 |
| Late collapse | 0 | 0.0% | — | — |
| Back-and-forth | 228 | 18.5% | 4.9 | 8.4 |
| Wire-to-wire | 289 | 23.4% | 5.9 | 9.6 |

**Late collapse bucket is empty.** The definition (loser's WP
> 0.80 in second half AND still lost) is strictly implied by
"winner's min WP < 0.20" (= loser's max WP > 0.80), so
priority-ordered Comeback absorbs every Late collapse candidate.
A useful empirical observation, not a bug — comeback ⊇ late
collapse under these definitions on ESPN WP data.

### Mid-range round-trip rate by bucket

| Bucket | N | % ≥1 round-trip | Mean round-trips/game |
|--------|---|-----------------|----------------------|
| **Comeback** | 324 | **99.7%** | **3.60** |
| **Back-and-forth** | 228 | **97.4%** | **3.28** |
| Wire-to-wire | 289 | 43.9% | 0.66 |
| Blowout | 393 | 28.0% | 0.42 |

Comeback + Back-and-forth together = **552 games (45%)** with
virtually guaranteed round-trips on ESPN WP.

### Pre-game spread as predictor

Spearman |spread| vs oscillation (n=1,135 games with spread
data):

- n_swings ≥ 0.10: ρ = **−0.341** (p < 0.0001)
- total_swing_distance: ρ = **−0.345** (p < 0.0001)
- n_midrange_swings: ρ = **−0.379** (p < 0.0001)

All negative and statistically significant — tighter spread
predicts more oscillation, moderately. Too weak to pick
individual games pre-tip, strong enough to confirm |spread| ≤ 6
is a reasonable universe filter.

### Strategy 3 addressable universe

| Filter | Games | % with ≥1 mid-range round-trip |
|--------|-------|-------------------------------|
| All games | 1,234 | 63.4% (782) |
| \|spread\| ≤ 6 | 549 | 75.2% (413) |
| \|spread\| ≤ 3 | 263 | 76.0% (200) |

**Comeback bucket contributes 51.3% of all round-trips** (1,165
of 2,272 total). That's the single most productive shape.

### Implications for Strategy 3

- **The mid-range oscillation premise is validated at scale.**
  75% of competitive games produce ≥1 mid-range round-trip on
  ESPN WP — a large addressable universe even before applying
  any pre-tip shape prediction.
- **Game selection matters and is partially predictable.** The
  |spread| ≤ 6 filter nearly doubles round-trip rate vs random
  sampling (75.2% vs 63.4%). Adding shape-based filtering
  (Comeback ∪ Back-and-forth captures ~45% of games but ~80%
  of round-trips) further concentrates yield — but requires
  mid-game observation, not pre-tip prediction.
- **Season-scale yield (ESPN terms):** 782 games × ~1.8
  round-trips per round-trip-producing game = ~1,400 round-trip
  events per regular season. At the HOU-LAL deep dive's
  $14.55/trade mean (maker-maker, pre-spread, on 100 contracts),
  upper-bound season yield is ~$20k — but with the ESPN caveat
  halving swing magnitudes, more realistic market-price yield
  is probably 30-50% of that figure, and fill quality, slippage,
  and capital-scaling constraints cut further. Still, the
  order-of-magnitude math is encouraging.

**ESPN caveat (material for all numbers above):** ESPN WP is
more reactive than real-money markets (+10-17pp compression
at the tails per the Phase 3B sportsbook backfill). Absolute
swing counts and round-trip rates are upper bounds on what
Kalshi/FanDuel would show. Relative ranking across buckets and
spread strata should transfer. Tier 3 Odds API sportsbook-
timeseries backfill is the next validation gate.

### Does not supersede

All prior entries stand. Complements the HOU-LAL deep dive
(same date) by answering "does the HOU-LAL pattern generalize?"
at season scale — answer: yes, for comeback and back-and-forth
shapes, and at 75% rates on |spread| ≤ 6.

## 2026-04-19 — Strategy 3 Odds API timeseries (n=15 FanDuel)

**Data:** FanDuel moneyline at 5-min intervals for 15
stratified games via the Odds API historical endpoint.
Report: `docs/analysis_outputs/strategy3_odds_api_timeseries.md`.
Credits used: ~5,564 (of ~10,000 monthly envelope).

### Key findings

**Pooled survival rate: 30.4%** (34 FanDuel round-trips /
112 ESPN round-trips across the same 15 games). Per bucket:
Comeback 31.2%, Back-and-forth 28.3%, Wire-to-wire 42.9%.
Survival rate is approximately uniform across game shapes.

**Best FanDuel-native thresholds:** (0.40, 0.50) produced
46 round-trips (35% more than the ESPN-denominated
0.35→0.50 baseline). (0.45, 0.55) also strong at 47.

**Favorite-side on FanDuel:** pooled blended net **−$18.40**
per position. **Favorite-side killed.** Resolution backstop
is negative EV on market prices. ESPN's +$4.34 blended EV
was a selection-bias artifact — favorites that can't recover
to 0.60 WP are disproportionately losing.

### Revised Strategy 3 universe estimate

2,272 ESPN-visible round-trips × 30.4% market survival =
**~689 market-price round-trips per season**. At the HOU-LAL
reference of $14.55/trade net maker-maker (100 contracts):
**~$10,025/season** at 100-contract sizing. The 30.4% survival
rate has wide CI at n=15 (~18-46%) but even the low end
projects positive annual EV.

### Verdict

Strategy 3 survives translation from ESPN to real-money
market prices. The mid-range operating zone ($0.35-$0.55)
captures most of the surviving universe. Favorite-side
variant is dead.

### Does not supersede

All prior entries stand. This is the first market-price
survival test of Strategy 3.

## 2026-04-19 — Kalshi historical trades probe: HOU-LAL

**Data:** Complete trade tape for HOU-LAL (2026-04-18) via
Kalshi's unauthenticated market trades endpoint
(`GET /markets/trades?ticker=...`). First use of this data
source. 93,838 trades across both sides (HOU: 38,573, LAL:
55,265), spanning 2026-04-14 01:12 UTC → 2026-04-19 03:22 UTC
(market open → settle). Total volume: 29.2M contracts.
Raw data cached at
`data/kalshi_trades/KXNBAGAME-26APR18HOULAL.json` (~23 MB).
Full report:
`docs/analysis_outputs/kalshi_trades_probe_houlal.md`.

### Headline findings

**Trade-size distribution (pooled, n=93,838):** median 45
contracts, mean 311, p90 502, p99 4,103, max 174,669.
Small trades dominate by count (52% of trades are ≤50
contracts) but big trades dominate by volume (the top 2.6%
of trades — the 5,000+ bucket — carry 34% of all contracts).

**Strategy 3 price zone ($0.35–0.55):** 44,629 trades /
11.9M contracts — **40.8% of total volume** sits in the
oscillation band we care about.

**Sizing (a 100-contract order):**
- Above the **66th percentile** of all observed trades
  (median trade = 45 contracts).
- A 100-contract order is ~**0.02%** of the median in-game
  5-min bucket volume (≈ 574k contracts/bucket).
- **100% of in-game 5-min buckets** have a 100-contract
  order at < 1% of bucket volume.
- Conclusion: 100-contract orders are effectively invisible
  in HOU-LAL flow. Even 1,000-contract orders (top 5.7%)
  would be well-absorbed at normal in-game volumes.

**Taker flow:** per-5-min net taker flow (yes_vol − no_vol)
is computed in Section 4 and provides a directional signal
we can cross-reference against WP moves in later analyses.

**Execution-quality cross-reference (Section 6):** 4,348
of 93,838 trades had a snapshot within ±30s (logger only
covered the game day, not the 4-day pre-game tape). Of
matched trades: 94.5% at the posted ask, 5.4% at bid,
~0% mid. Asymmetry likely reflects taker directionality
and snapshot cadence rather than absence of mid fills —
worth revisiting with tighter snapshot pairing on a game
where the logger ran the full market window.

### New capability

Kalshi's market-trades endpoint provides per-trade
resolution data (size, price, taker side, timestamp) for
all settled markets. This is a free, unauthenticated
data source that can retroactively characterize volume
and execution patterns on any completed NBA game market.
Combined with our logger's orderbook snapshots, this gives
trade-level + book-level paired data for execution
analysis. Unlike the logger, this captures the full
lifetime of the market (including days of pre-game price
discovery) regardless of when we started polling.

Endpoint note: the `/historical/trades` path probed first
returned empty for this ticker; `/markets/trades` returns
the full tape. Code uses the latter.

### Does not supersede

All prior entries stand. This adds a new data source and
the first volume/execution characterization of a Kalshi
NBA market.

## 2026-04-19 — Strategy 3 multi-game oscillation (4/19 playoff R1G1, n=4)

**Data:** 4 first-round playoff Game 1s captured by Kalshi
logger at 30s cadence with per-game file split (landed
2026-04-19): ORL@DET, PHI@BOS, PHX@OKC, POR@SAS. Full report:
`docs/analysis_outputs/strategy3_oscillation_multi.md`.

Heuristic tip detection + settlement-run end detection
applied independently per game. Strengthened from the original
prompt spec (which fired on static pre-game price drift) by
adding a rolling-window cumulative-movement requirement
(≥$0.02 movement within last 10 snapshots) — documented
in `analysis/strategy3_oscillation_multi.py`.

### Live-window summary

| Game | Tip (UTC) | Duration | Competitive? |
|------|-----------|---------:|--------------|
| ORL@DET | 22:34 | 145 min | ✓ |
| PHI@BOS | 17:08 | 47 min | — (blowout) |
| PHX@OKC | 19:45 | 37 min | — (blowout) |
| POR@SAS | 01:16 (4/20) | 105 min | — |

Only ORL@DET met the "both mids spent ≥30% of live window in
[0.30, 0.70]" competitive threshold. Other three games were
effective blowouts where settlement-run detection correctly
trimmed the window tight.

### Pooled round-trip economics (at (0.40, 0.50))

- **Round-trip frequency:** 1/4 games (25%) produced ≥1 trip.
- **Total trips pooled:** 2 (both from ORL@DET).
- **Mean net (maker-maker):** **$21.70 / trip** (vs $14.55
  on HOU-LAL reference).
- **Mean hold:** 49 min; **mean MAE:** 17.5% of entry.

At (0.35, 0.45): 3 trips, mean net $20.20, hold 34 min.
At (0.40, 0.55): 1 trip, mean net **$39.28**, hold 104 min.

### Pooled spread + depth (mid ≤ $0.50)

- Median realized spread: **$0.01** (matches HOU-LAL).
- Depth ≥ 50k: **55%** of observations at mid ≤ $0.50
  (above the 50% kill criterion).

### Viability scorecard (all 6 criteria pass)

| Criterion | Threshold | Pooled | Status |
|---|---|---|---|
| RT frequency at (0.40, 0.50) | ≥ 15% | 25% (1/4) | ✓ |
| Net per trip (median, maker) | ≥ $5 | $21.70 | ✓ |
| Realized spread (median) | ≤ $0.02 | $0.01 | ✓ |
| Depth (% ≥ 50k) | ≥ 50% | 55% | ✓ |
| Hold time (median) | ≥ 3 min | 49 min | ✓ |
| MAE (median, % of entry) | < 50% | 17.5% | ✓ |

### Cumulative Strategy 3 sample

Including HOU-LAL (4/18), total Kalshi-analyzed games:
**5**. Competitive games with ≥1 mid-range round-trip at
(0.40, 0.50): **2/5** (HOU-LAL, ORL@DET). Progress toward
10-game graduation threshold: **5/10**.

Early economics are encouraging — median maker-maker net
materially above the $5 kill threshold on both the n=1
HOU-LAL reference and the n=4 pooled sample. Blowout rate
(3/4 on 4/19) is the dominant headwind: Strategy 3 only
fires when the underdog side spends meaningful time below
$0.50, which requires in-game competitiveness the
pre-game market doesn't always deliver. Sample is still
too small to estimate the competitive-game rate; watch as
playoff R1 continues.

### Does not supersede

All prior entries stand. This extends the HOU-LAL
single-game analysis to a multi-game sample. HOU-LAL's
economics (median net $14.55 at (0.35, 0.50)) remain the
headline reference for deep-dive characterization; this
entry establishes the pooled-game methodology and first
cross-game scorecard.

## 2026-04-19 — Timeout execution window analysis (n=2, HOU-LAL + ORL@DET)

**Data:** ESPN PBP timeout events joined to Kalshi
`/markets/trades` tape and logger orderbook snapshots on
wall-clock timestamps. 20 timeouts across two games
(HOU-LAL: 11, ORL@DET: 9). 187,987 trades, 1,208 in-game
snapshots. 100 bootstrapped baseline windows per game
(live-play, non-overlapping with any timeout). Report:
`docs/analysis_outputs/timeout_execution_analysis.md`.

### What we measured

For each 90s window (timeout = [T, T+90s]; baseline =
randomly sampled live-play): trade count, contracts, mean
trade size, mean bid-ask spread from snapshots, yes-price
range / std / drift, mean bid and ask depth (`*_size_fp`).
Pooled across games.

### Pooled headline numbers

| Metric | Timeout | Baseline | Ratio |
|---|---:|---:|---:|
| Trades per window | 825 | 690 | 1.20× |
| Contracts per window | 339k | 224k | 1.51× |
| Mean spread ($) | 0.0101 | 0.0107 | 0.94× |
| Mid drift ($) | 0.21 | 0.15 | 1.35× |
| Mean bid depth (fp) | 290k | 126k | 2.30× |
| Mean ask depth (fp) | 453k | 248k | 1.83× |

Pooled: volume concentrates in timeout windows, spread
tightens marginally, depth dramatically deepens
(2.3× bid, 1.83× ask), but mid-drift is **higher** than
baseline (1.35×). Three of four thesis-relevant dimensions
point toward calmer execution; drift points the other way.

### After-run split: the real signal

"After-run" = one team outscored the other by ≥ 6 points
in the 120s before the timeout. Only **2 of 20 timeouts**
qualified (both HOU-LAL). These show a categorically
different profile:

| Metric | After-run (n=2) | Baseline | Ratio |
|---|---:|---:|---:|
| Contracts per window | 818k | 224k | **3.64×** |
| Mean spread ($) | 0.0100 | 0.0107 | 0.93× |
| Price range ($) | 0.33 | 0.40 | 0.83× |
| Mid drift ($) | 0.010 | 0.153 | **0.07×** |
| Mean bid depth (fp) | 318k | 126k | 2.52× |

The book dramatically settles in the 90s after a stop-the-
run timeout: mid-drift collapses to 7% of baseline while
volume triples and depth doubles. This is the pattern the
original thesis predicted — the pooled view diluted it by
including routine end-of-quarter / mandatory TV-break
timeouts that don't stop anything.

### Thesis status

**Partially supported, pending more games.** The after-run
cut is the correct operational signal, but n=2 after-run
timeouts is well below the bar for making a rule out of
it. The pooled 20-timeout result shows the expected
direction on volume/spread/depth but not on drift — drift
is contaminated by mid-run timeouts where the move is
still resolving into price.

Identifying which timeouts are "after-run" requires live
ESPN PBP access at the time of decision. The existing PBP
scraper is post-game — Phase 4 would need an online-PBP
adapter (same endpoint, higher cadence) to make this rule
actionable. Not a blocker for the research; is a dependency
for operationalization.

### Implications for Strategy 3 entry rule

- **Do not use generic "post-timeout" as an entry trigger.**
  The pooled signal is too diluted by routine timeouts.
- **Consider "after-scoring-run" as the real signal** —
  define run as ≥6-point differential in a 2-min window,
  then enter maker orders in the 60-90s after the ensuing
  timeout. Needs 8-10 more games of after-run observations
  to size effect with any precision.
- **Depth 2.3× baseline** means the queue-position cost
  rises during timeouts. At maker pricing, that's the right
  tradeoff — slower fill for better price discipline.
- **Spread tightening (0.94×) is small** and likely lost
  in noise; not load-bearing for the entry rule.

### Does not supersede

All prior entries stand. This is the first timeout-window
characterization. Status: under review — headline pooled
numbers weak, after-run cut strong but n=2.

## 2026-04-19 — Scoring-run trajectory analysis (n=2 games, 5 run-stopping timeouts)

**Data:** ESPN PBP + Kalshi trade tape joined on wallclock for
HOU-LAL (4/18) and ORL@DET (4/19). 227 scoring plays with
trade-tape coverage; 20 timeouts; 5 classified as run-stopping
(≥4-point margin in ≥120s lookback). Report:
`docs/analysis_outputs/scoring_run_trajectories.md`.

### Part A — Score-to-price impact

Per-basket impact on the scoring team's YES contract (pooled):

| Play type | n | Immediate (+10s) | Full (+60s) | Reaction lag |
|---|---:|---:|---:|---:|
| 2-pointer | 108 | +$0.0167 | +$0.0235 | 4.1 s |
| 3-pointer | 41 | +$0.0400 | +$0.0349 | 3.5 s |
| Free throw | 77 | +$0.0062 | +$0.0053 | 19.9 s |

**Execution budget is ~3-4 seconds** between a basket landing
and the market absorbing half its impact on 2s/3s. Free throws
lag ~20s — the market waits to see the full sequence. A 3-pointer
moves the scoring team's price ~4× more than a free throw.

### Part B — Post-timeout trajectory (run-stopping, n=5)

Trailing team's YES-price change after play resumes from a
run-stopping timeout:

| Metric | Mean | Median | % positive |
|---|---:|---:|---:|
| Recovery @ 1 min | +$0.020 | $0.000 | 40% |
| Recovery @ 3 min | +$0.036 | −$0.010 | 40% |
| Recovery @ 5 min | +$0.030 | −$0.010 | 40% |
| **Max recovery** | **+$0.090** | **+$0.090** | **80%** |
| Time to max (s) | — | 186 | — |

The fixed-checkpoint signal is too noisy at n=5 to anchor an
entry rule. The **max-recovery signal is directionally clean**
(80% of timeouts saw *some* price bounce within 5 min, mean
magnitude +$0.090), but the magnitude and timing vary enough
that a simple "hold 3 min then exit" rule captures less than
half the bounce on average.

### Part C — Run-detection parameter sweep

| (margin, lookback) | Run-stopping n | Mean rec @ 3 min | % positive |
|---|---:|---:|---:|
| (4, 120s) | 4 | +$0.048 | 50% |
| (4, 180s) | 4 | +$0.055 | 50% |
| (6, 120s) | 2 | $0.000 | 50% |
| (6, 180s) | 3 | −$0.003 | 33% |
| (8, 240s) | 3 | −$0.003 | 33% |

Best set — `(4, 120s)` and `(4, 180s)` — peaks at 50% positive
@ 3 min, below the 55% threshold for a rule. Tighter run
definitions (≥6 or ≥8 points) do not improve the hit rate at
this sample size.

### Thesis status

**Null result at n=5 run-stopping timeouts.** The momentum-
reversal thesis is not supported by the post-timeout recovery
signal at 3-minute fixed checkpoints. Two pieces complicate
drawing a strong conclusion:

1. **Max-recovery is 80% positive at +$0.090 mean** — the
   price does bounce, just with variable timing. A time-
   adaptive exit (sell at peak within 5 min rather than at
   a fixed 3-min checkpoint) would capture most of this.
   The current data doesn't support calibrating that exit
   rule either.
2. **n=5 is structurally thin.** 4 of the 5 came from a
   single game (ORL@DET). Need more run-stopping timeouts
   before the signal can be distinguished from noise.

### Connection to Strategy 3

Feeds the graduation thesis at the mechanism level. Strategy 3
at (0.40, 0.50) entry has already shown +$21.70 mean net /
trade on n=7 pooled round-trips — that is the operational
evidence. This analysis tested whether the *entry moment* can
be sharpened by using timeout-after-run as a trigger. At n=5
the answer is "not yet" — continue using price-level triggers
and collect more timeout-trajectory observations in parallel.

### Implications for entry rule refinement

- **Per-basket price impact is real and measurable.** A 3-pointer
  dropping the trailing team by +$0.04 on their opponent's YES
  (equivalently, −$0.04 on trailing team's YES) is exactly the
  dip Strategy 3 wants to buy. This is the ex-ante mechanism
  that has to be true for the strategy to work, and it is.
- **Timeout-as-trigger is not yet usable.** 50% hit rate on
  directional recovery means the strategy should not lean on
  "we saw a timeout, therefore buy." The current (0.40, 0.50)
  price-level rule is mechanism-agnostic and captures swings
  regardless of their proximate cause.
- **Budget for execution ~3-4 seconds** after a scoring play
  before the market absorbs half the impact. Manual execution
  is marginal; an automated signal engine needs to act
  inside this window.

### Does not supersede

All prior entries stand. Adds mechanism-level characterization
and a null result on the timeout-as-trigger variant. Strategy 3
graduation progress unchanged at 2/10 competitive Kalshi games.

## 2026-04-19 — ESPN-scale scoring-run pattern catalog (N=549 competitive games)

**Data:** Full 2025-26 regular season ESPN PBP + WP. Filter:
|spread| ≤ 6 (549 / 1,243 games). Report:
`docs/analysis_outputs/espn_scoring_run_catalog.md`. Complements
the n=2 Kalshi-level `scoring_run_trajectories.py` at 600×
scale using ESPN WP as the yardstick.

**ESPN CAVEAT (important).** ESPN WP is +10-17pp more reactive
than real-money markets at the tails per Phase 3B sportsbook
backfill. Absolute magnitudes here are upper bounds on what
Kalshi would show. Relative patterns transfer; absolute
recovery sizes will compress on market prices.

### What we measured

Scoring runs (5-parameter sweep), timeout association within
90s of game time, post-run WP trajectories at
+1/+2/+3/+5-min checkpoints + max recovery in 5 min, prior
degradation (underdog lead persistence at Q1/half/Q3/6:00 Q4),
and favorite vs underdog dip recovery across five thresholds.

### Headline numbers (primary params: margin ≥ 6, window ≤ 3 min)

**Run frequency:** 6,210 runs / 549 games = **11.3 runs per
competitive game**. 100% of games have ≥1 run at this threshold.

**Timeout association:** Only **36% of runs** are followed by
a timeout within 90s of game time (66% of those are called by
the trailing team). Most runs don't trigger a timeout — they're
either absorbed into the flow of play or end a quarter. **The
"timeout reliably follows a run" premise is weaker than the
thesis assumed.**

**Trailing-team recovery:**

| Checkpoint | Mean WP delta | Median | % positive | n |
|---|---:|---:|---:|---:|
| +1 min | +0.017 | +0.005 | 55% | 6,085 |
| +3 min | **+0.023** | +0.004 | **52%** | 5,818 |
| +5 min | +0.025 | +0.003 | 52% | 5,563 |
| Max (in 5 min) | **+0.120** | **+0.084** | **89%** | 6,210 |

**Fixed 3-min checkpoints are noisy (52% positive).** But the
*max* recovery within 5 min is **89% positive** at mean +0.12
WP — i.e., the book essentially always bounces, just with
variable timing (median 138s to peak).

### Favorite vs underdog trailing (prior-anchoring test)

| Group | n | % positive @ 3min | Mean max rec |
|---|---:|---:|---:|
| Favorite trailing | 2,947 | 54% | +0.125 |
| Underdog trailing | 3,263 | 50% | +0.116 |

Gap at fixed checkpoints is thin (4pp). **But the asymmetry
shows cleanly in dip recovery:**

**Favorite dip → recovery above 0.50**

| Threshold | % recover | Median time | Game-win % |
|---|---:|---:|---:|
| < 0.45 | 91% | 1.9 min | 50% |
| < 0.40 | 84% | 3.5 min | 47% |
| < 0.35 | 76% | 6.0 min | 41% |
| < 0.30 | 68% | 7.9 min | 38% |
| < 0.25 | 60% | 9.0 min | 34% |

**Underdog dip → recovery above 0.50**

| Threshold | % recover | Median time | Game-win % |
|---|---:|---:|---:|
| < 0.45 | 84% | 4.7 min | 39% |
| < 0.40 | 79% | 5.9 min | 37% |
| < 0.35 | 73% | 7.6 min | 35% |
| < 0.30 | 64% | 9.3 min | 31% |
| < 0.25 | 54% | 11.2 min | 27% |

**Favorites recover faster and more often from every dip
threshold.** At <0.45 the gap is 7pp and the recovery time is
2.5× faster (1.9 min vs 4.7 min). This is the prior-anchoring
mechanism observable at season scale — the WP model anchors
near the pre-game prior, so a favorite's dip mean-reverts up
toward ~0.50+ faster than an underdog's dip does.

### Timeouts do not help recovery

| Context | % positive @ 3min | Mean max rec |
|---|---:|---:|
| Run + timeout | 51% | +0.120 |
| Run, no timeout | 53% | +0.120 |

Timeouts are correlated with runs (36% of runs, 66% by the
trailing team when present) but they don't measurably improve
the trailing team's post-run recovery. Runs reverse at similar
rates regardless.

### Prior-acceptance inflection point

Underdog leading at checkpoint → underdog wins the game:

| Checkpoint | n leading | Win rate |
|---|---:|---:|
| End Q1 | — | 54% |
| Halftime | — | 63% |
| End Q3 | — | 73% |
| 6:00 Q4 | — | 79% |

At Q1 end, an underdog leading has only a 54% chance of
winning — the prior is still weighing heavily. By 6:00 Q4, the
prior has dissolved (79% conversion). This is the window where
the market lags game state the most — the first half.

### Strongest-signal run contexts

- **Best run magnitude:** 6-7 points (53% positive @ 3min) —
  marginal edge over larger runs
- **Best period:** Q1 (59% positive @ 3min)
- Larger runs (10+) and later quarters do *not* improve
  recovery rates; if anything they signal the deficit is real

### Thesis status

**Partially supported.** The prior-anchoring asymmetry
(favorites recover faster/more often than underdogs from any
given dip) is the cleanest signal in the catalog — a ~5pp edge
at each threshold, with 2-3× faster recovery times. This
supports Strategy 3 prioritizing games where the pre-game
favorite falls behind.

**Partially denied.** The "timeout-stops-the-run" mechanism is
weak at ESPN scale: only 36% of runs trigger a timeout, and
timeouts don't improve recovery rates. The entry rule should
not key off of timeouts.

**Fixed-checkpoint recovery at 52-54%** is thin for an entry
rule. The **max-recovery-in-5-min at 89% positive** is the
cleaner directional signal — but that's an outcome, not an
actionable exit rule (can't know peak in advance). A smart
exit rule would need to trail the price upward; a fixed
3-min hold captures only half the bounce.

### ESPN caveat re-stated

All recovery magnitudes above are ESPN WP. Kalshi recovery
will be **10-17pp smaller in absolute terms** at the tails.
The 91% favorite-dip-recovery at <0.45 ESPN WP may be 60-70%
at Kalshi <0.45. The relative favorite-vs-underdog asymmetry
should transfer; the absolute rates won't.

### Strategy 3 implications

- **Prioritize games where the pre-game favorite falls behind.**
  That's where the ESPN-scale prior-anchoring signal is
  strongest, and the mechanism transfers to market prices
  with smaller magnitude.
- **Do not use timeouts as an entry trigger.** Only 36% of
  runs trigger timeouts; recovery rates are identical with
  and without.
- **Entry rule should continue to be price-level** (the
  (0.40, 0.50) maker-maker rule), not event-triggered
  (scoring-run-plus-timeout).
- **Exit rule needs to be adaptive**, not fixed. Max recovery
  in 5 min is 89% positive — but at variable timing
  (median 138s to peak, long tail). A trailing-stop exit
  would capture more of the bounce than a fixed 3-min hold.
  Designing that exit rule is a future item.

### Cumulative sample posture

Kalshi-level sample unchanged: 2/10 competitive games toward
graduation. ESPN-scale catalog validates the mechanism at
season scale and prioritizes *which* game contexts are most
productive to collect Kalshi data on (favorite-trailing,
|spread| ≤ 6, mid-game).

### Does not supersede

All prior entries stand. Extends the scoring-run analysis
chain: (1) Kalshi trade-to-price (n=2, mechanism confirmed),
(2) ESPN game-flow trajectories (N=1,234, which shapes
oscillate), (3) this entry (N=549 competitive, which runs
produce recovery). Each layer informs a different piece of
the entry-rule design.

## 2026-04-20 — Timeout execution window analysis (HOU-LAL + ORL@DET)

**Script:** `analysis/timeout_execution_analysis.py`
**Report:** `docs/analysis_outputs/timeout_execution_analysis.md`

Paired Kalshi trade tape timestamps with ESPN PBP timeout events
to measure whether NBA timeouts create favorable execution
windows. 20 timeouts across 2 games (HOU-LAL 11, ORL@DET 9),
compared to 100 bootstrapped 90-second baseline windows per game.

### Key findings

**Depth is the headline:** Bid depth 2.30× baseline, ask depth
1.83× baseline during timeout windows. Market participants pile
resting orders onto the book during stoppages. Spread at $0.01
floor in 19 of 20 timeouts (vs occasional widening during live
play).

**Volume concentrates:** 1.20× trade count, 1.51× contract
volume. Larger mean trade size (1.18×). Consistent with
institutional/informed flow entering during known price windows.

**Price stability is mixed:** Range 1.14×, std 1.25×, drift
1.35× — all "worse" than baseline. But this is selection bias:
timeouts are called during volatile moments, and the 90-second
window starting at the whistle includes the tail of the price
move that triggered the timeout.

**After-run timeouts (n=2) show the settlement pattern:**
Mid drift drops to 0.07× baseline (effectively zero) in the
two timeouts following ≥6-point runs. Price moved before the
timeout, then stopped. The run-detection threshold (≥6 in 120s)
was too tight — only 2 of 20 timeouts qualified.

### Verdict

Timeout windows are confirmed as favorable execution
environments (depth, spread). They are NOT directional signals
(tested separately in the scoring-run trajectory analysis).
The entry rule should treat timeouts as execution opportunities,
not triggers.

## 2026-04-20 — Scoring-run trajectory analysis (HOU-LAL + ORL@DET, Kalshi)

**Script:** `analysis/scoring_run_trajectories.py`
**Report:** `docs/analysis_outputs/scoring_run_trajectories.md`

Kalshi-level score-to-price impact mapping and post-timeout
price trajectory measurement on 2 games with full data
alignment (ESPN PBP wallclock → Kalshi trade tape timestamps).

### Part A: Score-to-price impact

Per-basket price impact on Kalshi (pooled, n=226 scoring plays):
- 3-pointer: +$0.040 immediate (10s), median lag 3.5s
- 2-pointer: +$0.017 immediate, median lag 4.1s
- Free throw: +$0.006, median lag 19.9s (low information)

Impact peaks in $0.40-$0.50 zone at $0.024/play — Strategy 3's
operating zone is where individual baskets matter most to the
market. Impact tapers at extremes (≤$0.30: $0.015, >$0.70:
$0.013).

Execution budget for reactive entries: 3-4 seconds between
basket and full market reaction. Tight but nonzero. Maker
orders (resting before the event) bypass this constraint.

### Part B: Post-timeout trajectory (n=5 run-stopping timeouts)

Null result at fixed checkpoints: 40-50% positive recovery at
3 min, below the 55% threshold for a directional rule. n=5 is
too thin to confirm or retire. Max recovery was positive in 4
of 5 (80%), suggesting bounces happen but on unpredictable
timing. ORL@DET Q3 9:35 showed +$0.23 recovery (DET favorite
dipping to $0.48). HOU@LAL Q4 7:57 showed no recovery (HOU at
$0.05 — too far gone, outside the operating zone).

### Part C: Run detection sweep

(4, 120s) and (4, 180s) produced the best recovery signal at
50% positive (n=4). Tighter thresholds reduced sample too
aggressively. Deferred to ESPN-scale analysis for statistical
power.

### Does not supersede

All prior entries stand. This establishes the per-basket price
conversion factor and the post-timeout trajectory framework.
The ESPN-scale catalog (next entry) provides the sample size
this analysis lacked.

## 2026-04-20 — ESPN-scale scoring-run pattern catalog (N=1,234 games)

**Script:** `analysis/espn_scoring_run_catalog.py`
**Report:** `docs/analysis_outputs/espn_scoring_run_catalog.md`

Full-season (549 competitive games, |spread| ≤ 6) analysis of
scoring runs, timeout association, post-run WP trajectories,
prior degradation, and favorite/underdog recovery asymmetry.

**ESPN caveat:** All magnitudes are ESPN WP, which is +10-17pp
more reactive than Kalshi at the tails. Directional patterns
should transfer; absolute magnitudes will be smaller on Kalshi.

### Run frequency

At (6-point margin, 3-min window): 6,210 runs across 549 games
(11.3 runs/game). 100% of competitive games produce ≥1 run.
Scoring runs are ubiquitous — they are the normal rhythm of NBA
basketball, not rare events.

### Timeout association

36% of runs followed by a timeout within 90 seconds of game
time. Of those, 66% called by the trailing team. Timeout
association is frequent but not reliable as a signal.

### Post-run recovery: the base rate

At 3-min fixed checkpoint: 52% positive recovery (barely above
coin flip). But max recovery within 5 minutes is positive 89%
of the time, mean +0.12 WP. Median time to max recovery: 138s.

**Interpretation:** Runs almost always produce some bounce-back,
but the timing is unpredictable. This supports Strategy 3's
price-threshold-based entry/exit over any time-based rule.

### Favorite vs underdog asymmetry: confirmed, modest

Post-run recovery at 3 min: favorites 54% positive vs
underdogs 50%. Recovery from dips below 0.35 WP: favorites
76% vs underdogs 73%. Favorites recover ~1.5 min faster at
every threshold. The asymmetry is real but thin (3-6pp range).

### Timeouts do NOT help recovery: confirmed

Runs followed by timeout: 51% positive at 3 min.
Runs without timeout: 53% positive.
Delta: −2pp. At n=6,210 this is definitive. Timeouts are
execution windows, not recovery signals. This finding
settled the timeout-as-signal hypothesis.

### Period effects

Q1 runs reverse at 59% (best). Q4 at 44% (worst). The
pre-game prior is strongest early; by Q4 the game state
dominates. Strategy 3 entries are more reliable in Q1/Q2.

### Run magnitude sweet spot

6-7 point runs: 53% positive. 13+ point runs: 43%.
Moderate runs are the best entry context. Large runs more
often represent genuine separation.

### Prior degradation roadmap

Underdog leads at checkpoints → eventual win rate:
End Q1: 54%, Halftime: 63%, End Q3: 73%, 6:00 Q4: 79%.
The prior takes a full half to dissolve. The Q1-halftime
window is where market dislocation from game reality
should be largest.

### Strategy 3 implications

The entry rule should remain price-based. Contextual
modifiers (favor the favorite, prefer early-game entries,
don't wait for massive runs) provide modest edge
improvements. Timeouts are execution windows only.
Full synthesis in `docs/STRATEGY3_SPEC.md`.

### Does not supersede

All prior entries stand. This provides the statistical
foundation that the n=2 Kalshi-level analyses lacked.
The two analysis layers complement: ESPN for patterns
at scale, Kalshi for market-price validation.

## 2026-04-20 — WP vs Kalshi paired analysis infrastructure

Landed `analysis/wp_vs_kalshi_paired.py`: repeatable per-game
study of ESPN WP vs Kalshi trade price relationship. Favorite-
centric. 30-second VWAP bins + event-driven scoring-play
alignment. Tests convergence hypothesis (|delta| → 0 near
resolution), compression pattern by WP zone, and Strategy 3
zone mapping. Timeout windows flagged for execution quality
analysis. First target: POR@SAS Game 1 (401869194 /
KXNBAGAME-26APR19PORSAS). No findings yet — script implemented
but not yet run.

## 2026-04-20 — WP vs Kalshi paired analysis: four-game findings

**Script:** `analysis/wp_vs_kalshi_paired.py` (landed this session).
**Games analyzed:**

| Game | Date | |Spread| | Outcome | Kalshi trades | Type |
|------|------|---------|---------|---------------|------|
| POR@SAS | 4/19 | 10.5 | Chalk (SAS 111-98) | 50,838 | Blowout |
| ORL@DET | 4/19 | 8.5 | Upset (ORL 112-101) | 94,149 | One-directional upset |
| HOU@LAL | 4/18 | 2.5 | Upset (LAL 107-98) | 93,838 | Competitive |
| MIA@CHA | 4/14 | 5.5 | Chalk (CHA 127-126 OT) | 126,407 | OT thriller |

### Finding 1: Kalshi is always the more moderate voice

Kalshi compresses toward $0.50 relative to ESPN WP regardless
of direction. When ESPN is bullish on the favorite, Kalshi is
less bullish. When ESPN gets bearish, Kalshi is less bearish.

Delta by WP zone (favorite-centric, pooled across 4 games):

| WP zone | Mean Δ (Kalshi − ESPN) | N obs | Δ > 0 % |
|---------|----------------------|-------|---------|
| 0.00-0.20 | +2.7pp | 189 | 84% |
| 0.20-0.40 | +9.3pp | 206 | 98% |
| 0.40-0.60 | +6.3pp | 238 | 95% |
| 0.60-0.80 | +0.6pp | 237 | 57% |
| 0.80-1.00 | +0.4pp | 352 | 46% |

Pattern: delta peaks in the 0.20-0.40 zone (Kalshi +9pp above
ESPN) and shrinks toward zero at the extremes. This is the
compression pattern from Phase 3A confirmed on paired intra-game
data for the first time.

### Finding 2: Convergence depends on game type

| Game | R² (|Δ| ~ time) | Slope | Final 2 min |Δ| |
|------|-----------------|-------|-------------|
| HOU@LAL (competitive) | **0.463** | −0.000029 | 0.83pp |
| POR@SAS (blowout) | 0.077 | −0.000005 | 0.90pp |
| ORL@DET (upset) | 0.000 | +0.000001 | 0.45pp |
| MIA@CHA (OT thriller) | 0.086 | **+0.000016** | **9.04pp** |

Convergence is strongest in competitive games (R² = 0.463 for
HOU@LAL). Blowouts converge weakly. Upsets don't converge
linearly (delta explodes mid-game then snaps back). OT
thrillers actively diverge — ESPN WP swings faster than Kalshi
can reprice, producing growing delta in the final minutes.

Working hypothesis: "ESPN WP is a true anchor that Kalshi tends
toward as resolution approaches" holds for games that resolve
before the final minute. In games decided on the final
possession (MIA@CHA), Kalshi's market structure imposes a
speed limit that prevents convergence.

### Finding 3: ESPN WP reacts more per basket than Kalshi

Per-scoring-play reaction comparison (favorite-centric):

| WP zone | ESPN reaction | Kalshi reaction | ESPN/Kalshi ratio |
|---------|-------------|----------------|------------------|
| 0.00-0.20 | +9.25pp | +0.50pp | 18.5× |
| 0.20-0.40 | +2.5pp | −0.2pp | divergent |
| 0.40-0.60 | −0.9pp | −0.5pp | 1.8× |
| 0.60-0.80 | −0.3pp | −0.3pp | 1.0× |
| 0.80-1.00 | −0.5pp | −0.4pp | 1.3× |

ESPN reacts most extremely at WP tails. At extreme WP
(0.00-0.20), ESPN moves 18× more per basket than Kalshi.
In the Strategy 3 operating zone (0.40-0.60 from the
underdog's perspective), ESPN moves ~1.8× more.

Implication: price-based entry on Kalshi is correct over
model-based entry on ESPN WP. ESPN would generate too many
false signals from per-basket overreaction.

### Finding 4: Zone entry lead varies by game context

| Game | Pre-game Δ | Who entered S3 zone first | Lead |
|------|-----------|--------------------------|------|
| ORL@DET | −0.4pp | ESPN | 240s |
| HOU@LAL | +7.3pp | Simultaneous | 0s |
| MIA@CHA | −3.6pp | Kalshi | 2,250s |

ESPN leads into the zone when a strong prior is being violated
(upset from outside). Kalshi leads when it starts skeptical of
the favorite. For pick'em games, both enter simultaneously.

Practical implication: monitor both feeds; enter on whichever
crosses the threshold first. Do not hard-code which one leads.

### Finding 5: Timeouts remain delta-neutral (with a crunch-time caveat)

Across 3 of 4 games, mean delta at timeouts ≈ overall mean
delta. Timeouts are not convergence or divergence events.

Exception: MIA@CHA crunch-time timeouts (Q4 final 30 seconds)
showed delta swinging ±14pp between consecutive timeouts. In
games decided on the final possession, timeout windows are
moments of maximum delta instability. The execution-quality
finding (better depth/spread) may still hold, but the *price
level* during crunch-time timeouts is unreliable as fair value.

### Finding 6: Strategy 3 zone time correlates with competitiveness

| Game | |Spread| | S3 zone time | % of game |
|------|---------|-------------|-----------|
| HOU@LAL | 2.5 | 5,070s | 54.7% |
| MIA@CHA | 5.5 | 3,180s | 32.3% |
| ORL@DET | 8.5 | 4,560s | 4.5% |
| POR@SAS | 10.5 | 0s | 0% |

Lower |spread| → more zone time, as expected. The |spread| ≤ 6
filter correctly excludes POR@SAS (0% zone time) and correctly
includes HOU@LAL (55%) and MIA@CHA (32%). ORL@DET at |spread|
= 8.5 produced some zone time (4.5%) only because of the upset.

### Known script issues (non-blocking)

- §5 lead-time calculation should anchor to tip-off, not first
  trade timestamp. Caused a bad value (430,530s) on the initial
  HOU@LAL run; fixed by re-run, but the root cause is in the
  script. One-liner patch needed.
- §7 auto-text sometimes shows stale values from earlier runs
  (cosmetic; the tables are correct).

## 2026-04-21 — Strategy 3 graduation evaluation

Formal graduation evaluation on 168-game paired dataset (165
competitive, |spread| ≤ 6). Round-trip detection at 5 grids
on Kalshi trade-price timeseries. See
`docs/analysis_outputs/strategy3_graduation_eval.md` for full
results and graduation verdict.

STRATEGY3_SPEC.md updated to reflect 168-game calibration:
- §1A compression table: Kalshi = ESPN + delta, where delta =
  +8.30pp at 0.20-0.40 WP, −2.73pp at 0.80-1.00 WP.
- §3 convergence-zone exit preference: 1–3 min remaining is
  optimal exit window (|Δ| = 2.47pp, rising to 3.97pp at <1 min).
- §4 timeout evidence upgraded from ESPN-scale to Kalshi-confirmed
  (p = 8.5e-08 on n=7,175 timeout windows).
- §6 zone statistics: 95% of competitive games enter S3 zone,
  mean 2,991s zone time per game.

## 2026-04-21 — Strategy 3 failed entry & worst-case analysis

Complement to the graduation evaluation. Analyzed every entry
event at ≤$0.40 across 165 competitive games — not just completed
round-trips but also positions held to resolution (wins and
losses). Produces the true expected value per entry, fail rate
by quarter and spread, max adverse excursion distribution, and
worst-case scenarios. See
`docs/analysis_outputs/strategy3_failed_entries.md`.

**Critical result: the true EV per entry is −$4.57.** The
graduation verdict (100% of completed round-trips profitable,
median net $13.74) was computed on the subset of entries that
reached the exit threshold. Counting all entries: 60.9% complete
(mean +$15.49), 39.1% are held to a loss (mean −$35.82). The
losing-entry magnitude is 2.3× the winning-entry magnitude,
producing a negative blended EV.

Fail rate rises with both game period (Q1 34.3% → Q4 44.2% →
OT 46.2%) and spread magnitude (|spread| 1.0-2.0: 37.8% →
|spread| 5.5-6.0: 47.2%). 7.9% of losing entries were near-
misses (MFE ≥ exit − $0.02); most (92%) were clean losses where
the team got blown out. Strategy 3 in the naive (0.40, 0.50)
grid without stop-loss or selective entry is not profitable.

**Phase 4a gating should not trigger on the graduation verdict
alone.** The graduation scorecard measured completed-round-trip
economics, not entry-level EV. Next research: stop-loss
calibration, selective entry filters (Q1/Q2 + tighter spread),
and grid comparisons on the same full-entry basis.

## 2026-04-21 — Stop-loss parameter sweep & position management simulation

Replayed all entries from the failed-entry analysis at 20
stop-loss levels ($0.20-$0.39) plus no-stop baseline. Identified
optimal stop-loss, breakeven point, and false-stop rate. Also
tested averaging-in (add at $0.35 or $0.30) and partial exits
(sell half at $0.48, hold half for $0.55). Combined best
configuration reported with annual EV projection. Context
breakdowns by entry period and spread bucket. See
`docs/analysis_outputs/strategy3_stoploss_sweep.md`.

**Critical result: no stop-loss level, averaging-in variant, or
partial-exit configuration produced positive EV.** Naive baseline
annual EV is −$5,963. Optimal stop-loss ($0.34) improves to
−$2,531. Best combined config (stop $0.34 + avg-in $0.35)
reaches −$1,175 — an 80% loss reduction but still net negative.

False-stop rate at the optimum is 50.8%: half of stopped-out
positions would have recovered to complete a round-trip if held.
Tighter stops (lower level) have fewer false stops but catch
fewer winners that dipped deep. The entry signal at ≤$0.40 is
too weak to support a purely-risk-management solution.

**Phase 4a remains blocked.** Next research direction: selective
entry filters (period, spread magnitude, favorite-side,
ESPN-WP divergence) rather than further risk-management
variations. A team's YES price dropping to $0.40 in a competitive
game is not by itself an edge — the market correctly prices
~40% of those dips as heading to blowout.

## 2026-04-21 — Upside capture & trailing stop analysis

Extended the stop-loss sweep with resolution upside capture.
Tested scale-out ratios (sell 25-100% at first exit), trailing
stop distances ($0.03-$0.20), and held-to-resolution variants.
Full 96-configuration grid search across stop-loss × scale-out
× trailing stop parameters. Identifies best overall strategy
configuration and compares to naive, stop-only, and bilateral
baselines. See
`docs/analysis_outputs/strategy3_upside_capture.md`.

**Critical result: no configuration produced positive EV.**
Best found (stop $0.34 + sell 25% at $0.50 + hold 75% to
resolution, no trailing stop): mean P&L −$0.59 per entry,
annual EV −$852. Max single win $+49.16 (held to resolution),
max single loss $-25.34. Win rate 16.6%; winners are 1.94×
larger than losers but base rate is too low to flip positive.

Strategy shape after upside capture: 75% stop-outs at small
losses, 14% hold-to-resolution wins at +$49, 11% hold-to-
resolution losses at −$25. Lottery-like distribution but
still negative-sum.

**Five consecutive dead ends for naive entry:** completed-RT
subset is misleading; stop-loss alone doesn't fix it; avg-in
helps marginally; partial exits don't help; upside capture
barely helps. The entry signal at ≤$0.40 mispricing in 40%
of cases cannot be salvaged by exit-side mechanics. Selective
entry filters (period, spread, side, WP divergence) are the
next research direction. Bilateral backstop remains at
+$1,608 annual EV guaranteed.

## 2026-04-21 — Entry filter sweep: first positive-EV configurations found

Tested four entry filters on the Strategy 3 replay engine across
165 competitive games. Oscillation confirmation (was price recently
higher?), ESPN WP rate-of-change (fast drop = scoring run), favorite-
side restriction, and period filtering. Individual sweeps, combined
grid search (32 configurations), and full strategy evolution table
from naive through all optimizations. See
`docs/analysis_outputs/strategy3_entry_filters.md`.

**BREAKTHROUGH — 8 of 32 combined configurations produced positive
EV.** The first positive-EV result in the Strategy 3 research chain
after six consecutive negative findings.

### Top 3 configurations by mean P&L

| Config | Entries | Mean P&L | Annual EV | Win rate | Sharpe |
|---|---:|---:|---:|---:|---:|
| WP + Fav + Period + upside exit | 51 | **+$3.41** | **+$578** | 21.6% | 0.14 |
| Osc + WP + upside | 57 | +$1.76 | +$334 | — | — |
| WP + Period + upside | 152 | +$1.43 | +$725 | — | — |

### Best by annual EV (more entries, slightly lower per-entry)

WP + Period + upside: **+$725 annual EV at 152 entries** (vs 51 for
best mean). Trade-off between per-entry quality and opportunity
volume.

### Individual filter findings

- **Oscillation at 2min / $0.55 (standalone, simple exit): +$0.90
  mean, +$221 annual.** Simplest positive-EV config. Requires price
  to have been ≥ $0.55 within the last 2 minutes before the dip —
  i.e., the dip must be a fast scoring-run signature, not a slow
  grind.
- **ESPN WP momentum (2min / 3pp drop): −$1.00 mean.** Marginally
  helps but alone not enough.
- **Favorite-side only: −$1.99 mean (WORSE than baseline).**
  Surprising counterresult to the ESPN-scale asymmetry finding.
  On Kalshi at these price thresholds, underdog-side dips actually
  fare better (−$0.88 vs baseline −$1.27). The compression pattern
  puts Kalshi above ESPN in the underdog-dip zone, so dips there
  are less predictive of continued decline.
- **Period: Q1/Q2 only: −$0.96 mean.** Marginal individual effect
  but combines well with other filters.

### Strategy evolution table

| Strategy | Mean P&L | Annual EV | Verdict |
|---|---:|---:|---|
| 1. Naive (no stop, no filter) | −$4.22 | −$5,963 | negative |
| 2. + Stop-loss @$0.34 | −$1.27 | −$2,531 | negative |
| 3. + Upside capture (25/75) | −$0.59 | −$852 | negative |
| 4. + Entry filters (best mean) | **+$3.41** | **+$578** | **POSITIVE** |
| 4'. + Entry filters (best EV) | +$1.43 | +$725 | **POSITIVE** |
| 5. Bilateral only (baseline) | +$19.14 | +$1,608 | positive |
| 6. Best Strategy 3 + bilateral | — | **+$2,186** | **POSITIVE** |

### Filter precision/recall

Best config filters out **94% of candidates** (799/850 rejected,
51 passed). Of rejected entries, 35.5% would have failed anyway
(correctly rejected) and 64.5% would have reached $0.50
(false rejections). Filter recall is 2.1% — extremely selective.
This is the correct tradeoff: the filter maximizes EV per entry
by accepting only the highest-confidence dips, at the cost of
missing many marginal winners. The loosened WP+Period config
has higher annual EV (+$725) because it keeps more of the
borderline cases.

### Implication for Phase 4a

**Phase 4a can unlock on a selective-entry version of Strategy 3.**
The rule set:
- Entry: team's Kalshi bid ≤ $0.40 in a competitive game
  (|spread| ≤ 6)
- **Filter: ESPN WP for that team dropped ≥ 3pp in the last 2
  minutes** AND team is the pre-game favorite AND period is Q1 or Q2
- Position: 100 contracts
- Initial stop: $0.34
- At $0.50: sell 25 contracts
- Hold 75 contracts to resolution (no trailing stop)

Combined with bilateral Strategy 1 (+$1,608 annual), total projected
EV is **+$2,186/year** at 100-contract sizing — positive but modest.
Requires a live ESPN PBP/WP poller and live Kalshi bid-feed access
before Phase 4a can operate.

**Caveat:** the signal is data-limited (n=51 entries produced this
result). Confidence interval on mean is wide. Live paper-trading
in Phase 4a is the next validation step.

## 2026-04-22 — S4A spread expansion: all 7 buckets positive EV (404-game dataset)

Extended the S4A dip-recovery analysis from the 171-game core
dataset (|spread| ≤ 6) to the full 404-game Kalshi paired dataset
(all spreads). Part 8 Path B of the dip-recovery analysis. See
`docs/analysis_outputs/strategy4_spread_expansion_kalshi.md`.

| |Spread| | Games | Entries | Hit % | Mean P&L | Annual EV |
|----------|-------|---------|-------|----------|-----------|
| 1.0–2.0 | 36 | 29 | 51.7% | +$1.59 | +$702 |
| 2.5–3.5 | 69 | 71 | 47.9% | +$2.57 | +$1,446 |
| 4.0–5.0 | 31 | 29 | 48.3% | +$2.65 | +$1,357 |
| 5.5–6.0 | 35 | 37 | 64.9% | +$6.17 | +$3,570 |
| 6.5–8.0 | 46 | 43 | 58.1% | +$4.14 | +$2,116 |
| 8.5–10.0 | 38 | 36 | 58.3% | +$0.82 | +$425 |
| 10.5+ | 149 | 66 | 69.7% | +$4.55 | +$1,103 |

**All 7 buckets are positive EV.** Wider spreads produce higher
hit rates (69.7% at 10.5+ vs 47.9% at 2.5–3.5) but fewer
entries per game. The 5.5–6.0 bucket is the standout (+$6.17
mean P&L, 64.9% hit). Expansion buckets (|spread| > 6) have
36–66 entries each — directionally robust, exact dollar figures
noisy at these sample sizes.

Core (|spread| ≤ 6): +$7,075/yr. Expansion (|spread| > 6):
+$3,644/yr. **Uncapped total: +$10,718/yr** (bucket-level
extrapolation, not pooled replay). Engine already operates
without spread filter — no code change needed.

STRATEGY4_SPEC.md §2 updated: competitive game filter → uncapped.
§7 updated with all 7 buckets. §9 updated with expansion EV.

## 2026-04-22 — Bucket 5.5–6.0 investigation (inconclusive)

The 5.5–6.0 bucket's +$6.17 mean P&L (64.9% hit) was the
standout — nearly double the next-best per-entry mean.
Investigated whether this is structural or small-sample noise.
See `docs/analysis_outputs/strategy4_bucket_5_5_investigation.md`.

- Leave-one-out: mean ranges $5.32–$7.55 (never negative).
  No single game drives the result.
- Bootstrap 95% CI: −$2.90 to +$14.73.
- P(mean > 0): 91.1%.
- 28 distinct games contributing entries.

**Verdict: inconclusive.** Positive and stable, but confidence
interval includes zero. Cannot confirm structural sweet spot
vs favorable noise at n=37. No special treatment warranted.
Monitor as forward collection cron accumulates more data.

## 2026-04-22 — Stop execution reality (132 stop events, 404 games)

Analyzed what actually happens when S4A's $0.40 stop fires on
real Kalshi VWAP data. 132 stop events across 404 games. See
`docs/analysis_outputs/strategy4_stop_execution.md`.

| Category | Definition | % of stops |
|----------|-----------|-----------|
| Clean cross | VWAP $0.38–$0.42 | 50.0% |
| Moderate gap | VWAP $0.34–$0.38 | 32.6% |
| Severe gap | VWAP < $0.34 | 17.4% |

73.5% of stops are flash crashes (price above $0.45 just 60
seconds before the stop fires). Median dwell time at the
$0.38–$0.42 band is 0 bins — price typically blows through
$0.40 rather than lingering.

**Break-even stop price: $0.312.** Strategy stays positive
even under worst-case taker execution. Four execution
scenarios analyzed:

| Scenario | Annual EV | Δ vs baseline |
|----------|-----------|--------------|
| A — Baseline (stops at $0.40, maker) | +$1,410 | — |
| B — Maker NO-side resting + taker fallback | +$1,460 | +$49 |
| C — Taker stop at observed VWAP (worst case) | +$977 | −$433 |
| D — Hybrid (resting + 60s cancel fallback) | +$1,131 | −$279 |

**Recommended execution model: Scenario B.** Resting NO buy at
$0.60 placed at entry time; taker fallback if price gaps to
≤ $0.34 and resting order unfilled. Documented in
PHASE4A_DESIGN.md Decision 6.

## 2026-04-22 — Stop params sweep (retracted)

40-cell grid sweep: NO bid $0.58–$0.65 × taker fallback
$0.30–$0.38. Optimal cell: $0.58/$0.30 at +$2,252/yr. See
`docs/analysis_outputs/strategy4_stop_params.md`.

**RETRACTED.** Methodology only repriced existing stop events
at different fill prices — it was blind to entries that would
have been converted from stops to winners under different stop
levels (i.e., a wider stop catches positions that would have
recovered). The finding was superseded by the full sensitivity
sweep below.

## 2026-04-22 — $0.40 stop confirmed robust (full sensitivity sweep)

Full re-simulation at 11 stop levels ($0.35–$0.45) across all
404 games. Unlike the retracted params sweep, this replays the
entire entry/exit/stop logic at each level, correctly counting
converted winners. See
`docs/analysis_outputs/strategy4_stop_sensitivity.md`.

| Stop level | Entries | Hit % | Annual EV | Δ vs $0.40 |
|-----------|---------|-------|-----------|-----------|
| $0.35 | 311 | 57.9% | +$2,113 | +$227 |
| $0.38 | 311 | 54.0% | +$1,937 | +$51 |
| $0.40 | 311 | 52.4% | +$1,886 | — |
| $0.42 | 305 | 50.8% | +$1,871 | −$15 |
| $0.45 | 288 | 47.2% | +$1,039 | −$847 |

$0.35 appears best in the pooled data (+$227/yr over $0.40)
but the curve is bimodal and 5 of 7 spread buckets disagree
with the pooled optimum. $0.42 was refuted: 6 entries that
would have hit $0.90 are instead stopped, costing -$15/yr net.

**Conclusion: $0.40 confirmed robust.** All 11 levels are
positive EV. No parameter change warranted. The pooled $0.35
advantage is consistent with noise, not structure.

STRATEGY4_SPEC.md §10 #3 upgraded from PARTIALLY RESOLVED
to RESOLVED.

## 2026-04-23 — S1 bilateral operational simulation (404 games)

First simulation of Strategy 1 bilateral position construction
using realistic live-engine entry policies on the full 404-game
Kalshi paired dataset. See
`docs/analysis_outputs/strategy1_bilateral_sim.md`.

Three entry policies × 14 asymmetric threshold pairs. Stranded-
leg outcomes under 8 exit strategies (hold-to-resolution,
time-based abandonment at 5/10/15/20/30 min, price-based stops
at $0.10/$0.15/$0.20).

**Recommended operating point:** Policy A (any observation
≤ threshold, including opening tick), thresholds X=$0.20
(leg 2, tight), Y=$0.35 (leg 1, wide), T5 stranded exit.

| Component | Count | Total P&L | Per-unit |
|-----------|-------|-----------|----------|
| Completed bilaterals | 90 | +$4,817 | +$53.52 |
| Stranded T5 exits | 314 | −$681 | −$2.17 |
| **Net (404 games)** | | **+$4,136** | **+$10.24/game** |

Annual EV: **+$5,603/yr** (upper bound — `dog_vwap = 1 - fav_vwap`
approximation inflates bilateral cost slightly; real EV est.
10–20% lower → conservative range +$4,000–$4,500/yr).

### Key structural findings

1. **100% of completed bilaterals are "collapse bilaterals."**
   Leg 1 side's bid is ≥ $0.70 when leg 2 fills. Zero natural
   bilaterals (game still in doubt at leg 2 time). Every leg 2
   buy is insurance during the other side's collapse. Mean
   insurance value: +$4.36. 21% of cases saved (leg 1 side
   actually lost).

2. **Policy A (most aggressive) beats Policy B (downward
   crossing only).** Policy B has higher completion rate (32.8%
   vs 22.3%) but enters 37% fewer games, netting $4,780/yr vs
   $5,603/yr. Stranded-leg losses are so small with T5 that
   marginal entries from aggressive policy are net positive.

3. **All 7 spread buckets positive.** Core (|spread| ≤ 6):
   $14–18/game. 10.5+: $4.90/game (low bilateral completion
   rate but still net positive after T5 exits).

Prior estimate from `strategy1_recalibrated_bilateral.md` was
+$1,608/yr based on ESPN-calibrated rates with perfect bilateral
capture and no stranded-leg modeling. The simulation's +$5,603
reflects the reality that entering every game (not just bilateral
candidates) and exiting stranded legs quickly produces better
aggregate EV.

**Supersedes** the prior $1,608/yr estimate. Living spec:
`docs/STRATEGY1_SPEC.md`.

## 2026-04-23 — S1 bilateral follow-up: re-entry, T5 distribution, blowout filter

Three targeted investigations on the recommended S1 operating
point. See
`docs/analysis_outputs/strategy1_bilateral_followup.md`.

### Re-entry is structurally broken

Bilateral completion requires minimum 71 ticks (35.5 min)
between legs; median 209 ticks (104.5 min). T5 exits at 10
ticks (5 min). Re-entry therefore produces **zero bilateral
completions** — every additional entry is pure T5 churn.

Six configs tested (cooldown {1, 10} × loss_cap {none, $10,
$20}). All negative EV (−$2,595 to −$2,871/yr). Worst single-
game outcome under uncapped re-entry: −$33.49 (3 cascading
T5 exits during sustained collapse).

T5 and re-entry are fundamentally incompatible: T5 optimizes
stranded-leg losses by exiting before bilateral can complete,
and re-entry re-enters games where bilateral already failed
to form.

### T5 exit distribution is wider than the mean suggests

314 stranded T5 exits: 32% profitable (mean +$2.88), 68%
losses (mean −$4.53). Aggregate mean −$2.17.

By entry price: $0.10–$0.15 is sweetspot (53% profitable,
mean −$0.27). $0.30–$0.35 is worst (26% profitable, mean
−$3.04). Limited downside at very low prices produces better
T5 dynamics.

Percentiles: P10 = −$8.62, P25 = −$4.70, median = −$1.86,
P75 = +$0.69, P90 = +$3.39.

### Blowout filter helps per-game but costs total volume

Three filters (skip games where either side opens ≥ cutoff):

| Filter | Games | EV/game | Excluded EV/game |
|--------|-------|---------|------------------|
| None | 404 | $10.24 | — |
| ≥ $0.80 | 257 | $13.12 | excluded = +$5.20 |
| ≥ $0.75 | 218 | $13.80 | excluded = +$6.06 |
| ≥ $0.70 | 183 | $14.85 | excluded = +$6.42 |

Excluded games are themselves positive EV — the filter
cuts profitable entries along with unprofitable ones.
Corrected annual EV (proportional scaling) shows filtering
costs $1,500–$2,900/yr in missed opportunities. **Not
recommended** for the engine. Engine should enter all games.

## 2026-04-23 — S1 corrected analysis: KILL (0/62 configs positive)

The prior bilateral simulation (`strategy1_bilateral_sim.md`)
contained a fundamental design error: it combined T5 exits
(sell after 5 min) with bilateral completions (require 35+ min
hold) in the same P&L. A live engine cannot know at minute 5
which entries will complete bilaterally. The +$5,603/yr was
not operationally achievable.

Corrected analysis (`strategy1_swing_corrected.md`) replaced
the bilateral framing with coherent state-machine configs.
Key equivalence: selling at $0.65 = buying both sides at
$0.20 + $0.35. Swing trade captures identical economics.

62 configs tested (profit targets, stops, trailing stops,
time limits, combinations). **Zero positive EV.** Best:
trailing stop -$0.08 at -$103/yr. Hold-to-resolution:
-$3,562/yr.

Price trajectory characterization: 22% of games see underdog
peak > $0.80 (huge winners), 20% never reach $0.20 (collapse
from entry). Median time to $0.65: 172 ticks (86 min). Max
drawdown before peak for games reaching $0.50+: mean $0.08-
$0.11. The 22% of games that produce large underdog rallies
cannot compensate for the 78% that don't.

**S1 bilateral is killed.** The underdog side of Kalshi NBA
markets does not contain tradeable edge at any tested price
level or exit strategy. Alpha stack reduced to S4A + S3.

## 2026-04-23 — S4B underdog hybrid: KILL (revalidated +$148/yr)

Revalidated S4B on 404 games (prior: +$1,105/yr on 168 games).
1,323 configs tested. Best: momentum $0.10-$0.35, run $0.03,
lookback 180s, +$0.15 swing, stop $0.05 → +$148/yr ($0.19
per entry). 14 of 1,323 configs positive (1.1%).

Spread buckets: 3 of 7 negative EV. 8.5-10.0 bucket alone
provides +$1,839 of +$148 total — one bucket doing all the
work is noise. Resolution-lottery hybrid abandoned by
optimizer (best config is pure swing, zero hold-to-resolution).

S1 overlap analysis: 29% of S4B entries overlap with S1 leg 1.
S4B's exit rule beats S1's T5 by $2.83/entry on overlapping
trades, but this is moot — S1 itself is killed.

**S4B is killed.** Consistent with S1 kill — both fail because
the underdog base rate (~12-18% win probability) cannot be
overcome by exit-side mechanics.

## 2026-04-23 — Team-level S4A profiles: Kalshi 404-game dataset (playoff 16)

New script `analysis/team_profiles_playoff16.py`. Observational
profiling of the 16 playoff teams across the 404-game Kalshi
paired dataset. Per-team volatility, swing count, $0.50 crossover
rate, S4A hit rate, collapse rate, underdog upset rate. Split by
role × venue × spread bucket × opponent quality × period.

### S4A hit rate dispersion (Kalshi)

Wide dispersion observed: NYK 78.6% (n=14) to HOU 30.4% (n=23).
9 teams in Tier 1 (≥60%), 4 in Tier 2 (45-59%), 3 in Tier 3
(<45%). HOU was the only team with 95% CI entirely below pooled
52.4% — appeared to be a statistically significant avoid.

Tier 1 aggregate: 130 entries, 66.9% hit, +$7.73 mean P&L.
Tier 3 aggregate (HOU/LAL/TOR): 41 entries, ~34% hit, negative
mean P&L. If-we-filtered: Tier 1 only at +$3,141/yr vs
all-16-teams at +$1,661/yr.

### Other notable findings

- ATL: lowest collapse rate as favorite (11.8%, Z=-1.91).
- DEN: most volatile favorite (8.5 swings/game, Z=+2.04).
- PHX: extreme home/away split (40% home-fav hit vs 83% away).
- HOU Q4 as favorite: 0% S4A hit rate on 5 entries.
- Period pattern: Q3 entries showed highest hit rates across
  multiple teams, consistent with STRATEGY4_SPEC.md §7.

**Status: provisional — pending ESPN validation.** Individual
team CIs are wide (±15-20pp). Only HOU clears significance.
Team rankings may be noise at n=9-23 per team.

## 2026-04-23 — Team-level S4A profiles: ESPN full season — NOT VALIDATED

New script `analysis/team_profiles_espn_full.py`. Extended team
profiling to the full 1,234-game ESPN WP dataset (all 30 teams).
Applied the same S4A signal parameters to ESPN WP values.
Primary goal: validate Kalshi team-level hit rate dispersion at
3× sample size via Spearman rank-order correlation.

### Validation result

**Spearman ρ = −0.106, p = 0.69. Verdict: NOT VALIDATED.**

Team rankings between Kalshi and ESPN are statistically
indistinguishable from random. Only 3 of 16 playoff teams
matched tiers across datasets (DET, LAL, PHX).

### Key reversals

| Team | Kalshi rank | ESPN rank | Shift |
|------|-----------|---------|-------|
| NYK | 1 (78.6%) | 16 (32.8%) | −15 |
| ATL | 2 (75.0%) | 14 (38.1%) | −12 |
| HOU | 16 (30.4%) | 7 (45.9%) | +9 |
| TOR | 14 (44.4%) | 4 (53.3%) | +10 |

HOU — the only "statistically significant avoid" on Kalshi —
reverted to pooled average on ESPN (45.9% vs 44.2% pooled,
CI spans pooled). The significance finding was noise.

### Implication

**Team identity is not a stable predictor of S4A hit rate.**
The dispersion observed on the 404-game Kalshi dataset was
driven by small per-team sample sizes (n=9-23), not by
structural team-level tendencies. At 3× sample (n=24-62 per
team on ESPN), the rankings scramble completely.

**S4A's team-agnostic design is validated.** The engine should
continue trading all games with the same parameters. No team
filter, no team-specific params, no tier system. The pooled
53% hit rate is genuinely a pooled phenomenon, not a bimodal
distribution masked by aggregation.

**The Tier 1 parameter sensitivity sweep planned as a follow-up
is cancelled** — there is no stable Tier 1 to parameterize for.
