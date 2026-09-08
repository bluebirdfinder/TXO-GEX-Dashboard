$filePath = "ChatExport_2026-05-15\result.json"
$jsonText = [System.IO.File]::ReadAllText($filePath)
$data = $jsonText | ConvertFrom-Json

$totalProfit = 0
$tradeCount = 0
$signalCount = 0
$dailyStats = @{}

foreach ($m in $data.messages) {
    if ($m.type -ne "message") { continue }
    
    $text = ""
    if ($m.text -is [System.Collections.ArrayList] -or $m.text -is [Array]) {
        foreach ($part in $m.text) {
            if ($part -is [string]) { $text += $part }
            else { $text += $part.text }
        }
    } else {
        $text = $m.text
    }
    
    if ($text -notmatch "5K") { continue }
    
    $date = $m.date.Split("T")[0]
    if (-not $dailyStats.ContainsKey($date)) { $dailyStats[$date] = @{total=0; profit=0} }
    $dailyStats[$date].total++
    $signalCount++
    
    if ($text -match ":([\d.]+)\s+.+:([\d.]+)") {
        $en = [double]$Matches[1]
        $ex = [double]$Matches[2]
        
        $sym = ""
        if ($text -match "\]([A-Z0-9.!]+)") { $sym = $Matches[1] }
        
        $dir = "Long"
        # Check for Short using the chart emoji hex or assuming based on price movement for now
        # Actually, let's just check for the presence of certain characters via their int values
        $isShort = $false
        for ($i=0; $i -lt $text.Length; $i++) {
            if ([int]$text[$i] -eq 31354) { $isShort = $true; break } # 31354 is '空'
        }
        if ($isShort) { $dir = "Short" }
        
        $mult = 1.0
        if ($sym -match "BTC") { $mult = 0.1 }
        elseif ($sym -match "ETH") { $mult = 1.0 }
        elseif ($sym -match "NQ") { $mult = 2.0 }
        elseif ($sym -match "ES") { $mult = 5.0 }
        elseif ($sym -match "GC") { $mult = 10.0 }
        elseif ($sym -match "CL") { $mult = 10.0 }
        elseif ($sym -match "TX") { $mult = 10.0 }
        
        $diff = if ($dir -eq "Long") { $ex - $en } else { $en - $ex }
        $p = $diff * $mult
        
        $totalProfit += $p
        $dailyStats[$date].profit += $p
        $tradeCount++
    }
}

Write-Output "Signals: $signalCount"
Write-Output "Trades: $tradeCount"
Write-Output "Profit: $totalProfit"
foreach ($d in ($dailyStats.Keys | Sort-Object)) {
    Write-Output "$d : Count $($dailyStats[$d].total) | Profit $($dailyStats[$d].profit)"
}
