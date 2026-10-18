"""由帳本重播出帳戶狀態（單一事實來源）。數字只從事件算出來，沒有任何地方可以手改。
費用、保證金、損益的計算函式也放這裡，讓下單簿和測試用同一套。"""
from decimal import ROUND_HALF_UP, Decimal


def tax_per_lot(px, cfg):
    """期交稅：每口權利金(點x乘數) x 稅率，逐口四捨五入到整數元。"""
    v = Decimal(str(px)) * cfg["multiplier"] * Decimal(str(cfg["fees"]["tax_rate"]))
    return int(v.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def leg_fees(px, lots, cfg):
    """單腳單邊的手續費+期交稅（元）。"""
    return lots * cfg["fees"]["fee_per_lot_per_side"] + lots * tax_per_lot(px, cfg)


def legs_cash(legs, cfg):
    """開/平倉的現金流（元，不含費用）：賣出收權利金、買進付權利金。"""
    m = cfg["multiplier"]
    return sum((1 if lg["side"] == "sell" else -1) * lg["px"] * lg["lots"] * m for lg in legs)


def side_margin(legs, cp, cfg):
    """某一側(C或P)選擇權腿在到期時的最壞損失（不含權利金）= 保證金近似 v0。"""
    ls = [lg for lg in legs if lg["cp"] == cp]
    if not ls:
        return 0.0
    ks = sorted({lg["strike"] for lg in ls})
    pts = [0] + ks + [max(ks) * 2]

    def payoff(s):
        t = 0.0
        for lg in ls:
            iv = max(0, s - lg["strike"]) if cp == "C" else max(0, lg["strike"] - s)
            t += (1 if lg["side"] == "buy" else -1) * iv * lg["lots"]
        return t
    worst = min(payoff(s) for s in pts)
    return max(0.0, -worst) * cfg["multiplier"]


class State:
    def __init__(self, cfg, events):
        self.cfg = cfg
        self.capital = None
        self.account = None
        self.cash = 0.0
        self.groups = {}        # gid -> 未平倉組合
        self.orders = {}        # oid -> 掛單
        self.realized = 0.0     # 含費用
        self.fees_total = 0.0
        self.closed = []        # 已了結組合紀錄
        self.high_water = 0.0
        self.last_equity = None
        self.last_mark_date = None
        self.day_start_equity = {}   # 日期 -> 當日起始淨值
        self.dd_lock = None     # None / 'reduced' / 'halted'（只有 USER_RESUME 能解除）
        self.decisions = {}
        self.rejects = 0
        for e in events:
            self._apply(e)

    # ---- 事件重播 ----
    def _apply(self, e):
        t = e["type"]
        if t == "ACCOUNT_OPEN":
            self.account, self.capital = e["account"], float(e["capital"])
            self.cash = self.high_water = self.last_equity = self.capital
        elif t == "DECISION":
            self.decisions[e["decision_id"]] = e["decision"]
        elif t == "REJECT":
            self.rejects += 1
        elif t == "ORDER":
            self.orders[e["oid"]] = {**e["order"], "oid": e["oid"], "remaining": e["order"]["lots"], "status": "resting"}
        elif t == "ORDER_END":
            if e["oid"] in self.orders:
                self.orders[e["oid"]]["status"] = e["status"]
        elif t == "FILL":
            self.cash += e["cash_delta"]
            self.fees_total += e["fees"]
            self.groups[e["gid"]] = {
                "gid": e["gid"], "expiry": e["expiry"], "structure": e["structure"], "strategy_tag": e["strategy_tag"],
                "legs": [dict(lg) for lg in e["legs"]], "open_cash": e["cash_delta"], "exit_plan": e.get("exit_plan") or {},
                "opened_at": e["quote_ts"], "approx": e["approx"], "last_px": {i: lg["px"] for i, lg in enumerate(e["legs"])},
                "stale": False, "oid": e.get("oid")}
            o = self.orders.get(e.get("oid"))
            if o:
                o["remaining"] -= e["lots"]
                if o["remaining"] <= 0:
                    o["status"] = "filled"
        elif t in ("CLOSE", "SETTLE"):
            self.cash += e["cash_delta"]
            self.fees_total += e["fees"]
            g = self.groups.pop(e["gid"], None)
            if g:
                pnl = g["open_cash"] + e["cash_delta"]
                self.realized += pnl
                self.closed.append({"gid": e["gid"], "strategy_tag": g["strategy_tag"], "expiry": g["expiry"],
                                    "structure": g["structure"], "pnl": pnl, "reason": e.get("reason", t.lower()),
                                    "approx": g["approx"], "closed_at": e.get("at")})
        elif t == "MARK":
            self.last_equity = e["equity"]
            self.last_mark_date = e["date"]
            self.high_water = max(self.high_water, e["equity"])
            self.day_start_equity.setdefault(e["date"], e["day_start_equity"])
            for gid, px in e.get("group_px", {}).items():
                if gid in self.groups:
                    self.groups[gid]["last_px"] = {int(k): v for k, v in px["px"].items()}
                    self.groups[gid]["stale"] = px["stale"]
            if e.get("dd_lock"):
                self.dd_lock = e["dd_lock"] if self.dd_lock != "halted" else "halted"
        elif t == "USER_RESUME":
            self.dd_lock = None

    # ---- 估值 ----
    def position_value(self):
        """持倉清算價值（元）：多腳用最近買價、空腳用最近賣價，帶符號。"""
        m = self.cfg["multiplier"]
        tot = 0.0
        for g in self.groups.values():
            for i, lg in enumerate(g["legs"]):
                tot += (1 if lg["side"] == "buy" else -1) * g["last_px"][i] * lg["lots"] * m
        return tot

    def equity(self):
        return self.cash + self.position_value()

    def drawdown_pct(self):
        return 100 * (self.high_water - self.equity()) / self.high_water if self.high_water else 0.0

    def margin_by_expiry(self, extra_groups=()):
        """每個到期日：多空雙邊互抵，只收較大的一側。"""
        per = {}
        for g in list(self.groups.values()) + list(extra_groups):
            d = per.setdefault(g["expiry"], {"P": 0.0, "C": 0.0})
            for cp in ("P", "C"):
                d[cp] += side_margin(g["legs"], cp, self.cfg)
        return {k: max(v.values()) for k, v in per.items()}

    def margin_used(self, extra_groups=()):
        return sum(self.margin_by_expiry(extra_groups).values())

    def side_exposure(self, expiry, cp):
        """某到期日某一側(P=Bull Put, C=Bear Call)已成交部位的最壞虧損（扣掉收到的權利金）+ 口數。"""
        loss, lots = 0.0, 0
        for g in self.groups.values():
            if g["expiry"] != expiry:
                continue
            sides = [s for s in ("P", "C") if side_margin(g["legs"], s, self.cfg) > 0]
            if cp in sides:
                loss += max(0.0, side_margin(g["legs"], cp, self.cfg) - g["open_cash"] / len(sides))
                lots += max((lg["lots"] for lg in g["legs"] if lg["cp"] == cp and lg["side"] == "sell"), default=0)
        return loss, lots

    def resting(self, expiry=None):
        return [o for o in self.orders.values() if o["status"] == "resting" and (expiry is None or o["expiry"] == expiry)]

    def active_expiries(self):
        return {g["expiry"] for g in self.groups.values()} | {o["expiry"] for o in self.resting()}

    def day_pnl(self, date_str):
        """當日損益(元)。當天還沒計價過，起始淨值＝最近一次計價的淨值（沒有就用本金）。"""
        start = self.day_start_equity.get(date_str, self.last_equity)
        return self.equity() - start
