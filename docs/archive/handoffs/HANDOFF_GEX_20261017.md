# 交接檔：GEX 點位（週選導向）第二棒（2026-10-17 製作）

> 接續 `docs/HANDOFF_GEX_WEEKLY_20261016.md`（分支 `claude/handoff-20261016`，含附錄）。本檔只寫 10/17 這一棒新增的事實、分支、待辦。先讀那份再讀本檔。
> 使用者：週選實盤交易者，要「正確又準確」的 GEX 點位、新版照教科書定義。點位只是模型輸出，不構成投資建議，不得建議追價、不得建議拆週選價差單。

## 1. 一句話現況
v64.18（牆位新定義＋微台散戶比修正＋夜盤以夜盤價錨定）已在本機分支編譯完成、**未推送**；使用者尚未決定推送時間，也尚未決定「結算日剔除已結算合約」。Lumi 已被告知欄位與語意，等發版時間。

## 2. 分支總表（全部未推送，都在共用 .git）
| 分支 | commit | 內容 | 狀態 |
|---|---|---|---|
| `claude/release-wall-def`（暫時 worktree：`C:\Users\mingi\wt-release`） | 470abf4 | v64.18 發版：牆位新定義、微台散戶比修正、夜盤錨定＋牆位搜尋多 600 點、HISTORY、重編譯資料。基底 origin/main（10/16 下午） | 推送前必須先在 origin/main 最新上重做一次 bump＋重編譯（見 §6） |
| `claude/deque-snapshot-fix`（`wt-deque`） | c487c08 | `get_recent_trades` 快照加重試，修「deque mutated during iteration」警告；`scripts/test_trades_snapshot.py`（修前 76 次錯誤、修後 0） | 推送後需重啟報價服務（收盤後） |
| `claude/retail-clip-fix`（`wt-retail`） | 70990ed | 已包含在 release 分支（cherry-pick）；獨立保留 | 不必單獨推 |
| `claude/gex-wall-definition` / `gex-textbook` / `log-all-trades` / `store-backup-fix` | f78ea15 / 3c7b6a9 / 484b782 / bd0f95a | 10/16 交接檔的項目；`log-all-trades`、`store-backup-fix` 已改由「三聊天室接手」視窗負責 | 見 10/16 交接檔 |
| `claude/handoff-20261017` | 本檔 | 文件 | — |

## 3. 10/17 查到的事實
1. **夜盤快訊為什麼又錯**：線上仍是 v64.17 舊定義（Call Wall 46,300 在 Put Wall 47,000 之下）；且夜盤時 GEX 仍錨定日盤收盤現貨 47,111，履約價窗口只有 46,200～48,000，夜盤價 46,140 已掉出窗口，現價下方的牆算不到。
2. **修法（已在 release 分支）**：`calculate_true_gex_profile` 新增選填 `wall_extra`（預設 0＝舊行為）：牆位搜尋多看 ±600 點，長條圖與總和仍 ±900，Max Pain 只看 OI 不變。夜盤（15:00～08:45）用夜盤期貨價當錨（與既有 `active_night_spot`、`day_profile` 以期貨價當 spot 的慣例一致）。新輸出 `gex_anchor_price`、`night_vs_day_close`（夜盤期貨−日盤期貨收盤，**不是基差**）。模擬夜盤 05:30 實跑：Call Wall 46,300／Put Wall 46,000／Max Pain 46,500（不變）。測試 `scripts/test_gex_night_anchor.py` 4 項、`test_gex_walls.py` 8 項全過。
3. **假基差**：快訊「期現貨價差 (Basis) −971」＝夜盤期貨 46,140 減日盤收盤現貨 47,111，不是基差（現貨已收盤）。快訊文字由 **Lumi 端**組裝，TXO 不改；Lumi 已記待辦改用 `night_vs_day_close` 並改名。
4. **微台散戶多空比 bug**：散戶多空頭由「近月 OI − 法人全月份部位」推得，近月 OI 比法人全月空單小時空頭被夾成 0（10/16 微台淨 68,652 → 顯示 51.56%；正確 72,659 → 54.57%）。已修（改用全月合計 OI），稽核 PASS。
5. **`audit_vs_official.py --sample 0` 現況（release 分支編譯後）**：6 項 FAIL 中，微台已修；P/C 67.6＝期交所公布值，稽核自算 72.43 是稽核口徑不同；VIX 是盤中時間差；Max Pain（4 檔合併 46,500 vs 全契約 47,250）與「Call Wall 在 Call OI 前三大」是稽核舊假設（Max Pain 不改，使用者觀察很準）。
6. **資料飄移**：一次重編譯曾出現 Call/Put Wall 47,150／46,200、Max Pain 47,100、微台 58.02，原因是 TAIFEX 讀取逾時走備援；重跑兩次穩定。**發版前務必重編譯後檢查數字**（Call/Put Wall 應 48,000／47,000；Max Pain 46,500）。
7. **週末頁面「到期組成」含已結算 F3 的查證**：線上與本機資料都**沒有**含 F3（線上實測：Call Wall 組成 10/21 月選 54%｜10/23 週選 46%；Max Pain 46,500）。三聊天室視窗那張截圖（Call 47,200／Put 47,000／Max Pain 47,300／F3 77%）逐項吻合 10/15 夜～10/16 上午的舊資料（chip 日期 10/15，F3 當時合法存在），應是瀏覽器顯示舊畫面，不是資料問題。**真實缺口**：結算日 13:30 到期交所 OI 公布（10/16 約 15:29）之間，頁面用的是前一日 OI，會短暫含已結算合約。
8. **老墨 GEX 網頁**：老墨官網 `mofiinvestment.com/tools/` 沒有 GEX 工具；只有 10/8 文章（五萬點為何碰了就回，`/blog/live-20261008-gex-glass-fiber`）：他把最大 Call 集中處（5 萬）當上方關卡、翻轉點當防守線、依到期日分開看（3D 圖）、情境機率「不是勝率」。使用者給的截圖（現價 46,808、翻轉點 46,843、總 GEX −226 億、買權牆 47,300、跌破 46,300、情境 A～D）應來自老墨直播／會員工具，**網址使用者說稍後貼**。我們與外部對照：羊叔網站（`gooptions.cc/trend-core-gex/`，免費只見摘要）10/16 收盤：Gamma Flip 46,596、GEX+ Flip 46,853、總 GEX +17.7 億（我們通行版約 46,535～46,569、+16.09 億，同號相近）。
9. **報價服務**：運作中（15 秒原始記錄持續寫入）；日誌每 7～10 分鐘一次「momentum recorder error: deque mutated during iteration」（10/15～16 共 449 次）＝§2 的 `deque-snapshot-fix`，推送＋重啟前仍會出現。

## 4. 待使用者決定（用 AskUserQuestion 問）
1. 要不要補「結算日 13:30 後剔除已結算合約」：只套用在牆位、Gamma Flip、到期組成，**Max Pain 絕對不動**（使用者已確認）。
2. 發版推送時間（與 Lumi 約同時；推送前先確認 `gh run list --workflow auto_update.yml --limit 1` 是 completed）。
3. 分階段：`weekly_focus`（只給下一檔到期）先並排記錄 3～5 個交易日（含 10/21 結算）驗證，再決定頭條格式與 TG／網頁文案（使用者已同意此節奏）。

## 5. Lumi 端（視窗「GEX_VEX 審查 (參考羊叔)」，`local_b7a26795-ca8b-45fb-93de-24e735b7ba48（視窗「Lumi 牆位防呆與 TXO 協調交接」；舊視窗 local_fa50339d-… 已交棒、不再回應，往來一律找新的）`）
- 已告知：欄位 `call_wall_strike`（現價上方 Call GEX 最大）、`put_wall_strike`（現價下方）、舊值 `call_gex_peak_strike`／`put_gex_peak_strike`、`spot_price` 語意不變、新增 `gex_anchor_price`／`night_vs_day_close`、回測簽章新增選填 `wall_extra`。夜盤牆位相對 `gex_anchor_price`，不是 `spot_price`。
- Lumi 已做（分支 `claude/wall-sanity-guard` c3bb995，未 push，TXO 不碰）：防呆優先用 `gex_anchor_price`。假基差文字等發版時間確定才改。**發版時間確定後要先通知 Lumi。**
- **TXO 欠 Lumi 兩件唯讀驗證（尚未做）**：①用整數天（舊）與小數天到 13:30（現行）兩種到期天數重算 2026-10-14 結算日 13:30 前快照（公開版 commit 4136457，更新時間 10/14 09:03）的 Call／Put Wall、Zero Gamma、總 GEX／VEX，回報差多少點；②確認 10/14 23:59（更新時間 10/15 07:49）發布過牆位 47,700／47,700、總 GEX 0.0、`gamma_flip_standard` 為空的垃圾快照，是否有「資料抓失敗不覆蓋正常資料」的防護。
- 「三聊天室接手」視窗（`local_3f61b34e-…`）只做 JJ 紅黃線與報價服務／runner（`log-all-trades`、`store-backup-fix`），GEX 點位全歸這個工作流。

## 6. 接手順序
```
1. 開 Remote Control → git fetch → list_sessions（Lumi 視窗是否有新訊息）
2. 讀 10/16 交接檔（含附錄）＋本檔＋HANDOFF.md 第 0 節＋CLAUDE.md／AGENTS.md／記憶
3. AskUserQuestion：§4 三件事（含是否剔除已結算合約）
4. 發版前：在 origin/main 最新上重做（暫時 worktree）：cherry-pick release 分支的 4 個提交
   → python scripts/bump_version.py（若 v64.18 已存在則直接重編譯）→ 重編譯後檢查
   Call/Put Wall、Max Pain、微台比 → audit_vs_official.py --sample 0
5. 與使用者確認推送、先通知 Lumi、確認 auto_update 一輪 completed，再推送
6. 做 Lumi 兩件唯讀驗證並回報
7. 使用者貼老墨網址 → 對照他的翻轉點／牆位定義與我們差在哪
```

## 7. 規則與踩過的坑
- `git push` 一律先問；用暫時 worktree；只 add 自己的檔案；做完就 commit（別用 `git checkout -- .`）；使用者看不到 .md，文件要附 HTML 或貼在對話；問使用者用 AskUserQuestion；回報完成百分比、進度用表格、流程用 code block 圖。
- 紅線：不偽造資料、不建議拆週選價差單、不建議追價；指標公式只放私有資料夾；Max Pain 不動。
- 重編譯結果會隨 TAIFEX 逾時而飄移，推送前看數字。
- 用假時鐘模擬夜盤：`C:\Users\mingi\simnight.py`（把 `datetime.now` 固定為 10/16 21:30 UTC＝10/17 05:30 台灣）。
- JJ 頁面不要按儲存、不要調視窗大小、不要蓋 Q 姐版面（JJ 另由三聊天室接手視窗處理）。
