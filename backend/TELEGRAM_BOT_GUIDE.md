# 🤖 Trading Agent Telegram Bot - Guida Completa

Bot Telegram interattivo per monitorare e controllare il Trading Agent da remoto.

## 📋 Indice

1. [Setup](#setup)
2. [Configurazione](#configurazione)
3. [Comandi Disponibili](#comandi-disponibili)
4. [Integrazione](#integrazione)
5. [Notifiche Automatiche](#notifiche-automatiche)
6. [Sicurezza](#sicurezza)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Setup

### 1. Installa Dipendenze

```bash
cd backend
uv sync
```

La dipendenza `python-telegram-bot>=20.0` è già inclusa in `pyproject.toml`.

### 2. Crea il Bot su Telegram

1. Apri Telegram e cerca `@BotFather`
2. Invia `/newbot`
3. Scegli un nome per il bot (es. "My Trading Agent Bot")
4. Scegli uno username (es. "my_trading_agent_bot")
5. Riceverai il **Bot Token** (es. `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 3. Ottieni il tuo Chat ID

1. Cerca `@userinfobot` su Telegram
2. Invia `/start`
3. Riceverai il tuo **Chat ID** (es. `123456789`)

### 4. Configura le Variabili d'Ambiente

Aggiungi al file `.env` nella root del progetto:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

---

## ⚙️ Configurazione

### Verifica Configurazione

```python
from telegram_bot import TradingTelegramBot

bot = TradingTelegramBot()
if bot.enabled:
    print("✅ Bot configurato correttamente")
else:
    print("❌ Bot non configurato - controlla .env")
```

### Configurazione Avanzata

```python
# Usa token e chat_id custom
bot = TradingTelegramBot(
    token="your_custom_token",
    chat_id="your_custom_chat_id"
)
```

---

## 📱 Comandi Disponibili

### Comandi di Monitoraggio

| Comando | Descrizione | Esempio Output |
|---------|-------------|----------------|
| `/start` | Welcome message con info bot | Stato bot, network, tickers |
| `/status` | Stato trading engine | Running/Stopped, ultimo ciclo, prossimo ciclo |
| `/balance` | Saldo wallet Hyperliquid | Balance, margine usato, PnL totale |
| `/positions` | Posizioni aperte | Lista posizioni con PnL colorato |
| `/today` | Riepilogo giornaliero | Trades del giorno, PnL, ultime operazioni |
| `/config` | Configurazione corrente | Tickers, leverage, testnet, ciclo |
| `/help` | Lista comandi | Tutti i comandi disponibili |

### Comandi di Controllo

| Comando | Descrizione | Sicurezza |
|---------|-------------|-----------|
| `/stop` | Ferma il trading automatico | Richiede conferma via InlineKeyboard |
| `/resume` | Riprende il trading | Immediato |

### Esempi Output

**`/status`**
```
📊 STATO TRADING ENGINE

Stato: 🟢 ATTIVO
Ultimo ciclo: 14:35:22
Prossimo ciclo: 15:35:22 (tra 58m)
Intervallo cicli: 60 minuti

Il bot sta eseguendo il trading automatico.
```

**`/balance`**
```
💰 SALDO WALLET

Balance: $1,250.50
Margine usato: $150.25
Disponibile: $1,100.25

PnL totale: 🟢 $250.50 (+25.05%)
Balance iniziale: $1,000.00

Aggiornato al: 14:35:42 UTC
```

**`/positions`**
```
📈 POSIZIONI APERTE

🟢 BTC - LONG
Size: 0.050000
Entry: $45,000.0000 | Mark: $45,500.0000
PnL: 🟢 $25.0000
Leverage: 3x (cross)

🔴 ETH - SHORT
Size: 1.500000
Entry: $2,400.0000 | Mark: $2,380.0000
PnL: 🟢 $30.0000
Leverage: 2x (cross)

PnL Totale: 🟢 $55.0000
```

---

## 🔌 Integrazione

### Integrazione Base

```python
from telegram_bot import TradingTelegramBot
from trading_agent import TradingAgent

# 1. Crea il bot
bot = TradingTelegramBot()

# 2. Crea il trading agent
agent = TradingAgent()

# 3. Collega l'agent al bot
bot.set_trading_agent(agent)

# 4. Avvia il bot in background
bot.start_polling()

# 5. Continua con il trading loop normale
agent.run()
```

### Integrazione Completa

```python
import logging
from telegram_bot import TradingTelegramBot
from trading_agent import TradingAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Inizializza bot e agent
    bot = TradingTelegramBot()
    agent = TradingAgent()

    # Collega
    bot.set_trading_agent(agent)

    # Avvia bot in background
    bot.start_polling()

    try:
        # Trading loop principale
        agent.run()

    except KeyboardInterrupt:
        print("\n🛑 Chiusura...")

    finally:
        # Cleanup
        bot.stop()
        agent.shutdown()

if __name__ == "__main__":
    main()
```

### Integrazione con Notifiche

Il bot mantiene compatibilità completa con `TelegramNotifier`:

```python
# Il bot può inviare notifiche push come TelegramNotifier
bot.notify_trade_opened(
    symbol="BTC",
    direction="long",
    size_usd=500.0,
    leverage=3,
    entry_price=45000.0,
    stop_loss=44000.0,
    take_profit=47000.0
)

bot.notify_trade_closed(
    symbol="ETH",
    direction="short",
    exit_price=2380.0,
    pnl_usd=30.0,
    pnl_pct=1.5
)

bot.notify_circuit_breaker(
    reason="Max drawdown raggiunto",
    current_drawdown=15.5
)

bot.notify_daily_summary(
    trades=10,
    pnl=125.50,
    win_rate=70.0
)

bot.notify_error(
    error_msg="Connessione API persa",
    context="fetch_market_data"
)
```

---

## 🔔 Notifiche Automatiche

Il bot può inviare notifiche automatiche per:

### 1. Apertura Trade
```
🟢 TRADE APERTO

Asset: BTC
Direzione: LONG
Size: $500.00
Leva: 3x
Entry: $45,000.00
Stop Loss: $44,000.00
Take Profit: $47,000.00
```

### 2. Chiusura Trade
```
🔴 TRADE CHIUSO

Asset: ETH
Direzione: SHORT
Exit: $2,380.00
PnL: $30.00 (+1.50%)
```

### 3. Circuit Breaker
```
🚨 CIRCUIT BREAKER ATTIVATO

Motivo: Max drawdown raggiunto
Drawdown: 15.50%

Trading fermato automaticamente per protezione del capitale.
```

### 4. Riepilogo Giornaliero
```
📊 RIEPILOGO GIORNALIERO

Trades: 10
Win Rate: 70.0%
PnL: 🟢 $125.50

30/11/2025
```

### 5. Errori Critici
```
❌ ERRORE

Messaggio: Connessione API persa
Contesto: fetch_market_data
```

---

## 🔒 Sicurezza

### Controllo Accessi

Il bot accetta comandi **SOLO** dal `TELEGRAM_CHAT_ID` configurato:

```python
def _is_authorized(self, update: Update) -> bool:
    """Verifica se l'utente è autorizzato"""
    user_chat_id = str(update.effective_chat.id)
    authorized = user_chat_id == self.chat_id

    if not authorized:
        logger.warning(f"⚠️ Tentativo accesso non autorizzato da: {user_chat_id}")

    return authorized
```

### Logging Comandi

Tutti i comandi ricevuti vengono loggati:

```
2025-11-30 14:35:22 - telegram_bot - INFO - 📝 Comando ricevuto: /status da @username (chat_id: 123456789)
```

### Conferma Azioni Critiche

Il comando `/stop` richiede conferma via InlineKeyboard:

```
⚠️ CONFERMA STOP TRADING

Sei sicuro di voler fermare il trading automatico?

Le posizioni aperte rimarranno aperte.

[✅ Sì, ferma] [❌ Annulla]
```

### Best Practices

1. **Non condividere il Bot Token** - È come una password
2. **Limita l'accesso** - Solo il tuo Chat ID può usare il bot
3. **Usa HTTPS** - Telegram usa sempre HTTPS per sicurezza
4. **Revoca token compromessi** - Usa @BotFather → `/revoke`

---

## 🔧 Troubleshooting

### Bot non risponde ai comandi

**Problema:** Il bot non risponde ai comandi su Telegram

**Soluzioni:**
1. Verifica che `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` siano corretti nel `.env`
2. Controlla i log per errori:
   ```bash
   tail -f bot.log
   ```
3. Verifica che il bot sia avviato:
   ```python
   if bot.thread and bot.thread.is_alive():
       print("✅ Bot in esecuzione")
   ```
4. Testa il token manualmente:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
   ```

### Errore "Unauthorized"

**Problema:** `telegram.error.Unauthorized: Forbidden: bot was blocked by the user`

**Soluzione:** Hai bloccato il bot su Telegram. Sbloccalo e riprova.

### Errore "Chat not found"

**Problema:** Il bot non trova la chat con `TELEGRAM_CHAT_ID`

**Soluzioni:**
1. Verifica il Chat ID con @userinfobot
2. Invia `/start` al bot prima di usare altri comandi
3. Assicurati di aver iniziato una conversazione con il bot

### Trading Agent "Non connesso"

**Problema:** I comandi mostrano "Trading Agent non connesso"

**Soluzione:**
```python
# Assicurati di chiamare set_trading_agent
bot.set_trading_agent(agent)
```

### Bot si blocca o crasha

**Problema:** Il bot smette di rispondere dopo un po'

**Soluzioni:**
1. Controlla i log per eccezioni:
   ```python
   logger.error(f"Errore: {e}")
   ```
2. Riavvia il bot:
   ```python
   bot.stop()
   bot.start_polling()
   ```
3. Usa un supervisor (systemd, PM2, supervisord) per auto-restart

### Notifiche non arrivano

**Problema:** Le notifiche push non vengono ricevute

**Soluzioni:**
1. Verifica che `bot.notifier.enabled` sia `True`
2. Controlla che il Chat ID sia corretto
3. Testa manualmente:
   ```python
   bot.notifier.send("Test messaggio")
   ```

---

## 📚 Risorse Aggiuntive

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BotFather Guide](https://core.telegram.org/bots#6-botfather)

---

## 🎯 Prossimi Sviluppi

Funzionalità future pianificate:

- [ ] Comandi per modificare configurazione live
- [ ] Chart PnL inline
- [ ] Alert personalizzati
- [ ] Multi-user support
- [ ] Comandi admin avanzati
- [ ] Integration con webhook invece di polling

---

## 📝 Note Importanti

1. **Thread-safe:** Il bot gira in un thread separato con proprio event loop
2. **Async/Await:** Usa python-telegram-bot v20+ (completamente async)
3. **Background:** Non blocca il main thread del trading agent
4. **Graceful shutdown:** Usa `bot.stop()` per chiusura pulita
5. **Compatibilità:** Mantiene API di `TelegramNotifier` per backward compatibility

---

## 👨‍💻 Supporto

Per problemi o domande:
1. Controlla questa guida
2. Leggi i log del bot
3. Consulta la documentazione ufficiale
4. Apri una issue su GitHub

---

**Buon trading! 🚀📈**
