#!/bin/bash
# run_op666_recorder.sh - macOS version of run_recorder_all_day.ps1 (simplified; NO stale-file watchdog yet).
# Records TAIFEX options while a session is open (Taipei time): night 15:00-05:00, day 08:30-13:50.
#
# PARALLEL MODE (2026-11-16): the Dell recorder keeps writing to its own folder. This script writes to a DIFFERENT folder
# so the two copies can be compared at close. OP666 data cannot be rebuilt: never stop the Dell recorder from this script.
#
# Usage:   bash run_op666_recorder.sh /path/to/.env /path/to/op666_recorder.py
#   op666_recorder.py lives in the user's private folder (C:\Users\mingi\txo-private\op666\run on the Dell); copy it to the
#   Mac by hand (not via git, not in the public repo). Paths are taken from env vars, no code edit needed:
#     FUBON_ENV_PATH    = the .env above
#     OP666_RECORD_DIR  = $HOME/AI/op666_record_mac   (Mac's own folder, NOT the Dell's)
set -u
ENVFILE="${1:-}"; RECORDER="${2:-}"
[ -f "$ENVFILE" ] && [ -f "$RECORDER" ] || { echo "usage: $0 /path/to/.env /path/to/op666_recorder.py" >&2; exit 2; }
PY="${TXO_PYTHON:-python3}"
export PYTHONIOENCODING=utf-8
export FUBON_ENV_PATH="$ENVFILE"
export OP666_RECORD_DIR="${OP666_RECORD_DIR:-$HOME/AI/op666_record_mac}"
mkdir -p "$OP666_RECORD_DIR"
LOG="$OP666_RECORD_DIR/recorder_all.log"

# single instance (mkdir lock; stale after 2 min without refresh is not handled here - remove ~/.op666-mac-lock by hand if needed)
LOCK="$HOME/.op666-mac-lock"
mkdir "$LOCK" 2>/dev/null || { echo "another recorder wrapper is running ($LOCK)" >&2; exit 0; }
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

# Taipei time, minutes since midnight (Mac clock may be set elsewhere)
tpe_min() { TZ=Asia/Taipei date '+%H %M' | awk '{print $1*60+$2}'; }
is_open() { m=$(tpe_min); [ "$m" -ge 900 ] || [ "$m" -lt 300 ] || { [ "$m" -ge 510 ] && [ "$m" -lt 830 ]; }; }

while true; do
  if is_open; then
    echo "$(date '+%Y-%m-%dT%H:%M:%S') start" >> "$LOG"
    set -a; . "$ENVFILE"; set +a
    "$PY" "$RECORDER" >> "$OP666_RECORD_DIR/_out.txt" 2>> "$OP666_RECORD_DIR/_err.txt"
    echo "$(date '+%Y-%m-%dT%H:%M:%S') recorder exited ($?)" >> "$LOG"
    sleep 10
  else
    sleep 60
  fi
done
