# HANDOFF.md — TXO-GEX-Dashboard 交接單（唯一真相來源）

> 每次交接前更新並 commit。新視窗只需讀：`CLAUDE.md`（含「多視窗守則」）、本檔、`AGENTS.md`、[docs/LOCAL_EXECUTION_INVENTORY.md](docs/LOCAL_EXECUTION_INVENTORY.md)（哪些功能鎖在 Windows 本機、哪些能搬雲端）。
> HISTORY.md 很長，**只讀最新兩三個條目**（用 grep／指定行數），不要整份讀入。
> 最後更新：2026-09-30 上午（補記 UI 微調、CVD 第三個 bug、第二次區網暴露）；前次 2026-09-30 凌晨，因 context 視窗快滿（非額度用盡）交接。origin/main 在 `5ef4878`（v64.17）。
> 這份文件之前有整整 4 天（9/26～9/30，v64.5～v64.17）沒有回頭更新，內容已完全過期，這次是**整份重寫**，不是增補。舊內容如果需要考古，去看 git log 這個檔案的歷史。

## 0. 開工前檢查（每次，不要跳過）

1. `git fetch origin`，確認本機落後多少；main 會被 GitHub Actions 每天自動推資料 commit。
2. `git status`：**共用資料夾（`C:\Users\mingi\OneDrive\文件\TXO-GEX-Dashboard`）目前落後 origin/main 97 個 commit（還停在 9/26 的 `39d04e6`），且有 8 個檔案未 commit**（見第 2 節）。這些未 commit 的檔案是舊版本，**不要當作現況參考、不要 stash／覆蓋／刪除**。
3. 用 `list_sessions` 確認有沒有其他視窗指向同一資料夾且正在執行。
4. 改檔／commit／push 一律用暫時 worktree（`.claude/skills/multi-session-safety/SKILL.md`），不要直接在共用資料夾裡動 git 狀態。**push 前先問使用者。**
5. 本檔「已驗證／已完成」是前一個視窗的自述，動工前抽樣重跑確認。

## 1. ✅ 真實 CVD／大戶散戶動能已上線（2026-09-30 15:35 起）；剩「買賣方向」待使用者用富邦 App 比對

- **已合併進 main（`2c17adf`）並重啟正式服務**（`TXO-Live-Price-Server`，`C:/Users/mingi/txo-klines-runner`，只綁 127.0.0.1:8000）。實測夜盤：`/api/momentum?symbol=TXF` 有真實 bar（大戶委託口差、散戶成交筆數差）、`/api/cvd` 有累積，日誌可見 `FUTURE_AH`。
- **這兩個副圖從來沒有真實資料的四個原因**（都靠富邦真實推播才發現）：①UI 代號 `TXF`/`MXF`/`MTX`/`TMF` 與富邦別名 `TXF1!`/`MXF1!`/`TMF1!` 對不上（`/api/cvd`、`/api/momentum` 都是）；②推播資料幀的 `symbol` 是實際月份合約 `TXFJ6`，不是訂閱的別名，改用頻道 `id` 對回；③成交在 `data.trades[]`（每筆自帶 bid/ask），舊程式讀頂層 `price`/`size` 讀到空值；④**夜盤（15:00–05:00）必須以 `afterHours: true` 訂閱**才有資料，現依台北時間自動切換（`sync_session_subscriptions()`）。先前「凌晨夜盤成交稀疏」的判斷是誤判。
- **已驗證**：成交完整性（150 秒擷取口數 = 交易所 `tradeVolume` 增量，345 = 345）；夜盤資料流。
- **尚未證實**：買賣方向準確度。「介於買賣價之間」的成交約占 8–13%，沿用前一筆方向（是猜的）；交易所 `totalBidMatch`/`totalAskMatch` 加總約為成交量 1.48 倍（含組合單），不是乾淨基準。**使用者將用富邦 App 人工比對**；在此之前 CVD 數字僅供參考，不可當進出場依據。收盤後 5 分鐘內外盤表在 `%TEMP%/cvd_5min_table_20260930.md`（日盤 12:11–13:46）。
- **限制**：資料只在使用者電腦（本機服務）；手機看不到這兩個副圖。歷史時段（服務啟動前）沒有資料，故意留白。CVD 點數上限 20000 筆（成交熱絡的日子，圖上只看得到最近幾小時，累積值本身仍是全場次正確）。
- **待辦**：①買賣方向人工比對後，決定是否要發 v64.18（目前這些修復是「未升版號的微調」，已寫入 HISTORY）；②殘留測試伺服器（127.0.0.1:8001／8002／8004／8005）可關閉。

## 2. 🔴🔴 資安事件（已處理，但要知道發生過什麼）

2026-09-30 凌晨發現：共用資料夾（落後 97 個 commit，還是 v64.12 資安修補之前的版本）裡的 `scripts/live_price_server.py`，從 **9/29 08:50 就被執行，監聽 `0.0.0.0:8000`**（對整個區網開放，會外洩 `.env` 富邦 API 金鑰與憑證密碼），跑了約 16 小時。已立即終止該進程（PID 13924、34700）。**正式排程的安全版本**（`C:\Users\mingi\txo-klines-runner`，只綁 `127.0.0.1`）**全程沒受影響、一直在正常運作**。

**推測根因**：共用資料夾裡有舊視窗留下的未 commit 修改（見第 3 節），使用者或某個視窗在這個過時資料夾裡手動執行了 `live_price_server.py`。

**使用者已知情並決定**：富邦金鑰因為只在家用網路開過，先不換。**這個決定是基於「舊版有漏洞」的既有認知**——這次新發現的是「跑了 16 小時」這個更具體的時長，如果使用者想重新評估，可以再問一次要不要換金鑰，但除非使用者主動提起，不用每次交接都重提。

**2026-09-30 09:08 第二次發生**：共用資料夾同一份舊版 `live_price_server.py` 又被啟動，再次綁在 `0.0.0.0:8000`。發現後該進程已消失（**不是我終止的，我的終止指令被權限檢查擋下**，事後不知是誰關的），同時正式服務（PID 2304）也一併不見，我依使用者同意執行 `Start-ScheduledTask -TaskName "TXO-Live-Price-Server"` 重啟，確認只綁 `127.0.0.1:8000` 且富邦訂閱正常。**尚不清楚是誰／哪個視窗在 09:08 啟動舊版**，建議使用者重新評估是否換富邦金鑰，並把共用資料夾同步到 origin/main（見第 3 節）。

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

## 4. ✅ 動能鳥邏輯搬離公開 repo（2026-09-30 已完成，待使用者驗收）

- 已搬到 `C:/Users/mingi/txo-private/screener-indicators/`（不在 git）：`jj_ghost_claws.py`、`screener_indicators.py`（含 JJ MACD/CCI、真5K、九轉 DeMark v3 與輔助函式）、`tv_indicators_engine.py.bak`（備份）。`build_screener_cache.py` 改由 `TXO_PRIVATE_INDICATORS` 環境變數（預設該路徑）載入，路徑錯誤會明確報錯。
- 驗證：1387 檔 × 4 個計算，搬遷前後輸出完全相同。**尚未實跑完整 `build_screener_cache.py`**，使用者下次手動執行時請確認正常。
- `scripts/tv_indicators_engine.py` 已刪（死代碼），`AGENTS.md`／`GEMINI.md` 紅線 6 已改。
- **仍待辦**：使用者部署新版 Worker 後，移除 `room.js` 對 `indicator=jj`（舊路由）的暫時備援，只打 `indicator=bird`。注意這些檔案仍在 git 歷史中（使用者已決定不改寫歷史）。

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
