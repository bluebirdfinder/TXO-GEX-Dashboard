$filePath = "result.json"
$lines = Select-String -Path $filePath -Pattern "出場！"

$totalProfit = 0.0

foreach ($lineObj in $lines) {
    $line = $lineObj.Line
    
    $sym = ""
    if ($line -match '】([A-Z0-9.!]+)\s*\(') { $sym = $Matches[1] }
    
    $en = 0.0
    if ($line -match '進場價：([\d.]+)') { $en = [double]$Matches[1] }
    
    $ex = 0.0
    if ($line -match '出場價：([\d.]+)') { $ex = [double]$Matches[1] }
    
    $dir = "Long"
    if ($line -match '空單') { $dir = "Short" }
    
    $mult = 1.0
    if ($sym -like "*BTC*") { $mult = 0.1 }
    elseif ($sym -like "*ETH*") { $mult = 1.0 }
    elseif ($sym -like "*NQ*" -or $sym -like "*MNQ*") { $mult = 2.0 }
    elseif ($sym -like "*ES*" -or $sym -like "*MES*") { $mult = 5.0 }
    elseif ($sym -like "*GC*" -or $sym -like "*MGC*") { $mult = 10.0 }
    elseif ($sym -like "*CL*" -or $sym -like "*MCL*") { $mult = 10.0 }
    elseif ($sym -like "*TX*" -or $sym -like "*MTX*") { $mult = 10.0 }
    
    $diff = 0.0
    if ($dir -eq "Long") { $diff = $ex - $en } else { $diff = $en - $ex }
    
    $profit = $diff * $mult
    $totalProfit += $profit
}

Write-Host "Total Trades Analyzed: $($lines.Count)"
Write-Host "Total Profit (Simulated Micros): $totalProfit"
