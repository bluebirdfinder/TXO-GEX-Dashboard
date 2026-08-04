$dates = @('2026/07/28', '2026/07/29', '2026/07/30', '2026/07/31', '2026/08/03')

foreach ($d in $dates) {
    $body = "queryType=2&marketCode=0&commodity_id=TX&queryDate=$d"
    try {
        $r = Invoke-WebRequest -Uri 'https://www.taifex.com.tw/cht/3/futDailyMarketReport' -Method Post -Body $body -ContentType 'application/x-www-form-urlencoded' -UserAgent 'Mozilla/5.0'
        $html = $r.Content
        if ($html -match 'TX\s+.*?<td>(\d{1,2},\d{3})</td>') {
            Write-Host "$d TX Day Close: $($Matches[1])"
        } else {
            Write-Host "$d Parse result length: $($html.Length)"
        }
    } catch {
        Write-Host "$d Error: $_"
    }
}
