# 📊 TXO GEX Dashboard Project Status (v37.0)

**Current Version**: `v37.0`  
**Data Engine**: `scripts/fetch_and_calc_vision.py` (Playwright + Gemini 3.6 Vision Dual-Engine)  
**Status**: `100% OPERATIONAL & VERIFIED`  
**Passcode Protection**: `GEX2026` (Case-Insensitive with Eye Toggle 👁️)

---

## 🎯 v37.0 Updates (Current Sprint Highlights)

1. **🎨 5 大結算天期動態到期日標註 (DTE Expiration Annotations)**:
   - Plotly 直方圖圖例自動標註各合約精確結算日期（如 `🟨 近週選 W1 (08/19三結算)`、`🟩 次週選 W2 (08/26三結算)`、`🟦 當月月選 M1 (09/16三結算)`、`🟪 雙週五選 (08/21五結算)`）。

2. **📈 Net GEX 淨動態曲線與「🔀 疊加對比」模式**:
   - 繪製高對比白藍平滑曲線跨越履約價，於 **Zero Gamma (45,820.2)** 點位穿過 0 軸。
   - `Zero Gamma` (`y: 1.14`) 與 `Put Wall / Call Wall` (`y: 1.02`) 階梯式錯開，解決水平標籤重疊。
   - 按下 `🔀 疊加對比` 即可顯示黃色對照盤別 (T-1日盤/夜盤) 差異對比線與高亮動態按鈕。

3. **📊 三大法人選擇權 Call / Put 買賣超金額獨立雙行拆解**:
   - 復刻經典雙行排版，同時顯示外資、投信、自營商選擇權的 `Call` 與 `Put` 獨立買賣超金額與 `🔴/🟢` 多空燈號。

4. **🤖 Gemini AI 全市場籌碼與除權息 4 大焦點掃描**:
   - 結構化分為 4 大項目：大盤 GEX 位階判讀、莊家牆結算磁吸、Top 10 法人籌碼聚焦個股期、近期 TWSE 官方除權息扣點校正。

5. **📅 TWSE 除權息動態預警與過期自動隱藏**:
   - 過期除權息事件自動清除標註；僅針對未來的即將/當日除權息進行黃標預警。
   - 自動區分「除息 (現金)」、「除權 (配股)」與「除權息 (同天)」。

6. **⚡ 自動數據初始化與隱密安全性密碼解鎖**:
   - 網頁加載時立刻初始化預載籌碼數據，不留明碼提示，原生 `👁️ / 🙈` 顯示/隱藏密碼。
