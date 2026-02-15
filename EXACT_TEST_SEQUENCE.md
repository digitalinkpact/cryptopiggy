# EXACT TEST SEQUENCE - API Key to Live Trade

## Test Environment Setup

```bash
# Terminal 1: Set environment
export ALLOW_LIVE=1
export BACKEND_API_URL=http://localhost:8000
export LIVE_CONFIRM_TOKEN=test_token_123  # Optional but recommended

# Terminal 2: Start backend (if not deployed)
cd /path/to/backend
npm start  # or python main.py, etc.
# Ensure these routes work:
# GET  /api/health → 200 OK
# POST /api/credentials → {ok: true, canTrade: true}
# POST /api/trade → {orderId: "...", status: "filled"}
# GET  /api/balance/:userId → {balances: {...}}

# Terminal 3: Start Streamlit
cd /workspaces/cryptopiggy
streamlit run app_new.py
```

---

## Test Step 1: Initial Load

**Action**: Open browser to http://localhost:8501

**Expected UI State**:
```
✅ PAPER TRADING MODE: All trades are simulated

Sidebar:
  ⚙️ Configuration
  
  API Keys & Backend
  User ID: [auto-generated UUID like a1b2c3d4-...]
  Exchange: [binanceus] (dropdown)
  Backend URL: http://localhost:8000
  API Key: (empty password field)
  API Secret: (empty password field)
  ❌ Backend health: requests_unavailable (or connection error if backend not running)
  
  [💾 Save Keys]  [✅ Validate & Sync]
  
  Validation status: ❌ Not validated
  
  Exchange Status:
  ⚠️ No exchange configured (backend trading still available)
  
  Trading Mode:
  [ ] Enable Live Trading (unchecked)
```

**Console Logs** (check terminal running Streamlit):
```
INFO | CryptoPiggyTop initialized in paper mode
INFO | backend_enabled: False
INFO | backend_url: http://localhost:8000
```

---

## Test Step 2: Enter Credentials

**Action**: 
1. Keep auto-generated User ID (or enter your own like `test-user-binanceus-001`)
2. Select exchange: `binanceus`
3. Keep Backend URL: `http://localhost:8000` (or your deployed URL)
4. Paste your Binance.US API Key
5. Paste your Binance.US API Secret

**Expected UI State** (before clicking anything):
```
API Key: •••••••••••••••••• (shows dots, not actual key)
API Secret: •••••••••••••••••• (shows dots)
❌ Backend health: [error message or requests_unavailable]
```

---

## Test Step 3: Save Keys

**Action**: Click **💾 Save Keys**

**Expected UI Changes**:
```
Toast appears: ✅ Keys saved
Page reloads
Form fields now show:
  User ID: test-user-binanceus-001 (persisted)
  Exchange: binanceus (persisted)
  Backend URL: http://localhost:8000 (persisted)
  API Key: •••••••••••••••••• (persisted)
  API Secret: •••••••••••••••••• (persisted)
```

**File System Check**:
```bash
cat .cryptopiggy/credentials.json
```
**Expected Output**:
```json
{
  "user_id": "test-user-binanceus-001",
  "exchange": "binanceus",
  "api_key": "your-actual-key-here",
  "api_secret": "your-actual-secret-here",
  "backend_url": "http://localhost:8000",
  "validated": false
}
```

**Console Logs**:
```
INFO | Credentials saved to .cryptopiggy/credentials.json
```

---

## Test Step 4: Check Backend Health

**Action**: Page should auto-reload after saving, but manually refresh if needed

**Expected UI State** (if backend is running):
```
✅ Backend health: OK
```

**Expected UI State** (if backend is NOT running):
```
❌ Backend health: Connection refused
or
❌ Backend health: http_500
or
❌ Backend health: [timeout after 5 seconds]
```

**Fix if Failed**: Start backend in Terminal 2, then refresh page

---

## Test Step 5: Validate & Sync

**Action**: Click **✅ Validate & Sync**

**Expected Backend Request** (check backend logs):
```
POST /api/credentials
Body:
{
  "userId": "test-user-binanceus-001",
  "exchange": "binanceus",
  "apiKey": "your-actual-key",
  "apiSecret": "your-actual-secret"
}
```

**Expected Backend Response**:
```
200 OK
{
  "ok": true,
  "canTrade": true,
  "validated": true,
  "userId": "test-user-binanceus-001",
  "exchange": "binanceus"
}
```

**Expected UI Changes**:
```
Toast appears: ✅ Credentials validated and synced
Page reloads
Caption changes: Validation status: ✅ Validated
```

**File System Check**:
```bash
cat .cryptopiggy/credentials.json
```
**Expected Output**:
```json
{
  "user_id": "test-user-binanceus-001",
  "exchange": "binanceus",
  "api_key": "your-actual-key",
  "api_secret": "your-actual-secret",
  "backend_url": "http://localhost:8000",
  "validated": true   ← Changed from false to true
}
```

**Console Logs**:
```
INFO | Credentials validated with backend
INFO | bot.backend_enabled = True
INFO | bot.backend_last_health = True
```

**If Failed (Common Issues)**:

### ❌ "Validation failed: 401" or "Unauthorized"
**Cause**: Invalid API key/secret or wrong exchange
**Fix**: 
- Double-check keys copied correctly (no trailing spaces)
- Verify exchange is `binanceus` not `binance`
- Check Binance.US API key has "Enable Spot Trading" permission

### ❌ "Validation failed: invalid signature"
**Cause**: Backend signing logic doesn't match Binance.US requirements
**Fix**: Check backend `/api/credentials` route implementation

### ❌ "Validation failed: requests_unavailable"
**Cause**: `requests` library not installed
**Fix**: `pip install requests`

### ❌ "Validation failed: timeout"
**Cause**: Backend not responding within 5 seconds
**Fix**: Increase `BACKEND_TIMEOUT=10` env var, restart app

---

## Test Step 6: Enable Live Trading

**Action**: Check the **Enable Live Trading** checkbox

**Expected UI State** (if prerequisites met):
```
Warning box appears:

  ⚠️ Enable Live Trading?
  This will execute REAL trades with REAL money!
  
  Safety Limits:
  • Max trade: $50.00
  • Max portfolio risk: 1.0%
  • Daily trades: 20
  • Allowed symbols: BTC/USDT, ETH/USDT
  
  [🔴 ENABLE LIVE TRADING (I understand the risks)]
```

**Action**: Click **🔴 ENABLE LIVE TRADING**

**Expected UI Changes**:
```
Toast appears: ✅ Live trading enabled!
Page reloads
Top banner changes to RED:

  🔴 LIVE TRADING MODE ACTIVE
  WARNING: Real orders will be placed using real money!
  Max trade: $50.00 | Max risk: 1.0% | Daily limit: 0/20

Checkbox remains checked: [✓] Enable Live Trading
Footer changes: Mode: 🔴 LIVE
```

**Console Logs**:
```
INFO | Live trading ENABLED via Streamlit
INFO | bot.paper_mode = False
INFO | bot.live_confirmed = True
INFO | bot.is_live() = True
```

**If Blocked**:

### ❌ "Set ALLOW_LIVE=1 environment variable"
**Fix**: `export ALLOW_LIVE=1` in terminal, restart Streamlit

### ❌ "Validate & Sync credentials in Settings and ensure backend health is OK"
**Fix**: Redo Test Steps 3-5

---

## Test Step 7: Test Live Trade

**Action**: Navigate to **🤖 Bot Control** tab

**Expected UI**:
```
Bot Control

[Left Column]
Start Bot Loop
Cycles: 6
Interval (seconds): 5
[▶️ Start Bot]

[Right Column]
Quick Actions
[💾 Save State]
[🔄 Refresh Data]

Live Trade Test
Test Trade Amount (USD): 2.0  (number input, min 2.0, max 50.0)
[🧪 Test Live BUY (BTC/USDT)]

[💰 Fetch Backend Balance]

[🛑 Emergency Stop (Disable Live)]
```

**Action**: Keep amount at `2.0` (or increase to 10-15 if Binance.US minimum requires), click **🧪 Test Live BUY (BTC/USDT)**

**Expected Backend Request** (check backend logs):
```
POST /api/trade
Body:
{
  "userId": "test-user-binanceus-001",
  "exchange": "binanceus",
  "side": "buy",
  "symbol": "BTCUSDT",  ← Normalized from BTC/USDT
  "symbolCcxt": "BTC/USDT",
  "amountUsd": 2.0
}
```

**Expected Backend Response**:
```
200 OK
{
  "orderId": "12345678",
  "status": "FILLED",
  "price": "95432.50",
  "executedQty": "0.00002096",
  "cummulativeQuoteQty": "2.00",
  "side": "BUY",
  "symbol": "BTCUSDT",
  "transactTime": 1738675200000
}
```

**Expected UI Changes**:
```
Toast appears: ✅ Live order submitted. Order ID: 12345678
```

**Console Logs**:
```
INFO | 🔴 LIVE BACKEND ORDER: BUY BTC/USDT $2.00
INFO | Backend order response: {'orderId': '12345678', 'status': 'FILLED', ...}
INFO | Trade logged to state.json
```

**Binance.US Verification**:
```
1. Log into Binance.US
2. Go to Orders → Order History
3. Find order ID: 12345678
4. Verify:
   - Symbol: BTC/USDT (or BTCUSDT)
   - Side: BUY
   - Status: Filled
   - Executed: ~$2 worth of BTC
   - Time: matches transactTime
```

**If Failed (Common Issues)**:

### ❌ "Live order failed"
**Check Console**:
```
ERROR | Live backend order failed
ERROR | Backend response: {'error': 'MIN_NOTIONAL', ...}
```
**Fix**: Increase amount to $10-15 (Binance.US minimum varies by symbol)

### ❌ "Enable Live Trading first"
**Fix**: Redo Test Step 6

### ❌ Backend returns 400/500 error
**Check backend logs for error details**

---

## Test Step 8: Check Balance

**Action**: Click **💰 Fetch Backend Balance**

**Expected Backend Request**:
```
GET /api/balance/test-user-binanceus-001
```

**Expected Backend Response**:
```
200 OK
{
  "balances": {
    "BTC": {
      "free": "0.00002096",
      "locked": "0.00000000",
      "total": "0.00002096"
    },
    "USDT": {
      "free": "98.00",
      "locked": "0.00",
      "total": "98.00"
    }
  },
  "totalUsd": "100.00"
}
```

**Expected UI Changes**:
```
Toast appears: ✅ Balance fetched
Expandable JSON view shows:
{
  "balances": {
    "BTC": {"free": "0.00002096", "locked": "0.00000000", "total": "0.00002096"},
    "USDT": {"free": "98.00", "locked": "0.00", "total": "98.00"}
  },
  "totalUsd": "100.00"
}
```

**Verification**:
- BTC balance increased by ~0.00002096 (from trade)
- USDT balance decreased by ~$2 (from trade)

**Alternative**: Go to **📊 Portfolio** tab → expand **Backend Balance** → see same JSON

---

## Test Step 9: Check Trade Log

**Action**: Navigate to **📜 Trade Log** tab

**Expected UI**:
```
Recent Trades

Show last N trades: [slider at 20]

Table:
| Time                | Mode      | Side | Symbol   | Amount USD | Price      | Quantity     |
|---------------------|-----------|------|----------|------------|------------|--------------|
| 2026-02-04 10:30:15 | 🔴 LIVE   | BUY  | BTC/USDT | $2.00      | $95,432.50 | 0.00002096   |

[📥 Download Trade Log CSV]
```

**Verification**:
- Mode shows 🔴 LIVE (not 📝 PAPER)
- Side is BUY
- Symbol is BTC/USDT
- Amount is $2.00
- Price matches Binance.US order
- Quantity matches Binance.US order

---

## Test Step 10: Verify Persistence

**Action**: 
1. Close browser tab
2. Stop Streamlit (Ctrl+C)
3. Restart: `streamlit run app_new.py`
4. Open browser to http://localhost:8501

**Expected UI State**:
```
Settings panel:
  User ID: test-user-binanceus-001 (persisted)
  Exchange: binanceus (persisted)
  Backend URL: http://localhost:8000 (persisted)
  API Key: •••••••••••••••••• (persisted)
  API Secret: •••••••••••••••••• (persisted)
  ✅ Backend health: OK (rechecked on load)
  Validation status: ✅ Validated (persisted)

Live toggle:
  [✓] Enable Live Trading (checked, live mode persisted in session)
  🔴 LIVE TRADING MODE ACTIVE (banner shows)

Trade Log:
  Shows previous BTC/USDT buy order (persisted in state.json)
```

**File System Check**:
```bash
cat .cryptopiggy/credentials.json
# Should still show validated: true

cat state.json | jq '.trade_log[-1]'
# Should show last trade with live: true
```

---

## Test Step 11: Emergency Stop

**Action**: In **🤖 Bot Control** tab, click **🛑 Emergency Stop (Disable Live)**

**Expected UI Changes**:
```
Toast appears: Live trading disabled
Page reloads
Banner changes to GREEN: ✅ PAPER TRADING MODE
Checkbox unchecks: [ ] Enable Live Trading
Footer changes: Mode: 📝 PAPER
```

**Console Logs**:
```
INFO | 🛑 EMERGENCY STOP: Live trading disabled via Streamlit
INFO | bot.paper_mode = True
INFO | bot.live_confirmed = False
INFO | bot.is_live() = False
```

**Verification**:
- Any subsequent orders will be paper trades (not real)
- Trade log will show 📝 PAPER for new trades

---

## Final Verification Checklist

After completing all test steps, verify:

- [x] Keys saved and persist on restart
- [x] Backend health shows ✅ OK
- [x] Validate & Sync succeeds with real keys
- [x] Live toggle requires validation + backend health
- [x] Red banner shows when live enabled
- [x] Test trade executes and returns order ID
- [x] Order appears in Binance.US history
- [x] Order ID matches toast message
- [x] Balance fetch shows updated BTC/USDT
- [x] Trade log shows 🔴 LIVE entry
- [x] Emergency stop immediately disables live
- [x] All data persists across app restarts

---

## Automated Verification

Run the verification script to check code integrity:

```bash
python verify_backend_integration.py
```

**Expected Output**:
```
============================================================
Backend Integration Verification
============================================================

🔍 Checking imports...
  ✅ crypto_piggy_top

🔍 Checking backend integration...
  ✅ backend_url: http://localhost:8000
  ✅ backend_user_id: (not set)
  ✅ backend_enabled: False
  ✅ backend_last_health: None
  ✅ set_backend() method
  ✅ check_backend_health() method
  ✅ sync_credentials() method
  ✅ place_order_backend() method
  ✅ fetch_backend_balance() method

🔍 Checking is_live() logic...
  ✅ Initially paper mode (is_live=False)
  ✅ is_live=True when backend_enabled=False and all other checks pass
  ✅ is_live=False when backend_enabled=True and backend_last_health=False
  ✅ is_live=True when backend_enabled=True and backend_last_health=True

🔍 Checking minimum trade size...
  ✅ min_trade_size_usd: $2.0

🔍 Checking symbol normalization...
  ✅ Symbol normalized: BTC/USDT → BTCUSDT for binanceus
  ✅ symbolCcxt preserved: BTC/USDT

🔍 Checking credentials storage...
  ✅ Credentials path: .cryptopiggy/credentials.json
  ✅ Test credentials written
  ✅ Test credentials loaded correctly
  ✅ Cleanup successful

============================================================
Summary
============================================================
✅ PASS: Import Check
✅ PASS: Backend Integration
✅ PASS: is_live() Logic
✅ PASS: Minimum Trade Size
✅ PASS: Symbol Normalization
✅ PASS: Credentials Storage

Total: 6/6 checks passed

🎉 All checks passed! Backend integration ready.
```

---

## Success Criteria

**The flow is 100% working when:**

1. All 11 test steps complete without errors
2. Real order appears in Binance.US order history
3. Order ID in UI matches Binance.US order ID
4. Balance fetch shows correct updated amounts
5. Trade log shows 🔴 LIVE entry with order ID
6. `verify_backend_integration.py` passes all checks
7. Data persists across app restarts
8. Emergency stop immediately disables live mode

**If all criteria met → API key to live trade flow is VERIFIED 100% WORKING** ✅
