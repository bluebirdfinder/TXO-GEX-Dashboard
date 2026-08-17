# 🏛️ 期交所 TXO GEX Dashboard - 專案交接與個人筆電續接手冊 (v38.0)

本手冊整理了專案的**最新 Playwright + Gemini 3.6 Vision 雙 Call 批次數據引擎架構、5日歷程矩陣全欄位 Session-to-Session 增減差額標註、散戶多空比與國際熱錢對話式教學 Modal、GEX 圖表與 X 軸標題排版優化、UTF-8 完整解密與全站 Self-Audit 檢測機制**，以及**開發與更新標準作業流程 (SOP)** 與 **如何在個人筆電上透過 Antigravity IDE / VS Code 續接開發與富邦即時 API 串接**的完整指引。

---

## 📌 一、 專案現狀與 v38.0 完整功能清單

1. **📊 近 5 日關鍵市場指數與 GEX 結構歷程矩陣 — 全欄位（+）/（-）括號差額對照**：
   - **現貨 (加權 IX0001、櫃買 IX0043)**：**日盤列**與「前一日日盤」相比；**夜盤列**依期交所規範標示為 `-`。
   - **期貨與 GEX 指標 (台指期 TXF, Zero Gamma, Call Wall, Put Wall, Max Pain, P/C Ratio)**：當前盤面與**「緊鄰的前一個盤面 (Upstream Session)」**相比（如 T夜盤 vs T日盤、T日盤 vs T-1夜盤、T-1夜盤 vs T-1日盤）。
   - **醒目多空色彩**：正數為 `🔴 (加碼/上揚)`、負數為 `🟢 (減碼/下跌)`、零為灰色。

2. **💡 散戶多空比與三大法人籌碼診斷區 + 互動教學 Modal**：
   - **`ℹ️ 散戶多空比判讀教學` 互動 Modal**：詳述小台 (MXF) / 微台 (TMF) 反向指標公式、歷史轉折臨界門檻（`> +15%` 易拉回、`< -15%` 易反彈）與台指 VIX 恐慌指標連動說明。
   - **100% 法規合規**：移除所有券商特定名稱（如永豐期貨），全數標註「期交所官方公開數據計算」與學理量化說明，符合期貨法規。

3. **🌐 國際熱錢與三大外幣指標判讀教學 Modal**：
   - **`ℹ️ 匯率與熱錢指標教學` 互動 Modal**：詳細拆解美元/台幣 (USD/TWD - 外資資金風向球)、美元指數 (DXY - 全球資金吸鐵石)、美元/日圓 (USD/JPY - 套利平倉 Carry Trade 風險) 對台股流動性的連動機制。

4. **📌 日夜盤微觀結構速報與動態校正列**：
   - **日夜盤動態校正列 (Session Shift Banner)**：極速展示最新夜盤 vs 日盤價格漂移點數與最新 Zero Gamma 防守價位。
   - **微觀結構速報 (Microstructure Express Digest)**：自動識別最新盤面屬於「正 Gamma 波動度抑制區」或「負 Gamma 波動度放大區」，並即時連動最新 Call Wall / Put Wall 調倉位移。

5. **📐 GEX 直方圖 X 軸標題與圖例區間距排版最佳化 (Plotly Layout Optimization)**：
   - 優化 Plotly 圖表邊距與 `yanchor` 佈局，徹底解決「履約價 (Strike)」X 軸標題與底部圖例框 (Legend Box) 重疊的問題。

6. **🔒 核心 UTF-8 解密備援與全站 Self-Audit**：
   - 採用 `TextDecoder('utf-8')` 完整支援多位元 UTF-8 表情符號 (Emojis)，徹底消除解密 `URIError`。
   - 通過 Playwright 自動化 Self-Audit 檢測，確保無 Console 報錯與數據空缺。

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

## 🎯 四、 總結

所有功能、Gemini AI 行情解讀、除權息日程標註、287 檔契約涵蓋、真實 OI GEX 引擎、自動化排程與交接手冊全數 100% 完成！您可以安心推送到 GitHub！
