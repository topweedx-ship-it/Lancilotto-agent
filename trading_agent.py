"""
Trading Agent - Decisioni AI con OpenAI GPT-4o
"""
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import logging
import time
from typing import Optional, Dict, Any

load_dotenv()
logger = logging.getLogger(__name__)

# Configurazione
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY non trovata nel .env")

client = OpenAI(api_key=OPENAI_API_KEY)

# Costanti
MAX_RETRIES = 3
TIMEOUT_SECONDS = 60
PRIMARY_MODEL = "gpt-4o-2024-11-20"
FALLBACK_MODEL = "gpt-4o-mini"

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
            "enum": ["BTC", "ETH", "SOL"],
            "description": "Simbolo crypto su cui operare"
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


def previsione_trading_agent(prompt: str, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
    """
    Chiama OpenAI GPT-4o per ottenere decisioni di trading strutturate.

    Args:
        prompt: System prompt con dati di mercato e portfolio
        max_retries: Numero massimo di tentativi

    Returns:
        Dict con la decisione di trading

    Raises:
        RuntimeError: Se tutti i tentativi falliscono
    """

    last_error = None

    for attempt in range(max_retries):
        try:
            # Usa modello primario, fallback al secondo tentativo
            model = PRIMARY_MODEL if attempt < 2 else FALLBACK_MODEL

            logger.info(f"🤖 OpenAI API call (attempt {attempt + 1}/{max_retries}, model: {model})")

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un trading AI professionale. Analizza i dati e rispondi SOLO con JSON valido secondo lo schema richiesto."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "trade_decision",
                        "strict": True,
                        "schema": TRADE_DECISION_SCHEMA
                    }
                },
                temperature=0.3,  # Bassa per decisioni più consistenti
                max_tokens=1000,
                timeout=TIMEOUT_SECONDS
            )

            # Estrai risposta
            response_text = response.choices[0].message.content

            if not response_text:
                raise ValueError("Risposta vuota da OpenAI")

            # Parse JSON
            decision = json.loads(response_text)

            # Validazione aggiuntiva
            _validate_decision(decision)

            logger.info(
                f"✅ Decisione: {decision['operation']} {decision['symbol']} "
                f"{decision['direction']} (confidence: {decision['confidence']:.1%})"
            )

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
