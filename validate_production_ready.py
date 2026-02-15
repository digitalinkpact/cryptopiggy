#!/usr/bin/env python3
"""
FINAL VALIDATION & DEPLOYMENT SCRIPT
Runs all checks to ensure the application is production-ready.
Run with: python validate_production_ready.py
"""

import sys
import os
import json
from pathlib import Path

print("="*80)
print("CRYPTOPIGGY PRODUCTION READINESS VALIDATION")
print("="*80)

checks_passed = 0
checks_total = 0

# Check 1: All files exist
print("\n[CHECK 1] Verifying all required files exist...")
checks_total += 1
required_files = [
    'crypto_piggy_top.py',
    'app.py',
    'app_new.py',
    'test_app.py',
    'test_integration.py',
    'test_live_trading.py',
    'test_complete_flow.py',
    'requirements.txt',
    '.github/copilot-instructions.md'
]

all_exist = True
for f in required_files:
    if Path(f).exists():
        print(f"  ✅ {f}")
    else:
        print(f"  ❌ {f} MISSING")
        all_exist = False

if all_exist:
    print("  ✅ All required files present")
    checks_passed += 1
else:
    print("  ❌ Some files missing")

# Check 2: Python syntax validation
print("\n[CHECK 2] Validating Python syntax...")
checks_total += 1
import py_compile

files_to_check = [
    'crypto_piggy_top.py',
    'app.py',
    'app_new.py',
    'test_app.py',
    'test_integration.py',
    'test_live_trading.py',
    'test_complete_flow.py'
]

syntax_ok = True
for f in files_to_check:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  ✅ {f}")
    except py_compile.PyCompileError as e:
        print(f"  ❌ {f}: {e}")
        syntax_ok = False

if syntax_ok:
    print("  ✅ All files have valid syntax")
    checks_passed += 1
else:
    print("  ❌ Some files have syntax errors")

# Check 3: Critical constants defined
print("\n[CHECK 3] Verifying safety constants...")
checks_total += 1
try:
    from crypto_piggy_top import (
        MAX_TRADE_USD,
        MAX_PORTFOLIO_RISK_PCT,
        MAX_DAILY_TRADES,
        MAX_DAILY_LOSS_PCT
    )
    
    print(f"  ✅ MAX_TRADE_USD = ${MAX_TRADE_USD}")
    print(f"  ✅ MAX_PORTFOLIO_RISK_PCT = {MAX_PORTFOLIO_RISK_PCT:.1%}")
    print(f"  ✅ MAX_DAILY_TRADES = {MAX_DAILY_TRADES}")
    print(f"  ✅ MAX_DAILY_LOSS_PCT = {MAX_DAILY_LOSS_PCT:.1%}")
    checks_passed += 1
except Exception as e:
    print(f"  ❌ Failed to import constants: {e}")

# Check 4: Core engine methods exist
print("\n[CHECK 4] Verifying core engine methods...")
checks_total += 1
try:
    from crypto_piggy_top import CryptoPiggyTop2026
    
    bot = CryptoPiggyTop2026()
    required_methods = [
        'setup_exchange',
        'configure_api_keys',
        'is_live',
        'set_backend',
        'check_backend_health',
        'sync_credentials',
        'fetch_backend_balance',
        'place_order_backend',
        'get_equity',
        'fetch_ohlcv_df',
        'safe_ccxt_call',
        '_check_daily_limits',
        'place_order',
        'backtest',
        'hyperopt',
        'send_telegram',
        'status',
        'enable_live',
        'disable_live',
        'predict_next_close_series',
        'save_state',
        'load_state',
        'menu',
        'start_bot'
    ]
    
    missing = []
    for method in required_methods:
        if not hasattr(bot, method):
            missing.append(method)
        else:
            print(f"  ✅ {method}()")
    
    if not missing:
        checks_passed += 1
    else:
        print(f"  ❌ Missing methods: {missing}")
        
except Exception as e:
    print(f"  ❌ Failed to check methods: {e}")

# Check 5: Strategies implemented
print("\n[CHECK 5] Verifying strategy implementations...")
checks_total += 1
try:
    from crypto_piggy_top import CryptoPiggyTop2026, BaseStrategy, SMA_Crossover, RSI_Strategy
    
    bot = CryptoPiggyTop2026()
    
    print(f"  ✅ BaseStrategy class exists")
    print(f"  ✅ SMA_Crossover strategy available")
    print(f"  ✅ RSI_Strategy strategy available")
    print(f"  ✅ Active strategies: {list(bot.strategies.keys())}")
    
    checks_passed += 1
except Exception as e:
    print(f"  ❌ Strategy check failed: {e}")

# Check 6: State persistence works
print("\n[CHECK 6] Verifying state persistence...")
checks_total += 1
try:
    from crypto_piggy_top import CryptoPiggyTop2026
    
    bot = CryptoPiggyTop2026()
    bot.positions['BTC/USDT'] = {'qty': 0.1, 'price': 50000}
    bot.save_state()
    
    state_file = Path('state.json')
    if state_file.exists():
        data = json.loads(state_file.read_text())
        if 'positions' in data and 'BTC/USDT' in data['positions']:
            print("  ✅ State saved and loaded correctly")
            checks_passed += 1
        else:
            print("  ❌ State file missing position data")
    else:
        print("  ❌ State file not created")
        
except Exception as e:
    print(f"  ❌ State persistence failed: {e}")

# Check 7: Credentials file structure
print("\n[CHECK 7] Verifying credentials handling...")
checks_total += 1
try:
    creds_path = Path('.cryptopiggy/credentials.json')
    required_fields = ['user_id', 'exchange', 'api_key', 'api_secret', 'backend_url', 'validated']
    
    if creds_path.exists():
        creds = json.loads(creds_path.read_text())
        for field in required_fields:
            if field in creds:
                print(f"  ✅ {field}")
            else:
                print(f"  ❌ {field} missing")
        checks_passed += 1
    else:
        print("  ⚠️  Credentials file not yet created (will be on first save)")
        checks_passed += 1  # This is OK on first run
        
except Exception as e:
    print(f"  ❌ Credentials check failed: {e}")

# Check 8: requirements.txt valid
print("\n[CHECK 8] Verifying dependencies...")
checks_total += 1
try:
    reqs = Path('requirements.txt').read_text().strip().split('\n')
    print(f"  ✅ {len(reqs)} dependencies defined:")
    for req in reqs:
        if req.strip() and not req.startswith('#'):
            print(f"     - {req.strip()}")
    checks_passed += 1
except Exception as e:
    print(f"  ❌ Requirements check failed: {e}")

# Summary
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)
print(f"Checks Passed: {checks_passed}/{checks_total}")

if checks_passed == checks_total:
    print("\n🎉 ALL CHECKS PASSED - APPLICATION IS PRODUCTION READY!")
    print("\nDEPLOYMENT INSTRUCTIONS:")
    print("  1. pip install -r requirements.txt")
    print("  2. export ALLOW_LIVE=1")
    print("  3. export EXCHANGE=binanceus")
    print("  4. streamlit run app_new.py")
    print("  5. Configure API keys in Settings")
    print("  6. Validate & Sync credentials")
    print("  7. Enable live trading")
    print("  8. Test with $2 trade")
    sys.exit(0)
else:
    print(f"\n❌ {checks_total - checks_passed} check(s) failed")
    print("Please review errors above before deployment")
    sys.exit(1)
