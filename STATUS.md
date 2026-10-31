# 📊 TXO GEX Dashboard — 專案現狀與版本紀錄 (v64.18)

**當前版本**：`v64.18` (2026-09-27 網頁一律稱「動能鳥」；指標 IP 保護現況盤點)
**資料與視覺引擎**：`scripts/fetch_and_calc_vision.py` (Black-Scholes VEX/GEX+ 引擎 v64.18)
**即時報價網關**：`scripts/fubon_api_provider.py` & `scripts/live_price_server.py` (WebSocket Fubon Gateway v64.18)
**系統狀態**：`✅ 100% 運作正常`
**網頁通行碼**：（不在文件中公開；不區分大小寫，預設自動通關解鎖）

---

## 📋 2026-10-29 GEX 圖軸固定與自動縮放（前端修正，未升版）

- GEX 籌碼圖 X 軸原本寫死至少 ±7200（實際資料約 ±415 億），長條過短；改為依資料自動縮放，並在所有盤別間共用同一把尺，播放時不跳動。
- 履約價軸固定為所有盤別最小～最大履約價，上下各留 500 點。水平／垂直構圖皆套用。詳見 [HISTORY.md](HISTORY.md) 2026-10-29 條目。


## 📋 2026-10-17 ～ 10-20 現況更新（未升版）

- **現價**：週末／休市顯示最近一個場次（週五夜盤）收盤；富邦與 MIS 備援共用同一套場次規則（`scripts/mis_session.py`）。台指期沒有即時報價時，畫面標「非即時」。
- **戰情室（GitHub Pages）**：本機報價服務有開時，K 線優先讀本機 `klines_cache.json`（Pages 那份缺最新場次）。
- **ADX Pro V3**：微台 15M、4H 與 TV 一致；日線、1H 仍有差異（見 HISTORY.md 2026-10-17～10-20 條目）。Worker 為私有檔，由使用者自行部署（`bluebird-indicators`）。
- **已知限制**：盤中主圖缺本盤別已過去的 K 棒；Worker 因期交所對 Cloudflare 回 520 拿不到台指期即時價。


## 📋 2026-10-09 GEX 範圍盤點與老墨對照（未升版、未改引擎數字）

- 與老墨 MOFI GEX 頁面對照：符號、乘數 50 與通行寫法一致；**我們少乘 0.01（數字為「每 1%」標準值的 100 倍）、σ 用單一 VIX（非每履約價 IV）、只算 w1/w2/fri/mth 四檔且限現價附近履約價**。10/8 實測 OI 涵蓋率：合約 82.3%、再限履約價後 27.0%（口數比例，非 GEX 比例）。翻轉點對 σ 最敏感，牆位置較穩。詳見 [docs/GEX_SCOPE_AND_METHOD_LIMITS.md](docs/GEX_SCOPE_AND_METHOD_LIMITS.md)、[docs/MOFI_GEX_COMPARISON_20261009.md](docs/MOFI_GEX_COMPARISON_20261009.md)。
- 新增：`audit_vs_official.py` 的「GEX 引擎涵蓋率」資訊項；Call／Put Wall 卡片新增「到期組成」一行（牆所在履約價由哪些到期桶堆出，純讀既有逐桶 GEX）。
- **通行版(v2) GEX 並行回補與累積**（2026-10-09，未動引擎、未升版）：`scripts/gex_v2.py`（Black-76、各到期 F、每履約價 IV、全合約、×0.01、淨 GEX 牆、價位掃描翻轉點）、`gex_v2_backfill.py`（回補 2025-10-01～2026-10-08 共 247 天）、`gex_v2_backtest.py`（回測，判斷標準事先登記）、`gex_v2_daily.py`（每日累積，已接 `auto_update.yml`，失敗不影響主流程）；輸出 `data/gex_v2_history.json`（獨立檔）。結果與限制見 [docs/GEX_V2_BACKTEST_20261009.md](docs/GEX_V2_BACKTEST_20261009.md)：翻轉點 v1−v2 平均 −63 點（最近一週 −254）、牆差常達千點關卡、總 GEX 中位數約 0.78 倍且 26/247 天正負號不同；回測**沒有證據顯示 v2 預測力優於 v1**；官方當日 VIX 檔只保留當月，歷史 v1 以代理 VIX 計算（已標示並驗證）。
- 詳細演進見 [HISTORY.md](HISTORY.md) 2026-10-09 條目與 [HANDOFF.md](HANDOFF.md) T 列。
- 待使用者決定（會動交易判斷數字）：補 ×0.01、每履約價 IV（期交所盤後檔已含結算價與最後買賣價）、全合約；建議先做並行第二版＋近 40 日回測。

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

## 📋 選股雷達現況盤點（2026-09-26 盤點；「簡化近似」列已於 2026-10-06 更新，其餘仍為 9/26 數字，未升版、未改任何選股邏輯）

| 項目 | 實測結果（`data/screener_cache.json`、`data/screener_ohlcv_cache.json`，2026-09-24 資料） |
|---|---|
| universe | 1,423 筆＝1,383 檔上市股票/ETF ＋ 40 筆 TAIFEX 指數/股期代碼；畫面「全市場 1,400+ 檔」（`trading room/room.html:793`）略為誇大，實際可掃描 **1,383 檔** |
| 真實歷史涵蓋 | 1,383/1,383（**100%**）股票/ETF 有真實日K；40 筆 TAIFEX 代碼 `history_unavailable`＝設計上不適用（非限流失敗）。舊文件「97%」是把這 40 筆算進分母 |
| 各訊號所需K棒數涵蓋 | ≥35根 1,373 檔（JJ_MACD/CCI）；≥60根 1,362 檔（5K）；≥65根 1,362 檔（九轉）；≥89根 1,344 檔（真🚀🐦，其餘39檔為新掛牌ETF，退回舊近似版） |
| 投信認養／籌碼偏多 | 真資料（`compute_inst_flags()`，T86 滾動10日）：36 檔／613 檔；舊文件寫「還沒接」已更正 |
| **真實移植（Pine 原始碼）** | `macd_state`/`macd_hist_growing`/`cci_value`/`cci_signal`、🚀強火箭/🐦強力藍鳥、📐真5K突破、`demark_buy_state`/`demark_sell_state` |
| **簡化近似** | 已無。🛸⚡✈️🥚 四個近似訊號已於 v64.14 移除，改為 JJ鬼爪 8 訊號（🚀🐦✈️🐣🛸⚡💰⚠️）1:1 忠實移植（見下方 v64.14 條目）；`k5_state`、`demark_state` 舊欄位是否仍有殘留待確認 |
| SSL 驗證 | `scripts/build_screener_cache.py:56-58` 全域關閉憑證驗證（`CERT_NONE`），只回報未修改，見 HISTORY.md |

---

## 🛠️ 2026-10-07 戰情室實測修正（未升版號，版本字串仍 v64.17）

| 項目 | 現況 |
|---|---|
| 圖表即時推進 | 台指期 1～60 分線跟富邦成交價走；4H 以上、副圖指標仍待收盤 K 線更新 |
| 個股報價 | 富邦即時／報價檔／日K 取最新並標日期；報價檔已進 CI；選股快取＋個股日K 走本機工作排程 `TXO-Screener-Cache`（平日 16:30，只 commit） |
| 日內 K 歷史 | `scripts/backfill_taifex_klines.py` 可由期交所官方逐筆檔補回約一個月（與富邦 OHLC 100% 一致） |
| 本機報價服務 | 2026-10-07 21:58 已重啟套用新端點（`/api/stock_quote`、txf `open/high/low`） |
| 已知缺口 | 副圖指標（MACD／CCI／ADX）不隨即時 K 棒更新；搜尋只並列有 K 線資料的期貨（目前只有台積電期貨） |

詳見 [HISTORY.md](HISTORY.md) 最新條目。

---

## 🎯 v64.17 核心更新亮點

- 網頁上的「JJ」稱呼全部改為「動能鳥」（標題、說明、程式內字串與名稱）；Worker 新增 `indicator=bird` 別名。
- 盤點並如實記錄「指標運算搬到私有 Worker」的完成度與公開 repo 內仍含個人指標邏輯的檔案（待使用者決定）。

詳細請見 [HISTORY.md](HISTORY.md) v64.17 條目。

---

## 🎯 v64.16 核心更新亮點

- 指標庫「FVG／Order Blocks (SMC)」勾選框原本沒接任何繪圖，現接上 SMC 覆蓋層（勾選＝多顯示 FVG 與波段訂單塊）。
- Worker（`bluebird-indicators`）原始碼位置與 `indicator=smc` 路由已就緒（私有資料夾，待使用者部署）。

詳細請見 [HISTORY.md](HISTORY.md) v64.16 條目。

---

## 🎯 v64.15 核心更新亮點（SMC）

- **戰情室新增「🧠 SMC」開關**（LuxAlgo Smart Money Concepts，CC BY-NC-SA 4.0，個人非商業）：畫市場結構 BOS／CHoCH、訂單塊、EQH／EQL、FVG、強弱高低點，多方紅、空方綠。演算法在使用者私有 Worker／私有資料夾（不進公開 repo），公開 repo 只有畫圖程式。預設關閉。

詳細請見 [HISTORY.md](HISTORY.md) v64.15 條目。

---


---

> **更早的版本亮點（v64.14 → v44.0）已原樣搬到 [docs/archive/STATUS_版本亮點_v44-v64.14.md](docs/archive/STATUS_版本亮點_v44-v64.14.md)**；完整版本史與根因看 [HISTORY.md](HISTORY.md)。
