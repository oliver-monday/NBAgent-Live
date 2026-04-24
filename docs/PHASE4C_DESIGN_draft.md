# Phase 4c Design — Paper → Live Delta

Architecture decisions for promoting the S4A paper-trading
engine to real-money execution. This is a **design document**,
not a Code prompt. Review and discuss before implementation.

---

## 1. Scope

**Promoting:** the existing S4A engine (signal detector +
position manager + live runner) from paper-trading to
real-money execution on Kalshi.

**What changes:** order submission, fill monitoring,
stop-order management (including ratchet cancel-and-replace),
risk enforcement, and push notifications.

**What doesn't change:** signal detection logic, entry/exit
rule parameters, position manager P&L accounting, journal
format, game discovery, favorite determination. The signal
path is identical — only the execution layer is new.

---

## 2. Kalshi Trading API surface

### Authentication

RSA-PSS signing. Each request carries three headers:
- `KALSHI-ACCESS-KEY`: API key ID (generated in account
  settings)
- `KALSHI-ACCESS-SIGNATURE`: RSA-PSS signature of
  `{timestamp}{METHOD}{path}` (path without query params)
- `KALSHI-ACCESS-TIMESTAMP`: millisecond Unix timestamp

Private key stored as PEM file on disk (not in repo, not in
env var). Path configured via `KALSHI_KEY_PATH` env var.
API key ID via `KALSHI_API_KEY_ID` env var.

### Endpoints needed

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/portfolio/orders` | POST | Create limit/market order |
| `/portfolio/orders/{id}` | DELETE | Cancel resting order |
| `/portfolio/orders` | GET | List open orders (reconciliation) |
| `/portfolio/fills` | GET | Poll for fills on our orders |
| `/portfolio/positions` | GET | Reconcile engine state vs Kalshi |
| `/portfolio/balance` | GET | Pre-flight capital check |

### Order payload (create)

```json
{
  "ticker": "KXNBAGAME-26APR22ORLDET-ORL",
  "action": "buy",
  "side": "yes",
  "type": "limit",
  "count": 100,
  "yes_price": "0.6200",
  "client_order_id": "<uuid4>",
  "cancel_order_on_pause": true
}
```

`client_order_id` (UUID4) provides idempotency — if a
submission times out and we retry, Kalshi deduplicates on
this ID. Every order submission must generate a fresh UUID
and log it before sending.

`cancel_order_on_pause` = true ensures resting orders are
cancelled if Kalshi pauses trading (maintenance windows,
3–5 AM ET daily).

### Environments

| Environment | Base URL | Use |
|-------------|----------|-----|
| Demo | `https://demo-api.kalshi.co/trade-api/v2` | Phase 4b validation |
| Production | `https://api.elections.kalshi.com/trade-api/v2` | Phase 4c live |

Demo uses the same API surface with simulated funds.
**Phase 4b should run the full live engine against demo**
for at least one full game night before any production
order is submitted.

---

## 3. Order lifecycle for S4A with ratchet

### Entry

Signal detector emits `ENTRY` at price $P_entry.

1. Submit YES buy limit at $P_entry for 100 contracts.
2. Poll for fill (see §5). On fill confirmation:
   a. Submit YES sell limit at $0.90 (target exit, resting).
   b. Submit NO buy limit at $0.60 (initial stop, resting).
   c. Log both order IDs in position state.

All three orders are linked in the position manager by
game_id. The YES sell and NO buy form a manual OCO pair —
when either fills, the engine must cancel the other.

### Target exit ($0.90)

The YES sell at $0.90 fills.

1. Detect fill via polling (§5).
2. Cancel the resting NO buy (stop order).
3. Close position in manager, log P&L.

### Initial stop ($0.40 via NO buy at $0.60)

The NO buy at $0.60 fills = the favorite's YES price has
dropped to $0.40 (since YES $0.40 ≡ NO $0.60).

1. Detect fill via polling.
2. Cancel the resting YES sell at $0.90.
3. Position is now closed: we hold offsetting YES + NO
   contracts that net to zero at resolution.
4. Log as stop exit in manager.

**Note:** holding YES + NO is economically identical to
having sold the YES at $0.40. The position auto-resolves
at game end — one side pays $1.00, offsetting the other.
No further action needed.

### Ratchet trigger (Option A — cancel-and-replace)

Price rises ≥ $0.08 above $P_entry. Position manager fires
ratchet. New effective stop = $P_entry + $0.01.

1. Calculate new NO price: $1.00 - ($P_entry + $0.01).
   Example: entry $0.62 → ratchet stop $0.63 → NO buy at
   $0.37.
2. Cancel the resting NO buy at $0.60.
3. On cancel confirmation, submit new NO buy at the
   tighter price.
4. If the new NO buy submission **fails** (network error,
   rate limit):
   - Immediately re-submit the original NO buy at $0.60
     as fallback.
   - Log the failure as a `ratchet_replace_failed` event.
   - Retry the tighter NO buy on the next tick.
5. If the cancel of the $0.60 NO buy **fails** (already
   filled = stop already triggered while we were
   calculating):
   - Check if we now hold NO contracts (position query).
   - If yes: stop has fired during the ratchet window.
     Cancel the YES sell, log as stop exit.
   - If no: the cancel failed for a transient reason.
     Retry next tick.

**Race condition window:** between cancel confirmation and
replacement submission, there is no resting stop. Duration:
~100–500ms (one HTTP round trip). During this window, if the
price crashes from $0.55 to $0.35, the engine has no
resting protection. Mitigation: the engine's software stop
(polling every 30s) provides a backstop — if price is at
$0.35 on the next tick, the engine submits a taker YES sell
at market. Worst case: one polling cycle of unprotected
exposure (~30s). Acceptable given that S4A stops are almost
always flash crashes where the resting NO buy catches the
move anyway.

### End-of-game

Market transitions to settled status.

1. Cancel all resting orders for this game (YES sell, NO
   buy).
2. Kalshi auto-settles positions at resolution price.
3. Log final P&L from the settlement.

---

## 4. Module design

### New: `engine/kalshi_client.py` (~200 lines)

Authenticated HTTP client. Thin wrapper around `requests`
with RSA-PSS signing. Methods:

- `create_order(ticker, action, side, type, count, price)`
  → order_id
- `cancel_order(order_id)` → success/fail
- `get_order(order_id)` → order status
- `get_fills(ticker=, order_id=)` → list of fills
- `get_positions()` → list of positions
- `get_balance()` → available balance in dollars

Each method:
- Generates `client_order_id` (UUID4) for create.
- Signs the request with RSA-PSS.
- Retries on 5xx / timeout with exponential backoff
  (max 3 retries, same as logger pattern).
- Logs the full request/response for audit trail.
- Raises on 4xx (client error — don't retry, log and
  surface to operator).

### New: `engine/order_manager.py` (~250 lines)

Manages the order lifecycle described in §3. Sits between
the position manager and the Kalshi client. Tracks:

- Per-position: entry order ID, target order ID, stop
  order ID, ratchet state.
- OCO enforcement: when one side fills, cancel the other.
- Ratchet cancel-and-replace with fallback logic.
- Fill polling loop (see §5).

State is ephemeral (in-memory dict keyed by game_id). On
process restart, the reconciliation step (§7) rebuilds
state from Kalshi's position/order APIs.

### Modified: `engine/live_runner.py`

Add a `--live` flag (default: False = paper mode, current
behavior). When `--live`:
- Instantiate `KalshiClient` with auth credentials.
- Instantiate `OrderManager` wrapping the client.
- On entry signal: call `order_manager.submit_entry()`
  instead of logging a paper trade.
- On ratchet trigger: call
  `order_manager.ratchet_replace_stop()`.
- On game end: call `order_manager.close_game()`.
- Pre-flight: check `get_balance()` ≥ minimum required
  (configured, default $200).

Paper mode remains the default and is untouched.

### Modified: `engine/position_manager.py`

Add an `execution_mode` flag (`paper` / `live`). In live
mode, P&L is computed from actual fill prices (from
`get_fills`) rather than the signal price. The position
manager's ratchet logic (updating `effective_stop`) still
runs identically — it drives the order manager's
cancel-and-replace.

---

## 5. Fill monitoring

Kalshi has no push notification for fills. The engine must
poll.

**Approach:** every tick (30s), after processing price
signals, call `get_fills(ticker=game_ticker)` for each
game with an open position. Compare returned fills against
known fills (by trade_id). New fills trigger the OCO
cancel logic.

**Latency:** worst case 30s between fill and detection.
For target exits this is fine (position is already
profitable). For stop fills, the engine might submit a
redundant ratchet cancel for an already-filled stop — the
cancel will fail harmlessly and the fill-detection logic
handles the close.

**Alternative (future):** WebSocket fill feed. Kalshi
supports WebSocket streaming. A future optimization could
subscribe to the fill channel for near-instant detection.
Not required for Phase 4c at 100-contract sizing.

---

## 6. Risk layer

### Hard caps (engine-level, non-bypassable)

| Parameter | Value | Enforcement |
|-----------|-------|-------------|
| Max contracts per entry | 100 | Order manager refuses larger |
| Max entries per game | 2 | Position manager (existing) |
| Max concurrent positions | 4 | Position manager (existing) |
| Max daily gross loss | -$200 | Order manager checks before every entry |
| Min account balance | $200 | Pre-flight check at session start + before each entry |

### Kill switch

A file-based kill switch: if `data/KILL_SWITCH` exists,
the engine refuses all new entries and logs a warning
every tick. Creating the file is instantaneous (`touch
data/KILL_SWITCH` from any terminal). Removing it
re-enables trading.

The daily loss cap also acts as an automatic kill switch:
once cumulative session losses exceed the cap, no new
entries until the next session.

### Capital check

Before each entry, the order manager checks:
1. `get_balance()` ≥ entry cost (price × 100 contracts).
2. Session P&L ≥ daily loss cap.
3. Kill switch file doesn't exist.
4. Concurrent positions < max.

All four must pass. Any failure = no entry, log reason.

---

## 7. Reconciliation

On process start (and optionally every N minutes), the
engine reconciles its in-memory state against Kalshi:

1. `get_positions()` → list of actual holdings.
2. `get_orders()` → list of resting orders.
3. Compare against in-memory position state.
4. If discrepancy: log a `RECONCILIATION_MISMATCH` warning
   with full details. Do NOT auto-correct — surface to
   operator for manual resolution.

Reconciliation is defensive, not corrective. The engine
trusts its own state for trading decisions but alerts the
operator if reality diverges. Auto-correction risks
compounding errors (e.g., the engine thinks a fill didn't
happen, re-submits, doubles the position).

---

## 8. Push notifications

On every trade execution (entry, target exit, stop exit,
ratchet trigger), send a push notification so Oliver can
glance at his phone and confirm the engine is operating
normally.

**Implementation options (in order of simplicity):**

1. **Pushover** — $5 one-time purchase, REST API, 3 lines
   of Python. Delivers to iOS/Android.
2. **Ntfy.sh** — free, REST API, no account needed.
   `curl -d "S4A entry ORL@DET at $0.62" ntfy.sh/nbagent`
3. **Email via SMTP** — more setup, less immediate.
4. **Slack webhook** — if Oliver uses Slack.

Recommendation: Pushover or Ntfy. Both are one HTTP POST
per notification, no SDK, no dependencies beyond `requests`.

**Notification content:**
```
S4A ENTRY: ORL@DET
Buy 100 YES at $0.62
Stop: NO buy $0.60 resting
Target: YES sell $0.90 resting
Balance: $1,247
```

```
S4A RATCHET: ORL@DET
Stop moved: NO $0.60 → NO $0.37
Entry: $0.62, Peak: $0.72
```

```
S4A TARGET: ORL@DET
Sold 100 YES at $0.90
P&L: +$26.12 (net of fees)
Session: +$52.30
```

---

## 9. Staged rollout (revised)

### Phase 4b — Demo environment (1–3 game nights)

Run the full live engine against `demo-api.kalshi.co`.
Real signal detection on live Kalshi market data, real
order submission to demo, real fill monitoring. Validates
the entire order lifecycle without risking capital.

**Graduation criteria:**
- All order types submit and fill correctly (entry, target,
  stop, ratchet replace).
- OCO cancellation fires reliably on fill detection.
- No orphaned orders after game settlement.
- Reconciliation shows zero mismatches.
- Push notifications deliver.

### Phase 4c — Live, capped (2–3 weeks)

Production API. Real capital.

**Caps (from drawdown analysis, pending ratcheted update):**
- $100/game max notional (100 contracts × ~$0.65 entry).
- $200/day max loss (roughly worst-night from backtest).
- 4 concurrent positions max.
- Mandatory morning journal review.

**Graduation criteria:**
- 20+ entries executed.
- Fill prices within $0.02 of signal prices (validates
  maker execution assumption).
- No ratchet-replace failures (or all handled by fallback).
- Realized P&L directionally aligned with projected EV.
- No reconciliation mismatches.

### Phase 4d — Uncapped

Only after 4c results match projections within expected
variance. Cap raises are incremental, not a single jump.

---

## 10. Implementation sequence

Six Code prompts, each self-contained:

1. **`engine/kalshi_client.py`** — authenticated HTTP
   client with RSA-PSS signing. Unit-testable against
   demo endpoint. No trading logic.

2. **`engine/order_manager.py`** — order lifecycle
   management. Depends on kalshi_client. Includes OCO
   enforcement, ratchet cancel-and-replace, fill polling.
   Unit-testable with a mock client.

3. **`engine/live_runner.py` modifications** — `--live`
   flag, order manager integration, pre-flight checks,
   kill switch.

4. **Risk layer** — daily loss cap, balance checks,
   kill switch file. Added to order manager + live runner.

5. **Push notifications** — Pushover/Ntfy integration.
   Fires on every trade action.

6. **Demo validation run** — run against demo-api for
   one game night, verify the full lifecycle, graduate
   to production.

Each prompt is gated on the prior one landing successfully.
Total estimated: ~500 lines of new code + ~50 lines of
modifications to existing files.

---

## 11. Open questions for Oliver

1. **Notification preference:** Pushover ($5, polished) or
   Ntfy (free, minimal)? Or something else?

2. **Daily loss cap:** $200 feels right from the pre-ratchet
   drawdown (worst night was -$148). The ratcheted drawdown
   (pending) may suggest a different number. Want to wait
   for that analysis before locking this in?

3. **Demo validation duration:** one game night sufficient,
   or want 2–3 nights on demo before production?

4. **Starting capital:** how much are you planning to
   deposit for Phase 4c? This affects whether the $200
   min-balance check is appropriate or needs adjustment.

---

## Supersedes

PHASE4A_DESIGN.md "Paper → Live delta" section (5 bullet
points, ~330 lines estimated). This document expands that
sketch into a full design with the ratchet's order
management implications addressed.
