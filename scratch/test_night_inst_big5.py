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
        
        current_item = ""
        for r in soup.find_all('tr'):
            cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
            if not cols:
                continue
            row_str = " ".join(cols)
            if '臺股期貨' in row_str and '小型' not in row_str and '微型' not in row_str:
                current_item = "TX"
            elif '小型臺指' in row_str:
                current_item = "MTX"
            elif '微型臺指' in row_str:
                current_item = "Micro"
            
            if current_item and any(k in row_str for k in ['外資', '自營商', '投信']):
                print(f"[{current_item}]", cols)
except Exception as e:
    print("Err:", e)
