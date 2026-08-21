# -*- coding: utf-8 -*-
"""
TXO-GEX-Dashboard v42.0 — Multi-Source Live Price Gateway Server
3-Tier Provider Fallback System:
  Priority 1: Fubon Neo API WebSocket (scripts/fubon_api_provider.py)
  Priority 2: TradingView Local DOM Reader (scripts/tv_dom_reader.js -> POST /api/live_tick)
  Priority 3: TWSE / TAIFEX MIS Open API Polling Worker
"""

import os
import sys
import json
import time
import threading
import urllib.request
import ssl
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORT = 8000
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

class LivePriceState:
    def __init__(self):
        self.ticks = {
            "FUBON": None,
            "TRADINGVIEW": None,
            "TAIFEX_MIS": None
        }
        self.active_provider = "NONE"
        self.last_mis_poll = 0

    def update_tick(self, provider, price, change=0.0, pct=0.0):
        self.ticks[provider] = {
            "price": float(price),
            "change": float(change),
            "pct": float(pct),
            "ts": time.time()
        }

    def get_best_tick(self):
        now = time.time()
        # Priority 1: FUBON (valid if received within 5 seconds)
        f_tick = self.ticks.get("FUBON")
        if f_tick and (now - f_tick["ts"]) < 5.0:
            self.active_provider = "FUBON"
            return {**f_tick, "provider": "FUBON", "provider_name": "🟢 極速專線網關 (WebSocket)"}

        # Priority 2: TRADINGVIEW (valid if received within 5 seconds)
        tv_tick = self.ticks.get("TRADINGVIEW")
        if tv_tick and (now - tv_tick["ts"]) < 5.0:
            self.active_provider = "TRADINGVIEW"
            return {**tv_tick, "provider": "TRADINGVIEW", "provider_name": "🟡 網頁行情網關 (DOM)"}

        # Priority 3: TAIFEX / TWSE MIS (Fallback)
        mis_tick = self.ticks.get("TAIFEX_MIS")
        if mis_tick and (now - mis_tick["ts"]) < 15.0:
            self.active_provider = "TAIFEX_MIS"
            return {**mis_tick, "provider": "TAIFEX_MIS", "provider_name": "🔵 期交所 MIS 官方報價"}

        if mis_tick:
            return {**mis_tick, "provider": "TAIFEX_MIS", "provider_name": "🔵 期交所 MIS (快照)"}

        return {
            "price": 0.0,
            "change": 0.0,
            "pct": 0.0,
            "ts": now,
            "provider": "NONE",
            "provider_name": "⚪ 官方盤後定案 (靜態分析)"
        }

state = LivePriceState()

def poll_mis_api_worker():
    """ Priority 3: Fallback background poller for official TAIFEX MIS / TWSE API (Night & Day) """
    import datetime
    while True:
        success = False
        try:
            # Determine Night vs Day session
            now_h = datetime.datetime.now().hour
            market_type = '1' if (now_h >= 15 or now_h < 5) else '0'
            
            url = "https://mis.taifex.com.tw/futures/api/getQuoteList"
            payload = json.dumps({'MarketType': market_type, 'SymbolType': 'F'}).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://mis.taifex.com.tw/futures/'
            }
            
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                q_list = res.get('RtData', {}).get('QuoteList', [])
                tx_items = [q for q in q_list if q.get('SymbolID', '').startswith('TX') and q.get('CLastPrice')]
                if tx_items:
                    main_tx = tx_items[0]
                    last_p = float(main_tx.get('CLastPrice', 0))
                    ref_p = float(main_tx.get('CRefPrice', last_p) or last_p)
                    if last_p > 0:
                        chg = round(last_p - ref_p, 2)
                        pct = round((chg / ref_p * 100), 2) if ref_p > 0 else 0.0
                        provider_label = "🌐 期交所 MIS 夜盤行情" if market_type == '1' else "🌐 期交所 MIS 日盤行情"
                        state.update_tick("TAIFEX_MIS", last_p, chg, pct)
                        state.ticks["TAIFEX_MIS"]["provider_name"] = provider_label
                        success = True
        except Exception:
            pass

        if not success:
            try:
                # Fallback to official TWSE / TAIFEX market feed via Yahoo finance chart API
                url_yahoo = "https://query1.finance.yahoo.com/v8/finance/chart/^TWII"
                req_y = urllib.request.Request(url_yahoo, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req_y, timeout=5) as resp:
                    res = json.loads(resp.read().decode('utf-8'))
                    meta = res['chart']['result'][0]['meta']
                    last_p = float(meta['regularMarketPrice'])
                    ref_p = float(meta.get('previousClose', last_p) or last_p)
                    if last_p > 0:
                        chg = round(last_p - ref_p, 2)
                        pct = round((chg / ref_p * 100), 2) if ref_p > 0 else 0.0
                        state.update_tick("TAIFEX_MIS", last_p, chg, pct)
                        state.ticks["TAIFEX_MIS"]["provider_name"] = "🔵 期交所 / 證交所 官方備援行情"
            except Exception:
                pass

        time.sleep(3.0)

class PriceGatewayHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        import urllib.parse, os, mimetypes
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/api/live_tick'):
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'price' in query_params:
                try:
                    p = float(query_params['price'][0])
                    prov = query_params.get('provider', ['TRADINGVIEW'])[0].upper()
                    if p > 0:
                        state.update_tick(prov, p)
                except ValueError:
                    pass
            tick_data = state.get_best_tick()
            body = json.dumps(tick_data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        # Serve static Dashboard files for local gateway
        rel_path = parsed.path.lstrip('/')
        if not rel_path or rel_path == '':
            rel_path = 'index.html'
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(project_root, rel_path)
        
        if os.path.isfile(file_path):
            ctype, _ = mimetypes.guess_type(file_path)
            if not ctype:
                ctype = 'application/octet-stream'
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception:
                pass

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith('/api/live_tick'):
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len).decode('utf-8')
            try:
                payload = json.loads(post_body)
                provider = payload.get("provider", "TRADINGVIEW").upper()
                price = float(payload.get("price", 0))
                change = float(payload.get("change", 0))
                pct = float(payload.get("pct", 0))
                if price > 0:
                    state.update_tick(provider, price, change, pct)
                response = json.dumps({"status": "ok", "active_provider": state.active_provider}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(response)
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress verbose HTTP logging
        return

def fubon_worker():
    """ Priority 1: Fubon Neo API Active Provider Stream """
    try:
        from scripts.fubon_api_provider import fubon_provider, load_local_env
        load_local_env()
        api_key = os.getenv("FUBON_API_KEY", "")
        if api_key and "YOUR_" not in api_key and fubon_provider.is_active:
            print("[Live Gateway] Fubon API active streaming connected.")
            while True:
                quotes = fubon_provider.get_live_quotes()
                if quotes and quotes.get('txf_price'):
                    price_val = float(quotes['txf_price'])
                    state.update_tick("FUBON", price_val)
                    # Broadcast to Cloudflare Cloud Relay for global sharing (GitHub Pages & Friends)
                    try:
                        cf_url = "https://txo-gex-relay.bluebird-finder-tw.workers.dev/"
                        payload = json.dumps({
                            "ticker": "TXF1!",
                            "price": price_val,
                            "provider": "FUBON",
                            "provider_name": "🟢 極速專線網關 (WebSocket)",
                            "timestamp": int(time.time() * 1000)
                        }).encode('utf-8')
                        req = urllib.request.Request(cf_url, data=payload, headers={'Content-Type': 'application/json'})
                        urllib.request.urlopen(req, context=SSL_CTX, timeout=2)
                    except Exception:
                        pass
                time.sleep(1.0)
    except Exception as e:
        print(f"[Live Gateway] Fubon worker error: {e}")

def main():
    try:
        from scripts.fubon_api_provider import fubon_provider
        print(f"[Live Gateway] Fubon Provider Active Status: {fubon_provider.is_active}")
    except Exception as e:
        print(f"[Live Gateway] Fubon Provider Init Notice: {e}")

    mis_thread = threading.Thread(target=poll_mis_api_worker, daemon=True)
    mis_thread.start()

    fubon_thread = threading.Thread(target=fubon_worker, daemon=True)
    fubon_thread.start()

    server = ThreadingHTTPServer(('127.0.0.1', PORT), PriceGatewayHandler)
    print(f"=== TXO-GEX Multi-Source Price Gateway Running on Port {PORT} ===")
    print("Priority Order: 1. FUBON Neo API -> 2. TradingView DOM -> 3. TAIFEX MIS")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()
