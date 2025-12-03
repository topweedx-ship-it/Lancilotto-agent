import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class BitgetProvider(BaseProvider):
    """
    Provider per Bitget Futures (USDT-M).
    """
    BASE_URL = "https://api.bitget.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # Bitget symbol format: BTCUSDT_UMCBL
        pair = f"{symbol}USDT_UMCBL"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/api/mix/v1/market/ticker"
                params = {"symbol": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if data.get("retCode") != "00000" or not data.get("data"):
                return {}
            
            ticker = data["data"]
            
            return {
                "price": float(ticker.get("last", 0)),
                "volume_24h": float(ticker.get("usdtVolume", 0)), # Volume in quote currency
                "funding_rate": float(ticker.get("fundingRate", 0)), # A volte serve un'altra chiamata
                "open_interest": None,
                "source": "bitget_futures"
            }
        except Exception as e:
            logger.error(f"Bitget fetch error for {symbol}: {e}")
            return {}




