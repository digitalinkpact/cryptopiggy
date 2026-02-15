import time
import json
import os
import logging
import sys
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
import torch.optim as optim
import pandas_ta as ta
from collections import deque

# Optional requests for backend proxy integration
try:
    import requests
except Exception:
    requests = None

# Optional imports (some users may not install ccxt or telegram)
try:
    import ccxt
except Exception:
    ccxt = None

try:
    from telegram import Bot
except Exception:
    Bot = None

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("CryptoPiggyTop")

# PRODUCTION SAFETY LIMITS (cannot be overridden without code changes)
MAX_TRADE_USD = 50.0  # Hard limit per trade
MAX_PORTFOLIO_RISK_PCT = 0.01  # Maximum 1% of portfolio per trade
MAX_DAILY_TRADES = 20  # Prevent runaway bot
MAX_DAILY_LOSS_PCT = 0.05  # Auto-disable if daily loss exceeds 5%


class BaseStrategy:
    def __init__(self, params=None):
        self.params = params or {}

    def populate_indicators(self, df):
        raise NotImplementedError

    def populate_entry_trend(self, df):
        raise NotImplementedError

    def populate_exit_trend(self, df):
        raise NotImplementedError


class SMA_Crossover(BaseStrategy):
    def populate_indicators(self, df):
        short = int(self.params.get('short_window', 10))
        long = int(self.params.get('long_window', 30))
        df['sma_short'] = ta.sma(df['close'], length=short)
        df['sma_long'] = ta.sma(df['close'], length=long)
        return df

    def populate_entry_trend(self, df):
        df['entry'] = (df['sma_short'] > df['sma_long']) & (df['sma_short'].shift(1) <= df['sma_long'].shift(1))
        return df

    def populate_exit_trend(self, df):
        df['exit'] = (df['sma_short'] < df['sma_long']) & (df['sma_short'].shift(1) >= df['sma_long'].shift(1))
        return df


class RSI_Strategy(BaseStrategy):
    def populate_indicators(self, df):
        period = int(self.params.get('rsi_period', 14))
        df['rsi'] = ta.rsi(df['close'], length=period)
        return df

    def populate_entry_trend(self, df):
        df['entry'] = df['rsi'] < 30
        return df

    def populate_exit_trend(self, df):
        df['exit'] = df['rsi'] > 70
        return df


class LSTMPredictor(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(1, 64, 2, batch_first=True)
        self.fc = nn.Linear(64, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


class CryptoPiggyTop2026:
    def __init__(self):
        self.paper_mode = True
        self.live_confirmed = False
        self.exchange_name = os.getenv('EXCHANGE', 'paper')
        self.exchange = None
        # Backend proxy integration
        self.backend_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
        self.backend_user_id = os.getenv('BACKEND_USER_ID')
        self.backend_enabled = False
        self.backend_last_health = None
        try:
            self.backend_timeout = float(os.getenv('BACKEND_TIMEOUT', '5'))
        except Exception:
            self.backend_timeout = 5.0
        # Live confirmation guards
        self._live_confirm_token = os.getenv('LIVE_CONFIRM_TOKEN')
        self._allow_live_env = os.getenv('ALLOW_LIVE') == '1'
        # CLI or runtime dry-run flag (set in __main__)
        self.dry_run = False
        # Allowed trade symbols (safety)
        self.allowed_symbols = os.getenv('ALLOWED_SYMBOLS', 'BTC/USDT,ETH/USDT').split(',')
        self.positions = {}
        self.trade_log = []
        self.signal_log = deque(maxlen=100)
        self.coins = ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']
        self.strategies = {
            'sma_crossover': SMA_Crossover({'short_window': 10, 'long_window': 30}),
            'rsi': RSI_Strategy({'rsi_period': 14}),
        }
        self.active_strategy = 'sma_crossover'
        self.running = False
        self.consec_losses = 0
        self.peak_equity = 0.0
        self.daily_trades_count = 0
        self.daily_start_equity = 0.0
        self.last_trade_reset_day = datetime.utcnow().day
        self.risk_settings = {
            'max_position_pct': min(0.01, MAX_PORTFOLIO_RISK_PCT),
            'trailing_stop_pct': 0.02,
            'max_dd_pct': 0.20,
            'max_consec_loss': 5,
            'min_trade_size_usd': 2.0,
            'max_trade_size_usd': MAX_TRADE_USD,
        }
        self.lstm_model = LSTMPredictor()
        self.scaler = MinMaxScaler()
        self.optimizer = optim.Adam(self.lstm_model.parameters(), lr=0.0008)
        self.criterion = nn.MSELoss()
        self.telegram_bot = None
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if self.telegram_token and Bot is not None:
            try:
                self.telegram_bot = Bot(self.telegram_token)
                logger.info("Telegram bot initialized.")
            except Exception:
                self.telegram_bot = None
        self.load_state()
        self.peak_equity = self.get_equity()
        self.daily_start_equity = self.peak_equity

    def setup_exchange(self):
        """Initialize exchange connection with safety checks."""
        if ccxt is None:
            logger.warning("ccxt not installed; running in paper mode only.")
            self.exchange = None
            return
        
        try:
            if self.exchange_name.lower() == 'paper':
                self.exchange = None
                return
            elif self.exchange_name.lower() in ['binance', 'binanceus']:
                exchange_class = ccxt.binance
            elif hasattr(ccxt, self.exchange_name):
                exchange_class = getattr(ccxt, self.exchange_name)
            else:
                logger.error(f"Unknown exchange: {self.exchange_name}")
                self.exchange = None
                return
            
            api_key = os.getenv('EXCHANGE_API_KEY') or os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('EXCHANGE_API_SECRET') or os.getenv('BINANCE_API_SECRET')
            
            if api_key and api_secret:
                self.exchange = exchange_class({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'},
                })
                logger.info(f"Exchange {self.exchange_name} initialized with API credentials")
            else:
                self.exchange = exchange_class({'enableRateLimit': True})
                logger.warning('Exchange initialized in read-only mode (no API keys)')
                
        except Exception as e:
            logger.exception("Failed to setup exchange: %s", e)
            self.exchange = None

    def configure_api_keys(self):
        """Interactively configure API keys for live trading."""
        print("\n" + "="*60)
        print("⚠️  WARNING: CONFIGURING LIVE TRADING CREDENTIALS")
        print("="*60)
        print("You are about to enter API keys for REAL money trading.")
        print("Make sure you:")
        print("  1. Use API keys with SPOT trading only (no margin/futures)")
        print("  2. Set IP whitelist restrictions on your exchange")
        print("  3. Enable withdrawal restrictions")
        print("  4. Start with small amounts for testing")
        print("="*60 + "\n")
        
        proceed = input("Type 'I UNDERSTAND THE RISKS' to continue: ").strip()
        if proceed != 'I UNDERSTAND THE RISKS':
            print("Cancelled.")
            return False
        
        exchange_name = input("Exchange name (binance/kraken/coinbasepro): ").strip().lower()
        if not exchange_name:
            print("Cancelled.")
            return False
            
        api_key = input("API Key: ").strip()
        api_secret = input("API Secret: ").strip()
        
        if not api_key or not api_secret:
            print("❌ API keys cannot be empty. Cancelled.")
            return False
        
        os.environ['EXCHANGE'] = exchange_name
        os.environ['EXCHANGE_API_KEY'] = api_key
        os.environ['EXCHANGE_API_SECRET'] = api_secret
        self.exchange_name = exchange_name
        
        try:
            if hasattr(ccxt, exchange_name):
                test_exchange = getattr(ccxt, exchange_name)({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                })
                balance = test_exchange.fetch_balance()
                if balance:
                    print(f"✅ Connection successful! Exchange {exchange_name} configured.")
                    self.exchange = test_exchange
                    logger.info("Exchange %s configured with API keys", exchange_name)
                    return True
                else:
                    print("❌ Failed to fetch balance. Check credentials.")
                    return False
            else:
                print(f"❌ Exchange {exchange_name} not found in ccxt.")
                return False
        except Exception as e:
            logger.exception("Failed to configure exchange: %s", e)
            print(f"❌ Failed to configure exchange: {e}")
            return False

    def is_live(self):
        """Check if bot is in live trading mode with all safety checks passed."""
        if self.backend_enabled:
            backend_ok = self.backend_last_health is not False
        else:
            backend_ok = True
        return (not self.paper_mode and 
                self.live_confirmed and 
                (self.exchange is not None or self.backend_enabled) and
                not self.dry_run and
                backend_ok)

    def set_backend(self, user_id, url=None, enabled=True):
        """Configure backend proxy settings."""
        self.backend_user_id = user_id
        if url:
            self.backend_url = url
        self.backend_enabled = bool(enabled)

    def check_backend_health(self):
        """Ping backend health endpoint and cache status."""
        if not self.backend_url or requests is None:
            self.backend_last_health = False
            return False
        try:
            resp = requests.get(f"{self.backend_url}/api/health", timeout=self.backend_timeout)
            self.backend_last_health = resp.status_code == 200
            return self.backend_last_health
        except Exception:
            self.backend_last_health = False
            return False

    def sync_credentials(self, api_key, api_secret, exchange='binanceus'):
        """Sync credentials to backend for validation and live trading."""
        if requests is None or not self.backend_url:
            return {'ok': False, 'error': 'requests_unavailable_or_no_backend'}
        if not self.backend_user_id:
            return {'ok': False, 'error': 'missing_user_id'}
        payload = {
            'userId': self.backend_user_id,
            'exchange': exchange,
            'apiKey': api_key,
            'apiSecret': api_secret
        }
        try:
            resp = requests.post(f"{self.backend_url}/api/credentials", json=payload, timeout=self.backend_timeout)
            data = resp.json() if resp.content else {}
            data['status_code'] = resp.status_code
            return data
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def fetch_backend_balance(self):
        """Fetch live balance via backend proxy."""
        if requests is None or not self.backend_url or not self.backend_user_id:
            return None
        try:
            resp = requests.get(f"{self.backend_url}/api/balance/{self.backend_user_id}", timeout=self.backend_timeout)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def place_order_backend(self, side, symbol, amount_usd, exchange='binanceus'):
        """Place order through backend proxy."""
        if requests is None or not self.backend_url or not self.backend_user_id:
            return None
        normalized_symbol = symbol
        if exchange and exchange.lower().replace('.', '') in ['binanceus', 'binance_us', 'binanceus']:
            normalized_symbol = symbol.replace('/', '')
        payload = {
            'userId': self.backend_user_id,
            'exchange': exchange,
            'side': side,
            'symbol': normalized_symbol,
            'symbolCcxt': symbol,
            'amountUsd': amount_usd
        }
        try:
            resp = requests.post(f"{self.backend_url}/api/trade", json=payload, timeout=self.backend_timeout)
            if resp.status_code == 200:
                return resp.json()
            return {'error': f"backend_trade_failed_{resp.status_code}", 'body': resp.text}
        except Exception as e:
            return {'error': str(e)}

    def get_equity(self):
        """Get current portfolio value (USD equivalent)."""
        if self.is_live() and ccxt is not None:
            try:
                bal = self.safe_ccxt_call('fetch_balance')
                if not bal:
                    logger.warning("Failed to fetch live balance")
                    return 0.0
                
                total = 0.0
                if isinstance(bal, dict) and 'total' in bal:
                    for currency, amount in bal['total'].items():
                        if isinstance(amount, (int, float)) and amount > 0:
                            if currency in ['USDT', 'USD', 'USDC']:
                                total += float(amount)
                            else:
                                try:
                                    ticker = self.safe_ccxt_call('fetch_ticker', f'{currency}/USDT')
                                    if ticker and 'last' in ticker:
                                        total += float(amount) * float(ticker['last'])
                                except Exception:
                                    pass
                return total
            except Exception as e:
                logger.exception("Error fetching live equity: %s", e)
                return 0.0
        else:
            total = 10000.0
            for sym, pos in self.positions.items():
                price = pos.get('price', 50000)
                qty = pos.get('qty', 0)
                total += qty * price
            return total

    def fetch_ohlcv_df(self, symbol, timeframe='5m', limit=300):
        """Fetch OHLCV data from exchange or generate synthetic for testing."""
        if ccxt is not None and self.exchange is not None:
            try:
                ohlcv = self.safe_ccxt_call('fetch_ohlcv', symbol, timeframe, limit=limit)
                if ohlcv and len(ohlcv) > 0:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                    return df
            except Exception as e:
                logger.warning(f"Failed to fetch OHLCV from exchange: {e}, using synthetic data")

        logger.info(f"Generating synthetic OHLCV data for {symbol}")
        end = datetime.utcnow()
        delta = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440}.get(timeframe, 5)
        dates = [end - timedelta(minutes=delta * i) for i in reversed(range(limit))]
        prices = np.cumsum(np.random.normal(loc=0, scale=1, size=limit)) + 50000
        df = pd.DataFrame({
            'datetime': dates,
            'open': prices + np.random.normal(0, 5, size=limit),
            'high': prices + np.abs(np.random.normal(0, 10, size=limit)),
            'low': prices - np.abs(np.random.normal(0, 10, size=limit)),
            'close': prices,
            'volume': np.abs(np.random.normal(100, 50, size=limit))
        })
        return df

    def safe_ccxt_call(self, method_name, *args, max_retries: int = 3, backoff: float = 0.5, **kwargs):
        """Call ccxt exchange method with retry logic and error handling."""
        if self.exchange is None:
            return None
        
        for attempt in range(1, max_retries + 1):
            try:
                method = getattr(self.exchange, method_name, None)
                if method is None:
                    logger.error(f"Exchange has no method {method_name}")
                    return None
                return method(*args, **kwargs)
            except Exception as e:
                error_name = e.__class__.__name__
                
                if any(x in error_name for x in ['DDoSProtection', 'ExchangeNotAvailable', 'RequestTimeout', 'NetworkError']):
                    logger.warning(f"Transient error on {method_name} attempt {attempt}/{max_retries}: {e}")
                    if attempt < max_retries:
                        time.sleep(backoff * attempt)
                        continue
                
                elif any(x in error_name for x in ['RateLimitExceeded', 'TooManyRequests']):
                    logger.warning(f"Rate limit hit on {method_name}, backing off: {e}")
                    if attempt < max_retries:
                        time.sleep(backoff * attempt * 2)
                        continue
                
                elif 'Authentication' in error_name:
                    logger.error(f"Authentication error on {method_name}: {e}")
                    return None
                
                else:
                    logger.exception(f"Uncaught exception calling {method_name}: {e}")
                    return None
        
        logger.error(f"Exceeded retries for {method_name}")
        return None

    def _check_daily_limits(self):
        """Check if daily trading limits allow another order."""
        # Reset daily counters if day has changed
        current_day = datetime.utcnow().day
        if current_day != self.last_trade_reset_day:
            self.daily_trades_count = 0
            self.daily_start_equity = self.get_equity()
            self.last_trade_reset_day = current_day
            logger.info(f"Daily limits reset for new day. Daily equity baseline: ${self.daily_start_equity:,.2f}")
        
        # Check trade count limit
        if self.daily_trades_count >= MAX_DAILY_TRADES:
            logger.error(f"Daily trade limit reached: {self.daily_trades_count}/{MAX_DAILY_TRADES}")
            return False
        
        # Check daily loss limit
        current_equity = self.get_equity()
        if self.daily_start_equity > 0:
            daily_loss_pct = (self.daily_start_equity - current_equity) / self.daily_start_equity
            if daily_loss_pct > MAX_DAILY_LOSS_PCT:
                logger.error(f"Daily loss limit exceeded: {daily_loss_pct:.2%} > {MAX_DAILY_LOSS_PCT:.2%}")
                self.paper_mode = True
                self.live_confirmed = False
                self.send_telegram(f"🛑 AUTO-DISABLED: Daily loss {daily_loss_pct:.2%} exceeded limit. Switched to paper mode.")
                return False
        
        return True

    def place_order(self, side, symbol, amount_usd):
        """Place order with comprehensive safety checks."""
        # Check daily limits first
        if not self._check_daily_limits():
            logger.error("Order rejected: daily limits exceeded")
            return None
        
        # Validate side
        side = side.lower()
        if side not in ['buy', 'sell']:
            logger.error(f"Invalid order side: {side}")
            return None
        
        # Symbol whitelist check
        if symbol not in self.allowed_symbols:
            logger.error(f"Symbol {symbol} not in allowed whitelist: {self.allowed_symbols}")
            return None
        
        # Minimum trade size
        min_size = self.risk_settings.get('min_trade_size_usd', 10.0)
        if amount_usd < min_size:
            logger.warning(f'Order ${amount_usd:.2f} below minimum ${min_size:.2f} - rejected')
            return None
        
        # Maximum trade size (HARD LIMIT)
        max_size = min(
            self.risk_settings.get('max_trade_size_usd', MAX_TRADE_USD),
            MAX_TRADE_USD
        )
        if amount_usd > max_size:
            logger.warning(f'Order ${amount_usd:.2f} exceeds maximum ${max_size:.2f} - capping')
            amount_usd = max_size
        
        # Portfolio risk limit
        equity = self.get_equity()
        if equity > 0:
            max_allowed = equity * min(
                self.risk_settings.get('max_position_pct', MAX_PORTFOLIO_RISK_PCT),
                MAX_PORTFOLIO_RISK_PCT
            )
            if amount_usd > max_allowed:
                logger.warning(f'Order ${amount_usd:.2f} exceeds portfolio risk limit ${max_allowed:.2f} - capping')
                amount_usd = max_allowed
        
        # Get current price
        price = 50000.0  # Default for paper mode
        if self.exchange is not None:
            ticker = self.safe_ccxt_call('fetch_ticker', symbol)
            if ticker and 'last' in ticker:
                price = float(ticker['last'])
        
        qty = amount_usd / price
        
        # LIVE TRADING PATH
        if self.is_live() and self.backend_enabled and self.backend_url and self.backend_user_id:
            logger.info(f"🔴 LIVE BACKEND ORDER: {side.upper()} {symbol} ${amount_usd:.2f}")
            backend_order = self.place_order_backend(side, symbol, amount_usd, exchange=self.exchange_name)
            if backend_order and not backend_order.get('error'):
                self.daily_trades_count += 1
                order_id = backend_order.get('orderId') or backend_order.get('id')
                price = float(backend_order.get('price') or backend_order.get('avgPrice') or price)
                self.trade_log.append({
                    'time': time.time(),
                    'datetime': datetime.utcnow().isoformat(),
                    'side': side,
                    'symbol': symbol,
                    'amount_usd': amount_usd,
                    'qty': qty,
                    'price': price,
                    'live': True,
                    'order_id': order_id,
                    'status': backend_order.get('status', 'submitted')
                })
                if side == 'buy':
                    self.positions[symbol] = {'qty': qty, 'price': price, 'entry_time': time.time()}
                elif side == 'sell' and symbol in self.positions:
                    del self.positions[symbol]
                self.send_telegram(f"✅ LIVE {side.upper()} (backend): {qty:.6f} {symbol} @ ${price:.2f}")
                self.save_state()
                return backend_order
            logger.error("Live backend order failed")
            return None

        if self.is_live() and self.exchange is not None:
            try:
                logger.info(f"🔴 LIVE ORDER: {side.upper()} {qty:.6f} {symbol} @ ${price:.2f} (${amount_usd:.2f})")
                
                # Create market order
                order = self.safe_ccxt_call(
                    'create_order',
                    symbol,
                    'market',
                    side,
                    qty
                )
                
                if order:
                    logger.info(f"✅ Live order executed: {order.get('id', 'unknown')}")
                    self.daily_trades_count += 1
                    
                    # Log trade
                    self.trade_log.append({
                        'time': time.time(),
                        'datetime': datetime.utcnow().isoformat(),
                        'side': side,
                        'symbol': symbol,
                        'amount_usd': amount_usd,
                        'qty': qty,
                        'price': price,
                        'live': True,
                        'order_id': order.get('id'),
                        'status': order.get('status')
                    })
                    
                    # Send notification
                    self.send_telegram(f"✅ LIVE {side.upper()}: {qty:.6f} {symbol} @ ${price:.2f}")
                    
                    self.save_state()
                    return order
                else:
                    logger.error("Live order failed: no response from exchange")
                    return None
                    
            except Exception as e:
                logger.exception(f"Failed to place live order: {e}")
                self.send_telegram(f"🚨 ORDER FAILED: {side} {symbol} - {str(e)[:100]}")
                return None
        
        # PAPER TRADING PATH
        else:
            if side == 'buy':
                self.positions[symbol] = {'qty': qty, 'price': price, 'entry_time': time.time()}
                logger.info(f"📝 Paper BUY: {qty:.6f} {symbol} @ ${price:.2f} (${amount_usd:.2f})")
            else:
                if symbol in self.positions:
                    entry_price = self.positions[symbol].get('price', price)
                    pnl = (price - entry_price) / entry_price if entry_price > 0 else 0
                    logger.info(f"📝 Paper SELL: {qty:.6f} {symbol} @ ${price:.2f} (PnL: {pnl:.2%})")
                    del self.positions[symbol]
                else:
                    logger.warning(f"Cannot sell {symbol}: no position")
                    return None
            
            self.trade_log.append({
                'time': time.time(),
                'datetime': datetime.utcnow().isoformat(),
                'side': side,
                'symbol': symbol,
                'amount_usd': amount_usd,
                'qty': qty,
                'price': price,
                'live': False
            })
            
            return {'status': 'paper', 'side': side, 'symbol': symbol, 'amount': qty}

    def backtest(self, strategy_name, symbol='BTC/USDT', timeframe='1h', limit=500):
        if strategy_name not in self.strategies:
            print("Invalid strategy.")
            return
        strategy = self.strategies[strategy_name]
        df = self.fetch_ohlcv_df(symbol, timeframe, limit)
        if df is None or df.empty:
            print("No data.")
            return
        # Allow strategies to use multiple timeframes via params
        tf = self.strategies[strategy_name].params.get('timeframe', timeframe)
        df = strategy.populate_indicators(df)
        df = strategy.populate_entry_trend(df)
        df = strategy.populate_exit_trend(df)

        # Simulate simple position sizing and trades
        initial_cash = 10000.0
        cash = initial_cash
        position = 0.0
        position_entry_price = 0.0
        equity_curve = []
        strategy_returns = []
        positions = []

        use_ml = self.strategies[strategy_name].params.get('use_ml', False)
        # Precompute ML prediction once on whole series (lightweight)
        ml_predictions = None
        if use_ml and hasattr(self, 'lstm_model'):
            try:
                ml_predictions = self.predict_next_close_series(df['close'].values)
            except Exception:
                ml_predictions = None

        for idx in range(len(df)):
            row = df.iloc[idx]
            price = float(row['close'])
            entry_signal = bool(row.get('entry', False))
            exit_signal = bool(row.get('exit', False))

            ml_signal = False
            if ml_predictions is not None and idx < len(ml_predictions):
                ml_pred = ml_predictions[idx]
                ml_signal = ml_pred > price

            combined_entry = entry_signal and (ml_signal if use_ml else True)

            # Entry: buy with a fraction of cash
            if combined_entry and position == 0:
                alloc = self.risk_settings.get('max_position_pct', 0.02)
                amount_usd = cash * alloc
                if amount_usd >= self.risk_settings.get('min_trade_size_usd', 10.0):
                    qty = amount_usd / price
                    position = qty
                    position_entry_price = price
                    cash -= qty * price
                    positions.append({'idx': idx, 'side': 'buy', 'price': price, 'qty': qty})

            # Exit: sell entire position
            if exit_signal and position > 0:
                cash += position * price
                positions.append({'idx': idx, 'side': 'sell', 'price': price, 'qty': position})
                position = 0.0
                position_entry_price = 0.0

            # Update equity
            equity = cash + position * price
            equity_curve.append(equity)

            # strategy return for this step (pct change of equity)
            if len(equity_curve) > 1:
                prev = equity_curve[-2]
                ret = (equity - prev) / prev if prev != 0 else 0.0
            else:
                ret = 0.0
            strategy_returns.append(ret)

        # Compute metrics
        cum_returns = np.array(equity_curve) / initial_cash - 1
        total_return = float(cum_returns[-1]) if len(cum_returns) > 0 else 0.0
        peak = np.maximum.accumulate(cum_returns)
        drawdowns = peak - cum_returns
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        # Sharpe ratio approximation
        rets = np.array(strategy_returns)
        if rets.std() != 0:
            # Annualize assuming timeframe minutes
            minutes = {'1m': 1, '5m': 5, '15m': 15, '1h': 60}.get(tf, 60)
            periods_per_day = 24 * 60 / minutes
            annual_factor = np.sqrt(252 * periods_per_day)
            sharpe = float(rets.mean() / (rets.std() + 1e-9) * annual_factor)
        else:
            sharpe = 0.0

        print(f"Backtest results: Total Return {total_return:.2%}, Max DD {max_dd:.2%}, Sharpe {sharpe:.2f}")
        return {
            'total_return': total_return,
            'max_dd': max_dd,
            'sharpe': sharpe,
            'equity_curve': equity_curve,
            'positions': positions
        }

    def hyperopt(self, strategy_name, param_ranges, trials=20):
        if strategy_name not in self.strategies:
            print("Invalid.")
            return
        best_score = -np.inf
        best_params = {}
        for _ in range(trials):
            params = {}
            for k, v in param_ranges.items():
                if isinstance(v[0], int) and isinstance(v[1], int):
                    params[k] = int(np.random.randint(v[0], v[1] + 1))
                else:
                    params[k] = float(np.random.uniform(v[0], v[1]))
            self.strategies[strategy_name].params = params
            score = self.backtest(strategy_name)
            if score is not None and score > best_score:
                best_score = score
                best_params = params
        self.strategies[strategy_name].params = best_params
        print(f"Best params: {best_params} with score {best_score:.2%}")

    def send_telegram(self, message):
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if self.telegram_bot and chat_id:
            try:
                self.telegram_bot.send_message(chat_id, message)
            except Exception:
                logger.exception("Failed to send telegram message")

    def status(self):
        """Display current bot status."""
        mode = "🔴 LIVE" if self.is_live() else "✅ PAPER"
        print("\n" + "="*60)
        print(f"CryptoPiggy Status - {mode}")
        print("="*60)
        print(f"Active Strategy: {self.active_strategy}")
        print(f"Equity: ${self.get_equity():,.2f}")
        print(f"Open Positions: {len(self.positions)}")
        print(f"Total Trades: {len(self.trade_log)}")
        print(f"Daily Trades: {self.daily_trades_count}/{MAX_DAILY_TRADES}")
        print(f"Consecutive Losses: {self.consec_losses}")
        if self.is_live():
            print(f"⚠️  LIVE TRADING ENABLED - Real money at risk!")
        print("="*60 + "\n")

    def enable_live(self):
        """Enable live trading mode with safety checks."""
        if ccxt is None:
            print("❌ ccxt not available; cannot enable live mode")
            return False
        
        if not self._allow_live_env:
            print('❌ LIVE mode not allowed: Set ALLOW_LIVE=1 environment variable')
            return False
        
        if self.exchange is None:
            print('❌ No exchange configured. Run option 2 to configure API keys.')
            return False
        
        # Confirmation prompt
        print("\n" + "="*60)
        print("⚠️  ENABLING LIVE TRADING MODE")
        print("="*60)
        print("This will execute REAL trades with REAL money!")
        print(f"Safety limits:")
        print(f"  - Max trade size: ${MAX_TRADE_USD}")
        print(f"  - Max portfolio risk: {MAX_PORTFOLIO_RISK_PCT:.1%} per trade")
        print(f"  - Max daily trades: {MAX_DAILY_TRADES}")
        print(f"  - Max daily loss: {MAX_DAILY_LOSS_PCT:.1%}")
        print(f"  - Allowed symbols: {', '.join(self.allowed_symbols)}")
        print("="*60 + "\n")
        
        if self._live_confirm_token:
            confirm = input('Enter LIVE_CONFIRM_TOKEN: ').strip()
            if confirm != self._live_confirm_token:
                print('❌ Token mismatch. Live mode NOT enabled.')
                return False
        else:
            confirm = input('Type "YES I UNDERSTAND THE RISKS" to enable: ').strip()
            if confirm != 'YES I UNDERSTAND THE RISKS':
                print('❌ Confirmation not provided. Live mode NOT enabled.')
                return False
        
        # Enable live mode
        self.paper_mode = False
        self.live_confirmed = True
        self.daily_start_equity = self.get_equity()
        
        print("\n✅ LIVE TRADING ENABLED")
        self.send_telegram("🔴 Live trading mode ENABLED")
        logger.warning("LIVE TRADING MODE ENABLED")
        
        return True

    def disable_live(self):
        """Disable live trading and return to paper mode."""
        if self.is_live():
            self.paper_mode = True
            self.live_confirmed = False
            print("✅ Live trading disabled - switched to paper mode")
            self.send_telegram("✅ Live trading mode DISABLED - now in paper mode")
            logger.info("Live trading disabled")
        else:
            print("Already in paper mode")

    def predict_next_close_series(self, closes, window=50, predict_horizon=1, epochs=5):
        """Train a small LSTM on historical closes and predict next values for each timestep.

        Returns an array of predicted next closes aligned with input length (predictions start at index window-1).
        """
        if len(closes) < window + 1:
            return None
        # prepare sequences
        arr = np.array(closes).astype(float)
        # scale
        minv, maxv = arr.min(), arr.max()
        denom = maxv - minv if maxv != minv else 1.0
        scaled = (arr - minv) / denom

        X = []
        y = []
        for i in range(len(scaled) - window):
            X.append(scaled[i:i+window])
            y.append(scaled[i+window])
        X = np.array(X)
        y = np.array(y)

        # convert to torch
        try:
            model = LSTMPredictor()
            optim_local = optim.Adam(model.parameters(), lr=0.001)
            loss_fn = nn.MSELoss()
            model.train()
            X_t = torch.tensor(X[:, :, None], dtype=torch.float32)
            y_t = torch.tensor(y[:, None], dtype=torch.float32)
            for epoch in range(epochs):
                optim_local.zero_grad()
                pred = model(X_t)
                loss = loss_fn(pred, y_t)
                loss.backward()
                optim_local.step()

            model.eval()
            preds = []
            with torch.no_grad():
                for i in range(len(X)):
                    seq = X[i:i+1, :, None]
                    p = model(torch.tensor(seq, dtype=torch.float32)).numpy().ravel()[0]
                    preds.append(p * denom + minv)
            # Align predictions: pad initial window-1 with None
            preds_full = [None] * (window) + list(preds)
            # Trim to input length
            preds_full = preds_full[:len(closes)]
            return np.array([p if p is not None else closes[i] for i, p in enumerate(preds_full)])
        except Exception:
            logger.exception("LSTM prediction failed")
            return None

    def save_state(self):
        state = {
            'positions': self.positions,
            'trade_log': self.trade_log,
            'strategies': {k: v.params for k, v in self.strategies.items()},
            'paper_mode': self.paper_mode,
            'active_strategy': self.active_strategy
        }
        with open('state.json', 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        if os.path.exists('state.json'):
            try:
                with open('state.json', 'r') as f:
                    state = json.load(f)
                self.positions = state.get('positions', {})
                self.trade_log = state.get('trade_log', [])
                strat = state.get('strategies', {})
                for k, v in strat.items():
                    if k in self.strategies:
                        self.strategies[k].params = v
                self.paper_mode = state.get('paper_mode', True)
                self.active_strategy = state.get('active_strategy', self.active_strategy)
            except Exception:
                logger.exception("Failed to load state.json")

    def menu(self):
        """Interactive CLI menu."""
        while True:
            self.status()
            print("1. Select Strategy")
            print("2. Configure API Keys (for live trading)")
            print("3. Enable LIVE Mode (⚠️  requires API keys + confirmation)")
            print("4. Disable LIVE Mode (return to paper)")
            print("5. Run Backtest")
            print("6. Optimize Strategy (Hyperopt)")
            print("7. Start Bot Loop (simulation)")
            print("8. Save State & Exit")
            print("9. View Recent Trades")
            ch = input("\n→ ").strip()

            if ch == '1':
                print(f"\nAvailable: {', '.join(self.strategies.keys())}")
                s = input('Select strategy → ').strip()
                if s in self.strategies:
                    self.active_strategy = s
                    print(f"✅ Active strategy: {s}")
                else:
                    print('❌ Unknown strategy')
            
            elif ch == '2':
                self.configure_api_keys()
            
            elif ch == '3':
                self.enable_live()
            
            elif ch == '4':
                self.disable_live()
            
            elif ch == '5':
                symbol = input('Symbol (default BTC/USDT) → ').strip() or 'BTC/USDT'
                timeframe = input('Timeframe (default 5m) → ').strip() or '5m'
                self.backtest(self.active_strategy, symbol, timeframe)
            
            elif ch == '6':
                print("Running hyperparameter optimization...")
                ranges = {
                    'short_window': (5, 20),
                    'long_window': (20, 50)
                }
                trials = int(input('Number of trials (default 20) → ').strip() or 20)
                self.hyperopt(self.active_strategy, ranges, trials)
            
            elif ch == '7':
                cycles = int(input('Cycles to run (default 6) → ').strip() or 6)
                interval = int(input('Interval seconds (default 5) → ').strip() or 5)
                print(f'\nStarting bot loop for {cycles} cycles...')
                self.start_bot(cycles=cycles, interval_seconds=interval)
            
            elif ch == '8':
                self.save_state()
                print('✅ State saved. Exiting.')
                break
            
            elif ch == '9':
                print(f"\nRecent Trades (last 10):")
                for trade in self.trade_log[-10:]:
                    mode = "🔴LIVE" if trade.get('live') else "📝PAPER"
                    print(f"{mode} {trade.get('datetime', trade.get('time'))}: "
                          f"{trade['side'].upper()} {trade['symbol']} "
                          f"${trade['amount_usd']:.2f}")
            
            else:
                print('❌ Unknown option')

    def start_bot(self, cycles: int = 6, interval_seconds: int = 5):
        """Run bot loop for testing/simulation."""
        mode = "🔴 LIVE" if self.is_live() else "📝 PAPER"
        print(f'\n{mode} Bot loop starting...\n')
        
        strategy = self.strategies.get(self.active_strategy)
        symbol = 'BTC/USDT'
        
        for i in range(cycles):
            print(f"--- Cycle {i+1}/{cycles} ---")
            
            # Fetch data
            df = self.fetch_ohlcv_df(
                symbol,
                timeframe=strategy.params.get('timeframe', '5m'),
                limit=200
            )
            
            if df is None or df.empty:
                logger.warning(f'No OHLCV data available for cycle {i+1}')
                time.sleep(interval_seconds)
                continue
            
            # Generate signals
            df = strategy.populate_indicators(df)
            df = strategy.populate_entry_trend(df)
            df = strategy.populate_exit_trend(df)
            
            latest = df.iloc[-1]
            entry = bool(latest.get('entry', False))
            exit_signal = bool(latest.get('exit', False))
            price = float(latest['close'])
            
            # ML enhancement
            use_ml = strategy.params.get('use_ml', False)
            ml_ok = True
            if use_ml:
                preds = self.predict_next_close_series(df['close'].values)
                if preds is not None:
                    ml_ok = preds[-1] > price
                else:
                    ml_ok = False
            
            print(f"Price: ${price:.2f} | Entry: {entry} | Exit: {exit_signal} | ML: {ml_ok if use_ml else 'N/A'}")
            
            # Execute trades
            if entry and ml_ok and symbol not in self.positions:
                equity = self.get_equity()
                amount = min(
                    equity * self.risk_settings.get('max_position_pct', 0.01),
                    MAX_TRADE_USD
                )
                self.place_order('buy', symbol, amount)
            
            elif exit_signal and symbol in self.positions:
                pos = self.positions[symbol]
                amount = pos['qty'] * price
                self.place_order('sell', symbol, amount)
            
            time.sleep(interval_seconds)
        
        print(f'\n{mode} Bot loop complete!')
        self.save_state()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CryptoPiggy Trading Bot')
    parser.add_argument('--dry-run', action='store_true', help='Dry-run mode (no real orders)')
    args = parser.parse_args()
    
    bot = CryptoPiggyTop2026()
    
    if args.dry_run:
        bot.dry_run = True
        bot.paper_mode = True
        logger.info('⚠️  DRY-RUN MODE: No orders will be executed')
    
    # Run interactive menu
    try:
        bot.menu()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        bot.save_state()
        print("State saved. Exiting.")
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        bot.save_state()
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
