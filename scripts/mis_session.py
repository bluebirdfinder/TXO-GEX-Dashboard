# -*- coding: utf-8 -*-
"""期交所 MIS 備援報價的場次判斷（純函式，無網路、無副作用，方便單元測試）。

2026-10-17：原本 live_price_server.mis_polling_worker 只看鐘點選日盤／夜盤清單（15:00~05:00 夜盤，其餘日盤），
週六 05:00 到週一 15:00 會查到日盤清單，回週五日盤收盤 47,242，而最近一個場次其實是週五夜盤收盤 46,140。
規則與 FubonAPIProvider._quote_session_mode 相同（週六 05:00 起到週一 08:45 前查夜盤）。
不含國定假日（與富邦那邊一致）。
"""

NIGHT_MARKET_TYPE = '1'
DAY_MARKET_TYPE = '0'

STALE_SECONDS = 300  # 開盤中，MIS 報價時間超過 5 分鐘沒更新就不當現價發布


def mis_market_type(now):
    """該查 MIS 的哪一份清單。夜盤='1'、日盤='0'。now 為台北本機時間 datetime。"""
    hm = now.hour * 60 + now.minute
    wd = now.weekday()  # Mon=0 … Sun=6
    if wd == 6 or (wd == 5 and hm >= 5 * 60):
        return NIGHT_MARKET_TYPE  # 週末：最近一個場次是週五夜盤
    if hm >= 15 * 60 or hm < 8 * 60 + 45:
        return NIGHT_MARKET_TYPE
    return DAY_MARKET_TYPE


def session_is_open(now):
    """此刻是否在交易時段內（日盤 08:45-13:45；夜盤 15:00-隔天 05:00，週一凌晨與週六 05:00 後休市）。"""
    hm = now.hour * 60 + now.minute
    wd = now.weekday()
    if 8 * 60 + 45 <= hm < 13 * 60 + 45:
        return wd <= 4
    if hm >= 15 * 60:
        return wd <= 4          # 週一~週五 15:00 起的夜盤
    if hm < 5 * 60:
        return 1 <= wd <= 5     # 週二~週六凌晨：前一晚夜盤的後半段
    return False


def mis_quote_is_stale(now, ctime):
    """開盤中且報價時間（MIS CTime，'HHMMSS'）距現在超過 STALE_SECONDS → True。
    休市時回 False（休市本來就是最近一個場次的收盤價）。CTime 缺漏或格式不對：開盤中視為過期（不發布）。"""
    if not session_is_open(now):
        return False
    try:
        s = str(ctime).strip().zfill(6)
        q_sec = int(s[0:2]) * 3600 + int(s[2:4]) * 60 + int(s[4:6])
    except (TypeError, ValueError):
        return True
    now_sec = now.hour * 3600 + now.minute * 60 + now.second
    age = (now_sec - q_sec) % 86400  # 跨午夜也成立
    return age > STALE_SECONDS


# ---- 期交所 MIS 1 分 K（getChartData1M）解析 ----
# 2026-10-20：盤中主圖缺「本盤別已過去的 K 棒」（富邦分 K 一天只抓兩次）。MIS 的 1 分 K 是官方即時資料，
# 列格式 [HHMMSS, O, H, L, C, V]：標籤＝K 棒「結束」時間；分鐘可寫成 60（例如 '226000'＝23:00:00）；沒有日期。
import datetime as _dt

_TPE = _dt.timezone(_dt.timedelta(hours=8))


def _label_seconds(s):
    s = str(s).strip().zfill(6)
    return int(s[0:2]) * 3600 + int(s[2:4]) * 60 + int(s[4:6])


def parse_mis_ticks(ticks, now):
    """MIS Ticks → 1 分 K 清單 [{time(epoch 秒，K 棒開始), open, high, low, close, volume}]，時間由舊到新。
    列沒有日期：從最新一列往回推，標籤變大（相較較新的一列）代表跨過午夜、日期減一；
    標籤本身超過 24 小時（連續編號）也能處理。開高低收有任何一個不是正數的列丟掉，不補。"""
    rows = []
    for r in ticks or []:
        try:
            lab = _label_seconds(r[0])
            o, h, l, c = (float(x) for x in r[1:5])
            v = int(float(r[5]))
        except (TypeError, ValueError, IndexError):
            continue
        if o > 0 and h > 0 and l > 0 and c > 0 and h >= l:
            rows.append((lab, o, h, l, c, v))
    if not rows:
        return []
    now = now.astimezone(_TPE) if now.tzinfo else now.replace(tzinfo=_TPE)
    today0 = _dt.datetime(now.year, now.month, now.day, tzinfo=_TPE)
    now_tod = now.hour * 3600 + now.minute * 60 + now.second
    dayoff = -1 if rows[-1][0] > now_tod + 600 else 0   # 最新標籤比現在還晚：屬於前一個日曆日（或連續編號跨過午夜）
    out, prev = [], None
    for lab, o, h, l, c, v in reversed(rows):
        if prev is not None and lab > prev:
            dayoff -= 1
        prev = lab
        epoch = int((today0 + _dt.timedelta(days=dayoff)).timestamp()) + lab - 60
        out.append({"time": epoch, "open": o, "high": h, "low": l, "close": c, "volume": v})
    out.reverse()
    by_time = {}
    for b in out:          # 同一分鐘重複（例如 '225900' 與 '226000' 換分鐘瞬間同時出現）：保留較新的那一列
        by_time[b["time"]] = b
    return [by_time[t] for t in sorted(by_time)]
