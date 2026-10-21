"""快照／缺資料檢查／決策執行器測試。注意：這裡的 GEX、K 線、報價全是【測試用假資料】，只用來驗證程式邏輯，不是行情。
執行：cd "trading room/desk" && python -m unittest discover -s tests -v"""
import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import runner                                  # noqa: E402
import snapshot as sm                          # noqa: E402
from book import Desk, load_config             # noqa: E402

CFG = load_config()
TW = "+08:00"
NOW = datetime.fromisoformat("2026-10-26T10:00:00" + TW)


def rows():
    def r(sym, bid, bs, ask, as_):
        return {"SymbolID": sym, "CBestBidPrice": bid, "CBestBidSize": bs, "CBestAskPrice": ask, "CBestAskSize": as_,
                "CTime": "", "CDate": ""}
    return [r("TX446300V6-O", "85", "5", "86", "5"), r("TX446100V6-O", "19", "5", "20", "5"),
            r("TX446700J6-O", "80", "5", "81", "5"), r("TX446900J6-O", "18", "5", "19", "5")]


def bars(n=90, end=NOW - timedelta(minutes=1), base=46500, step=0.0):
    out = []
    for i in range(n):
        t = end - timedelta(minutes=n - 1 - i)
        p = base + step * i
        out.append({"ts": t.strftime("%Y-%m-%d %H:%M"), "open": p, "high": p + 2, "low": p - 2, "close": p, "volume": 10})
    return out


GEX = {"date": "2026-10-26", "last_updated_time": "2026-10-26 08:55", "call_wall_strike": 47000.0, "put_wall_strike": 46000.0,
       "zero_gamma_level": 46200.0, "max_pain_strike": 46500.0, "spot_price": 46500.0, "pc_ratio": 80.0, "total_gex_val": 1000.0,
       "gex_chain_stale": False, "vix_info": {"taifex_vix": 12.0}, "dte_dates": {"w4": "10/28(三)結算"}}
SPOT = {"price": 46500.0, "ts": (NOW - timedelta(seconds=5)).isoformat(), "provider": "TEST"}


def snap(**kw):
    a = dict(now=NOW, account="T0", gex=copy.deepcopy(GEX), spot=dict(SPOT), kbars=bars(), chain_rows=rows(),
             indicators={}, tg_signals=None, manual_ref="playbook v0")
    a.update(kw)
    return sm.build_snapshot(**a)


def ladder_json(**kw):
    d = {"action": "place_ladder", "expiry": {"code": "202610W4"}, "thesis": "測試", "invalidation": "跌破 46000",
         "exit_plan": {"stop_debit_pts": 150, "take_profit_debit_pts": None},
         "side_sets": [{"direction": "bull_put", "rungs": [{"short_strike": 46300, "long_strike": 46100, "lots": 1, "min_credit_pts": 65}]}],
         "strategy_tag": "ladder_test", "account": "T1", "decided_at": "2020-01-01T00:00:00+08:00"}
    d.update(kw)
    return d


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.desk = Desk(self.dir / "t0.jsonl", "T0", copy.deepcopy(CFG))
        self.rules = self.desk.cfg["snapshot"]

    def tearDown(self):
        self.tmp.cleanup()


class TestSnapshot(Base):
    def test_complete_snapshot_has_no_missing(self):
        self.assertEqual(sm.check(snap(), self.rules), [])
        c = sm.to_ctx(snap(), self.rules)
        self.assertEqual((c["spot"], c["iv"], c["missing"]), (46500.0, 12.0, []))

    def test_missing_pieces_reported_not_filled(self):
        self.assertIn("GEX 點位", sm.check(snap(gex=None), self.rules))
        self.assertIn("台指期現價", sm.check(snap(spot=None), self.rules))
        self.assertIn("選擇權報價鏈", sm.check(snap(chain_rows=[]), self.rules))
        self.assertTrue(any("1 分 K 不足" in m for m in sm.check(snap(kbars=bars(10)), self.rules)))
        g = copy.deepcopy(GEX)
        del g["vix_info"]
        self.assertIn("IV（期交所 VIX）", sm.check(snap(gex=g), self.rules))

    def test_stale_data_flagged(self):
        g = copy.deepcopy(GEX)
        g["last_updated_time"] = "2026-10-25 08:55"
        self.assertTrue(any("GEX 過期" in m for m in sm.check(snap(gex=g), self.rules)))
        old = dict(SPOT, ts=(NOW - timedelta(seconds=120)).isoformat())
        self.assertTrue(any("現價過期" in m for m in sm.check(snap(spot=old), self.rules)))
        self.assertTrue(any("最後一根太舊" in m for m in sm.check(snap(kbars=bars(end=NOW - timedelta(minutes=10))), self.rules)))
        g2 = copy.deepcopy(GEX)
        g2["gex_chain_stale"] = True
        self.assertTrue(any("標示過期" in m for m in sm.check(snap(gex=g2), self.rules)))

    def test_future_bars_are_dropped(self):
        b = bars() + [{"ts": (NOW + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M"), "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
        s = snap(kbars=b)
        self.assertTrue(all(sm._parse_tw(x["ts"]) <= NOW for x in s["kbars_1m"]))
        self.assertNotEqual(s["kbars_1m"][-1]["close"], 1)

    def test_t0_never_sees_tg_signals(self):
        self.assertIsNone(snap(tg_signals=[{"x": 1}])["tg_signals"])
        self.assertEqual(snap(account="T1", tg_signals=[{"x": 1}])["tg_signals"], [{"x": 1}])

    def test_save_is_immutable_and_tamper_detected(self):
        s = snap()
        path, sha = sm.save(s, self.dir / "snaps")
        self.assertEqual(sm.load(path)["decided_at"], s["decided_at"])
        with self.assertRaises(FileExistsError):
            sm.save(s, self.dir / "snaps")
        import gzip
        o = json.loads(gzip.open(path, "rb").read().decode("utf-8"))
        o["snapshot"]["spot"]["price"] = 1.0
        with gzip.open(path, "wb") as f:
            f.write(json.dumps(o, ensure_ascii=False).encode("utf-8"))
        with self.assertRaises(ValueError):
            sm.load(path)

    def test_surge_definition(self):
        up = bars(base=46000, step=10)           # 90 根每根 +10，近 60 根：最新收盤 − 區間低點
        self.assertGreater(sm.surge_pts(up, 60), 500)
        dn = bars(base=47000, step=-10)
        self.assertLess(sm.surge_pts(dn, 60), -500)
        self.assertIsNone(sm.surge_pts([], 60))


class TestRunner(Base):
    def ask_with(self, obj_or_text):
        text = obj_or_text if isinstance(obj_or_text, str) else json.dumps(obj_or_text, ensure_ascii=False)
        self.calls = []

        def ask(system, question, model):
            self.calls.append((system, question))
            return text
        return ask

    def test_missing_data_means_no_decision_and_ai_not_called(self):
        ask = self.ask_with(ladder_json())
        r = runner.run_decision(self.desk, snap(gex=None), self.dir / "snaps", ask=ask)
        self.assertEqual(r["status"], "no_decision")
        self.assertEqual(self.calls, [])
        ev = [e for e in self.desk.ledger.events() if e["type"] == "NO_DECISION"]
        self.assertEqual(len(ev), 1)
        self.assertIn("無決策：缺 GEX 點位", ev[0]["reasons"])
        self.assertTrue(ev[0]["snapshot"] and ev[0]["sha256"])

    def test_good_ladder_is_submitted_and_linked(self):
        r = runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=self.ask_with(ladder_json()))
        self.assertEqual(r["status"], "submitted", r)
        self.assertTrue(r["result"]["ok"], r)
        types = [e["type"] for e in self.desk.ledger.events()]
        self.assertIn("SNAPSHOT_LINK", types)
        self.assertEqual(len(self.desk.state.groups), 1)         # 信用 65 達標，保守成交
        self.assertTrue(self.desk.ledger.verify()[0])

    def test_ai_cannot_choose_account_or_time(self):
        runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=self.ask_with(ladder_json()))
        dec = [e for e in self.desk.ledger.events() if e["type"] == "DECISION"][0]["decision"]
        self.assertEqual((dec["account"], dec["decided_at"]), ("T0", NOW.isoformat(timespec="seconds")))

    def test_garbage_reply_is_no_decision(self):
        r = runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=self.ask_with("我覺得可以做多"))
        self.assertEqual(r["status"], "no_decision")
        self.assertEqual(self.desk.state.groups, {})

    def test_surge_blocks_new_ladder_by_red_line(self):
        s = snap(kbars=bars(base=46000, step=10))                 # 近 60 分鐘急拉 > 500 點，沒有竭盡
        r = runner.run_decision(self.desk, s, self.dir / "snaps", ask=self.ask_with(ladder_json()))
        self.assertFalse(r["result"]["ok"])
        self.assertTrue(any("不追價" in x for x in r["result"]["reasons"]), r)

    def test_prompt_has_no_tg_for_t0_and_no_chat(self):
        runner.run_decision(self.desk, snap(tg_signals=[{"x": 1}]), self.dir / "snaps", ask=self.ask_with({"action": "no_trade", "thesis": "觀望"}))
        system, q = self.calls[0]
        self.assertNotIn("共振", q)
        self.assertIn("盤面快照", q)
        self.assertIn("不得引用快照以外", system)

    def test_parse_decision_variants(self):
        self.assertEqual(runner.parse_decision('```json\n{"action":"no_trade"}\n```')["action"], "no_trade")
        self.assertEqual(runner.parse_decision('好的 {"a": {"b": "}"}} 結束')["a"]["b"], "}")
        self.assertIsNone(runner.parse_decision("沒有 json"))
        self.assertIsNone(runner.parse_decision('{"a": '))

    def test_chain_table_lists_near_strikes(self):
        t = runner.chain_table(snap(), CFG["quote_validity"])
        self.assertIn("46300P 85(5) / 86(5)", t)
        self.assertIn("46700C", t)

    def test_chain_table_hides_invalid_quotes(self):
        bad = rows() + [{"SymbolID": "TX446500V6-O", "CBestBidPrice": "16", "CBestBidSize": "3", "CBestAskPrice": "0", "CBestAskSize": "0", "CTime": "", "CDate": ""},
                        {"SymbolID": "TX446400V6-O", "CBestBidPrice": "20", "CBestBidSize": "1", "CBestAskPrice": "500", "CBestAskSize": "1", "CTime": "", "CDate": ""}]
        t = runner.chain_table(snap(chain_rows=bad), CFG["quote_validity"])
        self.assertNotIn("46500P", t)        # 沒有賣價
        self.assertNotIn("46400P", t)        # 買賣價差過大
        self.assertIn("46300P", t)


class TestReplay(Base):
    def test_replay_uses_only_past_data_and_runs_pipeline(self):
        import csv
        import gzip
        import replay
        rec = self.dir / "chain.jsonl.gz"
        with gzip.open(rec, "wt", encoding="utf-8") as f:
            f.write(json.dumps({"ts": NOW.isoformat(), "mt": "0", "q": rows()}, ensure_ascii=False) + "\n")
        gdir = self.dir / "gex"
        gdir.mkdir()
        (gdir / "20261026_0855.json").write_text(json.dumps(GEX), encoding="utf-8")
        future = dict(GEX, call_wall_strike=99999.0)
        (gdir / "20261026_1030.json").write_text(json.dumps(future), encoding="utf-8")      # 決策時間之後的 GEX，不可被用到
        kb = self.dir / "k.csv"
        with open(kb, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ts", "open", "high", "low", "close", "volume", "contract"])
            for b in bars() + [{"ts": (NOW + timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M"), "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]:
                w.writerow([b["ts"], b["open"], b["high"], b["low"], b["close"], b["volume"], "202610"])
        calls = []

        def ask(system, question, model):
            calls.append(question)
            return json.dumps(ladder_json())
        st = replay.replay(rec, gdir, kb, self.dir / "out", 30, ask=ask)
        self.assertEqual((st["snapshots"], st["submitted"], st["no_decision"]), (1, 1, 0), st)
        self.assertIn("買權牆 47,000", calls[0])
        self.assertNotIn("99,999", calls[0])
        self.assertNotIn("收盤：1 ", calls[0])

    def test_replay_stale_inputs_all_blocked(self):
        import gzip
        import replay
        rec = self.dir / "chain.jsonl.gz"
        with gzip.open(rec, "wt", encoding="utf-8") as f:
            f.write(json.dumps({"ts": NOW.isoformat(), "mt": "0", "q": rows()}) + "\n")
        gdir = self.dir / "gex"
        gdir.mkdir()
        kb = self.dir / "k.csv"
        kb.write_text("ts,open,high,low,close,volume,contract\n", encoding="utf-8")
        st = replay.replay(rec, gdir, kb, self.dir / "out", 30)
        self.assertEqual((st["submitted"], st["no_decision"]), (0, 1))
        self.assertIn("GEX 點位", st["reasons"])


class TestClosedSession(Base):
    """收盤後（13:45-15:00、05:00-08:45）決策：K 線/現價用剛收完那一盤；報價鏈凍結，不得成交。"""
    T = datetime.fromisoformat("2026-10-26T14:00:00" + TW)

    def closed_snap(self, **kw):
        end = self.T.replace(hour=13, minute=44)
        a = dict(now=self.T, kbars=bars(end=end), spot=dict(SPOT, ts=end.isoformat()))
        a.update(kw)
        return snap(**a)

    def test_session_of(self):
        f = lambda h, m: sm.session_of(NOW.replace(hour=h, minute=m))
        self.assertEqual([f(8, 44), f(8, 45), f(13, 44), f(13, 45), f(14, 59), f(15, 0), f(4, 59), f(5, 0)],
                         ["closed", "day", "day", "closed", "closed", "night", "night", "closed"])

    def test_closed_session_accepts_just_closed_bars(self):
        self.assertEqual(sm.check(self.closed_snap(), self.rules), [])
        self.assertEqual(sm.to_ctx(self.closed_snap(), self.rules)["session"], "closed")

    def test_closed_session_still_rejects_very_old_bars(self):
        old = self.closed_snap(kbars=bars(end=self.T - timedelta(hours=5)))
        self.assertTrue(any("最後一根太舊" in m for m in sm.check(old, self.rules)))

    def test_closed_session_ladder_placed_but_not_filled(self):
        calls = []

        def ask(system, question, model):
            calls.append(question)
            return json.dumps(ladder_json(valid_until="2026-10-27T05:00:00" + TW))
        r = runner.run_decision(self.desk, self.closed_snap(), self.dir / "snaps", ask=ask)
        self.assertTrue(r["result"]["ok"], r)
        self.assertEqual(self.desk.state.groups, {})                  # 凍結報價不成交
        self.assertEqual(len(self.desk.state.resting()), 1)           # 掛單等開盤
        self.assertIn("目前時段：休市中", calls[0])

    def test_closed_session_blocks_open_and_close(self):
        d = {"action": "open", "expiry": {"code": "202610W4"}, "structure": "bull_put_spread", "strategy_tag": "t",
             "legs": [{"side": "sell", "cp": "P", "strike": 46300, "lots": 1}, {"side": "buy", "cp": "P", "strike": 46100, "lots": 1}],
             "thesis": "t", "invalidation": "i", "exit_plan": {"stop_debit_pts": 150, "take_profit_debit_pts": None}}
        r = runner.run_decision(self.desk, self.closed_snap(), self.dir / "snaps", ask=lambda s, q, m: json.dumps(d))
        self.assertFalse(r["result"]["ok"])
        self.assertTrue(any("休市時段" in x for x in r["result"]["reasons"]), r)


class TestMisKbars(unittest.TestCase):
    def test_front_month_symbol_rolls_after_settlement(self):
        import sources
        f = lambda y, mo, d, h, mi, suf="F": sources.front_month_symbol(datetime(y, mo, d, h, mi, tzinfo=sources.TW), suf)
        self.assertEqual(f(2026, 10, 19, 10, 0), "TXFJ6-F")
        self.assertEqual(f(2026, 10, 21, 13, 0), "TXFJ6-F")           # 結算日 13:30 前還是十月
        self.assertEqual(f(2026, 10, 21, 14, 0), "TXFK6-F")           # 結算日 13:30 後換十一月
        self.assertEqual(f(2026, 12, 30, 10, 0, "M"), "TXFA7-M")      # 十二月過了結算日→隔年一月

    def test_end_labels_converted_to_start_and_forming_bar_dropped(self):
        import sources
        now = datetime(2026, 10, 20, 1, 20, 19, tzinfo=sources.TW)
        fake = lambda sym: {"Ticks": [["011900", "1", "2", "0", "1", "1"], ["012000", "1", "2", "0", "1", "1"], ["012100", "1", "2", "0", "1", "1"]]}
        self.assertEqual([b["ts"] for b in sources.live_kbars_mis(now, fetch=fake)], ["2026-10-20 01:18", "2026-10-20 01:19"])

    def test_midnight_crossing_dates(self):
        import sources
        now = datetime(2026, 10, 20, 0, 1, 30, tzinfo=sources.TW)
        fake = lambda sym: {"Ticks": [["235800", "1", "2", "0", "1", "1"], ["000000", "1", "2", "0", "1", "1"], ["000100", "1", "2", "0", "1", "1"]]}
        self.assertEqual([b["ts"] for b in sources.live_kbars_mis(now, fetch=fake)], ["2026-10-19 23:57", "2026-10-19 23:59", "2026-10-20 00:00"])

    def test_fetch_failure_returns_empty_not_fake(self):
        import sources

        def boom(sym):
            raise OSError("network")
        self.assertEqual(sources.live_kbars_mis(NOW, fetch=boom), [])


class TestPatrol(Base):
    """盤中 AI 巡邏的觸發條件（純函式）與一次完整呼叫。"""
    def st(self, **kw):
        a = {"last_call": 0.0, "last_price": None, "last_seq": 0, "calls": {}, "blind_seen": []}
        a.update(kw)
        return a

    def at(self, h, m):
        return datetime.fromisoformat(f"2026-10-26T{h:02d}:{m:02d}:00" + TW)

    def test_closed_session_never_calls(self):
        import patrol
        self.assertEqual(patrol.decide_trigger(self.st(), self.at(14, 0), 46500, [], [], self.desk.cfg), (False, "休市"))

    def test_first_check_waits_for_open_delay(self):
        import patrol
        self.assertFalse(patrol.decide_trigger(self.st(), self.at(8, 48), 46500, [], [], self.desk.cfg)[0])
        ok, why = patrol.decide_trigger(self.st(), self.at(8, 51), 46500, [], [], self.desk.cfg)
        self.assertTrue(ok)
        self.assertIn("第一次", why)

    def test_interval_price_move_and_cap(self):
        import patrol
        t_last = self.at(9, 0).timestamp()
        base = self.st(last_call=t_last, last_price=46500.0)
        c = self.desk.cfg
        self.assertFalse(patrol.decide_trigger(base, self.at(9, 20), 46510, [], [], c)[0])              # 才 20 分鐘、價沒動
        self.assertTrue(patrol.decide_trigger(base, self.at(9, 31), 46510, [], [], c)[0])               # 超過 30 分鐘
        ok, why = patrol.decide_trigger(base, self.at(9, 10), 46680, [], [], c)                         # 移動 180 點、隔 10 分鐘
        self.assertTrue(ok)
        self.assertIn("移動", why)
        self.assertFalse(patrol.decide_trigger(base, self.at(9, 2), 46700, [], [], c)[0])              # 移動大但才隔 2 分鐘（冷卻中）
        capped = self.st(last_call=t_last, calls={"2026-10-26": c["patrol"]["max_calls_per_day"]})
        self.assertFalse(patrol.decide_trigger(capped, self.at(10, 0), 46500, [], [], c)[0])

    def test_rule_patrol_events_and_blind_trigger(self):
        import patrol
        c = self.desk.cfg
        t_last = self.at(9, 0).timestamp()
        base = self.st(last_call=t_last, last_price=46500.0, last_seq=5)
        stop = {"seq": 6, "type": "CLOSE"}
        own_fill = {"seq": 7, "type": "FILL", "oid": None}
        resting_fill = {"seq": 8, "type": "FILL", "oid": "T0-O1"}
        self.assertFalse(patrol.decide_trigger(base, self.at(9, 10), 46500, [own_fill], [], c)[0])      # 自己決策的成交不算
        ok, why = patrol.decide_trigger(base, self.at(9, 10), 46500, [stop], [], c)
        self.assertTrue(ok)
        self.assertIn("CLOSE", why)
        self.assertTrue(patrol.decide_trigger(base, self.at(9, 10), 46500, [resting_fill], [], c)[0])
        self.assertFalse(patrol.decide_trigger(base, self.at(9, 1), 46500, [stop], [], c)[0])           # 事件冷卻 2 分鐘內不重複叫
        ok, why = patrol.decide_trigger(base, self.at(9, 10), 46500, [], ["T0-G1"], c)
        self.assertTrue(ok)
        self.assertIn("停損盯不到", why)
        seen = self.st(last_call=t_last, last_price=46500.0, blind_seen=["T0-G1"])
        self.assertFalse(patrol.decide_trigger(seen, self.at(9, 10), 46500, [], ["T0-G1"], c)[0])        # 已通知過的不再重複叫

    def test_run_once_updates_state_and_counts_calls(self):
        import patrol
        sp = self.dir / "patrol_state.json"
        res = patrol.run_once("T0", self.desk.cfg, self.desk, "測試觸發", sp, snapshot_fn=lambda a, r, c: (snap(), c, "（手冊）"),
                              ask=lambda s_, q, m: json.dumps({"action": "no_trade", "thesis": "觀望"}), snap_dir=self.dir / "snaps")
        self.assertEqual(res["status"], "submitted")
        st = patrol.load_state(sp)
        self.assertEqual(st["calls"], {datetime.now(sm.TW).date().isoformat(): 1})
        self.assertEqual(st["last_price"], 46500.0)
        self.assertGreaterEqual(st["last_seq"], 1)

    def test_prompt_shows_wake_reason_and_recent_actions(self):
        runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=lambda s_, q, m: json.dumps(ladder_json()))
        s2 = snap(sources={"slot": "現價較上次決策移動 +180 點"})
        p = runner.build_prompt(s2, self.desk, "", self.desk.cfg["snapshot"])
        self.assertIn("被叫醒的原因】現價較上次決策移動 +180 點", p)
        self.assertIn("你最近的動作", p)
        self.assertIn("place_ladder", p)
        self.assertIn("請不要引用", p)


class TestReview(Base):
    def test_due_windows(self):
        import review
        f = lambda h, m: review.due_kind(datetime.fromisoformat(f"2026-10-26T{h:02d}:{m:02d}:00" + TW))
        self.assertEqual([f(13, 49), f(13, 50), f(14, 59), f(15, 0), f(5, 4), f(5, 5), f(6, 49), f(6, 50), f(10, 0)],
                         [None, "day", "day", None, None, "night", "night", None, None])

    def test_note_key_night_uses_previous_day(self):
        import review
        t = datetime.fromisoformat("2026-10-27T05:30:00" + TW)
        self.assertEqual(review.note_key(t, "night"), "2026-10-26 night")
        self.assertEqual(review.note_key(datetime.fromisoformat("2026-10-26T14:00:00" + TW), "day"), "2026-10-26 day")

    def test_missing_data_skips_without_calling_ai(self):
        import review
        calls = []
        r = review.run_review(self.desk, snap(gex=None), "day", self.dir / "notes", ask=lambda s_, q, m: calls.append(1) or "x")
        self.assertEqual(r["status"], "skipped")
        self.assertEqual(calls, [])
        self.assertFalse((self.dir / "notes").exists())

    def test_note_written_with_programmatic_numbers_and_no_orders(self):
        import review
        runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=lambda s_, q, m: json.dumps(ladder_json()))
        before = len(self.desk.ledger.events())
        seen = {}

        def ask(system, question, model):
            seen["system"], seen["q"] = system, question
            return "## 1. 這個時段發生了什麼\n測試筆記"
        r = review.run_review(self.desk, snap(), "day", self.dir / "notes", ask=ask)
        self.assertEqual(r["status"], "written")
        self.assertTrue(Path(r["path"]).read_text(encoding="utf-8").startswith("# 日盤覆盤＋夜盤盤前規劃"))
        self.assertEqual(len(self.desk.ledger.events()), before)                 # 覆盤不改帳本
        self.assertIn("程式算好的帳戶數字", seen["q"])
        self.assertIn("不下單", seen["system"])
        self.assertIn("候選規則", seen["system"])
        self.assertIn("不得編造", seen["system"])


SAMPLE_FSP_HTML = """<table><tbody>
<TR bgcolor="#FFFFFF" class="12bk"><TD width="14%" align=middle>2026/10/28</TD><TD align=middle>202610W4</TD><TD align=right>46,200</TD><TD align=right>-</TD><TD align=right>-</TD></TR>
<TR><TD>2026/10/12</TD><TD>202610F2</TD><TD>49359</TD><TD>-</TD><TD>-</TD></TR>
<TR><TD>2026/09/16</TD><TD>202609</TD><TD>45759</TD><TD>2882.9</TD><TD>3619.2</TD></TR>
<TR><TD>2026/11/04</TD><TD>202611W1</TD><TD>-</TD><TD>-</TD><TD>-</TD></TR>
<TR><TD>日期</TD><TD>契約月份</TD><TD>x</TD></TR></tbody></table>"""


class TestSettlement(Base):
    def open_position(self):
        runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=lambda s_, q, m: json.dumps(ladder_json()))
        self.assertEqual(len(self.desk.state.groups), 1)

    def test_parse_official_page(self):
        import settlement
        from datetime import date
        d = settlement.parse_fsp(SAMPLE_FSP_HTML)
        self.assertEqual(d["202610W4"], (date(2026, 10, 28), 46200.0))
        self.assertEqual(d["202609"], (date(2026, 9, 16), 45759.0))
        self.assertNotIn("202611W1", d)                  # 結算價是「-」的略過
        self.assertEqual(len(d), 3)

    def test_settles_only_after_official_publication(self):
        import settlement
        from datetime import date
        self.open_position()
        fsp = settlement.parse_fsp(SAMPLE_FSP_HTML)
        self.assertEqual(settlement.settle_due(self.desk, date(2026, 10, 27), fsp), [])               # 還沒到期日
        self.assertEqual(settlement.settle_due(self.desk, date(2026, 10, 28), {}), [])                 # 到期日但官方還沒公布
        ev = settlement.settle_due(self.desk, date(2026, 10, 28), fsp)                                  # 官方公布：46,200 → 兩腳都價外
        self.assertEqual([e["type"] for e in ev], ["SETTLE"])
        self.assertEqual(self.desk.state.groups, {})
        self.assertEqual(self.desk.state.closed[0]["reason"], "到期結算")

    def test_official_date_earlier_than_computed_is_skipped_not_forced(self):
        import settlement
        from datetime import date
        self.open_position()
        ev = settlement.settle_due(self.desk, date(2026, 10, 27), {"202610W4": (date(2026, 10, 26), 46200.0)})
        self.assertEqual(ev[0]["type"], "SKIP")
        self.assertEqual(len(self.desk.state.groups), 1)


class TestMeetingAndHub(Base):
    def test_meeting_flow_order_and_minutes(self):
        import meeting
        runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=lambda s_, q, m: json.dumps(ladder_json()))
        before = len(self.desk.ledger.events())
        calls = []

        def ask(system, question, model):
            calls.append((system[:12], question))
            return f"第{len(calls)}段發言"
        r = meeting.run_meeting(self.desk, snap(), "day", self.dir / "meet", self.dir / "notes", ask=ask)
        self.assertEqual(r["status"], "written")
        m = json.loads(Path(r["path"]).read_text(encoding="utf-8"))
        self.assertEqual([t["speaker"] for t in m["turns"]], ["T0", "RISK", "T0", "CLERK"])
        self.assertEqual(m["minutes"], "第4段發言")
        self.assertTrue(m["simulated"])
        self.assertEqual(len(calls), 4)
        self.assertIn("第1段發言", calls[1][1])                          # 風控鳥看得到台選鳥的發言
        self.assertIn("第2段發言", calls[2][1])                          # 台選鳥回應時看得到風控鳥的質疑
        self.assertEqual(len(self.desk.ledger.events()), before)         # 開會不改帳本
        self.assertIn("程式算好的帳戶數字", calls[0][1])

    def test_meeting_skipped_without_data(self):
        import meeting
        called = []
        r = meeting.run_meeting(self.desk, snap(gex=None), "day", self.dir / "meet", self.dir / "notes", ask=lambda *a: called.append(1) or "x")
        self.assertEqual((r["status"], called), ("skipped", []))

    def test_agents_registry_is_valid(self):
        reg = json.loads((Path(__file__).resolve().parent.parent / "agents.json").read_text(encoding="utf-8"))
        ids = [a["id"] for k in ("traders", "researchers", "support") for a in reg[k]]
        self.assertEqual(len(ids), len(set(ids)))
        for a in reg["traders"] + reg["researchers"]:
            self.assertIn(a["status"], ("active", "planned"))
            if a["status"] == "planned":
                self.assertTrue(a.get("blocked_by"), a["id"])            # 規劃中的角色一定寫清楚缺什麼
        self.assertEqual([t["name"] for t in reg["traders"] if t["status"] == "active"], ["台選鳥"])

    def test_hub_and_meetings_api(self):
        import server
        acct = self.dir / "T0"
        acct.mkdir()
        Desk(acct / "ledger.jsonl", "T0", copy.deepcopy(CFG))
        (acct / "meetings").mkdir()
        (acct / "meetings" / "a.json").write_text(json.dumps({"id": "a", "at": "2026-10-26T14:00:00+08:00", "turns": [], "minutes": "m"}), encoding="utf-8")
        server.PRIVATE, server.live_rows, server.services = self.dir, (lambda now: []), (lambda account="T0": {})
        h = server.hub()
        t0 = next(t for t in h["traders"] if t["id"] == "T0")
        self.assertEqual(t0["summary"]["positions"], 0)
        self.assertEqual(t0["summary"]["equity"], 1000000.0)
        self.assertEqual(server.meetings("T0")[0]["minutes"], "m")


class TestMonitorSpreadThreshold(Base):
    """已持有部位（損益/停損/平倉）用較寬的買賣價差門檻；新開倉與掛單成交仍用 20 點。"""
    def wide_rows(self, ask=250):
        return [{"SymbolID": "TX446300V6-O", "CBestBidPrice": "199", "CBestBidSize": "5", "CBestAskPrice": str(ask), "CBestAskSize": "5"},
                {"SymbolID": "TX446100V6-O", "CBestBidPrice": "49", "CBestBidSize": "5", "CBestAskPrice": "50", "CBestAskSize": "5"}]

    def chain_of(self, rows_):
        return sm.chain_from_snapshot(snap(chain_rows=rows_), self.desk.cfg["quote_validity"])

    def test_close_cost_accepts_moderately_wide_spread_but_entry_does_not(self):
        c = self.chain_of(self.wide_rows(ask=240))          # 賣腳價差 41 點：> 20、≤ 60
        cost, why = c.close_cost([{"expiry": "202610W4", "cp": "P", "strike": 46300, "side": "sell", "lots": 1},
                                  {"expiry": "202610W4", "cp": "P", "strike": 46100, "side": "buy", "lots": 1}])
        self.assertEqual((cost, why), (240 - 49, None))                                    # 最保守：賣腳付賣價、買腳收買價
        self.assertIsNone(c.spread_credit("202610W4", "P", 46300, 46100)[0])                # 新成交判定仍然拒絕
        self.assertEqual(c.leg_price(("202610W4", "P", 46300), "sell")[0], None)

    def test_too_wide_still_invalid_for_monitoring(self):
        c = self.chain_of(self.wide_rows(ask=500))          # 價差 301 點 > 60：視為假報價
        cost, why = c.close_cost([{"expiry": "202610W4", "cp": "P", "strike": 46300, "side": "sell", "lots": 1}])
        self.assertIsNone(cost)
        self.assertIn("買賣價差過大", why)

    def test_stop_triggers_with_wide_but_acceptable_spread(self):
        import monitor
        runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=lambda s_, q, m: json.dumps(ladder_json()))
        self.assertEqual(len(self.desk.state.groups), 1)
        out = monitor.one_pass(self.desk, self.desk.cfg, NOW + timedelta(minutes=1), self.wide_rows(ask=240))   # 平倉成本 191 ≥ 停損 150
        self.assertEqual(out[0][0], "stop")
        self.assertEqual(self.desk.state.groups, {})


class TestMisLabelQuirk(unittest.TestCase):
    def test_minute_60_label_skipped(self):
        import sources
        now = datetime(2026, 10, 21, 5, 3, tzinfo=sources.TW)
        fake = lambda sym: {"Ticks": [["045800", "1", "2", "0", "1", "1"], ["045900", "1", "2", "0", "1", "1"], ["046000", "9", "9", "9", "9", "9"], ["050000", "1", "2", "0", "1", "1"]]}
        got = sources.live_kbars_mis(now, fetch=fake)
        self.assertEqual([b["ts"] for b in got], ["2026-10-21 04:57", "2026-10-21 04:58", "2026-10-21 04:59"])
        self.assertTrue(all(b["close"] != 9 for b in got))


class TestMonitorPass(Base):
    def test_stop_triggers_in_session_but_not_when_closed(self):
        import monitor
        run = runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=lambda s_, q, m: json.dumps(ladder_json()))
        self.assertEqual(len(self.desk.state.groups), 1, run)
        crash = [{"SymbolID": "TX446300V6-O", "CBestBidPrice": "199", "CBestBidSize": "5", "CBestAskPrice": "200", "CBestAskSize": "5"},
                 {"SymbolID": "TX446100V6-O", "CBestBidPrice": "49", "CBestBidSize": "5", "CBestAskPrice": "50", "CBestAskSize": "5"}]
        closed_now = datetime.fromisoformat("2026-10-26T14:00:00" + TW)
        self.assertEqual(monitor.one_pass(self.desk, self.desk.cfg, closed_now, crash), [])         # 休市不處理
        self.assertEqual(len(self.desk.state.groups), 1)
        out = monitor.one_pass(self.desk, self.desk.cfg, NOW + timedelta(minutes=1), crash)           # 盤中：平倉成本 151 ≥ 150 → 停損
        self.assertEqual(out[0][0], "stop")
        self.assertEqual(self.desk.state.groups, {})

    def test_blind_group_flagged_and_shown_in_prompt(self):
        import monitor
        runner.run_decision(self.desk, snap(), self.dir / "snaps", ask=lambda s_, q, m: json.dumps(ladder_json()))
        wide = [{"SymbolID": "TX446300V6-O", "CBestBidPrice": "199", "CBestBidSize": "5", "CBestAskPrice": "500", "CBestAskSize": "5"},
                {"SymbolID": "TX446100V6-O", "CBestBidPrice": "49", "CBestBidSize": "5", "CBestAskPrice": "50", "CBestAskSize": "5"}]
        t1 = NOW + timedelta(minutes=1)
        b1 = monitor.blind_groups(self.desk, self.desk.cfg, t1, wide, {})
        self.assertEqual(list(b1), ["T0-G1"])
        b2 = monitor.blind_groups(self.desk, self.desk.cfg, t1 + timedelta(minutes=5), wide, b1)
        self.assertEqual(b2["T0-G1"]["since"], b1["T0-G1"]["since"])               # 起算時間不會被洗掉
        self.assertEqual(monitor.blind_groups(self.desk, self.desk.cfg, t1 + timedelta(minutes=6), rows(), b2), {})   # 報價恢復就解除
        # 休市不更新
        closed = datetime.fromisoformat("2026-10-26T14:00:00" + TW)
        self.assertEqual(monitor.blind_groups(self.desk, self.desk.cfg, closed, wide, b1), b1)
        # 提示詞會告訴台選鳥「停損盯不到」
        hb = Path(self.desk.ledger.path).parent / "monitor_heartbeat.json"
        hb.write_text(json.dumps({"epoch": 0, "at": "x", "blind": b1}), encoding="utf-8")
        self.assertIn("停損盯不到", runner.book_summary(self.desk))


if __name__ == "__main__":
    unittest.main()
