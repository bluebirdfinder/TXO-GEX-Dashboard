# HANDOFF.md — TXO-GEX-Dashboard 交接單（唯一真相來源）

> 新視窗只需讀：`CLAUDE.md`、本檔、`AGENTS.md`（風控紅線）。HISTORY.md 很長，**只讀最新幾個條目**（`grep -n "^### " HISTORY.md | head -20` 再讀對應段落），不要整份讀入。
> 最後更新：2026-10-01 傍晚（上一個視窗因 context 視窗快滿而交接，非額度用盡）。**本檔是整份重寫**：9/30～10/01 兩天做了非常多事，舊的分段紀錄已併入 HISTORY.md，這裡只留現況與待辦。

## 0. 開工前檢查（每次，不要跳過）

1. `git fetch origin`；main 會被 GitHub Actions 每天自動推資料 commit（`🏛️ [Official] TAIFEX…`、`data: accumulate Fubon…`），落後是正常的。
2. 共用資料夾 `C:\Users\mingi\OneDrive\文件\TXO-GEX-Dashboard` **已在 2026-10-01 01:30 同步到 origin/main**（根治了三次區網暴露，見第 5 節）。它之後會慢慢落後，需要時 `git pull`；**不要在這個資料夾直接開發**。改檔／commit／push 一律用暫時 worktree（`.claude/skills/multi-session-safety/SKILL.md`）。
3. 檢查有沒有東西綁在 `0.0.0.0`：`netstat -ano | findstr LISTENING | findstr "0.0.0.0:80"` 應該空白；正式服務應只有 `127.0.0.1:8000`。
4. **`git push` 一律先問使用者**（用 AskUserQuestion）；使用者核准是「一批一批」的，不可沿用。
5. 本檔「已驗證」是上一個視窗的自述，動工前抽樣重跑確認：`python scripts/smoke_test_room.py`（線上版，37 項，約 3～4 分鐘，手機＋電腦）。
6. 使用者慣用繁體中文、白話解釋、進度用表格、分岔點用 AskUserQuestion（見第 9 節）。

## 1. 系統現況一覽（2026-10-01 傍晚）

| 零件 | 位置 | 狀態 |
|---|---|---|
| 網頁（GEX 主頁＋尋鳥戰情室） | GitHub Pages `bluebirdfinder.github.io/TXO-GEX-Dashboard/`（公開倉庫 `bluebirdfinder/TXO-GEX-Dashboard`） | 線上，煙霧測試 37/37。版本字串仍是 v64.17（這兩天都是「未升版號的微調」，細節在 HISTORY） |
| 本機價格服務（富邦即時價、五檔、CVD、大戶散戶動能） | `C:\Users\mingi\txo-klines-runner`（獨立 clone）；排程 `TXO-Live-Price-Server`（登入 Windows 自動啟動，掛了 15 秒重啟） | 運作中，只綁 `127.0.0.1:8000`；啟動時會 `git pull` main，所以**推送後要重啟服務才生效**（`Stop-ScheduledTask`→結束舊 python 進程→`Start-ScheduledTask`） |
| 私有 Cloudflare Worker `bluebird-indicators` | 原始碼在使用者私有資料夾 `C:\Users\mingi\OneDrive\文件\TradingView 指標\我寫的指標\ADX MTF 後端運算 (Cloudflare Worker)\worker.js`（**不在 git，不可 commit 進公開 repo**） | 已部署版本 `2026-10-01-a`（`?indicator=health` 回 `github_token_set:true`、Cron 已設，準時排程已於 10/02 驗證成功） |
| 本機排程 `TXO-Fubon-Futures-Klines` | 同 runner clone | 每天 05:30／14:00 累積富邦期貨日內 K；富邦只給最近一個場次，錯過補不回來，看 `data/klines_gap_report.json` |
| 雲端資料引擎 | GitHub Actions `auto_update.yml` | **GitHub 的 cron 結構性延遲 3～5 小時**（9 天 60 次執行 53 次晚超過 1 小時），已決定改用 Worker Cron 準時觸發，等使用者設定（第 2 節 A） |
| 私有資料夾 | `C:\Users\mingi\txo-private\`（不在 git） | `screener-indicators/`（選股雷達動能鳥／5K／九轉）、`smc/`、`shared-folder-backup-20260930/`、`PRIVATE_ACCESS_OPTIONS.md`、`handoff-20261001/`（本次交接的備份與測試工具） |

**Worker 目前的端點**（網址 `https://bluebird-indicators.bluebird-finder-tw.workers.dev/`，**必須帶 `Origin: https://bluebirdfinder.github.io` 標頭**，否則 403；PowerShell 的 `curl` 是別名要用 `curl.exe`，或請 Claude 從 Bash 驗證）：`indicator=chart`（主圖＋ADX 副圖全部運算）、`momentum`（雙層 MACD／CCI／AO）、`bird`、`smc`、預設 ADX、`quote`（期交所／證交所報價轉發，**上游間歇性回 520 擋雲端機房**，有時可用）、`health`。個股（不在 klines_cache 12 檔內）從 `data/stock_daily/NN.json` 分片補日／週／月 K。

**指標公式的位置（使用者的核心原則，見記憶 `project-indicator-ip-protection`）**：指標公式只能放在私有 Worker 或私有資料夾，網頁只拿結果。已完成：ADX Pro V3 完整版、雙層 MACD、CCI、AO、動能鳥、SMC、九轉、主圖動能鳥箭頭、VWAP、SMMA、VRVP、SAR、Supertrend、均線彩帶都在 Worker；選股雷達用的在私有資料夾。**網頁原始碼裡不應再出現指標公式**——煙霧測試有防護網（原始碼出現 `adxPeriod`、`bareEma`、`sarMaxAf` 等變數會失敗）。

## 2. 🔴 等使用者動手或決定的事（依優先順序）

| # | 事項 | 狀態／下一步 |
|---|---|---|
| A | ✅ **準時排程已驗證成功（2026-10-02）** | Worker Cron `3,33 * * * *`＋Secret `GITHUB_TOKEN` 已設定；10/02 台北 05:03／05:33／06:03 三輪都出現 `workflow_dispatch`，開跑時間為整點後約 12 秒（UTC 21:03:12／21:33:13／22:03:12），全部成功。**仍待辦**：①向使用者確認 GitHub 金鑰到期日並追蹤（fine-grained PAT 會過期，過期後準時排程會靜默失效，改回 GitHub 自己的晚 3～5 小時排程）②下午 15:03 等日盤時段再抽驗一次③週六 05:00（週五夜盤結算）沒涵蓋，要補在 `DISPATCH_SLOTS` 的 05/06 時段加 `Sat`。同日已推 `auto_update.yml`：push 被擋時 `git pull --rebase` 重試最多 5 次、加 `concurrency`。Lumi 專案在 TXO 後約 15 分鐘觸發，TXO 一輪實測 6～9 分鐘，夠用；使用者已把這些資訊轉告 Lumi |
| B | **手機在外面看富邦即時報價** | 富邦資料只在使用者家電腦。已比較方案（`txo-private\PRIVATE_ACCESS_OPTIONS.md`）：免費且安全性最高＝**Tailscale**（無公開入口，手機需開 App，設定約 20 分鐘）；付費最完整＝**Cloudflare Tunnel＋Access**（需網域約 US$2～10／年，朋友免裝 App，可強制實體金鑰）；ngrok 免費版不可行；「電腦推送到 Worker」無真正登入不建議。**使用者尚未選，網域未買。** 程式端已就緒：網頁 `GATEWAY_BASE`（不是從 github.io 開時向同位址要報價）、價格服務 `host_request_allowed()`（`TXO_ALLOWED_HOSTS`／`TXO_ALLOWED_TS_LOGINS`，預設行為不變）。Tailscale 做法：電腦與手機裝 Tailscale→後台開 MagicDNS＋HTTPS→電腦 `tailscale serve --bg 8000`→`.env` 加 `TXO_ALLOWED_HOSTS=.ts.net` 與 `TXO_ALLOWED_TS_LOGINS=信箱`→重啟服務→手機開 `https://電腦名.tailxxxx.ts.net/trading%20room/room.html` |
| C | **CVD 買賣方向驗證** | 成交完整性已驗證（口數總和＝交易所 `tradeVolume`，345＝345），**方向準確度未證實**：介於買賣價之間的成交約占 8–13%，沿用前一筆方向（是猜的）。使用者說會用富邦 App 對照 5 分鐘內外盤表（`txo-private\handoff-20261001\cvd_5min_table_20260930.md`＋原始 CSV），結果回報給 Claude。在此之前 CVD 數字僅供參考 |
| D | 個股期貨的大戶散戶動能 | 已擴到 36 檔個股／ETF 期貨（選股票會對應其期貨合約，如 2330→CDF）。10/01 日盤已見到訂閱與委託簿資料（CDF 大戶委託口差 -284），**成交筆數與 CVD 尚未仔細核對**——請用 `/api/momentum?symbol=CDF` 等確認 `trade_count_in_bar` 非 0 且合理 |
| E | 設定視窗「MA88 顏色」選擇器（`col-ribbons-88`）是擺設 | 從沒被讀取；預設藍色對應的是 MA200 年線而非 MA88，標籤「趨勢主線顏色」不明確。**待使用者決定**接到哪條線或移除 |
| F | 倉庫改私有（法規方向）的連帶事項 | ①GitHub 私有倉庫 Actions 免費時數 2,000 分鐘／月（公開不限），目前粗估 2,000～2,400 分鐘／月可能略超過②Worker 讀資料來源（公開 Pages）要改③Worker `ALLOWED_ORIGINS` 要換成私人網址④電腦要定時 `git pull`⑤Worker 的官方報價轉發是公開可呼叫，私人化後建議改成需密語。**尚未做** |
| G | 法規確認（使用者要自己查，Claude 非律師） | 富邦 API 行情條款（通常限本人使用）、期交所／證交所即時行情再散布需資訊廠商授權、投顧法（公開買賣建議、社群圖卡、AI 軍師輸出）、SMC 指標 CC BY-NC-SA 僅非商業。使用者選「自己＋幾位指定朋友」，**Claude 建議先只開放自己**（朋友看到即時報價可能構成再散布）。主頁「社群圖卡」功能先保留，法規確認後再決定 |
| H | `.git` 歷史肥大（本機約 645M，持續增加） | 使用者不想改寫公開歷史，所以不能 squash。方向（git-lfs／資料檔搬外部儲存）**尚未討論**。2026-10-01 又新增約 6MB 分片資料檔與一次 15MB 日 K 快取更新 |
| I | 清理本機殘留 | 本機有三十多個已合併的 `claude/*` 分支與 9 個暫時 worktree（`C:\Users\mingi\AppData\Local\Temp\txo-wt-*`）；保護分支 `backup/shared-folder-39d04e6-20260930` 請保留。清理前先問使用者 |

## 3. 這兩天（9/30～10/01）完成的重點（細節在 HISTORY.md 最新幾個條目）

- **資安**：區網暴露三次（共用資料夾舊版 `live_price_server.py` 綁 `0.0.0.0:8000`）已根治（同步到 origin/main）；程式端有 `host_request_allowed()`。
- **真實 CVD／大戶散戶動能**：這兩個副圖從來沒有真實資料，原因四個——UI 代號與富邦別名對不上（`TXF` vs `TXF1!`）、推播 `symbol` 是 `TXFJ6` 而非別名（改用頻道 `id` 對回）、成交在 `data.trades[]`、**夜盤必須 `afterHours: true` 訂閱**（依台北時間自動切換 `sync_session_subscriptions()`）。
- **富邦日盤報價是昨晚夜盤收盤價**：富邦 quote 的 `session` 只接受 `afterhours`，日盤要**不帶參數**；舊程式傳 `REGULAR` 報錯後默默改查夜盤。已修，且富邦報價 10 秒內新鮮時公開來源備援不得覆蓋。
- **加權指數漲跌算錯**：Yahoo 的 `previousClose` 是兩天前；改用證交所 MIS（官方），並補櫃買。
- **戰情室網頁三輪稽核**：偽數據／XSS／Gemini Key 不放網址／GEX 載入失敗紅色橫幅／交易時段用台北時間／價格與漲跌互相矛盾／GEX 距離用舊價／**圖表時間軸原本顯示 UTC（慢 8 小時）**／設定視窗欄位失效（Supertrend 週期倍數、九轉開關）／AI 軍師不再用假設權利金算風報比（紅線 4）／手機排版（五窗格一屏、選股雷達可捲動、TV 風格）。
- **全市場個股日／週／月 K**：`scripts/build_stock_daily_shards.py` 切 64 片 `data/stock_daily/NN.json`（djb2 雜湊 % 64，前端／Python／Worker 三邊一致）；每根 K 棒帶日期（舊快取沒有日期，有停牌／新上市的股票不能用位置猜日期）。分 K 沒有官方免費來源，只提示改看日 K 以上。
- **指標公式全部搬進 Worker**：新舊逐項比對 170/170 相同、端到端 44/44；唯一刻意改動是 VWAP 上下通道（舊版「±1σ」其實是固定點數，改為真正的成交量加權標準差）。

## 4. 測試與工具

| 工具 | 位置 | 用途 |
|---|---|---|
| 煙霧測試 | `scripts/smoke_test_room.py`（公開 repo） | `python scripts/smoke_test_room.py`（線上版）／`--url http://127.0.0.1:PORT/`（本機，先在專案根目錄 `python -m http.server PORT`）／`--only mobile\|desktop`。37 項：版本一致、無 JS 例外、手機五窗格、個股日 K、股票對應期貨、XSS 跳脫、選股雷達可捲動、設定欄位有效、即時報價與漲跌一致、**原始碼不含指標公式** 等。**改過 `trading room/` 或 `app.js` 後必跑** |
| Worker 測試 | `...\ADX MTF 後端運算 (Cloudflare Worker)\tests\`（私有，含 `README.txt`） | `worker_test2.mjs`（28 項行為測試）、`parity_test.mjs`（170 項新舊比對）、`e2e_migrated.py`（44 項端到端）、`baseline_capture.py`、`worker_server.mjs` |
| 探針腳本 | `txo-private\handoff-20261001\` | 富邦 WebSocket／REST 探針（`probe_ws.py`、`probe_night.py`、`probe_rest_quote.py` 等）、成交收集器；用 `.env` 登入富邦（會多開一個登入，用完 `os._exit(0)`） |
| 發版 | `release` skill／`scripts/bump_version.py` | 這兩天都沒升版號；使用者要發版時走 skill。`room.js?v=v64.17&b=日期字母` 的 `&b=` 是快取戳記，每次改 `room.js`／`room.css` 都要換，否則手機會吃舊檔 |

## 5. 資安事件摘要（要知道發生過什麼）

共用資料夾裡**舊版**（v64.12 資安修補之前）`scripts/live_price_server.py` 在 2026-09-29 08:50、09-30 09:08、09-30 19:20 被啟動三次，綁在 `0.0.0.0:8000`（對整個區網開放，會外洩 `.env` 的富邦金鑰與憑證密碼）。第三次進程樹顯示是 Windows「Python Manager」啟動器開的，很像在檔案總管雙擊那個 `.py`。已全部終止，並在 2026-10-01 01:30 將共用資料夾同步到 origin/main（備份：`txo-private\shared-folder-backup-20260930\`；唯一未推送 commit 內容經 `git cherry` 確認等價已在 main，保護分支 `backup/shared-folder-39d04e6-20260930`）。**富邦金鑰使用者因只在家用網路開過，決定先不換**；除非使用者主動提起，不用每次交接重提。已實測本機服務不會把 `.env`／程式檔／`.git` 當網頁送出（皆 404）。

## 6. 已知問題與備忘（不急）

- 週五夜盤結算（週六 05:00）原 GitHub cron 就沒涵蓋（`0-4` 換算是台北週一至週五早上）；Worker 的 `DISPATCH_SLOTS` 刻意照抄，要補在 05/06 時段加 `'Sat'`。
- 價格服務頂部「報價來源」文字（`active_provider`）是「最後一個更新任何指數的來源」，加權由證交所更新時會顯示「官方備援」，**只是標籤**；台指期價格實際來源看 `txf.provider`。
- `app.js` 的 `CHART_DEFAULTS`（2026-09-15 的 GEX 預設值）仍在，僅資料檔完全載入失敗時使用；戰情室對應情況已加紅色橫幅，主頁尚未。
- 通行碼 `GEX2026` 寫在公開的 `app.js`／`scripts/encrypt.py`／`scripts/fetch_and_calc_vision.py`，頁面預設自動通關，不是實質保護。
- 2027 休市日曆待官方公布。
- CVD 圖點數上限 20000 筆（成交熱絡日圖上只看得到最近幾小時，累積值本身全場次正確）。
- 手機沒有 CVD／大戶散戶動能（資料來自電腦上的服務）。
- 看富邦即時報價的方法：在家用電腦開 `http://localhost:8000/trading%20room/room.html`（顯示 🟢 富邦 NEO API (LIVE)）；從 github.io 開會被瀏覽器安全機制擋住對本機服務的連線。

## 7. 這兩天踩過的坑（給下一個視窗省時間）

- **Windows 路徑與中文**：用 Bash heredoc 寫含中文＋反斜線的 Python 腳本會被編碼／跳脫弄壞（`\U` 變 Unicode 跳脫、`\r` 變歸位字元、中文變亂碼）。**要寫含中文的檔案用 Write 工具**，路徑盡量用斜線。
- **換行符**：專案檔案是 CRLF（`autocrlf`），Python 讀寫要用 `newline=''` 並保留原換行，否則整檔 diff 全紅。
- **PowerShell**：`curl` 是 `Invoke-WebRequest` 別名；`&&` 不能用；`Stop-Process` 等動作若使用者沒明確核准，自動權限檢查可能擋下（使用者核准「重啟」後才可）。
- **Bash 工具**：前景 `sleep` 被擋，用迴圈輪詢或 `run_in_background`；長時間背景伺服器（`python -m http.server`）用完要關，我用 PowerShell 依埠號找到再 `Stop-Process`。
- **GitHub Pages 快取約 10 分鐘**：手機看不到更新先懷疑快取（無痕視窗、換 `&b=` 戳記）。
- **推送前**：`git fetch` 後若 main 已前進（CI 資料 commit），用 `git merge origin/main`，**不要 rebase 含合併 commit 的分支**。
- **富邦 API**：`rest_client.futopt.intraday.quote` 日盤不帶 `session`、夜盤 `session="AFTERHOURS"`；WebSocket 訂閱夜盤要 `afterHours: True`；推播資料幀 `symbol` 是實際月份合約（`TXFJ6`），訂閱別名 `TXF1!` 用 `id` 對回。
- **TWSE／TAIFEX MIS**：回 HTTP 520 不一定是壞掉，可能是擋雲端機房或暫時性；TWSE 憑證在 Python 3.13 需放寬 `VERIFY_X509_STRICT`（`live_price_server.SSL_CTX` 已處理）。

## 8. 風控與溝通偏好（不變）

核心風控見 `AGENTS.md`（嚴禁拆單、嚴禁追價、區分真實倉位、盤中別讀盤後 Excel、**嚴禁偽數據**）。使用者偏好：白話解釋（國中生也懂，必須用術語時先給白話）、進度用表格、分岔點用 AskUserQuestion、長任務回報進度、`git push` 一律先問、不要斷言正確性沒驗證過（用真實資料、獨立來源或新舊逐項比對——這兩天靠真實富邦推播抓到的 bug 全是光看程式碼看不出來的）、重大修復後主動走發版流程（`release` skill）、主動提醒法規風險。使用者晚上常外出或睡覺，不在時只做不影響線上的事，需要核准的動作留到使用者回來。
