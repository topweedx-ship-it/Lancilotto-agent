"""
Sistema di notifiche Telegram
"""
import os
import logging
import requests
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class TelegramNotifier:
    """Gestisce le notifiche Telegram"""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

        if not self.enabled:
            logger.warning("⚠️ Telegram notifier non configurato (mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)")

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """Invia messaggio Telegram"""
        if not self.enabled:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            response = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": parse_mode
                },
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"❌ Errore invio Telegram: {e}")
            return False

    def notify_trade_opened(
        self,
        symbol: str,
        direction: str,
        size_usd: float,
        leverage: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ) -> None:
        """Notifica apertura trade"""
        emoji = "🟢" if direction == "long" else "🔴"
        msg = f"""{emoji} <b>TRADE APERTO</b>

<b>Asset:</b> {symbol}
<b>Direzione:</b> {direction.upper()}
<b>Size:</b> ${size_usd:.2f}
<b>Leva:</b> {leverage}x
<b>Entry:</b> ${entry_price:.2f}
<b>Stop Loss:</b> ${stop_loss:.2f}
<b>Take Profit:</b> ${take_profit:.2f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        self.send(msg)

    def notify_trade_closed(
        self,
        symbol: str,
        direction: str,
        pnl: float,
        pnl_pct: float,
        reason: str
    ) -> None:
        """Notifica chiusura trade"""
        emoji = "✅" if pnl >= 0 else "❌"
        msg = f"""{emoji} <b>TRADE CHIUSO</b>

<b>Asset:</b> {symbol}
<b>Direzione:</b> {direction.upper()}
<b>P&L:</b> ${pnl:+.2f} ({pnl_pct:+.2f}%)
<b>Motivo:</b> {reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        self.send(msg)

    def notify_circuit_breaker(self, daily_loss: float, reason: str) -> None:
        """Notifica attivazione circuit breaker"""
        msg = f"""🚨 <b>CIRCUIT BREAKER ATTIVATO</b>

<b>Perdita giornaliera:</b> ${abs(daily_loss):.2f}
<b>Motivo:</b> {reason}

Il bot non aprirà nuove posizioni fino a domani.

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        self.send(msg)

    def notify_daily_summary(
        self,
        balance: float,
        daily_pnl: float,
        trades_count: int,
        win_rate: float
    ) -> None:
        """Notifica riepilogo giornaliero"""
        emoji = "📈" if daily_pnl >= 0 else "📉"
        msg = f"""{emoji} <b>RIEPILOGO GIORNALIERO</b>

<b>Balance:</b> ${balance:.2f}
<b>P&L Oggi:</b> ${daily_pnl:+.2f}
<b>Trade:</b> {trades_count}
<b>Win Rate:</b> {win_rate:.1%}

⏰ {datetime.now().strftime('%Y-%m-%d')}"""
        self.send(msg)

    def notify_error(self, error_type: str, error_msg: str) -> None:
        """Notifica errore critico"""
        msg = f"""⚠️ <b>ERRORE</b>

<b>Tipo:</b> {error_type}
<b>Messaggio:</b> {error_msg[:200]}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        self.send(msg)


# Istanza globale
notifier = TelegramNotifier()
