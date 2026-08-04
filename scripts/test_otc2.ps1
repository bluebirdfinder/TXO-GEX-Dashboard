$u = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes'
try {
    $r = Invoke-RestMethod -Uri $u -UserAgent 'Mozilla/5.0'
    Write-Host "OpenAPI success! Count: $($r.Count)"
    $r | Select-Object -First 5 | ForEach-Object { Write-Host ($_ | ConvertTo-Json -Compress) }
} catch {
    Write-Host "OpenAPI error: $_"
}

$u2 = 'https://www.tpex.org.tw/web/stock/aftertrading/index_summary/summary_result.php?l=zh-tw'
try {
    $r2 = Invoke-RestMethod -Uri $u2 -UserAgent 'Mozilla/5.0'
    Write-Host "Summary result success!"
    $r2.aaData | Select-Object -First 5 | ForEach-Object { Write-Host ($_ -join ' | ') }
} catch {
    Write-Host "Summary error: $_"
}
