import logging
import aiohttp
from typing import Dict, Any
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class KrakenProvider(BaseProvider):
    """
    Provider per Kraken (Spot).
    """
    BASE_URL = "https://api.kraken.com"

    def check_availability(self) -> bool:
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # Kraken usa XBT invece di BTC a volte, ma accetta query BTCUSD
        pair = f"{symbol}USD"
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/0/public/Ticker"
                params = {"pair": pair}
                
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()

            if data.get("error"):
                return {}
            
            result = data.get("result", {})
            # La chiave nel result potrebbe essere strana (es. XXBTZUSD)
            # Prendiamo il primo valore del dizionario
            if not result:
                return {}
                
            ticker = list(result.values())[0]
            
            return {
                "price": float(ticker["c"][0]), # c = last trade closed [price, lot volume]
                "volume_24h": float(ticker["v"][1]), # v = volume [today, 24h]
                "funding_rate": None,
                "open_interest": None,
                "source": "kraken_spot"
            }
        except Exception as e:
            logger.error(f"Kraken fetch error for {symbol}: {e}")
            return {}




