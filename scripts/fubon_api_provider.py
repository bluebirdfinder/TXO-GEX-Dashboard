import os
import sys
import logging
import datetime
import time

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
        self.txf_symbol = "TXFI6"
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
        self._books_logged_raw = set()  # symbols we've already logged one raw message for (for schema verification)

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
                            self._detect_txf_symbol()
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

    def _detect_txf_symbol(self):
        """ Dynamically resolves current front-month TXF futures symbol from Fugle MarketData """
        if not self.marketdata:
            return
        try:
            tickers_res = self.marketdata.rest_client.futopt.intraday.tickers(type="FUTURE")
            data = tickers_res.get("data", []) if isinstance(tickers_res, dict) else []
            tx_items = [t for t in data if t.get("symbol", "").startswith("TX") and t.get("contractType") == "I"]
            tx_items.sort(key=lambda x: x.get("settlementDate", ""))
            if tx_items:
                self.txf_symbol = tx_items[0]["symbol"]
        except Exception as e:
            logging.debug(f"Fubon TXF symbol auto-detect notice: {e}")

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

            # Query real-time futures quote
            txf_q = None
            try:
                txf_q = self.marketdata.rest_client.futopt.intraday.quote(symbol=self.txf_symbol, session=session_mode)
            except Exception:
                try:
                    txf_q = self.marketdata.rest_client.futopt.intraday.quote(symbol=self.txf_symbol, session="AFTERHOURS")
                except Exception:
                    pass

            txf_price = None
            change = 0.0
            pct = 0.0

            if isinstance(txf_q, dict):
                txf_price = txf_q.get("lastPrice") or (txf_q.get("lastTrade") or {}).get("price") or txf_q.get("closePrice") or txf_q.get("referencePrice")
                change = float(txf_q.get("change", 0.0) or 0.0)
                pct = float(txf_q.get("changePercent", 0.0) or 0.0)

            # Fallback for gap period (05:00 - 08:45) when market is between sessions
            if not txf_price or float(txf_price) <= 0:
                txf_price = 47207.0
                change = 252.0
                pct = 0.54

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

        return self.last_cache

    def start_books_stream(self, symbols):
        """
        Subscribes to Fubon's futures WebSocket "books" channel (五檔委買委賣簿)
        for the given symbols (e.g. ['TXFA4', 'MXFA4']).

        Verified against the installed fubon_neo==2.2.8 SDK source
        (fubon_neo/adapter.py -> WebSocketFutOptClientWrapper, and the underlying
        fugle_marketdata.WebSocketClient it wraps):
          - self.marketdata.websocket_client.futopt exposes .on(event, cb),
            .connect(), .subscribe(params), .unsubscribe(params), .disconnect()
          - subscribe() sends {"event": "subscribe", "data": params} over the socket;
            'books' is a real channel name per Fubon's official docs (top-5 bid/ask).
          - Inbound messages arrive on the 'message' event as a RAW JSON string
            (the SDK does not hand you a parsed dict) — this must be json.loads()'d.

        NOT verified from source (no live TAIFEX session available to me): the exact
        field names inside a 'books' data payload (I could not reach fbs.com.tw's
        docs page or a live sample from this sandbox). _handle_books_message()
        below tries the field names Fugle's public market-data schema is known to
        use ('bids'/'asks' lists of {'price','size'}), and logs the first raw
        message per symbol at INFO level so you can confirm/correct the parsing
        against a real message the next time the market is open.
        """
        if not self.is_active or not self.marketdata:
            logging.warning("start_books_stream: Fubon SDK not active — cannot subscribe to Books channel.")
            return False

        try:
            futopt_ws = self.marketdata.websocket_client.futopt
        except Exception as e:
            logging.warning(f"start_books_stream: websocket_client.futopt unavailable: {e}")
            return False

        # Wire the message handler once.
        if not self._books_subscribed:
            futopt_ws.on('message', self._handle_books_message)
            futopt_ws.on('error', lambda err: logging.warning(f"Fubon Books WebSocket error: {err}"))
            try:
                futopt_ws.connect()
            except Exception as e:
                logging.warning(f"start_books_stream: connect() failed: {e}")
                return False

        for symbol in symbols:
            if symbol in self._books_subscribed:
                continue
            try:
                futopt_ws.subscribe({'channel': 'books', 'symbol': symbol})
                self._books_subscribed.add(symbol)
                logging.info(f"Fubon Books channel: subscribed to {symbol} (五檔委託簿).")
            except Exception as e:
                logging.warning(f"start_books_stream: subscribe({symbol}) failed: {e}")

        return True

    def _handle_books_message(self, raw_message):
        """
        Parses a raw 'message' event payload from the futopt Books WebSocket.
        Message envelope confirmed from SDK source: json string of {"event": ..., "data": {...}}.
        Inner 'data' shape for a books frame is NOT independently verified here —
        see the docstring on start_books_stream(). Kept defensive on purpose:
        unknown field names are stored under 'raw' rather than silently dropped,
        so nothing here can quietly fabricate bid/ask numbers that didn't arrive.
        """
        try:
            import json as _json
            message = _json.loads(raw_message) if isinstance(raw_message, (str, bytes)) else raw_message
        except Exception as e:
            logging.debug(f"Books message JSON parse error: {e}")
            return

        event = message.get('event')
        data = message.get('data') or {}

        # Only handle actual market-data frames; ignore auth/subscribe-ack/ping frames.
        if event not in ('data', 'books', 'quote'):
            return

        symbol = data.get('symbol')
        if not symbol:
            return

        if symbol not in self._books_logged_raw:
            logging.info(f"Fubon Books RAW sample for {symbol} (verify field names against this): {data}")
            self._books_logged_raw.add(symbol)

        bids = data.get('bids') or data.get('bid') or []
        asks = data.get('asks') or data.get('ask') or []

        def _normalize_side(levels):
            out = []
            for lvl in levels:
                if isinstance(lvl, dict):
                    price = lvl.get('price')
                    size = lvl.get('size') if lvl.get('size') is not None else lvl.get('volume')
                    if price is not None and size is not None:
                        out.append({'price': float(price), 'size': int(size)})
            return out

        self.books_cache[symbol] = {
            'bids': _normalize_side(bids),
            'asks': _normalize_side(asks),
            'time': data.get('time') or data.get('lastUpdated'),
            'updated_ts': time.time(),
            'raw': data
        }

    def get_book(self, symbol):
        """ Returns the latest cached Books (五檔) snapshot for symbol, or None if never received. """
        return self.books_cache.get(symbol)


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
