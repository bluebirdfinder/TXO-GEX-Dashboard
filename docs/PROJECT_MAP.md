# PROJECT_MAP（自動產生，請勿手改）

> 產生時間 2026-11-12 11:23｜git HEAD `b2a6793`｜程式檔 115 個、資料檔 41 個
> 重新產生：`python tools/build_project_map.py`｜查影響範圍：`python tools/build_project_map.py --impact <檔名>`
> **限制**：讀／寫是用關鍵字推測；動態組出的檔名抓不到；只到檔案層級。改動前仍要打開檔案確認，這份是「先看哪裡」的索引，不是真相。

## 1. 入口與排程（什麼東西會自己跑、跑了會呼叫誰）

| 入口 | 排程／說明 | 直接呼叫 |
|---|---|---|
| `.github/workflows/auto_update.yml` | `3 21 * * 0-4` 05:03 TWD (Night Session Clo；`33 21 * * 0-4` 05:33 TWD (Night Session Set；`3 22 * * 0-4` 06:03 TWD (Night Session Fai …共 9 個時間點 | fetch_and_calc_vision.py、fetch_market_klines.py、fetch_real_quotes.py、gex_v2_daily.py |
| `scripts/run_fubon_klines_task.ps1` | run_fubon_klines_task.ps1 - scheduled wrapper: accumulate real Fubon f | fetch_fubon_futures_klines.py、local_data_store.py、runner_sync.ps1 |
| `scripts/run_live_server_task.ps1` | run_live_server_task.ps1 - keeps scripts/live_price_server.py running  | live_price_server.py、runner_sync.ps1 |
| `scripts/run_screener_cache_task.ps1` | run_screener_cache_task.ps1 - scheduled wrapper: refresh daily stock q | build_screener_cache.py、fetch_real_quotes.py、local_data_store.py、runner_sync.ps1 |
| `scripts/runner_sync.ps1` | runner_sync.ps1 - dot-sourced by the runner wrappers (run_live_server_ | local_data_store.py |
| `scripts/test_runner_sync.ps1` | --- "cloud" repo | local_data_store.py、runner_sync.ps1 |
| `start_live.bat` | — | live_price_server.py |
| `start_live_with_advisor.bat` | — | room.html、live_price_server.py、advisor_bridge.py、room.html |
| `trading room/desk/autostart/register_tasks.ps1` | register_tasks.ps1 - registers 5 "at log on" tasks (TXO-Desk-*) for th | run_service.ps1 |
| `trading room/desk/autostart/run_service.ps1` | run_service.ps1 - keeps one TXO-desk background service alive (restart | option_quote_recorder.py、advisor_bridge.py、monitor.py、patrol.py、server.py |
| `trading room/desk/start_desk.bat` | — | monitor.py、server.py |
| `trading room/start_advisor.bat` | — | advisor_bridge.py |

## 2. 資料檔流向（改資料格式前先看誰讀它）

| 資料檔 | 誰寫入（推測） | 誰讀取（推測） |
|---|---|---|
| `embedded_data.js` | fetch_and_calc_vision.py | index.html、bump_version.py、room.html |
| `encrypted_gex.json` | encrypt.py、fetch_and_calc_vision.py | app.js、do_encrypt.ps1、encrypt.ps1、update_and_encrypt.ps1 |
| `gex_data.json` | fetch_and_calc_vision.py | app.js、audit_vs_official.py、bump_version.py、do_encrypt.ps1、encrypt.ps1、encrypt.py、generate_social_card.py、gex_v2_daily.py …+6 |
| `gex_line_observations.json` | fetch_and_calc_vision.py | — |
| `gex_v2_history.json` | gex_v2_daily.py | gex_v2_backfill.py、gex_v2_backtest.py |
| `institutional_snapshots.json` | fetch_and_calc_vision.py | room_retail.js |
| `klines_cache.json` | backfill_taifex_klines.py、fetch_fubon_futures_klines.py、fetch_market_klines.py | local_data_store.py、test_local_data_store.py、test_runner_sync.ps1、sources.py、room.js |
| `klines_gap_report.json` | fetch_fubon_futures_klines.py、local_data_store.py | — |
| `momentum_data.json` | fetch_institutional_momentum.py | room.js |
| `momentum_snapshots.json` | fetch_institutional_momentum.py | — |
| `screener_cache.json` | build_screener_cache.py | local_data_store.py、test_local_data_store.py、room.js |
| `screener_ohlcv_cache.json` | build_screener_cache.py | build_stock_daily_shards.py、local_data_store.py |
| `session_snapshots.json` | fetch_and_calc_vision.py | backfill_snapshots.py |
| `social_card_latest.png` | generate_social_card.py | index.html |
| `social_card_p1_overview.png` | generate_social_card.py | app.js、index.html |
| `social_card_p2_gex_profile.png` | — | app.js、index.html、generate_social_card.py |
| `social_card_p3_sector_rotation.png` | — | app.js、index.html、generate_social_card.py |
| `stock_daily` | local_data_store.py | build_screener_cache.py、build_stock_daily_shards.py、test_local_data_store.py、room.js |
| `stock_futures_large_trader_cache.json` | fetch_and_calc_vision.py | — |
| `stock_institutional_history.json` | build_screener_cache.py | fetch_and_calc_vision.py、local_data_store.py |
| `taifex_stock_futures_contract_map.json` | fetch_and_calc_vision.py | fetch_tw_universe.py |
| `tw_holidays.json` | fetch_fubon_futures_klines.py | backfill_snapshots.py、fetch_and_calc_vision.py、fubon_api_provider.py、gex_v2.py、live_price_server.py |
| `tw_quotes_latest.json` | fetch_real_quotes.py | build_screener_cache.py、fetch_and_calc_vision.py、room.js |
| `tw_symbols_universe.json` | fetch_tw_universe.py | build_screener_cache.py、fetch_real_quotes.py、fubon_api_provider.py、room.js |
| `twse_t86_cache.json` | fetch_and_calc_vision.py | — |
| `us_macro_calendar.json` | — | fetch_and_calc_vision.py |
| `taifex_catalog.json` | — | fetch_and_calc_vision.py |
| `manifest.json` | build_brain_manifest.py | room.js |
| `chat_log.jsonl` | advisor_bridge.py | — |
| `consolidation_state.json` | — | advisor_bridge.py |
| `long_term.json` | — | advisor_bridge.py |
| `memory_changelog.jsonl` | advisor_bridge.py | — |
| `patterns.json` | — | advisor_bridge.py |
| `short_term.json` | — | advisor_bridge.py |
| `agents.json` | — | server.py、test_runner.py |
| `desk_config.json` | — | book.py |

## 3. 程式檔反查（改這個檔，誰會受影響）

「近距影響」= 2 層內（直接＋再一手，含透過資料檔傳遞）依賴它的程式檔數；更遠的關聯太弱不計。逐一展開用 `--impact`。

| 檔案 | 行數 | 用途 | 被誰用（直接） | 近距影響 | 讀 | 寫 | 環境變數／Secrets |
|---|---|---|---|---|---|---|---|
| `.github/workflows/auto_update.yml` | 108 | TAIFEX Data Engine (Day & Night Sessions) | bump_version.py | 1 | — | — | GEMINI_API_KEY |
| `app.js` | 3561 | — | index.html、bump_version.py、smoke_test_room.py | 6 | encrypted_gex.json、gex_data.json、social_card_p1_overview.png、social_card_p2_gex_profile.png、social_card_p3_sector_rotation.png | — | — |
| `cloudflare/worker.js` | 206 | TXO-GEX Cloud Relay Worker (Public Open Source Serverless Relay Versio | wrangler.toml | 1 | — | — | GEX_KV |
| `index.html` | 2063 | 尋鳥 Bluebird Finder — TXO GEX 量化系統與三大法人期權籌碼分析儀表板 | bump_version.py、live_price_server.py、server.py、room.html | 17 | embedded_data.js、social_card_latest.png、social_card_p1_overview.png、social_card_p2_gex_profile.png、social_card_p3_sector_rotation.png | — | — |
| `room.html` | 15 | 正在跳轉至尋鳥戰情交易室... | index.html、bump_version.py、smoke_test_room.py、start_live_with_advisor.bat、hub.html、meeting.html …+1 | 10 | — | — | — |
| `scripts/audit_vs_official.py` | 497 | audit_vs_official.py — 把 data/gex_data.json 裡每個區塊的數字，逐項「獨立」向期交所／證交所官方再 | — | 0 | gex_data.json | — | — |
| `scripts/backfill_institutional_snapshots.py` | 192 | backfill_institutional_snapshots.py - Seeds data/institutional_snapsho | — | 0 | — | — | — |
| `scripts/backfill_margin_balance.py` | 63 | backfill_margin_balance.py - Fills `margin_balance_billion` (融資餘額, 億 T | — | 0 | — | — | — |
| `scripts/backfill_margin_maint_estimates.py` | 99 | backfill_margin_maint_estimates.py - Rebuilds the day-by-day 融資維持率 EST | — | 0 | — | — | — |
| `scripts/backfill_snapshots.py` | 366 | — | backfill_institutional_snapshots.py、backfill_margin_balance.py、backfill_margin_maint_estimates.py | 3 | session_snapshots.json、tw_holidays.json | — | — |
| `scripts/backfill_taifex_klines.py` | 182 | backfill_taifex_klines.py - 用「期交所官方每日期貨成交資料」補回戰情室的日內 K 線歷史（真實資料，不是推算）。 | — | 5 | klines_cache.json | klines_cache.json | — |
| `scripts/build_screener_cache.py` | 709 | build_screener_cache.py | run_screener_cache_task.ps1 | 6 | stock_daily、tw_quotes_latest.json、tw_symbols_universe.json | screener_cache.json、screener_ohlcv_cache.json、stock_institutional_history.json | TXO_PRIVATE_INDICATORS |
| `scripts/build_stock_daily_shards.py` | 82 | build_stock_daily_shards.py - 把全市場個股日 K 切成 64 個小分片：data/stock_daily/00 | build_screener_cache.py | 2 | screener_ohlcv_cache.json、stock_daily | — | — |
| `scripts/bump_version.py` | 268 | TXO-GEX-Dashboard 一鍵原子版本升級工具 (Atomic Version Bumper) | — | 0 | embedded_data.js、gex_data.json | — | — |
| `scripts/compare_zero_gamma.py` | 108 | compare_zero_gamma.py — 並排比較兩種 Zero Gamma 算法（只做分析，不改資料檔、不影響網頁）。 | — | 0 | — | — | — |
| `scripts/compliance_check.py` | 102 | 社群內容合規檢查器（文字 / 圖卡 / 影片旁白共用）。 | post_social_cards.py | 1 | — | — | — |
| `scripts/do_encrypt.ps1` | 111 | Update recent_3_days_summary with real numbers | — | 0 | encrypted_gex.json、gex_data.json | — | — |
| `scripts/encrypt.ps1` | 27 | — | — | 0 | encrypted_gex.json、gex_data.json | — | — |
| `scripts/encrypt.py` | 57 | encrypt.py — Pure Encryption-Only Script | — | 4 | gex_data.json | encrypted_gex.json | — |
| `scripts/fetch_and_calc.py` | 9 | — | encrypt.py | 1 | — | — | — |
| `scripts/fetch_and_calc_vision.py` | 5057 | TAIFEX TXO Options GEX & Stock Futures Positioning Engine v36.0 (Visio | auto_update.yml、backfill_institutional_snapshots.py、backfill_margin_maint_estimates.py、backfill_snapshots.py、bump_version.py、compare_zero_gamma.py …+8 | 30 | gex_data.json、stock_institutional_history.json、tw_holidays.json、tw_quotes_latest.json、us_macro_calendar.json …+1 | embedded_data.js、encrypted_gex.json、gex_data.json、gex_line_observations.json、institutional_snapshots.json …+4 | — |
| `scripts/fetch_fubon_futures_klines.py` | 178 | fetch_fubon_futures_klines.py - LOCAL, run-by-hand: accumulate REAL fu | run_fubon_klines_task.ps1 | 12 | tw_holidays.json | klines_cache.json、klines_gap_report.json、tw_holidays.json | — |
| `scripts/fetch_institutional_momentum.py` | 231 | TAIFEX Institutional Momentum & Retail Positioning Pipeline | — | 1 | — | momentum_data.json、momentum_snapshots.json | — |
| `scripts/fetch_market_klines.py` | 358 | fetch_market_klines.py | auto_update.yml、backfill_taifex_klines.py、fetch_fubon_futures_klines.py | 10 | — | klines_cache.json | — |
| `scripts/fetch_real_quotes.py` | 281 | fetch_real_quotes.py | auto_update.yml、run_screener_cache_task.ps1 | 6 | tw_symbols_universe.json | tw_quotes_latest.json | — |
| `scripts/fetch_tw_universe.py` | 221 | Fetch and build the complete Taiwan Symbol Universe (`data/tw_symbols_ | — | 4 | taifex_stock_futures_contract_map.json | tw_symbols_universe.json | — |
| `scripts/fubon_api_connector.py` | 61 | fubon_api_connector.py | — | 0 | — | — | — |
| `scripts/fubon_api_provider.py` | 1217 | — | fetch_fubon_futures_klines.py、fubon_api_connector.py、fubon_klines_probe.py、live_price_server.py、test_futopt_watchdog.py、test_trades_snapshot.py | 11 | tw_holidays.json、tw_symbols_universe.json | — | FUBON_ACCOUNT_NO, FUBON_API_KEY, FUBON_API_MODE, FUBON_CERT_PASS, FUBON_CERT_PATH |
| `scripts/fubon_klines_probe.py` | 71 | fubon_klines_probe.py - READ-ONLY probe: what futures candles does the | — | 0 | — | — | — |
| `scripts/generate_qr_codes.py` | 107 | Bluebird Finder Social QR Code Generator | generate_social_card.py | 2 | — | — | — |
| `scripts/generate_social_card.py` | 984 | Bluebird Finder Social Infographic Generator v56.0 (1:1 Square 1080x10 | fetch_and_calc_vision.py | 17 | gex_data.json、social_card_p2_gex_profile.png、social_card_p3_sector_rotation.png | social_card_latest.png、social_card_p1_overview.png | — |
| `scripts/gex_v2.py` | 346 | gex_v2.py — 「通行版」GEX（教科書／業界常用寫法），與 fetch_and_calc_vision.py 的現行引擎(v1)並 | gex_v2_backfill.py、gex_v2_daily.py | 3 | tw_holidays.json | — | — |
| `scripts/gex_v2_backfill.py` | 237 | gex_v2_backfill.py — 回補「通行版(v2)」與「現行引擎(v1)」逐日 GEX 點位，供對照與回測。 | gex_v2_daily.py | 2 | gex_v2_history.json | — | — |
| `scripts/gex_v2_backtest.py` | 262 | gex_v2_backtest.py — 讀 data/gex_v2_history.json，量化「通行版(v2)」與「現行引擎(v1)」 | — | 0 | gex_v2_history.json | — | — |
| `scripts/gex_v2_daily.py` | 116 | gex_v2_daily.py — 每日並行累積「通行版(v2)」點位到 data/gex_v2_history.json（不碰 gex_d | auto_update.yml | 4 | gex_data.json、gex_v2_history.json | gex_v2_history.json | GEX_V2_HIST |
| `scripts/live_price_server.py` | 609 | TXO-GEX-Dashboard v50.9 — Multi-Source Live Price Gateway Server | run_live_server_task.ps1、start_live.bat、start_live_with_advisor.bat、room.js | 7 | tw_holidays.json | — | TXO_ALLOWED_HOSTS, TXO_ALLOWED_TS_LOGINS, TXO_GATEWAY_HOST, TXO_GATEWAY_PORT |
| `scripts/local_data_store.py` | 187 | Persistent local data store for the runner clone (C:\Users\mingi\txo-k | run_fubon_klines_task.ps1、run_screener_cache_task.ps1、runner_sync.ps1、test_local_data_store.py、test_runner_sync.ps1 | 9 | klines_cache.json、screener_cache.json、screener_ohlcv_cache.json、stock_institutional_history.json | klines_gap_report.json、stock_daily | TXO_BACKUP_DIR, TXO_LOCAL_STORE |
| `scripts/mis_session.py` | 100 | 期交所 MIS 備援報價的場次判斷（純函式，無網路、無副作用，方便單元測試）。 | live_price_server.py、test_mis_session.py、test_mis_ticks.py | 7 | — | — | — |
| `scripts/post_social_cards.py` | 197 | 把每日 3 張社群卡（data/social_card_p1/p2/p3）自動發到 FB 粉絲專頁 + IG 專業帳號（輪播）。 | — | 0 | gex_data.json | — | META_IG_GRAPH, META_IG_TOKEN, META_IG_USER_ID, META_PAGE_ID, META_PAGE_TOKEN |
| `scripts/run_fubon_klines_task.ps1` | 47 | run_fubon_klines_task.ps1 - scheduled wrapper: accumulate real Fubon f | — | 0 | — | — | PYTHONIOENCODING |
| `scripts/run_live_server_task.ps1` | 37 | run_live_server_task.ps1 - keeps scripts/live_price_server.py running  | — | 0 | — | — | PYTHONIOENCODING |
| `scripts/run_screener_cache_task.ps1` | 34 | run_screener_cache_task.ps1 - scheduled wrapper: refresh daily stock q | — | 0 | — | — | PYTHONIOENCODING |
| `scripts/runner_sync.ps1` | 29 | runner_sync.ps1 - dot-sourced by the runner wrappers (run_live_server_ | run_fubon_klines_task.ps1、run_live_server_task.ps1、run_screener_cache_task.ps1、test_runner_sync.ps1 | 4 | — | — | — |
| `scripts/smoke_test_room.py` | 206 | smoke_test_room.py - 尋鳥戰情室煙霧測試（每次改 trading room/ 後、或部署後跑一次）。 | — | 0 | gex_data.json | — | — |
| `scripts/test_futopt_watchdog.py` | 201 | 1) _timed_lock | — | 0 | — | — | — |
| `scripts/test_gex_empty_chain_guard.py` | 32 | 選擇權鏈為空（期交所抓取失敗）時，不可發布全 0 剖面；應沿用上一份正常 GEX 欄位並標記 stale。 | — | 0 | gex_data.json | — | — |
| `scripts/test_gex_night_anchor.py` | 32 | Night anchoring: walls follow the anchor price; wall_extra widens only | — | 0 | — | — | — |
| `scripts/test_gex_walls.py` | 58 | Self-test for the Call Wall / Put Wall definition in fetch_and_calc_vi | — | 0 | — | — | — |
| `scripts/test_local_data_store.py` | 118 | Self-test for local_data_store.py using temp dirs only (never touches  | — | 0 | klines_cache.json、screener_cache.json、stock_daily | — | — |
| `scripts/test_mis_session.py` | 36 | 2026-10-12 是週一；10/16 週五；10/17 週六；10/18 週日 | — | 0 | — | — | — |
| `scripts/test_mis_ticks.py` | 38 | 日盤：標籤＝結束時間，K 棒開始＝標籤−1 分 | — | 0 | — | — | — |
| `scripts/test_runner_sync.ps1` | 68 | --- "cloud" repo | — | 0 | klines_cache.json | — | TEMP, TXO_LOCAL_STORE |
| `scripts/test_settled_exclusion.py` | 17 | 結算日 13:30 後，已結算合約必須被剔除（牆位／Gamma Flip／到期組成／Max Pain 共用同一份 bucket）。 | — | 0 | — | — | — |
| `scripts/test_trades_snapshot.py` | 33 | get_recent_trades must survive concurrent appends (deque mutated durin | — | 0 | — | — | — |
| `scripts/update_and_encrypt.ps1` | 110 | — | — | 0 | encrypted_gex.json、gex_data.json | — | — |
| `start_live.bat` | 12 | — | — | 0 | — | — | — |
| `start_live_with_advisor.bat` | 22 | — | — | 0 | — | — | — |
| `tools/option_quote_recorder.py` | 88 | TAIFEX MIS option-chain quote recorder (stage-0 experiment, simulation | run_service.ps1 | 2 | — | — | — |
| `trading room/advisor_bridge.py` | 1047 | 幕僚鳥橋接程式：戰情室 → 本機 Claude Code（claude -p）→ 用你的 Claude 訂閱回答，不走 API 計費。 | start_live_with_advisor.bat、run_service.ps1、room.js、start_advisor.bat、test_advisor_guard.py | 9 | chat_log.jsonl、consolidation_state.json、long_term.json、patterns.json、short_term.json | chat_log.jsonl、memory_changelog.jsonl | ADVISOR_BRIDGE_PORT, ADVISOR_GUARD, ADVISOR_MEM_DIR |
| `trading room/advisor_guard.py` | 130 | 幕僚鳥防套話機制（純函式，無網路、無檔案副作用，方便單元測試）。 | advisor_bridge.py、test_advisor_guard.py | 6 | — | — | — |
| `trading room/build_brain_manifest.py` | 20 | 掃描 trading room/brain/ 下所有 .md，依標題切段，輸出 manifest.json（幕僚鳥檢索用）。 | — | 1 | — | manifest.json | — |
| `trading room/desk/autostart/register_tasks.ps1` | 23 | register_tasks.ps1 - registers 5 "at log on" tasks (TXO-Desk-*) for th | — | 0 | — | — | LOCALAPPDATA, USERNAME, USERPROFILE |
| `trading room/desk/autostart/run_service.ps1` | 31 | run_service.ps1 - keeps one TXO-desk background service alive (restart | register_tasks.ps1 | 1 | — | — | ADVISOR_MEM_DIR, LOCALAPPDATA, PYTHONIOENCODING, USERPROFILE |
| `trading room/desk/book.py` | 254 | 虛擬下單簿。只有這個類別會寫帳本；AI 只能遞交決策單(submit)，不能碰數字。 | daily_close.py、meeting.py、monitor.py、patrol.py、replay.py、review.py …+5 | 18 | desk_config.json | — | — |
| `trading room/desk/daily_close.py` | 45 | 每日計價與到期結算（程式寫帳本，AI 不碰）。 | — | 0 | — | — | — |
| `trading room/desk/decision.py` | 121 | 決策單格式（規格第6節、6.1）。AI 只輸出 JSON 決策單，不接受純文字下單；這裡只驗格式，不判斷風控。 | book.py、risk.py | 13 | — | — | — |
| `trading room/desk/expiry.py` | 53 | 到期代碼解析（照 AGENTS.md 的對照表）。202610W4=週三選第4個、202610F2=週五選第2個、202610=月選(第3個 | book.py、decision.py、quotes.py、risk.py、runner.py、sources.py …+1 | 18 | — | — | — |
| `trading room/desk/indicators.py` | 129 | 指標轉接層（公開檔，不含任何指標公式）：把 1 分 K 聚成 15M/30M、接上富邦累積的歷史，再呼叫「私有指標模組」。 | run_slot.py、test_indicators.py | 9 | — | — | TXO_DESK_INDICATORS |
| `trading room/desk/ledger.py` | 52 | 只增不改的帳本。只有程式能寫（沒有任何修改/刪除介面）；每筆帶雜湊鏈，事後被改動可被 verify() 抓到。 | book.py、test_desk.py | 12 | — | — | — |
| `trading room/desk/meeting.py` | 97 | 會議室（最小版）：收盤後覆盤寫完，台選鳥、風控鳥、文書鳥開一場短會，把「下個時段的計畫」過一遍，留下逐段發言與會議紀錄。 | patrol.py、test_runner.py | 3 | — | — | — |
| `trading room/desk/monitor.py` | 75 | 規則巡邏（規格附錄 C.2「程式規則巡邏」）：交易時段內每隔一段時間用最新 MIS 報價鏈檢查 | run_service.ps1、start_desk.bat、test_runner.py | 4 | — | — | — |
| `trading room/desk/patrol.py` | 164 | 盤中 AI 巡邏（規格附錄 C.2「AI 巡邏」）：日盤與夜盤交易時段內，台選鳥依行情自由決定要不要下單。 | run_service.ps1、test_runner.py | 3 | — | — | — |
| `trading room/desk/quotes.py` | 123 | 選擇權報價鏈與「可成交」判斷。保守算法：賣用買價、買用賣價。無效報價一律回 None，不補假數字。 | runner.py、snapshot.py、test_desk.py | 13 | — | — | — |
| `trading room/desk/replay.py` | 46 | 重放模式（階段 0/2 驗證用，不當成績）：拿已記錄的報價鏈檔，照時間一份份走一遍「快照→檢查→決策→下單簿」， | test_runner.py | 1 | — | — | — |
| `trading room/desk/review.py` | 131 | 盤後覆盤與盤前規劃（規格第9節）：每個交易時段結束後，台選鳥用白話寫一份筆記—— | meeting.py、patrol.py、test_runner.py | 4 | — | — | — |
| `trading room/desk/risk.py` | 159 | 紅線與風控檢查器（規格第8節）。全部由程式強制，AI 無法繞過。回傳違規字串列表；空列表＝通過。 | book.py、test_desk.py | 12 | — | — | — |
| `trading room/desk/run_slot.py` | 62 | 決策時段腳本：抓即時資料 → 快照 → 台選鳥決策 → 下單簿。全部是模擬單。 | daily_close.py、meeting.py、monitor.py、patrol.py、review.py、server.py …+1 | 15 | — | — | — |
| `trading room/desk/runner.py` | 208 | 決策執行器：快照 → 台選鳥(AI) → 決策單 JSON → 下單簿（驗證＋紅線）。全部是模擬單，不連券商。 | meeting.py、patrol.py、replay.py、review.py、run_slot.py、test_runner.py | 11 | — | — | — |
| `trading room/desk/server.py` | 249 | 台選鳥帳戶頁的本機資料服務（唯讀）：從你的私有帳本算出持倉/損益/風控距離，給網頁顯示。 | live_price_server.py、advisor_bridge.py、run_service.ps1、start_desk.bat、test_runner.py、hub.html …+2 | 15 | agents.json | — | — |
| `trading room/desk/settlement.py` | 85 | 到期結算（只用期交所官方「最後結算價」，不自己猜）。 | monitor.py、test_runner.py | 4 | — | — | — |
| `trading room/desk/snapshot.py` | 169 | 決策快照（規格第5節）：每次決策把餵給 AI 的全部輸入凍結存檔，之後覆盤與「考試」才公平。 | daily_close.py、meeting.py、monitor.py、patrol.py、replay.py、review.py …+5 | 19 | — | — | — |
| `trading room/desk/sources.py` | 218 | 資料來源轉接（只讀）：把真實檔案/服務的資料整理成快照需要的格式；讀不到就回 None，不補假值。 | daily_close.py、meeting.py、monitor.py、patrol.py、replay.py、review.py …+4 | 17 | gex_data.json、klines_cache.json | — | — |
| `trading room/desk/start_desk.bat` | 10 | — | — | 0 | — | — | — |
| `trading room/desk/state.py` | 168 | 由帳本重播出帳戶狀態（單一事實來源）。數字只從事件算出來，沒有任何地方可以手改。 | book.py、risk.py、test_desk.py | 13 | — | — | — |
| `trading room/desk/tests/test_desk.py` | 429 | 假決策單單元測試。全部數字手算：1 點 = 50 元；手續費每口每邊 13；期交稅=每口權利金x0.1% 逐口四捨五入。 | — | 0 | — | — | — |
| `trading room/desk/tests/test_indicators.py` | 126 | 指標轉接層測試（聚合、已收完判斷、接歷史、竭盡方向）。K 線全是測試用假資料；不含任何指標公式。 | — | 0 | — | — | — |
| `trading room/desk/tests/test_runner.py` | 610 | 快照／缺資料檢查／決策執行器測試。注意：這裡的 GEX、K 線、報價全是【測試用假資料】，只用來驗證程式邏輯，不是行情。 | — | 0 | agents.json | — | — |
| `trading room/desk/web/hub.html` | 105 | 交易室首頁 | server.py | 8 | — | — | — |
| `trading room/desk/web/meeting.html` | 61 | 會議室｜交易室 | server.py | 8 | — | — | — |
| `trading room/desk/web/trader.html` | 187 | 交易員帳戶頁 | server.py | 8 | — | — | — |
| `trading room/room.html` | 1043 | 🦅 尋鳥戰情交易室 — TXO GEX 即時戰情室 (Bird Trading Room v64.18) | index.html、room.html、bump_version.py、smoke_test_room.py、start_live_with_advisor.bat、hub.html …+2 | 10 | embedded_data.js | — | — |
| `trading room/room.js` | 5197 | — | bump_version.py、smoke_test_room.py、room.html | 9 | gex_data.json、klines_cache.json、momentum_data.json、screener_cache.json、stock_daily …+3 | — | — |
| `trading room/room_retail.js` | 93 | — | room.html | 9 | institutional_snapshots.json | — | — |
| `trading room/start_advisor.bat` | 7 | — | — | 0 | — | — | — |
| `trading room/test_advisor_guard.py` | 123 | 幕僚鳥防套話測試：python "trading room/test_advisor_guard.py"（不需要網路、不需要 Claude） | — | 0 | — | — | ADVISOR_MEM_DIR |
| `wrangler.toml` | 17 | Put sensitive values in Cloudflare Worker secrets instead of source co | — | 0 | — | — | — |

## 4. 沒有被任何地方引用的檔案（手動執行、測試或可能已廢棄）

程式：gex_tv_bookmark.html、cloudflare_worker.js、get_real_history.ps1、probe_publish_times.py、test_api.ps1、test_mis.ps1、test_otc.ps1、test_otc2.ps1、test_otc3.ps1、test_otc4.ps1、test_otc5.ps1、test_taifex_csv.ps1、test_taifex_history.ps1、test_taifex_opt.py、test_twse_history.py、test_yahoo.ps1、tv_dom_reader.js、option_quote_health.py、probe_opt.py

資料：js_270_catalog.json、social_card_p1_overview.jpg、social_card_p2_gex_profile.jpg、social_card_p3_sector_rotation.jpg、full_270_futures.json

## 5. 前端一致性：app.js 用到但 index.html 找不到的 DOM id

app.js 引用 134 個 id；靜態對照找不到：`cache-notice-banner`、`close-guide-btn`、`close-taxonomy-btn`、`guide-modal`、`macro-primary-regime`、`macro-primary-timer`、`open-guide-btn`、`overlay-legend`、`stock-spot-date-note`。（動態產生的元素會誤報，需人工確認。）

