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
                    return []
                snapshot_id = row[0]
                snapshot_created_at = row[1]
                
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
                            wallet_address=WALLET_ADDRESS
                        )
                        logger.info("✅ Notifica di avvio inviata via Telegram")
                    else:
                        logger.warning("⚠️ Telegram notifier non configurato (mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)")
                except Exception as e:
                    logger.error(f"❌ Errore nell'invio notifica Telegram: {e}", exc_info=True)
                
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
