# 📊 TXO GEX Dashboard Project Status (v39.0)

**Current Version**: `v39.0`  
**Data Engine**: `scripts/fetch_and_calc_vision.py` (Playwright + Gemini 3.6 Vision Dual-Engine)  
**Status**: `100% OPERATIONAL & VERIFIED`  
**Passcode Protection**: `GEX2026` (Case-Insensitive with Eye Toggle 👁️)

---

## 🎯 v39.0 Updates (Current Sprint Highlights)

1. **📱 GEX 直方圖手機版三階梯防遮擋標籤 (GEX Chart Staggered Badges)**:
   - 針對手機螢幕寬度較窄導致 Put Wall、Zero Gamma 與 Call Wall 標籤重疊的問題，全面採用 3 階梯垂直高度分層 (`y: 1.02`, `1.14`, `1.26`)。
   - 手機版自動轉換為精簡標籤 (`PW`, `ZG`, `CW`) 並縮小邊框內距 (`borderpad: 3`) 與字體，搭配動態上方留白 (`t: 95`)，實現 0 重疊、0 遮檔的頂級微觀渲染。

2. **📱 權威台指籌碼快訊與 VIX 觀測儀表手機版 2x2 矩陣化**:
   - 將外資期貨/ Call / Put 未平倉與台指 VIX 等 4 大指標於手機版自動調整為緊湊的 2x2 雙欄卡片佈局，大幅提升手機螢幕垂直空間利用率與閱讀體驗。

3. **📱 全站手機版 Touch 原生流暢滾動與 Self-Audit 驗證**:
   - 為所有數據矩陣與歷史表格全面啟用 `-webkit-overflow-scrolling: touch` 原生慣性滑動，通過 Playwright 390x844 移動端實機渲染測試。

4. **🛡️ 7 大步驟 Standard Operating Procedure (SOP)**:
   - 建立涵蓋語法與標籤閉合 Check-Syntax、期交所/證交所 API 數據與實體網頁截圖雙重對照、Playwright DOM 檢測的完整開發規範。
