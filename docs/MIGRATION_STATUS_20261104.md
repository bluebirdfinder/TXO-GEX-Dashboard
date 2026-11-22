# TXO 搬 Mac Mini M2：現況彙整（2026-11-04）

> 來源：唯讀彙整「專案搬遷協調」兩個聊天室與 `C:\Users\mingi\AI-migration\`（`progress.md`、`HANDOFF_搬遷總覽.md`）、`C:\Users\mingi\OneDrive\文件\搬遷交接-給Mac\MAC_SETUP.md`、「GitHub 遷移方案評估」、洋洋搬 Mac 紀錄、群益 API、溫哥 BP 等聊天室。
> **未讀內文**：「GEX 籌碼圖高度異常」「本機網頁內容不對」「JJ 錄製驗證」。**Lumi 本機排程現況未重驗**（只有 10/04 盤點）。
> 不含任何密碼、金鑰。本檔只新增、未 commit、未 push。

## 1. 已完成

| 項目 | 備註 |
|---|---|
| OneDrive 1 TB | Dell 用戶端已顯示 6.4 GB／1.0 TB |
| Mac 環境 | 不睡眠、停電自動開機、網路喚醒、關自動更新；OneDrive、Git 2.50.1、uv＋Python 3.13；8 GB 記憶體、剩 69 GB、macOS 26.3.1（10/11 數字） |
| Claude 設定同步 | 私有 repo `bluebirdfinder/Claude`，白名單 `.gitignore`，不含 `.credentials.json` |
| 洋洋已搬 Mac（10/29） | 13 個 launchd 排程；Dell 備援到約 11/5；詳見 `Lu_yangyang\docs\RUNBOOK_搬Mac_2026-10-28.md` |
| 備份（11/01） | `D:\TXO-backup\2026-11-01\`，6.33 GB；倉庫 bundle 已 verify；**無加密** |
| 本機未推送分支備份 | 11 條推到私有 repo `bluebirdfinder/TXO-GEX-Dashboard-private`（Actions 已先關） |
| 富邦 K 線不再進公開倉庫 | 10/16 起；正本 `~\.txo_local_store\futures_klines.json` |
| Mac 常駐程式查驗 | Hermes（Happy Hogan bot）、hipkiLocalServer 都只聽 127.0.0.1，與洋洋無衝突 |

## 2. 進行中

| 項目 | 狀態 |
|---|---|
| 溫哥 BP 模擬（11/04 開工） | 決策紀錄：`docs/WENGE_BP_決策紀錄_20261104.md` |
| 台選鳥規則重寫 | 只有 2 個回放窗口，結論不夠硬 |
| 群益 API | 月選報價穩；週選盤中買賣價、週選夜盤沒測；歷史買賣價要自己錄 |
| Lumi 減量（PR #2 OPEN） | 還沒合併；用量預計 11/9 前後才能驗證 |
| 幕僚鳥「先複述再確認」 | 測試 244 項過，未用真 Telegram 實測；commit 在 `desk-friction-guard`，未 push |

## 3. 未完成

| 項目 | 備註 |
|---|---|
| **富邦 SDK 在 Mac 能否跑** | 決定性卡點。只有第三方紀錄說有 macOS ARM64 版（`fubon_neo` 2.2.7／2.2.8、Python 3.8～3.13），非官方證實；要從富邦官方取得安裝檔 |
| 8 個 skill 寫死 `C:\Users\mingi` | antigravity-handover、backtest-review、factor-check、personal-assistant-builder（3 檔）、quant-strategy-dev、snowyowl |
| Mac clone 驗證、hook `python`→`python3` | 未做 |
| TXO 程式寫死 `C:\Users\mingi` | 研究員常設化聊天室已點出 |
| 群益 `SKCOM.dll` | Windows COM 元件，**我推測** Mac 跑不了，未驗證 |
| 公開歷史的 `pinescript` 資料夾（commit `3c0f43a`）與 508 個 K 線版本 | 要不要處理由使用者決定；未確認內容是否原創 |
| 倉庫改私有／法規確認 | `HANDOFF.md` 第 2 節 #2、#3 |
| 補備份 11/01 夜盤錄製檔、重做 `option_quotes\20261031_night.jsonl.gz` | 後者可能是不完整複本 |
| 備份加密（BitLocker To Go） | 使用者決定 |
| 2026-12-30 GitHub 金鑰到期 | 日曆已有 12/16 提醒 |
| `HANDOFF.md` 第 2 節其餘待辦 | 21 項，見該檔 |

## 4. 要不要和 Lumi 一起搬

結論：**同一波規劃、分開切換。**

```
共同準備（做一次）            分開切換
┌────────────────────┐    ┌─ 洋洋（已完成，觀察到 11/05）
│ ① Mac 實測富邦 SDK  │    ├─ Lumi（第二個，等減量驗證）
│ ② 寫死路徑改成變數   │───→├─ TXO 雲端部分（本來就在雲端）
│ ③ 金鑰存放規則       │    └─ TXO 即時報價／錄製（視 ① 結果）
│ ④ Git 乾淨化         │
└────────────────────┘
```

- Lumi 大半在雲端（Actions＋Cloudflare Worker）；本機落後 `origin/main` 319 個 commit，且有別人未 commit 的檔案。
- TXO 報價服務、OP666 錄製都用富邦 SDK；SDK 不能跑就只能 Dell（或 Windows VM）收資料、Mac 跑排程。
- 同一 Telegram／機器人金鑰不能兩邊同時跑。
- 8 GB 記憶體：Mac 常駐合計控制在約 4～5 GB。

## 5. 搬遷時機

- 台指期夜盤平日 15:00～隔天 05:00，所以安全窗口是**週六約 07:00（或使用者晚上到台北後）到週一約 08:00**。
- 週六 05:18～06:48 有 Lumi 晨報、05:30 有富邦 K 線累積（錯過補不回來）。
- 週日 OP666 只錄到心跳（10/31 紀錄）。

| 週末 | 內容（建議） |
|---|---|
| 11/7 晚～11/9 早 | **只做準備與 SDK 測試，不切換正式服務**（使用者已決定） |
| 11/14～15 | Lumi 切換（等 11/9 前後減量驗證） |
| 11/21～22 以後 | TXO，視 SDK 結果 |

## 6. 11/7 晚的測試腳本（待做）

1. 在 Mac 從富邦官方取得安裝檔，裝進 uv 的 Python 3.13 虛擬環境。
2. `python3 -c "import fubon_neo"`，貼回結果（不貼密碼）。
3. 休市只能測到登入；即時報價要週一盤中補測。
4. **未知：** Mac 登入富邦會不會踢掉 Dell 的登入。測之前先確認 Dell 沒在盤中，或先查富邦官方說明。
5. 同時（在副本／分支）改寫死路徑與 skill 路徑，重新盤點 Lumi 本機排程。

## 7. 注意

- 共用資料夾不要 git 切分支／pull／reset／stash／merge（見 `HANDOFF.md` 第 0 節與 `multi-session-safety` skill）。
- `git push` 一律先問使用者；`.env`、`C:\Capital\*.pfx` 不讀不貼。
- 不要在 Mac 啟動洋洋、Lumi、TXO 的排程，除非正式切換並關掉 Dell 對應排程。
