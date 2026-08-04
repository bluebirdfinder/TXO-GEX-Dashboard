$u2 = 'https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date=20260701&response=json'
$r2 = Invoke-RestMethod -Uri $u2 -UserAgent 'Mozilla/5.0'
Write-Host "TWSE 2026-07 Title: $($r2.title)"
$r2.data | Select-Object -Last 5 | ForEach-Object { Write-Host ($_ -join ' | ') }

$u_otc = 'https://www.tpex.org.tw/web/stock/aftertrading/index_summary/idx_summary_result.php?l=zh-tw'
$r_otc = Invoke-RestMethod -Uri $u_otc -UserAgent 'Mozilla/5.0'
Write-Host "TPEx OTC Title: $($r_otc.reportDate)"
$r_otc.aaData | Select-Object -First 5 | ForEach-Object { Write-Host ($_ -join ' | ') }
