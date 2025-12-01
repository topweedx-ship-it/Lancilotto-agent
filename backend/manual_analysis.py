import logging
import sys
import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("manual_analysis")

# Load environment
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_engine import bot_state, CONFIG, WALLET_ADDRESS
from indicators import analyze_multiple_tickers
from news_feed import fetch_latest_news
from trading_agent import previsione_trading_agent
from sentiment import get_sentiment
from forecaster import get_crypto_forecasts
from hyperliquid_trader import HyperLiquidTrader
from risk_manager import RiskManager, RiskConfig

def run_analysis(symbol: str):
    """Run a single analysis cycle for a specific symbol"""
    logger.info(f"🚀 Starting manual analysis for {symbol}")
    
    # Initialize
    if not bot_state.initialize():
        logger.error("❌ Initialization failed")
        return

    # 1. Fetch Market Data
    logger.info("📡 Fetching market data...")
    try:
        indicators_txt, indicators_json = analyze_multiple_tickers([symbol], testnet=CONFIG["TESTNET"])
    except Exception as e:
        logger.error(f"❌ Error fetching indicators: {e}")
        return

    # Other data (simplified for manual run)
    logger.info("Fetching news...")
    news_txt = fetch_latest_news()
    
    logger.info("Fetching sentiment...")
    sentiment_txt, sentiment_json = get_sentiment()
    
    logger.info("Fetching forecasts...")
    forecasts_txt, forecasts_json = get_crypto_forecasts(tickers=[symbol], testnet=CONFIG["TESTNET"])
    
    # 2. Build Prompt
    msg_info = f"""<indicatori>
{indicators_txt}
</indicatori>

<news>
{news_txt}
</news>

<sentiment>
{sentiment_txt}
</sentiment>

<forecast>
{forecasts_txt}
</forecast>"""

    # Account status (mock or real)
    account_status = bot_state.trader.get_account_status()
    portfolio_data = json.dumps(account_status, indent=2)
    
    with open('system_prompt.txt', 'r') as f:
        system_prompt_template = f.read()
    
    system_prompt = system_prompt_template.format(portfolio_data, msg_info)
    
    # 3. AI Decision
    logger.info("🤖 Requesting AI decision...")
    try:
        decision = previsione_trading_agent(system_prompt, cycle_id=f"manual_{datetime.now().strftime('%H%M%S')}")
    except Exception as e:
        logger.error(f"❌ Error from AI agent: {e}")
        return
    
    logger.info(f"🎯 AI Decision: {json.dumps(decision, indent=2)}")
    
    # 4. Trend Check
    if CONFIG["TREND_CONFIRMATION_ENABLED"] and bot_state.trend_engine and decision.get("operation") != "hold":
        logger.info(f"🔍 Running trend confirmation for {symbol}...")
        confirmation = bot_state.trend_engine.confirm_trend(symbol=symbol)
        logger.info(f"📊 Trend Confirmation: {confirmation}")
        
        trend_ok = True
        if not confirmation.should_trade:
            logger.warning("⛔ Trend check FAILED: insufficient quality")
            trend_ok = False
        elif CONFIG["SKIP_POOR_ENTRY"] and confirmation.entry_quality == "wait":
            logger.warning("⏳ Trend check WAIT: poor entry timing")
            trend_ok = False
        else:
            logger.info("✅ Trend check PASSED")
            
        if trend_ok:
             logger.info(f"✨ READY TO EXECUTE: {decision['operation']} {symbol} {decision['direction']}")
        else:
             logger.info("🚫 TRADE BLOCKED by trend check")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_analysis.py <SYMBOL>")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    run_analysis(symbol)
