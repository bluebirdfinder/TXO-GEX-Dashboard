# 🏛️ 期交所 TXO GEX Dashboard - 完整優化功能與官方數據網址交接手冊 (v37.0 Rewrite Spec)

> **本手冊適用對象**：個人筆電續接開發者 / AI 助理。
> **目的**：完整記載本日研討之所有前端面板 UI 架構、後端數據計算引擎邏輯、台灣股市紅漲綠跌規範，以及期交所/證交所權威資料來源 URL。

---

## 📌 一、 期交所 & 證交所 官方數據網址分類庫 (Official Data Source URLs)

### 🔴 A類：核心必備 (直接決定 GEX、籌碼與日夜盤數據)

1. **選擇權每日交易行情 (GEX、Call/Put Wall、Max Pain、OI 唯一權威來源)**
   * **URL**: `https://www.taifex.com.tw/cht/3/optDailyMarketReport`
   * **用途**: 計算全履約價 Call/Put 之成交量、未沖銷 (OI)、日盤/夜盤結算價。

2. **夜盤三大法人交易行情 (夜盤籌碼動向)**
   * **URL**: `https://www.taifex.com.tw/cht/3/futContractsDateAh`
   * **用途**: 每日 07:00 盤後定案，抓取外資與自營商在夜盤的大台 (TX)、小台 (MTX)、微台 (Micro) 淨買賣口數與金額。

3. **日盤三大法人期貨未平倉量 (日盤期貨籌碼)**
   * **URL**: `https://www.taifex.com.tw/cht/3/futContractsDateExcel`
   * **用途**: 每日 15:00 抓取外資 (如 `-85,179` 口)、投信、自營商之大台/小台未平倉部位。

4. **三大法人選擇權買賣權交易未平倉 (選擇權金額與金額比)**
   * **URL**: `https://www.taifex.com.tw/cht/3/callsAndPutsDateExcel`
   * **用途**: 抓取三大法人 Call/Put 契約金額 (億 TWD) 與買賣淨額。

5. **期貨大戶與特定法人未平倉部位 (大戶動向)**
   * **URL**: `https://www.taifex.com.tw/cht/3/largeTraderFutQry`
   * **用途**: 抓取前五大、前十大特定法人大戶之台指期淨部位。

6. **證交所三大法人買賣金額 (現貨籌碼)**
   * **URL**: `https://www.twse.com.tw/rwd/zh/marginTrading/BFI82U`
   * **用途**: 每日 15:30 抓取外資買賣超現貨金額 (億 TWD)、投信與自營商賣超金額。

7. **證交所 MIS 實時加權與櫃買指數 (Spot & OTC Price)**
   * **URL**: `https://mis.twse.com.tw/stock/api/getMarketInfo.jsp`
   * **用途**: 取得加權指數 (`IX0001`) 與櫃買指數 (`IX0043`) 當日收盤價。

8. **證交所全量個股盤後行情 (期現價差 Basis 計算)**
   * **URL**: `https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL`
   * **用途**: 取得 1,300+ 檔台股現貨收盤價，計算個股期貨與現貨之「期現價差 (Basis)」。

9. **證交所除權息預告表 API (TWT49U / TWT48U)**
   * **URL**: `https://www.twse.com.tw/rwd/zh/exRight/TWT49U?response=json`
   * **用途**: 抓取台股即將除權息日期、現金股利與配股股數，過期事件自動清除標註，僅對未來/當日事件進行預警。

10. **Yahoo Finance 國際熱錢即時 API (外匯動向)**
    * **USD/TWD (美金/台幣)**: `https://query1.finance.yahoo.com/v8/finance/chart/USDTWD=X`
    * **DXY (美元指數)**: `https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB`
    * **USD/JPY (美元/日圓)**: `https://query1.finance.yahoo.com/v8/finance/chart/JPY=X`

---

## 🎨 二、 前端面板視覺架構與紅漲綠跌規範 (UI Layout Spec v37.0)

### 1. 台灣股市色彩規範 (CRITICAL)
* **看漲 / 多頭 / Call GEX / Call Wall (天花板)** ➔ **🔴 紅色 (`#ff5252`)**
* **看跌 / 空頭 / Put GEX / Put Wall (地板)** ➔ **🟢 綠色 (`#00e676`)**
* **Zero Gamma (轉折點)** ➔ **🟡 黃色虛線 (`#ffd700`)**
* **Max Pain (最大痛點)** ➔ **紫羅蘭色 (`#a855f7`)**

---

### 2. v37.0 最新介面強化

1. **5 大結算天期動態到期日標註 (DTE Expiration Annotations)**:
   - 直方圖圖例自動標註各合約精確結算日期（如 `🟨 近週選 W1 (08/19三結算)`）。
2. **Net GEX 淨動態曲線與「🔀 疊加對比」模式**:
   - 繪製高對比白藍平滑曲線跨越履約價，跨越 Zero Gamma (45,820.2) 點位。
   - `Zero Gamma` (`y: 1.14`) 與 `Put Wall / Call Wall` (`y: 1.02`) 階梯式錯開，解決水平標籤重疊。
   - 按下 `🔀 疊加對比` 即可顯示黃色對照盤別 (T-1日盤/夜盤) 差異對比線與高亮動態按鈕。
3. **三大法人選擇權 Call / Put 買賣超金額獨立雙行拆解**:
   - 復刻經典雙行排版，同時顯示外資、投信、自營商選擇權的 `Call` 與 `Put` 獨立買賣超金額與 `🔴/🟢` 多空燈號。
4. **Gemini AI 4 大焦點掃描**:
   - 包含大盤判讀、莊家牆結算磁吸、Top 10 法人籌碼聚焦個股期與 TWSE 官方除權息扣點校正。
5. **TWSE 除權息動態預警與過期自動隱藏**:
   - 過期除權息事件自動隱藏，僅標註未來的即將/當日除權息事件。
   - 區分「除息 (現金)」、「除權 (配股)」與「除權息 (同天)」。

---

## 🛠️ 三、 本機離線雙擊開啟機制 (`file:///` Protocol CORS)

在 Chrome/Edge 本機直接雙擊開啟 `index.html` 時，瀏覽器安全政策會阻擋 Fetch API 讀取本地 `data/gex_data.json`。

### 解決方案
在 `data/embedded_data.js` 中定義全局變數：
```javascript
window.GEX_EMBEDDED_DATA = { ... gex payload ... };
```
在 `index.html` 中於 `app.js` 之前引用：
```html
<script src="data/embedded_data.js"></script>
<script src="app.js"></script>
```
在 `app.js` 的 `getFallbackData()` 中優先回傳 `window.GEX_EMBEDDED_DATA`，實現**線上/離線 100% 秒開**！

---

## 🔒 四、 通行碼加密機制 (Passcode Protection)

* 預設解密通行碼：`GEX2026`（不分大小寫）
* 提供原生 `👁️ / 🙈` 顯示/隱藏密碼切換與 Session 記錄。
* 採 CryptoJS AES 方式解密 `data/encrypted_gex.json`。

---

## 🚀 五、 個人筆電續接執行步驟

1. 拉取最新代碼：
   ```bash
   git clone https://github.com/bluebirdfinder/TXO-GEX-Dashboard.git
   cd TXO-GEX-Dashboard
   ```
2. 執行 Python 數據引擎測試：
   ```bash
   python scripts/fetch_and_calc_vision.py
   python scratch/make_embedded_data_js.py
   ```
3. 盤中即時報價串接（富邦 API / SDK）：
   * 回到個人電腦後，可於本地運行富邦 SDK 接收即時 Tick 價格更新 `spot_price` 與 `txf_price` 並推播重算，無須額外消耗 API 額度。
