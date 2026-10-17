"""結算日 13:30 後，已結算合約必須被剔除（牆位／Gamma Flip／到期組成／Max Pain 共用同一份 bucket）。"""
import datetime, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_and_calc_vision as f

tz = datetime.timezone(datetime.timedelta(hours=8))
d = {c: {'expiry': e, 'call': {}, 'put': {}} for c, e in
     [('202610F3', '20261016'), ('202610', '20261021'), ('202610F4', '20261023'), ('202610W4', '20261028')]}
ok = True
for h, m, want_fri in [(10, 0, '202610F3'), (13, 29, '202610F3'), (13, 30, '202610F4'), (16, 0, '202610F4')]:
    got = f.classify_txo_contract_buckets(d, now=datetime.datetime(2026, 10, 16, h, m, tzinfo=tz))['fri']
    good = got == want_fri
    ok &= good
    print('PASS' if good else 'FAIL', f'10/16 {h:02d}:{m:02d} fri bucket = {got}')
print('ALL PASS' if ok else 'FAILED')
sys.exit(0 if ok else 1)
