"""
Phase 3A follow-up:
  §6.4 — Pace vs bilateral involvement correlation.
  §6.7 — Sequential-opportunistic bilateral construction.

Writes both a stdout report and a durable markdown artifact at
docs/analysis_outputs/3a_followup_2026_04_17.md so the numbers are
reproducible without re-running.

Data sources:
  - data/nba_master_2025_26.csv             — game list + spreads
  - data/espn_wp/{gameId}.jsonl             — ESPN WP timeseries
  - data/pbp/{gameId}.jsonl                 — ESPN PBP (for clock/period)
  - basketball-reference.com (via cloudscraper) — team pace

Cross-checks vs Phase 3A baseline:
  - Strict (0.20, 0.20) at |spread|<=6 must be ~26.6% ± 0.5pp
  - Strict (0.15, 0.15) at |spread|<=6 must be ~17.1% ± 0.5pp
  - Strict (0.10, 0.10) at |spread|<=6 must be ~7.3%  ± 0.5pp
  - SAS bilateral involvement rate must be ~39.5%
  - TOR bilateral involvement rate must be ~18.8%
"""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy import stats

MASTER_CSV = Path("data/nba_master_2025_26.csv")
WP_DIR = Path("data/espn_wp")
PBP_DIR = Path("data/pbp")
OUTPUT_MD = Path("docs/analysis_outputs/3a_followup_2026_04_17.md")

REG_PERIOD_SEC = 720
OT_PERIOD_SEC = 300
REG_PERIODS = 4

# bbref team name → standard NBA abbreviation.
# This is a name-to-abbrev map, not an abbrev-to-abbrev map like
# scrapers/espn_scraper.py::_ABBR_NORM — different shape, kept local.
_BBREF_NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN", "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET", "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}


# ---- Output multiplexer (stdout + markdown) ---------------------------

class Report:
    """Writes to both stdout (pretty) and a markdown buffer (durable)."""
    def __init__(self):
        self.md: list[str] = []

    def say(self, text: str = "", md: str | None = None) -> None:
        """Print to stdout and accumulate markdown. If md is None, uses text."""
        print(text)
        self.md.append(text if md is None else md)

    def md_only(self, text: str) -> None:
        self.md.append(text)

    def stdout_only(self, text: str) -> None:
        print(text)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.md) + "\n")


# ---- Parse clock / period --------------------------------------------

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


# ---- File loaders ----------------------------------------------------

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


# ---- bbref pace scrape ------------------------------------------------

def scrape_bbref_pace(season_year: int = 2026) -> pd.DataFrame:
    """Return DataFrame with columns [team_abbr, team_name, pace, pace_rank].

    Raises RuntimeError with a clear message if bbref is unreachable or
    the pace table can't be parsed. Do NOT fall back to hardcoded values."""
    try:
        import cloudscraper  # local import: avoids import-time failure
                              # if cloudscraper is missing for unrelated users
    except ImportError as e:
        raise RuntimeError(
            "cloudscraper not installed. Run: pip install cloudscraper "
            "(also in requirements.txt). Original error: " + str(e)
        ) from e

    url = f"https://www.basketball-reference.com/leagues/NBA_{season_year}.html"
    scraper = cloudscraper.create_scraper()
    resp = scraper.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"bbref returned HTTP {resp.status_code} for {url}. "
            "Retry later (Cloudflare rate-limiting is the usual cause), "
            "or supply a local CSV. Do not hardcode pace values."
        )
    html = resp.text

    m = re.search(r'<table[^>]*id="advanced-team"[\s\S]*?</table>', html)
    if not m:
        raise RuntimeError(
            "bbref page loaded but 'advanced-team' table not found. "
            "The page layout may have changed. Inspect "
            + url + " and update the script."
        )

    tables = pd.read_html(StringIO(m.group(0)))
    df = tables[0]
    # MultiIndex columns — flatten by picking the second level
    df.columns = [c[1] if isinstance(c, tuple) else c for c in df.columns]

    if "Team" not in df.columns or "Pace" not in df.columns:
        raise RuntimeError(
            "bbref advanced-team parsed, but Team/Pace columns missing. "
            f"Got columns: {df.columns.tolist()}"
        )

    df = df[["Team", "Pace"]].copy()
    # Strip "*" from playoff team names and "League Average" row
    df["Team"] = df["Team"].astype(str).str.rstrip("*").str.strip()
    df = df[df["Team"] != "League Average"].reset_index(drop=True)

    # Map to standard abbreviations
    df["team_abbr"] = df["Team"].map(_BBREF_NAME_TO_ABBR)
    unmapped = df[df["team_abbr"].isna()]
    if len(unmapped) > 0:
        raise RuntimeError(
            "bbref returned teams not in name→abbrev map: "
            f"{unmapped['Team'].tolist()}. Add them to _BBREF_NAME_TO_ABBR."
        )

    df["Pace"] = pd.to_numeric(df["Pace"], errors="coerce")
    if df["Pace"].isna().any():
        raise RuntimeError(
            f"Pace values failed numeric coercion: "
            f"{df[df['Pace'].isna()]['Team'].tolist()}"
        )

    df["pace_rank"] = df["Pace"].rank(ascending=False, method="min").astype(int)
    df = df.rename(columns={"Team": "team_name", "Pace": "pace"})
    return df[["team_abbr", "team_name", "pace", "pace_rank"]].sort_values("team_abbr").reset_index(drop=True)


# ---- Fee helper (FEES.md formula) ------------------------------------

def kalshi_fee(contracts: int, price: float) -> float:
    """Taker fee per leg: round_up(0.07 × C × P × (1-P)) to the cent.
    At cent resolution using math.ceil. Floors at zero (the formula is
    already non-negative for valid P)."""
    if price <= 0 or price >= 1:
        return 0.0
    raw = 0.07 * contracts * price * (1.0 - price)
    # round up to the cent
    return math.ceil(raw * 100) / 100


# ---- Part A: §6.4 pace correlation -----------------------------------

def compute_team_involvement(obs: pd.DataFrame, game_meta: pd.DataFrame) -> pd.DataFrame:
    """Per team, on |spread|<=6 games with sec_rem>=60: bilateral <0.20
    involvement rate and game counts (home / away / any)."""
    sp6_ids = set(game_meta[game_meta["home_spread"].abs() <= 6]["game_id"])
    w = obs[(obs["sec_rem"] >= 60) & (obs["game_id"].isin(sp6_ids))]
    per_game = w.groupby("game_id").agg(
        min_home=("home_wp", "min"),
        min_away=("away_wp", "min"),
    ).reset_index()
    per_game = per_game.merge(
        game_meta[["game_id", "home_team_abbrev", "away_team_abbrev"]],
        on="game_id", how="left",
    )
    per_game["bilat_0_20"] = (
        (per_game["min_home"] < 0.20) & (per_game["min_away"] < 0.20)
    )

    teams = sorted(set(game_meta["home_team_abbrev"]).union(
        game_meta["away_team_abbrev"]))
    rows = []
    for t in teams:
        if pd.isna(t):
            continue
        home = per_game[per_game["home_team_abbrev"] == t]
        away = per_game[per_game["away_team_abbrev"] == t]
        any_ = per_game[
            (per_game["home_team_abbrev"] == t)
            | (per_game["away_team_abbrev"] == t)
        ]
        if len(any_) == 0:
            continue
        rows.append({
            "team_abbr": t,
            "games": len(any_),
            "home_games": len(home),
            "away_games": len(away),
            "bilat_0_20_rate": any_["bilat_0_20"].mean(),
        })
    return pd.DataFrame(rows).sort_values("bilat_0_20_rate", ascending=False).reset_index(drop=True)


def run_pace_analysis(rep: Report, obs: pd.DataFrame,
                      game_meta: pd.DataFrame) -> None:
    rep.say("")
    rep.say("=" * 70, md="")
    rep.say("PART A — §6.4 Pace vs bilateral involvement rate",
            md="## §6.4 — Pace vs bilateral involvement rate\n")
    rep.say("=" * 70, md="")

    # Involvement rates (reproduces 3A team table)
    inv = compute_team_involvement(obs, game_meta)
    sas = inv[inv["team_abbr"] == "SAS"]
    tor = inv[inv["team_abbr"] == "TOR"]
    rep.say("")
    rep.say("Cross-check vs Phase 3A team table:")
    rep.say("  SAS involvement rate: "
            f"{float(sas['bilat_0_20_rate'].iloc[0])*100:.1f}%  "
            f"(expected ~39.5%)")
    rep.say("  TOR involvement rate: "
            f"{float(tor['bilat_0_20_rate'].iloc[0])*100:.1f}%  "
            f"(expected ~18.8%)")

    # Scrape pace
    rep.say("")
    rep.say("Scraping basketball-reference pace (2025-26 regular season)...")
    pace_df = scrape_bbref_pace(2026)
    rep.say(f"  OK: {len(pace_df)} teams, pace range "
            f"[{pace_df['pace'].min():.1f}, {pace_df['pace'].max():.1f}] "
            f"poss/48.")

    # Join
    combined = inv.merge(pace_df, on="team_abbr", how="inner")
    missing_in_inv = set(pace_df["team_abbr"]) - set(inv["team_abbr"])
    missing_in_pace = set(inv["team_abbr"]) - set(pace_df["team_abbr"])
    if missing_in_inv:
        rep.say(f"  NOTE: teams in pace data not in involvement: "
                f"{sorted(missing_in_inv)}")
    if missing_in_pace:
        rep.say(f"  NOTE: teams in involvement not in pace data: "
                f"{sorted(missing_in_pace)}")
    combined["involvement_rank"] = (
        combined["bilat_0_20_rate"].rank(ascending=False, method="min").astype(int)
    )

    # Print/write the ranked table
    rep.say("")
    rep.say("Team-level table (sorted by bilateral involvement rate):")
    rep.md_only("")
    rep.md_only("### Per-team pace vs bilateral involvement\n")
    rep.md_only(
        "| Team | Pace | Pace rank | Bilat<0.20 | Bilat rank | n games |\n"
        "|------|------|-----------|------------|------------|---------|"
    )
    header = f"  {'Team':<5s} {'Pace':>6s} {'PaceR':>6s} {'Inv%':>7s} {'InvR':>6s} {'Games':>6s}"
    rep.stdout_only(header)
    combined_sorted = combined.sort_values(
        "bilat_0_20_rate", ascending=False).reset_index(drop=True)
    for _, r in combined_sorted.iterrows():
        inv_pct = float(r["bilat_0_20_rate"]) * 100
        rep.stdout_only(
            f"  {r['team_abbr']:<5s} "
            f"{r['pace']:>6.2f} {int(r['pace_rank']):>6d} "
            f"{inv_pct:>6.1f}% {int(r['involvement_rank']):>6d} "
            f"{int(r['games']):>6d}"
        )
        rep.md_only(
            f"| {r['team_abbr']} | {r['pace']:.2f} | "
            f"{int(r['pace_rank'])} | {inv_pct:.1f}% | "
            f"{int(r['involvement_rank'])} | {int(r['games'])} |"
        )

    # Correlations
    # Primary: n>=10 games per team
    primary = combined[combined["games"] >= 10]
    excluded = combined[combined["games"] < 10]
    rep.say("")
    rep.say(f"Small-sample exclusion: {len(excluded)} team(s) with "
            f"n < 10 competitive games excluded from primary "
            f"correlation.")
    if len(excluded) > 0:
        rep.say("  Excluded: " + ", ".join(
            f"{r['team_abbr']}({int(r['games'])})"
            for _, r in excluded.iterrows()
        ))

    def _corr(block: pd.DataFrame, label: str):
        if len(block) < 3:
            rep.say(f"  {label}: n={len(block)} too few for correlation.")
            return
        sp = stats.spearmanr(block["pace"], block["bilat_0_20_rate"])
        pe = stats.pearsonr(block["pace"], block["bilat_0_20_rate"])
        rep.say(f"  {label} (n={len(block)}):")
        rep.say(f"    Spearman ρ = {sp.statistic:+.3f}  "
                f"(p = {sp.pvalue:.4f})")
        rep.say(f"    Pearson  r = {pe.statistic:+.3f}  "
                f"(p = {pe.pvalue:.4f})")

    rep.say("")
    rep.say("Correlations of pace vs bilateral <0.20 involvement rate:")
    _corr(primary, "Primary (n>=10 games/team)")
    _corr(combined, "Full 30 teams (includes small-sample)")

    # Brief interpretation in markdown
    rep.md_only("")
    rep.md_only("### Correlation summary\n")
    sp_primary = stats.spearmanr(primary["pace"], primary["bilat_0_20_rate"])
    pe_primary = stats.pearsonr(primary["pace"], primary["bilat_0_20_rate"])
    sp_all = stats.spearmanr(combined["pace"], combined["bilat_0_20_rate"])
    pe_all = stats.pearsonr(combined["pace"], combined["bilat_0_20_rate"])
    rep.md_only(
        "| Scope | n | Spearman ρ | Spearman p | Pearson r | Pearson p |\n"
        "|-------|---|------------|------------|-----------|-----------|\n"
        f"| Primary (n≥10) | {len(primary)} | "
        f"{sp_primary.statistic:+.3f} | {sp_primary.pvalue:.4f} | "
        f"{pe_primary.statistic:+.3f} | {pe_primary.pvalue:.4f} |\n"
        f"| All 30 teams   | {len(combined)} | "
        f"{sp_all.statistic:+.3f} | {sp_all.pvalue:.4f} | "
        f"{pe_all.statistic:+.3f} | {pe_all.pvalue:.4f} |"
    )
    if len(excluded) > 0:
        rep.md_only("")
        excluded_str = ", ".join(
            f"{r['team_abbr']} ({int(r['games'])})"
            for _, r in excluded.iterrows()
        )
        rep.md_only(
            f"Small-sample exclusion ({len(excluded)} teams with <10 "
            f"competitive games): " + excluded_str + "."
        )


# ---- Part B: §6.7 sequential-opportunistic bilateral -----------------

def qualifications(series_home: pd.Series, series_away: pd.Series,
                   elapsed: pd.Series, X: float, Y: float) -> tuple[bool, bool, bool]:
    """For a single game's time series (home_wp, away_wp, elapsed),
    return (strict_symmetric, asymmetric_any_order, sequential_operational)
    at thresholds (X, Y).

    - strict_symmetric: min_home < X AND min_away < X  (Y unused here; we
      keep the interface consistent but the strict rate is a function of
      min(X, Y)/symmetric X; we pass X as the symmetric threshold).
    - asymmetric_any_order: (min_home < X AND min_away < Y) OR
                             (min_home < Y AND min_away < X),
      no time ordering.
    - sequential_operational: there exist t1<t2 such that
        (home<X at t1, away<Y at t2) OR (away<X at t1, home<Y at t2).
    """
    min_home = series_home.min()
    min_away = series_away.min()

    strict = bool(min_home < X and min_away < X)
    asymmetric = bool(
        (min_home < X and min_away < Y) or (min_home < Y and min_away < X)
    )

    # Sequential: compute earliest crossing times for each side at the
    # tighter threshold X, then check if the other side crosses Y later.
    home_below_X = series_home < X
    away_below_X = series_away < X
    home_below_Y = series_home < Y
    away_below_Y = series_away < Y

    t_home_X_first = elapsed[home_below_X].min() if home_below_X.any() else np.inf
    t_away_X_first = elapsed[away_below_X].min() if away_below_X.any() else np.inf

    seq = False
    # Case A: home dips <X first, then away dips <Y later
    if np.isfinite(t_home_X_first):
        if (away_below_Y & (elapsed > t_home_X_first)).any():
            seq = True
    # Case B: away dips <X first, then home dips <Y later
    if not seq and np.isfinite(t_away_X_first):
        if (home_below_Y & (elapsed > t_away_X_first)).any():
            seq = True

    return strict, asymmetric, seq


def run_sequential_analysis(rep: Report, obs: pd.DataFrame,
                            game_meta: pd.DataFrame) -> None:
    rep.say("")
    rep.say("=" * 70, md="")
    rep.say("PART B — §6.7 Sequential-opportunistic bilateral",
            md="## §6.7 — Sequential-opportunistic bilateral\n")
    rep.say("=" * 70, md="")

    # Window: sec_rem >= 60 (matches 3A tradeable window)
    w = obs[obs["sec_rem"] >= 60].dropna(
        subset=["home_wp", "away_wp", "elapsed"]
    ).sort_values(["game_id", "elapsed"])

    # Group once; per-game series iteration is unavoidable for sequential
    grouped = w.groupby("game_id")

    threshold_grid = [
        (0.20, 0.20), (0.15, 0.15), (0.10, 0.10),
        (0.15, 0.25), (0.15, 0.30),
        (0.20, 0.25), (0.20, 0.30), (0.20, 0.35),
        (0.10, 0.25), (0.10, 0.30),
    ]

    sp6_ids = set(game_meta[game_meta["home_spread"].abs() <= 6]["game_id"])
    all_gids = set(game_meta["game_id"])

    # For each game, evaluate all threshold pairs once.
    game_results: dict[str, dict[tuple[float, float], tuple[bool, bool, bool]]] = {}
    for gid, group in grouped:
        if gid not in all_gids:
            continue
        home_s = group["home_wp"]
        away_s = group["away_wp"]
        el_s = group["elapsed"]
        row = {}
        for (X, Y) in threshold_grid:
            row[(X, Y)] = qualifications(home_s, away_s, el_s, X, Y)
        game_results[gid] = row

    def rate(gids: Iterable[str], idx: int, pair: tuple[float, float]) -> tuple[int, int, float]:
        gids = [g for g in gids if g in game_results]
        if not gids:
            return (0, 0, float("nan"))
        k = sum(1 for g in gids if game_results[g][pair][idx])
        return (k, len(gids), k / len(gids))

    # Print rate tables
    rep.say("")
    rep.say("Rates by definition (window sec_rem>=60):")
    rep.md_only("")
    rep.md_only(
        "### Definitions\n\n"
        "- **Strict symmetric**: `min(home_wp) < X AND min(away_wp) < X`. "
        "Y ignored; included as a baseline reproducing the 3A bilateral numbers.\n"
        "- **Asymmetric any-order**: `(min_home < X AND min_away < Y) OR "
        "(min_home < Y AND min_away < X)`. Order of dips irrelevant.\n"
        "- **Sequential operational**: there exist t1 < t2 with one side "
        "dipping below X at t1 and the other dipping below Y at t2. "
        "The entry policy: buy leg 1 when it dips below X; wait and buy "
        "leg 2 when the other side dips below Y.\n\n"
        "All measurements on the tradeable window sec_rem ≥ 60.\n"
    )

    for universe_name, uids in (("All games", all_gids),
                                 ("|spread|<=6", sp6_ids)):
        rep.say("")
        rep.say(f"--- Universe: {universe_name} (N={len(uids & set(game_results))}) ---")
        rep.md_only(f"\n### Rates — {universe_name}\n")
        rep.md_only(
            "| X | Y | Strict | Asymmetric | Sequential |\n"
            "|---|---|--------|------------|------------|"
        )
        rep.stdout_only(
            f"  {'X':>5s} {'Y':>5s}  "
            f"{'Strict':>18s}  {'Asym':>18s}  {'Sequential':>18s}"
        )
        for (X, Y) in threshold_grid:
            ks_strict, n, _ = rate(uids, 0, (X, Y))
            ka, _, _ = rate(uids, 1, (X, Y))
            kseq, _, _ = rate(uids, 2, (X, Y))
            if n == 0:
                continue
            rep.stdout_only(
                f"  {X:>5.2f} {Y:>5.2f}  "
                f"{ks_strict:>6d}/{n:<4d} ({ks_strict/n*100:5.1f}%)  "
                f"{ka:>6d}/{n:<4d} ({ka/n*100:5.1f}%)  "
                f"{kseq:>6d}/{n:<4d} ({kseq/n*100:5.1f}%)"
            )
            rep.md_only(
                f"| {X:.2f} | {Y:.2f} | "
                f"{ks_strict/n*100:.1f}% ({ks_strict}/{n}) | "
                f"{ka/n*100:.1f}% ({ka}/{n}) | "
                f"{kseq/n*100:.1f}% ({kseq}/{n}) |"
            )

    # Cross-checks vs Phase 3A
    def _strict_pct(uids, X):
        k, n, _ = rate(uids, 0, (X, X))
        return k, n, (k / n * 100 if n else float("nan"))

    c1 = _strict_pct(sp6_ids, 0.20)
    c2 = _strict_pct(sp6_ids, 0.15)
    c3 = _strict_pct(sp6_ids, 0.10)
    rep.say("")
    rep.say("Cross-check vs Phase 3A (strict at |spread|<=6, sec_rem>=60):")
    rep.say(f"  (0.20, 0.20): {c1[2]:.1f}% ({c1[0]}/{c1[1]})  "
            f"expected ~26.6%  Δ={c1[2]-26.6:+.2f}pp")
    rep.say(f"  (0.15, 0.15): {c2[2]:.1f}% ({c2[0]}/{c2[1]})  "
            f"expected ~17.1%  Δ={c2[2]-17.1:+.2f}pp")
    rep.say(f"  (0.10, 0.10): {c3[2]:.1f}% ({c3[0]}/{c3[1]})  "
            f"expected ~7.3%   Δ={c3[2]-7.3:+.2f}pp")
    rep.md_only("")
    rep.md_only("### Cross-check vs Phase 3A\n")
    rep.md_only(
        "| Pair | This run | 3A baseline | Δ |\n"
        "|------|----------|-------------|---|\n"
        f"| (0.20, 0.20) | {c1[2]:.1f}% | 26.6% | "
        f"{c1[2]-26.6:+.2f}pp |\n"
        f"| (0.15, 0.15) | {c2[2]:.1f}% | 17.1% | "
        f"{c2[2]-17.1:+.2f}pp |\n"
        f"| (0.10, 0.10) | {c3[2]:.1f}% | 7.3%  | "
        f"{c3[2]-7.3:+.2f}pp |"
    )

    # EV-after-fees table (taker-taker, 100 contracts per leg, no spread)
    CONTRACTS = 100
    rep.say("")
    rep.say("EV-after-fees (100 contracts/leg, taker-taker, no spread cost):")
    rep.md_only("")
    rep.md_only("### EV-after-fees per opportunity\n")
    rep.md_only(
        "Assumes 100 contracts per leg, taker-taker fees per "
        "`docs/FEES.md` formula `⌈0.07 × C × P × (1-P)⌉` rounded up to "
        "the cent. Gross profit = $(1 − X − Y) × 100. Spread cost is a "
        "separate Phase 3B deliverable and is **not** included here.\n\n"
        "| X | Y | Gross | Fee leg-X | Fee leg-Y | Total fees | Net | Net/Gross |\n"
        "|---|---|-------|-----------|-----------|------------|-----|-----------|"
    )
    rep.stdout_only(
        f"  {'X':>5s} {'Y':>5s}  {'Gross':>7s}  "
        f"{'FeeX':>6s}  {'FeeY':>6s}  {'Fees':>7s}  {'Net':>7s}  "
        f"{'Net/Gross':>10s}"
    )
    for (X, Y) in threshold_grid:
        gross = (1.0 - X - Y) * CONTRACTS
        if gross <= 0:
            continue
        feeX = kalshi_fee(CONTRACTS, X)
        feeY = kalshi_fee(CONTRACTS, Y)
        total_fee = feeX + feeY
        net = gross - total_fee
        pct = net / gross * 100
        rep.stdout_only(
            f"  {X:>5.2f} {Y:>5.2f}  ${gross:>6.2f}  "
            f"${feeX:>5.2f}  ${feeY:>5.2f}  ${total_fee:>6.2f}  "
            f"${net:>6.2f}  {pct:>9.1f}%"
        )
        rep.md_only(
            f"| {X:.2f} | {Y:.2f} | ${gross:.2f} | "
            f"${feeX:.2f} | ${feeY:.2f} | ${total_fee:.2f} | "
            f"${net:.2f} | {pct:.1f}% |"
        )


# ---- Preliminary verdicts section ------------------------------------

def write_verdicts(rep: Report) -> None:
    rep.md_only("")
    rep.md_only("## Preliminary §6.4 / §6.7 verdicts\n")
    rep.md_only(
        "These are preliminary interpretations intended for operator "
        "review. **Formal retirement lines are not yet written to "
        "`docs/THESIS_open_questions.md` §6 resolution log** — that "
        "dispatch will also incorporate the 9-missing-games audit "
        "from the Phase 3A RESEARCH_LOG entry so the §6 log stays "
        "coherent.\n\n"
        "- **§6.4 (pace dominates swing propensity).** See the pace "
        "correlation block above. The prediction was a positive, "
        "monotonic pace↔involvement relationship. The Spearman ρ "
        "value and its p-value are the load-bearing evidence; if ρ is "
        "a clean positive in the primary (n≥10) sample with a "
        "convincing p, retire §6.4 as confirmed. If ρ is near zero or "
        "negative, retire as denied and start looking for alternative "
        "predictors (3-point attempt rate, late-game coaching "
        "tendencies).\n\n"
        "- **§6.7 (sequential-opportunistic outperforms strict).** "
        "The hypothesis is 'modified bilateral entry raises the "
        "effective frequency enough to offset the smaller per-trade "
        "profit.' See the rate table and the EV-after-fees table "
        "above. If sequential rates are materially higher than "
        "strict rates at the same (X, Y) *and* Net/Gross after fees "
        "remains positive, the hypothesis is supported and Strategy "
        "1's addressable universe widens. The EV-per-opportunity "
        "drops in absolute terms — the question is whether frequency "
        "gains more than compensate. Retirement line pending.\n"
    )


# ---- Orchestration ---------------------------------------------------

def main() -> int:
    rep = Report()

    rep.md_only(f"# Phase 3A follow-up — {date.today().isoformat()}\n")
    rep.md_only(
        "Scope: testing two unresolved §6 hypotheses from "
        "`docs/THESIS_open_questions.md` against the 2025-26 "
        "full-regular-season ESPN WP data scraped in Phase 2.\n\n"
        "- §6.4 — Pace dominates team-level swing propensity.\n"
        "- §6.7 — Sequential-opportunistic bilateral entry raises "
        "effective frequency vs strict same-game bilateral.\n"
    )
    rep.md_only("## Data\n")

    # Load
    master = pd.read_csv(MASTER_CSV)
    master["game_id"] = master["game_id"].astype(str)

    rep.stdout_only("=" * 70)
    rep.stdout_only("Phase 3A follow-up — §6.4 pace + §6.7 sequential")
    rep.stdout_only("=" * 70)

    wp_files = list(WP_DIR.glob("*.jsonl"))
    wp = load_jsonl_glob(WP_DIR)
    pbp = load_jsonl_glob(PBP_DIR)
    rep.stdout_only(f"  master rows: {len(master):,}")
    rep.stdout_only(f"  WP rows:     {len(wp):,}  ({len(wp_files):,} files)")
    rep.stdout_only(f"  PBP rows:    {len(pbp):,}")

    games_with_wp = set(wp["game_id"].unique())
    games_in_master = set(master["game_id"])
    missing = games_in_master - games_with_wp
    rep.stdout_only(f"  Games in master: {len(games_in_master):,}")
    rep.stdout_only(f"  Games with WP:   {len(games_with_wp):,}")
    rep.stdout_only(f"  Missing WP (skipped): {len(missing)}")

    rep.md_only(
        f"- 1,243 games in `data/nba_master_2025_26.csv`; "
        f"{len(games_with_wp):,} have ESPN WP files in `data/espn_wp/`.\n"
        f"- {len(missing)} games skipped for missing WP data (a known "
        f"open item from the Phase 3A RESEARCH_LOG entry).\n"
        f"- WP rows loaded: {len(wp):,}. PBP rows loaded: {len(pbp):,}.\n"
    )

    # Parse + join
    pbp["period_num"] = pbp["period"].apply(extract_period_num)
    pbp["clock_sec"] = pbp["clock"].apply(parse_clock)
    pbp["sec_rem"] = [sec_rem_in_period(p, c)
                     for p, c in zip(pbp["period_num"], pbp["clock_sec"])]
    pbp["elapsed"] = [elapsed_sec(p, c)
                     for p, c in zip(pbp["period_num"], pbp["clock_sec"])]

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

    max_period = (pbp.groupby("game_id")["period_num"].max()
                    .reset_index()
                    .rename(columns={"period_num": "max_period"}))
    game_meta = master[["game_id", "home_team_abbrev", "away_team_abbrev",
                        "home_score", "away_score", "home_spread"]].copy()
    game_meta = game_meta.merge(max_period, on="game_id", how="left")
    scraped_gids = set(obs["game_id"].unique())
    game_meta = game_meta[game_meta["game_id"].isin(scraped_gids)].copy()
    game_meta["final_margin"] = (game_meta["home_score"]
                                 - game_meta["away_score"]).abs()
    game_meta["is_ot"] = game_meta["max_period"] > REG_PERIODS
    game_meta["home_won"] = game_meta["home_score"] > game_meta["away_score"]

    rep.stdout_only("")
    rep.stdout_only(f"  Observations after join: {len(obs):,}")
    rep.stdout_only(f"  Games in meta (post-join): {len(game_meta):,}")
    rep.stdout_only(f"  |spread|<=6 games: "
                    f"{(game_meta['home_spread'].abs() <= 6).sum()}")

    # Parts
    run_pace_analysis(rep, obs, game_meta)
    run_sequential_analysis(rep, obs, game_meta)
    write_verdicts(rep)

    rep.write(OUTPUT_MD)
    rep.stdout_only("")
    rep.stdout_only("=" * 70)
    rep.stdout_only(f"Report written to {OUTPUT_MD}")
    rep.stdout_only("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
