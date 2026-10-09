"""
gex_v2_backfill.py — 回補「通行版(v2)」與「現行引擎(v1)」逐日 GEX 點位，供對照與回測。

輸出 data/gex_v2_history.json（獨立檔，不碰 gex_data.json 及任何現有欄位）。
用法： python scripts/gex_v2_backfill.py --start 2025-10-01 --end 2026-10-08 [--cache DIR] [--no-v1]

資料全部來自官方：
  期交所 optDataDown（選擇權 OI／結算價／買賣價）、futDataDown（台指期 O/H/L/C）、getVixData（臺指 VIX）、
  證交所 MI_5MINS_HIST（加權指數收盤）。缺任何一項的日子，該項留空（None），不補值。
v1 以「現行引擎的函式」重算：與 backfill_snapshots.py 同路徑，但 σ 用「當日」官方 VIX
（注意：backfill_snapshots.py 內的 v1 歷史重算呼叫 _gex_sigma_info()，抓的是「今天」的 VIX——已知差異，這裡修正為當日）。
"""
import argparse
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gex_v2 as g  # noqa: E402

OUT = os.path.join(ROOT, "data", "gex_v2_history.json")
TW = datetime.timezone(datetime.timedelta(hours=8))


def month_ranges(start, end):
    cur = start.replace(day=1)
    while cur <= end:
        nxt = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        yield max(cur, start), min(nxt - datetime.timedelta(days=1), end)
        cur = nxt


def cached(cache_dir, name, fn):
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        p = os.path.join(cache_dir, name)
        if os.path.exists(p) and os.path.getsize(p) > 200:
            return open(p, encoding="utf-8").read()
    txt = fn()
    if cache_dir:
        open(os.path.join(cache_dir, name), "w", encoding="utf-8").write(txt)
    return txt


def fetch_tx_ohlc(start, end, cache):
    """每日台指期 O/H/L/C（一般時段，取成交量最大的月份合約＝連續近月）。"""
    out = {}
    for a, b in month_ranges(start, end):
        url = ("https://www.taifex.com.tw/cht/3/futDataDown?down_type=1&commodity_id=TX"
               f"&queryStartDate={a:%Y/%m/%d}&queryEndDate={b:%Y/%m/%d}")
        txt = cached(cache, f"fut_{a:%Y%m}.csv", lambda: g.http_text(url))
        best = {}
        for line in txt.split("\n")[1:]:
            c = [x.strip() for x in line.split(",")]
            if len(c) < 18 or c[17] != "一般" or len(c[2]) != 6:
                continue
            o, h, l, cl, vol = (g._f(c[3]), g._f(c[4]), g._f(c[5]), g._f(c[6]), g._f(c[9]))
            if None in (o, h, l, cl) or vol is None:
                continue
            d = c[0].replace("/", "-")
            if d not in best or vol > best[d][0]:
                best[d] = (vol, {"o": o, "h": h, "l": l, "c": cl, "contract": c[2]})
        out.update({d: v[1] for d, v in best.items()})
        time.sleep(0.5)
    return out


def fetch_index_close(start, end, cache):
    out = {}
    for a, _ in month_ranges(start, end):
        url = f"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={a:%Y%m01}&response=json"
        txt = cached(cache, f"idx_{a:%Y%m}.json", lambda: g.http_text(url, enc="utf-8"))
        try:
            for row in json.loads(txt).get("data", []):
                y, m, d = row[0].split("/")
                v = [float(x.replace(",", "")) for x in row[1:5]]
                out[f"{int(y) + 1911}-{m}-{d}"] = {"o": v[0], "h": v[1], "l": v[2], "c": v[3]}
        except Exception as e:  # noqa: BLE001
            print(f"  [WARN] 指數 {a:%Y-%m} 解析失敗：{e}")
        time.sleep(0.5)
    return out


def fetch_vix(day, cache):
    try:
        txt = g.http_text(f"https://www.taifex.com.tw/cht/7/getVixData?filesname={day:%Y%m%d}", enc="utf-8", timeout=30, retries=1)
    except Exception:  # noqa: BLE001
        return None
    if "<html" in txt[:500].lower():     # 期交所對已過期的日期回傳 HTML 錯誤頁（官方當日檔只保留當月）
        return None
    for line in reversed([l.strip() for l in txt.splitlines() if l.strip()]):
        parts = line.split()
        if len(parts) >= 2:
            try:
                v = float(parts[-1])
                return round(v, 2) if 5 <= v <= 100 else None
            except ValueError:
                continue
    return None


def proxy_vix(per_expiry):
    """代理 VIX（**非官方**）：以 v2 反推的各到期 ATM IV，對總變異數(σ²T)線性內插到 30 天，換回年化 σ(%)。
    只用來在官方當日 VIX 取不到的歷史日子，讓 v1 的「結構」（4 桶、±900、單一 σ）仍能與 v2 並排比較；
    與官方 VIX 的差距用有官方值的日子驗證（見回測報告）。"""
    pts = sorted((e["T_days"], e["atm_iv"]) for e in per_expiry if e.get("atm_iv") and e["T_days"] >= 2)
    if not pts:
        return None
    tv = [(t / 365.0, (iv / 100.0) ** 2 * (t / 365.0)) for t, iv in pts]
    target = 30 / 365.0
    lo = [p for p in tv if p[0] <= target]
    hi = [p for p in tv if p[0] >= target]
    if lo and hi:
        x, y = lo[-1], hi[0]
        var = x[1] if y[0] == x[0] else x[1] + (y[1] - x[1]) * (target - x[0]) / (y[0] - x[0])
    else:
        p = tv[0] if not lo else tv[-1]
        var = p[1] / p[0] * target
    return round((var / target) ** 0.5 * 100, 2)


def to_v1_day_oi(day_data):
    """把 v2 解析結果轉成 v1 引擎吃的格式 {code: {expiry:'YYYYMMDD', call:{k:oi}, put:{k:oi}}}。"""
    out = {}
    for code, e in day_data.items():
        o = {"expiry": e["expiry"].strftime("%Y%m%d"), "call": {}, "put": {}}
        for (k, rt), x in e["q"].items():
            o["call" if rt == "C" else "put"][k] = x["oi"]
        out[code] = o
    return out


def v1_levels(fvc, day_iso, day_data, spot, vix):
    """以現行引擎(v1)重算當日收盤後(13:30 基準)點位。σ＝當日官方 VIX。"""
    if spot is None or vix is None:
        return None
    d = datetime.date.fromisoformat(day_iso)
    ref_dt = datetime.datetime(d.year, d.month, d.day, 13, 30, tzinfo=TW)
    day_oi = to_v1_day_oi(day_data)
    buckets = fvc.classify_txo_contract_buckets(day_oi, now=ref_dt)
    chain = fvc.build_real_option_chain(day_oi, buckets)
    dw, df, dm, _ = fvc.compute_days_to_expiries(ref_dt, TW)
    rd = fvc.days_from_expiries(ref_dt, fvc.bucket_expiry_dates(day_oi, buckets), TW)
    dw = rd['w1'] if rd.get('w1') is not None else dw
    df = rd['fri'] if rd.get('fri') is not None else df
    dm = rd['mth'] if rd.get('mth') is not None else dm
    fvc._gex_sigma_info = lambda: {"sigma": round(vix / 100.0, 4), "sigma_source": f"回補:當日 VIX {vix}", "risk_free_rate": 0.015}
    p = fvc.calculate_true_gex_profile(spot, chain, dw, df, dm, with_standard=True, days_w2=rd.get('w2'))
    return {"oi_split_level": p["zero_gamma_level"], "gamma_flip_standard": p["gamma_flip_standard"],
            "call_wall": p["call_wall_strike"], "put_wall": p["put_wall_strike"], "max_pain": p["max_pain_strike"],
            "total_gex_raw": p["total_gex_val"], "total_gex_per1pct": round(p["total_gex_val"] / 100.0, 3)}


def slim(lv):
    """歷史檔只留必要欄位（不含 per_strike，避免檔案過大）。"""
    keep = ("S0", "F_front", "total_gex", "flip", "flip_all", "call_wall_net", "call_wall_net_gex", "put_wall_net",
            "put_wall_net_gex", "call_wall_side", "put_wall_side", "top_pos", "top_neg", "max_pain_all",
            "coverage_iv_pct", "per_expiry")
    r = {k: lv[k] for k in keep}
    r["diag"] = lv["diag"]
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--cache")
    ap.add_argument("--no-v1", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    start, end = datetime.date.fromisoformat(a.start), datetime.date.fromisoformat(a.end)
    # 結果需要隔日資料，所以多抓幾天做 outcome
    end_ext = min(end + datetime.timedelta(days=7), datetime.date.today())
    fvc = None
    if not a.no_v1:
        import fetch_and_calc_vision as fvc  # noqa: E402

    print("下載台指期、加權指數…")
    tx = fetch_tx_ohlc(start, end_ext, a.cache)
    idx = fetch_index_close(start, end_ext, a.cache)

    days = {}
    for ms, me in month_ranges(start, end):
        txt = cached(a.cache, f"opt_{ms:%Y%m}_{me:%d}.csv", lambda: g.fetch_opt_text(ms, me))
        parsed = g.parse_opt(txt)
        print(f"{ms:%Y-%m}: {len(parsed)} 個交易日")
        for day_iso in sorted(parsed):
            if not (start <= datetime.date.fromisoformat(day_iso) <= end):
                continue
            ix = idx.get(day_iso)
            spot = ix["c"] if ix else None
            lv = g.compute_day(day_iso, parsed[day_iso], spot=spot)
            if lv is None:
                continue
            vix = fetch_vix(datetime.date.fromisoformat(day_iso), a.cache)
            vp = proxy_vix(lv["per_expiry"])
            rec = {"index_close": spot, "index": ix, "vix": vix, "vix_proxy": vp, "tx": tx.get(day_iso), "v2": slim(lv),
                   "v1": None, "v1_proxy": None}
            if fvc is not None:
                try:
                    rec["v1"] = v1_levels(fvc, day_iso, parsed[day_iso], spot, vix)          # 官方當日 VIX（取不到則 None）
                    rec["v1_proxy"] = v1_levels(fvc, day_iso, parsed[day_iso], spot, vp)     # 代理 VIX（非官方）
                except Exception as e:  # noqa: BLE001
                    print(f"  [WARN] {day_iso} v1 重算失敗：{e}")
            days[day_iso] = rec
        time.sleep(0.5)

    # 隔日 outcome 需要的 TX 資料也一併存（含 end 之後幾天）
    extra_tx = {d: v for d, v in tx.items() if d > end.isoformat()}
    extra_idx = {d: v for d, v in idx.items() if d > end.isoformat()}
    out = {
        "meta": {
            "created": datetime.datetime.now(TW).isoformat(timespec="seconds"),
            "range": [a.start, a.end],
            "v2": "通行版：Black-76、各到期 F（put-call parity）、每履約價 IV（價外側中間價，無則結算價）、全合約全履約價、×0.01、"
                  "T=日曆天/365、牆=淨GEX最大/最小、翻轉點=價位掃描(以加權指數收盤為基準，各到期F同比例平移、IV固定)",
            "v1": "現行引擎函式重算（單一當日 VIX、4 桶、現價±900）；total_gex_per1pct = total_gex_raw/100 以便與 v2 同單位",
            "min_price": g.MIN_PRICE, "r": g.R_FREE,
            "note": "模型輸出，不是預測；牆與翻轉點不代表價格會停留或反轉。缺資料的欄位為 null，未補值。",
        },
        "days": days,
        "tx_after_range": extra_tx,
        "index_after_range": extra_idx,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"完成：{len(days)} 天 → {a.out}（{os.path.getsize(a.out) / 1024:.0f} KB）")


if __name__ == "__main__":
    main()
