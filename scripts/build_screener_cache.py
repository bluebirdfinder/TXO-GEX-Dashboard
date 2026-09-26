"""
build_screener_cache.py
======================
Generates `data/screener_cache.json` for the Multi-Factor Quant Screener (選股雷達).
Processes all universe symbols using real daily quotes from `data/tw_quotes_latest.json`
AND real ~120-trading-day OHLCV history fetched per symbol from TWSE/TPEx official daily
history endpoints (data/screener_ohlcv_cache.json caches it per calendar day so re-runs
the same day are instant). Computes real dual-layer MACD (JJ_MACD)/CCI (JJ_CCI)/rocket-bird
(JJ鬼爪V4.1)/5K breakout/DeMark Sequential (神奇九轉) states, plus a few still-heuristic
signals and stock grades, from that history.

Real, line-for-line Pine ports (2026-09-17/18/24), each verified against the
independently-authored Python `ta` library on real TWSE 2330 data before being wired in:
  - `macd_state`/`macd_hist_growing`/`cci_value`/`cci_signal` — compute_jj_macd_and_cci(),
    from JJ_MACD_Sub.pine/JJ_CCI_Sub.pine, symbols with >=35 real bars.
  - 🚀強火箭/🐦強力藍鳥/✈️火箭/🐣藍鳥 in `signals` — compute_jj_rocket_and_bird(), from
    ghost_claws_v4.1.pine, symbols with >=89 real bars (a true SMA88 needs that many, no
    approximation exists). NOTE: ✈️火箭 here is the REAL JJ鬼爪 weak-rocket state and is a
    different signal from the heuristic ✈️噴射機 below despite sharing the plane emoji — the
    two are visually distinguished by their trailing text, not the emoji alone.
  - 📐真5K突破 in `signals` — compute_5k_breakout(), from 5K_Strategy_Master_v5.pine's entry
    logic only (no stop-loss/take-profit — a daily scan has no open position to manage), a
    DIFFERENT concept from the pre-existing `k5_state` heuristic below (see that function's
    docstring). Symbols with >=60 real bars.
  - `demark_buy_state`/`demark_sell_state` — compute_demark_v3(), a full port of
    demark_sequential_v3_equities.pine (Setup/Countdown state machine + all 7 filters),
    a NEW, separate pair of fields from the pre-existing `demark_state` heuristic below (see
    that function's docstring for why). Symbols with >=65 real bars.

🛸動能飛碟/⚡動能閃電/✈️噴射機/🥚帶殼鳥 in `signals`, `k5_state`, and `demark_state` are still
simplified heuristic proxies (moving-average and recent-close comparisons), not a literal
reimplementation of those indicators' true formulas — tracked separately in
SELF_AUDIT_FINDINGS_TODO.md ("指標源碼逐一校正") and out of scope for this pass. (✈️火箭 is a
different, real signal from ✈️噴射機 — see the note above.)
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
BULK_LATEST_DATE = None  # YYYYMMDD of the newest trading day in the TWSE bulk history (set at build/load time)

SSL_CTX = ssl.create_default_context()
# Full certificate-chain + hostname verification stays ON. TWSE/TPEx certificates lack a Subject Key
# Identifier, which Python 3.13's strict X.509 flag rejects, so only that one flag is relaxed.
SSL_CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT
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


def fetch_real_ohlcv_history(symbol, num_bars=120):
    """
    Real recent daily OHLCV for one symbol, newest last. Tries TWSE first (current month,
    walking back up to 10 months to gather enough bars), then TPEx the same way. Returns
    None (not a fabricated series) if neither official source has data for this symbol —
    e.g. a newly listed stock, an index/futures code that isn't an equity, or a delisted one.

    num_bars defaults to 120, not 60: compute_jj_rocket_and_bird() (JJ鬼爪's real 🚀強火箭/
    🐦強力藍鳥) needs a true SMA88 — unlike an EMA, an 88-day simple moving average literally
    cannot be computed from fewer than 88 real closes, there is no "approximation" available,
    and its crossover check (今天 vs 昨天) needs that SMA88 at two consecutive bars, so the
    hard floor is 89 bars. 120 leaves comfortable margin and also improves the dual-layer
    MACD's EMA26 convergence further (residual seed weight ~0.01% vs ~1% at 60 bars).

    NOTE: this per-symbol path is now only the fallback for TPEx(OTC)-only stocks — see
    fetch_twse_all_stocks_day()/build_twse_bulk_history() below for the real fix to TWSE
    coverage (a single per-date bulk endpoint instead of 1 request per stock).
    """
    today = datetime.today()
    for fetch_month in (fetch_twse_stock_month, fetch_tpex_stock_month):
        collected = []
        y, m = today.year, today.month
        for _ in range(10):  # this month + up to 9 back, enough for ~120 trading days incl. short/holiday months
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
    [6]最高價 [7]最低價 [8]收盤價. Returns {} for a genuinely empty answer (non-trading day: the
    request succeeded but carries no per-stock table) and None when the request itself FAILED
    (HTTP error such as TWSE's WAF 307, timeout, unparseable body) — the two must never be
    conflated: a failed trading day silently treated as a holiday drops one bar from every
    stock's history (found 2026-09-26: 2026-04-10 and 2026-05-11 vanished this way).
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
        return None
    return result


def build_twse_bulk_history(num_trading_days=120, max_calendar_days_back=180):
    """
    Real ~num_trading_days of OHLCV for every TWSE-listed stock, built from
    fetch_twse_all_stocks_day() walking backward one calendar day at a time (skipping
    non-trading days, which come back empty and don't count against num_trading_days).
    Returns {code: [bars ascending by date]}.
    """
    global BULK_LATEST_DATE
    history = {}
    day = datetime.today().date()
    collected = 0
    tried = 0
    while collected < num_trading_days and tried < max_calendar_days_back:
        date_str = day.strftime('%Y%m%d')
        day_data = fetch_twse_all_stocks_day(date_str)
        # None = the request failed (rate limit / WAF), NOT a holiday. Back off and retry; a day
        # that still fails after all retries aborts the whole build so a history with a silent
        # hole is never written as if it were complete.
        for wait in (15, 45, 90):
            if day_data is not None:
                break
            print(f"  [RETRY] {date_str}: waiting {wait}s before retrying TWSE bulk fetch")
            time.sleep(wait)
            day_data = fetch_twse_all_stocks_day(date_str)
        if day_data is None:
            raise RuntimeError(
                f"TWSE bulk history: {date_str} still failing after retries — refusing to build a "
                f"history with a possibly-missing trading day. Wait a few minutes (WAF cooldown) and rerun; "
                f"do not run other TWSE-hitting scripts at the same time.")
        if day_data:
            if collected == 0:
                BULK_LATEST_DATE = date_str  # first success walking backward = newest trading day
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


def _mfi_series(highs, lows, closes, volumes, length=14):
    """Money Flow Index — matches Pine's ta.mfi(hlc3, length) and the independently-authored
    `ta` Python library's MFIIndicator (verified against real TWSE 2330 data)."""
    tp = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]
    out = [50.0]
    for i in range(1, len(tp)):
        start = max(1, i - length + 1)
        pos = neg = 0.0
        for k in range(start, i + 1):
            rmf = tp[k] * volumes[k]
            if tp[k] > tp[k - 1]:
                pos += rmf
            elif tp[k] < tp[k - 1]:
                neg += rmf
        out.append(100.0 if neg == 0 else 100 - 100 / (1 + pos / neg))
    return out


def compute_jj_rocket_and_bird(bars):
    """
    Real 🚀強火箭/🐦強力藍鳥/✈️弱火箭/🐣一般藍鳥, ported line-for-line from the user's own
    ghost_claws_v4.1.pine (JJ鬼爪V4.1 — same indicator already live on the Cloudflare Worker
    for the trading room's own momentum HUD), using its "台股個股與一般ETF" auto-parameter
    branch: bias_neg=8.0, mfi_thresh=52.0. Screener's 🚀強火箭/🐦強力藍鳥/✈️弱火箭/🐣一般藍鳥
    map exactly to JJ鬼爪's is_strong_rocket/is_strong_bird/is_weak_rocket/is_normal_bird (same
    emoji, same Chinese name, matching the markers already drawn in
    scripts/tv_indicators_engine.py's own port of the same script). The stateful
    🛸強力再啟/⚡動能再啟 signals (which require replaying is_holding across the ENTIRE bar
    history, not just the last two bars) are still out of scope for this pass — screener's
    existing 🛸動能飛碟/⚡動能閃電/✈️噴射機/🥚帶殼鳥 heuristics are untouched.

    Pine definitions (ghost_claws_v4.1.pine):
      cond_bird   = crossover(hist, 0) and (ma17 > ma88) and (close > bb_basis)
      is_strong_bird   = cond_bird and bias88 <= -8.0
      is_normal_bird   = cond_bird and bias88 >  -8.0
      cond_rocket = crossover(ma17, ma88) and hist > 0
      is_strong_rocket = cond_rocket and mfi > 52.0
      is_weak_rocket   = cond_rocket and mfi <= 52.0

    Requires >=89 real bars: an 88-day SMA has no "approximation" the way an EMA does — it is
    simply undefined below 88 real closes, and the crossover check needs it at two consecutive
    bars. Returns (is_strong_rocket, is_strong_bird, is_weak_rocket, is_normal_bird) —
    False x4 if not computable.
    """
    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    volumes = [b["volume"] for b in bars]

    ma7 = _sma_series(closes, 7)
    ma17 = _sma_series(closes, 17)
    ma88 = _sma_series(closes, 88)
    bb_basis = _sma_series(closes, 20)
    bias88 = (closes[-1] - ma88[-1]) / ma88[-1] * 100.0 if ma88[-1] else 0.0

    ema12, ema26 = _ema_series(closes, 12), _ema_series(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal_line = _ema_series(macd_line, 9)
    hist = [a - b for a, b in zip(macd_line, signal_line)]

    mfi = _mfi_series(highs, lows, closes, volumes, 14)

    is_bull_trend = ma17[-1] > ma88[-1]
    is_above_bb = closes[-1] > bb_basis[-1]

    cond_bird = (hist[-2] <= 0 < hist[-1]) and is_bull_trend and is_above_bb
    is_strong_bird = cond_bird and bias88 <= -8.0
    is_normal_bird = cond_bird and bias88 > -8.0

    cond_rocket = (ma17[-2] <= ma88[-2]) and (ma17[-1] > ma88[-1]) and hist[-1] > 0
    is_strong_rocket = cond_rocket and mfi[-1] > 52.0
    is_weak_rocket = cond_rocket and mfi[-1] <= 52.0

    return is_strong_rocket, is_strong_bird, is_weak_rocket, is_normal_bird


def _twse_tick_size(price):
    """TWSE's official variable tick size by price band (not a fixed `syminfo.mintick` the
    way a future has) — needed for compute_5k_breakout()'s buffer_val."""
    if price < 10:
        return 0.01
    if price < 50:
        return 0.05
    if price < 100:
        return 0.1
    if price < 500:
        return 0.5
    if price < 1000:
        return 1.0
    return 5.0


def _atr_series(highs, lows, closes, length):
    """Wilder RMA-smoothed Average True Range — matches Pine's ta.atr() (verified against the
    independently-authored `ta` Python library on real TWSE 2330 data)."""
    tr = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    out = [tr[0]]
    for i in range(1, len(tr)):
        out.append((out[-1] * (length - 1) + tr[i]) / length)
    return out


def compute_5k_breakout(bars):
    """
    Real "5K突破" entry trigger, ported from the user's own 5K_Strategy_Master_v5.pine —
    entry logic ONLY (2026-09-24, by explicit user decision): no stop-loss/take-profit/MTF
    exit scaling, since those manage an already-open position and a daily screener scan has
    no notion of one. This is a DIFFERENT concept from the pre-existing `k5_state` heuristic
    ("5K創高突破" = new 5-day closing high) — the real 5K戰法 is a reversal pattern: a sharp
    drop, a confirmed local bottom, then a breakout back above that bottom bar's high.

    Pine logic (long side only — short/breakdown state is still tracked internally because
    the setup-invalidation rule below depends on it):
      is_pivot_low   = low[1] < low[0] and low[1] < low[2]   (bar[1] confirmed a local low)
      price_drop     = highest(high[1], 48) - low[1]
      -> if is_pivot_low and price_drop > atr_val[1] * 1.5: a new low-setup is armed
         (a same-direction setup already valid for >final_setup_age_limit bars back is NOT
         cleared by this — only an OPPOSING new setup within that many bars clears it, exactly
         mirroring the Pine "防雙刷壓制" rule)
      is_breakout    = an armed low-setup exists AND close > (that setup's high + 1 tick)
      long_entry     = is_breakout and close>open (bullish candle) and close in upper half of
                       today's own range; consumes (clears) the low-setup so it can't refire
                       off the same setup tomorrow

    Parameter provenance: 5K_Strategy_Master_v5.pine's auto-detect table (`asset_class`) has
    branches for index/commodity/forex/crypto futures only — an individual TW stock matches
    none of them, so `asset_class` stays "Unknown" and `is_auto_active` is false, meaning the
    script's own MANUAL/default inputs apply, not a stock-tuned branch (unlike JJ鬼爪, which
    has an explicit "台股個股與一般ETF" branch). Values used here are exactly those manual
    defaults: atr_len=5, atr_mult=1.5, lookback=48, setup_age_limit=10 (daily bars — the
    auto-table's own daily fallback is 3, but that branch never activates for a stock),
    buffer=1 tick (TWSE's real variable tick size by price band, not a fixed futures tick),
    ma_fast/slow=17/88, trend filter on (17MA>88MA required), trade_dir="Both" default.
    This is disclosed here, not silently assumed, because it means the formula is running
    with the script's generic fallback parameters, not ones the user calibrated for stocks.

    `pos_long == 0` (Pine's "only one position open at a time" gate) is deliberately dropped
    here — with no exit logic to ever flip it back to 0, keeping that gate would let at most
    ONE breakout ever fire across the entire lookback window. The setup-consumption-on-entry
    rule (clearing is_valid_low_setup the day it fires) already prevents the same setup from
    re-triggering, so dropping the position gate does not create infinite re-firing.

    Requires >=50 real bars (48-bar lookback + a few bars of runway). Returns True/False for
    whether a fresh breakout fired on the LAST bar.
    """
    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    opens = [b["open"] for b in bars]
    n = len(bars)

    atr = _atr_series(highs, lows, closes, 5)
    ma_fast = _sma_series(closes, 17)
    ma_slow = _sma_series(closes, 88)

    lookback = 48
    setup_age_limit = 10
    atr_mult = 1.5

    valid_low = valid_high = False
    low_bar_high = low_bar_idx = None
    high_bar_low = high_bar_idx = None
    breakout_today = False

    for i in range(2, n):
        is_pivot_low = lows[i - 1] < lows[i] and lows[i - 1] < lows[i - 2]
        is_pivot_high = highs[i - 1] > highs[i] and highs[i - 1] > highs[i - 2]

        if is_pivot_low:
            window = highs[max(0, i - lookback):i]
            highest_recent = max(window) if window else highs[i - 1]
            price_drop = highest_recent - lows[i - 1]
            if price_drop > atr[i - 1] * atr_mult:
                low_bar_high, low_bar_idx = highs[i - 1], i - 1
                valid_low = True
                if valid_high and (i - high_bar_idx <= setup_age_limit):
                    valid_high = False

        if is_pivot_high:
            window = lows[max(0, i - lookback):i]
            lowest_recent = min(window) if window else lows[i - 1]
            price_surge = highs[i - 1] - lowest_recent
            if price_surge > atr[i - 1] * atr_mult:
                high_bar_low, high_bar_idx = lows[i - 1], i - 1
                valid_high = True
                if valid_low and (i - low_bar_idx <= setup_age_limit):
                    valid_low = False

        buffer_val = _twse_tick_size(closes[i])
        is_bull_trend = ma_fast[i] > ma_slow[i]
        is_breakout = valid_low and closes[i] > (low_bar_high + buffer_val)
        is_bullish_candle = closes[i] > opens[i]
        is_upper_half = closes[i] > (highs[i] + lows[i]) / 2.0

        breakout_today = False
        if is_bull_trend and is_breakout and is_bullish_candle and is_upper_half:
            breakout_today = (i == n - 1)
            valid_low = False

    return breakout_today


def _rsi_series(closes, length=14):
    """Wilder-smoothed RSI — matches Pine's ta.rsi() (verified against the `ta` library)."""
    gains, losses = [0.0], [0.0]
    for i in range(1, len(closes)):
        chg = closes[i] - closes[i - 1]
        gains.append(max(chg, 0.0))
        losses.append(max(-chg, 0.0))

    def rma(vals, n):
        out = [vals[0]]
        for v in vals[1:]:
            out.append((out[-1] * (n - 1) + v) / n)
        return out

    avg_gain, avg_loss = rma(gains, length), rma(losses, length)
    out = []
    for g, l in zip(avg_gain, avg_loss):
        out.append(100.0 if l == 0 else 100 - 100 / (1 + g / l))
    return out


def _stoch_series(highs, lows, closes, length=9, smooth=3):
    """%K/%D stochastic — matches Pine's ta.stoch()+ta.sma() (verified against `ta` library)."""
    k = []
    for i in range(len(closes)):
        w = range(max(0, i + 1 - length), i + 1)
        hh, ll = max(highs[j] for j in w), min(lows[j] for j in w)
        k.append(100 * (closes[i] - ll) / (hh - ll) if hh != ll else 50.0)
    d = _sma_series(k, smooth)
    return k, d


def compute_demark_v3(bars):
    """
    Real 神奇九轉 (DeMark Sequential), ported from the user's own
    demark_sequential_v3_equities.pine ("個股專武版" — the version calibrated for stocks;
    v4 only has commodities/forex/indices branches, per DeMark_Version_History.md, equities
    was deliberately left on v3). Full port including the "七大過濾器武器庫" (2026-09-24, by
    explicit user decision), running with the script's own shipped default preset — situation
    mode "🔄 通用版 (均衡)" (its default input value): Volume(20d, 1.2x) + BB/KC Squeeze active
    as 1~3 entry-label filters, MA(60)/MACD/AO filters off, RSI/KD/ATR filters off (all four
    are input.bool(false,...) defaults in the source and are NOT overridden by situation mode,
    which only touches the Group-1 filters). RSI overbought/oversold + divergence are still
    computed unconditionally either way — they feed the 9↗/9↘/13★/13↘ Unicode states in
    Section 4 of the Pine source regardless of the cfg_rsi toggle (that toggle is declared but
    never actually wired into any gate in this version of the script — verified by reading
    every reference to it, not assumed).

    Setup phase: b_cnt/s_cnt count consecutive closes below/above close 4 bars back (TD Setup);
    completes at 9. Perfection (b_perf/s_perf) requires the count-8-or-9 extreme to exceed the
    count-6/7 extremes. Countdown phase (bc/sc) starts on Setup completion, advances on bars
    where close<=low[2] (buy side) / close>=high[2] (sell side), up to 13, with the "8 vs 5"
    and "13 vs 8" qualifying-bar rules, a TDST-breakout cancellation rule, an opposing-Setup
    cancellation rule, and a Recycle reset at count 22 to avoid a stale Countdown lingering
    through an extended one-way trend.

    Returns (buy_state, sell_state), each one of None/"1"/"2"/"3"/"7"/"8"/"9"/"9★"/"9↗"/"13"/
    "13★"/"13↘" for TODAY (buy_state from a declining move exhausting into a bottom, sell_state
    from a rally exhausting into a top — both computed independently, not mutually exclusive
    across different days, and 1/2/3 additionally require passing the entry filters above).
    """
    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    volumes = [b["volume"] for b in bars]
    n = len(bars)

    rsi = _rsi_series(closes, 14)
    k, d = _stoch_series(highs, lows, closes, 9, 3)
    ema12, ema26 = _ema_series(closes, 12), _ema_series(closes, 26)
    macd_line = [a - b_ for a, b_ in zip(ema12, ema26)]
    macd_sig = _ema_series(macd_line, 9)
    hl2 = [(h + l) / 2.0 for h, l in zip(highs, lows)]
    ao = [a - b_ for a, b_ in zip(_sma_series(hl2, 5), _sma_series(hl2, 34))]
    ma60 = _sma_series(closes, 60)
    vol_avg20 = _sma_series(volumes, 20)
    atr14 = _atr_series(highs, lows, closes, 14)
    bb_basis = _sma_series(closes, 20)
    # BB uses real stdev here, unlike JJ_CCI's mean-absolute-deviation:
    bb_stdev = []
    for i in range(n):
        w = closes[max(0, i - 19):i + 1]
        m = sum(w) / len(w)
        bb_stdev.append((sum((x - m) ** 2 for x in w) / len(w)) ** 0.5)
    bb_upper = [basis + 2.0 * sd for basis, sd in zip(bb_basis, bb_stdev)]
    bb_lower = [basis - 2.0 * sd for basis, sd in zip(bb_basis, bb_stdev)]
    kc_upper = [basis + 1.5 * a for basis, a in zip(bb_basis, atr14)]
    kc_lower = [basis - 1.5 * a for basis, a in zip(bb_basis, atr14)]

    # 通用版 preset (script's own default input values): Vol 20d/1.2x + Squeeze on;
    # MA/MACD/AO/RSI/KD off — all 5 wired below regardless, so a future preset change is a
    # one-line edit, not a re-port.
    CFG_VOL, CFG_VOL_M = True, 1.2
    CFG_SQZ = True
    CFG_MA = CFG_MACD = CFG_AO = CFG_KD = False

    var_b_cnt = var_s_cnt = 0
    b_maxH = s_minL = None
    bl6 = bl7 = bl8 = sh6 = sh7 = sh8 = None
    bc = sc = 0
    bc_on = sc_on = False
    bc_tdst = sc_tdst = None
    bc_cl5 = bc_cl8 = sc_cl5 = sc_cl8 = None
    bc_recyd = sc_recyd = False

    buy_state = sell_state = None

    for i in range(4, n):
        b_cond = closes[i] < closes[i - 4]
        s_cond = closes[i] > closes[i - 4]
        b_cond_prev = closes[i - 1] < closes[i - 5] if i >= 5 else False
        s_cond_prev = closes[i - 1] > closes[i - 5] if i >= 5 else False
        b_flip = b_cond and not b_cond_prev
        s_flip = s_cond and not s_cond_prev

        var_b_cnt = (1 if b_flip else (var_b_cnt + 1 if var_b_cnt > 0 else 0)) if b_cond else 0
        var_s_cnt = (1 if s_flip else (var_s_cnt + 1 if var_s_cnt > 0 else 0)) if s_cond else 0

        b_maxH = (highs[i] if var_b_cnt == 1 else max(b_maxH, highs[i])) if var_b_cnt > 0 else None
        s_minL = (lows[i] if var_s_cnt == 1 else min(s_minL, lows[i])) if var_s_cnt > 0 else None

        if var_b_cnt == 6: bl6 = lows[i]
        if var_b_cnt == 7: bl7 = lows[i]
        if var_b_cnt == 8: bl8 = lows[i]
        if var_s_cnt == 6: sh6 = highs[i]
        if var_s_cnt == 7: sh7 = highs[i]
        if var_s_cnt == 8: sh8 = highs[i]

        b_done = var_b_cnt == 9
        s_done = var_s_cnt == 9
        b_perf = b_done and None not in (bl6, bl7, bl8) and min(bl8, lows[i]) < min(bl6, bl7)
        s_perf = s_done and None not in (sh6, sh7, sh8) and max(sh8, highs[i]) > max(sh6, sh7)

        # --- Countdown cancellation (TDST breakout / opposing Setup) ---
        if bc_on and ((bc_tdst is not None and highs[i] > bc_tdst) or s_done):
            bc_on, bc, bc_cl5, bc_cl8 = False, 0, None, None
        if sc_on and ((sc_tdst is not None and lows[i] < sc_tdst) or b_done):
            sc_on, sc, sc_cl5, sc_cl8 = False, 0, None, None

        if b_done and not bc_on:
            bc_on, bc, bc_recyd = True, 0, False
            bc_tdst = b_maxH if b_maxH is not None else highs[i]
            bc_cl5 = bc_cl8 = None
        if s_done and not sc_on:
            sc_on, sc, sc_recyd = True, 0, False
            sc_tdst = s_minL if s_minL is not None else lows[i]
            sc_cl5 = sc_cl8 = None

        if bc_on and var_b_cnt == 22:
            bc, bc_recyd = 0, True
            bc_tdst = b_maxH if b_maxH is not None else highs[i]
            bc_cl5 = bc_cl8 = None
        if sc_on and var_s_cnt == 22:
            sc, sc_recyd = 0, True
            sc_tdst = s_minL if s_minL is not None else lows[i]
            sc_cl5 = sc_cl8 = None

        bc_bar = closes[i] <= lows[i - 2] if i >= 2 else False
        sc_bar = closes[i] >= highs[i - 2] if i >= 2 else False
        if bc_on and bc_bar and bc < 13 and not b_done:
            if bc == 7:
                if lows[i] < (bc_cl5 if bc_cl5 is not None else highs[i]):
                    bc, bc_cl8 = 8, closes[i]
            elif bc == 12:
                if lows[i] <= (bc_cl8 if bc_cl8 is not None else highs[i]):
                    bc = 13
            else:
                bc += 1
                if bc == 5: bc_cl5 = closes[i]
                if bc == 8: bc_cl8 = closes[i]

        if sc_on and sc_bar and sc < 13 and not s_done:
            if sc == 7:
                if highs[i] > (sc_cl5 if sc_cl5 is not None else lows[i]):
                    sc, sc_cl8 = 8, closes[i]
            elif sc == 12:
                if highs[i] >= (sc_cl8 if sc_cl8 is not None else lows[i]):
                    sc = 13
            else:
                sc += 1
                if sc == 5: sc_cl5 = closes[i]
                if sc == 8: sc_cl8 = closes[i]

        bc_comp = bc_on and bc == 13
        sc_comp = sc_on and sc == 13
        if bc_comp: bc_on = False
        if sc_comp: sc_on = False

        # --- Section 2: entry filters (1~3 labels) + Section 4: display states ---
        is_vol_break = volumes[i] > vol_avg20[i] * CFG_VOL_M
        is_squeeze = bb_upper[i] < kc_upper[i] and bb_lower[i] > kc_lower[i]
        is_ma_up_now = i >= 5 and ma60[i] > ma60[i - 5]
        is_ma_dn_now = i >= 5 and ma60[i] < ma60[i - 5]
        is_macd_bear, is_macd_bull = macd_line[i] < macd_sig[i], macd_line[i] > macd_sig[i]
        is_ao_bear, is_ao_bull = ao[i] < 0, ao[i] > 0

        pass_f1_buy = True
        if CFG_VOL and not is_vol_break: pass_f1_buy = False
        if CFG_SQZ and is_squeeze: pass_f1_buy = False
        if CFG_MA and not is_ma_up_now: pass_f1_buy = False
        if CFG_MACD and not is_macd_bear: pass_f1_buy = False
        if CFG_AO and not is_ao_bear: pass_f1_buy = False

        pass_f1_sell = True
        if CFG_VOL and not is_vol_break: pass_f1_sell = False
        if CFG_SQZ and is_squeeze: pass_f1_sell = False
        if CFG_MA and not is_ma_dn_now: pass_f1_sell = False
        if CFG_MACD and not is_macd_bull: pass_f1_sell = False
        if CFG_AO and not is_ao_bull: pass_f1_sell = False

        is_rsi_ob, is_rsi_os = rsi[i] >= 75, rsi[i] <= 25
        price_hh = closes[i] > (max(closes[max(0, i - 20):i]) if i >= 1 else closes[i])
        rsi_lh = rsi[i] < (max(rsi[max(0, i - 20):i]) if i >= 1 else rsi[i])
        is_bear_div = price_hh and rsi_lh
        price_ll = closes[i] < (min(closes[max(0, i - 20):i]) if i >= 1 else closes[i])
        rsi_hl = rsi[i] > (min(rsi[max(0, i - 20):i]) if i >= 1 else rsi[i])
        is_bull_div = price_ll and rsi_hl

        is_kd_cross_up = i > 0 and k[i - 1] <= d[i - 1] and k[i] > d[i] and k[i] < 30
        is_kd_cross_dn = i > 0 and k[i - 1] >= d[i - 1] and k[i] < d[i] and k[i] > 70
        block_b_exhaust = CFG_KD and not is_kd_cross_up
        block_s_exhaust = CFG_KD and not is_kd_cross_dn

        buy_state = None
        if not block_b_exhaust:
            if bc_comp and not bc_recyd:
                buy_state = "13★" if is_bull_div else ("13↘" if is_rsi_os else "13")
            elif b_done:
                buy_state = "9★" if b_perf else ("9↗" if is_ma_up_now else "9")
            elif var_b_cnt in (7, 8):
                buy_state = str(var_b_cnt)
            elif var_b_cnt in (1, 2, 3) and pass_f1_buy:
                buy_state = str(var_b_cnt)

        sell_state = None
        if not block_s_exhaust:
            if sc_comp and not sc_recyd:
                sell_state = "13★" if is_bear_div else ("13↗" if is_rsi_ob else "13")
            elif s_done:
                sell_state = "9★" if s_perf else ("9↘" if is_ma_dn_now else "9")
            elif var_s_cnt in (7, 8):
                sell_state = str(var_s_cnt)
            elif var_s_cnt in (1, 2, 3) and pass_f1_sell:
                sell_state = str(var_s_cnt)

    return buy_state, sell_state


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


def _normalize_quote_date(raw):
    """tw_quotes_latest.json mixes ROC dates ('1150924', TWSE/TPEx OpenAPI) and Gregorian
    ('20260924', TAIFEX). Return YYYYMMDD, or '' if unrecognised (never appended as a bar)."""
    d = str(raw or "").strip().replace("/", "").replace("-", "")
    if len(d) == 7 and d.isdigit():
        return str(int(d[:3]) + 1911) + d[3:]
    if len(d) == 8 and d.isdigit():
        return d
    return ""


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
            "demark_buy_state": None, "demark_sell_state": None,
            "volume_status": None, "score": 0, "history_unavailable": True
        }

    # Ensure the series ends at today's real quote (the fetched history may lag by a day
    # depending on when this script runs relative to TWSE/TPEx publishing today's bar).
    # Only append a quote that is verifiably NEWER than the newest bar in the history. Found
    # 2026-09-26: data/tw_quotes_latest.json was 17 days stale (2026-09-09) and the old
    # "close differs -> append" rule tacked that stale quote onto every stock's series as a fake
    # newest bar, corrupting every indicator. A quote with no/older date is never appended.
    quote_date = _normalize_quote_date(quote.get("date"))
    if (close > 0 and BULK_LATEST_DATE and quote_date > BULK_LATEST_DATE
            and (not bars or abs(bars[-1]["close"] - close) > 0.001)):
        bars = bars + [{"open": open_p, "high": high_p, "low": low_p, "close": close, "volume": volume}]

    closes = [b["close"] for b in bars]
    vols = [b["volume"] for b in bars]

    ma20 = sum(closes[-20:]) / len(closes[-20:]) if len(closes) >= 2 else close
    ma5 = sum(closes[-5:]) / len(closes[-5:]) if len(closes) >= 2 else close
    avg_vol_5 = sum(vols[-5:]) / len(vols[-5:]) if len(vols) >= 2 else (volume or 1)

    bias_pct = round(((close - ma20) / ma20 * 100.0), 2) if ma20 > 0 else 0.0
    vol_ratio = round((vols[-1] / avg_vol_5), 2) if avg_vol_5 > 0 else 1.0

    signals = []
    if len(closes) >= 89:
        # Real JJ鬼爪V4.1 is_strong_rocket/is_strong_bird/is_weak_rocket/is_normal_bird
        # (compute_jj_rocket_and_bird()) — replaces the price/volume-ratio proxy below for
        # symbols with enough history for a true SMA88 (see that function's docstring for why
        # 89 is a hard floor, not a tuning choice). Thinner-history symbols keep the old
        # heuristic so they still get a signal rather than none at all.
        is_strong_rocket, is_strong_bird, is_weak_rocket, is_normal_bird = compute_jj_rocket_and_bird(bars)
        if is_strong_rocket:
            signals.append("🚀 強火箭")
        elif is_weak_rocket:
            signals.append("✈️ 火箭")
        if is_strong_bird:
            signals.append("🐦 強力藍鳥")
        elif is_normal_bird:
            signals.append("🐣 藍鳥")
    else:
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

    # Real "5K突破" (5K_Strategy_Master_v5.pine entry-trigger only — see compute_5k_breakout()
    # docstring). Deliberately a NEW, separate signal rather than overwriting k5_state's
    # existing "5K創高突破" below: that heuristic means "made a new 5-day closing high" (trend
    # continuation), while the real 5K戰法 is a different concept (sharp drop -> confirmed
    # local bottom -> breakout back above it, a reversal pattern) — conflating the two under
    # one label would misrepresent both.
    if len(closes) >= 60 and compute_5k_breakout(bars):
        signals.append("📐 真5K突破")

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

    # Real 神奇九轉 (compute_demark_v3() — full Setup/Countdown state machine + 7-weapon filter
    # library, ported from demark_sequential_v3_equities.pine). A NEW, separate pair of fields
    # rather than replacing demark_state above: the old field conflates "buy-side" and
    # "sell-side" exhaustion into one string with no directionality, which the real DeMark
    # engine does not — it tracks a decline exhausting into a bottom (buy) and a rally
    # exhausting into a top (sell) as two independent tracks that can each be active.
    demark_buy_state = demark_sell_state = None
    if len(closes) >= 65:
        demark_buy_state, demark_sell_state = compute_demark_v3(bars)

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
    if "📐 真5K突破" in signals: score += 20
    if demark_buy_state in ("9★", "9↗", "13★"): score += 15
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
        "demark_state": demark_state, "demark_buy_state": demark_buy_state,
        "demark_sell_state": demark_sell_state, "volume_status": vol_status, "score": score,
        "history_unavailable": False
    }


def main():
    global BULK_LATEST_DATE
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
        BULK_LATEST_DATE = ohlcv_cache.get("_TWSE_BULK_LATEST")
        print(f"[OK] TWSE bulk history: using today's cache ({len(twse_bulk)} stocks)")
    else:
        twse_bulk = build_twse_bulk_history()
        ohlcv_cache["_TWSE_BULK"] = twse_bulk
        ohlcv_cache["_TWSE_BULK_LATEST"] = BULK_LATEST_DATE
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
