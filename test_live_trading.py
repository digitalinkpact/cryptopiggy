#!/usr/bin/env python3
"""
Test script to validate live trading setup in the Streamlit app.
Run this to check if live trading prerequisites are met.
"""
import os
import sys

def check_live_trading_config():
    """Check live trading configuration."""
    print("🔍 Checking Live Trading Configuration...\n")
    
    # Check environment variables
    print("1. Environment Variables:")
    allow_live = os.getenv('ALLOW_LIVE')
    print(f"   ALLOW_LIVE: {allow_live} {'✅' if allow_live == '1' else '❌ (needs to be 1)'}")
    
    exchange = os.getenv('EXCHANGE', 'paper')
    print(f"   EXCHANGE: {exchange}")
    
    api_key = os.getenv('EXCHANGE_API_KEY') or os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('EXCHANGE_API_SECRET') or os.getenv('BINANCE_API_SECRET')
    print(f"   API_KEY: {'✅ Set' if api_key else '❌ Not set'}")
    print(f"   API_SECRET: {'✅ Set' if api_secret else '❌ Not set'}")
    
    confirm_token = os.getenv('LIVE_CONFIRM_TOKEN')
    print(f"   LIVE_CONFIRM_TOKEN: {'✅ Set' if confirm_token else '⚠️  Not set (will require manual confirmation)'}")
    
    allowed_symbols = os.getenv('ALLOWED_SYMBOLS', 'BTC/USDT,ETH/USDT')
    print(f"   ALLOWED_SYMBOLS: {allowed_symbols}")
    
    # Try to initialize bot
    print("\n2. Bot Initialization:")
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        print(f"   ✅ Bot created successfully")
        print(f"   paper_mode: {bot.paper_mode}")
        print(f"   live_confirmed: {bot.live_confirmed}")
        print(f"   _allow_live_env: {bot._allow_live_env}")
        
        # Try exchange setup
        bot.setup_exchange()
        print(f"   exchange: {'✅ Initialized' if bot.exchange else '❌ Not initialized'}")
        
        # Check is_live() method
        is_live = bot.is_live()
        print(f"   is_live(): {is_live} {'✅' if is_live else '⚠️  (expected for initial state)'}")
        
        print("\n3. Live Trading Readiness:")
        if not bot._allow_live_env:
            print("   ❌ Set ALLOW_LIVE=1 environment variable")
        if not api_key or not api_secret:
            print("   ❌ Configure exchange API keys")
        if bot.exchange is None:
            print("   ❌ Exchange not initialized (check ccxt installation)")
        if bot._allow_live_env and api_key and api_secret and bot.exchange:
            print("   ✅ All prerequisites met! Live trading can be enabled in the UI.")
            print("   ⚠️  Remember to enable it through the Streamlit checkbox with proper confirmation.")
        
    except ImportError as e:
        print(f"   ❌ Failed to import: {e}")
        print("   Install dependencies: pip install -r requirements.txt")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("To enable live trading:")
    print("1. Set ALLOW_LIVE=1")
    print("2. Configure EXCHANGE, EXCHANGE_API_KEY, EXCHANGE_API_SECRET")
    print("3. Optional: Set LIVE_CONFIRM_TOKEN for additional safety")
    print("4. Start Streamlit app: streamlit run app.py")
    print("5. Check the 'Live mode' checkbox in the Controls section")
    print("6. Confirm the prompt to enable live trading")
    print("="*60)

if __name__ == "__main__":
    check_live_trading_config()
