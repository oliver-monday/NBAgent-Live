"""Team-level in-game Kalshi price profiles for the 16 playoff teams.

Observational scouting report. No strategy simulation at the
aggregate level — the headline question is whether S4A's pooled
52-53% hit rate has meaningful team-level dispersion that could
serve as a live-engine filter.

Sections:
  1. Game counts + role (fav/dog) distribution.
  2. In-game volatility profiles (range, swings, $0.50 cross,
     spread × team breakdown, opponent-quality split).
  3. Recovery profile (S4A hit rate per team) + collapse + upset
     + underdog peak.
  4. Period-specific S4A tendencies.
  5. Tier list, CIs, and if-we-filtered EV.
  6. Data-driven pattern discovery (outliers, clusters,
     home/away asymmetry, period standouts).

Run:
    python -m analysis.team_profiles_playoff16
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    COMP_FRACTION,
    REG_SEASON_GAMES,
    S4AConfig,
    S4ATrade,
    _precompute_trailing_max,
    load_kalshi_games_all_spreads,
    simulate_s4a,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MATCHED_CSV = REPO_ROOT / "data" / "wp_kalshi_paired" / "matched_games.csv"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "team_profiles_playoff16.md"
)

PLAYOFF_TEAMS: list[str] = [
    # East
    "DET", "BOS", "NYK", "CLE", "TOR", "ATL", "PHI", "ORL",
    # West
    "OKC", "SAS", "DEN", "LAL", "HOU", "MIN", "POR", "PHX",
]
PLAYOFF_SET = set(PLAYOFF_TEAMS)

# S4A config from STRATEGY4_SPEC.md §3
S4A_CFG = S4AConfig(
    lookback_sec=180, dip_depth=0.08,
    entry_lo=0.50, entry_hi=0.75,
    exit_target=0.90, stop_loss=0.40,
)
S4A_POOLED_HIT = 52.4   # 404-game baseline (from replay validation)

SPREAD_BUCKETS_FAV: list[tuple[str, float, float]] = [
    ("small (1-3)", 1.0, 3.0),
    ("medium (3.5-6)", 3.5, 6.0),
    ("large (6.5+)", 6.5, float("inf")),
]

SWING_THRESHOLD = 0.10
ROLE_COMBOS = [
    ("fav", True), ("fav", False), ("dog", True), ("dog", False),
]


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


# ---- Data loading ------------------------------------------------------

@dataclass
class GameMeta:
    ticker: str
    espn_game_id: str
    home_team: str
    away_team: str
    home_spread: float          # negative = home favored
    abs_spread: float
    fav_team: str
    dog_team: str
    winner_team: str            # determined from final fav_vwap
    fav_series: np.ndarray
    dog_series: np.ndarray
    period_series: np.ndarray
    game_secs_series: np.ndarray


@dataclass
class TeamGame:
    """One game × one focal team (can be home or away, fav or dog)."""
    game: GameMeta
    team: str                   # focal team
    opp: str
    is_home: bool
    is_favorite: bool
    series: np.ndarray          # team-centric YES bid trajectory
    opp_series: np.ndarray

    @property
    def role(self) -> str:
        return "fav" if self.is_favorite else "dog"

    @property
    def venue(self) -> str:
        return "home" if self.is_home else "away"

    @property
    def team_won(self) -> bool:
        return self.team == self.game.winner_team


def _fav_team_from_spread(
    home_team: str, away_team: str, home_spread: float,
    fav_series: np.ndarray,
) -> tuple[str, str]:
    """Determine fav and dog team names. Home_spread < 0 → home favored.
    Pick'em games (spread=0) fall back to early Kalshi opening price."""
    if home_spread < 0:
        return home_team, away_team
    if home_spread > 0:
        return away_team, home_team
    # Pick'em: use first non-NaN Kalshi observation
    first = None
    for v in fav_series[:20]:
        if not np.isnan(v) and v > 0.05:
            first = float(v)
            break
    if first is None or first >= 0.5:
        return home_team, away_team
    return away_team, home_team


def load_games() -> list[GameMeta]:
    """Load 404-game dataset + join with matched_games for team info."""
    meta_df = pd.read_csv(MATCHED_CSV)
    meta_df["home_spread"] = pd.to_numeric(
        meta_df["home_spread"], errors="coerce",
    )
    meta_df["abs_spread"] = pd.to_numeric(
        meta_df["abs_spread"], errors="coerce",
    )
    meta_map = {
        str(r.kalshi_event_ticker): r for r in meta_df.itertuples()
    }

    games_raw = load_kalshi_games_all_spreads()
    out: list[GameMeta] = []
    for g in games_raw:
        row = meta_map.get(g["ticker"])
        if row is None:
            continue
        fav_series = g["ts"]["fav_kalshi_vwap"].values.astype(float)
        dog_series = 1.0 - fav_series
        # Winner via final fav_vwap
        final = float(fav_series[-1])
        if final >= 0.95:
            fav_won = True
        elif final <= 0.05:
            fav_won = False
        else:
            continue  # unresolved — skip
        home_spread = (
            float(row.home_spread)
            if not pd.isna(row.home_spread) else 0.0
        )
        fav_team, dog_team = _fav_team_from_spread(
            str(row.home_team), str(row.away_team),
            home_spread, fav_series,
        )
        winner_team = fav_team if fav_won else dog_team
        period_series = (
            g["ts"]["period"].values.astype(float)
            if "period" in g["ts"].columns
            else np.full(len(fav_series), np.nan)
        )
        gs_series = (
            g["ts"]["game_seconds_elapsed"].values.astype(float)
            if "game_seconds_elapsed" in g["ts"].columns
            else np.full(len(fav_series), np.nan)
        )
        out.append(GameMeta(
            ticker=g["ticker"], espn_game_id=str(g["espn_game_id"]),
            home_team=str(row.home_team), away_team=str(row.away_team),
            home_spread=home_spread,
            abs_spread=float(g["abs_spread"]),
            fav_team=fav_team, dog_team=dog_team,
            winner_team=winner_team,
            fav_series=fav_series, dog_series=dog_series,
            period_series=period_series,
            game_secs_series=gs_series,
        ))
    return out


def build_team_games(games: list[GameMeta]) -> dict[str, list[TeamGame]]:
    """For each playoff team, emit TeamGames for games in which that
    team plays (home or away)."""
    out: dict[str, list[TeamGame]] = {t: [] for t in PLAYOFF_TEAMS}
    for g in games:
        for team_name, opp_name, is_home in [
            (g.home_team, g.away_team, True),
            (g.away_team, g.home_team, False),
        ]:
            if team_name not in PLAYOFF_SET:
                continue
            is_fav = (team_name == g.fav_team)
            series = g.fav_series if is_fav else g.dog_series
            opp_series = g.dog_series if is_fav else g.fav_series
            out[team_name].append(TeamGame(
                game=g, team=team_name, opp=opp_name,
                is_home=is_home, is_favorite=is_fav,
                series=series, opp_series=opp_series,
            ))
    return out


# ---- Metric primitives -------------------------------------------------

def price_range(series: np.ndarray) -> float:
    return float(series.max() - series.min())


def zigzag_swings(series: np.ndarray, threshold: float = SWING_THRESHOLD) -> int:
    """Count confirmed trough↔peak reversals of ≥ threshold."""
    if len(series) < 2:
        return 0
    swings = 0
    best_high = float(series[0])
    best_low = float(series[0])
    trend = 0
    for i in range(1, len(series)):
        p = float(series[i])
        if np.isnan(p):
            continue
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
    """Number of times series crosses $0.50."""
    if len(series) < 2:
        return 0
    crosses = 0
    prev = float(series[0])
    for i in range(1, len(series)):
        p = float(series[i])
        if (prev < 0.50 and p >= 0.50) or (prev > 0.50 and p <= 0.50):
            crosses += 1
        prev = p
    return crosses


def crossed_050(series: np.ndarray) -> bool:
    return count_050_crossings(series) > 0


# ---- Section 1 --------------------------------------------------------

def section1_counts(team_games: dict[str, list[TeamGame]]) -> list[dict]:
    rows: list[dict] = []
    for team, tgs in team_games.items():
        n = len(tgs)
        n_fav = sum(1 for t in tgs if t.is_favorite)
        n_dog = n - n_fav
        fav_opens = [
            float(t.game.fav_series[0]) for t in tgs if t.is_favorite
        ]
        dog_opens = [
            float(t.game.dog_series[0]) for t in tgs if not t.is_favorite
        ]
        rows.append({
            "team": team, "games": n,
            "as_fav": n_fav, "as_dog": n_dog,
            "fav_pct": 100 * n_fav / n if n else 0.0,
            "mean_fav_open": (
                float(np.mean(fav_opens)) if fav_opens else 0.0
            ),
            "mean_dog_open": (
                float(np.mean(dog_opens)) if dog_opens else 0.0
            ),
        })
    return sorted(rows, key=lambda r: -r["games"])


# ---- Section 2 --------------------------------------------------------

def section2_volatility(
    team_games: dict[str, list[TeamGame]],
) -> dict:
    """Compute per-team × role metrics. Returns nested dict."""
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        out[team] = {}
        for role in ("fav", "dog"):
            role_tgs = [t for t in tgs if t.role == role]
            # Aggregate across venue
            ranges = [price_range(t.series) for t in role_tgs]
            swings_all = [zigzag_swings(t.series) for t in role_tgs]
            crosses_all = [count_050_crossings(t.series) for t in role_tgs]
            crossed_rate = (
                100 * sum(1 for t in role_tgs if crossed_050(t.series))
                / len(role_tgs)
                if role_tgs else 0.0
            )
            out[team][role] = {
                "games": len(role_tgs),
                "mean_range": (
                    float(np.mean(ranges)) if ranges else 0.0
                ),
                "median_range": (
                    float(np.median(ranges)) if ranges else 0.0
                ),
                "p25_range": (
                    float(np.quantile(ranges, 0.25)) if ranges else 0.0
                ),
                "p75_range": (
                    float(np.quantile(ranges, 0.75)) if ranges else 0.0
                ),
                "mean_swings": (
                    float(np.mean(swings_all)) if swings_all else 0.0
                ),
                "median_swings": (
                    float(np.median(swings_all)) if swings_all else 0.0
                ),
                "mean_crosses": (
                    float(np.mean(crosses_all)) if crosses_all else 0.0
                ),
                "crossed_rate_pct": crossed_rate,
                "by_venue": {},
            }
            for is_home in (True, False):
                venue_tgs = [t for t in role_tgs if t.is_home == is_home]
                venue_label = "home" if is_home else "away"
                if not venue_tgs:
                    out[team][role]["by_venue"][venue_label] = {
                        "games": 0, "mean_range": 0.0,
                        "mean_swings": 0.0, "crossed_rate_pct": 0.0,
                    }
                    continue
                rr = [price_range(t.series) for t in venue_tgs]
                sw = [zigzag_swings(t.series) for t in venue_tgs]
                cr = sum(1 for t in venue_tgs if crossed_050(t.series))
                out[team][role]["by_venue"][venue_label] = {
                    "games": len(venue_tgs),
                    "mean_range": float(np.mean(rr)),
                    "mean_swings": float(np.mean(sw)),
                    "crossed_rate_pct": 100 * cr / len(venue_tgs),
                }
    return out


def section2d_spread_buckets(
    team_games: dict[str, list[TeamGame]],
) -> dict[str, dict[str, dict]]:
    """Per-team as-favorite split by |spread| bucket."""
    out: dict[str, dict[str, dict]] = {}
    for team, tgs in team_games.items():
        fav_tgs = [t for t in tgs if t.is_favorite]
        buckets: dict[str, list[TeamGame]] = {
            lab: [] for lab, _, _ in SPREAD_BUCKETS_FAV
        }
        for t in fav_tgs:
            for lab, lo, hi in SPREAD_BUCKETS_FAV:
                if lo <= t.game.abs_spread <= hi:
                    buckets[lab].append(t)
                    break
        out[team] = {}
        for lab, _, _ in SPREAD_BUCKETS_FAV:
            bs = buckets[lab]
            if not bs:
                out[team][lab] = {
                    "games": 0, "mean_range": 0.0,
                    "mean_swings": 0.0, "mean_peak": 0.0,
                }
                continue
            out[team][lab] = {
                "games": len(bs),
                "mean_range": float(np.mean(
                    [price_range(t.series) for t in bs]
                )),
                "mean_swings": float(np.mean(
                    [zigzag_swings(t.series) for t in bs]
                )),
                "mean_peak": float(np.mean(
                    [float(t.series.max()) for t in bs]
                )),
            }
    return out


def section2e_opponent_split(
    team_games: dict[str, list[TeamGame]],
    s4a_by_ticker: dict[str, list[S4ATrade]],
) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for team, tgs in team_games.items():
        playoff_opp = [t for t in tgs if t.opp in PLAYOFF_SET]
        non_playoff = [t for t in tgs if t.opp not in PLAYOFF_SET]
        out[team] = {}
        for label, group in [
            ("playoff", playoff_opp), ("non-playoff", non_playoff),
        ]:
            if not group:
                out[team][label] = {
                    "games": 0, "mean_range": 0.0,
                    "mean_swings": 0.0, "s4a_entries": 0,
                }
                continue
            s4a_count = sum(
                1 for t in group if t.is_favorite
                for _ in s4a_by_ticker.get(t.game.ticker, [])
            )
            out[team][label] = {
                "games": len(group),
                "mean_range": float(np.mean(
                    [price_range(t.series) for t in group]
                )),
                "mean_swings": float(np.mean(
                    [zigzag_swings(t.series) for t in group]
                )),
                "s4a_entries": s4a_count,
            }
    return out


# ---- Section 3 (S4A per-team + collapse + upset + dog peak) -----------

def run_s4a_on_all(games: list[GameMeta]) -> dict[str, list[S4ATrade]]:
    """Run S4A simulation and return trades grouped by event ticker."""
    # Wrap games in the structure simulate_s4a expects
    games_struct = [
        {
            "ticker": g.ticker,
            "abs_spread": g.abs_spread,
            "ts": pd.DataFrame({
                "fav_kalshi_vwap": g.fav_series,
                "period": g.period_series,
                "game_seconds_elapsed": g.game_secs_series,
            }),
        }
        for g in games
    ]
    precomp: dict[tuple[str, int], np.ndarray] = {}
    lb_bins = max(1, int(S4A_CFG.lookback_sec / BUCKET_SEC))
    for g in games_struct:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp[(g["ticker"], lb_bins)] = (
            _precompute_trailing_max(fav, lb_bins)
        )
    trades = simulate_s4a(games_struct, S4A_CFG, precomp)
    out: dict[str, list[S4ATrade]] = {}
    for t in trades:
        out.setdefault(t.ticker, []).append(t)
    return out


def section3a_s4a_per_team(
    team_games: dict[str, list[TeamGame]],
    s4a_by_ticker: dict[str, list[S4ATrade]],
) -> dict:
    per_team: dict[str, dict] = {}
    for team, tgs in team_games.items():
        fav_tgs = [t for t in tgs if t.is_favorite]
        entries: list[S4ATrade] = []
        for t in fav_tgs:
            entries.extend(s4a_by_ticker.get(t.game.ticker, []))
        if not entries:
            per_team[team] = {
                "games": len(fav_tgs), "entries": 0,
                "n_hit": 0, "hit_pct": 0.0,
                "mean_pnl": 0.0,
            }
            continue
        n_hit = sum(1 for e in entries if e.exit_type == "target")
        pnls = [e.net_pnl for e in entries]
        per_team[team] = {
            "games": len(fav_tgs), "entries": len(entries),
            "n_hit": n_hit,
            "hit_pct": 100 * n_hit / len(entries),
            "mean_pnl": float(np.mean(pnls)),
        }

        # By venue
        by_venue: dict[str, dict] = {}
        for is_home in (True, False):
            venue_tgs = [t for t in fav_tgs if t.is_home == is_home]
            venue_entries: list[S4ATrade] = []
            for t in venue_tgs:
                venue_entries.extend(s4a_by_ticker.get(t.game.ticker, []))
            lab = "home" if is_home else "away"
            if venue_entries:
                nh = sum(1 for e in venue_entries if e.exit_type == "target")
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
        per_team[team]["by_venue"] = by_venue

        # By spread bucket
        by_bucket: dict[str, dict] = {}
        for lab, lo, hi in SPREAD_BUCKETS_FAV:
            bucket_tgs = [
                t for t in fav_tgs
                if lo <= t.game.abs_spread <= hi
            ]
            bucket_entries: list[S4ATrade] = []
            for t in bucket_tgs:
                bucket_entries.extend(s4a_by_ticker.get(t.game.ticker, []))
            if bucket_entries:
                nh = sum(
                    1 for e in bucket_entries
                    if e.exit_type == "target"
                )
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
        per_team[team]["by_bucket"] = by_bucket
    return per_team


def section3b_collapse(
    team_games: dict[str, list[TeamGame]],
) -> dict[str, dict]:
    """As-favorite games where team's price drops below $0.40."""
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        fav_tgs = [t for t in tgs if t.is_favorite]
        if not fav_tgs:
            out[team] = {
                "games": 0, "collapse_pct": 0.0,
                "home_pct": 0.0, "away_pct": 0.0,
            }
            continue
        collapsed = sum(
            1 for t in fav_tgs if float(t.series.min()) <= 0.40
        )
        home_tgs = [t for t in fav_tgs if t.is_home]
        away_tgs = [t for t in fav_tgs if not t.is_home]
        home_coll = sum(
            1 for t in home_tgs if float(t.series.min()) <= 0.40
        )
        away_coll = sum(
            1 for t in away_tgs if float(t.series.min()) <= 0.40
        )
        out[team] = {
            "games": len(fav_tgs),
            "collapse_pct": 100 * collapsed / len(fav_tgs),
            "home_pct": (
                100 * home_coll / len(home_tgs) if home_tgs else 0.0
            ),
            "away_pct": (
                100 * away_coll / len(away_tgs) if away_tgs else 0.0
            ),
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
        home_tgs = [t for t in dog_tgs if t.is_home]
        away_tgs = [t for t in dog_tgs if not t.is_home]
        home_wins = sum(1 for t in home_tgs if t.team_won)
        away_wins = sum(1 for t in away_tgs if t.team_won)
        out[team] = {
            "games": len(dog_tgs), "wins": wins,
            "upset_pct": 100 * wins / len(dog_tgs),
            "home_pct": (
                100 * home_wins / len(home_tgs) if home_tgs else 0.0
            ),
            "away_pct": (
                100 * away_wins / len(away_tgs) if away_tgs else 0.0
            ),
        }
    return out


def section3d_dog_rally(
    team_games: dict[str, list[TeamGame]],
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        dog_tgs = [t for t in tgs if not t.is_favorite]
        if not dog_tgs:
            out[team] = {
                "games": 0, "mean_peak": 0.0,
                "peak_50_pct": 0.0, "peak_65_pct": 0.0,
                "home_mean_peak": 0.0, "away_mean_peak": 0.0,
            }
            continue
        peaks = [float(t.series.max()) for t in dog_tgs]
        home_peaks = [
            float(t.series.max()) for t in dog_tgs if t.is_home
        ]
        away_peaks = [
            float(t.series.max()) for t in dog_tgs if not t.is_home
        ]
        out[team] = {
            "games": len(dog_tgs),
            "mean_peak": float(np.mean(peaks)),
            "peak_50_pct": 100 * sum(1 for p in peaks if p >= 0.50) / len(peaks),
            "peak_65_pct": 100 * sum(1 for p in peaks if p >= 0.65) / len(peaks),
            "home_mean_peak": (
                float(np.mean(home_peaks)) if home_peaks else 0.0
            ),
            "away_mean_peak": (
                float(np.mean(away_peaks)) if away_peaks else 0.0
            ),
        }
    return out


# ---- Section 4: period tendencies -------------------------------------

def section4_period(
    team_games: dict[str, list[TeamGame]],
    s4a_by_ticker: dict[str, list[S4ATrade]],
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for team, tgs in team_games.items():
        fav_tgs = [t for t in tgs if t.is_favorite]
        by_period: dict[int, list[S4ATrade]] = {1: [], 2: [], 3: [], 4: []}
        for t in fav_tgs:
            for e in s4a_by_ticker.get(t.game.ticker, []):
                if e.entry_period in (1, 2, 3, 4):
                    by_period[e.entry_period].append(e)
        out[team] = {}
        for q, entries in by_period.items():
            if not entries:
                out[team][q] = {"entries": 0, "hit_pct": 0.0}
                continue
            nh = sum(1 for e in entries if e.exit_type == "target")
            out[team][q] = {
                "entries": len(entries),
                "hit_pct": 100 * nh / len(entries),
            }
    return out


# ---- Section 5 --------------------------------------------------------

def binomial_ci(successes: int, trials: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score CI (better than normal for small n / extreme p)."""
    if trials == 0:
        return (0.0, 100.0)
    z = 1.96  # two-sided 95%
    p = successes / trials
    denom = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2)) / denom
    return (100 * (center - half), 100 * (center + half))


def assign_tiers(
    per_team: dict[str, dict],
) -> dict[str, str]:
    """Tier 1: hit ≥ 60%. Tier 2: 45-59%. Tier 3: < 45%. No entries → untiered."""
    out: dict[str, str] = {}
    for team, st in per_team.items():
        if st["entries"] == 0:
            out[team] = "—"
            continue
        hp = st["hit_pct"]
        if hp >= 60:
            out[team] = "Tier 1"
        elif hp >= 45:
            out[team] = "Tier 2"
        else:
            out[team] = "Tier 3"
    return out


def filtered_ev(
    per_team: dict[str, dict],
    team_games: dict[str, list[TeamGame]],
    s4a_by_ticker: dict[str, list[S4ATrade]],
    tier_of: dict[str, str],
    allowed_tiers: set[str],
    tier_label: str,
) -> dict:
    """Compute S4A aggregate for entries where the fav team is in
    allowed tiers. Pooled across the 404 games."""
    games_in_universe: set[str] = set()
    entries: list[S4ATrade] = []
    # A trade is in-universe iff the favorite team is a playoff team
    # in an allowed tier.
    for team, tgs in team_games.items():
        if tier_of.get(team) not in allowed_tiers:
            continue
        for tg in tgs:
            if not tg.is_favorite:
                continue
            games_in_universe.add(tg.game.ticker)
            entries.extend(s4a_by_ticker.get(tg.game.ticker, []))
    if not entries:
        return {
            "universe": tier_label,
            "games": len(games_in_universe),
            "entries": 0, "hit_pct": 0.0,
            "mean_pnl": 0.0, "annual_ev": 0.0,
        }
    n_hit = sum(1 for e in entries if e.exit_type == "target")
    pnls = [e.net_pnl for e in entries]
    mean_pnl = float(np.mean(pnls))
    n_games_total = len(team_games) and sum(
        1 for tg_list in team_games.values() for tg in tg_list
        if tg.is_favorite
    ) or 1
    # Annual EV: pool-level (mean × entries_per_game × 1230 × 0.445)
    n_games_in_universe = len(games_in_universe) or 1
    epg = len(entries) / n_games_in_universe
    annual = mean_pnl * epg * REG_SEASON_GAMES * COMP_FRACTION
    return {
        "universe": tier_label,
        "games": len(games_in_universe),
        "entries": len(entries),
        "hit_pct": 100 * n_hit / len(entries),
        "mean_pnl": mean_pnl,
        "annual_ev": annual,
    }


# ---- Section 6 --------------------------------------------------------

def compute_outliers(
    section2: dict, section3a: dict, section3b: dict,
    section3c: dict, section3d: dict,
) -> list[dict]:
    """Scan every team × metric, flag z-score ≥ 1.5."""
    metrics: list[tuple[str, dict[str, float]]] = []
    # From Section 2
    for role in ("fav", "dog"):
        metrics.append((
            f"mean_range_{role}",
            {team: d[role]["mean_range"] for team, d in section2.items()
             if d[role]["games"] >= 3},
        ))
        metrics.append((
            f"mean_swings_{role}",
            {team: d[role]["mean_swings"] for team, d in section2.items()
             if d[role]["games"] >= 3},
        ))
        metrics.append((
            f"crossed_050_pct_{role}",
            {team: d[role]["crossed_rate_pct"] for team, d in section2.items()
             if d[role]["games"] >= 3},
        ))
    # From Section 3
    metrics.append((
        "s4a_hit_pct",
        {team: s["hit_pct"] for team, s in section3a.items() if s["entries"] >= 5},
    ))
    metrics.append((
        "collapse_pct",
        {team: s["collapse_pct"] for team, s in section3b.items() if s["games"] >= 3},
    ))
    metrics.append((
        "upset_pct",
        {team: s["upset_pct"] for team, s in section3c.items() if s["games"] >= 3},
    ))
    metrics.append((
        "dog_mean_peak",
        {team: s["mean_peak"] for team, s in section3d.items() if s["games"] >= 3},
    ))
    outliers: list[dict] = []
    for metric_name, values in metrics:
        if len(values) < 4:
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
                    "team": team, "metric": metric_name,
                    "value": v, "mean": mean, "z_score": z,
                    "direction": "HIGH" if z > 0 else "LOW",
                })
    return sorted(outliers, key=lambda r: -abs(r["z_score"]))


def cluster_teams(
    section2: dict, section3a: dict, section3b: dict, section3c: dict,
) -> dict[str, str]:
    """Simple rule-based clustering on key metrics."""
    out: dict[str, str] = {}
    # Gather per-team features
    feats: dict[str, dict] = {}
    for team in PLAYOFF_TEAMS:
        feats[team] = {
            "range_fav": section2[team]["fav"]["mean_range"],
            "swings_fav": section2[team]["fav"]["mean_swings"],
            "cross_fav": section2[team]["fav"]["crossed_rate_pct"],
            "s4a_hit": section3a[team].get("hit_pct", 0.0) if section3a[team]["entries"] >= 5 else None,
            "collapse": section3b[team].get("collapse_pct", 0.0),
            "upset": section3c[team].get("upset_pct", 0.0),
        }
    # Compute medians for thresholding
    def med(key):
        vals = [v[key] for v in feats.values() if v[key] is not None]
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


def home_away_asymmetry(
    section3a: dict,
) -> list[dict]:
    out: list[dict] = []
    for team, s in section3a.items():
        if s["entries"] < 5:
            continue
        by_venue = s.get("by_venue", {})
        home = by_venue.get("home", {})
        away = by_venue.get("away", {})
        if home.get("entries", 0) < 3 or away.get("entries", 0) < 3:
            continue
        delta = home["hit_pct"] - away["hit_pct"]
        out.append({
            "team": team,
            "home_hit": home["hit_pct"], "home_n": home["entries"],
            "away_hit": away["hit_pct"], "away_n": away["entries"],
            "delta": delta,
        })
    return sorted(out, key=lambda r: -abs(r["delta"]))


def period_standouts(section4: dict) -> list[dict]:
    out: list[dict] = []
    for team, periods in section4.items():
        for q, s in periods.items():
            if s["entries"] < 3:
                continue
            out.append({
                "team": team, "period": q,
                "entries": s["entries"], "hit_pct": s["hit_pct"],
            })
    return out


# ---- Report rendering --------------------------------------------------

def render_report(
    games: list[GameMeta], team_games: dict[str, list[TeamGame]],
    section1: list[dict], section2: dict,
    section2d: dict, section2e: dict,
    section3a: dict, section3b: dict, section3c: dict,
    section3d: dict, section4: dict,
    tiers: dict[str, str], filtered_evs: list[dict],
    outliers: list[dict], clusters: dict[str, str],
    asymmetries: list[dict], period_rows: list[dict],
) -> str:
    md: list[str] = []
    md.append("# Team-Level In-Game Profiles — 2025-26 Playoff 16\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Observational scouting report on **{len(games)} games** "
        "from the Kalshi-confirmed paired dataset. For each of the "
        "16 teams in the 2025-26 NBA playoffs, characterizes "
        "in-game Kalshi price behavior as favorite and as underdog, "
        "then overlays S4A entry data to surface team-level hit "
        "rate dispersion.\n"
    )
    md.append(
        "\n**Teams:** " + ", ".join(PLAYOFF_TEAMS) + ".\n"
    )
    md.append(
        "\n**Data approximation:** dog-side YES bid is computed as "
        "`1 − fav_kalshi_vwap` (same as prior analyses). No "
        "strategy simulation at the aggregate level — this is a "
        "profile, not a strategy test.\n"
    )

    # Section 1
    md.append("\n## Section 1 — Game counts and role distribution\n")
    md.append(
        "| Team | Games | As fav | As dog | Fav % | Mean fav open | Mean dog open |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for r in section1:
        md.append(
            f"| {r['team']} | {r['games']} | {r['as_fav']} | "
            f"{r['as_dog']} | {r['fav_pct']:.1f}% | "
            f"${r['mean_fav_open']:.3f} | "
            f"${r['mean_dog_open']:.3f} |\n"
        )

    # Section 2
    md.append("\n## Section 2 — In-game volatility profiles\n")
    md.append("\n### 2A. Price range (max − min) per game\n\n")
    md.append(
        "| Team | Role | Games | Mean range | Median | P25 | P75 |\n"
        "|---|---|---:|---:|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        for role in ("fav", "dog"):
            s = section2[team][role]
            if s["games"] == 0:
                continue
            md.append(
                f"| {team} | {role} | {s['games']} | "
                f"${s['mean_range']:.3f} | ${s['median_range']:.3f} | "
                f"${s['p25_range']:.3f} | ${s['p75_range']:.3f} |\n"
            )

    md.append("\n### 2B. Mean $0.10+ swings per game\n\n")
    md.append(
        "| Team | Role | Games | Mean swings | Median |\n"
        "|---|---|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        for role in ("fav", "dog"):
            s = section2[team][role]
            if s["games"] == 0:
                continue
            md.append(
                f"| {team} | {role} | {s['games']} | "
                f"{s['mean_swings']:.2f} | {s['median_swings']:.1f} |\n"
            )

    md.append("\n### 2C. $0.50 crossover rate\n\n")
    md.append(
        "| Team | Role | Games | Cross $0.50 % of games | Mean crossings/game |\n"
        "|---|---|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        for role in ("fav", "dog"):
            s = section2[team][role]
            if s["games"] == 0:
                continue
            md.append(
                f"| {team} | {role} | {s['games']} | "
                f"{s['crossed_rate_pct']:.1f}% | "
                f"{s['mean_crosses']:.2f} |\n"
            )

    md.append("\n### 2D. As-favorite spread magnitude breakdown\n\n")
    md.append(
        "| Team | Spread bucket | Games | Mean range | Mean swings | Mean peak |\n"
        "|---|---|---:|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        for lab, _, _ in SPREAD_BUCKETS_FAV:
            b = section2d[team][lab]
            if b["games"] == 0:
                continue
            md.append(
                f"| {team} | {lab} | {b['games']} | "
                f"${b['mean_range']:.3f} | "
                f"{b['mean_swings']:.2f} | "
                f"${b['mean_peak']:.3f} |\n"
            )

    md.append("\n### 2E. Opponent-quality split (playoff vs non-playoff opponent)\n\n")
    md.append(
        "| Team | Opp type | Games | Mean range | Mean swings | S4A entries |\n"
        "|---|---|---:|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        for label in ("playoff", "non-playoff"):
            s = section2e[team][label]
            if s["games"] == 0:
                continue
            md.append(
                f"| {team} | {label} | {s['games']} | "
                f"${s['mean_range']:.3f} | "
                f"{s['mean_swings']:.2f} | "
                f"{s['s4a_entries']} |\n"
            )

    # Section 3
    md.append("\n## Section 3 — Recovery and collapse profiles\n")
    md.append("\n### 3A. S4A hit rate per team (as favorite)\n\n")
    md.append(
        "This is the headline table. Teams sorted by hit %. Δ is "
        f"vs pooled {S4A_POOLED_HIT:.1f}%.\n\n"
        "| Team | As-fav games | S4A entries | Hit $0.90 | Hit % | Mean P&L | Δ vs pooled |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    sorted_s3a = sorted(
        section3a.items(), key=lambda kv: -kv[1]["hit_pct"],
    )
    for team, s in sorted_s3a:
        if s["entries"] == 0:
            md.append(
                f"| {team} | {s['games']} | 0 | 0 | — | — | — |\n"
            )
            continue
        delta = s["hit_pct"] - S4A_POOLED_HIT
        md.append(
            f"| {team} | {s['games']} | {s['entries']} | "
            f"{s['n_hit']} | {s['hit_pct']:.1f}% | "
            f"${s['mean_pnl']:+.2f} | "
            f"{delta:+.1f}pp |\n"
        )

    md.append("\n#### 3A sub-split: home vs away\n\n")
    md.append(
        "| Team | Venue | As-fav games | Entries | Hit % | Δ vs pooled |\n"
        "|---|---|---:|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        s = section3a[team]
        if s["entries"] == 0:
            continue
        for venue in ("home", "away"):
            v = s["by_venue"][venue]
            if v["entries"] == 0:
                md.append(
                    f"| {team} | {venue} | {v['games']} | 0 | — | — |\n"
                )
                continue
            md.append(
                f"| {team} | {venue} | {v['games']} | "
                f"{v['entries']} | {v['hit_pct']:.1f}% | "
                f"{v['hit_pct'] - S4A_POOLED_HIT:+.1f}pp |\n"
            )

    md.append("\n#### 3A sub-split: spread magnitude\n\n")
    md.append(
        "| Team | Spread bucket | As-fav games | Entries | Hit % |\n"
        "|---|---|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        s = section3a[team]
        if s["entries"] == 0:
            continue
        for lab, _, _ in SPREAD_BUCKETS_FAV:
            b = s["by_bucket"][lab]
            if b["entries"] == 0:
                continue
            md.append(
                f"| {team} | {lab} | {b['games']} | "
                f"{b['entries']} | {b['hit_pct']:.1f}% |\n"
            )

    md.append("\n### 3B. As-favorite — collapse rate (price drops ≤ $0.40)\n\n")
    md.append(
        "| Team | As-fav games | Collapse % | Home % | Away % |\n"
        "|---|---:|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        s = section3b[team]
        if s["games"] == 0:
            continue
        md.append(
            f"| {team} | {s['games']} | {s['collapse_pct']:.1f}% | "
            f"{s['home_pct']:.1f}% | {s['away_pct']:.1f}% |\n"
        )

    md.append("\n### 3C. As-underdog — upset rate\n\n")
    pooled_upsets = sum(s["wins"] for s in section3c.values())
    pooled_dog_games = sum(s["games"] for s in section3c.values())
    pooled_upset_pct = (
        100 * pooled_upsets / pooled_dog_games if pooled_dog_games else 0.0
    )
    md.append(
        f"Pooled upset rate across the 16 teams' underdog games: "
        f"{pooled_upset_pct:.1f}% ({pooled_upsets}/{pooled_dog_games}).\n\n"
        "| Team | As-dog games | Wins | Upset % | Home dog % | Away dog % | Δ vs pooled |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        s = section3c[team]
        if s["games"] == 0:
            continue
        md.append(
            f"| {team} | {s['games']} | {s['wins']} | "
            f"{s['upset_pct']:.1f}% | "
            f"{s['home_pct']:.1f}% | "
            f"{s['away_pct']:.1f}% | "
            f"{s['upset_pct'] - pooled_upset_pct:+.1f}pp |\n"
        )

    md.append("\n### 3D. As-underdog — peak price reached\n\n")
    md.append(
        "| Team | As-dog games | Mean peak | Peak ≥ $0.50 % | Peak ≥ $0.65 % | Home peak | Away peak |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for team in PLAYOFF_TEAMS:
        s = section3d[team]
        if s["games"] == 0:
            continue
        md.append(
            f"| {team} | {s['games']} | "
            f"${s['mean_peak']:.3f} | "
            f"{s['peak_50_pct']:.1f}% | "
            f"{s['peak_65_pct']:.1f}% | "
            f"${s['home_mean_peak']:.3f} | "
            f"${s['away_mean_peak']:.3f} |\n"
        )

    # Section 4
    md.append("\n## Section 4 — Period-specific S4A tendencies (as favorite)\n")
    md.append(
        "| Team | Q1 n | Q1 hit% | Q2 n | Q2 hit% | Q3 n | Q3 hit% | Q4 n | Q4 hit% | Dominant Q |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n"
    )
    for team in PLAYOFF_TEAMS:
        periods = section4[team]
        total = sum(s["entries"] for s in periods.values())
        if total == 0:
            continue
        max_q = max(periods, key=lambda q: periods[q]["entries"])
        row = [f"| {team} |"]
        for q in (1, 2, 3, 4):
            s = periods[q]
            if s["entries"] == 0:
                row.append(" 0 | — |")
            else:
                row.append(f" {s['entries']} | {s['hit_pct']:.1f}% |")
        row.append(f" Q{max_q} |\n")
        md.append("".join(row))

    # Section 5
    md.append("\n## Section 5 — Summary scorecards and actionable output\n")
    md.append("\n### 5A. S4A tier list\n\n")
    md.append(
        "- **Tier 1** (strong buy): hit rate ≥ 60% (sig. above pooled 52.4%)\n"
        "- **Tier 2** (neutral): hit rate 45-59%\n"
        "- **Tier 3** (avoid): hit rate < 45%\n\n"
        "| Tier | Team | S4A entries | Hit % | Mean P&L |\n"
        "|---|---|---:|---:|---:|\n"
    )
    for tier in ("Tier 1", "Tier 2", "Tier 3", "—"):
        tier_teams = [
            team for team, t in tiers.items() if t == tier
        ]
        tier_teams.sort(
            key=lambda team: -section3a[team]["hit_pct"],
        )
        for team in tier_teams:
            s = section3a[team]
            if s["entries"] == 0:
                md.append(
                    f"| {tier} | {team} | 0 | — | — |\n"
                )
                continue
            md.append(
                f"| {tier} | {team} | {s['entries']} | "
                f"{s['hit_pct']:.1f}% | "
                f"${s['mean_pnl']:+.2f} |\n"
            )

    md.append("\n### 5B. Sample size caveat (95% Wilson CI on hit rate)\n\n")
    md.append(
        "| Team | Entries | Hit % | 95% CI low | 95% CI high | Significant vs pooled? |\n"
        "|---|---:|---:|---:|---:|---|\n"
    )
    for team in PLAYOFF_TEAMS:
        s = section3a[team]
        if s["entries"] == 0:
            continue
        lo, hi = binomial_ci(s["n_hit"], s["entries"])
        if hi < S4A_POOLED_HIT:
            sig = "yes (below pooled)"
        elif lo > S4A_POOLED_HIT:
            sig = "yes (above pooled)"
        else:
            sig = "no (CI spans pooled)"
        md.append(
            f"| {team} | {s['entries']} | {s['hit_pct']:.1f}% | "
            f"{lo:.1f}% | {hi:.1f}% | {sig} |\n"
        )

    md.append("\n### 5C. If-we-filtered S4A aggregate EV\n\n")
    md.append(
        "Only trades where the favorite team belongs to the "
        "specified universe. Note: the 'baseline' row here is the "
        "subset of the 404-game dataset where the favorite is a "
        "playoff team (not the full 404-game aggregate).\n\n"
        "| Universe | Games | Entries | Hit % | Mean P&L | Annual EV |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    for f in filtered_evs:
        md.append(
            f"| {f['universe']} | {f['games']} | "
            f"{f['entries']} | {f['hit_pct']:.1f}% | "
            f"${f['mean_pnl']:+.2f} | "
            f"${f['annual_ev']:+,.0f} |\n"
        )

    # Section 6
    md.append("\n## Section 6 — Data-driven pattern discovery\n")
    md.append("\n### 6A. Biggest team-level outliers (|Z| ≥ 1.5)\n\n")
    md.append(
        "| Team | Metric | Value | 16-team mean | Z-score | Direction |\n"
        "|---|---|---:|---:|---:|---|\n"
    )
    for r in outliers[:20]:
        md.append(
            f"| {r['team']} | {r['metric']} | "
            f"{r['value']:.3f} | {r['mean']:.3f} | "
            f"{r['z_score']:+.2f} | {r['direction']} |\n"
        )
    if not outliers:
        md.append("| (none) | — | — | — | — | — |\n")

    md.append("\n### 6B. Team \"personality\" clusters\n\n")
    md.append(
        "Rule-based clusters from favorite-side volatility + S4A hit "
        "+ collapse + underdog upset rate. Thresholds use the 16-team "
        "medians on each dimension. \"Uncategorized\" means the team "
        "doesn't fit cleanly into any cluster.\n\n"
        "| Team | Cluster |\n"
        "|---|---|\n"
    )
    cluster_counts: Counter = Counter()
    for team in PLAYOFF_TEAMS:
        label = clusters.get(team, "Uncategorized")
        cluster_counts[label] += 1
        md.append(f"| {team} | {label} |\n")
    md.append(
        "\nCluster counts: "
        + ", ".join(f"{k}: {v}" for k, v in cluster_counts.most_common())
        + ".\n"
    )

    md.append("\n### 6C. Home-away asymmetry standouts\n\n")
    md.append(
        "Teams with largest |hit-rate delta| between home-fav and "
        "away-fav S4A entries. Minimum 3 entries per venue.\n\n"
        "| Team | Home-fav hit % | Away-fav hit % | Δ | Home n | Away n |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    for r in asymmetries[:10]:
        md.append(
            f"| {r['team']} | {r['home_hit']:.1f}% | "
            f"{r['away_hit']:.1f}% | "
            f"{r['delta']:+.1f}pp | "
            f"{r['home_n']} | {r['away_n']} |\n"
        )

    md.append("\n### 6D. Period-specific standouts (min 3 entries)\n\n")
    sorted_periods = sorted(period_rows, key=lambda r: -r["hit_pct"])
    md.append(
        "**Top 5 team × period combinations by hit rate:**\n\n"
        "| Team | Period | Entries | Hit % |\n"
        "|---|---|---:|---:|\n"
    )
    for r in sorted_periods[:5]:
        md.append(
            f"| {r['team']} | Q{r['period']} | "
            f"{r['entries']} | {r['hit_pct']:.1f}% |\n"
        )
    md.append(
        "\n**Bottom 5 team × period combinations by hit rate:**\n\n"
        "| Team | Period | Entries | Hit % |\n"
        "|---|---|---:|---:|\n"
    )
    for r in sorted_periods[-5:]:
        md.append(
            f"| {r['team']} | Q{r['period']} | "
            f"{r['entries']} | {r['hit_pct']:.1f}% |\n"
        )

    md.append(
        "\n---\n\n**Report is observational.** Findings inform "
        "engine parameterization but do not constitute a new "
        "strategy. No STRATEGY_SPEC changes until findings are "
        "reviewed.\n"
    )
    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading + joining dataset with matched_games...")
    games = load_games()
    log(f"  {len(games)} games with resolvable outcome")

    log("Running S4A simulation across all games...")
    s4a_by_ticker = run_s4a_on_all(games)
    total_s4a = sum(len(v) for v in s4a_by_ticker.values())
    log(f"  {total_s4a} S4A entries across all games")

    log("Building TeamGame records for 16 playoff teams...")
    team_games = build_team_games(games)
    for t in PLAYOFF_TEAMS:
        log(f"  {t}: {len(team_games[t])} games")

    log("Section 1...")
    s1 = section1_counts(team_games)
    log("Section 2 (volatility)...")
    s2 = section2_volatility(team_games)
    s2d = section2d_spread_buckets(team_games)
    s2e = section2e_opponent_split(team_games, s4a_by_ticker)
    log("Section 3 (recovery/collapse/upset)...")
    s3a = section3a_s4a_per_team(team_games, s4a_by_ticker)
    s3b = section3b_collapse(team_games)
    s3c = section3c_upset(team_games)
    s3d = section3d_dog_rally(team_games)
    log("Section 4 (period tendencies)...")
    s4 = section4_period(team_games, s4a_by_ticker)

    log("Section 5 (tiers, CIs, filtered EV)...")
    tiers = assign_tiers(s3a)
    filtered_evs = [
        filtered_ev(s3a, team_games, s4a_by_ticker, tiers,
                    {"Tier 1", "Tier 2", "Tier 3"},
                    "All 16 teams (baseline)"),
        filtered_ev(s3a, team_games, s4a_by_ticker, tiers,
                    {"Tier 1"}, "Tier 1 only"),
        filtered_ev(s3a, team_games, s4a_by_ticker, tiers,
                    {"Tier 1", "Tier 2"}, "Tier 1 + 2"),
        filtered_ev(s3a, team_games, s4a_by_ticker, tiers,
                    {"Tier 1", "Tier 2"},
                    "Tier 3 excluded (= Tier 1 + 2)"),
    ]
    log("Section 6 (patterns + clusters + asymmetry)...")
    outliers = compute_outliers(s2, s3a, s3b, s3c, s3d)
    clusters = cluster_teams(s2, s3a, s3b, s3c)
    asymmetries = home_away_asymmetry(s3a)
    period_rows = period_standouts(s4)

    log("Rendering report...")
    md = render_report(
        games=games, team_games=team_games,
        section1=s1, section2=s2, section2d=s2d, section2e=s2e,
        section3a=s3a, section3b=s3b, section3c=s3c, section3d=s3d,
        section4=s4,
        tiers=tiers, filtered_evs=filtered_evs,
        outliers=outliers, clusters=clusters,
        asymmetries=asymmetries, period_rows=period_rows,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
