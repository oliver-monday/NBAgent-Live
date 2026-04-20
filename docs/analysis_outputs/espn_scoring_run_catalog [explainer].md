This is a genuinely important dataset. Let me work through what it actually tells us because there are several findings that reframe how Strategy 3 should work, and one that's more significant than the synthesis section credits it for.

**The headline finding is Table 7, and it's a clean kill on the timeout-as-signal hypothesis.** Runs followed by timeouts recover at 51%; runs without timeouts recover at 53%. The delta is -2pp in the wrong direction. At n=6,210 this isn't noise — timeouts don't help recovery. Runs reverse (or don't) based on game dynamics that are independent of whether a coach calls timeout. The timeout is confirmed as an *execution window* (depth, spread — per the earlier analysis), not a *directional signal*. That distinction is now settled.

**The max recovery number is the one to stare at.** Table 3: 89% of runs produce *some* positive recovery within 5 minutes, with a mean of +0.12 WP and a median of +0.084. That's enormous for Strategy 3's thesis. It says: after almost any scoring run, the trailing team bounces back at least somewhat. The problem is the *fixed checkpoint* measurement — at 3 minutes, recovery is only 52% positive. The bounce happens, but it doesn't happen on a predictable clock. It happens at a median of 138 seconds to max, but with high variance.

This maps directly to Strategy 3's operating model. You're not entering a position with a 3-minute exit timer — you're entering when price crosses a threshold and exiting when it crosses back. The 89% max-recovery rate says the cross-back happens the vast majority of the time; it just doesn't happen at a fixed interval. The round-trip framework we already have (enter at 0.40, exit at 0.50) is the right structure. The new information is that the underlying game pattern producing those round-trips has an 89% base rate.

**The favorite/underdog asymmetry exists but it's thinner than I predicted.** Table 4: favorites recover at 54% vs underdogs at 50% at the 3-minute checkpoint. That's real but not dramatic. Tables 9 and 10 tell a more interesting story though, and the synthesis undersells it. Look at the recovery *rates* across thresholds:

At the < 0.35 threshold: favorites recover above 0.50 in 76% of games, underdogs in 73%. At < 0.25: favorites 60%, underdogs 54%. The gap widens at deeper dips — favorites are 6pp more likely to recover from extreme dips than underdogs. That's not a huge edge, but it's consistent and directional and it compounds with the prior-anchoring mechanism on the market side.

More importantly, look at the *speed*: favorites who dip below 0.35 recover in a median of 6.0 minutes vs underdogs at 7.6 minutes. Below 0.30: 7.9 vs 9.3 minutes. Favorites recover about 1.5 minutes faster at every threshold. For a swing trade, faster recovery means shorter hold time, which means less exposure to adverse game events.

**Table 8 is the prior-degradation roadmap.** Underdogs leading at end of Q1 win only 54% of the time — barely above coin flip. By halftime it's 63%, end of Q3 it's 73%, 6:00 Q4 it's 79%. The prior takes roughly a full half of basketball to dissolve. That Q1-to-halftime window (54% → 63%) is where the market should be most dislocated from game reality — the prior is still dominant but the game state is increasingly real. That's exactly where Strategy 3's operating window should be richest.

**Table 5 (period split) confirms this indirectly.** Q1 runs have the highest recovery rate at 59% positive. Q4 has the lowest at 44%. Early-game runs reverse more reliably because the prior reasserts itself. Late-game runs are more decisive — the team on a Q4 run is more likely to be genuinely pulling away. This is useful for entry-rule design: be more willing to fade runs in Q1/Q2, more cautious in Q4.

**Table 6 (magnitude split) has a counterintuitive finding.** Bigger runs don't produce better recovery — the 13+ point run bucket recovers at only 43%, the worst of any bucket. The 6-7 bucket is the best at 53%. This means the entry rule should *not* wait for massive runs. A moderate 6-7 point run is the sweet spot: big enough to move the market meaningfully, small enough that the trailing team is likely to respond.

**Where this leaves Strategy 3's entry rule:**

The data points toward a rule that's simpler than the timeout-triggered framework we were exploring but more nuanced than pure price-threshold:

The core signal remains price-based: enter when a team's contract dips below the entry threshold (0.40 on Kalshi). The contextual refinements from this analysis are:

First, favor positions on the pre-game favorite when they dip. They recover 6pp more often and 1.5 minutes faster. This is not the killed "favorite-side to resolution" variant — it's a swing-trade preference for which side to enter, with the same exit discipline.

Second, earlier in the game is better. Q1/Q2 runs reverse more reliably than Q3/Q4. The prior is your tailwind early; it's dissolved by late game.

Third, moderate runs (6-7 points) are the sweet spot. Don't wait for a blowout-level run — those are more likely to be genuine separation.

Fourth, timeouts are execution windows, not entry signals. When a timeout happens to coincide with your price threshold, take advantage of the 2.3× depth and $0.01 spread. When it doesn't, enter anyway — the recovery pattern is identical.

**Recommended next steps:**

This analysis exhausts what ESPN-scale data can tell us about game patterns. The remaining questions are all market-price questions that require Kalshi data: does the 89% max-recovery rate in ESPN WP translate to actual Kalshi price round-trips? Does the favorite asymmetry survive the market's compression? Those are Phase 3B questions answered by accumulating toward 10/10 competitive games.