# 🏛️ 期交所 TXO GEX Dashboard - 專案交接與個人筆電續接手冊 (v35.0)

本手冊整理了專案的**最新 Playwright + Gemini 3.6 Vision 雙 Call 批次數據引擎架構、國際熱錢動向 Card、個股期貨正逆價差 (Basis) 亮點**，以及**如何在個人筆電上透過 Antigravity IDE / VS Code 續接開發與富邦即時 API 串接**的完整指引。

---

## 📌 一、 專案現狀與 v35.0 完整功能清單

1. **🤖 Playwright + Gemini 3.6 Vision 雙 Call 批次數據引擎**：
   - 每日盤後定時自動由 Playwright 擷取期交所/證交所 A+B 類網頁，單次 Call 打包多圖給 Gemini 3.6 Vision 解析。
   - 全天僅消耗 **2 次 Gemini API 呼叫** (15:30 日盤 1 次 / 05:30 夜盤 1 次)。
   - 前置 DOM 日期 Smart Readiness Check，零浪費 API 額度。

2. **🌐 國際熱錢動向 Card (Hot Money Digest)**：
   - 即時追蹤 `USD/TWD`（美元/台幣）、`DXY`（美元指數）、`USD/JPY`（美元/日圓）。
   - 提供國中生也能懂的白話文字解讀（台幣強升 ➔ 外資熱錢匯入偏多；台幣急貶 ➔ 外資提款落跑偏空）。

3. **🎯 真實 OI 之 Black-Scholes GEX 引擎**：
   - 替代舊有高斯常態分布模擬，採用期交所當日各履約價真實 Call/Put OI (W1/W2/月選) 計算權威 GEX 柱狀圖、Call Wall 與 Put Wall。

4. **💎 個股期貨正逆價差 (Basis) 亮點**：
   - 計算台積電期、鴻海期、聯發科期等熱門個股期貨之期現貨價差，標示偏多/偏空趨勢標籤。

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
- **執行測試**：
  ```bash
  python scripts/fetch_and_calc_vision.py
  ```
- **富邦 API 盤中即時 GEX 串接**（回到個人筆電後隨時可開始）：
  - 富邦 SDK Python 腳本放於本地後端。
  - 盤中接收 Tick 價格 $S_t$，本地重算 GEX 後推播至 JSON，**Gemini API 使用次數依然保持 0 增加（每日 2 次）**。

---

## 🎯 三、 總結

所有功能、熱錢解讀、真實 OI GEX 引擎、自動化排程與交接手冊全數 100% 完成！您可以安心推送到 GitHub！
