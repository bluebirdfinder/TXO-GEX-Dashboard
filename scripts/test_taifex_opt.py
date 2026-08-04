import urllib.request
from bs4 import BeautifulSoup

def fetch_official_taifex_txo_oi():
    url = "https://www.taifex.com.tw/cht/3/optDailyMarketExcel?marketCode=0"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    call_oi_map = {}
    put_oi_map = {}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')
            print(f"Total table rows found: {len(rows)}")
            
            for r in rows:
                cols = [td.text.strip() for td in r.find_all(['td', 'th'])]
                # Check for TXO contract rows
                if cols and len(cols) >= 10 and cols[0] == 'TXO':
                    try:
                        strike = float(cols[2].replace(',', ''))
                        cp = cols[3].strip()  # Call / Put or 買權/賣權
                        oi_str = cols[9].replace(',', '')  # Open Interest column
                        oi = int(oi_str) if oi_str != '-' else 0
                        
                        if '買權' in cp or cp.upper() == 'CALL' or cp.upper() == 'C':
                            call_oi_map[strike] = call_oi_map.get(strike, 0) + oi
                        elif '賣權' in cp or cp.upper() == 'PUT' or cp.upper() == 'P':
                            put_oi_map[strike] = put_oi_map.get(strike, 0) + oi
                    except (ValueError, IndexError):
                        continue
                        
        print("Call strikes count:", len(call_oi_map))
        print("Put strikes count:", len(put_oi_map))
        if call_oi_map:
            sample_k = sorted(call_oi_map.keys())[:5]
            for k in sample_k:
                print(f"Strike {k}: Call OI = {call_oi_map[k]}, Put OI = {put_oi_map.get(k, 0)}")
                
    except Exception as e:
        print(f"Error fetching TAIFEX TXO Excel: {e}")

if __name__ == '__main__':
    fetch_official_taifex_txo_oi()
