# Strategy 1 Bilateral — Follow-Up Investigations
_Generated: 2026-04-23T03:23:31.173734+00:00_
Three focused follow-ups on the parent `strategy1_bilateral_sim.py` analysis. Dataset: **404 games** (resolvable outcomes, all spreads). Baseline operating point: Policy A at threshold (X=0.20, Y=0.35) with T5 (5-min / 10-tick) stranded exit.

**Data approximation (inherited from parent):** `dog_kalshi_vwap` is computed as `1 - fav_kalshi_vwap`. Kalshi bid-ask spread (1-2c typical) is not modeled, so bilateral cost is slightly optimistic. Directional findings are robust; absolute EV should be read as an upper bound.

## Investigation 1 — Re-entry simulation
Per-game state machine with up to **3 entries**. After a T5 exit, wait `cooldown_ticks` before re-entry eligibility. Optional per-game realized-loss cap halts further entries once cumulative game P&L ≤ -cap.

**Structural constraint revealed by this investigation:** bilaterals in the parent's single-entry baseline have a **minimum interim of 71 ticks (35.5 min)** between leg 1 and leg 2; median is 209 ticks. With T5 bounded at 10 ticks (5 min), re-entry guarantees **zero bilateral completions** — leg 2 never has time to fill before the T5 cutoff fires. Each re-entry cycle therefore realizes only T5 exit P&L (typically small negative due to fees + taker slippage). The results below quantify how much this death-by-cuts pattern costs per game.

| Config | Cooldown | Loss cap | Games entered | Total entries | Bilats | T5 exits | EoG | Bilat $ | T5 $ | EoG $ | EV/game | Annual EV | Δ vs baseline |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1-entry baseline | — | — | 404 | 404 | 90 | 314 | 0 | $+4,817 | $-681 | $0 | $+10.24 | $+5,603 | — |
| re-3 cd=1 cap=none | 1 | none | 404 | 1212 | 0 | 1212 | 0 | $+0 | $-2,119 | $+0 | $-5.25 | $-2,871 | $-8,473 |
| re-3 cd=1 cap=$10 | 1 | $10 | 404 | 1126 | 0 | 1126 | 0 | $+0 | $-1,959 | $+0 | $-4.85 | $-2,653 | $-8,256 |
| re-3 cd=1 cap=$20 | 1 | $20 | 404 | 1207 | 0 | 1207 | 0 | $+0 | $-2,108 | $+0 | $-5.22 | $-2,856 | $-8,459 |
| re-3 cd=10 cap=none | 10 | none | 404 | 1212 | 0 | 1212 | 0 | $+0 | $-2,035 | $+0 | $-5.04 | $-2,756 | $-8,359 |
| re-3 cd=10 cap=$10 | 10 | $10 | 404 | 1125 | 0 | 1125 | 0 | $+0 | $-1,916 | $+0 | $-4.74 | $-2,595 | $-8,198 |
| re-3 cd=10 cap=$20 | 10 | $20 | 404 | 1209 | 0 | 1209 | 0 | $+0 | $-2,038 | $+0 | $-5.04 | $-2,760 | $-8,363 |

### Entries-per-game distribution
| Config | 0 entries | 1 entry | 2 entries | 3 entries | Mean entries/game |
|---|---:|---:|---:|---:|---:|
| re-3 cd=1 cap=none | 0 | 0 | 0 | 404 | 3.00 |
| re-3 cd=1 cap=$10 | 0 | 20 | 46 | 338 | 2.79 |
| re-3 cd=1 cap=$20 | 0 | 0 | 5 | 399 | 2.99 |
| re-3 cd=10 cap=none | 0 | 0 | 0 | 404 | 3.00 |
| re-3 cd=10 cap=$10 | 0 | 20 | 47 | 337 | 2.78 |
| re-3 cd=10 cap=$20 | 0 | 0 | 3 | 401 | 2.99 |

### Blowout accumulation (worst 10 — no-cap, cd=1)
Worst per-game outcomes for the most permissive config (cooldown=1, no loss cap). Answers how bad the death-by-cuts scenario gets when the engine keeps re-entering.

| # | Game | |Spread| | Entries | Bilats | T5 | Cumulative P&L | Trajectory |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | KXNBAGAME-26MAR08NYKLAL | 2.5 | 3 | 0 | 3 | $-33.49 | T5@t72→t82:fav@$0.35→$0.29 ($-7.62); T5@t83→t93:fav@$0.26→$0.23 ($-3.90); T5@t94→t104:fav@$0.28→$0.07 ($-21.98) |
| 2 | KXNBAGAME-26FEB25BOSDEN | 3.5 | 3 | 0 | 3 | $-30.19 | T5@t207→t217:dog@$0.34→$0.19 ($-16.37); T5@t218→t228:dog@$0.18→$0.08 ($-10.08); T5@t229→t239:dog@$0.09→$0.06 ($-3.74) |
| 3 | KXNBAGAME-26APR01BOSMIA | 4.5 | 3 | 0 | 3 | $-29.77 | T5@t34→t44:dog@$0.34→$0.20 ($-14.88); T5@t45→t55:dog@$0.20→$0.09 ($-12.22); T5@t56→t66:dog@$0.09→$0.06 ($-2.67) |
| 4 | KXNBAGAME-26MAR25ATLDET | 2.5 | 3 | 0 | 3 | $-25.26 | T5@t76→t86:fav@$0.35→$0.29 ($-7.74); T5@t87→t97:fav@$0.27→$0.21 ($-7.12); T5@t98→t108:fav@$0.21→$0.11 ($-10.41) |
| 5 | KXNBAGAME-26APR02SASLAC | 3.5 | 3 | 0 | 3 | $-24.93 | T5@t52→t62:dog@$0.34→$0.21 ($-14.70); T5@t63→t73:dog@$0.18→$0.11 ($-8.70); T5@t74→t84:dog@$0.10→$0.09 ($-1.53) |
| 6 | KXNBAGAME-26APR12CHIDAL | 6.5 | 3 | 0 | 3 | $-24.65 | T5@t1→t11:dog@$0.34→$0.22 ($-13.36); T5@t12→t22:dog@$0.21→$0.16 ($-6.15); T5@t23→t33:dog@$0.16→$0.12 ($-5.15) |
| 7 | KXNBAGAME-26APR09INDBKN | 2.5 | 3 | 0 | 3 | $-23.81 | T5@t21→t31:dog@$0.34→$0.22 ($-13.77); T5@t32→t42:dog@$0.22→$0.20 ($-3.44); T5@t43→t53:dog@$0.19→$0.13 ($-6.61) |
| 8 | KXNBAGAME-26MAR12DENSAS | 5.5 | 3 | 0 | 3 | $-23.71 | T5@t49→t59:dog@$0.35→$0.30 ($-6.21); T5@t60→t70:dog@$0.28→$0.23 ($-6.63); T5@t71→t81:dog@$0.25→$0.15 ($-10.86) |
| 9 | KXNBAGAME-26APR01ATLORL | 4.5 | 3 | 0 | 3 | $-22.88 | T5@t72→t82:dog@$0.35→$0.35 ($-1.21); T5@t86→t96:dog@$0.32→$0.19 ($-14.99); T5@t97→t107:dog@$0.19→$0.13 ($-6.68) |
| 10 | KXNBAGAME-26MAR25MIACLE | 2.5 | 3 | 0 | 3 | $-22.80 | T5@t63→t73:fav@$0.34→$0.23 ($-12.62); T5@t74→t84:fav@$0.23→$0.16 ($-7.63); T5@t85→t95:fav@$0.17→$0.16 ($-2.56) |

## Investigation 2 — T5 exit P&L distribution
All **314 stranded T5 exits** from the parent's single-entry baseline. Shows the shape of per-exit P&L.

### P&L histogram

| P&L bucket | Count | % | Cumulative % |
|---|---:|---:|---:|
| > +$5.00 | 17 | 5.4% | 5.4% |
| +$2.00 to +$5.00 | 30 | 9.6% | 15.0% |
| +$0.50 to +$2.00 | 39 | 12.4% | 27.4% |
| -$0.50 to +$0.50 | 26 | 8.3% | 35.7% |
| -$2.00 to -$0.50 | 48 | 15.3% | 51.0% |
| -$5.00 to -$2.00 | 79 | 25.2% | 76.1% |
| < -$5.00 | 75 | 23.9% | 100.0% |

### Summary stats

- Profitable (P&L > $0): 100
- Unprofitable (P&L < $0): 214
- Approximately breakeven (|P&L| < $0.50): 26
- Mean P&L of profitable exits: $+2.88
- Mean P&L of unprofitable exits: $-4.53
- All T5 exits: mean $-2.17, median $-1.86, P10 $-8.62, P25 $-4.70, P75 $+0.69, P90 $+3.39

### Entry price vs T5 P&L

| Entry price | Count | Mean T5 P&L | Profitable % |
|---|---:|---:|---:|
| ≤ $0.10 | 59 | $-1.03 | 25.4% |
| $0.10-$0.15 | 47 | $-0.27 | 53.2% |
| $0.15-$0.20 | 27 | $-3.92 | 18.5% |
| $0.20-$0.25 | 32 | $-1.74 | 43.8% |
| $0.25-$0.30 | 28 | $-2.80 | 32.1% |
| $0.30-$0.35 | 121 | $-3.04 | 26.4% |

## Investigation 3 — Blowout filter sensitivity
Pre-game filter: skip the game entirely if either side's first in-game observation is ≥ cutoff. All filters run the same baseline (Policy A, (0.20, 0.35), T5).

### Single-entry baseline per filter

| Filter | Games | Entries | Bilats | Stranded | Bilat $ | Strand $ | EV/game | Annual EV | Δ vs unfiltered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| none (baseline) | 404 | 404 | 90 | 314 | $+4,817 | $-681 | $+10.24 | $+5,603 | $+0 |
| ≥ $0.80 | 257 | 257 | 76 | 181 | $+3,874 | $-502 | $+13.12 | $+7,181 | $+1,578 |
| ≥ $0.75 | 218 | 218 | 69 | 149 | $+3,455 | $-446 | $+13.80 | $+7,553 | $+1,951 |
| ≥ $0.70 | 183 | 183 | 62 | 121 | $+3,085 | $-367 | $+14.85 | $+8,127 | $+2,525 |

### Excluded games — spread distribution

| Filter | Excluded | 1-2 | 2.5-3.5 | 4-5 | 5.5-6 | 6.5-8 | 8.5-10 | 10.5+ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none (baseline) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ≥ $0.80 | 147 | 2 | 0 | 1 | 0 | 1 | 5 | 138 |
| ≥ $0.75 | 186 | 2 | 0 | 1 | 0 | 6 | 31 | 146 |
| ≥ $0.70 | 221 | 2 | 0 | 2 | 4 | 27 | 38 | 148 |

### Excluded games — what we're giving up

| Filter | Excluded | Their total P&L | Their mean EV/game | Interpretation |
|---|---:|---:|---:|---|
| none (baseline) | 0 | $0 | $0.00 | no games cut |
| ≥ $0.80 | 147 | $+763.75 | $+5.20 | cuts profitable games (filter costs EV) |
| ≥ $0.75 | 186 | $+1,127.30 | $+6.06 | cuts profitable games (filter costs EV) |
| ≥ $0.70 | 221 | $+1,418.42 | $+6.42 | cuts profitable games (filter costs EV) |

### Re-entry config under each filter (best re-entry config only)

Best re-entry config from Investigation 1: cooldown=10, loss_cap=$10, annual EV $-2,595 on the unfiltered universe. Apply each filter and re-run:

| Filter | Games | Total entries | Bilats | T5 | EoG | EV/game | Annual EV | Δ vs unfiltered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none (baseline) | 404 | 1125 | 0 | 1125 | 0 | $-4.74 | $-2,595 | $+0 |
| ≥ $0.80 | 257 | 694 | 0 | 694 | 0 | $-5.75 | $-3,149 | $-554 |
| ≥ $0.75 | 218 | 585 | 0 | 585 | 0 | $-6.08 | $-3,329 | $-733 |
| ≥ $0.70 | 183 | 489 | 0 | 489 | 0 | $-6.74 | $-3,690 | $-1,094 |

### Blowout filter + re-entry interaction

Worst 5 per-game P&L outcomes for the best re-entry config, WITH $0.80 filter vs WITHOUT. Tighter floors on the WITH side indicate the filter is defusing blowouts.

**Without $0.80 filter (top 5 worst):**

| # | Game | |Spread| | Entries | T5 | Cumulative P&L |
|---:|---|---:|---:|---:|---:|
| 1 | KXNBAGAME-26APR12GSWLAC | 6.5 | 3 | 3 | $-29.85 |
| 2 | KXNBAGAME-26MAR05UTAWAS | 2.5 | 3 | 3 | $-24.06 |
| 3 | KXNBAGAME-26APR10DETCHA | 5.5 | 3 | 3 | $-23.43 |
| 4 | KXNBAGAME-26MAR19MILUTA | 5.5 | 2 | 2 | $-19.79 |
| 5 | KXNBAGAME-26MAR01MILCHI | 2.5 | 1 | 1 | $-19.58 |

**With $0.80 filter (top 5 worst):**

| # | Game | |Spread| | Entries | T5 | Cumulative P&L |
|---:|---|---:|---:|---:|---:|
| 1 | KXNBAGAME-26APR12GSWLAC | 6.5 | 3 | 3 | $-29.85 |
| 2 | KXNBAGAME-26MAR05UTAWAS | 2.5 | 3 | 3 | $-24.06 |
| 3 | KXNBAGAME-26APR10DETCHA | 5.5 | 3 | 3 | $-23.43 |
| 4 | KXNBAGAME-26MAR19MILUTA | 5.5 | 2 | 2 | $-19.79 |
| 5 | KXNBAGAME-26MAR01MILCHI | 2.5 | 1 | 1 | $-19.58 |

## Recommended S1 engine configuration

Based on the three investigations, the best-tested configuration is:

- **Entry policy:** Policy A (any observation ≤ $0.35)
- **Thresholds:** X=$0.20 (leg 2 tight), Y=$0.35 (leg 1 wide)
- **Re-entry:** DISABLED (single entry per game). Investigation 1 showed re-entry at T5=5min produces **zero bilateral completions** because leg 2 takes 70+ ticks to fill (median 209 ticks). Every additional entry under re-entry is pure T5 churn — strictly negative EV.
- **Blowout filter:** ≥ $0.70
- **Stranded exit:** T5 (5-min abandonment at market)

**Headline annual EV at this config:** $+8,127 (single-entry, filter ≥ $0.70)

For comparison:
- Parent single-entry unfiltered baseline: $+5,603/yr
- Best re-entry unfiltered: $-2,595/yr (worse than baseline — re-entry destroys value)
- Best single-entry filtered: $+8,127/yr (≥ $0.70)
- Best re-entry filtered: $-2,595/yr (none (baseline))

**Key findings across the three investigations:**

1. **Re-entry at T5=5min is structurally broken** because bilaterals need 35+ min minimum to complete (median 104 min). T5 exits happen before leg 2 has any chance to fill. Re-entry would only help if T5 were extended past the typical bilateral horizon — but that defeats the point of re-entry (you can't retry within the same game).
2. **T5 exit distribution is wider than the mean suggests.** Aggregate T5 P&L is -$681 across 314 exits (mean -$2.17) — small enough that bilateral wins swamp it. But the per-exit distribution is not tight: 68% of T5 exits are losses, 24% lose more than $5, and P10 is -$8.62. The strand mechanism works at portfolio level because the 90 bilateral wins average +$53.52, not because individual strands are close to breakeven.
3. **Blowout filters help modestly.** Filtering out games where the underdog opens below a threshold cuts the most lopsided match-ups. The filter removes some profitable games too, but on balance the EV/game goes up (fewer games, but higher average EV).

**Caveats that matter for paper trading:**

- The `dog_kalshi_vwap = 1 - fav_vwap` approximation inflates bilateral cost slightly; real fills will be marginally worse.
- Simulation assumes leg-1 maker bids fill reliably at threshold; Kalshi queue priority is not modeled.
- The structural re-entry finding assumes leg-2 fills require the observed interim times (median 104 min). If real markets produce earlier leg-2 fills (e.g., during live momentum swings not captured in 30s-VWAP bins), re-entry economics could shift. Paper-trading will validate.

