# 🔍 Self-Audit 發現清單與待辦事項 (2026-09-13 稽核)

本文件彙整對 **GEX 主儀表板**（`index.html`/`app.js`/`scripts/*.py`）與 **尋鳥戰情交易室**（`trading room/room.js`/`room.html`）的 self-audit 結果，目的是揪出 Gemini/antigravity 遺留的幻覺資料、寫死假數字，以及需要對照真實指標源碼校正的部分。

**範圍聲明**：這份清單是目前 audit 到的部分，**不是全部掃完**。凡標示「⏳ 尚未稽核」的區塊，代表還沒仔細看過，開新的對話室時應該先從那些區塊開始，而不是假設已經乾淨。

**正在另一個聊天室處理、這份清單不用管的項目**：
大戶散戶動能指標所需的富邦 Books/Trades 即時行情串接（`scripts/fubon_api_provider.py`、`scripts/live_price_server.py`）——這是目前另一個 session 正在做的事，等它做完再回頭把 `room.js` 的假動能公式換成真數據。

---

## 一、GEX 主儀表板（index.html / app.js / scripts）

### 🔴 已確認的假資料 / hallucination

| # | 位置 | 問題 |
|---|---|---|
| 1 | `scripts/fetch_institutional_momentum.py` | docstring 宣稱「Fetches real TAIFEX...」，但**整支程式沒有任何網路請求**，法人未平倉/散戶留倉/近5日籌碼歷程全部是寫死常數（`foreign_oi = -12450` 等），跟真實市況無關，每次執行都輸出一樣的數字。 |
| 2 | `scripts/build_screener_cache.py` | 只有「當日收盤價/漲跌/量」是真的（來自 `tw_quotes_latest.json`），但拿去算均線/乖離率/量比/MACD狀態/5K趨勢/DeMark訊號的**過去30根K棒歷史是 `random.Random(股票代號當種子)` 生出來的假歷史**（`generate_synthetic_ohlcv`），所以算出來的訊號全部不可信。 |

### ⏳ 尚未稽核（優先順序建議）

1. **`scripts/fetch_and_calc_vision.py`**（3312行，核心 Black-Scholes GEX/VEX 引擎）——只做過關鍵字掃描（有命中 `random`/`mock` 但沒逐一確認是死註解還是活邏輯），**這是最重要、也最大支，下個 session 應該從這裡開始**。
2. `scripts/fetch_real_quotes.py`——同樣只做過關鍵字掃描，未逐函式核對。
3. `scripts/fubon_api_provider.py` 裡 `get_live_quotes()` 的 gap period 假保底值（`txf_price = 47207.0` 等，約在原檔案第170行附近，行號可能因本次改動而偏移）——這是「無資料時的保底」還是「常態性覆蓋真數據」需要查清楚。
4. `scripts/live_price_server.py` 的 `LivePriceState.__init__` 裡同樣寫死了指數保底值（47207.0 / 24530.8 / 278.45）——同上，需確認何時會被觸發、觸發頻率。
5. `data/session_snapshots.json` 與 `scripts/backfill_snapshots.py` 的快照產生邏輯。
6. `scripts/generate_social_card.py` 是否真的 100% 吃 `gex_data.json`，還是有獨立寫死的展示數字。
7. `app.js`（3250行）——尚未比照 `room.js` 那樣逐段檢查是否有類似「`renderLeftPanel()` 式」的凍結假資料或「真數據抓回來卻沒用上」的模式。這是**最容易漏掉、也最該優先查的地方**，因為 `room.js` 已經抓到三次一模一樣的 bug 模式（`momentumData`、`screenerCacheData` 都是抓了真資料但忽略不用），`app.js` 很可能也有。

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

- `room.html` 版面結構（ARCH_PLAN 提過的「頂部與左側 GEX 點位重複」是否真的修好、左右抽屜收合是否真的沒有滾動條問題）——目前只 spot-check 過事件監聽，沒有實際跑瀏覽器驗證版面。
- `room.css`。

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
4. 指標源碼逐一校正（第三節表格），新增缺漏的 4 支指標（JJ鬼爪、SAR、Smart Money Concept、Smart Mansfield RS、5K戰法真邏輯）。
5. 指標邏輯搬遷到後端（`tv_indicators_engine.py` 重新啟用、串接前端），解決 IP 曝露問題。
