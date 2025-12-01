# Multi-Timeframe Trend Detection System - Integration Guide

## Overview

This document describes the implementation of a two-phase multi-timeframe trend detection system that enhances the Trading Agent's coin selection and trading decision-making capabilities.

## Implementation Summary

### Phase 1: Trend Filter Enhancement for Coin Screener ✅

Enhanced the coin screening system with three new trend-based scoring factors:

1. **ADX Strength** (weight: 0.12)
   - Measures trend strength using 14-period ADX
   - Scores: 0.3 (ranging) → 0.5 (emerging) → 0.8 (strong) → 1.0 (very strong)
   - Threshold: ADX > 25 indicates strong trend

2. **EMA Alignment** (weight: 0.10)
   - Analyzes EMA20, EMA50, EMA200 alignment
   - Perfect bullish alignment (EMA20 > EMA50 > EMA200) scores 1.0
   - Checks price position relative to EMAs

3. **Donchian Position** (weight: 0.08)
   - 20-period Donchian Channel position (0-1 range)
   - Position > 0.8: Strong uptrend (score 1.0)
   - Position 0.6-0.8: Moderate uptrend (score 0.7)
   - Position 0.4-0.6: Consolidation (score 0.3)

**Total trend factors weight: 30%** of the overall coin score

### Phase 2: Real-Time Trend Confirmation Layer ✅

Implemented a multi-timeframe confirmation system that validates trend quality before each trading decision:

- **Daily timeframe**: Overall trend direction (using ADX and DI)
- **Hourly timeframe**: Momentum confirmation (using EMAs and RSI)
- **15-minute timeframe**: Entry timing (using MACD)

**Trend Quality Levels:**
- **EXCELLENT** (95% confidence): All 3 timeframes aligned
- **GOOD** (80% confidence): Daily + Hourly aligned
- **MODERATE** (65% confidence): Partial alignment
- **POOR** (40% confidence): Conflicting signals

## Files Modified/Created

### Modified Files:

1. **`backend/coin_screener/models.py`**
   - Added 9 new fields to `CoinMetrics` for trend indicators
   - Updated `ScoringWeights` with new trend factor weights
   - Modified weights to sum to 1.0 (reduced existing weights proportionally)

2. **`backend/coin_screener/data_providers/hyperliquid.py`**
   - Added `_calculate_trend_indicators()` method
   - Fetches 250 days of daily OHLCV data for EMA200
   - Calculates ADX, +DI, -DI, EMAs, and Donchian Channel
   - Integrated into `get_coin_metrics()` flow

3. **`backend/coin_screener/scoring.py`**
   - Added 3 new scoring methods:
     - `_calculate_adx_strength()`
     - `_calculate_ema_alignment()`
     - `_calculate_donchian_trend()`
   - Updated `_calculate_factors()` to include new factors
   - Updated `_composite_score()` to weight new factors

4. **`backend/coin_screener/test_screener.py`**
   - Added comprehensive unit tests for Phase 1 & 2
   - Tests for ADX scoring logic
   - Tests for EMA alignment scoring
   - Tests for Donchian position scoring
   - Tests for trend confirmation alignment

### New Files:

1. **`backend/trend_confirmation.py`** (620 lines)
   - `TrendDirection` enum (5 states)
   - `TrendQuality` enum (5 levels)
   - `TrendConfirmation` dataclass
   - `TrendConfirmationEngine` class with:
     - `confirm_trend()` - main entry point
     - `_analyze_daily()` - daily timeframe analysis
     - `_analyze_hourly()` - hourly timeframe analysis
     - `_analyze_15m()` - 15-minute timeframe analysis
     - `_calculate_alignment()` - multi-timeframe alignment
     - `_should_trade()` - trading decision logic
     - `_assess_entry_quality()` - entry timing assessment

## Academic Foundation

The implementation is based on peer-reviewed research:

1. **Jiang et al. (2022)** - Price-based indicators (EMAs, ADX) effective at daily/weekly frequencies
2. **Rohrbach et al. (2017)** - Momentum strategies exhibit higher Sharpe ratios for volatile crypto
3. **Zarattini, Pagani & Barbon (2025)** - Donchian ensemble approach achieved 1.5+ Sharpe ratio
4. **Multiple studies** - ADX > 25 threshold for strong trends in crypto markets

## Integration into main.py (NOT YET IMPLEMENTED)

To integrate Phase 2 into the main trading loop, you'll need to:

### 1. Initialize TrendConfirmationEngine

```python
from trend_confirmation import TrendConfirmationEngine

# In your initialization section
state.trend_engine = TrendConfirmationEngine(testnet=testnet)
```

### 2. Add Trend Confirmation Before Trading Decisions

```python
async def trading_cycle():
    # ... existing code ...

    for ticker in active_tickers:
        # Get coin metrics from screener (includes daily trend data)
        coin_metrics = state.screener.get_coin_metrics(ticker)

        # PHASE 2: Confirm trend before trading
        confirmation = state.trend_engine.confirm_trend(
            symbol=ticker,
            daily_metrics={
                'adx_14': coin_metrics.adx_14,
                'plus_di': coin_metrics.plus_di,
                'minus_di': coin_metrics.minus_di,
            }
        )

        # Log trend status
        logger.info(
            f"📊 {ticker} Trend: {confirmation.direction.value} "
            f"(Quality: {confirmation.quality.value}, "
            f"Confidence: {confirmation.confidence:.0%})"
        )

        # Skip if trend is not tradeable
        if not confirmation.should_trade:
            logger.info(f"⏭️ Skipping {ticker}: trend quality insufficient")
            continue

        # Skip if entry timing is poor
        if confirmation.entry_quality == "wait":
            logger.info(f"⏳ {ticker}: waiting for better entry")
            continue

        # Log entry quality
        if confirmation.entry_quality == "optimal":
            logger.info(f"✨ {ticker}: OPTIMAL entry opportunity!")

        # Proceed with existing trading logic
        # ... rest of your trading decision code ...
```

### 3. Optional: Pass Trend Info to LLM

You can enhance the LLM context with trend information:

```python
# Add to your LLM prompt
trend_context = f"""
Current Trend Analysis for {ticker}:
- Overall Direction: {confirmation.direction.value}
- Quality: {confirmation.quality.value} ({confirmation.confidence:.0%} confidence)
- Daily: {confirmation.daily_trend.value if confirmation.daily_trend else 'N/A'}
- Hourly: {confirmation.hourly_trend.value if confirmation.hourly_trend else 'N/A'}
- 15m: {confirmation.m15_trend.value if confirmation.m15_trend else 'N/A'}
- Entry Quality: {confirmation.entry_quality}
- Should Trade: {confirmation.should_trade}
"""
```

## Configuration

Add to your `main.py` configuration:

```python
CONFIG = {
    # ... existing config ...

    # Trend Filter Enhancement (Phase 1)
    "TREND_FILTER_ENABLED": True,
    "ADX_THRESHOLD": 25,
    "EMA_PERIODS": [20, 50, 200],
    "DONCHIAN_PERIODS": [10, 20, 50],

    # Trend Confirmation Layer (Phase 2)
    "TREND_CONFIRMATION_ENABLED": True,
    "MIN_TREND_CONFIDENCE": 0.6,
    "RSI_OVERBOUGHT": 70,
    "RSI_OVERSOLD": 30,
    "SKIP_POOR_ENTRY": True,  # Skip trades with entry_quality="wait"
}
```

## Testing

Run the comprehensive test suite:

```bash
cd backend/coin_screener
python test_screener.py
```

**Test Coverage:**
- ✅ ADX strength scoring (5 test cases)
- ✅ EMA alignment scoring (3 scenarios)
- ✅ Donchian position scoring (5 test cases)
- ✅ Scoring weights validation
- ✅ TrendConfirmationEngine initialization
- ✅ Multi-timeframe alignment logic (3 scenarios)

All tests passing: **11/11** ✅

## Usage Examples

### Example 1: Check Trend Quality for a Coin

```python
from trend_confirmation import TrendConfirmationEngine

engine = TrendConfirmationEngine(testnet=True)

# Check BTC trend
confirmation = engine.confirm_trend(symbol="BTC")

print(f"Direction: {confirmation.direction.value}")
print(f"Quality: {confirmation.quality.value}")
print(f"Confidence: {confirmation.confidence:.0%}")
print(f"Should Trade: {confirmation.should_trade}")
print(f"Entry Quality: {confirmation.entry_quality}")
```

### Example 2: Use Pre-computed Daily Metrics

```python
# From coin screener
coin_metrics = screener.get_coin_metrics("ETH")

# Pass daily metrics to avoid re-fetching
confirmation = engine.confirm_trend(
    symbol="ETH",
    daily_metrics={
        'adx_14': coin_metrics.adx_14,
        'plus_di': coin_metrics.plus_di,
        'minus_di': coin_metrics.minus_di,
    }
)
```

### Example 3: Filter Coins by Trend Quality

```python
# Get screened coins
selected_coins = screener.get_selected_coins()

# Filter by trend confirmation
tradeable_coins = []
for coin in selected_coins:
    confirmation = engine.confirm_trend(coin.symbol)

    if confirmation.should_trade and confirmation.entry_quality != "wait":
        tradeable_coins.append({
            'symbol': coin.symbol,
            'score': coin.score,
            'trend_quality': confirmation.quality.value,
            'trend_confidence': confirmation.confidence,
            'entry_quality': confirmation.entry_quality
        })

# Sort by confidence
tradeable_coins.sort(key=lambda x: x['trend_confidence'], reverse=True)
```

## Performance Considerations

### API Call Optimization

**Phase 1 (Coin Screener):**
- Fetches daily data once during weekly screening
- 250-day lookback for EMA200 calculation
- Cached for 24 hours

**Phase 2 (Trend Confirmation):**
- Can reuse daily metrics from Phase 1
- Fetches hourly (100 candles) and 15m (100 candles) data
- Called before each trading decision

**Rate Limit Management:**
- Daily data: ~1 API call per coin per day
- Hourly/15m data: 2 API calls per trading decision
- Consider implementing local caching for high-frequency trading

### Recommended Caching Strategy

```python
# In your state management
state.trend_cache = {}
state.trend_cache_ttl = {
    'daily': 3600,    # 1 hour
    'hourly': 300,    # 5 minutes
    '15m': 60,        # 1 minute
}
```

## Logging and Monitoring

Add these log statements to track trend system performance:

```python
# Log screening results with trend factors
logger.info(
    f"Selected: {coin.symbol} "
    f"(Score: {coin.score:.1f}, "
    f"ADX: {coin.metrics['adx_14']:.1f}, "
    f"EMA Align: {coin.factors['ema_alignment']:.2f}, "
    f"Donchian: {coin.metrics['donchian_position']:.2f})"
)

# Log trend confirmation decisions
logger.info(
    f"Trend Check {ticker}: "
    f"{confirmation.direction.value} "
    f"[{confirmation.quality.value}] "
    f"{confirmation.confidence:.0%} confidence - "
    f"{'✅ TRADE' if confirmation.should_trade else '❌ SKIP'}"
)

# Log entry quality alerts
if confirmation.entry_quality == "optimal":
    logger.warning(f"🎯 OPTIMAL ENTRY: {ticker}")
```

## Troubleshooting

### Issue: Insufficient daily data for EMA200

**Solution:** Coins with < 200 days of data will have `ema_200=None`. The scoring system handles this gracefully by using only EMA20 and EMA50.

### Issue: All coins getting neutral trend scores

**Check:**
1. Verify Hyperliquid API is returning daily data
2. Check `_calculate_trend_indicators()` is being called
3. Confirm `ta` library is installed (`pip install ta`)

### Issue: TrendConfirmationEngine always returns should_trade=False

**Check:**
1. Minimum confidence threshold (default 0.6)
2. RSI extreme conditions (overbought/oversold)
3. Trend quality (must be MODERATE or better)

## Future Enhancements

1. **Adaptive Thresholds**: Dynamically adjust ADX/RSI thresholds based on market volatility
2. **Multi-Asset Correlation**: Consider correlation between assets when selecting coins
3. **Trend Strength Score**: Add a composite "trend strength" metric combining all indicators
4. **Backtest Framework**: Implement systematic backtesting to optimize weights and thresholds
5. **Short Strategy**: Enhance Donchian scoring to better identify short opportunities
6. **Machine Learning**: Train model to predict optimal trend indicator weights

## References

1. Jiang et al. (2022) - "Trend-based forecast of cryptocurrency returns" - ScienceDirect
2. Rohrbach, Suremann & Osterrieder (2017) - University of Twente
3. Zarattini, Pagani & Barbon (2025) - "Catching Crypto Trends" - Swiss Finance Institute
4. PMC Study (2023) - "Effectiveness of RSI in Cryptocurrency Market"
5. Carnegie Mellon (2022) - "Technical Analysis in Cryptocurrency Market"

## Support

For issues or questions:
1. Check test suite: `python backend/coin_screener/test_screener.py`
2. Review log output for detailed trend analysis
3. Verify API connectivity and rate limits

---

**Implementation Status:**
- ✅ Phase 1: Trend Filter Enhancement - COMPLETE
- ✅ Phase 2: Trend Confirmation Layer - COMPLETE
- ⏳ Integration into main.py - PENDING (manual integration required)
- ⏳ Production deployment - PENDING
- ⏳ Backtesting and optimization - PENDING

**Last Updated:** 2025-12-01
**Version:** 1.0.0
