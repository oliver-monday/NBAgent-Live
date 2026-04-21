"""Strategy 3 holdout validation.

Tests whether the positive-EV entry-filter configs found by
`strategy3_entry_filters.py` survive a train/test split. If the
best train config produces positive mean P&L on held-out test
games, the filters are VALIDATED. If not, they are CURVE-FIT and
S3 filtered should be deprioritized.

- Part 1: 110/55 train/test split (seed=42, game-level).
- Part 2: full 32-config filter grid on train.
- Part 3: top configs evaluated on test (the verdict).
- Part 4: 6-seed stability analysis (seeds 42-47).
- Part 5: S4A cross-reference on the same split.
- Part 6: final verdict.

Run:
    python -m analysis.strategy3_holdout_validation
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy3_entry_filters import (
    SIMPLE_EXIT, UPSIDE_EXIT, FilterConfig, replay_all,
)
from analysis.strategy3_stoploss_sweep import (
    MAX_SPREAD_COMPETITIVE,
    REG_SEASON_COMPETITIVE,
    load_game_timeseries,
    load_metadata,
)
from analysis.strategy4_dip_recovery import (
    BUCKET_SEC,
    REG_SEASON_GAMES,
    COMP_FRACTION,
    S4AConfig,
    _precompute_trailing_max,
    simulate_s4a,
    summarize_s4a,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "strategy3_holdout_validation.md"
)


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


# ---- Split -------------------------------------------------------------

def split_games(
    games: list[dict], meta: dict[str, dict], seed: int,
    train_n: int = 110,
) -> tuple[list[dict], list[dict]]:
    """Split competitive games into train/test deterministically."""
    comp_tickers = sorted(
        g["ticker"] for g in games
        if meta.get(g["ticker"]) is not None
        and meta[g["ticker"]]["abs_spread"] is not None
        and meta[g["ticker"]]["abs_spread"] <= MAX_SPREAD_COMPETITIVE
    )
    rng = np.random.default_rng(seed)
    shuffled = list(comp_tickers)
    rng.shuffle(shuffled)
    train_tickers = set(shuffled[:train_n])
    test_tickers = set(shuffled[train_n:])
    train = [g for g in games if g["ticker"] in train_tickers]
    test = [g for g in games if g["ticker"] in test_tickers]
    return train, test


# ---- 32-config filter grid --------------------------------------------

OSC_ON = FilterConfig(osc_lookback_sec=120, osc_recent_high=0.55)
WP_ON = FilterConfig(wp_lookback_sec=120, wp_drop_min=0.03)
FAV_ON = FilterConfig(fav_only=True)
PERIOD_ON = FilterConfig(allowed_periods={1, 2})


def _combine(
    osc: bool, wp: bool, fav: bool, period: bool,
) -> FilterConfig:
    return FilterConfig(
        osc_lookback_sec=OSC_ON.osc_lookback_sec if osc else None,
        osc_recent_high=OSC_ON.osc_recent_high if osc else None,
        wp_lookback_sec=WP_ON.wp_lookback_sec if wp else None,
        wp_drop_min=WP_ON.wp_drop_min if wp else None,
        fav_only=FAV_ON.fav_only if fav else False,
        allowed_periods=PERIOD_ON.allowed_periods if period else None,
    )


def _date_range(games: list[dict], meta: dict[str, dict]) -> str:
    dates = sorted(
        meta[g["ticker"]]["game_date"]
        for g in games
        if g["ticker"] in meta and meta[g["ticker"]].get("game_date")
    )
    return f"{dates[0]} → {dates[-1]}" if dates else "—"


def sweep_grid(games: list[dict], meta: dict[str, dict]) -> list[dict]:
    """Return the 32-config grid results on the given game set."""
    n_games = len(games)
    rows = []
    for osc in (True, False):
        for wp in (True, False):
            for fav in (True, False):
                for period in (True, False):
                    cfg = _combine(osc, wp, fav, period)
                    for exit_cfg in (SIMPLE_EXIT, UPSIDE_EXIT):
                        outs, _ = replay_all(games, meta, cfg, exit_cfg)
                        n = len(outs)
                        if n == 0:
                            mean_pnl = float("nan")
                            median_pnl = float("nan")
                            std_pnl = 0.0
                            annual_ev = 0.0
                        else:
                            pnls = np.array([o.net_pnl for o in outs])
                            mean_pnl = float(pnls.mean())
                            median_pnl = float(np.median(pnls))
                            std_pnl = (
                                float(pnls.std(ddof=1)) if n > 1 else 0.0
                            )
                            entries_per_game = n / n_games if n_games else 0
                            annual_ev = (
                                mean_pnl * entries_per_game
                                * REG_SEASON_COMPETITIVE
                            )
                        rows.append({
                            "osc": osc, "wp": wp, "fav": fav,
                            "period": period, "exit": exit_cfg.label,
                            "cfg": cfg, "exit_cfg": exit_cfg,
                            "entries": n,
                            "mean_pnl": mean_pnl,
                            "median_pnl": median_pnl,
                            "std_pnl": std_pnl,
                            "annual_ev": annual_ev,
                            "outcomes": outs,
                        })
    return rows


def _cfg_desc(row: dict) -> str:
    parts = []
    if row["osc"]:
        parts.append("osc")
    if row["wp"]:
        parts.append("wp")
    if row["fav"]:
        parts.append("fav")
    if row["period"]:
        parts.append("period")
    return "+".join(parts) if parts else "none"


def _sort_rows(rows: list[dict]) -> list[dict]:
    """Sort by mean P&L desc; non-finite (zero-entry) last."""
    def key(r):
        bad = r["entries"] == 0 or (isinstance(r["mean_pnl"], float) and np.isnan(r["mean_pnl"]))
        return (1 if bad else 0, -r["mean_pnl"] if not bad else 0.0)
    return sorted(rows, key=key)


# ---- Apply a specific config to a game set ----------------------------

def evaluate_config(
    games: list[dict], meta: dict, cfg: FilterConfig, exit_cfg,
) -> dict:
    outs, _ = replay_all(games, meta, cfg, exit_cfg)
    n = len(outs)
    n_games = len(games)
    if n == 0:
        return {
            "entries": 0, "mean_pnl": float("nan"),
            "median_pnl": float("nan"), "annual_ev": 0.0,
            "win_rate": 0.0, "outcomes": [],
        }
    pnls = np.array([o.net_pnl for o in outs])
    mean_pnl = float(pnls.mean())
    entries_per_game = n / n_games if n_games else 0
    return {
        "entries": n,
        "mean_pnl": mean_pnl,
        "median_pnl": float(np.median(pnls)),
        "annual_ev": mean_pnl * entries_per_game * REG_SEASON_COMPETITIVE,
        "win_rate": 100 * float((pnls > 0).mean()),
        "outcomes": outs,
    }


# ---- Rendering --------------------------------------------------------

def render_split_table(
    md: list[str], train: list[dict], test: list[dict],
    meta: dict,
) -> None:
    md.append("## Part 1 — Train/Test Split\n")
    md.append(
        "Games shuffled with `numpy.random.default_rng(seed=42)` "
        "then split 110/55. Split is at the game level so entries "
        "from the same game stay together.\n"
    )

    def count_entries(games: list[dict]) -> int:
        outs, _ = replay_all(games, meta, FilterConfig(), SIMPLE_EXIT)
        return len(outs)

    md.append("| Split | Games | Entries (unfiltered, simple exit) | Date range |")
    md.append("|---|---:|---:|---|")
    md.append(
        f"| Train | {len(train)} | {count_entries(train)} | "
        f"{_date_range(train, meta)} |"
    )
    md.append(
        f"| Test | {len(test)} | {count_entries(test)} | "
        f"{_date_range(test, meta)} |"
    )
    md.append("")


def render_train_grid(md: list[str], rows: list[dict]) -> None:
    md.append("## Part 2 — Train-set 32-config grid\n")
    md.append(
        "Full filter × exit grid on the **train set only**. "
        "Sorted by mean P&L descending. Positive-EV rows bolded.\n"
    )
    md.append(
        "| # | Osc | WP | Fav | Period | Exit | Entries | Mean P&L | Annual EV |"
    )
    md.append("|---|:-:|:-:|:-:|:-:|:-:|---:|---:|---:|")
    sorted_rows = _sort_rows(rows)
    for i, r in enumerate(sorted_rows, 1):
        def _m(b: bool) -> str:
            return "✓" if b else "—"
        if r["entries"] == 0 or (
            isinstance(r["mean_pnl"], float) and np.isnan(r["mean_pnl"])
        ):
            mn, ev = "—", "—"
        else:
            mn_raw = f"${r['mean_pnl']:+.2f}"
            ev_raw = f"${r['annual_ev']:+,.0f}"
            if r["mean_pnl"] > 0:
                mn = f"**{mn_raw}**"
                ev = f"**{ev_raw}**"
            else:
                mn, ev = mn_raw, ev_raw
        md.append(
            f"| {i} | {_m(r['osc'])} | {_m(r['wp'])} | {_m(r['fav'])} | "
            f"{_m(r['period'])} | {r['exit']} | {r['entries']} | {mn} | {ev} |"
        )
    md.append("")


def render_test_evaluation(
    md: list[str], train_rows: list[dict],
    test_games: list[dict], meta: dict,
    train_games: list[dict],
) -> tuple[dict, dict]:
    md.append("## Part 3 — Test-set evaluation (the verdict)\n")
    # Top 3 by mean P&L (with entries > 0)
    valid = [
        r for r in train_rows
        if r["entries"] > 0
        and not (isinstance(r["mean_pnl"], float) and np.isnan(r["mean_pnl"]))
    ]
    top_mean = sorted(valid, key=lambda r: -r["mean_pnl"])[:3]
    top_ev = sorted(valid, key=lambda r: -r["annual_ev"])[:3]
    # Deduplicate
    seen = set()
    candidates: list[dict] = []
    for r in top_mean + top_ev:
        k = (r["osc"], r["wp"], r["fav"], r["period"], r["exit"])
        if k not in seen:
            seen.add(k)
            candidates.append(r)

    md.append(
        f"Top {len(candidates)} candidate configs from train set "
        "(top-3 by mean P&L ∪ top-3 by annual EV). Each evaluated "
        "on the held-out **test set** with no re-fitting.\n"
    )
    md.append(
        "| Config | Train entries | Train mean P&L | Train annual EV | "
        "Test entries | Test mean P&L | Test annual EV | Verdict |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|:-:|")
    best_test = None  # (row, test_stats)
    for r in candidates:
        test_stats = evaluate_config(
            test_games, meta, r["cfg"], r["exit_cfg"],
        )
        desc = _cfg_desc(r) + f"/{r['exit']}"
        verdict = (
            "✓ VALIDATED"
            if (test_stats["entries"] > 0
                and not np.isnan(test_stats["mean_pnl"])
                and test_stats["mean_pnl"] > 0)
            else "✗ FAILED"
        )
        if test_stats["entries"] == 0 or np.isnan(test_stats["mean_pnl"]):
            test_mn = "—"
            test_ev = "—"
        else:
            test_mn = f"${test_stats['mean_pnl']:+.2f}"
            test_ev = f"${test_stats['annual_ev']:+,.0f}"
        md.append(
            f"| {desc} | {r['entries']} | ${r['mean_pnl']:+.2f} | "
            f"${r['annual_ev']:+,.0f} | {test_stats['entries']} | "
            f"{test_mn} | {test_ev} | {verdict} |"
        )
        if (
            test_stats["entries"] > 0
            and not np.isnan(test_stats["mean_pnl"])
        ):
            if best_test is None or test_stats["mean_pnl"] > best_test[1]["mean_pnl"]:
                best_test = (r, test_stats)
    md.append("")

    # 3B detail
    if best_test is None:
        md.append(
            "_No candidate produced usable test-set entries._\n"
        )
        return {}, {}
    best_row, best_stats = best_test
    md.append("### 3B — Test-set detail for best test config\n")
    md.append(
        f"**Config:** {_cfg_desc(best_row)} / exit={best_row['exit']}\n"
    )
    outs = best_stats["outcomes"]
    n = len(outs) or 1
    md.append("#### Outcome distribution (test set)\n")
    md.append("| Exit type | Count | % | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    by_type: dict[str, list[float]] = {}
    for o in outs:
        by_type.setdefault(o.exit_type, []).append(o.net_pnl)
    for et, pnls in sorted(by_type.items()):
        md.append(
            f"| {et} | {len(pnls)} | {100*len(pnls)/n:.1f}% | "
            f"${np.mean(pnls):+.2f} |"
        )
    md.append("")
    md.append("#### Test-set P&L distribution\n")
    md.append("| Bucket | Count | % |")
    md.append("|---|---:|---:|")
    for label, pred in (
        ("< −$30", lambda v: v < -30),
        ("−$30 to −$10", lambda v: -30 <= v < -10),
        ("−$10 to $0", lambda v: -10 <= v < 0),
        ("$0 to $10", lambda v: 0 <= v < 10),
        ("$10 to $20", lambda v: 10 <= v < 20),
        ("$20 to $30", lambda v: 20 <= v < 30),
        ("> $30", lambda v: v >= 30),
    ):
        c = sum(1 for o in outs if pred(o.net_pnl))
        md.append(f"| {label} | {c} | {100*c/n:.1f}% |")
    md.append("")

    md.append("#### Test-set by entry period\n")
    md.append("| Period | Entries | Win rate | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    for q_label, pred in (
        ("Q1", lambda o: o.entry_period == 1),
        ("Q2", lambda o: o.entry_period == 2),
        ("Q3", lambda o: o.entry_period == 3),
        ("Q4", lambda o: o.entry_period == 4),
        ("OT", lambda o: o.entry_period is not None and o.entry_period >= 5),
    ):
        sub = [o for o in outs if pred(o)]
        if not sub:
            md.append(f"| {q_label} | 0 | — | — |")
            continue
        wr = 100 * float(np.mean([o.net_pnl > 0 for o in sub]))
        mn = float(np.mean([o.net_pnl for o in sub]))
        md.append(f"| {q_label} | {len(sub)} | {wr:.1f}% | ${mn:+.2f} |")
    md.append("")

    md.append("#### Train vs test win rate\n")
    # Re-evaluate best config on train for side-by-side
    train_stats = evaluate_config(
        train_games, meta, best_row["cfg"], best_row["exit_cfg"],
    )
    md.append("| Split | Entries | Win rate | Mean P&L |")
    md.append("|---|---:|---:|---:|")
    md.append(
        f"| Train | {train_stats['entries']} | "
        f"{train_stats['win_rate']:.1f}% | "
        f"${train_stats['mean_pnl']:+.2f} |"
    )
    md.append(
        f"| Test | {best_stats['entries']} | "
        f"{best_stats['win_rate']:.1f}% | "
        f"${best_stats['mean_pnl']:+.2f} |"
    )
    md.append("")
    return best_row, best_stats


def render_stability(
    md: list[str], games: list[dict], meta: dict,
) -> tuple[int, int]:
    md.append("## Part 4 — Stability analysis (6 seeds)\n")
    md.append(
        "For each seed: split → sweep train → pick best-by-mean-P&L "
        "config → evaluate on test. Counts how many seeds produce a "
        "validated test result.\n"
    )
    md.append(
        "| Seed | Best train config | Train entries | Train mean P&L "
        "| Test entries | Test mean P&L | Test annual EV | Validated? |"
    )
    md.append("|---|---|---:|---:|---:|---:|---:|:-:|")
    validated = 0
    total = 0
    for seed in (42, 43, 44, 45, 46, 47):
        log(f"  Seed {seed}...")
        train, test = split_games(games, meta, seed=seed)
        rows = sweep_grid(train, meta)
        valid = [
            r for r in rows
            if r["entries"] > 0
            and not (isinstance(r["mean_pnl"], float) and np.isnan(r["mean_pnl"]))
        ]
        if not valid:
            md.append(f"| {seed} | — | 0 | — | — | — | — | — |")
            continue
        best = max(valid, key=lambda r: r["mean_pnl"])
        test_stats = evaluate_config(
            test, meta, best["cfg"], best["exit_cfg"],
        )
        is_valid = (
            test_stats["entries"] > 0
            and not np.isnan(test_stats["mean_pnl"])
            and test_stats["mean_pnl"] > 0
        )
        total += 1
        if is_valid:
            validated += 1
        verdict = "✓" if is_valid else "✗"
        desc = _cfg_desc(best) + f"/{best['exit']}"
        test_mn = (
            "—" if test_stats["entries"] == 0 or np.isnan(test_stats["mean_pnl"])
            else f"${test_stats['mean_pnl']:+.2f}"
        )
        test_ev = (
            "—" if test_stats["entries"] == 0 or np.isnan(test_stats["mean_pnl"])
            else f"${test_stats['annual_ev']:+,.0f}"
        )
        md.append(
            f"| {seed} | {desc} | {best['entries']} | "
            f"${best['mean_pnl']:+.2f} | {test_stats['entries']} | "
            f"{test_mn} | {test_ev} | {verdict} |"
        )
    md.append("")
    md.append(
        f"**Seeds validated: {validated} / {total}.**\n"
    )
    if validated >= 4:
        md.append(
            "≥ 4 of 6 seeds produced a positive test-set P&L — "
            "filters are **robust across splits**.\n"
        )
    elif validated <= 2:
        md.append(
            "≤ 2 of 6 seeds produced a positive test-set P&L — "
            "filters are **curve-fit**; the main-report 32-config "
            "result is likely overfitting noise.\n"
        )
    else:
        md.append(
            "3 of 6 seeds validated — **intermediate result**, "
            "filter effect is weak or partially noise-dominated.\n"
        )
    return validated, total


def render_s4a_compare(
    md: list[str], train: list[dict], test: list[dict],
    meta: dict,
) -> tuple[dict, dict]:
    md.append("## Part 5 — S4A cross-reference on same split\n")
    md.append(
        "Consistency check: S4A has no fitted parameters to validate "
        "(it's a single hypothesized config). Running it on train and "
        "test halves measures data-set homogeneity.\n"
    )
    s4a_cfg = S4AConfig(
        lookback_sec=180, dip_depth=0.08,
        entry_lo=0.50, entry_hi=0.75,
        exit_target=0.90, stop_loss=0.40,
    )
    lb_bins = max(1, int(s4a_cfg.lookback_sec / BUCKET_SEC))

    def _run_s4a(games: list[dict]) -> dict:
        # Filter to competitive + build precomp
        filt = [
            g for g in games
            if meta.get(g["ticker"]) is not None
            and meta[g["ticker"]]["abs_spread"] is not None
            and meta[g["ticker"]]["abs_spread"] <= MAX_SPREAD_COMPETITIVE
        ]
        # Each game needs abs_spread attached in the same shape S4A expects
        s4a_games = [
            {"ticker": g["ticker"],
             "ts": g["ts"],
             "abs_spread": meta[g["ticker"]]["abs_spread"]}
            for g in filt
        ]
        precomp = {
            (g["ticker"], lb_bins):
            _precompute_trailing_max(
                g["ts"]["fav_kalshi_vwap"].values.astype(float), lb_bins,
            )
            for g in s4a_games
        }
        trades = simulate_s4a(s4a_games, s4a_cfg, precomp)
        return summarize_s4a(trades, len(s4a_games))

    train_s4a = _run_s4a(train)
    test_s4a = _run_s4a(test)
    # S3 best-filter on same split
    train_rows = sweep_grid(train, meta)
    valid = [
        r for r in train_rows
        if r["entries"] > 0
        and not (isinstance(r["mean_pnl"], float) and np.isnan(r["mean_pnl"]))
    ]
    if valid:
        s3_best = max(valid, key=lambda r: r["mean_pnl"])
        s3_train = {
            "entries": s3_best["entries"],
            "mean_pnl": s3_best["mean_pnl"],
        }
        s3_test_stats = evaluate_config(
            test, meta, s3_best["cfg"], s3_best["exit_cfg"],
        )
    else:
        s3_train = {"entries": 0, "mean_pnl": float("nan")}
        s3_test_stats = {"entries": 0, "mean_pnl": float("nan")}

    md.append(
        "| Strategy | Train entries | Train mean P&L | Test entries | "
        "Test mean P&L | Consistent? |"
    )
    md.append("|---|---:|---:|---:|---:|:-:|")

    def _fmt(x):
        if isinstance(x, float) and np.isnan(x):
            return "—"
        return f"${x:+.2f}"

    def _consistent(a, b, tol=5.0):
        if isinstance(a, float) and np.isnan(a):
            return False
        if isinstance(b, float) and np.isnan(b):
            return False
        return abs(a - b) <= tol

    md.append(
        f"| S3 best filter | {s3_train['entries']} | "
        f"{_fmt(s3_train['mean_pnl'])} | {s3_test_stats['entries']} | "
        f"{_fmt(s3_test_stats['mean_pnl'])} | "
        f"{'✓' if _consistent(s3_train['mean_pnl'], s3_test_stats['mean_pnl']) else '✗'} |"
    )
    md.append(
        f"| S4A best config | {train_s4a['entries']} | "
        f"{_fmt(train_s4a['mean_pnl'])} | {test_s4a['entries']} | "
        f"{_fmt(test_s4a['mean_pnl'])} | "
        f"{'✓' if _consistent(train_s4a['mean_pnl'], test_s4a['mean_pnl']) else '✗'} |"
    )
    md.append("")
    md.append(
        "_Consistency tolerance: ±$5 mean-P&L gap between train and test._\n"
    )
    return train_s4a, test_s4a


def render_verdict(
    md: list[str], best_test_row: dict, best_test_stats: dict,
    validated: int, total: int, s4a_test: dict,
) -> None:
    md.append("## Part 6 — Final verdict\n")
    if validated >= 4:
        status = "VALIDATED"
    elif validated <= 2:
        status = "CURVE-FIT"
    else:
        status = "INCONCLUSIVE"
    md.append(f"**Strategy 3 filtered: {status}** "
              f"({validated} of {total} seeds validated)\n")
    if status == "VALIDATED" and best_test_row:
        desc = _cfg_desc(best_test_row) + f"/{best_test_row['exit']}"
        md.append(
            f"- Recommended filter config: **{desc}**\n"
            f"- Test-set mean P&L: **${best_test_stats['mean_pnl']:+.2f}/entry**\n"
            f"- Test-set annual EV estimate: "
            f"**${best_test_stats['annual_ev']:+,.0f}** "
            f"(from held-out sample, not train)\n"
        )
        s3_ev = best_test_stats["annual_ev"]
    elif status == "CURVE-FIT":
        md.append(
            "- Train-set positives do not replicate on held-out "
            "games. The 32-config grid search appears to have "
            "captured noise. **S3 filtered is deprioritized.**\n"
            "- Phase 4a operational spec should rely on S1 bilateral "
            "and S4A only.\n"
        )
        s3_ev = 0
    else:
        md.append(
            "- Mixed signal — some seeds validate, others don't. "
            "Treat S3 filtered with skepticism; do not size large on "
            "it in Phase 4a.\n"
        )
        s3_ev = (
            best_test_stats["annual_ev"]
            if best_test_stats else 0
        )

    # Combined projection
    md.append("### Combined annual-EV projection\n")
    s4a_annual = (
        s4a_test["annual_ev"]
        if s4a_test and not np.isnan(s4a_test.get("mean_pnl", float("nan")))
        else 1886  # fall back to full-sample estimate
    )
    s1_annual = 1608
    md.append("| Strategy | Annual EV |")
    md.append("|---|---:|")
    md.append(f"| S1 bilateral | +${s1_annual:,} |")
    if status == "VALIDATED":
        md.append(f"| S3 filtered (test-set estimate) | +${s3_ev:,.0f} |")
    else:
        md.append("| S3 filtered | deprioritized |")
    md.append(
        f"| S4A best config (test-set half) | ${s4a_annual:+,.0f} |"
    )
    if status == "VALIDATED":
        total_ev = s1_annual + s3_ev + s4a_annual
    else:
        total_ev = s1_annual + s4a_annual
    md.append(f"| **Combined** | **${total_ev:+,.0f}** |")
    md.append("")


# ---- Main -------------------------------------------------------------

def main() -> int:
    log("Loading games + metadata...")
    games = load_game_timeseries()
    meta = load_metadata(PAIRED_DIR / "matched_games.csv")
    log(f"Loaded {len(games)} games, meta for {len(meta)}")

    md: list[str] = []
    md.append("# Strategy 3 — Holdout Validation\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Tests whether the positive-EV entry-filter configurations "
        "found by `strategy3_entry_filters.py` survive a train/test "
        "split. If the best train config produces positive mean P&L "
        "on held-out test games, filters are **validated**. If not, "
        "they are **curve-fit** and should be deprioritized.\n"
    )

    # Seed 42 primary split
    log("Splitting games (seed=42)...")
    train, test = split_games(games, meta, seed=42)
    log(f"Train {len(train)}, Test {len(test)}")
    render_split_table(md, train, test, meta)

    log("Running 32-config grid on train set...")
    train_rows = sweep_grid(train, meta)
    render_train_grid(md, train_rows)

    log("Evaluating top configs on test set...")
    best_test_row, best_test_stats = render_test_evaluation(
        md, train_rows, test, meta, train,
    )

    log("Running 6-seed stability analysis...")
    validated, total = render_stability(md, games, meta)

    log("Running S4A cross-reference...")
    train_s4a, test_s4a = render_s4a_compare(md, train, test, meta)

    render_verdict(
        md, best_test_row, best_test_stats,
        validated, total, test_s4a,
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(md) + "\n")
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
