import urllib.request
import json
import ssl
import re
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print("=== 1. Testing TAIFEX Night Session Futures Excel (futDailyMarketExcel?marketCode=1) ===")
url_night_excel = "https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=1"
try:
    req = urllib.request.Request(url_night_excel, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read().decode('big5', errors='ignore')
        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.find_all('tr')
        for r in rows[:30]:
            cols = [td.text.strip() for td in r.find_all(['td', 'th'])]
            if cols and len(cols) >= 6 and ('TX' in cols[0] or '臺股期貨' in cols[0] or 'TX' in cols):
                print("Night TX Row:", cols[:10])
except Exception as e:
    print("Night Excel Error:", e)

print("\n=== 2. Testing TAIFEX Day Session Futures (futDailyMarketReport) ===")
url_day_fut = "https://www.taifex.com.tw/cht/3/futDailyMarketReport"
params = urllib.parse.urlencode({'queryType': '2', 'marketCode': '0', 'commodity_id': 'TX'}).encode('utf-8')
try:
    req = urllib.request.Request(url_day_fut, data=params, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        for r in soup.find_all('tr'):
            cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
            if cols and len(cols) >= 6 and cols[0] == 'TX':
                print("Day TX Row:", cols[:8])
except Exception as e:
    print("Day Fut Error:", e)

print("\n=== 3. Testing TAIFEX Night Institutional (futContractsDateAh) ===")
url_night_inst = "https://www.taifex.com.tw/cht/3/futContractsDateAh"
try:
    req = urllib.request.Request(url_night_inst, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables in futContractsDateAh")
        for i, t in enumerate(tables):
            text = t.get_text()
            if '臺股期貨' in text or '外資' in text:
                print(f"--- Table {i} snippet ---")
                for r in t.find_all('tr')[:15]:
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols:
                        print(" ", cols)
except Exception as e:
    print("Night Inst Error:", e)
