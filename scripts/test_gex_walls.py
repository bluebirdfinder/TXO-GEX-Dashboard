"""Self-test for the Call Wall / Put Wall definition in fetch_and_calc_vision.calculate_true_gex_profile.
Call Wall must be the largest Call GEX strike at/above spot, Put Wall the largest |Put GEX| strike at/below spot; the old
unrestricted maxima are kept as call_gex_peak_strike / put_gex_peak_strike. Run: python scripts/test_gex_walls.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_and_calc_vision as v  # noqa: E402

ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok = ok and cond


def chain(spec):
    """spec: {strike: (call_oi, put_oi)} -> monthly-bucket-only chain."""
    out = {}
    for k, (c, p) in spec.items():
        out[float(k)] = {"call_oi_w1": 0, "put_oi_w1": 0, "call_oi_w2": 0, "put_oi_w2": 0,
                         "call_oi_fri": 0, "put_oi_fri": 0, "call_oi_mth": c, "put_oi_mth": p}
    return out


def prof(spot, spec):
    return v.calculate_true_gex_profile(spot, chain(spec), 3, 3, 12, fixed_base_strike=round(spot / 100) * 100)


# 10/16 situation: a huge Call OI sits deep in the money (46300) while spot is 47111
spec = {46200: (3000, 2000), 46300: (60000, 1000), 46500: (2000, 4000), 47000: (6000, 30000),
        47200: (5000, 4000), 47500: (3000, 3000), 48000: (12000, 2000)}
p = prof(47111.0, spec)
check("old behaviour kept as call_gex_peak_strike (deep ITM strike)", p["call_gex_peak_strike"] == 46300)
check("Call Wall is now above spot", p["call_wall_strike"] >= 47111 and p["call_wall_strike"] == 48000)
check("Put Wall is below spot", p["put_wall_strike"] <= 47111 and p["put_wall_strike"] == 47000)
check("Call Wall is not below Put Wall", p["call_wall_strike"] >= p["put_wall_strike"])
check("put peak keeps old definition", p["put_gex_peak_strike"] == 47000)

# normal day: the peaks are already on the right side -> both definitions agree
spec2 = {47000: (1000, 20000), 47500: (2000, 3000), 48000: (25000, 1000)}
p2 = prof(47400.0, spec2)
check("normal day: Call Wall == peak", p2["call_wall_strike"] == p2["call_gex_peak_strike"] == 48000)
check("normal day: Put Wall == peak", p2["put_wall_strike"] == p2["put_gex_peak_strike"] == 47000)

# spot below all heavy call strikes / above all heavy put strikes still gives sane sides
p3 = prof(46000.0, {46500: (9000, 100), 47000: (500, 100), 45800: (100, 8000)})
check("spot far below: Call Wall above, Put Wall below", p3["call_wall_strike"] >= 46000 and p3["put_wall_strike"] <= 46000)

# an empty chain (real fetch failed) must not raise and the walls stay on their own side of spot
p4 = v.calculate_true_gex_profile(47100.0, {}, 3, 3, 12, fixed_base_strike=47100)
check("empty chain: no exception, Call Wall >= spot >= Put Wall", p4["call_wall_strike"] >= 47100 >= p4["put_wall_strike"])

print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
