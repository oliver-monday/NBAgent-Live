# S3 Reframed — Extended S4A Entry Range
_Generated: 2026-04-23T20:12:55.810855+00:00_
Full 404-game Kalshi paired dataset (404 games). Tests whether pushing S4A's entry range downward ($0.35-$0.50) with S4A-style exits adds EV, plus retests the original S3 filter with five exit variants and a concurrent-tranche (averaging-down) simulation.

**Fee model:** maker on entry + target exit, taker on stop exit. 100 contracts per tranche. No resolution hold except where explicitly called out (Part 2 variants a/e). End-of-game closes at final VWAP with maker fee.

**Annualization:** mean P&L × entries/game × 1230 × 0.445 ≈ 547 effective entries/season.

## Part 1 — Extended entry range × exit-target sweep
128 configs tested. Sweep: entry zones × 7 targets × 4 stops. Skipped cells where stop ≥ entry_lo or target ≤ entry_hi (structurally invalid).

Positive EV configs: **8 of 128** (6.2%).

### Table 1 — Top 20 by annual EV

| # | Config | Entries | Hit % | Mean P&L | Annual EV |
|---:|---|---:|---:|---:|---:|
| 1 | entry[0.40,0.45] tgt0.90 stop0.34 | 151 | 26.5% | $+2.74 | $+561 |
| 2 | entry[0.40,0.45] tgt0.80 stop0.34 | 154 | 28.6% | $+1.38 | $+288 |
| 3 | entry[0.40,0.45] tgt0.70 stop0.34 | 160 | 33.8% | $+0.94 | $+204 |
| 4 | entry[0.40,0.45] tgt0.65 stop0.34 | 164 | 37.2% | $+0.75 | $+166 |
| 5 | entry[0.40,0.45] tgt0.90 stop0.30 | 143 | 28.0% | $+0.81 | $+157 |
| 6 | entry[0.40,0.45] tgt0.90 stop0.25 | 140 | 32.9% | $+0.69 | $+132 |
| 7 | entry[0.40,0.50] tgt0.90 stop0.34 | 201 | 28.4% | $+0.34 | $+92 |
| 8 | entry[0.40,0.45] tgt0.90 stop0.20 | 137 | 36.5% | $+0.29 | $+54 |
| 9 | entry[0.40,0.45] tgt0.65 stop0.30 | 159 | 40.9% | $-0.10 | $-22 |
| 10 | entry[0.35,0.45] tgt0.90 stop0.34 | 205 | 19.5% | $-0.11 | $-32 |
| 11 | entry[0.40,0.45] tgt0.60 stop0.34 | 166 | 39.8% | $-0.16 | $-36 |
| 12 | entry[0.40,0.45] tgt0.55 stop0.34 | 172 | 45.9% | $-0.33 | $-77 |
| 13 | entry[0.40,0.45] tgt0.65 stop0.25 | 158 | 46.2% | $-0.43 | $-92 |
| 14 | entry[0.40,0.45] tgt0.65 stop0.20 | 157 | 51.0% | $-0.48 | $-102 |
| 15 | entry[0.40,0.45] tgt0.80 stop0.30 | 147 | 29.9% | $-0.65 | $-130 |
| 16 | entry[0.40,0.45] tgt0.55 stop0.30 | 169 | 50.9% | $-0.60 | $-137 |
| 17 | entry[0.40,0.45] tgt0.50 stop0.34 | 175 | 53.1% | $-0.59 | $-139 |
| 18 | entry[0.40,0.45] tgt0.70 stop0.30 | 154 | 35.7% | $-0.68 | $-142 |
| 19 | entry[0.40,0.45] tgt0.60 stop0.30 | 162 | 44.4% | $-0.72 | $-159 |
| 20 | entry[0.38,0.50] tgt0.90 stop0.34 | 214 | 26.2% | $-0.59 | $-171 |

### Table 1A — Top 10 detail

| # | Config | Entries | Target | Stop | EOG | Hit % | Mean P&L | Median P&L | Mean winner | Mean loser | Max loss |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | entry[0.40,0.45] tgt0.90 stop0.34 | 151 | 40 | 111 | 0 | 26.5% | $+2.74 | $-11.89 | $+48.60 | $-13.78 | $-28.87 |
| 2 | entry[0.40,0.45] tgt0.80 stop0.34 | 154 | 44 | 110 | 0 | 28.6% | $+1.38 | $-11.85 | $+39.39 | $-13.82 | $-28.87 |
| 3 | entry[0.40,0.45] tgt0.70 stop0.34 | 160 | 54 | 106 | 0 | 33.8% | $+0.94 | $-11.67 | $+30.01 | $-13.86 | $-28.87 |
| 4 | entry[0.40,0.45] tgt0.65 stop0.34 | 164 | 61 | 103 | 0 | 37.2% | $+0.75 | $-11.19 | $+25.07 | $-13.66 | $-28.87 |
| 5 | entry[0.40,0.45] tgt0.90 stop0.30 | 143 | 40 | 103 | 0 | 28.0% | $+0.81 | $-15.24 | $+48.65 | $-17.77 | $-36.26 |
| 6 | entry[0.40,0.45] tgt0.90 stop0.25 | 140 | 46 | 94 | 0 | 32.9% | $+0.69 | $-19.68 | $+48.65 | $-22.77 | $-42.53 |
| 7 | entry[0.40,0.50] tgt0.90 stop0.34 | 201 | 57 | 144 | 0 | 28.4% | $+0.34 | $-15.29 | $+44.83 | $-17.27 | $-35.38 |
| 8 | entry[0.40,0.45] tgt0.90 stop0.20 | 137 | 50 | 87 | 0 | 36.5% | $+0.29 | $-24.35 | $+48.58 | $-27.46 | $-42.53 |
| 9 | entry[0.40,0.45] tgt0.65 stop0.30 | 159 | 65 | 94 | 0 | 40.9% | $-0.10 | $-14.06 | $+25.00 | $-17.47 | $-38.70 |
| 10 | entry[0.35,0.45] tgt0.90 stop0.34 | 205 | 40 | 165 | 0 | 19.5% | $-0.11 | $-10.72 | $+49.01 | $-12.02 | $-28.87 |

## Part 2 — S3 filter on 404 games, five exit variants
**S3 filter:** fav Kalshi VWAP ≤ $0.40, Q1/Q2, ESPN WP dropped ≥ 3pp in last 120s. First qualifying tick per game is the entry. 100 contracts.

### Table 2 — Filtered (full S3 filter)

| Variant | Entries | Mean P&L | Median P&L | Hit % | Annual EV |
|---|---:|---:|---:|---:|---:|
| S3 original (stop 0.34, 25% at 0.50, 75% hold) | 76 | $+2.52 | $-4.34 | 13.2% | $+259 |
| S4A-style (target 0.90, stop 0.40) | 76 | $+1.07 | $-0.60 | 1.3% | $+110 |
| target 0.70, stop 0.30 | 76 | $+0.34 | $-9.61 | 23.7% | $+35 |
| target 0.60, stop 0.30 | 76 | $-1.22 | $-9.40 | 26.3% | $-126 |
| Hold to resolution (no stop/target) | 76 | $-1.08 | $-35.94 | 36.8% | $-111 |

### Table 2B — Unfiltered (fav VWAP ≤ $0.40 only)

| Variant | Entries | Mean P&L | Median P&L | Hit % | Annual EV |
|---|---:|---:|---:|---:|---:|
| S3 original (stop 0.34, 25% at 0.50, 75% hold) | 147 | $+1.92 | $-4.13 | 12.2% | $+382 |
| S4A-style (target 0.90, stop 0.40) | 147 | $+1.20 | $-0.48 | 1.4% | $+239 |
| target 0.70, stop 0.30 | 147 | $-1.17 | $-9.31 | 19.7% | $-234 |
| target 0.60, stop 0.30 | 147 | $-1.89 | $-8.89 | 23.8% | $-377 |
| Hold to resolution (no stop/target) | 147 | $-0.40 | $-35.94 | 37.4% | $-79 |

## Part 3 — Concurrent tranche: S4A + add-on at $0.35-$0.50
S4A standard tranche opens first (entry $0.50-$0.75, exit $0.90, stop $0.40). If S4A remains open AND fav drops into $0.35-$0.50 with a ≥$0.08 dip from trailing 180s max, a second 100-contract tranche opens with its own independent target/stop.

### Table 3 — Add-on configs (standalone add-on EV)

| Target | Stop | S4A entries | Add-on entries | Add-on fire % | Add-on mean P&L | Add-on annual EV |
|---:|---:|---:|---:|---:|---:|---:|
| $0.90 | $0.34 | 235 | 114 | 48.5% | $+3.01 | $+464 |
| $0.90 | $0.30 | 235 | 114 | 48.5% | $+0.88 | $+136 |
| $0.80 | $0.34 | 235 | 114 | 48.5% | $+0.64 | $+98 |
| $0.90 | $0.25 | 235 | 114 | 48.5% | $+0.51 | $+79 |
| $0.70 | $0.34 | 235 | 114 | 48.5% | $+0.22 | $+33 |
| $0.80 | $0.30 | 235 | 114 | 48.5% | $-1.51 | $-233 |
| $0.70 | $0.30 | 235 | 114 | 48.5% | $-1.71 | $-264 |
| $0.60 | $0.34 | 235 | 114 | 48.5% | $-1.79 | $-276 |
| $0.80 | $0.25 | 235 | 114 | 48.5% | $-2.24 | $-346 |
| $0.70 | $0.25 | 235 | 114 | 48.5% | $-2.50 | $-386 |
| $0.60 | $0.30 | 235 | 114 | 48.5% | $-3.22 | $-498 |
| $0.60 | $0.25 | 235 | 114 | 48.5% | $-3.40 | $-525 |

### Table 3A — S4A-only vs S4A+add-on (best add-on config)

Best add-on config: target $0.90, stop $0.34.

| Strategy | Entries counted per game | Mean P&L | Annual EV |
|---|---|---:|---:|
| S4A-only (tranche 1) | 1 per S4A entry | $+3.23 | $+1,028 |
| S4A + add-on (combined per S4A entry) | 1 per S4A entry, add-on fires in 48.5% of them | $+4.69 | $+1,492 |
| Δ (add-on effect) | — | $+1.46 | $+464 |

## Part 4 — Holdout validation
Ran on top 1 Part 1 configs with 6-seed train/test splits (seeds 42-47, train/test ≈ 270/134 at 66.83% train fraction).


### entry[0.40,0.45] tgt0.90 stop0.34 — verdict: **VALIDATED** (5/6 seeds positive on test)

| Seed | Train mean P&L | Test mean P&L |
|---:|---:|---:|
| 42 | $+4.79 | $-0.45 |
| 43 | $+3.34 | $+1.38 |
| 44 | $+3.48 | $+1.42 |
| 45 | $+2.39 | $+3.31 |
| 46 | $+0.85 | $+6.80 |
| 47 | $+1.85 | $+5.68 |

## Part 5 — Comparison to existing S4A
| Config | Entries | Hit % | Mean P&L | Annual EV | Max single loss | Resolution exposure |
|---|---:|---:|---:|---:|---:|---|
| S4A standard [0.50-0.75] tgt0.90 stop0.40 | 311 | 57.6% | $+2.83 | $+1,193 | $-50.25 | no |
| Best extended: entry[0.40,0.45] tgt0.90 stop0.34 | 151 | 26.5% | $+2.74 | $+561 | $-28.87 | no |
| Best S3 filtered (S3 original (stop 0.34, 25% at 0.50, 75% hold)) | 76 | 13.2% | $+2.52 | $+259 | — | no |
| S3 original (a, filtered) | 76 | 13.2% | $+2.52 | $+259 | — | yes (75%) |
| Best Part 3 add-on (target $0.90, stop $0.34) standalone | 114 | — | $+3.01 | $+464 | — | no |

## Part 6 — Verdict

**DEFER**

Directional signal exists but EV is marginal relative to the complexity of adding a second S4A-family module. Best extended-entry: $+561/yr. Best S3 filtered variant: $+259/yr. Revisit after the forward-collection cron adds more paired games; if the signal holds at 600+ games, the BUILD threshold becomes achievable.

---

# Follow-up — Parts 7-11: Ratchet, Trailing, Add-on Holdout, Time Gate
_Follow-up run appended on 2026-04-23T20:12:55.811144+00:00_

Motivation: Part 1's best standalone extended-range config produced +$+561/yr but 74% of entries stopped out at the initial stop. Tests three mechanisms to reduce that drag: (7) ratchet / trailing stop, (8) holdout validation of the Part 3 add-on, (9) time-gated exit on the add-on. Part 10 refreshes the comparison table with the new configs; Part 11 revises the verdict.

## Part 7 — Breakeven ratchet / trailing stop on extended entries
Entry zone fixed at $0.40–$0.45 (Part 1 best). Target fixed at $0.90. Sweeps test what happens when we convert stops on recovered-then-fell-back trajectories from full stop-outs into near-scratch exits.

### Table 7A — Ratchet configs (12)

| Config | Entries | Target | Full stop | Ratchet stop | EoG | Hit % | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ratchet trigger+$0.10 / initial stop $0.34 | 163 | 36 | 87 | 40 | 0 | 22.1% | $+4.63 | $+1,023 |
| ratchet trigger+$0.08 / initial stop $0.34 | 163 | 35 | 84 | 44 | 0 | 21.5% | $+4.58 | $+1,010 |
| ratchet trigger+$0.15 / initial stop $0.34 | 159 | 37 | 94 | 28 | 0 | 23.3% | $+4.52 | $+974 |
| ratchet trigger+$0.20 / initial stop $0.34 | 158 | 38 | 99 | 21 | 0 | 24.1% | $+4.49 | $+961 |
| ratchet trigger+$0.12 / initial stop $0.34 | 162 | 36 | 91 | 35 | 0 | 22.2% | $+4.35 | $+956 |
| ratchet trigger+$0.08 / initial stop $0.30 | 160 | 35 | 71 | 54 | 0 | 21.9% | $+3.79 | $+822 |
| ratchet trigger+$0.10 / initial stop $0.30 | 160 | 36 | 74 | 50 | 0 | 22.5% | $+3.78 | $+819 |
| ratchet trigger+$0.05 / initial stop $0.34 | 166 | 30 | 77 | 59 | 0 | 18.1% | $+3.53 | $+794 |
| ratchet trigger+$0.15 / initial stop $0.30 | 154 | 37 | 83 | 34 | 0 | 24.0% | $+3.35 | $+698 |
| ratchet trigger+$0.12 / initial stop $0.30 | 159 | 36 | 80 | 43 | 0 | 22.6% | $+3.23 | $+696 |
| ratchet trigger+$0.20 / initial stop $0.30 | 153 | 38 | 88 | 27 | 0 | 24.8% | $+3.17 | $+657 |
| ratchet trigger+$0.05 / initial stop $0.30 | 164 | 30 | 64 | 70 | 0 | 18.3% | $+2.92 | $+649 |

### Table 7B — Trailing stop configs (8)

| Config | Entries | Target | Full stop | Trail stop | EoG | Hit % | Mean P&L | Annual EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| trail $0.10 / initial stop $0.30 | 174 | 20 | 0 | 154 | 0 | 11.5% | $+5.18 | $+1,221 |
| trail $0.10 / initial stop $0.34 | 174 | 20 | 47 | 107 | 0 | 11.5% | $+4.95 | $+1,168 |
| trail $0.08 / initial stop $0.30 | 174 | 17 | 0 | 157 | 0 | 9.8% | $+4.92 | $+1,158 |
| trail $0.08 / initial stop $0.34 | 174 | 17 | 18 | 139 | 0 | 9.8% | $+4.77 | $+1,124 |
| trail $0.12 / initial stop $0.30 | 168 | 24 | 14 | 130 | 0 | 14.3% | $+4.93 | $+1,123 |
| trail $0.12 / initial stop $0.34 | 170 | 24 | 62 | 84 | 0 | 14.1% | $+4.82 | $+1,111 |
| trail $0.15 / initial stop $0.34 | 167 | 27 | 78 | 62 | 0 | 16.2% | $+4.82 | $+1,090 |
| trail $0.15 / initial stop $0.30 | 164 | 27 | 43 | 94 | 0 | 16.5% | $+4.69 | $+1,041 |

### Table 7C — Best of each vs no-ratchet baseline

| Config | Entries | Hit % | Mean P&L | Annual EV | Δ vs baseline |
|---|---:|---:|---:|---:|---:|
| **Baseline** (entry[0.40,0.45] tgt0.90 stop0.34) | 151 | 26.5% | $+2.74 | $+561 | — |
| Best ratchet: ratchet trigger+$0.10 / initial stop $0.34 | 163 | 22.1% | $+4.63 | $+1,023 | $+462 |
| Best trail: trail $0.10 / initial stop $0.30 | 174 | 11.5% | $+5.18 | $+1,221 | $+660 |

## Part 8 — Holdout validation

### Table 8A — Add-on tranche (target $0.90, stop $0.34)

6-seed train/test split (67% train). Add-on standalone mean P&L computed over the add-on entries (tranche-2 fires) only.

| Seed | Train addon n | Train mean P&L | Test addon n | Test mean P&L |
|---:|---:|---:|---:|---:|
| 42 | 74 | $+5.74 | 40 | $-2.05 |
| 43 | 82 | $+3.65 | 32 | $+1.36 |
| 44 | 79 | $+2.78 | 35 | $+3.52 |
| 45 | 73 | $+2.25 | 41 | $+4.36 |
| 46 | 78 | $+1.09 | 36 | $+7.15 |
| 47 | 85 | $+1.04 | 29 | $+8.78 |

**Add-on holdout verdict:** **VALIDATED** (5/6 seeds positive on test).

### Table 8B — Best ratchet (ratchet trigger+$0.10 / initial stop $0.34)

6-seed train/test split. Best ratchet beat the no-ratchet baseline at +$+1,023/yr (vs baseline +$+561/yr).

| Seed | Train n | Train mean P&L | Test n | Test mean P&L |
|---:|---:|---:|---:|---:|
| 42 | 101 | $+6.00 | 62 | $+2.40 |
| 43 | 113 | $+4.59 | 50 | $+4.73 |
| 44 | 104 | $+5.62 | 59 | $+2.89 |
| 45 | 100 | $+3.88 | 63 | $+5.83 |
| 46 | 112 | $+3.60 | 51 | $+6.90 |
| 47 | 126 | $+3.56 | 37 | $+8.30 |

**Ratchet holdout verdict:** **VALIDATED** (6/6 seeds positive on test).

## Part 9 — Time-gated add-on tranche
Add-on tranche (target $0.90, stop $0.34) with a forced close if the add-on has been open for ≥ N minutes AND price has not recovered to entry + recovery_threshold. Forced close uses taker fee.

### Table 9A — Time-gate configs (18)

| Gate (min) | Recovery thr | Add-on entries | Target | Stop | Time-gate exits | EoG | Add-on mean P&L | Combined annual EV | Δ vs ungated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | $0.08 | 114 | 24 | 56 | 34 | 0 | $+1.19 | $+1,212 | $-280 |
| 30 | $0.10 | 114 | 23 | 56 | 35 | 0 | $+1.13 | $+1,203 | $-289 |
| 30 | $0.05 | 114 | 24 | 56 | 34 | 0 | $+0.49 | $+1,103 | $-389 |
| 20 | $0.08 | 114 | 17 | 50 | 47 | 0 | $-0.17 | $+1,001 | $-491 |
| 20 | $0.10 | 114 | 15 | 50 | 49 | 0 | $-0.51 | $+949 | $-544 |
| 20 | $0.05 | 114 | 17 | 50 | 47 | 0 | $-0.90 | $+888 | $-604 |
| 15 | $0.08 | 114 | 13 | 44 | 57 | 0 | $-1.33 | $+823 | $-669 |
| 15 | $0.05 | 114 | 15 | 44 | 55 | 0 | $-1.42 | $+809 | $-683 |
| 15 | $0.10 | 114 | 11 | 44 | 59 | 0 | $-1.65 | $+773 | $-719 |
| 10 | $0.08 | 114 | 11 | 41 | 62 | 0 | $-1.75 | $+758 | $-734 |
| 10 | $0.05 | 114 | 13 | 41 | 60 | 0 | $-1.82 | $+746 | $-746 |
| 8 | $0.08 | 114 | 10 | 37 | 67 | 0 | $-2.08 | $+706 | $-786 |
| 10 | $0.10 | 114 | 9 | 41 | 64 | 0 | $-2.13 | $+700 | $-793 |
| 8 | $0.10 | 114 | 8 | 37 | 69 | 0 | $-2.48 | $+644 | $-848 |
| 8 | $0.05 | 114 | 10 | 37 | 67 | 0 | $-2.77 | $+601 | $-892 |
| 5 | $0.08 | 114 | 7 | 27 | 80 | 0 | $-3.14 | $+544 | $-949 |
| 5 | $0.10 | 114 | 6 | 27 | 81 | 0 | $-3.35 | $+510 | $-982 |
| 5 | $0.05 | 114 | 7 | 27 | 80 | 0 | $-3.64 | $+466 | $-1,026 |

### Table 9B — Best time gate vs ungated baseline

| Variant | Add-on entries | Add-on mean | Combined annual EV | Δ vs ungated |
|---|---:|---:|---:|---:|
| Ungated (Part 3 best) | 114 | $+3.01 | $+1,492 | — |
| Best time-gated (30min / +$0.08 recovery) | 114 | $+1.19 | $+1,212 | $-280 |

## Part 10 — Updated comparison (Parts 1-9)

| Config | Entries | Hit % | Mean P&L | Annual EV | Max loss | Resolution? |
|---|---:|---:|---:|---:|---:|---|
| S4A standard [0.50-0.75] tgt0.90 stop0.40 | 311 | 57.6% | $+2.83 | $+1,193 | $-50.25 | no |
| Best extended standalone (Part 1) | 151 | 26.5% | $+2.74 | $+561 | $-28.87 | no |
| Best ratchet (Part 7): ratchet trigger+$0.10 / initial stop $0.34 | 163 | 22.1% | $+4.63 | $+1,023 | $-12.98 | no |
| Best trailing (Part 7): trail $0.10 / initial stop $0.30 | 174 | 11.5% | $+5.18 | $+1,221 | $-10.84 | no |
| S4A + add-on ungated (Part 3) combined | 235 (+114 addon) | — | $+4.69 | $+1,492 | — | no |
| S4A + add-on time-gated (Part 9, 30m/+$0.08) combined | 235 (+114 addon) | — | $+3.81 | $+1,212 | — | no |

## Part 11 — Updated verdict

**BUILD (ungated add-on tranche on S4A engine)**

Holdout-validated add-on tranche on top of the existing S4A engine produces meaningful incremental EV (5/6 seeds positive on test). Best variant: no time gate (ungated outperforms), target $0.90, stop $0.34. Combined annual EV $+1,492/yr vs single-entry S4A baseline $+1,028/yr → **incremental $+464/yr** from the add-on.

Recommend implementing as a second entry band + independent tranche inside the existing S4A engine module; no separate S3 engine is justified. Standalone extended-range (Parts 1, 7) alone does not clear BUILD threshold — the add-on structure is where the value lives.

Time gate note: time-gated variants produced combined $+1,212 vs ungated $+1,492. Patience beats forcing early exits — keep the add-on ungated.

---

# Follow-up #2 — Parts 12-15: Ratchet on S4A Standard + Add-On
_Follow-up run appended on 2026-04-23T20:12:55.811257+00:00_

Part 7's ratchet discovery (on EXTENDED entries, $0.40-$0.45) nearly doubled standalone EV. Parts 12-15 apply the same breakeven-ratchet mechanic to: (12) S4A's own standard entry zone $0.50-$0.75, (13) the add-on tranche from Part 3, (14) the full stack with both tranches ratcheted, (15) holdout validation of the winning config(s).

## Part 12 — Ratchet on S4A standard entries
S4A baseline: entry $0.50-$0.75, target $0.90, initial stop $0.40. S4A baseline (no ratchet): 311 entries, 57.6% hit, $+2.83 mean, $+1,193/yr.

### Table 12A — S4A ratchet configs (6)

| Trigger | Entries | Target | Full stop | Ratchet stop | EoG | Hit % | Ratchet % | Mean P&L | Annual EV | Δ baseline |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| +$0.08 | 358 | 149 | 88 | 121 | 0 | 41.6% | 33.8% | $+3.92 | $+1,899 | $+705 |
| +$0.05 | 372 | 130 | 74 | 168 | 0 | 34.9% | 45.2% | $+3.60 | $+1,812 | $+619 |
| +$0.10 | 355 | 150 | 97 | 108 | 0 | 42.3% | 30.4% | $+3.31 | $+1,592 | $+399 |
| +$0.20 | 320 | 176 | 126 | 18 | 0 | 55.0% | 5.6% | $+3.13 | $+1,355 | $+162 |
| +$0.12 | 345 | 159 | 111 | 75 | 0 | 46.1% | 21.7% | $+2.86 | $+1,337 | $+144 |
| +$0.15 | 331 | 167 | 117 | 47 | 0 | 50.5% | 14.2% | $+2.94 | $+1,316 | $+123 |
| (baseline, no ratchet) | 311 | — | — | — | — | 57.6% | — | $+2.83 | $+1,193 | — |

## Part 13 — Ratchet on add-on tranche only
S4A has NO ratchet (baseline $0.40 stop). Add-on tranche enters in $0.40-$0.45 when S4A is open; target $0.90, initial stop $0.34, plus breakeven ratchet on the add-on.

### Table 13A — Add-on ratchet configs (6)

| Trigger | S4A n | Add-on n | Addon target | Addon full stop | Addon ratchet stop | Addon EoG | Addon mean | Combined annual EV | Δ ungated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| +$0.15 | 235 | 114 | 31 | 59 | 24 | 0 | $+3.76 | $+1,608 | $+116 |
| +$0.20 | 235 | 114 | 33 | 66 | 15 | 0 | $+3.52 | $+1,572 | $+80 |
| +$0.12 | 235 | 114 | 29 | 58 | 27 | 0 | $+3.19 | $+1,520 | $+28 |
| +$0.10 | 235 | 114 | 27 | 56 | 31 | 0 | $+2.72 | $+1,448 | $-45 |
| +$0.08 | 235 | 114 | 23 | 50 | 41 | 0 | $+2.17 | $+1,363 | $-130 |
| +$0.05 | 235 | 114 | 17 | 43 | 54 | 0 | $+0.91 | $+1,168 | $-324 |
| (ungated add-on, Part 3 baseline) | 235 | 114 | — | — | — | — | $+3.01 | $+1,492 | — |

## Part 14 — Full stack: both tranches ratcheted
Top-3 S4A ratchet triggers × top-3 add-on ratchet triggers (Cartesian, deduped). Both tranches have independent ratchet state.

### Table 14A — Combined configs

| Config | S4A n | Add-on n | S4A mean | Add-on mean | Combined mean | Combined annual EV | Δ S4A-only | Δ ungated addon |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S4A+$0.10/addon+$0.20 | 235 | 80 | $+4.07 | $+7.24 | $+6.53 | $+2,079 | $+886 | $+587 |
| S4A+$0.10/addon+$0.15 | 235 | 80 | $+4.07 | $+6.78 | $+6.38 | $+2,030 | $+836 | $+537 |
| S4A+$0.08/addon+$0.20 | 235 | 76 | $+4.03 | $+7.22 | $+6.36 | $+2,025 | $+832 | $+533 |
| S4A+$0.08/addon+$0.15 | 235 | 76 | $+4.03 | $+6.74 | $+6.21 | $+1,976 | $+783 | $+483 |
| S4A+$0.10/addon+$0.12 | 235 | 80 | $+4.07 | $+5.75 | $+6.02 | $+1,917 | $+724 | $+425 |
| S4A+$0.08/addon+$0.12 | 235 | 76 | $+4.03 | $+5.64 | $+5.85 | $+1,863 | $+670 | $+371 |
| S4A+$0.05/addon+$0.20 | 235 | 61 | $+3.60 | $+7.95 | $+5.67 | $+1,804 | $+610 | $+311 |
| S4A+$0.05/addon+$0.15 | 235 | 61 | $+3.60 | $+7.06 | $+5.44 | $+1,730 | $+537 | $+238 |
| S4A+$0.05/addon+$0.12 | 235 | 61 | $+3.60 | $+6.35 | $+5.25 | $+1,672 | $+479 | $+179 |
| (S4A-only baseline) | 311 | 0 | $+2.83 | — | $+2.83 | $+1,193 | — | — |
| (S4A + ungated addon, Part 3 best) | 235 | 114 | $+3.23 | $+3.01 | $+4.69 | $+1,492 | — | — |

## Part 15 — Holdout validation + final comparison
Holdout the top config by combined annual EV (Part 13 or Part 14, whichever is higher). Also holdout S4A-with-ratchet standalone if it materially beats the S4A no-ratchet baseline.

### Table 15A — Top dual-tranche holdout (S4A+$0.10/addon+$0.20)

| Seed | Train n | Train mean P&L | Test n | Test mean P&L |
|---:|---:|---:|---:|---:|
| 42 | 155 | $+8.80 | 80 | $+2.13 |
| 43 | 162 | $+8.12 | 73 | $+3.00 |
| 44 | 161 | $+5.71 | 74 | $+8.32 |
| 45 | 151 | $+7.22 | 84 | $+5.30 |
| 46 | 155 | $+4.75 | 80 | $+9.97 |
| 47 | 161 | $+5.03 | 74 | $+9.79 |

**Dual-tranche holdout verdict:** **VALIDATED** (6/6 seeds positive on test).

### Table 15B — S4A-with-ratchet standalone (+$0.08 trigger)

| Seed | Train n | Train mean P&L | Test n | Test mean P&L |
|---:|---:|---:|---:|---:|
| 42 | 237 | $+5.57 | 121 | $+0.68 |
| 43 | 249 | $+3.72 | 109 | $+4.35 |
| 44 | 241 | $+3.25 | 117 | $+5.28 |
| 45 | 221 | $+4.09 | 137 | $+3.64 |
| 46 | 239 | $+3.72 | 119 | $+4.31 |
| 47 | 249 | $+2.81 | 109 | $+6.45 |

**S4A-with-ratchet holdout verdict:** **VALIDATED** (6/6 seeds positive on test).

### Final comparison — all key configs

| Config | Entries | Hit % | Mean P&L | Annual EV | Max loss |
|---|---:|---:|---:|---:|---:|
| S4A no-ratchet (baseline) | 311 | 57.6% | $+2.83 | $+1,193 | $-50.25 |
| S4A with ratchet (best Part 12, +$0.08) | 358 | 41.6% | $+3.92 | $+1,899 | $-36.90 |
| S4A + add-on no-ratchet (Part 3 baseline) | 235 (+114 addon) | — | $+4.69 | $+1,492 | — |
| S4A + addon (top dual, S4A+$0.10/addon+$0.20) | 235 (+80 addon) | — | $+6.53 | $+2,079 | — |
| Extended standalone + ratchet (Part 7 best) | 163 | 22.1% | $+4.63 | $+1,023 | $-12.98 |

### Final verdict (Parts 12-15 synthesis)

**SHIP — ratcheted add-on on S4A engine**

Best config: S4A ratchet +$0.10, add-on at $0.40-$0.45 target $0.90 stop $0.34 with ratchet +$0.20. Holdout-validated 6/6 seeds positive on test. Combined annual EV $+2,079/yr vs S4A-only $+1,193/yr → **incremental $+886/yr**.

Implementation path: extend the existing S4A engine module with (a) a breakeven ratchet parameter on the primary tranche, and (b) a secondary entry band at $0.40-$0.45 that opens a 100-contract tranche when S4A is already open and a dip trigger fires there. Each tranche has its own ratchet state. No separate S3 engine needed.

Additionally: S4A-with-ratchet standalone at +$0.08 trigger also holdout-validated (6/6 seeds). Standalone S4A-with-ratchet: $+1,899/yr vs baseline $+1,193/yr. The ratchet on S4A standard is itself a zero-complexity win — one parameter, no new entry bands — and can ship independently if the add-on build is deferred.

