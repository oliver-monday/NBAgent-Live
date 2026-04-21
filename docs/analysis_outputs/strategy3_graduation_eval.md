# Strategy 3 — Formal Graduation Evaluation

_Generated: 2026-04-21T04:24:47.638089+00:00_

Round-trip detection on 168-game paired Kalshi trade-price timeseries. Evaluates graduation criteria from `docs/KILL_CRITERIA_draft.md` on competitive games only (|spread| ≤ 6).

## §1 — Sample summary

- Games analyzed: **165** (of 168 total timeseries files)
- Competitive games (|spread| ≤ 6): **165**
- Date range: 2026-02-20 to 2026-04-15

## §2 — Round-trip frequency by grid

| Grid | Games w/ ≥1 RT | RT frequency | Total RTs | RTs/game (mean) |
|---|---:|---:|---:|---:|
| (0.35, 0.45) | 104 / 165 | 63.0% | 231 | 1.40 |
| (0.35, 0.50) | 94 / 165 | 57.0% | 184 | 1.12 |
| (0.40, 0.50) | 105 / 165 | 63.6% | 263 | 1.59 |
| (0.40, 0.55) | 92 / 165 | 55.8% | 204 | 1.24 |
| (0.45, 0.55) | 102 / 165 | 61.8% | 292 | 1.77 |

## §3 — Round-trip economics (primary grid 0.40, 0.50)

| Metric | Value |
|---|---|
| Total round-trips | 263 |
| Median gross profit | $14.59 |
| Median net profit (maker-maker) | $13.74 |
| Mean net profit (maker-maker) | $15.98 |
| Median hold time | 6m 31s |
| Mean hold time | 10m 1s |
| Min hold time | 0m 1s |
| Max hold time | 45m 48s |
| Profitable trips (net > 0) | 100.0% |

### Distribution of net profit

| Net profit bucket | Count | % |
|---|---:|---:|
| < $0 | 0 | 0.0% |
| $0 - $5 | 0 | 0.0% |
| $5 - $10 | 8 | 3.0% |
| $10 - $15 | 158 | 60.1% |
| $15 - $20 | 59 | 22.4% |
| > $20 | 38 | 14.4% |

## §4 — Hold time distribution (primary grid)

| Hold time bucket | Count | % |
|---|---:|---:|
| < 1 min | 30 | 11.4% |
| 1-5 min | 90 | 34.2% |
| 5-15 min | 73 | 27.8% |
| 15-30 min | 54 | 20.5% |
| 30-60 min | 16 | 6.1% |
| > 60 min | 0 | 0.0% |

## §5 — Entry period distribution (primary grid)

| Entry period | RTs | % | Mean net |
|---|---:|---:|---:|
| Q1 | 113 | 43.0% | $13.68 |
| Q2 | 40 | 15.2% | $13.09 |
| Q3 | 39 | 14.8% | $13.75 |
| Q4 | 63 | 24.0% | $21.92 |
| OT | 8 | 3.0% | $26.92 |

## §6 — Exit timing analysis

Tests the convergence-zone exit preference: do round-trips that complete in the 1–3 min window have better outcomes?

| Exit time remaining | RTs | % | Mean net |
|---|---:|---:|---:|
| > 12 min | 159 | 60.5% | $13.23 |
| 6-12 min | 36 | 13.7% | $14.34 |
| 3-6 min | 29 | 11.0% | $17.74 |
| 1-3 min | 17 | 6.5% | $20.70 |
| 0-1 min | 22 | 8.4% | $32.51 |

## §7 — Bilateral entry frequency

- Games where both sides dipped ≤ $0.40: **84 / 165 (50.9%)**
- Games where both sides dipped ≤ $0.35: **68 / 165 (41.2%)**

**When both sides dip ≤ $0.40:**

- Mean time between dips: 23m 35s of game-clock elapsed


**Guaranteed bilateral profit (if both fill at $0.40, both held to resolution):**

- Payout: $100.00 (one side resolves YES)
- Total cost: $80.00 (2 × $0.40 × 100)
- Gross: $20.00
- Fees (2 maker entry legs; losing side self-settles at $0, winner at $1): $0.86
- **Net: $19.14**

## §8 — Formal graduation scorecard

**Sample:** 165 competitive games (|spread| ≤ 6)

### Graduates if ALL pass:

| # | Criterion | Threshold | Measured | Status |
|---|---|---|---|---|
| 1 | RT frequency at (0.40, 0.50) | ≥ 15% | 63.6% (105/165) | ✓ |
| 2 | Median net per trip (maker) | ≥ $5 | $13.74 | ✓ |
| 3 | Realized spread (median) | ≤ $0.02 | $0.01* | ✓ |
| 4 | Depth (% ≥ 50k at entry) | ≥ 50% | 55%* | ✓ |
| 5 | Hold time (median) | ≥ 3 min | 6m 31s | ✓ |
| 6 | All RTs complete in < 90s | No | 17.9% < 90s | ✓ |

*Criteria 3 and 4 are from live orderbook data (n=5 logged games). Not measurable from historical trade data. Values carried forward from prior measurement.*

### Kill triggers (fail if ANY):

| # | Criterion | Threshold | Measured | Status |
|---|---|---|---|---|
| K1 | RT frequency | < 5% | 63.6% | safe |
| K2 | Median net per trip | < $0 | $13.74 | safe |
| K3 | Realized spread | ≥ $0.03 | $0.01* | safe |
| K4 | All RTs < 90s | Yes | 17.9% < 90s | safe |

### Verdict: **GRADUATED**

All measurable criteria pass. Phase 4a (signal alerts for manual paper-trading) is unlocked per `docs/KILL_CRITERIA_draft.md`.

