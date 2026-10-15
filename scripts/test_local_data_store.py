"""Self-test for local_data_store.py using temp dirs only (never touches the real store/data).
Run: python scripts/test_local_data_store.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok = ok and cond


def bars(times, tag):
    return [{"time": t, "open": tag, "high": tag, "low": tag, "close": tag, "volume": 1} for t in times]


def write_cache(root, txf_1m, other=None):
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    cache = {"version": "t", "assets": {
        "TXF": {"timeframes": {"1M": txf_1m, "1D": bars([1, 2], 9)}},
        "TAIEX": {"timeframes": {"1M": other or bars([10, 11], 5)}},
    }}
    with open(os.path.join(root, "data", "klines_cache.json"), "w", encoding="utf-8") as f:
        json.dump(cache, f)


def run(root, store, *args, backup=None):
    env = dict(os.environ, TXO_LOCAL_STORE=store, PYTHONIOENCODING="utf-8")
    if backup:
        env["TXO_BACKUP_DIR"] = backup
    # copy the module next to a fake ROOT so ROOT/data points at our temp tree
    sc = os.path.join(root, "scripts")
    os.makedirs(sc, exist_ok=True)
    with open(os.path.join(HERE, "local_data_store.py"), encoding="utf-8") as s, open(os.path.join(sc, "local_data_store.py"), "w", encoding="utf-8") as d:
        d.write(s.read())
    r = subprocess.run([sys.executable, os.path.join(sc, "local_data_store.py"), *args], capture_output=True, text=True, encoding="utf-8", env=env)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
    return r


def read(root):
    with open(os.path.join(root, "data", "klines_cache.json"), encoding="utf-8") as f:
        return json.load(f)


with tempfile.TemporaryDirectory() as tmp:
    root, store, bk = os.path.join(tmp, "runner"), os.path.join(tmp, "store"), os.path.join(tmp, "backup")
    # day 1: runner accumulated bars 100,101,102 (cloud file lacks them)
    write_cache(root, bars([100, 101, 102], 1))
    os.makedirs(os.path.join(root, "data", "stock_daily"))
    with open(os.path.join(root, "data", "stock_daily", "00.json"), "w") as f:
        f.write("{}")
    with open(os.path.join(root, "data", "screener_cache.json"), "w") as f:
        f.write('{"s":1}')
    check("absorb exits 0", run(root, store, "absorb").returncode == 0)
    check("store has futures file", os.path.exists(os.path.join(store, "futures_klines.json")))
    check("store has screener copy", os.path.exists(os.path.join(store, "screener", "screener_cache.json")) and os.path.exists(os.path.join(store, "screener", "stock_daily", "00.json")))
    # fresh cloud checkout: has newer bars 102(different) and 103, but not 100/101; stock_daily gone
    write_cache(root, bars([102, 103], 2))
    os.remove(os.path.join(root, "data", "screener_cache.json"))
    check("overlay exits 0", run(root, store, "overlay").returncode == 0)
    c = read(root)
    t = [b["time"] for b in c["assets"]["TXF"]["timeframes"]["1M"]]
    check("overlay unions bars by time (100..103)", t == [100, 101, 102, 103])
    same = [b for b in c["assets"]["TXF"]["timeframes"]["1M"] if b["time"] == 102][0]
    check("on same time the stored (Fubon) bar wins", same["open"] == 1)
    check("non-futures assets untouched", [b["time"] for b in c["assets"]["TAIEX"]["timeframes"]["1M"]] == [10, 11])
    check("other timeframes (1D) untouched", [b["time"] for b in c["assets"]["TXF"]["timeframes"]["1D"]] == [1, 2])
    check("screener file restored", os.path.exists(os.path.join(root, "data", "screener_cache.json")))
    # idempotent
    before = json.dumps(read(root), sort_keys=True)
    run(root, store, "overlay")
    check("overlay is idempotent", json.dumps(read(root), sort_keys=True) == before)
    # absorb again after new bars arrive, store must keep old ones even if checkout lacks them
    write_cache(root, bars([104], 3))
    run(root, store, "absorb")
    with open(os.path.join(store, "futures_klines.json"), encoding="utf-8") as f:
        st = json.load(f)
    check("store keeps old + new bars", [b["time"] for b in st["TXF"]["1M"]] == [100, 101, 102, 104] or [b["time"] for b in st["TXF"]["1M"]] == [100, 101, 102, 103, 104] or [b["time"] for b in st["TXF"]["1M"]] == [100, 101, 102, 104])
    # seed from another file (e.g. taken from a backup branch)
    seedroot = os.path.join(tmp, "seedsrc")
    write_cache(seedroot, bars([50, 51], 7))
    r = run(root, store, "seed", os.path.join(seedroot, "data", "klines_cache.json"))
    with open(os.path.join(store, "futures_klines.json"), encoding="utf-8") as f:
        st = json.load(f)
    check("seed merges extra bars", r.returncode == 0 and [b["time"] for b in st["TXF"]["1M"]][:2] == [50, 51])
    # backup keeps a dated copy and prunes beyond 14
    check("backup exits 0", run(root, store, "backup", backup=bk).returncode == 0)
    check("backup copy exists", len(os.listdir(bk)) == 1 and os.path.exists(os.path.join(bk, os.listdir(bk)[0], "futures_klines.json")))
    for i in range(20):
        os.makedirs(os.path.join(bk, f"2020-01-{i + 1:02d}"))
    run(root, store, "backup", backup=bk)
    check("backup prunes to 14 copies", len(os.listdir(bk)) == 14)
    # cap
    big = bars(range(0, 9000), 1)
    write_cache(root, big)
    run(root, store, "absorb")
    with open(os.path.join(store, "futures_klines.json"), encoding="utf-8") as f:
        st = json.load(f)
    check("cap (8000) applied, newest kept", len(st["TXF"]["1M"]) == 8000 and st["TXF"]["1M"][-1]["time"] == 8999)

print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
