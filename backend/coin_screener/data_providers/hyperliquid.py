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


class HyperliquidDataProvider:
    """Fetch market data from Hyperliquid"""

    def __init__(self, testnet: bool = True):
        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        self.info = Info(base_url, skip_ws=True)
        self.testnet = testnet
        logger.info(f"Initialized HyperliquidDataProvider ({'testnet' if testnet else 'mainnet'})")

    def get_available_symbols(self) -> List[str]:
        """
        Get list of all available trading symbols.

        Returns:
            List of symbol strings (e.g., ['BTC', 'ETH', 'SOL'])
        """
        try:
            meta = self.info.meta()
            symbols = [asset['name'] for asset in meta['universe']]
            logger.info(f"Found {len(symbols)} available symbols on Hyperliquid")
            return symbols
        except Exception as e:
            logger.error(f"Error fetching available symbols: {e}")
            return []

    def get_coin_metrics(self, symbol: str) -> Optional[CoinMetrics]:
        """
        Fetch comprehensive metrics for a single coin.

        Args:
            symbol: Coin symbol (e.g., 'BTC')

        Returns:
            CoinMetrics object or None if error
        """
        try:
            # Get current price
            mids = self.info.all_mids()
            if symbol not in mids:
                logger.warning(f"Symbol {symbol} not found in mids")
                return None

            current_price = float(mids[symbol])

            # Get orderbook for spread calculation
            spread_pct = self._calculate_spread(symbol)

            # Get historical prices for momentum
            price_7d = self._get_historical_price(symbol, days=7)
            price_30d = self._get_historical_price(symbol, days=30)

            # Get volume metrics
            volume_24h = self._get_24h_volume(symbol)
            volume_7d_avg = self._get_avg_volume(symbol, days=7)
            volume_30d_avg = self._get_avg_volume(symbol, days=30)

            # Get ATR for volatility
            atr_14, atr_sma_20 = self._calculate_atr_metrics(symbol)

            # Get trend indicators (Phase 1 enhancement)
            trend_indicators = self._calculate_trend_indicators(symbol)

            # Get funding rate (placeholder for now)
            funding_rate = 0.0  # Will be implemented if API available

            # Open interest (placeholder - Hyperliquid doesn't expose this easily)
            open_interest_usd = 0.0
            oi_7d_ago = 0.0

            # Calculate days listed (estimate from available candle data)
            days_listed = self._estimate_days_listed(symbol)

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
            orderbook = self.info.l2_snapshot(symbol)
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

    def _get_historical_price(self, symbol: str, days: int) -> Optional[float]:
        """Get price from N days ago"""
        try:
            df = self._fetch_ohlcv(symbol, interval="1d", limit=days + 1)
            if df is None or len(df) < days + 1:
                return None

            return float(df.iloc[-(days + 1)]["close"])

        except Exception as e:
            logger.debug(f"Error getting {days}d price for {symbol}: {e}")
            return None

    def _get_24h_volume(self, symbol: str) -> float:
        """Get 24h volume in USD"""
        try:
            df = self._fetch_ohlcv(symbol, interval="1d", limit=2)
            if df is None or len(df) < 1:
                return 0.0

            # Last complete day volume
            last_volume = float(df.iloc[-1]["volume"])
            last_price = float(df.iloc[-1]["close"])

            return last_volume * last_price

        except Exception as e:
            logger.debug(f"Error getting 24h volume for {symbol}: {e}")
            return 0.0

    def _get_avg_volume(self, symbol: str, days: int) -> Optional[float]:
        """Get average volume over N days"""
        try:
            df = self._fetch_ohlcv(symbol, interval="1d", limit=days)
            if df is None or len(df) < days:
                return None

            avg_volume = df["volume"].tail(days).mean()
            avg_price = df["close"].tail(days).mean()

            return float(avg_volume * avg_price)

        except Exception as e:
            logger.debug(f"Error getting {days}d avg volume for {symbol}: {e}")
            return None

    def _calculate_atr_metrics(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """
        Calculate ATR(14) and SMA(ATR, 20)

        Returns:
            Tuple of (atr_14, atr_sma_20)
        """
        try:
            df = self._fetch_ohlcv(symbol, interval="1d", limit=40)
            if df is None or len(df) < 40:
                return None, None

            # Calculate ATR(14)
            atr_indicator = ta.volatility.AverageTrueRange(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                window=14
            )
            df["atr_14"] = atr_indicator.average_true_range()

            # Calculate SMA(ATR, 20)
            df["atr_sma_20"] = df["atr_14"].rolling(window=20).mean()

            # Get latest values
            atr_14 = float(df.iloc[-1]["atr_14"])
            atr_sma_20 = float(df.iloc[-1]["atr_sma_20"])

            return atr_14, atr_sma_20

        except Exception as e:
            logger.debug(f"Error calculating ATR for {symbol}: {e}")
            return None, None

    def _estimate_days_listed(self, symbol: str) -> int:
        """
        Estimate number of days a symbol has been listed.

        Uses maximum available candle history as proxy.
        """
        try:
            # Try to fetch 1-year of daily data
            df = self._fetch_ohlcv(symbol, interval="1d", limit=365)
            if df is None:
                return 0

            return len(df)

        except Exception as e:
            logger.debug(f"Error estimating days listed for {symbol}: {e}")
            return 0

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

            ohlcv_data = self.info.candles_snapshot(
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

    def _calculate_trend_indicators(self, symbol: str) -> Dict[str, Optional[float]]:
        """
        Calculate trend indicators from daily data for Phase 1 enhancement.

        Calculates:
        - ADX (14-period Average Directional Index)
        - +DI and -DI (Directional Indicators)
        - EMAs (20, 50, 200-period Exponential Moving Averages)
        - Donchian Channel (20-period) and position within it

        Args:
            symbol: Coin symbol

        Returns:
            Dictionary with trend indicator values
        """
        try:
            # Fetch 250 days of data to calculate EMA200 properly
            df = self._fetch_ohlcv(symbol, interval="1d", limit=250)

            if df is None or len(df) < 50:
                logger.debug(f"Insufficient daily data for trend indicators on {symbol}")
                return {}

            # Calculate ADX and Directional Indicators
            adx_indicator = ta.trend.ADXIndicator(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=14
            )
            adx_14 = adx_indicator.adx().iloc[-1] if len(df) >= 14 else None
            plus_di = adx_indicator.adx_pos().iloc[-1] if len(df) >= 14 else None
            minus_di = adx_indicator.adx_neg().iloc[-1] if len(df) >= 14 else None

            # Calculate EMAs
            ema_20 = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator().iloc[-1] if len(df) >= 20 else None
            ema_50 = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator().iloc[-1] if len(df) >= 50 else None
            ema_200 = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator().iloc[-1] if len(df) >= 200 else None

            # Calculate Donchian Channel (20-period)
            donchian_upper = df['high'].rolling(window=20).max().iloc[-1] if len(df) >= 20 else None
            donchian_lower = df['low'].rolling(window=20).min().iloc[-1] if len(df) >= 20 else None

            # Calculate position within Donchian Channel (0-1 range)
            current_price = df['close'].iloc[-1]
            donchian_position = None
            if donchian_upper is not None and donchian_lower is not None and donchian_upper > donchian_lower:
                donchian_position = (current_price - donchian_lower) / (donchian_upper - donchian_lower)
                # Clamp to 0-1 range
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

        except Exception as e:
            logger.debug(f"Error calculating trend indicators for {symbol}: {e}")
            return {}
