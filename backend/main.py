from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from model_manager import get_model_manager
from db_utils import get_connection
from token_tracker import get_token_tracker
from notifications import notifier
import threading
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Trading Agent API")

# Configure CORS middleware BEFORE routes (best practice)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Trading Agent API is running"}


# Schemi per le API dei modelli
class ModelInfo(BaseModel):
    id: str
    name: str
    model_id: str
    provider: str
    available: bool
    supports_json_schema: bool
    supports_reasoning: bool


# Endpoint per i modelli
@app.get("/api/models", response_model=List[ModelInfo])
async def get_available_models():
    """Restituisce la lista dei modelli disponibili"""
    model_manager = get_model_manager()
    return model_manager.get_available_models()


@app.get("/api/models/current")
async def get_current_model():
    """
    Restituisce il modello corrente.
    Nota: Il modello viene configurato solo tramite variabile d'ambiente DEFAULT_AI_MODEL.
    Non è possibile modificarlo tramite API.
    """
    model_manager = get_model_manager()
    current_model_key = model_manager.get_current_model()
    model_config = model_manager.get_model_config(current_model_key)
    
    if not model_config:
        raise HTTPException(status_code=500, detail="Modello corrente non trovato")
    
    return {
        "id": current_model_key,
        "name": model_config.name,
        "model_id": model_config.model_id,
        "provider": model_config.provider.value,
        "available": model_manager.is_model_available(current_model_key)
    }


# =====================
# Modelli di risposta API per dashboard
# =====================

class BalancePoint(BaseModel):
    timestamp: datetime
    balance_usd: float


class OpenPosition(BaseModel):
    id: int
    snapshot_id: int
    symbol: str
    side: str
    size: float
    entry_price: Optional[float]
    mark_price: Optional[float]
    pnl_usd: Optional[float]
    leverage: Optional[str]
    snapshot_created_at: datetime


class BotOperation(BaseModel):
    id: int
    created_at: datetime
    operation: str
    symbol: Optional[str]
    direction: Optional[str]
    target_portion_of_balance: Optional[float]
    leverage: Optional[float]
    raw_payload: Any
    system_prompt: Optional[str]


class ExecutedTrade(BaseModel):
    id: int
    created_at: datetime
    bot_operation_id: Optional[int]
    trade_type: str
    symbol: str
    direction: str
    entry_price: Optional[float]
    exit_price: Optional[float]
    size: float
    size_usd: Optional[float]
    leverage: Optional[int]
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    exit_reason: Optional[str]
    pnl_usd: Optional[float]
    pnl_pct: Optional[float]
    duration_minutes: Optional[int]
    status: str
    closed_at: Optional[datetime]
    fees_usd: Optional[float]


class TradeStatistics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    best_trade: float
    worst_trade: float
    avg_duration_minutes: Optional[float]
    total_fees: float


# =====================
# Endpoint API Dashboard
# =====================

@app.get("/api/balance", response_model=List[BalancePoint])
async def get_balance() -> List[BalancePoint]:
    """Restituisce TUTTA la storia del saldo (balance_usd) ordinata nel tempo.
    
    I dati sono presi dalla tabella `account_snapshots`.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT created_at, balance_usd
                    FROM account_snapshots
                    ORDER BY created_at ASC;
                    """
                )
                rows = cur.fetchall()
        
        return [
            BalancePoint(timestamp=row[0], balance_usd=float(row[1]))
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero del saldo: {str(e)}")


@app.get("/api/open-positions", response_model=List[OpenPosition])
async def get_open_positions() -> List[OpenPosition]:
    """Restituisce le posizioni aperte dell'ULTIMO snapshot disponibile.
    
    - Prende l'ultimo record da `account_snapshots`.
    - Recupera le posizioni corrispondenti da `open_positions`.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Ultimo snapshot
                cur.execute(
                    """
                    SELECT id, created_at
                    FROM account_snapshots
                    ORDER BY created_at DESC
                    LIMIT 1;
                    """
                )
                row = cur.fetchone()
                if not row:
                    logger.warning("⚠️ Nessuno snapshot trovato in account_snapshots")
                    return []
                snapshot_id = row[0]
                snapshot_created_at = row[1]
                
                logger.info(f"🔍 Fetching positions for snapshot {snapshot_id} (created {snapshot_created_at})")

                # Posizioni aperte per quello snapshot
                cur.execute(
                    """
                    SELECT
                        id,
                        snapshot_id,
                        symbol,
                        side,
                        size,
                        entry_price,
                        mark_price,
                        pnl_usd,
                        leverage
                    FROM open_positions
                    WHERE snapshot_id = %s
                    ORDER BY symbol ASC, id ASC;
                    """,
                    (snapshot_id,),
                )
                rows = cur.fetchall()
                logger.info(f"✅ Trovate {len(rows)} posizioni per snapshot {snapshot_id}")
        
        return [
            OpenPosition(
                id=row[0],
                snapshot_id=row[1],
                symbol=row[2],
                side=row[3],
                size=float(row[4]),
                entry_price=float(row[5]) if row[5] is not None else None,
                mark_price=float(row[6]) if row[6] is not None else None,
                pnl_usd=float(row[7]) if row[7] is not None else None,
                leverage=row[8],
                snapshot_created_at=snapshot_created_at,
            )
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero delle posizioni: {str(e)}")


@app.get("/api/bot-operations", response_model=List[BotOperation])
async def get_bot_operations(
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Numero massimo di operazioni da restituire (default 50)",
    ),
) -> List[BotOperation]:
    """Restituisce le ULTIME `limit` operazioni del bot con il full system prompt.
    
    - I dati provengono da `bot_operations` uniti a `ai_contexts`.
    - Ordinati da più recente a meno recente.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        bo.id,
                        bo.created_at,
                        bo.operation,
                        bo.symbol,
                        bo.direction,
                        bo.target_portion_of_balance,
                        bo.leverage,
                        bo.raw_payload,
                        ac.system_prompt
                    FROM bot_operations AS bo
                    LEFT JOIN ai_contexts AS ac ON bo.context_id = ac.id
                    ORDER BY bo.created_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
        
        operations: List[BotOperation] = []
        for row in rows:
            operations.append(
                BotOperation(
                    id=row[0],
                    created_at=row[1],
                    operation=row[2],
                    symbol=row[3],
                    direction=row[4],
                    target_portion_of_balance=float(row[5]) if row[5] is not None else None,
                    leverage=float(row[6]) if row[6] is not None else None,
                    raw_payload=row[7],
                    system_prompt=row[8],
                )
            )
        
        return operations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero delle operazioni: {str(e)}")


# =====================
# Trade History API Endpoints
# =====================

@app.get("/api/trades", response_model=List[ExecutedTrade])
async def get_trades(
    page: int = Query(1, ge=1, description="Numero di pagina (1-based)"),
    limit: int = Query(50, ge=1, le=500, description="Numero di trades per pagina"),
    symbol: Optional[str] = Query(None, description="Filtra per symbol (es. BTC, ETH)"),
    direction: Optional[str] = Query(None, description="Filtra per direction (long/short)"),
    status: Optional[str] = Query(None, description="Filtra per status (open/closed/cancelled)"),
    date_from: Optional[str] = Query(None, description="Data inizio (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data fine (YYYY-MM-DD)"),
) -> List[ExecutedTrade]:
    """
    Restituisce la lista dei trades eseguiti con filtri e paginazione.

    Filtri disponibili:
    - symbol: Filtra per simbolo specifico
    - direction: Filtra per direzione (long/short)
    - status: Filtra per stato (open/closed/cancelled)
    - date_from: Data inizio (formato YYYY-MM-DD)
    - date_to: Data fine (formato YYYY-MM-DD)

    Paginazione:
    - page: Numero di pagina (default: 1)
    - limit: Numero di risultati per pagina (default: 50, max: 500)
    """
    try:
        # Costruisci query con filtri
        offset = (page - 1) * limit

        query = """
            SELECT
                id, created_at, bot_operation_id, trade_type, symbol, direction,
                entry_price, exit_price, size, size_usd, leverage,
                stop_loss_price, take_profit_price, exit_reason,
                pnl_usd, pnl_pct, duration_minutes, status, closed_at, fees_usd
            FROM executed_trades
            WHERE 1=1
        """
        params = []

        # Aggiungi filtri
        if symbol:
            query += " AND symbol = %s"
            params.append(symbol)

        if direction:
            query += " AND direction = %s"
            params.append(direction)

        if status:
            query += " AND status = %s"
            params.append(status)

        if date_from:
            query += " AND created_at >= %s::date"
            params.append(date_from)

        if date_to:
            query += " AND created_at < (%s::date + interval '1 day')"
            params.append(date_to)

        # Ordina per data (più recenti prima) e aggiungi paginazione
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        trades = []
        for row in rows:
            trades.append(
                ExecutedTrade(
                    id=row[0],
                    created_at=row[1],
                    bot_operation_id=row[2],
                    trade_type=row[3],
                    symbol=row[4],
                    direction=row[5],
                    entry_price=float(row[6]) if row[6] is not None else None,
                    exit_price=float(row[7]) if row[7] is not None else None,
                    size=float(row[8]),
                    size_usd=float(row[9]) if row[9] is not None else None,
                    leverage=row[10],
                    stop_loss_price=float(row[11]) if row[11] is not None else None,
                    take_profit_price=float(row[12]) if row[12] is not None else None,
                    exit_reason=row[13],
                    pnl_usd=float(row[14]) if row[14] is not None else None,
                    pnl_pct=float(row[15]) if row[15] is not None else None,
                    duration_minutes=row[16],
                    status=row[17],
                    closed_at=row[18],
                    fees_usd=float(row[19]) if row[19] is not None else None,
                )
            )

        return trades

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero dei trades: {str(e)}")


@app.get("/api/trades/stats", response_model=TradeStatistics)
async def get_trade_stats(
    symbol: Optional[str] = Query(None, description="Filtra per symbol (es. BTC, ETH)"),
    days: int = Query(30, ge=1, le=365, description="Numero di giorni da includere"),
) -> TradeStatistics:
    """
    Restituisce statistiche aggregate sui trades.

    Parametri:
    - symbol: Calcola statistiche per un simbolo specifico (opzionale)
    - days: Numero di giorni da includere nell'analisi (default: 30)

    Ritorna:
    - total_trades: Numero totale di trades
    - winning_trades: Numero di trades profittevoli
    - losing_trades: Numero di trades in perdita
    - win_rate: Percentuale di trades vincenti
    - total_pnl: P&L totale in USD
    - avg_pnl: P&L medio per trade
    - best_trade: Miglior trade (P&L più alto)
    - worst_trade: Peggior trade (P&L più basso)
    - avg_duration_minutes: Durata media dei trades
    - total_fees: Fees totali pagate
    """
    try:
        query = """
            SELECT
                COUNT(*) as total_trades,
                COUNT(*) FILTER (WHERE pnl_usd > 0) as winning_trades,
                COUNT(*) FILTER (WHERE pnl_usd < 0) as losing_trades,
                ROUND(100.0 * COUNT(*) FILTER (WHERE pnl_usd > 0) / NULLIF(COUNT(*), 0), 2) as win_rate,
                COALESCE(SUM(pnl_usd), 0) as total_pnl,
                COALESCE(AVG(pnl_usd), 0) as avg_pnl,
                COALESCE(MAX(pnl_usd), 0) as best_trade,
                COALESCE(MIN(pnl_usd), 0) as worst_trade,
                AVG(duration_minutes) as avg_duration_minutes,
                COALESCE(SUM(fees_usd), 0) as total_fees
            FROM executed_trades
            WHERE status = 'closed'
                AND pnl_usd IS NOT NULL
                AND created_at >= NOW() - INTERVAL '%s days'
        """
        params = [days]

        if symbol:
            query += " AND symbol = %s"
            params.append(symbol)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()

        if not row or row[0] == 0:
            # Nessun trade trovato, ritorna statistiche vuote
            return TradeStatistics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                avg_pnl=0.0,
                best_trade=0.0,
                worst_trade=0.0,
                avg_duration_minutes=None,
                total_fees=0.0,
            )

        return TradeStatistics(
            total_trades=row[0],
            winning_trades=row[1],
            losing_trades=row[2],
            win_rate=float(row[3]) if row[3] is not None else 0.0,
            total_pnl=float(row[4]),
            avg_pnl=float(row[5]),
            best_trade=float(row[6]),
            worst_trade=float(row[7]),
            avg_duration_minutes=float(row[8]) if row[8] is not None else None,
            total_fees=float(row[9]),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero delle statistiche: {str(e)}")


@app.get("/api/trades/{trade_id}", response_model=ExecutedTrade)
async def get_trade_by_id(trade_id: int) -> ExecutedTrade:
    """
    Restituisce i dettagli di un singolo trade.

    Parametri:
    - trade_id: ID del trade da recuperare

    Ritorna:
    - Dettagli completi del trade
    """
    try:
        query = """
            SELECT
                id, created_at, bot_operation_id, trade_type, symbol, direction,
                entry_price, exit_price, size, size_usd, leverage,
                stop_loss_price, take_profit_price, exit_reason,
                pnl_usd, pnl_pct, duration_minutes, status, closed_at, fees_usd
            FROM executed_trades
            WHERE id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (trade_id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Trade con ID {trade_id} non trovato")

        return ExecutedTrade(
            id=row[0],
            created_at=row[1],
            bot_operation_id=row[2],
            trade_type=row[3],
            symbol=row[4],
            direction=row[5],
            entry_price=float(row[6]) if row[6] is not None else None,
            exit_price=float(row[7]) if row[7] is not None else None,
            size=float(row[8]),
            size_usd=float(row[9]) if row[9] is not None else None,
            leverage=row[10],
            stop_loss_price=float(row[11]) if row[11] is not None else None,
            take_profit_price=float(row[12]) if row[12] is not None else None,
            exit_reason=row[13],
            pnl_usd=float(row[14]) if row[14] is not None else None,
            pnl_pct=float(row[15]) if row[15] is not None else None,
            duration_minutes=row[16],
            status=row[17],
            closed_at=row[18],
            fees_usd=float(row[19]) if row[19] is not None else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero del trade: {str(e)}")


# =====================
# Token Usage API Endpoints
# =====================

@app.get("/api/token-usage")
async def get_token_usage(period: str = Query("today", description="Period: today, session, week, month, all")):
    """
    Restituisce statistiche utilizzo token LLM per periodo specificato

    Args:
        period: "today", "session", "week", "month", "all"

    Returns:
        Statistiche dettagliate con breakdown per modello e purpose
    """
    try:
        tracker = get_token_tracker()

        # Determina periodo
        if period == "session":
            stats = tracker.get_session_stats()
            start_time = tracker.session_start
            end_time = None
        elif period == "today":
            stats = tracker.get_daily_stats()
            now = datetime.now()
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = None
        elif period == "week":
            from datetime import timedelta, timezone
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)
            stats = tracker._get_stats_from_db(start_time=start_time, end_time=end_time) if tracker.db_available else tracker._get_stats_from_memory([])
        elif period == "month":
            stats = tracker.get_monthly_stats()
            now = datetime.now()
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = None
        elif period == "all":
            stats = tracker._get_stats_from_db() if tracker.db_available else tracker._get_stats_from_memory(tracker.in_memory_usage)
            start_time = None
            end_time = None
        else:
            raise HTTPException(status_code=400, detail="Invalid period. Use: today, session, week, month, all")

        # Ottieni breakdown
        breakdown_by_model = tracker.get_cost_breakdown_by_model(start_time=start_time, end_time=end_time)
        breakdown_by_purpose = tracker.get_cost_breakdown_by_purpose(start_time=start_time, end_time=end_time)

        return {
            "period": period,
            "total_tokens": stats.total_tokens,
            "input_tokens": stats.input_tokens,
            "output_tokens": stats.output_tokens,
            "total_cost_usd": float(stats.total_cost_usd),
            "input_cost_usd": float(stats.input_cost_usd),
            "output_cost_usd": float(stats.output_cost_usd),
            "api_calls_count": stats.api_calls_count,
            "avg_tokens_per_call": float(stats.avg_tokens_per_call),
            "avg_response_time_ms": float(stats.avg_response_time_ms),
            "breakdown_by_model": breakdown_by_model,
            "breakdown_by_purpose": breakdown_by_purpose,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero token usage: {str(e)}")


@app.get("/api/token-usage/history")
async def get_token_history(days: int = Query(30, ge=1, le=365, description="Numero di giorni da includere")):
    """
    Restituisce storico giornaliero utilizzo token per grafici

    Args:
        days: Numero di giorni (1-365)

    Returns:
        Array di {date, tokens, cost, calls} per ogni giorno
    """
    try:
        tracker = get_token_tracker()
        history = tracker.get_daily_history(days=days)

        return {
            "days": days,
            "data": history
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero storico: {str(e)}")


from collections import deque
from market_data.aggregator import MarketDataAggregator

# =====================
# Market Data API Endpoints
# =====================

# Singleton aggregator instance
_market_data_aggregator = None

def get_market_aggregator():
    global _market_data_aggregator
    if _market_data_aggregator is None:
        _market_data_aggregator = MarketDataAggregator()
    return _market_data_aggregator

@app.get("/api/market-data/aggregate")
async def get_market_data_aggregate(symbol: str = "BTC"):
    """
    Restituisce dati di mercato aggregati per un symbol specifico.
    """
    try:
        aggregator = get_market_aggregator()
        snapshot = await aggregator.fetch_market_snapshot(symbol)
        return snapshot
    except Exception as e:
        logger.error(f"Errore nel recupero market data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


# =====================
# Coin Screener API Endpoints
# =====================

@app.get("/api/screener/latest")
async def get_latest_screener_result():
    """
    Restituisce l'ultimo risultato dello screening delle coin.
    """
    try:
        from coin_screener.db_utils import get_latest_screening
        with get_connection() as conn:
            result = get_latest_screening(conn)
        if not result:
            return {"selected_coins": [], "message": "Nessun dato di screening disponibile"}
        return result
    except Exception as e:
        logger.error(f"Errore nel recupero screening results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


# =====================
# System Configuration API Endpoints
# =====================

@app.get("/api/config")
async def get_system_config():
    """
    Restituisce la configurazione del sistema (cicli, Coin Screener, ecc.)
    """
    try:
        # Import qui per evitare import circolari
        from trading_engine import CONFIG
        from sentiment import INTERVALLO_SECONDI
        
        return {
            "trading": {
                "testnet": CONFIG.get("TESTNET", True),
                "tickers": CONFIG.get("TICKERS", []),
                "cycle_interval_minutes": CONFIG.get("CYCLE_INTERVAL_MINUTES", 5)
            },
            "cycles": {
                "trading_cycle_minutes": CONFIG.get("CYCLE_INTERVAL_MINUTES", 5),
                "sentiment_api_minutes": INTERVALLO_SECONDI // 60,
                "health_check_minutes": 5
            },
            "coin_screener": {
                "enabled": CONFIG.get("SCREENING_ENABLED", False),
                "top_n_coins": CONFIG.get("TOP_N_COINS", 5),
                "rebalance_day": CONFIG.get("REBALANCE_DAY", "sunday"),
                "fallback_tickers": CONFIG.get("FALLBACK_TICKERS", [])
            },
            "trend_confirmation": {
                "enabled": CONFIG.get("TREND_CONFIRMATION_ENABLED", False),
                "min_confidence": CONFIG.get("MIN_TREND_CONFIDENCE", 0.6)
            },
            "risk_management": {
                "max_daily_loss_usd": CONFIG.get("MAX_DAILY_LOSS_USD", 500.0),
                "max_daily_loss_pct": CONFIG.get("MAX_DAILY_LOSS_PCT", 5.0),
                "max_position_pct": CONFIG.get("MAX_POSITION_PCT", 30.0),
                "default_stop_loss_pct": CONFIG.get("DEFAULT_STOP_LOSS_PCT", 2.0),
                "default_take_profit_pct": CONFIG.get("DEFAULT_TAKE_PROFIT_PCT", 5.0)
            }
        }
    except Exception as e:
        logger.error(f"Errore nel recupero configurazione: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


# =====================
# System Logs API Endpoints
# =====================

@app.get("/api/system-logs")
async def get_system_logs(lines: int = Query(100, ge=1, le=1000)):
    """
    Restituisce le ultime N righe del file di log di sistema.
    """
    log_file = "trading_agent.log"
    try:
        if not os.path.exists(log_file):
             return {"logs": [], "message": "Log file not found"}
        
        with open(log_file, "r", encoding="utf-8") as f:
            # Leggi le ultime N righe usando deque
            last_lines = deque(f, maxlen=lines)
            return {"logs": list(last_lines)}
    except Exception as e:
        logger.error(f"Errore nella lettura dei log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")


# Mount static files for frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.on_event("startup")
def on_startup():
    """Initialize services on startup"""
    print("Trading Agent API started")
    
    # Avvia trading engine in background thread
    try:
        # Import qui per evitare import circolari
        from trading_engine import bot_state, CONFIG, WALLET_ADDRESS, TradingScheduler, trading_cycle, health_check
        
        def start_trading_engine():
            """Avvia il trading engine in un thread separato"""
            try:
                logger.info("🚀 Avvio Trading Engine in background...")
                
                # Inizializza
                if not bot_state.initialize():
                    logger.error("❌ Inizializzazione trading engine fallita")
                    return
                
                # Invia notifica di avvio via Telegram
                try:
                    if notifier.enabled:
                        logger.info("📤 Invio notifica di avvio via Telegram...")
                        notifier.notify_startup(
                            testnet=CONFIG["TESTNET"],
                            tickers=CONFIG["TICKERS"],
                            cycle_interval_minutes=CONFIG["CYCLE_INTERVAL_MINUTES"],
                            wallet_address=WALLET_ADDRESS,
                            screening_enabled=CONFIG.get("SCREENING_ENABLED", False),
                            top_n_coins=CONFIG.get("TOP_N_COINS", 5),
                            rebalance_day=CONFIG.get("REBALANCE_DAY", "sunday"),
                            sentiment_interval_minutes=5,  # Da sentiment.py INTERVALLO_SECONDI / 60
                            health_check_interval_minutes=5  # Da scheduler.py
                        )
                        logger.info("✅ Notifica di avvio inviata via Telegram")
                    else:
                        logger.warning("⚠️ Telegram notifier non configurato (mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)")
                except Exception as e:
                    logger.error(f"❌ Errore nell'invio notifica Telegram: {e}", exc_info=True)
                
                # Avvia thread per aggiornamento frequente account status (ogni 30s)
                def start_account_updater():
                    """Aggiorna lo stato dell'account ogni 30 secondi"""
                    import time
                    import db_utils
                    from services.history_sync import sync_trades_from_hyperliquid
                    
                    # Attendi inizializzazione
                    while not bot_state.initialized:
                        time.sleep(1)
                    
                    logger.info("🔄 Avvio loop aggiornamento account status (30s)...")
                    while True:
                        try:
                            if bot_state.trader:
                                account_status = bot_state.trader.get_account_status()
                                db_utils.log_account_status(account_status)
                                
                                # Sync trades history from Hyperliquid
                                sync_trades_from_hyperliquid(bot_state.trader)
                                
                                # logger.debug("✅ Account status e history aggiornati (background)")
                        except Exception as e:
                            logger.warning(f"⚠️ Errore aggiornamento account status: {e}")
                        
                        time.sleep(30) # Aggiorna ogni 30 secondi
                
                updater_thread = threading.Thread(target=start_account_updater, daemon=True)
                updater_thread.start()
                logger.info("✅ Account Updater thread avviato")
                
                # Avvia scheduler (bloccante)
                scheduler = TradingScheduler(
                    trading_func=trading_cycle,
                    interval_minutes=CONFIG["CYCLE_INTERVAL_MINUTES"],
                    health_check_func=health_check
                )
                
                scheduler.start()
                
            except Exception as e:
                logger.error(f"❌ Errore nell'avvio trading engine: {e}", exc_info=True)
        
        # Avvia in thread separato (daemon=True per terminare con il processo principale)
        trading_thread = threading.Thread(target=start_trading_engine, daemon=True)
        trading_thread.start()
        logger.info("✅ Trading Engine thread avviato")
        
    except ImportError as e:
        logger.warning(f"⚠️ Impossibile importare trading_engine: {e}")
        logger.warning("⚠️ Trading engine non avviato. Avvia manualmente con: python trading_engine.py")
    except Exception as e:
        logger.error(f"❌ Errore nell'avvio trading engine: {e}", exc_info=True)


@app.on_event("shutdown")
def on_shutdown():
    """Cleanup on shutdown"""
    print("Trading Agent API shutting down")
    # TODO: Cleanup services


# Serve frontend index.html for root and SPA routes
@app.get("/")
async def serve_root():
    """Serve the frontend index.html for root route"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")

    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "Frontend not built yet"}

# Catch-all route for SPA routing (must be last)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the frontend index.html for SPA routes that don't match API/static"""
    # Skip API and static routes
    if full_path.startswith("api") or full_path.startswith("static") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")

    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "Frontend not built yet"}
