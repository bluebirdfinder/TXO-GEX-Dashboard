# -*- coding: utf-8 -*-
"""
TXO-GEX-Dashboard v42.0 — Multi-Source Live Price Gateway Server
3-Tier Provider Fallback System:
  Priority 1: Fubon Neo API WebSocket (scripts/fubon_api_provider.py)
  Priority 2: TradingView Local DOM Reader (scripts/tv_dom_reader.js -> POST /api/live_tick)
  Priority 3: TWSE / TAIFEX MIS Open API Polling Worker
"""

import json
import time
import threading
import urllib.request
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8000
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

class LivePriceState:
    def __init__(self):
        self.lock = threading.Lock()
        self.ticks = {
            "FUBON": None,        # {"price": float, "change": float, "pct": float, "ts": float}
            "TRADINGVIEW": None,
            "TAIFEX_MIS": None
        }
        self.active_provider = "NONE"
        self.last_mis_poll = 0

    def update_tick(self, provider, price, change=0.0, pct=0.0):
        with self.lock:
            self.ticks[provider] = {
                "price": float(price),
                "change": float(change),
                "pct": float(pct),
                "ts": time.time()
            }

    def get_best_tick(self):
        now = time.time()
        with self.lock:
            # Priority 1: FUBON (valid if received within 5 seconds)
            f_tick = self.ticks["FUBON"]
            if f_tick and (now - f_tick["ts"]) < 5.0:
                self.active_provider = "FUBON"
                return {**f_tick, "provider": "FUBON", "provider_name": "🟢 極速專線網關 (WebSocket)"}

            # Priority 2: TRADINGVIEW (valid if received within 5 seconds)
            tv_tick = self.ticks["TRADINGVIEW"]
            if tv_tick and (now - tv_tick["ts"]) < 5.0:
                self.active_provider = "TRADINGVIEW"
                return {**tv_tick, "provider": "TRADINGVIEW", "provider_name": "🟡 網頁行情網關 (DOM)"}

            # Priority 3: TAIFEX / TWSE MIS (Fallback)
            mis_tick = self.ticks["TAIFEX_MIS"]
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
    """ Priority 3: Fallback background poller for TWSE/TAIFEX MIS API """
    while True:
        try:
            # Poll TAIFEX / TWSE MIS indices
            url = f"https://mis.twse.com.tw/stock/api/getFuturesInfo.jsp?ex=tse&ch=txf&_={int(time.time()*1000)}"
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                msg_list = data.get('msgArray', [])
                if msg_list:
                    item = msg_list[0]
                    # 'z' is last price, 'y' is yesterday close
                    last_price = float(item.get('z', item.get('pz', 0) or 0))
                    ref_price = float(item.get('y', 0) or last_price)
                    if last_price > 0:
                        chg = round(last_price - ref_price, 2)
                        pct = round((chg / ref_price * 100), 2) if ref_price > 0 else 0.0
                        state.update_tick("TAIFEX_MIS", last_price, chg, pct)
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
        if self.path.startswith('/api/live_tick') or self.path == '/':
            tick_data = state.get_best_tick()
            body = json.dumps(tick_data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
        else:
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

def main():
    mis_thread = threading.Thread(target=poll_mis_api_worker, daemon=True)
    mis_thread.start()

    server = HTTPServer(('0.0.0.0', PORT), PriceGatewayHandler)
    print(f"=== TXO-GEX Multi-Source Price Gateway Running on Port {PORT} ===")
    print("Priority Order: 1. FUBON Neo API -> 2. TradingView DOM -> 3. TAIFEX MIS")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()
