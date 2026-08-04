$twii = Invoke-RestMethod -Uri 'https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII?range=5d&interval=1d' -UserAgent 'Mozilla/5.0'
$two  = Invoke-RestMethod -Uri 'https://query1.finance.yahoo.com/v8/finance/chart/%5ETWO?range=5d&interval=1d' -UserAgent 'Mozilla/5.0'

Write-Host "=== TAIEX (^TWII) ==="
$timestamps = $twii.chart.result[0].timestamp
$closes = $twii.chart.result[0].indicators.quote[0].close
for ($i = 0; $i -lt $timestamps.Count; $i++) {
    $dt = ([datetimeOffset]::FromUnixTimeSeconds($timestamps[$i])).LocalDateTime.ToString("yyyy-MM-dd")
    Write-Host "$dt : $($closes[$i])"
}

Write-Host "=== OTC (^TWO) ==="
$timestamps_two = $two.chart.result[0].timestamp
$closes_two = $two.chart.result[0].indicators.quote[0].close
for ($i = 0; $i -lt $timestamps_two.Count; $i++) {
    $dt = ([datetimeOffset]::FromUnixTimeSeconds($timestamps_two[$i])).LocalDateTime.ToString("yyyy-MM-dd")
    Write-Host "$dt : $($closes_two[$i])"
}
