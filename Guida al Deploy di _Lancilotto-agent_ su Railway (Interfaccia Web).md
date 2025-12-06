# Guida al Deploy di "Lancilotto-agent" su Railway (Interfaccia Web)

Il progetto "Lancilotto-agent" è configurato per un deployment semplificato su Railway grazie al file `railway.json` [1]. Tuttavia, l'architettura richiede un database PostgreSQL e la configurazione di numerose variabili d'ambiente.

Questa guida illustra i passaggi per il deployment utilizzando **esclusivamente l'interfaccia web** di Railway.

## 1. Preparazione del Repository

Assicurati che il repository GitHub `topweedx-ship-it/Lancilotto-agent` sia accessibile e che tu abbia un account Railway collegato a GitHub.

## 2. Creazione del Progetto su Railway

1.  **Accedi a Railway:** Vai su `https://railway.app/` ed effettua il login.
2.  **Crea un Nuovo Progetto:** Clicca su **"New Project"** (Nuovo Progetto).
3.  **Scegli il Metodo di Deploy:** Seleziona **"Deploy from GitHub Repo"** (Deploy da Repository GitHub).
4.  **Seleziona il Repository:** Cerca e seleziona il repository `Lancilotto-agent`.
5.  **Configura il Deploy:** Railway rileverà automaticamente il file `railway.json` e il progetto verrà creato.

## 3. Aggiunta del Database PostgreSQL

Il backend dell'agente richiede un database PostgreSQL per il logging e la persistenza dei dati.

1.  **Aggiungi un Nuovo Servizio:** All'interno del tuo progetto Railway, clicca su **"New"** (Nuovo) e poi **"Database"**.
2.  **Seleziona PostgreSQL:** Scegli **"PostgreSQL"** dall'elenco dei database disponibili.
3.  **Attendi il Provisioning:** Railway creerà e avvierà automaticamente il servizio PostgreSQL.

## 4. Configurazione delle Variabili d'Ambiente

Questo è il passaggio più critico, poiché l'agente richiede chiavi API e credenziali di trading.

1.  **Vai alla Sezione Variabili:** Nel tuo progetto Railway, seleziona il servizio **"app"** (il tuo agente di trading) e vai alla tab **"Variables"** (Variabili).
2.  **Aggiungi le Variabili del Database:** Railway crea automaticamente le variabili per il database PostgreSQL. Devi usarle per configurare la variabile `DATABASE_URL` del tuo agente.
    *   Crea una nuova variabile:
        *   **Nome:** `DATABASE_URL`
        *   **Valore:** Utilizza la stringa di connessione fornita da Railway per il tuo servizio PostgreSQL. Di solito è disponibile nella sezione **"Connect"** del servizio DB.

3.  **Aggiungi le Variabili di Trading e AI (Obbligatorie):** Inserisci le seguenti variabili, sostituendo i segnaposto con i tuoi valori reali:

| Nome Variabile | Descrizione | Esempio di Valore |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Chiave API per i modelli GPT (GPT-5.1, GPT-4o-mini). | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `MASTER_ACCOUNT_ADDRESS` | Indirizzo del Master Account Hyperliquid (per le chiamate di lettura). | `0x...` |
| `TESTNET` | Modalità di trading. Imposta a `true` per Testnet o `false` per Mainnet. | `true` |
| `TESTNET_PRIVATE_KEY` | Chiave privata del wallet Hyperliquid Testnet (se `TESTNET=true`). | `0x...` |
| `TESTNET_WALLET_ADDRESS` | Indirizzo del wallet Hyperliquid Testnet (se `TESTNET=true`). | `0x...` |
| `PRIVATE_KEY` | Chiave privata del wallet Hyperliquid Mainnet (se `TESTNET=false`). | `0x...` |
| `WALLET_ADDRESS` | Indirizzo del wallet Hyperliquid Mainnet (se `TESTNET=false`). | `0x...` |

4.  **Aggiungi le Variabili Opzionali (Consigliate):**

| Nome Variabile | Descrizione |
| :--- | :--- |
| `DEEPSEEK_API_KEY` | Per usare il modello DeepSeek come alternativa. |
| `TELEGRAM_BOT_TOKEN` | Token del tuo bot Telegram per le notifiche. |
| `TELEGRAM_CHAT_ID` | ID della chat Telegram dove inviare le notifiche. |
| `COINGECKO_API_KEY` | Per aumentare il rate limit del coin screener. |

## 5. Configurazione del Servizio Backend (Agente)

Il file `railway.json` specifica il comando di avvio per il backend: `python main.py`.

1.  **Verifica il Comando di Avvio:** Nella tab **"Settings"** (Impostazioni) del servizio **"app"**, assicurati che il **"Start Command"** (Comando di Avvio) sia impostato correttamente.
    *   **Comando di Avvio:** `python backend/main.py` (Nota: il `railway.json` originale indica `python main.py`, ma il file principale è in `backend/main.py`. Potrebbe essere necessario correggerlo nell'interfaccia se il deploy fallisce).

2.  **Dominio Pubblico:** Nella tab **"Settings"**, assicurati che l'opzione **"Expose App"** (Esporre App) sia abilitata per ottenere un dominio pubblico. Questo è necessario per accedere alla dashboard web.

## 6. Deploy del Frontend (Dashboard)

Il progetto include un frontend React/Vite che deve essere servito.

**Opzione A: Deploy Integrato (Consigliato)**

Il backend `main.py` è configurato per servire i file statici del frontend se sono presenti nella directory `static/` [2].

1.  **Build del Frontend:** Poiché Railway esegue il deploy dal repository, il processo di build deve includere la compilazione del frontend.
    *   **Verifica il Dockerfile:** Il `Dockerfile` del progetto gestisce la build del frontend e del backend in un processo multi-stage. Railway dovrebbe eseguire questo `Dockerfile` automaticamente.
    *   **Se il Frontend non Appare:** Se la dashboard non è visibile, potrebbe essere necessario configurare un comando di build personalizzato in Railway per eseguire `pnpm run build:frontend` prima dell'avvio del backend.

**Opzione B: Deploy Separato (Avanzato)**

Se desideri un frontend separato per maggiore scalabilità:

1.  **Crea un Nuovo Servizio:** Aggiungi un altro servizio al tuo progetto Railway.
2.  **Seleziona il Repository:** Seleziona nuovamente il repository `Lancilotto-agent`.
3.  **Configura il Frontend:**
    *   **Root Directory:** Imposta la directory principale su `frontend/`.
    *   **Comando di Build:** `pnpm install && pnpm run build`
    *   **Comando di Avvio:** Un server statico (es. `serve -s dist`) o il comando di avvio di Railway per le app Node.js.

## 7. Monitoraggio e Debug

1.  **Log:** Dopo il deploy, vai alla tab **"Logs"** (Log) del servizio **"app"** per monitorare l'avvio del `Trading Engine` e l'esecuzione dei cicli di trading.
2.  **Salute del DB:** Controlla la tab **"Health"** (Salute) del servizio PostgreSQL per assicurarti che sia attivo e funzionante.
3.  **Accesso:** Una volta che il servizio "app" è attivo, clicca sul dominio fornito da Railway per accedere alla dashboard web.

---
**Riferimenti**

[1] `railway.json` del repository Lancilotto-agent.
[2] `backend/main.py` del repository Lancilotto-agent.
