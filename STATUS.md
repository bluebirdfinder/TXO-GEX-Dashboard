# 🚀 TXO GEX Dashboard - v8.0.0 Release Status (Final Release)

## 📌 Status Summary
- **Current Version**: v8.0.0 (3-Day 6-Session Snapshot & Microstructure Express Release)
- **Data Integrity**: 100% Direct integration with TWSE MIS (`mis.twse.com.tw`) & TAIFEX (`taifex.com.tw` / `futContractsDateAh`). Zero dummy data.
- **3-Day 6-Session Snapshots**: Full historical trajectory for T-2 Day, T-2 Night, T-1 Day, T-1 Night, T Day, T Night (Live) with interactive snapshot toggle bar.
- **Microstructure Express Digest**: Automated `generate_microstructure_summary()` backend generator with Positive/Negative Gamma regime tags, Flip Point proximity alerts (<100 pts), and Call/Put Wall displacement digest.
- **Official Indices Alignment**: Exact live index alignment (TAIEX `43,386.41`, OTC `362.89`, Day TXF `43,230.0`, Night TXF `42,650.0`).
- **Night Session Institutional Panel**: Official TAIFEX `futContractsDateAh` parsing (TX Foreign, MTX Foreign, Micro Foreign, TX Dealer) with automated plain text summary.
- **UI & Mobile Polish**: Unified FinTech font-family, 1:1 perfect circle user avatar protection, and responsive 2x2 card grid on mobile.

## 🎯 Completed Milestones (v8.0.0)
- [x] Implemented 3-Day 6-Session Snapshot history generator in `fetch_and_calc.py`.
- [x] Created interactive 6-session snapshot selector bar (`#history-session-selector`) in `index.html` & `app.js`.
- [x] Created `📌 日夜盤微觀結構速報` panel with dynamic theme border (Red Bullish / Green Bearish).
- [x] Aligned TAIEX (`43,386.41`) & OTC (`362.89`) using official TWSE MIS API.
- [x] Aligned Day TXF (`43,230.0`) & Night TXF (`42,650.0`) using TAIFEX official endpoints.
- [x] Enforced global font-family rule to eliminate system default fallback fonts (新細明體).
- [x] Fixed mobile avatar warping with 1:1 aspect-ratio perfect circle protection.
- [x] Updated Fubon SDK API security roadmap & Volume-Weighted GEX (vGEX) formula in documentation.
- [x] Updated all documentation files (`README.md`, `PROJECT_HANDOVER.md`, `OPTIONS_CHEATSHEET.md`, `STATUS.md`).
