# JJ 鬼爪 V3 - 雲端推播部署紀錄

> [!IMPORTANT]
> 本文件包含敏感憑證資訊，請勿公開分享。

## 📡 JJ 指標專屬 Telegram 機器人

| 項目 | 數值 |
|:---|:---|
| **Bot 顯示名稱** | JJ 指標復刻優化機器人 |
| **Bot Username** | `@beyond_jj_indicator_bot` |
| **Bot API Token** | `8667937062:AAEj6-FwJanpGcbS7kxWy3yEtBQp5xPHhfo` |
| **目標群組名稱** | JJ 做多三件套全商品監控 |
| **群組 Chat ID** | `-1003969735087` |

## ⚙️ Google Apps Script (GAS)

| 項目 | 數值 |
|:---|:---|
| **Webhook URL** | `https://script.google.com/macros/s/AKfycbwOIWdRVF_NUl7uFZZLXJDwgo_BIkLH3vTW90fPZJv715aqJxGTl2AfuEfuHBUE7ue3vA/exec` |
| **部署類型** | 網頁應用程式 (Web App) |
| **執行身分** | 您的 Google 帳號 |
| **存取權限** | 所有人 (Anyone) |

### GAS 完整代碼備份 (V4 智能翻譯版 - 已審查修訂)

```javascript
// JJ 指標專屬 Telegram 轉發腳本 (V4 智能翻譯版)
// 修訂記錄：
//   V4.1 - 修正 ETF API 來源，改用 TWSE 官方 ETF 專屬端點
//          修正 regex 加入 s flag，支援跨行匹配
//          保留「| 週期：xxx」後方的字串，不被替換掉

var token = "8667937062:AAEj6-FwJanpGcbS7kxWy3yEtBQp5xPHhfo";
var chat_id = "-1003969735087";

// 取得台股名稱清單（上市 + 上市 ETF + 上櫃），帶有 6 小時快取
function getTaiwanStocks() {
  var cache = CacheService.getScriptCache();
  var cachedData = cache.get("TW_STOCKS_V2");
  
  if (cachedData) {
    return JSON.parse(cachedData);
  }
  
  var stocks = {};
  
  // 1. 上市公司 (TWSE)
  try {
    var twse_res = UrlFetchApp.fetch(
      "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
      {muteHttpExceptions: true}
    );
    if (twse_res.getResponseCode() == 200) {
      var data = JSON.parse(twse_res.getContentText());
      for (var i = 0; i < data.length; i++) {
        var code = (data[i]["公司代號"] || "").trim();
        var name = (data[i]["公司簡稱"] || "").trim();
        if (code && name) stocks[code] = name;
      }
    }
  } catch(e) { Logger.log("TWSE 上市 API 失敗: " + e); }

  // 2. 上市 ETF（使用 TWSE 官方 ETF 專屬端點，最完整的 ETF 清單）
  //    欄位：證券代號 / ETF名稱
  try {
    var etf_res = UrlFetchApp.fetch(
      "https://openapi.twse.com.tw/v1/ETF/domestic",
      {muteHttpExceptions: true}
    );
    if (etf_res.getResponseCode() == 200) {
      var data = JSON.parse(etf_res.getContentText());
      for (var i = 0; i < data.length; i++) {
        var code = (data[i]["證券代號"] || "").trim();
        var name = (data[i]["ETF名稱"] || "").trim();
        if (code && name) stocks[code] = name;
      }
    }
  } catch(e) { Logger.log("TWSE ETF API 失敗: " + e); }
  
  // 3. 上櫃公司 (TPEx)
  try {
    var tpex_res = UrlFetchApp.fetch(
      "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
      {muteHttpExceptions: true}
    );
    if (tpex_res.getResponseCode() == 200) {
      var data = JSON.parse(tpex_res.getContentText());
      for (var i = 0; i < data.length; i++) {
        var code = (data[i]["公司代號"] || "").trim();
        var name = (data[i]["公司簡稱"] || "").trim();
        if (code && name) stocks[code] = name;
      }
    }
  } catch(e) { Logger.log("TPEx 上櫃 API 失敗: " + e); }

  // 存入快取 (21600 秒 = 6 小時)
  try {
    cache.put("TW_STOCKS_V2", JSON.stringify(stocks), 21600);
  } catch(e) { Logger.log("快取寫入失敗: " + e); }
  
  return stocks;
}

// 手動測試函數：在 GAS 編輯器直接執行，確認抓取是否成功
function testFetchStocks() {
  var stocks = getTaiwanStocks();
  Logger.log("共抓取 " + Object.keys(stocks).length + " 筆台股");
  Logger.log("2330 = " + stocks["2330"]);   // 應顯示「台積電」
  Logger.log("0050 = " + stocks["0050"]);   // 應顯示「元大台灣50」
  Logger.log("00929 = " + stocks["00929"]); // 應顯示「復華台灣科技優息」
  Logger.log("3481 = " + stocks["3481"]);   // 上櫃：群創
}

// 主入口：TradingView Webhook 觸發此函數
function doPost(e) {
  var data = e.postData.contents;
  
  // 嘗試識別台股代號並翻譯為中文名稱
  // 訊息格式：商品：2330 Taiwan Semiconductor Manufacturing 🇹🇼 | 週期：日線
  // 目標格式：商品：2330 台積電 🇹🇼 | 週期：日線
  try {
    var match = data.match(/商品：([0-9]{4,6}|[A-Z0-9]{4,6})\s+[^\n]*?🇹🇼/s);
    if (match) {
      var ticker = match[1];
      var stocksMap = getTaiwanStocks();
      if (stocksMap[ticker]) {
        var original = match[0];
        // 保留 🇹🇼 後方的文字（如「| 週期：日線」），只替換商品名稱那段
        var suffix = original.match(/🇹🇼(.*)/s);
        var replacement = "商品：" + ticker + " " + stocksMap[ticker] + " 🇹🇼" + (suffix ? suffix[1] : "");
        data = data.replace(original, replacement);
      }
    }
  } catch(e) {
    Logger.log("翻譯失敗（將發送原文）: " + e);
  }

  // 發送到 Telegram
  var payload = {
    'method': 'sendMessage',
    'chat_id': chat_id,
    'text': data,
    'parse_mode': 'HTML'
  };
  var options = {
    'method': 'post',
    'payload': payload
  };
  UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/', options);
}
```

## 🔔 TradingView 快訊設定步驟

1. 在 TradingView 把 `ghost_claws_v4.pine` 加入到圖表。
2. 點擊右上角的「**鬧鐘 (Alerts)**」圖示 → 「**新增快訊**」。
3. 條件選擇「**JJ 鬼爪 V4**」→「**任意快訊觸發**」。
4. 在「通知」分頁中：
   - ✅ 勾選「**Webhook URL**」
   - 貼入上方 **Webhook URL**
   - ✅ 勾選「**顯示彈出式視窗**」（手機 APP 推播）
5. 訊息欄位保留預設 `{{alert_message}}`（程式碼已內建訊息格式）。
6. 點擊「**建立**」完成。

> [!TIP]
> 此快訊與 5K 戰法的推播完全獨立。5K 戰法通知走 5K 專屬的 GAS，JJ 鬼爪通知走這支 GAS，Telegram 群組也是分開的。

> [!NOTE]
> **部署後的測試步驟**：在 GAS 編輯器中執行 `testFetchStocks()` 函數，確認 Logger 輸出 `2330 = 台積電` 等正確結果後，再重新部署為新版本。
