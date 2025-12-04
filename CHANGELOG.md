# Changelog

## [0.1.1] - 2025-12-04

### 🚀 New Features

#### 🤖 AI Decision Backtrack Analysis
- **Complete Backtrack System**: Nuovo sistema completo per analizzare decisioni AI storiche e correlarle con risultati effettivi
- **Decision Context Tracking**: Tracciamento completo del contesto AI (indicatori, news, sentiment, forecasts) per ogni decisione
- **Performance Correlation**: Analisi correlazione tra decisioni AI, condizioni di mercato e risultati di trading
- **Backtrack API Endpoint**: Nuovo endpoint `/api/backtrack-analysis` per analisi programmata
- **Decision Outcome Analysis**: Metriche avanzate su win rate, profit factor, exit reasons per categoria

#### 📊 Frontend Backtrack Dashboard
- **Backtrack Analysis Component**: Nuovo componente React per visualizzare analisi backtrack
- **Performance Metrics Dashboard**: Metriche chiave (win rate, execution rate, profit/loss) con filtri per periodo
- **Category Analysis**: Breakdown performance per operazione (open/close/hold), symbol e direzione
- **Exit Reason Distribution**: Analisi distribuzione motivi chiusura trade con impatto sul profitto
- **Improvement Recommendations**: Suggerimenti automatici basati su pattern identificati (confidence threshold, risk management)

#### 🐳 Docker Production Optimization
- **Build Optimization**: Riduzione tempi build da ~11 minuti a ~1-2 minuti per rebuild successivi
- **Layer Caching**: Implementazione intelligente caching dipendenze Python separate dal codice
- **Docker BuildKit**: Utilizzo BuildKit per build paralleli e caching avanzato
- **Multi-Environment Support**: Configurazioni separate per sviluppo e produzione

#### 🏭 Enterprise Production Deployment
- **Production-Ready Stack**: Configurazione completa per produzione con alta disponibilità
- **Security Hardening**: User non-root, read-only filesystem, security headers, rate limiting
- **SSL/TLS Support**: Configurazione Nginx con SSL termination e Let's Encrypt
- **Load Balancing**: Nginx reverse proxy con health checks e load balancing
- **Zero-Downtime Deployment**: Sistema di deployment rolling con backup automatico
- **Resource Management**: Limits CPU/memoria per tutti i servizi

#### 📈 Monitoring & Observability
- **Prometheus Integration**: Metriche complete per monitoraggio applicativo e infrastrutturale
- **Grafana Dashboards**: Dashboard pre-configurati per trading performance e system health
- **Centralized Logging**: Logging strutturato JSON per centralizzazione e analisi
- **Health Checks**: Health checks automatici per tutti i servizi con alerting
- **Metrics Collection**: Raccolta metriche API, database, sistema e trading performance

#### 💾 Backup & Recovery System
- **Automated Database Backup**: Backup PostgreSQL automatico con compressione
- **Configuration Backup**: Backup configurazione e certificati SSL
- **Retention Policy**: Gestione automatica retention backup con cleanup
- **Integrity Verification**: Verifica integrità backup con checksum
- **Recovery Scripts**: Script automatizzati per disaster recovery

#### 🔒 Security Enhancements
- **Container Security**: Security-opt, no-new-privileges, read-only root filesystem
- **Network Security**: Rate limiting, DDoS protection, IP filtering
- **Secret Management**: Environment-based secrets con Docker secrets support
- **SSL/TLS Everywhere**: Crittografia end-to-end per tutte le comunicazioni
- **Audit Logging**: Logging completo per compliance e security monitoring

#### 🚀 Deployment Automation
- **Production Deploy Script**: Script `production-deploy.sh` per deployment automatizzato
- **CI/CD Ready**: Support completo per pipeline CI/CD con GitLab CI, GitHub Actions
- **Environment Management**: Gestione multi-environment (dev/staging/prod)
- **Rollback Automation**: Rollback automatico in caso di deployment failure
- **Version Tagging**: Tagging automatico immagini Docker con git commit SHA

### 🐛 Bug Fixes
- Risolto memory leak nel backtrack analysis per dataset di grandi dimensioni
- Fix race condition in Docker build con dipendenze Python pesanti
- Corretto calcolo metriche performance per trade con dati incompleti
- Risolto timeout nei backup database per tabelle molto grandi

### 🛠 Maintenance
- Aggiornata versione a 0.1.1 in pyproject.toml
- Aggiunto supporto Python 3.13 con ottimizzazioni performance
- Migliorata gestione errori e logging strutturato
- Aggiornati requirements sicurezza e dipendenze

### 📚 Documentation
- **Production README**: Guida completa deployment produzione (`PRODUCTION_README.md`)
- **Docker Optimization**: Documentazione ottimizzazioni build (`DOCKER_OPTIMIZATION_README.md`)
- **Data Tracking Analysis**: Analisi sistema tracciamento dati (`DATA_TRACKING_ANALYSIS.md`)
- **API Documentation**: Documentazione completa nuovi endpoint backtrack
- **Security Guidelines**: Linee guida sicurezza per produzione

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




