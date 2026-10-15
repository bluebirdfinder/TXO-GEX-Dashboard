# run_live_server_task.ps1 - keeps scripts/live_price_server.py running for the trading room (started at Windows logon).
# Runs in the dedicated runner clone (outside OneDrive). Loopback-only server (127.0.0.1:8000), no admin rights needed.
# Loop: hard-sync the checkout to origin/main (+ overlay the local data store, see scripts/runner_sync.ps1) -> load Fubon credentials
# from the .env file into THIS process only -> run the server -> if it exits, wait 15 s and start it again.
# 2026-10-16: was `git pull --rebase --autostash`, which kept failing on data-file conflicts and started the server on stale code.
# ASCII only (Windows PowerShell 5.1 misreads non-ASCII in BOM-less scripts).
param([Parameter(Mandatory = $true)][string]$EnvFile)
$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'logs') | Out-Null
$Log = Join-Path $Repo 'logs\live_price_server.log'
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -FilePath $Log -Append -Encoding utf8 }
$LogBlock = { param($m) Log $m }
Set-Location $Repo
. (Join-Path $PSScriptRoot 'runner_sync.ps1')
while ($true) {
    if ((Test-Path $Log) -and ((Get-Item $Log).Length -gt 5MB)) { Move-Item -Force $Log "$Log.old" }
    Log '--- starting live_price_server ---'
    # A klines/screener task may hold the lock for a few minutes; wait for it so we never reset the checkout under a running task.
    if (Enter-RunnerLock 600) {
        try { Sync-Runner -LogFn $LogBlock } finally { Exit-RunnerLock }
    } else {
        Log 'WARN: runner lock busy for 10 min; starting the server without syncing'
    }
    foreach ($line in Get-Content -LiteralPath $EnvFile -Encoding UTF8) {
        $t = $line.Trim()
        if ($t -and -not $t.StartsWith('#') -and $t.Contains('=')) {
            $k, $v = $t.Split('=', 2)
            [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"', "'"), 'Process')
        }
    }
    $env:PYTHONIOENCODING = 'utf-8'
    python scripts/live_price_server.py 2>&1 | ForEach-Object { Log "srv: $_" }
    Log "server exited (code $LASTEXITCODE); restarting in 15 s"
    Start-Sleep -Seconds 15
}
