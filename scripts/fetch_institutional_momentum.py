"""
TAIFEX Institutional Momentum & Retail Positioning Pipeline
===========================================================
Fetches real TAIFEX Foreign/IT/Dealer and Retail Small TX positioning:
1. Foreign Net OI & Day Trading Net
2. Investment Trust (投信) Net OI & Day Trading Net
3. Dealers (自營商) Net OI & Day Trading Net
4. Retail Small TX Net OI & Bull/Bear Ratio (散戶多空比)
5. Historical 5-Day flow matrix (accumulated from real daily snapshots)

Outputs: data/momentum_data.json

Data sources:
- Institutions: TAIFEX official OpenAPI CSV
  (https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersGeneralBytheDate) —
  the same endpoint trading room/room.js falls back to live when this file is stale/missing,
  so the pre-generated file and that live fallback always agree.
- Retail small-TX: fetch_official_taifex_retail_sentiment() from fetch_and_calc_vision.py
  (real futContractsDate + futDailyMarketReport derived long/short/net).
- 5-day history: accumulated in data/momentum_snapshots.json day by day (same pattern as
  data/session_snapshots.json / data/institutional_snapshots.json elsewhere in this repo) —
  days without a real snapshot yet report has_snapshot:false with null fields instead of a
  fabricated number.
"""

import os
import sys
import json
import ssl
import datetime
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "data")
SNAPSHOT_FILE = os.path.join(_DATA_DIR, "momentum_snapshots.json")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

sys.path.insert(0, _SCRIPT_DIR)


def fetch_taifex_institutional_general():
    """
    Real all-products Three Major Institutional Investors daily figures straight from
    TAIFEX's official OpenAPI CSV. Returns {'foreign':{trading_net,oi_net}, 'it':{...},
    'dealer':{...}, 'date':'YYYYMMDD'} or None if the fetch/parse fails.
    """
    url = "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersGeneralBytheDate"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            text = resp.read().decode('utf-8-sig', errors='ignore')
        lines = [l for l in text.strip().split('\n') if l.strip()]
        if len(lines) < 2:
            return None
        header_cols = [h.strip() for h in lines[0].split(',')]
        idx = {h: i for i, h in enumerate(header_cols)}

        result = {}
        latest_date = None
        for line in lines[1:]:
            cols = line.split(',')
            if len(cols) < len(header_cols):
                continue
            date_str = cols[idx['日期']].strip()
            identity = cols[idx['身份別']].strip()
            trading_net = int(cols[idx['多空交易口數淨額']].replace(',', ''))
            oi_net = int(cols[idx['多空未平倉口數淨額']].replace(',', ''))
            latest_date = date_str
            if identity == '自營商':
                result['dealer'] = {'trading_net': trading_net, 'oi_net': oi_net}
            elif identity == '投信':
                result['it'] = {'trading_net': trading_net, 'oi_net': oi_net}
            elif identity in ('外資及陸資', '外資'):
                result['foreign'] = {'trading_net': trading_net, 'oi_net': oi_net}

        if all(k in result for k in ('foreign', 'it', 'dealer')):
            result['date'] = latest_date
            print(f"[OK] TAIFEX Institutional General (OpenAPI): Foreign={result['foreign']['oi_net']}, "
                  f"IT={result['it']['oi_net']}, Dealer={result['dealer']['oi_net']} for {latest_date}")
            return result
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX institutional general data: {e}")
    return None


def load_snapshots():
    try:
        with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_snapshots(snaps):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        json.dump(snaps, f, ensure_ascii=False, indent=2)


def get_recent_weekdays(n):
    """Simple Mon-Fri walk-back (this script is self-contained, no TW-holiday-calendar dependency)."""
    days = []
    cur = datetime.date.today()
    while len(days) < n:
        if cur.weekday() < 5:
            days.append(cur)
        cur -= datetime.timedelta(days=1)
    days.reverse()
    return days


def generate_momentum_data():
    now = datetime.datetime.now()
    snapshots = load_snapshots()

    live = fetch_taifex_institutional_general()

    retail = None
    try:
        from fetch_and_calc_vision import fetch_official_taifex_retail_sentiment
        retail = fetch_official_taifex_retail_sentiment()
    except Exception as e:
        print(f"[Warning] Failed to fetch retail sentiment: {e}")

    data_unavailable = live is None
    if live:
        foreign_oi, foreign_net = live['foreign']['oi_net'], live['foreign']['trading_net']
        it_oi, it_net = live['it']['oi_net'], live['it']['trading_net']
        dealer_oi, dealer_net = live['dealer']['oi_net'], live['dealer']['trading_net']
    else:
        foreign_oi = foreign_net = it_oi = it_net = dealer_oi = dealer_net = None

    mini_mtx = ((retail or {}).get('retail_sentiment_details') or {}).get('mini_mtx') or {}
    retail_long = mini_mtx.get('long_oi')
    retail_short = mini_mtx.get('short_oi')
    retail_net_oi = mini_mtx.get('net_oi')
    retail_total_oi = mini_mtx.get('near_oi')
    retail_ratio = mini_mtx.get('ratio')

    def stance_tag(net):
        if net is None:
            return '⚪ 無即時數據'
        if net > 0:
            return '偏多加碼'
        if net < 0:
            return '偏空減碼'
        return '中性觀望'

    # Persist the snapshot under the date the fetched data actually represents (TAIFEX's feed
    # may still be reporting the last settled trading day, e.g. before today's data is published) —
    # not today's calendar date, or the history would mislabel which day these numbers belong to.
    if live:
        data_date = datetime.datetime.strptime(live['date'], '%Y%m%d').date()
        snap_key = data_date.strftime('%Y-%m-%d')
        snapshots[snap_key] = {
            'date_display': data_date.strftime('%m/%d'),
            'foreign': foreign_oi, 'it': it_oi, 'dealer': dealer_oi,
            'retail_ratio': retail_ratio
        }
        save_snapshots(snapshots)

    # Real 5-day history from persisted snapshots; missing days -> null + has_snapshot:false,
    # never a fabricated number (matches data/session_snapshots.json / institutional_snapshots.json pattern)
    history = []
    for d in get_recent_weekdays(5):
        snap = snapshots.get(d.strftime('%Y-%m-%d'))
        if snap:
            history.append({
                'date': snap.get('date_display', d.strftime('%m/%d')),
                'foreign': snap.get('foreign'), 'it': snap.get('it'), 'dealer': snap.get('dealer'),
                'retail_ratio': snap.get('retail_ratio'), 'has_snapshot': True
            })
        else:
            history.append({
                'date': d.strftime('%m/%d'),
                'foreign': None, 'it': None, 'dealer': None, 'retail_ratio': None, 'has_snapshot': False
            })

    if data_unavailable:
        overall_stance, headline = 'UNKNOWN', '⚪ 無即時數據（TAIFEX OpenAPI 抓取失敗或非交易時段）'
    elif foreign_net > 0 and it_net > 0:
        overall_stance, headline = 'BULLISH', '三大法人今日同步偏多加碼'
    elif foreign_net < 0 and it_net < 0:
        overall_stance, headline = 'BEARISH', '三大法人今日同步偏空減碼'
    else:
        overall_stance, headline = 'MIXED', '三大法人今日方向分歧'

    data = {
        'version': 'v62.2',
        'updated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'date': live['date'] if live else now.strftime('%Y%m%d'),
        'data_unavailable': data_unavailable,
        'summary': {
            'overall_stance': overall_stance,
            'headline': headline
        },
        'institutions': {
            'foreign': {'name': '外資及陸資', 'oi_net': foreign_oi, 'trading_net': foreign_net, 'stance': stance_tag(foreign_net)},
            'it': {'name': '投信', 'oi_net': it_oi, 'trading_net': it_net, 'stance': stance_tag(it_net)},
            'dealer': {'name': '自營商', 'oi_net': dealer_oi, 'trading_net': dealer_net, 'stance': stance_tag(dealer_net)}
        },
        'retail': {
            'small_tx_long': retail_long,
            'small_tx_short': retail_short,
            'small_tx_net_oi': retail_net_oi,
            'small_tx_total_oi': retail_total_oi,
            'bull_bear_ratio_pct': retail_ratio,
            'data_unavailable': retail is None
        },
        'history_5d': history
    }

    output_path = os.path.join(_DATA_DIR, 'momentum_data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Generated institutional momentum and retail data: {output_path}")


if __name__ == '__main__':
    generate_momentum_data()
