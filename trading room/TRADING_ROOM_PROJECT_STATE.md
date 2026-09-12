# 🦅 尋鳥戰情交易室 (Bird Trading Room) 全面檢修與升級 Implementation Plan

本文件為 **尋鳥戰情交易室 (`room.html` / `room.js` / `room.css`)** 之全方位自檢 (Self-Audit)、指標對照、資料管線串接、UI/UX 版面優化與商業化升級實作計畫。

---

## 📌 專案定位與發展目標

1. **Phase 1 (當前階段)**：本人與表哥專用實戰操盤戰情室（台指期/選擇權組單、高精確度、零幻覺、實體 TV 指標對齊）。
2. **Phase 2 (測試階段)**：股友露米 (Lumi) 實盤測試，整合 Lumi 選擇權策略知識庫與 VVIX 避險模型。
3. **Phase 3 (商業化階段)**：開放會員註冊訂閱、權限分級、雲端即時運算推播與多模態 AI 量化軍師。

---

## 🔍 一、戰情室 14 大核心需求 Self-Audit 與根因分析

| 項次 | 需求模組 | 目前現狀與 Bug 根因 | 解決與重構方案 |
| :--- | :--- | :--- | :--- |
| **1** | **商品切換 (8大標的)** | 切換時僅換名稱與基底價，K棒為合成亂步 (Random Walk)，非真實走勢 | 串接 Yahoo Finance / 富邦 API / TAIFEX MIS 抓取真實 OHLC 歷史 K 棒與當日即時報價 |
| **2** | **時間框架切換 (10個TF)** | 按鈕切換時重跑隨機模擬，無法對應真實分K數據 | 建立多時區真實數據快取聚合器 (1M/3M/5M/15M/30M/1H/4H/1D/1W/1M) |
| **3** | **TV 主圖真實性** | Lightweight Charts 上繪製之訊號為亂數產生，與 TV 實盤脫節 | 嚴格按 Pine Script 演算法用 JS 100% 復刻，杜絕隨機生成 |
| **4** | **附圖 MACD & CCI** | 數值由隨機 K 棒算得，且 CCI 通道轉折標記無冷卻過濾 | 依真實 K 棒計算標準雙層 MACD (4色柱) 與 CCI(20) 買賣極值點 |
| **5 & 7** | **動能附圖：ADX Pro V3 (刪 DMI)** | 原 DMI 傳統三線過於雜亂，缺乏 4 態突破與頂底背離 | **徹底移除 DMI**，完整植入昨天開發好的 `ADX Pro V3`（雙色主線、4色突破標籤、背離、MTF看板） |
| **6** | **指標來源對齊** | 過去指標分散，未嚴格對齊老墨 XQ 與 TV 原始 Pine 檔 | 建立指標代碼對照庫，直接從 `我寫的指標\老墨 XQ 指標\` 資料夾讀取算法與參數 |
| **8** | **指標庫 & 選股雷達按鈕** | `room.js` 遺漏事件監聽器，點擊後 Modal 無反應 | 補齊 `open-indicator-settings-btn` 與 `btn-open-screener` 監聽邏輯與 Modal 互動 |
| **9** | **大戶散戶動能指標** | TV 無法取得台灣籌碼，網頁端目前僅有靜態骨架 | 串接期交所即時大台/小台/微台三大法人未平倉與成交口差，網頁即時動態運算 |
| **10** | **Smart Mansfield RS** | 尚未實作 | 依 `Smart_Mansfield_RS_v1.pine` 預留 RS 比較副圖與多標的切換介面 |
| **11** | **附圖分類結構** | 垂直排列過長，Chrome 100% 需頻繁滾動 | 將附圖模組化分類（動能類、震盪類、籌碼類、強度類），支援分頁與摺疊 |
| **12** | **版面與 GEX 重複** | 頂部與左側同時顯示 GEX 點位造成視覺冗餘；高度超出版面 | 移除右上角重複的 GEX 點位；重新調整 CSS Flex/Grid，確保 100% 縮放無滾動條 |
| **13** | **左右收合 + AI 軍師 2.0** | 左右側無收合功能（手機版擁擠）；AI 軍師為靜態範本，不支援圖片 | 實作左右側 1/4~1/5 伸縮抽屜；AI 軍師支援**文字 + 圖片截圖上傳**，對接 Gemini 2.5 API |
| **14** | **🔥 GEX 主圖即時更新與標的過濾** | 過去 GEX 只在左側顯示，未動態投射到主圖，且全商品混亂 | **自動在主圖繪製 GEX 5大防線與 TV 觸碰訊號**；**限定僅在 TXF (大台) / MXF (小台) / MTX (微台) 出現**，切換到加權、台積期、美債、DXY 等自動隱藏！ |

---

## 🛡️ 二、GEX 主圖即時渲染與標的限定規格 (對齊 bluebird_finder_GEX.pine)

依據 `C:\Users\mingi\OneDrive\文件\TG 自動化機器人\露米籌碼監控機器人\TradingView 指標\bluebird_finder_GEX.pine` 實作：

```mermaid
flowchart TD
    AssetCheck{當前切換之商品？}
    AssetCheck -->|TXF / MXF / MTX (台指/小台/微台)| ShowGEX[啟用 GEX 主圖疊加層]
    AssetCheck -->|加權/櫃買/台積期/美債/DXY/CL/個股期| HideGEX[完全隱藏 GEX 防線與訊號標籤]

    ShowGEX --> CalcLevels[取得當前 GEX 5 大點位]
    CalcLevels --> DrawLines[繪製 5 條水平防線 + 右側 Price Scale]
    DrawLines --> Line1[🔴 Call Wall: 天花板阻力]
    DrawLines --> Line2[🟠 VEX Early: 早鳥轉折警戒]
    DrawLines --> Line3[⚡ Zero Gamma: 做市商變盤點]
    DrawLines --> Line4[🟢 Put Wall: 地板支撐牆]
    DrawLines --> Line5[🔵 Max Pain: 結算引力位]

    ShowGEX --> SignalCheck[K 棒即時穿透偵測]
    SignalCheck -->|Close 向上突破 Call Wall| SigCW[📈 Call Wall 突破 標籤]
    SignalCheck -->|Close 向下跌破 VEX Early| SigVEX[🚨 VEX 早鳥轉折 標籤]
    SignalCheck -->|Close 向下跌破 Put Wall| SigPW[📉 Put Wall 跌破 標籤]

    ShowGEX --> FloatingBox[浮動防線資訊框 Floating Legend]
```

### 1. 標的顯示過濾規則 (Strict Asset Scope)
```javascript
const GEX_SUPPORTED_ASSETS = ['TXF', 'MXF', 'MTX', 'TMF'];

function updateGexChartOverlay(symbol) {
  const isSupported = GEX_SUPPORTED_ASSETS.includes(symbol);
  if (!isSupported) {
    clearGexPriceLinesAndMarkers();
    return;
  }
  renderGexPriceLines();
  detectAndRenderGexBreakoutMarkers();
}
```

### 2. TV 級訊號標籤與視覺呈現
1. **防線線條**：
   - `Call Wall`：顏色 `#FF76AC`，LineWidth 2，樣式 Solid。
   - `VEX Early`：顏色 `#FFA726`，LineWidth 1.5，樣式 Dashed。
   - `Zero Gamma`：顏色 `#FFEB3B`，LineWidth 2，樣式 Solid。
   - `Put Wall`：顏色 `#26A69A`，LineWidth 2，樣式 Solid。
   - `Max Pain`：顏色 `#42A5F5`，LineWidth 1，樣式 Dotted。
2. **K 棒圖示標記 (On-Chart Touch Visual Signals)**：
   - 突破 Call Wall：`📈 Call Wall 突破`（向上綠/紅色標籤，隨 K 棒自動定位）。
   - 跌破 VEX 早鳥：`🚨 VEX 早鳥轉折`（向下橘色警告標籤）。
   - 跌破 Put Wall：`📉 Put Wall 跌破`（向下紅色警示標籤）。
3. **智慧防重疊浮動標籤 (Floating Box)**：
   - 當 $|VEX - ZG| < 15$ 點時，自動合併顯示為 `⚡ ZG / 🟠 VEX: 46,220.1`，避免文字重疊。

---

## 📊 三、老墨 XQ / TV Pine 指標體系對照與分類表

依據 `C:\Users\mingi\OneDrive\文件\TradingView 指標\我寫的指標\老墨 XQ 指標\` 之完整架構：

```
老墨 XQ 指標體系
├── 01. 總體環境觀測 (Macro) ── 大盤融資維持率、風險偏好性 (Risk-On/Off)、VIX/VVIX
├── 02. 基本面觀測 (Fundamental) ── 本益比通道 (PE Bands)
├── 03. 技術面觀測 (Technical) ── SUPER TREND PRO MAX、雙重颱風 K 線、EXCEED CHARGE 充能爆發、RS STRONGER、AVWAP
├── 04. 籌碼面觀測 (Chips - 網頁特有) ── 分點力度指標、法人力度 (投本比)、大戶散戶動能、期權大額交易人
├── 05. 事件面觀測 (Events) ── 結算週期倒數、除權息
└── 06. TradingView 移植版 ── ADX Pro V3、Smart Mansfield RS Pro、Squeeze Momentum
```

---

## 🔥 四、ADX Pro V3 (adx_dual_color_v3.pine) 規格定義

嚴格復刻 `adx_dual_color_v3.pine` 之算法與視覺樣式：
1. **主線粗細**：LineWidth = 2.5，動態漸變雙色/四色（<20 綠色打底、20~30 紫色動能、30~50 金橘爆發、>50 深紅極端）。
2. **背景雲帶 (Cloud Fill)**：ADX 主線與 20 基準線之間的半透明填色。
3. **4 條基準警戒線**：`20` (灰虛)、`30` (紫虛)、`50` (橘虛)、`75` (紅實)。
4. **4 態突破標籤**：🔥真突破 (紅)、❄️真跌破 (藍)、⚠️假突破/假跌破 (灰)。
5. **背離標籤**：▼頂背離 (綠標籤)、▲底背離 (紅標籤)。
6. **MTF 看板**：15M / 1H / 4H / 日 狀態燈號。

---

## 🏛️ 五、大戶散戶動能指標：期交所即時數據需求

1. **盤中 MIS 即時串流**：`https://mis.taifex.com.tw/futures/api/getQuoteList`（大台/小台/微台即時成交量與委託口數）。
2. **三大法人每日契約**：`futContractsDateAh` (夜盤) / `futContractsDateExcel` (日盤)（外資、投信、自營商的多空未平倉淨額）。
3. **散戶代理模型**：
   $$\text{全市場小台未平倉} - \text{三大法人小台未平倉} = \text{散戶小台留倉}$$
   $$\text{散戶多空比} = \frac{\text{散戶多單} - \text{散戶空單}}{\text{散戶總未平倉口數}} \times 100\%$$

---

## 🤖 六、AI 量化軍師 2.0 規格（多模態 + Gemini 2.5）

1. **多模態截圖上傳**：支援直接貼上 (`Ctrl+V`) 盤面截圖或選擇權持倉對帳單。
2. **Gemini 2.5 Flash / Pro 視覺分析**：辨識 K 棒型態、DeMark 9★ 竭盡點、持倉未實現損益。
3. **知識庫與風控注入**：`AGENTS.md` 4 大紅線（嚴禁週選拆單、嚴禁暴衝追價、實盤與模擬 100% 區隔、盤中嚴禁讀盤後 Excel）+ Lumi 選擇權實戰策略庫。

---

## 🖥️ 七、UI/UX 版面重構方案

1. **左右伸縮抽屜 (Collapsible Sidebars)**：左側面板 ◀ 收合，右側 AI 軍師 收合 ▶，手機版以 Drawer 彈出。
2. **視窗適應 (No-Scrollbar at 100% Zoom)**：移除頂部重複 GEX，圖表區 `calc(100vh - header_height)` 自適應。

---

## 🚀 八、分階段實作 Roadmap

- [x] 修復「指標庫與參數設定」與「選股雷達」按鈕與 Modal 監聽。
- [x] 實作左右側面板伸縮收合功能 (CSS + JS Toggle，支援 Alt+1 / Alt+2)。
- [x] 移除頂部重複 GEX 點位，調整 Chrome 100% 視窗排版與 0 滾動條。
- [x] **實作 GEX 主圖即時疊加層**：5 大防線、TV 級觸碰突破/跌破標籤、浮動資訊框，並設定**僅在 TXF/MXF/MTX 顯示，其他商品自動隱藏**。

### Phase 1: 基礎版面重構 (已完成 ✅)
- [x] 移除右上角重複 GEX 點位，修復主圖覆蓋問題。
- [x] 附圖 4 移除 DMI，更換為 ADX Pro V3。
- [x] 修復指標庫設定 Modal、選股雷達 Modal 事件監聽。
- [x] 修復左右兩側抽屜式 1/4 伸縮收合。

### Phase 2: GEX 主圖即時繪製 (已完成 ✅)
- [x] 移植 `bluebird_finder_GEX.pine` 演算法。
- [x] 繪製 Call Wall / Put Wall / Zero Gamma / VEX / Max Pain 水平線與 Price Line。
- [x] 限制僅在 TXF / MXF / MTX 顯示，切換到其他標的自動隱藏。

### Phase 3: 多商品與多時區真實 K 線數據管線 (已完成 ✅)
- [x] 徹底拔除布朗運動隨機擬合，直連 TWSE/TAIFEX/Yahoo Finance 官方 API。
- [x] 嚴格區分「指數/殖利率 Volume: 0」與「期貨/個股真實成交量與 Volume MA 5/10」。
- [x] 支援 8 大核心商品 + 2,400 檔個股與 10 個 Timeframe (1M~1Mth)。

### Phase 4: 老墨/陳玠儒原創籌碼與 ADX Pro V3 面積雲帶 (已完成 ✅)
- [x] 副圖 4 繪製陳玠儒/老墨原創之價量籌碼累積量能柱 ✕ 亮黃大戶線 ✕ 散戶線。
- [x] 雙色 ADX Pro V3 面積雲帶與 26.65 頂部、22.37 突破、11.63 打底門檻對齊。

### Phase 5: AI 軍師 2.0 (多模態截圖 + Gemini 2.5 Flash) (已完成 ✅)
- [x] 戰情室右上角 `🔑 Key` 支援本地安全保存獨立 API Key（享每日 1,500 次獨立免費額度）。
- [x] 直連 Google Gemini 2.5 Flash 多模態 REST API。
- [x] 支援 `Ctrl+V` 貼上券商對帳單/圖表截圖，即時進行形態辨識與真金白銀部位診斷。
- [x] 注入 `AGENTS.md` 風控最高鐵律（週選嚴禁拆單、暴衝不追價、真金白銀持倉試算）。
- [x] 股號搜尋引擎全面支援鍵盤 `Enter` 鍵直接切換與 ↑/↓ 方向鍵導航。
- [x] 注入 AGENTS.md 4 大最高風控鐵律與即時部位體檢試算。
- [ ] 串接雲端 Gemini 2.5 視覺多模態 API。
