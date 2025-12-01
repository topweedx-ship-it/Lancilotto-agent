"""
Hyperliquid data provider for coin screening
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
import pandas as pd
import ta

from hyperliquid.info import Info
from hyperliquid.utils import constants

from ..models import CoinMetrics

logger = logging.getLogger(__name__)


from hyperliquid.utils.error import ClientError
import time

# Import helper per inizializzazione con retry
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
try:
    from hyperliquid_utils import init_info_with_retry
except ImportError:
    # Fallback se non trovato
    def init_info_with_retry(base_url: str, skip_ws: bool = True, max_retries: int = 5):
        retry_delay = 3
        for attempt in range(max_retries):
            try:
                return Info(base_url, skip_ws=skip_ws)
            except ClientError as e:
                error_args = e.args[0] if e.args else None
                if isinstance(error_args, tuple) and len(error_args) > 0 and error_args[0] == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limit (429) durante inizializzazione Info, retry in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Errore durante inizializzazione Info: {e}, retry in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                raise
        raise RuntimeError("Failed to initialize Info after all retries")

class HyperliquidDataProvider:
    """Fetch market data from Hyperliquid"""

    def __init__(self, testnet: bool = True):
        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        # Inizializza Info con retry logic per gestire rate limiting
        self.info = init_info_with_retry(base_url, skip_ws=True)
        self.testnet = testnet
        logger.info(f"Initialized HyperliquidDataProvider ({'testnet' if testnet else 'mainnet'})")
    

    def _retry_api_call(self, func, *args, max_retries=5, **kwargs):
        """Helper to retry API calls on rate limit"""
        retry_delay = 3  # seconds
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                error_args = e.args[0] if e.args else None
                if isinstance(error_args, tuple) and len(error_args) > 0 and error_args[0] == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 3, 6, 12, 24, 48s
                        logger.warning(f"Rate limit (429) in data provider, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                # Se non è 429 o abbiamo esaurito i retry, loggiamo e rilanciamo
                logger.error(f"API Error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in API call: {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                raise
        return None

    def get_all_prices(self) -> Dict[str, float]:
        """Fetch current prices for all symbols once."""
        try:
            mids = self._retry_api_call(self.info.all_mids)
            return {k: float(v) for k, v in mids.items()}
        except Exception as e:
            logger.error(f"Error fetching all prices: {e}")
            return {}

    def get_available_symbols(self) -> List[str]:
        """
        Get list of all available trading symbols.
        
        Returns:
            List of symbol strings (e.g., ['BTC', 'ETH', 'SOL'])
        """
        try:
            meta = self._retry_api_call(self.info.meta)
            symbols = [asset['name'] for asset in meta['universe']]
            logger.info(f"Found {len(symbols)} available symbols on Hyperliquid")
            return symbols
        except Exception as e:
            logger.error(f"Error fetching available symbols: {e}")
            return []

    def get_coin_metrics(self, symbol: str, current_price: Optional[float] = None) -> Optional[CoinMetrics]:
        """
        Fetch comprehensive metrics for a single coin.

        Args:
            symbol: Coin symbol (e.g., 'BTC')
            current_price: Optional pre-fetched current price

        Returns:
            CoinMetrics object or None if error
        """
        try:
            # Get current price if not provided
            if current_price is None:
                mids = self._retry_api_call(self.info.all_mids)
                if symbol not in mids:
                    logger.warning(f"Symbol {symbol} not found in mids")
                    return None
                current_price = float(mids[symbol])

            # Get orderbook for spread calculation
            spread_pct = self._calculate_spread(symbol)

            # Fetch OHLCV data ONCE for all metrics
            # 250 candles covers:
            # - Trend indicators (EMA200)
            # - ATR (40)
            # - 30d/7d avg volume
            # - 30d/7d price change
            df = self._fetch_ohlcv(symbol, interval="1d", limit=250)
            
            if df is None or df.empty:
                logger.warning(f"No OHLCV data for {symbol}")
                return None

            # Get historical prices for momentum
            price_7d = self._get_historical_price_from_df(df, days=7)
            price_30d = self._get_historical_price_from_df(df, days=30)

            # Get volume metrics
            volume_24h = self._get_24h_volume_from_df(df, current_price)
            volume_7d_avg = self._get_avg_volume_from_df(df, days=7)
            volume_30d_avg = self._get_avg_volume_from_df(df, days=30)

            # Get ATR for volatility
            atr_14, atr_sma_20 = self._calculate_atr_metrics_from_df(df)

            # Get trend indicators (Phase 1 enhancement)
            trend_indicators = self._calculate_trend_indicators_from_df(df)

            # Get funding rate (placeholder for now)
            funding_rate = 0.0  # Will be implemented if API available

            # Open interest (placeholder - Hyperliquid doesn't expose this easily)
            open_interest_usd = 0.0
            oi_7d_ago = 0.0

            # Calculate days listed (estimate from available candle data)
            days_listed = len(df)

            # Note: market_cap needs external data (CoinGecko)
            # For now, use a placeholder that will be filled by CoinGecko provider
            market_cap_usd = 0.0

            metrics = CoinMetrics(
                symbol=symbol,
                price=current_price,
                volume_24h_usd=volume_24h,
                market_cap_usd=market_cap_usd,  # Will be filled by CoinGecko
                open_interest_usd=open_interest_usd,
                funding_rate=funding_rate,
                spread_pct=spread_pct,
                days_listed=days_listed,
                price_7d_ago=price_7d,
                price_30d_ago=price_30d,
                volume_7d_avg=volume_7d_avg,
                volume_30d_avg=volume_30d_avg,
                oi_7d_ago=oi_7d_ago,
                atr_14=atr_14,
                atr_sma_20=atr_sma_20,
                # Add trend indicators
                adx_14=trend_indicators.get('adx_14'),
                plus_di=trend_indicators.get('plus_di'),
                minus_di=trend_indicators.get('minus_di'),
                ema_20=trend_indicators.get('ema_20'),
                ema_50=trend_indicators.get('ema_50'),
                ema_200=trend_indicators.get('ema_200'),
                donchian_upper_20=trend_indicators.get('donchian_upper_20'),
                donchian_lower_20=trend_indicators.get('donchian_lower_20'),
                donchian_position=trend_indicators.get('donchian_position')
            )

            return metrics

        except Exception as e:
            logger.error(f"Error fetching metrics for {symbol}: {e}")
            return None

    def _calculate_spread(self, symbol: str) -> float:
        """Calculate bid-ask spread percentage"""
        try:
            orderbook = self._retry_api_call(self.info.l2_snapshot, symbol)
            if not orderbook or "levels" not in orderbook:
                return 0.5  # Default to max allowed

            bids = orderbook["levels"][0]
            asks = orderbook["levels"][1]

            if not bids or not asks:
                return 0.5

            best_bid = float(bids[0]["px"])
            best_ask = float(asks[0]["px"])

            if best_bid <= 0:
                return 0.5

            spread_pct = ((best_ask - best_bid) / best_bid) * 100
            return spread_pct

        except Exception as e:
            logger.debug(f"Error calculating spread for {symbol}: {e}")
            return 0.5

    def _fetch_ohlcv(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Hyperliquid.

        Args:
            symbol: Asset symbol
            interval: Candle interval (e.g., '1d', '1h')
            limit: Number of candles

        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            interval_to_ms = {
                "1m": 60_000,
                "5m": 5 * 60_000,
                "15m": 15 * 60_000,
                "1h": 60 * 60_000,
                "4h": 4 * 60 * 60_000,
                "1d": 24 * 60 * 60_000,
            }

            if interval not in interval_to_ms:
                logger.error(f"Invalid interval: {interval}")
                return None

            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            step_ms = interval_to_ms[interval]
            start_ms = now_ms - limit * step_ms

            ohlcv_data = self._retry_api_call(
                self.info.candles_snapshot,
                name=symbol,
                interval=interval,
                startTime=start_ms,
                endTime=now_ms,
            )

            if not ohlcv_data:
                return None

            df = pd.DataFrame(ohlcv_data)
            df["timestamp"] = pd.to_datetime(df["t"], unit="ms", utc=True)

            df = df[["timestamp", "o", "h", "l", "c", "v"]].copy()
            df.rename(
                columns={
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume",
                },
                inplace=True,
            )

            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            df = df.sort_values("timestamp").reset_index(drop=True)
            return df

        except Exception as e:
            logger.debug(f"Error fetching OHLCV for {symbol}: {e}")
            return None

    def _get_historical_price_from_df(self, df: pd.DataFrame, days: int) -> Optional[float]:
        """Get price from N days ago using pre-fetched DataFrame"""
        try:
            if len(df) < days + 1:
                return None
            return float(df.iloc[-(days + 1)]["close"])
        except Exception:
            return None

    def _get_24h_volume_from_df(self, df: pd.DataFrame, current_price: float) -> float:
        """Get 24h volume in USD using pre-fetched DataFrame"""
        try:
            if df.empty:
                return 0.0
            # Last complete day volume or just last candle?
            # Previously used last candle.
            last_volume = float(df.iloc[-1]["volume"])
            # Using provided current_price is better than close of yesterday for 24h volume est
            return last_volume * current_price
        except Exception:
            return 0.0

    def _get_avg_volume_from_df(self, df: pd.DataFrame, days: int) -> Optional[float]:
        """Get average volume over N days using pre-fetched DataFrame"""
        try:
            if len(df) < days:
                return None
            
            subset = df.tail(days)
            avg_volume = subset["volume"].mean()
            avg_price = subset["close"].mean()
            return float(avg_volume * avg_price)
        except Exception:
            return None

    def _calculate_atr_metrics_from_df(self, df: pd.DataFrame) -> tuple[Optional[float], Optional[float]]:
        """Calculate ATR(14) and SMA(ATR, 20) using pre-fetched DataFrame"""
        try:
            if len(df) < 40:
                return None, None

            # Calculate ATR(14)
            atr_indicator = ta.volatility.AverageTrueRange(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                window=14
            )
            
            # We need to be careful not to modify the passed df in place if we reuse it, 
            # but adding columns is fine if we don't need pristine state later.
            # Using a copy to be safe.
            df_calc = df.copy()
            df_calc["atr_14"] = atr_indicator.average_true_range()
            df_calc["atr_sma_20"] = df_calc["atr_14"].rolling(window=20).mean()

            atr_14 = float(df_calc.iloc[-1]["atr_14"])
            atr_sma_20 = float(df_calc.iloc[-1]["atr_sma_20"])

            return atr_14, atr_sma_20
        except Exception:
            return None, None

    def _calculate_trend_indicators_from_df(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """Calculate trend indicators using pre-fetched DataFrame"""
        try:
            if len(df) < 50:
                return {}

            df_calc = df.copy()

            # Calculate ADX and Directional Indicators
            adx_indicator = ta.trend.ADXIndicator(
                high=df_calc['high'],
                low=df_calc['low'],
                close=df_calc['close'],
                window=14
            )
            adx_14 = adx_indicator.adx().iloc[-1] if len(df_calc) >= 14 else None
            plus_di = adx_indicator.adx_pos().iloc[-1] if len(df_calc) >= 14 else None
            minus_di = adx_indicator.adx_neg().iloc[-1] if len(df_calc) >= 14 else None

            # Calculate EMAs
            ema_20 = ta.trend.EMAIndicator(df_calc['close'], window=20).ema_indicator().iloc[-1] if len(df_calc) >= 20 else None
            ema_50 = ta.trend.EMAIndicator(df_calc['close'], window=50).ema_indicator().iloc[-1] if len(df_calc) >= 50 else None
            ema_200 = ta.trend.EMAIndicator(df_calc['close'], window=200).ema_indicator().iloc[-1] if len(df_calc) >= 200 else None

            # Calculate Donchian Channel (20-period)
            donchian_upper = df_calc['high'].rolling(window=20).max().iloc[-1] if len(df_calc) >= 20 else None
            donchian_lower = df_calc['low'].rolling(window=20).min().iloc[-1] if len(df_calc) >= 20 else None

            current_price = df_calc['close'].iloc[-1]
            donchian_position = None
            if donchian_upper is not None and donchian_lower is not None and donchian_upper > donchian_lower:
                donchian_position = (current_price - donchian_lower) / (donchian_upper - donchian_lower)
                donchian_position = max(0.0, min(1.0, donchian_position))

            return {
                'adx_14': adx_14,
                'plus_di': plus_di,
                'minus_di': minus_di,
                'ema_20': ema_20,
                'ema_50': ema_50,
                'ema_200': ema_200,
                'donchian_upper_20': donchian_upper,
                'donchian_lower_20': donchian_lower,
                'donchian_position': donchian_position
            }
        except Exception:
            return {}
