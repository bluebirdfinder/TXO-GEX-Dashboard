r"""台選鳥帳戶頁的本機資料服務（唯讀）：從你的私有帳本算出持倉/損益/風控距離，給網頁顯示。
  python server.py [埠號=8770]      然後用瀏覽器開 http://127.0.0.1:8770/
只綁 127.0.0.1、只讀、檢查 Host 標頭（防 DNS rebinding）；帳本與快照在 C:\Users\mingi\txo-private\desk\（不進 git，不上公開網頁）。
所有數字由程式從帳本重播算出，AI 不轉述。"""
import json
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import snapshot as sm
import sources
from book import Desk, load_config
from run_slot import PRIVATE, market_type

WEB = Path(__file__).parent / "web"
ACCOUNTS = ("T0", "T1")
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
_cache = {"t": 0.0, "rows": []}
_lock = threading.Lock()


def live_rows(now):
    """MIS 報價鏈（20 秒快取，避免頁面重新整理打爆期交所）。"""
    with _lock:
        if time.time() - _cache["t"] > 20:
            _cache["rows"] = sources.live_chain(market_type(now))
            _cache["t"] = time.time()
        return _cache["rows"]


def heartbeat(account):
    p = PRIVATE / account / "monitor_heartbeat.json"
    if not p.exists():
        return {"alive": False, "note": "規則巡邏沒有心跳檔（沒在跑或還沒更新過）"}
    h = json.loads(p.read_text(encoding="utf-8"))
    age = time.time() - h["epoch"]
    return {"alive": age < 120, "age_s": int(age), "last": h["at"], "session": h.get("session"), "blind": h.get("blind") or {},
            "note": "" if age < 120 else "規則巡邏超過 2 分鐘沒更新"}


def build(account):
    cfg = load_config()
    ledger = PRIVATE / account / "ledger.jsonl"
    if account not in ACCOUNTS or not ledger.exists():
        return {"error": f"找不到 {account} 的帳本"}
    desk = Desk(ledger, account, cfg)
    st = desk.state
    ev = desk.ledger.events()
    now = datetime.now(sources.TW).replace(microsecond=0)
    m = cfg["multiplier"]
    rows = live_rows(now)
    chain = None
    if rows:
        chain = sm.chain_from_snapshot(sm.build_snapshot(now, account, None, None, [], rows), cfg["quote_validity"])

    positions, unreal_total, stale_any = [], 0.0, False
    for g in st.groups.values():
        legs = g["legs"]
        base = max((lg["lots"] for lg in legs if lg["side"] == "sell"), default=1)
        gross = sum((1 if lg["side"] == "sell" else -1) * lg["px"] * lg["lots"] for lg in legs)     # 收到的淨權利金點數(總口數)
        width = max(lg["strike"] for lg in legs) - min(lg["strike"] for lg in legs)
        if chain:
            cost, why = chain.close_cost([{**lg, "expiry": g["expiry"]} for lg in legs])
        else:
            cost, why = None, "沒有即時報價"
        if cost is None:
            cost_pts, unreal, stale = None, None, True
            stale_any = True
        else:
            cost_pts = cost / base
            unreal = g["open_cash"] - cost * m              # 含開倉費用、未扣平倉費用
            unreal_total += unreal
            stale = False
        ep = g["exit_plan"] or {}
        positions.append({
            "gid": g["gid"], "expiry": g["expiry"], "structure": g["structure"], "tag": g["strategy_tag"],
            "legs": [{"side": lg["side"], "cp": lg["cp"], "strike": lg["strike"], "lots": lg["lots"], "px": lg["px"]} for lg in legs],
            "credit_pts": gross / base, "width": width, "max_loss": max(0.0, width * base * m - gross * m), "max_gain": gross * m,
            "close_cost_pts": cost_pts, "unrealized": unreal, "stale_reason": why if stale else None,
            "stop_debit_pts": ep.get("stop_debit_pts"), "take_profit_debit_pts": ep.get("take_profit_debit_pts"),
            "hold_to_settlement": bool(ep.get("hold_to_settlement")), "approx": g["approx"],
            "blind": (heartbeat(account).get("blind") or {}).get(g["gid"]) if stale else None})
    orders = [{"oid": o["oid"], "expiry": o["expiry"], "direction": o["direction"], "short": o["short_strike"], "long": o["long_strike"],
               "remaining": o["remaining"], "min_credit_pts": o["min_credit_pts"],
               "valid_until": datetime.fromtimestamp(o["valid_until"], sources.TW).isoformat(timespec="minutes")} for o in st.resting()]
    decisions = []
    for e in ev:
        if e["type"] == "DECISION":
            d = e["decision"]
            decisions.append({"id": e["decision_id"], "kind": "decision", "at": d.get("decided_at"), "action": d.get("action"),
                              "structure": d.get("structure") or d.get("strategy_tag"), "thesis": d.get("thesis"),
                              "invalidation": d.get("invalidation"), "exit_plan": d.get("exit_plan"), "manual_ref": d.get("manual_ref"),
                              "legs": d.get("legs") or d.get("side_sets")})
        elif e["type"] == "NO_DECISION":
            decisions.append({"id": e["decision_id"], "kind": "no_decision", "at": e.get("at"), "reasons": e["reasons"]})
        elif e["type"] == "REJECT":
            d = e.get("decision") or {}
            decisions.append({"id": e["decision_id"], "kind": "reject", "at": d.get("decided_at"), "reasons": e["reasons"]})
    links = {e["decision_id"]: e for e in ev if e["type"] == "SNAPSHOT_LINK"}
    fills = {e["decision_id"]: e for e in ev if e["type"] == "FILL"}
    for d in decisions:
        if d["id"] in links:
            d["snapshot"] = links[d["id"]]["snapshot"]
            d["sha256"] = links[d["id"]]["sha256"][:12]
        f = fills.get(d["id"])
        if f:
            d["fill"] = {"gid": f["gid"], "cash_delta": f["cash_delta"], "fees": f["fees"], "approx": f["approx"]}
    notes = []
    for f in sorted((PRIVATE / account / "notes").glob("*.md"), reverse=True)[:4]:
        txt = f.read_text(encoding="utf-8")
        notes.append({"file": f.name, "title": txt.splitlines()[0].lstrip("# ").strip() if txt else f.name, "text": txt})
    r = cfg["risk"]
    live_equity = st.equity() if stale_any else st.capital + st.realized + unreal_total
    hw = max(st.high_water, live_equity)
    today = now.date().isoformat()
    day_start = st.day_start_equity.get(today, st.last_equity)
    margin = st.margin_used()
    lots_by_side = {}
    for p_ in positions:
        for lg in p_["legs"]:
            if lg["side"] == "sell":
                lots_by_side[lg["cp"]] = lots_by_side.get(lg["cp"], 0) + lg["lots"]
    return {
        "account": account, "simulated": True, "as_of": now.isoformat(), "session": sm.session_of(now),
        "capital": st.capital, "cash": st.cash, "equity": live_equity, "equity_is_live": not stale_any,
        "unrealized": unreal_total, "realized": st.realized, "fees_total": st.fees_total,
        "return_pct": 100 * (live_equity - st.capital) / st.capital,
        "high_water": hw, "drawdown_pct": 100 * (hw - live_equity) / hw, "dd_lock": st.dd_lock,
        "day_pnl": live_equity - day_start,
        "margin_used": margin, "margin_util_pct": 100 * margin / live_equity if live_equity else 0,
        "limits": {"daily_loss_stop_pct": r["daily_loss_stop_pct"], "drawdown_halve_pct": r["drawdown_halve_pct"],
                   "drawdown_halt_pct": r["drawdown_halt_pct"], "margin_util_max_pct": r["margin_util_max_pct"],
                   "ladder_max_lots_per_side": r["ladder_max_lots_per_side"], "max_ladder_sets": r["max_ladder_sets"],
                   "one_side_loss_pct": r["ladder_one_side_max_loss_pct"], "both_sides_loss_pct": r["ladder_both_sides_max_loss_pct"]},
        "short_lots": lots_by_side, "active_expiries": sorted(st.active_expiries()),
        "notes": notes, "positions": positions, "orders": orders, "decisions": list(reversed(decisions))[:40],
        "no_decision_count": sum(1 for e in ev if e["type"] == "NO_DECISION"),
        "closed": list(reversed(st.closed))[:40],
        "review_flags": [e for e in ev if e["type"] == "REVIEW_FLAG"],
        "ledger_ok": desk.ledger.verify()[0], "events": len(ev),
        "monitor": heartbeat(account), "fill_validated": cfg["fill"]["validated"]}


class H(BaseHTTPRequestHandler):
    def _ok_host(self):
        return (self.headers.get("Host") or "").split(":")[0] in ALLOWED_HOSTS

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if not self._ok_host():
            return self._send(403, {"error": "host not allowed"})
        path, _, qs = self.path.partition("?")
        if path in ("/", "/index.html"):
            return self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/desk":
            acct = dict(x.split("=", 1) for x in qs.split("&") if "=" in x).get("account", "T0")
            try:
                return self._send(200, build(acct))
            except Exception as e:  # noqa: BLE001
                return self._send(500, {"error": str(e)})
        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    print(f"台選鳥帳戶頁 http://127.0.0.1:{port}/  （唯讀；Ctrl+C 結束）", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
