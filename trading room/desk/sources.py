"""資料來源轉接（只讀）：把真實檔案/服務的資料整理成快照需要的格式；讀不到就回 None，不補假值。
重放時一律用「決策時間以前」的資料（擋未來資料）。"""
import csv
import gzip
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TW = timezone(timedelta(hours=8))


def _t(s):
    t = datetime.fromisoformat(s.strip().replace(" ", "T"))
    return t if t.tzinfo else t.replace(tzinfo=TW)


class GexArchive:
    """資料夾內 YYYYMMDD_HHMM.json(.gz) 檔案（Lumi option_data/gex 格式）。at(now) 回傳 ≤ now 的最新一份，沒有就 None。"""

    def __init__(self, folder):
        self.items = []
        for p in sorted(Path(folder).glob("*.json*")):
            stem = p.name.split(".")[0]
            try:
                self.items.append((datetime.strptime(stem, "%Y%m%d_%H%M").replace(tzinfo=TW), p))
            except ValueError:
                continue

    def at(self, now):
        best = None
        for t, p in self.items:
            if t <= now:
                best = p
        if best is None:
            return None
        op = gzip.open if best.suffix == ".gz" else open
        with op(best, "rt", encoding="utf-8") as f:
            return json.load(f)


def gex_from_file(path, now=None):
    """單一 gex_data.json（TXO 專案現行檔）。若指定 now 且檔案更新時間晚於 now（重放用）→ None。"""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if now is not None and d.get("last_updated_time") and _t(d["last_updated_time"]) > now:
        return None
    return d


def load_kbars(csv_path, now, limit=300):
    """台指期 1 分 K（Lumi kbar_data/TX_1m.csv 格式）。只回 ts ≤ now 的最後 limit 根。"""
    out = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if _t(r["ts"]) <= now:
                out.append({"ts": r["ts"], "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]),
                            "close": float(r["close"]), "volume": int(float(r["volume"] or 0))})
    return out[-limit:]


def spot_from_kbars(bars):
    """重放用：沒有歷史即時報價時，以最後一根 1 分 K 的收盤當現價，時間=該根收盤時刻（標註來源，不是即時報價）。"""
    if not bars:
        return None
    t = _t(bars[-1]["ts"]) + timedelta(seconds=59)
    return {"price": bars[-1]["close"], "ts": t.isoformat(), "provider": "replay:kbar_close"}


def live_spot(url="http://127.0.0.1:8000/api/live_tick", timeout=5):
    """即時現價（報價服務 8000，富邦或官方備援）。ts 用「現在減資料年齡」；讀不到就 None。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        tx = d.get("txf") or {}
        if tx.get("price") is None or tx.get("ts") is None:
            return None
        return {"price": tx["price"], "ts": datetime.fromtimestamp(tx["ts"], TW).isoformat(), "provider": tx.get("provider")}
    except Exception:
        return None


def iter_recorded_chain(path):
    """報價紀錄器的 .jsonl.gz：逐份快照回傳 (aware datetime, rows)。"""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                o = json.loads(line)
                yield _t(o["ts"]), o["q"]


GEX_URLS = ("https://raw.githubusercontent.com/bluebirdfinder/TXO-GEX-Dashboard/main/data/gex_data.json",
            "http://127.0.0.1:8000/data/gex_data.json")
KLINES_URL = "http://127.0.0.1:8000/data/klines_cache.json"


def live_gex(urls=GEX_URLS, timeout=15):
    """依序嘗試各來源，回傳「更新時間最新」的一份；全失敗回 None。2026-10-20 實測：GitHub 主線版每天由排程更新，
    本機 8000 靜態檔可能落後（共用資料夾沒 pull），所以不能只看本機。新鮮度由 snapshot.check 判斷。"""
    best = None
    for u in urls:
        try:
            with urllib.request.urlopen(u, timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
        if best is None or str(d.get("last_updated_time")) > str(best.get("last_updated_time")):
            best = d
    return best


def live_kbars(now, url=KLINES_URL, symbol="TXF", limit=300, timeout=15):
    """報價服務 8000 的 klines_cache.json（富邦累積的台指期 1 分 K，time=分鐘起點 epoch 秒）。只回 ≤ now 的。
    2026-10-20 實測：這份檔案會落後（只到日盤 13:44，沒有夜盤），落後就會被 snapshot.check 判「1 分 K 太舊」而不下決策。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        arr = d["assets"][symbol]["timeframes"]["1M"]
    except Exception:
        return []
    out = []
    for c in arr[-limit - 400:]:
        t = datetime.fromtimestamp(c["time"], TW)
        if t <= now:
            out.append({"ts": t.strftime("%Y-%m-%d %H:%M"), "open": c["open"], "high": c["high"], "low": c["low"],
                        "close": c["close"], "volume": c.get("volume", 0)})
    return out[-limit:]


def live_chain(market_type, timeout=20):
    """期交所 MIS 全部 TXO 報價列（只留有買價或賣價的）。失敗回 []。與報價紀錄器同一個端點、同一種格式。"""
    payload = {"MarketType": market_type, "SymbolType": "O", "KindID": "1", "CID": "TXO",
               "ExpireMonth": "", "RowSize": "全部", "PageNo": "", "SortColumn": "", "AscDesc": "A"}
    keep = ("SymbolID", "CBestBidPrice", "CBestBidSize", "CBestAskPrice", "CBestAskSize", "CTime", "CDate")
    try:
        req = urllib.request.Request("https://mis.taifex.com.tw/futures/api/getQuoteList",
                                     data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json;charset=UTF-8", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            q = json.loads(r.read().decode("utf-8"))["RtData"]["QuoteList"]
    except Exception:
        return []
    return [{k: x.get(k) for k in keep} for x in q if x.get("SymbolID", "").startswith("TX")
            and (float(x.get("CBestBidPrice") or 0) > 0 or float(x.get("CBestAskPrice") or 0) > 0)]


MIS_CHART_URL = "https://mis.taifex.com.tw/futures/api/getChartData1M"


def front_month_symbol(now, suffix):
    """近月台指期 MIS 代號，例 TXFJ6-F（日盤）/ TXFJ6-M（夜盤）。月代碼 A-L=1~12 月，年取末碼。
    近月＝結算日（第 3 個週三）13:30 還沒到的第一個月；結算日 13:30 之後換下一個月。"""
    from datetime import time as dtime
    from expiry import expiry_date
    y, m = now.year, now.month
    for _ in range(3):
        if now.replace(tzinfo=None) < datetime.combine(expiry_date(f"{y}{m:02d}"), dtime(13, 30)):
            break
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"TXF{chr(ord('A') + m - 1)}{y % 10}-{suffix}"


def _assign_dates(ticks, now):
    """MIS 的 Ticks 只有 HHMMSS 沒有日期：由最新一根往回推，時間比下一根大就代表跨了一天。"""
    out, day, nxt = [], now.date(), None
    last_t = ticks[-1][0]
    if (last_t[:2] + ":" + last_t[2:4]) > (now + timedelta(minutes=1)).strftime("%H:%M"):
        day -= timedelta(days=1)             # 最新一根的時間比現在(+1 分鐘容許形成中的那根)還晚 → 屬於前一天
    # 註：MIS 標籤是「該根 1 分 K 的結束時刻」（日盤第一根 08:45-08:46 標 084600、共 300 根到 134500）
    for tk in reversed(ticks):
        if nxt is not None and tk[0] > nxt:
            day -= timedelta(days=1)
        nxt = tk[0]
        out.append((day, tk))
    return list(reversed(out))


def live_kbars_mis(now, limit=300, fetch=None, timeout=15):
    """期交所 MIS 官方 1 分 K（getChartData1M）：日盤用 -F、夜盤用 -M；盤中即時。回傳格式同 live_kbars。
    2026-10-20 實測：日盤 300 根、夜盤整盤 600+ 根，OHLCV 與富邦累積的 1 分 K 同一標籤逐項相同。
    MIS 標籤是該分鐘的『結束時刻』（2026-10-20 實測：MIS 的 134400 ＝ 富邦的 13:43 那根），這裡改成『開始時刻』輸出；還沒收完的那根丟掉。失敗回 []。"""
    m = now.hour * 60 + now.minute
    suffix = "F" if 8 * 60 + 45 <= m < 20 * 60 and m < 15 * 60 else "M"
    sym = front_month_symbol(now, suffix)
    try:
        if fetch:
            d = fetch(sym)
        else:
            req = urllib.request.Request(MIS_CHART_URL, data=json.dumps({"SymbolID": sym}).encode("utf-8"),
                                         headers={"Content-Type": "application/json;charset=UTF-8", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8"))["RtData"]
        ticks = d.get("Ticks") or []
    except Exception:
        return []
    if not ticks:
        return []
    out = []
    for day, tk in _assign_dates(ticks, now):
        if int(tk[0][2:4]) >= 60:
            continue    # 夜盤收盤前有一根標籤寫成 04:60 的特殊收盤根（2026-10-21 實測）：富邦/TradingView 都沒有這根，略過才與它們一致
        end = datetime.strptime(f"{day:%Y-%m-%d} {tk[0][:4]}", "%Y-%m-%d %H%M").replace(tzinfo=TW)
        if end <= now:                                  # 結束時刻還沒到的是形成中那根，丟掉
            t = end - timedelta(minutes=1)              # 輸出用「開始時刻」標籤，與富邦/TradingView 一致
            out.append({"ts": t.strftime("%Y-%m-%d %H:%M"), "open": float(tk[1]), "high": float(tk[2]), "low": float(tk[3]),
                        "close": float(tk[4]), "volume": int(float(tk[5]))})
    return out[-limit:]


def live_cache_tf(tf, url=KLINES_URL, symbol="TXF", limit=800, timeout=15):
    """富邦累積的 15M/30M 歷史（8000 的 klines_cache.json，time=開始時刻 epoch 秒）。給九轉計數當歷史用；失敗回 []。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            arr = json.loads(r.read().decode("utf-8"))["assets"][symbol]["timeframes"][tf]
    except Exception:
        return []
    return [{"ts": datetime.fromtimestamp(c["time"], TW).strftime("%Y-%m-%d %H:%M"), "open": c["open"], "high": c["high"],
             "low": c["low"], "close": c["close"], "volume": c.get("volume", 0)} for c in arr[-limit:]]
