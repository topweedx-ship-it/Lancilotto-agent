# 📊 Token Tracking & Cost Management - Guida Completa

Sistema completo di tracking consumo token LLM con calcolo costi, statistiche e visualizzazioni.

## 🎯 Panoramica

Il sistema traccia automaticamente:
- ✅ Token input/output per ogni chiamata LLM
- ✅ Costi calcolati in tempo reale per modello
- ✅ Breakdown per purpose (trading_decision, market_analysis, etc.)
- ✅ Storico giornaliero/mensile
- ✅ Statistiche aggregate e medie
- ✅ Visualizzazioni frontend con grafici
- ✅ Comandi Telegram per monitoraggio remoto

---

## 📦 Componenti Implementati

### 1. Backend - `token_tracker.py`

**Classe `TokenTracker`** con:
- Tracking automatico di ogni chiamata LLM
- Database PostgreSQL per persistenza
- Fallback in-memory se DB non disponibile
- Calcolo costi automatico basato su prezzi aggiornati
- API per statistiche aggregate

**Prezzi supportati** (per 1M token):
```python
PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}
```

### 2. Database - Tabella `llm_usage`

Schema completo con indici ottimizzati:
```sql
CREATE TABLE llm_usage (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    model VARCHAR(50) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    input_cost_usd DECIMAL(10, 6),
    output_cost_usd DECIMAL(10, 6),
    total_cost_usd DECIMAL(10, 6),
    purpose VARCHAR(50),
    ticker VARCHAR(20),
    cycle_id VARCHAR(50),
    response_time_ms INTEGER
);
```

### 3. API Endpoints - `main.py`

**GET `/api/token-usage?period={today|session|week|month|all}`**
```json
{
  "period": "today",
  "total_tokens": 125000,
  "total_cost_usd": 0.45,
  "breakdown_by_model": {
    "gpt-4o": {"tokens": 50000, "cost": 0.35, "calls": 15},
    "deepseek-chat": {"tokens": 75000, "cost": 0.10, "calls": 30}
  },
  "breakdown_by_purpose": {
    "trading_decision": {"tokens": 100000, "cost": 0.40, "calls": 35},
    "market_analysis": {"tokens": 25000, "cost": 0.05, "calls": 10}
  },
  "api_calls_count": 45,
  "avg_tokens_per_call": 2778,
  "avg_response_time_ms": 850
}
```

**GET `/api/token-usage/history?days=30`**
```json
{
  "days": 30,
  "data": [
    {"date": "2025-11-01", "tokens": 120000, "cost": 0.42, "calls": 45},
    {"date": "2025-11-02", "tokens": 135000, "cost": 0.48, "calls": 52}
  ]
}
```

### 4. Frontend - `TokenUsage.tsx`

Componente React con:
- 📊 Pie chart breakdown per modello
- 📈 Line chart trend ultimi 7 giorni
- 🎯 KPI cards (token totali, costo, media, latenza)
- 🔄 Auto-refresh ogni 60 secondi
- 📱 Responsive design completo
- ⚠️ Indicatori budget (verde/giallo/rosso)

### 5. Telegram Bot - Comando `/tokens`

Output esempio:
```
📊 Consumo Token LLM

📅 Oggi:
├ Token: 125,430
├ Costo: $0.4520
└ Chiamate: 45

📈 Questo mese:
├ Token: 2,450,000
├ Costo: $12.30
└ Media/giorno: $0.41

💰 Per modello (oggi):
├ gpt-4o: $0.3500 (78%)
├ deepseek-chat: $0.1020 (22%)

⏱ Tempo risposta medio: 850ms

Aggiornato: 14:35 UTC
```

Comando `/status` aggiornato con:
```
💰 Costo LLM oggi: $0.4520
```

---

## 🔌 Integrazione nel Trading Engine

### Step 1: Importa il tracker

```python
from token_tracker import get_token_tracker

# Inizializza (singleton globale)
tracker = get_token_tracker()
```

### Step 2: Traccia ogni chiamata LLM

**OpenAI / DeepSeek (compatibile OpenAI API):**

```python
import time

# Misura tempo di risposta
start_time = time.time()

# Chiamata LLM
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    # ... altri parametri
)

# Calcola latenza
response_time_ms = int((time.time() - start_time) * 1000)

# Traccia utilizzo
tracker.track_usage(
    model="gpt-4o",  # Nome modello
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    purpose="trading_decision",  # o "market_analysis", "news_summary"
    ticker="BTC",  # Asset analizzato (opzionale)
    cycle_id=f"cycle_{timestamp}",  # ID ciclo (opzionale)
    response_time_ms=response_time_ms  # Latenza (opzionale)
)
```

### Step 3: Esempio completo in `trading_agent.py`

```python
from token_tracker import get_token_tracker
from openai import OpenAI
import time

class TradingAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tracker = get_token_tracker()

    def make_trading_decision(self, ticker: str, market_data: dict) -> dict:
        """Chiama LLM per decisione di trading"""

        # Prepara prompt
        messages = [
            {"role": "system", "content": "You are a trading assistant..."},
            {"role": "user", "content": f"Analyze {ticker}: {market_data}"}
        ]

        # Misura tempo
        start = time.time()

        # Chiamata LLM
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"}
        )

        # Traccia consumo
        self.tracker.track_usage(
            model="gpt-4o",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            purpose="trading_decision",
            ticker=ticker,
            cycle_id=self.current_cycle_id,
            response_time_ms=int((time.time() - start) * 1000)
        )

        # Parse risposta
        decision = json.loads(response.choices[0].message.content)
        return decision
```

---

## 📊 Utilizzo del Frontend

### Aggiungere alla Dashboard

Il componente è già integrato in `Dashboard.tsx`. Per personalizzare:

```tsx
import { TokenUsage } from './components/TokenUsage'

function MyDashboard() {
  return (
    <div>
      {/* ... altri componenti ... */}

      {/* Token Usage con configurazione personalizzata */}
      <article className="p-4 rounded-lg border bg-white">
        <TokenUsage />
      </article>
    </div>
  )
}
```

### Budget Configuration

Modifica i budget in `TokenUsage.tsx`:

```tsx
const DAILY_BUDGET = 5.0   // Budget giornaliero ($)
const MONTHLY_BUDGET = 100.0  // Budget mensile ($)
```

O meglio, leggi da variabili d'ambiente:

```tsx
const DAILY_BUDGET = parseFloat(import.meta.env.VITE_TOKEN_DAILY_BUDGET_USD || "5.0")
const MONTHLY_BUDGET = parseFloat(import.meta.env.VITE_TOKEN_MONTHLY_BUDGET_USD || "100.0")
```

---

## 🤖 Utilizzo Telegram Bot

### Comandi disponibili

| Comando | Descrizione | Output |
|---------|-------------|--------|
| `/tokens` | Statistiche token complete | Oggi, mese, breakdown modelli |
| `/status` | Include costo oggi | Stato + `💰 Costo LLM oggi: $X.XX` |
| `/help` | Lista comandi aggiornata | Include `/tokens` |

### Test del bot

```bash
cd backend
python example_telegram_integration.py
```

Invia `/tokens` al bot su Telegram per verificare.

---

## 📈 Monitoraggio e Alerts

### Budget Alerts (TODO - implementazione futura)

```python
# In token_tracker.py o trading_agent.py

def check_budget_alerts():
    """Controlla se i budget sono stati superati"""
    tracker = get_token_tracker()

    # Budget configurabili
    DAILY_BUDGET = float(os.getenv("TOKEN_DAILY_BUDGET_USD", "5.0"))
    MONTHLY_BUDGET = float(os.getenv("TOKEN_MONTHLY_BUDGET_USD", "100.0"))

    # Check oggi
    today_stats = tracker.get_daily_stats()
    if today_stats.total_cost_usd > DAILY_BUDGET:
        # Invia alert via Telegram
        bot.notify_error(
            f"⚠️ Budget giornaliero superato: ${today_stats.total_cost_usd:.2f} > ${DAILY_BUDGET}",
            context="token_budget"
        )

    # Check mese
    month_stats = tracker.get_monthly_stats()
    if month_stats.total_cost_usd > MONTHLY_BUDGET:
        # Alert mensile
        bot.notify_error(
            f"⚠️ Budget mensile superato: ${month_stats.total_cost_usd:.2f} > ${MONTHLY_BUDGET}",
            context="token_budget"
        )
```

### Notifica giornaliera automatica (TODO)

Aggiungi allo scheduler:

```python
from apscheduler.schedulers.background import BackgroundScheduler

def send_daily_token_summary():
    """Invia riepilogo costi giornaliero alle 00:00 UTC"""
    tracker = get_token_tracker()
    today_stats = tracker.get_daily_stats()

    msg = f"""📊 RIEPILOGO COSTI TOKEN

Oggi: ${today_stats.total_cost_usd:.4f}
Token: {today_stats.total_tokens:,}
Chiamate: {today_stats.api_calls_count}

Media/chiamata: {today_stats.avg_tokens_per_call:.0f} token
Latenza media: {today_stats.avg_response_time_ms:.0f}ms
"""

    bot.notifier.send(msg)

# Setup scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_token_summary, 'cron', hour=0, minute=0)
scheduler.start()
```

---

## ⚙️ Configurazione

### Variabili d'ambiente (`.env`)

```env
# Database (già configurato)
DATABASE_URL=postgresql://user:pass@localhost:5432/trading_db

# Token budgets (opzionale - per alerts futuri)
TOKEN_DAILY_BUDGET_USD=5.00
TOKEN_MONTHLY_BUDGET_USD=100.00

# Telegram (già configurato)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Frontend (`.env` nella root)

```env
# API URL (opzionale, usa proxy Vite se non impostato)
VITE_API_URL=http://localhost:5611

# Budget thresholds (opzionale)
VITE_TOKEN_DAILY_BUDGET_USD=5.00
VITE_TOKEN_MONTHLY_BUDGET_USD=100.00
```

---

## 🧪 Testing

### Test Backend

```bash
cd backend
python token_tracker.py
```

Output atteso:
```
=== TEST TOKEN TRACKING ===
=== SESSION STATS ===
Total tokens: 4,300
Total cost: $0.008004
API calls: 2
...
✅ Test completato!
```

### Test API

```bash
# Test token usage endpoint
curl http://localhost:5611/api/token-usage?period=today | jq

# Test history endpoint
curl http://localhost:5611/api/token-usage/history?days=7 | jq
```

### Test Frontend

```bash
cd frontend
pnpm dev
```

Apri `http://localhost:5621` e verifica il componente Token Usage.

### Test Telegram Bot

```bash
cd backend
python example_telegram_integration.py
```

Invia `/tokens` su Telegram.

---

## 📝 Best Practices

### 1. Purpose Naming Convention

Usa nomi consistenti per `purpose`:
- `trading_decision` - Decisioni di apertura/chiusura trade
- `market_analysis` - Analisi generale di mercato
- `news_summary` - Riassunti news
- `risk_assessment` - Valutazione rischio
- `portfolio_rebalance` - Ribilanciamento portafoglio

### 2. Cycle ID

Usa un formato consistente per `cycle_id`:
```python
cycle_id = f"cycle_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
```

Permette di aggregare tutte le chiamate LLM di un singolo ciclo di trading.

### 3. Error Handling

Sempre wrappa il tracking in try/except:
```python
try:
    tracker.track_usage(...)
except Exception as e:
    logger.error(f"Errore tracking token: {e}")
    # Non bloccare il trading se il tracking fallisce
```

### 4. Database Maintenance

Query periodica per pulizia dati vecchi (opzionale):
```sql
-- Elimina record più vecchi di 6 mesi
DELETE FROM llm_usage
WHERE timestamp < NOW() - INTERVAL '6 months';
```

---

## 🔄 Aggiornamento Prezzi

Quando i prezzi cambiano, aggiorna `PRICING` in `token_tracker.py`:

```python
PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},  # ← Aggiorna qui
    # ...
}
```

I nuovi prezzi si applicano automaticamente ai tracking futuri.
I costi storici rimangono calcolati con i prezzi del momento.

---

## 📊 Metriche Chiave

### KPI da Monitorare

1. **Costo medio/giorno** - Target: < $2-5/giorno
2. **Token/decisione** - Ottimizza i prompt se troppo alto
3. **Latenza media** - Target: < 1000ms
4. **Modello più costoso** - Valuta switch a modelli più economici
5. **Breakdown per purpose** - Identifica aree di ottimizzazione

### Ottimizzazione Costi

- ✅ Usa `gpt-4o-mini` per task semplici
- ✅ Usa `deepseek-chat` quando possibile (molto economico)
- ✅ Riduci lunghezza prompts
- ✅ Cachea risultati quando applicabile
- ✅ Batch multiple richieste quando possibile

---

## 🆘 Troubleshooting

### Database non si connette

```bash
# Verifica connessione
psql $DATABASE_URL -c "SELECT 1"

# Tabella non esiste?
python -c "from token_tracker import get_token_tracker; get_token_tracker()"
```

### Costi non compaiono nel frontend

1. Verifica backend running: `curl http://localhost:5611/api/token-usage`
2. Controlla console browser per errori
3. Verifica proxy Vite in `vite.config.ts`

### Bot Telegram non risponde a /tokens

1. Verifica import: `from token_tracker import get_token_tracker`
2. Handler registrato: cerca `CommandHandler("tokens", self.cmd_tokens)`
3. Check logs: `tail -f bot.log`

---

## 📚 Risorse

- [OpenAI Pricing](https://openai.com/pricing)
- [DeepSeek Pricing](https://platform.deepseek.com/pricing)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Chart.js Documentation](https://www.chartjs.org/docs/)

---

**Sistema completo e pronto all'uso! 🚀**

Tracking automatico, visualizzazioni real-time, monitoring remoto via Telegram - tutto integrato seamlessly nel trading agent.
