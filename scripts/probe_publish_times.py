"""
量測期交所各項盤後資料「實際公布時間」的探針（只讀、每 60 秒查一次、不寫公開倉庫）。

用途：MARKET_DATA_SCHEDULE.md 寫的公布時間（例如大額交易人 17:00～18:30）是否真的如此，
以及該把排程第一梯次排在幾點。每個項目第一次查到「當日有資料」的時間，寫進
~/.txo_publish_probe/<查詢日>_<session>.json。

用法（時間都是台北時間）：
  python scripts/probe_publish_times.py --session day   # 日盤後：從 13:30 查到所有項目都出現或 19:30
  python scripts/probe_publish_times.py --session night # 夜盤後：從 04:30 查到所有項目都出現或 08:00
  python scripts/probe_publish_times.py --date 2026/10/06 --once   # 只查一次（測試用）

判斷「有資料」：頁面不含「查無資料」。選擇權三大法人（callsAndPutsDate）以頁面出現查詢日期為準。
"""
import argparse
import datetime as dt
import json
import os
import ssl
import time
import urllib.parse
import urllib.request

TPE = dt.timezone(dt.timedelta(hours=8))
H = {"User-Agent": "Mozilla/5.0"}
CTX = ssl.create_default_context()
BASE = "https://www.taifex.com.tw/cht/3/"


def _get(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=H)
    return urllib.request.urlopen(req, timeout=25, context=CTX).read().decode("utf-8", "ignore")


def _has_data(html, qdate, need_date=False):
    if need_date:
        return qdate in html
    return "查無資料" not in html and qdate in html


CHECKS = {
    "day": {   # 日盤收盤（13:45）之後的項目
        "三大法人期貨(日盤)": lambda d: _has_data(_get(f"{BASE}futContractsDate?queryDate={d}"), d),
        "三大法人選擇權(日盤)": lambda d: _has_data(_get(BASE + "callsAndPutsDate", {
            "queryType": "1", "goDay": "", "doQuery": "1", "dateaddcnt": "", "queryDate": d, "commodityId": "TXO"}), d, True),
        "大額交易人期貨": lambda d: _has_data(_get(BASE + "largeTraderFutQry", {"queryDate": d, "contractId": "TX"}), d),
        "大額交易人選擇權": lambda d: _has_data(_get(BASE + "largeTraderOptQry", {"queryDate": d, "contractId": "TXO"}), d),
    },
    "night": {  # 夜盤收盤（05:00）之後的項目
        "三大法人期貨(夜盤)": lambda d: _has_data(_get(f"{BASE}futContractsDateAh?queryDate={d}&commodityId="), d),
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", choices=["day", "night"], default="day")
    ap.add_argument("--date", help="查詢日 YYYY/MM/DD；預設：day＝今天，night＝今天（夜盤後那天的交易日）")
    ap.add_argument("--once", action="store_true", help="只查一次就結束（測試）")
    ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args()

    now = dt.datetime.now(TPE)
    qdate = a.date or now.strftime("%Y/%m/%d")
    checks = CHECKS[a.session]
    end_h, end_m = (19, 30) if a.session == "day" else (8, 0)
    deadline = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

    out_dir = os.path.join(os.path.expanduser("~"), ".txo_publish_probe")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{qdate.replace('/', '')}_{a.session}.json")
    result = {"query_date": qdate, "session": a.session, "started": now.isoformat(timespec="seconds"),
              "first_seen": {}, "errors": 0}

    while True:
        t = dt.datetime.now(TPE)
        for name, fn in checks.items():
            if name in result["first_seen"]:
                continue
            try:
                if fn(qdate):
                    result["first_seen"][name] = t.strftime("%H:%M:%S")
                    print(f"[{t:%H:%M:%S}] {name} 已出現", flush=True)
            except Exception as e:
                result["errors"] += 1
                print(f"[{t:%H:%M:%S}] {name} 查詢失敗：{e}", flush=True)
        result["last_check"] = t.strftime("%H:%M:%S")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if a.once or len(result["first_seen"]) == len(checks) or t >= deadline:
            break
        time.sleep(a.interval)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
