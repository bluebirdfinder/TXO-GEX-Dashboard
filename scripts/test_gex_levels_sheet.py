"""Self-test for the pure helpers of gex_levels_sheet.py (no network). Run: python scripts/test_gex_levels_sheet.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gex_levels_sheet as s  # noqa: E402

ok = True
def check(n, c):
    global ok
    print(("PASS " if c else "FAIL ") + n); ok = ok and c

# max pain on a tiny book: calls at 100 (10), puts at 100 (10), calls at 110 (5)
C = {100: 10, 110: 5}; P = {100: 10, 90: 4}
mp, loss = s.max_pain(C, P)
manual = {S: sum(max(0, S - k) * C.get(k, 0) + max(0, k - S) * P.get(k, 0) for k in set(C) | set(P)) for S in sorted(set(C) | set(P))}
check("max_pain picks the minimum of the manual loss table", mp == min(manual, key=manual.get) and loss == manual)
check("max_pain of an empty book is None", s.max_pain({}, {})[0] is None)
lo, hi = s.flat_band(loss, mp, 0.02)
check("flat_band contains the max pain strike", lo <= mp <= hi)
lo2, hi2 = s.flat_band(loss, mp, 1e9)
check("a huge tolerance widens the band to the whole range", (lo2, hi2) == (min(loss), max(loss)))
check("side labels", s.side(101, 100) == "現價上方" and s.side(99, 100) == "現價下方" and s.side(100, 100) == "現價")
check("fmt handles None", s.fmt(None) == "—" and s.fmt(1234.4) == "1,234")
print("ALL PASS" if ok else "SOME FAILED"); sys.exit(0 if ok else 1)
