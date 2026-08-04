import urllib.request
import json
import datetime

def fetch_twse_historical_taiex():
    now_dt = datetime.datetime.now()
    dates_to_query = [
        now_dt.strftime("%Y%m01"),
        (now_dt.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y%m01")
    ]
    
    result = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for d_str in dates_to_query:
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={d_str}&response=json"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                rows = data.get('data', [])
                for r in rows:
                    if len(r) >= 6:
                        # r[0] e.g. "115/07/31"
                        date_parts = r[0].split('/')
                        if len(date_parts) == 3:
                            m_d = f"{int(date_parts[1])}/{int(date_parts[2]):02d}"
                            close_p = float(r[4].replace(',', ''))
                            chg_v = float(r[5].replace(',', ''))
                            prev_p = close_p - chg_v
                            chg_pct = round((chg_v / prev_p * 100), 2) if prev_p > 0 else 0.0
                            result[m_d] = {
                                'date_str': r[0],
                                'spot_price': close_p,
                                'change_val': chg_v,
                                'change_pct': chg_pct
                            }
        except Exception as e:
            print(f"Error querying TWSE for {d_str}: {e}")
            
    return result

if __name__ == '__main__':
    res = fetch_twse_historical_taiex()
    print("TWSE History Parsed Days:", len(res))
    for k in sorted(res.keys())[-5:]:
        print(k, res[k])
