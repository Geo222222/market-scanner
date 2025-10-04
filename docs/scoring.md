# Scoring & Manipulation Signals

## Weight Presets
Each profile feeds the scoring function (`core.scoring.score`) with different weights. Positive rows add to the score, while rows labelled "Penalty" subtract.

| Component | Scalp | Swing | News | Notes |
|-----------|-------|-------|------|-------|
| Liquidity (log quote vol) | 4.0 | 2.5 | 3.0 | Rewards deep traded books |
| Liquidity (log top-5 depth) | 3.5 | 2.5 | 2.0 | Log-scaling avoids mega caps dominating |
| Volatility (ATR%) | 1.2 | 1.8 | 2.2 | Prefers instruments with exploitable range |
| Momentum (ret_15) | 1.5 | 2.2 | 2.8 | Medium-term drift |
| Momentum (ret_1) | 1.0 | 0.8 | 1.5 | Short-term continuation |
| Cost penalty (spread bps) | 3.0 | 2.0 | 2.2 | Subtracted from score |
| Cost penalty (slippage bps) | 2.5 | 1.5 | 1.8 | Subtracted from score |
| Carry bonus (funding) | 0.5 | 0.8 | 0.3 | Favourable funding (sign-adjusted) |
| Carry bonus (basis) | 0.3 | 0.6 | 0.2 | Negative basis preferred |
| Structure bonus (volume z-score) | 1.2 | 1.0 | 1.5 | Rewards live liquidity surges |
| Structure bonus (price velocity) | 0.8 | 1.0 | 1.4 | Prefers strong tape for breakout/news |
| Structure penalty (order-flow imbalance) | 3.5 | 2.5 | 2.8 | Penalises dominant one-sided books |
| Structure penalty (volatility regime) | 1.4 | 1.6 | 1.2 | Penalises sudden regime shifts (|ratio-1|) |
| Structure penalty (anomaly score / 10) | 0.7 | 0.6 | 0.8 | Penalises pump/dump & wash-trading signals |

Hard filters still apply:

- `qvol_usdt < SCANNER_MIN_QVOL_USDT`
- `spread_bps > SCANNER_MAX_SPREAD_BPS`

Failing either drops the symbol (`score = -1e6`).

### Manipulation Penalty
If `manip_score` is present, the final score is reduced by `0.4 x manip_score`. High-risk books therefore slide down the ranking even before explicit filtering.

## Manipulation Signals
`manip.detector.detect_manipulation` now combines depth heuristics with microstructure analytics:

1. **Rule Triggers**
   - `spoofing_depth_imbalance`: top-5 depth skew > 65% with a large opposing wall.
   - `liquidity_wall`: top level > 55% of book and larger than configured notional.
   - `liquidity_vacuum`: combined top-5 depth < 1.5 x configured notional.
   - `scam_wick`: last candle range > 3 x ATR.
   - `oi_price_divergence`: open interest +5% while price drops >0.8% over 15 bars.
   - `funding_price_divergence`: funding sign contradicts short-term momentum.
   - `post_surge_reversal`: momentum reverses immediately after a high-volume surge (pump/dump signature).
   - `wash_trade_volume`: outsized volume spike with thin depth (wash-trading footprint).

2. **Lightweight Logistic Model**
   - Features: absolute depth imbalance, wall ratio, wick/ATR ratio, positive OI delta, funding magnitude, depth vacuum, volume z-score, price velocity, anomaly score.
   - Linear weights convert to a probability in [0, 1]; scaled to [0, 100] and compared with rule severity totals.

The higher of rule-based severity and logistic probability becomes `manip_score`. Flags are emitted for every rule that trips. The state store keeps the previous open interest per symbol so deltas can be measured cycle-to-cycle.

### Using the Score
- `/rankings` exposes `max_manip_score` and `exclude_flags` filters.
- `/opportunities` folds the penalty into confidence (`confidence -= 0.6 x manip_score` plus additional structure penalties).
- The panel highlights any flagged symbol with colour-coded badges.

This setup is intentionally conservative: a few red flags are enough to demote entries, but clean books retain their base score with a zero manipulation penalty.
