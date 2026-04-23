# Strategy 4A — Drawdown & Capital Requirements
_Generated: 2026-04-23T07:49:45.438606+00:00_
Chronologically-ordered cumulative P&L curve from all **311 S4A entries** across the **404-game Kalshi paired dataset**. Single config: lookback 180s, dip ≥ $0.08, entry $0.50-$0.75, target $0.90, stop $0.40, 100 contracts. Fees: maker on entry + target exit, taker on stop exit.

## Section 1 — Entry timeline
- Total entries: **311**
- Date range: 2026-02-20 → 2026-04-16 (56 calendar days)
- Nights with ≥1 entry: **55**
- Mean entries/active night: 5.65
- Median entries/active night: 5
- P90 entries/night: 9
- Busiest night: **2026-03-11** with **14 entries**

## Section 2 — Running cumulative P&L
- Final cumulative P&L: **$+880.84**
- Max cumulative P&L: $+920.39 at 2026-04-11
- Min cumulative P&L: $-44.70 at 2026-02-20
- **Max peak-to-trough drawdown: $326.32**
  - Peak: $+509.82 at 2026-03-21
  - Trough: $+183.50 at 2026-03-29
  - Drawdown window: 8 days

## Section 3 — Win/loss streaks
- **Longest losing streak: 7 consecutive losses** (cumulative $-185.70)
- **Longest winning streak: 10 consecutive wins** (cumulative $+216.39)
- Mean loss streak length: 1.76 (n=75 streaks)
- Mean win streak length: 2.42 (n=74 streaks)

### Streak-length distribution

| Streak length | Win streaks | Loss streaks |
|---:|---:|---:|
| 1 | 32 | 43 |
| 2 | 20 | 17 |
| 3 | 7 | 9 |
| 4 | 5 | 4 |
| 5 | 2 | 1 |
| 6 | 4 | 0 |
| 7 | 2 | 1 |
| 8 | 1 | 0 |
| 10 | 1 | 0 |

## Section 4 — Capital requirements
- Minimum starting capital to never go negative: **$44.70**
  - Computed as |min cumulative P&L| = |$-44.70|
- Recommended starting capital (×1.5 safety margin): **$67.05**

### Capital deployed per entry (entry_price × 100)

| Metric | Value |
|---|---:|
| Mean | $64.44 |
| Median | $65.51 |
| P90 | $73.68 |
| Max | $74.99 |

### Peak concurrent capital deployed

- **Peak capital at risk simultaneously: $266.78**
- Occurred at: 2026-03-12T03:02:30+00:00
- Concurrent positions at peak: 4

(Computed via sweep-line over trade entry/exit timestamps. Concurrency reflects trades with overlapping entry-to-exit windows.)

### Return on capital

- Dataset span: 56 calendar days (annualization factor ×6.518)
- Final P&L: $+880.84 → annualized ~$+5,741.21/yr
- Return on minimum capital: **12844.0%/yr** ($+5,741 / $45)
- Return on recommended capital: **8562.7%/yr** ($+5,741 / $67)

## Section 5 — Nightly P&L distribution
- Active nights: 55
- Mean nightly P&L: $+16.02
- Median nightly P&L: $+16.84
- **Worst night:** 2026-03-07 at $-148.33 (7 entries)
- **Best night:** 2026-02-21 at $+168.65 (10 entries)

### Nightly P&L histogram

| P&L bucket | Nights | % |
|---|---:|---:|
| > +$50 | 15 | 27.3% |
| +$25 to +$50 | 7 | 12.7% |
| +$0 to +$25 | 10 | 18.2% |
| -$25 to $0 | 9 | 16.4% |
| -$50 to -$25 | 8 | 14.5% |
| < -$50 | 6 | 10.9% |

