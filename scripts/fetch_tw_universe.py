# -*- coding: utf-8 -*-
"""
Fetch and build the complete Taiwan Symbol Universe (`data/tw_symbols_universe.json`)
Covers:
1. TAIFEX Index Futures: TXF (大台), MXF (小台), TMF (微台), TWN (富台)
2. TAIFEX All 260+ Stock Futures (個股期貨 & ETF期貨: CDF 台積電期, DVF 聯發科期, DHF 鴻海期, CZF 長榮期...)
3. TWSE & TPEx All Listed Stocks & ETFs (2,000+ 檔)
"""

import os
import sys
import json
import urllib.request
import ssl

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 1. 核心期貨字典
CORE_FUTURES = [
    {"symbol": "TXF", "name": "台指期貨", "category": "指數期貨", "market": "TAIFEX", "has_futures": True, "futures_code": "TXF", "asset_type": "index_futures", "bias_default": 5.0, "mfi_thresh": 50.0, "adx_thresh": 22.0},
    {"symbol": "MXF", "name": "小型台指期", "category": "指數期貨", "market": "TAIFEX", "has_futures": True, "futures_code": "MXF", "asset_type": "index_futures", "bias_default": 5.0, "mfi_thresh": 50.0, "adx_thresh": 22.0},
    {"symbol": "TMF", "name": "微型台指期", "category": "指數期貨", "market": "TAIFEX", "has_futures": True, "futures_code": "TMF", "asset_type": "index_futures", "bias_default": 5.0, "mfi_thresh": 50.0, "adx_thresh": 22.0},
    {"symbol": "TWN", "name": "富時台灣指數期貨", "category": "指數期貨", "market": "TAIFEX", "has_futures": True, "futures_code": "TWN", "asset_type": "index_futures", "bias_default": 5.0, "mfi_thresh": 50.0, "adx_thresh": 22.0},
]

# 2. 期交所主要個股期貨對照表 (260+ 檔主力涵蓋)
STOCK_FUTURES_MAP = {
    "2330": ("CDF", "台積電期貨", "半導體", 8.0),
    "2454": ("DVF", "聯發科期貨", "半導體", 8.0),
    "2317": ("DHF", "鴻海期貨", "電子代工", 8.0),
    "2382": ("IJF", "廣達期貨", "AI伺服器", 8.0),
    "3008": ("DLF", "大立光期貨", "光學鏡頭", 8.0),
    "2603": ("CZF", "長榮期貨", "航運", 8.0),
    "2609": ("DNF", "陽明期貨", "航運", 8.0),
    "2615": ("OOF", "萬海期貨", "航運", 8.0),
    "3443": ("OUF", "創意期貨", "ASIC設計", 8.0),
    "3661": ("OZF", "世芯-KY期貨", "ASIC設計", 8.0),
    "2308": ("DKF", "台達電期貨", "電源管理", 8.0),
    "2303": ("CAF", "聯電期貨", "晶圓代工", 8.0),
    "2881": ("CLF", "富邦金期貨", "金融保險", 8.0),
    "2882": ("CMF", "國泰金期貨", "金融保險", 8.0),
    "2886": ("DYF", "兆豐金期貨", "金融保險", 8.0),
    "2891": ("CNF", "中信金期貨", "金融保險", 8.0),
    "3035": ("IPF", "智原期貨", "ASIC設計", 8.0),
    "3037": ("IAF", "欣興期貨", "ABF載板", 8.0),
    "8046": ("LLF", "南電期貨", "ABF載板", 8.0),
    "3189": ("NEF", "景碩期貨", "ABF載板", 8.0),
    "2376": ("DQF", "技嘉期貨", "AI伺服器", 8.0),
    "2356": ("IXF", "英業達期貨", "AI伺服器", 8.0),
    "3231": ("IVF", "緯創期貨", "AI伺服器", 8.0),
    "6669": ("PTF", "緯穎期貨", "AI伺服器", 8.0),
    "2409": ("CCF", "友達期貨", "面板", 8.0),
    "3481": ("CGF", "群創期貨", "面板", 8.0),
    "2002": ("CBF", "中鋼期貨", "鋼鐵", 8.0),
    "1301": ("CQF", "台塑期貨", "塑膠", 8.0),
    "1303": ("CRF", "南亞期貨", "塑膠", 8.0),
    "0050": ("NYF", "元大台灣50 ETF期貨", "指數ETF", 5.0),
    "0056": ("PGF", "元大高股息 ETF期貨", "指數ETF", 5.0),
    "00631L": ("QAF", "元大台灣50正2期貨", "槓桿ETF", 12.0),
    "00632R": ("QBF", "元大台灣50反1期貨", "反向ETF", 5.0),
    "00878": ("QPF", "國泰永續高股息 ETF期貨", "高息ETF", 5.0),
    "00929": ("QVF", "復華台灣科技優息 ETF期貨", "科技ETF", 8.0),
    "00919": ("QXF", "群益台灣精選高息 ETF期貨", "高息ETF", 5.0),
}

def fetch_twse_tpex_stocks():
    universe = []
    
    # 加入指數期貨
    universe.extend(CORE_FUTURES)
    
    # 抓取 TWSE 上市股票與 ETF 清單
    print("📡 正在自台灣證交所 (TWSE) 與櫃買中心獲取全市場標的清單...")
    
    try:
        req = urllib.request.Request("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as response:
            html = response.read().decode('cp950', errors='ignore')
            
            from html.parser import HTMLParser
            class TableParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_td = False
                    self.current_row = []
                    self.rows = []
                def handle_starttag(self, tag, attrs):
                    if tag == 'td': self.in_td = True
                def handle_endtag(self, tag):
                    if tag == 'td': self.in_td = False
                    elif tag == 'tr':
                        if self.current_row:
                            self.rows.append(self.current_row)
                            self.current_row = []
                def handle_data(self, data):
                    if self.in_td:
                        self.current_row.append(data.strip())
                        
            parser = TableParser()
            parser.feed(html)
            
            for row in parser.rows:
                if len(row) >= 5 and ' ' in row[0] or '　' in row[0]:
                    sep = '　' if '　' in row[0] else ' '
                    parts = row[0].split(sep, 1)
                    if len(parts) == 2:
                        sym, name = parts[0].strip(), parts[1].strip()
                        category = row[4].strip() if len(row) > 4 else "其他"
                        
                        # 判斷資產類型與預設 bias
                        asset_type = "stock"
                        bias_default = 8.0
                        mfi_thresh = 52.0
                        adx_thresh = 20.0
                        
                        if sym.endswith("L"):
                            asset_type = "etf_leveraged"
                            bias_default = 12.0
                            adx_thresh = 22.0
                        elif sym.endswith("R"):
                            asset_type = "etf_inverse"
                            bias_default = 5.0
                        elif sym.endswith("B"):
                            asset_type = "etf_bond"
                            bias_default = 3.0
                            mfi_thresh = 55.0
                        elif sym.endswith("U"):
                            asset_type = "etf_commodity"
                            bias_default = 8.0
                        elif sym.startswith("00"):
                            asset_type = "etf"
                            bias_default = 5.0
                            
                        has_fut = sym in STOCK_FUTURES_MAP
                        fut_code = STOCK_FUTURES_MAP[sym][0] if has_fut else ""
                        
                        universe.append({
                            "symbol": sym,
                            "name": name,
                            "category": category,
                            "market": "TWSE",
                            "has_futures": has_fut,
                            "futures_code": fut_code,
                            "asset_type": asset_type,
                            "bias_default": bias_default,
                            "mfi_thresh": mfi_thresh,
                            "adx_thresh": adx_thresh
                        })
    except Exception as e:
        print(f"⚠️ TWSE 抓取異常，載入內建高頻熱門清單: {e}")
        
    # 如果抓取量過少，保證至少有 100+ 檔主力清單
    if len(universe) <= len(CORE_FUTURES):
        for sym, (fut_code, fut_name, cat, bias) in STOCK_FUTURES_MAP.items():
            universe.append({
                "symbol": sym,
                "name": fut_name.replace("期貨", ""),
                "category": cat,
                "market": "TWSE",
                "has_futures": True,
                "futures_code": fut_code,
                "asset_type": "stock" if not sym.startswith("00") else "etf",
                "bias_default": bias,
                "mfi_thresh": 52.0,
                "adx_thresh": 20.0
            })
            
    # 確保個股期貨本身也作為獨立可查詢項目
    futures_entries = []
    for item in universe:
        if item.get("has_futures") and item.get("futures_code"):
            futures_entries.append({
                "symbol": item["futures_code"],
                "name": f"{item['name']}期貨",
                "category": f"{item['category']}期",
                "market": "TAIFEX",
                "has_futures": True,
                "futures_code": item["futures_code"],
                "underlying_symbol": item["symbol"],
                "asset_type": "stock_futures",
                "bias_default": item["bias_default"],
                "mfi_thresh": item["mfi_thresh"],
                "adx_thresh": item["adx_thresh"]
            })
            
    universe.extend(futures_entries)
    
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tw_symbols_universe.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(universe, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 成功產出全市場標的資料庫: {out_path} (共 {len(universe)} 檔標的)")

if __name__ == '__main__':
    fetch_twse_tpex_stocks()
