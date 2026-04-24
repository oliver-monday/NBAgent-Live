# Strategy 4A — Ratcheted Drawdown & Capital Requirements
_Generated: 2026-04-24T02:57:46.379017+00:00_
Engine-replay-derived drawdown analysis on the **404-game Kalshi paired dataset**. Two modes:
- **Ratcheted** — `ratchet_trigger=+$0.08` (STRATEGY4_SPEC §5A, the recommended config)
- **Baseline** — `ratchet_trigger=None` (legacy, no ratchet)

Both modes use target-level fills ($0.90 exactly) and the engine's maker/taker fee split (maker on entry + target + ratchet_stop, taker on full stop). Trade counts must match `engine/replay.py`: 358 ratcheted / 311 baseline.

## Section 1 — Entry timeline (ratcheted)
- Total entries: **358** (baseline: 311, Δ +47)
- Date range: 2026-02-20 → 2026-04-16 (56 calendar days)
- Nights with ≥1 entry: **55** (baseline: 55)
- Mean entries/active night: 6.51 (baseline: 5.65)
- Median entries/active night: 6
- P90 entries/night: 11
- Busiest night: **2026-03-11** with **15 entries**

## Section 2 — Running cumulative P&L (ratcheted)
- Final cumulative P&L: **$+1,401.68** (baseline: $+974.55)
- Max cumulative P&L: $+1,401.68 at 2026-04-16
- Min cumulative P&L: $-36.28 at 2026-02-20
- **Max peak-to-trough drawdown: $238.69**
  - Peak: $+419.52 at 2026-03-05
  - Trough: $+180.83 at 2026-03-11
  - Drawdown window: 5 days

### Side-by-side comparison

| Metric | Baseline (no ratchet) | Ratcheted (+$0.08) | Δ |
|---|---:|---:|---:|
| Final P&L | $+974.55 | $+1,401.68 | $+427.13 |
| Max cumulative | $+1,009.13 | $+1,401.68 | $+392.56 |
| Min cumulative | $-36.28 | $-36.28 | $+0.00 |
| **Max drawdown** | **$269.70** | **$238.69** | **$-31.01** |
| Drawdown window | 8 days | 5 days | — |

Engine-baseline numbers above differ from the pre-ratchet report (`strategy4a_drawdown.md` = $326.32 max DD / 8-day window / -$44.70 min) because the engine uses target-level fills ($0.90 exactly) while the pre-ratchet report used observed overshoot prices. Engine numbers are the authoritative reference for Phase 4c planning.

## Section 3 — Win/loss/scratch streaks (ratcheted)
Categories: **Win** (P&L > +$1.00), **Loss** (P&L < -$1.00), **Scratch** (-$1 ≤ P&L ≤ +$1). Scratches are primarily ratchet-stop exits in the ratcheted mode.

- **Longest losing streak: 3 consecutive losses** ($-71.52) [baseline: 7]
- **Longest winning streak: 7 consecutive wins** ($+138.91) [baseline: 10]
- Longest scratch streak: 6
- **Longest drawdown streak** (consecutive non-wins = L + S): 9 ($-39.08)
- Mean loss streak length: 1.38 (n=64) [baseline: 1.76]
- Mean win streak length: 1.71 (n=87) [baseline: 2.42]

### Streak-length distribution (ratcheted)

| Streak length | Win streaks | Loss streaks | Scratch streaks |
|---:|---:|---:|---:|
| 1 | 53 | 44 | 60 |
| 2 | 20 | 16 | 15 |
| 3 | 7 | 4 | 5 |
| 4 | 2 | 0 | 1 |
| 5 | 4 | 0 | 0 |
| 6 | 0 | 0 | 2 |
| 7 | 1 | 0 | 0 |

## Section 4 — Capital requirements (ratcheted)
- Minimum starting capital to never go negative: **$36.28** (baseline: $36.28)
  - Computed as |min cumulative P&L| = |$-36.28|
- Recommended starting capital (×1.5): **$54.42** (baseline: $54.42)

### Capital deployed per entry (entry_price × 100)

| Metric | Ratcheted | Baseline |
|---|---:|---:|
| Mean | $63.83 | $64.44 |
| Median | $64.92 | $65.51 |
| P90 | $73.30 | $73.68 |
| Max | $74.99 | $74.99 |

### Peak concurrent capital deployed

- **Peak capital at risk simultaneously: $272.24** (baseline: $266.78)
- Occurred at: 2026-04-05T20:23:30+00:00
- Concurrent positions at peak: 4 (baseline peak: 4)

(Sweep-line over trade entry/exit timestamps.)

### Return on capital (ratcheted)

- Dataset span: 56 calendar days (calendar-annualization factor ×6.518)
- Final P&L: $+1,401.68 → calendar-annualized ~$+9,135.98/yr
- Season-equivalent annualization (entries/games × 547): ~$+1,898.59/yr (matches `engine/replay.py` +$1,899/yr)
- Return on minimum capital: **25184.0%/yr calendar** ($+9,136 / $36)
- Return on recommended capital: **16789.3%/yr calendar** ($+9,136 / $54)

Both capital denominators are tiny ($20-$70) because the cumulative P&L curve rarely dips far below zero. Return-on-capital percentages above are arithmetic but not the load-bearing number for bankroll sizing — Section 7 uses the peak concurrent + worst-night envelopes instead.

## Section 5 — Nightly P&L distribution (ratcheted)
- Active nights: 55 (baseline: 55)
- Mean nightly P&L: $+25.49 (baseline: $+17.72)
- Median nightly P&L: $+29.05 (baseline: $+16.65)
- **Worst night:** 2026-03-07 at $-118.11 (9 entries) [baseline worst: 2026-03-07 at $-134.48]
- **Best night:** 2026-02-21 at $+157.02 (11 entries)
- **Losing nights:** 20/55 (36.4%) [baseline: 22/55 (40.0%)]

### Nightly P&L histogram (ratcheted)

| P&L bucket | Ratcheted nights | % | Baseline nights | % |
|---|---:|---:|---:|---:|
| > +$50 | 15 | 27.3% | 15 | 27.3% |
| +$25 to +$50 | 13 | 23.6% | 9 | 16.4% |
| +$0 to +$25 | 7 | 12.7% | 9 | 16.4% |
| -$25 to $0 | 10 | 18.2% | 9 | 16.4% |
| -$50 to -$25 | 9 | 16.4% | 11 | 20.0% |
| < -$50 | 1 | 1.8% | 2 | 3.6% |

## Section 6 — Ratchet impact decomposition
### Exits by type

| Exit type | Ratcheted n | Ratcheted % | Ratcheted mean | Baseline n | Baseline % | Baseline mean |
|---|---:|---:|---:|---:|---:|---:|
| target | 149 | 41.6% | $+23.35 | 179 | 57.6% | $+23.20 |
| stop | 88 | 24.6% | $-23.87 | 132 | 42.4% | $-24.08 |
| ratchet_stop | 121 | 33.8% | $+0.19 | 0 | 0.0% | $+0.00 |
| eod | 0 | 0.0% | $+0.00 | 0 | 0.0% | $+0.00 |

### Ratchet conversion analysis

Of the **121 ratchet-scratch exits** in the ratcheted mode, matching each to the closest-entry baseline trade on the same game (one-to-one, by entry bin index):

- Matched to a baseline **full stop**: **56** (46.3%) — ratchet saved a loss
- Matched to a baseline **target ($0.90)**: **48** (39.7%) — ratchet cost a winner
- Matched to a baseline **EOD resolution**: 0
- Unmatched (new entry that didn't exist in baseline): 17

The ratchet adds $+427.13 to total pool P&L on this dataset. Split between:
- 56 scratches that replaced full stops (each saving ≈$21 vs a full stop → ~$1,176 saved)
- 48 scratches that replaced targets (each giving up ≈$23 → ~$1,104 sacrificed)
- 17 new ratchet-mode entries that baseline never fired (each contributes their own target/stop/scratch outcome)

### Cumulative P&L contribution by exit type (ratcheted)

| Exit type | Total P&L contribution | % of total |
|---|---:|---:|
| target | $+3,478.67 | +248.2% |
| stop | $-2,100.57 | -149.9% |
| ratchet_stop | $+23.58 | +1.7% |
| eod | $+0.00 | +0.0% |

## Section 7 — Phase 4c capital planning summary
Plain-English synthesis for Phase 4c (capped real-money deployment) based on the ratcheted engine replay.

**Starting bankroll (recommended):** **$900**.
- Peak concurrent capital in the dataset: $272.24 (4 concurrent positions).
- 3× peak concurrent covers deployed + 2× reserve for drawdown and Kalshi gap-through risk on the full-stop side.
- Minimum-to-never-go-negative is only $36.28, but that assumes perfect execution of the next 404-game tape — not a planning number.

**Daily loss cap (manual-review trigger):** $50.
- Worst single night on this dataset: $-118.11.
- 5th-percentile nightly P&L: $-40.45.
- 10th-percentile nightly P&L: $-32.99.
- Breaching this cap triggers a manual review before the engine resumes next session.

**Per-game max notional:** $150 (= 2 entries × 100 contracts × $0.75 upper-entry bound). Max-concurrent-positions=4 caps total open exposure at $300, which fits comfortably inside the $900 recommended bankroll (leaves ~$600 as reserve for drawdown and gap-through losses).

**Consecutive losing-night kill switch:** after **3** consecutive losing nights, pause the engine for manual review.
- Longest losing streak (trades): 3.
- Longest drawdown streak (L + S combined): 9.
- A 3-night pause converts tape-equivalent drawdown into a human-verification checkpoint without over-reacting to noise (observed losing-night rates are ~36% in the ratcheted mode).

**Caveats:**
- The 404-game dataset is predominantly regular-season (Feb 20 – Apr 15, 2026). Playoff pace/timeout dynamics may shift the drawdown profile; re-run this analysis after the first ~40 playoff games have been paired.
- Ratchet-scratch exits assume a resting limit at `entry + $0.01` fills cleanly (maker). A live-execution shortfall (e.g. scratch-limit missed, contract drops further) would shift some scratches into $0.40 full stops. Monitor scratch-fill rates in the first Phase 4a paper-trading session.
- The engine hasn't been validated live yet. These numbers are replay-backed, not live-verified.

