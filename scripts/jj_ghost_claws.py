"""
jj_ghost_claws.py - line-by-line port of the user's own Pine Script "JJ Indicator V4.1 - Ghost Claws Master"
(all 8 signals: 🐣一般藍鳥 🐦強力藍鳥 ✈️弱火箭 🚀強火箭 ⚡動能再啟 🛸強力再啟 💰錢袋減碼 ⚠️警告出清).

Source of truth = the Pine code (pasted by the user 2026-09-27); this file must stay 1:1 with it. Pure Python so the
GitHub Actions job and the screener need no numpy/pandas. Pine semantics reproduced on purpose:
  * ta.ema seeds with the SMA of the first `length` values; ta.rma likewise (alpha = 1/length)
  * ta.dmi(len, len): Wilder RMA of TR / +DM / -DM, ADX = RMA of |+DI - -DI| / (+DI + -DI)
  * ta.mfi(hlc3, len): rsi-style ratio of volume*hlc3 flows split by the sign of change(hlc3)
  * `na` comparisons are false; `strength_grade` keeps its initial "C" when ADX >= strong threshold but close <= MA7
    (none of Pine's else-if branches matches) — reproduced exactly, not "fixed"
  * `exit_trigger = exit_state and not exit_state[1]`, `is_holding` / `reduce_count` / `just_reduced_in_wave` are
    `var` state replayed over the whole bar history

Known limitation (data, not logic): the screener only has ~120 daily bars per symbol, so the replayed `is_holding` state
and the slow ADX/EMA warm-up can differ from TradingView, which replays thousands of bars.
"""
import math

MFI_LEN = 14
ADX_LEN = 14
LEN7, LEN17, LEN88 = 7, 17, 88
FAST, SLOW, SIG = 12, 26, 9
BB_LEN = 20
USE_RESTART = True


def jj_params(symbol, asset_type="stock"):
    """Auto-mode thresholds for Taiwan stocks / ETFs (the Pine `asset_class` router)."""
    t = str(symbol or "").upper()
    if str(asset_type).lower() == "etf":
        if t.endswith("L"):
            return {"bias_pos": 12.0, "bias_neg": 12.0, "mfi": 50.0, "adx": 22.0, "asset_class": "台股槓桿 ETF (正2)"}
        if t.endswith("R"):
            return {"bias_pos": 5.0, "bias_neg": 5.0, "mfi": 52.0, "adx": 20.0, "asset_class": "台股反向 ETF (反1)"}
        if t.endswith("U"):
            return {"bias_pos": 8.0, "bias_neg": 8.0, "mfi": 50.0, "adx": 22.0, "asset_class": "台股期貨/商品 ETF"}
        if t.endswith("A"):
            return {"bias_pos": 8.0, "bias_neg": 8.0, "mfi": 52.0, "adx": 20.0, "asset_class": "台股主動型 ETF"}
        if t.endswith("B"):
            return {"bias_pos": 3.0, "bias_neg": 3.0, "mfi": 55.0, "adx": 20.0, "asset_class": "台股債券 ETF"}
    return {"bias_pos": 8.0, "bias_neg": 8.0, "mfi": 52.0, "adx": 20.0, "asset_class": "台股個股與一般ETF"}


# ---------- Pine series helpers (None == na) ----------
def sma(vals, n):
    out = [None] * len(vals)
    for i in range(n - 1, len(vals)):
        w = vals[i - n + 1:i + 1]
        if all(v is not None for v in w):
            out[i] = sum(w) / n
    return out


def ema(vals, n):
    """Pine ta.ema: first value = SMA of the first n non-na values, then alpha = 2/(n+1)."""
    a = 2.0 / (n + 1)
    out = [None] * len(vals)
    prev = None
    for i, v in enumerate(vals):
        if v is None:
            continue
        if prev is None:
            window = [x for x in vals[max(0, i - n + 1):i + 1]]
            if len(window) == n and all(x is not None for x in window):
                prev = sum(window) / n
                out[i] = prev
        else:
            prev = a * v + (1 - a) * prev
            out[i] = prev
    return out


def rma(vals, n):
    """Pine ta.rma: alpha = 1/n, seeded with the SMA of the first n non-na values."""
    out = [None] * len(vals)
    prev = None
    for i, v in enumerate(vals):
        if v is None:
            continue
        if prev is None:
            window = vals[max(0, i - n + 1):i + 1]
            if len(window) == n and all(x is not None for x in window):
                prev = sum(window) / n
                out[i] = prev
        else:
            prev = (prev * (n - 1) + v) / n
            out[i] = prev
    return out


def mfi(highs, lows, closes, vols, n):
    hlc3 = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]
    up, dn = [None], [None]
    for i in range(1, len(hlc3)):
        ch = hlc3[i] - hlc3[i - 1]
        up.append(0.0 if ch <= 0 else vols[i] * hlc3[i])
        dn.append(0.0 if ch >= 0 else vols[i] * hlc3[i])
    out = [None] * len(hlc3)
    for i in range(n, len(hlc3)):
        u, d = sum(up[i - n + 1:i + 1]), sum(dn[i - n + 1:i + 1])
        out[i] = 100.0 if d == 0 else (0.0 if u == 0 else 100.0 - 100.0 / (1.0 + u / d))
    return out


def dmi_adx(highs, lows, closes, n):
    """Pine ta.dmi(n, n) -> adx series."""
    L = len(closes)
    tr, pdm, mdm = [None] * L, [None] * L, [None] * L
    for i in range(1, L):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        up, down = highs[i] - highs[i - 1], -(lows[i] - lows[i - 1])
        pdm[i] = up if (up > down and up > 0) else 0.0
        mdm[i] = down if (down > up and down > 0) else 0.0
    trur, p, m = rma(tr, n), rma(pdm, n), rma(mdm, n)
    dx = [None] * L
    for i in range(L):
        if trur[i] is None or p[i] is None or m[i] is None or trur[i] == 0:
            continue
        plus, minus = 100.0 * p[i] / trur[i], 100.0 * m[i] / trur[i]
        s = plus + minus
        dx[i] = abs(plus - minus) / (1.0 if s == 0 else s) * 100.0
    return rma(dx, n)


def _gt(a, b):
    return a is not None and b is not None and a > b


def _lt(a, b):
    return a is not None and b is not None and a < b


def _ge(a, b):
    return a is not None and b is not None and a >= b


def _le(a, b):
    return a is not None and b is not None and a <= b


NAMES = ("normal_bird", "strong_bird", "weak_rocket", "strong_rocket",
         "restart_normal", "restart_strong", "reduce", "exit")


def compute_jj_series(bars, params):
    """Replay the whole history. Returns {'signals': {name: [bool per bar]}, 'grade': [...], plus indicator series}."""
    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    vols = [b.get("volume", 0) for b in bars]
    L = len(bars)

    ma7, ma17, ma88 = sma(closes, LEN7), sma(closes, LEN17), sma(closes, LEN88)
    bb_basis = sma(closes, BB_LEN)
    macd = [None if (a is None or b is None) else a - b for a, b in zip(ema(closes, FAST), ema(closes, SLOW))]
    sig = ema(macd, SIG)
    hist = [None if (m is None or s is None) else m - s for m, s in zip(macd, sig)]
    mfi_v = mfi(highs, lows, closes, vols, MFI_LEN)
    adx_v = dmi_adx(highs, lows, closes, ADX_LEN)
    bias88 = [None if (m is None or m == 0) else (c - m) / m * 100.0 for c, m in zip(closes, ma88)]

    adx_th, mfi_th = params["adx"], params["mfi"]
    bias_neg = params["bias_neg"]
    adx_strong = adx_th + 10.0

    out = {n: [False] * L for n in NAMES}
    grade = ["C"] * L
    is_holding, reduce_count, just_reduced = False, 0, False
    prev_exit_state = False  # exit_state[1]

    for i in range(L):
        h0 = hist[i]
        h1 = hist[i - 1] if i >= 1 else None
        h2 = hist[i - 2] if i >= 2 else None
        h3 = hist[i - 3] if i >= 3 else None
        a0 = adx_v[i]

        is_bull = _gt(ma17[i], ma88[i])
        is_above_bb = _gt(closes[i], bb_basis[i])
        is_below_bb = _lt(closes[i], bb_basis[i])

        g = "C"
        if is_bull:
            if _ge(a0, adx_strong) and _gt(closes[i], ma7[i]):
                g = "S"
            elif _ge(a0, adx_th) and _lt(a0, adx_strong):
                g = "A"
            elif _lt(a0, adx_th):
                g = "B"
        grade[i] = g

        cross_up_hist = h1 is not None and h0 is not None and h1 <= 0 < h0          # ta.crossover(hist, 0)
        cond_bird = cross_up_hist and is_bull and is_above_bb
        is_strong_bird = cond_bird and _le(bias88[i], -bias_neg)
        is_normal_bird = cond_bird and _gt(bias88[i], -bias_neg)

        m17p, m88p = (ma17[i - 1], ma88[i - 1]) if i >= 1 else (None, None)
        cross_up_ma = (m17p is not None and m88p is not None and ma17[i] is not None and ma88[i] is not None
                       and m17p <= m88p and ma17[i] > ma88[i])                          # ta.crossover(ma17, ma88)
        cond_rocket = cross_up_ma and _gt(h0, 0)
        is_strong_rocket = cond_rocket and _gt(mfi_v[i], mfi_th)
        is_weak_rocket = cond_rocket and _le(mfi_v[i], mfi_th)

        macd_was_cooling = _lt(h1, h2) and _lt(h2, h3)
        macd_now_turning = _gt(h0, h1) and _gt(h0, 0)

        if _gt(h0, h1):
            just_reduced = False

        cond_restart_base = (USE_RESTART and macd_was_cooling and macd_now_turning and is_bull and _gt(a0, adx_th)
                             and is_holding and not cond_bird and not cond_rocket)
        ma7_bounce = (i >= 1 and ma7[i - 1] is not None and lows[i - 1] <= ma7[i - 1] * 1.01) and _gt(closes[i], ma7[i])
        is_restart_strong = cond_restart_base and ma7_bounce
        is_restart_normal = cond_restart_base and not ma7_bounce

        if cond_bird or cond_rocket:
            is_holding, reduce_count, just_reduced = True, 0, False
        if is_restart_strong or is_restart_normal:
            reduce_count = 0

        ma7_crossunder = (i >= 1 and ma7[i] is not None and ma7[i - 1] is not None
                          and closes[i - 1] >= ma7[i - 1] and closes[i] < ma7[i])       # ta.crossunder(close, ma7)
        reduce_cond_ma7 = (g == "S") and ma7_crossunder and is_holding
        reduce_cond_macd = False
        if g == "S":
            reduce_cond_macd = _gt(h0, 0) and _lt(h0, h1) and _lt(h1, h2) and _lt(h2, h3) and is_bull
        elif g in ("A", "B"):
            reduce_cond_macd = _gt(h0, 0) and _lt(h0, h1) and _lt(h1, h2) and is_bull
        max_reduce = 3 if g == "S" else 2
        trigger_reduce_macd = reduce_cond_macd and is_holding and reduce_count < max_reduce and not just_reduced
        trigger_reduce = trigger_reduce_macd or reduce_cond_ma7
        if trigger_reduce_macd:
            reduce_count += 1
            just_reduced = True
        elif reduce_cond_ma7:
            reduce_count += 1

        if _lt(a0, adx_th):
            exit_state = _lt(h0, 0)
        elif _ge(a0, adx_th) and _lt(a0, adx_strong):
            exit_state = _lt(h0, 0) and is_below_bb
        else:
            exit_state = _lt(h0, 0) and is_below_bb and _lt(closes[i], ma17[i])
        # note: with na ADX Pine falls to the last branch (none of the comparisons is true) — same here
        exit_trigger = exit_state and not prev_exit_state
        trigger_exit = exit_trigger and is_holding
        prev_exit_state = exit_state
        if trigger_exit:
            is_holding = False

        for name, val in zip(NAMES, (is_normal_bird, is_strong_bird, is_weak_rocket, is_strong_rocket,
                                     is_restart_normal, is_restart_strong, trigger_reduce, trigger_exit)):
            out[name][i] = bool(val)

    return {"signals": out, "grade": grade, "hist": hist, "adx": adx_v, "mfi": mfi_v, "bias88": bias88,
            "ma7": ma7, "ma17": ma17, "ma88": ma88}


def compute_jj_last(bars, params):
    """Signals on the LAST bar (what the daily screener shows) + a few indicator values for the UI."""
    if not bars or len(bars) < LEN88 + 1:
        return None
    s = compute_jj_series(bars, params)
    last = {k: v[-1] for k, v in s["signals"].items()}
    last["grade"] = s["grade"][-1]
    last["adx"], last["mfi"], last["bias88"] = s["adx"][-1], s["mfi"][-1], s["bias88"][-1]
    return last
