# NBAgent-Live — Research Log

## 2026-04-16 — Pilot analysis on 2024-25 regular season (session handoff)

**Data:** 1,230 games, 60,590 minute-by-minute score snapshots.
**WP model:** Stern-style Brownian bridge (σ²_final = 170, HCA = 3.5).

### Findings

**Opportunity frequency (bilateral dip rates, tradeable window sec_rem ≥ 60s):**

| Threshold | All games | Final margin ≤10 | Final margin ≤5 | OT games |
|-----------|-----------|------------------|-----------------|----------|
| <0.20     | 30.0%     | 42.5% (262)      | 48.9% (151)     | 63.3%    |
| <0.15     | 21.0%     | 30.8% (190)      | 34.0% (105)     | 53.3%    |
| <0.10     | 12.0%     | 18.5% (114)      | 20.1% (62)      | 41.7%    |

**Timing separation:** In bilateral <0.20 games, median dip separation = 23 min of game clock; 98% ≥5 min apart. Sequential entry viable.

**At-moment calibration (Stern model):** Teams priced at ~10% WP by Stern actually win ~21% of the time — a stable +9-10pp residual across time-remaining cuts, consistent with NBA having fatter tails than Brownian bridge predicts (fouling strategy, 3-point comebacks). Residual is against **my** model; measuring against Kalshi requires Kalshi price data.

**Kalshi ≈ ESPN WP evidence (2 data points, 4/15 GSW-LAC Play-In):**
- At 72-74: ESPN 29.7% / Kalshi 30% (Δ 0.3pp)
- At 114-115: ESPN 33.2% / Kalshi 34% (Δ 0.8pp)

Tight tracking. If this generalizes, **ESPN's WP timeseries becomes a usable historical proxy for Kalshi prices**, and the Stern residual likely represents real edge against Kalshi pricing too.

### Three candidate strategies

1. **Bilateral convergence** — buy both sides cheap (e.g. $0.15 each), guaranteed $0.70 profit. Mechanical edge, liquidity-dependent.
2. **Single-side mean-reversion** — buy a team at low price, hold to resolution. Model-dependent; needs Kalshi price data to validate.
3. **Active management** — buy cheap, sell on swing-back. Sidesteps calibration — profits from volatility regardless of direction.

### Open questions / next steps

1. **Kalshi live logging (in progress).** Phase 1 of this project. Highest priority — data can only be captured going forward.
2. **ESPN PBP + WP ingest.** Better foundation than minute-level. See Phase 2.
3. **Pre-game spread integration.** Remove survivorship bias in competitive-game filter.
4. **Multi-season backfill.** Confirm stability (2014-2023 data available).
5. **Cold-model probe.** Check whether residual survives a properly empirical WP model.
