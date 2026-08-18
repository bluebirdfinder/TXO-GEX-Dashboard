# 🐦 尋鳥 Bluebird Finder — TXO GEX 量化系統與三大法人期權籌碼分析儀表板 (v39.0)

> **全台首創‧日夜盤雙維度對照‧GEX 圖直方圖手機版三階梯防遮擋標籤‧籌碼快訊手機版 2x2 雙欄卡片‧5日全欄位 session-to-session 增減差額標註‧散戶與國際熱錢對話式教學 Modal‧Net GEX 敏感度動態曲線‧TWSE 除權息預警**

[![GitHub Actions Night/Day Pipeline](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml/badge.svg)](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml)
[![Live Dashboard](https://img.shields.io/badge/Live-TXO_GEX_Dashboard-00d2ff?style=flat&logo=googlechrome)](https://bluebirdfinder.github.io/TXO-GEX-Dashboard/)
[![Engine Version](https://img.shields.io/badge/Engine-v39.0_Vision_Playwright-ffd700?style=flat&logo=python)](file:///scripts/fetch_and_calc_vision.py)
[![Compliance](https://img.shields.io/badge/Compliance-100%25_Academic_Regulatory-00e676?style=flat)](file:///OPTIONS_CHEATSHEET.md)

---

## 🌟 v39.0 核心升級與最新亮點 (Key Features)

### 1. 📱 GEX 直方圖手機版三階梯防遮擋標籤 (GEX Chart Staggered Badges)
- **三階梯垂直分層**：解決手機螢幕寬度較窄導致 Put Wall、Zero Gamma 與 Call Wall 標籤重疊覆蓋的問題，全面採用 `y: 1.02` (PW), `y: 1.14` (ZG), `y: 1.26` (CW) 3 階梯垂直高度分層。
- **手機端動態精簡**：手機介面自動切換精簡標籤 (`PW: 45750`, `ZG: 45920.5`, `CW: 46050`)，搭配上方留白擴大 (`margin.t: 95`)，實現 0 重疊、0 遮檔的頂級視覺體驗。

### 2. 📱 權威台指籌碼快訊與 VIX 觀測儀表手機版 2x2 矩陣化
- 將外資期貨/ Call / Put 未平倉與台指 VIX 等 4 大指標於手機版自動調整為緊湊的 2x2 雙欄卡片佈局 (`minmax(135px, 1fr)`)，大幅提升螢幕空間利用率。

### 3. 📱 全站手機版 Touch 原生流暢滾動與 Self-Audit 驗證
- 為所有歷史數據表格全面啟用 `-webkit-overflow-scrolling: touch` 原生慣性滑動，通過 Playwright 390x844 移動端實機 Playwright 渲染測試與 0 Console Errors 審計。

### 4. 📊 近 5 日關鍵市場指數與 GEX 結構歷程矩陣 — 全欄位（+）/（-）括號差額對照
- 現貨與衍生指標全數提供括號增減註記。現貨比較前一日日盤，期貨與 GEX 指標比較上一盤面 (Upstream Session)。

### 5. 💡 散戶多空比與三大法人籌碼診斷區 + 互動教學 Modal
- 新增 `ℹ️ 散戶多空比判讀教學` Modal。全站標註「期交所官方公開數據計算」，100% 合規。

### 6. 🌐 國際熱錢與三大外幣指標判讀教學 Modal
- 新增 `ℹ️ 匯率與熱錢指標教學` Modal，拆解 USD/TWD、DXY、USD/JPY 與台股資金連動機制。

---

## 🛡️ 開發與更新標準作業流程 (Standard Operating Procedure - SOP)

專案進行任何功能變更與發布前，嚴格執行 **7 大 SOP 防護關卡**：

1. **功能開發 (Development)**
2. **語法與 HTML `<div...</div>` 標籤閉合 Check-Syntax**
3. **數據雙重保險核對 (Data Audit Protocol)**：
   - 官網 API / Raw Data 匯入核對（期交所、證交所、Yahoo Finance）。
   - 網頁 Playwright 實體截圖數據與視覺呈現比對。
4. **Playwright 全站 Console Zero-Error & 7 大板塊 100% Population 審查**
5. **數據引擎與嵌入檔同步 (`fetch_and_calc_vision.py` & `make_embedded_data_js.py`)**
6. **專案文件同步 (`README.md`, `PROJECT_HANDOVER.md`, `STATUS.md`)**
7. **交付使用者 Commit & Push 至 GitHub**

---

## 🛠️ 系統架構與技術堆疊 (Tech Stack)

| 模組分工 | 使用技術 / 來源 API |
| :--- | :--- |
| **前端 UI 儀表板** | HTML5, Vanilla CSS3 (Sleek Dark Mode), Vanilla JavaScript (ES6+) |
| **圖表繪製引擎** | Plotly.js v2.27.0 (Relative Stacking Bar + Spline Scatter Plot) |
| **爬蟲與計算引擎** | Python 3.12, BeautifulSoup4, Playwright Stealth, CryptoJS |
| **即時行情數據源** | TWSE 臺灣證券交易所 (MIS / BFI82U / TWT49U), TAIFEX 期交所, Yahoo Finance API |
| **AI 摘要生成引擎** | Google Gemini 3.6 Vision / Gemini 2.5 Flash API |
| **自動化部署** | GitHub Actions (Cron 定時觸發日夜盤雙修剪流程) |

---

## 🚀 快速開始與本地執行 (Quick Start)

### 1. 安裝 Python 依賴環境
```bash
pip install urllib3 beautifulsoup4 pandas playwright requests
playwright install chromium
```

### 2. 執行數據抓取與 GEX 計算引擎
```bash
python scripts/fetch_and_calc_vision.py
```

### 3. 生成前端內建嵌入數據腳本
```bash
python scratch/make_embedded_data_js.py
```

### 4. 開啟網頁
雙擊開啟 `index.html` 或以 Live Server 執行即可。通行碼為 `GEX2026`（不分大小寫）。

---

## ⚖️ 免責與法律聲明 (Legal Disclaimer)

本網站（包含數據圖表、GEX 計算結果與 Gemini AI 分析說明）僅供學術研究與衍生性商品數據可視化參考，非屬證券期貨投資顧問行為，亦不構成任何買賣投資建議。衍生性商品交易具高度風險，投資人應獨立思考、審慎評估，並自負投資風險與盈虧責任。
