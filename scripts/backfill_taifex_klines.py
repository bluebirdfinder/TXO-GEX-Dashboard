"""
backfill_taifex_klines.py - 用「期交所官方每日期貨成交資料」補回戰情室的日內 K 線歷史（真實資料，不是推算）。

為什麼需要：富邦 futopt 的 candles 端點只給「最近一個場次」，沒有歷史端點（2026-09-27 探測 historical/* -> 404），
klines_cache.json 只能每天往後累積，所以 15 分線／1 分線的歷史只有幾個交易日。期交所每天公布「期貨每日成交行情
(逐筆成交)」檔案：https://www.taifex.com.tw/file/taifex/Dailydownload/DailydownloadCSV/Daily_YYYY_MM_DD.zip
（含夜盤＋日盤，約 1.5～2 MB 一天，官方、免費；實測可回溯約一個月）。本腳本把逐筆成交合成 K 棒：

  TXF(台指期)=TX、MXF(小台)=MTX、MTX(微台)=TMF、CDF(台積電期貨)=CDF，各取當場次成交最多的單一近月契約（排除價差單）。
  日盤棒以 08:45 為起點對齊（與富邦的棒一致：1H = 08:45、09:45…），夜盤棒對齊整點／整刻度（15:00 起）。
  只補「快取裡還沒有的棒」；富邦已經有的棒一律保留不動。1H 之後 4H 沿用既有的 aggregate_4h_from_1h。

用法：
    python scripts/backfill_taifex_klines.py --days 30                  # 回補最近 30 天（寫入 data/klines_cache.json）
    python scripts/backfill_taifex_klines.py --days 30 --dry-run        # 只下載＋報告，不寫檔
    python scripts/backfill_taifex_klines.py --compare 2026-10-06       # 拿官方逐筆合成的棒，對照快取內富邦的同一天（驗證用）
成交量欄位是「成交數量(B+S)」＝買賣雙方各算一次；2026-10-07 以 --compare 對照富邦 10/6 的 76 根 15 分棒，OHLC 100% 一致、量恰為 2.0 倍，所以除以 2（VOL_DIVISOR）。
"""
import argparse
import datetime
import io
import json
import os
import sys
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_market_klines import aggregate_4h_from_1h  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "klines_cache.json")
URL = "https://www.taifex.com.tw/file/taifex/Dailydownload/DailydownloadCSV/Daily_{y}_{m:02d}_{d:02d}.zip"
TZ = datetime.timezone(datetime.timedelta(hours=8))
PRODUCTS = {"TXF": "TX", "MXF": "MTX", "MTX": "TMF", "CDF": "CDF"}   # 戰情室代號 -> 期交所商品代號
TFS_MIN = {"1M": 1, "5M": 5, "15M": 15, "30M": 30, "1H": 60}
CAP = {"1M": 8000, "5M": 8000, "15M": 8000, "30M": 6000, "1H": 4000, "4H": 3000}   # 與 fetch_fubon_futures_klines.py 相同
VOL_DIVISOR = 2   # 官方「成交數量(B+S)」是買賣雙方各算一次，實測恰為富邦成交量的 2.0 倍


def fetch_day(d):
    """下載並解析某一天的檔案。回傳 {商品代號: [(epoch, price, qty, contract)]}；沒有檔案（假日）回傳 None。"""
    url = URL.format(y=d.year, m=d.month, d=d.day)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
    except Exception as e:  # noqa: BLE001
        print(f"  {d}: 無檔案（{type(e).__name__}）")
        return None
    if raw[:2] != b"PK":          # 假日／尚未公布時伺服器回的是網頁而不是 zip
        print(f"  {d}: 無檔案（非 zip，應為休市日或尚未公布）")
        return None
    z = zipfile.ZipFile(io.BytesIO(raw))
    text = z.read(z.namelist()[0]).decode("big5", errors="replace").splitlines()
    out = {p: [] for p in PRODUCTS.values()}
    for line in text[1:]:
        c = line.split(",")
        if len(c) < 7:
            continue
        prod = c[1].strip()
        if prod not in out:
            continue
        contract = c[2].strip()
        if "/" in contract:          # 跨月價差單，不是單一契約成交
            continue
        try:
            dt = datetime.datetime.strptime(c[0].strip() + c[3].strip().zfill(6), "%Y%m%d%H%M%S").replace(tzinfo=TZ)
            out[prod].append((int(dt.timestamp()), float(c[4]), int(c[5]), contract))
        except ValueError:
            continue
    return out


def session_of(ts):
    """回傳 (場次, 該場次的棒起點基準秒)。日盤 08:45–13:45 以 08:45 起算；其餘（夜盤）以整點對齊。"""
    dt = datetime.datetime.fromtimestamp(ts, TZ)
    mins = dt.hour * 60 + dt.minute
    if 8 * 60 + 45 <= mins <= 13 * 60 + 45:
        base = dt.replace(hour=8, minute=45, second=0, microsecond=0)
        return "day", int(base.timestamp())
    return "night", 0


def build_bars(ticks, tf_min):
    """ticks: [(epoch, price, qty, contract)] -> 該週期 K 棒 dict(time -> bar)。先挑各場次成交最多的契約。"""
    # 每個場次（日／夜，以日曆日＋場次區分）挑 tick 最多的單一契約
    by_sess = {}
    for t in ticks:
        s, _ = session_of(t[0])
        key = (datetime.datetime.fromtimestamp(t[0] - (0 if s == "day" else 5 * 3600), TZ).date(), s)   # 夜盤跨午夜：減 5 小時歸到開盤那天
        by_sess.setdefault(key, []).append(t)
    bars = {}
    step = tf_min * 60
    for key, ts in by_sess.items():
        cnt = {}
        for t in ts:
            cnt[t[3]] = cnt.get(t[3], 0) + 1
        front = max(cnt, key=cnt.get)
        for t in sorted((x for x in ts if x[3] == front), key=lambda x: x[0]):
            s, base = session_of(t[0])
            start = base + ((t[0] - base) // step) * step if s == "day" else (t[0] // step) * step
            b = bars.get(start)
            if b is None:
                bars[start] = {"time": start, "open": t[1], "high": t[1], "low": t[1], "close": t[1], "volume": t[2]}
            else:
                b["high"] = max(b["high"], t[1]); b["low"] = min(b["low"], t[1]); b["close"] = t[1]
                b["volume"] += t[2]
    for b in bars.values():
        b["volume"] //= VOL_DIVISOR          # 加總後才除，避免逐筆整數除法流失
    return bars


def compare(date_str):
    d = datetime.date.fromisoformat(date_str)
    day = fetch_day(d)
    if not day:
        return
    cache = json.load(open(CACHE, encoding="utf-8"))
    for sym, prod in PRODUCTS.items():
        for tf, m in (("15M", 15), ("1H", 60)):
            mine = build_bars(day[prod], m)
            theirs = {b["time"]: b for b in cache["assets"].get(sym, {}).get("timeframes", {}).get(tf, [])}
            common = sorted(set(mine) & set(theirs))
            if not common:
                print(f"{sym}/{prod} {tf}: 沒有共同的棒"); continue
            ohlc_ok = sum(1 for t in common if all(abs(mine[t][k] - theirs[t][k]) < 1e-9 for k in ("open", "high", "low", "close")))
            ratios = [mine[t]["volume"] / theirs[t]["volume"] for t in common if theirs[t]["volume"]]
            ratios.sort()
            med = ratios[len(ratios) // 2] if ratios else None
            print(f"{sym}/{prod} {tf}: 共同 {len(common)} 棒，OHLC 完全一致 {ohlc_ok}；量比(官方/富邦) 中位數 {med and round(med, 3)}，範圍 {ratios and (round(ratios[0], 2), round(ratios[-1], 2))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--compare")
    a = ap.parse_args()
    if a.compare:
        compare(a.compare)
        return
    cache = json.load(open(CACHE, encoding="utf-8"))
    today = datetime.datetime.now(TZ).date()
    added = {s: {k: 0 for k in TFS_MIN} for s in PRODUCTS}
    for i in range(a.days, -1, -1):
        d = today - datetime.timedelta(days=i)
        if d.weekday() >= 5:
            continue
        day = fetch_day(d)
        if not day:
            continue
        for sym, prod in PRODUCTS.items():
            tfs = cache["assets"].setdefault(sym, {"symbol": sym, "timeframes": {}}).setdefault("timeframes", {})
            for tf, m in TFS_MIN.items():
                new = build_bars(day[prod], m)
                have = {b["time"] for b in tfs.get(tf, [])}
                fresh = [b for t, b in new.items() if t not in have]
                if fresh:
                    tfs[tf] = sorted(tfs.get(tf, []) + fresh, key=lambda b: b["time"])[-CAP[tf]:]
                    added[sym][tf] += len(fresh)
        print(f"  {d}: 完成")
    for sym in PRODUCTS:
        tfs = cache["assets"][sym]["timeframes"]
        if tfs.get("1H"):
            by = {b["time"]: b for b in tfs.get("4H", [])}
            by.update({b["time"]: b for b in aggregate_4h_from_1h(tfs["1H"]) if b["time"] not in by})
            tfs["4H"] = [by[t] for t in sorted(by)][-CAP["4H"]:]
    print("新增棒數：", json.dumps(added, ensure_ascii=False))
    if a.dry_run:
        print("dry-run：不寫檔")
        return
    cache["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print("saved", CACHE)


if __name__ == "__main__":
    main()
