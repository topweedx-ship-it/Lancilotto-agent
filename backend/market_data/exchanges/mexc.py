import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class MexcProvider(BaseProvider):
    """
    Provider per MEXC Futures.
    """
    BASE_URL = "https://contract.mexc.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # MEXC usa BTC_USDT
        pair = f"{symbol}_USDT"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/api/v1/contract/ticker"
                params = {"symbol": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if not data.get("success") or not data.get("data"):
                return {}
            
            ticker = data["data"]
            
            return {
                "price": float(ticker.get("lastPrice", 0)),
                "volume_24h": float(ticker.get("volume24", 0)), # Check unit (often base asset)
                "funding_rate": float(ticker.get("fundingRate", 0)),
                "open_interest": None,
                "source": "mexc_futures"
            }
        except Exception as e:
            logger.error(f"MEXC fetch error for {symbol}: {e}")
            return {}




