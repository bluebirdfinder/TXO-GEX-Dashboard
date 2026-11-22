# 2026-11-09 今晚搬遷手冊（拳擊課後）

> 只新增、未 commit、未 push。不含任何金鑰。上位文件：[MIGRATION_STATUS_20261104.md](MIGRATION_STATUS_20261104.md)。
> 標示：✅ 今天實測讀到 ／ ⚠️ 我推測 ／ ❌ 沒查證

## 0. 今晚範圍（建議，使用者可改）

今晚是**交易日夜盤**（週一 15:00 起到週二 05:00），富邦報價、OP666 錄製、幕僚鳥等常駐服務整夜在跑。

| 類別 | 今晚動不動 | 理由 |
|---|---|---|
| TXO 富邦服務（Live-Price-Server、Fubon-Futures-Klines、OP666_Recorder、TXO-Desk-*、Intel-*、Staff-bot、Static-Front） | **不動** | 夜盤中、富邦 SDK 在 Mac 未實測；斷線會漏資料且補不回來 |
| Lumi 本機 3 個排程（TV-Auto-Sync、KBar-Collector、Option-Archiver） | **可搬** | 只用公開資料與 TradingView，不碰富邦（今天讀到） |
| 線上排程（GitHub Actions、Cloudflare Worker） | **不用搬** | 本來就在雲端，與哪台電腦無關 |

## 1. 全部排程清單（✅ 11/09 19:36 讀自 Windows 工作排程、GitHub、Claude 排程）

### 1-A 線上（搬遷後不變，只需確認沒被動到）

| 排程 | 時間（台灣） | 備註 |
|---|---|---|
| TXO `auto_update.yml` | 05:03／05:33／06:03、15:03／15:33／16:03、21:03／21:33／22:03 | ubuntu；另有 Cloudflare Worker cron `3,33 * * * *` 準時觸發 |
| Lumi `daily_run.yml` | main 仍 8 條 cron（15:18／15:48／16:18／16:48、05:18／05:48／06:18／06:48 UTC 換算後）；PR #2 減量尚未合併 | windows-latest；Worker 準時觸發 |
| Lumi `tv_daily_param_sync.yml` | **無排程**，只能手動；檔頭寫「擱置中，正式使用本機排程」 | 雲端版寫入從未測過，**不要當備援** |
| 私有倉庫 `TXO-GEX-Dashboard-private` | Actions 已關 | 不要打開 |

### 1-B 本機（Windows 工作排程）

| 排程 | 觸發 | 今晚 | 搬 Mac？ |
|---|---|---|---|
| **Lumi-TV-Auto-Sync** | 每 15 分＋登入 | **搬** | 可，見第 2 節 |
| Lumi-KBar-Collector | 每日 09:30 | 搬 | 可；今天 09:30 結果碼 1（SSL EOF 連線錯誤，期交所），原因未查 |
| Lumi-Option-Archiver | 每日 09:30、19:30 | 搬（見 2-C 的資料問題） | 可 |
| TXO-Live-Price-Server、TXO-Static-Front-8001 | 登入 | 不動 | 富邦 SDK 未測 |
| TXO-Fubon-Futures-Klines | 05:30／14:00 | 不動 | 富邦 SDK 未測 |
| OP666_Recorder | 登入 | 不動 | 富邦 SDK 未測 |
| TXO-Desk-bridge／monitor／patrol／recorder／server | 登入 | 不動 | 路徑寫死 `C:\Users\mingi`，⚠️ 需先改 |
| TXO-Intel-bot／daily／extract／jobs、TXO-Staff-bot | 登入／每 2 分／每日 08:30 | 不動 | 同上；`TXO-Intel-jobs` 最後結果碼 2147946720，原因未查 |
| TXO-Screener-Cache | 平日 16:30 | 不動 | 依賴私有資料夾 `txo-private` |
| TXO-Probe-Publish-Day／Night | 週一～五 13:30／04:30 | 不動 | **量測用，早該刪**；Night 最後結果碼 3221225786（被中斷）。刪除要使用者同意 |
| LuYangyang* 14 個 | 已停用 | — | 洋洋已在 Mac；Dell 備援期原定約 11/5 結束，清理由使用者決定 |

### 1-C Claude 排程（`~/.claude/scheduled-tasks`）

只有 2 個啟用：`op666-daily-report-reminder-weekdays`（週一～五 16:30 提醒貼台新日報）、`yangyang-interests-monthly-refresh`（每月 1 日）。其餘都是已過期的一次性任務。**這類排程只在 Claude App 開著時跑，搬 Mac 不會自動跟過去。**

## 2. TV GEX 指標每日更新（使用者最在意）

### 2-A 現況（✅ 讀自 `tv_auto_sync.py`、`tv_apply_daily_params.py`、log）

```
每 15 分 Lumi-TV-Auto-Sync 叫醒 tv_auto_sync.py
  ├─ 判斷視窗：日盤盤後 週一~五 15:30~23:59 ／ 夜盤晨報 週二~六 05:30~15:30
  ├─ 讀 GitHub 上 sent_state.json：今天 TG 快訊真的發了才繼續
  ├─ 讀 GitHub Pages 的 gex_data.json 算 6 個點位（缺欄位就攔截，不用預設值）
  ├─ 與 tv_sync_state.json 比對，沒變就跳過
  └─ tv_apply_daily_params.py --apply：Playwright 開「有畫面」的 Chromium（headless=False），
     用 tv_session.json 登入 TradingView，改指標面板＋6 個快訊，成功/失敗都發 Telegram
```

今天 18:07～19:33 的 log 每 15 分一行「無需動作」（亂碼，語意為推測），代表今天日盤盤後那一輪已經寫完。**所以下一次真正會寫入的是明天早上 05:30 以後**（夜盤晨報，Lumi TG 約 05:18～06:48 發出）。

### 2-B 搬到 Mac 的依賴清單

| 依賴 | 在哪 | 怎麼帶到 Mac |
|---|---|---|
| 程式（`tv_auto_sync.py`、`tv_apply_daily_params.py` 等） | Lumi repo `origin/main` | **clone GitHub，不要用 OneDrive 裡落後 357 個 commit 的本機副本** |
| `tv_session.json`（TradingView 登入憑證，已被 `.gitignore`） | Lumi 資料夾，**目前在 OneDrive 內** | 用 OneDrive 或隨身碟複製；**絕不進 git、不貼對話**。⚠️ 它放在雲端同步資料夾本身就有風險 |
| 環境變數 `LUMI_TELEGRAM_BOT_TOKEN`、`LUMI_TELEGRAM_GROUPCHAT_ID` | Windows 使用者環境變數 | **使用者自己在 Mac 設定，我不碰** |
| `TV_CHART_URL`（可選，預設有值） | 環境變數 | 通常不用設 |
| Python＋`requests`、`playwright`＋`playwright install chromium` | — | Mac 上 uv 的 Python 3.13 虛擬環境 |
| 需要有畫面的登入桌面 | — | 腳本 `headless=False`。Mac 已設自動登入（洋洋紀錄）；⚠️ 螢幕鎖定或無人登入時 Chromium 可能開不起來，❌ 未測 |
| 排程 | Windows 工作排程每 15 分 | Mac 用 launchd（洋洋已有 `docs/mac/make_plists.py` 可參考） |
| 暫停開關 | `tv_sync_pause.txt` 存在就跳過 | ✅ 目前 Dell 上沒有這個檔 |

### 2-C 其他兩支（KBar／Option）的資料問題

- `kbar_data/TX_1m.csv`（3.2 MB）、`option_data/`（55 MB）都被 `.gitignore`，是**累積型資料**，不在 GitHub。
- 若 Mac 從零開始累積，歷史會斷；兩邊同時累積則各存一份、不會互相覆蓋但會分岔。
- 建議：Mac 先用 OneDrive／隨身碟複製這兩個資料夾過去，**再**切換排程，且切換後 Dell 的兩個排程要停用，避免兩邊各自累積。
- 期交所只保留最近 30 個交易日逐筆，所以停機太久會補不回來。

## 3. 今晚時間線（建議）

```
[現在～搬前] 準備（Windows，我可先做）
  ① 確認 Dell 現況快照：tv_sync_state.json 內容、今天 TG 已發、log 正常
  ② 備份 Lumi 的 tv_session.json 與 tv_sync_state.json 到 D:\TXO-backup\（不加密，注意保管）

[拳擊後 ～ 約 23:00] Mac 準備（使用者操作，我一步步帶）
  ③ Mac clone Lumi 的 origin/main 到「英文路徑」（例如 ~/AI/Lumi-Chip-Bot）
  ④ 複製 tv_session.json、kbar_data/、option_data/ 進去
  ⑤ 建 uv 虛擬環境，裝 requests、playwright，playwright install chromium
  ⑥ 使用者自己設定兩個環境變數
  ⑦ 乾跑：python tv_auto_sync.py --dry-check（可加 --now "YYYY-MM-DD HH:MM" 假裝時間、
     --emit-params PATH 只算參數不碰 TV）；tv_apply_daily_params.py 才有 --dry-run／--apply／--yes。
     （Lumi 視窗 11/09 回覆；乾跑通過不代表真寫入會過）

[切換前最後一道檢查]
  ⑧ Dell 上先建立 tv_sync_pause.txt（暫停 Dell 版），再啟用 Mac 版 launchd
  ⑨ 絕對不要兩邊同時開著（會雙寫 TradingView 快訊、重複發 TG）

[明早 05:30 之後] 驗證
  ⑩ 看 Mac 版 log、TradingView 指標面板 6 個點位、Telegram 通知；與 TG 晨報數字比對
  ⑪ 任何一項不對 → 立刻退回（第 4 節）
```

## 4. 退回方式（最壞情況也只是回到今天）

| 狀況 | 做法 |
|---|---|
| Mac 版沒寫入／寫錯 | Mac：`launchctl bootout` 關掉該排程；Dell：刪除 `tv_sync_pause.txt`，下一個 15 分鐘整點即恢復。Dell 的 `tv_session.json` 與 `tv_sync_state.json` 沒動 |
| 快訊被重複寫 | 到 TradingView 快訊列表手動確認 6 個快訊；點位以 TG 晨報為準 |
| TradingView 登入失效 | 在原本登入過的那台執行 `tv_login_helper.py` 重新授權（本人在瀏覽器完成） |

## 5. 風險與我不確定的事

| 風險 | 等級 | 備註 |
|---|---|---|
| Mac 有畫面的 Chromium 在無人值守時能否開啟 | 中 | ❌ 未測，搬前一定要手動跑一次 |
| `tv_session.json` 在 Mac 被 TradingView 判為新裝置而失效 | 中 | ⚠️ 推測；失效就要本人重新登入 |
| 8 GB 記憶體（洋洋＋Chromium 同時） | 低～中 | Chromium 約數百 MB；洋洋的 13 個排程已在跑 |
| Lumi 本機 `main` 落後 357 個 commit | 低 | 因為 Mac 直接 clone，不受影響 |
| Lumi `cloudflare_worker_lumi_fusion.js` 未 commit 修改 | 與今晚無關 | 仍待使用者到 Cloudflare Dashboard 確認部署版本 |

## 5-B Lumi 視窗 11/09 補充（對方讀 origin/main 程式回覆，我未自行驗證）

| # | 要注意 | 做法 |
|---|---|---|
| 1 | 兩支寫 TV 的腳本寫死 `headless=False`（`tv_apply_daily_params.py` 約第 390 行、`tv_login_helper.py` 第 76/83 行），註解說穩定前不要改 | Mac 要用 **LaunchAgent**（使用者登入的圖形工作階段）；LaunchDaemon、螢幕鎖定、沒人登入都會開不了瀏覽器 → Mac 要**關螢幕鎖定、保持自動登入** |
| 2 | `tv_login_helper.py` 用 `channel="chrome"` | Mac 裝 **Google Chrome**，並先 `playwright install chromium` |
| 3 | `tv_session.json` 在新裝置／新 IP 可能被 TradingView 判失效 | 預留重新登入時間（本人在瀏覽器完成）；乾跑通過不代表真寫入能過 |
| 4 | `tv_auto_sync.py` 用 `git show origin/main:sent_state.json` | Mac 的 clone 必須能 `git fetch`（有 GitHub 權限），否則讀不到當天最新狀態 |
| 5 | `tv_sync_state.json` 是本機狀態檔（不進 git） | 要不要複製由使用者決定：不複製＝Mac 第一次會重寫一次同樣點位，通常無害（⚠️ 我推測） |
| 6 | 兩台不能同時啟用 | Dell 先建 `tv_sync_pause.txt` 再啟用 Mac |
| 7 | `register_option_archiver_task.ps1` 是 Windows 專用 | Mac 改寫 launchd；09:30／19:30 觸發用 Mac 本機時區，**Mac 時區要是 Asia/Taipei**（洋洋紀錄顯示已設） |
| 8 | `taifex_kbars.py` 來源只留約 30 個交易日；不可兩台同時累積同一份 `TX_1m.csv` | Mac 錯過的天數補不回；切換後 Dell 的 KBar／Option 排程要停 |
| 9 | Lumi 視窗承諾：今晚到明早**不改** `tv_*.py`、`sent_state` 流程；Dell 上相關 5 支腳本與 `origin/main` 相同 | Mac 直接 clone `origin/main` 即可 |

## 6. 搬後待做（不在今晚）

- TXO 富邦服務：先做 Mac 富邦 SDK 實測。
- 寫死路徑 `C:\Users\mingi` 改變數、8 個 skill 路徑。
- 刪除 `TXO-Probe-Publish-Day／Night`（量測完畢）。
- `~/.claude` 的 `CLAUDE.md`、`settings.json` 同步（使用者尚未決定）。
- Lumi PR #2 合併與用量驗證；2026-12-30 GitHub 金鑰到期（12/16 日曆提醒）。
