"""Investigate whether the |spread| 5.5-6.0 bucket's S4A outperformance
(+$6.17 mean P&L, 64.9% hit, n=37 in the Part 8 Path B analysis) is
structural or small-sample noise.

Reuses the exact `simulate_s4a` pipeline from
`analysis.strategy4_dip_recovery`, so the parity check against the
Path B 7-bucket rollup must match trade-for-trade. Then runs
entry-level detail, leave-one-out sensitivity, 10k-sample bootstrap,
adjacent-bucket comparison, and game-level concentration on the
5.5-6.0 subset.

Run:
    python -m analysis.strategy4_bucket_investigation
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    OT_LEN_SEC,
    Q_LEN_SEC,
    S4AConfig,
    S4ATrade,
    _precompute_trailing_max,
    load_kalshi_games_all_spreads,
    simulate_s4a,
    summarize_s4a,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MATCHED_CSV = REPO_ROOT / "data" / "wp_kalshi_paired" / "matched_games.csv"
MASTER_CSV = REPO_ROOT / "data" / "nba_master_2025_26.csv"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "strategy4_bucket_5_5_investigation.md"
)

# S4A best config from STRATEGY4_SPEC.md §2 / §3 / §4.
CFG = S4AConfig(
    lookback_sec=180, dip_depth=0.08,
    entry_lo=0.50, entry_hi=0.75,
    exit_target=0.90, stop_loss=0.40,
)

BUCKETS: list[tuple[str, float, float]] = [
    ("1.0-2.0", 1.0, 2.0),
    ("2.5-3.5", 2.5, 3.5),
    ("4.0-5.0", 4.0, 5.0),
    ("5.5-6.0", 5.5, 6.0),
    ("6.5-8.0", 6.5, 8.0),
    ("8.5-10.0", 8.5, 10.0),
    ("10.5+", 10.5, float("inf")),
]

TARGET_BUCKET = "5.5-6.0"
ADJACENT_LOWER = "4.0-5.0"
ADJACENT_UPPER = "6.5-8.0"

# Expected numbers from Part 8 Path B (for parity check).
EXPECTED_TARGET_ENTRIES = 37
EXPECTED_TARGET_HIT_PCT = 64.9
EXPECTED_TARGET_MEAN_PNL = 6.17

BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 42


def bucket_for(abs_spread: float) -> str | None:
    for lab, lo, hi in BUCKETS:
        if lo <= abs_spread <= hi:
            return lab
    return None


def entry_period_from_gse(gse: float | None) -> str | None:
    """Derive Q1/Q2/Q3/Q4/OT label from game_seconds_elapsed."""
    if gse is None or pd.isna(gse):
        return None
    gse = float(gse)
    for i in range(1, 5):
        if gse < i * Q_LEN_SEC:
            return f"Q{i}"
    return "OT"


def load_game_labels() -> dict[str, str]:
    """Build espn_game_id -> 'AWY @ HOM' label from nba_master."""
    master = pd.read_csv(MASTER_CSV)
    out: dict[str, str] = {}
    for r in master.itertuples():
        try:
            gid = str(int(r.game_id))
        except (ValueError, TypeError):
            continue
        away = getattr(r, "away_team_abbrev", None)
        home = getattr(r, "home_team_abbrev", None)
        if away and home:
            out[gid] = f"{away} @ {home}"
    return out


def enrich_trade(
    t: S4ATrade, game: dict, precomp_max: np.ndarray,
    labels: dict[str, str],
) -> dict:
    """Turn an S4ATrade into a dict enriched with per-entry context."""
    ts_df = game["ts"]
    gse_series = ts_df["game_seconds_elapsed"]
    entry_gse = (
        float(gse_series.iloc[t.entry_idx])
        if 0 <= t.entry_idx < len(gse_series)
        and not pd.isna(gse_series.iloc[t.entry_idx])
        else None
    )
    tmax = float(precomp_max[t.entry_idx])
    return {
        "ticker": t.ticker,
        "espn_game_id": game.get("espn_game_id"),
        "label": labels.get(str(game.get("espn_game_id", "")), "?"),
        "abs_spread": t.abs_spread,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "exit_type": t.exit_type,
        "pnl": t.net_pnl,
        "entry_gse": entry_gse,
        "entry_period": (
            f"Q{t.entry_period}" if t.entry_period
            else entry_period_from_gse(entry_gse) or "?"
        ),
        "hold_sec": t.hold_bins * BUCKET_SEC,
        "trailing_max": tmax,
        "dip_depth": tmax - t.entry_price,
        "is_reentry": t.is_reentry,
    }


def simulate_and_bucket(
    games: list[dict],
) -> tuple[
    dict[str, list[dict]],
    dict[str, dict],
    dict[tuple[str, int], np.ndarray],
]:
    """Run simulate_s4a on all games; bucket enriched trades.

    Returns (trades_by_bucket, bucket_summary, precomp_max).
    """
    lookback_bins = max(1, int(CFG.lookback_sec / BUCKET_SEC))
    precomp_max: dict[tuple[str, int], np.ndarray] = {}
    for g in games:
        fav = g["ts"]["fav_kalshi_vwap"].values
        precomp_max[(g["ticker"], lookback_bins)] = (
            _precompute_trailing_max(fav, lookback_bins)
        )

    labels = load_game_labels()
    games_by_ticker = {g["ticker"]: g for g in games}

    trades_by_bucket: dict[str, list[dict]] = {
        lab: [] for lab, _, _ in BUCKETS
    }
    bucket_games: dict[str, list[dict]] = {lab: [] for lab, _, _ in BUCKETS}
    for g in games:
        lab = bucket_for(g["abs_spread"])
        if lab is not None:
            bucket_games[lab].append(g)

    bucket_summary: dict[str, dict] = {}
    for lab, _, _ in BUCKETS:
        gs = bucket_games[lab]
        if not gs:
            bucket_summary[lab] = {
                "n_games": 0, "entries": 0, "hit_pct": 0.0,
                "mean_pnl": 0.0, "stop_pct": 0.0, "held_pct": 0.0,
            }
            continue
        trades = simulate_s4a(gs, CFG, precomp_max)
        s = summarize_s4a(trades, len(gs))
        bucket_summary[lab] = {
            "n_games": len(gs),
            "entries": s["entries"],
            "hit_pct": s["hit_pct"],
            "stop_pct": s["stop_pct"],
            "held_pct": s["held_pct"],
            "mean_pnl": s["mean_pnl"],
        }
        for t in trades:
            g = games_by_ticker[t.ticker]
            tmax_arr = precomp_max[(t.ticker, lookback_bins)]
            trades_by_bucket[lab].append(enrich_trade(t, g, tmax_arr, labels))

    return trades_by_bucket, bucket_summary, precomp_max


def parity_check(
    bucket_summary: dict[str, dict], trades_by_bucket: dict[str, list[dict]],
) -> tuple[bool, list[str]]:
    """Verify the 5.5-6.0 bucket matches the Path B headline numbers."""
    notes: list[str] = []
    b = bucket_summary[TARGET_BUCKET]
    entries_ok = b["entries"] == EXPECTED_TARGET_ENTRIES
    hit_ok = abs(b["hit_pct"] - EXPECTED_TARGET_HIT_PCT) <= 0.2
    mean_ok = abs(b["mean_pnl"] - EXPECTED_TARGET_MEAN_PNL) <= 0.02
    notes.append(
        f"5.5-6.0: entries={b['entries']} (expected {EXPECTED_TARGET_ENTRIES}) "
        f"{'OK' if entries_ok else 'FAIL'}"
    )
    notes.append(
        f"5.5-6.0: hit={b['hit_pct']:.1f}% (expected "
        f"{EXPECTED_TARGET_HIT_PCT:.1f}%) {'OK' if hit_ok else 'FAIL'}"
    )
    notes.append(
        f"5.5-6.0: mean=${b['mean_pnl']:+.2f} (expected "
        f"${EXPECTED_TARGET_MEAN_PNL:+.2f}) {'OK' if mean_ok else 'FAIL'}"
    )
    return (entries_ok and hit_ok and mean_ok), notes


def leave_one_out(pnls: list[float]) -> dict:
    arr = np.array(pnls)
    n = len(arr)
    if n < 2:
        return {"range_mean": (0.0, 0.0), "max_swing_delta": 0.0,
                "max_swing_idx": -1, "n_to_go_negative": None}
    total = arr.sum()
    loo_means = (total - arr) / (n - 1)
    full_mean = arr.mean()
    deltas = full_mean - loo_means
    max_idx = int(np.argmax(np.abs(deltas)))

    # How many entries (starting from the highest-P&L) must be removed
    # before the remaining mean goes negative?
    order = np.argsort(arr)[::-1]  # highest to lowest
    sorted_arr = arr[order]
    n_to_neg: int | None = None
    running = total
    remaining = n
    for k in range(n):
        running -= sorted_arr[k]
        remaining -= 1
        if remaining == 0:
            break
        if running / remaining < 0:
            n_to_neg = k + 1
            break
    return {
        "range_mean": (float(loo_means.min()), float(loo_means.max())),
        "max_swing_delta": float(deltas[max_idx]),
        "max_swing_idx": max_idx,
        "n_to_go_negative": n_to_neg,
    }


def bootstrap(pnls: list[float], n_iter: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    arr = np.array(pnls)
    n = len(arr)
    if n == 0:
        return {
            "mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0,
            "p_gt_zero": 0.0, "p_gt_adjacent": 0.0,
        }
    idx = rng.integers(0, n, size=(n_iter, n))
    resample_means = arr[idx].mean(axis=1)
    return {
        "mean": float(resample_means.mean()),
        "ci_lo": float(np.quantile(resample_means, 0.025)),
        "ci_hi": float(np.quantile(resample_means, 0.975)),
        "p_gt_zero": float((resample_means > 0).mean()),
    }


def p_gt_threshold(pnls: list[float], n_iter: int, seed: int,
                   threshold: float) -> float:
    rng = np.random.default_rng(seed)
    arr = np.array(pnls)
    n = len(arr)
    if n == 0:
        return 0.0
    idx = rng.integers(0, n, size=(n_iter, n))
    resample_means = arr[idx].mean(axis=1)
    return float((resample_means > threshold).mean())


def profile_bucket(trades: list[dict]) -> dict:
    if not trades:
        return {
            "n": 0,
            "entry_price": (None, None, None),
            "hold_sec": (None, None, None),
            "dip_depth": (None, None, None),
            "period_pct": {},
            "reentry_rate": 0.0,
            "hit_pct": 0.0,
            "stop_pct": 0.0,
            "held_pct": 0.0,
        }
    ep = np.array([t["entry_price"] for t in trades])
    hs = np.array([t["hold_sec"] for t in trades])
    dd = np.array([t["dip_depth"] for t in trades])
    periods = Counter(t["entry_period"] for t in trades)
    n = len(trades)
    period_pct = {p: 100.0 * c / n for p, c in periods.items()}
    exits = Counter(t["exit_type"] for t in trades)
    return {
        "n": n,
        "entry_price": (
            float(np.quantile(ep, 0.25)),
            float(np.median(ep)),
            float(np.quantile(ep, 0.75)),
        ),
        "hold_sec": (
            float(np.quantile(hs, 0.25)),
            float(np.median(hs)),
            float(np.quantile(hs, 0.75)),
        ),
        "dip_depth": (
            float(np.quantile(dd, 0.25)),
            float(np.median(dd)),
            float(np.quantile(dd, 0.75)),
        ),
        "period_pct": period_pct,
        "reentry_rate": 100.0 * sum(
            1 for t in trades if t["is_reentry"]
        ) / n,
        "hit_pct": 100.0 * exits.get("target", 0) / n,
        "stop_pct": 100.0 * exits.get("stop", 0) / n,
        "held_pct": 100.0 * sum(
            v for k, v in exits.items()
            if k not in ("target", "stop")
        ) / n,
    }


def game_concentration(trades: list[dict]) -> dict:
    per_game = Counter(t["espn_game_id"] for t in trades)
    games_with_1 = sum(1 for c in per_game.values() if c == 1)
    games_with_2 = sum(1 for c in per_game.values() if c == 2)
    # "Favorite won": when at least one entry in the game exited to
    # target (market reached $0.90), treat as proxy for the favorite
    # effectively winning — S4A does not hold to resolution, so we use
    # the exit_type distribution as the signal.
    wins = 0
    for gid, _ in per_game.items():
        game_trades = [t for t in trades if t["espn_game_id"] == gid]
        if any(t["exit_type"] == "target" for t in game_trades):
            wins += 1
    return {
        "distinct_games": len(per_game),
        "games_1_entry": games_with_1,
        "games_2_entries": games_with_2,
        "games_with_target_hit": wins,
        "games_with_target_hit_pct": (
            100.0 * wins / len(per_game) if per_game else 0.0
        ),
    }


# ---- Report rendering --------------------------------------------------

def render_report(
    games_total: int,
    bucket_summary: dict[str, dict],
    parity_ok: bool,
    parity_notes: list[str],
    target_trades: list[dict],
    adjacent_lower_trades: list[dict],
    adjacent_upper_trades: list[dict],
    loo: dict,
    boot: dict,
    p_gt_257: float,
    concentration: dict,
    verdict: str,
) -> str:
    md: list[str] = []
    md.append("# Strategy 4 — Bucket 5.5–6.0 Investigation\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Investigates whether the |spread| 5.5–6.0 bucket's "
        f"outperformance (+${EXPECTED_TARGET_MEAN_PNL:.2f} mean P&L, "
        f"{EXPECTED_TARGET_HIT_PCT:.1f}% hit, n="
        f"{EXPECTED_TARGET_ENTRIES}) reflects a structural edge or "
        "small-sample noise. Uses the "
        f"{games_total}-game Kalshi-confirmed dataset from Part 8 "
        "Path B.\n"
    )

    # Part 1 — parity
    md.append("\n## Part 1 — Parity check\n")
    md.append(
        "`PARITY CHECK: "
        f"{'PASS' if parity_ok else 'FAIL'}`\n\n"
    )
    md.append("Sub-checks:\n")
    for note in parity_notes:
        md.append(f"- {note}\n")
    md.append(
        "\nFull 7-bucket rollup (parity against Path B Table 2):\n\n"
        "| |spread| bucket | Games | Entries | Hit % | Stop % | "
        "Mean P&L |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    for lab, _, _ in BUCKETS:
        s = bucket_summary[lab]
        if s["entries"] == 0:
            md.append(f"| {lab} | {s['n_games']} | 0 | — | — | — |\n")
            continue
        md.append(
            f"| {lab} | {s['n_games']} | {s['entries']} | "
            f"{s['hit_pct']:.1f}% | {s['stop_pct']:.1f}% | "
            f"${s['mean_pnl']:+.2f} |\n"
        )

    # Part 2 — entry-level detail
    md.append("\n## Part 2 — Entry-level detail for 5.5–6.0 bucket\n")
    md.append(
        f"All {len(target_trades)} entries, sorted by P&L descending:\n\n"
        "| # | Game | \\|Spread\\| | Entry | Exit | Outcome | P&L | "
        "Entry period | Entry gse (s) | Hold (s) | Trail max | "
        "Dip depth | Re-entry |\n"
        "|---:|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---|\n"
    )
    sorted_tgt = sorted(target_trades, key=lambda t: -t["pnl"])
    for i, t in enumerate(sorted_tgt, 1):
        md.append(
            f"| {i} | {t['label']} | {t['abs_spread']:.1f} | "
            f"${t['entry_price']:.3f} | ${t['exit_price']:.3f} | "
            f"{t['exit_type']} | ${t['pnl']:+.2f} | "
            f"{t['entry_period']} | "
            f"{int(t['entry_gse']) if t['entry_gse'] is not None else '—'} | "
            f"{int(t['hold_sec'])} | ${t['trailing_max']:.3f} | "
            f"${t['dip_depth']:.3f} | "
            f"{'yes' if t['is_reentry'] else 'no'} |\n"
        )

    # Part 3 — leave-one-out
    md.append("\n## Part 3 — Outlier sensitivity (leave-one-out)\n")
    loo_lo, loo_hi = loo["range_mean"]
    md.append(
        f"- Leave-one-out mean range: **${loo_lo:+.2f} — "
        f"${loo_hi:+.2f}**\n"
        f"- Full-bucket mean: ${np.mean([t['pnl'] for t in target_trades]):+.2f}\n"
        f"- Max single-entry swing: "
        f"±${abs(loo['max_swing_delta']):.2f} (removing entry at "
        f"index {loo['max_swing_idx']} in the P&L-sorted list)\n"
    )
    if loo["n_to_go_negative"] is None:
        md.append(
            "- Entries to remove (starting from highest P&L) before "
            "bucket mean goes negative: **never goes negative** — "
            "removing all positive-P&L entries still leaves a "
            "non-negative remainder, or the bucket had no positive "
            "entries to remove.\n"
        )
    else:
        md.append(
            f"- Entries to remove (starting from highest P&L) before "
            f"bucket mean goes negative: "
            f"**{loo['n_to_go_negative']} of {len(target_trades)}**.\n"
        )

    # Part 4 — bootstrap
    md.append("\n## Part 4 — Bootstrap 95% CI (10,000 resamples)\n")
    md.append(
        f"- Bootstrap mean: ${boot['mean']:+.2f}\n"
        f"- 95% CI: (${boot['ci_lo']:+.2f}, ${boot['ci_hi']:+.2f})\n"
        f"- P(true mean > $0): {100 * boot['p_gt_zero']:.1f}%\n"
        f"- P(true mean > $2.57, adjacent 2.5–3.5 bucket null): "
        f"{100 * p_gt_257:.1f}%\n"
    )

    # Part 5 — adjacent-bucket comparison
    md.append("\n## Part 5 — Comparison to adjacent buckets\n")
    prof_lo = profile_bucket(adjacent_lower_trades)
    prof_mid = profile_bucket(target_trades)
    prof_hi = profile_bucket(adjacent_upper_trades)
    md.append(
        "| Metric | 4.0–5.0 | **5.5–6.0** | 6.5–8.0 |\n"
        "|---|---|---|---|\n"
        f"| n | {prof_lo['n']} | **{prof_mid['n']}** | {prof_hi['n']} |\n"
    )
    md.append(
        "| Entry price (p25 / med / p75) | "
        f"${prof_lo['entry_price'][0]:.2f} / "
        f"${prof_lo['entry_price'][1]:.2f} / "
        f"${prof_lo['entry_price'][2]:.2f} | "
        f"**${prof_mid['entry_price'][0]:.2f} / "
        f"${prof_mid['entry_price'][1]:.2f} / "
        f"${prof_mid['entry_price'][2]:.2f}** | "
        f"${prof_hi['entry_price'][0]:.2f} / "
        f"${prof_hi['entry_price'][1]:.2f} / "
        f"${prof_hi['entry_price'][2]:.2f} |\n"
    )
    md.append(
        "| Dip depth (p25 / med / p75) | "
        f"${prof_lo['dip_depth'][0]:.3f} / "
        f"${prof_lo['dip_depth'][1]:.3f} / "
        f"${prof_lo['dip_depth'][2]:.3f} | "
        f"**${prof_mid['dip_depth'][0]:.3f} / "
        f"${prof_mid['dip_depth'][1]:.3f} / "
        f"${prof_mid['dip_depth'][2]:.3f}** | "
        f"${prof_hi['dip_depth'][0]:.3f} / "
        f"${prof_hi['dip_depth'][1]:.3f} / "
        f"${prof_hi['dip_depth'][2]:.3f} |\n"
    )
    md.append(
        "| Hold sec (p25 / med / p75) | "
        f"{int(prof_lo['hold_sec'][0])} / "
        f"{int(prof_lo['hold_sec'][1])} / "
        f"{int(prof_lo['hold_sec'][2])} | "
        f"**{int(prof_mid['hold_sec'][0])} / "
        f"{int(prof_mid['hold_sec'][1])} / "
        f"{int(prof_mid['hold_sec'][2])}** | "
        f"{int(prof_hi['hold_sec'][0])} / "
        f"{int(prof_hi['hold_sec'][1])} / "
        f"{int(prof_hi['hold_sec'][2])} |\n"
    )
    all_periods = sorted(
        set(prof_lo["period_pct"]) | set(prof_mid["period_pct"])
        | set(prof_hi["period_pct"])
    )

    def _period_str(prof: dict) -> str:
        parts = []
        for p in all_periods:
            pct = prof["period_pct"].get(p, 0.0)
            parts.append(f"{p}: {pct:.0f}%")
        return ", ".join(parts)

    md.append(
        f"| Entry period split | {_period_str(prof_lo)} | "
        f"**{_period_str(prof_mid)}** | "
        f"{_period_str(prof_hi)} |\n"
    )
    md.append(
        "| Re-entry rate | "
        f"{prof_lo['reentry_rate']:.1f}% | "
        f"**{prof_mid['reentry_rate']:.1f}%** | "
        f"{prof_hi['reentry_rate']:.1f}% |\n"
    )
    md.append(
        "| Hit % / Stop % / Held % | "
        f"{prof_lo['hit_pct']:.1f}% / {prof_lo['stop_pct']:.1f}% / "
        f"{prof_lo['held_pct']:.1f}% | "
        f"**{prof_mid['hit_pct']:.1f}% / {prof_mid['stop_pct']:.1f}% / "
        f"{prof_mid['held_pct']:.1f}%** | "
        f"{prof_hi['hit_pct']:.1f}% / {prof_hi['stop_pct']:.1f}% / "
        f"{prof_hi['held_pct']:.1f}% |\n"
    )

    # Part 6 — concentration
    md.append("\n## Part 6 — Game-level concentration\n")
    md.append(
        f"- Distinct games producing entries: "
        f"**{concentration['distinct_games']}**\n"
        f"- Games with 1 entry: {concentration['games_1_entry']}\n"
        f"- Games with 2 entries (primary + re-entry): "
        f"{concentration['games_2_entries']}\n"
        f"- Games with at least one target hit ($0.90 exit): "
        f"{concentration['games_with_target_hit']} "
        f"({concentration['games_with_target_hit_pct']:.1f}% of "
        f"games-with-entry)\n"
    )

    # Verdict
    md.append("\n## Verdict\n")
    md.append(verdict)

    return "".join(md) + "\n"


def decide_verdict(
    loo: dict, boot: dict, prof_lo: dict, prof_mid: dict, prof_hi: dict,
    target_trades: list[dict],
) -> str:
    full_mean = float(np.mean([t["pnl"] for t in target_trades]))
    loo_lo, loo_hi = loo["range_mean"]
    loo_never_negative = loo_lo > 0
    swing_pct = (
        abs(loo["max_swing_delta"]) / abs(full_mean) * 100
        if full_mean != 0 else 0.0
    )
    p_gt_zero = boot["p_gt_zero"]

    # Profile divergence: is the 5.5-6.0 bucket's entry-price median
    # meaningfully different from BOTH adjacent buckets?
    mid_ep = prof_mid["entry_price"][1]
    lo_ep = prof_lo["entry_price"][1]
    hi_ep = prof_hi["entry_price"][1]
    ep_divergent = (
        abs(mid_ep - lo_ep) > 0.03 or abs(mid_ep - hi_ep) > 0.03
    )
    mid_hit = prof_mid["hit_pct"]
    lo_hit = prof_lo["hit_pct"]
    hi_hit = prof_hi["hit_pct"]
    hit_divergent = (
        abs(mid_hit - lo_hit) > 10.0 and abs(mid_hit - hi_hit) > 10.0
    )
    profile_divergent = ep_divergent or hit_divergent

    lines: list[str] = []
    lines.append(
        f"- Bootstrap P(mean > $0): **{100 * p_gt_zero:.1f}%** "
        f"({'>95% → robust' if p_gt_zero > 0.95 else 'not robust'})\n"
    )
    lines.append(
        f"- Leave-one-out min mean: **${loo_lo:+.2f}** "
        f"({'never goes negative' if loo_never_negative else 'can go negative'})\n"
    )
    lines.append(
        f"- Max single-entry swing: **{swing_pct:.0f}%** of full mean "
        f"({'> 50% → fragile' if swing_pct > 50 else '≤ 50% → stable'})\n"
    )
    lines.append(
        f"- Profile divergent from adjacent buckets: "
        f"**{'yes' if profile_divergent else 'no'}** "
        "(entry-price median Δ > $0.03 from at least one neighbor, "
        "or hit-rate Δ > 10pp from both neighbors)\n"
    )

    if p_gt_zero > 0.95 and loo_never_negative and profile_divergent:
        tag = "**Likely structural.**"
        rationale = (
            "Bootstrap CI is firmly positive, no single entry flips the "
            "result, and the entry profile differs meaningfully from "
            "adjacent buckets — consistent with a real effect rather "
            "than sampling noise."
        )
    elif p_gt_zero < 0.80 or swing_pct > 50:
        tag = "**Likely noise — treat as consistent with adjacent buckets.**"
        rationale = (
            "Either the bootstrap CI admits meaningful probability of "
            "negative true mean, or a single entry disproportionately "
            "drives the headline number. Don't read the +$6.17 as a "
            "load-bearing signal."
        )
    else:
        tag = "**Inconclusive at current sample size.**"
        rationale = (
            "The 5.5–6.0 bucket is positive and stable on most tests, "
            "but the sample is small enough that a structural vs noise "
            "verdict isn't warranted. Revisit once the dataset grows "
            "via the forward-collection cron."
        )

    lines.append(f"\n{tag}\n\n{rationale}\n")
    return "".join(lines)


# ---- Main --------------------------------------------------------------

def main() -> int:
    print("Loading 404-game Kalshi paired dataset...", flush=True)
    games = load_kalshi_games_all_spreads()
    print(f"  loaded {len(games)} games", flush=True)

    print("Simulating S4A on all games and bucketing...", flush=True)
    trades_by_bucket, bucket_summary, _precomp = simulate_and_bucket(games)

    print("Parity check on 5.5-6.0 bucket...", flush=True)
    parity_ok, parity_notes = parity_check(bucket_summary, trades_by_bucket)
    for note in parity_notes:
        print(f"  {note}", flush=True)
    if not parity_ok:
        print("\n!!! PARITY CHECK FAILED — diagnostics:", flush=True)
        for lab, _, _ in BUCKETS:
            s = bucket_summary[lab]
            print(
                f"  {lab}: games={s['n_games']} entries={s['entries']} "
                f"hit={s['hit_pct']:.1f}% mean=${s['mean_pnl']:+.2f}",
                flush=True,
            )
        return 2

    target = trades_by_bucket[TARGET_BUCKET]
    adj_lo = trades_by_bucket[ADJACENT_LOWER]
    adj_hi = trades_by_bucket[ADJACENT_UPPER]

    print(f"Leave-one-out on {len(target)} entries...", flush=True)
    pnls = [t["pnl"] for t in target]
    loo = leave_one_out(pnls)

    print(f"Bootstrap {BOOTSTRAP_N:,} resamples...", flush=True)
    boot = bootstrap(pnls, BOOTSTRAP_N, BOOTSTRAP_SEED)
    p_gt_257 = p_gt_threshold(pnls, BOOTSTRAP_N, BOOTSTRAP_SEED, 2.57)

    print("Adjacent-bucket profile comparison...", flush=True)
    prof_lo = profile_bucket(adj_lo)
    prof_mid = profile_bucket(target)
    prof_hi = profile_bucket(adj_hi)

    print("Game-level concentration...", flush=True)
    concentration = game_concentration(target)

    print("Rendering verdict + report...", flush=True)
    verdict = decide_verdict(loo, boot, prof_lo, prof_mid, prof_hi, target)
    md = render_report(
        games_total=len(games),
        bucket_summary=bucket_summary,
        parity_ok=parity_ok, parity_notes=parity_notes,
        target_trades=target,
        adjacent_lower_trades=adj_lo,
        adjacent_upper_trades=adj_hi,
        loo=loo, boot=boot, p_gt_257=p_gt_257,
        concentration=concentration, verdict=verdict,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    print(f"Report → {REPORT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
