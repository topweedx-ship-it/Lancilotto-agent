import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class GateProvider(BaseProvider):
    """
    Provider per Gate.io Futures (USDT-M).
    """
    BASE_URL = "https://api.gateio.ws"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # Gate usa format BTC_USDT
        pair = f"{symbol}_USDT"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/api/v4/futures/usdt/tickers"
                params = {"contract": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            # Gate ritorna una lista
            if not data or not isinstance(data, list):
                return {}
            
            ticker = data[0]
            
            return {
                "price": float(ticker.get("last", 0)),
                "volume_24h": float(ticker.get("volume_24h_quote", 0)), # Volume in quote (USDT)
                "funding_rate": float(ticker.get("funding_rate", 0)),
                "open_interest": float(ticker.get("total_size", 0)), # Check unit
                "source": "gate_futures"
            }
        except Exception as e:
            logger.error(f"Gate fetch error for {symbol}: {e}")
            return {}




