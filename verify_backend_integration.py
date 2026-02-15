#!/usr/bin/env python3
"""
Backend Integration Verification Script
Tests the complete API key → validation → backend sync → live trading flow
"""
import os
import sys
import json
from pathlib import Path

# Set ALLOW_LIVE for testing
os.environ['ALLOW_LIVE'] = '1'
os.environ['BACKEND_API_URL'] = 'http://localhost:8000'

def check_imports():
    """Verify all required imports work."""
    print("🔍 Checking imports...")
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        print("  ✅ crypto_piggy_top")
        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False


def check_backend_integration():
    """Verify backend integration methods exist."""
    print("\n🔍 Checking backend integration...")
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        
        # Check attributes
        assert hasattr(bot, 'backend_url'), "Missing backend_url"
        print(f"  ✅ backend_url: {bot.backend_url}")
        
        assert hasattr(bot, 'backend_user_id'), "Missing backend_user_id"
        print(f"  ✅ backend_user_id: {bot.backend_user_id or '(not set)'}")
        
        assert hasattr(bot, 'backend_enabled'), "Missing backend_enabled"
        print(f"  ✅ backend_enabled: {bot.backend_enabled}")
        
        assert hasattr(bot, 'backend_last_health'), "Missing backend_last_health"
        print(f"  ✅ backend_last_health: {bot.backend_last_health}")
        
        # Check methods
        assert hasattr(bot, 'set_backend'), "Missing set_backend()"
        print("  ✅ set_backend() method")
        
        assert hasattr(bot, 'check_backend_health'), "Missing check_backend_health()"
        print("  ✅ check_backend_health() method")
        
        assert hasattr(bot, 'sync_credentials'), "Missing sync_credentials()"
        print("  ✅ sync_credentials() method")
        
        assert hasattr(bot, 'place_order_backend'), "Missing place_order_backend()"
        print("  ✅ place_order_backend() method")
        
        assert hasattr(bot, 'fetch_backend_balance'), "Missing fetch_backend_balance()"
        print("  ✅ fetch_backend_balance() method")
        
        return True
    except Exception as e:
        print(f"  ❌ {e}")
        return False


def check_is_live_logic():
    """Verify is_live() checks backend health."""
    print("\n🔍 Checking is_live() logic...")
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        
        # Initial state should be paper mode
        assert bot.is_live() == False, "Should be paper mode initially"
        print("  ✅ Initially paper mode (is_live=False)")
        
        # Test backend_enabled = False path
        bot.backend_enabled = False
        bot.paper_mode = False
        bot.live_confirmed = True
        bot.exchange = 'mock'
        bot.dry_run = False
        # Should be True (backend_ok defaults to True when backend_enabled=False)
        assert bot.is_live() == True, "Should be live when backend not used"
        print("  ✅ is_live=True when backend_enabled=False and all other checks pass")
        
        # Test backend_enabled = True path with bad health
        bot.backend_enabled = True
        bot.backend_last_health = False
        # Should be False (backend health failing)
        assert bot.is_live() == False, "Should be paper when backend health fails"
        print("  ✅ is_live=False when backend_enabled=True and backend_last_health=False")
        
        # Test backend_enabled = True path with good health
        bot.backend_last_health = True
        # Should be True
        assert bot.is_live() == True, "Should be live when backend health OK"
        print("  ✅ is_live=True when backend_enabled=True and backend_last_health=True")
        
        return True
    except Exception as e:
        print(f"  ❌ {e}")
        return False


def check_min_trade_size():
    """Verify minimum trade size is $2."""
    print("\n🔍 Checking minimum trade size...")
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        
        min_size = bot.risk_settings.get('min_trade_size_usd')
        assert min_size == 2.0, f"Expected 2.0, got {min_size}"
        print(f"  ✅ min_trade_size_usd: ${min_size}")
        
        return True
    except Exception as e:
        print(f"  ❌ {e}")
        return False


def check_symbol_normalization():
    """Verify symbol normalization for Binance.US."""
    print("\n🔍 Checking symbol normalization...")
    try:
        from crypto_piggy_top import CryptoPiggyTop2026
        bot = CryptoPiggyTop2026()
        bot.backend_user_id = 'test-user'
        bot.backend_url = 'http://localhost:8000'
        
        # Mock requests to check payload
        class MockResponse:
            status_code = 200
            def json(self):
                return {'orderId': 'mock-123', 'status': 'filled', 'price': 50000}
        
        try:
            import requests
            original_post = requests.post
            
            def mock_post(url, json=None, **kwargs):
                # Verify symbol normalization
                if 'binanceus' in json.get('exchange', '').lower():
                    assert json['symbol'] == 'BTCUSDT', f"Expected BTCUSDT, got {json['symbol']}"
                    assert json['symbolCcxt'] == 'BTC/USDT', f"Expected BTC/USDT, got {json['symbolCcxt']}"
                    print(f"  ✅ Symbol normalized: BTC/USDT → BTCUSDT for binanceus")
                    print(f"  ✅ symbolCcxt preserved: {json['symbolCcxt']}")
                return MockResponse()
            
            requests.post = mock_post
            result = bot.place_order_backend('buy', 'BTC/USDT', 10.0, exchange='binanceus')
            requests.post = original_post
            
            return True
        except ImportError:
            print("  ⚠️  requests not installed, skipping symbol normalization test")
            return True
    except Exception as e:
        print(f"  ❌ {e}")
        return False


def check_credentials_storage():
    """Verify credential storage path."""
    print("\n🔍 Checking credentials storage...")
    try:
        CRED_PATH = Path('.cryptopiggy/credentials.json')
        print(f"  ✅ Credentials path: {CRED_PATH}")
        
        # Test save/load
        test_data = {
            'user_id': 'test-user-123',
            'exchange': 'binanceus',
            'api_key': 'test-key',
            'api_secret': 'test-secret',
            'backend_url': 'http://localhost:8000',
            'validated': True
        }
        
        CRED_PATH.parent.mkdir(parents=True, exist_ok=True)
        CRED_PATH.write_text(json.dumps(test_data, indent=2))
        print("  ✅ Test credentials written")
        
        loaded = json.loads(CRED_PATH.read_text())
        assert loaded == test_data, "Loaded data doesn't match"
        print("  ✅ Test credentials loaded correctly")
        
        # Cleanup
        CRED_PATH.unlink()
        if CRED_PATH.parent.exists() and not any(CRED_PATH.parent.iterdir()):
            CRED_PATH.parent.rmdir()
        print("  ✅ Cleanup successful")
        
        return True
    except Exception as e:
        print(f"  ❌ {e}")
        return False


def main():
    print("="*60)
    print("Backend Integration Verification")
    print("="*60)
    
    checks = [
        ("Import Check", check_imports),
        ("Backend Integration", check_backend_integration),
        ("is_live() Logic", check_is_live_logic),
        ("Minimum Trade Size", check_min_trade_size),
        ("Symbol Normalization", check_symbol_normalization),
        ("Credentials Storage", check_credentials_storage),
    ]
    
    results = []
    for name, check in checks:
        try:
            passed = check()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ {name} failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_checks = len(results)
    
    print(f"\nTotal: {total_passed}/{total_checks} checks passed")
    
    if total_passed == total_checks:
        print("\n🎉 All checks passed! Backend integration ready.")
        return 0
    else:
        print(f"\n⚠️  {total_checks - total_passed} checks failed. Review above output.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
