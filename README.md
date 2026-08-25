# 🐦 尋鳥 Bluebird Finder — TXO GEX 量化系統 (v46.2)

> **台指選擇權 Gamma Exposure 波動度與三大法人期權籌碼量化分析平台**
> T型報價視角 (DEFAULT) ✦ VEX 恐慌曝險 ✦ GEX+ Flip 早鳥防守線 ✦ 雙軌融資維持率 Location A 矩陣 ✦ 全套 3 張社群圖卡動態對齊與下載 ✦ 10 盤演變播放器 ✦ 期交所官方外匯引擎

[![GitHub Actions 自動更新](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml/badge.svg)](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml)
[![Live 儀表板](https://img.shields.io/badge/Live-TXO_GEX_Dashboard-00d2ff?style=flat&logo=googlechrome)](https://bluebirdfinder.github.io/TXO-GEX-Dashboard/)
[![引擎版本](https://img.shields.io/badge/Engine-v46.2-ffd700?style=flat&logo=python)](scripts/fetch_and_calc_vision.py)

---

## 🎓 GEX / VEX 全指標國中生白話懶人包

| 指標名稱 | 國中生白話比喻 | 它在看什麼？ | 實戰應用與操作指引 |
| :--- | :--- | :--- | :--- |
| **現價 (Spot)** | 👦 小明目前位置 | 大盤當前即時成交點位 | 作為一切防守距離的基準點 |
| **Call Wall** | 🧱 玻璃天花板 | 做市商賣壓最大牆位 | 大盤上漲貼近時容易漲不動 (可做 Sell Call 價差或多單停利) |
| **Put Wall** | 🛋️ 超大彈簧軟墊 | 做市商護盤最大支撐牆 | 大盤回檔跌至附近容易踩墊反彈 (可建立當沖多單或 Sell Put 價差) |
| **Zero Gamma** | ⚖️ 園區安檢紅外線 | 波動度壓抑 vs 暴跌助跌臨界點 | 站上走慢速安定區；跌破進入做市商追殺避險區 |
| **Max Pain** | 🎯 週三抽獎箱 | 散戶權利金賠最多、莊家賺最多的結算點 | 週二/週三結算前夕，指數常被主力壓回附近讓買方雙歸零 |
| **VEX (NEW)** | 😱 恐慌狂暴開關 | 當恐慌指數 (IV) 飆高時，做市商會護盤還是火上加油 | **負值時**代表盤中一旦急殺，做市商會無腦賣期貨火上加油！ |
| **GEX+ (NEW)** | 🛡️ 總安全指數 | 價格變動 (Gamma) + 恐慌情緒 (Vanna) 的合成總指數 | 正值代表全場做市商整體淨結構仍具備一定安定力道 |
| **GEX+ Flip (NEW)** | 🚨 早鳥提早警報線 | 結合恐慌感後，做市商真正的防守底線 | 比傳統 Zero Gamma 更靈敏發出早鳥大跌預警 |

---

## 🚨 早鳥警報線 (GEX+ Flip) 高低雙情境實戰口訣

### 🔴 情境一：當 VEX 為負值時 (恐慌氣氛重，最常見)
- **關係**：GEX+ Flip 會比 Zero Gamma **高**！（範例：`44,848 > 44,778`）
- **原因**：因為市場恐慌賣壓大，大盤往下掉時不需要等到跌破 `44,778`，在更高的 `44,848` 做市商就已經被恐慌嚇到提前拋售期貨。
- **實戰效果**：早鳥線在上方，給您「提早 70 點逃命 / 試空」的預警！

### 🟢 情境二：當 VEX 為正值時 (市場氣氛樂觀、買盤護盤厚實)
- **關係**：GEX+ Flip 會比 Zero Gamma **低**！（範例：`44,710 < 44,778`）
- **原因**：因為市場非常安定，做市商手裡緩衝很夠。就算大盤跌破 `44,778`，做市商也不會立刻慌張砍單，真正的防守底線可以退守到更低位置 (`44,710`)。
- **實戰效果**：早鳥線在下方，告訴您「大盤抗跌性極強，不要輕易被假跌破騙掉多單」！

💡 **一秒口訣記憶法**：
- 🔴 **VEX 為負 (恐慌強)** ➔ 早鳥線在 **上方**（提早發警報，提醒快跑/試空）。
- 🟢 **VEX 為正 (護盤厚)** ➔ 早鳥線在 **下方**（延後防守線，代表大盤很沉穩抗跌）。

## 🌟 v46.2 期交所/證交所全官方 Endpoint 對齊 & 動態解讀卡

### 🏛️ 1. 期交所 100% 真實成交量個股期貨榜首引擎 (Module 10)
- **353 檔契約精準對射**：對接期交所 `stockMargining` 與 `futDailyMarketExcel?commodity_id=STF`，榜首排序與口數 100% 零誤差對齊期交所官方 SSF 熱力圖。

### 💡 2. 本日籌碼體質與 Gemini AI 焦點解讀卡動態化引擎
- **解讀卡動態重構 (`executive_digest`)**：清除舊寫死點位，由 TAIFEX 當日數據實時推算現價、Zero Gamma、Call/Put Wall (45,400 / 45,000) 與 P/C Ratio (113.2%)。
- **除權息 API 實時對接 (`ai_ex_dividend_digest`)**：對接期交所 `contractAdj` 與證交所 `TWT48U/49U`，解析 229 檔最新除權息扣點資訊（如川湖 $51元、世芯-KY $32.55元、台光電 $25元、台積電 $4元）。

### 📊 3. 雙軌融資維持率與四級狀態燈號 (Location A 矩陣)
- **全市場整戶 vs 純個股維持率**：矩陣表 2 新增全市場整戶與純個股維持率，並帶入四級動態燈號標籤 (`🟢 安定` / `🟡 常態` / `🟠 警戒` / `🔴 斷頭洗盤`)。

### 📸 4. 社群圖卡 Card 8 區分日夜盤雙視角
- **對齊 Web Dashboard 雙視角**：重構 `generate_social_card.py` Card 8 HTML 模板為 `☀️ 日盤 (13:45)` 與 `🌙 夜盤校正` 雙層排版。

---

## 🌟 v45.4 核心功能與修復亮點

### ⚡ 1. 富邦 Neo API 實時行情串流與合規網關 (`fubon_api_provider.py` & `live_price_server.py`)
- **WebSocket 原生串接**：重構本機行情網關，串接富邦 Neo API MarketData WebSocket，實現近月台指期實時 Tick 價格、漲跌點數與漲跌幅極速推送。
- **日夜盤自動切換**：自動根據當前時段智慧判斷 `REGULAR` (日盤) 或 `AFTERHOURS` (夜盤) 並自動替換近月合約程式碼。
- **私有合法、公開合規**：遵守券商 API 報價散佈合規原則，`start_live.bat` 本機獨享實時 WebSocket 報價，雲端公開散佈防護機制完備。

### 📊 2. Live Tick 動態跳動與 Zero Gamma 雙圖 100% 實時同步連動
- **即時閃爍動畫**：網頁點位更新時自動觸發 `.live-tick-flash-up` (紅光上揚) 與 `.live-tick-flash-down` (綠光下跌) 視覺反饋。
- **Zero Gamma 盤中位移**：現價跳動時，Zero Gamma 依據做市商網絡 Gamma/Vanna 敏感度曲線動態推算當前實時防守臨界點。
- **圖 1 與 圖 2 雙表連動**：頂部 Card 4 與表 2《近 5 日關鍵市場指數矩陣》第一列 `🌙 T夜盤 (Live 即時動態)` 的台指期與 Zero Gamma 數字同步動態跳動與閃爍。

### 🔍 3. 微觀結構速報動態校正引擎 (`updateMicrostructureExpress()`)
- **告別靜態文案矛盾**：前端 `app.js` 與後端算式升級為實時動態評估，當標的價格 $> ZG$ 時，速報自動呈現 `🔴 正 Gamma 區 (護盤中)` 與護盤說明，消除歷史靜態數據產生的文案衝突。
- **Call Wall 突破動態告警**：當現價突破 Call Wall 天花板時，速報自動觸發 `🚀 Call Wall 已突破` 之 Gamma Squeeze 強勢軋空告警。

---

## 🌟 v45.3 核心功能與修復亮點

### 📸 1. 社群圖卡 100% 全動態對齊與數據一致性 Self-Audit 重構 (`generate_social_card.py`)
- **徹底清除靜態硬編碼**：重構 P1 核心籌碼看板 HTML 模板，剔除所有硬編碼數值，全面動態解構由 `fetch_and_calc_vision.py` 產出的 `gex_data.json` 數據。
- **動態算式與符號**：加權/櫃買指數、台指期日夜盤、Zero Gamma、Call/Put Wall、Max Pain、VEX/GEX+ Flip 及其差額位移全自動計算並套用色彩標籤，確保 Web 儀表板與下載圖卡數據 100% 精確同步。

### 📈 2. TWSE MIS 即時現貨與櫃買指數動態漲跌點數與趴數引擎 (`fetch_and_calc_vision.py`)
- 升級 `fetch_twse_realtime_indices()` 函數，擷取 MIS API 前日收盤價 $y$，即時算出現貨加權指數與櫃買指數的 **漲跌金額 (`spot_change`, `two_change`)** 與 **漲跌幅 (`spot_change_pct`, `two_change_pct`)**。
- 將漲跌金額與趴數封裝入全域 JSON 及 `data/embedded_data.js` 供前台與圖卡使用。

---

## 🌟 v45.0 核心功能亮點

### 1. 🇹🇼 台灣標準金融色彩 (紅漲看多 / 綠跌看空)
- 全站與 Modal 彈窗貫徹台灣交易員認知：🔴 紅色代表買盤/看多/護盤，🟢 綠色代表賣盤/看空/恐慌追殺。

### 2. ☀️ 日盤 Live 動態路由與日期校正
- 自動偵測 08:45~13:45 日盤時間並高亮導向 `☀️ 日盤 (Live)`，並嚴格修正未開盤之夜盤顯示。

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

### 5. 📸 1:1 正方形社群圖卡標準規範與多通道防碰撞引擎 (`generate_social_card.py`)
- **1:1 正方形黃金比例**：產出規格統一固定為 **1080 × 1080 像素**，消除橫向扁平感與上下過度空洞留白。
- **5 大關鍵位階多通道標籤防碰撞 (Anti-Collision Annotation Engine)**：
  - 當現價、Zero Gamma、早鳥轉折位階高度靠近時，自動劃分為 4 大水平通道：
    - `x: 0.02 (最左)`：`⏳ 標的現價` (`yanchor: middle`)
    - `x: 0.32 (中左)`：`🔮 GEX+ 早鳥轉折` (`yanchor: top`)
    - `x: 0.65 (中右)`：`⚡ Zero Gamma` (`yanchor: bottom`)
    - `x: 0.98 (最右)`：`Call Wall` (紅色上浮) / `Put Wall` (綠色下掛)
  - 確保所有位階標籤在任何行情動態下 100% 獨立不相重疊。
- **全套 3 張社群圖卡一鍵批次與 ZIP 下載 Modal 彈窗**：
  - 點擊頂部「📸 下載 IG/Threads 社群圖卡」即刻開啟全套圖卡 Modal 視窗。
  - 支援「🚀 一鍵下載全部 3 張 PNG」、「📦 打包下載 ZIP 壓縮包」與各圖卡單獨下載按鈕。

### 6. ⚡ 三級優先級即時報價網關
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
