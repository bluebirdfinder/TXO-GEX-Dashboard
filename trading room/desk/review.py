r"""盤後覆盤與盤前規劃（規格第9節）：每個交易時段結束後，台選鳥用白話寫一份筆記——
  這個時段發生什麼、我做了什麼、有沒有守規則、學到什麼（只列「候選規則」，要你確認才進手冊）、下個時段的規劃。
這份筆記【不下單、不改帳本】，只存成文字檔並顯示在帳戶頁（http://127.0.0.1:8770/）。
 日盤結束後 13:50~15:00 寫「日盤覆盤＋夜盤規劃」；夜盤結束後 05:05~06:50 寫「夜盤覆盤＋日盤規劃」
 （K 線與現價資料只在收盤後 120 分鐘內算新鮮，過了就不寫，不拿舊資料硬寫）。
用法：python review.py T0 day|night        筆記存在 C:\Users\mingi\txo-private\desk\<帳戶>\notes\（不進 git）"""
import json
import sys
from datetime import datetime
from pathlib import Path

import runner
import snapshot as sm
import sources
from book import Desk, load_config
from run_slot import PRIVATE, make_snapshot

SYSTEM = """你是「台選鳥」，尋鳥戰情交易室的台指選擇權【模擬】交易員。現在是收盤後的覆盤與盤前規劃時間：你【不下單】，只用繁體中文白話寫筆記。
使用者是交易約兩個月的新手，專有名詞請先用一句白話解釋再用術語；只能引用使用者訊息裡的數字與帳本，不得編造沒有給你的資料，也不要自己計算損益（損益數字由程式算好給你）。

筆記請照下面六段，每段用「## 標題」：
## 1. 這個時段發生了什麼
行情走勢與關鍵價位（GEX 牆、Zero Gamma、最大痛點）；用 3~5 句講完。
## 2. 我做了什麼、結果如何
逐筆列出本時段的決策（引用決策編號）與成交、停損停利；沒有動作就說明為什麼觀望。損益直接引用【程式算好的數字】。
## 3. 有沒有守規則
對照鐵律（週選不拆單、暴衝不追價、賣腳 IV 分區距離、禁裸賣、停損要有數字）與你自己當初寫的「判斷錯的條件」逐項檢查，違反或擦邊就老實寫。
## 4. 候選規則（尚未生效，需要使用者確認才會進手冊）
最多 3 條，每條固定三欄：證據（引用決策編號或數字）／限制（樣本多小、只在什麼行情看過）／還不知道的。證據不足就寫「本時段沒有足夠證據產生候選規則」。
## 5. 下個時段規劃
你預期的情境（偏多/偏空/區間）與依據；哪些條件出現你會開倉或掛階梯、哪些條件你會保持不動；既有持倉的處理（停損線、要不要提早平倉）；最需要注意的風險。
## 6. 給新手的白話說明
挑本時段最重要的一個動作或不動作，用國中生也能懂的比喻解釋「為什麼這樣做」、最壞情況會虧多少、其他選擇是什麼。
不要輸出 JSON，不要在最後加「完成 N%」之類的字。"""

KINDS = {"day": ("日盤", "夜盤"), "night": ("夜盤", "日盤")}


def due_kind(now):
    """現在該不該寫筆記：回傳 'day' / 'night' / None。"""
    m = now.hour * 60 + now.minute
    if 13 * 60 + 50 <= m < 15 * 60:
        return "day"
    if 5 * 60 + 5 <= m < 6 * 60 + 50:
        return "night"
    return None


def note_key(now, kind):
    """同一個收盤後只寫一次：夜盤筆記算前一天開的那一盤，鍵用該盤的開盤日。"""
    from datetime import timedelta
    d = now.date() if kind == "day" else (now - timedelta(days=1)).date()
    return f"{d.isoformat()} {kind}"


def numbers_block(desk, kind):
    """程式算好的帳戶數字（AI 只能引用，不得自己算）。"""
    st = desk.state
    ev = desk.ledger.events()
    return "\n".join([
        f"本金 {st.capital:,.0f}；淨值（依最近一次計價）{st.equity():,.0f}；累計已實現（含費用）{st.realized:,.0f}；手續費稅累計 {st.fees_total:,.0f}",
        f"自高點回撤 {st.drawdown_pct():.2f}%；回撤鎖定：{st.dd_lock or '無'}；保證金占用 {st.margin_used():,.0f}",
        f"未平倉 {len(st.groups)} 組、掛單 {len(st.resting())} 筆、已了結 {len(st.closed)} 筆；帳本事件共 {len(ev)} 筆",
        "已了結明細：" + ("；".join(f"{c['gid']} {c['structure']} 損益 {c['pnl']:+.0f}（{c['reason']}）" for c in st.closed[-8:]) or "無"),
        "檢討標記：" + ("；".join(f"{e['expiry']} {e['pct']:.1f}%" for e in ev if e["type"] == "REVIEW_FLAG") or "無"),
    ])


def decisions_block(desk, n=15):
    lines = runner.recent_lines(desk, n)
    return "\n".join(lines) or "（還沒有任何決策）"


def build_review_prompt(snap, desk, kind, playbook=""):
    done, nxt = KINDS[kind]
    g = snap["gex"] or {}
    ctx = sm.to_ctx(snap, desk.cfg["snapshot"])
    return f"""現在是{done}結束後的覆盤與{nxt}盤前規劃。決策時間 {snap['decided_at']}。

【手冊】{snap.get('manual_ref')}
{playbook or '（手冊尚空）'}

【程式算好的帳戶數字】
{numbers_block(desk, kind)}

【你的持倉與最近動作】
{runner.book_summary(desk)}

【最近決策（新→舊，含編號請以帳本頁為準）】
{decisions_block(desk)}

【行情與點位】
現價 {runner._num(ctx['spot'])}；IV（期交所 VIX）{runner._num(ctx['iv'], 2)}
GEX：買權牆 {runner._num(g.get('call_wall_strike'))}、賣權牆 {runner._num(g.get('put_wall_strike'))}、Zero Gamma {runner._num(g.get('zero_gamma_level'), 1)}、最大痛點 {runner._num(g.get('max_pain_strike'))}、PC ratio {runner._num(g.get('pc_ratio'), 1)}（GEX 更新 {g.get('last_updated_time')}）
近 60 分鐘高低：{runner._num(max((b['high'] for b in snap['kbars_1m'][-60:]), default=None))} / {runner._num(min((b['low'] for b in snap['kbars_1m'][-60:]), default=None))}
九轉（15M/30M）：{json.dumps((snap.get('indicators') or {}).get('demark'), ensure_ascii=False)}

請依六段格式寫筆記。"""


def run_review(desk, snap, kind, notes_dir, playbook="", ask=runner.bridge_ask, model="sonnet"):
    """寫一份筆記。回傳 {'status': 'written'|'skipped', ...}。資料缺漏就不寫（不拿舊資料硬寫）。"""
    missing = sm.check(snap, desk.cfg["snapshot"])
    if missing:
        return {"status": "skipped", "reasons": missing}
    text = ask(SYSTEM, build_review_prompt(snap, desk, kind, playbook), model)
    notes_dir = Path(notes_dir)
    notes_dir.mkdir(parents=True, exist_ok=True)
    stamp = snap["decided_at"].replace(":", "").replace("-", "").replace("+0800", "").replace("T", "_")
    done, nxt = KINDS[kind]
    path = notes_dir / f"{stamp}_{kind}.md"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(f"# {done}覆盤＋{nxt}盤前規劃（{desk.account}，模擬）\n\n時間：{snap['decided_at']}　手冊：{snap.get('manual_ref')}\n"
                    f"（候選規則只是候選，要使用者確認才會進手冊；本筆記不下單、不改帳本）\n\n{text.strip()}\n", encoding="utf-8")
    return {"status": "written", "path": str(path)}


def main(argv):
    account, kind = argv[1], argv[2]
    if kind not in KINDS:
        raise SystemExit("kind 要是 day 或 night")
    s, cfg, book = make_snapshot(account, f"{KINDS[kind][0]}覆盤")
    desk = Desk(PRIVATE / account / "ledger.jsonl", account, cfg)
    sm.save(s, PRIVATE / account / "snapshots")
    print(run_review(desk, s, kind, PRIVATE / account / "notes", book))


if __name__ == "__main__":
    main(sys.argv)
