import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class BybitProvider(BaseProvider):
    """
    Provider per Bybit V5 API (Linear Perpetuals).
    """
    BASE_URL = "https://api.bybit.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        pair = f"{symbol}USDT"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/v5/market/tickers"
                params = {"category": "linear", "symbol": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if data["retCode"] != 0 or not data["result"]["list"]:
                return {}

            ticker = data["result"]["list"][0]
            
            return {
                "price": float(ticker.get("lastPrice", 0)),
                "volume_24h": float(ticker.get("turnover24h", 0)), # Turnover è volume in USD
                "funding_rate": float(ticker.get("fundingRate", 0)),
                "open_interest": float(ticker.get("openInterestValue", 0)),
                "source": "bybit_linear"
            }
        except Exception as e:
            logger.error(f"Bybit fetch error for {symbol}: {e}")
            return {}




