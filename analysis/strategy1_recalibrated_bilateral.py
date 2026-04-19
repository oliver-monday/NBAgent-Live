"""
Strategy 1 recalibrated bilateral analysis.

Maps ESPN WP → estimated sportsbook-equivalent WP using the 57-point
calibration from the Odds API backfill, then re-runs the Phase 3A
bilateral analysis + §6.7 asymmetric-any-order analysis at
sportsbook-denominated thresholds, and computes EV-after-fees.

The backfill result (docs/analysis_outputs/strategy1_sportsbook_backfill.md)
established a mean +12.58pp residual — sportsbooks compress ESPN's
extremes substantially. This script translates that into Strategy 1's
real-money economics: what opportunity rate and EV survive at
sportsbook-realistic entry prices?

Usage:
    python -m analysis.strategy1_recalibrated_bilateral
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

from analysis.phase_3a_followup import (
    Report,
    extract_period_num,
    parse_clock,
    sec_rem_in_period,
    elapsed_sec,
    kalshi_fee,
    qualifications,
)
from analysis.strategy1_sportsbook_backfill import (
    identify_bilaterals,
    stratified_sample,
    parse_bookmaker_h2h,
    MASTER_CSV,
    WP_DIR,
    PBP_DIR,
    CACHE_DIR,
)

OUTPUT_MD = Path(
    "docs/analysis_outputs/strategy1_recalibrated_bilateral.md"
)

# Sportsbook-denominated thresholds for bilateral dip rates
SB_THRESHOLDS_BILATERAL = [0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15]

# Sportsbook-denominated threshold grid for §6.7 asymmetric analysis
SB_THRESHOLD_GRID = [
    # Strict symmetric
    (0.35, 0.35), (0.30, 0.30), (0.25, 0.25),
    # Asymmetric pairs — X is the tight leg, Y the relaxed
    (0.25, 0.35), (0.25, 0.40), (0.25, 0.45),
    (0.30, 0.35), (0.30, 0.40), (0.30, 0.45),
    (0.35, 0.40), (0.35, 0.45),
]

REFERENCE_POINTS = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35,
                    0.40, 0.45, 0.50]


# ---- Phase 1: build calibration from cached backfill -----------------

def load_calibration_pairs(rep: Report) -> pd.DataFrame:
    """Re-derive the 30-game bilateral sample, load cached Odds API
    responses, compute no-vig consensus per (game, moment), and pair
    with ESPN dip values. Returns DataFrame with (espn_wp, sb_consensus)
    per observation."""
    master = pd.read_csv(MASTER_CSV)
    master["game_id"] = master["game_id"].astype(str)
    rep.stdout_only("Identifying bilateral <0.20 games from ESPN data…")
    bilaterals = identify_bilaterals(master)
    rep.stdout_only(
        f"  {len(bilaterals)} bilateral games found (Phase 3A baseline: 146)"
    )
    plan = stratified_sample(bilaterals, n_target=30)
    rep.stdout_only(f"  Stratified sample: {len(plan)} games")

    pairs = []
    for _, pr in plan.iterrows():
        gid = pr["game_id"]
        for moment in ("home_dip", "away_dip"):
            cache_path = CACHE_DIR / f"{gid}_{moment}.json"
            if not cache_path.exists():
                continue
            try:
                cached = json.loads(cache_path.read_text())
            except json.JSONDecodeError:
                continue
            data = cached.get("data")
            if not isinstance(data, dict):
                continue
            home_name = data.get("home_team") or ""
            away_name = data.get("away_team") or ""
            target_ts = pr[f"{moment}_wallclock"]
            if not isinstance(target_ts, datetime):
                target_ts = pd.Timestamp(target_ts).to_pydatetime()
            books = parse_bookmaker_h2h(data, home_name, away_name, target_ts)
            fresh = [
                b for b in books
                if b["staleness_sec"] is not None
                and b["staleness_sec"] <= 300
            ]
            if not fresh:
                continue
            if moment == "home_dip":
                espn_wp = float(pr["min_home_wp"])
                sb = float(np.median([b["home_novig"] for b in fresh]))
            else:
                espn_wp = float(pr["min_away_wp"])
                sb = float(np.median([b["away_novig"] for b in fresh]))
            pairs.append({
                "game_id": gid,
                "moment": moment,
                "espn_wp": espn_wp,
                "sb_consensus": sb,
                "n_fresh_books": len(fresh),
            })
    df = pd.DataFrame(pairs)
    rep.stdout_only(
        f"  Calibration pairs loaded: {len(df)} "
        f"(from {len(plan) * 2} expected)"
    )
    return df


# ---- Phase 1b: fit calibration mapping -------------------------------

def build_mapping(cal_df: pd.DataFrame, rep: Report):
    """Fit a monotone symmetric interpolant ESPN WP → sportsbook-equivalent
    WP on the [0, 0.5] domain. Returns (espn_to_sb callable, anchor_x,
    anchor_y) where anchor arrays are the points fed to the interpolator
    for downstream inspection."""
    cal = cal_df[cal_df["espn_wp"] < 0.5].copy()
    if cal.empty:
        raise RuntimeError("No calibration data in [0, 0.5) — cannot fit.")

    # Aggregate to median sb_consensus per unique espn_wp (PCHIP needs
    # strictly-increasing x). Raw backfill has many observations at
    # espn_wp ≈ 0.001; aggregating stabilizes the fit at the tail.
    agg = (
        cal.groupby("espn_wp", as_index=False)
        .agg(sb_consensus=("sb_consensus", "median"),
             n_obs=("sb_consensus", "size"))
        .sort_values("espn_wp")
    )

    # Prepend anchors (0→0) and append (0.5→0.5). Drop any aggregate row
    # that conflicts with the anchors (e.g., extremely unlikely x=0 row).
    anchor_x = [0.0]
    anchor_y = [0.0]
    for _, r in agg.iterrows():
        anchor_x.append(float(r["espn_wp"]))
        anchor_y.append(float(r["sb_consensus"]))
    anchor_x.append(0.5)
    anchor_y.append(0.5)

    x_arr = np.asarray(anchor_x)
    y_arr = np.asarray(anchor_y)

    # Force monotonicity by taking a running max on y (the raw calibration
    # data has enough noise that a few observations are out of order —
    # without this PCHIP still accepts but can produce small dips).
    y_mono = np.maximum.accumulate(y_arr)

    interp = PchipInterpolator(x_arr, y_mono, extrapolate=False)

    def espn_to_sb(x):
        arr = np.atleast_1d(np.asarray(x, dtype=float))
        out = np.empty_like(arr)
        low_mask = arr <= 0.5
        out[low_mask] = np.clip(interp(arr[low_mask]), 0.0, 1.0)
        high = arr[~low_mask]
        if high.size:
            out[~low_mask] = 1.0 - np.clip(interp(1.0 - high), 0.0, 1.0)
        return out if np.ndim(x) else float(out[0])

    # Fit-quality report: predicted vs observed at each calibration point
    rep.stdout_only("\nCalibration fit quality (predicted vs observed):")
    rep.stdout_only(
        f"  {'espn_wp':>8s}  {'n_obs':>5s}  {'observed':>10s}  "
        f"{'predicted':>10s}  {'residual':>10s}"
    )
    total_abs_err = 0.0
    for _, r in agg.iterrows():
        pred = espn_to_sb(float(r["espn_wp"]))
        err = r["sb_consensus"] - pred
        total_abs_err += abs(err)
        rep.stdout_only(
            f"  {r['espn_wp']:>8.4f}  {int(r['n_obs']):>5d}  "
            f"{r['sb_consensus']:>10.4f}  {pred:>10.4f}  {err:>+10.4f}"
        )
    mae = total_abs_err / len(agg) if len(agg) else 0
    rep.stdout_only(f"  Mean absolute error at calibration points: {mae:.4f}")

    return espn_to_sb, x_arr, y_mono, agg


def print_reference_mapping(espn_to_sb, rep: Report) -> None:
    rep.say("\n--- Reference-point mapping ---")
    rep.md_only("\n### Reference-point mapping\n")
    rep.stdout_only(f"  {'ESPN WP':>8s}  {'Mapped SB WP':>14s}")
    rep.md_only("| ESPN WP | Mapped SB WP |\n|---------|-------------|")
    for x in REFERENCE_POINTS:
        y = espn_to_sb(x)
        rep.stdout_only(f"  {x:>8.2f}  {y:>14.4f}")
        rep.md_only(f"| {x:.2f} | {y:.4f} |")


def inverse_sb_to_espn(espn_to_sb, target_sb: float) -> float:
    """Numerical inverse: find ESPN x such that espn_to_sb(x) ≈ target_sb.
    Uses bisection on [0, 1] since the mapping is monotone."""
    if target_sb <= 0:
        return 0.0
    if target_sb >= 1:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        v = espn_to_sb(mid)
        if v < target_sb:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---- Phase 2: load full ESPN dataset + apply mapping -----------------

def load_obs_frame(rep: Report) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load full ESPN dataset and return (observations, game_meta).
    Pattern mirrors phase_3a_followup / phase3a_espn_dip_analysis."""
    master = pd.read_csv(MASTER_CSV)
    master["game_id"] = master["game_id"].astype(str)

    rep.stdout_only("\nLoading full ESPN WP + PBP dataset…")
    wp_rows = []
    pbp_rows = []
    for path in sorted(WP_DIR.glob("*.jsonl")):
        if path.stat().st_size == 0:
            continue
        with open(path) as f:
            for line in f:
                if line.strip():
                    wp_rows.append(json.loads(line))
    for path in sorted(PBP_DIR.glob("*.jsonl")):
        if path.stat().st_size == 0:
            continue
        with open(path) as f:
            for line in f:
                if line.strip():
                    pbp_rows.append(json.loads(line))
    wp = pd.DataFrame(wp_rows)
    pbp = pd.DataFrame(pbp_rows)
    rep.stdout_only(f"  WP rows: {len(wp):,}, PBP rows: {len(pbp):,}")

    pbp["period_num"] = pbp["period"].apply(extract_period_num)
    pbp["clock_sec"] = pbp["clock"].apply(parse_clock)
    pbp["sec_rem"] = [
        sec_rem_in_period(p, c)
        for p, c in zip(pbp["period_num"], pbp["clock_sec"])
    ]
    pbp["elapsed"] = [
        elapsed_sec(p, c)
        for p, c in zip(pbp["period_num"], pbp["clock_sec"])
    ]

    obs = wp.merge(
        pbp[["game_id", "id", "period_num", "clock_sec", "sec_rem",
             "elapsed", "homeScore", "awayScore"]],
        left_on=["game_id", "playId"], right_on=["game_id", "id"],
        how="inner",
    )
    obs = obs.rename(columns={"homeWinPercentage": "home_wp"})
    obs["home_wp"] = pd.to_numeric(obs["home_wp"], errors="coerce")
    obs["away_wp"] = 1.0 - obs["home_wp"]

    max_period = (pbp.groupby("game_id")["period_num"].max()
                    .reset_index()
                    .rename(columns={"period_num": "max_period"}))
    game_meta = master[[
        "game_id", "home_team_abbrev", "away_team_abbrev",
        "home_score", "away_score", "home_spread",
    ]].copy()
    game_meta = game_meta.merge(max_period, on="game_id", how="left")
    scraped_gids = set(obs["game_id"].unique())
    game_meta = game_meta[game_meta["game_id"].isin(scraped_gids)].copy()
    game_meta["final_margin"] = (
        game_meta["home_score"] - game_meta["away_score"]
    ).abs()
    game_meta["is_ot"] = game_meta["max_period"] > 4

    rep.stdout_only(f"  Observations joined: {len(obs):,}  "
                    f"games: {len(game_meta):,}")
    return obs, game_meta


# ---- Phase 3: bilateral dip rates at SB thresholds --------------------

def bilateral_at_sb_thresholds(
    rep: Report,
    obs: pd.DataFrame,
    game_meta: pd.DataFrame,
    espn_to_sb,
) -> pd.DataFrame:
    """Per-game min home/away SB-mapped WP in sec_rem>=60, then threshold
    scan. Returns a long-format table keyed by (threshold, universe)."""
    tradeable = obs[obs["sec_rem"] >= 60].dropna(
        subset=["home_wp", "away_wp"]
    ).copy()
    # Apply mapping
    tradeable["home_sb_wp"] = espn_to_sb(tradeable["home_wp"].to_numpy())
    tradeable["away_sb_wp"] = espn_to_sb(tradeable["away_wp"].to_numpy())

    # Complement sanity: home_sb + away_sb should be ~1 modulo
    # independent-side mapping noise.
    complement = tradeable["home_sb_wp"] + tradeable["away_sb_wp"]
    median_dev = float((complement - 1.0).abs().median())
    max_dev = float((complement - 1.0).abs().max())
    rep.stdout_only(
        f"  Mapped complement check: median |dev| = {median_dev:.4f}, "
        f"max = {max_dev:.4f}"
    )

    per_game = tradeable.groupby("game_id").agg(
        min_home=("home_sb_wp", "min"),
        min_away=("away_sb_wp", "min"),
    ).reset_index()

    sp6 = set(game_meta[game_meta["home_spread"].abs() <= 6]["game_id"])
    sp3 = set(game_meta[game_meta["home_spread"].abs() <= 3]["game_id"])
    m10 = set(game_meta[game_meta["final_margin"] <= 10]["game_id"])
    m5 = set(game_meta[game_meta["final_margin"] <= 5]["game_id"])
    ot = set(game_meta[game_meta["is_ot"]]["game_id"])

    universes = [
        ("All", set(per_game["game_id"])),
        ("|spread|<=6", sp6),
        ("|spread|<=3", sp3),
        ("margin<=10", m10),
        ("margin<=5", m5),
        ("OT", ot),
    ]

    rows = []
    for thr in SB_THRESHOLDS_BILATERAL:
        for name, ids in universes:
            sub = per_game[per_game["game_id"].isin(ids)]
            n = len(sub)
            if n == 0:
                continue
            hit = ((sub["min_home"] < thr) & (sub["min_away"] < thr)).sum()
            rows.append({
                "threshold_sb": thr, "universe": name,
                "n": n, "hits": int(hit), "rate": hit / n,
            })
    return pd.DataFrame(rows), tradeable


def print_bilateral_table(
    rep: Report, bilat_df: pd.DataFrame, espn_to_sb,
) -> None:
    rep.say("")
    rep.say("=" * 70)
    rep.say("B. Bilateral dip rates at sportsbook thresholds "
            "(sec_rem>=60)")
    rep.md_only("\n## B. Bilateral dip rates at sportsbook thresholds "
                "(sec_rem >= 60)\n")

    # Show which ESPN threshold each SB threshold corresponds to
    rep.md_only("SB threshold → ESPN-equivalent threshold "
                "(via inverse of calibration):\n")
    rep.stdout_only(f"  {'SB thr':>7s}  {'ESPN thr':>9s}")
    rep.md_only("| SB threshold | ESPN-equiv |\n|---|---|")
    for thr in SB_THRESHOLDS_BILATERAL:
        espn_equiv = inverse_sb_to_espn(espn_to_sb, thr)
        rep.stdout_only(f"  {thr:>7.2f}  {espn_equiv:>9.3f}")
        rep.md_only(f"| {thr:.2f} | {espn_equiv:.3f} |")

    # Pivot to wide format by universe
    wide = bilat_df.pivot_table(
        index="threshold_sb", columns="universe",
        values="rate", aggfunc="first",
    )
    cols = ["All", "|spread|<=6", "|spread|<=3",
            "margin<=10", "margin<=5", "OT"]
    cols = [c for c in cols if c in wide.columns]
    wide = wide[cols].sort_index(ascending=False)

    rep.say("")
    rep.stdout_only("  " + f"{'Threshold':>10s}" + "  " +
                    "  ".join(f"{c:>14s}" for c in cols))
    rep.md_only("\n| Threshold | " + " | ".join(cols) + " |\n|" +
                "|".join(["---"] * (len(cols) + 1)) + "|")
    for thr, row in wide.iterrows():
        cells = []
        for c in cols:
            n_row = bilat_df[
                (bilat_df["threshold_sb"] == thr)
                & (bilat_df["universe"] == c)
            ]
            if n_row.empty:
                cells.append("—")
            else:
                rate = row[c] * 100
                n = int(n_row["n"].iloc[0])
                cells.append(f"{rate:5.1f}% ({n})")
        rep.stdout_only(
            f"  {'<' + f'{thr:.2f}':>10s}  " +
            "  ".join(f"{cell:>14s}" for cell in cells)
        )
        rep.md_only(f"| <{thr:.2f} | " + " | ".join(cells) + " |")


# ---- Phase 3/4: §6.7 analysis at SB thresholds + EV ------------------

def run_sb_asymmetric(
    rep: Report,
    tradeable: pd.DataFrame,
    game_meta: pd.DataFrame,
):
    sp6 = set(game_meta[game_meta["home_spread"].abs() <= 6]["game_id"])
    w = tradeable[tradeable["game_id"].isin(sp6)].dropna(
        subset=["home_sb_wp", "away_sb_wp", "elapsed"]
    ).sort_values(["game_id", "elapsed"])

    game_results: dict[str, dict[tuple[float, float], tuple[bool, bool, bool]]] = {}
    for gid, group in w.groupby("game_id"):
        hs = group["home_sb_wp"]
        as_ = group["away_sb_wp"]
        el = group["elapsed"]
        row = {}
        for (X, Y) in SB_THRESHOLD_GRID:
            row[(X, Y)] = qualifications(hs, as_, el, X, Y)
        game_results[gid] = row

    n_games = len(game_results)

    # ---- C. Rates table ----
    rep.say("")
    rep.say("=" * 70)
    rep.say(f"C. §6.7 asymmetric rates at sportsbook thresholds "
            f"(|spread|<=6, N={n_games})")
    rep.md_only(
        f"\n## C. §6.7 asymmetric rates at sportsbook thresholds "
        f"(|spread| ≤ 6, N = {n_games})\n"
    )
    rep.stdout_only(
        f"  {'X':>5s} {'Y':>5s}  "
        f"{'Strict':>18s}  {'Asym':>18s}  {'Sequential':>18s}"
    )
    rep.md_only(
        "| X | Y | Strict | Asymmetric | Sequential |\n"
        "|---|---|--------|------------|------------|"
    )
    rates = {}
    for (X, Y) in SB_THRESHOLD_GRID:
        ks = sum(1 for r in game_results.values() if r[(X, Y)][0])
        ka = sum(1 for r in game_results.values() if r[(X, Y)][1])
        kseq = sum(1 for r in game_results.values() if r[(X, Y)][2])
        rates[(X, Y)] = {"strict": ks, "asym": ka, "seq": kseq}
        rep.stdout_only(
            f"  {X:>5.2f} {Y:>5.2f}  "
            f"{ks:>6d}/{n_games:<4d} ({ks/n_games*100:5.1f}%)  "
            f"{ka:>6d}/{n_games:<4d} ({ka/n_games*100:5.1f}%)  "
            f"{kseq:>6d}/{n_games:<4d} ({kseq/n_games*100:5.1f}%)"
        )
        rep.md_only(
            f"| {X:.2f} | {Y:.2f} | "
            f"{ks/n_games*100:.1f}% ({ks}/{n_games}) | "
            f"{ka/n_games*100:.1f}% ({ka}/{n_games}) | "
            f"{kseq/n_games*100:.1f}% ({kseq}/{n_games}) |"
        )

    # ---- D. EV-after-fees ----
    rep.say("")
    rep.say("=" * 70)
    rep.say("D. EV-after-fees at sportsbook entry prices "
            "(100 contracts/leg, taker-taker)")
    rep.md_only(
        "\n## D. EV-after-fees at sportsbook entry prices\n\n"
        "100 contracts per leg, taker-taker fees (Kalshi formula from "
        "`docs/FEES.md`). `Net (no sprd)` uses fees only; "
        "`Net (−1¢ sprd)` adds one tick of spread per leg "
        "($1/leg = $2/round-trip) as a sensitivity on §2.5. "
        "Opportunity rate is the asymmetric-any-order rate on "
        "|spread| ≤ 6 games.\n"
    )
    CONTRACTS = 100
    ev_rows = []
    for (X, Y) in SB_THRESHOLD_GRID:
        gross = (1.0 - X - Y) * CONTRACTS
        if gross <= 0:
            continue
        feeX = kalshi_fee(CONTRACTS, X)
        feeY = kalshi_fee(CONTRACTS, Y)
        fees = feeX + feeY
        net = gross - fees
        net_sprd = net - 2.0  # $1/leg × 2 legs
        asym = rates[(X, Y)]["asym"]
        rate_frac = asym / n_games if n_games else 0.0
        ev_game = rate_frac * net
        ev_game_sprd = rate_frac * net_sprd
        ev_rows.append({
            "X": X, "Y": Y, "gross": gross, "fees": fees,
            "net": net, "net_sprd": net_sprd,
            "rate": rate_frac, "ev_game": ev_game,
            "ev_game_sprd": ev_game_sprd,
        })

    rep.stdout_only(
        f"  {'X':>5s} {'Y':>5s}  {'Gross':>7s}  "
        f"{'Fees':>6s}  {'Net':>7s}  {'Net-sprd':>9s}  "
        f"{'Rate':>6s}  {'EV/gm':>7s}  {'EV/gm-sprd':>11s}"
    )
    rep.md_only(
        "| X | Y | Gross | Fees | Net (no sprd) | Net (−1¢ sprd) "
        "| Opp rate | EV/game | EV/game (−sprd) |\n"
        "|---|---|-------|------|---------------|----------------"
        "|----------|---------|-----------------|"
    )
    for r in ev_rows:
        rep.stdout_only(
            f"  {r['X']:>5.2f} {r['Y']:>5.2f}  "
            f"${r['gross']:>6.2f}  ${r['fees']:>5.2f}  "
            f"${r['net']:>6.2f}  ${r['net_sprd']:>8.2f}  "
            f"{r['rate']*100:>5.1f}%  ${r['ev_game']:>6.2f}  "
            f"${r['ev_game_sprd']:>10.2f}"
        )
        rep.md_only(
            f"| {r['X']:.2f} | {r['Y']:.2f} | ${r['gross']:.2f} | "
            f"${r['fees']:.2f} | ${r['net']:.2f} | ${r['net_sprd']:.2f} | "
            f"{r['rate']*100:.1f}% | ${r['ev_game']:.2f} | "
            f"${r['ev_game_sprd']:.2f} |"
        )

    # ---- E. Optimal threshold ----
    ev_rows.sort(key=lambda r: r["ev_game"], reverse=True)
    top3 = ev_rows[:3]
    rep.say("")
    rep.say("=" * 70)
    rep.say("E. Optimal threshold identification (top 3 by EV/game)")
    rep.md_only("\n## E. Optimal threshold identification\n")
    rep.md_only(
        "| Rank | X | Y | Opp rate | Net/trade | EV/game | "
        "EV/game (−sprd) |\n"
        "|------|---|---|----------|-----------|---------|"
        "-----------------|"
    )
    for i, r in enumerate(top3, 1):
        rep.stdout_only(
            f"  #{i}  X={r['X']:.2f} Y={r['Y']:.2f}  "
            f"rate={r['rate']*100:.1f}%  "
            f"net=${r['net']:.2f}  EV/game=${r['ev_game']:.2f}  "
            f"EV/game(−sprd)=${r['ev_game_sprd']:.2f}"
        )
        rep.md_only(
            f"| {i} | {r['X']:.2f} | {r['Y']:.2f} | "
            f"{r['rate']*100:.1f}% | ${r['net']:.2f} | "
            f"${r['ev_game']:.2f} | ${r['ev_game_sprd']:.2f} |"
        )
    best = top3[0] if top3 else None
    if best:
        rep.md_only(
            f"\n**Recommended operating point: ({best['X']:.2f}, "
            f"{best['Y']:.2f})** — balances opportunity rate "
            f"({best['rate']*100:.1f}%) against per-trade net "
            f"(${best['net']:.2f}). Higher frequency pairs "
            "(wider Y) produce more EV/game but shrink per-trade "
            "margin; tighter pairs are more fee-efficient but hit "
            "less often. The ranking above is on EV/game "
            "(pre-spread); adding one tick of spread per leg "
            "(§2.5 sensitivity) reduces EV uniformly but doesn't "
            "change the ordering meaningfully."
        )
    return rates, ev_rows


# ---- Phase 5: side-by-side vs Phase 3A --------------------------------

def side_by_side_comparison(
    rep: Report, rates: dict, ev_rows: list[dict],
) -> None:
    rep.say("")
    rep.say("=" * 70)
    rep.say("F. Side-by-side with Phase 3A (ESPN-denominated)")
    rep.md_only("\n## F. Side-by-side with Phase 3A\n")

    # Phase 3A ESPN-denominated benchmark at (0.20, 0.30) — from
    # the Phase 3A follow-up report.
    phase3a_rate = 0.490   # 49.0% asymmetric at (0.20, 0.30) on |spread|<=6
    phase3a_gross = 50.00
    phase3a_net = 47.40
    phase3a_ev = 23.23

    if not ev_rows:
        rep.say("  no EV rows to compare")
        return
    best = ev_rows[0]

    rep.md_only(
        "| Metric | ESPN-denominated (0.20, 0.30) "
        "| SB-calibrated (best pair) |\n|---|---|---|"
    )
    rows_sbs = [
        ("Threshold pair", "(0.20, 0.30)", f"({best['X']:.2f}, {best['Y']:.2f})"),
        ("Opportunity rate (|spread|≤6)",
         f"{phase3a_rate*100:.1f}%",
         f"{best['rate']*100:.1f}%"),
        ("Gross per trade", f"${phase3a_gross:.2f}", f"${best['gross']:.2f}"),
        ("Net per trade (after fees)",
         f"${phase3a_net:.2f}", f"${best['net']:.2f}"),
        ("EV per competitive game",
         f"${phase3a_ev:.2f}", f"${best['ev_game']:.2f}"),
        ("EV per game (−1¢ spread)",
         f"${phase3a_ev - phase3a_rate * 2:.2f}",
         f"${best['ev_game_sprd']:.2f}"),
    ]
    for k, v_old, v_new in rows_sbs:
        rep.stdout_only(f"  {k:<32s}  {v_old:>20s}  {v_new:>20s}")
        rep.md_only(f"| {k} | {v_old} | {v_new} |")


# ---- Phase 6: preliminary verdict + write -----------------------------

def write_verdict(rep: Report, ev_rows: list[dict], cal_df: pd.DataFrame):
    if not ev_rows:
        rep.md_only("\n## G. Preliminary verdict\n\nNo EV rows — aborting.\n")
        return
    best = ev_rows[0]
    ev = best["ev_game"]
    ev_sprd = best["ev_game_sprd"]

    if ev >= 15.0:
        verdict = (
            f"**Strategy 1 survives recalibration with meaningful EV.** "
            f"Best operating point ({best['X']:.2f}, {best['Y']:.2f}) "
            f"produces ${ev:.2f}/game pre-spread "
            f"(${ev_sprd:.2f}/game after §2.5 one-tick spread). "
            f"Opportunity rate ({best['rate']*100:.1f}%) is lower than "
            f"ESPN's 49.0% at (0.20, 0.30), but per-trade economics "
            f"remain positive. Proceed to Phase 3B Kalshi-data "
            f"validation at the recalibrated thresholds — the real "
            f"remaining unknowns are liquidity at sportsbook-price "
            f"Kalshi entries and whether Kalshi tracks sportsbook "
            f"consensus (the Phase 3B smoke test at n=6 suggested it "
            f"might diverge from ESPN similarly, i.e. it should track "
            f"sportsbooks)."
        )
    elif ev >= 5.0:
        verdict = (
            f"**Strategy 1 survives recalibration but is marginal.** "
            f"Best operating point ({best['X']:.2f}, {best['Y']:.2f}) "
            f"produces ${ev:.2f}/game pre-spread "
            f"(${ev_sprd:.2f}/game after §2.5 one-tick spread). "
            f"Proceed cautiously — liquidity haircuts from Phase 3B "
            f"could push this below viability. Consider the spread "
            f"sensitivity the more important of the two numbers: if "
            f"realized spreads are wider than one tick (likely in "
            f"extreme-price zones), EV erodes further."
        )
    else:
        verdict = (
            f"**Strategy 1 does not survive recalibration at meaningful "
            f"scale.** Best operating point ({best['X']:.2f}, "
            f"{best['Y']:.2f}) produces only ${ev:.2f}/game pre-spread "
            f"(${ev_sprd:.2f}/game after §2.5 one-tick spread). The "
            f"combination of lower opportunity rates and thinner "
            f"per-trade margins at sportsbook-realistic thresholds "
            f"renders the strategy economically uninteresting absent "
            f"some structural edge we haven't identified. Re-visit "
            f"Strategy 2 or Strategy 3 as primary paths before "
            f"considering Phase 4 authoring on Strategy 1."
        )
    rep.say("")
    rep.say("=" * 70)
    rep.say("G. Preliminary verdict")
    rep.md_only("\n## G. Preliminary verdict\n")
    rep.say(verdict)
    rep.md_only(verdict)
    rep.md_only(
        f"\n**Sample-size caveats:**\n\n"
        f"- Calibration based on {len(cal_df)} dip observations across "
        f"~30 games. The mapping in the [0.20, 0.50] ESPN range has "
        f"sparse direct calibration data — it's anchored at 0.5 and "
        f"extrapolated monotonically from the [0, 0.20] fit.\n"
        f"- Symmetry assumption (f(x) = 1 − f(1 − x)) is imposed by "
        f"construction and not independently validated. A bilateral-dip "
        f"analysis happens to rely most heavily on x < 0.5, so this is "
        f"low-impact for Strategy 1 but would matter more for Strategy "
        f"2 (single-side mean reversion) — revisit before reusing this "
        f"mapping there.\n"
        f"- One-tick spread assumption is a placeholder until §2.5 has "
        f"orderbook-measured spreads at these target entry prices.\n"
    )


# ---- Main -------------------------------------------------------------

def main() -> int:
    rep = Report()
    rep.md_only(
        f"# Strategy 1 recalibrated bilateral — "
        f"{date.today().isoformat()}\n"
    )
    rep.md_only(
        "Applies the 57-point ESPN→sportsbook calibration (from "
        "`docs/analysis_outputs/strategy1_sportsbook_backfill.md`) to "
        "the full 2025-26 ESPN dataset, then re-runs Phase 3A / §6.7 "
        "analyses at sportsbook-denominated thresholds to estimate "
        "Strategy 1's opportunity rate and EV on real-money markets. "
        "Question answered: **does Strategy 1 survive at "
        "sportsbook-realistic entry prices, and where is the optimal "
        "operating point?**\n"
    )
    rep.md_only("## A. Calibration mapping\n")

    rep.stdout_only("=" * 70)
    rep.stdout_only("Strategy 1 recalibrated bilateral analysis")
    rep.stdout_only("=" * 70)

    # Phase 1: load calibration, fit mapping
    cal_df = load_calibration_pairs(rep)
    espn_to_sb, anchor_x, anchor_y, agg = build_mapping(cal_df, rep)

    rep.md_only(
        f"Calibration built from {len(cal_df)} dip observations "
        f"({len(agg)} unique ESPN WP values after aggregation to "
        "median SB consensus per value). Fitted with PchipInterpolator "
        "on [0, 0.5]; symmetry f(x) = 1 − f(1 − x) extends to "
        "[0.5, 1]. Running-max applied to anchor y-values to enforce "
        "strict monotonicity in the face of noisy backfill data.\n"
    )
    print_reference_mapping(espn_to_sb, rep)

    # Phase 2: load obs + apply mapping
    obs, game_meta = load_obs_frame(rep)
    rep.md_only(
        f"\n**Full ESPN dataset**: {len(obs):,} observations across "
        f"{len(game_meta):,} games. Mapping applied independently to "
        "home and away sides; complement check on mapped values below.\n"
    )

    # Phase 3: bilateral rates
    bilat_df, tradeable = bilateral_at_sb_thresholds(
        rep, obs, game_meta, espn_to_sb,
    )
    print_bilateral_table(rep, bilat_df, espn_to_sb)

    # Phases 3 (continued) + 4: §6.7 + EV + optimal
    rates, ev_rows = run_sb_asymmetric(rep, tradeable, game_meta)

    # Phase 5: side-by-side
    side_by_side_comparison(rep, rates, ev_rows)

    # Phase 6: verdict + write
    write_verdict(rep, ev_rows, cal_df)

    rep.write(OUTPUT_MD)
    rep.stdout_only("")
    rep.stdout_only("=" * 70)
    rep.stdout_only(f"Report written to {OUTPUT_MD}")
    rep.stdout_only("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
