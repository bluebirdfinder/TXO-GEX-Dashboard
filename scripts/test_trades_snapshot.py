"""get_recent_trades must survive concurrent appends (deque mutated during iteration)."""
import sys, threading, time
from collections import deque
sys.path.insert(0, __file__.rsplit('scripts', 1)[0] + 'scripts')
import fubon_api_provider as fp

class Stub:
    get_recent_trades = fp.FubonApiProvider.get_recent_trades if hasattr(fp, 'FubonApiProvider') else None

def main():
    cls = next(v for v in vars(fp).values() if isinstance(v, type) and hasattr(v, 'get_recent_trades'))
    o = cls.__new__(cls)
    o.trades_log = {'X': deque(({'ts': i, 'size': 1, 'side': 'buy', 'price': 1} for i in range(5000)), maxlen=5000)}
    stop = False
    def writer():
        i = 5000
        while not stop:
            o.trades_log['X'].append({'ts': i, 'size': 1, 'side': 'buy', 'price': 1}); i += 1
    t = threading.Thread(target=writer, daemon=True); t.start()
    errs = 0
    end = time.time() + 3
    while time.time() < end:
        try:
            r = o.get_recent_trades('X', since_ts=0)
            assert len(r) > 0
        except RuntimeError:
            errs += 1
    stop = True
    assert errs == 0, f"{errs} RuntimeError"
    print("PASS concurrent append: no RuntimeError")
    print("ALL PASS")
main()
