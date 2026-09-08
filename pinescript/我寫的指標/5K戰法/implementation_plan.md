# 5K戰法 V2 (智能商品辨識版) 開發計畫

## 核心目標
建立一個能根據當前圖表商品 (Ticker)，自動切換最佳化參數的機制，讓使用者無需在切換商品時手動調整 `ATR 乘數`、`風報比` 與 `回溯區間`。將另存為 `5K_Strategy_Master_v2.pine`。

## User Review Required

> [!IMPORTANT]
> 關於「富時台灣指數 (FTSE Taiwan)」的設定：
> 雖然它的走勢與台指期 (TX) 高度連動，但在新加坡交易所 (SGX) 交易時，由於包含外資避險部位，短線洗盤的下影線可能會比台指期稍長。我目前將它與台指期設為同一等級（ATR乘數 1.5），但如果您覺得假突破太多，未來我們可以將它微調至 1.6 左右。

> [!TIP]
> 為了讓使用者保留控制權，我會設計一個「**智能切換開關 (Auto-Detect)**」，預設為開啟。如果您想自己微調，只要關閉開關，指標就會改吃您設定面板裡的手動數字。

## Proposed Changes

### [NEW] 5K_Strategy_Master_v2.pine

1. **新增智能參數引擎 (Auto-Parameter Engine)**
   - 抓取 `syminfo.root` 進行字串比對，涵蓋原型、小型 (E-mini)、微型 (Micro)。
   - **台股/台指家族**：TX, MTX, TWN (富時台灣)
   - **美股指數**：ES, MES, NQ, MNQ, YM, MYM, RTY, M2K
   - **國際指數**：NKD, MNI, FDAX, FDXM, HSI, HHI, MHI
   - **金屬/原物料**：GC, MGC, SI, SIL, HG, QC, CL, MCL, QM, NG, QG
   - **農產品**：ZS, ZC, ZW, ZL, CT
   - **外匯/匯率**：6E, M6E, 6B, M6B, 6A, 6C, 6J, DX

2. **參數覆寫邏輯**
   - 建立變數 `final_atr_mult`, `final_rr_ratio`, `final_lookback`。
   - 若 `use_auto` 開啟，則使用辨識結果；若無辨識結果或開關關閉，則退回使用原本 `input()` 裡的設定。

3. **資訊面板 (Dashboard) 升級**
   - 新增一行顯示**「商品辨識結果 (Detected Asset)」**（例如：`Nasdaq (High Vol)`）。
   - 新增一行顯示**「參數模式 (Mode)」**（`Auto` 或 `Manual`），確保切換過程透明清晰。

## Verification Plan
1. **編譯驗證**：確保大量字串比對與 `switch` 語句不會導致編譯超時或報錯。
2. **邏輯檢查**：確認 `final_` 變數有確實替代原本的 `atr_mult` 等計算邏輯。
