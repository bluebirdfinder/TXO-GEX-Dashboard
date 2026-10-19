"""選擇權報價鏈與「可成交」判斷。保守算法：賣用買價、買用賣價。無效報價一律回 None，不補假數字。"""
import re
from dataclasses import dataclass
from datetime import datetime

from expiry import MIS_PREFIX


@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    ts: float          # epoch 秒，該筆報價的更新時間


class QuoteChain:
    """quotes: {(expiry_code, cp, strike): Quote}；now: 取用此鏈的時間點（epoch 秒）。"""

    def __init__(self, now, quotes, validity):
        self.now = now
        self.quotes = quotes
        self.v = validity

    def usable(self, key, side):
        """side='sell' 需要買價與買量；'buy' 需要賣價與賣量。回傳 (價, 量) 或 (None, 原因)。"""
        q = self.quotes.get(key)
        if q is None:
            return None, "無此履約價報價"
        if self.now - q.ts > self.v["max_age_s"]:
            return None, "報價太舊"
        if q.ask < q.bid or q.bid < 0:
            return None, "買賣價異常"
        if q.ask - q.bid > self.v["max_bid_ask_spread_pts"]:
            return None, "買賣價差過大"
        px, size = (q.bid, q.bid_size) if side == "sell" else (q.ask, q.ask_size)
        if self.v.get("require_size_positive", True) and size <= 0:
            return None, "委託量為0"
        if px <= 0:
            return None, "價格為0"
        return (px, size), None

    def leg_price(self, key, side):
        """賣出→買價，買進→賣價。"""
        r, why = self.usable(key, side)
        return (r[0], r[1], None) if r else (None, 0, why)

    def spread_credit(self, expiry, cp, short_strike, long_strike):
        """賣腳買價 − 買腳賣價。回傳 (點數, 可成交口數上限, 原因)；任一腳無效 → (None, 0, 原因)。"""
        s, s_size, why = self.leg_price((expiry, cp, short_strike), "sell")
        if s is None:
            return None, 0, f"賣腳{why}"
        b, b_size, why = self.leg_price((expiry, cp, long_strike), "buy")
        if b is None:
            return None, 0, f"買腳{why}"
        return s - b, min(s_size, b_size), None

    def close_cost(self, legs):
        """平倉單組的成本(點，正=付出)：空腳用賣價買回、多腳用買價賣出。回傳 (點數, 原因)。"""
        total = 0.0
        for lg in legs:
            key = (lg["expiry"], lg["cp"], lg["strike"])
            if lg["side"] == "sell":      # 空腳 → 買回 → 付賣價
                r, why = self.usable(key, "buy")
                if not r:
                    return None, f"{lg['strike']}{lg['cp']} {why}"
                total += r[0] * lg["lots"]
            else:                         # 多腳 → 賣出 → 收買價
                r, why = self.usable(key, "sell")
                if not r:
                    return None, f"{lg['strike']}{lg['cp']} {why}"
                total -= r[0] * lg["lots"]
        return total, None


# ---- MIS 原始資料轉換 ----
_SYM = re.compile(r"^(TX[A-Z0-9])(\d{5})([A-X])(\d)-([A-Z])$")


def parse_mis_symbol(sym):
    """'TXY42200J6-N' → (到期代碼, cp, 履約價)；代碼格式不認得回 None。
    月份字母：A-L=1~12月 Call、M-X=1~12月 Put。年份尾碼假設 202x。"""
    m = _SYM.match(sym or "")
    if not m or m.group(1) not in MIS_PREFIX:
        return None
    typ, n = MIS_PREFIX[m.group(1)]
    idx = ord(m.group(3)) - ord("A")
    cp, month = ("C", idx + 1) if idx < 12 else ("P", idx - 11)
    year = 2020 + int(m.group(4))
    code = f"{year}{month:02d}" + ("" if typ == "monthly" else ("W" if typ == "weekly_wed" else "F") + str(n))
    return code, cp, int(m.group(2))


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v


def chain_from_mis_rows(now, rows, validity, ts_fallback=None):
    """rows: 紀錄器存的 q 列表。報價時間用 CDate+CTime；缺漏時用 ts_fallback，仍缺就當作過期(0)。"""
    quotes = {}
    for r in rows:
        k = parse_mis_symbol(r.get("SymbolID"))
        bid, ask = _f(r.get("CBestBidPrice")), _f(r.get("CBestAskPrice"))
        if not k or bid is None or ask is None:
            continue
        ts = ts_fallback or 0.0
        d, t = r.get("CDate"), r.get("CTime")
        if d and t and len(str(t)) >= 6:
            try:
                ts = datetime.strptime(f"{d}{str(t)[:6]}", "%Y%m%d%H%M%S").timestamp()
            except ValueError:
                pass
        quotes[k] = Quote(bid, ask, int(_f(r.get("CBestBidSize")) or 0), int(_f(r.get("CBestAskSize")) or 0), ts)
    return QuoteChain(now, quotes, validity)
