// JJ 指標 Telegram 轉發腳本 (V4.4 - 定時預暖快取版)
// 架構：每日定時排程預暖快取 → doPost 直接讀快取，零外部呼叫
var token = "8667937062:AAEj6-FwJanpGcbS7kxWy3yEtBQp5xPHhfo";
var chat_id = "-1003969735087";

// ============================================================
// 分段快取讀寫（兩段各 ~60KB，避免超過 100KB 上限）
// ============================================================
function putStocksInCache(cache, stocks) {
  var keys = Object.keys(stocks);
  var half = Math.ceil(keys.length / 2);
  var part1 = {}, part2 = {};
  for (var i = 0; i < keys.length; i++) {
    if (i < half) part1[keys[i]] = stocks[keys[i]];
    else part2[keys[i]] = stocks[keys[i]];
  }
  try {
    cache.put("TW_P1", JSON.stringify(part1), 86400); // 快取 24 小時
    cache.put("TW_P2", JSON.stringify(part2), 86400);
    cache.put("TW_OK", "1", 86400);
    Logger.log("快取成功：共 " + keys.length + " 筆");
  } catch(e) {
    Logger.log("快取寫入失敗：" + e);
  }
}

function getStocksFromCache(cache) {
  if (!cache.get("TW_OK")) return null;
  var p1 = cache.get("TW_P1");
  var p2 = cache.get("TW_P2");
  if (!p1 || !p2) return null;
  var stocks = {};
  var o1 = JSON.parse(p1), o2 = JSON.parse(p2);
  for (var k in o1) stocks[k] = o1[k];
  for (var k in o2) stocks[k] = o2[k];
  return stocks;
}

// ============================================================
// 抓取台股清單（上市 + 上市ETF + 上櫃）
// 僅使用公司基本資料 API（24 小時可用，非交易資料）
// ============================================================
function fetchTaiwanStocks() {
  var stocks = {};

  // 1. 上市公司（含ETF，t187ap03_L 是公司名錄，24h 可用）
  try {
    var r = UrlFetchApp.fetch("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", {muteHttpExceptions: true});
    if (r.getResponseCode() == 200) {
      var data = JSON.parse(r.getContentText());
      for (var i = 0; i < data.length; i++) {
        var code = (data[i]["公司代號"] || "").trim();
        var name = (data[i]["公司簡稱"] || "").trim();
        if (code && name) stocks[code] = name;
      }
      Logger.log("上市公司：" + Object.keys(stocks).length + " 筆");
    }
  } catch(e) { Logger.log("上市 API 失敗：" + e); }

  // 2. 上市 ETF 補充（使用每日行情 API，建議在收盤後執行）
  try {
    var r2 = UrlFetchApp.fetch("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", {muteHttpExceptions: true});
    if (r2.getResponseCode() == 200) {
      var data2 = JSON.parse(r2.getContentText());
      var etfCount = 0;
      for (var i = 0; i < data2.length; i++) {
        var code = (data2[i]["Code"] || "").trim();
        var name = (data2[i]["Name"] || "").trim();
        if (code && name && !stocks[code]) { // 只補上市清單沒有的（主要是 ETF）
          stocks[code] = name;
          etfCount++;
        }
      }
      Logger.log("ETF 補充：" + etfCount + " 筆");
    }
  } catch(e) { Logger.log("ETF 補充 API 失敗（非交易時段正常）：" + e); }

  // 3. 上櫃公司（mopsfin，24h 可用）
  try {
    var r3 = UrlFetchApp.fetch("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", {muteHttpExceptions: true});
    if (r3.getResponseCode() == 200) {
      var data3 = JSON.parse(r3.getContentText());
      var before = Object.keys(stocks).length;
      for (var i = 0; i < data3.length; i++) {
        var code = (data3[i]["公司代號"] || "").trim();
        var name = (data3[i]["公司簡稱"] || "").trim();
        if (code && name) stocks[code] = name;
      }
      Logger.log("上櫃公司：" + (Object.keys(stocks).length - before) + " 筆");
    }
  } catch(e) { Logger.log("上櫃 API 失敗：" + e); }

  Logger.log("合計：" + Object.keys(stocks).length + " 筆");
  return stocks;
}

// ============================================================
// 定時觸發用：每日 19:00 自動執行，預暖快取
// 設定方式：GAS 左側「觸發條件」→ 新增觸發條件
//           函數：refreshStockCache / 事件類型：時間觸發 / 每日 19:00-20:00
// ============================================================
function refreshStockCache() {
  Logger.log("開始刷新台股快取...");
  var cache = CacheService.getScriptCache();
  var stocks = fetchTaiwanStocks();
  putStocksInCache(cache, stocks);
}

// ============================================================
// 測試用：手動執行確認快取是否正常
// ============================================================
function testFetchStocks() {
  refreshStockCache(); // 強制重新抓取並存快取
  var cache = CacheService.getScriptCache();
  var stocks = getStocksFromCache(cache);
  if (!stocks) { Logger.log("快取讀取失敗！"); return; }
  Logger.log("共 " + Object.keys(stocks).length + " 筆台股");
  Logger.log("2330 = " + stocks["2330"]);
  Logger.log("0050 = " + stocks["0050"]);
  Logger.log("00929 = " + stocks["00929"]);
  Logger.log("3481 = " + stocks["3481"]);
}

// ============================================================
// 主入口：TradingView Webhook
// ============================================================
function doPost(e) {
  var data = e.postData.contents;

  try {
    var match = data.match(/商品：([0-9A-Z]{4,6})\s+[^\n]*?🇹🇼/s);
    if (match) {
      var ticker = match[1];
      var cache = CacheService.getScriptCache();
      var stocks = getStocksFromCache(cache);
      // 快取沒有時，才即時抓取（備援）
      if (!stocks) stocks = fetchTaiwanStocks();
      if (stocks && stocks[ticker]) {
        var original = match[0];
        var suffix = original.match(/🇹🇼(.*)/s);
        var replacement = "商品：" + ticker + " " + stocks[ticker] + " 🇹🇼" + (suffix ? suffix[1] : "");
        data = data.replace(original, replacement);
      }
    }
  } catch(e) { Logger.log("翻譯失敗：" + e); }

  var payload = {
    'method': 'sendMessage',
    'chat_id': chat_id,
    'text': data,
    'parse_mode': 'HTML'
  };
  
  try {
    UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/', {
      'method': 'post',
      'payload': payload,
      'muteHttpExceptions': true
    });
  } catch(e) {
    Logger.log("Telegram 發送失敗：" + e);
  }

  // 明確回傳 200 OK 給 TradingView，雖然 GAS 是同步執行，但明確的 response 有助於正常關閉連線
  return ContentService.createTextOutput("OK");
}
