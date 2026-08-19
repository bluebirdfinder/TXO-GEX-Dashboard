# 🏛️ TXO GEX 儀表板 — 完整優化功能與官方數據來源交接手冊 (v44.0)

> **適用對象**：個人筆電續接開發者 / AI 助理
> **目的**：完整記載前端面板 UI 架構、T型報價雙方向渲染、3層即時報價網關、半透明品牌水印、後端數據計算邏輯、台灣股市色彩規範，以及期交所/證交所權威數據來源 URL。

---

## 📌 一、期交所 & 證交所 官方數據網址清單

### 🔴 A 類：核心必備（直接決定 GEX、籌碼與日夜盤數據）

| # | 用途 | 官方 URL |
|---|---|---|
| 1 | **選擇權每日交易行情**（GEX、Call/Put OI、Max Pain） | `https://www.taifex.com.tw/cht/3/optDailyMarketReport` |
| 2 | **夜盤三大法人期貨交易**（外資/自營商夜盤 TX/MTX/Micro 口數） | `https://www.taifex.com.tw/cht/3/futContractsDateAh` |
| 3 | **日盤三大法人期貨未平倉**（Excel 格式，15:00 定案） | `https://www.taifex.com.tw/cht/3/futContractsDateExcel` |
| 4 | **三大法人選擇權買賣超金額**（Call/Put 億 TWD） | `https://www.taifex.com.tw/cht/3/callsAndPutsDate` |
| 5 | **大戶與特定法人未平倉**（前五大/前十大近月全月） | `https://www.taifex.com.tw/cht/3/largeTraderFutQry` |
| 6 | **散戶期貨未平倉**（MTX/TMF 計算散戶多空比） | `https://www.taifex.com.tw/cht/3/futContractsDate` |
| 7 | **台指 VIX 波動率指數** | `https://www.taifex.com.tw/cht/7/vixMinNew` |
| 8 | **台指期/小台期 日盤收盤行情 Excel** | `https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=0` |
| 9 | **台指期/小台期 夜盤收盤行情 Excel** | `https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=1` |

### 🟡 B 類：證交所數據

| # | 用途 | 官方 URL |
|---|---|---|
| 10 | **三大法人現貨買賣超金額**（BFI82U，億 TWD） | `https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json` |
| 11 | **加權指數 & 櫃買指數即時報價**（MIS） | `https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw|otc_o00.tw` |
| 12 | **全量個股盤後行情**（1,300+ 檔，計算期現價差 Basis） | `https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL` |
| 13 | **除權息預告表**（TWT49U，計算未來除息事件） | `https://www.twse.com.tw/rwd/zh/exRight/TWT49U?response=json` |

### 🟢 C 類：國際行情

| # | 用途 | 官方 URL |
|---|---|---|
| 14 | **美元/台幣 (USD/TWD)** | `https://query1.finance.yahoo.com/v8/finance/chart/USDTWD=X?interval=1d&range=10d` |
| 15 | **美元指數 (DXY)** | `https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1d&range=10d` |
| 16 | **美元/日圓 (USD/JPY)** | `https://query1.finance.yahoo.com/v8/finance/chart/USDJPY=X?interval=1d&range=10d` |

---

## 🎨 二、前端面板視覺架構與台灣紅漲綠跌規範

### 台灣股市色彩規範（不可更改）

| 顏色 | 色碼 | 用途 |
|---|---|---|
| 🔴 紅色 | `#ff5252` (var(--call-color)) | 看漲 / 多頭 / Call GEX / Call Wall 天花板 |
| 🟢 綠色 | `#00e676` (var(--put-color)) | 看跌 / 空頭 / Put GEX / Put Wall 地板 |
| 🟡 黃色 | `#ffd700` (var(--gold-accent)) | Zero Gamma 虛線 / 關鍵標示 |
| 🟣 紫色 | `#a855f7` | Max Pain 最大痛點 |
| 🔵 藍色 | `#00d2ff` (var(--primary-accent)) | Put Wall / 夜盤元素 / 系統標題色 |

### v44.0 前端面板 DOM 結構與浮水印規範

| 面板 | DOM Class / ID | 浮水印規則 |
|---|---|---|
| 近5日關鍵矩陣 | `key-metrics-5day-panel` | `.watermark-panel` (右下角 `© 尋鳥 Bluebird Finder`) |
| 微觀結構速報 | `microstructure-express-panel` | `.watermark-panel` (右下角 `© 尋鳥 Bluebird Finder`) |
| 熱錢動向 | `hot-money-express-panel` | `.watermark-panel` (右下角 `© 尋鳥 Bluebird Finder`) |
| 散戶多空比 | `sentiment-panel` | `.watermark-panel` (右下角 `© 尋鳥 Bluebird Finder`) |
| 夜盤盤後專區 | `night-trading-panel` | `.watermark-panel` (右下角 `© 尋鳥 Bluebird Finder`) |
| 5日期權歷程矩陣 | `.watermark-panel` (主面板) | 解讀卡片、表格1下方、表格2下方分別具備獨立浮水印 |
| AI 量化掃描 | `ai-quant-digest-panel` | `.watermark-panel` (右下角 `© 尋鳥 Bluebird Finder`) |
| 個股期貨篩選器 | `stock-futures-panel` | `.watermark-panel` + `max-height: 690px` (Top 10 一頁呈現) |
| 全站 Footer | `<footer>` | 圓形頭像 + 權威免責 + `© 2026 尋鳥 Bluebird Finder` 版權 |

---

## 🛡️ 三、標準作業流程 SOP（每次更新必執行）

```
[步驟 1] 功能開發
[步驟 2] 語法檢查（div 標籤對稱、JS 括號閉合）
[步驟 3] 資料與視覺核對
         ├─ 重跑 fetch_and_calc_vision.py，確認 [OK] 輸出
         └─ 開啟網頁，核對 T型報價視角 (Call右/Put左) 與 經典豎軸 (820px) 雙軌防碰撞
[步驟 4] 手機版面驗證（390px 寬，無遮擋、無溢出）
[步驟 5] 更新 embedded_data.js
[步驟 6] 更新所有 .md 文件（中文為主，不得包含第三方品牌名稱）
[步驟 7] git commit & push
```

---

*最後更新：2026-08-20 最新穩定版 | 尋鳥 Bluebird Finder | v44.0*
