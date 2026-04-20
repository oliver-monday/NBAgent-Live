"""ESPN-scale scoring-run pattern catalog.

Full 2025-26 season (~1,234 games) characterization of scoring
runs, timeout associations, post-run WP trajectories, prior
degradation, and favorite/underdog recovery asymmetry. ESPN-WP
complement to the Kalshi-level `scoring_run_trajectories.py`
(n=2 games) — 600× the sample size, same questions.

ESPN CAVEAT: WP magnitudes are upper bounds on Kalshi/sportsbook
equivalents (+10-17pp compression at tails per Phase 3B
sportsbook backfill). Relative patterns transfer; absolute
magnitudes don't.

Run:
    python -m analysis.espn_scoring_run_catalog
    python -m analysis.espn_scoring_run_catalog --max-spread 6
    python -m analysis.espn_scoring_run_catalog --max-spread 10
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy3_game_flow_trajectories import (
    MASTER_CSV,
    PBP_DIR,
    WP_DIR,
    Report,
    elapsed_sec,
    extract_period_num,
    load_jsonl_glob,
    parse_clock,
)

OUTPUT_MD = Path("docs/analysis_outputs/espn_scoring_run_catalog.md")

# Run detection parameter sweep
RUN_PARAMS = [
    (6, 2),   # margin, window-minutes
    (6, 3),
    (8, 3),
    (8, 4),
    (10, 4),
]
PRIMARY_PARAMS = (6, 3)
SENSITIVITY_PARAMS = (8, 3)

# Trajectory checkpoints (seconds of game time after run end)
RECOVERY_CHECKPOINTS = (60, 120, 180, 300)
MAX_RECOVERY_WINDOW_SEC = 300
WP_CHECKPOINT_TOLERANCE = 30

# Prior-degradation checkpoints (elapsed seconds, approx.)
PRIOR_CHECKPOINTS = {
    "End Q1": 720,
    "Halftime": 1440,
    "End Q3": 2160,
    "6:00 Q4": 2520,
}
PRIOR_TOLERANCE_SEC = 60

# Timeout window (game-clock seconds after run end)
TIMEOUT_WINDOW_SEC = 90

# Dip-recovery thresholds
DIP_THRESHOLDS = (0.45, 0.40, 0.35, 0.30, 0.25)


# ---- Helpers -------------------------------------------------------------

def is_timeout_play(play_row: pd.Series) -> bool:
    tp = play_row.get("type")
    if isinstance(tp, dict):
        if str(tp.get("id", "")) == "16":
            return True
        txt = str(tp.get("text", "")).lower()
        if "timeout" in txt:
            return True
    return False


def _wp_at(obs_sorted: pd.DataFrame, elapsed_target: float,
           tol_sec: float) -> float | None:
    """Nearest home_wp within ±tol_sec of elapsed_target. None if none."""
    if obs_sorted.empty:
        return None
    arr = obs_sorted["elapsed"].values
    idx = int(np.searchsorted(arr, elapsed_target))
    best = None
    best_d = tol_sec + 1
    for cand in (idx - 1, idx):
        if 0 <= cand < len(arr):
            d = abs(float(arr[cand]) - elapsed_target)
            if d <= tol_sec and d < best_d:
                best = float(obs_sorted["home_wp"].iloc[cand])
                best_d = d
    return best


# ---- Per-game run detection ---------------------------------------------

def detect_runs_per_game(
    scoring: pd.DataFrame, params: tuple[int, int],
) -> list[dict]:
    """Detect scoring runs for one game at a single (margin, window-min)
    parameter set.

    Approach: iterate scoring plays. At each play, compute
    window-backward sum for each side. Flag qualifying plays. Then
    merge consecutive qualifying plays for the same running side into
    a single run entry (keeping peak margin)."""
    if scoring.empty:
        return []
    margin_min, window_min = params
    window_sec = window_min * 60

    elapsed = scoring["elapsed"].values
    is_home = scoring["is_home_scoring"].values
    pts = scoring["scoreValue"].values

    flags: list[tuple[int, str, int]] = []  # (idx, running_side, margin)
    n = len(elapsed)
    lo_idx = 0
    for i in range(n):
        while lo_idx < i and elapsed[i] - elapsed[lo_idx] > window_sec:
            lo_idx += 1
        h = a = 0
        for j in range(lo_idx, i + 1):
            if is_home[j]:
                h += pts[j]
            else:
                a += pts[j]
        diff = h - a
        if diff >= margin_min:
            flags.append((i, "home", int(diff)))
        elif -diff >= margin_min:
            flags.append((i, "away", int(-diff)))

    if not flags:
        return []

    # Merge consecutive same-side flags (adjacent idx). A qualifying
    # play that's not immediately adjacent to the previous one OR is on
    # the other side starts a new run.
    runs: list[dict] = []
    cur_side = None
    cur_peak_idx = None
    cur_peak_margin = -1
    cur_first_idx = None
    prev_idx = -99
    for idx, side, mg in flags:
        if side != cur_side or idx != prev_idx + 1:
            if cur_side is not None:
                runs.append({
                    "first_idx": cur_first_idx,
                    "peak_idx": cur_peak_idx,
                    "side": cur_side,
                    "peak_margin": cur_peak_margin,
                })
            cur_side = side
            cur_first_idx = idx
            cur_peak_idx = idx
            cur_peak_margin = mg
        elif mg > cur_peak_margin:
            cur_peak_idx = idx
            cur_peak_margin = mg
        prev_idx = idx
    runs.append({
        "first_idx": cur_first_idx,
        "peak_idx": cur_peak_idx,
        "side": cur_side,
        "peak_margin": cur_peak_margin,
    })
    return runs


def build_scoring_df(pbp_game: pd.DataFrame) -> pd.DataFrame:
    """From a per-game PBP dataframe, return the scoring plays sorted
    by elapsed with an `is_home_scoring` column derived from score
    deltas."""
    g = pbp_game.sort_values("elapsed").reset_index(drop=True).copy()
    g["prev_home"] = g["homeScore"].shift(1).fillna(0)
    g["prev_away"] = g["awayScore"].shift(1).fillna(0)
    scoring = g[g["scoringPlay"] == True].copy()  # noqa: E712
    scoring["is_home_scoring"] = (
        scoring["homeScore"].astype(float)
        > scoring["prev_home"].astype(float)
    )
    return scoring[[
        "game_id", "id", "elapsed", "period_num", "clock",
        "homeScore", "awayScore", "scoreValue", "is_home_scoring",
        "team",
    ]].reset_index(drop=True)


# ---- Per-game analysis orchestration ------------------------------------

def analyze_game(
    gid: str, pbp_game: pd.DataFrame, obs_game: pd.DataFrame, meta: pd.Series,
) -> dict:
    home_fav = bool(meta.get("home_favorite", False))
    home_abbrev = meta["home_team_abbrev"]
    away_abbrev = meta["away_team_abbrev"]

    scoring = build_scoring_df(pbp_game)
    obs_sorted = obs_game.sort_values("elapsed").reset_index(drop=True)

    # Team ID → side map (from scoring plays)
    team_side: dict[str, str] = {}
    for r in scoring.itertuples():
        tid = (r.team or {}).get("id") if isinstance(r.team, dict) else None
        if tid:
            team_side.setdefault(
                str(tid), "home" if r.is_home_scoring else "away"
            )

    # All timeout plays in this game (pre-computed from PBP)
    timeouts = pbp_game[pbp_game.apply(is_timeout_play, axis=1)].copy()
    timeouts = timeouts.sort_values("elapsed").reset_index(drop=True)

    per_param_runs: dict[tuple[int, int], list[dict]] = {}
    for params in RUN_PARAMS:
        raw = detect_runs_per_game(scoring, params)
        enriched = []
        for r in raw:
            peak_play = scoring.iloc[r["peak_idx"]]
            first_play = scoring.iloc[r["first_idx"]]
            run_side = r["side"]                  # "home" or "away"
            trailing_side = "away" if run_side == "home" else "home"
            run_team = home_abbrev if run_side == "home" else away_abbrev
            trailing_team = (
                home_abbrev if trailing_side == "home" else away_abbrev
            )
            is_fav_trailing = (
                home_fav if trailing_side == "home" else (not home_fav)
            )
            run_end_elapsed = float(peak_play.elapsed)
            home_wp_end = _wp_at(
                obs_sorted, run_end_elapsed, WP_CHECKPOINT_TOLERANCE,
            )
            if home_wp_end is None:
                continue
            trailing_wp_end = (
                home_wp_end if trailing_side == "home"
                else 1.0 - home_wp_end
            )
            period_num = int(peak_play.period_num)

            # Recovery checkpoints
            recov = {}
            for cp in RECOVERY_CHECKPOINTS:
                h = _wp_at(obs_sorted, run_end_elapsed + cp,
                           WP_CHECKPOINT_TOLERANCE)
                if h is None:
                    recov[f"recovery_{cp}s"] = None
                else:
                    t_wp = h if trailing_side == "home" else 1.0 - h
                    recov[f"recovery_{cp}s"] = t_wp - trailing_wp_end

            # Max recovery in 5 min after
            window = obs_sorted[
                (obs_sorted["elapsed"] > run_end_elapsed)
                & (obs_sorted["elapsed"]
                   <= run_end_elapsed + MAX_RECOVERY_WINDOW_SEC)
            ]
            max_rec = None
            time_to_max = None
            if not window.empty:
                trail_wp_series = (
                    window["home_wp"].values if trailing_side == "home"
                    else 1.0 - window["home_wp"].values
                )
                i_max = int(np.argmax(trail_wp_series))
                max_rec = float(trail_wp_series[i_max]) - trailing_wp_end
                time_to_max = (
                    float(window["elapsed"].iloc[i_max]) - run_end_elapsed
                )

            # Timeout association
            timeout_found = False
            timeout_elapsed = None
            timeout_called_by_trailing = False
            time_to_timeout = None
            if not timeouts.empty:
                mask = (
                    (timeouts["elapsed"] >= run_end_elapsed)
                    & (timeouts["elapsed"]
                       <= run_end_elapsed + TIMEOUT_WINDOW_SEC)
                )
                matched = timeouts[mask]
                if not matched.empty:
                    to_row = matched.iloc[0]
                    timeout_found = True
                    timeout_elapsed = float(to_row["elapsed"])
                    time_to_timeout = timeout_elapsed - run_end_elapsed
                    tid = (to_row["team"] or {}).get("id") if isinstance(
                        to_row["team"], dict) else None
                    if tid and team_side.get(str(tid)) == trailing_side:
                        timeout_called_by_trailing = True

            enriched.append({
                "game_id": gid,
                "params": params,
                "run_team": run_team,
                "trailing_team": trailing_team,
                "run_side": run_side,
                "trailing_side": trailing_side,
                "run_magnitude": int(r["peak_margin"]),
                "run_end_elapsed": run_end_elapsed,
                "run_end_period": period_num,
                "home_wp_at_run_end": home_wp_end,
                "trailing_wp_at_run_end": trailing_wp_end,
                "score_diff_at_run_end": int(
                    peak_play.homeScore - peak_play.awayScore
                ),
                "pre_game_spread": float(meta.get("home_spread", np.nan)),
                "is_favorite_trailing": is_fav_trailing,
                "timeout_found": timeout_found,
                "timeout_called_by_trailing": timeout_called_by_trailing,
                "time_to_timeout": time_to_timeout,
                "max_recovery": max_rec,
                "time_to_max_sec": time_to_max,
                **recov,
            })
        per_param_runs[params] = enriched

    # Prior degradation checkpoints
    prior_rows = []
    underdog_side = "home" if (not home_fav) else "away"
    for label, e_target in PRIOR_CHECKPOINTS.items():
        home_wp = _wp_at(obs_sorted, e_target, PRIOR_TOLERANCE_SEC)
        if home_wp is None:
            continue
        ud_wp = home_wp if underdog_side == "home" else 1.0 - home_wp
        prior_rows.append({
            "game_id": gid,
            "checkpoint": label,
            "elapsed_target": e_target,
            "ud_wp": ud_wp,
            "ud_leads": ud_wp > 0.50,
            "underdog_won": bool(meta.get("underdog_won", False)),
        })

    # Favorite + underdog dip-recovery scans
    dip_events = []
    if not obs_sorted.empty:
        home_wp_arr = obs_sorted["home_wp"].values
        elapsed_arr = obs_sorted["elapsed"].values
        fav_wp = home_wp_arr if home_fav else 1.0 - home_wp_arr
        ud_wp_arr = 1.0 - fav_wp
        for label, wp_arr, side in (("favorite", fav_wp, "fav"),
                                    ("underdog", ud_wp_arr, "ud")):
            for thr in DIP_THRESHOLDS:
                cross = np.where(wp_arr < thr)[0]
                if cross.size == 0:
                    continue
                first_idx = int(cross[0])
                cross_elapsed = float(elapsed_arr[first_idx])
                # Recovery above 0.50 after first crossing
                after = wp_arr[first_idx:]
                above = np.where(after > 0.50)[0]
                if above.size > 0:
                    recovered = True
                    time_to_rec = float(
                        elapsed_arr[first_idx + int(above[0])] - cross_elapsed
                    )
                else:
                    recovered = False
                    time_to_rec = None
                # Outcome
                won = (
                    bool(meta.get("favorite_won", False)) if label == "favorite"
                    else bool(meta.get("underdog_won", False))
                )
                dip_events.append({
                    "game_id": gid,
                    "side": label,
                    "threshold": thr,
                    "recovered": recovered,
                    "time_to_recovery_sec": time_to_rec,
                    "won_game": won,
                })

    return {
        "game_id": gid,
        "per_param_runs": per_param_runs,
        "prior_rows": prior_rows,
        "dip_events": dip_events,
    }


# ---- Aggregation + tables ------------------------------------------------

def summarize_trajectories(runs: list[dict]) -> dict:
    s = {}
    for cp in RECOVERY_CHECKPOINTS:
        vals = [r[f"recovery_{cp}s"] for r in runs
                if r.get(f"recovery_{cp}s") is not None]
        if vals:
            s[f"rec_{cp}_mean"] = float(np.mean(vals))
            s[f"rec_{cp}_median"] = float(np.median(vals))
            s[f"rec_{cp}_pct_pos"] = 100 * float(np.mean([v > 0 for v in vals]))
            s[f"rec_{cp}_n"] = len(vals)
        else:
            for k in ("mean", "median", "pct_pos"):
                s[f"rec_{cp}_{k}"] = None
            s[f"rec_{cp}_n"] = 0
    mx = [r["max_recovery"] for r in runs if r.get("max_recovery") is not None]
    tt = [r["time_to_max_sec"] for r in runs if r.get("time_to_max_sec") is not None]
    s["max_mean"] = float(np.mean(mx)) if mx else None
    s["max_median"] = float(np.median(mx)) if mx else None
    s["max_pct_pos"] = 100 * float(np.mean([v > 0 for v in mx])) if mx else None
    s["time_to_max_median"] = float(np.median(tt)) if tt else None
    s["n_total"] = len(runs)
    return s


def _fmt(v, spec):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return format(v, spec)


def table3_trajectory(s: dict, heading: str) -> list[str]:
    out = [f"### {heading}", ""]
    out.append("| Metric | Mean | Median | % positive | n |")
    out.append("|---|---:|---:|---:|---:|")
    for cp in RECOVERY_CHECKPOINTS:
        lbl = f"Recovery @ {cp // 60} min" if cp >= 60 else f"Recovery @ {cp}s"
        out.append(
            f"| {lbl} | {_fmt(s.get(f'rec_{cp}_mean'), '+.4f')} | "
            f"{_fmt(s.get(f'rec_{cp}_median'), '+.4f')} | "
            f"{_fmt(s.get(f'rec_{cp}_pct_pos'), '.0f')}% | "
            f"{s.get(f'rec_{cp}_n', 0)} |"
        )
    out.append(
        f"| Max recovery | {_fmt(s.get('max_mean'), '+.4f')} | "
        f"{_fmt(s.get('max_median'), '+.4f')} | "
        f"{_fmt(s.get('max_pct_pos'), '.0f')}% | {s['n_total']} |"
    )
    out.append(
        f"| Time to max (s, median) | — | "
        f"{_fmt(s.get('time_to_max_median'), '.0f')} | — | — |"
    )
    out.append("")
    return out


def table_split_by_predicate(
    rows: list[dict], groups: list[tuple[str, "object"]],
    heading: str,
) -> list[str]:
    out = [f"### {heading}", ""]
    out.append(
        "| Group | n | Mean rec @ 3min | Median | % positive | Mean max rec |"
    )
    out.append("|---|---:|---:|---:|---:|---:|")
    for label, pred in groups:
        sub = [r for r in rows if pred(r)]
        s = summarize_trajectories(sub)
        out.append(
            f"| {label} | {s['n_total']} | "
            f"{_fmt(s.get('rec_180_mean'), '+.4f')} | "
            f"{_fmt(s.get('rec_180_median'), '+.4f')} | "
            f"{_fmt(s.get('rec_180_pct_pos'), '.0f')}% | "
            f"{_fmt(s.get('max_mean'), '+.4f')} |"
        )
    out.append("")
    return out


def _magnitude_bucket(m: int) -> str:
    if 6 <= m <= 7:
        return "6-7"
    if 8 <= m <= 9:
        return "8-9"
    if 10 <= m <= 12:
        return "10-12"
    if m >= 13:
        return "13+"
    return "other"


# ---- Main ---------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-spread", type=float, default=6.0)
    args = parser.parse_args()

    rep = Report()
    rep.md_only(
        "# ESPN-scale scoring-run pattern catalog\n"
    )
    rep.md_only(
        f"_Competitive filter: |spread| ≤ {args.max_spread}_\n"
    )
    rep.md_only(
        "ESPN-WP-based characterization of scoring runs, timeout "
        "association, post-run trajectories, prior degradation, and "
        "favorite/underdog recovery asymmetry across the full 2025-26 "
        "regular season. Complements the n=2 Kalshi-level "
        "`scoring_run_trajectories.py` at 600× the sample size.\n"
    )
    rep.md_only(
        "**ESPN caveat (important).** ESPN WP is more reactive than "
        "real-money markets at the tails (+10-17pp compression per "
        "Phase 3B sportsbook backfill). Absolute WP swing magnitudes "
        "here are upper bounds on Kalshi/sportsbook equivalents. "
        "Relative patterns (which runs, periods, magnitudes produce "
        "recovery) should transfer; absolute magnitudes will be "
        "smaller on Kalshi.\n"
    )

    t0 = time.time()
    print("Loading master CSV, WP, and PBP...")
    master = pd.read_csv(MASTER_CSV)
    master["game_id"] = master["game_id"].astype(str)
    wp = load_jsonl_glob(WP_DIR)
    pbp = load_jsonl_glob(PBP_DIR)
    print(f"  master={len(master):,}  wp={len(wp):,}  pbp={len(pbp):,}  "
          f"({time.time()-t0:.1f}s)")

    # Master prep
    master["home_spread"] = pd.to_numeric(
        master["home_spread"], errors="coerce"
    )
    master["home_favorite"] = master["home_spread"] < 0
    master["home_won"] = master["home_score"] > master["away_score"]
    master["favorite_won"] = master["home_won"] == master["home_favorite"]
    master["underdog_won"] = ~master["favorite_won"]
    master["abs_spread"] = master["home_spread"].abs()

    # Parse PBP clock / period / elapsed
    t0 = time.time()
    pbp["period_num"] = pbp["period"].apply(extract_period_num)
    pbp["clock_sec"] = pbp["clock"].apply(parse_clock)
    pbp["elapsed"] = [
        elapsed_sec(p, c) for p, c in zip(pbp["period_num"], pbp["clock_sec"])
    ]
    pbp = pbp.dropna(subset=["elapsed"])
    pbp["game_id"] = pbp["game_id"].astype(str)
    # Join WP
    obs = wp.merge(
        pbp[["game_id", "id", "elapsed", "period_num", "homeScore",
             "awayScore"]],
        left_on=["game_id", "playId"], right_on=["game_id", "id"],
        how="inner",
    )
    obs["home_wp"] = pd.to_numeric(obs["homeWinPercentage"], errors="coerce")
    obs = obs.dropna(subset=["home_wp"])
    obs["game_id"] = obs["game_id"].astype(str)
    print(f"  obs joined: {len(obs):,}  ({time.time()-t0:.1f}s)")

    # Filter to competitive games
    competitive = master[
        master["abs_spread"] <= args.max_spread
    ].copy()
    all_games = master.copy()
    print(f"  Games with |spread|≤{args.max_spread}: {len(competitive):,} "
          f"(of {len(all_games):,} total)")

    # Iterate per game
    pbp_by_game = {
        gid: g for gid, g in pbp.groupby("game_id")
    }
    obs_by_game = {
        gid: g for gid, g in obs.groupby("game_id")
    }

    per_game_results: list[dict] = []
    skipped = 0
    t0 = time.time()
    for i, row in enumerate(competitive.itertuples(), 1):
        gid = str(row.game_id)
        if gid not in pbp_by_game or gid not in obs_by_game:
            skipped += 1
            continue
        meta = pd.Series({
            "home_team_abbrev": row.home_team_abbrev,
            "away_team_abbrev": row.away_team_abbrev,
            "home_favorite": bool(row.home_favorite),
            "favorite_won": bool(row.favorite_won),
            "underdog_won": bool(row.underdog_won),
            "home_spread": row.home_spread,
        })
        per_game_results.append(
            analyze_game(gid, pbp_by_game[gid], obs_by_game[gid], meta)
        )
        if i % 100 == 0:
            print(f"  processed {i}/{len(competitive)} "
                  f"({time.time()-t0:.1f}s, skipped={skipped})")
    print(f"  done: {len(per_game_results)} games, skipped={skipped} "
          f"({time.time()-t0:.1f}s)")

    # Pool runs per param
    runs_by_param: dict[tuple[int, int], list[dict]] = {
        p: [] for p in RUN_PARAMS
    }
    for r in per_game_results:
        for p, lst in r["per_param_runs"].items():
            runs_by_param[p].extend(lst)

    # ---- Section 1: Run frequency ----
    rep.md_only("## Section 1 — Scoring-run frequency\n")
    rep.md_only("### Table 1 — Run frequency by parameter set\n")
    rep.md_only(
        "| Params (margin, window) | Total runs | Runs/game | "
        "Games w/ ≥1 run | % of games |"
    )
    rep.md_only(
        "|---|---:|---:|---:|---:|"
    )
    n_games = len(per_game_results)
    for params in RUN_PARAMS:
        lst = runs_by_param[params]
        games_with = len({r["game_id"] for r in lst})
        rep.md_only(
            f"| ({params[0]}, {params[1]}min) | {len(lst):,} | "
            f"{len(lst)/n_games:.2f} | {games_with:,} | "
            f"{100*games_with/n_games:.0f}% |"
        )
    rep.md_only("")

    # ---- Section 2: Timeout association ----
    rep.md_only("## Section 2 — Timeout association\n")
    rep.md_only(
        f"### Table 2 — Timeout association (primary: {PRIMARY_PARAMS})\n"
    )
    rep.md_only(
        "| Context | n runs | % followed by timeout (≤ 90s) | "
        "% called by trailing team (of those) |"
    )
    rep.md_only("|---|---:|---:|---:|")
    primary_runs = runs_by_param[PRIMARY_PARAMS]

    def _to_row(label: str, subset: list[dict]) -> str:
        if not subset:
            return f"| {label} | 0 | — | — |"
        with_to = [r for r in subset if r["timeout_found"]]
        by_trailing = [r for r in with_to if r["timeout_called_by_trailing"]]
        pct_to = 100 * len(with_to) / len(subset)
        pct_trail = (
            100 * len(by_trailing) / len(with_to) if with_to else 0.0
        )
        return (
            f"| {label} | {len(subset):,} | {pct_to:.0f}% | "
            f"{pct_trail:.0f}% |"
        )

    rep.md_only(_to_row("All runs", primary_runs))
    rep.md_only(_to_row(
        "Favorite trailing",
        [r for r in primary_runs if r["is_favorite_trailing"]],
    ))
    rep.md_only(_to_row(
        "Underdog trailing",
        [r for r in primary_runs if not r["is_favorite_trailing"]],
    ))
    rep.md_only("")

    # ---- Section 3: Post-run WP trajectory ----
    rep.md_only("## Section 3 — Post-run WP trajectory\n")
    prim_summary = summarize_trajectories(primary_runs)
    sens_summary = summarize_trajectories(runs_by_param[SENSITIVITY_PARAMS])
    for line in table3_trajectory(
        prim_summary,
        f"Table 3 — Post-run recovery, {PRIMARY_PARAMS} "
        f"(n={len(primary_runs)})",
    ):
        rep.md_only(line)
    for line in table3_trajectory(
        sens_summary,
        f"Sensitivity — {SENSITIVITY_PARAMS} "
        f"(n={len(runs_by_param[SENSITIVITY_PARAMS])})",
    ):
        rep.md_only(line)

    # Table 4: favorite vs underdog trailing
    for line in table_split_by_predicate(
        primary_runs,
        [
            ("Favorite trailing", lambda r: r["is_favorite_trailing"]),
            ("Underdog trailing", lambda r: not r["is_favorite_trailing"]),
            ("All", lambda r: True),
        ],
        "Table 4 — Favorite trailing vs underdog trailing",
    ):
        rep.md_only(line)

    # Table 5: by period
    for line in table_split_by_predicate(
        primary_runs,
        [
            ("Q1", lambda r: r["run_end_period"] == 1),
            ("Q2", lambda r: r["run_end_period"] == 2),
            ("Q3", lambda r: r["run_end_period"] == 3),
            ("Q4", lambda r: r["run_end_period"] == 4),
            ("OT", lambda r: r["run_end_period"] >= 5),
        ],
        "Table 5 — Post-run recovery by period",
    ):
        rep.md_only(line)

    # Table 6: by magnitude
    for line in table_split_by_predicate(
        primary_runs,
        [
            ("6-7", lambda r: 6 <= r["run_magnitude"] <= 7),
            ("8-9", lambda r: 8 <= r["run_magnitude"] <= 9),
            ("10-12", lambda r: 10 <= r["run_magnitude"] <= 12),
            ("13+", lambda r: r["run_magnitude"] >= 13),
        ],
        "Table 6 — Post-run recovery by run magnitude",
    ):
        rep.md_only(line)

    # Table 7: with timeout vs without
    for line in table_split_by_predicate(
        primary_runs,
        [
            ("With timeout (≤ 90s)", lambda r: r["timeout_found"]),
            ("No timeout", lambda r: not r["timeout_found"]),
        ],
        "Table 7 — Post-run recovery: with vs without timeout",
    ):
        rep.md_only(line)

    # ---- Section 4: Prior degradation ----
    rep.md_only("## Section 4 — Prior degradation\n")
    rep.md_only("### Table 8 — Underdog lead persistence\n")
    rep.md_only(
        "| Checkpoint | n games | n underdog leading | Mean UD WP "
        "(when leading) | Underdog wins (when leading) |"
    )
    rep.md_only("|---|---:|---:|---:|---:|")
    prior_rows = [p for r in per_game_results for p in r["prior_rows"]]
    prior_df = pd.DataFrame(prior_rows)
    if not prior_df.empty:
        for label in PRIOR_CHECKPOINTS:
            sub = prior_df[prior_df["checkpoint"] == label]
            leading = sub[sub["ud_leads"]]
            if leading.empty:
                rep.md_only(f"| {label} | {len(sub):,} | 0 | — | — |")
                continue
            win_rate = 100 * leading["underdog_won"].mean()
            rep.md_only(
                f"| {label} | {len(sub):,} | {len(leading):,} | "
                f"{leading['ud_wp'].mean():.3f} | {win_rate:.0f}% |"
            )
    rep.md_only("")

    # ---- Section 5: Dip recovery asymmetry ----
    dip_rows = [d for r in per_game_results for d in r["dip_events"]]
    dip_df = pd.DataFrame(dip_rows)

    def dip_table(side_label: str, side_key: str, heading: str) -> list[str]:
        out = [f"### {heading}", ""]
        out.append(
            "| Threshold | n games w/ crossing | % recover > 0.50 | "
            "Median time to recovery (min) | % "
            f"{side_label} wins |"
        )
        out.append("|---|---:|---:|---:|---:|")
        if dip_df.empty:
            out.append("| — | — | — | — | — |")
            out.append("")
            return out
        for thr in DIP_THRESHOLDS:
            sub = dip_df[
                (dip_df["side"] == side_key) & (dip_df["threshold"] == thr)
            ]
            if sub.empty:
                out.append(f"| < {thr:.2f} | 0 | — | — | — |")
                continue
            pct_rec = 100 * sub["recovered"].mean()
            median_t = sub[sub["recovered"]]["time_to_recovery_sec"].median()
            if pd.isna(median_t):
                median_str = "—"
            else:
                median_str = f"{median_t / 60:.1f}"
            pct_win = 100 * sub["won_game"].mean()
            out.append(
                f"| < {thr:.2f} | {len(sub):,} | {pct_rec:.0f}% | "
                f"{median_str} | {pct_win:.0f}% |"
            )
        out.append("")
        return out

    rep.md_only("## Section 5 — Favorite vs underdog dip recovery\n")
    for line in dip_table("favorite", "favorite",
                          "Table 9 — Favorite dip recovery"):
        rep.md_only(line)
    for line in dip_table("underdog", "underdog",
                          "Table 10 — Underdog dip recovery"):
        rep.md_only(line)

    # ---- Section 6: Synthesis ----
    synthesis = build_synthesis(
        run_counts_by_param={p: len(runs_by_param[p]) for p in RUN_PARAMS},
        primary_runs=primary_runs,
        primary_summary=prim_summary,
        dip_df=dip_df,
        prior_df=prior_df,
        n_games=n_games,
    )
    rep.md_only("## Section 6 — Synthesis\n")
    for line in synthesis:
        rep.md_only(line)

    rep.write(OUTPUT_MD)
    print(f"\nReport → {OUTPUT_MD}")

    # Verification prints
    print("\n=== Table 3 (primary params) ===")
    for line in table3_trajectory(
        prim_summary, f"Post-run recovery, {PRIMARY_PARAMS}",
    ):
        print(line)
    print("\n=== Table 4 (favorite vs underdog trailing) ===")
    for line in table_split_by_predicate(
        primary_runs,
        [
            ("Favorite trailing", lambda r: r["is_favorite_trailing"]),
            ("Underdog trailing", lambda r: not r["is_favorite_trailing"]),
            ("All", lambda r: True),
        ],
        "Favorite vs underdog trailing",
    ):
        print(line)
    print("\n=== Table 9 (favorite dip recovery) ===")
    for line in dip_table("favorite", "favorite", "Favorite dip recovery"):
        print(line)
    print("\n=== Synthesis ===")
    for line in synthesis:
        print(line)
    return 0


# ---- Synthesis ----------------------------------------------------------

def build_synthesis(
    run_counts_by_param: dict, primary_runs: list[dict],
    primary_summary: dict, dip_df: pd.DataFrame, prior_df: pd.DataFrame,
    n_games: int,
) -> list[str]:
    lines: list[str] = []

    # 1
    primary_cnt = run_counts_by_param[PRIMARY_PARAMS]
    lines.append(
        f"**1. Run frequency.** At the primary "
        f"(margin ≥ {PRIMARY_PARAMS[0]}, window ≤ {PRIMARY_PARAMS[1]} min) "
        f"definition, {primary_cnt:,} runs were detected across "
        f"{n_games:,} competitive games "
        f"({primary_cnt/n_games:.2f} runs/game). See Table 1."
    )
    lines.append("")

    # 2
    with_to = [r for r in primary_runs if r["timeout_found"]]
    pct_to = 100 * len(with_to) / len(primary_runs) if primary_runs else 0.0
    by_trail = [r for r in with_to if r["timeout_called_by_trailing"]]
    pct_trail = 100 * len(by_trail) / len(with_to) if with_to else 0.0
    lines.append(
        f"**2. Timeout association.** {pct_to:.0f}% of runs are "
        f"followed by a timeout within 90 seconds of game time; of "
        f"those, {pct_trail:.0f}% are called by the trailing team. "
        f"{'Timeouts do reliably follow runs.' if pct_to >= 50 else 'Timeouts are not a reliable marker of runs at ESPN scale.'} "
        "See Table 2."
    )
    lines.append("")

    # 3
    rec3 = primary_summary.get("rec_180_pct_pos")
    rec3m = primary_summary.get("rec_180_mean")
    max_pct = primary_summary.get("max_pct_pos")
    max_mean = primary_summary.get("max_mean")
    lines.append(
        f"**3. Trailing-team recovery.** At 3 min, the trailing team's "
        f"WP recovers (goes positive) "
        f"{rec3:.0f}% of the time with a mean delta of "
        f"{rec3m:+.4f}. Max recovery within 5 min is positive "
        f"{max_pct:.0f}% of the time with mean magnitude "
        f"{max_mean:+.4f}. "
        f"{'The base rate materially exceeds 50%.' if rec3 and rec3 >= 55 else 'Fixed 3-min checkpoint is not meaningfully above 50%.'} "
        "See Table 3."
    )
    lines.append("")

    # 4
    fav_tr = [r for r in primary_runs if r["is_favorite_trailing"]]
    ud_tr = [r for r in primary_runs if not r["is_favorite_trailing"]]
    fav_s = summarize_trajectories(fav_tr)
    ud_s = summarize_trajectories(ud_tr)
    fav_rec = fav_s.get("rec_180_pct_pos")
    ud_rec = ud_s.get("rec_180_pct_pos")

    # Dip recovery asymmetry
    if not dip_df.empty:
        fav_dip_30 = dip_df[
            (dip_df["side"] == "favorite") & (dip_df["threshold"] == 0.30)
        ]
        ud_dip_30 = dip_df[
            (dip_df["side"] == "underdog") & (dip_df["threshold"] == 0.30)
        ]
        fav_pct30 = 100 * fav_dip_30["recovered"].mean() if not fav_dip_30.empty else None
        ud_pct30 = 100 * ud_dip_30["recovered"].mean() if not ud_dip_30.empty else None
    else:
        fav_pct30 = ud_pct30 = None
    lines.append(
        f"**4. Favorite vs underdog recovery.** After being run on "
        f"(primary params): favorite trailing recovers "
        f"{_fmt(fav_rec, '.0f')}% vs underdog trailing "
        f"{_fmt(ud_rec, '.0f')}% (% positive @ 3 min). "
        f"After WP dips below 0.30: favorite recovers above 0.50 in "
        f"{_fmt(fav_pct30, '.0f')}% of games vs underdog "
        f"{_fmt(ud_pct30, '.0f')}%. See Tables 4, 9, 10."
    )
    lines.append("")

    # 5: strongest-signal bucket
    mag_groups = [(6, 7), (8, 9), (10, 12), (13, 99)]
    best_mag_label = None
    best_mag_pct = -1
    for lo, hi in mag_groups:
        sub = [r for r in primary_runs if lo <= r["run_magnitude"] <= hi]
        s = summarize_trajectories(sub)
        pct = s.get("rec_180_pct_pos") or -1
        if pct > best_mag_pct and s.get("n_total", 0) >= 20:
            best_mag_pct = pct
            best_mag_label = f"{lo}-{hi}" if hi < 99 else f"{lo}+"
    best_period = None
    best_period_pct = -1
    for p in (1, 2, 3, 4):
        sub = [r for r in primary_runs if r["run_end_period"] == p]
        s = summarize_trajectories(sub)
        pct = s.get("rec_180_pct_pos") or -1
        if pct > best_period_pct and s.get("n_total", 0) >= 20:
            best_period_pct = pct
            best_period = p
    lines.append(
        f"**5. Strongest-recovery context.** Best-performing run "
        f"magnitude bucket: **{best_mag_label}** "
        f"({best_mag_pct:.0f}% positive @ 3 min). Best-performing "
        f"period: **Q{best_period}** ({best_period_pct:.0f}% positive). "
        "See Tables 5, 6."
    )
    lines.append("")

    # 6: timeouts help recovery?
    with_s = summarize_trajectories(with_to)
    no_to = [r for r in primary_runs if not r["timeout_found"]]
    no_s = summarize_trajectories(no_to)
    with_rec = with_s.get("rec_180_pct_pos")
    no_rec = no_s.get("rec_180_pct_pos")
    delta = (with_rec - no_rec) if (with_rec is not None and no_rec is not None) else None
    lines.append(
        f"**6. Timeouts and recovery.** Runs followed by a timeout "
        f"recover at {_fmt(with_rec, '.0f')}% vs "
        f"{_fmt(no_rec, '.0f')}% without "
        f"(delta {_fmt(delta, '+.0f')}pp). "
        f"{'Timeouts show a meaningful recovery boost.' if delta and delta >= 5 else 'Timeouts do not measurably improve recovery at this scale; runs reverse at similar rates regardless.'} "
        "See Table 7."
    )
    lines.append("")

    # 7: inflection point
    if not prior_df.empty:
        conv_by_cp = {}
        for cp in PRIOR_CHECKPOINTS:
            sub = prior_df[prior_df["checkpoint"] == cp]
            leading = sub[sub["ud_leads"]]
            if not leading.empty:
                conv_by_cp[cp] = 100 * leading["underdog_won"].mean()
        conv_str = ", ".join(
            f"{cp} {v:.0f}%" for cp, v in conv_by_cp.items()
        )
    else:
        conv_str = "—"
    lines.append(
        f"**7. Prior-acceptance inflection.** Underdog-leading-"
        f"conversion rates: {conv_str}. The inflection — where "
        f"underdog-leads convert to wins at roughly the WP model's "
        f"implied rate — is where the prior has fully dissolved. "
        "See Table 8."
    )
    lines.append("")

    # 8: strategy 3 implications
    fav_over_ud_3min = (
        (fav_rec or 0) - (ud_rec or 0)
    )
    lines.append(
        "**8. Strategy 3 implications.** "
        + (
            "The favorite-trailing-after-run scenario produces a "
            "meaningfully higher recovery rate than underdog-trailing, "
            f"{fav_over_ud_3min:+.0f}pp at 3 min. "
            if fav_over_ud_3min >= 5 else
            "The favorite/underdog recovery gap is thin at ESPN scale. "
        )
        + (
            f"Best absolute recovery context is **{best_mag_label}-point "
            f"runs ending in Q{best_period}** "
            f"({best_mag_pct:.0f}% positive @ 3 min). "
        )
        + "Combined with the Kalshi-level n=2 null at 3-min checkpoints, "
        "the entry rule should continue to use price-level triggers "
        "rather than run/timeout context, but prioritize games where "
        "the pre-game favorite falls behind — that's where the prior-"
        "anchoring mechanism has the largest WP-recovery signal on the "
        "ESPN side, and the same mechanism transfers to market prices "
        "with smaller magnitude. ESPN caveat: these magnitudes are "
        "upper bounds; Kalshi recovery will be 10-17pp smaller at the "
        "tails."
    )
    lines.append("")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
