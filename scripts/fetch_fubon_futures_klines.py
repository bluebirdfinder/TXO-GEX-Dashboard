"""
fetch_fubon_futures_klines.py - LOCAL, run-by-hand: accumulate REAL futures intraday candles from Fubon Neo.

Why local + accumulate: Fubon's futopt REST gives intraday candles only for the MOST RECENT session per call
(regular session = the last day session, `session=afterhours` = the last night session) and has no historical
candles endpoint (probed 2026-09-27: historical/* -> 404). So history is built by running this once after each
day session and once after each night session (or once a day after 05:00): every run merges the returned bars into
data/klines_cache.json (dedupe by bar time, capped), so the series grows day by day. Bars are real: OHLC and the
`volume` come straight from Fubon (no derived or invented values).

Daily / weekly / monthly futures bars are NOT written here — scripts/fetch_market_klines.py builds them from TAIFEX
futDataDown, and it preserves the intraday bars this script accumulated.

Login = your own .env (the same credentials scripts/live_price_server.py uses); read-only market-data calls only,
no order or account queries. Stop live_price_server.py first if your broker allows one active login per key.

    python scripts/fetch_fubon_futures_klines.py            # TXF, MXF, MTX(微台), CDF
    python scripts/fetch_fubon_futures_klines.py TXF        # only some assets
    python scripts/fetch_fubon_futures_klines.py --dry-run  # fetch + report, write nothing
"""
import datetime
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_market_klines import FUTURES_ASSETS, aggregate_4h_from_1h  # noqa: E402

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "klines_cache.json")
TFS = {"1M": "1", "5M": "5", "15M": "15", "30M": "30", "1H": "60"}  # Fubon has no 3-minute bars; 4H is aggregated from 1H
CAP = {"1M": 8000, "5M": 8000, "15M": 8000, "30M": 6000, "1H": 4000, "4H": 3000}  # newest bars kept per timeframe


def to_bar(c):
    ts = datetime.datetime.fromisoformat(c["date"]).timestamp()
    return {"time": int(ts), "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"], "volume": int(c.get("volume") or 0)}


def merge(old, new, cap):
    by_time = {b["time"]: b for b in (old or [])}
    by_time.update({b["time"]: b for b in new})  # a re-fetched (more complete) bar replaces the earlier one
    return [by_time[t] for t in sorted(by_time)][-cap:]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    wanted = args or list(FUTURES_ASSETS)

    # credentials are loaded by fubon_api_provider itself from the project's .env
    from fubon_api_provider import fubon_provider as provider  # noqa: E402

    if not getattr(provider, "is_active", False):
        print("Fubon API not active (login failed / credentials missing) — nothing fetched.")
        return
    rest = provider.marketdata.rest_client.futopt

    with open(CACHE, "r", encoding="utf-8") as f:
        cache = json.load(f)

    for sym in wanted:
        if sym not in FUTURES_ASSETS:
            print(f"skip unknown asset {sym}")
            continue
        alias = FUTURES_ASSETS[sym][1]
        asset = cache["assets"].setdefault(sym, {"symbol": sym, "timeframes": {}})
        tfs = asset.setdefault("timeframes", {})
        # First real run replaces any earlier non-Fubon intraday series (the old Yahoo spot-index/formula-volume data).
        if not str(asset.get("intraday_source", "")).startswith("Fubon"):
            for k in [k for k in tfs if k in ("1M", "3M", "5M", "15M", "30M", "1H", "4H")]:
                del tfs[k]
        for tf_key, tf in TFS.items():
            fetched = []
            for session in (None, "afterhours"):
                try:
                    kw = {"symbol": alias, "timeframe": tf}
                    if session:
                        kw["session"] = session
                    fetched += [to_bar(c) for c in rest.intraday.candles(**kw).get("data", [])]
                except Exception as e:  # noqa: BLE001
                    print(f"  {sym} {tf_key} {session or 'regular'}: {type(e).__name__}: {str(e)[:80]}")
            if fetched:
                before = len(tfs.get(tf_key, []))
                tfs[tf_key] = merge(tfs.get(tf_key), fetched, CAP[tf_key])
                print(f"  {sym} {tf_key}: fetched {len(fetched)} -> stored {len(tfs[tf_key])} (was {before})")
        if tfs.get("1H"):
            tfs["4H"] = merge(tfs.get("4H"), aggregate_4h_from_1h(tfs["1H"]), CAP["4H"])
        asset["intraday_source"] = "Fubon Neo futopt intraday candles (accumulated locally; real OHLC + volume)"

    if dry:
        print("dry-run: nothing written")
        return
    cache["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"saved {CACHE}")


if __name__ == "__main__":
    main()
