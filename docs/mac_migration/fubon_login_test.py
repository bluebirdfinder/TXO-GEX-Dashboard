"""富邦 Neo SDK 在 Mac 的登入＋報價測試（只讀，不下單）。

用法（Mac 終端機，日盤 08:45～13:45 之間執行，約 1 分鐘）：
    ~/AI/fubon-test/bin/python fubon_login_test.py

設計：
- 帳號、金鑰、憑證路徑、憑證密碼一律用提示輸入（輸入時不顯示、不寫檔、不印出、不進 shell 歷史）。
- 只做：登入 → 取得即時行情權杖 → 查一次台指期近月報價 → 印出「成功／失敗」與價格。
- 不下單、不查帳務、不登出（SDK 沒有確認過的登出行為，不亂呼叫）。
- 登入可能會把 Dell 的富邦連線踢掉：執行前先確認 Dell 的報價服務狀態，執行後回 Dell 看是否斷線。
流程對照專案現有寫法：scripts/fubon_api_provider.py（apikey_login → exchange_realtime_token → MarketData）。
"""
import getpass
import sys
import time

from fubon_neo.sdk import FubonSDK, MarketData, Mode

SYMBOL = "TXF1!"  # 與 scripts/fubon_api_provider.py 一致


def ask(label, secret=False):
    return (getpass.getpass(label + "：") if secret else input(label + "：")).strip().strip("\"'")


def main():
    print("注意：全部用半形英數字（輸入法切英文，或用貼上），第二格填『富邦 API Key』，不是身分證字號。")
    account = ask("帳號（身分證字號，半形）", secret=True)
    key = ask("富邦 API Key（不是身分證字號）", secret=True)
    cert = ask("憑證檔完整路徑（.pfx）")
    cert_pass = ask("憑證密碼", secret=True)

    sdk = FubonSDK()
    t0 = time.time()
    if hasattr(sdk, "apikey_login"):
        res = sdk.apikey_login(account, key, cert, cert_pass)
    else:
        res = sdk.login(account, key, cert, cert_pass)
    ok = bool(getattr(res, "is_success", False))
    print(f"登入：{'成功' if ok else '失敗'}（{time.time() - t0:.1f} 秒）")
    if not ok:
        print("訊息：", getattr(res, "message", "（無）"))
        sys.exit(1)

    token = sdk.exchange_realtime_token()
    print("即時行情權杖：", "取得" if token else "失敗")
    if not token:
        sys.exit(2)

    md = MarketData(token, Mode.Normal)
    q = md.rest_client.futopt.intraday.quote(symbol=SYMBOL)
    if not isinstance(q, dict):
        q = getattr(q, "__dict__", {"raw": str(q)[:200]})
    keep = {k: q.get(k) for k in ("symbol", "name", "lastPrice", "lastUpdated", "date") if k in q}
    print("台指期近月報價：", keep or "（無欄位，請回報原始格式）")
    print("測試完成。請立刻回 Dell 檢查報價服務是否仍在連線。")


if __name__ == "__main__":
    main()
