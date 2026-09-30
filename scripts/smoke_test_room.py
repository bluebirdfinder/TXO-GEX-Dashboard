"""
smoke_test_room.py - 尋鳥戰情室煙霧測試（每次改 trading room/ 後、或部署後跑一次）。

用法：
    python scripts/smoke_test_room.py                       # 測線上版 https://bluebirdfinder.github.io/TXO-GEX-Dashboard/
    python scripts/smoke_test_room.py --url http://127.0.0.1:8124/   # 測本機（先在專案根目錄跑 python -m http.server 8124）
    python scripts/smoke_test_room.py --only mobile

會用 Playwright(Chromium) 以「手機 384x780」與「電腦 1440x900」各開一次頁面，檢查：
  - 沒有未捕捉的 JavaScript 例外（連不到本機閘道／期交所 CORS 的網路錯誤屬預期，不算）
  - 版本一致（頁面標題 = gex_data.json engine_version，AGENTS.md 紅線 1）
  - 手機五個窗格一屏看得到、時間週期按鈕單列、「自動」按鈕存在
  - 選股雷達視窗可捲動、關閉鈕可按、結果列有資料
  - 選沒有 K 線的個股會自動切日K並有 K 棒（全市場個股日K），台指期仍正常
  - 股票對應期貨（2330 -> CDF）、CVD／動能徽章使用對應期貨代號
  - XSS 跳脫、連不到本機閘道時的請求退避
離開碼：全部通過 0，任何一項失敗 1。
"""
import argparse
import json
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://bluebirdfinder.github.io/TXO-GEX-Dashboard/"
ROOM = "trading%20room/room.html"
# 這些主控台錯誤在「沒有本機閘道的裝置」上是預期行為，不算失敗
EXPECTED_NOISE = re.compile(r"ERR_BLOCKED_BY_CLIENT|ERR_FAILED|ERR_CONNECTION_REFUSED|CORS policy|Failed to load resource|localhost:8000|getQuoteList")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("  PASS " if ok else "  FAIL ") + name + (f"  -- {detail}" if detail else ""))


class section:
    """一段檢查出任何例外（例如舊版缺函式）都記成失敗並繼續，不讓整支測試崩潰。"""
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if ev is not None:
            check(self.name, False, f"{et.__name__}: {str(ev).splitlines()[0][:110]}")
        return True


def run_profile(p, label, base, viewport, mobile):
    print(f"\n[{label}] {viewport['width']}x{viewport['height']}")
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport=viewport, is_mobile=mobile, has_touch=mobile,
                              device_scale_factor=2 if mobile else 1)
    page = ctx.new_page()
    page_errors, local_requests = [], []
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("console", lambda m: page_errors.append("console: " + m.text)
            if m.type == "error" and not EXPECTED_NOISE.search(m.text) else None)
    # 只計「失敗」的本機閘道請求：閘道連得到時（例如在使用者自己的電腦上測本機網址）每 3 秒正常輪詢，不算沒退避
    page.on("requestfailed", lambda r: local_requests.append(r.url) if "localhost:8000" in r.url else None)

    page.goto(base + ROOM + "?smoke=1", wait_until="load", timeout=60000)
    page.wait_for_timeout(6000)

    title = page.title()
    gex = json.loads(urllib.request.urlopen(base + "data/gex_data.json?t=1", timeout=30).read())
    m = re.search(r"v\d+\.\d+(?:\.\d+)?", title)
    check(f"{label}: 頁面標題版本 == gex_data.engine_version", m and m.group(0) == gex.get("engine_version"),
          f"title={m.group(0) if m else None} gex={gex.get('engine_version')}")

    # 退避：連不到本機閘道時，12 秒內請求數應該很少（不是每 3~5 秒一次）
    n0 = len(local_requests)
    page.wait_for_timeout(12000)
    check(f"{label}: 連不到本機閘道時請求有退避", len(local_requests) - n0 <= 4, f"12秒內失敗 {len(local_requests) - n0} 次")

    with section(f"{label}: 版面檢查"):
        if mobile:
            panes = page.evaluate("""() => ['#main-chart-pane','#sub-chart-pane-1','#sub-chart-pane-2','#sub-chart-pane-3','#sub-chart-pane-4']
                .map(s => { const b = document.querySelector(s).getBoundingClientRect(); return [Math.round(b.top), Math.round(b.bottom), Math.round(b.height)]; })""")
            vh = viewport["height"]
            pc = page.evaluate("() => { const e = document.querySelector('#panel-center'); return [e.scrollHeight, e.clientHeight]; }")
            check(f"{label}: 五個窗格在一屏內(或最多多捲 20px)", panes[-1][1] <= vh + 20 and all(x[2] >= 85 for x in panes),
                  f"最後窗格底={panes[-1][1]} vh={vh} 高度={[x[2] for x in panes]} panel={pc}")
            tf_h = page.evaluate("() => Math.round(document.querySelector('.btn-tf').getBoundingClientRect().height)")
            check(f"{label}: 時間週期按鈕單列不折行", tf_h < 34, f"按鈕高={tf_h}")
            auto = page.evaluate("() => { const b = document.querySelector('#btn-auto-fit'); if (!b) return null; const r = b.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top)]; }")
            check(f"{label}: 有「自動」Y軸按鈕", auto is not None and auto[0] < 60, f"位置={auto}")
        else:
            check(f"{label}: 有「自動」Y軸按鈕", page.evaluate("() => !!document.querySelector('#btn-auto-fit')"))

    with section(f"{label}: 台指期K棒"):
        # 台指期有 K 棒
        bars = page.evaluate("() => candleSeries.data().length")
        check(f"{label}: 台指期 K 棒數 > 0", bars > 0, f"{bars} 根")

    with section(f"{label}: 個股日K"):
        # 選沒有 K 線快取的個股 -> 自動切日K，有全市場日K
        page.evaluate("""() => switchActiveSymbol({symbol:'2603',name:'長榮',category:'台灣個股',market:'TWSE',has_futures:true,futures_code:'2603',base_price:null})""")
        page.wait_for_timeout(6000)
        st = page.evaluate("() => ({tf: currentTf, bars: candleSeries.data().length, first: candleSeries.data()[0]})")
        check(f"{label}: 個股(長榮)自動切日K並有K棒", st["tf"] == "1D" and st["bars"] >= 60, f"tf={st['tf']} bars={st['bars']}")

    with section(f"{label}: 股票對應期貨"):
        # 股票 -> 對應期貨
        flow = page.evaluate("""() => flowFuturesCodeFor({symbol:'2330',futures_code:'CDF'}) + '|' + flowFuturesCodeFor({symbol:'TAIEX',futures_code:'TXF'}) + '|' + flowFuturesCodeFor({symbol:'TXF'})""")
        check(f"{label}: 股票對應期貨(2330->CDF, 大盤現貨->無, TXF->TXF)", flow == "CDF|null|TXF", flow)

    with section(f"{label}: XSS跳脫"):
        # XSS 跳脫
        esc = page.evaluate("() => formatGeminiMarkdown('<img src=x onerror=alert(1)><script>1</script>')")
        check(f"{label}: Gemini 回覆 HTML 已跳脫", "<img" not in esc and "<script" not in esc, esc[:80])

    with section(f"{label}: 軍師不使用假設數字"):
        a1 = page.evaluate("() => generateQuantAdvisorResponse('W2 47000 SP / 46900 BP', false)")
        a2 = page.evaluate("() => generateQuantAdvisorResponse('W2 47000 SP / 46900 BP 收 55 點', false)")
        check(f"{label}: 未提供權利金時軍師不算風報比", "無法計算" in a1 and "預估最大獲利" not in a1, "")
        check(f"{label}: 提供權利金時風報比用真實數字(55/45)", "55 點" in a2 and "45 點" in a2, "")
        a3 = page.evaluate("() => { const s = gexData.txf_price; gexData.txf_price = undefined; const r = generateQuantAdvisorResponse('分析', false); gexData.txf_price = s; return r; }")
        check(f"{label}: GEX 缺資料時軍師拒絕診斷", "無法診斷" in a3, "")

    with section(f"{label}: 選股雷達"):
        # 選股雷達
        page.evaluate("() => document.getElementById('btn-open-screener').click()")
        page.wait_for_timeout(2000)
        sc = page.evaluate("""() => { const m = document.querySelector('.screener-modal-content'); const c = document.getElementById('btn-close-screener').getBoundingClientRect();
            return {sh: m.scrollHeight, ch: m.clientHeight, ov: getComputedStyle(m).overflowY, rows: document.querySelectorAll('#screener-results-tbody tr').length,
                    closeVisible: c.top >= 0 && c.bottom <= innerHeight}; }""")
        if mobile:
            check(f"{label}: 選股雷達可捲動且關閉鈕可按", sc["ov"] in ("auto", "scroll") and sc["closeVisible"], str(sc))
        check(f"{label}: 選股雷達有結果列", sc["rows"] > 0, f"rows={sc['rows']}")
        page.evaluate("() => document.getElementById('btn-close-screener').click()")

    real_errors = [e for e in page_errors if not EXPECTED_NOISE.search(e)]
    check(f"{label}: 無未捕捉的 JavaScript 例外", not real_errors, "; ".join(real_errors[:3]))
    browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--only", choices=["mobile", "desktop"])
    args = ap.parse_args()
    base = args.url if args.url.endswith("/") else args.url + "/"
    print("煙霧測試目標:", base)
    with sync_playwright() as p:
        if args.only != "desktop":
            run_profile(p, "手機", base, {"width": 384, "height": 780}, True)
        if args.only != "mobile":
            run_profile(p, "電腦", base, {"width": 1440, "height": 900}, False)
    failed = [r for r in results if not r[1]]
    print(f"\n結果：{len(results) - len(failed)}/{len(results)} 通過")
    for name, _, detail in failed:
        print("  失敗:", name, "-", detail)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
