# HANDOFF.md — 現在做到哪、接下來做什麼（唯一的交接檔，永遠覆寫）

> **用法**：新視窗只需讀 `CLAUDE.md`、`AGENTS.md`（風控紅線）、本檔。交接時**只改這一份**，不要再新增 `HANDOFF_日期.md`。
> **資料新鮮度**：本檔於 2026-10-30 由 2026-10-04～10-22 的 5 份交接單合併而成。**10/22 之後的進展沒有被併入**（看 `git log` 與 `HISTORY.md` 最上面幾個條目補齊）。標「未確認」的是我沒能核實是否已做完。
> 舊交接單原文全部在 [docs/archive/handoffs/](docs/archive/handoffs/)（索引見 [docs/archive/INDEX.md](docs/archive/INDEX.md)），不是刪除。

## 0. 開工前檢查（每次）

1. `git fetch origin`；main 每天被 GitHub Actions 自動推資料 commit，落後是正常的。
2. **共用資料夾 `C:\Users\mingi\OneDrive\文件\TXO-GEX-Dashboard` 不要切分支／pull／reset／stash／merge**（幕僚鳥橋接與 `trading room/brain/` 在裡面）。改檔、commit、推送一律用暫時 worktree（`.claude/skills/multi-session-safety/SKILL.md`）。
3. `git status` 看有沒有別的視窗未 commit 的檔案；不是自己改的不碰。
4. 報價服務：`curl localhost:8000/api/live_tick` 應為 provider=FUBON；靜態前台 `localhost:8001/index.html`。8000 是 `txo-klines-runner` 的 clone，由排程 `TXO-Live-Price-Server` 管理，**不要自己另開 8000**。
5. **`git push` 一律先問使用者**，核准是一批一批的，不可沿用。
6. 使用者偏好：繁體中文、白話、進度用表格、回報完成百分比、要問用選項卡片（選項寫詳細）、每次結尾明講「有沒有需要使用者回答的事」。

## 1. 系統地圖（長期有效）

| 零件 | 位置 | 備註 |
|---|---|---|
| 網頁（GEX 主頁＋尋鳥戰情室） | GitHub Pages `bluebirdfinder.github.io/TXO-GEX-Dashboard/`（公開倉庫） | 版本字串 v64.18（STATUS 抬頭）；之後多次「未升版」微調，細節看 HISTORY |
| 本機價格服務（富邦即時價、五檔、CVD、大戶散戶動能） | `C:\Users\mingi\txo-klines-runner`（獨立 clone） | 啟動時 hard-sync 到 origin/main；**推送後要殺 python 讓排程重啟才生效**（約 1～6 分鐘無報價，先告知使用者、休市時做、做完驗證 provider=FUBON） |
| 私有 Cloudflare Worker `bluebird-indicators` | 原始碼在使用者私有資料夾（`TradingView 指標\我寫的指標\ADX MTF 後端運算 (Cloudflare Worker)\worker.js`） | **不在 git，不可進公開 repo**；Worker 一律由使用者自己貼到 Cloudflare 部署。只接受 `bluebirdfinder.github.io`／localhost 來源 |
| 資料引擎排程 | GitHub Actions `auto_update.yml` ＋ Worker Cron `3,33 * * * *` 準時觸發 | GitHub 自己的 cron 結構性延遲 3～5 小時 |
| 本機排程 | `TXO-Fubon-Futures-Klines`（05:30／14:00 累積富邦期貨 K）、`TXO-Static-Front-8001`、`TXO-Probe-Publish-Day/Night`（量完要刪） | 富邦只給最近一個場次，錯過補不回來 |
| 私有資料夾 | `C:\Users\mingi\txo-private\`（不在 git） | 選股指標、SMC、備份、`desk/personas.json` 等 |
| 本機資料每日備份 | `C:\Users\mingi\OneDrive\文件\TXO-runner-data-backup\<日期>\`（約 47MB／天） | 由 `txo-klines-runner\scripts\local_data_store.py backup` 產生，**程式內預設只留 14 份**（超過會自動輪替，總量約 650MB 封頂）。富邦 K 線錯過補不回來，這是保險，**不要手動刪**。是哪個排程呼叫它：未確認（可能是 `TXO-Fubon-Futures-Klines`） |
| 台選鳥交易室服務 | 排程 `TXO-Desk-server／bridge／monitor／patrol／recorder` 的工作目錄是 `.claude/worktrees/option-quote-recorder` | **這個 worktree 是正在跑的服務，不能移除或切分支** |
| 幕僚鳥橋接 | `trading room\advisor_bridge.py`，`127.0.0.1:8765`，用 `claude -p` | 沒有開機自動啟動；記憶在 `trading room\brain\memory\`（gitignore） |
| 指標公式 | 只放私有 Worker／私有資料夾，網頁只拿結果 | 煙霧測試 `scripts/smoke_test_room.py` 有防護網（原始碼出現公式變數會失敗） |

**日期型提醒**：GitHub 金鑰（fine-grained PAT）**2026-12-30 到期**，過期後準時排程會靜默退回晚 3～5 小時的 GitHub 排程；Google 日曆已有 2026-12-16 提醒（建新金鑰並更新 Cloudflare Secret `GITHUB_TOKEN`）。

## 2. 待辦與待決定（只列沒完成的；來源欄指舊交接單，原文在 archive）

### 2-1 等使用者動手或決定

| # | 事項 | 來源 | 狀態 |
|---|---|---|---|
| 1 | 手機在外面看富邦即時報價：Tailscale（免費）vs Cloudflare Tunnel＋Access（要網域） | 10/04 B | 使用者尚未選 |
| 2 | 倉庫改私有（法規方向）及連帶事項：Actions 免費時數 2,000 分鐘／月、Worker 資料來源與 `ALLOWED_ORIGINS`、Pages、每日排程、Telegram、露米連結 | 10/04 F、10/22 #6 | 10/24 發表後才規劃；repo 目前 PUBLIC |
| 3 | 法規確認：富邦行情條款、期交所／證交所再散布授權、投顧法、SMC 授權（CC BY-NC-SA 僅非商業） | 10/04 G | 使用者自己查；Claude 建議先只開放自己 |
| 4 | `.git` 歷史肥大（本機約 645M 且增加）；`klines_cache.json` 變 18.7MB | 10/04 H、R | 使用者不想改寫公開歷史；方向（git-lfs／外部儲存）未討論 |
| 5 | GEX v1 vs 通行版 v2：兩版並存，累積夠天數後重跑 `python scripts/gex_v2_backtest.py`，再決定是否取代 v1（走 release skill，通知 Lumi 重跑回測） | 10/04 T、GEX_V2 交接 | 未確認進度；詳見 [archive 的 GEX_V2 交接](docs/archive/handoffs/HANDOFF_GEX_V2_20261013.md) |
| 6 | 找不到 Zero Gamma 轉折時會退回「現價−150／−100」假數字；夜盤標的夜盤時段 `change_pct` 是夜盤期貨漲跌非現貨；2323 中環沒有行情 | 10/04 L | 待使用者決定（觸及「嚴禁偽數據」紅線，建議改成顯示無資料） |
| 7 | 設定視窗「MA88 顏色」選擇器是擺設，沒被讀取 | 10/04 E | 待決定接到哪條線或移除 |
| 8 | `TXO-Screener-Cache` 要不要加 `-Push` | 10/04 R | 待決定 |
| 9 | 群益 API：使用者以系統管理員執行元件 `install.bat`、自設環境變數登入、再跑唯讀測試（GC／CL／ZN／DX） | 10/22 #1、#2 | 未確認；**憑證 `C:\Capital\*.pfx` 不要讀** |
| 10 | CVD 買賣方向準確度驗證（使用者用富邦 App 對照 5 分鐘內外盤表）；在此之前 CVD 數字僅供參考 | 10/04 C | 未確認 |

### 2-2 可以直接做（不用等使用者）

| # | 事項 | 來源 | 備註 |
|---|---|---|---|
| 11 | 量完 3 個交易日後依 `~\.txo_publish_probe\` 結果定新排程時間表，改 `auto_update.yml` cron 與 Worker `DISPATCH_SLOTS`（Worker 要使用者手動部署）；刪除兩個探針排程 `Unregister-ScheduledTask`；Lumi 要錯開約 15 分鐘 | 10/04 N、P | 未確認；探針曾因電池設定沒跑 |
| 12 | 大額交易人「尚未公布」時，前端只顯示 —；加「資料尚未公布」字樣，並保留資料完整度閘門（引擎已有 `data_completeness`） | 10/04 N、P | 引擎端尚未在交易日 09:00～公布前實測 |
| 13 | 幕僚鳥 `bridgeAvailable()` 只等 0.8 秒導致答非所問；修法在分支 `claude/advisor-health-timeout`（commit 71d43ed，worktree `C:\Users\mingi\txo-wt-advisor-timeout`） | 10/22 | 未 push；JJ 視窗整合完再問使用者 |
| 14 | 幕僚鳥查個股會寫錯代號、沒資料硬寫（定穎投控 3715 寫成 3815）；紅線：沒有真實資料要明說 | 10/22 #4 | |
| 15 | 換新版幕僚鳥橋接（防套話 `advisor_guard.py` 生效）：把 `advisor_bridge.py`、`advisor_guard.py` 放進跑橋接的資料夾並重開 `start_advisor.bat` | 10/21 #2 | 會讓共用資料夾 git status 不乾淨，先問 |
| 16 | 8000 卡死根因：10/21 09:06 起富邦 SSLError 83 次、WebSocket 10053、MIS 429（jj_lines 記錄器被限流） | 10/22 #3 | 「重複登入」猜測沒證據；已有看門狗，真實斷線未測過 |
| 17 | Max Pain 只算 w1／w2／fri／mth 四個到期（涵蓋約 83.6% OI），全契約重算差約 200～300 點；Call Wall 是 Gamma 加權非最大 OI；微型臺指散戶多空比資料檔 58.02 vs 官方 62.65（原因未查出，**不要猜**） | 10/16 #2～4 | 對外說明要誠實 |
| 18 | 國定假日場次判斷：`_quote_session_mode()` 只看星期與鐘點 | 10/17 #4、10/21 #7 | |
| 19 | Worker 拿不到台指期即時價（期交所對 Cloudflare 回 520）；可行做法是本機把最新價 POST 給 Worker（要使用者再貼 Worker） | 10/21 #4 | |
| 20 | 個股現貨 `spot_date` 要等排程下一輪才出現，檢查 `data/gex_data.json` 的 `stock_futures[*].spot_date` | 10/21 #6 | |
| 21 | 清理本機殘留 worktree／分支（`.git`、`.claude` 有繼承的 Everyone DENY 刪除權限）：**不要再用 `--force` 批次刪**，會留下半殘；保護分支 `backup/shared-folder-39d04e6-20260930`、`claude/elegant-heisenberg-b65af4`（有他人未 commit 的 `room.js`）要保留 | 10/04 I | 使用者決定先留著。**2026-10-31 狀態**：`OneDrive\文件\` 下 7 個暫時副本 `txo-wt-1007／colors／day／docs／handoff-key／nightmis／wf-fix`（各約 56～66MB）：1007／colors／handoff-key／nightmis／wf-fix 五個已全併入 main；用 `git worktree remove`（不加 `--force`）試過一次，仍報 Permission denied，結果是**登記已被 git 移除、資料夾還在（各少 1 個檔案）、`.git/worktrees/` 殘留空登記**，不影響運作，內容無遺失，分支都還在。這 5 個資料夾現在可直接刪（內容都在 main），尚待使用者同意。`txo-wt-day`（11 個引擎產生的資料檔有修改）與 `txo-wt-docs`（1 個未追蹤的 `data/gex_line_observations.json`）尚未比對，不要刪 |

### 2-3 長期未解（不要說已解決）

| 事項 | 現況 |
|---|---|
| ADX 與 TradingView 不一致 | 微台 15M／4H 一致；1H（我們 50.2 vs TV 55）、日線（差在 TV 含夜盤）不一致，試過 4 種對齊都不是。**不要說「已對齊」** |
| JJ（rStock）大戶散戶動能公式 | 未解；TV 版三個值在 ±1.2K、像累積算法；探索紀錄在 `docs/JJ_RSTOCK_MOMENTUM_EXPLORATION.md` |
| 動能鳥未對照 TV 驗證 | 畫面有誠實標示，錄影／截圖不要特別展示 |
| 官方對帳 `python scripts/audit_vs_official.py --sample 0` | 10/20：1,485 項一致、3 項不一致（Max Pain 4 個到期、Call Wall 設計、對帳程式把夜盤當日盤）、7 項略過。**不要說 FAIL=0** |
| 幕僚鳥後續構想 | 開機自動啟動橋接（要使用者同意）、Opus 實測、知識庫同步到 runner、Mac mini M2 搬遷、雲端多人版（要帳號與獨立記憶，工程大）、覆盤回饋 |

## 3. 別的視窗／別的專案（動檔前先確認）

| 對象 | 狀態（10/22 當時） |
|---|---|
| JJ 視窗（`local_71e47402…`） | 正在把 `claude/jj-order-lines` 與共用資料夾分支（29 個未 push commit）合併，衝突 11 檔；**共用資料夾不要 merge／rebase／reset／stash／切分支** |
| 交易室設計視窗（「台選鳥交易室交接與檢查」`local_d67710b1…`） | 唯一的交易室設計視窗；規格在 `C:\Users\mingi\txo-wt-desk-friction\docs\TRADING_ROOM_ROLES_SPEC.md`（分支 `desk-friction-guard`，未 push）；其 worktree `.claude/worktrees/option-quote-recorder` 內的 `docs/HANDOFF_20261019/20261021*`、`DECISIONS_20261020`、`RESEARCH_LIBRARY_DRAFT`、`brain/desk/playbook.md` **刻意不推公開 repo，只存在該分支**，不要複製進本 repo。名詞：「交易室」＝AI 交易室（主管幕僚鳥＋研究員＋交易員），「戰情室」＝`trading room/room.html` 盯盤頁 |
| Lumi 專案（`TG 自動化機器人\露米籌碼監控機器人`） | 別人的專案，不動；Worker 線上實際是 Lumi 的 `cloudflare_worker_lumi_fusion.js`（約 954 行），**不要把 repo 內 `cloudflare/worker.js` 貼上去**（會讓 Lumi 推播消失） |
| 洋洋專案 | 別人的專案，不動 |

## 4. 千萬別做

| 別做 | 原因 |
|---|---|
| 把 Worker 原始碼、PDF、網頁通行碼、群益憑證、帳密放進公開 repo、聊天或截圖 | 指標 IP／資安 |
| 說 ADX／CVD「和 TV 完全一致」、說對帳「FAIL=0」 | 不是事實 |
| 替使用者寄信、編他的績效或感受 | 他自己寫自己寄 |
| 在共用資料夾做 git 狀態變更 | 見第 0 節 |
| 動洋洋、Lumi 專案的檔案 | 別人的專案 |
| 拆週選價差單、追價、用偽數據、盤中讀盤後 Excel 當即時行情 | AGENTS.md 紅線 |

## 5. 環境坑

| 坑 | 處理 |
|---|---|
| Bash heredoc 吞掉 `\n`、`\u`，中文加反斜線的 Python 補丁被弄壞 | 用 Write 工具寫成 `.py` 再執行；路徑盡量用斜線 |
| 專案檔是 CRLF | Python 讀寫用 `newline=''` 保留換行，否則整檔 diff |
| Python 輸出中文在 Windows 崩潰（cp950） | 加 `PYTHONIOENCODING=utf-8 PYTHONUTF8=1`；含中文的 curl `-d` 先寫成 UTF-8 檔再 `--data-binary @檔` |
| PowerShell `curl` 是別名、`&&` 不能用；前景 `sleep` 被擋 | 用 `curl.exe`；等待用 Monitor／輪詢 |
| `git worktree remove` 報 Permission denied | 資料夾已刪、登記殘留，之後 `git worktree prune`；別用 `--force` 批次 |
| 推送前 main 已前進 | `git merge origin/main`，**不要 rebase 含合併 commit 的分支**；push 前一律 `git fetch`、確認純往前 |
| GitHub Pages 快取約 10 分鐘 | 手機看不到更新先懷疑快取；`room.js?v=…&b=日期字母` 的 `&b=` 每次改 `room.js`／`room.css` 都要換 |
| 在瀏覽器直接開 Worker 網址會看到 `origin not allowed` | 正常；驗證要從戰情室頁面 console 發請求 |
| 內建瀏覽器連不到 `localhost:8000` 閘道、面板被隱藏時截圖逾時 | 用使用者自己的 Chrome，或 `javascript_tool`／`read_page` |
| MIS `getChartData1M` 標籤＝K 棒**結束**時間，分鐘可寫 60 | `scripts/mis_session.py` 的 `parse_mis_ticks` 已處理 |
| 富邦 API | 日盤 quote 不帶 `session`、夜盤 `session="AFTERHOURS"`；WebSocket 夜盤要 `afterHours: True`；推播 `symbol` 是 `TXFJ6`，用 `id` 對回別名 `TXF1!` |
| 證交所 openapi 憑證缺 Subject Key Identifier | Python 用 `ssl.create_default_context()` 並關閉 `VERIFY_X509_STRICT` |
| 個股期貨代碼別憑記憶（CAF＝南亞、CCF＝聯電） | 以 `data/taifex_stock_futures_contract_map.json` 為準 |

## 6. 常用驗證指令

```bash
curl -s localhost:8000/api/live_tick | python -c "import json,sys;d=json.load(sys.stdin)['txf'];print(d['provider'],d['price'])"
curl -s "localhost:8000/api/session_bars?symbol=TXF" | python -c "import json,sys;d=json.load(sys.stdin);print(d.get('session'),len(d.get('bars',[])))"
curl -s localhost:8765/health      # 幕僚鳥橋接
python scripts/smoke_test_room.py  # 改過 trading room/ 或 app.js 後必跑（線上版，37 項）
python scripts/test_mis_session.py && python scripts/test_mis_ticks.py && python "trading room/test_advisor_guard.py"
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/audit_vs_official.py --sample 0   # 收盤後（日盤 14:30、夜盤 05:30）
```

## 7. 資安備忘（發生過什麼）

2026-09-29～30 共用資料夾的舊版 `live_price_server.py` 曾三次綁在 `0.0.0.0:8000`（區網可見，可能外洩 `.env`），已終止並同步；富邦金鑰使用者決定先不換。平常檢查：`netstat -ano | findstr LISTENING | findstr "0.0.0.0:80"` 應為空白，正式服務只應有 `127.0.0.1:8000`。除非使用者提起，不用每次交接重提。
