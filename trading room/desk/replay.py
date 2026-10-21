"""重放模式（階段 0/2 驗證用，不當成績）：拿已記錄的報價鏈檔，照時間一份份走一遍「快照→檢查→決策→下單簿」，
確認程式流程、缺資料攔截、擋未來資料都正常。AI 預設換成固定回覆（觀望），不花額度；也可傳入自己的 ask。
用法：python replay.py <報價紀錄.jsonl.gz> <GEX檔或資料夾> <TX_1m.csv> <輸出資料夾> [每幾分鐘一次=30]"""
import json
import sys
from datetime import timedelta
from pathlib import Path

import runner
import snapshot as sm
import sources
from book import Desk, load_config


def hold_ask(system, question, model):
    return json.dumps({"action": "no_trade", "thesis": "重放模式固定回覆：觀望（不花 AI 額度）"}, ensure_ascii=False)


def replay(recorded, gex_src, kbar_csv, outdir, every_min=30, ask=hold_ask, account="T0", cfg=None):
    cfg = cfg or load_config()
    outdir = Path(outdir)
    desk = Desk(outdir / "ledger.jsonl", account, cfg)
    gx = sources.GexArchive(gex_src) if Path(gex_src).is_dir() else None
    last = None
    stats = {"snapshots": 0, "no_decision": 0, "submitted": 0, "reasons": {}}
    for now, rows in sources.iter_recorded_chain(recorded):
        if last is not None and now - last < timedelta(minutes=every_min):
            continue
        last = now
        gex = gx.at(now) if gx else sources.gex_from_file(gex_src, now)
        bars = sources.load_kbars(kbar_csv, now)
        s = sm.build_snapshot(now, account, gex, sources.spot_from_kbars(bars), bars, rows, manual_ref="replay",
                              sources={"mode": "replay", "recorded": str(recorded)})
        r = runner.run_decision(desk, s, outdir / "snapshots", ask=ask)
        stats["snapshots"] += 1
        stats[r["status"]] += 1
        for m in r.get("reasons", []):
            k = m.split("（")[0]          # 去掉「幾分鐘前/哪一根」之類的變動細節，方便統計
            stats["reasons"][k] = stats["reasons"].get(k, 0) + 1
    return stats


if __name__ == "__main__":
    a = sys.argv
    print(json.dumps(replay(a[1], a[2], a[3], a[4], float(a[5]) if len(a) > 5 else 30), ensure_ascii=False, indent=2))
