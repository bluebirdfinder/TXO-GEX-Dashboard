# 📈 TAIFEX TXO GEX 動態儀表板 (TAIFEX TXO Options GEX & Stock Futures Dashboard v4.0.0)

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)
![Plotly](https://img.shields.io/badge/Plotly.js-2.27.0-orange.svg)
![Security](https://img.shields.io/badge/AES--256-Encrypted-red.svg)
![Status](https://img.shields.io/badge/Version-v4.0.0--Live-brightgreen.svg)

> **台指選擇權 Gamma Exposure (GEX) 波動度量化分析與 4 大類股票期貨籌碼儀表板**  
> 全面採用**台灣股市標準配色（🔴 紅漲 / 🟢 綠跌）**，提供台指選擇權 Delta/Gamma 對沖曝光分析、零 Gamma 轉折點計算、三大法人籌碼矩陣與期交所全量 270 檔個股/ETF 期貨動態篩選器。

---

## 🌟 核心特色 (Key Features)

### 1. 🇹🇼 台灣股市紅漲綠跌色彩與動態 GEX 柱状圖 (Taiwan Standard GEX Profile)
- **台灣習慣紅漲綠跌配色**：
  - 🔴 **亮紅色柱 (Red)**：Call GEX（買權對沖牆 / 多頭上漲標示）
  - 🟢 **翡翠綠柱 (Green)**：Put GEX（賣權對沖牆 / 空頭下跌標示）
  - 🔷 **青藍色軌跡線**：Net GEX 淨曝光分布
- **動態點位對齊**：自動抓取最新加權現價 (~43,120)，並圍繞現價動態鋪設 $\pm 750$ 點履約價網格。
- **關鍵指標標註**：現價 Spot 虛線、Zero Gamma (波動度轉折點) 點線、Call Wall (天花板) 與 Put Wall (地板)。
- **三種到期切換**：全市場 Total GEX、近到期週選 (W1/W2/W4/W5) GEX、當月月選 GEX。

### 2. 💎 期交所全量 270 檔股票與 ETF 期貨篩選器 (Full 270 TAIFEX Contracts Screener)
- **4 大契約類別獨立劃分**：
  1. 🏢 **個股期貨** (標準 2,000 股/口，如台積電期 `2330`)
  2. 🔹 **小型個股期貨** (小型 100 股/口，如小型台積電期 `2330F`)
  3. 📈 **ETF 期貨** (標準 10,000 份/口，如 `0050`、`0056`、`00878`)
  4. 🔸 **小型 ETF 期貨** (小型 1,000 份/口，如小型台灣50期 `0050F`)
- **多欄位升降冪排序 (Column Sorting)**：點擊表頭標題（代號、現價、漲跌幅 %、成交量、外資買賣超、自營商買賣超）即刻動態排序。
- **標準質感深灰捲軸與固定表頭**：表格配置流暢滾動捲軸與 Top 0 黏性固定表頭 (Sticky Header)。
- **夜盤與關鍵字過濾**：`☑ 僅顯示有夜盤標的` 與 `🔍 關鍵字搜尋框`。
- **台灣色彩多空趨勢標籤**：標示 🔴 `▲ Bull` (多頭翻多) 與 🟢 `▼ Bear` (空頭偏空) 狀態。

### 3. 📉 散戶多空比與三大法人動向矩陣
- **微台與小台散戶多空比**：追蹤散戶未平倉部位，作為反向市場指標。
- **三大法人動態矩陣**：彙整前五大/前十大交易人期貨、外資期貨淨口數（🔴 多單加碼）、自營商選擇權組合與結算 OP 方向預估。

### 4. 🔒 隱私與安全性 (Passcode Protection)
- **AES-256 端到端本機解密**：數據全自動經過 AES-256 加密存儲。
- **原生顯示/隱藏密碼與嚴格防護**：支援 `👁️ 顯示密碼` 原生開關，絕不暴露出入口按鈕。

---

## 🏛️ 權威數據源 (Official Data Sources)

1. **台灣期交所 (TAIFEX) 官方 CSV/ODS 接口**：
   - 選擇權行情與未平倉：`https://www.taifex.com.tw/cht/3/optDailyMarketReport`
   - 官方 Delta / Gamma 矩陣：`https://www.taifex.com.tw/cht/3/optDailyDelta`
   - 三大法人期貨籌碼：`https://www.taifex.com.tw/cht/3/futDailyMarketReport`
   - 股票期貨官方總目錄 (ODS/CSV)：`https://www.taifex.com.tw/cht/2/stockLists`
2. **Yahoo Finance API & Cloudflare Worker 代理**：
   - 夜盤加權與微台/小台即時報價代理。

---

## 🧮 GEX 核心數學模型 (Mathematical Formula)

### Black-Scholes Gamma ($\Gamma$)：
$$\Gamma = \frac{N'(d_1)}{S \cdot \sigma \cdot \sqrt{T}}$$
其中 $d_1 = \frac{\ln(S/K) + (r + \frac{1}{2}\sigma^2)T}{\sigma \sqrt{T}}$

### TXO GEX 金額公式 (億 TWD)：
$$\text{Call GEX}_{K} = \frac{\text{Call OI}_{K} \times \Gamma_{K} \times S^2 \times 50}{10^8}$$
$$\text{Put GEX}_{K} = -\frac{\text{Put OI}_{K} \times \Gamma_{K} \times S^2 \times 50}{10^8}$$
$$\text{Net GEX}_{K} = \text{Call GEX}_{K} + \text{Put GEX}_{K}$$

* TXO 契約乘數：**50 TWD / 點**。

---

## 📁 專案架構 (Project Structure)

```text
txo-gex-dashboard/
├── index.html                 # 儀表板前端 HTML (270檔類別表單, Plotly 容器, Passcode 模組)
├── style.css                  # 深色主題 CSS 樣式 (深灰質感捲軸, 台灣紅漲綠跌色系)
├── app.js                     # 前端應用邏輯 (密碼解密, Plotly 繪圖, 270檔排序過濾, 代理連線)
├── OPTIONS_CHEATSHEET.md      # 選擇權口訣與 GEX 判讀速查表
├── STATUS.md                  # 專案版本與更新履歷 Log
├── README.md                  # 專案完整說明文件 (本檔案)
├── scripts/
│   └── fetch_and_calc.py      # TAIFEX 數據抓取, GEX 計算與 AES-256 加密腳本
├── data/
│   ├── gex_data.json          # 原始產出 JSON 數據檔 (包含 270 檔期交所契約)
│   └── encrypted_gex.json     # AES-256 加密封包
├── cloudflare/
│   └── worker.js              # Cloudflare Worker 免封鎖即時報價代理
└── .github/
    └── workflows/
        └── daily_update.yml   # 每日 15:15 TWD 自動運算與部署工作流
```

---

## 🚀 部署與使用說明 (Deployment)

1. 將本 Repository 複製或部署至 **GitHub Pages**。
2. 開啟網站輸入專屬通行碼（Passcode）解密儀表板。
3. 可點擊 `❓ 判讀教學` 檢視選擇權 BC/SC/BP/SP 口訣、多空紅綠色彩與 GEX 三招判讀。

---

## ⚖️ 免責與法律聲明 (Disclaimer)

本專案（包含圖表、GEX 計算數據與分析說明）僅供學術研究與衍生性商品數據可視化參考，非屬證券期貨投資顧問行為，亦不構成任何買賣投資建議。衍生性商品交易具高度風險，投資人應獨立思考、審慎評估，並自負投資風險與盈虧責任。
