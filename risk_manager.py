"""
Risk Manager - Gestione Stop-Loss, Take-Profit e Circuit Breaker
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import logging
import threading
import time

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """Configurazione parametri di rischio"""
    max_daily_loss_pct: float = 5.0          # Max perdita giornaliera %
    max_daily_loss_usd: float = 500.0        # Max perdita giornaliera USD
    max_position_pct: float = 30.0           # Max % balance per posizione
    max_total_exposure_pct: float = 60.0     # Max esposizione totale
    default_stop_loss_pct: float = 2.0       # Stop-loss default
    default_take_profit_pct: float = 5.0     # Take-profit default
    min_rr_ratio: float = 1.5                # Minimo Risk:Reward ratio
    max_consecutive_losses: int = 3          # Max perdite consecutive
    cooldown_after_losses_minutes: int = 30  # Cooldown dopo max perdite


@dataclass
class Position:
    """Rappresenta una posizione aperta"""
    symbol: str
    direction: str  # "long" o "short"
    entry_price: float
    size: float
    leverage: int
    stop_loss_price: float
    take_profit_price: float
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def stop_loss_pct(self) -> float:
        """Calcola SL% dal prezzo di entry"""
        if self.direction == "long":
            return ((self.entry_price - self.stop_loss_price) / self.entry_price) * 100
        else:
            return ((self.stop_loss_price - self.entry_price) / self.entry_price) * 100

    @property
    def take_profit_pct(self) -> float:
        """Calcola TP% dal prezzo di entry"""
        if self.direction == "long":
            return ((self.take_profit_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.take_profit_price) / self.entry_price) * 100

    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        """
        Verifica se le condizioni di uscita sono soddisfatte.

        Returns:
            "stop_loss", "take_profit", o None
        """
        if self.direction == "long":
            if current_price <= self.stop_loss_price:
                return "stop_loss"
            if current_price >= self.take_profit_price:
                return "take_profit"
        else:  # short
            if current_price >= self.stop_loss_price:
                return "stop_loss"
            if current_price <= self.take_profit_price:
                return "take_profit"
        return None

    def calculate_pnl(self, current_price: float) -> float:
        """Calcola P&L corrente in USD"""
        if self.direction == "long":
            pnl_per_unit = current_price - self.entry_price
        else:
            pnl_per_unit = self.entry_price - current_price

        return pnl_per_unit * self.size


class RiskManager:
    """
    Gestisce il rischio del portfolio con:
    - Stop-Loss / Take-Profit monitoring
    - Circuit breaker giornaliero
    - Position sizing
    - Cooldown dopo perdite consecutive
    """

    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
        self.positions: Dict[str, Position] = {}
        self.daily_pnl: float = 0.0
        self.daily_reset_time: datetime = datetime.now(timezone.utc)
        self.consecutive_losses: int = 0
        self.last_loss_time: Optional[datetime] = None
        self.is_circuit_breaker_active: bool = False
        self._lock = threading.Lock()

    def _reset_daily_stats_if_needed(self) -> None:
        """Reset statistiche giornaliere a mezzanotte UTC"""
        now = datetime.now(timezone.utc)
        if now.date() > self.daily_reset_time.date():
            logger.info("🔄 Reset statistiche giornaliere")
            self.daily_pnl = 0.0
            self.daily_reset_time = now
            self.is_circuit_breaker_active = False

    def can_open_position(self, balance_usd: float) -> Dict[str, Any]:
        """
        Verifica se è possibile aprire una nuova posizione.

        Returns:
            Dict con "allowed" (bool) e "reason" (str)
        """
        with self._lock:
            self._reset_daily_stats_if_needed()

            # 1. Controlla circuit breaker
            if self.is_circuit_breaker_active:
                return {
                    "allowed": False,
                    "reason": f"Circuit breaker attivo. Perdita giornaliera: ${abs(self.daily_pnl):.2f}"
                }

            # 2. Controlla perdita giornaliera
            if abs(self.daily_pnl) >= self.config.max_daily_loss_usd:
                self.is_circuit_breaker_active = True
                return {
                    "allowed": False,
                    "reason": f"Max perdita giornaliera raggiunta: ${abs(self.daily_pnl):.2f}"
                }

            daily_loss_pct = (abs(self.daily_pnl) / balance_usd) * 100 if balance_usd > 0 else 0
            if daily_loss_pct >= self.config.max_daily_loss_pct:
                self.is_circuit_breaker_active = True
                return {
                    "allowed": False,
                    "reason": f"Max perdita giornaliera %: {daily_loss_pct:.1f}%"
                }

            # 3. Controlla cooldown dopo perdite consecutive
            if self.consecutive_losses >= self.config.max_consecutive_losses:
                if self.last_loss_time:
                    cooldown_end = self.last_loss_time + timedelta(
                        minutes=self.config.cooldown_after_losses_minutes
                    )
                    if datetime.now(timezone.utc) < cooldown_end:
                        remaining = (cooldown_end - datetime.now(timezone.utc)).seconds // 60
                        return {
                            "allowed": False,
                            "reason": f"Cooldown attivo dopo {self.consecutive_losses} perdite. {remaining} min rimanenti."
                        }
                    else:
                        # Cooldown terminato, reset
                        self.consecutive_losses = 0

            return {"allowed": True, "reason": "OK"}

    def calculate_position_size(
        self,
        balance_usd: float,
        requested_portion: float,
        stop_loss_pct: float,
        leverage: int = 1
    ) -> Dict[str, float]:
        """
        Calcola la dimensione della posizione con risk management.

        Usa Fixed Fractional: rischia max 1-2% del capitale per trade.

        Returns:
            Dict con "size_usd", "effective_portion", "risk_usd"
        """
        # Max 2% del capitale a rischio per trade
        max_risk_per_trade = 0.02
        risk_amount = balance_usd * max_risk_per_trade

        # Position size basato su risk amount e stop loss
        if stop_loss_pct > 0:
            position_size_from_risk = (risk_amount / stop_loss_pct) * 100
        else:
            position_size_from_risk = balance_usd * requested_portion

        # Applica limiti
        max_position = balance_usd * (self.config.max_position_pct / 100)
        requested_size = balance_usd * requested_portion

        # Prendi il minimo tra: richiesto, calcolato da risk, e max consentito
        final_size = min(requested_size, position_size_from_risk, max_position)

        effective_portion = final_size / balance_usd if balance_usd > 0 else 0

        logger.info(
            f"📊 Position sizing: Richiesto={requested_portion:.1%}, "
            f"Risk-based={position_size_from_risk:.2f}, "
            f"Finale={final_size:.2f} ({effective_portion:.1%})"
        )

        return {
            "size_usd": final_size,
            "effective_portion": effective_portion,
            "risk_usd": risk_amount
        }

    def register_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        size: float,
        leverage: int,
        stop_loss_pct: float,
        take_profit_pct: float
    ) -> Position:
        """Registra una nuova posizione per il monitoring"""

        # Calcola prezzi SL/TP
        if direction == "long":
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
            take_profit_price = entry_price * (1 + take_profit_pct / 100)
        else:
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
            take_profit_price = entry_price * (1 - take_profit_pct / 100)

        position = Position(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            size=size,
            leverage=leverage,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price
        )

        with self._lock:
            self.positions[symbol] = position

        logger.info(
            f"📍 Posizione registrata: {symbol} {direction} @ {entry_price:.2f}, "
            f"SL={stop_loss_price:.2f}, TP={take_profit_price:.2f}"
        )

        return position

    def check_positions(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Controlla tutte le posizioni per SL/TP.

        Args:
            current_prices: Dict {symbol: price}

        Returns:
            Lista di posizioni da chiudere con motivo
        """
        to_close = []

        with self._lock:
            for symbol, position in self.positions.items():
                if symbol not in current_prices:
                    continue

                current_price = current_prices[symbol]
                exit_reason = position.check_exit_conditions(current_price)

                if exit_reason:
                    pnl = position.calculate_pnl(current_price)
                    to_close.append({
                        "symbol": symbol,
                        "direction": position.direction,
                        "reason": exit_reason,
                        "entry_price": position.entry_price,
                        "exit_price": current_price,
                        "pnl": pnl,
                        "position": position
                    })

                    logger.warning(
                        f"⚠️ {exit_reason.upper()}: {symbol} @ {current_price:.2f} "
                        f"(entry: {position.entry_price:.2f}, PnL: ${pnl:.2f})"
                    )

        return to_close

    def record_trade_result(self, pnl: float, was_stop_loss: bool = False) -> None:
        """Registra il risultato di un trade chiuso"""

        with self._lock:
            self.daily_pnl += pnl

            if pnl < 0:
                self.consecutive_losses += 1
                self.last_loss_time = datetime.now(timezone.utc)
                logger.warning(
                    f"📉 Perdita registrata: ${pnl:.2f} "
                    f"(consecutive: {self.consecutive_losses}, daily: ${self.daily_pnl:.2f})"
                )
            else:
                self.consecutive_losses = 0
                logger.info(f"📈 Profitto registrato: ${pnl:.2f} (daily: ${self.daily_pnl:.2f})")

    def remove_position(self, symbol: str) -> None:
        """Rimuove una posizione dal tracking"""
        with self._lock:
            if symbol in self.positions:
                del self.positions[symbol]
                logger.info(f"🗑️ Posizione {symbol} rimossa dal tracking")

    def get_status(self) -> Dict[str, Any]:
        """Ritorna lo stato corrente del risk manager"""
        with self._lock:
            return {
                "daily_pnl": self.daily_pnl,
                "consecutive_losses": self.consecutive_losses,
                "circuit_breaker_active": self.is_circuit_breaker_active,
                "open_positions": len(self.positions),
                "positions": {
                    s: {
                        "direction": p.direction,
                        "entry": p.entry_price,
                        "sl": p.stop_loss_price,
                        "tp": p.take_profit_price
                    }
                    for s, p in self.positions.items()
                }
            }
