# 🐦 尋鳥 Bluebird Finder — TXO GEX 量化系統 (v64.18)

> **台指選擇權 Gamma Exposure 波動度與三大法人期權籌碼量化分析平台**
> 🌪️ CBOE 美股 ^VVIX 實時採集 ✦ 4級尾部風險矩陣 ✦ 做市商賣腳安全氣墊 (350~500點外) ✦ 尋鳥戰情室 4 欄式 Macro Risk HUD ✦ 🏛️ TWSE 融資維持率發布狀態日期比對 ✦ 🧲 Max Pain 4 大空間幾何拓撲 ✕ 3 大籌碼強度 二維共振 12 種全情境實戰矩陣 ✦ 🦅 台指選擇權造市商 21 章量化實戰手冊 ✦ 5口微台 Covered Call 動態避險 ✦ 5 日歷程矩陣 ⚡ VIX 恐慌指數 (台/美) 雙軌欄位 ✦ 📌 日夜盤微觀結構速報 VIX 實時警報 ✦ 熱門股票期貨對照矩陣 ✦ GEX ✕ VIX 雙指標實戰共振矩陣 ✦ 通行碼彈窗自動通關

[![GitHub Actions 自動更新](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml/badge.svg)](https://github.com/bluebirdfinder/TXO-GEX-Dashboard/actions/workflows/auto_update.yml)
[![Live 儀表板](https://img.shields.io/badge/Live-TXO_GEX_Dashboard-00d2ff?style=flat&logo=googlechrome)](https://bluebirdfinder.github.io/TXO-GEX-Dashboard/)
[![引擎版本](https://img.shields.io/badge/Engine-v64.18-ffd700?style=flat&logo=python)](scripts/fetch_and_calc_vision.py)


> **更早的版本亮點（v64.14 → v44.0）已原樣搬到 [docs/archive/README_版本亮點_v44-v64.14.md](docs/archive/README_版本亮點_v44-v64.14.md)**；完整版本史看 [HISTORY.md](HISTORY.md)。

## 📋 2026-10-09 GEX 範圍盤點與通行版(v2)並行累積（未升版、未改引擎數字）

- 與老墨 MOFI GEX 頁面及美股通行寫法對照：符號、乘數 50 一致；**我們少乘 0.01（數字為標準值 100 倍）、σ 用單一當日 VIX、只算 4 檔合約且限現價 ±900**。10/8 實測 OI 涵蓋率合約 82.3%、再限履約價後 27.0%。老墨頁面的 OI 與官方不同，不可當逐點基準。見 [docs/GEX_SCOPE_AND_METHOD_LIMITS.md](docs/GEX_SCOPE_AND_METHOD_LIMITS.md)。
- 新增通行版(v2)GEX：`scripts/gex_v2*.py`，回補 247 天、每日並行累積到 `data/gex_v2_history.json`（獨立檔，不碰 `gex_data.json`）；結果與限制見 [docs/GEX_V2_BACKTEST_20261009.md](docs/GEX_V2_BACKTEST_20261009.md)：翻轉點 v1−v2 平均 −63 點、牆常差千點關卡，回測**沒有證據顯示 v2 預測力較好**，目前兩版並存、不取代。
- 新增：Call／Put Wall 卡片「到期組成」（牆由哪些到期堆出，週選到期後該份消失）；`audit_vs_official.py` 的 OI 涵蓋率檢查。
- 一律是模型輸出、下單參考，不代表價格會停留或反轉。

## 📋 2026-10-06 ～ 10-08 現況更新（文件同步，未升版）

- **對官方資料逐項對帳**：`scripts/audit_vs_official.py`（獨立向期交所／證交所重抓逐項比對，收盤後執行）；清除虛構資料（Max Pain 改全履約價、寫死的本週焦點週報、CPI／非農規則猜日期改讀 BLS 官方日程檔 `data/us_macro_calendar.json`、板塊輪動寫死占比、融資維持率、假成交量預設值等）。
- **GEX／VEX 波動率改用當日官方臺指 VIX**（原固定 18%），資料檔新增 `gex_model`；Zero Gamma 卡片改名「賣買權 OI 分界」，並排顯示新算的「標準 Gamma Flip」（`gamma_flip_standard`，價位掃描、現價±2,000 點內無轉折時顯示「—」並註明）與「日盤收盤值」（`gamma_flip_standard_close`）。
- 🔴 **到期天數誤差修正**：結算日當天（週三／週五）13:30 前，當天要結算的週選原本被當成 7 天後到期（只看星期幾的整數天），低估 gamma；改為到 13:30 結算時刻的小數天、結算後才切下一檔。影響每週三、週五 13:30 前的 GEX／VEX／Zero Gamma／標準 Gamma Flip（例：10/07 凌晨標準 flip 49,132→49,588、總 GEX 2,582→7,806）。
- 🔴 **當日資料未公布時不再借用舊快照**：大額交易人（期貨／選擇權）與三大法人選擇權在期交所尚未公布時回傳 None（`not_published`），資料檔新增 `data_completeness`，網頁狀態列顯示「⚠️ 期交所資料尚未公布」。先前每個交易日早上固定顯示凍結在 9/16 的大額交易人數字。
- 🔴 **個股期貨代碼對照表修正**：手寫的 `STOCK_FUTURES_MAP` 有 28 檔代碼對到別檔股票（例：聯電期實為 `CCF`，非 `CAF`），改以期交所官方對照表為準。
- **尋鳥戰情室**：右側 Y 軸只顯示彩色數字標籤（TV 風格）、GEX 名稱標籤畫在 VRVP 左側、ADX 附圖依可見資料自動縮放、新增黃金 GC（Yahoo；富邦 NEO 沒有海外期貨）、依商品顯示真實資料來源。
- **大戶散戶動能**：本機服務每分鐘存檔（`~/.txo_momentum_1m`，可合成任意分 K，`/api/momentum_history?tf=`）；還原 JJ（rStock）指標定義進行中，**未定案、演算法未改**，見 [docs/JJ_RSTOCK_MOMENTUM_EXPLORATION.md](docs/JJ_RSTOCK_MOMENTUM_EXPLORATION.md)。
- **排程調查**：期交所各項盤後資料實際公布時間尚未量準（`scripts/probe_publish_times.py`，本機排程 `TXO-Probe-Publish-Day`／`Night`）；MARKET_DATA_SCHEDULE.md 的「大額交易人 17:00～18:30」已標註為未驗證。排程時間尚未更動。
- **VEX 符號／Gamma Flip 驗證**（唯讀研究，未改引擎）：見 [docs/VEX_SIGN_AND_FLIP_VALIDATION_20261007.md](docs/VEX_SIGN_AND_FLIP_VALIDATION_20261007.md)；GEX+ 符號維持現狀、繼續觀察。
- 詳見 [HISTORY.md](HISTORY.md) 2026-10-06～10-08 條目與 [HANDOFF.md](HANDOFF.md) K～P 列。

## 📋 2026-09-26 選股雷達現況盤點（文件同步，未升版）

- 實測涵蓋：universe 1,423 筆＝**1,383 檔**上市股票/ETF（100% 有真實120日歷史）＋40 筆 TAIFEX 指數/股期代碼（設計上不適用日K）。畫面「1,400+ 檔」略為誇大；舊文件「97%」是把這40筆算進分母。
- **真實移植（Pine 原始碼）**：JJ_MACD/JJ_CCI、🚀強火箭/🐦強力藍鳥、📐真5K突破、神奇九轉（`demark_buy_state`/`demark_sell_state`）；**投信認養／籌碼偏多自 v64.0 起已是真資料**（舊文件寫「未接」已更正）。
- **仍是簡化近似**：🛸動能飛碟、⚡動能閃電、✈️噴射機、🥚帶殼鳥、`k5_state`、`demark_state`。
- `scripts/build_screener_cache.py:56-58` 全域關閉 SSL 驗證（`CERT_NONE`），已評估、僅回報未修改。
- 詳見 [HISTORY.md](HISTORY.md) 2026-09-26 條目與 [DASHBOARD_DATA_SOURCE_MAP.md](DASHBOARD_DATA_SOURCE_MAP.md) 第7列。

## 🌟 2026-10-07 戰情室實測修正與 K 線歷史回補（未升版號）

- **圖表跟即時報價走**：台指期 1～60 分線用富邦即時成交價推進最後一根；個股取「富邦即時／報價檔／日K」中最新者並標資料日期；開／高／低、手機底部列、報價服務斷線紅帶、搜尋下拉現貨＋期貨並列、副圖可拖曳。
- **持倉部位體檢不再冒充真實體檢**（先問部位）、洗價點改三級警戒；GEX 五大防線只顯示在台指期／小台／微台。
- **K 線歷史回補**：`scripts/backfill_taifex_klines.py` 用期交所官方逐筆成交檔補回日內 K（與富邦 OHLC 100% 一致），15 分線不用再等每天累積。

完整內容請見 [HISTORY.md](HISTORY.md) 與 [docs/ROOM_UX_WALKTHROUGH_2026-10-07.md](docs/ROOM_UX_WALKTHROUGH_2026-10-07.md)。

## 🌟 v64.17 網頁一律稱「動能鳥」

- 網頁上的「JJ」稱呼全部改為「動能鳥」（標題、說明、程式內字串與名稱）；Worker 新增 `indicator=bird` 別名。
- 盤點並如實記錄「指標運算搬到私有 Worker」的完成度與公開 repo 內仍含個人指標邏輯的檔案（待使用者決定）。

完整內容請見 [HISTORY.md](HISTORY.md) v64.17 條目。

## 🌟 v64.16 FVG/Order Blocks 勾選框接上 SMC

- 指標庫「FVG／Order Blocks (SMC)」勾選框原本沒接任何繪圖，現接上 SMC 覆蓋層（勾選＝多顯示 FVG 與波段訂單塊）。
- Worker（`bluebird-indicators`）原始碼位置與 `indicator=smc` 路由已就緒（私有資料夾，待使用者部署）。

完整內容請見 [HISTORY.md](HISTORY.md) v64.16 條目。

## 🌟 v64.15 戰情室 SMC 開關

- **戰情室新增「🧠 SMC」開關**（LuxAlgo Smart Money Concepts，CC BY-NC-SA 4.0，個人非商業）：畫市場結構 BOS／CHoCH、訂單塊、EQH／EQL、FVG、強弱高低點，多方紅、空方綠。演算法在使用者私有 Worker／私有資料夾（不進公開 repo），公開 repo 只有畫圖程式。預設關閉。

完整內容請見 [HISTORY.md](HISTORY.md) v64.15 條目。

## 🎓 GEX / VEX 全指標國中生白話懶人包

| 指標名稱 | 國中生白話比喻 | 它在看什麼？ | 實戰應用與操作指引 |
| :--- | :--- | :--- | :--- |
| **現價 (Spot)** | 👦 小明目前位置 | 大盤當前即時成交點位 | 作為一切防守距離的基準點 |
| **Call Wall** | 🧱 玻璃天花板 | 做市商賣壓最大牆位 | 大盤上漲貼近時容易漲不動 (可做 Sell Call 價差或多單停利) |
| **Put Wall** | 🛋️ 超大彈簧軟墊 | 做市商護盤最大支撐牆 | 大盤回檔跌至附近容易踩墊反彈 (可建立當沖多單或 Sell Put 價差) |
| **Zero Gamma** | ⚖️ 園區安檢紅外線 | 波動度壓抑 vs 暴跌助跌臨界點 | 站上走慢速安定區；跌破進入做市商追殺避險區 |
| **Max Pain** | 🎯 週三抽獎箱 | 散戶權利金賠最多、莊家賺最多的結算點 | 週二/週三結算前夕，指數常被主力壓回附近讓買方雙歸零 |
| **VEX (NEW)** | 😱 恐慌狂狂暴開關 | 當恐慌指數 (IV) 飆高時，做市商會護盤還是火上加油 | **負值時**代表盤中一旦急殺，做市商會無腦賣期貨火上加油！ |
| **GEX+ (NEW)** | 🛡️ 總安全指數 | 價格變動 (Gamma) + 恐慌情緒 (Vanna) 的合成總指數 | 正值代表全場做市商整體淨結構仍具備一定安定力道 |
| **GEX+ Flip (NEW)** | 🚨 早鳥提早警報線 | 結合恐慌感後，做市商真正的防守底線 | 比傳統 Zero Gamma 更靈敏發出早鳥大跌預警 |

---

## 🚨 早鳥警報線 (GEX+ Flip) 高低雙情境實戰口訣

### 🔴 情境一：當 VEX 為負值時 (恐慌氣氛重，最常見)
- **關係**：GEX+ Flip 會比 Zero Gamma **高**！（範例：`44,848 > 44,778`）
- **原因**：因為市場恐慌賣壓大，大盤往下掉時不需要等到跌破 `44,778`，在更高的 `44,848` 做市商就已經被恐慌嚇到提前拋售期貨。
- **實戰效果**：早鳥線在上方，給您「提早 70 點逃命 / 試空」的預警！

### 🟢 情境二：當 VEX 為正值時 (市場氣氛樂觀、買盤護盤厚實)
- **關係**：GEX+ Flip 會比 Zero Gamma **低**！（範例：`44,710 < 44,778`）
- **原因**：因為市場非常安定，做市商手裡緩衝很夠。就算大盤跌破 `44,778`，做市商也不會立刻慌張砍單，真正的防守底線可以退守到更低位置 (`44,710`)。
- **實戰效果**：早鳥線在下方，告訴您「大盤抗跌性極強，不要輕易被假跌破騙掉多單」！

💡 **一秒口訣記憶法**：
- 🔴 **VEX 為負 (恐慌強)** ➔ 早鳥線在 **上方**（提早發警報，提醒快跑/試空）。
- 🟢 **VEX 為正 (護盤厚)** ➔ 早鳥線在 **下方**（延後防守線，代表大盤很沉穩抗跌）。

---

## 🛠️ 系統架構

| 模組 | 技術 stack |
|---|---|
| **前端 UI** | HTML5, Vanilla CSS3 (深色擬物模式), Vanilla JavaScript ES6+ |
| **圖表引擎** | Plotly.js v2.27.0 (雙方向橫條/豎條 + 樣條 S 曲線) |
| **資料與視覺引擎** | Python 3.12, BeautifulSoup4, Pandas |
| **即時報價網關** | Python WebSockets / Asyncio |
| **加密與權限** | SHA-256 XOR 加密（通行碼不在文件中公開） |
| **自動化部署** | GitHub Actions Cron（每日 14:00 日盤定案 & 05:00 夜盤定案） |

---

## 🚀 本機執行步驟

```bash
pip install beautifulsoup4 requests websockets
python scripts/fetch_and_calc_vision.py
python -c "import json; data=json.load(open('data/gex_data.json',encoding='utf-8')); open('data/embedded_data.js','w',encoding='utf-8').write('window.GEX_EMBEDDED_DATA = ' + json.dumps(data, ensure_ascii=False) + ';')"
python -m http.server 8080 --bind 127.0.0.1
# 瀏覽器：http://localhost:8080/index.html
```

---

## ⚖️ 免責與法律聲明 (Legal Disclaimer)

本平台（含 GEX 計算結果、三大法人籌碼數據與 AI 解讀）**僅供學術研究與衍生性商品數據可視化參考**，非屬證券期貨投資顧問行為，亦不構成任何買賣投資建議。衍生性商品交易具高度風險，投資人應獨立思考、審慎評估，並自負投資盈虧責任。

© 2026 尋鳥 Bluebird Finder Quant Labs. 版權所有，未經授權請勿商業重製與無償轉載。
