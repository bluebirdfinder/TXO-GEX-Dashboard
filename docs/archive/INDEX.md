# docs/archive 索引（平常不用讀；要查「當時發生什麼」才來翻）

這裡的檔案**只搬不刪**，內容保持原樣。目前的現況與待辦只看根目錄的 [HANDOFF.md](../../HANDOFF.md)。
整理日期：2026-10-30。整理原則：按時間排序、重點併入現行檔、舊檔歸檔。

## handoffs/（交接單，依時間排序）

| 日期 | 檔案 | 它是什麼 | 現在的狀態 |
|---|---|---|---|
| 2026-08-20 | [HANDOVER_REWRITE_SPEC_v44_20260820.md](handoffs/HANDOVER_REWRITE_SPEC_v44_20260820.md) | v44.0 時期的完整功能與官方資料網址手冊 | 早已過期（現行為 v64.x）；官方網址地圖已由 [PROJECT_HANDOVER.md](../../PROJECT_HANDOVER.md) 第三節接手 |
| 2026-10-04 | [HANDOFF_20261004_長期背景版.md](handoffs/HANDOFF_20261004_長期背景版.md) | 原 `HANDOFF.md`（9/30～10/13 的 A～T 事項長表、資安事件、踩坑） | 已完成項目屬歷史，**未完成項目已併入新 [HANDOFF.md](../../HANDOFF.md) 第 2 節**；已完成項目的根因與驗證在 [HISTORY.md](../../HISTORY.md) |
| 2026-10-08 | [HANDOFF_THREE_CHATS_20261008.md](handoffs/HANDOFF_THREE_CHATS_20261008.md) | 三個聊天室（戰情室使用者體驗、ADX 縮放、夜盤價格驗證）統整 | 事項多已做完；未完成者已併入 HANDOFF.md |
| 2026-10-13 | [HANDOFF_GEX_V2_20261013.md](handoffs/HANDOFF_GEX_V2_20261013.md) | 老墨 GEX 研究、GEX 範圍盤點、通行版 v2 並行累積的原始任務與指令 | **仍是 v2 回測的操作說明**，要重跑回測時讀它；結論見 [docs/GEX_V2_BACKTEST_20261009.md](../GEX_V2_BACKTEST_20261009.md) |
| 2026-10-16 | [HANDOFF_20261016.md](handoffs/HANDOFF_20261016.md) | 投稿時間線（10/21 截止、10/24 分享）、官方對帳、加權漲跌修正、不要碰的 Lumi 檔 | 投稿已過；未完成技術項併入 HANDOFF.md |
| 2026-10-17 | [HANDOFF_20261017.md](handoffs/HANDOFF_20261017.md) | 幕僚鳥＋記憶、ADX Pro V3 對齊、週末現價、**架構事實（8000 是 runner 的 clone 等）** | 架構事實已併入 HANDOFF.md 第 1、5 節 |
| 2026-10-21 | [HANDOFF_20261021.md](handoffs/HANDOFF_20261021.md)、[.html](handoffs/HANDOFF_20261021.html) | 發表截止日當天的修正與現況（md 為精簡版、html 為完整排版版，主題與重點事項相同） | 投稿已過；未完成技術項併入 HANDOFF.md |

## 沒有放進這裡、但你可能在找的

| 檔案 | 位置與原因 |
|---|---|
| `HANDOFF_20261022.html`（10/22 交接單，群益 API、8001 靜態服務、幕僚鳥逾時修法） | 未被 git 追蹤，仍在共用資料夾根目錄；內容已併入 HANDOFF.md。**含使用者個人財務敘述，不可 commit 進公開 repo** |
| 台選鳥交易室的 `HANDOFF_20261019/20261021*`、`DECISIONS_20261020`、`RESEARCH_LIBRARY_DRAFT`、`brain/desk/playbook.md` | 只在分支 `worktree-option-quote-recorder`（`.claude/worktrees/option-quote-recorder/`），該分支刻意不推公開 repo |
| `.claude/worktrees/` 其他 4 個資料夾、`scratch/` | 9/16、8 月與 4 月的舊專案複本（共約 140 份 md；逐檔比對雜湊，4 個 9/16 worktree 的檔案都是現行檔的較舊版本），不是文件；移除要用 git 指令且要先確認無未 commit 內容，見 HANDOFF.md 第 2-2 節 #21 |

## 為什麼 STATUS.md／HISTORY.md／PROJECT_HANDOVER.md／README.md 沒有搬

`scripts/bump_version.py` 與 `AGENTS.md` 第 1 條紅線把這四個檔案寫死在根目錄（升版時會同步改它們的版本字串）。要搬就得先改腳本與紅線，風險大於好處，所以維持原位。
