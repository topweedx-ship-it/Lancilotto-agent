import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
import math

from db_utils import get_connection

logger = logging.getLogger(__name__)

def sync_trades_from_hyperliquid(trader):
    """
    Fetches user fills from Hyperliquid and synchronizes with executed_trades table.
    Handles both closing existing open trades and inserting missing historical trades.
    """
    if not trader:
        logger.warning("Trader instance not available for sync")
        return

    try:
        # Fetch last 100 fills
        fills = trader.get_user_fills()
        if not fills:
            return

        # Sort by time ascending
        fills.sort(key=lambda x: x["time"])

        with get_connection() as conn:
            with conn.cursor() as cur:
                for fill in fills:
                    _process_fill(cur, fill)
            conn.commit()
            
    except Exception as e:
        logger.error(f"Error syncing trades: {e}")

def _process_fill(cur, fill: Dict[str, Any]):
    """
    Process a single fill and update/insert into DB.
    """
    # Fill structure example:
    # {'closedPnl': '0.0', 'coin': 'HYPE', 'crossed': True, 'dir': 'Open Long', 
    #  'fee': '0.0031', 'feeToken': 'USDC', 'hash': '0x...', 'oid': 123, 
    #  'px': '12.34', 'side': 'B', 'startPosition': '0.0', 'sz': '10.0', 'time': 1700000000000}

    coin = fill.get("coin")
    direction_str = fill.get("dir", "") # "Open Long", "Close Short", etc.
    
    # Parse direction and action
    parts = direction_str.split(" ")
    if len(parts) < 2:
        # Fallback logic if dir format is different
        return

    action = parts[0].lower() # "open" or "close"
    direction = parts[1].lower() # "long" or "short"
    
    fill_time = datetime.fromtimestamp(fill["time"] / 1000.0, tz=timezone.utc)
    px = float(fill["px"])
    sz = float(fill["sz"])
    pnl = float(fill.get("closedPnl", 0))
    fee = float(fill.get("fee", 0))
    oid = str(fill.get("oid"))

    if action == "open":
        # Check if this trade already exists (deduplication by hl_order_id or approximate match)
        cur.execute(
            """
            SELECT id FROM executed_trades 
            WHERE hl_order_id = %s OR (symbol = %s AND ABS(EXTRACT(EPOCH FROM created_at) * 1000 - %s) < 5000)
            """,
            (oid, coin, fill["time"])
        )
        if cur.fetchone():
            return # Already exists

        # Insert new open trade (historical/missed)
        # Note: size_usd is approx px * sz
        cur.execute(
            """
            INSERT INTO executed_trades (
                trade_type, symbol, direction, size, entry_price, 
                leverage, hl_order_id, hl_fill_price, size_usd, 
                status, created_at, fees_usd
            ) VALUES (
                'open', %s, %s, %s, %s, 
                1, %s, %s, %s, 
                'open', %s, %s
            )
            """,
            (coin, direction, sz, px, oid, px, px * sz, fill_time, fee)
        )

    elif action == "close":
        # Look for an open trade to close
        # Match by symbol and direction (Close Long closes a Long position)
        # We look for the most recent open position for this symbol
        cur.execute(
            """
            SELECT id, entry_price, size FROM executed_trades
            WHERE symbol = %s AND direction = %s AND status = 'open'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (coin, direction)
        )
        row = cur.fetchone()
        
        if row:
            # Close existing trade
            trade_id, entry_price, open_size = row
            # If sizes match roughly, close fully. If not, it's partial or complex.
            # For simplicity, we close the trade found.
            
            # Calculate PnL %
            pnl_pct = 0
            if entry_price:
                if direction == "long":
                    pnl_pct = ((px - float(entry_price)) / float(entry_price)) * 100
                else:
                    pnl_pct = ((float(entry_price) - px) / float(entry_price)) * 100

            cur.execute(
                """
                UPDATE executed_trades
                SET status = 'closed',
                    exit_price = %s,
                    exit_reason = 'synced_fill',
                    pnl_usd = %s,
                    pnl_pct = %s,
                    closed_at = %s,
                    fees_usd = COALESCE(fees_usd, 0) + %s,
                    duration_minutes = EXTRACT(EPOCH FROM (%s - created_at)) / 60
                WHERE id = %s
                """,
                (px, pnl, pnl_pct, fill_time, fee, fill_time, trade_id)
            )
        else:
            # We found a CLOSE but no corresponding OPEN in DB.
            # This is a "Zombie" close or manual trade. 
            # We should insert a closed record to keep history complete.
            # Reconstruct entry price from PnL:
            # PnL = (Exit - Entry) * Size (Long)
            # Entry = Exit - (PnL / Size) (Long)
            # Short: PnL = (Entry - Exit) * Size => Entry = (PnL / Size) + Exit
            
            reconstructed_entry = px
            if sz > 0:
                if direction == "long":
                    reconstructed_entry = px - (pnl / sz)
                else:
                    reconstructed_entry = (pnl / sz) + px
            
            # Check if this specific close already exists? 
            # We don't have hl_close_order_id column. 
            # We use timestamp and symbol to dedup closed trades.
            cur.execute(
                """
                SELECT id FROM executed_trades 
                WHERE symbol = %s AND status = 'closed' AND ABS(EXTRACT(EPOCH FROM closed_at) * 1000 - %s) < 5000
                """,
                (coin, fill["time"])
            )
            if cur.fetchone():
                return # Already processed

            # Insert fully closed trade
            # We estimate created_at as fill_time - 1 minute if unknown
            cur.execute(
                """
                INSERT INTO executed_trades (
                    trade_type, symbol, direction, size, entry_price, 
                    exit_price, pnl_usd, pnl_pct,
                    leverage, hl_order_id, hl_fill_price, size_usd, 
                    status, created_at, closed_at, fees_usd, exit_reason
                ) VALUES (
                    'close', %s, %s, %s, %s,
                    %s, %s, 0, 
                    1, %s, %s, %s,
                    'closed', %s - INTERVAL '1 hour', %s, %s, 'synced_history'
                )
                """,
                (coin, direction, sz, reconstructed_entry, px, pnl, oid, px, px * sz, fill_time, fill_time, fee)
            )

