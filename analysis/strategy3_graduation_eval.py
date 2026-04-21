"""Strategy 3 formal graduation evaluation.

Reads paired timeseries CSVs from data/wp_kalshi_paired/ and runs
round-trip detection at multiple grids to evaluate graduation
criteria from docs/KILL_CRITERIA_draft.md.

Uses the fav_kalshi_vwap column (and its complement for the
underdog side) to detect price threshold crossings, then measures
round-trip frequency, net P&L, hold time, and exit zone behavior.

Run:
    python -m analysis.strategy3_graduation_eval

    # With metadata for spread filtering
    python -m analysis.strategy3_graduation_eval \\
        --metadata data/wp_kalshi_paired/matched_games.csv
"""

from __future__ import annotations

import argparse
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy3_graduation_eval.md"
)

TICKER_RE = re.compile(r"(KXNBAGAME-\d{2}[A-Z]{3}\d{2}[A-Z]{6})")

RT_GRIDS: list[tuple[float, float]] = [
    (0.35, 0.45),
    (0.35, 0.50),
    (0.40, 0.50),  # primary grid
    (0.40, 0.55),
    (0.45, 0.55),
]
PRIMARY_GRID = (0.40, 0.50)
CONTRACT_SIZE = 100
MAX_SPREAD_COMPETITIVE = 6.0

Q_LEN_SEC = 720
OT_LEN_SEC = 300


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def maker_fee(contracts: int, price: float) -> float:
    """Kalshi maker fee: ceil(0.0175 × C × P × (1-P)) to the cent."""
    if price <= 0 or price >= 1:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1.0 - price) * 100) / 100


# ---- Loading ------------------------------------------------------------

def discover_timeseries() -> list[tuple[str, Path]]:
    out = []
    for p in sorted(PAIRED_DIR.glob("*_timeseries.csv")):
        m = TICKER_RE.match(p.stem)
        if not m:
            continue
        out.append((m.group(1), p))
    return out


def load_timeseries(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        return df
    for c in (
        "game_seconds_elapsed", "period", "fav_wp_espn",
        "fav_kalshi_vwap", "fav_kalshi_last", "delta",
        "kalshi_volume", "kalshi_trade_count",
    ):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["game_seconds_elapsed", "fav_kalshi_vwap"])
    return df.sort_values("game_seconds_elapsed").reset_index(drop=True)


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


# ---- Round-trip detection -----------------------------------------------

def detect_round_trips(
    prices: np.ndarray, elapsed: np.ndarray, periods: np.ndarray,
    entry_thr: float, exit_thr: float,
) -> list[dict]:
    """Walk chronologically. Enter at ≤ entry_thr, exit at ≥ exit_thr.
    Only count round-trips where exit is strictly after entry (hold>0).
    """
    trips: list[dict] = []
    in_pos = False
    entry_price = entry_elapsed = entry_period = None
    for i in range(len(prices)):
        p = prices[i]
        if pd.isna(p):
            continue
        if not in_pos and p <= entry_thr:
            in_pos = True
            entry_price = float(p)
            entry_elapsed = float(elapsed[i])
            entry_period = int(periods[i]) if not pd.isna(periods[i]) else None
        elif in_pos and p >= exit_thr:
            hold = float(elapsed[i]) - entry_elapsed
            if hold <= 0:
                continue
            exit_period = int(periods[i]) if not pd.isna(periods[i]) else None
            trips.append({
                "entry_price": entry_price,
                "exit_price": float(p),
                "entry_elapsed": entry_elapsed,
                "exit_elapsed": float(elapsed[i]),
                "hold_time_sec": hold,
                "entry_period": entry_period,
                "exit_period": exit_period,
            })
            in_pos = False
            entry_price = entry_elapsed = entry_period = None
    return trips


def score_trips(trips: list[dict]) -> list[dict]:
    out = []
    for t in trips:
        gross = (t["exit_price"] - t["entry_price"]) * CONTRACT_SIZE
        fee_in = maker_fee(CONTRACT_SIZE, t["entry_price"])
        fee_out = maker_fee(CONTRACT_SIZE, t["exit_price"])
        net = gross - fee_in - fee_out
        out.append({
            **t,
            "gross": gross,
            "fees": fee_in + fee_out,
            "net": net,
        })
    return out


# ---- Aggregation helpers ------------------------------------------------

def max_period(ts: pd.DataFrame) -> int:
    if ts.empty or "period" not in ts.columns:
        return 4
    mp = ts["period"].dropna().max()
    return int(mp) if not pd.isna(mp) else 4


def total_game_length_sec(mp: int) -> int:
    if mp <= 4:
        return 4 * Q_LEN_SEC
    return 4 * Q_LEN_SEC + (mp - 4) * OT_LEN_SEC


def fmt_hold(seconds: float) -> str:
    if pd.isna(seconds):
        return "—"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def period_label(p: int | None) -> str:
    if p is None:
        return "—"
    return f"Q{p}" if p <= 4 else f"OT{p-4}"


# ---- Report sections ----------------------------------------------------

def section_1_sample(
    md: list[str], all_games: int, competitive: int, dates: list[str],
) -> None:
    md.append("## §1 — Sample summary\n")
    md.append(
        f"- Games analyzed: **{competitive}** (of {all_games} total "
        "timeseries files)"
    )
    md.append(
        f"- Competitive games (|spread| ≤ {MAX_SPREAD_COMPETITIVE:.0f}): "
        f"**{competitive}**"
    )
    if dates:
        md.append(f"- Date range: {min(dates)} to {max(dates)}")
    md.append("")


def section_2_frequency(
    md: list[str], per_game: list[dict], n_games: int,
) -> None:
    md.append("## §2 — Round-trip frequency by grid\n")
    md.append(
        "| Grid | Games w/ ≥1 RT | RT frequency | Total RTs | "
        "RTs/game (mean) |"
    )
    md.append("|---|---:|---:|---:|---:|")
    for grid in RT_GRIDS:
        games_with = 0
        total = 0
        for g in per_game:
            trips = g["grids"][grid]["all"]
            if trips:
                games_with += 1
            total += len(trips)
        freq = 100 * games_with / n_games if n_games else 0.0
        rtg = total / n_games if n_games else 0.0
        md.append(
            f"| ({grid[0]:.2f}, {grid[1]:.2f}) | "
            f"{games_with} / {n_games} | {freq:.1f}% | "
            f"{total} | {rtg:.2f} |"
        )
    md.append("")


def section_3_economics(
    md: list[str], per_game: list[dict], grid: tuple[float, float],
) -> None:
    md.append(
        f"## §3 — Round-trip economics (primary grid "
        f"{grid[0]:.2f}, {grid[1]:.2f})\n"
    )
    trips = [t for g in per_game for t in g["grids"][grid]["all"]]
    if not trips:
        md.append("_No round-trips at primary grid._\n")
        return
    nets = np.array([t["net"] for t in trips])
    grosses = np.array([t["gross"] for t in trips])
    holds = np.array([t["hold_time_sec"] for t in trips])
    pct_profitable = 100 * float((nets > 0).mean())
    md.append("| Metric | Value |")
    md.append("|---|---|")
    md.append(f"| Total round-trips | {len(trips)} |")
    md.append(f"| Median gross profit | ${np.median(grosses):.2f} |")
    md.append(f"| Median net profit (maker-maker) | ${np.median(nets):.2f} |")
    md.append(f"| Mean net profit (maker-maker) | ${nets.mean():.2f} |")
    md.append(f"| Median hold time | {fmt_hold(np.median(holds))} |")
    md.append(f"| Mean hold time | {fmt_hold(holds.mean())} |")
    md.append(f"| Min hold time | {fmt_hold(holds.min())} |")
    md.append(f"| Max hold time | {fmt_hold(holds.max())} |")
    md.append(f"| Profitable trips (net > 0) | {pct_profitable:.1f}% |")
    md.append("")
    md.append("### Distribution of net profit\n")
    buckets = [
        ("< $0", lambda v: v < 0),
        ("$0 - $5", lambda v: 0 <= v < 5),
        ("$5 - $10", lambda v: 5 <= v < 10),
        ("$10 - $15", lambda v: 10 <= v < 15),
        ("$15 - $20", lambda v: 15 <= v < 20),
        ("> $20", lambda v: v >= 20),
    ]
    md.append("| Net profit bucket | Count | % |")
    md.append("|---|---:|---:|")
    for label, pred in buckets:
        count = int(np.array([pred(v) for v in nets]).sum())
        pct = 100 * count / len(trips)
        md.append(f"| {label} | {count} | {pct:.1f}% |")
    md.append("")


def section_4_hold_time(
    md: list[str], per_game: list[dict], grid: tuple[float, float],
) -> None:
    md.append("## §4 — Hold time distribution (primary grid)\n")
    trips = [t for g in per_game for t in g["grids"][grid]["all"]]
    if not trips:
        md.append("_No round-trips._\n")
        return
    buckets = [
        ("< 1 min", lambda s: s < 60),
        ("1-5 min", lambda s: 60 <= s < 300),
        ("5-15 min", lambda s: 300 <= s < 900),
        ("15-30 min", lambda s: 900 <= s < 1800),
        ("30-60 min", lambda s: 1800 <= s < 3600),
        ("> 60 min", lambda s: s >= 3600),
    ]
    md.append("| Hold time bucket | Count | % |")
    md.append("|---|---:|---:|")
    for label, pred in buckets:
        cnt = sum(1 for t in trips if pred(t["hold_time_sec"]))
        pct = 100 * cnt / len(trips)
        md.append(f"| {label} | {cnt} | {pct:.1f}% |")
    md.append("")


def section_5_period(
    md: list[str], per_game: list[dict], grid: tuple[float, float],
) -> None:
    md.append("## §5 — Entry period distribution (primary grid)\n")
    trips = [t for g in per_game for t in g["grids"][grid]["all"]]
    if not trips:
        md.append("_No round-trips._\n")
        return
    md.append("| Entry period | RTs | % | Mean net |")
    md.append("|---|---:|---:|---:|")
    for p_label, pred in (
        ("Q1", lambda t: t["entry_period"] == 1),
        ("Q2", lambda t: t["entry_period"] == 2),
        ("Q3", lambda t: t["entry_period"] == 3),
        ("Q4", lambda t: t["entry_period"] == 4),
        ("OT", lambda t: t["entry_period"] is not None and t["entry_period"] >= 5),
    ):
        sub = [t for t in trips if pred(t)]
        if not sub:
            md.append(f"| {p_label} | 0 | 0.0% | — |")
            continue
        pct = 100 * len(sub) / len(trips)
        mean_net = np.mean([t["net"] for t in sub])
        md.append(
            f"| {p_label} | {len(sub)} | {pct:.1f}% | ${mean_net:.2f} |"
        )
    md.append("")


def section_6_exit_timing(
    md: list[str], per_game: list[dict], grid: tuple[float, float],
) -> None:
    md.append("## §6 — Exit timing analysis\n")
    md.append(
        "Tests the convergence-zone exit preference: do round-trips "
        "that complete in the 1–3 min window have better outcomes?\n"
    )
    md.append("| Exit time remaining | RTs | % | Mean net |")
    md.append("|---|---:|---:|---:|")
    all_trips = []
    for g in per_game:
        for t in g["grids"][grid]["all"]:
            tr_remaining = g["total_length_sec"] - t["exit_elapsed"]
            all_trips.append((t, tr_remaining))
    if not all_trips:
        md.append("| — | 0 | — | — |")
        md.append("")
        return
    buckets = [
        ("> 12 min", lambda tr: tr > 12 * 60),
        ("6-12 min", lambda tr: 6 * 60 < tr <= 12 * 60),
        ("3-6 min", lambda tr: 3 * 60 < tr <= 6 * 60),
        ("1-3 min", lambda tr: 60 < tr <= 3 * 60),
        ("0-1 min", lambda tr: 0 <= tr <= 60),
    ]
    for label, pred in buckets:
        sub = [t for t, tr in all_trips if pred(tr)]
        if not sub:
            md.append(f"| {label} | 0 | 0.0% | — |")
            continue
        pct = 100 * len(sub) / len(all_trips)
        mn = np.mean([t["net"] for t in sub])
        md.append(f"| {label} | {len(sub)} | {pct:.1f}% | ${mn:.2f} |")
    md.append("")


def section_7_bilateral(
    md: list[str], per_game: list[dict], n_games: int,
) -> None:
    md.append("## §7 — Bilateral entry frequency\n")

    def both_dipped(g: dict, thr: float) -> tuple[bool, float | None]:
        """Return (both_dipped, seconds_between_dips)."""
        ts = g["ts"]
        if ts.empty:
            return False, None
        fav = ts["fav_kalshi_vwap"].values
        dog = 1.0 - fav
        el = ts["game_seconds_elapsed"].values
        fav_mask = fav <= thr
        dog_mask = dog <= thr
        if not (fav_mask.any() and dog_mask.any()):
            return False, None
        fav_first = float(el[np.argmax(fav_mask)])
        dog_first = float(el[np.argmax(dog_mask)])
        return True, abs(fav_first - dog_first)

    n_040 = 0
    n_035 = 0
    gaps_040 = []
    for g in per_game:
        ok_040, gap_040 = both_dipped(g, 0.40)
        ok_035, _ = both_dipped(g, 0.35)
        if ok_040:
            n_040 += 1
            if gap_040 is not None:
                gaps_040.append(gap_040)
        if ok_035:
            n_035 += 1
    pct_040 = 100 * n_040 / n_games if n_games else 0.0
    pct_035 = 100 * n_035 / n_games if n_games else 0.0
    md.append(
        f"- Games where both sides dipped ≤ $0.40: "
        f"**{n_040} / {n_games} ({pct_040:.1f}%)**"
    )
    md.append(
        f"- Games where both sides dipped ≤ $0.35: "
        f"**{n_035} / {n_games} ({pct_035:.1f}%)**"
    )
    if gaps_040:
        mean_gap_sec = float(np.mean(gaps_040))
        md.append(
            f"\n**When both sides dip ≤ $0.40:**\n\n"
            f"- Mean time between dips: "
            f"{fmt_hold(mean_gap_sec)} of game-clock elapsed\n"
        )
    # Guaranteed bilateral P&L at ($0.40, $0.40)
    one_side = 0.40
    fee_entry = maker_fee(CONTRACT_SIZE, one_side)
    # Losing side exits at $0.00 (no fee — self-settles at $0), winning
    # side resolves to $1.00 (no exit fee either). Total cost both legs
    # = 2 × 100 × $0.40 = $80; payout = $100. Gross = $20. Two entry
    # maker fees per the §7 spec.
    gross = 20.0
    fees = 2 * fee_entry  # only the 2 entry legs have maker fees; resolution has none
    md.append(
        "\n**Guaranteed bilateral profit (if both fill at $0.40, "
        "both held to resolution):**\n"
    )
    md.append(f"- Payout: ${100.0:.2f} (one side resolves YES)")
    md.append(f"- Total cost: ${2 * one_side * CONTRACT_SIZE:.2f} "
              f"(2 × $0.40 × {CONTRACT_SIZE})")
    md.append(f"- Gross: ${gross:.2f}")
    md.append(
        f"- Fees (2 maker entry legs; losing side self-settles at $0, "
        f"winner at $1): ${fees:.2f}"
    )
    md.append(f"- **Net: ${gross - fees:.2f}**")
    md.append("")


def section_8_scorecard(
    md: list[str], per_game: list[dict], n_games: int,
    grid: tuple[float, float],
) -> None:
    md.append("## §8 — Formal graduation scorecard\n")
    md.append(f"**Sample:** {n_games} competitive games "
              f"(|spread| ≤ {MAX_SPREAD_COMPETITIVE:.0f})\n")

    primary_trips = [
        t for g in per_game for t in g["grids"][grid]["all"]
    ]
    games_with_primary = sum(
        1 for g in per_game if g["grids"][grid]["all"]
    )
    rt_freq_pct = 100 * games_with_primary / n_games if n_games else 0.0
    if primary_trips:
        median_net = float(np.median([t["net"] for t in primary_trips]))
        median_hold = float(np.median(
            [t["hold_time_sec"] for t in primary_trips]
        ))
        pct_under_90 = 100 * np.mean(
            [t["hold_time_sec"] < 90 for t in primary_trips]
        )
        all_under_90 = bool(np.all(
            [t["hold_time_sec"] < 90 for t in primary_trips]
        ))
    else:
        median_net = 0.0
        median_hold = 0.0
        pct_under_90 = 0.0
        all_under_90 = False

    def check(val, op, bar) -> str:
        if op == ">=":
            return "✓" if val >= bar else "✗"
        if op == "<=":
            return "✓" if val <= bar else "✗"
        if op == "<":
            return "✓" if val < bar else "✗"
        if op == "bool_false":
            return "✓" if not val else "✗"
        return "?"

    c1 = check(rt_freq_pct, ">=", 15.0)
    c2 = check(median_net, ">=", 5.0)
    c5 = check(median_hold, ">=", 180.0)
    c6 = check(all_under_90, "bool_false", None)

    md.append("### Graduates if ALL pass:\n")
    md.append("| # | Criterion | Threshold | Measured | Status |")
    md.append("|---|---|---|---|---|")
    md.append(
        f"| 1 | RT frequency at (0.40, 0.50) | ≥ 15% | "
        f"{rt_freq_pct:.1f}% ({games_with_primary}/{n_games}) | {c1} |"
    )
    md.append(
        f"| 2 | Median net per trip (maker) | ≥ $5 | "
        f"${median_net:.2f} | {c2} |"
    )
    md.append(
        "| 3 | Realized spread (median) | ≤ $0.02 | $0.01* | ✓ |"
    )
    md.append(
        "| 4 | Depth (% ≥ 50k at entry) | ≥ 50% | 55%* | ✓ |"
    )
    md.append(
        f"| 5 | Hold time (median) | ≥ 3 min | "
        f"{fmt_hold(median_hold)} | {c5} |"
    )
    md.append(
        f"| 6 | All RTs complete in < 90s | No | "
        f"{pct_under_90:.1f}% < 90s | {c6} |"
    )
    md.append(
        "\n*Criteria 3 and 4 are from live orderbook data (n=5 logged "
        "games). Not measurable from historical trade data. Values "
        "carried forward from prior measurement.*\n"
    )

    # Kill triggers
    k1 = check(rt_freq_pct, "<", 5.0)   # triggers if RT freq < 5%
    k2 = check(median_net, "<", 0.0)
    k_pass = all(s == "✓" for s in (c1, c2, c5, c6))  # using "✓" for pass
    md.append("### Kill triggers (fail if ANY):\n")
    md.append("| # | Criterion | Threshold | Measured | Status |")
    md.append("|---|---|---|---|---|")
    md.append(
        f"| K1 | RT frequency | < 5% | {rt_freq_pct:.1f}% | "
        f"{'KILL' if rt_freq_pct < 5.0 else 'safe'} |"
    )
    md.append(
        f"| K2 | Median net per trip | < $0 | ${median_net:.2f} | "
        f"{'KILL' if median_net < 0 else 'safe'} |"
    )
    md.append(
        "| K3 | Realized spread | ≥ $0.03 | $0.01* | safe |"
    )
    md.append(
        f"| K4 | All RTs < 90s | Yes | {pct_under_90:.1f}% < 90s | "
        f"{'KILL' if all_under_90 else 'safe'} |"
    )
    md.append("")

    # Verdict
    graduation_pass = all([
        c1 == "✓", c2 == "✓", c5 == "✓", c6 == "✓",
    ])
    any_kill = any([
        rt_freq_pct < 5.0, median_net < 0, all_under_90,
    ])
    if any_kill:
        verdict = "KILLED"
    elif graduation_pass:
        verdict = "GRADUATED"
    else:
        verdict = "NOT YET"

    md.append(f"### Verdict: **{verdict}**\n")
    if verdict == "GRADUATED":
        md.append(
            "All measurable criteria pass. Phase 4a (signal alerts "
            "for manual paper-trading) is unlocked per "
            "`docs/KILL_CRITERIA_draft.md`.\n"
        )
    elif verdict == "NOT YET":
        fails = []
        if c1 != "✓":
            fails.append("RT frequency")
        if c2 != "✓":
            fails.append("median net")
        if c5 != "✓":
            fails.append("median hold time")
        if c6 != "✓":
            fails.append("all-under-90s flag")
        md.append(
            "Some criteria did not pass: "
            + ", ".join(fails) + ". "
            "Review per-criterion results above and either iterate on "
            "the strategy spec or collect more data.\n"
        )
    else:
        md.append(
            "A kill trigger fired. Strategy 3 in current form is not "
            "viable at the evaluated grid. See the kill table above "
            "for which criterion failed.\n"
        )


# ---- Main ---------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metadata", type=str,
        default=str(PAIRED_DIR / "matched_games.csv"),
        help="Matched games CSV (for |spread| filtering).",
    )
    parser.add_argument(
        "--output", type=str, default=str(DEFAULT_OUTPUT),
    )
    args = parser.parse_args()

    meta_map = load_metadata(Path(args.metadata))
    log(f"Metadata loaded for {len(meta_map)} games")

    ts_files = discover_timeseries()
    log(f"Discovered {len(ts_files)} timeseries files")

    per_game: list[dict] = []
    dates: list[str] = []
    for ticker, path in ts_files:
        meta = meta_map.get(ticker)
        abs_spread = meta["abs_spread"] if meta else None
        if abs_spread is None or abs_spread > MAX_SPREAD_COMPETITIVE:
            continue
        ts = load_timeseries(path)
        if ts.empty:
            continue
        fav = ts["fav_kalshi_vwap"].values.astype(float)
        dog = 1.0 - fav
        elapsed = ts["game_seconds_elapsed"].values.astype(float)
        periods = ts["period"].values
        mp = max_period(ts)
        total_len = total_game_length_sec(mp)
        grids: dict[tuple[float, float], dict] = {}
        for entry, exit_ in RT_GRIDS:
            fav_raw = detect_round_trips(fav, elapsed, periods, entry, exit_)
            dog_raw = detect_round_trips(dog, elapsed, periods, entry, exit_)
            fav_trips = score_trips(fav_raw)
            dog_trips = score_trips(dog_raw)
            for t in fav_trips:
                t["side"] = "fav"
            for t in dog_trips:
                t["side"] = "dog"
            grids[(entry, exit_)] = {
                "fav": fav_trips, "dog": dog_trips,
                "all": fav_trips + dog_trips,
            }
        per_game.append({
            "ticker": ticker,
            "ts": ts,
            "max_period": mp,
            "total_length_sec": total_len,
            "abs_spread": abs_spread,
            "grids": grids,
        })
        if meta and meta.get("game_date"):
            dates.append(meta["game_date"])

    n_games = len(per_game)
    log(f"Competitive games evaluated: {n_games}")

    md: list[str] = []
    md.append("# Strategy 3 — Formal Graduation Evaluation\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Round-trip detection on 168-game paired Kalshi trade-price "
        "timeseries. Evaluates graduation criteria from "
        "`docs/KILL_CRITERIA_draft.md` on competitive games only "
        f"(|spread| ≤ {MAX_SPREAD_COMPETITIVE:.0f}).\n"
    )
    section_1_sample(md, len(ts_files), n_games, dates)
    section_2_frequency(md, per_game, n_games)
    section_3_economics(md, per_game, PRIMARY_GRID)
    section_4_hold_time(md, per_game, PRIMARY_GRID)
    section_5_period(md, per_game, PRIMARY_GRID)
    section_6_exit_timing(md, per_game, PRIMARY_GRID)
    section_7_bilateral(md, per_game, n_games)
    section_8_scorecard(md, per_game, n_games, PRIMARY_GRID)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md) + "\n")
    log(f"Report → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
