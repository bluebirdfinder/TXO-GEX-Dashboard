import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}
url = "https://www.taifex.com.tw/cht/3/largeTraderFutQryExport"

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read()
        csv_text = content.decode('big5', errors='ignore')
        lines = csv_text.splitlines()
        print("=== CSV Export Lines (First 25) ===")
        for l in lines[:25]:
            if '臺股期貨' in l or '契約' in l:
                print(" ", l)
except Exception as e:
    print("CSV Err:", e)
