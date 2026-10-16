"""
gex_levels_sheet.py — 「GEX 點位說明表」：用期交所官方未平倉＋教科書定義重算所有點位，每個點位標示定義、範圍與在現價的哪一側。

教科書定義（本表採用）：
  Gamma Exposure(GEX)  = OI × Γ(Black-76) × F² × 50 × 0.01 / 1e8（億 NT$／指數每動 1%）；買權 +、賣權 −（造市商持買權、賣賣權的簡化假設）
  Call Wall            = 現價「上方」(≥現價) 買權側 GEX 最大的履約價（壓力）；另列以 OI 最大者
  Put Wall             = 現價「下方」(≤現價) 賣權側 |GEX| 最大的履約價（支撐）；另列以 OI 最大者
  淨 GEX 牆            = 各履約價 (Call+Put) 淨 GEX 的最大／最小（老墨頁面的寫法；可能落在現價任一側）— 僅供對照
  Gamma Flip(Zero Γ)   = 價位掃描（所有到期的期貨價同比例平移、IV 固定）總 GEX 變號處，取離現價最近者
  Max Pain             = 使所有未平倉選擇權到期時「內含價值總和」最小的履約價；教科書以「單一到期」為準，另列所有還活著合約合併
所有資料來自期交所官方檔；已結算（到期日 ≤ 資料日）的合約一律排除。模型輸出，不是預測；牆與翻轉點不代表價格會停留或反轉。
用法：python scripts/gex_levels_sheet.py [--date YYYY-MM-DD] [--spot 加權收盤] [--html out.html]
"""
import argparse
import datetime
import html
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gex_v2 as g  # noqa: E402


def oi_by_strike(day_data, day, codes=None):
    C, P = defaultdict(int), defaultdict(int)
    for code, e in day_data.items():
        if e["expiry"] <= day or (codes is not None and code not in codes):
            continue
        for (k, rt), x in e["q"].items():
            (C if rt == "C" else P)[k] += x["oi"]
    return C, P


def max_pain(C, P):
    ks = sorted(set(C) | set(P))
    if not ks:
        return None, {}
    loss = {S: sum(max(0, S - k) * C.get(k, 0) + max(0, k - S) * P.get(k, 0) for k in ks) for S in ks}
    best = min(ks, key=loss.get)
    return best, loss


def flat_band(loss, best, pct=0.02):
    """額外損失不超過『最小損失本身 × pct』的連續區間——說明這個最大痛點有多平坦。"""
    base = loss[best]
    scale = base if base > 0 else (sum(loss.values()) / len(loss) if loss else 0)   # 最小損失為 0 的極端帳本改用平均損失當尺度
    ks = sorted(loss)
    lo = hi = best
    for k in reversed([x for x in ks if x < best]):
        if loss[k] - base <= scale * pct:
            lo = k
        else:
            break
    for k in [x for x in ks if x > best]:
        if loss[k] - base <= scale * pct:
            hi = k
        else:
            break
    return lo, hi


def side(k, spot):
    return "現價上方" if k > spot else ("現價下方" if k < spot else "現價")


def build(day_iso, spot=None):
    day = datetime.date.fromisoformat(day_iso)
    parsed = g.parse_opt(g.fetch_opt_text(day - datetime.timedelta(days=12), day + datetime.timedelta(days=1)))
    if day_iso not in parsed:
        raise SystemExit(f"{day_iso}: 期交所官方檔沒有這天的資料（尚未公布或非交易日）")
    dd = parsed[day_iso]
    lv = g.compute_day(day_iso, dd, spot=spot)
    if lv is None:
        raise SystemExit("無法計算（資料不足）")
    S0 = lv["S0"]
    ps = lv["per_strike"]
    live = {c: e for c, e in dd.items() if e["expiry"] > day}
    out = {"date": day_iso, "S0": S0, "F_front": lv["F_front"], "total_gex": lv["total_gex"], "flip": lv["flip"], "flip_all": lv["flip_all"]}

    above = {k: v for k, v in ps.items() if k >= S0}
    below = {k: v for k, v in ps.items() if k <= S0}
    cw = max(above, key=lambda k: above[k][0]) if above else None
    pw = min(below, key=lambda k: below[k][1]) if below else None
    out["call_wall"] = (cw, above[cw][0] if cw else None)
    out["put_wall"] = (pw, below[pw][1] if pw else None)
    C, P = oi_by_strike(dd, day)
    ca = {k: v for k, v in C.items() if k >= S0}
    pb = {k: v for k, v in P.items() if k <= S0}
    out["call_wall_oi"] = (max(ca, key=ca.get), max(ca.values())) if ca else (None, None)
    out["put_wall_oi"] = (max(pb, key=pb.get), max(pb.values())) if pb else (None, None)
    out["net_call_wall"] = (lv["call_wall_net"], lv["call_wall_net_gex"])
    out["net_put_wall"] = (lv["put_wall_net"], lv["put_wall_net_gex"])
    out["gex_peak_call"] = (lv["call_wall_side"], ps[int(lv["call_wall_side"])][0] if int(lv["call_wall_side"]) in ps else None)
    out["gex_peak_put"] = (lv["put_wall_side"], ps[int(lv["put_wall_side"])][1] if int(lv["put_wall_side"]) in ps else None)
    out["top_call"] = sorted(((k, v[0]) for k, v in ps.items()), key=lambda x: -x[1])[:5]
    out["top_put"] = sorted(((k, v[1]) for k, v in ps.items()), key=lambda x: x[1])[:5]

    mp_all, loss_all = max_pain(C, P)
    out["max_pain_all"] = (mp_all, flat_band(loss_all, mp_all))
    rows = []
    for code, e in sorted(live.items(), key=lambda kv: kv[1]["expiry"]):
        c, p = oi_by_strike(dd, day, {code})
        m, ls = max_pain(c, p)
        if m is None:
            continue
        rows.append({"code": code.strip(), "expiry": e["expiry"].isoformat(), "call_oi": sum(c.values()), "put_oi": sum(p.values()),
                     "max_pain": m, "band": flat_band(ls, m)})
    out["per_expiry"] = rows
    near = sorted(live.values(), key=lambda e: e["expiry"])[:4]
    near_codes = {c for c, e in live.items() if e in near}
    cn, pn = oi_by_strike(dd, day, near_codes)
    mpn, lsn = max_pain(cn, pn)
    out["max_pain_near4"] = (mpn, flat_band(lsn, mpn), sorted(e["expiry"].isoformat() for e in near))
    out["oi_total"] = (sum(C.values()), sum(P.values()))
    out["coverage_iv_pct"] = lv.get("coverage_iv_pct")
    return out


def fmt(x, nd=0):
    return "—" if x is None else (f"{x:,.{nd}f}")


def render_text(o):
    S0 = o["S0"]
    L = []
    L.append(f"GEX 點位說明表  資料日 {o['date']}  加權指數收盤 {S0:,.2f}  近月期貨(F) {o['F_front']:,.1f}  (還活著的合約 Call OI {o['oi_total'][0]:,} / Put OI {o['oi_total'][1]:,})")
    L.append("")
    L.append(f"{'點位':22}{'位置':>9}{'相對現價':>10}   定義與範圍")
    def line(name, k, note, gex=None):
        if k is None:
            L.append(f"{name:22}{'—':>9}{'':>10}   {note}"); return
        d = k - S0
        L.append(f"{name:22}{k:>9,.0f}{d:>+10,.0f}   [{side(k, S0)}] {note}" + (f"  (GEX {gex:+.2f} 億/每1%)" if gex is not None else ""))
    line("Call Wall（教科書）", o["call_wall"][0], "現價上方、買權側 GEX 最大 → 壓力", o["call_wall"][1])
    line("Put Wall（教科書）", o["put_wall"][0], "現價下方、賣權側 |GEX| 最大 → 支撐", o["put_wall"][1])
    line("Call Wall（OI 版）", o["call_wall_oi"][0], f"現價上方、買權 OI 最大（{fmt(o['call_wall_oi'][1])} 口）")
    line("Put Wall（OI 版）", o["put_wall_oi"][0], f"現價下方、賣權 OI 最大（{fmt(o['put_wall_oi'][1])} 口）")
    line("淨 GEX 最大（老墨式）", o["net_call_wall"][0], "各履約價淨 GEX 最大，不限位置", o["net_call_wall"][1])
    line("淨 GEX 最小（老墨式）", o["net_put_wall"][0], "各履約價淨 GEX 最小，不限位置", o["net_put_wall"][1])
    line("Gamma Flip（價位掃描）", o["flip"], f"總 GEX 變號處；總 GEX {o['total_gex']:+.2f} 億/每1%（現價處為{'正' if o['total_gex'] > 0 else '負'} Gamma）")
    mp, (lo, hi) = o["max_pain_all"]
    line("Max Pain（全部還活著）", mp, f"所有還活著的合約合併；平坦區間 {lo:,.0f}～{hi:,.0f}（額外損失≤2%）")
    mp4, (lo4, hi4), exps = o["max_pain_near4"]
    line("Max Pain（近四個到期）", mp4, f"{', '.join(e[5:] for e in exps)}；平坦區間 {lo4:,.0f}～{hi4:,.0f}")
    L.append("")
    L.append("各到期各自的最大痛點（教科書通常看『單一到期』）：")
    for r in o["per_expiry"]:
        L.append(f"  {r['expiry']}  {r['code']:9} Call {r['call_oi']:>7,} Put {r['put_oi']:>7,}   Max Pain {r['max_pain']:>7,.0f}  (平坦區間 {r['band'][0]:,.0f}～{r['band'][1]:,.0f})")
    L.append("")
    L.append("買權側 GEX 前五： " + "  ".join(f"{k:,.0f}({v:+.1f})" for k, v in o["top_call"]))
    L.append("賣權側 GEX 前五： " + "  ".join(f"{k:,.0f}({v:+.1f})" for k, v in o["top_put"]))
    L.append("")
    L.append("提醒：模型輸出，不是預測；牆與翻轉點不代表價格會停留或反轉。買權+／賣權−是造市商持買權、賣賣權的簡化假設，實際倉位看不到。")
    return "\n".join(L)


def render_html(o):
    S0 = o["S0"]
    e = html.escape
    def row(name, k, note, gex=None, hl=False):
        if k is None:
            return f"<tr><td>{e(name)}</td><td>—</td><td></td><td>{e(note)}</td></tr>"
        d = k - S0
        cls = ' class="hl"' if hl else ""
        g_ = f"　<span class='dim'>GEX {gex:+.2f}</span>" if gex is not None else ""
        return f"<tr{cls}><td>{e(name)}</td><td class='n'>{k:,.0f}</td><td class='n {'up' if d > 0 else 'dn'}'>{d:+,.0f}</td><td>[{side(k, S0)}] {e(note)}{g_}</td></tr>"
    mp, (lo, hi) = o["max_pain_all"]
    mp4, (lo4, hi4), exps = o["max_pain_near4"]
    rows = [
        row("Call Wall（教科書）", o["call_wall"][0], "現價上方、買權側 GEX 最大 → 壓力", o["call_wall"][1], True),
        row("Put Wall（教科書）", o["put_wall"][0], "現價下方、賣權側 |GEX| 最大 → 支撐", o["put_wall"][1], True),
        row("Call Wall（OI 版）", o["call_wall_oi"][0], f"現價上方、買權 OI 最大（{fmt(o['call_wall_oi'][1])} 口）"),
        row("Put Wall（OI 版）", o["put_wall_oi"][0], f"現價下方、賣權 OI 最大（{fmt(o['put_wall_oi'][1])} 口）"),
        row("淨 GEX 最大（老墨式）", o["net_call_wall"][0], "各履約價淨 GEX 最大，不限位置（對照用）", o["net_call_wall"][1]),
        row("淨 GEX 最小（老墨式）", o["net_put_wall"][0], "各履約價淨 GEX 最小，不限位置（對照用）", o["net_put_wall"][1]),
        row("Gamma Flip（價位掃描）", o["flip"], f"總 GEX 變號處；總 GEX {o['total_gex']:+.2f} 億/每 1%，現價處為{'正' if o['total_gex'] > 0 else '負'} Gamma", None, True),
        row("Max Pain（全部還活著）", mp, f"所有還活著的合約合併；平坦區間 {lo:,.0f}～{hi:,.0f}（額外損失 ≤2%）"),
        row("Max Pain（近四個到期）", mp4, f"{'、'.join(x[5:] for x in exps)}；平坦區間 {lo4:,.0f}～{hi4:,.0f}", None, True),
    ]
    exp_rows = "".join(
        f"<tr><td>{r['expiry']}</td><td>{e(r['code'])}</td><td class='n'>{r['call_oi']:,}</td><td class='n'>{r['put_oi']:,}</td>"
        f"<td class='n'>{r['max_pain']:,.0f}</td><td>{r['band'][0]:,.0f}～{r['band'][1]:,.0f}</td></tr>" for r in o["per_expiry"])
    topc = "、".join(f"{k:,.0f}（{v:+.1f}）" for k, v in o["top_call"])
    topp = "、".join(f"{k:,.0f}（{v:+.1f}）" for k, v in o["top_put"])
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEX 點位說明表 {o['date']}</title>
<style>:root{{--bg:#fff;--fg:#1d1d1f;--mut:#6b7280;--line:#e5e7eb;--hl:#fff8e1;--up:#c0392b;--dn:#1e8449}}
@media(prefers-color-scheme:dark){{:root{{--bg:#161616;--fg:#e8e8e8;--mut:#9aa0a6;--line:#333;--hl:#2b2410;--up:#ff7a70;--dn:#4cd08a}}}}
body{{font:15px/1.7 system-ui,'Microsoft JhengHei',sans-serif;background:var(--bg);color:var(--fg);max-width:980px;margin:20px auto;padding:0 16px}}
table{{border-collapse:collapse;width:100%;margin:10px 0}}td,th{{border:1px solid var(--line);padding:6px 10px;text-align:left}}th{{background:var(--hl)}}
td.n{{text-align:right;font-variant-numeric:tabular-nums}}tr.hl td{{background:var(--hl)}}.up{{color:var(--up)}}.dn{{color:var(--dn)}}.dim{{color:var(--mut)}}
.note{{border-left:4px solid #e0a800;background:var(--hl);padding:8px 12px;margin:12px 0}}h1{{font-size:20px}}h2{{font-size:16px;margin-top:22px}}</style></head><body>
<h1>GEX 點位說明表（教科書定義）— 資料日 {o['date']}</h1>
<p>加權指數收盤 <b>{S0:,.2f}</b>　近月期貨 {o['F_front']:,.1f}　還活著的合約 Call OI {o['oi_total'][0]:,} / Put OI {o['oi_total'][1]:,}　（資料全來自期交所官方檔；已結算合約已排除）</p>
<table><tr><th>點位</th><th>位置</th><th>相對現價</th><th>定義、範圍與所在側</th></tr>{''.join(rows)}</table>
<h2>各到期各自的最大痛點（教科書通常看單一到期）</h2>
<table><tr><th>到期日</th><th>契約</th><th>Call OI</th><th>Put OI</th><th>Max Pain</th><th>平坦區間</th></tr>{exp_rows}</table>
<h2>各履約價 GEX 前五（億 NT$／指數每動 1%）</h2><p>買權側：{topc}</p><p>賣權側：{topp}</p>
<div class="note">模型輸出，不是預測；牆與翻轉點不代表價格會停留或反轉。買權 +／賣權 − 是造市商持買權、賣賣權的簡化假設，實際倉位看不到。Max Pain 的「平坦區間」表示該範圍內額外損失 ≤2%，它是一個區間而不是一條精準的線。本表不構成投資建議。</div>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="資料日 YYYY-MM-DD（預設：官方檔最近一個已公布的交易日）")
    ap.add_argument("--spot", type=float, help="加權指數收盤（預設：自 data/gex_v2_history.json 該日的 index_close，沒有則用近月期貨價）")
    ap.add_argument("--html", help="輸出 HTML 路徑")
    a = ap.parse_args()
    day_iso = a.date
    if not day_iso:
        today = datetime.date.today()
        parsed = g.parse_opt(g.fetch_opt_text(today - datetime.timedelta(days=12), today + datetime.timedelta(days=1)))
        ok = [d for d, dd in parsed.items() if sum(x["oi"] for e in dd.values() for x in e["q"].values()) > 0]
        day_iso = sorted(ok)[-1]
    spot = a.spot
    if spot is None:
        try:
            import json
            h = json.load(open(os.path.join(os.path.dirname(HERE), "data", "gex_v2_history.json"), encoding="utf-8"))
            spot = (h["days"].get(day_iso) or {}).get("index_close")
        except Exception:  # noqa: BLE001
            spot = None
    o = build(day_iso, spot)
    print(render_text(o))
    if a.html:
        with open(a.html, "w", encoding="utf-8") as f:
            f.write(render_html(o))
        print("\nHTML ->", a.html)


if __name__ == "__main__":
    main()
