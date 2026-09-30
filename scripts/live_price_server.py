# -*- coding: utf-8 -*-
"""
TXO-GEX-Dashboard v50.9 — Multi-Source Live Price Gateway Server
Handles real-time streaming for TXF (台指期), TAIEX (加權指數), and OTC (櫃買指數).

Providers:
  Priority 1: Fubon Neo API SDK (Authenticated via .env credentials)
  Priority 2: Official TAIFEX / TWSE MIS API
"""

import os
import sys
import json
import time
import threading
import urllib.request
import ssl
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PORT = int(os.environ.get('TXO_GATEWAY_PORT', '8000'))
SSL_CTX = ssl.create_default_context()
# Certificate chain + hostname verification ON; only Python 3.13's strict X.509 flag is relaxed (TWSE/TPEx certs lack a Subject Key Identifier).
SSL_CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT

class LivePriceState:
    def __init__(self):
        # No stand-in prices: an index appears here only after a real quote arrived (AGENTS.md redline #6).
        self.indices = {}
        # Macro quotes (Yahoo, fetched server-side so the browser needs no CORS proxy): {"dxy": 101.03, "us10y": 5.18, "cl": 92.2, "vix": ...}
        self.macro = {}
        self.macro_ts = 0.0
        self.active_provider = "NONE"  # set by update_index() from the source that actually delivered a quote
        self.last_update = time.time()

    def update_index(self, key, price, change=0.0, pct=0.0, provider="FUBON"):
        if price > 0:
            self.indices[key] = {
                "price": float(price),
                "change": float(change),
                "pct": float(pct),
                "provider": provider,
                "ts": time.time()
            }
            self.active_provider = "FUBON" if str(provider).upper() == "FUBON" else "OFFICIAL"
            self.last_update = time.time()

state = LivePriceState()

MACRO_TICKERS = {"dxy": "DX-Y.NYB", "us10y": "%5ETNX", "cl": "CL=F", "vix": "%5EVIX", "vvix": "%5EVVIX"}


def macro_polling_worker(interval=30):
    """Real DXY / US10Y / CL / VIX / VVIX from Yahoo every `interval` seconds (Fubon Neo has TAIFEX products only). If a
    fetch fails the key is simply absent and the room keeps showing the cloud-built snapshot (fallback)."""
    while True:
        got = {}
        for key, tk in MACRO_TICKERS.items():
            try:
                req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}?interval=1d&range=1d",
                                             headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as r:
                    meta = json.loads(r.read().decode("utf-8"))["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice")
                if isinstance(price, (int, float)) and price > 0:
                    got[key] = float(price)
            except Exception as e:  # noqa: BLE001
                print(f"[Macro] {key} fetch failed: {e}")
        if got:
            state.macro = {**state.macro, **got}
            state.macro_ts = time.time()
        time.sleep(interval)


def _tw_open_days():
    import re
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tw_holidays.json")
        hol = set(re.findall(r"20\d\d-\d\d-\d\d", open(path, encoding="utf-8-sig").read()))
    except Exception:
        hol = set()
    return lambda d: d.weekday() < 5 and d.isoformat() not in hol


def watchdog_worker():
    """Keeps the Fubon connection healthy without a manual restart:
    - a fresh login shortly before each session (08:30 and 14:55) and once at start-up of the night session;
    - if a session is open (day 08:45-13:45, night 15:00-05:00 of a trading day) and no quote arrived for 120 s,
      log in again (at most once per 5 minutes)."""
    import datetime
    is_td = _tw_open_days()
    last_relogin, done_today = 0.0, set()
    while True:
        time.sleep(20)
        try:
            from scripts.fubon_api_provider import fubon_provider
            if not fubon_provider.is_active:
                continue
            now = datetime.datetime.now()
            hm = now.hour * 60 + now.minute
            today, yday = now.date(), now.date() - datetime.timedelta(days=1)
            day_open = is_td(today) and (8 * 60 + 45) <= hm <= (13 * 60 + 45)
            night_open = (now.hour >= 15 and is_td(today)) or (now.hour < 5 and is_td(yday))
            for tag, at in (("pre-day", 8 * 60 + 30), ("pre-night", 14 * 60 + 55)):
                key = (today, tag)
                if hm >= at and hm < at + 5 and key not in done_today and is_td(today):
                    done_today.add(key)
                    print(f"[Watchdog] scheduled {tag} re-login")
                    fubon_provider.relogin(); last_relogin = time.time()
            stale = time.time() - state.last_update
            if (day_open or night_open) and stale > 120 and time.time() - last_relogin > 300:
                print(f"[Watchdog] no quote for {int(stale)}s during an open session -> re-login")
                fubon_provider.relogin(); last_relogin = time.time()
        except Exception as e:  # noqa: BLE001
            print(f"[Watchdog] error: {e}")


def fubon_worker():
    """ Priority 1: Fubon Neo API Worker Thread """
    try:
        from scripts.fubon_api_provider import fubon_provider, load_local_env
        load_local_env()
        if fubon_provider.is_active:
            print("[Gateway] Fubon Neo API Worker Connected & Active!")
            state.active_provider = "FUBON"
            while True:
                quotes = fubon_provider.get_live_quotes()
                # Publish only what Fubon really returned. (This used to fall back to 47207.0 / +252 / +0.54 — a stale
                # made-up quote presented as a live Fubon tick whenever the quote call came back empty.)
                if quotes and quotes.get('txf_price'):
                    state.update_index('txf', quotes['txf_price'], quotes.get('change') or 0.0, quotes.get('pct') or 0.0, provider="FUBON")
                time.sleep(1.0)
    except Exception as e:
        print(f"[Gateway] Fubon Worker notice: {e}")

def fubon_books_worker():
    """
    Priority 1: Fubon Books (五檔委託簿) WebSocket Worker Thread.
    Waits for the REST-based fubon_worker() above to bring the SDK active, then subscribes once to every
    Fubon alias the room's CVD pane can show (TXF1!/MXF1!/TMF1! — see CVD_SYMBOL_ALIAS; MTX and TMF share
    TMF1!). Was TXF-only until 2026-09-30, which silently starved MXF/MTX/TMF's tick-rule side detection
    (get_cvd_series() falls back to "same side as the previous trade" without a books snapshot — degraded,
    not wrong, but not what the room's four-symbol CVD claims). Actual message handling happens on the
    SDK's own background thread (see FubonAPIProvider._handle_books_message); this loop just keeps the
    process alive and re-subscribes if the provider flips to active later than us.
    """
    try:
        from scripts.fubon_api_provider import fubon_provider, load_local_env
        load_local_env()
        subscribed = False
        while True:
            if fubon_provider.is_active and not subscribed:
                symbols = sorted(set(fubon_provider.CVD_SYMBOL_ALIAS.values()))
                ok = fubon_provider.start_books_stream(symbols)
                if ok:
                    print(f"[Gateway] Fubon Books Worker subscribed to {symbols} (五檔).")
                    subscribed = True
            time.sleep(5.0)
    except Exception as e:
        print(f"[Gateway] Fubon Books Worker notice: {e}")

def fubon_trades_worker():
    """
    Priority 1: Fubon Trades (逐筆成交) WebSocket Worker Thread.
    Same pattern as fubon_books_worker() — subscribes to every CVD-eligible alias once the SDK is
    active (was TXF-only, see fubon_books_worker()'s docstring), then the SDK's own background
    thread handles incoming messages.
    """
    try:
        from scripts.fubon_api_provider import fubon_provider, load_local_env
        load_local_env()
        subscribed = False
        while True:
            if fubon_provider.is_active and not subscribed:
                symbols = sorted(set(fubon_provider.CVD_SYMBOL_ALIAS.values()))
                ok = fubon_provider.start_trades_stream(symbols)
                if ok:
                    print(f"[Gateway] Fubon Trades Worker subscribed to {symbols} (逐筆成交).")
                    subscribed = True
            time.sleep(5.0)
    except Exception as e:
        print(f"[Gateway] Fubon Trades Worker notice: {e}")

def mis_polling_worker():
    """ Priority 2: Official TAIFEX / TWSE MIS API Polling Worker """
    while True:
        try:
            # Poll TAIFEX MIS for TXF
            now_h = time.localtime().tm_hour
            market_type = '1' if (now_h >= 15 or now_h < 5) else '0'
            url = "https://mis.taifex.com.tw/futures/api/getQuoteList"
            payload = json.dumps({'MarketType': market_type, 'SymbolType': 'F'}).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                q_list = res.get('RtData', {}).get('QuoteList', [])
                # Futures contracts only (day '-F', night '-M'), nearest month first as TAIFEX lists them. The old filter
                # startswith('TX') also matched 'TXF-S' (臺指現貨, the SPOT index), which comes first in the day list, so the
                # spot index was published as the TXF futures price (and its previous close as the reference).
                tx_items = [q for q in q_list
                            if q.get('SymbolID', '').startswith('TXF') and q.get('SymbolID', '').endswith(('-F', '-M')) and q.get('CLastPrice')]
                if tx_items:
                    main_tx = tx_items[0]
                    last_p = float(main_tx.get('CLastPrice', 0))
                    ref_p = float(main_tx.get('CRefPrice', last_p) or last_p)
                    if last_p > 0:
                        chg = round(last_p - ref_p, 2)
                        pct = round((chg / ref_p * 100), 2) if ref_p > 0 else 0.0
                        state.update_index('txf', last_p, chg, pct, provider="TAIFEX_MIS")
        except Exception as e:
            pass

        # Poll Yahoo Finance for TAIEX & OTC
        try:
            url_y = "https://query1.finance.yahoo.com/v8/finance/chart/^TWII"
            req_y = urllib.request.Request(url_y, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_y, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                meta = res['chart']['result'][0]['meta']
                last_p = float(meta['regularMarketPrice'])
                ref_p = float(meta.get('previousClose', last_p) or last_p)
                chg = round(last_p - ref_p, 2)
                pct = round((chg / ref_p * 100), 2) if ref_p > 0 else 0.0
                state.update_index('taiex', last_p, chg, pct, provider="TWSE")
        except Exception:
            pass

        time.sleep(3.0)

class PriceGatewayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard HTTP request logging to clean stdout/stderr
        pass

    _ALLOWED_ORIGINS = ("https://bluebirdfinder.github.io",)

    def _origin_allowed(self, origin):
        import urllib.parse
        if origin in self._ALLOWED_ORIGINS:
            return True
        try:
            u = urllib.parse.urlparse(origin)
            return u.scheme in ("http", "https") and u.hostname in ("localhost", "127.0.0.1")
        except Exception:
            return False

    def _send_cors(self):
        # Was 'Access-Control-Allow-Origin: *' (any website could read this server from the user's browser).
        origin = self.headers.get('Origin', '')
        if origin and self._origin_allowed(origin):
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _host_ok(self):
        # DNS-rebinding guard: only answer requests addressed to the loopback name/IP.
        host = (self.headers.get('Host') or '').split(':')[0].lower()
        return host in ('localhost', '127.0.0.1', '[::1]', '')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        try:
            import urllib.parse, mimetypes
            parsed = urllib.parse.urlparse(self.path)
            if not self._host_ok():
                self.send_response(403); self.end_headers(); return
            
            # API Endpoint for Live Indices (TXF, TAIEX, OTC)
            if parsed.path.startswith('/api/live_tick') or parsed.path.startswith('/api/live_price'):
                res_data = {
                    "active_provider": state.active_provider,
                    "provider_name": "🟢 富邦 API 極速專線" if state.active_provider == "FUBON" else ("🌐 官方行情備援" if state.active_provider == "OFFICIAL" else "⚪ 無即時數據"),
                    "indices": state.indices,
                    "age_sec": round(time.time() - state.last_update, 1),  # seconds since the last real quote (front end can flag stale data)
                    "ts": time.time()
                }
                for _k in ("txf", "taiex", "otc"):
                    if _k in state.indices:  # only real quotes; the front end skips missing ones
                        res_data[_k] = state.indices[_k]
                if state.macro:
                    res_data["macro"] = {**state.macro, "ts": state.macro_ts}
                body = json.dumps(res_data, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._send_cors()
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                return

            # API Endpoint for Books (五檔委託簿) — ?symbol=TXFA4, defaults to current TXF front-month
            if parsed.path.startswith('/api/books'):
                from scripts.fubon_api_provider import fubon_provider
                qs = urllib.parse.parse_qs(parsed.query)
                symbol = (qs.get('symbol', [None])[0]) or fubon_provider.txf_symbol
                book = fubon_provider.get_book(symbol)
                res_data = {
                    "symbol": symbol,
                    "book": book,
                    "subscribed": symbol in fubon_provider._books_subscribed,
                    "ts": time.time()
                }
                body = json.dumps(res_data, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._send_cors()
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                return

            # API Endpoint for 大戶散戶動能 30-min momentum bar — ?symbol=TXFA4
            if parsed.path.startswith('/api/momentum'):
                from scripts.fubon_api_provider import fubon_provider
                qs = urllib.parse.parse_qs(parsed.query)
                symbol = (qs.get('symbol', [None])[0]) or fubon_provider.txf_symbol
                bar = fubon_provider.get_momentum_bar_30m(symbol)
                res_data = {
                    "symbol": symbol,
                    "bar": bar,
                    "books_subscribed": symbol in fubon_provider._books_subscribed,
                    "trades_subscribed": symbol in fubon_provider._trades_subscribed,
                    "ts": time.time()
                }
                body = json.dumps(res_data, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._send_cors()
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                return

            # API Endpoint for real tick-rule CVD (Cumulative Volume Delta) — ?symbol=TXF (room UI code) or a raw Fubon alias
            if parsed.path.startswith('/api/cvd'):
                from scripts.fubon_api_provider import fubon_provider
                qs = urllib.parse.parse_qs(parsed.query)
                symbol = (qs.get('symbol', [None])[0]) or 'TXF'
                # Found 2026-09-30 testing: the room sends its UI code (TXF/MXF/MTX/TMF) but trades are tracked
                # under the Fubon alias (TXF1! etc) — comparing the UI code against _trades_subscribed (which
                # only ever holds aliases) was always False, so the CVD pane permanently showed "not connected"
                # even when it was. Map to the alias before touching either.
                alias = fubon_provider.CVD_SYMBOL_ALIAS.get(symbol, symbol)
                series = fubon_provider.get_cvd_series(alias)
                res_data = {
                    "symbol": symbol,
                    "series": series,
                    "trades_subscribed": alias in fubon_provider._trades_subscribed,
                    "ts": time.time()
                }
                body = json.dumps(res_data, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._send_cors()
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                return

            # Serve static Dashboard files
            rel_path = parsed.path.lstrip('/')
            if not rel_path or rel_path == '':
                rel_path = 'index.html'
            
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.normpath(os.path.join(project_root, urllib.parse.unquote(rel_path)))

            # Static files: ONLY public dashboard assets. The project root also holds .env (Fubon API key + certificate
            # password), scripts, logs and .git — none of that may ever be served (this used to serve everything:
            # GET /.env returned the secrets, and ../ walked out of the folder).
            real_root, real_file = os.path.realpath(project_root), os.path.realpath(file_path)
            rel_parts = os.path.relpath(real_file, real_root).replace(os.sep, '/').split('/')
            ext_ok = os.path.splitext(real_file)[1].lower() in (
                '.html', '.js', '.css', '.json', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.webp', '.woff', '.woff2', '.map')
            bad_name = any(k in os.path.basename(real_file).lower() for k in ('env', 'secret', 'cert', 'password', 'credential', 'token'))
            blocked_dir = rel_parts[0] in ('scripts', 'logs', 'docs', 'memory', '__pycache__', 'node_modules') or any(seg.startswith('.') for seg in rel_parts)
            inside = os.path.commonpath([real_root, real_file]) == real_root
            if not (inside and ext_ok and not bad_name and not blocked_dir):
                self.send_response(404); self.end_headers(); return

            if os.path.isfile(file_path):
                ctype, _ = mimetypes.guess_type(file_path)
                if not ctype:
                    ctype = 'application/octet-stream'
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', ctype)
                    self.send_header('Content-Length', str(len(content)))
                    self._send_cors()
                    self.end_headers()
                    self.wfile.write(content)
                    self.wfile.flush()
                    return
                except Exception as ex_file:
                    print(f"[Gateway] File serve error: {ex_file}")

            self.send_response(404)
            self.end_headers()
        except Exception as e:
            print(f"[Gateway] Handler error: {e}")
            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass

def run_server():
    # Loopback only: this process serves market data and the dashboard files to a browser on THIS machine. Binding 0.0.0.0
    # (what it used to do) exposed it to the whole LAN. Set TXO_GATEWAY_HOST to override on purpose.
    server = ThreadingHTTPServer((os.environ.get('TXO_GATEWAY_HOST', '127.0.0.1'), PORT), PriceGatewayHandler)
    print(f"=== 🦅 尋鳥戰情室 — 實時行情 Server 啟動於 http://localhost:{PORT} ===")
    
    # Start worker threads
    threading.Thread(target=macro_polling_worker, daemon=True).start()
    threading.Thread(target=watchdog_worker, daemon=True).start()
    t_fubon = threading.Thread(target=fubon_worker, daemon=True)
    t_fubon.start()
    
    t_mis = threading.Thread(target=mis_polling_worker, daemon=True)
    t_mis.start()

    t_books = threading.Thread(target=fubon_books_worker, daemon=True)
    t_books.start()

    t_trades = threading.Thread(target=fubon_trades_worker, daemon=True)
    t_trades.start()

    server.serve_forever()

if __name__ == "__main__":
    run_server()
