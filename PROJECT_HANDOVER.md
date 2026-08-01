# 🏛️ 期交所 TXO GEX Dashboard - 專案交接與開發指引手冊

本手冊整理了近期的**討論紀錄、架構決策、日夜盤自動更新機制**，以及**如何在個人筆電上透過 Antigravity IDE / VS Code 繼續進行富邦 API 即時數據開發**的詳細步驟。

---

## 📌 一、 專案現狀與今日完成事項

1. **夜盤 (Night Session) Excel 匯入與 GEX 重算**：
   - 整合期交所官方 Excel 端點：`https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=1`
   - 精確提取夜盤近月台指期收盤價與成交量，並以此重新校正當前最新 GEX 避險牆、Zero Gamma Level 與 Call/Put Wall。
   - 前端 Dashboard 頂部自動標註盤別標示（如 `🌙 夜盤收盤價校正 (05:00 Close)` 或 `☀️ 日盤結算籌碼 (13:45 Close)`）。

2. **GitHub Actions 時間保險與工作流程整合**：
   - 刪除舊有重複的 `daily_update.yml`。
   - 統整為單一工作流程 `.github/workflows/auto_update.yml`（名稱：`TAIFEX Data Engine (Day & Night Sessions)`）。
   - **時間保險機制 (3-Step Failover)**：
     - **🌙 夜盤更新**：台灣時間 **05:30**, **06:00**, **06:30**
     - **☀️ 日盤更新**：台灣時間 **15:30**, **16:00**, **16:30**
   - **一鍵手動執行**：配置 `workflow_dispatch:`，隨時可於 GitHub 網頁/手機 App Actions 頁面點擊 **"Run workflow"** 手動拉取最新數據。

---

## 📂 二、 專案核心檔案結構說明

- `scripts/fetch_and_calc.py`：期交所/證交所數據抓取、日夜盤自動判定與 GEX/基線計算核心。
- `.github/workflows/auto_update.yml`：GitHub Actions 自動日夜盤 Cron 排程與手動觸發工作流程。
- `data/gex_data.json` & `encrypted_gex.json`：計算產出之 JSON 原檔與 AES-256 加密密文。
- `app.js` & `index.html` & `style.css`：Dashboard 視覺化與解密渲染前端。
- `taifex_catalog.json` & `full_270_futures.json`：個股期貨 270 檔目錄與參考資料。

---

## 🚀 三、 將最新成果上傳至 GitHub 的步驟

請在現有電腦的終端機（PowerShell 或 Git Bash）執行以下命令，將今日完成的所有程式碼與數據推送到您的 GitHub 倉庫：

```bash
git status
git add .
git commit -m "🏛️ [Feat] 成功整合期交所夜盤 Excel 自動抓取、3-Step Failover 排程與前端 Session 標示"
git push
```

---

## 💻 四、 在個人筆電續接開發指南 (Antigravity IDE / VS Code)

當您回到個人筆電時，請按照以下步驟開啟專案：

### Step 1: 從 GitHub 下載專案
開啟個人筆電的終端機 (Terminal / PowerShell)，執行：
```bash
git clone <您的 GitHub 倉庫網址>
cd txo-gex-dashboard
```

### Step 2: 使用 IDE 開啟專案
- **使用 Antigravity IDE**：在 Antigravity IDE 中點選 `Open Folder` 並選擇 `txo-gex-dashboard` 目錄。
- **使用 VS Code**：執行 `code .` 或點擊 `File > Open Folder` 打開專案目錄。

### Step 3: 富邦 API 即時數據串流開發步驟 (未來規劃)
1. **安裝 Python 依賴套件**：
   ```bash
   pip install fubon-neo beautifulsoup4 requests pycryptodome
   ```
2. **申請並放置富邦憑證**：
   - 於個人筆電下載富邦 `.pfx` 憑證檔案（例如存放於 `C:/Cert/fubon_cert.pfx`）。
   - 在專案內建立 `.env` 或在腳本中寫入憑證路徑與密碼（切勿提交個人憑證至公開 GitHub 倉庫！）。
3. **建立即時串流腳本與籌碼語意分析**：
   - 建立 `scripts/fubon_realtime.py`，參考我們的交接範例連接 `FubonSDK` 訂閱台指期盤中即時 Tick/K線，隨時重算 GEX 並更新至 `data/gex_data.json`。
   - 可參考 `OPTIONS_CHEATSHEET.md` 第 5 章所定義之**「外資/十大特人期貨單日變化量 ($\Delta$ Net OI) 動態門檻與語意化形容詞」**，進行動態判讀與摘要生成！

---

## 🎯 總結

今日要求之**日盤與夜盤 Excel 匯入、時間保險重試、手動按鈕、Session 標籤與籌碼變化量形容詞規範已全數寫入專案文件**。您隨時可以將變更推送到 GitHub，並在個人筆電上無縫續接！

