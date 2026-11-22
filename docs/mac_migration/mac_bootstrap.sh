#!/bin/bash
# 在 Mac 終端機貼上執行：把 3 個檔案寫進 ~/AI/lumi_migration/
mkdir -p ~/AI/lumi_migration && cd ~/AI/lumi_migration
cat > run_lumi_task.sh <<'LUMI_EOF'
#!/bin/bash
# 用法：run_lumi_task.sh <Lumi 專案根目錄> <日誌檔名> <腳本> [參數...]
# 載入 ~/.lumi_env（使用者自己建立、chmod 600、不進 git），再用專案 venv 的 python 執行，輸出附加到日誌。
# 未在 Mac 實測。
set -u
ROOT="$1"; LOG="$2"; shift 2
cd "$ROOT" || exit 1
if [ -f "$HOME/.lumi_env" ]; then
  set -a; . "$HOME/.lumi_env"; set +a
fi
export TZ="Asia/Taipei"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] start: $*" >> "$ROOT/$LOG"
"$ROOT/.venv/bin/python" "$@" >> "$ROOT/$LOG" 2>&1
rc=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] exit=$rc" >> "$ROOT/$LOG"
exit $rc
LUMI_EOF
cat > make_lumi_plists.py <<'LUMI_EOF'
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
LUMI_EOF
cat > setup_lumi_mac.sh <<'LUMI_EOF'
#!/bin/bash
# Lumi 本機排程搬 Mac：環境準備（不啟用任何排程、不寫 TradingView）。未在 Mac 實測。
# 用法：bash setup_lumi_mac.sh            （在 Mac 終端機，一次一步，看輸出）
# 不處理金鑰：~/.lumi_env 與 tv_session.json 由使用者自己放。
set -u
ROOT="$HOME/AI/Lumi-Chip-Bot"
REPO="https://github.com/bluebirdfinder/Lumi-Chip-Bot.git"

echo "== 1. 檢查"
uname -m; sw_vers -productVersion
sudo -n true 2>/dev/null || echo "（時區檢查需要密碼，請自己執行：sudo systemsetup -gettimezone，應為 Asia/Taipei）"
[ -d "/Applications/Google Chrome.app" ] && echo "Chrome：已安裝" || echo "Chrome：未安裝（tv_login_helper.py 需要，請先安裝）"
command -v git >/dev/null && git --version
UV="$HOME/.local/bin/uv"; [ -x "$UV" ] && echo "uv：OK" || echo "uv：找不到 $UV"

echo "== 2. clone（若已存在則只 fetch，不改動）"
mkdir -p "$HOME/AI"
if [ -d "$ROOT/.git" ]; then git -C "$ROOT" fetch origin && git -C "$ROOT" status -sb | head -3
else git clone "$REPO" "$ROOT"; fi

echo "== 3. 虛擬環境與套件"
cd "$ROOT" || exit 1
[ -d .venv ] || "$UV" venv --python 3.13 .venv
"$UV" pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m playwright install chromium

echo "== 4. 需要你自己放的東西（腳本不處理）"
[ -f "$HOME/.lumi_env" ] && echo "~/.lumi_env：存在" || echo "~/.lumi_env：不存在 → 請自己建立，內容兩行：LUMI_TELEGRAM_BOT_TOKEN=... 與 LUMI_TELEGRAM_GROUPCHAT_ID=...，再 chmod 600"
[ -f "$ROOT/tv_session.json" ] && echo "tv_session.json：存在" || echo "tv_session.json：不存在 → 從 Dell 複製（不進 git）"
[ -d "$ROOT/kbar_data" ] && echo "kbar_data：存在" || echo "kbar_data：不存在 → 從 Dell 複製"
[ -d "$ROOT/option_data" ] && echo "option_data：存在" || echo "option_data：不存在 → 從 Dell 複製"

echo "== 5. 乾跑（不寫 TradingView）"
.venv/bin/python tv_auto_sync.py --dry-check || echo "乾跑回傳非 0，請把輸出貼給 Claude（不貼金鑰）"

echo "完成。尚未啟用任何排程。下一步：Dell 建 tv_sync_pause.txt，再產生並載入 plist（見 MIGRATION_ALL_PLAN_20261109.md）。"
LUMI_EOF
chmod +x *.sh; ls -l ~/AI/lumi_migration; echo 已寫入，下一步：bash setup_lumi_mac.sh
