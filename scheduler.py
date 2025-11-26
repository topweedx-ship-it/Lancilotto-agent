"""
Trading Scheduler - Esecuzione continua con APScheduler
"""
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED

logger = logging.getLogger(__name__)


class TradingScheduler:
    """
    Scheduler per il trading bot con:
    - Esecuzione ciclica configurabile
    - Health checks periodici
    - Graceful shutdown
    - Error recovery
    """

    def __init__(
        self,
        trading_func: Callable,
        interval_minutes: int = 3,
        health_check_func: Optional[Callable] = None
    ):
        self.trading_func = trading_func
        self.interval_minutes = interval_minutes
        self.health_check_func = health_check_func

        self.scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,  # Combina job persi
                'max_instances': 1,  # Mai più di 1 istanza
                'misfire_grace_time': 60  # Grazia di 60s per job mancati
            }
        )

        self.is_running = False
        self.cycle_count = 0
        self.last_success: Optional[datetime] = None
        self.last_error: Optional[str] = None

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def start(self) -> None:
        """Avvia lo scheduler"""

        logger.info(f"🚀 Avvio Trading Scheduler (intervallo: {self.interval_minutes} min)")

        # Job principale di trading
        self.scheduler.add_job(
            self._trading_wrapper,
            IntervalTrigger(minutes=self.interval_minutes),
            id='trading_cycle',
            name='Trading Cycle',
            replace_existing=True
        )

        # Job di health check (ogni 5 minuti)
        if self.health_check_func:
            self.scheduler.add_job(
                self._health_check_wrapper,
                IntervalTrigger(minutes=5),
                id='health_check',
                name='Health Check',
                replace_existing=True
            )

        # Event listeners
        self.scheduler.add_listener(
            self._job_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

        # Avvia
        self.scheduler.start()
        self.is_running = True

        logger.info("✅ Scheduler avviato con successo")

        # Esegui subito il primo ciclo
        logger.info("▶️ Esecuzione primo ciclo immediato...")
        self._trading_wrapper()

        # Keep alive loop
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _trading_wrapper(self) -> None:
        """Wrapper per il ciclo di trading con error handling"""
        self.cycle_count += 1
        start_time = datetime.now(timezone.utc)

        logger.info(f"\n{'='*60}")
        logger.info(f"📊 CICLO TRADING #{self.cycle_count} - {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"{'='*60}")

        try:
            self.trading_func()
            self.last_success = datetime.now(timezone.utc)
            self.last_error = None

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"✅ Ciclo #{self.cycle_count} completato in {duration:.1f}s")

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ Ciclo #{self.cycle_count} fallito: {e}", exc_info=True)

    def _health_check_wrapper(self) -> None:
        """Wrapper per health check"""
        try:
            if self.health_check_func:
                self.health_check_func()
        except Exception as e:
            logger.warning(f"⚠️ Health check fallito: {e}")

    def _job_listener(self, event) -> None:
        """Listener per eventi dei job"""
        if event.exception:
            logger.error(f"❌ Job {event.job_id} fallito con eccezione")
        elif hasattr(event, 'job_id'):
            if 'missed' in str(type(event)).lower():
                logger.warning(f"⚠️ Job {event.job_id} mancato")

    def _handle_shutdown(self, signum, frame) -> None:
        """Handler per shutdown graceful"""
        logger.info(f"🛑 Segnale di shutdown ricevuto ({signum})")
        self.stop()

    def stop(self) -> None:
        """Ferma lo scheduler in modo graceful"""
        if not self.is_running:
            return

        logger.info("🛑 Arresto scheduler in corso...")
        self.is_running = False

        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

        logger.info("✅ Scheduler arrestato")
        sys.exit(0)

    def get_status(self) -> dict:
        """Ritorna lo stato dello scheduler"""
        return {
            "running": self.is_running,
            "cycle_count": self.cycle_count,
            "interval_minutes": self.interval_minutes,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "next_run": str(self.scheduler.get_job('trading_cycle').next_run_time)
                       if self.scheduler.get_job('trading_cycle') else None
        }
