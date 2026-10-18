"""到期代碼解析（照 AGENTS.md 的對照表）。202610W4=週三選第4個、202610F2=週五選第2個、202610=月選(第3個週三)。
不處理國定假日順延；假日調整需另外用期交所行事曆（待確認）。"""
import re
from datetime import date, timedelta

_CODE = re.compile(r"^(\d{4})(\d{2})(?:([WF])([1-5]))?$")

# 期交所商品代碼 → (到期類型, 序號)；MIS 回傳的前綴（Lumi 附錄B：看到 TXY/TX4/TXZ，不是完整對照，待核對）
MIS_PREFIX = {"TXO": ("monthly", 0),
              "TX1": ("weekly_wed", 1), "TX2": ("weekly_wed", 2), "TX4": ("weekly_wed", 4), "TX5": ("weekly_wed", 5),
              "TXU": ("weekly_fri", 1), "TXV": ("weekly_fri", 2), "TXX": ("weekly_fri", 3), "TXY": ("weekly_fri", 4),
              "TXZ": ("weekly_fri", 5)}


def parse_code(code):
    m = _CODE.match(code or "")
    if not m:
        raise ValueError(f"到期代碼格式不對: {code!r}")
    y, mo, wf, n = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
    if not 1 <= mo <= 12:
        raise ValueError(f"月份不對: {code!r}")
    if wf is None:
        return y, mo, "monthly", 0
    return y, mo, ("weekly_wed" if wf == "W" else "weekly_fri"), int(n)


def expiry_type(code):
    return parse_code(code)[2]


def is_weekly(code):
    return expiry_type(code) != "monthly"


def _nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    d += timedelta(weeks=n - 1)
    if d.month != month:
        raise ValueError(f"{year}-{month:02d} 沒有第 {n} 個該星期幾")
    return d


def expiry_date(code):
    y, mo, typ, n = parse_code(code)
    if typ == "monthly":
        return _nth_weekday(y, mo, 2, 3)           # 每月第3個週三
    return _nth_weekday(y, mo, 2 if typ == "weekly_wed" else 4, n)


def dte(code, today):
    return (expiry_date(code) - today).days
