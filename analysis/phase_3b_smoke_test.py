"""
Phase 3B smoke test — paired Kalshi orderbook ↔ ESPN WP analysis.

Joins Kalshi snapshots (data/orderbook_snapshots/*.jsonl) with ESPN
WP timeseries (data/espn_wp/*.jsonl) at matched wallclock timestamps
via asof-merge, and reports the Kalshi-vs-ESPN residual distribution.

This is NOT formal Phase 3B — it's an n=2 smoke test of the paired-
data pipeline and the first real §1.1 read. Formal Phase 3B requires
≥5-10 games.

Usage:
  python -m analysis.phase_3b_smoke_test
  python -m analysis.phase_3b_smoke_test 401866758 401866759

If no gameIds are provided, auto-discovers all games that have both
an ESPN WP file and matching Kalshi event_ticker snapshots.

Report written to docs/analysis_outputs/3b_smoke_test_2026_04_18.md.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Reuse conventions from Phase 3A follow-up
from analysis.phase_3a_followup import Report
from scrapers.espn_scraper import _norm_team, scrape_game

KALSHI_DIR = Path("data/orderbook_snapshots")
WP_DIR = Path("data/espn_wp")
PBP_DIR = Path("data/pbp")
OUTPUT_MD = Path("docs/analysis_outputs/3b_smoke_test_2026_04_18.md")

# Same bucket edges as Phase 3A calibration for direct comparability
CALIB_BUCKETS = [0.0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20,
                 0.25, 0.35, 0.50, 0.65, 0.75, 0.85, 0.90, 0.925, 0.95,
                 0.975, 1.0]

ASOF_TOLERANCE_SEC = 300


# ---- Loaders ---------------------------------------------------------

def load_kalshi_all() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(KALSHI_DIR.glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                r.pop("orderbook", None)  # drop the heavy nested blob
                rows.append(r)
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    price_cols = [
        "yes_bid_dollars", "yes_ask_dollars",
        "no_bid_dollars", "no_ask_dollars",
        "last_price_dollars", "yes_bid_size_fp", "yes_ask_size_fp",
        "no_bid_size_fp", "no_ask_size_fp", "liquidity_dollars",
        "volume_fp", "volume_24h_fp", "open_interest_fp",
    ]
    for c in price_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["kalshi_mid"] = (df["yes_bid_dollars"] + df["yes_ask_dollars"]) / 2
    df["team_suffix"] = df["ticker"].str.rsplit("-", n=1).str[-1]
    df = df.sort_values("ts").reset_index(drop=True)
    return df


def parse_event_teams(event_ticker: str) -> tuple[str, str]:
    """Extract (away, home) standard abbreviations from a per-game event ticker.

    Kalshi event_ticker format: <SERIES>-YYMMMDD<AWAY><HOME>, with AWAY
    and HOME as 3-char NBA abbreviations. Returns empty strings if the
    ticker doesn't match the per-game shape."""
    parts = event_ticker.split("-")
    if len(parts) < 2:
        return ("", "")
    tail = parts[-1]
    # Date prefix is 7 chars: YY + MMM + DD, e.g., "26APR17"
    matchup = tail[7:]
    if len(matchup) != 6 or not matchup.isalpha():
        return ("", "")
    return (_norm_team(matchup[:3]), _norm_team(matchup[3:]))


def load_espn_timeline(game_id: str) -> pd.DataFrame:
    """Load ESPN WP + PBP and join on playId ↔ id. Return per-play
    timeline with wallclock, home_wp, period, clock, scores."""
    wp_path = WP_DIR / f"{game_id}.jsonl"
    pbp_path = PBP_DIR / f"{game_id}.jsonl"
    wp_rows = [json.loads(L) for L in wp_path.read_text().splitlines() if L.strip()]
    pbp_rows = [json.loads(L) for L in pbp_path.read_text().splitlines() if L.strip()]
    wp = pd.DataFrame(wp_rows)
    pbp = pd.DataFrame(pbp_rows)

    merged = wp.merge(
        pbp,
        left_on=["game_id", "playId"], right_on=["game_id", "id"],
        how="inner",
    )
    merged["wallclock_dt"] = pd.to_datetime(
        merged["wallclock"], utc=True, errors="coerce"
    )
    merged["home_wp"] = pd.to_numeric(
        merged["homeWinPercentage"], errors="coerce"
    )
    merged["period_num"] = merged["period"].apply(
        lambda p: p.get("number") if isinstance(p, dict) else p
    )
    merged["clock_str"] = merged["clock"].apply(
        lambda c: c.get("displayValue") if isinstance(c, dict) else c
    )
    merged = merged.dropna(
        subset=["wallclock_dt", "home_wp"]
    ).sort_values("wallclock_dt").reset_index(drop=True)
    return merged[
        ["game_id", "playId", "wallclock_dt", "home_wp",
         "period_num", "clock_str", "homeScore", "awayScore"]
    ]


# ---- Matching and joining -------------------------------------------

def match_game(espn_home: str, espn_away: str,
               kalshi_events: pd.DataFrame) -> str | None:
    """Find the Kalshi event_ticker matching a given ESPN (home, away)
    team pair. kalshi_events has columns event_ticker, away_team,
    home_team (all normalized)."""
    h = _norm_team(espn_home)
    a = _norm_team(espn_away)
    hit = kalshi_events[
        (kalshi_events["away_team"] == a) & (kalshi_events["home_team"] == h)
    ]
    if len(hit) == 0:
        # Try reversed order defensively — shouldn't happen if Kalshi
        # convention holds, but guards against ticker-order surprises.
        hit = kalshi_events[
            (kalshi_events["away_team"] == h) & (kalshi_events["home_team"] == a)
        ]
    if len(hit) == 0:
        return None
    return hit["event_ticker"].iloc[0]


def asof_join_side(
    kalshi_side: pd.DataFrame,
    espn_timeline: pd.DataFrame,
    tolerance_sec: int = ASOF_TOLERANCE_SEC,
) -> pd.DataFrame:
    """As-of merge Kalshi ticker observations against the ESPN timeline.
    For each Kalshi ts, carry forward the most recent ESPN play's
    home_wp, dropping rows with no play within tolerance."""
    kalshi_sorted = kalshi_side.sort_values("ts").reset_index(drop=True)
    espn_sorted = espn_timeline.sort_values("wallclock_dt").reset_index(drop=True)
    joined = pd.merge_asof(
        kalshi_sorted,
        espn_sorted[[
            "wallclock_dt", "home_wp", "period_num", "clock_str",
            "homeScore", "awayScore",
        ]],
        left_on="ts", right_on="wallclock_dt",
        direction="backward",
        tolerance=pd.Timedelta(seconds=tolerance_sec),
    )
    return joined


# ---- Report helpers --------------------------------------------------

def _pct(x: float) -> str:
    if pd.isna(x):
        return "—"
    return f"{x*100:+.2f}pp" if abs(x) < 1 else f"{x:.2f}"


def residual_bucket_table(pooled: pd.DataFrame, rep: Report, label: str) -> None:
    sub = pooled.dropna(subset=["espn_wp", "kalshi_mid_side", "residual"]).copy()
    if sub.empty:
        rep.say(f"  {label}: no data after filtering.")
        return
    sub["bucket"] = pd.cut(
        sub["espn_wp"], bins=CALIB_BUCKETS, include_lowest=True, right=True
    )
    agg = sub.groupby("bucket", observed=True).agg(
        n=("residual", "size"),
        mean_espn=("espn_wp", "mean"),
        mean_kalshi=("kalshi_mid_side", "mean"),
        mean_residual=("residual", "mean"),
    )
    agg["mean_residual_pp"] = agg["mean_residual"] * 100

    rep.say("")
    rep.say(f"--- {label} ---")
    hdr = f"{'bucket':<18s} {'n':>6s}  {'mean ESPN':>10s}  {'mean Kalshi':>11s}  {'residual (pp)':>14s}"
    rep.stdout_only(hdr)
    rep.md_only(f"\n#### {label}\n")
    rep.md_only(
        "| bucket | n | mean ESPN | mean Kalshi | residual (pp) |\n"
        "|--------|---|-----------|-------------|---------------|"
    )
    for idx, row in agg.iterrows():
        rep.stdout_only(
            f"{str(idx):<18s} {int(row['n']):>6d}  "
            f"{row['mean_espn']:>10.3f}  {row['mean_kalshi']:>11.3f}  "
            f"{row['mean_residual_pp']:>+13.2f}"
        )
        rep.md_only(
            f"| {str(idx)} | {int(row['n'])} | {row['mean_espn']:.3f} | "
            f"{row['mean_kalshi']:.3f} | {row['mean_residual_pp']:+.2f} |"
        )


# ---- Per-game analysis ----------------------------------------------

def analyze_game(
    rep: Report,
    game_id: str,
    meta: dict[str, Any],
    kalshi_home_side: pd.DataFrame,
    kalshi_away_side: pd.DataFrame,
    espn_timeline: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return (pooled_residuals_df, per_game_summary) for the game."""
    home_team = meta["home_team"]
    away_team = meta["away_team"]
    home_score = next(
        (int(t["score"]) for t in meta["teams"] if t["home_away"] == "home"),
        None,
    )
    away_score = next(
        (int(t["score"]) for t in meta["teams"] if t["home_away"] == "away"),
        None,
    )

    rep.stdout_only(f"\n--- Game {game_id}: {away_team} {away_score} @ {home_team} {home_score} ---")
    rep.md_only(
        f"\n### {game_id} — {away_team} {away_score} @ {home_team} {home_score}\n"
    )

    tip_ts = espn_timeline["wallclock_dt"].iloc[0]
    end_ts = espn_timeline["wallclock_dt"].iloc[-1]
    rep.stdout_only(f"  ESPN timeline: {len(espn_timeline)} plays,"
                    f" {tip_ts} → {end_ts}")

    # ---- Asof-join both sides against ESPN timeline ----
    home_joined = asof_join_side(kalshi_home_side, espn_timeline)
    away_joined = asof_join_side(kalshi_away_side, espn_timeline)

    # Drop rows with no ESPN match (pre-tip, halftime, post-end)
    home_live = home_joined.dropna(subset=["home_wp"]).copy()
    away_live = away_joined.dropna(subset=["home_wp"]).copy()

    rep.stdout_only(f"  Kalshi home-side (full): {len(kalshi_home_side):,}  "
                    f"joined+live: {len(home_live):,}")
    rep.stdout_only(f"  Kalshi away-side (full): {len(kalshi_away_side):,}  "
                    f"joined+live: {len(away_live):,}")

    # Kalshi mid range check
    if len(home_live):
        rep.stdout_only(f"  home-side kalshi_mid range: "
                        f"[{home_live['kalshi_mid'].min():.3f}, "
                        f"{home_live['kalshi_mid'].max():.3f}]")

    # ---- Sanity check: market complement ----
    # Pair home and away at matched Kalshi timestamps.
    complement = pd.merge_asof(
        home_live.sort_values("ts")[["ts", "kalshi_mid"]].rename(
            columns={"kalshi_mid": "mid_home"}
        ),
        away_live.sort_values("ts")[["ts", "kalshi_mid"]].rename(
            columns={"kalshi_mid": "mid_away"}
        ),
        on="ts", direction="nearest",
        tolerance=pd.Timedelta(seconds=5),
    ).dropna()
    if len(complement):
        complement["sum"] = complement["mid_home"] + complement["mid_away"]
        mean_dev = (complement["sum"] - 1.0).abs().mean()
        max_dev = (complement["sum"] - 1.0).abs().max()
        rep.stdout_only(f"  complement check (home+away mid vs 1.00): "
                        f"n={len(complement)}, mean |dev|={mean_dev:.4f}, "
                        f"max |dev|={max_dev:.4f}")
        rep.md_only(
            f"- Market complement check (home mid + away mid vs 1.00): "
            f"n={len(complement)}, mean |dev|={mean_dev:.4f}, "
            f"max |dev|={max_dev:.4f}"
        )
        complement_stats = {
            "n": len(complement), "mean_dev": mean_dev, "max_dev": max_dev,
        }
    else:
        complement_stats = None
        rep.stdout_only("  complement check: no matched pairs")

    # ---- Build pooled residual frame: one row per side per snapshot ----
    home_pooled = home_live.assign(
        side="home",
        espn_wp=home_live["home_wp"],
        kalshi_mid_side=home_live["kalshi_mid"],
    )
    away_pooled = away_live.assign(
        side="away",
        espn_wp=1.0 - away_live["home_wp"],
        kalshi_mid_side=away_live["kalshi_mid"],
    )
    pooled = pd.concat([
        home_pooled[[
            "ts", "side", "espn_wp", "kalshi_mid_side",
            "yes_bid_size_fp", "yes_ask_size_fp",
            "period_num", "clock_str", "homeScore", "awayScore",
        ]],
        away_pooled[[
            "ts", "side", "espn_wp", "kalshi_mid_side",
            "yes_bid_size_fp", "yes_ask_size_fp",
            "period_num", "clock_str", "homeScore", "awayScore",
        ]],
    ], ignore_index=True)
    pooled["residual"] = pooled["kalshi_mid_side"] - pooled["espn_wp"]
    pooled["game_id"] = game_id

    # ---- Screenshot cross-check: CHA-ORL end-of-Q1 ----
    if home_team == "ORL" and away_team == "CHA":
        # Last play in Q1 (end-of-quarter)
        q1 = espn_timeline[espn_timeline["period_num"] == 1]
        if len(q1):
            p_last = q1.iloc[-1]
            target_ts = p_last["wallclock_dt"]
            ascore = int(p_last["awayScore"])
            hscore = int(p_last["homeScore"])
            h_near = home_live.iloc[
                (home_live["ts"] - target_ts).abs().argsort().iloc[:1]
            ]
            a_near = away_live.iloc[
                (away_live["ts"] - target_ts).abs().argsort().iloc[:1]
            ]
            if len(h_near) and len(a_near):
                h_mid = float(h_near["kalshi_mid"].iloc[0])
                a_mid = float(a_near["kalshi_mid"].iloc[0])
                h_wp = float(h_near["home_wp"].iloc[0])
                rep.stdout_only(
                    f"  end-Q1 CHA {ascore} - ORL {hscore} @ {target_ts}:"
                    f" Kalshi ORL mid={h_mid:.3f}, CHA mid={a_mid:.3f},"
                    f" ESPN ORL WP={h_wp:.3f} (CHA WP={1-h_wp:.3f})"
                )
                rep.md_only(
                    f"\n**Screenshot cross-check — end of Q1:**\n\n"
                    f"- Score: CHA {ascore} – ORL {hscore} "
                    f"(wallclock {target_ts})\n"
                    f"- Kalshi ORL mid: `{h_mid:.3f}`; Kalshi CHA mid: "
                    f"`{a_mid:.3f}`\n"
                    f"- ESPN ORL WP: `{h_wp:.3f}`; ESPN CHA WP: "
                    f"`{1-h_wp:.3f}`\n"
                    f"- User-reported screenshots at Q1 end: "
                    f"Kalshi CHA ~17%, ESPN CHA ~8.6%."
                )

    # ---- Start-of-game snapshot ----
    first_play = espn_timeline.iloc[0]
    tip_ts_val = first_play["wallclock_dt"]
    h_tip = home_live.iloc[
        (home_live["ts"] - tip_ts_val).abs().argsort().iloc[:1]
    ]
    if len(h_tip):
        rep.stdout_only(f"  start-of-game ({tip_ts_val}): ESPN home_wp="
                        f"{float(h_tip['home_wp'].iloc[0]):.3f}, "
                        f"Kalshi home_mid="
                        f"{float(h_tip['kalshi_mid'].iloc[0]):.3f}")

    # ---- Per-game summary ----
    summary = {
        "game_id": game_id,
        "home": home_team, "away": away_team,
        "home_score": home_score, "away_score": away_score,
        "paired_n": int(len(home_live) + len(away_live)),
        "home_n": int(len(home_live)), "away_n": int(len(away_live)),
        "kalshi_home_range": (
            (float(home_live["kalshi_mid"].min()),
             float(home_live["kalshi_mid"].max()))
            if len(home_live) else (np.nan, np.nan)
        ),
        "complement": complement_stats,
    }

    # ---- Quarter-boundary timeline for narrative sanity ----
    rep.md_only("\n**Per-game residual timeline (quarter boundaries):**\n")
    rep.md_only(
        "| moment | wallclock | ESPN home_wp | Kalshi home mid | Kalshi away mid |\n"
        "|--------|-----------|--------------|-----------------|-----------------|"
    )
    quarters = [1, 2, 3, 4]
    for q in quarters:
        plays_q = espn_timeline[espn_timeline["period_num"] == q]
        if len(plays_q) == 0:
            continue
        start_play = plays_q.iloc[0]
        end_play = plays_q.iloc[-1]
        for label, p in (("start Q" + str(q), start_play),
                         ("end Q" + str(q), end_play)):
            wc = p["wallclock_dt"]
            h_close = home_live.iloc[
                (home_live["ts"] - wc).abs().argsort().iloc[:1]
            ] if len(home_live) else home_live
            a_close = away_live.iloc[
                (away_live["ts"] - wc).abs().argsort().iloc[:1]
            ] if len(away_live) else away_live
            h_mid = float(h_close["kalshi_mid"].iloc[0]) if len(h_close) else np.nan
            a_mid = float(a_close["kalshi_mid"].iloc[0]) if len(a_close) else np.nan
            h_wp = float(p["home_wp"])
            rep.md_only(
                f"| {label} | {wc.strftime('%H:%M:%S')} | "
                f"{h_wp:.3f} | {h_mid:.3f} | {a_mid:.3f} |"
            )

    # ---- Extreme-price liquidity read (§2.1 first look) ----
    extreme = pooled[pooled["kalshi_mid_side"] <= 0.20]
    if len(extreme):
        rep.md_only(
            f"\n**Liquidity at extreme-low prices (kalshi_mid ≤ 0.20):**"
            f" n={len(extreme)}, mean yes_bid_size_fp="
            f"{extreme['yes_bid_size_fp'].mean():,.0f}, "
            f"median yes_bid_size_fp="
            f"{extreme['yes_bid_size_fp'].median():,.0f}\n"
        )
        rep.stdout_only(f"  extreme-low (mid≤0.20): n={len(extreme)}, "
                        f"mean yes_bid_size_fp="
                        f"{extreme['yes_bid_size_fp'].mean():,.0f}")

    return pooled, summary


# ---- Main ------------------------------------------------------------

def main(argv: list[str]) -> int:
    rep = Report()
    rep.md_only(f"# Phase 3B smoke test — {date.today().isoformat()}\n")
    rep.md_only(
        "First paired Kalshi–ESPN analysis on n=2 games (CHA-ORL and "
        "GSW-PHX Play-In, 2026-04-17). **Not formal Phase 3B.** Joins "
        "Kalshi orderbook snapshots with ESPN WP at matched wallclock "
        "timestamps via as-of merge (300s backward tolerance).\n"
    )
    rep.md_only("## Data\n")

    # ---- Load Kalshi ----
    rep.stdout_only("=" * 70)
    rep.stdout_only("Phase 3B smoke test — Kalshi ↔ ESPN WP paired analysis")
    rep.stdout_only("=" * 70)
    rep.stdout_only("\nLoading Kalshi snapshots…")
    kalshi = load_kalshi_all()
    rep.stdout_only(f"  rows: {len(kalshi):,}")
    rep.stdout_only(f"  tickers: {kalshi['ticker'].nunique()}")
    rep.stdout_only(f"  ts range: {kalshi['ts'].min()} → {kalshi['ts'].max()}")

    # ---- Summarize event_tickers and teams ----
    events = (
        kalshi.groupby("event_ticker", as_index=False)
        .agg(n=("ts", "size"))
    )
    events["away_team"], events["home_team"] = zip(
        *events["event_ticker"].map(parse_event_teams)
    )
    rep.stdout_only("\nKalshi events and inferred teams:")
    for _, r in events.iterrows():
        rep.stdout_only(
            f"  {r['event_ticker']}: away={r['away_team']} "
            f"home={r['home_team']}  n={int(r['n']):,}"
        )

    # ---- Discover games to analyze ----
    if len(argv) > 1:
        game_ids = argv[1:]
    else:
        # Auto-discover: ESPN WP files whose (home,away) match a Kalshi event
        game_ids = []
        for wp_path in sorted(WP_DIR.glob("*.jsonl")):
            if wp_path.stat().st_size == 0:
                continue
            gid = wp_path.stem
            try:
                g = scrape_game(gid)
            except Exception:
                continue
            if not g:
                continue
            m = g["metadata"]
            match = match_game(m["home_team"], m["away_team"], events)
            if match:
                game_ids.append(gid)

    rep.stdout_only(f"\nGames to analyze: {game_ids}")

    if not game_ids:
        rep.stdout_only("No games matched. Nothing to do.")
        return 1

    rep.md_only(
        f"- Kalshi: {len(kalshi):,} snapshots across "
        f"{kalshi['ticker'].nunique()} tickers.\n"
        f"- ESPN games analyzed: {len(game_ids)}.\n"
        f"- As-of merge tolerance: {ASOF_TOLERANCE_SEC}s backward.\n"
    )

    rep.md_only("## Per-game analysis\n")

    all_pooled: list[pd.DataFrame] = []
    summaries: list[dict[str, Any]] = []
    for gid in game_ids:
        g = scrape_game(gid)
        if not g:
            rep.stdout_only(f"  ✗ {gid}: ESPN fetch failed; skipping")
            continue
        m = g["metadata"]
        event_key = match_game(m["home_team"], m["away_team"], events)
        if not event_key:
            rep.stdout_only(f"  ✗ {gid}: no Kalshi match for "
                            f"{m['away_team']}@{m['home_team']}")
            continue
        home_side = kalshi[
            (kalshi["event_ticker"] == event_key)
            & (kalshi["team_suffix"] == m["home_team"])
        ].copy()
        away_side = kalshi[
            (kalshi["event_ticker"] == event_key)
            & (kalshi["team_suffix"] == m["away_team"])
        ].copy()
        espn_timeline = load_espn_timeline(gid)

        pooled, summary = analyze_game(
            rep, gid, m, home_side, away_side, espn_timeline,
        )
        all_pooled.append(pooled)
        summaries.append(summary)

    if not all_pooled:
        rep.stdout_only("No games successfully analyzed.")
        return 1

    pooled_all = pd.concat(all_pooled, ignore_index=True)
    pooled_all = pooled_all.dropna(subset=["residual"])

    # ---- Section A: per-game summary ----
    rep.say("")
    rep.say("=" * 70)
    rep.say("A. Per-game summary")
    rep.md_only("\n## A. Per-game summary\n")
    rep.md_only(
        "| Game | gameId | Home | Away | Final | Paired obs | Kalshi home range |\n"
        "|------|--------|------|------|-------|-----------|-------------------|"
    )
    for s in summaries:
        rng = s["kalshi_home_range"]
        rng_str = f"[{rng[0]:.3f}, {rng[1]:.3f}]" if not pd.isna(rng[0]) else "—"
        rep.md_only(
            f"| {s['away']}@{s['home']} | {s['game_id']} | "
            f"{s['home']} | {s['away']} | "
            f"{s['away_score']}-{s['home_score']} | "
            f"{s['paired_n']} | {rng_str} |"
        )

    # ---- Section B: pooled residual distribution ----
    rep.say("")
    rep.say("=" * 70)
    rep.say("B. Pooled residual distribution")
    rep.md_only("\n## B. Pooled residual distribution\n")
    r = pooled_all["residual"].dropna()
    stats_rows = [
        ("n (paired obs)", f"{len(r):,}"),
        ("mean residual", f"{r.mean():+.4f} ({r.mean()*100:+.2f}pp)"),
        ("median residual", f"{r.median():+.4f} ({r.median()*100:+.2f}pp)"),
        ("std", f"{r.std():.4f}"),
        ("p5", f"{r.quantile(0.05):+.4f} ({r.quantile(0.05)*100:+.2f}pp)"),
        ("p25", f"{r.quantile(0.25):+.4f} ({r.quantile(0.25)*100:+.2f}pp)"),
        ("p75", f"{r.quantile(0.75):+.4f} ({r.quantile(0.75)*100:+.2f}pp)"),
        ("p95", f"{r.quantile(0.95):+.4f} ({r.quantile(0.95)*100:+.2f}pp)"),
        ("mean |residual|", f"{r.abs().mean():.4f} "
                             f"({r.abs().mean()*100:.2f}pp)"),
    ]
    for label, val in stats_rows:
        rep.say(f"  {label:<20s} {val}")
    rep.md_only("| Statistic | Value |\n|-----------|-------|")
    for label, val in stats_rows:
        rep.md_only(f"| {label} | {val} |")

    # ---- Section C: residual by ESPN WP bucket ----
    rep.say("")
    rep.say("=" * 70)
    rep.say("C. Residual stratified by ESPN WP bucket")
    rep.md_only("\n## C. Residual stratified by ESPN WP bucket\n")
    rep.md_only(
        "Pooled home + away observations; each snapshot contributes one "
        "row per side. Bucket on the side's own ESPN WP; residual = "
        "`kalshi_mid_that_side - espn_wp_that_side`.\n"
    )
    residual_bucket_table(pooled_all, rep, "All pooled (both games, both sides)")

    # ---- Section F: preliminary §1.1 assessment ----
    rep.say("")
    rep.say("=" * 70)
    rep.say("F. Preliminary §1.1 assessment")
    rep.md_only("\n## F. Preliminary §1.1 assessment\n")
    med = r.median()
    mean_abs = r.abs().mean()

    # Test for a compression-toward-0.5 pattern (Kalshi less extreme
    # than ESPN): correlate residual with (espn_wp - 0.5). If the
    # correlation is strongly negative, Kalshi is pulling prices
    # toward the midpoint relative to ESPN — a systematic structural
    # finding that the median-based check would miss because the
    # bucket-wise signs cancel.
    clean = pooled_all.dropna(subset=["espn_wp", "residual"])
    if len(clean) > 30:
        corr = float(
            np.corrcoef(
                clean["espn_wp"] - 0.5,
                clean["residual"],
            )[0, 1]
        )
    else:
        corr = float("nan")

    if mean_abs <= 0.02:
        verdict = (
            "Kalshi tracks ESPN tightly (mean |residual| ≤ 2pp). "
            "§1.1 supported at smoke-test scale. ESPN residuals should "
            "transfer as Kalshi residuals."
        )
    elif (not np.isnan(corr)) and corr < -0.50 and mean_abs > 0.03:
        verdict = (
            f"**Kalshi is systematically less extreme than ESPN** "
            f"(compression pattern — residual vs (ESPN WP − 0.5) "
            f"correlation = {corr:+.3f}; mean |residual| "
            f"{mean_abs*100:.2f}pp; median {med*100:+.2f}pp). "
            f"At low ESPN WP (favorites' comeback moments), Kalshi "
            f"prices the underdog *higher* than ESPN; at high ESPN WP, "
            f"Kalshi prices the favorite *lower*. Equivalent statement: "
            f"ESPN's WP swings harder with game state than Kalshi's. "
            f"Directly consistent with §1.4-style priors mattering, "
            f"but the direction is the opposite of what §1.4 predicts "
            f"about ESPN — here it's ESPN that looks *more* "
            f"game-state-reactive, not less. Material implication for "
            f"Strategy 2: the +3pp ESPN-vs-actual residual at low WP "
            f"does not transfer directly to Kalshi, because Kalshi's "
            f"prices are already +10pp above ESPN in that zone. The "
            f"relevant residual for Strategy 2 is "
            f"(actual_win_rate − Kalshi_mid), which the current "
            f"dataset can't estimate without more games that resolve "
            f"at the tails."
        )
    elif abs(med) > 0.05:
        sign = "above" if med > 0 else "below"
        verdict = (
            f"Kalshi systematically prices {sign} ESPN "
            f"(median residual {med*100:+.2f}pp). This is a material "
            "divergence — Strategy 2's entry rule needs to account for "
            "the Kalshi-vs-ESPN gap, not just the ESPN-vs-actual "
            "residual."
        )
    else:
        verdict = (
            f"Kalshi and ESPN diverge (mean |residual| "
            f"{mean_abs*100:.2f}pp, median {med*100:+.2f}pp, "
            f"residual-vs-(ESPN−0.5) correlation {corr:+.3f}) without "
            f"a pattern the current template recognizes. Inspect the "
            f"bucket table in Section C for structure before "
            f"interpreting."
        )
    rep.stdout_only("  " + verdict.replace("**", ""))
    rep.md_only(verdict)
    rep.md_only(
        "\n**n=2 games is far below any threshold for definitive "
        "conclusions.** This smoke test validates the pipeline; formal "
        "§1.1 analysis requires ≥5-10 games per the Phase 3B scoping.\n"
    )

    # Flush
    rep.write(OUTPUT_MD)
    rep.stdout_only("")
    rep.stdout_only("=" * 70)
    rep.stdout_only(f"Report written to {OUTPUT_MD}")
    rep.stdout_only("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
