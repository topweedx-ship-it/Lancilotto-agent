"""
Trading Agent - Main Entry Point
Versione con Risk Management e Scheduler integrati
"""
import logging
import sys
import os
import json
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

# Setup logging PRIMA di tutto
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Imports dei moduli
from indicators import analyze_multiple_tickers
from news_feed import fetch_latest_news
from trading_agent import previsione_trading_agent
from sentiment import get_sentiment
from forecaster import get_crypto_forecasts
from hyperliquid_trader import HyperLiquidTrader
from risk_manager import RiskManager, RiskConfig
from scheduler import TradingScheduler
import db_utils

# ============================================================
#                      CONFIGURAZIONE
# ============================================================

CONFIG = {
    # Trading
    "TESTNET": True,
    "TICKERS": ["BTC", "ETH", "SOL"],
    "CYCLE_INTERVAL_MINUTES": 3,

    # Risk Management
    "MAX_DAILY_LOSS_USD": 500.0,
    "MAX_DAILY_LOSS_PCT": 5.0,
    "MAX_POSITION_PCT": 30.0,
    "DEFAULT_STOP_LOSS_PCT": 2.0,
    "DEFAULT_TAKE_PROFIT_PCT": 5.0,
    "MAX_CONSECUTIVE_LOSSES": 3,

    # Execution
    "MIN_CONFIDENCE": 0.4,  # Non eseguire trade con confidence < 40%
}

# Credenziali
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

if not PRIVATE_KEY or not WALLET_ADDRESS:
    logger.error("❌ PRIVATE_KEY o WALLET_ADDRESS mancanti nel .env")
    sys.exit(1)


# ============================================================
#                    STATO GLOBALE
# ============================================================

class BotState:
    """Stato globale del bot"""

    def __init__(self):
        self.trader: Optional[HyperLiquidTrader] = None
        self.risk_manager: Optional[RiskManager] = None
        self.initialized: bool = False
        self.last_error: Optional[str] = None

    def initialize(self) -> bool:
        """Inizializza tutti i componenti"""
        if self.initialized:
            return True

        try:
            logger.info("🔧 Inizializzazione componenti...")

            # Database
            db_utils.init_db()
            logger.info("✅ Database inizializzato")

            # Trader
            self.trader = HyperLiquidTrader(
                secret_key=PRIVATE_KEY,
                account_address=WALLET_ADDRESS,
                testnet=CONFIG["TESTNET"]
            )
            logger.info(f"✅ HyperLiquid Trader inizializzato ({'testnet' if CONFIG['TESTNET'] else 'mainnet'})")

            # Risk Manager
            risk_config = RiskConfig(
                max_daily_loss_pct=CONFIG["MAX_DAILY_LOSS_PCT"],
                max_daily_loss_usd=CONFIG["MAX_DAILY_LOSS_USD"],
                max_position_pct=CONFIG["MAX_POSITION_PCT"],
                default_stop_loss_pct=CONFIG["DEFAULT_STOP_LOSS_PCT"],
                default_take_profit_pct=CONFIG["DEFAULT_TAKE_PROFIT_PCT"],
                max_consecutive_losses=CONFIG["MAX_CONSECUTIVE_LOSSES"]
            )
            self.risk_manager = RiskManager(config=risk_config)
            logger.info("✅ Risk Manager inizializzato")

            self.initialized = True
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ Errore inizializzazione: {e}", exc_info=True)
            return False


# Istanza globale
bot_state = BotState()


# ============================================================
#                    CICLO DI TRADING
# ============================================================

def trading_cycle() -> None:
    """
    Ciclo principale di trading:
    1. Fetch dati di mercato
    2. Costruisci prompt
    3. Ottieni decisione AI
    4. Verifica con risk manager
    5. Esegui trade
    6. Logga tutto
    """

    # Inizializza se necessario
    if not bot_state.initialized:
        if not bot_state.initialize():
            logger.error("❌ Impossibile inizializzare il bot")
            return

    trader = bot_state.trader
    risk_manager = bot_state.risk_manager

    # Variabili per error logging
    indicators_json = []
    news_txt = ""
    sentiment_json = {}
    forecasts_json = []
    account_status = {}
    system_prompt = ""

    try:
        # ========================================
        # 1. FETCH DATI DI MERCATO
        # ========================================
        logger.info("📡 Recupero dati di mercato...")

        # Indicatori tecnici
        try:
            indicators_txt, indicators_json = analyze_multiple_tickers(CONFIG["TICKERS"])
            logger.info(f"✅ Indicatori tecnici per {len(CONFIG['TICKERS'])} ticker")
        except Exception as e:
            logger.warning(f"⚠️ Errore indicatori: {e}")
            indicators_txt = "Dati indicatori non disponibili"

        # News
        try:
            news_txt = fetch_latest_news()
            logger.info(f"✅ News ({len(news_txt)} caratteri)")
        except Exception as e:
            logger.warning(f"⚠️ Errore news: {e}")
            news_txt = "News non disponibili"

        # Sentiment
        try:
            sentiment_txt, sentiment_json = get_sentiment()
            logger.info(f"✅ Sentiment: {sentiment_json.get('classificazione', 'N/A')}")
        except Exception as e:
            logger.warning(f"⚠️ Errore sentiment: {e}")
            sentiment_txt = "Sentiment non disponibile"
            sentiment_json = {}

        # Forecast
        try:
            forecasts_txt, forecasts_json = get_crypto_forecasts()
            logger.info("✅ Forecast recuperati")
        except Exception as e:
            logger.warning(f"⚠️ Errore forecast: {e}")
            forecasts_txt = "Forecast non disponibili"
            forecasts_json = []

        # ========================================
        # 2. STATO ACCOUNT
        # ========================================
        account_status = trader.get_account_status()
        balance_usd = account_status.get("balance_usd", 0)
        open_positions = account_status.get("open_positions", [])

        logger.info(f"💰 Balance: ${balance_usd:.2f}, Posizioni aperte: {len(open_positions)}")

        # Log snapshot
        try:
            snapshot_id = db_utils.log_account_status(account_status)
            logger.debug(f"📝 Account snapshot salvato (ID: {snapshot_id})")
        except Exception as e:
            logger.warning(f"⚠️ Errore salvataggio snapshot: {e}")

        # ========================================
        # 3. CHECK SL/TP POSIZIONI ESISTENTI
        # ========================================
        if open_positions:
            current_prices = trader.get_current_prices(CONFIG["TICKERS"])
            positions_to_close = risk_manager.check_positions(current_prices)

            for close_info in positions_to_close:
                symbol = close_info["symbol"]
                reason = close_info["reason"]
                pnl = close_info["pnl"]

                logger.warning(f"⚠️ {reason.upper()} trigger per {symbol}, PnL: ${pnl:.2f}")

                # Chiudi posizione
                try:
                    close_result = trader.exchange.market_close(symbol)
                    logger.info(f"✅ Posizione {symbol} chiusa: {close_result}")

                    # Registra risultato
                    risk_manager.record_trade_result(pnl, was_stop_loss=(reason == "stop_loss"))
                    risk_manager.remove_position(symbol)

                except Exception as e:
                    logger.error(f"❌ Errore chiusura {symbol}: {e}")

        # ========================================
        # 4. COSTRUISCI PROMPT
        # ========================================
        msg_info = f"""<indicatori>
{indicators_txt}
</indicatori>

<news>
{news_txt}
</news>

<sentiment>
{sentiment_txt}
</sentiment>

<forecast>
{forecasts_txt}
</forecast>"""

        # Aggiungi stato risk manager
        risk_status = risk_manager.get_status()
        msg_info += f"""

<risk_status>
Daily P&L: ${risk_status['daily_pnl']:.2f}
Perdite consecutive: {risk_status['consecutive_losses']}
Circuit breaker: {'ATTIVO' if risk_status['circuit_breaker_active'] else 'inattivo'}
</risk_status>"""

        # Load system prompt template
        with open('system_prompt.txt', 'r') as f:
            system_prompt_template = f.read()

        portfolio_data = json.dumps(account_status, indent=2)
        system_prompt = system_prompt_template.format(portfolio_data, msg_info)

        # ========================================
        # 5. DECISIONE AI
        # ========================================
        logger.info("🤖 Richiesta decisione all'AI...")

        decision = previsione_trading_agent(system_prompt)

        operation = decision.get("operation", "hold")
        symbol = decision.get("symbol", "BTC")
        direction = decision.get("direction", "long")
        confidence = decision.get("confidence", 0)
        reason = decision.get("reason", "")

        logger.info(
            f"🎯 Decisione AI: {operation} {symbol} {direction} "
            f"(confidence: {confidence:.1%})"
        )
        logger.info(f"📝 Motivazione: {reason[:100]}...")

        # ========================================
        # 6. ESECUZIONE CON RISK MANAGEMENT
        # ========================================
        result = {"status": "skipped"}

        if operation == "hold":
            logger.info("⏸️ HOLD - Nessuna azione")
            result = {"status": "hold", "reason": reason}

        elif confidence < CONFIG["MIN_CONFIDENCE"]:
            logger.warning(
                f"⚠️ Confidence troppo bassa ({confidence:.1%} < {CONFIG['MIN_CONFIDENCE']:.1%}), skip"
            )
            result = {"status": "skipped", "reason": f"Low confidence: {confidence:.1%}"}

        else:
            # Verifica con risk manager
            can_trade = risk_manager.can_open_position(balance_usd)

            if not can_trade["allowed"] and operation == "open":
                logger.warning(f"⛔ Trade bloccato: {can_trade['reason']}")
                result = {"status": "blocked", "reason": can_trade["reason"]}
            else:
                # Esegui con risk management
                try:
                    result = trader.execute_signal_with_risk(
                        order_json=decision,
                        risk_manager=risk_manager,
                        balance_usd=balance_usd
                    )

                    if result.get("status") == "ok" or "statuses" in result:
                        logger.info(f"✅ Trade eseguito: {result}")
                    else:
                        logger.warning(f"⚠️ Risultato trade: {result}")

                except Exception as e:
                    logger.error(f"❌ Errore esecuzione trade: {e}")
                    result = {"status": "error", "error": str(e)}

        # ========================================
        # 7. LOG SU DATABASE
        # ========================================
        try:
            op_id = db_utils.log_bot_operation(
                operation_payload=decision,
                system_prompt=system_prompt,
                indicators=indicators_json,
                news_text=news_txt,
                sentiment=sentiment_json,
                forecasts=forecasts_json
            )
            logger.info(f"📝 Operazione salvata (ID: {op_id})")
        except Exception as e:
            logger.error(f"❌ Errore salvataggio operazione: {e}")

    except Exception as e:
        logger.error(f"❌ ERRORE CRITICO nel ciclo: {e}", exc_info=True)

        # Log errore su database
        try:
            db_utils.log_error(
                e,
                context={
                    "indicators": indicators_json,
                    "news": news_txt[:500] if news_txt else None,
                    "sentiment": sentiment_json,
                    "forecasts": forecasts_json,
                    "account": account_status
                },
                source="trading_cycle"
            )
        except:
            pass


def health_check() -> None:
    """Health check per verificare connettività"""
    try:
        if bot_state.trader:
            mids = bot_state.trader.info.all_mids()
            logger.debug(f"✅ Health check: {len(mids)} simboli disponibili")
    except Exception as e:
        logger.warning(f"⚠️ Health check fallito: {e}")


# ============================================================
#                      ENTRY POINT
# ============================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 TRADING AGENT - Avvio")
    logger.info("=" * 60)
    logger.info(f"📋 Configurazione: {json.dumps(CONFIG, indent=2)}")

    try:
        # Inizializza
        if not bot_state.initialize():
            logger.error("❌ Inizializzazione fallita")
            sys.exit(1)

        # Avvia scheduler
        scheduler = TradingScheduler(
            trading_func=trading_cycle,
            interval_minutes=CONFIG["CYCLE_INTERVAL_MINUTES"],
            health_check_func=health_check
        )

        scheduler.start()

    except KeyboardInterrupt:
        logger.info("🛑 Interruzione manuale")
    except Exception as e:
        logger.error(f"❌ Errore fatale: {e}", exc_info=True)
        sys.exit(1)
