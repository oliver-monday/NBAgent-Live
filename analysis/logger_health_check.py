"""
Kalshi logger health check — quick terminal diagnostic.

Reads the tails of recently-modified orderbook_snapshots/*.jsonl
files and reports cadence, active tickers, complement sanity, and
staleness. No external dependencies beyond the standard library.

Usage:
    python -m analysis.logger_health_check

Exit code 0 on healthy, 1 on any warning.

Since the logger writes per-event files (one per Kalshi event_ticker),
during live capture there will be multiple active files simultaneously
(2-12 games tracked at once during playoff runs). This script scans
by mtime and aggregates the tails of the N most recently modified
files so you see the full active picture, not just one event.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

SNAP_DIR = Path("data/orderbook_snapshots")
TAIL_LINES = 200           # lines to tail per file (100 snapshots per side)
MAX_FILES = 30             # cap on files to inspect; takes the most recent
RECENT_WINDOW_SEC = 300    # "last 5 minutes" for active-ticker report
STALENESS_WARN_SEC = 120   # warn if newest snapshot older than this
CADENCE_WARN_SEC = 90      # warn if any gap exceeds this
COMPLEMENT_WARN = 0.03     # warn if |mid_home + mid_away - 1.0| exceeds this


def tail_lines(path: Path, n: int) -> list[str]:
    """Return the last n lines of a file, efficiently.

    Seeks from end in 8 KB chunks until we've gathered n+1 newlines
    (or hit the start of file), then decodes and splits. Avoids
    loading the entire file."""
    lines: list[bytes] = []
    block_size = 8192
    buf = b""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        while pos > 0 and buf.count(b"\n") <= n:
            step = min(block_size, pos)
            pos -= step
            f.seek(pos)
            buf = f.read(step) + buf
    text = buf.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return [ln for ln in lines[-n:] if ln.strip()]


def parse_snapshots(lines: list[str]) -> list[dict]:
    """Parse JSONL lines into a slim dict list with only the fields
    we care about. Silently drops malformed rows."""
    out = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        yb = r.get("yes_bid_dollars")
        ya = r.get("yes_ask_dollars")
        try:
            yb_f = float(yb) if yb is not None else None
            ya_f = float(ya) if ya is not None else None
        except (TypeError, ValueError):
            yb_f = ya_f = None
        mid = (yb_f + ya_f) / 2 if yb_f is not None and ya_f is not None else None
        try:
            bid_size = float(r.get("yes_bid_size_fp") or 0)
        except (TypeError, ValueError):
            bid_size = 0.0
        try:
            ts = datetime.fromisoformat(r["ts"])
        except (KeyError, ValueError):
            continue
        out.append({
            "ts": ts,
            "ticker": r.get("ticker", ""),
            "status": r.get("status", ""),
            "mid": mid,
            "bid_size": bid_size,
        })
    return out


def fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.1f} MB"


def fmt_size_fp(v: float) -> str:
    if v >= 1000:
        return f"{v:,.0f}"
    return f"{v:.1f}"


def main() -> int:
    files = list(SNAP_DIR.glob("*.jsonl")) if SNAP_DIR.exists() else []
    if not files:
        print("No JSONL files found in data/orderbook_snapshots/.")
        return 1

    # Sort by mtime descending; take the most recently modified
    # MAX_FILES so we see everything currently being written.
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    recent_files = files[:MAX_FILES]
    newest_mtime = max(p.stat().st_mtime for p in recent_files)
    total_bytes = sum(p.stat().st_size for p in recent_files)

    print("=== Kalshi Logger Health Check ===")
    print(f"Files scanned: {len(recent_files)} of {len(files)} total "
          f"(most-recently-modified first)")
    print(f"Combined size: {fmt_bytes(total_bytes)}")
    print(f"Newest file: {recent_files[0].name}")

    snaps: list[dict] = []
    for p in recent_files:
        lines = tail_lines(p, TAIL_LINES)
        if not lines:
            continue
        snaps.extend(parse_snapshots(lines))
    if not snaps:
        print("No parseable snapshots across scanned files.")
        return 1

    now = datetime.now(timezone.utc)
    last_ts = max(s["ts"] for s in snaps)
    age_sec = (now - last_ts).total_seconds()

    warnings = 0
    if age_sec > STALENESS_WARN_SEC:
        stale_tag = "⚠"
        warnings += 1
    else:
        stale_tag = ""
    print(f"Last snapshot: {last_ts.isoformat()} ({age_sec:.0f}s ago) {stale_tag}")
    if age_sec > STALENESS_WARN_SEC:
        print(f"  ⚠ Last snapshot >{STALENESS_WARN_SEC}s ago — "
              "logger may have stopped")

    # ---- Active tickers in last RECENT_WINDOW_SEC ----
    cutoff = last_ts.timestamp() - RECENT_WINDOW_SEC
    recent = [s for s in snaps if s["ts"].timestamp() >= cutoff]
    by_ticker: dict[str, list[dict]] = defaultdict(list)
    for s in recent:
        by_ticker[s["ticker"]].append(s)

    if not by_ticker:
        print("\n  No snapshots in last 5 min.")
    else:
        print(f"\nActive tickers (last {RECENT_WINDOW_SEC // 60} min):")
        for tk in sorted(by_ticker.keys()):
            newest = max(by_ticker[tk], key=lambda s: s["ts"])
            mid_s = f"{newest['mid']:.3f}" if newest["mid"] is not None else "n/a"
            size_s = fmt_size_fp(newest["bid_size"])
            print(f"  {tk:<36s}  mid={mid_s}  "
                  f"bid_size={size_s}  status={newest['status']}")

    # ---- Cadence ----
    print("\nCadence (last 5 min per ticker):")
    for tk in sorted(by_ticker.keys()):
        tss = sorted(s["ts"] for s in by_ticker[tk])
        if len(tss) < 2:
            print(f"  {tk}: only {len(tss)} snapshot(s) in window")
            continue
        diffs = [(tss[i + 1] - tss[i]).total_seconds()
                 for i in range(len(tss) - 1)]
        med = median(diffs)
        mx = max(diffs)
        tag = "⚠" if mx > CADENCE_WARN_SEC else "✓"
        if mx > CADENCE_WARN_SEC:
            warnings += 1
        # Compact suffix — last 16 chars of ticker usually shows the team
        short = tk[-20:]
        print(f"  …{short}  median {med:5.1f}s  max {mx:5.1f}s  {tag}")

    # ---- Complement check ----
    by_event: dict[str, list[dict]] = defaultdict(list)
    for tk, rows in by_ticker.items():
        event = tk.rsplit("-", 1)[0]  # strip trailing team suffix
        newest = max(rows, key=lambda s: s["ts"])
        by_event[event].append({"ticker": tk, **newest})

    paired = {ev: rows for ev, rows in by_event.items() if len(rows) == 2}
    if paired:
        print("\nComplement check (paired tickers):")
        for ev in sorted(paired.keys()):
            a, b = paired[ev]
            if a["mid"] is None or b["mid"] is None:
                print(f"  {ev}: missing mid on one side — skipped")
                continue
            total = a["mid"] + b["mid"]
            dev = abs(total - 1.0)
            tag = "⚠" if dev > COMPLEMENT_WARN else "✓"
            if dev > COMPLEMENT_WARN:
                warnings += 1
            # Compact event name
            ev_short = ev.rsplit("-", 1)[-1]
            print(f"  {ev_short}: {a['ticker'].rsplit('-', 1)[-1]} "
                  f"{a['mid']:.3f} + {b['ticker'].rsplit('-', 1)[-1]} "
                  f"{b['mid']:.3f} = {total:.3f}  (|dev|={dev:.4f}) {tag}")

    # ---- Session summary ----
    all_tss = [s["ts"] for s in snaps]
    all_tickers = {s["ticker"] for s in snaps}
    print("\nSession summary (from tails of scanned files):")
    print(f"  snapshots in tail: {len(snaps)}")
    print(f"  distinct tickers:  {len(all_tickers)}")
    if all_tss:
        span = (max(all_tss) - min(all_tss)).total_seconds()
        print(f"  tail span: {min(all_tss).isoformat()} → "
              f"{max(all_tss).isoformat()} ({span:.0f}s)")

    print()
    if warnings > 0:
        print(f"{warnings} warning(s) emitted.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
