"""
Esempio di integrazione del TradingTelegramBot con il Trading Agent

Questo file mostra come integrare il bot Telegram nel tuo trading engine.
"""
import logging
import time
from telegram_bot import TradingTelegramBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockTradingAgent:
    """Mock Trading Agent per test"""

    def __init__(self):
        self.is_running = True
        self.last_cycle_time = None
        self.next_cycle_time = None
        self.cycle_interval_minutes = 60
        self.initial_balance = 1000.0

        self.config = {
            'TICKERS': ['BTC', 'ETH', 'SOL'],
            'MAX_LEVERAGE': 3,
            'MAX_POSITION_SIZE_PCT': 0.3,
            'TESTNET': True,
            'CYCLE_INTERVAL_MINUTES': 60,
            'USE_COIN_SCREENER': False,
        }

        # Mock trader
        self.trader = MockTrader()

    def stop(self):
        """Ferma il trading"""
        self.is_running = False
        logger.info("🛑 Trading fermato")

    def resume(self):
        """Riprende il trading"""
        self.is_running = True
        logger.info("▶️ Trading ripreso")


class MockTrader:
    """Mock Hyperliquid Trader per test"""

    def get_account_state(self):
        """Restituisce stato account mock"""
        return {
            'balance_usd': 1250.50,
            'margin_used': 150.25,
            'open_positions': [
                {
                    'symbol': 'BTC',
                    'side': 'long',
                    'size': 0.05,
                    'entry_price': 45000.00,
                    'mark_price': 45500.00,
                    'pnl_usd': 25.00,
                    'leverage': '3x (cross)',
                },
                {
                    'symbol': 'ETH',
                    'side': 'short',
                    'size': 1.5,
                    'entry_price': 2400.00,
                    'mark_price': 2380.00,
                    'pnl_usd': 30.00,
                    'leverage': '2x (cross)',
                },
            ]
        }


# ==================== ESEMPIO 1: Integrazione Base ====================

def example_basic_integration():
    """Esempio di integrazione base"""
    print("\n" + "="*60)
    print("ESEMPIO 1: Integrazione Base")
    print("="*60)

    # 1. Crea il bot
    bot = TradingTelegramBot()

    # 2. Crea il trading agent (o usa quello esistente)
    trading_agent = MockTradingAgent()

    # 3. Collega il trading agent al bot
    bot.set_trading_agent(trading_agent)

    # 4. Avvia il bot in background
    bot.start_polling()

    print("\n✅ Bot avviato!")
    print("📱 Prova a inviare /start al bot su Telegram")

    # Il bot gira in background, il main thread può continuare
    # con il trading loop normale

    return bot, trading_agent


# ==================== ESEMPIO 2: Con Notifiche ====================

def example_with_notifications(bot: TradingTelegramBot):
    """Esempio di utilizzo delle notifiche"""
    print("\n" + "="*60)
    print("ESEMPIO 2: Notifiche Push")
    print("="*60)

    # Notifica apertura trade
    bot.notify_trade_opened(
        symbol="BTC",
        direction="long",
        size_usd=500.0,
        leverage=3,
        entry_price=45000.0,
        stop_loss=44000.0,
        take_profit=47000.0
    )
    print("📤 Notifica 'trade opened' inviata")

    # Notifica chiusura trade
    bot.notify_trade_closed(
        symbol="ETH",
        direction="short",
        exit_price=2380.0,
        pnl_usd=30.0,
        pnl_pct=1.5,
        reason="Take profit raggiunto"
    )
    print("📤 Notifica 'trade closed' inviata")

    # Notifica circuit breaker
    bot.notify_circuit_breaker(
        reason="Max drawdown raggiunto",
        current_drawdown=15.5
    )
    print("📤 Notifica 'circuit breaker' inviata")

    # Notifica riepilogo giornaliero
    bot.notify_daily_summary(
        trades=10,
        pnl=125.50,
        win_rate=70.0
    )
    print("📤 Notifica 'daily summary' inviata")

    # Notifica errore
    bot.notify_error(
        error_msg="Connessione API persa",
        context="fetch_market_data"
    )
    print("📤 Notifica 'error' inviata")


# ==================== ESEMPIO 3: Integrazione Completa ====================

def example_full_integration():
    """Esempio di integrazione completa in un trading engine"""
    print("\n" + "="*60)
    print("ESEMPIO 3: Integrazione Completa")
    print("="*60)

    # Setup
    trading_agent = MockTradingAgent()
    bot = TradingTelegramBot()
    bot.set_trading_agent(trading_agent)
    bot.start_polling()

    print("\n✅ Trading Agent + Bot Telegram pronti!")
    print("\nComandi disponibili su Telegram:")
    print("  /start - Info bot")
    print("  /status - Stato trading")
    print("  /balance - Saldo wallet")
    print("  /positions - Posizioni aperte")
    print("  /today - Riepilogo giornaliero")
    print("  /config - Configurazione")
    print("  /stop - Ferma trading")
    print("  /resume - Riprendi trading")
    print("  /help - Aiuto")

    # Simula un trading loop
    import time
    try:
        print("\n🔄 Trading loop in esecuzione...")
        print("   (Premi Ctrl+C per fermare)")

        while True:
            if trading_agent.is_running:
                # Qui va la logica di trading normale
                # Il bot risponde ai comandi in background
                pass

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n🛑 Chiusura...")
        bot.stop()
        print("✅ Bot fermato")

    return bot, trading_agent


# ==================== ESEMPIO 4: Solo Testing ====================

def example_test_bot_standalone():
    """Testa il bot senza Trading Agent"""
    print("\n" + "="*60)
    print("ESEMPIO 4: Test Bot Standalone")
    print("="*60)

    # Il bot può funzionare anche senza Trading Agent collegato
    bot = TradingTelegramBot()
    bot.start_polling()

    print("\n✅ Bot avviato in modalità standalone!")
    print("⚠️ Trading Agent non connesso - i comandi mostreranno 'Non connesso'")
    print("📱 Prova a inviare /start al bot su Telegram")

    import time
    try:
        print("\n⏳ Bot in ascolto... (Ctrl+C per fermare)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Chiusura...")
        bot.stop()


# ==================== MAIN ====================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║       TRADING AGENT - TELEGRAM BOT INTEGRATION             ║
║                  Esempi di utilizzo                        ║
╚════════════════════════════════════════════════════════════╝
""")

    # Verifica configurazione
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ ERRORE: Bot Telegram non configurato!")
        print("\nPer usare il bot, aggiungi al tuo .env:")
        print("  TELEGRAM_BOT_TOKEN=il_tuo_bot_token")
        print("  TELEGRAM_CHAT_ID=il_tuo_chat_id")
        print("\n📖 Guida setup:")
        print("  1. Crea un bot con @BotFather su Telegram")
        print("  2. Ottieni il token")
        print("  3. Ottieni il tuo chat_id con @userinfobot")
        exit(1)

    print("✅ Configurazione trovata!")
    print(f"   Bot Token: {token[:20]}...")
    print(f"   Chat ID: {chat_id}")

    # Scegli esempio
    print("\n" + "="*60)
    print("Scegli un esempio da eseguire:")
    print("="*60)
    print("1. Integrazione Base")
    print("2. Test Notifiche")
    print("3. Integrazione Completa (con loop)")
    print("4. Test Bot Standalone")
    print("="*60)

    choice = input("\nScegli (1-4) [default: 3]: ").strip() or "3"

    if choice == "1":
        bot, agent = example_basic_integration()
        # Keep running
        import time
        try:
            print("\n⏳ Bot in ascolto... (Ctrl+C per fermare)")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Chiusura...")
            bot.stop()

    elif choice == "2":
        bot, agent = example_basic_integration()
        time.sleep(2)  # Wait for bot to start
        example_with_notifications(bot)
        print("\n✅ Tutte le notifiche inviate!")
        print("   Controlla Telegram per vederle")
        input("\nPremi INVIO per chiudere...")
        bot.stop()

    elif choice == "3":
        example_full_integration()

    elif choice == "4":
        example_test_bot_standalone()

    else:
        print("❌ Scelta non valida")

    print("\n✅ Esempio completato!")
