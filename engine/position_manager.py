"""Position manager — risk enforcement + paper P&L tracking.

Stateful bookkeeper for open S4A positions across all active games.
Converts Signal values from S4ASignalDetector into TradeAction records
according to the risk rules (max entries per game, max concurrent
positions). Computes paper P&L net of Kalshi maker/taker fees so
results line up with the offline sweep.

No I/O. The caller (live_runner / replay) is responsible for emitting
TradeAction records to the trade journal.

Fee model:
  - Entry: maker (resting limit, queue priority).
  - Target exit at $0.90: maker (pre-placed resting sell).
  - Ratcheted stop exit at entry + $0.01: maker (pre-placed resting
    limit that moves up when the ratchet triggers).
  - Initial stop exit at $0.40: TAKER (reactive market sell — price
    has already collapsed through the level).
  - EOD resolution: no exit fee for clean win/loss (auto-settle);
    maker for mid-price settlements.

Breakeven ratchet (STRATEGY4_SPEC §5A):
  Once the favorite's price rises ≥ `ratchet_trigger` above the
  entry price, the stop moves from the initial `stop_loss` (0.40)
  up to `entry_price + 0.01` (breakeven after maker exit fee).
  Configure via `ratchet_trigger` on PositionManager. Set to 0 or
  None to disable (backward-compatible).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from engine.s4a_signal import Signal


# Exit-price resolution thresholds. Match analysis/strategy4_dip_recovery.py
# end-of-game behavior: a favorite quoted ≥ $0.95 at game end settles to
# $1.00 with no exit fee; ≤ $0.05 settles to $0.00 with no exit fee;
# anything in between settles at the mid-price with a normal exit fee.
RESOLUTION_WIN_CUTOFF = 0.95
RESOLUTION_LOSS_CUTOFF = 0.05

# Default stop-loss ($0.40) — matches STRATEGY4_SPEC §2.
DEFAULT_STOP_LOSS = 0.40

# Ratchet breakeven offset: stop moves to entry + this value to cover
# the maker exit fee on the ratchet-scratch sell.
RATCHET_OFFSET = 0.01


def maker_fee(contracts: int, price: float) -> float:
    """Kalshi maker fee per leg, in dollars."""
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1.0 - price) * 100) / 100


def taker_fee(contracts: int, price: float) -> float:
    """Kalshi taker fee per leg, in dollars."""
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.07 * contracts * price * (1.0 - price) * 100) / 100


@dataclass
class Position:
    game_id: str
    ticker: str
    entry_price: float
    entry_time: float                # epoch seconds
    contracts: int
    entries_this_game: int           # 1 for primary, 2 for re-entry
    # Ratchet state (STRATEGY4_SPEC §5A):
    highest_since_entry: float = 0.0     # updated each tick
    ratchet_triggered: bool = False      # becomes True when trigger hits
    effective_stop: float = DEFAULT_STOP_LOSS  # starts at initial stop
    status: str = "open"
    # Options: open / closed_target / closed_stop / closed_ratchet_stop /
    # closed_eod.


@dataclass
class TradeAction:
    action: str          # open / close_target / close_stop /
                         # close_ratchet_stop / close_eod / no_action
    game_id: str
    ticker: str
    price: float
    contracts: int
    ts: float
    pnl: float | None = None
    entry_price: float | None = None
    hold_seconds: float | None = None
    reason: str = ""
    ratchet_triggered: bool = False   # snapshot at exit (or False for
                                      # open/no_action events)


@dataclass
class PositionManager:
    contracts_per_entry: int = 100
    max_entries_per_game: int = 2
    max_concurrent_positions: int = 4
    stop_loss: float = DEFAULT_STOP_LOSS
    # Target exit level. Represents a resting limit — fills exactly at
    # this price, not at the (possibly higher) observed price that
    # triggered the exit.
    target_exit: float = 0.90
    # Breakeven ratchet trigger. Price must rise ≥ this amount above
    # entry before the stop moves to entry + RATCHET_OFFSET. Set to 0
    # or None to disable (matches pre-ratchet baseline behavior).
    ratchet_trigger: float | None = 0.08

    # Internal state.
    _positions: dict[str, Position] = field(default_factory=dict, init=False)
    _entries_count: dict[str, int] = field(default_factory=dict, init=False)
    _trade_log: list[dict] = field(default_factory=list, init=False)
    _ratchet_events: list[dict] = field(default_factory=list, init=False)

    # -- Helpers ---------------------------------------------------------

    def _ratchet_active_setting(self) -> bool:
        return (
            self.ratchet_trigger is not None
            and self.ratchet_trigger > 0
        )

    def _update_ratchet(self, pos: Position, price: float, ts: float) -> None:
        """Update highest_since_entry; fire ratchet if trigger met."""
        if price > pos.highest_since_entry:
            pos.highest_since_entry = price
        if not self._ratchet_active_setting():
            return
        if pos.ratchet_triggered:
            return
        if (
            pos.highest_since_entry - pos.entry_price
        ) >= self.ratchet_trigger:
            pos.ratchet_triggered = True
            pos.effective_stop = pos.entry_price + RATCHET_OFFSET
            self._ratchet_events.append({
                "ts": ts, "game_id": pos.game_id,
                "entry_price": pos.entry_price,
                "highest_since_entry": pos.highest_since_entry,
                "new_effective_stop": pos.effective_stop,
            })

    # -- Evaluation ------------------------------------------------------

    def evaluate(
        self, game_id: str, ticker: str,
        signal: Signal, price: float, ts: float,
    ) -> TradeAction:
        """Decide whether a signal becomes a trade action.

        Order of operations:
          1. If a position is open in this game, update ratchet state
             (peak + potential trigger).
          2. Entry signals dispatch to _handle_entry.
          3. Target exits dispatch to _handle_exit with type "target".
          4. Stop decision is driven by `effective_stop`, NOT by the
             signal detector's EXIT_STOP. This lets a ratcheted stop
             fire even when the detector's built-in $0.40 check has
             not tripped (ratcheted stop can be much higher than $0.40).
        """
        pos = self._positions.get(game_id)
        if pos is not None:
            self._update_ratchet(pos, price, ts)

        if signal is Signal.ENTRY:
            return self._handle_entry(game_id, ticker, price, ts)

        if signal is Signal.EXIT_TARGET:
            # Target exit fills at the target level (resting limit),
            # not the observed overshoot price.
            return self._handle_exit(
                game_id, ticker, exit_type="target",
                exit_price=self.target_exit, ts=ts,
            )

        # Stop check (manager-driven, uses effective_stop).
        if pos is not None and price <= pos.effective_stop:
            if pos.ratchet_triggered:
                return self._handle_exit(
                    game_id, ticker, exit_type="ratchet_stop",
                    exit_price=pos.effective_stop, ts=ts,
                )
            return self._handle_exit(
                game_id, ticker, exit_type="stop",
                exit_price=pos.effective_stop, ts=ts,
            )

        return TradeAction(
            action="no_action", game_id=game_id, ticker=ticker,
            price=price, contracts=0, ts=ts,
            reason=f"signal={signal.value}",
            ratchet_triggered=(
                pos.ratchet_triggered if pos is not None else False
            ),
        )

    def _handle_entry(
        self, game_id: str, ticker: str, price: float, ts: float,
    ) -> TradeAction:
        if game_id in self._positions:
            return TradeAction(
                action="no_action", game_id=game_id, ticker=ticker,
                price=price, contracts=0, ts=ts,
                reason="reject: position already open in this game",
            )
        if self._entries_count.get(game_id, 0) >= self.max_entries_per_game:
            return TradeAction(
                action="no_action", game_id=game_id, ticker=ticker,
                price=price, contracts=0, ts=ts,
                reason=(
                    f"reject: entries_this_game >= "
                    f"{self.max_entries_per_game}"
                ),
            )
        if self.active_count() >= self.max_concurrent_positions:
            return TradeAction(
                action="no_action", game_id=game_id, ticker=ticker,
                price=price, contracts=0, ts=ts,
                reason=(
                    f"reject: concurrent positions >= "
                    f"{self.max_concurrent_positions}"
                ),
            )

        entries = self._entries_count.get(game_id, 0) + 1
        self._entries_count[game_id] = entries
        pos = Position(
            game_id=game_id, ticker=ticker,
            entry_price=price, entry_time=ts,
            contracts=self.contracts_per_entry,
            entries_this_game=entries,
            highest_since_entry=price,
            ratchet_triggered=False,
            effective_stop=self.stop_loss,
        )
        self._positions[game_id] = pos
        label = "primary" if entries == 1 else "re-entry"
        reason = f"S4A entry ({label}) at ${price:.2f}"
        action = TradeAction(
            action="open", game_id=game_id, ticker=ticker,
            price=price, contracts=pos.contracts, ts=ts,
            reason=reason, ratchet_triggered=False,
        )
        self._trade_log.append(self._as_log_dict(action))
        return action

    def _handle_exit(
        self, game_id: str, ticker: str, exit_type: str,
        exit_price: float, ts: float,
    ) -> TradeAction:
        """Close an open position.

        exit_type:
          "target"        — reached $0.90 (maker on both legs).
          "ratchet_stop"  — hit ratcheted breakeven stop
                            (maker on both legs).
          "stop"          — hit initial $0.40 stop (maker on entry,
                            taker on exit).
        """
        pos = self._positions.get(game_id)
        if pos is None:
            return TradeAction(
                action="no_action", game_id=game_id, ticker=ticker,
                price=exit_price, contracts=0, ts=ts,
                reason=f"reject: no open position for exit ({exit_type})",
            )

        entry_fee = maker_fee(pos.contracts, pos.entry_price)
        if exit_type == "target":
            action_type = "close_target"
            exit_fee = maker_fee(pos.contracts, exit_price)
            pos.status = "closed_target"
            reason = f"S4A target: ${exit_price:.2f}"
        elif exit_type == "ratchet_stop":
            action_type = "close_ratchet_stop"
            exit_fee = maker_fee(pos.contracts, exit_price)
            pos.status = "closed_ratchet_stop"
            reason = (
                f"S4A ratchet stop: ${exit_price:.2f} "
                f"(entry ${pos.entry_price:.2f}, "
                f"peak ${pos.highest_since_entry:.2f})"
            )
        elif exit_type == "stop":
            action_type = "close_stop"
            exit_fee = taker_fee(pos.contracts, exit_price)
            pos.status = "closed_stop"
            reason = f"S4A stop: ${exit_price:.2f}"
        else:
            raise ValueError(f"unknown exit_type={exit_type!r}")

        pnl = (exit_price - pos.entry_price) * pos.contracts - entry_fee - exit_fee
        hold_sec = ts - pos.entry_time
        action = TradeAction(
            action=action_type, game_id=game_id, ticker=ticker,
            price=exit_price, contracts=pos.contracts, ts=ts,
            pnl=pnl, entry_price=pos.entry_price,
            hold_seconds=hold_sec, reason=reason,
            ratchet_triggered=pos.ratchet_triggered,
        )
        self._trade_log.append(self._as_log_dict(action))
        del self._positions[game_id]
        return action

    def end_of_game(
        self, game_id: str, final_price: float, ts: float,
    ) -> TradeAction | None:
        """Close any remaining position at resolution.

        Matches analysis/strategy4_dip_recovery.py end-of-game handling:
          - final_price ≥ 0.95: settle at $1.00, no exit fee
          - final_price ≤ 0.05: settle at $0.00, no exit fee
          - otherwise: settle at final_price with maker exit fee
        """
        pos = self._positions.get(game_id)
        if pos is None:
            return None

        if final_price >= RESOLUTION_WIN_CUTOFF:
            resolution, exit_fee = 1.0, 0.0
            reason = "EOD resolution: fav won (settled $1.00)"
        elif final_price <= RESOLUTION_LOSS_CUTOFF:
            resolution, exit_fee = 0.0, 0.0
            reason = "EOD resolution: fav lost (settled $0.00)"
        else:
            resolution = float(final_price)
            exit_fee = maker_fee(pos.contracts, resolution)
            reason = f"EOD resolution: mid-price ${resolution:.2f}"

        entry_fee = maker_fee(pos.contracts, pos.entry_price)
        pnl = (
            (resolution - pos.entry_price) * pos.contracts
            - entry_fee - exit_fee
        )
        pos.status = "closed_eod"
        action = TradeAction(
            action="close_eod", game_id=game_id, ticker=pos.ticker,
            price=resolution, contracts=pos.contracts, ts=ts,
            pnl=pnl, entry_price=pos.entry_price,
            hold_seconds=ts - pos.entry_time, reason=reason,
            ratchet_triggered=pos.ratchet_triggered,
        )
        self._trade_log.append(self._as_log_dict(action))
        del self._positions[game_id]
        return action

    # -- Introspection ---------------------------------------------------

    def active_count(self) -> int:
        return len(self._positions)

    def game_state(self, game_id: str) -> dict:
        pos = self._positions.get(game_id)
        return {
            "game_id": game_id,
            "has_position": pos is not None,
            "status": pos.status if pos else "none",
            "entry_price": pos.entry_price if pos else None,
            "highest_since_entry": (
                pos.highest_since_entry if pos else None
            ),
            "ratchet_triggered": (
                pos.ratchet_triggered if pos else False
            ),
            "effective_stop": pos.effective_stop if pos else None,
            "entries_this_game": self._entries_count.get(game_id, 0),
            "max_entries": self.max_entries_per_game,
        }

    def trade_log(self) -> list[dict]:
        return list(self._trade_log)

    def ratchet_events(self) -> list[dict]:
        return list(self._ratchet_events)

    def summary(self) -> dict:
        closes = [
            r for r in self._trade_log
            if r["action"] not in ("open", "no_action")
        ]
        n_close = len(closes)
        n_target = sum(
            1 for r in closes if r["action"] == "close_target"
        )
        n_stop = sum(
            1 for r in closes if r["action"] == "close_stop"
        )
        n_ratchet_stop = sum(
            1 for r in closes if r["action"] == "close_ratchet_stop"
        )
        n_eod = sum(1 for r in closes if r["action"] == "close_eod")
        pnls = [r["pnl"] for r in closes if r.get("pnl") is not None]
        total_pnl = sum(pnls)
        mean_pnl = total_pnl / len(pnls) if pnls else 0.0
        return {
            "entries": sum(
                1 for r in self._trade_log if r["action"] == "open"
            ),
            "closes": n_close,
            "closed_target": n_target,
            "closed_stop": n_stop,
            "closed_ratchet_stop": n_ratchet_stop,
            "closed_eod": n_eod,
            "total_pnl": total_pnl,
            "mean_pnl": mean_pnl,
            "hit_pct": (100.0 * n_target / n_close) if n_close else 0.0,
            "open_positions": self.active_count(),
            "ratchet_events": len(self._ratchet_events),
        }

    # -- Helpers ---------------------------------------------------------

    @staticmethod
    def _as_log_dict(action: TradeAction) -> dict:
        return {
            "ts": action.ts,
            "action": action.action,
            "game_id": action.game_id,
            "ticker": action.ticker,
            "price": action.price,
            "contracts": action.contracts,
            "pnl": action.pnl,
            "entry_price": action.entry_price,
            "hold_seconds": action.hold_seconds,
            "reason": action.reason,
            "ratchet_triggered": action.ratchet_triggered,
        }
