#!/bin/bash
# run_live_server_task.sh - macOS version of run_live_server_task.ps1 (Windows).
# Keeps scripts/live_price_server.py (127.0.0.1:8000) running; restarts 15 s after it exits.
#
# PARALLEL MODE (2026-11-16): the Dell keeps running its own copy. Do NOT stop the Dell until the close-of-day comparison.
# SAFETY: hard-resets the checkout to origin/main -> only run inside a DEDICATED clone (default ~/AI/txo-klines-runner),
#         never inside the OneDrive project folder (script refuses if the path contains "OneDrive").
#
# Usage:   bash scripts/run_live_server_task.sh /path/to/.env
#   The .env (created by the user on the Mac, NOT in git) holds FUBON_API_KEY / FUBON_ACCOUNT_NO /
#   FUBON_CERT_PATH / FUBON_CERT_PASS / FUBON_API_MODE. This script only reads it into its own process.
# Stop:    Ctrl+C (foreground test) or `launchctl bootout` if later wrapped in a plist.
set -u
ENVFILE="${1:-}"
[ -f "$ENVFILE" ] || { echo "usage: $0 /path/to/.env" >&2; exit 2; }

REPO="$(cd "$(dirname "$0")/.." && pwd)"
case "$REPO" in
  *OneDrive*) echo "ERROR: refusing to run inside a OneDrive folder ($REPO)." >&2; exit 2 ;;
esac
PY="${TXO_PYTHON:-python3}"
export PYTHONIOENCODING=utf-8
export TXO_LOCAL_STORE="${TXO_LOCAL_STORE:-$HOME/.txo_local_store}"

mkdir -p "$REPO/logs"
LOG="$REPO/logs/live_price_server.log"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

cd "$REPO" || exit 1
while true; do
  [ -f "$LOG" ] && [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 5242880 ] && mv -f "$LOG" "$LOG.old"
  log "--- starting live_price_server ---"
  git rebase --abort >/dev/null 2>&1; git merge --abort >/dev/null 2>&1
  git fetch origin main 2>&1 | while IFS= read -r l; do log "git: $l"; done
  git checkout -f -B main origin/main 2>&1 | while IFS= read -r l; do log "git: $l"; done
  "$PY" scripts/local_data_store.py overlay 2>&1 | while IFS= read -r l; do log "store: $l"; done

  # load .env into THIS process only (no echo of values)
  set -a; . "$ENVFILE"; set +a

  "$PY" scripts/live_price_server.py 2>&1 | while IFS= read -r l; do log "srv: $l"; done
  log "server exited; restarting in 15 s"
  sleep 15
done
