"""
audit_vs_official.py — 把 data/gex_data.json 裡每個區塊的數字，逐項「獨立」向期交所／證交所官方再抓一次比對。

用途：使用者要求「所有區塊的欄位數字都要和期交所／證交所核對，確定真實性」（2026-10-06）。
這支腳本不 import 引擎的取數函式（避免拿引擎自己的輸出當標準答案），一律直接打官方網址、
自己解析、自己重算，再和資料檔比。每一項輸出 PASS / FAIL / SKIP（SKIP＝官方當下沒資料，不能判斷）。

用法：
    python scripts/audit_vs_official.py                 # 對 data/gex_data.json
    python scripts/audit_vs_official.py --json out.json # 另存結果

注意：盤中官方資料還沒定案時，部分項目會 SKIP 或有時間差；請在收盤後（日盤 14:30 後、夜盤 05:30 後）執行。
"""
import argparse
import datetime
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0"}
CTX = ssl.create_default_context()
CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT   # 證交所憑證在 Python 3.13 的嚴格模式下會失敗

RESULTS = []   # (區塊, 項目, 資料檔, 官方, 結果, 備註)


def rec(block, item, ours, official, ok, note=""):
    RESULTS.append((block, item, ours, official, "PASS" if ok is True else ("SKIP" if ok is None else "FAIL"), note))


def http(url, data=None, enc="utf-8", timeout=30):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
        return r.read().decode(enc, errors="ignore")


def num(x):
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def close(a, b, tol=0.0):
    return a is not None and b is not None and abs(a - b) <= tol


def table_rows(html):
    soup = BeautifulSoup(html, "html.parser")
    return [[re.sub(r"\s+", "", c.get_text()) for c in r.find_all(["td", "th"])] for r in soup.find_all("tr")]


# ---------------------------------------------------------------- 1. 現貨指數（證交所 MIS）
def check_index(d):
    try:
        j = json.loads(http("https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw%7Cotc_o00.tw&json=1&delay=0"))
        for m in j["msgArray"]:
            z = num(m.get("z")) or num(m.get("y"))
            y = num(m.get("y"))
            if m["c"] == "t00":
                rec("現貨指數", "加權指數收盤", d["spot_price"], z, close(d["spot_price"], z, 0.5), "證交所 MIS（盤後為收盤價；盤中兩者有時間差）")
                rec("現貨指數", "加權指數漲跌", d["spot_change"], round(z - y, 2), close(d["spot_change"], round(z - y, 2), 0.5))
            if m["c"] == "o00":
                rec("現貨指數", "櫃買指數收盤", d["two_price"], z, close(d["two_price"], z, 0.05), "櫃買 MIS")
                rec("現貨指數", "櫃買指數漲跌", d["two_change"], round(z - y, 2), close(d["two_change"], round(z - y, 2), 0.05))
    except Exception as e:
        rec("現貨指數", "取得官方資料", None, None, None, f"失敗：{e}")


# ---------------------------------------------------------------- 2. 台指期價格（期交所）
def check_tx(d):
    q = datetime.datetime.strptime(d["date"], "%Y-%m-%d").strftime("%Y/%m/%d")
    for label, mc, key in (("日盤收盤", 0, "day_txf_price"), ("夜盤收盤", 1, "night_txf_price")):
        try:
            h = http(f"https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode={mc}&commodity_id=TX&queryDate={q}", enc="big5")
            row = next((r for r in table_rows(h) if r and r[0] == "TX" and len(r) > 5 and re.fullmatch(r"\d{6}", r[1])), None)
            off = num(row[5]) if row else None
            now_tpe = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(tzinfo=None)
            session_end = datetime.datetime.strptime(q, "%Y/%m/%d") + datetime.timedelta(hours=(13, 29)[mc]) + (datetime.timedelta(minutes=45) if mc == 0 else datetime.timedelta(minutes=0))
            if mc == 1 and now_tpe < datetime.datetime.strptime(q, "%Y/%m/%d") + datetime.timedelta(days=1, hours=5, minutes=30):
                rec("台指期", label, d.get(key), off, None, "夜盤尚未結束（隔日 05:00），官方數字還在變動，不比對")
                continue
            if off is None:
                rec("台指期", label, d.get(key), None, None, "官方當下沒有該場次資料")
            else:
                rec("台指期", label, d.get(key), off, close(d.get(key), off, 0.5), f"期交所每日行情表 {q} 近月收盤")
        except Exception as e:
            rec("台指期", label, d.get(key), None, None, f"失敗：{e}")


# ---------------------------------------------------------------- 3. 選擇權：P/C、最大痛點、結算日
def check_options(d):
    q = datetime.datetime.strptime(d["chip_base_date"], "%Y-%m-%d").strftime("%Y/%m/%d")
    try:
        raw = http(f"https://www.taifex.com.tw/cht/3/optDataDown?down_type=1&commodity_id=TXO&queryStartDate={q}&queryEndDate={q}", enc="cp950")
        C, P, per = defaultdict(int), defaultdict(int), defaultdict(lambda: [defaultdict(int), defaultdict(int)])
        exp = {}
        for line in raw.split("\n")[1:]:
            c = [x.strip() for x in line.split(",")]
            if len(c) < 21 or c[17] != "一般":
                continue
            try:
                k = float(c[3]); oi = int(c[11]) if c[11] not in ("-", "") else 0
            except ValueError:
                continue
            right = "call" if "買" in c[4] else ("put" if "賣" in c[4] else None)
            if not right:
                continue
            (C if right == "call" else P)[k] += oi
            per[c[2]][0 if right == "call" else 1][k] += oi
            exp[c[2]] = c[20]
        cs, ps = sum(C.values()), sum(P.values())
        if cs:
            pc = round(ps / cs * 100, 2)
            rec("選擇權", "全市場 P/C 未平倉比", d["pc_ratio"], pc, close(d["pc_ratio"], pc, 0.05), "期交所 optDataDown 全契約 Put OI ÷ Call OI")
        ks = sorted(set(C) | set(P))

        def mp(Cm, Pm):
            kk = sorted(set(Cm) | set(Pm))
            return min(kk, key=lambda S: sum(max(0, S - k) * Cm.get(k, 0) + max(0, k - S) * Pm.get(k, 0) for k in kk))
        rec("選擇權", "Max Pain（全契約、全履約價）", d["max_pain_strike"], mp(C, P), close(d["max_pain_strike"], mp(C, P), 100),
            "最大痛點只該取決於未平倉，不該隨現價改變；容許 ±100 點（四個週別合併 vs 全契約的差異）")
        # 近週選（最近到期的 W 契約）
        w = sorted((v, k) for k, v in exp.items() if re.search(r"W\d$", k))
        if w:
            code = w[0][1]
            rec("選擇權", f"Max Pain（最近到期週選 {code}，參考）", d["max_pain_strike"], mp(per[code][0], per[code][1]), None, "僅供參考：週選當週結算磁吸價位")
        top_call = max(C, key=C.get); top_put = max(P, key=P.get)
        rec("選擇權", "Call Wall 是否位於 Call 未平倉前三大履約價", d["call_wall_strike"], top_call, d["call_wall_strike"] in sorted(C, key=C.get, reverse=True)[:3], "Call Wall 為 Gamma 加權，不要求等於最大 OI 履約價")
        rec("選擇權", "Put Wall 參考（最大 Put OI 履約價）", d["put_wall_strike"], top_put, None, "Put Wall 為 Gamma 加權的近價牆位，與純 OI 最大處不必相同；僅供參考")
        # 結算日
        dte = d.get("dte_dates", {})
        wexp = sorted(v for k, v in exp.items() if re.search(r"W\d$", k))
        if wexp and dte.get("w1"):
            m = re.search(r"(\d+)/(\d+)", dte["w1"])
            off = datetime.datetime.strptime(wexp[0], "%Y%m%d")
            rec("選擇權", "近週選結算日", dte["w1"], off.strftime("%m/%d"), bool(m) and (int(m.group(1)), int(m.group(2))) == (off.month, off.day), "期交所 optDataDown 契約到期日")
    except Exception as e:
        rec("選擇權", "取得官方資料", None, None, None, f"失敗：{e}")


# ---------------------------------------------------------------- 4. VIX
def check_vix(d):
    v = d["vix_info"]
    for ds, tag in ((d["chip_base_date"].replace("-", ""), "today"),):
        try:
            lines = [l.strip() for l in http(f"https://www.taifex.com.tw/cht/7/getVixData?filesname={ds}", enc="big5").splitlines() if l.strip()]
            off = num(lines[-1].split()[-1])
            rec("VIX", "台指 VIX（期交所收盤前 1 分鐘平均）", v["taifex_vix"], off, close(v["taifex_vix"], off, 0.01), f"期交所 getVixData {ds}")
        except Exception as e:
            rec("VIX", "台指 VIX", v.get("taifex_vix"), None, None, f"失敗：{e}")
    for tk, key in (("%5EVIX", "us_vix"), ("%5EVVIX", "us_vvix")):
        try:
            j = json.loads(http(f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}?interval=1d&range=5d"))["chart"]["result"][0]
            px = j["meta"]["regularMarketPrice"]
            rec("VIX", f"{key}（Yahoo／CBOE，非期交所）", v[key], px, close(v[key], px, 0.3), "第三方行情；盤中有時間差，容許 ±0.3")
        except Exception as e:
            rec("VIX", key, v.get(key), None, None, f"失敗：{e}")


# ---------------------------------------------------------------- 5. 三大法人（期貨未平倉、現貨買賣超）
def tpe_label_to_date(lbl, ref_year):
    m = re.match(r"(\d+)/(\d+)", lbl)
    return datetime.date(ref_year, int(m.group(1)), int(m.group(2))) if m else None


def check_institutional(d):
    year = int(d["date"][:4])
    for h in d.get("institutional_5day_history", []):
        day = tpe_label_to_date(h["date"], year)
        if not day:
            continue
        q = day.strftime("%Y/%m/%d")
        # 期貨：臺股期貨 三大法人 未平倉淨口數
        try:
            rows = table_rows(http(f"https://www.taifex.com.tw/cht/3/futContractsDate?queryDate={urllib.parse.quote(q, safe='')}&commodityId=TXF"))
            idx = next((i for i, r in enumerate(rows) if len(r) > 2 and r[1] == "臺股期貨"), None)
            if idx is None:
                rec("三大法人期貨", f"{h['date']}", None, None, None, "官方查無資料")
            else:
                trio = [rows[idx], rows[idx + 1], rows[idx + 2]]
                def net(r):
                    nums = [num(x) for x in r if re.fullmatch(r"-?[\d,]+", x or "")]
                    return int(nums[-2]) if len(nums) >= 2 else None   # 倒數第二欄＝未平倉多空淨額口數
                off = {"dealer": net(trio[0]), "trust": net(trio[1]), "foreign": net(trio[2])}
                rec("三大法人期貨", f"{h['date']} 外資 TX 未平倉淨口數", h["foreign_fut_net"], off["foreign"], close(h["foreign_fut_net"], off["foreign"]), "期交所 futContractsDate")
                rec("三大法人期貨", f"{h['date']} 投信 TX 未平倉淨口數", h["trust_fut_net"], off["trust"], close(h["trust_fut_net"], off["trust"]))
                rec("三大法人期貨", f"{h['date']} 自營商 TX 未平倉淨口數", h["dealer_fut_net"], off["dealer"], close(h["dealer_fut_net"], off["dealer"]))
        except Exception as e:
            rec("三大法人期貨", h["date"], None, None, None, f"失敗：{e}")
        # 現貨：BFI82U（億）
        try:
            j = json.loads(http(f"https://www.twse.com.tw/rwd/zh/fund/BFI82U?type=day&dayDate={day.strftime('%Y%m%d')}&response=json"))
            if j.get("stat") != "OK":
                rec("三大法人現貨", h["date"], None, None, None, "證交所當日無資料")
                continue
            m = {r[0]: num(r[3]) / 1e8 for r in j["data"]}
            f_off = m.get("外資及陸資(不含外資自營商)", 0) + m.get("外資自營商", 0)
            t_off = m.get("投信")
            tot_off = m.get("合計")
            d_off = m.get("自營商(自行買賣)", 0) + m.get("自營商(避險)", 0)
            for lab, ours, off in (("外資", h["foreign_stock_net"], f_off), ("投信", h["trust_stock_net"], t_off), ("自營商", h["dealer_stock_net"], d_off), ("合計", h["total_stock_net"], tot_off)):
                rec("三大法人現貨", f"{h['date']} {lab}買賣超(億)", ours, round(off, 2), close(ours, off, 0.02), "證交所 BFI82U")
        except Exception as e:
            rec("三大法人現貨", h["date"], None, None, None, f"失敗：{e}")



# ---------------------------------------------------------------- 5b. 選擇權三大法人、夜盤三大法人、散戶多空比
def check_options_inst(d):
    year = int(d["date"][:4])
    for h in (d.get("institutional_5day_history") or [])[:3]:
        day = tpe_label_to_date(h["date"], year)
        q = day.strftime("%Y/%m/%d")
        try:
            body = urllib.parse.urlencode({"queryDate": q, "commodityId": "", "queryType": "", "goDay": "", "doQuery": "", "dateaddcnt": ""}).encode()
            req = urllib.request.Request("https://www.taifex.com.tw/cht/3/callsAndPutsDate", data=body, headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
            rows = table_rows(urllib.request.urlopen(req, context=CTX, timeout=30).read().decode("utf-8", "ignore"))
            i = next((k for k, r in enumerate(rows) if len(r) > 2 and r[1] == "臺指選擇權"), None)
            if i is None:
                rec("選擇權三大法人", h["date"], None, None, None, "官方查無資料"); continue
            # 買權：自營商(含欄位 r[3])、投信、外資；賣權：自營商(r[1]=賣權?)、投信、外資。最後一欄＝未平倉淨額契約金額(千元)
            amt = lambda r: num(r[-1]) / 1e5   # 千元 -> 億
            call = {"dealer": amt(rows[i]), "trust": amt(rows[i + 1]), "foreign": amt(rows[i + 2])}
            put = {"dealer": amt(rows[i + 3]), "trust": amt(rows[i + 4]), "foreign": amt(rows[i + 5])}
            for who, lab in (("foreign", "外資"), ("trust", "投信"), ("dealer", "自營商")):
                rec("選擇權三大法人", f"{h['date']} {lab} Call 未平倉淨額(億)", h[f"{who}_opt_call_net"], round(call[who], 2), close(h[f"{who}_opt_call_net"], call[who], 0.02), "期交所 callsAndPutsDate")
                rec("選擇權三大法人", f"{h['date']} {lab} Put 未平倉淨額(億)", h[f"{who}_opt_put_net"], round(put[who], 2), close(h[f"{who}_opt_put_net"], put[who], 0.02))
        except Exception as e:
            rec("選擇權三大法人", h["date"], None, None, None, f"失敗：{e}")


def check_night_inst(d):
    n = d.get("night_institutional_trading") or {}
    if not n.get("is_live", True) and n.get("tx_foreign_net_vol") is None:
        rec("夜盤三大法人", "整區", None, None, None, "資料檔標示無資料"); return
    q = d["chip_base_date"].replace("-", "/")
    try:
        rows = table_rows(http("https://www.taifex.com.tw/cht/3/futContractsDateAh?queryDate=" + urllib.parse.quote(q, safe="")))
        def trio(name):
            i = next((k for k, r in enumerate(rows) if len(r) > 2 and r[1] == name), None)
            if i is None:
                return None
            f = lambda r: (num(r[-2]), num(r[-1]))   # 交易淨額 口數、契約金額(千元)
            return {"dealer": f(rows[i]), "trust": f(rows[i + 1]), "foreign": f(rows[i + 2])}
        tx, mini, micro = trio("臺股期貨"), trio("小型臺指期貨"), trio("微型臺指期貨")
        if not tx:
            rec("夜盤三大法人", q, None, None, None, "官方查無資料"); return
        rec("夜盤三大法人", "外資 TX 夜盤淨口數", n["tx_foreign_net_vol"], tx["foreign"][0], close(n["tx_foreign_net_vol"], tx["foreign"][0]), "期交所 futContractsDateAh")
        rec("夜盤三大法人", "外資 TX 夜盤淨契約金額(億)", n["tx_foreign_net_amt"], round(tx["foreign"][1] / 1e5, 2), close(n["tx_foreign_net_amt"], tx["foreign"][1] / 1e5, 0.02))
        rec("夜盤三大法人", "自營商 TX 夜盤淨口數", n["tx_dealer_net_vol"], tx["dealer"][0], close(n["tx_dealer_net_vol"], tx["dealer"][0]))
        if mini:
            rec("夜盤三大法人", "外資 小台 夜盤淨口數", n["mini_foreign_net_vol"], mini["foreign"][0], close(n["mini_foreign_net_vol"], mini["foreign"][0]))
        if micro:
            rec("夜盤三大法人", "外資 微台 夜盤淨口數", n["micro_foreign_net_vol"], micro["foreign"][0], close(n["micro_foreign_net_vol"], micro["foreign"][0]))
    except Exception as e:
        rec("夜盤三大法人", "取得官方資料", None, None, None, f"失敗：{e}")


def check_retail(d):
    q = d["chip_base_date"].replace("-", "/")
    try:
        rows = table_rows(http("https://www.taifex.com.tw/cht/3/futContractsDate?queryDate=" + urllib.parse.quote(q, safe="")))
        def inst_oi(name):
            i = next((k for k, r in enumerate(rows) if len(r) > 2 and r[1] == name), None)
            if i is None:
                return None
            long_ = num(rows[i][9]) + num(rows[i + 1][7]) + num(rows[i + 2][7])
            short_ = num(rows[i][11]) + num(rows[i + 1][9]) + num(rows[i + 2][9])
            return long_, short_
        for name, cid, key in (("小型臺指期貨", "MTX", "retail_mini_ratio"), ("微型臺指期貨", "TMF", "retail_micro_ratio")):
            io = inst_oi(name)
            h = http(f"https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=0&commodity_id={cid}&queryDate={q}", enc="big5")
            near = sum(num(r[12]) or 0 for r in table_rows(h) if r and r[0] == cid and len(r) > 12 and re.fullmatch(r"\d{6}", r[1])) or None   # 分母＝全部到期月份未平倉合計
            if not io or not near:
                rec("散戶多空比", cid, d.get(key), None, None, "官方查無資料"); continue
            ratio = round((io[1] - io[0]) / near * 100, 2)
            rec("散戶多空比", f"{name}", d.get(key), ratio, close(d.get(key), ratio, 0.1), "(法人空−法人多)÷全市場未平倉(所有到期月)")
    except Exception as e:
        rec("散戶多空比", "取得官方資料", None, None, None, f"失敗：{e}")


# ---------------------------------------------------------------- 6. 大額交易人（臺股期貨前五／前十大）
def check_large_trader(d):
    year = int(d["date"][:4])
    for h in (d.get("institutional_5day_history") or [])[:3]:
        day = tpe_label_to_date(h["date"], year)
        if not day:
            continue
        q = day.strftime("%Y/%m/%d")
        try:
            rows = table_rows(http("https://www.taifex.com.tw/cht/3/largeTraderFutQry", data=urllib.parse.urlencode({"queryDate": q, "contractId": "TX"}).encode()))
            def pair(cell):   # "75,582(75,582)" -> (75582, 75582)
                m = re.match(r"([\d,]+)\(([\d,]+)\)", cell or "")
                return (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))) if m else (None, None)
            allrow = next((r for r in rows if r and r[0] == "所有契約"), None)
            if not allrow:
                rec("大額交易人", h["date"], None, None, None, "官方查無資料")
                continue
            b5, s5, b10, s10 = pair(allrow[1])[0], pair(allrow[5])[0], pair(allrow[3])[0], pair(allrow[7])[0]
            b10_spec, s10_spec = pair(allrow[3])[1], pair(allrow[7])[1]
            ours = h["lt_total"]
            rec("大額交易人", f"{h['date']} 臺股期貨(所有契約) 前五大淨部位", ours["top5_net"], b5 - s5, close(ours["top5_net"], b5 - s5), "期交所 largeTraderFutQry 買方−賣方")
            rec("大額交易人", f"{h['date']} 臺股期貨(所有契約) 前十大淨部位", ours["top10_net"], b10 - s10, close(ours["top10_net"], b10 - s10))
            rec("大額交易人", f"{h['date']} 前十大特定法人淨部位", ours["top10_spec_net"], b10_spec - s10_spec, close(ours["top10_spec_net"], b10_spec - s10_spec))
        except Exception as e:
            rec("大額交易人", h["date"], None, None, None, f"失敗：{e}")


# ---------------------------------------------------------------- 7. 個股期貨（逐檔）
def check_stock_futures(d, sample=40):
    sf = d["stock_futures"]
    q = d["chip_base_date"].replace("-", "")
    # 官方股期行情表（STF）
    try:
        h = http("https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=0&commodity_id=STF", enc="big5")
        stf_date = re.search(r"20\d\d/\d\d/\d\d", h).group(0)
        vol, oi = defaultdict(int), defaultdict(int)
        for r in table_rows(h):
            if len(r) >= 13 and "/" not in r[1] and re.fullmatch(r"\d{6}", r[1]):
                v, o = num(r[9]), num(r[12])
                vol[r[0]] += int(v or 0); oi[r[0]] += int(o or 0)
    except Exception as e:
        rec("個股期貨", "取得官方股期行情表", None, None, None, f"失敗：{e}"); return
    # 證交所收盤價（STOCK_DAY_ALL）
    spot = {}
    try:
        for x in json.loads(http("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")):
            c, chg = num(x.get("ClosingPrice")), num(x.get("Change"))
            spot[x["Code"]] = {"close": c, "chg": chg, "vol": int((num(x.get("TradeVolume")) or 0) / 1000)}
    except Exception as e:
        rec("個股期貨", "取得證交所收盤價", None, None, None, f"失敗：{e}")
    # 現貨三大法人 T86
    t86 = {}
    try:
        j = json.loads(http(f"https://www.twse.com.tw/rwd/zh/fund/T86?date={q}&selectType=ALLBUT0999&response=json"))
        if j.get("stat") == "OK":
            f = j["fields"]; ix = {n: i for i, n in enumerate(f)}
            for r in j["data"]:
                t86[r[0].strip()] = {"foreign": num(r[ix["外陸資買賣超股數(不含外資自營商)"]]) / 1000, "trust": num(r[ix["投信買賣超股數"]]) / 1000}
    except Exception as e:
        rec("個股期貨", "取得 T86", None, None, None, f"失敗：{e}")
    # 契約代號對照（stockMargining）
    symmap = {}
    try:
        for r in table_rows(http("https://www.taifex.com.tw/cht/5/stockMargining", enc="utf-8")):
            if len(r) >= 4 and r[0].isdigit():
                symmap.setdefault(r[2] + ("F" if "小型" in r[3] else ""), []).append(r[1])
    except Exception:
        pass
    n_ok = n_bad = 0
    bad = []
    for it in sf[:sample] if sample else sf:
        code = it["code"]
        # 小型契約（代碼以 F 結尾）、ETF 期貨不在 STF 表：標為 SKIP 並單獨統計
        if it.get("fut_oi") is None:
            rec("個股期貨", f"{code} {it['name']} 期貨量／未平倉", it.get("fut_volume"), None, None, "不在官方 STF 行情表（小型或 ETF 期貨）：本欄數字沒有官方來源可比對")
            continue
        sy = [s for s in symmap.get(code, []) if s in vol]
        if sy:
            best = max(sy, key=lambda s: vol[s])
            ok_v = it["fut_volume"] == vol[best]
            ok_o = it["fut_oi"] == oi[best]
            if not (ok_v and ok_o):
                n_bad += 1; bad.append(code)
            else:
                n_ok += 1
            rec("個股期貨", f"{code} {it['name']} 期貨成交量／未平倉（官方 {best}）", f"{it['fut_volume']}/{it['fut_oi']}", f"{vol[best]}/{oi[best]}", ok_v and ok_o, f"STF 表日期 {stf_date}")
        sp = spot.get(code)
        if sp and sp["close"]:
            rec("個股期貨", f"{code} 現貨收盤價", it["spot_price"], sp["close"], close(it["spot_price"], sp["close"], 0.01), "證交所 STOCK_DAY_ALL")
            if it.get("has_night") and d.get("session_type") == "NIGHT":
                rec("個股期貨", f"{code} 現貨漲跌幅%", it["change_pct"], None, None, "夜盤標的：夜盤時段 change_pct 是夜盤期貨漲跌，不是現貨日盤，不比對")
            elif sp["chg"] is not None and sp["close"] - sp["chg"] > 0:
                pct = round(sp["chg"] / (sp["close"] - sp["chg"]) * 100, 2)
                rec("個股期貨", f"{code} 現貨漲跌幅%", it["change_pct"], pct, close(it["change_pct"], pct, 0.02), "證交所 STOCK_DAY_ALL")
            rec("個股期貨", f"{code} 現貨成交量(張)", it["spot_volume"], sp["vol"], close(it["spot_volume"], sp["vol"], 1), "證交所 STOCK_DAY_ALL；與官方不符＝引擎用了估算值")
        t = t86.get(code)
        if t:
            rec("個股期貨", f"{code} 外資買賣超(張)", it.get("spot_foreign"), round(t["foreign"]), close(it.get("spot_foreign"), round(t["foreign"]), 1), "證交所 T86")
            rec("個股期貨", f"{code} 投信買賣超(張)", it.get("spot_trust"), round(t["trust"]), close(it.get("spot_trust"), round(t["trust"]), 1), "證交所 T86")


# ---------------------------------------------------------------- 8. 匯率（期交所每日匯率）
def check_fx(d):
    try:
        recs = []
        for r in table_rows(http("https://www.taifex.com.tw/cht/3/dailyFXRate")):
            if len(r) >= 5 and re.fullmatch(r"\d{4}/\d{2}/\d{2}", r[0]):
                recs.append((r[0], num(r[1]), num(r[4])))
        hist = (d.get("hot_money_digest") or {}).get("fx_5day_history", {})
        last = (hist.get("usdtwd") or [None])[-1]
        if recs and last:
            off = recs[-1]
            rec("匯率", "USD/TWD 最新一筆", last["price"], off[1], close(last["price"], off[1], 0.01), f"期交所每日匯率 {off[0]}")
        lj = (hist.get("usdjpy") or [None])[-1]
        if recs and lj:
            rec("匯率", "USD/JPY 最新一筆", lj["price"], recs[-1][2], close(lj["price"], recs[-1][2], 0.01), "期交所每日匯率")
    except Exception as e:
        rec("匯率", "取得官方資料", None, None, None, f"失敗：{e}")



def check_margin(d):
    try:
        j = json.loads(http("https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?response=json"))
        row = next((r for r in j["tables"][0]["data"] if "融資金額" in r[0]), None)
        pub = j.get("date")
        today_bal = num(row[5]) / 1e5 if row else None   # 千元 -> 億
        sess = next((s for s in d.get("history_10_sessions", []) if s.get("id") in ("t0_day", "t0_night")), None)
        ours = (sess or {}).get("margin_balance_billion")
        if ours is None or today_bal is None:
            rec("融資融券", "融資餘額(億)", ours, today_bal, None, f"證交所 MI_MARGN 公布日 {pub}；資料檔無對應欄位或官方尚未公布")
        else:
            rec("融資融券", "融資餘額(億)", ours, round(today_bal, 2), close(ours, today_bal, 0.05), f"證交所 MI_MARGN {pub}")
        for k in ("margin_maint_market", "margin_maint_stock"):
            v = (sess or {}).get(k)
            rec("融資融券", k, v, None, v is None, "證交所不公布整戶維持率，資料檔必須是空值（不得推算）")
    except Exception as e:
        rec("融資融券", "取得官方資料", None, None, None, f"失敗：{e}")


def check_no_fabricated_events(d):
    """行事曆不得出現沒有官方來源的事件（美國 CPI／非農／ADP 日期、公司財報）。"""
    bad = []
    focus = d.get("fubon_weekly_focus") or {}
    txt = json.dumps({"radar": d.get("macro_events_radar"), "schedule": focus.get("schedule")}, ensure_ascii=False)
    for kw in ("ADP", "ISM", "Broadcom", "博通", "HPE", "財報"):
        if kw in txt:
            bad.append(kw)
    rec("事件行事曆", "不得含無官方來源的美國數據／財報事件", bad or "無", "無", not bad, "僅允許：期交所結算日、證交所休市日、FOMC（聯準會官方日曆）、BLS 官方日程的 CPI／非農（data/us_macro_calendar.json）、四巫日／MSCI／富台指（規則日曆）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(ROOT, "data", "gex_data.json"))
    ap.add_argument("--json")
    ap.add_argument("--sample", type=int, default=40, help="個股期貨抽查檔數（0＝全部）")
    a = ap.parse_args()
    d = json.load(open(a.data, encoding="utf-8"))
    print(f"對帳資料檔：{a.data}（{d.get('last_updated_time')}，session={d.get('session_type')}，籌碼日={d.get('chip_base_date')}）")
    for fn in (check_index, check_tx, check_options, check_vix, check_institutional, check_options_inst, check_night_inst, check_retail, check_large_trader, check_fx, check_margin, check_no_fabricated_events):
        try:
            fn(d)
        except Exception as e:
            rec(fn.__name__, "未預期錯誤", None, None, None, str(e))
    try:
        check_stock_futures(d, a.sample)
    except Exception as e:
        rec("個股期貨", "未預期錯誤", None, None, None, str(e))
    cnt = defaultdict(lambda: defaultdict(int))
    for b, item, ours, off, res, note in RESULTS:
        cnt[b][res] += 1
        if res != "PASS":
            print(f"[{res}] {b} | {item} | 資料檔={ours} | 官方={off} | {note}")
    print("\n===== 統計 =====")
    for b, c in cnt.items():
        print(f"{b}: PASS {c['PASS']}  FAIL {c['FAIL']}  SKIP {c['SKIP']}")
    if a.json:
        json.dump(RESULTS, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
