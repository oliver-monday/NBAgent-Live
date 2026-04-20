"""Scoring-run trajectory analysis.

Measures the causal chain Strategy 3 exploits:
  scoring run → price moves → timeout → book settles
  → momentum reverses → price reverts

Part A characterizes the per-basket price impact.
Part B measures post-timeout price trajectories for run-stopping
vs routine timeouts.
Part C sweeps run-detection parameters.
Part D synthesizes a proto-rule (or null result).

Run:
    python -m analysis.scoring_run_trajectories
    python -m analysis.scoring_run_trajectories --games HOULAL
    python -m analysis.scoring_run_trajectories --games ORLDET
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.kalshi_trades_probe import _parse_ts, build_df
from analysis.strategy3_oscillation_houlal import maker_fee, taker_fee

REPO_ROOT = Path(__file__).resolve().parents[1]
PBP_DIR = REPO_ROOT / "data" / "pbp"
TRADES_DIR = REPO_ROOT / "data" / "kalshi_trades"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "scoring_run_trajectories.md"
)

GAMES = [
    {
        "slug": "HOULAL",
        "game_id": "401869190",
        "event_ticker": "KXNBAGAME-26APR18HOULAL",
        "date": "20260418",
        "label": "HOU@LAL",
    },
    {
        "slug": "ORLDET",
        "game_id": "401869193",
        "event_ticker": "KXNBAGAME-26APR19ORLDET",
        "date": "20260419",
        "label": "ORL@DET",
    },
]

# Run-detection parameter sets for the sensitivity sweep
RUN_PARAMS = [
    (4, 120),
    (4, 180),
    (6, 120),
    (6, 180),
    (8, 240),
]

# Trajectory checkpoints (seconds from play resume)
RECOVERY_CHECKPOINTS = (60, 120, 180, 300)

# Price-impact reaction curve (seconds after scoring play wallclock)
REACTION_OFFSETS = (5, 10, 15, 30, 60)


# ---- Team ID mapping -----------------------------------------------------

def fetch_team_map(game_id: str, date: str) -> dict[str, str]:
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/basketball/"
        f"nba/scoreboard?dates={date}"
    )
    data = json.load(urllib.request.urlopen(url))
    for ev in data.get("events", []):
        if ev["id"] != game_id:
            continue
        comps = ev["competitions"][0]["competitors"]
        return {c["team"]["id"]: c["team"]["abbreviation"] for c in comps}
    raise RuntimeError(f"Game {game_id} not on scoreboard for {date}")


# ---- PBP loading ---------------------------------------------------------

def load_plays(path: Path) -> pd.DataFrame:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            wc = p.get("wallclock")
            if not wc:
                continue
            rows.append({
                "wallclock": _parse_ts(wc),
                "type_id": str(p.get("type", {}).get("id", "")),
                "type_text": p.get("type", {}).get("text", ""),
                "scoringPlay": bool(p.get("scoringPlay")),
                "scoreValue": int(p.get("scoreValue") or 0),
                "team_id": p.get("team", {}).get("id"),
                "period": (p.get("period") or {}).get("number"),
                "clock": (p.get("clock") or {}).get("displayValue"),
                "homeScore": p.get("homeScore"),
                "awayScore": p.get("awayScore"),
                "text": p.get("text", ""),
            })
    return pd.DataFrame(rows).sort_values("wallclock").reset_index(drop=True)


def is_timeout_row(row) -> bool:
    if str(row.type_id) == "16":
        return True
    return "timeout" in (row.type_text or "").lower()


# ---- Trade tape loading --------------------------------------------------

def load_trades(event_ticker: str) -> pd.DataFrame:
    cache = TRADES_DIR / f"{event_ticker}.json"
    if not cache.exists():
        raise FileNotFoundError(
            f"Trade cache {cache} missing — run kalshi_trades_probe or "
            "timeout_execution_analysis first."
        )
    with cache.open() as f:
        payload = json.load(f)
    df = build_df(payload["trades"])
    # side_team is already set by build_df (last token of ticker)
    return df


def price_at(trades: pd.DataFrame, side: str, ts: datetime,
             window_sec: float = 5.0, direction: str = "before") -> float | None:
    """Return last yes_price_dollars for `side` within `window_sec` of ts.

    direction="before": trades in [ts - window, ts]
    direction="nearest": trades within ±window of ts, nearest wins
    """
    sub = trades[trades["side_team"] == side]
    if sub.empty:
        return None
    if direction == "before":
        lo = ts - timedelta(seconds=window_sec)
        mask = (sub["created_time"] >= lo) & (sub["created_time"] <= ts)
        m = sub[mask]
        if m.empty:
            return None
        return float(m.iloc[-1]["yes_price_dollars"])
    if direction == "nearest":
        delta = (sub["created_time"] - ts).abs()
        idx = delta.idxmin()
        if delta.loc[idx] > timedelta(seconds=window_sec):
            return None
        return float(sub.loc[idx, "yes_price_dollars"])
    raise ValueError(direction)


# ---- Part A: per-basket price impact -------------------------------------

def measure_scoring_plays(
    plays: pd.DataFrame, trades: pd.DataFrame, team_map: dict[str, str],
) -> pd.DataFrame:
    rows = []
    for play in plays[plays["scoringPlay"]].itertuples():
        abbrev = team_map.get(play.team_id)
        if abbrev is None:
            continue
        t = play.wallclock
        before = price_at(trades, abbrev, t, 5.0, "before")
        if before is None:
            continue
        row = {
            "wallclock": t, "scoreValue": play.scoreValue,
            "team": abbrev, "period": play.period,
            "clock": play.clock, "text": play.text,
            "price_before": before,
        }
        for off in REACTION_OFFSETS:
            row[f"price_after_{off}s"] = price_at(
                trades, abbrev, t + timedelta(seconds=off), 3.0, "nearest",
            )
        imp_10 = row["price_after_10s"]
        imp_60 = row["price_after_60s"]
        row["immediate_impact"] = (
            imp_10 - before if imp_10 is not None else None
        )
        row["full_impact"] = (
            imp_60 - before if imp_60 is not None else None
        )
        # Reaction lag: first trade on scoring team's side at ≥ 50% of
        # full_impact within 60s after play
        lag = None
        if row["full_impact"] is not None and abs(row["full_impact"]) > 1e-6:
            target = before + 0.5 * row["full_impact"]
            sub = trades[
                (trades["side_team"] == abbrev)
                & (trades["created_time"] >= t)
                & (trades["created_time"] <= t + timedelta(seconds=60))
            ]
            sign = 1 if row["full_impact"] > 0 else -1
            for tr in sub.itertuples():
                p = float(tr.yes_price_dollars)
                if sign > 0 and p >= target:
                    lag = (tr.created_time - t).total_seconds()
                    break
                if sign < 0 and p <= target:
                    lag = (tr.created_time - t).total_seconds()
                    break
        row["reaction_lag_sec"] = lag
        rows.append(row)
    return pd.DataFrame(rows)


def play_type_label(score_value: int) -> str:
    if score_value == 3:
        return "3-pointer"
    if score_value == 2:
        return "2-pointer"
    if score_value == 1:
        return "Free throw"
    return f"Other ({score_value})"


def table_price_impact_by_type(df: pd.DataFrame) -> list[str]:
    out = ["### Table 1 — Price impact by play type", ""]
    out.append(
        "| Play value | n | Mean immediate impact ($) | "
        "Mean full impact ($) | Median reaction lag (s) |"
    )
    out.append("|---|---:|---:|---:|---:|")
    d = df.copy()
    d["label"] = d["scoreValue"].map(play_type_label)
    for label in ["2-pointer", "3-pointer", "Free throw"]:
        sub = d[d["label"] == label]
        if sub.empty:
            out.append(f"| {label} | 0 | — | — | — |")
            continue
        imm = sub["immediate_impact"].dropna()
        full = sub["full_impact"].dropna()
        lag = sub["reaction_lag_sec"].dropna()
        lag_str = f"{lag.median():.1f}" if len(lag) else "—"
        out.append(
            f"| {label} | {len(sub)} | "
            f"{imm.mean():+.4f} | "
            f"{full.mean():+.4f} | "
            f"{lag_str} |"
        )
    out.append("")
    return out


def table_price_impact_by_price(df: pd.DataFrame) -> list[str]:
    out = ["### Table 2 — Price impact by scoring-team YES price", ""]
    out.append(
        "| Scoring team YES price | n | Mean immediate impact ($) |"
    )
    out.append("|---|---:|---:|")
    buckets = [
        ("≤ 0.30", lambda p: p <= 0.30),
        ("(0.30, 0.40]", lambda p: 0.30 < p <= 0.40),
        ("(0.40, 0.50]", lambda p: 0.40 < p <= 0.50),
        ("(0.50, 0.60]", lambda p: 0.50 < p <= 0.60),
        ("(0.60, 0.70]", lambda p: 0.60 < p <= 0.70),
        ("> 0.70", lambda p: p > 0.70),
    ]
    for label, pred in buckets:
        sub = df[df["price_before"].map(pred)]
        if sub.empty:
            out.append(f"| {label} | 0 | — |")
            continue
        imm = sub["immediate_impact"].dropna()
        out.append(
            f"| {label} | {len(sub)} | {imm.mean():+.4f} |"
        )
    out.append("")
    return out


# ---- Part B: run detection + post-timeout trajectories -------------------

def detect_run(
    plays: pd.DataFrame, t: datetime, lookback_sec: int,
    team_map: dict[str, str],
) -> tuple[int, str | None, str | None]:
    """Return (margin, leading_team, trailing_team) in lookback window."""
    lo = t - timedelta(seconds=lookback_sec)
    window = plays[
        (plays["wallclock"] >= lo) & (plays["wallclock"] <= t)
        & (plays["scoringPlay"])
    ]
    by_team: dict[str, int] = {}
    for r in window.itertuples():
        ab = team_map.get(r.team_id)
        if ab is None:
            continue
        by_team[ab] = by_team.get(ab, 0) + int(r.scoreValue or 0)
    if len(by_team) < 2:
        # if only one team scored, the other was trailing
        if len(by_team) == 1:
            lead = next(iter(by_team))
            other = next(a for a in set(team_map.values()) if a != lead)
            return by_team[lead], lead, other
        return 0, None, None
    scores = sorted(by_team.items(), key=lambda kv: -kv[1])
    return scores[0][1] - scores[1][1], scores[0][0], scores[1][0]


def classify_timeouts(
    plays: pd.DataFrame, team_map: dict[str, str],
    params: list[tuple[int, int]],
) -> list[dict]:
    timeouts = plays[plays.apply(is_timeout_row, axis=1)]
    out = []
    for to in timeouts.itertuples():
        best = {"margin": 0, "leading": None, "trailing": None,
                "params": None, "is_run": False}
        for min_margin, lookback in params:
            margin, lead, trail = detect_run(
                plays, to.wallclock, lookback, team_map,
            )
            if margin >= min_margin and margin > best["margin"]:
                best = {
                    "margin": margin, "leading": lead, "trailing": trail,
                    "params": (min_margin, lookback), "is_run": True,
                }
        out.append({
            "wallclock": to.wallclock,
            "period": to.period, "clock": to.clock,
            "type_text": to.type_text,
            "team_id": to.team_id,
            **best,
        })
    return out


def first_play_after(
    plays: pd.DataFrame, t: datetime,
) -> datetime | None:
    after = plays[
        (plays["wallclock"] > t)
        & (~plays.apply(is_timeout_row, axis=1))
    ]
    return after.iloc[0]["wallclock"] if not after.empty else None


def measure_trajectory(
    to: dict, plays: pd.DataFrame, trades: pd.DataFrame,
    team_map: dict[str, str],
) -> dict:
    trail = to["trailing"]
    out = {**to, "resume_time": None, "price_at_timeout": None,
           "price_at_resume": None, "max_recovery": None,
           "time_to_max_sec": None}
    for cp in RECOVERY_CHECKPOINTS:
        out[f"recovery_{cp}s"] = None
    if trail is None:
        # fall back to "side not on team_map" — pick either side
        return out
    t0 = to["wallclock"]
    out["price_at_timeout"] = price_at(trades, trail, t0, 5.0, "before")
    resume = first_play_after(plays, t0)
    if resume is None:
        return out
    out["resume_time"] = resume
    out["price_at_resume"] = price_at(trades, trail, resume, 5.0, "nearest")
    base = out["price_at_timeout"]
    for cp in RECOVERY_CHECKPOINTS:
        p = price_at(
            trades, trail, resume + timedelta(seconds=cp), 5.0, "nearest",
        )
        out[f"recovery_{cp}s"] = (p - base) if (p is not None and base is not None) else None

    # Max recovery in [resume, resume + 5min]
    if base is not None:
        sub = trades[
            (trades["side_team"] == trail)
            & (trades["created_time"] >= resume)
            & (trades["created_time"] <= resume + timedelta(seconds=300))
        ]
        if not sub.empty:
            max_idx = sub["yes_price_dollars"].idxmax()
            max_price = float(sub.loc[max_idx, "yes_price_dollars"])
            max_ts = sub.loc[max_idx, "created_time"]
            out["max_recovery"] = max_price - base
            out["time_to_max_sec"] = (max_ts - resume).total_seconds()
    return out


# ---- Table builders ------------------------------------------------------

def trajectory_summary(traj: list[dict]) -> dict:
    s = {}
    for cp in RECOVERY_CHECKPOINTS:
        vals = [d[f"recovery_{cp}s"] for d in traj
                if d.get(f"recovery_{cp}s") is not None]
        if vals:
            s[f"recovery_{cp}s_mean"] = float(np.mean(vals))
            s[f"recovery_{cp}s_median"] = float(np.median(vals))
            s[f"recovery_{cp}s_pct_pos"] = 100 * float(np.mean([v > 0 for v in vals]))
            s[f"recovery_{cp}s_n"] = len(vals)
        else:
            for k in ("mean", "median", "pct_pos"):
                s[f"recovery_{cp}s_{k}"] = None
            s[f"recovery_{cp}s_n"] = 0
    mx = [d["max_recovery"] for d in traj if d.get("max_recovery") is not None]
    tt = [d["time_to_max_sec"] for d in traj if d.get("time_to_max_sec") is not None]
    s["max_mean"] = float(np.mean(mx)) if mx else None
    s["max_median"] = float(np.median(mx)) if mx else None
    s["max_pct_pos"] = 100 * float(np.mean([v > 0 for v in mx])) if mx else None
    s["time_to_max_median"] = float(np.median(tt)) if tt else None
    return s


def table_trajectory(s: dict, heading: str) -> list[str]:
    out = [f"### {heading}", ""]
    out.append("| Metric | Mean | Median | % positive | n |")
    out.append("|---|---:|---:|---:|---:|")
    for cp in RECOVERY_CHECKPOINTS:
        m = s.get(f"recovery_{cp}s_mean")
        med = s.get(f"recovery_{cp}s_median")
        pct = s.get(f"recovery_{cp}s_pct_pos")
        n = s.get(f"recovery_{cp}s_n", 0)
        if m is None:
            out.append(
                f"| Recovery @ {cp//60 if cp>=60 else cp} "
                f"{'min' if cp>=60 else 's'} | — | — | — | 0 |"
            )
        else:
            out.append(
                f"| Recovery @ {cp//60 if cp>=60 else cp} "
                f"{'min' if cp>=60 else 's'} | "
                f"{m:+.4f} | {med:+.4f} | {pct:.0f}% | {n} |"
            )
    m = s.get("max_mean"); med = s.get("max_median"); pct = s.get("max_pct_pos")
    if m is not None:
        out.append(
            f"| Max recovery | {m:+.4f} | {med:+.4f} | {pct:.0f}% | — |"
        )
    tt = s.get("time_to_max_median")
    if tt is not None:
        out.append(f"| Time to max (s, median) | — | {tt:.0f} | — | — |")
    out.append("")
    return out


def table_run_vs_routine(run_s: dict, routine_s: dict) -> list[str]:
    out = ["### Table 5 — Run-stopping vs routine", ""]
    out.append("| Metric | Run-stopping | Routine | Delta |")
    out.append("|---|---:|---:|---:|")

    def row(label, k):
        r = run_s.get(k); o = routine_s.get(k)
        if r is None or o is None:
            out.append(f"| {label} | — | — | — |")
        else:
            out.append(f"| {label} | {r:+.4f} | {o:+.4f} | {r - o:+.4f} |")

    row("Mean recovery @ 3 min", "recovery_180s_mean")
    r = run_s.get("recovery_180s_pct_pos"); o = routine_s.get("recovery_180s_pct_pos")
    if r is not None and o is not None:
        out.append(
            f"| % positive @ 3 min | {r:.0f}% | {o:.0f}% | {r - o:+.0f}pp |"
        )
    else:
        out.append("| % positive @ 3 min | — | — | — |")
    row("Mean max recovery", "max_mean")
    out.append("")
    return out


def table_parameter_sweep(
    per_timeout: list[dict], params: list[tuple[int, int]],
) -> tuple[list[str], dict]:
    """For each (margin, lookback), classify then measure. Returns table
    rows + the best params (by % positive @ 3min)."""
    out = ["### Table 6 — Run-detection parameter sensitivity", ""]
    out.append(
        "| Params (margin, lookback) | Run-stopping count | "
        "Mean recovery @ 3 min | % positive @ 3 min | n w/ 3min data |"
    )
    out.append("|---|---:|---:|---:|---:|")
    best = {"params": None, "pct": -1.0, "mean": None, "n": 0}
    rows = []
    for margin, lookback in params:
        matching = [
            d for d in per_timeout
            if d.get("per_param", {}).get((margin, lookback))
        ]
        s = trajectory_summary(matching)
        pct = s.get("recovery_180s_pct_pos")
        mean = s.get("recovery_180s_mean")
        n = s.get("recovery_180s_n", 0)
        row = {
            "params": (margin, lookback), "count": len(matching),
            "mean_3min": mean, "pct_3min": pct, "n_3min": n,
        }
        rows.append(row)
        mean_s = f"{mean:+.4f}" if mean is not None else "—"
        pct_s = f"{pct:.0f}%" if pct is not None else "—"
        out.append(
            f"| ({margin}, {lookback}s) | {len(matching)} | {mean_s} | "
            f"{pct_s} | {n} |"
        )
        if pct is not None and pct > best["pct"] and n >= 2:
            best = {"params": (margin, lookback), "pct": pct,
                    "mean": mean, "n": n}
    out.append("")
    return out, best, rows


# ---- Per-game orchestration ---------------------------------------------

def run_game(game: dict) -> dict:
    print(f"\n=== {game['label']} ({game['game_id']}) ===")
    team_map = fetch_team_map(game["game_id"], game["date"])
    print(f"  Team map: {team_map}")

    pbp_path = PBP_DIR / f"{game['game_id']}.jsonl"
    if not pbp_path.exists():
        from scrapers.espn_scraper import save_game, scrape_game
        d = scrape_game(game["game_id"])
        if d:
            save_game(d)
    plays = load_plays(pbp_path)
    print(f"  PBP: {len(plays)} plays, "
          f"{int(plays['scoringPlay'].sum())} scoring plays")

    trades = load_trades(game["event_ticker"])
    print(f"  Trades: {len(trades):,}")

    # Part A
    impact_df = measure_scoring_plays(plays, trades, team_map)
    print(f"  Scoring plays with trade-tape coverage: {len(impact_df)}")

    # Part B
    classified = classify_timeouts(plays, team_map, RUN_PARAMS)
    trajectories = [
        measure_trajectory(c, plays, trades, team_map) for c in classified
    ]

    # Per-param classification for the sweep
    for traj in trajectories:
        traj["per_param"] = {}
        for margin, lookback in RUN_PARAMS:
            m, lead, trail = detect_run(
                plays, traj["wallclock"], lookback, team_map,
            )
            traj["per_param"][(margin, lookback)] = (m >= margin)

    n_run = sum(1 for t in classified if t["is_run"])
    print(f"  Timeouts: {len(classified)} total, "
          f"{n_run} run-stopping, {len(classified) - n_run} routine")

    return {
        "game": game,
        "team_map": team_map,
        "plays": plays,
        "trades": trades,
        "impact": impact_df,
        "trajectories": trajectories,
    }


# ---- Proto-rule synthesis ------------------------------------------------

def build_proto_rule(
    run_summary: dict, best_param: dict, n_run_stopping: int,
    n_games: int,
) -> list[str]:
    out = ["## Part D — Strategy 3 entry rule synthesis", ""]
    pct = best_param.get("pct")
    mean = best_param.get("mean")
    if (pct is None) or (pct < 55) or (best_param.get("params") is None):
        out.append(
            "**Null result.** The momentum-reversal thesis is not "
            "supported by the current data. Post-timeout trajectory is not "
            "directionally predictable enough at any tested parameter set "
            f"(best % positive @ 3 min = "
            f"{'—' if pct is None else f'{pct:.0f}%'}, below the 55% "
            "threshold required for a rule). "
            f"n={n_run_stopping} run-stopping timeouts across {n_games} "
            "games is thin — not enough to either confirm or retire the "
            "thesis. Collect more playoff games before revisiting."
        )
        out.append("")
        return out
    margin, lookback = best_param["params"]
    max_mean = run_summary.get("max_mean") or 0.0
    max_median = run_summary.get("max_median") or 0.0
    time_to_max = run_summary.get("time_to_max_median") or 0.0
    rec_3 = run_summary.get("recovery_180s_mean") or 0.0
    rec_3_pct = run_summary.get("recovery_180s_pct_pos") or 0.0

    gross = max_mean * 100
    entry_price = 0.40  # illustrative midpoint of Strategy 3 zone
    fees = maker_fee(100, entry_price) + maker_fee(
        100, entry_price + max_mean
    )
    net = gross - fees

    out.append(
        f"**Signal:** Trailing team outscored by ≥ {margin} points in "
        f"the {lookback}s before a timeout."
    )
    out.append("")
    out.append(
        "**Entry:** During the timeout dead ball, place a maker BUY "
        "on the trailing team's YES contract at the current mid or one "
        "tick below."
    )
    out.append("")
    out.append(
        f"**Expected recovery:** Trailing team's YES price rises by a "
        f"mean of ${rec_3:+.4f} within 3 min of play resuming, "
        f"{rec_3_pct:.0f}% of the time "
        f"(n={best_param['n']} run-stopping timeouts). Mean peak "
        f"recovery ${max_mean:+.4f}, median ${max_median:+.4f}, "
        f"reached ~{time_to_max:.0f}s after resume."
    )
    out.append("")
    out.append(
        "**Exit:** Sell at entry + mean peak recovery, or at "
        f"{time_to_max:.0f}s past resume, whichever comes first."
    )
    out.append("")
    out.append(
        f"**Per-trade economics at 100 contracts (illustrative, "
        f"entry ≈ $0.40):** gross ≈ ${gross:+.2f}, maker-maker fees "
        f"≈ ${fees:.2f}, net ≈ ${net:+.2f}."
    )
    out.append("")
    out.append(
        "**Caveats.** n is small "
        f"(n={best_param['n']} at the best parameter set across "
        f"{n_games} games). Signal direction and magnitude should be "
        "re-confirmed on 8-10 more run-stopping timeouts before wiring "
        "this into a live rule."
    )
    out.append("")
    return out


# ---- Main ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=str, default=None)
    args = parser.parse_args()

    selected = GAMES
    if args.games:
        want = {s.strip().upper() for s in args.games.split(",")}
        selected = [g for g in GAMES if g["slug"] in want]

    results = [run_game(g) for g in selected]

    md: list[str] = []
    md.append("# Scoring-run trajectory analysis\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Tests the causal chain Strategy 3 depends on: scoring run → "
        "price move → timeout → book settles → momentum reverses → "
        "price reverts. Part A characterizes per-basket price impact. "
        "Part B measures post-timeout trajectories split by run-stopping "
        "vs routine. Part C sweeps run-detection parameters. Part D "
        "synthesizes a proto-rule or null result.\n"
    )

    # Data summary
    md.append("## Data summary\n")
    md.append("| Game | Plays | Scoring plays | Impact coverage | Timeouts | Run-stopping |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for r in results:
        n_score = int(r["plays"]["scoringPlay"].sum())
        n_run = sum(1 for t in r["trajectories"] if t["is_run"])
        md.append(
            f"| {r['game']['label']} | {len(r['plays'])} | {n_score} | "
            f"{len(r['impact'])} | {len(r['trajectories'])} | {n_run} |"
        )
    md.append("")

    # Part A — per-game + pooled
    md.append("## Part A — Score-to-price impact\n")
    for r in results:
        md.append(f"#### {r['game']['label']}")
        md.extend(table_price_impact_by_type(r["impact"]))
    pooled_impact = pd.concat([r["impact"] for r in results], ignore_index=True)
    md.append("#### Pooled (both games)")
    md.extend(table_price_impact_by_type(pooled_impact))
    md.extend(table_price_impact_by_price(pooled_impact))

    # Part B — per-game trajectories + pooled
    md.append("## Part B — Post-timeout trajectories\n")
    pooled_traj = [t for r in results for t in r["trajectories"]]
    run_traj = [t for t in pooled_traj if t["is_run"]]
    routine_traj = [t for t in pooled_traj if not t["is_run"]]
    run_s = trajectory_summary(run_traj)
    routine_s = trajectory_summary(routine_traj)
    md.extend(table_trajectory(
        run_s, f"Table 3 — Run-stopping timeouts (n={len(run_traj)})",
    ))
    md.extend(table_trajectory(
        routine_s, f"Table 4 — Routine timeouts (n={len(routine_traj)})",
    ))
    md.extend(table_run_vs_routine(run_s, routine_s))

    # Part B4 — per-timeout detail
    md.append("### Per-timeout detail\n")
    md.append(
        "| Game | Period | Clock | Run? | Margin | Trailing | "
        "Price@TO | Rec 3min | Rec 5min | Max rec |"
    )
    md.append("|---|---:|---|---|---:|---|---:|---:|---:|---:|")
    for r in results:
        for t in r["trajectories"]:
            fmtf = lambda v, s=".4f": "—" if v is None else f"{v:+{s}}"
            md.append(
                f"| {r['game']['label']} | Q{t['period']} | {t['clock']} | "
                f"{'✓' if t['is_run'] else '—'} | {t['margin']} | "
                f"{t['trailing'] or '—'} | "
                f"{'—' if t['price_at_timeout'] is None else f'{t['price_at_timeout']:.4f}'} | "
                f"{fmtf(t.get('recovery_180s'))} | "
                f"{fmtf(t.get('recovery_300s'))} | "
                f"{fmtf(t.get('max_recovery'))} |"
            )
    md.append("")

    # Part C — parameter sweep
    md.append("## Part C — Run-detection parameter sweep\n")
    sweep_md, best_param, sweep_rows = table_parameter_sweep(
        pooled_traj, RUN_PARAMS,
    )
    md.extend(sweep_md)

    # Best-param-specific summary (used in Part D)
    best_match = []
    if best_param.get("params"):
        for t in pooled_traj:
            if t["per_param"].get(best_param["params"]):
                best_match.append(t)
    best_summary = trajectory_summary(best_match) if best_match else run_s

    # Part D — synthesis
    md.extend(build_proto_rule(
        best_summary, best_param, len(run_traj), len(results),
    ))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(md) + "\n")
    print(f"\nReport written → {REPORT_PATH}")

    # Verification prints
    print("\n=== Table 1 (pooled) ===")
    for line in table_price_impact_by_type(pooled_impact):
        print(line)
    print("\n=== Table 3 (run-stopping) ===")
    for line in table_trajectory(run_s, f"Run-stopping (n={len(run_traj)})"):
        print(line)
    print("\n=== Table 6 (parameter sweep) ===")
    for line in sweep_md:
        print(line)
    print("\n=== Proto-rule ===")
    for line in build_proto_rule(best_summary, best_param, len(run_traj), len(results)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
