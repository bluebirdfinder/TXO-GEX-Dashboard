import urllib.request
import urllib.parse
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

print("=== 1. futContractsDateExport ===")
url1 = "https://www.taifex.com.tw/cht/3/futContractsDateExport"
try:
    req = urllib.request.Request(url1, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        csv_text = resp.read().decode('big5', errors='ignore')
        lines = csv_text.splitlines()
        print(f"Lines count: {len(lines)}")
        for l in lines[:20]:
            if any(k in l for k in ['臺股期貨', '小型臺指', '微型臺指']):
                print(" ", l)
except Exception as e:
    print("Err1:", e)

print("\n=== 2. largeTraderFutQry POST ===")
url2 = "https://www.taifex.com.tw/cht/3/largeTraderFutQry"
params = urllib.parse.urlencode({'queryType': '1', 'marketCode': '0'}).encode('utf-8')
try:
    req = urllib.request.Request(url2, data=params, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        csv_text = resp.read().decode('big5', errors='ignore')
        lines = csv_text.splitlines()
        for l in lines:
            if '臺股期貨' in l:
                print(" ", l[:100])
except Exception as e:
    print("Err2:", e)
