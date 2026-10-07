# run_screener_cache_task.ps1 - scheduled wrapper: refresh daily stock quotes -> rebuild screener cache + per-stock daily K shards -> commit (optional push).
# Why local: build_screener_cache.py imports the owner's PRIVATE indicator modules (C:\Users\mingi\txo-private\screener-indicators,
# not in the public repo), so it cannot run in GitHub Actions. Runs in the dedicated runner clone (outside OneDrive).
# Suggested schedule: weekdays 16:30 (TWSE/TPEx daily files are published by then). Needs no Fubon login (official TWSE/TPEx data only).
# 2026-10-07: data/tw_quotes_latest.json and data/stock_daily/ had no schedule at all and sat stale for 7-13 days.
# ASCII only on purpose (Windows PowerShell 5.1 misreads non-ASCII in BOM-less scripts).
param([switch]$Push)
$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'logs') | Out-Null
$Log = Join-Path $Repo 'logs\screener_cache.log'
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -FilePath $Log -Append -Encoding utf8 }

Set-Location $Repo
Log '--- start ---'
git pull --rebase --autostash origin main 2>&1 | ForEach-Object { Log "git: $_" }
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

python scripts/fetch_real_quotes.py 2>&1 | ForEach-Object { Log "quotes: $_" }
if ($LASTEXITCODE -ne 0) { Log "ERROR: fetch_real_quotes exit code $LASTEXITCODE"; exit 1 }
python scripts/build_screener_cache.py 2>&1 | ForEach-Object { Log "screener: $_" }
if ($LASTEXITCODE -ne 0) { Log "ERROR: build_screener_cache exit code $LASTEXITCODE"; exit 1 }

git add data/tw_quotes_latest.json data/screener_cache.json data/stock_daily
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Log 'no data change'; exit 0 }
git commit -m "data: refresh daily stock quotes, screener cache and stock daily K shards ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))" 2>&1 | ForEach-Object { Log "git: $_" }
if ($Push) {
    git pull --rebase --autostash origin main 2>&1 | ForEach-Object { Log "git: $_" }
    git push origin HEAD:main 2>&1 | ForEach-Object { Log "git: $_" }
    if ($LASTEXITCODE -ne 0) { Log 'ERROR: push failed'; exit 1 }
}
Log '--- done ---'
