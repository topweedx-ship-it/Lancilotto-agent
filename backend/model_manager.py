"""
Model Manager - Gestione multi-modello per trading agent
Supporta: OpenAI (gpt-5.1, gpt-4o-mini) e DeepSeek
"""
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
from typing import Optional, Dict, Any, List
from enum import Enum

load_dotenv()
logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Provider dei modelli disponibili"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class ModelConfig:
    """Configurazione di un modello"""
    def __init__(
        self,
        name: str,
        provider: ModelProvider,
        model_id: str,
        api_key_env: str,
        base_url: Optional[str] = None,
        supports_json_schema: bool = True,
        supports_reasoning: bool = False,
        use_max_completion_tokens: bool = False
    ):
        self.name = name
        self.provider = provider
        self.model_id = model_id
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.supports_json_schema = supports_json_schema
        self.supports_reasoning = supports_reasoning
        self.use_max_completion_tokens = use_max_completion_tokens


# Configurazione modelli disponibili
AVAILABLE_MODELS: Dict[str, ModelConfig] = {
    "gpt-5.1": ModelConfig(
        name="GPT-5.1",
        provider=ModelProvider.OPENAI,
        model_id="gpt-5.1-2025-11-13",
        api_key_env="OPENAI_API_KEY",
        supports_json_schema=True,
        supports_reasoning=True,
        use_max_completion_tokens=True  # GPT-5.1 richiede max_completion_tokens invece di max_tokens
    ),
    "gpt-4o-mini": ModelConfig(
        name="GPT-4o Mini",
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
        supports_json_schema=True,
        supports_reasoning=False
    ),
    "deepseek": ModelConfig(
        name="DeepSeek V3",
        provider=ModelProvider.DEEPSEEK,
        model_id="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
        supports_json_schema=False,  # DeepSeek non supporta json_schema nativo, usa json_object
        supports_reasoning=False
    ),
    "deepseek-reasoner": ModelConfig(
        name="DeepSeek R1 (Reasoner)",
        provider=ModelProvider.DEEPSEEK,
        model_id="deepseek-reasoner",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
        supports_json_schema=False,
        supports_reasoning=True
    )
}

# Modello di default
DEFAULT_MODEL = "deepseek"


class ModelManager:
    """Gestore centralizzato per i modelli AI"""
    
    def __init__(self):
        self._clients: Dict[str, OpenAI] = {}
        self._initialize_clients()
        
        # Controlla se c'è un modello impostato via env, altrimenti usa il default
        env_model = os.getenv("DEFAULT_AI_MODEL", DEFAULT_MODEL)
        
        # Verifica che il modello da env sia valido e disponibile
        if env_model != DEFAULT_MODEL:
            if env_model not in AVAILABLE_MODELS:
                logger.warning(
                    f"⚠️ Modello {env_model} da DEFAULT_AI_MODEL non valido. "
                    f"Usando default: {DEFAULT_MODEL}"
                )
                self.current_model = DEFAULT_MODEL
            elif not self.is_model_available(env_model):
                logger.warning(
                    f"⚠️ Modello {env_model} da DEFAULT_AI_MODEL non disponibile. "
                    f"Usando default: {DEFAULT_MODEL}"
                )
                self.current_model = DEFAULT_MODEL
            else:
                self.current_model = env_model
                logger.info(f"✅ Modello da env impostato: {env_model}")
        else:
            self.current_model = DEFAULT_MODEL
    
    def _initialize_clients(self) -> None:
        """Inizializza i client per tutti i modelli disponibili"""
        for model_key, config in AVAILABLE_MODELS.items():
            try:
                api_key = os.getenv(config.api_key_env)
                if not api_key:
                    logger.warning(f"⚠️ API key non trovata per {config.name} ({config.api_key_env})")
                    continue
                
                client_kwargs = {"api_key": api_key}
                if config.base_url:
                    client_kwargs["base_url"] = config.base_url
                
                self._clients[model_key] = OpenAI(**client_kwargs)
                logger.info(f"✅ Client inizializzato per {config.name}")
            except Exception as e:
                logger.error(f"❌ Errore inizializzazione client {config.name}: {e}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Restituisce la lista dei modelli disponibili"""
        models = []
        for model_key, config in AVAILABLE_MODELS.items():
            api_key = os.getenv(config.api_key_env)
            models.append({
                "id": model_key,
                "name": config.name,
                "model_id": config.model_id,
                "provider": config.provider.value,
                "available": api_key is not None,
                "supports_json_schema": config.supports_json_schema,
                "supports_reasoning": config.supports_reasoning
            })
        return models
    
    def get_current_model(self) -> str:
        """Restituisce il modello corrente"""
        return self.current_model
    
    def set_current_model(self, model_key: str) -> bool:
        """Imposta il modello corrente"""
        if model_key not in AVAILABLE_MODELS:
            logger.error(f"❌ Modello {model_key} non disponibile")
            return False
        
        config = AVAILABLE_MODELS[model_key]
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            logger.error(f"❌ API key non disponibile per {config.name}")
            return False
        
        if model_key not in self._clients:
            logger.error(f"❌ Client non inizializzato per {config.name}")
            return False
        
        self.current_model = model_key
        logger.info(f"✅ Modello impostato su {config.name} ({config.model_id})")
        return True
    
    def get_client(self, model_key: Optional[str] = None) -> Optional[OpenAI]:
        """Restituisce il client per il modello specificato o corrente"""
        model = model_key or self.current_model
        return self._clients.get(model)
    
    def get_model_config(self, model_key: Optional[str] = None) -> Optional[ModelConfig]:
        """Restituisce la configurazione del modello"""
        model = model_key or self.current_model
        return AVAILABLE_MODELS.get(model)
    
    def is_model_available(self, model_key: str) -> bool:
        """Verifica se un modello è disponibile"""
        if model_key not in AVAILABLE_MODELS:
            return False
        config = AVAILABLE_MODELS[model_key]
        api_key = os.getenv(config.api_key_env)
        return api_key is not None and model_key in self._clients


# Istanza globale del model manager
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Restituisce l'istanza globale del model manager"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager

