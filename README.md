# 🐦 尋鳥 Bluebird Finder - TXO GEX 量化儀表板 v8.0.0 🚀
> **台指期權 Gamma Exposure 波動度、三大法人與大戶 5 日純數字籌碼歷程矩陣、TradingView Pine Script v6 即時推播、全量 270 檔個股期貨量化系統**

![Branding](https://img.shields.io/badge/Branding-%E5%B0%8B%E9%B3%A5%20Bluebird%20Finder-00d2ff.svg)
![Version](https://img.shields.io/badge/version-8.0.0-blue.svg)
![Data Source](https://img.shields.io/badge/Data%20Source-TAIFEX%20%7C%20TWSE-red.svg)
![TradingView](https://img.shields.io/badge/TradingView-Pine%20Script%20v6-green.svg)
![Security](https://img.shields.io/badge/Protection-AES--256--CBC-green.svg)

---

## 💡 系統核心特色 (Key Features)

### 1. ⚡ TradingView Pine Script v6 零延遲報價自動推播
* **對接付費 TradingView 報價**：支援 Pine Script v6 自動推播告警，將你的 TradingView 付費實時台指期夜盤 (`TXF1!`) 價格推送至 Cloudflare Worker。
* **動態重算 GEX 避險牆**：夜盤時間一有新報價，網頁端的黑修斯 Gamma ($\Gamma$) 與 Plotly GEX 柱狀圖即時重算與繪製。

### 2. 🏛️ 100% 期交所官方 Excel 匯入數據 (Official TAIFEX Excel Integration)
* **官方網頁 Web 匯入專用接口**：直連期交所官方 `callsAndPutsDateExcel` 接口，精確解析三大法人未平倉與交易金額。
* **投信選擇權真實還原**：精確解析投信 `Call: -3.08億 SC 🟢` 與 `Put: +0.003億 BP 🔴`（總部位 SC+BP 防守避險），與期交所官方紀錄 100% 吻合對齊。

### 3. 📋 三大法人與大戶 5 日純數字籌碼歷程矩陣 (5-Day Numerical History Matrix)
* **垂直對齊視覺系統**：採用 `tabular-nums` 等寬字型與 Flexbox 結構，數字靠右對齊、單位 (`口`/`億`) 與色點 (`🔴`/`🟢`) 垂直排成一直線。
* **💡 表格外獨立解讀卡 (Executive Digest Card)**：將 BC / SC / BP / SP 結構分析與結算展望獨立放置在表格上方。

### 4. 🐦 專屬品牌識別（尋鳥 Bluebird Finder）
* **頂級視覺與頭像**：結合少年研究員與藍鳥高畫質 LOGO，配置漸層科技藍與金屬金質感字體。

---

## 🔒 解密通行碼 (Passcode)

網頁開啟時需輸入加密通行碼進行端到端解密：
* **通行碼 (Passcode)**：`GEX2026`（大小寫皆可）

---

## ⚖️ 免責與法律聲明 (Disclaimer)

本網站及內部數據、圖表僅供學術研究與衍生性商品數據可視化參考，非屬證券期貨投資顧問行為，亦不構成任何投資建議。投資人應獨立思考、審慎評估，並自負投資風險與盈虧責任。
