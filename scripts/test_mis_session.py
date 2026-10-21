# -*- coding: utf-8 -*-
import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.mis_session import mis_market_type, session_is_open, mis_quote_is_stale

D = datetime.datetime
# 2026-10-12 是週一；10/16 週五；10/17 週六；10/18 週日
CASES_TYPE = [
    (D(2026, 10, 17, 4, 59), '1'), (D(2026, 10, 17, 5, 0), '1'),   # 週六上午＝週五夜盤（本次 bug）
    (D(2026, 10, 17, 10, 0), '1'), (D(2026, 10, 18, 12, 0), '1'),
    (D(2026, 10, 19, 8, 44), '1'), (D(2026, 10, 19, 8, 45), '0'),  # 週一開盤前仍夜盤
    (D(2026, 10, 19, 13, 50), '0'), (D(2026, 10, 19, 14, 59), '0'),
    (D(2026, 10, 19, 15, 0), '1'), (D(2026, 10, 20, 3, 0), '1'),
    (D(2026, 10, 16, 10, 0), '0'),
]
for now, exp in CASES_TYPE:
    assert mis_market_type(now) == exp, (now, exp, mis_market_type(now))

CASES_OPEN = [
    (D(2026, 10, 17, 10, 0), False), (D(2026, 10, 18, 22, 0), False), (D(2026, 10, 19, 2, 0), False),
    (D(2026, 10, 19, 9, 0), True), (D(2026, 10, 19, 14, 0), False), (D(2026, 10, 19, 15, 30), True),
    (D(2026, 10, 20, 2, 0), True), (D(2026, 10, 17, 2, 0), True), (D(2026, 10, 17, 5, 0), False),
]
for now, exp in CASES_OPEN:
    assert session_is_open(now) == exp, (now, exp)

# 過期判斷
assert mis_quote_is_stale(D(2026, 10, 17, 10, 0), '045957') is False          # 休市：不算過期
assert mis_quote_is_stale(D(2026, 10, 19, 9, 0, 30), '090020') is False       # 開盤中 10 秒前
assert mis_quote_is_stale(D(2026, 10, 19, 9, 10, 0), '090020') is True        # 開盤中 10 分鐘前 → 過期
assert mis_quote_is_stale(D(2026, 10, 19, 9, 0, 0), '134459') is True         # 開盤中卻是昨天日盤收盤 → 過期
assert mis_quote_is_stale(D(2026, 10, 20, 0, 0, 20), '235950') is False       # 跨午夜 30 秒內
assert mis_quote_is_stale(D(2026, 10, 19, 9, 0, 0), '') is True
assert mis_quote_is_stale(D(2026, 10, 19, 9, 0, 0), None) is True
print("mis_session: all tests passed")
