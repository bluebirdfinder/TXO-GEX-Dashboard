# 🔍 Self-Audit 發現清單與待辦事項 (2026-09-13 稽核)

本文件彙整對 **GEX 主儀表板**（`index.html`/`app.js`/`scripts/*.py`）與 **尋鳥戰情交易室**（`trading room/room.js`/`room.html`）的 self-audit 結果，目的是揪出 Gemini/antigravity 遺留的幻覺資料、寫死假數字，以及需要對照真實指標源碼校正的部分。

**範圍聲明**：這份清單是目前 audit 到的部分，**不是全部掃完**。凡標示「⏳ 尚未稽核」的區塊，代表還沒仔細看過，開新的對話室時應該先從那些區塊開始，而不是假設已經乾淨。

**正在另一個聊天室處理、這份清單不用管的項目**：
大戶散戶動能指標所需的富邦 Books/Trades 即時行情串接（`scripts/fubon_api_provider.py`、`scripts/live_price_server.py`）——這是目前另一個 session 正在做的事，等它做完再回頭把 `room.js` 的假動能公式換成真數據。

---

## ⚠️ 重要：目前同時有多個 session 在並行處理這個專案，開新對話室前請先確認彼此進度

2026-09-13 深夜發現：除了這個稽核 session、以及正在做大戶散戶動能即時串接的 session，**至少還有兩個其他獨立 session 也在動這個專案**：

1. **「Antigravity 專案交接準備」**：已完成交接工作並推上 `main`（commit `7488a9c`）——新增 `CLAUDE.md`、`.claude/skills/release/SKILL.md`、更新 `PROJECT_HANDOVER.md` 第五節，另外還做了全域的 `antigravity-handover` skill（含「零偽數據範本」）與 `cloud-automation-pipeline` skill（這兩個是全域 skill，不在這個 repo 的 git 樹裡）。這個 session 本身已收工。
2. **`txo-gex-dashboard-80`**：對 `scripts/fetch_and_calc_vision.py` 做真實資料修復（詳見下方「一之一」）。**2026-09-14 更新：這就是本次撰寫此更新的 session 本人——3 項全部做完，且已實跑完整 pipeline（`python scripts/fetch_and_calc_vision.py`）驗證 A+B+C 三項一起運作正常，見下方最新狀態表**。仍然**故意不 commit**，等使用者確認後才 commit + push。

**開新對話室接手這份清單之前，請先確認 `txo-gex-dashboard-80` 那邊 3 項有沒有全部做完並 commit**（截至 2026-09-14 凌晨：3 項都做完了，只是還沒 commit——真正要看的是 `git status` 有沒有還留著 `scripts/fetch_and_calc_vision.py` 的 uncommitted 修改，有的話代表還沒 commit，不要重做），避免兩邊改到同一個檔案（`fetch_and_calc_vision.py`）而衝突，也避免重複發現同一個 bug 浪費工。之後每開一個新 session 處理這個專案，都應該先讓它讀這份文件，確保大家看到的是同一份最新清單。

---

## 一之一、`txo-gex-dashboard-80` 發現的真實修復（本機尚未 commit，等 3 項一起測完）

這是另一個 session 對 `scripts/fetch_and_calc_vision.py` 做的修改，2026-09-13 深夜在使用者本機 `git status` 時發現是未 commit 狀態。內容經過檢視，**是真實、高品質的修復**，不是幻覺：

| 修復項目 | 內容 | 狀態 |
|---|---|---|
| `fetch_twse_institutional_t86()` | 抓證交所官方 T86 三大法人買賣超日報，取代原本 `stock_futures` 裡 `spot_inst_net`/`spot_foreign`/`spot_trust`/`spot_dealer` 的**佔位假數字**（含原本 `spot_gov = int(-spot_inst_net * 0.18)` 這種瞎猜比例，已移除），查不到時誠實標記 `spot_data_unavailable: true`，不補假數字。 | ✅ 已寫好，**已用完整 pipeline 實測**：2330 外資-8252/投信-181/自營-401，跟 T86 官方數字一致 |
| `fetch_taifex_stock_futures_contract_map()` | 抓期交所官方個股期貨合約代碼對照表（`data/taifex_stock_futures_contract_map.json`，265 檔真實對照，例如 `"2330": "CD"`），這份剛好也解決了「大戶散戶動能」個股期貨擴充所需的股票代號→期貨合約代碼對照。 | ✅ 已寫好，**已實測**，286 檔個股期貨裡成功對照 264 檔 |
| `fetch_taifex_stock_futures_large_trader_batch()` | 對每一檔個股期貨查期交所官方大額交易人未平倉，取代原本 `top5_net_oi`/`top10_net_oi` 的佔位假數字。 | ✅ 已寫好，**已實測**：2330 top10淨部位-3962，跟人工核對 TAIFEX 官網一致 |
| **5 日法人歷程矩陣，4/5 天寫死**（`institutional_5day_history`/`night_institutional_5day_history`） | 2026-09-14 凌晨完成：比照同檔案裡 `history_10_sessions` 已經在用的真實快照模式（`load_session_snapshots()`），新增 `data/institutional_snapshots.json` + `load/save/write_institutional_snapshot()`。T-4~T-1 改成「有真快照才顯示，沒有就 `has_snapshot: false` + 全部欄位 `null`」，不再寫死假數字；T-0 當天真數據會寫回快照，之後每天自然累積出真實歷史。**注意**：T-0 本身呼叫的 `fetch_official_taifex_large_trader()`/`fetch_official_taifex_futures_institutional_oi()`/`fetch_official_taifex_options_matrix()` 這幾支函式，內部本來就有「抓不到就默默退回寫死保底值」的舊行為（例如 `lt_inst.get('top5_net', -11018)` 這種 fallback），**這次沒有動它**，是範圍外的殘留問題，見下方新增條目。 | ✅ 已寫好，**已用完整 pipeline 實測**：首次執行 9/11(今天)✅真實、9/7~9/10 誠實顯示「尚無快照」 |

**追加發現（`app.js`，2026-09-13 深夜~09-14 凌晨陸續修好）**：
1. `renderGEXChart()` 「疊加對比模式」（比較今日 vs 前一盤別 Net GEX 曲線）原本是幻覺數據——`prevNetVal = netGexVal.map(v => v * 0.88 - 15.0)`，直接拿**今天自己的曲線**乘一個固定係數瞎掰出「前一盤」。已修好：改成真的從 `sessions[currentSessionIndex - 1]` 抓真實前一盤資料，依當前分頁比對真實履約價，缺資料的履約價用 `null` 讓圖表斷開而非誤導畫線到 0。✅ 已修。
2. `VALID_PASSCODE`：6 處寫死字面值 `'GEX2026'` 改成引用常數。✅ 已修（小問題，非資料造假，純程式碼品質）。
3. `populateAiQuantDigest()`：原本忽略使用者切換的歷史盤、永遠讀最新一盤，已修成跟著 `currentSessionIndex` 走。✅ 已修。

**確認了 `app.js` 確實跟 `room.js` 一樣藏著同類型假資料**，這份稽核清單「一、」的 `app.js` 待稽核項目，上述 4 點已處理，其餘（`handleLiveTick` 的 0.62 固定係數外推、股票期貨排行榜殘留的 `ADR_MAPPING.get(code,...)` 用到外層迴圈殘留變數導致 ADR 欄位可能對錯股票）**仍未處理**，見下方新條目。

**官股（八大官股行庫）調查結論**（2026-09-14 凌晨，使用者提供富邦/XQ App 截圖後追查）：官股買賣超**有真數據**，但真正來源是「全市場券商分點買賣日報」（證交所官方，需分點代號分類），**該查詢頁面有 CAPTCHA 保護**，無法免驗證碼自動化抓取；免費公開的 TWSE T86 只到外資/投信/自營商三大法人層級，沒有官股這一層。可行選項僅剩「付費資料商」（例如 FinMind Sponsor 方案的 `TaiwanStockGovernmentBankBuySell`），使用者目前沒有訂閱，**決定維持 `spot_gov = 0` + `spot_data_unavailable` 標記，不追這個欄位**，之後除非使用者決定付費訂閱資料商，否則不用重查。

**尚未處理的殘留問題（記錄，之後找時間一起處理）**：
1. `fetch_official_taifex_large_trader()` / `fetch_official_taifex_futures_institutional_oi()` / `fetch_official_taifex_options_matrix()` / `fetch_taifex_night_institutional_trading()` 這幾支函式，抓取失敗時會**默默**退回函式一開始就寫死的保底數字（例如 `res = {'dealer': 2019, 'trust': 75825, 'foreign': -82423}` 這種初始值），不會像本次新增的 5 日矩陣快照系統一樣明確標記「無即時數據」。目前只有在真的抓取失敗時才會顯示這些舊保底值（正常情況下都是抓到真數據），但嚴格來說跟 AGENTS.md 鐵律6「無真實數據時必須明確顯示⚪無即時數據」的要求還有落差，值得之後專門處理一次。
2. 個股期貨清單裡 `ADR_MAPPING.get(code, ...)` 用到的 `code` 是外層迴圈（`for idx, stk in enumerate(catalog_270)`）跑完後殘留的變數，不是當前這一列股票自己的代號（Python for 迴圈變數不會在迴圈結束後收回作用域），導致每一列的 ADR 連動欄位很可能對到錯的股票。跟本次任務無關，先記錄。

**2026-09-14 上午更新：已 commit + push**（`claude/bold-galileo-dy1oxb` 分支 commit `284a3e4`）。3 項 + app.js 修復全部上線，使用者已確認。

---

## 一、GEX 主儀表板（index.html / app.js / scripts）

### ✅ 已修復（2026-09-14 上午，`txo-gex-dashboard-80`）

**修正**：這兩個檔案的實際消費者查證後是 `trading room/room.js`（尋鳥戰情室），**不是** GEX 主儀表板 `app.js`/`index.html`——原文件把它們歸在「一、GEX主儀表板」章節底下是分類錯誤，但既然已確認是假資料就先修了，不用重複發現。

| # | 位置 | 問題 | 修復內容 |
|---|---|---|---|
| 1 | `scripts/fetch_institutional_momentum.py` | docstring 宣稱「Fetches real TAIFEX...」，但**整支程式沒有任何網路請求**，法人未平倉/散戶留倉/近5日籌碼歷程全部是寫死常數（`foreign_oi = -12450` 等），跟真實市況無關，每次執行都輸出一樣的數字。 | 改抓 TAIFEX 官方 OpenAPI CSV（`MarketDataOfMajorInstitutionalTradersGeneralBytheDate`，跟 `room.js` 本身在 `momentum_data.json` 失效時的即時 fallback 用同一個端點，確保兩條路徑數字一致）+ 重用 `fetch_official_taifex_retail_sentiment()` 取得散戶多空比；5日歷程改成 `data/momentum_snapshots.json` 真實快照累積（模式同 `institutional_snapshots.json`），沒真數據的日子誠實顯示 `has_snapshot:false`。已實測：外資-551426/投信84552/自營-277059、散戶多空比2.43%，跟官方數字一致。 |
| 2 | `scripts/build_screener_cache.py` | 只有「當日收盤價/漲跌/量」是真的（來自 `tw_quotes_latest.json`），但拿去算均線/乖離率/量比/MACD狀態/5K趨勢/DeMark訊號的**過去30根K棒歷史是 `random.Random(股票代號當種子)` 生出來的假歷史**（`generate_synthetic_ohlcv`），所以算出來的訊號全部不可信。 | 改成逐檔抓 TWSE `STOCK_DAY` / TPEx `tradingStock` 官方每日歷史（真實約30根K棒），依交易日快取到 `data/screener_ohlcv_cache.json` 避免每次都重打1400+次請求；抓不到真歷史的（例如 `TXF`/`MXF` 這類期貨代碼、下市股）明確標記 `history_unavailable:true`、訊號留空，不再捏造。**注意**：MACD/5K/DeMark 判斷邏輯本身仍是簡化版近似公式（不是逐行對照 Pine Script 的真實 TD Sequential/MACD），這次只解決「輸入數據是假的」問題，公式本身校正留給「指標源碼逐一校正」那個大項目。首次全量執行約 1400 檔，需要 10-20 分鐘（背景執行中）。 |

### 🔴 新發現的假資料（`fetch_official_taifex_retail_sentiment()`，2026-09-14 上午追查 momentum 修復時發現）

修復上面第1項時，重用 `fetch_official_taifex_retail_sentiment()`（`scripts/fetch_and_calc_vision.py`，本身餵給 GEX 主儀表板的散戶籌碼區塊）過程中，發現這支函式裡還有**其餘寫死假數字**，這次**只修了其中一處**（`mtx_r_net`/`tmf_r_net` 原本是 `9496`/`24932` 寫死常數，已改成用真實 `long-short` 算出）：

| 欄位 | 問題 | 狀態 |
|---|---|---|
| `mtx_r_net` / `tmf_r_net` | 原本寫死 `9496`/`24932`，跟旁邊算出來的真實 `long`/`short` 無關 | ✅ 已修，改成 `long - short` |
| `retail_sentiment_details.*.daily_change` | `2380`/`17451` 寫死，不是真實日增減 | ❌ 未修，需要歷史留倉比對（類似快照模式） |
| `retail_sentiment_details.*.prev_ratio` | `19.97`/`9.63` 寫死，不是真實前一日比率 | ❌ 未修，同上 |
| `retail_sentiment_details.broker_snapshot` | 整個區塊（`foreign_tx_net: -83078`、`foreign_call_net: 2543`等）全部寫死常數 | ❌ 未修，需要另外找真實對應數據源 |

### 🔴🔴 最嚴重發現與修復：核心 GEX 引擎的選擇權未平倉部位，從未接過真數據（2026-09-14）

**這是整份稽核清單目前為止最嚴重的發現**，比個股期貨籌碼或法人5日矩陣都嚴重，因為它是整個「尋鳥 TXO GEX 量化系統」的核心賣點本身：

`calculate_true_gex_profile()`（GEX/VEX 計算的心臟，`scripts/fetch_and_calc_vision.py`）接收一個 `option_chain` 參數，理論上應該裝真實 TAIFEX TXO 各履約價的未沖銷契約量（Open Interest）。**查證後，全部 3 個呼叫點永遠傳入空字典 `{}`**——整支程式從來沒有任何函式去抓 TAIFEX 真實選擇權未沖銷部位。函式內部原本的 fallback 是一個**以現價為中心人工湊出來的高斯鐘形曲線**（`int(3500 * math.exp(-((K-...)/300)**2) + 800)`），跟任何一天的真實選擇權籌碼毫無關係。也就是說：**Call Wall、Put Wall、Zero Gamma、Max Pain、Net GEX 曲線、GEX+ 翻轉點——這個產品從第一天上線至今，所有這些核心數字都是「真實現貨價 + 假選擇權籌碼」算出來的**。連「週選 W1 vs W2」的拆分都是假的，只是把同一個 GEX 數字乘 0.65/0.35 硬拆。

**已確認並徵求使用者同意修復**。真數據源：TAIFEX 官方「選擇權每日交易行情下載」`https://www.taifex.com.tw/cht/3/optDataDown?down_type=1&commodity_id=TXO&queryStartDate=...&queryEndDate=...`，**免驗證碼**，一次請求可涵蓋整段日期範圍（測試過4個交易日一次回傳，不用逐日查）。

| 修復項目 | 內容 |
|---|---|
| `fetch_taifex_txo_open_interest()` | 抓真實逐履約價/買賣權/契約月份未沖銷契約量。**注意**：回應宣稱的 charset 是 MS950 但實際要用 `cp950` 解碼，big5/utf-8 都會亂碼。 |
| `classify_txo_contract_buckets()` | 用每個契約的**真實結算日期**（而非解析代碼字尾字母）分類：無字尾=月選、結算日是週三=Wednesday週選、週五=Friday週選，取最近到期的分別當 w1/w2/fri/mth。 |
| `build_real_option_chain()` | 把分類好的真實OI組成 `calculate_true_gex_profile()` 要的格式，某履約價沒有真實資料就是真實的0口未平倉，不是預設值。 |
| `calculate_true_gex_profile()` 改寫 | 移除假高斯曲線 fallback；W1/W2 改成用各自真實到期天數分別算真實 Greeks（不再是同一個數字硬拆65/35）；履約價範圍改成「現價±900內的真實上市履約價」（剛好等於原本37檔的密度，只是資料是真的）；`option_chain` 完全抓不到時才退回舊的合成網格（且OI=0，不再是假高斯）。 |
| 即時路徑接線 | `generate_gex_payload()` 的 `gex_profile`/`day_profile`/歷史10盤別的即時GEX曲線，全部改吃這個真實 option chain。今天沒有真數據時明確印警告，不是安靜退回假數字。 |

**實測驗證**：Zero Gamma 45696、Call Wall 46500、Put Wall 46000，現價46184.85，走勢跟位階都合理（牆位在現價附近300-500點，不是亂跳）。

**順便修好的舊 bug**（在做歷史回補時發現 `backfill_snapshots.py` 自己也有問題，不是這次新增的）：
- `fetch_twse_index()` 用錯 `type=MS` 參數（回傳的是大盤成交統計，根本沒有大盤指數這一列）且取值欄位錯用 `row[-1]`（那欄其實是空白註記欄），兩個 bug 疊加導致**這支函式從來沒有真的抓到過歷史大盤指數**。已修正為 `type=IND` + `row[1]`。
- `fetch_taifex_daily_tx()` 用錯參數名 `Date_From`/`Date_To`（官方要的是 `queryStartDate`/`queryEndDate`），導致官網直接回「日期時間錯誤」錯誤頁，這支函式也從來沒有真的抓到過歷史TX期貨價。已修正。
- `fetch_taifex_pc_ratio()` 打的 URL `callPutRatioHis` 已經404，改成重用 `fetch_and_calc_vision.py` 裡本來就正常運作的 `fetch_official_taifex_pc_ratio()`。

**5日歷史回補**：`backfill_snapshots.py` 現在會用真實 TXO 未平倉 + 那一天的真實現貨價 + 那一天當下重算的到期天數，把 `session_snapshots.json` 裡 `zero_gamma_level`/`call_wall_strike`/`put_wall_strike`/`max_pain_strike` 也填上真數據（原本 docstring 自己承認「需要歷史OI，目前抓不到」，現在抓得到了）。已實測 09/08~09/11 四天全部填上合理的真實數字，09/14（今天，TAIFEX還沒公布）誠實留空不亂猜。

**尚未做的部分**：過去日子的「完整逐履約價GEX曲線」（`total_gex`/`weekly_gex`等陣列，不是單一數字的zero_gamma/call_wall）沒有一起回補，維持用今天的真實籌碼去套那天的現價（比零值/假數據好，但不是那天當下的真實籌碼)——這是經使用者同意的範圍縮減（「不管歷史數據」），如果之後要做完整歷史曲線回補，做法完全一樣（同一批已抓到的 `_txo_oi_by_date`），只是要多寫一段迴圈。

---

### ⏳ 尚未稽核（優先順序建議）

1. **`scripts/fetch_and_calc_vision.py`**（3500+行，核心 Black-Scholes GEX/VEX 引擎）——**部分稽核**：個股期貨法人籌碼(A/B)、法人5日矩陣(C)、`fetch_official_taifex_retail_sentiment()`、**核心GEX/VEX計算本體的選擇權未平倉數據（見上方🔴🔴最嚴重發現）** 都已查過並修復，但這是逐線索追出來的，**不是逐函式全文核對**，其餘尚未提及的函式還沒看過。仍是最大支、優先度最高的檔案。
2. ~~`scripts/fetch_real_quotes.py`~~ **✅ 2026-09-14上午已逐函式核對，乾淨無假資料**——全部走 TWSE/TPEx/TAIFEX 官方 OpenAPI，抓不到的股票誠實標記 `is_real:false`，不編數字。
3. `scripts/fubon_api_provider.py`／`scripts/live_price_server.py` 的寫死保底值——**不屬於這條清單處理範圍**，使用者已說明這兩支是「大戶散戶動能」的另一個聊天室在處理，這邊不要碰。
4. ~~`data/session_snapshots.json` 與 `scripts/backfill_snapshots.py`~~ **⚠️ 更正之前的誤判**：先前 session 稽核時看過全文覺得「乾淨」，但那次沒有實際執行測試過。2026-09-14 實際跑過才發現 `fetch_twse_index()`/`fetch_taifex_daily_tx()`/`fetch_taifex_pc_ratio()` 三支函式全部因為參數名/URL/欄位索引錯誤而**從來沒有真的抓到過任何數據**（靜默回傳 None，表面上看代碼邏輯正常但實際上一直失敗）。已於本次修復（見上方）。**教訓：只看代碼判斷「乾淨」不夠，看起來邏輯正確的 fetch 函式也要實際跑一次驗證真的有拿到數據，不能只憑閱讀程式碼判斷。**
5. ~~`scripts/generate_social_card.py`~~ **✅ 2026-09-14上午已核對，基本乾淨**——100% 吃真實 `gex_data.json` 產生三張社群卡圖，唯一疑點是 `build_card1_html()` 裡兩處極端罕見的 fallback（`data.get("gex_plus_flip", 45217.6)` 這種，只有在 `gex_plus_flip`/`total_vex` 兩個欄位都缺失時才會觸發，正常情況下引擎必定會算出這兩個值），影響機率極低，記錄但不列為優先修復項。
6. `app.js`（3250+行）——**部分稽核**：已修復 T-1疊加線、`populateAiQuantDigest`、`VALID_PASSCODE`。2026-09-14上午追查完以下兩點，決定先記錄不馬上修：
   - `handleLiveTick()` 用固定係數 `0.62` 把 tick 價格變動外推成 Zero Gamma/GEX+翻轉點的即時位移（`liveZg = baseZg + priceDelta * 0.62`）。這**不是憑空捏造的展示假數字**，而是「兩次後端完整重算之間，前端做即時內插近似」的工程手法（完整重算要跑整條選擇權鏈的 Black-Scholes，沒辦法每個 tick 都做），但 0.62 這個係數本身看不出是從當天真實選擇權鏈算出來的，比較像是抓一個業界常見經驗值，UI 上也沒有標示「這是即時內插近似值，正式數字以下次完整重算為準」。風險判斷：比起其他找到的「憑空編數字」問題輕微很多，且改動涉及即時報價渲染邏輯，貿然改有讓正式看盤功能出錯的風險，**先記錄，不在這次動**。
   - `app.js` 裡至少 17 處 `xxx_wall_strike || 數字` / `zero_gamma_level || 數字` 這種「欄位整個缺失時的保底預設值」，同一個欄位（例如 `put_wall_strike`）在不同函式裡寫死的保底數字互不相同（`44500`/`45500`/`44800`/`46100` 都出現過）——這些只有在 `gexData` 完全沒有該欄位時才會觸發（正常情況下後端一定會算出這些值），實務上幾乎不會被觸發，但嚴格來說跟正確版本比對「保底不一致」本身就說明是隨手抄當天螢幕數字寫死，不是有意義的預設。範圍大（17處分散在不同函式）、風險低，先記錄，之後有空一次性清乾淨（建議做法：改成 `|| null`，並讓下游改用「—」顯示取代直接 `.toLocaleString()`，需要逐一確認每個呼叫點不會因為 null 而壞掉）。

---

## 二、尋鳥戰情交易室（trading room/room.js, room.html）

### 🔴 Critical — 假數據冒充真實數據

| # | 位置 | 問題 | 狀態 |
|---|---|---|---|
| 1 | room.js:702-734（`大戶散戶動能`副圖） | 「大戶動能柱/線」是拿 K 棒開高低收公式湊出來的（`flowVal = ((收盤-開盤)/振幅) × 量 × 0.4`），「散戶反向線」是 `-大戶線 × 0.65`，跟法人未平倉毫無關係。真數據 `momentum_data.json` 有抓回來（room.js:15,193）但完全沒用上。 | 🔧 **修復中**（另一 session 在建富邦 Books/Trades 即時串接，這裡先不動） |
| 2 | room.js:2929-3020（選股雷達） | 每檔股票的訊號標籤（🚀強火箭/⭐5K突破/9★轉折等）跟漲跌幅%，全部是拿**股票代號字元的雜湊值**算出來的固定布林值，跟今天盤勢無關，永遠不變。真數據 `screener_cache.json` 有抓回來（room.js:3311,3325）但完全沒用上；而且 `screener_cache.json` 本身底層也是假的（見上方「一、」# 2）。 | ❌ 待修 |
| 3 | room.js:1507-1553（`renderLeftPanel()`） | 切到 TXF/TAIEX/OTC 時，開高低收、昨收、漲跌點數/幅度是**無條件寫死的固定文字**，永遠不變，沒有任何即時流覆蓋它們。 | ❌ 待修 |
| 4 | room.js:816-828（ADX Pro V3 背離判定） | 頂/底背離用**寫死絕對價位**（`highs[i]>=47200`/`lows[i]<=46150`）加註解裡寫死的特定歷史日期觸發，不是通用的價格/指標背離演算法，價格永久脫離這個區間後就永久失效。 | ❌ 待修（需 `adx_dual_color_v3.pine` 校正到 1:1） |

### 🟠 High

| # | 位置 | 問題 |
|---|---|---|
| 5 | room.js:1113,1126-1128 | ADX Pro V3 副圖 MTF 看板文字是凍結假字串（`15M:21.1 1H:29.9...`），門檻參考線（26.65/22.37/11.63）跟同段程式碼實際算 ADX 用的門檻（20/30/50/75）對不起來，像是把某天螢幕上剛好出現的數值誤當成標準門檻寫死。 |
| 6 | `scripts/tv_indicators_engine.py` | 文件（ARCH_PLAN.md/AGENTS.md/GEMINI.md）宣稱是「後端保密運算層」，但全庫搜尋**從未被任何程式呼叫**，是孤兒死代碼，Roadmap 打勾「已完成 1:1 對接」不實。 |
| 7 | 全部指標公式 | SMA/EMA/雙層MACD/CCI/AO/ADX/TD Sequential 全部寫在公開的 `room.js` 裡，view-source 可看到完整算法與參數（IP 曝露問題，見下方「三、」）。 |

### 🟡 Medium

| # | 位置 | 問題 |
|---|---|---|
| 8 | room.js:683-699（CVD） | 用開高低收估算的近似 CVD（`barDelta = 量×(收-開)/振幅×0.4`），是業界常見近似手法，但沒有標註「估算值」，容易誤以為是真實逐筆內外盤數據。 |
| 9 | 股號搜尋 vs K線快取 | 宣稱 2,400+ 檔可搜尋，但只有 8 大核心商品有真實 K 線快取（`klines_cache.json`）。切到快取外個股會顯示「橫盤不動」的誠實假K棒（沒有亂數波動，這點是對的），但「可查」≠「有真走勢圖」，容易誤導。 |

### ✅ 已查核沒問題

- GEX 主圖疊加層（`drawGexHorizontalRays`）：即時讀真實 `gexData` 動態算，邏輯正確。
- AI 軍師：有 Key 真呼叫 Gemini API；沒 Key/失敗時清楚標示「本地內建風控引擎」，沒偽裝成真 AI。
- 指標庫/選股雷達 Modal 按鈕事件監聽有正確綁定。
- K 線資料：8 大核心商品走真實多週期快取，全庫 `Math.random` 零命中。

### ⏳ 尚未稽核

- **`room.html` / `room.css` 版面與 UI 稽核**——目前只 spot-check 過事件監聽有沒有綁對（結論：有綁對），**完全沒有實際開瀏覽器跑過畫面**。需要驗證：
  - ARCH_PLAN 提過的「頂部與左側 GEX 點位重複」是否真的移除了。
  - 左右抽屜收合（Alt+1/Alt+2）是否真的沒有滾動條、100% 縮放下版面是否跑版。
  - 手機版（390px 寬）有沒有橫向溢出。
  - 建議用 Playwright/瀏覽器實際開頁面截圖比對，不要只看程式碼判斷「應該沒問題」。

---

## 三之一、選股雷達要「真的能用」需要的資料管線（大工程，需獨立排時程）

現況（見上方「二、」#2）：`screener_cache.json` 是「當日真實收盤價 + `random.Random()` 生出來的假30根K棒歷史」算出來的假訊號。使用者要的選股雷達，是「掃出我自己寫的真實指標（Ghost Claws / JJ MACD / JJ CCI / 5K戰法 / 神奇九轉）目前訊號有出現的個股」，這需要：

1. **真實歷史 K 線資料**：全市場 1,400+ 檔個股的真實日線/分線歷史（不是假隨機生成），可能來源：TWSE 官方歷史 API、Yahoo Finance 歷史資料等——需要評估抓取 1,400+ 檔的時間成本與 API 限流問題。
2. **把 JJ MACD / JJ CCI / Ghost Claws / 5K戰法 / DeMark 的 Python 版本，套用在每一檔股票的真實歷史資料上**，算出「今天訊號有沒有出現」。
3. 效能考量：1,400+ 檔 × 多個指標，全部重算可能會很慢，需要考慮快取策略（例如只在盤後跑一次，存成 `screener_cache.json`，跟現在的架構一樣，只是內容從假的換成真的）。

**這是本次稽核清單裡工程量最大的一項，建議獨立排時程處理，不要跟其他「校正既有指標參數」的小修小補混在一起估工時。**

---

## 三之二、JJ 鬼爪 V4.1 與 5K戰法 v5 —— 從零建置（工程量比「校正」大很多）

跟「JJ_MACD_Sub / JJ_CCI_Sub / ADX Pro V3」這種「room.js 已經有一版實作、只是要對照真源碼校正參數」不同，以下兩支目前是**完全零實作**，需要從你的 `.pine` 源碼重新設計、重新刻一份 JS/Python 版本，不是小修：

- **JJ 鬼爪 V4.1**（`JJ 指標復刻優化/ghost_claws_v4.1.pine`，450行）
- **5K戰法 v5**（`5K戰法/5K_Strategy_Master_v5.pine`，779行）

這兩支源碼行數都不小，建議跟「三之一」的選股雷達真實化一起排在同一個大工程階段，因為兩者都要重新設計（不是校正），值得跟其他小修小補分開估時間，避免被塞在同一批「順手改一改」的工作裡拖慢進度。

---

## 三、指標源碼對照校正（需要真實 .pine / 使用者確認）

使用者已提供真實指標源碼於私有 repo `bluebirdfinder/TradingView-Indicators`（已 `add_repo` 讀取過）。以下是使用者確認過「交易室現階段實際使用」的 15 項指標，需要逐一跟 `room.js` 現況核對：

| 指標 | 對應源碼 | 現況 |
|---|---|---|
| JJ 鬼爪 V4.1 | `JJ 指標復刻優化/ghost_claws_v4.1.pine` | ❌ room.js 完全沒有對應程式碼，需要新增 |
| JJ_MACD_Sub | `JJ 指標復刻優化/JJ_MACD_Sub.pine`（不是 `JJ Indicators/` 舊版） | 需逐行核對現有雙層 MACD 實作 |
| JJ_CCI_Sub | `JJ 指標復刻優化/JJ_CCI_Sub.pine` | 需逐行核對現有 CCI(20) 實作 |
| bluebird_finder_GEX_VIX.pine | `GEX_VIX 指標/bluebird_finder_GEX_VIX.pine`（含VIX完整版，不是陽春版） | room.js 目前只畫 5 條線，VIX 相關疊加還沒做 |
| 5K戰法 v5 | `5K戰法/5K_Strategy_Master_v5.pine` | ❌ 完全沒實作，選股雷達裡的「⭐5K突破」只是雜湊碼假標籤，不是真邏輯 |
| 神奇九轉 V3（通用版，交易室要顯示這版） | `神奇九轉/demark_sequential_v3.pine` | 現有 TD Sequential 簡化實作需比對這份源碼校正 |
| 神奇九轉 V4_Idx-Alert（僅背景警報，不上圖） | `神奇九轉/demark_sequential_v4_indices_alert.pine` | 需確認是否要接 webhook/警報邏輯 |
| VWAP / VRVP / SMMA200 / AO / CVD（TV 公開指標） | 無專屬 .pine（公開指標） | 已實作，SMMA/AO 已核對無誤，CVD 為近似值見上方 #8 |
| SAR（TV 公開指標） | 無專屬 .pine | ❌ room.js 檔頭註解宣稱有實作（`+ Supertrend + SAR`），但**全檔案零實作**，註解本身是假的 |
| 成交量 + 雙均量線 | 無專屬 .pine | ✅ 已正確合併成一條量能圖+2條MA，跟使用者需求一致 |
| Smart Money Concept | `合併公開指標/Merged_Indicators.md` | ❌ room.js 完全沒有對應程式碼，需要新增 |
| ADX Pro V3 | `老墨 XQ 指標/TradingView Indicators/ADX Dual Color/adx_dual_color_v3.pine` | 需要用這份源碼修正上方 #4、#5 的寫死背離/門檻問題 |
| Smart Mansfield RS | `老墨 XQ 指標/TradingView Indicators/Smart Mansfield RS/Smart_Mansfield_RS_v1.pine` | ❌ 完全沒實作，需要新增 |

**授權注意**：`mophyfei/MOFI_XQ`（老墨 XQ 腳本庫）是「保留所有權利、僅供個人學習」的授權，`.xsb` 是二進位不可讀。可以參考它 README 描述的**概念/方法論**（公開統計方法）重新用自己的真實數據實作，但不能反編譯或照抄。

---

## 四、大戶散戶動能指標——正確方法論（陳玠儒/股市擺渡人版本，已確認來源）

使用者最終確認的正確設計（YouTube《股市更生人 特別篇 第四篇》）：

1. **大戶委託口差（紅柱）**：期貨**掛單**（委託簿/五檔深度）的大額買賣委託口數差——需要 Books 頻道即時委託簿深度資料。
2. **散戶成交筆數差（綠柱）**：算「成交筆數」的買賣差，不是口數差——需要逐筆成交 tick 資料，且要能分辨每筆口數大小（用來分大單/小單）。
3. **市場委買委賣口差（黃線）**：全市場委託簿買賣淨口差——同樣需要委託簿深度資料。
4. 建議週期：**30分鐘線**（不建議日線，因台指期日內換手率過高）。
5. 交易判讀四象限：大戶多+散戶空＝做多；大戶空+散戶多＝做空；兩者同向＝觀望盤整。
6. 適用標的：**TXF（台指期）+ 個股期貨**（使用者已確認範圍，個股期貨限定成交量前10-20大避免失真）。

**資料可行性（本次 session 已確認）**：
- 富邦新一代 API 期貨 WebSocket 有獨立 `books` 頻道（五檔委買委賣），schema 已透過官方文件確認：
  ```json
  {"event":"data","channel":"books","id":"...",
   "data":{"symbol","type","exchange","time",
           "bids":[{"price","size"}...5檔],
           "asks":[{"price","size"}...5檔],
           "derivedBid":{"price","size"},
           "derivedAsk":{"price","size"},
           "isTrial":bool}}
  ```
- `scripts/fubon_api_provider.py` 已新增 `start_books_stream()`/`get_book()`，`scripts/live_price_server.py` 已接上 `fubon_books_worker()` 與 `GET /api/books`。
- 訂閱 symbol 改用官方連續月別名 `"TXF1!"`，取代原本自己猜前月合約的 `_detect_txf_symbol()`。

**使用者已確認要加（個股適用，跟上面的期貨大戶散戶動能是不同資料源，不衝突）**：
- **分點力度**（籌碼集中度）：看一檔股票今天的買賣，是集中在少數幾個券商分點、還是分散在很多分點。集中＝可能有主力/大戶用固定幾家券商在偷偷佈局；分散＝比較像很多散戶各自進場。資料源是證交所分點/券商進出資料，只適用**個股**（不適用 TXF 期貨），應規劃成切到個股畫面時的獨立籌碼副圖。老墨的 `分點力度.xsb` 概念可參考（README 已讀過），但 `.xsb` 是二進位、且授權為個人學習用，不可反編譯/照抄，需用真實證交所資料自行實作同樣的概念。

**這個聊天室正在做、還沒做完的部分**（新 session 不用管，等這裡完成再接手）：
- `trades` 頻道訂閱（用於「散戶成交筆數差」，需要逐筆成交 + 口數分類）
- 30分鐘線聚合邏輯
- 把 `room.js` 的假動能公式換成串接上面這些真數據
- 個股期貨（前10-20大熱門標的）範圍的 Books/Trades 訂閱擴充

---

## 五、建議的下一步優先順序

1. **`app.js` 全文比照 `room.js` 方式稽核**（目前完全沒做過，且已證實同一種「抓真數據卻不用」的 bug 在這個專案重複出現 3 次，`app.js` 很可能也中鏢）。
2. **`scripts/fetch_and_calc_vision.py`** 逐函式核對（GEX 主引擎，優先度最高的核心程式）。
3. 修復尋鳥戰情室的 3 個 Critical bug（假 OHLC 面板 #3、選股雷達雜湊碼 #2、ADX 背離寫死 #4）——這三個不需要等大戶散戶動能完工，可以並行處理。
4. 指標源碼逐一校正（第三節表格：JJ_MACD/JJ_CCI/ADX Pro V3/GEX_VIX/神奇九轉），以及新增 SAR、Smart Money Concept、Smart Mansfield RS 這 3 支目前零實作的小型指標。
5. `room.html`/`room.css` 版面與 UI 實測（開瀏覽器驗證，不要只看程式碼）。
6. **選股雷達真實化**（三之一）與 **JJ鬼爪/5K戰法從零建置**（三之二）——工程量最大，獨立排時程，不要跟其他小修混在一起估工時。
7. 指標邏輯搬遷到後端（`tv_indicators_engine.py` 重新啟用、串接前端），解決 IP 曝露問題。
