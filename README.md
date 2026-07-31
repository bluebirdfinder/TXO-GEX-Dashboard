# 📈 TAIFEX TXO GEX 動態儀表板 v6.0.0 🚀
> **台指期權 Gamma Exposure 波動度、三大法人與大戶 5 日純數字籌碼歷程矩陣、全量 270 檔個股期貨量化分析系統**

![Version](https://img.shields.io/badge/version-6.0.0-blue.svg)
![Data Source](https://img.shields.io/badge/Data%20Source-TAIFEX%20%7C%20TWSE-red.svg)
![Security](https://img.shields.io/badge/Protection-AES--256--CBC-green.svg)
![Color Standard](https://img.shields.io/badge/Color-Taiwan%20Standard%20(Red%3DRise%2C%20Green%3DFall)-brightgreen.svg)

---

## 💡 系統核心特色 (Key Features)

### 1. 🏛️ 100% 證交所與期交所官方數據直連 (100% Official Data)
* **官方權威來源**：直接串接 **台灣證券交易所 Open Data (`openapi.twse.com.tw`)** 與 **台灣期交所 (`www.taifex.com.tw`)** 每日盤後權威報告。
* **零虛假數據**：現價、漲跌幅 %、成交口數、三大法人買賣超、大戶與特定法人未平倉量 100% 來自官方，絕無隨機編造。

### 2. 📋 三大法人與大戶 5 日純數字籌碼歷程矩陣 (5-Day Numerical History Matrix)
* **期貨未平倉動向表**：追蹤前五大、前十大、前五特法、前十特法、外資、投信、自營商連續 5 日精確淨口數（如 `+6,420 口 🔴` / `-14,200 口 🟢`）。
* **現貨與選擇權全景表**：涵蓋三大法人現貨買賣超金額（外資/投信/自營金額）與選擇權 Buy Call / Buy Put 淨金額，全面杜絕文字混淆與紅字誤導。
* **💡 表格外獨立解讀卡 (Executive Digest Card)**：將 BC / SC / BP / SP 結構分析與結算展望獨立放置在表格上方，完全分離客觀數據表與文字解析。

### 3. 📊 4 大獨立 GEX 分布圖表切換 (4 Distinct GEX Datasets)
* 📊 **全市場 Total GEX**：全市場所有到期日對沖總合。
* ⚡ **週三結算選 (W1/W2/W4/W5)**：近到期週三結算週選分布圖。
* 🇺🇸 **週五結算選 (W1F/W2F/W4F/W5F)**：針對美國 CPI/NFP 事件發行的週五結算選分布圖。
* 🏛️ **當月月選 GEX**：當月月選大合約分布圖。

### 4. 📡 TradingView 實時報價整合（加權 IX0001 / 櫃買 IX0043 / 台指期夜盤 TXF1!）
* **頂部三獨立實時卡片**：加權指數 (`IX0001`)、櫃買指數 (`IX0043`) 與台指期夜盤 (`TXF1!`)。
* **每 3 秒連線跳動**：夜盤時間台指期近一 (`TXF1!`) 價格實時跳動，黑修斯 Gamma ($\Gamma$) 與 GEX 柱狀圖即時動態重算！

### 5. 💎 期交所全量 270 檔個股與 ETF 期貨篩選器 (270 Stock Futures)
* **完整涵蓋 4 大類別**：個股期貨 (標準 2000股)、小型個股期貨 (100股)、ETF 期貨 (10000份)、小型 ETF 期貨 (1000份)。
* **多維度篩選排序**：支援代號/名稱關鍵字搜尋、契約類別下拉切換、**🌙 僅顯示有夜盤標的**選取，以及現價、漲跌幅、成交量、外資/自營淨部位即點即排。

### 6. 👁️ 減輕視覺疲勞配色 (Comfortable Typography & Color Dots)
* **質感灰白標準字**：表格內文全部採用質感灰白標準字（`#e6edf3`）。
* **點綴色點**：僅在數字後方點綴小巧的 **🔴 買超/多單** 或 **🟢 賣超/空單** 圓點，視覺極致舒服不疲勞。

---

## 📂 專案檔案結構 (Project Structure)

```text
txo-gex-dashboard/
├── index.html                 # 主頁面 HTML5（含 5日純數字矩陣、獨立解讀卡、TV實時卡片）
├── style.css                  # CSS3 視覺系統（台灣紅綠配色、灰白舒適字體、深灰捲軸）
├── app.js                     # 前端邏輯（3秒報價連線、Plotly圖表動態重算、解密模組）
├── taifex_catalog.json        # 期交所官方 270 檔個股/ETF 期貨完整目錄
├── README.md                  # 本系統說明文件 v6.0.0
├── STATUS.md                  # 專案進度與里程碑紀錄
├── OPTIONS_CHEATSHEET.md      # 選擇權與 GEX 觀念速查口訣表
├── data/
│   ├── gex_data.json          # 明碼測試數據 JSON
│   └── encrypted_gex.json    # AES-256 加密正式數據 JSON
└── scripts/
    └── fetch_and_calc.py      # Python 數據引擎（直連 TWSE & TAIFEX 官方 API）
```

---

## 🔒 解密通行碼 (Passcode)

網頁開啟時需輸入加密通行碼進行端到端解密：
* **通行碼 (Passcode)**：`GEX2026`（大小寫皆可）

---

## ⚖️ 免責與法律聲明 (Disclaimer)

本網站及內部數據、圖表僅供學術研究與衍生性商品數據可視化參考，非屬證券期貨投資顧問行為，亦不構成任何投資建議。投資人應獨立思考、審慎評估，並自負投資風險與盈虧責任。
