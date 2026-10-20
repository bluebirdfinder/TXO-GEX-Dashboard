# register_tasks.ps1 - registers 5 "at log on" tasks (TXO-Desk-*) for the current user; no admin needed.
# Re-run safely: existing TXO-Desk-* tasks are replaced. Remove with:  Get-ScheduledTask TXO-Desk-* | Unregister-ScheduledTask -Confirm:$false
# ASCII only on purpose. Each task runs run_service.ps1 through the shared hidden launcher so no window flashes.
$ErrorActionPreference = 'Stop'
$Here = $PSScriptRoot
$Runner = Join-Path $Here 'run_service.ps1'
$Wt = (Resolve-Path (Join-Path $Here '..\..\..')).Path
$Launcher = Join-Path $env:USERPROFILE 'tools\hidden_launch\hidden_launch.pyw'
$Pyw = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\pythonw.exe'
if (-not (Test-Path $Launcher)) { throw "hidden launcher not found: $Launcher" }
if (-not (Test-Path $Pyw)) { throw "pythonw not found: $Pyw" }

foreach ($n in 'recorder', 'bridge', 'monitor', 'server', 'patrol') {
    $arg = "`"$Launcher`" --cwd `"$Wt`" -- powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -Name $n"
    $action = New-ScheduledTaskAction -Execute $Pyw -Argument $arg
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName "TXO-Desk-$n" -Action $action -Trigger $trigger -Settings $settings -User $env:USERNAME `
        -Description "TXO desk (simulated trading) background service: $n. Started at log on; run_service.ps1 restarts it if it exits." -Force | Out-Null
    "registered TXO-Desk-$n"
}
