import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class OkxProvider(BaseProvider):
    """
    Provider per OKX API V5 (Swap/Perpetuals).
    """
    BASE_URL = "https://www.okx.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        inst_id = f"{symbol}-USDT-SWAP"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/api/v5/market/ticker"
                params = {"instId": inst_id}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if data["code"] != "0" or not data["data"]:
                return {}

            ticker = data["data"][0]
            
            # OKX non fornisce il funding rate nel ticker, serve altra chiamata
            # Per semplicità qui prendiamo prezzo e volume, funding richiederebbe /public/funding-rate
            
            return {
                "price": float(ticker.get("last", 0)),
                "volume_24h": float(ticker.get("volCcy24h", 0)), # Volume in valuta quote (USDT)
                "funding_rate": None, # Richiede chiamata extra
                "open_interest": None,
                "source": "okx_swap"
            }
        except Exception as e:
            logger.error(f"OKX fetch error for {symbol}: {e}")
            return {}




