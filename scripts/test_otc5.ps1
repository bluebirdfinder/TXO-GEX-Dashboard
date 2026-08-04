$u = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes'
$r = Invoke-RestMethod -Uri $u -UserAgent 'Mozilla/5.0'

# Find SecuritiesCompanyCode for 櫃買指數 or OTC ETFs / index components if available
# Or let's inspect all items where SecuritiesCompanyCode matches index or '00'
$r | Where-Object { $_.SecuritiesCompanyCode -like '00*' -or $_.CompanyName -like '*指數*' } | Select-Object -First 10 | ForEach-Object { Write-Host ($_ | ConvertTo-Json -Compress) }
