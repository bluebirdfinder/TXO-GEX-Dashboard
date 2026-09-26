"""
backfill_margin_maint_estimates.py - Rebuilds the day-by-day 融資維持率 ESTIMATE chain.

TWSE publishes no market-wide maintenance ratio, so the dashboard estimates it (see
fetch_twse_margin_maintenance): est_D = est_(D-1) * (1 + TAIEX %chg_D) / (1 + 融資餘額 %chg_D),
where the balance change comes from TWSE MI_MARGN (前日餘額 -> 今日餘額 for date D) and the index
change from TWSE FMTQIK. The live estimator anchors on the previous trading day's persisted value; if
any day in between was never persisted the chain silently skips days (found 2026-09-26: 9/24 was
anchored on 9/17). This script replays the chain over every trading day with real inputs and writes
MARGIN_MAINT_EST_<date> (institutional_snapshots.json) plus the DAY entries in session_snapshots.json.
The starting anchor is the documented bootstrap baseline (160.0 / 145.0) at --anchor-date.

Usage: python scripts/backfill_margin_maint_estimates.py [--anchor-date 2026-09-14] [--dry-run]
"""
import argparse, datetime, json, os, ssl, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_and_calc_vision as eng  # noqa: E402
from backfill_snapshots import load_snapshots, save_snapshots  # noqa: E402

CTX = ssl.create_default_context()
CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT
H = {"User-Agent": "Mozilla/5.0"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), context=CTX, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def taiex_pct_by_date(start, end):
    """{YYYY-MM-DD: % change vs previous trading day} from FMTQIK (monthly tables)."""
    closes = {}
    d = datetime.date(start.year, start.month, 1) - datetime.timedelta(days=1)
    months = {(d.year, d.month), (start.year, start.month), (end.year, end.month)}
    for y, m in sorted(months):
        res = _get(f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={y}{m:02d}01&response=json")
        for row in res.get("data", []):
            roc, close = row[0].split("/"), float(row[4].replace(",", ""))
            closes[datetime.date(int(roc[0]) + 1911, int(roc[1]), int(roc[2]))] = close
        time.sleep(1)
    days = sorted(closes)
    return {days[i].isoformat(): (closes[days[i]] / closes[days[i - 1]] - 1) * 100 for i in range(1, len(days))}


def balances(d):
    res = _get(f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={d.strftime('%Y%m%d')}&selectType=MS&response=json")
    if res.get("stat") != "OK" or res.get("date") != d.strftime("%Y%m%d"):
        return None
    for row in res["tables"][0]["data"]:
        if "融資金額" in row[0]:
            return float(row[4].replace(",", "")), float(row[5].replace(",", ""))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor-date", default="2026-09-14")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    anchor = datetime.date.fromisoformat(a.anchor_date)
    last = eng.get_recent_tw_trading_days(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))), n=1)[-1]
    days, d = [], anchor + datetime.timedelta(days=1)
    while d <= last:
        if eng.is_tw_trading_day(d):
            days.append(d)
        d += datetime.timedelta(days=1)
    pct = taiex_pct_by_date(anchor, last)
    inst = eng.load_institutional_snapshots()
    snaps = load_snapshots()
    mk, sk = 160.0, 145.0  # documented bootstrap baseline at the anchor date
    for d in days:
        iso = d.isoformat()
        b = balances(d)
        time.sleep(1)
        if b is None or iso not in pct:
            print(f"{iso}: inputs unavailable, chain stops here")
            break
        bal_pct = (b[1] - b[0]) / b[0] * 100
        mk = round(mk * (1 + pct[iso] / 100) / (1 + bal_pct / 100), 1)
        sk = round(sk * (1 + pct[iso] / 100) / (1 + bal_pct / 100), 1)
        print(f"{iso}: TAIEX {pct[iso]:+.2f}%  融資餘額 {bal_pct:+.2f}%  -> 大盤 {mk} / 個股 {sk}")
        inst[f"MARGIN_MAINT_EST_{d.strftime('%Y%m%d')}"] = {"margin_maint_market": mk, "margin_maint_stock": sk}
        for key in (f"{iso}_DAY", f"{iso}_NIGHT"):
            if key in snaps:
                snaps[key]["margin_maint_market"], snaps[key]["margin_maint_stock"] = mk, sk
    for k in [k for k in inst if k.startswith("MARGIN_MAINT_EST_") and
              not eng.is_tw_trading_day(datetime.datetime.strptime(k[-8:], "%Y%m%d").date())]:
        print(f"drop non-trading-day key {k}")
        del inst[k]
    if not a.dry_run:
        eng.save_institutional_snapshots(inst)
        save_snapshots(snaps)


if __name__ == "__main__":
    main()
