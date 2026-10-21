# run_screener_cache_task.ps1 - scheduled wrapper: refresh daily stock quotes -> rebuild screener cache + per-stock daily K shards -> persistent local store.
# Why local: build_screener_cache.py imports the owner's PRIVATE indicator modules (C:\Users\mingi\txo-private\screener-indicators,
# not in the public repo), so it cannot run in GitHub Actions. Runs in the dedicated runner clone (outside OneDrive).
# Suggested schedule: weekdays 16:30 (TWSE/TPEx daily files are published by then). Needs no Fubon login (official TWSE/TPEx data only).
# 2026-10-07: data/tw_quotes_latest.json and data/stock_daily/ had no schedule at all and sat stale for 7-13 days.
# 2026-10-16: the runner no longer commits or pushes anything; results go to the local store (scripts/local_data_store.py) and a OneDrive backup copy.
# ASCII only on purpose (Windows PowerShell 5.1 misreads non-ASCII in BOM-less scripts).
param([switch]$Push)   # kept so old scheduled-task command lines still work; ignored
$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'logs') | Out-Null
$Log = Join-Path $Repo 'logs\screener_cache.log'
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -FilePath $Log -Append -Encoding utf8 }
$LogBlock = { param($m) Log $m }

Set-Location $Repo
Log '--- start ---'
if ($Push) { Log 'note: -Push is ignored (the runner no longer pushes data)' }
. (Join-Path $PSScriptRoot 'runner_sync.ps1')
if (-not (Enter-RunnerLock 1800)) { Log 'ERROR: runner lock busy for 30 min; giving up this run'; exit 1 }
try {
    Sync-Runner -LogFn $LogBlock
    $env:PYTHONIOENCODING = 'utf-8'
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    python scripts/fetch_real_quotes.py 2>&1 | ForEach-Object { Log "quotes: $_" }
    if ($LASTEXITCODE -ne 0) { Log "ERROR: fetch_real_quotes exit code $LASTEXITCODE"; exit 1 }
    python scripts/build_screener_cache.py 2>&1 | ForEach-Object { Log "screener: $_" }
    if ($LASTEXITCODE -ne 0) { Log "ERROR: build_screener_cache exit code $LASTEXITCODE"; exit 1 }
    python scripts/local_data_store.py absorb 2>&1 | ForEach-Object { Log "store: $_" }
    python scripts/local_data_store.py backup 2>&1 | ForEach-Object { Log "store: $_" }
}
finally { Exit-RunnerLock }
Log '--- done ---'
