@echo off
@chcp 65001 >nul
title TXO-GEX Multi-Source Live Gateway
echo ===================================================
echo ⚡ TXO-GEX 即時行情網關啟動中 (Port 8000)...
echo 優先順序: 1. 富邦 WebSocket -> 2. TradingView -> 3. 期交所 MIS
echo 正在為您開啟本機網關儀表板: http://localhost:8000
echo ===================================================
start http://localhost:8000
python scripts/live_price_server.py
pause
