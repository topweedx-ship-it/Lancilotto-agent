import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class CryptoComProvider(BaseProvider):
    """
    Provider per Crypto.com Exchange.
    """
    BASE_URL = "https://api.crypto.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # Crypto.com usa BTC_USDT
        pair = f"{symbol}_USDT"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/v2/public/get-ticker"
                params = {"instrument_name": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if data.get("code") != 0 or not data.get("result", {}).get("data"):
                return {}
            
            ticker = data["result"]["data"][0]
            
            return {
                "price": float(ticker.get("a", 0)), # a = latest trade price
                "volume_24h": float(ticker.get("v", 0)), # v = 24h volume
                "funding_rate": None,
                "open_interest": None,
                "source": "cryptocom_spot"
            }
        except Exception as e:
            logger.error(f"Crypto.com fetch error for {symbol}: {e}")
            return {}




