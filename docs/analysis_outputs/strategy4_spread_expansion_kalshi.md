# Strategy 4 — Part 8: Spread Expansion (Path B, Kalshi Confirmed)
_Generated: 2026-04-21T21:52:04.896297+00:00_
Dataset: 404 games with Kalshi paired timeseries CSVs from `data/wp_kalshi_paired/`. S4A simulated directly on `fav_kalshi_vwap` (30s VWAP from the Kalshi trade tape, same column `engine/replay.py` uses). Config from STRATEGY4_SPEC.md §3: lookback 180s, dip ≥ $0.08, entry $0.50–$0.75, target $0.90, stop $0.40.

**Path B uses Kalshi-confirmed prices only.** Games whose trade tape returned empty (typical of pre-retention-cliff games) are excluded rather than backfilled with the ESPN proxy — Path A (`strategy4_spread_expansion.md`) remains the ESPN-only reference.

## Table 1 — Entry rate by spread bucket
| |spread| bucket | Games | Games with ≥1 entry | Entries | Entries/game |
|---|---:|---:|---:|---:|
| 1.0–2.0 | 36 | 23 | 29 | 0.81 |
| 2.5–3.5 | 69 | 52 | 71 | 1.03 |
| 4.0–5.0 | 31 | 22 | 29 | 0.94 |
| 5.5–6.0 | 35 | 28 | 37 | 1.06 |
| 6.5–8.0 | 46 | 30 | 43 | 0.93 |
| 8.5–10.0 | 38 | 26 | 36 | 0.95 |
| 10.5+ | 149 | 54 | 66 | 0.44 |

## Table 2 — Hit rate and mean P&L by spread bucket
| |spread| bucket | Entries | Hit % | Mean P&L | Kalshi-confirmed annual EV |
|---|---:|---:|---:|---:|
| 1.0–2.0 | 29 | 51.7% | $+1.59 | $+702 |
| 2.5–3.5 | 71 | 47.9% | $+2.57 | $+1,446 |
| 4.0–5.0 | 29 | 48.3% | $+2.65 | $+1,357 |
| 5.5–6.0 | 37 | 64.9% | $+6.17 | $+3,570 |
| 6.5–8.0 | 43 | 58.1% | $+4.14 | $+2,116 |
| 8.5–10.0 | 36 | 58.3% | $+0.82 | $+425 |
| 10.5+ | 66 | 69.7% | $+4.55 | $+1,103 |

## Table 3 — Entry price distribution by spread bucket
| |spread| bucket | n | Min | p25 | Median | p75 | Max |
|---|---:|---:|---:|---:|---:|---:|
| 1.0–2.0 | 29 | $0.53 | $0.57 | $0.63 | $0.71 | $0.75 |
| 2.5–3.5 | 71 | $0.50 | $0.53 | $0.58 | $0.66 | $0.75 |
| 4.0–5.0 | 29 | $0.50 | $0.53 | $0.60 | $0.64 | $0.74 |
| 5.5–6.0 | 37 | $0.51 | $0.62 | $0.65 | $0.72 | $0.75 |
| 6.5–8.0 | 43 | $0.51 | $0.59 | $0.66 | $0.69 | $0.75 |
| 8.5–10.0 | 36 | $0.51 | $0.63 | $0.69 | $0.73 | $0.74 |
| 10.5+ | 66 | $0.52 | $0.67 | $0.71 | $0.73 | $0.75 |

## Table 4 — Parity check vs engine replay (|spread|≤6)
Path B on the |spread|≤6 subset should closely match the engine replay's equivalence run against `simulate_s4a`, since both consume the same `fav_kalshi_vwap` column. Small deltas are acceptable from different bucket rollup granularity; large deltas indicate a Path B pipeline bug.

| Source | Games | Entries | Hit % | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|
| Engine replay (2026-04-22) | 171 | 166 | 52.4% | $+3.21 | $+1,708 |
| Path B |spread|≤6 | 171 | 166 | 52.4% | $+3.21 | $+1,708 |

## Table 5 — Projected annual EV (Kalshi-confirmed)
Full breakdown across all spread buckets, then the two incremental rollups (existing universe vs expansion).

| Spread range | Games | Entries | Annual EV |
|---|---:|---:|---:|
| 1.0–2.0 | 36 | 29 | $+702 |
| 2.5–3.5 | 69 | 71 | $+1,446 |
| 4.0–5.0 | 31 | 29 | $+1,357 |
| 5.5–6.0 | 35 | 37 | $+3,570 |
| 6.5–8.0 | 46 | 43 | $+2,116 |
| 8.5–10.0 | 38 | 36 | $+425 |
| 10.5+ | 149 | 66 | $+1,103 |
| **Existing (|spread|≤6)** | **171** | **166** | **$+7,075** |
| **Expansion (|spread|>6)** | **233** | **145** | **$+3,644** |
| **All buckets** | **404** | **311** | **$+10,718** |

## Table 6 — Path A (ESPN proxy) vs Path B (Kalshi) on the same games
For each bucket, simulate both variants on only the games that have BOTH ESPN PBP/WP AND Kalshi trade-tape data. Quantifies the ESPN-to-Kalshi bias per bucket and validates the compression mapping used in Path A.

| |spread| bucket | Games (overlap) | ESPN entries / hit / mean | Kalshi entries / hit / mean |
|---|---:|---|---|
| 1.0–2.0 | 36 | 36 / 36.1% / $-3.71 | 29 / 51.7% / $+1.59 |
| 2.5–3.5 | 69 | 89 / 31.5% / $-7.61 | 71 / 47.9% / $+2.57 |
| 4.0–5.0 | 31 | 35 / 42.9% / $-3.25 | 29 / 48.3% / $+2.65 |
| 5.5–6.0 | 35 | 46 / 54.3% / $+2.19 | 37 / 64.9% / $+6.17 |
| 6.5–8.0 | 46 | 62 / 46.8% / $+1.30 | 43 / 58.1% / $+4.14 |
| 8.5–10.0 | 38 | 50 / 64.0% / $+4.23 | 36 / 58.3% / $+0.82 |
| 10.5+ | 149 | 111 / 64.0% / $+6.32 | 66 / 69.7% / $+4.55 |

