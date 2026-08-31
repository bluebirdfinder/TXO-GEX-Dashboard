# 🐦 尋鳥 Bluebird Finder — TXO GEX 量化系統 (v49.4)

> **台指選擇權 Gamma Exposure 波動度與三大法人期權籌碼量化分析平台**
> TWSE 現股報價雙軌熱備援 ✦ 通行碼彈窗自動通關與作用域熱修復 ✦ GitHub Actions 離峰 Cron 排程錯開 ✦ 離線夜盤時段視窗修復 ✦ 休市保護機制 ✦ TWSE 信用交易融資維持率 API 實時連線 ✦ 動態 4 階段 Session 配對架構 ✦ 官方 6 大夜盤股期/ETF期價量矩陣 ✦ 夜盤05:00收盤價精確校正 ✦ 排程時區防錯對齊 ✦ Gemini AI 摘要動態齊平 ✦ T型報價視角 (DEFAULT) ✦ iOS Safari 同步手勢下載修復 ✦ 社群圖卡即時重繪 ✦ HTTP 快取破壞與 Cache-Buster 防護 ✦ 手機版 ZIP 智慧自動包裝

[![GitHub Actions 自動更新](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml/badge.svg)](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml)
[![Live 儀表板](https://img.shields.io/badge/Live-TXO_GEX_Dashboard-00d2ff?style=flat&logo=googlechrome)](https://bluebirdfinder.github.io/TXO-GEX-Dashboard/)
[![引擎版本](https://img.shields.io/badge/Engine-v49.4-ffd700?style=flat&logo=python)](scripts/fetch_and_calc_vision.py)

---

## 🌟 v49.4 TWSE 現股報價雙軌熱備援與通行碼彈窗自動通關熱修復

### 🛡️ 1. TWSE 現股報價雙軌熱備援 (Multi-Tier Stock Spot Price Fallback)
- **多層級現貨抓取**：升級 `fetch_twse_stock_spot_prices()` 導入 Tier 1 TWSE OpenAPI (`STOCK_DAY_ALL`) ➔ Tier 2 TWSE MIS 官方即時 API 雙軌抓取備援，並校正靜態備用庫，確保個股期現貨價差計算極致精準。

### 🔑 2. 通行碼防護遮罩自動通關與作用域修復 (Passcode Modal Auto-Bypass & Scope Hotfix)
- **休市作用域修復**：修正 `app.js` 在市場休市時段 `isMarketClosed` 的 `liveZg` 作用域問題。
- **預設通關優化**：優化 `passcode-modal` 預設通行碼 (`GEX2026`) 自動通關邏輯，徹底解決開頁出現全螢幕黑色遮罩擋住內容之問題。

### ⏰ 1. GitHub Actions 離峰 Cron 排程錯開 (Cron Schedule Shift)
- **避開全球整點塞車**：將 `.github/workflows/auto_update.yml` 中的自動觸發時間由原整點（如 `:00` / `:30`）調為離峰時間（如 `:03` / `:33`），徹底解決 GitHub 官方伺服器整點排隊延遲問題。
- **融資維持率保險重試**：晚上維持率視窗新增 `22:03` (TWD) 備援排程，防止證交所盤後數據延遲發布時遺漏更新。

### 🌙 2. 離線/無富邦 Gateway 之夜盤時段視窗與休市保護 (Offline Session Guard)
- **時段涵蓋修正**：修正 `app.js` 與 Cloudflare Worker 之 `isNightSession` 判斷視窗 (`05:00~08:45 AM` 涵蓋入夜盤定案視窗)。
- **休市位移保護 (`isMarketClosed`)**：於非交易時段（05:00~08:45 / 13:45~15:00）鎖定動態位移，防止未開啟富邦 API 時備援來源（期交所 MIS / 雅虎）將夜盤定案版 Zero Gamma (`46,116.8`) 蓋掉。

### 🏛️ 3. TWSE 融資維持率發布狀態校正 (`fetch_twse_margin_maintenance`)
- **發布狀態邏輯修正**：修正 `fetch_and_calc_vision.py` 之 `is_published` 判斷，清晨執行時正確帶出已發布之融資維持率 (`159.2%`)。

---

## 🌟 v49.1 動態 4 階段時段 GEX 配對架構、期交所官方夜盤個股期 API 直連與 TWSE 融資維持率 API

### 🕒 1. 動態 4 階段 Session 時段配對架構 (4-Phase Dynamic Session Architecture)
- **時段感知與 GEX 點位嚴格配對**：重構行情判定邏輯，自動劃分 `DAY_LIVE` (日盤盤中 08:45~13:45)、`DAY_SETTLED` (日盤定案 13:45~15:00)、`NIGHT_LIVE` (夜盤盤中 15:00~05:00) 及 `NIGHT_SETTLED` (夜盤定案/週末休市) 4 大階段。
- **點位與警告動態連動**：標的物價格 (`active_price`) 嚴格配對當前階段之 Zero Gamma (`zg`)、Call Wall (`cw`)、Put Wall (`pw`) 與 Max Pain (`mp`)，並於微觀速報與 Gemini AI 掃描卡片實時觸發「Put Wall 跌破 (46,100 點失守) 向下尋求 Max Pain (45,700 點) 磁吸防守」之警示。

### 🌙 2. 期交所官方 6 大夜盤個股/ETF期貨 API 直連 (`marketCode=1`)
- **直連 TAIFEX 夜盤 API**：直接串接台灣期貨交易所官方夜盤行情 API (`futDailyMarketExcel?marketCode=1`)，精準抓取 6 大夜盤標的：台積電期 (`2330`)、小型台積期 (`2330F`)、聯電期 (`2303` CCF 夜盤定案 `127.00`)、元大台灣50期 (`0050`)、小型50期 (`0050F`) 及元大美債20年期 (`00679B`)。
- **現貨價與期貨價劃分 (真實期現價差 Basis)**：保留 TWSE 日盤現貨收盤價 (如聯電現貨 `130.00`) 與 TAIFEX 夜盤期貨定案價 (聯電期 `127.00`)，真實驗算並渲染最新夜盤逆價差 (`-3.00 點`)。

### 🏛️ 3. TWSE 信用交易融資維持率 API 實時動態連線 (`fetch_twse_margin_maintenance`)
- **實時 API 抓取與日期感知**：數據引擎直接連線臺灣證券交易所 (TWSE) 信用交易統計 API (`https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?response=json`)。當證交所完成當日盤後清算（約 20:30），自動辨識 `date` 狀態，即時轉為 `is_published = True` 並寫入當日大盤融資維持率 (`160.6% 🟢 安定`) 與個股維持率 (`145.9%`)。

### 🚀 4. 常駐防錯發布 SOP 與全站版號對齊 (`.agents/rules/VERSION_RELEASE.md`)
- **常駐 SOP 規則**：建置 `.agents/rules/VERSION_RELEASE.md` 自動常駐規則，規範版號變更時必須於 commit 前立即重跑 `python scripts/fetch_and_calc_vision.py` 重繪 Payload，徹底消除版號跳動與靜態/動態版號差異。

---

### 🛡️ 1. TWSE 現貨指數多源熱備援機制 (`scripts/fetch_and_calc_vision.py`)
- **多層級熱備援抓取 (Multi-Tier Fallback)**：重構 `fetch_twse_realtime_indices()`，依序嘗試 TWSE MIS API ➔ Yahoo Finance 全球 API (`^TWII` 加權 / `^TWOII` 櫃買) ➔ 本地 `gex_data.json` 快照，徹底解決 GitHub Actions 國外 IP 遭 TWSE 阻擋降級成舊值 `45811.01` / `400.95` 的硬碼問題。
- **現貨漲跌幅實時動態渲染**：清理 `index.html` 寫死之 `+3,186.45` 硬碼字串，於 `app.js` 加入 `#stat-spot-sub` 與 `#stat-otc-sub` 的動態點數與 % 渲染（隨行情實時調色）。

### 📊 2. 5 日歷程矩陣 T-1 前一交易日收盤價真實比對
- **廢除偽造歷史公式 (`spot_price - 74`)**：歷史 10 盤對齊真實前一交易日現貨收盤價 (`prev_day_spot = spot_price - spot_change`)，讓矩陣真實算出 `(+356.23)` 點與 `(+2.45)` 點，解決手動提早或多次觸發腳本時顯示偽造 `(+74.00)` 點之錯誤。

### ⏰ 3. GitHub Actions 補齊 21:00 TWD 融資維持率定時排程 (`auto_update.yml`)
- **新增 21:00 / 21:30 TWD 自動定時抓取**：於 `.github/workflows/auto_update.yml` 加入 `- cron: '0 13 * * 1-5'` (21:00 TWD)，在證交所每晚 21:00 公布「大盤整戶融資維持率」時自動補齊數據。
- **盤後定案保護**：夜網與 21:00 抓取時安全維護 15:30 盤後已定案之 GEX Profile 與三大法人籌碼，不重算或干擾 15:30 基線。

### ⚡ 4. 全站版本號 100% 對齊 (消除重整瞬間 V49 閃跳 V48.2)
- **前後端版本一致**：將 `scripts/fetch_and_calc_vision.py` 的 `ENGINE_VERSION` 提升為 `"v49.0"`，並重新產生 `data/gex_data.json` 與 `data/embedded_data.js`，解決 HTML 標籤 (`v49.0`) 與 JS 讀取數據 (`v48.2`) 不一致導致的重整閃爍現象。

---

## 🌟 v49.0 Instagram & Threads 官方 QR Code 增粉與 @bluebird_finder 標籤全站整合

### 📱 1. 獨立高解析度 QR Code 自動生成器 (`scripts/generate_qr_codes.py`)
- **雙平台高對比度 QR Code**：自動產出高解析度、高對比、相容所有手機鏡頭與第三方 APP 秒讀之 Instagram 與 Threads 專屬黑金科技風 QR Code。
- **QR Code 下方標示官方 ID (`@bluebird_finder`)**：於生成之 QR Code 圖檔、1:1 社群懶人圖卡與 Web 儀表板頁尾清楚標示 `IG: @bluebird_finder` 與 `Threads: @bluebird_finder`。

### 📸 2. 1:1 正方形社群懶人圖卡頁尾整合 (`scripts/generate_social_card.py`)
- **雙平台 QR Code 吸粉專區**：在每張每日自動生成發布之 1080x1080 圖卡（Card 1/2/3）頁尾加入雙平台 QR Code、官方 ID 標籤與吸粉文案：`📲 掃碼追蹤「尋鳥 Bluebird Finder」 | 每日即時盤中籌碼速報與做市商 GEX 轉折關卡`。

### 🌐 3. Web Dashboard 導覽列與頁尾吸粉卡片 (`index.html` & `style.css`)
- **頂部 Nav 按鈕**：新增 `📱 追蹤社群 (@bluebird_finder)` 亮眼按鈕，點擊可平滑滾動至頁尾社群專區。
- **頁尾吸粉卡片**：在頁尾版權宣告前增設大器美觀的 `social-follow-card` 專區，展示雙平台 QR Code、官方 ID 與一鍵開啟連結按鈕。

---

## 🌟 v48.1 國際重大總經事件、富台/MSCI 甩尾與結算日 實時避險防護雷達

### 🚨 1. 實時避險倒數雷達與 3 階動態風暴視窗 (`#macro-events-radar-panel`)
- **全方位重大事件庫**：整合 **週/月台指選大結算**、**SGX 富台指期貨結算**、**MSCI 季度/半年度尾盤爆量甩尾調整**、**美大非農 (NFP) + 失業率**、**美 ADP 小非農**、**美每週初領失業金 (Jobless Claims)**、**美 CPI 通膨數據** 與 **美聯儲 FOMC 利率決議**。
- **與 Lumi Telegram 機器人 v48.1 規格 100% 對齊 (`pattern_type`)**：
  - **`POINT_TIME` (定點數據型)**：美 CPI、大非農 NFP、ADP、初領失業金，預警發布前 15~30 分鐘流動性急遽抽離。
  - **`WINDOW_TIME` (視窗洗盤型)**：週/月選結算 (13:30)、富台指結算 (13:45)、MSCI 甩尾 (13:25)，預警尾盤撮合與大筆未平倉平倉擺盪。
- **事件專屬客製化提早預警時間窗 (Tailored Lead Warning Windows)**：
  - **重磅總經/月結算/MSCI**：提前 24 小時黃色警戒，發布前 90~120 分鐘觸發 `🚨 衝擊告急風暴圈` 紅光脈衝閃爍。
  - **常態/前瞻數據**：提前 6 小時黃色警戒，發布前 30 分鐘觸發告急。
- **美股夏冬令時間 (EDT/EST) 與台灣時間 (UTC+8) 動態自動校正**：全站顯示時間 100% 標註 `(台灣時間)`，全球絕對時間戳 (Epoch ms) 確保秒級倒數零誤差。
- **全站靜態資源版本標籤 (`?v=v48.1`)**：在 `index.html` 內所有的 CSS/JS/Data 標籤更新為 `?v=v48.1` 防快取。

---

## 🌟 v48.0 期交所官方 6 大夜盤個股/ETF期貨 價量與籌碼即時行情矩陣

### 🌙 1. 官方 6 大夜盤股期/ETF期 即時價量關係與指標導航 (Night-Traded 6 Spotlight)
- **夜盤 6 大開放契約聚焦**：專屬整合台積電期 (`2330`)、小型台積期 (`2330F`)、元大台灣50期 (`0050`)、小型台50期 (`0050F`)、聯電期 (`2303`) 與元大美債20年期 (`00679B`)。
- **市場熱門度與流動性優先級排序**：依據權重、成交量與市場關注度嚴格排序：`2330 (台積期)` ➔ `2330F (小台積期)` ➔ `0050 (台50期)` ➔ `0050F (小台50期)` ➔ `2303 (聯電期)` ➔ `00679B (美債期)`。
- **價量關係與警示訊號 (`app.js`)**：
  - **價差診斷 (Basis Diagnostic)**：精確計算期現價差（🔴 正價差 / 🟢 逆價差）與對應基差。
  - **大盤點數貢獻 (Points Contribution)**：估算台積期、聯電期、0050期對台指大盤的即時拉抬/壓低點數。
  - **價量動態動能訊號**：自動計算並標註 `🔥 價量齊揚 (強勢偏多)`、`⚠️ 帶量拉回 (壓力避險)` 與 `☕ 盤整觀望` 訊號。
  - **三大法人未平倉與除息日程**：呈現外資與自營商未平倉部位，並標註 TWSE 除權息日程與預扣現金股利。
- **全面板雙重浮水印安全防護**：於「產業資金輪動」與「6大夜盤價量矩陣」面板右下角全面補齊高對比度 **`© 尋鳥 Bluebird Finder`** 防護浮水印。
- **全站靜態資源版本標籤 (`?v=v48.0`)**：在 `index.html` 內所有的 CSS/JS/Data 標籤更新為 `?v=v48.0` 防快取。

---

## 🌟 v47.9 台指期夜盤 05:00 收盤價精確校正與自動排程時區防錯機制

### 🌙 1. 台指期夜盤 (TXF) 定案收盤價與 GEX 全套結構動態校正
- **夜盤收盤價校正至 46,388**：將台指期夜盤結算收盤價校正至期交所官方 05:00 定案值 46,388 點（取代盤中未收盤暫存價 45,993 點）。
- **GEX 籌碼結構與牆位全面聯動**：標的基準價變更同步引發 Call Wall (46,700 / 46,200), Zero Gamma (46,517.9 / 46,017.9), Put Wall (46,300 / 45,800), Max Pain (45,900 / 45,400) 與 P/C Ratio 全動態黑體算式精確重計算。
- **自動排程與時區邊界防錯 (`scripts/fetch_and_calc_vision.py`)**：
  - 優化夜盤視窗判定邏輯 `(3 <= now_hour < 12)`，確保清晨凌晨 03:00 起的自動或手動觸發皆能精確捕捉夜盤數據。
  - 明確規範 GitHub Actions UTC 排程時區對齊（例：UTC 21:30 = 台灣時間 05:30 AM），防止未收盤即過早發布報告。
- **全站靜態資源版本標籤 (`?v=v47.9`)**：在 `index.html` 內所有的 CSS/JS/Data 標籤更新為 `?v=v47.9` 防快取。

---

## 🌟 v47.8 Gemini AI 焦點掃描卡與頂部 KPI 數據 100% 動態同步

### 🤖 1. Gemini AI 焦點掃描卡與頂部 KPI 數據 100% 動態同步 (Gemini AI Dynamic Summary Alignment)
- **消除靜態 JSON 數字不一致**：修復底部 `Gemini AI 籌碼、價差與除權息事件量化焦點掃描` 卡片呈現硬編碼舊數據，與頂部動態 KPI 卡片/切換頁籤數據不符的問題。
- **動態綁定 Active Session 數據**：在 `populateAiQuantDigest()` 中動態帶入當前活躍 Session 之指數現價/夜盤價、Zero Gamma、Call Wall 與 Put Wall，確保 AI 摘要與儀表板頂部 100% 完全動態齊平！
- **全站靜態資源版本標籤 (`?v=v47.8`)**：在 `index.html` 內所有的 CSS/JS/Data 標籤更新為 `?v=v47.8` 防快取。

---

## 🌟 v47.6 社群圖卡即時重繪與 HTTP Cache-Buster 防快取機制

### 📸 1. 社群圖卡即時重新生成與防快取機制 (Fresh Social Card Regeneration & HTTP Cache Buster)
- **本機/伺服器端圖卡即時重新渲染**：執行 `python scripts/fetch_and_calc_vision.py` 重新根據最新市場籌碼資料產出最新 `social_card_p1_overview.png` (P1 盤後總覽)、`social_card_p2_gex_profile.png` (P2 GEX 對沖牆) 與 `social_card_p3_sector_rotation.png` (P3 板塊資金輪動)。
- **HTTP/CDN Cache-Buster 強制破壞快取**：為所有下載請求（Single PNG、All PNGs、ZIP 打包）與 Modal 預覽圖卡注入動態時間戳記 (`?t=${Date.now()}`) 與 `{ cache: 'no-cache' }` 標頭，徹底解決瀏覽器讀取 08:00 AM 舊圖快取的問題。

---

## 🌟 v47.5 手機版行動裝置多圖下載與跨平台 ZIP 智慧自動包裝修復

### 📱 1. 手機行動裝置多圖下載與 ZIP 智慧自動包裝修復 (Mobile OS Download Throttle & Smart ZIP)
- **手機雙核心防護機制**：針對 iOS Safari 與 Android Chrome 在彈出第一張下載提示（Prompt）時會吞掉/阻檔後續 `link.click()` 導致 P2 被吃掉的問題，加入 `isMobileDevice()` 智慧判定。
- **手機版一鍵自動 ZIP 打包**：行動裝置點擊「🚀 一鍵下載全部 3 張 PNG」時，自動切換為原生 `JSZip` 打包壓縮模式（100% 一點即收 1 個 ZIP 檔，完全不遺漏 P1/P2/P3 任何一張）。
- **下載間隔與 Blob 生命週期延展**：非 ZIP 下載的間隔從 500ms 拉長至 1,500ms，Blob 記憶體對象釋放延長至 15,000ms，徹底排除行動裝置記憶體與發起頻率限制。

---

## 🌟 v47.4 IG/Threads 社群圖卡一鍵下載與 Blob 零阻檔防護修正

### 📸 1. 社群圖卡一鍵下載 Blob 零阻檔防護 (Social Cards Batch PNG Download Engine Fix)
- **移除 `target="_blank"` 衝突**：重構 `downloadSingleCard()` 絕不添加 `target="_blank"`，解決 Chrome / Edge 彈出式視窗攔截器 (Popup Blocker) 將第一張圖卡 (`P1_Overview.png`) 誤判為腳本彈窗而阻檔下載的問題。
- **內存 Blob 物件下載**：透過 `fetch()` 將圖卡轉為 `Blob` 物件並綁定 `URL.createObjectURL`，100% 強制瀏覽器發起原生檔案下載。
- **序列化 Async/Await 佇列下載**：將「🚀 一鍵下載全部 3 張 PNG」改為 `async/await` 順序流觸發（每張間隔 500ms），徹底克服瀏覽器多檔案下載防護機制 (Multiple Download Warning)，保證 P1、P2、P3 全套圖卡 100% 穩定存檔。

---

## 🌟 v47.3 日夜盤微觀結構速報當下即時盤態單向強防護鎖定

### 📌 1. 當下即時盤態單向鎖定 (Microstructure Express Current Market Focus Lock)
- 徹底鎖定 `📌 日夜盤微觀結構速報` 於最新/當下實時盤態與即時 Tick 價位，避免點擊 5 日歷史表格列時干擾當下解讀。
- 保留 5 日表格與 Satellite GEX 雲圖的歷史切換功能，但速報卡片永遠專注於最新市場情境 (如即時現價與當前 Zero Gamma / Call Wall / Put Wall 距離)。

---

## 🌟 v47.2 交易時段動態狀態燈號、5 日矩陣日期錨定校正與 Max Pain 拓撲對齊

### ⏰ 1. 5 日歷程矩陣日期錨定校正與結算點數保護 (History Matrix Anchor & Price Protection)
- **開盤前日期對齊**：修正凌晨 00:00~08:44 日盤開盤前，矩陣將當日（T）尚未開盤之日/夜盤列入展示之錯位問題。開盤前自動錨定至上個交易日（T-1），完美呈現 05:00 AM 定案收盤價與定案期貨點數（如夜盤收盤 45,993 點對齊 TV 4-hour K線）。
- **定案點數防護**：修正前端 `app.js` 實時跳動邏輯在非交易時段無差別蓋寫定案列點數之 Bug。已定案收盤列鎖定期交所官方結算價，不被現貨加權指數或廣播 Tick 覆蓋。

### 🟢 2. 台灣時間交易時段實時狀態燈號 (Real-Time Taiwan Trading Session Status Pill)
- 前端 JavaScript 動態依當下台灣時間判定並展示即時狀態：
  - 🟢 `☀️ 日盤交易中 (08:45-13:45)`
  - 🟡 `☕ 盤後休市 / 非交易時段 (待 15:00 夜盤開盤)`
  - 🔵 `🌙 夜盤交易中 (15:00-05:00)`
  - 🟡 `☕ 早晨休市 / 非交易時段 (待 08:45 日盤開盤)`
  - ☕ `週五/週末定案版 (週末休市)`

### 📸 3. Max Pain 三大空間型態社群圖卡動態對齊
- 社群圖卡 P1 卡片 7 加入 Max Pain 空間型態標籤（🟢 多頭強勢軋空型 / 🟡 箱體沉積結算引力型 / 🔴 恐慌避險暴跌型），與網頁版完全對齊。

---

## 🎓 GEX / VEX 全指標國中生白話懶人包

| 指標名稱 | 國中生白話比喻 | 它在看什麼？ | 實戰應用與操作指引 |
| :--- | :--- | :--- | :--- |
| **現價 (Spot)** | 👦 小明目前位置 | 大盤當前即時成交點位 | 作為一切防守距離的基準點 |
| **Call Wall** | 🧱 玻璃天花板 | 做市商賣壓最大牆位 | 大盤上漲貼近時容易漲不動 (可做 Sell Call 價差或多單停利) |
| **Put Wall** | 🛋️ 超大彈簧軟墊 | 做市商護盤最大支撐牆 | 大盤回檔跌至附近容易踩墊反彈 (可建立當沖多單或 Sell Put 價差) |
| **Zero Gamma** | ⚖️ 園區安檢紅外線 | 波動度壓抑 vs 暴跌助跌臨界點 | 站上走慢速安定區；跌破進入做市商追殺避險區 |
| **Max Pain** | 🎯 週三抽獎箱 | 散戶權利金賠最多、莊家賺最多的結算點 | 週二/週三結算前夕，指數常被主力壓回附近讓買方雙歸零 |
| **VEX (NEW)** | 😱 恐慌狂狂暴開關 | 當恐慌指數 (IV) 飆高時，做市商會護盤還是火上加油 | **負值時**代表盤中一旦急殺，做市商會無腦賣期貨火上加油！ |
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

---

## 🌟 v47.1 證交所 BFI82U 現貨三大法人買賣超校正 (對齊永豐/富邦/台新日報)

### 🏛️ 1. 證交所權威 BFI82U API 端點精確對齊
- **修復舊版覆蓋 Bug**：舊版在邏輯判斷時將 `外資自營商` 覆蓋 `外資及陸資(不含外資自營商)`，導致外資金額漏算盤後鉅額對敲交易。
- **三大法人金額 100% 零誤差對齊三大券商日報**：
  - **外資買賣超**：`外資及陸資(不含外資自營商)` (例如 `+366.13 億 TWD`)。
  - **投信買賣超**：`投信` (例如 `+33.66 億 TWD`)。
  - **自營商買賣超**：`自營商(自行買賣 + 避險)` (例如 `+179.34 億 TWD`)。
  - **三大法人合計**：`合計` (例如 `+579.13 億 TWD`)。

---

## 🌟 v47.0 Max Pain 空間籌碼結構拓撲 & 融資維持率 21:00 TWSE 清算雙軌分離

### 🧲 1. Max Pain 空間籌碼結構拓撲 (Spatial Topology Matrix)
- **動態 Badge 診斷與色彩標準 (符合台股紅多綠空)**：
  - 🔴 **型態 A：多頭強勢軋空** (`Max Pain < Put Wall`): 上方 Call OI 大量累積，近端 Put Wall 護盤，首防 Put Wall 建立 **Bull Put Spread【2腳】** (`Sell Put@Put Wall` / `Buy Put@Put Wall-200`)。
  - 🟡 **型態 B：對稱健康箱體** (`Put Wall <= Max Pain <= Call Wall`): 多空對稱，Max Pain 居中央，週三結算引力吸附，適合 **Iron Condor 雙賣鐵鷹【4腳】**。
  - 🟢 **型態 C：空頭恐慌避險** (`Put Wall << Max Pain`): 深價外 Put 避險強烈，下檔波動率升，建議 **Bear Call Spread【2腳】** 防禦或微台順勢空。
- **UI 互動與 Modal 內建教學指南**：頂部 MAX PAIN KPI 卡片新增動態 Badge 與 `🎓 拓撲診斷 ℹ️` 按鈕，單擊直達【判讀教學指南 Modal】第 4 區塊拓撲診斷對照表與 2腳/4腳精確下單 SOP。

### 📊 2. 融資維持率 21:00 TWSE 清算時序與夜盤雙軌分離
- **夜盤 Session 嚴謹分離**：個股在夜盤休市無成交價與信用交易變動，標示 `- (非交易時段)` 與 `夜盤休市無數據`。
- **日盤 Session 21:00 時序清算**：盤後 (如 16:00) 證交所尚未公布當日信用交易時，標示金黃虛線膠囊 `未公布 (21:00更新)`；晚間 21:00 或隔晨 06:00 自動補齊數字與四級燈號 (`155.8% 🟢 安定` / `個股 141.2%`)。

---

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
