# 🏛️ 期交所 TXO GEX Dashboard - 專案交接與開發指引手冊 (最新完整版)

本手冊整理了近期的**討論紀錄、架構決策、日夜盤雙維度對照、夜盤盤後籌碼專區**，以及**如何在個人筆電上透過 Antigravity IDE / VS Code 繼續進行富邦 API 即時數據開發**的詳細步驟。

---

## 📌 一、 專案現狀與完整功能簡介

1. **🎴 頂部五大數據卡片日夜盤切一半 (Split-Card)**：
   - 包含台指期 (TXF)、Zero Gamma、Call Wall、Put Wall、Max Pain。
   - **上半部 `☀️ 日盤 (13:45)`**：展示每日 13:45 官方定案結算數值。
   - **下半部 `🌙 夜盤校正 (05:00)`**：展示每日 05:00 收盤價重算之 GEX 避險牆與位移點數（如 `Call Wall: 42,800 (-600點)`）。

2. **🟦 藍框對比摘要區 (Session Shift Banner)**：
   - 精確放置於第二排 Max Pain 右側廣闊區域，以亮藍邊框 (`border: 2px solid #00d2ff`) 展示夜盤相較日盤的期貨價差與避險牆位移對比。

3. **🌙 三大法人夜盤盤後交易籌碼專區 (futContractsDateAh)**：
   - 每日 07:00 自動爬取期交所夜盤盤後官方數據：
     - 外資夜盤台指期 (TX) 淨交易口數 & 契約金額 (億 TWD)
     - 外資夜盤小台 (MTX) 淨交易口數
     - 外資夜盤微台 (Micro) 淨交易口數
     - 自營商夜盤台指期 (TX) 淨交易口數 & 契約金額 (億 TWD)
   - 底部自動編譯 **「💡 夜盤籌碼白話解讀」** 文字摘要。

4. **📊 外資與大戶籌碼單日變化量 ($\Delta$ Net OI) 分級與契約金額精算**：
   - 算式：$\text{契約金額 (億 TWD)} = (|\Delta \text{Net OI}| \times \text{txf\_price} \times 200) / 1e8$
   - 帶出 5 大語意標籤 (`🔥 高檔大舉回補` / `📈 顯著回補` / `⚖️ 中性觀望` / `📉 顯著加碼加空` / `⚠️ 暴增高檔避險`)。

5. **💡 選擇權 P/C Ratio 與 Max Pain (最大痛點) 判讀指南**：
   - Max Pain 卡片底部內建 **`P/C Ratio: 108.5% (🔴 偏多看撐)`** 標籤（嚴格遵循台灣股市「紅漲綠跌」色彩）。
   - 彈窗 Modal 包含全套選擇權口訣、P/C Ratio 判讀與 Max Pain 黑手磁鐵拉回教學。

6. **📱 手機端極致 2x2 雙欄 RWD 響應式排版**：
   - 頂部卡片自動排版為 2x2 雙欄，頁籤列支援平滑橫滑。
   - 大頭貼縮圖強制維護為 **1:1 完美正圓形 (Perfect Circle)**，全站字體 100% 統一為 FinTech 質感微軟正黑體/蘋果系統字。

7. **⚙️ GitHub Actions 403 權限修復**：
   - `.github/workflows/auto_update.yml` 內建 `permissions: contents: write`，徹底解決 Actions 機器人推播時的 403 權限拒絕問題。

---

## 📂 二、 專案核心檔案結構說明

- `scripts/fetch_and_calc.py`：期交所/證交所數據抓取、日夜盤自動判定與 GEX/基線計算核心。
- `.github/workflows/auto_update.yml`：GitHub Actions 自動日夜盤 Cron 排程與手動觸發工作流程。
- `data/gex_data.json` & `encrypted_gex.json`：計算產出之 JSON 原檔與 AES-256 加密密文。
- `app.js` & `index.html` & `style.css`：Dashboard 視覺化與解密渲染前端。
- `taifex_catalog.json`：期交所全量 270 檔個股與 ETF 期貨目錄。
- `PROJECT_HANDOVER.md`：專案交接與個人電腦開發手冊。
- `OPTIONS_CHEATSHEET.md`：選擇權與籌碼語意分級標準速查表。
- `README.md`： GitHub 專案首頁說明與架構圖。

---

## 💻 三、 在個人筆電續接開發指南 (Antigravity IDE / VS Code)

當您回到個人筆電時，請按照以下步驟開啟專案：

### Step 1: 從 GitHub 下載專案
開啟個人筆電的終端機 (Terminal / PowerShell)，執行：
```bash
git clone https://github.com/bluebirdfinder/TXO-GEX-Dashboard.git
cd TXO-GEX-Dashboard
```

### Step 2: 使用 IDE 開啟專案
- **使用 Antigravity IDE**：在 Antigravity IDE 中點選 `Open Folder` 並選擇 `TXO-GEX-Dashboard` 目錄。
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

今日所有**切半卡片、藍框 Banner、夜盤盤後籌碼專區、P/C Ratio 紅綠球、270 檔個股期貨、手機版正圓形頭像與 GitHub Actions 403 修復**全數完成並同步更新至所有 Markdown 文件中。您隨時可以安心將檔案推送到 GitHub！
