# 🏛️ 期交所 TXO GEX Dashboard - 專案交接與個人筆電續接手冊 (v37.0)

本手冊整理了專案的**最新 Playwright + Gemini 3.6 Vision 雙 Call 批次數據引擎架構、5大結算天期動態到期日標註 (DTE Expiration Annotations)、Net GEX 淨動態曲線與「🔀 疊加對比」模式、三大法人選擇權 Call/Put 雙行拆解、直方圖三關價標籤階梯式錯開、TWSE 除權息動態預警、Gemini AI 4 大焦點掃描**，以及**如何在個人筆電上透過 Antigravity IDE / VS Code 續接開發與富邦即時 API 串接**的完整指引。

---

## 📌 一、 專案現狀與 v37.0 完整功能清單

1. **🎨 5 大結算天期動態到期日標註 (DTE Expiration Annotations)**：
   - 直方圖圖例動態顯示各合約精確結算日期：`🟨 近週選 W1 (08/19三結算)`、`🟩 次週選 W2 (08/26三結算)`、`🟦 當月月選 M1 (09/16三結算)`、`🟪 雙週五選 (08/21五結算)`。
   - 分層堆疊呈現做市商在當沖、波段與國際事件避險部位的精確時程。

2. **📈 Net GEX 淨動態曲線與「🔀 疊加對比」模式**：
   - **Net GEX 曲線 (Net GEX Profile Line)**：以白藍高對比平滑曲線 (`spline`) 跨越履約價，精確於 **Zero Gamma (45,820.2)** 點位穿過 0 軸，直觀展現多空轉折力道。
   - **標籤階梯式錯開 (Multi-tier Vertical Staggering)**：`Zero Gamma` 置於頂層 (`y: 1.14`)，`Put Wall (45,650)` 與 `Call Wall (46,000)` 置於底層 (`y: 1.02`)，徹底解決水平標籤重疊問題。
   - **🔀 疊加對比**：點擊即時切換黃色對照盤別 (T-1日盤/夜盤) 差異對比線，並提供明顯的反白高亮視覺回饋。

3. **📊 三大法人選擇權 Call / Put 買賣超金額獨立雙行拆解**：
   - 復刻經典雙行排版，獨立呈現外資、投信與自營商選擇權的 `Call` 與 `Put` 買賣超金額與 `🔴 (買超) / 🟢 (賣超)` 燈號，精確辨識法人偏多雙買或避險雙賣細節。

4. **🤖 Gemini AI 全市場籌碼、GEX 轉折與除權息事件 4 大焦點掃描**：
   - 🎯 **大盤 GEX 位階與假洗盤判讀**（45,841 現價位階 vs 45,500 轉折點）。
   - 🧱 **週月選莊家牆與結算磁吸**（46,000 Call Wall vs 45,500 Put Wall vs 45,900 Magnet）。
   - 🔥 **Top 10 法人籌碼聚焦標的**（外資/投信同步現貨買超 + 期貨淨多單雙重加碼股）。
   - 📅 **近期除權息扣點校正與價差防守**（TWSE 官方除權息扣點防誤判）。

5. **📅 TWSE 官方除權息動態預警與過期自動隱藏**：
   - 自動對齊 TWSE 除權息日程 API，**過期事件自動清除標註**，僅對未來的即將/當日除權息事件進行黃標預警。
   - 自動區分「除息 (現金股利)」、「除權 (股票配股)」與「除權息 (同天進行)」。

6. **⚡ 自動數據初始化與隱密安全性密碼解鎖**：
   - 開啟網頁即自動加載內建數據，絕不出現空白表格。
   - 隱密通行碼 `GEX2026`（不分大小寫），具備原生 `👁️ / 🙈` 明隱藏密碼切換與 Session 記錄。

---

## 🚀 二、 在個人筆電續接開發步驟 (Personal Laptop Continuation)

當您回到個人筆電時，請執行以下步驟續接開發：

```bash
# 1. 切換至您個人筆電的工作目錄，拉取最新代碼
git clone https://github.com/bluebirdfinder/TXO-GEX-Dashboard.git
cd TXO-GEX-Dashboard

# 若原本已有 clone，直接執行拉取最新提交：
git pull origin main
```

- 用 **Antigravity IDE** 或 **VS Code** 打開目錄。
- **執行測試與資料引擎**：
  ```bash
  python scripts/fetch_and_calc_vision.py
  python scratch/make_embedded_data_js.py
  ```
- **富邦 API 盤中即時 GEX 串接**（回到個人筆電後隨時可開始）：
  - 富邦 SDK Python 腳本放於本地後端。
  - 盤中接收 Tick 價格 $S_t$，本地重算 GEX 後推播至 JSON，**Gemini API 使用次數依然保持 0 增加（每日 2 次）**。

---

## 🎯 三、 總結

所有功能、Gemini AI 行情解讀、除權息日程標註、287 档契約涵蓋、真實 OI GEX 引擎、自動化排程與交接手冊全數 100% 完成！您可以安心推送到 GitHub！
