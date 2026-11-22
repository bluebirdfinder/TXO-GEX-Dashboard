# 交接檔：GEX 點位修正（週選導向）＋ JJ 大戶散戶動能還原（2026-10-16 夜製作）

> 給新視窗：先讀本檔，再讀 `HANDOFF.md`（第 0 節）、`CLAUDE.md`、`AGENTS.md`、記憶資料夾。**不要重新探索**；本檔的事實都是 10/16 當天實查過的，「未驗證」會明講。
> 使用者背景：**做週選擇權**的實盤交易者，10/16 因連續下殺虧損約 3 萬台幣，要求「正確又準確的 GEX 點位」，且新版本要「照教科書定義」。**所有點位只是模型輸出，不構成投資建議，不得鼓勵追價、不得建議拆週選價差單。**

---

## 1. 最重要的 5 件事（按優先順序）

| # | 事項 | 狀態 | 需要使用者做什麼 |
|---|---|---|---|
| 1 | **Call Wall 定義錯位**：10/16 盤後 Call Wall 46,300 在現價 47,111 下方 811 點、比 Put Wall 47,000 還低。教科書定義的正確值：Call Wall **48,000**、Put Wall 47,000 | 引擎改動＋8 項測試已提交在分支 `claude/gex-wall-definition`（f78ea15），**未發版** | 同意後走發版流程（升版、重編譯、推送） |
| 2 | **週選導向的點位**：使用者做週選，10/21（週三，週選＋月選合併大結算）占全部未平倉 **70.9%**；10/23 F4 僅 2.6%、10/28 W4 僅 1.2%、10/30 F5 僅 0.1% | 只有說明表（`scripts/gex_levels_sheet.py`，分支 `claude/gex-textbook` 3c7b6a9）；**網頁與 TG 快訊尚未改** | 決定「依到期分開」欄位格式（見 §4） |
| 3 | **Lumi 已通知**（10/16 夜）：quant_advisor.py 與 Cloudflare worker 直接用牆位，Call Wall 在現價下方時會出錯策略 | 訊息已送到 Lumi 視窗「GEX_VEX 審查 (參考羊叔)」（msg_id 63c6ca2c…），**尚未收到回覆** | 回家後確認 Lumi 回覆；發版前要先約好時間 |
| 4 | **JJ 綠線已破解**：綠線 ＝ 交易所累計「外盤成交筆數 − 內盤成交筆數」＝ 富邦成交頻道 `total.totalBidMatch − total.totalAskMatch`（自時段開盤起累計），取 K 棒收盤時的值 | 台指期 10/16 08:45～09:16 共 32 根驗證（相關 0.98、殘差 6.9）；**尚未整天／夜盤／多商品驗證** | 無 |
| 5 | **服務穩定度**：看門狗已加固並上線；「每筆成交都記錄」已寫好 | 分支 `claude/log-all-trades`（484b782）**未推送**，需重啟服務 | 同意推送＋重啟（建議在收盤後） |

---

## 2. 分支與提交總表（都在共用倉庫的 .git 裡，任何視窗用分支名就能看到）

### 2.1 已推送到 origin/main（今天）
| commit | 內容 |
|---|---|
| d0a212e | 看門狗第一版：鎖與 `connect()` 加逾時、重連改獨立執行緒、150 秒無資料自我重啟 |
| 655f5e7 | 看門狗第二版：偵測成交頻道死亡、交易時段認得國定假日 |
| 9068522 | runner 拋棄式 checkout＋本機持久資料庫（`scripts/local_data_store.py`、`scripts/runner_sync.ps1`、三個排程腳本改寫） |
| 01c9a50 | 15 秒原始記錄加入 `tot`（交易所累計買賣筆數），並把五檔頻道第一筆完整原始內容寫進日誌 |
| 6bdfbe8 | `auto_update.yml` 的 checkout 明確取 `ref: main`（修正排隊的 run 用舊 sha 與前一輪 rebase 衝突） |
| 0485f9a…8b07374 / ca83411 | JJ 樣本文件與台指期 1 分歷史 CSV |

### 2.2 **只在本機分支、尚未推送**（推送一律先問使用者，且先確認 `auto_update.yml` 最新一輪 `completed`）
| 分支 | commit | 內容 | 測試 | 上線動作 |
|---|---|---|---|---|
| `claude/gex-wall-definition` | f78ea15 | 引擎 `calculate_true_gex_profile`：Call Wall＝現價上方買權側 GEX 最大、Put Wall＝現價下方賣權側 \|GEX\| 最大；舊值另存 `call_gex_peak_strike`／`put_gex_peak_strike`；`gex_data.json` 輸出新欄位 | `scripts/test_gex_walls.py` 8 項 | **發版流程**（`release` skill：`bump_version.py`、重編譯資料、8 處版次一致、HISTORY.md），並先與 Lumi 約時間 |
| `claude/gex-textbook` | 3c7b6a9 | `scripts/gex_levels_sheet.py`：用官方未平倉＋通行版 v2 核心產出「GEX 點位說明表」（教科書定義，含各到期各自的 Max Pain、平坦區間） | `scripts/test_gex_levels_sheet.py` 6 項 | 純新增檔案，不影響線上 |
| `claude/log-all-trades` | 484b782 | 每個成交封包都記錄（`trades_YYYYMMDD.jsonl`，含逐筆與當下累計欄位）；記憶體緩衝、15 秒寫檔、失敗放回 | `scripts/test_futopt_watchdog.py` 36 項 | 推送後**重啟報價服務**（日盤收盤後） |
| `claude/store-backup-fix` | bd0f95a | 修正 OneDrive 備份同一天第二次執行 `PermissionError`（原本先刪資料夾，OneDrive 鎖檔）：改逐檔覆蓋 | `scripts/test_local_data_store.py` 17 項 | 推送後下一次排程自動套用（排程每次啟動時會 fetch＋對齊 main），**不需重啟** |
| `claude/handoff-20261016` | （本檔） | 本交接檔、HTML 版、新視窗指令 | — | 文件 |

> ⚠ **教訓**：我曾在清理工作目錄時用 `git checkout -- .` 把**尚未提交**的引擎改動還原掉，之後又口頭說「已提交」——這是錯的，後來重做才真正提交。**新視窗：做完就 commit 到自己的分支，絕不把成果留在未提交狀態。**

---

## 3. 現況（10/16 18:40 實查）

- **報價服務**（`TXO-Live-Price-Server`，runner 在 `C:\Users\mingi\txo-klines-runner`，**在 OneDrive 外面**）：08:43 起跑 `01c9a50` 的程式；資料新鮮度 ≈0 秒。包裝程式 `run_live_server_task.ps1`（新版）每次啟動會 fetch＋`checkout -f -B main origin/main`＋疊回本機資料庫。
- **runner 資料架構（新）**：runner **不再提交也不推送任何資料**。期貨盤中 K 線、選股快取、個股日 K 存在 `~\.txo_local_store\`，每次工作前後 `Sync-Runner`／`absorb`／`backup`；備份到 `OneDrive\文件\TXO-runner-data-backup\<日期>\`（保留 14 份）。舊狀態備份分支：`backup/runner-head-20261014`、`…20261016`、`…0516b`、`backup/runner-main-…`（runner 倉庫內），**先別刪**。
- **排程**：`TXO-Fubon-Futures-Klines`（平日 05:30／14:00，**週六 05:30 也會跑，抓週五夜盤**）、`TXO-Screener-Cache`（平日 16:30）、`TXO-Live-Price-Server`（登入時啟動，無限迴圈）。10/16 14:00 與 16:35 兩次**資料庫寫入成功**，備份步驟因上述 bug 失敗（資料沒遺失）。
- **JJ 頁面**：Chrome 內一個獨立視窗（標題「更生人策略看盤」），分頁在**舊對話的分頁群組**，新對話**看不到也控制不了**；請新視窗自己用 `tabs_context_mcp(createIfEmpty:true)` 開新分頁載入 `https://revive.rstock.com.tw/main-page`。**不要調整該視窗大小**（會觸發頁面重新整理，取樣器被清掉）；**不要按「儲存」**；Q 姐的 3 個版面一律不動。
- **本機原始記錄**：`~\.txo_momentum_1m\raw_YYYYMMDD.jsonl`（15 秒五檔＋成交；10/16 08:43 起含 `tot`）。**2026-10-15 23:38～10/16 03:05 因斷網缺資料**；10/15 20:24～23:38 台指期／台積電期／聯電期**逐筆成交遺失**（成交頻道死亡，看門狗當時還沒修）。
- **市場日曆**：10/17、10/18 週末休市；下個交易日 **10/19（週一）**；**10/21（週三）週選＋月選大結算**（OI 70.9%）。

---

## 4. GEX 點位：事實與待決定

### 4.1 10/16 資料日（加權收盤 47,111.26）的教科書重算
| 點位 | 值 | 相對現價 | 說明 |
|---|---|---|---|
| Call Wall（教科書） | **48,000** | +889 | 現價上方買權側 GEX 最大（舊引擎顯示 46,300 ✗） |
| Put Wall（教科書） | **47,000** | −111 | 現價下方賣權側 \|GEX\| 最大（與舊引擎相同 ✓） |
| Gamma Flip | 46,225～46,535 | −577 | 單一 VIX 版 46,225／每履約價 IV 版 46,535；現價處為正 Gamma |
| Max Pain（近四個到期 10/21、10/23、10/28、10/30） | 46,500 | −611 | 平坦區間 46,200～46,750（額外損失 ≤2%） |
| Max Pain（全部還活著的合約） | 47,000 | −111 | 平坦區間 46,650～47,250；**必須排除 10/16 當天已結算的 F3**（含它會得到 47,250，錯） |
| 老墨式淨 GEX 最大／最小 | 46,300／47,000 | | 不限位置，通行版 v2 同樣得到這組（所以錯位是**定義**問題，不是算錯） |

「Zero Gamma 46,241.2」其實是**賣買權 OI 分界**（引擎 10/6 改名，欄位仍叫 `zero_gamma_level`），不是 Gamma Flip；快訊上它和 VEX Flip 是同一數字。

### 4.2 各到期各自（週選導向）
| 到期 | 契約 | OI 占比 | Max Pain | 平坦區間 | Call Wall(上) | Put Wall(下) | 該到期 GEX |
|---|---|---|---|---|---|---|---|
| **10/21 週三** | 202610 | **70.9%** | 46,500 | 46,250～46,900 | 48,000 | 47,000 | +16.09 |
| 10/23 週五 | F4 | 2.6% | 46,000 | 46,000 | 48,000 | 46,000 | +2.69 |
| 10/28 週三 | W4 | 1.2% | 47,800 | 47,700～47,900 | 49,000 | 45,000 | −0.17 |
| 10/30 週五 | F5 | 0.1% | 47,200 | 47,200～47,250 | 51,700 | 46,750 | −0.05 |

→ 週一週二時，只有 10/21 這一檔有代表性；週選 F 檔的 OI 要接近到期才會累積。

### 4.3 **待使用者決定**（回家後用 AskUserQuestion 一次問完）
1. **發版**：同意 `claude/gex-wall-definition`（新定義）上線？（會動所有下游：網頁、TG 快訊、社群卡片、Lumi；要與 Lumi 約同一時間。）
2. **「依到期分開」的點位欄位**（建議設計，待確認）：`gex_data.json` 新增 `weekly_focus` 區塊，對「未來 14 天內、OI 占比 ≥1%」的每個到期給 `{expiry, code, weekday, oi_share_pct, call_wall_above, put_wall_below, max_pain, max_pain_band, expiry_gex}`，並標示 `primary`（OI 占比最大者）；OI 占比 <5% 時標「未平倉太少，僅供參考」。實作用 `scripts/gex_levels_sheet.py` 的每到期計算；**要決定用現行引擎（單一 VIX）還是通行版 v2（每履約價 IV，較教科書）**，我的建議是 v2。
3. **TG 快訊與網頁文案**：Call Wall 天花板／Put Wall 地板改措辭；「Zero Gamma」改標「OI 分界」並另列真正 Gamma Flip 範圍；Max Pain 註明範圍與平坦區間；是否加「本週主力到期」區塊。
4. **推送並重啟**：`log-all-trades`（成交每筆記錄）與 `store-backup-fix`。

### 4.4 TG 快訊貼文版（已給使用者，供朋友參考）
內容見對話；重點是更正「Call Wall 46,300 → 48,000」「Zero Gamma 實為 OI 分界」。

---

## 5. Lumi 端（露米籌碼監控機器人；路徑 `C:\Users\mingi\OneDrive\文件\TG 自動化機器人\露米籌碼監控機器人`）
- **誰讀牆位**：`quant_advisor.py` 第 308～339 行（`sell_call = call_wall`、`sell_put = put_wall`，條件 `put_wall <= max_pain <= call_wall`）；`cloudflare_worker_lumi_fusion.js` 第 374～392 行（GEX 牆位警報，讀 `call_wall_strike`／`put_wall_strike`／`zero_gamma_level`／`max_pain_strike`）。TG 盤後快訊文案由 Lumi 端組裝。
- **已通知**（見 §1 第 3 項）。通知內容已涵蓋：事實、風險、TXO 修正計畫（語意改變）、文案更正、週選導向、請回覆。
- **規則**：TXO 不改 Lumi 的檔案、Lumi 不改 TXO 的檔案；Lumi 有自己的 `CLAUDE.md`／`AGENTS.md`／`HANDOFF.md`，要動 Lumi 先讀它們並遵守多視窗守則。

---

## 6. JJ「大戶散戶動能」還原進度（**公式與細節只放私有資料夾**，公開 repo 不放定義）

私有資料夾：`C:\Users\mingi\txo-private\jj_momentum\`（`FINDINGS_20261015.md` 為完整紀錄、`jj_TXF_1m_20261014_history.csv`）。記憶檔 `reference_jj_sampling_method.md` 有取樣方法。

| 指標 | 進度 | 重點 |
|---|---|---|
| 綠線（散戶成交筆差） | **已破解（部分驗證）** | 見 §1 第 4 項；本機 `raw_20261016.jsonl` 的 `tot` 欄位可對照；時間對齊：JJ 第 m 分鐘 K 棒值＝該棒結束時（start+60s）的累計差 |
| 紅線（大戶委託口差？）、黃線（市場委託口差？） | **未解** | 五檔頻道只有 5 檔價量、沒有委託筆數／總量；期交所 MIS 公開行情也沒有；去趨勢後與成交衍生量相關僅 0.3～0.65。若是「成交資料」算的可窮舉（門檻×口數或筆數×累計或滾動視窗）；若是全市場委託簿總量則拿不到原料 |
| 大戶比例、同向指標 | 未開始 | |

- **取樣方法（重點）**：JJ 圖表內部有完整時間序列：`document.querySelector('iframe').contentWindow.chartWidget.model().model().dataSources()` 找 `title(true)==='大戶散戶動能'`，`.data()` 的 `firstIndex()/lastIndex()/valueAt(i)` 回 `[bar時間, 紅, 綠, 黃]`。**1 分線只載入約 300～1,000 根；5 分線 300 根約 25 小時**——要長歷史請用 5 分線。即時取樣用 Web Worker 計時（頁面 `setInterval` 被遮住會被降速）。切商品：點左上商品框→**先 Ctrl+A**→輸入→點第一筆。JS 輸出會被截斷（約 1,000 字）要分段，字串含 `n=` 會被過濾器擋。
- **資料完整度**：15 秒快照只涵蓋約 91% 成交量，所以要上 `log-all-trades`（每筆都記）才能窮舉紅黃線。
- **本機若要窮舉，下一步**：收集 1～3 個完整交易日（`trades_*.jsonl`＋JJ 5 分歷史），在私有資料夾寫窮舉腳本，用「去趨勢（變化量）相關」與「另一天樣本外驗證」評分，找不到就如實回報。

---

## 7. 使用者的規則（必讀）
- `git push` **一律先問**；推送前確認 `gh run list --workflow auto_update.yml --limit 1` 是 `completed`；用暫時 worktree；**只 add 自己的檔案**；不在共用資料夾動 git 狀態；別人未 commit 的檔案不碰（先 `list_sessions`）。
- 使用者**看不到 .md**：文件要同時給 HTML（`SendUserFile`）或貼在對話。要使用者回答的事用 **AskUserQuestion 卡片**；任何任務回報**完成百分比**；進度用表格、流程用 code block 圖。
- 使用者不在家時：只做不影響線上的事（不推送、不重啟）；**服務卡死時可自己重啟**（已授權）。
- 紅線（`AGENTS.md`）：不偽造資料、不建議拆週選價差單、不建議追價、持倉診斷分真實／範例、指標公式只放私有資料夾。
- 本專案**Remote Control 一開始就要開**（`set_remote_control` self=true）。

## 8. 踩過的坑
1. `git checkout -- .` 會把未提交成果還原掉（見 §2.2 教訓）。
2. 調整 Chrome 視窗大小會讓 JJ 頁面重新整理，取樣器清空。
3. PowerShell 沒有 heredoc；含中文／反斜線的腳本用 Write 工具寫成檔再跑。
4. 背景常駐的 python 本機伺服器、繞過瀏覽器區域網路權限、對 runner 的某些 git 操作會被自動模式擋下，**不要繞過**，回報使用者。
5. 電腦操作功能（computer-use）截圖會把使用者其他視窗暫時隱藏；除非必要不用。
6. 看門狗只看「有沒有任何訊息」曾漏掉成交頻道死亡；現已補。runner 舊作法 `git pull --rebase` 與雲端同寫 `klines_cache.json` 必衝突，已改拋棄式 checkout。

## 9. 建議的接手順序
```
1. 開 Remote Control → git fetch → list_sessions（確認誰在跑；Lumi 視窗是否已回覆）
2. 讀本檔、HANDOFF.md 第 0 節與最新列、CLAUDE.md、AGENTS.md、記憶資料夾
3. 抽樣驗證：報價服務在線(feed_age_sec)、今天 14:00/16:35 排程日誌、runner 狀態乾淨、分支都在
4. AskUserQuestion 一次問完：§4.3 的四件事
5. 依答案：發版（wall 定義）→ 與 Lumi 約同時上線 → weekly_focus 欄位 → TG／網頁文案 → 驗證（audit_vs_official.py --sample 0）
6. 推送 log-all-trades 與 store-backup-fix，收盤後重啟，確認 trades_*.jsonl 開始寫入
7. 週一 10/19 開盤：用整天資料驗證 JJ 綠線（含夜盤、聯電、台積電、小型台積電）；開始紅黃線窮舉
```

---

## 附錄（10/16 夜補充）：使用者的實際做法與「點位怎麼給」的決定

**使用者習慣**：週三晚上組「兩天後的週五選」；週五晚上組「下週三的週三選」。從來沒直接組過較遠的月選，不想把點位搞複雜。

**重要更正**：2026-10-21（週三）本身就是 10 月**月選**結算日（第 3 個週三）。所以「下週三那一檔」這週剛好是月選合約 `202610`，不是遠月；週一（10/19）組到週三也只剩 2 天，跟他「週三晚組週五」的節奏一樣。我先前把它說成「遠」是誤導，已在聊天更正。

**網頁現況（讀 origin/main）**：`gex_data.json` 已有各到期桶（`mth_*`＝10/21 月選、`fri_*`＝10/23、`w1_*`＝10/28、`w2_*`＝11/04 尚無 OI），並有 `weekly_gex / friday_gex / monthly_gex` 三個分頁資料與 `dte_dates`。但頭條的 `call_wall_strike / put_wall_strike / max_pain_strike / gamma_flip` 是**全部到期合併**，且牆仍是舊定義（不限現價上下）。10/16 夜 GEX 規模：月選約 2,777（Call 側加總）、10/23 約 235、10/28 約 25——**月選吃掉 90% 以上**。

**決定（最簡版，尚待使用者回家確認發版）**：
1. 頭條只放「下一檔你要下單的到期」一組點位：Call Wall（現價上方）、Put Wall（現價下方）、Gamma Flip、Max Pain（區間）。
2. 「下一檔」自動規則：離今天 2～5 個日曆日的下一個結算日（週三晚→當週五；週五晚→下週三；週一→當週三）。
3. 全部到期合併的數字降級成一行「背景」，不再當頭條。
4. 到期桶 OI 太小（Call+Put < 約 1,000 口）時標「OI 太小，參考性低」，不給牆。
5. 結算日前一天加提示：「這檔結算後這批 GEX 消失，點位重算」。
6. 網頁頭條與 TG 快訊用同一個函式算，避免兩邊不一致。

**10/21 月選單獨算（資料日 10/16、加權收盤 47,111.26）**：Call Wall 48,000（GEX +4.54）、Put Wall 47,000（-6.91）、Gamma Flip ≈ 46,569、Max Pain 46,500（平坦區間 46,250～46,900）、Call OI 59,855／Put OI 36,949。
**純週選（F4/W4/F5）**：總 GEX 僅約 +2.5 億（月選約 +16 億），牆與 Flip 力道弱；F5 只有 147 口。
腳本：臨時算法在 `scripts/gex_levels_sheet.py`（分支 claude/gex-textbook）加上「只取某些合約」的 `compute_day(sub)` 呼叫，尚未寫進正式程式。

**使用者回饋（10/16 夜）：「之前的 Max Pain 我覺得都很準，我有觀察」**
→ 發版時 **Max Pain 的算法與位置維持現狀，不要動**。網頁現行 `max_pain_strike` 是用 `w1/w2/fri/mth` 四檔近月合併（10/16 夜為 46,500，與我表中的「近四個到期」46,500 一致）；我表中「全部還活著」的 47,000 把遠月（11、12 月、2027）也算進去，**不採用作頭條**。只在旁邊加「平坦區間」（46,200～46,750）當補充，數值頭條仍沿用舊的。牆（Call/Put Wall）才是要改定義的部分。

---

## 附錄二（10/17 凌晨，Lumi 轉來的唯讀待辦，未做）

Lumi（視窗「GEX_VEX 審查 (參考羊叔)」）回覆：已收到牆位錯位通知，盤點完前不改任何東西；在使用者決定前不動 TXO 檔案。另請我們做兩件**唯讀**的事（使用者在 Lumi 視窗選的）：
1. 重算 **2026-10-14（週三結算日）13:30 前快照**（公開版 commit `4136457`，更新時間 10/14 09:03，籌碼日 10/14），比較「到期天數用整數天（舊算法）」與「小數天到 13:30（現行）」兩種的 Call／Put Wall、Zero Gamma、總 GEX／VEX 差多少點，用來判斷「到期天數修正是否讓結算日牆位變準」。Lumi 已知 09:03 為 Call 49,000／Put 48,500／總 GEX +4,400，15:04 為 48,300／48,000／+470（週選到期被移除的正常現象，看不出修正效果）。
2. 查防護：10/14 23:59 那筆（更新時間 10/15 07:49）牆位 47,700／47,700、總 GEX 0.0、`gamma_flip_standard` 為空，像資料抓失敗的垃圾快照，00:12 才恢復。請確認引擎／推送有沒有「資料不完整就不覆寫」的防護。
做法提示：引擎不是設計來重跑歷史日，先用 `git show 4136457:data/gex_data.json` 取當時輸入，再以只改 T 的方式離線重算；全程不動線上、不推送。

---

## 附錄三（10/17 凌晨，Lumi 的受影響清單，唯讀盤點）

Lumi 核對公開版屬實（10/17 01:57：call_wall 46,300 < 現價 47,111、call < put 47,000）。Lumi 端讀取牆位的地方（Lumi 尚未改任何檔案，等使用者決定；不會動 TXO 檔案）：
1. `cloudflare_worker_lumi_fusion.js`（正式推播，風險最高）：直接讀 call/put wall，只有 null 防呆，沒有位置合理性檢查；Call Wall 在現價下方時會產生「賣價內 Call」下單文字。需手動部署 Cloudflare，且檔案上有別的視窗未 commit 修改。
2. `send_tg_alert.ps1`：顯示牆位、型態判斷（cw<pw 時順序判斷會錯標）、`gex_points` 歷史記錄會存進異常牆位。
3. `tv_webhook_listener.py`、`tv_compute_daily_params.py`、`tv_auto_sync.py`、`update_tv_pine_defaults.py`：牆位寫進 TradingView Pine 預設值，圖上會畫出錯位的線。
4. `quant_advisor.py` 308～339 行：目前沒有正式流程呼叫，風險低。
5. 回測（`backtest_maxpain_topology.py` 等）：import TXO 共用資料夾的 `calculate_true_gex_profile`，**發版後 `call_wall_strike` 語意改變，Lumi 歷史回測的 Call Wall 會悄悄跟著變**——Lumi 要決定釘住舊定義或重跑。

**Lumi 擬建議的防呆規則（待使用者決定）**：`call_wall < 現價` 或 `put_wall > 現價` 或 `call_wall < put_wall` → 不產生策略／下單文字，標示「牆位異常」，只顯示數字；TG 型態與 TV 同步同規則。
**對我們的要求**：發版前先告知 Lumi **時間點**與**新欄位名稱**（`call_gex_peak_strike`／`put_gex_peak_strike`），發版後 Lumi 重新核對所有讀取處。
**新視窗注意**：發版時別忘了 TXO 共用資料夾同步會立刻影響 Lumi 回測；欄位語意改變要在發版說明中明講（HISTORY.md），並把舊的「不限位置最大值」留在新欄位，避免 Lumi 用到錯的語意。使用者約 23:00 回家後 Lumi 會把清單給他決定。

---

## 附錄四（10/17 夜，Lumi 更新）

10/17 夜盤晨報再次出現牆位錯位，使用者改決定「先處理牆位異常、對齊 TXO 專案」。Lumi 已實作防呆：分支 `claude/wall-sanity-guard`（c3bb995，基於 origin/main，**未 push**，TXO 檔案完全沒動）。規則：`call_wall < spot_price` 或 `put_wall > spot_price` 或 `call_wall <= put_wall` → 視為牆位異常；TG 快訊照實顯示數字加警語並停止型態判讀、Worker 比照缺牆位 Hard Block、TV 同步與 webhook 攔截。現價一律讀 `gex_data.json` 的 `spot_price`（缺值時只檢查 Call 是否高於 Put）。
**對我們的要求**：我們發版後這套防呆不用改；發版時要通知 Lumi **時間點**與新欄位名稱（`call_gex_peak_strike`／`put_gex_peak_strike`）；**`spot_price` 欄位若改名或語意改變，必須事先通知 Lumi**（它是防呆的唯一現價來源，本次發版不要動它）。
