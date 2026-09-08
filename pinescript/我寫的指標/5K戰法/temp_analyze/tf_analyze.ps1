$filePath = "ChatExport_2026-05-15\result.json"
$jsonText = [System.IO.File]::ReadAllText($filePath)
$data = $jsonText | ConvertFrom-Json

$tfStats = @{}

foreach ($m in $data.messages) {
    if ($m.type -ne "message") { continue }
    $text = ""
    if ($m.text -is [System.Collections.ArrayList] -or $m.text -is [Array]) {
        foreach ($part in $m.text) { if ($part -is [string]) { $text += $part } else { $text += $part.text } }
    } else { $text = $m.text }
    
    if ($text -notmatch "5K 戰法 V4") { continue }
    
    $tf = "Unknown"
    if ($text -match "\((?<tf>[^\)]+)\)") { $tf = $Matches.tf }
    
    if (-not $tfStats.ContainsKey($tf)) { $tfStats[$tf] = @{trades=0; wins=0; profit=0.0; signals=0} }
    $tfStats[$tf].signals++
    
    if ($text -match ":([\d.]+)\s+.+:([\d.]+)") {
        $en = [double]$Matches[1]
        $ex = [double]$Matches[2]
        
        $sym = ""
        if ($text -match "\]([A-Z0-9.!]+)") { $sym = $Matches[1] }
        
        $isShort = $false
        for ($i=0; $i -lt $text.Length; $i++) { if ([int]$text[$i] -eq 31354) { $isShort = $true; break } }
        $dir = if ($isShort) { "Short" } else { "Long" }
        
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
        
        $tfStats[$tf].trades++
        $tfStats[$tf].profit += $p
        if ($p -gt 0) { $tfStats[$tf].wins++ }
    }
}

Write-Output "Timeframe | Trades | WinRate | TotalProfit"
Write-Output "------------------------------------------"
foreach ($tf in ($tfStats.Keys | Sort-Object)) {
    $s = $tfStats[$tf]
    $wr = if ($s.trades -gt 0) { ($s.wins / $s.trades * 100).ToString("F1") + "%" } else { "0%" }
    Write-Output "$($tf.PadRight(10)) | $($s.trades.ToString().PadRight(6)) | $($wr.PadRight(7)) | $($s.profit.ToString("F2"))"
}
