---
name: multi-session-safety
description: TXO-GEX-Dashboard 多視窗安全流程 — 用獨立暫時 worktree 從 origin/main 合併並推送，避免動到共用資料夾裡別的視窗未 commit 的檔案；以及視窗交接與關舊視窗的步驟。當使用者說「合併後推上去」「同步 main」「開新視窗接手」「交接」，或 git status 出現不是自己改的未 commit 檔案、git log 出現不明 commit、main 落後 origin/main 時觸發。
---

# 多視窗安全流程

## 為什麼
共用同一資料夾的多個視窗＋GitHub Actions 自動排程推 main，會造成：未 commit 檔案分不出主人、不明 commit、`git merge --ff-only` 或 `git reset --hard` 蓋掉別人的東西。規則見 CLAUDE.md「多視窗守則」。

## A. 用暫時 worktree 安全推送（不碰共用資料夾）
1. `git fetch origin`
2. `git worktree add --detach <暫存資料夾> origin/main`（暫存資料夾放 `%TEMP%`，名稱要唯一）
3. 在暫存資料夾裡：`git cherry-pick <自己的commit>` 或直接編輯後 `git add <指定檔案>`（**只 add 自己的檔案，不用 `git add -A`**）→ `git commit`
4. `git fetch origin` 再確認 `git rev-list --left-right --count HEAD...origin/main` 左邊>0、右邊=0（純往前）；右邊>0 代表 main 又被推進，先 rebase／cherry-pick 到新的 origin/main
5. **push 前先問使用者**，同意後 `git push origin HEAD:main`
6. `git worktree remove --force <暫存資料夾>`；Windows／OneDrive 可能報 Permission denied，資料夾已刪但 `.git/worktrees/` 殘留登記，可稍後再 `git worktree prune`，不影響運作
7. 若要保留 commit 以待日後推送，用 `git worktree add -b <分支名>` 而不是 `--detach`（detached 的 commit 移除 worktree 後會遺失）

## B. 查別的視窗
- `list_sessions`（看 `cwd`、`isRunning`、`lastActivityAt`）找出指向同一資料夾的視窗；`ListAgents` 看誰在線。
- 用 commit 時間（+0800 換算 UTC）對照各視窗最後活動時間，可推測不明 commit 的作者，**但要向該視窗確認才算數**。
- 離線的 Remote Control／雲端視窗喚不醒也關不掉；本機視窗可用 `send_message` 喚醒詢問。

## C. 開新視窗交接
1. 把待辦、未 commit 檔案清單與各自主人、風險寫成一段指令給使用者貼進新視窗。
2. 新視窗確認讀懂後，才停止並封存舊視窗（`stop_session`／`archive_session`）；停止視窗不會刪除它已寫在資料夾裡的檔案，但會失去它的對話脈絡。
3. 舊視窗的未 commit 工作要由新視窗接手：先確認是否驗證完成，再 commit 到分支。
