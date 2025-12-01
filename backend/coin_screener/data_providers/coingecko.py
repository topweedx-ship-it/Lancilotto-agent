"""
CoinGecko data provider for market cap and volume data
"""
import logging
import requests
import time
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class CoinGeckoDataProvider:
    """Fetch market data from CoinGecko API"""

    # Mapping from common symbols to CoinGecko IDs
    SYMBOL_TO_ID = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "SOL": "solana",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "DOT": "polkadot",
        "MATIC": "polygon-ecosystem-token",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "UNI": "uniswap",
        "ATOM": "cosmos",
        "LTC": "litecoin",
        "BCH": "bitcoin-cash",
        "NEAR": "near",
        "APT": "aptos",
        "ARB": "arbitrum",
        "OP": "optimism",
        "SUI": "sui",
        "FIL": "filecoin",
        "AAVE": "aave",
        "MKR": "maker",
        "SNX": "synthetix-network-token",
        "CRV": "curve-dao-token",
        "LDO": "lido-dao",
        "PEPE": "pepe",
        "SHIB": "shiba-inu",
        "WIF": "dogwifcoin",
        "BONK": "bonk",
        "INJ": "injective-protocol",
        "TIA": "celestia",
        "SEI": "sei-network",
        "RUNE": "thorchain",
        # Add more as needed
    }

    # Known stablecoins
    STABLECOINS = {
        "USDT", "USDC", "DAI", "BUSD", "TUSD", "USDD",
        "FRAX", "USDP", "GUSD", "LUSD", "SUSD"
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CoinGecko provider.

        Args:
            api_key: Optional CoinGecko API key for higher rate limits
        """
        self.api_key = api_key
        self.base_url = "https://api.coingecko.com/api/v3"
        self.rate_limit_delay = 1.2 if api_key else 6.0  # Seconds between requests
        self.last_request_time = 0.0

        logger.info(
            f"Initialized CoinGeckoDataProvider "
            f"({'with API key' if api_key else 'free tier'})"
        )

    def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Fetch market cap and volume data for multiple symbols.

        Args:
            symbols: List of symbols to fetch

        Returns:
            Dict mapping symbol to market data
        """
        result = {}

        # Get CoinGecko IDs for symbols
        coin_ids = []
        symbol_to_id_map = {}

        for symbol in symbols:
            if symbol in self.STABLECOINS:
                continue  # Skip stablecoins

            coin_id = self.SYMBOL_TO_ID.get(symbol)
            if coin_id:
                coin_ids.append(coin_id)
                symbol_to_id_map[coin_id] = symbol
            else:
                logger.debug(f"No CoinGecko ID mapping for {symbol}")

        if not coin_ids:
            return result

        # Fetch data in batches (CoinGecko allows up to 250 per request)
        batch_size = 250
        for i in range(0, len(coin_ids), batch_size):
            batch = coin_ids[i:i + batch_size]
            batch_data = self._fetch_markets_batch(batch)

            for coin_id, data in batch_data.items():
                symbol = symbol_to_id_map.get(coin_id)
                if symbol:
                    result[symbol] = data

        logger.info(f"Fetched CoinGecko data for {len(result)}/{len(symbols)} symbols")
        return result

    def _fetch_markets_batch(self, coin_ids: List[str]) -> Dict[str, Dict]:
        """
        Fetch market data for a batch of coin IDs.

        Returns:
            Dict mapping coin_id to market data
        """
        self._rate_limit()

        try:
            params = {
                "vs_currency": "usd",
                "ids": ",".join(coin_ids),
                "order": "market_cap_desc",
                "per_page": 250,
                "page": 1,
                "sparkline": "false"
            }

            if self.api_key:
                # Check if it's a demo key (starts with 'CG-') or pro key
                if self.api_key.startswith("CG-"):
                    # Demo keys use a different header or param, usually x_cg_demo_api_key header
                    # But per docs, can be passed as query param 'x_cg_demo_api_key'
                    params["x_cg_demo_api_key"] = self.api_key
                else:
                    # Pro keys use x_cg_pro_api_key
                    params["x_cg_pro_api_key"] = self.api_key

            response = requests.get(
                f"{self.base_url}/coins/markets",
                params=params,
                timeout=10
            )

            if response.status_code == 429:
                logger.warning("CoinGecko rate limit hit, waiting...")
                time.sleep(60)
                return self._fetch_markets_batch(coin_ids)

            response.raise_for_status()
            data = response.json()

            result = {}
            for coin in data:
                coin_id = coin.get("id")
                if not coin_id:
                    continue

                result[coin_id] = {
                    "market_cap_usd": coin.get("market_cap", 0) or 0,
                    "volume_24h_usd": coin.get("total_volume", 0) or 0,
                    "price_usd": coin.get("current_price", 0) or 0,
                    "price_change_24h_pct": coin.get("price_change_percentage_24h", 0) or 0,
                }

            return result

        except requests.RequestException as e:
            logger.error(f"Error fetching CoinGecko markets batch: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error in CoinGecko batch fetch: {e}")
            return {}

    def get_coin_id(self, symbol: str) -> Optional[str]:
        """
        Get CoinGecko ID for a symbol.

        Args:
            symbol: Coin symbol

        Returns:
            CoinGecko ID or None
        """
        return self.SYMBOL_TO_ID.get(symbol)

    def is_stablecoin(self, symbol: str) -> bool:
        """Check if a symbol is a known stablecoin"""
        return symbol in self.STABLECOINS

    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def add_symbol_mapping(self, symbol: str, coingecko_id: str):
        """
        Add a custom symbol to CoinGecko ID mapping.

        Args:
            symbol: Coin symbol
            coingecko_id: CoinGecko API ID
        """
        self.SYMBOL_TO_ID[symbol] = coingecko_id
        logger.info(f"Added mapping: {symbol} -> {coingecko_id}")
