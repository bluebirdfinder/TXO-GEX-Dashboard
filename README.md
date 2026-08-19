# 🐦 尋鳥 Bluebird Finder — TXO GEX 量化系統 (v44.0)

> **台指選擇權 Gamma Exposure 波動度與三大法人期權籌碼量化分析平台**
> T型報價視角 (DEFAULT) ✦ 雙視角雙軌防碰撞標籤 ✦ 獨立單層面板架構 ✦ 10 盤演變播放器 ✦ 三級即時報價網關 ✦ 社群防盜標籤角落水印

[![GitHub Actions 自動更新](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml/badge.svg)](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml)
[![Live 儀表板](https://img.shields.io/badge/Live-TXO_GEX_Dashboard-00d2ff?style=flat&logo=googlechrome)](https://bluebirdfinder.github.io/TXO-GEX-Dashboard/)
[![引擎版本](https://img.shields.io/badge/Engine-v44.0-ffd700?style=flat&logo=python)](scripts/fetch_and_calc_vision.py)

---

## 🌟 v44.0 核心功能亮點

### 1. ↔️ 預設 T型報價視角 & 雙軌標籤防碰撞
- **T型報價視角（預設 DEFAULT）**：
  - **Y 軸 (豎軸)**：履約價 (Strike)，符合台灣期貨與選擇權交易員習慣的 T 型報價表邏輯。
  - **X 軸 (橫軸)**：GEX 曝險金額 (億 TWD)。**右側為 Call GEX 壓力牆 (+)，左側為 Put GEX 防守牆 (-)**。
  - **縱向防碰撞**：`Call Wall / Put Wall` 位於最右欄 (`x: 0.98`)，`Zero Gamma (ZG)` 獨立置於內側虛線軌 (`x: 0.82`)，縱向履約價接近時永不遮擋。
- **↕️ 經典橫軸視角 (切換按鈕)**：
  - 一鍵切換至傳統技術分析橫軸視角（X軸為履約價 / Y軸為 GEX 金額）。
  - **高低階梯式雙軌標籤**：`Put Wall / Call Wall` 於下層軌道 (`ay: -24`)，`Zero Gamma` 升至上層軌道 (`ay: -56`)，徹底告別標籤重疊。

### 2. 🛡️ 單層獨立面板 & 社群截圖防盜水印 (Watermark Protection)
- **單層無嵌套 DOM 結構**：所有 `.panel` 卡片 100% 獨立平級，告別多層包覆邊框。
- **子區塊獨立防偽**：除了核心面板右下角外，在《籌碼體質解讀卡》與《期貨 5 日歷程表》右下角單獨加入 `© 尋鳥 Bluebird Finder`，即使局部截圖發文也能 100% 保留版權標示。
- **Plotly 圖表雙浮水印**：畫布中央 `尋鳥 Bluebird Finder • TXO GEX Quant System` (`rgba(0, 210, 255, 0.09)`) 與右下角 `© 尋鳥 Bluebird Finder` (`rgba(255,255,255,0.28)` Low-Opacity 灰淡色防護)。

### 3. 💎 個股/ETF 期貨 Top 10 一頁 100% 完整呈現
- 篩選器表格滾動容器調整至 **`690px`**，切換「🔥 法人買超 Top 10」或「❄️ 法人賣超 Top 10」時，10 行熱門標的一頁直觀呈現，無需手動拉動滾動條。
- 5 日關鍵矩陣移除 `max-height` 滾動限制，5~6 行歷史行情直接完整展開。

### 4. 🎬 10 盤歷史籌碼動態演變播放器
- 支援一鍵點擊 `▶️ 播放 10 盤動態演變`，以 1.2 秒逐幀播放 **過去 5 天 10 個日夜盤** GEX 柱狀圖位移與 Net GEX S 曲線變形。

### 5. ⚡ 三級優先級即時報價網關
- 三級降級容錯：**優先 1**：極速專線網關 → **優先 2**：網頁行情網關 → **優先 3**：期交所 MIS 官方報價。

---

## 🛠️ 系統架構

| 模組 | 技術 stack |
|---|---|
| **前端 UI** | HTML5, Vanilla CSS3 (深色擬物模式), Vanilla JavaScript ES6+ |
| **圖表引擎** | Plotly.js v2.27.0 (雙方向橫條/豎條 + 樣條 S 曲線) |
| **資料與視覺引擎** | Python 3.12, BeautifulSoup4, Pandas |
| **即時報價網關** | Python WebSockets / Asyncio |
| **加密與權限** | SHA-256 XOR 加密（通行碼：GEX2026） |
| **自動化部署** | GitHub Actions Cron（每日 14:00 日盤定案 & 05:00 夜盤定案） |

---

## 🚀 本機執行步驟

```bash
pip install beautifulsoup4 requests websockets
python scripts/fetch_and_calc_vision.py
python -c "import json; data=json.load(open('data/gex_data.json',encoding='utf-8')); open('data/embedded_data.js','w',encoding='utf-8').write('window.GEX_EMBEDDED_DATA = ' + json.dumps(data, ensure_ascii=False) + ';')"
python -m http.server 8080
# 瀏覽器：http://localhost:8080/index.html （通行碼：GEX2026）
```

---

## ⚖️ 免責與法律聲明 (Legal Disclaimer)

本平台（含 GEX 計算結果、三大法人籌碼數據與 AI 解讀）**僅供學術研究與衍生性商品數據可視化參考**，非屬證券期貨投資顧問行為，亦不構成任何買賣投資建議。衍生性商品交易具高度風險，投資人應獨立思考、審慎評估，並自負投資盈虧責任。

© 2026 尋鳥 Bluebird Finder Quant Labs. 版權所有，未經授權請勿商業重製與無償轉載。
