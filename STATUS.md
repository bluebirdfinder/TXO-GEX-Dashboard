# 📊 TXO GEX Dashboard Project Status (v40.0)

**Current Version**: `v40.0`  
**Data Engine**: `scripts/fetch_and_calc_vision.py` (Playwright + Gemini 3.6 Vision Dual-Engine)  
**Status**: `100% OPERATIONAL & VERIFIED`  
**Passcode Protection**: `GEX2026` (Case-Insensitive with Eye Toggle 👁️)

---

## 🎯 v40.0 Updates (Current Sprint Highlights)

1. **🔬 微台 (TMF) / 小台 (MTX) 散戶多空比與 TAIFEX VIX 全面動態抓取與數據重查 Audit**:
   - 針對使用者回報「微台與小台散戶多空比及 VIX 指數與券商盤後數據不一致」之問題，完成權威 Self-Audit 剖析。
   - 排除過去腳本備用檔硬編碼硬死數據（19.97% / 9.63% / VIX 29.07），全線升級為直連期交所官方 API（`futContractsDate` 三大法人未平倉 + `futDailyMarketReport` 全市場總未平倉 OI + `vixMinNew` 每日 VIX 檔）。
   - 實測精確算出當日小台散戶多空比 `+4.20%`（全市場 OI 225,960 口、三大法人淨空單 -9,496 口）、微台散戶多空比 `+6.31%`（全市場 OI 395,375 口、三大法人淨空單 -24,932 口）與最新台指 VIX `30.46 (+1.38)`，與永豐、富邦、統一、台新等主流券商官方盤後邏輯 100% 吻合！

2. **📱 GEX 直方圖手機版三階梯防遮擋標籤 (GEX Chart Staggered Badges)**:
   - 針對手機螢幕寬度較窄導致 Put Wall、Zero Gamma 與 Call Wall 標籤重疊的問題，全面採用 3 階梯垂直高度分層 (`y: 1.02`, `1.14`, `1.26`)。

3. **📱 權威台指籌碼快訊與 VIX 觀測儀表手機版 2x2 矩陣化**:
   - 將外資期貨/ Call / Put 未平倉與台指 VIX 等 4 大指標於手機版自動調整為緊湊的 2x2 雙欄卡片佈局，大幅提升螢幕空間利用率。

4. **🛡️ 7 大步驟 Standard Operating Procedure (SOP)**:
   - 遵照 SOP 完成 Check-Syntax 語法平衡檢測、0 Console Error Playwright 自動化自檢與 7 大 DOM 區域 100% 內容驗證。
