@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo 幕僚鳥橋接啟動中（關閉此視窗即停止）...
python "trading room\advisor_bridge.py"
pause
