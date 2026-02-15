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

from crypto_piggy_top import CryptoPiggyTop2026

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


# Initialize session state
if 'bot' not in st.session_state:
    st.session_state.bot = CryptoPiggyTop2026()
    st.session_state.bot.setup_exchange()

if 'creds' not in st.session_state:
    st.session_state.creds = _load_credentials()

bot = st.session_state.bot
creds = st.session_state.creds

# Update backend settings from session state
bot.set_backend(creds['user_id'], url=creds['backend_url'], enabled=bool(creds.get('validated')))
bot.exchange_name = creds.get('exchange') or bot.exchange_name

# Check backend health
health_ok, health_msg = _check_backend_health(creds['backend_url'])
bot.backend_last_health = health_ok

if bot.is_live() and not health_ok:
    bot.paper_mode = True
    bot.live_confirmed = False
    st.error('⚠️ Live trading disabled: backend health check failed')

st.title('CryptoPiggyTop — Preview')

with st.expander('API Keys & Backend Settings', expanded=True):
    user_id = st.text_input('User ID', value=creds['user_id'])
    exchange_options = ['binanceus', 'binance', 'kraken', 'coinbasepro']
    exchange = st.selectbox('Exchange', exchange_options, index=exchange_options.index(creds['exchange']) if creds['exchange'] in exchange_options else 0)
    backend_url = st.text_input('Backend URL', value=creds['backend_url'])
    api_key = st.text_input('API Key', value=creds['api_key'], type='password')
    api_secret = st.text_input('API Secret', value=creds['api_secret'], type='password')

    health_ok, health_msg = _check_backend_health(backend_url)
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
            st.session_state.creds = creds
            bot.set_backend(creds['user_id'], url=creds['backend_url'], enabled=bool(creds.get('validated')))
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
                    st.session_state.creds = creds
                    bot.set_backend(user_id.strip(), url=backend_url.strip(), enabled=True)
                    bot.backend_last_health = health_ok
                    st.success('✅ Credentials validated and synced')
                    st.rerun()
                else:
                    creds['validated'] = False
                    _save_credentials(creds)
                    st.session_state.creds = creds
                    st.error(f"❌ Validation failed: {resp.get('error') or resp.get('message') or resp}")

    st.caption(f"Validation status: {'✅ Validated' if creds.get('validated') else '❌ Not validated'}")

col1, col2 = st.columns([2, 1])

with col1:
    st.header('Portfolio')
    positions = bot.positions
    total = bot.get_equity()
    rows = []
    for sym, pos in positions.items():
        qty = pos.get('qty', 0)
        price = pos.get('price', 50000)
        rows.append({'symbol': sym, 'qty': qty, 'price': price, 'value': qty * price})
    st.metric('Portfolio Value (approx)', f'${total:,.2f}')
    if rows:
        st.table(pd.DataFrame(rows))
    else:
        st.write('No open positions')

with col2:
    st.header('Recent Trades')
    trades = bot.trade_log
    if trades:
        dftr = pd.DataFrame(trades)[['time', 'side', 'symbol', 'amount_usd']]
        st.table(dftr.tail(10))
    else:
        st.write('No trades yet')

st.header('Live Ticker')

def get_exchange(name='binance'):
    try:
        import ccxt
        ex = getattr(ccxt, name)()
        return ex
    except Exception:
        return None

def safe_fetch_ticker(ex, symbol):
    try:
        return ex.fetch_ticker(symbol)
    except Exception as e:
        logger.exception('Ticker fetch failed')
        return None

exchange_name = st.selectbox('Exchange', ['binanceus', 'binance', 'kraken', 'coinbasepro'])
symbol = st.selectbox('Symbol', ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT'])
ex = get_exchange(exchange_name)

ticker_placeholder = st.empty()
if ex is None:
    st.warning('Exchange not available in this environment')
else:
    if st.button('Fetch Price'):
        tick = safe_fetch_ticker(ex, symbol)
        if tick:
            st.write('Last:', tick.get('last'))
            st.json(tick)
        else:
            st.error('Failed to fetch ticker')

st.write('App preview - data comes from `state.json` and live fetch via ccxt if available.')

st.header('Controls')
col_a, col_b, col_c = st.columns(3)
with col_a:
    poll = st.button('Start Polling 10s x 6')
with col_b:
    if st.button('Run Backtest'):
        with st.spinner('Running backtest...'):
            res = bot.backtest(bot.active_strategy, symbol, timeframe=bot.strategies[bot.active_strategy].params.get('timeframe', '5m'), limit=300)
            if isinstance(res, dict):
                st.success(f"Return: {res['total_return']:.2%} | Sharpe: {res['sharpe']:.2f} | MaxDD: {res['max_dd']:.2%}")
                st.line_chart(pd.Series(res['equity_curve']))
            else:
                st.write('Backtest returned:', res)
with col_c:
    live_mode = st.checkbox('Live mode', value=bot.is_live())
    backend_ready = bool(creds.get('validated')) and _check_backend_health(creds['backend_url'])[0]

    if live_mode and not bot.is_live():
        if not bot._allow_live_env:
            st.error('❌ Live trading disabled: Set ALLOW_LIVE=1 environment variable')
        elif not backend_ready:
            st.error('❌ Validate & Sync credentials in Settings and ensure backend health is OK')
        else:
            st.warning('⚠️ LIVE TRADING MODE - Real orders will be placed!')
            confirm_token = os.getenv('LIVE_CONFIRM_TOKEN')
            if confirm_token:
                user_token = st.text_input('Enter LIVE_CONFIRM_TOKEN:', type='password', key='live_token')
                if st.button('Enable Live Trading'):
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
                if st.button('⚠️ ENABLE LIVE TRADING (I understand the risks)'):
                    bot.paper_mode = False
                    bot.live_confirmed = True
                    bot.daily_trades_count = 0
                    bot.daily_start_equity = bot.get_equity()
                    bot.send_telegram("🔴 Live trading ENABLED via Streamlit")
                    logger.warning("LIVE TRADING MODE ENABLED BY USER")
                    st.success('✅ Live trading enabled!')
                    st.rerun()
    
    elif not live_mode and bot.is_live():
        bot.paper_mode = True
        bot.live_confirmed = False
        bot.daily_trades_count = 0
        bot.daily_start_equity = bot.get_equity()
        bot.send_telegram("✅ Live trading DISABLED via Streamlit")
        st.info('Switched to paper trading mode')
        st.rerun()

if bot.is_live():
    st.error('🔴 LIVE TRADING ACTIVE - Real orders will be placed')
else:
    st.success('✅ Paper Trading Mode - No real orders')

if poll and ex is not None:
    for i in range(6):
        t = safe_fetch_ticker(ex, symbol)
        if t:
            ticker_placeholder.metric(f'{symbol} price', f"{t.get('last')}")
        time.sleep(10)

st.header('LSTM prediction (BTC/USDT)')
if st.button('Show LSTM Prediction'):
    df_ohlc = bot.fetch_ohlcv_df('BTC/USDT', timeframe='5m', limit=300)
    if df_ohlc is None or df_ohlc.empty:
        st.error('No OHLCV available')
    else:
        preds = bot.predict_next_close_series(df_ohlc['close'].values)
        if preds is None:
            st.error('Prediction failed')
        else:
            st.line_chart(pd.DataFrame({'close': df_ohlc['close'].values, 'pred': preds}))
