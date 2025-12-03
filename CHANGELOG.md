# Changelog

## [0.1.0] - 2025-12-01

### 🚀 New Features

#### Frontend Dashboard
- **Performance Overview Widget**: Visualizzazione immediata di Saldo Attuale, PnL Totale ($ e %) e Saldo Iniziale. Gestione intelligente del saldo iniziale (primo valore > 0).
- **Market Data Widget**: Dati di mercato aggregati in tempo reale (Prezzo medio, Spread, Funding Rate, Deviazione Hyperliquid).
- **System Logs Widget**: Terminale di log integrato nella dashboard per il debugging in tempo reale.
- **Closed Positions Widget**: Storico delle posizioni chiuse con visualizzazione grafica del Win Rate e card dettagliate.
- **Enhanced Bot Operations**: Nuova UI per le operazioni del bot con box dedicati per "Market Data" (RSI, MACD) e "AI Forecast".
- **Manual Refresh**: Aggiunti pulsanti di aggiornamento manuale su tutti i singoli componenti per un controllo granulare.

#### Backend
- **API Endpoints**:
  - `GET /api/market-data/aggregate`: Endpoint per dati di mercato aggregati.
  - `GET /api/system-logs`: Endpoint per leggere i log di sistema.
  - `GET /api/trades/stats`: Statistiche avanzate sui trade chiusi.
- **Reliability**:
  - Implementata logica di **Retry automatico** con backoff esponenziale per le chiamate API Hyperliquid (fix errore 429 Rate Limit).
  - **File Logging**: Il sistema ora scrive i log su `trading_agent.log` oltre che su console.
  - **Database Cleanup**: Pulizia automatica di trade "fantasma" o invalidi (prezzi a 0).
- **Dependencies**: Aggiunta libreria `PyYAML` per la gestione delle configurazioni.

### 🐛 Bug Fixes
- Risolto errore `ECONNREFUSED` all'avvio del frontend (race condition con il backend).
- Risolto calcolo errato `+Infinity%` nel widget Performance Overview.
- Risolto crash del backend per mancanza di `pyyaml`.
- Corretta visualizzazione trade con prezzi nulli/zero.

### 🛠 Maintenance
- Aggiornata configurazione `uv` e `pyproject.toml`.
- Migliorata gestione errori nel `trading_engine`.




