"""紅線與風控檢查器（規格第8節）。全部由程式強制，AI 無法繞過。回傳違規字串列表；空列表＝通過。
ctx（由呼叫端提供，缺資料就是缺資料，不補假值）：
  now(epoch秒), today(date), spot(台指期現價), iv(百分比數字，如 15.2), surge_pts(近期有號急拉急殺點數，None=無資料),
  exhaustion_ok(15M/30M 九轉竭盡或均線走平，True/False), missing(缺漏資料名稱列表，由資料層填)"""
from decision import DIRECTIONS
from expiry import dte, is_weekly, parse_code
from state import side_margin

OPENING = ("open", "place_ladder", "adjust")


def _distance_floor(iv, cfg):
    for tier in cfg["risk"]["iv_cushion"]:
        if iv > tier["iv_gt"]:
            return tier["min_distance_pts"]
    return cfg["risk"]["iv_cushion"][-1]["min_distance_pts"]


def structure_errors(structure, legs):
    """腿和宣稱的結構要對得上（防止把裸賣包裝成價差）。"""
    n = len(legs)
    sells = [lg for lg in legs if lg["side"] == "sell"]
    buys = [lg for lg in legs if lg["side"] == "buy"]
    if structure == "bull_put_spread":
        ok = n == 2 and all(lg["cp"] == "P" for lg in legs) and sells[0]["strike"] > buys[0]["strike"] and sells[0]["lots"] == buys[0]["lots"] if len(sells) == len(buys) == 1 else False
    elif structure == "bear_call_spread":
        ok = n == 2 and all(lg["cp"] == "C" for lg in legs) and sells[0]["strike"] < buys[0]["strike"] and sells[0]["lots"] == buys[0]["lots"] if len(sells) == len(buys) == 1 else False
    elif structure == "iron_condor":
        ok = n == 4 and len(sells) == len(buys) == 2 and not naked_shorts(legs)
        ok = ok and {lg["cp"] for lg in sells} == {"C", "P"}
    elif structure == "butterfly":
        ok = n == 3 and len({lg["cp"] for lg in legs}) == 1 and not naked_shorts(legs) and len(sells) == 1 and sells[0]["lots"] == sum(b["lots"] for b in buys)
    elif structure in ("long_call", "long_put", "single_leg"):
        ok = n == 1 and legs[0]["side"] == "buy" and (structure != "long_call" or legs[0]["cp"] == "C") and (structure != "long_put" or legs[0]["cp"] == "P")
    else:
        ok = False
    return [] if ok else [f"legs 與 structure={structure} 不符（或含沒有買腳保護的賣腳）"]


def naked_shorts(legs):
    """有沒有賣腳沒被『更價外』的買腳保護（Call 的買腳要在更高履約價，Put 的買腳要更低）。回傳未保護的口數。"""
    uncovered = 0
    for cp in ("C", "P"):
        shorts = sorted([[lg["strike"], lg["lots"]] for lg in legs if lg["cp"] == cp and lg["side"] == "sell"],
                        key=lambda x: -x[0] if cp == "C" else x[0])      # 最難被保護的先配
        longs = [[lg["strike"], lg["lots"]] for lg in legs if lg["cp"] == cp and lg["side"] == "buy"]
        for s, need in shorts:
            for lo in longs:
                if need and lo[1] and ((lo[0] > s) if cp == "C" else (lo[0] < s)):
                    take = min(need, lo[1])
                    need -= take
                    lo[1] -= take
            uncovered += need
    return uncovered


def _sell_distance_errors(strike, cp, spot, floor_pts):
    dist = (spot - strike) if cp == "P" else (strike - spot)      # 價外為正
    if dist < floor_pts:
        side = "價內或太貼近現價" if dist < 0 else f"距離現價只有 {dist:.0f} 點"
        return [f"IV 分區氣墊：{strike}{cp} 賣腳{side}，目前 IV 要求至少 {floor_pts} 點價外"]
    return []


def ladder_worst_loss(decision, cfg):
    """某方向：整套階梯全部成交的最壞虧損(元)，含手續費與期交稅粗估。回傳 {direction: (loss, lots)}。"""
    m = cfg["multiplier"]
    out = {}
    for s in decision["side_sets"]:
        loss, lots = 0.0, 0
        for r in s["rungs"]:
            width = abs(r["short_strike"] - r["long_strike"])
            fee = r["lots"] * 2 * cfg["fees"]["fee_per_lot_per_side"]
            loss += r["lots"] * max(0.0, width - r["min_credit_pts"]) * m + fee
            lots += r["lots"]
        out[s["direction"]] = (loss, lots)
    return out


def check(decision, ctx, state):
    cfg = state.cfg
    r = cfg["risk"]
    act = decision["action"]
    v = []
    if act in OPENING:
        miss = ctx.get("missing") or []
        miss = list(miss) + [n for n, k in (("現價", "spot"), ("IV", "iv")) if ctx.get(k) is None]
        if miss:
            return [f"無決策：缺 {'、'.join(miss)} 資料或未通過新鮮度檢查（不補假資料）"]
        if state.dd_lock == "halted":
            v.append(f"帳戶自高點回撤 ≥ {r['drawdown_halt_pct']}%，已全部停機，需使用者檢討並同意才恢復")
        if state.capital is None:
            v.append("帳戶尚未建立")
        equity = state.equity()
        pnl = state.day_pnl(ctx["today"].isoformat())
        if pnl <= -r["daily_loss_stop_pct"] / 100 * state.capital:
            v.append(f"單日虧損已達 {r['daily_loss_stop_pct']}%，當日停止開新倉")
        # 暴衝／急殺不追價（紅線3）
        surge = ctx.get("surge_pts")
        if surge is not None and abs(surge) >= r["surge_block_pts"] and not ctx.get("exhaustion_ok"):
            v.append(f"紅線：盤中急{'拉' if surge > 0 else '殺'} {abs(surge):.0f} 點，且未見 15M/30M 九轉竭盡或均線走平，禁止新開倉/新掛階梯（不追價）")
        code = decision.get("expiry", {}).get("code")
        stage_ok = r["allowed_structures_by_stage"][r["stage"]]
        if code and code not in state.active_expiries() and len(state.active_expiries()) >= r["max_ladder_sets"]:
            v.append(f"同時存在的到期日已達上限 {r['max_ladder_sets']} 個")
        if act in ("open", "adjust"):
            if decision["structure"] not in stage_ok:
                v.append(f"策略 {decision['structure']} 目前階段 {r['stage']} 尚未開放" + ("（掩護賣Call需先支援期貨腿）" if decision["structure"] == "covered_call" else ""))
            v += structure_errors(decision["structure"], decision["legs"]) if decision["structure"] != "covered_call" else []
            if naked_shorts(decision["legs"]):
                v.append("禁止裸賣：賣腳沒有被更價外的買腳保護（規格6.2）")
            if code and decision["structure"] in ("long_call", "long_put", "single_leg") and dte(code, ctx["today"]) < r["naked_buy_min_dte"]:
                v.append(f"紅線：DTE {dte(code, ctx['today'])} < {r['naked_buy_min_dte']} 天，禁止單獨買進價外裸 Call/Put")
            if ctx.get("iv") is not None and ctx.get("spot") is not None:
                floor = _distance_floor(ctx["iv"], cfg)
                for lg in decision["legs"]:
                    if lg["side"] == "sell":
                        v += _sell_distance_errors(lg["strike"], lg["cp"], ctx["spot"], floor)
        if act == "place_ladder":
            floor = _distance_floor(ctx["iv"], cfg)
            cap = r["ladder_max_lots_per_side"] // (2 if state.dd_lock == "reduced" else 1)
            worst = ladder_worst_loss(decision, cfg)
            both = 0.0
            for s in decision["side_sets"]:
                cp, _ = DIRECTIONS[s["direction"]]
                ex_loss, ex_lots = state.side_exposure(code, cp)
                rest = [o for o in state.resting(code) if o["cp"] == cp]
                rest_loss = sum(o["remaining"] * max(0.0, abs(o["short_strike"] - o["long_strike"]) - o["min_credit_pts"]) * cfg["multiplier"] for o in rest)
                loss = worst[s["direction"]][0] + ex_loss + rest_loss
                lots = worst[s["direction"]][1] + ex_lots + sum(o["remaining"] for o in rest)
                both += loss
                if lots > cap:
                    v.append(f"{s['direction']} 階梯總口數 {lots} 超過單邊上限 {cap} 組（含已成交與掛單中；放大須使用者同意）")
                lim = r["ladder_one_side_max_loss_pct"] / 100 * equity
                if loss > lim:
                    v.append(f"{s['direction']} 階梯全部成交的最壞虧損約 {loss:,.0f} 元 > 單方向上限 {lim:,.0f} 元（{r['ladder_one_side_max_loss_pct']}%）")
                for rg in s["rungs"]:
                    v += _sell_distance_errors(rg["short_strike"], cp, ctx["spot"], floor)
            lim2 = r["ladder_both_sides_max_loss_pct"] / 100 * equity
            if len(decision["side_sets"]) > 1 and both > lim2:
                v.append(f"多空雙邊同時全部成交的最壞虧損約 {both:,.0f} 元 > 雙邊上限 {lim2:,.0f} 元（{r['ladder_both_sides_max_loss_pct']}%）")
    elif act == "close":
        g = state.groups.get(decision.get("group_id"))
        if g is None:
            v.append("找不到這個 group_id 的未平倉組合")
        if "legs" in decision and g is not None and is_weekly(g["expiry"]):
            v.append("紅線：週選價差禁止拆單，只能整組平倉、轉倉或到期結算")
    return v
