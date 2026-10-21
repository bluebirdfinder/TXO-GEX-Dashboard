r"""到期結算（只用期交所官方「最後結算價」，不自己猜）。
資料來源：https://www.taifex.com.tw/cht/5/optIndxFSP（指數類選擇權最後結算價；契約月份代碼與本系統相同，
例：202610F3、202610W2、月選 202609；臺指選擇權欄＝TXO）。官方在結算日收盤後才會公布，沒公布就不結算、下一輪再試。
用法：python settlement.py T0            檢查帳戶有沒有已到期且官方已公布結算價的到期日，有就結算
      （monitor.py 會自動每 5 分鐘呼叫；這裡也能手動執行）"""
import re
import sys
import urllib.request
from datetime import date, datetime

import sources
from book import Desk, load_config
from run_slot import PRIVATE

URL = "https://www.taifex.com.tw/cht/5/optIndxFSP"
_ROW = re.compile(r"<TR[^>]*>(.*?)</TR>", re.I | re.S)
_TD = re.compile(r"<TD[^>]*>\s*([^<]*?)\s*</TD>", re.I | re.S)
_CODE = re.compile(r"^\d{6}(?:[WF][1-5])?$")


def parse_fsp(html):
    """從官方頁面 HTML 取出 {到期代碼: (最後結算日 date, 臺指選擇權最後結算價 float)}；格式不認得的列略過。"""
    out = {}
    for row in _ROW.findall(html):
        tds = _TD.findall(row)
        if len(tds) < 3 or not _CODE.match(tds[1]):
            continue
        try:
            d = datetime.strptime(tds[0], "%Y/%m/%d").date()
            px = float(tds[2].replace(",", ""))
        except ValueError:
            continue                       # 例如結算價欄是「-」
        out[tds[1]] = (d, px)
    return out


def fetch_fsp(url=URL, timeout=20):
    """抓官方頁面並解析；失敗回 {}（不結算，下一輪再試）。頁面是 Big5 編碼。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=timeout).read()
        return parse_fsp(raw.decode("cp950", "replace"))
    except Exception:
        return {}


def active_codes(desk):
    return sorted(desk.state.active_expiries())


def settle_due(desk, today, fsp):
    """帳戶裡有持倉或掛單的到期日：官方已公布「最後結算日 ≤ 今天」就結算。
    官方日期為準（遇颱風假/國定假日，實際結算日會和系統算的第 3 個週三/週五不同，2026-10-20 實測 108 筆裡有 10 筆不同）；
    若官方日期比系統算的到期日還早（desk.settle 不允許），跳過並回報，請人工確認。回傳事件列表。"""
    out = []
    for code in active_codes(desk):
        got = fsp.get(code)
        if got is None or got[0] > today:
            continue
        d, px = got
        try:
            out += desk.settle(code, px, today)
        except ValueError as e:
            out.append({"type": "SKIP", "expiry": code, "reason": f"官方最後結算日 {d}，但 {e}；不結算，請人工確認"})
    return out


def main(argv):
    account = argv[1]
    cfg = load_config()
    desk = Desk(PRIVATE / account / "ledger.jsonl", account, cfg)
    today = datetime.now(sources.TW).date()
    due = active_codes(desk)
    if not due:
        print("沒有持倉或掛單")
        return
    fsp = fetch_fsp()
    print("持有的到期日：", due, "官方已公布：", {c: fsp[c] for c in due if c in fsp} or "尚未公布")
    for e in settle_due(desk, today, fsp):
        print(e["type"], e.get("gid") or e.get("expiry"), e.get("cash_delta", e.get("reason", "")))


if __name__ == "__main__":
    main(sys.argv)
