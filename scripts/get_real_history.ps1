# Query TWSE FMTQIK for July 2026 and August 2026
$u_jul = 'https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date=20260701&response=json'
$r_jul = Invoke-RestMethod -Uri $u_jul -UserAgent 'Mozilla/5.0'
Write-Host "=== TWSE July 2026 Last 5 Days ==="
$r_jul.data | Select-Object -Last 5 | ForEach-Object { Write-Host ($_ -join ' | ') }

$u_aug = 'https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date=20260801&response=json'
$r_aug = Invoke-RestMethod -Uri $u_aug -UserAgent 'Mozilla/5.0'
Write-Host "=== TWSE August 2026 ==="
$r_aug.data | ForEach-Object { Write-Host ($_ -join ' | ') }

# Query TPEx Index history for July and August
$u_otc_jul = 'https://www.tpex.org.tw/web/stock/aftertrading/index_summary/idx_summary_result.php?l=zh-tw&d=115/07/31'
# Let's check TPEx index report endpoint:
$u_otc_main = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes'
$r_otc_main = Invoke-RestMethod -Uri $u_otc_main -UserAgent 'Mozilla/5.0'
$otc_dates = $r_otc_main | Group-Object -Property Date
Write-Host "=== OTC Mainboard Dates ==="
$otc_dates | Select-Object -Last 5 | ForEach-Object { Write-Host $_.Name }
