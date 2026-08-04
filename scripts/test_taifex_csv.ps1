$u = 'https://www.taifex.com.tw/cht/3/futDailyMarketExport?queryType=2&marketCode=0&commodity_id=TX&queryDate=2026/07/31'
try {
    $r = Invoke-WebRequest -Uri $u -UserAgent 'Mozilla/5.0'
    $lines = $r.Content -split "`n"
    Write-Host "Lines count: $($lines.Count)"
    $lines | Select-Object -First 10 | ForEach-Object { Write-Host $_ }
} catch {
    Write-Host "Error: $_"
}
