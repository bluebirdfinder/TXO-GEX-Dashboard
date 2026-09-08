# 5K Strategy Master - 專案狀態 (Project State)

## 📌 專案概覽 (Project Overview)

本專案旨在開發一個名為「5K Strategy Master」的 TradingView Pine Script (v6) 指標。該指標基於群益期貨 151 營業員的「5K戰法」，並整合了溫哥的 1 分 K MACD 跨時區 (MTF) 停利邏輯。專為海外期貨 (指數、外匯、原物料) 的 5 分 K 短線當沖所設計。

## 📍 目前開發階段 (Current Phase)

**開發階段**: V4 雙向獨立與倉位管理階段 (V4 Independent Mode & Sizing)
**目前版本**: `v4.0` (檔案: `5K_Strategy_Master_v4.pine`)
**主要聚焦**: 多空訊號解鎖獨立運作、防雙刷機制優化、以及根據 4H 大時框自動提示倉位管理建議。

### 最近完成 (Recently Completed)

- [x] **V4 雙向獨立系統 (2026-05-10)**
  - [x] **解除多空互鎖**: 實作獨立的 `pos_long` 與 `pos_short` 狀態機，支援同時捕捉雙向訊號。
  - [x] **防雙刷機制 (Setup Age Limit)**: 自動壓制 10 根 K 棒內的反向型態，防止震盪盤被巴。
  - [x] **倉位管理建議**: 根據 4H 大時區均線狀態，自動提示「標準倉位」或「縮半倉」。
  - [x] **台股配色統一**: 全面將進出場圖示、警報與 Dashboard 統一為「多紅空綠」。
- [x] **V3 警報與多時框狀態 (2026-05-09)**
  - [x] **Telegram 通知系統**: 實作 `alert()` 動態通知，支援 Webhook 轉發。
  - [x] **MTF 均線狀態**: 抓取週、日、4H、1H、30分時框的均線狀態並加入通知。
  - [x] **市場狀態判斷**: 實作盤整/糾結與趨勢方向的自動判定。
  - [x] **加密貨幣支援**: 擴充辨識邏輯至所有 Crypto 商品，並針對 BTC 優化參數。
- [x] **V2 智能參數引擎 (2026-04-25)**
  - [x] **智能商品辨識**: 實作 `syminfo.root` 自動辨識與多品項參數覆寫。
  - [x] **Lookback Bug 修復**: 修正 V1 中 `ta.highest/lowest` 寫死的問題，套用動態回溯。
  - [x] **實戰參數觀察**: 透過 V2 智能模式進行多商品切換測試，確認參數自動給定符合預期。
- [x] **V1 核心戰法實作 (2026-04-20)**
  - [x] **5K 戰法核心邏輯**: 實作急殺/急拉偵測與局部極值判定。
  - [x] **收 K 確認機制**: 實作突破基準價且型態符合要求的進場過濾。
  - [x] **溫哥版 MTF 停利**: 實作 1 分 K MACD 交叉停利邏輯。
  - [x] **UI Dashboard**: 實作即時資訊面板。

### 待處理 / 下一步 (Next Steps)

- [ ] **實盤盲測 (V4)**: 讓使用者透過 V4 獨立模式進行多商品切換測試，觀察解除互鎖後的勝率與利潤捕捉情況。
- [ ] **停損機制升級**: 評估是否將目前的「固定極值停損」改為或加入「ATR 追蹤停損 (Trailing Stop)」。

## 🎯 開發藍圖 (Roadmap)

### 已完成階段 (Completed Phases)

- [x] **Phase 0: 需求分析與邏輯定案**
  - [x] 解析「5K戰法」圖文與影片邏輯。
  - [x] 優化「急殺/急拉」定義 (引入 ATR)。
  - [x] 確認「等收 K」高勝率進場與 MTF MACD 停利機制。
- [x] **Phase 1: 基礎版本開發 (v1)**
  - [x] 專案文件建立 (Project State, Documentation, Version History)。
  - [x] 核心邏輯實作 (極值偵測、進場、停損、停利、互鎖)。
  - [x] 靈敏度優化：將極值判定的條件從「左右各 2 根」縮短為「左右各 1 根」。
  - [x] 視覺化分離：將停損 (SL) 與停利 (TP) 徹底拆開，停損使用三角形，停利用 `＄` 符號。
  - [x] 狀態機邏輯修正：修復單邊過濾器導致的出場失效，並加入進場後冷卻機制。
  - [x] 實作 17MA / 88MA 的順勢交易濾網。
- [x] **Phase 2: 智能版本與實戰測試 (v2)**
  - [x] 實作 `Auto-Detect` 智能商品辨識與參數覆寫。
  - [x] 交付使用者在 TradingView 進行回測與觀察多商品切換。
  - [x] 根據實戰反饋微調各類商品的 ATR 乘數預設值。
- [x] **Phase 3: 警報系統與多時框狀態 (v3)**
  - [x] 實作 Telegram 通知系統與 MTF 均線狀態顯示。
  - [x] 擴充「智能商品辨識邏輯」，支援所有加密貨幣並優化 BTC 參數。
- [x] **Phase 4: 雙向獨立系統與台股配色 (v4)**
  - [x] 解除多空互鎖，實作獨立的 `pos_long` 與 `pos_short` 狀態機。
  - [x] 引入 Setup Age 壓制機制防止雙刷。
  - [x] 加入倉位管理建議，並將視覺配色統一為台股習慣 (多紅空綠)。

### 進行中與待辦階段 (Active & Future Phases)

- [ ] **Phase 5: 功能擴充 (視需求)**
  - [ ] 根據 V4 實戰反饋微調 Setup Age 預設值 (目前 10 根)。
  - [ ] 評估是否加入「ATR 追蹤停損 (Trailing Stop)」。

## 📋 待辦事項 (To-Do List)

- [x] 撰寫 `5K_Strategy_Documentation.md`。
- [x] 撰寫 `5K_Strategy_Version_History.md`。
- [ ] 持續優化 `5K_Strategy_Master_v4.pine` 程式碼穩定性。
- [ ] 實戰回饋收集與調整。

## 📁 相關檔案 (Related Files)

*   **README.md**: GitHub 導讀文件。
*   **腳本目錄**: `c:\Users\mingi\OneDrive\文件\TradingView 指標\我寫的指標\5K戰法\`

- **參考資料**: `5K戰法說明.txt`, `5K戰法 - 影片一.mp4`, `5K戰法 - 附圖一.jpg` (位於 OneDrive)
