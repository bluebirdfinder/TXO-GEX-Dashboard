"""
gex_v2_daily.py — 每日並行累積「通行版(v2)」點位到 data/gex_v2_history.json（不碰 gex_data.json 的任何欄位）。

由 .github/workflows/auto_update.yml 在主流程之後呼叫（continue-on-error，失敗不影響主流程）。
做的事（冪等）：
  1. 抓期交所最近 ~10 天 optDataDown，找出尚未入檔、且 OI／結算價已公布的交易日。
  2. 對每個新交易日算 v2（見 gex_v2.py），並附上：加權指數 OHLC、臺指 VIX、台指期 OHLC。
  3. 同時存「v1_live」＝當下 data/gex_data.json 顯示給使用者的點位（chip_base_date 等於該日時才存；
     之後同一日再執行會用較新的覆蓋，次日起凍結），這是「使用者實際看到的 v1」的歷史紀錄。
  4. 另存「v1」＝以現行引擎函式在 13:30 基準、當日 VIX 重算（與回補相同路徑，可跨日比較）；匯入失敗則留空。
資料誠實：官方資料未公布 → 該日不寫，不用舊資料頂替；任何欄位取不到 → null，不補值。
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gex_v2 as g  # noqa: E402
import gex_v2_backfill as bf  # noqa: E402

HIST = os.environ.get("GEX_V2_HIST") or os.path.join(ROOT, "data", "gex_v2_history.json")   # 環境變數僅供測試覆寫
GEX = os.path.join(ROOT, "data", "gex_data.json")
TW = datetime.timezone(datetime.timedelta(hours=8))


def load_hist():
    try:
        return json.load(open(HIST, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"meta": {"created": datetime.datetime.now(TW).isoformat(timespec="seconds"),
                         "note": "模型輸出，不是預測。缺資料的欄位為 null，未補值。"}, "days": {}}


def v1_live_snapshot(day_iso):
    try:
        d = json.load(open(GEX, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if d.get("chip_base_date") != day_iso:
        return None
    close_ok = d.get("gamma_flip_standard_close_date") == day_iso
    return {"source": "data/gex_data.json", "last_updated_time": d.get("last_updated_time"), "engine_version": d.get("engine_version"),
            "session_name": d.get("session_name"),
            "gamma_flip_standard_close": d.get("gamma_flip_standard_close") if close_ok else None,
            "gamma_flip_standard_live": d.get("gamma_flip_standard"),
            "oi_split_level": d.get("zero_gamma_level"), "call_wall": d.get("call_wall_strike"), "put_wall": d.get("put_wall_strike"),
            "max_pain": d.get("max_pain_strike"), "total_gex_val_raw": d.get("total_gex_val"),
            "total_gex_per1pct": round(d["total_gex_val"] / 100.0, 3) if isinstance(d.get("total_gex_val"), (int, float)) else None,
            "sigma": (d.get("gex_model") or {}).get("sigma")}


def main():
    H = load_hist()
    days = H.setdefault("days", {})
    today = datetime.datetime.now(TW).date()
    start = today - datetime.timedelta(days=10)
    parsed = g.parse_opt(g.fetch_opt_text(start, today))
    changed = False
    fvc = None
    try:
        import fetch_and_calc_vision as fvc  # noqa: E402
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] 無法匯入現行引擎，略過 v1 重算：{e}")

    idx_cache, tx_cache = {}, {}
    for day_iso in sorted(parsed):
        dd = parsed[day_iso]
        # OI／結算價尚未公布 → 跳過（不借用舊資料）
        oi_total = sum(x["oi"] for e in dd.values() for x in e["q"].values())
        n_settle = sum(1 for e in dd.values() for x in e["q"].values() if x["settle"] is not None)
        if oi_total <= 0 or n_settle == 0:
            print(f"{day_iso}: OI／結算價尚未公布，略過")
            continue
        day = datetime.date.fromisoformat(day_iso)
        rec = days.get(day_iso)
        if rec is None:
            ym = (day.year, day.month)
            if ym not in idx_cache:
                idx_cache[ym] = bf.fetch_index_close(day.replace(day=1), day, None)
                tx_cache[ym] = bf.fetch_tx_ohlc(day.replace(day=1), day, None)
            ix = idx_cache[ym].get(day_iso)
            spot = ix["c"] if ix else None
            lv = g.compute_day(day_iso, dd, spot=spot)
            if lv is None:
                continue
            vix = bf.fetch_vix(day, None)
            rec = {"index_close": spot, "index": ix, "vix": vix, "tx": tx_cache[ym].get(day_iso), "v2": bf.slim(lv), "v1": None}
            if fvc is not None:
                try:
                    rec["v1"] = bf.v1_levels(fvc, day_iso, dd, spot, vix)
                except Exception as e:  # noqa: BLE001
                    print(f"[WARN] {day_iso} v1 重算失敗：{e}")
            days[day_iso] = rec
            changed = True
            print(f"{day_iso}: 新增 v2（flip={rec['v2']['flip']}, 牆 {rec['v2']['call_wall_net']}/{rec['v2']['put_wall_net']}）")
        live = v1_live_snapshot(day_iso)
        # 只在實質點位改變時才更新（時間戳、盤中即時 flip 每次都不同，不列入比較，避免每次排程都改寫檔案）
        MAT = ("gamma_flip_standard_close", "oi_split_level", "call_wall", "put_wall", "max_pain", "total_gex_val_raw", "sigma", "engine_version")
        if live and (not rec.get("v1_live") or any(rec["v1_live"].get(k) != live.get(k) for k in MAT)):
            rec["v1_live"] = live
            changed = True
            print(f"{day_iso}: 更新 v1_live")
    if changed:
        H["meta"]["last_daily_update"] = datetime.datetime.now(TW).isoformat(timespec="seconds")
        json.dump(H, open(HIST, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(f"已寫入 {HIST}（共 {len(days)} 天）")
    else:
        print("無新資料")


if __name__ == "__main__":
    main()
