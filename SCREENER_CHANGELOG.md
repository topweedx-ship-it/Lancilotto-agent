# Coin Screener Module - Changelog

## [1.1.0] - 2025-12-02

### Added
- **Smart Rotation Logic**: Implemented a batch-based rotation system (`ANALYSIS_BATCH_SIZE=5`) to cycle through `TOP_N_COINS` (increased to 20). This ensures the AI analyzes a diverse set of coins over time without exceeding token limits or rate limits.
- **Phased Trading Cycle**: Split the trading logic into two distinct phases:
    - **Management Phase**: Analyzes *only* currently open positions to decide on CLOSE or HOLD.
    - **Scouting Phase**: Analyzes *only* the current batch of candidate coins to decide on OPEN.
- **Duplicate Trade Prevention**: Added explicit checks in `trading_engine.py` to block opening new positions if a position for that symbol already exists.
- **Cycle ID**: Introduced `cycle_id` (e.g., `manage_20251202_...`, `scout_20251202_...`) to uniquely identify and group operations within a single execution cycle.

### Changed
- **Configuration Defaults**: Increased `TOP_N_COINS` from 15 to 20.
- **Dashboard**: Updated frontend to display `cycle_id` in the Decision History table.
- **Logging**: Enhanced logging to clearly distinguish between Management and Scouting phases.

## [1.0.0] - 2025-12-01

### Added
- **Rate Limiting Optimization**: Implemented batch fetching for prices and metrics to prevent 429 errors from Hyperliquid API.
- **Data Providers**: Added `get_all_prices()` and optimized `get_coin_metrics()` to use single OHLCV fetch.

## [0.1.0] - 2025-11-26

### Added
- Initial implementation of Coin Screener module.
- Hard filters (volume, market cap, etc.).
- Scoring system (momentum, volatility, volume, etc.).
- Database integration and migration.
- Caching system.
