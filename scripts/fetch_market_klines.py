"""
fetch_market_klines.py
======================
Authentic Market Multi-Asset & Multi-Timeframe K-Line Data Pipeline
- Real market OHLC price bars from official market endpoints (TWSE / TAIFEX / Yahoo Finance).
- STRICT RULE (AGENTS.md #6):
  1. Price indices (TAIEX, OTC) and yield assets (US10Y, DXY) strictly have Volume = 0 (is_index: True).
  2. Futures and stocks (TXF, CDF, MTX, MXF, CL, 2330, 2454, 2317) have authentic contract / share volume (is_index: False).
"""

import os
import sys
import json
import time
import math
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

SYMBOLS_MAP = {
    'TXF': {'query': '%5ETWII', 'name': '台指期貨', 'is_index': False, 'is_yield': False, 'decimals': 0, 'fut_vol_mult': 1.0, 'base_contract_vol': 3600},
    'TAIEX': {'query': '%5ETWII', 'name': '加權指數', 'is_index': True, 'is_yield': False, 'decimals': 2, 'fut_vol_mult': 0, 'base_contract_vol': 0},
    'OTC': {'query': None, 'name': '櫃買指數', 'is_index': True, 'is_yield': False, 'decimals': 2, 'fut_vol_mult': 0, 'base_contract_vol': 0},
    'CDF': {'query': '2330.TW', 'name': '台積電期貨', 'is_index': False, 'is_yield': False, 'decimals': 0, 'fut_vol_mult': 0, 'base_contract_vol': 0},
    'MTX': {'query': '%5ETWII', 'name': '微台期貨', 'is_index': False, 'is_yield': False, 'decimals': 0, 'fut_vol_mult': 2.2, 'base_contract_vol': 8200},
    'MXF': {'query': '%5ETWII', 'name': '小台期貨', 'is_index': False, 'is_yield': False, 'decimals': 0, 'fut_vol_mult': 1.5, 'base_contract_vol': 5400},
    'US10Y': {'query': '%5ETNX', 'name': '美國10年公債殖利率', 'is_index': True, 'is_yield': True, 'decimals': 3, 'fut_vol_mult': 0, 'base_contract_vol': 0},
    'DXY': {'query': 'DX-Y.NYB', 'name': '美元指數 (DXY)', 'is_index': True, 'is_yield': False, 'decimals': 3, 'fut_vol_mult': 0, 'base_contract_vol': 0},
    'CL': {'query': 'CL=F', 'name': '紐約輕原油期貨', 'is_index': False, 'is_yield': False, 'decimals': 2, 'fut_vol_mult': 0, 'base_contract_vol': 0},
    '2330': {'query': '2330.TW', 'name': '台積電', 'is_index': False, 'is_yield': False, 'decimals': 0, 'fut_vol_mult': 0, 'base_contract_vol': 0},
    '2454': {'query': '2454.TW', 'name': '聯發科', 'is_index': False, 'is_yield': False, 'decimals': 0, 'fut_vol_mult': 0, 'base_contract_vol': 0},
    '2317': {'query': '2317.TW', 'name': '鴻海', 'is_index': False, 'is_yield': False, 'decimals': 1, 'fut_vol_mult': 0, 'base_contract_vol': 0}
}

TF_MAP = {
    '1M': ('1m', '1d', 60),
    '3M': ('5m', '2d', 180),
    '5M': ('5m', '5d', 300),
    '15M': ('15m', '5d', 900),
    '30M': ('30m', '1mo', 1800),
    '1H': ('60m', '3mo', 3600),
    # '4H' is deliberately absent here: Yahoo Finance's chart API has no native 4-hour
    # interval (only 1m/2m/5m/15m/30m/60m/90m/1d/5d/1wk/1mo/3mo), so it can't be fetched
    # directly. It used to just re-request '60m' data under a longer '3mo' range and label
    # it "4H" — that gave more bars, but every bar was still 1-hour spaced, never actually
    # aggregated into real 4-hour candles (found 2026-09-16 while testing the ADX MTF
    # Cloudflare Worker: 4H's bar-to-bar gaps were 3600/1800s, identical to 1H's, not 14400s).
    # Real 4H bars are now synthesized in aggregate_4h_from_1h() below, from this same real
    # 1H fetch (bumped to '3mo' so there's enough history for a decent 4H view too).
    '1D': ('1d', '1y', 86400),
    '1W': ('1wk', '2y', 604800),
    '1Mth': ('1mo', '5y', 2592000)
}

def aggregate_4h_from_1h(hourly_bars):
    """
    Builds real 4-hour OHLCV candles by grouping every 4 consecutive real 1-hour bars
    (positional grouping over the actual fetched sequence, not fixed-clock-boundary
    resampling — TXF/TAIEX trade in specific TW session windows, not continuously, so
    grouping the real sequential bars we have is more meaningful than forcing alignment to
    arbitrary UTC 4-hour clock boundaries that would cut across session gaps).
    """
    bars = []
    for i in range(0, len(hourly_bars) - 3, 4):
        chunk = hourly_bars[i:i + 4]
        bars.append({
            'time': chunk[0]['time'],
            'open': chunk[0]['open'],
            'high': max(b['high'] for b in chunk),
            'low': min(b['low'] for b in chunk),
            'close': chunk[-1]['close'],
            'volume': sum(b['volume'] for b in chunk)
        })
    return bars

import datetime
import ssl

_TPEX_CTX = ssl.create_default_context()
_TPEX_CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT  # TPEx cert lacks Subject Key Identifier (Python 3.13 strict X.509); chain+hostname still verified


def fetch_tpex_otc_daily(months=14):
    """
    REAL 櫃買指數 (OTC index) daily OHLC from the TPEx official monthly endpoint
    www.tpex.org.tw/www/zh-tw/indexInfo/inx?date=YYYY/MM/01 (fields: 日期/開市/最高/最低/收市/漲跌).
    Replaces the old source '006201.TWO' — that is the 元大富櫃50 ETF (price ~46), not the index (~413).
    TPEx publishes no intraday index bars, so only 1D / 1W / 1Mth exist; intraday timeframes are simply
    absent (the room shows no bars rather than a proxy). Volume is 0 (index, AGENTS.md #6 rule 1).
    """
    tz = datetime.timezone(datetime.timedelta(hours=8))
    today = datetime.datetime.now(tz).date()
    y, m = today.year, today.month
    days = []
    for _ in range(months):
        url = f"https://www.tpex.org.tw/www/zh-tw/indexInfo/inx?date={y}/{m:02d}/01&response=json"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, context=_TPEX_CTX, timeout=15) as resp:
                res = json.loads(resp.read().decode('utf-8'))
            for row in res['tables'][0]['data']:
                dt = datetime.datetime.strptime(row[0], '%Y/%m/%d').replace(hour=9, tzinfo=tz)
                o, h, l, c = (float(x.replace(',', '')) for x in row[1:5])
                days.append({'time': int(dt.timestamp()), 'open': o, 'high': h, 'low': l, 'close': c, 'volume': 0, '_d': dt.date()})
        except Exception as e:
            print(f"  [TPEx OTC] {y}-{m:02d} failed: {e}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        time.sleep(0.6)
    days.sort(key=lambda b: b['time'])

    def agg(key_fn):
        out, cur, cur_key = [], None, None
        for b in days:
            k = key_fn(b['_d'])
            if k != cur_key:
                if cur: out.append(cur)
                cur, cur_key = {'time': b['time'], 'open': b['open'], 'high': b['high'], 'low': b['low'], 'close': b['close'], 'volume': 0}, k
            else:
                cur['high'] = max(cur['high'], b['high']); cur['low'] = min(cur['low'], b['low']); cur['close'] = b['close']
        if cur: out.append(cur)
        return out

    strip = lambda bars: [{k: v for k, v in b.items() if k != '_d'} for b in bars]
    return {
        '1D': strip(days),
        '1W': agg(lambda d: d.isocalendar()[:2]),
        '1Mth': agg(lambda d: (d.year, d.month)),
    }


def aggregate_daily_to_wm(days):
    """days: ascending [{'time','open','high','low','close','volume','_d'(date)}] -> {'1D','1W','1Mth'} (real aggregation)."""
    def agg(key_fn):
        out, cur, cur_key = [], None, None
        for b in days:
            k = key_fn(b['_d'])
            if k != cur_key:
                if cur: out.append(cur)
                cur, cur_key = {'time': b['time'], 'open': b['open'], 'high': b['high'], 'low': b['low'], 'close': b['close'], 'volume': b['volume']}, k
            else:
                cur['high'] = max(cur['high'], b['high']); cur['low'] = min(cur['low'], b['low'])
                cur['close'] = b['close']; cur['volume'] += b['volume']
        if cur: out.append(cur)
        return out
    strip = lambda bars: [{k: v for k, v in b.items() if k != '_d'} for b in bars]
    return {'1D': strip(days), '1W': agg(lambda d: d.isocalendar()[:2]), '1Mth': agg(lambda d: (d.year, d.month))}


# Dashboard asset -> (TAIFEX commodity id, Fubon alias). The dashboard's "MTX" is 微台 (TMF) and "MXF" is 小台 (TAIFEX id MTX).
FUTURES_ASSETS = {
    'TXF': ('TX', 'TXF1!'),
    'MXF': ('MTX', 'MXF1!'),
    'MTX': ('TMF', 'TMF1!'),
    'CDF': ('CDF', 'CDF1!'),
}
INTRADAY_KEYS = ('1M', '3M', '5M', '15M', '30M', '1H', '4H')


def fetch_taifex_futures_daily(commodity_id, months=14):
    """
    REAL futures daily bars (day session "一般", front month) with real volume from TAIFEX's official
    futDataDown (期貨每日交易行情). Replaces the old Yahoo ^TWII (spot index!) series with formula-made
    volume. Front month = the first plain YYYYMM contract listed for the date (weekly contracts skipped).
    """
    tz = datetime.timezone(datetime.timedelta(hours=8))
    today = datetime.datetime.now(tz).date()
    y, m = today.year, today.month
    days = []
    for _ in range(months):
        first = datetime.date(y, m, 1)
        last = datetime.date(y + (m == 12), (m % 12) + 1, 1) - datetime.timedelta(days=1)
        url = (f"https://www.taifex.com.tw/cht/3/futDataDown?down_type=1&commodity_id={commodity_id}"
               f"&queryStartDate={first:%Y/%m/%d}&queryEndDate={min(last, today):%Y/%m/%d}")
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode('cp950', errors='ignore')
            seen = set()
            for line in text.splitlines()[1:]:
                c = [x.strip() for x in line.split(',')]
                if len(c) < 18 or c[17] != '一般' or c[0] in seen or not (len(c[2]) == 6 and c[2].isdigit()):
                    continue
                try:
                    o, h, l, cl = (float(c[i].replace(',', '')) for i in (3, 4, 5, 6))
                    vol = int(c[9].replace(',', ''))
                except ValueError:
                    continue
                seen.add(c[0])  # first listed 6-digit contract of the date = front month
                dt = datetime.datetime.strptime(c[0], '%Y/%m/%d').replace(hour=9, tzinfo=tz)
                days.append({'time': int(dt.timestamp()), 'open': o, 'high': h, 'low': l, 'close': cl, 'volume': vol, '_d': dt.date()})
        except Exception as e:
            print(f"  [TAIFEX {commodity_id}] {y}-{m:02d} failed: {e}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        time.sleep(0.6)
    days.sort(key=lambda b: b['time'])
    return aggregate_daily_to_wm(days)


def fetch_all_klines(only=None):
    output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'klines_cache.json')
    out_data = {
        'version': 'v62.2',
        'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'timestamp': int(time.time()),
        'assets': {}
    }

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            prev = json.load(f)
    except Exception:
        prev = {'assets': {}}
    if only:  # refresh just some assets, keep the rest of the existing cache untouched
        out_data['assets'] = prev.get('assets', {})
        out_data['version'] = prev.get('version', out_data['version'])

    # 1. First fetch reference volume profiles from real stocks (2330)
    ref_volumes = {}
    try:
        url_2330 = "https://query1.finance.yahoo.com/v8/finance/chart/2330.TW?interval=15m&range=5d"
        req = urllib.request.Request(url_2330, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
            res = raw['chart']['result'][0]
            v_list = [v for v in res['indicators']['quote'][0].get('volume', []) if v and v > 0]
            if v_list:
                avg_v = sum(v_list) / len(v_list)
                ref_volumes['15M'] = [v / avg_v for v in v_list]
    except Exception as e:
        print(f"Ref volume error: {e}")

    for sym, meta in SYMBOLS_MAP.items():
        if only and sym not in only:
            continue
        sym_name = meta['name']
        is_index = meta['is_index']
        is_yield = meta['is_yield']
        fut_mult = meta.get('fut_vol_mult', 0)
        base_vol = meta.get('base_contract_vol', 0)
        
        print(f"Processing data for {sym} ({sym_name})... is_index={is_index}")
        out_data['assets'][sym] = {
            'name': sym_name,
            'symbol': sym,
            'is_index': is_index,
            'is_yield': is_yield,
            'decimals': meta['decimals'],
            'timeframes': {}
        }
        
        if sym in FUTURES_ASSETS:
            # Futures NEVER come from Yahoo (its series here was the spot index ^TWII / a stock, with a
            # formula-made volume). Daily/weekly/monthly = TAIFEX official; intraday = Fubon Neo bars that
            # scripts/fetch_fubon_futures_klines.py accumulates locally and which are preserved here.
            prev_asset = (prev.get('assets') or {}).get(sym, {})
            keep = {}
            if str(prev_asset.get('intraday_source', '')).startswith('Fubon'):
                keep = {k: v for k, v in (prev_asset.get('timeframes') or {}).items() if k in INTRADAY_KEYS}
                out_data['assets'][sym]['intraday_source'] = prev_asset['intraday_source']
            out_data['assets'][sym]['daily_source'] = 'TAIFEX futDataDown (day session, front month)'
            out_data['assets'][sym]['timeframes'] = {**keep, **fetch_taifex_futures_daily(FUTURES_ASSETS[sym][0])}
            print(f"  -> {sym} futures: " + ", ".join(f"{k}={len(v)}" for k, v in out_data['assets'][sym]['timeframes'].items()))
            continue
        q = meta['query']
        if q is None:  # OTC: official TPEx daily bars only
            out_data['assets'][sym]['timeframes'] = fetch_tpex_otc_daily()
            print(f"  -> OTC official: " + ", ".join(f"{k}={len(v)}" for k, v in out_data['assets'][sym]['timeframes'].items()))
            continue
        for tf_key, (interval, period, sec_len) in TF_MAP.items():
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?interval={interval}&range={period}"
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    raw = json.loads(resp.read().decode('utf-8'))
                    res = raw['chart']['result'][0]
                    timestamps = res.get('timestamp', [])
                    quote = res['indicators']['quote'][0]
                    
                    opens = quote.get('open', [])
                    highs = quote.get('high', [])
                    lows = quote.get('low', [])
                    closes = quote.get('close', [])
                    raw_vols = quote.get('volume', [])
                    
                    bars = []
                    last_valid_vol = 0
                    
                    for i in range(len(timestamps)):
                        o = opens[i] if i < len(opens) else None
                        h = highs[i] if i < len(highs) else None
                        l = lows[i] if i < len(lows) else None
                        c = closes[i] if i < len(closes) else None
                        v = raw_vols[i] if i < len(raw_vols) else None
                        
                        if None in (o, h, l, c) or c == 0:
                            continue
                        
                        # --- VOLUME RESOLUTION ---
                        if is_index or is_yield:
                            # Strict 0 volume for price indices & yields
                            final_vol = 0
                        elif fut_mult > 0:
                            # Taiwan Futures (TXF, MTX, MXF): compute authentic contract volume based on market volatility & turnover
                            rng = max(1.0, abs(h - l))
                            vol_ratio = rng / max(10.0, (c * 0.002))
                            # TF multiplier (1M=0.1x, 5M=0.4x, 15M=1.0x, 1H=3.5x, 1D=35x)
                            tf_ratio = math.sqrt(sec_len / 900.0)
                            calc_vol = int(base_vol * tf_ratio * (0.6 + min(2.5, vol_ratio * 0.5)))
                            final_vol = max(100, calc_vol)
                        else:
                            # Stocks & Commodity Futures (CDF, 2330, 2454, 2317, CL)
                            if v is not None and v > 0:
                                last_valid_vol = int(v)
                                final_vol = int(v)
                            else:
                                final_vol = 0  # no reported volume for this bar: 0, never a carried-forward or invented number
                        
                        bars.append({
                            'time': timestamps[i],
                            'open': round(o, meta['decimals']) if meta['decimals'] > 0 else int(round(o)),
                            'high': round(h, meta['decimals']) if meta['decimals'] > 0 else int(round(h)),
                            'low': round(l, meta['decimals']) if meta['decimals'] > 0 else int(round(l)),
                            'close': round(c, meta['decimals']) if meta['decimals'] > 0 else int(round(c)),
                            'volume': final_vol
                        })
                    
                    if bars:
                        out_data['assets'][sym]['timeframes'][tf_key] = bars
                        non_zero = sum(1 for b in bars if b['volume'] > 0)
                        print(f"  -> {tf_key}: {len(bars)} bars. Non-zero volumes: {non_zero}")
            except Exception as e:
                print(f"  -> {tf_key} failed: {e}")

        # Synthesize real 4H bars from the real 1H bars just fetched (see TF_MAP comment above
        # for why 4H can't be requested from Yahoo directly).
        hourly = None if sym in FUTURES_ASSETS else out_data['assets'][sym]['timeframes'].get('1H')
        if hourly:
            four_h_bars = aggregate_4h_from_1h(hourly)
            if four_h_bars:
                out_data['assets'][sym]['timeframes']['4H'] = four_h_bars
                print(f"  -> 4H: {len(four_h_bars)} bars (aggregated from {len(hourly)} real 1H bars).")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    print(f"Done! Saved authentic klines to {output_file}")

if __name__ == '__main__':
    fetch_all_klines(only=sys.argv[1:] or None)
