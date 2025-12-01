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
log_filename = "trading_agent.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename, mode='a', encoding='utf-8')
    ]
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
from whalealert import fetch_whale_alerts_from_api
import db_utils

# Coin screener
from coin_screener import CoinScreener

# Trend confirmation (Phase 2)
from trend_confirmation import TrendConfirmationEngine

# Notifiche Telegram
from notifications import notifier

# ============================================================
#                      CONFIGURAZIONE
# ============================================================

# Leggi TESTNET da variabile d'ambiente (default: True)
TESTNET_ENV = os.getenv("TESTNET", "true").lower()
CONFIG = {
    # Trading
    "TESTNET": TESTNET_ENV in ("true", "1", "yes"),
    "TICKERS": ["BTC", "ETH", "SOL"],
    "CYCLE_INTERVAL_MINUTES": 5,

    # Coin Screening
    "SCREENING_ENABLED": True,  # Set to True to enable dynamic coin selection
    "TOP_N_COINS": 5,
    "REBALANCE_DAY": "sunday",
    "FALLBACK_TICKERS": ["BTC", "ETH", "SOL"],  # Used if screening fails or disabled

    # Trend Confirmation (Phase 2)
    "TREND_CONFIRMATION_ENABLED": True,  # Enable multi-timeframe trend confirmation
    "MIN_TREND_CONFIDENCE": 0.6,  # Minimum trend confidence to trade (0-1)
    "SKIP_POOR_ENTRY": True,  # Skip trades when entry_quality is "wait"
    "ADX_THRESHOLD": 25,  # ADX threshold for strong trends
    "RSI_OVERBOUGHT": 70,  # RSI overbought level
    "RSI_OVERSOLD": 30,  # RSI oversold level

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

# Credenziali - seleziona in base a TESTNET
IS_TESTNET = CONFIG["TESTNET"]

# Master Account Address (stesso per mainnet e testnet)
MASTER_ACCOUNT_ADDRESS = os.getenv("MASTER_ACCOUNT_ADDRESS")
if not MASTER_ACCOUNT_ADDRESS:
    logger.error("❌ MASTER_ACCOUNT_ADDRESS mancante nel .env")
    logger.error("   Questo è l'indirizzo del Master Account che contiene i fondi")
    logger.error("   Usato per le chiamate di lettura (Info API)")
    sys.exit(1)

if IS_TESTNET:
    PRIVATE_KEY = os.getenv("TESTNET_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
    WALLET_ADDRESS = os.getenv("TESTNET_WALLET_ADDRESS") or os.getenv("WALLET_ADDRESS")
    network_name = "TESTNET"
else:
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
    network_name = "MAINNET"

if not PRIVATE_KEY or not WALLET_ADDRESS:
    logger.error(f"❌ Credenziali mancanti per {network_name}")
    if IS_TESTNET:
        logger.error("   Richieste: TESTNET_PRIVATE_KEY e TESTNET_WALLET_ADDRESS")
        logger.error("   (o PRIVATE_KEY e WALLET_ADDRESS come fallback)")
        logger.error("   Testnet URL: https://app.hyperliquid-testnet.xyz/trade")
        logger.error("   Testnet Faucet: https://app.hyperliquid-testnet.xyz/drip")
    else:
        logger.error("   Richieste: PRIVATE_KEY e WALLET_ADDRESS")
    sys.exit(1)

logger.info(f"🌐 Modalità: {network_name}")
logger.info(f"   Master Account: {MASTER_ACCOUNT_ADDRESS}")
logger.info(f"   API Wallet: {WALLET_ADDRESS}")
if IS_TESTNET:
    logger.info(f"   Testnet URL: https://app.hyperliquid-testnet.xyz/trade")


# ============================================================
#                    STATO GLOBALE
# ============================================================

class BotState:
    """Stato globale del bot"""

    def __init__(self):
        self.trader: Optional[HyperLiquidTrader] = None
        self.risk_manager: Optional[RiskManager] = None
        self.screener: Optional[CoinScreener] = None
        self.trend_engine: Optional[TrendConfirmationEngine] = None
        self.active_trades: dict[str, int] = {}  # symbol -> trade_id mapping
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
                account_address=WALLET_ADDRESS,  # API wallet per Exchange (trading)
                master_account_address=MASTER_ACCOUNT_ADDRESS,  # Master Account per Info (lettura)
                testnet=CONFIG["TESTNET"]
            )
            logger.info(f"✅ HyperLiquid Trader inizializzato ({'testnet' if CONFIG['TESTNET'] else 'mainnet'})")
            logger.info(f"   Master Account: {MASTER_ACCOUNT_ADDRESS}")
            logger.info(f"   API Wallet: {WALLET_ADDRESS}")

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

            # Coin Screener (se abilitato)
            if CONFIG["SCREENING_ENABLED"]:
                self.screener = CoinScreener(
                    testnet=CONFIG["TESTNET"],
                    coingecko_api_key=os.getenv("COINGECKO_API_KEY"),
                    top_n=CONFIG["TOP_N_COINS"]
                )
                logger.info("✅ Coin Screener inizializzato")

                # Run migration for screener tables
                from coin_screener.db_migration import run_migration
                with db_utils.get_connection() as conn:
                    run_migration(conn)

            # Trend Confirmation Engine (se abilitato - Phase 2)
            if CONFIG["TREND_CONFIRMATION_ENABLED"]:
                self.trend_engine = TrendConfirmationEngine(testnet=CONFIG["TESTNET"])
                # Configure thresholds from CONFIG
                self.trend_engine.config['adx_threshold'] = CONFIG["ADX_THRESHOLD"]
                self.trend_engine.config['rsi_overbought'] = CONFIG["RSI_OVERBOUGHT"]
                self.trend_engine.config['rsi_oversold'] = CONFIG["RSI_OVERSOLD"]
                self.trend_engine.config['min_confidence'] = CONFIG["MIN_TREND_CONFIDENCE"]
                logger.info("✅ Trend Confirmation Engine inizializzato")
                logger.info(f"   ADX threshold: {CONFIG['ADX_THRESHOLD']}")
                logger.info(f"   Min confidence: {CONFIG['MIN_TREND_CONFIDENCE']}")

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
    screener = bot_state.screener

    # Variabili per error logging
    indicators_json = []
    news_txt = ""
    sentiment_json = {}
    forecasts_json = []
    whale_alerts_list = []
    account_status = {}
    system_prompt = ""

    try:
        # ========================================
        # 0. SELEZIONE COIN (se screening abilitato)
        # ========================================
        if CONFIG["SCREENING_ENABLED"] and screener:
            try:
                # Check se serve rebalance completo
                if screener.should_rebalance():
                    logger.info("🔄 Rebalance settimanale: eseguo screening completo...")
                    try:
                        result = screener.run_full_screening()

                        # Log su database
                        from coin_screener.db_utils import log_screening_result
                        with db_utils.get_connection() as conn:
                            log_screening_result(conn, result)
                    except Exception as e:
                        # Se lo screening completo fallisce (es. rate limit), prova a usare dati cached
                        logger.warning(f"⚠️ Screening completo fallito: {e}")
                        logger.info("📋 Provo a usare dati cached o fallback...")
                        selected_coins = screener.get_selected_coins(top_n=CONFIG["TOP_N_COINS"])
                        if selected_coins:
                            tickers = [coin.symbol for coin in selected_coins]
                            logger.info(f"🎯 Trading su coin cached: {', '.join(tickers)}")
                        else:
                            raise  # Se non ci sono dati cached, usa fallback
                else:
                    # Update giornaliero
                    logger.info("📊 Update giornaliero scores...")
                    try:
                        result = screener.update_scores()
                    except Exception as e:
                        # Se l'update fallisce, usa dati cached
                        logger.warning(f"⚠️ Update scores fallito: {e}, uso dati cached")
                        pass  # Continua con get_selected_coins che userà cache

                # Ottieni top coins (da cache se disponibile)
                selected_coins = screener.get_selected_coins(top_n=CONFIG["TOP_N_COINS"])
                if selected_coins:
                    tickers = [coin.symbol for coin in selected_coins]
                    logger.info(f"🎯 Trading su: {', '.join(tickers)}")
                else:
                    # Nessun dato disponibile, usa fallback
                    raise ValueError("Nessun dato disponibile dal screener")

            except Exception as e:
                logger.error(f"❌ Errore screening: {e}", exc_info=True)
                logger.info(f"📋 Uso fallback tickers: {CONFIG['FALLBACK_TICKERS']}")
                tickers = CONFIG["FALLBACK_TICKERS"]
        else:
            # Screening disabilitato, usa CONFIG["TICKERS"]
            tickers = CONFIG["TICKERS"]

        # ========================================
        # 1. FETCH DATI DI MERCATO
        # ========================================
        logger.info("📡 Recupero dati di mercato...")

        # Indicatori tecnici
        try:
            indicators_txt, indicators_json = analyze_multiple_tickers(
                tickers, 
                testnet=CONFIG["TESTNET"]
            )
            logger.info(f"✅ Indicatori tecnici per {len(tickers)} ticker")
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
            forecasts_txt, forecasts_json = get_crypto_forecasts(
                tickers=tickers,
                testnet=CONFIG["TESTNET"]
            )
            logger.info("✅ Forecast recuperati")
        except Exception as e:
            logger.warning(f"⚠️ Errore forecast: {e}")
            forecasts_txt = "Forecast non disponibili"
            forecasts_json = []

        # Whale Alerts
        try:
            whale_alerts_txt, whale_alerts_list = fetch_whale_alerts_from_api(max_alerts=10)
            logger.info(f"✅ Whale alerts recuperati: {len(whale_alerts_list)} alert")
        except Exception as e:
            logger.warning(f"⚠️ Errore whale alerts: {e}")
            whale_alerts_txt = "Whale alert non disponibili"
            whale_alerts_list = []

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
            current_prices = trader.get_current_prices(tickers)
            positions_to_close = risk_manager.check_positions(current_prices)

            for close_info in positions_to_close:
                symbol = close_info["symbol"]
                reason = close_info["reason"]
                pnl = close_info["pnl"]

                logger.warning(f"⚠️ {reason.upper()} trigger per {symbol}, PnL: ${pnl:.2f}")

                # Chiudi posizione usando execute_signal_with_risk per avere la gestione completa
                try:
                    close_order = {
                        "operation": "close",
                        "symbol": symbol,
                        "direction": "long"  # Non importante per close, ma richiesto
                    }

                    close_result = trader.execute_signal_with_risk(
                        close_order,
                        risk_manager,
                        balance_usd
                    )

                    # Gestisci diversi tipi di risultato
                    if close_result is None:
                        logger.error(f"❌ Chiusura {symbol} ritornato None - posizione potrebbe essere ancora aperta")
                        # NON rimuovere dal tracking se la chiusura fallisce
                    elif isinstance(close_result, dict):
                        status = close_result.get("status", "unknown")
                        if status == "skipped":
                            logger.info(f"ℹ️ {close_result.get('message', f'Posizione {symbol} già chiusa')}")
                            risk_manager.remove_position(symbol)
                            # Log trade closure (position already closed)
                            if symbol in bot_state.active_trades:
                                try:
                                    db_utils.close_trade(
                                        trade_id=bot_state.active_trades[symbol],
                                        exit_price=current_prices.get(symbol, 0),
                                        exit_reason="manual",  # Already closed outside bot
                                        pnl_usd=0,
                                        pnl_pct=0
                                    )
                                    del bot_state.active_trades[symbol]
                                except Exception as log_err:
                                    logger.warning(f"⚠️ Errore logging chiusura trade {symbol}: {log_err}")
                        elif status == "error":
                            error_msg = close_result.get("message", "Errore sconosciuto")
                            symbol_used = close_result.get("symbol_used", symbol)
                            logger.error(f"❌ Errore chiusura {symbol} (simbolo usato: {symbol_used}): {error_msg}")
                            logger.warning(f"⚠️ Posizione {symbol} NON rimossa dal tracking - verifica manualmente")
                            # NON rimuovere dal tracking se la chiusura fallisce
                        elif status == "ok":
                            method = close_result.get("method", "standard")
                            logger.info(f"✅ Posizione {symbol} chiusa ({method}): {close_result.get('message', '')}")
                            # Registra risultato solo se la chiusura è andata a buon fine
                            risk_manager.record_trade_result(pnl, was_stop_loss=(reason == "stop_loss"))
                            risk_manager.remove_position(symbol)
                            # Log trade closure
                            if symbol in bot_state.active_trades:
                                try:
                                    # Get position info for P&L calculation
                                    position = next((p for p in open_positions if p["symbol"] == symbol), None)
                                    entry_price = position.get("entry_price", 0) if position else 0
                                    exit_price = close_result.get("fill_price") or current_prices.get(symbol, 0)
                                    pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price else None

                                    db_utils.close_trade(
                                        trade_id=bot_state.active_trades[symbol],
                                        exit_price=exit_price,
                                        exit_reason="stop_loss" if reason == "stop_loss" else "take_profit",
                                        pnl_usd=pnl,
                                        pnl_pct=pnl_pct,
                                        fees_usd=close_result.get("fees", 0)
                                    )
                                    del bot_state.active_trades[symbol]
                                    logger.debug(f"📝 Trade {symbol} logged as closed (SL/TP)")

                                    # Notifica Telegram
                                    try:
                                        notifier.notify_trade_closed(
                                            symbol=symbol,
                                            direction=position.get("side", "unknown").lower() if position else "unknown",
                                            pnl=pnl,
                                            pnl_pct=pnl_pct or 0.0,
                                            reason=reason
                                        )
                                    except Exception as note_err:
                                        logger.warning(f"⚠️ Errore notifica Telegram chiusura (SL/TP): {note_err}")
                                except Exception as log_err:
                                    logger.warning(f"⚠️ Errore logging chiusura trade {symbol}: {log_err}")
                        else:
                            # Risultato positivo ma status non standard
                            logger.info(f"✅ Posizione {symbol} chiusa: {close_result}")
                            risk_manager.record_trade_result(pnl, was_stop_loss=(reason == "stop_loss"))
                            risk_manager.remove_position(symbol)
                            # Log trade closure
                            if symbol in bot_state.active_trades:
                                try:
                                    position = next((p for p in open_positions if p["symbol"] == symbol), None)
                                    entry_price = position.get("entry_price", 0) if position else 0
                                    exit_price = current_prices.get(symbol, 0)
                                    pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price else None

                                    db_utils.close_trade(
                                        trade_id=bot_state.active_trades[symbol],
                                        exit_price=exit_price,
                                        exit_reason="stop_loss" if reason == "stop_loss" else "take_profit",
                                        pnl_usd=pnl,
                                        pnl_pct=pnl_pct
                                    )
                                    del bot_state.active_trades[symbol]
                                except Exception as log_err:
                                    logger.warning(f"⚠️ Errore logging chiusura trade {symbol}: {log_err}")
                    else:
                        # Risultato non-dict (probabilmente successo)
                        logger.info(f"✅ Posizione {symbol} chiusa: {close_result}")
                        risk_manager.record_trade_result(pnl, was_stop_loss=(reason == "stop_loss"))
                        risk_manager.remove_position(symbol)
                        # Log trade closure
                        if symbol in bot_state.active_trades:
                            try:
                                position = next((p for p in open_positions if p["symbol"] == symbol), None)
                                entry_price = position.get("entry_price", 0) if position else 0
                                exit_price = current_prices.get(symbol, 0)
                                pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price else None

                                db_utils.close_trade(
                                    trade_id=bot_state.active_trades[symbol],
                                    exit_price=exit_price,
                                    exit_reason="stop_loss" if reason == "stop_loss" else "take_profit",
                                    pnl_usd=pnl,
                                    pnl_pct=pnl_pct
                                )
                                del bot_state.active_trades[symbol]
                            except Exception as log_err:
                                logger.warning(f"⚠️ Errore logging chiusura trade {symbol}: {log_err}")

                except Exception as e:
                    logger.error(f"❌ Eccezione durante chiusura {symbol}: {e}", exc_info=True)
                    # NON rimuovere dal tracking in caso di eccezione
                    logger.warning(f"⚠️ Posizione {symbol} NON rimossa dal tracking a causa dell'errore")

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
</forecast>

<whale_alerts>
{whale_alerts_txt}
</whale_alerts>"""

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

        # Genera cycle_id univoco per questo ciclo di trading
        cycle_id = f"cycle_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        decision = previsione_trading_agent(system_prompt, cycle_id=cycle_id)

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
        # 5.5 TREND CONFIRMATION (Phase 2)
        # ========================================
        trend_check_passed = True
        trend_info = ""

        if CONFIG["TREND_CONFIRMATION_ENABLED"] and bot_state.trend_engine and operation != "hold":
            try:
                logger.info(f"🔍 Verifica trend per {symbol}...")

                # Get daily metrics from screener if available
                daily_metrics = None
                if screener and CONFIG["SCREENING_ENABLED"]:
                    selected_coins = screener.get_selected_coins()
                    for coin in selected_coins:
                        if coin.symbol == symbol:
                            daily_metrics = {
                                'adx_14': coin.metrics.get('adx_14'),
                                'plus_di': coin.metrics.get('plus_di'),
                                'minus_di': coin.metrics.get('minus_di'),
                            }
                            break

                # Confirm trend
                confirmation = bot_state.trend_engine.confirm_trend(
                    symbol=symbol,
                    daily_metrics=daily_metrics
                )

                # Log trend analysis
                logger.info(
                    f"📊 Trend {symbol}: {confirmation.direction.value} "
                    f"[{confirmation.quality.value}] "
                    f"({confirmation.confidence:.0%} confidence)"
                )
                logger.info(
                    f"   Daily: {confirmation.daily_trend.value if confirmation.daily_trend else 'N/A'}, "
                    f"Hourly: {confirmation.hourly_trend.value if confirmation.hourly_trend else 'N/A'}, "
                    f"15m: {confirmation.m15_trend.value if confirmation.m15_trend else 'N/A'}"
                )
                logger.info(f"   Entry quality: {confirmation.entry_quality}")

                # Prepare formatted strings
                daily_adx_str = f"{confirmation.daily_adx:.1f}" if confirmation.daily_adx is not None else "N/A"
                hourly_rsi_str = f"{confirmation.hourly_rsi:.1f}" if confirmation.hourly_rsi is not None else "N/A"

                # Store trend info for context
                trend_info = f"""
Trend Analysis for {symbol}:
- Overall: {confirmation.direction.value} [{confirmation.quality.value}] ({confirmation.confidence:.0%})
- Daily: {confirmation.daily_trend.value if confirmation.daily_trend else 'N/A'} (ADX: {daily_adx_str})
- Hourly: {confirmation.hourly_trend.value if confirmation.hourly_trend else 'N/A'} (RSI: {hourly_rsi_str})
- 15m: {confirmation.m15_trend.value if confirmation.m15_trend else 'N/A'} (MACD: {confirmation.m15_macd_signal})
- Entry: {confirmation.entry_quality}
"""

                # Check if we should trade
                if not confirmation.should_trade:
                    logger.warning(f"⏭️ Trend check FAILED: qualità trend insufficiente")
                    trend_check_passed = False
                elif CONFIG["SKIP_POOR_ENTRY"] and confirmation.entry_quality == "wait":
                    logger.warning(f"⏳ Trend check WAIT: entry timing non ottimale")
                    trend_check_passed = False
                elif confirmation.entry_quality == "optimal":
                    logger.info(f"✨ OPTIMAL entry opportunity per {symbol}!")
                else:
                    logger.info(f"✅ Trend check passed (entry: {confirmation.entry_quality})")

            except Exception as e:
                logger.error(f"❌ Errore trend confirmation: {e}", exc_info=True)
                # In caso di errore, procedi comunque (fail-safe)
                logger.warning("⚠️ Procedendo senza trend confirmation a causa dell'errore")

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

        elif not trend_check_passed:
            logger.warning(f"⛔ Trade bloccato: trend check non superato")
            result = {"status": "blocked", "reason": "Trend confirmation failed"}

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

                        # ========================================
                        # 6.5 LOG EXECUTED TRADE
                        # ========================================
                        try:
                            # Will be set after logging bot_operation
                            op_id_placeholder = None  # Will be filled after section 7

                            if operation == "open" and result.get("status") == "ok":
                                # Log opened trade
                                # Fallback per entry_price se non presente nella risposta
                                entry_price = result.get("fill_price")
                                if not entry_price:
                                    mids = trader.info.all_mids()
                                    entry_price = float(mids.get(symbol, 0))

                                trade_id = db_utils.log_executed_trade(
                                    bot_operation_id=None,  # Will update after bot_operation is logged
                                    trade_type="open",
                                    symbol=symbol,
                                    direction=direction,
                                    size=result.get("size", decision.get("size", 0)),
                                    entry_price=entry_price,
                                    leverage=decision.get("leverage"),
                                    stop_loss_price=decision.get("stop_loss"),
                                    take_profit_price=decision.get("take_profit"),
                                    hl_order_id=result.get("order_id"),
                                    hl_fill_price=result.get("fill_price"),
                                    size_usd=result.get("size_usd"),
                                    raw_response=result
                                )
                                bot_state.active_trades[symbol] = trade_id
                                logger.debug(f"📝 Trade {symbol} logged as open (ID: {trade_id})")

                                # Notifica Telegram
                                try:
                                    notifier.notify_trade_opened(
                                        symbol=symbol,
                                        direction=direction,
                                        size_usd=result.get("size_usd", 0.0),
                                        leverage=decision.get("leverage", 1),
                                        entry_price=entry_price,
                                        stop_loss=decision.get("stop_loss", 0.0),
                                        take_profit=decision.get("take_profit", 0.0)
                                    )
                                except Exception as note_err:
                                    logger.warning(f"⚠️ Errore notifica Telegram apertura: {note_err}")

                            elif operation == "close" and result.get("status") == "ok":
                                # Log closed trade
                                if symbol in bot_state.active_trades:
                                    # Get position info for P&L calculation
                                    position = next((p for p in open_positions if p["symbol"] == symbol), None)
                                    pos_entry_price = position.get("entry_price", 0) if position else 0
                                    
                                    # Fallback per exit_price
                                    exit_price = result.get("fill_price")
                                    if not exit_price:
                                        mids = trader.info.all_mids()
                                        exit_price = float(mids.get(symbol, 0))

                                    # Calculate P&L if not provided
                                    pnl_usd = result.get("pnl_usd")
                                    if pnl_usd is None and position:
                                        size = position.get("size", 0)
                                        # PnL calc: (Exit - Entry) * Size (for Long)
                                        # For Short: (Entry - Exit) * Size
                                        # Assuming standard linear contract logic or handled by exchange
                                        # RiskManager uses direction aware logic, let's replicate or rely on backend
                                        side = position.get("side", "long")
                                        if side.lower() == "long":
                                            pnl_usd = (exit_price - pos_entry_price) * size
                                        else:
                                            pnl_usd = (pos_entry_price - exit_price) * size

                                    pnl_pct = ((exit_price - pos_entry_price) / pos_entry_price * 100) if pos_entry_price > 0 else 0

                                    db_utils.close_trade(
                                        trade_id=bot_state.active_trades[symbol],
                                        exit_price=exit_price,
                                        exit_reason="signal",  # AI-driven close
                                        pnl_usd=pnl_usd,
                                        pnl_pct=pnl_pct,
                                        fees_usd=result.get("fees", 0)
                                    )
                                    del bot_state.active_trades[symbol]
                                    logger.debug(f"📝 Trade {symbol} logged as closed")

                                    # Notifica Telegram
                                    try:
                                        notifier.notify_trade_closed(
                                            symbol=symbol,
                                            direction=position.get("side", "unknown").lower() if position else "unknown",
                                            pnl=pnl_usd or 0.0,
                                            pnl_pct=pnl_pct or 0.0,
                                            reason=decision.get("reason", "Signal AI")
                                        )
                                    except Exception as note_err:
                                        logger.warning(f"⚠️ Errore notifica Telegram chiusura: {note_err}")
                                else:
                                    logger.warning(f"⚠️ Close operation per {symbol} ma nessun trade attivo tracciato")

                        except Exception as log_err:
                            logger.warning(f"⚠️ Errore logging executed trade: {log_err}", exc_info=True)
                            # Continue execution even if logging fails

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
                    "whale_alerts": whale_alerts_list,
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

        # Invia notifica di avvio via Telegram PRIMA di avviare lo scheduler
        try:
            if notifier.enabled:
                logger.info("📤 Invio notifica di avvio via Telegram...")
                notifier.notify_startup(
                    testnet=CONFIG["TESTNET"],
                    tickers=CONFIG["TICKERS"],
                    cycle_interval_minutes=CONFIG["CYCLE_INTERVAL_MINUTES"],
                    wallet_address=WALLET_ADDRESS,
                    screening_enabled=CONFIG.get("SCREENING_ENABLED", False),
                    top_n_coins=CONFIG.get("TOP_N_COINS", 5),
                    rebalance_day=CONFIG.get("REBALANCE_DAY", "sunday"),
                    sentiment_interval_minutes=5,  # Da sentiment.py INTERVALLO_SECONDI / 60
                    health_check_interval_minutes=5  # Da scheduler.py
                )
                logger.info("✅ Notifica di avvio inviata via Telegram")
            else:
                logger.warning("⚠️ Telegram notifier non configurato (mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)")
        except Exception as e:
            logger.error(f"❌ Errore nell'invio notifica Telegram: {e}", exc_info=True)

        # Avvia scheduler (bloccante)
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
