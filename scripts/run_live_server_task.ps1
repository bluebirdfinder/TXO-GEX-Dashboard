# run_live_server_task.ps1 - keeps scripts/live_price_server.py running for the trading room (started at Windows logon).
# Runs in the dedicated runner clone (outside OneDrive). Loopback-only server (127.0.0.1:8000), no admin rights needed.
# Loop: git pull (latest main) -> load Fubon credentials from the .env file into THIS process only -> run the server ->
# if it exits, wait 15 s and start it again. ASCII only (Windows PowerShell 5.1 misreads non-ASCII in BOM-less scripts).
param([Parameter(Mandatory = $true)][string]$EnvFile)
$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'logs') | Out-Null
$Log = Join-Path $Repo 'logs\live_price_server.log'
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -FilePath $Log -Append -Encoding utf8 }
Set-Location $Repo
while ($true) {
    if ((Test-Path $Log) -and ((Get-Item $Log).Length -gt 5MB)) { Move-Item -Force $Log "$Log.old" }
    Log '--- starting live_price_server ---'
    git pull --rebase --autostash origin main 2>&1 | ForEach-Object { Log "git: $_" }
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
