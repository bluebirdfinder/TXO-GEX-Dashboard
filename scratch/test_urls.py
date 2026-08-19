import sys
import urllib.request
import json
import ssl

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = {
    "TWSE 三大法人買賣超 (BFI82U)": "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json",
    "TWSE 加權與櫃買指數 (MIS)": "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw|otc_o00.tw",
    "TAIFEX 夜盤行情 (futDailyMarketExcel)": "https://www.taifex.com.tw/cht/3/futDailyMarketExcel?marketCode=1",
    "TAIFEX 日盤期貨三大法人 (futContractsDate)": "https://www.taifex.com.tw/cht/3/futContractsDate",
    "TAIFEX 日盤選擇權行情 (optDailyMarketReport)": "https://www.taifex.com.tw/cht/3/optDailyMarketReport",
    "TAIFEX 期貨大額交易人 (largeTraderFutQry)": "https://www.taifex.com.tw/cht/3/largeTraderFutQry"
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

print("=== Test TAIFEX & TWSE Endpoints Connection ===")
for name, url in urls.items():
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            content_type = resp.headers.get('Content-Type', '')
            data = resp.read()
            print(f"[OK] {name}: Status {resp.status}, Size {len(data)} bytes, Type: {content_type[:30]}")
    except Exception as e:
        print(f"[ERR] {name}: {e}")
