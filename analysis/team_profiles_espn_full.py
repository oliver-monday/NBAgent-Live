"""Team profiles — full 2025-26 ESPN WP validation (all 30 teams).

Companion to `team_profiles_playoff16.py`. Runs the same six-section
analysis on the full 1,234-game ESPN WP dataset. Primary goal:
**validate whether team-level S4A hit rate dispersion observed on
Kalshi holds at 3× sample size**, using Spearman's ρ between the
Kalshi and ESPN hit-rate rankings of the 16 playoff teams.

**Calibration caveat:** ESPN WP is systematically more reactive than
Kalshi at the tails (compression mapping from
`wp_vs_kalshi_aggregate.md`: +8.30pp at 0.20–0.40 WP, −2.73pp at
0.80–1.00 WP). Absolute S4A hit rates and P&L are therefore NOT
directly comparable between the two reports. The validation is on
**rank order**, not absolute levels.

Run:
    python -m analysis.team_profiles_espn_full
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PBP_DIR = REPO_ROOT / "data" / "pbp"
WP_DIR = REPO_ROOT / "data" / "espn_wp"
MASTER_CSV = REPO_ROOT / "data" / "nba_master_2025_26.csv"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "team_profiles_espn_full.md"
)

PLAYOFF_TEAMS: list[str] = [
    "DET", "BOS", "NYK", "CLE", "TOR", "ATL", "PHI", "ORL",
    "OKC", "SAS", "DEN", "LAL", "HOU", "MIN", "POR", "PHX",
]
PLAYOFF_SET = set(PLAYOFF_TEAMS)

# Kalshi ranks from team_profiles_playoff16.md Section 3A, for
# the Spearman rank comparison.
KALSHI_RANK = {
    "NYK": 1, "ATL": 2, "CLE": 3, "BOS": 4, "POR": 5,
    "OKC": 6, "DEN": 7, "SAS": 8, "PHI": 9, "PHX": 10,
    "ORL": 11, "MIN": 12, "DET": 13, "TOR": 14, "LAL": 15,
    "HOU": 16,
}
KALSHI_HIT_PCT = {
    "NYK": 78.6, "ATL": 75.0, "CLE": 70.6, "BOS": 66.7, "POR": 66.7,
    "OKC": 64.7, "DEN": 61.9, "SAS": 61.5, "PHI": 60.0, "PHX": 56.2,
    "ORL": 54.5, "MIN": 54.5, "DET": 53.8, "TOR": 44.4, "LAL": 44.4,
    "HOU": 30.4,
}
KALSHI_TIER = {
    "NYK": "Tier 1", "ATL": "Tier 1", "CLE": "Tier 1", "BOS": "Tier 1",
    "POR": "Tier 1", "OKC": "Tier 1", "DEN": "Tier 1", "SAS": "Tier 1",
    "PHI": "Tier 1", "PHX": "Tier 2", "ORL": "Tier 2", "MIN": "Tier 2",
    "DET": "Tier 2", "TOR": "Tier 3", "LAL": "Tier 3", "HOU": "Tier 3",
}

# S4A signal parameters
S4A_LOOKBACK_SEC = 180
S4A_DIP = 0.08
S4A_ENTRY_LO = 0.50
S4A_ENTRY_HI = 0.75
S4A_TARGET = 0.90
S4A_STOP = 0.40
S4A_POOLED_POOLED_HIT = None  # computed from dataset

CONTRACTS = 100
SWING_THRESHOLD = 0.10

# Game-time helpers
Q_LEN_SEC = 720
OT_LEN_SEC = 300
MIN_SEC_REM_FILTER = 60  # exclude final minute

SPREAD_BUCKETS_FAV: list[tuple[str, float, float]] = [
    ("small (1-3)", 1.0, 3.0),
    ("medium (3.5-6)", 3.5, 6.0),
    ("large (6.5+)", 6.5, float("inf")),
]


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


def maker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1 - price) * 100) / 100


def taker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    return math.ceil(0.07 * contracts * price * (1 - price) * 100) / 100


# ---- Data loading ------------------------------------------------------

_CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2}(?:\.\d+)?)$")


def _parse_clock_str(s: str | None) -> float | None:
    if not s:
        return None
    m = _CLOCK_RE.match(s.strip())
    if not m:
        return None
    try:
        return int(m.group(1)) * 60 + float(m.group(2))
    except ValueError:
        return None


def _elapsed_from_period_clock(
    period: int, clock_sec: float,
) -> float:
    if period <= 4:
        return (period - 1) * Q_LEN_SEC + (Q_LEN_SEC - clock_sec)
    return 4 * Q_LEN_SEC + (period - 5) * OT_LEN_SEC + (OT_LEN_SEC - clock_sec)


def _total_game_sec(max_period: int) -> float:
    if max_period <= 4:
        return 4 * Q_LEN_SEC
    return 4 * Q_LEN_SEC + (max_period - 4) * OT_LEN_SEC


@dataclass
class GameData:
    game_id: str
    home_team: str
    away_team: str
    home_spread: float
    home_score: int
    away_score: int
    fav_team: str
    dog_team: str
    winner_team: str
    # Observations: list of (elapsed_sec, period, fav_wp) sorted by elapsed.
    # Filtered to sec_rem >= MIN_SEC_REM_FILTER.
    observations: list[tuple[float, int, float]] = field(default_factory=list)


def _parse_game(
    game_id: str, home_team: str, away_team: str,
    home_spread: float, home_score: int, away_score: int,
) -> GameData | None:
    pbp_path = PBP_DIR / f"{game_id}.jsonl"
    wp_path = WP_DIR / f"{game_id}.jsonl"
    if not pbp_path.exists() or not wp_path.exists():
        return None
    # Plays: pid → (period, elapsed)
    plays: dict[str, tuple[int, float]] = {}
    max_period = 4
    with pbp_path.open() as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            pid = obj.get("id")
            period_raw = (obj.get("period") or {}).get("number")
            if period_raw is None:
                continue
            period = int(period_raw)
            max_period = max(max_period, period)
            clock_str = (obj.get("clock") or {}).get("displayValue")
            clock_sec = _parse_clock_str(clock_str)
            if clock_sec is None:
                continue
            elapsed = _elapsed_from_period_clock(period, clock_sec)
            if pid:
                plays[str(pid)] = (period, elapsed)
    total_sec = _total_game_sec(max_period)

    # WP observations
    obs: list[tuple[float, int, float]] = []
    with wp_path.open() as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            pid = obj.get("playId")
            home_wp = obj.get("homeWinPercentage")
            if pid is None or home_wp is None:
                continue
            key = str(pid)
            if key not in plays:
                continue
            period, elapsed = plays[key]
            sec_rem = total_sec - elapsed
            if sec_rem < MIN_SEC_REM_FILTER:
                continue
            obs.append((elapsed, period, float(home_wp)))
    obs.sort(key=lambda x: x[0])
    if len(obs) < 5:
        return None

    # Determine favorite from first observation + home_spread tiebreak
    first_home_wp = obs[0][2]
    if abs(first_home_wp - 0.5) < 0.01:
        # Pick'em — use home_spread
        if home_spread < 0:
            fav_side = "home"
        elif home_spread > 0:
            fav_side = "away"
        else:
            fav_side = "home"
    else:
        fav_side = "home" if first_home_wp > 0.5 else "away"

    if fav_side == "home":
        fav_team, dog_team = home_team, away_team
    else:
        fav_team, dog_team = away_team, home_team

    # Winner from scores (preferred). Fallback: final home_wp.
    if home_score > away_score:
        winner_team = home_team
    elif away_score > home_score:
        winner_team = away_team
    else:
        # Fallback to final ESPN WP
        final_home_wp = obs[-1][2]
        if final_home_wp >= 0.5:
            winner_team = home_team
        else:
            winner_team = away_team

    # Transform observations to fav_wp perspective
    if fav_side == "home":
        fav_obs = obs
    else:
        fav_obs = [(e, p, 1.0 - w) for (e, p, w) in obs]

    return GameData(
        game_id=game_id, home_team=home_team, away_team=away_team,
        home_spread=home_spread,
        home_score=home_score, away_score=away_score,
        fav_team=fav_team, dog_team=dog_team,
        winner_team=winner_team, observations=fav_obs,
    )


def load_all_games() -> list[GameData]:
    master = pd.read_csv(MASTER_CSV)
    master["home_spread"] = pd.to_numeric(
        master["home_spread"], errors="coerce",
    )
    master["home_score"] = pd.to_numeric(
        master["home_score"], errors="coerce",
    )
    master["away_score"] = pd.to_numeric(
        master["away_score"], errors="coerce",
    )
    games: list[GameData] = []
    skipped = 0
    for r in master.itertuples():
        try:
            gid = str(int(r.game_id))
        except (ValueError, TypeError):
            continue
        home_team = getattr(r, "home_team_abbrev", None)
        away_team = getattr(r, "away_team_abbrev", None)
        if not home_team or not away_team:
            continue
        home_spread = (
            float(r.home_spread) if not pd.isna(r.home_spread) else 0.0
        )
        home_score = (
            int(r.home_score) if not pd.isna(r.home_score) else 0
        )
        away_score = (
            int(r.away_score) if not pd.isna(r.away_score) else 0
        )
        gd = _parse_game(
            gid, str(home_team), str(away_team),
            home_spread, home_score, away_score,
        )
        if gd is None:
            skipped += 1
            continue
        games.append(gd)
    log(f"  loaded {len(games)} games; skipped {skipped} (missing/short)")
    return games


# ---- TeamGame structure + team organization --------------------------

@dataclass
class TeamGame:
    game: GameData
    team: str
    opp: str
    is_home: bool
    is_favorite: bool

    @property
    def series(self) -> np.ndarray:
        """Team-centric WP series (fav_wp if team is fav, else 1 − fav_wp)."""
        fav = np.array([o[2] for o in self.game.observations])
        return fav if self.is_favorite else 1.0 - fav

    @property
    def elapsed(self) -> np.ndarray:
        return np.array([o[0] for o in self.game.observations])

    @property
    def periods(self) -> np.ndarray:
        return np.array([o[1] for o in self.game.observations])

    @property
    def team_won(self) -> bool:
        return self.team == self.game.winner_team

    @property
    def abs_spread(self) -> float:
        return abs(self.game.home_spread)


def build_team_games(
    games: list[GameData],
) -> dict[str, list[TeamGame]]:
    out: dict[str, list[TeamGame]] = defaultdict(list)
    for g in games:
        for team, opp, is_home in [
            (g.home_team, g.away_team, True),
            (g.away_team, g.home_team, False),
        ]:
            is_fav = (team == g.fav_team)
            out[team].append(TeamGame(
                game=g, team=team, opp=opp,
                is_home=is_home, is_favorite=is_fav,
            ))
    return out


# ---- S4A signal on irregular ESPN observations -----------------------

@dataclass
class S4AResult:
    game_id: str
    entered: bool
    entry_elapsed: float = 0.0
    entry_period: int = 0
    entry_wp: float = 0.0
    exit_type: str = ""        # target / stop / resolution_win / resolution_loss / none
    exit_wp: float = 0.0
    pnl: float = 0.0


def apply_s4a(game: GameData) -> S4AResult:
    """Apply S4A signal using elapsed-time trailing max (180s window)."""
    obs = game.observations
    n = len(obs)
    if n < 2:
        return S4AResult(game_id=game.game_id, entered=False)

    # Sliding window for trailing max on fav_wp
    # We'll use a simple linear scan with a deque-like search — n is
    # at most ~500 per game so this is cheap.
    entered = False
    entry_idx = -1
    entry_wp = 0.0
    entry_elapsed = 0.0
    entry_period = 0
    for i in range(n):
        e_i, p_i, wp_i = obs[i]
        if not entered:
            # Trailing max over prior observations within [e_i - 180, e_i]
            cutoff = e_i - S4A_LOOKBACK_SEC
            tmax = wp_i
            for j in range(i, -1, -1):
                e_j = obs[j][0]
                if e_j < cutoff:
                    break
                if obs[j][2] > tmax:
                    tmax = obs[j][2]
            if (
                S4A_ENTRY_LO <= wp_i <= S4A_ENTRY_HI
                and (tmax - wp_i) >= S4A_DIP
            ):
                entered = True
                entry_idx = i
                entry_wp = wp_i
                entry_elapsed = e_i
                entry_period = p_i
                continue
        else:
            # In position: check exits
            if wp_i >= S4A_TARGET:
                entry_fee = maker_fee(CONTRACTS, entry_wp)
                exit_fee = maker_fee(CONTRACTS, S4A_TARGET)
                pnl = (S4A_TARGET - entry_wp) * CONTRACTS - entry_fee - exit_fee
                return S4AResult(
                    game_id=game.game_id, entered=True,
                    entry_elapsed=entry_elapsed,
                    entry_period=entry_period,
                    entry_wp=entry_wp,
                    exit_type="target", exit_wp=S4A_TARGET, pnl=pnl,
                )
            if wp_i <= S4A_STOP:
                entry_fee = maker_fee(CONTRACTS, entry_wp)
                exit_fee = taker_fee(CONTRACTS, S4A_STOP)
                pnl = (S4A_STOP - entry_wp) * CONTRACTS - entry_fee - exit_fee
                return S4AResult(
                    game_id=game.game_id, entered=True,
                    entry_elapsed=entry_elapsed,
                    entry_period=entry_period,
                    entry_wp=entry_wp,
                    exit_type="stop", exit_wp=S4A_STOP, pnl=pnl,
                )
    # End of observations without hitting target/stop
    if not entered:
        return S4AResult(game_id=game.game_id, entered=False)

    # Resolution: use final fav_wp (≥ 0.95 = win, ≤ 0.05 = loss, else mid)
    final_wp = obs[-1][2]
    entry_fee = maker_fee(CONTRACTS, entry_wp)
    if final_wp >= 0.95:
        resolution = 1.0
        exit_type = "resolution_win"
        exit_fee = 0.0
    elif final_wp <= 0.05:
        resolution = 0.0
        exit_type = "resolution_loss"
        exit_fee = 0.0
    else:
        resolution = float(final_wp)
        exit_type = "resolution_mid"
        exit_fee = maker_fee(CONTRACTS, resolution)
    pnl = (resolution - entry_wp) * CONTRACTS - entry_fee - exit_fee
    return S4AResult(
        game_id=game.game_id, entered=True,
        entry_elapsed=entry_elapsed,
        entry_period=entry_period,
        entry_wp=entry_wp,
        exit_type=exit_type, exit_wp=resolution, pnl=pnl,
    )


# ---- Metric primitives -------------------------------------------------

def price_range(series: np.ndarray) -> float:
    return float(series.max() - series.min()) if len(series) else 0.0


def zigzag_swings(series: np.ndarray, threshold: float = SWING_THRESHOLD) -> int:
    if len(series) < 2:
        return 0
    swings = 0
    best_high = float(series[0])
    best_low = float(series[0])
    trend = 0
    for i in range(1, len(series)):
        p = float(series[i])
        if trend == 1:
            if p > best_high:
                best_high = p
            elif best_high - p >= threshold:
                swings += 1
                trend = -1
                best_low = p
        elif trend == -1:
            if p < best_low:
                best_low = p
            elif p - best_low >= threshold:
                swings += 1
                trend = 1
                best_high = p
        else:
            if p >= best_low + threshold:
                swings += 1
                trend = 1
                best_high = p
            elif p <= best_high - threshold:
                swings += 1
                trend = -1
                best_low = p
            else:
                best_high = max(best_high, p)
                best_low = min(best_low, p)
    return swings


def count_050_crossings(series: np.ndarray) -> int:
    if len(series) < 2:
        return 0
    crosses = 0
    prev = float(series[0])
    for i in range(1, len(series)):
        p = float(series[i])
        if (prev < 0.5 and p >= 0.5) or (prev > 0.5 and p <= 0.5):
            crosses += 1
        prev = p
    return crosses


def crossed_050(series: np.ndarray) -> bool:
    return count_050_crossings(series) > 0


# ---- Section computations ---------------------------------------------

def section1_counts(team_games: dict[str, list[TeamGame]]) -> list[dict]:
    rows = []
    for team, tgs in team_games.items():
        n = len(tgs)
        n_fav = sum(1 for t in tgs if t.is_favorite)
        n_dog = n - n_fav
        fav_opens = [
            float(t.series[0]) for t in tgs if t.is_favorite and len(t.series) > 0
        ]
        dog_opens = [
            float(t.series[0]) for t in tgs if not t.is_favorite and len(t.series) > 0
        ]
        rows.append({
            "team": team,
            "is_playoff": team in PLAYOFF_SET,
            "games": n, "as_fav": n_fav, "as_dog": n_dog,
            "fav_pct": 100 * n_fav / n if n else 0.0,
            "mean_fav_open": (
                float(np.mean(fav_opens)) if fav_opens else 0.0
            ),
            "mean_dog_open": (
                float(np.mean(dog_opens)) if dog_opens else 0.0
            ),
        })
    return sorted(rows, key=lambda r: -r["games"])


def section2_volatility(
    team_games: dict[str, list[TeamGame]],
) -> dict:
    out = {}
    for team, tgs in team_games.items():
        out[team] = {}
        for role in ("fav", "dog"):
            role_tgs = [
                t for t in tgs
                if (role == "fav") == t.is_favorite
            ]
            ranges = [price_range(t.series) for t in role_tgs]
            swings = [zigzag_swings(t.series) for t in role_tgs]
            crosses = [count_050_crossings(t.series) for t in role_tgs]
            crossed_rate = (
                100 * sum(1 for t in role_tgs if crossed_050(t.series))
                / len(role_tgs) if role_tgs else 0.0
            )
            out[team][role] = {
                "games": len(role_tgs),
                "mean_range": float(np.mean(ranges)) if ranges else 0.0,
                "median_range": float(np.median(ranges)) if ranges else 0.0,
                "mean_swings": float(np.mean(swings)) if swings else 0.0,
                "mean_crosses": float(np.mean(crosses)) if crosses else 0.0,
                "crossed_rate_pct": crossed_rate,
            }
    return out


def section3a_s4a(
    team_games: dict[str, list[TeamGame]],
    s4a_by_gid: dict[str, S4AResult],
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        fav_tgs = [t for t in tgs if t.is_favorite]
        entries: list[S4AResult] = []
        for t in fav_tgs:
            r = s4a_by_gid.get(t.game.game_id)
            if r is not None and r.entered:
                entries.append(r)
        if not entries:
            out[team] = {
                "games": len(fav_tgs), "entries": 0,
                "n_hit": 0, "hit_pct": 0.0, "mean_pnl": 0.0,
                "by_venue": {}, "by_bucket": {},
            }
            continue
        n_hit = sum(1 for r in entries if r.exit_type == "target")
        pnls = [r.pnl for r in entries]
        out[team] = {
            "games": len(fav_tgs), "entries": len(entries),
            "n_hit": n_hit,
            "hit_pct": 100 * n_hit / len(entries),
            "mean_pnl": float(np.mean(pnls)),
        }
        by_venue: dict[str, dict] = {}
        for is_home in (True, False):
            venue_tgs = [t for t in fav_tgs if t.is_home == is_home]
            venue_entries = [
                s4a_by_gid[t.game.game_id] for t in venue_tgs
                if s4a_by_gid.get(t.game.game_id, S4AResult("", False)).entered
            ]
            lab = "home" if is_home else "away"
            if venue_entries:
                nh = sum(1 for r in venue_entries if r.exit_type == "target")
                by_venue[lab] = {
                    "games": len(venue_tgs),
                    "entries": len(venue_entries),
                    "n_hit": nh,
                    "hit_pct": 100 * nh / len(venue_entries),
                }
            else:
                by_venue[lab] = {
                    "games": len(venue_tgs),
                    "entries": 0, "n_hit": 0, "hit_pct": 0.0,
                }
        out[team]["by_venue"] = by_venue

        by_bucket: dict[str, dict] = {}
        for lab, lo, hi in SPREAD_BUCKETS_FAV:
            bucket_tgs = [t for t in fav_tgs if lo <= t.abs_spread <= hi]
            bucket_entries = [
                s4a_by_gid[t.game.game_id] for t in bucket_tgs
                if s4a_by_gid.get(t.game.game_id, S4AResult("", False)).entered
            ]
            if bucket_entries:
                nh = sum(1 for r in bucket_entries if r.exit_type == "target")
                by_bucket[lab] = {
                    "games": len(bucket_tgs),
                    "entries": len(bucket_entries),
                    "hit_pct": 100 * nh / len(bucket_entries),
                }
            else:
                by_bucket[lab] = {
                    "games": len(bucket_tgs),
                    "entries": 0, "hit_pct": 0.0,
                }
        out[team]["by_bucket"] = by_bucket
    return out


def section3b_collapse(
    team_games: dict[str, list[TeamGame]],
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        fav_tgs = [t for t in tgs if t.is_favorite]
        if not fav_tgs:
            out[team] = {
                "games": 0, "collapse_pct": 0.0,
                "home_pct": 0.0, "away_pct": 0.0,
            }
            continue
        def min_drop(t: TeamGame) -> bool:
            s = t.series
            return len(s) > 0 and float(s.min()) <= S4A_STOP
        c = sum(1 for t in fav_tgs if min_drop(t))
        home = [t for t in fav_tgs if t.is_home]
        away = [t for t in fav_tgs if not t.is_home]
        hc = sum(1 for t in home if min_drop(t))
        ac = sum(1 for t in away if min_drop(t))
        out[team] = {
            "games": len(fav_tgs),
            "collapse_pct": 100 * c / len(fav_tgs),
            "home_pct": 100 * hc / len(home) if home else 0.0,
            "away_pct": 100 * ac / len(away) if away else 0.0,
        }
    return out


def section3c_upset(
    team_games: dict[str, list[TeamGame]],
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        dog_tgs = [t for t in tgs if not t.is_favorite]
        if not dog_tgs:
            out[team] = {
                "games": 0, "wins": 0, "upset_pct": 0.0,
                "home_pct": 0.0, "away_pct": 0.0,
            }
            continue
        wins = sum(1 for t in dog_tgs if t.team_won)
        home = [t for t in dog_tgs if t.is_home]
        away = [t for t in dog_tgs if not t.is_home]
        hw = sum(1 for t in home if t.team_won)
        aw = sum(1 for t in away if t.team_won)
        out[team] = {
            "games": len(dog_tgs), "wins": wins,
            "upset_pct": 100 * wins / len(dog_tgs),
            "home_pct": 100 * hw / len(home) if home else 0.0,
            "away_pct": 100 * aw / len(away) if away else 0.0,
        }
    return out


def section3d_dog_peak(
    team_games: dict[str, list[TeamGame]],
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        dog_tgs = [t for t in tgs if not t.is_favorite]
        if not dog_tgs:
            out[team] = {
                "games": 0, "mean_peak": 0.0,
                "peak_50_pct": 0.0, "peak_65_pct": 0.0,
            }
            continue
        peaks = [
            float(t.series.max()) for t in dog_tgs if len(t.series) > 0
        ]
        if not peaks:
            out[team] = {
                "games": len(dog_tgs), "mean_peak": 0.0,
                "peak_50_pct": 0.0, "peak_65_pct": 0.0,
            }
            continue
        out[team] = {
            "games": len(dog_tgs),
            "mean_peak": float(np.mean(peaks)),
            "peak_50_pct": 100 * sum(1 for p in peaks if p >= 0.50) / len(peaks),
            "peak_65_pct": 100 * sum(1 for p in peaks if p >= 0.65) / len(peaks),
        }
    return out


def section4_period(
    team_games: dict[str, list[TeamGame]],
    s4a_by_gid: dict[str, S4AResult],
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        fav_tgs = [t for t in tgs if t.is_favorite]
        by_period: dict[int, list[S4AResult]] = {1: [], 2: [], 3: [], 4: []}
        for t in fav_tgs:
            r = s4a_by_gid.get(t.game.game_id)
            if r is None or not r.entered:
                continue
            p = r.entry_period
            if p in (1, 2, 3, 4):
                by_period[p].append(r)
        out[team] = {}
        for q, entries in by_period.items():
            if not entries:
                out[team][q] = {"entries": 0, "hit_pct": 0.0}
                continue
            nh = sum(1 for r in entries if r.exit_type == "target")
            out[team][q] = {
                "entries": len(entries),
                "hit_pct": 100 * nh / len(entries),
            }
    return out


def binomial_ci_wilson(
    successes: int, trials: int, alpha: float = 0.05,
) -> tuple[float, float]:
    if trials == 0:
        return (0.0, 100.0)
    z = 1.96
    p = successes / trials
    denom = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2)) / denom
    return (100 * (center - half), 100 * (center + half))


def assign_tiers(s3a: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for team, s in s3a.items():
        if s["entries"] == 0:
            out[team] = "—"
            continue
        hp = s["hit_pct"]
        if hp >= 60:
            out[team] = "Tier 1"
        elif hp >= 45:
            out[team] = "Tier 2"
        else:
            out[team] = "Tier 3"
    return out


def filtered_aggregate(
    s3a: dict, team_games: dict[str, list[TeamGame]],
    s4a_by_gid: dict[str, S4AResult], tiers: dict[str, str],
    allowed_tiers: set[str], label: str, scale_games: float = 1230 * (549 / 1234),
) -> dict:
    games_in: set[str] = set()
    entries: list[S4AResult] = []
    for team, tgs in team_games.items():
        if tiers.get(team) not in allowed_tiers:
            continue
        for tg in tgs:
            if not tg.is_favorite:
                continue
            r = s4a_by_gid.get(tg.game.game_id)
            if r is None or not r.entered:
                games_in.add(tg.game.game_id)
                continue
            games_in.add(tg.game.game_id)
            entries.append(r)
    if not entries:
        return {
            "universe": label, "games": len(games_in),
            "entries": 0, "hit_pct": 0.0,
            "mean_pnl": 0.0, "annual_ev": 0.0,
        }
    nh = sum(1 for r in entries if r.exit_type == "target")
    pnls = [r.pnl for r in entries]
    mean_pnl = float(np.mean(pnls))
    n_games = len(games_in) or 1
    epg = len(entries) / n_games
    annual_ev = mean_pnl * epg * scale_games
    return {
        "universe": label, "games": len(games_in),
        "entries": len(entries),
        "hit_pct": 100 * nh / len(entries),
        "mean_pnl": mean_pnl, "annual_ev": annual_ev,
    }


def spearman_rho(
    ranks_a: list[int], ranks_b: list[int],
) -> tuple[float, float]:
    """Return (rho, approximate p-value one-sided H1:rho>0)."""
    n = len(ranks_a)
    if n < 3 or len(ranks_b) != n:
        return 0.0, 1.0
    a = np.array(ranks_a, dtype=float)
    b = np.array(ranks_b, dtype=float)
    d = a - b
    rho = 1 - 6 * (d ** 2).sum() / (n * (n * n - 1))
    # Approximate p-value via t-distribution
    if abs(rho) >= 1.0:
        return float(rho), 0.0
    try:
        tstat = rho * math.sqrt((n - 2) / (1 - rho * rho))
    except ZeroDivisionError:
        return float(rho), 1.0
    # Two-sided normal approximation for simplicity
    # (rough — for small n, use t-dist; for n=16 this is acceptable)
    from math import erf, sqrt
    p_two = 2 * (1 - 0.5 * (1 + erf(abs(tstat) / sqrt(2))))
    return float(rho), float(p_two)


def compute_outliers(
    section2: dict, s3a: dict, s3b: dict, s3c: dict, s3d: dict,
) -> list[dict]:
    metrics: list[tuple[str, dict[str, float]]] = []
    for role in ("fav", "dog"):
        metrics.append((
            f"mean_range_{role}",
            {t: d[role]["mean_range"] for t, d in section2.items()
             if d[role]["games"] >= 5},
        ))
        metrics.append((
            f"mean_swings_{role}",
            {t: d[role]["mean_swings"] for t, d in section2.items()
             if d[role]["games"] >= 5},
        ))
        metrics.append((
            f"crossed_050_pct_{role}",
            {t: d[role]["crossed_rate_pct"] for t, d in section2.items()
             if d[role]["games"] >= 5},
        ))
    metrics.append((
        "s4a_hit_pct",
        {t: s["hit_pct"] for t, s in s3a.items() if s["entries"] >= 10},
    ))
    metrics.append((
        "collapse_pct",
        {t: s["collapse_pct"] for t, s in s3b.items() if s["games"] >= 5},
    ))
    metrics.append((
        "upset_pct",
        {t: s["upset_pct"] for t, s in s3c.items() if s["games"] >= 5},
    ))
    metrics.append((
        "dog_mean_peak",
        {t: s["mean_peak"] for t, s in s3d.items() if s["games"] >= 5},
    ))
    outliers: list[dict] = []
    for mname, values in metrics:
        if len(values) < 5:
            continue
        arr = np.array(list(values.values()))
        mean = float(arr.mean())
        std = float(arr.std(ddof=1))
        if std == 0:
            continue
        for team, v in values.items():
            z = (v - mean) / std
            if abs(z) >= 1.5:
                outliers.append({
                    "team": team, "metric": mname,
                    "value": v, "mean": mean, "z_score": z,
                    "direction": "HIGH" if z > 0 else "LOW",
                })
    return sorted(outliers, key=lambda r: -abs(r["z_score"]))


def cluster_teams(
    section2: dict, s3a: dict, s3b: dict, s3c: dict,
) -> dict[str, str]:
    out: dict[str, str] = {}
    feats: dict[str, dict] = {}
    for team in section2:
        hit = s3a[team]["hit_pct"] if s3a[team]["entries"] >= 5 else None
        feats[team] = {
            "range_fav": section2[team]["fav"]["mean_range"],
            "swings_fav": section2[team]["fav"]["mean_swings"],
            "cross_fav": section2[team]["fav"]["crossed_rate_pct"],
            "s4a_hit": hit,
            "collapse": s3b[team]["collapse_pct"],
            "upset": s3c[team]["upset_pct"],
        }
    def med(key):
        vals = [f[key] for f in feats.values() if f[key] is not None]
        return float(np.median(vals)) if vals else 0.0
    med_range = med("range_fav")
    med_swings = med("swings_fav")
    med_s4a = med("s4a_hit")
    med_collapse = med("collapse")
    med_upset = med("upset")
    for team, f in feats.items():
        label = "Uncategorized"
        hi_vol = f["range_fav"] > med_range and f["swings_fav"] > med_swings
        lo_vol = f["range_fav"] < med_range and f["swings_fav"] < med_swings
        if hi_vol and f["cross_fav"] > 30:
            label = "Volatile oscillator"
        elif f["s4a_hit"] is not None and f["s4a_hit"] >= 60 and f["collapse"] < med_collapse:
            label = "Steady dominator"
        elif f["upset"] > med_upset and f["s4a_hit"] is not None and f["s4a_hit"] < med_s4a:
            label = "Scrappy underdog"
        elif lo_vol:
            label = "Low-volatility favorite"
        out[team] = label
    return out


def home_away_asymmetry(s3a: dict) -> list[dict]:
    out = []
    for team, s in s3a.items():
        if s["entries"] < 10:
            continue
        by = s.get("by_venue", {})
        home = by.get("home", {})
        away = by.get("away", {})
        if home.get("entries", 0) < 5 or away.get("entries", 0) < 5:
            continue
        out.append({
            "team": team,
            "home_hit": home["hit_pct"], "home_n": home["entries"],
            "away_hit": away["hit_pct"], "away_n": away["entries"],
            "delta": home["hit_pct"] - away["hit_pct"],
        })
    return sorted(out, key=lambda r: -abs(r["delta"]))


def period_standouts(s4: dict) -> list[dict]:
    out = []
    for team, periods in s4.items():
        for q, s in periods.items():
            if s["entries"] < 5:
                continue
            out.append({
                "team": team, "period": q,
                "entries": s["entries"], "hit_pct": s["hit_pct"],
            })
    return out


# ---- Report rendering --------------------------------------------------

def render_report(
    n_games: int,
    section1: list[dict], section2: dict,
    s3a: dict, s3b: dict, s3c: dict, s3d: dict,
    s4: dict, tiers: dict[str, str],
    filtered_evs: list[dict],
    outliers: list[dict], clusters: dict[str, str],
    asymmetries: list[dict], period_rows: list[dict],
    rank_comparison: list[dict], spearman_info: dict,
    pooled_hit_pct: float,
) -> str:
    md: list[str] = []
    md.append("# Team Profiles — Full-Season ESPN WP Validation\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Full-season profile on **{n_games} games** from the 2025-26 "
        "ESPN WP dataset (all 30 NBA teams). Companion to "
        "`team_profiles_playoff16.md` (404-game Kalshi dataset, "
        "playoff 16 only). Primary goal: validate the team-level "
        "S4A hit rate dispersion observed on Kalshi against a 3× "
        "sample via Spearman's rank correlation.\n"
    )
    md.append(
        "\n**Calibration caveat.** ESPN WP is systematically more "
        "reactive than Kalshi at the tails (+8.30pp at 0.20–0.40 "
        "WP, −2.73pp at 0.80–1.00 WP — from "
        "`wp_vs_kalshi_aggregate.md`). Absolute S4A hit rates, "
        "entry counts, and P&L on ESPN data are **NOT** directly "
        "comparable to Kalshi. The validation target is the "
        "**rank order** of team hit rates between the two datasets.\n"
    )
    md.append(
        f"\n**Pooled ESPN S4A hit rate on this dataset:** "
        f"{pooled_hit_pct:.1f}%. Kalshi pooled was 52.4%. The gap "
        "reflects the ESPN reactivity — interpret Δ-vs-pooled at "
        "ESPN-pooled-level, not Kalshi-pooled.\n"
    )

    # Section 1
    md.append("\n## Section 1 — Team game counts and role distribution\n\n")
    md.append(
        "★ = playoff 16. Sorted by game count.\n\n"
        "| Team | ★ | Games | As fav | As dog | Fav % | Mean fav open | Mean dog open |\n"
        "|---|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for r in section1:
        star = "★" if r["is_playoff"] else ""
        md.append(
            f"| {r['team']} | {star} | {r['games']} | "
            f"{r['as_fav']} | {r['as_dog']} | {r['fav_pct']:.1f}% | "
            f"{r['mean_fav_open']:.3f} | "
            f"{r['mean_dog_open']:.3f} |\n"
        )

    # Section 2
    md.append("\n## Section 2 — In-game volatility profiles (WP scale)\n")
    md.append("\n### 2A/B/C — Range, swings, $0.50 crossover (combined)\n\n")
    md.append(
        "| Team | ★ | Role | Games | Mean range | Mean swings | Cross 0.50 % |\n"
        "|---|---|---|---:|---:|---:|---:|\n"
    )
    all_teams_sorted = [r["team"] for r in section1]
    for team in all_teams_sorted:
        star = "★" if team in PLAYOFF_SET else ""
        for role in ("fav", "dog"):
            s = section2[team][role]
            if s["games"] == 0:
                continue
            md.append(
                f"| {team} | {star} | {role} | {s['games']} | "
                f"{s['mean_range']:.3f} | {s['mean_swings']:.2f} | "
                f"{s['crossed_rate_pct']:.1f}% |\n"
            )

    # Section 3A — the headline
    md.append("\n## Section 3 — Recovery and collapse profiles\n")
    md.append(
        "\n### 3A. S4A hit rate per team (as favorite) — all 30 teams\n\n"
    )
    md.append(
        "Teams ranked by ESPN hit %. For the 16 playoff teams, the "
        "Kalshi rank from `team_profiles_playoff16.md` is shown for "
        "direct comparison. Δ vs pooled is relative to the ESPN "
        f"pooled rate {pooled_hit_pct:.1f}%.\n\n"
        "| ESPN rank | Team | ★ | As-fav | S4A entries | Hit % | Mean P&L | Δ vs pooled | Kalshi rank | Rank Δ |\n"
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    # Sort by hit pct; include only teams with ≥ 1 entry
    eligible = [
        (team, s) for team, s in s3a.items()
        if s["entries"] >= 1
    ]
    eligible.sort(key=lambda kv: -kv[1]["hit_pct"])
    for espn_rank, (team, s) in enumerate(eligible, 1):
        star = "★" if team in PLAYOFF_SET else ""
        kalshi_rank = KALSHI_RANK.get(team, "—")
        rank_delta = (
            kalshi_rank - espn_rank if isinstance(kalshi_rank, int) else "—"
        )
        delta_pooled = s["hit_pct"] - pooled_hit_pct
        md.append(
            f"| {espn_rank} | {team} | {star} | {s['games']} | "
            f"{s['entries']} | {s['hit_pct']:.1f}% | "
            f"${s['mean_pnl']:+.2f} | {delta_pooled:+.1f}pp | "
            f"{kalshi_rank} | "
            f"{rank_delta:+d}" if isinstance(rank_delta, int) else
            f"| {espn_rank} | {team} | {star} | {s['games']} | "
            f"{s['entries']} | {s['hit_pct']:.1f}% | "
            f"${s['mean_pnl']:+.2f} | {delta_pooled:+.1f}pp | "
            f"{kalshi_rank} | —"
        )
        md.append(" |\n")

    # Spearman rank comparison
    md.append("\n### Spearman rank-order correlation (playoff 16)\n\n")
    md.append(
        f"ρ = **{spearman_info['rho']:+.3f}**, "
        f"approx p-value = {spearman_info['p_value']:.4f}. "
        f"Verdict: **{spearman_info['verdict']}**.\n"
    )
    md.append(
        "\nTeams ordered by Kalshi rank. ESPN rank is the team's "
        "position in the ESPN-pooled hit-rate ordering (1 = highest). "
        "For teams that did not fire any S4A entry on ESPN, rank is —.\n\n"
        "| Kalshi rank | Team | Kalshi hit% | ESPN hit% | ESPN rank | Rank Δ (K-E) |\n"
        "|---:|---|---:|---:|---:|---:|\n"
    )
    for row in rank_comparison:
        rd = row["rank_delta"]
        rd_str = f"{rd:+d}" if rd is not None else "—"
        espn_rank_str = (
            str(row["espn_rank"]) if row["espn_rank"] is not None else "—"
        )
        espn_hit_str = (
            f"{row['espn_hit']:.1f}%" if row["espn_hit"] is not None else "—"
        )
        md.append(
            f"| {row['kalshi_rank']} | {row['team']} | "
            f"{row['kalshi_hit']:.1f}% | "
            f"{espn_hit_str} | {espn_rank_str} | {rd_str} |\n"
        )

    # Sub-split: home vs away
    md.append("\n#### 3A sub-split: home vs away (playoff teams only)\n\n")
    md.append(
        "| Team | Venue | Entries | Hit % |\n"
        "|---|---|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        s = s3a.get(team, {})
        if not s or s.get("entries", 0) == 0:
            continue
        for venue in ("home", "away"):
            v = s["by_venue"].get(venue, {})
            if v.get("entries", 0) == 0:
                continue
            md.append(
                f"| {team} | {venue} | {v['entries']} | "
                f"{v['hit_pct']:.1f}% |\n"
            )

    # Sub-split: spread
    md.append("\n#### 3A sub-split: spread magnitude (playoff teams only)\n\n")
    md.append(
        "| Team | Spread | Entries | Hit % |\n"
        "|---|---|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        s = s3a.get(team, {})
        if not s or s.get("entries", 0) == 0:
            continue
        for lab, _, _ in SPREAD_BUCKETS_FAV:
            b = s["by_bucket"].get(lab, {})
            if b.get("entries", 0) == 0:
                continue
            md.append(
                f"| {team} | {lab} | {b['entries']} | "
                f"{b['hit_pct']:.1f}% |\n"
            )

    # 3B
    md.append(
        "\n### 3B. Collapse rate as favorite (fav WP drops ≤ 0.40)\n\n"
    )
    md.append(
        "| Team | ★ | As-fav games | Collapse % | Home % | Away % |\n"
        "|---|---|---:|---:|---:|---:|\n"
    )
    for team in all_teams_sorted:
        star = "★" if team in PLAYOFF_SET else ""
        s = s3b.get(team, {})
        if not s or s.get("games", 0) == 0:
            continue
        md.append(
            f"| {team} | {star} | {s['games']} | "
            f"{s['collapse_pct']:.1f}% | "
            f"{s['home_pct']:.1f}% | {s['away_pct']:.1f}% |\n"
        )

    # 3C
    md.append("\n### 3C. Upset rate as underdog\n\n")
    pooled_upsets = sum(s["wins"] for s in s3c.values())
    pooled_dg = sum(s["games"] for s in s3c.values())
    pool_up_pct = 100 * pooled_upsets / pooled_dg if pooled_dg else 0.0
    md.append(
        f"Pooled upset rate across all 30 teams: {pool_up_pct:.1f}% "
        f"({pooled_upsets}/{pooled_dg}).\n\n"
        "| Team | ★ | As-dog | Wins | Upset % | Home % | Away % | Δ vs pooled |\n"
        "|---|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for team in all_teams_sorted:
        star = "★" if team in PLAYOFF_SET else ""
        s = s3c.get(team, {})
        if not s or s.get("games", 0) == 0:
            continue
        md.append(
            f"| {team} | {star} | {s['games']} | {s['wins']} | "
            f"{s['upset_pct']:.1f}% | "
            f"{s['home_pct']:.1f}% | {s['away_pct']:.1f}% | "
            f"{s['upset_pct'] - pool_up_pct:+.1f}pp |\n"
        )

    # 3D
    md.append("\n### 3D. Underdog peak WP\n\n")
    md.append(
        "| Team | ★ | As-dog games | Mean peak | Peak ≥ 0.50 % | Peak ≥ 0.65 % |\n"
        "|---|---|---:|---:|---:|---:|\n"
    )
    for team in all_teams_sorted:
        star = "★" if team in PLAYOFF_SET else ""
        s = s3d.get(team, {})
        if not s or s.get("games", 0) == 0:
            continue
        md.append(
            f"| {team} | {star} | {s['games']} | "
            f"{s['mean_peak']:.3f} | "
            f"{s['peak_50_pct']:.1f}% | "
            f"{s['peak_65_pct']:.1f}% |\n"
        )

    # Section 4
    md.append("\n## Section 4 — Period-specific S4A tendencies\n\n")
    md.append(
        "| Team | ★ | Q1 n | Q1 hit% | Q2 n | Q2 hit% | Q3 n | Q3 hit% | Q4 n | Q4 hit% | Dom Q |\n"
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n"
    )
    for team in all_teams_sorted:
        star = "★" if team in PLAYOFF_SET else ""
        periods = s4.get(team, {})
        total = sum(s["entries"] for s in periods.values())
        if total == 0:
            continue
        max_q = max(periods, key=lambda q: periods[q]["entries"])
        cells = [f"| {team} | {star} |"]
        for q in (1, 2, 3, 4):
            s = periods[q]
            if s["entries"] == 0:
                cells.append(" 0 | — |")
            else:
                cells.append(f" {s['entries']} | {s['hit_pct']:.1f}% |")
        cells.append(f" Q{max_q} |\n")
        md.append("".join(cells))

    # Section 5
    md.append("\n## Section 5 — Summary scorecards\n")

    # 5A tier list
    md.append("\n### 5A. S4A tier list (all 30 teams)\n\n")
    md.append(
        "- **Tier 1** (≥60%), **Tier 2** (45-59%), **Tier 3** (<45%)\n\n"
        "| Tier | Team | ★ | Entries | Hit % | Mean P&L |\n"
        "|---|---|---|---:|---:|---:|\n"
    )
    for tier in ("Tier 1", "Tier 2", "Tier 3", "—"):
        team_list = [t for t, tt in tiers.items() if tt == tier]
        team_list.sort(key=lambda t: -s3a[t]["hit_pct"])
        for team in team_list:
            star = "★" if team in PLAYOFF_SET else ""
            s = s3a[team]
            md.append(
                f"| {tier} | {team} | {star} | {s['entries']} | "
                f"{s['hit_pct']:.1f}% | "
                f"${s['mean_pnl']:+.2f} |\n"
            )

    # 5B CIs
    md.append("\n### 5B. Sample-size CIs (95% Wilson)\n\n")
    md.append(
        f"Pooled ESPN hit rate: {pooled_hit_pct:.1f}%. "
        f"Significance is vs this ESPN-pooled rate.\n\n"
        "| Team | ★ | Entries | Hit % | CI low | CI high | Significant vs pooled? |\n"
        "|---|---|---:|---:|---:|---:|---|\n"
    )
    for team in all_teams_sorted:
        star = "★" if team in PLAYOFF_SET else ""
        s = s3a.get(team, {})
        if not s or s.get("entries", 0) == 0:
            continue
        lo, hi = binomial_ci_wilson(s["n_hit"], s["entries"])
        if hi < pooled_hit_pct:
            sig = "yes (below)"
        elif lo > pooled_hit_pct:
            sig = "yes (above)"
        else:
            sig = "no"
        md.append(
            f"| {team} | {star} | {s['entries']} | "
            f"{s['hit_pct']:.1f}% | {lo:.1f}% | {hi:.1f}% | {sig} |\n"
        )

    # 5C filter
    md.append("\n### 5C. If-we-filtered S4A aggregate EV\n\n")
    md.append(
        "Only trades where the favorite team is in the specified "
        "universe. ESPN-scale P&L — not directly comparable to "
        "Kalshi.\n\n"
        "| Universe | Games | Entries | Hit % | Mean P&L | Annual EV (ESPN-scale) |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    for f in filtered_evs:
        md.append(
            f"| {f['universe']} | {f['games']} | "
            f"{f['entries']} | {f['hit_pct']:.1f}% | "
            f"${f['mean_pnl']:+.2f} | ${f['annual_ev']:+,.0f} |\n"
        )

    # 5D Kalshi ↔ ESPN validation
    md.append(
        "\n### 5D. Kalshi ↔ ESPN validation summary (playoff 16)\n\n"
    )
    md.append(
        "| Team | Kalshi hit% | ESPN hit% | Kalshi tier | ESPN tier | Tier match? |\n"
        "|---|---:|---:|---|---|---|\n"
    )
    tier_matches = 0
    for team in PLAYOFF_TEAMS:
        k_hit = KALSHI_HIT_PCT[team]
        s = s3a.get(team, {})
        e_hit = s.get("hit_pct") if s.get("entries", 0) > 0 else None
        k_tier = KALSHI_TIER[team]
        e_tier = tiers.get(team, "—")
        match = "yes" if k_tier == e_tier else "no"
        if match == "yes":
            tier_matches += 1
        e_hit_str = f"{e_hit:.1f}%" if e_hit is not None else "—"
        md.append(
            f"| {team} | {k_hit:.1f}% | {e_hit_str} | "
            f"{k_tier} | {e_tier} | {match} |\n"
        )
    md.append(
        f"\n**Tier-match count:** {tier_matches}/16 "
        f"({100 * tier_matches / 16:.1f}%).\n"
    )
    md.append(
        f"\n**Spearman ρ (rank correlation):** "
        f"{spearman_info['rho']:+.3f} "
        f"(p ≈ {spearman_info['p_value']:.4f}).\n\n"
        f"**Verdict:** **{spearman_info['verdict']}**.\n"
    )
    # HOU-specific check
    hou_s = s3a.get("HOU", {})
    if hou_s.get("entries", 0) > 0:
        hou_lo, hou_hi = binomial_ci_wilson(
            hou_s["n_hit"], hou_s["entries"],
        )
        hou_sig = hou_hi < pooled_hit_pct
        md.append(
            "\n**HOU significance check:** ESPN HOU hit rate "
            f"{hou_s['hit_pct']:.1f}% on {hou_s['entries']} entries, "
            f"95% CI ({hou_lo:.1f}%, {hou_hi:.1f}%) vs ESPN pooled "
            f"{pooled_hit_pct:.1f}%. HOU is statistically "
            f"significantly below pooled: **{'yes' if hou_sig else 'no'}**.\n"
        )

    # Section 6
    md.append("\n## Section 6 — Data-driven pattern discovery\n")
    md.append("\n### 6A. Biggest outliers (all 30 teams, |Z| ≥ 1.5)\n\n")
    md.append(
        "| Team | ★ | Metric | Value | Mean | Z | Direction |\n"
        "|---|---|---|---:|---:|---:|---|\n"
    )
    for r in outliers[:25]:
        star = "★" if r["team"] in PLAYOFF_SET else ""
        md.append(
            f"| {r['team']} | {star} | {r['metric']} | "
            f"{r['value']:.3f} | {r['mean']:.3f} | "
            f"{r['z_score']:+.2f} | {r['direction']} |\n"
        )

    md.append("\n### 6B. Personality clusters (all 30 teams)\n\n")
    md.append(
        "| Team | ★ | Cluster |\n|---|---|---|\n"
    )
    cluster_counts: Counter = Counter()
    for team in all_teams_sorted:
        star = "★" if team in PLAYOFF_SET else ""
        cl = clusters.get(team, "Uncategorized")
        cluster_counts[cl] += 1
        md.append(f"| {team} | {star} | {cl} |\n")
    md.append(
        "\nCluster counts: "
        + ", ".join(f"{k}: {v}" for k, v in cluster_counts.most_common())
        + ".\n"
    )

    md.append("\n### 6C. Home-away asymmetry standouts\n\n")
    md.append(
        "Teams with min 5 entries in each venue, sorted by |Δ|.\n\n"
        "| Team | ★ | Home hit% | Away hit% | Δ | Home n | Away n |\n"
        "|---|---|---:|---:|---:|---:|---:|\n"
    )
    for r in asymmetries[:12]:
        star = "★" if r["team"] in PLAYOFF_SET else ""
        md.append(
            f"| {r['team']} | {star} | {r['home_hit']:.1f}% | "
            f"{r['away_hit']:.1f}% | "
            f"{r['delta']:+.1f}pp | "
            f"{r['home_n']} | {r['away_n']} |\n"
        )

    md.append(
        "\n### 6D. Period-specific standouts (min 5 entries)\n\n"
    )
    sorted_periods = sorted(period_rows, key=lambda r: -r["hit_pct"])
    md.append(
        "**Top 10 team × period by hit rate:**\n\n"
        "| Team | ★ | Period | Entries | Hit % |\n"
        "|---|---|---|---:|---:|\n"
    )
    for r in sorted_periods[:10]:
        star = "★" if r["team"] in PLAYOFF_SET else ""
        md.append(
            f"| {r['team']} | {star} | Q{r['period']} | "
            f"{r['entries']} | {r['hit_pct']:.1f}% |\n"
        )
    md.append(
        "\n**Bottom 10 team × period by hit rate:**\n\n"
        "| Team | ★ | Period | Entries | Hit % |\n"
        "|---|---|---|---:|---:|\n"
    )
    for r in sorted_periods[-10:]:
        star = "★" if r["team"] in PLAYOFF_SET else ""
        md.append(
            f"| {r['team']} | {star} | Q{r['period']} | "
            f"{r['entries']} | {r['hit_pct']:.1f}% |\n"
        )

    md.append(
        "\n---\n\nValidation analysis. Findings inform engine "
        "parameterization but do not constitute a new strategy.\n"
    )
    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading full-season ESPN WP + PBP dataset...")
    games = load_all_games()
    n_games = len(games)
    if n_games == 0:
        log("FAIL: no games loaded")
        return 2

    log("Running S4A on each game (elapsed-time trailing max)...")
    s4a_by_gid: dict[str, S4AResult] = {}
    for g in games:
        s4a_by_gid[g.game_id] = apply_s4a(g)
    n_entries = sum(1 for r in s4a_by_gid.values() if r.entered)
    n_hits = sum(
        1 for r in s4a_by_gid.values()
        if r.entered and r.exit_type == "target"
    )
    pooled_hit_pct = 100 * n_hits / n_entries if n_entries else 0.0
    log(
        f"  {n_entries} S4A entries total, pooled hit rate "
        f"{pooled_hit_pct:.1f}%"
    )

    log("Building per-team TeamGame lists...")
    team_games = build_team_games(games)
    log(f"  {len(team_games)} distinct teams")

    log("Sections 1-4 (counts, volatility, recovery, periods)...")
    s1 = section1_counts(team_games)
    s2 = section2_volatility(team_games)
    s3a = section3a_s4a(team_games, s4a_by_gid)
    s3b = section3b_collapse(team_games)
    s3c = section3c_upset(team_games)
    s3d = section3d_dog_peak(team_games)
    s4 = section4_period(team_games, s4a_by_gid)

    log("Sections 5-6 (tiers, CIs, filter EV, patterns)...")
    tiers = assign_tiers(s3a)
    filtered_evs = [
        filtered_aggregate(
            s3a, team_games, s4a_by_gid, tiers,
            {"Tier 1", "Tier 2", "Tier 3"}, "All 30 teams (baseline)",
        ),
        filtered_aggregate(
            s3a, team_games, s4a_by_gid, tiers,
            {"Tier 1"}, "Tier 1 only",
        ),
        filtered_aggregate(
            s3a, team_games, s4a_by_gid, tiers,
            {"Tier 1", "Tier 2"}, "Tier 3 excluded (= Tier 1 + 2)",
        ),
    ]
    outliers = compute_outliers(s2, s3a, s3b, s3c, s3d)
    clusters = cluster_teams(s2, s3a, s3b, s3c)
    asymmetries = home_away_asymmetry(s3a)
    period_rows = period_standouts(s4)

    log("Computing Spearman rank correlation for playoff 16...")
    # Build ESPN rank list restricted to playoff 16
    eligible = [
        (team, s) for team, s in s3a.items()
        if team in PLAYOFF_SET and s["entries"] >= 1
    ]
    eligible.sort(key=lambda kv: -kv[1]["hit_pct"])
    espn_rank_map: dict[str, int] = {
        team: rank for rank, (team, _) in enumerate(eligible, 1)
    }
    rank_comparison: list[dict] = []
    kalshi_ranks_paired: list[int] = []
    espn_ranks_paired: list[int] = []
    for team in PLAYOFF_TEAMS:
        k_rank = KALSHI_RANK[team]
        k_hit = KALSHI_HIT_PCT[team]
        e_rank = espn_rank_map.get(team)
        e_hit = (
            s3a[team]["hit_pct"]
            if s3a.get(team, {}).get("entries", 0) > 0 else None
        )
        if e_rank is not None:
            kalshi_ranks_paired.append(k_rank)
            espn_ranks_paired.append(e_rank)
            rank_delta = k_rank - e_rank
        else:
            rank_delta = None
        rank_comparison.append({
            "team": team, "kalshi_rank": k_rank, "kalshi_hit": k_hit,
            "espn_rank": e_rank, "espn_hit": e_hit,
            "rank_delta": rank_delta,
        })
    rho, p_value = spearman_rho(kalshi_ranks_paired, espn_ranks_paired)
    # Verdict logic
    if p_value < 0.05 and rho >= 0.5:
        verdict = "VALIDATED (ρ ≥ 0.5, p < 0.05)"
    elif rho < 0.3:
        verdict = "NOT VALIDATED (ρ < 0.3)"
    else:
        verdict = "INCONCLUSIVE (0.3 ≤ ρ < 0.5, or p ≥ 0.05)"
    spearman_info = {"rho": rho, "p_value": p_value, "verdict": verdict}
    log(
        f"  ρ = {rho:+.3f}, p = {p_value:.4f}, verdict: {verdict}"
    )

    log("Rendering report...")
    md = render_report(
        n_games=n_games, section1=s1, section2=s2,
        s3a=s3a, s3b=s3b, s3c=s3c, s3d=s3d, s4=s4,
        tiers=tiers, filtered_evs=filtered_evs,
        outliers=outliers, clusters=clusters,
        asymmetries=asymmetries, period_rows=period_rows,
        rank_comparison=rank_comparison,
        spearman_info=spearman_info,
        pooled_hit_pct=pooled_hit_pct,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
