# Trading Agent 

**Versione: 0.1.0**

Trading Agent è un progetto open source ispirato a [Alpha Arena](https://nof1.ai/), una piattaforma di trading AI-driven che promuove la competizione tra agenti LLMs. L'obiettivo di questo progetto è sviluppare un agente di trading automatizzato, capace di analizzare dati di mercato, notizie, sentiment e segnali provenienti da grandi movimenti ("whale alert") per prendere decisioni di trading informate.

## Caratteristiche principali

- **Analisi multi-sorgente**: integra dati di mercato, news, sentiment analysis e whale alert.
- **Previsioni**: utilizza modelli di forecasting per anticipare i movimenti di prezzo.
- **Modularità**: ogni componente (news, sentiment, indicatori, whale alert, forecasting) è gestito da moduli separati, facilmente estendibili.
- **Ispirazione Alpha Arena**: il progetto prende spunto dall'approccio competitivo e AI-driven di Alpha Arena, con l'obiettivo di creare agenti sempre più performanti.
- **Gestione multi-modello AI**: supporta GPT-5.1, GPT-4o-mini e DeepSeek con selezione dinamica.
- **Coin Screener Dinamico**: seleziona automaticamente le migliori coin in base a filtri quantitativi (volume, momentum, volatilità).
- **Analisi Manuale**: possibilità di eseguire analisi on-demand su specifiche coin senza interrompere il bot.

## 📊 Dashboard Web

Il progetto include una moderna dashboard web (React/Vite) per il monitoraggio in tempo reale.

### Caratteristiche Dashboard (v0.1.0)
- **Performance Overview**: Saldo, PnL e metriche chiave.
- **Market Data**: Dati di mercato aggregati e spread.
- **Operazioni AI**: Log delle decisioni dell'agente con ragionamento e forecast.
- **System Logs**: Log di sistema in tempo reale.
- **Gestione Posizioni**: Visualizzazione posizioni aperte e storico chiuse.

Per avviare la dashboard:
```bash
cd frontend
pnpm install
pnpm dev
```
La dashboard sarà accessibile a `http://localhost:5621`.

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
   - `TESTNET` - Modalità testnet/mainnet ("true" per testnet, "false" per mainnet, default: "true")
   - **Per Testnet:**
     - `TESTNET_PRIVATE_KEY` - Chiave privata wallet Hyperliquid Testnet
     - `TESTNET_WALLET_ADDRESS` - Indirizzo wallet Hyperliquid Testnet
     - Testnet URL: https://app.hyperliquid-testnet.xyz/trade
     - Testnet Faucet: https://app.hyperliquid-testnet.xyz/drip
   - **Per Mainnet:**
     - `PRIVATE_KEY` - Chiave privata wallet Hyperliquid Mainnet
     - `WALLET_ADDRESS` - Indirizzo wallet Hyperliquid Mainnet

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

## Utilizzo Avanzato

### Analisi Manuale

È possibile eseguire un'analisi on-demand su una specifica criptovaluta per verificare le condizioni di mercato o testare l'AI senza dover attendere il ciclo automatico del bot.

```bash
cd backend
python manual_analysis.py <SYMBOL>
```

Esempio:
```bash
python manual_analysis.py ETH
```

Questo script eseguirà l'intero processo decisionale (fetch dati, analisi tecnica, news, sentiment, decisione AI, trend check) e mostrerà il risultato nei log.

## Video di presentazione

Guarda la presentazione del progetto su YouTube:  
[https://www.youtube.com/watch?v=Vrl2Ar_SvSo&t=45s](https://www.youtube.com/watch?v=Vrl2Ar_SvSo&t=45s)

## Licenza

Questo progetto è distribuito sotto licenza MIT.

---

> Progetto avviato da Rizzo AI Academy
