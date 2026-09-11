# 🤖 尋鳥 TXO GEX 量化系統 AI 助理最高風控鐵律與行為規範 (AGENTS.md)

本規範為 Antigravity AI 在本專案（TXO-GEX-Dashboard）提供開發、版本發布、交易診斷與策略建議時之 **最高強制性風控與開發鐵律**。所有 AI Agent 必須 100% 遵守，絕不可違背。

---

## 🚨 4 大不可踰越之開發與風控紅線 (Hard Redlines)

### 🔴 1. 嚴禁未重新編譯數據檔即發布新版本（杜絕「版本閃一下又跳回舊版」老問題）
- **原理**：網頁載入時首先渲染 `index.html` 的靜態標題，但隨後 `app.js` 中的 `updateFreshnessIndicator(data)` 會在解析 `data/gex_data.json` 或 `data/embedded_data.js` 時，**自動以 `data.engine_version` 動態覆寫標題與頁尾**。若僅修改 HTML/MD 文件而未同步重新編譯數據，網頁載入完成後會立刻被舊資料覆寫（呈現「閃一下新版又跳回舊版」）。
- **鐵律**：
  1. 升級版本號時，**優先使用一鍵工具**：`python scripts/bump_version.py <新版次>`；
  2. 或手動修改 `scripts/fetch_and_calc_vision.py` 的 `ENGINE_VERSION = "vX.Y"` 後，**必須立即執行 `python scripts/fetch_and_calc_vision.py`** 產出包含新版次的 `gex_data.json`、`encrypted_gex.json`、`embedded_data.js`；
  3. 必須同時確保 8 大關鍵位置版次 100% 一致：
     - `scripts/fetch_and_calc_vision.py` (`ENGINE_VERSION`)
     - `data/gex_data.json` (`engine_version`)
     - `data/embedded_data.js` (`engine_version`)
     - `index.html` (標題與 `?v=vX.Y`)
     - `README.md`
     - `HISTORY.md`
     - `STATUS.md`
     - `PROJECT_HANDOVER.md`

### 🔴 2. 嚴禁對週選 (W1/W2/W4/W5/F1) 垂直價差單建議「拆單 (Legging Out)」
- **原理**：週選擇權 (DTE < 1~3 天) 時間衰退與波動極度劇烈。將垂直價差單 (Vertical Spread) 拆開（例如先平倉賣腳 SP/SC、留買腳 BP/BC 裸露）會將**已鎖定的有限風險解鎖為無限/極大風險**，極易引發「多空雙巴 (Double Whiplash) 慘案」。
- **鐵律**：對所有週選價差單，**一律嚴禁建議拆單**！必須維持整組價差單平倉、轉倉或到期結算。

### 🔴 3. 嚴禁在價格暴衝/急殺時建議「追價 (Chasing Price)」
- **原理**：盤中 500~1,000 點暴衝或急殺往往伴隨隱含波動率 (IV) 飆升與做市商 Gamma 軋空/追殺。在暴衝高點追多或暴跌低點追空屬於高風險情緒性交易。
- **鐵律**：盤中暴衝時，**第一時間手動暫停逆勢洗價單**，嚴禁建議追價。必須等待 15M/30M K 線出現 DeMark (9★/13★) 買賣盤竭盡或均線走平過濾後，方可建立新部位。

### 🔴 4. 診斷持倉部位時，必須 100% 區分「真實真金白銀倉位」與「模擬範例」
- **原理**：使用者為實盤真金白銀交易。
- **鐵律**：進行部位審核時，必須同時檢查：
  1. 賣腳 (Sell Leg) 是否已被市場價格貫穿/進入價內 (ITM)；
  2. 當前未實現損益與市價對手價平倉成本；
  3. 最大獲利與最大可能虧損 (Reward/Risk) 風報比；
  4. 給出明確的 IOC 洗價條件數值，絕不給出空泛或死套公式的危險建議。

### 🔴 5. 嚴禁盤中交易時段讀取盤後 Excel 當作即時行情（杜絕台指期報價倒錯與 5 日矩陣正負號顛倒）
- **原理**：期交所日盤盤後結算 Excel (`futDailyMarketExcel?marketCode=0`) 在交易日 13:45 結算前，內容為**前一交易日之結算價**。若在 08:45 ~ 13:45 盤中直接讀取該 Excel，會將昨日價格誤當成今日價格，與昨夜盤相減後產生致命的正負號顛倒（例如大盤大跌 -800 點，台指期卻顯示暴漲 +800 點）。
- **鐵律**：
  1. **盤中即時行情一律強制走 MIS 串流端點**：`https://mis.taifex.com.tw/futures/api/getQuoteList`，即時抓取當月大台期貨合約 (`TXF...-F`)。
  2. **盤後 Excel 必須強制校驗日期標頭**：僅當 Excel 內嵌日期 == 今日日期 且 時間 >= 14:00 時，才允許作為今日日盤定案結算價；若日期為昨日，必須嚴格歸類為 `prev_day_tx`。
  3. **數據引擎必須執行「現貨與期貨方向性一致性校驗 (Sanity Check)」**：若加權指數下跌超過 200 點，台指期絕不可出現暴漲超過 300 點的倒錯反向數據，否則觸發自動熔斷校正。

---

## 📅 台灣台指選擇權 (TXO) 結算週期與代碼 100% 準確判讀規範

| 選擇權類型 | 結算日規律 | 券商 App / 系統簡稱 | 期交所官方對照代碼 |
| :--- | :--- | :--- | :--- |
| **週三選 (Weekly Wed)** | **每週三 13:30 結算** | `YYYYMMW1` / `W2` / `W4` / `W5` | `TX1` / `TX2` / `TX4` / `TX5` |
| **週五選 (Weekly Fri)** | **每週五 13:30 結算** | `YYYYMMF1` / `F2` / `F3` / `F4` / `F5` | `TXU` / `TXV` / `TXX` / `TXY` / `TXZ` |
| **月選擇權 (Monthly)** | **每月第 3 個週三結算** | `YYYYMM` (僅年月，無 W 或 F 後綴) | `TXO` |
