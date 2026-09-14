# 📊 GEX 網頁 + 尋鳥戰情室 —— 前台區塊 × 交易策略 × 數據來源 對照表

> 建立日期：2026-09-15。這份文件回答「網頁上每個區塊怎麼來的、能拿來做什麼交易判斷、稽核狀態如何」，
> 是給使用者審閱、也是給未來新開對話室的 Claude 快速接手用的**持久參考文件**（不是對話記憶，存在 repo 裡）。
>
> 表格欄位說明：
> - **交易策略參考**：這個區塊的數字可以怎麼用在下單決策上
> - **數據來源名稱／從哪裡來**：真實數據的官方名稱與網址
> - **台灣時間公布**：官方發布/定案時間
> - **對應程式**：抓取與計算的檔案/函式
> - **稽核狀態**：這 3 天 self-audit 有沒有查過
> - **已修正？**：發現的假資料問題是否已經修好
> - **需要你決定的事**：還懸而未決、需要你選擇的地方

---

## 一、GEX 主儀表板（index.html / app.js / scripts/fetch_and_calc_vision.py）

| # | 前台區塊 | 交易策略參考 | 數據來源名稱 | 從哪裡來（網址） | 台灣時間公布 | 對應程式 | 稽核狀態 | 已修正？ | 需要你決定的事 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 加權指數(IX0001)卡 | 大盤方向判斷、跟台指期比對算正逆價差 | TWSE 即時指數 | mis.twse.com.tw / openapi.twse.com.tw | 盤中即時，13:30 收盤定案 | `fetch_twse_realtime_indices()` | 未逐行稽核 | — | 無 |
| 2 | 櫃買指數(IX0043)卡 | 同上，針對上櫃股 | TPEx 即時指數 | www.tpex.org.tw | 盤中即時，13:30 收盤定案 | `fetch_twse_realtime_indices()` | 未逐行稽核 | — | 無 |
| 3 | 台指期(TXF1!)日夜盤卡 | 期現價差(Basis)判斷、多空氣氛 | TAIFEX 期貨每日行情 / MIS即時 | mis.taifex.com.tw、futDailyMarketExcel | 日盤13:45定案／夜盤隔日05:00定案 | `fetch_official_taifex_tx_prices()` | 已稽核（AGENTS.md鐵律5防呆：盤中強制MIS，避免讀到昨日結算價） | 原本就是真實 | 無 |
| 4 | ZERO GAMMA／CALL WALL／PUT WALL／MAX PAIN 卡（4張） | **選擇權下單價位參考、垂直價差單/covered call 的履約價選擇、台指期多空進出場點位** | TXO選擇權每日交易行情（未沖銷契約量） | taifex.com.tw/cht/3/optDataDown | **下午3點後**（選擇權盤後資料公布） | `calculate_true_gex_profile()` + `fetch_taifex_txo_open_interest()` | ✅ 已稽核 | ✅ **已修正**（本次最大發現：原本100%用假高斯曲線，現在是真實未沖銷部位） | 無，已完成並實測 |
| 5 | VEX恐慌曝險 & GEX+ FLIP 卡 | 早鳥警報線，提前判斷GEX翻轉方向 | 同上（TXO未沖銷部位 + Vanna計算） | 同上 | 同上 | 同上函式 | ✅ 已稽核 | ✅ 已修正 | 無 |
| 6 | VIX恐慌指數 & 美股^VIX/^VVIX卡 | 恐慌情緒判斷、賣腳安全氣墊距離設定 | TAIFEX VIX指數 + Yahoo Finance ^VIX/^VVIX | taifex.com.tw/cht/7/vixMinNew + query1.finance.yahoo.com | 盤中即時 | `fetch_official_taifex_vix()` | 未特別逐行稽核，但本來就走真實API | — | 無 |
| 7 | 日夜盤價差 Banner | 快速看日夜盤價差方向 | 同 Card 3 台指期資料 | 同上 | 同上 | app.js 內建計算 | 未特別稽核 | — | 無 |
| 8 | 近5日關鍵市場與GEX結構歷程矩陣 | 判斷趨勢延續性、GEX翻轉點逐日位移方向 | `session_snapshots.json`（真實快照累積） | 內部持久化，來源同上各項 | 每日盤後累積 | `write_current_session_snapshot()` / `backfill_snapshots.py` | ✅ 已稽核 | ✅ **今天修好3個抓取bug**（大盤指數/TX期貨價/PC ratio此前從未真的抓到過歷史） | 無 |
| 9 | 📌日夜盤微觀結構速報 | 極速多空位移、變盤臨界判定 | 即時tick + gexData 內插 | app.js 內部計算 | 即時 | `updateMicrostructureExpress()` | ⏳ 部分稽核 | ❌ **`handleLiveTick`用固定0.62係數外推Zero Gamma，未修**（判斷為低風險工程近似，非憑空造假，故意先不動） | **要不要現在修這個0.62係數？**（風險：牽動即時報價渲染，需要更謹慎測試） |
| 10 | 國際熱錢動向與5日匯率歷程 | 外資避險成本、資金流向判斷 | TAIFEX 每日外幣參考匯率 | taifex.com.tw/cht/3/dailyFXRate | 盤後公布 | `fetch_5day_exchange_rates()` | 未逐行稽核 | — | 無 |
| 11 | 國際總經事件雷達 | 避開財報/FOMC等事件前後高波動 | 內部維護的事件日曆演算法 | 程式生成，非外部即時API | — | `renderMacroEventsRadar()` / `calculate_macro_events_radar()` | ✅ 2026-09-15已稽核 | ❌ **未修**：`macro_risk_dashboard`（DXY/US10Y/VIX卡片）完全零fetch、打字寫死，且跟別處真VIX不同步；`raw_calendar_items`寫死5筆2026年事件，09/16 FOMC後會悄悄變永久空清單，無任何提示。倒數計時器真正吃的`valid_events`是動態算的，不受影響 | **要怎麼修？**（見下方彙總） |
| 12 | 主GEX圖表（Total/週三選/週五選/月選 分頁 + 疊加對比 + 10盤播放器） | **核心：選擇權下單價位、價差單/covered call位置、台指期多空進出場參考** | 同 Card 4-5，TXO未沖銷部位逐履約價分布 | 同上 | 下午3點後 | `calculate_true_gex_profile()` | ✅ 已稽核 | ✅ **已修正**（含「疊加對比」T-1真實前一盤資料，原本是今天曲線亂算） | 無 |
| 13 | 散戶籌碼與台指快訊（小台MXF/微台TMF） | **反向指標**：散戶極端偏多(>+15%)易被軋、極端偏空(<-15%)易反彈 | TAIFEX 三大法人期貨未平倉 | taifex.com.tw/cht/3/futContractsDate 等 | **15:00~15:45** | `fetch_official_taifex_retail_sentiment()` | ✅ 已稽核 | ✅ **今天修好** `daily_change`/`prev_ratio`/`broker_snapshot` 全部真實化 | 無 |
| 14 | 夜盤三大法人交易籌碼 | 夜盤外資動向，預判隔日開盤跳空 | TAIFEX futContractsDateAh | taifex.com.tw | 隔日 07:00 盤後定案 | `fetch_taifex_night_institutional_trading()` | ⏳ 部分稽核（抓取失敗時有寫死保底值-422，未強制顯示無數據） | 部分 | **要不要修「抓取失敗時默默用舊保底值」這個殘留問題？** |
| 15 | 法人5日期權與籌碼歷程矩陣（執行摘要+期貨未平倉5日+現貨買賣超/選擇權5日） | 判斷法人趨勢連續性、Call/Put籌碼消長 | `institutional_snapshots.json`真實快照 | 內部持久化 | 每日累積 | 相關 snapshot 函式（今天新建） | ✅ 已稽核 | ✅ **已修正**（原本4/5天永遠寫死假數字） | 無 |
| 16 | Gemini AI籌碼與除權息事件掃描 | AI輔助解讀（明確非投資建議） | gex_data.json彙總 + Gemini API | 內部彙總+Google Gemini | 即時 | `populateAiQuantDigest()` | ⏳ 部分稽核 | ✅ 今天修好「忽略使用者選盤，永遠讀最新」的bug | 無 |
| 17 | 個股期貨287檔篩選明細（含產業資金輪動、夜盤6檔聚光燈） | **個股期大額交易人判斷主力動向、正逆價差扣除除息判斷真假逆價差、投信認養篩選飆股** | TAIFEX大額交易人未沖銷部位結構表 + TWSE T86三大法人買賣超 | taifex.com.tw/cht/3/largeTraderFutQry + twse.com.tw/rwd/zh/fund/T86 | **17:00~18:30**（大額交易人）／**15:00~15:45**（T86現貨法人） | `fetch_taifex_stock_futures_large_trader_batch()` + `fetch_twse_institutional_t86_latest()` | ✅ 已稽核（Component A/B，本次最早修的） | ✅ 已修正 | 「官股行庫」欄位因無官方逐股數據來源，維持顯示不可用（已跟你確認過）。**2026-09-15新發現並已修**：「🚀投信波段認養」徽章原本是idx取模公式假訊號，已改誠實停用（比照選股雷達同款問題的處理方式），真正做到位需要新建逐股多日買超歷史，列入選股雷達真實化大工程 |

---

## 二、尋鳥戰情交易室（trading room/room.html, room.js）

| # | 前台區塊 | 交易策略參考 | 數據來源名稱 | 從哪裡來 | 台灣時間公布 | 對應程式 | 稽核狀態 | 已修正？ | 需要你決定的事 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 主圖K線（5圖同步：主圖+副圖1-4） | 看盤操作、進出場判斷 | `klines_cache.json`（8大核心商品真實多週期快取）+ Fubon即時 | 內部快取 + 富邦Neo API | 即時 | 另一聊天室維護的即時串接 | ✅ 已確認乾淨（原文件：「K線資料：8大核心商品走真實多週期快取，全庫Math.random零命中」） | 原本就真實 | 無 |
| 2 | 大戶散戶動能副圖 | 大戶（外資/投信/自營期貨）vs散戶方向判斷 | `momentum_data.json` + 富邦Books/Trades（規劃中） | TAIFEX OpenAPI + 富邦Neo API | 15:00後（法人）/即時（Books/Trades） | `loadMomentumData()`；即時串接是**另一聊天室在做** | ⏳ 部分（我修好了momentum_data.json來源；圖表即時串接是另一session範圍） | 部分 | 等另一聊天室的Books/Trades完工後才能100%真實 |
| 3 | ADX Pro V3副圖 | 趨勢強度、頂/底背離進出場訊號 | 真實K線算出的DI/ADX | 內部計算 | 即時 | room.js ADX計算段落 | ✅ 已稽核 | ✅ **今天修好**背離判定用固定絕對價位（47200/46150）的bug，改成真實相對背離判定 | 無 |
| 4 | VRVP成交量分布 | 找支撐壓力密集成交區 | 真實K線量能 | 內部計算 | 即時 | room.js VRVP Canvas | ⏳ 未稽核 | — | 無 |
| 5 | 左側面板報價/GEX距離/OHLC | 看盤、GEX關卡位階距離判斷 | gex_data.json（GEX部分真實）+ OHLC | 內部 | 即時/盤後 | `renderLeftPanel()` | ✅ 已稽核 | ✅ **今天修好**漲跌/昨收假資料；開盤/最高/最低目前無真實來源，誠實顯示「—」 | 無（已是誠實狀態） |
| 6 | AI量化軍師（Gemini） | AI輔助診斷（非投資建議） | Gemini API + gexData | Google Gemini API | 即時 | room.js AI Advisor Engine | ✅ 已確認乾淨（有Key真呼叫，沒Key清楚標示「本地內建風控引擎」，不偽裝真AI） | 原本就誠實 | 無 |
| 7 | 選股雷達 Modal | 多因子選股（技術面訊號篩選） | `screener_cache.json`（今天改真實，97%覆蓋率） | TWSE MI_INDEX批量端點 + TPEx | 盤後 | `runBirdQuantScreener()` + `build_screener_cache.py` | ✅ 已稽核 | ✅ **今天修好**雜湊碼假訊號，改真實訊號比對 | 「投信認養」「籌碼偏多」2個篩選條件還沒接真數據，永遠不觸發（誠實不匹配） |
| 8 | 商品搜尋/自動完成（Ctrl+K） | 快速切換商品 | `symbolsUniverse`真實股票清單 | 內部清單檔 | — | room.js Symbol Search Engine | ⏳ 未稽核 | — | 無 |
| 9 | 法人動能 Modal（另一個彈窗，非副圖） | 三大法人多空方向、留倉淨額判斷 | TAIFEX OpenAPI（即時fallback）+ momentum_data.json | openapi.taifex.com.tw | 15:00後 | `loadMomentumData()` | ✅ 已稽核 | ✅ 今天修好 | 無 |
| 10 | 權值貢獻HUD | 台積電等權值股對大盤點數貢獻判斷 | 內部依市值权重估算 | 內部計算 | 即時 | `point_contrib`算法（fetch_and_calc_vision.py） | ⏳ 未逐行稽核（權重倍數如台積電×8.25疑似寫死經驗值） | — | 是否要改用真實流通市值即時算權重，還是維持經驗值 |
| 11 | Fubon即時報價流（頂部HUD價格） | 即時盤中報價 | `live_price_server.py`（另一聊天室範圍） | 富邦Neo API | 即時 | `initFubonLivePriceStream()` | 不屬於本次範圍 | — | 無（另一session處理） |
| 12 | 海外期貨/美債/美元指數Tick（CL/US10Y/DXY） | 外資避險成本、國際連動判斷 | `CORE_PRESET_ASSETS`（部分base_price可能是寫死參考值） | 內部設定 | — | `initOverseasLiveTickStream()` | ⏳ 未稽核 | — | 需要查證這些base_price是即時更新還是寫死參考 |

---

## 三、這3天完整工作紀錄（2026-09-13 深夜 ～ 2026-09-15）

### ✅ 已完成並修正的問題

| 項目 | 發現的問題 | 解決狀態 |
|---|---|---|
| GEX核心引擎 | 選擇權未沖銷部位從未接過真數據，全部是假高斯曲線 | ✅ 已接上TAIFEX真實optDataDown，含5日歷史回補 |
| 個股期貨法人籌碼(A/B) | 期貨面/現貨面法人籌碼皆為idx排名公式硬湊 | ✅ 已接上TAIFEX大額交易人+TWSE T86真實數據 |
| 法人5日矩陣(C) | 4/5天永遠寫死假數字 | ✅ 已改真實快照累積模式 |
| `fetch_institutional_momentum.py` | 零網路請求，純寫死常數 | ✅ 已接上TAIFEX OpenAPI真實數據 |
| `build_screener_cache.py` | 過去30根K棒是亂數生成假歷史 | ✅ 已接上TWSE批量端點真實歷史，97%覆蓋率 |
| `backfill_snapshots.py` | 3支抓取函式因參數/URL錯誤從未真正抓到數據 | ✅ 已修好，實測確認真的能抓到 |
| `fetch_official_taifex_retail_sentiment()` | daily_change/prev_ratio/broker_snapshot全部寫死 | ✅ 已改真實快照比對 |
| app.js T-1疊加線 | 拿今天曲線亂算充當前一盤 | ✅ 已改真實前一盤資料 |
| app.js populateAiQuantDigest | 忽略使用者選盤，永遠讀最新 | ✅ 已修正 |
| app.js VALID_PASSCODE | 6處寫死字面值 | ✅ 已改用常數 |
| ADR_MAPPING | 變數作用域bug，每列對錯股票；ADR漲跌幅寫死 | ✅ 已修正+改真實Yahoo Finance |
| room.js 假OHLC面板 | TXF/TAIEX/OTC開高低收全部寫死文字 | ✅ 已改真實數據，缺的部分誠實顯示「—」 |
| room.js ADX背離 | 用寫死絕對價位判定 | ✅ 已改真實相對背離判定 |
| room.js 選股雷達 | 雜湊碼生成假訊號 | ✅ 已接上真實screener_cache.json |

### ❌ 還沒處理 / 刻意跳過

| 項目 | 原因 |
|---|---|
| 大戶散戶動能即時串接（Books/Trades） | 明確排除範圍，另一聊天室處理中 |
| 指標源碼逐一校正（JJ鬼爪/SAR/Smart Money Concept等） | 判斷工程量太大不該趕，需要專門session |
| 指標邏輯搬遷後端 | 同上 |
| `handleLiveTick` 0.62固定係數 | 判斷風險輕微+改動有風險，先記錄 |
| app.js 17處不一致的寫死保底值 | 風險低、範圍大，先記錄待清理 |
| `fetch_official_taifex_large_trader()`等4支函式的靜默假保底值 | 記錄待處理 |
| 官股行庫(spot_gov)真實數據 | 已確認無免費官方逐股來源，你已同意維持不可用 |
| 夜盤法人交易的-422保底值 | 今天新發現，還沒處理 |
| 選股雷達「投信認養」「籌碼偏多」篩選 | 需要額外串接institutional資料，還沒做 |
| 總經事件雷達 | 完全未稽核，不確定是真清單還是有捏造 |
| 尋鳥戰情室VRVP、商品搜尋、權值貢獻HUD、海外期貨Tick | 完全未稽核 |

### ✅ 2026-09-15：app.js 全文 + fetch_and_calc_vision.py 剩餘函式稽核完成

依「五、建議的下一步優先順序」第1、2項執行，詳細清單見 `SELF_AUDIT_FINDINGS_TODO.md`「零、」章節。已直接修復並實測：`fetch_official_taifex_specific_traders()`（原本抓HTML從未解析、全寫死）、個股期貨列表`it_badge`投信認養假訊號、`fetch_and_calc_vision.py`死代碼65行、`pc_ratio`查表日期bug、app.js`populateStockFutures()`假比例拆分、app.js快取降級死碼。**尚未commit**，等你確認。

### 🤔 需要你決定的事（彙總，已更新）

1. ~~總經事件雷達優先稽核嗎？~~ **已稽核**：`macro_risk_dashboard`(DXY/US10Y/VIX卡片)零fetch打字寫死且跟真VIX不同步；事件日曆09/16 FOMC後會悄悄變永久空清單。→ 現在就重建成真數據 vs 先只修「會變空清單」這個功能性bug vs 先下架等有真數據
2. `fetch_twse_margin_maintenance()` 融資維持率——官方API證實沒有真正的維持率欄位，現在用線性外推公式編出來的（連抓取成功都一樣）。→ 標記不可用只顯示餘額 vs 保留公式但標「估算值」vs 花時間查其他官方來源
3. 系統性靜默假保底值清理——比原本已知多找到3支關鍵函式（含**現貨價本身**、VIX），共7支後端函式+app.js 34處不一致常數(比原估17處多一倍)+5處過時預設區塊。→ 這次一次做完 vs 先做後端7支(核心交易輸入,風險較高) vs 全部記錄另排session
4. `handleLiveTick` 0.62係數、個股期貨點數貢獻固定乘數(8.25/0.85/1.5/0.1)、GEX引擎固定18%波動率、8大產業固定占比——同一類「工程近似非造假」判斷題，是否要投入時間換真實動態計算？

### 📋 接下來建議的執行順序

1. 上述4項決定（用選項讓使用者選）
2. 指標源碼逐一校正（大工程，需要獨立session專心做）
3. 尋鳥戰情室剩餘未稽核區塊（VRVP、權值貢獻HUD、海外期貨Tick）
4. 選股雷達真實化 + JJ鬼爪/5K戰法從零建置（含本次新發現的個股期貨投信認養徽章，一起規劃逐股多日籌碼歷史系統）

---

*最後更新：2026-09-15。這份文件會持續更新，新開對話室時請先讀這份文件了解現況。*
