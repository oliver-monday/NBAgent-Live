# Strategy 4 — Part 7: Halftime Entry Study
_Generated: 2026-04-21T19:19:54.288779+00:00_
Dataset: 165 competitive games (|spread| ≤ 6) from the 168-game paired dataset. Halftime VWAP defined as the mean `fav_kalshi_vwap` over the final 60s (last 2 bins) of Q2. Exit framework matches S4A best config: target $0.90, stop $0.40, entry zone $0.50–$0.75.
## Table 1 — Halftime entry universe
| Metric | Value |
|---|---:|
| Games with Q2 halftime VWAP observed | 165 |
| Halftime VWAP in $0.50–$0.75 | 54 (32.7%) |
| Games where halftime entry fires | 54 |
Halftime VWAP distribution: min $0.01, p25 $0.40, median $0.63, p75 $0.81, max $0.99.

## Table 2 — Halftime entry P&L vs S4A dip-triggered
| Strategy | Entries | Hit % | Stop % | Held % | Mean P&L | Median P&L | Max win | Max loss | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Halftime entry | 54 | 42.6% | 57.4% | 0.0% | $-1.80 | $-15.37 | $+40.28 | $-35.25 | $-323 |
| S4A dip (best cfg) | 161 | 52.8% | 47.2% | 0.0% | $+3.53 | $+17.48 | $+40.61 | $-43.60 | $+1,886 |

## Table 3 — Halftime entries by halftime-to-prior delta
Delta = pre-game Kalshi price − halftime VWAP. Positive delta means favorite has dropped from its pre-game anchor (disruption signal).

| Δ bucket | Entries | Hit % | Mean P&L | Annual EV share |
|---|---:|---:|---:|---:|
| fav above prior (Δ<0) | 29 | 51.7% | $-1.72 | $-166 |
| 0–$0.05 below prior | 10 | 30.0% | $-4.80 | $-159 |
| $0.05–$0.10 below prior | 5 | 40.0% | $+1.29 | $+21 |
| >$0.10 below prior | 10 | 30.0% | $-0.58 | $-19 |

## Table 4 — S4A dip entries: timing within Q3
Of S4A dip entries that fire in Q3 (total: 27), how many fire within the first seconds of Q3? This measures whether the dip-trigger is already capturing halftime-adjacent moments.

| Window | Entries | % of Q3 entries |
|---|---:|---:|
| First 60s of Q3 | 2 | 7.4% |
| First 120s of Q3 | 5 | 18.5% |
| All Q3 entries | 27 | 100% |

## Table 5 — Halftime entry + S4A dip (combined, Q3+ dip only)
Halftime entry and S4A-dip run on the same game. After a halftime exit (or if halftime did not fire), the dip trigger scans Q3 onward. Each game can produce up to 2 trades.

| Leg | Entries | Hit % | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|
| Halftime leg | 54 | 42.6% | $-1.80 | $-323 |
| Q3+ dip leg | 83 | 63.9% | $+5.25 | $+1,444 |
| **Combined** | **137** | — | **$+2.47** | **$+1,121** |

For reference, baseline S4A dip (all-game) annual EV = $+1,886. The combined strategy captures both the halftime entry and any post-halftime dip, at the cost of potentially forgoing a pre-halftime dip that the baseline would have caught.

