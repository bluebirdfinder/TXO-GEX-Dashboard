# run_fubon_klines_task.ps1 - scheduled wrapper: accumulate real Fubon futures intraday candles, then commit (and optionally push).
# Runs in the dedicated runner clone (outside OneDrive), never in the shared working folder.
# Fubon serves only the LATEST session per call, so each session must be captured before the next one starts:
#   05:30 -> night session (just closed at 05:00) + previous day session
#   14:00 -> day session (closed 13:45) + the night session that ended at 05:00
# The scheduler option "run as soon as possible after a missed start" catches up after a powered-off PC; anything older
# than the latest session is unrecoverable and is listed in data/klines_gap_report.json.
# ASCII only on purpose (Windows PowerShell 5.1 misreads non-ASCII in BOM-less scripts); the .env path is a parameter.
param(
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [switch]$Push
)
$ErrorActionPreference = 'Continue'  # native tools write progress to stderr; PS 5.1 would abort on it under 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'logs') | Out-Null
$Log = Join-Path $Repo 'logs\fubon_klines.log'
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -FilePath $Log -Append -Encoding utf8 }

Set-Location $Repo
Log '--- start ---'
# One active login per API key may be enforced: skip if the live price server is running.
if (Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object { $_.CommandLine -like '*live_price_server*' }) {
    Log 'SKIP: live_price_server.py is running (would double-login). Retry at the next scheduled time.'
    exit 0
}
git pull --rebase --autostash origin main 2>&1 | ForEach-Object { Log "git: $_" }
foreach ($line in Get-Content -LiteralPath $EnvFile -Encoding UTF8) {
    $t = $line.Trim()
    if ($t -and -not $t.StartsWith('#') -and $t.Contains('=')) {
        $k, $v = $t.Split('=', 2)
        [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"', "'"), 'Process')
    }
}
$env:PYTHONIOENCODING = 'utf-8'
python scripts/fetch_fubon_futures_klines.py 2>&1 | ForEach-Object { Log "py: $_" }
if ($LASTEXITCODE -ne 0) { Log "ERROR: fetch script exit code $LASTEXITCODE"; exit 1 }

git add data/klines_cache.json data/klines_gap_report.json
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Log 'no data change'; exit 0 }
git commit -m "data: accumulate Fubon futures intraday candles ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))" 2>&1 | ForEach-Object { Log "git: $_" }
if ($Push) {
    git pull --rebase --autostash origin main 2>&1 | ForEach-Object { Log "git: $_" }
    git push origin HEAD:main 2>&1 | ForEach-Object { Log "git: $_" }
    if ($LASTEXITCODE -ne 0) { Log 'ERROR: push failed'; exit 1 }
}
Log '--- done ---'
