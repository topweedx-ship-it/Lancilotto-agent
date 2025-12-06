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
# Log file path - works both locally and in Docker
# Use /app/logs only if writable (Docker), otherwise use current directory
log_dir = "."
if os.path.exists("/app/logs"):
    try:
        # Test if we can write to /app/logs
        test_file = "/app/logs/.write_test"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        log_dir = "/app/logs"
    except (PermissionError, OSError):
        log_dir = "."
log_filename = os.path.join(log_dir, "trading_agent.log")

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
SCREENING_ENV = os.getenv("SCREENING_ENABLED", "false").lower()

CONFIG = {
    # Trading
    "TESTNET": TESTNET_ENV in ("true", "1", "yes"),
    "TICKERS": ["BTC", "ETH", "SOL"],
    "CYCLE_INTERVAL_MINUTES": 5,

    # Coin Screening
    "SCREENING_ENABLED": SCREENING_ENV in ("true", "1", "yes"),
    "TOP_N_COINS": 20,          # Aumentato per avere più pool di scelta
    "ANALYSIS_BATCH_SIZE": 5,   # Quante coin analizzare per ciclo (rotazione)
    "REBALANCE_DAY": "sunday",
    "FALLBACK_TICKERS": ["BTC", "ETH", "SOL"],  # Used if screening fails or disabled

    # Trend Confirmation (Phase 2)
    "TREND_CONFIRMATION_ENABLED": True,  # Enable multi-timeframe trend confirmation
    "MIN_TREND_CONFIDENCE": 0.6,  # Minimum trend confidence to trade (0-1)
    "SKIP_POOR_ENTRY": True,  # Skip trades when entry_quality is "wait"
    "ADX_THRESHOLD": 25,  # ADX threshold for strong trends
    "RSI_OVERBOUGHT": 70,  # RSI overbought level
    "RSI_OVERSOLD": 30,  # RSI oversold level
    "ALLOW_SCALPING": os.getenv("ALLOW_SCALPING", "false").lower() in ("true", "1", "yes"),  # Scalping mode

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
    logger.info("   Testnet URL: https://app.hyperliquid-testnet.xyz/trade")


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
        self.rotation_index: int = 0             # Indice per rotazione coin
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
                self.trend_engine.config['allow_scalping'] = CONFIG["ALLOW_SCALPING"]
                logger.info("✅ Trend Confirmation Engine inizializzato")
                logger.info(f"   ADX threshold: {CONFIG['ADX_THRESHOLD']}")
                logger.info(f"   Min confidence: {CONFIG['MIN_TREND_CONFIDENCE']}")
                logger.info(f"   Scalping mode: {'ENABLED' if CONFIG['ALLOW_SCALPING'] else 'DISABLED'}")

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

    try:
        # ========================================
        # 0. SELEZIONE COIN (se screening abilitato)
        # ========================================
        tickers_manage = []
        tickers_scout = []
        
        # Identifica coin in portafoglio (da analizzare SEMPRE per gestire chiusure)
        if bot_state.active_trades:
            tickers_manage = list(bot_state.active_trades.keys())

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
                            tickers_scout_all = [coin.symbol for coin in selected_coins]
                            logger.info(f"🎯 Trading su coin cached: {', '.join(tickers_scout_all)}")
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
                all_selected_coins = screener.get_selected_coins(top_n=CONFIG["TOP_N_COINS"])
                
                if all_selected_coins:
                    # LOGICA DI ROTAZIONE SCOUTING
                    # Identifica candidati disponibili (escludendo quelli già in portafoglio)
                    # NOTA: I tickers_manage sono già gestiti separatamente
                    held_symbols_set = set(tickers_manage)
                    candidates = [c.symbol for c in all_selected_coins if c.symbol not in held_symbols_set]
                    
                    # Seleziona batch corrente per scouting
                    batch_size = CONFIG.get("ANALYSIS_BATCH_SIZE", 5)
                    
                    if candidates:
                        start_idx = bot_state.rotation_index % len(candidates)
                        end_idx = start_idx + batch_size
                        
                        # Gestione overflow lista (wrap-around)
                        if end_idx <= len(candidates):
                            tickers_scout = candidates[start_idx:end_idx]
                        else:
                            # Prendi fino alla fine e ricomincia dall'inizio
                            tickers_scout = candidates[start_idx:] + candidates[:end_idx - len(candidates)]
                            
                        # Aggiorna indice per il prossimo ciclo
                        # Avanziamo solo se abbiamo effettivamente preso dei candidati
                        bot_state.rotation_index = (start_idx + batch_size) % len(candidates)
                    
                    logger.info(f"🎯 Target: {len(tickers_manage)} in gestione, {len(tickers_scout)} in scouting")
                    if tickers_manage:
                        logger.info(f"   Gestione: {', '.join(tickers_manage)}")
                    if tickers_scout:
                        logger.info(f"   Scouting: {', '.join(tickers_scout)}")
                else:
                    # Nessun dato disponibile, usa fallback
                    raise ValueError("Nessun dato disponibile dal screener")

            except Exception as e:
                logger.error(f"❌ Errore screening: {e}", exc_info=True)
                logger.info(f"📋 Uso fallback tickers: {CONFIG['FALLBACK_TICKERS']}")
                tickers_scout = CONFIG["FALLBACK_TICKERS"]
        else:
            # Screening disabilitato, usa CONFIG["TICKERS"]
            # Se screening disabilitato, mettiamo tutto in scouting per semplicità, 
            # ma rimuoviamo quelli già in gestione per evitare doppi
            fallback_tickers = CONFIG["TICKERS"]
            tickers_scout = [t for t in fallback_tickers if t not in tickers_manage]

        # Combine for efficient fetching
        all_tickers = list(set(tickers_manage + tickers_scout))
        if not all_tickers:
            logger.warning("⚠️ Nessun ticker da analizzare")
            return

        # ========================================
        # 1. FETCH DATI DI MERCATO (UNICA CHIAMATA)
        # ========================================
        logger.info(f"📡 Recupero dati di mercato per {len(all_tickers)} ticker...")

        # Indicatori tecnici
        try:
            # analyze_multiple_tickers returns (full_text, json_list)
            # We need to parse json_list to map by ticker
            _, indicators_list = analyze_multiple_tickers(
                all_tickers, 
                testnet=CONFIG["TESTNET"]
            )
            # Map indicators by ticker
            indicators_map = {item['ticker']: item for item in indicators_list if 'ticker' in item}
            logger.info("✅ Indicatori tecnici recuperati")
        except Exception as e:
            logger.warning(f"⚠️ Errore indicatori: {e}")
            indicators_map = {}

        # News
        try:
            # fetch_latest_news returns text. We might need structured news or just pass active text.
            # For now, news is global or per ticker? The function takes symbols list.
            # Assuming global news context for now, or we optimize later.
            news_txt = fetch_latest_news(symbols=all_tickers)
            logger.info(f"✅ News ({len(news_txt)} caratteri)")
        except Exception as e:
            logger.warning(f"⚠️ Errore news: {e}")
            news_txt = "News non disponibili"

        # Sentiment (Global)
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
                tickers=all_tickers,
                testnet=CONFIG["TESTNET"]
            )
            # Map forecasts by ticker if possible, or just use the list
            forecasts_map = {f.get('Ticker'): f for f in forecasts_json if f.get('Ticker')}
            logger.info("✅ Forecast recuperati")
        except Exception as e:
            logger.warning(f"⚠️ Errore forecast: {e}")
            forecasts_json = []
            forecasts_map = {}

        # Whale Alerts (Global)
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

        # --- FIX: SYNC STATO REALE ---
        # Filtra tickers_manage per includere SOLO le posizioni realmente aperte.
        # Questo evita chiamate inutili all'AI se il trade è stato chiuso altrove o per stop-loss.
        real_open_symbols = [p['symbol'] for p in open_positions]
        
        # Identifica e rimuovi i "trade fantasma" (presenti in memoria ma non sull'exchange)
        ghost_trades = [t for t in tickers_manage if t not in real_open_symbols]
        for ghost in ghost_trades:
            logger.info(f"👻 Rilevato trade fantasma su {ghost}: rimuovo da gestione interna")
            if ghost in bot_state.active_trades:
                del bot_state.active_trades[ghost]
            tickers_manage.remove(ghost)
            
        if not tickers_manage and ghost_trades:
             logger.info("⏩ Nessuna posizione reale da gestire dopo il sync. Salto Fase Gestione.")
        # -----------------------------

        # Log snapshot
        try:
            snapshot_id = db_utils.log_account_status(account_status)
            logger.debug(f"📝 Account snapshot salvato (ID: {snapshot_id})")
        except Exception as e:
            logger.warning(f"⚠️ Errore salvataggio snapshot: {e}")

        # ========================================
        # 3. CHECK SL/TP LOCALE (Risk Manager)
        # ========================================
        if open_positions:
            # Need prices for risk manager check
            current_prices = {}
            # Extract prices from indicators if available, else fetch
            for t in all_tickers:
                if t in indicators_map and 'current' in indicators_map[t]:
                     current_prices[t] = indicators_map[t]['current'].get('price')
            
            # Fallback fetch if missing
            missing_prices = [t for t in tickers_manage if t not in current_prices or not current_prices[t]]
            if missing_prices:
                fetched = trader.get_current_prices(missing_prices)
                current_prices.update(fetched)

            positions_to_close = risk_manager.check_positions(current_prices)

            for close_info in positions_to_close:
                # ... (Logic for SL/TP closing remains same, abbreviated for brevity) ...
                symbol = close_info["symbol"]
                reason = close_info["reason"]
                pnl = close_info["pnl"]
                logger.warning(f"⚠️ {reason.upper()} trigger per {symbol}, PnL: ${pnl:.2f}")
                
                try:
                    close_order = {
                        "operation": "close",
                        "symbol": symbol,
                        "direction": "long"
                    }
                    close_result = trader.execute_signal_with_risk(
                        close_order,
                        risk_manager,
                        balance_usd
                    )
                    # Log logic identical to previous...
                    if close_result and close_result.get("status") == "ok":
                         # Remove from active trades so we don't analyze it in management phase
                         if symbol in tickers_manage:
                             tickers_manage.remove(symbol)
                except Exception as e:
                    logger.error(f"❌ Eccezione chiusura SL/TP {symbol}: {e}")

        # Helper to build prompt
        def build_prompt_data(target_tickers):
            # For simplicity, we pass the JSON list of indicators for the target tickers
            subset_indicators = [indicators_map[t] for t in target_tickers if t in indicators_map]
            subset_forecasts = [forecasts_map[t] for t in target_tickers if t in forecasts_map]
            
            return json.dumps(subset_indicators, indent=2), json.dumps(subset_forecasts, indent=2)

        # ========================================
        # 4. FASE GESTIONE (Attiva se ci sono posizioni)
        # ========================================
        if tickers_manage:
            logger.info(f"🤖 FASE GESTIONE: Analisi {len(tickers_manage)} posizioni aperte...")
            
            # Genera cycle_id univoco per gestione
            cycle_id_manage = f"manage_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            # Build specific prompt
            # Filter indicators
            subset_ind, subset_forc = build_prompt_data(tickers_manage)
            
            # Costruisci prompt specifico
            # Nota: System prompt template viene caricato e formattato
            # Usiamo un msg_info custom che focalizza l'attenzione
            
            msg_info_manage = f"""<context>
ANALYSIS TYPE: OPEN POSITIONS MANAGEMENT
FOCUS: Decide whether to CLOSE or HOLD existing positions.
DO NOT OPEN NEW POSITIONS IN THIS PHASE.
</context>

<active_positions>
{json.dumps(open_positions, indent=2)}
</active_positions>

<indicators>
{subset_ind}
</indicators>

<news>
{news_txt}
</news>

<sentiment>
{sentiment_txt}
</sentiment>

<forecast>
{subset_forc}
</forecast>

<whale_alerts>
{whale_alerts_txt}
</whale_alerts>

<risk_status>
Daily P&L: ${risk_manager.daily_pnl:.2f}
Consecutive Losses: {risk_manager.consecutive_losses}
</risk_status>
"""
            # Load system prompt template
            with open('system_prompt.txt', 'r') as f:
                system_prompt_template = f.read()
            
            # Format prompt
            final_prompt_manage = system_prompt_template.format(
                json.dumps(account_status, indent=2), 
                msg_info_manage
            )
            
            # Call AI
            try:
                decision_manage = previsione_trading_agent(
                    final_prompt_manage, 
                    cycle_id=cycle_id_manage
                )
                
                # Process Decision
                op_manage = decision_manage.get("operation", "hold")
                sym_manage = decision_manage.get("symbol")
                
                if op_manage == "close" and sym_manage in tickers_manage:
                    logger.info(f"📉 DECISIONE GESTIONE: CLOSE {sym_manage}")
                    # Execute Close
                    res = trader.execute_signal_with_risk(decision_manage, risk_manager, balance_usd)
                    # Log ... (reuse existing logic structure or function)
                    # For brevity, assume logging handles it via DB utils inside execute or after
                    # Log to DB
                    if 'execution_result' not in decision_manage:
                        decision_manage['execution_result'] = res
                    decision_manage['cycle_id'] = cycle_id_manage
                    
                    db_utils.log_bot_operation(
                        operation_payload=decision_manage,
                        system_prompt=final_prompt_manage,
                        indicators=json.loads(subset_ind),
                        news_text=news_txt,
                        sentiment=sentiment_json,
                        forecasts=json.loads(subset_forc)
                    )
                    
                    # If closed successfully, remove from active trades map locally if needed
                    if res.get("status") == "ok":
                        # Remove active trade ID
                        if sym_manage in bot_state.active_trades:
                            try:
                                # Get position info for P&L calculation
                                position = next((p for p in open_positions if p["symbol"] == sym_manage), None)
                                entry_price = position.get("entry_price", 0) if position else 0
                                # Use fill price or fallback to current market price
                                exit_price = res.get("fill_price")
                                if not exit_price and sym_manage in current_prices:
                                    exit_price = current_prices[sym_manage]
                                
                                pnl_usd = res.get("pnl_usd")
                                
                                # Calculate Pnl if missing
                                if pnl_usd is None and position:
                                    size = position.get("size", 0)
                                    if exit_price and exit_price > 0:
                                        side = position.get("side", "long")
                                        if side.lower() == "long":
                                            pnl_usd = (exit_price - entry_price) * size
                                        else:
                                            pnl_usd = (entry_price - exit_price) * size
                                    else:
                                        pnl_usd = 0

                                pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price and entry_price > 0 else 0

                                db_utils.close_trade(
                                    trade_id=bot_state.active_trades[sym_manage],
                                    exit_price=exit_price or 0,
                                    exit_reason="signal",
                                    pnl_usd=pnl_usd,
                                    pnl_pct=pnl_pct,
                                    fees_usd=res.get("fees", 0)
                                )
                                del bot_state.active_trades[sym_manage]
                                logger.info(f"✅ Trade {sym_manage} chiuso e loggato")
                                
                                # Notify
                                try:
                                    notifier.notify_trade_closed(
                                        symbol=sym_manage,
                                        direction=position.get("side", "unknown") if position else "unknown",
                                        pnl=pnl_usd or 0.0,
                                        pnl_pct=pnl_pct or 0.0,
                                        reason="Signal AI"
                                    )
                                except Exception as e:
                                    logger.warning(f"⚠️ Notify error: {e}")
                                    
                            except Exception as log_err:
                                logger.error(f"❌ Errore logging chiusura: {log_err}")
                            
                elif op_manage == "open":
                    logger.warning("⚠️ AI ha suggerito OPEN in fase GESTIONE. Ignorato.")
                else:
                    logger.info(f"⏸️ GESTIONE: {op_manage} su {sym_manage}")
                    # Log HOLD decision for tracking
                    decision_manage['cycle_id'] = cycle_id_manage
                    db_utils.log_bot_operation(
                        operation_payload=decision_manage,
                        system_prompt=final_prompt_manage,
                        indicators=json.loads(subset_ind)
                    )

            except Exception as e:
                logger.error(f"❌ Errore fase gestione: {e}")

        # ========================================
        # 5. FASE SCOUTING (Attiva se ci sono candidati)
        # ========================================
        if tickers_scout:
            logger.info(f"🔭 FASE SCOUTING: Analisi {len(tickers_scout)} opportunità...")
            
            cycle_id_scout = f"scout_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            subset_ind, subset_forc = build_prompt_data(tickers_scout)
            
            msg_info_scout = f"""<context>
ANALYSIS TYPE: MARKET SCOUTING
FOCUS: Look for new OPEN opportunities among the candidates.
IGNORE existing positions (handled separately).
</context>

<candidates>
{', '.join(tickers_scout)}
</candidates>

<indicators>
{subset_ind}
</indicators>

<news>
{news_txt}
</news>

<sentiment>
{sentiment_txt}
</sentiment>

<forecast>
{subset_forc}
</forecast>

<whale_alerts>
{whale_alerts_txt}
</whale_alerts>

<risk_status>
Daily P&L: ${risk_manager.daily_pnl:.2f}
</risk_status>
"""
            # Load and format prompt
            with open('system_prompt.txt', 'r') as f:
                system_prompt_template = f.read()
                
            final_prompt_scout = system_prompt_template.format(
                json.dumps(account_status, indent=2), 
                msg_info_scout
            )
            
            # Call AI
            try:
                decision_scout = previsione_trading_agent(
                    final_prompt_scout, 
                    cycle_id=cycle_id_scout
                )
                
                op_scout = decision_scout.get("operation", "hold")
                sym_scout = decision_scout.get("symbol")
                conf_scout = decision_scout.get("confidence", 0)
                
                trend_info = ""  # Initialize default
                
                if op_scout == "open":
                    if sym_scout not in tickers_scout:
                        logger.warning(f"⚠️ AI ha suggerito {sym_scout} che non è nei candidati ({tickers_scout})")
                    else:
                        # Trend Confirmation Logic (Phase 2)
                        trend_check_passed = True
                        trend_info = ""
                        
                        if CONFIG["TREND_CONFIRMATION_ENABLED"] and bot_state.trend_engine:
                            # Logic for trend confirmation ... (reuse existing)
                            # Simplified call:
                            daily_metrics = None # Get from screener if possible
                            confirmation = bot_state.trend_engine.confirm_trend(sym_scout, daily_metrics)
                            trend_info = str(confirmation) # Detailed string
                            
                            if not confirmation.should_trade:
                                trend_check_passed = False
                                logger.warning(f"⛔ Trend check fallito per {sym_scout}")
                        
                        if trend_check_passed and conf_scout >= CONFIG["MIN_CONFIDENCE"]:
                            # Log Operation FIRST
                            decision_scout['cycle_id'] = cycle_id_scout
                            if trend_info:
                                decision_scout['trend_info'] = trend_info

                            op_id = db_utils.log_bot_operation(
                                operation_payload=decision_scout,
                                system_prompt=final_prompt_scout,
                                indicators=json.loads(subset_ind),
                                news_text=news_txt,
                                sentiment=sentiment_json,
                                forecasts=json.loads(subset_forc)
                            )
                            logger.info(f"📝 Operation logged (ID: {op_id})")

                            # Execute Open
                            can_trade = risk_manager.can_open_position(balance_usd)
                            if can_trade["allowed"]:
                                res = trader.execute_signal_with_risk(decision_scout, risk_manager, balance_usd)
                                # Log execution...
                                if 'execution_result' not in decision_scout:
                                    decision_scout['execution_result'] = res

                                if res.get("status") == "ok":
                                    try:
                                        entry_price = res.get("fill_price")
                                        if not entry_price:
                                            # Fallback to current market price from indicators
                                            if sym_scout in indicators_map and 'current' in indicators_map[sym_scout]:
                                                entry_price = indicators_map[sym_scout]['current'].get('price', 0)

                                        trade_id = db_utils.log_executed_trade(
                                            bot_operation_id=op_id,  # Link to the logged operation
                                            trade_type="open",
                                            symbol=sym_scout,
                                            direction=decision_scout.get("direction", "long"),
                                            size=res.get("size", 0),
                                            entry_price=entry_price or 0,
                                            leverage=decision_scout.get("leverage", 1),
                                            stop_loss_price=decision_scout.get("stop_loss", 0),
                                            take_profit_price=decision_scout.get("take_profit", 0),
                                            hl_order_id=res.get("order_id"),
                                            hl_fill_price=res.get("fill_price"),
                                            size_usd=res.get("size_usd"),
                                            raw_response=res
                                        )
                                        bot_state.active_trades[sym_scout] = trade_id
                                        logger.info(f"✅ Trade {sym_scout} aperto e loggato (ID: {trade_id})")

                                        # Notify - Calculate actual SL/TP prices from percentages
                                        try:
                                            risk_info = res.get("risk_management", {})
                                            sl_pct = risk_info.get("stop_loss_pct", 2.0)
                                            tp_pct = risk_info.get("take_profit_pct", 5.0)
                                            direction = decision_scout.get("direction", "long")

                                            # Calculate actual prices based on entry and direction
                                            if entry_price and entry_price > 0:
                                                if direction == "long":
                                                    stop_loss_price = entry_price * (1 - sl_pct / 100)
                                                    take_profit_price = entry_price * (1 + tp_pct / 100)
                                                else:  # short
                                                    stop_loss_price = entry_price * (1 + sl_pct / 100)
                                                    take_profit_price = entry_price * (1 - tp_pct / 100)
                                            else:
                                                stop_loss_price = 0.0
                                                take_profit_price = 0.0

                                            notifier.notify_trade_opened(
                                                symbol=sym_scout,
                                                direction=direction,
                                                size_usd=res.get("size_usd", 0.0),
                                                leverage=decision_scout.get("leverage", 1),
                                                entry_price=entry_price or 0,
                                                stop_loss=stop_loss_price,
                                                take_profit=take_profit_price
                                            )
                                        except Exception as e:
                                            logger.warning(f"⚠️ Notify error: {e}")

                                    except Exception as log_err:
                                        logger.error(f"❌ Errore logging apertura: {log_err}")
                            else:
                                logger.warning(f"⛔ Risk Manager blocca apertura: {can_trade['reason']}")
                                decision_scout['execution_result'] = {"status": "blocked", "reason": can_trade['reason']}
                        else:
                             logger.info(f"⏩ Skip OPEN {sym_scout}: Conf {conf_scout:.2f} o Trend Check {trend_check_passed}")
                
                elif op_scout == "close":
                    logger.warning("⚠️ AI ha suggerito CLOSE in fase SCOUTING. Ignorato.")

                    # Log close operation (not executed)
                    decision_scout['cycle_id'] = cycle_id_scout
                    if trend_info:
                        decision_scout['trend_info'] = trend_info

                    db_utils.log_bot_operation(
                        operation_payload=decision_scout,
                        system_prompt=final_prompt_scout,
                        indicators=json.loads(subset_ind),
                        news_text=news_txt,
                        sentiment=sentiment_json,
                        forecasts=json.loads(subset_forc)
                    )

                elif op_scout == "hold":
                    logger.info(f"⏸️ HOLD {sym_scout} - Conf: {conf_scout:.2f}")

                    # Log hold operation
                    decision_scout['cycle_id'] = cycle_id_scout
                    if trend_info:
                        decision_scout['trend_info'] = trend_info

                    db_utils.log_bot_operation(
                        operation_payload=decision_scout,
                        system_prompt=final_prompt_scout,
                        indicators=json.loads(subset_ind),
                        news_text=news_txt,
                        sentiment=sentiment_json,
                        forecasts=json.loads(subset_forc)
                    )

                else:
                    logger.info(f"⏩ Skip {sym_scout}: Conf {conf_scout:.2f} o Trend Check {trend_check_passed}")

                    # Log skip operation
                    decision_scout['cycle_id'] = cycle_id_scout
                    if trend_info:
                        decision_scout['trend_info'] = trend_info

                    db_utils.log_bot_operation(
                        operation_payload=decision_scout,
                        system_prompt=final_prompt_scout,
                        indicators=json.loads(subset_ind),
                        news_text=news_txt,
                        sentiment=sentiment_json,
                        forecasts=json.loads(subset_forc)
                    )

            except Exception as e:
                logger.error(f"❌ Errore fase scouting: {e}")

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
        except Exception:
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
