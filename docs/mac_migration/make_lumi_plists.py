"""產生 Lumi 三個本機排程的 launchd plist（Mac）。草稿：只寫檔，不安裝、不呼叫 launchctl。未在 Mac 實測。

用法（Dell 或 Mac 都能跑，只用標準函式庫）：
    python make_lumi_plists.py --root /Users/xxx/AI/Lumi-Chip-Bot --out ./launchd

設計重點：
- 一律用 LaunchAgent（使用者登入的圖形工作階段）。TV 腳本寫死 headless=False，LaunchDaemon 或沒人登入會開不了瀏覽器。
- 不把任何金鑰寫進 plist。環境變數放在使用者自己建立的 ~/.lumi_env（chmod 600，不進 git），由 run_lumi_task.sh 載入。
- 排程對應 Windows 工作排程：
    Lumi-TV-Auto-Sync       每 15 分＋登入   -> tv_auto_sync.py
    Lumi-KBar-Collector     每日 09:30       -> taifex_kbars.py --update
    Lumi-Option-Archiver    每日 09:30、19:30 -> option_archive.py
- StartCalendarInterval 用 Mac 本機時區，Mac 時區必須是 Asia/Taipei（用 `sudo systemsetup -gettimezone` 確認）。
"""
import argparse
import os
import plistlib

PREFIX = "com.lumi."
# 包裝腳本與本檔放在同一個資料夾（不在 Lumi 的 repo 裡）
WRAPPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_lumi_task.sh")

# (label 後綴, 腳本與參數, 日誌檔, 觸發)
JOBS = [
    ("tv-auto-sync", ["tv_auto_sync.py"], "tv_auto_sync.log", ("every_and_load", 900)),
    ("kbar-collector", ["taifex_kbars.py", "--update"], "kbar_collector.log", ("calendar", [(9, 30)])),
    ("option-archiver", ["option_archive.py"], "option_archive.log", ("calendar", [(9, 30), (19, 30)])),
]


def build(suffix, cmd, log, trigger, root, home):
    d = {
        "Label": PREFIX + suffix,
        "ProgramArguments": ["/bin/bash", WRAPPER, root, log] + cmd,
        "WorkingDirectory": root,
        "ProcessType": "Interactive",  # 需要圖形介面（TV 腳本開有畫面的瀏覽器）
        "EnvironmentVariables": {
            "HOME": home,
            "PATH": f"{home}/.local/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONIOENCODING": "utf-8",
        },
    }
    kind, arg = trigger
    if kind == "every_and_load":
        d["StartInterval"] = arg
        d["RunAtLoad"] = True
    elif kind == "calendar":
        items = [{"Hour": h, "Minute": m} for h, m in arg]
        d["StartCalendarInterval"] = items if len(items) > 1 else items[0]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/Users/YOURNAME/AI/Lumi-Chip-Bot")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "launchd"))
    args = ap.parse_args()
    root = args.root.rstrip("/")
    home = os.path.dirname(os.path.dirname(root))  # /Users/xxx/AI/Lumi-Chip-Bot -> /Users/xxx
    out = os.path.expanduser(args.out)
    os.makedirs(out, exist_ok=True)
    for suffix, cmd, log, trigger in JOBS:
        path = os.path.join(out, f"{PREFIX}{suffix}.plist")
        with open(path, "wb") as f:
            plistlib.dump(build(suffix, cmd, log, trigger, root, home), f)
        print("寫出", path)


if __name__ == "__main__":
    main()
