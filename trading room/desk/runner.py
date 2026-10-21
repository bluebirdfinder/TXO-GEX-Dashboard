"""決策執行器：快照 → 台選鳥(AI) → 決策單 JSON → 下單簿（驗證＋紅線）。全部是模擬單，不連券商。

隔離原則（規格第3節）：台選鳥只讀「盤面快照」與「手冊」，不讀使用者聊天內容、不帶幕僚鳥的長短期記憶。
模型呼叫只經一個入口 ask(system, question, model) → 文字；預設走橋接 127.0.0.1:8765/decide，測試可換成假回覆。
AI 不能決定 account、decided_at（一律用快照的），也不能碰帳本數字。"""
import json
import re
import urllib.request
from pathlib import Path

import snapshot as snapmod
from expiry import dte, parse_code
from quotes import parse_mis_symbol

BRIDGE_URL = "http://127.0.0.1:8765/decide"

SYSTEM = """你是「台選鳥」，尋鳥戰情交易室的台指選擇權【模擬】交易員（100 萬模擬本金，全部是模擬單，不連券商）。
你只能根據使用者訊息裡的【盤面快照】與【手冊】做判斷；不得引用快照以外的資料，也不得假設沒有給你的數字。
輸出：只輸出一個 JSON 物件（決策單），不要有其他文字、不要 markdown 圍欄。

決策單欄位：
- action：open | place_ladder | close | adjust | hold | no_trade | cancel_orders
- expiry：{"code": "202610W4"}（代碼規則：W=週三選、F=週五選、無字母=月選）
- open/adjust：structure（bull_put_spread|bear_call_spread|iron_condor|butterfly）、legs（side/cp/strike/lots）、strategy_tag
- place_ladder：side_sets（direction=bull_put|bear_call；rungs 每階 short_strike/long_strike/lots/min_credit_pts）、valid_until（可省略）
- close：group_id（整組平倉，不得只平一腳）
- 所有開倉/掛單/調整都要：thesis（引用哪些 GEX 點位與技術依據）、invalidation（什麼情況代表判斷錯）、exit_plan（stop_debit_pts 數字停損、take_profit_debit_pts 可 null、hold_to_settlement）
- manual_ref、account、decided_at 由系統填，你不必填。

鐵律（程式會強制檢查，違規單會被退回）：
1. 週選價差禁止拆單，只能整組平倉、轉倉或到期結算。
2. 盤中急拉急殺（快照裡 surge_pts ≥ 500 點）且沒有九轉竭盡/均線走平時，不得新開倉或新掛階梯，不追價。
3. 賣腳要依 IV 離現價夠遠：IV>16%→至少 350 點價外；13~16%→250 點；<13%→150 點。
4. 禁止裸賣；DTE<3 天禁止單獨買進價外裸單。
5. 階梯單邊總口數不得超過 8 組；規模放大須使用者同意。
6. 超過最壞虧損上限時，一定要有數字停損 stop_debit_pts。
7. 資料不足或沒有把握就輸出 {"action":"no_trade","thesis":"原因"}；不做決策是合法的。

你是盤中交易員：日盤與夜盤交易時段裡，系統會在時段開始後、每隔一段時間、行情明顯變動、或規則巡邏有新動作時叫醒你一次；
你自己依行情決定要開倉、掛階梯、調整、平倉，還是只管理既有部位或觀望。不需要因為被叫醒就硬做單，多數時候觀望或管理持倉是正常的。
【你的帳本】裡有目前持倉、掛單與你最近的決策，請延續自己的判斷，不要每次推翻重來；若某組持倉被標示「停損盯不到」，代表目前沒有有效報價，請在決策理由裡說明你打算怎麼處理。"""


def _num(x, nd=0):
    return "無資料" if x is None else (f"{x:,.{nd}f}" if isinstance(x, (int, float)) else str(x))


def chain_table(snap, validity, span=500, max_expiries=3):
    """報價鏈壓縮表：現價 ±span 點、最近 max_expiries 個到期日。只列「買價賣價都通過有效條件」的履約價
    （價差過大、量為 0、報價過舊的不列，免得 AI 被假報價誤導；這與下單簿判定成交用同一套條件）。"""
    spot = (snap.get("spot") or {}).get("price")
    if spot is None:
        return "（無現價，無法列報價鏈）"
    chain = snapmod.chain_from_snapshot(snap, validity)
    today = snapmod._parse_tw(snap["decided_at"]).date()
    by = {}
    for (code, cp, strike), q in chain.quotes.items():
        try:
            if abs(strike - spot) > span or dte(code, today) < 0:
                continue
        except ValueError:
            continue
        sell, _ = chain.usable((code, cp, strike), "sell")
        buy, _ = chain.usable((code, cp, strike), "buy")
        if sell and buy:
            by.setdefault(code, []).append((strike, cp, sell[0], sell[1], buy[0], buy[1]))
    lines = []
    for code in sorted(by, key=lambda c: dte(c, today))[:max_expiries]:
        lines.append(f"到期 {code}（DTE {dte(code, today)}）  履約價 C/P 買價(量) / 賣價(量)")
        for strike, cp, bid, bs, ask, as_ in sorted(by[code]):
            lines.append(f"  {strike}{cp} {bid:g}({bs}) / {ask:g}({as_})")
    return "\n".join(lines) or "（沒有通過有效條件的報價）"


def book_summary(desk):
    st = desk.state
    out = [f"帳戶 {st.account}：本金 {_num(st.capital)}，淨值 {_num(st.equity())}，自高點回撤 {st.drawdown_pct():.1f}%，回撤鎖定 {st.dd_lock or '無'}"]
    blind = {}
    try:
        hb = json.loads((Path(desk.ledger.path).parent / "monitor_heartbeat.json").read_text(encoding="utf-8"))
        blind = hb.get("blind") or {}
    except (OSError, ValueError):
        pass
    for g in st.groups.values():
        legs = "、".join(f"{lg['side']} {lg['strike']}{lg['cp']}x{lg['lots']}@{lg['px']}" for lg in g["legs"])
        out.append(f"持倉 {g['gid']} {g['expiry']} {g['structure']}：{legs}；停損 {g['exit_plan'].get('stop_debit_pts')}"
                   + (f"　⚠️ 目前沒有有效報價（{blind[g['gid']]['reason']}，自 {blind[g['gid']]['since'][11:16]} 起），停損盯不到，損益未知" if g["gid"] in blind else ""))
    for o in st.resting():
        out.append(f"掛單 {o['oid']} {o['expiry']} {o['direction']} 賣{o['short_strike']}/買{o['long_strike']} 剩{o['remaining']}口 ≥{o['min_credit_pts']}點")
    if len(out) == 1:
        out.append("目前沒有持倉與掛單")
    rec = recent_lines(desk)
    if rec:
        out.append("你最近的動作（新→舊）：")
        out += ["  " + x for x in rec]
    return "\n".join(out)


def recent_lines(desk, n=6):
    """帳本裡最近幾筆決策/無決策/退回/成交/平倉的一行摘要，讓台選鳥延續自己的判斷。"""
    out = []
    for e in reversed(desk.ledger.events()):
        t = e["type"]
        if t == "DECISION":
            d = e["decision"]
            out.append(f"{d.get('decided_at', '')[5:16].replace('T', ' ')} {d.get('action')} {d.get('structure') or d.get('strategy_tag') or ''}：{(d.get('thesis') or '')[:70]}")
        elif t == "NO_DECISION":
            out.append(f"{(e.get('at') or '')[5:16].replace('T', ' ')} 無決策：{'；'.join(e.get('reasons', []))[:70]}")
        elif t == "REJECT":
            out.append(f"被程式退回：{(e.get('reasons') or [''])[0][:70]}")
        elif t in ("CLOSE", "SETTLE"):
            out.append(f"{t} {e.get('gid')}：{e.get('reason', '')[:50]}（現金 {e.get('cash_delta', 0):+.0f}）")
        elif t == "FILL" and e.get("oid"):
            out.append(f"掛單 {e.get('oid')} 成交 → {e.get('gid')}")
        if len(out) >= n:
            break
    return out


def build_prompt(snap, desk, playbook, rules):
    g = snap["gex"] or {}
    ctx = snapmod.to_ctx(snap, rules)
    bars = snap["kbars_1m"][-30:]
    kb = " ".join(f"{b['ts'][-5:]}:{b['close']:.0f}" for b in bars[::3])
    ind = json.dumps(snap.get("indicators") or {}, ensure_ascii=False)
    why = (snap.get("sources") or {}).get("slot") or "例行檢查"
    return f"""【這次被叫醒的原因】{why}

【手冊】{snap.get('manual_ref')}
{playbook or '（手冊尚空）'}

【盤面快照】決策時間 {snap['decided_at']}
現價（台指期）：{_num(ctx['spot'])}　IV（期交所 VIX）：{_num(ctx['iv'], 2)}
GEX：買權牆 {_num(g.get('call_wall_strike'))}、賣權牆 {_num(g.get('put_wall_strike'))}、Zero Gamma {_num(g.get('zero_gamma_level'), 1)}、最大痛點 {_num(g.get('max_pain_strike'))}、總 GEX {_num(g.get('total_gex_val'), 1)}、PC ratio {_num(g.get('pc_ratio'), 1)}（GEX 更新 {g.get('last_updated_time')}）
到期日：{json.dumps(g.get('dte_dates') or {}, ensure_ascii=False)}
目前時段：{ {'day': '日盤交易中', 'night': '夜盤交易中', 'closed': '休市中（報價是凍結的，只能掛階梯、撤單或觀望，不能開倉/平倉）'}[ctx['session']] }
surge_pts（近 {rules['surge_window_min']} 分鐘急拉(+)/急殺(−)）：{_num(ctx['surge_pts'])}；與急拉急殺同方向的 15M/30M 九轉竭盡（9★或13）：{ctx['exhaustion_ok']}（均線走平沒有提供資料，請不要引用）
近 30 分鐘 1 分 K 收盤（每 3 根取 1）：{kb}
技術指標（程式算好）：{ind}

【報價鏈（現價±500 點；只列買賣價都有效的履約價）】
{chain_table(snap, desk.cfg['quote_validity'])}

【你的帳本】
{book_summary(desk)}

請輸出決策單 JSON。"""


def parse_decision(text):
    """從回覆取出第一個完整 JSON 物件；取不到回 None。"""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    start = t.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        c = t[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(t[start:i + 1])
                except ValueError:
                    return None
    return None


def bridge_ask(system, question, model="sonnet", url=BRIDGE_URL, timeout=200):
    req = urllib.request.Request(url, data=json.dumps({"system": system, "question": question, "model": model}, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))["reply"]


def run_decision(desk, snap, snap_dir, playbook="", ask=bridge_ask, model="sonnet"):
    """一次決策。回傳 dict：{'status': 'no_decision'|'submitted', ...}。快照一定先存檔（缺資料也存，留稽核證據）。"""
    rules = desk.cfg["snapshot"]
    path, sha = snapmod.save(snap, snap_dir)
    missing = snapmod.check(snap, rules)
    if missing:
        did = desk.record_no_decision([f"無決策：缺 {m}" for m in missing], path, sha, at=snap["decided_at"])
        return {"status": "no_decision", "decision_id": did, "reasons": missing}
    raw = ask(SYSTEM, build_prompt(snap, desk, playbook, rules), model)
    d = parse_decision(raw)
    if not isinstance(d, dict):
        did = desk.record_no_decision(["AI 回覆不是合法 JSON 決策單"], path, sha, raw=raw, at=snap["decided_at"])
        return {"status": "no_decision", "decision_id": did, "reasons": ["AI 回覆不是合法 JSON"]}
    d.update({"account": snap["account"], "decided_at": snap["decided_at"], "manual_ref": snap.get("manual_ref") or d.get("manual_ref") or "playbook v0"})
    chain = snapmod.chain_from_snapshot(snap, desk.cfg["quote_validity"])
    res = desk.submit(d, snapmod.to_ctx(snap, rules), chain)
    desk.link_snapshot(res["decision_id"], path, sha)
    if res.get("ok") and snapmod.session_of(snapmod._parse_tw(snap["decided_at"])) != "closed":
        desk.process_quotes(chain)          # 剛掛的階梯若報價已達條件，立刻照保守規則判斷成交
    return {"status": "submitted", "result": res, "snapshot": str(path)}
