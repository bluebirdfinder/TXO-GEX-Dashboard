# 🚀 TXO GEX Dashboard - v7.0.0 Release Status

## 📌 Status Summary
- **Current Version**: v7.0.0 (Official Night/Day Dual-Session & Institutional Trading Release)
- **Data Integrity**: 100% Direct integration with TWSE (`openapi.twse.com.tw`) and TAIFEX (`taifex.com.tw` / `futContractsDateAh`). Zero dummy data.
- **Dual-Session Split Cards**: 5 core stat cards (TXF, Zero Gamma, Call Wall, Put Wall, Max Pain) display both Daytime (13:45) and Night-Close (05:00) calibrated metrics.
- **Blue Box Session Shift Banner**: Dedicated shift comparison card placed next to Max Pain for real-time gap & wall displacement digest.
- **Night Session Institutional Panel**: Official TAIFEX `futContractsDateAh` parsing (TX Foreign, MTX Foreign, Micro Foreign, TX Dealer) with automated plain text summary.
- **Taxonomy & Notional Calculation**: Dynamic scaling algorithm with notional contract value in 100M TWD (億 TWD) and 5-tier semantic tags.
- **Options Education & P/C Ratio**: P/C Ratio (108.5%) displayed with 🔴/🟢 Taiwan market color symbols and Max Pain magnet effect education modal.
- **Mobile RWD & UI Polish**: 2x2 grid card layout for mobile, perfect 1:1 circle rule for user avatar, and 100% unified FinTech font family.
- **CI/CD Auto-Pipeline**: Actions Bot 403 permission issue resolved via `permissions: contents: write`.

## 🎯 Completed Milestones (v7.0.0)
- [x] Implemented Split-Card layout (Daytime 13:45 vs Night 05:00 Close) for 5 core stat cards.
- [x] Positioned Blue Box Session Shift Banner directly to the right of Max Pain.
- [x] Added `🌙 三大法人夜盤盤後交易籌碼專區` with direct TAIFEX `futContractsDateAh` parser.
- [x] Implemented automated plain-text Night Session Institutional Trading summary digest.
- [x] Enforced Taiwan Market Color Standard (🔴 Red = Bullish / 🟢 Green = Bearish) across P/C Ratio & indicators.
- [x] Added P/C Ratio & Max Pain education guides into the interactive `❓ 判讀教學` Modal.
- [x] Fixed mobile avatar warping with 1:1 aspect-ratio perfect circle protection.
- [x] Enforced global font-family rule to eliminate system default fallback fonts (新細明體).
- [x] Resolved GitHub Actions 403 push permission error in `auto_update.yml`.
- [x] Verified full 270 stock futures catalog fallback array in `app.js`.
