# Resolved Roadmap

## 2026-04-16 — Phase 0: Repo bootstrap
Created NBAgent-Live repo structure: logger/, data/orderbook_snapshots/, docs/, .github/workflows/. Bootstrapped CLAUDE.md, README.md, RESEARCH_LOG.md seed.

## 2026-04-16 — Phase 1: Kalshi orderbook logger
Implemented `logger/kalshi_logger.py` — long-lived polling process that auto-discovers today's NBA game markets and logs orderbook snapshots every 30s to `data/orderbook_snapshots/{date}.jsonl`. Scheduled via `kalshi_logger.yml` in three daily blocks (morning, midday, evening) with self-termination on idle. Market data endpoints unauthenticated — no Kalshi account required.

## 2026-04-16 — Phase 1 fix: per-game market discovery filter

First verification of Phase 0+1 revealed the `discover_nba_game_markets` filter silently rejected every real per-game market. Root cause: `close_ts` for Kalshi playoff markets is set to the series-conclusion buffer (~2 weeks out), so the "close within 36h" window never matched. Replaced with a ticker-prefix date parser (`KXNBAGAME-YYMMMDD...` → game date in ET) accepting ±1 day of today ET. Phase 1 remains *implemented but unverified* — awaiting a first successful production block with snapshots committed before promoting to *confirmed working*.
