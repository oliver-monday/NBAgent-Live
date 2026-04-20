"""Strategy 3 multi-game oscillation analysis.

Generalization of `strategy3_oscillation_houlal.py` to the per-game
JSONL file split. Auto-discovers games, runs swing + round-trip +
spread + depth analysis on each, then pools cross-game stats.

Run:
    python -m analysis.strategy3_oscillation_multi --date 2026-04-19
    python -m analysis.strategy3_oscillation_multi  # ALL games
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd

from analysis.strategy3_oscillation_houlal import (
    compute_mae,
    detect_swings,
    find_round_trips,
    score_round_trip,
)

SNAP_DIR = Path("data/orderbook_snapshots")
OUTPUT_MD = Path("docs/analysis_outputs/strategy3_oscillation_multi.md")

# Ignore old pre-split date-based files (mixed games; handled elsewhere)
DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")
PER_GAME_GLOB = "KXNBAGAME-*.jsonl"
TICKER_DATE_RE = re.compile(r"KXNBAGAME-(\d{2})([A-Z]{3})(\d{2})([A-Z]{6})")
_MONTHS = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
           "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

# Tip/end heuristics.
# Prompt spec: "first snapshot where both sides have mids in (0.05, 0.95)
# and at least one side's mid changed from the previous snapshot."
# Observed on 4/19 playoff data: pre-game books often sit at a single static
# price (e.g., ORL@DET was flat at 0.785 for hours before real tip at
# 22:30 UTC) with occasional one-tick rebalancing moves — which satisfies
# the "changed from previous snapshot" rule and fires tip far too early.
# We add a rolling-window cumulative-movement requirement: at least one
# side must have moved ≥ TIP_MIN_MOVE over the last TIP_MIN_WINDOW snapshots.
# This filters out static pre-game periods while still being purely
# price-based (no external tip time needed).
TIP_LO, TIP_HI = 0.05, 0.95
TIP_MIN_WINDOW = 10
TIP_MIN_MOVE = 0.02
SETTLED_LO, SETTLED_HI = 0.02, 0.98
SETTLED_CONSECUTIVE = 5

# Round-trip grid
RT_PAIRS = [
    (0.35, 0.50), (0.35, 0.45),
    (0.40, 0.50), (0.40, 0.55),
    (0.45, 0.55), (0.45, 0.60),
]

# Spread / depth buckets (mid ≤ 0.50)
ENTRY_BUCKETS = [
    (0.00, 0.20, "≤ $0.20"),
    (0.20, 0.30, "(0.20, 0.30]"),
    (0.30, 0.40, "(0.30, 0.40]"),
    (0.40, 0.50, "(0.40, 0.50]"),
]

# HOU-LAL n=1 reference for the scorecard
HOULAL_REF = {
    "rt_freq_040_050": "100% (1/1)",
    "net_maker_median": 14.55,
    "realized_spread_median": 0.01,
    "depth_pct_50k": 50.0,
    "hold_median_min": 23.0,
    "mae_median_pct": 11.6,
}


# ---- File discovery ------------------------------------------------------

def parse_event_ticker(stem: str) -> dict | None:
    """Extract date + team codes from `KXNBAGAME-26APR19PHIBOS`."""
    m = TICKER_DATE_RE.match(stem)
    if not m:
        return None
    yy, mon, dd, teams = m.groups()
    if mon not in _MONTHS:
        return None
    try:
        date = pd.Timestamp(
            year=2000 + int(yy), month=_MONTHS[mon], day=int(dd), tz="UTC"
        )
    except ValueError:
        return None
    return {
        "event_ticker": stem,
        "date": date,
        "date_str": date.strftime("%Y-%m-%d"),
        "away": teams[:3],
        "home": teams[3:],
    }


def discover_games(date_filter: str | None) -> list[dict]:
    files: list[dict] = []
    for p in sorted(SNAP_DIR.glob(PER_GAME_GLOB)):
        if DATE_FILE_RE.match(p.name):
            continue
        info = parse_event_ticker(p.stem)
        if info is None:
            continue
        if date_filter and info["date_str"] != date_filter:
            continue
        info["path"] = p
        files.append(info)
    return files


# ---- Loading -------------------------------------------------------------

_PRICE_COLS = (
    "yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars", "no_ask_dollars",
    "last_price_dollars", "yes_bid_size_fp", "yes_ask_size_fp",
    "volume_fp", "open_interest_fp",
)


def load_game(path: Path) -> pd.DataFrame:
    rows: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    for c in _PRICE_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["mid"] = (df["yes_bid_dollars"] + df["yes_ask_dollars"]) / 2
    df["spread"] = df["yes_ask_dollars"] - df["yes_bid_dollars"]
    df["team"] = df["ticker"].str.rsplit("-", n=1).str[-1]
    df = df.drop_duplicates(subset=["ts", "ticker"])
    df = df.dropna(subset=["mid"]).sort_values(["team", "ts"]).reset_index(drop=True)
    return df


# ---- Live-window detection ----------------------------------------------

def detect_live_window_heuristic(
    side_a: pd.DataFrame, side_b: pd.DataFrame,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """Heuristic tip + settlement detection using a paired view.

    Tip: first merged timestamp where both sides' mids are in (TIP_LO,
    TIP_HI) AND at least one side's mid changed from the previous
    merged row.

    End: first run of SETTLED_CONSECUTIVE merged rows where either
    side's mid is in [0, SETTLED_LO] ∪ [SETTLED_HI, 1].
    """
    if side_a.empty or side_b.empty:
        return None, None
    a = side_a[["ts", "mid"]].rename(columns={"mid": "mid_a"}).sort_values("ts")
    b = side_b[["ts", "mid"]].rename(columns={"mid": "mid_b"}).sort_values("ts")
    merged = pd.merge_asof(
        a, b, on="ts", direction="nearest",
        tolerance=pd.Timedelta(seconds=30),
    ).dropna().reset_index(drop=True)
    if merged.empty:
        return None, None

    in_live = (
        (merged["mid_a"] > TIP_LO) & (merged["mid_a"] < TIP_HI)
        & (merged["mid_b"] > TIP_LO) & (merged["mid_b"] < TIP_HI)
    )
    # Rolling cumulative move over last TIP_MIN_WINDOW rows (max − min of mid).
    range_a = (
        merged["mid_a"].rolling(TIP_MIN_WINDOW).max()
        - merged["mid_a"].rolling(TIP_MIN_WINDOW).min()
    )
    range_b = (
        merged["mid_b"].rolling(TIP_MIN_WINDOW).max()
        - merged["mid_b"].rolling(TIP_MIN_WINDOW).min()
    )
    moving = (range_a >= TIP_MIN_MOVE) | (range_b >= TIP_MIN_MOVE)
    tip_mask = (in_live & moving).fillna(False)
    if not tip_mask.any():
        return None, None
    tip_idx = int(tip_mask.idxmax())
    # Anchor tip at the *start* of the movement window, not its end, so
    # the run-up into active play isn't trimmed off.
    tip_idx = max(0, tip_idx - (TIP_MIN_WINDOW - 1))
    tip_ts = merged.loc[tip_idx, "ts"]

    # End: scan after tip for 5 consecutive settled rows
    sub = merged.iloc[tip_idx:].reset_index(drop=True)
    settled = (
        (sub["mid_a"] <= SETTLED_LO) | (sub["mid_a"] >= SETTLED_HI)
        | (sub["mid_b"] <= SETTLED_LO) | (sub["mid_b"] >= SETTLED_HI)
    ).values
    end_ts: pd.Timestamp | None = None
    for i in range(len(settled) - SETTLED_CONSECUTIVE + 1):
        if settled[i:i + SETTLED_CONSECUTIVE].all():
            end_ts = sub.loc[i, "ts"]
            break
    if end_ts is None:
        end_ts = sub.loc[len(sub) - 1, "ts"]
    return tip_ts, end_ts


def slice_live(side: pd.DataFrame, tip_ts, end_ts) -> pd.DataFrame:
    mask = (side["ts"] >= tip_ts) & (side["ts"] <= end_ts)
    return side[mask].reset_index(drop=True)


# ---- Per-game analysis ---------------------------------------------------

def analyze_game(info: dict, min_snapshots: int) -> dict:
    """Load one game file, detect live window, run analyses, return
    a structured result dict. If skipped, `result['skip_reason']` set."""
    out: dict = {
        "info": info,
        "n_snap_total": 0,
        "teams": [],
        "skip_reason": None,
    }
    df = load_game(info["path"])
    out["n_snap_total"] = len(df)
    if df.empty:
        out["skip_reason"] = "empty file"
        return out
    teams = sorted(df["team"].unique().tolist())
    out["teams"] = teams
    if len(teams) != 2:
        out["skip_reason"] = f"expected 2 tickers, got {len(teams)}"
        return out

    sides_raw = {t: df[df["team"] == t].reset_index(drop=True) for t in teams}
    tip_ts, end_ts = detect_live_window_heuristic(
        sides_raw[teams[0]], sides_raw[teams[1]],
    )
    if tip_ts is None:
        out["skip_reason"] = "could not detect tip"
        return out
    out["tip_ts"] = tip_ts
    out["end_ts"] = end_ts

    live_sides: dict[str, pd.DataFrame] = {}
    for t in teams:
        live_sides[t] = slice_live(sides_raw[t], tip_ts, end_ts)

    n_live_min = min(len(s) for s in live_sides.values())
    out["n_live_min"] = n_live_min
    if n_live_min < min_snapshots:
        out["skip_reason"] = (
            f"only {n_live_min} live snapshots (< {min_snapshots})"
        )
        return out

    # Timeseries summary per side
    ts_summary = {}
    for t, side in live_sides.items():
        gaps = side["ts"].diff().dt.total_seconds().dropna()
        ts_summary[t] = {
            "n": len(side),
            "duration_sec": (
                (side["ts"].iloc[-1] - side["ts"].iloc[0]).total_seconds()
                if len(side) >= 2 else 0.0
            ),
            "median_gap": float(gaps.median()) if len(gaps) else 0.0,
            "p5_gap": float(gaps.quantile(0.05)) if len(gaps) else 0.0,
            "p95_gap": float(gaps.quantile(0.95)) if len(gaps) else 0.0,
            "mid_min": float(side["mid"].min()),
            "mid_max": float(side["mid"].max()),
            "mean_spread": float(side["spread"].mean()),
        }
    out["ts_summary"] = ts_summary

    # Complement check
    if len(teams) == 2:
        a, b = teams
        comp = pd.merge_asof(
            live_sides[a].sort_values("ts")[["ts", "mid"]].rename(
                columns={"mid": "mid_a"}),
            live_sides[b].sort_values("ts")[["ts", "mid"]].rename(
                columns={"mid": "mid_b"}),
            on="ts", direction="nearest",
            tolerance=pd.Timedelta(seconds=5),
        ).dropna()
        if len(comp):
            comp["sum"] = comp["mid_a"] + comp["mid_b"]
            out["comp_n"] = int(len(comp))
            out["comp_mean_dev"] = float((comp["sum"] - 1.0).abs().mean())
            out["comp_max_dev"] = float((comp["sum"] - 1.0).abs().max())

    # Swings per side
    swings_by_side: dict[str, list[dict]] = {}
    for t, side in live_sides.items():
        sw = detect_swings(side["mid"], side["ts"])
        for s in sw:
            s["side"] = t
        swings_by_side[t] = sw
    pooled_swings = [s for lst in swings_by_side.values() for s in lst]
    out["swings_by_side"] = swings_by_side
    out["n_swings_05"] = sum(1 for s in pooled_swings if s["magnitude"] >= 0.05)
    out["n_swings_10"] = sum(1 for s in pooled_swings if s["magnitude"] >= 0.10)
    out["n_swings_15"] = sum(1 for s in pooled_swings if s["magnitude"] >= 0.15)
    out["n_swings_20"] = sum(1 for s in pooled_swings if s["magnitude"] >= 0.20)
    out["max_swing"] = max((s["magnitude"] for s in pooled_swings), default=0.0)

    # Round-trips: scan both sides at each (entry, exit) pair
    rt_results: dict[tuple[float, float], list[dict]] = {}
    for entry, exit_thr in RT_PAIRS:
        trips: list[dict] = []
        for t, side in live_sides.items():
            raw = find_round_trips(side, entry, exit_thr)
            for tr in raw:
                tr["side"] = t
                scored = score_round_trip(tr, contracts=100)
                scored = compute_mae(scored, side)
                trips.append(scored)
        rt_results[(entry, exit_thr)] = trips
    out["rt_results"] = rt_results

    # Spread + depth at mid ≤ 0.50
    combined_live = pd.concat(list(live_sides.values()), ignore_index=True)
    out["combined_live"] = combined_live

    # Competitive flag: both sides spent ≥30% of live window in [0.30, 0.70]
    def _competitive(side: pd.DataFrame) -> float:
        if side.empty:
            return 0.0
        return float(((side["mid"] >= 0.30) & (side["mid"] <= 0.70)).mean())

    comp_fracs = [_competitive(s) for s in live_sides.values()]
    out["competitive"] = all(f >= 0.30 for f in comp_fracs)
    out["competitive_fracs"] = comp_fracs

    # Per-bucket spread/depth rows (for pooling later)
    out["bucket_rows"] = []
    for lo, hi, label in ENTRY_BUCKETS:
        if lo == 0:
            sub = combined_live[combined_live["mid"] <= hi]
        else:
            sub = combined_live[
                (combined_live["mid"] > lo) & (combined_live["mid"] <= hi)
            ]
        out["bucket_rows"].append({
            "label": label, "lo": lo, "hi": hi,
            "spreads": sub["spread"].dropna().tolist(),
            "depths": sub["yes_bid_size_fp"].dropna().tolist(),
        })

    return out


# ---- Rendering -----------------------------------------------------------

def _fmt_duration(sec: float) -> str:
    return f"{sec/60:.1f} min"


def render_report(
    results: list[dict], date_filter: str | None, min_snapshots: int,
) -> str:
    md: list[str] = []
    header_date = date_filter or "all dates"
    md.append(f"# Strategy 3 multi-game oscillation analysis — {header_date}\n")
    md.append(
        "Generalization of the HOU-LAL single-game oscillation analysis to "
        f"all per-game JSONL files (filter: `{header_date}`, min live "
        f"snapshots: {min_snapshots}). Uses heuristic tip detection; "
        "per-side swing + round-trip + spread + depth analyses; pooled "
        "cross-game round-trip economics.\n"
    )

    processed = [r for r in results if r.get("skip_reason") is None]
    skipped = [r for r in results if r.get("skip_reason") is not None]

    # ---- Section 1: games processed ----
    md.append("## Section 1 — Games processed\n")
    md.append("| Game | File | Teams | Live snapshots | Duration | Mean spread | Status |")
    md.append("|---|---|---|---:|---:|---:|---|")
    for r in results:
        info = r["info"]
        game_label = f"{info['away']}@{info['home']} ({info['date_str']})"
        file_label = f"`{info['path'].name}`"
        if r.get("skip_reason"):
            md.append(
                f"| {game_label} | {file_label} | — | "
                f"{r.get('n_snap_total', 0)} | — | — | "
                f"⚠ skipped: {r['skip_reason']} |"
            )
            continue
        teams = "/".join(r["teams"])
        n_live = r["n_live_min"]
        dur_sec = (r["end_ts"] - r["tip_ts"]).total_seconds()
        mean_sp = np.mean([
            r["ts_summary"][t]["mean_spread"] for t in r["teams"]
        ])
        md.append(
            f"| {game_label} | {file_label} | {teams} | {n_live:,} | "
            f"{_fmt_duration(dur_sec)} | ${mean_sp:.4f} | ok |"
        )
    md.append("")
    md.append(f"Processed: **{len(processed)}** / Skipped: **{len(skipped)}**.\n")

    if not processed:
        md.append("_No games to analyze; report ends here._\n")
        return "\n".join(md)

    # ---- Section 2: per-game oscillation summary ----
    md.append("## Section 2 — Per-game oscillation summary\n")
    md.append(
        "| Game | Swings ≥$0.10 | ≥$0.15 | Max swing | RTs (0.35,0.50) "
        "| RTs (0.40,0.50) | Mean spread | Competitive? |"
    )
    md.append(
        "|---|---:|---:|---:|---:|---:|---:|---|"
    )
    for r in processed:
        info = r["info"]
        rt_35_50 = len([
            tr for tr in r["rt_results"].get((0.35, 0.50), [])
            if not tr["incomplete"]
        ])
        rt_40_50 = len([
            tr for tr in r["rt_results"].get((0.40, 0.50), [])
            if not tr["incomplete"]
        ])
        mean_sp = np.mean([
            r["ts_summary"][t]["mean_spread"] for t in r["teams"]
        ])
        md.append(
            f"| {info['away']}@{info['home']} | "
            f"{r['n_swings_10']} | {r['n_swings_15']} | "
            f"${r['max_swing']:.3f} | {rt_35_50} | {rt_40_50} | "
            f"${mean_sp:.4f} | {'✓' if r['competitive'] else '—'} |"
        )
    md.append("")

    # ---- Section 3: pooled round-trip economics ----
    md.append("## Section 3 — Pooled round-trip economics\n")
    md.append(
        "All completed round-trips across all processed games, at each "
        "(entry, exit) pair. Fees per FEES.md: taker "
        "`ceil(0.07 × 100 × P × (1-P))`, maker `ceil(0.0175 × ...)`, "
        "applied at both legs.\n"
    )
    md.append(
        "| Entry | Exit | N games w/≥1 | Total trips | Mean hold (min) "
        "| Mean gross | Mean net (maker) | Mean MAE ($) | Mean MAE (%) |"
    )
    md.append(
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    pool_by_pair: dict[tuple[float, float], list[dict]] = {}
    for pair in RT_PAIRS:
        trips_pool: list[dict] = []
        games_with = 0
        for r in processed:
            completes = [
                tr for tr in r["rt_results"].get(pair, [])
                if not tr["incomplete"]
            ]
            if completes:
                games_with += 1
            trips_pool.extend(completes)
        pool_by_pair[pair] = trips_pool
        entry, exit_thr = pair
        if trips_pool:
            mean_hold = np.mean([tr["hold_sec"] for tr in trips_pool]) / 60
            mean_gross = np.mean([tr["gross"] for tr in trips_pool])
            mean_net = np.mean([tr["net_maker"] for tr in trips_pool])
            mean_mae = np.mean([tr["mae_drawdown"] for tr in trips_pool])
            mean_mae_pct = np.mean(
                [tr["mae_drawdown_pct"] for tr in trips_pool]
            ) * 100
            md.append(
                f"| {entry:.2f} | {exit_thr:.2f} | {games_with}/{len(processed)} | "
                f"{len(trips_pool)} | {mean_hold:.1f} | ${mean_gross:.2f} | "
                f"${mean_net:.2f} | ${mean_mae:.3f} | {mean_mae_pct:.1f}% |"
            )
        else:
            md.append(
                f"| {entry:.2f} | {exit_thr:.2f} | 0/{len(processed)} | "
                f"0 | — | — | — | — | — |"
            )
    md.append("")

    # ---- Section 4: pooled spread + depth ----
    md.append("## Section 4 — Pooled spread and depth at mid ≤ $0.50\n")
    md.append(
        "Bucketed observations across all processed games.\n\n"
        "| Mid bucket | n obs | Mean spread | Median | p75 | Mean depth "
        "| Median depth | % ≥ 50k depth |"
    )
    md.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    )
    pool_buckets: dict[str, dict] = {}
    for label in [b[2] for b in ENTRY_BUCKETS]:
        pool_buckets[label] = {"spreads": [], "depths": []}
    for r in processed:
        for row in r["bucket_rows"]:
            pool_buckets[row["label"]]["spreads"].extend(row["spreads"])
            pool_buckets[row["label"]]["depths"].extend(row["depths"])
    for lo, hi, label in ENTRY_BUCKETS:
        sp = pd.Series(pool_buckets[label]["spreads"])
        dp = pd.Series(pool_buckets[label]["depths"])
        if len(sp) == 0 and len(dp) == 0:
            md.append(f"| {label} | 0 | — | — | — | — | — | — |")
            continue
        mean_sp = sp.mean() if len(sp) else float("nan")
        med_sp = sp.median() if len(sp) else float("nan")
        p75_sp = sp.quantile(0.75) if len(sp) else float("nan")
        mean_dp = dp.mean() if len(dp) else float("nan")
        med_dp = dp.median() if len(dp) else float("nan")
        pct_50k = (dp >= 50_000).mean() * 100 if len(dp) else float("nan")
        md.append(
            f"| {label} | {len(sp):,} | ${mean_sp:.4f} | ${med_sp:.4f} | "
            f"${p75_sp:.4f} | {mean_dp:,.0f} | {med_dp:,.0f} | "
            f"{pct_50k:.0f}% |"
        )
    md.append("")

    # ---- Section 5: scorecard ----
    md.append("## Section 5 — Cross-game scorecard\n")
    md.append(
        "Viability thresholds below are illustrative graduation gates. "
        f"n={len(processed)} is still below the n=10 graduation sample.\n"
    )

    n_games = len(processed)
    trips_40_50 = pool_by_pair[(0.40, 0.50)]
    games_with_40_50 = sum(
        1 for r in processed
        if any(not tr["incomplete"]
               for tr in r["rt_results"].get((0.40, 0.50), []))
    )
    rt_freq_pct = 100 * games_with_40_50 / n_games if n_games else 0.0

    net_median = (
        median([tr["net_maker"] for tr in trips_40_50])
        if trips_40_50 else None
    )
    mae_median_pct = (
        median([tr["mae_drawdown_pct"] for tr in trips_40_50]) * 100
        if trips_40_50 else None
    )
    hold_median_min = (
        median([tr["hold_sec"] for tr in trips_40_50]) / 60
        if trips_40_50 else None
    )

    # Spread/depth at mid ≤ 0.50 (pool all buckets with lo < 0.50)
    all_spreads: list[float] = []
    all_depths: list[float] = []
    for _, _, label in ENTRY_BUCKETS:
        all_spreads.extend(pool_buckets[label]["spreads"])
        all_depths.extend(pool_buckets[label]["depths"])
    realized_spread_med = (
        float(np.median(all_spreads)) if all_spreads else None
    )
    depth_pct_50k = (
        100 * float(np.mean(np.array(all_depths) >= 50_000))
        if all_depths else None
    )

    def status(val, op, bar) -> str:
        if val is None:
            return "insufficient data"
        if op == ">=":
            return "✓" if val >= bar else "✗"
        if op == "<=":
            return "✓" if val <= bar else "✗"
        if op == "<":
            return "✓" if val < bar else "✗"
        return "?"

    md.append(
        "| Criterion | Threshold | n=1 (HOU-LAL) | n=N (pooled) | Status |"
    )
    md.append(
        "|---|---|---|---|---|"
    )
    md.append(
        f"| Round-trip frequency (% of games w/≥1 trip at 0.40,0.50) | "
        f"≥ 15% | {HOULAL_REF['rt_freq_040_050']} | "
        f"{rt_freq_pct:.0f}% ({games_with_40_50}/{n_games}) | "
        f"{status(rt_freq_pct, '>=', 15.0)} |"
    )
    md.append(
        f"| Net per trip (maker-maker, pooled median) | ≥ $5 | "
        f"${HOULAL_REF['net_maker_median']:.2f} | "
        f"{('$' + f'{net_median:.2f}') if net_median is not None else '—'} | "
        f"{status(net_median, '>=', 5.0)} |"
    )
    md.append(
        f"| Realized spread (median, mid ≤ 0.50) | ≤ $0.02 | "
        f"${HOULAL_REF['realized_spread_median']:.2f} | "
        f"{('$' + f'{realized_spread_med:.4f}') if realized_spread_med is not None else '—'} | "
        f"{status(realized_spread_med, '<=', 0.02)} |"
    )
    md.append(
        f"| Depth (% ≥ 50k at mid ≤ 0.50) | ≥ 50% | "
        f"~{HOULAL_REF['depth_pct_50k']:.0f}% | "
        f"{(f'{depth_pct_50k:.0f}%') if depth_pct_50k is not None else '—'} | "
        f"{status(depth_pct_50k, '>=', 50.0)} |"
    )
    md.append(
        f"| Hold time (median) | ≥ 3 min | "
        f"{HOULAL_REF['hold_median_min']:.0f} min | "
        f"{(f'{hold_median_min:.1f} min') if hold_median_min is not None else '—'} | "
        f"{status(hold_median_min, '>=', 3.0)} |"
    )
    md.append(
        f"| MAE (median, % of entry) | < 50% | "
        f"{HOULAL_REF['mae_median_pct']:.1f}% | "
        f"{(f'{mae_median_pct:.1f}%') if mae_median_pct is not None else '—'} | "
        f"{status(mae_median_pct, '<', 50.0)} |"
    )
    md.append("")

    # ---- Section 6: game-by-game detail ----
    md.append("## Section 6 — Game-by-game detail (appendix)\n")
    md.append("### Round-trips at (0.40, 0.50)\n")
    md.append(
        "| Game | Side | Entry ts | Entry | Exit ts | Exit | Hold (min) "
        "| Net (maker) | MAE ($) |"
    )
    md.append("|---|---|---|---:|---|---:|---:|---:|---:|")
    any_rt = False
    for r in processed:
        for tr in r["rt_results"].get((0.40, 0.50), []):
            if tr["incomplete"]:
                continue
            any_rt = True
            info = r["info"]
            md.append(
                f"| {info['away']}@{info['home']} | {tr['side']} | "
                f"{pd.Timestamp(tr['entry_ts']).strftime('%Y-%m-%d %H:%M')} | "
                f"{tr['entry_price']:.3f} | "
                f"{pd.Timestamp(tr['exit_ts']).strftime('%H:%M')} | "
                f"{tr['exit_price']:.3f} | {tr['hold_sec']/60:.1f} | "
                f"${tr['net_maker']:.2f} | ${tr['mae_drawdown']:.3f} |"
            )
    if not any_rt:
        md.append("| — | — | — | — | — | — | — | — | — |")
    md.append("")
    md.append("### Swings ≥ $0.10 (pooled both sides)\n")
    md.append(
        "| Game | Side | Type | Start | End | Magnitude | Duration |"
    )
    md.append("|---|---|---|---|---|---:|---:|")
    any_sw = False
    for r in processed:
        info = r["info"]
        for t, sw in r["swings_by_side"].items():
            for s in sw:
                if s["magnitude"] < 0.10:
                    continue
                any_sw = True
                md.append(
                    f"| {info['away']}@{info['home']} | {t} | {s['type']} | "
                    f"{pd.Timestamp(s['start_ts']).strftime('%H:%M:%S')} | "
                    f"{pd.Timestamp(s['end_ts']).strftime('%H:%M:%S')} | "
                    f"${s['magnitude']:.3f} | "
                    f"{s['duration_sec']/60:.1f} min |"
                )
    if not any_sw:
        md.append("| — | — | — | — | — | — | — |")
    md.append("")

    return "\n".join(md)


# ---- Main ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date", type=str, default=None,
        help="Filter to games from this date (YYYY-MM-DD). "
             "If omitted, process ALL per-game files.",
    )
    parser.add_argument(
        "--min-snapshots", type=int, default=50,
        help="Skip games with fewer than this many live snapshots "
             "(partial captures or blowouts with early exit)",
    )
    args = parser.parse_args()

    games = discover_games(args.date)
    if not games:
        raise SystemExit(
            f"No per-game files matched (date={args.date}). "
            f"Checked {SNAP_DIR / PER_GAME_GLOB}"
        )
    print(f"Discovered {len(games)} game file(s):")
    for g in games:
        print(f"  - {g['event_ticker']} ({g['away']}@{g['home']}, {g['date_str']})")

    results: list[dict] = []
    for i, info in enumerate(games, 1):
        label = f"{info['away']}@{info['home']}"
        print(f"\nProcessing game {i}/{len(games)}: {label}...")
        res = analyze_game(info, args.min_snapshots)
        if res.get("skip_reason"):
            print(f"  SKIP: {res['skip_reason']}")
        else:
            tip = res["tip_ts"]
            end = res["end_ts"]
            dur_min = (end - tip).total_seconds() / 60
            print(f"  tip: {tip}  end: {end}  ({dur_min:.1f} min)")
            print(
                f"  live snapshots (min per side): {res['n_live_min']:,}  "
                f"swings ≥$0.10: {res['n_swings_10']}  "
                f"competitive: {res['competitive']}"
            )
        results.append(res)

    md = render_report(results, args.date, args.min_snapshots)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(md + "\n")
    print(f"\nReport written → {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
