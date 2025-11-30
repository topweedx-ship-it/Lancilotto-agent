# Trading Agent 

**Versione: 0.1.0**

Trading Agent è un progetto open source ispirato a [Alpha Arena](https://nof1.ai/), una piattaforma di trading AI-driven che promuove la competizione tra agenti LLMs. L'obiettivo di questo progetto è sviluppare un agente di trading automatizzato, capace di analizzare dati di mercato, notizie, sentiment e segnali provenienti da grandi movimenti ("whale alert") per prendere decisioni di trading informate.

## Caratteristiche principali

- **Analisi multi-sorgente**: integra dati di mercato, news, sentiment analysis e whale alert.
- **Previsioni**: utilizza modelli di forecasting per anticipare i movimenti di prezzo.
- **Modularità**: ogni componente (news, sentiment, indicatori, whale alert, forecasting) è gestito da moduli separati, facilmente estendibili.
- **Ispirazione Alpha Arena**: il progetto prende spunto dall'approccio competitivo e AI-driven di Alpha Arena, con l'obiettivo di creare agenti sempre più performanti.
- **Gestione multi-modello AI**: supporta GPT-5.1, GPT-4o-mini e DeepSeek con selezione dinamica.

## Configurazione

### Setup iniziale

1. **Copia il file di esempio delle variabili d'ambiente:**
   ```bash
   cp .env.example .env
   ```

2. **Configura le variabili d'ambiente necessarie nel file `.env`:**

   **Variabili REQUIRED:**
   - `OPENAI_API_KEY` - Chiave API OpenAI (per GPT-5.1 e GPT-4o-mini)
   - `DATABASE_URL` - Connection string PostgreSQL

   **Variabili per Trading Live:**
   - `PRIVATE_KEY` - Chiave privata wallet Hyperliquid
   - `WALLET_ADDRESS` - Indirizzo wallet Hyperliquid

   **Variabili OPZIONALI (migliorano le funzionalità):**
   - `DEEPSEEK_API_KEY` - Per usare il modello DeepSeek
   - `COINGECKO_API_KEY` - Per aumentare rate limit del coin screener
   - `CMC_PRO_API_KEY` - Per Fear & Greed Index
   - `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` - Per notifiche Telegram
   - `VITE_API_URL` - URL backend per il frontend (default: http://localhost:8000)

3. **Consulta il file `.env.example` per dettagli completi su tutte le variabili disponibili.**

### Modelli AI supportati

Il sistema supporta automaticamente:
- **GPT-5.1** (`gpt-5.1-2025-11-13`) - Modello di default, richiede `OPENAI_API_KEY`
- **GPT-4o-mini** - Modello veloce ed economico, richiede `OPENAI_API_KEY`
- **DeepSeek** - Modello alternativo, richiede `DEEPSEEK_API_KEY`

Il sistema rileva automaticamente quali modelli sono disponibili in base alle API keys configurate. Puoi selezionare il modello dal frontend o tramite API.

## Video di presentazione

Guarda la presentazione del progetto su YouTube:  
[https://www.youtube.com/watch?v=Vrl2Ar_SvSo&t=45s](https://www.youtube.com/watch?v=Vrl2Ar_SvSo&t=45s)

## Licenza

Questo progetto è distribuito sotto licenza MIT.

---

> Progetto avviato da Rizzo AI Academy
