"""
backfill_snapshots.py - One-time historical snapshot seeder
Uses TAIFEX/TWSE historical APIs to populate session_snapshots.json
with real spot/txf/vix/pc_ratio for past N trading days.
GEX fields (zero_gamma etc.) are now also real: TAIFEX's 選擇權每日交易行情下載
(optDataDown) publishes real per-strike TXO open interest for a date range in one request,
so each historical day gets calculate_true_gex_profile() run against that day's own real
open interest and real spot price, instead of the null placeholder this file used to leave
in place (real backfill needs it, and now it's actually available).
"""
import os, sys, json, ssl, datetime, urllib.request, time
sys.stdout.reconfigure(encoding="utf-8")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR   = os.path.join(os.path.dirname(_SCRIPT_DIR), "data")
SNAPSHOT_FILE    = os.path.join(_DATA_DIR, "session_snapshots.json")
TW_HOLIDAYS_FILE = os.path.join(_DATA_DIR, "tw_holidays.json")

sys.path.insert(0, _SCRIPT_DIR)
from fetch_and_calc_vision import (
    fetch_taifex_txo_open_interest, classify_txo_contract_buckets,
    build_real_option_chain, calculate_true_gex_profile, compute_days_to_expiries,
    fetch_official_taifex_pc_ratio
)

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent": "Mozilla/5.0"}

def _load_tw_holidays():
    try:
        with open(TW_HOLIDAYS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).get("holidays", []))
    except Exception:
        return set()

TW_HOLIDAYS = _load_tw_holidays()

def is_tw_trading_day(d):
    if d.weekday() >= 5: return False
    if d.strftime("%Y-%m-%d") in TW_HOLIDAYS: return False
    return True

def get_past_tw_trading_days(n):
    today = datetime.date.today()
    days, curr = [], today
    while len(days) < n:
        if is_tw_trading_day(curr): days.append(curr)
        curr -= datetime.timedelta(days=1)
    return days

def load_snapshots():
    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_snapshots(snaps):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snaps, f, ensure_ascii=False, indent=2)

def fetch_url(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as r:
            raw = r.read()
        try: return raw.decode("utf-8")
        except Exception: return raw.decode("big5", errors="replace")
    except Exception as e:
        print(f"  [WARN] {url[:70]}: {e}")
        return None

def fetch_taifex_daily_tx(date_str):
    """
    Fetch TX (front-month 臺股期貨) day/night closing from TAIFEX's official 期貨每日交易行情
    下載 (futDataDown) for one date (YYYYMMDD). Confirmed against a live response that this
    endpoint needs queryStartDate/queryEndDate (YYYY/MM/DD) — Date_From/Date_To (the params
    this function used before) return a "DateTime error" page instead of data, so this always
    silently returned (None, None). Column layout (decoded as cp950, not utf-8/big5):
    [0]交易日期 [1]契約 [2]到期月份(週別) [6]收盤價 [17]交易時段(一般/盤後).
    """
    y, m, d = date_str[:4], date_str[4:6], date_str[6:]
    slash_date = f"{y}/{m}/{d}"
    url = f"https://www.taifex.com.tw/cht/3/futDataDown?down_type=1&commodity_id=TX&queryStartDate={slash_date}&queryEndDate={slash_date}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=12) as r:
            raw = r.read()
        text = raw.decode("cp950", errors="ignore")
    except Exception as e:
        print(f"  [WARN] futDataDown {date_str}: {e}")
        return None, None

    day_close = night_close = None
    front_month = None
    for line in text.split("\n"):
        if not line.strip():
            continue
        cols = [c.strip() for c in line.split(",")]
        if len(cols) < 18 or cols[0] != slash_date:
            continue
        contract_code = cols[2]
        if front_month is None:
            front_month = contract_code  # rows are listed nearest-month first
        if contract_code != front_month:
            continue
        try:
            close_val = float(cols[6].replace(",", ""))
        except ValueError:
            continue
        if cols[17] == '一般' and day_close is None:
            day_close = close_val
        elif cols[17] == '盤後' and night_close is None:
            night_close = close_val
    return day_close, night_close

_pc_ratio_cache = None

def fetch_taifex_pc_ratio(date_str):
    """
    PC ratio for date YYYYMMDD, via fetch_and_calc_vision's fetch_official_taifex_pc_ratio()
    (the old callPutRatioHis URL this used to hit 404s — TAIFEX moved it to /cht/3/pcRatio,
    already correctly handled there). That function returns a dict keyed like "2026/9/11" (no
    zero-padding), fetched once and reused across this backfill's date range.
    """
    global _pc_ratio_cache
    if _pc_ratio_cache is None:
        _pc_ratio_cache = fetch_official_taifex_pc_ratio()
    y, m, d = date_str[:4], date_str[4:6], date_str[6:]
    key = f"{y}/{int(m)}/{int(d)}"
    return _pc_ratio_cache.get(key)

def fetch_twse_index(date_str):
    """
    Fetch TWSE TAIEX closing for date YYYYMMDD. type=IND is the 價格指數 table — type=MS (the
    original value here) returns market-breadth statistics that don't include this row at all,
    and even a row that did match would need column [1] (收盤指數), not [-1] (a trailing
    處理註記 column that's usually empty) — both bugs confirmed against a live response.
    """
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date_str}&type=IND&response=json"
    txt = fetch_url(url)
    if not txt: return None
    try:
        data = json.loads(txt)
        for tbl in data.get("tables",[]):
            for row in tbl.get("data",[]):
                if len(row) > 1 and "發行量加權股價指數" in str(row[0]):
                    try: return float(str(row[1]).replace(",",""))
                    except Exception: pass
    except Exception: pass
    return None

def backfill(n_days=10, overwrite=False):
    trading_days = get_past_tw_trading_days(n_days)
    snapshots = load_snapshots()
    print(f"Backfilling {n_days} trading days...")

    # Real TXO open interest for the whole window in ONE request (TAIFEX allows date ranges),
    # keyed by ISO date -> {contract_code: {"expiry":.., "call":{strike:oi}, "put":{strike:oi}}}
    tw_tz = datetime.timezone(datetime.timedelta(hours=8))
    range_start = trading_days[-1].strftime("%Y/%m/%d")
    range_end = trading_days[0].strftime("%Y/%m/%d")
    txo_oi_by_date = fetch_taifex_txo_open_interest(range_start, range_end)

    written = 0
    for day in trading_days:
        date_str = day.strftime("%Y%m%d")
        iso_str  = day.strftime("%Y-%m-%d")

        day_oi = txo_oi_by_date.get(iso_str)
        gex_profile_by_price = {}  # memoize per spot price so DAY/NIGHT sharing a price don't recompute
        if day_oi:
            buckets = classify_txo_contract_buckets(day_oi)
            real_chain = build_real_option_chain(day_oi, buckets)
            ref_dt = datetime.datetime(day.year, day.month, day.day, 13, 30, tzinfo=tw_tz)  # TXO settles 13:30
            days_wed, days_fri, days_mth, _ = compute_days_to_expiries(ref_dt, tw_tz)

            def real_gex_fields(price):
                if price is None or price <= 0:
                    return None
                if price not in gex_profile_by_price:
                    gex_profile_by_price[price] = calculate_true_gex_profile(price, real_chain, days_wed, days_fri, days_mth)
                p = gex_profile_by_price[price]
                return {
                    "zero_gamma_level": p["zero_gamma_level"], "gex_plus_flip": p["gex_plus_flip"],
                    "call_wall_strike": p["call_wall_strike"], "put_wall_strike": p["put_wall_strike"],
                    "max_pain_strike": p["max_pain_strike"]
                }
        else:
            def real_gex_fields(price):
                return None
            print(f"  [WARN] No real TXO open interest for {iso_str} — GEX fields stay null (not guessed).")

        for sess in ["DAY", "NIGHT"]:
            key = f"{iso_str}_{sess}"
            if key in snapshots and not overwrite:
                print(f"  SKIP {key}")
                continue
            print(f"  Fetching {key}...", end=" ")
            spot = fetch_twse_index(date_str)
            day_txf, night_txf = fetch_taifex_daily_tx(date_str)
            pc_ratio = fetch_taifex_pc_ratio(date_str)
            txf = day_txf if sess == "DAY" else night_txf

            gex_fields = real_gex_fields(txf) or real_gex_fields(spot) or {
                "zero_gamma_level": None, "gex_plus_flip": None,
                "call_wall_strike": None, "put_wall_strike": None, "max_pain_strike": None
            }

            snapshots[key] = {
                "date": iso_str, "session": sess,
                "spot_price": spot, "otc_price": None, "txf_price": txf,
                **gex_fields,
                "pc_ratio": pc_ratio, "taifex_vix": None, "us_vix": None,
                "margin_maint_market": None, "margin_maint_stock": None,
                "written_at": f"{iso_str}T23:59:00+08:00", "source": "backfill"
            }
            print(f"spot={spot}, txf={txf}, pc={pc_ratio}, zero_gamma={gex_fields['zero_gamma_level']}")
            written += 1
            time.sleep(0.4)
    save_snapshots(snapshots)
    print(f"\n[DONE] Written {written} new snapshots to {SNAPSHOT_FILE}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=10)
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()
    backfill(n_days=args.days, overwrite=args.overwrite)
