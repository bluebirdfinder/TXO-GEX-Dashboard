"""
gex_v2_backtest.py — 讀 data/gex_v2_history.json，量化「通行版(v2)」與「現行引擎(v1)」的點位差距，並做事先寫定的回測。

【事先登記的判斷標準（2026-10-09 在看到結果前寫定，之後不得為了好看而改）】
  M1 點位差距：v1 − v2 的逐日差（標準 Gamma Flip／買權牆／賣權牆／Max Pain／總GEX）。只描述，不評好壞。
     v1 有兩種 σ 來源：官方當日 VIX（期交所只保留當月檔，所以天數少）與代理 VIX（v2 反推的 30 天 ATM IV，非官方，全期可算）。
  M2 總 GEX vs 隔日波動：日 t 收盤後的總 GEX（v1、v2 各一）與「日 t+1 指數 (最高−最低)/日t收盤」的 Spearman 相關，
     以及總 GEX 最高 1/3 與最低 1/3 兩組的隔日波動平均差（排列檢定 p 值）。理論預期：GEX 越正 → 隔日波動越小（負相關）。
  M3 翻轉點位置：日 t 收盤在翻轉點上方 vs 下方，隔日波動幅度與隔日絕對報酬的差（排列檢定）。理論預期：下方波動較大。
  M4 牆被觸及：日 t+1 的 [最低,最高] 是否碰到買權牆／賣權牆；對照組＝以日 t 收盤為軸的鏡像價位（距離相同、方向相反）。
     只看距離收盤 ≤ 3% 的牆。
  M5 Max Pain：|日t+1 收盤 − Max Pain| 的平均，v1 vs v2；以及 Max Pain 是否比「日t收盤不動」更接近日t+1收盤。
  不做事後挑選；顯著性不做多重比較校正，所以 p 值只能當參考。樣本日數很少、日與日 OI 高度重疊，**結論只能是「方向有沒有證據」，
  不能證明準不準，更不是進出場訊號**。

【無偷看未來】日 t 的點位只用日 t 收盤後公布的 OI／結算價；結果全部取日 t+1 以後。
"""
import argparse
import json
import os
import random
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "data", "gex_v2_history.json")


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def spearman(a, b):
    if len(a) < 5:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = st.mean(ra), st.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else None


def perm_p(g1, g2, n=10000, seed=7):
    """兩組平均差的雙尾排列檢定。"""
    if len(g1) < 5 or len(g2) < 5:
        return None
    obs = abs(st.mean(g1) - st.mean(g2))
    pool = list(g1) + list(g2)
    rnd = random.Random(seed)
    k = len(g1)
    hit = 0
    for _ in range(n):
        rnd.shuffle(pool)
        if abs(st.mean(pool[:k]) - st.mean(pool[k:])) >= obs:
            hit += 1
    return (hit + 1) / (n + 1)


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def fmt(x, d=1):
    return "—" if x is None else (f"{x:,.{d}f}")


def safe(fn):
    def w(r):
        try:
            return fn(r)
        except (TypeError, KeyError):
            return None
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hist", default=HIST)
    ap.add_argument("--md")
    a = ap.parse_args()
    H = json.load(open(a.hist, encoding="utf-8"))
    days = H["days"]
    idx = {d: v["index"] for d, v in days.items() if v.get("index")}
    idx.update(H.get("index_after_range", {}))
    dates = sorted(idx)
    nxt = {dates[i]: dates[i + 1] for i in range(len(dates) - 1)}
    L = []
    out = L.append

    def sec(t):
        out(f"\n## {t}\n")

    VERS = [("v1(代理VIX)", "v1_proxy"), ("v1(官方VIX)", "v1")]
    n_off = sum(1 for d in days.values() if d.get("v1"))
    n_prx = sum(1 for d in days.values() if d.get("v1_proxy"))
    rows = []
    for d in sorted(days):
        r = days[d]
        if d not in nxt or not idx.get(d):
            continue
        c0, n = idx[d]["c"], idx[nxt[d]]
        rows.append({"d": d, "c0": c0, "rng": (n["h"] - n["l"]) / c0 * 100, "ret": (n["c"] - c0) / c0 * 100,
                     "hi": n["h"], "lo": n["l"], "c1": n["c"], "r": r})
    out(f"# 通行版(v2) vs 現行引擎(v1)：點位差距與回測（{min(days)} ~ {max(days)}，共 {len(days)} 個交易日；有隔日資料可回測 {len(rows)} 天）")
    out("\n> 模型輸出，不是預測。牆與翻轉點不代表價格會停留或反轉。判斷標準於看結果前寫定（見 scripts/gex_v2_backtest.py 檔頭）。")
    out(f"\nv1 以官方當日 VIX 重算的天數：{n_off}（期交所只保留當月檔）；以代理 VIX 重算的天數：{n_prx}。")
    pv = [(d, v["vix"], v["vix_proxy"]) for d, v in sorted(days.items()) if v.get("vix") and v.get("vix_proxy")]
    if pv:
        out("代理 VIX 驗證（有官方值的日子）：" + "；".join(f"{d[5:]} 官方 {o} / 代理 {p}" for d, o, p in pv)
            + f"。平均絕對誤差 {st.mean(abs(o - p) for _, o, p in pv):.2f} 個 VIX 點。")

    # ---------------- M1
    sec("M1 點位差距（v1 − v2，指數點；每日收盤後）")
    pairs = {
        "標準 Gamma Flip": lambda k: safe(lambda r: (r[k]["gamma_flip_standard"], r["v2"]["flip"])),
        "買權牆（v2 用淨 GEX 最大）": lambda k: safe(lambda r: (r[k]["call_wall"], r["v2"]["call_wall_net"])),
        "賣權牆（v2 用淨 GEX 最小）": lambda k: safe(lambda r: (r[k]["put_wall"], r["v2"]["put_wall_net"])),
        "賣權牆（v2 改用 v1 同定義：賣權側最大）": lambda k: safe(lambda r: (r[k]["put_wall"], r["v2"]["put_wall_side"])),
        "買權牆（v2 改用 v1 同定義：買權側最大）": lambda k: safe(lambda r: (r[k]["call_wall"], r["v2"]["call_wall_side"])),
        "Max Pain（v2 全合約）": lambda k: safe(lambda r: (r[k]["max_pain"], r["v2"]["max_pain_all"])),
    }
    for vname, vk in VERS:
        out(f"\n**{vname}**\n")
        out("| 項目 | n | 平均差 | 中位差 | 平均|差| | 90% 分位|差| | 完全相同 | |差|≤100 點 |")
        out("|---|---|---|---|---|---|---|---|")
        for name, mk in pairs.items():
            fn = mk(vk)
            diffs = []
            for d in sorted(days):
                v = fn(days[d])
                if v and v[0] is not None and v[1] is not None:
                    diffs.append(v[0] - v[1])
            if not diffs:
                continue
            ab = [abs(x) for x in diffs]
            out(f"| {name} | {len(diffs)} | {fmt(st.mean(diffs))} | {fmt(st.median(diffs))} | {fmt(st.mean(ab))} | {fmt(pct(ab, .9))} | "
                f"{sum(1 for x in ab if x == 0) / len(ab) * 100:.0f}% | {sum(1 for x in ab if x <= 100) / len(ab) * 100:.0f}% |")
        tr = [(days[d][vk]["total_gex_per1pct"], days[d]["v2"]["total_gex"]) for d in sorted(days) if days[d].get(vk)]
        ratio = [x / y for x, y in tr if y and y > 0 and x > 0]
        if ratio:
            out(f"\n總 GEX（同單位 億/每1%）：v1/v2 比值（兩者皆為正的 {len(ratio)} 天）中位數 {fmt(st.median(ratio), 2)}、"
                f"90% 分位 {fmt(pct(ratio, .9), 2)}、最小 {fmt(min(ratio), 2)}、最大 {fmt(max(ratio), 2)}；"
                f"兩者正負號不同的天數 {sum(1 for x, y in tr if (x > 0) != (y > 0))}/{len(tr)}。")
    cov = [days[d]["v2"]["coverage_iv_pct"] for d in days if days[d]["v2"].get("coverage_iv_pct") is not None]
    out(f"\nv2 的 IV 覆蓋率（OI 口數中成功反推 IV 的比例）：平均 {fmt(st.mean(cov), 1)}%、最低 {fmt(min(cov), 1)}%。")

    # ---------------- 各版本取值器
    SRC = [("v2", safe(lambda r: r["v2"]["total_gex"]), safe(lambda r: r["v2"]["flip"]), safe(lambda r: r["v2"]["call_wall_net"]),
            safe(lambda r: r["v2"]["put_wall_net"]), safe(lambda r: r["v2"]["max_pain_all"]))]
    for vname, vk in VERS:
        SRC.append((vname, safe(lambda r, vk=vk: r[vk]["total_gex_per1pct"]), safe(lambda r, vk=vk: r[vk]["gamma_flip_standard"]),
                    safe(lambda r, vk=vk: r[vk]["call_wall"]), safe(lambda r, vk=vk: r[vk]["put_wall"]), safe(lambda r, vk=vk: r[vk]["max_pain"])))

    # ---------------- M2
    sec("M2 總 GEX vs 隔日波動（預期負相關：GEX 越正、隔日越不晃）")
    out("| 版本 | n | Spearman(總GEX, 隔日波動%) | 最高1/3 平均隔日波動% | 最低1/3 平均隔日波動% | 差 | 排列檢定 p |")
    out("|---|---|---|---|---|---|---|")
    for name, tot, flip, cw, pw, mp in SRC:
        pr = [(tot(x["r"]), x["rng"]) for x in rows if tot(x["r"]) is not None]
        if len(pr) < 15:
            out(f"| {name} | {len(pr)} | 樣本太少，不計算 | | | | |")
            continue
        xs, ys = [p[0] for p in pr], [p[1] for p in pr]
        rho = spearman(xs, ys)
        o = sorted(range(len(xs)), key=lambda i: xs[i])
        k = len(o) // 3
        lo_g, hi_g = [ys[i] for i in o[:k]], [ys[i] for i in o[-k:]]
        out(f"| {name} | {len(xs)} | {fmt(rho, 3)} | {fmt(st.mean(hi_g), 2)} | {fmt(st.mean(lo_g), 2)} | {fmt(st.mean(hi_g) - st.mean(lo_g), 2)} | {fmt(perm_p(hi_g, lo_g), 3)} |")

    # ---------------- M3
    sec("M3 收盤在翻轉點上方 vs 下方（預期：下方隔日波動較大）")
    out("| 版本 | 上方 n | 下方 n | 上方 平均隔日波動% | 下方 平均隔日波動% | p（波動） | 上方 平均|報酬|% | 下方 平均|報酬|% | p（|報酬|） |")
    out("|---|---|---|---|---|---|---|---|---|")
    for name, tot, flip, cw, pw, mp in SRC:
        up_r, dn_r, up_a, dn_a = [], [], [], []
        for x in rows:
            f = flip(x["r"])
            if f is None:
                continue
            (up_r if x["c0"] > f else dn_r).append(x["rng"])
            (up_a if x["c0"] > f else dn_a).append(abs(x["ret"]))
        if len(up_r) >= 5 and len(dn_r) >= 5:
            out(f"| {name} | {len(up_r)} | {len(dn_r)} | {fmt(st.mean(up_r), 2)} | {fmt(st.mean(dn_r), 2)} | {fmt(perm_p(up_r, dn_r), 3)} | "
                f"{fmt(st.mean(up_a), 2)} | {fmt(st.mean(dn_a), 2)} | {fmt(perm_p(up_a, dn_a), 3)} |")
        else:
            out(f"| {name} | {len(up_r)} | {len(dn_r)} | 任一組 < 5 天，不計算 | | | | | |")

    # ---------------- M4
    sec("M4 牆被隔日觸及的比例（對照＝鏡像價位，距離相同方向相反；只看距收盤 ≤3% 的牆）")
    out("鏡像對照為事先登記；**同側基準為看到結果後新增**（樣本期間指數長期上漲，鏡像會有漂移偏差）：同側基準＝以全樣本日的隔日最高/最低相對日t收盤的經驗分布，"
        "算出『同方向、同距離的任意價位』被觸及的機率，再對各牆的距離取平均。它仍不控制波動度叢集（高波動日兩邊都更容易被觸及）。\n")
    ups = sorted(((x["hi"] - x["c0"]) / x["c0"]) for x in rows)
    dns = sorted(((x["c0"] - x["lo"]) / x["c0"]) for x in rows)

    def p_touch(w, c0):
        import bisect
        if w >= c0:
            xx, arr = (w - c0) / c0, ups
        else:
            xx, arr = (c0 - w) / c0, dns
        return 1 - bisect.bisect_left(arr, xx) / len(arr)

    out("| 牆 | n | 牆被觸及 | 鏡像價位被觸及 | 同側基準(事後加) |")
    out("|---|---|---|---|---|")
    for name, tot, flip, cw, pw, mp in SRC:
        for wn, wf in (("買權牆", cw), ("賣權牆", pw)):
            n = hit = mir = 0
            base = 0.0
            for x in rows:
                w = wf(x["r"])
                if w is None or abs(w - x["c0"]) / x["c0"] > 0.03:
                    continue
                n += 1
                hit += x["lo"] <= w <= x["hi"]
                mir += x["lo"] <= 2 * x["c0"] - w <= x["hi"]
                base += p_touch(w, x["c0"])
            if n:
                out(f"| {name} {wn} | {n} | {hit / n * 100:.0f}% | {mir / n * 100:.0f}% | {base / n * 100:.0f}% |")

    # ---------------- M5
    sec("M5 Max Pain 與隔日收盤的距離（指數點）")
    out("| 版本 | n | 平均 |隔日收盤−Max Pain| | Max Pain 比「收盤不動」更接近隔日收盤的比例 |")
    out("|---|---|---|---|")
    for name, tot, flip, cw, pw, mp in SRC:
        ds = [(abs(x["c1"] - mp(x["r"])), abs(x["c1"] - x["c0"])) for x in rows if mp(x["r"]) is not None]
        if ds:
            out(f"| {name} | {len(ds)} | {fmt(st.mean(p_ for p_, _ in ds), 0)} | {sum(1 for p_, q_ in ds if p_ < q_) / len(ds) * 100:.0f}% |")
    out("\n（註：Max Pain 與加權指數的價位基準相同，未扣除期現貨基差。）")

    # ---------------- 最近 10 天
    sec("最近 10 個交易日並列（指數點；v1 為官方 VIX 版，無官方 VIX 的日子以代理版括號標示）")
    out("| 日期 | 收盤 | VIX(官方/代理) | v1 標準Flip | v2 Flip | v1 買牆 | v2 買牆(淨) | v1 賣牆 | v2 賣牆(淨) | v1 MaxPain | v2 MaxPain | v1 總GEX | v2 總GEX |")
    out("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for d in sorted(days)[-10:]:
        r = days[d]
        v1 = r.get("v1") or r.get("v1_proxy") or {}
        tag = "" if r.get("v1") else "*"
        v2 = r["v2"]
        out(f"| {d} | {fmt(r.get('index_close'), 0)} | {fmt(r.get('vix'), 2)}/{fmt(r.get('vix_proxy'), 2)} | {fmt(v1.get('gamma_flip_standard'), 0)}{tag} | {fmt(v2.get('flip'), 0)} | "
            f"{fmt(v1.get('call_wall'), 0)}{tag} | {fmt(v2.get('call_wall_net'), 0)} | {fmt(v1.get('put_wall'), 0)}{tag} | {fmt(v2.get('put_wall_net'), 0)} | "
            f"{fmt(v1.get('max_pain'), 0)}{tag} | {fmt(v2.get('max_pain_all'), 0)} | {fmt(v1.get('total_gex_per1pct'), 2)}{tag} | {fmt(v2.get('total_gex'), 2)} |")
    out("\n（* ＝ 該日 v1 以代理 VIX 計算）")

    txt = "\n".join(L) + "\n"
    print(txt)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    main()
