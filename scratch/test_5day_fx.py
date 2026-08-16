import urllib.request
import json
import ssl
import datetime

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

symbols = {
    "usdtwd": "USDTWD=X",
    "dxy": "DX-Y.NYB",
    "usdjpy": "USDJPY=X"
}

fx_5day_history = {}

for key, sym in symbols.items():
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=10d"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            closes = result['indicators']['quote'][0]['close']
            
            history = []
            for i in range(len(timestamps)):
                if closes[i] is not None:
                    dt_str = datetime.datetime.fromtimestamp(timestamps[i]).strftime('%m/%d')
                    price = round(closes[i], 2)
                    prev_p = closes[i-1] if i > 0 and closes[i-1] is not None else price
                    chg = round(price - prev_p, 2)
                    pct = round((chg / prev_p * 100), 2) if prev_p > 0 else 0.0
                    history.append({"date": dt_str, "price": price, "change": chg, "pct": pct})
            
            fx_5day_history[key] = history[-5:]  # last 5 trading days
            print(f"=== {key.upper()} 5-Day History ===")
            for item in fx_5day_history[key]:
                print(" ", item)
    except Exception as e:
        print(f"Err {key}:", e)
