# HANDOFF.md — 現在做到哪、接下來做什麼（唯一的交接檔，永遠覆寫）

> **用法**：新視窗只需讀 `CLAUDE.md`、`AGENTS.md`（風控紅線）、本檔。交接時**只改這一份**，不要再新增 `HANDOFF_日期.md`。
> **資料新鮮度**：本檔於 2026-10-30 由 2026-10-04～10-22 的 5 份交接單合併而成。**10/22 之後的進展沒有被併入**（看 `git log` 與 `HISTORY.md` 最上面幾個條目補齊）。標「未確認」的是我沒能核實是否已做完。**2026-11-22 的 Mac 搬遷現況已併入 §2-00，同日的 git 未 commit／分支盤點與整合結果在 §2-00b。**
> 舊交接單原文全部在 [docs/archive/handoffs/](docs/archive/handoffs/)（索引見 [docs/archive/INDEX.md](docs/archive/INDEX.md)），不是刪除。

## 0. 開工前檢查（每次）

1. `git fetch origin`；main 每天被 GitHub Actions 自動推資料 commit，落後是正常的。
2. **共用資料夾 `C:\Users\mingi\OneDrive\文件\TXO-GEX-Dashboard` 不要切分支／pull／reset／stash／merge**（幕僚鳥橋接與 `trading room/brain/` 在裡面）。改檔、commit、推送一律用暫時 worktree（`.claude/skills/multi-session-safety/SKILL.md`）。
3. `git status` 看有沒有別的視窗未 commit 的檔案；不是自己改的不碰。
4. 報價服務：`curl localhost:8000/api/live_tick` 應為 provider=FUBON；靜態前台 `localhost:8001/index.html`。8000 是 `txo-klines-runner` 的 clone，由排程 `TXO-Live-Price-Server` 管理，**不要自己另開 8000**。
5. **`git push` 一律先問使用者**，核准是一批一批的，不可沿用。
6. 要合併分支、解衝突、同步 main、push 前檢查：先載入全域 skill `branch-hygiene`（先 `git merge-tree` 試合併、不在共用資料夾動 git 狀態），細節見 §2-00b。
7. 使用者偏好：繁體中文、白話、進度用表格、回報完成百分比、要問用選項卡片（選項寫詳細）、每次結尾明講「有沒有需要使用者回答的事」。

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

### 2-00 Mac mini 搬遷（2026-11-22 現況；目的：Dell 上班時間可以關機，Dell 當停用備援、不刪）

**規則**：同一個任務不可兩台同時跑（切換＝先停 Dell 再啟 Mac）；Mac 只當執行機、Dell 當開發機；搬遷期間交易室程式碼凍結。完整紀錄與證據：[docs/MIGRATION_ALL_PLAN_20261109.md](docs/MIGRATION_ALL_PLAN_20261109.md) §6-H／6-I／6-J（**未 commit**）；Mac 用的 launchd 範本與腳本在 `docs/mac_migration/`（`__HOME__` 以 sed 置換）。Mac＝`alex@Alex-Mac-mini`，富邦用 `~/AI/fubon-test/bin/python`（系統 python3 是 3.9、沒有 fubon_neo），金鑰檔 `~/AI/txo-mac.env`（chmod 600）。

| 已在 Mac 並行（Dell 完全沒動） | launchd 標籤 | 資料位置 |
|---|---|---|
| OP666 逐筆錄製 | `com.txo.op666-recorder-mac` | `~/AI/op666_record_mac`（≠ Dell 的 `txo-private\op666_record`） |
| 報價服務（8000） | `com.txo.live-price-mac` | `~/AI/txo-klines-runner` |
| 選擇權報價鏈（30 秒） | `com.txo.optrec-mac` | `~/AI/option_quotes_mac`（腳本要自己從 OneDrive 工作區 `tools/` 複製到 `~/AI/optrec/`） |
| 看門狗 v3 | `com.txo.watchdog-mac` | `~/AI/watchdog`（日誌 `watchdog.log`；沒檔案＝沒事件） |
| 電源／自動登入／重開機測試 | — | sleep 0、autorestart 1、FileVault Off、自動登入 alex；**重開機後服務自動恢復已實測（休市）** |

| 還沒搬（先留 Dell 或待處理） | 備註 |
|---|---|
| 葡萄錄製器 `TXO-Grape-Recorder` | 切換日搬：改 3 個寫死路徑（DESK、IND_DIR、LUMI_CSV）、複製狀態檔 `kbars_1m.csv`／`signals.jsonl`／`outcomes.jsonl`／`state.json`，Dell 停、Mac 啟 |
| 動能鳥（jj）歷史錄製 | **長期錄製**（TV 拿不到委託簿）。它是報價服務內的背景執行緒（私有 `txo-private\jj_momentum\jj_lines.py`），開盤第一筆委託簿進來才自動載入，不用手動啟動；Mac 沒有該私有模組所以不會錄；切換時要複製模組，同一時間只能一台錄（避免加重 MIS 429） |
| 富邦期貨 K（05:30／14:00） | 一個月內補得回來；只能一台推 GitHub |
| 交易室服務（desk 八項）、幕僚鳥、情報鳥、Telegram 機器人 | 開發中、不能兩台同跑 → 先留 Dell；暫停前先確認 T0／T2／W0 沒有未平倉與掛單（11/22 帳本最後決策皆「無決策」，但沒找到持倉檔，**未直接確認**） |
| Tailnet 入口 `TXO-Tailnet-Gate`（`txo-private\tailnet\gate.py`，只綁 Dell 的 Tailscale IP，轉發 8001／8770／8792，入口頁 8800） | Dell 關機前要在 Mac 另做入口並改轉發目標；戰情室網頁抓的是 Dell 的報價服務，要一起規劃 |
| Mac 上 `com.txo.static-front` | **已查明（11/22 晚）**：跑 `/usr/bin/python3 ~/AI/txo-static/static_front.py`（= repo 的 `docs/mac_migration/static_front.py`，8001 靜態前台，只綁 127.0.0.1，`/api/*` 轉給 8000），根目錄是 Mac 上 OneDrive 的 `TXO-GEX-Dashboard`；RunAtLoad＋KeepAlive。Dell `TXO-Static-Front-8001` 的 Mac 版，屬唯讀靜態服務，兩台同跑不衝突。安裝日期未確認（腳本檔日期 11/10，推測當時裝的）。留著即可 |
| macOS 27.2.1 更新 | **已完成（11/22 晚實測 `sw_vers`＝27.2.1）**；「自動安裝 macOS 更新」已關（`AutomaticallyInstallMacOSUpdates`＝0）。之後只在週末手動更新，更新後重跑 `launchctl list \| grep com.txo` 確認四個服務＋static-front 起來。重開機後 optrec／op666／live-price／static-front 都有 PID，watchdog 無常駐 PID（疑為定時工作，`watchdog.log` 不存在＝沒事件）。**Mac「遠端登入」是 Off**，所以 Dell 連不上 Mac（SSH port 22 拒絕）；要不要打開由使用者決定（系統安全設定，Claude 不自己開） |
| Lumi 側 | `fix/tv-cross-platform-keys` 是否 push 要先問使用者；GITHUB_TOKEN 約 12/23 前換；Dell 17 個停用 Lumi 任務約一週後再刪；`Haiqi-TV-Auto-Sync` 失敗待處理；`TXO-Probe-Publish-Day/Night` 刪除要同意 |

**踩過的坑（已查證）**
- **OP666 錄製器每 200 行才 flush**（`op666_recorder.py` 第 226～228 行）：休市時每分鐘只有 4 筆心跳，檔案約每 12～13 分鐘才更新一次，所以不能用「檔案修改時間／最後一筆時間」判斷卡住；強制重啟還會丟掉未寫入的暫存。看門狗因此只在交易時段檢查 OP666（門檻 600 秒）。我 11/22 因此誤判兩次（以為 Dell 被擠掉、看門狗誤報），已更正。
- Dell `.env` 是 CRLF：複製到 Mac 要 `tr -d '\r'`，否則金鑰多一個 `\r`。
- 檔案修改時間不可信；用每分鐘事件數（讀 `"rx"` 時間戳）判斷有沒有缺口。
- Dell 報價服務日誌自 11/21 16:35 起每分鐘約 2,000 筆「Connection is already closed」（週末休市時反覆換夜盤重新訂閱）：舊問題，非 Mac 造成；平日是否消失待看。
- 富邦同帳號 Dell 與 Mac 同時登入，休市時兩邊都正常；**開盤後是否互相擠掉未驗證**。

**明天（週一 11/23）08:50 後要驗證**
1. Dell 與 Mac 的 OP666 都在成長（用每分鐘事件數比，不要看檔案時間）。
2. `txo-private\jj_momentum\history\jj_20261123.jsonl` 出現並成長（證明動能鳥自己啟動）。
3. 兩邊選擇權報價鏈 `health_*.csv` 的 status 都是 ok。
4. Mac 的 `~/AI/watchdog/watchdog.log` 看有沒有重啟或限流暫停紀錄。
5. 都通過後才規劃切換（葡萄先、再富邦期貨 K）；Dell 關機是最後一步。

### 2-00b 未 commit／分支盤點與整合（2026-11-22；Lumi 與 TXO 兩個 repo，只列現況與待辦）

**已 push（11/22 使用者核准，只這 3 筆）**

| 專案 | 內容 | 目的地 |
|---|---|---|
| TXO | 搬遷文件、`docs/mac_migration/`、本檔（`1a9230b`） | main（純往前） |
| TXO | `claude/bold-galileo-dy1oxb`（專案地圖 `tools/build_project_map.py`、`docs/PROJECT_MAP.md`） | 同名分支，沒進 main |
| Lumi | `fix/tv-cross-platform-keys`（macOS 快捷鍵用 Meta；fetch 失敗會通知） | 遠端新分支，沒進 main，Mac 要用時 fetch 該分支 |

**只在本機、沒 push**

| 分支（本機） | 內容 | 狀態與限制 |
|---|---|---|
| TXO `integration/desk-20261122`（暫時 worktree `AppData\Local\Temp\txo-wt-integ-1122`） | 交易室開發版 `desk-friction-guard` ＋ origin/main ＋ Dell 服務分支 `worktree-option-quote-recorder`，另帶 Dell 執行中版本才有的 `run_service.ps1`（w0／monitor2／patrol2）與 `server.py`（Tailscale 位址） | 單元測試 316 個全過、對最新 origin/main 試合併 0 衝突；**含私有文件與 Tailscale 位址，不可推公開 repo**；**尚未部署到 Dell**（搬遷期間交易室程式凍結）。衝突解法與依據在 commit message |
| Lumi `claude/migration-wip-20261122`（暫時 worktree `AppData\Local\Temp\lumi-wt-wip-1122`） | 共用資料夾 6 個已修改檔＋17 個沒有備份的新檔（V6／溫哥 BP／葡萄回測報告與腳本） | **只當備份，不可合進 main**：它的 `send_tg_alert.ps1`、`fetch_chip_data.ps1` 是舊版，origin 已有 11/17、11/18 的新措辭與守門員（PR #6），合進去會蓋回舊版 |
| 其餘舊分支 | TXO：`desk-friction-guard`（88／510，9 衝突，已整合進上列分支）、`jj-order-lines`（1 衝突）、`op666-chip`（2）、`release-wall-def`（9）、`mac/screener-cache-runner`（0 衝突，是否 Mac 選股快取要用**未確認**）；Lumi：`tg-wording-20261112`（已被 origin 新版取代，不建議整合） | 試合併結果見 `branch-hygiene` skill 的做法重跑；舊分支內容我沒逐一讀過 |

**衝突根因（已查證部分）**：交易室程式在 main 與開發分支各 commit 了一份（cherry-pick 沒加 `-x`，hash 不同，對應 `4726e90`／`a7336d6` 與 dfg 的 `018b1da`／`97753bc`），之後各自再改 500 多個 commit → 合併時 add/add。「當初為什麼分開」是推測。

**還留在共用 TXO 資料夾的未 commit（沒動）**：引擎重新產生的 11 個 `data/*` 檔（建議丟掉不 commit，GitHub Actions 每天會自己推）；`social_video_sample/out/` 1,080 個檔 168MB（應進 `.gitignore`）；社群合規文件與腳本（`docs/SOCIAL_COMPLIANCE_*`、`scripts/compliance_check.py`、`scripts/post_social_cards.py`，屬社群工作線）；根目錄的 PPT／PDF（依文件規則 4 不可 `git add`）。暫時資料夾裡約 15 個舊 worktree 有 150～330 個「已刪除」檔，是空殼殘骸，可整批 `git worktree prune` 後清掉（不要 `--force` 批次刪）。**Lumi 共用資料夾**另有 `log/`（728K 舊日誌）等未 commit 檔，沒動。

**待辦**
1. 使用者決定：`mac/screener-cache-runner` 是否要推；`integration/desk-20261122` 何時部署到 Dell（建議搬遷穩定後、先備份、有人盯著）。
2. 整合另外 3 條舊分支前先跑 `git merge-tree` 試合併，一次一個主題。
3. 把 `social_video_sample/out/` 等生成物加進 `.gitignore`（需使用者同意，動到 tracked 的 `.gitignore`）。
4. 搬遷切換前，Lumi 要用的 `fix/tv-cross-platform-keys` 是否合進 main，要先問使用者；Lumi 共用資料夾的舊版修改不要用來覆蓋 origin。

### 2-0 交易室軌道 A：幕僚鳥／研究員（2026-11-16 交接，只列現況與待辦）

**程式位置**：開發版在 `C:\Users\mingi\txo-wt-desk-friction`（分支 `desk-friction-guard`，commit 皆只在本機、**未 push**；最新 eab972f）。執行版在 `C:\Users\mingi\txo-private\desk\intel`（幕僚鳥 `staff_bot.py`、`quota_gate.py`、`intel_jobs.py`）與部署資料夾 `.claude\worktrees\option-quote-recorder\trading room`（橋接 `advisor_bridge.py`，埠 8765）。**改執行版前一律先備份**到 `txo-private\desk\deploy_backup_20261111\`，並先問使用者。

| 項目 | 狀態 |
|---|---|
| R_TXF 台指期貨分析師、R_OF（海外期貨，planned）、首頁情報鳥卡片 | 已做；R_FUT 已拆成兩位 |
| 登入過期被誤報成「額度用完」 | 已修並部署（`quota_gate.py`、`intel_jobs.py`）；11/12 使用者已用手機授權重新登入 Claude，橋接實測通過 |
| 幕僚鳥回答漏出「卡片工具」等內部規則 | 已修並部署：`advisor_bridge.py` 呼叫 claude 時加環境變數 `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`（不可改用 `--bare`，會讓登入失效）；已重啟橋接 |
| 幕僚鳥問盤勢可引用即時行情 | 已部署：`quote_block()` 讀本機 `127.0.0.1:8000/api/live_price`，過時／沒開服務都明講無數據，附「漲跌基準不同」提醒（夜盤台指期相對日盤收盤、加權相對前一日收盤） |
| 聊天被拿去開研究任務 | 11/16 已部署：`classify()` 改成預設聊天，只有「研究：」「幫我研究／分析」「派研究員」「完整研究」才排任務，長文（300 字）或網址才當資料 |
| 影片轉文字失敗（`TypeError: metadata_errors`） | 11/16 已把 `av` 19.0.1 換成 16.1.0（退回：`pip install av==19.0.1`）。**只證明錯誤消失，沒用真影片完整跑過；沒查其他專案是否依賴 av** |
| Telegram 幕僚鳥沒有長期記憶（11/17 查明） | 洋洋式記憶早就在橋接（`brain/memory/long_term.json`，目前只有 5 條，ACT-R 淡化、每週整理）；Telegram 走的 `/decide` 刻意無記憶。11/17 已新增橋接 `/chat` 入口（`handle_ask` 去掉圖片、行情改放系統提示不進紀錄），`quota_gate.chat_ask()` 與 `staff_bot.ask_bridge()` 改走它；記憶建議會在回覆後附「💡 要記住嗎？回覆：記住 N 級…」由使用者決定。`/decide`、`/research`（交易員、研究員）不動。已備份（`txo-private\desk\deploy_backup_20261117\`）並部署、重啟橋接與幕僚鳥；開發版 commit 8ef9003（未 push）。單元測試＋暫時橋接 8799 實測通過、實機 `/chat` 讀得到真實記憶；**Telegram 真人聊天尚未驗證**。退回：把備份 3 檔複製回原位並結束 python 程序（15 秒自動重啟） |

**待辦（依序）**
0. 驗證 `/chat`：Telegram 傳「記住：…」→「查看記憶」→ 問一題需要用到該記憶的問題，確認有引用。注意 Telegram 與網頁戰情室現在共用短期記憶與對話紀錄。
1. 使用者在 Telegram 回「重跑」，看任務 #28（含影片）能否跑完收到 ✅；沒收到就看 `txo-private\desk\intel\jobs\jobs.json` 的 error。任務 #18～#22 因重跑上限（最近 3 筆）不會自動重跑，要使用者重貼題目。
2. 驗證聊天修正：在 Telegram 打含「分析」的閒聊，應直接回答、不排任務。
3. 幕僚鳥「智商比洋洋淺」（11/18 16:08 已修兩個明確缺陷，開發版 commit 見 desk-friction-guard 最新一筆，未 push）：查 TG 實際對話發現 ①使用者回覆(引用)訊息時，聊天分支把被引用內容丟掉，幕僚鳥才回「沒看到前面提的 ETF」；②聊天走 claude -p 且 --tools 為空，沒有網搜，問 00993B 公開說明書只能回「我沒有工具」。已修：引用全文併進問題（記憶指令不加前綴）、/chat 開 WebSearch/WebFetch（沿用研究員守門 hook）；實機測 00993B 有搜尋並附來源。備份在 txo-private 的 deploy_backup_20261118_chat。研究任務 29 個失敗 15 個（登入過期最多、額度用完、no_assignment、逾時）：額度與 no_assignment 重試在 11/12–11/17 已修；11/18 21:46 再修三處並部署（備份 deploy_backup_20261118_research）：登入過期改暫停＋每 10 分鐘靜默重試、登入好自動接著跑（只通知一次、24 小時放棄）；指派單兩次不合格改保底指派全部研究員；單一研究員逾時不拖垮整場、備註寫進會議紀錄。單元測試 307 全過，**尚未用真實研究任務完整跑過一場**。11/18 22:00 回顧 14 份完成報告（評等：6 份有實質糾錯價值、7 份卡在未驗證、1 份沒完成；抽查 4 個數字都對，任務 4 的「2.67 誤植」疑為判錯；沒有一份有價位／情境／失效條件；沒做一般聊天對照）後再改並部署（備份 deploy_backup_20261118_value，commit f9fc006）：文書鳥紀錄置頂必填「對交易的含義」（偏多空不動、成立／失效條件、可事後驗證預測）；確認研究時材料和「收到 N 則」對不上會先警告一次；回應輪遇到官方頁面一次可查的事實矛盾要自己查一手來源。**尚未驗證實際效果；「一般聊天 vs 研究室」對照實驗未做。**研究產出對交易員有沒有價值尚未評估（沒讀報告內容）。洋洋是別人的專案，未讀，差距是否來自她那邊的工具／長 session 屬推測。舊紀錄：已查證它每次都是無記憶的單次呼叫、Sonnet、無工具（行情是今天才接）；差距原因屬推測。使用者無法使用老墨「墨寶」，不做 A/B。長期記憶已於 11/17 接上（見上表 `/chat`）；下一步：記憶只有 5 條要靠使用者累積、接 GEX／籌碼資料給它引用（新功能，需先和使用者定範圍）。
4. 仍開著：R_TXF 開盤前 08:30 排程（只有草稿，未建立，需使用者同意，不可動既有排程）；交易室遠端觀看方式（Tailscale 私人連結 vs 只放報告頁，使用者沒選）；其他研究員、研究員→交易員資訊流、幕僚鳥進績效會議、主題追蹤。
5. 未驗證／已知：真額度也撞過一次（任務 #24「session limit」，11/12 02:30 恢復）；夜盤行情漲跌基準不同不是 bug，但提醒要保留在行情區塊；runner 資料夾 `C:\Users\mingi\txo-klines-runner` 有與 GitHub 相同但顯示未 commit 的檔案，要 pull 前先告知使用者。
6. 登入再過期時：使用者家裡電腦開終端機 `claude` → `/login`；遠端時可在新視窗叫 Claude 執行 `claude auth login --claudeai`（需用 FIFO 保持程式等待、使用者在手機授權後把代碼貼給 Claude）。登入代碼不要存檔。

### 2-0b 交易室軌道 B：多策略帳戶（買方／突破／溫哥 BP）（2026-11-18 起，開發中）

**設計與討論全文（含點子發想、未來規劃）**：私人資料夾 `C:\Users\mingi\txo-private\desk\strategies\MULTI_STRATEGY_DESIGN_DRAFT_20261118.md`（不在 git，內有策略數字）。這裡只留現況與待辦。

**帳戶對照（代號＝策略）**

| 代號 | 策略 | 誰下單 | 狀態（11/18） |
|---|---|---|---|
| T0 | 收租（賣方價差） | 台選鳥 AI | 運行中，規則沒動 |
| T1 | 收租＋看 TG 訊號 | 台選鳥 AI | 只在設定檔，沒看到帳本 |
| T2 | 買方／突破（bull_call_debit、bear_put_debit、long_call、long_put） | 台選鳥 AI | 設定與風控已寫；**已部署並常駐（2026-11-20 00:27）**：提示詞 SYSTEM_DEBIT＋手冊 `playbook_debit v0`；排程 `TXO-Desk-monitor2`／`TXO-Desk-patrol2`（登入自動啟動，由 `autostart/run_service.ps1` 的 monitor2／patrol2 帶 T2），第一次決策 T2-D1 = no_trade 正常；備份在 `txo-private\desk\backup_20261120_t2deploy`；T0 服務未重啟（行為不變）。已知限制：標的價格停損不會自動盯，靠 AI 叫醒時判斷 |
| W0 | 溫哥 BP 順勢（S 版 `wenge_bp_spread`＝bear_put_debit；L 版 `wenge_bp_single`＝單買 Put，僅模擬實驗） | 程式機械下單，不叫 AI | **11/18 15:24 已部署並以 `--dry`（只評估、不下單）常駐**；開發版 commit `2cf60cb`（分支 desk-friction-guard，未 push） |

**已做（開發分支 `txo-wt-desk-friction`，未 commit、未部署）**：`desk_config.json` 新增 T2、W0 與 `debit_profile`；`decision.py` 新增兩種買進價差結構、`stop_loss_pct`／`take_profit_pct`、帳戶改讀設定檔；`risk.py` 買方帳戶不套 IV 氣墊、結構清單與單買 DTE 各帳戶獨立、買方價差腿驗證（`naked_shorts(any_strike=True)` 只給買方帳戶）；`book.py` 買方以權利金損益 % 出場、單筆權利金上限 2% 淨值、淨付出須 >0、一開就停損擋下。新增 `tests/test_debit.py` 18 個測試，全部 274 個測試通過。紅線沒放鬆：不追價閘門與整組平倉仍適用買方。

**【11/19 T2 提示詞與手冊（開發版 commit f04e892，分支 desk-friction-guard，未部署、未 push）】** `runner.py` 新增 `SYSTEM_DEBIT` 與 `system_for(desk)`：買方帳戶（profile=debit：T2、W0）用買方提示詞（4 個買方結構、`stop_loss_pct`／`take_profit_pct`、權利金上限 2%、不追價、DTE<3 只能價差、不可階梯），賣方帳戶 T0/T1 不變；`book_summary` 買方持倉顯示「權利金 -35%／+20%」；`run_slot.read_playbook(profile)` 買方讀 `brain/desk/playbook_debit.md`，沒有就顯示「手冊尚空」，不會拿賣方手冊。新增 4 個測試，全部 316 通過。**手冊草稿在私有資料夾 `txo-private\desk\strategies\PLAYBOOK_DEBIT_DRAFT_20261119.md`，使用者確認前不寫入 `brain/desk/playbook_debit.md`。** T2 的 monitor／patrol／run_slot 常駐尚未設定（不啟用就不會下單）；`review.py` 每日覆盤仍只有賣方提示詞；手冊裡的時間停損，T2 只能靠 AI 自己 close。

**【11/19 T2 買方手冊已啟用（檔案層）】** 使用者確認後，已把 `PLAYBOOK_DEBIT_DRAFT_20261119.md`（第二版，wall_fade 主測＋breakout_pullback 對照）寫成 `trading room/brain/desk/playbook_debit.md`（gitignored），放在執行用工作樹 `.claude/worktrees/option-quote-recorder` 與開發版兩處。**但執行用工作樹還沒部署新的 runner.py／run_slot.py（開發版 commit f04e892、1e22c4e），T2 也沒有常駐排程，所以目前 T2 不會讀手冊、也不會下單。** 部署步驟同前（備份→複製 runner.py、run_slot.py、測試→重啟 monitor／patrol），再為 T2 設定 monitor／patrol／run_slot 排程；第一次要有人盯著。已知限制：標的價格停損無法由程式自動盯，只靠 AI 被叫醒時判斷。研究腳本與回測紀錄在私有 `strategies/`（wall_study*_20261119.py、MULTI_STRATEGY_DESIGN_DRAFT 的 11/19 條目）。

**使用者決定（11/18）**：先照「共用買方基礎 → 再分帳戶」；突破策略等九轉竭盡或回檔才進（不追價）；買方策略開 T2 獨立帳戶，並另開 W0 記錄溫哥 BP；先做 W0 下單器。

**待辦（依序）**
1. **W0 下單器部署**（已寫完，尚未部署）：開發版 `desk/w0_runner.py`（讀葡萄記錄器維護的 `txo-private\desk\grape\kbars_1m.csv`（只讀，超過 6 分鐘沒更新就「無決策」）、呼叫私有 `desk_indicators/wenge_bp.py` 評估條件 1~8、選價（近月優先、DTE≥2、買腳 Put 賣價 95±10 點、賣腳下 200 點）、同訊號同時開 4 個標籤：當沖版 S `wenge_bp_spread`／L `wenge_bp_single`、留倉版 S `wenge_bp_spread_hold`／L `wenge_bp_single_hold`；當沖版與留倉版各自一次只持有一組）。出場：權利金 +20%／−35% 由 `monitor.py W0` 盯盤；時間停損（60 分鐘未賺 +10%）、價格停損（5 分 K 收盤站回 MA20）、**當沖版每個時段出清（日盤 13:25、夜盤 04:55，不留倉）**、留倉版強制出場（DTE≤1 13:25、DTE 0 12:30）由下單器做。每次評估寫 `txo-private\desk\W0\w0_eval.jsonl`（條件、數值、結果）。測試 `tests/test_w0_runner.py` 25 個，全部 299 個通過。**【11/18 部署紀錄】實際常駐的 desk 服務跑在 `.claude\worktrees\option-quote-recorder\trading room\desk`（不是開發版資料夾）。已備份舊檔到 `txo-private\desk\deploy_backup_20261118\`（book.py decision.py risk.py desk_config.json），複製新版＋`w0_runner.py`＋兩份測試進去；T0 當時 0 持倉 0 掛單，重啟 monitor／patrol／server 成功。`autostart\run_service.ps1` 新增 `w0`（`w0_runner.py --dry`），註冊排程 `TXO-Desk-w0`（登入啟動）。那個工作樹還有別的視窗未 commit 的檔案（agents.json、server.py、fut_brief.py 等），我沒碰；我改的檔案在那邊也尚未 commit。**退回**：把備份複製回去、停 `TXO-Desk-w0`（`Stop-ScheduledTask`＋`Unregister-ScheduledTask`）、重啟 monitor／patrol。**開下單的步驟**：看完一個完整時段的 `w0_eval.jsonl` 後，把 `run_service.ps1` 的 `--dry` 拿掉、另外常駐 `monitor.py W0`（盯停損停利），第一次要有人盯著。live 工作樹跑全套測試 181 個有 1 個失敗：`test_research_room.test_max_analysts_cap`（3≠4），與本次改動無關（不碰 research room），疑與該工作樹未 commit 的 agents.json 有關，未查。****【11/19 夜盤觀察與選價改版】** 昨夜 163 次評估無中斷、條件 1~5 全成立僅 2 次（04:20、04:25），皆無法下單：VIX 約 49 時 95 點權利金的 Put 在 37,400~37,500（離現價約 2,500 點、彩券），且集中在剩 1 天的週選被 min_dte 2 濾掉。使用者決定改距離版：買腳＝現價下 200±100 點最近的有效報價履約價（`select_mode: distance`，原版 `premium` 仍可切換），失敗原因改列每個到期日。已部署（備份 deploy_backup_20261119_w0pick，commit 見 desk-friction-guard 最新一筆）、W0 仍 `--dry`。以昨夜報價鏈重放（現價用 call-put 平價粗估，僅供參考）：約 27% 的 5 分鐘時段能選到有效報價，限制來自買賣價差（高波動時常 >20 點）而非距離容許值；選到時價差淨付出中位約 100 點（5,000 元，在 2% 上限內），**單買 Put 買腳中位約 655 點（約 32,750 元）超過單筆 2% 上限，L 版多半會被擋**。待決定：是否放寬 W0 的買賣價差門檻（會增加摩擦成本）、L 版是否調整上限。**部署步驟（原）**：①備份執行版 `book.py decision.py risk.py desk_config.json` 到 `deploy_backup_<日期>`（這幾支 T0 也在用，改了要重啟 T0 的 monitor／patrol）②複製 `w0_runner.py` 與測試 ③用 `desk/autostart/run_service.ps1` 註冊常駐（下單器＋`monitor.py W0`）④第一次先 `--dry` 看一個交易時段的評估紀錄。**出場 B（5K Pine 標的價位出場）、5K 型態分標籤 `wenge_bp_5k`、L 版以外的 A/B 對照共 8 條戰績線、戰績總表（規格 7.2）都還沒做。**
   - **使用者決定（11/18）**：條件 6、7 改只記錄不篩選（`log_only_conditions`）；進場閘門＝條件 1、2、3、4、5＋「離出清不到 30 分鐘不新進」（取代私有模組裡的條件 8）；當沖版為主、留倉版另標籤對照。以下「發現」段保留作脈絡。
   - **發現（脈絡）：條件 7「IV ≤ 16%」在目前行情幾乎不會成立**——11/18 期交所 VIX 約 49.5，W0 在高波動期不會進場；而使用者的想法正是「高波動改做買方」。**更正歸屬（使用者 11/18 指出）：條件 5～8 不是溫哥說的，是 Lumi 規格作者（我們自己的視窗）加的**；溫哥原話只有規格第 1 節那幾項（只買 P、各週期 MACD 在 0 軸下、30/60 分力道向下、權利金 90～100 點、停利約 20%、緩跌也可買）。條件 7 的出處是 `OPTIONS_IV_QUANT_STRATEGY_GUIDE.md`。**我沒有核對過 LINE 對話截圖**，只讀了規格文字；截圖原件是否還在、與規格第 1 節是否一致，未驗證。處理方式已於 11/18 決定為只記錄不篩選。
   - 設計值（Lumi 規格沒寫、我自訂、未回測）：min_dte=2、權利金 95±10、一次一組、條件5 chase_ok＝不在急拉急殺≥500 點且無竭盡、條件6＝現價在 Zero Gamma 之下、前日 IV＝即時 IV−taifex_vix_change。全部放在 `desk_config.json` 的 `w0` 區塊，標 status。
2. T2 的提示詞與 `playbook_debit` 手冊（分帳戶提示詞段落，`runner.py` 目前只有賣方版）。
3. 盤面標籤（regime）：程式依 IV、近 60 分鐘振幅、GEX 正負 Gamma 算「盤整／高波動／觀望」，先只寫帳本不下單，觀察幾週；高波動門檻要用歷史快照統計，不憑感覺。之後才開 T3（自動切換）與 T0、T2 對照。
4. 部署前一律先備份到 `txo-private\desk\deploy_backup_<日期>\` 並問使用者；開發版 commit 與 push 都要使用者同意。

**未解**
- 使用者說過「有一個獨立帳戶來記錄模擬單」，11/18 查了程式、設定檔、文件與 12 個以上舊聊天（關鍵字：模擬單、交易室、手動下單、我的模擬、獨立帳戶）。**最可能就是溫哥 BP 那句**：11/06 Lumi 視窗（`local_1baaddcb`「溫哥 BP 策略與 GEX 分析」）使用者的原話是「傳到 TXO 專案給台選鳥交易員使用，並**另外記錄這個策略的模擬單戰績**，然後一樣定期檢討和優化」，規格在 `給TXO視窗_溫哥BP順勢策略_台選鳥模擬與戰績追蹤_20261104.md`（Lumi 資料夾）；TXO 端規格視窗是 `local_bc692bc9`。這個需求就是 W0。**尚待使用者確認**是否另外還有「記錄自己手動單」的帳戶（若有，暫名 H0：使用者登記、同一套報價與成交模型、帳本分開）。
- **W0 條件逐條檢討（11/18，使用者要求；使用者的前提：溫哥把 BP 當小台在打，應是很短、條件嚴苛的當沖單，此為使用者推測、未驗證）**：溫哥原話只支撐條件 2、3（各分 K MACD 0 軸下、30/60 分力道向下，週期組合與「柱狀體比前一根小」是規格作者的操作化定義）；條件 4 來自使用者自己的均線戰法；條件 5 是專案紅線（不可刪）；條件 1 是資料紀律；條件 6、7、8 與 W0 現有的持有規則（min_dte=2、DTE≤1 強制出場、60 分鐘時間停損）都是我們自加或自訂、無溫哥出處。建議（待使用者決定）：2、3、4、5、1 為進場閘門；6、7 改「只記錄不篩選」（規格 7.2 本來就要拆「條件 6 成立 vs 不成立」的勝率，擋掉就沒法比；且對買 Put 的短線單，IV 隨急殺上升不一定不利，屬推測）；8 改成「收盤前 N 分鐘不新進」配合當沖出場；持有改成「當沖版」（時段收盤前一律出清、不留倉），留倉版另開標籤對照；min_dte、時間停損分鐘數用已記錄的資料校準，不憑感覺。條件全疊會讓訊號太少（葡萄記錄器 8 天只有 13 筆 🍇），30 筆前不下結論。
- 同類獨立帳戶規格還有：**R1＝ORB 開盤區間突破機械式紙上帳戶**（`給TXO視窗_ORB機械式紙上帳戶_20261030.md`，Lumi 資料夾，買進價差 Bull Call／Bear Put、虧 50% 停損、賺最大獲利 70% 停利、13:25 出清，**程式未實作**）；葡萄前瞻記錄器（`txo-private\desk\grape`，常駐，只記訊號與 60 分鐘結果、不下單）。T2、W0 做完的買方基礎可直接給 R1 用。
- 買方策略有效性沒有證據：收租單 18 組 1 勝只能說「這段波動期收租表現差」，不能推出買方會賺。買賣價差摩擦實測 10～16 點，買方價差單權利金小、受影響更大；停損 35% 可能常被「一開就停損」擋下，成交率要看真實報價。

**點子（尚未決定，不要當定案）**：高 IV 時買價差優於單買（可抵一部分 IV 回落風險，推測待回測）；路由器先用程式規則，不讓 AI 自由選策略（49 筆決策標籤幾乎全不重複）；T3 與 T0、T2 對照才能證明「會切換」比「固定」好；W0 與 T2 可對照「規則選」對「AI 選」。

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
| 21 | 清理本機殘留 worktree／分支（`.git`、`.claude` 有繼承的 Everyone DENY 刪除權限）：**不要再用 `--force` 批次刪**，會留下半殘；保護分支 `backup/shared-folder-39d04e6-20260930`、`claude/elegant-heisenberg-b65af4`（有他人未 commit 的 `room.js`）要保留 | 10/04 I | 使用者決定先留著。**2026-10-31 狀態**：`OneDrive\文件\` 下 7 個暫時副本 `txo-wt-1007／colors／day／docs／handoff-key／nightmis／wf-fix`（各約 56～66MB）：1007／colors／handoff-key／nightmis／wf-fix 五個已全併入 main；用 `git worktree remove`（不加 `--force`）試過一次，仍報 Permission denied，結果是**登記已被 git 移除、資料夾還在（各少 1 個檔案）、`.git/worktrees/` 殘留空登記**，不影響運作，內容無遺失，分支都還在。這 5 個資料夾已由使用者於 2026-10-31 刪除（`.git/worktrees/` 的 5 個空登記殘留仍刪不掉，不影響運作）。`txo-wt-day`（10/06 的 11 個引擎產生檔，之後 main 已重新產生 200～334 次）與 `txo-wt-docs`（10/06 的觀察紀錄，main 的同日紀錄更新、已涵蓋）**2026-11-01 比對確認沒有獨有內容，可刪，尚待使用者動手**。**不可刪**：`TXO-runner-data-backup`、`.claude/worktrees/option-quote-recorder` |

### 2-3 長期未解（不要說已解決）

| 事項 | 現況 |
|---|---|
| ADX 與 TradingView 不一致 | 微台 15M／4H 一致；1H（我們 50.2 vs TV 55）、日線（差在 TV 含夜盤）不一致，試過 4 種對齊都不是。**不要說「已對齊」** |
| JJ（rStock）大戶散戶動能公式 | **紅黃線已於 2026-10-20 破解**（紅＝MIS 委買口−委賣口、黃＝委買筆−委賣筆，來源 MIS `getQuoteDetail`；綠＝外盤成交筆−內盤成交筆；詳見使用者私有資料夾 `txo-private/jj_momentum/FINDINGS_20261015.md`，公式只放私有資料夾）。此行取自專案記憶，我沒有重新驗證程式端是否已套用；舊探索紀錄在 `docs/JJ_RSTOCK_MOMENTUM_EXPLORATION.md` |
| 動能鳥未對照 TV 驗證 | 畫面有誠實標示，錄影／截圖不要特別展示 |
| 官方對帳 `python scripts/audit_vs_official.py --sample 0` | 10/20：1,485 項一致、3 項不一致（Max Pain 4 個到期、Call Wall 設計、對帳程式把夜盤當日盤）、7 項略過。**不要說 FAIL=0** |
| 舊 SELF_AUDIT 交接區塊遺留的低優先事項（9/17～9/24 寫的，**未確認是否仍成立**） | ①`futDailyMarketReport` 中文標籤編碼異常，只在 `parse_taifex_fut_oi()` 解過，沒全面搜其他解析點；②戰情室 CL／US10Y／DXY 的 `initOverseasLiveTickStream()` 名不符實、從未真輪詢；③`scripts/build_screener_cache.py` 全域關閉 SSL 驗證（`CERT_NONE`）只回報未修改。原文在 [docs/archive/handoffs/SELF_AUDIT_舊交接區塊_20260915-20260924.md](docs/archive/handoffs/SELF_AUDIT_舊交接區塊_20260915-20260924.md) |
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
