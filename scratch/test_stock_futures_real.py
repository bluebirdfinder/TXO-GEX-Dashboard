import urllib.request
import json
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

print("=== Testing TWSE Stock Day Prices (STOCK_DAY_ALL) ===")
url_twse = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
stock_spot_dict = {}
try:
    req = urllib.request.Request(url_twse, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        for d in data:
            code = d.get('Code', '')
            try:
                close_p = float(d.get('ClosingPrice', '0').replace(',', ''))
                chg_p = float(d.get('Change', '0').replace(',', ''))
                prev_p = close_p - chg_p if close_p > 0 else close_p
                pct = round((chg_p / prev_p * 100), 2) if prev_p > 0 else 0.0
                vol = int(int(d.get('TradeVolume', '0').replace(',', '')) / 1000)
                stock_spot_dict[code] = {"price": close_p, "change_pct": pct, "volume": vol}
            except ValueError:
                pass
        print(f"Loaded {len(stock_spot_dict)} TWSE stock spot prices")
        print("Sample 2330 (TSMC):", stock_spot_dict.get('2330'))
except Exception as e:
    print("TWSE Stock Err:", e)
