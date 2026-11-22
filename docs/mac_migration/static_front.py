"""本機靜態網頁服務（8001）。只送檔案；/api/* 轉給 8000 報價服務，8000 沒回應就 3 秒內回 503，
這樣報價服務卡住時，首頁與戰情室仍然開得起來。不寫任何檔案、不連富邦。"""
import os, sys, json, urllib.request
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.environ.get("TXO_STATIC_ROOT", r"C:\Users\mingi\txo-klines-runner")
GATEWAY = "http://127.0.0.1:8000"
PORT = int(os.environ.get("TXO_STATIC_PORT", "8001"))

class H(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            try:
                with urllib.request.urlopen(GATEWAY + self.path, timeout=3) as r:
                    b = r.read(); code = r.status; ct = r.headers.get("Content-Type", "application/json")
            except Exception as e:
                b = json.dumps({"error": "報價服務暫時沒回應", "detail": str(e)[:80]}, ensure_ascii=False).encode("utf-8")
                code, ct = 503, "application/json; charset=utf-8"
            self.send_response(code); self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(b); return
        return super().do_GET()
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()
    def log_message(self, *a): pass

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), partial(H, directory=ROOT)).serve_forever()
