r"""決策時段腳本：抓即時資料 → 快照 → 台選鳥決策 → 下單簿。全部是模擬單。
用法（每個時段手動或排程呼叫一次）：
  python run_slot.py T0 <時段名> [--dry]
  時段名只是標籤（日盤收盤後/夜盤收盤後/開盤後檢查…），寫進快照 sources；--dry＝只抓資料、存快照、檢查缺漏，不叫 AI。
帳本與快照放使用者私有資料夾（不進 git）：C:\Users\mingi\txo-private\desk\<帳戶>（資料夾）
"""
import sys
from datetime import datetime
from pathlib import Path

import indicators
import runner
import snapshot as sm
import sources
from book import Desk, load_config

PRIVATE = Path(r"C:\Users\mingi\txo-private\desk")
PLAYBOOK = Path(__file__).resolve().parent.parent / "brain" / "desk" / "playbook.md"       # gitignored；使用者確認後才寫入


def market_type(now):
    m = now.hour * 60 + now.minute
    return "0" if 8 * 60 + 45 <= m < 13 * 60 + 45 else "1"


def read_playbook():
    if PLAYBOOK.exists():
        text = PLAYBOOK.read_text(encoding="utf-8")
        first = text.splitlines()[0] if text else ""
        return first.strip("# ").strip() or "playbook", text
    return "playbook v0", "（手冊尚空：只有程式紅線與使用者 2026-10-19/20 的決定，沒有經驗規則。）"


def make_snapshot(account, slot, cfg=None):
    """抓即時資料組成快照。回傳 (快照, 設定, 手冊全文)。資料抓不到的欄位如實留空，由 snapshot.check 判斷。"""
    now = datetime.now(sources.TW).replace(microsecond=0)
    cfg = cfg or load_config()
    ref, book = read_playbook()
    bars = sources.live_kbars_mis(now, limit=1000) or sources.live_kbars(now)       # 期交所 MIS 官方 1 分 K 優先；失敗才用 8000 的富邦累積檔
    ind = indicators.build_indicators(bars, {"15M": sources.live_cache_tf("15M"), "30M": sources.live_cache_tf("30M")},
                                      indicators.load_private(), cfg["snapshot"]["demark_recent_bars"], cfg["snapshot"]["demark_require_perfection"])
    s = sm.build_snapshot(now, account, sources.live_gex(), sources.live_spot(), bars, sources.live_chain(market_type(now)),
                          indicators=ind, manual_ref=ref, sources={"slot": slot, "gex": "github main / 8000", "kbars": "TAIFEX MIS getChartData1M（備援 8000 klines_cache）",
                                                   "spot": "8000 live_tick", "chain": "TAIFEX MIS getQuoteList"})
    return s, cfg, book


def main(argv):
    account, slot = argv[1], argv[2]
    dry = "--dry" in argv
    s, cfg, book = make_snapshot(account, slot)
    if dry:
        path, sha = sm.save(s, PRIVATE / account / "snapshots")
        print("快照", path, "缺漏：", sm.check(s, cfg["snapshot"]) or "無")
        return
    desk = Desk(PRIVATE / account / "ledger.jsonl", account, cfg)
    print(runner.run_decision(desk, s, PRIVATE / account / "snapshots", playbook=book))


if __name__ == "__main__":
    main(sys.argv)
