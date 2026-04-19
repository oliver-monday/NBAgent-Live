"""
Strategy 3 oscillation analysis — HOU-LAL deep dive (n=1).

First Kalshi oscillation characterization on real in-game data. HOU-LAL
(2026-04-18 NBA Play-In) is the best single candidate — competitive
game, full live-window Kalshi coverage, observable runs.

Sections:
  1. Price timeseries summary (per side)
  2. Swing detection + magnitude/duration characterization
  3. Round-trip opportunity enumeration at entry/exit grids
  4. Bid-ask spread at Strategy 3 entry price levels
  5. Top-of-book depth at Strategy 3 entry price levels
  6. Strategy 3 viability scorecard against kill criteria

Outputs:
  - Markdown report → docs/analysis_outputs/strategy3_oscillation_houlal.md
  - Key findings to stdout
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

SNAP_DIR = Path("data/orderbook_snapshots")
OUTPUT_MD = Path("docs/analysis_outputs/strategy3_oscillation_houlal.md")
EVENT_FILTER = "HOULAL"

# Tip detection. For this single-game HOU-LAL analysis we anchor on the
# ESPN-verified tip time (00:48 UTC 4/19 from the Phase 3B smoke test).
# A volume-rate-based auto-detector was attempted; it's sensitive to
# pre-tip flow spikes (isolated large bets) and logger-gap boundary
# artifacts. For future multi-game oscillation work, build something
# more robust (e.g., first snapshot where ≥ 5 consecutive windows of
# sustained ≥100 fp/sec rate). For n=1 deep-dive, known-tip-anchor is
# fine and avoids spurious detection.
TIP_OVERRIDE_TS = pd.Timestamp("2026-04-19T00:48:00Z")
TIP_VOL_WINDOW = 20             # 10-min rolling window at 30s cadence
TIP_VOL_RATE_THRESHOLD = 200.0  # fp per second — used for cross-check log only
# Post-settlement detection: when mid stays in extreme zones for N
# consecutive snapshots (settlement + wind-down), that's game-over.
SETTLED_CONSECUTIVE = 5
SETTLED_LO = 0.02
SETTLED_HI = 0.98

# Swing detection
SWING_MIN_MAG = 0.02
SMOOTH_WINDOW = 3

# Round-trip grid
ENTRY_THRESHOLDS = [0.15, 0.20, 0.25, 0.30]
EXIT_DELTAS = [0.10, 0.15, 0.20]

# Strategy 3 entry-zone buckets (for spread + depth analysis)
ENTRY_BUCKETS = [
    (0.0, 0.10, "≤ $0.10"),
    (0.10, 0.15, "(0.10, 0.15]"),
    (0.15, 0.20, "(0.15, 0.20]"),
    (0.20, 0.25, "(0.20, 0.25]"),
    (0.25, 0.30, "(0.25, 0.30]"),
]


# ---- Fees ---------------------------------------------------------------

def taker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1:
        return 0.0
    return math.ceil(0.07 * contracts * price * (1.0 - price) * 100) / 100


def maker_fee(contracts: int, price: float) -> float:
    if price <= 0 or price >= 1:
        return 0.0
    return math.ceil(0.0175 * contracts * price * (1.0 - price) * 100) / 100


# ---- Data loading -------------------------------------------------------

def load_houlal() -> pd.DataFrame:
    """Load HOU-LAL snapshots from 2026-04-18.jsonl and 2026-04-19.jsonl.
    Returns DataFrame sorted by (team, ts)."""
    rows: list[dict] = []
    for fn in ("2026-04-18.jsonl", "2026-04-19.jsonl"):
        p = SNAP_DIR / fn
        if not p.exists():
            continue
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if EVENT_FILTER not in r.get("ticker", ""):
                    continue
                rows.append(r)
    if not rows:
        raise RuntimeError("No HOU-LAL rows found in date-based JSONL files")
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    for c in ("yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars",
              "no_ask_dollars", "last_price_dollars",
              "yes_bid_size_fp", "yes_ask_size_fp",
              "volume_fp", "open_interest_fp"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["mid"] = (df["yes_bid_dollars"] + df["yes_ask_dollars"]) / 2
    df["spread"] = df["yes_ask_dollars"] - df["yes_bid_dollars"]
    df["team"] = df["ticker"].str.rsplit("-", n=1).str[-1]
    # Deduplicate by (ts, ticker) in case of file overlap
    df = df.drop_duplicates(subset=["ts", "ticker"])
    df = df.dropna(subset=["mid"]).sort_values(
        ["team", "ts"]).reset_index(drop=True)
    return df


def detect_live_window(side: pd.DataFrame) -> tuple[int, int]:
    """Return (first_idx, last_idx) of the live-play window.

    Tip: first snapshot at or after TIP_OVERRIDE_TS (ESPN-verified).
    End: first N consecutive snapshots with mid in settlement zone.

    Also computes and prints the volume-rate-based auto-detection as a
    cross-check; may differ from the override due to pre-tip flow.
    """
    # ESPN-anchored tip
    first_mask = side["ts"] >= TIP_OVERRIDE_TS
    if not first_mask.any():
        return 0, len(side) - 1
    first = int(first_mask.idxmax())

    # Settlement end
    mids_after = side["mid"].iloc[first:].reset_index(drop=True)
    settled = (mids_after <= SETTLED_LO) | (mids_after >= SETTLED_HI)
    last = len(side) - 1
    if settled.any():
        arr = settled.values
        for i in range(len(arr) - SETTLED_CONSECUTIVE + 1):
            if arr[i:i + SETTLED_CONSECUTIVE].all():
                last = first + i
                break
    return first, last


def auto_detect_tip_crosscheck(side: pd.DataFrame) -> pd.Timestamp | None:
    """Compute the volume-rate-based tip estimate for cross-check only."""
    if len(side) < TIP_VOL_WINDOW:
        return None
    vol_delta = side["volume_fp"].diff().fillna(0).clip(lower=0)
    time_delta = side["ts"].diff().dt.total_seconds().fillna(1.0).clip(
        lower=1.0
    )
    vol_rate = vol_delta / time_delta
    rolling = vol_rate.rolling(window=TIP_VOL_WINDOW).mean()
    live_mask = rolling > TIP_VOL_RATE_THRESHOLD
    if not live_mask.any():
        return None
    first = max(0, int(live_mask.idxmax()) - (TIP_VOL_WINDOW - 1))
    return side["ts"].iloc[first]


# ---- Swing detection ----------------------------------------------------

def detect_swings(
    mids: pd.Series, tss: pd.Series, min_mag: float = SWING_MIN_MAG,
) -> list[dict]:
    """Detect oscillations using scipy.signal.find_peaks with prominence
    filtering. Prominence = min_mag ensures each returned extremum has
    at least min_mag of depth/height relative to surrounding terrain.
    Robust to plateaus (many consecutive tick-identical snapshots)."""
    if len(mids) < 3:
        return []
    smoothed = (
        mids.rolling(window=SMOOTH_WINDOW, center=True).median().fillna(mids)
    )
    vals = smoothed.values.astype(float)

    # Peaks (local maxima) and troughs (local minima). scipy doesn't
    # find troughs directly — invert the signal for the second call.
    peaks, _ = find_peaks(vals, prominence=min_mag)
    troughs, _ = find_peaks(-vals, prominence=min_mag)

    # Combine + sort by index, tag type
    extrema = sorted(
        [(int(i), float(vals[i]), "max") for i in peaks]
        + [(int(i), float(vals[i]), "min") for i in troughs],
        key=lambda e: e[0],
    )
    if not extrema:
        return []

    # Prepend a virtual extremum at idx 0 with opposite type of first
    # real extremum so the very first run (leading downswing or
    # upswing from the game start) gets counted.
    first_type = extrema[0][2]
    opposite = "min" if first_type == "max" else "max"
    extrema = [(0, float(vals[0]), opposite)] + extrema

    # Append a trailing virtual extremum at the last index with opposite
    # of the last real extremum so the final movement is captured.
    last_type = extrema[-1][2]
    opposite_last = "min" if last_type == "max" else "max"
    extrema.append((len(vals) - 1, float(vals[-1]), opposite_last))

    # Build swings between consecutive extrema, filtering magnitude
    swings: list[dict] = []
    for i in range(1, len(extrema)):
        a = extrema[i - 1]
        b = extrema[i]
        mag = abs(b[1] - a[1])
        if mag < min_mag:
            continue
        swings.append({
            "type": "up" if a[2] == "min" else "down",
            "start_idx": a[0], "end_idx": b[0],
            "start_price": a[1], "end_price": b[1],
            "magnitude": mag,
            "start_ts": tss.iloc[a[0]],
            "end_ts": tss.iloc[b[0]],
            "duration_sec": (
                tss.iloc[b[0]] - tss.iloc[a[0]]
            ).total_seconds(),
        })
    return swings


# ---- Round-trip enumeration ---------------------------------------------

def find_round_trips(
    side: pd.DataFrame, entry_threshold: float, exit_threshold: float,
) -> list[dict]:
    """Greedy scan: enter on first mid ≤ entry, exit on first subsequent
    mid ≥ exit. Returns round-trips in chronological order."""
    mids = side["mid"].values
    tss = side["ts"].values
    trips: list[dict] = []
    i = 0
    n = len(mids)
    while i < n:
        if mids[i] <= entry_threshold:
            entry_price = float(mids[i])
            entry_ts = tss[i]
            j = i + 1
            while j < n and mids[j] < exit_threshold:
                j += 1
            if j < n:
                exit_price = float(mids[j])
                exit_ts = tss[j]
                trips.append({
                    "entry_ts": entry_ts, "entry_price": entry_price,
                    "exit_ts": exit_ts, "exit_price": exit_price,
                    "hold_sec": float(
                        (pd.Timestamp(exit_ts)
                         - pd.Timestamp(entry_ts)).total_seconds()
                    ),
                    "incomplete": False,
                })
                i = j + 1
            else:
                trips.append({
                    "entry_ts": entry_ts, "entry_price": entry_price,
                    "exit_ts": tss[-1], "exit_price": float(mids[-1]),
                    "hold_sec": float(
                        (pd.Timestamp(tss[-1])
                         - pd.Timestamp(entry_ts)).total_seconds()
                    ),
                    "incomplete": True,
                })
                break
        else:
            i += 1
    return trips


def score_round_trip(trip: dict, contracts: int = 100) -> dict:
    gross = (trip["exit_price"] - trip["entry_price"]) * contracts
    taker_total = (
        taker_fee(contracts, trip["entry_price"])
        + taker_fee(contracts, trip["exit_price"])
    )
    maker_total = (
        maker_fee(contracts, trip["entry_price"])
        + maker_fee(contracts, trip["exit_price"])
    )
    return {
        **trip,
        "gross": gross,
        "taker_fees": taker_total,
        "maker_fees": maker_total,
        "net_taker": gross - taker_total,
        "net_maker": gross - maker_total,
    }


# ---- Report builder -----------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.md: list[str] = []

    def say(self, line: str = "", md: str | None = None) -> None:
        print(line)
        self.md.append(line if md is None else md)

    def stdout(self, line: str = "") -> None:
        print(line)

    def md_only(self, line: str = "") -> None:
        self.md.append(line)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.md) + "\n")


# ---- Analysis orchestration ---------------------------------------------

def main() -> int:
    rep = Report()
    rep.md_only(
        "# Strategy 3 oscillation analysis — HOU-LAL (2026-04-18)\n"
    )
    rep.md_only(
        "First Kalshi oscillation characterization on real in-game data. "
        "HOU-LAL NBA Play-In, LAL home, won 107-98. Logger captured the "
        "live window at 30s cadence.\n\n"
        "**n=1 caveat**: all findings below are single-game observations. "
        "Strategy 3 viability requires multi-game confirmation. This "
        "analysis validates the pipeline and produces a proof-of-concept "
        "characterization, not a graduation test.\n"
    )

    print("=" * 70)
    print("Strategy 3 oscillation analysis — HOU-LAL")
    print("=" * 70)

    # ---- Load ----
    print("\nLoading HOU-LAL snapshots…")
    df = load_houlal()
    print(f"  Total rows: {len(df):,}")
    print(f"  Tickers: {df['team'].unique().tolist()}")

    # Split by side
    sides = {t: df[df["team"] == t].reset_index(drop=True)
             for t in sorted(df["team"].unique())}

    # ---- Detect live window (ESPN-anchored tip + settlement) ----
    print(f"  ESPN-anchored tip: {TIP_OVERRIDE_TS}")
    tip_info = {}
    live_sides: dict[str, pd.DataFrame] = {}
    for t, side in sides.items():
        first, last = detect_live_window(side)
        first_ts = side["ts"].iloc[first]
        last_ts = side["ts"].iloc[last]
        tip_info[t] = (first, last, first_ts, last_ts)
        auto_ts = auto_detect_tip_crosscheck(side)
        auto_str = f" (auto-detect: {auto_ts})" if auto_ts else ""
        print(f"  {t}-side live window: idx [{first}, {last}] = "
              f"{first_ts} → {last_ts}  "
              f"({(last - first + 1)} snapshots){auto_str}")
        live_sides[t] = side.iloc[first:last + 1].reset_index(drop=True)

    # Use the earlier of the two detected tips + later of two ends for
    # the combined window (so the complement check below has fully
    # overlapping data)
    combined_tip_ts = min(info[2] for info in tip_info.values())
    combined_end_ts = max(info[3] for info in tip_info.values())
    print(f"  Combined window: {combined_tip_ts}  →  {combined_end_ts}")

    # ---- Section 1: Price timeseries summary ----
    rep.md_only("## 1. Price timeseries summary\n")
    print("\n=== Section 1: Price timeseries summary ===")
    rep.md_only(
        f"Live window: **{combined_tip_ts.isoformat()}** → "
        f"**{combined_end_ts.isoformat()}**. Tip anchored on ESPN-"
        f"verified tip-off (2026-04-19 00:48 UTC from Phase 3B smoke "
        f"test). End trimmed at first {SETTLED_CONSECUTIVE} consecutive "
        f"snapshots with mid in [0, {SETTLED_LO:.2f}] ∪ "
        f"[{SETTLED_HI:.2f}, 1]. Volume-rate auto-detector computed "
        f"as cross-check (see stdout); deferred to known-tip for this "
        f"single-game deep-dive due to sensitivity to pre-tip flow "
        f"spikes and logger-gap artifacts.\n"
    )

    rep.md_only(
        "| Side | n snapshots | Duration | Median gap | p5/p95 gap | "
        "Price range | Mean spread |\n"
        "|------|-------------|----------|------------|------------|"
        "-------------|-------------|"
    )
    for t in sorted(live_sides.keys()):
        side = live_sides[t]
        n = len(side)
        if n < 2:
            continue
        dur = (side["ts"].iloc[-1] - side["ts"].iloc[0]).total_seconds()
        tss = side["ts"]
        gaps = tss.diff().dt.total_seconds().dropna()
        lo, hi = side["mid"].min(), side["mid"].max()
        mean_sp = side["spread"].mean()
        print(f"  {t}: n={n}, duration={dur/60:.1f}m, "
              f"median gap={gaps.median():.1f}s, "
              f"p5/p95={gaps.quantile(0.05):.1f}s/{gaps.quantile(0.95):.1f}s, "
              f"mid range [{lo:.3f}, {hi:.3f}], mean spread=${mean_sp:.3f}")
        rep.md_only(
            f"| {t} | {n} | {dur/60:.1f} min | "
            f"{gaps.median():.1f}s | "
            f"{gaps.quantile(0.05):.1f}s / {gaps.quantile(0.95):.1f}s | "
            f"[{lo:.3f}, {hi:.3f}] | ${mean_sp:.3f} |"
        )

    # Complement check
    # Pair home (LAL) and away (HOU) on matched ts (within 5s)
    if "HOU" in live_sides and "LAL" in live_sides:
        comp = pd.merge_asof(
            live_sides["HOU"].sort_values("ts")[["ts", "mid"]].rename(
                columns={"mid": "mid_hou"}),
            live_sides["LAL"].sort_values("ts")[["ts", "mid"]].rename(
                columns={"mid": "mid_lal"}),
            on="ts", direction="nearest",
            tolerance=pd.Timedelta(seconds=5),
        ).dropna()
        comp["sum"] = comp["mid_hou"] + comp["mid_lal"]
        mean_dev = (comp["sum"] - 1.0).abs().mean()
        max_dev = (comp["sum"] - 1.0).abs().max()
        flag = " ⚠" if max_dev > 0.03 else ""
        print(f"\nComplement check: n={len(comp)}, mean |dev|={mean_dev:.4f}, "
              f"max |dev|={max_dev:.4f}{flag}")
        rep.md_only(
            f"\n**Complement check** (home + away mid): n={len(comp)}, "
            f"mean |dev| = {mean_dev:.4f}, max |dev| = {max_dev:.4f}.{flag}\n"
        )

    # ---- Section 2: Swing detection ----
    print("\n=== Section 2: Swing detection ===")
    rep.md_only("\n## 2. Swing detection and characterization\n")
    rep.md_only(
        f"Algorithm: 3-point rolling median → local extrema → "
        f"merge consecutive same-type → drop swings with magnitude "
        f"< ${SWING_MIN_MAG:.2f}. Swings are (trough→peak) upswings "
        "or (peak→trough) downswings on smoothed mid.\n"
    )

    all_swings: dict[str, list[dict]] = {}
    for t in sorted(live_sides.keys()):
        side = live_sides[t]
        swings = detect_swings(side["mid"], side["ts"])
        all_swings[t] = swings
        print(f"  {t}: {len(swings)} swings ≥ ${SWING_MIN_MAG:.2f}")

    # Per-side magnitude distribution
    rep.md_only(
        "### Per-side swing counts by magnitude threshold\n\n"
        "| Side | ≥$0.05 | ≥$0.10 | ≥$0.15 | ≥$0.20 | Total ≥$0.02 |\n"
        "|------|--------|--------|--------|--------|--------------|"
    )
    for t in sorted(all_swings.keys()):
        sw = all_swings[t]
        counts = {m: sum(1 for s in sw if s["magnitude"] >= m)
                  for m in (0.05, 0.10, 0.15, 0.20)}
        rep.md_only(
            f"| {t} | {counts[0.05]} | {counts[0.10]} | "
            f"{counts[0.15]} | {counts[0.20]} | {len(sw)} |"
        )

    # Combined magnitude/duration stats
    pooled = [s for sw in all_swings.values() for s in sw]
    rep.md_only("\n### Pooled magnitude + duration stats\n")
    if pooled:
        mags = pd.Series([s["magnitude"] for s in pooled])
        durs = pd.Series([s["duration_sec"] / 60 for s in pooled])
        rep.md_only(
            "| Stat | Magnitude | Duration (min) |\n"
            "|------|-----------|---------------|\n"
            f"| median | ${mags.median():.4f} | {durs.median():.2f} |\n"
            f"| mean   | ${mags.mean():.4f} | {durs.mean():.2f} |\n"
            f"| p75    | ${mags.quantile(0.75):.4f} | {durs.quantile(0.75):.2f} |\n"
            f"| p90    | ${mags.quantile(0.90):.4f} | {durs.quantile(0.90):.2f} |\n"
            f"| max    | ${mags.max():.4f} | {durs.max():.2f} |"
        )

    # Table of all swings ≥ $0.10
    big = [s for s in pooled if s["magnitude"] >= 0.10]
    big.sort(key=lambda s: s["start_ts"])
    rep.md_only(f"\n### All swings ≥ $0.10 (pooled both sides, N={len(big)})\n")
    if big:
        rep.md_only(
            "| side | type | start | end | start price | end price | "
            "magnitude | duration |\n"
            "|------|------|-------|-----|-------------|-----------|"
            "-----------|----------|"
        )
        # Attach side to each swing for the table
        side_map: dict[int, str] = {}
        for t, sw in all_swings.items():
            for s in sw:
                if s["magnitude"] >= 0.10:
                    side_map[id(s)] = t
        for s in big:
            t = side_map.get(id(s), "?")
            rep.md_only(
                f"| {t} | {s['type']} | "
                f"{pd.Timestamp(s['start_ts']).strftime('%H:%M:%S')} | "
                f"{pd.Timestamp(s['end_ts']).strftime('%H:%M:%S')} | "
                f"{s['start_price']:.3f} | {s['end_price']:.3f} | "
                f"${s['magnitude']:.3f} | {s['duration_sec']/60:.1f} min |"
            )

    print(f"  Pooled ≥$0.10 swings: {len(big)}")

    # ---- Section 3: Round-trip opportunities ----
    print("\n=== Section 3: Round-trip opportunities ===")
    rep.md_only("\n## 3. Round-trip opportunity identification\n")
    rep.md_only(
        "Greedy scan: enter when mid ≤ entry threshold, exit on first "
        "subsequent mid ≥ exit threshold, then resume scanning. Incomplete "
        "trips (still in position at game end) reported but excluded from "
        "summary statistics.\n"
    )

    # Summary table: combined both sides
    rep.md_only(
        "### Summary — all (entry, exit) pairs (both sides combined)\n\n"
        "| Entry | Exit | Δ | N trips | Mean hold (min) | Mean gross | "
        "Mean net (taker) | Mean net (maker) |\n"
        "|-------|------|---|---------|-----------------|------------|"
        "------------------|-------------------|"
    )
    all_trips_by_pair: dict[tuple[float, float], list[dict]] = {}
    for entry in ENTRY_THRESHOLDS:
        for delta in EXIT_DELTAS:
            exit_thr = entry + delta
            key = (entry, exit_thr)
            trips_both: list[dict] = []
            for t, side in live_sides.items():
                trips = find_round_trips(side, entry, exit_thr)
                for tr in trips:
                    tr["side"] = t
                    trips_both.append(score_round_trip(tr))
            all_trips_by_pair[key] = trips_both
            complete = [tr for tr in trips_both if not tr["incomplete"]]
            if complete:
                mean_hold = np.mean([tr["hold_sec"] for tr in complete]) / 60
                mean_gross = np.mean([tr["gross"] for tr in complete])
                mean_net_tk = np.mean([tr["net_taker"] for tr in complete])
                mean_net_mk = np.mean([tr["net_maker"] for tr in complete])
                cells = (
                    f"| {entry:.2f} | {exit_thr:.2f} | +{delta:.2f} | "
                    f"{len(complete)} | {mean_hold:.1f} | "
                    f"${mean_gross:.2f} | ${mean_net_tk:.2f} | "
                    f"${mean_net_mk:.2f} |"
                )
            else:
                cells = (
                    f"| {entry:.2f} | {exit_thr:.2f} | +{delta:.2f} | "
                    f"0 | — | — | — | — |"
                )
            rep.md_only(cells)

    # Detailed table of all round-trips at the most-permissive pair
    # (entry 0.30, exit 0.40 — likely highest count)
    detail_key = (0.30, 0.40)
    detail_trips = all_trips_by_pair.get(detail_key, [])
    rep.md_only(
        f"\n### All round-trips at ({detail_key[0]:.2f}, "
        f"{detail_key[1]:.2f}) — most-permissive pair\n"
    )
    if detail_trips:
        rep.md_only(
            "| side | entry ts | entry | exit ts | exit | hold (min) | "
            "gross | taker fees | net (taker) | net (maker) | incomplete |\n"
            "|------|----------|-------|---------|------|------------|"
            "-------|------------|-------------|-------------|------------|"
        )
        detail_trips.sort(key=lambda tr: tr["entry_ts"])
        for tr in detail_trips:
            rep.md_only(
                f"| {tr['side']} | "
                f"{pd.Timestamp(tr['entry_ts']).strftime('%H:%M:%S')} | "
                f"{tr['entry_price']:.3f} | "
                f"{pd.Timestamp(tr['exit_ts']).strftime('%H:%M:%S')} | "
                f"{tr['exit_price']:.3f} | "
                f"{tr['hold_sec']/60:.1f} | "
                f"${tr['gross']:.2f} | ${tr['taker_fees']:.2f} | "
                f"${tr['net_taker']:.2f} | ${tr['net_maker']:.2f} | "
                f"{'yes' if tr['incomplete'] else 'no'} |"
            )

    # Print summary to stdout
    for key, trips in all_trips_by_pair.items():
        complete = [tr for tr in trips if not tr["incomplete"]]
        print(f"  Entry ${key[0]:.2f} → exit ${key[1]:.2f}: "
              f"{len(complete)} complete round-trip(s)")

    # ---- Section 4: Spreads at entry zones ----
    print("\n=== Section 4: Spreads at entry zones ===")
    rep.md_only("\n## 4. Bid-ask spread at Strategy 3 entry price levels\n")
    rep.md_only(
        "Spread observations while mid ≤ $0.30, bucketed by mid price "
        "level. Reports spread in dollars and as a percentage of mid "
        "(the latter is the correct cost metric for Strategy 3 — at "
        "$0.02 spread, mid=$0.15 is 13% cost vs mid=$0.25 is 8%).\n"
    )
    rep.md_only(
        "| Bucket | n | Mean spread | Median | p75 | Max | Mean spread / mid |\n"
        "|--------|---|-------------|--------|-----|-----|-------------------|"
    )
    combined_live = pd.concat(list(live_sides.values())).sort_values("ts")
    for lo, hi, label in ENTRY_BUCKETS:
        if lo == 0:
            sub = combined_live[combined_live["mid"] <= hi]
        else:
            sub = combined_live[
                (combined_live["mid"] > lo) & (combined_live["mid"] <= hi)
            ]
        sub = sub.dropna(subset=["spread", "mid"])
        if len(sub) == 0:
            rep.md_only(f"| {label} | 0 | — | — | — | — | — |")
            continue
        mean_s = sub["spread"].mean()
        med_s = sub["spread"].median()
        p75_s = sub["spread"].quantile(0.75)
        max_s = sub["spread"].max()
        pct = (sub["spread"] / sub["mid"]).mean() * 100
        rep.md_only(
            f"| {label} | {len(sub)} | ${mean_s:.4f} | ${med_s:.4f} | "
            f"${p75_s:.4f} | ${max_s:.4f} | {pct:.1f}% |"
        )

    # ---- Section 5: Depth at entry zones ----
    print("\n=== Section 5: Book depth at entry zones ===")
    rep.md_only("\n## 5. Top-of-book depth at Strategy 3 entry price levels\n")
    rep.md_only(
        "`yes_bid_size_fp` at top-of-book when mid is in each entry "
        "zone. Flag: whether depth ≥ 50,000 (~50 contracts at $1 "
        "nominal — the kill-criteria minimum fill size).\n"
    )
    rep.md_only(
        "| Bucket | n | Mean size | Median | Min | Max | ≥50k depth? |\n"
        "|--------|---|-----------|--------|-----|-----|-------------|"
    )
    for lo, hi, label in ENTRY_BUCKETS:
        if lo == 0:
            sub = combined_live[combined_live["mid"] <= hi]
        else:
            sub = combined_live[
                (combined_live["mid"] > lo) & (combined_live["mid"] <= hi)
            ]
        sub = sub.dropna(subset=["yes_bid_size_fp"])
        if len(sub) == 0:
            rep.md_only(f"| {label} | 0 | — | — | — | — | — |")
            continue
        mean_sz = sub["yes_bid_size_fp"].mean()
        med_sz = sub["yes_bid_size_fp"].median()
        min_sz = sub["yes_bid_size_fp"].min()
        max_sz = sub["yes_bid_size_fp"].max()
        pct_50k = (sub["yes_bid_size_fp"] >= 50_000).mean() * 100
        flag = "✓" if pct_50k >= 50 else "⚠"
        rep.md_only(
            f"| {label} | {len(sub)} | {mean_sz:,.0f} | "
            f"{med_sz:,.0f} | {min_sz:,.0f} | {max_sz:,.0f} | "
            f"{pct_50k:.0f}% {flag} |"
        )

    # ---- Section 6: Viability scorecard ----
    print("\n=== Section 6: Viability scorecard ===")
    rep.md_only("\n## 6. Strategy 3 viability scorecard (n=1)\n")
    rep.md_only(
        "Single-game observation only — n=1 is not statistically "
        "meaningful. This characterizes the pipeline and produces a "
        "proof-of-concept reading, not a graduation test.\n"
    )

    # Compute observed metrics
    big_swing_mags = [s["magnitude"] for s in pooled if s["magnitude"] >= 0.10]
    median_big_mag = median(big_swing_mags) if big_swing_mags else None

    # Best-pair round trips: entry <= 0.25, exit >= +0.10
    mid25_trips = [tr for tr in all_trips_by_pair.get((0.25, 0.35), [])
                   if not tr["incomplete"]]
    median_hold_sec = (
        median([tr["hold_sec"] for tr in mid25_trips]) if mid25_trips else None
    )

    # Spread in the Strategy 3 entry zone (mid ≤ $0.30)
    z = combined_live[combined_live["mid"] <= 0.30].dropna(
        subset=["spread"])
    median_spread = z["spread"].median() if len(z) else None

    # Depth at mid ≤ $0.30
    z2 = combined_live[combined_live["mid"] <= 0.30].dropna(
        subset=["yes_bid_size_fp"])
    pct_50k_at_entry = (
        (z2["yes_bid_size_fp"] >= 50_000).mean() * 100 if len(z2) else None
    )

    def _pass(val, op, bar) -> str:
        if val is None:
            return "Insufficient data"
        if op == ">=":
            return "✓ Pass" if val >= bar else "✗ Fail"
        if op == "<":
            return "✓ Pass" if val < bar else "✗ Fail"
        return "?"

    rep.md_only(
        "| Criterion | Threshold | Observed (HOU-LAL) | Status |\n"
        "|-----------|-----------|--------------------|--------|\n"
        f"| Round-trip frequency | ≥ 8% of competitive games | "
        f"n/a (n=1) | — |\n"
        f"| Swing magnitude (median of ≥$0.10 swings) | ≥ $0.10 capture | "
        f"{('$' + f'{median_big_mag:.3f}') if median_big_mag else 'none'} | "
        f"{_pass(median_big_mag, '>=', 0.10)} |\n"
        f"| Realized spread at entry (median, mid ≤ $0.30) | < $0.03 | "
        f"{('$' + f'{median_spread:.4f}') if median_spread is not None else '—'} | "
        f"{_pass(median_spread, '<', 0.03)} |\n"
        f"| Book depth at entry (% ≥ 50k at mid ≤ $0.30) | ≥ 50 contracts | "
        f"{(f'{pct_50k_at_entry:.0f}% of snapshots ≥ 50k') if pct_50k_at_entry is not None else '—'} | "
        f"{_pass(pct_50k_at_entry, '>=', 50)} |\n"
        f"| Hold time (median at 0.25→0.35) | ≥ 90 seconds | "
        f"{(f'{median_hold_sec:.0f}s') if median_hold_sec else 'no complete trips'} | "
        f"{_pass(median_hold_sec, '>=', 90)} |"
    )

    print("\nViability scorecard (observed vs threshold):")
    print(f"  Swing magnitude ≥$0.10 median: "
          f"{f'${median_big_mag:.3f}' if median_big_mag else 'n/a'}")
    print(f"  Median spread at mid ≤$0.30: "
          f"{f'${median_spread:.4f}' if median_spread is not None else 'n/a'}")
    print(f"  Depth ≥50k at mid ≤$0.30: "
          f"{f'{pct_50k_at_entry:.0f}%' if pct_50k_at_entry is not None else 'n/a'} of snapshots")
    print(f"  Median hold @(0.25, 0.35): "
          f"{f'{median_hold_sec:.0f}s' if median_hold_sec else 'n/a'}")

    # Write report
    rep.write(OUTPUT_MD)
    print(f"\nReport written to {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
