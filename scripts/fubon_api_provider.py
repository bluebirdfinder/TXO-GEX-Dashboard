import os
import sys
import logging
import datetime
import time
import threading
from collections import deque

# Set up logging for Fubon Provider
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def load_local_env():
    """
    Parses local .env file manually if python-dotenv is not installed,
    ensuring seamless environment variable injection without extra dependencies.
    Strips single and double quotes from key-value pairs.
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("\"'")
        except Exception as e:
            logging.warning(f"Failed to parse .env file: {e}")

load_local_env()

class FubonAPIProvider:
    """
    Encapsulates Fubon Neo API SDK & MarketData integration for Taiwan Index Spot & TXF Futures.
    Provides Zero-Trust security handling, dynamic symbol detection, and real-time quote streaming.
    """
    def __init__(self):
        self.api_key = os.getenv("FUBON_API_KEY", "").strip("\"'")
        self.secret_key = os.getenv("FUBON_SECRET_KEY", "").strip("\"'")
        self.account_no = os.getenv("FUBON_ACCOUNT_NO", "").strip("\"'")
        self.cert_path = os.getenv("FUBON_CERT_PATH", "").strip("\"'")
        self.cert_pass = os.getenv("FUBON_CERT_PASS", "").strip("\"'")
        self.mode = os.getenv("FUBON_API_MODE", "FALLBACK").upper().strip("\"'")
        
        self.is_active = False
        self.sdk_instance = None
        self.marketdata = None
        # Continuous front-month alias (per Fubon's official "商品代碼與連續月別名" docs):
        # resolves to the current near-month contract and auto-rolls after settlement,
        # for both REST (/intraday/quote) and WebSocket subscribe — no manual detection needed.
        self.txf_symbol = "TXF1!"
        # UI display code (room.js's GEX_SUPPORTED_SYMBOLS: TXF/MXF/MTX/TMF) -> Fubon Neo alias. The room's
        # "MTX" is TAIFEX 微台 (Fubon alias TMF1!) and "MXF" is TAIFEX 小台 (Fubon alias MXF1!) — same
        # naming as scripts/fetch_market_klines.py's FUTURES_ASSETS, confirmed against the live API 2026-09-27.
        self.CVD_SYMBOL_ALIAS = {"TXF": "TXF1!", "MXF": "MXF1!", "MTX": "TMF1!", "TMF": "TMF1!"}
        # 個股／ETF 期貨（CDF 台積電期、CQF 台塑期…共 36 檔）同樣用 <代號>1! 連續月別名；代號清單取自 data/tw_symbols_universe.json。
        # 2026-09-30 實測：36 檔 x (買賣簿＋成交) x (日盤＋夜盤) = 156 個訂閱全數成功、零錯誤。
        try:
            import json as _json
            _uni_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tw_symbols_universe.json")
            with open(_uni_path, encoding="utf-8") as _f:
                _uni = _json.load(_f)
            for _it in (_uni if isinstance(_uni, list) else _uni.get("symbols", [])):
                _code = str(_it.get("symbol", ""))
                if _it.get("asset_type") == "stock_futures" and _code and _code not in self.CVD_SYMBOL_ALIAS:
                    self.CVD_SYMBOL_ALIAS[_code] = _code + "1!"
        except Exception as _e:
            logging.warning(f"stock-futures alias list not loaded ({_e}); only TXF/MXF/MTX/TMF will have CVD/momentum")
        self.last_cache = {
            'spot_price': None,
            'otc_price': None,
            'txf_price': None,
            'change': 0.0,
            'pct': 0.0,
            'source': 'Fubon Neo API (Live)'
        }
        self.last_fetch_ts = 0

        # Books (五檔委託簿) WebSocket stream state.
        # books_cache[symbol] = {'bids': [{'price':..,'size':..}, ...], 'asks': [...], 'time':.., 'raw': <last raw message dict>}
        self.books_cache = {}
        self._books_subscribed = set()
        # Fubon subscribes by alias ('TXF1!') but echoes the resolved contract code ('TXFJ6') as the
        # 'symbol' of every data frame (verified against the live feed 2026-09-30). The subscribe ack
        # and every data frame share the same channel 'id', so that id is the reliable way back to the
        # alias every cache, lookup and the room's CVD_SYMBOL_ALIAS are keyed by.
        self._channel_alias = {}
        # Night-session (15:00-05:00) data is only pushed to subscriptions made with afterHours=True (verified against
        # the live feed 2026-09-30: a plain subscribe gets one stale snapshot then nothing all night, an afterHours
        # subscribe streams type FUTURE_AH ticks). Each (channel, symbol, afterHours) is subscribed at most once; both
        # modes may coexist because only one session trades at a time. Kept so a reconnect can replay them.
        self._sub_modes = set()

        # Trades (逐筆成交) WebSocket stream state.
        # trades_log[symbol] = a bounded deque of {'price','size','side','ts'} — 'side' is
        # inferred (tick rule) since the trades schema itself is not fully confirmed; see
        # start_trades_stream()'s docstring for exactly what is and isn't verified.
        self.trades_log = {}
        self._trades_subscribed = set()
        self._trades_last_serial = {}  # symbol -> serial of the last trades frame, to drop exact replays
        self._trades_logged_raw = set()  # symbols we've logged one raw message for, for schema verification
        self._TRADES_LOG_MAXLEN = 20000  # ~a session's worth of prints per symbol; bounded so memory can't grow unbounded
        # 大戶散戶動能 1 分鐘歷史（可合成 5／15／30 分）：每 15 秒更新「進行中的分鐘」並每 60 秒寫檔，重開機後可讀回。
        # 檔案放在 repo 外（預設 ~/.txo_momentum_history，可用 MOMENTUM_HISTORY_DIR 覆蓋），避免被 git add 進公開倉庫。
        # 只存真實收到的資料；沒開機／沒連線的時段不會補值。
        self._mom_hist = {}   # alias -> {minute_start_ts(int): 1 分鐘紀錄（欄位見 record_momentum_bars）}
        self._mom_hist_dirty = set()
        self._mom_hist_lock = threading.Lock()
        self._mom_hist_dir = os.getenv("MOMENTUM_HISTORY_DIR") or os.path.join(os.path.expanduser("~"), ".txo_momentum_1m")
        self._mom_hist_keep_days = 5   # 1 分鐘資料量大，只留 5 天
        self._mom_hist_started = False

        # Real Cumulative Volume Delta (CVD) — signed-volume running total built tick-by-tick
        # from the same confirmed tick-rule 'side' used for trades_log, kept as its own
        # incrementally-updated counter (not re-summed from trades_log, which is bounded and
        # can evict old prints on a high-volume day — that would silently under-count CVD).
        # Resets to 0 whenever a new TAIFEX session (day 08:45 / night 15:00) begins, matching
        # how real CVD indicators behave. Cannot be backfilled before this process started
        # tracking — see get_cvd_series()'s docstring.
        self.cvd_cumulative = {}    # symbol -> running signed-volume total for the current session
        self.cvd_session_start = {} # symbol -> epoch ts of the session the above total belongs to
        self.cvd_points = {}        # symbol -> bounded deque of {'ts','value'} snapshots since session start

        # Shared futopt WebSocket connection state (Books + Trades share ONE connection —
        # see _ensure_futopt_connected() for why this must not be connected twice).
        # fubon_books_worker() and fubon_trades_worker() run as separate OS threads in
        # live_price_server.py and can both notice is_active flip True within the same
        # instant, so the connect-once check below needs a real lock, not just a flag —
        # a bare "if not connected: connect()" is a check-then-act race between threads.
        self._futopt_ws = None
        self._futopt_connected = False
        self._futopt_connect_lock = threading.Lock()

        self._initialize_sdk()

    def _initialize_sdk(self):
        """
        Attempts to load Fubon Neo SDK and MarketData if credentials are valid.
        If credentials or SDK are missing/invalid, gracefully defaults to FALLBACK mode.
        """
        if self.mode == "FALLBACK" or not self.api_key or "YOUR_" in self.api_key:
            logging.info("Fubon API Provider: Operating in [FALLBACK] Mode (Official Web APIs).")
            self.is_active = False
            return

        try:
            import fubon_neo
            from fubon_neo.sdk import FubonSDK, MarketData, Mode
            
            logging.info("Fubon Neo SDK module found. Authenticating client...")
            sdk = FubonSDK()
            
            if self.api_key and self.cert_path:
                if hasattr(sdk, "apikey_login"):
                    res = sdk.apikey_login(self.account_no, self.api_key, self.cert_path, self.cert_pass)
                else:
                    res = sdk.login(self.account_no, self.secret_key or self.api_key, self.cert_path, self.cert_pass)
                
                is_success = getattr(res, "is_success", False)
                if res and is_success:
                    self.sdk_instance = sdk
                    try:
                        token = sdk.exchange_realtime_token()
                        if token:
                            self.marketdata = MarketData(token, Mode.Normal)
                            self.is_active = True
                            logging.info(f"SUCCESS: Fubon API Provider Authenticated & MarketData Active! Target Front-Month: {self.txf_symbol}")
                        else:
                            logging.warning("Fubon API: Failed to obtain exchange_realtime_token.")
                            self.is_active = False
                    except Exception as ex:
                        logging.warning(f"Fubon MarketData Init error: {ex}")
                        self.is_active = False
                else:
                    msg = getattr(res, "message", str(res))
                    logging.warning(f"Fubon API Login failed: {msg}. Defaulting to Web API fallback.")
                    self.is_active = False
            else:
                logging.info("Fubon API credentials incomplete in .env. Operating in Web API fallback mode.")
                self.is_active = False
        except ImportError:
            logging.info("fubon_neo SDK package not installed locally. Using Web API fallback.")
            self.is_active = False
        except Exception as e:
            logging.warning(f"Fubon API Initialization error: {e}. Falling back to Web API.")
            self.is_active = False

    def get_live_quotes(self):
        """
        Retrieves real-time index & futures quotes from Fubon Provider.
        Returns dict: {'spot_price': float, 'otc_price': float, 'txf_price': float, 'change': float, 'pct': float, 'source': str}
        """
        if not self.is_active or not self.marketdata:
            return {
                'spot_price': None,
                'otc_price': None,
                'txf_price': None,
                'change': 0.0,
                'pct': 0.0,
                'source': 'Official Web API (Fallback)'
            }

        now = time.time()
        if (now - self.last_fetch_ts) < 0.8 and self.last_cache.get('txf_price'):
            return self.last_cache

        try:
            now_h = datetime.datetime.now().hour
            # Session determination: 15:00 ~ 08:45 uses AFTERHOURS / Night session, 08:45 ~ 14:00 uses REGULAR
            session_mode = "AFTERHOURS" if (now_h >= 15 or now_h < 8 or (now_h == 8 and datetime.datetime.now().minute < 45)) else "REGULAR"

            # Query real-time futures quote.
            # Verified against the live API 2026-10-01: the `session` parameter only accepts "afterhours" (night session).
            # The day session is requested WITHOUT any session parameter; passing "REGULAR" raises an error. The old code
            # swallowed that error and silently re-queried AFTERHOURS, so during the whole day session the "Fubon" quote was
            # last night's closing price (48,296) while the market was trading at ~48,380. No silent fallback to the other
            # session any more: if the call fails, we report "no quote" rather than a stale number.
            txf_q = None
            try:
                if session_mode == "REGULAR":
                    txf_q = self.marketdata.rest_client.futopt.intraday.quote(symbol=self.txf_symbol)
                else:
                    txf_q = self.marketdata.rest_client.futopt.intraday.quote(symbol=self.txf_symbol, session="AFTERHOURS")
            except Exception as e:
                logging.warning(f"Fubon futopt quote ({session_mode}) failed: {e}")

            txf_price = None
            change = 0.0
            pct = 0.0

            if isinstance(txf_q, dict):
                txf_price = txf_q.get("lastPrice") or (txf_q.get("lastTrade") or {}).get("price") or txf_q.get("closePrice") or txf_q.get("referencePrice")
                change = float(txf_q.get("change", 0.0) or 0.0)
                pct = float(txf_q.get("changePercent", 0.0) or 0.0)

            # No price from Fubon (e.g. the 05:00-08:45 gap): report "no quote" — the caller/front end shows no live
            # price. This used to substitute a made-up 47207.0 / +252 / +0.54 that looked like a real Fubon tick.

            # Query real-time spot index quotes (Day session)
            spot_price = None
            otc_price = None
            if session_mode == "REGULAR":
                try:
                    spot_q = self.marketdata.rest_client.stock.intraday.quote(symbol="IX0001")
                    otc_q = self.marketdata.rest_client.stock.intraday.quote(symbol="IX0043")
                    if isinstance(spot_q, dict):
                        spot_price = spot_q.get("closePrice") or spot_q.get("lastPrice")
                    if isinstance(otc_q, dict):
                        otc_price = otc_q.get("closePrice") or otc_q.get("lastPrice")
                except Exception:
                    pass

            if txf_price and float(txf_price) > 0:
                self.last_cache = {
                    'spot_price': float(spot_price) if spot_price else None,
                    'otc_price': float(otc_price) if otc_price else None,
                    'txf_price': float(txf_price),
                    'change': change,
                    'pct': pct,
                    'source': f'Fubon Neo API ({session_mode})'
                }
                self.last_fetch_ts = now
                return self.last_cache

        except Exception as e:
            logging.debug(f"Fubon live quote fetch error: {e}")

        # Never hand out an old cached quote as if it were current: after 10 s without a successful fetch report "no quote".
        if time.time() - self.last_fetch_ts > 10:
            return {'spot_price': None, 'otc_price': None, 'txf_price': None, 'change': 0.0, 'pct': 0.0,
                    'source': 'Fubon Neo API (no fresh quote)'}
        return self.last_cache

    def _ensure_futopt_connected(self):
        """
        Connects the shared futopt WebSocket client exactly once and wires a
        SINGLE unified message handler (_handle_futopt_message) that dispatches
        by channel. Both start_books_stream() and start_trades_stream() call
        this instead of each independently calling .on()/.connect().

        Fixes a real bug hit during live testing on 2026-09-14: the two streams
        used to each call futopt_ws.connect() independently, racing to start a
        second run_forever() thread on the same socket
        ("WebSocketException: socket is already opened"). Worse, both handlers
        were registered as separate 'message' listeners, so EVERY message went
        to BOTH — a trades 'data' frame has no 'bids'/'asks', so
        _handle_books_message would silently overwrite books_cache[symbol]
        with empty bid/ask lists on every trade tick, corrupting
        big_order_diff. The single dispatcher below only calls the handler for
        the channel the message actually belongs to.
        """
        if self._futopt_connected:
            return self._futopt_ws

        if not self.is_active or not self.marketdata:
            return None

        # Hold the lock across the whole check-connect-set sequence: without this,
        # two threads can both pass the "if self._futopt_connected" check above
        # before either sets it True, and both go on to call futopt_ws.connect().
        with self._futopt_connect_lock:
            if self._futopt_connected:  # re-check: another thread may have connected while we waited for the lock
                return self._futopt_ws

            try:
                futopt_ws = self.marketdata.websocket_client.futopt
            except Exception as e:
                logging.warning(f"_ensure_futopt_connected: websocket_client.futopt unavailable: {e}")
                return None

            futopt_ws.on('message', self._handle_futopt_message)
            futopt_ws.on('error', lambda err: logging.warning(f"Fubon futopt WebSocket error: {err}"))
            futopt_ws.on('disconnect', lambda code, msg: self._on_futopt_disconnect(code, msg))
            try:
                futopt_ws.connect()
            except Exception as e:
                logging.warning(f"_ensure_futopt_connected: connect() failed: {e}")
                return None

            self._futopt_ws = futopt_ws
            self._futopt_connected = True
            return futopt_ws

    def relogin(self):
        """Fresh login + market-data token, then re-establish the futopt WebSocket and its subscriptions. The SDK gives
        the REST token once at login and nothing here refreshed it, so a long-running server could end up serving
        stale data silently; live_price_server's watchdog calls this."""
        self._initialize_sdk()
        if self.is_active:
            self._on_futopt_disconnect("relogin", "watchdog / pre-session refresh")
        return self.is_active

    def _on_futopt_disconnect(self, code, msg):
        """ Auto-reconnect + re-subscribe both channels on disconnect, per Fubon's documented reconnect pattern. """
        logging.warning(f"Fubon futopt WebSocket disconnected ({code}: {msg}). Reconnecting...")
        self._futopt_connected = False
        futopt_ws = self._ensure_futopt_connected()
        if not futopt_ws:
            logging.warning("Fubon futopt WebSocket reconnect failed: could not re-establish connection.")
            return
        try:
            for channel, symbol, ah in list(self._sub_modes):
                params = {'channel': channel, 'symbol': symbol}
                if ah:
                    params['afterHours'] = True
                futopt_ws.subscribe(params)
            logging.info("Fubon futopt WebSocket reconnected and re-subscribed to all channels.")
        except Exception as e:
            logging.warning(f"Fubon futopt WebSocket re-subscribe after reconnect failed: {e}")

    def _handle_futopt_message(self, raw_message):
        """
        Single entry point for ALL futopt WebSocket messages (books + trades
        share one connection). Parses the envelope once, then dispatches to
        _process_books_data()/_process_trades_data() by the message's own
        'channel' field — never guesses which stream a message belongs to.
        """
        try:
            import json as _json
            message = _json.loads(raw_message) if isinstance(raw_message, (str, bytes)) else raw_message
        except Exception as e:
            logging.debug(f"futopt message JSON parse error: {e}")
            return

        event = message.get('event')

        if event == 'subscribed':
            info = message.get('data') or {}
            channel = info.get('channel')
            if info.get('id') and info.get('symbol'):
                self._channel_alias[info['id']] = info['symbol']
            if channel == 'books':
                logging.info(f"Fubon Books: subscription confirmed — {info}")
            elif channel == 'trades':
                logging.info(f"Fubon Trades: subscription confirmed — {info}")
            return
        if event != 'data':
            return  # ignore auth/heartbeat/pong/error/unsubscribed frames

        channel = message.get('channel')
        data = message.get('data') or {}
        alias = self._channel_alias.get(message.get('id'))
        if channel == 'books':
            self._process_books_data(data, alias)
        elif channel == 'trades':
            self._process_trades_data(data, alias)

    def start_books_stream(self, symbols):
        """
        Subscribes to Fubon's futures WebSocket "books" channel (五檔委買委賣簿)
        for the given symbols (e.g. ['TXFA4', 'MXFA4']).

        Verified against the installed fubon_neo==2.2.8 SDK source
        (fubon_neo/adapter.py -> WebSocketFutOptClientWrapper, and the underlying
        fugle_marketdata.WebSocketClient it wraps) AND against the official
        "期權 WebSocket / Channels / Books" doc page (fbs.com.tw/TradeAPI):
          - self.marketdata.websocket_client.futopt exposes .on(event, cb),
            .connect(), .subscribe(params), .unsubscribe(params), .disconnect()
          - subscribe() sends {"event": "subscribe", "data": params} over the socket.
          - Inbound messages arrive on the 'message' event as a RAW JSON string
            (the SDK does not hand you a parsed dict) — this must be json.loads()'d.
          - A books data frame is exactly:
              {"event": "data", "channel": "books", "id": "<CHANNEL_ID>",
               "data": {"symbol", "type", "exchange", "time",
                        "bids": [{"price","size"}, ...] (top 5),
                        "asks": [{"price","size"}, ...] (top 5),
                        "derivedBid": {"price","size"},  # spread-contract only, else 0/0
                        "derivedAsk": {"price","size"},
                        "isTrial": bool}}  # only present during call-auction/trial matching
        _process_books_data() below parses exactly this shape — no field-name
        guessing left.
        """
        futopt_ws = self._ensure_futopt_connected()
        if not futopt_ws:
            logging.warning("start_books_stream: Fubon SDK not active or connection failed — cannot subscribe to Books channel.")
            return False

        for symbol in symbols:
            try:
                self._subscribe_for_current_session(futopt_ws, 'books', symbol)
                if symbol not in self._books_subscribed:
                    logging.info(f"Fubon Books channel: subscribed to {symbol} (五檔委託簿).")
                self._books_subscribed.add(symbol)
            except Exception as e:
                logging.warning(f"start_books_stream: subscribe({symbol}) failed: {e}")

        return True

    def _process_books_data(self, data, alias=None):
        """ Handles one books 'data' payload (already unwrapped from the event envelope). Cached under the subscribed alias when known. """
        symbol = alias or data.get('symbol')
        if not symbol:
            return

        def _normalize_side(levels):
            return [{'price': float(lvl['price']), 'size': int(lvl['size'])} for lvl in (levels or [])]

        derived_bid = data.get('derivedBid') or {'price': 0, 'size': 0}
        derived_ask = data.get('derivedAsk') or {'price': 0, 'size': 0}

        self.books_cache[symbol] = {
            'bids': _normalize_side(data.get('bids')),
            'asks': _normalize_side(data.get('asks')),
            'derived_bid': {'price': float(derived_bid.get('price', 0)), 'size': int(derived_bid.get('size', 0))},
            'derived_ask': {'price': float(derived_ask.get('price', 0)), 'size': int(derived_ask.get('size', 0))},
            'is_trial': bool(data.get('isTrial', False)),
            'time': data.get('time'),
            'updated_ts': time.time()
        }

    def get_book(self, symbol):
        """ Returns the latest cached Books (五檔) snapshot for symbol, or None if never received. """
        return self.books_cache.get(symbol)

    # ------------------------------------------------------------------
    # Trades (逐筆成交) stream — needed for 散戶成交筆數差 (retail trade-COUNT
    # differential, per 陳玠儒/股市擺渡人's methodology: count of buy prints
    # minus count of sell prints, NOT summed volume).
    # ------------------------------------------------------------------

    def start_trades_stream(self, symbols):
        """
        Subscribes to Fubon's futures WebSocket "trades" channel (逐筆成交).

        CONFIRMED (same verified mechanism as start_books_stream — see its
        docstring): subscribe({'channel': 'trades', 'symbol': ...}) over the
        same futopt websocket_client, same connect/on/message/disconnect API.

        NOT independently confirmed for the FUTURES trades payload (I could not
        reach fbs.com.tw or developer.fugle.tw from this sandbox to see a real
        futopt 'trades' example — only the Books page was hand-verified by the
        user). What I have instead, from web-search summaries only (weaker
        evidence, treat as "likely, not certain"):
          - A general Fugle "trades" schema (this may be the STOCK version,
            not futopt) showing: symbol, price, size, volume(cumulative),
            bid, ask, isClose, time, serial.
          - A separate summary claiming the *futures* trades payload has:
            symbol, price, size, time (microseconds), serial.
        Since these two disagree on whether bid/ask/volume are present, this
        code does NOT assume bid/ask exist. It infers the trade's aggressor
        side using the tick rule against the Books cache (already confirmed)
        instead: price >= best ask -> buy print, price <= best bid -> sell
        print, otherwise inherit the previous print's side. This sidesteps
        depending on unconfirmed trades-payload fields entirely.

        Like start_books_stream(), the first raw message per symbol is logged
        at INFO so the parsing can be corrected against a real message.
        """
        futopt_ws = self._ensure_futopt_connected()
        if not futopt_ws:
            logging.warning("start_trades_stream: Fubon SDK not active or connection failed — cannot subscribe to Trades channel.")
            return False

        for symbol in symbols:
            try:
                self._subscribe_for_current_session(futopt_ws, 'trades', symbol)
                if symbol not in self._trades_subscribed:
                    logging.info(f"Fubon Trades channel: subscribed to {symbol} (逐筆成交).")
                self._trades_subscribed.add(symbol)
            except Exception as e:
                logging.warning(f"start_trades_stream: subscribe({symbol}) failed: {e}")

        return True

    _TAIPEI_TZ = datetime.timezone(datetime.timedelta(hours=8))

    def _session_after_hours(self, now_ts=None):
        """True while the TAIFEX night session (15:00-05:00 Taipei) is the one trading. In the gaps with no session
        (05:00-08:45, 13:45-15:00) keep the mode of the last subscription rather than flapping."""
        now_ts = now_ts if now_ts is not None else time.time()
        dt = datetime.datetime.fromtimestamp(now_ts, tz=self._TAIPEI_TZ)
        hm = dt.hour * 60 + dt.minute
        if hm >= 15 * 60 or hm < 5 * 60:
            return True
        if 8 * 60 + 45 <= hm < 13 * 60 + 45:
            return False
        return getattr(self, '_last_after_hours', False)

    def _subscribe_for_current_session(self, futopt_ws, channel, symbol):
        ah = self._session_after_hours()
        self._last_after_hours = ah
        key = (channel, symbol, ah)
        if key in self._sub_modes:
            return
        params = {'channel': channel, 'symbol': symbol}
        if ah:
            params['afterHours'] = True
        futopt_ws.subscribe(params)
        self._sub_modes.add(key)

    def sync_session_subscriptions(self):
        """Called periodically by the gateway workers: when the day/night session flips, subscribe every channel/symbol
        we already track in the new mode (no unsubscribe needed - the other session's stream simply goes quiet)."""
        futopt_ws = self._futopt_ws
        if not futopt_ws or not self._futopt_connected:
            return
        ah = self._session_after_hours()
        pending = [(ch, sym) for ch, syms in (('books', self._books_subscribed), ('trades', self._trades_subscribed))
                   for sym in syms if (ch, sym, ah) not in self._sub_modes]
        for ch, sym in pending:
            try:
                self._subscribe_for_current_session(futopt_ws, ch, sym)
            except Exception as e:
                logging.warning(f"sync_session_subscriptions: {ch} {sym} failed: {e}")
        if pending:
            logging.info(f"Fubon session flip -> {'night (afterHours)' if ah else 'day'}: re-subscribed {len(pending)} channel(s).")

    @classmethod
    def _taifex_session_start_ts(cls, now_ts=None):
        """
        Returns the epoch-seconds start of the TAIFEX session `now_ts` (default: now)
        falls in, per the official boundary documented in
        scripts/fetch_and_calc_vision.py (~line 3139): day session opens 08:45, night
        session opens 15:00 and runs past midnight into the next calendar day.

        The 13:45-15:00 gap between day close and night open has no live trades, so it
        is treated as a continuation of the day session that just closed — this branch
        only matters for bookkeeping and is never actually hit by a real incoming tick.
        """
        now_ts = now_ts if now_ts is not None else time.time()
        now_dt = datetime.datetime.fromtimestamp(now_ts, tz=cls._TAIPEI_TZ)
        hm = now_dt.hour * 60 + now_dt.minute
        day_open_hm = 8 * 60 + 45
        night_open_hm = 15 * 60
        if day_open_hm <= hm < night_open_hm:
            session_open = now_dt.replace(hour=8, minute=45, second=0, microsecond=0)
        elif hm >= night_open_hm:
            session_open = now_dt.replace(hour=15, minute=0, second=0, microsecond=0)
        else:
            # Before 08:45 — still inside the night session that opened the previous calendar day.
            prev_day = now_dt - datetime.timedelta(days=1)
            session_open = prev_day.replace(hour=15, minute=0, second=0, microsecond=0)
        return session_open.timestamp()

    def _process_trades_data(self, data, alias=None):
        """
        Handles one trades 'data' payload (already unwrapped from the event envelope).

        Verified against the live feed (2026-09-30): a frame looks like
          {'symbol': 'TXFJ6', 'trades': [{'price', 'size', 'bid', 'ask'}, ...],
           'total': {...}, 'time': <us epoch>, 'serial': <int>}
        i.e. prints are in a 'trades' list (not top-level price/size), each carrying the best bid/ask
        at match time. Side is the tick rule against that bid/ask: at/above ask = buy, at/below bid = sell.
        Cached under the subscribed alias (see _channel_alias) so lookups by 'TXF1!' etc. find it.
        """
        symbol = alias or data.get('symbol')
        if not symbol:
            return
        prints = data.get('trades')
        if not isinstance(prints, list):
            # Older/alternative shape: a single print at the top level.
            prints = [data] if data.get('price') is not None and data.get('size') is not None else []
        if not prints:
            return

        serial = data.get('serial')
        if serial is not None:
            if self._trades_last_serial.get(symbol) == serial:
                return  # exact replay of the previous frame
            self._trades_last_serial[symbol] = serial

        if symbol not in self._trades_logged_raw:
            logging.info(f"Fubon Trades RAW sample for {symbol} (verify against this): {data}")
            self._trades_logged_raw.add(symbol)

        for tr in prints:
            price = tr.get('price')
            size = tr.get('size')
            if price is None or size is None:
                continue

            side = None
            t_bid, t_ask = tr.get('bid'), tr.get('ask')
            if t_bid and t_ask:
                if price >= t_ask:
                    side = 'buy'
                elif price <= t_bid:
                    side = 'sell'
            if side is None:
                book = self.books_cache.get(symbol)
                if book and book.get('bids') and book.get('asks'):
                    if price >= book['asks'][0]['price']:
                        side = 'buy'
                    elif price <= book['bids'][0]['price']:
                        side = 'sell'
            if side is None:
                log = self.trades_log.get(symbol)
                side = log[-1]['side'] if log else 'buy'

            now = time.time()
            if symbol not in self.trades_log:
                self.trades_log[symbol] = deque(maxlen=self._TRADES_LOG_MAXLEN)
            self.trades_log[symbol].append({
                'price': float(price),
                'size': int(size),
                'side': side,
                'ts': now
            })

            # Real CVD: same side as above, accumulated as its own persistent counter
            # (see __init__ comment for why it isn't derived from trades_log).
            session_start = self._taifex_session_start_ts(now)
            if self.cvd_session_start.get(symbol) != session_start:
                self.cvd_session_start[symbol] = session_start
                self.cvd_cumulative[symbol] = 0
                self.cvd_points[symbol] = deque(maxlen=self._TRADES_LOG_MAXLEN)
            signed_size = int(size) if side == 'buy' else -int(size)
            self.cvd_cumulative[symbol] = self.cvd_cumulative.get(symbol, 0) + signed_size
            self.cvd_points[symbol].append({'ts': now, 'value': self.cvd_cumulative[symbol]})

    def get_recent_trades(self, symbol, since_ts=None):
        """ Returns cached trade prints for symbol, optionally only those at/after since_ts (epoch seconds). """
        log = self.trades_log.get(symbol)
        if not log:
            return []
        if since_ts is None:
            return list(log)
        return [t for t in log if t['ts'] >= since_ts]

    def get_momentum_bar_30m(self, symbol):
        """
        Aggregates the current (in-progress) 30-minute bar's three momentum
        lines, per 陳玠儒/股市擺渡人's methodology (see
        ../trading room/TRADING_ROOM_PROJECT_STATE.md for the full writeup):

          - big_order_diff (大戶委託口差): sum(bid sizes) - sum(ask sizes)
            from the current top-5 Books snapshot. This is an APPROXIMATION
            of the original concept (large resting orders specifically) —
            we only have top-5 depth, not a full order book we could filter
            by order size, so this uses total top-5 committed size on each
            side as the proxy. Documented, not hidden.
          - retail_trade_count_diff (散戶成交筆數差): count of buy-side trade
            prints minus count of sell-side trade prints in this bar — COUNT
            of prints, not summed volume, per the methodology.
          - market_order_diff (市場委買委賣口差): same top-5 Books snapshot as
            big_order_diff. With only top-5 depth available (not the full
            market's resting orders), this session has no way to compute a
            genuinely different "whole market" number from the "big player"
            number — both currently read the same Books snapshot. Flagged
            here rather than silently faked into two different-looking lines.

        Returns None if no book/trades data is cached yet for symbol.
        """
        book = self.books_cache.get(symbol)
        if not book:
            return None

        bid_total = sum(lvl['size'] for lvl in book.get('bids', []))
        ask_total = sum(lvl['size'] for lvl in book.get('asks', []))
        big_order_diff = bid_total - ask_total

        now = time.time()
        bar_start = now - (now % 1800)  # current 30-minute wall-clock bucket
        recent = self.get_recent_trades(symbol, since_ts=bar_start)
        buy_count = sum(1 for t in recent if t['side'] == 'buy')
        sell_count = sum(1 for t in recent if t['side'] == 'sell')

        return {
            'symbol': symbol,
            'bar_start_ts': bar_start,
            'big_order_diff': big_order_diff,
            'retail_trade_count_diff': buy_count - sell_count,
            'market_order_diff': big_order_diff,  # see docstring: same source as big_order_diff for now
            'trade_count_in_bar': len(recent),
            'is_trial': bool(book.get('is_trial', False)),
            'updated_ts': now
        }

    def _mom_hist_path(self, alias):
        safe = alias.replace('!', '_')
        return os.path.join(self._mom_hist_dir, safe + ".json")

    def _mom_hist_load(self, alias):
        """Lazy-load one symbol's saved bars from disk the first time it is touched."""
        if alias in self._mom_hist:
            return
        bars = {}
        try:
            import json as _json
            with open(self._mom_hist_path(alias), encoding="utf-8") as f:
                for b in _json.load(f):
                    bars[int(b['t'])] = b
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.warning(f"momentum history load failed for {alias}: {e}")
        self._mom_hist[alias] = bars

    def record_momentum_bars(self):
        """
        每 15 秒呼叫：更新目前與上一個「分鐘」的紀錄（買賣筆數／口數由 trades_log 重算，重複呼叫結果相同）。
        欄位：t 分鐘起點、bid／ask 該分鐘最後一次五檔買／賣量合計、bid_avg／ask_avg 該分鐘內快照平均、
        big=bid-ask（與 get_momentum_bar_30m 同定義）、buy_n／sell_n 買／賣筆數、buy_v／sell_v 買／賣口數、n 成交筆數。
        只存真實收到的資料；沒連線的分鐘不會補值。
        """
        now = time.time()
        cur = int(now - now % 60)
        with self._mom_hist_lock:
            for alias in list(self._books_subscribed):
                book = self.books_cache.get(alias)
                if not book:
                    continue
                self._mom_hist_load(alias)
                hist = self._mom_hist[alias]
                bid = sum(l['size'] for l in book.get('bids', []))
                ask = sum(l['size'] for l in book.get('asks', []))
                for t in (cur - 60, cur):
                    trades = [x for x in self.get_recent_trades(alias, since_ts=t) if x['ts'] < t + 60]
                    rec = hist.get(t)
                    if t == cur:
                        if rec is None:
                            rec = {'t': t, 'bid': bid, 'ask': ask, 'bid_avg': bid, 'ask_avg': ask, 'snaps': 1}
                        else:
                            k = rec.get('snaps', 1)
                            rec['bid_avg'] = (rec['bid_avg'] * k + bid) / (k + 1)
                            rec['ask_avg'] = (rec['ask_avg'] * k + ask) / (k + 1)
                            rec['snaps'] = k + 1
                            rec['bid'], rec['ask'] = bid, ask
                    elif rec is None:
                        continue   # 上一分鐘沒有任何快照（服務當時沒在跑）就不補
                    rec['big'] = rec['bid'] - rec['ask']
                    rec['buy_n'] = sum(1 for x in trades if x['side'] == 'buy')
                    rec['sell_n'] = sum(1 for x in trades if x['side'] == 'sell')
                    rec['buy_v'] = sum(x['size'] for x in trades if x['side'] == 'buy')
                    rec['sell_v'] = sum(x['size'] for x in trades if x['side'] == 'sell')
                    rec['n'] = len(trades)
                    hist[t] = rec
                self._mom_hist_dirty.add(alias)
                if alias in self._RAW_LOG_ALIASES:
                    self._append_raw_snapshot(alias, now, book)

    # 還原 JJ（rStock）指標定義用：只對少數商品把每 15 秒的原始五檔＋該 15 秒成交寫成 jsonl（每天一個檔，不進 git）
    _RAW_LOG_ALIASES = ("TXF1!", "CCF1!")

    def _append_raw_snapshot(self, alias, now, book):
        import json as _json
        try:
            os.makedirs(self._mom_hist_dir, exist_ok=True)
            day = datetime.datetime.fromtimestamp(now, tz=self._TAIPEI_TZ).strftime("%Y%m%d")
            trades = self.get_recent_trades(alias, since_ts=now - 15)
            row = {'ts': round(now, 1), 'alias': alias,
                   'bids': [[l['price'], l['size']] for l in book.get('bids', [])],
                   'asks': [[l['price'], l['size']] for l in book.get('asks', [])],
                   'trades_15s': [[x['ts'], x['price'], x['size'], x['side']] for x in trades]}
            with open(os.path.join(self._mom_hist_dir, f"raw_{day}.jsonl"), "a", encoding="utf-8") as f:
                f.write(_json.dumps(row, separators=(',', ':')) + "\n")
        except Exception as e:
            logging.warning(f"raw snapshot log failed: {e}")

    def save_momentum_history(self):
        import json as _json
        cutoff = time.time() - self._mom_hist_keep_days * 86400
        with self._mom_hist_lock:
            os.makedirs(self._mom_hist_dir, exist_ok=True)
            for alias in list(self._mom_hist_dirty):
                rows = sorted((b for b in self._mom_hist[alias].values() if b['t'] >= cutoff), key=lambda b: b['t'])
                self._mom_hist[alias] = {b['t']: b for b in rows}
                tmp = self._mom_hist_path(alias) + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    _json.dump(rows, f, separators=(',', ':'))
                os.replace(tmp, self._mom_hist_path(alias))
            self._mom_hist_dirty.clear()

    def get_momentum_history(self, symbol, days=5, tf_minutes=30):
        """
        1 分鐘紀錄合成 tf_minutes 分鐘的 bar（oldest first）。合成規則：big／bid／ask＝該 bar 最後一分鐘的快照
        （與即時 30 分 bar 同定義）、bid_avg／ask_avg＝各分鐘平均再平均、買賣筆數與口數＝加總；
        retail＝buy_n−sell_n、mkt＝big（與即時端點一致，來源相同）。
        """
        alias = self.CVD_SYMBOL_ALIAS.get(symbol, symbol)
        tf_sec = max(1, int(tf_minutes)) * 60
        with self._mom_hist_lock:
            self._mom_hist_load(alias)
            cutoff = time.time() - days * 86400
            rows = sorted((b for b in self._mom_hist[alias].values() if b['t'] >= cutoff and 'buy_n' in b), key=lambda b: b['t'])
        out = {}
        for r in rows:
            k = int(r['t'] // tf_sec * tf_sec)
            g = out.get(k)
            if g is None:
                g = out[k] = {'t': k, 'buy_n': 0, 'sell_n': 0, 'buy_v': 0, 'sell_v': 0, 'n': 0, '_ba': 0.0, '_aa': 0.0, '_m': 0}
            g['buy_n'] += r['buy_n']; g['sell_n'] += r['sell_n']
            g['buy_v'] += r['buy_v']; g['sell_v'] += r['sell_v']; g['n'] += r['n']
            g['_ba'] += r['bid_avg']; g['_aa'] += r['ask_avg']; g['_m'] += 1
            g['bid'], g['ask'], g['big'] = r['bid'], r['ask'], r['big']
        res = []
        for k in sorted(out):
            g = out[k]
            m = g.pop('_m'); ba = g.pop('_ba'); aa = g.pop('_aa')
            g['bid_avg'] = round(ba / m, 2); g['ask_avg'] = round(aa / m, 2)
            g['retail'] = g['buy_n'] - g['sell_n']
            g['mkt'] = g['big']
            res.append(g)
        return res

    def start_momentum_recorder(self):
        """Idempotent: background thread that records every 15 s and saves to disk every 60 s."""
        if self._mom_hist_started:
            return
        self._mom_hist_started = True
        def _loop():
            last_save = 0
            while True:
                try:
                    self.record_momentum_bars()
                    if time.time() - last_save >= 60:
                        self.save_momentum_history()
                        last_save = time.time()
                except Exception as e:
                    logging.warning(f"momentum recorder error: {e}")
                time.sleep(15)
        threading.Thread(target=_loop, daemon=True, name="momentum-recorder").start()

    def get_cvd_series(self, symbol, max_points=3000):
        """
        Returns the real tick-rule Cumulative Volume Delta series for `symbol`'s current
        TAIFEX session, as {'ts','value'} snapshots taken after every real trade print
        received since this process started tracking (see _process_trades_data()).

        `symbol` accepts either the room's UI code (TXF/MXF/MTX/TMF, via CVD_SYMBOL_ALIAS) or the raw
        Fubon alias directly — trades are tracked and stored under the Fubon alias, since that is what
        _process_trades_data() receives on the wire. A UI code the alias map doesn't know is used as-is.

        Deliberately has NO backfill before this process's own tracking began — unlike
        klines, there is no historical tick archive to reconstruct real CVD from, so a
        session that started before this server connected will show a shorter series
        than the true full-session CVD, not a wrong one. Downsamples evenly to
        `max_points` for payload size when a session has produced more ticks than that,
        always keeping the true latest point so the live edge is never stale.

        Returns None if no trade has been received yet for this symbol this session.
        """
        symbol = self.CVD_SYMBOL_ALIAS.get(symbol, symbol)
        points = self.cvd_points.get(symbol)
        if not points:
            return None

        pts = list(points)
        if len(pts) > max_points:
            step = len(pts) / max_points
            thinned = [pts[int(i * step)] for i in range(max_points)]
            thinned[-1] = pts[-1]
            pts = thinned

        book = self.books_cache.get(symbol)
        return {
            'symbol': symbol,
            'session_start_ts': self.cvd_session_start.get(symbol),
            'cumulative_delta': self.cvd_cumulative.get(symbol, 0),
            'trade_count_in_session': len(points),
            'points': pts,
            'is_trial': bool(book.get('is_trial', False)) if book else False,
            'updated_ts': time.time()
        }


# Global singleton instance for app-wide access
fubon_provider = FubonAPIProvider()

if __name__ == "__main__":
    print("=== Fubon API Provider Diagnostic Test ===")
    print(f"Status Active: {fubon_provider.is_active}")
    if fubon_provider.is_active:
        quotes = fubon_provider.get_live_quotes()
        print(f"Data Source Mode: {quotes['source']}")
        print(f"Live TXF Quote: {quotes['txf_price']} (Change: {quotes['change']} / {quotes['pct']}%)")
    else:
        print("Fubon Provider operating in FALLBACK mode.")
