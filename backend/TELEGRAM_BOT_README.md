# 🤖 Telegram Bot - Quick Start

Bot Telegram interattivo per controllare il Trading Agent da remoto.

## ⚡ Setup Rapido (5 minuti)

### 1. Installa dipendenze
```bash
cd backend
uv sync
```

### 2. Crea il bot su Telegram
1. Cerca `@BotFather` su Telegram
2. Invia `/newbot` e segui le istruzioni
3. Copia il **Bot Token** che ricevi

### 3. Ottieni il tuo Chat ID
1. Cerca `@userinfobot` su Telegram
2. Invia `/start`
3. Copia il tuo **Chat ID**

### 4. Configura .env
Aggiungi alla root del progetto `.env`:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### 5. Testa il bot
```bash
cd backend
python example_telegram_integration.py
```

Prova a inviare `/start` al bot su Telegram!

## 🚀 Integrazione nel Trading Agent

```python
from telegram_bot import TradingTelegramBot

# Crea e configura il bot
bot = TradingTelegramBot()
bot.set_trading_agent(trading_agent)
bot.start_polling()

# Il bot gira in background!
# Continua con il trading loop normale
```

## 📱 Comandi Disponibili

- `/start` - Info bot e menu
- `/status` - Stato trading engine
- `/balance` - Saldo wallet
- `/positions` - Posizioni aperte
- `/today` - Riepilogo giornaliero
- `/config` - Configurazione
- `/stop` - Ferma trading (con conferma)
- `/resume` - Riprendi trading
- `/help` - Lista comandi

## 📊 Notifiche Automatiche

Il bot invia notifiche push per:
- ✅ Apertura/chiusura trades
- 🚨 Circuit breaker attivato
- ❌ Errori critici
- 📊 Riepilogo giornaliero

## 🔒 Sicurezza

- ✅ Solo il tuo Chat ID può controllare il bot
- ✅ Conferma richiesta per azioni critiche (`/stop`)
- ✅ Logging completo di tutti i comandi
- ✅ Nessun dato sensibile nei log

## 📖 Documentazione Completa

Leggi [TELEGRAM_BOT_GUIDE.md](./TELEGRAM_BOT_GUIDE.md) per:
- Esempi di integrazione avanzati
- Troubleshooting
- API reference completa
- Best practices

## 🎯 Esempio Output

**`/positions`**
```
📈 POSIZIONI APERTE

🟢 BTC - LONG
Size: 0.050000
Entry: $45,000 | Mark: $45,500
PnL: 🟢 $25.00
Leverage: 3x

PnL Totale: 🟢 $25.00
```

## ⚙️ File Creati

- `telegram_bot.py` - Classe principale TradingTelegramBot
- `example_telegram_integration.py` - Esempi di integrazione
- `TELEGRAM_BOT_GUIDE.md` - Guida completa
- `TELEGRAM_BOT_README.md` - Questo file (quick start)

## 🆘 Problemi?

**Bot non risponde?**
- Verifica Bot Token e Chat ID in `.env`
- Controlla di aver inviato `/start` al bot
- Controlla i log: `tail -f bot.log`

**"Trading Agent non connesso"?**
```python
# Assicurati di collegare l'agent
bot.set_trading_agent(agent)
```

**Altre domande?**
- Leggi [TELEGRAM_BOT_GUIDE.md](./TELEGRAM_BOT_GUIDE.md)
- Controlla [python-telegram-bot docs](https://docs.python-telegram-bot.org/)

---

**Fatto! Il bot è pronto. Buon trading! 🚀**
