# 📊 TXO GEX Dashboard — 專案現狀與版本紀錄 (v50.5)

**當前版本**：`v50.5` (2026-09-03 台指選擇權造市商 21 章量化實戰手冊與 Covered Call 完全體版)
**資料與視覺引擎**：`scripts/fetch_and_calc_vision.py` (Black-Scholes VEX/GEX+ 引擎 v50.5)
**即時報價網關**：`scripts/fubon_api_provider.py` & `scripts/live_price_server.py` (WebSocket Fubon Gateway v50.5)
**系統狀態**：`✅ 100% 運作正常`
**網頁通行碼**：`GEX2026`（不區分大小寫，預設自動通關解鎖）

---

## 🎯 v50.5 核心更新亮點 (21-Chapter Options Quant Playbook & Covered Call)

### 🦅 1. 21 大章節造市商量化操盤手冊全面收錄
- **獨立 Markdown 策略手冊產出**：自動導出 `docs/OPTIONS_QUANT_PLAYBOOK.md`，方便隨時傳入 Lumi 機器人進行策略建構與自動化回測。
- **線上儀表板即時彈窗**：點擊 `Card 9` 頂部 `📖 VIX 教學` 即可隨身查閱 1 ~ 21 章完整圖文。
- **跨資產 Covered Call 4 大機構級變形**：PMCC、動態 Delta 避險、Covered Straddle、Ratio 慢牛流。
- **輝哥 100% 現貨本位不開槓桿週週收息**：231 萬資金配置、週三/週一雙節奏收息、拆單 2:3 階梯防現貨被廉價收購。
- **兩階段修煉全圖譜**：階段一固定 5 口微台收租流 ➔ 階段二 VIX 動態 Delta 自動避險對沖流。

### 🤖 2. 方案 B：本週重大市場焦點週報全自動排程引擎
- 實作 `generate_dynamic_weekly_focus` 演算法，根據目前日期動態界定每週一至週五交易時段，自動識別重大總經事件與對應股票期貨標的。

### ⚡ 1. 近 5 日關鍵市場指數與 GEX 結構歷程矩陣：新增 `⚡ VIX 恐慌 (台/美)` 欄位
- 於 5 日歷史表格新增 `⚡ VIX 恐慌 (台/美)` 專屬欄位，完整追蹤過去 10 個日夜盤台指 VIX 與美股 ^VIX 動態演變與恐慌級別。

### 📌 2. 日夜盤微觀結構速報：整合 VIX 實時恐慌警報
- 在即時多空位移判定中，融合 VIX 指數評級與做市商避險狀態，給出買賣方具體防守指引。

### 🛠️ 3. 網頁 HTML DOM 結構修復與 0ms 秒開優化
- 修復 `index.html` 未閉合標籤與 Modal 預設隱藏，解決全螢幕遮罩問題。

### 📅 1. 富邦期貨本週市場焦點 (Fubon Weekly Market Focus 2026.08.31 - 09.04)
- **事件與股票期貨標的對應**：
  - `8/31 (週一)`：MSCI 季度調整 ✕ 載板（欣興 3037 / 景碩 3189 / 南電 8046）、記憶體（華邦電 2344 / 旺宏 2337 / 南亞科 2408）股票期貨。
  - `9/01 (週二)`：ISM 製造業指數 ✕ MNQ 微型那指期貨 / MES 微型標普期貨。
  - `9/02 (週三)`：半導體展 (9/2-9/4) ✕ 戴爾 (Dell) 財報 ✕ 設備股（弘塑 3131 / 辛耘 3583 / 萬潤 6187）、AI伺服器（鴻海 2317 / 廣達 2382 / 緯創 3231）股票期貨。
  - `9/03 (週四)`：ISM 非製造業指數 ✕ 博通 (Broadcom)/HPE 財報 ✕ MNQ 微型那指、ASIC（世芯-KY 3661 / 智原 3035 / 創意 3443）股票期貨。
  - `9/04 (週五)`：美國 8 月非農就業 (NFP + 失業率) ✕ MNQ / MES 微型期貨。

### 🚨 2. 防護雷達動態卡片渲染 (`app.js`)
- 在頂部防護雷達新增本週市場焦點網格區塊，將富邦期貨每週重點與股票期貨對照標的動態渲染給交易者參考。

---

### ⚡ 1. 台指 TAIFEX VIX ✕ 美股 CBOE VIX (`^VIX`) 雙軌數據引擎 (`scripts/fetch_and_calc_vision.py`)
- **多源即時對接**：自動串接期交所 vixMinNew / getVixData 抓取台指 VIX（最新 `26.09` / `+1.17`），並透過 Yahoo Finance API 無縫對接美股 CBOE VIX（`16.10` / `-0.24`），根目錄 Payload 封裝 `vix_info` 導出至 `gex_data.json` 與 `embedded_data.js`。

### 🟢🔵🟡🔴 2. 波動率四級市場狀態評級與燈號
- **自動評判燈號**：根據台指 VIX 自動劃分：🟢 極度平靜 (`<14.0`) / 🔵 常態溫和 (`14.0~18.0`) / 🟡 恐慌升溫 (`18.0~22.0`) / 🔴 極度恐慌 (`>22.0`)，並給出做市商對沖與買賣方策略指引。

### 📊 3. Card 9: VIX 恐慌指數 & 美股 ^VIX 核心數據卡片 (`index.html` & `app.js`)
- **頂部雙軌卡片**：於儀表板 `.summary-grid` 新增第 9 張核心數據卡片，完美呈現日盤台指 VIX、夜盤美股 VIX、變動幅與恐慌燈號徽章，提供一鍵點擊 `📖 VIX 教學` 鈕開啟實戰手冊。

### 📖 4. 互動式教學彈窗 (`vix-modal`)
- **完全量化對策手冊**：收錄 VIX 白話原理、選擇權權利金定價關聯、數值對照表以及 **GEX ✕ VIX 雙指標實戰共振矩陣**（情境 1 正 GEX 鎖區間 / 情境 2 負 GEX 破牆防守 / 情境 3 恐慌極致 + VIX 衝高轉折正金字塔爆賺點）。

### 📸 5. 2K 盤後社交圖卡引擎同步渲染 (`scripts/generate_social_card.py`)
- **P1 圖卡升級**：P1 盤後總覽 1:1 方形圖卡注入 VIX 指標看板。

---

### ⚡ 1. 頂部連線狀態標籤閃爍跳動熱修復 (Status Pill Anti-Flicker Fix)
- **連線鎖定旗標**：修復 `app.js` 中 `updateMarketTradingStatus()` 每 2 秒強制重洗狀態文字與 `handleLiveTick()` 傳入 `provider_name` 互相搶奪蓋掉標籤文字的衝突，補齊 `feedText.dataset.hasLiveSocket = 'true'` 連線鎖定旗標。

### 📈 2. Zero Gamma 與 GEX+ Flip 即時計算複利累加漂移修復 (Zero Gamma Accumulation Drift Fix)
- **消除重複扣血**：解決高頻 Tick（富邦 API WebSocket / HTTP 輪詢）觸發時，`liveZg` 不斷在已修改過的 `gexData.zero_gamma_level` 上重複加減價格價差的複利累加 BUG（避免點位一路扣至 `-24,436.6` 等無窮負數點）。
- **靜態凍結記憶體**：引入 `_base_zero_gamma` 與 `_base_gex_plus_flip` 靜態凍結記憶體，確保實時點位算式精準依據官方日/夜盤結算點位進行單次動態校正。

### 🛡️ 3. GEX 圖表 Y 軸防爆邊界保護網 (Plotly Chart Safety Bounds Guard)
- **Plotly 刻度保護**：針對 `renderGEXChart()` 增加 `> 10000` 數值門檻防護，避免異常點位破壞 Plotly Y 軸（履約價 Strike）刻度，確保履約價柱狀圖與線型絕不擠壓變形。

---

## 🎯 v49.3 歷史更新紀錄（Multi-Tier Stock Spot Price Fallback & Passcode Auto-Bypass）

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

## 🎯 v49.1 核心更新亮點（Dynamic 4-Phase Session Architecture & Night Stock Futures API）

### 🕒 1. 動態 4 階段 Session 時段配對架構 (4-Phase Dynamic Session Architecture)
- **時段感知與 GEX 點位嚴格配對**：重構行情判定邏輯，自動劃分 `DAY_LIVE` (日盤盤中 08:45~13:45)、`DAY_SETTLED` (日盤定案 13:45~15:00)、`NIGHT_LIVE` (夜盤盤中 15:00~05:00) 及 `NIGHT_SETTLED` (夜盤定案/週末休市) 4 大階段。
- **點位與警告動態連動**：標的物價格 (`active_price`) 嚴格配對當前階段之 Zero Gamma (`zg`)、Call Wall (`cw`)、Put Wall (`pw`) 與 Max Pain (`mp`)，實時觸發「Put Wall 跌破 (46,100 點失守) 向下尋求 Max Pain (45,700 點) 磁吸防守」之警示。

### 🌙 2. 期交所官方 6 大夜盤個股/ETF期貨 API 直連 (`marketCode=1`)
- **直連 TAIFEX 夜盤 API**：直接串接台灣期貨交易所官方夜盤行情 API (`futDailyMarketExcel?marketCode=1`)，精準抓取 6 大夜盤標的：台積電期 (`2330`)、小型台積期 (`2330F`)、聯電期 (`2303` CCF 夜盤定案 `127.00`)、元大台灣50期 (`0050`)、小型50期 (`0050F`) 及元大美債20年期 (`00679B`)。
- **現貨價與期貨價劃分 (真實期現價差 Basis)**：保留 TWSE 日盤現貨收盤價 (如聯電現貨 `130.00`) 與 TAIFEX 夜盤期貨定案價 (聯電期 `127.00`)，真實驗算並渲染最新夜盤逆價差 (`-3.00 點`)。

### 🏛️ 3. TWSE 信用交易融資維持率 API 實時動態連線 (`fetch_twse_margin_maintenance`)
- **實時 API 抓取與日期感知**：數據引擎連線 TWSE 統計 API，當證交所完成盤後清算（約 20:30），自動轉為 `is_published = True` 並寫入當日大盤融資維持率 (`160.6% 🟢 安定`) 與個股維持率 (`145.9%`)。

### 🚀 4. 常駐防錯發布 SOP 規則 (`.agents/rules/VERSION_RELEASE.md`)
- **常駐 SOP 規則**：建置 `.agents/rules/VERSION_RELEASE.md` 自動常駐規則，規範版號變更時必須於 commit 前立即重跑腳本重繪 Payload，徹底消除版號跳動問題。

---

### 🛡️ 1. TWSE 現貨指數多源熱備援機制 (`scripts/fetch_and_calc_vision.py`)
- **多層級熱備援抓取 (Multi-Tier Fallback)**：重構 `fetch_twse_realtime_indices()`，依序嘗試 TWSE MIS API ➔ Yahoo Finance 全球 API (`^TWII` 加權 / `^TWOII` 櫃買) ➔ 本地 `gex_data.json` 快照，徹底解決 GitHub Actions 國外 IP 遭 TWSE 阻擋降級成舊值 `45811.01` / `400.95` 的硬碼問題。加權現貨精準為 `46,331.45 (+356.23)`，櫃買指數為 `402.83 (+2.45)`。
- **現貨漲跌幅實時動態渲染**：清理 `index.html` 寫死之 `+3,186.45` 硬碼字串，於 `app.js` 加入 `#stat-spot-sub` 與 `#stat-otc-sub` 的動態點數與 % 渲染（隨行情實時調色）。

### 📊 2. 5 日歷程矩陣 T-1 前一交易日收盤價真實比對
- **廢除偽造歷史公式 (`spot_price - 74`)**：歷史 10 盤對齊真實前一交易日現貨收盤價 (`prev_day_spot = spot_price - spot_change`)，讓矩陣真實算出 `(+356.23)` 點與 `(+2.45)` 點，解決手動提早或多次觸發腳本時顯示偽造 `(+74.00)` 點之錯誤。

### ⏰ 3. GitHub Actions 補齊 21:00 TWD 融資維持率定時排程 (`auto_update.yml`)
- **新增 21:00 / 21:30 TWD 自動定時抓取**：於 `.github/workflows/auto_update.yml` 加入 `- cron: '0 13 * * 1-5'` (21:00 TWD)，在證交所每晚 21:00 公布「大盤整戶融資維持率」時自動補齊數據。
- **盤後定案保護**：夜網與 21:00 抓取時安全維護 15:30 盤後已定案之 GEX Profile 與三大法人籌碼，不重算或干擾 15:30 基線。

### ⚡ 4. 全站版本號 100% 對齊 (消除重整瞬間 V49 閃跳 V48.2)
- **前後端版本一致**：將 `scripts/fetch_and_calc_vision.py` 的 `ENGINE_VERSION` 提升為 `"v49.0"`，並重新產生 `data/gex_data.json` 與 `data/embedded_data.js`，解決 HTML 標籤 (`v49.0`) 與 JS 讀取數據 (`v48.2`) 不一致導致的重整閃爍現象。

---

## 🎯 v49.0 社群圖卡與吸粉專區亮點 (IG & Threads QR Code Follow Engine)

### 📱 1. 獨立高解析度 QR Code 自動生成器 (`scripts/generate_qr_codes.py`)
- **雙平台高對比度 QR Code**：自動產出高解析度、高對比、相容所有手機鏡頭與第三方 APP 秒讀之 Instagram (`assets/qr_instagram.png`) 與 Threads (`assets/qr_threads.png`) 專屬黑金科技風 QR Code。
- **QR Code 下方標示官方 ID (`@bluebird_finder`)**：於生成之 QR Code 圖檔、1:1 社群懶人圖卡與 Web 儀表板頁尾清楚標示 `IG: @bluebird_finder` 與 `Threads: @bluebird_finder`。

### 📸 2. 1:1 正方形社群懶人圖卡頁尾整合 (`scripts/generate_social_card.py`)
- **雙平台 QR Code 吸粉專區**：在每張每日自動生成發布之 1080x1080 圖卡（Card 1/2/3）頁尾加入雙平台 QR Code、官方 ID 標籤與吸粉文案：`📲 掃碼追蹤「尋鳥 Bluebird Finder」 | 每日即時盤中籌碼速報與做市商 GEX 轉折關卡`。

### 🌐 3. Web Dashboard 導覽列與頁尾吸粉卡片 (`index.html` & `style.css`)
- **頂部 Nav 按鈕**：新增 `📱 追蹤社群 (@bluebird_finder)` 亮眼按鈕，點擊可平滑滾動至頁尾社群專區。
- **頁尾吸粉卡片**：在頁尾版權宣告前增設大器美觀的 `social-follow-card` 專區，展示雙平台 QR Code、官方 ID 與一鍵開啟連結按鈕。

---

## 🎯 v48.1 核心更新亮點（Macro Catalysts & Settlement Live Risk Radar）

### 🚨 1. 國際總經、富台/MSCI 甩尾與期權結算日 實時避險雷達 (`#macro-events-radar-panel`)
- **完整納入關鍵大事件**：包含 **週/月台指選結算**、**SGX 富台指期貨結算**、**MSCI 季度/半年度尾盤爆量甩尾調整**、**美大非農 (NFP) + 失業率**、**美 ADP 小非農**、**美每週初領失業金 (Jobless Claims)**、**美 CPI 通膨數據** 與 **FOMC 利率決議**。
- **與 Lumi Telegram 機器人 v48.1 雙型態對齊 (`pattern_type`)**：
  - **`POINT_TIME` (定點數據型)**：美 CPI、大非農 NFP、ADP、初領失業金，告警提示發布前 15~30 分鐘流動性抽離與劇烈刷洗。
  - **`WINDOW_TIME` (視窗洗盤型)**：週/月選結算 (13:30)、富台指結算 (13:45)、MSCI 甩尾 (13:25)，告警提示尾盤 13:25~13:30 爆量擺盪。
- **事件專屬客製化提早預警時間窗 (Tailored Lead Warning Windows)**：
  - 各事件具備獨立 `warning_lead_hours` (黃色警戒時數) 與 `critical_lead_mins` (紅色告急分鐘數)。
  - 重磅總經與月結算採 24h 警戒 / 120m 告急風暴閃爍；小數據採 6h 警戒 / 30m 告急。
- **美股夏冬令時間 (EDT/EST) 與台灣時間 (UTC+8) 自動校正**：顯示時間全標註 `(台灣時間)`。

---

### 🌙 1. 官方 6 大夜盤股期/ETF期 即時價量關係與指標導航 (`app.js`)
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

## 🎯 v47.9 核心更新亮點（Night Session Close Calibration & Schedule Timezone Precision）

### 🌙 1. 台指期夜盤 (TXF) 定案收盤價與 GEX 全套結構動態校正 (`fetch_and_calc_vision.py`)
- **夜盤收盤價校正至 46,388**：將台指期夜盤結算收盤價校正至期交所官方 05:00 定案值 46,388 點（取代盤中未收盤暫存價 45,993 點）。
- **GEX 籌碼結構與牆位全面聯動**：標的基準價變更同步引發 Call Wall (46,700 / 46,200), Zero Gamma (46,517.9 / 46,017.9), Put Wall (46,300 / 45,800), Max Pain (45,900 / 45,400) 與 P/C Ratio 全動態黑體算式精確重計算。
- **自動排程與時區邊界防錯 (`scripts/fetch_and_calc_vision.py`)**：
  - 優化夜盤視窗判定邏輯 `(3 <= now_hour < 12)`，確保清晨凌晨 03:00 起的自動或手動觸發皆能精確捕捉夜盤數據。
  - 明確規範 GitHub Actions UTC 排程時區對齊（例：UTC 21:30 = 台灣時間 05:30 AM），防止未收盤即過早發布報告。
- **全站靜態資源版本標籤 (`?v=v47.9`)**：在 `index.html` 內所有的 CSS/JS/Data 標籤更新為 `?v=v47.9` 防快取。

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
- 社群圖卡 P1 卡片 7 加入 Max Pain 空間型態標籤（🔴 痛點沉底/下檔磁吸型 / 🟡 箱體沉積結算引力型 / 🟢 恐慌避險暴跌型），與網頁版完全對齊。

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

### 🧲 1. Max Pain 4 大空間幾何拓撲 ✕ 3 大籌碼強度 二維共振實戰矩陣 (Spatial Topology Matrix)
- **4 大空間幾何拓撲動態 Badge 與色彩標準**：
  - 🔴 **型態 A：痛點沉底 / 懸空防守拓撲** (`Max Pain < Put Wall < Call Wall`): 市場最大痛點沉在低檔，近端 Put Wall 建立防守線。若籌碼偏多 (Level +1/+2) 為踩牆軋空；若籌碼偏空 (Level -1/-2) 則 Put Wall 脆弱，一旦跌破將順勢被下方 Max Pain 引力磁吸加速下殺！
  - 🟡 **型態 B：對稱健康箱體** (`Put Wall <= Max Pain <= Call Wall`): 多空對稱，Max Pain 居中央，週三結算引力吸附，適合 **Iron Condor 雙賣鐵鷹【4腳】**。
  - 🟢 **型態 C：恐慌避險 / 下檔開天窗** (`Put Wall << Max Pain ≈ Call Wall`): 深價外 Put 避險強烈，下檔支撐真空開天窗，波動率升，建議 **Bear Call Spread【2腳】** 防禦或微台順勢空。
  - 🚀 **型態 D：極端軋空 / 痛點頂天** (`Put Wall < Call Wall < Max Pain`): 市場大額 Put 累積極重將痛點推至天際超越 Call Wall，做市商面臨雙重 Gamma 擠壓，引爆主升段飆漲軋空。
- **12 種二維共振實戰矩陣 (空間幾何 ✕ 籌碼強度 Level)**：
  - 徹底解決「大跌行情卻死板判定多頭軋空」的認知矛盾，在 UI Badge、Tooltip 與 Modal 診斷表格中提供 12 種全情境精確 SOP 指引（如 A1 踩牆軋空、A3 假支撐磁吸下殺、C1 恐慌 V 轉、C3 順風避險大崩盤、D1 歷史級破裂軋空等）。

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

