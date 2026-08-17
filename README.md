# 🐦 尋鳥 Bluebird Finder — TXO GEX 量化系統與三大法人期權籌碼分析儀表板 (v38.0)

> **全台首創‧日夜盤雙維度對照‧Playwright + Gemini 3.6 Vision 雙 Call 批次數據引擎‧5日全欄位 session-to-session 增減差額標註‧散戶與國際熱錢對話式教學 Modal‧Net GEX 敏感度動態曲線‧TWSE 除權息預警**

[![GitHub Actions Night/Day Pipeline](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml/badge.svg)](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml)
[![Live Dashboard](https://img.shields.io/badge/Live-TXO_GEX_Dashboard-00d2ff?style=flat&logo=googlechrome)](https://bluebirdfinder.github.io/TXO-GEX-Dashboard/)
[![Engine Version](https://img.shields.io/badge/Engine-v38.0_Vision_Playwright-ffd700?style=flat&logo=python)](file:///scripts/fetch_and_calc_vision.py)
[![Compliance](https://img.shields.io/badge/Compliance-100%25_Academic_Regulatory-00e676?style=flat)](file:///OPTIONS_CHEATSHEET.md)

---

## 🌟 v38.0 核心升級與最新亮點 (Key Features)

### 1. 📊 近 5 日關鍵市場指數與 GEX 結構歷程矩陣 — 全欄位（+）/（-）括號差額對照
- **現貨 (加權 IX0001、櫃買 IX0043)**：**日盤列**與「前一日日盤」相比；**夜盤列**依期交所規範標示為 `-`。
- **期貨與 GEX 指標 (台指期 TXF, Zero Gamma, Call Wall, Put Wall, Max Pain, P/C Ratio)**：當前盤面與**「緊鄰的前一個盤面 (Upstream Session)」**相比（如 T夜盤 vs T日盤、T日盤 vs T-1夜盤、T-1夜盤 vs T-1日盤）。
- **醒目多空色彩**：正數為 `🔴 (加碼/上揚)`、負數為 `🟢 (減碼/下跌)`、零為灰色。

### 2. 💡 散戶多空比與三大法人籌碼診斷區 + 互動教學 Modal
- **`ℹ️ 散戶多空比判讀教學` 互動 Modal**：詳述小台 (MXF) / 微台 (TMF) 反向指標公式、歷史轉折臨界門檻（`> +15%` 易拉回、`< -15%` 易反彈）與台指 VIX 恐慌指標連動說明。
- **100% 法規合規**：移除所有券商特定名稱（如永豐期貨），全數標註「期交所官方公開數據計算」與學理量化說明，符合期貨法規。

### 3. 🌐 國際熱錢與三大外幣指標判讀教學 Modal
- **`ℹ️ 匯率與熱錢指標教學` 互動 Modal**：詳細拆解美元/台幣 (USD/TWD - 外資資金風向球)、美元指數 (DXY - 全球資金吸鐵石)、美元/日圓 (USD/JPY - 套利平倉 Carry Trade 風險) 對台股流動性的連動機制。

### 4. 📌 日夜盤微觀結構速報與動態校正列
- **日夜盤動態校正列 (Session Shift Banner)**：極速展示最新夜盤 vs 日盤價格漂移點數與最新 Zero Gamma 防守價位。
- **微觀結構速報 (Microstructure Express Digest)**：自動識別最新盤面屬於「正 Gamma 波動度抑制區」或「負 Gamma 波動度放大區」，並即時連動最新 Call Wall / Put Wall 調倉位移。

### 5. 📐 GEX 直方圖 X 軸標題與圖例區間距排版最佳化 (Plotly Layout Optimization)
- 優化 Plotly 圖表邊距與 `yanchor` 佈局，徹底解決「履約價 (Strike)」X 軸標題與底部圖例框 (Legend Box) 重疊的問題。

### 6. 🔒 核心 UTF-8 解密備援與全站 Self-Audit
- 採用 `TextDecoder('utf-8')` 完整支援多位元 UTF-8 表情符號 (Emojis)，徹底消除解密 `URIError`。
- 通過 Playwright 自動化 Self-Audit 檢測，確保無 Console 報錯與數據空缺。

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
