"""
Prometheus Metrics per monitoring
"""
import logging
from typing import Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Raccolta metriche per Prometheus"""

    def __init__(self, port: int = 8000):
        self.port = port
        self.enabled = PROMETHEUS_AVAILABLE

        if not self.enabled:
            logger.warning("⚠️ prometheus_client non installato, metriche disabilitate")
            return

        # Contatori
        self.trades_total = Counter(
            'trading_trades_total',
            'Totale trade eseguiti',
            ['operation', 'symbol', 'direction', 'result']
        )

        self.errors_total = Counter(
            'trading_errors_total',
            'Totale errori',
            ['type', 'source']
        )

        # Gauge
        self.balance = Gauge(
            'trading_balance_usd',
            'Balance corrente in USD'
        )

        self.daily_pnl = Gauge(
            'trading_daily_pnl_usd',
            'P&L giornaliero in USD'
        )

        self.open_positions = Gauge(
            'trading_open_positions',
            'Numero posizioni aperte'
        )

        self.circuit_breaker = Gauge(
            'trading_circuit_breaker_active',
            'Circuit breaker attivo (1) o no (0)'
        )

        # Histogram
        self.cycle_duration = Histogram(
            'trading_cycle_duration_seconds',
            'Durata ciclo di trading',
            buckets=[1, 5, 10, 30, 60, 120, 300]
        )

        self.api_latency = Histogram(
            'trading_api_latency_seconds',
            'Latenza chiamate API',
            ['service'],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
        )

    def start_server(self) -> None:
        """Avvia server HTTP per Prometheus"""
        if not self.enabled:
            return

        try:
            start_http_server(self.port)
            logger.info(f"✅ Prometheus metrics server su porta {self.port}")
        except Exception as e:
            logger.error(f"❌ Errore avvio metrics server: {e}")

    def record_trade(
        self,
        operation: str,
        symbol: str,
        direction: str,
        result: str
    ) -> None:
        """Registra un trade"""
        if self.enabled:
            self.trades_total.labels(
                operation=operation,
                symbol=symbol,
                direction=direction,
                result=result
            ).inc()

    def record_error(self, error_type: str, source: str) -> None:
        """Registra un errore"""
        if self.enabled:
            self.errors_total.labels(type=error_type, source=source).inc()

    def update_balance(self, value: float) -> None:
        """Aggiorna balance"""
        if self.enabled:
            self.balance.set(value)

    def update_daily_pnl(self, value: float) -> None:
        """Aggiorna P&L giornaliero"""
        if self.enabled:
            self.daily_pnl.set(value)

    def update_positions(self, count: int) -> None:
        """Aggiorna numero posizioni"""
        if self.enabled:
            self.open_positions.set(count)

    def set_circuit_breaker(self, active: bool) -> None:
        """Imposta stato circuit breaker"""
        if self.enabled:
            self.circuit_breaker.set(1 if active else 0)


# Istanza globale
metrics = MetricsCollector()
