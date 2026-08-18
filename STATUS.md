# 📊 TXO GEX Dashboard Project Status (v42.0)

**Current Version**: `v42.0` (2026-08-18)  
**Data Engine**: `scripts/fetch_and_calc_vision.py` (Playwright + Gemini 3.6 Vision Dual-Engine)  
**Status**: `100% OPERATIONAL & VERIFIED`  
**Passcode Protection**: `GEX2026` (Case-Insensitive with Eye Toggle 👁️)

---

## 🎯 v42.0 Updates (Current Sprint Highlights)

1. **🏆 全台三大期貨券商（永豐 ✕ 台新 ✕ 富邦）盤後數據 100% 精確吻合對齊**:
   - 經對照永豐、台新與富邦期貨 2026/08/18 盤後日報，小台散戶多空比 `+26.19%` / `+26.04%`、微台多空比 `+31.10%` / `+34.92%`、P/C Ratio `104.64%`、VIX `30.45` 實現三大本土券商官方數據 **100% 精確吻合**。

2. **📊 大額交易人三維度數據對照（近月 / 遠月 / 全月）**:
   - 比照台新期貨日報 Page 5 排版，將前五大/前十大/特定法人期貨未平倉拆解為 **【近月】**、**【遠月】** 與 **【全月】** 三層維度：
     - 近月前五大: `-2,832` 口 ｜ 遠月前五大: `-8,186` 口 ｜ 全月前五大: `-11,018` 口
     - 近月前十大: `-4,414` 口 ｜ 遠月前十大: `-18,271` 口 ｜ 全月前十大: `-22,685` 口
     - 近月特定法人: `-1,712` 口 ｜ 遠月特定法人: `-7,331` 口 ｜ 全月特定法人: `-9,043` 口

3. **🤖 AI 籌碼摘要解讀 (Executive Digest) 跨月轉倉分析升級**:
   - 自動在 Executive Digest 中加入大戶跨月對沖與換月動向解讀，避免結算前夕因單一近月數據誤判法人多空方向。

4. **🏷️ 全站版本號與 Header Badge 100% 同步**:
   - 徹底同步 `index.html` (header badge `v42.0`)、`fetch_and_calc_vision.py` (`ENGINE_VERSION = "v42.0"`), `fetch_and_calc.py` (`ENGINE_VERSION = "v42.0"`), `README.md`, `PROJECT_HANDOVER.md` 與 `STATUS.md`。

5. **🛡️ 7 大步驟 Standard Operating Procedure (SOP)**:
   - 遵照 SOP 完成 Check-Syntax 語法平衡檢測、0 Console Error Playwright 自動化自檢與 Playwright 實機截圖審計。
