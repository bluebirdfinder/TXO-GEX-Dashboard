param([Parameter(Mandatory=$true)][string]$Scripts)
$ErrorActionPreference = 'Continue'
$ok = $true
function Check($name, $cond) { if ($cond) { "PASS $name" } else { "FAIL $name"; $script:ok = $false } }
$tmp = Join-Path $env:TEMP ("runner_sync_test_" + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$origin = Join-Path $tmp 'origin'; $runner = Join-Path $tmp 'runner'; $store = Join-Path $tmp 'store'
$env:TXO_LOCAL_STORE = $store
function Bars($times, $tag) { ($times | ForEach-Object { @{ time = $_; open = $tag; high = $tag; low = $tag; close = $tag; volume = 1 } }) }
function WriteCache($dir, $times, $tag) {
    New-Item -ItemType Directory -Force -Path (Join-Path $dir 'data') | Out-Null
    $c = @{ version = 't'; assets = @{ TXF = @{ timeframes = @{ '1M' = @(Bars $times $tag) } } } }
    $c | ConvertTo-Json -Depth 8 | Out-File -FilePath (Join-Path $dir 'data\klines_cache.json') -Encoding utf8
}
# --- "cloud" repo
git init -q -b main $origin
Set-Location $origin
git config user.email t@t; git config user.name t
New-Item -ItemType Directory -Force -Path (Join-Path $origin 'scripts') | Out-Null
Copy-Item (Join-Path $Scripts 'local_data_store.py') (Join-Path $origin 'scripts\')
Copy-Item (Join-Path $Scripts 'runner_sync.ps1') (Join-Path $origin 'scripts\')
WriteCache $origin @(1, 2, 3) 1
git add -A; git commit -q -m base
# --- runner clone
git clone -q $origin $runner
Set-Location $runner
git config user.email t@t; git config user.name t
# runner produced bars 100,101 locally and committed them (the OLD scheme), plus an uncommitted change
WriteCache $runner @(1, 2, 3, 100, 101) 9
git add -A; git commit -q -m "local data commit"
Add-Content (Join-Path $runner 'data\klines_cache.json') ' '
# the store (absorbed earlier from the runner's own data)
python scripts/local_data_store.py absorb | Out-Null
# cloud moves on: rewrites the SAME file (this is what used to conflict)
Set-Location $origin
WriteCache $origin @(1, 2, 3, 4, 5) 2
git add -A; git commit -q -m "cloud update"
# --- run Sync-Runner in the runner
Set-Location $runner
$logs = New-Object System.Collections.ArrayList
$LogBlock = { param($m) [void]$logs.Add($m) }
. (Join-Path $runner 'scripts\runner_sync.ps1')
Check 'lock acquired' (Enter-RunnerLock 5)
try { Sync-Runner -LogFn $LogBlock } finally { Exit-RunnerLock }
$head = (git rev-parse HEAD).Trim(); $oh = (git -C $origin rev-parse HEAD).Trim()
Check 'HEAD == origin/main after sync' ($head -eq $oh)
Check 'no rebase leftovers' (-not (Test-Path (Join-Path $runner '.git\rebase-merge')))
$st = git status --porcelain
Check 'only data file modified (overlay), nothing staged/unmerged' (($st | Where-Object { $_ -match '^(UU|AA|DU|UD|A |M )' }).Count -eq 0)
$j = Get-Content (Join-Path $runner 'data\klines_cache.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$times = @($j.assets.TXF.timeframes.'1M' | ForEach-Object { $_.time } | Sort-Object)
Check 'cloud bars (4,5) kept' (($times -contains 4) -and ($times -contains 5))
Check 'runner-only bars (100,101) overlaid back' (($times -contains 100) -and ($times -contains 101))
# a second sync must be stable
Check 'lock acquired (2)' (Enter-RunnerLock 5)
try { Sync-Runner -LogFn $LogBlock } finally { Exit-RunnerLock }
$j2 = Get-Content (Join-Path $runner 'data\klines_cache.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Check 'second sync keeps same bar count' (@($j2.assets.TXF.timeframes.'1M').Count -eq $times.Count)
# mutex: a second holder must time out while the lock is held
Check 'lock acquired (3)' (Enter-RunnerLock 5)
$r = Start-Job -ScriptBlock { $m = New-Object System.Threading.Mutex($false, 'Global\txo-runner-git'); $g = $m.WaitOne(1500); if ($g) { $m.ReleaseMutex() }; $g }
$res = Receive-Job -Wait $r
Exit-RunnerLock
Check 'second process cannot take the lock while held' ($res -eq $false)
Set-Location $env:TEMP
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
if ($ok) { "ALL PASS" } else { "SOME FAILED"; $logs | Select-Object -First 12 }
