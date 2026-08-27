# 📊 TXO GEX Dashboard — 專案現狀與版本紀錄 (v47.8)

**當前版本**：`v47.8` (2026-08-28 Gemini AI 焦點掃描卡與頂部 KPI 數據動態 100% 同步版)
**資料與視覺引擎**：`scripts/fetch_and_calc_vision.py` (Black-Scholes VEX/GEX+ 引擎 v47.8)
**即時報價網關**：`scripts/fubon_api_provider.py` & `scripts/live_price_server.py` (WebSocket Fubon Gateway v47.8)
**系統狀態**：`✅ 100% 運作正常`
**網頁通行碼**：`GEX2026`（不區分大小寫，支援 👁️ 眼睛切換顯示）

---

## 🎯 v47.8 核心更新亮點（Gemini AI Dynamic Summary Alignment）

### 🤖 1. Gemini AI 焦點掃描卡與頂部 KPI 數據 100% 動態同步 (`app.js`)
- **消除靜態 JSON 數字不一致**：修復底部 `Gemini AI 籌碼、價差與除權息事件量化焦點掃描` 卡片呈現硬編碼舊數據，與頂部動態 KPI 卡片/切換頁籤數據不符的問題。
- **動態綁定 Active Session 數據**：在 `populateAiQuantDigest()` 中動態帶入當前活躍 Session 之指數現價/夜盤價、Zero Gamma、Call Wall 與 Put Wall，確保 AI 摘要與儀表板頂部 100% 完全動態齊平！
- **全站靜態資源版本標籤 (`?v=v47.8`)**：在 `index.html` 內所有的 CSS/JS/Data 標籤更新為 `?v=v47.8` 防快取。

---

## 🎯 v47.6 核心更新亮點（Fresh Social Card Regeneration & HTTP Cache Buster）

### 📸 1. 社群圖卡即時重新生成與防快取機制 (`app.js`)
- **本機/伺服器端圖卡即時重新渲染**：執行 `python scripts/fetch_and_calc_vision.py` 重新根據最新市場籌碼資料產出最新 `social_card_p1_overview.png` (P1 盤後總覽)、`social_card_p2_gex_profile.png` (P2 GEX 對沖牆) 與 `social_card_p3_sector_rotation.png` (P3 板塊資金輪動)。
- **HTTP/CDN Cache-Buster 強制破壞快取**：為所有下載請求（Single PNG、All PNGs、ZIP 打包）與 Modal 預覽圖卡注入動態時間戳記 (`?t=${Date.now()}`) 與 `{ cache: 'no-cache' }` 標頭，徹底解決瀏覽器讀取 08:00 AM 舊圖快取的問題。

---

## 🎯 v47.5 核心更新亮點（Mobile OS Download Throttle & Smart ZIP Auto-Package）

### 📱 1. 手機行動裝置多圖下載與 ZIP 智慧自動包裝修復 (`app.js`)
- **手機雙核心防護機制**：針對 iOS Safari 與 Android Chrome 在彈出第一張下載提示（Prompt）時會吞掉/阻檔後續 `link.click()` 導致 P2 被吃掉的問題，加入 `isMobileDevice()` 智慧判定。
- **手機版一鍵自動 ZIP 打包**：行動裝置點擊「🚀 一鍵下載全部 3 張 PNG」時，自動切換為原生 `JSZip` 打包壓縮模式（100% 一點即收 1 個 ZIP 檔，完全不遺漏 P1/P2/P3 任何一張）。
- **下載間隔與 Blob 生命週期延展**：非 ZIP 下載的間隔從 500ms 拉長至 1,500ms，Blob 記憶體對象釋放延長至 15,000ms，徹底排除行動裝置記憶體與發起頻率限制。

---

## 🎯 v47.4 核心更新亮點（IG/Threads Social Cards Batch PNG Download Engine Fix）

### 📸 1. 社群圖卡一鍵下載 Blob 零阻檔防護 (`app.js`)
- **移除 `target="_blank"` 衝突**：重構 `downloadSingleCard()` 絕不添加 `target="_blank"`，解決 Chrome / Edge 彈出式視窗攔截器 (Popup Blocker) 將第一張圖卡 (`P1_Overview.png`) 誤判為腳本彈窗而阻檔下載的問題。
- **內存 Blob 物件下載**：透過 `fetch()` 將圖卡轉為 `Blob` 物件並綁定 `URL.createObjectURL`，100% 強制瀏覽器發起原生檔案下載。
- **序列化 Async/Await 佇列下載**：將「🚀 一鍵下載全部 3 張 PNG」改為 `async/await` 順序流觸發（每張間隔 500ms），徹底克服瀏覽器多檔案下載防護機制 (Multiple Download Warning)，保證 P1、P2、P3 全套圖卡 100% 穩定存檔。

---

## 🎯 v47.3 核心更新亮點（Microstructure Express Current Market Focus Lock）

### 📌 1. 當下即時盤態單向鎖定
- 徹底鎖定 `📌 日夜盤微觀結構速報` 於最新/當下實時盤態與即時 Tick 價位，避免點擊 5 日歷史表格列時干擾當下解讀。
- 保留 5 日表格與 Satellite GEX 雲圖的歷史切換功能，但速報卡片永遠專注於最新市場情境 (如即時現價與當前 Zero Gamma / Call Wall / Put Wall 距離)。

---

## 🎯 v47.2 核心更新亮點（Trading Session Real-Time Status & History Matrix Date Anchor Alignment）

### ⏰ 1. 5 日歷程矩陣日期錨定校正與結算點數保護
- **開盤前日期對齊**：修正凌晨 00:00~08:44 日盤開盤前，矩陣將當日（T）尚未開盤之日/夜盤列入展示之錯位問題。開盤前自動錨定至上個交易日（T-1），完美呈現 05:00 AM 定案收盤價與定案期貨點數（如夜盤收盤 45,993 點對齊 TV 4-hour K線）。
- **定案點數防護**：修正前端 `app.js` 實時跳動邏輯在非交易時段無差別蓋寫定案列點數之 Bug。已定案收盤列鎖定期交所官方結算價，不被現貨加權指數或廣播 Tick 覆蓋。

### 🟢 2. 台灣時間交易時段實時狀態燈號
- 前端 JavaScript 動態依當下台灣時間判定並展示即時狀態：
  - 🟢 `☀️ 日盤交易中 (08:45-13:45)`
  - 🟡 `☕ 盤後休市 / 非交易時段 (待 15:00 夜盤開盤)`
  - 🔵 `🌙 夜盤交易中 (15:00-05:00)`
  - 🟡 `☕ 早晨休市 / 非交易時段 (待 08:45 日盤開盤)`
  - ☕ `週五/週末定案版 (週末休市)`

### 📸 3. Max Pain 三大空間型態社群圖卡動態對齊
- 社群圖卡 P1 卡片 7 加入 Max Pain 空間型態標籤（🟢 多頭強勢軋空型 / 🟡 箱體沉積結算引力型 / 🔴 恐慌避險暴跌型），與網頁版完全對齊。

---

## 🎯 v47.1 核心更新亮點（TWSE BFI82U Spot Institutional Trading Brokerage Daily Standard）

### 🏛️ 1. 證交所權威 BFI82U API 端點精確對齊
- **修復舊版覆蓋 Bug**：修復舊版在邏輯判斷時將 `外資自營商` 覆蓋 `外資及陸資(不含外資自營商)`，導致外資金額漏算盤後鉅額對敲交易之問題。
- **三大法人買賣超金額 100% 零誤差對齊永豐 / 富邦 / 台新日報**：
  - **外資買賣超**：`外資及陸資(不含外資自營商)` (`+366.13 億 TWD`)
  - **投信買賣超**：`投信` (`+33.66 億 TWD`)
  - **自營商買賣超**：`自營商(自行買賣 + 避險)` (`+179.34 億 TWD`)
  - **三大法人合計**：`合計` (`+579.13 億 TWD`)

---

## 🎯 v47.0 核心更新亮點（Max Pain Spatial Topology & TWSE 21:00 Margin Maintenance Dual Session Split）

### 🧲 1. Max Pain 空間籌碼結構拓撲 (Spatial Topology Matrix)
- **動態 Badge 診斷與色彩標準 (符合台股紅多綠空)**：
  - 🔴 **型態 A：多頭強勢軋空** (`Max Pain < Put Wall`): 上方 Call OI 大量累積，近端 Put Wall 護盤，首防 Put Wall 建立 **Bull Put Spread【2腳】** (`Sell Put@Put Wall` / `Buy Put@Put Wall-200`)。
  - 🟡 **型態 B：對稱健康箱體** (`Put Wall <= Max Pain <= Call Wall`): 多空對稱，Max Pain 居中央，週三結算引力吸附，適合 **Iron Condor 雙賣鐵鷹【4腳】**。
  - 🟢 **型態 C：空頭恐慌避險** (`Put Wall << Max Pain`): 深價外 Put 避險強烈，下檔波動率升，建議 **Bear Call Spread【2腳】** 防禦或微台順勢空。
- **UI 動態 Badge 與 Modal 內建教學指南**：頂部 MAX PAIN KPI 卡片整合動態 Badge 與 `🎓 拓撲診斷 ℹ️` 按鈕，單擊直達【判讀教學指南 Modal】第 4 區塊拓撲診斷對照表與 2腳/4腳精確下單 SOP。

### 📊 2. 融資維持率 21:00 TWSE 清算時序與夜盤雙軌分離
- **夜盤 Session 嚴謹分離**：個股在夜盤休市無成交價與信用交易變動，標示 `- (非交易時段)` 與 `夜盤休市無數據`。
- **日盤 Session 21:00 時序清算**：盤後 (如 16:00) 證交所尚未公布當日信用交易時，標示金黃虛線膠囊 `未公布 (21:00更新)`；晚間 21:00 或隔晨 06:00 自動補齊數字與四級燈號 (`155.8% 🟢 安定` / `個股 141.2%`)。

---

## 🎯 v46.2 核心更新亮點（TAIFEX / TWSE Official Endpoints & Dynamic Digest Engines）

### 📊 1. 雙軌融資維持率與四級狀態燈號 (Location A 矩陣)
- **四級燈號膠囊**：矩陣表 2 融資維持率儲存格與副標題全自動渲染四級燈號：`≥ 160%` 🟢 **安定** | `150% ~ 160%` 🟡 **常態** | `140% ~ 150%` 🟠 **警戒** | `< 140%` 🔴 **斷頭/洗盤**。

### ⚡ 2. 期交所 100% 真實成交量個股期貨榜首引擎 (Module 10)
- **353 檔契約精準對射**：對接期交所 `stockMargining` 與 `futDailyMarketExcel?commodity_id=STF`，全自動擷取全市場個股期貨成交量與結算價，榜首排序 100% 零誤差對齊期交所官方 SSF 熱力圖。

### 💡 3. 本日籌碼體質與選擇權結構解讀卡動態重構 (`executive_digest`)
- **告別寫死舊點位**：將 Section 3 頂部 `💡 本日籌碼體質解讀卡` 改為由當日 TAIFEX 真實數據即時推導，動態更新現價、Zero Gamma、Call Wall (45,400) 與 Put Wall (45,000)。

### 🤖 4. Gemini AI 籌碼、價差與除權息掃描卡動態化 (`ai_ex_dividend_digest`)
- **對接期交所 contractAdj & 證交所 TWT48U/49U**：解析 229 檔最新除權息扣點資訊（如川湖 $51元、世芯-KY $32.55元、台光電 $25元、台積電 $4元），並即時連動熱門個股期貨標的。

### 📸 5. 社群圖卡 Card 8 區分日夜盤雙視角
- **對齊 Web Dashboard 雙視角**：將 `generate_social_card.py` Card 8 重構為 `☀️ 日盤 (13:45)` 與 `🌙 夜盤校正` 雙層版面。

---

## 🎯 v45.5 核心更新亮點（TAIFEX Official FX Engine & Precise Calibration）

### 🌐 期交所官方外匯參考匯率引擎 (`dailyFXRate`)
- **期交所官方 API 數據對齊**：全面廢棄傳統國際場外點位（Yahoo FX），改為直接解析台灣期交所官方每日外幣參考匯率（`https://www.taifex.com.tw/cht/3/dailyFXRate`）。
- **美元/台幣 (USD/TWD) 與 美元/日圓 (USD/JPY) 100% 精準校準**：完全符合央行與期交所每日 16:00 官方公告基準（如 08/25: USD/TWD 31.87 / USD/JPY 159.47），徹底消除場外即時價位與交割參考價的點位落差。

### 💵 美元指數 (DXY Index & Futures) 高精度交割對齊
- **紐約 ICE 美元指數期貨結算價基準對齊**：校正 DXY 多日滾動漲跌幅與點位計算，精確反映 `98.73` ➔ `98.81` ➔ `98.73` ➔ `98.93` ➔ `98.90` 的交割結構，修復過去因四捨五入導致滾動變動顯示 `+0.00` 的落差。

---

## 🎯 v45.4 核心更新亮點（Fubon API Live Gateway & Dynamic Zero Gamma Sync）

### ⚡ 富邦 Neo API 實時行情串流與合規網關 (`fubon_api_provider.py`)
- **Fubon MarketData WebSocket 原生串接**：完成本機行情網關對富邦 Neo API SDK 的全功能實接，實現台指期近月合約 Tick 價位、漲跌點數與漲跌幅極速推播。
- **智慧時段與合約轉換**：自動依時間判斷 `REGULAR` (日盤) 與 `AFTERHOURS` (夜盤) 合約碼。
- **合規性確保**：資訊安全嚴格控管，`.env` 私鑰離線防護，本機獨享即時數據。

### 📊 Live Tick 動態跳動與 Zero Gamma 雙圖 100% 實時同步連動 (`app.js`)
- **即時視覺特效**：實時點位更新觸發 `.live-tick-flash-up` / `.live-tick-flash-down` 紅綠閃爍動畫。
- **Zero Gamma 盤中動態位移**：現價跳動時，Zero Gamma 依 Gamma/Vanna 曲線即時推演最新防守臨界點。
- **圖 1 與 圖 2 雙表實時連動**：Card 4 與表 2《近 5 日關鍵市場指數矩陣》頂列 `🌙 T夜盤 (Live 即時動態)` 數字動態同步跳動。

### 🔍 日夜盤微觀結構速報動態校正引擎 (`updateMicrostructureExpress()`)
- **消除靜態文案矛盾**：依據實時現價與 Zero Gamma 關係動態開關，確保現價在 Zero Gamma 之上時 100% 呈現 `🔴 正 Gamma 區 (護盤中)`。
- **Call Wall 突破告警**：現價超越 Call Wall 天花板時自動輸出 `🚀 Call Wall 已突破` 之 Gamma Squeeze 軋空告警。

---

## 🎯 v45.3 核心更新亮點（Social Card Dynamic Sync & TWSE Real-time Change Release）

### 📸 社群圖卡數據 100% 全動態對齊與數據一致性 Self-Audit 重構
- **徹底清除硬編碼 (Hardcoding Removal)**：完全重構 `scripts/generate_social_card.py` 的 P1 核心籌碼看板 HTML 模板。將加權指數、櫃買指數、台指期日/夜盤、Zero Gamma、Call/Put Wall、Max Pain、P/C Ratio、VEX/GEX+ Flip 及其位移點數全面改為動態解構由 `fetch_and_calc_vision.py` 產出的 `gex_data.json` 數據 Payload。
- **Web 儀表板與下載圖卡數據 100% 絕對同步**：解決過去儀表板顯示即時數據而下載之 IG/Threads 圖卡呈現寫死舊數據的落差問題。

### 📈 TWSE MIS 現貨與櫃買指數動態漲跌點數與趴數引擎升級
- **即時現貨價差計算 (`fetch_and_calc_vision.py`)**：升級 `fetch_twse_realtime_indices()` 函數，擷取 MIS API 前日收盤價 $y$，即時算出現貨加權指數與櫃買指數的 **漲跌金額 (`spot_change`, `two_change`)** 與 **漲跌幅 (`spot_change_pct`, `two_change_pct`)**。
- **Payload & 內嵌數據同步注入**：將漲跌資訊完整封裝入 `gex_data.json` 與 `data/embedded_data.js`，供前端 UI 與全套圖卡動態選用與高亮標示。

---

## 🎯 v45.2 核心更新亮點（Card 8 Dual-Session & Payload Fix Release）

### ☀️/🌙 Card 8 (VEX 恐慌曝險 & GEX+ Flip) 日夜盤雙層卡片重構
- **對齊 Card 3~7 雙層設計**：頂部 6 張籌碼卡片達 100% 結構統一，同時呈現 `☀️ 日盤 (13:45)` 與 `🌙 夜盤校正 (05:00)` 雙套轉折價位與 VEX 恐慌金額。
- **補齊 Payload Key (`gex_plus_flip`)**：修復 `fetch_and_calc_vision.py` Payload 返回物件遺漏 `gex_plus_flip` 欄位之 Bug，實現夜盤轉折價位 (+100.0點) 實時動態位移。
- **配色與 Icon 100% 嚴格對齊**：修正 VEX Badge 邏輯，確保 `🔴 恐慌時做市商護盤` (紅色 `#ff5252` 多頭) 與 `🟢 恐慌時做市商助跌` (綠色 `#00e676` 空頭) 之 Icon 圓點與文字顏色完全對齊。
- **社群圖卡動態適應**：`generate_social_card.py` 同步適應全新 VEX 恐慌開關狀態與無 `$` 符號純淨點位呈現，確保 Playwright 與 TG 自動截圖 100% 美觀正常。

---

## 🎯 v45.0 核心更新亮點（Major Quant & Social Automation Release）

### 1. 🌀 高階 VEX (Vanna Exposure 恐慌曝險) & GEX+ 計算引擎
- **Black-Scholes Vanna 算式**：計算各履約價與全場做市商 Vanna 恐慌曝險。
- **GEX+ Flip (合成轉折點)**：導出結合「價格波動 (Gamma)」與「恐慌指數 (Vanna)」的靈敏轉折線，提供盤中更早的大跌早鳥預警。

### 2. 📸 尋鳥 Bluebird Finder 專屬風格 1:1 正方形社群懶人圖卡生成器 (`generate_social_card.py`)
- **1:1 正方形標準規格**：每日自動產生 1080x1080 像素、1:1 正方形黃金比例圖卡，擺脫橫向扁平感與上下過度留白。
- **5 大位階多通道標籤防碰撞 (Anti-Collision Engine)**：
  - `現價 Spot` (x: 0.02, left middle) | `GEX+ Flip` (x: 0.32, center top) | `Zero Gamma` (x: 0.65, center bottom) | `Call/Put Wall` (x: 0.98, right top/bottom)。
  - 保障即使現價與轉折位階重疊（如 45,217 vs 45,224），標籤亦 100% 獨立無遮擋。
- 專為 IG、Telegram 與 Threads 發文設計，網頁頂部提供 **`📸 下載 IG/Threads 社群圖卡`** 一鍵快捷下載按鈕。
- 烙印 `© 尋鳥 Bluebird Finder Quant Labs` 官方標章，100% 原創品牌防偽，無任何第三方 IP 字眼。

### 3. 🎓 國中生秒懂白話文教學說明與 Modal 彈窗
- 前端新增卡片 Card 8 (VEX & GEX+ Flip) 與 `❓ 判讀教學` 手冊彈窗。
- 清楚對照區隔 **Max Pain (最大痛點結算日壓制)** vs **VEX (盤中恐慌急殺)** vs **GEX+ Flip (早鳥警報線)**。
- 新增「早鳥警報線高於/低於 Zero Gamma」的一秒口訣。

---

## 🎯 v44.1 核心修復與優化紀錄（Patch Release）

### 1. ☀️/🌙 即時行情時段路由修正 (Live Tick Session Routing Fix)
- **問題修復**：修正 `app.js` -> `handleLiveTick()` 未判斷日夜盤時段之 Bug。現在日盤時間 (08:45 ~ 13:45) 之即時串流點位會正確寫入 `☀️ 日盤` 欄位並顯示漲跌閃爍動畫，不再誤刷 `🌙 夜盤` 數字。
- **價差自動校正**：即時點位更新時，同步實時連動重算日夜盤點位差 `stat-txf-shift`。

### 2. ⚖️ 法規與行情數據授權合規釋疑與註解
- **三軌分流架構**：明確分流「富邦 API (本機個人自用專屬)」與「期交所/證交所 MIS 公開資訊 (個人非商業研究 100% 合規)」，免除二次轉發之法律疑慮。
- **合規聲明**：更新免責聲明與學理說明，符合市場公開資訊合理使用原則 (Fair Use)。

---

## 🎯 v44.0 核心更新亮點（Major UX & Architecture Release）

### 1. 🛡️ 單層獨立面板架構 (Clean 1-Layer DOM Architecture)
- 徹底修正 HTML 閉合標籤，所有 `.panel` 均為 100% 獨立平級單層盒子，消除所有疊加嵌套邊框。

### 2. 📸 社群防盜角落水印與子區塊版權標註
- **核心面板右下角**：透過 `.watermark-panel` 統一烙印半透明版權標示 `© 尋鳥 Bluebird Finder` (`rgba(255, 255, 255, 0.28)` Low-Opacity)。
- **子區塊獨立防偽**：特別在《籌碼體質解讀卡》與《期貨 5 日歷程表》右下角單獨加入版權標籤，滿足使用者隨手「局部裁切截圖發文」時的品牌防偽需求。

### 3. 🛡️ 雙視角雙軌標籤防碰撞機制
- **經典橫軸模式**：`Put Wall / Call Wall` 於下層軌道 (`ay: -24`)，`Zero Gamma (ZG)` 升至上層軌道 (`ay: -56`)，履約價接近時永不安重疊。
- **T型報價視角 (DEFAULT)**：`Call Wall / Put Wall` 位於最右欄 (`x: 0.98`)，`Zero Gamma (ZG)` 置於內側虛線軌 (`x: 0.82`)，解決 Y 軸重疊問題。

### 4. 💎 個股/ETF 期貨 Top 10 一頁 100% 完整呈現
- 篩選器表格容器最大高度調升至 `690px`，切換「🔥 法人買超 Top 10」時，10 行標的一頁直觀呈現不裁切。
---

## 🎯 v45.6 籌碼研討與量化規劃紀錄（Margin Maintenance Ratio & Lumi Quant Resonance）

### 📊 1. 融資維持率算式與含/不含 ETF 核心差異（Quant Insight）
- **官方數據源**：臺灣證券交易所 (TWSE) 每日 `信用交易統計 (MI_MARGIN)` API (`https://www.twse.com.tw/zh/trading/margin/mi-margin.html`)。
- **全市場融資維持率（含 ETF，XQ 視角）**：
  $$\text{大盤整戶維持率} = \frac{\sum (\text{股票+ETF 融資張數} \times \text{今日收盤價})}{\text{原始融資成本}} \times 100\%$$
  - **特點**：因包含高股息/美債 ETF 等龐大抵押市值與低波動部位，大盤維持率會被拉高/稀釋（如停留在 `155%`）。能真實反映全市場**「槓桿籌碼是否徹底沉澱/退場」**（若維持率仍高，代表個股雖殺完，但 ETF 槓桿未退，反彈追價量能不足）。
- **個股融資維持率（不含 ETF，玩股網視角）**：
  - **特點**：扣除 ETF 類別後單獨計算。反應極度靈敏，能率先預警中小型飆股與單一個股的**追繳斷頭潮 (Margin Call Panic)**。

### 💡 2. 大盤門檻動態性與共振指標規劃 (Lumi Fusion Synergy)
- **法定追繳門檻**：`130%` (固定，不隨大盤萬點/創高或 GDP 改變)。
- **大盤共振防守門檻**：
  - **個股維持率 (不含 ETF)**：`< 138% ~ 140%` 觸發極致恐慌洗盤。
  - **全市場維持率 (含 ETF)**：`< 145% ~ 150%` 即達到全市場連鎖斷頭警戒。
- **Lumi 雙重共振機制**：
  - 當 `VEX 恐慌指數` 觸發 **[助跌 / Panic]** 且 `大盤融資維持率` 降至 **`< 145%` 警戒區** ➜ **TG 機器人觸發 [🚨 雙重極致洗盤/強烈 V 轉共振警報]**，作為選擇權 Bull Put Spread / 買 Call 佈局高勝率 SS 級訊號！

---

*最後更新：2026-08-26 最新校準與籌碼研討紀錄 | 尋鳥 Bluebird Finder | v45.6*

