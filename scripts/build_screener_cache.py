"""
build_screener_cache.py
======================
Generates `data/screener_cache.json` for the Multi-Factor Quant Screener (選股雷達).
Processes all universe symbols using real daily quotes from `data/tw_quotes_latest.json`
AND real ~60-trading-day OHLCV history fetched per symbol from TWSE/TPEx official daily
history endpoints (data/screener_ohlcv_cache.json caches it per calendar day so re-runs
the same day are instant). Computes Momentum Bird signals, real dual-layer MACD (JJ_MACD)
and CCI (JJ_CCI) states, 5K trends, DeMark indicators, and stock grades from that real
history.

`macd_state`/`macd_hist_growing`/`cci_value`/`cci_signal` (see compute_jj_macd_and_cci())
are a line-for-line port of the user's own JJ_MACD_Sub.pine and JJ_CCI_Sub.pine — real
EMA/CCI math, not an approximation — for symbols with >=35 real bars (2026-09-17). The
EMA/CCI formulas were cross-checked against the independently-authored Python `ta` library
on real TWSE 2330 data before being wired in (exact match to several decimals on MACD line/
signal/histogram and CCI for the last 8 trading days). The 🚀/🐦/5K/DeMark states below are
still simplified heuristic proxies (moving-average and recent-close comparisons), not a
literal reimplementation of those indicators' true formulas — tracked separately in
SELF_AUDIT_FINDINGS_TODO.md ("指標源碼逐一校正") and out of scope for this pass.
"""

import json
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
UNIVERSE_FILE = os.path.join(ROOT_DIR, "data", "tw_symbols_universe.json")
QUOTES_FILE = os.path.join(ROOT_DIR, "data", "tw_quotes_latest.json")
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "screener_cache.json")
OHLCV_CACHE_FILE = os.path.join(ROOT_DIR, "data", "screener_ohlcv_cache.json")
INST_HISTORY_FILE = os.path.join(ROOT_DIR, "data", "stock_institutional_history.json")
INST_HISTORY_TRADING_DAYS = 10

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def _fetch_url(url, retries=2):
    """Retry with escalating backoff — TWSE/TPEx rate-limit under a fast back-to-back batch of
    1000+ requests, and a bare failure would otherwise get silently recorded as
    history_unavailable even though the same URL fetches fine after backing off. A single
    quick retry (the first version of this fix) only recovered about a fifth of the failures
    (1210 -> 970 unavailable out of 1383), so the block outlasts a 1s wait for many of them —
    this uses longer, increasing waits instead of one short one."""
    last_err = None
    backoffs = [2.0, 5.0]
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=12) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoffs[min(attempt, len(backoffs) - 1)])
    raise last_err


def fetch_twse_stock_month(symbol, year, month):
    """One month of real daily OHLCV for a TWSE-listed symbol, or [] if unavailable."""
    date_str = f"{year:04d}{month:02d}01"
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={date_str}&stockNo={symbol}&response=json"
    try:
        data = json.loads(_fetch_url(url))
        if data.get('stat') != 'OK':
            return []
        bars = []
        for row in data.get('data', []):
            try:
                bars.append({
                    "open": float(row[3].replace(',', '')),
                    "high": float(row[4].replace(',', '')),
                    "low": float(row[5].replace(',', '')),
                    "close": float(row[6].replace(',', '')),
                    "volume": int(row[1].replace(',', '')) // 1000
                })
            except (ValueError, IndexError):
                continue
        return bars
    except Exception:
        return []


def fetch_tpex_stock_month(symbol, year, month):
    """One month of real daily OHLCV for a TPEx(OTC)-listed symbol, or [] if unavailable."""
    url = f"https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?code={symbol}&date={year:04d}%2F{month:02d}%2F01&id=&response=json"
    try:
        data = json.loads(_fetch_url(url))
        tables = data.get('tables', [])
        if not tables:
            return []
        bars = []
        for row in tables[0].get('data', []):
            try:
                bars.append({
                    "open": float(row[3].replace(',', '')),
                    "high": float(row[4].replace(',', '')),
                    "low": float(row[5].replace(',', '')),
                    "close": float(row[6].replace(',', '')),
                    "volume": int(row[1].replace(',', '')) // 1000
                })
            except (ValueError, IndexError):
                continue
        return bars
    except Exception:
        return []


def fetch_real_ohlcv_history(symbol, num_bars=60):
    """
    Real recent daily OHLCV for one symbol, newest last. Tries TWSE first (current month,
    walking back up to 6 months to gather enough bars), then TPEx the same way. Returns
    None (not a fabricated series) if neither official source has data for this symbol —
    e.g. a newly listed stock, an index/futures code that isn't an equity, or a delisted one.

    num_bars defaults to 60 (not 30): the real dual-layer MACD (see compute_jj_macd_and_cci())
    needs enough warm-up for its EMA26 to converge — at 30 bars the seed value (the first
    close in the window) still carries ~15% weight into today's EMA, at 60 bars that's down
    to ~1%, close enough to what a chart with its full history behind it would show.

    NOTE: this per-symbol path is now only the fallback for TPEx(OTC)-only stocks — see
    fetch_twse_all_stocks_day()/build_twse_bulk_history() below for the real fix to TWSE
    coverage (a single per-date bulk endpoint instead of 1 request per stock).
    """
    today = datetime.today()
    for fetch_month in (fetch_twse_stock_month, fetch_tpex_stock_month):
        collected = []
        y, m = today.year, today.month
        for _ in range(6):  # this month + up to 5 back, enough for ~60 trading days incl. short/holiday months
            collected = fetch_month(symbol, y, m) + collected
            if len(collected) >= num_bars:
                break
            m -= 1
            if m == 0:
                m, y = 12, y - 1
            time.sleep(0.12)
        if len(collected) >= 5:  # accept a short-but-real series over nothing; a few bars is still real
            return collected[-num_bars:]
    return None


def fetch_twse_all_stocks_day(date_str):
    """
    Real OHLCV for EVERY TWSE-listed stock on one date (YYYYMMDD), in a single request —
    confirmed against a live response that TWSE's MI_INDEX?type=ALLBUT0999 endpoint returns
    a ~1382-row "每股每日行情" table with every listed stock's open/high/low/close/volume for
    that day. This replaces the old design of one request per stock per month (1400+ requests,
    which TWSE/TPEx started rate-limiting hard) with ~20-25 requests total (one per trading
    day needed), each covering the whole market at once.
    Column layout verified against a live 2330 row: [0]代號 [1]名稱 [2]成交股數 [5]開盤價
    [6]最高價 [7]最低價 [8]收盤價. Returns {} on a non-trading day or fetch failure.
    """
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date_str}&type=ALLBUT0999&response=json"
    result = {}
    try:
        data = json.loads(_fetch_url(url))
        for t in data.get('tables', []):
            rows = t.get('data', [])
            if len(rows) > 500:  # the full per-stock table; other tables on this page are small summaries
                for row in rows:
                    try:
                        code = row[0].strip()
                        result[code] = {
                            "open": float(row[5].replace(',', '')),
                            "high": float(row[6].replace(',', '')),
                            "low": float(row[7].replace(',', '')),
                            "close": float(row[8].replace(',', '')),
                            "volume": int(row[2].replace(',', '')) // 1000
                        }
                    except (ValueError, IndexError):
                        continue
                break
    except Exception as e:
        print(f"  [WARN] TWSE bulk fetch failed for {date_str}: {e}")
    return result


def build_twse_bulk_history(num_trading_days=60, max_calendar_days_back=100):
    """
    Real ~num_trading_days of OHLCV for every TWSE-listed stock, built from
    fetch_twse_all_stocks_day() walking backward one calendar day at a time (skipping
    non-trading days, which come back empty and don't count against num_trading_days).
    Returns {code: [bars ascending by date]}.
    """
    history = {}
    day = datetime.today().date()
    collected = 0
    tried = 0
    while collected < num_trading_days and tried < max_calendar_days_back:
        date_str = day.strftime('%Y%m%d')
        day_data = fetch_twse_all_stocks_day(date_str)
        if day_data:
            for code, bar in day_data.items():
                history.setdefault(code, []).append(bar)
            collected += 1
            if collected % 5 == 0:
                print(f"  ...TWSE bulk history: {collected}/{num_trading_days} trading days collected")
            time.sleep(0.3)
        tried += 1
        day -= timedelta(days=1)
    for code in history:
        history[code].reverse()  # walked backward, so newest-first -> reverse to oldest-first
    print(f"[OK] TWSE bulk history built: {collected} trading days x {len(history)} stocks (~{tried} calendar days scanned)")
    return history


def fetch_twse_t86_for_date(date_str):
    """
    Real per-stock 三大法人買賣超 (TWSE T86) for one date (YYYYMMDD), or {} if the market was
    closed or that date isn't published yet. Minimal standalone copy of the same parse already
    used by scripts/fetch_and_calc_vision.py's fetch_twse_institutional_t86() — duplicated
    (not imported) so this script stays independently runnable without pulling in that much
    larger module's own top-level behavior. Column layout: [0]證券代號
    [4]外陸資買賣超(不含外資自營商) [7]外資自營商買賣超 [10]投信買賣超 [11]自營商買賣超(合計).
    """
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
    result = {}
    try:
        data = json.loads(_fetch_url(url))
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
                "foreign": foreign_net,
                "trust": trust_net,
                "dealer": dealer_net,
                "total": foreign_net + trust_net + dealer_net,
            }
    except Exception as e:
        print(f"  [WARN] TWSE T86 fetch failed for {date_str}: {e}")
    return result


def load_inst_history():
    try:
        with open(INST_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_inst_history(history):
    with open(INST_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)


def update_inst_history(num_trading_days=INST_HISTORY_TRADING_DAYS, max_calendar_days_back=25):
    """
    Ensures data/stock_institutional_history.json has real per-stock T86 snapshots for the
    most recent `num_trading_days` trading days, keyed by ISO date. Walks backward from today
    one calendar day at a time (skipping non-trading days, which come back empty), fetching
    only the dates not already cached — so this is a no-op single-file-read most days once the
    window is full, not a full re-backfill every run. Also prunes dates older than the window
    so this file doesn't grow forever.
    """
    history = load_inst_history()
    day = datetime.today().date()
    collected_dates = []
    tried = 0
    while len(collected_dates) < num_trading_days and tried < max_calendar_days_back:
        date_iso = day.isoformat()
        if date_iso in history:
            collected_dates.append(date_iso)
        else:
            day_data = fetch_twse_t86_for_date(day.strftime('%Y%m%d'))
            if day_data:
                history[date_iso] = day_data
                collected_dates.append(date_iso)
                time.sleep(0.3)
        tried += 1
        day -= timedelta(days=1)
    # Prune anything outside the window so the file doesn't grow unbounded.
    keep = set(collected_dates)
    for k in list(history.keys()):
        if k not in keep:
            del history[k]
    save_inst_history(history)
    print(f"[OK] Stock institutional T86 history: {len(collected_dates)}/{num_trading_days} trading days on file")
    return history


def compute_inst_flags(symbol, inst_history):
    """
    Real 投信認養 (investment-trust adoption) / 籌碼偏多 (institutionally bullish) flags from
    inst_history (date_iso -> {code: {foreign, trust, dealer, total}}), newest date last once
    sorted. Adoption = trust net-buy on 3+ consecutive most-recent trading days (the common
    practitioner definition). Chip-bullish = the combined foreign+trust+dealer net was
    positive on at least 2 of the most recent 3 trading days. Returns (it_consec_days,
    is_it_adopted, chip_bull) — honestly False/0 when fewer than 3 real days exist yet for
    this symbol, never guessed.
    """
    dates_desc = sorted(inst_history.keys(), reverse=True)
    it_consec_days = 0
    for d in dates_desc:
        row = inst_history[d].get(symbol)
        if row is None or row.get("trust", 0) <= 0:
            break
        it_consec_days += 1

    recent3 = [inst_history[d].get(symbol) for d in dates_desc[:3]]
    recent3 = [r for r in recent3 if r is not None]
    chip_bull = len(recent3) >= 3 and sum(1 for r in recent3 if r.get("total", 0) > 0) >= 2

    is_it_adopted = it_consec_days >= 3
    return it_consec_days, is_it_adopted, chip_bull


def _ema_series(values, length):
    """Standard exponential moving average, seeded with the first value — matches Pine
    Script's ta.ema() (and the independently-authored `ta` Python library, cross-checked
    against real TWSE data before this was wired in)."""
    alpha = 2.0 / (length + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def _sma_series(values, length):
    out = []
    for i in range(len(values)):
        window = values[max(0, i + 1 - length):i + 1]
        out.append(sum(window) / len(window))
    return out


def _mean_dev_series(values, length):
    """Rolling mean ABSOLUTE deviation — matches Pine Script's ta.dev(), which despite the
    similar name is not the standard deviation. CCI is defined using this, not stdev."""
    out = []
    for i in range(len(values)):
        window = values[max(0, i + 1 - length):i + 1]
        m = sum(window) / len(window)
        out.append(sum(abs(x - m) for x in window) / len(window))
    return out


def compute_jj_macd_and_cci(bars):
    """
    Real dual-layer MACD + CCI, ported line-for-line from the user's own JJ_MACD_Sub.pine and
    JJ_CCI_Sub.pine (C:\\Users\\mingi\\OneDrive\\文件\\TradingView 指標\\我寫的指標\\JJ 指標復刻優化\\).

    JJ_MACD's whole point: a standard main MACD(12,26,9) sets the histogram's HEIGHT, but a
    faster sub MACD(3,15,5) sets its COLOR — the sub layer can flip bullish (macd_sub > 0)
    while the main histogram is still underwater, giving an earlier heads-up than a plain
    single-layer MACD would ("水下出現紅色柱體" in the original Pine comments). Requires
    >=35 bars for both EMA26 (main) and EMA15 (sub) to have meaningfully converged.

    JJ_CCI is CCI(20) on hlc3 using Pine's ta.dev() (mean absolute deviation, not stdev), with
    buy/sell markers on crossing ±100/±200 — collapsed here to a single most-extreme label
    since this feeds one JSON field rather than four independent chart markers.

    Returns (macd_state, hist_growing, cci_value, cci_signal).
    """
    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    hlc3 = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]

    ema12, ema26 = _ema_series(closes, 12), _ema_series(closes, 26)
    macd_main = [a - b for a, b in zip(ema12, ema26)]
    signal_main = _ema_series(macd_main, 9)
    hist_main = [a - b for a, b in zip(macd_main, signal_main)]

    ema3, ema15 = _ema_series(closes, 3), _ema_series(closes, 15)
    macd_sub = [a - b for a, b in zip(ema3, ema15)]
    signal_sub = _ema_series(macd_sub, 5)
    hist_sub = [a - b for a, b in zip(macd_sub, signal_sub)]

    is_up = macd_sub[-1] > 0
    was_up = macd_sub[-2] > 0
    momentum_up = hist_sub[-1] > hist_sub[-2]

    if is_up and momentum_up:
        # JJ's color_up_pos (紅) — sub-MACD bullish AND accelerating: genuine confirmed
        # bullish momentum. "零軸上"/"水下" distinguishes by the MAIN histogram's own sign,
        # exactly like the original heuristic this replaces.
        macd_state = "零軸上金叉" if hist_main[-1] > 0 else "MACD 水下金叉"
    elif is_up and not was_up:
        # Sub-MACD just crossed bullish this bar — JJ's signature early flip, before the
        # main MACD histogram necessarily confirms it.
        macd_state = "MACD 柱狀體翻紅"
    else:
        macd_state = "死叉觀望"

    hist_growing = hist_main[-1] > hist_main[-2] and hist_main[-1] > 0

    cci_sma = _sma_series(hlc3, 20)
    cci_dev = _mean_dev_series(hlc3, 20)
    cci = [(h - s) / (0.015 * d) if d > 0 else 0.0 for h, s, d in zip(hlc3, cci_sma, cci_dev)]

    cci_signal = None
    if cci[-2] <= -200 < cci[-1]:
        cci_signal = "🔴 急殺超賣反彈(穿越-200)"
    elif cci[-2] <= 200 < cci[-1]:
        cci_signal = "🟢 極端過熱(穿越+200)"
    elif cci[-2] <= -100 < cci[-1]:
        cci_signal = "🔴 轉強買點(穿越-100)"
    elif cci[-2] <= 100 < cci[-1]:
        cci_signal = "🟢 過熱賣點(穿越+100)"

    return macd_state, hist_growing, round(cci[-1], 1), cci_signal


def load_ohlcv_cache():
    try:
        with open(OHLCV_CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("_date") == datetime.today().strftime("%Y-%m-%d"):
            return cache.get("data", {})
    except Exception:
        pass
    return {}


def save_ohlcv_cache(data):
    with open(OHLCV_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"_date": datetime.today().strftime("%Y-%m-%d"), "data": data}, f, ensure_ascii=False)


def compute_symbol_metrics(item, quote, bars, inst_history):
    symbol = str(item.get("symbol", ""))
    name = item.get("name", symbol)
    market = item.get("market", "TWSE")
    category = item.get("category", "其他")
    asset_type = item.get("asset_type", "stock")

    close = quote.get("close", 0.0)
    open_p = quote.get("open", close)
    high_p = quote.get("high", close)
    low_p = quote.get("low", close)
    pct_change = quote.get("pct_change", 0.0)
    change = quote.get("change", 0.0)
    volume = quote.get("volume", 0)
    amount = quote.get("amount", 0)

    it_consec_days, is_it_adopted, chip_bull = compute_inst_flags(symbol, inst_history)

    base = {
        "symbol": symbol, "name": name, "market": market, "category": category,
        "asset_type": asset_type, "price": close, "open": open_p, "high": high_p,
        "low": low_p, "change": change, "pct_change": pct_change, "volume": volume,
        "amount": amount, "it_consec_days": it_consec_days, "it_adopted": is_it_adopted,
        "chip_bull": chip_bull
    }

    if not bars or len(bars) < 5:
        # No real history available for this symbol (e.g. a futures/index code, or newly
        # listed) — report it honestly instead of inventing a signal from fake history.
        # it_adopted/chip_bull are independent of price history, so they still carry through.
        return {
            **base, "bias_pct": None, "vol_ratio": None, "grade": None, "signals": [],
            "macd_state": None, "macd_hist_growing": False, "cci_value": None,
            "cci_signal": None, "k5_state": None, "demark_state": None,
            "volume_status": None, "score": 0, "history_unavailable": True
        }

    # Ensure the series ends at today's real quote (the fetched history may lag by a day
    # depending on when this script runs relative to TWSE/TPEx publishing today's bar).
    if close > 0 and (not bars or abs(bars[-1]["close"] - close) > 0.001):
        bars = bars + [{"open": open_p, "high": high_p, "low": low_p, "close": close, "volume": volume}]

    closes = [b["close"] for b in bars]
    vols = [b["volume"] for b in bars]

    ma20 = sum(closes[-20:]) / len(closes[-20:]) if len(closes) >= 2 else close
    ma5 = sum(closes[-5:]) / len(closes[-5:]) if len(closes) >= 2 else close
    avg_vol_5 = sum(vols[-5:]) / len(vols[-5:]) if len(vols) >= 2 else (volume or 1)

    bias_pct = round(((close - ma20) / ma20 * 100.0), 2) if ma20 > 0 else 0.0
    vol_ratio = round((vols[-1] / avg_vol_5), 2) if avg_vol_5 > 0 else 1.0

    signals = []
    if pct_change >= 2.5 and vol_ratio >= 1.5 and close > ma5:
        signals.append("🚀 強火箭")
    if bias_pct >= 4.0 and pct_change > 1.0 and close > ma20:
        signals.append("🐦 強力藍鳥")
    if vol_ratio >= 2.0 and pct_change >= 3.0:
        signals.append("🛸 動能飛碟")
    if close > ma5 and ma5 > ma20 and pct_change > 0.5:
        signals.append("⚡ 動能閃電")
    if vol_ratio >= 2.2 and len(closes) >= 10 and high_p >= max(closes[-10:]):
        signals.append("✈️ 噴射機")
    if abs(bias_pct) <= 1.5 and vol_ratio <= 0.8:
        signals.append("🥚 帶殼鳥")

    if len(closes) >= 35:
        macd_state, macd_hist_growing, cci_value, cci_signal = compute_jj_macd_and_cci(bars)
    else:
        # Too little real history for a converged EMA26/EMA15 (new listing, thin history) —
        # keep the old price/MA proxy for these edge cases rather than serving an
        # unconverged, unreliable "real" number under the same field name.
        if close > ma20 and pct_change > 0:
            macd_state = "零軸上金叉" if bias_pct > 3.0 else "MACD 水下金叉"
        elif pct_change > 0:
            macd_state = "MACD 柱狀體翻紅"
        else:
            macd_state = "死叉觀望"
        macd_hist_growing, cci_value, cci_signal = False, None, None

    if len(closes) >= 5 and close >= max(closes[-5:]):
        k5_state = "5K 創高突破"
    elif close > ma5 and ma5 > ma20:
        k5_state = "5K 多頭發散"
    elif close > ma20:
        k5_state = "5K 站上 20MA"
    else:
        k5_state = "5K 跌破 20MA"

    demark_state = "無"
    if len(closes) >= 9:
        if all(closes[i] > closes[i - 4] for i in range(-4, 0)):
            demark_state = "DeMark 9★ 買盤竭盡"
        elif all(closes[i] < closes[i - 4] for i in range(-4, 0)):
            demark_state = "DeMark 13★ 轉折點"

    if vol_ratio >= 2.0:
        vol_status = "爆量 (2.0x+)"
    elif vol_ratio >= 1.5:
        vol_status = "放量 (1.5x+)"
    elif vol_ratio >= 0.8:
        vol_status = "溫和量 (1.0x)"
    else:
        vol_status = "縮量 (<0.8x)"

    score = 0
    if "🚀 強火箭" in signals: score += 30
    if "🐦 強力藍鳥" in signals: score += 25
    if "🛸 動能飛碟" in signals: score += 25
    if "⚡ 動能閃電" in signals: score += 15
    if macd_state in ["零軸上金叉", "MACD 水下金叉"]: score += 20
    if macd_hist_growing: score += 10
    if cci_signal and cci_signal.startswith("🔴"): score += 10
    if k5_state in ["5K 創高突破", "5K 多頭發散"]: score += 15
    if pct_change > 0: score += int(pct_change * 5)

    if score >= 60:
        grade = "S"
    elif score >= 35:
        grade = "A"
    elif score >= 15:
        grade = "B"
    else:
        grade = "C"

    return {
        **base, "bias_pct": bias_pct, "vol_ratio": vol_ratio, "grade": grade,
        "signals": signals, "macd_state": macd_state, "macd_hist_growing": macd_hist_growing,
        "cci_value": cci_value, "cci_signal": cci_signal, "k5_state": k5_state,
        "demark_state": demark_state, "volume_status": vol_status, "score": score,
        "history_unavailable": False
    }


def main():
    print(f"=== Building Quant Screener Cache [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===")

    if not os.path.exists(UNIVERSE_FILE) or not os.path.exists(QUOTES_FILE):
        print("Missing universe or quotes file!")
        return

    with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
        universe = json.load(f)

    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        quotes_data = json.load(f).get("quotes", {})

    ohlcv_cache = load_ohlcv_cache()
    cache_dirty = False

    # Real per-stock 三大法人買賣超 history for 投信認養/籌碼偏多 — self-maintaining rolling
    # window (see update_inst_history), independent of the OHLCV cache above.
    inst_history = update_inst_history()

    # Real TWSE-wide history via the bulk per-date endpoint — covers the large majority of
    # the universe (TWSE-listed stocks) in ~20-25 requests instead of one per stock. Reused
    # from today's cache when already fetched today (keyed under "_TWSE_BULK").
    if "_TWSE_BULK" in ohlcv_cache:
        twse_bulk = ohlcv_cache["_TWSE_BULK"]
        print(f"[OK] TWSE bulk history: using today's cache ({len(twse_bulk)} stocks)")
    else:
        twse_bulk = build_twse_bulk_history()
        ohlcv_cache["_TWSE_BULK"] = twse_bulk
        cache_dirty = True
        save_ohlcv_cache(ohlcv_cache)

    results = []
    print(f"Processing {len(universe)} symbols (TWSE bulk history + per-symbol TPEx fallback)...")

    bulk_hits, fetched, cached_hits, unavailable = 0, 0, 0, 0
    for i, item in enumerate(universe):
        sym = str(item.get("symbol", ""))
        quote = quotes_data.get(sym, {})
        asset_type = item.get("asset_type", "stock")

        if asset_type in ("index_futures", "stock_futures"):
            # Not an equity — TWSE/TPEx daily history doesn't apply.
            bars = None
        elif sym in twse_bulk and len(twse_bulk[sym]) >= 5:
            bars = twse_bulk[sym]
            bulk_hits += 1
        elif sym in ohlcv_cache:
            bars = ohlcv_cache[sym]
            cached_hits += 1
        else:
            # TPEx(OTC)-only stocks, or anything the TWSE bulk table didn't include —
            # fall back to the slower per-symbol fetch (paced to avoid the rate-limit that
            # a fast 1400-request batch triggered before).
            bars = fetch_real_ohlcv_history(sym)
            ohlcv_cache[sym] = bars if bars else []
            cache_dirty = True
            fetched += 1
            time.sleep(0.6)
            if fetched % 50 == 0:
                print(f"  ...fetched real history for {fetched} fallback symbols so far ({i + 1}/{len(universe)} processed)")
                save_ohlcv_cache(ohlcv_cache)  # checkpoint periodically in case of interruption

        if not bars:
            unavailable += 1
        metrics = compute_symbol_metrics(item, quote, bars, inst_history)
        results.append(metrics)

    if cache_dirty:
        save_ohlcv_cache(ohlcv_cache)

    print(f"Real history: {bulk_hits} from TWSE bulk, {fetched} freshly fetched (TPEx/fallback), "
          f"{cached_hits} from today's per-symbol cache, {unavailable} unavailable (no fake fallback).")

    results.sort(key=lambda x: x["score"], reverse=True)

    cache = {
        "last_update": datetime.now().isoformat(),
        "total_symbols": len(results),
        "history_unavailable_count": unavailable,
        "s_grade_count": sum(1 for x in results if x["grade"] == "S"),
        "a_grade_count": sum(1 for x in results if x["grade"] == "A"),
        "symbols": results
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"=== Screener cache successfully built! Saved {len(results)} symbols to {OUTPUT_FILE} ===")

    huaxin = next((x for x in results if x["symbol"] == "1605"), None)
    if huaxin:
        print("\n[VERIFICATION] 1605 (華新) Screener Cache:")
        print(json.dumps(huaxin, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
