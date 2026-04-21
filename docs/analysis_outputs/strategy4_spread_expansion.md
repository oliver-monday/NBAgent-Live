# Strategy 4 — Part 8: Spread Expansion (Path A, ESPN Proxy)
_Generated: 2026-04-21T21:44:18.217215+00:00_
Dataset: 1135 games with ESPN PBP + WP data from `data/nba_master_2025_26.csv`. S4A simulated against ESPN win-probability treated as a directional proxy for Kalshi favorite price. Best config from STRATEGY4_SPEC.md §3: lookback 180s, dip ≥ $0.08, entry $0.50–$0.75, target $0.90, stop $0.40.

**Important caveat.** ESPN WP is NOT Kalshi price. ESPN swings harder (compression mapping from the 168-game aggregate: favorites swing ~5–8pp deeper on ESPN than on Kalshi in mid WP zones). Entry rates, hit rates, and P&L values below are ESPN-scale, not Kalshi-confirmed. The Path A question is: *does the favorite-recovery pattern exist at wider spreads?* Path B (on Kalshi trade tapes from the full-season backfill) will produce the confirmed numbers.

## Table 1 — Entry rate by spread bucket
| |spread| bucket | Games | Games with ≥1 entry | Entries | Entries/game |
|---|---:|---:|---:|---:|
| 1.0–2.0 | 134 | 100 | 144 | 1.07 |
| 2.5–3.5 | 183 | 153 | 216 | 1.18 |
| 4.0–5.0 | 138 | 122 | 182 | 1.32 |
| 5.5–6.0 | 94 | 85 | 125 | 1.33 |
| 6.5–8.0 | 164 | 150 | 219 | 1.34 |
| 8.5–10.0 | 132 | 119 | 167 | 1.27 |
| 10.5+ | 290 | 180 | 243 | 0.84 |

## Table 2 — Hit rate and mean P&L by spread bucket
| |spread| bucket | Entries | Hit % | Mean P&L | ESPN-scale annual EV |
|---|---:|---:|---:|---:|
| 1.0–2.0 | 144 | 36.8% | $-3.68 | $-2,165 |
| 2.5–3.5 | 216 | 34.3% | $-4.37 | $-2,820 |
| 4.0–5.0 | 182 | 36.3% | $-3.90 | $-2,813 |
| 5.5–6.0 | 125 | 47.2% | $-0.15 | $-112 |
| 6.5–8.0 | 219 | 42.5% | $-3.90 | $-2,852 |
| 8.5–10.0 | 167 | 54.5% | $+0.25 | $+172 |
| 10.5+ | 243 | 58.0% | $+0.99 | $+453 |

## Table 3 — Entry price distribution by spread bucket
| |spread| bucket | n | Min | p25 | Median | p75 | Max |
|---|---:|---:|---:|---:|---:|---:|
| 1.0–2.0 | 144 | $0.50 | $0.53 | $0.60 | $0.69 | $0.75 |
| 2.5–3.5 | 216 | $0.50 | $0.53 | $0.59 | $0.66 | $0.75 |
| 4.0–5.0 | 182 | $0.50 | $0.55 | $0.61 | $0.69 | $0.75 |
| 5.5–6.0 | 125 | $0.50 | $0.57 | $0.64 | $0.70 | $0.75 |
| 6.5–8.0 | 219 | $0.50 | $0.58 | $0.66 | $0.71 | $0.75 |
| 8.5–10.0 | 167 | $0.50 | $0.61 | $0.68 | $0.72 | $0.75 |
| 10.5+ | 243 | $0.50 | $0.66 | $0.71 | $0.73 | $0.75 |

## Table 4 — Sanity: Kalshi vs ESPN proxy on |spread|≤6
Same strategy, same entry/exit rules, same filter band. Compares the confirmed Kalshi run (165 competitive games) against the ESPN-proxy run on the same (or nearly same) universe. A large gap indicates the proxy misrepresents entry frequency or P&L.

| Source | Games | Entries | Hit % | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|
| Kalshi (confirmed) | 171 | 166 | 52.4% | $+3.21 | $+1,708 |
| ESPN proxy | 549 | 667 | 37.8% | $-3.30 | $-2,195 |

## Table 5 — Projected expansion annual EV (ESPN-scale)
Adds the 6.5+ buckets to the existing competitive universe. **All numbers are ESPN-scale**, not Kalshi-confirmed. Use Path B (full-season Kalshi backfill) before committing.

| Spread range | Games | Entries | Annual EV (ESPN-scale) |
|---|---:|---:|---:|
| 1.0–2.0 | 134 | 144 | $-2,165 |
| 2.5–3.5 | 183 | 216 | $-2,820 |
| 4.0–5.0 | 138 | 182 | $-2,813 |
| 5.5–6.0 | 94 | 125 | $-112 |
| 6.5–8.0 | 164 | 219 | $-2,852 |
| 8.5–10.0 | 132 | 167 | $+172 |
| 10.5+ | 290 | 243 | $+453 |

**Totals:** 1135 games, 1296 entries, ESPN-scale annual EV $-10,137.
- Existing universe (|spread|≤6): $-7,910 (ESPN-scale)
- Expansion (|spread|>6): $-2,227 (ESPN-scale)

