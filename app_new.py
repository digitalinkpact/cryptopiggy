import streamlit as st
import pandas as pd
import time
import os
import logging
import json
import uuid
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

from crypto_piggy_top import CryptoPiggyTop2026, MAX_TRADE_USD, MAX_PORTFOLIO_RISK_PCT, MAX_DAILY_TRADES

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('CryptoPiggyApp')

CREDENTIALS_PATH = Path('.cryptopiggy/credentials.json')


def _load_credentials():
    data = {}
    if CREDENTIALS_PATH.exists():
        try:
            data = json.loads(CREDENTIALS_PATH.read_text())
        except Exception:
            data = {}
    user_id = data.get('user_id') or os.getenv('BACKEND_USER_ID') or str(uuid.uuid4())
    exchange = data.get('exchange') or os.getenv('EXCHANGE', 'binanceus')
    api_key = data.get('api_key') or os.getenv('EXCHANGE_API_KEY') or os.getenv('BINANCE_API_KEY')
    api_secret = data.get('api_secret') or os.getenv('EXCHANGE_API_SECRET') or os.getenv('BINANCE_API_SECRET')
    backend_url = data.get('backend_url') or os.getenv('BACKEND_API_URL', 'http://localhost:8000')
    validated = bool(data.get('validated', False))
    return {
        'user_id': user_id,
        'exchange': exchange,
        'api_key': api_key or '',
        'api_secret': api_secret or '',
        'backend_url': backend_url,
        'validated': validated
    }


def _save_credentials(data):
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'user_id': data.get('user_id'),
        'exchange': data.get('exchange'),
        'api_key': data.get('api_key'),
        'api_secret': data.get('api_secret'),
        'backend_url': data.get('backend_url'),
        'validated': bool(data.get('validated', False))
    }
    CREDENTIALS_PATH.write_text(json.dumps(payload, indent=2))


def _check_backend_health(url, timeout=5.0):
    if requests is None:
        return False, 'requests_unavailable'
    try:
        resp = requests.get(f"{url}/api/health", timeout=timeout)
        body = (resp.text or '').strip()
        snippet = body.replace('\n', ' ')[:200]
        if resp.status_code == 200:
            return True, 'ok'
        if snippet:
            return False, f"http_{resp.status_code}: {snippet}"
        return False, f"http_{resp.status_code}: empty_response"
    except Exception as e:
        return False, str(e)


def _sync_credentials(url, payload, timeout=5.0):
    if requests is None:
        return {'ok': False, 'error': 'requests_unavailable'}
    try:
        resp = requests.post(f"{url}/api/credentials", json=payload, timeout=timeout)
        raw_body = resp.text or ''
        content_type = (resp.headers.get('Content-Type') or '').lower()

        if not resp.ok:
            logger.error('Credential sync failed with status %s, content-type=%s, body=%s', resp.status_code, content_type, raw_body[:500])
            return {
                'ok': False,
                'status_code': resp.status_code,
                'content_type': content_type,
                'raw_response': raw_body[:1000],
                'error': f'http_{resp.status_code}'
            }

        if not raw_body.strip():
            return {'ok': True, 'status_code': resp.status_code, 'content_type': content_type}

        if 'application/json' not in content_type:
            logger.error('Credential sync returned non-JSON response, status=%s, content-type=%s, body=%s', resp.status_code, content_type, raw_body[:500])
            return {
                'ok': False,
                'status_code': resp.status_code,
                'content_type': content_type,
                'raw_response': raw_body[:1000],
                'error': 'non_json_response'
            }

        try:
            data = resp.json()
        except ValueError:
            logger.error('Credential sync JSON parse failed, status=%s, body=%s', resp.status_code, raw_body[:500])
            return {
                'ok': False,
                'status_code': resp.status_code,
                'content_type': content_type,
                'raw_response': raw_body[:1000],
                'error': 'invalid_json_response'
            }

        data['status_code'] = resp.status_code
        data['content_type'] = content_type
        return data
    except requests.exceptions.Timeout:
        return {'ok': False, 'error': 'Backend timeout - check if backend is running'}
    except requests.exceptions.ConnectionError:
        return {'ok': False, 'error': 'Cannot connect to backend - verify URL and backend status'}
    except Exception as e:
        return {'ok': False, 'error': f'Credential sync failed: {str(e)}'}


def _fetch_backend_balance(url, user_id, timeout=5.0):
    if requests is None:
        return None
    try:
        resp = requests.get(f"{url}/api/balance/{user_id}", timeout=timeout)
        content_type = (resp.headers.get('Content-Type') or '').lower()
        if resp.status_code == 200 and 'application/json' in content_type:
            try:
                return resp.json()
            except ValueError:
                logger.error('Balance endpoint returned invalid JSON: %s', (resp.text or '')[:500])
                return None
        if resp.status_code != 200:
            logger.error('Balance fetch failed with status %s: %s', resp.status_code, (resp.text or '')[:500])
        return None
    except Exception:
        return None


# Configure page
st.set_page_config(
    page_title="CryptoPiggy Trading Bot",
    page_icon="🐷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if 'bot' not in st.session_state:
    st.session_state.bot = CryptoPiggyTop2026()
    st.session_state.bot.setup_exchange()

bot = st.session_state.bot

if 'creds' not in st.session_state:
    st.session_state.creds = _load_credentials()

creds = st.session_state.creds

# Cache backend health check to avoid redundant calls
if 'backend_health_cache' not in st.session_state:
    st.session_state.backend_health_cache = {'time': 0, 'status': False, 'msg': 'not_checked'}

# Only check health every 30 seconds to avoid spam
if time.time() - st.session_state.backend_health_cache['time'] > 30:
    health_ok, health_msg = _check_backend_health(creds['backend_url'])
    st.session_state.backend_health_cache = {'time': time.time(), 'status': health_ok, 'msg': health_msg}
else:
    health_ok = st.session_state.backend_health_cache['status']
    health_msg = st.session_state.backend_health_cache['msg']

bot.set_backend(creds['user_id'], url=creds['backend_url'], enabled=bool(creds.get('validated')))
bot.backend_last_health = health_ok
bot.exchange_name = creds.get('exchange') or bot.exchange_name

if bot.is_live() and not health_ok:
    bot.paper_mode = True
    bot.live_confirmed = False
    st.error('⚠️ Live trading disabled: backend health check failed')

# Custom CSS for better styling
st.markdown("""
<style>
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        color: #856404;
    }
    .danger-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title('🐷 CryptoPiggy Trading Bot')

# Trading mode banner
if bot.is_live():
    st.markdown("""
    <div class="danger-box">
        <h2>🔴 LIVE TRADING MODE ACTIVE</h2>
        <p><strong>WARNING:</strong> Real orders will be placed using real money!</p>
        <p>Max trade: ${:.2f} | Max risk: {:.1%} | Daily limit: {}/{}</p>
    </div>
    """.format(MAX_TRADE_USD, MAX_PORTFOLIO_RISK_PCT, bot.daily_trades_count, MAX_DAILY_TRADES), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
elif bot.dry_run:
    st.info('🔵 DRY-RUN MODE: Orders simulated but not executed')
else:
    st.success('✅ PAPER TRADING MODE: All trades are simulated')

# Sidebar
with st.sidebar:
    st.header('⚙️ Configuration')

    st.subheader('API Keys & Backend')
    user_id = st.text_input('User ID', value=creds['user_id'])
    exchange_options = ['binanceus', 'binance', 'kraken', 'coinbasepro']
    exchange = st.selectbox('Exchange', exchange_options, index=exchange_options.index(creds['exchange']) if creds['exchange'] in exchange_options else 0)
    backend_url = st.text_input('Backend URL', value=creds['backend_url'])
    api_key = st.text_input('API Key', value=creds['api_key'], type='password')
    api_secret = st.text_input('API Secret', value=creds['api_secret'], type='password')

    # Use cached health check from above
    if health_ok:
        st.success('✅ Backend health: OK')
    else:
        st.error(f"❌ Backend health: {health_msg}")

    cols = st.columns(2)
    with cols[0]:
        if st.button('💾 Save Keys'):
            creds.update({
                'user_id': user_id.strip(),
                'exchange': exchange,
                'backend_url': backend_url.strip(),
                'api_key': api_key.strip(),
                'api_secret': api_secret.strip()
            })
            _save_credentials(creds)
            st.success('✅ Keys saved')
            st.rerun()

    with cols[1]:
        if st.button('✅ Validate & Sync'):
            if not api_key.strip() or not api_secret.strip():
                st.error('❌ API key/secret required')
            else:
                payload = {
                    'userId': user_id.strip(),
                    'exchange': exchange,
                    'apiKey': api_key.strip(),
                    'apiSecret': api_secret.strip()
                }
                resp = _sync_credentials(backend_url.strip(), payload)
                ok = bool(resp.get('ok') or resp.get('canTrade') or resp.get('validated') or resp.get('status') in ['ok', 'success'])
                if resp.get('status_code') == 200 and resp.get('error') is None:
                    ok = True
                if ok:
                    creds.update({
                        'user_id': user_id.strip(),
                        'exchange': exchange,
                        'backend_url': backend_url.strip(),
                        'api_key': api_key.strip(),
                        'api_secret': api_secret.strip(),
                        'validated': True
                    })
                    _save_credentials(creds)
                    bot.set_backend(user_id.strip(), url=backend_url.strip(), enabled=True)
                    bot.backend_last_health = health_ok
                    st.success('✅ Credentials validated and synced')
                    st.rerun()
                else:
                    creds['validated'] = False
                    _save_credentials(creds)
                    st.error(f"❌ Validation failed: {resp.get('error') or resp.get('message') or resp}")

    st.caption(f"Validation status: {'✅ Validated' if creds.get('validated') else '❌ Not validated'}")

    # Exchange status
    st.subheader('Exchange Status')
    if bot.exchange:
        st.success(f"✅ Connected: {bot.exchange_name}")
    else:
        st.warning("⚠️ No exchange configured (backend trading still available)")

    # Live mode toggle
    st.subheader('Trading Mode')
    live_mode_requested = st.checkbox(
        'Enable Live Trading',
        value=bot.is_live(),
        help='Requires ALLOW_LIVE=1 and validated backend credentials'
    )

    backend_ready = bool(creds.get('validated')) and health_ok

    if live_mode_requested and not bot.is_live():
        if not bot._allow_live_env:
            st.error('❌ Set ALLOW_LIVE=1 environment variable')
        elif not backend_ready:
            st.error('❌ Validate & Sync credentials and ensure backend health is OK')
        else:
            st.markdown("""
            <div class="warning-box">
                <h4>⚠️ Enable Live Trading?</h4>
                <p>This will execute REAL trades with REAL money!</p>
                <p><strong>Safety Limits:</strong></p>
                <ul>
                    <li>Max trade: ${:.2f}</li>
                    <li>Max portfolio risk: {:.1%}</li>
                    <li>Daily trades: {}</li>
                    <li>Allowed symbols: {}</li>
                </ul>
            </div>
            """.format(MAX_TRADE_USD, MAX_PORTFOLIO_RISK_PCT, MAX_DAILY_TRADES, ', '.join(bot.allowed_symbols)), unsafe_allow_html=True)

            confirm_token = os.getenv('LIVE_CONFIRM_TOKEN')
            if confirm_token:
                user_token = st.text_input('Enter LIVE_CONFIRM_TOKEN:', type='password', key='live_token')
                if st.button('🔴 ENABLE LIVE TRADING', type='primary'):
                    if user_token == confirm_token:
                        bot.paper_mode = False
                        bot.live_confirmed = True
                        bot.daily_trades_count = 0
                        bot.daily_start_equity = bot.get_equity()
                        bot.send_telegram("🔴 Live trading ENABLED via Streamlit")
                        logger.warning("LIVE TRADING MODE ENABLED BY USER")
                        st.success('✅ Live trading enabled!')
                        st.rerun()
                    else:
                        st.error('❌ Invalid confirmation token')
            else:
                if st.button('🔴 ENABLE LIVE TRADING (I understand the risks)', type='primary'):
                    bot.paper_mode = False
                    bot.live_confirmed = True
                    bot.daily_trades_count = 0
                    bot.daily_start_equity = bot.get_equity()
                    bot.send_telegram("🔴 Live trading ENABLED via Streamlit")
                    logger.warning("LIVE TRADING MODE ENABLED BY USER")
                    st.success('✅ Live trading enabled!')
                    st.rerun()

    elif not live_mode_requested and bot.is_live():
        bot.paper_mode = True
        bot.live_confirmed = False
        # Reset daily counters when switching modes for safety
        bot.daily_trades_count = 0
        bot.daily_start_equity = bot.get_equity()
        bot.send_telegram("✅ Live trading DISABLED via Streamlit")
        st.info('Switched to paper trading')
        st.rerun()

    st.divider()
    
    # Strategy selection
    st.subheader('Strategy')
    strategy_options = list(bot.strategies.keys())
    selected_strategy = st.selectbox(
        'Active Strategy',
        strategy_options,
        index=strategy_options.index(bot.active_strategy) if bot.active_strategy in strategy_options else 0
    )
    if selected_strategy != bot.active_strategy:
        bot.active_strategy = selected_strategy
        st.success(f'✅ Switched to {selected_strategy}')

# Main content
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        'Portfolio Value',
        f'${bot.get_equity():,.2f}',
        delta=None,
        help='Current portfolio value in USD'
    )

with col2:
    st.metric(
        'Open Positions',
        len(bot.positions),
        help='Number of currently open positions'
    )

with col3:
    st.metric(
        'Total Trades',
        len(bot.trade_log),
        delta=f"{bot.daily_trades_count} today",
        help=f'All-time trades (Daily limit: {MAX_DAILY_TRADES})'
    )

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(['📊 Portfolio', '📈 Backtest', '🤖 Bot Control', '📜 Trade Log'])

with tab1:
    st.subheader('Current Positions')
    if bot.positions:
        positions_data = []
        for symbol, pos in bot.positions.items():
            qty = pos.get('qty', 0)
            entry_price = pos.get('price', 0)
            # Try to get current price
            current_price = entry_price
            if bot.exchange:
                try:
                    ticker = bot.safe_ccxt_call('fetch_ticker', symbol)
                    if ticker and 'last' in ticker:
                        current_price = float(ticker['last'])
                except:
                    pass
            
            value = qty * current_price
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            
            positions_data.append({
                'Symbol': symbol,
                'Quantity': f'{qty:.6f}',
                'Entry Price': f'${entry_price:,.2f}',
                'Current Price': f'${current_price:,.2f}',
                'Value': f'${value:,.2f}',
                'P&L %': f'{pnl_pct:+.2f}%'
            })
        
        df_positions = pd.DataFrame(positions_data)
        st.dataframe(df_positions, use_container_width=True)
    else:
        st.info('No open positions')

    with st.expander('Backend Balance'):
        if creds.get('validated'):
            balance = _fetch_backend_balance(creds['backend_url'], creds['user_id'])
            if balance:
                st.json(balance)
            else:
                st.warning('Balance unavailable')
        else:
            st.info('Validate & Sync credentials to view balance')

with tab2:
    st.subheader('Strategy Backtest')
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        backtest_symbol = st.selectbox('Symbol', ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
    with col_b:
        backtest_timeframe = st.selectbox('Timeframe', ['5m', '15m', '1h', '4h', '1d'], index=0)
    with col_c:
        backtest_limit = st.number_input('Candles', min_value=50, max_value=1000, value=300)
    
    if st.button('🚀 Run Backtest', type='primary'):
        with st.spinner('Running backtest...'):
            result = bot.backtest(
                bot.active_strategy,
                backtest_symbol,
                timeframe=backtest_timeframe,
                limit=backtest_limit
            )
            
            if result and isinstance(result, dict):
                # Display metrics
                metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                with metric_col1:
                    st.metric('Total Return', f"{result['total_return']:.2%}")
                with metric_col2:
                    st.metric('Max Drawdown', f"{result['max_dd']:.2%}")
                with metric_col3:
                    st.metric('Sharpe Ratio', f"{result['sharpe']:.2f}")
                with metric_col4:
                    st.metric('Win Rate', f"{result.get('win_rate', 0):.2%}")
                
                # Equity curve
                if 'equity_curve' in result:
                    st.subheader('Equity Curve')
                    equity_df = pd.DataFrame({
                        'Equity': result['equity_curve']
                    })
                    st.line_chart(equity_df)
                
                st.success('✅ Backtest complete!')
            else:
                st.error('❌ Backtest failed')

with tab3:
    st.subheader('Bot Control')
    
    col_x, col_y = st.columns(2)
    
    with col_x:
        st.write('**Start Bot Loop**')
        bot_cycles = st.number_input('Cycles', min_value=1, max_value=20, value=6)
        bot_interval = st.number_input('Interval (seconds)', min_value=1, max_value=60, value=5)
        
        if st.button('▶️ Start Bot', type='primary'):
            if bot.is_live():
                st.warning('⚠️ Running in LIVE mode - real trades will be executed!')
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i in range(bot_cycles):
                status_text.text(f'Cycle {i+1}/{bot_cycles}...')
                progress_bar.progress((i + 1) / bot_cycles)
                
                # Run one cycle
                try:
                    df = bot.fetch_ohlcv_df('BTC/USDT', timeframe='5m', limit=200)
                    if df is not None and not df.empty:
                        strategy = bot.strategies[bot.active_strategy]
                        df = strategy.populate_indicators(df)
                        df = strategy.populate_entry_trend(df)
                        df = strategy.populate_exit_trend(df)
                        
                        latest = df.iloc[-1]
                        entry = bool(latest.get('entry', False))
                        exit_signal = bool(latest.get('exit', False))
                        
                        if entry and 'BTC/USDT' not in bot.positions:
                            amount = min(bot.get_equity() * 0.01, MAX_TRADE_USD)
                            bot.place_order('buy', 'BTC/USDT', amount)
                            st.info(f'📝 Buy signal executed')
                        elif exit_signal and 'BTC/USDT' in bot.positions:
                            pos = bot.positions['BTC/USDT']
                            bot.place_order('sell', 'BTC/USDT', pos['qty'] * float(latest['close']))
                            st.info(f'📝 Sell signal executed')
                except Exception as e:
                    st.error(f'Error in cycle {i+1}: {e}')
                
                time.sleep(bot_interval)
            
            status_text.text('Bot loop complete!')
            bot.save_state()
            st.success('✅ Bot loop finished')
    
    with col_y:
        st.write('**Quick Actions**')
        if st.button('💾 Save State'):
            bot.save_state()
            st.success('✅ State saved')
        
        if st.button('🔄 Refresh Data'):
            st.rerun()

        st.markdown('**Live Trade Test**')
        test_amount = st.number_input(
            'Test Trade Amount (USD)',
            min_value=2.0,
            max_value=float(MAX_TRADE_USD),
            value=float(max(2.0, bot.risk_settings.get('min_trade_size_usd', 2.0))),
            step=1.0
        )
        if st.button('🧪 Test Live BUY (BTC/USDT)'):
            if not bot.is_live():
                st.error('❌ Enable Live Trading first')
            else:
                result = bot.place_order('buy', 'BTC/USDT', float(test_amount))
                if result:
                    order_id = result.get('orderId') or result.get('id') or 'unknown'
                    st.success(f"✅ Live order submitted. Order ID: {order_id}")
                else:
                    st.error('❌ Live order failed')

        if st.button('💰 Fetch Backend Balance'):
            balance = _fetch_backend_balance(creds['backend_url'], creds['user_id'])
            if balance:
                st.success('✅ Balance fetched')
                st.json(balance)
            else:
                st.error('❌ Balance unavailable')
        
        if bot.is_live():
            if st.button('🛑 Emergency Stop (Disable Live)', type='secondary'):
                bot.paper_mode = True
                bot.live_confirmed = False
                bot.daily_trades_count = 0
                bot.daily_start_equity = bot.get_equity()
                bot.send_telegram("🛑 EMERGENCY STOP: Live trading disabled via Streamlit")
                logger.warning("EMERGENCY STOP: Live trading disabled by user")
                st.warning('Live trading disabled')
                st.rerun()

with tab4:
    st.subheader('Recent Trades')
    
    if bot.trade_log:
        trades_to_show = st.slider('Show last N trades', 5, 50, 20)
        
        trades_data = []
        for trade in bot.trade_log[-trades_to_show:]:
            trades_data.append({
                'Time': trade.get('datetime', trade.get('time')),
                'Mode': '🔴 LIVE' if trade.get('live') else '📝 PAPER',
                'Side': trade['side'].upper(),
                'Symbol': trade['symbol'],
                'Amount USD': f"${trade['amount_usd']:.2f}",
                'Price': f"${trade.get('price', 0):.2f}",
                'Quantity': f"{trade.get('qty', 0):.6f}"
            })
        
        df_trades = pd.DataFrame(trades_data)
        st.dataframe(df_trades, use_container_width=True)
        
        # Download button
        csv = df_trades.to_csv(index=False)
        st.download_button(
            label='📥 Download Trade Log CSV',
            data=csv,
            file_name='cryptopiggy_trades.csv',
            mime='text/csv'
        )
    else:
        st.info('No trades yet')

# Footer
st.divider()
st.caption(f'CryptoPiggy Trading Bot | Strategy: {bot.active_strategy} | Mode: {"🔴 LIVE" if bot.is_live() else "📝 PAPER"}')
