# 📊 TXO GEX Dashboard — 專案現狀與版本紀錄 (v45.3)

**當前版本**：`v45.3` (2026-08-25 全套 3 張社群圖卡動態數據與 TWSE 即時現貨漲跌計算對齊版)
**資料與視覺引擎**：`scripts/fetch_and_calc_vision.py` (Black-Scholes VEX/GEX+ 引擎 v45.3)
**社群懶人圖卡生成器**：`scripts/generate_social_card.py` (4K 尋鳥品牌原創風格全動態渲染圖卡)
**系統狀態**：`✅ 100% 運作正常`
**網頁通行碼**：`GEX2026`（不區分大小寫，支援 👁️ 眼睛切換顯示）

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
- 5 日關鍵矩陣移除 `max-height` 滾動限制，完整呈現 5 行數據。

---

*最後更新：2026-08-21 最新修復版 | 尋鳥 Bluebird Finder | v44.1*

