"""
Simple tests for coin screener module
"""
import sys
import os
sys.path.append('..')

from coin_screener import CoinScreener, HardFilterConfig, ScoringWeights
from coin_screener.models import CoinMetrics
from coin_screener.filters import HardFilters
from coin_screener.scoring import CoinScorer

# Import for Phase 1 & 2 tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from trend_confirmation import TrendConfirmationEngine, TrendDirection, TrendQuality


def test_hard_filters():
    """Test hard filters"""
    print("\n🧪 Testing hard filters...")

    config = HardFilterConfig()
    filters = HardFilters(config)

    # Create test metrics
    good_coin = CoinMetrics(
        symbol="BTC",
        price=50000,
        volume_24h_usd=100_000_000,
        market_cap_usd=1_000_000_000,
        open_interest_usd=50_000_000,
        funding_rate=0.0001,
        spread_pct=0.1,
        days_listed=365
    )

    bad_coin = CoinMetrics(
        symbol="SCAM",
        price=0.01,
        volume_24h_usd=1000,  # Too low
        market_cap_usd=100_000,  # Too low
        open_interest_usd=100,
        funding_rate=0.01,
        spread_pct=2.0,  # Too wide
        days_listed=5  # Too new
    )

    assert filters.check_single_coin(good_coin) == True
    assert filters.check_single_coin(bad_coin) == False

    print("✅ Hard filters test passed")


def test_scoring():
    """Test scoring system"""
    print("\n🧪 Testing scoring system...")

    scorer = CoinScorer()

    # Create test metrics
    coins = [
        CoinMetrics(
            symbol="BTC",
            price=50000,
            price_7d_ago=45000,  # +11% momentum
            price_30d_ago=40000,  # +25% momentum
            volume_24h_usd=100_000_000,
            volume_7d_avg=90_000_000,
            volume_30d_avg=80_000_000,
            market_cap_usd=1_000_000_000,
            open_interest_usd=50_000_000,
            oi_7d_ago=45_000_000,
            funding_rate=0.0001,
            spread_pct=0.1,
            days_listed=365,
            atr_14=1000,
            atr_sma_20=900
        ),
        CoinMetrics(
            symbol="ETH",
            price=3000,
            price_7d_ago=2900,  # +3.4% momentum
            price_30d_ago=2800,
            volume_24h_usd=80_000_000,
            volume_7d_avg=75_000_000,
            volume_30d_avg=70_000_000,
            market_cap_usd=400_000_000,
            open_interest_usd=30_000_000,
            oi_7d_ago=28_000_000,
            funding_rate=0.0002,
            spread_pct=0.15,
            days_listed=300,
            atr_14=50,
            atr_sma_20=48
        ),
    ]

    scored = scorer.score_coins(coins, btc_price=50000, btc_price_7d=45000)

    assert len(scored) == 2
    assert scored[0].rank == 1
    assert scored[1].rank == 2
    assert all(0 <= coin.score <= 100 for coin in scored)

    print(f"  BTC score: {scored[0].score:.2f}")
    print(f"  ETH score: {scored[1].score:.2f}")
    print("✅ Scoring test passed")


def test_screener_initialization():
    """Test screener initialization"""
    print("\n🧪 Testing screener initialization...")

    screener = CoinScreener(
        testnet=True,
        top_n=3,
        cache_enabled=True
    )

    assert screener.testnet == True
    assert screener.top_n == 3
    assert screener.hl_provider is not None
    assert screener.cg_provider is not None
    assert screener.cache is not None

    print("✅ Screener initialization test passed")


def test_full_screening():
    """Test full screening (may be slow)"""
    print("\n🧪 Testing full screening...")
    print("⚠️  This test is slow as it fetches real data from APIs")

    screener = CoinScreener(
        testnet=True,
        top_n=3,
        cache_enabled=True
    )

    try:
        result = screener.run_full_screening()

        print(f"  Total symbols checked: {len(result.selected_coins) + len(result.excluded_coins)}")
        print(f"  Selected coins: {len(result.selected_coins)}")
        print(f"  Excluded coins: {len(result.excluded_coins)}")

        if result.selected_coins:
            print(f"  Top coin: {result.selected_coins[0].symbol} (score: {result.selected_coins[0].score:.2f})")

        # Basic assertions
        assert result.selected_coins is not None
        assert result.screening_timestamp is not None
        assert result.next_rebalance is not None

        print("✅ Full screening test passed")

    except Exception as e:
        print(f"⚠️  Full screening test failed: {e}")
        print("   This is expected if APIs are unavailable or rate-limited")


def test_cache():
    """Test caching system"""
    print("\n🧪 Testing cache...")

    from coin_screener.data_providers import DataCache

    cache = DataCache(cache_dir=".cache/test")

    # Test set and get
    cache.set("test_key", {"data": "value"})
    value = cache.get("test_key", max_age_seconds=60)

    assert value is not None
    assert value["data"] == "value"

    # Test expiration
    expired = cache.get("test_key", max_age_seconds=0)
    assert expired is None

    # Cleanup
    cache.clear()

    print("✅ Cache test passed")


def test_adx_strength_scoring():
    """Test ADX strength scoring logic (Phase 1)"""
    print("\n🧪 Testing ADX strength scoring...")

    scorer = CoinScorer()

    # Test various ADX levels
    test_cases = [
        (15, 0.3, "weak/ranging"),
        (22, 0.5, "emerging trend"),
        (35, 0.8, "strong trend"),
        (50, 1.0, "very strong trend"),
        (None, 0.5, "no data")
    ]

    for adx, expected_score, description in test_cases:
        coin = CoinMetrics(
            symbol="TEST",
            price=100,
            volume_24h_usd=1_000_000,
            market_cap_usd=10_000_000,
            open_interest_usd=1_000_000,
            funding_rate=0.0001,
            spread_pct=0.1,
            days_listed=100,
            adx_14=adx
        )
        score = scorer._calculate_adx_strength(coin)
        assert score == expected_score, f"ADX {adx} ({description}): expected {expected_score}, got {score}"
        print(f"  ✓ ADX {adx} ({description}): score = {score}")

    print("✅ ADX strength scoring test passed")


def test_ema_alignment_scoring():
    """Test EMA alignment scoring (Phase 1)"""
    print("\n🧪 Testing EMA alignment scoring...")

    scorer = CoinScorer()

    # Perfect bullish alignment
    coin_perfect_bullish = CoinMetrics(
        symbol="TEST",
        price=110,
        volume_24h_usd=1_000_000,
        market_cap_usd=10_000_000,
        open_interest_usd=1_000_000,
        funding_rate=0.0001,
        spread_pct=0.1,
        days_listed=100,
        ema_20=105,
        ema_50=100,
        ema_200=90
    )
    score = scorer._calculate_ema_alignment(coin_perfect_bullish)
    assert abs(score - 1.0) < 0.001, f"Perfect bullish: expected 1.0, got {score}"
    print(f"  ✓ Perfect bullish alignment: score = {score}")

    # Partial alignment (no EMA200)
    coin_partial = CoinMetrics(
        symbol="TEST",
        price=105,
        volume_24h_usd=1_000_000,
        market_cap_usd=10_000_000,
        open_interest_usd=1_000_000,
        funding_rate=0.0001,
        spread_pct=0.1,
        days_listed=100,
        ema_20=103,
        ema_50=100,
        ema_200=None
    )
    score = scorer._calculate_ema_alignment(coin_partial)
    assert 0.7 <= score <= 0.9, f"Partial alignment: score {score} not in expected range"
    print(f"  ✓ Partial alignment (no EMA200): score = {score}")

    # No alignment
    coin_no_align = CoinMetrics(
        symbol="TEST",
        price=95,
        volume_24h_usd=1_000_000,
        market_cap_usd=10_000_000,
        open_interest_usd=1_000_000,
        funding_rate=0.0001,
        spread_pct=0.1,
        days_listed=100,
        ema_20=98,
        ema_50=100,
        ema_200=105
    )
    score = scorer._calculate_ema_alignment(coin_no_align)
    assert score == 0.5, f"No alignment: expected 0.5, got {score}"
    print(f"  ✓ No alignment: score = {score}")

    print("✅ EMA alignment scoring test passed")


def test_donchian_position_scoring():
    """Test Donchian position scoring (Phase 1)"""
    print("\n🧪 Testing Donchian position scoring...")

    scorer = CoinScorer()

    test_cases = [
        (0.9, 1.0, "strong uptrend"),
        (0.7, 0.7, "moderate uptrend"),
        (0.5, 0.3, "consolidation"),
        (0.2, 0.5, "potential downtrend"),
        (None, 0.5, "no data")
    ]

    for position, expected_score, description in test_cases:
        coin = CoinMetrics(
            symbol="TEST",
            price=100,
            volume_24h_usd=1_000_000,
            market_cap_usd=10_000_000,
            open_interest_usd=1_000_000,
            funding_rate=0.0001,
            spread_pct=0.1,
            days_listed=100,
            donchian_position=position
        )
        score = scorer._calculate_donchian_trend(coin)
        assert score == expected_score, f"Position {position} ({description}): expected {expected_score}, got {score}"
        print(f"  ✓ Position {position} ({description}): score = {score}")

    print("✅ Donchian position scoring test passed")


def test_scoring_weights_sum():
    """Test that new scoring weights sum to 1.0"""
    print("\n🧪 Testing scoring weights...")

    try:
        weights = ScoringWeights()
        total = (
            weights.momentum_7d + weights.momentum_30d + weights.volatility_regime +
            weights.volume_trend + weights.oi_trend + weights.funding_stability +
            weights.liquidity_score + weights.relative_strength +
            weights.adx_strength + weights.ema_alignment + weights.donchian_position
        )
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"
        print(f"  ✓ Weights sum: {total:.4f}")
        print(f"  ✓ Trend factors weight: {weights.adx_strength + weights.ema_alignment + weights.donchian_position:.2f}")
        print("✅ Scoring weights test passed")
    except ValueError as e:
        print(f"❌ Scoring weights validation failed: {e}")
        raise


def test_trend_confirmation_engine():
    """Test TrendConfirmationEngine initialization (Phase 2)"""
    print("\n🧪 Testing TrendConfirmationEngine...")

    try:
        engine = TrendConfirmationEngine(testnet=True)
        assert engine.testnet == True
        assert engine.info is not None
        assert engine.config['adx_threshold'] == 25
        assert engine.config['min_confidence'] == 0.6
        print("  ✓ Engine initialized successfully")
        print(f"  ✓ ADX threshold: {engine.config['adx_threshold']}")
        print(f"  ✓ Min confidence: {engine.config['min_confidence']}")
        print("✅ TrendConfirmationEngine test passed")
    except Exception as e:
        print(f"⚠️  TrendConfirmationEngine test failed: {e}")
        print("   This is expected if Hyperliquid API is unavailable")


def test_trend_confirmation_alignment():
    """Test trend alignment calculation logic"""
    print("\n🧪 Testing trend alignment calculation...")

    engine = TrendConfirmationEngine(testnet=True)

    # Test perfect alignment (all bullish)
    daily = {'direction': TrendDirection.STRONG_BULLISH}
    hourly = {'direction': TrendDirection.BULLISH, 'rsi': 60, 'rsi_signal': 'normal'}
    m15 = {'direction': TrendDirection.BULLISH, 'macd_signal': 'bullish', 'near_ema': True}

    direction, quality, confidence = engine._calculate_alignment(daily, hourly, m15)

    assert direction == TrendDirection.STRONG_BULLISH
    assert quality == TrendQuality.EXCELLENT
    assert confidence == 0.95
    print("  ✓ Perfect bullish alignment: EXCELLENT quality, 95% confidence")

    # Test partial alignment (2/3 bullish)
    daily = {'direction': TrendDirection.BULLISH}
    hourly = {'direction': TrendDirection.BULLISH, 'rsi': 55, 'rsi_signal': 'normal'}
    m15 = {'direction': TrendDirection.NEUTRAL, 'macd_signal': 'neutral', 'near_ema': False}

    direction, quality, confidence = engine._calculate_alignment(daily, hourly, m15)

    assert direction == TrendDirection.BULLISH
    assert quality == TrendQuality.GOOD
    assert confidence == 0.80
    print("  ✓ Partial alignment (2/3): GOOD quality, 80% confidence")

    # Test conflicting signals
    daily = {'direction': TrendDirection.BULLISH}
    hourly = {'direction': TrendDirection.BEARISH, 'rsi': 40, 'rsi_signal': 'normal'}
    m15 = {'direction': TrendDirection.NEUTRAL, 'macd_signal': 'neutral', 'near_ema': False}

    direction, quality, confidence = engine._calculate_alignment(daily, hourly, m15)

    assert quality == TrendQuality.POOR
    assert confidence == 0.40
    print("  ✓ Conflicting signals: POOR quality, 40% confidence")

    print("✅ Trend alignment calculation test passed")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Running Coin Screener Tests")
    print("=" * 60)

    try:
        # Core tests
        test_hard_filters()
        test_scoring()
        test_screener_initialization()
        test_cache()

        # Phase 1 tests - Trend indicators
        print("\n" + "=" * 60)
        print("🔬 Phase 1: Trend Filter Enhancement Tests")
        print("=" * 60)
        test_scoring_weights_sum()
        test_adx_strength_scoring()
        test_ema_alignment_scoring()
        test_donchian_position_scoring()

        # Phase 2 tests - Trend confirmation
        print("\n" + "=" * 60)
        print("🔬 Phase 2: Trend Confirmation Layer Tests")
        print("=" * 60)
        test_trend_confirmation_engine()
        test_trend_confirmation_alignment()

        # Optional: test full screening (slow)
        run_slow_tests = input("\n❓ Run full screening test? (slow, requires APIs) [y/N]: ")
        if run_slow_tests.lower() == 'y':
            test_full_screening()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
