import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class HtxProvider(BaseProvider):
    """
    Provider per HTX (Huobi) Linear Swap.
    """
    BASE_URL = "https://api.hbdm.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # HTX usa BTC-USDT
        pair = f"{symbol}-USDT"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/linear-swap-ex/market/detail/merged"
                params = {"contract_code": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if data.get("status") != "ok" or not data.get("tick"):
                return {}
            
            tick = data["tick"]
            
            return {
                "price": float(tick.get("close", 0)),
                "volume_24h": float(tick.get("vol", 0)), # Trade turnover
                "funding_rate": None,
                "open_interest": float(tick.get("amount", 0)) if "amount" in tick else None,
                "source": "htx_swap"
            }
        except Exception as e:
            logger.error(f"HTX fetch error for {symbol}: {e}")
            return {}




