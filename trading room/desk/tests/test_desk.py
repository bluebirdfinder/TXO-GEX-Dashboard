"""假決策單單元測試。全部數字手算：1 點 = 50 元；手續費每口每邊 13；期交稅=每口權利金x0.1% 逐口四捨五入。
執行：cd "trading room/desk" && python -m unittest discover -s tests -v"""
import copy
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import risk                                    # noqa: E402
from book import Desk, load_config              # noqa: E402
from expiry import dte, expiry_date, expiry_type  # noqa: E402
from ledger import Ledger                       # noqa: E402
from quotes import Quote, QuoteChain, chain_from_mis_rows, parse_mis_symbol  # noqa: E402
from state import tax_per_lot                   # noqa: E402

CFG = load_config()
TW = "+08:00"
W4 = "202610W4"       # 2026-10-28 週三
NOW = datetime.fromisoformat("2026-10-26T10:00:00" + TW).timestamp()


def chain(quotes, now=NOW, ts=None):
    q = {k: Quote(*v, ts=NOW if ts is None else ts) for k, v in quotes.items()}
    return QuoteChain(now, q, CFG["quote_validity"])


# 現價 46,500，賣 46,300P(買85/賣86) 買 46,100P(買19/賣20) → 信用 85-20=65 點
BASE = {(W4, "P", 46300): (85, 86, 5, 5), (W4, "P", 46100): (19, 20, 5, 5),
        (W4, "C", 46700): (80, 81, 5, 5), (W4, "C", 46900): (18, 19, 5, 5)}
CTX = {"now": NOW, "today": date(2026, 10, 26), "spot": 46500, "iv": 12.0, "surge_pts": 0, "exhaustion_ok": False, "missing": []}


def order(**kw):
    d = {"account": "T0", "decided_at": "2026-10-26T10:00:00" + TW, "action": "open", "expiry": {"code": W4},
         "structure": "bull_put_spread", "strategy_tag": "bp_test",
         "legs": [{"side": "sell", "cp": "P", "strike": 46300, "lots": 1}, {"side": "buy", "cp": "P", "strike": 46100, "lots": 1}],
         "thesis": "t", "invalidation": "i", "exit_plan": {"stop_debit_pts": 150, "take_profit_debit_pts": 10},
         "manual_ref": "playbook v0"}
    d.update(kw)
    return d


def ladder(rungs_bp=((46300, 46100, 1, 65),), rungs_bc=(), **kw):
    sets = [{"direction": "bull_put", "rungs": [dict(short_strike=a, long_strike=b, lots=c, min_credit_pts=p) for a, b, c, p in rungs_bp]}]
    if rungs_bc:
        sets.append({"direction": "bear_call", "rungs": [dict(short_strike=a, long_strike=b, lots=c, min_credit_pts=p) for a, b, c, p in rungs_bc]})
    d = order(action="place_ladder", side_sets=sets)
    d.pop("structure"); d.pop("legs")
    d.update(kw)
    return d


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.desk = Desk(Path(self.tmp.name) / "t0.jsonl", "T0", copy.deepcopy(CFG))

    def tearDown(self):
        self.tmp.cleanup()


class TestFeesAndExpiry(unittest.TestCase):
    def test_tax_examples_from_statement(self):    # 規格第7節：17,300→17、20,600→21、3,150→3
        self.assertEqual(tax_per_lot(346, CFG), 17)
        self.assertEqual(tax_per_lot(412, CFG), 21)
        self.assertEqual(tax_per_lot(63, CFG), 3)

    def test_expiry_codes(self):
        self.assertEqual(expiry_date("202610W4"), date(2026, 10, 28))
        self.assertEqual(expiry_date("202610W1"), date(2026, 10, 7))
        self.assertEqual(expiry_date("202610"), date(2026, 10, 21))      # 第3個週三
        self.assertEqual(expiry_date("202610F2"), date(2026, 10, 9))     # 第2個週五
        self.assertEqual(expiry_type("202610F2"), "weekly_fri")
        self.assertEqual(dte("202610W4", date(2026, 10, 26)), 2)

    def test_mis_symbol(self):
        self.assertEqual(parse_mis_symbol("TXY42200J6-N"), ("202610F4", "C", 42200))
        self.assertEqual(parse_mis_symbol("TX442200V6-N"), ("202610W4", "P", 42200))
        self.assertEqual(parse_mis_symbol("TXO33900J6-N"), ("202610", "C", 33900))
        self.assertEqual(parse_mis_symbol("TXO33900J6-O"), ("202610", "C", 33900))   # 2026-10-19 實測：日盤後綴是 -O\n        self.assertIsNone(parse_mis_symbol("TXO-R"))\n        self.assertIsNone(parse_mis_symbol("TXO-Q"))


class TestQuotes(unittest.TestCase):
    def test_credit_and_invalid_quotes(self):
        c = chain(BASE)
        self.assertEqual(c.spread_credit(W4, "P", 46300, 46100), (65, 5, None))
        stale = chain(BASE, now=NOW + 500)             # 全部超過 120 秒
        self.assertIsNone(stale.spread_credit(W4, "P", 46300, 46100)[0])
        wide = chain({**BASE, (W4, "P", 46300): (3, 3500, 5, 5)})
        self.assertIsNone(wide.spread_credit(W4, "P", 46300, 46100)[0])
        nosize = chain({**BASE, (W4, "P", 46100): (19, 20, 5, 0)})
        self.assertEqual(nosize.spread_credit(W4, "P", 46300, 46100)[2], "買腳委託量為0")


class TestOpenAndSettle(Base):
    def test_open_fill_numbers_hand_checked(self):
        r = self.desk.submit(order(), CTX, chain(BASE))
        self.assertEqual(r["result"], "filled")
        # 賣 85 點 = 4,250 元；買 20 點 = 1,000 元 → 現金 +3,250
        # 費用：13x2=26；稅 賣 4,250x0.1%=4.25→4、買 1,000x0.1%=1 → 5 → 共 31
        self.assertEqual(r["fees"], 31)
        self.assertEqual(r["cash_delta"], 3250 - 31)
        self.assertTrue(r["approx"])                   # 驗證前一律「近似」
        self.assertEqual(self.desk.state.cash, 1_000_000 + 3250 - 31)

    def test_expire_worthless_free_and_pnl(self):
        self.desk.submit(order(), CTX, chain(BASE))
        self.desk.settle(W4, 46500, date(2026, 10, 28))
        st = self.desk.state
        self.assertEqual(st.groups, {})
        self.assertEqual(st.realized, 3250 - 31)       # 價外歸零不再收費用
        self.assertEqual(st.cash, 1_000_000 + 3219)

    def test_expire_itm_loss(self):
        self.desk.submit(order(), CTX, chain(BASE))
        self.desk.settle(W4, 46000, date(2026, 10, 28))    # 46300P 內含 300、46100P 內含 100 → 淨 -200 點 = -10,000
        st = self.desk.state
        itm_fees = (13 + tax_per_lot(300, CFG)) + (13 + tax_per_lot(100, CFG))   # 假設與平倉同率（待確認）
        self.assertEqual(st.realized, 3250 - 31 - 10000 - itm_fees)

    def test_cannot_settle_before_expiry(self):
        self.desk.submit(order(), CTX, chain(BASE))
        with self.assertRaises(ValueError):
            self.desk.settle(W4, 46500, date(2026, 10, 27))

    def test_no_valid_quote_means_no_fill_and_no_fake_price(self):
        r = self.desk.submit(order(), CTX, chain(BASE, now=NOW + 999))
        self.assertEqual(r["result"], "no_fill")
        self.assertEqual(self.desk.state.groups, {})
        self.assertEqual(self.desk.state.cash, 1_000_000)

    def test_close_group_conservative(self):
        r = self.desk.submit(order(), CTX, chain(BASE))
        gid = r["gid"]
        later = chain({(W4, "P", 46300): (39, 40, 5, 5), (W4, "P", 46100): (9, 10, 5, 5)})
        c = self.desk.submit({"account": "T0", "decided_at": "2026-10-26T11:00:00" + TW, "action": "close", "group_id": gid,
                              "manual_ref": "p"}, CTX, later)
        # 買回賣腳@賣價40=2,000元付出；賣出買腳@買價9=450元收入；費用 26 + 稅 40x50x.1%=2 +9x50x.1%=0.45→0 → 28
        self.assertEqual(c["result"], "closed")
        self.assertEqual(c["fees"], 26 + 2 + 0)
        self.assertEqual(c["cash_delta"], -2000 + 450 - 28)
        self.assertEqual(self.desk.state.realized, (3250 - 31) + (-2000 + 450 - 28))


class TestLedger(Base):
    def test_hash_chain_detects_tampering(self):
        self.desk.submit(order(), CTX, chain(BASE))
        self.assertTrue(self.desk.ledger.verify()[0])
        p = self.desk.ledger.path
        p.write_text(p.read_text(encoding="utf-8").replace('"cash_delta":3219', '"cash_delta":9999'), encoding="utf-8")
        self.assertFalse(Ledger(p).verify()[0])
        with self.assertRaises(RuntimeError):
            self.desk.ledger.append("MARK", date="x")

    def test_no_mutation_api(self):
        public = [n for n in dir(Ledger) if not n.startswith("_")]
        self.assertEqual(sorted(public), ["append", "events", "verify"])

    def test_replay_is_deterministic(self):
        self.desk.submit(order(), CTX, chain(BASE))
        self.assertEqual(self.desk.state.cash, self.desk.state.cash)
        self.assertEqual(self.desk.state.fees_total, 31)


class TestRedlines(Base):
    def rejected(self, d, ctx=None, ch=None, why=None):
        r = self.desk.submit(d, ctx or CTX, ch or chain(BASE))
        self.assertFalse(r["ok"], r)
        if why:
            self.assertTrue(any(why in x for x in r["reasons"]), r["reasons"])
        return r

    def test_legging_out_weekly_blocked(self):
        gid = self.desk.submit(order(), CTX, chain(BASE))["gid"]
        d = {"account": "T0", "decided_at": "2026-10-26T11:00:00" + TW, "action": "close", "group_id": gid, "manual_ref": "p",
             "legs": [{"side": "buy", "cp": "P", "strike": 46300, "lots": 1}]}     # 只平賣腳
        self.rejected(d, why="禁止拆單")
        self.assertIn(gid, self.desk.state.groups)

    def test_naked_short_blocked(self):
        d = order(structure="bull_put_spread", legs=[{"side": "sell", "cp": "P", "strike": 46300, "lots": 1}])
        self.rejected(d, why="裸賣")

    def test_structure_mislabel_blocked(self):       # 賣腳的保護買腳方向反了
        d = order(legs=[{"side": "sell", "cp": "P", "strike": 46100, "lots": 1}, {"side": "buy", "cp": "P", "strike": 46300, "lots": 1}])
        self.rejected(d)

    def test_naked_buy_dte_lt3(self):
        d = order(structure="long_put", legs=[{"side": "buy", "cp": "P", "strike": 46100, "lots": 1}])
        self.desk.cfg["risk"]["stage"] = "B"
        self.rejected(d, why="DTE 2 < 3")

    def test_single_leg_not_allowed_in_stage_A(self):
        d = order(structure="long_put", legs=[{"side": "buy", "cp": "P", "strike": 46100, "lots": 1}])
        self.rejected(d, why="尚未開放")

    def test_covered_call_not_supported_yet(self):
        d = order(structure="covered_call", legs=[{"side": "sell", "cp": "C", "strike": 46700, "lots": 1}])
        self.rejected(d)

    def test_iv_cushion(self):
        near = order(legs=[{"side": "sell", "cp": "P", "strike": 46400, "lots": 1}, {"side": "buy", "cp": "P", "strike": 46200, "lots": 1}])
        self.rejected(near, ctx={**CTX, "iv": 15}, why="IV 分區氣墊")   # iv15 → 至少 250 點價外，46400 只有 100
        self.rejected(near, ctx={**CTX, "iv": 18}, why="350")       # iv>16 → 350
        far = order(legs=[{"side": "sell", "cp": "P", "strike": 46000, "lots": 1}, {"side": "buy", "cp": "P", "strike": 45800, "lots": 1}])
        q = {(W4, "P", 46000): (60, 61, 5, 5), (W4, "P", 45800): (10, 11, 5, 5)}
        self.assertTrue(self.desk.submit(far, {**CTX, "iv": 15}, chain(q))["ok"])    # 500 點價外 OK

    def test_itm_short_leg_is_not_a_cushion(self):
        itm = order(legs=[{"side": "sell", "cp": "P", "strike": 47000, "lots": 1}, {"side": "buy", "cp": "P", "strike": 46800, "lots": 1}])
        self.rejected(itm, why="價內")

    def test_no_chasing_on_surge(self):
        self.rejected(order(), ctx={**CTX, "surge_pts": -700}, why="不追價")
        self.rejected(ladder(), ctx={**CTX, "surge_pts": 800}, why="不追價")
        ok = self.desk.submit(order(), {**CTX, "surge_pts": -700, "exhaustion_ok": True}, chain(BASE))
        self.assertTrue(ok["ok"])                                   # 九轉竭盡後可以

    def test_missing_data_means_no_decision(self):
        self.rejected(order(), ctx={**CTX, "missing": ["GEX"]}, why="無決策：缺 GEX")
        self.rejected(order(), ctx={**CTX, "iv": None}, why="IV")
        self.assertEqual(self.desk.state.groups, {})

    def test_reject_is_logged_with_reasons(self):
        self.rejected(order(), ctx={**CTX, "missing": ["K線"]})
        ev = [e for e in self.desk.ledger.events() if e["type"] == "REJECT"]
        self.assertEqual(len(ev), 1)
        self.assertIn("K線", ev[0]["reasons"][0])

    def test_bad_format(self):
        d = order()
        d["decided_at"] = "2026-10-26T10:00:00Z"
        self.rejected(d, why="+08:00")
        d = order(); d.pop("exit_plan")
        self.rejected(d, why="exit_plan")
        d = order(account="T1")
        self.rejected(d)

    def test_daily_loss_stop(self):
        self.desk.submit(order(), CTX, chain(BASE))
        big_loss = chain({(W4, "P", 46300): (700, 701, 5, 5), (W4, "P", 46100): (5, 6, 5, 5)})
        self.desk.mark("2026-10-26", big_loss)        # 浮虧 (700-5)x50=34,750 > 3 萬
        self.rejected(order(decided_at="2026-10-26T12:00:00" + TW, legs=[{"side": "sell", "cp": "C", "strike": 46700, "lots": 1}, {"side": "buy", "cp": "C", "strike": 46900, "lots": 1}], structure="bear_call_spread"),
                      why="單日虧損")


class TestLadder(Base):
    def test_ladder_resting_nothing_filled_zero_margin(self):
        r = self.desk.submit(ladder(rungs_bp=((46300, 46100, 1, 70),)), CTX)       # 信用只有 65 < 70
        self.assertEqual(r["result"], "ladder_placed")
        self.assertEqual(self.desk.process_quotes(chain(BASE)), [])
        self.assertEqual(self.desk.state.margin_used(), 0)
        self.assertEqual(self.desk.state.cash, 1_000_000)

    def test_ladder_fills_only_when_credit_reached(self):
        self.desk.submit(ladder(rungs_bp=((46300, 46100, 2, 65),)), CTX)
        out = self.desk.process_quotes(chain(BASE))                                  # 信用剛好 65
        self.assertEqual(out[0][0], "fill")
        st = self.desk.state
        self.assertEqual(len(st.groups), 1)
        self.assertEqual(st.margin_used(), 200 * 50 * 2)                              # 寬 200 點 x 2 口 x 50
        self.assertEqual(st.cash, 1_000_000 + 2 * 3250 - 2 * 31)

    def test_partial_fill_limited_by_book_size(self):
        self.desk.submit(ladder(rungs_bp=((46300, 46100, 4, 65),)), CTX)
        q = {**BASE, (W4, "P", 46300): (85, 86, 2, 5)}                               # 賣腳買量只有 2
        self.desk.process_quotes(chain(q))
        st = self.desk.state
        self.assertEqual(sum(lg["lots"] for g in st.groups.values() for lg in g["legs"] if lg["side"] == "sell"), 2)
        self.assertEqual(st.resting()[0]["remaining"], 2)

    def test_touching_mid_price_is_not_fill(self):
        self.desk.submit(ladder(rungs_bp=((46300, 46100, 1, 65.5),)), CTX)           # 中間價約 65.5，但可成交只有 65
        self.assertEqual(self.desk.process_quotes(chain(BASE)), [])

    def test_stale_quote_never_fills(self):
        self.desk.submit(ladder(), CTX)
        self.assertEqual(self.desk.process_quotes(chain(BASE, now=NOW + 1000)), [])

    def test_order_expires(self):
        self.desk.submit(ladder(rungs_bp=((46300, 46100, 1, 99),)), CTX)
        later = NOW + 4 * 3600                                                         # 超過 13:45
        out = self.desk.process_quotes(chain(BASE, now=later))
        self.assertEqual(out[0][0], "expired")

    def test_both_sides_offset_margin(self):
        self.desk.submit(ladder(rungs_bp=((46300, 46100, 1, 60),), rungs_bc=((46700, 46900, 1, 60),)), CTX)
        self.desk.process_quotes(chain(BASE))
        st = self.desk.state
        self.assertEqual(len(st.groups), 2)
        self.assertEqual(st.margin_used(), 200 * 50)          # 多空互抵：只收單邊（近似 v0）

    def test_ladder_worst_loss_limits(self):
        # 8 口 x 200 點價差、信用 65：最壞 8x(200-65)x50=54,000 + 費用 > 5%x100 萬 → 被退回（規格自己的例子剛好在線上）
        d = ladder(rungs_bp=((46300, 46100, 1, 65), (46300, 46100, 2, 65), (46300, 46100, 2, 65), (46300, 46100, 3, 65)))
        r = self.desk.submit(d, CTX)
        self.assertFalse(r["ok"])
        self.assertTrue(any("最壞虧損" in x for x in r["reasons"]), r["reasons"])
        # 150 點寬、信用 65：8x85x50=34,000+208 → 通過
        ok = ladder(rungs_bp=((46300, 46150, 1, 65), (46300, 46150, 2, 65), (46300, 46150, 2, 65), (46300, 46150, 3, 65)))
        self.assertTrue(self.desk.submit(ok, CTX)["ok"])

    def test_lots_cap_8_and_resting_counted(self):
        self.assertTrue(self.desk.submit(ladder(rungs_bp=((46300, 46150, 5, 65),)), CTX)["ok"])
        r = self.desk.submit(ladder(rungs_bp=((46300, 46150, 4, 65),)), CTX)           # 5+4=9 > 8
        self.assertFalse(r["ok"])
        self.assertTrue(any("超過單邊上限" in x for x in r["reasons"]), r["reasons"])

    def test_both_sides_double_loss_cap(self):
        bp = ((46300, 46150, 8, 65),)
        bc = ((46700, 46850, 8, 65),)       # 各 8x85x50=34,000+208，合計 68,416 < 10 萬，且各自 < 5%
        self.assertTrue(self.desk.submit(ladder(rungs_bp=bp, rungs_bc=bc), CTX)["ok"])
        self.desk.cfg["risk"]["ladder_both_sides_max_loss_pct"] = 5.0
        d2 = ladder(rungs_bp=((46300, 46150, 1, 65),), rungs_bc=((46700, 46850, 1, 65),), expiry={"code": W4})
        d2["decided_at"] = "2026-10-26T10:05:00" + TW
        r = self.desk.submit(d2, CTX)
        self.assertFalse(r["ok"])

    def test_ladder_sets_limit(self):
        for code in ("202610W4", "202610F4"):
            self.desk.submit(ladder(expiry={"code": code}), {**CTX, "today": date(2026, 10, 26)})
        r = self.desk.submit(ladder(expiry={"code": "202611W1"}), CTX)
        self.assertFalse(r["ok"])
        self.assertTrue(any("到期日已達上限" in x for x in r["reasons"]))

    def test_stop_loss_enforced_by_program(self):
        self.desk.submit(ladder(rungs_bp=((46300, 46100, 1, 65),), exit_plan={"stop_debit_pts": 150, "take_profit_debit_pts": None}), CTX)
        self.desk.process_quotes(chain(BASE))
        crash = chain({(W4, "P", 46300): (199, 200, 5, 5), (W4, "P", 46100): (49, 50, 5, 5)})   # 平倉成本 200-49=151 ≥ 150
        out = self.desk.process_quotes(crash)
        self.assertEqual(out[0][0], "stop")
        self.assertEqual(self.desk.state.groups, {})
        self.assertEqual(self.desk.state.closed[0]["reason"].startswith("停損觸發"), True)


class TestMarkAndDrawdown(Base):
    def test_mark_to_market_not_all_in_entry_day(self):
        self.desk.submit(order(), CTX, chain(BASE))
        m1 = self.desk.mark("2026-10-26", chain(BASE))
        # 多腳以買價 19、空腳以賣價 86 清算：持倉值 = 19x50 - 86x50 = -3,350；現金 1,003,219 → 淨值 999,869
        self.assertEqual(m1["equity"], 1_000_000 + 3250 - 31 + (19 - 86) * 50)
        m2 = self.desk.mark("2026-10-27", chain({(W4, "P", 46300): (49, 50, 5, 5), (W4, "P", 46100): (9, 10, 5, 5)}))
        self.assertEqual(m2["equity"], 1_000_000 + 3219 + (9 - 50) * 50)
        self.assertNotEqual(m1["equity"], m2["equity"])

    def test_stale_quote_carries_last_price_and_flags(self):
        self.desk.submit(order(), CTX, chain(BASE))
        r = self.desk.mark("2026-10-26", chain(BASE, now=NOW + 9999))
        self.assertEqual(len(r["stale_groups"]), 1)

    def test_drawdown_lock_needs_user_resume(self):
        self.desk.submit(order(), CTX, chain(BASE))
        self.desk.mark("2026-10-26", chain(BASE))
        # 讓淨值掉 ~16%：空腳賣價飆到 3,300 點（-16 萬）
        r = self.desk.mark("2026-10-27", chain({(W4, "P", 46300): (3290, 3300, 5, 5), (W4, "P", 46100): (19, 20, 5, 5)}))
        self.assertEqual(r["dd_lock"], "reduced")
        self.assertEqual(self.desk.state.dd_lock, "reduced")
        self.desk.mark("2026-10-28", chain(BASE))                    # 淨值回來，鎖仍在
        self.assertEqual(self.desk.state.dd_lock, "reduced")
        self.desk.user_resume("使用者同意恢復")
        self.assertIsNone(self.desk.state.dd_lock)

    def test_halted_blocks_everything_new(self):
        self.desk.submit(order(), CTX, chain(BASE))
        self.desk.mark("2026-10-26", chain({(W4, "P", 46300): (5200, 5201, 5, 5), (W4, "P", 46100): (19, 20, 5, 5)}))
        self.assertEqual(self.desk.state.dd_lock, "halted")
        r = self.desk.submit(order(decided_at="2026-10-26T12:00:00" + TW), CTX, chain(BASE))
        self.assertFalse(r["ok"])
        self.assertTrue(any("全部停機" in x for x in r["reasons"]))

    def test_margin_cap_blocks_fill(self):
        self.desk.cfg["accounts"]["T0"]["capital"] = 1
        d = Desk(Path(self.tmp.name) / "tiny.jsonl", "T0", {**self.desk.cfg, "accounts": {"T0": {"capital": 100_000}}})
        r = d.submit(order(legs=[{"side": "sell", "cp": "P", "strike": 46300, "lots": 6}, {"side": "buy", "cp": "P", "strike": 46100, "lots": 6}]), CTX, chain(BASE))
        # 6x200x50=60,000 > 50% x 100,000
        self.assertEqual(r["result"], "no_fill")


class TestMisChain(unittest.TestCase):
    def test_chain_from_mis_rows(self):
        rows = [{"SymbolID": "TX442200J6-N", "CBestBidPrice": "10.0", "CBestAskPrice": "12.0", "CBestBidSize": "3", "CBestAskSize": "4",
                 "CDate": "20261026", "CTime": "100000"}]
        ch = chain_from_mis_rows(datetime(2026, 10, 26, 10, 0, 30).timestamp(), rows, CFG["quote_validity"])
        r, why = ch.usable(("202610W4", "C", 42200), "sell")
        self.assertEqual(r, (10.0, 3))


if __name__ == "__main__":
    unittest.main()
