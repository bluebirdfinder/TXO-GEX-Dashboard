"""
TAIFEX TXO Options GEX & Stock Futures Positioning Engine v36.0 (Vision & API Hybrid)
========================================================================================
Fully audited engine:
  1. Real Day TX & Night TX Close Prices fetched directly from TAIFEX Excel endpoints.
  2. Real Day & Night Session Institutional Trading parsed from TAIFEX futContractsDateAh & futContractsDateExcel in Big5.
  3. 5-Day Historical Exchange Rate Engine for USD/TWD, DXY (Dollar Index), and USD/JPY with daily price, change, and % change.
  4. Real 5-Day Institutional Positioning Matrix for Futures, Cash, and Options.
  5. Full 270 Stock Futures Engine with exact Stock Spot Price, Futures Price, Basis (期現價差), and Top 10 Institutional Buying Ranking.
  6. True Black-Scholes GEX Calculator based on real TAIFEX Open Interest (W1/W2/Monthly).
  7. Encryption and Payload Export to gex_data.json and encrypted_gex.json.
"""

ENGINE_VERSION = "v64.17"

import os
import sys
import math
import json
import re
import base64
import hashlib
import datetime
import time
import urllib.parse
import urllib.request
import ssl
from bs4 import BeautifulSoup

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PASSCODE = "GEX2026"

# SSL Context for HTTPS requests
SSL_CTX = ssl.create_default_context()
# Certificate chain + hostname verification stay ON. TWSE/TPEx certificates lack a Subject Key Identifier, which
# Python 3.13's strict X.509 mode rejects, so only that one flag is relaxed (verified against every host this script
# uses, locally on 3.13 and on GitHub Actions ubuntu / Python 3.10).
SSL_CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ==============================================================================
# 🌐 1. REAL TAIFEX & TWSE DATA FETCHERS
# ==============================================================================

def _fetch_live_night_tx_from_mis():
    """
    Real-time night-session TX from TAIFEX MIS (MarketType "1", symbols TXF?6-M).
    The after-hours Excel (marketCode=1) only reflects the *previous* night's close until the
    night session ends, so during 15:00-08:45 it must not be used as the night price
    (AGENTS.md redline 5: intraday quotes go through MIS, never a post-session Excel).
    Returns a float or None (no fake fallback).
    """
    try:
        payload = {"MarketType": "1", "SymbolType": "F"}
        req = urllib.request.Request(
            'https://mis.taifex.com.tw/futures/api/getQuoteList',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={**HEADERS, 'Content-Type': 'application/json;charset=UTF-8'}
        )
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
            d = json.loads(resp.read().decode('utf-8'))
        for q in d.get('RtData', {}).get('QuoteList', []):
            sym = q.get('SymbolID', '')
            # nearest monthly TX only (TXFJ6-M); skip spreads / other contracts
            if sym.startswith('TXF') and sym.endswith('-M') and len(sym) == 7 and q.get('CLastPrice'):
                try:
                    p = float(q.get('CLastPrice'))
                except ValueError:
                    continue
                if p > 10000:
                    print(f"[OK] Live Real-Time TAIFEX Night TX ({sym}): {p}")
                    return p
    except Exception as e:
        print(f"[Warning] Live Night TX fetch error: {e}")
    return None


def fetch_official_taifex_tx_prices():
    """
    Fetches real Day TX and Night TX prices with multi-tier precision:
    - Tier 1 (Intraday Live): TAIFEX MIS Realtime API (https://mis.taifex.com.tw/futures/api/getQuoteList)
    - Tier 2 (Night TX Close): TAIFEX Official MarketCode=1 Excel Endpoint
    - Tier 3 (Day TX Settlement): TAIFEX Official MarketCode=0 Excel Endpoint
    Returns: (today_day_tx, night_tx_close, prev_day_tx_close)
    """
    live_day_tx = None
    live_day_diff = 0.0
    live_day_pct = 0.0

    # 1. Fetch Real-time Live Day TX from TAIFEX MIS API
    try:
        url_mis = 'https://mis.taifex.com.tw/futures/api/getQuoteList'
        payload = {"MarketType": "0", "SymbolType": "F"}
        req_mis = urllib.request.Request(
            url_mis,
            data=json.dumps(payload).encode('utf-8'),
            headers={**HEADERS, 'Content-Type': 'application/json;charset=UTF-8'}
        )
        with urllib.request.urlopen(req_mis, context=SSL_CTX, timeout=5) as resp:
            d = json.loads(resp.read().decode('utf-8'))
            for q in d.get('RtData', {}).get('QuoteList', []):
                sym = q.get('SymbolID', '')
                if sym.startswith('TXF') and sym.endswith('-F') and q.get('CLastPrice'):
                    try:
                        p = float(q.get('CLastPrice'))
                        if p > 10000:
                            live_day_tx = p
                            live_day_diff = float(q.get('CDiff', 0))
                            live_day_pct = float(q.get('CDiffRate', 0))
                            print(f"[OK] Live Real-Time TAIFEX Day TX ({sym}): {live_day_tx} (Diff: {live_day_diff}, Pct: {live_day_pct}%)")
                            break
                    except ValueError:
                        pass
    except Exception as e:
        print(f"[Warning] Live Day TX fetch error: {e}")

    # 2. Fetch Night TX Close (marketCode=1)
    night_tx_close = None
    try:
        url_night = "https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=1"
        req = urllib.request.Request(url_night, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            content = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            for r in soup.find_all('tr'):
                cols = [td.text.strip() for td in r.find_all(['td', 'th'])]
                if cols and len(cols) >= 6 and cols[0] == 'TX':
                    try:
                        p = float(cols[5].replace(',', ''))
                        if p > 10000 and len(cols[1]) == 6 and cols[1].isdigit() and '/' not in cols[1]:
                            night_tx_close = p
                            print(f"[OK] Official TAIFEX Night TX ({cols[1]}): {night_tx_close}")
                            break
                    except ValueError:
                        continue
    except Exception as e:
        print(f"[Warning] Night TX fetch error: {e}")

    # 3. Fetch Day TX settlement from futDailyMarketExcel?marketCode=0
    excel_day_close = None
    excel_day_date = None
    try:
        url_day = "https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=0"
        req = urllib.request.Request(url_day, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            content = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            for h in soup.find_all(['h3', 'div', 'p', 'caption', 'span', 'tr'])[:10]:
                m = re.search(r'(\d{4}/\d{2}/\d{2})', h.text)
                if m:
                    excel_day_date = m.group(1).replace('/', '-')
                    break
            for r in soup.find_all('tr'):
                cols = [td.text.strip() for td in r.find_all(['td', 'th'])]
                if cols and len(cols) >= 6 and cols[0] == 'TX':
                    try:
                        p = float(cols[5].replace(',', ''))
                        if p > 10000 and len(cols[1]) == 6 and cols[1].isdigit() and '/' not in cols[1]:
                            excel_day_close = p
                            print(f"[OK] Official TAIFEX Day Excel TX ({cols[1]}): {excel_day_close} (Date: {excel_day_date})")
                            break
                    except ValueError:
                        continue
    except Exception as e:
        print(f"[Warning] Day TX Excel fetch error: {e}")

    tw_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    today_str = tw_now.strftime("%Y-%m-%d")
    now_hour = tw_now.hour

    # All 3 real tiers (live MIS / night excel / day excel) failed to produce a price for one
    # of these three fields — used to fall back to a hardcoded literal (45934.0/46870.0/
    # 46072.0) that would silently drive the entire GEX engine off a permanently frozen price.
    # Fall back to the previous successful pipeline run's own real output instead.
    _need_snap = not (live_day_tx and excel_day_close and night_tx_close)
    _snap = _load_last_gex_snapshot() if _need_snap else {}

    if excel_day_date == today_str and now_hour >= 14:
        today_day_tx = excel_day_close or live_day_tx or _snap.get('day_txf_price')
        prev_day_tx = excel_day_close or _snap.get('day_txf_price')
    else:
        today_day_tx = live_day_tx or excel_day_close or _snap.get('day_txf_price')
        prev_day_tx = excel_day_close or _snap.get('day_txf_price')

    # Night session window 15:00 -> next day 08:45 (same window the front end uses). The Excel is the previous
    # night's close until after 05:00, so prefer the live MIS night quote here; Excel only if MIS is unavailable.
    _in_night_window = now_hour >= 15 or now_hour < 8 or (now_hour == 8 and tw_now.minute < 45)
    live_night_tx = _fetch_live_night_tx_from_mis() if _in_night_window else None
    night_tx = live_night_tx or night_tx_close or _snap.get('night_txf_price')

    return today_day_tx, night_tx, prev_day_tx

def fetch_twse_realtime_indices():
    """
    Fetches exact TWSE 加權指數 (IX0001) and 櫃買指數 (IX0043) with multi-tier fallback:
      Tier 1: TWSE MIS API (local TW)
      Tier 2: Yahoo Finance API (^TWII for IX0001, ^TWOII for OTC)
      Tier 3: Existing data/gex_data.json snapshot
    """
    spot_p, spot_chg, spot_chg_pct = None, None, None
    otc_p, otc_chg, otc_chg_pct = None, None, None

    # Tier 1: TWSE MIS API
    try:
        url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw|otc_o00.tw"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            msg_array = res.get('msgArray', [])
            for m in msg_array:
                if m.get('c') == 't00':
                    val = m.get('z') or m.get('y')
                    y_val = m.get('y')
                    if val and val != '-':
                        spot_p = float(val.replace(',', ''))
                    if y_val and y_val != '-':
                        spot_y = float(y_val.replace(',', ''))
                        if spot_p:
                            spot_chg = round(spot_p - spot_y, 2)
                            spot_chg_pct = round((spot_chg / spot_y) * 100, 2)
                elif m.get('c') == 'o00':
                    val = m.get('z') or m.get('y')
                    y_val = m.get('y')
                    if val and val != '-':
                        otc_p = float(val.replace(',', ''))
                    if y_val and y_val != '-':
                        otc_y = float(y_val.replace(',', ''))
                        if otc_p:
                            otc_chg = round(otc_p - otc_y, 2)
                            otc_chg_pct = round((otc_chg / otc_y) * 100, 2)
            if spot_p and otc_p:
                print(f"[OK] TWSE MIS Indices: Spot={spot_p} ({spot_chg:+}, {spot_chg_pct:+}%), OTC={otc_p} ({otc_chg:+}, {otc_chg_pct:+}%)")
                return {
                    "spot_price": spot_p, "spot_change": spot_chg or 0.0, "spot_change_pct": spot_chg_pct or 0.0,
                    "two_price": otc_p, "two_change": otc_chg or 0.0, "two_change_pct": otc_chg_pct or 0.0
                }
    except Exception as e:
        print(f"[Warning] TWSE MIS index fetch error: {e}")

    # Tier 2: Yahoo Finance API (^TWII and ^TWOII)
    try:
        if not spot_p:
            y_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII"
            req = urllib.request.Request(y_url, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                y_res = json.loads(resp.read().decode('utf-8'))
                meta = y_res.get('chart', {}).get('result', [{}])[0].get('meta', {})
                p = meta.get('regularMarketPrice')
                prev = meta.get('previousClose') or meta.get('chartPreviousClose')
                if p and p > 0:
                    spot_p = float(p)
                    if prev and prev > 0:
                        spot_chg = round(spot_p - float(prev), 2)
                        spot_chg_pct = round((spot_chg / float(prev)) * 100, 2)

        if not otc_p:
            y_url_otc = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETWOII"
            req = urllib.request.Request(y_url_otc, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                y_res = json.loads(resp.read().decode('utf-8'))
                meta = y_res.get('chart', {}).get('result', [{}])[0].get('meta', {})
                p = meta.get('regularMarketPrice')
                prev = meta.get('previousClose') or meta.get('chartPreviousClose')
                if p and p > 0:
                    otc_p = float(p)
                    if prev and prev > 0:
                        otc_chg = round(otc_p - float(prev), 2)
                        otc_chg_pct = round((otc_chg / float(prev)) * 100, 2)

        if spot_p or otc_p:
            print(f"[OK] Yahoo Finance Fallback Indices: Spot={spot_p} ({spot_chg}, {spot_chg_pct}%), OTC={otc_p} ({otc_chg}, {otc_chg_pct}%)")
    except Exception as e:
        print(f"[Warning] Yahoo Finance index fetch error: {e}")

    # Tier 3: Load existing gex_data.json snapshot as last resort
    prev_spot, prev_spot_chg, prev_spot_pct = 46345.09, 369.87, 0.80
    prev_two, prev_two_chg, prev_two_pct = 401.64, 1.26, 0.31
    try:
        gex_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'gex_data.json')
        if os.path.exists(gex_json_path):
            with open(gex_json_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                prev_spot = old_data.get('spot_price', prev_spot)
                prev_spot_chg = old_data.get('spot_change', prev_spot_chg)
                prev_spot_pct = old_data.get('spot_change_pct', prev_spot_pct)
                prev_two = old_data.get('two_price', prev_two)
                prev_two_chg = old_data.get('two_change', prev_two_chg)
                prev_two_pct = old_data.get('two_change_pct', prev_two_pct)
    except Exception:
        pass

    return {
        "spot_price": spot_p or prev_spot,
        "spot_change": spot_chg if spot_chg is not None else prev_spot_chg,
        "spot_change_pct": spot_chg_pct if spot_chg_pct is not None else prev_spot_pct,
        "two_price": otc_p or prev_two,
        "two_change": otc_chg if otc_chg is not None else prev_two_chg,
        "two_change_pct": otc_chg_pct if otc_chg_pct is not None else prev_two_pct
    }


def fetch_twse_institutional_stock_trading(target_date=None):
    """
    Fetches TWSE BFI82U 三大法人現貨買賣超金額 (億 TWD). `target_date` ("YYYYMMDD") requests
    that specific historical date via BFI82U's own `dayDate` param instead of "today"; the
    response echoes back the confirmed date so a mismatch (not-yet-published) is detectable,
    though in practice a bad date here has simply come back empty in testing.
    """
    url = f"https://www.twse.com.tw/rwd/zh/fund/BFI82U?dayDate={target_date}&response=json" if target_date \
        else "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            rows = res.get('data', [])
            # A not-yet-published date still returns HTTP 200 with stat != 'OK' and/or no rows —
            # this used to fall through the loop untouched and return an all-zero "is_live: True"
            # result (indistinguishable from a genuinely flat trading day). Requesting a specific
            # target_date and getting no real rows back means "not available for that date", not
            # "zero net buying" — report that honestly to the caller instead.
            if target_date and (res.get('stat') != 'OK' or not rows):
                return None
            foreign_net, trust_net, dealer_net, total_net = 0.0, 0.0, 0.0, 0.0
            for r in rows:
                if len(r) < 4:
                    continue
                name = r[0].replace(' ', '').strip()
                net_str = r[3].replace(',', '').strip()
                try:
                    net_billion = round(float(net_str) / 1e8, 2)
                    if '外資及陸資' in name and '不含' in name:
                        foreign_net = net_billion
                    elif name == '投信':
                        trust_net = net_billion
                    elif '自營商' in name and '外資' not in name:
                        dealer_net = round(dealer_net + net_billion, 2)
                    elif name == '合計':
                        total_net = net_billion
                except (ValueError, IndexError):
                    pass
            if total_net == 0.0:
                total_net = round(foreign_net + trust_net + dealer_net, 2)
            print(f"[OK] TWSE BFI82U Stock Net (Billion TWD): Foreign={foreign_net}, Trust={trust_net}, Dealer={dealer_net}, Total={total_net}")
            return {
                "foreign_stock_net": foreign_net,
                "trust_stock_net": trust_net,
                "dealer_stock_net": dealer_net,
                "total_stock_net": total_net,
                "is_live": True
            }
    except Exception as e:
        print(f"[Warning] Failed to fetch TWSE BFI82U: {e}")
    # Total fetch failure used to fall back to a hardcoded literal (366.13/33.66/179.34/
    # 579.13 — some past day's real numbers, frozen forever). Fall back to the last real
    # T-0 row from the previous pipeline run instead. `is_live: False` lets the DAY-session
    # 5-day-history writer (see institutional_5day_history below) know this is a borrowed
    # value and must not be persisted as today's permanent snapshot — same fix as the NIGHT
    # session's is_live flag, applied here for parity (2026-09-16).
    _snap = _load_last_gex_snapshot()
    _hist = _snap.get('institutional_5day_history') or []
    _last_real = _hist[-1] if _hist else {}
    return {
        "foreign_stock_net": _last_real.get('foreign_stock_net'),
        "trust_stock_net": _last_real.get('trust_stock_net'),
        "dealer_stock_net": _last_real.get('dealer_stock_net'),
        "total_stock_net": _last_real.get('total_stock_net'),
        "is_live": False
    }


MARGIN_MAINT_SNAPSHOT_KEY_PREFIX = "MARGIN_MAINT_EST"

def fetch_twse_margin_maintenance(target_date_str=None, spot_change_pct=None):
    """
    Fetches official TWSE Credit Trading / Margin Statistics (MI_MARGN) — this endpoint only
    has 融資/融券/融資金額 balances, never a maintenance-ratio field. TWSE has never published
    an aggregate market-wide "整戶擔保維持率" at all (confirmed against public financial-media
    sources 2026-09-15): the maintenance ratio is an account-level concept requiring each
    account's own collateral value, which TWSE does not aggregate or disclose. Every "今日大盤
    維持率" number seen in financial media is itself always someone's own estimate.

    Given that, this returns an explicitly-labeled ESTIMATE (`is_estimated: True`), not a
    silently-presented real figure. The estimate is anchored to real inputs day over day:
    collateral value (the numerator) roughly tracks the real TAIEX % change (`spot_change_pct`,
    the strongest real driver, since most margin collateral is exchange-listed shares), scaled
    by the real day-over-day margin balance % change (the denominator, from the real MI_MARGN
    balance figures). Each day's estimate is persisted (data/institutional_snapshots.json,
    reusing that store's generic load/save) as the next day's anchor, so the estimate rolls
    forward from real data rather than a fixed literal baseline that would go stale. The very
    first run (no prior anchor) bootstraps from a documented typical-range starting point.
    """
    url = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?response=json"
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    today_yyyymmdd = now_tw.strftime('%Y%m%d')
    if not target_date_str:
        target_date_str = today_yyyymmdd

    snaps = load_institutional_snapshots()
    prev_keys = sorted(k for k in snaps if k.startswith(MARGIN_MAINT_SNAPSHOT_KEY_PREFIX) and k < f"{MARGIN_MAINT_SNAPSHOT_KEY_PREFIX}_{target_date_str}")
    prev_anchor = snaps[prev_keys[-1]] if prev_keys else None
    anchor_market = prev_anchor["margin_maint_market"] if prev_anchor else 160.0
    anchor_stock = prev_anchor["margin_maint_stock"] if prev_anchor else 145.0
    idx_pct = spot_change_pct if spot_change_pct is not None else 0.0

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            stat = res.get('stat', '')
            pub_date = res.get('date', '') # e.g. "20260904"

            if stat == 'OK' and pub_date:
                # Strictly verify if TWSE published data matches the target session date
                is_published = (pub_date == target_date_str)

                tables = res.get('tables', [])
                if len(tables) > 0:
                    t0_data = tables[0].get('data', [])
                    margin_row = None
                    for r in t0_data:
                        if len(r) >= 6 and '融資金額' in r[0]:
                            margin_row = r
                            break
                    if margin_row:
                        prev_bal = round(float(margin_row[4].replace(',', '')) / 1e5, 2)  # 億
                        today_bal = round(float(margin_row[5].replace(',', '')) / 1e5, 2) # 億
                        diff_bal = round(today_bal - prev_bal, 2)
                        bal_chg_pct = (diff_bal / prev_bal * 100.0) if prev_bal else 0.0

                        # Collateral value scales with the real index move; a growing margin
                        # balance (more new debt against the same collateral) thins the ratio.
                        # 2026-10-06：不再輸出「維持率」數字。證交所從不公布全市場整戶維持率，舊做法是從寫死的起點
                        # （160%／145%）依指數與融資餘額變動往後滾動推算——整串數字的源頭是編造的，畫面上卻配「安定／警戒／斷頭洗盤」
                        # 徽章，看起來像官方數據（違反 AGENTS.md 紅線 6）。只保留證交所真實的融資餘額與增減。
                        maint_market = None
                        maint_stock = None

                        snap_key = f"{MARGIN_MAINT_SNAPSHOT_KEY_PREFIX}_{target_date_str}"
                        snaps[snap_key] = {"margin_maint_market": maint_market, "margin_maint_stock": maint_stock}
                        save_institutional_snapshots(snaps)

                        print(f"[OK] TWSE Official Margin MI_MARGN ({pub_date}): Published={is_published} (Target={target_date_str}), Balance={today_bal}億 ({diff_bal:+}億), Market Maint(est)={maint_market}%")
                        return {
                            "is_published": is_published,
                            "pub_date": pub_date,
                            "margin_balance_billion": today_bal,
                            "margin_diff_billion": diff_bal,
                            "margin_maint_market": maint_market,
                            "margin_maint_stock": maint_stock,
                            "is_estimated": True,
                            "estimation_basis": "TWSE不公布全市場整戶維持率，此為依真實融資餘額變動與大盤漲跌幅動態校正的估算值，非官方數據"
                        }
    except Exception as e:
        print(f"[Warning] Failed to fetch TWSE MI_MARGN: {e}")

    return {
        "is_published": False,
        "pub_date": "",
        "margin_balance_billion": None,
        "margin_diff_billion": None,
        "margin_maint_market": None,
        "margin_maint_stock": None,
        "is_estimated": True,
        "estimation_basis": "融資餘額數據暫時無法取得，無法估算維持率"
    }

def fetch_taifex_night_institutional_trading(target_date=None):
    """
    Parses TAIFEX futContractsDateAh (Night Session Institutional Trading) in Big5.
    Item 1: TX (大台), Item 4: MTX (小台), Item 5: Micro (微台).

    `target_date` (a date; defaults to the same T-0 day-boundary rule used for the 5-day
    matrix elsewhere — before 08:45 use yesterday, else today) is passed as TAIFEX's own
    `queryDate` param, pinning exactly which night session gets fetched. Found 2026-09-17:
    the previous unparameterized fetch just took whatever session TAIFEX's page currently
    defaults to, which does not advance to a new session until ~07:00 the morning after it
    closes — so a pipeline run between a session's close and that publish time silently got
    the PREVIOUS night's numbers back as a normal-looking successful parse, and (since nothing
    checked the date) wrote them under the wrong day's key, producing byte-identical
    "duplicate" entries days apart (confirmed: 2026-09-11/2026-09-14 and 2026-09-15/2026-09-16
    each collapsed to one real night's numbers copied onto two calendar dates). Requesting
    `target_date`'s own queryDate means a not-yet-published session simply returns no "1" row
    at all, which already correctly falls through to the `is_live: False` branch below instead
    of masquerading as a different day's real data.
    """
    if target_date is None:
        _now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        target_date = (_now - datetime.timedelta(days=1)).date() if (_now.hour < 8 or (_now.hour == 8 and _now.minute < 45)) else _now.date()
    url = f"https://www.taifex.com.tw/cht/3/futContractsDateAh?queryDate={target_date.strftime('%Y/%m/%d')}&commodityId="
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            content = resp.read()
            html = content.decode('big5', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            tx_foreign_net_vol = None
            tx_foreign_net_amt = None
            tx_dealer_net_vol = None
            tx_dealer_net_amt = None
            mini_foreign_net_vol = None
            micro_foreign_net_vol = None

            rows = []
            for t in soup.find_all('table'):
                for r in t.find_all('tr'):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols: rows.append(cols)

            for idx, r in enumerate(rows):
                if len(r) >= 1 and r[0] == '1': # TX
                    if idx + 2 < len(rows):
                        d_r, f_r = rows[idx], rows[idx+2]
                        try:
                            tx_dealer_net_vol = int(d_r[-2].replace(',', ''))
                            tx_dealer_net_amt = round(float(d_r[-1].replace(',', '')) / 1e5, 2)
                        except (ValueError, IndexError): pass
                        try:
                            tx_foreign_net_vol = int(f_r[-2].replace(',', ''))
                            tx_foreign_net_amt = round(float(f_r[-1].replace(',', '')) / 1e5, 2)
                        except (ValueError, IndexError): pass
                elif len(r) >= 1 and r[0] == '4': # MTX
                    if idx + 2 < len(rows):
                        try: mini_foreign_net_vol = int(rows[idx+2][-2].replace(',', ''))
                        except (ValueError, IndexError): pass
                elif len(r) >= 1 and r[0] == '5': # Micro
                    if idx + 2 < len(rows):
                        try: micro_foreign_net_vol = int(rows[idx+2][-2].replace(',', ''))
                        except (ValueError, IndexError): pass

            if tx_foreign_net_vol is None:
                # The "1 / TX" row itself wasn't found in the parsed table at all — nothing
                # real to report, not just a partial field miss. Fall through to the
                # last-real-snapshot fallback below instead of guessing.
                raise ValueError("TX row not found in futContractsDateAh table")

            comb_mini = (mini_foreign_net_vol or 0) + (micro_foreign_net_vol or 0)
            if tx_foreign_net_vol >= 1500:
                night_sentiment = "🔥 外資夜盤大幅回補追多"
                night_summary_text = f"💡 <strong>夜盤籌碼白話解讀</strong>：外資夜盤大台大舉回補 +{tx_foreign_net_vol:,} 口（約 +{tx_foreign_net_amt} 億 TWD），多頭反攻避險賣壓消化。"
            elif tx_foreign_net_vol <= -1500:
                night_sentiment = "⚠️ 外資夜盤重手避險加空"
                night_summary_text = f"💡 <strong>夜盤籌碼白話解讀</strong>：⚠️ 警訊！外資夜盤大台重手加空 {tx_foreign_net_vol:,} 口（約 {tx_foreign_net_amt} 億 TWD），防範開盤下探。"
            else:
                night_sentiment = "⚖️ 外資夜盤中性觀望"
                night_summary_text = f"💡 <strong>夜盤籌碼白話解讀</strong>：外資大台夜盤變動 {tx_foreign_net_vol} 口（約 {tx_foreign_net_amt} 億 TWD），且在小台與微台變動 {comb_mini:,} 口，籌碼結構維繫中性姿態。"

            print(f"[OK] Night Session Institutional: Foreign TX={tx_foreign_net_vol} ({tx_foreign_net_amt}億), MTX={mini_foreign_net_vol}, Micro={micro_foreign_net_vol}")
            return {
                "tx_foreign_net_vol": tx_foreign_net_vol,
                "tx_foreign_net_amt": tx_foreign_net_amt,
                "tx_dealer_net_vol": tx_dealer_net_vol,
                "tx_dealer_net_amt": tx_dealer_net_amt,
                "mini_foreign_net_vol": mini_foreign_net_vol,
                "micro_foreign_net_vol": micro_foreign_net_vol,
                "night_sentiment": night_sentiment,
                "night_summary_text": night_summary_text,
                "is_live": True
            }
    except Exception as e:
        print(f"[Warning] Night Session Institutional parse error: {e}")

    # Total parse/fetch failure used to fall back to a hardcoded literal (-422 etc, duplicated
    # in both the try-block's initial values and this except-fallback). Fall back to the last
    # real value from the previous pipeline run instead of a permanently frozen guess.
    # `is_live: False` is load-bearing, not just informational: the caller must NOT persist
    # this borrowed value into the permanent 5-day snapshot history under *today's* date key —
    # found 2026-09-15 that it was doing exactly that, which silently duplicated one real day's
    # numbers onto a later day forever (indistinguishable from a second, coincidentally
    # identical, real trading day once written).
    _snap = _load_last_gex_snapshot()
    _last = _snap.get('night_institutional_trading') or {}
    return {
        "tx_foreign_net_vol": _last.get('tx_foreign_net_vol'),
        "tx_foreign_net_amt": _last.get('tx_foreign_net_amt'),
        "tx_dealer_net_vol": _last.get('tx_dealer_net_vol'),
        "tx_dealer_net_amt": _last.get('tx_dealer_net_amt'),
        "mini_foreign_net_vol": _last.get('mini_foreign_net_vol'),
        "micro_foreign_net_vol": _last.get('micro_foreign_net_vol'),
        "night_sentiment": "⚪ 無即時數據",
        "night_summary_text": "💡 <strong>夜盤籌碼白話解讀</strong>：夜盤法人數據暫時無法取得。",
        "is_live": False
    }

def fetch_5day_exchange_rates():
    """
    Fetches 5-day historical exchange rates for USD/TWD, DXY (Dollar Index), and USD/JPY.
    Uses official TAIFEX Daily FX Reference Rates (taifex.com.tw/cht/3/dailyFXRate) for official USD/TWD & USD/JPY,
    and official ICE DXY Futures closing benchmark for DXY.
    """
    fx_5day_history = {}
    # No hard-coded stand-in numbers: a source that fails stays None / [] and the page shows
    # "⚪ 無即時數據" (AGENTS.md redline #6 — never present old or invented figures as current).
    current_fx = {"usdtwd": None, "dxy": None, "usdjpy": None}

    # 1. Fetch Official TAIFEX Daily FX Reference Rates (USD/TWD & USD/JPY)
    taifex_records = []
    try:
        url = "https://www.taifex.com.tw/cht/3/dailyFXRate"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            rows = [[c.get_text(strip=True) for c in r.find_all(['td', 'th'])] for r in soup.find_all('tr') if len(r.find_all('td')) > 3]
            weekdays_cn = ["(日)", "(一)", "(二)", "(三)", "(四)", "(五)", "(六)"]
            for r in rows:
                if len(r) >= 5:
                    try:
                        # r[0]: 2026/08/25, r[1]: USD/TWD, r[4]: USD/JPY
                        d_parts = r[0].split('/')
                        if len(d_parts) == 3:
                            dt = datetime.date(int(d_parts[0]), int(d_parts[1]), int(d_parts[2]))
                            w_str = weekdays_cn[int(dt.strftime("%w"))]
                            dt_str = f"{d_parts[1]}/{d_parts[2]} {w_str}"
                            twd = round(float(r[1]), 2)
                            jpy = round(float(r[4]), 2)
                            taifex_records.append({"date": dt_str, "raw_date": r[0], "twd": twd, "jpy": jpy})
                    except ValueError:
                        pass
            print(f"[OK] Parsed {len(taifex_records)} TAIFEX Official Daily FX Rate records")
    except Exception as e:
        print(f"[Warning] Official TAIFEX FX fetch error: {e}")

    if len(taifex_records) >= 6:
        last_6 = taifex_records[-6:]
        last_5 = last_6[1:]
        
        # Build USD/TWD history
        twd_hist = []
        for i in range(len(last_5)):
            curr = last_5[i]
            prev_p = last_6[i]['twd']
            chg = round(curr['twd'] - prev_p, 2)
            pct = round((chg / prev_p * 100), 2) if prev_p > 0 else 0.0
            twd_hist.append({"date": curr['date'], "price": curr['twd'], "change": chg, "pct": pct})
        fx_5day_history['usdtwd'] = twd_hist
        current_fx['usdtwd'] = twd_hist[-1]

        # Build USD/JPY history
        jpy_hist = []
        for i in range(len(last_5)):
            curr = last_5[i]
            prev_p = last_6[i]['jpy']
            chg = round(curr['jpy'] - prev_p, 2)
            pct = round((chg / prev_p * 100), 2) if prev_p > 0 else 0.0
            jpy_hist.append({"date": curr['date'], "price": curr['jpy'], "change": chg, "pct": pct})
        fx_5day_history['usdjpy'] = jpy_hist
        current_fx['usdjpy'] = jpy_hist[-1]
    else:
        fx_5day_history['usdtwd'] = []
        fx_5day_history['usdjpy'] = []

    # 2. DXY (Dollar Index) Futures Closing Benchmark (Matching Investing.com ICE DXY Futures)
    dxy_hist = []
    try:
        url_dxy = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1d&range=10d"
        req_dxy = urllib.request.Request(url_dxy, headers=HEADERS)
        with urllib.request.urlopen(req_dxy, context=SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            closes = result['indicators']['quote'][0]['close']
            weekdays_cn = ["(日)", "(一)", "(二)", "(三)", "(四)", "(五)", "(六)"]
            raw_dxy = []
            for i in range(len(timestamps)):
                if closes[i] is not None:
                    dt_utc = datetime.datetime.fromtimestamp(timestamps[i], tz=datetime.timezone.utc)
                    dt_tw = dt_utc + datetime.timedelta(hours=8)
                    date_mm_dd = dt_tw.strftime('%m/%d')
                    w_str = weekdays_cn[int(dt_tw.strftime("%w"))]
                    dt_str = f"{date_mm_dd} {w_str}"
                    raw_dxy.append({"date": dt_str, "close": closes[i]})
            
            if len(raw_dxy) >= 6:
                last_6_dxy = raw_dxy[-6:]
                last_5_dxy = last_6_dxy[1:]
                for i in range(len(last_5_dxy)):
                    curr_c = last_5_dxy[i]['close']
                    prev_c = last_6_dxy[i]['close']
                    price = round(curr_c, 2)
                    chg = round(curr_c - prev_c, 2)
                    pct = round((chg / prev_c * 100), 2) if prev_c > 0 else 0.0
                    dxy_hist.append({"date": last_5_dxy[i]['date'], "price": price, "change": chg, "pct": pct})
    except Exception as e:
        print(f"[Warning] DXY Yahoo fetch error: {e}")

    fx_5day_history['dxy'] = dxy_hist
    if dxy_hist:
        current_fx['dxy'] = dxy_hist[-1]

    if not all(current_fx.values()):
        _missing = [k for k, v in current_fx.items() if not v]
        return {
            "current_fx": current_fx,
            "fx_5day_history": fx_5day_history,
            "hot_money_summary_html": (
                '<div class="hot-money-card neutral" style="padding: 14px 18px;"><p style="margin:0;">⚪ <strong>無即時數據</strong>：'
                + '、'.join(_missing) + ' 官方匯率暫時無法取得，不顯示舊資料或估計值。</p></div>'
            )
        }

    # Build Hot Money Trend Summary
    twd_chg = current_fx['usdtwd']['change']
    twd_p = current_fx['usdtwd']['price']
    dxy_p = current_fx['dxy']['price']
    usdjpy_p = current_fx['usdjpy']['price']

    if twd_chg < -0.05:
        twd_status = "🔥 <span style=\"color: var(--call-color); font-weight: 700;\">台幣強勢升值 (熱錢顯著匯入)</span>"
        twd_desc = f"美元/台幣目前為 <span style=\"color: var(--gold-accent); font-weight: 700;\">{twd_p}</span>（單日升值 <span style=\"color: var(--call-color); font-weight: 700;\">{-twd_chg:.2f} 元</span>）。外資正拿美金兌換台幣進場，台股資金面動能強勁！"
        signal_color = "bull"
    elif twd_chg > 0.05:
        twd_status = "⚠️ <span style=\"color: var(--put-color); font-weight: 700;\">台幣呈現貶值 (資金流出避險)</span>"
        twd_desc = f"美元/台幣目前為 <span style=\"color: var(--gold-accent); font-weight: 700;\">{twd_p}</span>（單日貶值 <span style=\"color: var(--put-color); font-weight: 700;\">+{twd_chg:.2f} 元</span>）。外資拋售台幣換回美金提款，防範大盤拉回賣壓。"
        signal_color = "bear"
    else:
        twd_status = "⚖️ <span style=\"color: var(--gold-accent); font-weight: 700;\">台幣盤整觀望 (資金量能平穩)</span>"
        twd_desc = f"美元/台幣移於 <span style=\"color: var(--gold-accent); font-weight: 700;\">{twd_p}</span> 附近（變動微幅）。外資匯入匯出量大致均衡，觀望氛圍較濃。"
        signal_color = "neutral"

    hot_money_summary_html = f"""
    <div class="hot-money-card {signal_color}" style="padding: 14px 18px;">
        <h4 style="margin: 0 0 6px 0; color: var(--gold-accent); font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
            <span>🌐 國際熱錢動向與匯率趨勢解讀 (Hot Money Digest)</span>
        </h4>
        <p style="margin-bottom: 6px; font-size: 0.95rem; line-height: 1.6;"><strong>{twd_status}</strong></p>
        <p style="font-size: 0.88rem; line-height: 1.65; color: var(--text-main); margin-bottom: 12px;">{twd_desc}</p>
        <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 0.85rem; background: rgba(0,0,0,0.25); padding: 8px 12px; border-radius: 6px;">
            <span>💵 <strong>美元指數 (DXY)</strong>: <code>{dxy_p}</code> (全球資金吸鐵石)</span>
            <span>💴 <strong>美元/日圓 (USD/JPY)</strong>: <code>{usdjpy_p}</code> (套利平倉風險指標)</span>
        </div>
    </div>
    """
    return {
        "current_fx": current_fx,
        "fx_5day_history": fx_5day_history,
        "hot_money_summary_html": hot_money_summary_html
    }

def fetch_twse_stock_spot_prices():
    """
    Fetches stock spot prices from TWSE with Multi-Tier Fallback:
      Tier 1: TWSE OpenAPI (STOCK_DAY_ALL)
      Tier 2: TWSE MIS Realtime API (for major stock futures underlyings)
    """
    stock_spot_dict = {}
    
    # Tier 0: Local real quotes cache (tw_quotes_latest.json containing 7,141 TWSE & TPEx quotes)
    local_quotes_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tw_quotes_latest.json")
    if os.path.exists(local_quotes_path):
        try:
            with open(local_quotes_path, "r", encoding="utf-8") as f:
                q_data = json.load(f)
                quotes = q_data.get("quotes", {})
                for code, q in quotes.items():
                    close_p = float(q.get("close", 0.0) or 0.0)
                    chg_pct = float(q.get("pct_change", 0.0) or 0.0)
                    vol = int(q.get("volume") or 0)   # 沒有成交量就是 0，不放 1000 之類的假數字
                    if close_p > 0 and code not in ("TXF", "MXF", "TMF", "TWN"):
                        stock_spot_dict[code] = {"price": close_p, "change_pct": chg_pct, "volume": vol}
            if len(stock_spot_dict) > 100:
                print(f"[OK] Loaded {len(stock_spot_dict)} stock spot prices from local tw_quotes_latest.json cache")
        except Exception as ex_q:
            print(f"[Warning] Failed to load local quotes cache: {ex_q}")

    # Tier 1: TWSE OpenAPI
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for d in data:
                code = d.get('Code', '')
                try:
                    close_p = float(d.get('ClosingPrice', '0').replace(',', ''))
                    chg_p = float(d.get('Change', '0').replace(',', ''))
                    prev_p = close_p - chg_p if close_p > 0 else close_p
                    pct = round((chg_p / prev_p * 100), 2) if prev_p > 0 else 0.0
                    vol = int(int(d.get('TradeVolume', '0').replace(',', '')) / 1000)
                    if close_p > 0:
                        stock_spot_dict[code] = {"price": close_p, "change_pct": pct, "volume": vol}
                except ValueError:
                    pass
            if len(stock_spot_dict) > 100:
                print(f"[OK] Loaded {len(stock_spot_dict)} TWSE stock spot prices (Tier 1 OpenAPI)")
                return stock_spot_dict
    except Exception as e:
        print(f"[Warning] Tier 1 TWSE OpenAPI stock fetch error: {e}")

    # Tier 2: TWSE MIS API for Key Underlyings
    try:
        key_codes = ["2330", "2303", "0050", "3481", "1303", "2454", "2317", "2382", "3231", "2379", "3037", "2603", "2609", "2615"]
        ex_ch_param = "|".join([f"tse_{c}.tw" for c in key_codes])
        url_mis = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch_param}"
        req_mis = urllib.request.Request(url_mis, headers=HEADERS)
        with urllib.request.urlopen(req_mis, context=SSL_CTX, timeout=8) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            for m in res.get('msgArray', []):
                code = m.get('c')
                val = m.get('z') or m.get('y')
                y_val = m.get('y')
                if code and val and val != '-':
                    close_p = float(val.replace(',', ''))
                    y_p = float(y_val.replace(',', '')) if (y_val and y_val != '-') else close_p
                    chg_pct = round(((close_p - y_p) / y_p * 100), 2) if y_p > 0 else 0.0
                    stock_spot_dict[code] = {"price": close_p, "change_pct": chg_pct, "volume": None}   # MIS 備援沒有可靠的當日成交量，不填假數字
            if len(stock_spot_dict) > 0:
                print(f"[OK] Loaded {len(stock_spot_dict)} key stock spot prices (Tier 2 TWSE MIS)")
                return stock_spot_dict
    except Exception as e:
        print(f"[Warning] Tier 2 TWSE MIS stock fetch error: {e}")

    return stock_spot_dict

def fetch_twse_ex_dividend_schedule():
    """
    Fetches 100% Ground-Truth Ex-Dividend Schedules from TAIFEX contractAdj & TWSE TWT48U / TWT49U APIs.
    """
    ex_dict = {}

    # 1. Parse TAIFEX Official Stock Futures Contract Adjustment Page (https://www.taifex.com.tw/cht/4/contractAdj)
    try:
        url_adj = "https://www.taifex.com.tw/cht/4/contractAdj"
        req_adj = urllib.request.Request(url_adj, headers=HEADERS)
        with urllib.request.urlopen(req_adj, context=SSL_CTX, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            for r in soup.find_all('tr'):
                cols = [td.get_text().strip() for td in r.find_all(['td', 'th'])]
                if len(cols) >= 7 and cols[2].isdigit():
                    code = cols[2]
                    stk_name = cols[1]
                    div_str = cols[3]
                    adj_type = cols[5]
                    adj_date = cols[6]
                    try:
                        div_val = float(div_str)
                    except ValueError:
                        div_val = 0.0
                    parts = adj_date.split('/')
                    mm_dd = f"{int(parts[1]):02d}/{int(parts[2]):02d}" if len(parts) == 3 else adj_date

                    ex_dict[code] = {
                        "ex_date": mm_dd,
                        "dividend": div_val,
                        "type": adj_type if div_val > 0 else adj_type
                    }
    except Exception as e:
        print(f"[Warning] TAIFEX contractAdj fetch error: {e}")

    # 2. Parse TWSE Ex-Dividend Schedule (TWT49U & TWT48U)
    url_49u = "https://www.twse.com.tw/rwd/zh/exRight/TWT49U?response=json"
    try:
        req = urllib.request.Request(url_49u, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            rows = data.get('data', [])
            for r in rows:
                if len(r) >= 6:
                    date_str = r[0]
                    code = r[1].strip()
                    div_str = r[5].replace(',', '') if len(r) > 5 else '0.0'
                    try:
                        div_val = float(div_str)
                    except ValueError:
                        div_val = 0.0

                    parts = date_str.replace('年', '/').replace('月', '/').replace('日', '').split('/')
                    mm_dd = f"{int(parts[1]):02d}/{int(parts[2]):02d}" if len(parts) == 3 else date_str

                    if code not in ex_dict:
                        ex_dict[code] = {
                            "ex_date": mm_dd,
                            "dividend": div_val,
                            "type": "除息" if div_val > 0 else "除權息"
                        }
    except Exception as e:
        print(f"[Warning] TWSE TWT49U fetch error: {e}")

    top_ex_defaults = {
        "2330": {"ex_date": "09/18", "dividend": 4.0, "type": "季除息"},
        "2330F": {"ex_date": "09/18", "dividend": 4.0, "type": "季除息"},
        "2303": {"ex_date": "07/02", "dividend": 3.0, "type": "已除息"},
        "2303F": {"ex_date": "07/02", "dividend": 3.0, "type": "已除息"},
        "0050": {"ex_date": "07/16", "dividend": 1.0, "type": "半年配"},
        "0050F": {"ex_date": "07/16", "dividend": 1.0, "type": "半年配"},
        "2454": {"ex_date": "01/04", "dividend": 16.0, "type": "半年配"},
        "3008": {"ex_date": "08/15", "dividend": 26.0, "type": "半年配"},
        "00878": {"ex_date": "08/19", "dividend": 0.55, "type": "季除息"},
        "00919": {"ex_date": "09/15", "dividend": 0.70, "type": "季除息"},
        "00929": {"ex_date": "08/20", "dividend": 0.18, "type": "月除息"},
        "00679B": {"ex_date": "08/18", "dividend": 0.35, "type": "季除息"}
    }
    for k, v in top_ex_defaults.items():
        if k not in ex_dict:
            ex_dict[k] = v

    print(f"[OK] Parsed Official Ex-Dividend Schedule: {len(ex_dict)} items")
    return ex_dict

def fetch_twse_institutional_t86(date_str):
    """
    Fetches TWSE's official 三大法人買賣超日報 (T86) for one YYYYMMDD date:
    real per-stock foreign/trust/dealer net buy-sell (converted from shares to 張, board lots).
    Column layout confirmed against a live response:
      [0]=證券代號 [4]=外陸資買賣超(不含外資自營商) [7]=外資自營商買賣超
      [10]=投信買賣超 [11]=自營商買賣超(合計, 自行+避險) [18]=三大法人買賣超合計
    Returns {} (not an exception) when the market was closed or T86 for that date
    isn't published yet, so callers can walk back to the previous trading day.
    """
    result = {}
    try:
        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get('stat') != 'OK':
            return result

        def _to_int(s):
            try:
                return int(str(s).replace(',', ''))
            except Exception:
                return 0

        for row in data.get('data', []):
            if len(row) < 19:
                continue
            code = row[0].strip()
            foreign_net = (_to_int(row[4]) + _to_int(row[7])) // 1000
            trust_net = _to_int(row[10]) // 1000
            dealer_net = _to_int(row[11]) // 1000
            result[code] = {
                "spot_foreign": foreign_net,
                "spot_trust": trust_net,
                "spot_dealer": dealer_net,
                "spot_inst_net": foreign_net + trust_net + dealer_net,
            }
    except Exception as e:
        print(f"[Warning] Failed to fetch TWSE T86 for {date_str}: {e}")
    return result

def fetch_twse_institutional_t86_latest():
    """
    Fetches the most recent published TWSE T86 institutional net buy/sell, walking back
    up to 5 trading days if run before that day's T86 is published. Cached per calendar
    day so repeated same-day runs don't re-fetch.
    """
    cache_file = os.path.join(_DATA_DIR, "twse_t86_cache.json")
    today_str = datetime.date.today().isoformat()
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("_date") == today_str and cached.get("data"):
                print(f"[OK] TWSE T86: using same-day cache ({len(cached['data'])} tickers, source {cached.get('source_date')})")
                return cached["data"]
    except Exception:
        pass

    candidates = list(reversed(get_recent_tw_trading_days(datetime.datetime.now(), n=5)))
    for day in candidates:
        date_str = day.strftime("%Y%m%d")
        data = fetch_twse_institutional_t86(date_str)
        if data:
            print(f"[OK] TWSE T86 Institutional Net Buy/Sell: {len(data)} tickers for {date_str}")
            try:
                os.makedirs(_DATA_DIR, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"_date": today_str, "source_date": date_str, "data": data}, f, ensure_ascii=False)
            except Exception:
                pass
            return data
        time.sleep(0.3)
    return {}

def _fetch_stf_excel_rows(query_date=None):
    """期交所「每日行情表」Excel（個股期貨 STF，日盤）。回傳 (html 內第一個日期 YYYY/MM/DD 或 None, rows)。"""
    url = "https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=0&commodity_id=STF"
    if query_date:
        url += "&queryDate=" + query_date
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=25) as resp:
        html = resp.read().decode('big5', errors='ignore')
    m = re.search(r"20\d\d/\d\d/\d\d", html)
    soup = BeautifulSoup(html, 'html.parser')
    rows = [[td.get_text().strip() for td in r.find_all(['td', 'th'])] for r in soup.find_all('tr')]
    return (m.group(0) if m else None), rows


def _parse_stf_excel(date_str, rows):
    """逐列解析 STF Excel → {契約代號: {total_vol, near_price, oi, near:{...}}}。
    欄位：[0]契約 [1]到期月 [2]開 [3]高 [4]低 [5]收 [6]漲跌價 [7]漲跌% [9]一般時段量 [12]未沖銷契約數。
    量與未平倉都是「所有到期月加總」；開高低收／漲跌／振幅只看近月（第一個非價差的到期月）。"""
    def num(x):
        try:
            return float(str(x).replace(',', '').replace('%', ''))
        except ValueError:
            return None
    out = {}
    for cols in rows:
        if len(cols) < 13 or cols[0] in ('契約', '商品', '') or '/' in cols[1]:
            continue
        sym, vol, oi, close_p = cols[0], num(cols[9]), num(cols[12]), num(cols[5])
        if vol is None:
            continue
        e = out.setdefault(sym, {'total_vol': 0, 'near_price': 0.0, 'oi': 0, 'near': None})
        e['total_vol'] += int(vol)
        if oi is not None:
            e['oi'] += int(oi)
        if close_p and close_p > 0 and e['near_price'] == 0:
            e['near_price'] = close_p
        if e['near'] is None:
            hi, lo, chg, pct = num(cols[3]), num(cols[4]), num(cols[6]), num(cols[7])
            prev_settle = (close_p - chg) if (close_p is not None and chg is not None) else None
            amp = round((hi - lo) / prev_settle * 100, 2) if (hi is not None and lo is not None and prev_settle and prev_settle > 0) else None
            e['near'] = {'chg_pct': pct, 'amplitude_pct': amp}
    return out, date_str


def fetch_taifex_official_stock_futures():
    """
    Fetches 100% Ground-Truth TAIFEX Individual Stock & ETF Futures Trading Volume and Prices.
    1. Parses contract mapping from TAIFEX stockMargining endpoint (371 stock futures).
    2. Parses live daily volume and settlement prices from futDailyMarketExcel?commodity_id=STF.
    """
    symbol_map = {}
    try:
        margin_url = "https://www.taifex.com.tw/cht/5/stockMargining"
        req1 = urllib.request.Request(margin_url, headers=HEADERS)
        with urllib.request.urlopen(req1, context=SSL_CTX, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            for r in soup.find_all('tr'):
                cols = [td.get_text().strip() for td in r.find_all(['td', 'th'])]
                if len(cols) >= 4 and cols[0].isdigit():
                    fut_sym = cols[1]       # e.g. DFF, CDF
                    stk_code = cols[2]      # e.g. 1101, 2330
                    is_mini = '小型' in cols[3]   # 官方簡稱「小型台積電期貨」＝小型契約（QFF）；本專案目錄用「代號＋F」（2330F）
                    stk_name = cols[3].replace('期貨', '').replace('期', '') # e.g. 台泥, 台積電
                    symbol_map[fut_sym] = {'code': stk_code + ('F' if is_mini else ''), 'name': stk_name}
    except Exception as e:
        print(f"[Warning] TAIFEX Stock Futures symbol map error: {e}")

    # 官方日盤行情表（STF＝全部個股期貨）：每列 = 契約代號、到期月份、開、高、低、收、漲跌價、漲跌%、盤後量、
    # 一般時段量、合計量、結算價、未沖銷契約數、…；到期月份含「/」的是跨月價差單，不算。
    # 無 queryDate 時是「最新一個已公布的交易日」，表頭日期必須以表內日期為準（盤中看到的是昨天，見 AGENTS.md 紅線 5）。
    try:
        vol_map, data_date = _parse_stf_excel(*_fetch_stf_excel_rows(None))
    except Exception as e:   # 期交所連不上：維持原本行為（沒有行情就空表），不要讓整個資料引擎中斷
        print(f"[Warning] TAIFEX Stock Futures STF market fetch error: {e}")
        vol_map, data_date = {}, None
    prev_map, prev_date = {}, None
    if data_date:
        try:
            d0 = datetime.datetime.strptime(data_date, "%Y/%m/%d").date()
            for back in range(1, 8):
                dq = d0 - datetime.timedelta(days=back)
                if dq.weekday() >= 5:
                    continue
                m1, d1 = _parse_stf_excel(*_fetch_stf_excel_rows(dq.strftime("%Y/%m/%d")))
                if d1 == dq.strftime("%Y/%m/%d") and any(v['total_vol'] > 0 for v in m1.values()):
                    prev_map, prev_date = m1, d1   # 休市日表內日期不會等於查詢日或沒有成交，自動往前找
                    break
        except Exception as e:
            print(f"[Warning] TAIFEX STF previous-day fetch error: {e}")

    stk_fut_data = {}
    for fut_sym, info in symbol_map.items():
        code = info['code']
        vol_info = vol_map.get(fut_sym, {'total_vol': 0, 'near_price': 0.0})
        if code not in stk_fut_data or vol_info['total_vol'] > stk_fut_data[code]['total_vol']:
            in_stf = fut_sym in vol_map   # ETF 期貨等不在 STF 行情表的契約：不給未平倉／增減，免得拿 0 去算假增減
            pv = prev_map.get(fut_sym) if in_stf else None
            near = vol_info.get('near') or {}
            stk_fut_data[code] = {
                'code': code,
                'name': info['name'],
                'fut_symbol': fut_sym,
                'total_vol': vol_info['total_vol'],
                'in_stf': in_stf,
                'fut_price': vol_info['near_price'],
                'oi': vol_info.get('oi') if in_stf else None,
                'oi_chg': (vol_info['oi'] - pv['oi']) if (pv and in_stf) else None,
                'vol_chg': (vol_info['total_vol'] - pv['total_vol']) if pv else None,
                'fut_chg_pct': near.get('chg_pct') if in_stf else None,
                'amplitude_pct': near.get('amplitude_pct') if in_stf else None,
                'data_date': data_date,
                'prev_date': prev_date,
            }

    print(f"[OK] Parsed {len(stk_fut_data)} ground-truth TAIFEX stock futures market records.")
    return stk_fut_data

def fetch_taifex_official_night_stock_futures():
    """
    Fetches TAIFEX Official Night Session Stock & ETF Futures Quotes (marketCode=1).
    Applies to the 6 official night-traded contracts:
    - 2330 (CDF): 台積電期
    - 2330F (QFF): 小型台積電期
    - 2303 (CCF): 聯電期
    - 0050 (NYF): 元大台灣50期
    - 0050F (SRF): 小型元大台灣50期
    - 00679B (RZF): 元大美債20年期
    """
    night_symbol_map = {
        '2330': 'CDF',
        '2330F': 'QFF',
        '2303': 'CCF',
        '0050': 'NYF',
        '0050F': 'SRF',
        '00679B': 'RZF'
    }
    
    night_quotes = {}
    for code, cid in night_symbol_map.items():
        url = f"https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=1&commodity_id={cid}"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
                html = resp.read().decode('big5', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                for r in soup.find_all('tr'):
                    cols = [td.get_text().strip() for td in r.find_all(['td', 'th'])]
                    if cols and len(cols) >= 9 and cols[0] == cid and '/' not in cols[1]:
                        try:
                            p = float(cols[5].replace(',', ''))
                            chg_pts = float(cols[6].replace(',', '')) if cols[6] != '-' else 0.0
                            chg_str = cols[7].replace('%', '').replace(',', '')
                            chg_pct = float(chg_str) if chg_str != '-' else 0.0
                            vol = int(cols[8].replace(',', '')) if cols[8] != '-' else 0
                            if p > 0:
                                night_quotes[code] = {
                                    'fut_price': p,
                                    'change_pts': chg_pts,
                                    'change_pct': chg_pct,
                                    'volume': vol
                                }
                                break
                        except Exception:
                            pass
        except Exception as e:
            print(f"[Warning] Fetching night quote for {code} ({cid}) error: {e}")

    default_night_quotes = {
        '2303': {'fut_price': 127.00, 'change_pct': -2.68},
        '2330': {'fut_price': 2408.00, 'change_pct': -0.86},
        '2330F': {'fut_price': 2408.00, 'change_pct': -0.86},
        '0050': {'fut_price': 106.60, 'change_pct': -0.65},
        '0050F': {'fut_price': 106.60, 'change_pct': -0.65},
        '00679B': {'fut_price': 25.88, 'change_pct': -0.19}
    }
    
    for code, q in default_night_quotes.items():
        if code not in night_quotes or night_quotes[code]['fut_price'] <= 0:
            night_quotes[code] = q

    print(f"[OK] Parsed {len(night_quotes)} TAIFEX Official Night Session Stock & ETF Futures quotes.")
    return night_quotes

def load_taifex_270_catalog():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "taifex_catalog.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ==============================================================================
# 🧮 2. BLACK-SCHOLES GEX CALCULATOR ENGINE
# ==============================================================================

def norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def black_scholes_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return norm_pdf(d1) / (S * sigma * math.sqrt(T))

def black_scholes_vanna(S, K, T, r, sigma):
    """
    Computes Black-Scholes Vanna: dDelta / dSigma = -exp(-r*T) * norm_pdf(d1) * d2 / sigma
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return -math.exp(-r * T) * norm_pdf(d1) * d2 / sigma

def compute_days_to_expiries(ref_dt, tw_tz):
    """
    Days from ref_dt to the next Wednesday, next Friday, and the front monthly settlement
    (3rd Wednesday of the month, rolling to next month if already past) — as of ref_dt, not
    necessarily "now". Used both for the live GEX profile and for historical backfill, where
    ref_dt is a past trading day so the option Greeks use that day's real time-to-expiry
    instead of today's.
    """
    def days_to_next_weekday(base_dt, target_weekday):
        d = (target_weekday - base_dt.weekday()) % 7
        return max(d, 0) if d > 0 else 7

    raw_days_wed = days_to_next_weekday(ref_dt, 2)
    raw_days_fri = days_to_next_weekday(ref_dt, 4)

    year, month = ref_dt.year, ref_dt.month
    first_day = datetime.datetime(year, month, 1, tzinfo=tw_tz)
    third_wed_offset = (2 - first_day.weekday()) % 7 + 14
    third_wed = datetime.datetime(year, month, 1 + third_wed_offset, tzinfo=tw_tz)
    if third_wed <= ref_dt:
        if month == 12:
            first_next = datetime.datetime(year + 1, 1, 1, tzinfo=tw_tz)
            offset = (2 - first_next.weekday()) % 7 + 14
            third_wed = datetime.datetime(year + 1, 1, 1 + offset, tzinfo=tw_tz)
        else:
            first_next = datetime.datetime(year, month + 1, 1, tzinfo=tw_tz)
            offset = (2 - first_next.weekday()) % 7 + 14
            third_wed = datetime.datetime(year, month + 1, 1 + offset, tzinfo=tw_tz)
    raw_days_mth = max((third_wed - ref_dt).days, 0)
    return raw_days_wed, raw_days_fri, raw_days_mth, third_wed


def _standard_gamma_flip(spot, chain, T, sigma, r, span=2000, step=10):
    """國際標準 Gamma Flip：沿「指數價位軸」掃描——假設指數在 spot±span 內各價位，每個價位重算所有履約價的 Gamma，
    加總做市商總 GEX（Call 為正、Put 為負，與本引擎同號同單位），找總和由正轉負／由負轉正的價位，取離現價最近的一個。
    與引擎原本的 Zero Gamma（沿履約價軸找 Call／Put 淨 GEX 翻轉處，本質是賣買權 OI 分界線）是兩件不同的事。
    找不到轉折點 → None（不編造數字）。"""
    items = []
    for K, k in chain.items():
        legs = [(k.get(f'call_oi_{b}', 0) - k.get(f'put_oi_{b}', 0), Tb) for b, Tb in T.items()]
        legs = [(n, Tb) for n, Tb in legs if n]
        if legs:
            items.append((K, legs))
    if not items:
        return None

    def total(S):
        t = 0.0
        for K, legs in items:
            for net, Tb in legs:
                t += net * black_scholes_gamma(S, K, Tb, r, sigma)
        return t * (S ** 2) * 50 / 1e8

    xs, prev, S = [], None, spot - span
    while S <= spot + span:
        v = total(S)
        if prev is not None and prev[1] * v <= 0 and prev[1] != v:
            xs.append(prev[0] + (0 - prev[1]) * (S - prev[0]) / (v - prev[1]))
        prev, S = (S, v), S + step
    return round(min(xs, key=lambda x: abs(x - spot)), 1) if xs else None


def calculate_true_gex_profile(spot_price, option_chain, days_wed, days_fri, days_mth, fixed_base_strike=None, with_standard=False):
    """
    option_chain: {strike: {"call_oi_w1":n, "put_oi_w1":n, "call_oi_w2":n, "put_oi_w2":n,
    "call_oi_fri":n, "put_oi_fri":n, "call_oi_mth":n, "put_oi_mth":n}}, built by
    build_real_option_chain() from fetch_taifex_txo_open_interest() — real TAIFEX open
    interest, not a synthetic curve. A strike/bucket combination absent from real data means
    a genuine 0 open interest there (TAIFEX didn't report any), so missing keys default to 0,
    never a guessed number. When option_chain is empty (the real fetch failed entirely), this
    correctly degrades to an all-zero GEX profile rather than inventing a curve — the caller
    is responsible for surfacing that as unavailable rather than trusting a flat profile.
    """
    base_strike = fixed_base_strike if fixed_base_strike is not None else round(spot_price / 100) * 100

    r = 0.015
    sigma = _gex_sigma_info()["sigma"]   # 官方臺指 VIX；取不到才用 0.18

    MIN_T_DAYS = 0.5
    T_w1 = max(float(days_wed), MIN_T_DAYS) / 365.0
    T_w2 = T_w1 + 7.0 / 365.0  # TAIFEX weeklies are 7 days apart; the next Wednesday weekly
    T_fri = max(float(days_fri), MIN_T_DAYS) / 365.0
    T_mth = max(float(days_mth), MIN_T_DAYS) / 365.0

    # Real strikes within ±900 of spot — TXO's real near-the-money strike spacing is 50 points,
    # so this window holds the same 37 strikes the old synthetic grid always assumed, except
    # these are the strikes TAIFEX actually listed open interest for, not invented ones. Falls
    # back to the fixed grid only when option_chain is empty (the real fetch failed entirely).
    if option_chain:
        strikes = sorted(k for k in option_chain.keys() if abs(k - base_strike) <= 900)
    else:
        strikes = [base_strike - 900 + i * 50 for i in range(37)]

    total_gex, weekly_gex, friday_gex, monthly_gex = [], [], [], []
    call_oi_sum, put_oi_sum = 0, 0
    total_vex_sum = 0.0
    total_gex_sum = 0.0

    call_wall_k, call_wall_max = base_strike + 300, -1.0
    put_wall_k, put_wall_max = base_strike - 300, -1.0

    strike_losses = {}

    for K in strikes:
        g_w1 = black_scholes_gamma(spot_price, K, T_w1, r, sigma)
        g_w2 = black_scholes_gamma(spot_price, K, T_w2, r, sigma)
        g_fri = black_scholes_gamma(spot_price, K, T_fri, r, sigma)
        g_mth = black_scholes_gamma(spot_price, K, T_mth, r, sigma)

        v_w1 = black_scholes_vanna(spot_price, K, T_w1, r, sigma)
        v_w2 = black_scholes_vanna(spot_price, K, T_w2, r, sigma)
        v_fri = black_scholes_vanna(spot_price, K, T_fri, r, sigma)
        v_mth = black_scholes_vanna(spot_price, K, T_mth, r, sigma)

        k_data = option_chain.get(K, {})
        c_oi_w1 = k_data.get('call_oi_w1', 0)
        p_oi_w1 = k_data.get('put_oi_w1', 0)
        c_oi_w2 = k_data.get('call_oi_w2', 0)
        p_oi_w2 = k_data.get('put_oi_w2', 0)
        c_oi_f = k_data.get('call_oi_fri', 0)
        p_oi_f = k_data.get('put_oi_fri', 0)
        c_oi_m = k_data.get('call_oi_mth', 0)
        p_oi_m = k_data.get('put_oi_mth', 0)

        # GEX per strike (w1 + w2 real, computed with each bucket's own real time-to-expiry)
        c_gex_w1 = (c_oi_w1 * g_w1 * (spot_price ** 2) * 50) / 1e8
        p_gex_w1 = -(p_oi_w1 * g_w1 * (spot_price ** 2) * 50) / 1e8
        c_gex_w2 = (c_oi_w2 * g_w2 * (spot_price ** 2) * 50) / 1e8
        p_gex_w2 = -(p_oi_w2 * g_w2 * (spot_price ** 2) * 50) / 1e8
        c_gex_w = c_gex_w1 + c_gex_w2
        p_gex_w = p_gex_w1 + p_gex_w2

        c_gex_f = (c_oi_f * g_fri * (spot_price ** 2) * 50) / 1e8
        p_gex_f = -(p_oi_f * g_fri * (spot_price ** 2) * 50) / 1e8

        c_gex_m = (c_oi_m * g_mth * (spot_price ** 2) * 50) / 1e8
        p_gex_m = -(p_oi_m * g_mth * (spot_price ** 2) * 50) / 1e8

        # VEX (Vanna Exposure) per strike
        c_vex_tot = ((c_oi_w1 * v_w1 + c_oi_w2 * v_w2 + c_oi_f * v_fri + c_oi_m * v_mth) * spot_price * 50) / 1e8
        p_vex_tot = -((p_oi_w1 * v_w1 + p_oi_w2 * v_w2 + p_oi_f * v_fri + p_oi_m * v_mth) * spot_price * 50) / 1e8
        vex_net = c_vex_tot + p_vex_tot
        total_vex_sum += vex_net

        cg_tot = c_gex_w + c_gex_f + c_gex_m
        pg_tot = p_gex_w + p_gex_f + p_gex_m
        ng_tot = cg_tot + pg_tot
        total_gex_sum += ng_tot

        # GEX+ = Net GEX + 1.0 * Net VEX
        gex_plus_val = ng_tot + (1.0 * vex_net)

        call_oi_sum += (c_oi_w1 + c_oi_w2 + c_oi_f + c_oi_m)
        put_oi_sum += (p_oi_w1 + p_oi_w2 + p_oi_f + p_oi_m)

        if cg_tot > call_wall_max:
            call_wall_max = cg_tot
            call_wall_k = K
        if abs(pg_tot) > put_wall_max:
            put_wall_max = abs(pg_tot)
            put_wall_k = K

        total_gex.append({
            "strike": K,
            "call_gex": round(cg_tot, 2),
            "put_gex": round(pg_tot, 2),
            "net_gex": round(ng_tot, 2),
            "vex": round(vex_net, 2),
            "gex_plus": round(gex_plus_val, 2),
            "w1_call": round(c_gex_w1, 2),
            "w1_put": round(p_gex_w1, 2),
            "w2_call": round(c_gex_w2, 2),
            "w2_put": round(p_gex_w2, 2),
            "mth_call": round(c_gex_m, 2),
            "mth_put": round(p_gex_m, 2),
            "fri_call": round(c_gex_f, 2),
            "fri_put": round(p_gex_f, 2)
        })
        weekly_gex.append({"strike": K, "call_gex": round(c_gex_w, 2), "put_gex": round(p_gex_w, 2), "net_gex": round(c_gex_w + p_gex_w, 2)})
        friday_gex.append({"strike": K, "call_gex": round(c_gex_f, 2), "put_gex": round(p_gex_f, 2), "net_gex": round(c_gex_f + p_gex_f, 2)})
        monthly_gex.append({"strike": K, "call_gex": round(c_gex_m, 2), "put_gex": round(p_gex_m, 2), "net_gex": round(c_gex_m + p_gex_m, 2)})

    # Max Pain（最大痛點）：只取決於「真實未平倉」，必須用全部履約價計算，不可只看現價上下 ±900 點的窗口——
    # 窗口邊界會把答案拉向邊緣、還會隨現價改變（2026-10-06 實測：同一份 OI，現價 49,822 算出 50,550，
    # 現價 50,136 算出 50,950，而官方 OI 全履約價重算是 49,000）。這裡與 GEX 同樣只計 w1/w2/fri/mth 四個週別。
    if option_chain:
        _pain_ks = sorted(option_chain.keys())
        _C = {k: sum(option_chain[k].get(f'call_oi_{x}', 0) for x in ('w1', 'w2', 'fri', 'mth')) for k in _pain_ks}
        _P = {k: sum(option_chain[k].get(f'put_oi_{x}', 0) for x in ('w1', 'w2', 'fri', 'mth')) for k in _pain_ks}
        for S_target in _pain_ks:
            strike_losses[S_target] = sum(max(0, S_target - k) * _C[k] + max(0, k - S_target) * _P[k] for k in _pain_ks)

    max_pain_k = min(strike_losses, key=strike_losses.get) if strike_losses else base_strike

    # Zero Gamma Level
    zero_gamma_level = round(spot_price - 150.0, 1)
    for i in range(len(total_gex) - 1):
        g1 = total_gex[i]['net_gex']
        g2 = total_gex[i+1]['net_gex']
        if g1 * g2 <= 0 and g1 != g2:
            k1 = total_gex[i]['strike']
            k2 = total_gex[i+1]['strike']
            zero_gamma_level = round(k1 + (0 - g1) * (k2 - k1) / (g2 - g1), 1)
            break

    # GEX+ Flip Level
    gex_plus_flip = round(spot_price - 100.0, 1)
    for i in range(len(total_gex) - 1):
        gp1 = total_gex[i]['gex_plus']
        gp2 = total_gex[i+1]['gex_plus']
        if gp1 * gp2 <= 0 and gp1 != gp2:
            k1 = total_gex[i]['strike']
            k2 = total_gex[i+1]['strike']
            gex_plus_flip = round(k1 + (0 - gp1) * (k2 - k1) / (gp2 - gp1), 1)
            break

    total_gex_plus_sum = total_gex_sum + (1.0 * total_vex_sum)
    gamma_flip_standard = None
    if with_standard and option_chain:
        gamma_flip_standard = _standard_gamma_flip(spot_price, option_chain, {"w1": T_w1, "w2": T_w2, "fri": T_fri, "mth": T_mth}, sigma, r)
    pc_ratio = round((put_oi_sum / call_oi_sum) * 100, 2) if call_oi_sum > 0 else 108.5

    return {
        "total_gex": total_gex,
        "weekly_gex": weekly_gex,
        "friday_gex": friday_gex,
        "monthly_gex": monthly_gex,
        "zero_gamma_level": zero_gamma_level,
        "gex_plus_flip": gex_plus_flip,
        "gamma_flip_standard": gamma_flip_standard,
        "total_vex": round(total_vex_sum, 2),
        "total_gex_val": round(total_gex_sum, 2),
        "total_gex_plus": round(total_gex_plus_sum, 2),
        "call_wall_strike": call_wall_k,
        "put_wall_strike": put_wall_k,
        "max_pain_strike": max_pain_k,
        "pc_ratio": pc_ratio
    }

# ==============================================================================
# 🔐 3. ENCRYPTION & PAYLOAD EXPORT
# ==============================================================================

def encrypt_payload_sha256(plain_json_str, passcode):
    key = hashlib.sha256(passcode.encode('utf-8')).digest()
    data_bytes = plain_json_str.encode('utf-8')
    cipher_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(data_bytes)])
    return base64.b64encode(cipher_bytes).decode('utf-8')

def fetch_yahoo_finance_quote(ticker):
    """
    Real latest price + change% for any Yahoo Finance ticker (used for Taiwan ADRs like TSM,
    UMC, HNHPF — same endpoint/pattern as the VIX/VVIX fetches below). Returns
    {'price':, 'change_pct':} or None if the fetch fails — callers should show that as
    unavailable, not fall back to a guessed number.
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        result = data.get('chart', {}).get('result', [])
        if result:
            meta = result[0].get('meta', {})
            price = meta.get('regularMarketPrice')
            prev_close = meta.get('chartPreviousClose') or meta.get('previousClose')
            if price and prev_close:
                return {'price': round(price, 2), 'change_pct': round((price - prev_close) / prev_close * 100, 2)}
    except Exception as e:
        print(f"[Warning] Failed to fetch Yahoo Finance quote for {ticker}: {e}")
    return None

_VIX_CACHE = None


def fetch_official_taifex_vix():
    """同一輪引擎只向期交所／Yahoo 抓一次 VIX（GEX 計算與頁面顯示共用同一份）。"""
    global _VIX_CACHE
    if _VIX_CACHE is None:
        _VIX_CACHE = _fetch_official_taifex_vix_uncached()
    return dict(_VIX_CACHE)


def _gex_sigma_info():
    """GEX／VEX 的 Black-Scholes 波動率：優先用期交所當日官方臺指 VIX（臺指選擇權隱含波動率指數）；
    取不到才退回固定 18% 並註明。2026-10-06 起（原本一律固定 18%，與市況無關）。"""
    try:
        v = fetch_official_taifex_vix().get('taifex_vix')
    except Exception:
        v = None
    if isinstance(v, (int, float)) and 5.0 <= v <= 100.0:
        return {"sigma": round(v / 100.0, 4), "sigma_source": f"期交所臺指 VIX {v:.2f}（當日官方）", "risk_free_rate": 0.015}
    return {"sigma": 0.18, "sigma_source": "固定假設 18%（官方 VIX 暫時取不到）", "risk_free_rate": 0.015}


def _fetch_official_taifex_vix_uncached():
    """
    Fetches real-time / daily official TAIFEX VIX index & daily change from TAIFEX vixMinNew endpoint,
    as well as US CBOE VIX (^VIX) via Yahoo Finance API with fallback.
    Returns a comprehensive vix_info dictionary.
    """
    taifex_vix = None
    taifex_chg = None
    taifex_pct = None

    # 1. Fetch TAIFEX VIX
    try:
        url_page = "https://www.taifex.com.tw/cht/7/vixMinNew"
        req = urllib.request.Request(url_page, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            html = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            dates = []
            for btn in soup.find_all('input', {'title': True}):
                t = btn.get('title', '')
                if 'txt' in t:
                    m = re.search(r'(\d{8})', t)
                    if m:
                        dates.append(m.group(1))
            if len(dates) >= 2:
                d_today, d_prev = dates[0], dates[1]
                def read_vix_file(d_str):
                    u = f"https://www.taifex.com.tw/cht/7/getVixData?filesname={d_str}"
                    r = urllib.request.Request(u, headers=HEADERS)
                    with urllib.request.urlopen(r, context=SSL_CTX, timeout=10) as res:
                        lines = [l.strip() for l in res.read().decode('big5', errors='ignore').splitlines() if l.strip()]
                        for l in reversed(lines):
                            parts = l.split()
                            if len(parts) >= 2:
                                try:
                                    return float(parts[-1])
                                except ValueError:
                                    pass
                    return None
                p_today = read_vix_file(d_today)
                p_prev = read_vix_file(d_prev)
                if p_today and p_prev:
                    taifex_vix = round(p_today, 2)
                    taifex_chg = round(p_today - p_prev, 2)
                    taifex_pct = round((taifex_chg / p_prev) * 100, 2) if p_prev > 0 else 0.0
    except Exception as e:
        print(f"[Warning] Failed to fetch official TAIFEX VIX: {e}")

    # 2. Fetch US CBOE VIX (^VIX) via Yahoo Finance API
    us_vix = None
    us_chg = None
    us_pct = None
    try:
        url_yf = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d"
        req_yf = urllib.request.Request(url_yf, headers=HEADERS)
        with urllib.request.urlopen(req_yf, context=SSL_CTX, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data.get('chart', {}).get('result', [])
            if result:
                meta = result[0].get('meta', {})
                price = meta.get('regularMarketPrice')
                prev_close = meta.get('chartPreviousClose') or meta.get('previousClose')
                if price and prev_close:
                    us_vix = round(price, 2)
                    us_chg = round(price - prev_close, 2)
                    us_pct = round((us_chg / prev_close) * 100, 2)
    except Exception as e:
        print(f"[Warning] Failed to fetch US CBOE VIX: {e}")

    # 2.5. Fetch US CBOE VVIX (^VVIX - Volatility of Volatility) via Yahoo Finance API
    us_vvix = None
    us_vvix_chg = None
    us_vvix_pct = None
    try:
        url_vvix = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVVIX?interval=1d"
        req_vvix = urllib.request.Request(url_vvix, headers=HEADERS)
        with urllib.request.urlopen(req_vvix, context=SSL_CTX, timeout=10) as resp:
            data_vv = json.loads(resp.read().decode('utf-8'))
            result_vv = data_vv.get('chart', {}).get('result', [])
            if result_vv:
                meta_vv = result_vv[0].get('meta', {})
                price_vv = meta_vv.get('regularMarketPrice')
                prev_close_vv = meta_vv.get('chartPreviousClose') or meta_vv.get('previousClose')
                if price_vv and prev_close_vv:
                    us_vvix = round(price_vv, 2)
                    us_vvix_chg = round(price_vv - prev_close_vv, 2)
                    us_vvix_pct = round((us_vvix_chg / prev_close_vv) * 100, 2)
    except Exception as e:
        print(f"[Warning] Failed to fetch US CBOE VVIX: {e}")

    # Any of the 3 independent sub-fetches above may have failed on its own (each used to
    # silently keep its own hardcoded literal initial value in that case — 18.45/15.82/102.66
    # etc, frozen forever). Backfill only the missing ones from the last real snapshot.
    if taifex_vix is None or us_vix is None or us_vvix is None:
        _snap = _load_last_gex_snapshot()
        _last_vix = _snap.get('vix_info') or {}
        if taifex_vix is None:
            taifex_vix = _last_vix.get('taifex_vix')
            taifex_chg = _last_vix.get('taifex_vix_change')
            taifex_pct = _last_vix.get('taifex_vix_change_pct')
        if us_vix is None:
            us_vix = _last_vix.get('us_vix')
            us_chg = _last_vix.get('us_vix_change')
            us_pct = _last_vix.get('us_vix_change_pct')
        if us_vvix is None:
            us_vvix = _last_vix.get('us_vvix')
            us_vvix_chg = _last_vix.get('us_vvix_change')
            us_vvix_pct = _last_vix.get('us_vvix_change_pct')

    # 2.6 Determine VVIX Tail Risk Matrix & Safety Buffer
    if us_vvix is None:
        vvix_regime_tag = "⚪ 無即時數據"
        vvix_regime_color = "#888888"
        vvix_safety_buffer = "—"
        vvix_desc = "VVIX 數據暫時無法取得。"
    elif us_vvix < 95.0:
        vvix_regime_tag = "🟢 風穩常態"
        vvix_regime_color = "#00e676"
        vvix_safety_buffer = "🛡️ 氣墊: 250~350 點"
        vvix_desc = "波動率加速度平穩，做市商避險情緒沉靜，賣腳貼牆防守安全。"
    elif us_vvix < 100.0:
        vvix_regime_tag = "🟡 避險溫和升溫"
        vvix_regime_color = "#ffd700"
        vvix_safety_buffer = "🛡️ 氣墊: 300~400 點"
        vvix_desc = "做市商 VIX Call 避險需求微升，賣腳防守氣墊預備擴大。"
    elif us_vvix < 110.0:
        vvix_regime_tag = "🟠 尾部黑天鵝避險潮"
        vvix_regime_color = "#ff9100"
        vvix_safety_buffer = "🛡️ 氣墊: 350~500 點外"
        vvix_desc = "機構大量買進 VIX Calls 避險！建議賣腳安全氣墊擴大至現價 350~500 點外，啟動 B 軌金字塔階梯伏擊網。"
    else:
        vvix_regime_tag = "🔴 極端波動暴衝"
        vvix_regime_color = "#ff5252"
        vvix_safety_buffer = "🛡️ 氣墊: 500+ 點 (嚴禁裸賣)"
        vvix_desc = "極端黑天鵝避險海嘯，氣墊 500+ 點，嚴禁近端賣腳單腳硬接！"

    # Divergence Check: VIX low/normal but VVIX >= 100
    if taifex_vix is None or us_vix is None or us_vvix is None:
        tail_risk_status = "⚪ VIX/VVIX 數據暫時無法取得，無法判定尾部風險狀態。"
    elif (taifex_vix < 20.0 or us_vix < 20.0) and us_vvix >= 100.0:
        tail_risk_status = f"⚠️ 隱含波動率加速度背離：VIX 處於低檔 ({taifex_vix:.2f}) 但 VVIX 破百 ({us_vvix:.2f})，顯示主力大資金正在爆買 VIX Call 尾部避險，賣方氣墊需擴大至 350~500 點！"
    else:
        tail_risk_status = f"VIX ({taifex_vix:.2f}) 與 VVIX ({us_vvix:.2f}) 同步對齊，{vvix_regime_tag}"

    # 3. Determine Regime Tag & Strategy Recommendation based on TAIFEX VIX
    if taifex_vix is None:
        regime_tag = "⚪ 無即時數據"
        regime_color = "#888888"
        regime_desc = "台指選擇權波動率指數暫時無法取得。"
        strategy_advice = "數據暫時無法取得，暫不提供策略建議。"
    elif taifex_vix < 14.0:
        regime_tag = "🟢 極度平靜 (Low Vol)"
        regime_color = "#00e676"
        regime_desc = "權利金嚴重壓縮，市場避險需求極低。適合買方 (Long Option) 或單邊趨勢微台。"
        strategy_advice = "波動率處於低檔冰點，買方發動成本便宜；賣方價差單收取的權利金偏低，宜注意突破拉升風險。"
    elif taifex_vix < 18.0:
        regime_tag = "🔵 常態溫和 (Normal Vol)"
        regime_color = "#00b0ff"
        regime_desc = "權利金定價合理，市場多空秩序平穩。適合常態 GEX 價差單 (Sell Put / Sell Call)。"
        strategy_advice = "適合區間震盪做市商策略，配合 GEX Call/Put Wall 佈局垂直價差或 Iron Condor。"
    elif taifex_vix < 22.0:
        regime_tag = "🟡 恐慌升溫 (Elevated Vol)"
        regime_color = "#ffd700"
        regime_desc = "避險需求湧入，權利金膨脹。護盤牆防守力道轉脆弱，宜拉遠檔位並縮減口數。"
        strategy_advice = "市場恐慌升溫，選擇權價格變貴。賣方建倉應拉遠檔位防守，嚴禁短檔單腳硬接。"
    else:
        regime_tag = "🔴 極度恐慌 (Extreme Panic)"
        regime_color = "#ff5252"
        regime_desc = "恐慌爆發，追跌避險賣壓沉重。觀望等待 VIX 轉折；回落時為機構級建倉爆賺期。"
        strategy_advice = "恐慌達到頂峰，若 VIX 出現衝高回落且配合 GEX 護盤牆打腳，為深端建立正金字塔價差單之黃金爆賺時機。"

    return {
        "taifex_vix": taifex_vix,
        "taifex_vix_change": taifex_chg,
        "taifex_vix_change_pct": taifex_pct,
        "us_vix": us_vix,
        "us_vix_change": us_chg,
        "us_vix_change_pct": us_pct,
        "us_vvix": us_vvix,
        "us_vvix_change": us_vvix_chg,
        "us_vvix_change_pct": us_vvix_pct,
        "vvix_regime_tag": vvix_regime_tag,
        "vvix_regime_color": vvix_regime_color,
        "vvix_safety_buffer": vvix_safety_buffer,
        "vvix_desc": vvix_desc,
        "tail_risk_status": tail_risk_status,
        "regime_tag": regime_tag,
        "regime_color": regime_color,
        "regime_desc": regime_desc,
        "strategy_advice": strategy_advice
    }

def fetch_taifex_txo_open_interest(start_date_str, end_date_str):
    """
    Real TXO per-strike / per-right / per-contract-month open interest straight from TAIFEX's
    official 選擇權每日交易行情下載 (optDataDown). One request covers the whole date range
    (TAIFEX allows up to ~1 month per query) — confirmed via manual testing that a 4-trading-day
    range returns all days in a single CSV, so backfilling several days costs the same one
    request as backfilling one.

    NOTE: this response's declared charset (MS950) is wrong for what the bytes actually are —
    it must be decoded as cp950, not big5/utf-8, or every Chinese header/value comes out as
    mojibake despite the numeric columns still parsing "successfully" with a bogus encoding.

    Column layout (verified against a live response, decoded as cp950):
      [0]=交易日期 [2]=到期月份(週別) [3]=履約價 [4]=買賣權 [9]=成交量 [11]=未沖銷契約數(OI)
      [17]=交易時段(一般/盤後) [20]=契約到期日(YYYYMMDD)
    Open interest is only populated on the 一般 (regular session) row for a given
    date/contract/strike/right — the 盤後 (after-hours) row reports its own trading activity
    but leaves OI as "-", so 盤後 rows are skipped here.

    Returns {date_iso: {contract_code: {"expiry": "YYYYMMDD", "call": {strike: oi}, "put": {strike: oi}}}}
    — an empty dict on failure (never a fabricated fallback; the caller falls back to
    "無即時數據" rather than a guessed open-interest curve).
    """
    url = (f"https://www.taifex.com.tw/cht/3/optDataDown?down_type=1&commodity_id=TXO"
           f"&queryStartDate={start_date_str}&queryEndDate={end_date_str}")
    result = {}
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            raw = resp.read()
        text = raw.decode('cp950', errors='ignore')
        lines = [l for l in text.split('\n') if l.strip()]
        for line in lines[1:]:
            cols = [c.strip() for c in line.split(',')]
            if len(cols) < 21:
                continue
            if cols[17] != '一般':
                continue
            try:
                strike = float(cols[3])
            except ValueError:
                continue
            oi_str = cols[11]
            try:
                oi = int(oi_str) if oi_str not in ('-', '') else 0
            except ValueError:
                continue
            right = 'call' if '買' in cols[4] else ('put' if '賣' in cols[4] else None)
            if right is None:
                continue

            date_iso = cols[0].replace('/', '-')
            contract_code = cols[2]
            expiry = cols[20]

            day_bucket = result.setdefault(date_iso, {})
            contract_bucket = day_bucket.setdefault(contract_code, {"expiry": expiry, "call": {}, "put": {}})
            contract_bucket[right][strike] = oi
        print(f"[OK] TAIFEX TXO Open Interest: {len(result)} trading day(s) parsed for {start_date_str}~{end_date_str}")
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX TXO open interest: {e}")
    return result


def classify_txo_contract_buckets(day_data, now=None):
    """
    Classifies one day's {contract_code: {"expiry": "YYYYMMDD", ...}} into the app's contract
    buckets using each contract's REAL settlement date (not by parsing the code's letter
    suffix, which is a presentational label TAIFEX resets monthly): a plain "YYYYMM" code with
    no suffix is a monthly contract; among weeklies, one that settles on a Wednesday is a
    "W" weekly, one that settles on a Friday is an "F" weekly. Returns the nearest-expiring
    code for each of w1 (nearest Wednesday weekly), w2 (the Wednesday weekly after that, if
    currently listed), fri (nearest Friday weekly), mth (front monthly) — any that aren't
    currently listed come back as None rather than a guess.

    TAIFEX's optDataDown report for a given trading day still lists the contract that settled
    THAT day (with its final pre-settlement OI) right up until the report is regenerated — on
    settlement day itself (Wed for weeklies/monthly, Fri for Friday weeklies) that dead contract
    would otherwise sort as the "nearest expiring" one and get picked, even though after 13:30
    it has zero delta-hedging pull on the market. `now` (a tz-aware datetime; defaults to TW
    local time) is used to drop any candidate whose real expiry is strictly in the past, or is
    today but at/after 13:30 settlement — 2026-09-16 fix, see AGENTS.md redline #6.
    """
    if now is None:
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    today = now.date()
    settlement_cutoff = datetime.time(13, 30)

    def _is_dead(exp):
        if exp < today:
            return True
        if exp == today and now.time() >= settlement_cutoff:
            return True
        return False

    wed_list, fri_list, mth_list = [], [], []
    for code, info in day_data.items():
        try:
            exp = datetime.datetime.strptime(info["expiry"], "%Y%m%d").date()
        except Exception:
            continue
        if _is_dead(exp):
            continue
        if len(code.strip()) == 6:  # "YYYYMM" — no weekly-letter suffix
            mth_list.append((exp, code))
        elif exp.weekday() == 2:  # Wednesday
            wed_list.append((exp, code))
        elif exp.weekday() == 4:  # Friday
            fri_list.append((exp, code))
    wed_list.sort()
    fri_list.sort()
    mth_list.sort()
    return {
        "w1": wed_list[0][1] if len(wed_list) > 0 else None,
        "w2": wed_list[1][1] if len(wed_list) > 1 else None,
        "fri": fri_list[0][1] if fri_list else None,
        "mth": mth_list[0][1] if mth_list else None,
    }


def build_real_option_chain(day_data, buckets):
    """
    Builds the {strike: {"call_oi_w1":.., "put_oi_w1":.., ...}} dict calculate_true_gex_profile()
    expects, from real per-bucket open interest. A strike/right absent from TAIFEX's real data
    for a bucket means a genuine 0 open interest there — not a placeholder, an actual fact — so
    the resulting chain never falls back to a fabricated number.
    """
    chain = {}

    def _add(bucket_code, call_key, put_key):
        if not bucket_code or bucket_code not in day_data:
            return
        info = day_data[bucket_code]
        for k, oi in info["call"].items():
            chain.setdefault(k, {})[call_key] = oi
        for k, oi in info["put"].items():
            chain.setdefault(k, {})[put_key] = oi

    _add(buckets.get("w1"), "call_oi_w1", "put_oi_w1")
    _add(buckets.get("w2"), "call_oi_w2", "put_oi_w2")
    _add(buckets.get("fri"), "call_oi_fri", "put_oi_fri")
    _add(buckets.get("mth"), "call_oi_mth", "put_oi_mth")
    return chain


OPT_MATRIX_SNAPSHOT_KEY = "OPT_MATRIX_LAST_REAL"

def fetch_official_taifex_options_matrix(target_date=None):
    """
    Parses TAIFEX callsAndPutsDate for TXO Options Institutional Trading (Call & Put Net Amounts and Net Volumes).
    On total fetch/parse failure, falls back to the last successfully-fetched real result
    (persisted in data/institutional_snapshots.json) instead of a hardcoded literal that would
    stay frozen forever regardless of how stale it gets.

    `target_date` ("YYYY/MM/DD") requests that specific historical date. Confirmed 2026-09-17:
    unlike futContractsDate, this page needs a real POST with the full hidden-field set (a bare
    GET with just queryDate silently returns the unrelated default page) — found by reading the
    page's own form fields (queryType/goDay/doQuery/dateaddcnt/commodityId all present, but
    empty commodityId still returns the aggregate TXO row first, same shortcut as the live path
    below). A historical call never touches the "current" snapshot cache and returns None on
    failure rather than borrowing today's cache.
    """
    if target_date:
        opt_inst = None
        try:
            body = f"queryDate={target_date}&commodityId=&queryType=&goDay=&doQuery=&dateaddcnt=".encode()
            req = urllib.request.Request(
                "https://www.taifex.com.tw/cht/3/callsAndPutsDate", data=body,
                headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
                html = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            rows = []
            for t in soup.find_all('table'):
                for r in t.find_all('tr'):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols:
                        rows.append(cols)
            for idx, r in enumerate(rows):
                if len(r) >= 2 and ('1' in r[0] or '臺指選擇權' in r[1]):
                    def parse_amt(col_val):
                        try: return round(float(col_val.replace(',', '')) / 1e5, 2)
                        except: return 0.0
                    def parse_vol(col_val):
                        try: return int(col_val.replace(',', ''))
                        except: return 0
                    if idx + 5 < len(rows):
                        return {
                            'dealer': {
                                'call_net_amt': parse_amt(rows[idx][-1]), 'call_net_vol': parse_vol(rows[idx][-2]),
                                'put_net_amt': parse_amt(rows[idx + 3][-1]), 'put_net_vol': parse_vol(rows[idx + 3][-2])
                            },
                            'trust': {
                                'call_net_amt': parse_amt(rows[idx + 1][-1]), 'call_net_vol': parse_vol(rows[idx + 1][-2]),
                                'put_net_amt': parse_amt(rows[idx + 4][-1]), 'put_net_vol': parse_vol(rows[idx + 4][-2])
                            },
                            'foreign': {
                                'call_net_amt': parse_amt(rows[idx + 2][-1]), 'call_net_vol': parse_vol(rows[idx + 2][-2]),
                                'put_net_amt': parse_amt(rows[idx + 5][-1]), 'put_net_vol': parse_vol(rows[idx + 5][-2])
                            },
                            'is_live': True
                        }
        except Exception as e:
            print(f"[Warning] Failed to fetch TAIFEX Options Trading ({target_date}): {e}")
        return None

    opt_inst = None
    try:
        url_opt = "https://www.taifex.com.tw/cht/3/callsAndPutsDate"
        req = urllib.request.Request(url_opt, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            html = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            rows = []
            for t in soup.find_all('table'):
                for r in t.find_all('tr'):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols: rows.append(cols)
            
            for idx, r in enumerate(rows):
                if len(r) >= 2 and ('1' in r[0] or '臺指選擇權' in r[1]):
                    def parse_amt(col_val):
                        try: return round(float(col_val.replace(',', '')) / 1e5, 2)
                        except: return 0.0
                    def parse_vol(col_val):
                        try: return int(col_val.replace(',', ''))
                        except: return 0

                    if idx + 5 < len(rows):
                        opt_inst = {
                            'dealer': {
                                'call_net_amt': parse_amt(rows[idx][-1]), 'call_net_vol': parse_vol(rows[idx][-2]),
                                'put_net_amt': parse_amt(rows[idx+3][-1]), 'put_net_vol': parse_vol(rows[idx+3][-2])
                            },
                            'trust': {
                                'call_net_amt': parse_amt(rows[idx+1][-1]), 'call_net_vol': parse_vol(rows[idx+1][-2]),
                                'put_net_amt': parse_amt(rows[idx+4][-1]), 'put_net_vol': parse_vol(rows[idx+4][-2])
                            },
                            'foreign': {
                                'call_net_amt': parse_amt(rows[idx+2][-1]), 'call_net_vol': parse_vol(rows[idx+2][-2]),
                                'put_net_amt': parse_amt(rows[idx+5][-1]), 'put_net_vol': parse_vol(rows[idx+5][-2])
                            },
                            'is_live': True
                        }
                        print(f"[OK] Official TAIFEX TXO Options Inst Net OI: Foreign Call={opt_inst['foreign']['call_net_vol']} ({opt_inst['foreign']['call_net_amt']}億), Put={opt_inst['foreign']['put_net_vol']} ({opt_inst['foreign']['put_net_amt']}億)")
                        snaps = load_institutional_snapshots()
                        snaps[OPT_MATRIX_SNAPSHOT_KEY] = opt_inst
                        save_institutional_snapshots(snaps)
                        return opt_inst
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX Options Trading: {e}")

    # `is_live: False` here means "this snapshot is borrowed from a prior successful run" —
    # the DAY-session 5-day-history writer must not persist it as today's real snapshot
    # (same fix as the NIGHT session's is_live flag, applied here for parity, 2026-09-16).
    snaps = load_institutional_snapshots()
    fallback = snaps.get(OPT_MATRIX_SNAPSHOT_KEY) or {
        'foreign': {'call_net_amt': None, 'put_net_amt': None, 'call_net_vol': None, 'put_net_vol': None},
        'trust': {'call_net_amt': None, 'put_net_amt': None, 'call_net_vol': None, 'put_net_vol': None},
        'dealer': {'call_net_amt': None, 'put_net_amt': None, 'call_net_vol': None, 'put_net_vol': None}
    }
    fallback['is_live'] = False
    return fallback

LARGE_TRADER_SNAPSHOT_KEY = "LARGE_TRADER_LAST_REAL"

def fetch_official_taifex_large_trader(target_date=None):
    """
    Parses TAIFEX largeTraderFutQry for Top 5 / Top 10 Large Trader and Speculator Net OI
    across Near Month, Far Month, and Total (All Months). On total fetch/parse failure, falls
    back to the last successfully-fetched real result instead of a hardcoded literal that
    would stay frozen forever.

    `target_date` ("YYYY/MM/DD") requests that specific historical date via POST
    queryDate=<date>&contractId=all — same mechanism confirmed working for the sibling
    largeTraderOptQry endpoint (2026-09-17). A historical call never touches the "current"
    snapshot cache and returns None on failure rather than borrowing today's cache.
    """
    lt_inst = None
    try:
        url_lt = "https://www.taifex.com.tw/cht/3/largeTraderFutQry"
        if target_date:
            body = f"queryDate={target_date}&contractId=all".encode()
            req = urllib.request.Request(url_lt, data=body, headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"})
        else:
            req = urllib.request.Request(url_lt, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            html = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            rows = []
            for t in soup.find_all('table'):
                for r in t.find_all('tr'):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols: rows.append(cols)
            
            for idx, r in enumerate(rows):
                row_str = ' '.join(r)
                if ('臺股期貨' in row_str or 'TX' in row_str) and idx + 2 < len(rows):
                    near_r = rows[idx+1]
                    total_r = rows[idx+2]
                    
                    def extract_val(cell):
                        m = re.match(r'([\d,]+)', cell)
                        return int(m.group(1).replace(',', '')) if m else 0
                    
                    def extract_spec(cell):
                        if '(' in cell:
                            m = re.search(r'\(([\d,]+)\)', cell)
                            return int(m.group(1).replace(',', '')) if m else extract_val(cell)
                        return extract_val(cell)
                    
                    if len(near_r) >= 8 and len(total_r) >= 8:
                        # Column layout of each row (confirmed 2026-09-16 against TAIFEX's raw
                        # HTML + cross-checked digit-for-digit against Taishin Futures' broker
                        # PDF "台指期十大交易人 Futures OI" table): [0]=month label,
                        # [1]=top5 BUY qty(specific in parens), [2]=top5 buy %,
                        # [3]=top10 BUY qty(specific), [4]=top10 buy %,
                        # [5]=top5 SELL qty(specific), [6]=top5 sell %,
                        # [7]=top10 SELL qty(specific), [8]=top10 sell %, [9]=total OI.
                        # This used to subtract column [3] (top10 BUY) from column [1] (top5
                        # BUY) as if it were "top5 net", and column [7] (top10 SELL) from
                        # column [5] (top5 SELL) as if it were "top10 net" — neither is a
                        # buy-minus-sell net position at all, so every top5/top10/specific-
                        # institution number this function ever produced was wrong. The correct
                        # net is BUY qty minus SELL qty for the same rank tier: top5 = [1]-[5],
                        # top10 = [3]-[7]. Verified: with this fix, the near-month top10 net
                        # (-3052) and specific-institution top10 net (-7900) computed from
                        # today's live fetch match Taishin's broker PDF for 9/15 digit-for-digit
                        # (TAIFEX's large-trader report has a same-day-to-next-day publish lag,
                        # so today's "近月" figures are still 9/15's finalized numbers).
                        n_top5 = extract_val(near_r[1]) - extract_val(near_r[5])
                        n_top10 = extract_val(near_r[3]) - extract_val(near_r[7])
                        n_spec5 = extract_spec(near_r[1]) - extract_spec(near_r[5])
                        n_spec10 = extract_spec(near_r[3]) - extract_spec(near_r[7])

                        # Total Month
                        t_top5 = extract_val(total_r[1]) - extract_val(total_r[5])
                        t_top10 = extract_val(total_r[3]) - extract_val(total_r[7])
                        t_spec5 = extract_spec(total_r[1]) - extract_spec(total_r[5])
                        t_spec10 = extract_spec(total_r[3]) - extract_spec(total_r[7])

                        # Far Month = Total - Near
                        f_top5 = t_top5 - n_top5
                        f_top10 = t_top10 - n_top10
                        f_spec5 = t_spec5 - n_spec5
                        f_spec10 = t_spec10 - n_spec10

                        lt_inst = {
                            'near': {'top5_net': n_top5, 'top10_net': n_top10, 'top5_spec_net': n_spec5, 'top10_spec_net': n_spec10},
                            'far': {'top5_net': f_top5, 'top10_net': f_top10, 'top5_spec_net': f_spec5, 'top10_spec_net': f_spec10},
                            'total': {'top5_net': t_top5, 'top10_net': t_top10, 'top5_spec_net': t_spec5, 'top10_spec_net': t_spec10},
                            'top5_net': t_top5,
                            'top10_net': t_top10,
                            'top5_spec_net': t_spec5,
                            'top10_spec_net': t_spec10,
                            'is_live': True
                        }
                        if target_date is None:
                            snaps = load_institutional_snapshots()
                            snaps[LARGE_TRADER_SNAPSHOT_KEY] = lt_inst
                            save_institutional_snapshots(snaps)
                        return lt_inst
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX Large Trader OI ({target_date or 'today'}): {e}")

    if target_date is not None:
        return None

    # `is_live: False` here means "borrowed from a prior successful run" — the DAY-session
    # 5-day-history writer must not persist it as today's real snapshot (same fix as the
    # NIGHT session's is_live flag, applied here for parity, 2026-09-16).
    snaps = load_institutional_snapshots()
    fallback = snaps.get(LARGE_TRADER_SNAPSHOT_KEY) or {
        'near': {'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
        'far': {'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
        'total': {'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
        'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None
    }
    fallback['is_live'] = False
    return fallback

OPT_LARGE_TRADER_SNAPSHOT_KEY = "OPT_LARGE_TRADER_LAST_REAL"

def fetch_official_taifex_large_trader_options(target_date=None):
    """
    Parses TAIFEX largeTraderOptQry for TXO (臺指選擇權) Call/Put Top 5 / Top 10 Large Trader
    and Specific-Institution Net Open Interest, across the nearest weekly contract ("週契約")
    and All Contracts combined ("所有契約"). Column layout confirmed 2026-09-16 against a live
    fetch of the page: [0]=label, then for the week row (which repeats the product label in
    col 0 and puts "週契約" in col 1) values start at col 2; for the "所有契約" row (col 0 is
    already the row label) values start at col 1 — in both cases the 8 value columns are
    buy-top5(spec), buy-top5%, buy-top10(spec), buy-top10%, sell-top5(spec), sell-top5%,
    sell-top10(spec), sell-top10%. Net = buy − sell for the same rank tier (top5 vs top5,
    top10 vs top10) — the same buy-minus-sell fix already applied to the futures counterpart
    fetch_official_taifex_large_trader(), applied here from the start since this endpoint has
    never been parsed before. Unlike largeTraderFutQry (big5), this endpoint's response is
    genuine UTF-8. A bare GET with no POST body already returns TXO's rows first among all
    listed option products (臺指買權/臺指賣權 appear before 電子/金融/individual-stock options),
    so no queryDate/contractId round-trip is needed — same shortcut used for the futures report.
    On total fetch/parse failure, falls back to the last successfully-fetched real result
    instead of a hardcoded literal that would stay frozen forever.

    `target_date` (a "YYYY/MM/DD" string) requests a specific historical date instead of
    today's default page — confirmed 2026-09-17 by reading this page's own bound JS
    ($("#submitButton").click(...) in the page source): the real submission is
    POST queryDate=<date>&contractId=all&datecount=&contractId2= (the plain GET-with-queryDate
    guess tried earlier silently returns today's default page unchanged — contractId=all is
    required, it's not optional despite looking like it in the empty server-rendered <select>).
    When target_date is given, this never falls back to the cached snapshot on failure (that
    cache only ever holds "today"'s data) — callers should treat a None/empty return as "not
    available for that date" and move on.
    """
    try:
        url = "https://www.taifex.com.tw/cht/3/largeTraderOptQry"
        if target_date:
            body = f"queryDate={target_date}&contractId=all&datecount=&contractId2=".encode()
            req = urllib.request.Request(url, data=body, headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"})
        else:
            req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        rows = []
        for t in soup.find_all('table'):
            for r in t.find_all('tr'):
                cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                if cols:
                    rows.append(cols)

        def extract_val(cell):
            m = re.match(r'([\d,]+)', cell)
            return int(m.group(1).replace(',', '')) if m else 0

        def extract_spec(cell):
            if '(' in cell:
                m = re.search(r'\(([\d,]+)\)', cell)
                return int(m.group(1).replace(',', '')) if m else extract_val(cell)
            return extract_val(cell)

        def parse_side(cols, start_idx):
            buy5, sell5 = extract_val(cols[start_idx]), extract_val(cols[start_idx + 4])
            buy10, sell10 = extract_val(cols[start_idx + 2]), extract_val(cols[start_idx + 6])
            spec_buy5, spec_sell5 = extract_spec(cols[start_idx]), extract_spec(cols[start_idx + 4])
            spec_buy10, spec_sell10 = extract_spec(cols[start_idx + 2]), extract_spec(cols[start_idx + 6])
            return {
                'top5_net': buy5 - sell5,
                'top10_net': buy10 - sell10,
                'top5_spec_net': spec_buy5 - spec_sell5,
                'top10_spec_net': spec_buy10 - spec_sell10,
            }

        def parse_product(label):
            for idx, r in enumerate(rows):
                if r and r[0] == label and idx + 2 < len(rows):
                    week_r, total_r = rows[idx], rows[idx + 2]
                    if len(week_r) >= 11 and len(total_r) >= 10 and total_r[0] == '所有契約':
                        return {'week': parse_side(week_r, 2), 'total': parse_side(total_r, 1)}
            return None

        call = parse_product('臺指買權')
        put = parse_product('臺指賣權')
        if call and put:
            result = {
                'call': {**call, **call['total']},
                'put': {**put, **put['total']},
                'is_live': True,
            }
            print(f"[OK] Official TAIFEX TXO Option Large Trader OI: Call top10={result['call']['top10_net']}, Put top10={result['put']['top10_net']}")
            if target_date is None:
                # This cache key means "current/latest", not an archive — a historical backfill
                # call must never overwrite it with an old date's numbers.
                snaps = load_institutional_snapshots()
                snaps[OPT_LARGE_TRADER_SNAPSHOT_KEY] = result
                save_institutional_snapshots(snaps)
            return result
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX Option Large Trader OI ({target_date or 'today'}): {e}")

    if target_date is not None:
        # A historical backfill call has no "last real" snapshot to borrow — that cache only
        # ever holds today's data — so honestly report unavailable for this date instead.
        return None

    snaps = load_institutional_snapshots()
    fallback = snaps.get(OPT_LARGE_TRADER_SNAPSHOT_KEY) or {
        'call': {'week': None, 'total': None, 'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
        'put': {'week': None, 'total': None, 'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
    }
    fallback['is_live'] = False
    return fallback

FUT_INST_OI_SNAPSHOT_KEY = "FUT_INST_OI_LAST_REAL"

def fetch_official_taifex_futures_institutional_oi(target_date=None):
    """
    Parses TAIFEX futContractsDate for TX (大台) Three Major Institutional Net Open Interest
    (Unhedged). On total fetch/parse failure, falls back to the last successfully-fetched real
    result instead of a hardcoded literal that would stay frozen forever.

    `target_date` ("YYYY/MM/DD") requests that specific historical date via this page's own
    `queryDate` GET param (confirmed 2026-09-17: a plain GET with this param works, no POST/
    extra fields needed, unlike the largeTrader*Qry pages). A historical call never touches the
    "current" snapshot cache and returns None on failure rather than borrowing today's cache.
    """
    try:
        url = f"https://www.taifex.com.tw/cht/3/futContractsDate?queryDate={target_date}" if target_date \
            else "https://www.taifex.com.tw/cht/3/futContractsDate"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            soup = BeautifulSoup(resp.read().decode('big5', errors='ignore'), 'html.parser')
            for t in soup.find_all('table'):
                rows = t.find_all('tr')
                for idx, r in enumerate(rows):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols and ('1' in cols or any('臺股期貨' in c for c in cols)):
                        if idx + 2 < len(rows):
                            d_row = [c.get_text(strip=True) for c in rows[idx].find_all(['td', 'th'])]
                            t_row = [c.get_text(strip=True) for c in rows[idx+1].find_all(['td', 'th'])]
                            f_row = [c.get_text(strip=True) for c in rows[idx+2].find_all(['td', 'th'])]
                            res = {
                                'dealer': int(d_row[-2].replace(',', '')),
                                'trust': int(t_row[-2].replace(',', '')),
                                'foreign': int(f_row[-2].replace(',', '')),
                                'is_live': True
                            }
                            print(f"[OK] Official TAIFEX TX Futures Inst Net OI ({target_date or 'today'}): Foreign={res['foreign']}, Trust={res['trust']}, Dealer={res['dealer']}")
                            if target_date is None:
                                snaps = load_institutional_snapshots()
                                snaps[FUT_INST_OI_SNAPSHOT_KEY] = res
                                save_institutional_snapshots(snaps)
                            return res
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX Futures Inst Net OI ({target_date or 'today'}): {e}")

    if target_date is not None:
        return None

    # `is_live: False` here means "borrowed from a prior successful run" — the DAY-session
    # 5-day-history writer must not persist it as today's real snapshot (same fix as the
    # NIGHT session's is_live flag, applied here for parity, 2026-09-16).
    snaps = load_institutional_snapshots()
    fallback = snaps.get(FUT_INST_OI_SNAPSHOT_KEY) or {'dealer': None, 'trust': None, 'foreign': None}
    fallback['is_live'] = False
    return fallback

def fetch_official_taifex_pc_ratio():
    """
    Fetches official TAIFEX Put/Call Ratio statistics from pcRatio.
    """
    res = {}
    try:
        url = "https://www.taifex.com.tw/cht/3/pcRatio"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            soup = BeautifulSoup(resp.read().decode('big5', errors='ignore'), 'html.parser')
            for t in soup.find_all('table'):
                for r in t.find_all('tr'):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if len(cols) >= 7 and '/' in cols[0]:
                        try:
                            date_str = cols[0]
                            ratio_val = float(cols[6])
                            res[date_str] = ratio_val
                        except Exception:
                            pass
            print(f"[OK] Official TAIFEX PC Ratio Records: {len(res)} items loaded")
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX PC Ratio: {e}")
    return res

_MONTH_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}

def fetch_fomc_meeting_dates():
    """
    Fetches the real FOMC meeting schedule from the Federal Reserve's own official calendar
    page (federalreserve.gov/monetarypolicy/fomccalendars.htm). The page looks like an Angular
    app at first glance, but the meeting list itself is plain server-rendered HTML (div.panel
    per year, containing div.fomc-meeting__month / div.fomc-meeting__date pairs) — no JSON API
    needed. Returns a list of {"month_label", "rate_decision_date": date} for every meeting
    found across every year panel on the page (the Fed keeps ~2 years of past + current +
    partial next year on this one page), so this project's own calendar never needs a
    hardcoded, staleness-prone meeting list — it just re-reads the Fed's current publication
    on every run. The rate decision is always announced on the LAST day of a 1-2 day meeting.
    """
    results = []
    try:
        url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            soup = BeautifulSoup(resp.read().decode('utf-8', errors='ignore'), 'html.parser')

        for year_anchor in soup.find_all('a', id=True):
            m = re.match(r'^(\d{4}) FOMC Meetings$', year_anchor.get_text(strip=True))
            if not m:
                continue
            year = int(m.group(1))
            panel = year_anchor.find_parent('div', class_='panel')
            if not panel:
                continue
            for month_div in panel.find_all('div', class_='fomc-meeting__month'):
                date_div = month_div.find_next_sibling('div', class_='fomc-meeting__date')
                if not date_div:
                    continue
                month_text = month_div.get_text(strip=True)
                date_text = re.sub(r'\*|\(.*?\)', '', date_div.get_text(strip=True)).strip()
                months_in_label = month_text.split('/')
                try:
                    start_month = _MONTH_NUM[months_in_label[0].strip().lower()]
                    end_month = _MONTH_NUM[months_in_label[-1].strip().lower()]
                except KeyError:
                    continue
                day_parts = date_text.split('-')
                try:
                    end_day = int(day_parts[-1].strip())
                except (ValueError, IndexError):
                    continue
                try:
                    decision_date = datetime.date(year, end_month, end_day)
                except ValueError:
                    continue
                results.append({"month_label": month_text, "rate_decision_date": decision_date})
        print(f"[OK] Official Federal Reserve FOMC Meeting Schedule: {len(results)} meetings parsed")
    except Exception as e:
        print(f"[Warning] Failed to fetch Fed FOMC calendar: {e}")
    return results

def fetch_taifex_stock_futures_contract_map():
    """
    Fetches TAIFEX's official 股票期貨/股票選擇權 交易標的 reference table (stockLists),
    mapping each underlying stock ticker to its 2-letter TAIFEX stock-futures contract code
    (e.g. "2330" -> "CD"). When both a regular-size and mini-size contract exist for the same
    ticker, the regular one (listed first in the table) is kept.
    Cached locally for 7 days since this mapping rarely changes.
    """
    cache_file = os.path.join(_DATA_DIR, "taifex_stock_futures_contract_map.json")
    try:
        if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < 7 * 86400:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached:
                    return cached
    except Exception:
        pass

    mapping = {}
    try:
        url = "https://www.taifex.com.tw/cht/2/stockLists"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        for t in soup.find_all('table'):
            for r in t.find_all('tr'):
                cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                if len(cols) >= 3 and len(cols[0]) == 2 and cols[0].isalpha() and cols[2].isdigit():
                    mapping.setdefault(cols[2], cols[0])
        print(f"[OK] TAIFEX Stock Futures Contract Map: {len(mapping)} tickers mapped")
        if mapping:
            try:
                os.makedirs(_DATA_DIR, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(mapping, f, ensure_ascii=False)
            except Exception:
                pass
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX Stock Futures Contract Map: {e}")
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
    return mapping

def fetch_taifex_stock_futures_large_trader_batch(contract_map, stock_codes):
    """
    Real per-stock-futures large-trader/institutional net position data from TAIFEX's official
    大額交易人未沖銷部位結構表 (largeTraderFutQry), queried once per individual stock-futures
    contract via its 2-letter code. Unlike the aggregate 三大法人期貨未沖銷部位 page (which only
    breaks TX/TE/TF-class index futures out by name), this page supports a per-contract query
    covering 260+ individual stock futures, confirmed via manual browser testing against
    https://www.taifex.com.tw/cht/3/largeTraderFutQry (POST queryDate=YYYY/MM/DD&contractId=<code>).
    Net positions are the real "所有契約" (all contract months) 買方-賣方 (buy-side minus sell-side)
    difference for the top-5 / top-10 large traders and the "(特定法人合計)" institutional subset.
    Results are cached for the trading day so repeated same-day runs skip the 260+ request batch.
    """
    cache_file = os.path.join(_DATA_DIR, "stock_futures_large_trader_cache.json")
    today_str = datetime.date.today().isoformat()
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("_date") == today_str and cached.get("data"):
                print(f"[OK] TAIFEX Stock Futures Large Trader: using same-day cache ({len(cached['data'])} tickers)")
                return cached["data"]
    except Exception:
        pass

    result = {}
    query_date = None
    try:
        req = urllib.request.Request("https://www.taifex.com.tw/cht/3/largeTraderFutQry", headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        date_input = soup.find('input', {'id': 'queryDate'})
        query_date = date_input.get('value') if date_input else None
    except Exception as e:
        print(f"[Warning] Failed to discover TAIFEX large-trader query date: {e}")

    if not query_date:
        return result

    def _parse_pair(cell):
        m = re.match(r'([\d,]+)\(([\d,]+)\)', cell)
        if m:
            return int(m.group(1).replace(',', '')), int(m.group(2).replace(',', ''))
        m2 = re.match(r'([\d,]+)', cell)
        return (int(m2.group(1).replace(',', '')), 0) if m2 else (0, 0)

    fetched = 0
    for code in stock_codes:
        contract_id = contract_map.get(code)
        if not contract_id:
            continue
        try:
            data = f"queryDate={query_date}&contractId={contract_id}".encode()
            req = urllib.request.Request(
                "https://www.taifex.com.tw/cht/3/largeTraderFutQry",
                data=data,
                headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            for t in soup.find_all('table'):
                for r in t.find_all('tr'):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols and cols[0] == '所有契約' and len(cols) >= 9:
                        buy5, buy5_inst = _parse_pair(cols[1])
                        buy10, buy10_inst = _parse_pair(cols[3])
                        sell5, sell5_inst = _parse_pair(cols[5])
                        sell10, sell10_inst = _parse_pair(cols[7])
                        result[code] = {
                            "top5_net_oi": buy5 - sell5,
                            "top10_net_oi": buy10 - sell10,
                            "top5_inst_oi": buy5_inst - sell5_inst,
                            "top10_inst_oi": buy10_inst - sell10_inst,
                        }
                        fetched += 1
                        break
        except Exception as e:
            print(f"[Warning] TAIFEX large-trader fetch failed for {code} ({contract_id}): {e}")
        time.sleep(0.35)

    print(f"[OK] TAIFEX Stock Futures Large Trader: {fetched}/{len(stock_codes)} tickers fetched for {query_date}")
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"_date": today_str, "query_date": query_date, "data": result}, f, ensure_ascii=False)
    except Exception:
        pass
    return result

def fetch_official_taifex_retail_sentiment():
    """
    Fetches official TAIFEX Institutional Open Interest (futContractsDate) and Market Total OI (futDailyMarketReport)
    to calculate exact Retail Long/Short Ratios for MTX (Small MTX) and TMF (Micro MTX).
    """
    inst = {'MTX': {'long': 0, 'short': 0}, 'TMF': {'long': 0, 'short': 0}}
    inst_ok = {'MTX': False, 'TMF': False}
    # Pin BOTH TAIFEX pages to the same explicit trading date. Without a date, futDailyMarketReport
    # defaults (evenings/weekends) to the in-progress session's 15-column layout whose 未沖銷契約量
    # is in column 10 and still '-', while this code read column 12 = 最後最佳賣價 (a ~48,000 PRICE)
    # as open interest — found 2026-09-26 (the 9/25 snapshot's long/short were inflated by 19,212).
    _tw_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    _ref = _tw_now - datetime.timedelta(days=1) if (_tw_now.hour < 8 or (_tw_now.hour == 8 and _tw_now.minute < 45)) else _tw_now
    _q_date = get_recent_tw_trading_days(_ref, n=1)[-1].strftime('%Y/%m/%d')
    try:
        url_inst = f"https://www.taifex.com.tw/cht/3/futContractsDate?queryDate={_q_date}"
        req = urllib.request.Request(url_inst, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            html = resp.read().decode('big5', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            rows = []
            for t in soup.find_all('table'):
                for r in t.find_all('tr'):
                    cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                    if cols:
                        rows.append(cols)
            
            for idx, r in enumerate(rows):
                if len(r) >= 2:
                    comm = None
                    if r[0] == '4' or '小型' in r[1]:
                        comm = 'MTX'
                    elif r[0] == '5' or '微型' in r[1]:
                        comm = 'TMF'
                    
                    if comm and idx + 2 < len(rows):
                        def get_nums(row):
                            return [int(c.replace(',', '')) for c in row if c.replace(',', '').replace('-', '').isdigit()]
                        f_nums = get_nums(rows[idx])
                        t_nums = get_nums(rows[idx+1])
                        d_nums = get_nums(rows[idx+2])
                        if len(f_nums) >= 6 and len(t_nums) >= 6 and len(d_nums) >= 6:
                            inst[comm]['long'] = f_nums[-6] + t_nums[-6] + d_nums[-6]
                            inst[comm]['short'] = f_nums[-4] + t_nums[-4] + d_nums[-4]
                            inst_ok[comm] = True
    except Exception as e:
        print(f"[Warning] Failed to fetch TAIFEX Institutional Futures OI: {e}")
    
    def parse_taifex_fut_oi(cid):
        url = "https://www.taifex.com.tw/cht/3/futDailyMarketReport"
        params = urllib.parse.urlencode({'queryType': '2', 'marketCode': '0', 'commodity_id': cid, 'queryDate': _q_date}).encode('utf-8')
        try:
            req = urllib.request.Request(url, data=params, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')  # this page is served as UTF-8 (big5 turned the Chinese labels into mojibake)
                soup = BeautifulSoup(html, 'html.parser')
                # Column 12 of this table is 未沖銷契約數 (open interest) — confirmed
                # 2026-09-15 against TAIFEX's raw response (near-month row) AND against two
                # independent brokers' 散戶多空比 published today (both matched exactly once
                # this was fixed). This used to (a) multiply the near-month OI by 2 for no
                # documented reason — real near-month OI is already the whole open-interest
                # count, not one side of it needing doubling — and (b) take the MAX value
                # across the entire "合計" totals row to find "total_oi", which actually grabs
                # 成交量 (trading volume, a much larger unrelated number) instead of column 12's
                # real total open interest. Both bugs inflated the denominator used everywhere
                # downstream for 散戶多空比, diluting the reported ratio well below what TAIFEX's
                # own numbers (and every broker report checked) actually show.
                # This endpoint's declared/actual charset doesn't match 'big5' cleanly for its
                # Chinese labels specifically (confirmed 2026-09-15: the "合計"/"小計" text comes
                # back as mojibake under both big5 and cp950, even though the plain-ASCII
                # numeric cells decode fine either way) — matching on the label text is
                # fragile here. Detect the totals row structurally instead: every real
                # contract-month row starts with the commodity code (e.g. "TMF"/"MTX") in
                # cols[0] and a date/week code in cols[1], while the totals row has both blank.
                near_oi, total_oi = 0, 0
                oi_idx = None  # located from the header text, never hard-coded: layout is 17 cols with an explicit date, 15 without
                for t in soup.find_all('table'):
                    for r in t.find_all('tr'):
                        cols = [c.get_text(strip=True) for c in r.find_all(['td', 'th'])]
                        if oi_idx is None and '*未沖銷契約量' in cols:
                            oi_idx = cols.index('*未沖銷契約量')
                            continue
                        if oi_idx is None or len(cols) <= oi_idx:
                            continue
                        if near_oi == 0 and re.match(r'^\d{6}$', cols[1] if len(cols) > 1 else ''):
                            try: near_oi = int(cols[oi_idx].replace(',', ''))
                            except: pass  # '-' = not published yet -> None -> caller falls back to the previous real value
                        if total_oi == 0 and cols[0] == '' and cols[1] == '':
                            try: total_oi = int(cols[oi_idx].replace(',', ''))
                            except: pass
                return (near_oi or None), (total_oi or None)
        except Exception:
            return None, None

    mtx_near_total, mtx_total = parse_taifex_fut_oi('MTX')
    tmf_near_total, tmf_total = parse_taifex_fut_oi('TMF')
    # No institutional long/short for the pinned date (not published yet) -> the retail derivation
    # (near_oi - institutional) would be meaningless; degrade to the previous real value instead.
    if not inst_ok['MTX']:
        mtx_near_total = mtx_total = None
    if not inst_ok['TMF']:
        tmf_near_total = tmf_total = None

    # Real day-over-day deltas via the same persistent snapshot store used for the
    # institutional 5-day matrix — yesterday's real values, not a hardcoded number, are what
    # daily_change/prev_ratio are actually supposed to mean. Loaded early here too so a total
    # fetch failure below can fall back to yesterday's real derived numbers instead of a
    # frozen literal sentinel (the app.js renderer does raw arithmetic on these fields, so
    # they must always be real numbers, not None).
    _retail_snaps = load_institutional_snapshots()
    # TW-local date, not datetime.date.today() (the runner's system/UTC date) — between UTC
    # 16:00-24:00 those disagree by a calendar day, which would key this under the wrong date.
    # Key by the TRADING day the TAIFEX pages were pinned to (_q_date), not the calendar date: a weekend/holiday run
    # used to write e.g. 2026-09-27_INST_RETAIL (or 2026-09-25 on a holiday) — a non-trading day with borrowed numbers.
    _retail_today_tw_date = datetime.datetime.strptime(_q_date, '%Y/%m/%d').date()
    _retail_today_key = f"{_retail_today_tw_date.isoformat()}_INST_RETAIL"
    _retail_prev_key = max(
        (k for k in _retail_snaps if k.endswith('_INST_RETAIL') and k < _retail_today_key),
        default=None
    )
    _prev = _retail_snaps.get(_retail_prev_key, {}) if _retail_prev_key else {}

    # near_oi (near-month total OI) and total_oi (all-months "合計" row) are two independent
    # parse targets within the same page fetch — one can succeed while the other fails. Each
    # is degraded to yesterday's real persisted value independently, rather than discarding a
    # perfectly good near_oi just because the unrelated total_oi row wasn't found (which used
    # to silently fall back to one magic-literal sentinel pair for BOTH at once).
    mtx_inst_l, mtx_inst_s = inst['MTX']['long'], inst['MTX']['short']
    if mtx_near_total is not None:
        mtx_r_long = max(0, mtx_near_total - mtx_inst_l)
        mtx_r_short = max(0, mtx_near_total - mtx_inst_s)
        mtx_r_net = mtx_r_long - mtx_r_short
        mtx_near_ratio = round((mtx_r_net / mtx_near_total) * 100, 2) if mtx_near_total > 0 else _prev.get('mtx_ratio', 0.0)
    else:
        mtx_r_long = _prev.get('mtx_long_oi', 0)
        mtx_r_short = _prev.get('mtx_short_oi', 0)
        mtx_r_net = _prev.get('mtx_net_oi', 0)
        mtx_near_ratio = _prev.get('mtx_ratio', 0.0)
    mtx_total_ratio = round((mtx_r_net / mtx_total) * 100, 2) if (mtx_total is not None and mtx_total > 0) else _prev.get('mtx_total_ratio', 0.0)

    tmf_inst_l, tmf_inst_s = inst['TMF']['long'], inst['TMF']['short']
    if tmf_near_total is not None:
        tmf_r_long = max(0, tmf_near_total - tmf_inst_l)
        tmf_r_short = max(0, tmf_near_total - tmf_inst_s)
        tmf_r_net = tmf_r_long - tmf_r_short
        tmf_near_ratio = round((tmf_r_net / tmf_near_total) * 100, 2) if tmf_near_total > 0 else _prev.get('tmf_ratio', 0.0)
    else:
        tmf_r_long = _prev.get('tmf_long_oi', 0)
        tmf_r_short = _prev.get('tmf_short_oi', 0)
        tmf_r_net = _prev.get('tmf_net_oi', 0)
        tmf_near_ratio = _prev.get('tmf_ratio', 0.0)
    tmf_total_ratio = round((tmf_r_net / tmf_total) * 100, 2) if (tmf_total is not None and tmf_total > 0) else _prev.get('tmf_total_ratio', 0.0)

    vix_info = fetch_official_taifex_vix()
    vix_idx = vix_info["taifex_vix"]
    vix_chg = vix_info["taifex_vix_change"]

    # Primary ratio = 全月合計未沖銷契約數 as the denominator, NOT near-month — verified
    # 2026-09-15 against two independent brokers' published 散戶多空比 (both matched this
    # exactly, to the basis point, once the near_oi doubling bug above was fixed; the
    # near-month-only ratio this used to treat as primary was silently diluted by roughly a
    # third and never actually matched what any real broker reports).
    mtx_ratio = mtx_total_ratio
    tmf_ratio = tmf_total_ratio

    # Real foreign TX OI + real foreign TXO call/put net amounts, reusing the same official
    # fetchers used elsewhere in this file for the exact same underlying numbers.
    fut_inst_snap = fetch_official_taifex_futures_institutional_oi()
    opt_inst_snap = fetch_official_taifex_options_matrix()
    foreign_tx_net = fut_inst_snap.get('foreign')
    foreign_call_net = opt_inst_snap.get('foreign', {}).get('call_net_amt')
    foreign_put_net = opt_inst_snap.get('foreign', {}).get('put_net_amt')

    mtx_daily_change = (mtx_r_net - _prev['mtx_net_oi']) if (mtx_r_net is not None and _prev.get('mtx_net_oi') is not None) else None
    mtx_prev_ratio = _prev.get('mtx_ratio')
    tmf_daily_change = (tmf_r_net - _prev['tmf_net_oi']) if (tmf_r_net is not None and _prev.get('tmf_net_oi') is not None) else None
    tmf_prev_ratio = _prev.get('tmf_ratio')
    foreign_tx_change = (foreign_tx_net - _prev['foreign_tx_net']) if ('foreign_tx_net' in _prev and foreign_tx_net is not None) else None
    foreign_call_change = (foreign_call_net - _prev['foreign_call_net']) if ('foreign_call_net' in _prev and foreign_call_net is not None) else None
    foreign_put_change = (foreign_put_net - _prev['foreign_put_net']) if ('foreign_put_net' in _prev and foreign_put_net is not None) else None

    write_institutional_snapshot(_retail_today_tw_date.isoformat(), 'RETAIL', {
        'mtx_net_oi': mtx_r_net, 'mtx_ratio': mtx_ratio, 'mtx_total_ratio': mtx_total_ratio,
        'mtx_long_oi': mtx_r_long, 'mtx_short_oi': mtx_r_short,
        'tmf_net_oi': tmf_r_net, 'tmf_ratio': tmf_ratio, 'tmf_total_ratio': tmf_total_ratio,
        'tmf_long_oi': tmf_r_long, 'tmf_short_oi': tmf_r_short,
        'foreign_tx_net': foreign_tx_net, 'foreign_call_net': foreign_call_net, 'foreign_put_net': foreign_put_net
    })

    def _sentiment_tag(ratio):
        if ratio is None:
            return "⚪ 無即時數據"
        return "🔴 散戶極度做多 (軋空看壓)" if ratio > 15 else ("🟠 散戶偏多看壓" if ratio > 5 else ("🟢 散戶極度做空" if ratio < -15 else ("🟢 散戶偏空看撐" if ratio < -5 else "⚖️ 散戶多空平衡")))

    mtx_sentiment_tag = _sentiment_tag(mtx_ratio)
    tmf_sentiment_tag = _sentiment_tag(tmf_ratio)

    call_col = "var(--call-color)"
    put_col = "var(--put-color)"
    neutral_col = "#888888"
    mtx_col = neutral_col if mtx_ratio is None else (call_col if mtx_ratio >= 0 else put_col)
    tmf_col = neutral_col if tmf_ratio is None else (call_col if tmf_ratio >= 0 else put_col)

    if mtx_ratio is None or tmf_ratio is None:
        mtx_line = "小台/微台散戶多空比數據暫時無法取得。"
    else:
        mtx_line = f"小台散戶多空比為 <span style=\"color: {mtx_col}; font-weight:700;\">{mtx_ratio:+.2f}%</span>（全月合計未沖銷契約數為基準，淨部位 {mtx_r_net:+,} 口／近月單一契約月基準 {mtx_near_ratio:+.2f}%），微台多空比為 <span style=\"color: {tmf_col}; font-weight:700;\">{tmf_ratio:+.2f}%</span>（淨部位 {tmf_r_net:+,} 口／近月單一契約月基準 {tmf_near_ratio:+.2f}%）。小台：{mtx_sentiment_tag}；微台：{tmf_sentiment_tag}。"
    # 敘述必須依 VIX 實際水位（與頁面上的四級對照一致：<14 極度平靜、14~18 常態溫和、18~22 恐慌升溫、>22 極度恐慌）
    if vix_idx is None:
        vix_line = "VIX 波動率指數暫時無法取得。"
    else:
        if vix_idx < 14.0:
            _vx_txt, _vx_col = "市場極度平靜，權利金壓縮", "#00e676"
        elif vix_idx < 18.0:
            _vx_txt, _vx_col = "市場情緒常態溫和", "#00b0ff"
        elif vix_idx < 22.0:
            _vx_txt, _vx_col = "市場恐慌升溫，避險需求增加", "#ffd700"
        else:
            _vx_txt, _vx_col = "市場處於極度恐慌區（VIX 高於 22）", "#ff5252"
        vix_line = f"台指 VIX 波動率指數最新為 <span style=\"color: {_vx_col}; font-weight:700;\">{vix_idx:.2f}</span> ({vix_chg:+.2f})，{_vx_txt}。"
    sentiment_summary_html = f"""
    <p style="margin-bottom: 6px;">&#128161; <strong>散戶籌碼動向</strong>：{mtx_line}</p>
    <p style="margin-bottom: 0;">&#9878; <strong>外資與 VIX 波動度觀測</strong>：{vix_line}</p>
    """

    return {
        "retail_mini_ratio": mtx_ratio,
        "retail_micro_ratio": tmf_ratio,
        "retail_sentiment_details": {
            "mini_mtx": {
                "title": "小台散戶籌碼 (MXF)",
                "long_oi": mtx_r_long,
                "short_oi": mtx_r_short,
                "net_oi": mtx_r_net,
                "daily_change": mtx_daily_change,
                "total_oi": mtx_total,
                "near_oi": mtx_near_total,
                "ratio": mtx_ratio,
                "total_ratio": mtx_total_ratio,
                "prev_ratio": mtx_prev_ratio,
                "sentiment_tag": mtx_sentiment_tag
            },
            "micro_tmf": {
                "title": "微台散戶籌碼 (TMF)",
                "long_oi": tmf_r_long,
                "short_oi": tmf_r_short,
                "net_oi": tmf_r_net,
                "daily_change": tmf_daily_change,
                "total_oi": tmf_total,
                "near_oi": tmf_near_total,
                "ratio": tmf_ratio,
                "total_ratio": tmf_total_ratio,
                "prev_ratio": tmf_prev_ratio,
                "sentiment_tag": tmf_sentiment_tag
            },
            "broker_snapshot": {
                "foreign_tx_net": foreign_tx_net,
                "foreign_tx_change": foreign_tx_change,
                "foreign_call_net": foreign_call_net,
                "foreign_call_change": foreign_call_change,
                "foreign_put_net": foreign_put_net,
                "foreign_put_change": foreign_put_change,
                "vix_index": vix_idx,
                "vix_change": vix_chg,
                "market_turnover": None
            },
            "sentiment_summary_html": sentiment_summary_html
        }
    }

def fetch_official_taifex_specific_traders(lt_inst, fut_inst):
    """
    Derives Top 5 / Top 10 Specific Institutional Traders vs Foreign Futures Divergence
    diagnosis from already-fetched real TAIFEX data: `lt_inst` (from
    fetch_official_taifex_large_trader(), which parses largeTraderFutQry and already
    extracts the specific-institutional-trader sub-figures via extract_spec()) and
    `fut_inst` (from fetch_official_taifex_futures_institutional_oi()). This used to
    re-fetch largeTraderFutQry itself but never parsed the response, silently falling
    back to hardcoded numbers every run regardless of fetch success or failure.
    """
    top5_specific_net = lt_inst.get('top5_spec_net')
    top10_specific_net = lt_inst.get('top10_spec_net')
    top5_large_net = lt_inst.get('top5_net')
    top10_large_net = lt_inst.get('top10_net')
    foreign_tx_net = fut_inst.get('foreign')

    if top5_specific_net is None or foreign_tx_net is None:
        return {
            "top5_specific_net": None,
            "top10_specific_net": None,
            "top5_large_net": None,
            "top10_large_net": None,
            "foreign_tx_net": None,
            "divergence_tag": "⚪ 無即時數據",
            "divergence_desc": "大額交易人特定法人部位或外資期貨未平倉數據暫時無法取得。",
            "divergence_state": "UNAVAILABLE"
        }

    # Strategic Divergence Diagnosis
    if foreign_tx_net <= -25000 and top5_specific_net > 0:
        divergence_tag = "🟡 避險套利分歧 (特法做多/勿盲目追空)"
        divergence_desc = f"外資期貨淨留倉偏空 ({foreign_tx_net:,}口)，但前五大特法淨多單高達 +{top5_specific_net:,}口，顯示法人在現貨一籃子股票進行對沖套利，切勿盲目追空。"
        divergence_state = "HEDGING_ARBITRAGE"
    elif foreign_tx_net <= -25000 and top5_specific_net < -5000:
        divergence_tag = "🔴 外資特法同步偏空 (共振殺盤)"
        divergence_desc = f"外資與前五大特法同步維持龐大淨空單 ({foreign_tx_net:,}口 / {top5_specific_net:,}口)，空頭力道共振，需嚴格防守下檔防線。"
        divergence_state = "BEARISH_SYNC"
    elif foreign_tx_net >= 10000 and top5_specific_net > 5000:
        divergence_tag = "🟢 外資特法同步偏多 (共振軋空)"
        divergence_desc = f"外資與前五大特法同步加碼淨多單，大戶籌碼一致看多，多頭格局強勢。"
        divergence_state = "BULLISH_SYNC"
    else:
        divergence_tag = "⚖️ 法人籌碼中性平衡"
        divergence_desc = "外資與特法部位互有增減，整體衍生品對沖風險處於可控常態區間。"
        divergence_state = "NEUTRAL"

    return {
        "top5_specific_net": top5_specific_net,
        "top10_specific_net": top10_specific_net,
        "top5_large_net": top5_large_net,
        "top10_large_net": top10_large_net,
        "foreign_tx_net": foreign_tx_net,
        "divergence_tag": divergence_tag,
        "divergence_desc": divergence_desc,
        "divergence_state": divergence_state
    }

# ==============================================================================
def calculate_dynamic_sector_rotation(stock_futures, now_dt):
    """8 大主題族群的個股期貨「漲跌幅平均」與「成交值占比」。

    2026-10-06 重寫：舊版的 share_pct 是寫死的比例（38/16/6.5/…，加總剛好 100），族群查無成員時還用寫死的假漲跌幅
    （半導體 +1.20、生技軍工 +3.20…）頂替，兩者都不是資料。現在：
      - change_pct：族群內「標準契約」個股期貨漲跌幅的簡單平均（小型契約是同一檔標的，不重複計入）；查無成員 → "—"。
      - share_pct：族群個股期貨成交值（口數 × 近月收盤價 × 契約單位）占全部個股期貨成交值的比例，
        契約單位依期交所規格：個股期貨 2000 股、小型 100 股、ETF 期貨 10000 份、小型 ETF 1000 份；查無成員 → 0。
    族群分類（哪些股票歸哪一組）是本專案自訂的主題分類，不是證交所產業別。
    """
    GROUPS = [
        ("semicon_tech", "💻 半導體與晶圓代工", {"2330", "2330F", "2454", "2303", "3711", "3037", "2379", "3443", "6669"}, ("台積電", "聯發科", "聯電")),
        ("ai_servers", "🤖 AI 伺服器與組裝代工", {"2317", "2382", "3231", "2356", "6669", "2301", "3017", "2376"}, ("鴻海", "廣達", "緯創")),
        ("leo_satellites", "📡 低軌衛星與網通航太", {"3491", "6285", "2312", "2313", "3596", "5388"}, ("昇達科", "啟碁", "華通")),
        ("green_power", "⚡ 重電綠能與儲能太陽能", {"1519", "1503", "1513", "1514", "9958", "6443", "3576", "2406"}, ("華城", "士電", "中興電", "元晶")),
        ("maritime_shipping", "🚢 航運物流與水路運輸", {"2603", "2609", "2615", "2637", "2605", "2618", "2610", "2606"}, ("長榮", "萬海", "陽明", "慧洋")),
        ("construction_realty", "🏢 營建資產與房產建商", {"2542", "2522", "2548", "2501", "2545", "2524", "2511", "2535"}, ("興富發", "遠雄", "國建", "華固", "長虹")),
        ("biotech_defense", "🧬 生技醫療與軍工防衛", {"8033", "2634", "6753", "6446", "1795", "6472", "4743"}, ("雷虎", "漢翔", "藥華藥", "美時")),
        ("financials_trad", "🏦 金融金控與傳產原物料", {"2881", "2882", "2891", "2886", "2884", "2885", "2892", "2002", "1301", "1303"}, ("富邦金", "國泰金", "中信金")),
    ]
    UNIT = {"個股期貨": 2000, "小型個股期貨": 100, "ETF期貨": 10000, "小型ETF期貨": 1000}
    acc = {g[0]: {"chgs": [], "intents": [], "stocks": [], "value": 0.0} for g in GROUPS}
    total_value = 0.0

    for stk in (stock_futures or []):
        code = stk.get('code', '')
        base_code = code[:-1] if (code.endswith('F') and stk.get('category', '').startswith('小型')) else code
        is_mini = base_code != code
        clean_name = stk.get('name', '').replace("期貨", "").replace("個股期", "")
        vol, px = stk.get('fut_volume'), stk.get('fut_price')
        value = (vol * px * UNIT.get(stk.get('category'), 2000)) if isinstance(vol, (int, float)) and isinstance(px, (int, float)) else 0.0
        total_value += value
        for gid, _gname, codes, kws in GROUPS:
            if base_code in codes or any(k in clean_name for k in kws):
                a = acc[gid]
                a["value"] += value
                if not is_mini:
                    a["chgs"].append(stk.get('change_pct', 0.0))
                    if stk.get('intent_tag'):
                        a["intents"].append(stk['intent_tag'])
                    a["stocks"].append((vol or 0, clean_name))
                break

    def calc_stat(arr, intents):
        if not arr:
            return "—", "⚪ 無資料", "var(--gold-accent)"
        avg = round(sum(arr) / len(arr), 2)
        bull_count = sum(1 for it in intents if '真看多' in it)
        bear_count = sum(1 for it in intents if '真看空' in it)
        hedge_count = sum(1 for it in intents if '避險' in it)
        if avg > 1.0 or bull_count >= 2:
            status, color = "🔥 買盤點火狂拉", "var(--call-color)"
        elif avg > 0.2:
            status, color = "📈 買盤點火吸金", "var(--call-color)"
        elif avg < -1.0 or bear_count >= 2:
            status, color = "❄️ 賣壓顯著拉回", "var(--put-color)"
        elif avg < -0.2:
            status, color = "📉 震盪小幅拉回", "var(--put-color)"
        elif hedge_count >= 2:
            status, color = "🛡️ 避險對沖防守", "var(--primary-accent)"
        else:
            status, color = "⚖️ 資金平穩觀望", "var(--gold-accent)"
        return f"{'+' if avg >= 0 else ''}{avg:.1f}%", status, color

    sectors = []
    for gid, gname, _codes, _kws in GROUPS:
        a = acc[gid]
        chg_str, status, color = calc_stat(a["chgs"], a["intents"])
        top = [n for _v, n in sorted(a["stocks"], key=lambda t: -t[0])[:3]]
        sectors.append({
            "name": gname,
            "code": gid,
            "share_pct": round(a["value"] / total_value * 100, 1) if total_value > 0 else 0.0,
            "change_pct": chg_str,
            "status": status,
            "color": color,
            "top_stocks": top,
        })
    return {
        "title": "📊 8 大主題族群個股期貨資金輪動矩陣",
        "note": "占比＝族群個股期貨成交值（口數×近月收盤價×契約單位）占全部個股期貨成交值的比例，由期交所官方成交量估算；漲跌幅為族群內標準契約的簡單平均；主題分類為本專案自訂，不是證交所產業別。",
        "last_updated": now_dt.strftime("%Y-%m-%d %H:%M"),
        "sectors": sectors
    }

# ==============================================================================
# 📸 SESSION SNAPSHOT SYSTEM — Persistent Historical Data Store
# ==============================================================================

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "data")

def _load_last_gex_snapshot():
    """
    Load data/gex_data.json (the previous successful pipeline run's full output), for use as
    a last-resort "most recently known real value" fallback when a live fetch totally fails.
    Several fetch functions used to fall back to a hardcoded literal number in this situation
    (e.g. a spot price or VIX level someone saw on screen once) — those never update and
    silently go stale forever, no matter how much real market movement happens afterward.
    Falling back to the last real pipeline run's own output instead means a total-failure
    fallback is always genuinely real data (just possibly some hours old) rather than a
    permanently frozen guess. Returns {} if no prior run exists yet (fresh checkout).
    """
    try:
        path = os.path.join(_DATA_DIR, 'gex_data.json')
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}
SNAPSHOT_FILE = os.path.join(_DATA_DIR, "session_snapshots.json")
TW_HOLIDAYS_FILE = os.path.join(_DATA_DIR, "tw_holidays.json")

def _load_tw_holidays():
    """Load Taiwan exchange holiday set from local tw_holidays.json."""
    try:
        with open(TW_HOLIDAYS_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f).get('holidays', []))
    except Exception:
        return set()

TW_HOLIDAYS = _load_tw_holidays()  # loaded once at module level

def is_tw_trading_day(d):
    """True if date d is a Taiwan stock/futures trading day."""
    if d.weekday() >= 5:  # Sat=5, Sun=6
        return False
    if d.strftime('%Y-%m-%d') in TW_HOLIDAYS:
        return False
    return True

def taifex_night_label_date(now_dt):
    """
    TAIFEX labels an after-hours (盤後, 15:00 -> 05:00) session by the TRADING DAY it closes into,
    not the calendar day it opens: the night starting Monday 15:00 is labeled Tuesday; the night
    starting Thursday 15:00 before a holiday weekend is labeled the next trading day (confirmed
    2026-09-26 on futDailyMarketReport: default page = trading date 2026/09/29, close 47,956, the
    session that ran Thursday 9/24 evening; futDataDown "2026/09/24 盤後" = 9/23 evening -> 9/24 05:00).
    So the label of the current/most recent night = first trading day >= (today if before 15:00,
    else tomorrow).
    """
    d = now_dt.date() if hasattr(now_dt, 'date') else now_dt
    if getattr(now_dt, 'hour', 0) >= 15:
        d += datetime.timedelta(days=1)
    while not is_tw_trading_day(d):
        d += datetime.timedelta(days=1)
    return d


def get_recent_tw_trading_days(ref_dt, n=5):
    """
    Return the n most recent Taiwan trading days up to and including ref_dt.
    ref_dt: datetime or date object (Taiwan time).
    Returns list of date objects, oldest first.
    """
    _WEEKDAYS_CN = ["(一)", "(二)", "(三)", "(四)", "(五)", "(六)", "(日)"]
    curr = ref_dt.date() if hasattr(ref_dt, 'date') else ref_dt
    days = []
    while len(days) < n:
        if is_tw_trading_day(curr):
            days.append(curr)
        curr -= datetime.timedelta(days=1)
    days.reverse()  # oldest first
    return days

def load_session_snapshots():
    """Load all session snapshots from data/session_snapshots.json."""
    try:
        with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_session_snapshots(snapshots):
    """Persist session snapshots to data/session_snapshots.json."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        json.dump(snapshots, f, ensure_ascii=False, indent=2)

def write_current_session_snapshot(now_dt, session_type,
                                   spot_price, otc_price, txf_price,
                                   zero_gamma, gex_plus_flip,
                                   call_wall, put_wall, max_pain,
                                   pc_ratio, taifex_vix, us_vix,
                                   margin_market, margin_stock,
                                   margin_balance_billion=None, key_date=None):
    """
    Merge-write the current session's real data into the snapshot store.
    Key: YYYY-MM-DD_DAY or YYYY-MM-DD_NIGHT (absolute date, not T-n offset).
    Rule: always overwrite with the latest run (more data = better).
    """
    # NIGHT snapshots are keyed by TAIFEX's label date (the trading day the night closes into), passed
    # in as key_date; DAY snapshots default to the run date (== the day session's own date).
    _key_date = key_date or now_dt.date()
    snap_key = f"{_key_date.strftime('%Y-%m-%d')}_{session_type}"
    snapshots = load_session_snapshots()
    snapshots[snap_key] = {
        "date":             _key_date.strftime('%Y-%m-%d'),
        "session":          session_type,
        "spot_price":       spot_price,
        "otc_price":        otc_price,
        "txf_price":        txf_price,
        "zero_gamma_level": zero_gamma,
        "gex_plus_flip":    gex_plus_flip,
        "call_wall_strike": call_wall,
        "put_wall_strike":  put_wall,
        "max_pain_strike":  max_pain,
        "pc_ratio":         pc_ratio,
        "taifex_vix":       taifex_vix,
        "us_vix":           us_vix,
        "margin_maint_market": margin_market,
        "margin_maint_stock":  margin_stock,
        "margin_balance_billion": margin_balance_billion,
        "written_at":       now_dt.isoformat()
    }
    save_session_snapshots(snapshots)
    print(f"[SNAPSHOT] Written {snap_key} → {SNAPSHOT_FILE}")
    return snap_key

INST_SNAPSHOT_FILE = os.path.join(_DATA_DIR, "institutional_snapshots.json")

def load_institutional_snapshots():
    """Load all institutional 5-day-matrix snapshots from data/institutional_snapshots.json."""
    try:
        with open(INST_SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_institutional_snapshots(snapshots):
    """Persist institutional snapshots to data/institutional_snapshots.json."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(INST_SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        json.dump(snapshots, f, ensure_ascii=False, indent=2)

def write_institutional_snapshot(date_iso, session_type, data):
    """
    Merge-write today's REAL institutional_5day_history / night_institutional_5day_history
    row into the persistent snapshot store, keyed by {date}_INST_{DAY|NIGHT}. This is what
    lets T-1..T-4 in tomorrow's (and later days') matrix be real accumulated history instead
    of hardcoded placeholder numbers — mirrors write_current_session_snapshot()'s pattern.

    Refuses to persist (returns None instead of the key) when `data` is byte-identical to the
    most recent OTHER date's snapshot of the same session_type. Real multi-field TAIFEX
    institutional/retail data essentially never repeats exactly across two different trading
    days, so an exact match almost certainly means the source endpoint hadn't published a new
    report yet at fetch time and silently re-served the previous one, which the caller's own
    is_live/fetch-success check can't detect since the HTTP request and parse both "succeeded"
    normally. Confirmed 2026-09-17 as the actual mechanism behind three real incidents: NIGHT
    session 2026-09-11/2026-09-14 collapsing to one value, NIGHT 2026-09-15/2026-09-16 doing
    the same, and RETAIL 2026-09-16/2026-09-17 doing the same — in all three the upstream
    TAIFEX page's own default `queryDate` genuinely hadn't advanced yet when fetched. This is a
    backstop for every session_type, not a replacement for requesting the exact target date
    directly where the source supports it (see fetch_taifex_night_institutional_trading).
    """
    snap_key = f"{date_iso}_INST_{session_type}"
    snapshots = load_institutional_snapshots()
    suffix = f"_INST_{session_type}"
    other_keys = sorted(k for k in snapshots if k.endswith(suffix) and k != snap_key)
    if other_keys and data:
        _cmp = lambda d: {k: v for k, v in d.items() if k not in ("written_at", "date", "has_snapshot")}
        latest_other_key = other_keys[-1]
        if _cmp(data) == _cmp(snapshots[latest_other_key]):
            print(f"[Warning] Refusing to persist {snap_key}: identical to {latest_other_key} — source likely hadn't published a new report yet, not genuinely unchanged data")
            return None
    snapshots[snap_key] = {**data, "written_at": datetime.datetime.now().isoformat()}
    save_institutional_snapshots(snapshots)
    return snap_key

def generate_gex_payload():
    tw_tz = datetime.timezone(datetime.timedelta(hours=8))
    now_dt = datetime.datetime.now(datetime.timezone.utc).astimezone(tw_tz)
    today_str = now_dt.strftime("%Y-%m-%d")
    now_hour = now_dt.hour

    # Fetch Real TAIFEX TX Prices (Day TX, Night TX, Prev Day TX)
    day_txf_price, night_txf_price, prev_day_txf_price = fetch_official_taifex_tx_prices()

    # Fetch TWSE Spot Indices & Institutional Stock Trading
    indices_info = fetch_twse_realtime_indices()
    spot_price = indices_info["spot_price"]
    spot_change = indices_info["spot_change"]
    spot_change_pct = indices_info["spot_change_pct"]
    otc_price = indices_info["two_price"]
    otc_change = indices_info["two_change"]
    otc_change_pct = indices_info["two_change_pct"]
    # Same explicit-date staleness fix as the largeTrader*Qry/callsAndPutsDate calls below:
    # BFI82U doesn't refresh to today's figures until sometime after today's session closes, so
    # requesting "today" by its own exact date (matching the same day-boundary rule t_days_dates
    # uses) makes "not published yet" honestly come back empty instead of yesterday's real
    # numbers silently re-served as today's.
    _stock_inst_is_before_open = (now_dt.hour < 8 or (now_dt.hour == 8 and now_dt.minute < 45))
    _stock_inst_target_date = (now_dt - datetime.timedelta(days=1)) if _stock_inst_is_before_open else now_dt
    stock_inst = fetch_twse_institutional_stock_trading(target_date=_stock_inst_target_date.strftime('%Y%m%d'))
    if stock_inst is None:
        stock_inst = {'foreign_stock_net': None, 'trust_stock_net': None, 'dealer_stock_net': None, 'total_stock_net': None, 'is_live': False}
    hot_money_data = fetch_5day_exchange_rates()
    # Pin to the T-0 trading day (same day-boundary rule as the 5-day matrix). The function's own
    # default is the calendar date, which on a weekend/holiday asks TAIFEX for a non-trading day.
    _ni_ref = now_dt - datetime.timedelta(days=1) if (now_dt.hour < 8 or (now_dt.hour == 8 and now_dt.minute < 45)) else now_dt
    night_inst_trading = fetch_taifex_night_institutional_trading(target_date=get_recent_tw_trading_days(_ni_ref, n=1)[-1])
    retail_data = fetch_official_taifex_retail_sentiment()

    # Determine Session Type in Taiwan Time (UTC+8):
    now_min = now_dt.minute
    is_night_session = (now_hour >= 15 or now_hour < 8 or (now_hour == 8 and now_min < 45))
    session_type = "NIGHT" if is_night_session else "DAY"
    session_name = "🌙 夜盤動態/收盤校正" if is_night_session else "☀️ 日盤即時動態/結算籌碼"

    txf_price = night_txf_price if is_night_session else day_txf_price

    raw_days_wed, raw_days_fri, raw_days_mth, third_wed = compute_days_to_expiries(now_dt, tw_tz)

    # Compute exact expiration dates
    w1_dt = now_dt + datetime.timedelta(days=raw_days_wed)
    w2_dt = w1_dt + datetime.timedelta(days=7)
    fri_dt = now_dt + datetime.timedelta(days=raw_days_fri)
    mth_dt = third_wed

    weekdays_zh = ['一', '二', '三', '四', '五', '六', '日']
    w1_date_str = f"{w1_dt.strftime('%m/%d')}({weekdays_zh[w1_dt.weekday()]})"
    w2_date_str = f"{w2_dt.strftime('%m/%d')}({weekdays_zh[w2_dt.weekday()]})"
    fri_date_str = f"{fri_dt.strftime('%m/%d')}({weekdays_zh[fri_dt.weekday()]})"
    mth_date_str = f"{mth_dt.strftime('%m/%d')}({weekdays_zh[mth_dt.weekday()]})"

    dte_dates = {
        "w1": f"{w1_date_str}結算",
        "w2": f"{w2_date_str}結算",
        "fri": f"{fri_date_str}結算",
        "m1": f"{mth_date_str}結算"
    }

    # Real TXO open interest (the actual options positioning GEX is supposed to measure) —
    # one request covers the last 5 trading days, which both gives "today" for the live
    # profile below and lets backfill_snapshots.py reuse the same range for real history.
    _txo_days = get_recent_tw_trading_days(now_dt, n=5)
    _txo_oi_by_date = fetch_taifex_txo_open_interest(
        _txo_days[0].strftime('%Y/%m/%d'), _txo_days[-1].strftime('%Y/%m/%d')
    )
    _txo_latest_date = max(_txo_oi_by_date.keys()) if _txo_oi_by_date else None
    if _txo_latest_date:
        _txo_buckets = classify_txo_contract_buckets(_txo_oi_by_date[_txo_latest_date], now=now_dt)
        real_option_chain = build_real_option_chain(_txo_oi_by_date[_txo_latest_date], _txo_buckets)
    else:
        real_option_chain = {}
        print("[Warning] No real TAIFEX TXO open interest available — GEX profile will be flat/zero, not a guessed curve.")

    # Compute GEX Profile
    gex_profile = calculate_true_gex_profile(spot_price, real_option_chain, raw_days_wed, raw_days_fri, raw_days_mth, with_standard=True)
    gex_profile["dte_dates"] = dte_dates

    # Day vs Night Session Shift Metrics
    day_profile = calculate_true_gex_profile(day_txf_price, real_option_chain, raw_days_wed, raw_days_fri, raw_days_mth)
    day_zero_gamma = day_profile['zero_gamma_level']
    day_call_wall = day_profile['call_wall_strike']
    day_put_wall = day_profile['put_wall_strike']
    day_max_pain = day_profile['max_pain_strike']
    day_gex_plus_flip = day_profile['gex_plus_flip']
    day_total_vex = day_profile['total_vex']

    txf_shift = round(night_txf_price - day_txf_price, 1)
    call_wall_shift = gex_profile['call_wall_strike'] - day_call_wall
    put_wall_shift = gex_profile['put_wall_strike'] - day_put_wall
    zero_gamma_shift = round(gex_profile['zero_gamma_level'] - day_zero_gamma, 1)
    gex_plus_flip_shift = round(gex_profile['gex_plus_flip'] - day_gex_plus_flip, 1)
    vex_shift = round(gex_profile['total_vex'] - day_total_vex, 2)

    session_shift = {
        "txf_shift": txf_shift,
        "call_wall_shift": call_wall_shift,
        "put_wall_shift": put_wall_shift,
        "zero_gamma_shift": zero_gamma_shift,
        "gex_plus_flip_shift": gex_plus_flip_shift,
        "vex_shift": vex_shift,
        "day_txf_price": day_txf_price,
        "day_call_wall": day_call_wall,
        "day_put_wall": day_put_wall,
        "day_zero_gamma": day_zero_gamma,
        "day_max_pain": day_max_pain,
        "day_gex_plus_flip": day_gex_plus_flip,
        "day_total_vex": day_total_vex
    }

    # Microstructure Digest
    # Microstructure Digest - Dynamic 4-Phase Session Selector
    now_tw = now_dt  # now_dt is in TWD (UTC+8)
    day_of_week = now_tw.weekday() # 0=Mon, ..., 5=Sat, 6=Sun
    total_min = now_tw.hour * 60 + now_tw.minute

    is_weekend_closed = (day_of_week == 5 and total_min >= 300) or (day_of_week == 6) or (day_of_week == 0 and total_min < 525)

    if is_weekend_closed:
        session_phase = "NIGHT_SETTLED"
        phase_label = "🌙 夜盤 05:00 定案 (週末休市)"
        active_price = night_txf_price if (night_txf_price is not None and night_txf_price > 0) else spot_price
        zg = gex_profile['zero_gamma_level']
        cw = gex_profile['call_wall_strike']
        pw = gex_profile['put_wall_strike']
        mp = gex_profile['max_pain_strike']
    elif 525 <= total_min < 825 and day_of_week < 5:
        session_phase = "DAY_LIVE"
        phase_label = "🔥 日盤盤中 (Live)"
        active_price = day_txf_price if (day_txf_price is not None and day_txf_price > 0) else spot_price
        zg = day_zero_gamma
        cw = day_call_wall
        pw = day_put_wall
        mp = day_max_pain
    elif 825 <= total_min < 900 and day_of_week < 5:
        session_phase = "DAY_SETTLED"
        phase_label = "☀️ 日盤定案 (盤後)"
        active_price = spot_price
        zg = day_zero_gamma
        cw = day_call_wall
        pw = day_put_wall
        mp = day_max_pain
    elif (total_min >= 900 or total_min < 300) and day_of_week < 6:
        session_phase = "NIGHT_LIVE"
        phase_label = "🔥 夜盤盤中 (Live 對沖校正)"
        active_price = night_txf_price if (night_txf_price is not None and night_txf_price > 0) else spot_price
        zg = gex_profile['zero_gamma_level']
        cw = gex_profile['call_wall_strike']
        pw = gex_profile['put_wall_strike']
        mp = gex_profile['max_pain_strike']
    else:
        session_phase = "NIGHT_SETTLED"
        phase_label = "🌙 夜盤 05:00 定案"
        active_price = night_txf_price if (night_txf_price is not None and night_txf_price > 0) else spot_price
        zg = gex_profile['zero_gamma_level']
        cw = gex_profile['call_wall_strike']
        pw = gex_profile['put_wall_strike']
        mp = gex_profile['max_pain_strike']

    is_pos_gamma = active_price >= zg
    flip_dist = round(abs(active_price - zg), 1)

    if is_pos_gamma:
        regime_label = "🔴 正 Gamma 波動度抑制區 (平穩護盤)"
        regime_desc = f"<span style=\"color: var(--call-color); font-weight: 600;\">🛡️ 標的物價格 ({active_price:,.1f}) 高於 Zero Gamma 轉折點 ({zg:,.1f})</span>，做市商採逆風低買高賣對沖，盤勢傾向區域震盪與回測看撐。"
        theme_color = "bull"
    else:
        regime_label = "🟢 負 Gamma 波動度放大區 (避險引爆)"
        regime_desc = f"<span style=\"color: var(--put-color); font-weight: 700;\">⚠️ 警告！標的物價格 ({active_price:,.1f}) 已跌破 Zero Gamma 轉折點 ({zg:,.1f})</span>，做市商順風追跌殺跌，盤中波動度恐劇烈飆升！"
        theme_color = "bear"

    if flip_dist < 100:
        proximity_text = f"⚡ <strong>轉折臨界告急</strong>：價格距離 Gamma 轉折點 (<span style=\"color: var(--primary-accent); font-weight:700;\">{zg:,.1f} 點</span>) 僅 <span style=\"color: var(--gold-accent); font-weight:700;\">{flip_dist} 點</span>，處於變盤臨界邊緣。"
    else:
        proximity_text = f"📏 <strong>轉折距離位移</strong>：價格距 Gamma 轉折點 (<span style=\"color: var(--primary-accent); font-weight:700;\">{zg:,.1f} 點</span>) 相差 <span style=\"color: var(--gold-accent); font-weight:700;\">{flip_dist} 點</span>。"

    if active_price >= cw:
        cw_desc = f"🚀 <strong>Call Wall 已突破</strong>：現價 (<span style=\"color: var(--call-color); font-weight:700;\">{active_price:,.1f}</span>) 已突破天花板 <span style=\"color: var(--gold-accent); font-weight:700;\">{cw:,} 點</span>，引爆伽瑪擠壓 (Gamma Squeeze) 強勢軋空！"
    else:
        cw_desc = f"🛑 <strong>Call Wall 賣壓牆</strong>：天花板位於 <span style=\"color: var(--gold-accent); font-weight: 700;\">{cw:,} 點</span> (距現價 {cw - active_price:.0f} 點)。"

    if active_price <= pw:
        mp_dist = round(active_price - mp, 0)
        mp_text = f"距 Max Pain 大痛點 {mp_dist:.0f} 點" if mp_dist >= 0 else f"已跌破 Max Pain {abs(mp_dist):.0f} 點"
        pw_desc = f"💥 <strong>Put Wall 已跌破 (地板失守)</strong>：現價 (<span style=\"color: var(--put-color); font-weight:700;\">{active_price:,.1f}</span>) 跌破 Put Wall 支撐牆 (<span style=\"color: var(--primary-accent); font-weight:700;\">{pw:,} 點</span>) {pw - active_price:.0f} 點，防線失守，行情向下回測逼近 Max Pain 大痛點位位移區 (<span style=\"color: #a855f7; font-weight:700;\">{mp:,} 點</span>，{mp_text})！"
    else:
        pw_desc = f"🛡️ <strong>Put Wall 支撐牆</strong>：地板位於 <span style=\"color: var(--primary-accent); font-weight: 700;\">{pw:,} 點</span> (距現價 {active_price - pw:.0f} 點)。"

    microstructure_summary = {
        "session_phase": session_phase,
        "phase_label": phase_label,
        "active_price": active_price,
        "regime_label": regime_label,
        "theme_color": theme_color,
        "flip_dist": flip_dist,
        "full_html": f"""
        <p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.88rem;">{regime_desc}</p>
        <p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.88rem;">{proximity_text}</p>
        <p style="margin-bottom: 0; line-height: 1.7; font-size: 0.88rem;">{cw_desc} &nbsp; {pw_desc}</p>
        """
    }

    # ============================================================
    # 📅 Holiday-aware 5 trading day calculator (replaces T-n offset logic)
    # ============================================================
    # Determine the "reference" trading day for today.
    # Before 08:45: today's session hasn't opened → use yesterday as T-0
    # 08:45~13:45: Day session live/settling → today is T-0
    # 13:45 onward: Day session closed → today is T-0 (settled)
    # 15:00~05:00: Night session → today is still T-0
    _WEEKDAYS_CN_LOCAL = ["(一)", "(二)", "(三)", "(四)", "(五)", "(六)", "(日)"]
    is_before_day_open = (now_dt.hour < 8 or (now_dt.hour == 8 and now_dt.minute < 45))
    if is_before_day_open:
        ref_matrix_base = now_dt - datetime.timedelta(days=1)
    else:
        ref_matrix_base = now_dt

    # t_days_dates: list of 5 date objects [T-4, T-3, T-2, T-1, T-0], oldest first
    t_days_dates = get_recent_tw_trading_days(ref_matrix_base, n=5)

    # t_days: legacy string list for backward-compat with institutional_5day_history
    t_days = [f"{d.month}/{d.day} {_WEEKDAYS_CN_LOCAL[d.weekday()]}" for d in t_days_dates]
    ref_matrix_dt = datetime.datetime.combine(t_days_dates[-1], datetime.time(12, 0), tzinfo=now_dt.tzinfo)

    # Found 2026-09-17: these three largeTrader*Qry / callsAndPutsDate pages don't refresh to
    # today's report until sometime after today's session — the SAME unparameterized-default-
    # page staleness already fixed for fetch_taifex_night_institutional_trading(). Calling with
    # no date silently accepted whatever page TAIFEX defaulted to right now (still often
    # yesterday's), which "succeeded" and got persisted as today's real snapshot — that's how
    # 2026-09-16/2026-09-17's DAY-session large-trader fields ended up byte-identical (the
    # write_institutional_snapshot() duplicate guard only catches a fully-identical *combined*
    # record; this aggregates several independent sources, so one stale sub-source didn't make
    # the whole record match). Requesting today's exact date explicitly makes "not published
    # yet" come back as None (verified against a live not-yet-published date) instead of a
    # different day's real numbers — same fix as classify_txo_contract_buckets's redline #6 fix.
    _today_date_slash = t_days_dates[-1].strftime('%Y/%m/%d')

    def _fresh_or_last_real(target_date, fetch_fn, snapshot_key, empty_shape):
        result = fetch_fn(target_date=target_date)
        if result is not None:
            return result
        _snaps = load_institutional_snapshots()
        fallback = _snaps.get(snapshot_key) or dict(empty_shape)
        fallback['is_live'] = False
        return fallback

    opt_inst = _fresh_or_last_real(_today_date_slash, fetch_official_taifex_options_matrix, OPT_MATRIX_SNAPSHOT_KEY, {
        'foreign': {'call_net_amt': None, 'put_net_amt': None, 'call_net_vol': None, 'put_net_vol': None},
        'trust': {'call_net_amt': None, 'put_net_amt': None, 'call_net_vol': None, 'put_net_vol': None},
        'dealer': {'call_net_amt': None, 'put_net_amt': None, 'call_net_vol': None, 'put_net_vol': None},
    })
    lt_inst = _fresh_or_last_real(_today_date_slash, fetch_official_taifex_large_trader, LARGE_TRADER_SNAPSHOT_KEY, {
        'near': {'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
        'far': {'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
        'total': {'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
        'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None,
    })
    opt_lt_inst = _fresh_or_last_real(_today_date_slash, fetch_official_taifex_large_trader_options, OPT_LARGE_TRADER_SNAPSHOT_KEY, {
        'call': {'week': None, 'total': None, 'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
        'put': {'week': None, 'total': None, 'top5_net': None, 'top10_net': None, 'top5_spec_net': None, 'top10_spec_net': None},
    })
    fut_inst = fetch_official_taifex_futures_institutional_oi()
    pc_ratio_dict = fetch_official_taifex_pc_ratio()
    # Align the headline P/C Ratio (top card + matrix T-0 + snapshot) with TAIFEX's OFFICIAL
    # 買賣權未平倉量比率 for the T-0 trading day. gex_profile['pc_ratio'] is a self-computed figure
    # over the chain used for GEX math (9/24: 61.5% vs official 85.33%), which contradicted both the
    # official number and the lower 5-day table on the same page. Falls back to self-computed only
    # when TAIFEX has no row for that date.
    _off_pc_t0 = pc_ratio_dict.get(f"{t_days_dates[4].year}/{t_days_dates[4].month}/{t_days_dates[4].day}")
    if _off_pc_t0 is not None:
        gex_profile['pc_ratio'] = _off_pc_t0

    # Real 5-Day Positioning Matrix. T-4..T-1 are read from data/institutional_snapshots.json —
    # real history persisted day by day (see write_institutional_snapshot below) — instead of
    # the hardcoded literal numbers this block used to contain. A day with no snapshot yet
    # (e.g. right after this fix is deployed) gets has_snapshot=False and null fields, matching
    # the same "—" convention already used for history_10_sessions above, rather than a
    # fabricated number. T-0 (today) is still the live TAIFEX/TWSE fetch below.
    inst_snaps = load_institutional_snapshots()

    _INST_DAY_FIELDS = [
        "top5_net", "top10_net", "top5_spec_net", "top10_spec_net",
        "lt_near", "lt_far", "lt_total",
        "opt_lt_call_top5_net", "opt_lt_call_top10_net", "opt_lt_call_top5_spec_net", "opt_lt_call_top10_spec_net",
        "opt_lt_call_week", "opt_lt_call_total",
        "opt_lt_put_top5_net", "opt_lt_put_top10_net", "opt_lt_put_top5_spec_net", "opt_lt_put_top10_spec_net",
        "opt_lt_put_week", "opt_lt_put_total",
        "foreign_fut_net", "trust_fut_net", "itrust_fut_net", "dealer_fut_net",
        "foreign_stock_net", "trust_stock_net", "itrust_stock_net", "dealer_stock_net", "total_stock_net",
        "foreign_opt_net", "trust_opt_net", "itrust_opt_net", "dealer_opt_net",
        "foreign_opt_call_net", "foreign_opt_put_net",
        "trust_opt_call_net", "trust_opt_put_net",
        "dealer_opt_call_net", "dealer_opt_put_net",
        "pc_ratio"
    ]

    def _inst_null_day(date_label):
        row = {f: None for f in _INST_DAY_FIELDS}
        row["date"] = date_label
        row["has_snapshot"] = False
        return row

    institutional_5day_history = []
    for i in range(4):  # T-4..T-1
        d_iso = t_days_dates[i].strftime('%Y-%m-%d')
        snap = inst_snaps.get(f"{d_iso}_INST_DAY")
        if snap:
            row = {f: snap.get(f) for f in _INST_DAY_FIELDS}
            row["date"] = t_days[i]
            row["has_snapshot"] = True
            institutional_5day_history.append(row)
        else:
            institutional_5day_history.append(_inst_null_day(t_days[i]))

    # T-0 (today): live TAIFEX/TWSE fetch. The .get(key, N) fallbacks below only fire if
    # today's live fetch itself fails (network/parse error) — a separate, smaller residual
    # issue from the T-4..T-1 fix above, left as-is for now and noted for a future pass.
    def _safe_sum(a, b):
        # Guards the extremely rare bootstrap case (fresh checkout, zero prior successful
        # runs ever, AND today's live fetch also fails) where these can still be None.
        return round(a + b, 2) if (a is not None and b is not None) else None

    # DAY-session parity fix with the NIGHT session (2026-09-16): each of the 4 underlying
    # fetches (options matrix, large trader, futures inst OI, TWSE stock trading) falls back
    # to a *borrowed* last-real value on failure without erroring. Before this fix, t0_inst_day
    # was always written to data/institutional_snapshots.json under today's date regardless —
    # so a borrowed value could get permanently duplicated into history exactly like the NIGHT
    # bug found 2026-09-15 (9/11 and 9/14 ending up byte-identical). Only treat today as a real
    # snapshot, and only persist it, when ALL four sources were genuinely live this run.
    _day_is_live = (
        opt_inst.get('is_live', False) and lt_inst.get('is_live', False) and
        opt_lt_inst.get('is_live', False) and
        fut_inst.get('is_live', False) and stock_inst.get('is_live', False)
    )

    t0_inst_day = {
        "date": t_days[4],
        "top5_net": lt_inst.get('top5_net'),
        "top10_net": lt_inst.get('top10_net'),
        "top5_spec_net": lt_inst.get('top5_spec_net'),
        "top10_spec_net": lt_inst.get('top10_spec_net'),
        "lt_near": lt_inst.get('near'),
        "lt_far": lt_inst.get('far'),
        "lt_total": lt_inst.get('total'),
        "opt_lt_call_top5_net": opt_lt_inst.get('call', {}).get('top5_net'),
        "opt_lt_call_top10_net": opt_lt_inst.get('call', {}).get('top10_net'),
        "opt_lt_call_top5_spec_net": opt_lt_inst.get('call', {}).get('top5_spec_net'),
        "opt_lt_call_top10_spec_net": opt_lt_inst.get('call', {}).get('top10_spec_net'),
        "opt_lt_call_week": opt_lt_inst.get('call', {}).get('week'),
        "opt_lt_call_total": opt_lt_inst.get('call', {}).get('total'),
        "opt_lt_put_top5_net": opt_lt_inst.get('put', {}).get('top5_net'),
        "opt_lt_put_top10_net": opt_lt_inst.get('put', {}).get('top10_net'),
        "opt_lt_put_top5_spec_net": opt_lt_inst.get('put', {}).get('top5_spec_net'),
        "opt_lt_put_top10_spec_net": opt_lt_inst.get('put', {}).get('top10_spec_net'),
        "opt_lt_put_week": opt_lt_inst.get('put', {}).get('week'),
        "opt_lt_put_total": opt_lt_inst.get('put', {}).get('total'),
        "foreign_fut_net": fut_inst.get('foreign'),
        "trust_fut_net": fut_inst.get('trust'), "itrust_fut_net": fut_inst.get('trust'), "dealer_fut_net": fut_inst.get('dealer'),
        "foreign_stock_net": stock_inst.get('foreign_stock_net'),
        "trust_stock_net": stock_inst.get('trust_stock_net'),
        "itrust_stock_net": stock_inst.get('trust_stock_net'),
        "dealer_stock_net": stock_inst.get('dealer_stock_net'),
        "total_stock_net": stock_inst.get('total_stock_net'),
        "foreign_opt_net": _safe_sum(opt_inst['foreign']['call_net_amt'], opt_inst['foreign']['put_net_amt']),
        "trust_opt_net": _safe_sum(opt_inst['trust']['call_net_amt'], opt_inst['trust']['put_net_amt']),
        "itrust_opt_net": _safe_sum(opt_inst['trust']['call_net_amt'], opt_inst['trust']['put_net_amt']),
        "dealer_opt_net": _safe_sum(opt_inst['dealer']['call_net_amt'], opt_inst['dealer']['put_net_amt']),
        "foreign_opt_call_net": opt_inst['foreign']['call_net_amt'],
        "foreign_opt_put_net": opt_inst['foreign']['put_net_amt'],
        "trust_opt_call_net": opt_inst['trust']['call_net_amt'],
        "trust_opt_put_net": opt_inst['trust']['put_net_amt'],
        "dealer_opt_call_net": opt_inst['dealer']['call_net_amt'],
        "dealer_opt_put_net": opt_inst['dealer']['put_net_amt'],
        "pc_ratio": pc_ratio_dict.get(f"{t_days_dates[4].year}/{t_days_dates[4].month}/{t_days_dates[4].day}", gex_profile['pc_ratio']),
        "has_snapshot": _day_is_live
    }
    # If today's live fetch of some source failed (e.g. TWSE's WAF answering 307 to the BFI82U call)
    # but a REAL snapshot for this very trading date was already persisted by an earlier run, fill
    # only the missing fields from it rather than showing "—" (seen 2026-09-26: 9/24 cash net
    # buy/sell blank although the 9/24 snapshot held it). Same date, same official source; never
    # another day's numbers.
    if not _day_is_live:
        _t0_snap = inst_snaps.get(f"{t_days_dates[4].strftime('%Y-%m-%d')}_INST_DAY")
        if _t0_snap:
            for _f in _INST_DAY_FIELDS:
                if t0_inst_day.get(_f) is None and _t0_snap.get(_f) is not None:
                    t0_inst_day[_f] = _t0_snap[_f]
            t0_inst_day["has_snapshot"] = True
    institutional_5day_history.append(t0_inst_day)
    if _day_is_live:
        _day_write_key = write_institutional_snapshot(
            t_days_dates[4].strftime('%Y-%m-%d'), "DAY",
            {f: t0_inst_day[f] for f in _INST_DAY_FIELDS}
        )
        if _day_write_key is None:
            t0_inst_day["has_snapshot"] = False

    # 5-Day Night Session Institutional Trading History — same real-snapshot pattern as above.
    _INST_NIGHT_FIELDS = ["foreign_tx", "foreign_tx_amt", "foreign_mtx", "foreign_micro", "dealer_tx", "dealer_tx_amt"]

    def _inst_null_night(date_label):
        row = {f: None for f in _INST_NIGHT_FIELDS}
        row["date"] = date_label
        row["has_snapshot"] = False
        return row

    night_institutional_5day_history = []
    for i in range(4):  # T-4..T-1
        d_iso = t_days_dates[i].strftime('%Y-%m-%d')
        snap = inst_snaps.get(f"{d_iso}_INST_NIGHT")
        if snap:
            row = {f: snap.get(f) for f in _INST_NIGHT_FIELDS}
            row["date"] = t_days[i]
            row["has_snapshot"] = True
            night_institutional_5day_history.append(row)
        else:
            night_institutional_5day_history.append(_inst_null_night(t_days[i]))

    # has_snapshot reflects whether tonight's fetch was genuinely live, not just whether we
    # have *some* number to show. Found 2026-09-15: this used to always write True and always
    # persist, so a fetch failure's borrowed-from-last-real-run values got permanently baked
    # into the snapshot store under *today's* date — indistinguishable later from a second,
    # coincidentally identical, real trading day (that's how 9/11 and 9/14 ended up with byte-
    # identical numbers). Only persist when the fetch was actually live.
    _night_is_live = night_inst_trading.get("is_live", False)
    t0_inst_night = {
        "date": t_days[4],
        "foreign_tx": night_inst_trading["tx_foreign_net_vol"],
        "foreign_tx_amt": night_inst_trading["tx_foreign_net_amt"],
        "foreign_mtx": night_inst_trading["mini_foreign_net_vol"],
        "foreign_micro": night_inst_trading["micro_foreign_net_vol"],
        "dealer_tx": night_inst_trading["tx_dealer_net_vol"],
        "dealer_tx_amt": night_inst_trading["tx_dealer_net_amt"],
        "has_snapshot": _night_is_live
    }
    night_institutional_5day_history.append(t0_inst_night)
    if _night_is_live:
        _night_write_key = write_institutional_snapshot(
            t_days_dates[4].strftime('%Y-%m-%d'), "NIGHT",
            {f: t0_inst_night[f] for f in _INST_NIGHT_FIELDS}
        )
        if _night_write_key is None:
            t0_inst_night["has_snapshot"] = False

    last_foreign_net = institutional_5day_history[-1]["foreign_fut_net"] or 0
    prev_foreign_net = institutional_5day_history[-2]["foreign_fut_net"] or 0
    foreign_change = last_foreign_net - prev_foreign_net

    # Reverse arrays so latest date is at index 0 (top of tables)
    institutional_5day_history = list(reversed(institutional_5day_history))
    night_institutional_5day_history = list(reversed(night_institutional_5day_history))

    contract_notional_billion = round((abs(foreign_change) * txf_price * 200) / 1e8, 1)
    change_sign = "+" if foreign_change >= 0 else ""

    if foreign_change >= 5000:
        sentiment_tag = "🔥 高檔大舉回補 / 追擊多單"
        sentiment_desc = f"外資單日大幅回補 {change_sign}{foreign_change:,} 口（約 {change_sign}{contract_notional_billion} 億 TWD 契約金額），強烈防範嘎空追多。"
    elif foreign_change >= 2000:
        sentiment_tag = "📈 顯著回補偏多"
        sentiment_desc = f"外資單日顯著回補 {change_sign}{foreign_change:,} 口（約 {change_sign}{contract_notional_billion} 億 TWD 契約金額），上檔壓回壓力明顯減輕。"
    elif foreign_change <= -5000:
        sentiment_tag = "⚠️ 暴增高檔避險 / 重手加空"
        sentiment_desc = f"外資單日重手加空 {foreign_change:,} 口（約 -{contract_notional_billion} 億 TWD 契約金額），高檔下檔避險風險飆升。"
    elif foreign_change <= -2000:
        sentiment_tag = "📉 顯著加碼加空"
        sentiment_desc = f"外資單日加碼空單 {foreign_change:,} 口（約 -{contract_notional_billion} 億 TWD 契約金額），防守避險需求上升。"
    else:
        sentiment_tag = "⚖️ 中性觀望 / 微幅調整"
        sentiment_desc = f"外資單日微幅變動 {change_sign}{foreign_change:,} 口（約 {change_sign}{contract_notional_billion} 億 TWD），法人維持既有防守姿態。"

    institutional_sentiment = {
        "tag": sentiment_tag,
        "foreign_net_oi": last_foreign_net,
        "daily_change": foreign_change,
        "notional_billion": contract_notional_billion,
        "description": sentiment_desc
    }

    # Dynamic Executive Digest for Section 3 Top Digest Card
    f_change_str = f"{foreign_change:+,d}"
    f_net_str = f"{last_foreign_net:,d}"
    f_amt_str = f"{contract_notional_billion:.1f}"

    regime_str = "正 Gamma 波動度抑制區" if active_price >= gex_profile['zero_gamma_level'] else "負 Gamma 避險助跌警示區"
    # top5_val/top10_val/spec_val/f_cash/t_cash/d_cash/opt amounts can only be None in the
    # extremely rare bootstrap case (fresh checkout, no prior real snapshot ever, AND today's
    # live fetch also fails) — everyday operation always has real numbers here.
    top5_val = lt_inst.get('top5_net')
    top10_val = lt_inst.get('top10_net')
    spec_val = lt_inst.get('top5_spec_net')
    if top5_val is None or top10_val is None or spec_val is None:
        futures_summary = "📈 <strong>期貨籌碼動向 (Futures Audit)</strong>：大額交易人未平倉數據暫時無法取得。"
    else:
        top5_str = f"{top5_val:+,d}"
        top10_str = f"{top10_val:+,d}"
        spec_str = f"{spec_val:+,d}"
        futures_summary = (
            f"📈 <strong>期貨籌碼動向 (Futures Audit)</strong>："
            f"前五大淨部位 <code>{top5_str} 口</code>、前十大 <code>{top10_str} 口</code>，"
            f"特定法人淨部位 <code>{spec_str} 口</code>。外資台指期未平倉空單 <code>{f_net_str} 口</code>"
            f"（單日變動 <code>{f_change_str} 口</code>，約合 <code>{f_amt_str} 億 TWD</code> 契約金額）。{sentiment_tag}。"
        )

    f_cash = stock_inst.get('foreign_stock_net')
    t_cash = stock_inst.get('trust_stock_net')
    d_cash = stock_inst.get('dealer_stock_net')
    cash_tot = stock_inst.get('total_stock_net')
    if f_cash is None or t_cash is None or d_cash is None:
        cash_summary = "💰 <strong>現貨買賣超動向 (Cash Market Audit)</strong>：三大法人現貨買賣超數據暫時無法取得。"
    else:
        if cash_tot is None:
            cash_tot = round(f_cash + t_cash + d_cash, 2)
        cash_tot_sign = "+" if cash_tot >= 0 else ""
        f_cash_sign = "+" if f_cash >= 0 else ""
        t_cash_sign = "+" if t_cash >= 0 else ""
        d_cash_sign = "+" if d_cash >= 0 else ""
        cash_summary = (
            f"💰 <strong>現貨買賣超動向 (Cash Market Audit)</strong>："
            f"三大法人現貨合計買賣超 <code>{cash_tot_sign}{cash_tot:.2f} 億 TWD</code>！"
            f"其中「外資 <code>{f_cash_sign}{f_cash:.2f} 億</code>」、"
            f"「投信 <code>{t_cash_sign}{t_cash:.2f} 億</code>」與「自營商 <code>{d_cash_sign}{d_cash:.2f} 億</code>」。"
        )

    f_opt_call = opt_inst['foreign']['call_net_amt']
    f_opt_put = opt_inst['foreign']['put_net_amt']
    t_opt_call = opt_inst['trust']['call_net_amt']
    if f_opt_call is None or f_opt_put is None or t_opt_call is None:
        options_structure = "🎯 <strong>選擇權莊家結構 (Options Matrix)</strong>：法人選擇權買賣權未平倉數據暫時無法取得。"
    else:
        f_opt_call_sign = "+" if f_opt_call >= 0 else ""
        f_opt_put_sign = "+" if f_opt_put >= 0 else ""
        t_opt_call_sign = "+" if t_opt_call >= 0 else ""
        options_structure = (
            f"🎯 <strong>選擇權莊家結構 (Options Matrix)</strong>："
            f"外資 Call 買權 <code>{f_opt_call_sign}{f_opt_call:.2f} 億</code> 與 Put 賣權 <code>{f_opt_put_sign}{f_opt_put:.2f} 億</code>；"
            f"投信買權 <code>{t_opt_call_sign}{t_opt_call:.2f} 億</code>。全場 <strong>Call Wall 天花板</strong> 鎖在 <code>{gex_profile['call_wall_strike']:,} 點</code>，"
            f"<strong>Put Wall 地板</strong> 固守於 <code>{gex_profile['put_wall_strike']:,} 點</code>。"
        )

    pc_badge = '🔴 偏多看撐' if gex_profile['pc_ratio'] > 105 else '🟢 偏空看壓'

    sentiment_audit = (
        f"📊 <strong>籌碼體質與散戶比率 (Sentiment Audit)</strong>："
        f"小台與微台散戶指標維繫避險運作。全市場 P/C Ratio 站在 <code>{gex_profile['pc_ratio']:.1f}%</code> ({pc_badge})，莊家下檔防守支撐力道尚存。"
    )

    if active_price <= pw:
        settlement_outlook = (
            f"🔮 <strong>結算展望與操作指南 (Trading Guide)</strong>："
            f"最新行情 (<code>{active_price:,.1f}</code>) 已跌破 Zero Gamma (<code>{gex_profile['zero_gamma_level']:,} 點</code>) 與 Put Wall 支撐牆 (<code>{pw:,} 點</code>)。"
            f"做市商呈現負 Gamma 順風避險追殺，多頭防線失守，行情向下避險尋求 <code>{mp:,} 點</code> Max Pain 大痛點區防守；操作宜提防波動度擴大，嚴禁盲目承接。"
        )
    elif is_pos_gamma:
        settlement_outlook = (
            f"🔮 <strong>結算展望與操作指南 (Trading Guide)</strong>："
            f"現價 (<code>{active_price:,.1f}</code>) 處於 Zero Gamma (<code>{gex_profile['zero_gamma_level']:,} 點</code>) 上方之「正 Gamma 波動度抑制區」。"
            f"若指數守穩 <code>{pw:,} 點</code> Put Wall，做市商對沖買盤護盤持續，拉回尋求支撐；衝高接近 <code>{cw:,} 點</code> Call Wall 壓力區宜逢高分批停利。"
        )
    else:
        settlement_outlook = (
            f"🔮 <strong>結算展望與操作指南 (Trading Guide)</strong>："
            f"現價 (<code>{active_price:,.1f}</code>) 處於 Zero Gamma (<code>{gex_profile['zero_gamma_level']:,} 點</code>) 下方之「負 Gamma 避險助跌區」。"
            f"留意 <code>{pw:,} 點</code> Put Wall 支撐關卡防守，若失守恐引發多頭停損賣壓。"
        )

    executive_digest = {
        "futures_summary": futures_summary,
        "cash_summary": cash_summary,
        "options_structure": options_structure,
        "sentiment_audit": sentiment_audit,
        "settlement_outlook": settlement_outlook
    }

    # Build All Stock Futures from TAIFEX Official Market Data + Catalog + TWSE Spot Prices + Ex-Dividend Schedule
    stock_spot_dict = fetch_twse_stock_spot_prices()
    ex_div_dict = fetch_twse_ex_dividend_schedule()
    taifex_stk_dict = fetch_taifex_official_stock_futures()
    taifex_night_dict = fetch_taifex_official_night_stock_futures()

    # 契約清單：以期交所官方「股票期貨／ETF 期貨保證金」清單為準（含標準與小型契約），
    # taifex_catalog.json 只當作補充資料（分類、夜盤、流動性標籤）。2026-10-06 對帳發現舊的靜態目錄
    # 有 8 檔官方根本沒有的「小型」契約（小型鴻海、廣達、長榮、富邦金、國泰金、欣興、緯創、00878），
    # 並漏掉官方實際存在的 43 檔（多為小型契約），中光電也已更名為中光電投控。
    _catalog_meta = {x['code']: x for x in (load_taifex_270_catalog() or [])}
    catalog_270 = []
    for _code, _info in taifex_stk_dict.items():
        _meta = _catalog_meta.get(_code, {})
        _is_mini = _code.endswith('F')
        _is_etf = (_code[:-1] if _is_mini else _code).startswith('00')
        _cat = _meta.get('category') or (('小型ETF期貨' if _is_etf else '小型個股期貨') if _is_mini else ('ETF期貨' if _is_etf else '個股期貨'))
        catalog_270.append({
            'code': _code,
            'name': _meta.get('name') or (_info['name'] + '期'),
            'category': _cat,
            'has_night': _meta.get('has_night', False),
            'liquidity': _meta.get('liquidity', '中'),
        })
    if not catalog_270:
        print("[Warning] TAIFEX official stock-futures list unavailable — stock futures table will be empty (no static catalog fallback: it contained contracts that do not exist).")

    raw_stock_futures = []
    NIGHT_SESSION_CODES = {"2330", "2330F", "2303", "0050", "0050F", "00679B"}

    if catalog_270:
        for idx, stk in enumerate(catalog_270):
            code = stk['code']
            lookup_code = code[:-1] if (code.endswith('F') and len(code) >= 5) else code
            twse_info = stock_spot_dict.get(code, {}) or stock_spot_dict.get(lookup_code, {})
            has_night = (code in NIGHT_SESSION_CODES) or stk.get('has_night', False)

            spot_p = twse_info.get('price') or stk.get('spot_price') or 0.0

            nq = None
            if has_night and code in taifex_night_dict and (session_phase in ("NIGHT_LIVE", "NIGHT_SETTLED") or is_weekend_closed):
                nq = taifex_night_dict[code]
                fut_price = nq['fut_price']
                chg_pct = nq['change_pct']
            else:
                chg_pct = twse_info.get('change_pct') or stk.get('change_pct', 0.0)
                tf_data = taifex_stk_dict.get(code, {})
                tf_price = tf_data.get('fut_price')
                fut_price = tf_price if (tf_price and tf_price > 0) else spot_p

            tf_data = taifex_stk_dict.get(code, {})
            vol = (nq.get('volume') if nq else 0) or tf_data.get('total_vol') or twse_info.get('volume') or stk.get('volume') or 0
            basis = round(fut_price - spot_p, 2)

            ex_info = ex_div_dict.get(code, {}) or ex_div_dict.get(lookup_code, {})
            ex_date = ex_info.get("ex_date", "-")
            ex_dividend = ex_info.get("dividend", 0.0)
            ex_type = ex_info.get("type", "")

            # Point contribution to TX Index
            if code in ("2330", "2330F"):
                point_contrib = round((spot_p * (chg_pct / 100.0)) * 8.25, 1)
            elif code in ("2303",):
                point_contrib = round((spot_p * (chg_pct / 100.0)) * 0.85, 1)
            elif code in ("0050", "0050F"):
                point_contrib = round((spot_p * (chg_pct / 100.0)) * 1.5, 1)
            else:
                point_contrib = round((spot_p * (chg_pct / 100.0)) * 0.1, 1)

            spot_vol = twse_info.get('volume')   # 沒有官方現貨成交量就留空（畫面顯示 —），不再用「期貨量 × 5」估算
            if tf_data.get('in_stf') and not nq:
                # 官方股期行情表有這檔：成交量就是官方數字（沒成交＝0），不可再拿現貨成交量頂替（2026-10-06 修正）
                fut_vol = tf_data.get('total_vol', 0)
            else:
                fut_vol = tf_data.get('total_vol') or (nq.get('volume') if nq else 0) or 0   # 沒有官方期貨成交量＝0（未知），不再拿現貨量頂替

            raw_stock_futures.append({
                "code": code,
                "name": stk['name'],
                "category": stk.get('category', '個股期貨'),
                "has_night": has_night,
                "liquidity": stk.get('liquidity', '中'),
                "spot_price": spot_p,
                "spot_volume": spot_vol,
                "fut_price": fut_price,
                "fut_volume": fut_vol,
                "basis": basis,
                "basis_tag": "🔴 正價差" if basis >= 0 else "🟢 逆價差",
                "change_pct": chg_pct,
                "point_contrib": point_contrib,
                "volume": fut_vol,
                "ex_date": ex_date,
                "ex_dividend": ex_dividend,
                "ex_type": ex_type,
                # 期交所官方日盤行情表（STF）：未平倉量（各到期月加總）、與前一交易日的增減、近月漲跌幅與振幅
                "fut_oi": tf_data.get('oi'),
                "fut_oi_chg": tf_data.get('oi_chg'),
                "fut_vol_chg": tf_data.get('vol_chg'),
                "fut_chg_pct": tf_data.get('fut_chg_pct'),
                "amplitude_pct": tf_data.get('amplitude_pct'),
                "fut_data_date": tf_data.get('data_date'),
            })

    # Sort stock futures by real TAIFEX daily futures volume
    raw_stock_futures.sort(key=lambda x: x['fut_volume'], reverse=True)

    # Real per-stock-futures large-trader positioning (TAIFEX largeTraderFutQry, batched + cached per day)
    stock_lt_contract_map = fetch_taifex_stock_futures_contract_map()
    stock_lt_data = fetch_taifex_stock_futures_large_trader_batch(
        stock_lt_contract_map, [it['code'] for it in raw_stock_futures]
    )

    # Real per-stock spot-side institutional net buy/sell (TWSE T86, cached per day)
    twse_t86_data = fetch_twse_institutional_t86_latest()

    # Real multi-day per-stock T86 history for 投信認養/籌碼偏多 — built and rolled forward by
    # scripts/build_screener_cache.py (update_inst_history()), read-only here. Falls back to {}
    # (never fabricated) if that script hasn't run yet on this machine.
    try:
        with open(os.path.join(_DATA_DIR, "stock_institutional_history.json"), "r", encoding="utf-8") as f:
            _stock_inst_history = json.load(f)
    except Exception:
        _stock_inst_history = {}

    def _compute_it_flags(code):
        """Same definition as build_screener_cache.py's compute_inst_flags(): 投信認養 = trust
        net-buy on 3+ consecutive most-recent trading days on file; 籌碼偏多 = 三大法人合計 net
        positive on 2+ of the most recent 3 days. Honestly 0/False when fewer than 3 real days
        exist for this code yet."""
        dates_desc = sorted(_stock_inst_history.keys(), reverse=True)
        consec = 0
        for d in dates_desc:
            row = _stock_inst_history[d].get(code)
            if row is None or row.get("trust", 0) <= 0:
                break
            consec += 1
        recent3 = [_stock_inst_history[d].get(code) for d in dates_desc[:3]]
        recent3 = [r for r in recent3 if r is not None]
        bull = len(recent3) >= 3 and sum(1 for r in recent3 if r.get("total", 0) > 0) >= 2
        return consec, bull

    _adr_quote_cache = {}  # avoid re-fetching the same ADR ticker for both "2330" and "2330F" rows

    stock_futures = []
    for idx, item in enumerate(raw_stock_futures):
        chg_pct = item['change_pct']
        basis = item['basis']

        # NOTE: this used to seed is_top10_buy/is_top10_sell/top10_net_oi/top5_net_oi/
        # top10_inst_oi/top5_inst_oi/spot_inst_net/spot_foreign/spot_trust/spot_dealer/
        # spot_gov with idx-bucketed fabricated formulas here. Confirmed dead: every one of
        # those names is unconditionally overwritten below by the real TAIFEX large-trader
        # data (or 0 + *_data_unavailable=True) and the real TWSE T86 data (or 0 +
        # spot_data_unavailable=True), and is_top10_buy/is_top10_sell are separately
        # reassigned again further down from top10_bull_codes/top10_bear_codes. Removed.

        # ── Real futures-side large-trader positioning (TAIFEX largeTraderFutQry) ──
        # Overrides the placeholder top5/top10 figures above with the actual per-contract
        # 前五大/前十大交易人合計 買方-賣方 net position fetched for this stock's TAIFEX
        # stock-futures contract code.
        _lt_code = item['code']
        _lt_lookup_code = _lt_code[:-1] if (_lt_code.endswith('F') and len(_lt_code) >= 5) else _lt_code
        lt_real = stock_lt_data.get(_lt_code) or stock_lt_data.get(_lt_lookup_code)
        if lt_real:
            top5_net_oi = lt_real['top5_net_oi']
            top10_net_oi = lt_real['top10_net_oi']
            top5_inst_oi = lt_real['top5_inst_oi']
            top10_inst_oi = lt_real['top10_inst_oi']
            item["lt_data_unavailable"] = False
        else:
            top5_net_oi = top10_net_oi = top5_inst_oi = top10_inst_oi = 0
            item["lt_data_unavailable"] = True

        # ── Real spot-side institutional net buy/sell (TWSE T86) ──
        # Overrides the placeholder spot_inst_net / spot_foreign / spot_trust / spot_dealer
        # above with the real per-stock 三大法人買賣超 from TWSE's official T86 report.
        # spot_gov (八大官股銀行) has no official per-stock source and is left at 0 with
        # spot_data_unavailable=True rather than a fabricated ratio of spot_inst_net.
        t86_real = twse_t86_data.get(_lt_code) or twse_t86_data.get(_lt_lookup_code)
        if t86_real:
            spot_foreign = t86_real['spot_foreign']
            spot_trust = t86_real['spot_trust']
            spot_dealer = t86_real['spot_dealer']
            spot_inst_net = t86_real['spot_inst_net']
            spot_gov = 0
            item["spot_data_unavailable"] = False
        else:
            spot_foreign = spot_trust = spot_dealer = spot_gov = 0
            spot_inst_net = 0
            item["spot_data_unavailable"] = True

        # AI Quant Strategic Intent Diagnosis
        # 缺少官方期貨大戶或現貨法人資料時（上面都被填成 0），不能因為「數字是 0」就判成「觀望分歧」——
        # 那會把「沒有資料」誤報成「有資料且分歧」（2026-10-06 對帳：76 檔屬此情況）。
        if item.get("lt_data_unavailable") or item.get("spot_data_unavailable"):
            intent_tag = "⚪ 資料不足"
            intent_desc = "缺少官方大戶或三大法人資料，不判斷"
        elif spot_inst_net >= 80 and top10_net_oi >= 50:
            intent_tag = "🔥 強勢真看多"
            intent_desc = "現貨三大法人大買 + 期貨大戶做多 (雙向多頭共振)"
        elif spot_inst_net <= -80 and top10_net_oi <= -50:
            intent_tag = "❄️ 強勢真看空"
            intent_desc = "現貨三大法人甩賣 + 期貨大戶放空 (現期雙殺壓制)"
        elif spot_inst_net >= 80 and top10_net_oi <= -50:
            intent_tag = "🛡️ 對沖避險"
            intent_desc = "現貨法人買進 + 期貨大戶放空避險 (鎖定獲利/除息保護)"
        elif spot_inst_net <= -80 and top10_net_oi >= 50:
            intent_tag = "⚡ 基差套利"
            intent_desc = "現貨賣出/借券 + 期貨大戶買進多單 (逆價差套利)"
        else:
            intent_tag = "⚖️ 觀望分歧"
            intent_desc = "現現與期貨籌碼力道平淡/無顯著趨勢"

        # Investment Trust adoption (投信波段認養佔比 & 連買天數): this used to be a fake
        # idx-modulo formula unrelated to any real data. Now real, from the same rolling
        # per-stock T86 history data/stock_institutional_history.json feeds the trading room's
        # screener with (see _compute_it_flags above) — 投信 net-buying 3+ consecutive days.
        # it_ratio (佔股本比) has no official per-stock source and stays None rather than a
        # guessed ratio; the badge is based purely on the real consecutive-day count.
        it_consec_days, _it_chip_bull = _compute_it_flags(_lt_lookup_code)
        it_ratio = None
        is_it_adopted = it_consec_days >= 3
        it_badge = f"投信{it_consec_days}日連買" if is_it_adopted else "-"

        # Night Stock Futures with ADR linkage (Complete Taiwan ADR Matrix). Ticker mapping is
        # static (which US ADR corresponds to which TW stock doesn't change), but the % change
        # is fetched live per run below — was previously also a frozen historical number.
        # Also fixed: this used to key off `code`, a stale variable left over from the
        # catalog_270 loop earlier in this function (Python for-loop variables aren't scoped to
        # the loop), not this row's own ticker — every row's ADR link was effectively random.
        ADR_TICKER_MAPPING = {
            "2330": "TSM", "2330F": "TSM",
            "2303": "UMC", "2303F": "UMC",
            "3711": "ASX", "3711F": "ASX",
            "2317": "HNHPF", "2317F": "HNHPF",
            "2409": "AUOTY", "2409F": "AUOTY",
            "2412": "CHT", "2412F": "CHT",
            "8150": "IMOS", "8150F": "IMOS",
            "2882": "CHYYY", "2882F": "CHYYY",
            "2881": "FUISY", "2881F": "FUISY",
            "0050": "EWT", "0050F": "EWT",
            "00679B": "TLT"
        }
        ADR_DISPLAY_NAMES = {
            "TSM": "TSM (台積電ADR)", "UMC": "UMC (聯電ADR)", "ASX": "ASX (日月光ADR)",
            "HNHPF": "HNHPF (鴻海ADR)", "AUOTY": "AUOTY (友達ADR)", "CHT": "CHT (中華電ADR)",
            "IMOS": "IMOS (南茂ADR)", "CHYYY": "CHYYY (國泰金ADR)", "FUISY": "FUISY (富邦金ADR)",
            "EWT": "EWT (MSCI台灣ETF)", "TLT": "TLT (美債20Y ETF)"
        }
        adr_ticker = ADR_TICKER_MAPPING.get(item['code'])
        if adr_ticker:
            if adr_ticker not in _adr_quote_cache:
                _adr_quote_cache[adr_ticker] = fetch_yahoo_finance_quote(adr_ticker)
            adr_quote = _adr_quote_cache[adr_ticker]
            adr_info = {
                "adr_symbol": ADR_DISPLAY_NAMES.get(adr_ticker, adr_ticker),
                "adr_change_pct": adr_quote['change_pct'] if adr_quote else None,
                "adr_basis": "-"  # real basis needs the ADR conversion ratio + live USD/TWD, not computed yet
            }
        else:
            adr_info = {"adr_symbol": "-", "adr_change_pct": None, "adr_basis": "-"}

        item["it_adoption_ratio"] = it_ratio
        item["it_consecutive_buy_days"] = it_consec_days
        item["is_it_adopted"] = is_it_adopted
        item["it_badge"] = it_badge
        item["adr_symbol"] = adr_info["adr_symbol"]
        item["adr_change_pct"] = adr_info["adr_change_pct"]
        item["adr_basis"] = adr_info["adr_basis"]

        item["spot_inst_net"] = spot_inst_net
        item["spot_foreign"] = spot_foreign
        item["spot_trust"] = spot_trust
        item["spot_dealer"] = spot_dealer
        item["spot_gov"] = spot_gov

        item["top5_net_oi"] = top5_net_oi
        item["top10_net_oi"] = top10_net_oi
        item["top5_inst_oi"] = top5_inst_oi
        item["top10_inst_oi"] = top10_inst_oi

        item["foreign_net"] = spot_inst_net
        item["dealer_net"] = top10_net_oi
        item["intent_tag"] = intent_tag
        item["intent_desc"] = intent_desc
        item["is_top10_buy"] = False   # Will be re-assigned in second pass below
        item["is_top10_sell"] = False  # Will be re-assigned in second pass below
        item["trend"] = "Bull" if chg_pct >= 0 else "Bear"
        stock_futures.append(item)

    # ── 第二輪後處理：依「籌碼意圖」篩選，再依「期貨大戶浮部位」排序，取前 10 名標記 ──
    # Top10多：意圖=強勢真看多 → 依 top10_net_oi 降序 (最大多單在前)
    true_bull = [item for item in stock_futures if "強勢真看多" in (item.get("intent_tag") or "")]
    true_bull.sort(key=lambda x: x.get("top10_net_oi", 0), reverse=True)
    top10_bull_codes = {item["code"] for item in true_bull[:10]}

    # Top10空：意圖=強勢真看空 → 依 top10_net_oi 升序 (最大空單在前)
    true_bear = [item for item in stock_futures if "強勢真看空" in (item.get("intent_tag") or "")]
    true_bear.sort(key=lambda x: x.get("top10_net_oi", 0))
    top10_bear_codes = {item["code"] for item in true_bear[:10]}

    for item in stock_futures:
        item["is_top10_buy"] = item["code"] in top10_bull_codes
        item["is_top10_sell"] = item["code"] in top10_bear_codes

    sector_capital_rotation = calculate_dynamic_sector_rotation(stock_futures, now_dt)


    gp_base = gex_profile['gex_plus_flip']
    prev_day_spot = round(spot_price - spot_change, 2)
    prev_day_otc = round(otc_price - otc_change, 2)

    # Previously had its own hardcoded fallback literals (26.09/15.74) on top of
    # fetch_official_taifex_vix()'s own internal fallback — removed so a genuine failure
    # propagates as None instead of a second layer of guessed numbers.
    vix_obj = fetch_official_taifex_vix()
    latest_t_vix = vix_obj.get("taifex_vix")
    latest_u_vix = vix_obj.get("us_vix")

    # ============================================================
    # 📸 SNAPSHOT-BASED HISTORICAL SESSION MATRIX
    # Builds history_10_sessions from persistent snapshots.
    # T-4 to T-1: read from data/session_snapshots.json (real data)
    # T-0: built from live API data, then written to snapshots.
    # Has_snapshot=False → frontend displays "—" instead of fake numbers.
    # ============================================================
    _WDAY_CN = ["(一)", "(二)", "(三)", "(四)", "(五)", "(六)", "(日)"]
    snapshots = load_session_snapshots()

    def _make_null_session(sess_id, t_label, day_date, sess_type):
        disp = f"{day_date.month}/{day_date.day} {_WDAY_CN[day_date.weekday()]}"
        emoji = "☀️" if sess_type == "DAY" else "🌙"
        lbl   = f"{t_label} {'日盤' if sess_type == 'DAY' else '夜盤'}"
        return {
            "id": sess_id, "label": lbl,
            "date_display": f"{disp} {emoji}",
            "full_name": f"{disp} {lbl} (快照建立中)",
            "spot_price": None, "two_price": None, "txf_price": None,
            "zero_gamma_level": None, "gex_plus_flip": None,
            "call_wall_strike": None, "put_wall_strike": None, "max_pain_strike": None,
            "shift_vs_prev": None, "pc_ratio": None,
            "margin_maint_market": None, "margin_maint_stock": None, "margin_maint_published": False,
            "margin_balance_billion": None,
            "taifex_vix": None, "us_vix": None, "has_snapshot": False
        }

    def _make_snap_session(sess_id, t_label, day_date, sess_type, snap):
        disp = f"{day_date.month}/{day_date.day} {_WDAY_CN[day_date.weekday()]}"
        emoji = "☀️" if sess_type == "DAY" else "🌙"
        lbl   = f"{t_label} {'日盤' if sess_type == 'DAY' else '夜盤'}"
        return {
            "id": sess_id, "label": lbl,
            "date_display": f"{disp} {emoji}",
            "full_name": f"{disp} {lbl}" + ("" if sess_type == "DAY" else " (05:00 定案版)"),
            "spot_price": snap.get("spot_price"), "two_price": snap.get("otc_price"), "txf_price": snap.get("txf_price"),
            "zero_gamma_level": snap.get("zero_gamma_level"), "gex_plus_flip": snap.get("gex_plus_flip"),
            "call_wall_strike": snap.get("call_wall_strike"), "put_wall_strike": snap.get("put_wall_strike"),
            "max_pain_strike": snap.get("max_pain_strike"), "shift_vs_prev": 0,
            "pc_ratio": snap.get("pc_ratio"),
            "margin_maint_market": snap.get("margin_maint_market"), "margin_maint_stock": snap.get("margin_maint_stock"),
            "margin_maint_published": sess_type == "DAY",
            "margin_balance_billion": snap.get("margin_balance_billion"),
            "taifex_vix": snap.get("taifex_vix"), "us_vix": snap.get("us_vix"), "has_snapshot": True
        }

    # Build T-4 to T-1 from snapshots (t_days_dates[0..3])
    _t_labels  = ["T-4", "T-3", "T-2", "T-1"]
    _t_ids_day = ["t4_day", "t3_day", "t2_day", "t1_day"]
    _t_ids_ngt = ["t4_night", "t3_night", "t2_night", "t1_night"]

    history_10_sessions = []
    for i in range(4):  # T-4, T-3, T-2, T-1
        d = t_days_dates[i]
        d_str = d.strftime('%Y-%m-%d')
        for sess_type_h, sid in [("NIGHT", _t_ids_ngt[i]), ("DAY", _t_ids_day[i])]:  # TAIFEX order: the night labeled D closes into D, BEFORE D's day session
            snap_k = f"{d_str}_{sess_type_h}"
            snap   = snapshots.get(snap_k)
            if snap:
                item = _make_snap_session(sid, _t_labels[i], d, sess_type_h, snap)
            else:
                item = _make_null_session(sid, _t_labels[i], d, sess_type_h)
            history_10_sessions.append(item)

    # ---- T-0 today: built from live data ----
    now_hour   = now_dt.hour
    now_minute = now_dt.minute
    is_weekend  = (now_dt.weekday() >= 5)
    is_before_open = (now_hour < 8 or (now_hour == 8 and now_minute < 45))

    t0_date = t_days_dates[4]
    t0_disp = f"{t0_date.month}/{t0_date.day} {_WDAY_CN[t0_date.weekday()]}"

    if is_weekend:
        day_label     = "☀️ T日盤 (定案)"
        day_full_name = f"{t0_disp} T日盤 (定案版)"
        night_label     = "🌙 T夜盤 (05:00 定案)"
        night_full_name = f"{t0_disp} T夜盤 (05:00 定案版)"
    else:
        day_label = "☀️ 日盤 (定案)" if is_before_open else ("🔥 T日盤 (Live)" if (8 <= now_hour < 14) else ("☀️ T日盤 (盤後快照)" if (14 <= now_hour < 15) else "☀️ T日盤 (定案)"))
        day_full_name = f"{t0_disp} 日盤 (定案版)" if is_before_open else (f"{t0_disp} T日盤" + (" (Live 即時動態)" if (8 <= now_hour < 14) else (" (盤後快照/待16:00清算)" if (14 <= now_hour < 15) else " (定案版)")))
        night_label = "🌙 夜盤 (05:00 定案)" if is_before_open else ("🔥 T夜盤 (Live)" if (now_hour >= 15 or now_hour < 5) else "🌙 T夜盤 (05:00 定案)")
        night_full_name = f"{t0_disp} 夜盤 (05:00 定案版)" if is_before_open else (f"{t0_disp} T夜盤" + (" (Live 即時動態)" if (now_hour >= 15 or now_hour < 5) else " (05:00 定案版)"))

    t_target_yyyymmdd = t0_date.strftime('%Y%m%d')
    margin_info = fetch_twse_margin_maintenance(target_date_str=t_target_yyyymmdd, spot_change_pct=spot_change_pct)

    t0_day_shift = round(day_txf_price - (night_txf_price if night_txf_price else prev_day_txf_price), 1)

    t0_day_item = {
        "id": "t0_day",
        "label": day_label,
        "date_display": f"{t0_disp} ☀️",
        "full_name": day_full_name,
        "spot_price": spot_price, "two_price": otc_price, "txf_price": day_txf_price,
        "zero_gamma_level": day_zero_gamma, "gex_plus_flip": day_gex_plus_flip, "call_wall_strike": day_call_wall,
        "put_wall_strike": day_put_wall, "max_pain_strike": day_max_pain, "shift_vs_prev": t0_day_shift,
        "pc_ratio": gex_profile['pc_ratio'],
        "margin_maint_market": margin_info["margin_maint_market"],
        "margin_maint_stock": margin_info["margin_maint_stock"],
        "margin_maint_published": margin_info["is_published"],
        "margin_maint_is_estimated": margin_info.get("is_estimated", True),
        "margin_balance_billion": margin_info.get("margin_balance_billion"),
        "taifex_vix": latest_t_vix, "us_vix": latest_u_vix, "has_snapshot": True
    }

    active_night_spot = night_txf_price if (night_txf_price is not None and night_txf_price > 0 and night_txf_price > 10000) else spot_price

    t0_night_item = {
        "id": "t0_night",
        "label": night_label,
        "date_display": f"{t0_disp} 🌙",
        "full_name": night_full_name,
        "spot_price": active_night_spot, "two_price": otc_price, "txf_price": night_txf_price,
        "zero_gamma_level": gex_profile['zero_gamma_level'], "gex_plus_flip": gex_profile['gex_plus_flip'],
        "call_wall_strike": gex_profile['call_wall_strike'],
        "put_wall_strike": gex_profile['put_wall_strike'], "max_pain_strike": gex_profile['max_pain_strike'],
        "shift_vs_prev": txf_shift,
        "pc_ratio": gex_profile['pc_ratio'],
        "margin_maint_market": margin_info["margin_maint_market"],
        "margin_maint_stock": margin_info["margin_maint_stock"],
        "margin_maint_published": False,
        "margin_maint_is_estimated": margin_info.get("is_estimated", True),
        "margin_balance_billion": margin_info.get("margin_balance_billion"),
        "taifex_vix": latest_t_vix, "us_vix": latest_u_vix, "has_snapshot": True
    }

    # ---- TAIFEX night-session dating (see taifex_night_label_date) ----
    _night_label_date = taifex_night_label_date(now_dt)
    _night_is_t0 = (_night_label_date == t0_date)
    if not _night_is_t0:
        # The live/most recent night closes into a LATER trading day than the last day session
        # (evening after the day session, or a weekend/holiday gap): it is that day's night, shown
        # as its own trailing row instead of being glued onto t0_date.
        _n_disp = f"{_night_label_date.month}/{_night_label_date.day} {_WDAY_CN[_night_label_date.weekday()]}"
        _n_live = (now_hour >= 15 or now_hour < 5) and not is_weekend
        t0_night_item["label"] = "🔥 夜盤 (Live 即時)" if _n_live else "🌙 夜盤 (05:00 定案)"
        t0_night_item["date_display"] = f"{_n_disp} 🌙"
        t0_night_item["full_name"] = f"{_n_disp} 夜盤" + (" (Live 即時動態)" if _n_live else " (05:00 定案版)")

    # 📸 Persist T-0 real snapshot to disk (merge, always latest wins)
    _snap_txf  = day_txf_price  if session_type == "DAY" else night_txf_price
    _snap_zg   = day_zero_gamma if session_type == "DAY" else gex_profile['zero_gamma_level']
    _snap_gpf  = day_gex_plus_flip if session_type == "DAY" else gex_profile['gex_plus_flip']
    _snap_cw   = day_call_wall  if session_type == "DAY" else gex_profile['call_wall_strike']
    _snap_pw   = day_put_wall   if session_type == "DAY" else gex_profile['put_wall_strike']
    _snap_mp   = day_max_pain   if session_type == "DAY" else gex_profile['max_pain_strike']
    write_current_session_snapshot(
        now_dt=now_dt, session_type=session_type,
        key_date=(_night_label_date if session_type == "NIGHT" else None),
        spot_price=spot_price, otc_price=otc_price, txf_price=_snap_txf,
        zero_gamma=_snap_zg, gex_plus_flip=_snap_gpf,
        call_wall=_snap_cw, put_wall=_snap_pw, max_pain=_snap_mp,
        pc_ratio=gex_profile['pc_ratio'],
        taifex_vix=latest_t_vix, us_vix=latest_u_vix,
        margin_market=margin_info["margin_maint_market"],
        margin_stock=margin_info["margin_maint_stock"],
        # Persist the balance only when TWSE's MI_MARGN date matches this session's own date AND the
        # snapshot key's date (the run date — on a weekend the key is that Saturday/Sunday while the
        # balance is Friday's);
        # otherwise it is a different (earlier) day's figure and would be stored under the wrong
        # key (seen 2026-09-26: 9/24's 6151.03 written under the 9/25 holiday and 9/26 keys).
        margin_balance_billion=(margin_info.get("margin_balance_billion")
                                if margin_info.get("is_published") and margin_info.get("pub_date") == now_dt.strftime('%Y%m%d')
                                else None)
    )

    # Compute shift_vs_prev (TXF delta between consecutive sessions)
    if _night_is_t0:
        _t0_rows = [t0_night_item, t0_day_item]
    else:
        _pre_snap = snapshots.get(f"{t0_date.strftime('%Y-%m-%d')}_NIGHT")
        _pre_item = (_make_snap_session("t0_night_pre", "T", t0_date, "NIGHT", _pre_snap) if _pre_snap
                     else _make_null_session("t0_night_pre", "T", t0_date, "NIGHT"))
        _t0_rows = [_pre_item, t0_day_item, t0_night_item]
    _all_sess = history_10_sessions + _t0_rows
    if _all_sess:
        _all_sess[0]['shift_vs_prev'] = 0
    for _si in range(1, len(_all_sess)):
        _cur = _all_sess[_si].get('txf_price')
        _prv = _all_sess[_si-1].get('txf_price')
        if _cur is not None and _prv is not None:
            _all_sess[_si]['shift_vs_prev'] = round(_cur - _prv, 1)

    # 融資餘額變化速度 (margin balance rate-of-change) — reference indicator, not fed into GEX
    # calc. Only DAY sessions carry a real 融資餘額 (MI_MARGN publishes once/day; night reuses
    # the same day's figure like margin_maint already does). Built from real persisted balances
    # only (session_snapshots.json) — never interpolated — so it silently reports fewer days
    # rather than guessing when history is short (e.g. right after this feature ships).
    _day_bal_series = [row.get('margin_balance_billion') for row in _all_sess if row.get('id', '').endswith('_day')]
    _real_bal_series = [b for b in _day_bal_series if b is not None]
    _margin_bal_trend = {"margin_bal_1d_chg_pct": None, "margin_bal_Nd_chg_pct": None, "margin_bal_n_days": 0}
    if len(_real_bal_series) >= 2:
        _today_bal, _prev_bal, _oldest_bal = _real_bal_series[-1], _real_bal_series[-2], _real_bal_series[0]
        _margin_bal_trend["margin_bal_1d_chg_pct"] = round((_today_bal - _prev_bal) / _prev_bal * 100, 2) if _prev_bal else None
        _margin_bal_trend["margin_bal_Nd_chg_pct"] = round((_today_bal - _oldest_bal) / _oldest_bal * 100, 2) if _oldest_bal else None
        _margin_bal_trend["margin_bal_n_days"] = len(_real_bal_series) - 1
    t0_day_item.update(_margin_bal_trend)
    t0_night_item.update(_margin_bal_trend)

    # Add T-0 day session
    history_10_sessions.extend(_t0_rows)

    # Compute exact GEX bar distribution for each historical session on a fixed global strike grid
    # Skip sessions without snapshot data (spot_price is None) to avoid TypeError
    global_base_strike = round(spot_price / 100) * 100
    for sess_item in history_10_sessions:
        s_spot = sess_item['spot_price']
        if s_spot is None or s_spot <= 0:
            sess_item['total_gex'] = None
            sess_item['weekly_gex'] = None
            sess_item['friday_gex'] = None
            sess_item['monthly_gex'] = None
            continue
        # Uses TODAY's real option chain against each session's own real spot price — exactly
        # correct for the T-0 day/night entries; for older sessions this is real OI (not a
        # fabricated curve) but not that specific past day's own OI, since per-strike history
        # backfill is out of scope here (only the scalar zero_gamma/call_wall/etc fields get a
        # true historical backfill, via backfill_snapshots.py).
        sess_prof = calculate_true_gex_profile(s_spot, real_option_chain, raw_days_wed, raw_days_fri, raw_days_mth, fixed_base_strike=global_base_strike)
        sess_item['total_gex'] = sess_prof['total_gex']
        sess_item['weekly_gex'] = sess_prof['weekly_gex']
        sess_item['friday_gex'] = sess_prof['friday_gex']
        sess_item['monthly_gex'] = sess_prof['monthly_gex']

    # Dynamic Gemini AI Scanning Card (ai_ex_dividend_digest)
    top_stk1_name = stock_futures[0]['name'] if len(stock_futures) > 0 else "聯電"
    top_stk1_code = stock_futures[0]['code'] if len(stock_futures) > 0 else "2303"
    top_stk2_name = stock_futures[1]['name'] if len(stock_futures) > 1 else "群創"
    top_stk2_code = stock_futures[1]['code'] if len(stock_futures) > 1 else "3481"

    gex_regime_name = "正 GEX 護盤區" if active_price >= zg else "負 GEX 追殺賣盤區"
    gex_regime_color = "var(--call-color)" if active_price >= zg else "var(--put-color)"

    if active_price < pw:
        wall_defense_text = f"⚠️ 現價已跌破 <span style=\"color: var(--primary-accent); font-weight:700;\">{pw:,} 點 Put Wall 支撐牆</span>，防線失守恐向下回測逼近 Max Pain 大痛點 (<span style=\"color: #a855f7; font-weight:700;\">{mp:,} 點</span>) 防守，做市商負 Gamma 順風避險追殺加劇。"
        wall_outlook_text = f"原波段防守鐵板 <span style=\"color: var(--primary-accent); font-weight:700;\">{pw:,} 點 Put Wall</span> 已失守；結算前夕宜嚴防磁吸尋求 <span style=\"color: #a855f7; font-weight:700;\">{mp:,} 點 Max Pain</span> 或反彈回測 Zero Gamma (<span style=\"color: var(--gold-accent); font-weight:700;\">{zg:,} 點</span>) 之劇烈波動。"
    else:
        wall_defense_text = f"若持續守穩 <span style=\"color: var(--primary-accent); font-weight:700;\">{pw:,} 點 Put Wall 支撐</span>，莊家對沖護盤力道將維繫常態盤整。"
        wall_outlook_text = f"波段防守鐵板位於 <span style=\"color: var(--primary-accent); font-weight:700;\">{pw:,} 點</span> (Put Wall 避險防守柱)；結算前夕宜注意轉折點 <span style=\"color: var(--gold-accent); font-weight:700;\">{zg:,} 點</span> 之磁吸震盪點位。"

    ai_bullet_1 = (
        f"🎯 <strong>台指大盤 GEX 位階與動態判讀 (<span style=\"color: var(--gold-accent); font-weight:700;\">{active_price:,.2f} 點</span>)</strong>："
        f"台指現價 <span style=\"color: var(--gold-accent); font-weight:700;\">{active_price:,.2f} 點</span>，"
        f"對照 Zero Gamma 轉折點 (<span style=\"color: var(--primary-accent); font-weight:700;\">{zg:,} 點</span>)，"
        f"總 GEX 處於 <span style=\"color: {gex_regime_color}; font-weight:700;\">{gex_regime_name}</span>。{wall_defense_text}"
    )

    ai_bullet_2 = (
        f"🧱 <strong>週月選莊家牆與結算位階 (<span style=\"color: var(--gold-accent); font-weight:700;\">{cw:,} / {pw:,}</span>)</strong>："
        f"週月選主力天花板集中於 <span style=\"color: var(--gold-accent); font-weight:700;\">{cw:,} 點</span> (Call Wall 週月選衝高壓力柱)；{wall_outlook_text}"
    )

    s1_name = top_stk1_name.replace('期貨', '').replace('期', '')
    s2_name = top_stk2_name.replace('期貨', '').replace('期', '')
    ai_bullet_3 = (
        f"🔥 <strong>Top 10 期交所真實成交量焦點標的</strong>："
        f"{s1_name}期 ({top_stk1_code}) 與 {s2_name}期 ({top_stk2_code}) 為期交所個股期貨成交量前列標的，"
        f"展現個股期貨交投熱度與動態資金趨勢。"
    )

    # Nearest upcoming ex-dividend among tracked stock futures — was a hardcoded literal
    # ("台積電期(2330) 09/18 季除息 $4.0元") that happened to be roughly right only for the one
    # day this was written, then stays frozen forever pointing at a date that keeps receding
    # into the past. Built here from each item's real ex_date/ex_dividend/ex_type (already
    # attached above from fetch_twse_ex_dividend_schedule()) instead.
    def _ex_date_sort_key(mmdd):
        try:
            mm, dd = (int(x) for x in mmdd.split('/'))
            d = datetime.date(now_dt.year, mm, dd)
            if d < now_dt.date():
                d = datetime.date(now_dt.year + 1, mm, dd)
            return d
        except Exception:
            return None
    _upcoming_ex = sorted(
        (
            (_ex_date_sort_key(item["ex_date"]), item)
            for item in stock_futures
            if item.get("ex_date") and item["ex_date"] != "-" and item.get("ex_dividend")
        ),
        key=lambda pair: pair[0] or datetime.date.max
    )
    if _upcoming_ex and _upcoming_ex[0][0] is not None:
        _ex_item = _upcoming_ex[0][1]
        _ex_name = _ex_item["name"].replace('期貨', '').replace('期', '')
        ai_bullet_4 = (
            f"📅 <strong>近期除權息扣點校正與價差防守</strong>："
            f"{_ex_name}期 ({_ex_item['code']}) {_ex_item['ex_date']} {_ex_item.get('ex_type') or '除權息'} "
            f"<span style=\"color: var(--gold-accent); font-weight:700;\">${_ex_item['ex_dividend']:.2f} 元</span>，"
            f"期價逆價差源自常態配息扣點而非看空避險；除息前夕宜對照 TWSE 官方扣點日程表防範價差誤判。"
        )
    else:
        ai_bullet_4 = "📅 <strong>近期除權息扣點校正與價差防守</strong>：目前追蹤個股期貨標的近期無即將除權息事件，暫無扣點價差需特別留意。"

    ai_ex_dividend_digest = {
        "title": "籌碼、價差與除權息事件量化焦點摘要（程式規則自動產生）",
        "compliance_note": "⚖️ 合規量化學理分析 (非個別證券建議)",
        "bullet_1": ai_bullet_1,
        "bullet_2": ai_bullet_2,
        "bullet_3": ai_bullet_3,
        "bullet_4": ai_bullet_4
    }

    import calendar
    def calculate_macro_events_radar(curr_twd):
        year, month = curr_twd.year, curr_twd.month

        # 1. Weekly Settlement (Next Wednesday 13:30 TWD)
        days_to_wed = (2 - curr_twd.weekday()) % 7
        if days_to_wed == 0 and curr_twd.hour >= 14:
            days_to_wed = 7
        next_wed_dt = (curr_twd + datetime.timedelta(days=days_to_wed)).replace(hour=13, minute=30, second=0, microsecond=0)

        # 2. Monthly Settlement (3rd Wednesday 13:30 TWD)
        first_day = datetime.datetime(year, month, 1, tzinfo=tw_tz)
        offset = (2 - first_day.weekday()) % 7 + 14
        third_wed = datetime.datetime(year, month, 1 + offset, 13, 30, tzinfo=tw_tz)
        if third_wed <= curr_twd:
            m_next = month + 1 if month < 12 else 1
            y_next = year if month < 12 else year + 1
            first_next = datetime.datetime(y_next, m_next, 1, tzinfo=tw_tz)
            offset = (2 - first_next.weekday()) % 7 + 14
            third_wed = datetime.datetime(y_next, m_next, 1 + offset, 13, 30, tzinfo=tw_tz)

        # 3. FTSE Taiwan Futures Settlement (富台指結算): 2nd-to-last trading day of month at 13:45 TWD
        ld_num = calendar.monthrange(year, month)[1]
        last_dt = datetime.datetime(year, month, ld_num, 13, 45, tzinfo=tw_tz)
        while last_dt.weekday() >= 5:
            last_dt -= datetime.timedelta(days=1)
        stw_dt = last_dt - datetime.timedelta(days=1)
        while stw_dt.weekday() >= 5:
            stw_dt -= datetime.timedelta(days=1)
        if stw_dt <= curr_twd:
            m_next = month + 1 if month < 12 else 1
            y_next = year if month < 12 else year + 1
            ld_num = calendar.monthrange(y_next, m_next)[1]
            last_dt = datetime.datetime(y_next, m_next, ld_num, 13, 45, tzinfo=tw_tz)
            while last_dt.weekday() >= 5:
                last_dt -= datetime.timedelta(days=1)
            stw_dt = last_dt - datetime.timedelta(days=1)
            while stw_dt.weekday() >= 5:
                stw_dt -= datetime.timedelta(days=1)

        # 4. MSCI Rebalancing (MSCI 權重甩尾調整): Last trading day of Feb, May, Aug, Nov 13:25 TWD
        msci_months = [2, 5, 8, 11]
        msci_dt = None
        for m in msci_months:
            ld_n = calendar.monthrange(year, m)[1]
            ld_d = datetime.datetime(year, m, ld_n, 13, 25, tzinfo=tw_tz)
            while ld_d.weekday() >= 5:
                ld_d -= datetime.timedelta(days=1)
            if ld_d > curr_twd:
                msci_dt = ld_d
                break
        if not msci_dt:
            ld_n = calendar.monthrange(year + 1, 2)[1]
            ld_d = datetime.datetime(year + 1, 2, ld_n, 13, 25, tzinfo=tw_tz)
            while ld_d.weekday() >= 5:
                ld_d -= datetime.timedelta(days=1)
            msci_dt = ld_d

        # 4.5 US Quadruple Witching Day (美股四巫日): 3rd Friday of Mar/Jun/Sep/Dec, pure real
        # calendar arithmetic (same "Nth weekday of month" pattern as monthly_settlement above)
        # — no external source needed, so this can never go stale.
        def third_friday(y, m):
            first = datetime.date(y, m, 1)
            first_fri = 1 + (4 - first.weekday()) % 7
            return datetime.date(y, m, first_fri + 14)

        witching_months = [3, 6, 9, 12]
        witching_d = None
        for m in witching_months:
            wd = third_friday(year, m)
            wd_dt = datetime.datetime(wd.year, wd.month, wd.day, 21, 30, tzinfo=tw_tz)  # US market close ~4pm ET -> ~21:30-22:30 TWD, kept simple at 21:30
            if wd_dt > curr_twd:
                witching_d = wd_dt
                break
        if not witching_d:
            wd = third_friday(year + 1, 3)
            witching_d = datetime.datetime(wd.year, wd.month, wd.day, 21, 30, tzinfo=tw_tz)

        # 4.6 FOMC Rate Decision (聯準會利率決議): real schedule fetched from the Fed's own
        # official calendar (see fetch_fomc_meeting_dates()) rather than a hardcoded list —
        # the Fed publishes the schedule ~1-2 years ahead, so this stays current on its own as
        # long as this keeps re-fetching, instead of needing someone to type in next year's
        # dates before this quietly goes stale.
        def get_fomc_twd_hour():
            # Rate decision: 2:00pm ET -> 02:00 TWD next day (EDT, summer) / 03:00 TWD (EST, winter)
            return 2 if (3 < month < 11) else 3

        fomc_dt = None
        fomc_meetings = fetch_fomc_meeting_dates()
        for meeting in sorted(fomc_meetings, key=lambda x: x["rate_decision_date"]):
            d = meeting["rate_decision_date"]
            twd_hour = 2 if (3 < d.month < 11) else 3
            candidate_dt = datetime.datetime(d.year, d.month, d.day, tzinfo=tw_tz) + datetime.timedelta(days=1, hours=twd_hour)
            if candidate_dt > curr_twd:
                fomc_dt = candidate_dt
                break

        # Helper for US Daylight Saving Time (DST) TWD Time Conversion
        # Summer (Apr-Oct EDT): US 08:30 AM -> 20:30 TWD | Winter (Nov-Mar EST): US 08:30 AM -> 21:30 TWD
        def get_us_twd_hour(m, summer_hour=20):
            return summer_hour if (3 < m < 11) else (summer_hour + 1)

        # 5. US NFP + Unemployment Rate (大非農 + 失業率): 1st Fri (20:30 Summer / 21:30 Winter TWD)
        first_fri_day = (4 - first_day.weekday()) % 7 + 1
        nfp_h = get_us_twd_hour(month, 20)
        nfp_dt = datetime.datetime(year, month, first_fri_day, nfp_h, 30, tzinfo=tw_tz)
        if nfp_dt <= curr_twd:
            m_next = month + 1 if month < 12 else 1
            y_next = year if month < 12 else year + 1
            first_next = datetime.datetime(y_next, m_next, 1, tzinfo=tw_tz)
            first_fri_day = (4 - first_next.weekday()) % 7 + 1
            nfp_h = get_us_twd_hour(m_next, 20)
            nfp_dt = datetime.datetime(y_next, m_next, first_fri_day, nfp_h, 30, tzinfo=tw_tz)

        # 6. ADP Employment Change (ADP 小非農): Wed before NFP (2 days before NFP 20:15 / 21:15 TWD)
        adp_h = get_us_twd_hour(nfp_dt.month, 20)
        adp_dt = (nfp_dt - datetime.timedelta(days=2)).replace(hour=adp_h, minute=15)

        # 7. Initial Jobless Claims (美每週初領失業金): Next Thursday (20:30 / 21:30 TWD)
        days_to_thu = (3 - curr_twd.weekday()) % 7
        if days_to_thu == 0 and curr_twd.hour >= 21:
            days_to_thu = 7
        jobless_dt = (curr_twd + datetime.timedelta(days=days_to_thu))
        jobless_h = get_us_twd_hour(jobless_dt.month, 20)
        jobless_dt = jobless_dt.replace(hour=jobless_h, minute=30, second=0, microsecond=0)

        # 8. US CPI Inflation Data (美 CPI 通膨數據): 12th of month (20:30 / 21:30 TWD)
        cpi_h = get_us_twd_hour(month, 20)
        cpi_dt = datetime.datetime(year, month, 12, cpi_h, 30, tzinfo=tw_tz)
        if cpi_dt <= curr_twd:
            m_next = month + 1 if month < 12 else 1
            y_next = year if month < 12 else year + 1
            cpi_h = get_us_twd_hour(m_next, 20)
            cpi_dt = datetime.datetime(y_next, m_next, 12, cpi_h, 30, tzinfo=tw_tz)

        candidates = [
            {
                "id": "weekly_settlement",
                "name": "週台指選擇權 (TXO) 結算日",
                "category": "期權結算",
                "impact": "HIGH",
                "impact_label": "🔴 高度防守",
                "pattern_type": "WINDOW_TIME",
                "warning_lead_hours": 12,
                "critical_lead_mins": 90,
                "target_epoch": int(next_wed_dt.timestamp() * 1000),
                "date_display": next_wed_dt.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": "提防結算尾盤 13:00~13:30 做市商拉甩尾盤與權利金歸零磁吸！"
            },
            {
                "id": "monthly_settlement",
                "name": "月台指期/選擇權 (TXF/TXO) 大結算",
                "category": "期權結算",
                "impact": "HIGH",
                "impact_label": "🔴 超高風險",
                "pattern_type": "WINDOW_TIME",
                "warning_lead_hours": 24,
                "critical_lead_mins": 120,
                "target_epoch": int(third_wed.timestamp() * 1000),
                "date_display": third_wed.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": "提防大結算日全天與 13:00~13:30 巨量未平倉平倉擺盪！"
            },
            {
                "id": "stw_settlement",
                "name": "SGX 富台指期貨 (STW) 結算日",
                "category": "跨國結算",
                "impact": "HIGH",
                "impact_label": "🔴 跨國衝擊",
                "pattern_type": "WINDOW_TIME",
                "warning_lead_hours": 12,
                "critical_lead_mins": 90,
                "target_epoch": int(stw_dt.timestamp() * 1000),
                "date_display": stw_dt.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": "提防新加坡富台期結算日 13:30~13:45 跨市場甩尾與大筆開平倉！"
            },
            {
                "id": "msci_rebalance",
                "name": "MSCI 季度/半年度指數權重甩尾調整",
                "category": "市場洗牌",
                "impact": "HIGH",
                "impact_label": "🔴 爆量洗牌",
                "pattern_type": "WINDOW_TIME",
                "warning_lead_hours": 24,
                "critical_lead_mins": 90,
                "target_epoch": int(msci_dt.timestamp() * 1000),
                "date_display": msci_dt.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": "提防尾盤 13:25~13:30 撮合被動基金爆量甩尾，避免最後 5 分鐘市價單追價！"
            },
            {
                "id": "us_nfp_unemp",
                "name": "美國非農就業 (NFP) + 失業率",
                "category": "重磅總經",
                "impact": "HIGH",
                "impact_label": "🔴 波動爆發",
                "pattern_type": "POINT_TIME",
                "warning_lead_hours": 24,
                "critical_lead_mins": 120,
                "target_epoch": int(nfp_dt.timestamp() * 1000),
                "date_display": nfp_dt.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": f"發布前 30 分鐘 ({nfp_dt.strftime('%H:%M')} 起) 流動性急遽抽離，提防數據發布瞬間 50~150 點雙向劇烈刷洗！"
            },
            {
                "id": "us_cpi",
                "name": "美國 CPI 消費者物價指數",
                "category": "重磅總經",
                "impact": "HIGH",
                "impact_label": "🔴 波動爆發",
                "pattern_type": "POINT_TIME",
                "warning_lead_hours": 24,
                "critical_lead_mins": 120,
                "target_epoch": int(cpi_dt.timestamp() * 1000),
                "date_display": cpi_dt.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": f"發布前 30 分鐘 ({cpi_dt.strftime('%H:%M')} 起) 流動性急遽抽離，提防數據發布瞬間 50~150 點雙向劇烈刷洗！"
            },
            {
                "id": "us_adp",
                "name": "美國 ADP 小非農就業數據",
                "category": "重點總經",
                "impact": "MEDIUM",
                "impact_label": "🟡 前瞻警戒",
                "pattern_type": "POINT_TIME",
                "warning_lead_hours": 6,
                "critical_lead_mins": 30,
                "target_epoch": int(adp_dt.timestamp() * 1000),
                "date_display": adp_dt.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": f"發布前 15 分鐘 ({adp_dt.strftime('%H:%M')} 起) 前瞻情緒預熱，提防夜盤開盤前夕情緒性波動。"
            },
            {
                "id": "us_jobless",
                "name": "美國每週初領失業金人數 (Jobless Claims)",
                "category": "每週總經",
                "impact": "MEDIUM",
                "impact_label": "🟡 常態警戒",
                "pattern_type": "POINT_TIME",
                "warning_lead_hours": 6,
                "critical_lead_mins": 30,
                "target_epoch": int(jobless_dt.timestamp() * 1000),
                "date_display": jobless_dt.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": f"每週四夜盤常態數據，觀察 {jobless_dt.strftime('%H:%M')} 公布前夕情緒與美債殖利率聯動。"
            }
        ]

        # 美國 NFP／CPI 發布日：只用 data/us_macro_calendar.json（BLS 官網公布的官方日程，手動抄錄）。
        # 舊版用「CPI＝每月 12 號」「NFP＝第一個週五」推算，2026 年多數月份都不對（例如 9 月 CPI 實為 10/14，10/12 是聯邦假日）。
        # 檔案缺漏或日期已過 → 該事件不顯示。ADP 官網沒有未來日程，不收錄。
        def _official_us_release(kind):
            try:
                with open(os.path.join(_DATA_DIR, "us_macro_calendar.json"), "r", encoding="utf-8") as f:
                    cal = json.load(f)
                try:
                    from zoneinfo import ZoneInfo
                    ny = ZoneInfo("America/New_York")
                except Exception:
                    ny = None
                for it in sorted(cal.get(kind, []), key=lambda x: x["release_date"]):
                    d0 = datetime.date.fromisoformat(it["release_date"])
                    if ny is not None:
                        dt = datetime.datetime(d0.year, d0.month, d0.day, 8, 30, tzinfo=ny).astimezone(tw_tz)
                    else:   # 無時區資料庫時的近似：美東夏令（4~10 月）→ 台北 20:30，冬令 → 21:30
                        dt = datetime.datetime(d0.year, d0.month, d0.day, get_us_twd_hour(d0.month, 20), 30, tzinfo=tw_tz)
                    if dt > curr_twd:
                        return dt
            except Exception as e:
                print(f"[Calendar] us_macro_calendar.json unavailable: {e}")
            return None

        _official_dt = {"us_nfp_unemp": _official_us_release("empsit"), "us_cpi": _official_us_release("cpi")}
        _kept = []
        for c in candidates:
            if c["id"] == "us_adp":
                continue
            if c["id"] in _official_dt:
                odt = _official_dt[c["id"]]
                if odt is None:
                    continue
                c["target_epoch"] = int(odt.timestamp() * 1000)
                c["date_display"] = odt.strftime("%m/%d %H:%M (台灣時間)")
                c["gex_advice"] = f"發布前 30 分鐘 ({odt.strftime('%H:%M')} 起) 流動性急遽抽離，提防數據發布瞬間 50~150 點雙向劇烈刷洗！（發布日期：美國勞工統計局官方日程）"
            _kept.append(c)
        candidates = _kept

        if witching_d:
            candidates.append({
                "id": "us_quad_witching",
                "name": "美股四巫日 (Quadruple Witching Day)",
                "category": "跨國結算",
                "impact": "HIGH",
                "impact_label": "🔴 跨國衝擊",
                "pattern_type": "WINDOW_TIME",
                "warning_lead_hours": 24,
                "critical_lead_mins": 90,
                "target_epoch": int(witching_d.timestamp() * 1000),
                "date_display": witching_d.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": "美股四大衍生性商品(股指期貨/股指選擇權/個股期貨/個股選擇權)同時到期結算，尾盤爆量與美股夜盤波動同步放大，注意跨市場連動。"
            })

        if fomc_dt:
            candidates.append({
                "id": "fomc_rate_decision",
                "name": "聯準會 FOMC 利率決議",
                "category": "重磅總經",
                "impact": "HIGH",
                "impact_label": "🔴 波動爆發",
                "pattern_type": "POINT_TIME",
                "warning_lead_hours": 24,
                "critical_lead_mins": 120,
                "target_epoch": int(fomc_dt.timestamp() * 1000),
                "date_display": fomc_dt.strftime("%m/%d %H:%M (台灣時間)"),
                "gex_advice": f"發布前 30 分鐘 ({fomc_dt.strftime('%H:%M')} 起) 流動性急遽抽離，利率決議瞬間與隨後記者會期間提防台指期夜盤 50~200 點雙向劇烈刷洗！"
            })

        valid_events = [e for e in candidates if e["target_epoch"] >= int(curr_twd.timestamp() * 1000)]
        valid_events.sort(key=lambda x: x["target_epoch"])

        # 🌐 圖 1: 全球股市風險儀表板 (DXY, US10Y, VIX 即時報價)
        # Previously 100% hardcoded literals (including a 20-day EMA this pipeline never
        # actually computes) that never updated and disagreed with the real VIX fetched
        # elsewhere in this same file. DXY/US10Y are real Yahoo Finance quotes (same generic
        # fetcher used for ADR quotes); VIX reuses the real value already fetched above rather
        # than a third hardcoded copy. No fabricated "EMA20"/trend narrative — trend_label is
        # only a same-day real change direction, not a claimed technical indicator.
        dxy_quote = fetch_yahoo_finance_quote("DX-Y.NYB")
        us10y_quote = fetch_yahoo_finance_quote("%5ETNX")

        def _risk_entry(name, quote, unit=""):
            if not quote:
                return {"name": name, "price": None, "change_pct": None, "trend_label": "⚪ 無即時數據"}
            trend_label = f"{'▲ 較昨日走升' if quote['change_pct'] >= 0 else '▼ 較昨日走弱'} ({quote['change_pct']:+.2f}%)"
            return {"name": name, "price": quote['price'], "change_pct": quote['change_pct'], "trend_label": trend_label, "unit": unit}

        macro_risk_dashboard = {
            "summary": (f"台指VIX {latest_t_vix:.1f}、美股VIX {latest_u_vix:.1f}；" if (latest_t_vix is not None and latest_u_vix is not None) else "") +
                       "DXY/US10Y/VIX 即時報價僅供總經氛圍參考，非量化交易訊號。",
            "dxy": _risk_entry("美元指數 (DXY)", dxy_quote),
            "us10y": _risk_entry("美殖利率 (10年期 US10Y)", us10y_quote, unit="%"),
            "vix": {
                "name": "VIX恐慌指標 (CBOE)",
                "price": latest_u_vix,
                "trend_label": "⚪ 無即時數據" if latest_u_vix is None else ("🔴 恐慌偏高" if latest_u_vix >= 20 else "🟢 低波安定")
            }
        }

        # 📅 圖 2: 近期重要財經事件日曆 (Macro Economic Calendar)
        # Previously a hardcoded list of 5 events with specific 2026 dates that would silently
        # become a permanently empty table once the last of them passed (no error, no "no
        # data" message — just nothing, forever). `candidates`/`valid_events` above are
        # already real, calendar-arithmetic-derived, and extend indefinitely into the future
        # (weekly/monthly settlements, NFP, CPI, ADP, jobless claims) — reuse that list here
        # too instead of maintaining a second, separate, finite one.
        _impact_color_map = {"HIGH": "#ff5252", "MEDIUM": "#ffaa00", "LOW": "#26a69a"}
        _impact_label_map = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}
        macro_events_calendar = []
        for e in valid_events[:8]:
            ev_dt = datetime.datetime.fromtimestamp(e["target_epoch"] / 1000, tz=tw_tz)
            macro_events_calendar.append({
                "date": f"{ev_dt.month}/{ev_dt.day} {_WDAY_CN[ev_dt.weekday()]}",
                "event": e["name"],
                "focus": e["gex_advice"],
                "impact": _impact_label_map.get(e["impact"], e["impact"]),
                "impact_code": e["impact"],
                "impact_color": _impact_color_map.get(e["impact"], "#ffaa00")
            })

        return {
            "primary_event": valid_events[0] if valid_events else candidates[0],
            "upcoming_list": valid_events[:5],
            "macro_risk_dashboard": macro_risk_dashboard,
            "macro_events_calendar": macro_events_calendar
        }

    macro_events_data = calculate_macro_events_radar(now_dt)

    def generate_dynamic_weekly_focus(curr_twd):
        """
        方案 B：全自動對接期交所與國際財經日曆 API，動態生成「市場焦點週報」
        以每週一至週五為基準，自動識別重大總經事件與對應台股/美股期貨標的。
        """
        # 1. Check if user provided manual override JSON file
        override_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "weekly_focus_override.json")
        if os.path.exists(override_path):
            try:
                with open(override_path, "r", encoding="utf-8") as f:
                    ov = json.load(f)
                    if ov and "schedule" in ov:
                        return ov
            except Exception as e:
                print(f"[WeeklyFocus] Override read error: {e}")

        # 2. Compute current active trading week (Monday to Friday)
        wday = curr_twd.weekday()
        if wday >= 5:  # Saturday or Sunday: preview upcoming week
            days_to_next_mon = (7 - wday)
            mon = curr_twd + datetime.timedelta(days=days_to_next_mon)
        else:
            mon = curr_twd - datetime.timedelta(days=wday)

        tue = mon + datetime.timedelta(days=1)
        wed = mon + datetime.timedelta(days=2)
        thu = mon + datetime.timedelta(days=3)
        fri = mon + datetime.timedelta(days=4)

        date_range_str = f"{mon.strftime('%Y.%m.%d')} – {fri.strftime('%m.%d')}"

        # 3. 只放「有官方規則或官方公告可核對」的事項（2026-10-06 重寫）：
        #    - 台指週選／週五選／月選擇權結算日：期交所契約規格（每週三、每週五、每月第三個週三 13:30）
        #    - 臺灣證交所休市日：data/tw_holidays.json
        #    - FOMC 利率決議：聯準會官方日曆（fetch_fomc_meeting_dates）
        #    不再放美國經濟數據發布日與個別公司財報：以前這裡用「日期 ≤ 7 號就是 ISM」之類的推測字串，
        #    實際沒有接任何行事曆來源，卻標示「全自動對接國際財經日曆」，屬於憑空編造。
        fomc_by_date = {}
        try:
            for meeting in fetch_fomc_meeting_dates():
                d0 = meeting["rate_decision_date"]
                twd_hour = 2 if (3 < d0.month < 11) else 3     # 美東 14:00 → 台北隔日 02:00（夏令）／03:00（冬令）
                fomc_by_date[d0 + datetime.timedelta(days=1)] = twd_hour
        except Exception as e:
            print(f"[WeeklyFocus] FOMC calendar unavailable: {e}")

        try:
            with open(os.path.join(_DATA_DIR, "us_macro_calendar.json"), "r", encoding="utf-8") as _f:
                _us_cal = json.load(_f)
        except Exception:
            _us_cal = {}

        def day_events(d):
            dd = d.date() if hasattr(d, 'date') else d
            ev = []
            if not is_tw_trading_day(dd):
                ev.append("休市（臺灣證交所休市日／週末）" if dd.weekday() < 5 else "週末休市")
                return ev
            if dd.weekday() == 2:
                third = 15 <= dd.day <= 21
                ev.append("台指期貨／選擇權每月結算日（13:30）" if third else "台指週三選擇權結算（13:30）")
            if dd.weekday() == 4:
                ev.append("台指週五選擇權結算（13:30）")
            return ev

        schedule = []
        for label, d in (("週一", mon), ("週二", tue), ("週三", wed), ("週四", thu), ("週五", fri)):
            evs = day_events(d)
            dd = d.date() if hasattr(d, 'date') else d
            for _kind, _label in (("cpi", "美國 CPI"), ("empsit", "美國非農就業 (NFP) 與失業率")):
                for _it in _us_cal.get(_kind, []):
                    if _it["release_date"] == dd.isoformat():
                        evs.append(f"{_label}（美東 08:30，BLS 官方日程）")
            for fd, hh in fomc_by_date.items():
                if fd == dd:
                    evs.append(f"聯準會 FOMC 利率決議（台灣時間 {dd.strftime('%m/%d')} {hh:02d}:00，美東前一日 14:00）")
            schedule.append({"date": f"{d.strftime('%m/%d')} ({label})", "event": " ✕ ".join(evs) if evs else "無官方結算日或重大排程", "categories": []})

        return {
            "title": "本週市場日曆（期交所結算日／休市日／FOMC）",
            "source": "期交所契約規格、證交所休市日、聯準會官方日曆、美國勞工統計局官方日程（CPI／非農，data/us_macro_calendar.json）；不含 ADP 與個別公司財報（沒有官方來源）",
            "date_range": date_range_str,
            "theme": "",
            "schedule": schedule
        }

    # 觀察記錄（2026-10-06 使用者要求並排觀察「現行 Zero Gamma」「VEX 早鳥線」「標準 Gamma Flip」）：
    # 每輪引擎以「籌碼日」為鍵，覆寫該日最新一筆，累積成長期可回頭檢驗的紀錄（data/gex_line_observations.json）。
    try:
        _obs_path = os.path.join(_DATA_DIR, "gex_line_observations.json")
        try:
            with open(_obs_path, "r", encoding="utf-8") as _f:
                _obs = json.load(_f)
        except Exception:
            _obs = {}
        _obs[t0_date.strftime("%Y-%m-%d")] = {
            "updated": now_dt.strftime("%Y-%m-%d %H:%M"), "session": session_type, "engine": ENGINE_VERSION,
            "spot": spot_price, "txf_day": day_txf_price, "txf_night": night_txf_price,
            "zero_gamma_oi_boundary": gex_profile['zero_gamma_level'], "gex_plus_flip": gex_profile['gex_plus_flip'],
            "gamma_flip_standard": gex_profile.get('gamma_flip_standard'),
            "call_wall": gex_profile['call_wall_strike'], "put_wall": gex_profile['put_wall_strike'], "max_pain": gex_profile['max_pain_strike'],
            "taifex_vix": (fetch_official_taifex_vix() or {}).get("taifex_vix"), "sigma": _gex_sigma_info().get("sigma"),
        }
        with open(_obs_path, "w", encoding="utf-8") as _f:
            json.dump(dict(sorted(_obs.items())[-400:]), _f, ensure_ascii=False, indent=1)
    except Exception as _e:
        print(f"[Warning] gex_line_observations not written: {_e}")

    return {
        "date": today_str,
        "chip_base_date": t0_date.strftime("%Y-%m-%d"),  # the trading day the chip/OI data actually belongs to (today_str is the run date, e.g. a Saturday)
        "engine_version": ENGINE_VERSION,
        "session_type": session_type,
        "session_name": session_name,
        "session_shift": session_shift,
        "last_updated_time": now_dt.strftime("%Y-%m-%d %H:%M"),
        "spot_price": spot_price,
        "spot_change": spot_change,
        "spot_change_pct": spot_change_pct,
        "two_price": otc_price,
        "two_change": otc_change,
        "two_change_pct": otc_change_pct,
        "day_txf_price": day_txf_price,
        "night_txf_price": night_txf_price,
        "txf_price": txf_price,
        "zero_gamma_level": gex_profile['zero_gamma_level'],
        "gex_plus_flip": gex_profile['gex_plus_flip'],
        "gamma_flip_standard": gex_profile.get('gamma_flip_standard'),
        "call_wall_strike": gex_profile['call_wall_strike'],
        "put_wall_strike": gex_profile['put_wall_strike'],
        "max_pain_strike": gex_profile['max_pain_strike'],
        "opt_large_trader": opt_lt_inst,
        "pc_ratio": gex_profile['pc_ratio'],
        "total_gex": gex_profile['total_gex'],
        "weekly_gex": gex_profile['weekly_gex'],
        "friday_gex": gex_profile['friday_gex'],
        "monthly_gex": gex_profile['monthly_gex'],
        "history_10_sessions": history_10_sessions,
        "history_6_sessions": history_10_sessions[-6:],
        "dte_dates": dte_dates,
        "institutional_5day_history": institutional_5day_history,
        "night_institutional_5day_history": night_institutional_5day_history,
        "institutional_sentiment": institutional_sentiment,
        "executive_digest": executive_digest,
        "microstructure_summary": microstructure_summary,
        "hot_money_digest": hot_money_data,
        "night_institutional_trading": night_inst_trading,
        "retail_mini_ratio": retail_data["retail_mini_ratio"],
        "retail_micro_ratio": retail_data["retail_micro_ratio"],
        "retail_sentiment_details": retail_data["retail_sentiment_details"],
        "specific_traders": fetch_official_taifex_specific_traders(lt_inst, fut_inst),
        "total_vex": gex_profile['total_vex'],
        "total_gex_val": gex_profile['total_gex_val'],
        "total_gex_plus": gex_profile['total_gex_plus'],
        "sector_capital_rotation": sector_capital_rotation,
        "stock_futures": stock_futures,
        "ai_ex_dividend_digest": ai_ex_dividend_digest,
        "macro_events_radar": macro_events_data,
        "vix_info": fetch_official_taifex_vix(),
        "gex_model": _gex_sigma_info(),
        "fubon_weekly_focus": generate_dynamic_weekly_focus(now_dt)
    }

def main():
    print(f"=== Running TAIFEX Data Engine ({ENGINE_VERSION}) ===")
    data_obj = generate_gex_payload()
    plain_json_str = json.dumps(data_obj, ensure_ascii=False, indent=2)

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    raw_path = os.path.join(data_dir, "gex_data.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(plain_json_str)
    print(f"[OK] Saved raw JSON data to: {raw_path}")

    enc_payload = encrypt_payload_sha256(plain_json_str, PASSCODE)
    enc_obj = {
        "status": "encrypted",
        "algorithm": "AES-256-CBC-SHA256-XOR",
        "payload": enc_payload
    }
    enc_path = os.path.join(data_dir, "encrypted_gex.json")
    with open(enc_path, "w", encoding="utf-8") as f:
        json.dump(enc_obj, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved encrypted payload to: {enc_path}")

    js_path = os.path.join(data_dir, "embedded_data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.GEX_EMBEDDED_DATA = " + plain_json_str + ";\n")
    print(f"[OK] Saved embedded JS data to: {js_path}")

    # Generate 4K Bluebird Finder Social Infographic Card for IG & Threads
    try:
        from generate_social_card import generate_bluebird_social_card
        generate_bluebird_social_card(raw_path)
    except Exception as e:
        print(f"[Warning] Could not generate social card: {e}")

if __name__ == "__main__":
    main()
