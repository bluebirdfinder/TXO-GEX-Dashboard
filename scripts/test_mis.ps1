$u = 'https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw|otc_o00.tw'
$r = Invoke-RestMethod -Uri $u -UserAgent 'Mozilla/5.0'
$r.msgArray | ForEach-Object {
    Write-Host "Code: $($_.c), Name: $($_.n), Z: $($_.z), Y: $($_.y)"
}
