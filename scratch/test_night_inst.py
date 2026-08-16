import urllib.request
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

url = "https://www.taifex.com.tw/cht/3/futContractsDateAh"
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read()
        # Test utf-8 vs big5
        try:
            html = content.decode('utf-8')
        except UnicodeDecodeError:
            html = content.decode('big5', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        for t in tables:
            for r in t.find_all('tr'):
                cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                if cols and any(k in "".join(cols) for k in ['臺股期貨', '小型臺指', '微型臺指', '外資', '自營商']):
                    print(cols)
except Exception as e:
    print("Err:", e)
