# Strategy 4 — Stop Execution Parameter Sweep
_Generated: 2026-04-22T22:57:36.387453+00:00_
Sweeps the NO-side resting bid level ($0.58–$0.65) and severe-gap fallback threshold ($0.30–$0.38) across 132 S4A stop events from the 404-game Kalshi-confirmed dataset. Finds the (NO_bid, fallback_threshold) pair that maximizes annual EV under realistic execution.

**Interpretation note:** the fallback-fired case exits at the fallback price with taker fees (operational model: engine cancels the stalled resting order when VWAP crosses the fallback and market-sells at approximately that level). The prompt's literal reading had fallback exiting at `stop_vwap`, which makes fallback P&L-inert; this script implements the operational reading so the sweep yields a meaningful fallback axis.

Dataset anchors: 404 games, 311 total entries, 132 stops, non-stop P&L $+4,476.54 (held constant across cells).

## Part 1 — Full grid results
Sorted by annual EV descending. Top 5 highlighted with bold.

| # | NO_bid | YES equiv | Fallback | Maker | Fallback | Unfilled | Avg exit | Stop P&L | Annual EV |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **1** | **$0.58** | **$0.42** | **$0.30** | **127** | **5** | **0** | **$0.415** | **$-2,813.79** | **$+2,252** |
| **2** | **$0.58** | **$0.42** | **$0.32** | **122** | **10** | **0** | **$0.412** | **$-2,859.59** | **$+2,190** |
| **3** | **$0.59** | **$0.41** | **$0.30** | **127** | **5** | **0** | **$0.406** | **$-2,940.79** | **$+2,080** |
| **4** | **$0.58** | **$0.42** | **$0.34** | **109** | **23** | **0** | **$0.406** | **$-2,959.04** | **$+2,055** |
| **5** | **$0.59** | **$0.41** | **$0.32** | **122** | **10** | **0** | **$0.403** | **$-2,981.59** | **$+2,025** |
| 6 | $0.58 | $0.42 | $0.36 | 91 | 41 | 0 | $0.401 | $-3,043.38 | $+1,941 |
| 7 | $0.60 | $0.40 | $0.30 | 127 | 5 | 0 | $0.396 | $-3,067.79 | $+1,908 |
| 8 | $0.59 | $0.41 | $0.34 | 109 | 23 | 0 | $0.398 | $-3,068.04 | $+1,908 |
| 9 | $0.58 | $0.42 | $0.38 | 66 | 66 | 0 | $0.400 | $-3,093.11 | $+1,874 |
| 10 | $0.60 | $0.40 | $0.32 | 122 | 10 | 0 | $0.394 | $-3,103.59 | $+1,860 |
| 11 | $0.59 | $0.41 | $0.36 | 91 | 41 | 0 | $0.394 | $-3,134.38 | $+1,818 |
| 12 | $0.59 | $0.41 | $0.38 | 66 | 66 | 0 | $0.395 | $-3,159.11 | $+1,784 |
| 13 | $0.60 | $0.40 | $0.34 | 109 | 23 | 0 | $0.390 | $-3,177.04 | $+1,760 |
| 14 | $0.61 | $0.39 | $0.30 | 88 | 5 | 39 | $0.388 | $-3,219.34 | $+1,703 |
| 15 | $0.60 | $0.40 | $0.38 | 66 | 66 | 0 | $0.390 | $-3,225.11 | $+1,695 |
| 16 | $0.60 | $0.40 | $0.36 | 91 | 41 | 0 | $0.388 | $-3,225.38 | $+1,695 |
| 17 | $0.61 | $0.39 | $0.32 | 83 | 10 | 39 | $0.386 | $-3,250.19 | $+1,661 |
| 18 | $0.61 | $0.39 | $0.34 | 70 | 23 | 39 | $0.383 | $-3,310.77 | $+1,579 |
| 19 | $0.61 | $0.39 | $0.38 | 27 | 66 | 39 | $0.387 | $-3,316.27 | $+1,572 |
| 20 | $0.62 | $0.38 | $0.30 | 61 | 5 | 66 | $0.383 | $-3,327.84 | $+1,556 |
| 21 | $0.61 | $0.39 | $0.36 | 52 | 41 | 39 | $0.382 | $-3,341.29 | $+1,538 |
| 22 | $0.62 | $0.38 | $0.32 | 56 | 10 | 66 | $0.381 | $-3,353.69 | $+1,521 |
| 23 | $0.63 | $0.37 | $0.30 | 47 | 5 | 80 | $0.379 | $-3,398.19 | $+1,461 |
| 24 | $0.62 | $0.38 | $0.34 | 43 | 23 | 66 | $0.379 | $-3,401.27 | $+1,456 |
| 25 | $0.62 | $0.38 | $0.36 | 25 | 41 | 66 | $0.379 | $-3,413.79 | $+1,440 |
| 26 | $0.63 | $0.37 | $0.32 | 42 | 10 | 80 | $0.377 | $-3,419.09 | $+1,432 |
| 27 | $0.63 | $0.37 | $0.36 | 11 | 41 | 80 | $0.378 | $-3,448.50 | $+1,392 |
| 28 | $0.63 | $0.37 | $0.34 | 29 | 23 | 80 | $0.376 | $-3,453.80 | $+1,385 |
| 29 | $0.64 | $0.36 | $0.30 | 36 | 5 | 91 | $0.375 | $-3,454.35 | $+1,385 |
| 30 | $0.64 | $0.36 | $0.32 | 31 | 10 | 91 | $0.375 | $-3,470.25 | $+1,363 |
| 31 | $0.64 | $0.36 | $0.34 | 18 | 23 | 91 | $0.374 | $-3,491.96 | $+1,334 |
| 32 | $0.65 | $0.35 | $0.30 | 25 | 5 | 102 | $0.373 | $-3,498.86 | $+1,324 |
| 33 | $0.65 | $0.35 | $0.32 | 20 | 10 | 102 | $0.373 | $-3,509.81 | $+1,309 |
| 34 | $0.65 | $0.35 | $0.34 | 7 | 23 | 102 | $0.373 | $-3,518.65 | $+1,297 |

_Baseline Scenario B ($0.60 NO / $0.34 fallback) annual EV: $+1,760._

## Part 2 — Sensitivity heatmap
Annual EV across the (NO_bid × fallback) surface. Blank cells skipped because fallback ≥ YES equivalent.

| NO_bid \ Fallback | $0.30 | $0.32 | $0.34 | $0.36 | $0.38 |
|---|---:|---:|---:|---:|---:|
| $0.58 | $+2,252 ★ | $+2,190 | $+2,055 | $+1,941 | $+1,874 |
| $0.59 | $+2,080 | $+2,025 | $+1,908 | $+1,818 | $+1,784 |
| $0.60 | $+1,908 | $+1,860 | $+1,760 | $+1,695 | $+1,695 |
| $0.61 | $+1,703 | $+1,661 | $+1,579 | $+1,538 | $+1,572 |
| $0.62 | $+1,556 | $+1,521 | $+1,456 | $+1,440 | — |
| $0.63 | $+1,461 | $+1,432 | $+1,385 | $+1,392 | — |
| $0.64 | $+1,385 | $+1,363 | $+1,334 | — | — |
| $0.65 | $+1,324 | $+1,309 | $+1,297 | — | — |

★ = peak cell.

## Part 3a — NO_bid marginal value at fallback=$0.34
Walks NO_bid from $0.58→$0.65 holding fallback fixed. Each step's Δ EV isolates the effect of moving the resting bid by one cent.

| NO_bid | Maker fills | Avg exit | Annual EV | Δ EV vs prev | Marginal note |
|---:|---:|---:|---:|---:|---|
| $0.58 | 109 | $0.406 | $+2,055 | — |  |
| $0.59 | 109 | $0.398 | $+1,908 | $-148 | slippage exceeds marginal fill benefit |
| $0.60 | 109 | $0.390 | $+1,760 | $-148 | slippage exceeds marginal fill benefit |
| $0.61 | 70 | $0.383 | $+1,579 | $-181 | slippage exceeds marginal fill benefit |
| $0.62 | 43 | $0.379 | $+1,456 | $-123 | slippage exceeds marginal fill benefit |
| $0.63 | 29 | $0.376 | $+1,385 | $-71 | slippage exceeds marginal fill benefit |
| $0.64 | 18 | $0.374 | $+1,334 | $-52 | slippage exceeds marginal fill benefit |
| $0.65 | 7 | $0.373 | $+1,297 | $-36 | slippage exceeds marginal fill benefit |

## Part 3b — Fallback marginal value at optimal NO_bid
Walks fallback from $0.30→$0.38 holding NO_bid fixed at the grid-optimal **$0.58** (yes_equiv $0.42).

| Fallback | Taker fallbacks | Taker unfilled | Annual EV | Δ EV vs prev |
|---:|---:|---:|---:|---:|
| $0.30 | 5 | 0 | $+2,252 | — |
| $0.32 | 10 | 0 | $+2,190 | $-62 |
| $0.34 | 23 | 0 | $+2,055 | $-135 |
| $0.36 | 41 | 0 | $+1,941 | $-114 |
| $0.38 | 66 | 0 | $+1,874 | $-67 |

## Part 4 — Per-stop detail at top-EV configuration
Optimal cell: **NO_bid $0.58 / fallback $0.30** → annual EV $+2,252. All 132 stops, sorted by P&L ascending (worst first).

| # | Game | \|Spread\| | Entry | stop_vwap | Outcome | Exit price | P&L |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | BKN @ DET | 14.5 | $0.746 | $0.261 | taker_fallback | $0.300 | $-46.43 |
| 2 | UTA @ PHI | 7.5 | $0.717 | $0.287 | taker_fallback | $0.300 | $-43.56 |
| 3 | DAL @ CLE | 16.5 | $0.749 | $0.332 | maker_fill | $0.420 | $-33.68 |
| 4 | LAL @ PHX | 6.0 | $0.749 | $0.381 | maker_fill | $0.420 | $-33.64 |
| 5 | MIL @ CHI | 2.5 | $0.746 | $0.395 | maker_fill | $0.420 | $-33.41 |
| 6 | BKN @ GSW | 11.5 | $0.745 | $0.371 | maker_fill | $0.420 | $-33.23 |
| 7 | PHX @ BOS | 8.5 | $0.743 | $0.377 | maker_fill | $0.420 | $-33.02 |
| 8 | ORL @ BOS | 13.5 | $0.743 | $0.334 | maker_fill | $0.420 | $-33.02 |
| 9 | ORL @ LAL | 5.0 | $0.740 | $0.366 | maker_fill | $0.420 | $-32.82 |
| 10 | CLE @ NOP | 4.5 | $0.604 | $0.297 | taker_fallback | $0.300 | $-32.28 |
| 11 | HOU @ MIN | 1.5 | $0.734 | $0.330 | maker_fill | $0.420 | $-32.20 |
| 12 | NOP @ SAC | 5.5 | $0.734 | $0.305 | maker_fill | $0.420 | $-32.14 |
| 13 | DET @ OKC | 12.5 | $0.733 | $0.375 | maker_fill | $0.420 | $-32.08 |
| 14 | POR @ PHI | 8.5 | $0.731 | $0.374 | maker_fill | $0.420 | $-31.88 |
| 15 | DEN @ UTA | 11.5 | $0.729 | $0.382 | maker_fill | $0.420 | $-31.70 |
| 16 | GSW @ LAC | 5.5 | $0.725 | $0.354 | maker_fill | $0.420 | $-31.31 |
| 17 | LAC @ IND | 8.5 | $0.725 | $0.374 | maker_fill | $0.420 | $-31.25 |
| 18 | DEN @ SAS | 5.5 | $0.724 | $0.360 | maker_fill | $0.420 | $-31.22 |
| 19 | MIL @ PHX | 11.5 | $0.722 | $0.385 | maker_fill | $0.420 | $-30.98 |
| 20 | IND @ ORL | 13.5 | $0.720 | $0.396 | maker_fill | $0.420 | $-30.80 |
| 21 | UTA @ DEN | 18.5 | $0.718 | $0.375 | maker_fill | $0.420 | $-30.63 |
| 22 | HOU @ PHX | 1.5 | $0.718 | $0.351 | maker_fill | $0.420 | $-30.59 |
| 23 | LAC @ MEM | 5.5 | $0.718 | $0.390 | maker_fill | $0.420 | $-30.56 |
| 24 | WAS @ BKN | 3.5 | $0.712 | $0.398 | maker_fill | $0.420 | $-29.98 |
| 25 | LAL @ ORL | 3.5 | $0.710 | $0.318 | maker_fill | $0.420 | $-29.77 |
| 26 | DAL @ ORL | 9.5 | $0.709 | $0.369 | maker_fill | $0.420 | $-29.69 |
| 27 | MIN @ BOS | 10.5 | $0.709 | $0.371 | maker_fill | $0.420 | $-29.68 |
| 28 | GSW @ HOU | 8.5 | $0.708 | $0.354 | maker_fill | $0.420 | $-29.56 |
| 29 | CLE @ MIL | 3.5 | $0.706 | $0.336 | maker_fill | $0.420 | $-29.44 |
| 30 | GSW @ SAC | 10.5 | $0.696 | $0.358 | maker_fill | $0.420 | $-28.41 |
| 31 | LAC @ SAS | 7.5 | $0.694 | $0.342 | maker_fill | $0.420 | $-28.21 |
| 32 | SAC @ LAC | 13.5 | $0.690 | $0.358 | maker_fill | $0.420 | $-27.78 |
| 33 | DEN @ MEM | 13.5 | $0.689 | $0.386 | maker_fill | $0.420 | $-27.74 |
| 34 | HOU @ CHI | 8.5 | $0.685 | $0.380 | maker_fill | $0.420 | $-27.31 |
| 35 | PHI @ CHA | 6.5 | $0.685 | $0.396 | maker_fill | $0.420 | $-27.30 |
| 36 | PHI @ MIN | 9.5 | $0.684 | $0.378 | maker_fill | $0.420 | $-27.17 |
| 37 | ORL @ MIN | 6.5 | $0.683 | $0.395 | maker_fill | $0.420 | $-27.07 |
| 38 | ATL @ MIL | 1.0 | $0.680 | $0.390 | maker_fill | $0.420 | $-26.83 |
| 39 | SAC @ TOR | 13.5 | $0.679 | $0.396 | maker_fill | $0.420 | $-26.68 |
| 40 | NOP @ LAL | 8.5 | $0.673 | $0.321 | maker_fill | $0.420 | $-26.16 |
| 41 | LAC @ MEM | 5.5 | $0.670 | $0.377 | maker_fill | $0.420 | $-25.77 |
| 42 | WAS @ BKN | 3.5 | $0.669 | $0.339 | maker_fill | $0.420 | $-25.71 |
| 43 | MIN @ HOU | 10.5 | $0.668 | $0.396 | maker_fill | $0.420 | $-25.65 |
| 44 | MIA @ CHA | 7.5 | $0.667 | $0.360 | maker_fill | $0.420 | $-25.56 |
| 45 | NYK @ ATL | 1.5 | $0.661 | $0.392 | maker_fill | $0.420 | $-24.97 |
| 46 | HOU @ CHI | 8.5 | $0.530 | $0.272 | taker_fallback | $0.300 | $-24.88 |
| 47 | NYK @ ATL | 1.5 | $0.660 | $0.336 | maker_fill | $0.420 | $-24.87 |
| 48 | CHI @ GSW | 6.5 | $0.660 | $0.383 | maker_fill | $0.420 | $-24.84 |
| 49 | CHA @ POR | 2.5 | $0.656 | $0.370 | maker_fill | $0.420 | $-24.46 |
| 50 | DEN @ OKC | 6.5 | $0.655 | $0.379 | maker_fill | $0.420 | $-24.34 |
| 51 | MIA @ CHA | 5.5 | $0.653 | $0.355 | maker_fill | $0.420 | $-24.17 |
| 52 | PHX @ SAS | 9.5 | $0.652 | $0.326 | maker_fill | $0.420 | $-24.05 |
| 53 | MIN @ DEN | 3.0 | $0.652 | $0.388 | maker_fill | $0.420 | $-24.03 |
| 54 | HOU @ NYK | 4.0 | $0.652 | $0.399 | maker_fill | $0.420 | $-23.99 |
| 55 | DAL @ POR | 10.5 | $0.652 | $0.395 | maker_fill | $0.420 | $-23.98 |
| 56 | SAS @ TOR | 6.0 | $0.651 | $0.387 | maker_fill | $0.420 | $-23.90 |
| 57 | PHI @ MIA | 2.5 | $0.518 | $0.195 | taker_fallback | $0.300 | $-23.76 |
| 58 | GSW @ UTA | 5.5 | $0.647 | $0.384 | maker_fill | $0.420 | $-23.53 |
| 59 | LAL @ HOU | 2.5 | $0.639 | $0.385 | maker_fill | $0.420 | $-22.70 |
| 60 | DAL @ POR | 10.5 | $0.636 | $0.396 | maker_fill | $0.420 | $-22.48 |
| 61 | NOP @ HOU | 6.5 | $0.631 | $0.393 | maker_fill | $0.420 | $-21.94 |
| 62 | CHI @ PHX | 10.5 | $0.631 | $0.320 | maker_fill | $0.420 | $-21.91 |
| 63 | ORL @ NOP | 4.5 | $0.628 | $0.355 | maker_fill | $0.420 | $-21.68 |
| 64 | CHI @ MEM | 3.5 | $0.628 | $0.307 | maker_fill | $0.420 | $-21.67 |
| 65 | MIA @ IND | 9.5 | $0.626 | $0.397 | maker_fill | $0.420 | $-21.43 |
| 66 | PHX @ OKC | 5.5 | $0.621 | $0.350 | maker_fill | $0.420 | $-20.98 |
| 67 | HOU @ CHA | 4.5 | $0.618 | $0.383 | maker_fill | $0.420 | $-20.62 |
| 68 | MIA @ HOU | 1.5 | $0.617 | $0.400 | maker_fill | $0.420 | $-20.60 |
| 69 | BOS @ NYK | 4.5 | $0.616 | $0.360 | maker_fill | $0.420 | $-20.45 |
| 70 | CLE @ DET | 8.0 | $0.615 | $0.351 | maker_fill | $0.420 | $-20.33 |
| 71 | DEN @ LAC | 4.5 | $0.613 | $0.329 | maker_fill | $0.420 | $-20.11 |
| 72 | POR @ DEN | 8.5 | $0.612 | $0.357 | maker_fill | $0.420 | $-20.00 |
| 73 | LAC @ NOP | 1.5 | $0.609 | $0.384 | maker_fill | $0.420 | $-19.79 |
| 74 | CHA @ PHX | 4.5 | $0.604 | $0.400 | maker_fill | $0.420 | $-19.28 |
| 75 | PHI @ ATL | 6.5 | $0.602 | $0.383 | maker_fill | $0.420 | $-19.08 |
| 76 | LAC @ SAS | 7.5 | $0.601 | $0.378 | maker_fill | $0.420 | $-19.00 |
| 77 | PHI @ NOP | 3.5 | $0.597 | $0.396 | maker_fill | $0.420 | $-18.57 |
| 78 | CHI @ MEM | 3.5 | $0.597 | $0.379 | maker_fill | $0.420 | $-18.55 |
| 79 | CHI @ GSW | 6.5 | $0.591 | $0.349 | maker_fill | $0.420 | $-17.97 |
| 80 | OKC @ TOR | 2.0 | $0.590 | $0.400 | maker_fill | $0.420 | $-17.89 |
| 81 | MIL @ BKN | 2.5 | $0.586 | $0.389 | maker_fill | $0.420 | $-17.45 |
| 82 | MIA @ MIL | 6.0 | $0.583 | $0.396 | maker_fill | $0.420 | $-17.13 |
| 83 | CLE @ MIL | 3.5 | $0.580 | $0.393 | maker_fill | $0.420 | $-16.83 |
| 84 | IND @ SAC | 3.5 | $0.577 | $0.386 | maker_fill | $0.420 | $-16.58 |
| 85 | LAL @ MIA | 3.5 | $0.577 | $0.347 | maker_fill | $0.420 | $-16.54 |
| 86 | MIN @ PHI | 2.5 | $0.573 | $0.384 | maker_fill | $0.420 | $-16.20 |
| 87 | MEM @ BKN | 1.5 | $0.572 | $0.400 | maker_fill | $0.420 | $-16.10 |
| 88 | TOR @ DEN | 6.5 | $0.572 | $0.398 | maker_fill | $0.420 | $-16.09 |
| 89 | LAC @ IND | 8.5 | $0.572 | $0.368 | maker_fill | $0.420 | $-16.02 |
| 90 | PHX @ TOR | 4.5 | $0.571 | $0.397 | maker_fill | $0.420 | $-15.95 |
| 91 | OKC @ BOS | 2.5 | $0.570 | $0.389 | maker_fill | $0.420 | $-15.86 |
| 92 | POR @ MIN | 2.5 | $0.569 | $0.341 | maker_fill | $0.420 | $-15.79 |
| 93 | SAC @ DAL | 8.0 | $0.567 | $0.398 | maker_fill | $0.420 | $-15.59 |
| 94 | MIA @ HOU | 1.5 | $0.564 | $0.383 | maker_fill | $0.420 | $-15.30 |
| 95 | ORL @ LAL | 5.0 | $0.563 | $0.343 | maker_fill | $0.420 | $-15.20 |
| 96 | MIN @ LAL | 2.5 | $0.563 | $0.397 | maker_fill | $0.420 | $-15.17 |
| 97 | SAS @ DET | 1.0 | $0.559 | $0.394 | maker_fill | $0.420 | $-14.81 |
| 98 | CHI @ SAC | 2.5 | $0.559 | $0.394 | maker_fill | $0.420 | $-14.80 |
| 99 | DEN @ OKC | 8.0 | $0.557 | $0.385 | maker_fill | $0.420 | $-14.54 |
| 100 | PHX @ MIL | 1.5 | $0.556 | $0.399 | maker_fill | $0.420 | $-14.49 |
| 101 | ATL @ DET | 2.5 | $0.554 | $0.361 | maker_fill | $0.420 | $-14.28 |
| 102 | LAL @ HOU | 2.5 | $0.554 | $0.395 | maker_fill | $0.420 | $-14.27 |
| 103 | POR @ PHI | 8.5 | $0.549 | $0.389 | maker_fill | $0.420 | $-13.81 |
| 104 | IND @ ORL | 13.5 | $0.548 | $0.343 | maker_fill | $0.420 | $-13.70 |
| 105 | LAC @ DAL | 7.5 | $0.546 | $0.383 | maker_fill | $0.420 | $-13.46 |
| 106 | DET @ CLE | 2.5 | $0.544 | $0.346 | maker_fill | $0.420 | $-13.26 |
| 107 | LAL @ HOU | 2.5 | $0.544 | $0.390 | maker_fill | $0.420 | $-13.26 |
| 108 | TOR @ PHX | 2.5 | $0.534 | $0.396 | maker_fill | $0.420 | $-12.25 |
| 109 | GSW @ HOU | 8.5 | $0.532 | $0.321 | maker_fill | $0.420 | $-12.10 |
| 110 | ATL @ CLE | 1.5 | $0.532 | $0.366 | maker_fill | $0.420 | $-12.07 |
| 111 | POR @ PHX | 3.5 | $0.531 | $0.391 | maker_fill | $0.420 | $-11.93 |
| 112 | GSW @ DAL | 1.5 | $0.530 | $0.382 | maker_fill | $0.420 | $-11.83 |
| 113 | IND @ CHI | 4.5 | $0.529 | $0.396 | maker_fill | $0.420 | $-11.81 |
| 114 | UTA @ WAS | 2.5 | $0.529 | $0.397 | maker_fill | $0.420 | $-11.75 |
| 115 | CHA @ BOS | 4.5 | $0.528 | $0.399 | maker_fill | $0.420 | $-11.71 |
| 116 | MIL @ NOP | 4.0 | $0.528 | $0.386 | maker_fill | $0.420 | $-11.65 |
| 117 | DEN @ OKC | 8.0 | $0.525 | $0.308 | maker_fill | $0.420 | $-11.37 |
| 118 | POR @ HOU | 6.5 | $0.523 | $0.351 | maker_fill | $0.420 | $-11.18 |
| 119 | DET @ TOR | 3.5 | $0.523 | $0.382 | maker_fill | $0.420 | $-11.14 |
| 120 | BOS @ DEN | 3.5 | $0.522 | $0.388 | maker_fill | $0.420 | $-11.03 |
| 121 | TOR @ NOP | 2.5 | $0.519 | $0.331 | maker_fill | $0.420 | $-10.78 |
| 122 | MIL @ PHX | 11.5 | $0.519 | $0.316 | maker_fill | $0.420 | $-10.73 |
| 123 | PHX @ MIN | 3.5 | $0.516 | $0.398 | maker_fill | $0.420 | $-10.51 |
| 124 | ORL @ LAC | 4.0 | $0.516 | $0.397 | maker_fill | $0.420 | $-10.43 |
| 125 | MEM @ PHI | 2.5 | $0.512 | $0.394 | maker_fill | $0.420 | $-10.11 |
| 126 | PHI @ MIA | 2.5 | $0.511 | $0.376 | maker_fill | $0.420 | $-9.96 |
| 127 | HOU @ ORL | 2.5 | $0.508 | $0.395 | maker_fill | $0.420 | $-9.71 |
| 128 | MIL @ UTA | 5.5 | $0.508 | $0.370 | maker_fill | $0.420 | $-9.66 |
| 129 | DET @ CHA | 5.5 | $0.507 | $0.361 | maker_fill | $0.420 | $-9.54 |
| 130 | LAL @ HOU | 2.5 | $0.504 | $0.384 | maker_fill | $0.420 | $-9.28 |
| 131 | DET @ NYK | 4.0 | $0.503 | $0.331 | maker_fill | $0.420 | $-9.13 |
| 132 | ORL @ PHX | 3.5 | $0.501 | $0.362 | maker_fill | $0.420 | $-8.94 |

## Part 5 — Robustness check (bootstrap)
10,000 resamples (with replacement) of the 132 stops. Non-stop P&L held constant.

| Cell (NO_bid / fallback) | Bootstrap mean | 95% CI | P(EV > 0) | P(beats baseline) |
|---|---:|---|---:|---:|
| $0.58 / $0.30 | $+2,254 | ($+2,009, $+2,495) | 100.0% | 100.0% |
| $0.58 / $0.32 | $+2,192 | ($+1,944, $+2,438) | 100.0% | 100.0% |
| $0.59 / $0.30 | $+2,082 | ($+1,840, $+2,321) | 100.0% | 100.0% |

_Baseline Scenario B reference: bootstrap mean $+1,762, 95% CI ($+1,508, $+2,011), P(EV>0) = 100.0%._

## Recommendation

**Optimal cell:** NO_bid $0.58 / fallback $0.30 (YES equivalent $0.42).

**Annual EV:** $+2,252 vs baseline Scenario B $+1,760 (Δ $+492).

**Bootstrap robustness:** P(optimal beats baseline) = 100.0% across 10,000 resamples; 95% CI ($+2,009, $+2,495).

**Verdict:** the optimal cell meaningfully beats the current Scenario B default and the bootstrap agrees. Recommend updating STRATEGY4_SPEC.md §4 and PHASE4A_DESIGN.md Decision 6 to the optimal values. Paper-test in Phase 4b to confirm against live fills before committing real capital to the change.

**Operational framing:** the NO_bid axis trades earlier-but-shallower maker fills (higher NO_bid / lower YES equivalent) against bigger-but-later exits (lower NO_bid). The fallback axis limits downside on severe gaps by cutting losses when the VWAP crashes past the resting order. Under the operational interpretation, fallback is a risk-management knob whose benefit shows up as lifted stop P&L on the worst-outcome subset of stops.

