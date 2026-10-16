@echo off
@chcp 65001 >nul
title 尋鳥戰情室 + 幕僚鳥（報價服務）
cd /d "%~dp0"
echo ===================================================
echo  尋鳥戰情室：即時報價服務 (8000) + 幕僚鳥橋接 (8765)
echo ===================================================
netstat -ano | findstr /R /C:"127.0.0.1:8000 .*LISTENING" >nul
if %errorlevel%==0 (
  echo.
  echo [注意] 8000 埠已經有一個報價服務在跑（可能是舊的 start_live.bat）。
  echo        請先關掉舊的視窗，再重新執行這個檔案，
  echo        否則 8000 讀到的會是舊版檔案，看不到幕僚鳥。
  echo.
  pause
  exit /b 1
)
start "幕僚鳥橋接（關掉此視窗＝幕僚鳥停止）" /min python "trading room\advisor_bridge.py"
start "" "http://localhost:8000/trading%%20room/room.html"
python scripts\live_price_server.py
pause
