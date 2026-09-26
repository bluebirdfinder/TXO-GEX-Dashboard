# HANDOFF.md — TXO-GEX-Dashboard 交接單（唯一真相來源）

> 每次交接前更新並 commit。新視窗只需讀：`CLAUDE.md`（含「多視窗守則」）、本檔、`AGENTS.md`。
> HISTORY.md 很長，**只讀最新兩個條目**（用 grep／指定行數），不要整份讀入。
> 最後更新：2026-09-26，origin/main 約在 `bc33f43`（開工前務必 `git fetch origin` 確認）。

## 0. 開工前檢查（每次）
1. `git fetch origin`，看落後多少；main 會被 GitHub Actions 每天自動推資料 commit。
2. `git status`：看有沒有別人的未 commit 檔案（見第 2 節）。
3. 用 `list_sessions` 確認有沒有其他視窗指向同一資料夾且正在執行。
4. 改檔／commit／push 一律照 `.claude/skills/multi-session-safety/SKILL.md` 用暫時 worktree；**push 前先問使用者**。
5. **本檔裡的「已驗證／已完成」是前一個視窗的自述，動工前請抽樣重跑確認，不要直接採信。**

## 1. 待辦

> **2026-09-26 進度（接手視窗）**：以下項目已合併並隨 **v64.5** 發布（分支 `claude/release-v64.5` 推上 main）；詳見 HISTORY.md v64.5。
> | 項目 | 狀態 | 分支 |
> |---|---|---|
> | 1 修 `bump_version.py` ＋ 2 稽核 SOP | ✅ 完成（release skill 已補「寫出檔案 vs CI git add」步驟，腳本自動警告） | `claude/fix-bump-version` |
> | 3 弱火箭／一般藍鳥 | ✅ 後端＋**前端接線**＋快取重生；獨立 `ta` 比對 1,345 檔 0 不一致。已隨 v64.5 發版 | `claude/screener-weak-rocket` |
> | 4 「1,400+」→「1,380+」 | ✅ | 同上 |
> | 5 fetch 失敗旗標＋重試 | ✅（失敗回 None、退避重試、仍失敗中止建置） | 同上 |
> | 額外發現 | 選股腳本曾把過期 17 天的 `tw_quotes_latest.json` 當「最新 K 棒」附加 → 已修（僅在報價日期較新時附加）；舊快取所有訊號受污染 | 同上 |
> | 法人 T-1~T-4 回補 | ✅ 新腳本 `scripts/backfill_institutional_snapshots.py`；補 9/18、9/21、9/22、9/23 日夜盤（欄位對映用 9/17 日盤與 9/16/9/17/9/24 夜盤重抓比對，逐欄一致）。9/25 中秋休市無資料 | `claude/backfill-institutional` |
> | 額外發現 | `data/tw_holidays.json` 2026 年與證交所官方不符（漏 9/25 中秋、春節 2/12–2/20、4/6、10/26、12/25，誤列 1/26–1/30、10/01），已按官方修正；2025、2027 尚未對照官方 | 同上 |
> | 仍待辦 | SSL 全域 `CERT_NONE`（項 6）、CL/US10Y/DXY 輪詢、`futDailyMarketReport` 編碼、worktree 殘留清理、融資餘額速度指標觀察 | — |

### 第一批：不需要使用者在場（可先做）
| # | 項目 | 現況 | 備註 |
|---|---|---|---|
| 1 | 修 `scripts/bump_version.py` | ①不會插入新版本內容區塊（`release_note` 參數收了沒用）②全域字串置換會把舊條目「(v64.3)」標籤也改成新版 ③進度計數 [1/5]…[5/7] 不一致 | 舊視窗「9/26 交接續作」已開始處理，先確認它做到哪 |
| 2 | 稽核 SOP 補一步 | 核對「腳本實際寫出的檔案」與「CI `.github/workflows/auto_update.yml` 的 `git add` 清單」是否一致 | v64.4 就是漏了這一步 |
| 3 | 弱火箭✈️／一般藍鳥🐣（選股雷達） | `compute_jj_rocket_and_bird()` 回傳 4 值，程式完成、離線驗證（自述：1,336 檔回放 40,918 次、強弱互斥 0 違規）；**✅ 已重生快取並隨 v64.5 發版（見上方進度表）** | 共用資料夾內舊視窗的同名未 commit 檔已被取代 |
| 4 | 選股畫面「1,400+ 檔」改實際數字 | 實際可掃描 1,383 檔股票/ETF（`trading room/room.html:793`、`room.js:216,3403`） | 只是文字，UI 未改 |
| 5 | `fetch_twse_all_stocks_day()` 失敗旗標與重試 | 失敗只印 WARN 回 `{}`，與休市日無法區分，會讓全市場少一天 K 棒卻無聲（`build_screener_cache.py`） | 只是建議，未動 |
| 6 | `build_screener_cache.py:56-58` SSL 驗證 | 全域 `CERT_NONE`；建議改預設驗證＋certifi，TWSE/TPEx 憑證鏈驗證失敗才對這兩網域降級並註明原因 | 已評估、未改 |
| 7 | 融資餘額變化速度指標 | v64.4 上線，需連續 2 天以上真實資料才有數字，幾天後看 T0 欄位小字確認開始出數字 | 只需觀察 |
| 8 | 低優先雜項 | 戰情室 CL/US10Y/DXY 即時輪詢（目前只是靜態提示）；`futDailyMarketReport` 中文標籤編碼全面搜尋；`data-pipeline-integrity` skill 正式測試；殘留 worktree 清理（`.git/worktrees/` 有殘留登記 `txo-docsync`、`main-merge-wt`、`txo-guard`；`.claude/worktrees/` 4 個舊資料夾） | |

### 第二批：需要使用者在場或決定（等使用者說要做再做）
| # | 項目 | 現況 | 需要使用者 |
|---|---|---|---|
| 9 | **CVD 真實化** | 程式碼完成、離線驗證通過（自述）。K 棒版，支援 1M/3M/5M/15M/30M/1H/4H；1D/1W/1月不支援；只有 TXF/MXF/MTX/TMF 有真實 tick、無法回補歷史。**全部未 commit** | 使用者夜盤（15:00~05:00）在場：跑 `scripts/live_price_server.py`、戰情室切 CVD 分頁核對真實 tick；通過後才 commit，再用 `bump_version.py` 發版（`room.html`/`room.js` 版本字串仍是 v64.3） |
| 10 | JJ鬼爪V4.1 對照 TradingView | 卡片標題仍標「⚠️未對照 TradingView 驗證」；Chrome 擴充功能讀不到 canvas 圖表，無法自動比對 | 使用者在場逐根 K 棒核對，通過後拿掉 `room.html` 內警告字樣 |
| 11 | Smart Money Concept 移植 | 未開始；源碼在使用者私有資料夾 `TradingView 指標\合併好用公開指標\Merged_Indicators.md`；部署架構比照 JJ鬼爪，合併進同一份 Cloudflare `worker.js`（`indicator=` 路由） | 使用者在場 |
| 12 | 三大法人 5 日矩陣 T-1~T-4 歷史缺口 | 期貨未平倉／選擇權大額／現貨買賣超／夜盤法人，存在 `institutional_snapshots.json`，回補腳本不補，CI 修好後只往後累積 | 使用者決定補不補（需逐日查官方資料，工程量中等） |
| 13 | 選股雷達剩餘近似訊號 | 🛸動能飛碟、⚡動能閃電、✈️噴射機、🥚帶殼鳥、`k5_state`、`demark_state` 仍是簡化近似 | 先問使用者有沒有對應 Pine 源碼 |
| 14 | 使用者的 TradingView 分頁 | 卡在「離開此網站？」原生對話框，AI 關不掉 | 使用者手動關 |

## 2. 共用資料夾內「別人未 commit 的檔案」（不要 stash／覆蓋／刪除／順手 commit）

> ⚠️ v64.5 推上 main 後，共用資料夾內舊視窗的 `scripts/build_screener_cache.py` 未 commit 版本已被 main 上更完整的版本取代（含失敗重試、過期報價修正）；`trading room/room.js` 的 CVD 修改與 main 上同檔（弱火箭接線、版本字串）將在未來 `git pull`/merge 時出現衝突，須由使用者決定處理方式，AI 不要自行覆蓋。
| 檔案 | 主人／性質 |
|---|---|
| `scripts/fubon_api_provider.py`、`scripts/live_price_server.py`、`trading room/room.js` | 舊視窗「TXO-GEX-Dashboard 交接續作」的 CVD 真實化。`room.js` 的 diff 比它當初記錄多 6 行，發版前先看實際 diff |
| `scripts/build_screener_cache.py` | 同一舊視窗的弱火箭／一般藍鳥 |
| `SELF_AUDIT_FINDINGS_TODO.md` | 同一舊視窗（CVD／弱火箭狀態標記） |
| `trading room/room.html` | 版本字串（v64.3→v64.4）遺留變更，發版流程產物，不要手動 commit |
| `data/stock_futures_large_trader_cache.json`、`data/twse_t86_cache.json` | pipeline 本機快取，不在 CI `git add` 清單，**不該 commit** |

## 3. 風險與已知坑
- 多個 Claude 視窗共用同一實體資料夾（非 worktree 隔離），曾出現不明作者 commit；已查清 `170105f`／`344d038` 是「期交所網頁整合至 GEX」視窗做的 v64.4，且已在 main。
- 曾差點用 `git merge --ff-only` 蓋掉 main 上 46 次自動排程 commit；main 會被 GitHub Actions 每天推進，合併前必須 `git fetch`。
- 停止／封存舊視窗不會刪掉它已寫在資料夾裡的檔案，但會失去它的對話脈絡；離線的 Remote Control／雲端視窗無法喚醒或關閉。
- 上一批 `PROJECT_HANDOVER.md` 缺 v64.4 列已補；`bump_version.py` 修好前，每次發版都要人工檢查 PROJECT_HANDOVER／README／STATUS 的「最新內容」有沒有被誤標。
- Windows／OneDrive 刪 worktree 常報 Permission denied，資料夾刪掉但 `.git/worktrees/` 留登記，不影響運作。

## 4. 使用者偏好（摘要）
進度用表格；分岔點用 AskUserQuestion；技術概念先白話解釋再帶術語；重大修復後主動走發版流程（`release` skill）；push 一律先問；不要斷言正確性沒驗證過（用真實資料、獨立函式庫或手動追蹤比對）；核心風控見 `AGENTS.md`。
