# Scoring-run trajectory analysis

_Generated: 2026-04-20T05:35:34.710116+00:00_

Tests the causal chain Strategy 3 depends on: scoring run → price move → timeout → book settles → momentum reverses → price reverts. Part A characterizes per-basket price impact. Part B measures post-timeout trajectories split by run-stopping vs routine. Part C sweeps run-detection parameters. Part D synthesizes a proto-rule or null result.

## Data summary

| Game | Plays | Scoring plays | Impact coverage | Timeouts | Run-stopping |
|---|---:|---:|---:|---:|---:|
| HOU@LAL | 479 | 109 | 108 | 11 | 1 |
| ORL@DET | 476 | 118 | 118 | 9 | 4 |

## Part A — Score-to-price impact

#### HOU@LAL
### Table 1 — Price impact by play type

| Play value | n | Mean immediate impact ($) | Mean full impact ($) | Median reaction lag (s) |
|---|---:|---:|---:|---:|
| 2-pointer | 53 | +0.0111 | +0.0134 | 4.0 |
| 3-pointer | 21 | +0.0333 | +0.0210 | 2.7 |
| Free throw | 34 | +0.0071 | +0.0097 | 3.8 |

#### ORL@DET
### Table 1 — Price impact by play type

| Play value | n | Mean immediate impact ($) | Mean full impact ($) | Median reaction lag (s) |
|---|---:|---:|---:|---:|
| 2-pointer | 55 | +0.0220 | +0.0333 | 4.6 |
| 3-pointer | 20 | +0.0470 | +0.0495 | 4.2 |
| Free throw | 43 | +0.0056 | +0.0019 | 24.8 |

#### Pooled (both games)
### Table 1 — Price impact by play type

| Play value | n | Mean immediate impact ($) | Mean full impact ($) | Median reaction lag (s) |
|---|---:|---:|---:|---:|
| 2-pointer | 108 | +0.0167 | +0.0235 | 4.1 |
| 3-pointer | 41 | +0.0400 | +0.0349 | 3.5 |
| Free throw | 77 | +0.0062 | +0.0053 | 19.9 |

### Table 2 — Price impact by scoring-team YES price

| Scoring team YES price | n | Mean immediate impact ($) |
|---|---:|---:|
| ≤ 0.30 | 42 | +0.0145 |
| (0.30, 0.40] | 38 | +0.0174 |
| (0.40, 0.50] | 42 | +0.0240 |
| (0.50, 0.60] | 29 | +0.0190 |
| (0.60, 0.70] | 41 | +0.0161 |
| > 0.70 | 34 | +0.0126 |

## Part B — Post-timeout trajectories

### Table 3 — Run-stopping timeouts (n=5)

| Metric | Mean | Median | % positive | n |
|---|---:|---:|---:|---:|
| Recovery @ 1 min | +0.0200 | +0.0000 | 40% | 5 |
| Recovery @ 2 min | +0.0180 | -0.0100 | 20% | 5 |
| Recovery @ 3 min | +0.0360 | -0.0100 | 40% | 5 |
| Recovery @ 5 min | +0.0300 | -0.0100 | 40% | 5 |
| Max recovery | +0.0900 | +0.0900 | 80% | — |
| Time to max (s, median) | — | 186 | — | — |

### Table 4 — Routine timeouts (n=15)

| Metric | Mean | Median | % positive | n |
|---|---:|---:|---:|---:|
| Recovery @ 1 min | — | — | — | 0 |
| Recovery @ 2 min | — | — | — | 0 |
| Recovery @ 3 min | — | — | — | 0 |
| Recovery @ 5 min | — | — | — | 0 |

### Table 5 — Run-stopping vs routine

| Metric | Run-stopping | Routine | Delta |
|---|---:|---:|---:|
| Mean recovery @ 3 min | — | — | — |
| % positive @ 3 min | — | — | — |
| Mean max recovery | — | — | — |

### Per-timeout detail

| Game | Period | Clock | Run? | Margin | Trailing | Price@TO | Rec 3min | Rec 5min | Max rec |
|---|---:|---|---|---:|---|---:|---:|---:|---:|
| HOU@LAL | Q1 | 6:11 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q1 | 2:52 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q2 | 6:22 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q2 | 4:35 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q3 | 6:09 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q3 | 4:02 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q3 | 1:08 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q4 | 7:57 | ✓ | 8 | HOU | 0.0500 | -0.0100 | -0.0100 | +0.0000 |
| HOU@LAL | Q4 | 5:50 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q4 | 3:22 | — | 0 | — | — | — | — | — |
| HOU@LAL | Q4 | 15.8 | — | 0 | — | — | — | — | — |
| ORL@DET | Q1 | 8:27 | — | 0 | — | — | — | — | — |
| ORL@DET | Q1 | 3:06 | — | 0 | — | — | — | — | — |
| ORL@DET | Q2 | 6:16 | — | 0 | — | — | — | — | — |
| ORL@DET | Q2 | 3:34 | — | 0 | — | — | — | — | — |
| ORL@DET | Q3 | 9:35 | ✓ | 5 | DET | 0.4800 | +0.2300 | +0.2300 | +0.2400 |
| ORL@DET | Q3 | 7:45 | ✓ | 10 | ORL | 0.3000 | +0.0300 | +0.0400 | +0.0900 |
| ORL@DET | Q3 | 3:43 | ✓ | 9 | DET | 0.3900 | -0.0300 | -0.0300 | +0.0100 |
| ORL@DET | Q4 | 8:15 | ✓ | 4 | DET | 0.3300 | -0.0400 | -0.0800 | +0.1100 |
| ORL@DET | Q4 | 3:45 | — | 0 | — | — | — | — | — |

## Part C — Run-detection parameter sweep

### Table 6 — Run-detection parameter sensitivity

| Params (margin, lookback) | Run-stopping count | Mean recovery @ 3 min | % positive @ 3 min | n w/ 3min data |
|---|---:|---:|---:|---:|
| (4, 120s) | 4 | +0.0475 | 50% | 4 |
| (4, 180s) | 4 | +0.0550 | 50% | 4 |
| (6, 120s) | 2 | +0.0000 | 50% | 2 |
| (6, 180s) | 3 | -0.0033 | 33% | 3 |
| (8, 240s) | 3 | -0.0033 | 33% | 3 |

## Part D — Strategy 3 entry rule synthesis

**Null result.** The momentum-reversal thesis is not supported by the current data. Post-timeout trajectory is not directionally predictable enough at any tested parameter set (best % positive @ 3 min = 50%, below the 55% threshold required for a rule). n=5 run-stopping timeouts across 2 games is thin — not enough to either confirm or retire the thesis. Collect more playoff games before revisiting.

