"""報價紀錄器 health 統計（階段 0）。收盤後跑一次，看筆數、錯誤、429、延遲、檔案大小與中斷空窗。

用法：python -I tools/option_quote_health.py [YYYYMMDD] [輸出資料夾=C:\\Users\\mingi\\txo-private\\option_quotes]
不給日期＝用資料夾裡最新的 health_*.csv。只讀檔，不改任何東西。
"""
import csv
import statistics
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DIR = Path(r"C:\Users\mingi\txo-private\option_quotes")
GAP_S = 90          # 兩筆之間超過這麼久（紀錄器間隔 30 秒的 3 倍）算一次空窗


def pick_file(d, day):
    if day:
        return d / f"health_{day}.csv"
    files = sorted(d.glob("health_*.csv"))
    if not files:
        raise SystemExit(f"{d} 底下沒有 health_*.csv")
    return files[-1]


def summarize(rows):
    """rows: csv.DictReader 轉出的 list。回傳統計 dict；只用真實紀錄，沒有就回空統計。"""
    out = {"total": len(rows), "by_session": {}, "gaps": []}
    prev = None
    for r in rows:
        key = r.get("market_type") or "closed"
        s = out["by_session"].setdefault(key, {"ok": 0, "err": 0, "429": 0, "closed": 0, "other": 0, "lat": [], "rows": []})
        st = (r.get("status") or "").strip()
        if st == "ok":
            s["ok"] += 1
            s["lat"].append(float(r["latency_s"] or 0))
            s["rows"].append(int(r["rows"] or 0))
        elif st == "closed":
            s["closed"] += 1
        elif "429" in st:
            s["429"] += 1
        elif st.startswith("err") or st.startswith("error"):
            s["err"] += 1
        else:
            s["other"] += 1
        t = datetime.fromisoformat(r["ts"])
        if prev is not None and (t - prev).total_seconds() > GAP_S and st != "closed":
            out["gaps"].append((prev.isoformat(timespec="seconds"), t.isoformat(timespec="seconds"), int((t - prev).total_seconds())))
        if st != "closed":
            prev = t
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")        # python -I 會忽略 PYTHONIOENCODING，這裡直接指定，避免 Windows 終端機亂碼
    d = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DIR
    f = pick_file(d, sys.argv[1] if len(sys.argv) > 1 else None)
    with open(f, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    s = summarize(rows)
    print(f"檔案：{f.name}　總筆數 {s['total']}")
    for k, v in s["by_session"].items():
        name = {"0": "日盤", "1": "夜盤", "closed": "休市"}.get(k, k)
        lat = v["lat"]
        line = f"[{name}] 成功 {v['ok']}　錯誤 {v['err']}　429 {v['429']}　休市 {v['closed']}　其他 {v['other']}"
        if lat:
            lat_sorted = sorted(lat)
            line += f"　延遲平均 {statistics.mean(lat):.2f}s／最大 {max(lat):.2f}s／P95 {lat_sorted[int(len(lat_sorted) * 0.95) - 1]:.2f}s　有報價列數平均 {statistics.mean(v['rows']):.0f}"
        print(line)
    if s["gaps"]:
        print(f"中斷空窗（>{GAP_S} 秒）共 {len(s['gaps'])} 段：")
        for a, b, sec in s["gaps"]:
            print(f"  {a} → {b}（{sec // 60} 分 {sec % 60} 秒）")
    else:
        print("沒有中斷空窗")
    data = sorted(d.glob(f"{f.stem.replace('health_', '')}_*.jsonl.gz"))
    for p in data:
        print(f"資料檔 {p.name}：{p.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
