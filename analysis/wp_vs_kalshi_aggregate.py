"""Cross-game aggregation of WP vs Kalshi paired analyses.

Reads all *_timeseries.csv and *_scoring_plays.csv files from
data/wp_kalshi_paired/ and produces a pooled statistical report.

Run:
    python -m analysis.wp_vs_kalshi_aggregate

    # Only aggregate specific games (by event ticker prefix)
    python -m analysis.wp_vs_kalshi_aggregate --filter "KXNBAGAME-26"

    # Include game metadata (requires matched_games.csv)
    python -m analysis.wp_vs_kalshi_aggregate \\
        --metadata data/wp_kalshi_paired/matched_games.csv
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy import stats as _scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "wp_vs_kalshi_aggregate.md"
)
SUMMARY_CSV_PATH = PAIRED_DIR / "aggregate_summary.csv"

VWAP_BUCKET_SEC = 30
Q_LEN_SEC = 720
OT_LEN_SEC = 300

WP_ZONES = [
    (0.00, 0.20, "0.00-0.20"),
    (0.20, 0.40, "0.20-0.40"),
    (0.40, 0.60, "0.40-0.60"),
    (0.60, 0.80, "0.60-0.80"),
    (0.80, 1.0001, "0.80-1.00"),
]
TR_BUCKETS = [
    (36 * 60, float("inf"), "> 36 min"),
    (24 * 60, 36 * 60, "24-36 min"),
    (12 * 60, 24 * 60, "12-24 min"),
    (6 * 60, 12 * 60, "6-12 min"),
    (3 * 60, 6 * 60, "3-6 min"),
    (1 * 60, 3 * 60, "1-3 min"),
    (0.0, 1 * 60, "0-1 min"),
]
S3_FAV_LO = 0.35
S3_FAV_HI = 0.65

TICKER_RE = re.compile(r"(KXNBAGAME-\d{2}[A-Z]{3}\d{2}[A-Z]{6})")


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


# ---- Loading ------------------------------------------------------------

def discover_games(filter_prefix: str | None) -> list[dict]:
    rows = []
    for p in sorted(PAIRED_DIR.glob("*_timeseries.csv")):
        m = TICKER_RE.match(p.stem)
        if not m:
            continue
        ticker = m.group(1)
        if filter_prefix and not ticker.startswith(filter_prefix):
            continue
        sp = PAIRED_DIR / f"{ticker}_scoring_plays.csv"
        rows.append({
            "ticker": ticker,
            "ts_path": p,
            "sp_path": sp if sp.exists() else None,
        })
    return rows


def load_timeseries(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        return df
    df["bucket_start_utc"] = pd.to_datetime(
        df["bucket_start_utc"], utc=True, errors="coerce",
    )
    for c in ("game_seconds_elapsed", "period", "fav_wp_espn",
              "fav_kalshi_vwap", "fav_kalshi_last", "delta",
              "kalshi_volume", "kalshi_trade_count"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_scoring_plays(path: Path) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty:
        return df
    for c in ("fav_wp_before", "fav_wp_after", "wp_delta",
              "kalshi_price_before", "kalshi_price_after",
              "kalshi_price_delta", "wp_vs_kalshi_reaction_diff",
              "score_value"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_metadata(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    df = pd.read_csv(path)
    out = {}
    for r in df.itertuples():
        out[str(r.kalshi_event_ticker)] = {
            "espn_game_id": str(r.espn_game_id),
            "game_date": str(r.game_date),
            "away_team": str(r.away_team),
            "home_team": str(r.home_team),
            "home_spread": float(r.home_spread) if pd.notna(r.home_spread) else None,
            "abs_spread": float(r.abs_spread) if pd.notna(r.abs_spread) else None,
        }
    return out


# ---- Per-game summary ---------------------------------------------------

def total_game_length_sec(max_period: float) -> int:
    mp = int(max_period) if not pd.isna(max_period) else 4
    if mp <= 4:
        return 4 * Q_LEN_SEC
    return 4 * Q_LEN_SEC + (mp - 4) * OT_LEN_SEC


def per_game_stats(
    ticker: str, ts: pd.DataFrame, meta: dict | None,
) -> dict:
    out: dict = {
        "ticker": ticker,
        "n_buckets": int(len(ts)),
        "n_ingame": int(ts["game_seconds_elapsed"].notna().sum()),
    }
    if meta:
        out.update({
            "game_date": meta.get("game_date"),
            "away_team": meta.get("away_team"),
            "home_team": meta.get("home_team"),
            "home_spread": meta.get("home_spread"),
            "abs_spread": meta.get("abs_spread"),
        })
    if ts.empty:
        return out
    ingame = ts.dropna(subset=["delta", "game_seconds_elapsed"])
    if ingame.empty:
        return out
    max_period = ingame["period"].dropna().max() if "period" in ingame.columns else 4
    total_len = total_game_length_sec(max_period if not pd.isna(max_period) else 4)
    ingame = ingame.copy()
    ingame["time_remaining"] = total_len - ingame["game_seconds_elapsed"]
    ingame["abs_delta"] = ingame["delta"].abs()

    out["mean_delta"] = float(ingame["delta"].mean())
    out["mean_abs_delta"] = float(ingame["abs_delta"].mean())
    final2 = ingame[ingame["time_remaining"] <= 120]
    out["final_2m_abs_delta"] = (
        float(final2["abs_delta"].mean()) if not final2.empty else None
    )

    # Convergence regression
    if len(ingame) >= 2:
        x = ingame["game_seconds_elapsed"].values
        y = ingame["abs_delta"].values
        if _HAS_SCIPY:
            res = _scipy_stats.linregress(x, y)
            out["r_squared"] = float(res.rvalue ** 2)
            out["slope"] = float(res.slope)
            out["p_value"] = float(res.pvalue)
        else:
            slope, intercept = np.polyfit(x, y, 1)
            yhat = slope * x + intercept
            ss_res = np.sum((y - yhat) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2) or 1.0
            out["r_squared"] = float(1.0 - ss_res / ss_tot)
            out["slope"] = float(slope)
            out["p_value"] = None

    # Strategy 3 zone
    k = ingame.dropna(subset=["fav_kalshi_vwap"])
    if not k.empty:
        zone = k[
            (k["fav_kalshi_vwap"] >= S3_FAV_LO)
            & (k["fav_kalshi_vwap"] <= S3_FAV_HI)
        ]
        out["zone_buckets"] = int(len(zone))
        out["zone_pct"] = 100 * len(zone) / len(k)
        out["zone_seconds"] = int(len(zone) * VWAP_BUCKET_SEC)
    return out


# ---- Aggregation sections ----------------------------------------------

def _mean_ci(vals: np.ndarray) -> tuple[float, float, int]:
    """Return (mean, half-width of 95% CI, n). Falls back to std/sqrt(n)
    when scipy is unavailable."""
    clean = vals[~np.isnan(vals)]
    n = len(clean)
    if n == 0:
        return float("nan"), float("nan"), 0
    if n < 2:
        return float(clean.mean()), float("nan"), n
    m = float(clean.mean())
    sd = float(clean.std(ddof=1))
    if _HAS_SCIPY:
        t = _scipy_stats.t.ppf(0.975, df=n - 1)
    else:
        t = 1.96
    return m, float(t * sd / np.sqrt(n)), n


def section_a_sample(md: list[str], per_game: list[dict],
                     pooled_ts: pd.DataFrame,
                     pooled_sp: pd.DataFrame) -> None:
    md.append("## §A — Sample summary\n")
    dates = sorted([g["game_date"] for g in per_game if g.get("game_date")])
    md.append(f"- Games analyzed: **{len(per_game)}**")
    if dates:
        md.append(f"- Date range: {dates[0]} to {dates[-1]}")
    spreads = [g.get("abs_spread") for g in per_game if g.get("abs_spread") is not None]
    if spreads:
        s = np.array(spreads)
        md.append(
            f"- |Spread| distribution: mean {s.mean():.2f}, "
            f"median {np.median(s):.2f}, min {s.min():.2f}, "
            f"max {s.max():.2f}"
        )
    n_buckets = int(pooled_ts["game_seconds_elapsed"].notna().sum()) \
        if not pooled_ts.empty else 0
    md.append(
        f"- Total 30s bins (in-game): {n_buckets:,} across {len(per_game)} games"
    )
    md.append(
        f"- Total scoring plays: {len(pooled_sp):,} "
        f"across {len(per_game)} games"
    )
    md.append("")


def section_b_delta_by_zone(md: list[str], pooled_ts: pd.DataFrame) -> None:
    md.append("## §B — Delta by WP zone (pooled)\n")
    md.append("| WP zone | Mean Δ ± 95% CI | Median Δ | N obs | Δ > 0 % |")
    md.append("|---|---:|---:|---:|---:|")
    sub = pooled_ts.dropna(
        subset=["delta", "fav_wp_espn", "game_seconds_elapsed"]
    )
    if sub.empty:
        md.append("| — | — | — | 0 | — |")
        md.append("")
        return
    for lo, hi, label in WP_ZONES:
        z = sub[(sub["fav_wp_espn"] >= lo) & (sub["fav_wp_espn"] < hi)]
        if z.empty:
            md.append(f"| {label} | — | — | 0 | — |")
            continue
        m, ci, n = _mean_ci(z["delta"].values)
        med = float(z["delta"].median())
        pct_pos = 100 * float((z["delta"] > 0).mean())
        ci_str = f"±{ci*100:.2f}" if not np.isnan(ci) else "±—"
        md.append(
            f"| {label} | {m*100:+.2f}pp {ci_str}pp | "
            f"{med*100:+.2f}pp | {n:,} | {pct_pos:.0f}% |"
        )
    md.append("")


def section_c_convergence(md: list[str], pooled_ts: pd.DataFrame,
                          per_game: list[dict]) -> None:
    md.append("## §C — Convergence regression\n")
    sub = pooled_ts.dropna(
        subset=["delta", "game_seconds_elapsed"]
    ).copy()
    sub["abs_delta"] = sub["delta"].abs()

    def _reg(x, y) -> tuple[float, float, float, int]:
        if len(x) < 2:
            return float("nan"), float("nan"), float("nan"), len(x)
        if _HAS_SCIPY:
            r = _scipy_stats.linregress(x, y)
            return r.slope, r.rvalue ** 2, r.pvalue, len(x)
        slope, intercept = np.polyfit(x, y, 1)
        yhat = slope * x + intercept
        ss_res = np.sum((y - yhat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2) or 1.0
        return float(slope), float(1 - ss_res / ss_tot), float("nan"), len(x)

    # Pooled + per-bucket
    md.append("| Subset | Slope | R² | p | n |")
    md.append("|---|---:|---:|---:|---:|")
    slope, r2, p, n = _reg(
        sub["game_seconds_elapsed"].values, sub["abs_delta"].values,
    )
    p_s = f"{p:.3g}" if not np.isnan(p) else "—"
    md.append(f"| Pooled | {slope:.6f}/s | {r2:.3f} | {p_s} | {n:,} |")

    # By abs_spread bucket: need metadata per bucket_start via ticker.
    # Attach per-game abs_spread to pooled_ts via its `ticker` column.
    if "ticker" in sub.columns:
        spreads = {g["ticker"]: g.get("abs_spread") for g in per_game}
        sub["abs_spread"] = sub["ticker"].map(spreads)
        for label, pred in (
            ("|spread| ≤ 3", lambda s: s <= 3),
            ("|spread| 3-6", lambda s: (s > 3) & (s <= 6)),
            ("|spread| > 6", lambda s: s > 6),
        ):
            bucket = sub.dropna(subset=["abs_spread"])
            bucket = bucket[pred(bucket["abs_spread"])]
            if bucket.empty:
                md.append(f"| {label} | — | — | — | 0 |")
                continue
            slope, r2, p, n = _reg(
                bucket["game_seconds_elapsed"].values,
                bucket["abs_delta"].values,
            )
            p_s = f"{p:.3g}" if not np.isnan(p) else "—"
            md.append(
                f"| {label} | {slope:.6f}/s | {r2:.3f} | {p_s} | {n:,} |"
            )
    md.append("")

    # Mean |Δ| by time-remaining bucket
    md.append("### Mean |Δ| by time remaining (pooled)\n")
    md.append("| Time remaining | Mean |Δ| | Median |Δ| | N |")
    md.append("|---|---:|---:|---:|")
    max_per_game = sub.groupby("ticker")["period"].max() if "ticker" in sub.columns else None
    if max_per_game is not None:
        tot_len_map = max_per_game.apply(total_game_length_sec).to_dict()
        sub = sub.copy()
        sub["time_remaining"] = sub.apply(
            lambda r: tot_len_map.get(r["ticker"], 4 * Q_LEN_SEC)
            - r["game_seconds_elapsed"],
            axis=1,
        )
    else:
        sub["time_remaining"] = (4 * Q_LEN_SEC) - sub["game_seconds_elapsed"]
    for lo, hi, label in TR_BUCKETS:
        z = sub[(sub["time_remaining"] > lo) & (sub["time_remaining"] <= hi)]
        if z.empty:
            md.append(f"| {label} | — | — | 0 |")
            continue
        md.append(
            f"| {label} | {z['abs_delta'].mean()*100:.2f}pp | "
            f"{z['abs_delta'].median()*100:.2f}pp | {len(z):,} |"
        )
    md.append("")


def section_d_scoring(md: list[str], pooled_sp: pd.DataFrame) -> None:
    md.append("## §D — Scoring play reaction ratios (pooled)\n")
    covered = pooled_sp.dropna(subset=["wp_delta", "kalshi_price_delta"])
    if covered.empty:
        md.append("_No scoring-play coverage._\n")
        return
    md.append(f"Coverage: {len(covered):,} / {len(pooled_sp):,} plays.\n")
    md.append("### By score value")
    md.append("")
    md.append(
        "| Score value | n | Mean wp_delta | Mean Kalshi Δ | Ratio |"
    )
    md.append("|---|---:|---:|---:|---:|")
    for sv in sorted(covered["score_value"].dropna().unique()):
        z = covered[covered["score_value"] == sv]
        wp_m = z["wp_delta"].mean()
        k_m = z["kalshi_price_delta"].mean()
        ratio = f"{wp_m / k_m:.2f}×" if abs(k_m) > 1e-6 else "—"
        md.append(
            f"| {int(sv)}-pt | {len(z):,} | {wp_m*100:+.2f}pp | "
            f"{k_m*100:+.2f}pp | {ratio} |"
        )
    md.append("")
    md.append("### By WP zone at time of play")
    md.append("")
    md.append(
        "| WP zone | n | Mean wp_delta | Mean Kalshi Δ | Ratio |"
    )
    md.append("|---|---:|---:|---:|---:|")
    for lo, hi, label in WP_ZONES:
        z = covered[
            (covered["fav_wp_before"] >= lo)
            & (covered["fav_wp_before"] < hi)
        ]
        if z.empty:
            md.append(f"| {label} | 0 | — | — | — |")
            continue
        wp_m = z["wp_delta"].mean()
        k_m = z["kalshi_price_delta"].mean()
        ratio = f"{wp_m / k_m:.2f}×" if abs(k_m) > 1e-6 else "—"
        md.append(
            f"| {label} | {len(z):,} | {wp_m*100:+.2f}pp | "
            f"{k_m*100:+.2f}pp | {ratio} |"
        )
    md.append("")


def section_e_s3_zone(md: list[str], per_game: list[dict]) -> None:
    md.append("## §E — Strategy 3 zone statistics\n")
    rows = []
    for g in per_game:
        if g.get("zone_buckets") is None:
            continue
        rows.append(g)
    if not rows:
        md.append("_No zone data._\n")
        return
    comp = [r for r in rows
            if r.get("abs_spread") is not None and r["abs_spread"] <= 6]
    if comp:
        with_zone = [r for r in comp if (r.get("zone_buckets") or 0) > 0]
        md.append(
            f"- Competitive games (|spread| ≤ 6): **{len(comp)}**; "
            f"{len(with_zone)}/{len(comp)} "
            f"({100*len(with_zone)/len(comp):.0f}%) entered S3 zone."
        )
        if with_zone:
            mean_sec = np.mean([r["zone_seconds"] for r in with_zone])
            mean_pct = np.mean([r["zone_pct"] for r in with_zone])
            md.append(
                f"- Among those: mean zone time {mean_sec:,.0f}s "
                f"({mean_pct:.1f}% of in-game bins)."
            )
    # Zone time vs |spread| regression
    xs = np.array([r["abs_spread"] for r in rows
                   if r.get("abs_spread") is not None])
    ys = np.array([r["zone_seconds"] for r in rows
                   if r.get("abs_spread") is not None])
    if len(xs) >= 2:
        if _HAS_SCIPY:
            res = _scipy_stats.linregress(xs, ys)
            md.append(
                f"- Zone time ~ |spread| regression: slope "
                f"{res.slope:.1f} s/spread-pt, R² = {res.rvalue**2:.3f}, "
                f"p = {res.pvalue:.3g}, n = {len(xs)}."
            )
        else:
            slope, intercept = np.polyfit(xs, ys, 1)
            md.append(
                f"- Zone time ~ |spread| regression "
                f"(numpy polyfit, no p-value): slope "
                f"{slope:.1f} s/spread-pt, n = {len(xs)}."
            )
    md.append("")


def section_f_timeouts(md: list[str], pooled_ts: pd.DataFrame) -> None:
    md.append("## §F — Delta stability at timeouts (pooled)\n")
    sub = pooled_ts.dropna(subset=["delta", "game_seconds_elapsed"])
    if sub.empty or "is_timeout_window" not in sub.columns:
        md.append("_No data._\n")
        return
    to = sub[sub["is_timeout_window"] == True]   # noqa: E712
    other = sub[sub["is_timeout_window"] != True]  # noqa: E712
    to_abs = to["delta"].abs().dropna()
    other_abs = other["delta"].abs().dropna()
    md.append(f"- Timeout windows: n = {len(to_abs):,}")
    md.append(f"- Non-timeout windows: n = {len(other_abs):,}")
    if to_abs.empty:
        md.append("")
        return
    md.append(
        f"- Mean |Δ| in timeout windows: {to_abs.mean()*100:.2f}pp"
    )
    md.append(
        f"- Mean |Δ| outside timeout windows: {other_abs.mean()*100:.2f}pp"
    )
    if _HAS_SCIPY and len(to_abs) > 1 and len(other_abs) > 1:
        res = _scipy_stats.mannwhitneyu(
            to_abs, other_abs, alternative="two-sided",
        )
        md.append(
            f"- Mann-Whitney U test: U = {res.statistic:.0f}, "
            f"p = {res.pvalue:.3g}."
        )
    else:
        md.append(
            "- Significance test skipped (scipy unavailable or "
            "sample too small)."
        )
    md.append("")


def section_g_per_game(md: list[str], per_game: list[dict]) -> None:
    md.append("## §G — Per-game summary table\n")
    md.append(
        "| Ticker | Date | Spread | R² | Mean Δ | "
        "Final 2m |Δ| | Zone time % | n in-game |"
    )
    md.append("|---|---|---:|---:|---:|---:|---:|---:|")
    rows = sorted(per_game, key=lambda g: (g.get("game_date") or "", g["ticker"]))
    for g in rows:
        sp = g.get("home_spread")
        sp_s = f"{sp:+.1f}" if sp is not None else "—"
        r2 = g.get("r_squared")
        r2_s = f"{r2:.3f}" if r2 is not None else "—"
        md_ = g.get("mean_delta")
        md_s = f"{md_*100:+.2f}pp" if md_ is not None else "—"
        f2 = g.get("final_2m_abs_delta")
        f2_s = f"{f2*100:.2f}pp" if f2 is not None else "—"
        zp = g.get("zone_pct")
        zp_s = f"{zp:.1f}%" if zp is not None else "—"
        md.append(
            f"| {g['ticker']} | {g.get('game_date') or '—'} | "
            f"{sp_s} | {r2_s} | {md_s} | {f2_s} | {zp_s} | "
            f"{g.get('n_ingame', 0):,} |"
        )
    md.append("")


# ---- Main ---------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", type=str, default=None,
                        help="Event ticker prefix filter (e.g., 'KXNBAGAME-26').")
    parser.add_argument("--metadata", type=str, default=None,
                        help="Path to matched_games.csv (joins abs_spread + teams).")
    args = parser.parse_args()

    games = discover_games(args.filter)
    if not games:
        raise SystemExit(
            f"No *_timeseries.csv files in {PAIRED_DIR} "
            f"(filter={args.filter!r})."
        )
    log(f"Discovered {len(games)} games")

    meta_map = load_metadata(Path(args.metadata)) if args.metadata else {}
    log(f"Metadata loaded for {len(meta_map)} games")

    per_game: list[dict] = []
    ts_frames: list[pd.DataFrame] = []
    sp_frames: list[pd.DataFrame] = []
    for g in games:
        ts = load_timeseries(g["ts_path"])
        if not ts.empty:
            ts["ticker"] = g["ticker"]
            ts_frames.append(ts)
        sp = load_scoring_plays(g["sp_path"]) if g["sp_path"] else pd.DataFrame()
        if not sp.empty:
            sp["ticker"] = g["ticker"]
            sp_frames.append(sp)
        per_game.append(per_game_stats(
            g["ticker"], ts, meta_map.get(g["ticker"]),
        ))
    pooled_ts = (
        pd.concat(ts_frames, ignore_index=True) if ts_frames else pd.DataFrame()
    )
    pooled_sp = (
        pd.concat(sp_frames, ignore_index=True) if sp_frames else pd.DataFrame()
    )

    md: list[str] = []
    md.append("# WP vs Kalshi Paired Analysis — Cross-Game Aggregation\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    if not _HAS_SCIPY:
        md.append(
            "**Note:** scipy not available; significance tests skipped "
            "and regressions use numpy polyfit (no p-values).\n"
        )
    section_a_sample(md, per_game, pooled_ts, pooled_sp)
    section_b_delta_by_zone(md, pooled_ts)
    section_c_convergence(md, pooled_ts, per_game)
    section_d_scoring(md, pooled_sp)
    section_e_s3_zone(md, per_game)
    section_f_timeouts(md, pooled_ts)
    section_g_per_game(md, per_game)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(md) + "\n")
    log(f"Report → {REPORT_PATH}")

    # Summary CSV
    summary_cols = [
        "ticker", "game_date", "away_team", "home_team",
        "home_spread", "abs_spread", "n_ingame", "r_squared",
        "slope", "p_value", "mean_delta", "mean_abs_delta",
        "final_2m_abs_delta", "zone_buckets", "zone_seconds",
        "zone_pct",
    ]
    summary_df = pd.DataFrame(per_game)
    for c in summary_cols:
        if c not in summary_df.columns:
            summary_df[c] = None
    summary_df = summary_df[summary_cols].sort_values(
        ["game_date", "ticker"]
    )
    summary_df.to_csv(SUMMARY_CSV_PATH, index=False)
    log(f"Summary CSV → {SUMMARY_CSV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
