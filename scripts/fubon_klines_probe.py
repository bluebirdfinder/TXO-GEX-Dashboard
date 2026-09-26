"""
fubon_klines_probe.py - READ-ONLY probe: what futures candles does the Fubon Neo market-data REST API give?

Why: the room's TXF/MTX/MXF/CDF K-lines currently come from the wrong instrument (^TWII / 2330.TW) with a
formula-made volume (see HISTORY v64.9). Fubon's REST candles are server-side data, so they can be
queried any time (holiday / after close) — the Fubon quote *program* does not need to be open, only a
valid API login from your own .env (same credentials scripts/live_price_server.py already uses).

This script only PRINTS what comes back (field names, bar counts, first/last bars). It writes no files and
never places or queries orders. Run it yourself while you are at the machine:

    python scripts/fubon_klines_probe.py            # default symbol TXF1!
    python scripts/fubon_klines_probe.py TXFJ6      # or an explicit contract code

Close other sessions that hold the same API key first (e.g. stop scripts/live_price_server.py) in case the
broker allows only one active login per key.
"""
import datetime
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fubon_api_provider import fubon_provider as provider  # noqa: E402  (module-level instance: loads .env, logs in, builds MarketData)


def show(label, call):
    print(f"\n=== {label}")
    try:
        res = call()
    except Exception as e:  # noqa: BLE001 - a probe should report, not crash
        print(f"  ERROR: {type(e).__name__}: {e}")
        return
    if isinstance(res, dict):
        print("  top-level keys:", list(res.keys()))
        bars = res.get("data") or res.get("candles") or []
    else:
        bars = res or []
    print(f"  bars: {len(bars)}")
    if bars:
        print("  fields:", list(bars[0].keys()) if isinstance(bars[0], dict) else type(bars[0]))
        print("  first:", json.dumps(bars[0], ensure_ascii=False)[:200])
        print("  last :", json.dumps(bars[-1], ensure_ascii=False)[:200])


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "TXF1!"
    if not getattr(provider, "is_active", False):
        print("Fubon API is not active (login failed or credentials missing in .env) — nothing to probe.")
        return
    rest = provider.marketdata.rest_client.futopt
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=10)).isoformat()

    for session in ("REGULAR", "AFTERHOURS"):
        show(f"intraday.candles {symbol} 15m {session}",
             lambda s=session: rest.intraday.candles(symbol=symbol, timeframe="15", session=s))
    show(f"historical.candles {symbol} 1m (last 10 days)",
         lambda: rest.historical.candles(symbol=symbol, timeframe="1", **{"from": start, "to": today.isoformat()}))
    show(f"historical.candles {symbol} 15m (last 10 days)",
         lambda: rest.historical.candles(symbol=symbol, timeframe="15", **{"from": start, "to": today.isoformat()}))
    show(f"historical.candles {symbol} D (last 60 days)",
         lambda: rest.historical.candles(symbol=symbol, timeframe="D",
                                         **{"from": (today - datetime.timedelta(days=60)).isoformat(), "to": today.isoformat()}))


if __name__ == "__main__":
    main()
