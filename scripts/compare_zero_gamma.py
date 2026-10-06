"""
compare_zero_gamma.py — 並排比較兩種 Zero Gamma 算法（只做分析，不改資料檔、不影響網頁）。

A. 現行（沿「履約價軸」）：照當天收盤現價，算每個履約價上 Call 與 Put 的淨 GEX，由低到高找符號翻轉處（線性內插）。
   這是 calculate_true_gex_profile() 目前的做法。
B. 標準（沿「價格軸」，SpotGamma 等的 Gamma Flip）：假設指數漲跌到一排不同價位 S，在每個價位重新計算所有履約價的
   Gamma 後加總做市商總 GEX(S)；總和由負轉正（或由正轉負）的價位就是 Zero Gamma。

兩者都使用同一份期交所官方未平倉、同一個波動率（當日官方臺指 VIX）、同一套 Black-Scholes，只差「在哪條軸上找 0」。

用法：python scripts/compare_zero_gamma.py [天數，預設 5]
"""
import datetime
import importlib.util
import json
import os
import ssl
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
spec = importlib.util.spec_from_file_location("eng", os.path.join(ROOT, "scripts", "fetch_and_calc_vision.py"))
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)

TZ = datetime.timezone(datetime.timedelta(hours=8))
CTX = ssl.create_default_context()
CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT


def twse_closes(n):
    """證交所 FMTQIK：近幾日加權指數收盤（官方）。"""
    out = {}
    now = datetime.datetime.now(TZ)
    for back in (0, 1):
        d = (now.replace(day=1) - datetime.timedelta(days=back * 28)).strftime("%Y%m01")
        req = urllib.request.Request(f"https://www.twse.com.tw/exchangeReport/FMTQIK?response=json&date={d}", headers={"User-Agent": "Mozilla/5.0"})
        j = json.loads(urllib.request.urlopen(req, context=CTX, timeout=30).read().decode("utf-8"))
        for r in j.get("data", []):
            y, m, dd = r[0].split("/")
            out[datetime.date(int(y) + 1911, int(m), int(dd))] = float(r[4].replace(",", ""))
    return dict(sorted(out.items())[-n:])


def net_gex_at(S, chain, T, sigma, r=0.015):
    """價格軸上的總 GEX(S)：calls 為正、puts 為負（與引擎同號、同單位），各到期週別用各自的 T。"""
    tot = 0.0
    for K, k in chain.items():
        for b, Tb in T.items():
            g = eng.black_scholes_gamma(S, K, Tb, r, sigma)
            tot += (k.get(f"call_oi_{b}", 0) - k.get(f"put_oi_{b}", 0)) * g * (S ** 2) * 50 / 1e8
    return tot


def zero_crossings(f, lo, hi, step):
    xs, prev = [], None
    S = lo
    while S <= hi:
        v = f(S)
        if prev is not None and prev[1] * v <= 0 and prev[1] != v:
            xs.append(round(prev[0] + (0 - prev[1]) * (S - prev[0]) / (v - prev[1]), 1))
        prev = (S, v)
        S += step
    return xs


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    closes = twse_closes(n)
    days = list(closes)
    oi = eng.fetch_taifex_txo_open_interest(days[0].strftime("%Y/%m/%d"), days[-1].strftime("%Y/%m/%d"))
    vix = eng.fetch_official_taifex_vix().get("taifex_vix")
    sigma = (vix / 100.0) if vix else 0.18
    print(f"\n波動率 σ={sigma:.4f}（{'當日官方臺指 VIX' if vix else '固定假設'}），r=1.5%；每日各用當天收盤現價與當天官方未平倉\n")
    print(f"{'日期':<11}{'加權收盤':>10}{'A 現行':>10}{'B 標準(離現價最近)':>20}{'B 全部轉折點':>22}{'現價處總GEX':>12}")
    for d in days:
        key = d.strftime("%Y-%m-%d")
        if key not in oi:
            print(f"{key:<11}（期交所當日無未平倉資料）")
            continue
        now = datetime.datetime(d.year, d.month, d.day, 14, 0, tzinfo=TZ)
        buckets = eng.classify_txo_contract_buckets(oi[key], now=now)
        chain = eng.build_real_option_chain(oi[key], buckets)
        wed, fri, mth, _ = eng.compute_days_to_expiries(now, TZ)
        MIN_T = 0.5
        T_w1 = max(float(wed), MIN_T) / 365.0
        T = {"w1": T_w1, "w2": T_w1 + 7 / 365.0, "fri": max(float(fri), MIN_T) / 365.0, "mth": max(float(mth), MIN_T) / 365.0}
        S0 = closes[d]
        # A：引擎現行（臨時覆寫 σ）
        saved = eng._gex_sigma_info
        eng._gex_sigma_info = lambda s=sigma: {"sigma": s, "sigma_source": "cmp", "risk_free_rate": 0.015}
        try:
            a = eng.calculate_true_gex_profile(S0, chain, wed, fri, mth)["zero_gamma_level"]
        finally:
            eng._gex_sigma_info = saved
        # B：價格軸掃描
        xs = zero_crossings(lambda S: net_gex_at(S, chain, T, sigma), S0 - 2000, S0 + 2000, 10)
        nearest = min(xs, key=lambda x: abs(x - S0)) if xs else None
        g0 = net_gex_at(S0, chain, T, sigma)
        print(f"{key:<11}{S0:>10,.0f}{a:>10,.1f}{(nearest if nearest is not None else float('nan')):>20,.1f}{str(xs):>22}{g0:>12,.0f}")
    print("\n說明：A 與 B 差距大的日子，代表『履約價軸上的牆位交界』和『價格軸上做市商由穩定轉為助跌的轉折』是兩個不同位置；"
          "B 沒有任何轉折點（空清單）代表掃描範圍內總 GEX 恆正或恆負，標準算法也沒有轉折點可報。")


if __name__ == "__main__":
    main()
