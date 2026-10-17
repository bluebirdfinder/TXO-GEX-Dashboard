"""Night anchoring: walls follow the anchor price; wall_extra widens only the wall search; Max Pain is anchor-independent."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_and_calc_vision as f

def chain():
    c = {}
    for k in range(44000, 49050, 50):
        c[float(k)] = {'call_oi_mth': 100, 'put_oi_mth': 100}
    c[48000.0]['call_oi_mth'] = 5000   # big call far above a night anchor of 46,140 (outside +/-900 of 46,100)
    c[46000.0]['put_oi_mth'] = 4000
    return c

def run(anchor, extra):
    return f.calculate_true_gex_profile(anchor, chain(), 3, 5, 4, wall_extra=extra)

def main():
    a0 = run(46140.0, 0); a1 = run(46140.0, 1500)
    assert a1['call_wall_strike'] >= 46140 >= a1['put_wall_strike'], a1
    assert a1['call_wall_strike'] == 48000.0, a1['call_wall_strike']      # widened search finds it
    assert a0['call_wall_strike'] != 48000.0                              # default window cannot
    print("PASS wall_extra widens wall search only")
    assert len(a0['total_gex']) == len(a1['total_gex']), "chart window must not change"
    print("PASS chart window unchanged")
    d = run(47111.26, 0)
    assert d['max_pain_strike'] == a1['max_pain_strike'] == a0['max_pain_strike']
    print("PASS Max Pain independent of anchor/window")
    assert a1['put_wall_strike'] == 46000.0, a1['put_wall_strike']
    print("PASS Put Wall below anchor")
    print("ALL PASS")
main()
