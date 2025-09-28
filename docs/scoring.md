# Scoring & Manipulation Signals

## Weight Presets
Each profile feeds the scoring function (`core.scoring.score`) with different weights:

| Component | Scalp | Swing | News |
|-----------|-------|-------|------|
| Liquidity (log quote vol) | 4.0 | 2.5 | 3.0 |
| Liquidity (log top-5 depth) | 3.5 | 2.5 | 2.0 |
| Volatility (ATR%) | 1.2 | 1.8 | 2.2 |
| Momentum (ret_15) | 1.5 | 2.2 | 2.8 |
| Momentum (ret_1) | 1.0 | 0.8 | 1.5 |
| Cost penalty (spread bps) | 3.0 | 2.0 | 2.2 |
| Cost penalty (slippage bps) | 2.5 | 1.5 | 1.8 |
| Carry bonus (funding) | 0.5 | 0.8 | 0.3 |
| Carry bonus (basis) | 0.3 | 0.6 | 0.2 |

Scores are logarithmic on liquidity/depth, linear on ATR/momentum, and subtract cost penalties. Carry terms can be disabled globally (`SCANNER_INCLUDE_CARRY=false`) or per-request (`include_carry=false`).

### Hard Filters
- `qvol_usdt < SCANNER_MIN_QVOL_USDT`
- `spread_bps > SCANNER_MAX_SPREAD_BPS`

Failing either drops the symbol (`score = -1e6`).

### Manipulation Penalty
If `manip_score` is present, the final score is reduced by `0.4 × manip_score`. High-risk books therefore slide down the ranking even before explicit filtering.

## Manipulation Signals
`manip.detector.detect_manipulation` combines:

1. **Rule Triggers**
   - `spoofing_depth_imbalance`: top-5 depth skew > 65% with a large opposing wall.
   - `liquidity_wall`: top level > 55% of book and larger than configured notional.
   - `liquidity_vacuum`: combined top-5 depth < 1.5 × configured notional.
   - `scam_wick`: last candle range > 3 × ATR.
   - `oi_price_divergence`: open interest +5% while price drops >0.8% over 15 bars.
   - `funding_price_divergence`: funding sign contradicts short-term momentum.

2. **Lightweight Logistic Model**
   - Features: absolute depth imbalance, wall ratio, wick/ATR ratio, positive OI delta, funding magnitude, and depth vacuum.
   - Linear weights convert to a probability in [0, 1]; scaled to [0, 100] and compared with rule severity totals.

The higher of rule-based severity and logistic probability becomes `manip_score`. Flags are emitted for every rule that trips. The state store keeps the previous open interest per symbol so deltas can be measured cycle-to-cycle.

### Using the Score
- `/rankings` exposes `max_manip_score` and `exclude_flags` filters.
- `/opportunities` folds the penalty into confidence (`confidence -= 0.6 × manip_score`).
- The panel highlights any flagged symbol with colour-coded badges.

This setup is intentionally conservative: a few red flags are enough to demote entries, but clean books retain their base score with a zero manipulation penalty.
