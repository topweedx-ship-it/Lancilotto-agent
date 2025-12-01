"""
Database utilities for coin screener
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from psycopg2.extras import Json

logger = logging.getLogger(__name__)


def log_screening_result(conn, result: 'CoinScreenerResult') -> int:
    """
    Log a screening result to the database.

    Args:
        conn: psycopg2 connection
        result: CoinScreenerResult object

    Returns:
        ID of the created screening record
    """
    with conn.cursor() as cur:
        # Insert main screening record
        cur.execute(
            """
            INSERT INTO coin_screenings (
                screening_type,
                selected_coins,
                excluded_coins,
                raw_scores,
                next_rebalance
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                result.screening_type,
                Json([coin.to_dict() for coin in result.selected_coins]),
                Json(result.excluded_coins),
                Json([coin.to_dict() for coin in result.selected_coins]),
                result.next_rebalance
            )
        )
        screening_id = cur.fetchone()[0]

        # Insert individual coin scores
        for coin in result.selected_coins:
            cur.execute(
                """
            INSERT INTO coin_scores_history (
                screening_id,
                symbol,
                score,
                rank,
                factors,
                metrics
            )
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (
                screening_id,
                coin.symbol,
                float(coin.score) if coin.score is not None else 0.0,
                coin.rank,
                Json(coin.factors),
                Json(coin.metrics)
            )
        )

    conn.commit()
    logger.info(f"Logged screening result (ID: {screening_id})")
    return screening_id


def log_coin_metrics(conn, metrics: 'CoinMetrics'):
    """
    Log coin metrics snapshot to database.

    Args:
        conn: psycopg2 connection
        metrics: CoinMetrics object
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO coin_metrics_snapshots (
                symbol,
                price,
                volume_24h_usd,
                market_cap_usd,
                open_interest_usd,
                funding_rate,
                spread_pct,
                days_listed,
                raw_data
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                metrics.symbol,
                metrics.price,
                metrics.volume_24h_usd,
                metrics.market_cap_usd,
                metrics.open_interest_usd,
                metrics.funding_rate,
                metrics.spread_pct,
                metrics.days_listed,
                Json(metrics.to_dict())
            )
        )
    conn.commit()


def get_latest_screening(conn) -> Optional[Dict[str, Any]]:
    """
    Get the most recent screening result.

    Args:
        conn: psycopg2 connection

    Returns:
        Dict with screening data or None
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, created_at, screening_type, selected_coins,
                   excluded_coins, next_rebalance
            FROM coin_screenings
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "created_at": row[1],
            "screening_type": row[2],
            "selected_coins": row[3],
            "excluded_coins": row[4],
            "next_rebalance": row[5]
        }


def get_coin_score_history(
    conn,
    symbol: str,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    Get historical scores for a specific coin.

    Args:
        conn: psycopg2 connection
        symbol: Coin symbol
        limit: Number of records to return

    Returns:
        List of score records
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT created_at, score, rank, factors, metrics
            FROM coin_scores_history
            WHERE symbol = %s
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (symbol, limit)
        )

        return [
            {
                "created_at": row[0],
                "score": float(row[1]) if row[1] else None,
                "rank": row[2],
                "factors": row[3],
                "metrics": row[4]
            }
            for row in cur.fetchall()
        ]


def get_screening_stats(conn) -> Dict[str, Any]:
    """
    Get statistics about screenings.

    Args:
        conn: psycopg2 connection

    Returns:
        Dict with stats
    """
    with conn.cursor() as cur:
        # Total screenings
        cur.execute("SELECT COUNT(*) FROM coin_screenings;")
        total_screenings = cur.fetchone()[0]

        # Latest screening
        cur.execute(
            """
            SELECT created_at, screening_type
            FROM coin_screenings
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        latest = cur.fetchone()

        # Most frequently selected coins
        cur.execute(
            """
            SELECT symbol, COUNT(*) as selections
            FROM coin_scores_history
            WHERE rank <= 5
            GROUP BY symbol
            ORDER BY selections DESC
            LIMIT 10;
            """
        )
        top_coins = [{"symbol": row[0], "selections": row[1]} for row in cur.fetchall()]

        return {
            "total_screenings": total_screenings,
            "latest_screening_time": latest[0] if latest else None,
            "latest_screening_type": latest[1] if latest else None,
            "top_selected_coins": top_coins
        }
