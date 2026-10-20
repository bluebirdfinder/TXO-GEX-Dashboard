r"""規則巡邏（規格附錄 C.2「程式規則巡邏」）：交易時段內每隔一段時間用最新 MIS 報價鏈檢查
 掛單是否達條件成交、停損/停利是否觸發、掛單是否過期（全部由 book.process_quotes 處理，不花 AI 額度）；
 每個時段結束前後做一次每日計價（mark）。休市時什麼都不做（報價是凍結的，不能成交）。
用法：python monitor.py T0 [間隔秒=30]   （Ctrl+C 或關掉程序即停止；帳本在 C:\Users\mingi\txo-private\desk\<帳戶>\）"""
import json
import sys
import time
from datetime import datetime

import settlement
import snapshot as sm
import sources
from book import Desk, load_config
from run_slot import PRIVATE, market_type


def one_pass(desk, cfg, now, rows):
    """做一輪巡邏。回傳 process_quotes 的事件列表；休市或沒報價回 []。"""
    if sm.session_of(now) == "closed" or not rows:
        return []
    s = sm.build_snapshot(now, desk.account, None, None, [], rows)
    chain = sm.chain_from_snapshot(s, cfg["quote_validity"])
    return desk.process_quotes(chain)


def blind_groups(desk, cfg, now, rows, prev):
    """哪些持倉現在沒有有效報價（任一腳買賣價差過大/沒量/過舊）→ 停損盯不到。回傳 {gid: {since, reason}}。
    休市或沒報價時不更新（維持上次結果）。不估價、不補價，只標記讓帳戶頁與決策提示詞看得到。"""
    if sm.session_of(now) == "closed" or not rows:
        return prev
    chain = sm.chain_from_snapshot(sm.build_snapshot(now, desk.account, None, None, [], rows), cfg["quote_validity"])
    out = {}
    for g in desk.state.groups.values():
        cost, why = chain.close_cost([{**lg, "expiry": g["expiry"]} for lg in g["legs"]])
        if cost is None:
            out[g["gid"]] = {"since": (prev.get(g["gid"]) or {}).get("since", now.isoformat()), "reason": why}
    return out


def main(argv):
    account = argv[1]
    every = float(argv[2]) if len(argv) > 2 else 30.0
    cfg = load_config()
    desk = Desk(PRIVATE / account / "ledger.jsonl", account, cfg)
    last_mark = None
    blind = {}
    last_settle_check = 0.0
    print(f"規則巡邏 {account}，每 {every:.0f} 秒；Ctrl+C 結束", flush=True)
    while True:
        t0 = time.time()
        now = datetime.now(sources.TW).replace(microsecond=0)
        sess = sm.session_of(now)
        if sess != "closed":
            rows = sources.live_chain(market_type(now))
            for ev in one_pass(desk, cfg, now, rows):
                print(now.isoformat(), ev, flush=True)
            blind = blind_groups(desk, cfg, now, rows, blind)
            # 每個時段最後 3 分鐘做一次每日計價（日盤 13:42~13:45、夜盤 04:57~05:00）
            m = now.hour * 60 + now.minute
            if (13 * 60 + 42 <= m < 13 * 60 + 45 or 4 * 60 + 57 <= m < 5 * 60) and last_mark != (now.date(), sess) and rows:
                s = sm.build_snapshot(now, account, None, None, [], rows)
                print(now.isoformat(), "mark", desk.mark(now.date().isoformat(), sm.chain_from_snapshot(s, cfg["quote_validity"])), flush=True)
                last_mark = (now.date(), sess)
        if desk.state.active_expiries() and time.time() - last_settle_check > 300:       # 每 5 分鐘看一次官方有沒有公布最後結算價
            last_settle_check = time.time()
            for ev in settlement.settle_due(desk, now.date(), settlement.fetch_fsp()):
                print(now.isoformat(), "結算", ev.get("type"), ev.get("gid") or ev.get("expiry"), ev.get("cash_delta", ev.get("reason", "")), flush=True)
        (PRIVATE / account / "monitor_heartbeat.json").write_text(
            json.dumps({"epoch": time.time(), "at": now.isoformat(), "session": sess, "blind": blind}, ensure_ascii=False), encoding="utf-8")   # 給帳戶頁與決策提示詞看
        time.sleep(max(1.0, every - (time.time() - t0)))


if __name__ == "__main__":
    main(sys.argv)
