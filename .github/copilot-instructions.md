# CryptoPiggy AI Agent Instructions

## Big picture
- **Core engine**: `CryptoPiggyTop2026` in [crypto_piggy_top.py](../crypto_piggy_top.py) handles strategies, backtest, risk controls, orders, and state.
- **UIs**: Two Streamlit apps:
  - [app.py](../app.py): Lightweight preview UI
  - [app_new.py](../app_new.py): Production UI with persistent `st.session_state` bot instance
- **Data flow**: OHLCV fetch → strategy indicators/signals → backtest/loop → `place_order()` → `state.json` persistence
- **Architecture**: Bot can operate in 3 modes: paper (default), live via backend proxy, or live via direct `ccxt` exchange calls

## Safety & live trading guardrails (NEVER bypass)
- Live mode requires ALL of: `ALLOW_LIVE=1` env var, exchange/backend configured, user confirmation, `bot.live_confirmed=True`
- `--dry-run` CLI flag forces paper mode regardless of settings
- `place_order()` enforces:
  - `allowed_symbols` whitelist (default: `BTC/USDT`, `ETH/USDT`)
  - Hard caps: `MAX_TRADE_USD=50`, `MAX_PORTFOLIO_RISK_PCT=0.01`, `MAX_DAILY_TRADES=20`, `MAX_DAILY_LOSS_PCT=0.05`
  - `_check_daily_limits()` auto-disables live trading if limits breached (switches to paper + Telegram alert)
- ALWAYS check `bot.is_live()` before any order creation logic
- All `ccxt` calls MUST use `safe_ccxt_call()` wrapper (handles retries, rate limits, transient errors)

## Key conventions
- **OHLCV schema**: Columns MUST be `['datetime','open','high','low','close','volume']` (exact names)
- **Strategy pattern**: Subclass `BaseStrategy`, implement `populate_indicators()`, `populate_entry_trend()`, `populate_exit_trend()`
  - Set `df['entry']` and `df['exit']` as boolean columns (see `SMA_Crossover`, `RSI_Strategy`)
  - Strategy `params['timeframe']` must match backtest timeframe for indicator alignment
- **LSTM**: `predict_next_close_series()` does per-call training (50-bar window) → AVOID calling in tight loops
- **State persistence**: Only via explicit `save_state()` (JSON file); `load_state()` runs on bot init
- **Streamlit session state**: Bot and credentials MUST be stored in `st.session_state` to survive reruns (see [app_new.py](../app_new.py) pattern)

## Backend proxy integration (essential for live trading)
- **Config sources** (precedence): `.cryptopiggy/credentials.json` → env vars → defaults
- **Health check**: `check_backend_health(url)` → `GET /api/health` (expect 200)
- **Credential sync**: `sync_credentials(url, payload)` → `POST /api/credentials` (validates API keys)
  - Success indicators: `ok=True`, `canTrade=True`, `validated=True`, `status='ok'|'success'`, OR `status_code=200 && error=None`
- **Order placement**: `place_order_backend(side, symbol, amount_usd)` → `POST /api/trade`
  - **Symbol normalization**: Backend expects `BTCUSDT` (no `/`), CCXT uses `BTC/USDT`
- **Balance fetch**: `fetch_backend_balance(url, user_id)` → `GET /api/balance/{userId}`
- Backend is optional; falls back to direct `ccxt` or paper mode if unavailable

## Credential persistence
- **File**: `.cryptopiggy/credentials.json` (created by UI)
- **Fields**: `user_id`, `exchange`, `api_key`, `api_secret`, `backend_url`, `validated` (boolean)
- `validated` flag set only after successful `/api/credentials` sync
- Streamlit: Keep in `st.session_state.creds` to avoid disk I/O on every rerun

## Developer workflows
- **CLI**:
  - Paper mode: `python crypto_piggy_top.py`
  - Dry-run: `python crypto_piggy_top.py --dry-run`
  - Interactive menu: runs automatically, includes backtest/hyperopt/live enable
- **Streamlit**:
  - Preview UI: `streamlit run app.py`
  - Production UI: `streamlit run app_new.py` (recommended - persists state)
- **Testing**:
  - Validation: `python test_app.py` (unit tests)
  - Live setup: `python test_live_trading.py` (prerequisite checker)
  - Integration: `python test_integration.py` (comprehensive test suite)
  - Pattern: Import bot once at module level (avoids re-initialization)
- **Environment**:
  - Required: `pip install -r requirements.txt`
  - Optional backend: expects `http://localhost:8000` with `/api/health`, `/api/credentials`, `/api/trade`, `/api/balance/:userId`

## Integration points
- **Exchange**: `setup_exchange()` initializes `ccxt` (optional, wrapped in try/except)
- **CCXT**: `safe_ccxt_call(method, *args, **kwargs)` handles:
  - Transient errors: `DDoSProtection`, `RequestTimeout`, `NetworkError`, `ExchangeNotAvailable`
  - Rate limits: Exponential backoff for `RateLimitExceeded`
  - Auth errors: Fail immediately on `Authentication*` errors
- **Telegram**: `send_telegram(msg)` when `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` set
- **Order execution path** (priority order):
  1. Live backend: `place_order_backend()` if `backend_enabled=True` and live mode
  2. Live CCXT: `exchange.create_order()` via `safe_ccxt_call()` if live mode and exchange configured
  3. Paper mode: Local simulation (default)

## Testing patterns
- **Bot instance**: Create once at module level, reuse across tests (see [test_app.py](../test_app.py))
  ```python
  bot = CryptoPiggyTop2026()  # Module-level
  def test_something():
      assert bot.paper_mode == True
  ```
- **Streamlit mocking**: Tests don't actually run Streamlit, just import components
- **Daily limits**: `test_3_daily_limits()` in [test_integration.py](../test_integration.py) validates `_check_daily_limits()` logic

## Common gotchas
- Without API keys, exchanges are read-only (no `create_order` method available)
- `state.json` drives UI portfolio/history but isn't auto-updated on every action
- Streamlit reruns on every input; without `st.session_state`, bot recreates from scratch (loses trades/positions)
- Backend validation responses vary widely; check multiple success fields (see credential sync logic)
- Symbol format differs: CCXT uses `BTC/USDT`, some exchanges/backends use `BTCUSDT`
- LSTM training is expensive; synthetic OHLCV data is generated when exchange fetch fails (for testing)
