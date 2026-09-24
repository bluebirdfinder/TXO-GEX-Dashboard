# 🏛️ TXO GEX 儀表板 — 專案交接手冊 (v64.2)

本手冊記錄專案現狀、核心功能清單、數據引擎 Self-Audit 熱備援架構、開發 SOP 與個人筆電續接步驟。

---

## 📌 一、v64.2 完整功能清單與數據引擎架構

### 核心分析與視覺化模組

| # | 功能 | 說明 |
|---|---|---|
| 0 | **🆕 選股雷達「5K真突破」✕「神奇九轉」真指標上線 (v64.2)** | `5K_Strategy_Master_v5.pine`進場觸發邏輯（急殺確認+局部低點偵測+防雙刷壓制+突破確認K棒+均線濾網，不含停損停利）與`demark_sequential_v3_equities.pine`完整Setup/Countdown狀態機+7大過濾器武器庫（成交量/Squeeze/均線斜率/MACD/AO/RSI/KD）真實移植進`scripts/build_screener_cache.py`；RSI/Stochastic/ATR數學對照獨立Python `ta` 函式庫逐位驗證；新增`signals`陣列「📐真5K突破」項目與獨立`demark_buy_state`/`demark_sell_state`欄位（皆不覆蓋既有的不同概念欄位）；抓真實觸發的股票逐日核對Setup生命週期與9天計數不中斷，證實邏輯正確非巧合。完整驗證方式見 [HISTORY.md](HISTORY.md) v64.2 條目 |
| 0.001 | **🆕 選股雷達 JJ_MACD/JJ_CCI 真指標上線 (v64.1)** | 使用者自己另一份私有Pine Script（`JJ_MACD_Sub.pine`／`JJ_CCI_Sub.pine`）真實移植進`scripts/build_screener_cache.py`，取代`macd_state`欄位原本均線+漲跌幅湊出來的heuristic；EMA/CCI數學已對照獨立Python `ta` 函式庫用真實2330資料逐位驗證吻合才接上；OHLCV回看窗口25→60交易日補足EMA收斂；新增`cci_value`/`cci_signal`/`macd_hist_growing`欄位；順手修好戰情室`sc-macd-grow`死checkbox與選股雷達結果表「MACD/量能」欄位原本沒接真資料兩個既有bug。完整驗證方式見 [HISTORY.md](HISTORY.md) v64.1 條目 |
| 0.002 | **🚨🚨 4類法人籌碼資料源「隔日重複值」bug家族根除 ✕ JJ鬼爪V4.1上線 ✕ 選股雷達真數據化 (v64.0)** | 夜盤三大法人/期貨大戶/選擇權大戶/現貨與選擇權法人金額共4類TAIFEX/TWSE來源，都在官方報表「隔天才更新」的空窗期被誤判成當天真實資料寫進永久歷史（2類使用者截圖抓到、1類回補過程意外發現「正在發生中」）；已幫全部相關fetch函式加上明確`target_date`日期查詢，查不到就誠實回報未發布。另外移除Max Pain型態C死碼（62天真實回測驗證，比照露米籌碼監控機器人稽核發現）；JJ鬼爪V4.1指標移植上線（跟ADX Pro V3合併成單一Cloudflare Worker，`indicator=`參數路由）；選股雷達投信認養/籌碼偏多真數據化（全市場滾動10日三大法人歷史）；修復主儀表板與戰情室即時報價死碼/無備援問題。完整根因與驗證方式見 [HISTORY.md](HISTORY.md) v64.0 條目 |
| 0.005 | **🔴🔴 週選結算日歷史回補資料同樣中招，已修正 session_snapshots.json (v63.6)** | v63.5 只驗證並修好「今天」即時計算路徑；用真實 TAIFEX 資料回頭驗證 `backfill_snapshots.py` 的歷史回補路徑，證實 2026-09-09（週三週選結算）與 2026-09-11（週五週選結算）兩天的 DAY/NIGHT 快照，當初都是用同一根因的舊版 `classify_txo_contract_buckets()`（無時間檢查）算出來、選到已結算歸零的當週合約，且 09-11 的錯誤數字目前正顯示在網站「5日歷程」表格上。已直接用修正後邏輯重算這4筆快照的 zero_gamma_level/gex_plus_flip/call_wall_strike/put_wall_strike/max_pain_strike 並回填 `data/session_snapshots.json`，重跑引擎後 `history_10_sessions` 已更新為正確數字 |
| 0.01 | **🔴🔴 月選結算日「已死合約」誤選重大修正 (v63.5)** | `classify_txo_contract_buckets()` 對6碼月選合約單純用到期日排序取最早一口，完全沒檢查「現在時間 vs 到期日」；TAIFEX 官方 `optDataDown` 報表在結算日當天仍列出剛結算的當月合約（含結算前最終OI），導致函式誤選已結算歸零、對夜盤無避險牽引力的9月合約（202609）而非真正的10月月選（202610）。新增 `now` 參數（預設台北時區當下時間），排除「真實到期日 < 今天」或「到期日=今天且已過13:30結算」的候選合約，同步套用於 w1/w2/fri/mth 四桶；`backfill_snapshots.py` 呼叫端改用該歷史交易日13:30作為 `now` 基準，避免歷史回補把所有過去交易日誤判成「已過期」。驗證：put_wall_strike 45500→45000（-500點）、zero_gamma_level 45765.6→45158.5（-607點） |
| 0.02 | **🆕 選擇權大額交易人淨部位串接 ✕ Call/Put Wall 交叉印證徽章 (v63.4)** | 新增 `fetch_official_taifex_large_trader_options()` 串接 TAIFEX「選擇權大額交易人未沖銷部位結構表」(`largeTraderOptQry`)，取得 Call/Put 各自前五大/前十大淨部位（週約/所有契約），欄位結構經真實 fetch 逐碼核對並套用 v63.3 修好的「買方－賣方」正確公式；前端新增獨立表格「1.5 選擇權大額交易人淨部位 5 日歷程」（比照 `has_snapshot`/`is_live` 防呆）；Call Wall/Put Wall 卡片新增大額交易人交叉印證徽章（防守中／轉買方避險／⚪ 無即時數據） |
| 0.05 | **🛠️ 尋鳥戰情室3個Critical bug修復 ✕ ADR真實報價 ✕ 選股快取97%覆蓋率 (v62.4)** | 修復假OHLC面板、ADX背離寫死絕對價位、選股雷達雜湊碼假訊號；ADR_MAPPING變數作用域bug+改真實Yahoo Finance報價；散戶籌碼daily_change/prev_ratio/broker_snapshot改真實日對日快照比對；選股快取改用TWSE單日批量端點，覆蓋率32%→97%、執行時間20-30分鐘→15秒；新增 `DASHBOARD_DATA_SOURCE_MAP.md` 前台區塊×策略×數據來源持久對照表 |
| 0.1 | **🔴🔴 GEX 核心引擎真實選擇權未沖銷部位接軌 ✕ 5日歷史真實回補 (v62.3)** | Self-Audit 最高優先級發現：`calculate_true_gex_profile()` 上線以來 Call Wall/Put Wall/Zero Gamma/Max Pain 全部由假高斯曲線算出，選擇權籌碼從未接過真數據；已改接 TAIFEX 官方「選擇權每日交易行情下載」真實逐履約價未沖銷契約量，W1/W2 改真實分開算；`backfill_snapshots.py` 同步接上真實歷史 GEX 並修復 3 個從未真正抓到數據的舊 bug；`fetch_institutional_momentum.py`/`fetch_official_taifex_retail_sentiment()`/`build_screener_cache.py` 一併真數據化 |
| 0.2 | **🛡️ 戰情室 100% 真實數據管線 ✕ 嚴禁偽數據 Self-Audit ✕ Gemini 2.5 Flash 軍師 (v62.2)** | 實裝 Hard Redline #6；拔除所有布朗運動擬合與隨機假數據；嚴格區分「指數/殖利率 Volume: 0」與「期貨/個股真實合約量」；股號搜尋 Enter 鍵直接切換；老墨/陳玠儒大戶散戶動能與雙色 ADX Pro V3 面積雲帶；Gemini 2.5 Flash 獨立 Key 本機安全保存與多模態截圖即時診斷 |
| 0.1 | **🌪️ CBOE VVIX 尾部避險雷達 ✕ 4級尾部風險矩陣 ✕ 戰情室 4 欄 HUD (v62.0)** | 實時採集 Yahoo Finance `^VVIX` (102.66)；建立 4 級尾部風險矩陣與賣腳氣墊 (350~500點)；VIX/VVIX 隱含波動率加速度背離診斷；戰情室 4 欄式 Macro Risk HUD 連動 |
| 0.1 | **⏱️ 台股全市場盤後數據公布時程全覽與四大商品籌碼量化 (v61.0)** | 建立 `MARKET_DATA_SCHEDULE.md`，梳理 13:30~05:00 數據流水線；升級台指期、選擇權、個股期、個股四大主力商品量化策略；清理夜盤卡片非官方合成欄位與整合 8 大主題意圖標籤 |
| 0.1 | **🏛️ TWSE 融資維持率發布狀態嚴格校驗 (v50.7)** | 修正 `pub_date == target_date_str` 日期嚴格校驗，開盤至 20:30 清算前正確顯示「未公布」，杜絕盤中提前渲染前日數據漏洞 |
| 0.1 | **🧲 Max Pain 4 大空間拓撲 ✕ 3 大籌碼強度 二維共振實戰矩陣 (v50.6)** | 升級 4 大幾何拓撲 (A 痛點沉底、B 對稱箱體、C 恐慌避險、D 極端軋空) ✕ 法人籌碼強度 Level，產出 12 種全情境實戰矩陣，杜絕多空認知矛盾 |
| 0.1 | **🦅 台指選擇權造市商 21 章量化實戰手冊 (v50.5)** | 收錄完整 21 章造市商操盤心法、5口微台 Covered Call 動態避險、輝哥 100% 現貨本位不開槓桿週週收息 SOP 與獨立導出文件 `docs/OPTIONS_QUANT_PLAYBOOK.md` |
| 0.1 | **📅 方案 B：本週重大市場焦點週報自動化 (v50.4)** | 實作 `generate_dynamic_weekly_focus` 演算法，每週一全自動根據期交所與總經日曆更新週報與對應股票期貨，免人工介入 |
| 0.1 | **⚡ VIX 5日歷史歷程欄位 & 恐慌警報 (v50.3)** | 於 5 日歷程矩陣新增 `⚡ VIX 恐慌 (台/美)` 欄位與日夜盤微觀結構 VIX 實時警報，修復 HTML DOM 閉合結構 |
| 0.1 | **📅 富邦期貨本週焦點與股期矩陣 (v50.2)** | 整合富邦 8/31-9/04 週報事件（MSCI、ISM製造業/非製造業、半導體展、Dell/Broadcom/HPE財報、非農就業）對應載板/記憶體/設備/AI伺服器/ASIC股票期貨 |
| 0.1 | **⚡ VIX 雙軌數據引擎與對策手冊** | 整合 TAIFEX VIX (26.09) ✕ 美股 ^VIX (15.74) 雙軌即時連線、四級恐慌燈號評級、Card 9 頂部數據卡片與 VIX ✕ GEX 實戰彈窗 |
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
| 14 | **🕒 動態 4 階段 Session 時段配對架構 (v49.1)** | 劃分 DAY_LIVE / DAY_SETTLED / NIGHT_LIVE / NIGHT_SETTLED，標的價與 GEX 點位 (zg/cw/pw/mp) 嚴格相干配對 |
| 15 | **🌙 期交所官方 6 大夜盤個股期 API 直連 (v49.1)** | 直連期交所 marketCode=1 API 抓取 2303 聯電期 (127.00)、2330 台積期 (2408.00)、0050 期 (106.60)，保留 TWSE 現貨價渲染真實夜盤逆價差 (-3.00) |
| 16 | **🏛️ TWSE 信用融資維持率 API 實時動態連線 (v49.1)** | 直連 TWSE 信用交易 MI_MARGN API，盤後 20:30 清算完成自動更新融資餘額 (5,671.78億) 與維持率 (160.6% 🟢 安定) |

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

## 🤝 五、Claude Code 交接基礎設施 (2026-09-14)

隨著開發主力從 Antigravity 轉為 Claude Code，加入以下常駐設置：

| 項目 | 位置 | 說明 |
|---|---|---|
| **`CLAUDE.md`** | 專案根目錄 | Claude Code 每個 session 開場自動載入，用 `@AGENTS.md` 引入既有 6 大風控鐵律，取代過去只有 `GEMINI.md` 會被讀取的狀況 |
| **`release` skill** | `.claude/skills/release/SKILL.md` | 專案專屬發版 SOP，把 `scripts/bump_version.py` 的原子升級流程包成可觸發的 skill，並將「補寫 HISTORY.md 變更說明」列為不可省略的一步 |
| **`antigravity-handover` skill**（全域） | `~/.claude/skills/antigravity-handover/` | 接手其他 Antigravity 舊專案時的交接準備 SOP，不屬於本 repo |
| **`cloud-automation-pipeline` skill**（全域） | `~/.claude/skills/cloud-automation-pipeline/` | 雲端排程自動化管線通用 SOP（GitHub Actions 排程、資料完整性防呆、防重複發送鎖），不屬於本 repo |

---

*最後更新：2026-08-26 推送版 | 尋鳥 Bluebird Finder | v46.2*
