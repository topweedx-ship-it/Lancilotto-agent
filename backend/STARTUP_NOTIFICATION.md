# 🚀 Trading Agent Startup Notification

## Panoramica

Il sistema di notifica di avvio del Trading Agent è già completamente implementato e funzionante. Quando il trading agent viene avviato, invia automaticamente una notifica via Telegram con i dettagli della configurazione.

## ✅ Implementazione Esistente

### 1. Modulo Notifiche (`notifications.py`)

Il metodo `notify_startup()` è stato implementato nella classe `TelegramNotifier`:

```python
def notify_startup(
    self,
    testnet: bool = True,
    tickers: list = None,
    cycle_interval_minutes: int = 60,
    wallet_address: str = None
) -> None:
    """Notifica avvio Trading Agent"""
```

**Caratteristiche:**
- ✅ Indica se è TESTNET (🧪) o MAINNET (🌐)
- ✅ Mostra wallet address abbreviato per sicurezza
- ✅ Lista degli asset monitorati
- ✅ Intervallo dei cicli di trading
- ✅ Timestamp di avvio
- ✅ Formattazione HTML per Telegram

### 2. Integrazione nel Trading Engine (`trading_engine.py`)

La notifica viene inviata automaticamente all'avvio del trading agent (linee 554-568):

```python
# Invia notifica di avvio via Telegram PRIMA di avviare lo scheduler
try:
    if notifier.enabled:
        logger.info("📤 Invio notifica di avvio via Telegram...")
        notifier.notify_startup(
            testnet=CONFIG["TESTNET"],
            tickers=CONFIG["TICKERS"],
            cycle_interval_minutes=CONFIG["CYCLE_INTERVAL_MINUTES"],
            wallet_address=WALLET_ADDRESS
        )
        logger.info("✅ Notifica di avvio inviata via Telegram")
    else:
        logger.warning("⚠️ Telegram notifier non configurato")
except Exception as e:
    logger.error(f"❌ Errore nell'invio notifica Telegram: {e}", exc_info=True)
```

**Vantaggi dell'implementazione:**
- 🛡️ **Error handling robusto**: Se l'invio fallisce, l'agent continua comunque l'esecuzione
- 📊 **Logging dettagliato**: Ogni tentativo è loggato
- ⚡ **Non bloccante**: La notifica viene inviata prima dello scheduler ma non blocca l'avvio
- 🔧 **Configurabile**: Usa le variabili d'ambiente del file `.env`

## 📱 Formato del Messaggio

Quando il trading agent viene avviato, riceverai un messaggio Telegram come questo:

```
🚀 TRADING AGENT AVVIATO

🧪 TESTNET  (oppure 🌐 MAINNET)
Wallet: 0x1234567...abc123
Asset monitorati: BTC, ETH, SOL
Intervallo cicli: 3 minuti

✅ Sistema operativo e pronto al trading

⏰ 2025-12-01 14:35:22
```

## 🔧 Configurazione

### Variabili d'Ambiente Richieste (`.env`)

```env
# Bot Telegram (richiesto per notifiche)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Configurazione Trading Agent
TESTNET=true                           # true per testnet, false per mainnet
TESTNET_WALLET_ADDRESS=0x...           # Wallet address per testnet
TESTNET_PRIVATE_KEY=0x...              # Private key per testnet

# Oppure per mainnet:
# TESTNET=false
# WALLET_ADDRESS=0x...
# PRIVATE_KEY=0x...
```

### Verifica Configurazione

Puoi verificare che il notifier sia configurato correttamente:

```bash
cd backend
python -c "
from notifications import notifier
print('Telegram notifier abilitato:', notifier.enabled)
"
```

Output atteso:
```
Telegram notifier abilitato: True
```

## 🧪 Test Manuale

### Test della Notifica di Avvio

```bash
cd backend
python -c "
from notifications import notifier
import os

CONFIG = {
    'TESTNET': True,
    'TICKERS': ['BTC', 'ETH', 'SOL'],
    'CYCLE_INTERVAL_MINUTES': 3
}

WALLET_ADDRESS = os.getenv('TESTNET_WALLET_ADDRESS')

notifier.notify_startup(
    testnet=CONFIG['TESTNET'],
    tickers=CONFIG['TICKERS'],
    cycle_interval_minutes=CONFIG['CYCLE_INTERVAL_MINUTES'],
    wallet_address=WALLET_ADDRESS
)
print('✅ Notifica inviata! Controlla Telegram')
"
```

### Test Completo del Trading Agent

Per vedere la notifica in azione con l'avvio reale del trading agent:

```bash
cd backend
python trading_engine.py
```

All'avvio vedrai nei log:

```
2025-12-01 14:35:20 | INFO | __main__ | ============================================================
2025-12-01 14:35:20 | INFO | __main__ | 🚀 TRADING AGENT - Avvio
2025-12-01 14:35:20 | INFO | __main__ | ============================================================
2025-12-01 14:35:21 | INFO | __main__ | 📤 Invio notifica di avvio via Telegram...
2025-12-01 14:35:22 | INFO | notifications | ✅ Notifica di avvio inviata con successo
2025-12-01 14:35:22 | INFO | __main__ | ✅ Notifica di avvio inviata via Telegram
```

E contemporaneamente riceverai il messaggio su Telegram.

## 🔍 Troubleshooting

### La notifica non viene inviata

**Problema**: Nessun messaggio su Telegram all'avvio

**Soluzioni**:

1. **Verifica credenziali Telegram**:
   ```bash
   cat .env | grep TELEGRAM
   ```
   Devono essere presenti `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`

2. **Verifica che il bot sia abilitato**:
   ```bash
   python -c "from notifications import notifier; print('Enabled:', notifier.enabled)"
   ```

3. **Controlla i log** per eventuali errori:
   ```bash
   python trading_engine.py 2>&1 | grep -i telegram
   ```

4. **Testa manualmente il bot**:
   ```bash
   python -c "
   from notifications import notifier
   result = notifier.send('🧪 Test messaggio')
   print('Successo:', result)
   "
   ```

### Errore "Telegram notifier non configurato"

**Causa**: Mancano `TELEGRAM_BOT_TOKEN` o `TELEGRAM_CHAT_ID` nel file `.env`

**Soluzione**: Aggiungi le credenziali nel file `.env`:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### Come ottenere le credenziali Telegram

1. **Crea un bot Telegram**:
   - Apri Telegram e cerca `@BotFather`
   - Invia `/newbot` e segui le istruzioni
   - Copia il token fornito → `TELEGRAM_BOT_TOKEN`

2. **Ottieni il tuo Chat ID**:
   - Apri Telegram e cerca `@userinfobot`
   - Invia `/start`
   - Copia il tuo ID → `TELEGRAM_CHAT_ID`

3. **Avvia il bot**:
   - Cerca il tuo bot su Telegram
   - Invia `/start` per attivarlo

## 📊 Altre Notifiche Disponibili

Oltre alla notifica di avvio, il sistema supporta:

- ✅ `notify_trade_opened()` - Trade aperto
- ✅ `notify_trade_closed()` - Trade chiuso
- ✅ `notify_circuit_breaker()` - Circuit breaker attivato
- ✅ `notify_daily_summary()` - Riepilogo giornaliero
- ✅ `notify_error()` - Errori critici
- ✅ **`notify_startup()` - Avvio trading agent** ← Già implementato

E con il bot interattivo completo (`telegram_bot.py`):

- ✅ `/start` - Info iniziali
- ✅ `/status` - Stato attuale del bot
- ✅ `/balance` - Bilancio corrente
- ✅ `/positions` - Posizioni aperte
- ✅ `/today` - Performance giornaliera
- ✅ `/tokens` - Consumo token LLM
- ✅ `/stop` - Ferma il bot
- ✅ `/resume` - Riprendi il bot
- ✅ `/config` - Mostra configurazione
- ✅ `/help` - Lista comandi

## 🎯 Conclusione

✅ **La funzionalità richiesta è già completamente implementata e funzionante.**

Quando avvii il trading agent con `python trading_engine.py`, riceverai automaticamente una notifica Telegram con:
- Network (Testnet/Mainnet)
- Wallet address
- Asset monitorati
- Intervallo cicli
- Timestamp di avvio

Nessuna modifica ulteriore è necessaria. Il sistema è pronto all'uso! 🚀
