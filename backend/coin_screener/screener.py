"""
Main coin screening engine
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .models import (
    CoinScore,
    CoinScreenerResult,
    CoinMetrics,
    HardFilterConfig,
    ScoringWeights
)
from .filters import HardFilters
from .scoring import CoinScorer
from .data_providers import HyperliquidDataProvider, CoinGeckoDataProvider, DataCache
from hyperliquid.utils.error import ClientError

logger = logging.getLogger(__name__)


class CoinScreener:
    """
    Main cryptocurrency screening engine.

    Combines data from Hyperliquid and CoinGecko to screen and rank coins
    based on quantitative criteria.
    """

    def __init__(
        self,
        testnet: bool = True,
        coingecko_api_key: Optional[str] = None,
        top_n: int = 5,
        filter_config: Optional[HardFilterConfig] = None,
        scoring_weights: Optional[ScoringWeights] = None,
        cache_enabled: bool = True
    ):
        """
        Initialize coin screener.

        Args:
            testnet: Use Hyperliquid testnet
            coingecko_api_key: Optional CoinGecko API key
            top_n: Number of top coins to return
            filter_config: Hard filter configuration
            scoring_weights: Scoring weights configuration
            cache_enabled: Enable caching
        """
        self.testnet = testnet
        self.top_n = top_n

        # Initialize data providers
        self.hl_provider = HyperliquidDataProvider(testnet=testnet)
        self.cg_provider = CoinGeckoDataProvider(api_key=coingecko_api_key)
        self.cache = DataCache() if cache_enabled else None

        # Initialize filters and scorer
        self.filters = HardFilters(config=filter_config or HardFilterConfig())
        self.scorer = CoinScorer(weights=scoring_weights or ScoringWeights())

        # State
        self.last_screening: Optional[CoinScreenerResult] = None
        self.last_screening_time: Optional[datetime] = None

        logger.info(
            f"Initialized CoinScreener (testnet={testnet}, top_n={top_n}, "
            f"cache={'enabled' if cache_enabled else 'disabled'})"
        )

    def run_full_screening(self) -> CoinScreenerResult:
        """
        Run complete screening process.

        Steps:
        1. Get all available symbols from Hyperliquid
        2. Fetch metrics from Hyperliquid and CoinGecko
        3. Apply hard filters
        4. Score remaining coins
        5. Select top N
        6. Cache results

        Returns:
            CoinScreenerResult with selected coins
        """
        logger.info("🔍 Starting full coin screening...")

        # 1. Get available symbols
        symbols = self.hl_provider.get_available_symbols()
        logger.info(f"Found {len(symbols)} symbols on Hyperliquid")

        if not symbols:
            logger.error("No symbols found")
            return self._empty_result()

        # 2. Fetch metrics
        all_metrics = self._fetch_all_metrics(symbols)
        logger.info(f"Fetched metrics for {len(all_metrics)} coins")

        if not all_metrics:
            logger.error("No metrics fetched")
            return self._empty_result()

        # 3. Apply hard filters
        passing_coins, excluded_coins = self.filters.apply_filters(all_metrics)
        logger.info(
            f"Hard filters: {len(passing_coins)} passed, {len(excluded_coins)} excluded"
        )

        if not passing_coins:
            logger.warning("No coins passed hard filters")
            return self._empty_result(excluded_coins=excluded_coins)

        # 4. Get BTC metrics for relative strength
        btc_metrics = next((m for m in all_metrics if m.symbol == "BTC"), None)
        btc_price = btc_metrics.price if btc_metrics else None
        btc_price_7d = btc_metrics.price_7d_ago if btc_metrics else None

        # 5. Score coins
        scored_coins = self.scorer.score_coins(
            passing_coins,
            btc_price=btc_price,
            btc_price_7d=btc_price_7d
        )

        # 6. Select top N
        selected_coins = scored_coins[:self.top_n]

        logger.info(
            f"✅ Screening complete: Selected {len(selected_coins)} coins"
        )
        for i, coin in enumerate(selected_coins, 1):
            logger.info(
                f"  {i}. {coin.symbol}: {coin.score:.2f} points "
                f"(7d: {coin.factors.get('momentum_7d', 0)*100:.1f}, "
                f"vol: {coin.factors.get('volume_trend', 0)*100:.1f})"
            )

        # Create result
        now = datetime.now(timezone.utc)
        result = CoinScreenerResult(
            selected_coins=selected_coins,
            excluded_coins=excluded_coins,
            screening_timestamp=now,
            next_rebalance=self._calculate_next_rebalance(now),
            screening_type="full_rebalance"
        )

        # Cache result
        if self.cache:
            self.cache.set("last_screening", result, )
            self.cache.set("selected_coins", selected_coins)

        self.last_screening = result
        self.last_screening_time = now

        return result

    def update_scores(self) -> CoinScreenerResult:
        """
        Quick update of scores for currently selected coins.

        Faster than full screening, used for daily updates.

        Returns:
            Updated CoinScreenerResult
        """
        logger.info("📊 Updating scores for current selection...")

        # Get last screening
        last_result = self.get_cached_result()
        if not last_result or not last_result.selected_coins:
            logger.warning("No previous screening found, running full screening")
            return self.run_full_screening()

        # Get symbols from last screening
        symbols = [coin.symbol for coin in last_result.selected_coins]

        # Fetch updated metrics
        all_metrics = self._fetch_all_metrics(symbols)

        if not all_metrics:
            logger.error("Failed to fetch updated metrics")
            return last_result

        # Re-score
        btc_metrics = next((m for m in all_metrics if m.symbol == "BTC"), None)
        btc_price = btc_metrics.price if btc_metrics else None
        btc_price_7d = btc_metrics.price_7d_ago if btc_metrics else None

        scored_coins = self.scorer.score_coins(
            all_metrics,
            btc_price=btc_price,
            btc_price_7d=btc_price_7d
        )

        # Update result
        now = datetime.now(timezone.utc)
        result = CoinScreenerResult(
            selected_coins=scored_coins[:self.top_n],
            excluded_coins=last_result.excluded_coins,
            screening_timestamp=now,
            next_rebalance=last_result.next_rebalance,
            screening_type="daily_update"
        )

        # Cache
        if self.cache:
            self.cache.set("last_screening", result)
            self.cache.set("selected_coins", result.selected_coins)

        self.last_screening = result
        self.last_screening_time = now

        logger.info(f"✅ Scores updated for {len(scored_coins)} coins")

        return result

    def get_selected_coins(self, top_n: Optional[int] = None) -> List[CoinScore]:
        """
        Get currently selected coins (from cache or last screening).

        Args:
            top_n: Override number of coins to return

        Returns:
            List of CoinScore objects
        """
        n = top_n or self.top_n

        # Try cache first
        if self.cache:
            cached = self.cache.get("selected_coins", max_age_seconds=3600)
            if cached:
                logger.debug("Using cached selected coins")
                return cached[:n]

        # Use last screening
        if self.last_screening:
            return self.last_screening.selected_coins[:n]

        # No data available
        logger.warning("No selected coins available, consider running screening")
        return []

    def get_cached_result(self) -> Optional[CoinScreenerResult]:
        """Get last screening result from cache or memory"""
        if self.cache:
            cached = self.cache.get("last_screening", max_age_seconds=86400)
            if cached:
                return cached

        return self.last_screening

    def should_rebalance(self) -> bool:
        """
        Check if it's time for a full rebalance.

        Returns:
            True if rebalance is needed
        """
        last_result = self.get_cached_result()
        if not last_result:
            return True

        now = datetime.now(timezone.utc)
        return now >= last_result.next_rebalance

    def _fetch_all_metrics(self, symbols: List[str]) -> List[CoinMetrics]:
        """
        Fetch metrics for all symbols from both Hyperliquid and CoinGecko.

        Args:
            symbols: List of symbols to fetch

        Returns:
            List of CoinMetrics
        """
        metrics_list = []

        # Fetch Hyperliquid data
        logger.info(f"Fetching Hyperliquid data for {len(symbols)} symbols...")
        logger.warning("⚠️ Rate limiting severo: usando delay estesi tra le chiamate (2-3s per simbolo)")
        hl_metrics = {}
        import time
        consecutive_429 = 0  # Track consecutive 429 errors
        
        for i, symbol in enumerate(symbols):
            # Add delay between requests to avoid rate limiting
            if i > 0:
                if consecutive_429 >= 3:
                    # Se abbiamo ricevuto molti 429 consecutivi, aspettiamo più a lungo
                    wait_time = 30  # 30 secondi di pausa
                    logger.warning(f"⚠️ Molti errori 429 consecutivi ({consecutive_429}), pausa di {wait_time}s...")
                    time.sleep(wait_time)
                    consecutive_429 = 0  # Reset counter
                elif i % 10 == 0:  # Every 10 requests, add a longer delay
                    logger.info(f"Processed {i}/{len(symbols)} symbols, pausing to avoid rate limits...")
                    time.sleep(10)  # 10 second pause every 10 requests
                else:
                    time.sleep(2)  # 2 second delay between requests (aumentato da 0.5s)
            
            try:
                metrics = self.hl_provider.get_coin_metrics(symbol)
                if metrics:
                    hl_metrics[symbol] = metrics
                    consecutive_429 = 0  # Reset on success
            except ClientError as e:
                error_args = e.args[0] if e.args else None
                if isinstance(error_args, tuple) and len(error_args) > 0 and error_args[0] == 429:
                    consecutive_429 += 1
                    logger.warning(f"Rate limit (429) per {symbol} (consecutivi: {consecutive_429})")
                    # Se riceviamo 429, aspettiamo prima di continuare
                    if consecutive_429 < 3:
                        time.sleep(5)  # 5 secondi di pausa dopo un 429
                else:
                    logger.warning(f"Failed to fetch metrics for {symbol}: {e}")
            except Exception as e:
                logger.warning(f"Failed to fetch metrics for {symbol}: {e}")
                # Continue with next symbol instead of failing completely
                continue

        # Fetch CoinGecko data
        logger.info("Fetching CoinGecko market data...")
        cg_data = self.cg_provider.get_market_data(symbols)

        # Merge data
        for symbol, hl_m in hl_metrics.items():
            # Add CoinGecko data if available
            if symbol in cg_data:
                cg = cg_data[symbol]
                hl_m.market_cap_usd = cg.get("market_cap_usd", 0)
                # Use CoinGecko volume if higher quality
                if cg.get("volume_24h_usd", 0) > 0:
                    hl_m.volume_24h_usd = cg["volume_24h_usd"]

            # Mark stablecoins
            hl_m.is_stablecoin = self.cg_provider.is_stablecoin(symbol)
            hl_m.coingecko_id = self.cg_provider.get_coin_id(symbol)

            metrics_list.append(hl_m)

        return metrics_list

    def _calculate_next_rebalance(self, current_time: datetime) -> datetime:
        """
        Calculate next rebalance time (next Sunday 00:00 UTC).

        Args:
            current_time: Current timestamp

        Returns:
            Next rebalance datetime
        """
        # Days until next Sunday (0=Monday, 6=Sunday)
        days_until_sunday = (6 - current_time.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7  # If today is Sunday, schedule for next Sunday

        next_sunday = current_time + timedelta(days=days_until_sunday)
        next_rebalance = next_sunday.replace(hour=0, minute=0, second=0, microsecond=0)

        return next_rebalance

    def _empty_result(self, excluded_coins: List[str] = None) -> CoinScreenerResult:
        """Create an empty result"""
        now = datetime.now(timezone.utc)
        return CoinScreenerResult(
            selected_coins=[],
            excluded_coins=excluded_coins or [],
            screening_timestamp=now,
            next_rebalance=self._calculate_next_rebalance(now),
            screening_type="full_rebalance"
        )

    def clear_cache(self):
        """Clear all cached data"""
        if self.cache:
            count = self.cache.clear()
            logger.info(f"Cleared {count} cache files")
        self.last_screening = None
        self.last_screening_time = None
