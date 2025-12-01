"""
Trading Agent - Decisioni AI con supporto multi-modello
"""
import json
import logging
import time
from typing import Optional, Dict, Any

from model_manager import get_model_manager
from token_tracker import get_token_tracker

logger = logging.getLogger(__name__)

# Costanti
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60

# JSON Schema per structured output
TRADE_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["open", "close", "hold"],
            "description": "Tipo di operazione trading"
        },
        "symbol": {
            "type": "string",
            "description": "Simbolo crypto su cui operare (es. BTC, ETH, SOL, AAVE)"
        },
        "direction": {
            "type": "string",
            "enum": ["long", "short"],
            "description": "Direzione: long (prezzo sale) o short (prezzo scende)"
        },
        "target_portion_of_balance": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Frazione del balance da usare (0.0-1.0)"
        },
        "leverage": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Leva da 1x a 10x"
        },
        "stop_loss_pct": {
            "type": "number",
            "minimum": 0.5,
            "maximum": 10,
            "description": "Stop-loss in percentuale dal prezzo di entry"
        },
        "take_profit_pct": {
            "type": "number",
            "minimum": 1,
            "maximum": 50,
            "description": "Take-profit in percentuale dal prezzo di entry"
        },
        "reason": {
            "type": "string",
            "minLength": 10,
            "maxLength": 500,
            "description": "Spiegazione della decisione"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Livello di confidenza (0-1)"
        }
    },
    "required": [
        "operation",
        "symbol",
        "direction",
        "target_portion_of_balance",
        "leverage",
        "stop_loss_pct",
        "take_profit_pct",
        "reason",
        "confidence"
    ],
    "additionalProperties": False
}


def previsione_trading_agent(
    prompt: str,
    max_retries: int = MAX_RETRIES,
    model_key: Optional[str] = None,
    cycle_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Chiama il modello AI selezionato per ottenere decisioni di trading strutturate.

    Args:
        prompt: System prompt con dati di mercato e portfolio
        max_retries: Numero massimo di tentativi
        model_key: Chiave del modello da usare (None = modello corrente)

    Returns:
        Dict con la decisione di trading

    Raises:
        RuntimeError: Se tutti i tentativi falliscono
    """
    model_manager = get_model_manager()
    
    # Determina il modello da usare
    if model_key:
        if not model_manager.is_model_available(model_key):
            logger.error(f"❌ Modello {model_key} non disponibile")
            model_key = None
    
    if not model_key:
        model_key = model_manager.get_current_model()
    
    model_config = model_manager.get_model_config(model_key)
    client = model_manager.get_client(model_key)
    
    if not client or not model_config:
        logger.error(f"❌ Client o configurazione non disponibile per {model_key}")
        raise RuntimeError(f"Modello {model_key} non disponibile")
    
    # Lista di modelli fallback (escludendo quello corrente)
    fallback_models = [m for m in model_manager.get_available_models() 
                      if m["id"] != model_key and m["available"]]
    
    last_error = None

    for attempt in range(max_retries):
        try:
            # Usa modello corrente per i primi tentativi, poi fallback
            if attempt == 0:
                current_model_key = model_key
            elif attempt < len(fallback_models) + 1:
                current_model_key = fallback_models[attempt - 1]["id"]
            else:
                current_model_key = model_key  # Ultimo tentativo con modello originale
            
            current_config = model_manager.get_model_config(current_model_key)
            current_client = model_manager.get_client(current_model_key)
            
            if not current_client or not current_config:
                continue
            
            logger.info(
                f"🤖 API call (attempt {attempt + 1}/{max_retries}, "
                f"model: {current_config.name} ({current_config.model_id}))"
            )

            # Misura tempo di risposta per tracking
            start_time = time.time()

            # Prepare system prompt based on model capabilities
            if current_config.supports_json_schema:
                # For models with json_schema, the prompt can be simpler
                system_content = "You are a professional trading AI. Analyze the data and respond ONLY with valid JSON according to the required schema."
            else:
                # For models without json_schema (e.g. DeepSeek), include the schema in the prompt
                system_content = """You are a professional trading AI. Analyze the data and respond EXCLUSIVELY with a valid JSON in this exact format:

{
  "operation": "open|close|hold",
  "symbol": "COIN_SYMBOL",
  "direction": "long|short",
  "target_portion_of_balance": 0.1,
  "leverage": 3,
  "stop_loss_pct": 2.0,
  "take_profit_pct": 5.0,
  "reason": "Detailed explanation of the decision",
  "confidence": 0.7
}

IMPORTANT: 
- operation must be one of: "open", "close", "hold"
- symbol must be the ticker of the analyzed coin (e.g. "BTC", "ETH", "SOL", "AAVE")
- direction must be "long" or "short"
- target_portion_of_balance: number between 0.0 and 1.0
- leverage: integer between 1 and 10
- stop_loss_pct: number between 0.5 and 10
- take_profit_pct: number between 1 and 50
- confidence: number between 0.0 and 1.0
- Respond ONLY with the JSON, without additional text."""

            # Prepara i parametri della richiesta
            request_params = {
                "model": current_config.model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": system_content
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Bassa per decisioni più consistenti
                "timeout": TIMEOUT_SECONDS
            }
            
            # Usa il parametro corretto per limitare i token di output
            # GPT-5.1 richiede max_completion_tokens, altri modelli usano max_tokens
            if current_config.use_max_completion_tokens:
                request_params["max_completion_tokens"] = 1000
            else:
                request_params["max_tokens"] = 1000
            
            # Aggiungi formato JSON appropriato
            if current_config.supports_json_schema:
                # Usa json_schema per modelli che lo supportano (OpenAI)
                request_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "trade_decision",
                        "strict": True,
                        "schema": TRADE_DECISION_SCHEMA
                    }
                }
            else:
                # Usa json_object per modelli che non supportano json_schema (es. DeepSeek)
                request_params["response_format"] = {"type": "json_object"}
            
            response = current_client.chat.completions.create(**request_params)

            # Calcola tempo di risposta
            response_time_ms = int((time.time() - start_time) * 1000)

            # Traccia utilizzo token
            try:
                tracker = get_token_tracker()
                usage = response.usage
                
                # Estrai simbolo dal prompt se possibile (per ticker)
                ticker = None
                if "symbol" in prompt.lower():
                    # Cerca simboli comuni nel prompt
                    for sym in ["BTC", "ETH", "SOL"]:
                        if sym in prompt:
                            ticker = sym
                            break
                
                tracker.track_usage(
                    model=current_config.model_id,
                    input_tokens=usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 0,
                    output_tokens=usage.completion_tokens if hasattr(usage, 'completion_tokens') else 0,
                    purpose="Trading Decision",
                    ticker=ticker,
                    cycle_id=cycle_id,
                    response_time_ms=response_time_ms
                )
            except Exception as e:
                # Non bloccare il flusso se il tracking fallisce
                logger.warning(f"⚠️ Errore tracking token: {e}")

            # Estrai risposta
            response_text = response.choices[0].message.content

            if not response_text:
                raise ValueError(f"Risposta vuota da {current_config.name}")

            # Parse JSON
            decision = json.loads(response_text)

            # Validazione aggiuntiva
            _validate_decision(decision)

            logger.info(
                f"✅ Decisione ({current_config.name}): {decision['operation']} {decision['symbol']} "
                f"{decision['direction']} (confidence: {decision['confidence']:.1%})"
            )
            
            # Aggiungi info sul modello usato alla risposta
            decision["_model_used"] = current_model_key
            decision["_model_name"] = current_config.name

            return decision

        except json.JSONDecodeError as e:
            last_error = e
            logger.error(f"❌ JSON parse error (attempt {attempt + 1}): {e}")

        except Exception as e:
            last_error = e
            logger.error(f"❌ API error (attempt {attempt + 1}): {e}")

        # Exponential backoff
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            logger.info(f"⏳ Waiting {wait_time}s before retry...")
            time.sleep(wait_time)

    # Tutti i tentativi falliti - ritorna decisione di sicurezza
    logger.error(f"❌ Tutti i {max_retries} tentativi falliti. Ultimo errore: {last_error}")

    return {
        "operation": "hold",
        "symbol": "BTC",
        "direction": "long",
        "target_portion_of_balance": 0.0,
        "leverage": 1,
        "stop_loss_pct": 2.0,
        "take_profit_pct": 4.0,
        "reason": f"Fallback a HOLD per errore API: {str(last_error)[:100]}",
        "confidence": 0.0
    }


def _validate_decision(decision: Dict[str, Any]) -> None:
    """
    Validazione aggiuntiva della decisione di trading.

    Raises:
        ValueError: Se la decisione non è valida
    """

    # Verifica R:R ratio
    sl_pct = decision.get('stop_loss_pct', 0)
    tp_pct = decision.get('take_profit_pct', 0)

    if sl_pct > 0:
        rr_ratio = tp_pct / sl_pct
        if rr_ratio < 1.0:
            logger.warning(f"⚠️ R:R ratio basso: {rr_ratio:.2f} (TP: {tp_pct}%, SL: {sl_pct}%)")

    # Verifica confidence
    confidence = decision.get('confidence', 0)
    if confidence < 0.3:
        logger.warning(f"⚠️ Confidence bassa: {confidence:.1%}")

    # Verifica position size con leva
    portion = decision.get('target_portion_of_balance', 0)
    leverage = decision.get('leverage', 1)
    effective_exposure = portion * leverage

    if effective_exposure > 0.5:
        logger.warning(f"⚠️ Esposizione elevata: {effective_exposure:.1%} (portion={portion:.1%}, leva={leverage}x)")


# Funzione di test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_prompt = """
    Portfolio: Balance $1000, nessuna posizione aperta.

    BTC: $95000, RSI=45, MACD positivo, trend rialzista.
    Sentiment: Fear & Greed = 35 (Fear)

    Decidi se aprire una posizione.
    """

    result = previsione_trading_agent(test_prompt)
    print(f"\n📊 Risultato test:\n{json.dumps(result, indent=2)}")
