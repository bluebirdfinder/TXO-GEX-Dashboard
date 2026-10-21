"""選擇權鏈為空（期交所抓取失敗）時，不可發布全 0 剖面；應沿用上一份正常 GEX 欄位並標記 stale。"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_and_calc_vision as f

ok = True
def chk(name, cond):
    global ok
    ok &= bool(cond); print('PASS' if cond else 'FAIL', name)

zero = f.calculate_true_gex_profile(47000, {}, 3, 3, 7, with_standard=True)
good = {"total_gex": [{"strike": 47000}], "weekly_gex": [1], "friday_gex": [1], "monthly_gex": [1],
        "zero_gamma_level": 46900.0, "gex_plus_flip": 46950.0, "gamma_flip_standard": 46800.0, "total_vex": 5.0,
        "total_gex_val": 123.4, "total_gex_plus": 130.0, "call_wall_strike": 48000.0, "put_wall_strike": 47000.0,
        "call_gex_peak_strike": 46300.0, "put_gex_peak_strike": 47000.0, "max_pain_strike": 46500.0, "pc_ratio": 70.0}
with tempfile.TemporaryDirectory() as d:
    json.dump(good, open(os.path.join(d, 'gex_data.json'), 'w'))
    out, carried = f.carry_forward_gex_profile(zero, data_dir=d)
    chk('carried from previous good file', carried)
    chk('walls restored', out['call_wall_strike'] == 48000.0 and out['put_wall_strike'] == 47000.0)
    chk('gamma_flip_standard restored (not None)', out['gamma_flip_standard'] == 46800.0)
    chk('stale flag set', out['gex_chain_stale'] is True)
    # 上一份本身是垃圾（總 GEX 0）→ 不沿用
    bad = dict(good, total_gex_val=0.0, total_gex=[])
    json.dump(bad, open(os.path.join(d, 'gex_data.json'), 'w'))
    out2, carried2 = f.carry_forward_gex_profile(zero, data_dir=d)
    chk('does not carry a garbage previous file', not carried2 and out2 is zero or (not carried2))
with tempfile.TemporaryDirectory() as d:
    out3, carried3 = f.carry_forward_gex_profile(zero, data_dir=d)
    chk('missing previous file -> no carry, no exception', not carried3)
print('ALL PASS' if ok else 'FAILED'); sys.exit(0 if ok else 1)
