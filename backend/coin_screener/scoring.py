"""
Scoring system for cryptocurrency screening
"""
import logging
import numpy as np
from typing import List, Dict
from .models import CoinMetrics, CoinScore, ScoringWeights
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CoinScorer:
    """Calculate composite scores for cryptocurrencies"""

    def __init__(self, weights: ScoringWeights = None):
        self.weights = weights or ScoringWeights()

    def score_coins(
        self,
        coins: List[CoinMetrics],
        btc_price: float = None,
        btc_price_7d: float = None
    ) -> List[CoinScore]:
        """
        Score and rank a list of coins.

        Args:
            coins: List of CoinMetrics to score
            btc_price: Current BTC price for relative strength calculation
            btc_price_7d: BTC price 7 days ago

        Returns:
            List of CoinScore objects sorted by score (highest first)
        """
        if not coins:
            return []

        scored_coins = []

        for coin in coins:
            try:
                factors = self._calculate_factors(coin, coins, btc_price, btc_price_7d)
                score = self._composite_score(factors)

                coin_score = CoinScore(
                    symbol=coin.symbol,
                    score=score,
                    rank=0,  # Will be set after sorting
                    factors=factors,
                    metrics=coin.to_dict(),
                    last_updated=datetime.now(timezone.utc)
                )
                scored_coins.append(coin_score)

            except Exception as e:
                logger.warning(f"Error scoring {coin.symbol}: {e}")
                continue

        # Sort by score (highest first) and assign ranks
        scored_coins.sort(key=lambda x: x.score, reverse=True)
        for rank, coin in enumerate(scored_coins, start=1):
            coin.rank = rank

        logger.info(f"Scored {len(scored_coins)} coins")
        return scored_coins

    def _calculate_factors(
        self,
        coin: CoinMetrics,
        all_coins: List[CoinMetrics],
        btc_price: float = None,
        btc_price_7d: float = None
    ) -> Dict[str, float]:
        """
        Calculate all scoring factors for a coin.

        Each factor should be normalized to 0-1 range.
        """
        factors = {}

        # Existing factors (1-8)
        # 1. Momentum 7d (percentile ranking)
        factors['momentum_7d'] = self._calculate_momentum_7d(coin, all_coins)

        # 2. Momentum 30d (percentile ranking)
        factors['momentum_30d'] = self._calculate_momentum_30d(coin, all_coins)

        # 3. Volatility regime
        factors['volatility_regime'] = self._calculate_volatility_regime(coin)

        # 4. Volume trend
        factors['volume_trend'] = self._calculate_volume_trend(coin)

        # 5. OI trend
        factors['oi_trend'] = self._calculate_oi_trend(coin)

        # 6. Funding stability
        factors['funding_stability'] = self._calculate_funding_stability(coin)

        # 7. Liquidity score
        factors['liquidity_score'] = self._calculate_liquidity_score(coin)

        # 8. Relative strength vs BTC
        factors['relative_strength'] = self._calculate_relative_strength(
            coin, btc_price, btc_price_7d
        )

        # NEW TREND FACTORS (Phase 1 - 9-11)
        # 9. ADX strength (trend strength indicator)
        factors['adx_strength'] = self._calculate_adx_strength(coin)

        # 10. EMA alignment (trend direction clarity)
        factors['ema_alignment'] = self._calculate_ema_alignment(coin)

        # 11. Donchian position (trend confirmation)
        factors['donchian_position'] = self._calculate_donchian_trend(coin)

        return factors

    def _composite_score(self, factors: Dict[str, float]) -> float:
        """
        Calculate composite score from factors.

        Returns:
            Score in 0-100 range
        """
        score = 0.0

        # Existing factors
        score += factors.get('momentum_7d', 0) * self.weights.momentum_7d
        score += factors.get('momentum_30d', 0) * self.weights.momentum_30d
        score += factors.get('volatility_regime', 0) * self.weights.volatility_regime
        score += factors.get('volume_trend', 0) * self.weights.volume_trend
        score += factors.get('oi_trend', 0) * self.weights.oi_trend
        score += factors.get('funding_stability', 0) * self.weights.funding_stability
        score += factors.get('liquidity_score', 0) * self.weights.liquidity_score
        score += factors.get('relative_strength', 0) * self.weights.relative_strength

        # NEW: Trend factors (Phase 1)
        score += factors.get('adx_strength', 0) * self.weights.adx_strength
        score += factors.get('ema_alignment', 0) * self.weights.ema_alignment
        score += factors.get('donchian_position', 0) * self.weights.donchian_position

        # Scale to 0-100
        return score * 100

    # Factor calculation methods

    def _calculate_momentum_7d(self, coin: CoinMetrics, all_coins: List[CoinMetrics]) -> float:
        """
        Calculate 7-day momentum as percentile ranking.

        Returns value 0-1 where 1 = highest momentum
        """
        if coin.price_7d_ago is None or coin.price_7d_ago <= 0:
            return 0.5  # Neutral if no data

        # Calculate 7-day return
        return_7d = (coin.price - coin.price_7d_ago) / coin.price_7d_ago

        # Get all 7d returns
        returns_7d = []
        for c in all_coins:
            if c.price_7d_ago is not None and c.price_7d_ago > 0:
                ret = (c.price - c.price_7d_ago) / c.price_7d_ago
                returns_7d.append(ret)

        if not returns_7d:
            return 0.5

        # Calculate percentile rank
        percentile = self._percentile_rank(return_7d, returns_7d)
        return percentile

    def _calculate_momentum_30d(self, coin: CoinMetrics, all_coins: List[CoinMetrics]) -> float:
        """Calculate 30-day momentum as percentile ranking"""
        if coin.price_30d_ago is None or coin.price_30d_ago <= 0:
            return 0.5

        return_30d = (coin.price - coin.price_30d_ago) / coin.price_30d_ago

        returns_30d = []
        for c in all_coins:
            if c.price_30d_ago is not None and c.price_30d_ago > 0:
                ret = (c.price - c.price_30d_ago) / c.price_30d_ago
                returns_30d.append(ret)

        if not returns_30d:
            return 0.5

        return self._percentile_rank(return_30d, returns_30d)

    def _calculate_volatility_regime(self, coin: CoinMetrics) -> float:
        """
        Volatility regime: 1 if ATR(14) > SMA(ATR, 20), else 0.5

        Higher volatility is preferred for trading opportunities.
        """
        if coin.atr_14 is None or coin.atr_sma_20 is None:
            return 0.5

        return 1.0 if coin.atr_14 > coin.atr_sma_20 else 0.5

    def _calculate_volume_trend(self, coin: CoinMetrics) -> float:
        """
        Volume trend: min(volume_7d_avg / volume_30d_avg, 2) / 2

        Caps at 2x to avoid extreme outliers.
        """
        if coin.volume_7d_avg is None or coin.volume_30d_avg is None:
            return 0.5

        if coin.volume_30d_avg <= 0:
            return 0.5

        ratio = coin.volume_7d_avg / coin.volume_30d_avg
        capped_ratio = min(ratio, 2.0)
        return capped_ratio / 2.0  # Normalize to 0-1

    def _calculate_oi_trend(self, coin: CoinMetrics) -> float:
        """
        OI trend: 1 if weekly OI change > 0, else 0.5
        """
        if coin.oi_7d_ago is None or coin.oi_7d_ago <= 0:
            return 0.5

        oi_change = coin.open_interest_usd - coin.oi_7d_ago

        return 1.0 if oi_change > 0 else 0.5

    def _calculate_funding_stability(self, coin: CoinMetrics) -> float:
        """
        Funding stability: 1 - min(abs(funding_rate) / 0.01, 1)

        Prefers near-zero funding rates (balanced market).
        """
        abs_funding = abs(coin.funding_rate)
        normalized = min(abs_funding / 0.01, 1.0)
        return 1.0 - normalized

    def _calculate_liquidity_score(self, coin: CoinMetrics) -> float:
        """
        Liquidity score: 1 - min(spread_pct / 0.5, 1)

        Lower spread = better liquidity
        """
        normalized = min(coin.spread_pct / 0.5, 1.0)
        return 1.0 - normalized

    def _calculate_relative_strength(
        self,
        coin: CoinMetrics,
        btc_price: float = None,
        btc_price_7d: float = None
    ) -> float:
        """
        Relative strength: performance vs BTC over 7 days

        Returns 0-1 where >0.5 = outperforming BTC
        """
        if btc_price is None or btc_price_7d is None:
            return 0.5

        if coin.price_7d_ago is None or coin.price_7d_ago <= 0:
            return 0.5

        if btc_price_7d <= 0:
            return 0.5

        # Calculate returns
        coin_return = (coin.price - coin.price_7d_ago) / coin.price_7d_ago
        btc_return = (btc_price - btc_price_7d) / btc_price_7d

        # Relative return
        relative_return = coin_return - btc_return

        # Map to 0-1 scale (assume ±50% relative performance range)
        # 0 = -50% underperformance, 0.5 = match BTC, 1 = +50% outperformance
        normalized = (relative_return + 0.5) / 1.0
        return np.clip(normalized, 0.0, 1.0)

    @staticmethod
    def _percentile_rank(value: float, values: List[float]) -> float:
        """
        Calculate percentile rank of value in values list.

        Returns 0-1 where 1 = highest percentile
        """
        if not values:
            return 0.5

        values_array = np.array(values)
        percentile = np.sum(values_array < value) / len(values_array)
        return percentile

    # NEW TREND SCORING METHODS (Phase 1)

    def _calculate_adx_strength(self, coin: CoinMetrics) -> float:
        """
        ADX-based trend strength score.

        Based on academic research suggesting ADX > 25 for strong trends in crypto.
        Returns 0-1 where higher values indicate stronger trends.

        Logic:
        - ADX < 20: Ranging market (score = 0.3)
        - ADX 20-25: Emerging trend (score = 0.5)
        - ADX 25-40: Strong trend (score = 0.8)
        - ADX > 40: Very strong trend (score = 1.0)
        """
        if coin.adx_14 is None:
            return 0.5  # Neutral if no data

        adx = coin.adx_14

        if adx < 20:
            return 0.3  # Weak/ranging market
        elif adx < 25:
            return 0.5  # Emerging trend
        elif adx < 40:
            return 0.8  # Strong trend
        else:
            return 1.0  # Very strong trend

    def _calculate_ema_alignment(self, coin: CoinMetrics) -> float:
        """
        EMA alignment score for trend direction clarity.

        Perfect bullish alignment (EMA20 > EMA50 > EMA200) = 1.0
        Checks multiple conditions:
        - Price position relative to EMAs
        - EMA ordering (bullish or bearish alignment)

        Returns 0-1 where higher values indicate better trend alignment.
        """
        if None in [coin.ema_20, coin.ema_50, coin.price]:
            return 0.5  # Neutral if no data

        score = 0.5  # Base score (neutral)

        # Bullish alignment checks
        if coin.ema_20 > coin.ema_50:
            score += 0.2

        # Add bonus if we have EMA200 data and it's aligned
        if coin.ema_200 is not None:
            if coin.ema_50 > coin.ema_200:
                score += 0.2

        # Check if price is above the trend (bullish)
        if coin.price > coin.ema_20:
            score += 0.1

        return min(score, 1.0)

    def _calculate_donchian_trend(self, coin: CoinMetrics) -> float:
        """
        Donchian channel position as trend indicator.

        Based on Zarattini et al. (2025) research on trend-following strategies.
        Position in channel indicates trend strength:
        - High position (>0.8): Strong uptrend
        - Mid-high (0.6-0.8): Moderate uptrend
        - Mid (0.4-0.6): Consolidation/neutral
        - Low (<0.4): Potential downtrend

        Returns 0-1 where higher values indicate stronger uptrends.
        """
        if coin.donchian_position is None:
            return 0.5  # Neutral if no data

        pos = coin.donchian_position

        if pos > 0.8:
            return 1.0  # Strong uptrend
        elif pos > 0.6:
            return 0.7  # Moderate uptrend
        elif pos > 0.4:
            return 0.3  # Neutral/consolidation
        else:
            # For downtrend: could be valuable for short strategies
            # For now, return neutral score
            return 0.5
