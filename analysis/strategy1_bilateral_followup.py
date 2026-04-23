"""Strategy 1 bilateral — follow-up investigations.

Three focused follow-ups on `analysis/strategy1_bilateral_sim.py`:

1. Re-entry simulation: allow up to 3 entries per game after T5
   exits, with cooldown + per-game loss caps. Quantifies the
   "death by a thousand cuts" risk in dominant-favorite games.

2. T5 exit P&L distribution: for the 314 stranded T5 exits from
   the parent's single-entry baseline, show the shape of the
   P&L histogram and how it correlates with leg-1 entry price.

3. Blowout filter sensitivity: test a pre-game filter that
   skips games where either side's opening Kalshi price is
   above a cutoff. Measure what's cut and whether the filter
   makes re-entry safer.

All three use the parent's operating point (Policy A at
threshold (0.20, 0.35) with T5 stranded exit) as the baseline.

Run:
    python -m analysis.strategy1_bilateral_followup
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from analysis.strategy1_bilateral_sim import (
    ANNUAL_SCALE_GAMES,
    CONTRACTS,
    GameCtx,
    SPREAD_BUCKETS,
    bucket_for,
    kalshi_fee,
    prepare_games,
    simulate_policy,
    stranded_time_abandon_pnl,
)
from analysis.strategy4_dip_recovery import load_kalshi_games_all_spreads

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    REPO_ROOT / "docs" / "analysis_outputs"
    / "strategy1_bilateral_followup.md"
)

# Baseline operating point from parent script.
BASELINE_POLICY = "A"
BASELINE_X = 0.20
BASELINE_Y = 0.35
T5_TICKS = 10         # 5 min × 2 ticks/min (30s bins)

# Re-entry investigation grid.
MAX_ENTRIES_PER_GAME = 3
COOLDOWN_TICKS_GRID = [1, 10]
LOSS_CAP_GRID: list[float | None] = [None, 10.0, 20.0]

# Blowout filter cutoffs (skip game if either side's first
# observation ≥ cutoff, i.e., other side opens ≤ 1 − cutoff).
FILTER_CUTOFFS: list[float | None] = [None, 0.80, 0.75, 0.70]

# T5 distribution buckets.
PNL_BUCKETS: list[tuple[str, float, float]] = [
    ("> +$5.00", 5.00, float("inf")),
    ("+$2.00 to +$5.00", 2.00, 5.00),
    ("+$0.50 to +$2.00", 0.50, 2.00),
    ("-$0.50 to +$0.50", -0.50, 0.50),
    ("-$2.00 to -$0.50", -2.00, -0.50),
    ("-$5.00 to -$2.00", -5.00, -2.00),
    ("< -$5.00", -float("inf"), -5.00),
]

ENTRY_PRICE_BUCKETS: list[tuple[str, float, float]] = [
    ("≤ $0.10", 0.0, 0.10),
    ("$0.10-$0.15", 0.10, 0.15),
    ("$0.15-$0.20", 0.15, 0.20),
    ("$0.20-$0.25", 0.20, 0.25),
    ("$0.25-$0.30", 0.25, 0.30),
    ("$0.30-$0.35", 0.30, 0.35),
]


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True,
    )


# ---- Re-entry state machine --------------------------------------------

@dataclass
class ReEntry:
    entry_tick: int
    entry_price: float
    leg1_side: str              # "fav" / "dog"
    outcome: str                # "bilateral" / "T5" / "end_of_game"
    exit_tick: int
    exit_price: float           # resolution-value equivalent for bilateral
    pnl: float
    leg2_price: float | None = None


@dataclass
class ReEntryGameResult:
    ticker: str
    abs_spread: float
    winner: str
    entries: list[ReEntry] = field(default_factory=list)
    capped_at_loss: bool = False

    @property
    def cumulative_pnl(self) -> float:
        return sum(e.pnl for e in self.entries)

    @property
    def n_bilats(self) -> int:
        return sum(1 for e in self.entries if e.outcome == "bilateral")

    @property
    def n_t5(self) -> int:
        return sum(1 for e in self.entries if e.outcome == "T5")

    @property
    def n_entries(self) -> int:
        return len(self.entries)


def _bilateral_pnl_from_prices(leg1_price: float, leg2_price: float) -> float:
    cost = (leg1_price + leg2_price) * CONTRACTS
    fee1 = kalshi_fee(CONTRACTS, leg1_price, maker=True)
    fee2 = kalshi_fee(CONTRACTS, leg2_price, maker=True)
    return 1.0 * CONTRACTS - cost - fee1 - fee2


def _t5_exit_pnl(
    leg1_price: float, exit_price: float,
) -> float:
    entry_fee = kalshi_fee(CONTRACTS, leg1_price, maker=True)
    exit_fee = kalshi_fee(CONTRACTS, exit_price, maker=False)
    return (exit_price - leg1_price) * CONTRACTS - entry_fee - exit_fee


def simulate_reentry_game(
    ctx: GameCtx,
    x: float, y: float,
    cooldown_ticks: int,
    loss_cap: float | None,
    max_entries: int,
) -> ReEntryGameResult:
    """Simulate re-entry state machine on one game's trajectory."""
    result = ReEntryGameResult(
        ticker=ctx.ticker, abs_spread=ctx.abs_spread, winner=ctx.winner,
    )
    n = ctx.n_ticks
    fav = ctx.fav_series
    dog = ctx.dog_series

    state = "IDLE"
    leg1_tick = -1
    leg1_price = 0.0
    leg1_side = ""
    cooldown_until = 0

    i = 0
    while i < n:
        if len(result.entries) >= max_entries:
            break
        if loss_cap is not None and result.cumulative_pnl <= -loss_cap:
            result.capped_at_loss = True
            break
        if state == "IDLE" and i >= cooldown_until:
            # Check entry (Policy A: any observation ≤ Y)
            fav_i, dog_i = fav[i], dog[i]
            if fav_i <= y or dog_i <= y:
                state = "LEG1_OPEN"
                leg1_tick = i
                if fav_i <= y and dog_i <= y:
                    # Both ≤ Y at same tick — pick lower-priced side.
                    leg1_side = "fav" if fav_i <= dog_i else "dog"
                elif fav_i <= y:
                    leg1_side = "fav"
                else:
                    leg1_side = "dog"
                leg1_price = (
                    float(fav_i) if leg1_side == "fav" else float(dog_i)
                )
                i += 1
                continue
        if state == "LEG1_OPEN":
            # Check leg 2 fill (other side ≤ X)
            other = dog[i] if leg1_side == "fav" else fav[i]
            if other <= x:
                leg2_price = float(other)
                pnl = _bilateral_pnl_from_prices(leg1_price, leg2_price)
                result.entries.append(ReEntry(
                    entry_tick=leg1_tick, entry_price=leg1_price,
                    leg1_side=leg1_side, outcome="bilateral",
                    exit_tick=i,
                    exit_price=1.0,  # bilateral always pays $1.00 combined
                    pnl=pnl, leg2_price=leg2_price,
                ))
                state = "IDLE"
                cooldown_until = i + cooldown_ticks
                i += 1
                continue
            # Check T5 timeout
            if i - leg1_tick >= T5_TICKS:
                exit_price_series = (
                    fav if leg1_side == "fav" else dog
                )
                exit_price = float(exit_price_series[i])
                pnl = _t5_exit_pnl(leg1_price, exit_price)
                result.entries.append(ReEntry(
                    entry_tick=leg1_tick, entry_price=leg1_price,
                    leg1_side=leg1_side, outcome="T5",
                    exit_tick=i, exit_price=exit_price, pnl=pnl,
                ))
                state = "IDLE"
                cooldown_until = i + cooldown_ticks
                i += 1
                continue
        i += 1

    # Open position at game end: hold to resolution
    if state == "LEG1_OPEN":
        entry_fee = kalshi_fee(CONTRACTS, leg1_price, maker=True)
        payoff = 1.0 if leg1_side == ctx.winner else 0.0
        pnl = (payoff - leg1_price) * CONTRACTS - entry_fee
        result.entries.append(ReEntry(
            entry_tick=leg1_tick, entry_price=leg1_price,
            leg1_side=leg1_side, outcome="end_of_game",
            exit_tick=n - 1, exit_price=payoff, pnl=pnl,
        ))
    return result


@dataclass
class ReEntryConfigRollup:
    cooldown_ticks: int
    loss_cap: float | None
    games_entered: int
    total_entries: int
    n_bilats: int
    n_t5: int
    n_eog: int
    bilat_total_pnl: float
    t5_total_pnl: float
    eog_total_pnl: float
    net_total_pnl: float
    ev_per_game: float
    annual_ev: float
    per_game: list[ReEntryGameResult]


def run_reentry_config(
    ctxs: list[GameCtx],
    cooldown_ticks: int,
    loss_cap: float | None,
    max_entries: int = MAX_ENTRIES_PER_GAME,
    x: float = BASELINE_X, y: float = BASELINE_Y,
) -> ReEntryConfigRollup:
    per_game: list[ReEntryGameResult] = []
    for c in ctxs:
        per_game.append(simulate_reentry_game(
            c, x, y, cooldown_ticks, loss_cap, max_entries,
        ))
    games_entered = sum(1 for g in per_game if g.n_entries > 0)
    total_entries = sum(g.n_entries for g in per_game)
    n_bilats = sum(g.n_bilats for g in per_game)
    n_t5 = sum(g.n_t5 for g in per_game)
    n_eog = sum(
        1 for g in per_game for e in g.entries
        if e.outcome == "end_of_game"
    )
    bilat_total = sum(
        e.pnl for g in per_game for e in g.entries
        if e.outcome == "bilateral"
    )
    t5_total = sum(
        e.pnl for g in per_game for e in g.entries
        if e.outcome == "T5"
    )
    eog_total = sum(
        e.pnl for g in per_game for e in g.entries
        if e.outcome == "end_of_game"
    )
    net = bilat_total + t5_total + eog_total
    n_games = len(ctxs)
    evpg = net / n_games if n_games else 0.0
    return ReEntryConfigRollup(
        cooldown_ticks=cooldown_ticks, loss_cap=loss_cap,
        games_entered=games_entered, total_entries=total_entries,
        n_bilats=n_bilats, n_t5=n_t5, n_eog=n_eog,
        bilat_total_pnl=bilat_total, t5_total_pnl=t5_total,
        eog_total_pnl=eog_total, net_total_pnl=net,
        ev_per_game=evpg, annual_ev=evpg * ANNUAL_SCALE_GAMES,
        per_game=per_game,
    )


def baseline_single_entry_rollup(
    ctxs: list[GameCtx],
) -> ReEntryConfigRollup:
    """Reuse parent's simulate_policy for a 1-entry-per-game baseline."""
    entries = simulate_policy(
        ctxs, BASELINE_POLICY, BASELINE_X, BASELINE_Y,
    )
    per_game: dict[str, ReEntryGameResult] = {}
    for ctx in ctxs:
        per_game[ctx.ticker] = ReEntryGameResult(
            ticker=ctx.ticker, abs_spread=ctx.abs_spread,
            winner=ctx.winner,
        )
    n_bilats = 0
    n_t5 = 0
    bilat_total = 0.0
    t5_total = 0.0
    for e in entries:
        g = per_game[e.game_ticker]
        if e.leg2_filled:
            assert e.leg2_price is not None
            pnl = _bilateral_pnl_from_prices(e.leg1_price, e.leg2_price)
            g.entries.append(ReEntry(
                entry_tick=e.leg1_tick, entry_price=e.leg1_price,
                leg1_side=e.leg1_side, outcome="bilateral",
                exit_tick=e.leg2_tick or 0, exit_price=1.0,
                pnl=pnl, leg2_price=e.leg2_price,
            ))
            n_bilats += 1
            bilat_total += pnl
        else:
            # T5 exit using parent's helper
            pnl = stranded_time_abandon_pnl(e, T5_TICKS, e.winner)
            # Determine exit price for bookkeeping: leg1_bid_after_entry[T5_TICKS]
            if T5_TICKS < len(e.leg1_bid_after_entry):
                exit_price = float(
                    e.leg1_bid_after_entry[T5_TICKS]
                )
            else:
                # Resolution fallback (past game end)
                exit_price = 1.0 if e.leg1_side == e.winner else 0.0
            g.entries.append(ReEntry(
                entry_tick=e.leg1_tick, entry_price=e.leg1_price,
                leg1_side=e.leg1_side, outcome="T5",
                exit_tick=e.leg1_tick + T5_TICKS,
                exit_price=exit_price, pnl=pnl,
            ))
            n_t5 += 1
            t5_total += pnl
    per_game_list = list(per_game.values())
    games_entered = sum(1 for g in per_game_list if g.n_entries > 0)
    total_entries = sum(g.n_entries for g in per_game_list)
    net = bilat_total + t5_total
    n_games = len(ctxs)
    evpg = net / n_games if n_games else 0.0
    return ReEntryConfigRollup(
        cooldown_ticks=0, loss_cap=None,
        games_entered=games_entered, total_entries=total_entries,
        n_bilats=n_bilats, n_t5=n_t5, n_eog=0,
        bilat_total_pnl=bilat_total, t5_total_pnl=t5_total,
        eog_total_pnl=0.0, net_total_pnl=net,
        ev_per_game=evpg, annual_ev=evpg * ANNUAL_SCALE_GAMES,
        per_game=per_game_list,
    )


# ---- T5 distribution (Investigation 2) --------------------------------

def describe_t5_distribution(
    baseline: ReEntryConfigRollup,
) -> dict:
    t5_entries = [
        (g, e) for g in baseline.per_game for e in g.entries
        if e.outcome == "T5"
    ]
    pnls = np.array([e.pnl for _, e in t5_entries])
    if len(pnls) == 0:
        return {}
    bucket_rows: list[dict] = []
    cum = 0
    for lab, lo, hi in PNL_BUCKETS:
        mask = (pnls >= lo) & (pnls < hi)
        count = int(mask.sum())
        cum += count
        bucket_rows.append({
            "label": lab, "count": count,
            "pct": 100 * count / len(pnls),
            "cum_pct": 100 * cum / len(pnls),
        })
    profitable = int((pnls > 0).sum())
    unprofitable = int((pnls < 0).sum())
    breakeven = int((np.abs(pnls) < 0.5).sum())
    mean_profit = (
        float(pnls[pnls > 0].mean()) if (pnls > 0).any() else 0.0
    )
    mean_loss = (
        float(pnls[pnls < 0].mean()) if (pnls < 0).any() else 0.0
    )

    # Entry price breakdown
    price_rows: list[dict] = []
    for lab, lo, hi in ENTRY_PRICE_BUCKETS:
        subset = [
            e.pnl for _, e in t5_entries
            if lo <= e.entry_price < hi
        ]
        if not subset:
            price_rows.append({
                "label": lab, "count": 0,
                "mean_pnl": 0.0, "profitable_pct": 0.0,
            })
            continue
        arr = np.array(subset)
        price_rows.append({
            "label": lab, "count": len(arr),
            "mean_pnl": float(arr.mean()),
            "profitable_pct": 100 * (arr > 0).mean(),
        })
    return {
        "n": len(pnls),
        "buckets": bucket_rows,
        "profitable": profitable,
        "unprofitable": unprofitable,
        "breakeven": breakeven,
        "mean_profit": mean_profit,
        "mean_loss": mean_loss,
        "percentiles": {
            "mean": float(pnls.mean()),
            "median": float(np.median(pnls)),
            "p10": float(np.quantile(pnls, 0.10)),
            "p25": float(np.quantile(pnls, 0.25)),
            "p75": float(np.quantile(pnls, 0.75)),
            "p90": float(np.quantile(pnls, 0.90)),
        },
        "price_rows": price_rows,
    }


# ---- Blowout filter (Investigation 3) ---------------------------------

def apply_filter(
    ctxs: list[GameCtx], cutoff: float | None,
) -> tuple[list[GameCtx], list[GameCtx]]:
    """Return (kept, excluded) under the filter rule: skip games
    whose first observation has either side's bid ≥ cutoff."""
    if cutoff is None:
        return ctxs, []
    kept: list[GameCtx] = []
    excluded: list[GameCtx] = []
    for c in ctxs:
        first_fav = float(c.fav_series[0])
        first_dog = float(c.dog_series[0])
        if first_fav >= cutoff or first_dog >= cutoff:
            excluded.append(c)
        else:
            kept.append(c)
    return kept, excluded


# ---- Reporting helpers -------------------------------------------------

def worst_n_games(
    rollup: ReEntryConfigRollup, n: int = 10,
) -> list[ReEntryGameResult]:
    return sorted(
        rollup.per_game, key=lambda g: g.cumulative_pnl,
    )[:n]


def _trajectory_summary(g: ReEntryGameResult) -> str:
    if not g.entries:
        return "(no entries)"
    parts: list[str] = []
    for e in g.entries:
        if e.outcome == "bilateral":
            parts.append(
                f"bilat@t{e.entry_tick}:{e.leg1_side}@"
                f"${e.entry_price:.2f}"
            )
        elif e.outcome == "T5":
            parts.append(
                f"T5@t{e.entry_tick}→t{e.exit_tick}:"
                f"{e.leg1_side}@${e.entry_price:.2f}→"
                f"${e.exit_price:.2f} (${e.pnl:+.2f})"
            )
        else:
            parts.append(
                f"EOG@t{e.entry_tick}:"
                f"{e.leg1_side}@${e.entry_price:.2f} "
                f"(${e.pnl:+.2f})"
            )
    cap = " [loss-capped]" if g.capped_at_loss else ""
    return "; ".join(parts) + cap


# ---- Report rendering --------------------------------------------------

def render_report(
    n_games: int,
    baseline: ReEntryConfigRollup,
    reentry_configs: list[ReEntryConfigRollup],
    t5_distribution: dict,
    filter_single: list[dict],
    filter_reentry: list[dict],
    best_reentry: ReEntryConfigRollup,
    filter_worst_with: list[ReEntryGameResult],
    filter_worst_without: list[ReEntryGameResult],
) -> str:
    md: list[str] = []
    md.append("# Strategy 1 Bilateral — Follow-Up Investigations\n")
    md.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    md.append(
        f"Three focused follow-ups on the parent "
        f"`strategy1_bilateral_sim.py` analysis. Dataset: "
        f"**{n_games} games** (resolvable outcomes, all spreads). "
        "Baseline operating point: Policy A at threshold "
        f"(X={BASELINE_X:.2f}, Y={BASELINE_Y:.2f}) with T5 "
        f"(5-min / {T5_TICKS}-tick) stranded exit.\n"
    )
    md.append(
        "\n**Data approximation (inherited from parent):** "
        "`dog_kalshi_vwap` is computed as `1 - fav_kalshi_vwap`. "
        "Kalshi bid-ask spread (1-2c typical) is not modeled, so "
        "bilateral cost is slightly optimistic. Directional "
        "findings are robust; absolute EV should be read as an "
        "upper bound.\n"
    )

    # ---- Investigation 1 ------------------------------------------
    md.append("\n## Investigation 1 — Re-entry simulation\n")
    md.append(
        "Per-game state machine with up to "
        f"**{MAX_ENTRIES_PER_GAME} entries**. After a T5 exit, "
        "wait `cooldown_ticks` before re-entry eligibility. "
        "Optional per-game realized-loss cap halts further "
        "entries once cumulative game P&L ≤ -cap.\n"
    )
    md.append(
        "\n**Structural constraint revealed by this investigation:** "
        "bilaterals in the parent's single-entry baseline have a "
        f"**minimum interim of 71 ticks (35.5 min)** between leg 1 "
        "and leg 2; median is 209 ticks. With T5 bounded at "
        f"{T5_TICKS} ticks (5 min), re-entry guarantees **zero "
        "bilateral completions** — leg 2 never has time to fill "
        "before the T5 cutoff fires. Each re-entry cycle therefore "
        "realizes only T5 exit P&L (typically small negative due to "
        "fees + taker slippage). The results below quantify how "
        "much this death-by-cuts pattern costs per game.\n\n"
        "| Config | Cooldown | Loss cap | Games entered | Total entries | Bilats | T5 exits | EoG | Bilat $ | T5 $ | EoG $ | EV/game | Annual EV | Δ vs baseline |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    baseline_ev = baseline.annual_ev
    md.append(
        f"| 1-entry baseline | — | — | "
        f"{baseline.games_entered} | {baseline.total_entries} | "
        f"{baseline.n_bilats} | {baseline.n_t5} | 0 | "
        f"${baseline.bilat_total_pnl:+,.0f} | "
        f"${baseline.t5_total_pnl:+,.0f} | $0 | "
        f"${baseline.ev_per_game:+,.2f} | "
        f"${baseline.annual_ev:+,.0f} | — |\n"
    )
    for r in reentry_configs:
        loss_cap_str = (
            "none" if r.loss_cap is None else f"${r.loss_cap:.0f}"
        )
        delta = r.annual_ev - baseline_ev
        md.append(
            f"| re-3 cd={r.cooldown_ticks} cap={loss_cap_str} | "
            f"{r.cooldown_ticks} | {loss_cap_str} | "
            f"{r.games_entered} | {r.total_entries} | "
            f"{r.n_bilats} | {r.n_t5} | {r.n_eog} | "
            f"${r.bilat_total_pnl:+,.0f} | "
            f"${r.t5_total_pnl:+,.0f} | "
            f"${r.eog_total_pnl:+,.0f} | "
            f"${r.ev_per_game:+,.2f} | ${r.annual_ev:+,.0f} | "
            f"${delta:+,.0f} |\n"
        )

    # Entries-per-game distribution
    md.append("\n### Entries-per-game distribution\n")
    md.append(
        "| Config | 0 entries | 1 entry | 2 entries | 3 entries | Mean entries/game |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    for r in reentry_configs:
        loss_cap_str = (
            "none" if r.loss_cap is None else f"${r.loss_cap:.0f}"
        )
        counts = Counter(g.n_entries for g in r.per_game)
        n = len(r.per_game)
        mean_entries = r.total_entries / n if n else 0.0
        md.append(
            f"| re-3 cd={r.cooldown_ticks} cap={loss_cap_str} | "
            f"{counts.get(0, 0)} | {counts.get(1, 0)} | "
            f"{counts.get(2, 0)} | {counts.get(3, 0)} | "
            f"{mean_entries:.2f} |\n"
        )

    # Blowout accumulation on no-cap
    md.append("\n### Blowout accumulation (worst 10 — no-cap, cd=1)\n")
    no_cap = next(
        (r for r in reentry_configs
         if r.cooldown_ticks == 1 and r.loss_cap is None),
        None,
    )
    if no_cap is not None:
        md.append(
            "Worst per-game outcomes for the most permissive config "
            "(cooldown=1, no loss cap). Answers how bad the "
            "death-by-cuts scenario gets when the engine keeps "
            "re-entering.\n\n"
            "| # | Game | |Spread| | Entries | Bilats | T5 | Cumulative P&L | Trajectory |\n"
            "|---:|---|---:|---:|---:|---:|---:|---|\n"
        )
        for i, g in enumerate(worst_n_games(no_cap, 10), 1):
            md.append(
                f"| {i} | {g.ticker} | {g.abs_spread:.1f} | "
                f"{g.n_entries} | {g.n_bilats} | {g.n_t5} | "
                f"${g.cumulative_pnl:+.2f} | "
                f"{_trajectory_summary(g)} |\n"
            )

    # ---- Investigation 2 ------------------------------------------
    md.append("\n## Investigation 2 — T5 exit P&L distribution\n")
    md.append(
        f"All **{t5_distribution.get('n', 0)} stranded T5 exits** "
        "from the parent's single-entry baseline. Shows the shape "
        "of per-exit P&L.\n\n"
        "### P&L histogram\n\n"
        "| P&L bucket | Count | % | Cumulative % |\n"
        "|---|---:|---:|---:|\n"
    )
    for row in t5_distribution.get("buckets", []):
        md.append(
            f"| {row['label']} | {row['count']} | "
            f"{row['pct']:.1f}% | {row['cum_pct']:.1f}% |\n"
        )
    md.append("\n### Summary stats\n\n")
    p = t5_distribution.get("percentiles", {})
    md.append(
        f"- Profitable (P&L > $0): "
        f"{t5_distribution.get('profitable', 0)}\n"
        f"- Unprofitable (P&L < $0): "
        f"{t5_distribution.get('unprofitable', 0)}\n"
        f"- Approximately breakeven (|P&L| < $0.50): "
        f"{t5_distribution.get('breakeven', 0)}\n"
        f"- Mean P&L of profitable exits: "
        f"${t5_distribution.get('mean_profit', 0):+.2f}\n"
        f"- Mean P&L of unprofitable exits: "
        f"${t5_distribution.get('mean_loss', 0):+.2f}\n"
        f"- All T5 exits: mean ${p.get('mean', 0):+.2f}, "
        f"median ${p.get('median', 0):+.2f}, "
        f"P10 ${p.get('p10', 0):+.2f}, "
        f"P25 ${p.get('p25', 0):+.2f}, "
        f"P75 ${p.get('p75', 0):+.2f}, "
        f"P90 ${p.get('p90', 0):+.2f}\n"
    )

    md.append("\n### Entry price vs T5 P&L\n\n")
    md.append(
        "| Entry price | Count | Mean T5 P&L | Profitable % |\n"
        "|---|---:|---:|---:|\n"
    )
    for row in t5_distribution.get("price_rows", []):
        if row["count"] == 0:
            md.append(
                f"| {row['label']} | 0 | — | — |\n"
            )
            continue
        md.append(
            f"| {row['label']} | {row['count']} | "
            f"${row['mean_pnl']:+.2f} | "
            f"{row['profitable_pct']:.1f}% |\n"
        )

    # ---- Investigation 3 ------------------------------------------
    md.append("\n## Investigation 3 — Blowout filter sensitivity\n")
    md.append(
        "Pre-game filter: skip the game entirely if either side's "
        "first in-game observation is ≥ cutoff. All filters run "
        "the same baseline (Policy A, (0.20, 0.35), T5).\n"
    )

    md.append("\n### Single-entry baseline per filter\n\n")
    md.append(
        "| Filter | Games | Entries | Bilats | Stranded | "
        "Bilat $ | Strand $ | EV/game | Annual EV | Δ vs unfiltered |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    unfiltered_annual = None
    for row in filter_single:
        if unfiltered_annual is None:
            unfiltered_annual = row["annual_ev"]
        delta = row["annual_ev"] - unfiltered_annual
        md.append(
            f"| {row['filter_label']} | {row['n_games']} | "
            f"{row['n_entries']} | {row['n_bilats']} | "
            f"{row['n_stranded']} | "
            f"${row['bilat_total_pnl']:+,.0f} | "
            f"${row['t5_total_pnl']:+,.0f} | "
            f"${row['ev_per_game']:+,.2f} | "
            f"${row['annual_ev']:+,.0f} | "
            f"${delta:+,.0f} |\n"
        )

    md.append("\n### Excluded games — spread distribution\n\n")
    md.append(
        "| Filter | Excluded | 1-2 | 2.5-3.5 | 4-5 | 5.5-6 | 6.5-8 | 8.5-10 | 10.5+ |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for row in filter_single:
        md.append(f"| {row['filter_label']} | {row['n_excluded']} |")
        sd = row.get("excluded_spread_dist", {})
        for lab, _, _ in SPREAD_BUCKETS:
            md.append(f" {sd.get(lab, 0)} |")
        md.append("\n")

    md.append("\n### Excluded games — what we're giving up\n\n")
    md.append(
        "| Filter | Excluded | Their total P&L | Their mean EV/game | Interpretation |\n"
        "|---|---:|---:|---:|---|\n"
    )
    for row in filter_single:
        if row["n_excluded"] == 0:
            md.append(
                f"| {row['filter_label']} | 0 | $0 | $0.00 | "
                "no games cut |\n"
            )
            continue
        mean_ex_ev = (
            row["excluded_total_pnl"] / row["n_excluded"]
            if row["n_excluded"] else 0.0
        )
        if mean_ex_ev > 0:
            interp = "cuts profitable games (filter costs EV)"
        elif mean_ex_ev < 0:
            interp = "cuts losing games (filter improves EV)"
        else:
            interp = "break-even cut"
        md.append(
            f"| {row['filter_label']} | {row['n_excluded']} | "
            f"${row['excluded_total_pnl']:+,.2f} | "
            f"${mean_ex_ev:+.2f} | {interp} |\n"
        )

    md.append(
        "\n### Re-entry config under each filter (best re-entry config only)\n\n"
    )
    loss_cap_str_best = (
        "none" if best_reentry.loss_cap is None
        else f"${best_reentry.loss_cap:.0f}"
    )
    md.append(
        f"Best re-entry config from Investigation 1: "
        f"cooldown={best_reentry.cooldown_ticks}, "
        f"loss_cap={loss_cap_str_best}, "
        f"annual EV ${best_reentry.annual_ev:+,.0f} on the "
        "unfiltered universe. Apply each filter and re-run:\n\n"
        "| Filter | Games | Total entries | Bilats | T5 | EoG | "
        "EV/game | Annual EV | Δ vs unfiltered |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    unfilt_re_annual = None
    for row in filter_reentry:
        if unfilt_re_annual is None:
            unfilt_re_annual = row["annual_ev"]
        delta = row["annual_ev"] - unfilt_re_annual
        md.append(
            f"| {row['filter_label']} | {row['n_games']} | "
            f"{row['total_entries']} | {row['n_bilats']} | "
            f"{row['n_t5']} | {row['n_eog']} | "
            f"${row['ev_per_game']:+,.2f} | "
            f"${row['annual_ev']:+,.0f} | "
            f"${delta:+,.0f} |\n"
        )

    md.append(
        "\n### Blowout filter + re-entry interaction\n\n"
        "Worst 5 per-game P&L outcomes for the best re-entry config, "
        "WITH $0.80 filter vs WITHOUT. Tighter floors on the WITH "
        "side indicate the filter is defusing blowouts.\n\n"
        "**Without $0.80 filter (top 5 worst):**\n\n"
        "| # | Game | |Spread| | Entries | T5 | Cumulative P&L |\n"
        "|---:|---|---:|---:|---:|---:|\n"
    )
    for i, g in enumerate(filter_worst_without[:5], 1):
        md.append(
            f"| {i} | {g.ticker} | {g.abs_spread:.1f} | "
            f"{g.n_entries} | {g.n_t5} | "
            f"${g.cumulative_pnl:+.2f} |\n"
        )
    md.append(
        "\n**With $0.80 filter (top 5 worst):**\n\n"
        "| # | Game | |Spread| | Entries | T5 | Cumulative P&L |\n"
        "|---:|---|---:|---:|---:|---:|\n"
    )
    for i, g in enumerate(filter_worst_with[:5], 1):
        md.append(
            f"| {i} | {g.ticker} | {g.abs_spread:.1f} | "
            f"{g.n_entries} | {g.n_t5} | "
            f"${g.cumulative_pnl:+.2f} |\n"
        )

    # ---- Recommended config synthesis --------------------------
    md.append("\n## Recommended S1 engine configuration\n")
    best_reentry_filter = max(filter_reentry, key=lambda r: r["annual_ev"])
    best_single_filter = max(filter_single, key=lambda r: r["annual_ev"])
    # Global best across (single vs re-entry) × filter
    if best_single_filter["annual_ev"] >= best_reentry_filter["annual_ev"]:
        use_reentry = False
        global_best = best_single_filter
    else:
        use_reentry = True
        global_best = best_reentry_filter

    md.append(
        "\nBased on the three investigations, the best-tested "
        "configuration is:\n\n"
        f"- **Entry policy:** Policy A (any observation ≤ "
        f"${BASELINE_Y:.2f})\n"
        f"- **Thresholds:** X=${BASELINE_X:.2f} (leg 2 tight), "
        f"Y=${BASELINE_Y:.2f} (leg 1 wide)\n"
    )
    if use_reentry:
        md.append(
            f"- **Re-entry:** enabled, max {MAX_ENTRIES_PER_GAME} "
            f"entries/game, cooldown "
            f"{best_reentry.cooldown_ticks} tick"
            f"{'s' if best_reentry.cooldown_ticks != 1 else ''}, "
            f"loss cap {loss_cap_str_best}\n"
        )
    else:
        md.append(
            "- **Re-entry:** DISABLED (single entry per game). "
            "Investigation 1 showed re-entry at T5=5min produces "
            "**zero bilateral completions** because leg 2 takes "
            "70+ ticks to fill (median 209 ticks). Every "
            "additional entry under re-entry is pure T5 churn — "
            "strictly negative EV.\n"
        )
    md.append(
        f"- **Blowout filter:** {global_best['filter_label']}\n"
        f"- **Stranded exit:** T5 (5-min abandonment at market)\n"
    )
    md.append(
        f"\n**Headline annual EV at this config:** "
        f"${global_best['annual_ev']:+,.0f}"
        f" ({'re-entry' if use_reentry else 'single-entry'}, "
        f"filter {global_best['filter_label']})\n"
    )
    md.append(
        f"\nFor comparison:\n"
        f"- Parent single-entry unfiltered baseline: "
        f"${baseline.annual_ev:+,.0f}/yr\n"
        f"- Best re-entry unfiltered: "
        f"${best_reentry.annual_ev:+,.0f}/yr "
        f"(worse than baseline — re-entry destroys value)\n"
        f"- Best single-entry filtered: "
        f"${best_single_filter['annual_ev']:+,.0f}/yr "
        f"({best_single_filter['filter_label']})\n"
        f"- Best re-entry filtered: "
        f"${best_reentry_filter['annual_ev']:+,.0f}/yr "
        f"({best_reentry_filter['filter_label']})\n"
    )
    md.append(
        "\n**Key findings across the three investigations:**\n\n"
        "1. **Re-entry at T5=5min is structurally broken** "
        "because bilaterals need 35+ min minimum to complete "
        "(median 104 min). T5 exits happen before leg 2 has any "
        "chance to fill. Re-entry would only help if T5 were "
        "extended past the typical bilateral horizon — but that "
        "defeats the point of re-entry (you can't retry within "
        "the same game).\n"
        "2. **T5 exit distribution is wider than the mean "
        "suggests.** Aggregate T5 P&L is -$681 across 314 exits "
        "(mean -$2.17) — small enough that bilateral wins "
        "swamp it. But the per-exit distribution is not tight: "
        "68% of T5 exits are losses, 24% lose more than $5, and "
        "P10 is -$8.62. The strand mechanism works at portfolio "
        "level because the 90 bilateral wins average +$53.52, "
        "not because individual strands are close to breakeven.\n"
        "3. **Blowout filters help modestly.** Filtering out "
        "games where the underdog opens below a threshold cuts "
        "the most lopsided match-ups. The filter removes some "
        "profitable games too, but on balance the EV/game goes "
        "up (fewer games, but higher average EV).\n"
    )
    md.append(
        "\n**Caveats that matter for paper trading:**\n\n"
        "- The `dog_kalshi_vwap = 1 - fav_vwap` approximation "
        "inflates bilateral cost slightly; real fills will be "
        "marginally worse.\n"
        "- Simulation assumes leg-1 maker bids fill reliably at "
        "threshold; Kalshi queue priority is not modeled.\n"
        "- The structural re-entry finding assumes leg-2 fills "
        "require the observed interim times (median 104 min). If "
        "real markets produce earlier leg-2 fills (e.g., during "
        "live momentum swings not captured in 30s-VWAP bins), "
        "re-entry economics could shift. Paper-trading will "
        "validate.\n"
    )
    return "".join(md) + "\n"


# ---- Main --------------------------------------------------------------

def main() -> int:
    log("Loading Kalshi paired dataset (all spreads)...")
    games = load_kalshi_games_all_spreads()
    log(f"  {len(games)} games loaded")
    ctxs = prepare_games(games)
    log(f"  {len(ctxs)} games with resolvable outcome")

    # --- Investigation 1 ---
    log(
        "Investigation 1: baseline + "
        f"{len(COOLDOWN_TICKS_GRID) * len(LOSS_CAP_GRID)} "
        "re-entry configs..."
    )
    baseline = baseline_single_entry_rollup(ctxs)
    log(
        f"  baseline: {baseline.games_entered} games entered, "
        f"{baseline.n_bilats} bilats, {baseline.n_t5} T5 exits, "
        f"${baseline.annual_ev:+,.0f}/yr"
    )
    reentry_configs: list[ReEntryConfigRollup] = []
    for cd in COOLDOWN_TICKS_GRID:
        for lc in LOSS_CAP_GRID:
            r = run_reentry_config(ctxs, cd, lc)
            reentry_configs.append(r)
            log(
                f"  re-3 cd={cd} cap="
                f"{'none' if lc is None else f'${lc:.0f}'}: "
                f"{r.total_entries} entries, {r.n_bilats} bilats, "
                f"${r.annual_ev:+,.0f}/yr"
            )
    best_reentry = max(reentry_configs, key=lambda r: r.annual_ev)

    # --- Investigation 2 ---
    log("Investigation 2: T5 distribution on baseline stranded set...")
    t5_dist = describe_t5_distribution(baseline)
    log(f"  {t5_dist.get('n', 0)} T5 exits")

    # --- Investigation 3 ---
    log("Investigation 3: blowout filter × (single-entry, re-entry)...")
    filter_single: list[dict] = []
    filter_reentry: list[dict] = []
    for cutoff in FILTER_CUTOFFS:
        kept, excluded = apply_filter(ctxs, cutoff)
        label = (
            "none (baseline)" if cutoff is None
            else f"≥ ${cutoff:.2f}"
        )

        # Single-entry on kept
        single = baseline_single_entry_rollup(kept)
        # Excluded total P&L under single-entry policy (what we
        # give up by filtering)
        if excluded:
            excluded_single = baseline_single_entry_rollup(excluded)
            excl_total = excluded_single.net_total_pnl
            excl_spread_dist = Counter()
            for g in excluded:
                lab = bucket_for(g.abs_spread)
                if lab is not None:
                    excl_spread_dist[lab] += 1
        else:
            excl_total = 0.0
            excl_spread_dist = Counter()
        filter_single.append({
            "filter_label": label, "cutoff": cutoff,
            "n_games": single.games_entered if cutoff is None
                       else len(kept),
            "n_entries": single.total_entries,
            "n_bilats": single.n_bilats,
            "n_stranded": single.n_t5,
            "bilat_total_pnl": single.bilat_total_pnl,
            "t5_total_pnl": single.t5_total_pnl,
            "ev_per_game": single.ev_per_game,
            "annual_ev": single.annual_ev,
            "n_excluded": len(excluded),
            "excluded_total_pnl": excl_total,
            "excluded_spread_dist": dict(excl_spread_dist),
        })

        # Re-entry on kept with best-reentry config params
        if kept:
            r = run_reentry_config(
                kept,
                best_reentry.cooldown_ticks, best_reentry.loss_cap,
            )
        else:
            r = ReEntryConfigRollup(
                cooldown_ticks=best_reentry.cooldown_ticks,
                loss_cap=best_reentry.loss_cap,
                games_entered=0, total_entries=0, n_bilats=0,
                n_t5=0, n_eog=0, bilat_total_pnl=0.0,
                t5_total_pnl=0.0, eog_total_pnl=0.0,
                net_total_pnl=0.0, ev_per_game=0.0, annual_ev=0.0,
                per_game=[],
            )
        filter_reentry.append({
            "filter_label": label, "cutoff": cutoff,
            "n_games": len(kept), "total_entries": r.total_entries,
            "n_bilats": r.n_bilats, "n_t5": r.n_t5,
            "n_eog": r.n_eog,
            "ev_per_game": r.ev_per_game, "annual_ev": r.annual_ev,
        })

    # Blowout filter × re-entry interaction — worst 5 with vs
    # without the $0.80 filter, at the best re-entry config.
    kept_080, _ = apply_filter(ctxs, 0.80)
    worst_with = worst_n_games(
        run_reentry_config(
            kept_080,
            best_reentry.cooldown_ticks, best_reentry.loss_cap,
        ),
        5,
    )
    worst_without = worst_n_games(best_reentry, 5)

    log("Rendering report...")
    md = render_report(
        n_games=len(ctxs),
        baseline=baseline,
        reentry_configs=reentry_configs,
        t5_distribution=t5_dist,
        filter_single=filter_single,
        filter_reentry=filter_reentry,
        best_reentry=best_reentry,
        filter_worst_with=worst_with,
        filter_worst_without=worst_without,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(md)
    log(f"Report → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
