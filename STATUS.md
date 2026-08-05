# 🚀 TXO GEX Dashboard - v9.1.0 Release Status (Fubon Neo SDK Live & Precision Sync)

## 📌 Status Summary
- **Current Version**: v9.1.0 (Engine v31.0)
- **Fubon Neo API SDK**: 🟢 **100% Authenticated & Active (`fubon_neo` v2.2.8)** - Direct WebSocket Live Streaming API with Zero-Trust Security.
- **Data Integrity**: Direct integration with Fubon Neo SDK, TWSE MIS & OpenAPI (`FMTQIK`), TPEx OpenAPI, and TAIFEX (`taifex.com.tw` / `futContractsDateAh` / `optDailyMarketReport`).
- **Session Timing & Date Annotations**: 3-Day Table features explicit timing badges for Day Session (`📅 M/DD 13:45`) and Next-Day Night Close (`🌙 M/DD 05:00收盤`).
- **Real Open Interest GEX Matrix**: Direct parsing of TAIFEX Options Daily Market Report for strike-by-strike Real Call/Put OI.
- **Data Freshness LED**: Real-time LED indicator (🟢 Fresh <4h / 🟡 Aging 4-12h / 🔴 Expired >12h) in header.
- **LocalStorage Resilience**: Automatic offline/network fallback caching with warning banner.
- **Overlay Compare Mode**: Interactive side-by-side comparison of T-Day vs T-Night (Live) GEX distributions.
- **3-Day 6-Session Snapshots**: Full historical trajectory for T-2 Day, T-2 Night, T-1 Day, T-1 Night, T Day, T Night (Live).

## 🎯 Completed Milestones (v9.1.0)
- [x] Successfully authenticated Fubon Neo SDK (`v2.2.8`) with `apikey_login` and local Zero-Trust `.env` configuration.
- [x] Restored `app.js` syntax integrity and all stat card rendering pipelines.
- [x] Added dynamic TWSE FMTQIK and TPEx API historical query modules in `fetch_and_calc.py`.
- [x] Integrated real TAIFEX TXO Option Open Interest parser (`fetch_official_taifex_txo_oi`) for GEX calculations.
- [x] Annotated 3-day table headers and rows with explicit day session and next-day night close dates.
- [x] Re-encrypted & synchronized raw JSON payloads (`gex_data.json`, `encrypted_gex.json`).
- [x] Updated all repository documentation (`README.md`, `PROJECT_HANDOVER.md`, `STATUS.md`).
