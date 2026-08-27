# 🏛️ TXO GEX 儀表板 — 專案交接手冊 (v47.4)

本手冊記錄專案現狀、核心功能清單、開發 SOP 與個人筆電續接步驟。

---

## 📌 一、v47.4 完整功能清單

### 核心分析與視覺化模組

| # | 功能 | 說明 |
|---|---|---|
| 1 | **T型報價視角 (DEFAULT)** | 預設 Y 軸為履約價 Strike / X 軸為 GEX 金額，符合台灣期貨選擇權 T 型報價表直覺 |
| 2 | **左右對稱 Call/Put 分離** | Call GEX 壓在右側 (+X)，Put GEX 壓在左側 (-X)，中間貫穿 Net GEX S 曲線 |
| 3 | **🛡️ 雙軌標籤防碰撞** | 經典視角為高低階梯軌 (`ay: -56` vs `-24`)；T型視角為雙欄軌 (`x: 0.82` vs `0.98`)，永不重疊遮擋 |
| 4 | **📸 單層面板與子區塊浮水印** | 100% 單層獨立面板，搭配面板右下角及 key-subcards 獨立版權標籤 `© 尋鳥 Bluebird Finder` 方便社群截圖發文 |
| 5 | **💎 個股期貨 Top 10 一頁呈現** | 篩選器表格高調升至 690px，切換 Top 10 買超/賣超時一頁 10 行完全不裁切 |
| 6 | **🎬 10 盤籌碼動態播放器與三色徽章** | 1.2 秒間隔播放過去 5 天 10 個日夜盤 GEX 位移演變，搭配 Live(紅字閃爍)/快照(金黃)/定案(粉藍) 動態三色徽章 |
| 7 | **5 日 10 時段 GEX 矩陣** | T-4 日/夜 ~ T 日/夜盤，含加權、櫃買、TXF、ZG、CW、PW、Max Pain、P/C Ratio (無高度限制直接呈現) |
| 8 | **多色 DTE 多到期日直方圖** | W1🟨 / W2🟩 / M1🟦 / 雙週五🟪 四段到期日分色 |
| 9 | **🔀 疊加對比模式** | 動態比對當前 vs 前一盤別 GEX 曲線差異 |
| 10 | **Net GEX 敏感度曲線** | 白藍樣條曲線精確標示 Zero Gamma 轉折點 |
| 11 | **⚡ 富邦 API WebSocket 實時網關** | 富邦 Neo API MarketData 實時串流，日夜盤合約自動切換與點位閃爍 |
| 12 | **📊 Zero Gamma 雙圖動態連動** | Live Tick 驅動 Zero Gamma 動態位移，圖 1 卡片與圖 2 矩陣頂列 100% 實時同步跳動 |
| 13 | **🌐 期交所官方外匯引擎 (v45.5)** | 直接解析期交所 `dailyFXRate` 每日外幣參考匯率，台幣/日圓與美元指數結算價 100% 精準校準 |

### 三級即時報價網關模組

| # | 功能 | 說明 |
|---|---|---|
| 14 | **三級容錯報價網關** | 優先 1: Fubon WebSocket 專線 ➔ 優先 2: DOM 網關 ➔ 優先 3: 期交所 MIS API |
| 15 | **即時 Tick 閃爍特效** | 頂部膠囊即時顯示報價源狀態，價格跳動觸發亮紅/亮綠閃爍特效 (`.live-tick-flash-up/down`) |

---

## 🌐 三、期交所與證交所 官方權威 Endpoint 網址地圖 (v46.2)

| 資料庫 / 模組名稱 | 官方網址 (URL) | 抓取邏輯與資料用途 |
|---|---|---|
| **1. TAIFEX 股票期貨除權息契約調整** | `https://www.taifex.com.tw/cht/4/contractAdj` | 抓取全場 270+ 檔股票期貨現金股利、股票股利、除權息契約調整日 |
| **2. TWSE 證交所除權息預告表** | `https://www.twse.com.tw/rwd/zh/exRight/TWT48U?response=json` | 預告未來上市公司除權息日期與現金股利 |
| **3. TWSE 證交所除權息計算結果** | `https://www.twse.com.tw/rwd/zh/exRight/TWT49U?response=json` | 當日除權息參考價、扣除現金價值與加權指數預估扣點數 |
| **4. TAIFEX 股票期貨交易量熱力圖** | `https://taifex.com.tw/eventTaifexTradingCenter/cht/ssf.do` | 每日前十大股票期貨交易量 (含日盤/含夜盤切換)、真實成交口數與熱力圖 |
| **5. TAIFEX 股票期貨每日市場總行情** | `https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=0&commodity_id=STF` | 全場個股期貨成交量、開高低收、結算價與未平倉口數 |
| **6. TAIFEX 股票期貨保證金公告** | `https://www.taifex.com.tw/cht/5/stockMargining` | 371 檔期交所個股期貨合約代號 (CDF, CAF, CCF) 與股票代號 (2330, 2303) 精準對射 |
| **7. TAIFEX 臺指選擇權波動率指數 (VIX)** | `https://www.taifex.com.tw/indes/index.aspx` | 期交所官方 30 天期隱含波動率指數，驅動 VEX 做市商避險防守計算 |
| **8. TWSE 證交所每日價格指數 (MI-INDEX)** | `https://www.twse.com.tw/zh/trading/historical/mi-index.html` | 證交所官方大盤加權指數 (IX0001)、寶島指數及各大主題產業指數收盤與漲跌 |
| **9. TWSE MIS 類股即時行情** | `https://mis.twse.com.tw/stock/spot-stock?lang=zhHant` | 證交所 33 大產業類股即時價量，歸納至 8 大精準主題資金輪動矩陣 |
| **10. TAIFEX 每日外幣參考匯率** | `https://www.taifex.com.tw/cht/3/dailyFXRate` | 期交所官方台幣/美元、日圓/美元、美元指數每日參考匯率與歷史歷程 |

---

## 🛡️ 四、標準作業流程 SOP（必須逐步執行）

**步驟 1**：功能開發 (HTML / CSS / JavaScript / Python)

**步驟 2**：語法平衡檢查（HTML div 對稱、JS 括號閉合）

**步驟 3**：資料正確性與視覺核對
- 重跑 `fetch_and_calc_vision.py`，確認 `[OK]` 輸出
- 瀏覽器開啟，確認 T型報價視角與經典視角渲染無錯位與文字撞鍵

**步驟 4**：手機版面驗證（390px 寬，無橫向溢出，標籤角落平整）

**步驟 5**：嵌入資料同步
```bash
python -c "import json; d=json.load(open('data/gex_data.json',encoding='utf-8')); open('data/embedded_data.js','w',encoding='utf-8').write('window.GEX_EMBEDDED_DATA = ' + json.dumps(d, ensure_ascii=False) + ';')"
```

**步驟 6**：更新所有 `.md` 文件（中文為主，不得包含第三方品牌名稱）

**步驟 7**：Git 推送
```bash
git add -A
git commit -m "feat: v46.2 - [本次修改說明]"
git push origin main
```

---

*最後更新：2026-08-26 推送版 | 尋鳥 Bluebird Finder | v46.2*
