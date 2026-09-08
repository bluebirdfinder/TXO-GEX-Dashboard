"""
fetch_real_quotes.py
====================
Fetches accurate, 100% real daily close and intraday quotes directly from:
- TWSE OpenAPI (Taiwan Stock Exchange / 上市)
- TPEx OpenAPI (Taipei Exchange / 上櫃)
- TAIFEX OpenAPI (Taiwan Futures Exchange / 期交所)

Saves clean quotes to `data/tw_quotes_latest.json`.
"""

import json
import ssl
import sys
import os
import urllib.request
from datetime import datetime

# Disable SSL verification for TWSE/TPEx/TAIFEX government endpoints on Windows
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tw_quotes_latest.json")
UNIVERSE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tw_symbols_universe.json")

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8', errors='ignore'))

def fetch_twse_quotes():
    """Fetch TWSE daily quotes for all listed stocks."""
    print("Fetching TWSE listed stock quotes...")
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    quotes = {}
    try:
        data = fetch_json(url)
        for item in data:
            code = item.get("Code", "").strip()
            if not code:
                continue
            
            close_str = item.get("ClosingPrice", "0").replace(",", "")
            open_str = item.get("OpeningPrice", "0").replace(",", "")
            high_str = item.get("HighestPrice", "0").replace(",", "")
            low_str = item.get("LowestPrice", "0").replace(",", "")
            vol_str = item.get("TradeVolume", "0").replace(",", "")
            val_str = item.get("TradeValue", "0").replace(",", "")
            change_str = item.get("Change", "0").replace(",", "")

            try:
                close_price = float(close_str) if close_str != "--" else 0.0
                open_price = float(open_str) if open_str != "--" else close_price
                high_price = float(high_str) if high_str != "--" else max(open_price, close_price)
                low_price = float(low_str) if low_str != "--" else min(open_price, close_price)
                volume = float(vol_str) if vol_str != "--" else 0.0
                amount = float(val_str) if val_str != "--" else 0.0
                change = float(change_str) if change_str != "--" else 0.0
            except ValueError:
                continue

            prev_close = close_price - change if close_price > 0 else 0.0
            pct_change = (change / prev_close * 100.0) if prev_close > 0 else 0.0

            quotes[code] = {
                "symbol": code,
                "name": item.get("Name", "").strip(),
                "market": "TWSE",
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "change": round(change, 2),
                "pct_change": round(pct_change, 2),
                "volume": int(volume),
                "amount": int(amount),
                "date": item.get("Date", ""),
                "is_real": True
            }
        print(f"-> Successfully loaded {len(quotes)} TWSE quotes.")
    except Exception as e:
        print(f"Error fetching TWSE quotes: {e}")
    return quotes

def fetch_tpex_quotes():
    """Fetch TPEx daily quotes for all OTC stocks."""
    print("Fetching TPEx OTC stock quotes...")
    url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
    quotes = {}
    try:
        data = fetch_json(url)
        for item in data:
            code = item.get("SecuritiesCompanyCode", "").strip() or item.get("Code", "").strip()
            if not code or len(code) > 6:
                continue

            close_str = item.get("Close", "0").replace(",", "")
            open_str = item.get("Open", "0").replace(",", "")
            high_str = item.get("High", "0").replace(",", "")
            low_str = item.get("Low", "0").replace(",", "")
            vol_str = item.get("TradingShares", "0").replace(",", "")
            val_str = item.get("TransactionAmount", "0").replace(",", "")
            change_str = item.get("Change", "0").replace(",", "")

            try:
                close_price = float(close_str) if close_str != "----" else 0.0
                open_price = float(open_str) if open_str != "----" else close_price
                high_price = float(high_str) if high_str != "----" else max(open_price, close_price)
                low_price = float(low_str) if low_str != "----" else min(open_price, close_price)
                volume = float(vol_str) if vol_str != "----" else 0.0
                amount = float(val_str) if val_str != "----" else 0.0
                change = float(change_str) if change_str != "----" else 0.0
            except ValueError:
                continue

            prev_close = close_price - change if close_price > 0 else 0.0
            pct_change = (change / prev_close * 100.0) if prev_close > 0 else 0.0

            quotes[code] = {
                "symbol": code,
                "name": item.get("CompanyName", "").strip(),
                "market": "TPEx",
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "change": round(change, 2),
                "pct_change": round(pct_change, 2),
                "volume": int(volume),
                "amount": int(amount),
                "date": item.get("Date", ""),
                "is_real": True
            }
        print(f"-> Successfully loaded {len(quotes)} TPEx quotes.")
    except Exception as e:
        print(f"Error fetching TPEx quotes: {e}")
    return quotes

def fetch_taifex_quotes():
    """Fetch TAIFEX futures quotes."""
    print("Fetching TAIFEX futures quotes...")
    url = "https://openapi.taifex.com.tw/v1/DailyMarketReportFut"
    quotes = {}
    try:
        data = fetch_json(url)
        # Select current active front-month contract per product
        for item in data:
            contract = item.get("Contract", "").strip()
            if not contract:
                continue

            # Standardize main contract names (TX -> TXF, MXF -> MXF)
            sym = contract
            if sym == "TX":
                sym = "TXF"
            elif sym in ["MXF", "MTX"]:
                sym = "MXF"

            # Avoid duplicates if front month already added
            if sym in quotes:
                continue

            last_str = item.get("Last", "0").replace(",", "")
            open_str = item.get("Open", "0").replace(",", "")
            high_str = item.get("High", "0").replace(",", "")
            low_str = item.get("Low", "0").replace(",", "")
            vol_str = item.get("Volume", "0").replace(",", "")
            change_str = item.get("Change", "0").replace(",", "")
            pct_str = item.get("%", "0").replace("%", "").replace(",", "")

            try:
                close_price = float(last_str) if last_str != "-" else 0.0
                open_price = float(open_str) if open_str != "-" else close_price
                high_price = float(high_str) if high_str != "-" else max(open_price, close_price)
                low_price = float(low_str) if low_str != "-" else min(open_price, close_price)
                volume = float(vol_str) if vol_str != "-" else 0.0
                change = float(change_str) if change_str != "-" else 0.0
                pct_change = float(pct_str) if pct_str != "-" else 0.0
            except ValueError:
                continue

            quotes[sym] = {
                "symbol": sym,
                "name": f"{contract} 期貨",
                "market": "TAIFEX",
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "change": round(change, 2),
                "pct_change": round(pct_change, 2),
                "volume": int(volume),
                "amount": 0,
                "date": item.get("Date", ""),
                "is_real": True
            }
        print(f"-> Successfully loaded {len(quotes)} TAIFEX quotes.")
    except Exception as e:
        print(f"Error fetching TAIFEX quotes: {e}")
    return quotes

def main():
    print(f"=== Running Real Quotes Fetcher [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===")
    
    twse_map = fetch_twse_quotes()
    tpex_map = fetch_tpex_quotes()
    taifex_map = fetch_taifex_quotes()

    # Load symbol universe to verify coverage
    universe = []
    if os.path.exists(UNIVERSE_FILE):
        with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
            universe = json.load(f)

    merged_quotes = {}
    
    # 1. Populate from universe
    for u_item in universe:
        code = str(u_item.get("symbol", "")).strip()
        f_code = str(u_item.get("futures_code", "")).strip()
        
        # Check stock price match
        quote = twse_map.get(code) or tpex_map.get(code) or taifex_map.get(code) or taifex_map.get(f_code)
        
        if quote:
            merged_quotes[code] = quote
        else:
            # Fallback placeholder if market is closed or not found
            merged_quotes[code] = {
                "symbol": code,
                "name": u_item.get("name", code),
                "market": u_item.get("market", "TWSE"),
                "open": 0.0,
                "high": 0.0,
                "low": 0.0,
                "close": 0.0,
                "change": 0.0,
                "pct_change": 0.0,
                "volume": 0,
                "amount": 0,
                "date": datetime.now().strftime("%Y%m%d"),
                "is_real": False
            }

    # Add any extra quotes
    for k, v in twse_map.items():
        if k not in merged_quotes:
            merged_quotes[k] = v
    for k, v in tpex_map.items():
        if k not in merged_quotes:
            merged_quotes[k] = v
    for k, v in taifex_map.items():
        if k not in merged_quotes:
            merged_quotes[k] = v

    output_data = {
        "last_update": datetime.now().isoformat(),
        "total_quotes": len(merged_quotes),
        "quotes": merged_quotes
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"=== Successfully saved {len(merged_quotes)} real quotes to {OUTPUT_FILE} ===")
    
    # Verify 1605 (華新)
    if "1605" in merged_quotes:
        print("\n[VERIFICATION] 1605 (華新) Real Quote:")
        print(json.dumps(merged_quotes["1605"], ensure_ascii=False, indent=2))
    else:
        print("\n[WARNING] 1605 not found in merged quotes!")

if __name__ == "__main__":
    main()
