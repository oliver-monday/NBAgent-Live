"""Kalshi historical trades probe — HOU-LAL (2026-04-18).

Pulls the complete trade tape for both sides of the HOU-LAL market
via Kalshi's unauthenticated market trades endpoint. Characterizes
volume, trade sizes, temporal patterns, taker flow, and price
concentration. Writes a markdown report and caches raw trades.

Run:
    python -m analysis.kalshi_trades_probe
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_FILE = REPO_ROOT / "data" / "orderbook_snapshots" / "2026-04-18.jsonl"
TRADES_DIR = REPO_ROOT / "data" / "kalshi_trades"
REPORT_PATH = REPO_ROOT / "docs" / "analysis_outputs" / "kalshi_trades_probe_houlal.md"
RAW_JSON_PATH = TRADES_DIR / "KXNBAGAME-26APR18HOULAL.json"

EVENT_TICKER = "KXNBAGAME-26APR18HOULAL"
# ESPN-anchored approximate tip time (from oscillation analysis)
TIP_UTC = datetime(2026, 4, 19, 0, 48, tzinfo=timezone.utc)


# ---------- Ticker discovery ----------

def discover_tickers() -> list[str]:
    """Find HOU-LAL market tickers from logger snapshots, fallback to API."""
    tickers: set[str] = set()
    if SNAPSHOT_FILE.exists():
        with SNAPSHOT_FILE.open() as f:
            for line in f:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = row.get("ticker", "")
                if EVENT_TICKER in t:
                    tickers.add(t)
    if not tickers:
        # Fallback: probe markets by event_ticker
        resp = requests.get(
            f"{BASE_URL}/markets",
            params={"event_ticker": EVENT_TICKER, "limit": 50},
            timeout=30,
        )
        resp.raise_for_status()
        for m in resp.json().get("markets", []):
            tickers.add(m["ticker"])
    return sorted(tickers)


# ---------- Trade fetch ----------

def fetch_all_trades(ticker: str) -> list[dict]:
    """Paginate through all trades for a ticker via /markets/trades.

    Note: the `/historical/trades` path returned empty for this event on
    probe (2026-04-19). `/markets/trades` returns the full tape and is
    unauthenticated for settled markets.
    """
    url = f"{BASE_URL}/markets/trades"
    all_trades: list[dict] = []
    cursor: str | None = None
    while True:
        params: dict = {"ticker": ticker, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        trades = data.get("trades", [])
        all_trades.extend(trades)
        cursor = data.get("cursor")
        if not cursor or not trades:
            break
        time.sleep(0.25)
    return all_trades


# ---------- Helpers ----------

def _parse_ts(s: str) -> datetime:
    # ISO-8601 with trailing Z or explicit offset
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def build_df(trades: list[dict]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["created_time"] = df["created_time"].map(_parse_ts)
    df["count_fp"] = df["count_fp"].astype(float)
    df["yes_price_dollars"] = df["yes_price_dollars"].astype(float)
    df["no_price_dollars"] = df["no_price_dollars"].astype(float)
    df["side_team"] = df["ticker"].str.rsplit("-", n=1).str[-1]
    df = df.sort_values("created_time").reset_index(drop=True)
    return df


# ---------- Analysis sections ----------

SIZE_BUCKETS = [
    ("1-10", 1, 10),
    ("11-50", 11, 50),
    ("51-100", 51, 100),
    ("101-500", 101, 500),
    ("501-1000", 501, 1000),
    ("1001-5000", 1001, 5000),
    ("5000+", 5001, float("inf")),
]

PRICE_BUCKETS = [
    ("$0.00-0.10", 0.00, 0.10),
    ("$0.10-0.20", 0.10, 0.20),
    ("$0.20-0.30", 0.20, 0.30),
    ("$0.30-0.40", 0.30, 0.40),
    ("$0.40-0.50", 0.40, 0.50),
    ("$0.50-0.60", 0.50, 0.60),
    ("$0.60-0.70", 0.60, 0.70),
    ("$0.70-0.80", 0.70, 0.80),
    ("$0.80-0.90", 0.80, 0.90),
    ("$0.90-1.00", 0.90, 1.0001),
]


def section1_summary(df: pd.DataFrame, tickers: list[str]) -> str:
    lines = ["## Section 1 — Data summary", ""]
    lines.append(f"- Tickers discovered: {', '.join(tickers)}")
    lines.append(f"- Total trades (both sides): **{len(df):,}**")
    for t in tickers:
        sub = df[df["ticker"] == t]
        lines.append(f"  - `{t}`: {len(sub):,} trades")
    if len(df):
        lines.append(f"- Time range: {df['created_time'].min().isoformat()} → {df['created_time'].max().isoformat()}")
        lines.append(f"- Total volume (count_fp sum): **{df['count_fp'].sum():,.2f}**")
    lines.append("")
    lines.append("### Raw count_fp sample (for unit inspection)")
    lines.append("")
    lines.append("```")
    for row in df.head(10).itertuples():
        lines.append(f"count_fp={row.count_fp:>12.2f}  yes_price={row.yes_price_dollars:.4f}  taker={row.taker_side}  t={row.created_time.isoformat()}")
    lines.append("```")
    lines.append("")
    lines.append("Interpretation: `count_fp` values include fractional contracts (e.g., 1870.38, 464.08) — they are reported in contracts, not a fixed-point integer. Fractional amounts reflect partial maker fills.")
    lines.append("")
    return "\n".join(lines)


def _size_bucket(n: float) -> str:
    for name, lo, hi in SIZE_BUCKETS:
        if lo <= n <= hi:
            return name
    return "5000+"


def section2_size_distribution(df: pd.DataFrame) -> str:
    lines = ["## Section 2 — Trade size distribution", ""]

    def table_for(subset: pd.DataFrame, label: str) -> list[str]:
        out = [f"### {label} (n={len(subset):,}, total contracts={subset['count_fp'].sum():,.2f})", ""]
        if subset.empty:
            out.append("_no trades_")
            out.append("")
            return out
        total_n = len(subset)
        total_v = subset["count_fp"].sum()
        out.append("| Bucket | Trades | % of trades | Volume | % of volume |")
        out.append("|---|---:|---:|---:|---:|")
        buckets = subset["count_fp"].map(_size_bucket)
        for name, _, _ in SIZE_BUCKETS:
            mask = buckets == name
            n = int(mask.sum())
            v = float(subset.loc[mask, "count_fp"].sum())
            out.append(f"| {name} | {n:,} | {100*n/total_n:.1f}% | {v:,.2f} | {100*v/total_v if total_v else 0:.1f}% |")
        out.append("")
        q = subset["count_fp"].quantile
        out.append(
            f"- median: **{subset['count_fp'].median():.2f}**, "
            f"mean: **{subset['count_fp'].mean():.2f}**, "
            f"p75: **{q(0.75):.2f}**, p90: **{q(0.90):.2f}**, p99: **{q(0.99):.2f}**, "
            f"max: **{subset['count_fp'].max():.2f}**"
        )
        out.append("")
        return out

    lines.extend(table_for(df, "Pooled (both sides)"))
    for t in sorted(df["ticker"].unique()):
        lines.extend(table_for(df[df["ticker"] == t], t))
    return "\n".join(lines)


def section3_volume_over_time(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    lines = ["## Section 3 — Volume over time (5-min buckets)", ""]
    if df.empty:
        return "\n".join(lines + ["_no trades_"]), pd.DataFrame()
    d = df.copy()
    d["bucket"] = d["created_time"].dt.floor("5min")
    # VWAP on yes_price
    agg = d.groupby("bucket").apply(
        lambda g: pd.Series({
            "trades": len(g),
            "volume": g["count_fp"].sum(),
            "mean_size": g["count_fp"].mean(),
            "vwap_yes": (g["yes_price_dollars"] * g["count_fp"]).sum() / g["count_fp"].sum(),
        }),
        include_groups=False,
    ).reset_index()
    agg = agg.sort_values("bucket").reset_index(drop=True)
    agg["phase"] = agg["bucket"].map(lambda t: "pre-tip" if t < TIP_UTC else "in-game/post")

    lines.append(f"Tip reference time (UTC): **{TIP_UTC.isoformat()}**")
    lines.append("")
    lines.append("| Bucket (UTC) | Phase | Trades | Volume | Mean size | VWAP yes |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for r in agg.itertuples():
        lines.append(
            f"| {r.bucket.strftime('%Y-%m-%d %H:%M')} | {r.phase} | {int(r.trades):,} | "
            f"{r.volume:,.2f} | {r.mean_size:,.2f} | {r.vwap_yes:.4f} |"
        )
    lines.append("")

    pre = agg[agg["phase"] == "pre-tip"]
    lines.append(f"- Pre-tip trades: **{int(pre['trades'].sum()):,}** / volume **{pre['volume'].sum():,.2f}**")
    if len(agg):
        peak = agg.loc[agg["volume"].idxmax()]
        lines.append(f"- Peak 5-min bucket: **{peak['bucket'].strftime('%Y-%m-%d %H:%M')} UTC** — volume {peak['volume']:,.2f} across {int(peak['trades'])} trades")
    lines.append("")
    return "\n".join(lines), agg


def section4_taker_flow(df: pd.DataFrame) -> str:
    lines = ["## Section 4 — Taker-side flow (5-min buckets)", ""]
    if df.empty:
        return "\n".join(lines + ["_no trades_"])
    d = df.copy()
    d["bucket"] = d["created_time"].dt.floor("5min")
    rows = []
    for bucket, g in d.groupby("bucket"):
        yes = g[g["taker_side"] == "yes"]
        no = g[g["taker_side"] == "no"]
        rows.append({
            "bucket": bucket,
            "yes_n": len(yes), "yes_vol": yes["count_fp"].sum(),
            "no_n": len(no), "no_vol": no["count_fp"].sum(),
            "net_flow": yes["count_fp"].sum() - no["count_fp"].sum(),
        })
    agg = pd.DataFrame(rows).sort_values("bucket")
    lines.append("Net taker flow = yes_volume − no_volume (positive ⇒ YES-buyers aggressing).")
    lines.append("")
    lines.append("| Bucket (UTC) | YES trades | YES vol | NO trades | NO vol | Net flow |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for r in agg.itertuples():
        lines.append(
            f"| {r.bucket.strftime('%Y-%m-%d %H:%M')} | {r.yes_n:,} | {r.yes_vol:,.2f} | "
            f"{r.no_n:,} | {r.no_vol:,.2f} | {r.net_flow:+,.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def section5_volume_by_price(df: pd.DataFrame) -> str:
    lines = ["## Section 5 — Volume by yes-price bucket", ""]
    if df.empty:
        return "\n".join(lines + ["_no trades_"])
    rows = []
    for name, lo, hi in PRICE_BUCKETS:
        mask = (df["yes_price_dollars"] >= lo) & (df["yes_price_dollars"] < hi)
        sub = df[mask]
        rows.append({
            "bucket": name,
            "trades": len(sub),
            "volume": sub["count_fp"].sum(),
            "mean_size": sub["count_fp"].mean() if len(sub) else 0.0,
        })
    t_agg = pd.DataFrame(rows)
    lines.append("| Price bucket (yes) | Trades | Volume | Mean size |")
    lines.append("|---|---:|---:|---:|")
    for r in t_agg.itertuples():
        lines.append(f"| {r.bucket} | {int(r.trades):,} | {r.volume:,.2f} | {r.mean_size:,.2f} |")
    lines.append("")
    strat3_mask = (df["yes_price_dollars"] >= 0.35) & (df["yes_price_dollars"] < 0.55)
    s3 = df[strat3_mask]
    lines.append(
        f"- Strategy 3 zone ($0.35–0.55): **{len(s3):,}** trades, "
        f"**{s3['count_fp'].sum():,.2f}** contracts "
        f"({100*s3['count_fp'].sum()/df['count_fp'].sum():.1f}% of total volume)."
    )
    lines.append("")
    return "\n".join(lines)


def section6_book_crossref(df: pd.DataFrame) -> str:
    lines = ["## Section 6 — Trade × orderbook snapshot cross-reference", ""]
    if not SNAPSHOT_FILE.exists():
        lines.append("_Snapshot file missing; skipped._")
        lines.append("")
        return "\n".join(lines)
    # Load snapshots for HOU-LAL tickers only
    snaps: dict[str, list[dict]] = defaultdict(list)
    with SNAPSHOT_FILE.open() as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = row.get("ticker", "")
            if EVENT_TICKER not in t:
                continue
            try:
                ts = _parse_ts(row["ts"])
                yb = float(row.get("yes_bid_dollars") or "nan")
                ya = float(row.get("yes_ask_dollars") or "nan")
            except (KeyError, ValueError, TypeError):
                continue
            snaps[t].append((ts, yb, ya))
    for t in snaps:
        snaps[t].sort(key=lambda x: x[0])

    if not any(snaps.values()):
        lines.append("_No usable snapshots for HOU-LAL in 2026-04-18.jsonl; skipped._")
        lines.append("")
        return "\n".join(lines)

    # Nearest snapshot within 30s
    import bisect
    classify = {"bid": 0, "ask": 0, "mid": 0, "outside": 0, "nomatch": 0, "nobook": 0}
    for trade in df.itertuples():
        arr = snaps.get(trade.ticker, [])
        if not arr:
            classify["nomatch"] += 1
            continue
        ts_list = [s[0] for s in arr]
        idx = bisect.bisect_left(ts_list, trade.created_time)
        best = None
        for cand in (idx - 1, idx):
            if 0 <= cand < len(arr):
                d_sec = abs((arr[cand][0] - trade.created_time).total_seconds())
                if d_sec <= 30 and (best is None or d_sec < best[0]):
                    best = (d_sec, arr[cand])
        if best is None:
            classify["nomatch"] += 1
            continue
        _, (_, yb, ya) = best
        import math
        if math.isnan(yb) or math.isnan(ya):
            classify["nobook"] += 1
            continue
        p = trade.yes_price_dollars
        if abs(p - yb) < 1e-6:
            classify["bid"] += 1
        elif abs(p - ya) < 1e-6:
            classify["ask"] += 1
        elif yb < p < ya:
            classify["mid"] += 1
        else:
            classify["outside"] += 1
    total_matched = sum(v for k, v in classify.items() if k not in ("nomatch", "nobook"))
    lines.append(f"Matched trades (±30s, book available): **{total_matched:,}** / {len(df):,}")
    lines.append("")
    lines.append("| Classification | Count | % of matched |")
    lines.append("|---|---:|---:|")
    for k in ("bid", "ask", "mid", "outside"):
        n = classify[k]
        pct = 100 * n / total_matched if total_matched else 0
        lines.append(f"| at {k} | {n:,} | {pct:.1f}% |")
    lines.append(f"| _no book match_ | {classify['nomatch']:,} | — |")
    lines.append(f"| _book had null bid/ask_ | {classify['nobook']:,} | — |")
    lines.append("")
    lines.append("Trades landing at the bid or ask cost one tick of spread; 'mid' trades execute between the posted NBBO (e.g., price improvement from a hidden maker).")
    lines.append("")
    return "\n".join(lines)


def section7_sizing(df: pd.DataFrame, vol_by_bucket: pd.DataFrame) -> str:
    lines = ["## Section 7 — Sizing implications", ""]
    if df.empty:
        return "\n".join(lines + ["_no trades_"])
    sizes = df["count_fp"]
    total = len(sizes)
    for threshold in (100, 500, 1000):
        pct_ge = 100 * (sizes >= threshold).sum() / total
        lines.append(f"- Trades ≥ {threshold} contracts: **{pct_ge:.1f}%** of all trades ({(sizes >= threshold).sum():,}/{total:,}).")
    med = sizes.median()
    lines.append(f"- Percentile of a 100-contract order: roughly the **{100*(sizes < 100).sum()/total:.0f}th** percentile (median trade = {med:.1f} contracts).")
    lines.append("")
    # Invisibility: fraction of 5-min buckets where 100 contracts < 1% of bucket volume
    if not vol_by_bucket.empty:
        buckets = vol_by_bucket[vol_by_bucket["phase"] == "in-game/post"]
        if not buckets.empty:
            share = 100 / buckets["volume"].replace(0, pd.NA)
            invisible_frac = (share < 0.01).mean()
            median_share = (100 / buckets["volume"].median()) * 100
            lines.append(
                f"- In-game 5-min buckets where a 100-contract order is <1% of bucket volume: "
                f"**{100*invisible_frac:.0f}%** of buckets."
            )
            lines.append(
                f"- Median in-game 5-min bucket volume: **{buckets['volume'].median():,.0f}** contracts → "
                f"a 100-contract order is ~**{median_share:.2f}%** of that bucket."
            )
    lines.append("")
    return "\n".join(lines)


# ---------- Main ----------

def main() -> None:
    TRADES_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Discovering tickers...")
    tickers = discover_tickers()
    print(f"Tickers: {tickers}")
    if not tickers:
        raise SystemExit("No tickers discovered.")

    # Fetch and cache
    if RAW_JSON_PATH.exists():
        print(f"Loading cached raw trades from {RAW_JSON_PATH}")
        with RAW_JSON_PATH.open() as f:
            payload = json.load(f)
        all_trades = payload["trades"]
    else:
        all_trades = []
        for t in tickers:
            print(f"Fetching trades for {t}...")
            trades = fetch_all_trades(t)
            print(f"  → {len(trades):,} trades")
            all_trades.extend(trades)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "event_ticker": EVENT_TICKER,
            "tickers": tickers,
            "trades": all_trades,
        }
        with RAW_JSON_PATH.open("w") as f:
            json.dump(payload, f)
        print(f"Cached {len(all_trades):,} trades → {RAW_JSON_PATH}")

    df = build_df(all_trades)
    print(f"DataFrame shape: {df.shape}")

    sections = []
    sections.append(f"# Kalshi historical trades probe — HOU-LAL (2026-04-18)\n")
    sections.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n")
    sections.append(f"_Source: `GET {BASE_URL}/markets/trades` (unauthenticated)._\n")
    sections.append(section1_summary(df, tickers))
    sections.append(section2_size_distribution(df))
    sec3, vol_agg = section3_volume_over_time(df)
    sections.append(sec3)
    sections.append(section4_taker_flow(df))
    sections.append(section5_volume_by_price(df))
    sections.append(section6_book_crossref(df))
    sections.append(section7_sizing(df, vol_agg))

    REPORT_PATH.write_text("\n".join(sections))
    print(f"Report written → {REPORT_PATH}")


if __name__ == "__main__":
    main()
