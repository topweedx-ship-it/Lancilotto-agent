# Coin Screener Module - Setup Guide

## Quick Start

### 1. Enable Screening

Edit `main.py` CONFIG:

```python
CONFIG = {
    ...
    "SCREENING_ENABLED": True,  # ← Set to True
    "TOP_N_COINS": 15,          # Number of coins to trade
    ...
}
```

### 2. (Optional) Add CoinGecko API Key

Edit `.env`:

```bash
COINGECKO_API_KEY=your_api_key_here
```

This is optional but recommended for higher rate limits (free tier: 10-50 req/min).

### 3. Run Database Migration

The migration runs automatically on first initialization when `SCREENING_ENABLED=True`.

To run manually:

```bash
python -c "
from coin_screener.db_migration import run_migration
from db_utils import get_connection
with get_connection() as conn:
    run_migration(conn)
"
```

### 4. Test the Screener

```bash
# Run example script
python example_screener.py

# Or run unit tests
cd coin_screener
python test_screener.py
```

### 5. Start the Bot

```bash
python main.py
```

The bot will now:
- Select coins dynamically via screening
- Rebalance every Sunday
- Update scores daily
- Fall back to BTC/ETH/SOL if screening fails

## How It Works

### Screening Cycle

```
Sunday 00:00 UTC → Full Rebalance
    ↓
Run hard filters (volume, market cap, etc.)
    ↓
Score coins (momentum, volume, volatility, etc.)
    ↓
Select top N coins
    ↓
Daily 00:00 UTC → Update scores for selected coins
    ↓
Every 3 minutes → Use cached selection for trading
```

### Hard Filters (Exclusion Criteria)

Coins must meet ALL these requirements:

- ✅ Volume 24h ≥ $50M
- ✅ Market Cap ≥ $250M
- ✅ Listed ≥ 30 days
- ✅ Open Interest ≥ $10M
- ✅ Bid-ask spread ≤ 0.5%
- ✅ Not a stablecoin

### Scoring Factors (0-100 points)

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| Momentum 7d | 20% | Short-term price performance |
| Momentum 30d | 15% | Medium-term price performance |
| Volatility Regime | 15% | ATR expanding (trading opportunities) |
| Volume Trend | 15% | Recent vs historical volume |
| OI Trend | 10% | Open interest growth |
| Funding Stability | 10% | Balanced funding rate |
| Liquidity | 10% | Tight bid-ask spread |
| Relative Strength | 5% | Outperformance vs BTC |

## Configuration Options

### Basic Config (main.py)

```python
CONFIG = {
    "SCREENING_ENABLED": True,
    "TOP_N_COINS": 15,                       # How many to select
    "FALLBACK_TICKERS": ["BTC", "ETH", "SOL"], # Used if screening fails
    ...
}
```

### Advanced Config (Custom Filters)

```python
from coin_screener import CoinScreener, HardFilterConfig, ScoringWeights

# Stricter filters
filters = HardFilterConfig(
    min_volume_24h_usd=100_000_000,  # $100M
    min_market_cap_usd=1_000_000_000, # $1B
    min_days_listed=60,
    max_spread_pct=0.3
)

# Custom weights (momentum-focused)
weights = ScoringWeights(
    momentum_7d=0.30,
    momentum_30d=0.20,
    volatility_regime=0.10,
    volume_trend=0.15,
    oi_trend=0.10,
    funding_stability=0.05,
    liquidity_score=0.05,
    relative_strength=0.05
)

# In BotState.initialize()
self.screener = CoinScreener(
    testnet=CONFIG["TESTNET"],
    filter_config=filters,
    scoring_weights=weights,
    top_n=CONFIG["TOP_N_COINS"]
)
```

## Monitoring

### Check Current Selection

```sql
-- Latest screening
SELECT created_at, screening_type, selected_coins
FROM coin_screenings
ORDER BY created_at DESC
LIMIT 1;

-- Top performing coins (last 30 days)
SELECT symbol, COUNT(*) as selections, AVG(score) as avg_score
FROM coin_scores_history
WHERE rank <= 5
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY symbol
ORDER BY selections DESC;
```

### Logs

Look for these log messages:

```
🔄 Rebalance settimanale: eseguo screening completo...
✅ Screening complete: Selected 5 coins
  1. BTC: 87.42 points
  2. ETH: 82.15 points
  ...
🎯 Trading su: BTC, ETH, SOL, AVAX, LINK
```

### Cache Location

`.cache/screener/` - stores screening results for 1 hour

Clear cache:
```python
screener.clear_cache()
```

## Troubleshooting

### Issue: No coins pass filters

**Solution:** Lower filter thresholds

```python
HardFilterConfig(
    min_volume_24h_usd=20_000_000,   # Lower from $50M
    min_market_cap_usd=100_000_000,  # Lower from $250M
    min_days_listed=15,               # Lower from 30
)
```

### Issue: CoinGecko rate limit (429 error)

**Symptoms:** `CoinGecko rate limit hit, waiting...`

**Solutions:**
1. Get a free API key from CoinGecko
2. Add to `.env`: `COINGECKO_API_KEY=xxx`
3. The system auto-retries with backoff

### Issue: Screening very slow

**Normal behavior:**
- First run: 30-60 seconds (fetching all data)
- Subsequent runs: 5-10 seconds (using cache)

**Speed up:**
- Reduce `TOP_N_COINS` in testing
- Enable cache (default)
- Use CoinGecko API key

### Issue: Missing CoinGecko mapping

**Symptom:** Some coins excluded, "No CoinGecko ID mapping" in logs

**Solution:** Add mapping manually

```python
# In example_screener.py or main.py initialization
screener.cg_provider.add_symbol_mapping("SYMBOL", "coingecko-id")

# Example:
screener.cg_provider.add_symbol_mapping("WIF", "dogwifcoin")
```

Find CoinGecko IDs at: https://www.coingecko.com/

### Issue: Testnet has few coins

**Expected:** Hyperliquid testnet has ~10-20 coins vs 100+ on mainnet

**Solution:**
- This is normal
- For full testing, use mainnet (set `TESTNET=False`)
- Or lower filter thresholds for testnet

## Database Schema

### coin_screenings
```sql
id                BIGSERIAL PRIMARY KEY
created_at        TIMESTAMPTZ
screening_type    TEXT          -- 'full_rebalance' | 'daily_update'
selected_coins    JSONB         -- Array of selected CoinScore
excluded_coins    JSONB         -- Array of excluded symbols
raw_scores        JSONB         -- Full score data
next_rebalance    TIMESTAMPTZ
```

### coin_scores_history
```sql
id            BIGSERIAL PRIMARY KEY
created_at    TIMESTAMPTZ
screening_id  BIGINT
symbol        TEXT
score         NUMERIC(5,2)
rank          INTEGER
factors       JSONB      -- Breakdown of scoring factors
metrics       JSONB      -- Raw coin metrics
```

### coin_metrics_snapshots
```sql
id                   BIGSERIAL PRIMARY KEY
created_at           TIMESTAMPTZ
symbol               TEXT
price                NUMERIC
volume_24h_usd       NUMERIC
market_cap_usd       NUMERIC
open_interest_usd    NUMERIC
funding_rate         NUMERIC
spread_pct           NUMERIC
days_listed          INTEGER
raw_data             JSONB
```

## API Reference

### CoinScreener

```python
screener = CoinScreener(
    testnet=True,
    coingecko_api_key=None,
    top_n=15,
    filter_config=None,
    scoring_weights=None,
    cache_enabled=True
)

# Full screening
result = screener.run_full_screening()

# Quick update
result = screener.update_scores()

# Get cached
coins = screener.get_selected_coins(top_n=15)

# Check rebalance
if screener.should_rebalance():
    screener.run_full_screening()
```

### CoinScore

```python
coin = result.selected_coins[0]

coin.symbol        # "BTC"
coin.score         # 87.42
coin.rank          # 1
coin.factors       # {"momentum_7d": 0.85, ...}
coin.metrics       # {"price": 50000, "volume_24h_usd": 1e9, ...}
coin.last_updated  # datetime
```

## Performance Tips

1. **Use cache**: Keep `cache_enabled=True` (default)
2. **Optimize top_n**: Only select coins you'll trade (e.g., 3-5)
3. **Use API key**: Get CoinGecko API key for better rate limits
4. **Testnet vs Mainnet**: Testnet has fewer coins but faster testing

## Next Steps

1. ✅ Enable screening in main.py
2. ✅ Run example_screener.py to test
3. ✅ Monitor first few runs via logs
4. ✅ Query database to see results
5. ✅ Adjust filters/weights based on your strategy
6. ✅ Set up monitoring alerts (optional)

## Support

- 📖 Full docs: `coin_screener/README.md`
- 🧪 Tests: `coin_screener/test_screener.py`
- 💡 Example: `example_screener.py`
- 🐛 Issues: Check logs and database tables

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│            Main Trading Bot (main.py)           │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│           CoinScreener (screener.py)            │
│  ┌───────────────────────────────────────────┐  │
│  │  1. HyperliquidDataProvider               │  │
│  │     ↓ (prices, volume, ATR, spread)       │  │
│  │  2. CoinGeckoDataProvider                 │  │
│  │     ↓ (market cap, volume 24h)            │  │
│  │  3. HardFilters (filters.py)              │  │
│  │     ↓ (exclude unsuitable coins)          │  │
│  │  4. CoinScorer (scoring.py)               │  │
│  │     ↓ (score 0-100 per coin)              │  │
│  │  5. Select Top N                          │  │
│  │     ↓                                      │  │
│  │  6. DataCache + Database                  │  │
│  └───────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
         [BTC, ETH, SOL, ...]
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│    Trading Cycle (analyze → decide → execute)   │
└─────────────────────────────────────────────────┘
```
