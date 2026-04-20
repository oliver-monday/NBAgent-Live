# Strategy 3 multi-game oscillation analysis — 2026-04-19

Generalization of the HOU-LAL single-game oscillation analysis to all per-game JSONL files (filter: `2026-04-19`, min live snapshots: 50). Uses heuristic tip detection; per-side swing + round-trip + spread + depth analyses; pooled cross-game round-trip economics.

## Section 1 — Games processed

| Game | File | Teams | Live snapshots | Duration | Mean spread | Status |
|---|---|---|---:|---:|---:|---|
| ORL@DET (2026-04-19) | `KXNBAGAME-26APR19ORLDET.jsonl` | DET/ORL | 290 | 145.2 min | $0.0106 | ok |
| PHI@BOS (2026-04-19) | `KXNBAGAME-26APR19PHIBOS.jsonl` | BOS/PHI | 93 | 46.7 min | $0.0101 | ok |
| PHX@OKC (2026-04-19) | `KXNBAGAME-26APR19PHXOKC.jsonl` | OKC/PHX | 73 | 36.6 min | $0.0101 | ok |
| POR@SAS (2026-04-19) | `KXNBAGAME-26APR19PORSAS.jsonl` | POR/SAS | 210 | 105.0 min | $0.0100 | ok |

Processed: **4** / Skipped: **0**.

## Section 2 — Per-game oscillation summary

| Game | Swings ≥$0.10 | ≥$0.15 | Max swing | RTs (0.35,0.50) | RTs (0.40,0.50) | Mean spread | Competitive? |
|---|---:|---:|---:|---:|---:|---:|---|
| ORL@DET | 21 | 13 | $0.390 | 2 | 2 | $0.0106 | ✓ |
| PHI@BOS | 0 | 0 | $0.080 | 0 | 0 | $0.0101 | — |
| PHX@OKC | 0 | 0 | $0.000 | 0 | 0 | $0.0101 | — |
| POR@SAS | 6 | 2 | $0.150 | 0 | 0 | $0.0100 | — |

## Section 3 — Pooled round-trip economics

All completed round-trips across all processed games, at each (entry, exit) pair. Fees per FEES.md: taker `ceil(0.07 × 100 × P × (1-P))`, maker `ceil(0.0175 × ...)`, applied at both legs.

| Entry | Exit | N games w/≥1 | Total trips | Mean hold (min) | Mean gross | Mean net (maker) | Mean MAE ($) | Mean MAE (%) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.35 | 0.50 | 1/4 | 2 | 48.8 | $25.50 | $24.72 | $0.035 | 11.3% |
| 0.35 | 0.45 | 1/4 | 3 | 34.2 | $21.00 | $20.20 | $0.023 | 7.5% |
| 0.40 | 0.50 | 1/4 | 2 | 49.1 | $22.50 | $21.70 | $0.065 | 17.5% |
| 0.40 | 0.55 | 1/4 | 1 | 103.6 | $40.00 | $39.28 | $0.010 | 4.7% |
| 0.45 | 0.55 | 1/4 | 1 | 103.6 | $40.00 | $39.28 | $0.010 | 4.7% |
| 0.45 | 0.60 | 1/4 | 1 | 103.6 | $40.00 | $39.28 | $0.010 | 4.7% |

## Section 4 — Pooled spread and depth at mid ≤ $0.50

Bucketed observations across all processed games.

| Mid bucket | n obs | Mean spread | Median | p75 | Mean depth | Median depth | % ≥ 50k depth |
|---|---:|---:|---:|---:|---:|---:|---:|
| ≤ $0.20 | 401 | $0.0101 | $0.0100 | $0.0100 | 222,772 | 70,662 | 58% |
| (0.20, 0.30] | 35 | $0.0100 | $0.0100 | $0.0100 | 91,787 | 18,221 | 43% |
| (0.30, 0.40] | 182 | $0.0104 | $0.0100 | $0.0100 | 145,298 | 66,988 | 55% |
| (0.40, 0.50] | 50 | $0.0116 | $0.0100 | $0.0100 | 122,646 | 18,295 | 38% |

## Section 5 — Cross-game scorecard

Viability thresholds below are illustrative graduation gates. n=4 is still below the n=10 graduation sample.

| Criterion | Threshold | n=1 (HOU-LAL) | n=N (pooled) | Status |
|---|---|---|---|---|
| Round-trip frequency (% of games w/≥1 trip at 0.40,0.50) | ≥ 15% | 100% (1/1) | 25% (1/4) | ✓ |
| Net per trip (maker-maker, pooled median) | ≥ $5 | $14.55 | $21.70 | ✓ |
| Realized spread (median, mid ≤ 0.50) | ≤ $0.02 | $0.01 | $0.0100 | ✓ |
| Depth (% ≥ 50k at mid ≤ 0.50) | ≥ 50% | ~50% | 55% | ✓ |
| Hold time (median) | ≥ 3 min | 23 min | 49.1 min | ✓ |
| MAE (median, % of entry) | < 50% | 11.6% | 17.5% | ✓ |

## Section 6 — Game-by-game detail (appendix)

### Round-trips at (0.40, 0.50)

| Game | Side | Entry ts | Entry | Exit ts | Exit | Hold (min) | Net (maker) | MAE ($) |
|---|---|---|---:|---|---:|---:|---:|---:|
| ORL@DET | ORL | 2026-04-19 22:34 | 0.215 | 00:03 | 0.525 | 88.1 | $30.26 | $0.010 |
| ORL@DET | ORL | 2026-04-20 00:07 | 0.395 | 00:17 | 0.535 | 10.0 | $13.14 | $0.120 |

### Swings ≥ $0.10 (pooled both sides)

| Game | Side | Type | Start | End | Magnitude | Duration |
|---|---|---|---|---|---:|---:|
| ORL@DET | DET | down | 22:34:22 | 22:44:02 | $0.130 | 9.7 min |
| ORL@DET | DET | up | 22:56:03 | 23:04:02 | $0.155 | 8.0 min |
| ORL@DET | DET | down | 23:04:02 | 23:08:29 | $0.105 | 4.5 min |
| ORL@DET | DET | up | 23:21:29 | 23:31:36 | $0.105 | 10.1 min |
| ORL@DET | DET | down | 23:57:00 | 00:04:32 | $0.180 | 7.5 min |
| ORL@DET | DET | up | 00:04:32 | 00:12:04 | $0.240 | 7.5 min |
| ORL@DET | DET | down | 00:12:04 | 00:22:31 | $0.360 | 10.5 min |
| ORL@DET | DET | down | 00:38:02 | 00:44:02 | $0.120 | 6.0 min |
| ORL@DET | DET | down | 00:46:30 | 00:51:31 | $0.260 | 5.0 min |
| ORL@DET | DET | down | 00:55:31 | 00:59:35 | $0.150 | 4.1 min |
| ORL@DET | ORL | up | 22:34:53 | 22:49:01 | $0.200 | 14.1 min |
| ORL@DET | ORL | down | 22:55:30 | 23:04:00 | $0.170 | 8.5 min |
| ORL@DET | ORL | up | 23:04:00 | 23:08:28 | $0.110 | 4.5 min |
| ORL@DET | ORL | down | 23:21:28 | 23:31:34 | $0.110 | 10.1 min |
| ORL@DET | ORL | up | 23:58:30 | 00:04:31 | $0.180 | 6.0 min |
| ORL@DET | ORL | down | 00:04:31 | 00:11:30 | $0.240 | 7.0 min |
| ORL@DET | ORL | up | 00:11:30 | 00:21:00 | $0.390 | 9.5 min |
| ORL@DET | ORL | down | 00:21:00 | 00:26:01 | $0.115 | 5.0 min |
| ORL@DET | ORL | up | 00:38:29 | 00:45:02 | $0.150 | 6.5 min |
| ORL@DET | ORL | up | 00:46:29 | 00:51:31 | $0.270 | 5.0 min |
| ORL@DET | ORL | up | 00:55:30 | 00:59:34 | $0.150 | 4.1 min |
| POR@SAS | POR | down | 01:25:02 | 02:04:34 | $0.130 | 39.5 min |
| POR@SAS | POR | up | 02:04:34 | 02:43:31 | $0.130 | 39.0 min |
| POR@SAS | POR | down | 02:43:31 | 03:01:33 | $0.150 | 18.0 min |
| POR@SAS | SAS | up | 01:24:30 | 02:04:33 | $0.130 | 40.0 min |
| POR@SAS | SAS | down | 02:04:33 | 02:43:30 | $0.130 | 39.0 min |
| POR@SAS | SAS | up | 02:43:30 | 03:01:32 | $0.150 | 18.0 min |

