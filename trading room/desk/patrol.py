r"""盤中 AI 巡邏（規格附錄 C.2「AI 巡邏」）：日盤與夜盤交易時段內，台選鳥依行情自由決定要不要下單。
 兩層巡邏：規則巡邏（monitor.py：停損停利、掛單成交，不花額度）＋ AI 巡邏（本檔）。
 本檔每分鐘做一次「便宜的檢查」（只看現價與帳本），只有符合觸發條件才組快照、叫台選鳥一次：
   1. 時段開始後第一次檢查（開盤後 first_delay_min 分鐘）
   2. 距上次叫它超過 min_interval_min 分鐘
   3. 現價較上次決策移動 ≥ move_trigger_pts 點（至少隔 cooldown_min 分鐘）
   4. 規則巡邏有新動作（停損/停利/掛單成交/掛單過期），或有持倉變成「停損盯不到」（至少隔 event_cooldown_min 分鐘）
 每天最多叫 max_calls_per_day 次（保護你的 Claude 額度）。休市時什麼都不做（盤後覆盤見 review.py）。
用法：python patrol.py T0        帳本與狀態在 C:\Users\mingi\txo-private\desk\<帳戶>\（不進 git）"""
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import meeting
import review
import runner
import snapshot as sm
import sources
from book import Desk, load_config
from run_slot import PRIVATE, make_snapshot

EVENT_TYPES = {"CLOSE", "SETTLE", "ORDER_END"}


def session_open_time(now):
    """目前這個交易時段的開始時刻（日盤 08:45、夜盤 15:00）；休市回 None。"""
    s = sm.session_of(now)
    if s == "closed":
        return None
    if s == "day":
        return now.replace(hour=8, minute=45, second=0, microsecond=0)
    return (now if now.hour >= 15 else now - timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)


def load_state(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"last_call": 0.0, "last_price": None, "last_seq": 0, "calls": {}, "blind_seen": []}


def save_state(path, st):
    Path(path).write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def new_events(events, last_seq):
    """上次叫 AI 之後，規則巡邏新產生的動作（停損/停利/掛單成交/掛單過期）。FILL 只算由掛單成交的（oid 不為空）。"""
    out = []
    for e in events:
        if e["seq"] <= last_seq:
            continue
        if e["type"] in EVENT_TYPES or (e["type"] == "FILL" and e.get("oid")):
            out.append(e)
    return out


def decide_trigger(st, now, price, events, blind, cfg):
    """回傳 (要不要叫 AI, 原因)。純函式，方便測試。st 是狀態 dict（不會被修改）。"""
    p = cfg["patrol"]
    if sm.session_of(now) == "closed":
        return False, "休市"
    today = now.date().isoformat()
    if st["calls"].get(today, 0) >= p["max_calls_per_day"]:
        return False, f"今天已叫 {p['max_calls_per_day']} 次，達上限"
    since = now.timestamp() - st["last_call"]
    opened = session_open_time(now)
    first = st["last_call"] < opened.timestamp()          # 這個時段還沒叫過
    if first:
        if now >= opened + timedelta(minutes=p["first_delay_min"]):
            return True, "時段開始後的第一次檢查"
        return False, "時段剛開始，等開盤穩定"
    ev = new_events(events, st["last_seq"])
    fresh_blind = [g for g in blind if g not in st.get("blind_seen", [])]
    if (ev or fresh_blind) and since >= p["event_cooldown_min"] * 60:
        if ev:
            return True, "規則巡邏有新動作：" + "、".join(sorted({e["type"] for e in ev}))
        return True, "持倉沒有有效報價，停損盯不到：" + "、".join(fresh_blind)
    if price is not None and st["last_price"] is not None and abs(price - st["last_price"]) >= p["move_trigger_pts"] and since >= p["cooldown_min"] * 60:
        return True, f"現價較上次決策移動 {price - st['last_price']:+.0f} 點"
    if since >= p["min_interval_min"] * 60:
        return True, f"距上次已 {int(since // 60)} 分鐘"
    return False, "沒有觸發"


def run_once(account, cfg, desk, reason, state_path, snapshot_fn=make_snapshot, ask=runner.bridge_ask, snap_dir=None):
    """叫台選鳥一次並更新狀態。回傳 run_decision 的結果。"""
    s, cfg, book = snapshot_fn(account, reason, cfg)
    res = runner.run_decision(desk, s, snap_dir or PRIVATE / account / "snapshots", playbook=book, ask=ask)
    st = load_state(state_path)
    now = datetime.now(sources.TW)
    st["last_call"] = now.timestamp()
    sp = (s.get("spot") or {}).get("price")
    if sp is not None:
        st["last_price"] = sp
    st["last_seq"] = max((e["seq"] for e in desk.ledger.events()), default=0)
    day = now.date().isoformat()
    st["calls"] = {day: st["calls"].get(day, 0) + 1}      # 只留當天，避免檔案越長越大
    st["blind_seen"] = list(load_blind(account))
    save_state(state_path, st)
    return res


def load_blind(account):
    try:
        return list((json.loads((PRIVATE / account / "monitor_heartbeat.json").read_text(encoding="utf-8")).get("blind") or {}))
    except (OSError, ValueError):
        return []


def main(argv):
    account = argv[1]
    cfg = load_config()
    desk = Desk(PRIVATE / account / "ledger.jsonl", account, cfg)
    state_path = PRIVATE / account / "patrol_state.json"
    print(f"AI 巡邏 {account}：每分鐘檢查一次，符合觸發條件才叫台選鳥；Ctrl+C 結束", flush=True)
    while True:
        t0 = time.time()
        try:
            now = datetime.now(sources.TW).replace(microsecond=0)
            kind = review.due_kind(now)
            if kind:                                    # 收盤後：寫覆盤與盤前規劃（不下單），每個時段一次
                st = load_state(state_path)
                key = review.note_key(now, kind)
                if key not in st.get("reviews", []):
                    print(now.isoformat(), "寫覆盤筆記：", key, flush=True)
                    s, cfg2, book = make_snapshot(account, f"{review.KINDS[kind][0]}覆盤", cfg)
                    sm.save(s, PRIVATE / account / "snapshots")
                    res = review.run_review(desk, s, kind, PRIVATE / account / "notes", book)
                    print(now.isoformat(), json.dumps(res, ensure_ascii=False)[:300], flush=True)
                    if res.get("status") == "written":                # 筆記寫好後開一場短會（台選鳥、風控鳥、文書鳥）
                        try:
                            mres = meeting.run_meeting(desk, s, kind, PRIVATE / account / "meetings", PRIVATE / account / "notes")
                            print(now.isoformat(), "會議：", json.dumps(mres, ensure_ascii=False)[:300], flush=True)
                        except Exception as e:  # noqa: BLE001
                            print(now.isoformat(), "會議失敗：", type(e).__name__, str(e)[:200], flush=True)
                    st = load_state(state_path)
                    att = st.get("review_attempts", {})
                    att[key] = att.get(key, 0) + 1
                    st["review_attempts"] = {k: v for k, v in att.items() if k in (key, *st.get("reviews", [])[-3:])}
                    if res.get("status") == "written" or att[key] >= 3:        # 寫成功，或最多試 3 次（資料缺漏就放棄，不拿舊資料硬寫）
                        st["reviews"] = (st.get("reviews", []) + [key])[-6:]
                    save_state(state_path, st)
            if sm.session_of(now) != "closed":
                st = load_state(state_path)
                spot = sources.live_spot()
                price = spot["price"] if spot else None
                ok, reason = decide_trigger(st, now, price, desk.ledger.events(), load_blind(account), cfg)
                if ok:
                    print(now.isoformat(), "叫台選鳥：", reason, flush=True)
                    res = run_once(account, cfg, desk, reason, state_path)
                    print(now.isoformat(), res.get("status"), json.dumps(res.get("result") or res.get("reasons"), ensure_ascii=False, default=str)[:300], flush=True)
        except Exception as e:  # noqa: BLE001 - 巡邏不能因為單次失敗就死掉
            print(datetime.now().isoformat(), "巡邏錯誤：", type(e).__name__, str(e)[:200], flush=True)
        time.sleep(max(5.0, 60.0 - (time.time() - t0)))


if __name__ == "__main__":
    main(sys.argv)
