# API Key → Live Trading Flow - Complete Setup & Testing Guide

## What Was Fixed

### 1. **Backend Proxy Integration** (`crypto_piggy_top.py`)
- Added `requests` import with try/except for optional backend proxy
- Added `set_backend()`, `check_backend_health()`, `sync_credentials()`, `place_order_backend()`, `fetch_backend_balance()`
- Modified `is_live()` to check `backend_enabled` and `backend_last_health`
- Added backend order path in `place_order()` that runs **before** ccxt direct path
- Normalize Binance.US symbols (BTC/USDT → BTCUSDT) for backend while preserving CCXT format
- Lowered `min_trade_size_usd` from $10 to $2 for tiny test trades

### 2. **Streamlit App Backend Integration** (`app_new.py` & `app.py`)
- Added credential storage to `.cryptopiggy/credentials.json` with `_load_credentials()`, `_save_credentials()`
- Added `_check_backend_health()`, `_sync_credentials()`, `_fetch_backend_balance()` helper functions
- Added Settings UI with:
  - User ID input (auto-generated UUID if not set)
  - Exchange selector (binanceus, binance, kraken, coinbasepro)
  - Backend URL input (default: http://localhost:8000)
  - API Key/Secret password inputs
  - **💾 Save Keys** button → writes to `.cryptopiggy/credentials.json`
  - **✅ Validate & Sync** button → calls `/api/credentials`, marks `validated: true` on success
  - Backend health indicator (✅ OK or ❌ error message)
  - Validation status caption
- Modified live toggle to require:
  - `ALLOW_LIVE=1` env var
  - Validated backend credentials (`validated: true` in storage)
  - Backend health check passing
- Added **Test Live BUY** button in Bot Control tab (app_new.py only)
- Added **Fetch Backend Balance** button (app_new.py only)
- Added Backend Balance expander in Portfolio tab (app_new.py only)

### 3. **Error Handling**
- All backend calls wrapped in try/except with timeout
- Status code checking (200 = success, others logged)
- Clear error toasts for validation failures
- Fallback if backend drops after live mode enabled (auto-disables)

---

## Testing Flow (Step-by-Step)

### Prerequisites
1. **Set environment variable**:
   ```bash
   export ALLOW_LIVE=1
   ```

2. **Start backend server** (or use deployed URL):
   ```bash
   # Assuming backend is at http://localhost:8000 with these routes:
   # GET  /api/health
   # POST /api/credentials (body: {userId, exchange, apiKey, apiSecret})
   # POST /api/trade (body: {userId, exchange, side, symbol, amountUsd})
   # GET  /api/balance/:userId
   ```

3. **Get Binance.US API keys**:
   - Log into Binance.US → API Management
   - Create API key with:
     - ✅ Enable Spot Trading
     - ✅ Enable Reading
     - ❌ No withdrawals
     - IP whitelist recommended

---

### Test Step 1: Save Keys
1. Run: `streamlit run app_new.py` (or `app.py`)
2. Expand **API Keys & Backend Settings** section
3. Enter:
   - **User ID**: Leave auto-generated or enter your own
   - **Exchange**: Select `binanceus`
   - **Backend URL**: `http://localhost:8000` (or your deployed URL)
   - **API Key**: Paste Binance.US API key
   - **API Secret**: Paste Binance.US API secret
4. Click **💾 Save Keys**
5. ✅ **Expected**: Toast "✅ Keys saved" → page reloads → keys persist in form (stored at `.cryptopiggy/credentials.json`)

---

### Test Step 2: Validate & Sync
1. With keys saved, ensure backend health shows **✅ Backend health: OK**
   - If ❌, check backend is running and accessible
2. Click **✅ Validate & Sync**
3. ✅ **Expected**: 
   - Toast "✅ Credentials validated and synced"
   - Caption changes to "Validation status: ✅ Validated"
   - Page reloads with `validated: true` persisted
4. ❌ **If Failed**:
   - Check console logs for error details
   - Common issues:
     - Backend `/api/credentials` route not working
     - Invalid API signature (check Binance.US key permissions)
     - 401/403 auth errors (check keys are correct)
     - Network timeout (increase `BACKEND_TIMEOUT` env var)

---

### Test Step 3: Enable Live Trading
1. Scroll to **Trading Mode** section
2. Check the **Enable Live Trading** checkbox
3. ✅ **Expected**:
   - Warning box appears: "⚠️ Enable Live Trading? This will execute REAL trades with REAL money!"
   - Shows safety limits (Max trade: $50, Max portfolio risk: 1%, Daily trades: 20, Allowed symbols: BTC/USDT, ETH/USDT)
4. Click **🔴 ENABLE LIVE TRADING (I understand the risks)** button
5. ✅ **Expected**:
   - Toast "✅ Live trading enabled!"
   - Page reloads
   - Top banner changes to 🔴 red "LIVE TRADING MODE ACTIVE"
   - Footer shows "Mode: 🔴 LIVE"
6. ❌ **If Blocked**:
   - Error "❌ Set ALLOW_LIVE=1 environment variable" → export ALLOW_LIVE=1 and restart
   - Error "❌ Validate & Sync credentials..." → redo Test Step 2

---

### Test Step 4: Try Tiny Live Trade
**(app_new.py only - not in app.py)**

1. Go to **🤖 Bot Control** tab
2. In right column under **Live Trade Test**:
   - Set **Test Trade Amount (USD)**: `2.0` (minimum)
3. Click **🧪 Test Live BUY (BTC/USDT)**
4. ✅ **Expected**:
   - Toast "✅ Live order submitted. Order ID: [order_id]"
   - Check Binance.US → Orders → Open Orders or Order History for new BTC buy
   - Order should be ~$2 worth of BTC at market price
5. ❌ **If Failed**:
   - Toast "❌ Live order failed" → check console logs
   - Common issues:
     - Symbol format wrong (should be `BTCUSDT` for Binance.US backend, `BTC/USDT` for CCXT)
     - Insufficient balance
     - Order size below Binance.US minimum (varies by symbol, usually ~$10-15 for BTC)
     - Rate limit exceeded
     - Missing userId in backend payload

---

### Test Step 5: Check Balance Update
**(app_new.py only)**

1. In **🤖 Bot Control** tab, click **💰 Fetch Backend Balance**
2. ✅ **Expected**:
   - Toast "✅ Balance fetched"
   - JSON response showing USDT balance, BTC balance, total USD value
3. Verify BTC balance increased if trade succeeded

**Alternative**: In **📊 Portfolio** tab, expand **Backend Balance**
- Shows same balance JSON if credentials validated

---

## Verification Checklist

After completing all test steps, verify:

- ✅ Keys saved and persist on page reload
- ✅ Backend health check shows ✅ OK
- ✅ Validate & Sync succeeds with ✅ Validated caption
- ✅ Live toggle requires validation + backend health
- ✅ Live mode banner shows 🔴 red when enabled
- ✅ Test trade executes and returns order ID
- ✅ Binance.US order history shows real order
- ✅ Backend balance fetch returns real account balance
- ✅ Trade log (📜 Trade Log tab) shows 🔴 LIVE for real orders
- ✅ Emergency Stop button disables live mode instantly

---

## Troubleshooting Common Issues

### Issue: "❌ Backend health: Connection refused"
**Fix**: Start backend server or check `BACKEND_API_URL` env var

### Issue: "❌ Validation failed: 401" or "invalid signature"
**Fix**: 
1. Double-check API key/secret copied correctly (no spaces)
2. Ensure Binance.US key has "Enable Spot Trading" permission
3. Check backend is correctly signing requests with Binance.US API

### Issue: Live trade returns "❌ Live order failed"
**Diagnose**:
1. Check console logs for detailed error
2. Verify `bot.backend_enabled = True` (should happen after Validate & Sync)
3. Verify `bot.is_live()` returns True (check all conditions: `not paper_mode`, `live_confirmed`, `backend_enabled`, `backend_last_health`)
4. Check backend `/api/trade` route logs for incoming request

### Issue: Symbol format error (e.g., "Invalid symbol")
**Fix**: Backend should normalize symbols:
- CCXT format: `BTC/USDT`
- Binance.US format: `BTCUSDT` (no slash)
- `place_order_backend()` now handles this automatically for binanceus exchange

### Issue: Order rejected by Binance.US ("MIN_NOTIONAL")
**Fix**: Increase test trade amount to $10-15 (Binance.US minimum varies by symbol)

---

## Files Modified

1. **crypto_piggy_top.py**:
   - Added backend proxy methods
   - Modified `is_live()` to check backend health
   - Added backend order path in `place_order()`
   - Lowered min trade size to $2

2. **app_new.py**:
   - Added credential storage/loading
   - Added Settings UI with Save/Validate buttons
   - Added live toggle gating on validation + backend health
   - Added Test Live BUY button
   - Added Fetch Backend Balance button
   - Added Backend Balance expander

3. **app.py**:
   - Added credential storage/loading
   - Added Settings UI with Save/Validate buttons
   - Modified live toggle gating

---

## Next Steps After Verification

Once the full flow works:

1. **Deploy backend** to production URL (e.g., Heroku, Railway, Fly.io)
2. **Update `BACKEND_API_URL`** env var or in Settings UI
3. **Set `LIVE_CONFIRM_TOKEN`** env var for extra safety (requires token entry before enabling live)
4. **Test with smaller timeframes** in bot loop to see live trades execute automatically
5. **Monitor trade log** for 🔴 LIVE orders
6. **Enable Telegram alerts** (set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`) to get notifications

---

## Final Notes

- **Backend is required for live trading** - ccxt direct path is preserved but backend path runs first
- **Credentials stored locally** at `.cryptopiggy/credentials.json` (gitignored)
- **Validation status persists** across app restarts
- **Live mode auto-disables** if backend health check fails
- **Emergency Stop** button in Bot Control tab instantly disables live mode
- **Minimum trade size is $2** but Binance.US may require higher per symbol
- **Symbol normalization** handles BTC/USDT → BTCUSDT for Binance.US backend
