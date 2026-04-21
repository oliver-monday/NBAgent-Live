"""Strategy 3 failed-entry & worst-case distribution analysis.

Complement to the graduation evaluation: measures every entry
event at ≤ entry_threshold (default $0.40) across 165 competitive
games — not just completed round-trips but also positions held to
resolution (wins and losses). Produces true EV per entry, fail
rate by quarter and spread, max-adverse-excursion distribution,
and worst-case scenarios.

Run:
    python -m analysis.strategy3_failed_entries
    python -m analysis.strategy3_failed_entries \\
        --metadata data/wp_kalshi_paired/matched_games.csv
    python -m analysis.strategy3_failed_entries \\
        --metadata data/wp_kalshi_paired/matched_games.csv \\
        --entry 0.40 --exit 0.50
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PAIRED_DIR = REPO_ROOT / "data" / "wp_kalshi_paired"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy3_failed_entries.md"
)
ENTRIES_CSV = PAIRED_DIR / "all_entries.csv"

TICKER_RE = re.compile(r"(KXNBAGAME-\d{2}[A-Z]{3}\d{2}[A-Z]{6})")
CONTRACT_SIZE = 100
MAX_SPREAD_COMPETITIVE = 6.0
RESOLUTION_WIN_CUTOFF = 0.95
RESOLUTION_LOSS_CUTOFF = 0.05
NEAR_MISS_PAD = 0.02  # MFE within $0.02 of exit threshold = "came close"


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def maker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1.0 - price) * 100) / 100


# ---- Entry record -------------------------------------------------------

@dataclass
class EntryRecord:
    game_ticker: str
    side: str
    entry_price: float
    entry_time: str
    entry_game_seconds: float
    entry_period: int | None
    outcome: str                  # completed | held_win | held_loss | held_mid
    exit_price: float
    resolution_value: float
    hold_time_sec: float
    gross_pnl: float
    net_pnl: float
    max_adverse_excursion: float  # lowest price during hold
    max_favorable_excursion: float  # highest price during hold
    mae_pct: float                # (entry - MAE) / entry
    came_close: bool
    exit_period: int | None = None
    abs_spread: float | None = None


# ---- State machine ------------------------------------------------------

def detect_entries_one_side(
    game_ticker: str, side: str, prices: np.ndarray,
    times: np.ndarray, elapsed: np.ndarray, periods: np.ndarray,
    entry_thr: float, exit_thr: float,
) -> list[EntryRecord]:
    """Walk the timeseries for one side. Track every entry at
    price ≤ entry_thr and its eventual outcome."""
    out: list[EntryRecord] = []
    n = len(prices)
    if n == 0:
        return out

    in_pos = False
    e_price = e_time = e_elapsed = e_period = None
    mae = mfe = None
    final_price = None

    for i in range(n):
        p = prices[i]
        if pd.isna(p):
            continue
        final_price = float(p)
        if not in_pos and p <= entry_thr:
            in_pos = True
            e_price = float(p)
            e_time = str(times[i])
            e_elapsed = float(elapsed[i])
            e_period = (
                int(periods[i]) if not pd.isna(periods[i]) else None
            )
            mae = float(p)
            mfe = float(p)
            continue
        if in_pos:
            mae = min(mae, float(p))
            mfe = max(mfe, float(p))
            if p >= exit_thr:
                hold = float(elapsed[i]) - e_elapsed
                if hold <= 0:
                    # intra-bucket move; skip
                    in_pos = False
                    continue
                exit_price = float(p)
                fee_in = maker_fee(CONTRACT_SIZE, e_price)
                fee_out = maker_fee(CONTRACT_SIZE, exit_price)
                gross = (exit_price - e_price) * CONTRACT_SIZE
                net = gross - fee_in - fee_out
                out.append(EntryRecord(
                    game_ticker=game_ticker, side=side,
                    entry_price=e_price, entry_time=e_time,
                    entry_game_seconds=e_elapsed,
                    entry_period=e_period,
                    outcome="completed",
                    exit_price=exit_price,
                    resolution_value=exit_price,
                    hold_time_sec=hold,
                    gross_pnl=gross, net_pnl=net,
                    max_adverse_excursion=mae,
                    max_favorable_excursion=mfe,
                    mae_pct=((e_price - mae) / e_price) if e_price > 0 else 0.0,
                    came_close=mfe >= (exit_thr - NEAR_MISS_PAD),
                    exit_period=(
                        int(periods[i]) if not pd.isna(periods[i]) else None
                    ),
                ))
                in_pos = False

    # Unclosed position at end of timeseries
    if in_pos and e_price is not None and final_price is not None:
        last_idx = n - 1
        # Walk backward for the last non-nan price (should already be final_price)
        resolution = (
            1.0 if final_price >= RESOLUTION_WIN_CUTOFF
            else 0.0 if final_price <= RESOLUTION_LOSS_CUTOFF
            else float(final_price)
        )
        if resolution == 1.0:
            outcome = "held_win"
        elif resolution == 0.0:
            outcome = "held_loss"
        else:
            outcome = "held_mid"
        # Fees: entry leg paid; exit leg only if not a self-settlement.
        # Per prompt spec: at resolution (1.00 or 0.00) no exit fee.
        # At mid-price termination (indeterminate), treat as market exit
        # with a maker fee.
        fee_in = maker_fee(CONTRACT_SIZE, e_price)
        if outcome == "held_mid":
            fee_out = maker_fee(CONTRACT_SIZE, resolution)
        else:
            fee_out = 0.0
        gross = (resolution - e_price) * CONTRACT_SIZE
        net = gross - fee_in - fee_out
        hold = float(elapsed[last_idx]) - e_elapsed
        out.append(EntryRecord(
            game_ticker=game_ticker, side=side,
            entry_price=e_price, entry_time=e_time,
            entry_game_seconds=e_elapsed,
            entry_period=e_period,
            outcome=outcome,
            exit_price=float(final_price),
            resolution_value=float(resolution),
            hold_time_sec=hold,
            gross_pnl=gross, net_pnl=net,
            max_adverse_excursion=mae,
            max_favorable_excursion=mfe,
            mae_pct=((e_price - mae) / e_price) if e_price > 0 else 0.0,
            came_close=mfe >= (exit_thr - NEAR_MISS_PAD),
            exit_period=(
                int(periods[last_idx]) if not pd.isna(periods[last_idx]) else None
            ),
        ))
    return out


# ---- Loading + metadata -------------------------------------------------

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


def load_timeseries(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        return df
    for c in ("game_seconds_elapsed", "period", "fav_kalshi_vwap"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["game_seconds_elapsed", "fav_kalshi_vwap"])
    return df.sort_values("game_seconds_elapsed").reset_index(drop=True)


# ---- Report helpers -----------------------------------------------------

def fmt_hold(seconds: float) -> str:
    if pd.isna(seconds) or seconds is None:
        return "—"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s"


def _mean(arr) -> float:
    return float(np.mean(arr)) if len(arr) else float("nan")


def _median(arr) -> float:
    return float(np.median(arr)) if len(arr) else float("nan")


def section_1_summary(
    md: list[str], entries: list[EntryRecord], n_games: int,
    entry_thr: float, exit_thr: float,
) -> None:
    md.append("## §1 — Sample summary\n")
    md.append(f"- Games analyzed: **{n_games}** competitive "
              f"(|spread| ≤ {MAX_SPREAD_COMPETITIVE:.0f})")
    md.append(
        f"- Entry threshold: **${entry_thr:.2f}** | "
        f"Exit threshold: **${exit_thr:.2f}**"
    )
    fav = sum(1 for e in entries if e.side == "fav")
    dog = sum(1 for e in entries if e.side == "dog")
    md.append(
        f"- Total entries detected: **{len(entries)}** "
        f"({fav} fav-side, {dog} dog-side)"
    )
    outcomes = {}
    for e in entries:
        outcomes[e.outcome] = outcomes.get(e.outcome, 0) + 1
    n = len(entries) or 1
    md.append(f"  - Completed round-trips: "
              f"{outcomes.get('completed', 0)} "
              f"({100 * outcomes.get('completed', 0) / n:.1f}%)")
    md.append(f"  - Held to win: "
              f"{outcomes.get('held_win', 0)} "
              f"({100 * outcomes.get('held_win', 0) / n:.1f}%)")
    md.append(f"  - Held to loss: "
              f"{outcomes.get('held_loss', 0)} "
              f"({100 * outcomes.get('held_loss', 0) / n:.1f}%)")
    md.append(f"  - Held indeterminate (timeseries ended mid-price): "
              f"{outcomes.get('held_mid', 0)} "
              f"({100 * outcomes.get('held_mid', 0) / n:.1f}%)")
    md.append("")


def section_2_breakdown(md: list[str], entries: list[EntryRecord]) -> None:
    md.append("## §2 — Success/failure breakdown\n")
    md.append("| Outcome | Count | % | Mean P&L | Median P&L |")
    md.append("|---|---:|---:|---:|---:|")
    n = len(entries) or 1
    for label, key in (
        ("Completed RT", "completed"),
        ("Held to win", "held_win"),
        ("Held to loss", "held_loss"),
        ("Held indeterminate", "held_mid"),
    ):
        sub = [e for e in entries if e.outcome == key]
        if not sub:
            md.append(f"| {label} | 0 | 0.0% | — | — |")
            continue
        pnls = [e.net_pnl for e in sub]
        md.append(
            f"| {label} | {len(sub)} | {100*len(sub)/n:.1f}% | "
            f"${_mean(pnls):+.2f} | ${_median(pnls):+.2f} |"
        )
    all_pnl = [e.net_pnl for e in entries]
    md.append(
        f"| **All entries** | **{len(entries)}** | 100.0% | "
        f"**${_mean(all_pnl):+.2f}** | **${_median(all_pnl):+.2f}** |"
    )
    md.append("")
    md.append(
        f"**True expected value per entry: ${_mean(all_pnl):+.2f}** "
        f"(accounts for all outcomes, weighted by observed frequency).\n"
    )


def section_3_ev(
    md: list[str], entries: list[EntryRecord], n_games: int,
    rt_per_game: float = 1.59, reg_season_games: int = 549,
) -> None:
    md.append("## §3 — True expected value per entry\n")
    md.append(f"If you enter at ≤ entry_threshold in a competitive game:\n")
    n = len(entries) or 1
    for label, key in (
        ("completing a round-trip", "completed"),
        ("holding to a win", "held_win"),
        ("holding to a loss", "held_loss"),
    ):
        sub = [e for e in entries if e.outcome == key]
        if not sub:
            continue
        pct = 100 * len(sub) / n
        mean_net = _mean([e.net_pnl for e in sub])
        md.append(f"- {pct:.1f}% chance of {label} → mean net ${mean_net:+.2f}")
    blended = _mean([e.net_pnl for e in entries])
    entries_per_game = len(entries) / n_games if n_games else 0.0
    md.append("")
    md.append(f"**Blended EV per entry: ${blended:+.2f}**")
    md.append(
        f"\nEntries per competitive game (observed): **{entries_per_game:.2f}**"
    )
    md.append(
        f"\nAt {entries_per_game:.2f} entries/game × "
        f"{reg_season_games} competitive games per season: "
        f"**~${blended * entries_per_game * reg_season_games:,.0f} "
        "estimated annual EV** (maker-maker, 100 contracts per entry)."
    )
    md.append("")


def section_4_failed_deep(md: list[str], entries: list[EntryRecord]) -> None:
    md.append("## §4 — Failed-entry deep dive\n")
    md.append("| Metric | Held to loss | Held to win |")
    md.append("|---|---|---|")
    loss = [e for e in entries if e.outcome == "held_loss"]
    win = [e for e in entries if e.outcome == "held_win"]

    def _fmt_price(arr):
        return f"${_mean(arr):.4f}" if arr else "—"

    def _fmt_pct(bools):
        if not bools:
            return "—"
        return f"{100 * np.mean(bools):.1f}%"

    md.append(
        f"| Count | {len(loss)} | {len(win)} |"
    )
    md.append(
        f"| Mean entry price | "
        f"{_fmt_price([e.entry_price for e in loss])} | "
        f"{_fmt_price([e.entry_price for e in win])} |"
    )
    md.append(
        f"| Mean max favorable excursion | "
        f"{_fmt_price([e.max_favorable_excursion for e in loss])} | "
        f"{_fmt_price([e.max_favorable_excursion for e in win])} |"
    )
    md.append(
        f"| Came close (MFE ≥ exit − $0.02) | "
        f"{_fmt_pct([e.came_close for e in loss])} | "
        f"{_fmt_pct([e.came_close for e in win])} |"
    )
    md.append(
        f"| Mean hold time to resolution | "
        f"{fmt_hold(_mean([e.hold_time_sec for e in loss])) if loss else '—'} | "
        f"{fmt_hold(_mean([e.hold_time_sec for e in win])) if win else '—'} |"
    )

    def _mean_period(sub):
        vals = [e.entry_period for e in sub if e.entry_period is not None]
        if not vals:
            return "—"
        return f"Q{_mean(vals):.1f}"

    md.append(
        f"| Mean entry period | "
        f"{_mean_period(loss)} | {_mean_period(win)} |"
    )
    md.append("")


def section_5_by_period(
    md: list[str], entries: list[EntryRecord],
) -> None:
    md.append("## §5 — Failed entries by entry period\n")
    md.append("| Entry period | Total entries | Failed (loss) | Fail rate |")
    md.append("|---|---:|---:|---:|")
    for p_label, pred in (
        ("Q1", lambda e: e.entry_period == 1),
        ("Q2", lambda e: e.entry_period == 2),
        ("Q3", lambda e: e.entry_period == 3),
        ("Q4", lambda e: e.entry_period == 4),
        ("OT", lambda e: e.entry_period is not None and e.entry_period >= 5),
    ):
        sub = [e for e in entries if pred(e)]
        failed = [e for e in sub if e.outcome == "held_loss"]
        if not sub:
            md.append(f"| {p_label} | 0 | 0 | — |")
            continue
        rate = 100 * len(failed) / len(sub)
        md.append(f"| {p_label} | {len(sub)} | {len(failed)} | {rate:.1f}% |")
    md.append("")


def section_6_by_spread(
    md: list[str], entries: list[EntryRecord],
) -> None:
    md.append("## §6 — Failed entries by spread bucket\n")
    md.append("| |Spread| bucket | Total entries | Failed (loss) | Fail rate |")
    md.append("|---|---:|---:|---:|")
    buckets = [
        ("1.0 - 2.0", lambda s: 1.0 <= s <= 2.0),
        ("2.5 - 3.5", lambda s: 2.5 <= s <= 3.5),
        ("4.0 - 5.0", lambda s: 4.0 <= s <= 5.0),
        ("5.5 - 6.0", lambda s: 5.5 <= s <= 6.0),
    ]
    for label, pred in buckets:
        sub = [
            e for e in entries
            if e.abs_spread is not None and pred(e.abs_spread)
        ]
        failed = [e for e in sub if e.outcome == "held_loss"]
        if not sub:
            md.append(f"| {label} | 0 | 0 | — |")
            continue
        rate = 100 * len(failed) / len(sub)
        md.append(f"| {label} | {len(sub)} | {len(failed)} | {rate:.1f}% |")
    md.append("")


def section_7_mae(md: list[str], entries: list[EntryRecord]) -> None:
    md.append("## §7 — Max adverse excursion distribution (all entries)\n")
    md.append("| MAE (% of entry price) | Count | % |")
    md.append("|---|---:|---:|")
    n = len(entries) or 1
    buckets = [
        ("0% (never went lower)", lambda pct: pct == 0),
        ("0-10%", lambda pct: 0 < pct <= 10),
        ("10-25%", lambda pct: 10 < pct <= 25),
        ("25-50%", lambda pct: 25 < pct <= 50),
        ("50-75%", lambda pct: 50 < pct <= 75),
        ("75-100%", lambda pct: pct > 75),
    ]
    for label, pred in buckets:
        count = sum(1 for e in entries if pred(e.mae_pct * 100))
        md.append(f"| {label} | {count} | {100*count/n:.1f}% |")
    md.append("")


def section_8_worst(md: list[str], entries: list[EntryRecord]) -> None:
    md.append("## §8 — Worst-case scenarios\n")
    md.append("### 10 worst individual entries\n")
    md.append(
        "| Game | Side | Entry | Q | MAE | Final | Net P&L |"
    )
    md.append("|---|---|---:|---:|---:|---:|---:|")
    worst = sorted(entries, key=lambda e: e.net_pnl)[:10]
    for e in worst:
        md.append(
            f"| {e.game_ticker} | {e.side} | "
            f"${e.entry_price:.4f} | {e.entry_period or '—'} | "
            f"${e.max_adverse_excursion:.4f} | "
            f"${e.exit_price:.4f} | ${e.net_pnl:+.2f} |"
        )
    md.append("")
    # Aggregate per game
    md.append("### 5 worst games (summed P&L across all entries)\n")
    md.append(
        "| Game | |Spread| | Entries | Completed | Failed | Game P&L |"
    )
    md.append("|---|---:|---:|---:|---:|---:|")
    by_game: dict[str, list[EntryRecord]] = {}
    for e in entries:
        by_game.setdefault(e.game_ticker, []).append(e)
    sums = []
    for g, lst in by_game.items():
        total = sum(e.net_pnl for e in lst)
        n_completed = sum(1 for e in lst if e.outcome == "completed")
        n_failed = sum(1 for e in lst if e.outcome in ("held_loss", "held_mid"))
        sp = lst[0].abs_spread
        sums.append((g, sp, len(lst), n_completed, n_failed, total))
    sums.sort(key=lambda r: r[-1])
    for g, sp, ne, nc, nf, total in sums[:5]:
        sp_s = f"{sp:.1f}" if sp is not None else "—"
        md.append(
            f"| {g} | {sp_s} | {ne} | {nc} | {nf} | ${total:+.2f} |"
        )
    md.append("")


def section_9_risk(md: list[str], entries: list[EntryRecord]) -> None:
    md.append("## §9 — Risk-adjusted summary\n")
    pnls = np.array([e.net_pnl for e in entries])
    if len(pnls) == 0:
        md.append("_No entries._\n")
        return
    mean_pnl = float(pnls.mean())
    std_pnl = float(pnls.std(ddof=1)) if len(pnls) > 1 else 0.0
    md.append("**Sharpe-like metric**")
    md.append(f"- Mean P&L per entry: ${mean_pnl:+.2f}")
    md.append(f"- Std P&L per entry: ${std_pnl:.2f}")
    if std_pnl > 0:
        md.append(f"- Ratio (mean / std): {mean_pnl / std_pnl:.3f}")
    md.append("")
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    n = len(pnls)
    win_rate = 100 * len(wins) / n
    loss_rate = 100 * len(losses) / n
    md.append("**Win / loss**")
    md.append(f"- Win rate (net > 0): {win_rate:.1f}%")
    md.append(f"- Loss rate (net < 0): {loss_rate:.1f}%")
    avg_win = float(wins.mean()) if len(wins) else float("nan")
    avg_loss = float(losses.mean()) if len(losses) else float("nan")
    md.append(f"- Mean winning entry: ${avg_win:+.2f}")
    md.append(f"- Mean losing entry: ${avg_loss:+.2f}")
    if len(wins) and len(losses) and avg_loss != 0:
        ratio = abs(avg_win / avg_loss)
        md.append(f"- Win/loss magnitude ratio: {ratio:.2f}×")
    md.append("")
    # Kelly approximation
    p = len(wins) / n
    q = 1 - p
    if len(wins) and len(losses) and abs(avg_loss) > 0:
        b = abs(avg_win / avg_loss)
        f_star = (p * b - q) / b if b > 0 else 0.0
        md.append("**Kelly criterion (approximate, for educational reference)**")
        md.append(
            f"- f* = (p·b − q) / b = "
            f"({p:.3f}·{b:.3f} − {q:.3f}) / {b:.3f} = **{f_star:.3f}**"
        )
        md.append(
            f"- At $1,000 bankroll: ${1000 * f_star:.2f} per entry"
        )
        md.append(
            f"- At ~$0.40 entry price, that's "
            f"{1000 * f_star / 0.40:.0f} contracts per entry — "
            f"{'but clamp to CONTRACT_SIZE=100 for consistency with the rest of the spec' if 1000 * f_star / 0.40 > 100 else 'within the 100-contract default'}."
        )
    md.append("")


# ---- Main ---------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metadata", type=str,
        default=str(PAIRED_DIR / "matched_games.csv"),
    )
    parser.add_argument("--entry", type=float, default=0.40)
    parser.add_argument("--exit", dest="exit_", type=float, default=0.50)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    meta_map = load_metadata(Path(args.metadata))
    log(f"Metadata loaded for {len(meta_map)} games")

    ts_files = sorted(PAIRED_DIR.glob("*_timeseries.csv"))
    log(f"Discovered {len(ts_files)} timeseries files")

    all_entries: list[EntryRecord] = []
    n_games = 0
    for p in ts_files:
        m = TICKER_RE.match(p.stem)
        if not m:
            continue
        ticker = m.group(1)
        meta = meta_map.get(ticker)
        abs_sp = meta["abs_spread"] if meta else None
        if abs_sp is None or abs_sp > MAX_SPREAD_COMPETITIVE:
            continue
        ts = load_timeseries(p)
        if ts.empty:
            continue
        n_games += 1
        fav = ts["fav_kalshi_vwap"].values.astype(float)
        dog = 1.0 - fav
        el = ts["game_seconds_elapsed"].values.astype(float)
        pr = ts["period"].values
        tm = ts["bucket_start_utc"].values
        for side, prices in (("fav", fav), ("dog", dog)):
            recs = detect_entries_one_side(
                ticker, side, prices, tm, el, pr,
                args.entry, args.exit_,
            )
            for r in recs:
                r.abs_spread = abs_sp
            all_entries.extend(recs)

    log(f"Competitive games evaluated: {n_games}")
    log(f"Total entries: {len(all_entries)}")

    # Write entry-level CSV
    PAIRED_DIR.mkdir(parents=True, exist_ok=True)
    if all_entries:
        pd.DataFrame([asdict(e) for e in all_entries]).to_csv(
            ENTRIES_CSV, index=False,
        )
        log(f"Entries CSV → {ENTRIES_CSV}")

    md: list[str] = []
    md.append("# Strategy 3 — Failed Entry & Worst-Case Analysis\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        "Complement to the graduation evaluation. Every entry event "
        f"at ≤ ${args.entry:.2f} is tracked through to its outcome: "
        f"completed round-trip at ≥ ${args.exit_:.2f}, held to win, "
        "held to loss, or held to indeterminate (timeseries ended "
        "mid-price). Produces the true expected value per entry.\n"
    )
    section_1_summary(md, all_entries, n_games, args.entry, args.exit_)
    section_2_breakdown(md, all_entries)
    section_3_ev(md, all_entries, n_games)
    section_4_failed_deep(md, all_entries)
    section_5_by_period(md, all_entries)
    section_6_by_spread(md, all_entries)
    section_7_mae(md, all_entries)
    section_8_worst(md, all_entries)
    section_9_risk(md, all_entries)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md) + "\n")
    log(f"Report → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
