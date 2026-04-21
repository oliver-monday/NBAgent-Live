"""S4A signal detector — pure logic, no I/O.

Maintains a trailing-max window over recent price observations for one
game's favorite side. On each price update, emits a Signal enum value
indicating whether an S4A entry/exit condition has fired. The caller
(PositionManager + live_runner / replay) decides whether to act on the
signal; the detector only detects.

Defaults mirror STRATEGY4_SPEC.md §3 best config:
  lookback 180s, dip ≥ $0.08, entry $0.50-$0.75,
  target $0.90, stop $0.40.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class Signal(Enum):
    NO_OP = "no_op"
    ENTRY = "entry"
    HOLD = "hold"
    EXIT_TARGET = "exit_target"
    EXIT_STOP = "exit_stop"


@dataclass
class S4ASignalDetector:
    """Per-game S4A signal detector.

    The detector keeps a time-bounded deque of recent (ts, price)
    observations and emits a Signal each update. The "trailing max"
    is the max price within the lookback window (strict older-than
    eviction so a 180s window over 30s-spaced ticks always yields
    6 observations, matching pandas rolling(window=6, min_periods=1)
    which is what the offline analysis used).
    """

    lookback_sec: float = 180.0
    dip_threshold: float = 0.08
    entry_lo: float = 0.50
    entry_hi: float = 0.75
    exit_target: float = 0.90
    exit_stop: float = 0.40

    # Internal state. _observations holds (ts, price) pairs still in the
    # lookback window. _trailing_max is recomputed on each update.
    _observations: deque = field(default_factory=deque, init=False, repr=False)
    _trailing_max: float = field(default=0.0, init=False, repr=False)
    _has_position: bool = field(default=False, init=False, repr=False)

    def reset(self) -> None:
        self._observations.clear()
        self._trailing_max = 0.0
        self._has_position = False

    def update(self, ts: float, fav_bid: float) -> Signal:
        """Feed one price observation; return a Signal."""
        self._observations.append((ts, fav_bid))

        # Evict observations strictly older than (ts - lookback_sec).
        # Strict inequality is required to match pandas rolling(window=N,
        # min_periods=1) semantics for evenly spaced ticks: for a 180s
        # window over 30s bins, the current observation plus the last 5
        # prior = 6 observations. See PHASE4A_DESIGN.md for derivation.
        cutoff = ts - self.lookback_sec
        while self._observations and self._observations[0][0] <= cutoff:
            self._observations.popleft()

        if self._observations:
            self._trailing_max = max(p for _, p in self._observations)
        else:
            self._trailing_max = fav_bid

        if self._has_position:
            if fav_bid >= self.exit_target:
                return Signal.EXIT_TARGET
            if fav_bid <= self.exit_stop:
                return Signal.EXIT_STOP
            return Signal.HOLD

        dip = self._trailing_max - fav_bid
        if dip >= self.dip_threshold and self.entry_lo <= fav_bid <= self.entry_hi:
            return Signal.ENTRY
        return Signal.NO_OP

    def notify_entry(self) -> None:
        """Position manager informs the detector that an entry executed."""
        self._has_position = True

    def notify_exit(self) -> None:
        """Position manager informs the detector that a position closed."""
        self._has_position = False

    @property
    def trailing_max(self) -> float:
        return self._trailing_max

    @property
    def current_dip(self) -> float:
        """Dip of the most recent observation from the trailing max."""
        if not self._observations:
            return 0.0
        last_price = self._observations[-1][1]
        return max(0.0, self._trailing_max - last_price)

    @property
    def has_position(self) -> bool:
        return self._has_position

    @property
    def observation_count(self) -> int:
        return len(self._observations)
