# V5 程式撰寫指引 (Coding Guide for Gemini Pro)

> **本文件用途**：給 AI 程式撰寫助手的逐步實作指引。
> **基礎**：以 `5K_Strategy_Master_v4_1.pine`（548 行）為基礎修改。
> **目標輸出**：`5K_Strategy_Master_v5.pine`
> **策略細節參考**：`5K_Strategy_Documentation.md`

---

## 重要規則

1. **不覆蓋 V4.1**，另存新檔 `5K_Strategy_Master_v5.pine`
2. 第一行改為：`indicator("5K Strategy Master V5", shorttitle="5K戰法 V5", overlay=true, max_labels_count=500)`
3. 所有新參數都要加 **Tooltip**（詳見下方各段）
4. 程式分段交付，每段寫完請確認再繼續

---

## 分段實作計畫

### 段落一：停利時框自動縮放（替換 V4.1 第 137~139 行）

**位置**：Section 2 基礎計算，原始程式第 137 行附近

**新增輸入參數群組（加在 `grp_macd` 之前）：**

```pinescript
grp_tp_tf = "停利時框設定 (TP Timeframe) V5"
use_auto_tp_tf = input.bool(true, title="自動適應停利時框 (Auto TP Timeframe)",
    group=grp_tp_tf,
    tooltip="開啟時，停利 MACD 時框依圖表時框自動縮放：\n5分K→1分K / 30分K→5分K / 1H→15分K / 4H→1H / 日K→4H\n\n這修正了 V4.1 的核心問題：\n✅ 歷史回測不再出現因數據缺失造成的假性抱波段\n✅ 實盤停利行為與歷史圖表一致\n\n關閉時改用下方手動指定的時框。")

manual_tp_tf = input.string("1", title="手動停利時框 (Manual TP Timeframe)",
    options=["1","3","5","15","30","60","240","D"],
    group=grp_tp_tf,
    tooltip="關閉自動模式時生效。\n1=1分K, 3=3分K, 5=5分K, 15=15分K, 30=30分K, 60=1H, 240=4H, D=日K")
```

**計算邏輯（加在 Section 2 基礎計算中，替換原本的 `request.security("1", ...)` 行）：**

```pinescript
// [V5] 停利 MACD 時框自動縮放
string auto_tp_tf_val =
    timeframe.period == "1"   ? "1"   :
    timeframe.period == "2"   ? "1"   :
    timeframe.period == "3"   ? "1"   :
    timeframe.period == "5"   ? "1"   :
    timeframe.period == "10"  ? "3"   :
    timeframe.period == "15"  ? "3"   :
    timeframe.period == "30"  ? "5"   :
    timeframe.period == "60"  ? "15"  :
    timeframe.period == "120" ? "30"  :
    timeframe.period == "240" ? "60"  :
    timeframe.period == "D"   ? "240" :
    timeframe.period == "W"   ? "D"   : "1"

string final_tp_tf = use_auto_tp_tf ? auto_tp_tf_val : manual_tp_tf

// 取代原本硬寫死 "1" 的那一行
[macdLine_tp, signalLine_tp, histLine_tp] =
    request.security(syminfo.tickerid, final_tp_tf, ta.macd(close, macd_fast, macd_slow, macd_signal))
is_macd_dead_cross_tp   = ta.crossunder(macdLine_tp, signalLine_tp)
is_macd_golden_cross_tp = ta.crossover(macdLine_tp, signalLine_tp)
```

**停利最低獲利門檻（取代原本 Section 6 固定 0.5 倍的地方）：**

```pinescript
// [V5] 停利最低獲利門檻依時框自動調整
float auto_min_profit_ratio =
    (timeframe.period == "1" or timeframe.period == "3" or timeframe.period == "5") ? 0.3 :
    (timeframe.period == "240" or timeframe.period == "D") ? 0.8 :
    timeframe.period == "W" ? 1.0 : 0.5

// 出場邏輯中，把原本的 0.5 改成 auto_min_profit_ratio
bool has_min_profit = close > (long_entry_price + sl_distance * auto_min_profit_ratio)
// 空單同理
bool has_min_profit = close < (short_entry_price - sl_distance * auto_min_profit_ratio)
```

**Section 6 出場邏輯中，MACD 交叉判斷也要改為 `is_macd_dead_cross_tp` / `is_macd_golden_cross_tp`。**

---

### 段落二：保本停損（Breakeven Stop）

**新增輸入參數群組（加在停利時框設定之後）：**

```pinescript
grp_sl_protect = "停損保護設定 (Stop Loss Protection) V5"

use_be_stop = input.bool(true, title="啟用保本停損 (Breakeven Stop)",
    group=grp_sl_protect,
    tooltip="開啟後，當帳面獲利達到「停損距離 × 保本門檻」時，停損自動移至進場成本，確保此單不虧損。\n\n移動時會同步發送 TG 通知，請手動在交易所更新停損掛單位置。\n\n智能模式下門檻依商品自動設定：\n⚡ 高波動（BTC/NG/HSI）：1.5 倍\n📈 趨勢型（黃金/外匯/原油）：0.8 倍\n📊 其他（台指/那指/標普）：1.0 倍")

manual_be_trigger = input.float(1.0, title="手動保本觸發門檻 (倍停損距離)",
    step=0.1, minval=0.3, maxval=3.0,
    group=grp_sl_protect,
    tooltip="關閉智能模式時生效。獲利達停損距離的幾倍時觸發保本。\n建議：0.8~1.5 之間，依商品波動率調整。")

use_trailing_stop = input.bool(true, title="啟用追蹤停損 (Trailing Stop)",
    group=grp_sl_protect,
    tooltip="保本後，停損線自動向有利方向追蹤，鎖住更多浮動盈利。\n\n⚠️ 在 1/3/5 分 K 時框下，無論此設定為何，追蹤停損自動停用（MACD 停利已足夠）。\n\n移動幅度達 0.5 倍 ATR 時發送 TG 通知，請手動更新交易所停損掛單。")

manual_trail_atr_mult = input.float(1.5, title="手動追蹤停損 ATR 乘數",
    step=0.1, minval=0.5, maxval=5.0,
    group=grp_sl_protect,
    tooltip="關閉智能模式時生效。追蹤停損設在最近高點（做多）或低點（做空）的幾倍 ATR 處。\n數值越小追蹤越緊（容易被洗出），越大越鬆（保護較少）。\n智能模式依時框自動設定：15/30分K=1.5，1H=2.0，4H=2.0，日K=2.5。")
```

**計算邏輯（加在 Section 1.5 智能商品辨識邏輯的 `final_setup_age_limit` 計算之後）：**

```pinescript
// [V5] 保本停損門檻智能預設
float auto_be_trigger =
    array.includes(array.from("BTC","ETH","SOL","XRP"), r) ? 1.5 :
    array.includes(array.from("NG","QG","MNG"), r)          ? 1.5 :
    array.includes(array.from("HSI","HHI","MHI","MCH"), r)  ? 1.5 :
    array.includes(array.from("SI","SIL","PA","PL","MPL"), r)? 1.2 :
    array.includes(array.from("NKD","MNI","FDAX","FDXM"), r)? 1.2 :
    array.includes(array.from("GC","MGC","HG","QC","MHG"), r)? 0.8 :
    array.includes(array.from("CL","MCL","QM"), r)           ? 0.8 :
    array.includes(array.from("6E","M6E","6A","6C","DX","6B","M6B","6J"), r) ? 0.8 :
    1.0
float final_be_trigger = is_auto_active ? auto_be_trigger : manual_be_trigger

// [V5] 追蹤停損 ATR 倍數智能預設
float auto_trail_atr =
    (timeframe.period == "1" or timeframe.period == "3" or timeframe.period == "5") ? 1.0 :
    (timeframe.period == "15" or timeframe.period == "30") ? 1.5 :
    timeframe.period == "60"  ? 2.0 :
    timeframe.period == "240" ? 2.0 :
    timeframe.period == "D"   ? 2.5 : 1.5
float final_trail_atr_mult = is_auto_active ? auto_trail_atr : manual_trail_atr_mult

// [V5] 5分K以下自動停用追蹤停損
bool is_small_tf = timeframe.period == "1" or timeframe.period == "3" or timeframe.period == "5"
bool effective_trailing = use_trailing_stop and not is_small_tf
```

**在 Section 3 狀態變數中新增：**
```pinescript
var bool long_be_triggered  = false  // 記錄多單是否已觸發保本
var bool short_be_triggered = false  // 記錄空單是否已觸發保本
var float long_sl_prev  = na        // 追蹤停損通知節流用
var float short_sl_prev = na
```

**在 Section 6 出場邏輯「if pos_long == 1」的最前面插入（停損判斷之前）：**

```pinescript
// [V5] 保本停損
if pos_long == 1 and use_be_stop and not long_be_triggered
    float sl_dist = math.abs(long_entry_price - long_sl_price)
    if close > (long_entry_price + sl_dist * final_be_trigger) and long_sl_price < long_entry_price
        long_sl_price     := long_entry_price
        long_be_triggered := true

// [V5] 追蹤停損（保本後才啟動）
if pos_long == 1 and effective_trailing and long_be_triggered
    float trail_price = high - (atr_val * final_trail_atr_mult)
    if trail_price > long_sl_price
        long_sl_prev  := long_sl_price
        long_sl_price := trail_price

// 空單對稱邏輯
if pos_short == 1 and use_be_stop and not short_be_triggered
    float sl_dist = math.abs(short_entry_price - short_sl_price)
    if close < (short_entry_price - sl_dist * final_be_trigger) and short_sl_price > short_entry_price
        short_sl_price     := short_entry_price
        short_be_triggered := true

if pos_short == 1 and effective_trailing and short_be_triggered
    float trail_price = low + (atr_val * final_trail_atr_mult)
    if trail_price < short_sl_price
        short_sl_prev  := short_sl_price
        short_sl_price := trail_price
```

**在進場時重置保本標記（`if long_entry_cond` 之後）：**
```pinescript
if long_entry_cond
    // ... 原有設定 ...
    long_be_triggered := false
    long_sl_prev      := na

if short_entry_cond
    // ... 原有設定 ...
    short_be_triggered := false
    short_sl_prev      := na
```

**在出場時也重置（`if long_sl_cond or long_tp_cond` 之後）：**
```pinescript
    long_be_triggered := false
    long_sl_prev      := na
```

---

### 段落三：視覺元素 (BE 標籤) + Dashboard 更新

**保本標籤（加在 Section 8 視覺化呈現，`plotshape` 區塊之後）：**

```pinescript
// [V5] 保本觸發標籤
bool be_just_triggered_long  = long_be_triggered  and not long_be_triggered[1]  and pos_long == 1
bool be_just_triggered_short = short_be_triggered and not short_be_triggered[1] and pos_short == 1

if be_just_triggered_long
    label.new(bar_index, long_entry_price, "BE",
        color=color.aqua, textcolor=color.black,
        style=label.style_label_left, size=size.small,
        tooltip="停損已移至保本（進場成本）")

if be_just_triggered_short
    label.new(bar_index, short_entry_price, "BE",
        color=color.aqua, textcolor=color.black,
        style=label.style_label_right, size=size.small,
        tooltip="停損已移至保本（進場成本）")
```

**Dashboard 新增兩行（在 Section 9 `table.cell` 區塊，Setup Age 之後）：**

```pinescript
// 注意：table.new 的列數需從 10 改為 12

// TP MACD TF（第 10 列）
table.cell(panel, 0, 10, "TP MACD TF:", text_color=color.white, text_halign=text.align_left, text_size=p_size)
table.cell(panel, 1, 10, f_get_tf_name(final_tp_tf), text_color=color.aqua, text_halign=text.align_right, text_size=p_size)

// SL Mode（第 11 列）
string sl_mode_long  = not use_be_stop ? "Fixed" : (not long_be_triggered  ? "Fixed" : (effective_trailing ? "Trailing" : "Breakeven"))
string sl_mode_short = not use_be_stop ? "Fixed" : (not short_be_triggered ? "Fixed" : (effective_trailing ? "Trailing" : "Breakeven"))
string sl_mode_txt   = pos_long == 1 ? sl_mode_long : (pos_short == 1 ? sl_mode_short : "—")
color sl_mode_col    = sl_mode_txt == "Trailing" ? color.lime : (sl_mode_txt == "Breakeven" ? color.aqua : color.gray)
table.cell(panel, 0, 11, "SL Mode:", text_color=color.white, text_halign=text.align_left, text_size=p_size)
table.cell(panel, 1, 11, sl_mode_txt, text_color=sl_mode_col, text_halign=text.align_right, text_size=p_size)
```

---

### 段落四：TG 訊息全面更新

**新增 helper function（加在 `f_trend_dot` 之後）：**

```pinescript
// [V5] 跨時框進場建議
f_get_entry_guidance() =>
    timeframe.period == "1" or timeframe.period == "3" or timeframe.period == "5" ? "" :
    timeframe.period == "15" or timeframe.period == "30" ? "\n💡 建議：可等下根開盤進場，避免追高" :
    timeframe.period == "60" ? "\n💡 建議：降至 15 分 K 確認精確進場點" :
    timeframe.period == "240" ? "\n💡 建議：降至 1H 確認進場點，注意成本差異" :
    "\n💡 建議：明日降至 4H/1H 尋找精確進場點，直接進場成本可能偏差大"
```

**更新進場訊息（在原本 `long_msg` / `short_msg` 字串結尾加入）：**

```pinescript
// long_msg 結尾加上：
"🎯 停利參考：" + f_get_tf_name(final_tp_tf) + " MACD 死叉時出場" + f_get_entry_guidance() + "\n" +
"⏰ " + time_str + "（台灣）"

// short_msg 結尾同理（黃金交叉）
```

**新增保本通知訊息（在 Section 7 訊息字串區塊加入）：**

```pinescript
string long_be_msg = "🔐 【停損移至保本】" + disp_name + " " + tf_name + "\n" +
                     "停損更新至進場價 " + str.tostring(long_entry_price) + "\n" +
                     "已確保此單不虧損！請手動更新交易所停損掛單。\n" +
                     "⏰ " + time_str + "（台灣）"

string short_be_msg = "🔐 【停損移至保本】" + disp_name + " " + tf_name + "\n" +
                      "停損更新至進場價 " + str.tostring(short_entry_price) + "\n" +
                      "已確保此單不虧損！請手動更新交易所停損掛單。\n" +
                      "⏰ " + time_str + "（台灣）"

string long_trail_msg = "🔒 【追蹤停損更新】" + disp_name + " " + tf_name + "\n" +
                        "停損上移至 " + str.tostring(long_sl_price, "#.##") +
                        "（前值 " + str.tostring(long_sl_prev, "#.##") + "）\n" +
                        "浮盈已鎖住 " + str.tostring(long_sl_price - long_entry_price, "#.##") + " 點，請手動更新交易所停損掛單。\n" +
                        "⏰ " + time_str + "（台灣）"

string short_trail_msg = "🔒 【追蹤停損更新】" + disp_name + " " + tf_name + "\n" +
                         "停損下移至 " + str.tostring(short_sl_price, "#.##") +
                         "（前值 " + str.tostring(short_sl_prev, "#.##") + "）\n" +
                         "浮盈已鎖住 " + str.tostring(short_entry_price - short_sl_price, "#.##") + " 點，請手動更新交易所停損掛單。\n" +
                         "⏰ " + time_str + "（台灣）"
```

**新增警報觸發（在原有 `alert()` 區塊之後）：**

```pinescript
// 保本通知（每單一次）
if be_just_triggered_long
    alert(long_be_msg, alert.freq_once_per_bar)
if be_just_triggered_short
    alert(short_be_msg, alert.freq_once_per_bar)

// 追蹤停損更新通知（節流：移動 >= 0.5 ATR 才發）
bool long_trail_notify  = pos_long == 1  and effective_trailing and long_be_triggered  and
                          not na(long_sl_prev)  and math.abs(long_sl_price - long_sl_prev)  >= (atr_val * 0.5)
bool short_trail_notify = pos_short == 1 and effective_trailing and short_be_triggered and
                          not na(short_sl_prev) and math.abs(short_sl_price - short_sl_prev) >= (atr_val * 0.5)

if long_trail_notify
    alert(long_trail_msg, alert.freq_once_per_bar)
    long_sl_prev := long_sl_price   // 重置節流基準

if short_trail_notify
    alert(short_trail_msg, alert.freq_once_per_bar)
    short_sl_prev := short_sl_price
```

---

## 注意事項 / 陷阱提醒

1. **`table.new` 列數**：原本是 `10`，V5 加了兩行，改為 `12`。
2. **`max_labels_count`**：原本 500，BE 標籤額外消耗 labels，如有問題可調高。
3. **`be_just_triggered` 的計算**：使用 `not xxx[1]` 的方式偵測「剛觸發的那一刻」，需確保 `var bool` 在進場時正確重置。
4. **追蹤停損通知的節流**：`long_sl_prev` 每次通知後需更新，否則同一根 K 棒的後續更新也會觸發。
5. **停損移動方向保護**：保本後追蹤時，停損只能往更有利的方向移動（多單只能往上，空單只能往下），程式中的 `if trail_price > long_sl_price` 已確保這點。
6. **V5 的 `is_macd_dead_cross_tp` 變數名稱**要替換掉 V4.1 中的 `is_macd_dead_cross_1m`，出場邏輯中的引用也要一起改。
