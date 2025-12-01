"""
Utility functions for Hyperliquid API initialization with rate limiting handling.
"""
import time
import logging
from hyperliquid.info import Info
from hyperliquid.utils.error import ClientError

logger = logging.getLogger(__name__)


def init_info_with_retry(base_url: str, skip_ws: bool = True, max_retries: int = 10) -> Info:
    """
    Inizializza Info con retry logic per gestire rate limiting.
    
    Il costruttore di Info chiama spot_meta() che può ricevere 429.
    
    Args:
        base_url: URL base dell'API Hyperliquid
        skip_ws: Se saltare WebSocket
        max_retries: Numero massimo di tentativi
        
    Returns:
        Istanza di Info inizializzata
        
    Raises:
        ClientError: Se tutti i retry falliscono
        RuntimeError: Se l'inizializzazione fallisce dopo tutti i retry
    """
    retry_delay = 10  # seconds - aumentato significativamente per rate limit severi
    
    for attempt in range(max_retries):
        try:
            return Info(base_url, skip_ws=skip_ws)
        except ClientError as e:
            error_args = e.args[0] if e.args else None
            # Check for 429 Too Many Requests
            if isinstance(error_args, tuple) and len(error_args) > 0 and error_args[0] == 429:
                if attempt < max_retries - 1:
                    # Exponential backoff con cap a 120 secondi: 10, 20, 40, 80, 120, 120, ...
                    # Dopo 5 tentativi, usa sempre 120 secondi
                    if attempt < 4:
                        wait_time = retry_delay * (2 ** attempt)
                    else:
                        wait_time = 120  # 2 minuti per tentativi successivi
                    logger.warning(f"Rate limit (429) durante inizializzazione Info, retry in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    logger.warning(f"⚠️ Rate limiting molto severo - potrebbe richiedere diversi minuti per inizializzare")
                    time.sleep(wait_time)
                    continue
            # Se non è 429 o abbiamo esaurito i retry, rilanciamo l'errore
            logger.error(f"Errore ClientError dopo {max_retries} tentativi: {e}")
            raise
        except Exception as e:
            # Per altri errori, proviamo comunque a ritentare
            if attempt < max_retries - 1:
                wait_time = min(retry_delay * (attempt + 1), 30)
                logger.warning(f"Errore durante inizializzazione Info: {e}, retry in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            logger.error(f"Errore dopo {max_retries} tentativi: {e}")
            raise
    
    # Non dovrebbe mai arrivare qui, ma per sicurezza
    raise RuntimeError("Failed to initialize Info after all retries")

