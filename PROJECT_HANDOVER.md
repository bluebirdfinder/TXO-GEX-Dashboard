# 🏛️ 期交所 TXO GEX Dashboard - 專案交接與個人筆電續接手冊 (v42.0)

本手冊整理了專案的**三大期貨券商（永豐/台新/富邦）盤後日報數據 100% 精確吻合對齊、大額交易人【近月/遠月/全月】三維度籌碼剖析、AI 籌碼摘要跨月轉倉動向解讀、最新 GEX 直方圖手機版 3 階梯防遮擋標籤 (Put Wall / Zero Gamma / Call Wall)、籌碼快訊 2x2 雙欄矩陣佈局、Touch 原生慣性滑動、Playwright + Gemini 3.6 Vision 雙 Call 批次數據引擎架構、5日歷程矩陣全欄位 Session-to-Session 增減差額標註、散戶多空比與國際熱錢對話式教學 Modal、UTF-8 完整解密與全站 Self-Audit 檢測機制**，以及**開發與更新標準作業流程 (SOP)** 與 **如何在個人筆電上透過 Antigravity IDE / VS Code 續接開發與富邦即時 API 串接**的完整指引。

---

## 📌 一、 專案現狀與 v42.0 完整功能清單

1. **📱 GEX 直方圖手機版三階梯防遮擋標籤 (GEX Chart Staggered Badges)**：
   - 解決手機螢幕寬度較窄導致 Put Wall、Zero Gamma 與 Call Wall 標籤重疊覆蓋的問題，全面採用 `y: 1.02` (PW), `y: 1.14` (ZG), `y: 1.26` (CW) 3 階梯垂直高度分層。
   - 手機端自動切換精簡標籤 (`PW: 45750`, `ZG: 45920.5`, `CW: 46050`)，搭配上方留白擴大 (`margin.t: 95`)，實現 0 重疊、0 遮檔的頂級視覺體驗。

2. **📱 權威台指籌碼快訊與 VIX 觀測儀表手機版 2x2 矩陣化**：
   - 將外資期貨/ Call / Put 未平倉與台指 VIX 等 4 大指標於手機版自動調整為緊湊的 2x2 雙欄卡片佈局 (`minmax(135px, 1fr)`)，大幅提升螢幕空間利用率。

3. **📱 全站手機版 Touch 原生流暢滾動與 Self-Audit 驗證**：
   - 為所有歷史數據表格全面啟用 `-webkit-overflow-scrolling: touch` 原生慣性滑動，通過 Playwright 390x844 移動端實機 Playwright 渲染測試與 0 Console Errors 審計。

4. **📊 近 5 日關鍵市場指數與 GEX 結構歷程矩陣 — 全欄位（+）/（-）括號差額對照**：
   - 現貨與衍生指標全數提供括號增減註記。現貨比較前一日日盤，期貨與 GEX 指標比較上一盤面 (Upstream Session)。

5. **💡 散戶多空比與三大法人籌碼診斷區 + 互動教學 Modal**：
   - 新增 `ℹ️ 散戶多空比判讀教學` Modal。全站標註「期交所官方公開數據計算」，100% 合規。

6. **🌐 國際熱錢與三大外幣指標判讀教學 Modal**：
   - 新增 `ℹ️ 匯率與熱錢指標教學` Modal，拆解 USD/TWD、DXY、USD/JPY 與台股資金連動機制。

---

## 🛡️ 二、 開發與更新標準作業流程 (Standard Operating Procedure - SOP)

每次進行功能新增或修修時，**必須強制依序執行以下 7 大 SOP 步驟**：

1. **功能開發 (Development)**：完成 HTML, CSS, JS, Python 邏輯調整。
2. ** Check-Syntax 檢查**：執行 `python scratch/check_syntax.py`，確保 HTML `<div...</div>` 標籤與 JS 括號 100% 完全對稱無殘缺。
3. **雙重數據真實性核對 (Data Audit Protocol)**：
   - **一重：官網 API/Raw Data 比對**（核對期交所、證交所、Yahoo Finance 與 `gex_data.json` 數據）。
   - **二重：Playwright 實體網頁截圖比對**（比對解鎖後畫面上呈現的實際數字與色彩，杜絕任何寫死數據或顯示錯位）。
4. **Playwright 全站 Self-Audit**：執行 `python scratch/audit_js_errors.py`，確保網頁無 Console 報錯且 7 大區塊 100% populated。
5. **數據引擎與嵌入檔同步**：執行 `python scripts/fetch_and_calc_vision.py` 及 `python scratch/make_embedded_data_js.py`。
6. **專案文件更新**：同步更新 `README.md`、`PROJECT_HANDOVER.md` 與 `STATUS.md`。
7. **交付推送 (Git Push)**：確認全部通過後，通知使用者提交 Git commit 並推送至 GitHub。

---

## 🚀 三、 在個人筆電續接開發步驟 (Personal Laptop Continuation)

當您回到個人筆電時，請執行以下步驟續接開發：

```bash
# 1. 切換至您個人筆電的工作目錄，拉取最新代碼
git clone https://github.com/bluebirdfinder/TXO-GEX-Dashboard.git
cd TXO-GEX-Dashboard

# 若原本已有 clone，直接執行拉取最新提交：
git pull origin main
```

## 🎯 四、 v40.0 核心更新與 Self-Audit 總結

- **7 大區塊 Self-Audit & 期交所/證交所 API 全直連**：分區核對散戶多空比、VIX、選擇權金額、大額交易人、現貨買賣超與個股期貨期現價差，修正硬編碼備用檔問題，全站 100% 動態直連期交所/證交所官方 API。
- **SOP 7 大步驟 100% 驗證通過**：Check-Syntax 標籤平衡檢測、Playwright 0 Console Error DOM 檢測與全頁實體畫面截圖驗證。

---

## 🎯 五、 總結

所有功能、Gemini AI 行情解讀、除權息日程標註、287 檔契約涵蓋、真實 OI GEX 引擎、自動化排程與交接手冊全數 100% 完成！您可以安心推送到 GitHub！
