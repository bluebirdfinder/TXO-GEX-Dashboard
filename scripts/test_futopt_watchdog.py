import sys, time, threading, os, logging
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
import fubon_api_provider as m

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok = ok and cond


# 1) _timed_lock
lk = threading.Lock()
with m._timed_lock(lk, 0.2) as got:
    check("timed_lock acquires free lock", got is True)
lk.acquire()
t0 = time.time()
with m._timed_lock(lk, 0.3) as got:
    check("timed_lock gives up on held lock", got is False and 0.25 < time.time() - t0 < 1.0)
lk.release()

# 2) _call_with_timeout
check("call_with_timeout returns value", m._call_with_timeout(lambda: 7, 1) == 7)
t0 = time.time()
check("call_with_timeout times out on hang", m._call_with_timeout(lambda: time.sleep(5), 0.4) == "timeout" and time.time() - t0 < 1.5)
try:
    m._call_with_timeout(lambda: (_ for _ in ()).throw(ValueError("boom")), 1)
    check("call_with_timeout re-raises", False)
except ValueError:
    check("call_with_timeout re-raises", True)

# 3) watchdog: hung reconnect must not block, then escalate
cls = [v for k, v in vars(m).items() if isinstance(v, type) and hasattr(v, "futopt_watchdog")][0]
p = cls.__new__(cls)
p.is_active = True
p._sub_modes = {("books", "X", False)}
p._futopt_watchdog_last_try = 0.0
p._futopt_watchdog_fires = 0
p._last_trades_ts = {}
p._last_futopt_msg_ts = 1.0
p._proc_start_ts = time.time() - 3600
p._futopt_ws = None
p._in_taifex_trading_window = lambda now_ts=None: True
p.feed_age_sec = lambda: 999.0
hang = threading.Event()
p._on_futopt_disconnect = lambda c, mm: hang.wait(30)   # simulates a wedged reconnect
exits = []
real_exit = os._exit
os._exit = lambda code: exits.append(code)
t0 = time.time()
r1 = p.futopt_watchdog(stale_after=180, cooldown=300)
check("watchdog returns immediately although reconnect hangs", r1 is True and time.time() - t0 < 1.0 and p._futopt_watchdog_fires == 1)
p._futopt_watchdog_last_try = time.time() - 100   # < 150s since the forced reconnect: no escalation yet
r2 = p.futopt_watchdog(stale_after=180, cooldown=300)
check("no self-exit before 150s", exits == [])
p._futopt_watchdog_last_try = time.time() - 160   # > 150s, still stale -> escalate
p.futopt_watchdog(stale_after=180, cooldown=300)
check("self-exit (code 3) when still stale 150s after forced reconnect", exits == [3])
# uptime guard: a freshly started process must not self-exit
exits.clear()
p._proc_start_ts = time.time() - 60
p._futopt_watchdog_last_try = time.time() - 160
p.futopt_watchdog(stale_after=180, cooldown=300)
check("no self-exit within first 10 min of uptime", exits == [])
# healthy feed resets counter
p.feed_age_sec = lambda: 5.0
p.futopt_watchdog()
check("healthy feed resets fires counter", p._futopt_watchdog_fires == 0)

# 4) trades-channel watchdog: books alive, TXF trades silent -> forced reconnect; then escalation
import datetime
Cls = cls
q = Cls.__new__(Cls)
q.is_active = True
q._sub_modes = {("books", "TXF1!", False), ("trades", "TXF1!", False)}
q._futopt_watchdog_last_try = 0.0
q._futopt_watchdog_fires = 0
q._last_futopt_msg_ts = time.time()
q._proc_start_ts = time.time() - 7200
q._futopt_ws = None
q._in_taifex_trading_window = lambda now_ts=None: True
q.feed_age_sec = lambda: 1.0                       # books are fresh
q._last_trades_ts = {"TXF1!": time.time() - 30}    # a trade 30 s ago -> healthy
rec = []
q._on_futopt_disconnect = lambda c, mm: rec.append((c, mm))
os._exit = lambda code: exits.append(code)
exits.clear()
check("healthy trades -> watchdog does nothing", q.futopt_watchdog() is False and not q._trades_channel_dead())
q._last_trades_ts = {"TXF1!": time.time() - 900}   # no trade for 15 min while books are fresh
check("silent trades channel detected", q._trades_channel_dead() is True)
fired = q.futopt_watchdog()
time.sleep(0.3)
check("trades dead + books alive -> forced reconnect", fired is True and rec and rec[0][0] == "watchdog")
q._futopt_watchdog_last_try = time.time() - 160
q.futopt_watchdog()
check("still silent 150s after reconnect -> self-exit", exits == [3])
exits.clear()
q._last_trades_ts = {"TXF1!": time.time()}         # trades resumed
q._futopt_watchdog_last_try = time.time() - 160
check("trades resumed -> no action, counter reset", q.futopt_watchdog() is False and q._futopt_watchdog_fires == 0 and exits == [])
# symbol not subscribed for trades -> never 'dead'
q._sub_modes = {("books", "TXF1!", False)}
q._last_trades_ts = {}
check("no trades subscription -> not dead", q._trades_channel_dead() is False)
# session opened < 10 min ago -> not dead yet (window 10 min ago was closed)
q._sub_modes = {("trades", "TXF1!", False)}
q._in_taifex_trading_window = lambda now_ts=None: now_ts is None   # only 'now' is inside a session
check("session just opened -> grace period", q._trades_channel_dead() is False)

# 5) holiday-aware trading window (real class method, temp holiday file)
import tempfile
hf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
hf.write('{"holidays": ["2026-10-09"]}')
hf.close()
Cls._HOLIDAY_FILE = hf.name
Cls._holiday_cache = (None, frozenset())
tz = Cls._TAIPEI_TZ
def ts(y, mo, d, h, mi):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=tz).timestamp()
W = Cls._in_taifex_trading_window
check("Thu 10/8 10:00 day session open", W(ts(2026, 10, 8, 10, 0)) is True)
check("Thu 10/8 22:00 night session open (evening before a holiday still trades)", W(ts(2026, 10, 8, 22, 0)) is True)
check("Fri 10/9 02:00 night session continues after Thu evening", W(ts(2026, 10, 9, 2, 0)) is True)
check("Fri 10/9 10:00 holiday -> closed", W(ts(2026, 10, 9, 10, 0)) is False)
check("Fri 10/9 16:00 holiday -> no night session", W(ts(2026, 10, 9, 16, 0)) is False)
check("Sat 10/10 02:00 (previous day was a holiday) -> closed", W(ts(2026, 10, 10, 2, 0)) is False)
check("Mon 10/12 10:00 open again", W(ts(2026, 10, 12, 10, 0)) is True)
check("Sat 10/10 10:00 weekend closed", W(ts(2026, 10, 10, 10, 0)) is False)
check("Wed 14:30 gap between sessions closed", W(ts(2026, 10, 14, 14, 30)) is False)
check("Wed 05:30 gap closed", W(ts(2026, 10, 14, 5, 30)) is False)
Cls._HOLIDAY_FILE = "does-not-exist.json"
Cls._holiday_cache = (None, frozenset())
check("missing holiday file -> falls back to weekday rule", W(ts(2026, 10, 9, 10, 0)) is True)
os.unlink(hf.name)

# 6) cumulative 'total' block of trades frames is kept and written into the 15 s raw snapshot
import collections, json, tempfile as _tf
z = Cls.__new__(Cls)
z._trades_logged_raw = set()
z._trades_last_serial = {}
z._last_trades_ts = {}
z._trades_total = {}
z.books_cache = {}
z.trades_log = {}
z.cvd_session_start = {}
z.cvd_cumulative = {}
z.cvd_points = {}
z._TRADES_LOG_MAXLEN = 100
z._taifex_session_start_ts = lambda now: 0
z._process_trades_data({'symbol': 'TXFJ6', 'trades': [{'price': 100, 'size': 2, 'bid': 99, 'ask': 100}],
                        'total': {'tradeVolume': 4345, 'totalBidMatch': 3064, 'totalAskMatch': 3163}, 'serial': 1}, alias='TXF1!')
check("trades frame 'total' stored", z._trades_total.get('TXF1!', {}).get('totalBidMatch') == 3064 and z._trades_total['TXF1!']['totalAskMatch'] == 3163)
with _tf.TemporaryDirectory() as d:
    z._mom_hist_dir = d
    z.get_recent_trades = lambda alias, since_ts=None: []
    z._append_raw_snapshot('TXF1!', time.time(), {'bids': [{'price': 99, 'size': 1}], 'asks': [{'price': 100, 'size': 1}]})
    row = json.loads(open([os.path.join(d, f) for f in os.listdir(d)][0], encoding="utf-8").readline())
    check("raw snapshot carries 'tot'", row.get('tot', {}).get('totalBidMatch') == 3064)
    z._append_raw_snapshot('NOPE1!', time.time(), {'bids': [], 'asks': []})
    last = [json.loads(l) for l in open([os.path.join(d, f) for f in os.listdir(d)][0], encoding="utf-8")][-1]
    check("raw snapshot without totals has no 'tot'", 'tot' not in last)
zb = Cls.__new__(Cls)
zb.books_cache = {}
zb._books_logged_raw = set()
zb._process_books_data({'symbol': 'TXFJ6', 'bids': [{'price': 1, 'size': 2}], 'asks': [{'price': 2, 'size': 3}], 'extra': 'x'}, alias='TXF1!')
check("books raw sample logged once", 'TXF1!' in zb._books_logged_raw and zb.books_cache['TXF1!']['bids'][0]['size'] == 2)

hang.set()
os._exit = real_exit
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
