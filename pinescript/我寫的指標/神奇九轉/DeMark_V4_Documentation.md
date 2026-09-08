# 🚀 神奇九轉 V4 (DeMark Sequential V4) 終極實戰手冊與開發藍圖

這份文件為 **DeMark Sequential V4** 版本的權威技術規格書與「量化交易員實戰操作手冊 (Playbook)」。V4 在 V3 的「AI 商品識別」與「模組化武器庫」基礎上，全面引進行業級的**「斜率偵測 (Slope Detection)」**、**「動態 ATR 防暴衝停損 (Dynamic ATR Anti-Stop-Hunting)」**、**「Section 6 Webhook JSON 警報引擎」** 以及 **「雙軌 Telegram 機器人雲端共振網關」**。

---

## 🛡️ 1. 七大過濾器武器庫：分類與微觀邏輯

在 V3/V4 的設計中，我們將過濾指標分為三大集團，讓交易者能根據**當下所處的九轉階段 (發動 vs 竭盡)**，選用最正確的武器。

### 🚀 第一集團：專武級「發動過濾器」(專盯 1~3 初升段/試單)

此階段目標：過濾無效盤整雜訊，抓取真正帶量有力的「破局點」。

* **成交量 (Volume) - 驗證真偽的測謊機**：要求 `當前量 > 均量 x 1.5倍`。避免主力無量畫線，有量才是真金白銀砸出來發動點。
* **布林擠壓 (BB Squeeze) - 專制死魚盤整的核武器**：要求布林通道與肯特納通道「解壓縮」的瞬間才放行。完美解決成交量指標的盲區（能順利抓取原物料那種「無量但沿著邊緣緩漲」的行情）。
* **均線斜率 (MA Slope) - 大勢所趨的順風車**：要求觀察週期（如 60MA/50MA/20MA）斜率必須明確上揚（做多）或下彎（做空）。避免在均線下彎的壓力帶逆勢摸底。
* **MACD (12, 26, 9) - 趨勢動力量級**：【V4 核心升級】改採斜率偵測（`macd > macd[1]`），比傳統 EMA 交叉提前 3~5 根 K 棒抓取動能轉換。
* **AO (5, 34) - 中長期定海神針**：【V4 核心升級】改採動態慣性斜率偵測（`ao > ao[1]`），有效過濾大牛市中的微小拉回假轉折。

### 🎯 第二集團：專武級「竭盡捕捉器」(專盯 7~9, 13 尋找轉折)

此階段目標：趨勢已經走到末端（橡皮筋拉到極限），尋找「動能耗竭」的二次確認，準備逆勢抄底/摸頭。

* **RSI 面板 (14) - 背離之王**：尋找「價格創新低/高，但 RSI 拒絕創新低/高」的底部抬升背離點。【V4 加嚴】加入 5 棒以上時間跨度檢測（`nz(bs_hh[1]) > 5`），徹底剔除高頻假背離。
* **KD 面板 (9,3,3) - 狙擊手的扣板機**：在數字 9 亮起時，等待極度靈敏的 KD 從 80 以上死叉（或 20 以下金叉），作為右側的安全進場點，避免盲目接掉下來的刀子。

### 🛡️ 兩棲輔助集團：避震器與訊號槍

* **ATR (真實波動幅度的均值)**：
  * **搭配 1~3 (壓縮爆發)**：若發生在 ATR 極度壓縮（布林縮口）後的帶量 1~3，是極佳發動點。
  * **搭配 7~13 (極限防守線 - V4 動態機制)**：依據盤面波動率（Squeeze 壓縮 vs 噴發）自動動態調整 ATR 防守倍數（例如 FX 模式下 1.0x 於 Squeeze 時自動放寬至 1.5x；大盤模式下採用 2.2x 專家防守線），完美錯開機構演算法 HFT 的掃單帶。

---

### 🌟 V3/V4 首創：神級 Unicode 狀態系統 (視覺化防護網)

為了解決傳統九轉「無法區分鈍化或背離」的痛點，並完美避免與實體 Emoji (如 JJ 鬼爪指標) 發生遮擋或視覺干擾，V4 繼承並優化了純文字 Unicode 箭頭與星號：

| 情境狀態 (內部判定邏輯) | 視覺呈現 | 代表意義 (實戰反射動作) |
| :--- | :--- | :--- |
| **強勢漲不停 (高檔鈍化)** | **`13 ↗`** | 上升趨勢極強。可以減碼，但**絕對不要放空**，抱緊剩餘股票！ |
| **弱勢跌不停 (低檔鈍化)** | **`13 ↘`** | 下跌趨勢極強。**絕對不要亂接刀子**，它還沒跌完！ |
| **多頭回檔加碼 (均線上彎)** | **`9 ↗`** | 大順風中的小逆風結束。代表「向上的火箭拉回載客了，**準備上車做多！**」 |
| **空頭反彈加空 (均線下彎)** | **`9 ↘`** | 大逆風中的小反彈結束。代表「向下的列車反彈結束，**準備空他！**」 |
| **危險背離/極限 (RSI破壞)** | **`13 ★`** | 極限轉折/背離確認。該跑了，或者是準備反向操作的時候！ |
| **常規竭盡 (無特殊狀況)** | **`單純 9 或 13`** | 一般力道用盡。依照九轉原有紀律應對。 |

---

## ⚡ 2. DeMark V4 核心突破與技術進化

### 1️⃣ **斜率偵測引擎 (Slope Detection Engine)**
傳統 MACD / AO 交叉常有 3~5 根 K 棒的滯後性。V4 導入斜率變動率運算：
* 做多條件：`macd_line > macd_line[1]` (MACD 斜率轉正)
* 做空條件：`macd_line < macd_line[1]` (MACD 斜率轉負)
此技術可在恐慌殺盤或暴力反彈的最初幾根 K 棒立即放行，大幅拉高盈虧比。

### 2️⃣ **動態 ATR 防暴衝防守 (Dynamic ATR Anti-Stop-Hunting)**
* 在低波動（BB Squeeze）期間，市場極易出現惡意插針掃停損。V4 引進動態防禦：當偵測到 Squeeze 狀態，自動拉寬 ATR 停損倍數。
* 在指數大盤模式中，採用 **2.2x ATR 專家防守線**，並對線條進行動態生命週期管理（`line.delete`），維持圖面簡潔不雜亂。

### 3️⃣ **Countdown 倒數時序邏輯修復 (Bug Fix)**
* 傳統 Pine Script 寫法中，`bc_on` 常因 `not b_done` 条件限制，導致第 9 棒無法兼作 Countdown 第 1 棒，延誤一個 Bar。
* V4 徹底解鎖此時序阻擋，實現標準 TD 倒數時序無縫銜接。

### 4️⃣ **Section 6 Webhook Alert 標準 JSON 載荷**
V4 警報版統一導入 Section 6，且**強制加載 `barstate.isconfirmed`**，防範 K 棒未收盤前重複跳發快訊：

```pine
bool alert_buy_13_star  = draw_b13_star and barstate.isconfirmed
bool alert_buy_9_star   = (draw_b9_star or draw_b9) and barstate.isconfirmed
bool alert_sell_13_star = draw_s13_star and barstate.isconfirmed
bool alert_sell_9_star  = (draw_s9_star or draw_s9) and barstate.isconfirmed

if alert_buy_13_star
    string msg_b13 = '{"ticker":"' + syminfo.ticker + '","timeframe":"' + timeframe.period + '","strategy":"神奇九轉 13★ 竭盡","signal":"BUY","price":' + str.tostring(close) + ',"message":"九轉 13★ 底部背離史詩級觸底"}'
    alert(msg_b13, alert.freq_once_per_bar_close)
```

---

## 🤖 3. 雙軌 Telegram 機器人與雲端共振網關 (Cloudflare Worker)

系統嚴格遵循權責分離原則，採用雙軌 Telegram 機器人分工：

```
                    [TradingView V4 Webhook Alert] 
                                  │
                                  ▼
                     [Cloudflare Worker Gateway]
                                  │
  ┌───────────────────────────────┴───────────────────────────────┐
  ▼                                                               ▼
【露米 (Lumi) 籌碼監控機器人】                   【尋鳥量化交易機器人】
(台指期 & 選擇權專屬頻道)                       (VIP 真金白銀當沖共振頻道)
- 權責區：露米籌碼監控機器人專案                - 專屬 Token: 8478998219...
- 15:15 每日盤後文字摘要 + 9 張圖卡             - 專屬 Group: -1004454170968
- 台指期 & 週選擇權 GEX 門鎖策略 Call 訊        - 專打跨商品/全市場 SS 級多指標精選共振
  (GEX 門鎖 + 九轉/5K/JJ 條件觸發)               (九轉 9★/13★ + 5K + JJ 排列組合共振)
```


---

## 🌍 4. 跨市場 V4 專武配置與指南

| 專武名稱 | 適用市場 | 核心 V4 升級技術 | 狀態 |
| :--- | :--- | :--- | :--- |
| **`demark_sequential_v4_indices_alert.pine`** | 格式化台指/全球大盤 | 斜率偵測 + 2.2x ATR + Section 6 Webhook + 尋鳥機器人對接 | **✅ 實戰上線** |
| **`demark_sequential_v4_indices.pine`** | 台指/大盤 (原檔) | 100% 原始未更動純淨備份版 | **✅ 純淨備份** |
| **`demark_sequential_v4_forex.pine`** | G7 貨幣對 / 黃金 | Dynamic ATR (Squeeze 1.5x) + 20MA 斜率 + 倒數時序修復 | **✅ V4 認證** |
| **`demark_sequential_v4_commodities.pine`**| 原油/金屬/農產品 | 200MA 超級循環年線 + Squeeze 無量緩漲 + 大師指南 UI | **✅ V4 認證** |
| **`demark_sequential_v4_equities.pine`** | 台股個股 (規劃) | MACD 斜率 + Squeeze OR 5棒背離 + Webhook | ⏳ 待另存升級 |
| **`demark_sequential_v4_equities_us.pine`**| 美股個股 (規劃) | 50MA 斜率 + 三階市值提示 + Webhook | ⏳ 待另存升級 |
| **`demark_sequential_v4_crypto.pine`** | 比特幣/加密貨幣 (規劃)| 2.5x 爆量過濾 + 2.5x ATR 防插針避震器 | ⏳ 待獨立開發 |
| **`demark_sequential_v4.pine`** | 全商品旗艦大一統 | 6 大專武驗證完畢後，封裝 AI 智能自動路由大腦 | 🎯 終極目標 |

---

> [!NOTE]
> 本手冊為 V4 版本之總綱與技術標準。後續所有 V4 衍生專武皆須遵循「另存新檔防護」、「收盤價確定性鎖定 (`barstate.isconfirmed`)」與「Section 6 Webhook JSON 規範」。
