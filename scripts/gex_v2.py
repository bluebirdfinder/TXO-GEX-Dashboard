"""
gex_v2.py — 「通行版」GEX（教科書／業界常用寫法），與 fetch_and_calc_vision.py 的現行引擎(v1)並行，不覆蓋任何現有欄位。

2026-10-09 建立。動機：與老墨 MOFI 頁面及美股通行寫法對照後，發現 v1 有 (1) 少乘 0.01、(2) 單一 VIX 當 σ、
(3) 只算 w1/w2/fri/mth 四檔且限現價附近履約價。本檔用同一份期交所官方盤後檔 (optDataDown) 做通行算法，
供回補回測與每日並行累積，**由使用者決定**日後要不要取代 v1。

通行算法（SqueezeMetrics / 開源教學 / 一般業者共通的寫法）：
    每個履約價每個到期的 GEX = (CallOI − PutOI) × Γ × F² × 50 × 0.01 / 1e8      （億 NT$／指數每動 1%）
    Γ：Black-76，F＝各到期期貨價，σ＝該履約價自己的隱含波動率，T＝距結算日曆天/365
    買權 +、賣權 −（假設造市商持買權、賣賣權——簡化假設，實際看不到）
    所有到期、所有履約價加總；牆＝各履約價淨 GEX 的最大／最小；翻轉點＝價位掃描的零點

資料誠實原則（AGENTS.md 紅線 6）：
    - 全部來自期交所官方檔；F 由 put-call parity 從結算價反推；IV 由價外側報價反推。
    - 反推不出來的履約價（無報價、價格過低、違反無套利）**排除並計入 excluded_oi**，絕不插補、不補假值。
    - IV 價格優先用「最後最佳買賣價中間價」，沒有才用結算價，並記錄來源比例（結算價對冷門價外可能是理論價）。
    - 這是模型輸出，不是預測；牆與翻轉點不代表價格會停留或反轉。
"""
import datetime
import math
import re
import ssl
import time
import urllib.request
from collections import defaultdict

R_FREE = 0.015          # 與 v1 相同；對 Γ 影響極小
MULT = 50.0             # TXO 每點 50 元
PER_PCT = 0.01          # 「指數每動 1%」
MIN_PRICE = 0.1         # 最小跳動單位；低於此價（地板價）IV 無意義 → 排除。0.05~0.1 與 0.5 比較：牆位不變，總 GEX 差約 7%
CTX = ssl.create_default_context()
CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT
UA = {"User-Agent": "Mozilla/5.0"}


# ------------------------------------------------------------------ Black-76
def _pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def b76_price(F, K, T, sigma, is_call, r=R_FREE):
    if T <= 0 or sigma <= 0:
        return max(0.0, (F - K) if is_call else (K - F)) * math.exp(-r * T)
    sd = sigma * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sd * sd) / sd
    d2 = d1 - sd
    df = math.exp(-r * T)
    return df * (F * _cdf(d1) - K * _cdf(d2)) if is_call else df * (K * _cdf(-d2) - F * _cdf(-d1))


def b76_gamma(F, K, T, sigma):
    """dΔ/dF（對期貨價）；與 v1 的 BS gamma 同形（折現因子在 GEX 層級可忽略，通行寫法不含）。"""
    if T <= 0 or sigma <= 0 or F <= 0 or K <= 0:
        return 0.0
    sd = sigma * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * sd * sd) / sd
    return _pdf(d1) / (F * sd)


def implied_vol(price, F, K, T, is_call, r=R_FREE):
    """二分法反推 Black-76 IV；價格不合無套利界限 → None（不編造）。"""
    if price is None or price < MIN_PRICE or T <= 0:
        return None
    df = math.exp(-r * T)
    intrinsic = df * max(0.0, (F - K) if is_call else (K - F))
    upper = df * (F if is_call else K)
    if price <= intrinsic + 1e-9 or price >= upper:
        return None
    lo, hi = 0.01, 3.0
    if b76_price(F, K, T, hi, is_call, r) < price or b76_price(F, K, T, lo, is_call, r) > price:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if b76_price(F, K, T, mid, is_call, r) < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------------------------ 結算日備援推導
_HOL = None


def _holidays():
    global _HOL
    if _HOL is None:
        import json
        import os
        try:
            p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tw_holidays.json")
            _HOL = set(json.load(open(p, encoding="utf-8")).get("holidays", []))
        except Exception:  # noqa: BLE001
            _HOL = set()
    return _HOL


def derive_expiry(code):
    """期交所舊檔（約 2025-12 中旬前）沒有「契約到期日」欄，改由合約代碼推導：
    YYYYMM＝該月第 3 個週三；YYYYMMWn＝第 n 個週三；YYYYMMFn＝第 n 個週五；遇休市順延到下一個交易日。
    已用有真實到期日的資料逐一驗證此規則（見 docs/GEX_V2_BACKTEST_*.md），推不出來就回 None（不猜）。"""
    m = re.fullmatch(r"(\d{4})(\d{2})(?:([WF])(\d))?", code.strip())
    if not m:
        return None
    y, mo, kind, n = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
    wd = 4 if kind == "F" else 2
    nth = int(n) if n else 3
    d = datetime.date(y, mo, 1)
    d += datetime.timedelta(days=(wd - d.weekday()) % 7 + 7 * (nth - 1))
    if d.month != mo:
        return None
    hol = _holidays()
    while d.weekday() >= 5 or d.isoformat() in hol:
        d += datetime.timedelta(days=1)
    return d


# ------------------------------------------------------------------ 下載與解析
def http_text(url, enc="cp950", timeout=60, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
                return r.read().decode(enc, errors="ignore")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"下載失敗 {url}: {last}")


def fetch_opt_text(start, end):
    """start/end: datetime.date。期交所單次最多約一個月。"""
    return http_text("https://www.taifex.com.tw/cht/3/optDataDown?down_type=1&commodity_id=TXO"
                     f"&queryStartDate={start:%Y/%m/%d}&queryEndDate={end:%Y/%m/%d}")


def _f(x):
    x = x.strip()
    if x in ("", "-"):
        return None
    try:
        return float(x.replace(",", ""))
    except ValueError:
        return None


def parse_opt(text):
    """回傳 {date_iso: {code: {"expiry": date, "q": {(strike, 'C'|'P'): {oi, settle, bid, ask, close}}}}}。
    欄位（cp950）：[0]日期 [2]到期月份(週別) [3]履約價 [4]買賣權 [8]收盤價 [10]結算價 [11]未沖銷 [12]最佳買 [13]最佳賣 [17]時段 [20]到期日。
    只取「一般」時段（OI 只在一般時段列有值）。"""
    out = {}
    for line in text.split("\n")[1:]:
        c = [x.strip() for x in line.split(",")]
        if len(c) < 21 or c[17] != "一般":
            continue
        k = _f(c[3])
        if k is None:
            continue
        right = "C" if "買" in c[4] else ("P" if "賣" in c[4] else None)
        if right is None:
            continue
        try:
            exp = datetime.datetime.strptime(c[20], "%Y%m%d").date()
        except ValueError:
            exp = derive_expiry(c[2])      # 舊檔無此欄 → 由代碼推導
            if exp is None:
                continue
        oi = _f(c[11])
        d = out.setdefault(c[0].replace("/", "-"), {})
        e = d.setdefault(c[2], {"expiry": exp, "q": {}})
        e["q"][(k, right)] = {"oi": int(oi) if oi is not None else 0, "settle": _f(c[10]),
                              "bid": _f(c[12]), "ask": _f(c[13]), "close": _f(c[8])}
    return out


# ------------------------------------------------------------------ 單日計算
def forward_from_parity(q, T, r=R_FREE):
    """F = K + e^{rT}(C − P)，取 |C−P| 最小的 3 個履約價的中位數（用結算價，兩邊都要有 ≥ MIN_PRICE）。"""
    cands = []
    ks = sorted({k for (k, _) in q})
    for k in ks:
        c, p = q.get((k, "C")), q.get((k, "P"))
        if not c or not p:
            continue
        cs, ps = c["settle"], p["settle"]
        if cs is None or ps is None or cs < MIN_PRICE or ps < MIN_PRICE:
            continue
        cands.append((abs(cs - ps), k + math.exp(r * T) * (cs - ps)))
    if len(cands) < 1:
        return None
    cands.sort()
    top = sorted(f for _, f in cands[:3])
    return top[len(top) // 2]


def _quote_price(x, is_call, F, K):
    """IV 用價：買賣價都有且 0<bid≤ask 用中間價；否則用結算價。回傳 (price, source)。"""
    b, a, s = x.get("bid"), x.get("ask"), x.get("settle")
    if b is not None and a is not None and 0 < b <= a:
        return (b + a) / 2.0, "mid"
    if s is not None and s > 0:
        return s, "settle"
    return None, None


def build_day(day_iso, day_data, r=R_FREE):
    """把一天的官方檔整理成可算 GEX 的結構。已到期（到期日 ≤ 當日）的合約剔除（13:30 後已結算）。"""
    day = datetime.date.fromisoformat(day_iso)
    expiries = []
    diag = {"oi_total": 0, "oi_used": 0, "oi_no_iv": 0, "iv_mid": 0, "iv_settle": 0, "contracts": 0, "skipped_dead": 0}
    for code, e in sorted(day_data.items(), key=lambda kv: kv[1]["expiry"]):
        if e["expiry"] <= day:
            diag["skipped_dead"] += 1
            continue
        T = (e["expiry"] - day).days / 365.0
        q = e["q"]
        F = forward_from_parity(q, T, r)
        n_oi = sum(v["oi"] for v in q.values())
        diag["oi_total"] += n_oi
        diag["contracts"] += 1
        if F is None or n_oi == 0:
            diag["oi_no_iv"] += n_oi
            continue
        strikes = {}
        for k in sorted({k for (k, _) in q}):
            is_call = k >= F                      # 價外側：K≥F 取買權，否則賣權
            x = q.get((k, "C" if is_call else "P"))
            iv = None
            if x:
                price, src = _quote_price(x, is_call, F, k)
                iv = implied_vol(price, F, k, T, is_call, r)
                if iv is not None:
                    diag["iv_mid" if src == "mid" else "iv_settle"] += 1
            c_oi = q.get((k, "C"), {}).get("oi", 0)
            p_oi = q.get((k, "P"), {}).get("oi", 0)
            if iv is None:
                diag["oi_no_iv"] += c_oi + p_oi
                continue
            diag["oi_used"] += c_oi + p_oi
            strikes[k] = {"iv": iv, "c_oi": c_oi, "p_oi": p_oi}
        expiries.append({"code": code, "expiry": e["expiry"], "T": T, "F": F, "strikes": strikes, "oi": n_oi})
    return {"day": day_iso, "expiries": expiries, "diag": diag}


def gex_cell(F, K, T, iv, c_oi, p_oi):
    """通行公式；回傳 (call_side, put_side)，put_side 為負。"""
    g = b76_gamma(F, K, T, iv) * F * F * MULT * PER_PCT / 1e8
    return c_oi * g, -p_oi * g


def total_at(built, scale):
    """假設所有到期的期貨價同比例平移 scale（IV 固定＝sticky-strike），回傳總 GEX（億/每1%）。"""
    t = 0.0
    for e in built["expiries"]:
        F = e["F"] * scale
        for k, s in e["strikes"].items():
            a, b = gex_cell(F, k, e["T"], s["iv"], s["c_oi"], s["p_oi"])
            t += a + b
    return t


def levels(built, spot=None, span=2000.0, step=25.0):
    """當日所有點位。spot＝掃描基準（通常用加權指數收盤，與 v1 一致）；沒給就用近月月選 F。"""
    exps = built["expiries"]
    if not exps:
        return None
    monthly = [e for e in exps if re.fullmatch(r"\d{6}", e["code"].strip())]
    f_front = (monthly[0] if monthly else exps[0])["F"]
    S0 = spot if spot else f_front
    per_k = defaultdict(lambda: [0.0, 0.0])
    per_exp = []
    for e in exps:
        te = 0.0
        for k, s in e["strikes"].items():
            a, b = gex_cell(e["F"], k, e["T"], s["iv"], s["c_oi"], s["p_oi"])
            per_k[k][0] += a
            per_k[k][1] += b
            te += a + b
        atm = None
        if e["strikes"]:
            kk = min(e["strikes"], key=lambda k: abs(k - e["F"]))
            atm = round(e["strikes"][kk]["iv"] * 100, 2)      # 最接近 F 的履約價之 IV（ATM IV）
        per_exp.append({"code": e["code"].strip(), "expiry": e["expiry"].isoformat(), "T_days": round(e["T"] * 365),
                        "F": round(e["F"], 1), "gex": round(te, 3), "oi": e["oi"], "strikes_with_iv": len(e["strikes"]),
                        "atm_iv": atm})
    net = {k: v[0] + v[1] for k, v in per_k.items()}
    total = sum(net.values())
    call_wall = max(net, key=net.get)
    put_wall = min(net, key=net.get)
    call_side = max(per_k, key=lambda k: per_k[k][0])
    put_side = min(per_k, key=lambda k: per_k[k][1])
    # 價位掃描翻轉點：同比例平移（以 S0 為準），取離 S0 最近的零點；也回傳全部零點供檢視
    zeros, prev = [], None
    n = int(span / step)
    for i in range(-n, n + 1):
        S = S0 + i * step
        v = total_at(built, S / S0)   # 所有到期的 F 同比例平移，IV 固定（sticky-strike）
        if prev is not None and prev[1] * v <= 0 and prev[1] != v:
            zeros.append(prev[0] + (0 - prev[1]) * (S - prev[0]) / (v - prev[1]))
        prev = (S, v)
    flip = min(zeros, key=lambda z: abs(z - S0)) if zeros else None
    # Max Pain：全合約、全履約價（只取決於 OI）
    return {
        "S0": round(S0, 2), "F_front": round(f_front, 1), "total_gex": round(total, 3),
        "flip": round(flip, 1) if flip is not None else None, "flip_all": [round(z, 1) for z in zeros],
        "call_wall_net": call_wall, "call_wall_net_gex": round(net[call_wall], 3),
        "put_wall_net": put_wall, "put_wall_net_gex": round(net[put_wall], 3),
        "call_wall_side": call_side, "put_wall_side": put_side,
        "top_pos": [(k, round(v, 3)) for k, v in sorted(net.items(), key=lambda kv: -kv[1])[:3]],
        "top_neg": [(k, round(v, 3)) for k, v in sorted(net.items(), key=lambda kv: kv[1])[:3]],
        "per_expiry": per_exp,
        "per_strike": {int(k): [round(v[0], 4), round(v[1], 4)] for k, v in sorted(per_k.items())},
    }


def max_pain_all(day_data, day):
    """全合約全履約價的最大痛點（含未到期合約；不涉及 σ）。"""
    C, P = defaultdict(int), defaultdict(int)
    for code, e in day_data.items():
        if e["expiry"] <= day:
            continue
        for (k, rt), x in e["q"].items():
            (C if rt == "C" else P)[k] += x["oi"]
    ks = sorted(set(C) | set(P))
    if not ks:
        return None
    return min(ks, key=lambda S: sum(max(0, S - k) * C.get(k, 0) + max(0, k - S) * P.get(k, 0) for k in ks))


def compute_day(day_iso, day_data, spot=None):
    built = build_day(day_iso, day_data)
    lv = levels(built, spot=spot)
    if lv is None:
        return None
    lv["max_pain_all"] = max_pain_all(day_data, datetime.date.fromisoformat(day_iso))
    d = built["diag"]
    lv["diag"] = d
    lv["coverage_iv_pct"] = round(d["oi_used"] / d["oi_total"] * 100, 2) if d["oi_total"] else None
    return lv
