# 🐦 尋鳥 Bluebird Finder — TXO GEX 量化系統與三大法人期權籌碼分析儀表板 (v37.0)

> **全台首創‧日夜盤雙維度對照‧Playwright + Gemini 3.6 Vision 雙 Call 批次數據引擎‧Multi-DTE 到期日標註‧Net GEX 敏感度動態曲線‧TWSE 除權息預警‧國際熱錢動向儀表板**

[![GitHub Actions Night/Day Pipeline](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml/badge.svg)](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml)
[![Live Dashboard](https://img.shields.io/badge/Live-TXO_GEX_Dashboard-00d2ff?style=flat&logo=googlechrome)](https://bluebirdfinder.github.io/TXO-GEX-Dashboard/)
[![Engine Version](https://img.shields.io/badge/Engine-v37.0_Vision_Playwright-ffd700?style=flat&logo=python)](file:///scripts/fetch_and_calc_vision.py)
[![Compliance](https://img.shields.io/badge/Compliance-100%25_Academic_Regulatory-00e676?style=flat)](file:///OPTIONS_CHEATSHEET.md)

---

## 🌟 v37.0 核心升級與最新亮點 (Key Features)

### 1. 🎨 5 大結算天期動態到期日標註 (DTE Expiration Annotations)
- **精確動態結算日期**：直方圖圖例自動標註各合約精確到期日（如 `🟨 近週選 W1 (08/19三結算)`、`🟩 次週選 W2 (08/26三結算)`、`🟦 當月月選 M1 (09/16三結算)`、`🟪 雙週五選 (08/21五結算)`）。
- **Evan (LIETA.IO) 專業 5 色分層堆疊**：直觀呈現在當沖防守、波段鐵板與國際事件避險部位的籌碼分佈。

### 2. 📈 Net GEX 淨動態曲線與「🔀 疊加對比」模式
- **恆常 Net GEX 曲線 (Net GEX Profile Line)**：以白藍高對比平滑曲線 (`spline`) 跨越履約價，精確於 **Zero Gamma (45,820.2)** 點位穿過 0 軸，直觀展現多空轉折力道。
- **錯開三關價標籤 (Multi-tier Vertical Staggering)**：將 `Zero Gamma` 提升至頂層高位 (`y: 1.14`)，`Put Wall (45,650)` 與 `Call Wall (46,000)` 置於下層 (`y: 1.02`)，徹底解決水平標籤互相遮蔽問題。
- **🔀 疊加對比動態回饋**：點擊按鈕即刻開啟黃色對照盤別 (T-1日盤/夜盤) 差異對比線，並提供明顯的反白高亮視覺回饋。

### 3. 📊 三大法人選擇權 Call / Put 買賣超金額獨立雙行拆解
- 復刻經典雙行排版，獨立呈現外資、投信與自營商選擇權的 `Call` 與 `Put` 買賣超金額與 `🔴 (買超) / 🟢 (賣超)` 燈號，精確辨識法人偏多雙買或避險雙賣細節。

### 4. 🤖 Gemini AI 全市場籌碼、GEX 轉折與除權息事件 4 大焦點掃描
- **4 大項目結構化條列**：
  1. 🎯 **大盤 GEX 位階與假洗盤判讀**（45,841 現價位階 vs 45,500 轉折點）。
  2. 🧱 **週月選莊家牆與結算磁吸**（46,000 Call Wall vs 45,500 Put Wall vs 45,900 Magnet）。
  3. 🔥 **Top 10 法人籌碼聚焦標的**（外資/投信同步現貨買超 + 期貨淨多單雙重加碼股）。
  4. 📅 **近期除權息扣點校正與價差防守**（TWSE 官方除權息扣點防誤判）。
- 100% 遵守證券投資顧問法規，採用學理情境說明。

### 5. 📅 TWSE 官方除權息動態預警與 287 檔全涵蓋期貨
- **過期自動隱藏**：過期除權息事件自動清除標註；僅針對 **未來即將 / 當日除權息** 事件進行醒目預警。
- **精確區分類型**：自動區分「除息 (現金股利)」、「除權 (股票配股)」與「除權息 (同天進行)」。
- **全量 287 檔涵蓋**：包含小型商品（2330F 小型台積電期、0050F 小型元大台灣50ETF期）與夜盤可交易之 6 檔核心商品。

### 6. 🔒 隱密安全性密碼解鎖與自動初始化
- 隱密通行碼 **`GEX2026`**（不分大小寫），提供原生 `👁️ / 🙈` 顯示/隱藏密碼按鈕。
- 開啟網頁即自動初始化加載內建數據，絕不出現空白表格。

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
