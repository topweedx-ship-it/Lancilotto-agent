# 🚂 Guida Completa al Deploy su Railway

Questa guida ti accompagna passo per passo nel deployment del Trading Agent su Railway utilizzando **solo l'interfaccia web**. Non è necessario utilizzare la CLI di Railway.

## ⚡ Quick Start (5 minuti)

Se hai già familiarità con Railway, ecco i passi essenziali:

1. **Crea progetto su [Railway](https://railway.app)** → Collega GitHub
2. **Deploy PostgreSQL** → Copia `DATABASE_URL`
3. **Deploy Backend** → Seleziona repo `topweedx-ship-it/Lancilotto-agent`
   - Root Directory: `backend`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Configura Variabili d'Ambiente**:
   ```bash
   DATABASE_URL=postgresql://...  # Dal database
   OPENAI_API_KEY=sk-proj-...     # Tua OpenAI key
   TRADING_BOT_ENABLED=false      # false per test
   PYTHONUNBUFFERED=1
   ```
5. **Genera dominio pubblico** → Visita l'app!

📖 **Continua a leggere per istruzioni dettagliate con screenshot e troubleshooting.**

---

## 📋 Indice

1. [Introduzione](#introduzione)
2. [Prerequisiti](#prerequisiti)
3. [Architettura del Progetto](#architettura-del-progetto)
4. [Setup Account Railway](#setup-account-railway)
5. [Step 1: Deploy del Database PostgreSQL](#step-1-deploy-del-database-postgresql)
6. [Step 2: Deploy del Backend (Applicazione Principale)](#step-2-deploy-del-backend-applicazione-principale)
7. [Step 3: Configurazione Variabili d'Ambiente](#step-3-configurazione-variabili-dambiente)
8. [Step 4: Build e Deploy del Frontend (Opzionale)](#step-4-build-e-deploy-del-frontend-opzionale)
9. [Step 5: Verifica e Testing](#step-5-verifica-e-testing)
10. [Troubleshooting](#troubleshooting)
11. [Costi e Piano Gratuito](#costi-e-piano-gratuito)
12. [Manutenzione e Aggiornamenti](#manutenzione-e-aggiornamenti)

---

## 🎯 Introduzione

Il **Trading Agent** è un'applicazione di trading automatizzato che utilizza AI per analizzare mercati, news e sentiment. Questa guida ti mostrerà come deployare l'intera applicazione su Railway, una piattaforma cloud moderna che semplifica il deployment di applicazioni web.

### Cosa Deploy su Railway:
- ✅ **Backend FastAPI** (Python) - Server principale con API
- ✅ **Database PostgreSQL** - Storage per dati e configurazioni
- ✅ **Frontend React** (integrato nel backend) - Dashboard web

---

## 📋 Prerequisiti

Prima di iniziare, assicurati di avere:

### Account e Credenziali
- ✅ **Account GitHub** - Per accedere al repository
- ✅ **Account Railway** - Registrazione gratuita su [railway.app](https://railway.app)
- ✅ **OpenAI API Key** - Necessaria per l'AI (GPT-4 o GPT-4o-mini)
  - Ottienila su: https://platform.openai.com/api-keys
- ⚡ **Hyperliquid Wallet** (Opzionale) - Solo se vuoi fare trading live
  - Private Key e Wallet Address
  - Per testnet: https://app.hyperliquid-testnet.xyz/

### API Keys Opzionali (Migliorano le funzionalità)
- 🔸 **DeepSeek API Key** - Modello AI alternativo
- 🔸 **CoinGecko API Key** - Dati di mercato aggiuntivi
- 🔸 **CoinMarketCap API Key** - Fear & Greed Index
- 🔸 **Telegram Bot Token** - Notifiche Telegram

### Cosa NON serve
- ❌ CLI o terminal - Useremo solo l'interfaccia web
- ❌ Docker localmente - Railway gestisce tutto
- ❌ Conoscenze DevOps avanzate

---

## 🏗️ Architettura del Progetto

Comprendere la struttura del progetto ti aiuterà durante il deployment:

```
trading-agent/
├── backend/               # 🐍 Backend Python (FastAPI)
│   ├── main.py           # Entry point dell'applicazione
│   ├── pyproject.toml    # Dipendenze Python
│   ├── uv.lock           # Lock file dipendenze
│   ├── trading_engine.py # Engine di trading
│   ├── model_manager.py  # Gestione modelli AI
│   ├── db_utils.py       # Database utilities
│   └── ...               # Altri moduli
├── frontend/             # ⚛️ Frontend React (Vite)
│   ├── app/             # Componenti React
│   ├── package.json     # Dipendenze Node.js
│   ├── vite.config.ts   # Configurazione build
│   └── ...
├── static/              # 📦 Frontend buildato (serve questo)
│   └── logo.png        # Assets statici
├── Dockerfile           # Build container per Docker
├── railway.json         # Configurazione Railway
├── .env.example         # Template variabili d'ambiente
└── README.md

**Componenti chiave per Railway:**
- **Backend**: Serve API su porta 5611 + serve frontend statico
- **Database**: PostgreSQL per storage dati
- **Frontend**: Build a static files, serviti dal backend
```

### Come Funziona
1. Il **frontend** (React) viene buildato in file statici → cartella `static/`
2. Il **backend** (FastAPI) serve:
   - API REST su `/api/*`
   - Frontend statico dalla cartella `static/`
3. Il **database** PostgreSQL memorizza:
   - Posizioni di trading
   - Storico operazioni
   - Configurazioni e logs

---

## 🚀 Setup Account Railway

### Passo 1: Registrazione
1. Vai su **[railway.app](https://railway.app)**
2. Clicca su **"Start a New Project"** o **"Sign Up"**
3. Scegli il metodo di registrazione:
   - ✅ **GitHub** (Consigliato) - Accesso diretto ai repository
   - Oppure: Email, Discord, Google

### Passo 2: Verifica Email (se richiesta)
- Controlla la tua email e conferma l'account

### Passo 3: Crea un Nuovo Progetto
1. Dalla dashboard Railway, clicca su **"New Project"**
2. Ti verrà chiesto di collegare GitHub (se non l'hai già fatto)
3. Autorizza Railway ad accedere ai tuoi repository GitHub

**Screenshot di riferimento:**
```
[Dashboard Railway]
┌─────────────────────────────────────┐
│ 🚂 Railway Dashboard                │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  + New Project              │   │
│  └─────────────────────────────┘   │
│                                     │
│  Your Projects:                     │
│  (Nessun progetto ancora)           │
└─────────────────────────────────────┘
```

---

## 📊 Step 1: Deploy del Database PostgreSQL

Il database deve essere deployato **prima** del backend, perché l'applicazione necessita del `DATABASE_URL` per avviarsi.

### 1.1 Crea il Servizio Database

1. Nel tuo progetto Railway, clicca su **"+ New"**
2. Seleziona **"Database"**
3. Scegli **"PostgreSQL"**

Railway creerà automaticamente un database PostgreSQL con:
- ✅ Username e password generati
- ✅ Host e porta configurati
- ✅ Database pronto all'uso

### 1.2 Ottieni la Connection String

1. Clicca sul servizio **PostgreSQL** appena creato
2. Vai alla tab **"Variables"**
3. Copia la variabile `DATABASE_URL`

Il formato sarà simile a:
```
postgresql://postgres:password@hostname.railway.app:5432/railway
```

**⚠️ IMPORTANTE**: Salva questa stringa, ti servirà nella configurazione del backend.

### 1.3 Configurazione Database (Opzionale)

Railway configura automaticamente:
- 🔹 **Backups automatici** (se hai un piano a pagamento)
- 🔹 **Replica geografica** (opzionale)
- 🔹 **Volume storage** - Dati persistenti

Non è necessaria configurazione aggiuntiva per iniziare.

---

## 🚢 Step 2: Deploy del Backend (Applicazione Principale)

Ora deployeremo l'applicazione principale che include:
- Backend FastAPI (server API)
- Trading Engine
- Frontend buildato (servito dal backend)

### 2.1 Collega il Repository GitHub

1. Nel tuo progetto Railway, clicca su **"+ New"**
2. Seleziona **"GitHub Repo"**
3. Cerca e seleziona: **`topweedx-ship-it/Lancilotto-agent`**
4. Railway rileverà automaticamente che è un progetto Python

### 2.2 Configurazione Automatica di Railway

Railway utilizzerà **Nixpacks** (builder automatico) per:
1. ✅ Rilevare che è un progetto Python
2. ✅ Installare le dipendenze da `backend/pyproject.toml`
3. ✅ Configurare il runtime Python 3.13

### 2.3 Configura le Impostazioni di Deploy

#### A. Imposta il Root Directory
Railway deve sapere dove si trova il codice del backend:

1. Nel servizio appena creato, vai a **"Settings"**
2. Scorri fino a **"Root Directory"**
3. Imposta: `backend`

Questo dice a Railway di eseguire il build dalla cartella `backend/`.

#### B. Configura il Start Command

1. Sempre in **"Settings"**, scorri fino a **"Deploy"**
2. Trova **"Custom Start Command"**
3. Imposta:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

**Perché questo comando?**
- `uvicorn` → Server ASGI per FastAPI
- `main:app` → File `main.py`, oggetto `app`
- `--host 0.0.0.0` → Accetta connessioni da internet
- `--port $PORT` → Usa la porta fornita da Railway (dinamica)

#### C. Esponi il Servizio Pubblicamente

1. In **"Settings"**, vai alla sezione **"Networking"**
2. Clicca su **"Generate Domain"**
3. Railway genererà un dominio tipo: `your-app.up.railway.app`

Questo dominio sarà l'URL pubblico della tua applicazione.

---

## 🔐 Step 3: Configurazione Variabili d'Ambiente

Le variabili d'ambiente contengono le credenziali e configurazioni sensibili.

### 3.1 Accedi alle Variabili d'Ambiente

1. Nel servizio del backend, vai alla tab **"Variables"**
2. Clicca su **"+ New Variable"** oppure **"Raw Editor"** (più veloce)

### 3.2 Variabili OBBLIGATORIE

Copia e incolla queste variabili, sostituendo i valori con i tuoi:

```bash
# ============================================================
# DATABASE (REQUIRED) - Copia dal servizio PostgreSQL
# ============================================================
DATABASE_URL=postgresql://postgres:password@hostname.railway.app:5432/railway

# ============================================================
# OPENAI API (REQUIRED) - Per l'AI Trading Agent
# ============================================================
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# ============================================================
# TRADING BOT CONTROL (REQUIRED)
# ============================================================
# Imposta "false" per testare senza fare trading reale
TRADING_BOT_ENABLED=false

# ============================================================
# PYTHON CONFIG (REQUIRED per Railway)
# ============================================================
PYTHONUNBUFFERED=1
```

### 3.3 Variabili per Trading LIVE (Opzionali ma necessarie per trading)

⚠️ **ATTENZIONE**: Aggiungi queste solo se vuoi fare trading reale!

#### Per Testnet (Consigliato per test):
```bash
# Testnet Configuration
TESTNET=true
TESTNET_PRIVATE_KEY=your-testnet-private-key
TESTNET_WALLET_ADDRESS=your-testnet-wallet-address
```

#### Per Mainnet (Solo dopo aver testato):
```bash
# Mainnet Configuration  
TESTNET=false
PRIVATE_KEY=your-mainnet-private-key
WALLET_ADDRESS=your-mainnet-wallet-address
```

🔥 **SICUREZZA**: NON condividere mai le tue private keys!

### 3.4 Variabili OPZIONALI (Migliorano le funzionalità)

Aggiungi queste se hai le relative API keys:

```bash
# ============================================================
# AI MODELS - OPZIONALI
# ============================================================
# DeepSeek (modello AI alternativo)
DEEPSEEK_API_KEY=sk-your-deepseek-key

# ============================================================
# MARKET DATA - OPZIONALI
# ============================================================
# CoinGecko (migliora rate limit coin screener)
COINGECKO_API_KEY=CG-your-coingecko-key

# CoinMarketCap (Fear & Greed Index)
CMC_PRO_API_KEY=your-cmc-key

# ============================================================
# NOTIFICHE - OPZIONALI
# ============================================================
# Telegram Bot
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# ============================================================
# FRONTEND - OPZIONALE
# ============================================================
# URL del backend per il frontend (Railway lo configura automaticamente)
# VITE_API_URL=https://your-app.up.railway.app
```

### 3.5 Variabili Speciali Railway

Railway fornisce automaticamente alcune variabili:
- `PORT` → Porta su cui il server deve ascoltare (configurato automaticamente)
- `RAILWAY_ENVIRONMENT` → Ambiente (production, staging, etc.)

Non è necessario configurarle manualmente.

### 3.6 Salvare le Variabili

1. Clicca su **"Add"** per ogni variabile
2. Oppure usa **"Raw Editor"** e incolla tutto insieme
3. Railway salverà automaticamente

**⚡ Il deploy ripartirà automaticamente dopo aver salvato le variabili!**

---

## 🎨 Step 4: Build e Deploy del Frontend (Opzionale)

Il frontend può essere:
1. **Buildato manualmente** e committato nella cartella `static/` (già fatto nel repo)
2. **Buildato automaticamente** durante il deploy su Railway

### Opzione A: Frontend Pre-Buildato (Consigliato)

Se nella cartella `static/` del repository c'è già un `index.html`, il frontend è già buildato e verrà servito automaticamente dal backend.

✅ **Nessuna azione necessaria!**

### Opzione B: Build Automatico del Frontend su Railway

Se vuoi che Railway buildi automaticamente il frontend ad ogni deploy:

#### 4.1 Aggiungi Build Command

1. Vai in **"Settings"** del servizio backend
2. Trova **"Custom Build Command"**
3. Imposta:
   ```bash
   cd /app && pnpm install && cd frontend && pnpm install && pnpm build && cd ..
   ```

Questo comando:
- Installa `pnpm` (package manager veloce)
- Installa dipendenze root e frontend
- Builda il frontend in `static/`

#### 4.2 Configura Nixpacks per Node.js + Python

Railway deve sapere che il progetto usa sia Node.js (frontend) che Python (backend).

Crea un file `nixpacks.toml` nella root del repository:

**Contenuto di `nixpacks.toml`:**
```toml
[phases.setup]
nixPkgs = ['nodejs-18_x', 'python313']

[phases.install]
cmds = [
  'cd /app && npm install -g pnpm',
  'cd /app && pnpm install',
  'cd /app/frontend && pnpm install'
]

[phases.build]
cmds = [
  'cd /app/frontend && pnpm build'
]

[start]
cmd = 'cd /app/backend && uvicorn main:app --host 0.0.0.0 --port $PORT'
```

⚠️ **Nota**: Questa configurazione è avanzata. Se il frontend è già buildato, puoi saltare questo step.

### Opzione C: Frontend Separato (Avanzato)

Puoi deployare il frontend come servizio separato:
1. Crea un nuovo servizio Railway
2. Collega lo stesso repository
3. Imposta Root Directory: `frontend`
4. Railway rileverà Vite e builderà automaticamente
5. Configura le variabili `VITE_API_URL` puntando al backend

**Pro**: Frontend e backend scalabili indipendentemente  
**Contro**: Più complesso, richiede configurazione CORS

---

## ✅ Step 5: Verifica e Testing

Dopo il deploy, verifica che tutto funzioni correttamente.

### 5.1 Controlla i Logs di Deploy

1. Nel servizio backend, vai alla tab **"Deployments"**
2. Clicca sull'ultimo deployment
3. Vedrai i logs in tempo reale:

```
Building...
✅ Installing dependencies...
✅ Building application...
✅ Starting server...
INFO: Uvicorn running on 0.0.0.0:PORT
✅ Application started successfully!
```

Se vedi errori:
- ❌ Controlla che tutte le variabili d'ambiente siano configurate
- ❌ Verifica che `DATABASE_URL` sia corretta
- ❌ Vedi la sezione [Troubleshooting](#troubleshooting)

### 5.2 Testa l'Endpoint Health Check

1. Apri il dominio generato da Railway: `https://your-app.up.railway.app`
2. Vai all'endpoint health: `https://your-app.up.railway.app/api/health`

Dovresti vedere:
```json
{
  "status": "healthy",
  "message": "Trading Agent API is running"
}
```

✅ Se vedi questo messaggio, il backend funziona!

### 5.3 Accedi alla Dashboard

1. Vai alla root: `https://your-app.up.railway.app`
2. Dovresti vedere la dashboard del Trading Agent

Se vedi "Frontend not built yet":
- Il frontend non è stato buildato
- Segui le istruzioni in [Step 4](#step-4-build-e-deploy-del-frontend-opzionale)

### 5.4 Controlla i Logs in Real-Time

1. Nel servizio backend, vai alla tab **"Logs"**
2. Vedrai i logs dell'applicazione in tempo reale

Cerca messaggi come:
```
✅ Trading Engine thread avviato
✅ Database connesso
✅ Modelli AI caricati
```

### 5.5 Testa le Funzionalità

#### Test API:
- `/api/health` → Verifica che l'API sia online
- `/api/models` → Lista modelli AI disponibili
- `/api/metrics/overview` → Metriche di trading

#### Test Dashboard:
- **Performance Overview** → Saldo e PnL
- **Market Data** → Dati di mercato
- **System Logs** → Logs in tempo reale

### 5.6 Test Database

Verifica che il database funzioni:

1. Nel servizio PostgreSQL, vai alla tab **"Query"**
2. Esegui:
   ```sql
   SELECT * FROM pg_stat_activity;
   ```
3. Dovresti vedere connessioni attive dal backend

---

## 🔧 Troubleshooting

### Problema: Deploy Fallisce con "Application Error"

**Possibili cause:**
1. ❌ Variabili d'ambiente mancanti
2. ❌ `DATABASE_URL` errata o database non avviato
3. ❌ Start command configurato male

**Soluzioni:**
- ✅ Controlla i logs di deploy per dettagli
- ✅ Verifica che tutte le variabili REQUIRED siano configurate
- ✅ Assicurati che il database sia running (verde)
- ✅ Verifica lo start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Problema: "Internal Server Error" 500

**Possibili cause:**
1. ❌ `OPENAI_API_KEY` mancante o non valida
2. ❌ Database non raggiungibile
3. ❌ Errore nel codice Python

**Soluzioni:**
- ✅ Controlla i logs: tab "Logs" del servizio backend
- ✅ Verifica che `OPENAI_API_KEY` sia valida: https://platform.openai.com/api-keys
- ✅ Testa la connessione al database dalla tab "Query" di PostgreSQL

### Problema: Frontend non si carica

**Possibili cause:**
1. ❌ Cartella `static/` vuota o mancante
2. ❌ Frontend non buildato

**Soluzioni:**
- ✅ Verifica che nella root del repo ci sia la cartella `static/` con `index.html`
- ✅ Buildate il frontend localmente:
  ```bash
  cd frontend
  pnpm install
  pnpm build
  ```
- ✅ Committa i file buildati e fai il redeploy

### Problema: "Module not found" Errori Python

**Possibili cause:**
1. ❌ Dipendenze mancanti in `pyproject.toml`
2. ❌ Root Directory non configurata

**Soluzioni:**
- ✅ Verifica che Root Directory sia `backend`
- ✅ Controlla che `pyproject.toml` e `uv.lock` esistano in `backend/`

### Problema: Database Connection Timeout

**Possibili cause:**
1. ❌ `DATABASE_URL` errata
2. ❌ Database non avviato
3. ❌ Rete tra servizi non configurata

**Soluzioni:**
- ✅ Copia nuovamente `DATABASE_URL` dal servizio PostgreSQL
- ✅ Verifica che il database sia "Running" (stato verde)
- ✅ Railway configura automaticamente la rete privata tra servizi

### Problema: Trading Bot non fa trade

**Possibili cause:**
1. ❌ `TRADING_BOT_ENABLED=false` (modalità demo)
2. ❌ Private keys mancanti
3. ❌ Hyperliquid API non configurata

**Soluzioni:**
- ✅ Verifica nei logs: "TRADING BOT IS DISABLED" → imposta `TRADING_BOT_ENABLED=true`
- ✅ Aggiungi `PRIVATE_KEY` e `WALLET_ADDRESS` (o testnet equivalents)
- ✅ Testa prima su testnet: `TESTNET=true`

### Problema: Costi Inaspettati

**Possibili cause:**
1. ❌ Utilizzo oltre il piano gratuito
2. ❌ Database troppo grande
3. ❌ CPU/RAM oltre i limiti

**Soluzioni:**
- ✅ Controlla il "Usage" nella dashboard Railway
- ✅ Piano gratuito: $5/mese inclusi, poi pay-as-you-go
- ✅ Ottimizza query al database
- ✅ Riduci frequenza polling se necessario

### Ottieni Supporto

Se i problemi persistono:
1. 📧 **Railway Support**: https://railway.app/help
2. 💬 **Discord Railway**: https://discord.gg/railway
3. 📖 **Docs Railway**: https://docs.railway.app
4. 🐛 **Issues GitHub**: Apri un issue nel repository

---

## 💰 Costi e Piano Gratuito

### Piano Gratuito Railway

Railway offre un **piano gratuito** con:
- ✅ **$5 di crediti inclusi al mese**
- ✅ **Nessuna carta di credito richiesta** (per iniziare)
- ✅ Perfetto per testing e sviluppo
- ⚡ Pay-as-you-go dopo i $5

### Cosa Include nei $5 Gratuiti

**Stima utilizzo Trading Agent:**
- **Backend**: ~$2-3/mese
  - Compute: ~$1.50/mese (512MB RAM, CPU moderato)
  - Network: ~$0.50/mese (traffico medio)
- **Database PostgreSQL**: ~$1-2/mese
  - Storage: 1GB incluso (sufficiente per iniziare)
  - Compute: minimo

**Totale stimato**: ~$3-5/mese

✅ **Rientri nel piano gratuito** se l'utilizzo è moderato!

### Quando Serve la Carta di Credito

Railway richiede una carta per:
- 🔸 Uso oltre i $5/mese
- 🔸 Production deployments intensivi
- 🔸 Database con storage >1GB

### Ridurre i Costi

**Ottimizzazioni:**
1. ✅ Usa `TRADING_BOT_ENABLED=false` quando non trading
2. ✅ Riduci la frequenza di polling (modifica nel codice)
3. ✅ Usa testnet per sviluppo (consuma meno risorse)
4. ✅ Sospendi il servizio quando non in uso (da Settings)

### Monitoraggio Costi

1. Dashboard Railway → **"Usage"**
2. Vedrai consumo in tempo reale:
   - Compute (CPU/RAM)
   - Network (banda)
   - Storage (database)

---

## 🔄 Manutenzione e Aggiornamenti

### Deploy Automatico da GitHub

Railway può deployare automaticamente ad ogni push su GitHub:

#### Configurazione Auto-Deploy

1. Nel servizio backend, vai a **"Settings"**
2. Scorri a **"Deploy Triggers"**
3. Attiva **"Automatic Deploys"**
4. Scegli il branch: `main` (o il tuo branch preferito)

Ora, ogni push su GitHub trigghererà automaticamente un nuovo deploy!

### Deploy Manuale

Se vuoi controllare manualmente i deploy:

1. Vai alla tab **"Deployments"**
2. Clicca su **"Deploy"** in alto a destra
3. Railway farà il pull del codice e rebuilderà

### Rollback a Deploy Precedenti

Se un deploy introduce bug:

1. Vai alla tab **"Deployments"**
2. Trova il deployment funzionante
3. Clicca sui 3 puntini (**...**) → **"Rollback"**

Railway ripristinerà immediatamente il deployment precedente!

### Aggiornare le Variabili d'Ambiente

1. Vai alla tab **"Variables"**
2. Modifica o aggiungi variabili
3. Railway farà automaticamente il redeploy

### Backup Database (Importante!)

⚠️ **Il piano gratuito non include backup automatici!**

**Opzioni:**
1. **Upgrade a Piano Pro** → Backup automatici inclusi
2. **Export Manuale**:
   - Vai al servizio PostgreSQL
   - Tab **"Query"**
   - Esporta dati con `pg_dump` (richiede CLI)

**Raccomandazione**: Fai backup regolari dei dati importanti!

### Monitoraggio Logs

Tieni d'occhio i logs per problemi:

1. Tab **"Logs"** → Logs in real-time
2. Filtra per severità: `ERROR`, `WARNING`, `INFO`
3. Cerca pattern di errori ripetuti

### Scaling (Se Necessario)

Se l'app diventa lenta:

1. Vai a **"Settings"** → **"Resources"**
2. Aumenta RAM/CPU (richiede piano a pagamento)
3. Railway aggiusterà automaticamente i limiti

---

## 📚 Risorse Aggiuntive

### Documentazione
- 📖 **Railway Docs**: https://docs.railway.app
- 📖 **Trading Agent README**: Vedi `README.md` del repository
- 📖 **FastAPI Docs**: https://fastapi.tiangolo.com

### Community e Supporto
- 💬 **Discord Railway**: https://discord.gg/railway
- 🐦 **Twitter Railway**: https://twitter.com/Railway
- 🐙 **GitHub Repository**: https://github.com/topweedx-ship-it/Lancilotto-agent

### Video e Tutorial
- 🎥 **Video Presentazione Trading Agent**: [YouTube](https://www.youtube.com/watch?v=Vrl2Ar_SvSo&t=45s)
- 🎥 **Railway Tutorials**: https://railway.app/tutorials

---

## ✅ Checklist Finale

Prima di considerare il deploy completato:

- [ ] ✅ Database PostgreSQL deployato e running
- [ ] ✅ Backend deployato e health check funzionante
- [ ] ✅ Tutte le variabili d'ambiente REQUIRED configurate
- [ ] ✅ Dominio pubblico generato e accessibile
- [ ] ✅ Frontend caricato (oppure vedi dashboard)
- [ ] ✅ Logs puliti senza errori critici
- [ ] ✅ Testato almeno un endpoint API
- [ ] ✅ Trading bot configurato (enabled/disabled come desiderato)
- [ ] ✅ Monitoraggio costi attivato
- [ ] ✅ Auto-deploy configurato (opzionale ma consigliato)

---

## 🎉 Conclusione

Congratulazioni! 🎊 Hai deployato con successo il Trading Agent su Railway!

### Cosa hai imparato:
- ✅ Deploy di applicazioni Python/FastAPI su Railway
- ✅ Configurazione database PostgreSQL cloud
- ✅ Gestione variabili d'ambiente sicure
- ✅ Build e deploy di frontend React
- ✅ Monitoring e troubleshooting

### Prossimi Passi:
1. 🔍 Esplora la dashboard e familiarizza con le funzionalità
2. 📊 Monitora le performance del bot
3. 🧪 Testa su testnet prima di usare mainnet
4. 🔧 Configura notifiche Telegram (opzionale)
5. 📈 Ottimizza strategie di trading

### Sicurezza e Best Practices:
- 🔒 **MAI** committare chiavi private nel repository
- 🔒 Usa sempre testnet per sperimentare
- 🔒 Monitora i logs per attività sospette
- 🔒 Fai backup regolari del database
- 🔒 Tieni aggiornate le dipendenze

---

**Buon trading! 🚀📈**

Per domande o problemi, apri un issue su GitHub o contatta il supporto Railway.

---

*Guida creata per il progetto Trading Agent - Versione 1.0*  
*Ultimo aggiornamento: Dicembre 2024*
