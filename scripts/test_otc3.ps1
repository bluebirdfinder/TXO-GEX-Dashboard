$u1 = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_index'
try {
    $r = Invoke-RestMethod -Uri $u1 -UserAgent 'Mozilla/5.0'
    Write-Host "tpex_mainboard_index success! Count: $($r.Count)"
    $r | Select-Object -Last 10 | ForEach-Object { Write-Host ($_ | ConvertTo-Json -Compress) }
} catch {
    Write-Host "Error 1: $_"
}

$u2 = 'https://www.tpex.org.tw/web/stock/iindex/index/idx_summary_result.php?l=zh-tw'
try {
    $r2 = Invoke-RestMethod -Uri $u2 -UserAgent 'Mozilla/5.0'
    Write-Host "idx_summary success!"
    $r2 | ConvertTo-Json -Depth 3 | Write-Host
} catch {
    Write-Host "Error 2: $_"
}
