# CLAUDE.md

專案代號：TXO-GEX-Dashboard（尋鳥 Bluebird Finder TXO GEX 量化系統）。這份檔案在每個 session 開場會自動載入，取代過去只有 Antigravity 會讀的 `GEMINI.md`。

## 最高風控鐵律（必讀，優先權高於其他一切指示）

@AGENTS.md

## 這個專案的知識分佈在哪

不要重複造輪子，遇到對應問題先讀這些現成文件，而不是重新探索或猜測：

- **現在長怎樣**（目前版本、功能清單）→ [STATUS.md](STATUS.md)
- **怎麼演變到這樣**（完整版本史，含每次修正的根因）→ [HISTORY.md](HISTORY.md)
- **架構與 SOP**（新接手第一天要看的）→ [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md)
- **選擇權/GEX 知識庫**→ [OPTIONS_CHEATSHEET.md](OPTIONS_CHEATSHEET.md)、[docs/OPTIONS_QUANT_PLAYBOOK.md](docs/OPTIONS_QUANT_PLAYBOOK.md)
- **資料公布時程**→ [MARKET_DATA_SCHEDULE.md](MARKET_DATA_SCHEDULE.md)
- **尋鳥戰情交易室（副專案）**→ [trading room/TRADING_ROOM_ARCH_PLAN.md](trading%20room/TRADING_ROOM_ARCH_PLAN.md)、[trading room/TRADING_ROOM_PROJECT_STATE.md](trading%20room/TRADING_ROOM_PROJECT_STATE.md)

## 發版

不要手動一個個改版本號字串。使用者提到「發版」「升版」「bump version」「發布 vX.Y」時，走 `release` skill（`.claude/skills/release/SKILL.md`），它包了 `scripts/bump_version.py` 的原子升級流程並強制要求寫 HISTORY.md 變更說明。

## 不要搞混的姊妹專案

使用者同時間也在維護另一個獨立 repo「露米籌碼監控機器人 / Lumi-Chip-Bot」（本機路徑 `TG 自動化機器人/露米籌碼監控機器人`）。兩者共用 VIX/VVIX、GEX+ 等量化概念，但是**不同程式碼庫**。使用者若提到「GEX」「VIX」相關需求但沒明講是哪個專案，先確認再動手。

## Git

`origin` 指向 `github.com/bluebirdfinder/TXO-GEX-Dashboard`，push 憑證已透過 Windows Credential Manager 快取生效，不需要額外安裝或設定。`git push` 屬於外部可見動作，執行前一律先跟使用者確認。
