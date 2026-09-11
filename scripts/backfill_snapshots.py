"""
backfill_snapshots.py - One-time historical snapshot seeder
Uses TAIFEX/TWSE historical APIs to populate session_snapshots.json
with real spot/txf/vix/pc_ratio for past N trading days.
GEX fields (zero_gamma etc.) are set to null (requires historical OI, not available).
"""
import os, sys, json, ssl, datetime, urllib.request, time
sys.stdout.reconfigure(encoding="utf-8")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR   = os.path.join(os.path.dirname(_SCRIPT_DIR), "data")
SNAPSHOT_FILE    = os.path.join(_DATA_DIR, "session_snapshots.json")
TW_HOLIDAYS_FILE = os.path.join(_DATA_DIR, "tw_holidays.json")

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
    """Fetch TX day/night closing from TAIFEX CSV."""
    url = f"https://www.taifex.com.tw/cht/3/futDataDown?down_type=1&commodity_id=TX&Date_From={date_str}&Date_To={date_str}"
    txt = fetch_url(url)
    if not txt: return None, None
    day_close = night_close = None
    for line in txt.split("\n"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 9: continue
        date_col = parts[0].replace("/","")
        if date_str not in date_col: continue
        try:
            close_val = float(parts[7].replace(",",""))
            if close_val < 10000: continue
            if "夜盤" in line or len(parts) > 10 and parts[1] == "1":
                if night_close is None: night_close = close_val
            else:
                if day_close is None: day_close = close_val
        except Exception: continue
    return day_close, night_close

def fetch_taifex_pc_ratio(date_str):
    """Fetch PC ratio history page and look for date_str."""
    url = "https://www.taifex.com.tw/cht/3/callPutRatioHis"
    txt = fetch_url(url)
    if not txt: return None
    y, m, d = date_str[:4], date_str[4:6], date_str[6:]
    target = f"{y}/{m}/{d}"
    for line in txt.split("\n"):
        if target in line:
            import re
            nums = re.findall(r"[\d,]+\.?\d*", line)
            if nums:
                try: return float(nums[-1].replace(",",""))
                except Exception: pass
    return None

def fetch_twse_index(date_str):
    """Fetch TWSE TAIEX closing for date YYYYMMDD."""
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date_str}&type=MS&response=json"
    txt = fetch_url(url)
    if not txt: return None
    try:
        data = json.loads(txt)
        for tbl in data.get("tables",[]):
            for row in tbl.get("data",[]):
                if "發行量加權" in str(row[0]):
                    try: return float(str(row[-1]).replace(",",""))
                    except Exception: pass
    except Exception: pass
    return None

def backfill(n_days=10, overwrite=False):
    trading_days = get_past_tw_trading_days(n_days)
    snapshots = load_snapshots()
    print(f"Backfilling {n_days} trading days...")
    written = 0
    for day in trading_days:
        date_str = day.strftime("%Y%m%d")
        iso_str  = day.strftime("%Y-%m-%d")
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
            snapshots[key] = {
                "date": iso_str, "session": sess,
                "spot_price": spot, "otc_price": None, "txf_price": txf,
                "zero_gamma_level": None, "gex_plus_flip": None,
                "call_wall_strike": None, "put_wall_strike": None, "max_pain_strike": None,
                "pc_ratio": pc_ratio, "taifex_vix": None, "us_vix": None,
                "margin_maint_market": None, "margin_maint_stock": None,
                "written_at": f"{iso_str}T23:59:00+08:00", "source": "backfill"
            }
            print(f"spot={spot}, txf={txf}, pc={pc_ratio}")
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
