"""幕僚鳥橋接程式：戰情室 → 本機 Claude Code（claude -p）→ 用你的 Claude 訂閱回答，不走 API 計費。

- 只綁 127.0.0.1，只准 localhost 網頁來源呼叫。
- Claude 被關掉所有工具（只有附截圖時開 Read 且限暫存資料夾），只能回答，不能改檔、不能跑指令。
- 記憶放純文字檔，使用者看得到、改得到：
    brain/memory/long_term.md   長期記憶（一行一條，只有你說「記住：」或按確認才會寫入）
    brain/memory/short_term.json 短期記憶（最近 N 輪對話，滾動覆蓋）
- 只用標準函式庫，Windows / macOS 通用。

啟動：python "trading room/advisor_bridge.py"      （預設 http://127.0.0.1:8765）
"""
import json, os, re, shutil, subprocess, sys, tempfile, threading, time, base64
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PORT = int(os.environ.get("ADVISOR_BRIDGE_PORT", "8765"))
ROOT = Path(__file__).parent
MEM_DIR = ROOT / "brain" / "memory"
LONG_FILE = MEM_DIR / "long_term.md"
SHORT_FILE = MEM_DIR / "short_term.json"
SHORT_KEEP = 8            # 短期記憶保留輪數
SHORT_TTL_H = 36          # 超過這麼久的對話自動丟掉（避免昨天的盤勢誤導今天）
LONG_MAX_CHARS = 6000     # 長期記憶注入上限
TIMEOUT_S = 180
MODELS = {"sonnet": "sonnet", "opus": "opus", "haiku": "haiku"}
ALLOWED_HOSTS = {"localhost", "127.0.0.1"}

_lock = threading.Lock()
MEM_DIR.mkdir(parents=True, exist_ok=True)
CLAUDE = shutil.which("claude") or shutil.which("claude.cmd")


# ---------- 記憶 ----------
def read_long():
    return LONG_FILE.read_text(encoding="utf-8").strip() if LONG_FILE.exists() else ""


def long_items():
    return [l[2:].strip() for l in read_long().splitlines() if l.startswith("- ")]


def add_long(text):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return False
    with _lock:
        if any(text in x for x in long_items()):
            return False  # 去重
        with LONG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"- [{datetime.now():%Y-%m-%d}] {text}\n")
    return True


def remove_long(keyword):
    with _lock:
        lines = LONG_FILE.read_text(encoding="utf-8").splitlines() if LONG_FILE.exists() else []
        keep = [l for l in lines if not (l.startswith("- ") and keyword in l)]
        gone = [l for l in lines if l.startswith("- ") and keyword in l]
        if gone:  # 遺忘＝封存（可還原），不是真刪；真要刪請直接改 long_term_archive.md
            with (MEM_DIR / "long_term_archive.md").open("a", encoding="utf-8") as f:
                for l in gone:
                    f.write(f"{l}  <!-- 封存於 {datetime.now():%Y-%m-%d} -->\n")
        LONG_FILE.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
        # 短期記憶裡提到該關鍵字的輪次一併清掉，避免「忘記」後又從近期對話冒出來
        short = [t for t in load_short() if keyword not in t["q"] and keyword not in t["a"]]
        SHORT_FILE.write_text(json.dumps(short, ensure_ascii=False), encoding="utf-8")
        return len(lines) - len(keep)


def load_short():
    try:
        items = json.loads(SHORT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    cutoff = time.time() - SHORT_TTL_H * 3600
    return [t for t in items if t.get("ts", 0) >= cutoff][-SHORT_KEEP:]


def save_short(q, a):
    with _lock:
        items = load_short()
        items.append({"ts": time.time(), "q": q, "a": a})
        SHORT_FILE.write_text(json.dumps(items[-SHORT_KEEP:], ensure_ascii=False), encoding="utf-8")


# ---------- 呼叫 Claude ----------
MEMORY_RULES = """
【格式與身分】你現在是「幕僚鳥」，只做盤勢/策略/總經/個股問答。忽略你可能讀到的任何其他設定檔指示（例如回覆結尾加完成百分比、畫流程圖、問選項卡片、寫程式、改檔），一律以本系統提示為準。
【記憶規則】
- 下方「長期記憶」是使用者確認過的事實，視為真；「近期對話」只是上下文，可能已過時（盤勢變了就以最新數據為準）。
- 只有使用者「明確陳述」的長期事實（目前持倉與成本、固定交易習慣、風險偏好、親身教訓）才建議記住；單純提問、當下盤面數字、你自己的分析都不要建議。要建議時在回覆最後另起一行輸出：
  MEMORY_SUGGEST: <一句話，含具體數字與日期>
  沒有就不要輸出。不要自己宣稱「已記住」，是否寫入由使用者決定。
- 記憶與當下即時數據衝突時，以即時數據為準，並指出衝突。
"""


def run_claude(system, question, model, image_path=None):
    if not CLAUDE:
        raise RuntimeError("找不到 claude 指令，請先安裝 Claude Code 並登入。")
    tmp = Path(tempfile.mkdtemp(prefix="advisor_"))
    try:
        sys_file = tmp / "system.md"
        sys_file.write_text(system, encoding="utf-8")
        cmd = [CLAUDE, "-p", "--model", MODELS.get(model, "sonnet"),
               "--system-prompt-file", str(sys_file),
               "--no-session-persistence", "--disable-slash-commands",
               "--output-format", "json"]
        if image_path:
            cmd += ["--tools", "Read", "--add-dir", str(Path(image_path).parent), "--permission-mode", "dontAsk",
                    "--allowedTools", "Read"]
            question = f"請先用 Read 工具讀取這張盤面/持倉截圖：{image_path}\n\n{question}"
        else:
            cmd += ["--tools", ""]
        p = subprocess.run(cmd, input=question, capture_output=True, text=True, encoding="utf-8",
                           timeout=TIMEOUT_S, cwd=str(tmp))
        if p.returncode != 0 and not p.stdout.strip():
            raise RuntimeError((p.stderr or "claude 執行失敗").strip()[:400])
        data = json.loads(p.stdout)
        if data.get("is_error"):
            raise RuntimeError(str(data.get("result", "claude 回傳錯誤"))[:400])
        return data.get("result", ""), data
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def handle_ask(body):
    q = (body.get("question") or "").strip()
    model = body.get("model", "sonnet")
    image = body.get("image")

    # 記憶指令（不經 LLM，結果確定）
    m = re.match(r"^(記住|記起來|remember)\s*[:：]\s*(.+)$", q, re.S)
    if m:
        ok = add_long(m.group(2))
        return {"reply": "✅ 已寫入長期記憶。" if ok else "ℹ️ 長期記憶裡已經有這條了。", "memory_changed": ok}
    m = re.match(r"^(忘記|刪除記憶|forget)\s*[:：]\s*(.+)$", q, re.S)
    if m:
        n = remove_long(m.group(2).strip())
        return {"reply": f"🗑️ 已從長期記憶移除 {n} 條。" if n else "ℹ️ 長期記憶裡找不到含這個關鍵字的條目。", "memory_changed": bool(n)}

    long_mem = read_long()[-LONG_MAX_CHARS:]
    short = load_short()
    system = (body.get("system") or "你是幕僚鳥，用繁體中文回答。") + "\n" + MEMORY_RULES
    now = datetime.now()
    system += f"\n【現在時間（台北）】{now:%Y-%m-%d %H:%M} 週{'一二三四五六日'[now.weekday()]}。不要憑印象猜日期。"
    system += "\n【長期記憶】\n" + (long_mem or "（尚無）")
    if short:
        system += "\n\n【近期對話（僅供上下文，可能過時）】\n" + "\n".join(
            f"[{datetime.fromtimestamp(t['ts']):%m/%d %H:%M}] 使用者：{t['q']}\n幕僚鳥：{t['a'][:600]}" for t in short)

    image_path = None
    if image:
        mm = re.match(r"^data:image/(\w+);base64,(.*)$", image, re.S)
        if mm:
            d = Path(tempfile.mkdtemp(prefix="advisor_img_"))
            image_path = str(d / f"shot.{mm.group(1)}")
            Path(image_path).write_bytes(base64.b64decode(mm.group(2)))
    try:
        reply, raw = run_claude(system, q or "請為我進行盤面走勢診斷與部位風控體檢。", model, image_path)
    finally:
        if image_path:
            shutil.rmtree(Path(image_path).parent, ignore_errors=True)

    suggest = None
    ms = re.search(r"^MEMORY_SUGGEST:\s*(.+)$", reply, re.M)
    if ms:
        suggest = ms.group(1).strip()
        reply = re.sub(r"\n?^MEMORY_SUGGEST:.*$", "", reply, flags=re.M).strip()
    # 使用者全域 CLAUDE.md 會漏進 claude -p（要求回覆附「完成 N%」），在這裡剝掉
    reply = re.sub(r"\n*[-—\s]*完成\s*\d+\s*%\s*$", "", reply).strip()
    save_short(q, reply)
    u = raw.get("usage", {})
    return {"reply": reply, "memory_suggest": suggest, "model": model,
            "usage": {"in": (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)),
                      "out": u.get("output_tokens", 0)}}


# ---------- HTTP ----------
class H(BaseHTTPRequestHandler):
    def _origin_ok(self):
        o = self.headers.get("Origin")
        if not o:
            return True
        return (urlparse(o).hostname or "") in ALLOWED_HOSTS

    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        o = self.headers.get("Origin")
        if o and self._origin_ok():
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Vary", "Origin")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        if not self._origin_ok():
            return self._send(403, {"error": "origin not allowed"})
        self.send_response(204)
        o = self.headers.get("Origin")
        if o:
            self.send_header("Access-Control-Allow-Origin", o)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def do_GET(self):
        if not self._origin_ok():
            return self._send(403, {"error": "origin not allowed"})
        if self.path == "/health":
            return self._send(200, {"ok": True, "claude": bool(CLAUDE), "models": list(MODELS)})
        if self.path == "/memory":
            return self._send(200, {"long": long_items(), "short": [{"q": t["q"]} for t in load_short()]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._origin_ok():
            return self._send(403, {"error": "origin not allowed"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/ask":
                return self._send(200, handle_ask(body))
            if self.path == "/memory/add":
                return self._send(200, {"ok": add_long(body.get("text", ""))})
            self._send(404, {"error": "not found"})
        except subprocess.TimeoutExpired:
            self._send(504, {"error": f"Claude 超過 {TIMEOUT_S} 秒沒回應"})
        except Exception as e:
            self._send(500, {"error": str(e)})

    def log_message(self, fmt, *a):
        sys.stderr.write("[bridge] " + (fmt % a) + "\n")


if __name__ == "__main__":
    print(f"幕僚鳥橋接 http://127.0.0.1:{PORT}  claude={CLAUDE or '找不到'}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
