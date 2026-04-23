# Strategy 4B Revalidation (404-Game Dataset)
_Generated: 2026-04-23T04:24:11.662835+00:00_
Full S4B config sweep on **404 games** from the Kalshi-confirmed paired dataset (all spreads). Prior S4B result on 168 games (|spread| ≤ 6) was +$1105/yr with a fragile 12.6% resolution-win rate — this revalidation tests whether that holds on the larger dataset, adds stop-loss variants not in the original, breaks down by spread bucket, and quantifies overlap with S1 bilateral's stranded-leg mechanics.

**Data approximation (inherited from parent):** `dog_vwap` is computed as `1 - fav_kalshi_vwap`. Kalshi bid-ask spread (1-2c typical) is not modeled. Directional findings are robust; absolute EV should be read as an upper bound.

## Section 1 — S4B config sweep (momentum + static × hybrid × stop)
Total configs tested: **1323**. Top 10 by annual EV:

| # | Label | Entries | Target | Stop | Held | Res win | Res loss | Mean P&L | Annual EV |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | mom $0.10-$0.35 run$0.03 lb180s +$0.15 swing stop$0.05 | 574 | 170 | 404 | 0 | 0 | 0 | $+0.19 | $+148 |
| 2 | mom $0.15-$0.35 run$0.03 lb180s +$0.15 swing stop$0.05 | 529 | 160 | 369 | 0 | 0 | 0 | $+0.18 | $+130 |
| 3 | mom $0.15-$0.35 run$0.03 lb300s +$0.10 swing stop$0.05 | 540 | 208 | 332 | 0 | 0 | 0 | $+0.13 | $+98 |
| 4 | mom $0.10-$0.35 run$0.03 lb300s +$0.15 swing stop$0.05 | 583 | 170 | 413 | 0 | 0 | 0 | $+0.12 | $+92 |
| 5 | mom $0.10-$0.35 run$0.05 lb300s +$0.10 swing stop$0.05 | 528 | 204 | 324 | 0 | 0 | 0 | $+0.12 | $+84 |
| 6 | mom $0.15-$0.35 run$0.03 lb300s +$0.15 swing stop$0.05 | 534 | 159 | 375 | 0 | 0 | 0 | $+0.11 | $+82 |
| 7 | mom $0.25-$0.35 run$0.03 lb300s +$0.20 swing stop$0.05 | 420 | 106 | 314 | 0 | 0 | 0 | $+0.12 | $+67 |
| 8 | mom $0.25-$0.30 run$0.03 lb300s +$0.10 swing stop$0.05 | 362 | 140 | 222 | 0 | 0 | 0 | $+0.08 | $+38 |
| 9 | mom $0.10-$0.30 run$0.03 lb300s +$0.20 swing stop$0.05 | 534 | 125 | 409 | 0 | 0 | 0 | $+0.05 | $+36 |
| 10 | mom $0.25-$0.30 run$0.03 lb300s +$0.15 swing stop$0.05 | 356 | 108 | 248 | 0 | 0 | 0 | $+0.06 | $+30 |

Across all 1323 configs: **14 positive EV** (1.1%), **1309 non-positive**. Near-breakeven (|annual EV| ≤ $50): 13.

## Section 2 — Best config deep dive
**Best config:** `mom $0.10-$0.35 run$0.03 lb180s +$0.15 swing stop$0.05`

- Entries: 574
- Target (swing) exits: 170 (29.6%)
- Stop exits: 404 (70.4%)
- Held to resolution: 0 (0.0%)
  - Resolution wins: 0
  - Resolution losses: 0
- Mean P&L: $+0.19
- Total P&L: $+109.52
- Annual EV: $+148

Hold time (seconds): median 660s, P25 330s, P75 1380s, max 5400s

Per-game entry distribution: 60 games with 1 entry, 257 games with 2 entries, 87 games with 0 entries

### 168-game subset vs full 404-game

| Metric | 168-game subset (|spread| ≤ 6) | Full 404-game |
|---|---:|---:|
| Games | 171 | 404 |
| Entries | 240 | 574 |
| Target exits | 71 | 170 |
| Mean P&L | $-0.07 | $+0.19 |
| Annual EV | $-57 | $+148 |

Prior published result (different config): +$1105/yr on 168 games with momentum, entry $0.25-$0.35, run $0.03, lookback 300s, exit +$0.20, hybrid 50/50. The revalidation sweep may select a different 'best' config — direct comparison against the published number is heuristic, not strict.

## Section 3 — Spread bucket breakdown (top 3 configs)

### Top 1: `mom $0.10-$0.35 run$0.03 lb180s +$0.15 swing stop$0.05` — annual EV $+148

| |Spread| | Games | Entries | Swing exits | Res wins | Res losses | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1.0-2.0 | 36 | 43 | 11 | 0 | 0 | $-1.17 | $-765 ⚠ |
| 2.5-3.5 | 69 | 88 | 30 | 0 | 0 | $+0.83 | $+582 |
| 4.0-5.0 | 31 | 49 | 12 | 0 | 0 | $-1.21 | $-1,048 ⚠ |
| 5.5-6.0 | 35 | 60 | 18 | 0 | 0 | $+0.31 | $+286 |
| 6.5-8.0 | 46 | 83 | 26 | 0 | 0 | $+0.71 | $+697 |
| 8.5-10.0 | 38 | 69 | 25 | 0 | 0 | $+1.85 | $+1,839 |
| 10.5+ | 149 | 182 | 48 | 0 | 0 | $-0.32 | $-216 ⚠ |

_Negative-EV buckets: 1.0-2.0, 4.0-5.0, 10.5+_

### Top 2: `mom $0.15-$0.35 run$0.03 lb180s +$0.15 swing stop$0.05` — annual EV $+130

| |Spread| | Games | Entries | Swing exits | Res wins | Res losses | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1.0-2.0 | 36 | 41 | 9 | 0 | 0 | $-2.23 | $-1,392 ⚠ |
| 2.5-3.5 | 69 | 86 | 30 | 0 | 0 | $+1.12 | $+767 |
| 4.0-5.0 | 31 | 44 | 12 | 0 | 0 | $-0.67 | $-519 ⚠ |
| 5.5-6.0 | 35 | 59 | 18 | 0 | 0 | $+0.35 | $+320 |
| 6.5-8.0 | 46 | 79 | 24 | 0 | 0 | $+0.46 | $+429 |
| 8.5-10.0 | 38 | 67 | 24 | 0 | 0 | $+1.58 | $+1,528 |
| 10.5+ | 149 | 153 | 43 | 0 | 0 | $-0.27 | $-154 ⚠ |

_Negative-EV buckets: 1.0-2.0, 4.0-5.0, 10.5+_

### Top 3: `mom $0.15-$0.35 run$0.03 lb300s +$0.10 swing stop$0.05` — annual EV $+98

| |Spread| | Games | Entries | Swing exits | Res wins | Res losses | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1.0-2.0 | 36 | 41 | 14 | 0 | 0 | $-1.03 | $-643 ⚠ |
| 2.5-3.5 | 69 | 88 | 37 | 0 | 0 | $+0.84 | $+584 |
| 4.0-5.0 | 31 | 44 | 17 | 0 | 0 | $-0.12 | $-90 ⚠ |
| 5.5-6.0 | 35 | 62 | 23 | 0 | 0 | $-0.19 | $-181 ⚠ |
| 6.5-8.0 | 46 | 80 | 30 | 0 | 0 | $-0.15 | $-145 ⚠ |
| 8.5-10.0 | 38 | 68 | 29 | 0 | 0 | $+0.87 | $+855 |
| 10.5+ | 149 | 157 | 58 | 0 | 0 | $+0.07 | $+39 |

_Negative-EV buckets: 1.0-2.0, 4.0-5.0, 5.5-6.0, 6.5-8.0_

## Section 4 — S1 overlap analysis
S1 bilateral Policy A fires leg 1 on every game at the first tick where either side's YES bid ≤ $0.35 (typically the underdog at tip-off). S4B is always on the dog side at $0.10-$0.35 with a momentum trigger. Substantial overlap is possible. This section quantifies whether S4B adds incremental value or just repackages value S1 already captures.

**Overlap definition:** S4B trade overlaps S1 iff same game, S1 leg1 is on dog side, entry prices within $0.05, entry ticks within 20. S1 P&L is its T5 exit P&L (what S1 earns on that leg — note: bilateral-completing S1 entries get a different actual exit; T5 P&L is used here as the counterfactual comparison to S4B's exit rule on the same entry).

| Category | Count | Mean S1 P&L | Mean S4B P&L | Mean delta | Total S4B P&L |
|---|---:|---:|---:|---:|---:|
| Overlapping entries | 166 | $-1.45 | $+1.39 | $+2.83 | $+230.33 |
| S4B-only entries | 408 | n/a | $-0.30 | n/a | $-120.81 |
| **Combined S4B total** | **574** | — | — | — | **$+109.52** |

**Incremental value calculation (if running S4B on top of S1):**
- S4B-only entries contribute full P&L: $-120.81
- Overlapping entries contribute the delta vs S1's T5 exit: $+470.58
- **Total incremental P&L: $+349.77** on 404 games → **$+474/yr incremental**

For reference, S4B standalone annual EV: $+148/yr. Subtracting the S1-redundant portion yields the incremental figure above.

## Section 5 — Verdict and recommendation

### 1. Does S4B survive revalidation?
- Best config annual EV: **$+148/yr** on 404 games (vs prior +$1105/yr on 168 games, different config).
- Verdict: **WEAKENED**.

### 2. Is S4B incremental to S1?
- Overlap rate: **166 / 574 S4B entries (28.9%)** overlap with S1 leg 1.
- S4B-only (purely incremental) entries: 408.
- Mean delta on overlapping entries: **$+2.83** (S4B exit vs S1 T5 exit).
- Incremental annual EV: **$+474/yr**.
- Verdict: **COMPLEMENTARY**. S4B's exit rule is meaningfully better than S1's T5 exit on overlapping entries. Consider replacing T5 with S4B-style swing exits in S1's stranded-leg management, rather than building S4B as a separate module.

### 3. Updated alpha stack
| Strategy | Annual EV contribution |
|---|---:|
| S4A (core, |spread| ≤ 6) | +$7,075 |
| S4A (expansion, |spread| > 6) | +$3,644 |
| S1 bilateral | +$4,000-$5,600 |
| S3 filtered | +$578-$825 |
| **S4B (revalidated)** | **Replace S1 T5 with S4B exit → +$637/yr estimated lift on S1** |

S4B informs S1 exit design rather than running as its own module.

