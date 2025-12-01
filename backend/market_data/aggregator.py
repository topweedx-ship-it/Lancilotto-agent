import asyncio
import importlib
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import yaml

# Try to import Hyperliquid provider from the project structure
try:
    from backend.coin_screener.data_providers.hyperliquid import HyperliquidDataProvider
except ImportError:
    # Fallback if running outside of standard package context
    try:
        import sys
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
        from backend.coin_screener.data_providers.hyperliquid import HyperliquidDataProvider
    except ImportError:
        HyperliquidDataProvider = None

logger = logging.getLogger(__name__)

class MarketDataAggregator:
    """
    Aggregator for market data from multiple exchanges (CEX/DEX).
    Collects spot and derivatives data to provide a global market context.
    """

    def __init__(self, config_path: str = "config/market_data.yaml"):
        self.providers: Dict[str, Any] = {}
        self.config = self._load_config(config_path)
        self._init_providers()
        
        # Hyperliquid is special as it's the primary trading venue
        # We use the existing data provider from coin_screener
        is_testnet = os.getenv("TESTNET", "true").lower() == "true"
        
        # Cache per Hyperliquid instance
        self.hyperliquid = None
        if HyperliquidDataProvider:
            try:
                # Singleton pattern: reuse instance if already available in bot_state or similar
                # For now, we create one instance per aggregator but we should ensure aggregator is singleton
                self.hyperliquid = HyperliquidDataProvider(testnet=is_testnet)
                logger.info(f"Hyperliquid provider initialized (Testnet: {is_testnet})")
            except Exception as e:
                logger.error(f"Failed to initialize Hyperliquid provider: {e}")
                self.hyperliquid = None
        else:
            logger.warning("HyperliquidDataProvider class not found. Hyperliquid data will be unavailable.")


    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load configuration from YAML or environment variables."""
        config = {
            "providers": [],
            "timeout": 5
        }
        
        # 1. Load from file if exists (relative to backend root or absolute)
        paths_to_try = [path, os.path.join("backend", path), os.path.join(os.getcwd(), path)]
        
        for p in paths_to_try:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        file_config = yaml.safe_load(f)
                        if file_config:
                            config.update(file_config)
                    logger.info(f"Loaded market data config from {p}")
                    break
                except Exception as e:
                    logger.error(f"Error loading config from {p}: {e}")

        # 2. Override/Augment from Environment Variables
        # Example: MARKET_DATA_PROVIDERS="binance,coinbase"
        env_providers = os.getenv("MARKET_DATA_PROVIDERS")
        if env_providers:
            config["providers"] = [p.strip() for p in env_providers.split(",") if p.strip()]
            
        return config

    def _init_providers(self):
        """
        Dynamically load and initialize configured providers.
        Expects providers to be in backend/market_data/exchanges/{name}.py
        """
        for provider_name in self.config.get("providers", []):
            try:
                # Construct module path (e.g., backend.market_data.exchanges.binance)
                module_path = f"backend.market_data.exchanges.{provider_name}"
                
                try:
                    module = importlib.import_module(module_path)
                except ImportError:
                    # Try relative import if we are inside the package
                    module = importlib.import_module(f".exchanges.{provider_name}", package="backend.market_data")
                
                # Convention: Class name is Capitalized name + "Provider" (e.g. BinanceProvider)
                # Special handling for names with underscore (crypto_com -> CryptoComProvider)
                class_name = "".join(x.capitalize() for x in provider_name.split("_")) + "Provider"
                
                if hasattr(module, class_name):
                    provider_class = getattr(module, class_name)
                    
                    # Instantiate provider
                    provider_instance = provider_class()
                    
                    # Check availability
                    is_available = True
                    if hasattr(provider_instance, "check_availability"):
                        is_available = provider_instance.check_availability()
                    
                    if is_available:
                        self.providers[provider_name] = provider_instance
                        logger.info(f"Initialized external provider: {provider_name}")
                    else:
                        logger.warning(f"Provider {provider_name} unavailable (check config/keys)")
                else:
                    logger.error(f"Class {class_name} not found in module {provider_name}")
                    
            except ImportError as e:
                logger.debug(f"Could not import provider module {provider_name}: {e}")
            except Exception as e:
                logger.error(f"Error initializing provider {provider_name}: {e}")

    async def fetch_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Main entry point: Fetch market data from all sources and aggregate.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 1. Fetch Hyperliquid Data (Primary Source)
        hl_task = self._fetch_hyperliquid_data(symbol)
        
        # 2. Fetch External Providers
        provider_tasks = []
        provider_names = []
        
        for name, provider in self.providers.items():
            provider_names.append(name)
            provider_tasks.append(self._safe_fetch_provider(name, provider, symbol))
            
        all_results = await asyncio.gather(hl_task, *provider_tasks, return_exceptions=True)
        
        hl_data = all_results[0]
        provider_results = all_results[1:]
        
        providers_data = {}
        for i, result in enumerate(provider_results):
            name = provider_names[i]
            if isinstance(result, Exception):
                logger.error(f"Provider {name} raised exception: {result}")
                providers_data[name] = {"error": str(result)}
            elif result:
                providers_data[name] = result
            else:
                providers_data[name] = None

        if isinstance(hl_data, Exception):
            logger.error(f"Hyperliquid fetch failed: {hl_data}")
            hl_data = {"error": str(hl_data)}

        # 3. Aggregate Metrics
        global_metrics = self._calculate_aggregates(hl_data, providers_data)
        
        return {
            "timestamp": timestamp,
            "symbol": symbol,
            "global_market": global_metrics,
            "hyperliquid": hl_data,
            "providers": providers_data
        }

    async def _fetch_hyperliquid_data(self, symbol: str) -> Dict[str, Any]:
        if not self.hyperliquid:
            return {"error": "Provider not initialized"}
            
        try:
            loop = asyncio.get_running_loop()
            metrics = await loop.run_in_executor(None, self.hyperliquid.get_coin_metrics, symbol)
            
            if metrics:
                return {
                    "price": metrics.price,
                    "volume_24h": metrics.volume_24h_usd,
                    "funding_rate": metrics.funding_rate,
                    "open_interest": metrics.open_interest_usd,
                    "spread_pct": metrics.spread_pct,
                    "atr_14": metrics.atr_14,
                    "source": "hyperliquid"
                }
            return {"status": "not_found", "symbol": symbol}
            
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid data: {e}")
            raise e

    async def _safe_fetch_provider(self, name: str, provider: Any, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            method_name = "get_market_data"
            if not hasattr(provider, method_name):
                method_name = "fetch_ticker"
                if not hasattr(provider, method_name):
                    return {"error": "Method not implemented"}

            method = getattr(provider, method_name)
            
            if asyncio.iscoroutinefunction(method):
                data = await method(symbol)
            else:
                loop = asyncio.get_running_loop()
                data = await loop.run_in_executor(None, method, symbol)
                
            return data
            
        except Exception as e:
            logger.error(f"Error in provider {name}: {e}")
            return {"error": str(e)}

    def _calculate_aggregates(self, hl_data: Dict, providers_data: Dict) -> Dict[str, Any]:
        prices = []
        volumes = []
        funding_rates = []
        
        all_sources = [hl_data] + list(providers_data.values())
        
        for data in all_sources:
            if not isinstance(data, dict) or "error" in data:
                continue
                
            p = data.get("price") or data.get("last") or data.get("close")
            if p and isinstance(p, (int, float, str)):
                try:
                    prices.append(float(p))
                except ValueError:
                    pass

            v = data.get("volume_24h") or data.get("volume")
            if v and isinstance(v, (int, float, str)):
                try:
                    volumes.append(float(v))
                except ValueError:
                    pass
            
            f = data.get("funding_rate")
            if f and isinstance(f, (int, float, str)):
                try:
                    funding_rates.append(float(f))
                except ValueError:
                    pass

        if not prices:
            return {"status": "insufficient_data"}

        avg_price = sum(prices) / len(prices)
        total_volume = sum(volumes)
        avg_funding = sum(funding_rates) / len(funding_rates) if funding_rates else 0.0
        
        hl_price = None
        hl_deviation = None
        if isinstance(hl_data, dict) and "price" in hl_data:
            hl_price = float(hl_data["price"])
            if avg_price > 0:
                hl_deviation = ((hl_price - avg_price) / avg_price) * 100

        return {
            "average_price": avg_price,
            "min_price": min(prices),
            "max_price": max(prices),
            "price_spread_pct": ((max(prices) - min(prices)) / min(prices)) * 100 if min(prices) > 0 else 0,
            "total_volume_global": total_volume,
            "average_funding_rate": avg_funding,
            "sources_count": len(prices),
            "hyperliquid_deviation_pct": hl_deviation,
            "is_hyperliquid_premium": hl_deviation > 0 if hl_deviation is not None else None
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        print("Initializing Market Data Aggregator...")
        aggregator = MarketDataAggregator()
        
        symbol = "BTC"
        print(f"\nFetching snapshot for {symbol}...")
        snapshot = await aggregator.fetch_market_snapshot(symbol)
        
        import json
        print("\n--- Market Snapshot ---")
        print(json.dumps(snapshot, indent=2, default=str))

    asyncio.run(main())
