import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

# 1. Fetch TWSE BFI82U (Institutional Stock Net Buy/Sell in TWD)
try:
    url_bfi = "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
    req = urllib.request.Request(url_bfi, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("=== TWSE BFI82U Sample ===")
        print("Title:", data.get("title"))
        for row in data.get("data", []):
            print(" ", row[0], "買進:", row[1], "賣出:", row[2], "買賣超:", row[3])
except Exception as e:
    print("BFI82U err:", e)

# 2. Fetch USD/TWD Exchange Rate via Yahoo Finance
try:
    url_fx = "https://query1.finance.yahoo.com/v8/finance/chart/USDTWD=X?interval=1d&range=5d"
    req = urllib.request.Request(url_fx, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        fx_data = json.loads(resp.read().decode('utf-8'))
        meta = fx_data['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice')
        prev_close = meta.get('chartPreviousClose')
        chg = round(price - prev_close, 4) if price and prev_close else 0.0
        print(f"\n=== USD/TWD Exchange Rate ===")
        print(f"Current USD/TWD: {price}, Prev Close: {prev_close}, Change: {chg}")
except Exception as e:
        print("FX err:", e)
