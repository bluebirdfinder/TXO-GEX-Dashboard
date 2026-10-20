r"""指標轉接層（公開檔，不含任何指標公式）：把 1 分 K 聚成 15M/30M、接上富邦累積的歷史，再呼叫「私有指標模組」。
指標公式只放使用者私有資料夾（預設 C:\Users\mingi\txo-private\desk_indicators\，可用環境變數 TXO_DESK_INDICATORS 改），
公開 repo 只拿到結果。找不到私有模組＝不提供指標（exhaustion 一律當作『沒有竭盡』，保守擋單），不拿近似公式頂替。

K 線時間標籤一律「該根開始時刻」（與富邦、TradingView 相同）。聚合以「交易時段開始」為錨：日盤 08:45、夜盤 15:00。
只用「已收完」的 K 棒做判斷（形成中的最後一根不算）。"""
import importlib.util
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

TW = timezone(timedelta(hours=8))
PRIVATE_DIR = Path(os.environ.get("TXO_DESK_INDICATORS") or r"C:\Users\mingi\txo-private\desk_indicators")


def load_private(name="demark_v4_indices", folder=None):
    path = Path(folder or PRIVATE_DIR) / f"{name}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"txo_private_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _t(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TW)


def session_start(t):
    """該時刻所屬交易時段的開始（日盤 08:45、夜盤 15:00；凌晨 0-5 點屬於前一天開的夜盤）。休市時段回 None。"""
    m = t.hour * 60 + t.minute
    if 8 * 60 + 45 <= m < 13 * 60 + 45:
        return t.replace(hour=8, minute=45, second=0, microsecond=0)
    if m >= 15 * 60:
        return t.replace(hour=15, minute=0, second=0, microsecond=0)
    if m < 5 * 60:
        return (t - timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
    return None


def resample(bars_1m, minutes):
    """1 分 K（ts=開始時刻）→ N 分 K，錨定交易時段開始。回傳 [{'ts','open','high','low','close','volume','n'}]，n=該桶內 1 分 K 根數。"""
    buckets = {}
    order = []
    for b in bars_1m:
        t = _t(b["ts"])
        s = session_start(t)
        if s is None:
            continue
        k = s + timedelta(minutes=((t - s).total_seconds() // 60 // minutes) * minutes)
        if k not in buckets:
            buckets[k] = {"ts": k.strftime("%Y-%m-%d %H:%M"), "open": b["open"], "high": b["high"], "low": b["low"],
                          "close": b["close"], "volume": b.get("volume", 0), "n": 1}
            order.append(k)
        else:
            x = buckets[k]
            x["high"] = max(x["high"], b["high"])
            x["low"] = min(x["low"], b["low"])
            x["close"] = b["close"]
            x["volume"] += b.get("volume", 0)
            x["n"] += 1
    return [buckets[k] for k in order]


def closed_only(buckets, minutes, last_1m_ts):
    """去掉還沒收完的桶：桶開始 + N 分鐘 ≤ 最後一根已收 1 分 K 的結束時刻（開始+1 分鐘）。"""
    end = _t(last_1m_ts) + timedelta(minutes=1)
    return [b for b in buckets if _t(b["ts"]) + timedelta(minutes=minutes) <= end]


def merge_history(cache_bars, fresh_bars, max_gap_h=60, minutes=15):
    """富邦累積的歷史 + 剛聚出來的新棒。重疊部分以富邦為準；回傳 (合併後, 缺口小時數或 None, 說明)。
    缺口＝新棒第一根與歷史最後一根之間的時間差；超過 max_gap_h 代表中間缺了整個時段，計數狀態不可信。"""
    if not fresh_bars:
        return list(cache_bars), None, "沒有新棒，只用歷史"
    if not cache_bars:
        return list(fresh_bars), None, "沒有歷史，只用新棒（計數可能不完整）"
    last_hist = _t(cache_bars[-1]["ts"])
    add = [b for b in fresh_bars if _t(b["ts"]) > last_hist]
    if not add:
        return list(cache_bars), 0.0, "新棒都已在歷史裡"
    gap_h = (_t(add[0]["ts"]) - last_hist).total_seconds() / 3600
    # 同一個交易時段內必須逐根相連（中間漏掉任何一根都不行）；跨時段才允許時段之間的空檔
    if session_start(last_hist) == session_start(_t(add[0]["ts"])) and gap_h * 60 > minutes + 0.5:
        return list(cache_bars) + add, gap_h, f"同一時段內歷史與新棒之間漏了 {gap_h * 60 - minutes:.0f} 分鐘，指標計數不可信"
    # 連續：同一時段內下一根，或跨時段（日盤→夜盤約 1.25 小時、夜盤→日盤約 3.75 小時、週末約 52 小時）
    if gap_h > max_gap_h:
        return list(cache_bars) + add, gap_h, f"歷史與新棒之間缺了 {gap_h:.0f} 小時（超過 {max_gap_h}），指標計數不可信"
    return list(cache_bars) + add, gap_h, "ok"


def demark_summary(bars, mod, recent=3, require_perfection=True):
    """對一個週期的「已收完」K 棒跑私有九轉模組，回傳摘要。recent＝最近幾根內出現過竭盡訊號都算。"""
    if mod is None:
        return {"available": False, "reason": "找不到私有指標模組"}
    if len(bars) < 30:
        return {"available": False, "reason": f"K 棒太少（{len(bars)} 根）"}
    st = mod.compute(bars)
    last = st[-1]
    win = st[-recent:]
    down = any((s["b_done"] and (s["b_perf"] or not require_perfection)) or s["bc_comp"] for s in win)
    up = any((s["s_done"] and (s["s_perf"] or not require_perfection)) or s["sc_comp"] for s in win)
    return {"available": True, "last_bar": bars[-1]["ts"], "bars_used": len(bars),
            "b_cnt": last["b_cnt"], "s_cnt": last["s_cnt"], "bc": last["bc"], "sc": last["sc"],
            "down_exhausted": down, "up_exhausted": up}


def build_indicators(fresh_1m, cache_by_tf, mod, recent=3, require_perfection=True, max_gap_h=60):
    """fresh_1m：最新一段 1 分 K（ts=開始時刻，已排除形成中那根）；cache_by_tf：{'15M': [...], '30M': [...]}（富邦累積，ts=開始時刻）。
    回傳 indicators dict（可直接放進快照）。exhaustion 的方向判斷由 snapshot.to_ctx 依 surge 正負決定。"""
    out = {"demark": {}, "note": []}
    if not fresh_1m:
        out["note"].append("沒有 1 分 K，無法算指標")
    for tf, minutes in (("15M", 15), ("30M", 30)):
        fresh = closed_only(resample(fresh_1m, minutes), minutes, fresh_1m[-1]["ts"]) if fresh_1m else []
        merged, gap_h, msg = merge_history(cache_by_tf.get(tf) or [], fresh, max_gap_h, minutes)
        if "不可信" in msg:
            out["demark"][tf] = {"available": False, "reason": msg}
        else:
            out["demark"][tf] = demark_summary(merged, mod, recent, require_perfection)
            out["demark"][tf]["history"] = msg
    ok = [v for v in out["demark"].values() if v.get("available")]
    out["down_exhausted"] = any(v["down_exhausted"] for v in ok)
    out["up_exhausted"] = any(v["up_exhausted"] for v in ok)
    if not ok:
        out["note"].append("九轉不可用：竭盡一律視為『沒有』")
    return out
