# Coin Screener Module

Sistema di selezione dinamica delle criptovalute per il Trading Agent.

## Overview

Il modulo `coin_screener` implementa un sistema quantitativo di screening che:
- Analizza tutte le coin disponibili su Hyperliquid
- Applica filtri hard per escludere coin non idonee
- Calcola punteggi compositi basati su momentum, volume, volatilità e altri fattori
- Seleziona le top N coin per il trading automatico
- Esegue rebalancing settimanale e aggiornamenti giornalieri

## Struttura

```
coin_screener/
├── __init__.py              # Exports principali
├── screener.py              # Engine principale
├── models.py                # Data models (CoinScore, CoinMetrics, etc.)
├── filters.py               # Filtri hard
├── scoring.py               # Sistema di scoring
├── db_migration.py          # Migrazione database
├── db_utils.py              # Utilità database
├── README.md                # Questa documentazione
└── data_providers/
    ├── __init__.py
    ├── hyperliquid.py       # Provider dati Hyperliquid
    ├── coingecko.py         # Provider dati CoinGecko
    └── cache.py             # Sistema di caching
```

## Configurazione

### Environment Variables

Aggiungi al file `.env`:

```bash
# Coin Screener (opzionale)
COINGECKO_API_KEY=your_api_key_here  # Opzionale, aumenta rate limit
```

### CONFIG in main.py

```python
CONFIG = {
    # Coin Screening
    "SCREENING_ENABLED": False,  # Set to True per abilitare
    "TOP_N_COINS": 5,            # Numero di coin da selezionare
    "REBALANCE_DAY": "sunday",   # Giorno per rebalance completo
    "FALLBACK_TICKERS": ["BTC", "ETH", "SOL"],  # Fallback se screening fallisce
    ...
}
```

## Filtri Hard

Le coin devono soddisfare TUTTI questi criteri per essere considerate:

| Filtro | Valore Default | Descrizione |
|--------|----------------|-------------|
| `min_volume_24h_usd` | $50M | Volume minimo 24h |
| `min_market_cap_usd` | $250M | Market cap minimo |
| `min_days_listed` | 30 | Giorni minimi di listing |
| `min_open_interest_usd` | $10M | Open interest minimo |
| `max_spread_pct` | 0.5% | Spread bid-ask massimo |
| `exclude_stablecoins` | True | Escludi stablecoin |

## Sistema di Scoring

Ogni coin riceve un punteggio 0-100 basato su questi fattori:

| Fattore | Peso | Descrizione |
|---------|------|-------------|
| `momentum_7d` | 20% | Performance 7 giorni (percentile) |
| `momentum_30d` | 15% | Performance 30 giorni (percentile) |
| `volatility_regime` | 15% | ATR(14) > SMA(ATR, 20) |
| `volume_trend` | 15% | Volume 7d vs 30d |
| `oi_trend` | 10% | Trend open interest |
| `funding_stability` | 10% | Stabilità funding rate |
| `liquidity_score` | 10% | Spread bid-ask |
| `relative_strength` | 5% | Performance vs BTC |

**Formula finale:**
```python
score = sum(weight * factor_score for weight, factor_score in factors) * 100
```

## Utilizzo

### Esempio Base

```python
from coin_screener import CoinScreener

# Inizializzazione
screener = CoinScreener(
    testnet=True,
    coingecko_api_key="your_api_key",
    top_n=5
)

# Screening completo (settimanale)
result = screener.run_full_screening()

print(f"Selected coins: {[c.symbol for c in result.selected_coins]}")
for coin in result.selected_coins:
    print(f"{coin.symbol}: {coin.score:.2f} points")

# Update giornaliero
updated = screener.update_scores()

# Get cached results (per ciclo trading)
coins = screener.get_selected_coins()
tickers = [c.symbol for c in coins]
```

### Configurazione Personalizzata

```python
from coin_screener import CoinScreener, HardFilterConfig, ScoringWeights

# Custom filters
filters = HardFilterConfig(
    min_volume_24h_usd=100_000_000,  # $100M
    min_market_cap_usd=500_000_000,  # $500M
    min_days_listed=60,
    max_spread_pct=0.3
)

# Custom weights
weights = ScoringWeights(
    momentum_7d=0.25,     # Più peso al momentum breve
    momentum_30d=0.10,
    volatility_regime=0.20,
    volume_trend=0.20,
    oi_trend=0.05,
    funding_stability=0.05,
    liquidity_score=0.10,
    relative_strength=0.05
)

screener = CoinScreener(
    testnet=True,
    filter_config=filters,
    scoring_weights=weights
)
```

## Scheduling

Il sistema implementa automaticamente:

- **Rebalance completo**: Ogni domenica 00:00 UTC
- **Update scores**: Ogni 24 ore
- **Check rapido**: Ogni ciclo di trading (usa cache)

## Database

Il modulo crea 3 tabelle:

### `coin_screenings`
Registra ogni screening completo con timestamp, tipo, coin selezionate ed escluse.

### `coin_scores_history`
Storico dei punteggi per ogni coin, utile per analisi trend.

### `coin_metrics_snapshots`
Snapshot dei metrics grezzi per debugging.

### Migrazione

La migrazione viene eseguita automaticamente all'inizializzazione se `SCREENING_ENABLED=True`.

Per eseguire manualmente:

```python
from coin_screener.db_migration import run_migration
from db_utils import get_connection

with get_connection() as conn:
    run_migration(conn)
```

## Query Utili

### Ultime coin selezionate
```sql
SELECT selected_coins
FROM coin_screenings
ORDER BY created_at DESC
LIMIT 1;
```

### Storico punteggi di una coin
```sql
SELECT created_at, score, rank, factors
FROM coin_scores_history
WHERE symbol = 'BTC'
ORDER BY created_at DESC
LIMIT 30;
```

### Top coin più selezionate
```sql
SELECT symbol, COUNT(*) as selections
FROM coin_scores_history
WHERE rank <= 5
GROUP BY symbol
ORDER BY selections DESC
LIMIT 10;
```

## Integrazione con main.py

Il modulo si integra automaticamente nel ciclo di trading:

1. All'inizializzazione, crea il `CoinScreener` se `SCREENING_ENABLED=True`
2. Ad ogni ciclo, verifica se serve rebalance
3. Se sì, esegue screening completo e logga risultati
4. Altrimenti usa coins cached
5. Passa i ticker selezionati al resto del pipeline

## Caching

Il sistema usa cache su file per ridurre chiamate API:

- **Screening results**: 1 ora
- **Selected coins**: 1 ora
- **CoinGecko data**: Gestito dal rate limiter interno

Cache location: `.cache/screener/`

Per pulire la cache:
```python
screener.clear_cache()
```

## Testing

Esempio di test:

```python
def test_screener():
    screener = CoinScreener(testnet=True, top_n=3)

    # Test screening
    result = screener.run_full_screening()
    assert len(result.selected_coins) <= 3
    assert all(coin.score >= 0 and coin.score <= 100
               for coin in result.selected_coins)

    # Test cache
    cached = screener.get_selected_coins()
    assert len(cached) > 0

    print("✅ All tests passed")
```

## Troubleshooting

### No coins pass filters
Probabilmente i filtri sono troppo restrittivi. Prova:
- Ridurre `min_market_cap_usd` a $100M
- Ridurre `min_volume_24h_usd` a $20M
- Verificare che ci siano abbastanza coin su testnet

### CoinGecko rate limit
Se usi la tier gratuita (50 req/min):
- Il sistema rispetta automaticamente i limiti
- Considera ottenere una API key Pro per rate limit più alti
- Il caching riduce le chiamate ripetute

### Hyperliquid Rate Limiting (429)
Il sistema implementa diverse ottimizzazioni per evitare il rate limiting severo di Hyperliquid:
- **Pre-fetching dei prezzi**: I prezzi correnti (`all_mids`) vengono scaricati in un'unica chiamata batch all'inizio dello screening, invece di una chiamata per ogni simbolo.
- **Singola chiamata per metriche**: Invece di 5-6 chiamate separate per simbolo (7d, 30d, volume, ATR, trend), viene scaricato un unico set di candele OHLCV (250 giorni) e tutte le metriche vengono calcolate in memoria.
- **Adaptive Delays**: Il sistema introduce delay tra le chiamate (0.5s) e pause più lunghe (5s) ogni 20 simboli.
- **Exponential Backoff**: Se si verifica un errore 429, il sistema attende progressivamente più a lungo (fino a 30s) prima di riprovare.

### Screening molto lento
- Prima esecuzione è lenta (fetching dati per tutte le coin)
- Successive esecuzioni usano cache
- Considera ridurre numero di simboli da analizzare

### Missing data
Alcune coin potrebbero non avere mapping CoinGecko. Aggiungi manualmente:

```python
screener.cg_provider.add_symbol_mapping("SYMBOL", "coingecko-id")
```

## Metriche di Performance

Il modulo logga metriche dettagliate:

```
🔍 Starting full coin screening...
Found 50 symbols on Hyperliquid
Fetched metrics for 45 coins
Hard filters: 12 passed, 33 excluded
Scored 12 coins
✅ Screening complete: Selected 5 coins
  1. BTC: 87.42 points (7d: 85.3, vol: 92.1)
  2. ETH: 82.15 points (7d: 78.9, vol: 88.4)
  ...
```

## Roadmap

Features future:
- [ ] Machine learning per weights ottimali
- [ ] Backtesting del screening system
- [ ] Alert su cambio composizione portfolio
- [ ] Integration con più exchange
- [ ] API REST per query esterne

## Supporto

Per problemi o feature request, aprire issue su GitHub con:
- Log completo dell'errore
- Configurazione usata
- Ambiente (testnet/mainnet)
