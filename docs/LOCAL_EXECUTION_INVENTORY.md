# 本機執行依賴盤點（Local Execution Inventory）

> 這份文件回答一個問題：**這個專案哪些部分「必須」在使用者的 Windows 電腦上跑，哪些其實可以搬去雲端或別台機器（例如 Mac mini M2）？**
> 起因：2026-09-30 討論「選股雷達的動能鳥指標邏輯要不要搬離公開 repo」時，使用者問「本機執行會不會累積很多檔案、未來要不要租雲端主機、要不要搬去 Mac mini M2 常駐」。查證後發現關鍵限制是**富邦 Neo SDK 是 Windows 專屬的編譯二進位**，這決定了哪些功能被鎖死在 Windows 上。
> 更新方式：以後任何新增「本機排程」或「雲端排程」的功能，都應該回來補這份表，不要只寫進 HISTORY.md 就結束——那裡是變更記錄，這裡是「現況地圖」。

## 一、關鍵事實：為什麼有些東西「一定」要留在 Windows

已安裝的富邦 Neo SDK（`pip` 裝不到，是券商網站下載的私有套件）核心檔案是：

```
site-packages/fubon_neo/_fubon_neo.pyd
```

`.pyd` 是 **Windows 專屬的編譯二進位模組**（Python C 擴充，等同 Linux 的 `.so`、Mac 的 `.dylib`，但三者互不通用）。這代表：

- **只要一個功能需要即時呼叫富邦 API（報價、五檔、逐筆成交），這個功能就被鎖在 Windows 上**，除非富邦官方另外提供 Mac／Linux 版的 SDK（未查證，需要直接問富邦或查其開發者文件）。
- 換到 Mac mini M2（ARM64）或雲端 Linux 主機，都不能直接把這幾支腳本原封不動搬過去執行。

## 二、現況總表

| 組件 | 執行方式 | 排程 | 需要富邦 SDK？ | 能不能脫離 Windows？ |
|---|---|---|:---:|---|
| `scripts/fetch_and_calc_vision.py`（GEX 主引擎） | ☁️ 雲端（GitHub Actions, Ubuntu） | `.github/workflows/auto_update.yml`，一天 9 個時間點（日夜盤收盤＋融資維持率窗口） | 否 | 已經在雲端跑，不受影響 |
| `scripts/fetch_market_klines.py`（現貨/指數/CL/DXY/US10Y K 線 + 期貨日K來源） | ☁️ 雲端（同上 workflow） | 同上 | 否（期貨部分改抓 TAIFEX 官方 `futDataDown`，也不需要富邦） | 已經在雲端跑 |
| `scripts/live_price_server.py`（即時報價閘道：TXF/TAIEX/OTC 報價、五檔、逐筆成交、CVD、總經 DXY/US10Y/CL/VIX/VVIX） | 💻 本機常駐 | Windows 工作排程 `TXO-Live-Price-Server`，登入時啟動，掛掉自動重啟 | **是（核心功能）** | **不能**——即時報價/CVD 是這支的存在理由，全部要富邦 WebSocket |
| `scripts/fetch_fubon_futures_klines.py`（富邦期貨日內 K 線累積：TXF/MXF/MTX/CDF） | 💻 本機、排程 | Windows 工作排程 `TXO-Fubon-Futures-Klines`，每天 05:30／14:00 | **是** | **不能**——富邦只給「最近一個場次」的日內 K，沒有歷史端點，只能常駐累積 |
| `scripts/run_screener_cache_task.ps1`（個股日報價 `fetch_real_quotes.py` → 選股快取＋個股日K分片 `build_screener_cache.py`） | 💻 本機、排程（**建議**，2026-10-07 新增腳本，尚未註冊） | Windows 工作排程 `TXO-Screener-Cache`，平日 16:30（註冊指令見腳本檔頭說明／HANDOFF） | 否（只用證交所／櫃買官方資料） | **不能**——`build_screener_cache.py` 會 import 私有指標資料夾 `txo-private\screener-indicators`（不在公開 repo），GitHub Actions 跑不了；報價檔那一步另在雲端 `auto_update.yml` 也有跑 |
| `scripts/build_screener_cache.py`（選股雷達，1,400+ 檔全市場） | 💻 本機、**手動**執行 | **目前沒有排程**——一直是我在對話 session 裡手動跑完手動 commit（2026-09-30 查證確認，之前誤以為它在雲端排程裡，是我的錯誤假設） | 否（純 TWSE/TPEx 官方 HTTP 端點） | **可以**——沒有任何富邦依賴，理論上今天就能搬去雲端排程或 Mac mini，只是還沒設 |
| `scripts/jj_ghost_claws.py`（動能鳥 8 訊號；2026-09-30 已搬私有資料夾，`build_screener_cache.py` 改由該處載入） | 跟著上面一起跑 | 同上 | 否 | 同上，可以搬 |
| 私有 Cloudflare Worker（`bluebird-indicators`：ADX／雙層MACD／CCI／AO／動能鳥 HUD／SMC） | ☁️ Cloudflare（獨立於 GitHub Actions） | 常駐服務，使用者手動部署 | 否 | 已經在雲端，不受影響 |

## 三、資料量與 git 歷史（2026-09-30 實測）

| 項目 | 大小 | 備註 |
|---|---|---|
| `data/klines_cache.json` | 5.5M | 有上限：`fetch_fubon_futures_klines.py` 每個時間級別最多留 8000 根 K 棒，不會無限長大 |
| `data/screener_cache.json` | 1.3M | |
| `data/screener_ohlcv_cache.json` | 12M | 1,400+ 檔 × 120 天 K 線 |
| `data/gex_data.json` | 920K | |
| `data/` 資料夾總計 | 39M | |
| **`.git` 歷史總計** | **645M** | ⚠️ **持續肥大中，沒有上限**——每天多次把資料檔案完整 commit 進 git，舊版本從未清除。clone/fetch 速度會越來越慢。這是獨立於「本機/雲端」的另一個問題，這裡先記錄，**尚未處理**，處理方式（git-lfs／搬到外部儲存／定期整理歷史）需要使用者決定，且使用者已表態不想改寫公開歷史，所以「定期 squash 舊 commit」這條路目前不能用。 |

## 四、如果未來要上 Mac mini M2 常駐，或租雲端主機

**能直接搬的（無富邦依賴，純 Python + HTTP）：**
- `scripts/build_screener_cache.py` + `scripts/jj_ghost_claws.py`（選股雷達）——今天就能設成本機或任何機器的排程
- 理論上也能反過來搬「上」雲端排程（GitHub Actions），因為它不需要富邦帳號登入

**不能搬、鎖在 Windows（或需要先跟富邦確認有沒有其他平台 SDK）的：**
- `scripts/live_price_server.py`（即時報價／CVD）
- `scripts/fetch_fubon_futures_klines.py`（富邦期貨日內 K）

**如果真的要讓這兩塊脫離「使用者自己的 Windows 電腦開機」限制，選項是：**
1. 問富邦有沒有 Mac／Linux 版 SDK（未查證，最先該做的）。
2. 租一台 **Windows** 雲端主機／VM（例如 Azure/AWS 的 Windows Server），24/7 開機跑這兩支腳本——但這是額外月費，且仍然是「這兩塊功能」而非整個專案需要。
3. 換一個有跨平台 SDK 或純 REST API 的即時行情來源，放棄目前的富邦 WebSocket 逐筆成交（會失去 CVD 的資料來源，需要重新設計）。
4. 維持現狀：這兩塊留在使用者的 Windows 電腦，其餘（主引擎、K線、選股雷達、Worker）已經或可以搬去雲端/其他機器。

本文件不做決定，只記錄現況與限制；要不要動、動哪一塊，由使用者決定。
