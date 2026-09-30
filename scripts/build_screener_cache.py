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
  - all 8 JJ鬼爪V4.1 signals (🚀強火箭 🐦強力藍鳥 ✈️火箭 🐣藍鳥 🛸強力再啟 ⚡動能再啟 💰減碼 ⚠️出清) in
    `signals` — scripts/jj_ghost_claws.py, a 1:1 port of the user's own "JJ Indicator V4.1 - Ghost
    Claws Master" Pine (pasted 2026-09-27), symbols with >=89 real bars (a true SMA88 needs that many;
    below that NO JJ signal is produced — no proxy). ADX/MFI/EMA follow Pine's ta.* semantics; the
    再啟/減碼/出清 state machine replays over the ~120 available bars, so it may differ from
    TradingView's much longer replay.
  - 📐真5K突破 in `signals` — compute_5k_breakout(), from 5K_Strategy_Master_v5.pine's entry
    logic only (no stop-loss/take-profit — a daily scan has no open position to manage), a
    DIFFERENT concept from the pre-existing `k5_state` heuristic below (see that function's
    docstring). Symbols with >=60 real bars.
  - `demark_buy_state`/`demark_sell_state` — compute_demark_v3(), a full port of
    demark_sequential_v3_equities.pine (Setup/Countdown state machine + all 7 filters),
    a NEW, separate pair of fields from the pre-existing `demark_state` heuristic below (see
    that function's docstring for why). Symbols with >=65 real bars.

`k5_state` and `demark_state` are still simplified heuristic proxies (moving-average and recent-close
comparisons), not a literal reimplementation of those indicators' true formulas — tracked separately in
SELF_AUDIT_FINDINGS_TODO.md ("指標源碼逐一校正"). The old heuristic signals 🛸動能飛碟/⚡動能閃電/✈️噴射機/🥚帶殼鳥
were removed: they were rough stand-ins for 🛸強力再啟/⚡動能再啟/✈️弱火箭/🐣一般藍鳥, which are now real.
"""

import json
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 動能鳥／個人指標運算（JJ MACD+CCI、真5K突破、神奇九轉 DeMark v3、8 訊號）已搬到使用者私有資料夾，
# 不放在公開 repo。路徑由環境變數 TXO_PRIVATE_INDICATORS 指定，預設如下。找不到時明確報錯，不靜默失敗。
# ---------------------------------------------------------------------------
_PRIVATE_DIR = os.environ.get("TXO_PRIVATE_INDICATORS", r"C:\Users\mingi\txo-private\screener-indicators")
if not os.path.isfile(os.path.join(_PRIVATE_DIR, "screener_indicators.py")):
    sys.exit("❌ 找不到私有指標模組：" + os.path.join(_PRIVATE_DIR, "screener_indicators.py") + "\n"
             "   選股雷達的動能鳥／5K／九轉運算放在私有資料夾（不在 git）。請確認路徑，或設定環境變數 TXO_PRIVATE_INDICATORS。")
sys.path.insert(0, _PRIVATE_DIR)
import jj_ghost_claws as jj  # noqa: E402  (私有)
from screener_indicators import compute_jj_macd_and_cci, compute_5k_breakout, compute_demark_v3  # noqa: E402  (私有)

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


def _roc_to_yyyymmdd(text):
    """'115/09/01' (民國年/月/日，TPEx 有時尾巴帶星號) -> '20260901'; None when unparseable."""
    try:
        y, m, d = str(text).replace('*', '').strip().split('/')
        return f"{int(y) + 1911:04d}{int(m):02d}{int(d):02d}"
    except (ValueError, AttributeError):
        return None


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
                    "date": _roc_to_yyyymmdd(row[0]),
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
                    "date": _roc_to_yyyymmdd(row[0]),
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

    num_bars defaults to 120, not 60: jj_ghost_claws.py (JJ鬼爪's real 🚀強火箭/
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
                history.setdefault(code, []).append(dict(bar, date=date_str))  # 帶日期：有停牌／新上市的股票 K 棒數較少，不能用位置推日期
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
    jj_last = None
    if len(closes) >= 89:
        # All 8 JJ鬼爪V4.1 signals from scripts/jj_ghost_claws.py (line-by-line port of the user's Pine; the state-machine
        # ones — 再啟/減碼/出清 — replay is_holding over the whole ~120-bar history, so they can differ from TradingView's
        # longer replay). Per-asset auto thresholds follow the Pine `asset_class` router (ETF suffix L/R/U/A/B).
        # A symbol with < 89 real bars gets NO JJ signal (a true SMA88 does not exist) — no proxy substitute any more.
        jj_last = jj.compute_jj_last(bars, jj.jj_params(symbol, asset_type))
    if jj_last:
        if jj_last["strong_rocket"]:
            signals.append("🚀 強火箭")
        elif jj_last["weak_rocket"]:
            signals.append("✈️ 火箭")
        if jj_last["strong_bird"]:
            signals.append("🐦 強力藍鳥")
        elif jj_last["normal_bird"]:
            signals.append("🐣 藍鳥")
        if jj_last["restart_strong"]:
            signals.append("🛸 強力再啟")
        elif jj_last["restart_normal"]:
            signals.append("⚡ 動能再啟")
        if jj_last["reduce"]:
            signals.append("💰 減碼")
        if jj_last["exit"]:
            signals.append("⚠️ 出清")

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
    if "🛸 強力再啟" in signals: score += 25
    if "⚡ 動能再啟" in signals: score += 15
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
        "signals": signals,
        "jj_grade": jj_last["grade"] if jj_last else None,  # JJ強度 S/A/B/C (Pine strength_grade)
        "jj_adx": round(jj_last["adx"], 1) if jj_last and jj_last.get("adx") is not None else None,
        "macd_state": macd_state, "macd_hist_growing": macd_hist_growing,
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
