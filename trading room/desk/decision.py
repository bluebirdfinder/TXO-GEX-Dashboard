"""決策單格式（規格第6節、6.1）。AI 只輸出 JSON 決策單，不接受純文字下單；這裡只驗格式，不判斷風控。
exit_plan 為了讓「停損停利由程式盯盤」能執行，要求數字欄位 stop_debit_pts / take_profit_debit_pts
（平倉成本點數：>=停損值觸發停損；<=停利值觸發停利）；規格範例是純文字，這是補充，需使用者確認。"""
import re
from datetime import datetime

from expiry import parse_code

ACTIONS = {"open", "hold", "close", "adjust", "no_trade", "place_ladder", "cancel_orders"}
STRUCTURES = {"bull_put_spread", "bear_call_spread", "iron_condor", "butterfly", "single_leg", "long_call", "long_put",
              "covered_call"}
DIRECTIONS = {"bull_put": ("P", -1), "bear_call": ("C", +1)}   # (cp, 長腳相對賣腳的方向)
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+08:00$")


def _err(errors, msg):
    errors.append(msg)


def validate(d):
    """回傳錯誤字串列表；空列表＝格式合法。"""
    e = []
    if not isinstance(d, dict):
        return ["決策單必須是 JSON 物件"]
    if d.get("account") not in ("T0", "T1"):
        _err(e, "account 必須是 T0 或 T1")
    if not isinstance(d.get("decided_at"), str) or not _ISO.match(d["decided_at"]):
        _err(e, "decided_at 必須是台灣時區 ISO 格式（結尾 +08:00）")
    act = d.get("action")
    if act not in ACTIONS:
        _err(e, f"action 必須是 {sorted(ACTIONS)} 之一")
        return e
    if not d.get("manual_ref"):
        _err(e, "manual_ref（使用的手冊版本）必填")
    if act in ("open", "place_ladder", "adjust") and not (d.get("thesis") and d.get("invalidation")):
        _err(e, "thesis 與 invalidation 必填（為什麼、什麼情況代表判斷錯）")
    if act in ("open", "place_ladder", "adjust"):
        try:
            parse_code(d.get("expiry", {}).get("code"))
        except (ValueError, AttributeError) as ex:
            _err(e, f"expiry.code 不合法: {ex}")
    if act in ("open", "adjust"):
        if d.get("structure") not in STRUCTURES:
            _err(e, f"structure 必須是 {sorted(STRUCTURES)} 之一")
        if not d.get("strategy_tag"):
            _err(e, "strategy_tag 必填（每種策略各自統計）")
        _validate_legs(d.get("legs"), e)
        _validate_exit_plan(d.get("exit_plan"), e)
    if act == "place_ladder":
        _validate_ladder(d, e)
        _validate_exit_plan(d.get("exit_plan"), e)
    if act == "close":
        if not d.get("group_id"):
            _err(e, "close 必須指定 group_id（整組價差平倉，不接受只指定單腳）")
        if "legs" in d:
            _err(e, "紅線：close 不接受 legs——價差禁止拆單，一律整組平倉（週選尤其不可只平賣腳留買腳裸露）")
    return e


def _validate_legs(legs, e):
    if not isinstance(legs, list) or not legs:
        _err(e, "legs 必須是非空陣列")
        return
    for i, lg in enumerate(legs):
        if lg.get("side") not in ("buy", "sell"):
            _err(e, f"legs[{i}].side 必須是 buy/sell")
        if lg.get("cp") not in ("C", "P"):
            _err(e, f"legs[{i}].cp 必須是 C/P")
        if not isinstance(lg.get("strike"), int) or lg["strike"] <= 0:
            _err(e, f"legs[{i}].strike 必須是正整數")
        if not isinstance(lg.get("lots"), int) or lg["lots"] <= 0:
            _err(e, f"legs[{i}].lots 必須是正整數")


def _validate_exit_plan(p, e):
    if not isinstance(p, dict):
        _err(e, "exit_plan 必填")
        return
    for k in ("stop_debit_pts", "take_profit_debit_pts"):
        v = p.get(k)
        if v is not None and not isinstance(v, (int, float)):
            _err(e, f"exit_plan.{k} 必須是數字或 null")
    if not p.get("hold_to_settlement") and p.get("stop_debit_pts") is None:
        _err(e, "exit_plan 必須有數字停損 stop_debit_pts，或明確 hold_to_settlement=true")


def _validate_ladder(d, e):
    sets = d.get("side_sets")
    if not isinstance(sets, list) or not sets:
        _err(e, "place_ladder 需要 side_sets")
        return
    seen = set()
    for i, s in enumerate(sets):
        if s.get("direction") not in DIRECTIONS:
            _err(e, f"side_sets[{i}].direction 必須是 bull_put 或 bear_call")
            continue
        if s["direction"] in seen:
            _err(e, f"side_sets 裡 {s['direction']} 重複")
        seen.add(s["direction"])
        cp, sign = DIRECTIONS[s["direction"]]
        rungs = s.get("rungs")
        if not isinstance(rungs, list) or not rungs:
            _err(e, f"side_sets[{i}].rungs 必須是非空陣列")
            continue
        for j, r in enumerate(rungs):
            ss, ls = r.get("short_strike"), r.get("long_strike")
            if not (isinstance(ss, int) and isinstance(ls, int)):
                _err(e, f"side_sets[{i}].rungs[{j}] 履約價必須是整數")
            elif (ls - ss) * sign <= 0:
                _err(e, f"side_sets[{i}].rungs[{j}] 買腳必須在賣腳的{'下方' if sign < 0 else '上方'}（方向 {s['direction']}）")
            if not isinstance(r.get("lots"), int) or r["lots"] <= 0:
                _err(e, f"side_sets[{i}].rungs[{j}].lots 必須是正整數")
            if not isinstance(r.get("min_credit_pts"), (int, float)) or r["min_credit_pts"] <= 0:
                _err(e, f"side_sets[{i}].rungs[{j}].min_credit_pts 必須是正數")
    if "valid_until" in d and not (isinstance(d["valid_until"], str) and _ISO.match(d["valid_until"])):
        _err(e, "valid_until 必須是 +08:00 的 ISO 時間")


def ts_of(iso):
    return datetime.fromisoformat(iso).timestamp()
