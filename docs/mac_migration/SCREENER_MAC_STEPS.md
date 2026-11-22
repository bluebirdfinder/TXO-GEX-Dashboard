# 選股快取搬到 Mac：步驟（2026-11-22）

目標：Mac 與 Dell 並行跑 `TXO-Screener-Cache`（平日 16:30）。這個任務**不推 GitHub**，各自寫自己的本機資料庫（Mac：`~/.txo_local_store`，與 Dell 不共用），所以兩台同跑不衝突。正式切換（停 Dell）要等並行比對幾天、使用者同意。

## 前提
- 本檔所在的 commit 已進 origin/main（腳本 `scripts/run_screener_cache_task.sh` 與 `.gitattributes` 在 main 上）。**腳本每次執行會把資料夾強制同步成 origin/main，不在 main 上會被洗掉。**
- Mac 的 `~/AI/txo-klines-runner` 是專用的可拋棄 clone（腳本遇到路徑含 OneDrive 會拒絕執行）。
- 私有選股模組在 `~/OneDrive/文件/txo-private-mac-copy/screener-indicators`（內有 `screener_indicators.py`）。Mac Python 是 3.9.6，私有模組能否在 3.9 跑**未驗證**，乾跑就是測這個。

## 步驟（在 Mac 終端機）
1. 更新專用 clone 並乾跑（只抓報價、建快取，**不寫入資料庫、不備份**）：
   ```sh
   cd ~/AI/txo-klines-runner && git fetch origin && git checkout -f -B main origin/main && TXO_SCREENER_DRYRUN=1 bash scripts/run_screener_cache_task.sh; tail -15 logs/screener_cache.log
   ```
   通過標準：日誌最後出現 `dry run: skipped store absorb/backup` 與 `--- done ---`，沒有 `ERROR`。
2. 乾跑通過後，載入排程：
   ```sh
   sed "s#__HOME__#$HOME#g" docs/mac_migration/com.txo.screener-mac.plist.template > ~/Library/LaunchAgents/com.txo.screener-mac.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.txo.screener-mac.plist && launchctl list | grep screener
   ```
3. 第一次正式執行（平日 16:30）有人盯著：看 `logs/screener_cache.log` 是否出現 `store: ... absorb` 與 `--- done ---`。

## 退出
```sh
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.txo.screener-mac.plist && rm ~/Library/LaunchAgents/com.txo.screener-mac.plist
```
Dell 的排程全程沒動。
