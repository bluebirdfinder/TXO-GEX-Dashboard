import urllib.request
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

print("=== 1. Testing callsAndPutsDate (Day Options Institutional) ===")
url_opt_inst = "https://www.taifex.com.tw/cht/3/callsAndPutsDate"
try:
    req = urllib.request.Request(url_opt_inst, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read()
        html = content.decode('big5', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")
        for i, t in enumerate(tables):
            text = t.get_text()
            if '臺指選擇權' in text or '買權' in text or '賣權' in text:
                print(f"--- Table {i} ---")
                for r in t.find_all('tr')[:20]:
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols:
                        print(" ", cols)
except Exception as e:
    print("Err callsAndPutsDate:", e)

print("\n=== 2. Testing largeTraderFutQry (Large Trader Futures) ===")
url_lt_fut = "https://www.taifex.com.tw/cht/3/largeTraderFutQry"
try:
    req = urllib.request.Request(url_lt_fut, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read()
        html = content.decode('big5', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        for t in soup.find_all('table'):
            text = t.get_text()
            if '臺股期貨' in text:
                for r in t.find_all('tr'):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols and any('臺股期貨' in c for c in cols):
                        print("  Large Trader TX:", cols)
except Exception as e:
    print("Err largeTraderFutQry:", e)
