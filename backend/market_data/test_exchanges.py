import unittest
import asyncio
import logging
from backend.market_data.exchanges.binance import BinanceProvider
from backend.market_data.exchanges.bybit import BybitProvider
from backend.market_data.exchanges.okx import OkxProvider
from backend.market_data.exchanges.coinbase import CoinbaseProvider
from backend.market_data.exchanges.mexc import MexcProvider

# Configura logging per vedere errori se ci sono
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestExchanges")

class TestExchangeProviders(unittest.IsolatedAsyncioTestCase):
    
    async def test_binance_provider(self):
        logger.info("Testing Binance Provider...")
        provider = BinanceProvider()
        data = await provider.get_market_data("BTC")
        self._validate_response(data, "binance")

    async def test_bybit_provider(self):
        logger.info("Testing Bybit Provider...")
        provider = BybitProvider()
        data = await provider.get_market_data("BTC")
        self._validate_response(data, "bybit")

    async def test_okx_provider(self):
        logger.info("Testing OKX Provider...")
        provider = OkxProvider()
        data = await provider.get_market_data("BTC")
        self._validate_response(data, "okx")

    async def test_coinbase_provider(self):
        logger.info("Testing Coinbase Provider...")
        provider = CoinbaseProvider()
        data = await provider.get_market_data("BTC")
        self._validate_response(data, "coinbase")

    async def test_mexc_provider(self):
        logger.info("Testing MEXC Provider...")
        provider = MexcProvider()
        data = await provider.get_market_data("BTC")
        self._validate_response(data, "mexc")

    def _validate_response(self, data, provider_name):
        """Helper per validare la struttura della risposta"""
        print(f"[{provider_name.upper()}] Response: {data}")
        
        self.assertIsInstance(data, dict, f"{provider_name} should return a dict")
        self.assertTrue(data, f"{provider_name} returned empty data")
        
        # Verifica campi obbligatori
        self.assertIn("price", data, f"{provider_name} missing price")
        self.assertIn("volume_24h", data, f"{provider_name} missing volume_24h")
        self.assertIn("source", data, f"{provider_name} missing source")
        
        # Verifica valori sensati
        self.assertIsInstance(data["price"], float)
        self.assertGreater(data["price"], 0, f"{provider_name} price should be > 0")
        
        if data["volume_24h"] is not None:
             self.assertIsInstance(data["volume_24h"], float)
             self.assertGreater(data["volume_24h"], 0, f"{provider_name} volume should be > 0")

if __name__ == "__main__":
    unittest.main()




