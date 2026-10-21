@echo off
rem 台選鳥（模擬）：規則巡邏 + 帳戶頁。兩個視窗最小化執行；關掉視窗就停止。
rem 帳戶頁網址 http://127.0.0.1:8770/
chcp 65001 >nul
cd /d "%~dp0"
start "台選鳥規則巡邏 T0" /min python monitor.py T0 30
start "台選鳥帳戶頁" /min python server.py 8770
timeout /t 3 >nul
start "" http://127.0.0.1:8770/
