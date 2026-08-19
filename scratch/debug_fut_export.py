import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}
url = "https://www.taifex.com.tw/cht/3/futContractsDateExport"

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        csv_text = resp.read().decode('big5', errors='ignore')
        lines = csv_text.splitlines()
        for i, l in enumerate(lines):
            print(f"Line {i}: {l}")
except Exception as e:
    print("Err:", e)
