$urls = @(
    'https://www.tpex.org.tw/openapi/v1/tpex_index',
    'https://www.tpex.org.tw/openapi/v1/tpex_index_daily',
    'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_index',
    'https://www.tpex.org.tw/openapi/v1/tpex_index_series',
    'https://www.tpex.org.tw/web/stock/iindex/index/idx_summary_result.php?l=zh-tw&d=115/07/31',
    'https://www.tpex.org.tw/web/stock/iindex/index/idx_summary_result.php?l=zh-tw&d=115/08/03'
)

foreach ($u in $urls) {
    try {
        $r = Invoke-RestMethod -Uri $u -UserAgent 'Mozilla/5.0'
        Write-Host "URL: $u -> SUCCESS!"
        $r | Select-Object -First 3 | ForEach-Object { Write-Host ($_ | ConvertTo-Json -Compress) }
    } catch {
        Write-Host "URL: $u -> Error: $_"
    }
}
