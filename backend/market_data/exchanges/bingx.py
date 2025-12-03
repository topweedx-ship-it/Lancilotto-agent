import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class BingxProvider(BaseProvider):
    """
    Provider per BingX Swap.
    """
    BASE_URL = "https://open-api.bingx.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # BingX usa BTC-USDT
        pair = f"{symbol}-USDT"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/openApi/swap/v2/quote/ticker"
                params = {"symbol": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if data.get("code") != 0 or not data.get("data"):
                return {}
            
            ticker = data["data"]
            
            return {
                "price": float(ticker.get("lastPrice", 0)),
                "volume_24h": float(ticker.get("volume24h", 0)), # Volume 24h
                "funding_rate": float(ticker.get("fundingRate", 0)) if "fundingRate" in ticker else None,
                "open_interest": None,
                "source": "bingx_swap"
            }
        except Exception as e:
            logger.error(f"BingX fetch error for {symbol}: {e}")
            return {}




