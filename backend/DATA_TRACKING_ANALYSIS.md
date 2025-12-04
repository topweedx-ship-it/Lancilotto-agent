# Analisi Tracciamento Dati - Trading Agent Backtrack
## Stato Attuale vs Raccomandazioni

### ✅ DATI GIÀ TRACCIATI

#### 1. Decisioni AI (`bot_operations`)
- Operazione (open/close/hold)
- Symbol, direction, target_portion_of_balance, leverage
- Raw payload completo con ragione e confidence
- Timestamp e collegamento ad AI context

#### 2. Trade Eseguiti (`executed_trades`)
- Collegamento diretto alle decisioni AI
- Prezzi entry/exit, size, P&L, duration
- Exit reason (take_profit, stop_loss, manual, signal, trend_reversal)
- Fee, slippage, leverage, stop_loss/take_profit levels
- Stato (open/closed/cancelled)

#### 3. Contesto AI (`ai_contexts` + context tables)
- **Indicators** (`indicators_contexts`): RSI, MACD, EMA, volumi, OI, funding rate, pivot points
- **News** (`news_contexts`): Testo news rilevante
- **Sentiment** (`sentiment_contexts`): Valore sentiment + classificazione
- **Forecasts** (`forecasts_contexts`): Previsioni prezzo con confidence intervals

#### 4. Stato Account (`account_snapshots`)
- Balance periodico
- Posizioni aperte con P&L corrente

#### 5. Token Usage (`llm_usage` via token_tracker)
- Token input/output per chiamata
- Costi per modello
- Tempi di risposta
- Modello utilizzato

#### 6. Errori (`errors`)
- Errori con contesto e traceback

### ❌ DATI MANCANTI - HIGH PRIORITY

#### 1. Performance Modelli AI
**Attuale**: Token usage e costi
**Mancante**:
- **Accuracy per modello**: Win rate per modello specifico
- **Response time correlation**: Correlazione tra velocità risposta e qualità decisione
- **Model selection rationale**: Perché è stato scelto quel modello
- **Fallback reasons**: Quando/Perché è stato fatto fallback a modello alternativo
- **Cost-benefit analysis**: Performance vs costo per modello

#### 2. Market Conditions al Momento Decisione
**Attuale**: Indicatori tecnici nel contesto
**Mancante**:
- **Market regime**: Trending vs Ranging (ADX, volatilità)
- **Correlazioni inter-market**: BTC vs ALT, USD vs crypto
- **Liquidity metrics**: Bid-ask spread changes, volume profile
- **Order book depth**: Livelli di liquidità disponibili
- **Whale activity**: Grossi movimenti di capitale rilevati

#### 3. Timing e Latency
**Attuale**: Timestamp decisione
**Mancante**:
- **Decision-to-execution time**: Quanto tempo passa tra decisione AI e ordine su exchange
- **Market condition changes**: Come cambiano le condizioni mentre aspetti esecuzione
- **Slippage analysis**: Slippage effettivo vs slippage teorico
- **Queue position**: Posizione in coda ordini durante alta volatilità

#### 4. Risk Metrics Evolutivi
**Attuale**: Stop loss e take profit statici
**Mancante**:
- **Portfolio risk metrics**: Value at Risk (VaR), Expected Shortfall
- **Drawdown tracking**: Max drawdown per sessione, giornaliero, storico
- **Sharpe ratio**: Risk-adjusted returns
- **Consecutive losses tracking**: Pattern di perdite consecutive
- **Position sizing evolution**: Come cambia sizing basato su performance

#### 5. External Factors Impact
**Attuale**: News e sentiment di base
**Mancante**:
- **News impact quantification**: Correlazione impatto news su prezzo
- **Social sentiment**: Twitter, Reddit, Telegram sentiment analysis
- **On-chain metrics**: Transazioni grandi, liquidations, funding rate changes
- **Geopolitical events**: Integrazione news geopolitiche
- **Competitor actions**: Movimenti di altri grandi trader/CTA

### 🎯 RACCOMANDAZIONI IMPLEMENTAZIONE

#### Fase 1: High Impact, Low Effort (1-2 settimane)

##### A. Extend `bot_operations` table
```sql
ALTER TABLE bot_operations ADD COLUMN IF NOT EXISTS
    model_used VARCHAR(50),
    response_time_ms INTEGER,
    fallback_reason TEXT,
    market_regime VARCHAR(20), -- 'trending', 'ranging', 'volatile'
    correlation_btc DECIMAL(5,4),
    decision_to_execution_ms INTEGER;
```

##### B. Extend `executed_trades` table
```sql
ALTER TABLE executed_trades ADD COLUMN IF NOT EXISTS
    queue_position INTEGER,
    actual_slippage_pct DECIMAL(6,4),
    liquidity_at_execution DECIMAL(20,8),
    post_execution_price DECIMAL(20,8); -- Price 1min after execution
```

##### C. New table: `market_conditions`
```sql
CREATE TABLE market_conditions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol TEXT NOT NULL,
    regime TEXT, -- trending/ranging/high_volatility
    adx_14 DECIMAL(6,2),
    correlation_btc DECIMAL(5,4),
    correlation_sp500 DECIMAL(5,4),
    bid_ask_spread_pct DECIMAL(8,6),
    orderbook_depth_usd DECIMAL(20,2),
    whale_transaction_count INTEGER,
    liquidation_long_usd DECIMAL(20,2),
    liquidation_short_usd DECIMAL(20,2)
);
```

#### Fase 2: Medium Impact, Medium Effort (2-4 settimane)

##### A. Risk Metrics Table
```sql
CREATE TABLE risk_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    portfolio_value_usd DECIMAL(20,2),
    daily_pnl_usd DECIMAL(20,2),
    max_drawdown_pct DECIMAL(6,2),
    sharpe_ratio DECIMAL(6,2),
    var_95_pct DECIMAL(6,2), -- Value at Risk 95%
    consecutive_losses INTEGER,
    total_open_positions INTEGER,
    largest_position_pct DECIMAL(5,2)
);
```

##### B. External Factors Table
```sql
CREATE TABLE external_factors (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    news_impact_score DECIMAL(3,2), -- -1 to 1
    social_sentiment_score DECIMAL(3,2), -- -1 to 1
    whale_alert_volume_usd DECIMAL(20,2),
    geopolitical_risk_index DECIMAL(3,2),
    on_chain_flow_usd DECIMAL(20,2),
    competitor_positions_change INTEGER
);
```

#### Fase 3: Advanced Analytics (4+ settimane)

##### A. Model Performance Tracking
- Accuracy per modello per condizioni di mercato
- Learning from mistakes: pattern recognition
- Model confidence calibration
- Ensemble model performance

##### B. Predictive Features
- Previsione slippage basato su condizioni
- Previsione liquidity crunch
- Market regime prediction
- Risk prediction models

### 📊 METRICHE AGGIUNTIVE DA CALCOLARE

#### 1. Decision Quality Metrics
- **Decision Accuracy**: % decisioni che portano a profitto
- **False Positive Rate**: % operazioni "open" che falliscono
- **Precision vs Recall**: Trade buoni vs trade mancati
- **Confidence Calibration**: Confidence score vs actual win rate

#### 2. Execution Quality Metrics
- **Slippage Efficiency**: Slippage effettivo vs teorico
- **Timing Efficiency**: Profitto perso per delay esecuzione
- **Market Impact**: Quanto influenzi prezzo con ordine tuo

#### 3. Risk-Adjusted Performance
- **Calmar Ratio**: Return vs Max Drawdown
- **Sortino Ratio**: Return vs Downside Deviation
- **Win Rate by Risk Level**: Performance per livello rischio assunto

### 🔍 ANALISI BACKTRACK MIGLIORATE

Con questi dati aggiuntivi, il backtrack potrebbe rispondere a:

1. **"Perché ho perso quel trade?"**
   - Condizioni di mercato al momento decisione
   - Timing dell'esecuzione
   - Qualità slippage ottenuto

2. **"Qual è il modello migliore?"**
   - Performance per modello per condizioni mercato
   - Costo vs beneficio
   - Tempi di risposta vs accuracy

3. **"Dovrei cambiare strategia?"**
   - Pattern di fallimento ricorrenti
   - Correlazione con condizioni esterne
   - Risk metrics evolution

4. **"Come ottimizzare execution?"**
   - Slippage analysis per condizioni
   - Liquidity impact
   - Timing optimization

### 💡 PROSSIMI PASSI

1. **Implementare Fase 1** entro 1-2 settimane
2. **Aggiornare backtrack_analysis.py** per usare nuovi campi
3. **Creare dashboard** per visualizzare metriche avanzate
4. **A/B testing** di diverse strategie basato su analytics
5. **Model fine-tuning** basato su pattern identificati

---

*Questo documento è generato automaticamente dall'analisi del codice esistente e identifica i gap nel tracciamento dati per ottimizzare il backtrack delle decisioni di trading.*
