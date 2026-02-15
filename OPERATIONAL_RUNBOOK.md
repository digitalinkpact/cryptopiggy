# CryptoPiggy - Operational Runbook

**Last Updated**: February 4, 2026  
**Version**: 1.0.0 - Production Ready ✅

---

## 🚀 QUICK START (5 Minutes)

### 1. Install & Start Backend
```bash
# Backend should be running on localhost:8000
# with endpoints: /api/health, /api/credentials, /api/trade, /api/balance/:userId
# If backend is not running yet, that's OK - app will show warning but still work in paper mode
```

### 2. Install Python Deps
```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables
```bash
export ALLOW_LIVE=1
export EXCHANGE=binanceus
export BACKEND_API_URL=http://localhost:8000
```

### 4. Start App
```bash
streamlit run app.py
# Opens at http://localhost:8501
```

### 5. First Trade (Paper Mode)
```
Settings → Run Backtest → See results ✅
Live Ticker → Fetch Price → See BTC price ✅
Controls → Start Polling → Monitor live prices ✅
```

---

## 🔴 LIVE TRADING SETUP (If Ready)

### Step 1: Get API Keys
1. Go to Binance.US Account → API Management
2. Create new API key (SPOT trading only)
3. IP Whitelist: add your current IP
4. Disable Withdrawals
5. Enable Orders

### Step 2: Input Keys in App
1. Open app Settings panel
2. Enter API Key and Secret
3. Click "💾 Save Keys"
4. Click "✅ Validate & Sync"
   - Should show: "✅ Credentials validated and synced"

### Step 3: Enable Live Mode
1. Scroll to Controls section
2. Check "Enable Live Trading"
3. You'll see confirmation prompt
4. Click "ENABLE LIVE TRADING (I understand the risks)"
5. App now shows: 🔴 LIVE TRADING ACTIVE

### Step 4: Test with $2
1. In Controls → Test Live BUY (BTC/USDT)
2. Should execute and show in trade log
3. In Controls → Test Live SELL to close
4. If successful → ready for real trading!

---

## 📊 DAILY OPERATIONS

### Morning Checklist
- [ ] Check app is running
- [ ] Verify backend health: ✅ OK in settings
- [ ] Check overnight trades in trade log
- [ ] Review daily PnL
- [ ] Verify live mode still enabled

### During Trading
- Monitor portfolio value in UI
- Check recent trades executing correctly
- Watch for any Telegram alerts
- Verify orders complete within 1-2 seconds

### Evening Checklist
- Review daily summary
- Check if any losses near 5% limit
- If so, consider reducing trade size
- Look at PnL trends

### End of Day
- App auto-resets daily limits at UTC midnight
- Trade counter resets to 0
- Loss baseline resets to current equity
- Ready for new day

---

## ⚠️ SAFETY LIMITS - KNOW THESE!

| Limit | Value | What It Does |
|-------|-------|------------|
| Max Trade | $50 | Can never trade more than $50 in one order |
| Max Risk % | 1% | Order capped at 1% of current portfolio |
| Max Daily Trades | 20 | Can't execute more than 20 trades/day |
| Max Daily Loss | 5% | App auto-disables if lose > 5% today |
| Min Trade | $2 | Can't trade less than $2 |
| Allowed Symbols | BTC/USDT, ETH/USDT | Only these pairs allowed |

**These are HARD CODED and cannot be changed by users!**

---

## 🛡️ EMERGENCY PROCEDURES

### If You See "🛑 AUTO-DISABLED" Message
**What happened**: Daily loss > 5%  
**What to do**: 
1. App already switched to paper mode
2. Review trades that caused loss
3. Check for market bugs (flash crashes, etc)
4. Start fresh tomorrow (UTC midnight)

### If Backend Shows "❌ Backend health: failed"
**What happened**: Cannot connect to backend  
**What to do**:
1. Check backend server is running: `ps aux | grep node`
2. Check backend URL is correct in settings
3. Try http://localhost:8000/api/health in browser
4. If browser returns JSON: backend is OK, check firewall
5. If browser fails: backend is down, restart it

### If You Can't Enable Live Trading
**What happened**: Missing prerequisites  
**Check**:
1. ALLOW_LIVE=1 environment variable set
2. Backend shows ✅ OK health
3. Credentials show ✅ Validated
4. Browser console has no errors

### If Order Stuck/Not Executing
**What happened**: Exchange or network issue  
**What to do**:
1. Check recent trades in trade log
2. Check exchange status page
3. Wait 30 seconds, try again
4. If still fails, check order manually on exchange
5. Review logs for error details

### If App Crashes
**What happened**: Bug or resource issue  
**What to do**:
1. Check error message in terminal
2. Kill process: `pkill -f "streamlit run"`
3. Restart: `streamlit run app.py`
4. Review latest trade log for inconsistencies
5. Report error with timestamp + full message

---

## 📈 TRADING BEST PRACTICES

### Position Sizing
- Start with $2 minimum
- Build up to $5, $10, $20 as confidence grows
- Never exceed $50 per trade (hard limit)
- Keep portfolio risk at 1% per trade

### Daily Risk Management
- Start day with max daily loss = 5% of portfolio
- Example: $10,000 portfolio → max daily loss = $500
- If you hit $500 loss, app auto-disables
- This prevents catastrophic losses

### Strategy Selection
- SMA_Crossover: Good for trending markets
- RSI_Strategy: Good for mean reversion
- Both available in strategy selector
- Can backtest either before enabling live

### Backtesting Before Live
1. Select strategy
2. Run backtest
3. Review returns + sharpe ratio
4. If returns positive, confident to trade
5. If returns negative, tune parameters

---

## 🔍 MONITORING & LOGGING

### Where to Check Status
**UI Elements**:
- Portfolio Value: Top left metric
- Open Positions: Portfolio tab
- Recent Trades: Tab or right column
- Mode: "✅ Paper" or "🔴 Live" at bottom

**Files**:
- `state.json` - Current positions + trade log
- `.cryptopiggy/credentials.json` - Saved API keys
- Console output - Real-time logs

**Alerts**:
- Telegram messages (if configured)
- Trade execution confirmations
- Error warnings
- Daily limit breaches

### Reading Trade Log
```
🔴LIVE 2026-02-04T14:32:15.123456: BUY BTC/USDT $25.00
📝PAPER 2026-02-04T14:32:20.654321: SELL BTC/USDT $25.00
```

Legend:
- 🔴LIVE = real exchange order
- 📝PAPER = simulated paper trade
- Timestamp = when order executed
- Side = BUY or SELL
- Symbol = what was traded
- Amount = USD amount

---

## 💰 EXAMPLE: YOUR FIRST LIVE TRADES

### Scenario: $1,000 Portfolio, New to Live Trading

**Day 1 - Conservative**
```
Morning: Start with $1,000 equity
Trade 1: BUY $2 BTC/USDT @ $45,000 → fills
Trade 2: SELL $2 BTC/USDT @ $45,050 → fills +$0.22 profit ✅
Daily PnL: +$0.22 (0.02%)
Evening: Still have $1,000 (profit kept)
```

**Day 2 - Slightly Bigger**
```
Morning: Start with $1,000.22 equity
Trade 1: BUY $5 BTC/USDT @ $45,000
Trade 2: SELL $5 BTC/USDT @ $44,900 → fills -$5.56 loss ❌
Daily PnL: -$5.56 (-0.56%)
Confidence: Growing - only lost 0.56%!
Daily Loss Limit: -$50 still available (5% of $1,000)
```

**Day 3 - Building Confidence**
```
Morning: Start with $994.64 equity
Trade 1-5: Win 4, lose 1 → +$20 overall
Daily PnL: +$20 (+2.01%)
Evening: Portfolio now $1,014.64
Trend: ✅ Making money!
```

**Day 4 - Big Loss Day (Disaster Recovery)**
```
Morning: Start with $1,014.64 equity
Trade 1-15: Market flash crash, lose on most trades
Daily Loss: -$60 (5.92% of starting equity)
App Action: ✅ AUTO-DISABLES live mode, shows warning 🛑
Telegram: "AUTO-DISABLED: Daily loss 5.92% exceeded limit"
App Mode: Automatically switched to 📝 Paper mode
What You See: "🛑 AUTO-DISABLED" message
Action Needed: Wait until tomorrow, review what went wrong
```

---

## 🧪 VALIDATION CHECKLIST (Before Going Live)

Run before enabling live trading with real money:

```
❌→✅ Integration Tests
$ python test_integration.py
Expected: ✅ Tests Passed: 10/10 (100%)

❌→✅ Import All Modules
$ python -c "from crypto_piggy_top import *; print('OK')"
Expected: OK

❌→✅ Backend Health
Go to Settings → Backend URL should show: ✅ Backend health: OK

❌→✅ Credential Save
Settings → dummy keys → Save → Reload page → keys still there

❌→✅ Credential Validate
Settings → real keys → Validate & Sync → shows ✅ validated

❌→✅ Paper Trade
Controls → Run Backtest → completes with returns

❌→✅ Live Mode Toggle
Controls → Enable Live Trading → shows 🔴 LIVE TRADING ACTIVE

❌→✅ Test $2 Buy
Controls → Test Live BUY (BTC/USDT) → shows in trade log as 🔴LIVE

❌→✅ Test $2 Sell
Controls → Test Live SELL → closes position
```

If all ✅, you're ready!

---

## 📞 TROUBLESHOOTING TABLE

| Problem | Check | Fix |
|---------|-------|-----|
| App won't start | Python 3.10+, deps installed | `pip install -r requirements.txt` |
| Backend shows failed | Backend running, correct URL | Start backend or check URL |
| Can't save keys | Creds directory exists | Creates auto, but check permissions |
| Can't validate keys | Keys valid, network OK | Check exchange API key restrictions |
| Can't enable live | All guards pass? | Ensure ALLOW_LIVE=1 + backend ✅ |
| Order rejected | Daily limits? | Check daily trades + loss %. Wait if needed. |
| Order stuck | Network? Exchange? | Check backend logs, exchange status |
| Trade not in log | Recent trades display | Scroll down, check filters |
| App slow | Too many trades? | Restart, check logs for errors |
| High latency | Exchange, network | Monitor, consider smaller size |

---

## 📈 PERFORMANCE EXPECTATIONS

| Operation | Typical Time |
|-----------|-------------|
| App startup | 2-3 seconds |
| Page reload | < 1 second (session state cached) |
| Backtest (500 candles) | 200-500ms |
| Order placement | 1-3 seconds (exchange dependent) |
| Backend health check | 50-200ms |
| LSTM prediction | 500ms - 2s (first run longer) |

---

## 🔐 SECURITY REMINDERS

⚠️ **DO NOT**:
- Share your API keys
- Commit `.cryptopiggy/credentials.json` to git
- Run in untrusted network (especially with live keys)
- Enable live trading on borrowed computer
- Leave terminal window visible with API keys in history

✅ **DO**:
- Use API keys with SPOT trading only (no futures/margin)
- IP whitelist your current IP on exchange
- Disable API withdrawals
- Start with small amounts ($2-$5)
- Monitor daily PnL religiously
- Keep console running for logs
- Back up `state.json` and `.cryptopiggy/credentials.json`

---

## 📊 REPORTING & ANALYSIS

### Daily Summary
```python
# Check state.json after each day:
{
  "positions": {...},           # Current open positions
  "trade_log": [                # All trades today
    {
      "datetime": "2026-02-04T14:32:15",
      "side": "buy",
      "symbol": "BTC/USDT",
      "amount_usd": 25.00,
      "price": 45000.00,
      "live": true              # ← real or paper
    }
  ]
}

# Calculate daily PnL:
# = portfolio value tonight - portfolio value this morning
# If portfolio went 10,000 → 10,100 = +$100 profit
```

### Monthly Report
- Total trades executed
- Win rate (wins / total trades)
- Average winning trade size
- Average losing trade size
- Total monthly PnL
- Max drawdown
- Sharpe ratio (if backtest enabled)

---

## 🎯 SUCCESS CRITERIA

You'll know the app is working correctly when:

✅ Paper trades execute instantly  
✅ State persists across page refreshes  
✅ Daily limits auto-reset at midnight UTC  
✅ Live orders appear in trade log within 3 seconds  
✅ Telegram alerts fire on major events  
✅ Backend health shows ✅ OK  
✅ Credentials save and persist  
✅ Portfolio value updates  
✅ No errors in console logs  
✅ Backtest completes with realistic returns  

---

## 🚀 YOU ARE NOW READY!

Everything is set up correctly. Your first production trade is moments away!

**Remember**:
- Start small ($2-$5)
- Monitor closely first day
- Understand the limits
- Review trades daily
- Build confidence slowly

Good luck! 🎉

---

*For questions, review code comments and `.github/copilot-instructions.md` for AI agent guidance.*

*For production deployment, see `PRODUCTION_READY_CHECKLIST.md`.*
