# 📊 TXO GEX Dashboard Project Status (v38.0)

**Current Version**: `v38.0`  
**Data Engine**: `scripts/fetch_and_calc_vision.py` (Playwright + Gemini 3.6 Vision Dual-Engine)  
**Status**: `100% OPERATIONAL & VERIFIED`  
**Passcode Protection**: `GEX2026` (Case-Insensitive with Eye Toggle 👁️)

---

## 🎯 v38.0 Updates (Current Sprint Highlights)

1. **📊 近 5 日關鍵市場指數與 GEX 結構歷程矩陣 — 全欄位（+）/（-）括號差額對照**:
   - 現貨與衍生指標全數提供括號增減註記。現貨比較前一日日盤，期貨與 GEX 指標比較上一盤面 (Upstream Session)。

2. **💡 散戶多空比與三大法人籌碼診斷區 + 互動教學 Modal**:
   - 新增 `ℹ️ 散戶多空比判讀教學` Modal。全站移除特定券商名稱，標註「期交所官方公開數據計算」，100% 合規。

3. **🌐 國際熱錢與三大外幣指標判讀教學 Modal**:
   - 新增 `ℹ️ 匯率與熱錢指標教學` Modal，拆解 USD/TWD、DXY、USD/JPY 與台股資金連動機制。

4. **📌 日夜盤微觀結構速報與動態校正列**:
   - 即時顯示日夜盤價格漂移點數與最新 Zero Gamma 防守價位，連動正/負 Gamma 屬性判定與 Call/Put Wall 牆體位移。

5. **📐 GEX 直方圖 X 軸標題與圖例區間距排版最佳化**:
   - 優化 Plotly Layout `margin.b` 與 `legend.y`，徹底解決「履約價 (Strike)」標題與圖例框重疊問題。

6. **🔒 UTF-8 解密備援與全站 Self-Audit 檢測**:
   - 採用 `TextDecoder('utf-8')` 完整支援 UTF-8 表情符號 (Emojis)，通過 Playwright 自動化 Self-Audit 檢測。

7. **🛡️ 7 大步驟 Standard Operating Procedure (SOP)**:
   - 建立涵蓋語法與標籤閉合 Check-Syntax、期交所/證交所 API 數據與實體網頁截圖雙重對照、Playwright DOM 檢測的完整開發規範。
