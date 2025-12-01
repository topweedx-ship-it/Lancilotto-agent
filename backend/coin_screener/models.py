"""
Data models for coin screening
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class CoinScore:
    """Represents a scored cryptocurrency"""
    symbol: str
    score: float  # 0-100
    rank: int
    factors: Dict[str, float]  # Detailed breakdown of scoring factors
    metrics: Dict[str, Any]    # Raw data (volume, OI, market cap, etc.)
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "score": round(self.score, 2),
            "rank": self.rank,
            "factors": {k: round(v, 4) for k, v in self.factors.items()},
            "metrics": self.metrics,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class CoinScreenerResult:
    """Results from a complete screening operation"""
    selected_coins: List[CoinScore]  # Top N coins ordered by score
    excluded_coins: List[str]         # Coins excluded by hard filters
    screening_timestamp: datetime
    next_rebalance: datetime
    screening_type: str = "full_rebalance"  # or "daily_update"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "selected_coins": [coin.to_dict() for coin in self.selected_coins],
            "excluded_coins": self.excluded_coins,
            "screening_timestamp": self.screening_timestamp.isoformat(),
            "next_rebalance": self.next_rebalance.isoformat(),
            "screening_type": self.screening_type
        }


@dataclass
class CoinMetrics:
    """Raw metrics for a single cryptocurrency"""
    symbol: str
    price: float
    volume_24h_usd: float
    market_cap_usd: float
    open_interest_usd: float
    funding_rate: float
    spread_pct: float
    days_listed: int

    # Historical data for calculations
    price_7d_ago: Optional[float] = None
    price_30d_ago: Optional[float] = None
    volume_7d_avg: Optional[float] = None
    volume_30d_avg: Optional[float] = None
    oi_7d_ago: Optional[float] = None

    # Technical indicators
    atr_14: Optional[float] = None
    atr_sma_20: Optional[float] = None

    # Trend indicators (daily timeframe for Phase 1)
    adx_14: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    donchian_upper_20: Optional[float] = None
    donchian_lower_20: Optional[float] = None
    donchian_position: Optional[float] = None  # 0-1 range

    # Additional metadata
    is_stablecoin: bool = False
    coingecko_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "volume_24h_usd": self.volume_24h_usd,
            "market_cap_usd": self.market_cap_usd,
            "open_interest_usd": self.open_interest_usd,
            "funding_rate": self.funding_rate,
            "spread_pct": self.spread_pct,
            "days_listed": self.days_listed,
            "price_7d_ago": self.price_7d_ago,
            "price_30d_ago": self.price_30d_ago,
            "volume_7d_avg": self.volume_7d_avg,
            "volume_30d_avg": self.volume_30d_avg,
            "oi_7d_ago": self.oi_7d_ago,
            "atr_14": self.atr_14,
            "atr_sma_20": self.atr_sma_20,
            "adx_14": self.adx_14,
            "plus_di": self.plus_di,
            "minus_di": self.minus_di,
            "ema_20": self.ema_20,
            "ema_50": self.ema_50,
            "ema_200": self.ema_200,
            "donchian_upper_20": self.donchian_upper_20,
            "donchian_lower_20": self.donchian_lower_20,
            "donchian_position": self.donchian_position,
            "is_stablecoin": self.is_stablecoin,
            "coingecko_id": self.coingecko_id
        }


@dataclass
class HardFilterConfig:
    """Configuration for hard filters"""
    min_volume_24h_usd: float = 50_000_000
    min_market_cap_usd: float = 250_000_000
    min_days_listed: int = 30
    min_open_interest_usd: float = 10_000_000
    max_spread_pct: float = 0.5
    exclude_stablecoins: bool = True

    # List of known stablecoins to exclude
    stablecoin_symbols: List[str] = field(default_factory=lambda: [
        "USDT", "USDC", "DAI", "BUSD", "TUSD", "USDD",
        "FRAX", "USDP", "GUSD", "LUSD", "SUSD"
    ])


@dataclass
class ScoringWeights:
    """Weights for scoring factors (must sum to 1.0)"""
    # Existing factors (reduced to make room for trend factors)
    momentum_7d: float = 0.15        # Was 0.20
    momentum_30d: float = 0.10       # Was 0.15
    volatility_regime: float = 0.10  # Was 0.15
    volume_trend: float = 0.10       # Was 0.15
    oi_trend: float = 0.08           # Was 0.10
    funding_stability: float = 0.07  # Was 0.10
    liquidity_score: float = 0.05    # Was 0.10
    relative_strength: float = 0.05  # Unchanged

    # NEW TREND FACTORS (Phase 1 - total 0.30)
    adx_strength: float = 0.12       # ADX > 25 = strong trend
    ema_alignment: float = 0.10      # EMA20 > EMA50 alignment
    donchian_position: float = 0.08  # Position in Donchian Channel

    def __post_init__(self):
        """Validate weights sum to 1.0"""
        total = (
            self.momentum_7d + self.momentum_30d + self.volatility_regime +
            self.volume_trend + self.oi_trend + self.funding_stability +
            self.liquidity_score + self.relative_strength +
            self.adx_strength + self.ema_alignment + self.donchian_position
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")
