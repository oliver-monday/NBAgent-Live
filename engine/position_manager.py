"""Position manager — risk enforcement + paper P&L tracking.

Stateful bookkeeper for open S4A positions across all active games.
Converts Signal values from S4ASignalDetector into TradeAction records
according to the risk rules (max entries per game, max concurrent
positions). Computes paper P&L net of Kalshi maker fees so results are
directly comparable to the projected +$1,886/yr from the offline sweep.

No I/O. The caller (live_runner / replay) is responsible for emitting
TradeAction records to the trade journal.
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


def maker_fee(contracts: int, price: float) -> float:
    """Kalshi maker fee per leg, in dollars.

    ceil(0.0175 * contracts * price * (1 - price) * 100) / 100.
    Matches analysis/strategy4_dip_recovery.py so paper results line
    up with the offline sweep.
    """
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1.0 - price) * 100) / 100


@dataclass
class Position:
    game_id: str
    ticker: str
    entry_price: float
    entry_time: float            # epoch seconds
    contracts: int
    entries_this_game: int       # 1 for primary, 2 for re-entry
    status: str = "open"         # open / closed_target / closed_stop / closed_eod


@dataclass
class TradeAction:
    action: str                  # open / close_target / close_stop / close_eod / no_action
    game_id: str
    ticker: str
    price: float
    contracts: int
    ts: float
    pnl: float | None = None
    entry_price: float | None = None
    hold_seconds: float | None = None
    reason: str = ""


@dataclass
class PositionManager:
    contracts_per_entry: int = 100
    max_entries_per_game: int = 2
    max_concurrent_positions: int = 4

    # Internal state.
    _positions: dict[str, Position] = field(default_factory=dict, init=False)
    _entries_count: dict[str, int] = field(default_factory=dict, init=False)
    _trade_log: list[dict] = field(default_factory=list, init=False)

    # -- Evaluation ------------------------------------------------------

    def evaluate(
        self, game_id: str, ticker: str,
        signal: Signal, price: float, ts: float,
    ) -> TradeAction:
        """Decide whether a signal becomes a trade action."""
        if signal is Signal.ENTRY:
            return self._handle_entry(game_id, ticker, price, ts)
        if signal in (Signal.EXIT_TARGET, Signal.EXIT_STOP):
            return self._handle_exit(game_id, ticker, signal, price, ts)
        return TradeAction(
            action="no_action", game_id=game_id, ticker=ticker,
            price=price, contracts=0, ts=ts,
            reason=f"signal={signal.value}",
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
        )
        self._positions[game_id] = pos
        label = "primary" if entries == 1 else "re-entry"
        reason = f"S4A entry ({label}) at ${price:.2f}"
        action = TradeAction(
            action="open", game_id=game_id, ticker=ticker,
            price=price, contracts=pos.contracts, ts=ts,
            reason=reason,
        )
        self._trade_log.append(self._as_log_dict(action))
        return action

    def _handle_exit(
        self, game_id: str, ticker: str, signal: Signal,
        price: float, ts: float,
    ) -> TradeAction:
        pos = self._positions.get(game_id)
        if pos is None:
            return TradeAction(
                action="no_action", game_id=game_id, ticker=ticker,
                price=price, contracts=0, ts=ts,
                reason=f"reject: no open position for {signal.value}",
            )

        if signal is Signal.EXIT_TARGET:
            action_type = "close_target"
            pos.status = "closed_target"
            reason = f"S4A target: ${price:.2f}"
        else:
            action_type = "close_stop"
            pos.status = "closed_stop"
            reason = f"S4A stop: ${price:.2f}"

        fees = maker_fee(pos.contracts, pos.entry_price) + maker_fee(
            pos.contracts, price,
        )
        pnl = (price - pos.entry_price) * pos.contracts - fees
        hold_sec = ts - pos.entry_time
        action = TradeAction(
            action=action_type, game_id=game_id, ticker=ticker,
            price=price, contracts=pos.contracts, ts=ts,
            pnl=pnl, entry_price=pos.entry_price,
            hold_seconds=hold_sec, reason=reason,
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
          - otherwise: settle at final_price with normal exit fee
        """
        pos = self._positions.get(game_id)
        if pos is None:
            return None

        if final_price >= RESOLUTION_WIN_CUTOFF:
            resolution, exit_fee = 1.0, 0.0
            reason = f"EOD resolution: fav won (settled $1.00)"
        elif final_price <= RESOLUTION_LOSS_CUTOFF:
            resolution, exit_fee = 0.0, 0.0
            reason = f"EOD resolution: fav lost (settled $0.00)"
        else:
            resolution = float(final_price)
            exit_fee = maker_fee(pos.contracts, resolution)
            reason = f"EOD resolution: mid-price ${resolution:.2f}"

        entry_fee = maker_fee(pos.contracts, pos.entry_price)
        pnl = (resolution - pos.entry_price) * pos.contracts - entry_fee - exit_fee
        pos.status = "closed_eod"
        action = TradeAction(
            action="close_eod", game_id=game_id, ticker=pos.ticker,
            price=resolution, contracts=pos.contracts, ts=ts,
            pnl=pnl, entry_price=pos.entry_price,
            hold_seconds=ts - pos.entry_time, reason=reason,
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
            "entries_this_game": self._entries_count.get(game_id, 0),
            "max_entries": self.max_entries_per_game,
        }

    def trade_log(self) -> list[dict]:
        return list(self._trade_log)

    def summary(self) -> dict:
        closes = [
            r for r in self._trade_log if r["action"] != "open"
            and r["action"] != "no_action"
        ]
        n_close = len(closes)
        n_target = sum(1 for r in closes if r["action"] == "close_target")
        n_stop = sum(1 for r in closes if r["action"] == "close_stop")
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
            "closed_eod": n_eod,
            "total_pnl": total_pnl,
            "mean_pnl": mean_pnl,
            "hit_pct": (100.0 * n_target / n_close) if n_close else 0.0,
            "open_positions": self.active_count(),
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
        }
