#!/usr/bin/env python3
"""
Script di test per verificare se le notifiche Telegram funzionano
"""
import os
from dotenv import load_dotenv
from notifications import notifier

load_dotenv()

print("=" * 60)
print("TEST NOTIFICA TELEGRAM")
print("=" * 60)

# Verifica configurazione
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print(f"\n📋 Configurazione:")
print(f"   TELEGRAM_BOT_TOKEN: {'✅ Presente' if token else '❌ Mancante'}")
if token:
    print(f"   Token: {token[:20]}...")
print(f"   TELEGRAM_CHAT_ID: {'✅ Presente' if chat_id else '❌ Mancante'}")
if chat_id:
    print(f"   Chat ID: {chat_id}")

print(f"\n🔧 Notifier enabled: {notifier.enabled}")

if not notifier.enabled:
    print("\n❌ Notifier non abilitato!")
    print("   Verifica che TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID siano nel .env")
    exit(1)

# Test invio messaggio semplice
print("\n📤 Invio messaggio di test...")
result = notifier.send("🧪 Test notifica Telegram - Se vedi questo messaggio, funziona!")

if result:
    print("✅ Messaggio inviato con successo!")
else:
    print("❌ Fallito invio messaggio")

# Test notifica di avvio
print("\n📤 Invio notifica di avvio...")
try:
    notifier.notify_startup(
        testnet=True,
        tickers=["BTC", "ETH", "SOL"],
        cycle_interval_minutes=3,
        wallet_address="0x1234567890123456789012345678901234567890"
    )
    print("✅ Notifica di avvio inviata!")
except Exception as e:
    print(f"❌ Errore: {e}")

print("\n" + "=" * 60)
print("Test completato!")
print("=" * 60)





