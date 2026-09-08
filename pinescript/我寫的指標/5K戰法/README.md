# 5K Strategy Master - 專業海外期貨短線指標系統 (V4.1)

![TradingView](https://img.shields.io/badge/Platform-TradingView-blue)
![Pine Script](https://img.shields.io/badge/Language-Pine%20Script%20v6-orange)
![Version](https://img.shields.io/badge/Version-4.1-red)

本專案是一個基於 **5K 戰法** 核心邏輯開發的高級 TradingView 指標系統，專為海外期貨（指數、黃金、原油、外匯）與加密貨幣的 5 分鐘時框短線交易設計。

## 🚀 核心亮點

- **雙向獨立偵測 (Independent Mode)**：徹底解除多空互鎖，支援 V 型反轉與雙向持倉偵測。
- **智能商品辨識 (Auto-Detect)**：自動識別 NQ, GC, BTC, TX 等數十種商品，自動覆寫最佳化參數。
- **時框智能壓制 (Auto Setup Age)**：V4.1 新增！根據圖表時框自動調整防雙刷壓制力度，完美適應從 1分K 到日線的各種節奏。
- **大週期倉位管理 (Sizing Consensus)**：結合 4H 與日線趨勢共識，自動給予「標準倉位」或「縮半倉」建議。
- **Telegram 警報集成**：透過 Google Apps Script (GAS) 完美轉發精美排版的即時訊號通知。

## 🛠️ 快速上手

1. **安裝指標**：
   - 開啟 `5K_Strategy_Master_v4.pine` 檔案。
   - 複製全部程式碼，貼入 TradingView 的 Pine Editor 並點擊「添加到圖表」。
2. **警報設定**：
   - 點擊指標警報圖示，條件選擇 `任何 alert() 函數調用`。
   - Webhook URL 填入您的 GAS 轉發網址。
3. **閱讀文檔**：
   - 詳細邏輯請參考 [5K_Strategy_Documentation.md](./5K_Strategy_Documentation.md)。

## 📂 專案文件索引

- 📑 [使用說明文檔](./5K_Strategy_Documentation.md) - 深入解析進出場邏輯與參數。
- 📜 [版本演進歷史](./5K_Strategy_Version_History.md) - 從 V1 到 V4.1 的完整紀錄。
- 🗺️ [開發紀錄 Walkthrough](./walkthrough.md) - 技術決策與演進筆記。
- 📊 [專案目前狀態](./5K_Strategy_Project_State.md) - 開發進度與 To-Do。

## ⚖️ 免責聲明
本指標僅供技術分析參考，不構成任何投資建議。投資交易具有高度風險，請務必嚴格執行風控管理。
