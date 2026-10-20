# run_service.ps1 - keeps one TXO-desk background service alive (restarts it 15s after it exits).
# ASCII only on purpose (Windows PowerShell 5.1 misreads non-ASCII in BOM-less scripts).
# Services: recorder (option quote recorder), bridge (advisor bridge 8765), monitor (rules patrol), server (account page 8770), patrol (AI patrol)
param([Parameter(Mandatory = $true)][ValidateSet('recorder', 'bridge', 'monitor', 'server', 'patrol')][string]$Name)

$ErrorActionPreference = 'Continue'
$Desk = Split-Path -Parent $PSScriptRoot                 # ...\trading room\desk
$Wt = (Resolve-Path (Join-Path $Desk '..\..')).Path      # worktree root
$Repo = (Resolve-Path (Join-Path $Wt '..\..\..')).Path   # main repo folder (holds the real trading room\brain\memory)
$Py = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
$Priv = Join-Path $env:USERPROFILE 'txo-private'
$LogDir = Join-Path $Priv 'desk\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

switch ($Name) {
    'recorder' { $Cwd = $Wt;   $SvcArgs = @('-I', 'tools\option_quote_recorder.py', '30', (Join-Path $Priv 'option_quotes')) }
    'bridge'   { $Cwd = $Wt;   $SvcArgs = @('"trading room\advisor_bridge.py"'); $env:ADVISOR_MEM_DIR = (Join-Path $Repo 'trading room\brain\memory') }
    'monitor'  { $Cwd = $Desk; $SvcArgs = @('monitor.py', 'T0', '30') }
    'server'   { $Cwd = $Desk; $SvcArgs = @('server.py', '8770') }
    'patrol'   { $Cwd = $Desk; $SvcArgs = @('patrol.py', 'T0') }
}
$env:PYTHONIOENCODING = 'utf-8'

while ($true) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') start $Name" | Out-File -FilePath (Join-Path $LogDir "$Name.log") -Append -Encoding utf8
    Start-Process -FilePath $Py -ArgumentList $SvcArgs -WorkingDirectory $Cwd -NoNewWindow -Wait `
        -RedirectStandardOutput (Join-Path $LogDir "$Name.out.log") -RedirectStandardError (Join-Path $LogDir "$Name.err.log")
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') exited, restart in 15s" | Out-File -FilePath (Join-Path $LogDir "$Name.log") -Append -Encoding utf8
    Start-Sleep -Seconds 15
}
