"""虛擬下單簿。只有這個類別會寫帳本；AI 只能遞交決策單(submit)，不能碰數字。
成交一律保守：賣用買價、買用賣價、扣手續費與期交稅；成交判定在驗證通過前標「近似」。全部是模擬單，不連券商。"""
import json
from datetime import datetime, time as dtime, timedelta
from pathlib import Path

import decision as dec
import risk
from expiry import expiry_date
from ledger import Ledger
from state import State, leg_fees, legs_cash

DEFAULT_CFG = Path(__file__).parent / "desk_config.json"


def load_config(path=DEFAULT_CFG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def default_valid_until(decided_at_iso):
    """預設掛單有效到最近一次收盤：日盤13:45前→當天13:45，之後→隔天05:00（夜盤收盤）。"""
    t = datetime.fromisoformat(decided_at_iso)
    if t.time() < dtime(13, 45):
        return t.replace(hour=13, minute=45, second=0, microsecond=0).timestamp()
    nxt = (t + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
    return nxt.timestamp()


class Desk:
    def __init__(self, ledger_path, account, cfg=None):
        self.cfg = cfg or load_config()
        self.account = account
        self.ledger = Ledger(ledger_path)
        if not any(e["type"] == "ACCOUNT_OPEN" for e in self.ledger.events()):
            self.ledger.append("ACCOUNT_OPEN", account=account, capital=self.cfg["accounts"][account]["capital"], simulated=True)

    @property
    def state(self):
        return State(self.cfg, self.ledger.events())

    def _approx(self):
        return not self.cfg["fill"]["validated"]

    def _next(self, prefix):
        kinds = {"D": ("DECISION", "REJECT"), "G": ("FILL",), "O": ("ORDER",)}[prefix]
        return f"{self.account}-{prefix}{sum(1 for e in self.ledger.events() if e['type'] in kinds) + 1}"

    # ---------------- 遞交決策單 ----------------
    def submit(self, d, ctx, chain=None):
        st = self.state
        did = self._next("D")
        errors = dec.validate(d)
        if not errors and d.get("account") != self.account:
            errors = [f"這本帳本是 {self.account}，決策單帳戶是 {d.get('account')}"]
        if not errors:
            errors = risk.check(d, ctx, st)
        if errors:
            self.ledger.append("REJECT", decision_id=did, decision=d if isinstance(d, dict) else None, reasons=errors)
            return {"ok": False, "decision_id": did, "reasons": errors}
        self.ledger.append("DECISION", decision_id=did, decision=d, manual_ref=d.get("manual_ref"))
        act = d["action"]
        ts = dec.ts_of(d["decided_at"])
        if act in ("hold", "no_trade"):
            self.ledger.append("NO_TRADE", decision_id=did, note=d.get("thesis", ""))
            return {"ok": True, "decision_id": did, "result": "no_action"}
        if act == "cancel_orders":
            n = 0
            for o in st.resting(d.get("expiry", {}).get("code")):
                self.ledger.append("ORDER_END", oid=o["oid"], status="cancelled", reason="決策單撤單", decision_id=did)
                n += 1
            return {"ok": True, "decision_id": did, "result": f"cancelled {n}"}
        if act == "place_ladder":
            return {"ok": True, "decision_id": did, "result": "ladder_placed", "orders": self._place_ladder(d, did, ts)}
        if act == "close":
            return self._close_group(d["group_id"], chain, ts, "決策單平倉", did)
        return self._open(d, did, ctx, chain, ts)       # open / adjust(加腳)

    # ---------------- 階梯掛單 ----------------
    def _place_ladder(self, d, did, ts):
        vu = dec.ts_of(d["valid_until"]) if d.get("valid_until") else default_valid_until(d["decided_at"])
        oids = []
        for s in d["side_sets"]:
            cp = dec.DIRECTIONS[s["direction"]][0]
            for r in s["rungs"]:
                oid = self._next("O")
                self.ledger.append("ORDER", oid=oid, decision_id=did, order={
                    "direction": s["direction"], "expiry": d["expiry"]["code"], "cp": cp,
                    "short_strike": r["short_strike"], "long_strike": r["long_strike"], "lots": r["lots"],
                    "min_credit_pts": r["min_credit_pts"], "valid_until": vu, "strategy_tag": d.get("strategy_tag", "ladder"),
                    "exit_plan": d.get("exit_plan"), "placed_at": ts})
                oids.append(oid)
        return oids

    # ---------------- 直接開倉 ----------------
    def _open(self, d, did, ctx, chain, ts):
        code = d["expiry"]["code"]
        legs, why = [], None
        for lg in d["legs"]:
            key = (code, lg["cp"], lg["strike"])
            px, size, w = chain.leg_price(key, lg["side"]) if chain else (None, 0, "沒有報價鏈")
            if px is None or lg["lots"] > size:
                why = f"{lg['strike']}{lg['cp']} " + (w or f"委託量不足（要 {lg['lots']} 口、只有 {size}）")
                break
            legs.append({**lg, "expiry": code, "px": px})
        if why:
            self.ledger.append("NO_FILL", decision_id=did, reason=f"無有效報價，不成交：{why}")
            return {"ok": True, "decision_id": did, "result": "no_fill", "reason": why}
        return self._fill(did, None, code, d["structure"], d.get("strategy_tag", ""), legs, d.get("exit_plan"), ts, chain.now)

    def _fill(self, did, oid, code, structure, tag, legs, exit_plan, ts, quote_ts, lots=None):
        st = self.state
        fees = sum(leg_fees(lg["px"], lg["lots"], self.cfg) for lg in legs)
        gid = self._next("G")
        trial = {"expiry": code, "legs": legs}
        equity = st.equity()
        used = st.margin_used([trial])
        cap = self.cfg["risk"]["margin_util_max_pct"] / 100 * equity
        if used > cap:
            self.ledger.append("NO_FILL", decision_id=did, oid=oid,
                               reason=f"保證金使用 {used:,.0f} 元 > 上限 {cap:,.0f} 元（{self.cfg['risk']['margin_util_max_pct']}%）")
            return {"ok": True, "decision_id": did, "result": "no_fill", "reason": "margin"}
        cash = legs_cash(legs, self.cfg) - fees
        ev = self.ledger.append("FILL", decision_id=did, oid=oid, gid=gid, expiry=code, structure=structure, strategy_tag=tag,
                                legs=legs, lots=lots if lots is not None else max(lg["lots"] for lg in legs), fees=fees,
                                cash_delta=cash, approx=self._approx(), quote_ts=quote_ts, exit_plan=exit_plan, at=ts)
        return {"ok": True, "decision_id": did, "result": "filled", "gid": gid, "cash_delta": cash, "fees": fees,
                "approx": self._approx(), "seq": ev["seq"]}

    # ---------------- 平倉 ----------------
    def _close_group(self, gid, chain, ts, reason, did=None):
        g = self.state.groups.get(gid)
        if g is None:
            return {"ok": False, "reasons": ["找不到未平倉組合"]}
        cost, why = chain.close_cost([{**lg, "expiry": g["expiry"]} for lg in g["legs"]]) if chain else (None, "沒有報價鏈")
        if cost is None:
            self.ledger.append("NO_FILL", decision_id=did, gid=gid, reason=f"平倉無有效報價：{why}")
            return {"ok": True, "result": "no_fill", "reason": why}
        close_legs = []
        for lg in g["legs"]:
            k = (g["expiry"], lg["cp"], lg["strike"])
            px, _, _ = chain.leg_price(k, "buy" if lg["side"] == "sell" else "sell")
            close_legs.append({"side": "buy" if lg["side"] == "sell" else "sell", "cp": lg["cp"], "strike": lg["strike"], "lots": lg["lots"], "px": px})
        fees = sum(leg_fees(l["px"], l["lots"], self.cfg) for l in close_legs)
        cash = legs_cash(close_legs, self.cfg) - fees
        self.ledger.append("CLOSE", decision_id=did, gid=gid, legs=close_legs, fees=fees, cash_delta=cash, reason=reason, at=ts)
        return {"ok": True, "result": "closed", "gid": gid, "cash_delta": cash, "fees": fees}

    # ---------------- 報價進來：掛單成交、停損停利、掛單過期 ----------------
    def process_quotes(self, chain):
        out = []
        st = self.state
        for o in st.resting():
            if chain.now > o["valid_until"]:
                self.ledger.append("ORDER_END", oid=o["oid"], status="expired", reason="掛單期限已到")
                out.append(("expired", o["oid"]))
                continue
            credit, size, why = chain.spread_credit(o["expiry"], o["cp"], o["short_strike"], o["long_strike"])
            if credit is None or credit < o["min_credit_pts"]:
                continue
            take = min(o["remaining"], size)
            if take <= 0:
                continue
            ss, _, _ = chain.leg_price((o["expiry"], o["cp"], o["short_strike"]), "sell")
            ls, _, _ = chain.leg_price((o["expiry"], o["cp"], o["long_strike"]), "buy")
            legs = [{"side": "sell", "cp": o["cp"], "strike": o["short_strike"], "lots": take, "expiry": o["expiry"], "px": ss},
                    {"side": "buy", "cp": o["cp"], "strike": o["long_strike"], "lots": take, "expiry": o["expiry"], "px": ls}]
            struct = "bull_put_spread" if o["cp"] == "P" else "bear_call_spread"
            r = self._fill(None, o["oid"], o["expiry"], struct, o["strategy_tag"], legs, o.get("exit_plan"),
                           chain.now, chain.now, lots=take)
            out.append(("fill", o["oid"], r.get("result"), take))
            st = self.state
        for g in list(self.state.groups.values()):
            ep = g["exit_plan"] or {}
            if ep.get("hold_to_settlement") and ep.get("stop_debit_pts") is None:
                continue
            cost, _ = chain.close_cost([{**lg, "expiry": g["expiry"]} for lg in g["legs"]])
            if cost is None:
                continue
            base = max((lg["lots"] for lg in g["legs"] if lg["side"] == "sell"), default=1)
            pts = cost / base
            if ep.get("stop_debit_pts") is not None and pts >= ep["stop_debit_pts"]:
                out.append(("stop", g["gid"], self._close_group(g["gid"], chain, chain.now, f"停損觸發（平倉成本 {pts:.1f} 點 ≥ {ep['stop_debit_pts']}）")))
            elif ep.get("take_profit_debit_pts") is not None and pts <= ep["take_profit_debit_pts"]:
                out.append(("take_profit", g["gid"], self._close_group(g["gid"], chain, chain.now, f"停利觸發（平倉成本 {pts:.1f} 點 ≤ {ep['take_profit_debit_pts']}）")))
        return out

    # ---------------- 每日計價 ----------------
    def mark(self, date_str, chain):
        st = self.state
        m = self.cfg["multiplier"]
        group_px, pos_value = {}, 0.0
        for g in st.groups.values():
            px_map, stale = {}, False
            for i, lg in enumerate(g["legs"]):
                key = (g["expiry"], lg["cp"], lg["strike"])
                px, _, _ = chain.leg_price(key, "sell" if lg["side"] == "buy" else "buy")   # 多腳以買價、空腳以賣價清算
                if px is None:
                    px, stale = g["last_px"][i], True          # 沒有效報價就沿用上次價並標記，不憑空估
                px_map[str(i)] = px
                pos_value += (1 if lg["side"] == "buy" else -1) * px * lg["lots"] * m
            group_px[g["gid"]] = {"px": px_map, "stale": stale}
        equity = st.cash + pos_value
        day_start = st.day_start_equity.get(date_str, st.last_equity)
        hw = max(st.high_water, equity)
        dd = 100 * (hw - equity) / hw
        lock = "halted" if dd >= self.cfg["risk"]["drawdown_halt_pct"] else "reduced" if dd >= self.cfg["risk"]["drawdown_halve_pct"] else None
        self.ledger.append("MARK", date=date_str, equity=equity, cash=st.cash, positions_value=pos_value,
                           day_start_equity=day_start, group_px=group_px, dd_lock=lock, drawdown_pct=dd)
        return {"equity": equity, "drawdown_pct": dd, "dd_lock": lock, "stale_groups": [k for k, v in group_px.items() if v["stale"]]}

    # ---------------- 到期結算 ----------------
    def settle(self, expiry, settle_px, today):
        if today < expiry_date(expiry):
            raise ValueError(f"{expiry} 要到 {expiry_date(expiry)} 才能結算，今天是 {today}")
        out = []
        for o in self.state.resting(expiry):
            self.ledger.append("ORDER_END", oid=o["oid"], status="expired", reason="到期未成交")
        for g in [g for g in self.state.groups.values() if g["expiry"] == expiry]:
            cash, fees, itm = 0.0, 0.0, False
            legs = []
            for lg in g["legs"]:
                iv = max(0, settle_px - lg["strike"]) if lg["cp"] == "C" else max(0, lg["strike"] - settle_px)
                legs.append({**lg, "intrinsic": iv})
                cash += (1 if lg["side"] == "buy" else -1) * iv * lg["lots"] * self.cfg["multiplier"]
                if iv > 0:   # 價外歸零免手續費與稅；價內結算費用規則待確認（假設與平倉同率，標註）
                    itm = True
                    fees += leg_fees(iv, lg["lots"], self.cfg)
            cash -= fees
            ev = self.ledger.append("SETTLE", gid=g["gid"], expiry=expiry, settle_px=settle_px, legs=legs, fees=fees, cash_delta=cash,
                                    reason="到期結算", fee_model="itm_assumed_same_rate" if itm else "worthless_free", at=str(today))
            out.append(ev)
        return out

    def user_resume(self, note):
        """只有人（使用者）能呼叫：解除回撤鎖定。AI 通道不得暴露這個方法。"""
        self.ledger.append("USER_RESUME", note=note)
