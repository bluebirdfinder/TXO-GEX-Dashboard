r"""會議室（最小版）：收盤後覆盤寫完，台選鳥、風控鳥、文書鳥開一場短會，把「下個時段的計畫」過一遍，留下逐段發言與會議紀錄。
流程（4 次 Claude 呼叫）：
  1. 台選鳥：報告下個時段計畫（依覆盤筆記與帳本）
  2. 風控鳥：第二層風控——挑毛病、說最壞情況、點出可能違反哪條紀律（只提意見，不能覆蓋程式紅線，也不改任何帳本）
  3. 台選鳥：回應（接受或不接受，並說明理由）
  4. 文書鳥：只整理——結論、分歧、待辦、需要使用者決定的事（不加判斷）
會議不下單、不改帳本；產出存成 JSON，顯示在 http://127.0.0.1:8770/meeting 。
之後有研究員時，把他們的報告當作會議資料、加進發言順序即可（見 agents.json）。
用法：python meeting.py T0 day|night      會議紀錄存在 C:\Users\mingi\txo-private\desk\<帳戶>\meetings\（不進 git）"""
import json
import sys
from datetime import datetime
from pathlib import Path

import review
import runner
import snapshot as sm
import sources
from book import Desk, load_config
from run_slot import PRIVATE, make_snapshot

COMMON = """你在「尋鳥交易室」的收盤後小會議裡發言。全部是【模擬】交易，使用者是交易約兩個月的新手：專有名詞先用一句白話解釋。
只能引用使用者訊息裡的數字與文字，不得編造資料，也不要自己計算損益（程式已算好）。用繁體中文，簡短有重點，不要輸出 JSON，不要加「完成 N%」。"""

SYSTEM = {
    "T0": "你是「台選鳥」，台指選擇權模擬交易員。" + COMMON + "\n你的任務依指示：報告計畫，或回應風控鳥的質疑（誠實承認被說中的地方，不要硬辯）。",
    "RISK": ("你是「風控鳥」，交易室的第二層風控。" + COMMON + "\n你的工作：挑毛病，不是附和。針對台選鳥的計畫與帳本，最多列 3 個風險點，每點固定三句："
             "『最壞情況（用元與點數說）』『可能違反哪條紀律（週選不拆單／暴衝不追價／賣腳 IV 分區距離／禁裸賣／停損要有數字／保證金與口數上限／停損盯不到時怎麼辦）』"
             "『如果發生建議怎麼做』。你只提意見，不能覆蓋程式紅線，也沒有下單權限。若沒有明顯風險，就明說並指出最該盯的一件事。"),
    "CLERK": ("你是「文書鳥」，書記。" + COMMON + "\n你只整理，不加判斷，沒有工具權限。請輸出四段（## 標題）：## 結論（3 點內）／## 分歧（誰不同意什麼；沒有就寫無）／"
              "## 待辦（誰、做什麼；只列會議上實際提到的）／## 需要使用者決定的事（每項附一句白話說明；沒有就寫「目前沒有需要使用者決定的事」）。"),
}
NAMES = {"T0": "台選鳥", "RISK": "風控鳥", "CLERK": "文書鳥"}


def latest_review_text(notes_dir):
    files = sorted(Path(notes_dir).glob("*.md"), reverse=True)
    return files[0].read_text(encoding="utf-8") if files else "（還沒有覆盤筆記）"


def context(snap, desk, review_text):
    g = snap["gex"] or {}
    ctx = sm.to_ctx(snap, desk.cfg["snapshot"])
    return f"""【會議時間】{snap['decided_at']}
【程式算好的帳戶數字】
{review.numbers_block(desk, None)}
【持倉與最近動作】
{runner.book_summary(desk)}
【行情與點位】現價 {runner._num(ctx['spot'])}；IV {runner._num(ctx['iv'], 2)}；GEX 買權牆 {runner._num(g.get('call_wall_strike'))}、賣權牆 {runner._num(g.get('put_wall_strike'))}、Zero Gamma {runner._num(g.get('zero_gamma_level'), 1)}、最大痛點 {runner._num(g.get('max_pain_strike'))}
九轉（15M/30M）：{json.dumps((snap.get('indicators') or {}).get('demark'), ensure_ascii=False)}
【最近一份覆盤與盤前規劃筆記】
{review_text}"""


def run_meeting(desk, snap, kind, meetings_dir, notes_dir, ask=runner.bridge_ask, model="sonnet"):
    """開一場會。資料缺漏就不開（不拿舊資料硬開）。回傳 {'status': 'written'|'skipped', ...}。"""
    missing = sm.check(snap, desk.cfg["snapshot"])
    if missing:
        return {"status": "skipped", "reasons": missing}
    done, nxt = review.KINDS[kind]
    base = context(snap, desk, latest_review_text(notes_dir))
    turns = []

    def say(who, instruction):
        convo = "\n\n".join(f"【{t['name']}】\n{t['text']}" for t in turns) or "（還沒有人發言）"
        text = ask(SYSTEM[who], f"{base}\n\n【到目前為止的會議發言】\n{convo}\n\n【輪到你】{instruction}", model).strip()
        turns.append({"speaker": who, "name": NAMES[who], "text": text})

    say("T0", f"用 5 點以內報告你對{nxt}的計畫：預期情境、什麼條件會動作、什麼條件不動、既有持倉怎麼處理。")
    say("RISK", "針對台選鳥的計畫與帳本挑毛病。")
    say("T0", "回應風控鳥的每一點：接受、部分接受或不接受，並說明理由；若計畫要調整，寫出調整後的重點。")
    say("CLERK", "整理這場會議。")
    minutes = turns[-1]["text"]
    meetings_dir = Path(meetings_dir)
    meetings_dir.mkdir(parents=True, exist_ok=True)
    stamp = snap["decided_at"].replace(":", "").replace("-", "").replace("+0800", "").replace("T", "_")
    path = meetings_dir / f"{stamp}_{kind}.json"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps({"id": path.stem, "kind": kind, "at": snap["decided_at"], "account": desk.account, "simulated": True,
                                "topic": f"{done}結束後：{nxt}計畫會議", "turns": turns, "minutes": minutes}, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"status": "written", "path": str(path)}


def main(argv):
    account, kind = argv[1], argv[2]
    if kind not in review.KINDS:
        raise SystemExit("kind 要是 day 或 night")
    s, cfg, _ = make_snapshot(account, f"{review.KINDS[kind][0]}後會議")
    desk = Desk(PRIVATE / account / "ledger.jsonl", account, cfg)
    sm.save(s, PRIVATE / account / "snapshots")
    print(run_meeting(desk, s, kind, PRIVATE / account / "meetings", PRIVATE / account / "notes"))


if __name__ == "__main__":
    main(sys.argv)
