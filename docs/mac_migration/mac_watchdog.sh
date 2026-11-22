#!/bin/bash
# Mac 看門狗 v3（2026-11-22）：錄製「真的停了」才只重啟該服務，不重開機。
# 由 launchd 每 60 秒呼叫一次（com.txo.watchdog-mac）。只重啟、不刪檔、不改資料。
#
# 【為什麼要讀「檔案內最後一筆資料的時間」又「只在交易時段判斷」】
#   OP666 錄製器是「累積滿 200 行或緩衝區滿才寫入磁碟」（op666_recorder.py 第 226～228 行）。
#   休市時每分鐘只有 4 筆心跳，檔案要隔約 12 分鐘才會更新一次，檔案時間與內容都會「看起來停了」。
#   2026-11-22 實測：資料明明每分鐘都在收，看門狗卻誤報 548 秒沒資料。
#   所以：OP666 只在「預期有大量資料」的交易時段才檢查（與 Dell 的看門狗相同的時段），門檻也放寬。
#   重啟時 Python 緩衝區的資料會一起丟掉，所以寧可少重啟，也不要誤重啟。
#
#   - OP666：交易時段內，最新 .jsonl 最後一筆 "rx" 超過 600 秒 → 重啟 com.txo.op666-recorder-mac
#   - 選擇權報價鏈：health_*.csv 最後一行時間超過 300 秒 → 重啟 com.txo.optrec-mac（每 30 秒寫一次，隨時可查）
#   - 重啟保護：同一服務第一次間隔 10 分鐘，連續失敗則加倍，最長 30 分鐘；資料恢復後重置。
#   - 限流保護：Mac 的選擇權報價鏈最近 3 筆 status 都不是 ok → 暫停 30 分鐘後自動再試。
# 測試：DRYRUN=1 只印不做；FORCE_STALE=1 假裝全部過期且在交易時段（搭配 DRYRUN=1 使用）。

UIDN=$(id -u)
DIR="$HOME/AI/watchdog"
LOG="$DIR/watchdog.log"
STATE="$DIR/state"
mkdir -p "$STATE"
now=$(date +%s)

# 開機後 5 分鐘內不動作（服務還在啟動、登入富邦）
boot=$(sysctl -n kern.boottime 2>/dev/null | sed 's/.*sec = \([0-9]*\).*/\1/')
if [ -n "$boot" ] && [ $((now - boot)) -lt 300 ] && [ -z "$FORCE_STALE" ]; then
  exit 0
fi

# 現在（台北時間）應不應該有大量資料？與 Dell 的 run_recorder_all_day.ps1 的 Test-Trading 相同：
#   日盤 週一～五 08:50～13:45；夜盤 週一～五 15:05 起、週二～六 00:00～05:00
is_trading() {
  [ -n "$FORCE_STALE" ] && return 0
  dow=$(date +%u)
  m=$((10#$(date +%H) * 60 + 10#$(date +%M)))
  if [ "$dow" -ge 1 ] && [ "$dow" -le 5 ]; then
    [ "$m" -ge 530 ] && [ "$m" -lt 825 ] && return 0
    [ "$m" -ge 905 ] && return 0
  fi
  if [ "$dow" -ge 2 ] && [ "$dow" -le 6 ]; then
    [ "$m" -lt 300 ] && return 0
  fi
  return 1
}

# 檔案內最後一筆資料的時間（epoch 秒）
#   OP666 .jsonl：每行開頭 "rx": 秒數
#   health .csv：最後一行第一欄 ISO 時間（例 2026-11-22T16:48:05+08:00）
content_epoch() {
  f="$1"
  case "$f" in
    *.jsonl)
      tail -c 20000 "$f" 2>/dev/null | grep -o '"rx": [0-9]*' | tail -1 | awk '{print $2}'
      ;;
    *.csv)
      ts=$(tail -1 "$f" 2>/dev/null | cut -d, -f1)
      case "$ts" in
        ????-??-??T??:??:??[+-]??:??)
          z="${ts: -6}"; base="${ts%??????}"
          date -j -f "%Y-%m-%dT%H:%M:%S%z" "${base}${z/:/}" +%s 2>/dev/null
          ;;
      esac
      ;;
  esac
}

# 限流自動保護：Mac 這份目前只是並行備援（Dell 才是正本），
# 最近 3 筆 health 的 status 都不是 ok（可能被期交所限流）→ 先停掉 Mac 的選擇權報價鏈，避免加重封鎖；
# 暫停滿 30 分鐘自動再試一次，再失敗就再停。人不在家也會自動處理。
ratelimit_guard() {
  label=com.txo.optrec-mac
  plist="$HOME/Library/LaunchAgents/$label.plist"
  PAUSE="$STATE/optrec_paused"
  if [ -f "$PAUSE" ]; then
    since=$(cat "$PAUSE")
    if [ $((now - since)) -ge 1800 ]; then
      if [ -n "$DRYRUN" ]; then echo "[DRYRUN] 暫停滿 30 分鐘 → 會重新啟動 $label"; return 0; fi
      rm -f "$PAUSE"
      echo "$(date '+%F %T') optrec 暫停滿 30 分鐘 → 重新啟動試試" >> "$LOG"
      launchctl bootstrap "gui/$UIDN" "$plist" >> "$LOG" 2>&1
    fi
    return 0
  fi
  f=$(ls "$HOME/AI/option_quotes_mac"/health_*.csv 2>/dev/null | sort | tail -1)
  [ -z "$f" ] && return 0
  [ "$(wc -l < "$f")" -lt 5 ] && return 0
  bad=$(tail -3 "$f" | awk -F, '$3!="ok"{n++} END{print n+0}')
  if [ "$bad" -ge 3 ]; then
    if [ -n "$DRYRUN" ]; then echo "[DRYRUN] 連續 3 筆非 ok → 會暫停 $label"; return 0; fi
    echo "$now" > "$PAUSE"
    echo "$(date '+%F %T') optrec 連續 3 筆 status 非 ok（可能被限流）→ 暫停 30 分鐘" >> "$LOG"
    launchctl bootout "gui/$UIDN/$label" >> "$LOG" 2>&1
  fi
}

check() {   # 名稱 launchd標籤 資料夾 檔名樣式 最大允許秒數 [是否只在交易時段檢查：trading]
  name="$1"; label="$2"; dir="$3"; pat="$4"; max="$5"; gate="$6"
  [ "$name" = "optrec" ] && [ -f "$STATE/optrec_paused" ] && return 0   # 限流暫停中，不要被當成「卡住」又重啟
  [ -n "$FORCE_STALE" ] && max=-1
  if [ "$gate" = "trading" ] && ! is_trading; then
    return 0
  fi
  newest=$(ls "$dir"/$pat 2>/dev/null | sort | tail -1)   # 檔名依日期排序，最後一個＝最新
  if [ -z "$newest" ]; then
    age=999999
  else
    ep=$(content_epoch "$newest")
    [ -z "$ep" ] && ep=$(stat -f %m "$newest")             # 讀不到才退而求其次用修改時間
    age=$((now - ep))
  fi
  if [ "$age" -le "$max" ]; then
    [ -z "$DRYRUN" ] && rm -f "$STATE/$name.cool" "$STATE/$name"   # 資料恢復，重置重啟保護
    return 0
  fi
  last=0
  [ -f "$STATE/$name" ] && last=$(cat "$STATE/$name")
  cool=600
  [ -f "$STATE/$name.cool" ] && cool=$(cat "$STATE/$name.cool")
  if [ $((now - last)) -lt "$cool" ] && [ -z "$DRYRUN" ]; then
    return 0
  fi
  msg="$(date '+%F %T') $name 已 ${age} 秒沒有新資料（檔案：${newest:-無}）→ 重啟 $label"
  if [ -n "$DRYRUN" ]; then
    echo "[DRYRUN] $msg"
    return 0
  fi
  echo "$now" > "$STATE/$name"
  next=$((cool * 2)); [ "$next" -gt 1800 ] && next=1800
  echo "$next" > "$STATE/$name.cool"
  echo "$msg（下次最短間隔 ${next} 秒）" >> "$LOG"
  launchctl kickstart -k "gui/$UIDN/$label" >> "$LOG" 2>&1
}

ratelimit_guard
check op666  com.txo.op666-recorder-mac "$HOME/AI/op666_record_mac" "2*.jsonl"    600 trading
check optrec com.txo.optrec-mac         "$HOME/AI/option_quotes_mac" "health_*.csv" 300
exit 0
