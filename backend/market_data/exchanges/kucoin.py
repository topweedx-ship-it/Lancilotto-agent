import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class KucoinProvider(BaseProvider):
    """
    Provider per KuCoin Futures.
    """
    BASE_URL = "https://api-futures.kucoin.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # KuCoin Futures usa XBTUSDTM per BTC
        s = "XBT" if symbol == "BTC" else symbol
        pair = f"{s}USDTM"
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/api/v1/ticker"
                params = {"symbol": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if data.get("code") != "200000" or not data.get("data"):
                return {}
            
            ticker = data["data"]
            
            return {
                "price": float(ticker.get("price", 0)),
                "volume_24h": float(ticker.get("volume", 0)), # Check if quote or base
                "funding_rate": None, # Richiede altra chiamata
                "open_interest": None,
                "source": "kucoin_futures"
            }
        except Exception as e:
            logger.error(f"KuCoin fetch error for {symbol}: {e}")
            return {}




