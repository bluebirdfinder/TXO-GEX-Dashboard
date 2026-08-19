@echo off
title TXO-GEX Multi-Source Live Gateway
echo ===================================================
echo ⚡ TXO-GEX 即時行情網關啟動中 (Port 8000)...
echo 優先順序: 1. 富邦 WebSocket -> 2. TradingView -> 3. 期交所 MIS
echo ===================================================
python scripts/live_price_server.py
pause
