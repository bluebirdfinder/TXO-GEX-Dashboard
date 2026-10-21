"""指標轉接層測試（聚合、已收完判斷、接歷史、竭盡方向）。K 線全是測試用假資料；不含任何指標公式。"""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indicators as ind   # noqa: E402
import snapshot as sm      # noqa: E402

TW = "+08:00"


def mk(start, n, price=100.0, step=0.0):
    out, t = [], datetime.strptime(start, "%Y-%m-%d %H:%M")
    for i in range(n):
        p = price + step * i
        out.append({"ts": (t + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M"), "open": p, "high": p + 1, "low": p - 1, "close": p + 0.5, "volume": 10})
    return out


class FakeMod:
    """假的私有模組：讓最後一根 b_done+b_perf 為真，用來驗證轉接層的方向與視窗邏輯。"""
    def __init__(self, down=False, up=False, perf=True):
        self.down, self.up, self.perf = down, up, perf

    def compute(self, bars):
        st = [{"b_cnt": 0, "s_cnt": 0, "b_done": False, "s_done": False, "b_perf": False, "s_perf": False,
               "bc": 0, "sc": 0, "bc_comp": False, "sc_comp": False} for _ in bars]
        st[-2]["b_done"], st[-2]["b_perf"] = self.down, self.perf
        st[-2]["s_done"], st[-2]["s_perf"] = self.up, self.perf
        return st


class TestResample(unittest.TestCase):
    def test_day_session_anchored_at_0845(self):
        bars = mk("2026-10-19 08:45", 300)
        r15 = ind.resample(bars, 15)
        self.assertEqual((len(r15), r15[0]["ts"], r15[-1]["ts"]), (20, "2026-10-19 08:45", "2026-10-19 13:30"))
        r30 = ind.resample(bars, 30)
        self.assertEqual([b["ts"][-5:] for b in r30[:3]], ["08:45", "09:15", "09:45"])
        self.assertTrue(all(b["n"] == 30 for b in r30))

    def test_night_session_anchored_at_1500_and_crosses_midnight(self):
        bars = mk("2026-10-19 23:30", 120)               # 23:30 → 01:29
        r30 = ind.resample(bars, 30)
        self.assertEqual([b["ts"] for b in r30], ["2026-10-19 23:30", "2026-10-20 00:00", "2026-10-20 00:30", "2026-10-20 01:00"])

    def test_ohlc_aggregation(self):
        bars = mk("2026-10-19 09:00", 15, price=100, step=1)
        b = ind.resample(bars, 15)[0]
        self.assertEqual((b["open"], b["high"], b["low"], b["close"], b["volume"]), (100, 115, 99, 114.5, 150))

    def test_closed_only_drops_forming_bucket(self):
        bars = mk("2026-10-19 09:00", 20)                # 到 09:19，已收完 1 根 15M（09:00），09:15 那根還沒收完
        r = ind.resample(bars, 15)
        c = ind.closed_only(r, 15, bars[-1]["ts"])
        self.assertEqual([b["ts"][-5:] for b in c], ["09:00"])


class TestMerge(unittest.TestCase):
    def test_overlap_prefers_history_and_appends_new(self):
        t0 = datetime(2026, 10, 19, 8, 45)
        row = lambda i, c: {"ts": (t0 + timedelta(minutes=15 * i)).strftime("%Y-%m-%d %H:%M"), "open": c, "high": c + 1, "low": c - 1, "close": c, "volume": 1}
        hist = [row(i, 50) for i in range(4)]            # 08:45 .. 09:30
        fresh = [row(3, 99), row(4, 60), row(5, 61)]     # 09:30 重疊、09:45、10:00 新
        m, gap, msg = ind.merge_history(hist, fresh)
        self.assertEqual(msg, "ok")
        self.assertEqual([b["close"] for b in m], [50, 50, 50, 50, 60, 61])      # 重疊那根以歷史為準

    def test_gap_too_large_is_flagged(self):
        hist = mk("2026-10-14 08:45", 3)
        fresh = mk("2026-10-20 08:45", 3)
        m, gap, msg = ind.merge_history(hist, fresh, max_gap_h=60)
        self.assertGreater(gap, 60)
        self.assertIn("不可信", msg)

    def test_missing_bars_inside_same_session_flagged(self):
        hist = mk("2026-10-19 08:45", 1)                 # 歷史停在 08:45 這根
        fresh = mk("2026-10-19 10:00", 1)                # 新棒從 10:00 開始：同一日盤中間漏了一大段
        m, gap, msg = ind.merge_history(hist, fresh, minutes=15)
        self.assertIn("不可信", msg)

    def test_weekend_gap_allowed(self):
        hist = mk("2026-10-17 04:50", 1)                 # 週六凌晨夜盤尾
        fresh = mk("2026-10-19 08:45", 1)
        self.assertEqual(ind.merge_history(hist, fresh)[2], "ok")


class TestExhaustion(unittest.TestCase):
    def build(self, mod, **kw):
        fresh = mk("2026-10-19 08:45", 300, step=0.0)
        def hist(minutes, n=40):                         # 歷史：結束在週六凌晨夜盤尾（與週一日盤相隔約 52 小時，算連續）
            t = datetime(2026, 10, 17, 4, 59) - timedelta(minutes=minutes * (n - 1))
            return [{"ts": (t + timedelta(minutes=minutes * i)).strftime("%Y-%m-%d %H:%M"), "open": 1, "high": 2, "low": 0, "close": 1, "volume": 1} for i in range(n)]
        cache = {"15M": hist(15), "30M": hist(30)}
        return ind.build_indicators(fresh, cache, mod, **kw)

    def test_no_private_module_means_unavailable_and_no_exhaustion(self):
        r = self.build(None)
        self.assertFalse(r["down_exhausted"] or r["up_exhausted"])
        self.assertIn("九轉不可用", " ".join(r["note"]))

    def test_down_exhaustion_detected_with_perfection(self):
        r = self.build(FakeMod(down=True))
        self.assertTrue(r["down_exhausted"])
        self.assertFalse(r["up_exhausted"])

    def test_perfection_required_by_default(self):
        self.assertFalse(self.build(FakeMod(down=True, perf=False))["down_exhausted"])
        self.assertTrue(self.build(FakeMod(down=True, perf=False), require_perfection=False)["down_exhausted"])

    def test_direction_follows_surge_sign_in_ctx(self):
        rules = {"surge_window_min": 60}
        up_bars = [{"ts": f"2026-10-19 10:{i:02d}", "open": 1, "high": 2, "low": 1, "close": 1 + i * 20, "volume": 1} for i in range(40)]
        self.assertGreater(sm.surge_pts(up_bars, 60), 0)
        self.assertTrue(sm._exhaustion({"down_exhausted": False, "up_exhausted": True}, 600))      # 急拉看買盤竭盡
        self.assertFalse(sm._exhaustion({"down_exhausted": True, "up_exhausted": False}, 600))     # 急拉時賣盤竭盡沒用
        self.assertTrue(sm._exhaustion({"down_exhausted": True, "up_exhausted": False}, -600))     # 急殺看賣盤竭盡
        self.assertFalse(sm._exhaustion({}, -600))


if __name__ == "__main__":
    unittest.main()
