# Timeout execution window analysis

_Generated: 2026-04-20T05:09:12.972749+00:00_

Measures whether NBA timeouts create favorable execution windows on Kalshi by comparing volume, spread, price stability, and depth in [T, T+90s] timeout windows against 100 bootstrapped baseline windows per game (live-play periods not overlapping any timeout window).

## 1. Data summary

| Game | PBP plays | Timeouts | Trades | In-game snapshots |
|---|---:|---:|---:|---:|
| HOU@LAL | 479 | 11 | 93,838 | 614 |
| ORL@DET | 476 | 9 | 94,149 | 594 |

## 2. Per-game timeout vs baseline

### HOU@LAL

| Metric | Timeout (90s) | Baseline (90s) | Ratio |
|---|---:|---:|---:|
| Trades per window | 624.09 | 644.82 | 0.97 |
| Contracts per window | 270,861 | 210,453 | 1.29 |
| Mean trade size | 384.7 | 325.0 | 1.18 |
| Mean spread ($) | 0.0100 | 0.0109 | 0.92 |
| Price range ($) | 0.5436 | 0.3934 | 1.38 |
| Price std ($) | 0.2497 | 0.1650 | 1.51 |
| Mid drift ($) | 0.2382 | 0.1508 | 1.58 |
| Mean bid depth (fp) | 313,382 | 93,652 | 3.35 |
| Mean ask depth (fp) | 474,989 | 219,475 | 2.16 |

### ORL@DET

| Metric | Timeout (90s) | Baseline (90s) | Ratio |
|---|---:|---:|---:|
| Trades per window | 1070.89 | 735.70 | 1.46 |
| Contracts per window | 423,249 | 238,382 | 1.78 |
| Mean trade size | 360.8 | 310.5 | 1.16 |
| Mean spread ($) | 0.0102 | 0.0106 | 0.96 |
| Price range ($) | 0.3422 | 0.4029 | 0.85 |
| Price std ($) | 0.1611 | 0.1713 | 0.94 |
| Mid drift ($) | 0.1678 | 0.1549 | 1.08 |
| Mean bid depth (fp) | 261,112 | 158,594 | 1.65 |
| Mean ask depth (fp) | 426,508 | 275,593 | 1.55 |

## 3. Pooled comparison (both games)

### 90-second windows

| Metric | Timeout (90s) | Baseline (90s) | Ratio |
|---|---:|---:|---:|
| Trades per window | 825.15 | 690.26 | 1.20 |
| Contracts per window | 339,436 | 224,418 | 1.51 |
| Mean trade size | 373.9 | 317.7 | 1.18 |
| Mean spread ($) | 0.0101 | 0.0107 | 0.94 |
| Price range ($) | 0.4530 | 0.3982 | 1.14 |
| Price std ($) | 0.2099 | 0.1682 | 1.25 |
| Mid drift ($) | 0.2065 | 0.1529 | 1.35 |
| Mean bid depth (fp) | 289,861 | 126,123 | 2.30 |
| Mean ask depth (fp) | 453,173 | 247,534 | 1.83 |

Tight 60s variant (same baseline for comparison):

### 60-second timeout windows vs 90-second baseline

| Metric | Timeout (90s) | Baseline (90s) | Ratio |
|---|---:|---:|---:|
| Trades per window | 562.90 | 690.26 | 0.82 |
| Contracts per window | 229,660 | 224,418 | 1.02 |
| Mean trade size | 377.5 | 317.7 | 1.19 |
| Mean spread ($) | 0.0101 | 0.0107 | 0.94 |
| Price range ($) | 0.4505 | 0.3982 | 1.13 |
| Price std ($) | 0.2112 | 0.1682 | 1.26 |
| Mid drift ($) | 0.1980 | 0.1529 | 1.30 |
| Mean bid depth (fp) | 270,592 | 126,123 | 2.15 |
| Mean ask depth (fp) | 410,702 | 247,534 | 1.66 |

## 4. Run-context split

Run = one team outscored the other by ≥ 6 points in the 120s before the timeout.

After-run timeouts (pooled): **2**. Other timeouts: **18**.

### After-run timeouts vs baseline

| Metric | Timeout (90s) | Baseline (90s) | Ratio |
|---|---:|---:|---:|
| Trades per window | 1239.00 | 690.26 | 1.79 |
| Contracts per window | 817,903 | 224,418 | 3.64 |
| Mean trade size | 589.0 | 317.7 | 1.85 |
| Mean spread ($) | 0.0100 | 0.0107 | 0.93 |
| Price range ($) | 0.3300 | 0.3982 | 0.83 |
| Price std ($) | 0.1531 | 0.1682 | 0.91 |
| Mid drift ($) | 0.0100 | 0.1529 | 0.07 |
| Mean bid depth (fp) | 317,918 | 126,123 | 2.52 |
| Mean ask depth (fp) | 537,245 | 247,534 | 2.17 |

### Other timeouts vs baseline

| Metric | Timeout (90s) | Baseline (90s) | Ratio |
|---|---:|---:|---:|
| Trades per window | 779.17 | 690.26 | 1.13 |
| Contracts per window | 286,273 | 224,418 | 1.28 |
| Mean trade size | 350.0 | 317.7 | 1.10 |
| Mean spread ($) | 0.0101 | 0.0107 | 0.94 |
| Price range ($) | 0.4667 | 0.3982 | 1.17 |
| Price std ($) | 0.2162 | 0.1682 | 1.29 |
| Mid drift ($) | 0.2283 | 0.1529 | 1.49 |
| Mean bid depth (fp) | 286,743 | 126,123 | 2.27 |
| Mean ask depth (fp) | 443,831 | 247,534 | 1.79 |

## 5. Verdict

Pooled across 2 games: volume concentrates in timeout windows (1.20× baseline); spread tightens (0.94×); mid-price drift rises (1.35×); top-of-book depth deepens (2.30×). **Thesis partially supported:** most dimensions point toward calmer execution in timeout windows, with at least one inconclusive or reversed signal.

## 6. Implication for Strategy 3 entry rule

Spread tightens modestly during timeouts, so the maker price target is closer to the mid and the fill probability at a given offset is higher. Deeper resting bid size means the queue-position cost for a maker order is higher, but so is the odds of a clean fill without partial execution.

## Appendix — per-timeout detail

| Game | Period | Clock | Type | Run? | Margin (2min) | Trades | Contracts | Mean spread |
|---|---:|---|---|---|---:|---:|---:|---:|
| HOU@LAL | Q1 | 6:11 | Full Timeout | — | 2 | 853 | 587,946 | 0.0100 |
| HOU@LAL | Q1 | 2:52 | Full Timeout | — | 0 | 635 | 124,054 | 0.0100 |
| HOU@LAL | Q2 | 6:22 | Full Timeout | — | 1 | 571 | 193,735 | 0.0100 |
| HOU@LAL | Q2 | 4:35 | Full Timeout | — | 2 | 478 | 144,875 | 0.0100 |
| HOU@LAL | Q3 | 6:09 | Full Timeout | — | 1 | 543 | 121,659 | 0.0100 |
| HOU@LAL | Q3 | 4:02 | Full Timeout | — | 0 | 690 | 230,622 | 0.0100 |
| HOU@LAL | Q3 | 1:08 | Full Timeout | — | 1 | 598 | 167,059 | 0.0100 |
| HOU@LAL | Q4 | 7:57 | Full Timeout | — | 3 | 1126 | 702,970 | 0.0100 |
| HOU@LAL | Q4 | 5:50 | Full Timeout | — | 1 | 892 | 540,756 | 0.0100 |
| HOU@LAL | Q4 | 3:22 | Full Timeout | — | 2 | 394 | 142,471 | 0.0100 |
| HOU@LAL | Q4 | 15.8 | Full Timeout | — | 2 | 85 | 23,323 | 0.0100 |
| ORL@DET | Q1 | 8:27 | Full Timeout | — | 3 | 1110 | 454,428 | 0.0100 |
| ORL@DET | Q1 | 3:06 | Full Timeout | — | 2 | 873 | 250,720 | 0.0100 |
| ORL@DET | Q2 | 6:16 | Full Timeout | — | 2 | 498 | 116,666 | 0.0100 |
| ORL@DET | Q2 | 3:34 | Full Timeout | — | 0 | 429 | 109,929 | 0.0100 |
| ORL@DET | Q3 | 9:35 | Full Timeout | — | 5 | 1357 | 429,044 | 0.0117 |
| ORL@DET | Q3 | 7:45 | Full Timeout | ✓ | 10 | 770 | 308,793 | 0.0100 |
| ORL@DET | Q3 | 3:43 | Full Timeout | ✓ | 7 | 1708 | 1,327,013 | 0.0100 |
| ORL@DET | Q4 | 8:15 | Full Timeout | — | 4 | 1488 | 318,227 | 0.0100 |
| ORL@DET | Q4 | 3:45 | Full Timeout | — | 0 | 1405 | 494,422 | 0.0100 |

