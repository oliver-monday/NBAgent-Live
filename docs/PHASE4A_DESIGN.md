# Phase 4a — S4A Paper-Trading Engine: Design Record

Architecture decisions, scope, and open questions for the S4A
paper-trading engine implemented in `engine/`. This doc is the
single source of truth for *why* the engine looks the way it
does; implementation details live in the code.

---

## Scope

- **In scope (this build):** S4A (favorite dip-recovery) paper
  trading against live Kalshi market-data feeds. Signal detection,
  position management, tick-by-tick journaling, replay validation
  against the 168-game historical dataset.
- **Out of scope:** S1 (bilateral), S3 filtered, real-money order
  submission, alerting, dashboard. Those are separate builds
  gated on paper-trading validation.

---

## Module boundaries

- `engine/s4a_signal.py` — pure signal detection. No I/O, no
  network, no files. One `S4ASignalDetector` instance per game.
  Emits `Signal` enum values (`entry`, `exit_target`,
  `exit_stop`, `hold`, `no_op`).
- `engine/position_manager.py` — pure state tracker. Converts
  signals into `TradeAction` records under risk rules (max
  entries per game, max concurrent positions). Computes paper
  P&L net of maker fees so numbers line up with the offline
  +$1,886/yr.
- `engine/live_runner.py` — the only module with network I/O.
  Polls Kalshi every 30s, feeds prices into the detector +
  manager, appends JSONL to the trade journal.
- `engine/replay.py` — drives historical timeseries through the
  same detector + manager to verify reproduction of the offline
  result.

Keeping signal + manager pure lets the replay validate behavior
without mocking HTTP. The same logic path runs in both live and
historical modes.

---

## Decision 1 — Separate process from the logger

The Kalshi orderbook logger captures irreplaceable data (Kalshi
has no historical orderbook archive). The paper-trading engine is
new and unverified. A crash in the engine must not take out the
logger.

Both processes consume the same public Kalshi market-data API
(unauthenticated), so there is no shared resource contention.
They run as independent Python processes, started and stopped
independently. No shared state beyond the filesystem (and the
engine does not write anywhere the logger reads).

---

## Decision 2 — Favorite from Kalshi opening prices

The favorite side is determined from the first observation where
both sides' `yes_bid_dollars` are above `SETTLE_THRESHOLD`
($0.05). Once locked, it does not change for the rest of the
game.

**Why not pre-game spread from a sportsbook feed?** Adding an
external dependency for a signal that Kalshi prices already
contain is unnecessary surface area. Kalshi's opening quotes are
the market's consensus — for any game where the two sides have
meaningfully different prices, the higher-priced side is the
favorite by definition.

**Edge case:** pick'em games (opening prices within a cent of
$0.50). S4A's signal fires on the favorite side during a dip.
For pick'ems, whichever side happens to be higher at the lock
moment becomes "favorite" by convention. This is acceptable
because pick'em games are rare and the S4A entry zone
($0.50–$0.75) and dip threshold ($0.08) would likely trigger
on either side anyway.

---

## Decision 3 — Risk defaults

Paper-mode risk parameters mirror STRATEGY4_SPEC.md §3 / §5:

- `contracts_per_entry = 100`
- `max_entries_per_game = 2` (one primary + one re-entry)
- `max_concurrent_positions = 4` (soft cap — can be raised after
  a week of paper results show concurrency rarely binds)
- No daily loss cap in paper mode. Real-money mode must add
  one.

The 4-concurrent cap is intentionally conservative. Most NBA
evenings have 6–10 games; the cap forces the engine to stop
opening new positions once 4 are already running, preventing an
over-concentrated night of simultaneous exposure while we still
have no execution-latency data from real fills.

---

## Decision 4 — Trailing max: time-based window, strict eviction

The signal detector uses a time-based deque of
`(ts, price)` observations and evicts entries with
`ts_old <= ts_now - lookback_sec`. Strict-greater-than eviction
(not ≥) is required to match pandas `rolling(window=6,
min_periods=1)` semantics used by the offline sweep.

For evenly spaced 30s ticks and a 180s window, this produces
exactly 6 observations in the window (the current one plus the 5
most recent prior), which matches the bin-based rolling max in
`analysis/strategy4_dip_recovery.py::simulate_s4a`. The replay
validates the equivalence end-to-end.

For live runs with occasional dropped ticks (network blip), the
time-based window still produces sensible behavior: it looks
back in real time, not in ticks. A dropped tick just means one
fewer observation in the window — the dip threshold becomes
harder to trigger momentarily, which is the conservative
direction.

---

## Decision 5 — Skipped Phase 4a alerts

The original Phase 4a plan included a signal-alert layer
(push/SMS/Slack on S4A entry triggers, manual execution on
kalshi.com). This build skips alerts and goes straight to
paper-trading.

**Rationale:** an alert system is ~200 lines of code that would
be discarded once paper-trading validates the strategy and real
trading begins. Paper-trading already:
- Runs the exact signal + position logic the real system will use
- Uses live Kalshi prices (same data real orders would see)
- Records every decision in a reviewable journal

Validation comes from reviewing the morning's journal against
what actually happened in the markets, not from Oliver manually
executing trades on the Kalshi web UI in real time. Morning
review is cheaper, more thorough, and doesn't require Oliver
to be awake during late-night West Coast games.

---

## Paper → Live delta

What has to be built to promote the paper-trading engine to a
real-money system:

1. **Authenticated Kalshi trading API client.** Separate from
   the market-data HTTP helper in `live_runner.py`. New surface:
   order submission, cancellation, fill notifications, position
   queries. New secret: Kalshi API key. Estimated ~150 lines.
2. **Daily loss cap + kill switch.** Hard caps at the manager
   level, provably unbypassable by the signal layer. Estimated
   ~40 lines.
3. **Push notifications on trade execution.** Out-of-band
   confirmation that a trade fired so Oliver can check the
   Kalshi UI if something looks off. ~30 lines.
4. **Fill-monitoring latency loop.** After order submission,
   watch for a fill within N seconds; cancel and re-price if not
   filled. ~50 lines.

Total: ~270 lines on top of the current engine. The signal
detector and position manager do not change.

---

## Journal schema (reference)

Journal path: `data/paper_trades/YYYY-MM-DD.jsonl`.

Record types:
- `session_start` — once at process start.
- `tick` — every 30s per active game.
- `trade` — on every open / close / close_eod.
- `game_finished` — when a market transitions to a settled
  status.
- `session_end` — once at process exit (includes summary dict).

All timestamps are UTC ISO-8601. Prices are floats in dollars.
P&L is net of maker fees on both legs.

---

## Open questions for later

- **Concurrent-position study.** After a target hit at $0.90,
  could a second dip in the same game support a fresh entry?
  Offline sweep treated re-entry as allowed (max 2 per game)
  but doesn't study concurrent-with-first-position re-entry.
- **S1 + S3 layering.** When is it safe to run S4A, S1, and
  S3-filtered simultaneously on the same game? Multi-strategy
  capital allocation is not designed.
- **Playoff parameter sensitivity.** The 168-game dataset spans
  regular season + first-round playoffs. Later rounds may have
  different dynamics (fewer games, higher stakes, tighter
  spreads). Worth a sensitivity check once playoff data
  accumulates.
- **Pre-tip behavior.** `live_runner.py` waits for both sides to
  quote above $0.05 before locking the favorite. In practice
  Kalshi's pre-tip penny grid settles quickly; if it doesn't,
  the engine waits without emitting signals. A future enhancement
  could add a "pre-tip timer" warning.
