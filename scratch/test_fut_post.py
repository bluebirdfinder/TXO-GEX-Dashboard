import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

url = "https://www.taifex.com.tw/cht/3/futContractsDate"
data = urllib.parse.urlencode({'queryType': '1'}).encode('utf-8')

try:
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        content = resp.read()
        html = content.decode('big5', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        for i, t in enumerate(soup.find_all('table')):
            for r in t.find_all('tr'):
                cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                if cols and len(cols) > 5 and any(k in "".join(cols) for k in ['臺股期貨', '外資', '自營商', '投信']):
                    print(cols)
except Exception as e:
    print("Err:", e)
