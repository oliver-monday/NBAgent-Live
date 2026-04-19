# Strategy 3 oscillation analysis — HOU-LAL (2026-04-18)

First Kalshi oscillation characterization on real in-game data. HOU-LAL NBA Play-In, LAL home, won 107-98. Logger captured the live window at 30s cadence.

**n=1 caveat**: all findings below are single-game observations. Strategy 3 viability requires multi-game confirmation. This analysis validates the pipeline and produces a proof-of-concept characterization, not a graduation test.

## 1. Price timeseries summary

Live window: **2026-04-19T00:48:06.093415+00:00** → **2026-04-19T03:06:05.941785+00:00**. Tip anchored on ESPN-verified tip-off (2026-04-19 00:48 UTC from Phase 3B smoke test). End trimmed at first 5 consecutive snapshots with mid in [0, 0.02] ∪ [0.98, 1]. Volume-rate auto-detector computed as cross-check (see stdout); deferred to known-tip for this single-game deep-dive due to sensitivity to pre-tip flow spikes and logger-gap artifacts.

| Side | n snapshots | Duration | Median gap | p5/p95 gap | Price range | Mean spread |
|------|-------------|----------|------------|------------|-------------|-------------|
| HOU | 277 | 138.0 min | 30.0s | 29.7s / 30.3s | [0.015, 0.615] | $0.011 |
| LAL | 277 | 138.0 min | 30.0s | 29.7s / 30.2s | [0.405, 0.985] | $0.011 |

**Complement check** (home + away mid): n=277, mean |dev| = 0.0036, max |dev| = 0.0300. ⚠


## 2. Swing detection and characterization

Algorithm: 3-point rolling median → local extrema → merge consecutive same-type → drop swings with magnitude < $0.02. Swings are (trough→peak) upswings or (peak→trough) downswings on smoothed mid.

### Per-side swing counts by magnitude threshold

| Side | ≥$0.05 | ≥$0.10 | ≥$0.15 | ≥$0.20 | Total ≥$0.02 |
|------|--------|--------|--------|--------|--------------|
| HOU | 11 | 5 | 3 | 3 | 22 |
| LAL | 12 | 5 | 3 | 3 | 19 |

### Pooled magnitude + duration stats

| Stat | Magnitude | Duration (min) |
|------|-----------|---------------|
| median | $0.0600 | 5.99 |
| mean   | $0.0820 | 6.40 |
| p75    | $0.1000 | 8.00 |
| p90    | $0.2000 | 13.01 |
| max    | $0.2300 | 26.00 |

### All swings ≥ $0.10 (pooled both sides, N=10)

| side | type | start | end | start price | end price | magnitude | duration |
|------|------|-------|-----|-------------|-----------|-----------|----------|
| LAL | up | 00:48:06 | 00:56:05 | 0.425 | 0.535 | $0.110 | 8.0 min |
| HOU | down | 00:49:36 | 00:56:06 | 0.605 | 0.475 | $0.130 | 6.5 min |
| LAL | up | 01:18:05 | 01:27:05 | 0.535 | 0.645 | $0.110 | 9.0 min |
| HOU | down | 01:18:05 | 01:26:35 | 0.465 | 0.355 | $0.110 | 8.5 min |
| LAL | down | 01:42:05 | 02:08:05 | 0.675 | 0.475 | $0.200 | 26.0 min |
| HOU | up | 01:42:05 | 02:08:05 | 0.325 | 0.525 | $0.200 | 26.0 min |
| LAL | up | 02:13:36 | 02:23:35 | 0.555 | 0.765 | $0.210 | 10.0 min |
| HOU | down | 02:13:36 | 02:23:35 | 0.445 | 0.245 | $0.200 | 10.0 min |
| HOU | down | 02:46:36 | 03:06:05 | 0.245 | 0.015 | $0.230 | 19.5 min |
| LAL | up | 02:47:05 | 03:00:35 | 0.760 | 0.985 | $0.225 | 13.5 min |

## 3. Round-trip opportunity identification — extreme grid

Greedy scan: enter when mid ≤ entry threshold, exit on first subsequent mid ≥ exit threshold, then resume scanning. Incomplete trips (still in position at game end) reported but excluded from summary statistics.

This grid uses extreme-price entries ($0.15–$0.30) inherited from Strategy 1/2 thinking. The zero-result below was the motivation for Section 3B's mid-range re-run.

### Summary — extreme grid (both sides combined)

| Entry | Exit | Δ | N trips | Mean hold (min) | Mean gross | Mean net (taker) | Mean net (maker) |
|-------|------|---|---------|-----------------|------------|------------------|-------------------|
| 0.15 | 0.25 | +0.10 | 0 | — | — | — | — |
| 0.15 | 0.30 | +0.15 | 0 | — | — | — | — |
| 0.15 | 0.35 | +0.20 | 0 | — | — | — | — |
| 0.20 | 0.30 | +0.10 | 0 | — | — | — | — |
| 0.20 | 0.35 | +0.15 | 0 | — | — | — | — |
| 0.20 | 0.40 | +0.20 | 0 | — | — | — | — |
| 0.25 | 0.35 | +0.10 | 0 | — | — | — | — |
| 0.25 | 0.40 | +0.15 | 0 | — | — | — | — |
| 0.25 | 0.45 | +0.20 | 0 | — | — | — | — |
| 0.30 | 0.40 | +0.10 | 0 | — | — | — | — |
| 0.30 | 0.45 | +0.15 | 0 | — | — | — | — |
| 0.30 | 0.50 | +0.20 | 0 | — | — | — | — |

### No complete round-trips at any extreme-grid pair

HOU-LAL's swings all started from mid ≥ $0.325 and exits required rebound above entry + $0.10. HOU never rebounded above the exit threshold from any entry ≤ $0.30. This is the finding that drove Section 3B's mid-range grid.


## 3B. Round-trip opportunity identification — mid-range grid

Entry thresholds $0.30–$0.45, exit +$0.10 or +$0.15. Aligned with where HOU-LAL's actual swings sit (see Section 2). The interpretive question: do real oscillations in the competitive mid-range produce executable round-trips at realistic Strategy 3 entry prices?

### Summary — mid-range grid (both sides combined)

| Entry | Exit | Δ | N trips | Mean hold (min) | Mean gross | Mean net (taker) | Mean net (maker) |
|-------|------|---|---------|-----------------|------------|------------------|-------------------|
| 0.30 | 0.40 | +0.10 | 0 | — | — | — | — |
| 0.30 | 0.45 | +0.15 | 0 | — | — | — | — |
| 0.35 | 0.45 | +0.10 | 1 | 23.0 | $14.00 | $10.66 | $13.16 |
| 0.35 | 0.50 | +0.15 | 1 | 41.0 | $18.00 | $14.66 | $17.16 |
| 0.40 | 0.50 | +0.10 | 1 | 45.5 | $13.00 | $9.57 | $12.14 |
| 0.40 | 0.55 | +0.15 | 0 | — | — | — | — |
| 0.45 | 0.55 | +0.10 | 1 | 8.0 | $13.00 | $9.55 | $12.13 |
| 0.45 | 0.60 | +0.15 | 1 | 34.0 | $19.00 | $15.62 | $18.15 |

### All round-trips at (0.45, 0.55) — highest-count pair

| side | entry ts | entry | exit ts | exit | hold (min) | gross | taker fees | net (taker) | net (maker) | MAE price | MAE drawdown | incomplete |
|------|----------|-------|---------|------|------------|-------|------------|-------------|-------------|-----------|--------------|------------|
| LAL | 00:48:06 | 0.425 | 00:56:05 | 0.555 | 8.0 | $13.00 | $3.45 | $9.55 | $12.13 | 0.405 | $0.020 (5%) | no |
| HOU | 01:09:05 | 0.445 | 03:06:05 | 0.015 | 117.0 | $-43.00 | $1.84 | $-44.84 | $-43.47 | 0.015 | $0.430 (97%) | yes |

## 3C. Intra-position drawdown (maximum adverse excursion)

For each completed round-trip (both Section 3 and 3B), we scan the mid timeseries between entry and exit and record the lowest observed mid. The drawdown from entry to that low is the trader's maximum unrealized loss during the hold — how much they had to stomach before the exit signal fired. A trip that nets $15 but first drops $12 has a materially different risk profile than one that monotonically rose.

**N completed trips pooled (Sections 3 + 3B):** 5

| Stat | Drawdown ($) | Drawdown (% of entry) | Time to MAE (sec) |
|------|--------------|------------------------|-------------------|
| median | $0.040 | 11.6% | 870 |
| mean   | $0.042 | 11.1% | 612 |
| max    | $0.090 | 22.8% | 1139 |

## 3D. Favorite-side round-trip scan (with resolution backstop)

LAL was home-court favorite in HOU-LAL and won 107-98, so any LAL YES position held to settlement resolves at $1.00. Entry thresholds $0.55-$0.65 target favorite-side dips; if the dip recovers to the exit threshold, the trip is a completed round-trip (like Sections 3/3B). If the favorite never recovers and instead wins the game, the position settles at $1.00 — converting a 'missed exit' into an accidental bonus. If the favorite loses, the position settles at $0.00 and the trader takes a full-sized loss.


### Summary — favorite-side grid

| Entry | Exit | Completed | Res wins | Res losses | Mean net (maker, completed) | Mean net (resolution) |
|-------|------|-----------|----------|-------------|-----------------------------|----------------------|
| 0.55 | 0.65 | 2 | 0 | 0 | $18.42 | — |
| 0.55 | 0.70 | 2 | 0 | 0 | $23.45 | — |
| 0.60 | 0.70 | 2 | 0 | 0 | $20.71 | — |
| 0.60 | 0.75 | 1 | 0 | 0 | $33.25 | — |
| 0.65 | 0.75 | 1 | 0 | 0 | $33.25 | — |
| 0.65 | 0.80 | 1 | 0 | 0 | $38.30 | — |

### All favorite-side trips (completed + resolution)

| entry ts | entry | exit/res ts | exit/res price | hold (min) | gross | net (maker) | MAE drawdown | outcome |
|----------|-------|-------------|----------------|-----------|-------|-------------|--------------|---------|
| 00:48:06 (@0.55→0.65) | 0.425 | 01:26:35 | 0.655 | 38.5 | $23.00 | $22.17 | $0.020 (5%) | completed |
| 00:48:06 (@0.55→0.70) | 0.425 | 01:41:05 | 0.715 | 53.0 | $29.00 | $28.21 | $0.020 (5%) | completed |
| 00:48:06 (@0.60→0.70) | 0.425 | 01:41:05 | 0.715 | 53.0 | $29.00 | $28.21 | $0.020 (5%) | completed |
| 00:48:06 (@0.60→0.75) | 0.425 | 02:23:35 | 0.765 | 95.5 | $34.00 | $33.25 | $0.020 (5%) | completed |
| 00:48:06 (@0.65→0.75) | 0.425 | 02:23:35 | 0.765 | 95.5 | $34.00 | $33.25 | $0.020 (5%) | completed |
| 00:48:06 (@0.65→0.80) | 0.425 | 02:34:35 | 0.815 | 106.5 | $39.00 | $38.30 | $0.020 (5%) | completed |
| 01:49:05 (@0.60→0.70) | 0.575 | 02:22:35 | 0.715 | 33.5 | $14.00 | $13.21 | $0.100 (17%) | completed |
| 01:49:35 (@0.55→0.65) | 0.520 | 02:20:06 | 0.675 | 30.5 | $15.50 | $14.67 | $0.045 (9%) | completed |
| 01:49:35 (@0.55→0.70) | 0.520 | 02:22:35 | 0.715 | 33.0 | $19.50 | $18.70 | $0.045 (9%) | completed |

## 3E. Dual-exit expected value (favorite side)

For each entry threshold, pool positions entered at that level under the tightest exit rule (+$0.10) and compute the blended EV across completed round-trips and resolution outcomes. This captures the value of the hold-to-resolution backstop: even if the active-exit rule fails, a favorite win saves the position, and a favorite loss destroys it.

| Entry | n_total | n_completed | n_res_win | n_res_loss | Blended EV / trade (maker) |
|-------|---------|-------------|-----------|------------|---------------------------|
| 0.55 | 2 | 2 | 0 | 0 | $18.42 |
| 0.60 | 2 | 2 | 0 | 0 | $20.71 |
| 0.65 | 1 | 1 | 0 | 0 | $33.25 |

## 4. Bid-ask spread at Strategy 3 entry price levels

Spread observations while mid ≤ $0.30, bucketed by mid price level. Reports spread in dollars and as a percentage of mid (the latter is the correct cost metric for Strategy 3 — at $0.02 spread, mid=$0.15 is 13% cost vs mid=$0.25 is 8%).

| Bucket | n | Mean spread | Median | p75 | Max | Mean spread / mid |
|--------|---|-------------|--------|-----|-----|-------------------|
| ≤ $0.10 | 31 | $0.0100 | $0.0100 | $0.0100 | $0.0100 | 29.4% |
| (0.10, 0.15] | 2 | $0.0150 | $0.0150 | $0.0175 | $0.0200 | 12.0% |
| (0.15, 0.20] | 17 | $0.0106 | $0.0100 | $0.0100 | $0.0200 | 5.7% |
| (0.20, 0.25] | 19 | $0.0111 | $0.0100 | $0.0100 | $0.0200 | 4.9% |
| (0.25, 0.30] | 19 | $0.0105 | $0.0100 | $0.0100 | $0.0200 | 4.0% |

## 5. Top-of-book depth at Strategy 3 entry price levels

`yes_bid_size_fp` at top-of-book when mid is in each entry zone. Flag: whether depth ≥ 50,000 (~50 contracts at $1 nominal — the kill-criteria minimum fill size).

| Bucket | n | Mean size | Median | Min | Max | ≥50k depth? |
|--------|---|-----------|--------|-----|-----|-------------|
| ≤ $0.10 | 31 | 307,971 | 129,103 | 5,005 | 755,953 | 77% ✓ |
| (0.10, 0.15] | 2 | 1,349 | 1,349 | 76 | 2,622 | 0% ⚠ |
| (0.15, 0.20] | 17 | 397,444 | 206,143 | 220 | 1,203,361 | 59% ✓ |
| (0.20, 0.25] | 19 | 82,398 | 5,844 | 6 | 464,348 | 16% ⚠ |
| (0.25, 0.30] | 19 | 63,099 | 25,472 | 3,083 | 176,713 | 37% ⚠ |

## 6. Strategy 3 viability scorecard (n=1)

Single-game observation only — n=1 is not statistically meaningful. This characterizes the pipeline and produces a proof-of-concept reading, not a graduation test.

| Criterion | Threshold | Observed (HOU-LAL) | Status |
|-----------|-----------|--------------------|--------|
| Round-trip frequency | ≥ 8% of competitive games | n/a (n=1) | — |
| Swing magnitude (median of ≥$0.10 swings) | ≥ $0.10 capture | $0.200 | ✓ Pass |
| Realized spread at entry (median, mid ≤ $0.30) | < $0.03 | $0.0100 | ✓ Pass |
| Book depth at entry (% ≥ 50k at mid ≤ $0.30) | ≥ 50 contracts | 50% of snapshots ≥ 50k | ✓ Pass |
| Hold time (median at 0.25→0.35) | ≥ 90 seconds | no complete trips | Insufficient data |
| Mid-range round-trips (0.35, 0.50) | ≥ 1 per competitive game | 1 complete | ✓ Pass |
| Mid-range round-trip net profit (maker-maker, pooled) | > $0 after fees | $14.55 | ✓ Pass |
| Max adverse excursion (median of pooled completes) | < 50% of entry price | 11.6% of entry | ✓ Pass |

| Favorite-side round-trips (best pair) | ≥ 1 | 2 completed at (0.55, 0.65) | ✓ Pass |
| Favorite-side blended EV (best entry, maker) | > $0 | $33.25 @ entry 0.65 | ✓ Pass |
