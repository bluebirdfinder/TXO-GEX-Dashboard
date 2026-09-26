"""
backfill_margin_balance.py - Fills `margin_balance_billion` (融資餘額, 億 TWD) into existing
data/session_snapshots.json DAY/NIGHT entries so the 融資餘額變化速度 indicator (v64.4) has real
history immediately instead of waiting days for live runs to accumulate it.

Source: TWSE MI_MARGN with an explicit `date` (selectType=MS). Row '融資金額(仟元)' carries
[買進, 賣出, 現償, 前日餘額, 今日餘額]; 今日餘額/1e5 = 億 TWD. The response echoes its own `date`;
anything other than the requested date (e.g. a holiday) is skipped, never borrowed.
Only fills entries whose balance is currently None; never invents a snapshot key.

Usage: python scripts/backfill_margin_balance.py [--days 10] [--dry-run]
"""
import argparse, json, os, ssl, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backfill_snapshots import get_past_tw_trading_days, load_snapshots, save_snapshots  # noqa: E402

CTX = ssl.create_default_context()
CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT  # TWSE cert lacks Subject Key Identifier; chain+hostname still verified


def fetch_balance(d):
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={d.strftime('%Y%m%d')}&selectType=MS&response=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=15) as r:
        res = json.loads(r.read().decode("utf-8"))
    if res.get("stat") != "OK" or res.get("date") != d.strftime("%Y%m%d"):
        return None
    for row in res["tables"][0]["data"]:
        if "融資金額" in row[0]:
            return round(float(row[5].replace(",", "")) / 1e5, 2)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    snaps = load_snapshots()
    changed = 0
    for d in sorted(get_past_tw_trading_days(a.days)):
        iso = d.isoformat()
        keys = [k for k in (f"{iso}_DAY", f"{iso}_NIGHT") if k in snaps and snaps[k].get("margin_balance_billion") is None]
        if not keys:
            continue
        bal = fetch_balance(d)
        time.sleep(1.0)
        print(f"{iso}: balance={bal} -> {keys}")
        if bal is None:
            continue
        for k in keys:
            snaps[k]["margin_balance_billion"] = bal
            changed += 1
    if changed and not a.dry_run:
        save_snapshots(snaps)
    print(f"filled={changed}{' (dry-run, not saved)' if a.dry_run else ''}")


if __name__ == "__main__":
    main()
