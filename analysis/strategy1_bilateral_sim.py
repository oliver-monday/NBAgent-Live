"""Strategy 1 bilateral — operational live-engine simulation.

Simulates S1 bilateral position construction on the full 404-game
Kalshi paired dataset under realistic entry policies. Quantifies:
bilateral completion rates, interim exposure, stranded-leg outcomes
under multiple exit strategies, late-bilateral insurance value,
operational EV per (policy, threshold) pair, spread-bucket
breakdowns, and comparison to the prior `strategy1_recalibrated_bilateral.md`
estimate.

Data caveat: we have per-bin `fav_kalshi_vwap` from the paired
pipeline but not a separate `dog_kalshi_vwap`. The dog side's YES
bid is approximated as `1 - fav_kalshi_vwap`, which ignores the
Kalshi bid-ask spread (typically 1-2c). This means the simulated
bilateral cost is slightly optimistic; reported annual EV should
be read as an upper bound. See Section 7 caveat note.

Run:
    python -m analysis.strategy1_bilateral_sim
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.strategy4_dip_recovery import (
    COMP_FRACTION,
    REG_SEASON_GAMES,
    RESOLUTION_LOSS_CUTOFF,
    RESOLUTION_WIN_CUTOFF,
    fav_outcome,
    load_kalshi_games_all_spreads,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs" / "strategy1_bilateral_sim.md"
)

CONTRACTS = 100
BUCKET_SEC = 30

# Asymmetric threshold pairs (X = tight leg, Y = wide leg).
THRESHOLD_PAIRS: list[tuple[float, float]] = [
    (0.20, 0.20), (0.20, 0.25), (0.20, 0.30), (0.20, 0.35),
    (0.25, 0.25), (0.25, 0.30), (0.25, 0.35), (0.25, 0.40),
    (0.30, 0.30), (0.30, 0.35), (0.30, 0.40),
    (0.35, 0.35), (0.35, 0.40), (0.35, 0.45),
]

SPREAD_BUCKETS: list[tuple[str, float, float]] = [
    ("1.0-2.0", 1.0, 2.0),
    ("2.5-3.5", 2.5, 3.5),
    ("4.0-5.0", 4.0, 5.0),
    ("5.5-6.0", 5.5, 6.0),
    ("6.5-8.0", 6.5, 8.0),
    ("8.5-10.0", 8.5, 10.0),
    ("10.5+", 10.5, float("inf")),
]

POLICIES = ["A", "B", "C"]
POLICY_DESC = {
    "A": "Any observation ≤ Y (most aggressive, includes opening tick)",
    "B": "Downward crossing only (prior tick > Y, current ≤ Y)",
    "C": "Any observation ≤ Y with 10-tick (5-min) warmup",
}
WARMUP_TICKS_C = 10

# Abandonment exits (stranded-leg analysis)
ABANDON_MINUTES = [5, 10, 15, 20, 30]
ABANDON_TICKS = [m * 2 for m in ABANDON_MINUTES]  # 30s bins
PRICE_STOPS = [0.10, 0.15, 0.20]

# Game-count assumptions for annualization. Current scale matches
# strategy4_*'s convention so numbers are directly comparable.
ANNUAL_SCALE_GAMES = REG_SEASON_GAMES * COMP_FRACTION  # ~547

TARGET_DIFF_COLLAPSE = 0.70   # leg1-side bid at leg2 fill for Type 2


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


def kalshi_fee(contracts: int, price: float, maker: bool = True) -> float:
    if price <= 0 or price >= 1 or contracts <= 0:
        return 0.0
    rate = 0.0175 if maker else 0.07
    return math.ceil(rate * contracts * price * (1 - price) * 100) / 100


def bucket_for(abs_spread: float) -> str | None:
    for lab, lo, hi in SPREAD_BUCKETS:
        if lo <= abs_spread <= hi:
            return lab
    return None


# ---- Per-game extraction ----------------------------------------------

@dataclass
class GameCtx:
    ticker: str
    abs_spread: float
    winner: str                 # "fav" / "dog" / "unknown"
    fav_series: np.ndarray      # per-bin fav YES bid VWAP
    dog_series: np.ndarray      # 1 - fav_series (approximation)
    n_ticks: int


def prepare_games(games: list[dict]) -> list[GameCtx]:
    out: list[GameCtx] = []
    skipped = 0
    for g in games:
        outcome = fav_outcome(g["ts"])
        if outcome == "unknown":
            skipped += 1
            continue
        fav = g["ts"]["fav_kalshi_vwap"].values.astype(float)
        if len(fav) < 2:
            skipped += 1
            continue
        dog = 1.0 - fav
        out.append(GameCtx(
            ticker=g["ticker"], abs_spread=float(g["abs_spread"]),
            winner="fav" if outcome == "win" else "dog",
            fav_series=fav, dog_series=dog, n_ticks=len(fav),
        ))
    if skipped:
        log(
            f"  skipped {skipped} games with unresolved outcome "
            "(final VWAP not within [0, 0.05] ∪ [0.95, 1])"
        )
    return out


# ---- Section 1: Theoretical bilateral census --------------------------

def theoretical_bilateral(
    ctx: GameCtx, x: float, y: float,
) -> bool:
    """Does this game allow a bilateral at (X, Y)? One side dips ≤ X
    and the other side dips ≤ Y (either assignment)."""
    min_fav = float(ctx.fav_series.min())
    min_dog = float(ctx.dog_series.min())
    deeper = min(min_fav, min_dog)
    shallower = max(min_fav, min_dog)
    return deeper <= x and shallower <= y


def section1_census(
    ctxs: list[GameCtx],
) -> list[dict]:
    rows: list[dict] = []
    total_games = len(ctxs)
    for x, y in THRESHOLD_PAIRS:
        all_rate = sum(
            1 for c in ctxs if theoretical_bilateral(c, x, y)
        )
        bucket_rates: dict[str, tuple[int, int]] = {}
        for lab, lo, hi in SPREAD_BUCKETS:
            subset = [c for c in ctxs if lo <= c.abs_spread <= hi]
            fires = sum(
                1 for c in subset if theoretical_bilateral(c, x, y)
            )
            bucket_rates[lab] = (fires, len(subset))
        rows.append({
            "x": x, "y": y,
            "theoretical_fires": all_rate,
            "total_games": total_games,
            "rate": all_rate / total_games if total_games else 0.0,
            "by_bucket": bucket_rates,
        })
    return rows


# ---- Section 2: Entry policy simulation -------------------------------

@dataclass
class BilatEntry:
    game_ticker: str
    abs_spread: float
    winner: str
    leg1_side: str                   # "fav" / "dog"
    leg1_price: float
    leg1_tick: int
    leg2_filled: bool
    leg2_price: float | None
    leg2_tick: int | None
    interim_ticks: int | None
    # For stranded exit simulations, store leg1's bid trajectory from
    # leg1_tick onward (small — avg few hundred floats per entry).
    leg1_bid_after_entry: np.ndarray = field(
        default_factory=lambda: np.array([], dtype=float),
    )
    # Leg1-side bid at leg2 fill time (for Type 2 collapse classification)
    leg1_bid_at_leg2: float | None = None


def _leg1_entry_tick(
    primary: np.ndarray, secondary: np.ndarray,
    y: float, policy: str, warmup: int,
) -> tuple[int | None, str]:
    """Find the tick where leg 1 fires. Returns (tick, leg1_side).

    Both sides are evaluated simultaneously. Whichever dips ≤ Y first
    under the policy is leg 1. If neither dips by game end, returns
    (None, "").
    """
    n = len(primary)
    if policy == "A":
        start = 0
    elif policy == "B":
        start = 1
    elif policy == "C":
        start = warmup
    else:
        raise ValueError(f"Unknown policy {policy}")

    for i in range(start, n):
        fav_i = primary[i]
        dog_i = secondary[i]
        if policy == "B":
            fav_prev = primary[i - 1]
            dog_prev = secondary[i - 1]
            fav_fires = fav_prev > y and fav_i <= y
            dog_fires = dog_prev > y and dog_i <= y
        else:
            fav_fires = fav_i <= y
            dog_fires = dog_i <= y
        if fav_fires and dog_fires:
            # Both sides fire at the same tick — pick the one with the
            # LOWER price at this moment (better fill, and "first-to-
            # threshold" is ambiguous so use price as tiebreak).
            return i, ("fav" if fav_i <= dog_i else "dog")
        if fav_fires:
            return i, "fav"
        if dog_fires:
            return i, "dog"
    return None, ""


def simulate_policy(
    ctxs: list[GameCtx], policy: str, x: float, y: float,
) -> list[BilatEntry]:
    """Run one (policy, X, Y) combo across all games."""
    entries: list[BilatEntry] = []
    for ctx in ctxs:
        # Primary = fav series, secondary = dog series. The side labels
        # are "fav" and "dog"; we watch both under the policy.
        tick, side = _leg1_entry_tick(
            ctx.fav_series, ctx.dog_series, y, policy, WARMUP_TICKS_C,
        )
        if tick is None:
            continue

        if side == "fav":
            leg1_series = ctx.fav_series
            leg2_series = ctx.dog_series
        else:
            leg1_series = ctx.dog_series
            leg2_series = ctx.fav_series

        leg1_price = float(leg1_series[tick])
        # Leg 2: scan from tick+1 for leg2_series ≤ X.
        leg2_filled = False
        leg2_price: float | None = None
        leg2_tick_val: int | None = None
        interim: int | None = None
        leg1_bid_at_leg2: float | None = None
        for j in range(tick + 1, ctx.n_ticks):
            if leg2_series[j] <= x:
                leg2_filled = True
                leg2_price = float(leg2_series[j])
                leg2_tick_val = j
                interim = j - tick
                leg1_bid_at_leg2 = float(leg1_series[j])
                break

        bid_after = leg1_series[tick:].copy()
        entries.append(BilatEntry(
            game_ticker=ctx.ticker, abs_spread=ctx.abs_spread,
            winner=ctx.winner, leg1_side=side,
            leg1_price=leg1_price, leg1_tick=tick,
            leg2_filled=leg2_filled, leg2_price=leg2_price,
            leg2_tick=leg2_tick_val, interim_ticks=interim,
            leg1_bid_after_entry=bid_after,
            leg1_bid_at_leg2=leg1_bid_at_leg2,
        ))
    return entries


# ---- P&L helpers ------------------------------------------------------

def bilateral_pnl(e: BilatEntry) -> float:
    """P&L for a completed bilateral.

    Payout is exactly $1.00 regardless of winner (YES on each side,
    one settles $1 + the other $0). Cost = leg1 + leg2 + fees both
    legs (maker)."""
    assert e.leg2_filled and e.leg2_price is not None
    cost = (e.leg1_price + e.leg2_price) * CONTRACTS
    fee1 = kalshi_fee(CONTRACTS, e.leg1_price, maker=True)
    fee2 = kalshi_fee(CONTRACTS, e.leg2_price, maker=True)
    return (1.0 * CONTRACTS) - cost - fee1 - fee2


def stranded_resolution_pnl(e: BilatEntry) -> float:
    """Hold to resolution: leg1_side wins → $1.00 payout; loses → $0."""
    entry_fee = kalshi_fee(CONTRACTS, e.leg1_price, maker=True)
    payoff = 1.0 if e.leg1_side == e.winner else 0.0
    # No exit fee — resolution settles directly.
    return (payoff - e.leg1_price) * CONTRACTS - entry_fee


def stranded_time_abandon_pnl(
    e: BilatEntry, abandon_ticks: int, winner: str,
) -> float:
    """Time-based abandonment: sell at market after `abandon_ticks`
    from leg1 entry. If the timeout hasn't arrived by game end, treat
    as hold-to-resolution."""
    entry_fee = kalshi_fee(CONTRACTS, e.leg1_price, maker=True)
    n = len(e.leg1_bid_after_entry)
    if abandon_ticks >= n:
        # Timeout past end of game — resolution
        payoff = 1.0 if e.leg1_side == winner else 0.0
        return (payoff - e.leg1_price) * CONTRACTS - entry_fee
    exit_price = float(e.leg1_bid_after_entry[abandon_ticks])
    exit_fee = kalshi_fee(CONTRACTS, exit_price, maker=False)
    return (exit_price - e.leg1_price) * CONTRACTS - entry_fee - exit_fee


def stranded_price_stop_pnl(
    e: BilatEntry, stop_price: float, winner: str,
) -> float:
    """Price stop: sell at market when leg1_side bid first drops
    below stop_price. If it never drops, hold to resolution."""
    entry_fee = kalshi_fee(CONTRACTS, e.leg1_price, maker=True)
    arr = e.leg1_bid_after_entry
    # Skip the entry tick itself (arr[0] == leg1_price by construction).
    for k in range(1, len(arr)):
        if arr[k] <= stop_price:
            exit_price = float(arr[k])
            exit_fee = kalshi_fee(CONTRACTS, exit_price, maker=False)
            return (exit_price - e.leg1_price) * CONTRACTS - entry_fee - exit_fee
    # Never stopped out; hold to resolution
    payoff = 1.0 if e.leg1_side == winner else 0.0
    return (payoff - e.leg1_price) * CONTRACTS - entry_fee


# ---- Section 3/4 aggregators -----------------------------------------

@dataclass
class StrandedStats:
    exit_strategy: str
    n: int
    mean_pnl: float
    median_pnl: float
    total_pnl: float
    win_rate: float             # for Strategy H: resolution wins


def compute_stranded_stats(
    stranded: list[BilatEntry],
) -> dict[str, StrandedStats]:
    """Compute stats for each exit strategy on the stranded subset."""
    out: dict[str, StrandedStats] = {}
    if not stranded:
        return out

    # Strategy H: hold to resolution
    pnls_H = [stranded_resolution_pnl(e) for e in stranded]
    wins_H = sum(1 for e in stranded if e.leg1_side == e.winner)
    out["H"] = StrandedStats(
        exit_strategy="H (hold to resolution)",
        n=len(stranded),
        mean_pnl=float(np.mean(pnls_H)),
        median_pnl=float(np.median(pnls_H)),
        total_pnl=float(np.sum(pnls_H)),
        win_rate=wins_H / len(stranded) if stranded else 0.0,
    )

    # Strategy T at each abandonment tick
    for mins, ticks in zip(ABANDON_MINUTES, ABANDON_TICKS):
        pnls = [
            stranded_time_abandon_pnl(e, ticks, e.winner)
            for e in stranded
        ]
        key = f"T{mins}"
        out[key] = StrandedStats(
            exit_strategy=f"T{mins} (abandon at {mins} min / {ticks} ticks)",
            n=len(stranded),
            mean_pnl=float(np.mean(pnls)),
            median_pnl=float(np.median(pnls)),
            total_pnl=float(np.sum(pnls)),
            win_rate=0.0,
        )

    # Strategy P at each stop price
    for sp in PRICE_STOPS:
        pnls = [
            stranded_price_stop_pnl(e, sp, e.winner) for e in stranded
        ]
        key = f"P{int(sp * 100):02d}"
        out[key] = StrandedStats(
            exit_strategy=f"P{int(sp * 100):02d} (stop at ${sp:.2f})",
            n=len(stranded),
            mean_pnl=float(np.mean(pnls)),
            median_pnl=float(np.median(pnls)),
            total_pnl=float(np.sum(pnls)),
            win_rate=0.0,
        )

    return out


def best_stranded_strategy(
    stats: dict[str, StrandedStats],
) -> tuple[str, StrandedStats] | None:
    if not stats:
        return None
    return max(stats.items(), key=lambda kv: kv[1].mean_pnl)


# ---- Section 4: Late-bilateral insurance analysis --------------------

@dataclass
class InsuranceStats:
    n_total_bilats: int
    n_type1: int                # "natural"
    n_type2: int                # "collapse"
    mean_insurance_value: float
    n_saved: int                # type 2 where leg1 actually lost


def compute_insurance(
    bilats: list[BilatEntry],
) -> InsuranceStats:
    if not bilats:
        return InsuranceStats(0, 0, 0, 0.0, 0)
    n1 = n2 = saved = 0
    ins_vals: list[float] = []
    for e in bilats:
        assert e.leg1_bid_at_leg2 is not None
        if e.leg1_bid_at_leg2 >= TARGET_DIFF_COLLAPSE:
            n2 += 1
            b_pnl = bilateral_pnl(e)
            # Counterfactual: if we hadn't bought leg 2, we'd hold leg 1
            # to resolution. Realized: 1.0 if leg1 wins, 0.0 if loses.
            leg1_entry_fee = kalshi_fee(
                CONTRACTS, e.leg1_price, maker=True,
            )
            realized_cf_payoff = 1.0 if e.leg1_side == e.winner else 0.0
            realized_cf = (
                (realized_cf_payoff - e.leg1_price) * CONTRACTS
                - leg1_entry_fee
            )
            ins_vals.append(b_pnl - realized_cf)
            # "Saved" means leg 1 actually lost (insurance paid off)
            if e.leg1_side != e.winner:
                saved += 1
        else:
            n1 += 1
    return InsuranceStats(
        n_total_bilats=len(bilats),
        n_type1=n1, n_type2=n2,
        mean_insurance_value=(
            float(np.mean(ins_vals)) if ins_vals else 0.0
        ),
        n_saved=saved,
    )


# ---- Section 5: Operational EV rollup --------------------------------

@dataclass
class OpPointResult:
    policy: str
    x: float
    y: float
    best_stranded_key: str
    n_games: int
    n_entries: int
    n_bilats: int
    n_stranded: int
    bilat_total_pnl: float
    stranded_total_pnl: float
    net_total_pnl: float
    ev_per_game: float
    annual_ev: float


def ev_rollup(
    ctxs: list[GameCtx], policy: str, x: float, y: float,
    bilat_entries: list[BilatEntry] | None = None,
) -> OpPointResult:
    if bilat_entries is None:
        bilat_entries = simulate_policy(ctxs, policy, x, y)
    bilats = [e for e in bilat_entries if e.leg2_filled]
    stranded = [e for e in bilat_entries if not e.leg2_filled]
    bilat_pnls = [bilateral_pnl(e) for e in bilats]
    bilat_total = float(np.sum(bilat_pnls)) if bilat_pnls else 0.0
    stats = compute_stranded_stats(stranded)
    best = best_stranded_strategy(stats)
    if best is None:
        best_key = "—"
        strand_total = 0.0
    else:
        best_key, best_stats = best
        strand_total = best_stats.total_pnl
    n_games = len(ctxs)
    net_total = bilat_total + strand_total
    ev_per_game = net_total / n_games if n_games else 0.0
    annual_ev = ev_per_game * ANNUAL_SCALE_GAMES
    return OpPointResult(
        policy=policy, x=x, y=y, best_stranded_key=best_key,
        n_games=n_games, n_entries=len(bilat_entries),
        n_bilats=len(bilats), n_stranded=len(stranded),
        bilat_total_pnl=bilat_total,
        stranded_total_pnl=strand_total,
        net_total_pnl=net_total,
        ev_per_game=ev_per_game, annual_ev=annual_ev,
    )


# ---- Section 6: Spread bucket breakdown ------------------------------

def bucket_rollup(
    ctxs: list[GameCtx], policy: str, x: float, y: float,
) -> dict[str, dict]:
    """Per-bucket entries, bilats, stranded, EV for one op point."""
    ctxs_by_bucket: dict[str, list[GameCtx]] = {
        lab: [] for lab, _, _ in SPREAD_BUCKETS
    }
    for c in ctxs:
        lab = bucket_for(c.abs_spread)
        if lab is not None:
            ctxs_by_bucket[lab].append(c)
    all_entries = simulate_policy(ctxs, policy, x, y)
    entries_by_bucket: dict[str, list[BilatEntry]] = {
        lab: [] for lab, _, _ in SPREAD_BUCKETS
    }
    ctx_bucket = {c.ticker: bucket_for(c.abs_spread) for c in ctxs}
    for e in all_entries:
        lab = ctx_bucket.get(e.game_ticker)
        if lab is not None:
            entries_by_bucket[lab].append(e)

    out: dict[str, dict] = {}
    for lab, _, _ in SPREAD_BUCKETS:
        bucket_ctxs = ctxs_by_bucket[lab]
        if not bucket_ctxs:
            out[lab] = {
                "n_games": 0, "n_entries": 0,
                "n_bilats": 0, "n_stranded": 0,
                "ev_per_game": 0.0, "annual_ev": 0.0,
            }
            continue
        entries = entries_by_bucket[lab]
        res = ev_rollup(
            bucket_ctxs, policy, x, y, bilat_entries=entries,
        )
        out[lab] = {
            "n_games": res.n_games, "n_entries": res.n_entries,
            "n_bilats": res.n_bilats, "n_stranded": res.n_stranded,
            "ev_per_game": res.ev_per_game,
            "annual_ev": res.annual_ev,
            "best_stranded_key": res.best_stranded_key,
        }
    return out


# ---- Report rendering ------------------------------------------------

def render_report(
    ctxs: list[GameCtx],
    section1_rows: list[dict],
    section2_rows: list[dict],
    section3_best: list[dict],
    section4_rows: list[dict],
    section5_rows: list[OpPointResult],
    section6: dict[str, dict[str, dict]],
    top_points: list[OpPointResult],
) -> str:
    md: list[str] = []
    md.append("# Strategy 1 — Bilateral Operational Simulation\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Simulates S1 bilateral position construction on "
        f"**{len(ctxs)} games** from the Kalshi-confirmed paired "
        "dataset (resolvable outcome, all spreads). Three entry "
        "policies × 14 threshold pairs × per-game tick replay. "
        "Stranded-leg outcomes computed under hold-to-resolution, "
        "time-based abandonment (5-30 min), and price-based stops "
        "($0.10-$0.20).\n"
    )
    md.append(
        "\n**Data approximation:** `dog_kalshi_vwap` is computed as "
        "`1 - fav_kalshi_vwap` because the paired pipeline only "
        "emits the favorite-side VWAP. Kalshi bid-ask spread is "
        "typically 1-2c, so actual dog-side bids are slightly "
        "**below** `1 - fav_vwap`. Simulated bilateral cost is "
        "therefore slightly optimistic; real fills will be "
        "marginally worse. Directional findings are robust; absolute "
        "EV should be read as an upper bound.\n"
    )

    # ---- Section 1 ----------------------------------------------------
    md.append(
        "\n## Section 1 — Theoretical bilateral census\n"
    )
    md.append(
        "For each (X, Y) pair, a game is a theoretical bilateral "
        "if one side's YES bid touched ≤ X and the other side's "
        "touched ≤ Y (any order, any timing). This reproduces the "
        "offline 'both sides dip at any point' rate — live engines "
        "can do at most this well.\n\n"
        "| (X, Y) | Games | Theor. rate | 1-2 | 2.5-3.5 | 4-5 | 5.5-6 | 6.5-8 | 8.5-10 | 10.5+ |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for r in section1_rows:
        by_bucket = r["by_bucket"]
        md.append(
            f"| ({r['x']:.2f}, {r['y']:.2f}) | "
            f"{r['total_games']} | "
            f"{r['theoretical_fires']} / {100 * r['rate']:.1f}% |"
        )
        for lab, _, _ in SPREAD_BUCKETS:
            fires, total = by_bucket[lab]
            if total == 0:
                md.append(" — |")
            else:
                md.append(
                    f" {fires}/{total} ({100 * fires / total:.0f}%) |"
                )
        md.append("\n")

    # ---- Section 2 ----------------------------------------------------
    md.append(
        "\n## Section 2 — Entry policy simulation\n"
    )
    md.append("**Policies tested:**\n\n")
    for p in POLICIES:
        md.append(f"- **Policy {p}** — {POLICY_DESC[p]}\n")
    md.append(
        "\n| Policy | (X, Y) | Games w/ leg1 | Bilat complete | Complete % | Stranded | Stranded % |\n"
        "|---|---|---:|---:|---:|---:|---:|\n"
    )
    for r in section2_rows:
        total = r["entries"]
        if total == 0:
            pct_complete = pct_stranded = 0.0
        else:
            pct_complete = 100 * r["n_bilats"] / total
            pct_stranded = 100 * r["n_stranded"] / total
        md.append(
            f"| {r['policy']} | "
            f"({r['x']:.2f}, {r['y']:.2f}) | "
            f"{r['entries']} | {r['n_bilats']} | "
            f"{pct_complete:.1f}% | {r['n_stranded']} | "
            f"{pct_stranded:.1f}% |\n"
        )

    # ---- Section 3 ----------------------------------------------------
    md.append(
        "\n## Section 3 — Stranded-leg analysis (best op point per policy × threshold)\n"
    )
    md.append(
        "For each (policy, threshold pair), stranded-leg outcomes under "
        "hold-to-resolution (H), time-based abandonment (T5-T30), and "
        "price-based stops (P10/P15/P20). Table below shows the "
        "BEST exit strategy per op point.\n\n"
        "| Policy | (X, Y) | Stranded n | Best exit | Mean P&L | Median P&L | Total P&L |\n"
        "|---|---|---:|---|---:|---:|---:|\n"
    )
    for r in section3_best:
        if r["n_stranded"] == 0:
            md.append(
                f"| {r['policy']} | ({r['x']:.2f}, {r['y']:.2f}) | "
                f"0 | n/a | n/a | n/a | n/a |\n"
            )
            continue
        md.append(
            f"| {r['policy']} | ({r['x']:.2f}, {r['y']:.2f}) | "
            f"{r['n_stranded']} | {r['best_exit']} | "
            f"${r['mean_pnl']:+.2f} | ${r['median_pnl']:+.2f} | "
            f"${r['total_pnl']:+,.2f} |\n"
        )

    # ---- Section 4 ----------------------------------------------------
    md.append(
        "\n## Section 4 — Late-bilateral insurance analysis\n"
    )
    md.append(
        "For completed bilaterals, classify by leg-1-side bid at the "
        "moment leg 2 fills. **Type 1 (natural):** leg1 bid < "
        f"${TARGET_DIFF_COLLAPSE:.2f} at leg 2 — game still in doubt. "
        "**Type 2 (collapse insurance):** leg1 bid ≥ "
        f"${TARGET_DIFF_COLLAPSE:.2f} — leg 2 is being bought during "
        "the opposite side's collapse. 'Saved' = Type 2 where leg 1 "
        "ended up losing (insurance paid off).\n\n"
        "| Policy | (X, Y) | Total bilats | Type 1 | Type 2 | Mean insurance value | Saved |\n"
        "|---|---|---:|---:|---:|---:|---:|\n"
    )
    for r in section4_rows:
        md.append(
            f"| {r['policy']} | ({r['x']:.2f}, {r['y']:.2f}) | "
            f"{r['n_total']} | {r['n_type1']} | {r['n_type2']} | "
            f"${r['mean_insurance']:+.2f} | {r['n_saved']} |\n"
        )

    # ---- Section 5 ----------------------------------------------------
    md.append(
        "\n## Section 5 — Operational EV rollup (sorted by annual EV)\n"
    )
    md.append(
        "Per op point: completed bilaterals at bilateral P&L + "
        "stranded positions at BEST exit strategy. Games with no "
        f"entry contribute $0. Annual EV = EV/game × "
        f"{ANNUAL_SCALE_GAMES:.0f} (competitive-rate scaling, "
        "consistent with `strategy4_dip_recovery.py`).\n\n"
        "| Policy | (X, Y) | Entries | Bilat | Strand | Bilat $ | Strand $ | EV/game | Annual EV | Best strand |\n"
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n"
    )
    sorted_section5 = sorted(
        section5_rows, key=lambda r: -r.annual_ev,
    )
    for r in sorted_section5:
        md.append(
            f"| {r.policy} | ({r.x:.2f}, {r.y:.2f}) | "
            f"{r.n_entries} | {r.n_bilats} | {r.n_stranded} | "
            f"${r.bilat_total_pnl:+,.0f} | "
            f"${r.stranded_total_pnl:+,.0f} | "
            f"${r.ev_per_game:+,.2f} | "
            f"${r.annual_ev:+,.0f} | "
            f"{r.best_stranded_key} |\n"
        )
    best_op = sorted_section5[0]
    md.append(
        f"\n**Recommended operating point:** "
        f"Policy {best_op.policy} at "
        f"(X={best_op.x:.2f}, Y={best_op.y:.2f}) with stranded "
        f"exit strategy **{best_op.best_stranded_key}**. "
        f"Annual EV: **${best_op.annual_ev:+,.0f}** "
        f"({best_op.n_bilats} bilats / {best_op.n_stranded} stranded "
        f"per {best_op.n_games} games).\n"
    )

    # ---- Section 6 ----------------------------------------------------
    md.append(
        "\n## Section 6 — Spread-bucket breakdown (top 3 op points)\n"
    )
    for i, op in enumerate(top_points, 1):
        md.append(
            f"\n### Top {i}: Policy {op.policy} "
            f"({op.x:.2f}, {op.y:.2f}) — "
            f"stranded exit {op.best_stranded_key}\n\n"
            "| |Spread| | Games | Entries | Bilat | Strand | EV/game | Annual EV |\n"
            "|---|---:|---:|---:|---:|---:|---:|\n"
        )
        buckets = section6.get((op.policy, op.x, op.y))
        if buckets is None:
            continue
        for lab, _, _ in SPREAD_BUCKETS:
            b = buckets[lab]
            md.append(
                f"| {lab} | {b['n_games']} | {b['n_entries']} | "
                f"{b['n_bilats']} | {b['n_stranded']} | "
                f"${b['ev_per_game']:+,.2f} | "
                f"${b['annual_ev']:+,.0f} |\n"
            )

    # ---- Section 7 ----------------------------------------------------
    md.append(
        "\n## Section 7 — Comparison to prior estimate\n"
    )
    md.append(
        "The prior `strategy1_recalibrated_bilateral.md` estimate "
        "assumed perfect bilateral capture (if both sides dip at any "
        "point, you catch both). This analysis captures live-engine "
        "reality: entry timing policy + stranded risk.\n\n"
    )
    # Compute metrics for recommended op point to compare
    rec = best_op
    mean_per_bilat = (
        rec.bilat_total_pnl / rec.n_bilats if rec.n_bilats else 0.0
    )
    rec_ctxs = len(ctxs)
    completion_rate = (
        100 * rec.n_bilats / rec_ctxs if rec_ctxs else 0.0
    )
    mean_stranded = (
        rec.stranded_total_pnl / rec.n_stranded
        if rec.n_stranded else 0.0
    )
    md.append(
        "| Metric | Prior estimate | This analysis |\n"
        "|---|---|---|\n"
        f"| Threshold pair (X, Y) | (0.25, 0.35) | "
        f"({rec.x:.2f}, {rec.y:.2f}) |\n"
        f"| Entry policy | perfect capture | Policy {rec.policy} "
        f"({POLICY_DESC[rec.policy]}) |\n"
        f"| Opportunity / completion rate | 17.7% | "
        f"{completion_rate:.1f}% |\n"
        f"| Net per completed bilateral | $37.08 | "
        f"${mean_per_bilat:+.2f} |\n"
        f"| Stranded position cost | not modeled | "
        f"${mean_stranded:+.2f} mean ({rec.n_stranded} cases, "
        f"best exit: {rec.best_stranded_key}) |\n"
        f"| EV/game | $6.55 | ${rec.ev_per_game:+,.2f} |\n"
        f"| Annual EV | $1,608 | ${rec.annual_ev:+,.0f} |\n"
    )
    md.append(
        "\n**Interpretation.** The prior estimate's $1,608/yr "
        "assumed perfect bilateral capture and did not price "
        "stranded risk. The live-engine simulation's headline "
        f"(${rec.annual_ev:+,.0f}/yr at the recommended op point) "
        "is the operationally realistic number — it reflects "
        "what a tick-by-tick engine running the indicated policy "
        "can actually earn given the real dip-timing distribution "
        "and resolvable-outcome subset. Whether to build the S1 "
        "engine module is a judgment on the delta vs development "
        "cost, and on whether the mean-insurance-value finding "
        "from Section 4 argues for or against late-bilateral "
        "construction as a deliberate subpattern.\n"
    )
    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading Kalshi paired dataset (all spreads)...")
    games = load_kalshi_games_all_spreads()
    log(f"  {len(games)} games loaded")
    ctxs = prepare_games(games)
    log(f"  {len(ctxs)} games with resolvable outcome")

    # Section 1
    log("Section 1: theoretical bilateral census...")
    section1_rows = section1_census(ctxs)

    # Sections 2-5: simulate every policy × threshold pair
    log(
        f"Sections 2-5: simulating {len(POLICIES)} × "
        f"{len(THRESHOLD_PAIRS)} = "
        f"{len(POLICIES) * len(THRESHOLD_PAIRS)} op points..."
    )
    section2_rows: list[dict] = []
    section3_best: list[dict] = []
    section4_rows: list[dict] = []
    section5_rows: list[OpPointResult] = []

    all_entries_cache: dict[tuple[str, float, float], list[BilatEntry]] = {}
    for policy in POLICIES:
        for x, y in THRESHOLD_PAIRS:
            entries = simulate_policy(ctxs, policy, x, y)
            all_entries_cache[(policy, x, y)] = entries
            bilats = [e for e in entries if e.leg2_filled]
            stranded = [e for e in entries if not e.leg2_filled]
            section2_rows.append({
                "policy": policy, "x": x, "y": y,
                "entries": len(entries), "n_bilats": len(bilats),
                "n_stranded": len(stranded),
            })
            # Stranded best exit
            stats = compute_stranded_stats(stranded)
            best = best_stranded_strategy(stats)
            if best is None:
                section3_best.append({
                    "policy": policy, "x": x, "y": y,
                    "n_stranded": 0, "best_exit": "—",
                    "mean_pnl": 0.0, "median_pnl": 0.0,
                    "total_pnl": 0.0,
                })
            else:
                key, st = best
                section3_best.append({
                    "policy": policy, "x": x, "y": y,
                    "n_stranded": st.n,
                    "best_exit": st.exit_strategy,
                    "mean_pnl": st.mean_pnl,
                    "median_pnl": st.median_pnl,
                    "total_pnl": st.total_pnl,
                })
            # Insurance analysis
            ins = compute_insurance(bilats)
            section4_rows.append({
                "policy": policy, "x": x, "y": y,
                "n_total": ins.n_total_bilats,
                "n_type1": ins.n_type1, "n_type2": ins.n_type2,
                "mean_insurance": ins.mean_insurance_value,
                "n_saved": ins.n_saved,
            })
            # EV rollup
            res = ev_rollup(ctxs, policy, x, y, bilat_entries=entries)
            section5_rows.append(res)

    # Section 6: top-3 op points, bucket breakdown
    log("Section 6: bucket breakdowns for top 3 op points...")
    sorted_section5 = sorted(
        section5_rows, key=lambda r: -r.annual_ev,
    )
    top_points = sorted_section5[:3]
    section6: dict[tuple, dict[str, dict]] = {}
    for op in top_points:
        key = (op.policy, op.x, op.y)
        section6[key] = bucket_rollup(ctxs, op.policy, op.x, op.y)

    log("Rendering report...")
    md = render_report(
        ctxs=ctxs, section1_rows=section1_rows,
        section2_rows=section2_rows, section3_best=section3_best,
        section4_rows=section4_rows,
        section5_rows=section5_rows, section6=section6,
        top_points=top_points,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
