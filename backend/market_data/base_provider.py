from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseProvider(ABC):
    """
    Interfaccia base per tutti i provider di dati di mercato.
    Ogni nuovo exchange deve ereditare da questa classe.
    """

    @abstractmethod
    def check_availability(self) -> bool:
        """
        Verifica se il provider è configurato correttamente e raggiungibile.
        Returns:
            bool: True se disponibile, False altrimenti.
        """
        pass

    @abstractmethod
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Ottiene i dati di mercato standardizzati per un simbolo.
        
        Args:
            symbol: Simbolo (es. 'BTC', 'ETH')
            
        Returns:
            Dict con chiavi standard:
            - price (float)
            - volume_24h (float)
            - funding_rate (float, opzionale)
            - open_interest (float, opzionale)
            - source (str)
        """
        pass




