import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

print("=== 1. POST callsAndPutsDate ===")
url1 = "https://www.taifex.com.tw/cht/3/callsAndPutsDate"
data1 = urllib.parse.urlencode({'queryType': '1'}).encode('utf-8')
try:
    req = urllib.request.Request(url1, data=data1, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read()
        html = content.decode('big5', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        for i, t in enumerate(soup.find_all('table')):
            rows = t.find_all('tr')
            if len(rows) > 5:
                print(f"Table {i} has {len(rows)} rows")
                for r in rows[:15]:
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols:
                        print(" ", cols)
except Exception as e:
    print("Err1:", e)

print("\n=== 2. POST largeTraderFutQry ===")
url2 = "https://www.taifex.com.tw/cht/3/largeTraderFutQry"
data2 = urllib.parse.urlencode({'queryType': '1'}).encode('utf-8')
try:
    req = urllib.request.Request(url2, data=data2, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read()
        html = content.decode('big5', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        for i, t in enumerate(soup.find_all('table')):
            rows = t.find_all('tr')
            if len(rows) > 3:
                for r in rows[:15]:
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols and any('臺股期貨' in c for c in cols):
                        print("  LT TX:", cols)
except Exception as e:
    print("Err2:", e)
