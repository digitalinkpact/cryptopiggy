#!/usr/bin/env python3
"""
Complete end-to-end flow test for CryptoPiggy Trading Bot.
Tests the entire workflow from initialization to live trading.
Run with: python test_complete_flow.py
"""

import sys
import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('CompleteFlowTest')

def test_complete_flow():
    """Test the complete trading flow."""
    print("\n" + "="*70)
    print("CRYPTOPIGGY COMPLETE FLOW TEST")
    print("="*70)
    
    passed = 0
    failed = 0
    
    # Test 1: Core imports
    print("\n[1/10] Testing core imports...")
    try:
        from crypto_piggy_top import (
            CryptoPiggyTop2026,
            MAX_TRADE_USD,
            MAX_PORTFOLIO_RISK_PCT,
            MAX_DAILY_TRADES,
            MAX_DAILY_LOSS_PCT
        )
        print("✅ Core engine imports successful")
        passed += 1
    except Exception as e:
        print(f"❌ Import failed: {e}")
        failed += 1
        return False
    
    # Test 2: Bot initialization
    print("\n[2/10] Testing bot initialization...")
    try:
        bot = CryptoPiggyTop2026()
        assert bot.paper_mode == True, "Should start in paper mode"
        assert bot.live_confirmed == False, "Should not be live confirmed"
        assert bot.daily_trades_count == 0, "Should have 0 trades"
        print("✅ Bot initialized correctly")
        passed += 1
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")
        failed += 1
        return False
    
    # Test 3: Daily limits method exists and works
    print("\n[3/10] Testing daily limits enforcement...")
    try:
        result = bot._check_daily_limits()
        assert result == True, "Initial check should pass"
        
        # Test max trades
        bot.daily_trades_count = MAX_DAILY_TRADES
        result = bot._check_daily_limits()
        assert result == False, "Should fail when max trades reached"
        
        # Reset for next tests
        bot.daily_trades_count = 0
        print("✅ Daily limits enforcement working")
        passed += 1
    except Exception as e:
        print(f"❌ Daily limits test failed: {e}")
        failed += 1
    
    # Test 4: Order validation (paper mode)
    print("\n[4/10] Testing order validation...")
    try:
        # Invalid side
        result = bot.place_order('invalid', 'BTC/USDT', 10)
        assert result is None, "Invalid side should be rejected"
        
        # Invalid symbol
        result = bot.place_order('buy', 'INVALID/USDT', 10)
        assert result is None, "Invalid symbol should be rejected"
        
        # Too small
        result = bot.place_order('buy', 'BTC/USDT', 0.5)
        assert result is None, "Too small order should be rejected"
        
        # Valid paper trade
        result = bot.place_order('buy', 'BTC/USDT', 10)
        assert result is not None, "Valid order should succeed"
        assert 'BTC/USDT' in bot.positions, "Position should be created"
        
        print("✅ Order validation working")
        passed += 1
    except Exception as e:
        print(f"❌ Order validation failed: {e}")
        failed += 1
    
    # Test 5: State persistence
    print("\n[5/10] Testing state persistence...")
    try:
        # Save current state
        bot.save_state()
        state_file = Path('state.json')
        assert state_file.exists(), "State file should be created"
        
        # Load in new bot
        bot2 = CryptoPiggyTop2026()
        assert len(bot2.positions) > 0, "Positions should be loaded"
        assert len(bot2.trade_log) > 0, "Trades should be loaded"
        
        print("✅ State persistence working")
        passed += 1
    except Exception as e:
        print(f"❌ State persistence failed: {e}")
        failed += 1
    
    # Test 6: Backend health check
    print("\n[6/10] Testing backend integration...")
    try:
        bot.backend_url = "http://localhost:8000"
        result = bot.check_backend_health()
        # Result can be True or False, just check no crash
        print(f"✅ Backend health check returned: {result}")
        passed += 1
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        failed += 1
    
    # Test 7: Credential sync (mock)
    print("\n[7/10] Testing credential sync...")
    try:
        bot.backend_url = "http://invalid.local:9999"
        result = bot.sync_credentials('test_key', 'test_secret', 'binanceus')
        assert isinstance(result, dict), "Should return dict"
        assert 'ok' in result or 'error' in result, "Should have ok or error field"
        print("✅ Credential sync handling correct")
        passed += 1
    except Exception as e:
        print(f"❌ Credential sync failed: {e}")
        failed += 1
    
    # Test 8: Live mode guards
    print("\n[8/10] Testing live mode safety guards...")
    try:
        # Should not be live without all requirements
        is_live = bot.is_live()
        assert is_live == False, "Should not be live in paper mode"
        
        # Check environment guard
        allow_live = bot._allow_live_env
        print(f"   ALLOW_LIVE env: {allow_live}")
        
        print("✅ Live mode guards working")
        passed += 1
    except Exception as e:
        print(f"❌ Live mode guards failed: {e}")
        failed += 1
    
    # Test 9: OHLCV fetch
    print("\n[9/10] Testing OHLCV data fetch...")
    try:
        df = bot.fetch_ohlcv_df('BTC/USDT', timeframe='5m', limit=100)
        assert df is not None, "Should return dataframe"
        assert len(df) > 0, "Should have data"
        assert 'close' in df.columns, "Should have close column"
        print("✅ OHLCV fetch working")
        passed += 1
    except Exception as e:
        print(f"❌ OHLCV fetch failed: {e}")
        failed += 1
    
    # Test 10: Strategy execution
    print("\n[10/10] Testing strategy execution...")
    try:
        strategy = bot.strategies['sma_crossover']
        df = bot.fetch_ohlcv_df('BTC/USDT', timeframe='5m', limit=100)
        df = strategy.populate_indicators(df)
        df = strategy.populate_entry_trend(df)
        df = strategy.populate_exit_trend(df)
        
        assert 'entry' in df.columns, "Should have entry signals"
        assert 'exit' in df.columns, "Should have exit signals"
        print("✅ Strategy execution working")
        passed += 1
    except Exception as e:
        print(f"❌ Strategy execution failed: {e}")
        failed += 1
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✅ Passed: {passed}/10")
    print(f"❌ Failed: {failed}/10")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Core engine is ready.")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Start backend on localhost:8000")
        print("  3. Run app: streamlit run app_new.py")
        print("  4. Configure API keys in Settings")
        print("  5. Validate & Sync credentials")
        print("  6. Enable live trading with confirmation")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed. Review output above.")
        return False


if __name__ == "__main__":
    success = test_complete_flow()
    sys.exit(0 if success else 1)
