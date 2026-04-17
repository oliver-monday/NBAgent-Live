"""
Phase 3A: ESPN WP bilateral dip + calibration analysis.

Replays the pilot (v2/v3) analyses against 2025-26 ESPN WP data with
pre-game spreads from nba_master_2025_26.csv.

Part 0 — Data loading + field discovery (self-documenting).
Part 1 — Bilateral dip frequency across universes and thresholds.
Part 2 — At-moment calibration by WP bucket (the key Strategy-2 test).
Part 3 — Team-level swing propensity.
Part 4 — Home/away dip asymmetry.

All output goes to stdout. Findings will be added to RESEARCH_LOG.md
only after manual review.

Data shape observed 2026-04-17:
  WP line:  {game_id, homeWinPercentage, tiePercentage, playId}
  PBP line: {game_id, id (joins to playId), homeScore, awayScore,
             period: {number, ...}, clock: {displayValue, ...}, ...}
  Master:   {game_id (int), home_team_abbrev, away_team_abbrev,
             home_score, away_score, home_spread, ...}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

MASTER_CSV = Path("data/nba_master_2025_26.csv")
WP_DIR = Path("data/espn_wp")
PBP_DIR = Path("data/pbp")

REG_PERIOD_SEC = 720       # 12-min regulation quarter
OT_PERIOD_SEC = 300        # 5-min OT period
REG_PERIODS = 4


# ---- Clock / period parsing --------------------------------------------

def parse_clock(clock_raw: Any) -> float:
    """Parse ESPN clock to seconds. Handles '12:00', '0:30.1', '30.4', '0.0',
    and the nested {'displayValue': '...'} variant."""
    if clock_raw is None:
        return np.nan
    if isinstance(clock_raw, dict):
        clock_raw = clock_raw.get("displayValue")
    if clock_raw is None:
        return np.nan
    s = str(clock_raw).strip()
    if ":" in s:
        parts = s.split(":")
        try:
            m = int(parts[0])
            sec = float(parts[1])
            return m * 60 + sec
        except ValueError:
            return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def extract_period_num(p: Any) -> Any:
    if isinstance(p, dict):
        return p.get("number")
    return p


def sec_rem_in_period(period, clock_sec):
    """Seconds remaining. Regulation: regulation time left.
    OT: within-current-period time left (OT length unknown a priori)."""
    if pd.isna(period) or pd.isna(clock_sec):
        return np.nan
    p = int(period)
    if p <= REG_PERIODS:
        return (REG_PERIODS - p) * REG_PERIOD_SEC + clock_sec
    return clock_sec


def elapsed_sec(period, clock_sec):
    """Seconds elapsed since tip-off. Monotone within a game."""
    if pd.isna(period) or pd.isna(clock_sec):
        return np.nan
    p = int(period)
    if p <= REG_PERIODS:
        return (p - 1) * REG_PERIOD_SEC + (REG_PERIOD_SEC - clock_sec)
    return (
        REG_PERIODS * REG_PERIOD_SEC
        + (p - REG_PERIODS - 1) * OT_PERIOD_SEC
        + (OT_PERIOD_SEC - clock_sec)
    )


# ---- File loading ------------------------------------------------------

def load_jsonl_glob(directory: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(directory.glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


# ---- Table-printing helpers -------------------------------------------

def _pct(x: float) -> str:
    if pd.isna(x):
        return "  nan"
    return f"{x*100:5.1f}%"


def print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ---- Part 1: Bilateral dip rates --------------------------------------

def bilateral_analysis(obs: pd.DataFrame, game_meta: pd.DataFrame,
                       thresholds=(0.20, 0.15, 0.10)) -> None:
    print_header("PART 1 — Bilateral dip rates")

    # Universes, each as boolean mask on game_meta.game_id
    universes = []
    universes.append(("All games", game_meta["game_id"]))
    sp6 = game_meta[game_meta["home_spread"].abs() <= 6]["game_id"]
    universes.append(("|spread|<=6", sp6))
    sp3 = game_meta[game_meta["home_spread"].abs() <= 3]["game_id"]
    universes.append(("|spread|<=3", sp3))
    m10 = game_meta[game_meta["final_margin"] <= 10]["game_id"]
    universes.append(("final_margin<=10", m10))
    m5 = game_meta[game_meta["final_margin"] <= 5]["game_id"]
    universes.append(("final_margin<=5", m5))
    ot = game_meta[game_meta["is_ot"]]["game_id"]
    universes.append(("OT games", ot))

    for window in (60, 180, 300):
        w = obs[obs["sec_rem"] >= window].dropna(subset=["home_wp", "away_wp"])
        if w.empty:
            print(f"\n--- window sec_rem>={window}: no data ---")
            continue

        # Per-game min home/away WP in window
        per_game = w.groupby("game_id").agg(
            min_home=("home_wp", "min"),
            min_away=("away_wp", "min"),
        ).reset_index()

        print(f"\n--- Tradeable window: sec_rem >= {window} sec ---")
        header = f"{'Threshold':>10s}  " + "  ".join(
            f"{name:>18s}" for name, _ in universes
        )
        print(header)

        for thr in thresholds:
            per_game[f"bilat_{thr}"] = (
                (per_game["min_home"] < thr) & (per_game["min_away"] < thr)
            )
            row_cells = [f"<{thr:.2f}   "]
            for name, gids in universes:
                sub = per_game[per_game["game_id"].isin(gids)]
                n = len(sub)
                if n == 0:
                    row_cells.append(f"{'—':>18s}")
                else:
                    rate = sub[f"bilat_{thr}"].mean()
                    row_cells.append(f"{rate*100:6.1f}% ({n:>4d})  ")
            print("  ".join(row_cells))

    # Timing separation for bilateral <0.20 in |spread|<=6, sec_rem>=60
    w = obs[obs["sec_rem"] >= 60].dropna(subset=["home_wp", "away_wp", "elapsed"])
    idx_home = w.groupby("game_id")["home_wp"].idxmin()
    idx_away = w.groupby("game_id")["away_wp"].idxmin()
    home_min = w.loc[idx_home, ["game_id", "home_wp", "elapsed"]].rename(
        columns={"home_wp": "min_home", "elapsed": "t_home_min"})
    away_min = w.loc[idx_away, ["game_id", "away_wp", "elapsed"]].rename(
        columns={"away_wp": "min_away", "elapsed": "t_away_min"})
    per_game = home_min.merge(away_min, on="game_id")
    per_game["separation_sec"] = (
        per_game["t_home_min"] - per_game["t_away_min"]).abs()

    # |spread|<=6 + bilateral <0.20
    bilat = per_game[per_game["game_id"].isin(sp6)]
    bilat = bilat[(bilat["min_home"] < 0.20) & (bilat["min_away"] < 0.20)]

    print("\n--- Timing separation (|spread|<=6, bilateral <0.20, sec_rem>=60) ---")
    if bilat.empty:
        print("  no bilateral games in this universe")
    else:
        sep = bilat["separation_sec"]
        print(f"  N games: {len(bilat)}")
        print(f"  median separation: {sep.median():.0f} sec "
              f"({sep.median()/60:.1f} min)")
        print(f"  p10 / p25 / p75 / p90: "
              f"{sep.quantile(0.10):.0f} / {sep.quantile(0.25):.0f} / "
              f"{sep.quantile(0.75):.0f} / {sep.quantile(0.90):.0f} sec")
        print(f"  fraction >= 5 min:  {(sep >= 300).mean()*100:.1f}%")
        print(f"  fraction >= 15 min: {(sep >= 900).mean()*100:.1f}%")
        print(f"  fraction <  3 min:  {(sep <  180).mean()*100:.1f}%  "
              "(tests §6.2 temporal clustering hypothesis)")

    # Comparison to pilot
    all_bilat = per_game.copy()
    all_bilat_rate = (
        (all_bilat["min_home"] < 0.20) & (all_bilat["min_away"] < 0.20)
    ).mean() * 100
    sp6_sub = per_game[per_game["game_id"].isin(sp6)]
    sp6_rate = (
        (sp6_sub["min_home"] < 0.20) & (sp6_sub["min_away"] < 0.20)
    ).mean() * 100
    m10_sub = per_game[per_game["game_id"].isin(m10)]
    m10_rate = (
        (m10_sub["min_home"] < 0.20) & (m10_sub["min_away"] < 0.20)
    ).mean() * 100

    print("\n--- Comparison to pilot (Stern-implied WP, 2024-25) ---")
    print(f"  Pilot:    bilat<0.20 = 30.0% (all), 42.5% (margin<=10)")
    print(f"  This run: bilat<0.20 = {all_bilat_rate:.1f}% (all), "
          f"{sp6_rate:.1f}% (|spread|<=6), {m10_rate:.1f}% (margin<=10)")


# ---- Part 2: At-moment calibration ------------------------------------

CALIB_BUCKETS = [0.0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20,
                 0.25, 0.35, 0.50]


def calibration_analysis(obs: pd.DataFrame, game_meta: pd.DataFrame) -> None:
    print_header("PART 2 — At-moment calibration (Stern residual against ESPN)")

    # Attach home_won to obs
    obs = obs.merge(game_meta[["game_id", "home_won"]], on="game_id", how="left")

    # Stack home + away perspectives
    home_rows = obs[["game_id", "sec_rem", "home_wp", "home_won"]].copy()
    home_rows.columns = ["game_id", "sec_rem", "wp", "won"]
    away_rows = obs[["game_id", "sec_rem", "away_wp", "home_won"]].copy()
    away_rows["away_won"] = ~away_rows["home_won"]
    away_rows = away_rows[["game_id", "sec_rem", "away_wp", "away_won"]]
    away_rows.columns = ["game_id", "sec_rem", "wp", "won"]

    stacked = pd.concat([home_rows, away_rows], ignore_index=True)
    stacked = stacked.dropna(subset=["wp", "won", "sec_rem"])

    for window in (60, 180, 300):
        sub = stacked[stacked["sec_rem"] >= window]
        if sub.empty:
            continue

        sub = sub.copy()
        sub["bucket"] = pd.cut(sub["wp"], bins=CALIB_BUCKETS, include_lowest=True,
                               right=True)
        agg = sub.groupby("bucket", observed=True).agg(
            n=("wp", "size"),
            mean_wp=("wp", "mean"),
            actual=("won", "mean"),
        )
        agg["residual_pp"] = (agg["actual"] - agg["mean_wp"]) * 100
        # EV per contract bought at mean WP (price = mean WP dollars,
        # payoff 1 if won): EV = actual - mean_wp as fraction.
        agg["ev_frac"] = agg["actual"] - agg["mean_wp"]

        print(f"\n--- At-moment calibration (sec_rem >= {window}) ---")
        print(f"{'bucket':<16s}  {'n':>7s}  {'mean WP':>8s}  "
              f"{'actual':>8s}  {'resid (pp)':>11s}  {'EV @ price':>10s}")
        for idx, row in agg.iterrows():
            print(
                f"{str(idx):<16s}  "
                f"{int(row['n']):>7,d}  "
                f"{row['mean_wp']:>8.3f}  "
                f"{row['actual']:>8.3f}  "
                f"{row['residual_pp']:>+10.1f}  "
                f"{row['ev_frac']*100:>+9.1f}%"
            )


# ---- Part 3: Team swing propensity ------------------------------------

def team_swing_analysis(obs: pd.DataFrame, game_meta: pd.DataFrame) -> None:
    print_header("PART 3 — Team-level swing propensity "
                 "(|spread|<=6, sec_rem>=60)")

    sp6_ids = set(game_meta[game_meta["home_spread"].abs() <= 6]["game_id"])
    w = obs[(obs["sec_rem"] >= 60) & (obs["game_id"].isin(sp6_ids))]
    if w.empty:
        print("  no data in |spread|<=6 universe")
        return
    # Per-game min home/away
    per_game = w.groupby("game_id").agg(
        min_home=("home_wp", "min"),
        min_away=("away_wp", "min"),
    ).reset_index()
    per_game = per_game.merge(
        game_meta[["game_id", "home_team_abbrev", "away_team_abbrev"]],
        on="game_id", how="left",
    )
    per_game["bilat_0_20"] = (per_game["min_home"] < 0.20) & (per_game["min_away"] < 0.20)

    # Build per-team rollup
    teams = set(game_meta["home_team_abbrev"]).union(game_meta["away_team_abbrev"])
    rows = []
    for team in teams:
        if pd.isna(team):
            continue
        home = per_game[per_game["home_team_abbrev"] == team]
        away = per_game[per_game["away_team_abbrev"] == team]
        any_ = per_game[(per_game["home_team_abbrev"] == team)
                        | (per_game["away_team_abbrev"] == team)]
        if len(any_) == 0:
            continue
        rows.append({
            "team": team,
            "games": len(any_),
            "home_games": len(home),
            "away_games": len(away),
            "bilat_0_20_rate": any_["bilat_0_20"].mean(),
            "home_min_wp_median": home["min_home"].median()
                if len(home) else np.nan,
            "away_min_wp_median": away["min_away"].median()
                if len(away) else np.nan,
        })
    teams_df = pd.DataFrame(rows).sort_values(
        "bilat_0_20_rate", ascending=False).reset_index(drop=True)

    print(f"\n{'Team':<5s} {'G':>4s} {'H':>3s} {'A':>3s} "
          f"{'Bilat<0.20':>11s} {'HomeMinWP(med)':>16s} "
          f"{'AwayMinWP(med)':>16s}")
    for _, r in teams_df.iterrows():
        print(
            f"{r['team']:<5s} "
            f"{int(r['games']):>4d} {int(r['home_games']):>3d} "
            f"{int(r['away_games']):>3d} "
            f"{r['bilat_0_20_rate']*100:>10.1f}% "
            f"{r['home_min_wp_median']:>15.3f} "
            f"{r['away_min_wp_median']:>15.3f}"
        )

    print(f"\nTop 5 swing-propensity (bilateral <0.20 involvement rate):")
    for _, r in teams_df.head(5).iterrows():
        print(f"  {r['team']}  {r['bilat_0_20_rate']*100:5.1f}%  "
              f"(n={int(r['games'])})")
    print(f"\nBottom 5 swing-propensity:")
    for _, r in teams_df.tail(5).iterrows():
        print(f"  {r['team']}  {r['bilat_0_20_rate']*100:5.1f}%  "
              f"(n={int(r['games'])})")


# ---- Part 4: Home/away asymmetry --------------------------------------

def homeaway_analysis(obs: pd.DataFrame, game_meta: pd.DataFrame) -> None:
    print_header("PART 4 — Home/Away dip asymmetry "
                 "(|spread|<=6, sec_rem>=60)")

    sp6_ids = set(game_meta[game_meta["home_spread"].abs() <= 6]["game_id"])
    w = obs[(obs["sec_rem"] >= 60) & (obs["game_id"].isin(sp6_ids))]
    per_game = w.groupby("game_id").agg(
        min_home=("home_wp", "min"),
        min_away=("away_wp", "min"),
    ).reset_index()
    if per_game.empty:
        print("  no data")
        return

    for thr in (0.20, 0.15, 0.10):
        h_rate = (per_game["min_home"] < thr).mean()
        a_rate = (per_game["min_away"] < thr).mean()
        ratio = a_rate / h_rate if h_rate > 0 else np.nan
        print(f"\n  Threshold <{thr:.2f}  (N games = {len(per_game)})")
        print(f"    Home-team dip rate: {h_rate*100:5.1f}%")
        print(f"    Away-team dip rate: {a_rate*100:5.1f}%")
        print(f"    Away/Home ratio:    {ratio:5.2f}x")

    print(f"\n  Median min WP:")
    print(f"    Home: {per_game['min_home'].median():.3f}")
    print(f"    Away: {per_game['min_away'].median():.3f}")


# ---- Part 0 + orchestration ------------------------------------------

def main() -> int:
    print("=" * 70)
    print("Phase 3A: ESPN WP bilateral dip + calibration analysis")
    print("=" * 70)

    # Load
    master = pd.read_csv(MASTER_CSV)
    master["game_id"] = master["game_id"].astype(str)

    print("\n--- Loading JSONL files ---")
    wp = load_jsonl_glob(WP_DIR)
    pbp = load_jsonl_glob(PBP_DIR)
    print(f"  master rows: {len(master):,}")
    print(f"  WP rows:     {len(wp):,}")
    print(f"  PBP rows:    {len(pbp):,}")

    print(f"\n  WP columns:  {sorted(wp.columns.tolist())}")
    print(f"  PBP columns: {sorted(pbp.columns.tolist())}")
    print(f"\n  WP sample row:  {dict(wp.iloc[0])}")

    # Parse PBP fields
    pbp["period_num"] = pbp["period"].apply(extract_period_num)
    pbp["clock_sec"] = pbp["clock"].apply(parse_clock)
    pbp["sec_rem"] = [sec_rem_in_period(p, c)
                     for p, c in zip(pbp["period_num"], pbp["clock_sec"])]
    pbp["elapsed"] = [elapsed_sec(p, c)
                     for p, c in zip(pbp["period_num"], pbp["clock_sec"])]

    # Join WP <- PBP on (game_id, playId==id)
    obs = wp.merge(
        pbp[["game_id", "id", "period_num", "clock_sec", "sec_rem",
             "elapsed", "homeScore", "awayScore"]],
        left_on=["game_id", "playId"], right_on=["game_id", "id"],
        how="inner",
    )
    obs = obs.rename(columns={"homeWinPercentage": "home_wp",
                              "tiePercentage": "tie_pct"})
    if "tie_pct" not in obs.columns:
        obs["tie_pct"] = 0.0
    obs["home_wp"] = pd.to_numeric(obs["home_wp"], errors="coerce")
    obs["tie_pct"] = pd.to_numeric(obs["tie_pct"], errors="coerce").fillna(0.0)
    obs["away_wp"] = 1.0 - obs["home_wp"] - obs["tie_pct"]

    # Build game-level metadata from master + PBP max period
    max_period = (pbp.groupby("game_id")["period_num"].max()
                    .reset_index()
                    .rename(columns={"period_num": "max_period"}))
    game_meta = master[["game_id", "home_team_abbrev", "away_team_abbrev",
                        "home_score", "away_score", "home_spread"]].copy()
    game_meta = game_meta.merge(max_period, on="game_id", how="left")
    # Need games with scraped WP — inner-filter to those with data
    scraped_gids = set(obs["game_id"].unique())
    game_meta = game_meta[game_meta["game_id"].isin(scraped_gids)].copy()

    game_meta["final_margin"] = (game_meta["home_score"]
                                 - game_meta["away_score"]).abs()
    game_meta["is_ot"] = game_meta["max_period"] > REG_PERIODS
    game_meta["home_won"] = game_meta["home_score"] > game_meta["away_score"]

    print("\n--- Post-join summary ---")
    print(f"  Observations: {len(obs):,}")
    print(f"  Games with WP:         {obs['game_id'].nunique():,}")
    print(f"  Games joined to master:{len(game_meta):,}")
    print(f"  Games with home_spread:{game_meta['home_spread'].notna().sum():,}")
    print(f"  OT games:              {game_meta['is_ot'].sum():,}")
    print(f"  Home WP null count:    {obs['home_wp'].isna().sum():,}")
    print(f"  sec_rem null count:    {obs['sec_rem'].isna().sum():,}")

    if len(game_meta) < 50:
        print("\n*** WARNING: fewer than 50 games — results are PRELIMINARY ***")

    # Run analyses
    bilateral_analysis(obs, game_meta)
    calibration_analysis(obs, game_meta)
    team_swing_analysis(obs, game_meta)
    homeaway_analysis(obs, game_meta)

    print("\n" + "=" * 70)
    print("Phase 3A analysis complete.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
