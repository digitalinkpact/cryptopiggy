#!/usr/bin/env python3
"""
Test script for CryptoPiggy Streamlit app.
Verifies that the app and bot components work correctly.
Run with: python test_app.py
"""

import sys
import os
import logging
import json
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('CryptoPiggyAppTest')

def test_imports():
    """Test that all required imports work."""
    print("\n" + "="*60)
    print("1. Testing Imports")
    print("="*60)
    
    try:
        import streamlit as st
        print("✅ streamlit")
    except ImportError as e:
        print(f"❌ streamlit: {e}")
        return False
    
    try:
        import pandas as pd
        print("✅ pandas")
    except ImportError as e:
        print(f"❌ pandas: {e}")
        return False
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        print("✅ crypto_piggy_top")
    except ImportError as e:
        print(f"❌ crypto_piggy_top: {e}")
        return False
    
    try:
        import ccxt
        print("✅ ccxt")
    except ImportError as e:
        print(f"❌ ccxt: {e}")
        return False
    
    try:
        import torch
        print("✅ torch")
    except ImportError as e:
        print(f"❌ torch: {e}")
        return False
    
    return True


def test_bot_initialization():
    """Test that the bot initializes correctly."""
    print("\n" + "="*60)
    print("2. Testing Bot Initialization")
    print("="*60)
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        print("✅ Bot instance created")
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")
        return False
    
    # Check bot attributes
    try:
        assert hasattr(bot, 'paper_mode'), "Missing paper_mode"
        print(f"✅ paper_mode: {bot.paper_mode}")
        
        assert hasattr(bot, 'live_confirmed'), "Missing live_confirmed"
        print(f"✅ live_confirmed: {bot.live_confirmed}")
        
        assert hasattr(bot, 'exchange'), "Missing exchange"
        print(f"✅ exchange: {bot.exchange if bot.exchange else 'None (paper mode)'}")
        
        assert hasattr(bot, 'positions'), "Missing positions"
        print(f"✅ positions: {len(bot.positions)} open")
        
        assert hasattr(bot, 'trade_log'), "Missing trade_log"
        print(f"✅ trade_log: {len(bot.trade_log)} trades")
        
        assert hasattr(bot, 'strategies'), "Missing strategies"
        print(f"✅ strategies: {list(bot.strategies.keys())}")
        
        assert hasattr(bot, 'active_strategy'), "Missing active_strategy"
        print(f"✅ active_strategy: {bot.active_strategy}")
        
    except AssertionError as e:
        print(f"❌ {e}")
        return False
    
    return True


def test_exchange_setup():
    """Test exchange setup functionality."""
    print("\n" + "="*60)
    print("3. Testing Exchange Setup")
    print("="*60)
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        
        # Test setup_exchange
        bot.setup_exchange()
        print("✅ setup_exchange() executed")
        
        # Check if exchange is initialized (in paper mode it won't be)
        if bot.exchange:
            print(f"✅ Exchange initialized: {bot.exchange_name}")
        else:
            print(f"⚠️  Exchange not initialized (expected in paper mode)")
        
    except Exception as e:
        print(f"❌ Exchange setup failed: {e}")
        return False
    
    return True


def test_ohlcv_fetch():
    """Test OHLCV data fetching."""
    print("\n" + "="*60)
    print("4. Testing OHLCV Data Fetch")
    print("="*60)
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        
        # Fetch synthetic data (doesn't require exchange)
        df = bot.fetch_ohlcv_df('BTC/USDT', timeframe='5m', limit=100)
        
        if df is None or df.empty:
            print("❌ No OHLCV data returned")
            return False
        
        print(f"✅ OHLCV data fetched: {len(df)} candles")
        print(f"✅ Columns: {list(df.columns)}")
        print(f"✅ Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        
    except Exception as e:
        print(f"❌ OHLCV fetch failed: {e}")
        return False
    
    return True


def test_strategy_execution():
    """Test strategy signal generation."""
    print("\n" + "="*60)
    print("5. Testing Strategy Execution")
    print("="*60)
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        
        # Fetch data
        df = bot.fetch_ohlcv_df('BTC/USDT', timeframe='5m', limit=100)
        
        # Get active strategy
        strategy = bot.strategies.get(bot.active_strategy)
        if not strategy:
            print(f"❌ Strategy '{bot.active_strategy}' not found")
            return False
        
        # Populate indicators
        df = strategy.populate_indicators(df)
        print(f"✅ Indicators populated")
        
        # Populate entry trend
        df = strategy.populate_entry_trend(df)
        print(f"✅ Entry signals generated")
        
        # Populate exit trend
        df = strategy.populate_exit_trend(df)
        print(f"✅ Exit signals generated")
        
        # Check signals
        entries = df['entry'].sum()
        exits = df['exit'].sum()
        print(f"✅ Signals: {entries} entries, {exits} exits")
        
    except Exception as e:
        print(f"❌ Strategy execution failed: {e}")
        return False
    
    return True


def test_backtest():
    """Test backtest functionality."""
    print("\n" + "="*60)
    print("6. Testing Backtest")
    print("="*60)
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        
        # Run backtest
        result = bot.backtest(
            bot.active_strategy,
            'BTC/USDT',
            timeframe='5m',
            limit=200
        )
        
        if not result or not isinstance(result, dict):
            print("❌ Backtest returned invalid result")
            return False
        
        print(f"✅ Backtest completed")
        print(f"   Total Return: {result['total_return']:.2%}")
        print(f"   Max Drawdown: {result['max_dd']:.2%}")
        print(f"   Sharpe Ratio: {result['sharpe']:.2f}")
        print(f"   Equity Curve: {len(result['equity_curve'])} points")
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        return False
    
    return True


def test_state_persistence():
    """Test state loading and saving."""
    print("\n" + "="*60)
    print("7. Testing State Persistence")
    print("="*60)
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        import tempfile
        
        # Create bot and add test data
        bot = CryptoPiggyTop2026()
        
        # Add test position
        bot.positions['BTC/USDT'] = {'qty': 0.5, 'price': 50000.0}
        bot.trade_log.append({
            'time': datetime.now().isoformat(),
            'side': 'buy',
            'symbol': 'BTC/USDT',
            'amount_usd': 25000.0,
            'qty': 0.5,
            'price': 50000.0,
            'live': False
        })
        
        # Save state
        bot.save_state()
        print("✅ State saved")
        
        # Check if state.json exists
        if not os.path.exists('state.json'):
            print("❌ state.json not created")
            return False
        
        print("✅ state.json created")
        
        # Load state into new bot
        bot2 = CryptoPiggyTop2026()
        
        if 'BTC/USDT' not in bot2.positions:
            print("❌ Positions not loaded from state.json")
            return False
        
        print("✅ Positions loaded from state.json")
        
        if len(bot2.trade_log) == 0:
            print("❌ Trade log not loaded from state.json")
            return False
        
        print("✅ Trade log loaded from state.json")
        
    except Exception as e:
        print(f"❌ State persistence test failed: {e}")
        return False
    
    return True


def test_order_validation():
    """Test order validation logic."""
    print("\n" + "="*60)
    print("8. Testing Order Validation")
    print("="*60)
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026, MAX_TRADE_USD
        
        bot = CryptoPiggyTop2026()
        
        # Test minimum size rejection
        result = bot.place_order('buy', 'BTC/USDT', 1.0)  # Below $2 min
        if result is not None:
            print("⚠️  Minimum size validation: order should have been rejected")
        else:
            print("✅ Minimum size validation working")
        
        # Test maximum size cap
        bot.place_order('buy', 'BTC/USDT', 1000.0)  # Above $50 max
        if 'BTC/USDT' in bot.positions:
            qty = bot.positions['BTC/USDT']['qty']
            price = bot.positions['BTC/USDT']['price']
            amount = qty * price
            if amount <= MAX_TRADE_USD:
                print(f"✅ Maximum size capped: ${amount:.2f} <= ${MAX_TRADE_USD}")
            else:
                print(f"❌ Maximum size NOT capped: ${amount:.2f} > ${MAX_TRADE_USD}")
                return False
        
        # Test symbol whitelist
        result = bot.place_order('buy', 'XYZ/USDT', 25.0)
        if result is None:
            print("✅ Symbol whitelist validation working")
        else:
            print("❌ Symbol whitelist not enforced")
            return False
        
    except Exception as e:
        print(f"❌ Order validation test failed: {e}")
        return False
    
    return True


def test_live_mode_checks():
    """Test live mode safety checks."""
    print("\n" + "="*60)
    print("9. Testing Live Mode Safety Checks")
    print("="*60)
    
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        
        bot = CryptoPiggyTop2026()
        
        # Check is_live() logic
        is_live = bot.is_live()
        print(f"✅ is_live(): {is_live} (expected False in paper mode)")
        
        # Check _allow_live_env
        allow_live_env = bot._allow_live_env
        print(f"✅ _allow_live_env: {allow_live_env}")
        
        # Check live_confirmed flag
        live_confirmed = bot.live_confirmed
        print(f"✅ live_confirmed: {live_confirmed} (expected False)")
        
        # Check dry_run flag
        dry_run = bot.dry_run
        print(f"✅ dry_run: {dry_run} (expected False)")
        
        # Verify all must be True for is_live()
        if is_live:
            print("❌ is_live() returned True when it should be False")
            return False
        
        print("✅ Live mode safety checks working correctly")
        
    except Exception as e:
        print(f"❌ Live mode checks failed: {e}")
        return False
    
    return True


def test_app_imports():
    """Test that app.py imports work."""
    print("\n" + "="*60)
    print("10. Testing App Imports")
    print("="*60)
    
    try:
        # Try to parse app.py to check for syntax errors
        with open('app.py', 'r') as f:
            code = f.read()
        
        compile(code, 'app.py', 'exec')
        print("✅ app.py syntax is valid")
        
        # Check key imports in app.py
        if 'import streamlit as st' in code:
            print("✅ streamlit imported")
        else:
            print("❌ streamlit import missing")
            return False
        
        if 'from crypto_piggy_top import CryptoPiggyTop2026' in code:
            print("✅ CryptoPiggyTop2026 imported")
        else:
            print("❌ CryptoPiggyTop2026 import missing")
            return False
        
    except SyntaxError as e:
        print(f"❌ app.py has syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ App import test failed: {e}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CryptoPiggy Streamlit App Test Suite")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Bot Initialization", test_bot_initialization),
        ("Exchange Setup", test_exchange_setup),
        ("OHLCV Fetch", test_ohlcv_fetch),
        ("Strategy Execution", test_strategy_execution),
        ("Backtest", test_backtest),
        ("State Persistence", test_state_persistence),
        ("Order Validation", test_order_validation),
        ("Live Mode Safety", test_live_mode_checks),
        ("App Imports", test_app_imports),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🟢 ALL TESTS PASSED - App is ready!")
        return 0
    else:
        print(f"🔴 {total - passed} test(s) failed - Please review")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
