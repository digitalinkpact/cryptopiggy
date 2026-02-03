# CryptoPiggy AI Agent Instructions

## Architecture Overview

CryptoPiggy is a cryptocurrency trading bot with dual interfaces: a Streamlit web UI ([app.py](../app.py)) and a CLI menu ([crypto_piggy_top.py](../crypto_piggy_top.py)). The core bot class `CryptoPiggyTop2026` manages strategies, backtesting, risk controls, and order execution with paper/live mode support.

**Data Flow**: Strategies consume OHLCV data → populate indicators/signals → backtest engine simulates trades with equity tracking → optionally ML-enhance signals → paper/live order execution → state.json persistence.

**Key Components:**
- **Strategy System**: Plugin-based strategies inherit from [BaseStrategy](../crypto_piggy_top.py#L33) (populate_indicators, populate_entry_trend, populate_exit_trend). Built-in: `SMA_Crossover` (L47), `RSI_Strategy` (L64).
- **LSTM Predictor**: PyTorch-based [LSTMPredictor](../crypto_piggy_top.py#L79) class for ML-enhanced signals via [predict_next_close_series()](../crypto_piggy_top.py#L502) with 50-bar lookback window.
- **Exchange Integration**: `ccxt` library handles multi-exchange connectivity; fallback to synthetic random walk data if unavailable via [fetch_ohlcv_df()](../crypto_piggy_top.py#L235).
- **Risk Management**: Position sizing, trailing stops, max drawdown, consecutive loss tracking in `risk_settings` dict.
- **State Persistence**: `state.json` stores positions, trade_log, and strategy params; loaded on init, saved only on explicit `save_state()` call.
- **Menu-driven CLI**: Interactive menu (option 1-8) in [menu()](../crypto_piggy_top.py#L582) method; option 7 runs simulated bot loop via [start_bot()](../crypto_piggy_top.py#L629).

## Safety & Live Trading Guardrails

**Critical**: Live mode requires multi-layered confirmation to prevent accidental real trades:
1. Environment flag: `ALLOW_LIVE=1` (checked via `_allow_live_env`)
2. Token confirmation: `LIVE_CONFIRM_TOKEN` env var or interactive "YES" prompt
3. Explicit call to [enable_live()](../crypto_piggy_top.py#L479) method
4. Symbol whitelist: `allowed_symbols` list (default: BTC/USDT,ETH/USDT via env var `ALLOWED_SYMBOLS`)
5. Dry-run flag: `--dry-run` CLI arg forces `self.dry_run = True` and paper mode

When modifying order execution ([place_order()](../crypto_piggy_top.py#L295)):
- **Always check** `is_live() AND not self.dry_run` before real exchange calls
- **Validate** symbol against `allowed_symbols` whitelist (triggers warning if not whitelisted)
- **Cap orders** by `max_position_pct` of equity (default 2%)
- **Use** [safe_ccxt_call()](../crypto_piggy_top.py#L262) wrapper for all exchange API calls (handles retries, rate limits, auth errors with exponential backoff)
- **Check** `min_trade_size_usd` (default $10) before attempting any order

## Development Workflows

### Running the Bot
```bash
# CLI menu (paper mode by default)
python crypto_piggy_top.py

# Dry-run mode (no real orders even if live enabled)
python crypto_piggy_top.py --dry-run

# Streamlit web UI (default port 8501, or via Docker)
streamlit run app.py

# Docker deployment
docker build -t cryptopiggy . && docker run -p 8501:8501 cryptopiggy
```

### Testing & Validation Workflow
1. **Backtest first**: Option 4 in CLI menu or `bot.backtest('strategy_name', 'BTC/USDT')` returns {total_return, max_dd, sharpe, equity_curve}
2. **Hyperparameter optimize**: Option 5 or `bot.hyperopt('sma_crossover', {'short_window': (5,20), 'long_window': (20,50)}, trials=20)`
3. **Simulate execution**: Option 7 (`start_bot()`) runs paper mode loop with synthetic/live OHLCV—useful to validate signal generation and state changes
4. **Validate state.json**: Check positions, trade_log, and strategy params persisted correctly after save

### Backtesting Pattern
```python
# In strategies: params dict controls behavior
strategy.params = {'short_window': 10, 'long_window': 30, 'timeframe': '5m'}

# Backtest returns dict with: total_return, max_dd, sharpe, equity_curve, positions
result = bot.backtest('sma_crossover', 'BTC/USDT', timeframe='5m', limit=300)
```

### Adding New Strategies
1. Inherit from [BaseStrategy](../crypto_piggy_top.py#L33) in crypto_piggy_top.py
2. Implement `populate_indicators()`, `populate_entry_trend()`, `populate_exit_trend()` methods
3. Use pandas_ta for indicators: `ta.sma()`, `ta.rsi()`, etc. (imported as `import pandas_ta as ta`)
4. Register in `bot.strategies` dict in `__init__()` (L99-104)
5. Strategy signals: set `df['entry']` and `df['exit']` boolean columns
6. Strategies are stateless; `params` dict passed via `self.strategies[name].params` controls behavior

Example:
```python
class MyStrategy(BaseStrategy):
    def populate_indicators(self, df):
        df['ema'] = ta.ema(df['close'], length=self.params.get('period', 20))
        return df
    
    def populate_entry_trend(self, df):
        df['entry'] = df['close'] > df['ema']
        return df
    
    def populate_exit_trend(self, df):
        df['exit'] = df['close'] < df['ema']
        return df

# Register in bot
bot.strategies['my_strategy'] = MyStrategy({'period': 20})
```

## Key Conventions

- **OHLCV Data**: `fetch_ohlcv_df()` returns pandas DataFrame with columns: `['datetime', 'open', 'high', 'low', 'close', 'volume']`. Falls back to synthetic random walk if exchange unavailable.
- **Logging**: Use module-level logger from `logging.getLogger()`. Format: `'%(asctime)s | %(levelname)s | %(message)s'`
- **Error Handling**: `safe_ccxt_call()` handles transient exchange errors (DDoS, rate limits, timeouts) with exponential backoff. Returns `None` on failure.
- **State Management**: Call `save_state()` after trades; `load_state()` on init restores positions/history.

## Integration Points

- **CCXT Exchange**: [setup_exchange()](../crypto_piggy_top.py#L137) initializes read-only mode without API keys. Use [configure_api_keys()](../crypto_piggy_top.py#L165) for live credentials; reinitializes exchange with new credentials.
- **Telegram Notifications**: Optional `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` env vars enable `send_telegram()` alerts for trade execution (L126 bot init, uses python-telegram-bot).
- **PyTorch ML**: LSTM model trains on-demand in [predict_next_close_series()](../crypto_piggy_top.py#L502) with 50-bar lookback window. Strategies enable via `params['use_ml'] = True` and use predictions in [start_bot()](../crypto_piggy_top.py#L629).
- **CLI Menu**: [menu()](../crypto_piggy_top.py#L582) loops through 8 options; option 7 calls `start_bot()` for simulation with configurable cycles.
- **Streamlit Web UI**: [app.py](../app.py) creates standalone bot instance, displays portfolio via `state.json`, runs backtests with equity curve visualization. Uses `@st.cache_resource` for exchange instances.

## Testing & Validation

- **Hyperopt**: `hyperopt()` method runs random search over param ranges, optimizes on backtest Sharpe ratio.
- **Streamlit UI**: [app.py](../app.py#L100-L122) includes backtest trigger with equity curve visualization.
- **Paper Mode Validation**: Default mode uses synthetic OHLCV and simulated fills; check `trade_log` for execution history.

## Common Gotchas

- **Optional Dependencies**: Some imports are wrapped in try/except (ccxt, telegram Bot) to allow graceful degradation; always check before use or log warnings if missing.
- **DataFrame Column Names**: Backtest loop and strategy signals expect exact column names: `['datetime', 'open', 'high', 'low', 'close', 'volume']` plus computed columns like `['entry', 'exit', 'sma_short', etc.]`.
- **Indicator Alignment**: pandas_ta returns aligned series; ensure `dropna()` before strategy signals to avoid NaN entries.
- **Timeframe Mismatch**: Strategy `params['timeframe']` must match backtest `timeframe` arg for correct bar alignment.
- **State Persistence**: `state.json` is only written on explicit `save_state()` call or menu option 6. Not automatic on every trade.
- **Exchange Public vs Private**: Without API keys, exchange only supports public methods (fetch_ticker, fetch_ohlcv). `createOrder` disabled until credentials configured via [configure_api_keys()](../crypto_piggy_top.py#L165).
- **LSTM Training Overhead**: [predict_next_close_series()](../crypto_piggy_top.py#L502) trains fresh model each call (5 epochs by default)—costly for frequent calls; cache if needed.
- **Synthetic Data Fallback**: [fetch_ohlcv_df()](../crypto_piggy_top.py#L235) generates random walk if exchange unavailable; paper mode always uses this for backtesting.
- **Order Placement Guards**: [place_order()](../crypto_piggy_top.py#L295) checks min_trade_size_usd, symbol whitelist, and max_position_pct BEFORE attempting live/paper execution.
- **Dry-Run vs Paper Mode**: `--dry-run` flag forces both `dry_run=True` AND `paper_mode=True` at CLI startup (parsed in `__main__`). Useful for testing order logic without state changes.
- **Streaming vs Batch**: Streamlit app instantiates a fresh `CryptoPiggyTop2026()` on each run (unless cached); use `@st.cache_resource` for expensive operations like exchange setup.
