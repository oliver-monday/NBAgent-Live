"""
Strategy 3 game flow trajectory analysis — ESPN WP oscillation by
game shape.

Classifies the full 2025-26 ESPN WP dataset (1,234 games) into five
trajectory-shape buckets (blowout / comeback / late_collapse /
back_and_forth / wire_to_wire) and characterizes swing + mid-range
round-trip features per bucket. Produces the map of "where the
swings live" ahead of spending Odds API credits on market-price
timeseries backfill.

**ESPN caveat** (material for all magnitudes in this report):
ESPN WP is more reactive to game state than real-money markets —
the Phase 3B sportsbook backfill established a +10-17pp compression
at the tails. Swing magnitudes below are upper bounds on what Kalshi
or FanDuel would show. The *relative* ranking across buckets should
transfer; the *absolute* swing counts and round-trip rates will not.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import find_peaks

# ---- Paths / constants -------------------------------------------------

WP_DIR = Path("data/espn_wp")
PBP_DIR = Path("data/pbp")
MASTER_CSV = Path("data/nba_master_2025_26.csv")
OUTPUT_MD = Path("docs/analysis_outputs/strategy3_game_flow_trajectories.md")

REG_PERIODS = 4
REG_PERIOD_SEC = 720    # 12 min
OT_PERIOD_SEC = 300     # 5 min

# Feature thresholds
TRADEABLE_SEC_REM_MIN = 60   # sec_rem ≥ 60 = tradeable window
SWING_MIN_MAG = 0.02
SMOOTH_WINDOW = 3

# Mid-range definitions
MIDRANGE_LOW = 0.25
MIDRANGE_HIGH = 0.75
MIDRANGE_SWING_MIN = 0.10
ENTRY_THRESH = 0.35         # side dips to or below
EXIT_THRESH = 0.50          # side recovers to or above

BUCKET_ORDER = [
    "blowout", "comeback", "late_collapse", "back_and_forth", "wire_to_wire",
]
BUCKET_LABEL = {
    "blowout": "Blowout",
    "comeback": "Comeback",
    "late_collapse": "Late collapse",
    "back_and_forth": "Back-and-forth",
    "wire_to_wire": "Wire-to-wire",
}


# ---- Utility functions (copied from phase3a_espn_dip_analysis) ---------

def parse_clock(clock_raw: Any) -> float:
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
            return int(parts[0]) * 60 + float(parts[1])
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
    if pd.isna(period) or pd.isna(clock_sec):
        return np.nan
    p = int(period)
    if p <= REG_PERIODS:
        return (REG_PERIODS - p) * REG_PERIOD_SEC + clock_sec
    return clock_sec


def elapsed_sec(period, clock_sec):
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


def load_jsonl_glob(directory: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(directory.glob("*.jsonl")):
        if path.stat().st_size == 0:
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


# ---- Per-game feature extraction --------------------------------------

def count_complete_roundtrips(
    series: np.ndarray, entry_thresh: float, exit_thresh: float,
) -> int:
    """Greedy scan of a 1-D WP series: enter when value ≤ entry, exit
    when value ≥ exit, then resume. Returns count of *complete* trips
    only (incomplete trips at series end are excluded)."""
    n = 0
    i = 0
    sz = len(series)
    while i < sz:
        if series[i] <= entry_thresh:
            j = i + 1
            while j < sz and series[j] < exit_thresh:
                j += 1
            if j < sz:
                n += 1
                i = j + 1
            else:
                break
        else:
            i += 1
    return n


def detect_swings(values: np.ndarray) -> list[dict]:
    """Return list of swings ≥ SWING_MIN_MAG on a 1-D WP series. Uses
    scipy find_peaks with prominence filtering (robust to plateaus)
    plus virtual anchors at series start/end to capture leading and
    trailing runs."""
    if len(values) < 3:
        return []
    # Smooth: 3-point centered median, fill NaN with original
    s = pd.Series(values)
    smoothed = s.rolling(SMOOTH_WINDOW, center=True).median()
    smoothed = smoothed.fillna(s).values.astype(float)

    peaks, _ = find_peaks(smoothed, prominence=SWING_MIN_MAG)
    troughs, _ = find_peaks(-smoothed, prominence=SWING_MIN_MAG)
    extrema = sorted(
        [(int(i), float(smoothed[i]), "max") for i in peaks]
        + [(int(i), float(smoothed[i]), "min") for i in troughs],
        key=lambda e: e[0],
    )
    if not extrema:
        return []
    first_type = extrema[0][2]
    opposite_first = "min" if first_type == "max" else "max"
    extrema = [(0, float(smoothed[0]), opposite_first)] + extrema
    last_type = extrema[-1][2]
    opposite_last = "min" if last_type == "max" else "max"
    extrema.append((len(smoothed) - 1, float(smoothed[-1]), opposite_last))

    swings: list[dict] = []
    for k in range(1, len(extrema)):
        a = extrema[k - 1]
        b = extrema[k]
        mag = abs(b[1] - a[1])
        if mag < SWING_MIN_MAG:
            continue
        swings.append({
            "type": "up" if a[2] == "min" else "down",
            "magnitude": mag,
            "start_wp": a[1], "end_wp": b[1],
            "start_idx": a[0], "end_idx": b[0],
        })
    return swings


def compute_features(gid: str, live: pd.DataFrame, meta: pd.Series) -> dict:
    """Per-game features on the tradeable window (sec_rem ≥ 60)."""
    home_wp = live["home_wp"].to_numpy(dtype=float)
    sec_rem = live["sec_rem"].to_numpy(dtype=float)
    n_obs = len(home_wp)

    # Flow shape
    centered = home_wp - 0.5
    # Lead changes: sign flips (ignore zeros)
    sign = np.sign(centered)
    sign_nz = sign.copy()
    sign_nz[sign_nz == 0] = np.nan
    # Forward-fill to treat exact-0.50 as "no change"
    sign_series = pd.Series(sign_nz).ffill().to_numpy()
    sign_series = sign_series[~np.isnan(sign_series)]
    n_lead_changes = (
        int(np.sum(np.diff(sign_series) != 0)) if len(sign_series) > 1 else 0
    )
    pct_competitive = float(np.mean((home_wp >= 0.30) & (home_wp <= 0.70)))
    max_wp_home = float(home_wp.max())
    min_wp_home = float(home_wp.min())
    wp_range = max_wp_home - min_wp_home
    home_won = bool(meta["home_won"])
    winner_min_wp = min_wp_home if home_won else (1.0 - max_wp_home)

    # Swings on home_wp
    swings = detect_swings(home_wp)
    mags = [s["magnitude"] for s in swings]
    n_swings_total = len(swings)
    n_swings_05 = sum(1 for m in mags if m >= 0.05)
    n_swings_10 = sum(1 for m in mags if m >= 0.10)
    n_swings_15 = sum(1 for m in mags if m >= 0.15)
    n_swings_20 = sum(1 for m in mags if m >= 0.20)
    max_swing = float(max(mags)) if mags else 0.0
    median_swing = float(np.median(mags)) if mags else 0.0
    total_swing_distance = float(sum(mags))

    # Mid-range swings (both endpoints in [0.25, 0.75], magnitude ≥ 0.10)
    n_midrange_swings = sum(
        1 for s in swings
        if s["magnitude"] >= MIDRANGE_SWING_MIN
        and MIDRANGE_LOW <= s["start_wp"] <= MIDRANGE_HIGH
        and MIDRANGE_LOW <= s["end_wp"] <= MIDRANGE_HIGH
    )

    # Mid-range round-trips (home + away perspectives)
    home_rts = count_complete_roundtrips(home_wp, ENTRY_THRESH, EXIT_THRESH)
    away_wp = 1.0 - home_wp
    away_rts = count_complete_roundtrips(away_wp, ENTRY_THRESH, EXIT_THRESH)
    midrange_roundtrips = home_rts + away_rts

    return {
        "game_id": gid,
        "n_obs": n_obs,
        "n_lead_changes": n_lead_changes,
        "pct_competitive": pct_competitive,
        "max_wp_home": max_wp_home,
        "min_wp_home": min_wp_home,
        "wp_range": wp_range,
        "winner_min_wp": float(winner_min_wp),
        "n_swings_total": n_swings_total,
        "n_swings_05": n_swings_05,
        "n_swings_10": n_swings_10,
        "n_swings_15": n_swings_15,
        "n_swings_20": n_swings_20,
        "max_swing": max_swing,
        "median_swing": median_swing,
        "total_swing_distance": total_swing_distance,
        "n_midrange_swings": n_midrange_swings,
        "midrange_roundtrips": midrange_roundtrips,
        "midrange_rts_home": home_rts,
        "midrange_rts_away": away_rts,
    }


def classify_bucket(live: pd.DataFrame, meta: pd.Series,
                    features: dict) -> str:
    """Priority-ordered bucket assignment. First match wins."""
    home_wp = live["home_wp"].to_numpy(dtype=float)
    sec_rem = live["sec_rem"].to_numpy(dtype=float)
    home_won = bool(meta["home_won"])
    final_margin = float(meta["final_margin"])

    if home_won:
        winner_wp = home_wp
        loser_wp = 1.0 - home_wp
    else:
        winner_wp = 1.0 - home_wp
        loser_wp = home_wp

    # 1. Blowout: winner's WP > 0.90 before Q4 (sec_rem > 720) AND
    #    final margin > 15
    pre_q4 = sec_rem > REG_PERIOD_SEC
    if pre_q4.any():
        if winner_wp[pre_q4].max() > 0.90 and final_margin > 15:
            return "blowout"

    # 2. Comeback: winner's min WP < 0.20 anywhere in tradeable window
    if winner_wp.min() < 0.20:
        return "comeback"

    # 3. Late collapse: loser's WP > 0.80 in second half (sec_rem < 1440)
    #    and they still lost
    second_half = sec_rem < 1440
    if second_half.any() and loser_wp[second_half].max() > 0.80:
        return "late_collapse"

    # 4. Back-and-forth: ≥ 3 lead changes AND pct_competitive ≥ 0.40
    if features["n_lead_changes"] >= 3 and features["pct_competitive"] >= 0.40:
        return "back_and_forth"

    # 5. Wire-to-wire default
    return "wire_to_wire"


# ---- Report helpers ---------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.md: list[str] = []

    def say(self, line: str = "", md: str | None = None) -> None:
        print(line)
        self.md.append(line if md is None else md)

    def stdout(self, line: str = "") -> None:
        print(line)

    def md_only(self, line: str = "") -> None:
        self.md.append(line)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.md) + "\n")


def _fmt_n_pct(n: int, total: int) -> str:
    return f"{n} ({n / total * 100:.1f}%)" if total else f"{n}"


# ---- Main --------------------------------------------------------------

def main() -> int:
    rep = Report()
    rep.md_only("# Game flow trajectory analysis — ESPN WP, 2025-26 season\n")
    rep.md_only(
        "Classifies 1,234 ESPN WP timeseries into five trajectory-shape "
        "buckets and characterizes swing + mid-range round-trip features "
        "per bucket. Answers: **which game shapes produce the mid-range "
        "oscillation that Strategy 3 needs?**\n"
    )
    rep.md_only(
        "**ESPN caveat:** All magnitudes below are ESPN WP, which the "
        "Phase 3B sportsbook backfill established as +10-17pp more "
        "reactive than real-money markets at the tails. Absolute swing "
        "counts and round-trip rates are upper bounds on what Kalshi "
        "or FanDuel would show. The *relative ranking* across buckets "
        "should hold; the absolute yield will be smaller in production.\n"
    )

    # ---- Load ----
    print("=" * 70)
    print("Strategy 3 game-flow trajectory analysis")
    print("=" * 70)
    print("\nLoading ESPN WP + PBP + master CSV…")
    master = pd.read_csv(MASTER_CSV)
    master["game_id"] = master["game_id"].astype(str)
    wp = load_jsonl_glob(WP_DIR)
    pbp = load_jsonl_glob(PBP_DIR)
    print(f"  WP rows: {len(wp):,}")
    print(f"  PBP rows: {len(pbp):,}")

    # Parse PBP clock/period
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

    # Join
    obs = wp.merge(
        pbp[["game_id", "id", "period_num", "clock_sec", "sec_rem",
             "elapsed", "homeScore", "awayScore"]],
        left_on=["game_id", "playId"], right_on=["game_id", "id"],
        how="inner",
    )
    obs = obs.rename(columns={"homeWinPercentage": "home_wp",
                              "tiePercentage": "tie_pct"})
    obs["home_wp"] = pd.to_numeric(obs["home_wp"], errors="coerce")
    if "tie_pct" in obs.columns:
        obs["tie_pct"] = pd.to_numeric(
            obs["tie_pct"], errors="coerce"
        ).fillna(0.0)
    else:
        obs["tie_pct"] = 0.0
    obs["away_wp"] = 1.0 - obs["home_wp"] - obs["tie_pct"]

    # Game meta
    max_period = (
        pbp.groupby("game_id")["period_num"].max().reset_index()
        .rename(columns={"period_num": "max_period"})
    )
    game_meta = master[[
        "game_id", "home_team_abbrev", "away_team_abbrev",
        "home_score", "away_score", "home_spread",
    ]].copy()
    game_meta = game_meta.merge(max_period, on="game_id", how="left")
    scraped = set(obs["game_id"].unique())
    game_meta = game_meta[game_meta["game_id"].isin(scraped)].copy()
    game_meta["final_margin"] = (
        game_meta["home_score"] - game_meta["away_score"]
    ).abs()
    game_meta["is_ot"] = game_meta["max_period"] > REG_PERIODS
    game_meta["home_won"] = (
        game_meta["home_score"] > game_meta["away_score"]
    )
    game_meta = game_meta.set_index("game_id")
    print(f"  Game meta: {len(game_meta):,} games")

    # ---- Per-game feature extraction ----
    print("\nExtracting per-game features…")
    features_list: list[dict] = []
    skipped_fewobs = 0
    missing_meta = 0
    groups = obs.groupby("game_id", sort=False)
    total_games = len(groups)
    for i, (gid, obs_sub) in enumerate(groups):
        if i > 0 and i % 100 == 0:
            print(f"  Processed {i} / {total_games} games")
        if gid not in game_meta.index:
            missing_meta += 1
            continue
        meta = game_meta.loc[gid]

        obs_sorted = obs_sub.dropna(
            subset=["home_wp", "sec_rem", "elapsed"]
        ).sort_values("elapsed")
        live = obs_sorted[obs_sorted["sec_rem"] >= TRADEABLE_SEC_REM_MIN]
        if len(live) < 10:
            skipped_fewobs += 1
            continue

        features = compute_features(gid, live, meta)
        features["bucket"] = classify_bucket(live, meta, features)
        features["home_spread"] = meta["home_spread"]
        features["abs_spread"] = (
            abs(meta["home_spread"]) if pd.notna(meta["home_spread"])
            else np.nan
        )
        features["final_margin"] = meta["final_margin"]
        features["is_ot"] = bool(meta["is_ot"])
        features["home_won"] = bool(meta["home_won"])
        features_list.append(features)

    df = pd.DataFrame(features_list)
    print(f"  Feature extraction complete: {len(df):,} games")
    print(f"  Skipped (<10 obs in tradeable window): {skipped_fewobs}")
    print(f"  Missing meta: {missing_meta}")

    rep.md_only("## Data\n")
    rep.md_only(
        f"- Games processed: **{len(df):,}** / {total_games} "
        f"(skipped {skipped_fewobs} games with <10 tradeable obs; "
        f"{missing_meta} missing meta).\n"
        f"- Tradeable window: `sec_rem ≥ {TRADEABLE_SEC_REM_MIN}s`.\n"
        f"- Swing detection: `scipy.signal.find_peaks` with prominence "
        f"= {SWING_MIN_MAG:.2f} on 3-point rolling-median-smoothed "
        "home_wp series.\n"
        f"- Mid-range round-trip grid: entry at side_wp ≤ "
        f"{ENTRY_THRESH:.2f}, exit at side_wp ≥ {EXIT_THRESH:.2f}. "
        "Summed across home + away perspectives.\n"
    )

    # ---- Section 1: Bucket distribution ----
    rep.md_only("\n## 1. Bucket distribution\n")

    def bucket_dist(frame: pd.DataFrame, label: str) -> None:
        rep.md_only(f"\n### {label}\n")
        rep.md_only(
            "| Bucket | N | % | Mean |spread| | Mean final margin |\n"
            "|--------|---|---|----------------|-------------------|"
        )
        total = len(frame)
        for b in BUCKET_ORDER:
            sub = frame[frame["bucket"] == b]
            n = len(sub)
            if n == 0:
                rep.md_only(f"| {BUCKET_LABEL[b]} | 0 | 0.0% | — | — |")
                continue
            mean_sp = sub["abs_spread"].dropna().mean()
            mean_fm = sub["final_margin"].mean()
            rep.md_only(
                f"| {BUCKET_LABEL[b]} | {n} | "
                f"{n / total * 100:.1f}% | "
                f"{mean_sp:.2f} | {mean_fm:.1f} |"
            )
        rep.md_only(f"| **Total** | **{total}** | — | — | — |")

    bucket_dist(df, "All games")
    bucket_dist(df[df["abs_spread"] <= 6], "|spread| ≤ 6")

    # Spread cross-tab
    rep.md_only("\n### Spread × bucket cross-tabulation\n")
    rep.md_only(
        "| Bucket | \\|spread\\|≤3 | \\|spread\\| 3-6 | "
        "\\|spread\\| 6-10 | \\|spread\\|>10 | No spread |\n"
        "|--------|---------------|------------------|"
        "-------------------|------------------|-----------|"
    )
    bins = [
        ("≤3", lambda s: s <= 3),
        ("3-6", lambda s: (s > 3) & (s <= 6)),
        ("6-10", lambda s: (s > 6) & (s <= 10)),
        (">10", lambda s: s > 10),
    ]
    for b in BUCKET_ORDER:
        sub = df[df["bucket"] == b]
        nospread = sub["abs_spread"].isna().sum()
        cells = []
        for _, cond in bins:
            mask_vals = cond(sub["abs_spread"].dropna())
            # re-align to sub's index
            ok = sub["abs_spread"].dropna()
            cells.append(int(mask_vals.sum()) if len(ok) else 0)
        rep.md_only(
            f"| {BUCKET_LABEL[b]} | {cells[0]} | {cells[1]} | "
            f"{cells[2]} | {cells[3]} | {nospread} |"
        )

    # Print bucket summary
    print("\nBucket distribution (all games):")
    for b in BUCKET_ORDER:
        sub = df[df["bucket"] == b]
        print(f"  {BUCKET_LABEL[b]:<18s} n={len(sub):>4d}  "
              f"{len(sub)/len(df)*100:>5.1f}%  "
              f"final_margin={sub['final_margin'].mean():.1f}")

    # ---- Section 2: Oscillation characteristics per bucket ----
    rep.md_only("\n## 2. Oscillation characteristics per bucket\n")
    rep.md_only(
        "| Bucket | N | Mean ≥0.10 | Mean ≥0.15 | Median max_swing | "
        "Mean total_swing | Mean lead_changes | Mean pct_competitive |\n"
        "|--------|---|-----------|-----------|------------------|"
        "------------------|--------------------|----------------------|"
    )
    for b in BUCKET_ORDER:
        sub = df[df["bucket"] == b]
        if sub.empty:
            rep.md_only(
                f"| {BUCKET_LABEL[b]} | 0 | — | — | — | — | — | — |"
            )
            continue
        rep.md_only(
            f"| {BUCKET_LABEL[b]} | {len(sub)} | "
            f"{sub['n_swings_10'].mean():.2f} | "
            f"{sub['n_swings_15'].mean():.2f} | "
            f"{sub['max_swing'].median():.3f} | "
            f"{sub['total_swing_distance'].mean():.2f} | "
            f"{sub['n_lead_changes'].mean():.1f} | "
            f"{sub['pct_competitive'].mean():.2f} |"
        )

    # ---- Section 3: Mid-range swing analysis per bucket ----
    rep.md_only("\n## 3. Mid-range swing analysis per bucket\n")
    rep.md_only(
        "Strategy 3 headline: these are the games where mid-range "
        "oscillation produces executable round-trips.\n"
    )

    def midrange_table(frame: pd.DataFrame, label: str) -> None:
        rep.md_only(f"\n### {label}\n")
        rep.md_only(
            "| Bucket | N | Mean midrange_swings | "
            "Mean midrange_roundtrips | % ≥1 roundtrip | % ≥2 roundtrips |\n"
            "|--------|---|---------------------|"
            "------------------------|----------------|"
            "-----------------|"
        )
        for b in BUCKET_ORDER:
            sub = frame[frame["bucket"] == b]
            if sub.empty:
                rep.md_only(
                    f"| {BUCKET_LABEL[b]} | 0 | — | — | — | — |"
                )
                continue
            rep.md_only(
                f"| {BUCKET_LABEL[b]} | {len(sub)} | "
                f"{sub['n_midrange_swings'].mean():.2f} | "
                f"{sub['midrange_roundtrips'].mean():.2f} | "
                f"{(sub['midrange_roundtrips'] >= 1).mean() * 100:.1f}% | "
                f"{(sub['midrange_roundtrips'] >= 2).mean() * 100:.1f}% |"
            )

    midrange_table(df, "All games")
    midrange_table(df[df["abs_spread"] <= 6], "|spread| ≤ 6")

    # Print top-level
    print("\nMid-range round-trip rate by bucket (all games):")
    for b in BUCKET_ORDER:
        sub = df[df["bucket"] == b]
        if sub.empty:
            continue
        rate = (sub["midrange_roundtrips"] >= 1).mean() * 100
        print(f"  {BUCKET_LABEL[b]:<18s} n={len(sub):>4d}  "
              f"≥1 rt: {rate:>5.1f}%  mean rts={sub['midrange_roundtrips'].mean():.2f}")

    # ---- Section 4: Spread as oscillation predictor ----
    rep.md_only("\n## 4. Pre-game spread as oscillation predictor\n")
    with_sp = df.dropna(subset=["abs_spread"])
    if len(with_sp) > 3:
        sp1 = stats.spearmanr(with_sp["abs_spread"], with_sp["n_swings_10"])
        sp2 = stats.spearmanr(
            with_sp["abs_spread"], with_sp["total_swing_distance"]
        )
        sp3 = stats.spearmanr(
            with_sp["abs_spread"], with_sp["n_midrange_swings"]
        )
        rep.md_only(
            "Spearman correlations between |pre-game spread| and "
            "oscillation features:\n\n"
            "| Feature | Spearman ρ | p-value |\n"
            "|---------|------------|---------|\n"
            f"| n_swings ≥ 0.10 | {sp1.statistic:+.3f} | "
            f"{sp1.pvalue:.4f} |\n"
            f"| total_swing_distance | {sp2.statistic:+.3f} | "
            f"{sp2.pvalue:.4f} |\n"
            f"| n_midrange_swings | {sp3.statistic:+.3f} | "
            f"{sp3.pvalue:.4f} |"
        )
        print(f"\nSpread Spearman vs oscillation (n={len(with_sp)}):")
        print(f"  n_swings≥0.10:       ρ={sp1.statistic:+.3f} (p={sp1.pvalue:.4f})")
        print(f"  total_swing_dist:    ρ={sp2.statistic:+.3f} (p={sp2.pvalue:.4f})")
        print(f"  n_midrange_swings:   ρ={sp3.statistic:+.3f} (p={sp3.pvalue:.4f})")
    else:
        rep.md_only("Insufficient spread-tagged data for correlations.")

    rep.md_only("\n### |spread| bucket breakdown\n")
    rep.md_only(
        "| Spread bucket | N | Mean swings ≥0.10 | "
        "Mean midrange_roundtrips | % with ≥1 midrange_roundtrip |\n"
        "|---------------|---|-------------------|"
        "------------------------|-----------------------------|"
    )
    for label, cond in bins:
        sub = with_sp[cond(with_sp["abs_spread"])]
        if len(sub) == 0:
            rep.md_only(f"| {label} | 0 | — | — | — |")
            continue
        rep.md_only(
            f"| {label} | {len(sub)} | "
            f"{sub['n_swings_10'].mean():.2f} | "
            f"{sub['midrange_roundtrips'].mean():.2f} | "
            f"{(sub['midrange_roundtrips'] >= 1).mean() * 100:.1f}% |"
        )

    # ---- Section 5: OT games ----
    rep.md_only("\n## 5. OT games (reference)\n")
    ot = df[df["is_ot"]]
    rep.md_only(
        f"N OT games: **{len(ot)}** "
        f"({len(ot)/len(df)*100:.1f}% of processed).\n"
    )
    if not ot.empty:
        rep.md_only(
            "| Feature | Mean | Median |\n"
            "|---------|------|--------|\n"
            f"| n_swings ≥ 0.10 | {ot['n_swings_10'].mean():.2f} | "
            f"{ot['n_swings_10'].median():.1f} |\n"
            f"| n_midrange_swings | {ot['n_midrange_swings'].mean():.2f} | "
            f"{ot['n_midrange_swings'].median():.1f} |\n"
            f"| midrange_roundtrips | {ot['midrange_roundtrips'].mean():.2f} | "
            f"{ot['midrange_roundtrips'].median():.1f} |\n"
            f"| n_lead_changes | {ot['n_lead_changes'].mean():.1f} | "
            f"{ot['n_lead_changes'].median():.1f} |\n"
            f"| total_swing_distance | {ot['total_swing_distance'].mean():.2f} | "
            f"{ot['total_swing_distance'].median():.2f} |"
        )
        pct_rt_ot = (ot["midrange_roundtrips"] >= 1).mean() * 100
        pct_rt_all = (df["midrange_roundtrips"] >= 1).mean() * 100
        rep.md_only(
            f"\n% OT games with ≥1 midrange round-trip: **{pct_rt_ot:.1f}%** "
            f"(vs {pct_rt_all:.1f}% across all games). Playoff series "
            "produce proportionally more OT games than regular season, "
            "so Strategy 3's playoff yield should run above baseline.\n"
        )

    # ---- Section 6: Target universe sizing ----
    rep.md_only("\n## 6. Strategy 3 target universe sizing\n")

    n_total = len(df)
    n_rt_any = int((df["midrange_roundtrips"] >= 1).sum())
    rep.md_only(
        f"**All games, ≥1 midrange round-trip:** "
        f"{n_rt_any} / {n_total} "
        f"({n_rt_any / n_total * 100:.1f}%)\n"
    )

    sp6 = df[df["abs_spread"] <= 6]
    if not sp6.empty:
        n_rt_sp6 = int((sp6["midrange_roundtrips"] >= 1).sum())
        rep.md_only(
            f"**|spread| ≤ 6, ≥1 midrange round-trip:** "
            f"{n_rt_sp6} / {len(sp6)} "
            f"({n_rt_sp6 / len(sp6) * 100:.1f}%)\n"
        )

    sp3 = df[df["abs_spread"] <= 3]
    if not sp3.empty:
        n_rt_sp3 = int((sp3["midrange_roundtrips"] >= 1).sum())
        rep.md_only(
            f"**|spread| ≤ 3, ≥1 midrange round-trip:** "
            f"{n_rt_sp3} / {len(sp3)} "
            f"({n_rt_sp3 / len(sp3) * 100:.1f}%)\n"
        )

    # Most productive bucket (largest contribution to total round-trips)
    rep.md_only("\n### Round-trip contribution by bucket\n")
    total_rts = df["midrange_roundtrips"].sum()
    rep.md_only(
        "| Bucket | N | Total round-trips | % of all round-trips | "
        "Mean per game |\n"
        "|--------|---|-------------------|----------------------|"
        "---------------|"
    )
    bucket_rows = []
    for b in BUCKET_ORDER:
        sub = df[df["bucket"] == b]
        if sub.empty:
            continue
        rts = int(sub["midrange_roundtrips"].sum())
        pct = rts / total_rts * 100 if total_rts else 0.0
        rep.md_only(
            f"| {BUCKET_LABEL[b]} | {len(sub)} | {rts} | "
            f"{pct:.1f}% | {sub['midrange_roundtrips'].mean():.2f} |"
        )
        bucket_rows.append((b, rts, pct))

    if bucket_rows:
        top = max(bucket_rows, key=lambda r: r[1])
        rep.md_only(
            f"\nMost productive bucket: **{BUCKET_LABEL[top[0]]}** "
            f"({top[1]} round-trips, {top[2]:.1f}% of total)."
        )

    # Max yield if we could predict shape pre-tip (sum round-trips across
    # buckets with ≥1 rt rate > some baseline). Simpler: the max yield =
    # sum of round-trips in productive buckets.
    productive_buckets = [
        b for b, rts, pct in bucket_rows
        if (df[df["bucket"] == b]["midrange_roundtrips"] >= 1).mean() > 0.5
    ]
    productive_n = int(df[df["bucket"].isin(productive_buckets)].shape[0])
    productive_rts = int(
        df[df["bucket"].isin(productive_buckets)]["midrange_roundtrips"].sum()
    )
    rep.md_only(
        f"\n### Hypothetical: perfect pre-tip shape prediction\n\n"
        f"If we could predict pre-tip which games would fall into a "
        f"**≥50% round-trip rate bucket**, we'd target "
        f"{productive_n} / {n_total} games "
        f"({productive_n/n_total*100:.1f}%) and capture "
        f"{productive_rts} / {int(total_rts)} round-trips "
        f"({productive_rts/total_rts*100:.1f}% of total, if total_rts>0). "
        f"Buckets meeting the bar: "
        f"{', '.join(BUCKET_LABEL[b] for b in productive_buckets) or 'none'}.\n\n"
        "Note: we cannot predict bucket pre-tip reliably. This is an "
        "upper-bound scenario. Pre-game spread alone is a weak "
        "predictor (see Section 4 Spearman correlations)."
    )

    rep.md_only(
        "\n### Caveat — ESPN WP vs market prices\n\n"
        "All round-trip counts above use ESPN WP as the signal. The "
        "Phase 3B sportsbook backfill established that real-money "
        "markets compress +10-17pp relative to ESPN at the tails: a "
        "$0.10 ESPN swing is typically a $0.05-$0.07 Kalshi swing. "
        "The round-trip threshold grid in this analysis (entry ≤ 0.35, "
        "exit ≥ 0.50) therefore implies a Kalshi-equivalent swing of "
        "maybe $0.10 gross minus spread rather than the full $0.15. "
        "The bucket-relative ranking should transfer (games where ESPN "
        "shows lots of swings will show more Kalshi swings than games "
        "where ESPN shows few), but the absolute yield will be smaller "
        "in production. Tier 3 Odds API sportsbook-timeseries backfill "
        "is the next validation step.\n"
    )

    # Print target summary
    print("\nStrategy 3 target universe:")
    print(f"  All games with ≥1 midrange round-trip: "
          f"{n_rt_any}/{n_total} ({n_rt_any/n_total*100:.1f}%)")
    if not sp6.empty:
        print(f"  |spread|≤6:      {n_rt_sp6}/{len(sp6)} "
              f"({n_rt_sp6/len(sp6)*100:.1f}%)")
    if not sp3.empty:
        print(f"  |spread|≤3:      {n_rt_sp3}/{len(sp3)} "
              f"({n_rt_sp3/len(sp3)*100:.1f}%)")
    if bucket_rows:
        print(f"  Most productive: {BUCKET_LABEL[top[0]]} "
              f"({top[1]} round-trips, {top[2]:.1f}% of total)")

    # Write report
    rep.write(OUTPUT_MD)
    print(f"\nReport written to {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
