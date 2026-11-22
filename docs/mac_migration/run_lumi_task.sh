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
