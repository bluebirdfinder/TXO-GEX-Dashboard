# 交接：JJ 大戶散戶動能還原＋報價服務／runner（2026-10-17 寫，給 10/19 週一開盤接手的新視窗）

> GEX 點位（牆位發版、Max Pain、Lumi 往來）**不在這份**，由視窗「GEX 週選點位修正交接」處理。這份只管 **JJ 錄製／還原** 與 **本機報價服務／runner**。
> 接手第一件事：開 Remote Control（`set_remote_control` self=true）。

## 1. 最重要的 5 件事
| # | 事項 | 狀態 |
|---|---|---|
| 1 | **週一 10/19 開盤前**推送 `claude/log-all-trades`（484b782）並重啟報價服務，讓每一筆成交都寫進 `trades_YYYYMMDD.jsonl`（窮舉紅黃線的原料） | 未推送，要先問使用者 |
| 2 | 推送 `claude/store-backup-fix`（bd0f95a）：排程備份「同一天第二次」會 PermissionError 的 bug | 未推送，要先問使用者 |
| 3 | **週一起累積 JJ 頁面錄製**：台指期為主，加台積電期／聯電期／小型台積電，用 JJ 圖表內部資料取樣 | 週一開始 |
| 4 | 整天驗證綠線（含夜盤、其他商品）；用完整成交流窮舉紅線、黃線 | 待做 |
| 5 | 收盤後跑 `audit_vs_official.py --sample 0`；確認週六 05:30 klines 排程有跑 | 待做 |

## 2. 分支（都在共用倉庫，用分支名就能看到；**都沒推送**）
| 分支 | commit | 內容 |
|---|---|---|
| `claude/log-all-trades` | 484b782 | 每個成交封包都記錄；`flush_trade_frames()` 在記錄迴圈裡寫 `trades_YYYYMMDD.jsonl`（含逐筆價量、買賣價、當下累計 `total`） |
| `claude/store-backup-fix` | bd0f95a | `local_data_store` 的 OneDrive 備份改逐檔覆蓋，不再 `shutil.rmtree`（17 個測試） |
已在 main：看門狗（沒訊息 180 秒重連、再卡 150 秒且 uptime>600 就 `os._exit(3)` 讓外殼 15 秒後重啟；成交頻道 10 分鐘無資料也重連；含國定假日交易時段判斷）、runner 拋棄式 checkout＋本機資料庫 `~\.txo_local_store`、`auto_update.yml` 的 `ref: main`。
推送規則：先問使用者；先 `gh run list --workflow auto_update.yml --limit 1` 確認 `completed`；用暫時 worktree；只 add 自己的檔案。

## 3. JJ 還原進度（公式與細節只放私有資料夾，公開 repo 不放）
私有資料夾 `C:\Users\mingi\txo-private\jj_momentum\`：`FINDINGS_20261015.md`（完整紀錄）、`jj_TXF_1m_20261014_history.csv`。記憶檔 `reference_jj_sampling_method.md` 有取樣方法。
| 線 | 進度 |
|---|---|
| 綠（散戶成交筆差） | **已破解（部分驗證）**：＝交易所累計「外盤成交筆數 − 內盤成交筆數」＝富邦成交頻道每筆附帶的 `total.totalBidMatch − total.totalAskMatch`，取該分鐘 K 棒收盤（start+60s）的值。台指期 10/16 早盤 32 根相關 +0.98。待驗證：整天、夜盤、其他商品 |
| 紅（大戶委託口差？）、黃（市場委託口差？） | **未解**。去趨勢後與成交衍生量相關僅 0.3～0.65；五檔頻道沒有委託筆數／總量，MIS 也沒有。若來自成交資料可窮舉；若是全市場委託簿總量就拿不到原料（要如實回報） |
**窮舉做法**：收集 1～3 個完整交易日 `trades_*.jsonl`＋JJ 5 分線歷史；在私有資料夾寫腳本，掃「門檻（口數／名目）×筆數或口數×累計或滾動視窗」，用**去趨勢（變化量）相關**評分，另一天樣本外驗證。累計序列的相關會被趨勢灌水，不可當證據。
**取樣方法**：JJ 圖表在同源 iframe，`document.querySelector('iframe').contentWindow.chartWidget.model().model().dataSources()` 找 `title(true)==='大戶散戶動能'`，`.data()` 的 `firstIndex()/lastIndex()/valueAt(i)` 回 `[bar時間, 紅, 綠, 黃]`。1 分線只載入約 300～1,000 根、5 分線 300 根（約 25 小時），要長歷史用 5 分線。即時取樣用 Web Worker 計時。切商品：點左上商品框→**先 Ctrl+A**→輸入→點第一筆（可輸入中文，例如「台積電」，小型的會自己跑出來）。JS 輸出約 1,000 字會被截斷要分段，字串含 `n=` 會被過濾器擋。JJ 值約每 20 秒更新。

## 4. 使用者的規則（必讀）
- **JJ 網站**：使用者開了一個「Claude 測試」面板給我用，可儲存編輯；**另外三個 Q 姐的面板絕對不要動、不要按儲存、不要蓋掉版面、不要調整 Chrome 視窗大小**（會讓 JJ 重新整理，取樣器清空）。
- 錄製時：使用者會把 Chrome 留在最上面；盡量不用電腦操作功能（截圖會暫時隱藏使用者其他視窗）；視窗被遮住圖例 DOM 會過期，所以用圖表內部資料。
- 使用者看不到 .md：文件要同時給 HTML（`SendUserFile`）或貼在對話；要決定的事用 **AskUserQuestion 卡片**；任何任務回報**完成百分比**；進度用表格、流程用 code block 圖。
- 使用者不在時只做不影響線上的事；**報價服務卡死可自己重啟**（已授權）。其他一律不推送。
- 紅線（`AGENTS.md`）：不偽造資料、不建議追價／拆週選價差單；指標公式只放私有資料夾。

## 5. 踩過的坑
1. `git checkout -- .` 會把未提交成果還原掉（曾弄丟牆位改動）。寫完就 commit 到自己的分支。
2. 調 Chrome 視窗大小 → JJ 重新整理 → 取樣器清空。
3. PowerShell 沒有 heredoc；含中文／反斜線的腳本用 Write 寫成檔再跑。
4. 背景常駐 python 本機伺服器、繞過瀏覽器區域網路權限、部分 runner git 操作會被自動模式擋，**不要繞過**，回報使用者。
5. 看門狗曾只看「任何訊息」漏掉成交頻道死亡（10/15 20:24～23:38 台指期／台積電期／聯電期無成交，五檔正常）；已補成交頻道檢查。
6. 15 秒快照只涵蓋約 91% 成交量，所以才要 `log-all-trades`。
7. runner 在 OneDrive 之外是故意的；舊 `git pull --rebase` 與雲端同寫 `klines_cache.json` 必衝突，已改拋棄式 checkout。

## 6. 建議接手順序
```
週末  1. 開 Remote Control → git fetch → list_sessions（GEX 視窗在跑，別碰它的檔案）
      2. 讀本檔、CLAUDE.md、AGENTS.md、記憶、私有 FINDINGS
      3. 驗證：報價服務在線、feed 新鮮、runner 乾淨、兩個分支都在
      4. AskUserQuestion：推送 log-all-trades＋store-backup-fix？何時重啟？
週一  5. 08:30 前：推送、重啟、確認 trades_20261019.jsonl 開始寫入
      6. 開盤：JJ「Claude 測試」面板取樣（台指期為主，穿插台積電期／聯電期／小型台積電）
      7. 收盤後：整天驗證綠線→窮舉紅黃→audit_vs_official.py --sample 0
```
