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
hang.set()
os._exit = real_exit
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
