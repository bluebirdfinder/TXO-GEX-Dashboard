r"""每日計價與到期結算（程式寫帳本，AI 不碰）。
  python daily_close.py T0 mark                      # 用當下 MIS 報價鏈做每日計價（mark-to-market）
  python daily_close.py T0 settle <到期代碼> <官方結算價>   # 到期結算；結算價必須是期交所官方公布值，由使用者或官方來源提供，程式不自己猜
  python daily_close.py T0 report                    # 唯讀：淨值、回撤、未平倉、掛單、已了結損益、REVIEW_FLAG
帳本在 C:\Users\mingi\txo-private\desk\<帳戶>\ledger.jsonl（不進 git）。"""
import sys
from datetime import datetime

import snapshot as sm
import sources
from book import Desk, load_config
from run_slot import PRIVATE, market_type


def main(argv):
    account, cmd = argv[1], argv[2]
    now = datetime.now(sources.TW).replace(microsecond=0)
    cfg = load_config()
    desk = Desk(PRIVATE / account / "ledger.jsonl", account, cfg)
    if cmd == "mark":
        rows = sources.live_chain(market_type(now))
        if not rows:
            print("沒有取得報價鏈，不計價（不補假價）")
            return
        s = sm.build_snapshot(now, account, None, None, [], rows)
        chain = sm.chain_from_snapshot(s, cfg["quote_validity"])
        print(desk.mark(now.date().isoformat(), chain))
    elif cmd == "settle":
        code, px = argv[3], float(argv[4])
        for e in desk.settle(code, px, now.date()):
            print(e["type"], e.get("gid") or "", e.get("cash_delta") or e.get("pnl"), e.get("note", ""))
    elif cmd == "report":
        st = desk.state
        print(f"淨值 {st.equity():,.0f}／本金 {st.capital:,.0f}／自高點回撤 {st.drawdown_pct():.1f}%／鎖定 {st.dd_lock or '無'}")
        print(f"未平倉 {len(st.groups)} 組、掛單 {len(st.resting())} 筆、已了結 {len(st.closed)} 筆、已實現（含費用）{st.realized:,.0f}")
        for e in desk.ledger.events():
            if e["type"] == "REVIEW_FLAG":
                print("檢討標記：", e["expiry"], f"{e['pct']:.1f}%", e["note"])
    else:
        raise SystemExit("指令：mark | settle <代碼> <結算價> | report")


if __name__ == "__main__":
    main(sys.argv)
