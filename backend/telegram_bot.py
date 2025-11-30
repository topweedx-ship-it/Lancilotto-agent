"""
Bot Telegram interattivo per Trading Agent
Gestisce comandi utente e notifiche in tempo reale
"""
import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from threading import Thread
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from notifications import TelegramNotifier
from token_tracker import get_token_tracker

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class TradingTelegramBot:
    """Bot Telegram interattivo per controllo Trading Agent"""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

        # Trading Agent reference (set later via set_trading_agent)
        self.trading_agent: Optional[Any] = None

        # Application and thread management
        self.application: Optional[Application] = None
        self.thread: Optional[Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        # Notifier for push notifications (compatibility with existing system)
        self.notifier = TelegramNotifier(token=self.token, chat_id=self.chat_id)

        if not self.enabled:
            logger.warning("⚠️ Telegram bot non configurato (mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)")
        else:
            logger.info("✅ Telegram bot configurato correttamente")

    def set_trading_agent(self, agent: Any) -> None:
        """Collega il Trading Agent al bot"""
        self.trading_agent = agent
        logger.info("✅ Trading Agent collegato al bot Telegram")

    def _is_authorized(self, update: Update) -> bool:
        """Verifica se l'utente è autorizzato"""
        if not update.effective_chat:
            return False

        user_chat_id = str(update.effective_chat.id)
        authorized = user_chat_id == self.chat_id

        if not authorized:
            logger.warning(f"⚠️ Tentativo accesso non autorizzato da chat_id: {user_chat_id}")

        return authorized

    async def _log_command(self, update: Update, command: str) -> None:
        """Log di tutti i comandi ricevuti"""
        user = update.effective_user
        chat_id = update.effective_chat.id if update.effective_chat else "unknown"
        logger.info(f"📝 Comando ricevuto: /{command} da {user.username or user.first_name} (chat_id: {chat_id})")

    # ==================== COMMAND HANDLERS ====================

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /start"""
        await self._log_command(update, "start")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        # Determina stato e network
        if self.trading_agent:
            is_running = getattr(self.trading_agent, 'is_running', False)
            status_emoji = "🟢" if is_running else "🔴"
            status_text = "Attivo" if is_running else "Fermo"

            # Detect testnet from config
            config = getattr(self.trading_agent, 'config', {})
            is_testnet = config.get('TESTNET', False)
            network = "Testnet" if is_testnet else "Mainnet"

            # Get tickers
            tickers = config.get('TICKERS', ['BTC', 'ETH', 'SOL'])
            tickers_str = ", ".join(tickers)
        else:
            status_emoji = "⚪"
            status_text = "Non connesso"
            network = "N/A"
            tickers_str = "N/A"

        welcome_msg = f"""🤖 <b>Trading Agent Bot</b>

<b>Stato:</b> {status_emoji} {status_text}
<b>Network:</b> {network}
<b>Tickers:</b> {tickers_str}

<b>Comandi disponibili:</b>
/status - Stato bot e ciclo trading
/balance - Saldo wallet corrente
/positions - Posizioni aperte
/today - Riepilogo giornaliero
/config - Configurazione completa
/stop - Ferma trading
/resume - Riprendi trading
/help - Lista comandi completa

<i>Bot pronto per gestire il tuo trading! 🚀</i>"""

        await update.message.reply_text(welcome_msg, parse_mode="HTML")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /status"""
        await self._log_command(update, "status")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        if not self.trading_agent:
            await update.message.reply_text("⚪ Trading Agent non connesso.")
            return

        # Get status info
        is_running = getattr(self.trading_agent, 'is_running', False)
        last_cycle = getattr(self.trading_agent, 'last_cycle_time', None)
        next_cycle = getattr(self.trading_agent, 'next_cycle_time', None)
        cycle_interval = getattr(self.trading_agent, 'cycle_interval_minutes', 60)

        status_emoji = "🟢" if is_running else "🔴"
        status_text = "ATTIVO" if is_running else "FERMO"

        # Format times
        if last_cycle:
            last_cycle_str = last_cycle.strftime("%H:%M:%S")
        else:
            last_cycle_str = "Mai eseguito"

        if next_cycle:
            next_cycle_str = next_cycle.strftime("%H:%M:%S")
            time_until = (next_cycle - datetime.now(timezone.utc)).total_seconds()
            minutes_until = int(time_until / 60)
            next_cycle_str += f" (tra {minutes_until}m)"
        else:
            next_cycle_str = "N/A"

        # Get today's token cost
        try:
            tracker = get_token_tracker()
            today_stats = tracker.get_daily_stats()
            cost_today = today_stats.total_cost_usd
            cost_str = f"${cost_today:.4f}"
        except Exception as e:
            logger.error(f"Errore lettura costi token: {e}")
            cost_str = "N/A"

        msg = f"""📊 <b>STATO TRADING ENGINE</b>

<b>Stato:</b> {status_emoji} {status_text}
<b>Ultimo ciclo:</b> {last_cycle_str}
<b>Prossimo ciclo:</b> {next_cycle_str}
<b>Intervallo cicli:</b> {cycle_interval} minuti

💰 <b>Costo LLM oggi:</b> {cost_str}

<i>Il bot sta {('eseguendo' if is_running else 'aspettando')} il trading automatico.</i>"""

        await update.message.reply_text(msg, parse_mode="HTML")

    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /balance"""
        await self._log_command(update, "balance")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        if not self.trading_agent:
            await update.message.reply_text("⚪ Trading Agent non connesso.")
            return

        try:
            # Get balance from trading agent
            trader = getattr(self.trading_agent, 'trader', None)
            if not trader:
                await update.message.reply_text("⚠️ Trader non disponibile.")
                return

            # Fetch current account state
            account_state = trader.get_account_state()
            balance_usd = account_state.get('balance_usd', 0.0)
            margin_used = account_state.get('margin_used', 0.0)
            available = balance_usd - margin_used

            # Get initial balance if tracked
            initial_balance = getattr(self.trading_agent, 'initial_balance', balance_usd)
            pnl = balance_usd - initial_balance
            pnl_pct = (pnl / initial_balance * 100) if initial_balance > 0 else 0.0

            pnl_emoji = "🟢" if pnl >= 0 else "🔴"

            msg = f"""💰 <b>SALDO WALLET</b>

<b>Balance:</b> ${balance_usd:,.2f}
<b>Margine usato:</b> ${margin_used:,.2f}
<b>Disponibile:</b> ${available:,.2f}

<b>PnL totale:</b> {pnl_emoji} ${pnl:,.2f} ({pnl_pct:+.2f}%)
<b>Balance iniziale:</b> ${initial_balance:,.2f}

<i>Aggiornato al: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</i>"""

            await update.message.reply_text(msg, parse_mode="HTML")

        except Exception as e:
            logger.error(f"❌ Errore nel recupero balance: {e}")
            await update.message.reply_text(f"❌ Errore nel recupero del saldo: {str(e)}")

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /positions"""
        await self._log_command(update, "positions")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        if not self.trading_agent:
            await update.message.reply_text("⚪ Trading Agent non connesso.")
            return

        try:
            # Get positions from trading agent
            trader = getattr(self.trading_agent, 'trader', None)
            if not trader:
                await update.message.reply_text("⚠️ Trader non disponibile.")
                return

            account_state = trader.get_account_state()
            positions = account_state.get('open_positions', [])

            if not positions:
                await update.message.reply_text("📭 Nessuna posizione aperta al momento.")
                return

            msg = "<b>📈 POSIZIONI APERTE</b>\n\n"

            total_pnl = 0.0
            for pos in positions:
                symbol = pos.get('symbol', 'N/A')
                side = pos.get('side', 'N/A')
                size = pos.get('size', 0.0)
                entry_price = pos.get('entry_price', 0.0)
                mark_price = pos.get('mark_price', 0.0)
                pnl_usd = pos.get('pnl_usd', 0.0)
                leverage = pos.get('leverage', 'N/A')

                total_pnl += pnl_usd

                side_emoji = "🟢" if side.lower() == 'long' else "🔴"
                pnl_emoji = "🟢" if pnl_usd >= 0 else "🔴"

                msg += f"""{side_emoji} <b>{symbol}</b> - {side.upper()}
Size: {size:.6f}
Entry: ${entry_price:,.4f} | Mark: ${mark_price:,.4f}
PnL: {pnl_emoji} ${pnl_usd:,.4f}
Leverage: {leverage}

"""

            total_emoji = "🟢" if total_pnl >= 0 else "🔴"
            msg += f"<b>PnL Totale:</b> {total_emoji} ${total_pnl:,.4f}"

            await update.message.reply_text(msg, parse_mode="HTML")

        except Exception as e:
            logger.error(f"❌ Errore nel recupero posizioni: {e}")
            await update.message.reply_text(f"❌ Errore nel recupero delle posizioni: {str(e)}")

    async def cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /today - riepilogo giornaliero"""
        await self._log_command(update, "today")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        if not self.trading_agent:
            await update.message.reply_text("⚪ Trading Agent non connesso.")
            return

        try:
            # Get daily stats from database
            from db_utils import get_connection

            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Get today's operations
                    cur.execute("""
                        SELECT operation, symbol, direction, created_at
                        FROM bot_operations
                        WHERE created_at >= %s
                        ORDER BY created_at DESC
                    """, (today_start,))
                    operations = cur.fetchall()

                    # Get balance history for today
                    cur.execute("""
                        SELECT balance_usd, created_at
                        FROM account_snapshots
                        WHERE created_at >= %s
                        ORDER BY created_at ASC
                    """, (today_start,))
                    balances = cur.fetchall()

            # Calculate stats
            num_trades = len([op for op in operations if op[0] in ('open', 'close')])
            num_open = len([op for op in operations if op[0] == 'open'])
            num_close = len([op for op in operations if op[0] == 'close'])

            # Calculate PnL
            if balances and len(balances) >= 2:
                start_balance = float(balances[0][0])
                current_balance = float(balances[-1][0])
                daily_pnl = current_balance - start_balance
                daily_pnl_pct = (daily_pnl / start_balance * 100) if start_balance > 0 else 0.0
            else:
                daily_pnl = 0.0
                daily_pnl_pct = 0.0

            pnl_emoji = "🟢" if daily_pnl >= 0 else "🔴"

            msg = f"""📊 <b>RIEPILOGO GIORNALIERO</b>
<i>{datetime.now(timezone.utc).strftime('%d/%m/%Y')}</i>

<b>Operazioni totali:</b> {num_trades}
  • Aperture: {num_open}
  • Chiusure: {num_close}

<b>PnL giornaliero:</b> {pnl_emoji} ${daily_pnl:,.2f} ({daily_pnl_pct:+.2f}%)

<b>Ultime operazioni:</b>
"""

            # Show last 5 operations
            for i, op in enumerate(operations[:5]):
                operation, symbol, direction, created_at = op
                time_str = created_at.strftime('%H:%M')
                direction_emoji = "🟢" if direction == 'long' else "🔴" if direction == 'short' else "⚪"
                msg += f"{time_str} - {operation.upper()} {direction_emoji} {symbol or ''}\n"

            if not operations:
                msg += "<i>Nessuna operazione oggi</i>\n"

            await update.message.reply_text(msg, parse_mode="HTML")

        except Exception as e:
            logger.error(f"❌ Errore nel recupero riepilogo giornaliero: {e}")
            await update.message.reply_text(f"❌ Errore nel recupero del riepilogo: {str(e)}")

    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /config"""
        await self._log_command(update, "config")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        if not self.trading_agent:
            await update.message.reply_text("⚪ Trading Agent non connesso.")
            return

        config = getattr(self.trading_agent, 'config', {})

        # Extract config values
        tickers = config.get('TICKERS', ['BTC', 'ETH', 'SOL'])
        max_leverage = config.get('MAX_LEVERAGE', 3)
        max_position_size = config.get('MAX_POSITION_SIZE_PCT', 0.3)
        is_testnet = config.get('TESTNET', False)
        cycle_interval = config.get('CYCLE_INTERVAL_MINUTES', 60)
        use_screener = config.get('USE_COIN_SCREENER', False)

        network_emoji = "🧪" if is_testnet else "🌐"

        msg = f"""⚙️ <b>CONFIGURAZIONE</b>

<b>Network:</b> {network_emoji} {'Testnet' if is_testnet else 'Mainnet'}
<b>Tickers:</b> {', '.join(tickers)}
<b>Coin Screener:</b> {'✅ Attivo' if use_screener else '❌ Disattivo'}

<b>Risk Management:</b>
  • Max Leverage: {max_leverage}x
  • Max Position Size: {max_position_size * 100:.0f}% del balance

<b>Ciclo Trading:</b>
  • Intervallo: {cycle_interval} minuti

<i>Configurazione caricata da .env e config.py</i>"""

        await update.message.reply_text(msg, parse_mode="HTML")

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /stop - ferma il trading"""
        await self._log_command(update, "stop")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        if not self.trading_agent:
            await update.message.reply_text("⚪ Trading Agent non connesso.")
            return

        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Sì, ferma", callback_data="confirm_stop"),
                InlineKeyboardButton("❌ Annulla", callback_data="cancel_stop"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ <b>CONFERMA STOP TRADING</b>\n\nSei sicuro di voler fermare il trading automatico?\n\n"
            "<i>Le posizioni aperte rimarranno aperte.</i>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /resume - riprende il trading"""
        await self._log_command(update, "resume")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        if not self.trading_agent:
            await update.message.reply_text("⚪ Trading Agent non connesso.")
            return

        try:
            # Resume trading
            if hasattr(self.trading_agent, 'resume'):
                self.trading_agent.resume()
                await update.message.reply_text("✅ Trading ripreso! Il bot riprenderà l'esecuzione automatica.")
            else:
                # Fallback: set is_running flag
                self.trading_agent.is_running = True
                await update.message.reply_text("✅ Trading ripreso!")

        except Exception as e:
            logger.error(f"❌ Errore nel resume trading: {e}")
            await update.message.reply_text(f"❌ Errore: {str(e)}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /help"""
        await self._log_command(update, "help")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        help_msg = """📖 <b>COMANDI DISPONIBILI</b>

<b>/start</b> - Welcome message e info bot
<b>/status</b> - Stato trading engine e costi
<b>/balance</b> - Saldo wallet Hyperliquid
<b>/positions</b> - Posizioni aperte con PnL
<b>/today</b> - Riepilogo giornaliero
<b>/tokens</b> - Consumo token LLM e costi
<b>/config</b> - Configurazione attuale
<b>/stop</b> - Ferma il trading automatico
<b>/resume</b> - Riprendi il trading
<b>/help</b> - Mostra questo messaggio

<b>Notifiche Automatiche:</b>
Il bot invierà notifiche per:
• Apertura/chiusura trades
• Errori critici
• Circuit breaker attivato
• Riepilogo giornaliero

<i>Per supporto: @yourname</i>"""

        await update.message.reply_text(help_msg, parse_mode="HTML")

    async def cmd_tokens(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per comando /tokens - statistiche consumo token LLM"""
        await self._log_command(update, "tokens")

        if not self._is_authorized(update):
            await update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
            return

        try:
            tracker = get_token_tracker()

            # Get statistics
            today_stats = tracker.get_daily_stats()
            month_stats = tracker.get_monthly_stats()
            breakdown_today = tracker.get_cost_breakdown_by_model()

            # Calculate averages
            now = datetime.now(timezone.utc)
            days_in_month = now.day
            avg_daily_cost = month_stats.total_cost_usd / days_in_month if days_in_month > 0 else 0.0

            # Format breakdown (top 3 models)
            sorted_models = sorted(
                breakdown_today.items(),
                key=lambda x: x[1]['cost'],
                reverse=True
            )[:3]

            models_text = ""
            if sorted_models:
                for model, data in sorted_models:
                    percentage = (data['cost'] / today_stats.total_cost_usd * 100) if today_stats.total_cost_usd > 0 else 0
                    models_text += f"├ {model}: ${data['cost']:.4f} ({percentage:.0f}%)\n"
                models_text = models_text.rstrip('\n')
            else:
                models_text = "├ Nessun dato"

            msg = f"""📊 <b>Consumo Token LLM</b>

📅 <b>Oggi:</b>
├ Token: {today_stats.total_tokens:,}
├ Costo: ${today_stats.total_cost_usd:.4f}
└ Chiamate: {today_stats.api_calls_count}

📈 <b>Questo mese:</b>
├ Token: {month_stats.total_tokens:,}
├ Costo: ${month_stats.total_cost_usd:.2f}
└ Media/giorno: ${avg_daily_cost:.2f}

💰 <b>Per modello (oggi):</b>
{models_text}

⏱ <b>Tempo risposta medio:</b> {today_stats.avg_response_time_ms:.0f}ms

<i>Aggiornato: {now.strftime('%H:%M UTC')}</i>"""

            await update.message.reply_text(msg, parse_mode="HTML")

        except Exception as e:
            logger.error(f"❌ Errore nel comando /tokens: {e}")
            await update.message.reply_text(f"❌ Errore nel recupero statistiche token: {str(e)}")

    # ==================== CALLBACK HANDLERS ====================

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler per callback da InlineKeyboard"""
        query = update.callback_query
        await query.answer()

        if not self._is_authorized(update):
            await query.edit_message_text("❌ Non sei autorizzato a usare questo bot.")
            return

        if query.data == "confirm_stop":
            if self.trading_agent:
                try:
                    # Stop trading
                    if hasattr(self.trading_agent, 'stop'):
                        self.trading_agent.stop()
                    else:
                        # Fallback: set is_running flag
                        self.trading_agent.is_running = False

                    await query.edit_message_text("🛑 <b>Trading fermato!</b>\n\nIl bot non aprirà nuove posizioni.", parse_mode="HTML")
                except Exception as e:
                    logger.error(f"❌ Errore nello stop trading: {e}")
                    await query.edit_message_text(f"❌ Errore: {str(e)}", parse_mode="HTML")
            else:
                await query.edit_message_text("⚪ Trading Agent non connesso.")

        elif query.data == "cancel_stop":
            await query.edit_message_text("✅ Operazione annullata. Il trading continua normalmente.")

    # ==================== NOTIFICATION METHODS (Compatibility) ====================

    def notify_trade_opened(
        self,
        symbol: str,
        direction: str,
        size_usd: float,
        leverage: int,
        entry_price: float,
        stop_loss: float = None,
        take_profit: float = None
    ) -> None:
        """Notifica apertura trade (usa TelegramNotifier)"""
        self.notifier.notify_trade_opened(
            symbol=symbol,
            direction=direction,
            size_usd=size_usd,
            leverage=leverage,
            entry_price=entry_price,
            stop_loss=stop_loss or 0.0,
            take_profit=take_profit or 0.0
        )

    def notify_trade_closed(
        self,
        symbol: str,
        direction: str,
        exit_price: float,
        pnl_usd: float,
        pnl_pct: float,
        reason: str = "Trade chiuso"
    ) -> None:
        """Notifica chiusura trade (usa TelegramNotifier)"""
        self.notifier.notify_trade_closed(
            symbol=symbol,
            direction=direction,
            pnl=pnl_usd,
            pnl_pct=pnl_pct,
            reason=reason
        )

    def notify_circuit_breaker(self, reason: str, current_drawdown: float) -> None:
        """Notifica circuit breaker attivato"""
        msg = f"""🚨 <b>CIRCUIT BREAKER ATTIVATO</b>

<b>Motivo:</b> {reason}
<b>Drawdown:</b> {current_drawdown:.2f}%

Trading fermato automaticamente per protezione del capitale."""
        self.notifier.send(msg)

    def notify_daily_summary(self, trades: int, pnl: float, win_rate: float) -> None:
        """Notifica riepilogo giornaliero"""
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        msg = f"""📊 <b>RIEPILOGO GIORNALIERO</b>

<b>Trades:</b> {trades}
<b>Win Rate:</b> {win_rate:.1f}%
<b>PnL:</b> {pnl_emoji} ${pnl:,.2f}

<i>{datetime.now(timezone.utc).strftime('%d/%m/%Y')}</i>"""
        self.notifier.send(msg)

    def notify_error(self, error_msg: str, context: str = None) -> None:
        """Notifica errore critico"""
        msg = f"""❌ <b>ERRORE</b>

<b>Messaggio:</b> {error_msg}"""
        if context:
            msg += f"\n<b>Contesto:</b> {context}"

        self.notifier.send(msg)

    # ==================== BOT LIFECYCLE ====================

    def start_polling(self) -> None:
        """Avvia il bot in background thread"""
        if not self.enabled:
            logger.warning("⚠️ Bot Telegram disabilitato, impossibile avviare polling")
            return

        if self.thread and self.thread.is_alive():
            logger.warning("⚠️ Bot Telegram già in esecuzione")
            return

        logger.info("🚀 Avvio bot Telegram in background...")

        # Create and start thread
        self.thread = Thread(target=self._run_bot, daemon=True)
        self.thread.start()

        logger.info("✅ Bot Telegram avviato in background thread")

    def _run_bot(self) -> None:
        """Esegue il bot in un thread separato (con proprio event loop)"""
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            # Build application
            self.application = Application.builder().token(self.token).build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("balance", self.cmd_balance))
            self.application.add_handler(CommandHandler("positions", self.cmd_positions))
            self.application.add_handler(CommandHandler("today", self.cmd_today))
            self.application.add_handler(CommandHandler("config", self.cmd_config))
            self.application.add_handler(CommandHandler("tokens", self.cmd_tokens))
            self.application.add_handler(CommandHandler("stop", self.cmd_stop))
            self.application.add_handler(CommandHandler("resume", self.cmd_resume))
            self.application.add_handler(CommandHandler("help", self.cmd_help))

            # Add callback handler
            self.application.add_handler(CallbackQueryHandler(self.callback_handler))

            # Run polling
            # stop_signals=None per evitare errore "set_wakeup_fd only works in main thread"
            logger.info("🤖 Bot Telegram in ascolto...")
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                stop_signals=None
            )

        except Exception as e:
            logger.error(f"❌ Errore nel bot Telegram: {e}")
        finally:
            if self.loop:
                self.loop.close()

    def stop(self) -> None:
        """Ferma il bot in modo pulito"""
        if self.application:
            logger.info("🛑 Fermando bot Telegram...")

            # Stop application
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self.application.stop(), self.loop)

            # Wait for thread
            if self.thread:
                self.thread.join(timeout=5)

            logger.info("✅ Bot Telegram fermato")


# ==================== STANDALONE TEST ====================

if __name__ == "__main__":
    # Test bot standalone
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    bot = TradingTelegramBot()

    if bot.enabled:
        print("✅ Bot configurato, avvio polling...")
        bot.start_polling()

        try:
            # Keep main thread alive
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Chiusura bot...")
            bot.stop()
    else:
        print("❌ Bot non configurato. Imposta TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID in .env")
