# Strategy 3 — Failed Entry & Worst-Case Analysis

_Generated: 2026-04-21T05:05:19.233649+00:00_

Complement to the graduation evaluation. Every entry event at ≤ $0.40 is tracked through to its outcome: completed round-trip at ≥ $0.50, held to win, held to loss, or held to indeterminate (timeseries ended mid-price). Produces the true expected value per entry.

## §1 — Sample summary

- Games analyzed: **165** competitive (|spread| ≤ 6)
- Entry threshold: **$0.40** | Exit threshold: **$0.50**
- Total entries detected: **422** (158 fav-side, 264 dog-side)
  - Completed round-trips: 257 (60.9%)
  - Held to win: 0 (0.0%)
  - Held to loss: 165 (39.1%)
  - Held indeterminate (timeseries ended mid-price): 0 (0.0%)

## §2 — Success/failure breakdown

| Outcome | Count | % | Mean P&L | Median P&L |
|---|---:|---:|---:|---:|
| Completed RT | 257 | 60.9% | $+15.49 | $+13.71 |
| Held to win | 0 | 0.0% | — | — |
| Held to loss | 165 | 39.1% | $-35.82 | $-37.97 |
| Held indeterminate | 0 | 0.0% | — | — |
| **All entries** | **422** | 100.0% | **$-4.57** | **$+11.18** |

**True expected value per entry: $-4.57** (accounts for all outcomes, weighted by observed frequency).

## §3 — True expected value per entry

If you enter at ≤ entry_threshold in a competitive game:

- 60.9% chance of completing a round-trip → mean net $+15.49
- 39.1% chance of holding to a loss → mean net $-35.82

**Blended EV per entry: $-4.57**

Entries per competitive game (observed): **2.56**

At 2.56 entries/game × 549 competitive games per season: **~$-6,419 estimated annual EV** (maker-maker, 100 contracts per entry).

## §4 — Failed-entry deep dive

| Metric | Held to loss | Held to win |
|---|---|---|
| Count | 165 | 0 |
| Mean entry price | $0.3542 | — |
| Mean max favorable excursion | $0.3914 | — |
| Came close (MFE ≥ exit − $0.02) | 7.9% | — |
| Mean hold time to resolution | 25m 23s | — |
| Mean entry period | Q2.5 | — |

## §5 — Failed entries by entry period

| Entry period | Total entries | Failed (loss) | Fail rate |
|---|---:|---:|---:|
| Q1 | 172 | 59 | 34.3% |
| Q2 | 67 | 27 | 40.3% |
| Q3 | 66 | 27 | 40.9% |
| Q4 | 104 | 46 | 44.2% |
| OT | 13 | 6 | 46.2% |

## §6 — Failed entries by spread bucket

| |Spread| bucket | Total entries | Failed (loss) | Fail rate |
|---|---:|---:|---:|
| 1.0 - 2.0 | 90 | 34 | 37.8% |
| 2.5 - 3.5 | 195 | 69 | 35.4% |
| 4.0 - 5.0 | 65 | 28 | 43.1% |
| 5.5 - 6.0 | 72 | 34 | 47.2% |

## §7 — Max adverse excursion distribution (all entries)

| MAE (% of entry price) | Count | % |
|---|---:|---:|
| 0% (never went lower) | 41 | 9.7% |
| 0-10% | 60 | 14.2% |
| 10-25% | 57 | 13.5% |
| 25-50% | 47 | 11.1% |
| 50-75% | 30 | 7.1% |
| 75-100% | 187 | 44.3% |

## §8 — Worst-case scenarios

### 10 worst individual entries

| Game | Side | Entry | Q | MAE | Final | Net P&L |
|---|---|---:|---:|---:|---:|---:|
| KXNBAGAME-26MAR09MEMBKN | fav | $0.3997 | 2 | $0.0100 | $0.0100 | $-40.39 |
| KXNBAGAME-26MAR20ATLHOU | dog | $0.3997 | 1 | $0.0100 | $0.0100 | $-40.39 |
| KXNBAGAME-26APR01INDCHI | fav | $0.3996 | 2 | $0.0100 | $0.0100 | $-40.38 |
| KXNBAGAME-26FEB24OKCTOR | fav | $0.3996 | 2 | $0.0100 | $0.0100 | $-40.38 |
| KXNBAGAME-26FEB24DALBKN | dog | $0.3996 | 1 | $0.0100 | $0.0100 | $-40.38 |
| KXNBAGAME-26MAR19PHISAC | dog | $0.3995 | 1 | $0.0100 | $0.0100 | $-40.37 |
| KXNBAGAME-26APR05CHAMIN | dog | $0.3995 | 3 | $0.0100 | $0.0100 | $-40.37 |
| KXNBAGAME-26FEB20MILNOP | fav | $0.3994 | 3 | $0.0100 | $0.0100 | $-40.36 |
| KXNBAGAME-26APR06DETORL | fav | $0.3993 | 1 | $0.0100 | $0.0100 | $-40.35 |
| KXNBAGAME-26MAR25WASUTA | fav | $0.3989 | 1 | $0.0100 | $0.0100 | $-40.31 |

### 5 worst games (summed P&L across all entries)

| Game | |Spread| | Entries | Completed | Failed | Game P&L |
|---|---:|---:|---:|---:|---:|
| KXNBAGAME-26MAR20ATLHOU | 3.5 | 1 | 0 | 1 | $-40.39 |
| KXNBAGAME-26FEB24DALBKN | 1.5 | 1 | 0 | 1 | $-40.38 |
| KXNBAGAME-26MAR19PHISAC | 2.5 | 1 | 0 | 1 | $-40.37 |
| KXNBAGAME-26APR06DETORL | 2.5 | 1 | 0 | 1 | $-40.35 |
| KXNBAGAME-26MAR25WASUTA | 4.5 | 1 | 0 | 1 | $-40.31 |

## §9 — Risk-adjusted summary

**Sharpe-like metric**
- Mean P&L per entry: $-4.57
- Std P&L per entry: $25.88
- Ratio (mean / std): -0.177

**Win / loss**
- Win rate (net > 0): 60.9%
- Loss rate (net < 0): 39.1%
- Mean winning entry: $+15.49
- Mean losing entry: $-35.82
- Win/loss magnitude ratio: 0.43×

**Kelly criterion (approximate, for educational reference)**
- f* = (p·b − q) / b = (0.609·0.432 − 0.391) / 0.432 = **-0.295**
- At $1,000 bankroll: $-295.17 per entry
- At ~$0.40 entry price, that's -738 contracts per entry — within the 100-contract default.

