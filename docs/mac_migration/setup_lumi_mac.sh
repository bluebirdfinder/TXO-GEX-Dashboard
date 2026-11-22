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
