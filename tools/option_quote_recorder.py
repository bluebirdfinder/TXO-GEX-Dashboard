"""TAIFEX MIS option-chain quote recorder (stage-0 experiment, simulation research only).

Every N seconds, snapshot the whole TXO chain (monthly + weekly) from getQuoteList
(SymbolType=O) and append compact rows (only strikes that have a bid or ask) to <outdir>/YYYYMMDD_day|night.jsonl.gz
(one gzip member per snapshot, so appending is safe and `gzip -dc` / Python gzip read it as one stream).
Only real MIS data is stored; nothing is filled in. Request health is logged to
<outdir>/health_YYYYMMDD.csv so rate-limit / blocking can be judged afterwards.

Usage: python -I option_quote_recorder.py [interval_sec=30] [outdir]
"""
import csv
import gzip
import json
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TW = timezone(timedelta(hours=8))
URL = "https://mis.taifex.com.tw/futures/api/getQuoteList"
CTX = ssl.create_default_context()
KEEP = ("SymbolID", "CBestBidPrice", "CBestBidSize", "CBestAskPrice", "CBestAskSize",
        "CBidPrice1", "CAskPrice1", "CLastPrice", "CTotalVolume", "CTime", "CDate",
        "SettlementPrice", "OpenInterest")


def market_type(now):
    """0 = day session (08:45-13:45), 1 = night (15:00-05:00); None = closed."""
    m = now.hour * 60 + now.minute
    if 8 * 60 + 45 <= m < 13 * 60 + 45:
        return "0"
    if m >= 15 * 60 or m < 5 * 60:
        return "1"
    return None


def fetch(mt):
    payload = {"MarketType": mt, "SymbolType": "O", "KindID": "1", "CID": "TXO",
               "ExpireMonth": "", "RowSize": "全部", "PageNo": "", "SortColumn": "", "AscDesc": "A"}
    req = urllib.request.Request(
        URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json;charset=UTF-8", "User-Agent": "Mozilla/5.0"})
    t0 = time.time()
    with urllib.request.urlopen(req, context=CTX, timeout=15) as r:
        body = r.read()
    return json.loads(body.decode("utf-8"))["RtData"]["QuoteList"], time.time() - t0, len(body)


def main():
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    out = Path(sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\mingi\txo-private\option_quotes")
    out.mkdir(parents=True, exist_ok=True)
    print(f"recording every {interval}s -> {out}", flush=True)
    while True:
        t_loop = time.time()
        now = datetime.now(TW)
        mt = market_type(now)
        # 夜盤跨午夜：凌晨 05:00 前仍算前一天開的那一盤，檔名用該盤的開盤日
        day = (now - timedelta(days=1) if now.hour < 5 else now).strftime("%Y%m%d")
        status, n, lat, size = "closed", 0, 0.0, 0
        if mt is not None:
            try:
                q, lat, size = fetch(mt)
                # 只存「有買價或賣價」的列（沒報價的列是空的，存了只佔空間）；每份快照獨立 gzip 區塊，可直接附加
                rows = [{k: x.get(k) for k in KEEP} for x in q
                        if x.get("SymbolID", "").startswith("TX")
                        and (float(x.get("CBestBidPrice") or 0) > 0 or float(x.get("CBestAskPrice") or 0) > 0)]
                line = json.dumps({"ts": now.isoformat(timespec="milliseconds"), "mt": mt, "q": rows}, ensure_ascii=False) + "\n"
                with gzip.open(out / f"{day}_{'day' if mt == '0' else 'night'}.jsonl.gz", "ab") as f:
                    f.write(line.encode("utf-8"))
                status, n = "ok", len(rows)
            except Exception as e:  # keep running; the error itself is the data
                status = f"err:{type(e).__name__}:{str(e)[:80]}"
        hp = out / f"health_{day}.csv"
        new = not hp.exists()
        with open(hp, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["ts", "market_type", "status", "rows", "latency_s", "bytes"])
            w.writerow([now.isoformat(timespec="seconds"), mt, status, n, round(lat, 2), size])
        time.sleep(max(1.0, interval - (time.time() - t_loop)))


if __name__ == "__main__":
    main()
