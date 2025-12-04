# 🚀 Docker Build Optimization

## Problema Risolto

Il build Docker stava impiegando **~11 minuti** principalmente per scaricare dipendenze Python pesanti (torch, prophet, numpy, scikit-learn, etc.).

## Ottimizzazioni Implementate

### 1. **Layer Caching Ottimizzato**
- **Prima**: Dipendenze scaricate ogni volta
- **Ora**: Dipendenze cachate separatamente dal codice

### 2. **Struttura Dockerfile Migliore**
```dockerfile
# 1. Frontend: cache package.json prima del codice
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 2. Backend: cache pyproject.toml prima del codice
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project
```

### 3. **.dockerignore Intelligente**
Esclude file non necessari dal build context:
- File Git, cache Python, node_modules
- Log files, file temporanei
- File di sviluppo (.env, test files)

### 4. **Docker BuildKit**
```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

## Risultati Attesi

| Scenario | Prima | Ora |
|----------|-------|-----|
| **Primo build** | ~11 min | ~8-9 min |
| **Build successivi** (solo codice cambia) | ~11 min | ~1-2 min |
| **Build successivi** (dipendenze cambiano) | ~11 min | ~6-7 min |

## Come Usare

### Metodo 1: Script Bash
```bash
# Build ottimizzato
./build.sh

# Build + test + avvia
./build.sh --test --up
```

### Metodo 2: Make (Raccomandato)
```bash
# Build ottimizzato
make build

# Sviluppo completo: build + avvia + logs
make dev

# Solo riavvia
make restart

# Analisi backtrack
make backtrack-analysis
```

### Metodo 3: Docker Compose Diretto
```bash
# Build con BuildKit
DOCKER_BUILDKIT=1 docker compose build

# Avvia
docker compose up -d
```

## Comandi Utili

```bash
# Vedi logs build dettagliati
docker compose build --progress=plain

# Build senza cache (per debug)
docker compose build --no-cache

# Vedi dimensione immagini
docker images trading-agent:latest --format "table {{.Repository}}\t{{.Size}}"

# Cache efficiente per rebuild
docker compose build --parallel
```

## Troubleshooting

### Build ancora lento?
1. **Controlla connessione internet** - dipendenze pesanti richiedono banda
2. **Docker daemon memory** - assicurati abbia abbastanza RAM (4GB+)
3. **Pulizia cache** - `docker system prune` se necessario

### Problemi di cache?
```bash
# Forza rebuild senza cache
make clean
make build

# Oppure
docker compose build --no-cache
```

## Architettura Ottimizzata

```
Build Context (Ridotto da .dockerignore)
├── frontend/
│   ├── package.json + pnpm-lock.yaml  ← CACHED
│   └── src/                           ← COPIED LATE
├── backend/
│   ├── pyproject.toml + uv.lock       ← CACHED
│   └── src/                           ← COPIED LATE
└── Dockerfile

Dockerfile Layers
├── Frontend deps (cached)
├── Frontend build (changes rarely)
├── Python deps (cached - BIGGEST WIN!)
├── Python code (changes often)
└── Final image
```

## Metriche di Successo

Dopo l'ottimizzazione, monitora:
- **Build time** per rebuild successivi: dovrebbe essere < 2 minuti
- **Cache hit ratio**: la maggior parte dei layer dovrebbe essere cached
- **Image size**: dovrebbe rimanere stabile (~2-3GB con dipendenze ML)

## Note Tecniche

- **uv.lock**: garantisce versioni esatte, migliora riproducibilità
- **--frozen**: previene aggiornamenti automatici imprevisti
- **--no-install-project**: dipendenze solo, non il progetto stesso
- **BuildKit**: parallelizzazione e caching avanzato
