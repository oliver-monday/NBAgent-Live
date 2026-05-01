# Paper-Trade Journal Review v1
_Generated: 2026-04-30T23:12:18.401075+00:00_
Backtest anchors (from STRATEGY4_SPEC §5A, ratcheted 404-game replay): 0.89 entries/game, 41.6% target hit rate, 24.6% full-stop rate, 33.8% ratchet-scratch rate, +$3.92 mean P&L per entry. Variance tolerances on this small sample: ±15pp on rates, ±$2 on mean P&L, [0.5, 2.0] on entries-per-game ratio.

## 1. Coverage summary
- Journal files: **9** (2026-04-21 → 2026-04-30 if sorted)
- Distinct (date, game_id) pairs observed: **26**
- Of those, well-observed (≥120 ticks ≈ ≥1h polling): **3**
- session_start records: **12**
- session_end records: **2** (unmatched / sessions started without ending: **10**)
- tick records: **1,005**
- trade records: **3** (3 open, 0 close)
- invalid JSON lines: 0
- `game_finished` records: **never observed** (PHASE4A_DESIGN documents this type but the engine writer does not emit it; market `closed` / `settled` statuses are likewise absent — every tick has `market_status="active"`).

## 2. Operational health
| Date | Games | Sessions | Crashes | Tick gaps >60s | Errors |
|------|------:|---------:|--------:|---------------:|-------:|
| 2026-04-21 | 3 | 4 | 2 | 3 | 0 |
| 2026-04-22 | 2 | 1 | 1 | 0 | 0 |
| 2026-04-23 | 3 | 1 | 1 | 0 | 0 |
| 2026-04-24 | 3 | 1 | 1 | 0 | 0 |
| 2026-04-25 | 4 | 1 | 1 | 0 | 0 |
| 2026-04-26 | 4 | 1 | 1 | 0 | 0 |
| 2026-04-28 | 3 | 1 | 1 | 0 | 0 |
| 2026-04-29 | 1 | 1 | 1 | 0 | 0 |
| 2026-04-30 | 3 | 1 | 1 | 0 | 0 |

Games with tick-gap anomalies (3 of 26):
- 2026-04-21 PHI-at-BOS: median gap 30.9s, max gap 2639.9s (182 ticks)
- 2026-04-21 POR-at-SAS: median gap 30.9s, max gap 2639.9s (183 ticks)
- 2026-04-21 HOU-at-LAL: median gap 30.9s, max gap 2639.9s (183 ticks)

## 3. Signal & entry behavior
- Entries observed: **3**
- Expected (well-observed games × 0.89): ~2.7 → ratio 1.12× (within band)
- Expected (all games × 0.89): ~23.1 → ratio 0.13× (BELOW band)

### Entry price distribution

| Bucket | Count |
|---|---:|
| $0.40–$0.45 | 0 |
| $0.45–$0.50 | 0 |
| $0.50–$0.55 | 0 |
| $0.55–$0.60 | 0 |
| $0.60–$0.65 | 0 |
| $0.65–$0.70 | 1 |
| $0.70–$0.75 | 2 |
| $0.75–$0.80 | 0 |
| $0.80–$0.85 | 0 |

Out-of-spec entries (price ∉ [$0.50, $0.75]): **0**.

### Entries per game

| Entries | Games |
|---:|---:|
| 0 | 23 |
| 1 | 3 |

### Time of entry (since first tick of game)

| Date | Game | Entry $ | Time since first tick |
|---|---|---:|---:|
| 2026-04-21 | PHI-at-BOS | $0.66 | 130.2 min |
| 2026-04-21 | POR-at-SAS | $0.73 | 130.2 min |
| 2026-04-21 | PHI-at-BOS | $0.71 | 10155.1 min |

## 4. Exit behavior
**No closes recorded across the entire dataset.** Open positions: 3. Without close events the target / stop / scratch / EOD breakdown cannot be compared against backtest. This is the load-bearing finding of this review.

## 5. Ratchet behavior
Tick records do not carry a `ratchet_triggered` field; ratchet status is inferred from the post-entry price trajectory in the same game's tick stream. For each entry, we walk forward and look for any tick where fav_bid ≥ entry + $0.08.

- Entries inferred to have triggered the ratchet (post-entry max ≥ entry+$0.08): **1 / 1**
- Backtest reference: 270 / 358 entries (75.4%) reached the +$0.08 trigger on the 404-game replay; of those, ~44.8% ended as scratches and ~55.2% as targets.

### Per-entry ratchet inference

| Date | Game | Entry $ | Post-entry ticks | Max post-entry $ | Triggered |
|---|---|---:|---:|---:|:---:|
| 2026-04-28 | PHI-at-BOS | $0.71 | 63 | $0.89 | YES |

Mean P&L on ratchet-triggered vs non-triggered entries: **not computable** (zero closes in journal).

## 6. Favorite determination
Full sanity check (compare favorite to higher Kalshi YES bid at lock moment) requires the underdog's bid at lock time, which the journal does not record. Available partial check: first observed `fav_bid` for each game must be > $0.50, since the favorite is by definition the >50% side of a binary YES market. Pick'em flag: first fav_bid within $0.02 of $0.50.

- Games where fav_team flipped mid-stream: **0** (any > 0 is a HIGH bug)
- Games whose first fav_bid < $0.50 (favorite on the wrong side): **0** (any > 0 is a HIGH bug)
- Games whose first fav_bid = $0.50 exactly (pick'em edge case): **1**
- Pick'em games (first fav_bid in [$0.50, $0.52]): **3**

## 7. Anomalies & follow-ups
- **HIGH** — 10 session_start record(s) have no matching session_end (12 starts, 2 ends). All observed session_ends carry `interrupted=true`.
  - _Expected:_ Sessions should write a clean session_end on graceful shutdown (max_run reached, idle exit, EOD).
  - _Next step:_ Diagnose engine shutdown path; confirm session_end is written on Ctrl-C / SIGTERM, not just on internal exit.
- **HIGH** — 3 entries opened but 0 closes ever logged.
  - _Expected:_ Engine should emit close_target / close_stop / close_ratchet_stop / close_eod events when positions exit. PHASE4A_DESIGN §journal contract specifies these.
  - _Next step:_ Possible causes: (a) sessions terminating before any exit signal fires (consistent with all session_ends carrying interrupted=true); (b) end_of_game() not being called on graceful shutdown; (c) journal writer not wired to close-action codepath. Verify by replaying one of the 3 entries against engine.replay and confirming a close action would fire on the same data.
- **MEDIUM** — 3 of 26 games show tick-gap anomalies (median > 60s or max > 5min).
  - _Expected:_ Median ~30s, no individual gap should exceed ~60s under normal polling.
  - _Next step:_ Spot-check the affected games against logger uptime; if engine was started late or interrupted, those gaps are expected and not a code defect.
- **MEDIUM** — 0 / 26 games reached a `game_finished` event.
  - _Expected:_ Engine should emit `game_finished` (or set a closed/settled tick status) when a market resolves so downstream audits can distinguish 'still in progress' from 'engine missed the close.'
  - _Next step:_ Phase 4a engine enhancement: emit `game_finished` on market_status transition to closed/settled (or mirror the existing ratchet_event approach with a structured close record).
- **LOW** — 1 game(s) opened with first fav_bid = $0.50 exactly (pick'em). Engine resolved a favorite anyway (likely from pre-game spread / ESPN), which is a reasonable fallback but worth tracking.
  - _Expected:_ Document pick'em handling explicitly in PHASE4A_DESIGN; consider whether to skip such games entirely or accept the spread-based tie-break.
  - _Next step:_ Watch list — re-evaluate after more pick'em games accumulate to see if outcomes track backtest.

## 8. Verdict
**BLOCK** — At least one HIGH-severity finding present. Diagnose before continuing live runs. See §7 for blockers.

