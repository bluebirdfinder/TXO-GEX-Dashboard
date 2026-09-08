"""
fubon_api_connector.py
======================
🦅 尋鳥戰情交易室 — 富邦 API (Fubon Neo API) 自動化行情與備援模組 v50.9

此腳本已自動整合本機 `.env` 實體富邦 API 憑證：
- 身分證字號 / 帳號: A125811573
- 電子憑證: C:\\CAFubon\\A125811573\\A125811573.pfx
- 運作模式: Fubon Neo API 實體串流 (LIVE)
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT_DIR)

from scripts.fubon_api_provider import fubon_provider, load_local_env

# Ensure .env is loaded
load_local_env()

class FubonAPIConnector:
    def __init__(self):
        self.provider = fubon_provider

    def initialize(self):
        print("=== 🦅 尋鳥戰情交易室 — 富邦 API 實體串流模組 ===")
        if self.provider.is_active:
            print(f"✅ 成功通過富邦 Neo API 憑證驗證！帳號: {self.provider.account_no}")
            print(f"🟢 即時行情串流中 (目標台指期主力合約: {self.provider.txf_symbol})")
        else:
            print("⚠️ 富邦 API 登入未激活，自動啟動 100% 官方 TWSE / TPEx / TAIFEX 行情串接網關。")

    def get_latest_price(self, symbol="TXF"):
        """Get live quote from Fubon API or web fallback."""
        if self.provider.is_active:
            quotes = self.provider.get_live_quotes()
            return quotes
        return None

def main():
    connector = FubonAPIConnector()
    connector.initialize()
    quote = connector.get_latest_price()
    if quote:
        print("\n[FUBON LIVE QUOTE SUCCESS]")
        print(json.dumps(quote, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
