# 三個聊天室統整交接（2026-10-08 22:10 製作）

> 給新視窗：先讀本檔，再讀 `HANDOFF.md`（第 0 節、L～R 列）、`CLAUDE.md`、`AGENTS.md`。**不要重新探索**；本檔列的事實都是 10/08 22:10 前後實際查過的。
> 這三個聊天室（使用者側欄標題）：
> 1. 「尋鳥戰情室使用者體驗測試」＝10/07 起的「扮演用戶測試戰情室」（本檔簡稱 **A**）
> 2. 「TXO-GEX-Dashboard ADX 縮放 10/7」（session `local_75c39bac…`，簡稱 **B**）
> 3. 「TXO-GEX-Dashboard 夜盤價格驗證」（session `local_eceaf9b9…`，10/06 的視窗，簡稱 **C**）
> 另外還有別的視窗在同一個資料夾：「戰情室優化＋個股期貨擴充」×2、「JJ 大戶散戶動能日盤比對」×3（有的標示 running）、「OP666簡報技術指標分析」（分支 `claude/op666-chip`）。**動檔案前先 `list_sessions` 看誰在跑，不要碰別人未 commit 的東西。**

---

## 0. 系統現況（22:10 實查）

- 夜盤進行中（15:00～05:00）。**10/09（週五）國慶補假休市，下個交易日 10/12（週一）**；週五選 F2 結算順延到 10/12（已修，`a202d01`）。
- 本機報價服務 `TXO-Live-Price-Server`：程序 PID 18604，**啟動於 10/08 09:12:49＝仍是舊版，沒有看門狗**（看門狗 `4f514c4` 在 09:17 才推上 main）。runner 副本（`C:\Users\mingi\txo-klines-runner`）啟動時會 `git pull`，所以「重啟」即可套用。
- 雲端引擎 `auto_update.yml`：22:03 有一輪 workflow_dispatch 在跑（in_progress），推送前必須先確認 `gh run list --workflow auto_update.yml --limit 1` 的 status 是 `completed`。
- 本機工作排程：`TXO-Fubon-Futures-Klines`（05:30／14:00）、`TXO-Probe-Publish-Day/Night`、`TXO-Screener-Cache`（平日 16:30，**只 commit 不推送**，10/08 已跑成功）、`TXO-Live-Price-Server`。
- runner 副本有一個**未推送**的資料 commit `37d6ebc`（選股快取／個股日 K／報價檔 10/08 16:50）。
- `klines_cache.json` 已用期交所官方逐筆檔回補（15 分線回溯到 9/2），18.7 MB，git 歷史會再肥。
- 共用資料夾目前分支 `claude/bold-galileo-dy1oxb`（落後 origin/main 很多），**不要在這個資料夾做 git 合併／重設**。

---

## A. 「尋鳥戰情室使用者體驗測試」

### 已完成（都已推上 main，細節見 `HISTORY.md` 最新條目與 `docs/ROOM_UX_WALKTHROUGH_2026-10-07.md`）
- 盤中像用戶實測戰情室，找出 15 項問題並全部修正：圖表即時推進（台指期 1～60 分）、持倉體檢先問部位、GEX 面板只在 TXF/MXF/MTX/TMF、個股報價取富邦即時／報價檔／日 K 最新並標日期、開高低、搜尋下拉不再被裁且現貨＋期貨並列、全域 Esc、可視範圍統一、副圖可拖曳、手機底部列、斷線紅帶、昨收標示、洗價三級（50/75/90%）。
- 新增 gateway 端點 `/api/stock_quote`、`/api/live_tick` 的 txf `open/high/low`（已於 10/07 21:58 重啟生效，後來又被 B 的 09:12 重啟覆蓋仍含這些）。
- `scripts/backfill_taifex_klines.py`：期交所官方逐筆檔合成日內 K，與富邦 OHLC 100% 一致，量 ÷2。已在 runner 副本回補並推送。
- 選股快取＋個股日 K 排程腳本 `scripts/run_screener_cache_task.ps1` ＋ 工作排程 `TXO-Screener-Cache`。報價檔也加進 `auto_update.yml`。

### 未完成
1. **JJ 大戶散戶動能取樣（最大的一項）**
   - 已取：台指期 1 分 5 筆（09:19～09:21）、聯電期 CCF-1 1 筆（309／241／28）；台積電期貨 CDF 0 筆。判讀見 `docs/JJ_SAMPLES_20261008.md`（**本檔已隨本交接一起推送**）。
   - 初步結論：JJ **不是單純五檔買賣口差**。台指期 JJ 值 -400～-529，但台指期五檔口差只有 ±6；聯電期五檔口差約 200～300，與 JJ 紅／綠量級相近。JJ 值一分鐘才更新一次（新分鐘後 40～50 秒才換）。圖例文字切商品後不重畫，**要看右側價格軸的彩色標籤**。
   - 本機逐筆成交疑似偏少（09:20 台指期一分鐘只有 232 口）→ 要重驗 `trades_15s` 日盤完整性（10/01 驗證的是口數總和對交易所 tradeVolume）。
   - **為什麼慢（已實測）**：JJ 分頁在 Chrome 裡 `visibilityState = hidden`，計時器被降速約 7 倍（3 秒內只跑 4 次、預期 30 次）。要取樣必須把那個 Chrome 視窗**放在最前面、不要縮小**。
   - **JJ 版面限制**：「儲存」只能蓋掉現有版面，不能另存。使用者有 3 個版面：常用版面（TX-1）、New（TX-1，2025-12 建）、加權指數；**使用者明說不要蓋掉（那是「Q 姐」的系統），他會問 Q 姐能否建新清單**。所以：**不要按儲存**。使用者建好新清單後會告訴你名稱，再載入它來取樣。
   - Chrome 擴充套件分頁 `1964926060` 還開著 JJ（聯電期 1 分，未存檔），可關掉。
   - 操作 JJ 頁面的注意事項在 `docs/JJ_RSTOCK_MOMENTUM_EXPLORATION.md`（origin/main 上；連線上限約 5 個分頁、新增指標很不穩、切商品後要點畫布再按左下角圖示）。新增「大戶散戶動能」子圖：技術指標 → 雙擊 `futures--revive-ti`（點一下常不生效，過幾分鐘才出現，別重複點以免出現多份）。
2. 副圖指標（MACD／CCI／ADX）不隨即時 K 棒更新；4H 以上週期不做即時推進；搜尋只並列有 K 線的期貨（目前只有台積電期貨 CDF）。
3. #11（加權／櫃買超過 2 分鐘沒更新就標「昨收／資料延遲」）還沒在真實交易日 9:00 前後各看一次——下一個交易日是 10/12。
4. `TXO-Screener-Cache` 要不要加 `-Push`（目前只 commit，線上版個股資料不會自動更新）。
5. 本機到富邦（api.fugle.tw）10/08 00:20 起有 SSL 錯誤與連線中斷，報價服務變慢；之後再發生要查網路。
6. 回報原則：使用者說「黃線正負號與五檔口差 3/3 相符」那個 10/07 夜盤判斷，10/08 日盤樣本不支持，**不要再用它當結論**。

---

## B. 「TXO-GEX-Dashboard ADX 縮放 10/7」

### 已完成（已推送，見 `HANDOFF.md` L～P 列與 `HISTORY.md`）
- ADX 附圖自動縮放（`11fac95`）、GEX 名稱標籤畫在 VRVP 左側（`42a55fd`）。
- 大戶散戶動能每分鐘存檔（`~\.txo_momentum_1m\`）＋`/api/momentum_history?tf=`；台指期與聯電期每 15 秒原始五檔＋成交寫 `raw_YYYYMMDD.jsonl`（還原 JJ 用，今天一直有在記，到 15:30 還有 CCF1!／TXF1! 各約 3,400 筆）。
- 個股期貨代碼改以期交所官方對照表為準（28 檔原本對錯）。
- 期交所公布時間探針（`probe_publish_times.py`）與排程；「舊快照冒充當日」修正；到期天數改小數天；休市日順延結算（週五選 10/09→10/12）；`data_completeness`＋網頁「資料尚未公布」提示；`klines_cache` 改 5 分鐘版本號快取。
- **看門狗**（`4f514c4`）：交易時段內 180 秒沒訊息就重連＋重新訂閱 futopt WebSocket，`/api/momentum` 回補。已推送到 main。

### 未完成
1. **重啟本機報價服務套用看門狗**（現行程序是 09:12 的舊版）。B 與使用者約好「13:45 收盤後」重啟，但目前沒重啟；現在是夜盤，**重啟會中斷即時報價／五檔／CVD 約 30～60 秒並重新登入富邦——先問使用者**。重啟方式：結束 `live_price_server.py` 的 python 程序，`TXO-Live-Price-Server` 排程 15 秒後自動拉最新 main 並重啟（PowerShell 殺程序這步在 auto mode 會被擋，需要使用者授權）。
2. B 提到「05:15 的排程任務還卡在授權（等使用者按允許）」——不確定是哪個任務，用 `mcp__scheduled-tasks__list_scheduled_tasks` 查。
3. 10/09 20:00 的探針彙整任務可能回報「資料不足」（10/07 日盤探針沒跑，原因疑似電池／休眠，已改允許電池；**沒有設定喚醒電腦**）。10/09 休市所以也量不到。
4. `HANDOFF.md` P 列自己寫的「其餘（副圖高度可調、手機版版面、資料真實性巡檢）尚未做」——副圖高度與手機版已由 A 完成；**資料真實性巡檢（逐欄追來源）沒做**。
5. 休市日順延結算只用 10/07 OI 驗證過，**歷史連假沒逐一回測**；10/12 開盤後要實測週五選 F2／週選分類是否正確。
6. VEX／GEX+ 符號：使用者決定先不改，若破解不了羊叔公式就用教科書版（`docs/VEX_SIGN_AND_FLIP_VALIDATION_20261007.md`）。

---

## C. 「TXO-GEX-Dashboard 夜盤價格驗證」（10/06）

### 已完成
- 夜盤台指期價格改用 MIS 即時價並驗證（本機 50142 vs 官方 50139～50142，`409bdb3`）。
- 戰情室：頂部不再被切、AI 快捷按鈕換行、OHLC 圖例預設顯示最新 K 棒、黃金 GC 分頁、依商品標真實來源（**富邦沒有海外期貨**，GC／CL／DXY／US10Y 用 Yahoo）、左欄當日開高低、微台 GEX bug、右側 Y 軸只顯示彩色數字標籤。
- GEX 主頁個股期貨表（漲跌幅／振幅／OI 增減／6 種排行，官方清單 320 檔）。
- **官方對帳稽核**：`scripts/audit_vs_official.py`（1,400+ 項 PASS）；清除虛構資料（Max Pain 隨現價變動、寫死週報、規則猜日期的 CPI／非農→改讀 `data/us_macro_calendar.json`、寫死板塊占比、融資維持率、假成交量、寫死 VIX 敘述）。
- GEX／VEX 波動率改用當日官方臺指 VIX；Zero Gamma 卡片改名「賣買權 OI 分界」並排「標準 Gamma Flip」；每輪寫 `data/gex_line_observations.json`。
- Lumi 交接資料夾 `露米籌碼監控機器人\from_txo_audit_20261006\`（含 `NEW_WINDOW_PROMPT.txt`）。

### 未完成（出自 C 的交接清單，B 之後也沒做完的部分）
1. 下一輪引擎成功後、收盤後跑 `python scripts/audit_vs_official.py --sample 0`，確認 FAIL=0；確認 `data/gex_line_observations.json` 已產生、網頁「標準 Gamma Flip」有數字。觀察記錄累積幾週後，加上 Lumi 的 `kbar_data/TX_1m.csv` 重做「跌破各條線之後」的檢驗。
2. 結論未定：Zero Gamma／VEX 早鳥線要不要改成單一條標準 Gamma Flip（使用者選「兩種並排、幫我觀察記錄」）。事實：VEX 早鳥線與 Zero Gamma 幾乎同一條（207/208 快照差 <0.15 點）；跌破後 60 分鐘再下殺 >100 點比例 12%＝基準 12%（34 次，樣本短且單邊上漲）。
3. 待使用者決定：找不到 Zero Gamma 轉折時引擎退回「現價−150／−100」的假數字；夜盤時段 `change_pct` 是夜盤期貨漲跌非現貨；ADP 日程沒有官方來源；2323 中環沒有行情。
4. **OP666 視窗協調（有衝突風險）**：分支 `claude/op666-chip`（worktree `C:\Users\mingi\AppData\Local\Temp\txo-wt-op666`，**ahead 13／behind 66，尚未推送**）改了 `trading room/room.js`（`computeStrongWeakLevels`／`renderStrongWeakLevels`，掛在 `renderMainOverlays` 開頭，`indicatorConfig.swLevels`）、`room.html`（指標庫多 `chk-sw`、載入 `room_panels.js`／`room_retail.js`），新增 `room_panels.js`、`room_retail.js`。A 這兩天也大改了 `room.js`（即時 K 棒、可視範圍、股票報價、洗價、分隔線…）和 `room.html`（`left-quote-asof`、手機底部列）。**它推送前必須先 merge origin/main，衝突要由它解**；你不要動它的 worktree／分支。要溝通用 `SendMessage` 對 `local_59efe38b-de74-46ba-bdf4-df1ef5416105`。
5. Lumi（露米籌碼監控機器人）的 `backtest_maxpain_topology.py` 繼承 Max Pain 舊錯誤，重跑結果在其交接資料夾；除非使用者要求，不改 Lumi 檔案。
6. 舊待辦：手機看富邦報價（Tailscale，等使用者在家）、CVD 買賣方向驗證（使用者用富邦 App 對照）、法規確認（富邦行情條款／期交所再散布／投顧法）、倉庫改私有、`.git` 肥大（已 645MB+，使用者不想改寫公開歷史）。

---

## 規則與教訓（每個視窗都要遵守）

- **`git push` 一律先用 AskUserQuestion 問**；核准是一批一批，不可沿用。推送前確認 `auto_update.yml` 最新一輪 `completed`。用暫時 worktree（`.claude/skills/multi-session-safety/SKILL.md`），**只 add 自己的檔案**，不用 `git add -A`。push 若回 500 是 GitHub 暫時故障，稍後重試即可；rebase 衝突時先看 `git status`，別硬推。
- **使用者看不到 .md 檔**：交付文件要同時給 HTML（用 `SendUserFile`）或直接把內容貼在對話裡；表格請用 code block 文字格式更保險。問使用者問題用 `AskUserQuestion` 選項卡片，且先把解釋講完再問；任何任務回報完成百分比；流程用 code block 畫圖。
- 紅線（`AGENTS.md`）：不偽造資料、不建議拆週選價差單、不建議追價；持倉診斷要分真實／範例；指標公式只能放私有 Worker／私有資料夾。
- 使用者晚上常外出，不在時只做不影響線上的事（不推送、不重啟服務）。
- 瀏覽器工具坑：內建瀏覽器窗格被隱藏時 `visibilityState=hidden`，圖表寬度為 0，量可視範圍會得到假數字 → 用 Playwright 無頭瀏覽器驗證（`python -m playwright`，已安裝）。本機 8000 服務吃的是 runner 副本（`C:\Users\mingi\txo-klines-runner`）的檔案，**不是共用資料夾**；要測自己改的檔案用只讀轉接（開一個靜態伺服器、`/api/*` 轉到 8000）。
- JJ 網站：Chrome 擴充套件操作，只讀、不按儲存、不刪指標；同時連線約 5 個分頁上限。
- 資料與程式碼檔多為 CRLF；Python 讀寫要小心換行；含中文／反斜線的腳本用 Write 工具寫成檔案再跑。

---

## 建議的接手順序

```
1. git fetch；list_sessions 看誰在跑；讀 HANDOFF.md（0、L～R）
2. 問使用者：現在要不要重啟報價服務套看門狗（夜盤會中斷 30～60 秒）
3. 等 auto_update 最新一輪 completed 後，跑 audit_vs_official.py --sample 0（C-1）
4. JJ 取樣：確認使用者已拿到新清單名稱 + Chrome 視窗在最前面，再取 CCF-1／CDF 樣本（A-1）
5. 10/12 開盤：驗 #11 昨收標示、週五選 F2 分類（A-3、B-5）
6. 其餘待決定項整理成 AskUserQuestion 一次問完（C-3、A-4）
```
