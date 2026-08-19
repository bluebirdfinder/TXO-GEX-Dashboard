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
        html = content.decode('big5', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        for i, t in enumerate(soup.find_all('table')):
            for r in t.find_all('tr')[:30]:
                cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                if cols and len(cols) > 2:
                    print(cols)
except Exception as e:
    print("Err:", e)
