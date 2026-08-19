import urllib.request
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0'}

def get_taifex_tx_prices():
    day_tx_close = None
    night_tx_close = None

    # 1. Fetch Night TX Close from futDailyMarketExcel?marketCode=1
    try:
        url_night = "https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=1"
        req = urllib.request.Request(url_night, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            content = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            for r in soup.find_all('tr'):
                cols = [td.text.strip() for td in r.find_all(['td', 'th'])]
                if cols and len(cols) >= 6 and cols[0] == 'TX':
                    p_str = cols[5].replace(',', '')
                    try:
                        p = float(p_str)
                        if p > 0:
                            night_tx_close = p
                            print(f"[OK] Night TX ({cols[1]}): {night_tx_close}")
                            break
                    except ValueError:
                        continue
    except Exception as e:
        print("Night TX err:", e)

    # 2. Fetch Day TX Close from futDailyMarketExcel?marketCode=0
    try:
        url_day = "https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=0"
        req = urllib.request.Request(url_day, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            content = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            for r in soup.find_all('tr'):
                cols = [td.text.strip() for td in r.find_all(['td', 'th'])]
                if cols and len(cols) >= 6 and cols[0] == 'TX':
                    p_str = cols[5].replace(',', '')
                    try:
                        p = float(p_str)
                        if p > 0:
                            day_tx_close = p
                            print(f"[OK] Day TX ({cols[1]}): {day_tx_close}")
                            break
                    except ValueError:
                        continue
    except Exception as e:
        print("Day TX err:", e)

    return day_tx_close, night_tx_close

day_p, night_p = get_taifex_tx_prices()
print(f"\nResult -> Day TX: {day_p}, Night TX: {night_p}, Shift: {round((night_p or 0) - (day_p or 0), 1) if night_p and day_p else 0}")
