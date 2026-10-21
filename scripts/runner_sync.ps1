# runner_sync.ps1 - dot-sourced by the runner wrappers (run_live_server_task.ps1, run_fubon_klines_task.ps1, run_screener_cache_task.ps1).
# ASCII only on purpose (Windows PowerShell 5.1 misreads non-ASCII in BOM-less scripts).
#
# The runner clone (C:\Users\mingi\txo-klines-runner, outside OneDrive) is a DISPOSABLE checkout: before every task it is hard-reset to
# origin/main, and the data the runner produces itself lives in a persistent local store (scripts/local_data_store.py) that is
# overlaid back into data/ after the reset. Nothing is ever committed in the runner, so `git pull --rebase` conflicts (the cloud engine
# writes the same data files) can no longer leave a half-done rebase behind (2026-10-14..16).

function Enter-RunnerLock {
    param([int]$TimeoutSec = 600)
    $script:RunnerMutex = New-Object System.Threading.Mutex($false, 'Global\txo-runner-git')
    try { return $script:RunnerMutex.WaitOne($TimeoutSec * 1000) }
    catch [System.Threading.AbandonedMutexException] { return $true }   # the previous holder died; we own it now
}

function Exit-RunnerLock {
    try { if ($script:RunnerMutex) { $script:RunnerMutex.ReleaseMutex() } } catch { }
}

# Hard-sync the checkout to origin/main and overlay the local store. Call only while holding the runner lock.
function Sync-Runner {
    param([scriptblock]$LogFn)
    git rebase --abort 2>&1 | Out-Null     # leftovers of an old half-done rebase / merge (harmless when none)
    git merge --abort 2>&1 | Out-Null
    git fetch origin main 2>&1 | ForEach-Object { & $LogFn "git: $_" }
    git checkout -f -B main origin/main 2>&1 | ForEach-Object { & $LogFn "git: $_" }
    python scripts/local_data_store.py overlay 2>&1 | ForEach-Object { & $LogFn "store: $_" }
}
