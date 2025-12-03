import logging
import aiohttp
from typing import Dict, Any, Optional
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class BinanceProvider(BaseProvider):
    """
    Provider per Binance Futures (USDT-M).
    Usa API pubbliche, non richiede API key per i dati di mercato.
    """
    
    BASE_URL = "https://fapi.binance.com"

    def check_availability(self) -> bool:
        # Le API pubbliche sono sempre "disponibili" a meno di blocchi IP
        return True

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        # Mappa simboli generici (BTC) ai simboli Binance (BTCUSDT)
        # Hyperliquid usa spesso solo il base asset name
        pair = f"{symbol}USDT"
        
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Ottieni Prezzo e Volume 24h
                ticker_url = f"{self.BASE_URL}/fapi/v1/ticker/24hr"
                async with session.get(ticker_url, params={"symbol": pair}, timeout=5) as resp:
                    if resp.status != 200:
                        logger.warning(f"Binance ticker failed for {pair}: {resp.status}")
                        return {}
                    ticker_data = await resp.json()

                # 2. Ottieni Funding Rate e Open Interest (opzionale, ma utile)
                # Facciamo una chiamata separata per il Premium Index che contiene il funding
                funding_url = f"{self.BASE_URL}/fapi/v1/premiumIndex"
                async with session.get(funding_url, params={"symbol": pair}, timeout=5) as resp:
                    funding_data = await resp.json() if resp.status == 200 else {}

            # Estrai dati
            return {
                "price": float(ticker_data.get("lastPrice", 0)),
                "volume_24h": float(ticker_data.get("quoteVolume", 0)), # Volume in USDT
                "funding_rate": float(funding_data.get("lastFundingRate", 0)) if funding_data else None,
                "open_interest": None, # Richiede altra chiamata, saltiamo per velocità
                "source": "binance_futures"
            }

        except Exception as e:
            logger.error(f"Error fetching Binance data for {symbol}: {e}")
            return {"error": str(e)}




