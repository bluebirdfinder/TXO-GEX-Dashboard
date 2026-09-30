"""
build_stock_daily_shards.py - 把全市場個股日 K 切成 64 個小分片：data/stock_daily/00.json ... 63.json

為什麼要切：
  - 完整的 data/screener_ohlcv_cache.json 約 15MB。Cloudflare Worker 免費版每次請求 CPU 只有 10ms，
    解析 15MB 會超時；手機網頁也不該為了看一檔股票下載 2.4MB。
  - 切成 64 片後每片約 100KB：Worker、手機網頁都只抓「這檔股票所在的那一片」。

分片規則（前端 room.js、Worker、本腳本三邊必須一致）：
  djb2 雜湊：h = 5381; for ch in code: h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF ; shard = h % 64
  檔名兩位數補零，例如 '2330' -> data/stock_daily/NN.json

每片格式（緊湊陣列，省體積）：
  {"latest": "20260930", "built": "2026-09-30", "n": 22, "bars": {"2330": [[date, open, high, low, close, volume_lots], ...], ...}}
  date 為 YYYYMMDD 整數；volume 單位為「張」（與 screener_ohlcv_cache.json 相同）；沒有日期的舊格式 K 棒一律略過，
  寧可缺也不猜日期。

用法：
    python scripts/build_stock_daily_shards.py            # 由 data/screener_ohlcv_cache.json 產生
build_screener_cache.py 每次重建全市場資料後也會自動呼叫本腳本。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "screener_ohlcv_cache.json")
OUT_DIR = os.path.join(ROOT, "data", "stock_daily")
SHARDS = 64


def shard_of(code):
    h = 5381
    for ch in str(code):
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    return h % SHARDS


def build(src=SRC, out_dir=OUT_DIR):
    with open(src, encoding="utf-8") as f:
        cache = json.load(f)
    data = cache.get("data", {})
    all_bars = dict(data.get("_TWSE_BULK", {}))
    for k, v in data.items():
        if not k.startswith("_") and isinstance(v, list) and v:
            all_bars[k] = v
    latest = data.get("_TWSE_BULK_LATEST") or ""
    built = cache.get("_date", "")

    shards = [dict() for _ in range(SHARDS)]
    kept = skipped = 0
    for code, bars in all_bars.items():
        rows = []
        for b in bars:
            d = b.get("date")
            if not d or len(str(d)) != 8:
                skipped += 1
                continue
            rows.append([int(d), b["open"], b["high"], b["low"], b["close"], b.get("volume", 0)])
        if rows:
            shards[shard_of(code)][code] = rows
            kept += 1

    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for i, bars in enumerate(shards):
        payload = {"latest": latest, "built": built, "n": len(bars), "bars": bars}
        path = os.path.join(out_dir, f"{i:02d}.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        total += os.path.getsize(path)
    biggest = max(os.path.getsize(os.path.join(out_dir, f"{i:02d}.json")) for i in range(SHARDS))
    print(f"[OK] stock_daily shards: {kept} stocks in {SHARDS} files, total {total / 1e6:.1f}MB, largest {biggest / 1e3:.0f}KB, "
          f"{skipped} undated bars skipped")
    return kept


if __name__ == "__main__":
    if not os.path.exists(SRC):
        sys.exit(f"missing {SRC}")
    build()
