# TPEx OTC Index History API
$u1 = 'https://www.tpex.org.tw/web/stock/aftertrading/index_summary/idx_summary_result.php?l=zh-tw&d=115/07/31'
$r1 = Invoke-RestMethod -Uri $u1 -UserAgent 'Mozilla/5.0'
Write-Host "TPEx 115/07/31: $($r1.reportTitle)"
$r1.aaData | ForEach-Object { Write-Host ($_ -join ' | ') }

$u2 = 'https://www.tpex.org.tw/web/stock/aftertrading/index_summary/idx_summary_result.php?l=zh-tw&d=115/08/03'
$r2 = Invoke-RestMethod -Uri $u2 -UserAgent 'Mozilla/5.0'
Write-Host "TPEx 115/08/03: $($r2.reportTitle)"
$r2.aaData | ForEach-Object { Write-Host ($_ -join ' | ') }
