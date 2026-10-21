"""決策快照（規格第5節）：每次決策把餵給 AI 的全部輸入凍結存檔，之後覆盤與「考試」才公平。
缺資料或過期 → 回報 missing，上游一律「無決策：缺 XX」，嚴禁補假資料（專案紅線 #6）。
時間一律台灣時區（+08:00）。程式只組裝與檢查，不產生任何行情數字。"""
import gzip
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from quotes import QuoteChain, chain_from_mis_rows

TW = timezone(timedelta(hours=8))
GEX_KEEP = ("date", "last_updated_time", "session_type", "engine_version", "spot_price", "txf_price", "day_txf_price",
            "night_txf_price", "zero_gamma_level", "gex_plus_flip", "gamma_flip_standard", "call_wall_strike",
            "put_wall_strike", "max_pain_strike", "pc_ratio", "total_gex_val", "total_gex_plus", "total_vex",
            "gex_chain_stale", "data_completeness", "vix_info", "gex_model", "dte_dates")
GEX_REQUIRED = ("call_wall_strike", "put_wall_strike", "zero_gamma_level", "max_pain_strike", "spot_price")


def _parse_tw(s):
    """'2026-10-19 15:03' 或帶 +08:00 的 ISO → aware datetime（沒標時區就當台灣時間）。"""
    if not isinstance(s, str):
        return None
    try:
        t = datetime.fromisoformat(s.strip().replace(" ", "T"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=TW)


def session_of(now):
    """日盤 08:45-13:45、夜盤 15:00-05:00，其餘休市（不含假日，假日靠資料過期自然攔下）。"""
    m = now.hour * 60 + now.minute
    if 8 * 60 + 45 <= m < 13 * 60 + 45:
        return "day"
    if m >= 15 * 60 or m < 5 * 60:
        return "night"
    return "closed"


def build_snapshot(now, account, gex, spot, kbars, chain_rows, indicators=None, tg_signals=None, manual_ref=None, sources=None):
    """now: aware datetime（台灣）。各輸入原樣凍結（gex 只保留需要的欄位）；缺的就給 None，由 check 回報。
    kbars: [{'ts': 'YYYY-MM-DD HH:MM', 'open','high','low','close','volume'}...] 只收 ts <= now 的（擋未來資料）。
    spot: {'price': float, 'ts': ISO 或 None, 'provider': str} 或 None。"""
    bars = [b for b in (kbars or []) if (_parse_tw(b.get("ts")) or now + timedelta(days=1)) <= now]
    snap = {
        "version": 1,
        "account": account,
        "decided_at": now.isoformat(timespec="seconds"),
        "manual_ref": manual_ref,
        "gex": {k: gex[k] for k in GEX_KEEP if gex and k in gex} if gex else None,
        "spot": spot,
        "kbars_1m": bars[-300:],
        "chain_rows": chain_rows,        # 紀錄器的有報價列，原樣
        "indicators": indicators or {},  # 由程式算好再給 AI（SMC/FVG/九轉…），不讓 AI 看圖猜
        "tg_signals": tg_signals if account == "T1" else None,      # T0 不看共振訊號
        "sources": sources or {},
    }
    return snap


def check(snap, rules):
    """回傳缺漏/過期清單（空＝可決策）。rules 來自 desk_config['snapshot']。"""
    now = _parse_tw(snap["decided_at"])
    sess = session_of(now)      # 休市時段（收盤後決策）K 線與現價只要求「是剛收完的那一盤」，盤中則要求即時
    miss = []
    g = snap.get("gex")
    if not g:
        miss.append("GEX 點位")
    else:
        lost = [k for k in GEX_REQUIRED if g.get(k) is None]
        if lost:
            miss.append("GEX 欄位 " + "/".join(lost))
        upd = _parse_tw(g.get("last_updated_time"))
        if upd is None:
            miss.append("GEX 更新時間")
        elif now - upd > timedelta(minutes=rules["gex_max_age_min"]):
            miss.append(f"GEX 過期（{int((now - upd).total_seconds() // 60)} 分鐘前）")
        if g.get("gex_chain_stale"):
            miss.append("GEX 選擇權鏈標示過期")
        if (g.get("vix_info") or {}).get("taifex_vix") is None:
            miss.append("IV（期交所 VIX）")
    sp = snap.get("spot")
    if not sp or sp.get("price") is None:
        miss.append("台指期現價")
    else:
        t = _parse_tw(sp.get("ts"))
        if t is None:
            miss.append("現價時間戳")
        elif (now - t).total_seconds() > (rules["spot_max_age_s"] if sess != "closed" else rules["closed_max_age_min"] * 60):
            miss.append(f"現價過期（{int((now - t).total_seconds())} 秒前）")
    bars = snap.get("kbars_1m") or []
    if len(bars) < rules["min_kbars"]:
        miss.append(f"1 分 K 不足（{len(bars)} 根，需要 {rules['min_kbars']} 根）")
    else:
        last = _parse_tw(bars[-1]["ts"])
        if (now - last).total_seconds() > (rules["kbar_max_age_s"] if sess != "closed" else rules["closed_max_age_min"] * 60):
            miss.append(f"1 分 K 最後一根太舊（{bars[-1]['ts']}）")
    if not snap.get("chain_rows"):
        miss.append("選擇權報價鏈")
    return miss


def surge_pts(bars, window_min):
    """近 window_min 分鐘內「最新收盤相對區間低點(急拉，正)或高點(急殺，負)」的點數，取絕對值較大者；起手定義，待使用者確認。"""
    if not bars:
        return None
    w = bars[-window_min:]
    last = w[-1]["close"]
    up = last - min(b["low"] for b in w)
    dn = last - max(b["high"] for b in w)
    return up if abs(up) >= abs(dn) else dn


def chain_from_snapshot(snap, validity):
    """CTime 是最後成交時間、不是報價更新時間 → 去掉，改以快照時間當報價時間，避免誤判過期或亂用舊時間。"""
    now = _parse_tw(snap["decided_at"])
    rows = [{k: v for k, v in r.items() if k not in ("CTime", "CDate")} for r in snap["chain_rows"]]
    return chain_from_mis_rows(now.timestamp(), rows, validity, ts_fallback=now.timestamp())


def _exhaustion(ind, surge):
    """急殺(surge<0)要看「賣盤竭盡」(down_exhausted：買進 Setup 9★/Countdown 13)，急拉要看 up_exhausted；
    指標沒提供＝不算竭盡（保守）。舊格式 exhaustion_ok 仍相容。"""
    if "down_exhausted" in ind or "up_exhausted" in ind:
        return bool(ind.get("down_exhausted") if (surge is not None and surge < 0) else ind.get("up_exhausted"))
    return bool(ind.get("exhaustion_ok"))


def to_ctx(snap, rules):
    """給 risk.check 用的 ctx。缺漏清單放 missing；有缺漏時 spot/iv 仍如實給 None，不補值。"""
    now = _parse_tw(snap["decided_at"])
    g = snap.get("gex") or {}
    sp = snap.get("spot") or {}
    ind = snap.get("indicators") or {}
    return {
        "now": now.timestamp(), "today": now.date(), "session": session_of(now),
        "spot": sp.get("price"),
        "iv": (g.get("vix_info") or {}).get("taifex_vix"),
        "surge_pts": surge_pts(snap.get("kbars_1m") or [], rules["surge_window_min"]),
        "exhaustion_ok": _exhaustion(ind, surge_pts(snap.get("kbars_1m") or [], rules["surge_window_min"])),
        "missing": check(snap, rules),
    }


def save(snap, outdir):
    """寫成 <outdir>/<帳戶>/<決策時間>.json.gz，附 sha256；同名檔案存在就拒絕（快照不可改）。"""
    d = Path(outdir) / snap["account"]
    d.mkdir(parents=True, exist_ok=True)
    stamp = snap["decided_at"].replace(":", "").replace("-", "").replace("+0800", "").replace("T", "_")
    path = d / f"{stamp}.json.gz"
    if path.exists():
        raise FileExistsError(f"快照已存在，不可覆寫：{path}")
    body = json.dumps(snap, ensure_ascii=False, sort_keys=True).encode("utf-8")
    sha = hashlib.sha256(body).hexdigest()
    with gzip.open(path, "wb") as f:
        f.write(json.dumps({"sha256": sha, "snapshot": snap}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return path, sha


def load(path):
    """讀回並驗證 sha256；內容被改過就丟例外。"""
    with gzip.open(path, "rb") as f:
        o = json.loads(f.read().decode("utf-8"))
    body = json.dumps(o["snapshot"], ensure_ascii=False, sort_keys=True).encode("utf-8")
    if hashlib.sha256(body).hexdigest() != o["sha256"]:
        raise ValueError(f"快照內容與 sha256 不符（被改過？）：{path}")
    return o["snapshot"]
