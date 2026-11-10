#!/bin/bash
# run_screener_cache_task.sh - macOS version of run_screener_cache_task.ps1 (Windows).
# Refresh daily stock quotes -> rebuild screener cache + per-stock daily K shards -> persistent local store.
#
# SAFETY: this script HARD-RESETS the checkout to origin/main (same as the Windows runner). It must only be run
# inside a DEDICATED, DISPOSABLE clone (default ~/AI/txo-klines-runner), NEVER inside the OneDrive project folder.
# It refuses to run when the repo path contains "OneDrive".
#
# Dry run:  TXO_SCREENER_DRYRUN=1 bash scripts/run_screener_cache_task.sh
#           -> fetches quotes and builds the cache inside the clone, but does NOT absorb into the local store
#              and does NOT write any backup. Use this for the first supervised test on the Mac.
#
# Environment (all optional; defaults shown):
#   TXO_PRIVATE_INDICATORS  $HOME/OneDrive/文件/txo-private-mac-copy/screener-indicators
#   TXO_LOCAL_STORE         $HOME/.txo_local_store            (Mac's own store; NOT shared with the Dell)
#   TXO_BACKUP_DIR          $HOME/AI/txo-backup-mac           (local, NOT the Dell's OneDrive backup folder)
#   TXO_PYTHON              python3
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
case "$REPO" in
  *OneDrive*) echo "ERROR: refusing to run inside a OneDrive folder ($REPO). Use a dedicated clone." >&2; exit 2 ;;
esac

export PYTHONIOENCODING=utf-8
export TXO_PRIVATE_INDICATORS="${TXO_PRIVATE_INDICATORS:-$HOME/OneDrive/文件/txo-private-mac-copy/screener-indicators}"
export TXO_LOCAL_STORE="${TXO_LOCAL_STORE:-$HOME/.txo_local_store}"
export TXO_BACKUP_DIR="${TXO_BACKUP_DIR:-$HOME/AI/txo-backup-mac}"
PY="${TXO_PYTHON:-python3}"
DRY="${TXO_SCREENER_DRYRUN:-0}"

mkdir -p "$REPO/logs"
LOG="$REPO/logs/screener_cache.log"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }
# run a command, prefix every output line with a tag, return the command's exit code
run_logged() {
  local tag="$1"; shift
  "$@" 2>&1 | while IFS= read -r line; do log "$tag: $line"; done
  return "${PIPESTATUS[0]}"
}

cd "$REPO" || exit 1
log "--- start (dry=$DRY) ---"

# lock (macOS has no flock): mkdir is atomic; a lock older than 30 min is treated as stale
LOCK="$HOME/.txo-runner-lock"
for i in $(seq 1 180); do
  if mkdir "$LOCK" 2>/dev/null; then break; fi
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then rmdir "$LOCK" 2>/dev/null; continue; fi
  sleep 10
done
if [ ! -d "$LOCK" ]; then log "ERROR: runner lock busy for 30 min; giving up this run"; exit 1; fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

# --- Sync-Runner: hard-sync to origin/main, overlay the local store ---
git rebase --abort >/dev/null 2>&1
git merge --abort >/dev/null 2>&1
run_logged git git fetch origin main
run_logged git git checkout -f -B main origin/main
run_logged store "$PY" scripts/local_data_store.py overlay

run_logged quotes "$PY" scripts/fetch_real_quotes.py
rc=$?; if [ $rc -ne 0 ]; then log "ERROR: fetch_real_quotes exit code $rc"; exit 1; fi

run_logged screener "$PY" scripts/build_screener_cache.py
rc=$?; if [ $rc -ne 0 ]; then log "ERROR: build_screener_cache exit code $rc"; exit 1; fi

if [ "$DRY" = "1" ]; then
  log "dry run: skipped store absorb/backup"
else
  run_logged store "$PY" scripts/local_data_store.py absorb
  run_logged store "$PY" scripts/local_data_store.py backup
fi
log "--- done ---"
