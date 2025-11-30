"""
Token Tracker - Sistema di tracking consumo token LLM e costi

Traccia l'utilizzo di token per ogni chiamata LLM, calcola i costi
e fornisce statistiche aggregate per periodo, modello e scopo.
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class UsageStats:
    """Statistiche di utilizzo token"""
    total_tokens: int
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    input_cost_usd: float
    output_cost_usd: float
    api_calls_count: int
    avg_tokens_per_call: float
    avg_response_time_ms: float


class TokenTracker:
    """Traccia consumo token e costi per ogni modello LLM"""

    # Prezzi per 1M token (input/output) - aggiornati Nov 2024
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
        "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
        "deepseek-chat": {"input": 0.14, "output": 0.28},
        "deepseek-reasoner": {"input": 0.55, "output": 2.19},
        # Fallback per modelli sconosciuti
        "default": {"input": 1.00, "output": 2.00},
    }

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.session_start = datetime.now(timezone.utc)

        # In-memory fallback se database non disponibile
        self.in_memory_usage: List[Dict[str, Any]] = []
        self.db_available = self._check_db_availability()

        if not self.db_available:
            logger.warning("⚠️ Database non disponibile - usando fallback in-memory per token tracking")

    def _check_db_availability(self) -> bool:
        """Verifica se il database è disponibile"""
        if not self.db_url:
            return False

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False

    @contextmanager
    def _get_connection(self):
        """Context manager per connessione database"""
        if not self.db_url:
            raise RuntimeError("DATABASE_URL not configured")

        conn = psycopg2.connect(self.db_url)
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_table_exists(self) -> None:
        """Crea la tabella llm_usage se non esiste"""
        if not self.db_available:
            return

        schema_sql = """
        CREATE TABLE IF NOT EXISTS llm_usage (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            model VARCHAR(50) NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            input_cost_usd DECIMAL(10, 6),
            output_cost_usd DECIMAL(10, 6),
            total_cost_usd DECIMAL(10, 6),
            purpose VARCHAR(50),
            ticker VARCHAR(20),
            cycle_id VARCHAR(50),
            response_time_ms INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_llm_usage_timestamp ON llm_usage(timestamp);
        CREATE INDEX IF NOT EXISTS idx_llm_usage_model ON llm_usage(model);
        CREATE INDEX IF NOT EXISTS idx_llm_usage_purpose ON llm_usage(purpose);
        CREATE INDEX IF NOT EXISTS idx_llm_usage_cycle ON llm_usage(cycle_id);
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(schema_sql)
                conn.commit()
                logger.info("✅ Tabella llm_usage verificata/creata")
        except Exception as e:
            logger.error(f"❌ Errore creazione tabella llm_usage: {e}")
            self.db_available = False

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> tuple[float, float, float]:
        """Calcola costi input, output e totale per un modello"""
        # Normalizza nome modello per matching
        model_key = model.lower()

        # Cerca prezzo specifico o usa default
        pricing = self.PRICING.get(model_key, self.PRICING["default"])

        # Calcola costi (prezzi sono per 1M token)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        return input_cost, output_cost, total_cost

    def track_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        purpose: str = None,
        ticker: str = None,
        cycle_id: str = None,
        response_time_ms: int = None
    ) -> None:
        """
        Traccia utilizzo token per una chiamata LLM

        Args:
            model: Nome del modello (es. "gpt-4o", "deepseek-chat")
            input_tokens: Token nel prompt
            output_tokens: Token nella risposta
            purpose: Scopo della chiamata (es. "trading_decision", "market_analysis")
            ticker: Simbolo asset analizzato (es. "BTC")
            cycle_id: ID del ciclo di trading
            response_time_ms: Tempo di risposta in millisecondi
        """
        total_tokens = input_tokens + output_tokens
        input_cost, output_cost, total_cost = self._calculate_cost(model, input_tokens, output_tokens)

        usage_record = {
            "timestamp": datetime.now(timezone.utc),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": total_cost,
            "purpose": purpose,
            "ticker": ticker,
            "cycle_id": cycle_id,
            "response_time_ms": response_time_ms,
        }

        # Salva in database se disponibile
        if self.db_available:
            try:
                self._ensure_table_exists()
                self._save_to_db(usage_record)
            except Exception as e:
                logger.error(f"❌ Errore salvataggio usage in DB: {e}")
                # Fallback a in-memory
                self.in_memory_usage.append(usage_record)
        else:
            # Usa in-memory storage
            self.in_memory_usage.append(usage_record)

        # Log
        logger.info(
            f"📊 Token tracking: {model} | {total_tokens:,} tokens "
            f"(in:{input_tokens:,}, out:{output_tokens:,}) | "
            f"${total_cost:.6f} | {purpose or 'N/A'}"
        )

    def _save_to_db(self, record: Dict[str, Any]) -> None:
        """Salva record nel database"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO llm_usage (
                        timestamp, model, input_tokens, output_tokens, total_tokens,
                        input_cost_usd, output_cost_usd, total_cost_usd,
                        purpose, ticker, cycle_id, response_time_ms
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record["timestamp"],
                        record["model"],
                        record["input_tokens"],
                        record["output_tokens"],
                        record["total_tokens"],
                        record["input_cost_usd"],
                        record["output_cost_usd"],
                        record["total_cost_usd"],
                        record["purpose"],
                        record["ticker"],
                        record["cycle_id"],
                        record["response_time_ms"],
                    ),
                )
            conn.commit()

    def get_session_stats(self) -> UsageStats:
        """Statistiche dall'avvio del bot/sessione corrente"""
        if self.db_available:
            try:
                return self._get_stats_from_db(start_time=self.session_start)
            except Exception as e:
                logger.error(f"Errore lettura stats da DB: {e}")

        # Fallback a in-memory
        return self._get_stats_from_memory(self.in_memory_usage)

    def get_daily_stats(self, date: datetime = None) -> UsageStats:
        """Statistiche per un giorno specifico (default: oggi)"""
        if date is None:
            date = datetime.now(timezone.utc)

        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        if self.db_available:
            try:
                return self._get_stats_from_db(start_time=start, end_time=end)
            except Exception as e:
                logger.error(f"Errore lettura daily stats: {e}")

        # Fallback
        filtered = [r for r in self.in_memory_usage if start <= r["timestamp"] < end]
        return self._get_stats_from_memory(filtered)

    def get_monthly_stats(self, month: datetime = None) -> UsageStats:
        """Statistiche per un mese specifico (default: mese corrente)"""
        if month is None:
            month = datetime.now(timezone.utc)

        start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Calcola primo giorno del mese successivo
        if month.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        if self.db_available:
            try:
                return self._get_stats_from_db(start_time=start, end_time=end)
            except Exception as e:
                logger.error(f"Errore lettura monthly stats: {e}")

        # Fallback
        filtered = [r for r in self.in_memory_usage if start <= r["timestamp"] < end]
        return self._get_stats_from_memory(filtered)

    def get_cost_breakdown_by_model(self, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Dict[str, float]]:
        """Breakdown costi per modello"""
        if self.db_available:
            try:
                return self._get_breakdown_by_model_from_db(start_time, end_time)
            except Exception as e:
                logger.error(f"Errore breakdown by model: {e}")

        # Fallback
        filtered = self._filter_by_time(self.in_memory_usage, start_time, end_time)
        breakdown = {}
        for record in filtered:
            model = record["model"]
            if model not in breakdown:
                breakdown[model] = {"tokens": 0, "cost": 0.0, "calls": 0}

            breakdown[model]["tokens"] += record["total_tokens"]
            breakdown[model]["cost"] += record["total_cost_usd"]
            breakdown[model]["calls"] += 1

        return breakdown

    def get_cost_breakdown_by_purpose(self, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Dict[str, float]]:
        """Breakdown costi per scopo (purpose)"""
        if self.db_available:
            try:
                return self._get_breakdown_by_purpose_from_db(start_time, end_time)
            except Exception as e:
                logger.error(f"Errore breakdown by purpose: {e}")

        # Fallback
        filtered = self._filter_by_time(self.in_memory_usage, start_time, end_time)
        breakdown = {}
        for record in filtered:
            purpose = record["purpose"] or "unknown"
            if purpose not in breakdown:
                breakdown[purpose] = {"tokens": 0, "cost": 0.0, "calls": 0}

            breakdown[purpose]["tokens"] += record["total_tokens"]
            breakdown[purpose]["cost"] += record["total_cost_usd"]
            breakdown[purpose]["calls"] += 1

        return breakdown

    def get_daily_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Storico giornaliero per ultimi N giorni"""
        if self.db_available:
            try:
                return self._get_daily_history_from_db(days)
            except Exception as e:
                logger.error(f"Errore daily history: {e}")

        # Fallback
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        daily_data = {}
        for record in self.in_memory_usage:
            if start <= record["timestamp"] <= end:
                date_key = record["timestamp"].date().isoformat()
                if date_key not in daily_data:
                    daily_data[date_key] = {"tokens": 0, "cost": 0.0, "calls": 0}

                daily_data[date_key]["tokens"] += record["total_tokens"]
                daily_data[date_key]["cost"] += record["total_cost_usd"]
                daily_data[date_key]["calls"] += 1

        # Converti in lista ordinata
        return [
            {"date": date, **stats}
            for date, stats in sorted(daily_data.items())
        ]

    # ==================== METODI DATABASE ====================

    def _get_stats_from_db(self, start_time: datetime = None, end_time: datetime = None) -> UsageStats:
        """Legge statistiche dal database"""
        query = """
            SELECT
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_cost_usd), 0) as total_cost_usd,
                COALESCE(SUM(input_cost_usd), 0) as input_cost_usd,
                COALESCE(SUM(output_cost_usd), 0) as output_cost_usd,
                COUNT(*) as api_calls_count,
                COALESCE(AVG(total_tokens), 0) as avg_tokens_per_call,
                COALESCE(AVG(response_time_ms), 0) as avg_response_time_ms
            FROM llm_usage
            WHERE 1=1
        """

        params = []
        if start_time:
            query += " AND timestamp >= %s"
            params.append(start_time)
        if end_time:
            query += " AND timestamp < %s"
            params.append(end_time)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                result = cur.fetchone()

        if not result:
            return UsageStats(0, 0, 0, 0.0, 0.0, 0.0, 0, 0.0, 0.0)

        return UsageStats(
            total_tokens=int(result["total_tokens"]),
            input_tokens=int(result["input_tokens"]),
            output_tokens=int(result["output_tokens"]),
            total_cost_usd=float(result["total_cost_usd"]),
            input_cost_usd=float(result["input_cost_usd"]),
            output_cost_usd=float(result["output_cost_usd"]),
            api_calls_count=int(result["api_calls_count"]),
            avg_tokens_per_call=float(result["avg_tokens_per_call"]),
            avg_response_time_ms=float(result["avg_response_time_ms"]),
        )

    def _get_breakdown_by_model_from_db(self, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Dict[str, float]]:
        """Breakdown per modello dal database"""
        query = """
            SELECT
                model,
                SUM(total_tokens) as tokens,
                SUM(total_cost_usd) as cost,
                COUNT(*) as calls
            FROM llm_usage
            WHERE 1=1
        """

        params = []
        if start_time:
            query += " AND timestamp >= %s"
            params.append(start_time)
        if end_time:
            query += " AND timestamp < %s"
            params.append(end_time)

        query += " GROUP BY model ORDER BY cost DESC"

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                results = cur.fetchall()

        return {
            row["model"]: {
                "tokens": int(row["tokens"]),
                "cost": float(row["cost"]),
                "calls": int(row["calls"]),
            }
            for row in results
        }

    def _get_breakdown_by_purpose_from_db(self, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Dict[str, float]]:
        """Breakdown per purpose dal database"""
        query = """
            SELECT
                COALESCE(purpose, 'unknown') as purpose,
                SUM(total_tokens) as tokens,
                SUM(total_cost_usd) as cost,
                COUNT(*) as calls
            FROM llm_usage
            WHERE 1=1
        """

        params = []
        if start_time:
            query += " AND timestamp >= %s"
            params.append(start_time)
        if end_time:
            query += " AND timestamp < %s"
            params.append(end_time)

        query += " GROUP BY purpose ORDER BY cost DESC"

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                results = cur.fetchall()

        return {
            row["purpose"]: {
                "tokens": int(row["tokens"]),
                "cost": float(row["cost"]),
                "calls": int(row["calls"]),
            }
            for row in results
        }

    def _get_daily_history_from_db(self, days: int) -> List[Dict[str, Any]]:
        """Storico giornaliero dal database"""
        query = """
            SELECT
                DATE(timestamp) as date,
                SUM(total_tokens) as tokens,
                SUM(total_cost_usd) as cost,
                COUNT(*) as calls
            FROM llm_usage
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
        """

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (days,))
                results = cur.fetchall()

        return [
            {
                "date": row["date"].isoformat(),
                "tokens": int(row["tokens"]),
                "cost": float(row["cost"]),
                "calls": int(row["calls"]),
            }
            for row in results
        ]

    # ==================== METODI UTILITY ====================

    def _get_stats_from_memory(self, records: List[Dict[str, Any]]) -> UsageStats:
        """Calcola statistiche da lista in-memory"""
        if not records:
            return UsageStats(0, 0, 0, 0.0, 0.0, 0.0, 0, 0.0, 0.0)

        total_tokens = sum(r["total_tokens"] for r in records)
        input_tokens = sum(r["input_tokens"] for r in records)
        output_tokens = sum(r["output_tokens"] for r in records)
        total_cost = sum(r["total_cost_usd"] for r in records)
        input_cost = sum(r["input_cost_usd"] for r in records)
        output_cost = sum(r["output_cost_usd"] for r in records)
        calls = len(records)

        response_times = [r["response_time_ms"] for r in records if r.get("response_time_ms")]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

        return UsageStats(
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=total_cost,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            api_calls_count=calls,
            avg_tokens_per_call=total_tokens / calls if calls > 0 else 0.0,
            avg_response_time_ms=avg_response_time,
        )

    def _filter_by_time(
        self,
        records: List[Dict[str, Any]],
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[Dict[str, Any]]:
        """Filtra records per time range"""
        filtered = records

        if start_time:
            filtered = [r for r in filtered if r["timestamp"] >= start_time]
        if end_time:
            filtered = [r for r in filtered if r["timestamp"] < end_time]

        return filtered


# ==================== SINGLETON GLOBALE ====================

_tracker_instance: Optional[TokenTracker] = None


def get_token_tracker() -> TokenTracker:
    """Ottieni istanza singleton del TokenTracker"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = TokenTracker()
    return _tracker_instance


# ==================== STANDALONE TEST ====================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    tracker = get_token_tracker()

    # Test tracking
    print("\n=== TEST TOKEN TRACKING ===\n")

    tracker.track_usage(
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        purpose="trading_decision",
        ticker="BTC",
        response_time_ms=1200
    )

    tracker.track_usage(
        model="deepseek-chat",
        input_tokens=2000,
        output_tokens=800,
        purpose="market_analysis",
        ticker="ETH",
        response_time_ms=850
    )

    # Test stats
    print("\n=== SESSION STATS ===")
    stats = tracker.get_session_stats()
    print(f"Total tokens: {stats.total_tokens:,}")
    print(f"Total cost: ${stats.total_cost_usd:.6f}")
    print(f"API calls: {stats.api_calls_count}")

    print("\n=== BREAKDOWN BY MODEL ===")
    breakdown = tracker.get_cost_breakdown_by_model()
    for model, data in breakdown.items():
        print(f"{model}: {data['tokens']:,} tokens, ${data['cost']:.6f}, {data['calls']} calls")

    print("\n=== BREAKDOWN BY PURPOSE ===")
    breakdown = tracker.get_cost_breakdown_by_purpose()
    for purpose, data in breakdown.items():
        print(f"{purpose}: {data['tokens']:,} tokens, ${data['cost']:.6f}, {data['calls']} calls")

    print("\n✅ Test completato!")
