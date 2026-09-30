# HANDOFF.md — TXO-GEX-Dashboard 交接單（唯一真相來源）

> 每次交接前更新並 commit。新視窗只需讀：`CLAUDE.md`（含「多視窗守則」）、本檔、`AGENTS.md`、[docs/LOCAL_EXECUTION_INVENTORY.md](docs/LOCAL_EXECUTION_INVENTORY.md)（哪些功能鎖在 Windows 本機、哪些能搬雲端）。
> HISTORY.md 很長，**只讀最新兩三個條目**（用 grep／指定行數），不要整份讀入。
> 最後更新：2026-09-30 凌晨，因 context 視窗快滿（非額度用盡）交接。origin/main 在 `5ef4878`（v64.17）。
> 這份文件之前有整整 4 天（9/26～9/30，v64.5～v64.17）沒有回頭更新，內容已完全過期，這次是**整份重寫**，不是增補。舊內容如果需要考古，去看 git log 這個檔案的歷史。

## 0. 開工前檢查（每次，不要跳過）

1. `git fetch origin`，確認本機落後多少；main 會被 GitHub Actions 每天自動推資料 commit。
2. `git status`：**共用資料夾（`C:\Users\mingi\OneDrive\文件\TXO-GEX-Dashboard`）目前落後 origin/main 97 個 commit（還停在 9/26 的 `39d04e6`），且有 8 個檔案未 commit**（見第 2 節）。這些未 commit 的檔案是舊版本，**不要當作現況參考、不要 stash／覆蓋／刪除**。
3. 用 `list_sessions` 確認有沒有其他視窗指向同一資料夾且正在執行。
4. 改檔／commit／push 一律用暫時 worktree（`.claude/skills/multi-session-safety/SKILL.md`），不要直接在共用資料夾裡動 git 狀態。**push 前先問使用者。**
5. 本檔「已驗證／已完成」是前一個視窗的自述，動工前抽樣重跑確認。

## 1. 🔴 最優先：CVD 驗證仍在進行中，接手第一件事

分支 `claude/cvd-verify`（本機分支，**未 push**，base 是 origin/main + merge 了 `claude/cvd-real-tick`）：

- 已修好兩個 bug（commit `61884e3`）：①前端傳 UI 代號（`TXF`/`MXF`/`MTX`/`TMF`），後端訂閱與比對卻用富邦別名（`TXF1!`/`MXF1!`/`TMF1!`），兩者從沒對上過，CVD 分頁永遠誤報「尚未連上」；②後端只訂閱了 TXF 一檔，MXF/MTX/TMF 完全沒訂閱。兩個都已修好並用真實富邦登入驗證過映射正確。
- **邏輯已驗證**（模擬交易資料手算比對）：tick-rule 買賣方向判斷、累積值計算、時間戳遞增、換場次重置，全部正確。
- **還沒驗證的**：真實成交進來後，累積值是否合理（凌晨夜盤成交稀疏，等了近 1 小時沒等到一筆）。**這是唯一卡住發版的事**，不需要重寫程式，純粹是等時機（交易時段內、有成交量時）。
- 測試環境：暫存 worktree `C:\Users\mingi\AppData\Local\Temp\txo-wt-cvd2-4364`（可能已被系統清掉，不影響——bug 修復已經 commit 在 `claude/cvd-verify` 分支了，不依賴那個資料夾）。若要重新起測試伺服器：另開 worktree、把 `scripts/live_price_server.py` 的 `PORT = 8000` 那行改成讀 `TXO_GATEWAY_PORT` 環境變數（已經改過，見分支），用 `TXO_GATEWAY_PORT=8001` 跑，避免動到正式常駐的 8000 埠。
- **接手步驟**：①確認現在是交易時段（日盤 08:45–13:45 或夜盤 15:00–05:00）；②起測試伺服器（見上）；③輪詢 `http://localhost:8001/api/cvd?symbol=TXF` 直到 `series` 不是 `null`；④打開戰情室、切到 CVD 分頁，跟真實市場走勢對一下是否合理；⑤通過後把 `claude/cvd-verify` 合併進 v64.18、發版、push（先問使用者）。

## 2. 🔴🔴 資安事件（已處理，但要知道發生過什麼）

2026-09-30 凌晨發現：共用資料夾（落後 97 個 commit，還是 v64.12 資安修補之前的版本）裡的 `scripts/live_price_server.py`，從 **9/29 08:50 就被執行，監聽 `0.0.0.0:8000`**（對整個區網開放，會外洩 `.env` 富邦 API 金鑰與憑證密碼），跑了約 16 小時。已立即終止該進程（PID 13924、34700）。**正式排程的安全版本**（`C:\Users\mingi\txo-klines-runner`，只綁 `127.0.0.1`）**全程沒受影響、一直在正常運作**。

**推測根因**：共用資料夾裡有舊視窗留下的未 commit 修改（見第 3 節），使用者或某個視窗在這個過時資料夾裡手動執行了 `live_price_server.py`。

**使用者已知情並決定**：富邦金鑰因為只在家用網路開過，先不換。**這個決定是基於「舊版有漏洞」的既有認知**——這次新發現的是「跑了 16 小時」這個更具體的時長，如果使用者想重新評估，可以再問一次要不要換金鑰，但除非使用者主動提起，不用每次交接都重提。

## 3. 共用資料夾內「別人未 commit 的檔案」（不要 stash／覆蓋／刪除）

落後 97 個 commit，且有這些未 commit 的修改（來源不明，可能是造成第 2 節資安事件的舊視窗）：

| 檔案 | 備註 |
|---|---|
| `scripts/fubon_api_provider.py`、`scripts/live_price_server.py` | **極可能是沒有資安修補的舊版本**——main 上（v64.12 起）已經有正確、安全的版本，共用資料夾這份不要當參考，也不要 commit |
| `trading room/room.js` | 舊版 CVD／弱火箭相關修改，main 上已有更完整版本 |
| `scripts/build_screener_cache.py` | 舊版 |
| `SELF_AUDIT_FINDINGS_TODO.md` | 舊版標記 |
| `data/stock_futures_large_trader_cache.json`、`data/twse_t86_cache.json` | 本機 pipeline 快取，不在 CI `git add` 清單，本來就不該 commit |

**建議**：找機會把共用資料夾同步到 origin/main（`git fetch` + 使用者確認後 `git reset --hard origin/main`，**這會丟掉上面這些過時的未 commit 檔案**，先跟使用者確認這些檔案裡沒有他想保留的東西）。目前還沒做這件事，因為沒把握這些檔案裡有沒有使用者還想要的內容。

## 4. 待辦：動能鳥邏輯搬離公開 repo（已決定方案，還沒動手）

使用者已決定：改放本機私有資料夾執行（比照 CVD／K 線模式），**不改寫 git 歷史**。技術路線已確認可行——查證後發現 `build_screener_cache.py` 本來就不在雲端排程裡（一直是手動執行），所以這個搬遷不影響任何現有自動化。

**具體要做的**（完全還沒開始，只查過函式位置）：
1. 把 `scripts/jj_ghost_claws.py` 整份、以及 `scripts/build_screener_cache.py` 裡的 `compute_jj_macd_and_cci`（377行起）、`compute_5k_breakout`（548行起）、`compute_demark_v3`（680行起）搬到使用者私有資料夾（建議 `C:\Users\mingi\txo-private\screener-indicators\`，比照 SMC 的模式）。
2. `build_screener_cache.py` 改成從私有資料夾 import，路徑錯誤時要清楚報錯（不要靜默失敗）。
3. `scripts/tv_indicators_engine.py`（未被任何地方引用，且與 Pine 邏輯不一致）——確認真的沒人用之後可以直接砍掉，私有資料夾留一份備份。
4. 驗證：跑一次 `build_screener_cache.py`，跟現有 `data/screener_cache.json` 的訊號分布比對，確認搬遷沒改變任何計算結果。
5. `room.js` 前端字串已在 v64.17 全改成「動能鳥」，**使用者部署新版 Worker 後**，記得移除 `room.js` 裡對 `indicator=jj`（舊路由）的暫時備援，改成只打 `indicator=bird`。

## 5. 待辦：`.git` 歷史肥大（新發現，未處理）

`.git` 資料夾已經 **645M**，持續肥大中（每天多次把資料檔案完整 commit 進去，沒有清除機制）。使用者已表態不想改寫公開 repo 歷史，所以「squash 舊 commit」這條路目前不能用。處理方式（git-lfs／資料檔案搬去外部儲存／其他）**尚未討論，需要使用者決定方向**。詳見 [docs/LOCAL_EXECUTION_INVENTORY.md](docs/LOCAL_EXECUTION_INVENTORY.md) 第三節。

## 6. SMC（已上線 v64.15，等使用者部署 Worker）

- 演算法（Python 參考版＋Worker 用 JS 版）在使用者電腦 `C:\Users\mingi\txo-private\smc\`（**不在 git**，`README_SMC.md` 有部署步驟與 TradingView 核對清單）。
- 前端「🧠 SMC」按鈕已上線，**Worker 尚未加入 `indicator=smc` 前不會畫圖，也不會報錯**。
- 待使用者：①把 `C:\Users\mingi\OneDrive\文件\TradingView 指標\我寫的指標\ADX MTF 後端運算 (Cloudflare Worker)\worker.js` 全文貼到 Cloudflare 並 Deploy（已含 `indicator=smc`／`indicator=bird`，原檔備份 `worker.js.bak_before_smc_20260927`）；②用 TradingView 核對 `README_SMC.md` 的事件清單。

## 7. 本機常駐排程現況（一切正常運作中，不用動）

- `TXO-Fubon-Futures-Klines`：每天 05:30／14:00 累積富邦期貨日內 K，`C:\Users\mingi\txo-klines-runner`，日誌同目錄 `logs\fubon_klines.log`。富邦只給「最近一個場次」，錯過補不回來，每次執行看 `data/klines_gap_report.json`。
- `TXO-Live-Price-Server`：登入 Windows 即背景啟動，只綁 `127.0.0.1:8000`，掛掉自動重啟，看門狗每天 08:30／14:55 重新登入、交易時段 120 秒沒報價也會重登。日誌 `logs\live_price_server.log`。
- 兩者都在 `C:\Users\mingi\txo-klines-runner`（獨立於 OneDrive 共用資料夾的乾淨 clone），停用用 `Unregister-ScheduledTask -TaskName <name> -Confirm:$false`。

## 8. 其他仍待處理，不急

- `live_price_server.py` 的 SSL 仍是 `CERT_NONE`（其他腳本已在 v64.11 改為驗證憑證）。
- 2027 休市日曆待官方公布。
- 通行碼字串仍寫在 `app.js`／`scripts/encrypt.py`／`scripts/fetch_and_calc_vision.py`（v64.16 只從 README/STATUS 文件移除，未改程式，頁面預設自動通關本來就不是實質保護）。

## 9. 風控與溝通偏好（不變）

核心風控見 `AGENTS.md`。進度用表格；分岔點用 AskUserQuestion；技術概念先白話解釋再帶術語；重大修復後主動走發版流程（`release` skill）；`git push` 一律先問；不要斷言正確性沒驗證過（用真實資料、獨立函式庫或手動追蹤比對，已多次證實這樣能抓到本可漏掉的 bug——這次 CVD 的兩個 symbol-mapping bug 就是靠真實登入實測才發現的，光看程式碼看不出來）。
