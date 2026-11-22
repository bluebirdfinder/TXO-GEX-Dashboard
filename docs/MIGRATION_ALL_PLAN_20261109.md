# 全專案搬遷安排（Dell → Mac Mini M2）2026-11-09

> 只新增、未 commit、未 push。不含金鑰。上位文件：[MIGRATION_STATUS_20261104.md](MIGRATION_STATUS_20261104.md)、[今晚手冊](MIGRATION_TONIGHT_RUNBOOK_20261109.md)。
> 標示：✅ 已讀到／已測 ｜ ⚠️ 推測 ｜ ❌ 未驗證。Mac 端的腳本**全部未在 Mac 實測**。

## 1. 已準備好的東西

| 檔案 | 用途 | 驗證 |
|---|---|---|
| [mac_migration/setup_lumi_mac.sh](mac_migration/setup_lumi_mac.sh) | Mac 端環境準備：檢查、clone Lumi、建 venv、裝套件、列出你要自己放的檔、跑 `--dry-check`。**不啟用任何排程** | ✅ bash 語法檢查通過；❌ 未在 Mac 跑 |
| [mac_migration/make_lumi_plists.py](mac_migration/make_lumi_plists.py) | 產生 Lumi 3 個排程的 launchd 檔（LaunchAgent） | ✅ 在 Dell 產生並讀回，時間與 Windows 排程一致；❌ 未載入 |
| [mac_migration/run_lumi_task.sh](mac_migration/run_lumi_task.sh) | 排程包裝：載入 `~/.lumi_env`、用 venv 執行、寫日誌 | ✅ 語法通過；❌ 未在 Mac 跑 |

## 2. 分階段時間表（越早越好，但被兩個東西卡住）

```
卡點 A：富邦 SDK 在 Mac 能不能跑   → 決定 TXO 即時報價／錄製能不能搬
卡點 B：TXO 程式寫死 C:\Users\mingi → 不改，搬過去就壞

階段 0 ─ 今晚        Lumi 3 個本機排程（不依賴 A、B）
階段 1 ─ 週二 11/10  富邦 SDK 實測（日盤 08:45～13:45 才看得到即時報價）＋改寫死路徑（在分支）
階段 2 ─ 週二～週五  Mac 並行乾跑 TXO 非富邦部分（Static-Front、Screener-Cache、Intel/Staff-bot）
階段 3 ─ 週末 11/14～15（最早）TXO 富邦服務切換
階段 4 ─ 切換後 1 週 觀察，之後清理 Dell
```

**為什麼 TXO 富邦服務最快是這個週末：** 它們整週交易日都在收資料，漏掉富邦 K 線補不回來（盤點文件）。只有休市窗口才能停。若階段 1 發現 SDK 在 Mac 跑不了，階段 3 取消，改成「Dell 收資料、Mac 跑其餘」。

## 3. 每日運行項目完整對照

| # | 項目 | 類型 | 搬到 | 階段 | 依賴／備註 |
|---|---|---|---|---|---|
| 1 | Lumi-TV-Auto-Sync（每 15 分） | 本機 | Mac | **0 今晚** | `tv_session.json`、Chrome、有畫面登入、`~/.lumi_env` |
| 2 | Lumi-KBar-Collector（09:30） | 本機 | Mac | 0 | `kbar_data/` 要先複製；今天 09:30 SSL 失敗（原因未查） |
| 3 | Lumi-Option-Archiver（09:30／19:30） | 本機 | Mac | 0 | `option_data/`（55 MB）要先複製 |
| 4 | TXO-Static-Front-8001 | 本機 | Mac | 2 | 純靜態前端；⚠️ 路徑待確認 |
| 5 | TXO-Screener-Cache（平日 16:30） | 本機 | Mac | 2 | 要私有資料夾 `txo-private\screener-indicators`；❌ Mac 沒有 |
| 6 | TXO-Intel-bot／extract／jobs／daily、TXO-Staff-bot | 本機 | Mac | 2 | 路徑寫死 `C:\Users\mingi`；用 Claude；金鑰在 `txo-private\desk\intel`；同一 bot 金鑰**不可兩邊同時跑** |
| 7 | TXO-Desk-bridge／monitor／patrol／recorder／server | 本機 | Mac | 2～3 | 同上；recorder 可能依賴富邦（❌ 未讀） |
| 8 | TXO-Live-Price-Server | 本機 | **視 SDK** | 3 | 富邦 Neo SDK；推送後要重啟服務 |
| 9 | TXO-Fubon-Futures-Klines（05:30／14:00） | 本機 | **視 SDK** | 3 | 富邦；正本 `~\.txo_local_store`（48 MB） |
| 10 | OP666_Recorder | 本機 | **視 SDK** | 3 | 富邦；`txo-private\op666_record` 3 GB 不可重建 |
| 11 | TXO-Probe-Publish-Day／Night | 本機 | **不搬，刪除** | 隨時 | 量測用，早該結束；刪除要你同意 |
| 12 | 群益 `C:\Capital\*` 腳本 | 本機 | **留 Dell** | — | `SKCOM.dll` 是 Windows 元件，兩個視窗都這樣說 |
| 13 | TXO `auto_update.yml`、Cloudflare Worker cron | 線上 | 不搬 | — | 與電腦無關 |
| 14 | Lumi `daily_run.yml`（8 條 cron） | 線上 | 不搬 | — | PR #2 減量未合併 |
| 15 | Claude 排程：`op666-daily-report-reminder-weekdays`、`yangyang-interests-monthly-refresh` | Claude App | 看用哪台開 App | 3 | **只在 Claude App 開著時跑** |
| 16 | 洋洋 | 本機 | 已在 Mac | 完成 | Dell 14 個已停用 |

## 4. 不在 git 裡、必須手動搬的東西

| 東西 | 大小 | 用在哪 | 搬法 |
|---|---|---|---|
| `tv_session.json`、`tv_sync_state.json`（Lumi 資料夾） | 小 | #1 | 使用者複製；**不進 git、不貼對話** |
| Lumi `kbar_data/`、`option_data/` | 3 MB、55 MB | #2、#3 | OneDrive 或隨身碟 |
| `~/.lumi_env`（兩個 Telegram 變數） | — | #1 | 使用者自己建 |
| TXO `.env`（富邦金鑰等） | 4 KB | #4～#10 | 密碼管理器；**不放任何備份或雲端資料夾** |
| `~\.txo_local_store` | 48 MB | #9 | 複製；11/01 備份已有，但之後有新資料 |
| `txo-private` | 5.5 GB | #5～#10 | 隨身碟（`D:` 備份 11/01 版）；**不上 OneDrive** |
| `trading room\brain`（幕僚鳥記憶） | 0.5 MB | #6、#7 | 複製 |
| 富邦 SDK 安裝檔與憑證 | — | #8～#10 | 使用者向富邦取得；憑證不經我手 |
| Claude 設定 `~/.claude` | — | 全部 | 兩檔未同步（`CLAUDE.md`、`settings.json`），等你決定 |

## 5. 切換規則（所有項目共通）

1. **同一時間只有一台執行同一個排程。** 切換 = 先停 Dell（或建暫停檔）→ 啟 Mac。同一個 Telegram／TradingView 帳號兩台同時跑會重複寫入、重複推播。
2. 先乾跑、再切換；切換後 Dell 的對應排程**停用不刪除**，保留一週當退路。
3. 退回 = 停 Mac、啟 Dell，並把 Mac 期間累積的資料複製回來。
4. 夜盤、日盤進行中不停富邦服務；停機窗口見 [今晚手冊](MIGRATION_TONIGHT_RUNBOOK_20261109.md)。
5. `git push` 一律先問你；共用資料夾不做 git 狀態變更。

## 6. 今晚（階段 0）執行順序

```
A. Mac：bash setup_lumi_mac.sh（我帶你看輸出）
B. 你：建 ~/.lumi_env、複製 tv_session.json／kbar_data／option_data、關螢幕鎖定、裝 Chrome
C. Mac：.venv/bin/python tv_auto_sync.py --dry-check  → 貼回輸出（不含金鑰）
D. Mac：python make_lumi_plists.py --root ~/AI/Lumi-Chip-Bot --out ~/Library/LaunchAgents
E. Dell：建 tv_sync_pause.txt、停用 Lumi-KBar-Collector 與 Lumi-Option-Archiver
F. Mac：launchctl bootstrap gui/$(id -u) 三個 plist
G. 明早 05:30 後：核對 TradingView 6 個點位與 TG 晨報
退回：Mac launchctl bootout；Dell 刪 tv_sync_pause.txt、啟用兩個排程
```

## 6-B. 階段 0 實際進度（2026-11-10 00:15 更新）

- ✅ Mac 腳本放在 `~/AI/lumi_migration/`；Lumi 為私有 repo，Mac 用「只讀 Lumi 的細粒度權杖」clone（`useHttpPath` 讓憑證獨立、不蓋掉洋洋那組；權杖 90 天到期，約 2027-02-08 前要換）。
- ✅ `--dry-check --now "2026-11-09 23:50"` 在 Mac 回「相同，跳過」→ 算法與 Dell 一致。
- ✅ `tv_apply_daily_params.py`（預設 dry-run）在 Mac 讀到面板當前值 = 乾跑值 → 登入憑證有效。⚠️ 該腳本單獨執行讀的是 Lumi 資料夾 9 月舊檔，**不可加 `--apply`**。
- ✅ Mac 載入 `com.lumi.tv-auto-sync` / `kbar-collector` / `option-archiver`；TV 排程試跑 exit=0。
- ✅ Dell 停用 `Lumi-TV-Auto-Sync` / `Lumi-KBar-Collector` / `Lumi-Option-Archiver`（改用停用而非暫停檔：暫停檔在窗口內每 15 分鐘會發一則 TG）。退回 = Dell `Enable-ScheduledTask` 三個 + Mac `launchctl bootout gui/$(id -u) <plist>`。
- ❌ 待驗：11/10 05:30 後 Mac 是否真的寫入並發 TG；09:30 kbar/option 是否成功。

## 6-C. 2026-11-10 事件：Mac 的 TV 更新失敗，已退回 Dell

- 現象：06:17 起 Mac 每 15 分鐘重試，Telegram 回報「6 個快訊找不到 Condition 選項」；面板仍是舊值（使用者截圖證實）。
- 原因（程式碼推斷＋與症狀吻合，Mac 日誌未逐行驗證）：`tv_apply_daily_params.py` 第 186 行 `Control+A`、第 369 行 `Control+s` 在 Mac 的 Chromium 不是全選／存檔 → 面板新值沒寫進去、版面沒存 → 程式重新載入頁面，改動被還原 → 下拉清單裡沒有含新點位的選項。
- 為什麼乾跑沒抓到：`--dry-check`／dry-run 只讀不寫，沒走到「輸入數字、存預設值、存版面」這幾步。
- 處置：07:10 左右 Mac 執行 `launchctl bootout gui/$(id -u)/com.lumi.tv-auto-sync` 並停掉相關 python；Dell 重新啟用 `Lumi-TV-Auto-Sync` 並立刻跑，07:22 成功補寫，使用者畫面確認 6 個值正確（43000/42442/42392/40500/42000/40298）。
- 目前 TV 更新由 **Dell 負責**；Mac 只剩 K 線收集（kbar）與選擇權存檔（option-archiver）。
- 修正：Lumi 視窗已在 Lumi repo 本機分支 `fix/tv-cross-platform-keys`（commit 3cbf508 加第二個 commit）做好 Mac／Windows 快捷鍵與 `git fetch` 失敗不再默默吞掉；**尚未 push、未在 Mac 實測**。
- 教訓（寫進所有類似搬遷）：任何「寫入」型排程，切換前必須先在新機器做一次**真實寫入測試**，且要有人看著、舊機保持可退回；乾跑通過不等於能搬。
- **07:32～07:50 Mac 手動驗證（使用者盯著畫面）**：Mac 本機把兩個快捷鍵 sed 成 `Meta+A`／`Meta+s`（未 commit、未 push），7:32 面板改回舊值後執行 → 7:37 成功；7:44 面板與 6 個快訊都改回舊值後再執行（先把 `tv_sync_state.json` 改名強制重做）→ 7:50 成功，面板、6 個快訊、版面都已儲存。**根因確認為快捷鍵。**
- 觀察：`refresh_all_alerts` 每改一個快訊就重新搜尋並從第一個檢查（刻意設計，因為存檔後列表順序會變），約多花 2～3 分鐘；功能正確，列為日後優化，不在盤中改。
- 觀察：快訊編輯視窗的「訊息」欄為 9/26 建立時的文字（48,000…），腳本不改它，與 Dell 行為相同。
- **07:57 Mac 重新接手 TV 更新**：`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.lumi.tv-auto-sync.plist`，首次執行「點位相同，跳過」exit=0。Dell 的 `Lumi-TV-Auto-Sync` 維持**停用**作為退路（Dell 狀態檔已備份：07:22 版）。**Mac 的 `tv_apply_daily_params.py` 有本機修改（Meta+A／Meta+s），不可 `git checkout`**，直到 Lumi 的正式修正 push 並在 Mac 取得。
- 退回 Dell 的方法：Mac `launchctl bootout gui/$(id -u)/com.lumi.tv-auto-sync` → Dell `Enable-ScheduledTask Lumi-TV-Auto-Sync`；若 Dell 因狀態檔相同而跳過，需把 Dell 的 `tv_sync_state.json` 改名強制重做。
- （以下為最初的重搬條件，已達成 (2)，(1) 以本機修改暫代）重新搬 TV 的條件：(1) 修正 push 並在 Mac 拉到；(2) 在 Dell 暫停的前提下，Mac 做一次有人盯著的真實寫入；(3) 成功後才停 Dell。

## 6-D. 2026-11-10 富邦 Neo SDK 在 Mac 的登入測試（只讀，不下單）

- Mac（arm64）裝 `fubon_neo 2.5.0` macOS wheel，用 `docs/mac_migration/fubon_login_test.py` 測：登入成功（0.2 秒）、取得即時行情權杖、查到台指期近月 TXFK6 = 43222。
- **第一次失敗原因有兩個疊在一起**：①「API Key 或密碼」那格誤填身分證字號（訊息：APIKEY尚未申請）；②帳號輸入成全形。第二次填富邦 API Key、全部半形即成功。
- 憑證密碼 = 身分證字號（半形）。憑證檔 .pfx 經 OneDrive 暫存資料夾傳到 Mac（`~/AI/fubon-test/cert/`），Dell 端暫存資料夾已刪；**待辦：使用者到 OneDrive 網頁版回收桶永久刪除 `fubon_cert_tmp` 與 .pfx**。
- **Dell 沒被踢**：Mac 08:35 登入後，08:45 開盤 Dell `live_price_server` 持續收到富邦成交與五檔資料。結論：同一帳號可同時在 Mac 與 Dell 登入（僅驗證開盤時點，未長時間觀察）。
- 結論：富邦服務可搬到 Mac；實際切換（live_price_server、OP666_Recorder、Desk-recorder、Fubon-Futures-Klines）依第 5 節規則，先做有人盯著的真實運行，最早排 11/14–15 週末。**OP666_Recorder 資料不可重建，切換期間兩邊並行、不可中斷。**
- 群益 API 留 Dell（SKCOM.dll 僅 Windows）。

## 6-E. 2026-11-10 Lumi 專案剩餘搬遷項目（Lumi 視窗確認）

- 本機排程（TV／KBar／Option-Archiver）已全搬 Mac；Dell 上 Lumi 相關 17 個排程全部 Disabled。線上（daily_run.yml、tv_daily_param_sync.yml、Cloudflare Worker）不搬。
- 待驗證：Mac 09:30 的 KBar／Option-Archiver 第一次實跑；Mac 16:05 後的 TV 更新（標準：`--dry-check` 對照 → 真寫入 → 按鈕變 All changes saved → 重新載入值還在）。
- 資料：`option_data/`、`kbar_data/` 含實盤紀錄，不進 git，歷史資料要用使用者自己的方式搬。
- Dell 寫死路徑（Lumi 視窗查證）：`send_tg_alert.ps1:83,344`、`tv_webhook_listener.py:20`、`tv_compute_daily_params.py:39`、`market_calendar_advisor.py:64`、`update_tv_pine_defaults.py:34`、`capture_gex_cards.py:15`、`register_option_archiver_task.ps1:13`。找不到會退到 GitHub 公開版（判讀，未實跑驗證）。
- 3 個只在 Dell 的 Lumi 本機分支已 `git bundle` 備份到 `C:\Users\mingi\OneDrive\lumi_branch_backup\`（verify 通過；使用者決定先備份、不推送）。
- 待使用者決定：Actions 額度 PR #2、`cloudflare_worker_lumi_fusion.js` 線上是否已部署。

## 7. 明天（階段 1）要你配合的事

- 週二日盤 08:45～13:45 之間，在 Mac 裝富邦 SDK 並跑登入＋報價測試（約 10 分鐘）。
- ❌ 未知：Mac 登入富邦是否踢掉 Dell 登入；測試時 Dell 的報價服務可能斷線，建議選日盤中段、先告知。

## 6-F. 2026-11-10 夜 階段 2：Static-Front（#4）Mac 試跑

- 重開機後確認：Lumi 3 個排程與洋洋 12 個排程都自動載入（`launchctl list`），Mac 重開不影響。
- Mac 的 OneDrive 已同步「文件」：`~/OneDrive/文件/TXO-GEX-Dashboard`，**不需要另外 git clone**；不要在該資料夾對 Mac 下 git 指令（避免與 Dell 的 OneDrive 同步互相打架）。
- `static_front.py` 不在 git，副本放 `docs/mac_migration/static_front.py`；用環境變數 `TXO_STATIC_ROOT` 指定網頁資料夾，不用改程式。
- 試跑結果：首頁 200、`/api/*` 回 503（Mac 沒有 8000 報價服務，屬預期）。第一次因等待 3 秒不夠回 000，等 8 秒後正常。
- 已建立 `~/AI/txo-static/static_front.py` 與 `~/Library/LaunchAgents/com.txo.static-front.plist`（`plutil -lint` OK），**尚未載入**，Dell 的 TXO-Static-Front-8001 照跑。
- 待辦：階段 3 前處理「開機時 OneDrive 尚未掛載」的啟動時機；切換規則同 §5（先停 Dell 再啟 Mac）。

## 6-G. 2026-11-11 凌晨 階段 2：Screener-Cache（#5）Mac 乾跑通過

- 原本以為「只要複製」是錯的：Dell 版是 PowerShell 腳本，要在獨立 runner 複本跑，且會硬重設到 origin/main，結果寫進 `~\.txo_local_store`（與富邦 K 線 #9 共用同一資料庫）。
- 已在本機分支 `mac/screener-cache-runner`（獨立 worktree `C:\Users\mingi\txo-wt-mac-screener`，commit 8cf66a5、57fb7cb，**未 push**）寫 Mac 版 `scripts/run_screener_cache_task.sh`；副本放 `docs/mac_migration/run_screener_cache_task.sh`。腳本拒絕在含 OneDrive 的路徑執行；乾跑模式（`TXO_SCREENER_DRYRUN=1`）不寫資料庫。
- `txo-private` 快照已複製到 OneDrive `txo-private-mac-copy`（1.58 GB、6,280 檔，排除 `op666_record`、`option_quotes`）。**搬遷完成後要刪除並從 OneDrive 網頁版資源回收筒永久刪除。**
- Mac 乾跑結果：`logs/screener_cache.log` 0 個 ERROR；`screener_cache.json` 為 1423 檔、S 級 50、A 級 347，與 Dell 11/10 16:36 版完全一致。
- 尚未做：真實寫入測試（absorb/backup）、決定資料庫正本、複製 Dell 的 `~\.txo_local_store` 到 Mac、建 launchd 排程（不載入）、停 Dell 的 TXO-Screener-Cache。切換依 §5 規則，建議與階段 3 一起決定。

## 6-H. 2026-11-22 進度盤點與超出原規劃的項目（只讀查證，未改任何服務）

> 本節由搬遷協調視窗於 11/22 寫入。**11/11～11/22 之間本文件沒有更新**，下列為補查結果。標示：✅ 已查證（附證據）｜⚠️ 推測｜❌ 未驗證。

### A. Mac 實測現況（使用者 11/22 貼的終端機輸出）

| 項目 | 結果 | 證據 |
|---|---|---|
| Lumi 三個排程（TV／KBar／Option-Archiver） | ✅ 已載入、結束碼 0、持續運行 | `launchctl list`；`tv_auto_sync.log` 11/22 14:50 仍每 15 分鐘執行 |
| **TV 更新真實寫入** | ✅ **11/19、11/20 連續兩天成功**（各約 5.5 分鐘）：「TV 已更新（日盤盤後）…指標面板、6 個快訊、版面都已儲存」；之後各輪皆「點位跟上次成功寫入的相同，跳過」 | `tv_auto_sync.log` 第 2772～2775、3056～3059 行 |
| KBar、Option-Archiver | ✅ 11/22 09:30 日誌有更新；`option_data` 11/21 09:30／19:30 有寫入 | `ls -lt` |
| 11/16 富邦並行測試（報價服務、OP666 錄製） | ❌ **沒有做過**：`~/AI/txo-klines-runner/logs/` 只有 11/11 的 `screener_cache.log`；沒有 `~/AI/op666_record_mac` | `ls` 結果 |
| Lumi 專案 git | ⚠️ 落後 origin/main 160 個 commit；`tv_apply_daily_params.py` 有未 commit 的本機修改（Meta+A／Meta+s，2 行）；未追蹤 `log/`、`tv_sync_state.json.bak_0743` | `git status`、`git diff --stat` |
| Mac Python | ✅ 3.9.6（Dell 為 3.13；私有新模組能否在 3.9 跑 ❌ 未驗證） | `python3 --version` |

**Lumi 風險：** 修正分支 `fix/tv-cross-platform-keys` **仍未 push**（只在 Dell 本機 69c2185 與 bundle 備份）。Mac 上的快捷鍵修改只是本機未 commit，**在分支 push 前，Mac 的 `tv_apply_daily_params.py` 不可 `git checkout`／覆蓋**；Mac 要 `git pull` 前先備份該檔。（Lumi 視窗 11/22 回報，使用者尚未決定是否 push。）

### B. 11/9 規劃之後新增、超出規劃的項目（Dell 排程清查 11/22）

| 項目 | 事實 | 搬遷影響 |
|---|---|---|
| `TXO-Desk-monitor2`／`patrol2`（T2 買方帳戶，11/20 上線） | Dell 常駐，用 `claude -p` | 需 Mac 登入 Claude；T2 帳本在 txo-private\desk |
| `TXO-Desk-w0`（溫哥 BP，`--dry`） | 同上；讀 `txo-private\desk\grape\kbars_1m.csv`（只讀） | 依賴 Grape 記錄器 |
| `TXO-Grape-Recorder` | 常駐，`txo-private\desk\grape\grape_recorder.py serve` | 前瞻記錄器，資料不可重建 ⚠️ |
| `OP666-OwnFlow-Live` | 常駐，8792 網頁，只讀 `op666_record` | 隨 OP666 錄製搬遷 |
| `TXO-Tailnet-Gate` | 已在 Dell 運行；綁 Tailscale 位址，轉發 8001／8770／8792，入口頁 8800 | Mac 要自裝 Tailscale、重跑一份；手機書籤位址會變；**使用者尚未決定的「手機遠端觀看」已事實上用 Tailscale 實作** |
| `Haiqi-TV-Auto-Sync`（海期 GEX 指標，每天 21:00） | Dell 啟用中；**11/20 22:39 結果碼 1（失敗）**；屬「TradingView 指標」資料夾專案，非 Lumi | 另算一項搬遷；失敗原因未查，建議交給該專案視窗 |
| `TXO-Probe-Publish-Day/Night` | 仍 Ready、持續執行（最近 11/21） | 量測早該結束，刪除待使用者同意 |
| `TXO-Staff-bot` | 工作排程顯示 Ready，但 `staff_bot.py` 程序 11/21 10:18 起在執行（外層殼已結束屬正常）；最後日誌 11/21 21:09 為 Telegram 連線被重設 | 是否能正常回覆 ❌ 未驗證（Telegram 傳一句話可測） |

### C. 程式與資料位置（搬遷前提）

| 項目 | 事實 | 影響 |
|---|---|---|
| **實際常駐的交易室程式不在乾淨的 git** | 跑在 OneDrive 內的 `.claude\worktrees\option-quote-recorder\trading room\desk`（含其他視窗未 commit 的檔案）；開發版 `C:\Users\mingi\txo-wt-desk-friction`（分支 `desk-friction-guard`）**領先 origin/main 88 個 commit，全部沒 push** | Mac 從 GitHub clone 拿不到；要用 git bundle 或複製資料夾另搬，且不能進公開 repo |
| `txo-private` 容量 | **14.4 GB／10,960 檔**（op666_record 8.0 GB、option_quotes 2.4 GB、op666 2.3 GB、desk 1.8 GB）；原規劃寫 5.5 GB | 11/10 複製到 OneDrive 的 `txo-private-mac-copy`（1.58 GB，不含 op666_record／option_quotes）已過期；desk 帳本與記憶要在切換當下才複製 |
| Claude 登入 | 幕僚鳥橋接、patrol、研究員、Telegram 聊天都靠 `claude -p`；11/12 發生過登入過期 | Mac 需獨立登入；同一 Telegram bot 不可兩邊同時跑 |
| 社群自動發文（11/12 起） | `post_social_cards.py`、`make_reel.py`（edge-tts）等，預設乾跑、尚未排程；Meta 憑證尚未申請 | 目前不影響搬遷；日後上線前先決定在哪台跑 |

### D. 修正後的階段判斷

```
階段 0 Lumi 本機排程      ✅ 完成且穩定（TV 兩天真寫入成功）
階段 2 Static-Front       ✅ Mac 試跑通過（未啟用）
階段 2 Screener-Cache     ✅ Mac 乾跑通過（未啟用，11/11）
階段 2 Intel／Staff-bot   ❌ 未開始
階段 3 富邦服務切換       ❌ 未開始（11/14～15 目標已過；並行測試沒做）
新增項目（B、C）          ❌ 未規劃
```

### E. 待使用者決定／動手

1. 是否 push `fix/tv-cross-platform-keys`（Mac 是否能安全 pull 取決於此；push 前一律先問）。
2. 交易室程式怎麼搬：git bundle 還是複製資料夾（88 個 commit 目前只在本機）。
3. 何時做富邦並行試跑（Mac 要先建 `.env`、手動複製 `op666_recorder.py`，皆由使用者自己做）。
4. `Haiqi-TV-Auto-Sync` 失敗原因與是否搬 Mac（交給 TradingView 指標視窗）。
5. 刪除 `TXO-Probe-Publish-Day/Night`；OneDrive 回收桶永久刪除 `fubon_cert_tmp`、`.pfx`；搬遷結束後刪除 `txo-private-mac-copy`。

## 6-I. 2026-11-22 下午 Mac 富邦並行啟動（階段 3 前置，Dell 完全未動）

| 時間 | 事項 | 結果 | 證據 |
|---|---|---|---|
| 15:11 | Mac 環境檢查 | ✅ `~/AI/fubon-test/bin/python` 有 `fubon_neo`（系統 python3 沒有，之後一律指定此環境）；Claude 已登入；Tailscale 未安裝 | 終端機輸出 |
| 15:20 | 建 Mac 專用 `~/AI/txo-mac.env`（從 OneDrive 專案 `.env` 複製，只改 `FUBON_CERT_PATH` 為 Mac 路徑，chmod 600） | ✅ 長度 64/10/45/10/4，憑證檔存在。**坑：Dell 的 .env 是 CRLF，金鑰尾端多 `\r`，要 `tr -d '\r'`**（否則 source 時出現 `command not found: ^M`、長度多 1） | 終端機輸出 |
| 15:25 | OP666 `--probe` | ✅ 登入成功、3232 筆選擇權代碼、選 80 檔 | 終端機輸出 |
| 15:29 | OP666 `--seconds 40` 真訂閱 | ✅ 寫入 151 筆：authenticated 1、heartbeat 2、pong 2、snapshot 64、subscribed 82（休市，無成交屬正常） | `20261122_night.jsonl` |
| 15:35 | 載入 `com.txo.op666-recorder-mac`（LaunchAgent，寫 `~/AI/op666_record_mac`） | ✅ 程序 87043 狀態 0，檔案持續成長 | `launchctl list`、`ls -l` |
| 15:37 | 載入 `com.txo.live-price-mac`（Mac 報價服務，`~/AI/txo-klines-runner`） | ✅ 程序 87078；books 訂閱確認；`/api/live_tick` = FUBON 33919，與 Dell 同值 | 終端機輸出 |
| 15:39 | Dell 檢查（Mac 登入後） | ✅ Dell OP666 程序 28888、報價服務 24888 仍在；Dell 報價 FUBON 33919；`_out.txt` 無斷線；報價日誌最近的 SSLError 都在 Mac 啟動前（已知的 Wi-Fi 問題）。⚠️ 休市無資料可證明 Dell 沒被擠掉，**明天開盤兩邊檔案都要成長才算數** | Dell 查詢 |

**檔案位置（Mac）：** `~/AI/op666/`（錄製腳本與 `run_op666_recorder.sh`）、`~/AI/txo-klines-runner/scripts/run_live_server_task.sh`、啟動設定 `docs/mac_migration/com.txo.*.plist.template`（`__HOME__` 以 sed 置換）。
**退回：** `launchctl bootout gui/$(id -u)/com.txo.op666-recorder-mac`、`…/com.txo.live-price-mac`。Dell 不受影響。
**尚未做：** Tailscale 安裝；交易室程式打包；明天 08:45 開盤對照（T8）；OP666 Mac 版少了「檔案停止成長自動重啟」看門狗，正式切換前要補。
**錄製資料夾 ≠ Dell：** Mac 寫 `~/AI/op666_record_mac`，不可與 Dell 的 `txo-private\op666_record` 混用。

## 6-J. 2026-11-22 傍晚 Mac 並行擴充（Dell 完全未動）

| 時間 | 事項 | 結果 | 證據 |
|---|---|---|---|
| 16:40 | Mac 電源／登入設定檢查 | ✅ sleep 0、displaysleep 0、autorestart 1、womp 1、FileVault Off、自動登入 alex | `pmset -g`、`fdesetup status` |
| 16:42 | **重開機測試** | ✅ 重開後 OP666（PID 793）、報價服務（807）自動恢復，`curl live_tick`＝FUBON 33919.0，Tailscale 三台在線 | 終端機輸出 |
| 16:48 | 選擇權報價鏈 `com.txo.optrec-mac` 常駐安裝 | ✅ 每 30 秒一筆、status 全 ok、約 1200～1600 筆報價／次。坑：`~/AI/optrec/option_quote_recorder.py` 要自己從 OneDrive 工作區 `tools/` 複製過去，否則 launchd 一直報 No such file | health_20261122.csv |
| 傍晚 | 動能鳥錄製調查 | ✅ 它是報價服務內的背景執行緒（`jj_lines.py`），開盤第一筆委託簿進來才自動載入，**不用手動啟動**；Mac 沒有私有模組，所以 Mac 不會錄。週末 Dell 日誌每分鐘約 2000 筆「Connection is already closed」是 11/21 16:35 起的舊問題，非 Mac 造成 | 程式碼、日誌 |
| 17:02 | 看門狗 `mac_watchdog.sh` v3 ＋ `com.txo.watchdog-mac.plist.template` | ✅ DRYRUN 測試通過（A 印兩行、B 不印）。**重要發現（已查證）：OP666 錄製器每 200 行才 flush（op666_recorder.py 第 226～228 行），休市時每分鐘僅 4 筆心跳，檔案約每 12～13 分鐘才更新一次**，所以「檔案修改時間／最後一筆時間」在休市時會誤判卡住；先前兩版看門狗因此誤報，且誤重啟會丟掉未寫入的暫存資料。v3 改為：OP666 只在交易時段（週一～五 08:50～13:45、15:05 起、週二～六 00:00～05:00）檢查、門檻 600 秒、重啟間隔加倍至 30 分鐘；選擇權報價鏈讀 CSV 最後一行時間（300 秒）；連續 3 筆 status 非 ok 則自動暫停 30 分鐘。Dell 的 OP666 同樣有此 flush 行為（先前以為是 Windows 讀取延遲，是錯的） | 終端機輸出、程式碼 |

**新發現：** Mac 上已有 `com.txo.static-front`（8001 靜態前端？），來源不明，待查。Tailnet 入口目前仍在 Dell，Dell 關機前要在 Mac 另做入口並改轉發目標（見對話結論）。
**動能鳥歷史錄製是長期的**（為了累積委託簿歷史，TV 拿不到），不是短期錄製。切換時 Mac 需複製私有 `jj_lines.py`，且同一時間只能一台錄。