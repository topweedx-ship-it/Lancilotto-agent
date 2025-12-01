"""
Real-time trend confirmation layer.

Verifies trend quality before each trading decision using multi-timeframe analysis.
Implements top-down analysis approach: Daily -> Hourly -> 15M
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Dict
import pandas as pd
import ta

from hyperliquid.info import Info
from hyperliquid.utils import constants

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Trend direction classification"""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


class TrendQuality(Enum):
    """Overall trend quality assessment"""
    EXCELLENT = "excellent"  # All timeframes aligned
    GOOD = "good"           # Major timeframes aligned
    MODERATE = "moderate"   # Some alignment
    POOR = "poor"           # Conflicting signals
    INVALID = "invalid"     # Do not trade


@dataclass
class TrendConfirmation:
    """Result of multi-timeframe trend analysis"""
    symbol: str
    direction: TrendDirection
    quality: TrendQuality
    confidence: float  # 0-1

    # Per-timeframe analysis
    daily_trend: Optional[TrendDirection] = None
    hourly_trend: Optional[TrendDirection] = None
    m15_trend: Optional[TrendDirection] = None

    # Supporting data
    daily_adx: Optional[float] = None
    hourly_rsi: Optional[float] = None
    m15_macd_signal: Optional[str] = None

    # Trading recommendation
    should_trade: bool = False
    recommended_direction: Optional[str] = None  # "long" or "short"
    entry_quality: Optional[str] = None  # "optimal", "acceptable", "wait"

    def __str__(self) -> str:
        """String representation for logging"""
        return (
            f"{self.symbol}: {self.direction.value} "
            f"(Q: {self.quality.value}, Conf: {self.confidence:.0%}, "
            f"Trade: {self.should_trade}, Entry: {self.entry_quality})"
        )


class TrendConfirmationEngine:
    """
    Multi-timeframe trend confirmation engine.

    Validates trend quality before trading decisions.
    Implements top-down analysis approach.
    """

    def __init__(self, testnet: bool = True):
        """
        Initialize trend confirmation engine.

        Args:
            testnet: Use Hyperliquid testnet
        """
        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        from hyperliquid_utils import init_info_with_retry
        self.info = init_info_with_retry(base_url, skip_ws=True)
        self.testnet = testnet

        # Configuration
        self.config = {
            'adx_threshold': 25,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'min_confidence': 0.6,  # Minimum confidence to trade
        }

        logger.info(f"Initialized TrendConfirmationEngine ({'testnet' if testnet else 'mainnet'})")

    def confirm_trend(
        self,
        symbol: str,
        daily_metrics: Optional[Dict] = None
    ) -> TrendConfirmation:
        """
        Perform multi-timeframe trend confirmation.

        Args:
            symbol: Trading pair symbol
            daily_metrics: Pre-computed daily metrics from screener (optional)

        Returns:
            TrendConfirmation with trading recommendation
        """
        logger.info(f"🔍 Confirming trend for {symbol}...")

        try:
            # 1. Get daily trend (from screener or compute)
            daily = self._analyze_daily(symbol, daily_metrics)

            # 2. Get hourly trend
            hourly = self._analyze_hourly(symbol)

            # 3. Get 15m trend
            m15 = self._analyze_15m(symbol)

            # 4. Calculate alignment and confidence
            direction, quality, confidence = self._calculate_alignment(
                daily, hourly, m15
            )

            # 5. Determine if we should trade
            should_trade = self._should_trade(quality, confidence, hourly)

            # 6. Determine entry quality
            entry_quality = self._assess_entry_quality(m15, direction)

            # 7. Determine recommended direction
            recommended_direction = None
            if direction in [TrendDirection.BULLISH, TrendDirection.STRONG_BULLISH]:
                recommended_direction = "long"
            elif direction in [TrendDirection.BEARISH, TrendDirection.STRONG_BEARISH]:
                recommended_direction = "short"

            result = TrendConfirmation(
                symbol=symbol,
                direction=direction,
                quality=quality,
                confidence=confidence,
                daily_trend=daily.get('direction'),
                hourly_trend=hourly.get('direction'),
                m15_trend=m15.get('direction'),
                daily_adx=daily.get('adx'),
                hourly_rsi=hourly.get('rsi'),
                m15_macd_signal=m15.get('macd_signal'),
                should_trade=should_trade,
                recommended_direction=recommended_direction,
                entry_quality=entry_quality
            )

            logger.info(f"📊 Trend confirmation: {result}")
            return result

        except Exception as e:
            logger.error(f"Error confirming trend for {symbol}: {e}")
            # Return conservative result on error
            return TrendConfirmation(
                symbol=symbol,
                direction=TrendDirection.NEUTRAL,
                quality=TrendQuality.INVALID,
                confidence=0.0,
                should_trade=False
            )

    def _analyze_daily(
        self,
        symbol: str,
        precomputed: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze daily timeframe for overall trend direction.
        Uses ADX and EMA alignment.

        Args:
            symbol: Trading symbol
            precomputed: Pre-computed metrics from coin screener

        Returns:
            Dictionary with daily trend analysis
        """
        if precomputed:
            # Use data from coin_screener
            adx = precomputed.get('adx_14', 0)
            plus_di = precomputed.get('plus_di', 0)
            minus_di = precomputed.get('minus_di', 0)
        else:
            # Fetch fresh data
            df = self._fetch_ohlcv(symbol, '1d', 50)
            if df is None or len(df) < 14:
                return {'direction': TrendDirection.NEUTRAL, 'adx': 0, 'strength': 'unknown'}

            adx, plus_di, minus_di = self._calculate_adx(df)

        # Determine direction based on ADX and DI
        if adx > self.config['adx_threshold']:
            if plus_di > minus_di:
                direction = TrendDirection.STRONG_BULLISH if adx > 40 else TrendDirection.BULLISH
            else:
                direction = TrendDirection.STRONG_BEARISH if adx > 40 else TrendDirection.BEARISH
        else:
            direction = TrendDirection.NEUTRAL

        strength = 'strong' if adx > 40 else 'moderate' if adx > 25 else 'weak'

        return {
            'direction': direction,
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di,
            'strength': strength
        }

    def _analyze_hourly(self, symbol: str) -> Dict:
        """
        Analyze hourly timeframe for momentum and RSI.
        Confirms daily trend or signals caution.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with hourly trend analysis
        """
        df = self._fetch_ohlcv(symbol, '1h', 100)

        if df is None or len(df) < 50:
            return {'direction': TrendDirection.NEUTRAL, 'rsi': 50, 'rsi_signal': 'unknown'}

        # Calculate indicators
        rsi = self._calculate_rsi(df, 14)
        ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
        ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
        current_price = df['close'].iloc[-1]

        # Determine direction
        if current_price > ema_20 > ema_50:
            direction = TrendDirection.BULLISH
        elif current_price < ema_20 < ema_50:
            direction = TrendDirection.BEARISH
        else:
            direction = TrendDirection.NEUTRAL

        # Check RSI for overbought/oversold
        rsi_signal = "normal"
        if rsi > self.config['rsi_overbought']:
            rsi_signal = "overbought"
        elif rsi < self.config['rsi_oversold']:
            rsi_signal = "oversold"

        return {
            'direction': direction,
            'rsi': rsi,
            'rsi_signal': rsi_signal,
            'ema_alignment': current_price > ema_20 > ema_50 or current_price < ema_20 < ema_50
        }

    def _analyze_15m(self, symbol: str) -> Dict:
        """
        Analyze 15-minute timeframe for entry timing.
        Uses MACD for momentum shifts.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with 15m trend analysis
        """
        df = self._fetch_ohlcv(symbol, '15m', 100)

        if df is None or len(df) < 50:
            return {'direction': TrendDirection.NEUTRAL, 'macd_signal': 'unknown'}

        # Calculate MACD
        macd, signal, histogram = self._calculate_macd(df)

        # Determine MACD signal
        if macd > signal and histogram > 0:
            macd_signal = "bullish"
            direction = TrendDirection.BULLISH
        elif macd < signal and histogram < 0:
            macd_signal = "bearish"
            direction = TrendDirection.BEARISH
        else:
            macd_signal = "neutral"
            direction = TrendDirection.NEUTRAL

        # Check for pullback to EMA (entry opportunity)
        ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        distance_to_ema = abs(current_price - ema_20) / ema_20 * 100

        return {
            'direction': direction,
            'macd': macd,
            'macd_signal': macd_signal,
            'histogram': histogram,
            'ema_20': ema_20,
            'distance_to_ema_pct': distance_to_ema,
            'near_ema': distance_to_ema < 0.5  # Within 0.5% of EMA
        }

    def _calculate_alignment(
        self,
        daily: Dict,
        hourly: Dict,
        m15: Dict
    ) -> Tuple[TrendDirection, TrendQuality, float]:
        """
        Calculate overall trend alignment across timeframes.

        Args:
            daily: Daily timeframe analysis
            hourly: Hourly timeframe analysis
            m15: 15-minute timeframe analysis

        Returns:
            Tuple of (direction, quality, confidence)
        """
        directions = [
            daily.get('direction'),
            hourly.get('direction'),
            m15.get('direction')
        ]

        # Count bullish/bearish/neutral
        bullish_count = sum(1 for d in directions if d in [
            TrendDirection.BULLISH, TrendDirection.STRONG_BULLISH
        ])
        bearish_count = sum(1 for d in directions if d in [
            TrendDirection.BEARISH, TrendDirection.STRONG_BEARISH
        ])

        # Determine overall direction
        if bullish_count >= 2:
            direction = TrendDirection.STRONG_BULLISH if bullish_count == 3 else TrendDirection.BULLISH
        elif bearish_count >= 2:
            direction = TrendDirection.STRONG_BEARISH if bearish_count == 3 else TrendDirection.BEARISH
        else:
            direction = TrendDirection.NEUTRAL

        # Determine quality
        if bullish_count == 3 or bearish_count == 3:
            quality = TrendQuality.EXCELLENT
            confidence = 0.95
        elif bullish_count == 2 or bearish_count == 2:
            # Check if daily and hourly align (most important)
            daily_hourly_align = (
                daily.get('direction') in [TrendDirection.BULLISH, TrendDirection.STRONG_BULLISH] and
                hourly.get('direction') in [TrendDirection.BULLISH, TrendDirection.STRONG_BULLISH]
            ) or (
                daily.get('direction') in [TrendDirection.BEARISH, TrendDirection.STRONG_BEARISH] and
                hourly.get('direction') in [TrendDirection.BEARISH, TrendDirection.STRONG_BEARISH]
            )

            if daily_hourly_align:
                quality = TrendQuality.GOOD
                confidence = 0.80
            else:
                quality = TrendQuality.MODERATE
                confidence = 0.65
        else:
            quality = TrendQuality.POOR
            confidence = 0.40

        return direction, quality, confidence

    def _should_trade(
        self,
        quality: TrendQuality,
        confidence: float,
        hourly: Dict
    ) -> bool:
        """
        Determine if conditions are suitable for trading.

        Args:
            quality: Overall trend quality
            confidence: Confidence score (0-1)
            hourly: Hourly timeframe analysis

        Returns:
            True if conditions are suitable for trading
        """
        # Don't trade if quality is poor or invalid
        if quality in [TrendQuality.POOR, TrendQuality.INVALID]:
            return False

        # Don't trade if confidence is too low
        if confidence < self.config['min_confidence']:
            return False

        # Be cautious if RSI is extreme
        if hourly.get('rsi_signal') in ['overbought', 'oversold']:
            # Still allow if quality is excellent
            if quality != TrendQuality.EXCELLENT:
                return False

        return True

    def _assess_entry_quality(
        self,
        m15: Dict,
        direction: TrendDirection
    ) -> str:
        """
        Assess the quality of potential entry based on 15m analysis.

        Args:
            m15: 15-minute timeframe analysis
            direction: Overall trend direction

        Returns:
            Entry quality: "optimal", "acceptable", or "wait"
        """
        # Optimal: Near EMA with MACD aligned
        if m15.get('near_ema'):
            if (direction in [TrendDirection.BULLISH, TrendDirection.STRONG_BULLISH] and
                m15.get('macd_signal') == 'bullish'):
                return "optimal"
            elif (direction in [TrendDirection.BEARISH, TrendDirection.STRONG_BEARISH] and
                  m15.get('macd_signal') == 'bearish'):
                return "optimal"

        # Acceptable: MACD aligned but not near EMA
        if ((direction in [TrendDirection.BULLISH, TrendDirection.STRONG_BULLISH] and
             m15.get('macd_signal') == 'bullish') or
            (direction in [TrendDirection.BEARISH, TrendDirection.STRONG_BEARISH] and
             m15.get('macd_signal') == 'bearish')):
            return "acceptable"

        return "wait"

    # Helper methods for indicator calculations

    def _fetch_ohlcv(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Hyperliquid.

        Args:
            symbol: Asset symbol
            interval: Candle interval (e.g., '1d', '1h', '15m')
            limit: Number of candles

        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            from datetime import datetime, timezone

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
            logger.debug(f"Error fetching OHLCV for {symbol} ({interval}): {e}")
            return None

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Tuple[float, float, float]:
        """
        Calculate ADX, +DI, -DI.

        Args:
            df: DataFrame with OHLCV data
            period: ADX period (default 14)

        Returns:
            Tuple of (adx, plus_di, minus_di)
        """
        adx_indicator = ta.trend.ADXIndicator(
            df['high'],
            df['low'],
            df['close'],
            window=period
        )
        return (
            adx_indicator.adx().iloc[-1],
            adx_indicator.adx_pos().iloc[-1],
            adx_indicator.adx_neg().iloc[-1]
        )

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate RSI.

        Args:
            df: DataFrame with OHLCV data
            period: RSI period (default 14)

        Returns:
            RSI value
        """
        rsi = ta.momentum.RSIIndicator(df['close'], window=period)
        return rsi.rsi().iloc[-1]

    def _calculate_macd(self, df: pd.DataFrame) -> Tuple[float, float, float]:
        """
        Calculate MACD, Signal, Histogram.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (macd, signal, histogram)
        """
        macd_indicator = ta.trend.MACD(df['close'])
        return (
            macd_indicator.macd().iloc[-1],
            macd_indicator.macd_signal().iloc[-1],
            macd_indicator.macd_diff().iloc[-1]
        )
