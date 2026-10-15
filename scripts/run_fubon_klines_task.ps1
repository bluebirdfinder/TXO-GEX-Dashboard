# run_fubon_klines_task.ps1 - scheduled wrapper: accumulate real Fubon futures intraday candles into the persistent local store.
# Runs in the dedicated runner clone (outside OneDrive), never in the shared working folder.
# Fubon serves only the LATEST session per call, so each session must be captured before the next one starts:
#   05:30 -> night session (just closed at 05:00) + previous day session
#   14:00 -> day session (closed 13:45) + the night session that ended at 05:00
# The scheduler option "run as soon as possible after a missed start" catches up after a powered-off PC; anything older
# than the latest session is unrecoverable and is listed in data/klines_gap_report.json.
# 2026-10-16: the runner no longer commits or pushes anything. The checkout is hard-reset to origin/main and the accumulated bars live in
# the local store (scripts/local_data_store.py), which is also copied once per run to the OneDrive backup folder. See scripts/runner_sync.ps1.
# ASCII only on purpose (Windows PowerShell 5.1 misreads non-ASCII in BOM-less scripts); the .env path is a parameter.
param(
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [switch]$Push   # kept so old scheduled-task command lines still work; ignored
)
$ErrorActionPreference = 'Continue'  # native tools write progress to stderr; PS 5.1 would abort on it under 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'logs') | Out-Null
$Log = Join-Path $Repo 'logs\fubon_klines.log'
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -FilePath $Log -Append -Encoding utf8 }
$LogBlock = { param($m) Log $m }

Set-Location $Repo
Log '--- start ---'
if ($Push) { Log 'note: -Push is ignored (the runner no longer pushes data)' }
. (Join-Path $PSScriptRoot 'runner_sync.ps1')
if (-not (Enter-RunnerLock 1800)) { Log 'ERROR: runner lock busy for 30 min; giving up this run'; exit 1 }
try {
    # Two simultaneous logins with the same API key were tested on 2026-09-27: both REST sessions worked, neither was kicked,
    # so this task runs even while live_price_server.py is up.
    Sync-Runner -LogFn $LogBlock
    foreach ($line in Get-Content -LiteralPath $EnvFile -Encoding UTF8) {
        $t = $line.Trim()
        if ($t -and -not $t.StartsWith('#') -and $t.Contains('=')) {
            $k, $v = $t.Split('=', 2)
            [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"', "'"), 'Process')
        }
    }
    $env:PYTHONIOENCODING = 'utf-8'
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8  # read python's UTF-8 output correctly in the log
    python scripts/fetch_fubon_futures_klines.py 2>&1 | ForEach-Object { Log "py: $_" }
    if ($LASTEXITCODE -ne 0) { Log "ERROR: fetch script exit code $LASTEXITCODE"; exit 1 }
    python scripts/local_data_store.py absorb 2>&1 | ForEach-Object { Log "store: $_" }
    python scripts/local_data_store.py backup 2>&1 | ForEach-Object { Log "store: $_" }
}
finally { Exit-RunnerLock }
Log '--- done ---'
