r"""
Persistent local data store for the runner clone (C:\Users\mingi\txo-klines-runner, outside OneDrive).

Why: the runner used to COMMIT its own data (accumulated Fubon futures intraday candles, screener cache, per-stock daily K
shards) and then `git pull --rebase` on every task / server restart. The cloud engine (auto_update.yml) writes the same
files (data/klines_cache.json, data/tw_quotes_latest.json), so those pulls conflicted nearly every day; the rebase stayed
half-done, the server restarted on stale code and later tasks could not commit (2026-10-14..16).

New model: the runner checkout is disposable (fetch + reset --hard origin/main before every task), and everything the runner
itself produces lives here, outside git, and is overlaid back into data/ after each reset (working-tree only, never committed):
  absorb   data/ -> store   (futures intraday bars are UNIONED by bar time; screener files are copied)
  overlay  store -> data/   (futures bars unioned into the fresh cloud klines_cache.json; screener files copied back)
  backup   store -> a dated copy under the backup folder (default: OneDrive\...\TXO-runner-data-backup), keeps 14 copies
  seed     merge the futures bars of ANY klines_cache.json (e.g. one taken from a backup branch) into the store

Fubon serves only the LATEST session per call, so these bars cannot be re-fetched later - the store is the source of truth.
"""
import argparse
import datetime
import glob
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
STORE = os.environ.get("TXO_LOCAL_STORE") or os.path.join(os.path.expanduser("~"), ".txo_local_store")
BACKUP = os.environ.get("TXO_BACKUP_DIR") or os.path.join(os.path.expanduser("~"), "OneDrive", "文件", "TXO-runner-data-backup")

FUTURES = ("TXF", "MXF", "MTX", "CDF")                      # == fetch_market_klines.FUTURES_ASSETS
CAP = {"1M": 8000, "5M": 8000, "15M": 8000, "30M": 6000, "1H": 4000, "4H": 3000}   # == fetch_fubon_futures_klines.CAP
KLINES = "klines_cache.json"
GAP = "klines_gap_report.json"
SCREENER_FILES = ("screener_cache.json", "screener_ohlcv_cache.json", "stock_institutional_history.json")
STOCK_DAILY = "stock_daily"
STORE_KLINES = "futures_klines.json"


def _load(path):
    with open(path, encoding="utf-8-sig") as f:   # tolerate a BOM (PowerShell 5.1 writes one)
        return json.load(f)


def _dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def merge_bars(old, new, cap):
    """Union by bar time; on the same time the bar from `new` wins (same rule as fetch_fubon_futures_klines.merge)."""
    by_time = {b["time"]: b for b in (old or [])}
    by_time.update({b["time"]: b for b in (new or [])})
    return [by_time[t] for t in sorted(by_time)][-cap:]


def _futures_of(cache):
    out = {}
    for sym in FUTURES:
        tfs = ((cache.get("assets") or {}).get(sym) or {}).get("timeframes") or {}
        out[sym] = {tf: tfs[tf] for tf in CAP if tf in tfs}
    return out


def _merge_store(store, incoming):
    n = 0
    for sym, tfs in incoming.items():
        for tf, bars in tfs.items():
            before = len((store.setdefault(sym, {}).get(tf)) or [])
            store[sym][tf] = merge_bars(store[sym].get(tf), bars, CAP[tf])
            n += len(store[sym][tf]) - before
    return n


def absorb_file(klines_path):
    store_path = os.path.join(STORE, STORE_KLINES)
    store = _load(store_path) if os.path.exists(store_path) else {}
    added = _merge_store(store, _futures_of(_load(klines_path)))
    _dump(store_path, store)
    return added


def cmd_absorb(_a):
    added = absorb_file(os.path.join(DATA, KLINES))
    print(f"absorb: futures bars added to store: {added}")
    os.makedirs(os.path.join(STORE, "screener"), exist_ok=True)
    gap = os.path.join(DATA, GAP)
    if os.path.exists(gap):
        shutil.copy2(gap, os.path.join(STORE, GAP))
    for name in SCREENER_FILES:
        src = os.path.join(DATA, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(STORE, "screener", name))
    sd = os.path.join(DATA, STOCK_DAILY)
    if os.path.isdir(sd):
        dst = os.path.join(STORE, "screener", STOCK_DAILY)
        os.makedirs(dst, exist_ok=True)
        for p in glob.glob(os.path.join(sd, "*.json")):
            shutil.copy2(p, os.path.join(dst, os.path.basename(p)))
    print("absorb: done ->", STORE)


def cmd_overlay(_a):
    store_path = os.path.join(STORE, STORE_KLINES)
    if os.path.exists(store_path):
        store = _load(store_path)
        cache_path = os.path.join(DATA, KLINES)
        cache = _load(cache_path)
        n = 0
        for sym, tfs in store.items():
            tgt = cache.setdefault("assets", {}).setdefault(sym, {}).setdefault("timeframes", {})
            for tf, bars in tfs.items():
                before = len(tgt.get(tf) or [])
                tgt[tf] = merge_bars(tgt.get(tf), bars, CAP[tf])
                n += len(tgt[tf]) - before
        _dump(cache_path, cache)
        print(f"overlay: futures bars added into data/{KLINES}: {n}")
    gap = os.path.join(STORE, GAP)
    if os.path.exists(gap):
        shutil.copy2(gap, os.path.join(DATA, GAP))
    sc = os.path.join(STORE, "screener")
    for name in SCREENER_FILES:
        src = os.path.join(sc, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DATA, name))
    sd = os.path.join(sc, STOCK_DAILY)
    if os.path.isdir(sd):
        os.makedirs(os.path.join(DATA, STOCK_DAILY), exist_ok=True)
        for p in glob.glob(os.path.join(sd, "*.json")):
            shutil.copy2(p, os.path.join(DATA, STOCK_DAILY, os.path.basename(p)))
    print("overlay: done")


def cmd_backup(a):
    if not os.path.isdir(STORE):
        print("backup: nothing to back up (store missing)")
        return
    dest_root = a.dest or BACKUP
    os.makedirs(dest_root, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    dest = os.path.join(dest_root, stamp)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(STORE, dest)
    old = sorted(d for d in os.listdir(dest_root) if os.path.isdir(os.path.join(dest_root, d)))
    for d in old[:-14]:
        shutil.rmtree(os.path.join(dest_root, d), ignore_errors=True)
    print("backup: ->", dest)


def cmd_seed(a):
    added = absorb_file(a.file)
    print(f"seed: futures bars added to store from {a.file}: {added}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("absorb").set_defaults(fn=cmd_absorb)
    sub.add_parser("overlay").set_defaults(fn=cmd_overlay)
    b = sub.add_parser("backup")
    b.add_argument("--dest")
    b.set_defaults(fn=cmd_backup)
    s = sub.add_parser("seed")
    s.add_argument("file")
    s.set_defaults(fn=cmd_seed)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
