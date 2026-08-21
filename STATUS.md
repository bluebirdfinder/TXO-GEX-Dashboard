# 📊 TXO GEX Dashboard — 專案現狀與版本紀錄 (v45.1)

**當前版本**：`v45.1` (2026-08-22 全套社群圖卡批次下載與 Modal 預覽增強版)
**資料與視覺引擎**：`scripts/fetch_and_calc_vision.py` (Black-Scholes VEX/GEX+ 引擎 v45.0)
**社群懶人圖卡生成器**：`scripts/generate_social_card.py` (4K 尋鳥品牌原創風格圖卡)
**系統狀態**：`✅ 100% 運作正常`
**網頁通行碼**：`GEX2026`（不區分大小寫，支援 👁️ 眼睛切換顯示）

---

## 🎯 v45.1 核心更新亮點（Multi-Card Download & Social Modal Release）

### 📸 全套 3 張 IG/Threads 社群圖卡一鍵批次下載與 Modal 彈窗
- **全套 3 張完整支援**：同時提供 P1 盤後籌碼總覽、P2 GEX 雙向對沖牆、P3 板塊資金輪動全套 1080x1080 黃金比例社群圖卡。
- **🚀 一鍵下載全部 3 張 PNG**：徹底解決原先僅能下載第一張圖卡之限制，順序觸發全套圖片下載。
- **📦 打包下載 ZIP 壓縮包**：整合 `JSZip` 引擎打包產出 `Bluebird_Finder_GEX_Social_Cards.zip`，完美避開瀏覽器多圖下載攔截機制。
- **🖼️ 1:1 縮圖即時預覽與單圖獨立下載**：專屬 Modal 視窗提供 3 張圖卡高畫質縮圖與個別獨立下載按鈕。

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

