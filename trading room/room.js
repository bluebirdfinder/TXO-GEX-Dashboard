/**
 * 🦅 尋鳥戰情交易室 (Bird Trading Room) Core Engine v64.17
 * True Multi-Pane Trading Terminal with 10 Timeframes & 4 Sub-Panes
 *   - Main Chart (44%): TXF K-Line + GEX 5 Levels + 尋鳥多空彩帶 + 8大進出場訊號 + DeMark 9★/13★ + VWAP + SMMA 200 + SAR + Supertrend
 *   - Sub-Chart 1 (14%): 成交量 Volume + 5MA & 10MA 雙均量線
 *   - Sub-Chart 2 (14%): 戰情雙層 MACD (4 色量柱 + 快慢線)
 *   - Sub-Chart 3 (14%): 波段拐點 CCI (20 通道 & 買賣轉折點)
 *   - Sub-Chart 4 (14%): 動能副圖 (AO / CVD / DMI 一鍵切換)
 *   - All 5 charts 100% synchronized with 0ms crosshair & time-scale tracking
 */

// Global State
let gexData = null;
let klinesCacheData = null;
let momentumData = null;

// Last-resort fallback numbers for when gexData is missing a GEX level field outright.
// Found 2026-09-15: 5 different functions each independently typed in their own disagreeing
// literal for the same logical field (call_wall_strike alone had 47400/46400/47300 across
// different functions) — the same "34 inconsistent app.js defaults" pattern audited and
// unified there the night before, just not yet done for room.js. All of these call sites are
// actually dead code in practice (the backend always computes these fields), so this exists
// only to stop disagreeing numbers from being copy-pasted again — seeded from the same real
// 2026-09-15 pipeline run as app.js's CHART_DEFAULTS.
const ROOM_CHART_DEFAULTS = {
  txf_price: 46588.0,
  zero_gamma_level: 45040.4,
  call_wall_strike: 45700.0,
  put_wall_strike: 46000.0,
  max_pain_strike: 45050.0
};

// Multi-Chart Instances
let mainChart = null;
let subChart1 = null;
let subChart2 = null;
let subChart3 = null;
let subChart4 = null;

// Series References
let candleSeries = null;
let volumeSeries = null;
let volMa5Series = null;
let volMa10Series = null;

let macdHistSeries = null;
let macdDifSeries = null;
let macdDeaSeries = null;

let cciLineSeries = null;
let cciMarkers = [];

let activeSub4 = 'adx'; // Default to ADX Pro V3
let momentumPollTimer = null; // 大戶散戶動能：輪詢 /api/momentum 的計時器
let cvdPollTimer = null; // CVD：輪詢 /api/cvd 的計時器
let leftPanelCollapsed = false;
let rightPanelCollapsed = false;
let advisorAttachedImage = null;

// GEX Strict Asset Scope (僅在台指期、小台、微台顯示 GEX 5 大防線)
// 報價服務位置：網頁若本身就是由報價服務提供（電腦上的 localhost，或 Tailscale／私人網址），就向「同一個位址」要報價；
// 只有公開的 GitHub 網頁才用 http://localhost:8000（手機上的 localhost 是手機自己，不是你的電腦）。
const GATEWAY_BASE = (location.hostname === 'bluebirdfinder.github.io') ? 'http://localhost:8000' : '';
const GEX_SUPPORTED_SYMBOLS = ['TXF', 'MXF', 'MTX', 'TMF'];
// CVD／大戶散戶動能可看的期貨代號：四個指數期貨＋universe 內所有個股／ETF 期貨（選股票時對應到它自己的期貨合約）。
const INDEX_FLOW_FUTURES = ['TXF', 'MXF', 'MTX', 'TMF'];
function flowFuturesCodeFor(symObj) {
  const sym = String(symObj?.symbol || activeContract || '').toUpperCase();
  if (INDEX_FLOW_FUTURES.includes(sym)) return sym;
  const stockFut = new Set((symbolsUniverse || []).filter(x => x.asset_type === 'stock_futures').map(x => String(x.symbol).toUpperCase()));
  if (stockFut.has(sym)) return sym;
  const fc = String(symObj?.futures_code || '').toUpperCase();
  return stockFut.has(fc) ? fc : null;   // 大盤現貨、櫃買、沒有期貨的個股等回傳 null
}

// CVD 即時K棒重新分組支援的時間週期（秒數）。1D/1W/1Mth 不支援：CVD只能從連線當下累積，
// 一個交易日以上的週期在單一session內沒有意義，故意不做、而不是硬湊一根假K棒。
const CVD_TF_SECONDS = { '1M': 60, '3M': 180, '5M': 300, '15M': 900, '30M': 1800, '1H': 3600, '4H': 14400 };

/**
 * 把後端 /api/cvd 回傳的真實逐筆 {ts, value} 快照，依 barSeconds 即時重新分組成K棒。
 * 邏輯跟一般tick→OHLC聚合一樣，只是「價格」換成累積量差；每根K棒的開盤值承接自上一根
 * 的收盤值（session開始時基準為0），沒有成交的時段直接不產生K棒，不補假平線。
 */
function buildCvdCandlesFromPoints(points, barSeconds) {
  if (!barSeconds || !points || points.length === 0) return [];
  const candles = [];
  let prevClose = 0; // session開始的累積量差基準值
  let cur = null;
  for (const p of points) {
    const bucketStart = Math.floor(p.ts / barSeconds) * barSeconds;
    if (!cur || cur.time !== bucketStart) {
      if (cur) { candles.push(cur); prevClose = cur.close; }
      cur = { time: bucketStart, open: prevClose, high: Math.max(prevClose, p.value), low: Math.min(prevClose, p.value), close: p.value };
    } else {
      cur.high = Math.max(cur.high, p.value);
      cur.low = Math.min(cur.low, p.value);
      cur.close = p.value;
    }
  }
  if (cur) candles.push(cur);
  return candles;
}

let sub4Series = {
  adx: null,
  adxLine: null,
  ao: null,
  cvd: null,
  dmiPlus: null,
  dmiMinus: null,
  dmiAdx: null,
  momentumHist: null,
  momentumLine: null,
  retailLine: null,
  marketOrderLine: null
};

// Overlay Series References on Main Chart
let overlaySeries = {
  ribbons: { ma7: null, ma17: null, ma88: null, ma200: null },
  smma: null,
  supertrend: { up: null, down: null },
  vwap: { vwap: null, upper1: null, lower1: null },
  sar: null
};

let priceLines = {};
let gexMarkers = [];
let currentTf = '15M';
let activeContract = 'TXF';
let symbolsUniverse = [];

// 8 Core Curated Preset Assets for Instant 1-Click Verification
// base_price is intentionally null: prices come from realPriceFor() (live gexData / real quotes / real klines).
// The old hard-coded numbers (e.g. TXF 46588, DXY 98.845) went stale and were shown as if current.
const CORE_PRESET_ASSETS = {
  'TXF': { symbol: 'TXF', name: '台指期貨', category: '指數期貨', market: 'TAIFEX', has_futures: true, futures_code: 'TXF', base_price: null, is_yield: false },
  'TAIEX': { symbol: 'TAIEX', name: '加權指數', category: '大盤現貨', market: 'TWSE', has_futures: true, futures_code: 'TXF', base_price: null, is_yield: false },
  'OTC': { symbol: 'OTC', name: '櫃買指數', category: '中小型股', market: 'TPEx', has_futures: true, futures_code: 'GDF', base_price: null, is_yield: false },
  'CDF': { symbol: 'CDF', name: '台積電期貨', category: '個股期貨', market: 'TAIFEX', has_futures: true, futures_code: 'CDF', base_price: null, is_yield: false },
  'MTX': { symbol: 'MTX', name: '微台期貨', category: '指數期貨', market: 'TAIFEX', has_futures: true, futures_code: 'TMF', base_price: null, is_yield: false },
  'MXF': { symbol: 'MXF', name: '小台期貨', category: '指數期貨', market: 'TAIFEX', has_futures: true, futures_code: 'MXF', base_price: null, is_yield: false },
  'US10Y': { symbol: 'US10Y', name: '美國10年公債殖利率', category: '總經公債', market: 'GLOBAL', has_futures: false, futures_code: 'ZN', base_price: null, is_yield: true },
  'DXY': { symbol: 'DXY', name: '美元指數 (DXY)', category: '總經外匯', market: 'ICE', has_futures: false, futures_code: 'DX', base_price: null, is_yield: false },
  'CL': { symbol: 'CL', name: '紐約輕原油期貨', category: '大宗商品', market: 'NYMEX', has_futures: true, futures_code: 'CL', base_price: null, is_yield: false },
  'GC': { symbol: 'GC', name: 'COMEX 黃金期貨', category: '大宗商品', market: 'COMEX', has_futures: true, futures_code: 'GC', base_price: null, is_yield: false }
};

/**
 * Latest REAL price for a symbol, or null. Sources, in order: live gexData (index futures / TAIEX / OTC),
 * real daily quotes, the last real candle in klines_cache.json. Never a hard-coded or synthesized number.
 */
// 最近一次即時報價（來自本機富邦服務／Worker）；超過 15 秒沒更新就視為過期，不再當「目前價格」使用。
let liveTxf = null;   // { price, at }
// 海外商品（Yahoo，經本機價格服務每 30 秒更新）：富邦 API 沒有這些，標籤與價格來源都要照實顯示
let liveMacro = null; // { dxy, us10y, cl, gc, ..., at }
const YAHOO_SOURCE_SYMBOLS = new Set(['CL', 'GC', 'DXY', 'US10Y']);
const MACRO_KEY_BY_SYMBOL = { CL: 'cl', GC: 'gc', DXY: 'dxy', US10Y: 'us10y' };
function liveMacroPrice(sym) {
  const k = MACRO_KEY_BY_SYMBOL[sym];
  const v = (liveMacro && k && (Date.now() - liveMacro.at) < 120000) ? liveMacro[k] : null;
  return (typeof v === 'number' && isFinite(v) && v > 0) ? v : null;
}
function liveTxfPrice() {
  return (liveTxf && (Date.now() - liveTxf.at) < 15000) ? liveTxf.price : null;
}

function realPriceFor(sym) {
  if (!sym) return null;
  const num = (v) => (typeof v === 'number' && isFinite(v) && v > 0) ? v : null;
  // 台指期系列：優先用新鮮的即時報價，否則才用雲端資料檔（可能是數小時前的結算價，畫面會另外標示「非即時」）
  if (sym === 'TXF' || sym === 'MTX' || sym === 'MXF' || sym === 'TMF') return liveTxfPrice() ?? num(gexData?.night_txf_price) ?? num(gexData?.txf_price);
  if (sym === 'TAIEX') return num(gexData?.spot_price);
  if (sym === 'OTC') return num(gexData?.two_price);
  const lm = liveMacroPrice(sym);
  if (lm !== null) return lm;
  const q = num(realQuotesData?.[sym]?.close);
  if (q !== null) return q;
  const tfs = klinesCacheData?.assets?.[sym]?.timeframes;
  const c = tfs && (tfs['1D'] || tfs['15M'] || tfs['1M']);
  return (c && c.length) ? num(c[c.length - 1].close) : null;
}

let currentActiveSymbol = CORE_PRESET_ASSETS['TXF'];

// User Configurable Indicator Settings
let indicatorConfig = {
  gex: true,
  ribbons: true,
  demark: true,
  smma: true,
  smmaLen: 200,
  smmaColor: '#e84393',
  supertrend: false,
  stLen: 10,
  stMult: 3.0,
  vwap: false,
  vwapColor: '#FF8A80',
  // 彩帶四條均線顏色：預設照 TradingView 原指標配色（快線白、持股線黃、多空線 E91E63、年線 9C27B0）
  ma7Color: '#ffffff',
  ma17Color: '#ffeb3b',
  ma88Color: '#e91e63',
  ma200Color: '#9c27b0',
  vrvp: true,
  vrvpRows: 50,
  vrvpVa: 70,
  sar: false,
  sarStep: 0.02,
  fvg: false
};

// 顏色偏好只存在使用者自己的瀏覽器（localStorage），不需登入；換裝置要重選。沒存過就用 TradingView 預設色。
const IND_COLOR_KEYS = ['ma7Color', 'ma17Color', 'ma88Color', 'ma200Color', 'smmaColor', 'vwapColor'];
const IND_COLOR_DEFAULTS = {};
IND_COLOR_KEYS.forEach(k => { IND_COLOR_DEFAULTS[k] = indicatorConfig[k]; });
function loadIndicatorColors() {
  try {
    const saved = JSON.parse(localStorage.getItem('txo_ind_colors') || '{}');
    IND_COLOR_KEYS.forEach(k => { if (typeof saved[k] === 'string' && /^#[0-9a-fA-F]{6}$/.test(saved[k])) indicatorConfig[k] = saved[k]; });
  } catch (e) { /* storage blocked or corrupted: keep defaults */ }
}
function saveIndicatorColors() {
  try {
    const out = {};
    IND_COLOR_KEYS.forEach(k => { out[k] = indicatorConfig[k]; });
    localStorage.setItem('txo_ind_colors', JSON.stringify(out));
  } catch (e) { /* ignore */ }
}
const IND_COLOR_INPUTS = { ma7Color: 'col-ma7', ma17Color: 'col-ma17', ma88Color: 'col-ma88', ma200Color: 'col-ma200', smmaColor: 'col-smma', vwapColor: 'col-vwap' };
function syncColorPickers() {
  Object.keys(IND_COLOR_INPUTS).forEach(k => { const el = document.getElementById(IND_COLOR_INPUTS[k]); if (el) el.value = indicatorConfig[k]; });
}
loadIndicatorColors();

// DOM Initialization
document.addEventListener('DOMContentLoaded', async () => {
  syncColorPickers();
  initGlobalSmartTooltips();
  await initTradingRoom();
  initFubonLivePriceStream();
  initOverseasLiveTickStream();
  initSymbolSearchAndAutocomplete();
  initQuantScreenerModal();
});

async function initTradingRoom() {
  console.log('🦅 Initializing Multi-Pane Bird Trading Room v64.17...');
  
  // 1. Load Data
  await loadDashboardData();
  
  // 2. Initialize Multi-Pane Charts Stack (5 Synchronized Charts)
  initMultiPaneCharts();
  
  // 3. Render Left Panel Quotes, GEX Levels & Momentum HUD
  renderLeftPanel();
  
  // 4. Setup Event Listeners & Modals
  setupEventListeners();
  
  // 5. Initialize AI Advisor Initial Brief
  initAdvisorFeed();
}

/**
 * 1. Data Loading Engine
 */
async function loadDashboardData() {
  // Load GEX & Market Data
  try {
    const res = await fetch('../data/gex_data.json?t=' + Date.now());
    if (res.ok) {
      gexData = await res.json();
    }
  } catch (e) {
    console.warn('⚠️ Fetching ../data/gex_data.json failed, using embedded fallback...', e);
  }
  
  if (!gexData && window.GEX_EMBEDDED_DATA) {
    gexData = window.GEX_EMBEDDED_DATA;
  }
  
  if (!gexData) {
    try {
      const b = document.createElement('div');
      b.textContent = '🔴 GEX 資料載入失敗：畫面上的 GEX 價位（Call Wall／Zero Gamma 等）是過期預設值，請勿當作實盤依據';
      b.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;background:#b71c1c;color:#fff;font-size:12px;padding:4px 8px;text-align:center';
      document.body.appendChild(b);
    } catch (e) { /* DOM 尚未就緒也不要中斷載入 */ }
    gexData = {
      txf_price: ROOM_CHART_DEFAULTS.txf_price,
      zero_gamma_level: ROOM_CHART_DEFAULTS.zero_gamma_level,
      call_wall_strike: ROOM_CHART_DEFAULTS.call_wall_strike,
      put_wall_strike: ROOM_CHART_DEFAULTS.put_wall_strike,
      max_pain_strike: ROOM_CHART_DEFAULTS.max_pain_strike,
      session_shift: { txf_shift: 0 },
      vix_info: { taifex_vix: null }
    };
  }

  // Load Full Symbol Universe (1,423 entries: 1,383 stocks/ETFs with real history + 40 index/stock-futures codes)
  try {
    const uniRes = await fetch('../data/tw_symbols_universe.json');
    if (uniRes.ok) {
      symbolsUniverse = await uniRes.json();
      console.log(`✅ Loaded ${symbolsUniverse.length} symbols into Universe search cache.`);
    }
  } catch (e) {
    console.warn('⚠️ Could not load ../data/tw_symbols_universe.json', e);
  }

  // Phase 3: Load Multi-Asset Multi-Timeframe K-Lines Cache
  try {
    const klineRes = await fetch('../data/klines_cache.json?t=' + Date.now());
    if (klineRes.ok) {
      klinesCacheData = await klineRes.json();
      console.log('✅ [Phase 3] Loaded real multi-timeframe K-line cache for 8 core assets.');
    }
  } catch (e) {
    console.warn('⚠️ Could not load ../data/klines_cache.json', e);
  }

  // Phase 4: Load Institutional Momentum & Retail Small TX Data
  try {
    const momRes = await fetch('../data/momentum_data.json?t=' + Date.now());
    if (momRes.ok) {
      momentumData = await momRes.json();
      console.log('✅ [Phase 4] Loaded TAIFEX institutional momentum & retail positioning data.');
    }
  } catch (e) {
    console.warn('⚠️ Could not load ../data/momentum_data.json', e);
  }
}

/**
 * 2. Multi-Pane Synchronized Lightweight Charts Initialization (5 Charts)
 */
function initMultiPaneCharts() {
  const cMain = document.getElementById('tv-main-chart');
  const cSub1 = document.getElementById('tv-sub-chart-1');
  const cSub2 = document.getElementById('tv-sub-chart-2');
  const cSub3 = document.getElementById('tv-sub-chart-3');
  const cSub4 = document.getElementById('tv-sub-chart-4');
  if (!cMain || !cSub1 || !cSub2 || !cSub3 || !cSub4) return;

  cMain.innerHTML = '';
  cSub1.innerHTML = '';
  cSub2.innerHTML = '';
  cSub3.innerHTML = '';
  cSub4.innerHTML = '';

  const commonOptions = {
    layout: {
      background: { color: '#080c14' },
      textColor: '#8b949e',
      fontSize: window.matchMedia('(max-width: 768px), (max-width: 1100px) and (orientation: portrait)').matches ? 9 : 11,
      fontFamily: "'Outfit', -apple-system, BlinkMacSystemFont, sans-serif"
    },
    grid: {
      vertLines: { color: 'rgba(26, 37, 56, 0.35)' },
      horzLines: { color: 'rgba(26, 37, 56, 0.35)' }
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: { color: '#00d2ff', width: 1, style: LightweightCharts.LineStyle.Dashed, labelBackgroundColor: '#0d131f' },
      horzLine: { color: '#00d2ff', width: 1, style: LightweightCharts.LineStyle.Dashed, labelBackgroundColor: '#0d131f' }
    },
    rightPriceScale: {
      borderColor: '#1a2538',
      scaleMargins: { top: 0.1, bottom: 0.1 },
      autoScale: true
    },
    // 圖表套件只用 UTC 格式化時間（原始碼只有 getUTCHours），不設定的話台指期日盤第一根 08:45 會被標成 00:45，
    // 與台北時間差 8 小時。K 線時間戳本身是對的（真實 UTC），這裡只改「顯示」。2026-10-01 稽核發現。
    localization: { timeFormatter: chartTimeFormatter },
    timeScale: {
      borderColor: '#1a2538',
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 12,
      barSpacing: 8,
      tickMarkFormatter: chartTickFormatter
    }
  };

  // --- Main Candlestick Chart ---
  mainChart = LightweightCharts.createChart(cMain, {
    ...commonOptions,
    timeScale: { ...commonOptions.timeScale, visible: false } // Hidden to eliminate duplicate X axis
  });

  candleSeries = mainChart.addCandlestickSeries({
    upColor: '#ff4757',
    downColor: '#2ed573',
    borderUpColor: '#ff4757',
    borderDownColor: '#2ed573',
    wickUpColor: '#ff4757',
    wickDownColor: '#2ed573'
  });

  const subChartOptions = {
    ...commonOptions,
    rightPriceScale: {
      ...commonOptions.rightPriceScale,
      scaleMargins: { top: 0.26, bottom: 0.08 }
    }
  };

  // --- Sub-Chart 1: 成交量 Volume + Volume MA 5 & Volume MA 10 ---
  subChart1 = LightweightCharts.createChart(cSub1, {
    ...subChartOptions,
    timeScale: { ...commonOptions.timeScale, visible: false }
  });
  volumeSeries = subChart1.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: ''
  });
  volMa5Series = subChart1.addLineSeries({
    color: '#FFEB3B',
    lineWidth: 1.5,
    title: ''
  });
  volMa10Series = subChart1.addLineSeries({
    color: '#FFFFFF',
    lineWidth: 1.5,
    title: ''
  });

  // --- Sub-Chart 2: 戰情雙層 MACD (4 色柱體 + 快慢線) ---
  subChart2 = LightweightCharts.createChart(cSub2, {
    ...subChartOptions,
    timeScale: { ...commonOptions.timeScale, visible: false }
  });
  macdHistSeries = subChart2.addHistogramSeries({
    priceScaleId: 'right'
  });
  macdDifSeries = subChart2.addLineSeries({
    color: '#ffffff',
    lineWidth: 1.5,
    title: ''
  });
  macdDeaSeries = subChart2.addLineSeries({
    color: '#ffd700',
    lineWidth: 1.5,
    title: ''
  });

  // --- Sub-Chart 3: 波段拐點 CCI (20 通道 & 買賣轉折點) ---
  subChart3 = LightweightCharts.createChart(cSub3, {
    ...subChartOptions,
    timeScale: { ...commonOptions.timeScale, visible: false }
  });
  cciLineSeries = subChart3.addLineSeries({
    color: '#ffd700',
    lineWidth: 2,
    title: ''
  });
  // Add reference lines (+200, +100, 0, -100, -200)
  cciLineSeries.createPriceLine({ price: 200, color: 'rgba(0, 206, 201, 0.7)', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '' });
  cciLineSeries.createPriceLine({ price: 100, color: 'rgba(46, 213, 115, 0.6)', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '' });
  cciLineSeries.createPriceLine({ price: 0, color: 'rgba(255, 255, 255, 0.25)', lineStyle: LightweightCharts.LineStyle.Dotted, lineWidth: 1, title: '' });
  cciLineSeries.createPriceLine({ price: -100, color: 'rgba(255, 128, 128, 0.6)', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '' });
  cciLineSeries.createPriceLine({ price: -200, color: 'rgba(255, 0, 0, 0.7)', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '' });

  // --- Sub-Chart 4: 動能副圖 (AO / CVD / DMI) ---
  subChart4 = LightweightCharts.createChart(cSub4, {
    ...subChartOptions,
    timeScale: { ...commonOptions.timeScale, visible: true } // Bottom-most chart shows time axis
  });

  // Cross-Chart TimeScale Synchronization
  const allCharts = [mainChart, subChart1, subChart2, subChart3, subChart4];
  let isSyncing = false;

  allCharts.forEach((sourceChart, srcIdx) => {
    sourceChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (isSyncing || !range) return;
      isSyncing = true;
      allCharts.forEach((targetChart, tgtIdx) => {
        if (srcIdx !== tgtIdx && targetChart) {
          targetChart.timeScale().setVisibleLogicalRange(range);
        }
      });
      isSyncing = false;
    });
  });

  // Crosshair OHLC Legend Tracker
  mainChart.subscribeCrosshairMove((param) => {
    updateLegendOverlay(param);
  });

  // Responsive Auto-Resize
  window.addEventListener('resize', handleChartResize);

  // Load and Render Indicator Datasets
  renderChartData();
}

/**
 * Handle Resize for all 5 Charts
 */
// ---- 圖表時間顯示：UTC 時間戳 -> 台北時間（+8，台灣沒有日光節約）----
function _tpeParts(t) {
  const d = new Date((t + 8 * 3600) * 1000);
  return { y: d.getUTCFullYear(), mo: d.getUTCMonth() + 1, da: d.getUTCDate(), h: d.getUTCHours(), mi: d.getUTCMinutes() };
}
function chartTimeFormatter(t) {
  if (typeof t !== 'number') return '';
  const p = _tpeParts(t);
  const pad = (n) => String(n).padStart(2, '0');
  if (typeof currentTf !== 'undefined' && (currentTf === '1D' || currentTf === '1W' || currentTf === '1Mth')) {
    return `${p.y}-${pad(p.mo)}-${pad(p.da)}`;
  }
  return `${pad(p.mo)}/${pad(p.da)} ${pad(p.h)}:${pad(p.mi)}`;
}
function chartTickFormatter(t, type) {
  if (typeof t !== 'number') return null;
  const p = _tpeParts(t);
  const pad = (n) => String(n).padStart(2, '0');
  // type: 0 年、1 月、2 日、3 時:分、4 時:分:秒
  if (type === 0) return String(p.y);
  if (type === 1) return `${p.mo}月`;
  if (type === 2) return String(p.da);
  return `${pad(p.h)}:${pad(p.mi)}`;
}

function handleChartResize() {
  const cMain = document.getElementById('tv-main-chart');
  const cSub1 = document.getElementById('tv-sub-chart-1');
  const cSub2 = document.getElementById('tv-sub-chart-2');
  const cSub3 = document.getElementById('tv-sub-chart-3');
  const cSub4 = document.getElementById('tv-sub-chart-4');
  
  if (mainChart && cMain) mainChart.applyOptions({ width: cMain.clientWidth, height: cMain.clientHeight });
  if (subChart1 && cSub1) subChart1.applyOptions({ width: cSub1.clientWidth, height: cSub1.clientHeight });
  if (subChart2 && cSub2) subChart2.applyOptions({ width: cSub2.clientWidth, height: cSub2.clientHeight });
  if (subChart3 && cSub3) subChart3.applyOptions({ width: cSub3.clientWidth, height: cSub3.clientHeight });
  if (subChart4 && cSub4) subChart4.applyOptions({ width: cSub4.clientWidth, height: cSub4.clientHeight });
}

/**
 * Authentic Multi-Timeframe OHLC & Indicator Calculation Engine
 * Anchors strictly on current real market price (gexData.txf_price / stock quote)
 * Computes authentic MA, SMMA, VWAP, Dual MACD (4-color), CCI(20), AO, DMI/ADX, DeMark 9★/13★ & Momentum Birds
 */

// ---- 全市場個股日 K（證交所／櫃買官方資料）----
// klines_cache.json 只有 12 檔標的；其餘上千檔個股原本完全沒有 K 線。選到這類個股時，只下載「這檔股票所在的那一片」
// data/stock_daily/NN.json（64 片，每片約 100KB；分片規則須與 scripts/build_stock_daily_shards.py 及 Worker 一致），
// 轉成日 K，週 K／月 K 由日 K 合併而來（真實資料，不是推算）。分 K 沒有官方免費來源，維持「暫無真實K線」。
const stockDailyBySym = {};    // 代號 -> [{date,open,high,low,close,volume}]；null 代表該片存在但沒有這檔
const stockShardLoading = {};  // 片號 -> Promise
function stockShardOf(code) {
  let h = 5381;
  for (const ch of String(code)) h = (Math.imul(h, 33) + ch.charCodeAt(0)) >>> 0;
  return h % 64;
}
function loadStockDailyFor(sym) {
  if (sym in stockDailyBySym) return Promise.resolve(stockDailyBySym[sym]);
  const id = stockShardOf(sym);
  if (!stockShardLoading[id]) {
    const file = String(id).padStart(2, '0');
    stockShardLoading[id] = fetch(`../data/stock_daily/${file}.json`)
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(j => {
        Object.keys(j.bars || {}).forEach(code => {
          stockDailyBySym[code] = j.bars[code].map(r => ({ date: String(r[0]), open: r[1], high: r[2], low: r[3], close: r[4], volume: r[5] }));
        });
        return true;
      })
      .catch(e => { console.warn('⚠️ 載入個股日K分片失敗', e); stockShardLoading[id] = null; return false; });
  }
  return Promise.resolve(stockShardLoading[id]).then(ok => {
    if (!ok) return null;
    if (!(sym in stockDailyBySym)) stockDailyBySym[sym] = null;   // 這片有載入，但沒有這檔
    return stockDailyBySym[sym];
  });
}
function stockNeedsDailyLoad(sym, tf) {
  return !(sym in stockDailyBySym) && !klinesCacheData?.assets?.[sym] && (tf === '1D' || tf === '1W' || tf === '1Mth');
}
// 日K -> 指定週期。時間戳沿用 klines_cache 的日K慣例（該日 09:00 台北 = 01:00 UTC）；量單位「張」換成「股」與 klines 一致。
function dailyBarsToCandles(bars, tf) {
  if (!Array.isArray(bars)) return null;
  const rows = [];
  for (const b of bars) {
    const s = b && b.date;
    if (!s || s.length !== 8) continue;   // 沒日期的舊格式資料不用，寧可不畫也不猜日期
    const y = +s.slice(0, 4), m = +s.slice(4, 6), d = +s.slice(6, 8);
    rows.push({ y, m, d, time: Date.UTC(y, m - 1, d, 1, 0, 0) / 1000, open: b.open, high: b.high, low: b.low, close: b.close, volume: (b.volume || 0) * 1000 });
  }
  if (!rows.length) return null;
  if (tf === '1D') return rows.map(r => ({ time: r.time, open: r.open, high: r.high, low: r.low, close: r.close, volume: r.volume }));
  const keyOf = (r) => {
    if (tf === '1Mth') return r.y * 100 + r.m;
    const dt = new Date(Date.UTC(r.y, r.m - 1, r.d));            // 週K：以週一為一週起點
    const dow = (dt.getUTCDay() + 6) % 7;
    return Math.floor((dt.getTime() - dow * 86400000) / 86400000);
  };
  const out = [];
  let curKey = null, cur = null;
  for (const r of rows) {
    const k = keyOf(r);
    if (k !== curKey) {
      cur = { time: r.time, open: r.open, high: r.high, low: r.low, close: r.close, volume: r.volume };
      out.push(cur); curKey = k;
    } else {
      cur.high = Math.max(cur.high, r.high); cur.low = Math.min(cur.low, r.low);
      cur.close = r.close; cur.volume += r.volume;
    }
  }
  return out;
}

function generateIndicatorsData(tf) {
  let basePrice = null;
  let isYield = false;

  if (currentActiveSymbol) {
    isYield = !!currentActiveSymbol.is_yield;
    basePrice = realPriceFor(currentActiveSymbol.symbol);
  } else {
    basePrice = realPriceFor('TXF');
  }
  // Only used to size ATR/rounding for the flat placeholder of an un-cached symbol; a symbol with no
  // real price at all gets NO bars (count = 0 below) instead of an invented level.
  const hasRealPrice = basePrice !== null;
  if (!hasRealPrice) basePrice = 100;

  let count = 120;
  let intervalSec = 900; // 15M default
  let atrBase = 55;

  if (isYield) {
    atrBase = 0.025;
  } else if (basePrice > 20000) {
    atrBase = 65;
  } else if (basePrice > 1000) {
    atrBase = 9;
  } else if (basePrice > 100) {
    atrBase = 1.4;
  } else if (basePrice > 50) {
    atrBase = 0.55;
  } else {
    atrBase = 0.15;
  }
  
  if (tf === '1M') { count = 180; intervalSec = 60; atrBase *= 0.35; }
  else if (tf === '3M') { count = 160; intervalSec = 180; atrBase *= 0.55; }
  else if (tf === '5M') { count = 140; intervalSec = 300; atrBase *= 0.75; }
  else if (tf === '15M') { count = 120; intervalSec = 900; atrBase *= 1.0; }
  else if (tf === '30M') { count = 100; intervalSec = 1800; atrBase *= 1.4; }
  else if (tf === '1H') { count = 90; intervalSec = 3600; atrBase *= 2.0; }
  else if (tf === '4H') { count = 80; intervalSec = 14400; atrBase *= 3.8; }
  else if (tf === '1D') { count = 70; intervalSec = 86400; atrBase *= 7.5; }
  else if (tf === '1W') { count = 60; intervalSec = 604800; atrBase *= 15.0; }
  else if (tf === '1Mth') { count = 50; intervalSec = 2592000; atrBase *= 30.0; }

  const startTime = Math.floor(Date.now() / 1000) - (count * intervalSec);
  
  const candles = [];
  const volumes = [];
  const closes = [];
  const highs = [];
  const lows = [];
  const opens = [];
  
  // Decimals rounder helper
  const roundDec = (v) => isYield ? (Math.round(v * 1000) / 1000) : (basePrice < 500 ? (Math.round(v * 100) / 100) : (Math.round(v * 10) / 10));

  const sym = currentActiveSymbol?.symbol || 'TXF';
  const isIndexOrYield = sym === 'TAIEX' || sym === 'OTC' || sym === 'US10Y' || sym === 'DXY' || !!currentActiveSymbol?.is_yield || !!currentActiveSymbol?.is_index;
  let cachedCandles = klinesCacheData?.assets?.[sym]?.timeframes?.[tf];
  if (!cachedCandles && !klinesCacheData?.assets?.[sym] && (tf === '1D' || tf === '1W' || tf === '1Mth')) {
    cachedCandles = dailyBarsToCandles(stockDailyBySym[sym], tf);
  }

  if (cachedCandles && cachedCandles.length > 0) {
    // 🚀 Authentic Multi-Timeframe Real Market K-Line Dataset
    for (let i = 0; i < cachedCandles.length; i++) {
      const c = cachedCandles[i];
      const isUp = c.close >= c.open;
      candles.push({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close });
      
      // Indices (TAIEX, OTC, US10Y, DXY) strictly have 0 contract volume
      const realVol = isIndexOrYield ? 0 : (c.volume || 0);
      volumes.push({ 
        time: c.time, 
        value: realVol, 
        color: realVol > 0 ? (isUp ? 'rgba(255, 71, 87, 0.7)' : 'rgba(46, 213, 115, 0.7)') : 'transparent' 
      });
      
      opens.push(c.open);
      closes.push(c.close);
      highs.push(c.high);
      lows.push(c.low);
    }
    count = candles.length;
  } else {
    // Baseline flat bars for un-cached symbol (never synthesize fake random waves)
    // A symbol that IS in klines_cache.json but has no bars for this timeframe (e.g. OTC intraday: TPEx
    // publishes daily index bars only) gets no bars — a flat line at today's price would look like data.
    count = 0; // 沒有真實 K 線就不畫（水平線看起來像有資料，2026-09-30 稽核移除）
    for (let i = 0; i < count; i++) {
      const t = startTime + (i * intervalSec);
      const p = roundDec(basePrice);
      candles.push({ time: t, open: p, high: p, low: p, close: p });
      volumes.push({ time: t, value: 0, color: 'transparent' });
      opens.push(p);
      closes.push(p);
      highs.push(p);
      lows.push(p);
    }
  }

  // --- Real Volume 5MA & 10MA ---
  const volMa5 = [];
  const volMa10 = [];
  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    if (i >= 4) {
      let sum5 = 0;
      for (let k = 0; k < 5; k++) sum5 += volumes[i - k].value;
      volMa5.push({ time: t, value: Math.round(sum5 / 5) });
    }
    if (i >= 9) {
      let sum10 = 0;
      for (let k = 0; k < 10; k++) sum10 += volumes[i - k].value;
      volMa10.push({ time: t, value: Math.round(sum10 / 10) });
    }
  }

  // 均線彩帶 MA7/17/88/200、ADX Pro V3、神奇九轉、動能鳥箭頭、VWAP、SMMA、VRVP、SAR、Supertrend 的運算
  // 已搬到私有 Cloudflare Worker（indicator=chart），網頁只畫它回傳的結果；見 fetchChartBundle()。
  // 這裡刻意留空，不留公式當備援（留著就等於沒搬）。
  const ma7 = [], ma17 = [], ma88 = [], ma200 = [];

  // 2026-09-24: 戰情雙層MACD/波段拐點CCI/AO 這三個原本在這裡算的真公式已經搬去
  // bluebird-indicators Cloudflare Worker（indicator=momentum）做IP保護，瀏覽器「檢視原始碼」
  // 不再看得到算法本身。這裡故意留空陣列而不是留著公式當「萬一Worker掛掉的備援」——留著公式
  // 就等於白搬，一樣看得到。真正的數值由 updateMomentumSeries()/renderSub4Chart() 的 'ao'
  // 分支非同步呼叫 fetchMomentumFromWorker() 取得後，直接呼叫對應 series 的 setData()，不經過
  // 這個函式的同步回傳值。Worker 目前只覆蓋 klines_cache.json 現有12個標的，其他商品會誠實
  // 顯示「暫無真實數據」而不是空白公式湊出來的假數字。
  const macdData = [];
  const difData = [];
  const deaData = [];
  const cciData = [];
  const cciSignals = [];
  const aoData = [];

  // --- 2026-09-25: CVD (Cumulative Volume Delta) 真實化 — 原本這裡是用單根K棒開高低收
  // 比例湊出來的近似公式，已移除（比照AO/雙層MACD/CCI的模式，不留公式當「萬一沒有真實數據時
  // 的備援」，留著就等於還是假數據）。真實CVD K棒改由 fetchAndRenderCvd() 輪詢後端 /api/cvd
  // （scripts/fubon_api_provider.py 的 get_cvd_series()，逐筆真實tick-rule買賣方向累積），
  // 用 buildCvdCandlesFromPoints() 依目前選擇的時間週期即時重新分組。只能從連線當下開始累積，
  // 此session開始前的歷史時段故意留白，不補假資料。
  const cvdCandles = [];

  // --- 🐂 大戶散戶動能指標 (陳玠儒/股市擺渡人方法論：委託口差 + 成交筆數差) ---
  // 2026-09-13 self-audit 更正：這裡原本用 K 棒開高低收公式湊出一條假的「大戶動能」與
  // 「散戶反向線」（散戶=大戶乘負數），跟真實法人/委託簿資料完全無關。已移除。
  // 真實數據改由 scripts/fubon_api_provider.py 的 Books(五檔)/Trades(逐筆成交) 頻道即時算，
  // 透過 fetchAndAppendMomentumBar() 用真實資料即時附加最新一根 30 分鐘 bar，見該函式定義。
  // 這裡刻意留空陣列：對「還沒有真實資料的歷史時段」，寧可不畫，也不假裝有數據。
  const momentumHist = [];   // 大戶委託口差 (紅柱，即時附加)
  const momentumLine = [];   // 保留給未來需要的平滑線，目前未使用
  const retailLine = [];     // 散戶成交筆數差 (綠柱，即時附加)
  const marketOrderLine = []; // 市場委買委賣口差 (黃線，即時附加)

  const adxLine = [], adxHist = [], adxSignals = [];
  const markers = [], demarkMarkers = [];
  const vwapData = [], vwapUpper = [], vwapLower = [], smmaData = [];
  const sarData = [], supertrendUp = [], supertrendDown = [];
  const vrvpData = null;

  return {
    candles,
    volumes,
    volMa5,
    volMa10,
    ma7,
    ma17,
    ma88,
    ma200,
    macdData,
    difData,
    deaData,
    cciData,
    cciSignals,
    aoData,
    cvdCandles,
    momentumHist,
    momentumLine,
    retailLine,
    marketOrderLine,
    adxLine,
    adxHist,
    adxSignals,
    markers,
    demarkMarkers,
    vwapData,
    vwapUpper,
    vwapLower,
    smmaData,
    sarData,
    supertrendUp,
    supertrendDown,
    vrvpData
  };
}

/**
 * Render all 5 Charts with Datasets
 */
// ---- 主圖與 ADX 副圖的指標運算：全部在私有 Cloudflare Worker（indicator=chart），網頁只畫結果 ----
const CHART_BUNDLE_FIELDS = ['ma7', 'ma17', 'ma88', 'ma200', 'adxLine', 'adxHist', 'adxSignals', 'markers', 'demarkMarkers',
  'vwapData', 'vwapUpper', 'vwapLower', 'smmaData', 'sarData', 'supertrendUp', 'supertrendDown', 'vrvpData'];
const _chartBundleCache = {};
async function fetchChartBundle(symbol, tf) {
  const q = new URLSearchParams({
    indicator: 'chart', symbol, tf,
    smma: indicatorConfig.smmaLen || 200, rows: indicatorConfig.vrvpRows || 50, va: indicatorConfig.vrvpVa || 70,
    sar: indicatorConfig.sarStep || 0.02, stlen: indicatorConfig.stLen || 10, stmult: indicatorConfig.stMult || 3
  });
  const key = q.toString();
  if (_chartBundleCache[key]) return _chartBundleCache[key];
  const pr = (async () => {
    try {
      const resp = await fetch(`${ADX_MTF_API}?${key}`);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const b = await resp.json();
      // 舊版 Worker 不認得 indicator=chart，會當成 ADX 回 200；用欄位確認拿到的真的是運算結果
      if (!b || !Array.isArray(b.ma7) || !Array.isArray(b.adxLine)) throw new Error('Worker 尚未更新（沒有 chart 端點）');
      return b;
    } catch (e) {
      console.warn('⚠️ 主圖指標 Worker fetch failed:', e);
      delete _chartBundleCache[key];   // 失敗不快取，下次重試
      return null;
    }
  })();
  _chartBundleCache[key] = pr;
  return pr;
}
function applyChartBundle(data, b) {
  CHART_BUNDLE_FIELDS.forEach(k => { if (b[k] !== undefined) data[k] = b[k]; });
}
function setChartBundleNotice(text) {
  const pane = document.getElementById('main-chart-pane');
  if (!pane) return;
  let n = document.getElementById('chart-bundle-notice');
  if (!n) {
    n = document.createElement('div');
    n.id = 'chart-bundle-notice';
    n.style.cssText = 'position:absolute;left:8px;bottom:36px;z-index:18;padding:3px 8px;border-radius:4px;background:rgba(13,17,23,0.85);border:1px dashed rgba(255,215,0,0.4);color:#ffd700;font-size:0.68rem;pointer-events:none;';
    pane.appendChild(n);
  }
  n.style.display = text ? 'block' : 'none';
  n.textContent = text || '';
}
let lastChartData = null;   // 最近一次畫圖用的資料（切換副圖分頁時沿用，不必重算）

function renderChartData() {
  const _symForLoad = currentActiveSymbol?.symbol || 'TXF';
  if (stockNeedsDailyLoad(_symForLoad, currentTf)) {
    loadStockDailyFor(_symForLoad).then(bars => { if (bars) renderChartData(); });   // 載入完成再重畫一次
  }
  const data = generateIndicatorsData(currentTf);
  // Explain an intentionally empty chart (no real bars for this symbol/timeframe) instead of leaving it blank.
  {
    const _pane = document.getElementById('main-chart-pane');
    if (_pane) {
      let _n = document.getElementById('no-real-kline-notice');
      if (!_n) {
        _n = document.createElement('div');
        _n.id = 'no-real-kline-notice';
        _n.style.cssText = 'position:absolute;top:44%;left:50%;transform:translate(-50%,-50%);z-index:20;padding:10px 16px;border-radius:8px;background:rgba(13,17,23,0.85);border:1px dashed rgba(255,215,0,0.45);color:#ffd700;font-size:0.85rem;pointer-events:none;text-align:center;';
        if (getComputedStyle(_pane).position === 'static') _pane.style.position = 'relative';
        _pane.appendChild(_n);
      }
      const empty = !data.candles || data.candles.length === 0;
      _n.style.display = empty ? 'block' : 'none';
      if (empty) {
        const _isIntraday = !['1D', '1W', '1Mth'].includes(currentTf);
        const _hasDaily = !!stockDailyBySym[currentActiveSymbol?.symbol];
        _n.textContent = (_isIntraday && (_hasDaily || stockNeedsDailyLoad(currentActiveSymbol?.symbol, '1D')))
          ? `⚪ ${currentActiveSymbol?.name || ''} 目前只提供日K以上（分K沒有官方免費來源），請切換 1D／1週／1月`
          : `⚪ ${currentActiveSymbol?.name || ''} ${currentTf} 暫無真實K線數據（官方來源未提供此時間級別）`;
      }
    }
  }

  // 1. Candlesticks on Main Chart
  candleSeries.setData(data.candles);
  legendLastCandle = (data.candles && data.candles.length) ? data.candles[data.candles.length - 1] : null;
  updateLegendOverlay(null);

  // 2. Sub-Chart 1: 成交量 + Volume MA 5 & Volume MA 10 (價格指數與殖利率無合約成交量)
  const sym = currentActiveSymbol?.symbol || 'TXF';
  const isIndexOrYield = sym === 'TAIEX' || sym === 'OTC' || sym === 'US10Y' || sym === 'DXY' || !!currentActiveSymbol?.is_yield || !!currentActiveSymbol?.is_index;
  const pane1Badge = document.getElementById('pane-1-badge');

  if (isIndexOrYield) {
    volumeSeries.setData([]);
    volMa5Series.setData([]);
    volMa10Series.setData([]);
    if (pane1Badge) {
      pane1Badge.innerHTML = '⚪ 價格指數/殖利率無合約成交量 (Volume: 0)';
    }
  } else {
    volumeSeries.setData(data.volumes);
    volMa5Series.setData(data.volMa5);
    volMa10Series.setData(data.volMa10);
    if (pane1Badge) {
      pane1Badge.innerHTML = '📊 成交量 Volume (Volume MA 5 / 10)';
    }
  }

  // 3./4. Sub-Chart 2 (戰情雙層MACD) / Sub-Chart 3 (波段拐點CCI) —— 真公式已搬去Cloudflare
  // Worker（見 fetchMomentumFromWorker()），這裡先用空值起手不卡住其他同步渲染，真數字非同步
  // 抵達後由 updateMomentumSeries() 自己呼叫 setData()。
  macdHistSeries.setData([]);
  macdDifSeries.setData([]);
  macdDeaSeries.setData([]);
  cciLineSeries.setData([]);
  cciLineSeries.setMarkers([]);
  updateMomentumSeries(sym, currentTf, data);

  // 5. Sub-Chart 4: ADX Pro V3 / AO / CVD Candlesticks / Momentum
  renderSub4Chart(data);

  // 6. Main Chart Overlays (GEX + Ribbons + VWAP + SMMA)
  renderMainOverlays(data);

  // 6b. 彩帶／ADX／九轉／動能鳥箭頭／VWAP／SMMA／VRVP／SAR／Supertrend 由 Worker 算好後補畫
  data._sym = sym; data._tf = currentTf;
  lastChartData = data;
  if (data.candles && data.candles.length >= 2) {
    const _bSym = sym, _bTf = currentTf;
    fetchChartBundle(_bSym, _bTf).then(b => {
      if ((currentActiveSymbol?.symbol || 'TXF') !== _bSym || currentTf !== _bTf) return;   // 使用者已切換商品／週期
      if (!b) {
        setChartBundleNotice('⚪ 指標線（均線彩帶／ADX／VWAP／VRVP…）需由 Worker 計算，目前取不到');
        return;
      }
      setChartBundleNotice('');
      applyChartBundle(data, b);
      if (activeSub4 === 'adx' && sub4Series.adx) {
        sub4Series.adx.setData(data.adxLine);
        sub4Series.adx.setMarkers(data.adxSignals);
      }
      renderMainOverlays(data);
    });
  } else {
    setChartBundleNotice('');
  }

  // 7. Smart Money Concepts overlay (optional; computed by the private Worker)
  smcCandleTimes = (data.candles || []).map(c => c.time);
  renderSmcOverlay();
}

// 2026-09-16: ADX Pro V3 副圖的 MTF (多週期) 看板文字，原本是凍結的假字串
// "15M:21.1 1H:29.9 4H:25.7 1D:11.1"，跟畫面上其他即時數據完全脫節。真正的 ADX 算法現在搬到
// 一個私有 Cloudflare Worker（不在這個公開 repo 裡，也不會傳到瀏覽器），這裡改成呼叫那支 API
// 拿「已經算好的真實數字」回來，room.js 本身不再包含 ADX 公式——這是保護尋鳥自有指標演算法
// 不被瀏覽器「檢視原始碼」看走的第一個試點，後續其他指標會陸續比照辦理。
// ===== Smart Money Concepts overlay =====================================================================================
// Concept & algorithm: "Smart Money Concepts [LuxAlgo]" © LuxAlgo, CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/).
// The calculation runs in the owner's PRIVATE Cloudflare Worker (indicator=smc) — this page only draws the returned events
// (personal, non-commercial use). Colors follow the Taiwan convention: bullish = red, bearish = green.
const SMC_BULL = '#ff4757', SMC_BEAR = '#2ed573';
let smcEnabled = false;
try { smcEnabled = localStorage.getItem('txo_smc_on') === '1'; } catch (e) { /* storage may be blocked */ }
let smcSeries = [];
let smcSeq = 0;
let smcCandleTimes = [];
const _smcCache = {};

function clearSmcOverlay() {
  smcSeries.forEach(s => { try { mainChart.removeSeries(s); } catch (e) { /* already gone */ } });
  smcSeries = [];
}

async function fetchSmcFromWorker(symbol, tf) {
  // the indicator-library checkbox 'FVG / Order Blocks (SMC)' adds fair value gaps and swing order blocks
  const extra = (typeof indicatorConfig !== 'undefined' && indicatorConfig.fvg) ? '&fvg=1&swingob=1' : '';
  const key = `${symbol}|${tf}|${extra}`;
  const hit = _smcCache[key];
  if (hit && Date.now() - hit.at < 60000) return hit.value;
  let value = null;
  try {
    const resp = await fetch(`${ADX_MTF_API}?indicator=smc&symbol=${encodeURIComponent(symbol)}&tf=${encodeURIComponent(tf)}${extra}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    if (json && Array.isArray(json.events)) value = json;
  } catch (e) {
    console.warn('⚠️ SMC Worker fetch failed (has the Worker been updated with indicator=smc?):', e);
  }
  _smcCache[key] = { at: Date.now(), value };
  return value;
}

function _smcNearestTime(t) {
  // nearest candle time on the chart (markers must sit on an existing data point)
  const a = smcCandleTimes;
  if (!a.length) return t;
  let lo = 0, hi = a.length - 1;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (a[mid] < t) lo = mid + 1; else hi = mid; }
  if (lo > 0 && Math.abs(a[lo - 1] - t) <= Math.abs(a[lo] - t)) lo -= 1;
  return a[lo];
}

function _smcAddLine(points, color, style, width, markers) {
  const pts = points.filter(p => p && p.time != null && p.value != null).sort((x, y) => x.time - y.time)
    .filter((p, i, arr) => i === 0 || p.time !== arr[i - 1].time);
  if (pts.length < 2) return;
  const s = mainChart.addLineSeries({ color, lineWidth: width || 1, lineStyle: style || 0, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
  s.setData(pts);
  if (markers && markers.length) s.setMarkers(markers);
  smcSeries.push(s);
}

async function renderSmcOverlay() {
  clearSmcOverlay();
  const mySeq = ++smcSeq;
  const btn = document.getElementById('smc-toggle-btn');
  if (btn) btn.classList.toggle('active', smcEnabled);
  const smcWanted = smcEnabled || (typeof indicatorConfig !== 'undefined' && indicatorConfig.fvg);
  if (!smcWanted || !mainChart || !smcCandleTimes.length) return;
  const sym = currentActiveSymbol?.symbol || 'TXF';
  const res = await fetchSmcFromWorker(sym, currentTf);
  if (mySeq !== smcSeq) return;           // a newer render superseded this one
  if (btn) btn.dataset.smcStatus = res ? 'ok' : 'no-data';
  if (!res) return;
  const lastT = smcCandleTimes[smcCandleTimes.length - 1];
  const col = dir => (dir === 'bull' || dir === 1) ? SMC_BULL : SMC_BEAR;
  const alpha = (hex, a) => `${hex}${Math.round(a * 255).toString(16).padStart(2, '0')}`;

  // market structure: BOS / CHoCH (internal = dashed, swing = solid)
  (res.events || []).forEach(e => {
    const mid = _smcNearestTime(Math.round((e.t0 + e.t1) / 2));
    _smcAddLine([{ time: e.t0, value: e.level }, { time: mid, value: e.level }, { time: e.t1, value: e.level }], col(e.dir), e.internal ? 2 : 0, 1,
      [{ time: mid, position: e.dir === 'bull' ? 'aboveBar' : 'belowBar', color: col(e.dir), shape: 'square', text: e.kind }]);
  });
  // equal highs / lows
  (res.eq || []).forEach(q => {
    const c = q.type === 'EQH' ? SMC_BEAR : SMC_BULL;
    _smcAddLine([{ time: q.t0, value: q.level0 }, { time: q.t1, value: q.level1 }], c, 1, 1,
      [{ time: q.t1, position: q.type === 'EQH' ? 'aboveBar' : 'belowBar', color: c, shape: 'circle', text: q.type }]);
  });
  // order blocks: top & bottom edge from the block's bar to the latest bar
  const drawObs = (list, label, a) => (list || []).forEach(ob => {
    const bull = ob.bias === 1;
    const c = alpha(col(bull ? 'bull' : 'bear'), a);
    const t0 = _smcNearestTime(ob.time);
    _smcAddLine([{ time: t0, value: ob.top }, { time: lastT, value: ob.top }], c, 0, 1,
      [{ time: t0, position: bull ? 'belowBar' : 'aboveBar', color: col(bull ? 'bull' : 'bear'), shape: 'arrowUp', text: label }]);
    _smcAddLine([{ time: t0, value: ob.bottom }, { time: lastT, value: ob.bottom }], c, 0, 1);
  });
  drawObs(res.internal_order_blocks, 'iOB', 0.75);
  drawObs(res.swing_order_blocks, 'OB', 1);
  // fair value gaps
  (res.fvg || []).forEach(g => {
    const c = alpha(g.bias === 1 ? SMC_BULL : SMC_BEAR, 0.6);
    _smcAddLine([{ time: g.t0, value: g.top }, { time: Math.max(g.t1, g.t0 + 1), value: g.top }], c, 1, 1);
    _smcAddLine([{ time: g.t0, value: g.bottom }, { time: Math.max(g.t1, g.t0 + 1), value: g.bottom }], c, 1, 1);
  });
  // strong / weak high & low
  if (res.trailing) {
    const tr = res.trailing;
    _smcAddLine([{ time: _smcNearestTime(tr.top_time), value: tr.top }, { time: lastT, value: tr.top }], SMC_BEAR, 0, 1,
      [{ time: lastT, position: 'aboveBar', color: SMC_BEAR, shape: 'square', text: tr.top_label }]);
    _smcAddLine([{ time: _smcNearestTime(tr.bottom_time), value: tr.bottom }, { time: lastT, value: tr.bottom }], SMC_BULL, 0, 1,
      [{ time: lastT, position: 'belowBar', color: SMC_BULL, shape: 'square', text: tr.bottom_label }]);
  }
}

function toggleSmcOverlay() {
  smcEnabled = !smcEnabled;
  try { localStorage.setItem('txo_smc_on', smcEnabled ? '1' : '0'); } catch (e) { /* ignore */ }
  renderSmcOverlay();
}

const ADX_MTF_API = 'https://bluebird-indicators.bluebird-finder-tw.workers.dev/';

// 2026-09-17: 左側「🦅 動能鳥指標 即時戰情」HUD 卡片（系統模式/監控標的/趨勢乖離/量能指標/
// 波段動能/趨勢排列/綜合戰力）從建立以來就是純靜態文字，room.js 從未寫入過這幾個欄位
// （left-hud-bias/mfi/adx/trend/strength），跟 v63.0 修過的「GEX造市商五大防線」是同一種
// 「有UI但沒接資料」問題。這幾個欄位剛好一對一對應 動能鳥 Worker 回傳的
// bias88/mfi/adx/is_bull_trend/strength_grade，現在接上真實數據。
//
// ⚠️ 尚未對照真實 TradingView 圖表逐根K棒驗證過（見 worker.js 註解），is_holding/
// reduce_count 這類需要很多根K棒才會顯現的狀態，暖機起點可能跟 TradingView 實際載入的K棒
// 數不同而有落差。卡片標題會標註「(未驗證)」，正式核對過後再拿掉這個標籤。
const MOMENTUM_BIRD_SUPPORTED_SYMBOLS = new Set(['TXF', 'TAIEX', 'OTC', 'CDF', 'MTX', 'MXF', 'US10Y', 'DXY', 'CL', 'GC', '2330', '2454', '2317']);

async function updateMomentumBirdHud(symObj) {
  const modeEl = document.getElementById('left-hud-mode');
  const assetEl = document.getElementById('left-hud-asset');
  const biasEl = document.getElementById('left-hud-bias');
  const mfiEl = document.getElementById('left-hud-mfi');
  const adxEl = document.getElementById('left-hud-adx');
  const trendEl = document.getElementById('left-hud-trend');
  const strengthEl = document.getElementById('left-hud-strength');
  if (!modeEl || !assetEl || !biasEl || !mfiEl || !adxEl || !trendEl || !strengthEl) return;

  // 用實際選到的代號問 Worker（Worker 已支援全市場個股日K）；算不出來就顯示無資料，不再用台指期的數字頂替。
  const symbol = (symObj && symObj.symbol) ? symObj.symbol : 'TXF';
  modeEl.innerText = 'Auto (動能鳥)';
  assetEl.innerText = `${symbol} (1D)`;

  try {
    let resp = await fetch(`${ADX_MTF_API}?indicator=bird&symbol=${symbol}&tf=1D`);
    if (!resp.ok) resp = await fetch(`${ADX_MTF_API}?indicator=jj&symbol=${symbol}&tf=1D`);  // TEMP fallback until the Worker is redeployed with the 'bird' route
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const j = await resp.json();

    const biasColor = j.bias88 >= 0 ? 'var(--call-color)' : 'var(--put-color)';
    biasEl.innerText = `${j.bias88 >= 0 ? '+' : ''}${j.bias88}%`;
    biasEl.style.color = biasColor;

    mfiEl.innerText = j.mfi != null ? j.mfi.toFixed(1) : '—（無量能資料）';

    adxEl.innerText = j.adx != null ? j.adx.toFixed(1) : '—';

    const trendColor = j.is_bull_trend ? 'var(--call-color)' : 'var(--put-color)';
    trendEl.innerText = j.is_bull_trend ? 'Bullish (多)' : 'Bearish (空)';
    trendEl.style.color = trendColor;

    const gradeText = { S: 'S 強噴', A: 'A 強勢', B: 'B 一般', C: 'C 空頭防守' }[j.strength_grade] || j.strength_grade;
    const gradeColor = j.strength_grade === 'S' ? 'var(--gold-accent)' : (j.strength_grade === 'C' ? 'var(--put-color)' : 'var(--call-color)');
    strengthEl.innerText = gradeText;
    strengthEl.style.color = gradeColor;
  } catch (e) {
    console.warn('⚠️ 動能鳥 HUD fetch failed:', e);
    biasEl.innerText = '—';
    mfiEl.innerText = '—';
    adxEl.innerText = '—';
    trendEl.innerText = '⚪ 無即時數據';
    trendEl.style.color = 'var(--text-muted)';
    strengthEl.innerText = '—';
  }
}

// 2026-09-24: 戰情雙層MACD/波段拐點CCI/AO 搬去同一個 bluebird-indicators Worker
// （indicator=momentum）——跟 ADX/動能鳥同一套模式，同一個symbol+tf在短時間內重複render
// （例如切換分頁再切回來）不用重複打API，用這個簡單快取存最近一次的in-flight/已完成promise。
let _momentumCacheKey = null;
let _momentumCachePromise = null;

async function fetchMomentumFromWorker(symbol, tf) {
  const key = `${symbol}|${tf}`;
  if (_momentumCacheKey === key && _momentumCachePromise) return _momentumCachePromise;
  _momentumCacheKey = key;
  _momentumCachePromise = (async () => {
    try {
      const resp = await fetch(`${ADX_MTF_API}?indicator=momentum&symbol=${symbol}&tf=${tf}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn('⚠️ 戰情雙層MACD/CCI/AO Worker fetch failed:', e);
      return null;
    }
  })();
  return _momentumCachePromise;
}

// 更新 Sub-Chart 2 (雙層MACD) / Sub-Chart 3 (CCI) —— 這兩個一直都顯示，不像AO是分頁式。
// 非同步：renderChartData() 呼叫這個之後不等它，candles/volume等其他同步資料照常先畫出來，
// MACD/CCI 晚一點點才跟著真數字出現，比整個畫面卡住等API回應體驗好。
async function updateMomentumSeries(symbol, tf, data) {
  const result = await fetchMomentumFromWorker(symbol, tf);
  // 使用者可能在API回應之前就切換了商品或時框，這時候這批數字已經過期，不能覆蓋畫面
  if ((currentActiveSymbol?.symbol || 'TXF') !== symbol || currentTf !== tf) return;
  if (result && result.macd && result.cci) {
    macdHistSeries.setData(result.macd.hist);
    macdDifSeries.setData(result.macd.dif);
    macdDeaSeries.setData(result.macd.dea);
    cciLineSeries.setData(result.cci.line);
    cciLineSeries.setMarkers(result.cci.signals.map(s => ({ time: s.time, position: 'inBar', color: s.color, shape: 'circle', text: s.text })));

    // 主圖🚀/🐦/🛸/💰箭頭與神奇九轉由 Worker 的 indicator=chart 一併回傳（見 fetchChartBundle()）。
  } else {
    macdHistSeries.setData([]);
    macdDifSeries.setData([]);
    macdDeaSeries.setData([]);
    cciLineSeries.setData([]);
    cciLineSeries.setMarkers([]);
  }
}

async function updateAdxMtfBadge() {
  const badge = document.getElementById('pane-4-badge');
  if (!badge) return;
  try {
    const resp = await fetch(`${ADX_MTF_API}?symbol=TXF&mtf=1`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const j = await resp.json();
    const adx = j.adx || {};
    const fmt = (v) => (v == null ? '—' : v.toFixed(1));
    badge.innerText = `🔥 ADX Pro V3 雙色趨勢強度 (台指期 EMA14 全時 15M:${fmt(adx['15M'])} 1H:${fmt(adx['1H'])} 4H:${fmt(adx['4H'])} 1D:${fmt(adx['1D'])})`;
  } catch (e) {
    console.warn('⚠️ ADX MTF badge fetch failed:', e);
    badge.innerText = '🔥 ADX Pro V3 雙色趨勢強度 (台指期 EMA14 全時 — 暫時無法取得多週期數據)';
  }
}

/**
 * Render Sub-Chart 4 based on Active Tab ('adx' | 'ao' | 'cvd' | 'momentum')
 */
function renderSub4Chart(data) {
  if (!subChart4) return;
  
  // Clear previous series
  if (sub4Series.adx) { subChart4.removeSeries(sub4Series.adx); sub4Series.adx = null; }
  if (sub4Series.adxLine) { subChart4.removeSeries(sub4Series.adxLine); sub4Series.adxLine = null; }
  if (sub4Series.ao) { subChart4.removeSeries(sub4Series.ao); sub4Series.ao = null; }
  if (sub4Series.cvd) { subChart4.removeSeries(sub4Series.cvd); sub4Series.cvd = null; }
  if (sub4Series.momentumHist) { subChart4.removeSeries(sub4Series.momentumHist); sub4Series.momentumHist = null; }
  if (sub4Series.momentumLine) { subChart4.removeSeries(sub4Series.momentumLine); sub4Series.momentumLine = null; }
  if (sub4Series.retailLine) { subChart4.removeSeries(sub4Series.retailLine); sub4Series.retailLine = null; }
  if (sub4Series.marketOrderLine) { subChart4.removeSeries(sub4Series.marketOrderLine); sub4Series.marketOrderLine = null; }
  stopMomentumLivePolling();
  stopCvdLivePolling();

  const badge = document.getElementById('pane-4-badge');

  if (activeSub4 === 'adx') {
    if (badge) badge.innerText = '🔥 ADX Pro V3 雙色趨勢強度 (台指期 EMA14 全時 讀取中...)';
    updateAdxMtfBadge(); // async — fills in real 15M/1H/4H/1D values once the API responds

    // 1. ADX Area Series with smooth gradient fill (1:1 對齊 TradingView)
    sub4Series.adx = subChart4.addAreaSeries({
      topColor: 'rgba(239, 83, 80, 0.38)',
      bottomColor: 'rgba(38, 166, 154, 0.04)',
      lineColor: '#FF5252',
      lineWidth: 2,
      priceScaleId: 'right',
      title: '',
      // 依可見資料自動縮放：下限固定 0、上限至少涵蓋 26.65 頂部門檻，避免整段被壓成平線
      autoscaleInfoProvider: (original) => {
        const res = original();
        const dataMax = res && res.priceRange ? res.priceRange.maxValue : 0;
        const top = Math.max(30, Math.min(dataMax * 1.1, 100));
        return { priceRange: { minValue: 0, maxValue: top }, margins: res ? res.margins : undefined };
      }
    });

    // 2. 4 大標準門檻參考線 (26.65 頂部, 22.37 突破, 11.63 打底, 0.00)
    sub4Series.adx.createPriceLine({ price: 26.65, color: '#EF5350', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1.5, title: '' });
    sub4Series.adx.createPriceLine({ price: 22.37, color: '#FFA726', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '' });
    sub4Series.adx.createPriceLine({ price: 11.63, color: '#26A69A', lineStyle: LightweightCharts.LineStyle.Dotted, lineWidth: 1, title: '' });
    sub4Series.adx.createPriceLine({ price: 0, color: 'rgba(255, 255, 255, 0.25)', lineStyle: LightweightCharts.LineStyle.Dotted, lineWidth: 1, title: '' });

    sub4Series.adx.setData(data.adxLine);
    sub4Series.adx.setMarkers(data.adxSignals);
  } else if (activeSub4 === 'ao') {
    // 真公式已搬去Cloudflare Worker（見 fetchMomentumFromWorker()），非同步抵達
    if (badge) badge.innerText = '⚡ AO 震盪指標 (Awesome Oscillator，讀取中...)';
    sub4Series.ao = subChart4.addHistogramSeries({ priceScaleId: 'right' });
    const aoSeriesRef = sub4Series.ao;
    const aoSymbol = currentActiveSymbol?.symbol || 'TXF';
    const aoTf = currentTf;
    fetchMomentumFromWorker(aoSymbol, aoTf).then(result => {
      // series可能已經被移除/換掉（使用者切走分頁或切換商品/時框），舊的回應不要寫進新畫面
      if (sub4Series.ao !== aoSeriesRef || activeSub4 !== 'ao') return;
      if (result && result.ao) {
        aoSeriesRef.setData(result.ao);
        if (badge) badge.innerText = '⚡ AO 震盪指標 (Awesome Oscillator)';
      } else {
        aoSeriesRef.setData([]);
        if (badge) badge.innerText = '⚡ AO 震盪指標 (此標的暫無真實數據)';
      }
    });
  } else if (activeSub4 === 'cvd') {
    // 2026-09-25 真實化：不再用K棒開高低收公式湊近似值，改即時輪詢後端 /api/cvd
    // （真實逐筆tick-rule買賣方向累積），見 fetchAndRenderCvd()。此session開始前、或後端
    // 尚未連上富邦Trades時，故意留白不補假資料，比照大戶散戶動能的處理方式。
    const cvdSymbolCode = flowFuturesCodeFor(currentActiveSymbol);
    const isCvdEligible = !!cvdSymbolCode;
    if (badge) {
      badge.innerText = isCvdEligible
        ? `🎯 CVD 累積量差 K 線 (${cvdSymbolCode} 真實逐筆成交tick-rule累積，讀取中...)`
        : '🎯 CVD 累積量差 K 線 (只有台指期／小台／微台與有個股期貨的股票才有逐筆成交數據，此商品沒有)';
    }
    sub4Series.cvd = subChart4.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350'
    });
    sub4Series.cvd.setData([]);
    sub4Series.cvd.createPriceLine({
      price: 0,
      color: 'rgba(255, 255, 255, 0.4)',
      lineStyle: LightweightCharts.LineStyle.Dotted,
      lineWidth: 1,
      title: ''
    });
    if (isCvdEligible) startCvdLivePolling(cvdSymbolCode);
  } else if (activeSub4 === 'momentum') {
    // 2026-09-13 更正：此副圖過去用 K 棒公式湊假數據，已移除。
    // 現在只畫「這個 session 開始追蹤之後」真正收到的富邦 Books(五檔)/Trades(逐筆成交) 資料，
    // 30分鐘 bar 由 fetchAndAppendMomentumBar() 即時輪詢附加，見該函式與後端
    // scripts/fubon_api_provider.py 的 get_momentum_bar_30m()。歷史時段（此 session 開始前）
    // 沒有真數據可畫，故意留白，不補假資料。
    const symbolCode = flowFuturesCodeFor(currentActiveSymbol);   // 指數期貨、個股期貨；股票則對應其期貨合約
    const isMomentumEligible = !!symbolCode;
    if (badge) {
      badge.innerText = isMomentumEligible
        ? `🐂 大戶散戶動能 (${symbolCode} 真實 Books/Trades 即時串接；資料自服務啟動後累積)`
        : '🐂 大戶散戶動能 (只有台指期／小台／微台與有個股期貨的股票才有委託簿數據，此商品沒有)';
    }

    // 1. 大戶委託口差 (紅柱=偏多掛單較多，綠柱=偏空掛單較多；來源：Books 五檔委買委賣總口數差)
    sub4Series.momentumHist = subChart4.addHistogramSeries({
      priceScaleId: 'right',
      title: ''
    });

    // 2. 散戶成交筆數差 (青綠色；來源：Trades 逐筆成交，買筆數-賣筆數，非口數)
    sub4Series.retailLine = subChart4.addLineSeries({
      color: '#00CEC9',
      lineWidth: 1.5,
      priceScaleId: 'right',
      title: ''
    });

    // 3. 市場委買委賣口差 (黃線；目前與大戶委託口差同源，見後端註解說明限制)
    sub4Series.marketOrderLine = subChart4.addLineSeries({
      color: '#FFEB3B',
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      priceScaleId: 'right',
      title: ''
    });

    // 4. 0 基準水平線
    sub4Series.momentumHist.createPriceLine({
      price: 0,
      color: 'rgba(255, 255, 255, 0.4)',
      lineStyle: LightweightCharts.LineStyle.Dashed,
      lineWidth: 1,
      title: ''
    });

    sub4Series.momentumHist.setData(data.momentumHist);
    sub4Series.retailLine.setData(data.retailLine);
    sub4Series.marketOrderLine.setData(data.marketOrderLine);

    if (isMomentumEligible) startMomentumLivePolling(symbolCode);
  }
}

/**
 * Render Overlays on Main Chart
 */
/**
 * 大戶散戶動能：即時輪詢後端 /api/momentum，把真實的「目前這根 30 分鐘 bar」
 * 附加到圖表最新一個點（lightweight-charts 的 series.update() 對同一個 time 會覆蓋、
 * 對新 time 會新增一筆，正好符合「bar 還在進行中就不斷更新最新值」的需求）。
 * 只有在 Sub-Chart 4 切到 'momentum' 分頁時才會呼叫（見 renderSub4Chart）。
 */
let _momentumRetryAt = 0;  // 連不到本機閘道（如手機）時每 60 秒才試一次，不每 5 秒撞一次
async function fetchAndAppendMomentumBar(symbol) {
  if (Date.now() < _momentumRetryAt) return;
  try {
    const res = await fetch(`${GATEWAY_BASE}/api/momentum?symbol=${encodeURIComponent(symbol)}`, { cache: 'no-store' });
    if (!res.ok) { _momentumRetryAt = Date.now() + 60000; return; }
    const payload = await res.json();
    const bar = payload && payload.bar;
    if (!bar || activeSub4 !== 'momentum') return;

    const t = Math.floor(bar.bar_start_ts);
    const isBull = bar.big_order_diff >= 0;

    if (sub4Series.momentumHist) {
      sub4Series.momentumHist.update({
        time: t,
        value: bar.big_order_diff,
        color: isBull ? 'rgba(255, 71, 87, 0.85)' : 'rgba(46, 213, 115, 0.85)'
      });
    }
    if (sub4Series.retailLine) {
      sub4Series.retailLine.update({ time: t, value: bar.retail_trade_count_diff });
    }
    if (sub4Series.marketOrderLine) {
      sub4Series.marketOrderLine.update({ time: t, value: bar.market_order_diff });
    }

    const badge = document.getElementById('pane-4-badge');
    if (badge && !payload.books_subscribed && !payload.trades_subscribed) {
      badge.innerText = '🐂 大戶散戶動能 (後端尚未連上富邦 Books/Trades — 檢查 live_price_server.py 是否已啟動)';
    }
  } catch (e) {
    _momentumRetryAt = Date.now() + 60000;
    // Gateway server (live_price_server.py) not running locally — fail silently,
    // this is expected whenever the user isn't running it (e.g. this cloud session).
  }
}

// 先讀本機服務存檔的歷史 30 分 bar（重開機不歸零），再接上即時輪詢；只畫服務真正收到過的 bar，缺的時段留白
async function loadMomentumHistory(symbol) {
  try {
    const res = await fetch(`${GATEWAY_BASE}/api/momentum_history?symbol=${encodeURIComponent(symbol)}&days=5`, { cache: 'no-store' });
    if (!res.ok) return;
    const bars = ((await res.json()) || {}).bars || [];
    if (!bars.length || activeSub4 !== 'momentum' || !sub4Series.momentumHist) return;
    sub4Series.momentumHist.setData(bars.map(b => ({
      time: b.t, value: b.big,
      color: b.big >= 0 ? 'rgba(255, 71, 87, 0.85)' : 'rgba(46, 213, 115, 0.85)'
    })));
    if (sub4Series.retailLine) sub4Series.retailLine.setData(bars.map(b => ({ time: b.t, value: b.retail })));
    if (sub4Series.marketOrderLine) sub4Series.marketOrderLine.setData(bars.map(b => ({ time: b.t, value: b.mkt })));
  } catch (e) { /* 本機服務沒開（如手機）：維持原行為，靜默略過 */ }
}

async function startMomentumLivePolling(symbol) {
  stopMomentumLivePolling();
  await loadMomentumHistory(symbol);
  if (activeSub4 !== 'momentum') return;
  stopMomentumLivePolling();   // await 期間可能又被呼叫一次，避免重複計時器
  fetchAndAppendMomentumBar(symbol);
  momentumPollTimer = setInterval(() => fetchAndAppendMomentumBar(symbol), 5000);
}

function stopMomentumLivePolling() {
  if (momentumPollTimer) {
    clearInterval(momentumPollTimer);
    momentumPollTimer = null;
  }
}

/**
 * CVD：即時輪詢後端 /api/cvd，把真實逐筆tick-rule買賣方向累積出來的 {ts,value} 序列
 * 依目前選擇的時間週期（見 CVD_TF_SECONDS）重新分組成K棒，整批 setData() 覆蓋畫面。
 * 每次都整批覆蓋而不是只 update() 最新一筆，是因為session邊界重置、時間週期切換都會讓
 * 「只更新最後一筆」的邏輯出錯，整批覆蓋雖然多耗一點頻寬，但正確性風險低很多。
 * 只有在 Sub-Chart 4 切到 'cvd' 分頁時才會呼叫（見 renderSub4Chart）。
 */
let _cvdRetryAt = 0;  // 連不到本機閘道（如手機）時 60 秒才試一次
async function fetchAndRenderCvd(symbol) {
  if (Date.now() < _cvdRetryAt) return;
  try {
    const res = await fetch(`${GATEWAY_BASE}/api/cvd?symbol=${encodeURIComponent(symbol)}`, { cache: 'no-store' });
    if (!res.ok) { _cvdRetryAt = Date.now() + 60000; return; }
    const payload = await res.json();
    if (activeSub4 !== 'cvd' || !sub4Series.cvd) return;

    const badge = document.getElementById('pane-4-badge');
    const series = payload && payload.series;

    if (!payload.trades_subscribed) {
      sub4Series.cvd.setData([]);
      if (badge) badge.innerText = '🎯 CVD 累積量差 K 線 (後端尚未連上富邦 Trades — 檢查 live_price_server.py 是否已啟動)';
      return;
    }
    if (!series) {
      sub4Series.cvd.setData([]);
      if (badge) badge.innerText = '🎯 CVD 累積量差 K 線 (本次連線後尚未收到真實逐筆成交，等待成交中)';
      return;
    }

    const barSeconds = CVD_TF_SECONDS[currentTf];
    if (!barSeconds) {
      sub4Series.cvd.setData([]);
      if (badge) badge.innerText = '🎯 CVD 累積量差 K 線 (此時間週期尚未支援即時重建，請切換至1分~4小時)';
      return;
    }

    sub4Series.cvd.setData(buildCvdCandlesFromPoints(series.points, barSeconds));
    if (badge) {
      const sessionStartStr = series.session_start_ts
        ? new Date(series.session_start_ts * 1000).toLocaleTimeString('zh-TW', { hour12: false })
        : '?';
      badge.innerText = `🎯 CVD 累積量差 K 線 (真實逐筆成交，自本session ${sessionStartStr} 開始累積，共 ${series.trade_count_in_session} 筆；累積淨口數 ${series.cumulative_delta})`;
    }
  } catch (e) {
    _cvdRetryAt = Date.now() + 60000;
    // Gateway server (live_price_server.py) not running locally — fail silently,
    // this is expected whenever the user isn't running it (e.g. this cloud session).
  }
}

function startCvdLivePolling(symbol) {
  stopCvdLivePolling();
  fetchAndRenderCvd(symbol);
  cvdPollTimer = setInterval(() => fetchAndRenderCvd(symbol), 5000);
}

function stopCvdLivePolling() {
  if (cvdPollTimer) {
    clearInterval(cvdPollTimer);
    cvdPollTimer = null;
  }
}

// 「神奇九轉」勾選框：以前讀了值卻沒用，取消勾選後九轉箭頭仍會畫（2026-10-01 稽核發現）。
function visibleMarkers(data) {
  const all = data.markers || [];
  if (indicatorConfig.demark) return all;
  const demarkKeys = new Set((data.demarkMarkers || []).map(m => `${m.time}|${m.text}`));
  return all.filter(m => !demarkKeys.has(`${m.time}|${m.text}`));
}

function renderMainOverlays(data) {
  // Clear old series
  if (overlaySeries.ribbons.ma7) { mainChart.removeSeries(overlaySeries.ribbons.ma7); overlaySeries.ribbons.ma7 = null; }
  if (overlaySeries.ribbons.ma17) { mainChart.removeSeries(overlaySeries.ribbons.ma17); overlaySeries.ribbons.ma17 = null; }
  if (overlaySeries.ribbons.ma88) { mainChart.removeSeries(overlaySeries.ribbons.ma88); overlaySeries.ribbons.ma88 = null; }
  if (overlaySeries.ribbons.ma200) { mainChart.removeSeries(overlaySeries.ribbons.ma200); overlaySeries.ribbons.ma200 = null; }
  if (overlaySeries.smma) { mainChart.removeSeries(overlaySeries.smma); overlaySeries.smma = null; }
  if (overlaySeries.vwap.vwap) { mainChart.removeSeries(overlaySeries.vwap.vwap); overlaySeries.vwap.vwap = null; }
  if (overlaySeries.vwap.upper1) { mainChart.removeSeries(overlaySeries.vwap.upper1); overlaySeries.vwap.upper1 = null; }
  if (overlaySeries.vwap.lower1) { mainChart.removeSeries(overlaySeries.vwap.lower1); overlaySeries.vwap.lower1 = null; }
  if (overlaySeries.sar) { mainChart.removeSeries(overlaySeries.sar); overlaySeries.sar = null; }
  if (overlaySeries.supertrend.up) { mainChart.removeSeries(overlaySeries.supertrend.up); overlaySeries.supertrend.up = null; }
  if (overlaySeries.supertrend.down) { mainChart.removeSeries(overlaySeries.supertrend.down); overlaySeries.supertrend.down = null; }

  // 1. 尋鳥多空彩帶 (MA7, MA17, MA88, MA200)
  if (indicatorConfig.ribbons) {
    overlaySeries.ribbons.ma7 = mainChart.addLineSeries({ color: indicatorConfig.ma7Color, lineWidth: 1.5, title: '' });
    overlaySeries.ribbons.ma17 = mainChart.addLineSeries({ color: indicatorConfig.ma17Color, lineWidth: 1.5, title: '' });
    overlaySeries.ribbons.ma88 = mainChart.addLineSeries({ color: indicatorConfig.ma88Color, lineWidth: 2, title: '' });
    overlaySeries.ribbons.ma200 = mainChart.addLineSeries({ color: indicatorConfig.ma200Color, lineWidth: 2, title: '' });

    overlaySeries.ribbons.ma7.setData(data.ma7);
    overlaySeries.ribbons.ma17.setData(data.ma17);
    overlaySeries.ribbons.ma88.setData(data.ma88);
    overlaySeries.ribbons.ma200.setData(data.ma200);
  }

  // 2. SMMA 200
  if (indicatorConfig.smma) {
    overlaySeries.smma = mainChart.addLineSeries({
      color: indicatorConfig.smmaColor || '#e84393',
      lineWidth: 2,
      title: ''
    });
    overlaySeries.smma.setData(data.smmaData);
  }

  // 3. VWAP
  if (indicatorConfig.vwap) {
    const vwapColor = indicatorConfig.vwapColor || '#FF8A80';
    overlaySeries.vwap.vwap = mainChart.addLineSeries({ color: vwapColor, lineWidth: 2, title: '' });
    overlaySeries.vwap.upper1 = mainChart.addLineSeries({ color: 'rgba(76, 175, 80, 0.5)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, title: '' });
    overlaySeries.vwap.lower1 = mainChart.addLineSeries({ color: 'rgba(76, 175, 80, 0.5)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, title: '' });

    overlaySeries.vwap.vwap.setData(data.vwapData);
    overlaySeries.vwap.upper1.setData(data.vwapUpper);
    overlaySeries.vwap.lower1.setData(data.vwapLower);
  }

  // 3b. Parabolic SAR（計算在 Worker indicator=chart，這裡只畫）
  if (indicatorConfig.sar) {
    overlaySeries.sar = mainChart.addLineSeries({
      color: '#FFEB3B',
      lineVisible: false,
      pointMarkersVisible: true,
      pointMarkersRadius: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      title: ''
    });
    overlaySeries.sar.setData(data.sarData);
  }

  // 3c. Supertrend（計算在 Worker indicator=chart，這裡只畫）. Rendered
  // as two line series (up-trend segment green, down-trend segment red) since Lightweight
  // Charts v4 has no native per-point line color; each series has `undefined` for bars outside
  // its own trend, which renders as a gap, so together they look like one color-flipping line.
  if (indicatorConfig.supertrend) {
    overlaySeries.supertrend.up = mainChart.addLineSeries({
      color: '#26A69A',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      title: ''
    });
    overlaySeries.supertrend.down = mainChart.addLineSeries({
      color: '#EF5350',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      title: ''
    });
    overlaySeries.supertrend.up.setData(data.supertrendUp);
    overlaySeries.supertrend.down.setData(data.supertrendDown);
  }

  // 4. VRVP (可見範圍成交量分佈圖: POC, VAH, VAL)
  if (indicatorConfig.vrvp && data.vrvpData) {
    drawVrvpHorizontalRays(data.vrvpData);
    renderVrvpCanvasOverlay(data.vrvpData);
  } else {
    clearVrvpRays();
    clearVrvpCanvas();
  }

  // 5. GEX Horizontal Key Lines (嚴格限定僅在台指期/小台/微台顯示)
  const currentSymbolCode = (currentActiveSymbol?.symbol || activeContract || '').toUpperCase();
  const isGexEligible = GEX_SUPPORTED_SYMBOLS.includes(currentSymbolCode);

  if (indicatorConfig.gex && gexData && isGexEligible) {
    drawGexHorizontalRays(data.candles);
  } else {
    clearGexPriceLines();
    // 恢復純粹的 DeMark 與動能鳥標記
    candleSeries.setMarkers(visibleMarkers(data));
  }
}

/**
 * Draw VRVP Key Horizontal Rays (POC: 桃紅實線, VAH/VAL: 亮橘點線)
 */
function drawVrvpHorizontalRays(vrvp) {
  if (!candleSeries || !vrvp) return;
  clearVrvpRays();

  // 1. POC (Point of Control) - 桃紅實線 2px
  priceLines.poc = candleSeries.createPriceLine({
    price: vrvp.poc,
    color: '#E91E63',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Solid,
    axisLabelVisible: true,
    title: ''
  });

  // 2. VAH (Value Area High) - 亮橘點線 1.5px
  priceLines.vah = candleSeries.createPriceLine({
    price: vrvp.vah,
    color: '#FFA726',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: ''
  });

  // 3. VAL (Value Area Low) - 亮橘點線 1.5px
  priceLines.val = candleSeries.createPriceLine({
    price: vrvp.val,
    color: '#FFA726',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: ''
  });
}

function clearVrvpRays() {
  if (priceLines.poc && candleSeries) { candleSeries.removePriceLine(priceLines.poc); priceLines.poc = null; }
  if (priceLines.vah && candleSeries) { candleSeries.removePriceLine(priceLines.vah); priceLines.vah = null; }
  if (priceLines.val && candleSeries) { candleSeries.removePriceLine(priceLines.val); priceLines.val = null; }
}

/**
 * Clear GEX Price Lines & Markers
 */
function clearGexPriceLines() {
  if (priceLines.cw && candleSeries) { candleSeries.removePriceLine(priceLines.cw); priceLines.cw = null; }
  if (priceLines.vex && candleSeries) { candleSeries.removePriceLine(priceLines.vex); priceLines.vex = null; }
  if (priceLines.zg && candleSeries) { candleSeries.removePriceLine(priceLines.zg); priceLines.zg = null; }
  if (priceLines.pw && candleSeries) { candleSeries.removePriceLine(priceLines.pw); priceLines.pw = null; }
  if (priceLines.mp && candleSeries) { candleSeries.removePriceLine(priceLines.mp); priceLines.mp = null; }
  gexLabelDefs = [];
  renderGexLabels();
}

/**
 * Draw GEX Key Defensive Rays (1:1 對齊 TradingView 尋鳥 GEX x VIX 風控原廠配色)
 * 嚴格限定台指期、小台、微台
 */
function drawGexHorizontalRays(candles) {
  if (!candleSeries || !gexData) return;
  clearGexPriceLines();

  const cw = gexData.call_wall_strike || ROOM_CHART_DEFAULTS.call_wall_strike;
  // Math.round(...*10)/10 guards against IEEE754 subtraction artifacts (e.g. 45558.8 - 0.1
  // landing on 45558.699999999997 instead of 45558.7) leaking into the on-chart price label —
  // found 2026-09-16 during a full room.html UI pass: the label was literally showing
  // "VEX Early (45558.700000000004)".
  const vex = Math.round(((gexData.zero_gamma_level || ROOM_CHART_DEFAULTS.zero_gamma_level) - 0.1) * 10) / 10;
  const zg = gexData.zero_gamma_level || ROOM_CHART_DEFAULTS.zero_gamma_level;
  const pw = gexData.put_wall_strike || ROOM_CHART_DEFAULTS.put_wall_strike;
  const mp = gexData.max_pain_strike || ROOM_CHART_DEFAULTS.max_pain_strike;

  // 1. Call Wall (賣權強壓天花板) - 粉紅實線 2px
  priceLines.cw = candleSeries.createPriceLine({
    price: cw,
    color: '#FF76AC',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Solid,
    axisLabelVisible: true
  });

  // 2. VEX Early Flip (VEX 早鳥轉折線) - 亮橘虛線 1.5px
  priceLines.vex = candleSeries.createPriceLine({
    price: vex,
    color: '#FFA726',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    axisLabelVisible: Math.abs(vex - zg) >= 15
  });

  // 3. Zero Gamma (基準多空變盤點) - 亮黃實線 2px
  priceLines.zg = candleSeries.createPriceLine({
    price: zg,
    color: '#FFEB3B',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Solid,
    axisLabelVisible: true
  });

  // 4. Put Wall (買權防守地板牆) - 青綠實線 2px
  priceLines.pw = candleSeries.createPriceLine({
    price: pw,
    color: '#26A69A',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Solid,
    axisLabelVisible: true
  });

  // 5. Max Pain (最大痛點引力) - 亮藍點線 1px
  priceLines.mp = candleSeries.createPriceLine({
    price: mp,
    color: '#42A5F5',
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true
  });



  // 名稱＋數值文字標籤（TV 截圖風格）：畫在 VRVP 籌碼分布圖左側，不壓在籌碼分布上；價位數字仍由右側 Y 軸色塊顯示
  const zgVexClose = Math.abs(vex - zg) < 15;
  gexLabelDefs = [
    { price: mp, color: '#42A5F5', text: `Max Pain: ${mp}` },
    { price: cw, color: '#FF76AC', text: `Call Wall: ${cw}` },
    zgVexClose
      ? { price: zg, color: '#FFEB3B', text: `⚡ ZG / 🟠 VEX: ${zg}` }
      : { price: zg, color: '#FFEB3B', text: `⚡ ZG: ${zg}` },
    { price: pw, color: '#26A69A', text: `Put Wall: ${pw}` }
  ];
  if (!zgVexClose) gexLabelDefs.push({ price: vex, color: '#FFA726', text: `🟠 VEX: ${vex}` });
  renderGexLabels();

  // 6. TV 級即時穿透偵測與標籤 (On-Chart Touch Visual Signals)
  if (candles && candles.length > 0) {
    const combinedMarkers = [];
    let lastSignalT = 0;

    for (let i = 1; i < candles.length; i++) {
      const prevC = candles[i - 1].close;
      const currC = candles[i].close;
      const t = candles[i].time;

      // 突破 Call Wall
      if (prevC <= cw && currC > cw) {
        combinedMarkers.push({ time: t, position: 'aboveBar', color: '#FF76AC', shape: 'arrowUp', text: '📈 Call Wall 突破' });
      }
      // 跌破 VEX 早鳥線
      else if (prevC >= vex && currC < vex) {
        combinedMarkers.push({ time: t, position: 'belowBar', color: '#FFA726', shape: 'arrowDown', text: '🚨 VEX 早鳥轉折' });
      }
      // 跌破 Put Wall
      else if (prevC >= pw && currC < pw) {
        combinedMarkers.push({ time: t, position: 'belowBar', color: '#26A69A', shape: 'arrowDown', text: '📉 Put Wall 跌破' });
      }
    }

    // 合併既有 DeMark 訊號
    candleSeries.setMarkers(combinedMarkers);
  }
}

/**
 * Update Floating Legend on Crosshair Move
 */
// 當日開盤／最高／最低：只用 K 線快取裡的真實分 K，依官方場次切（日盤 08:45～13:45、夜盤 15:00～隔日 05:00；
// 加權／櫃買現貨 09:00～13:30）。K 線快取還沒跟上目前進行中的場次（例如日盤剛開、快取只有昨晚夜盤）、
// 或不在台灣場次的商品（海外）就回傳 null（畫面顯示 —），絕不拿舊場次冒充「當日」。
function tpeSessionAt(t, isFut) {
  const tp = _tpeParts(t);
  const mins = tp.h * 60 + tp.mi;
  const dayStart = isFut ? 8 * 60 + 45 : 9 * 60, dayEnd = isFut ? 13 * 60 + 45 : 13 * 60 + 30;
  // 台北＝UTC+8：「台北當日 00:00」的 UTC 秒數
  const midnightTpe = (y, mo, da) => Date.UTC(y, mo - 1, da) / 1000 - 8 * 3600;
  if (mins >= dayStart && mins <= dayEnd) {
    const start = midnightTpe(tp.y, tp.mo, tp.da) + dayStart * 60;
    return { start, end: start + (dayEnd - dayStart) * 60 + 59, label: '日盤' };
  }
  if (isFut && mins >= 15 * 60) {
    const start = midnightTpe(tp.y, tp.mo, tp.da) + 15 * 3600;
    return { start, end: start + 14 * 3600, label: '夜盤' };
  }
  if (isFut && mins <= 5 * 60) {
    const prev = _tpeParts(t - 86400);
    const start = midnightTpe(prev.y, prev.mo, prev.da) + 15 * 3600;
    return { start, end: start + 14 * 3600, label: '夜盤' };
  }
  return null;   // 場次空檔（例如 05:00～08:45）
}
function sessionOhlcFor(sym) {
  const isFut = ['TXF', 'MTX', 'MXF', 'TMF', 'CDF'].includes(sym), isSpot = sym === 'TAIEX' || sym === 'OTC';
  if (!isFut && !isSpot) return null;
  const tfs = klinesCacheData?.assets?.[sym]?.timeframes;
  if (!tfs) return null;
  const bars = tfs['1M'] || tfs['3M'] || tfs['5M'] || tfs['15M'] || null;
  if (!bars || !bars.length) return null;
  const last = bars[bars.length - 1];
  const sess = tpeSessionAt(last.time, isFut);
  if (!sess) return null;
  // 現在若正在另一個場次進行中（快取還沒有它的 K 棒），不顯示舊場次
  const nowSess = tpeSessionAt(Math.floor(Date.now() / 1000), isFut);
  if (nowSess && nowSess.start !== sess.start) return null;
  const inSess = bars.filter(b => b.time >= sess.start && b.time <= sess.end);
  if (!inSess.length) return null;
  const pad = (n) => String(n).padStart(2, '0');
  const tp = _tpeParts(last.time), sp = _tpeParts(sess.start);
  return {
    open: inSess[0].open,
    high: Math.max(...inSess.map(b => b.high)),
    low: Math.min(...inSess.map(b => b.low)),
    label: `${sess.label} ${pad(sp.mo)}/${pad(sp.da)} 起`,
    lastBar: `${pad(tp.mo)}/${pad(tp.da)} ${pad(tp.h)}:${pad(tp.mi)}`
  };
}

// 最新一根真 K 棒（滑鼠不在圖上時，圖例顯示它，行為同 TradingView；沒有 K 棒就維持 --）
let legendLastCandle = null;
function updateLegendOverlay(param) {
  let candle = null;
  if (param && param.time && param.seriesData) candle = param.seriesData.get(candleSeries);
  else candle = legendLastCandle;
  if (!candle) return;

  const isYield = currentActiveSymbol && currentActiveSymbol.is_yield;
  const _lp = currentActiveSymbol ? realPriceFor(currentActiveSymbol.symbol) : null;
  const isSmall = _lp !== null && _lp < 500;

  const fmt = (v) => isYield ? v.toFixed(3) + '%' : (isSmall ? v.toFixed(2) : v.toLocaleString());

  const lOpen = document.getElementById('leg-open');
  const lHigh = document.getElementById('leg-high');
  const lLow = document.getElementById('leg-low');
  const lClose = document.getElementById('leg-close');
  const lDiff = document.getElementById('leg-diff');

  if (lOpen) lOpen.innerText = fmt(candle.open);
  if (lHigh) lHigh.innerText = fmt(candle.high);
  if (lLow) lLow.innerText = fmt(candle.low);
  if (lClose) lClose.innerText = fmt(candle.close);

  if (lDiff) {
    const diff = candle.close - candle.open;
    const sign = diff >= 0 ? '+' : '';
    const formattedDiff = isYield ? diff.toFixed(3) : (isSmall ? diff.toFixed(2) : (Math.round(diff * 10) / 10).toLocaleString());
    lDiff.innerText = `${sign}${formattedDiff}`;
    lDiff.style.color = diff >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }
}

/**
 * 4. Render Left Panel Quotes, GEX Levels & Macro Risk HUD
 */
// GEX 防線距離（天花板／零 Gamma／地板／最大痛點 vs 目前價格）。
// The GEX levels are TXO strikes in TAIEX/TXF index points, so a distance is only meaningful for the
// index-point family and only when a real price exists; anything else shows "—" (not DXY 98.8 - 48,000).
function refreshGexDistances(baseP, cw, zg, pw, mp) {
  const gexApplicable = baseP !== null && ['TXF', 'MTX', 'MXF', 'TMF', 'TWN', 'TAIEX'].includes(currentActiveSymbol?.symbol || 'TXF');
  const setDist = (id, level, digits) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (!gexApplicable) { el.innerText = '—'; el.style.color = 'var(--text-muted)'; return; }
    const d = baseP - level;
    el.innerText = `${d >= 0 ? '+' : ''}${digits ? d.toFixed(digits) : Math.round(d)} 點`;
    el.style.color = d >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  };
  setDist('left-dist-cw', cw, 0);
  setDist('left-dist-zg', zg, 1);
  setDist('left-dist-pw', pw, 0);
  setDist('left-dist-mp', mp, 0);
}

function renderLeftPanel() {
  if (!gexData) return;

  updateMomentumBirdHud(currentActiveSymbol); // async — fills in real bias/mfi/adx/trend/grade once the API responds

  const isIndexFutures = currentActiveSymbol && ['TXF', 'MXF', 'TMF', 'TWN'].includes(currentActiveSymbol.symbol);
  const baseP = realPriceFor(currentActiveSymbol?.symbol || 'TXF');  // null => shown as '—', never a stale constant
  
  const cw = gexData?.call_wall_strike || ROOM_CHART_DEFAULTS.call_wall_strike;
  const zg = gexData?.zero_gamma_level || ROOM_CHART_DEFAULTS.zero_gamma_level;
  const pw = gexData?.put_wall_strike || ROOM_CHART_DEFAULTS.put_wall_strike;
  const mp = gexData?.max_pain_strike || ROOM_CHART_DEFAULTS.max_pain_strike;

  // 1. Triple indices in left panel
  const topTaiex = document.getElementById('top-val-taiex');
  const topChgTaiex = document.getElementById('top-chg-taiex');
  if (topTaiex) {
    const p = gexData?.spot_price;
    topTaiex.innerText = p ? Number(p).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—';
  }
  if (topChgTaiex) {
    const chg = gexData?.spot_change !== undefined ? gexData.spot_change : 0;
    const pct = gexData?.spot_change_pct !== undefined ? gexData.spot_change_pct : 0;
    const sign = chg >= 0 ? '+' : '';
    topChgTaiex.innerText = `${sign}${chg.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
    topChgTaiex.style.color = chg >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const topOtc = document.getElementById('top-val-otc');
  const topChgOtc = document.getElementById('top-chg-otc');
  if (topOtc) {
    const p = gexData?.two_price;
    topOtc.innerText = p ? Number(p).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—';
  }
  if (topChgOtc) {
    const chg = gexData?.two_change !== undefined ? gexData.two_change : 0;
    const pct = gexData?.two_change_pct !== undefined ? gexData.two_change_pct : 0;
    const sign = chg >= 0 ? '+' : '';
    topChgOtc.innerText = `${sign}${chg.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
    topChgOtc.style.color = chg >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  // 2. Main Selected Symbol Quotes & Change — real values (TAIEX/OTC reuse the same real
  // change/% already computed above for the header pills; TXF/MTX/MXF uses the real
  // night-vs-day session close spread, same figure app.js's txf_shift already shows).
  const lDiffEl = document.getElementById('left-price-diff');
  const lPctEl = document.getElementById('left-price-pct');
  if (lDiffEl && lPctEl) {
    let diff = null, pct = null;
    if (currentActiveSymbol.symbol === 'TXF' || currentActiveSymbol.symbol === 'MTX' || currentActiveSymbol.symbol === 'MXF') {
      const dayTxf = gexData?.day_txf_price;
      const nightTxf = gexData?.night_txf_price;
      if (dayTxf && nightTxf) {
        diff = nightTxf - dayTxf;
        pct = (diff / dayTxf) * 100;
      }
    } else if (currentActiveSymbol.symbol === 'TAIEX') {
      diff = gexData?.spot_change;
      pct = gexData?.spot_change_pct;
    } else if (currentActiveSymbol.symbol === 'OTC') {
      diff = gexData?.two_change;
      pct = gexData?.two_change_pct;
    }
    if (diff !== null && diff !== undefined && pct !== null && pct !== undefined) {
      const sign = diff >= 0 ? '+' : '';
      const color = diff >= 0 ? 'var(--call-color)' : 'var(--put-color)';
      lDiffEl.innerText = `${sign}${diff.toFixed(diff < 100 ? 2 : 0)}`;
      lDiffEl.style.color = color;
      lPctEl.innerText = `(${sign}${pct.toFixed(2)}%)`;
      lPctEl.style.color = color;
    } else {
      lDiffEl.innerText = '—';
      lPctEl.innerText = '(—)';
      lDiffEl.style.color = lPctEl.style.color = 'var(--text-muted)';
    }
  }

  // 3. OHLC stats — 昨收(prev close) is real for all three (derived from real price minus
  // real change, or the other session's real close for TXF). 開盤/最高/最低 have no real
  // intraday source wired up yet (that needs the live tick stream's own running high/low,
  // which lives in live_price_server.py's scope, not touched here) — shown as "—" instead
  // of a frozen number that was never real to begin with.
  const lOpen = document.getElementById('left-open');
  const lHigh = document.getElementById('left-high');
  const lLow = document.getElementById('left-low');
  const lPrev = document.getElementById('left-prev');
  if (lOpen && lHigh && lLow && lPrev) {
    let prevClose = null;
    if (currentActiveSymbol.symbol === 'TXF') {
      prevClose = gexData?.day_txf_price;
    } else if (currentActiveSymbol.symbol === 'TAIEX') {
      if (gexData?.spot_price !== undefined && gexData?.spot_change !== undefined) {
        prevClose = gexData.spot_price - gexData.spot_change;
      }
    } else if (currentActiveSymbol.symbol === 'OTC') {
      if (gexData?.two_price !== undefined && gexData?.two_change !== undefined) {
        prevClose = gexData.two_price - gexData.two_change;
      }
    }
    const sOhlc = sessionOhlcFor(currentActiveSymbol?.symbol);
    const fmtP = (v) => v.toLocaleString(undefined, { minimumFractionDigits: v < 500 ? 2 : 0, maximumFractionDigits: v < 500 ? 2 : 0 });
    lOpen.innerText = sOhlc ? fmtP(sOhlc.open) : '—';
    lHigh.innerText = sOhlc ? fmtP(sOhlc.high) : '—';
    lLow.innerText = sOhlc ? fmtP(sOhlc.low) : '—';
    [lOpen, lHigh, lLow].forEach(el => { el.title = sOhlc ? `${sOhlc.label}（取自 K 線快取，最後一根 ${sOhlc.lastBar}）` : '沒有真實的場次 K 棒資料，不顯示數字'; });
    lPrev.innerText = (prevClose !== null && !isNaN(prevClose)) ? prevClose.toLocaleString(undefined, { minimumFractionDigits: prevClose < 500 ? 2 : 1, maximumFractionDigits: prevClose < 500 ? 2 : 1 }) : '—';
  }

  // Header Title
  const activeTitle = document.getElementById('active-symbol-title');
  if (activeTitle) activeTitle.innerText = `⚡ ${currentActiveSymbol.name} 即時報價 (${currentActiveSymbol.symbol})`;

  // Quotes
  const pEl = document.getElementById('left-main-price');
  if (pEl) {
    pEl.innerText = baseP === null ? '—' : (currentActiveSymbol.is_yield ? `${baseP.toFixed(3)}%` : (baseP < 500 ? baseP.toFixed(2) : baseP.toLocaleString()));
  }

  // Distances（抽成 refreshGexDistances()：即時報價進來時也要用最新價格重算，否則距離停在載入時的舊價）
  refreshGexDistances(baseP, cw, zg, pw, mp);

  // Strike levels themselves (🛡️ GEX 造市商五大防線 card). Found 2026-09-15: this whole card
  // was permanently frozen at whatever numbers were typed into room.html's initial markup —
  // cw/zg/pw/mp above were already real and used for the *distance* spans right next to these,
  // but nothing ever wrote the real number into the level display itself.
  const vex = gexData?.gex_plus_flip !== undefined ? gexData.gex_plus_flip : zg;
  const sCWEl = document.getElementById('left-strike-cw');
  if (sCWEl) sCWEl.innerText = Math.round(cw).toLocaleString();
  const sVexEl = document.getElementById('left-strike-vex');
  if (sVexEl) sVexEl.innerText = vex.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const sZGEl = document.getElementById('left-strike-zg');
  if (sZGEl) sZGEl.innerText = zg.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const sPWEl = document.getElementById('left-strike-pw');
  if (sPWEl) sPWEl.innerText = Math.round(pw).toLocaleString();
  const sMPEl = document.getElementById('left-strike-mp');
  if (sMPEl) sMPEl.innerText = Math.round(mp).toLocaleString();

  // 🏛️ 法人籌碼體質 card. Found 2026-09-15: this card had no element ids at all in
  // room.html — pure static placeholder text ("-12,450 口" etc.), never touched by any JS,
  // permanently frozen since the feature was built. Wired to the same real fields already
  // used elsewhere (institutional_sentiment from the futures-institutional-OI fetch, real
  // pc_ratio, and today's real margin-maintenance estimate from history_10_sessions).
  const instSent = gexData?.institutional_sentiment;
  const instTagEl = document.getElementById('left-inst-tag');
  if (instTagEl) instTagEl.innerText = instSent?.tag || '—';
  const instForeignEl = document.getElementById('left-inst-foreign');
  if (instForeignEl && instSent?.foreign_net_oi !== undefined) {
    const v = instSent.foreign_net_oi;
    const chgNote = instSent.daily_change >= 0 ? '回補' : '加碼放空';
    instForeignEl.innerText = `${v >= 0 ? '+' : ''}${v.toLocaleString()} 口 (${chgNote})`;
    instForeignEl.style.color = v >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }
  const instPcEl = document.getElementById('left-inst-pcratio');
  if (instPcEl && gexData?.pc_ratio !== undefined) {
    const pcv = gexData.pc_ratio;
    instPcEl.innerText = `${pcv.toFixed(1)}% ${pcv > 105 ? '🔴 偏多看撐' : '🟢 偏空看壓'}`;
  }
  const instMarginEl = document.getElementById('left-inst-margin');
  const t0Session = (gexData?.history_10_sessions || []).find(s => s.id === 't0_night' || s.id === 't0_day');
  if (instMarginEl) {
    const mm = t0Session?.margin_maint_market;
    instMarginEl.innerText = (mm == null) ? '—' : `${mm.toFixed(1)}% ${mm >= 150 ? '🟢 安定' : (mm >= 140 ? '🟡 常態' : '🟠 警戒')}`;
  }

  // Header quick pills
  const topZG = document.getElementById('top-stat-zg');
  const topCW = document.getElementById('top-stat-cw');
  const topPW = document.getElementById('top-stat-pw');
  const topMP = document.getElementById('top-stat-mp');
  const topVIX = document.getElementById('top-stat-vix');

  if (topZG) topZG.innerText = zg.toLocaleString();
  if (topCW) topCW.innerText = cw.toLocaleString();
  if (topPW) topPW.innerText = pw.toLocaleString();
  if (topMP) topMP.innerText = mp.toLocaleString();
  if (topVIX) {
    const vixVal = gexData.vix_info ? gexData.vix_info.taifex_vix : null;  // no stand-in number when missing
    topVIX.innerText = (typeof vixVal === 'number') ? `${vixVal} ${vixVal >= 22 ? '🔴' : (vixVal >= 18 ? '🟠' : '🟢')}` : '—';
  }
  const topVVIX = document.getElementById('top-stat-vvix');
  if (topVVIX) {
    const vvixVal = gexData.vix_info ? gexData.vix_info.us_vvix : null;
    if (typeof vvixVal === 'number') {
      const badge = vvixVal >= 110 ? '🔴' : (vvixVal >= 100 ? '🟠' : (vvixVal >= 95 ? '🟡' : '🟢'));
      topVVIX.innerText = `${vvixVal.toFixed(2)} ${badge}`;
    } else {
      topVVIX.innerText = '—';
    }
  }

  // Update Left Macro Risk HUD. Path bug fixed 2026-09-15: macro_risk_dashboard is nested
  // under macro_events_radar in the real payload (see generate_gex_payload()'s
  // "macro_events_radar": macro_events_data), not at the top level — this HUD had silently
  // shown its own hardcoded fallback literals forever since gexData.macro_risk_dashboard was
  // always undefined.
  updateMacroRiskHUD(gexData.macro_events_radar?.macro_risk_dashboard || null);
}

/**
 * Update Left Macro Risk HUD (DXY, US10Y, VIX, VVIX)
 */
function updateMacroRiskHUD(macroData, liveTick) {
  const dxyValEl = document.getElementById('risk-val-dxy');
  const dxyBadgeEl = document.getElementById('risk-badge-dxy');
  const us10yValEl = document.getElementById('risk-val-us10y');
  const us10yBadgeEl = document.getElementById('risk-badge-us10y');
  const vixValEl = document.getElementById('risk-val-vix');
  const vixBadgeEl = document.getElementById('risk-badge-vix');
  const vvixValEl = document.getElementById('risk-val-vvix');
  const vvixBadgeEl = document.getElementById('risk-badge-vvix');
  const overallBadgeEl = document.getElementById('risk-overall-badge');
  const summaryEl = document.getElementById('risk-macro-summary');

  // Real values only (AGENTS.md redline #6): the backend sends null when a quote failed, and there are
  // no stand-in defaults — a missing value renders as "—" / "無數據" instead of an invented number.
  const num = (v) => (typeof v === 'number' && isFinite(v)) ? v : null;
  const dxyPrice = num(liveTick?.dxy) ?? num(macroData?.dxy?.price);
  const us10yPrice = num(liveTick?.us10y) ?? num(macroData?.us10y?.price);
  const vixPrice = num(liveTick?.vix) ?? num(macroData?.vix?.price) ?? num(gexData?.vix_info?.us_vix);
  const vvixPrice = num(liveTick?.vvix) ?? num(gexData?.vix_info?.us_vvix);
  const tailStatus = gexData?.vix_info?.tail_risk_status || '';
  const summary = macroData?.summary || (tailStatus ? `💡 ${tailStatus}` : '💡 總經資料暫時無法取得');

  if (dxyValEl) dxyValEl.textContent = dxyPrice === null ? '—' : dxyPrice.toFixed(3);
  if (dxyBadgeEl) dxyBadgeEl.textContent = dxyPrice === null ? '無數據' : (dxyPrice < 100.5 ? '破20MA(多)' : '站20MA(壓)');

  if (us10yValEl) us10yValEl.textContent = us10yPrice === null ? '—' : `${us10yPrice.toFixed(3)}%`;
  if (us10yBadgeEl) us10yBadgeEl.textContent = us10yPrice === null ? '無數據' : (us10yPrice >= 4.7 ? '站20MA(壓)' : '破20MA(多)');

  if (vixValEl) vixValEl.textContent = vixPrice === null ? '—' : vixPrice.toFixed(2);
  if (vixBadgeEl) vixBadgeEl.textContent = vixPrice === null ? '無數據' : (vixPrice < 20 ? '低波安定' : '恐慌升溫');

  if (vvixValEl) vvixValEl.textContent = vvixPrice === null ? '—' : vvixPrice.toFixed(2);
  if (vvixBadgeEl) {
    if (vvixPrice === null) {
      vvixBadgeEl.textContent = '無數據';
      vvixBadgeEl.style.color = 'var(--text-muted)';
      vvixBadgeEl.style.background = 'rgba(255,255,255,0.06)';
    } else if (vvixPrice >= 110) {
      vvixBadgeEl.textContent = '極端暴衝';
      vvixBadgeEl.style.color = '#ff5252';
      vvixBadgeEl.style.background = 'rgba(255,82,82,0.15)';
    } else if (vvixPrice >= 100) {
      vvixBadgeEl.textContent = '尾部避險潮';
      vvixBadgeEl.style.color = '#ff9100';
      vvixBadgeEl.style.background = 'rgba(255,145,0,0.15)';
    } else if (vvixPrice >= 95) {
      vvixBadgeEl.textContent = '避險升溫';
      vvixBadgeEl.style.color = '#ffd700';
      vvixBadgeEl.style.background = 'rgba(255,215,0,0.15)';
    } else {
      vvixBadgeEl.textContent = '風穩常態';
      vvixBadgeEl.style.color = '#00e676';
      vvixBadgeEl.style.background = 'rgba(0,230,118,0.15)';
    }
  }

  if (summaryEl) summaryEl.textContent = summary.startsWith('💡') ? summary : `💡 ${summary}`;
  if (overallBadgeEl) {
    const isTailRisk = vvixPrice !== null && vvixPrice >= 100;
    const isGood = vixPrice !== null && dxyPrice !== null && vixPrice < 20 && dxyPrice < 102 && !isTailRisk;
    if (vixPrice === null || dxyPrice === null) {
      overallBadgeEl.textContent = '⚪ 資料不足';
      overallBadgeEl.style.color = 'var(--text-muted)';
      overallBadgeEl.style.borderColor = 'var(--text-muted)';
      overallBadgeEl.style.background = 'rgba(255,255,255,0.06)';
    } else if (isTailRisk) {
      overallBadgeEl.textContent = '🟠 尾部避險';
      overallBadgeEl.style.color = '#ff9100';
      overallBadgeEl.style.borderColor = '#ff9100';
      overallBadgeEl.style.background = 'rgba(255,145,0,0.18)';
    } else {
      overallBadgeEl.textContent = isGood ? '🟢 總經偏安' : '🔴 總經避險';
      overallBadgeEl.style.color = isGood ? '#26a69a' : '#ff5252';
      overallBadgeEl.style.borderColor = isGood ? '#26a69a' : '#ff5252';
      overallBadgeEl.style.background = isGood ? 'rgba(38,166,154,0.18)' : 'rgba(255,82,82,0.18)';
    }
  }

  // Micro flash glow animation if live tick triggered
  if (liveTick) {
    [dxyValEl, us10yValEl, vixValEl, vvixValEl].forEach(el => {
      if (el) {
        el.style.transition = 'text-shadow 0.2s ease';
        el.style.textShadow = '0 0 8px rgba(0, 210, 255, 0.8)';
        setTimeout(() => { el.style.textShadow = 'none'; }, 400);
      }
    });
  }
}

/**
 * 5. Event Listeners & Modals
 */
function setupEventListeners() {
  const smcBtn = document.getElementById('smc-toggle-btn');
  if (smcBtn) { smcBtn.classList.toggle('active', smcEnabled); smcBtn.addEventListener('click', toggleSmcOverlay); }

  // Timeframe Buttons (10 TFs)
  const tfBtns = document.querySelectorAll('.btn-tf');
  tfBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      tfBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTf = btn.getAttribute('data-tf');
      renderChartData();
    });
  });

  // Core Preset Assets & Contract Switcher (8 Core Curated Assets)
  const contractBtns = document.querySelectorAll('.contract-tab');
  contractBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      contractBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const code = btn.getAttribute('data-contract');
      
      if (CORE_PRESET_ASSETS[code]) {
        switchActiveSymbol(CORE_PRESET_ASSETS[code]);
      } else {
        const matched = symbolsUniverse.find(s => s.symbol === code || s.futures_code === code);
        if (matched) {
          switchActiveSymbol(matched);
        } else {
          activeContract = code;
          renderChartData();
        }
      }
    });
  });

  // Mobile Drawer Triggers & Controls
  const btnToggleLeftDrawer = document.getElementById('btn-toggle-left-drawer');
  const btnToggleRightDrawer = document.getElementById('btn-toggle-right-drawer');
  const btnCloseLeft = document.getElementById('btn-close-left-drawer');
  const btnCloseRight = document.getElementById('btn-close-right-drawer');
  const overlay = document.getElementById('mobile-drawer-overlay');
  const leftPanel = document.getElementById('panel-left') || document.getElementById('room-left-panel');
  const rightPanel = document.getElementById('panel-right') || document.getElementById('room-right-panel');

  function closeAllDrawers() {
    if (leftPanel) leftPanel.classList.remove('drawer-open');
    if (rightPanel) rightPanel.classList.remove('drawer-open');
    if (overlay) overlay.classList.remove('active');
    setTimeout(handleChartResize, 300);
  }

  if (btnToggleLeftDrawer && leftPanel && overlay) {
    btnToggleLeftDrawer.addEventListener('click', () => {
      const isOpen = leftPanel.classList.contains('drawer-open');
      closeAllDrawers();
      if (!isOpen) {
        leftPanel.classList.add('drawer-open');
        overlay.classList.add('active');
      }
    });
  }

  if (btnToggleRightDrawer && rightPanel && overlay) {
    btnToggleRightDrawer.addEventListener('click', () => {
      const isOpen = rightPanel.classList.contains('drawer-open');
      closeAllDrawers();
      if (!isOpen) {
        rightPanel.classList.add('drawer-open');
        overlay.classList.add('active');
      }
    });
  }

  if (btnCloseLeft) btnCloseLeft.addEventListener('click', closeAllDrawers);
  if (btnCloseRight) btnCloseRight.addEventListener('click', closeAllDrawers);
  if (overlay) overlay.addEventListener('click', closeAllDrawers);

  // Sub-Pane 4 Tab Switcher (AO / CVD / DMI / Momentum)
  const sub4Tabs = document.querySelectorAll('.sub4-tab-btn');
  sub4Tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      sub4Tabs.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeSub4 = btn.getAttribute('data-sub4');
      const momentumPanel = document.getElementById('momentum-panel');
      const tvChart4 = document.getElementById('tv-sub-chart-4');
      if (tvChart4) tvChart4.style.display = '';
      if (momentumPanel) momentumPanel.classList.add('hidden');
      const _symNow = currentActiveSymbol?.symbol || 'TXF';
      const data = (lastChartData && lastChartData._sym === _symNow && lastChartData._tf === currentTf) ? lastChartData : generateIndicatorsData(currentTf);
      renderSub4Chart(data);
    });
  });

  // Momentum Refresh Button
  const momentumRefreshBtn = document.getElementById('momentum-refresh-btn');
  if (momentumRefreshBtn) {
    momentumRefreshBtn.addEventListener('click', () => loadMomentumData(true));
  }

  // Indicator Settings Modal
  const modal = document.getElementById('indicator-settings-modal');
  const openModalBtn = document.getElementById('open-indicator-settings-btn');
  const closeModalBtn = document.getElementById('close-settings-modal-btn');
  const applySettingsBtn = document.getElementById('apply-indicator-settings-btn');

  if (openModalBtn && modal) {
    openModalBtn.addEventListener('click', () => {
      modal.classList.add('show');
    });
  }

  if (closeModalBtn && modal) {
    closeModalBtn.addEventListener('click', () => {
      modal.classList.remove('show');
    });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('show');
    });
  }

  const resetColorsBtn = document.getElementById('btn-reset-ind-colors');
  if (resetColorsBtn) {
    resetColorsBtn.addEventListener('click', () => {
      IND_COLOR_KEYS.forEach(k => { indicatorConfig[k] = IND_COLOR_DEFAULTS[k]; });
      syncColorPickers();
    });
  }

  if (applySettingsBtn && modal) {
    applySettingsBtn.addEventListener('click', () => {
      indicatorConfig.gex = document.getElementById('chk-gex').checked;
      indicatorConfig.ribbons = document.getElementById('chk-ribbons').checked;
      indicatorConfig.demark = document.getElementById('chk-demark').checked;
      indicatorConfig.smma = document.getElementById('chk-smma').checked;
      indicatorConfig.smmaLen = parseInt(document.getElementById('param-smma-len').value) || 200;
      indicatorConfig.smmaColor = document.getElementById('col-smma').value || '#e84393';
      indicatorConfig.supertrend = document.getElementById('chk-supertrend').checked;
      indicatorConfig.vwap = document.getElementById('chk-vwap').checked;
      indicatorConfig.vwapColor = document.getElementById('col-vwap').value || '#FF8A80';
      indicatorConfig.ma7Color = document.getElementById('col-ma7').value || IND_COLOR_DEFAULTS.ma7Color;
      indicatorConfig.ma17Color = document.getElementById('col-ma17').value || IND_COLOR_DEFAULTS.ma17Color;
      indicatorConfig.ma88Color = document.getElementById('col-ma88').value || IND_COLOR_DEFAULTS.ma88Color;
      indicatorConfig.ma200Color = document.getElementById('col-ma200').value || IND_COLOR_DEFAULTS.ma200Color;
      saveIndicatorColors();
      indicatorConfig.vrvp = document.getElementById('chk-vrvp').checked;
      indicatorConfig.vrvpRows = parseInt(document.getElementById('param-vrvp-rows').value) || 50;
      indicatorConfig.vrvpVa = parseInt(document.getElementById('param-vrvp-va').value) || 70;
      indicatorConfig.sar = document.getElementById('chk-sar').checked;
      indicatorConfig.sarStep = parseFloat(document.getElementById('param-sar-step').value) || 0.02;
      indicatorConfig.fvg = document.getElementById('chk-fvg').checked;
      // Supertrend 週期／倍數：欄位一直存在但從沒被讀取（2026-10-01 稽核發現），改了沒有效果
      indicatorConfig.stLen = parseInt(document.getElementById('param-st-len').value) || 10;
      indicatorConfig.stMult = parseFloat(document.getElementById('param-st-mult').value) || 3.0;

      modal.classList.remove('show');
      renderChartData();
    });
  }

  // 🎯 Multi-Factor Quant Screener Modal Trigger
  const screenerModal = document.getElementById('quant-screener-modal');
  const openScreenerBtn = document.getElementById('btn-open-screener');
  const closeScreenerBtn = document.getElementById('close-screener-modal-btn');

  if (openScreenerBtn && screenerModal) {
    openScreenerBtn.addEventListener('click', () => {
      screenerModal.classList.add('show');
    });
  }
  if (closeScreenerBtn && screenerModal) {
    closeScreenerBtn.addEventListener('click', () => {
      screenerModal.classList.remove('show');
    });
  }
  if (screenerModal) {
    screenerModal.addEventListener('click', (e) => {
      if (e.target === screenerModal) screenerModal.classList.remove('show');
    });
  }

  // ◀ ▶ Left & Right Sidebars Smooth Collapse
  const panelLeft = document.getElementById('panel-left');
  const panelRight = document.getElementById('panel-right');
  const btnToggleLeft = document.getElementById('btn-toggle-left-panel');
  const btnCollapseLeft = document.getElementById('btn-collapse-left');
  const btnToggleRight = document.getElementById('btn-toggle-right-panel');
  const btnCollapseRight = document.getElementById('btn-collapse-right');
  const btnDockLeft = document.getElementById('btn-dock-left');
  const btnDockRight = document.getElementById('btn-dock-right');
  const iconLeft = document.getElementById('icon-left-panel');
  const iconRight = document.getElementById('icon-right-panel');

  const toggleLeftPanel = () => {
    leftPanelCollapsed = !leftPanelCollapsed;
    if (panelLeft) panelLeft.classList.toggle('collapsed', leftPanelCollapsed);
    if (btnToggleLeft) btnToggleLeft.classList.toggle('active', !leftPanelCollapsed);
    if (iconLeft) iconLeft.innerText = leftPanelCollapsed ? '▶' : '◀';
    document.body.classList.toggle('left-collapsed', leftPanelCollapsed);
    setTimeout(handleChartResize, 290);
  };

  const toggleRightPanel = () => {
    rightPanelCollapsed = !rightPanelCollapsed;
    if (panelRight) panelRight.classList.toggle('collapsed', rightPanelCollapsed);
    if (btnToggleRight) btnToggleRight.classList.toggle('active', !rightPanelCollapsed);
    if (iconRight) iconRight.innerText = rightPanelCollapsed ? '◀' : '▶';
    document.body.classList.toggle('right-collapsed', rightPanelCollapsed);
    setTimeout(handleChartResize, 290);
  };

  if (btnToggleLeft) btnToggleLeft.addEventListener('click', toggleLeftPanel);
  if (btnCollapseLeft) btnCollapseLeft.addEventListener('click', toggleLeftPanel);
  if (btnDockLeft) btnDockLeft.addEventListener('click', toggleLeftPanel);

  if (btnToggleRight) btnToggleRight.addEventListener('click', toggleRightPanel);
  if (btnCollapseRight) btnCollapseRight.addEventListener('click', toggleRightPanel);
  if (btnDockRight) btnDockRight.addEventListener('click', toggleRightPanel);

  // 🔑 Gemini API Key Configuration Modal (Stored safely in client-side localStorage)
  const geminiModal = document.getElementById('gemini-key-modal');
  const openGeminiBtn = document.getElementById('btn-open-gemini-key');
  const closeGeminiBtn = document.getElementById('close-gemini-key-modal-btn');
  const saveGeminiBtn = document.getElementById('btn-save-gemini-key');
  const clearGeminiBtn = document.getElementById('btn-clear-gemini-key');
  const keyInput = document.getElementById('gemini-api-key-input');

  if (openGeminiBtn && geminiModal) {
    openGeminiBtn.addEventListener('click', () => {
      if (keyInput) keyInput.value = localStorage.getItem('gemini_api_key') || '';
      geminiModal.classList.add('show');
    });
  }

  if (closeGeminiBtn && geminiModal) {
    closeGeminiBtn.addEventListener('click', () => geminiModal.classList.remove('show'));
  }

  if (geminiModal) {
    geminiModal.addEventListener('click', (e) => {
      if (e.target === geminiModal) geminiModal.classList.remove('show');
    });
  }

  if (saveGeminiBtn && keyInput) {
    saveGeminiBtn.addEventListener('click', () => {
      const k = keyInput.value.trim();
      if (k) {
        localStorage.setItem('gemini_api_key', k);
        appendAdvisorMessage('ai', '✅ <strong>Gemini 2.5 API Key 設定成功！</strong> 已解鎖即時多模態視覺與無限制 AI 量化對話。');
      } else {
        localStorage.removeItem('gemini_api_key');
      }
      if (geminiModal) geminiModal.classList.remove('show');
    });
  }

  if (clearGeminiBtn && keyInput) {
    clearGeminiBtn.addEventListener('click', () => {
      localStorage.removeItem('gemini_api_key');
      keyInput.value = '';
      if (geminiModal) geminiModal.classList.remove('show');
      appendAdvisorMessage('ai', 'ℹ️ 已清除 Gemini API Key，恢復為本地內建量化風控引擎。');
    });
  }

  // Keyboard Shortcuts (Alt+1: Toggle Left, Alt+2: Toggle Right, Ctrl+K: Search)
  document.addEventListener('keydown', (e) => {
    if (e.altKey && e.key === '1') {
      e.preventDefault();
      toggleLeftPanel();
    } else if (e.altKey && e.key === '2') {
      e.preventDefault();
      toggleRightPanel();
    }
  });

  // AI Advisor Screenshot Attachment & Paste (Ctrl+V) Handling
  const attachBtn = document.getElementById('advisor-attach-btn');
  const fileInput = document.getElementById('advisor-file-input');
  const previewContainer = document.getElementById('advisor-img-preview-container');
  const previewThumb = document.getElementById('advisor-img-preview-thumb');
  const imgNameEl = document.getElementById('advisor-img-name');
  const removeImgBtn = document.getElementById('advisor-remove-img-btn');

  if (attachBtn && fileInput) {
    attachBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) handleImageAttachment(file);
    });
  }

  if (removeImgBtn) {
    removeImgBtn.addEventListener('click', () => {
      advisorAttachedImage = null;
      if (previewContainer) previewContainer.classList.add('hidden');
      if (fileInput) fileInput.value = '';
    });
  }

  // Paste Screenshot directly in Input box
  const inputEl = document.getElementById('advisor-input');
  if (inputEl) {
    inputEl.addEventListener('paste', (e) => {
      const items = (e.clipboardData || e.originalEvent.clipboardData).items;
      for (const item of items) {
        if (item.type.indexOf('image') !== -1) {
          const file = item.getAsFile();
          handleImageAttachment(file);
          e.preventDefault();
          break;
        }
      }
    });
  }

  function handleImageAttachment(file) {
    const reader = new FileReader();
    reader.onload = (event) => {
      advisorAttachedImage = event.target.result;
      if (previewThumb) previewThumb.src = advisorAttachedImage;
      if (imgNameEl) imgNameEl.innerText = file.name || '盤面截圖.png';
      if (previewContainer) previewContainer.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  }

  // AI Advisor Quick Chips
  const auditChips = document.querySelectorAll('.audit-chip');
  auditChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const action = chip.getAttribute('data-action');
      handleAdvisorAction(action);
    });
  });

  // AI Advisor Send Input
  const sendBtn = document.getElementById('advisor-send-btn');
  if (sendBtn && inputEl) {
    sendBtn.addEventListener('click', () => {
      sendAdvisorQuery(inputEl.value);
      inputEl.value = '';
    });
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        sendAdvisorQuery(inputEl.value);
        inputEl.value = '';
      }
    });
  }
}

/**
 * 6. AI Quant Advisor (尋鳥 AI 量化軍師) Engine
 * Powered by Gemini Pro reasoning + AGENTS.md Highest Wind Control Redlines + Real Position Audit Engine
 */
// 軍師診斷所需的 GEX 欄位。缺任何一個就回報 ok=false，由呼叫端明說「無法診斷」；不再用寫死的舊數字
// （TXF 47187、VVIX 102.66、ROOM_CHART_DEFAULTS…）給實盤建議（AGENTS.md 紅線 4／6）。
function gexAdviceInputs() {
  const g = gexData || {};
  const num = v => (typeof v === 'number' && isFinite(v) && v > 0) ? v : null;
  const vi = g.vix_info || {};
  const o = {
    txf: liveTxfPrice() ?? num(g.txf_price), zg: num(g.zero_gamma_level), cw: num(g.call_wall_strike),
    pw: num(g.put_wall_strike), mp: num(g.max_pain_strike),
    vvix: num(vi.us_vvix) ?? num(vi.vvix), vix: num(vi.taifex_vix)
  };
  o.ok = o.txf !== null && o.zg !== null && o.cw !== null && o.pw !== null && o.mp !== null && !gexIsFallbackNow();
  return o;
}
// 載入失敗、畫面正在用過期預設值時（頂端有紅色橫幅），軍師也不能用它診斷
function gexIsFallbackNow() {
  return !!gexData && gexData.txf_price === ROOM_CHART_DEFAULTS.txf_price && gexData.zero_gamma_level === ROOM_CHART_DEFAULTS.zero_gamma_level;
}
const ADVISOR_NO_DATA_HTML = '<div style="border-left: 3px solid #8b95a5; padding-left: 8px;"><strong>⚪ 目前無法診斷</strong>'
  + '<p style="margin-top:6px; font-size:0.8rem; line-height:1.5;">GEX 資料缺欄位或載入失敗，軍師不會拿舊數字給實盤建議。請稍後重新整理，或到主頁確認資料更新時間。</p></div>';

function initAdvisorFeed() {
  const feed = document.getElementById('advisor-feed');
  if (!feed) return;

  const { txf, zg, cw, pw, mp, ok: gexOk } = gexAdviceInputs();
  if (!gexOk) { feed.innerHTML = ''; appendAdvisorMessage('ai', ADVISOR_NO_DATA_HTML); return; }

  const isPosGamma = txf >= zg;
  const distCW = cw - txf;
  const distPW = txf - pw;

  // Mirrors app.js's live #stat-mp-topology-badge classifier so both surfaces agree.
  // 型態C已移除（死碼+62天真實回測最多只抓到1~2天，見app.js同一段註解）。
  let topologyLabel;
  if (mp > cw) {
    topologyLabel = '🚀 型態 D【極端軋空 / 痛點頂天拓撲】';
  } else if (mp < pw) {
    topologyLabel = '🔴 型態 A【痛點沉底 / 懸空防守拓撲】';
  } else {
    topologyLabel = '🟡 型態 B【對稱健康箱體拓撲】';
  }

  feed.innerHTML = `
    <div class="advisor-msg ai">
      <div class="msg-meta">
        <span class="sender">🤖 尋鳥 AI 量化軍師 (Gemini Pro ✕ AGENTS.md)</span>
        <span class="time">${new Date().toLocaleTimeString()}</span>
      </div>
      <div class="msg-bubble">
        <h4 style="color: var(--primary-accent); margin-bottom: 6px; font-size: 0.88rem;">🦅 戰情室即時全域量化診斷 (v64.17)</h4>
        <p style="font-size: 0.8rem; line-height: 1.55; margin-bottom: 6px;">
          🔹 <strong>當前空間拓撲</strong>：${topologyLabel}<br>
          ⚡ <strong>GEX 狀態</strong>：台指期 (<strong>${txf}</strong>) 位於 Zero Gamma (<strong>${zg}</strong>) ${isPosGamma ? '上方，做市商正 Gamma 具備<span style="color:#26a69a;">減震收斂效應</span>' : '下方，處於負 Gamma <span style="color:#ff5252;">助漲助跌擴張區</span>'}。<br>
          ・<strong>上檔天花板 (Call Wall)</strong>：<code>${cw}</code> (距目前 <strong>+${distCW} 點</strong>)<br>
          ・<strong>下檔防守線 (Put Wall)</strong>：<code>${pw}</code> (距目前 <strong>-${distPW} 點</strong>)<br>
          ・<strong>結算最大痛點 (Max Pain)</strong>：<code>${mp}</code>
        </p>
        <div class="topology-banner" style="margin-top: 6px;">
          🛡️ <strong>軍師即時風控提醒 (AGENTS.md 鐵律)</strong>：<br>
          1. <strong>嚴禁對週選價差單拆單 (No Legging Out)</strong>，避免解鎖無限風險引發多空雙巴。<br>
          2. <strong>盤中暴衝急拉/急殺時嚴禁追價</strong>，請等待 15M/30M DeMark 9★ 竭盡過濾。<br>
          3. 支援<strong>直接輸入持倉部位 (如: <code>W2 47000 SP / 46900 BP</code>)</strong>，我會立即為您進行真金白銀部位體檢與連續洗價單試算！
        </div>
      </div>
    </div>
  `;
}

/**
 * Handle Advisor Quick Action Chips
 */
function handleAdvisorAction(action) {
  const feed = document.getElementById('advisor-feed');
  if (!feed) return;

  const { txf, zg, cw, pw, mp, ok: gexOk } = gexAdviceInputs();
  if (!gexOk) { appendAdvisorMessage('ai', ADVISOR_NO_DATA_HTML); return; }

  let title = '';
  let content = '';

  if (action === 'topology') {
    title = '⚡ 空間拓撲與做市商 Gamma 深度體檢報告';
    content = `
      1. <strong>空間結構</strong>：指數 (${txf}) 位於 Zero Gamma (${zg}) 之上，做市商處於正 Gamma 避險狀態（低買高賣），大盤具有強烈向均值回歸的粘滯性。<br>
      2. <strong>雙向防禦邊界</strong>：
         - 上檔天花板以 <strong>Call Wall ${cw}</strong> 為極限壓力區（做市商大量賣出 Call 避險買盤在此竭盡）。<br>
         - 下檔地板以 <strong>Put Wall ${pw}</strong> 為強烈支撐牆（做市商賣出 Put 避險回補買盤集結）。<br>
      3. <strong>最佳策略</strong>：適合採取 <strong>週選鐵兀鷹 (Iron Condor)</strong> 或 <strong>雙向賣出垂直價差單</strong>，收斂週選時間價值 (Theta Decay)。
    `;
  } else if (action === 'audit') {
    title = '🛡️ 真實持倉部位風控體檢規範 (AGENTS.md 嚴格執行)';
    content = `
      1. <strong>賣腳 (Sell Leg) 安全邊際</strong>：距市價目前約 <strong>${Math.abs(txf - pw)} 點</strong>，處於價外 (OTM) 安全防守走廊。<br>
      2. <strong>風控紅線 1 - 嚴禁拆單 (No Legging Out)</strong>：
         - 週選垂直價差單 (Vertical Spread) <strong>絕不可單獨平倉獲利的賣腳而留下買腳裸露</strong>，此舉會將已鎖定的有限風險瞬間解鎖為無限/極大風險！<br>
      3. <strong>風控紅線 2 - 暴衝暫停追價</strong>：
         - 盤中急拉或急殺超過 300 點時，嚴禁手動追價追空，應先暫停逆勢洗價，等待 15M K 線走平或 DeMark 9★ 出現。
    `;
  } else if (action === 'condor') {
    const ucSell = cw;
    const ucBuy = cw + 100;
    const dpSell = pw;
    const dpBuy = pw - 100;
    title = '🦅 本週週選鐵兀鷹 (Iron Condor) 量化推薦點位';
    content = `
      ・<strong>上翼 (Bear Call Spread 熊市看跌價差)</strong>：
        - 賣出 <strong>${ucSell} Call</strong> + 買進 <strong>${ucBuy} Call</strong> (鎖定 Call Wall 阻力，避開上檔被軋風險)<br>
      ・<strong>下翼 (Bull Put Spread 牛市看跌價差)</strong>：
        - 賣出 <strong>${dpSell} Put</strong> + 買進 <strong>${dpBuy} Put</strong> (鎖定 Put Wall 支撐，享有下檔有限風險)<br>
      ・<strong>獲利安全走廊</strong>：<strong>${dpSell} ～ ${ucSell}</strong> (寬達 ${ucSell - dpSell} 點震盪獲利區間)<br>
      ・<strong>防守鐵律</strong>：只要指數未突破兩側防線，整組持有至週三 13:30 結算享受 100% 權利金歸零收益。
    `;
  } else if (action === 'ioc') {
    const triggerStop = pw - 30;
    title = '🎯 券商連續洗價單實盤設定規範 (IOC 雙腳同退)';
    content = `
      ・<strong>連續洗價觸發條件</strong>：
        - 當台指期即時市價 <strong>貫穿/跌破 ${triggerStop} 點</strong> 或 <strong>整組價差平倉成本觸及 50 點 (虧損達停損門檻)</strong>。<br>
      ・<strong>下單委託類型</strong>：<strong>IOC (Immediate-or-Cancel) 市價/對手價</strong>。<br>
      ・<strong>執行指令</strong>：<strong>整組價差單雙腳一次送出平倉</strong> (買回賣腳 + 賣出買腳)。<br>
      ・<strong>防呆保護</strong>：嚴禁手動單腳平倉，確保保證金立即釋放，100% 規避系統性黑天鵝風險。
    `;
  }

  appendAdvisorMessage('ai', `<strong>${title}</strong><p style="margin-top:6px; font-size:0.8rem; line-height:1.5;">${content}</p>`);
}

/**
 * Send and Process Free-Form User Query to AI Advisor
 */
async function sendAdvisorQuery(query) {
  if ((!query || !query.trim()) && !advisorAttachedImage) return;
  const cleanQ = (query || '').trim();

  // 1. Render User Message (with Image if attached)
  let userMsgHtml = escapeHtml(cleanQ);
  const attachedImgSrc = advisorAttachedImage;
  if (attachedImgSrc) {
    userMsgHtml = `
      <div style="margin-bottom: 6px;">
        <img src="${attachedImgSrc}" alt="截圖" style="max-width: 100%; max-height: 180px; border-radius: 6px; border: 1px solid var(--primary-accent); display: block; margin-bottom: 4px;">
      </div>
      <div>${escapeHtml(cleanQ) || '📷 [已傳送盤面/持倉截圖，請軍師診斷]'}</div>
    `;
  }
  appendAdvisorMessage('user', userMsgHtml);

  // Clear attached image
  advisorAttachedImage = null;
  const previewContainer = document.getElementById('advisor-img-preview-container');
  if (previewContainer) previewContainer.classList.add('hidden');
  const fileInput = document.getElementById('advisor-file-input');
  if (fileInput) fileInput.value = '';

  const apiKey = localStorage.getItem('gemini_api_key');

  if (apiKey) {
    const loadingId = 'ai-loading-' + Date.now();
    appendAdvisorMessage('ai', `<div id="${loadingId}"><span style="color:var(--primary-accent);">⚡ 正在連線 Gemini 2.5 Flash 進行即時盤面多模態診斷中...</span></div>`);
    
    try {
      const geminiReply = await callGeminiApi(apiKey, cleanQ, attachedImgSrc);
      const loadingEl = document.getElementById(loadingId);
      if (loadingEl) {
        loadingEl.parentElement.innerHTML = formatGeminiMarkdown(geminiReply);
      }
    } catch (err) {
      const loadingEl = document.getElementById(loadingId);
      const fallbackHtml = generateQuantAdvisorResponse(cleanQ, !!attachedImgSrc);
      if (loadingEl) {
        loadingEl.parentElement.innerHTML = `
          <div style="color: #ff9800; font-size: 0.76rem; margin-bottom: 6px;">⚠️ Gemini API 連線失敗 (${err.message})，自動切換至本地量化引擎：</div>
          ${fallbackHtml}
        `;
      }
    }
  } else {
    setTimeout(() => {
      let responseHtml = generateQuantAdvisorResponse(cleanQ, !!attachedImgSrc);
      responseHtml += `
        <div style="margin-top: 8px; padding: 6px 8px; background: rgba(255, 215, 0, 0.08); border-radius: 4px; border: 1px dashed var(--gold-accent); font-size: 0.72rem; display: flex; justify-content: space-between; align-items: center;">
          <span>💡 尚未配置 Gemini API Key，目前使用本地內建風控引擎</span>
          <button onclick="document.getElementById('btn-open-gemini-key').click()" style="background: var(--gold-accent); color: #080c14; border: none; border-radius: 3px; padding: 2px 6px; font-weight: 700; cursor: pointer;">🔑 配置 Key</button>
        </div>
      `;
      appendAdvisorMessage('ai', responseHtml);
    }, 350);
  }
}

/**
 * Call Google Gemini 2.5 Multi-Modal REST API
 */
async function callGeminiApi(apiKey, query, base64Image) {
  const currentPrice = realPriceFor(currentActiveSymbol?.symbol || 'TXF') ?? gexData?.txf_price ?? null;
  const _g = gexAdviceInputs();
  const cw = _g.ok ? _g.cw : '無資料';
  const zg = _g.ok ? _g.zg : '無資料';
  const pw = _g.ok ? _g.pw : '無資料';
  const mp = _g.ok ? _g.mp : '無資料';
  const vix = gexData?.vix_info?.taifex_vix ?? '無資料';
  const vvix = gexData?.vix_info?.us_vvix ?? '無資料';
  // 只用真實 K 線快取的最新收盤；沒有就明說無資料，不再寫死數字（AGENTS.md 紅線 6）。
  const dxyReal = realPriceFor('DXY');
  const us10yReal = realPriceFor('US10Y');
  const dxy = dxyReal === null ? '無資料' : dxyReal;
  const us10y = us10yReal === null ? '無資料' : us10yReal;

  const systemInstruction = `你是「尋鳥戰情交易室 AI 量化軍師 (Bird Quant Advisor)」，結合老墨 XQ 指標體系與 TXO GEX 造市商對沖模型。
最高風控鐵律與行為準則 (AGENTS.md)：
1. 嚴禁對週選擇權 (W1/W2/W4/W5/F1) 垂直價差單建議「拆單 (No Legging Out)」，必須維持整組價差單平倉或轉倉。
2. 盤中價格暴衝/急殺時嚴禁建議追價，等待 15M/30M DeMark 9★ 買賣盤竭盡。
3. 診斷實盤真金白銀部位時，檢查賣腳安全邊際、未實現損益、IOC 洗價點數。
當前即時盤面數據：
- 當前監控商品：${currentActiveSymbol?.name || '台指期'} (${currentActiveSymbol?.symbol || 'TXF'})，即時報價：${currentPrice === null ? '無即時報價' : currentPrice}
- GEX 造市商五大防線：Call Wall: ${cw}, Zero Gamma: ${zg}, Put Wall: ${pw}, Max Pain: ${mp}
- 波動率與宏觀雷達：VIX: ${vix}, VVIX: ${vvix}, DXY: ${dxy}, 美債10Y: ${us10y}${us10yReal === null ? '' : '%'}
請以專業、精準、結構化的繁體中文 Markdown 回覆，重點條列空間拓撲與實戰建議。`;

  const parts = [];
  if (base64Image) {
    const cleanB64 = base64Image.replace(/^data:image\/\w+;base64,/, '');
    parts.push({
      inline_data: {
        mime_type: 'image/png',
        data: cleanB64
      }
    });
  }

  parts.push({
    text: query || '請為我進行盤面走勢診斷與部位風控體檢。'
  });

  const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent';

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
    body: JSON.stringify({
      contents: [{ role: 'user', parts }],
      system_instruction: { parts: [{ text: systemInstruction }] },
      generationConfig: {
        temperature: 0.4,
        maxOutputTokens: 1500
      }
    })
  });

  if (!response.ok) {
    const errJson = await response.json().catch(() => ({}));
    throw new Error(errJson?.error?.message || `API 請求失敗 (${response.status})`);
  }

  const result = await response.json();
  const text = result?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error('Gemini 未回傳有效文字內容');
  return text;
}

// 把外部文字（Gemini 回覆、使用者輸入）當純文字塞進 innerHTML 前先跳脫，避免回覆或截圖內的惡意 HTML 執行，
// 進而讀走存在 localStorage 的 Gemini API Key。
function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function formatGeminiMarkdown(md) {
  if (!md) return '';
  let html = escapeHtml(md)
    .replace(/^### (.*$)/gim, '<h4 style="color:var(--primary-accent); margin:6px 0 3px 0; font-size:0.88rem;">$1</h4>')
    .replace(/^## (.*$)/gim, '<h3 style="color:var(--gold-accent); margin:8px 0 4px 0; font-size:0.95rem;">$1</h3>')
    .replace(/^# (.*$)/gim, '<h2 style="color:#fff; margin:10px 0 6px 0; font-size:1.05rem;">$1</h2>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/`([^`]+)`/gim, '<code style="background:rgba(0,210,255,0.15); color:var(--primary-accent); padding:1px 4px; border-radius:3px;">$1</code>')
    .replace(/^\- (.*$)/gim, '<li style="margin-left:14px; font-size:0.8rem; line-height:1.5;">$1</li>')
    .replace(/\n\n/gim, '<br><br>')
    .replace(/\n/gim, '<br>');
  return `<div style="font-size:0.8rem; line-height:1.55;">${html}</div>`;
}

/**
 * Intelligent AI Quant Reasoning & Position Parsing Engine
 * Powered by Gemini 2.5 Multi-modal Vision + AGENTS.md Highest Wind Control Redlines
 */
function generateQuantAdvisorResponse(query, hasImage = false) {
  const { txf, zg, cw, pw, mp, vvix, vix, ok: gexOk } = gexAdviceInputs();
  if (!gexOk) return ADVISOR_NO_DATA_HTML;

  const qLower = (query || '').toLowerCase();
  let imageBadge = '';
  if (hasImage) {
    imageBadge = `
      <div style="background: rgba(0, 210, 255, 0.12); border-left: 3px solid var(--primary-accent); padding: 5px 8px; border-radius: 4px; margin-bottom: 8px; font-size: 0.76rem;">
        📸 <strong>[Gemini 2.5 盤面/對帳單截圖視覺辨識完成]</strong><br>
        已自動解析您的圖表走勢、DeMark 9★ 轉折標籤與持倉點位。
      </div>
    `;
  }

  // --- 1. Position Parsing Engine (持倉部位體檢與洗價單試算) ---
  const strikeRegex = /\b(\d{4,5})\b/g;
  const strikesFound = (query.match(strikeRegex) || []).map(Number).filter(n => n >= 30000 && n <= 60000);
  
  const hasSp = /sp|sell\s*put|賣put|賣出看跌|看漲垂直/i.test(query);
  const hasBp = /bp|buy\s*put|買put|買進看跌/i.test(query);
  const hasSc = /sc|sell\s*call|賣call|賣出看漲|看跌垂直/i.test(query);
  const hasBc = /bc|buy\s*call|買call|買進看漲/i.test(query);
  const isPositionQuery = (strikesFound.length > 0) && (hasSp || hasBp || hasSc || hasBc || /持倉|部位|體檢|洗價|停損|一口|口|單/i.test(query));

  if (isPositionQuery && strikesFound.length >= 1) {
    let sellStrike = strikesFound[0];
    let buyStrike = strikesFound.length >= 2 ? strikesFound[1] : null;
    let posType = 'Bull Put Spread (賣出看跌垂直價差)';

    if (hasSc || (hasBc && !hasSp)) {
      posType = 'Bear Call Spread (賣出看漲垂直價差)';
      if (buyStrike && sellStrike > buyStrike) {
        // Swap to make sellStrike the lower strike for Call spread
        const tmp = sellStrike; sellStrike = buyStrike; buyStrike = tmp;
      }
    } else {
      // Put Spread: sellStrike typically higher than buyStrike
      if (buyStrike && sellStrike < buyStrike) {
        const tmp = sellStrike; sellStrike = buyStrike; buyStrike = tmp;
      }
    }

    const distToSell = Math.abs(txf - sellStrike);
    const isItm = (posType.includes('Put') && txf < sellStrike) || (posType.includes('Call') && txf > sellStrike);
    // 不再假設「權利金＝價差寬度 × 0.32」這種死套公式（用它算出的最大獲利／最大虧損對真實部位是錯的，違反紅線 4）：
    // 只有使用者自己提供實際成交權利金（例如「收 55 點」「權利金 55」「@55」）才計算風報比與 IOC 平倉成本。
    const safetyLevel = isItm ? '🔴 價內被貫穿 (極高風險)' : `價外，距賣腳 ${distToSell} 點（距離不等於安全，請看剩餘天數與下方 IOC 條件）`;

    const spreadWidth = buyStrike ? Math.abs(sellStrike - buyStrike) : null;
    const creditMatch = query.match(/(?:權利金|收|進場|成交|credit|@)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:點|pt|pts)?/i);
    const netCredit = creditMatch ? parseFloat(creditMatch[1]) : null;
    const validCredit = netCredit !== null && spreadWidth !== null && netCredit > 0 && netCredit < spreadWidth;
    const maxLoss = validCredit ? Math.round((spreadWidth - netCredit) * 100) / 100 : null;
    const rrText = validCredit
      ? `最大獲利 <strong>${netCredit} 點</strong> ($${netCredit * 50} TWD) / 最大風險 <strong>${maxLoss} 點</strong> ($${maxLoss * 50} TWD)（風報比 1 : ${(maxLoss / netCredit).toFixed(1)}）`
      : '<strong>無法計算</strong>：請在問題中附上實際成交權利金（點數），例如「收 55 點」。軍師不會用假設的權利金替真實部位算風報比。';
    const triggerTxf = posType.includes('Put') ? (sellStrike + 20) : (sellStrike - 20);
    const closeCostText = validCredit
      ? `<strong><code>${Math.round(netCredit * 1.8 * 10) / 10} 點</code></strong>（＝收取權利金 ${netCredit} × 1.8，常見經驗值，請依自己的風險承受度調整）`
      : '<strong>請先提供成交權利金</strong>';

    return `
      <div style="border-left: 3px solid #00d2ff; padding-left: 8px;">
        ${imageBadge}
        <h4 style="color: var(--gold-accent); margin-bottom: 4px;">🛡️ 真實持倉部位風控體檢診斷書</h4>
        <p style="font-size: 0.8rem; line-height: 1.5; margin-bottom: 6px;">
          ・<strong>識別部位結構</strong>：<code>${posType}</code><br>
          ・<strong>賣腳履約價 (Sell Leg)</strong>：<strong>${sellStrike}</strong> (距現價：<strong>${distToSell} 點</strong>)<br>
          ${buyStrike ? `・<strong>買腳履約價 (Buy Leg)</strong>：<strong>${buyStrike}</strong> (價差寬度: <strong>${spreadWidth === null ? '—' : spreadWidth + ' 點'}</strong>)<br>` : ''}
          ・<strong>持倉狀態</strong>：<strong>${safetyLevel}</strong><br>
          ・<strong>風報比 (Reward/Risk)</strong>：${rrText}
        </p>

        <div style="background: rgba(255, 71, 87, 0.12); border: 1px solid rgba(255, 71, 87, 0.4); border-radius: 6px; padding: 6px 8px; margin: 6px 0; font-size: 0.78rem;">
          🚨 <strong>AGENTS.md 最高風控鐵律審核</strong>：<br>
          1. <strong>嚴禁拆單 (No Legging Out)</strong>：對週選擇權垂直價差單，<strong>絕不可先平倉賣腳留下買腳</strong>！拆單會解除有限風險保護，引發多空雙巴悲劇。<br>
          2. <strong>維持整組處理</strong>：平倉、轉倉或停損必須整組雙腳同步送出。
        </div>

        <div style="background: rgba(0, 210, 255, 0.08); border: 1px solid rgba(0, 210, 255, 0.25); border-radius: 6px; padding: 6px 8px; font-size: 0.78rem;">
          🎯 <strong>券商連續洗價單實盤設定指南 (IOC)</strong>：<br>
          ・<strong>觸發條件</strong>：當台指期 (TXF) ${posType.includes('Put') ? '跌破' : '漲破'} <strong><code>${triggerTxf} 點</code></strong> 或 價差平倉成本觸及 ${closeCostText}<br>
          ・<strong>委託方式</strong>：<code>IOC (Immediate-or-Cancel) 市價/對手價</code><br>
          ・<strong>執行動作</strong>：雙腳整組同時代出平倉 (買回 ${sellStrike} ${posType.includes('Put') ? 'SP' : 'SC'} ＋ 賣出 ${buyStrike || (sellStrike - 100)} ${posType.includes('Put') ? 'BP' : 'BC'})<br>
          ・<strong>優點</strong>：保證金瞬間釋放，絕不產生單腳裸露風險！
        </div>
      </div>
    `;
  }

  // --- 2. Legging Out / 拆單 Question Handling ---
  if (/拆單|平賣留買|平掉賣腳|單腳|解鎖/i.test(query)) {
    return `
      <div style="border-left: 3px solid #ff4757; padding-left: 8px;">
        <h4 style="color: #ff4757; margin-bottom: 4px;">🚨 嚴禁拆單 (Strictly No Legging Out) — 風控最高紅線</h4>
        <p style="font-size: 0.8rem; line-height: 1.55;">
          <strong>為什麼週選擇權 (DTE < 1~3 天) 嚴禁拆單？</strong><br>
          1. <strong>有限風險解鎖為無限風險</strong>：垂直價差單本質是「用買腳保護賣腳」。若將賣腳 SP/SC 獲利了結、留下買腳 BP/BC，看似鎖定賣腳利潤，實際上是將「有限風險解鎖為大額實值虧損風險」。<br>
          2. <strong>時間價值 (Theta) 劇烈衰退</strong>：週選買腳時間衰退極度劇烈，行情一旦回調震盪，買腳權利金會光速歸零，造成「賣腳賺小錢、買腳賠大錢」的<strong>多空雙巴慘案 (Double Whiplash)</strong>。<br>
          3. <strong>鐵律遵循</strong>：所有週選價差單一律維持整組進出，平倉時請使用<strong>券商 IOC 雙腳同步平倉</strong>！
        </p>
      </div>
    `;
  }

  // --- 3. GEX Mechanics & Volatility Analysis ---
  if (/gex|gamma|zero gamma|call wall|put wall|max pain|vex|造市商|做市商/i.test(query)) {
    const isPos = txf >= zg;
    return `
      <div style="border-left: 3px solid #00d2ff; padding-left: 8px;">
        <h4 style="color: var(--primary-accent); margin-bottom: 4px;">⚡ GEX 做市商 Gamma 拓撲結構詳解</h4>
        <p style="font-size: 0.8rem; line-height: 1.55;">
          ・<strong>當前台指期</strong>：<code>${txf}</code> ｜ <strong>Zero Gamma</strong>：<code>${zg}</code><br>
          ・<strong>正負 Gamma 定位</strong>：當前指數處於 <strong>${isPos ? '正 Gamma 區間 (Positive Gamma)' : '負 Gamma 區間 (Negative Gamma)'}</strong>。<br>
          ${isPos ? '🔹 <strong>正 Gamma 特性</strong>：做市商交易方向為「低買高賣」動態對沖避險，這會形成波動率減震器 (Volatility Dampener)，使盤勢傾向在 Call Wall (${cw}) 與 Put Wall (${pw}) 之間震盪收斂。' : '🔸 <strong>負 Gamma 特性</strong>：做市商交易方向為「追漲殺跌」動態對沖，極易引發市場 Gamma 軋空或加速追殺，盤中波動率將顯著擴張！'}<br><br>
          ・<strong>4 大關鍵防線佈局</strong>：<br>
          1. <strong>Call Wall (${cw})</strong>：上方最強賣壓天花板 (做市商大量 Call 集中履約價)。<br>
          2. <strong>Put Wall (${pw})</strong>：下方最強支撐地板牆 (做市商大量 Put 集中履約價)。<br>
          3. <strong>Max Pain (${mp})</strong>：全市場選擇權買方總虧損最大、賣方獲利最大的結算痛點。
        </p>
      </div>
    `;
  }

  // --- 4. Technical Indicators & Momentum Birds ---
  if (/動能鳥|火箭|藍鳥|demark|九轉|macd|cci|dmi|指標/i.test(query)) {
    return `
      <div style="border-left: 3px solid #ffd700; padding-left: 8px;">
        <h4 style="color: var(--gold-accent); margin-bottom: 4px;">🦅 尋鳥量化指標系統精髓與進出場規則</h4>
        <p style="font-size: 0.8rem; line-height: 1.55;">
          1. <strong>🚀 強火箭 (帶量突破)</strong>：<br>
             - 條件：K 線實體站穩 MA7，MA7 > MA17 多頭排列，主 MACD 快線大於慢線，成交量 > 1.6 倍 VolMA5。<br>
             - 操作：期貨順勢多單進場，或佈局 Bull Put Spread。<br>
          2. <strong>🐦 強藍鳥 (超跌起漲 / 抄底)</strong>：<br>
             - 條件：CCI(20) 跌破 -110 超賣區，伴隨 DeMark 9★ 買盤竭盡或 K 棒止跌紅吞噬。<br>
             - 操作：左側試探建倉，嚴設 Put Wall 停損。<br>
          3. <strong>✨ 神奇九轉 (DeMark 9★ / 13★)</strong>：<br>
             - 綠色 <strong>9★ 抄底</strong>：連續 9 根 K 線收盤價低於前第 4 根收盤價，代表賣盤竭盡，轉折將至。<br>
             - 紅色 <strong>9★ 逃頂</strong>：連續 9 根 K 線收盤價高於前第 4 根收盤價，代表買盤竭盡，宜減碼獲利了結。<br>
          4. <strong>⚡ 雙層 MACD (4 色柱體)</strong>：<br>
             - 🔴 紅柱：多頭加速 ｜ 🔵 藍柱：多頭動能減速或水下提早翻紅預警 ｜ 🟢 綠柱：空頭主跌加速。
        </p>
      </div>
    `;
  }

  // --- 5. General Gemini Reasoning & Quant Advice ---
  return `
    <div style="border-left: 3px solid #38bdf8; padding-left: 8px;">
      ${imageBadge}
      <h4 style="color: #38bdf8; margin-bottom: 4px;">🤖 尋鳥 AI 軍師即時研判與策略建議</h4>
      <p style="font-size: 0.8rem; line-height: 1.55;">
        針對您的提問：「<strong>${escapeHtml(query || '盤面截圖診斷')}</strong>」：<br><br>
        1. <strong>當前宏觀與波動率避險雷達</strong>：<br>
           - 台指期即時價位：<code>${txf}</code> ｜ Zero Gamma 多空分水嶺：<code>${zg}</code><br>
           - 🌪️ <strong>VVIX 尾部避險指標</strong>：${vvix === null ? '<code>無資料</code>' : `<code>${vvix}</code> ${vvix > 105 ? '⚠️ <span style="color:#ff9100;">機構避險情緒升溫，賣方組單應加大買腳保護</span>' : '<span style="color:#8b95a5;">未達 105 避險警戒線</span>'}`}。<br>
           - 台指 VIX：<code>${vix === null ? '無資料' : vix}</code>｜DXY：<code>${realPriceFor('DXY') ?? '無資料'}</code>（K 線快取最新收盤，非即時）。<br><br>
        2. <strong>選擇權與期貨策略部署</strong>：<br>
           - <strong>區間操作首選</strong>：在 <strong>Put Wall (${pw})</strong> 與 <strong>Call Wall (${cw})</strong> 之間採取週選鐵兀鷹 (Iron Condor) 策略收取時間價值。<br>
           - <strong>進出場風控原則</strong>：嚴禁單邊裸賣！嚴禁拆單！若遇盤中暴衝超過 300 點，嚴禁盲目追價，待 15M/30M 出現 DeMark 9★ 或均線走平再行佈局。<br><br>
        💡 <em>提示：您可以直接輸入具體持倉履約價（例如 <code>W2 47000 SP 2口 @ 65, 46900 BP 2口 @ 35</code>）或貼上對帳單截圖，我會即時為您計算 Sell Leg 安全距離、風報比與券商 IOC 洗價單參數！</em>
      </p>
    </div>
  `;
}

/**
 * Append Message Bubble to Advisor Feed
 */
function appendAdvisorMessage(type, contentHtml) {
  const feed = document.getElementById('advisor-feed');
  if (!feed) return;

  const msgEl = document.createElement('div');
  msgEl.className = `advisor-msg ${type}`;
  msgEl.innerHTML = `
    <div class="msg-meta">
      <span class="sender">${type === 'user' ? '交易員 (You)' : '🤖 尋鳥 AI 量化軍師'}</span>
      <span class="time">${new Date().toLocaleTimeString()}</span>
    </div>
    <div class="msg-bubble">${contentHtml}</div>
  `;
  feed.appendChild(msgEl);
  feed.scrollTop = feed.scrollHeight;
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/**
 * GEX 關鍵價名稱標籤：獨立 canvas，文字靠右對齊在 VRVP 最大延伸寬度的左邊，避免與籌碼分布重疊。
 * 價格軸被縮放／拖曳時 y 會變，所以另有輕量輪詢（只在 y 簽名改變時重畫）。
 */
let gexLabelDefs = [];
function renderGexLabels() {
  const container = document.getElementById('main-chart-pane');
  if (!container) return;
  let canvas = document.getElementById('gex-label-canvas');
  if (!canvas) {
    if (!gexLabelDefs.length) return;
    canvas = document.createElement('canvas');
    canvas.id = 'gex-label-canvas';
    canvas.style.cssText = 'position:absolute;top:0;right:0;pointer-events:none;z-index:6;';
    container.style.position = 'relative';
    container.appendChild(canvas);
  }
  const rect = container.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr; canvas.height = rect.height * dpr;
  canvas.style.width = `${rect.width}px`; canvas.style.height = `${rect.height}px`;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!gexLabelDefs.length || !candleSeries) return;
  ctx.scale(dpr, dpr);
  ctx.font = '600 12px "Microsoft JhengHei", "Segoe UI", sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'bottom';
  // 標籤右緣 = VRVP 最大寬度的左邊再留 12px（VRVP 畫在 rect.width - 55 往左 28% 寬）
  const rightEdge = rect.width - 55 - rect.width * 0.28 - 12;
  const usedY = [];
  const sorted = gexLabelDefs.map(d => ({ d, y: candleSeries.priceToCoordinate(d.price) })).filter(o => o.y !== null).sort((a, b) => a.y - b.y);
  for (const o of sorted) {
    let y = o.y - 3;                       // 字底貼在線的上方
    for (const u of usedY) if (Math.abs(y - u) < 14) y = u + 14;   // 兩條線太近時往下錯開，避免文字疊在一起
    usedY.push(y);
    if (y < 10 || y > rect.height - 4) continue;   // 超出可視範圍就不畫
    ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 3;
    ctx.fillStyle = o.d.color;
    ctx.fillText(o.d.text, rightEdge, y);
  }
}
setInterval(() => {
  if (!gexLabelDefs.length || !candleSeries) return;
  const container = document.getElementById('main-chart-pane');
  if (!container) return;
  const r = container.getBoundingClientRect();
  const sig = gexLabelDefs.map(d => { const y = candleSeries.priceToCoordinate(d.price); return y === null ? 'n' : Math.round(y); }).sort((a, b) => a - b).join(',') + ',';
  // 與 renderGexLabels 的簽名格式不同（排序／空值），單純用「是否變動」判斷即可
  if (sig + r.width + 'x' + r.height !== window.__gexLabelPoll) {
    window.__gexLabelPoll = sig + r.width + 'x' + r.height;
    renderGexLabels();
  }
}, 400);

/**
 * 7. VRVP Canvas Overlay (Visible Range Volume Profile: Right 30% Width)
 * Up Vol: 寶藍色 (#2962FF) / Down Vol: 金黃色 (#FFB300) in 70% Value Area
 */
function renderVrvpCanvasOverlay(vrvp) {
  const container = document.getElementById('main-chart-pane');
  if (!container || !vrvp || !vrvp.bins || !candleSeries) return;

  let canvas = document.getElementById('vrvp-overlay-canvas');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'vrvp-overlay-canvas';
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.right = '0';
    canvas.style.height = '100%';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '5';
    container.style.position = 'relative';
    container.appendChild(canvas);
  }

  const rect = container.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.scale(dpr, dpr);

  const maxVol = vrvp.maxBinVol || 1;
  const maxWidth = rect.width * 0.28; // 30% width minus price scale margin
  const rightMargin = 55; // Offset from price scale

  vrvp.bins.forEach(bin => {
    const yTop = candleSeries.priceToCoordinate(bin.priceHigh);
    const yBottom = candleSeries.priceToCoordinate(bin.priceLow);

    if (yTop === null || yBottom === null) return;
    const barY = Math.min(yTop, yBottom);
    const barH = Math.max(1, Math.abs(yBottom - yTop));

    const totalW = (bin.totalVol / maxVol) * maxWidth;
    const upW = bin.totalVol > 0 ? (bin.volUp / bin.totalVol) * totalW : 0;
    const downW = totalW - upW;

    const startX = rect.width - rightMargin - totalW;

    // Up Vol (Buy Volume)
    ctx.fillStyle = bin.inVa ? 'rgba(41, 98, 255, 0.65)' : 'rgba(30, 136, 229, 0.25)';
    ctx.fillRect(startX, barY, upW, barH);

    // Down Vol (Sell Volume)
    ctx.fillStyle = bin.inVa ? 'rgba(255, 179, 0, 0.70)' : 'rgba(212, 172, 13, 0.25)';
    ctx.fillRect(startX + upW, barY, downW, barH);

    // Highlight POC Line Bar
    if (bin.isPoc) {
      ctx.strokeStyle = '#E91E63';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(startX, barY, totalW, barH);
    }
  });
}

function clearVrvpCanvas() {
  const canvas = document.getElementById('vrvp-overlay-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

/**
 * 8. Fubon Neo API & Live Gateway WebSocket/HTTP Live Stream
 * Connects to http://localhost:8000/api/live_price (live_price_server.py)
 *
 * 2026-09-17: this used to be a SECOND definition of initFubonLivePriceStream() (JS silently
 * lets the later one in source order win when a function is declared twice at the same scope)
 * — the one that actually ran was the different implementation further down this file (polling
 * /api/live_tick, updating top-val-... / left-main-price). This copy polled a DIFFERENT endpoint
 * (/api/live_price) into DIFFERENT elements (hud-txf-price/hud-txf-change) that don't even
 * exist in room.html, so it was dead in two ways at once — removed rather than kept as an
 * unreachable duplicate.
 */

/**
 * 9. Global Symbol Search & Autocomplete Engine (Ctrl+K & Enter Key Support)
 */
function initSymbolSearchAndAutocomplete() {
  const searchInput = document.getElementById('symbol-search-input');
  const dropdown = document.getElementById('symbol-search-dropdown');
  if (!searchInput || !dropdown) return;

  let currentMatches = [];
  let focusedIndex = -1;

  // Global Ctrl+K / Cmd+K Shortcut
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });

  // 2026-10-07 全域 Esc：關閉最上層開著的視窗（指標庫、API Key、選股雷達）；搜尋框自己的 Esc 另行處理。
  window.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || e.target === searchInput) return;
    const open = [...document.querySelectorAll('.settings-modal-overlay.show, .screener-modal.show')];
    if (open.length) open[open.length - 1].classList.remove('show');
  });

  function updateHighlight() {
    const items = dropdown.querySelectorAll('.search-result-item');
    items.forEach((item, idx) => {
      if (idx === focusedIndex) {
        item.classList.add('selected');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('selected');
      }
    });
  }

  function executeSearch(query) {
    const q = (query || searchInput.value).trim().toLowerCase();
    if (!q) {
      dropdown.classList.add('hidden');
      dropdown.innerHTML = '';
      currentMatches = [];
      focusedIndex = -1;
      return;
    }

    const universe = (symbolsUniverse && symbolsUniverse.length > 0) ? symbolsUniverse : Object.values(CORE_PRESET_ASSETS);

    currentMatches = universe.filter(item => {
      const symMatch = item.symbol && item.symbol.toLowerCase().includes(q);
      const nameMatch = item.name && item.name.toLowerCase().includes(q);
      const futMatch = item.futures_code && item.futures_code.toLowerCase().includes(q);
      return symMatch || nameMatch || futMatch;
    }).slice(0, 15);

    focusedIndex = -1;

    if (currentMatches.length === 0) {
      dropdown.innerHTML = `<div style="padding: 10px 14px; color: var(--text-muted); font-size: 0.78rem;">未找到相符的商品標的 (按 Enter 嘗試強制加載)</div>`;
      dropdown.classList.remove('hidden');
      return;
    }

    dropdown.innerHTML = currentMatches.map((item, idx) => `
      <div class="search-result-item" data-idx="${idx}">
        <div class="search-item-left">
          <span class="search-item-sym">${item.symbol}</span>
          <span class="search-item-name">${item.name}</span>
        </div>
        <div class="search-item-right">
          <span class="search-tag-market">${item.market || 'TWSE'}</span>
          ${item.has_futures ? `<span class="search-tag-fut">期貨 ${item.futures_code}</span>` : ''}
        </div>
      </div>
    `).join('');

    dropdown.classList.remove('hidden');

    dropdown.querySelectorAll('.search-result-item').forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.getAttribute('data-idx'));
        const targetSym = currentMatches[idx];
        if (targetSym) {
          selectAndApplySymbol(targetSym);
        }
      });
    });
  }

  function selectAndApplySymbol(symObj) {
    if (!symObj) return;
    switchActiveSymbol(symObj);
    dropdown.classList.add('hidden');
    dropdown.innerHTML = '';
    searchInput.value = '';
    currentMatches = [];
    focusedIndex = -1;
    searchInput.blur();
  }

  // Input listener
  searchInput.addEventListener('input', () => {
    executeSearch(searchInput.value);
  });

  // Focus listener
  searchInput.addEventListener('focus', () => {
    if (searchInput.value.trim()) {
      executeSearch(searchInput.value);
    }
  });

  // Keyboard navigation & Enter key submission
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (currentMatches.length > 0) {
        focusedIndex = (focusedIndex + 1) % currentMatches.length;
        updateHighlight();
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (currentMatches.length > 0) {
        focusedIndex = (focusedIndex - 1 + currentMatches.length) % currentMatches.length;
        updateHighlight();
      }
    } else if (e.key === 'Escape') {
      dropdown.classList.add('hidden');
      focusedIndex = -1;
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const rawQ = searchInput.value.trim();
      if (!rawQ) return;

      if (focusedIndex >= 0 && focusedIndex < currentMatches.length) {
        selectAndApplySymbol(currentMatches[focusedIndex]);
      } else if (currentMatches.length > 0) {
        selectAndApplySymbol(currentMatches[0]);
      } else {
        // Direct resolution for typed stock / future code (e.g. 2330, 2454, TXF, TAIEX, 台積電)
        const qUpper = rawQ.toUpperCase();
        const universe = (symbolsUniverse && symbolsUniverse.length > 0) ? symbolsUniverse : Object.values(CORE_PRESET_ASSETS);
        let found = universe.find(s => s.symbol.toUpperCase() === qUpper || s.name.toUpperCase() === qUpper || (s.futures_code && s.futures_code.toUpperCase() === qUpper))
                 || CORE_PRESET_ASSETS[qUpper];

        if (!found) {
          // Dynamic fallback for any valid stock symbol
          const stockNames = { '2330': '台積電', '2454': '聯發科', '2317': '鴻海', '2382': '廣達', '2603': '長榮', '0050': '元大台灣50' };
          found = {
            symbol: qUpper,
            name: stockNames[qUpper] || `個股 ${qUpper}`,
            category: '台灣個股',
            market: 'TWSE',
            has_futures: true,
            futures_code: qUpper,
            base_price: null
          };
        }
        selectAndApplySymbol(found);
      }
    }
  });

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
      focusedIndex = -1;
    }
  });
}

/**
 * 10. Switch Active Symbol & Reconfigure Engine (AI Router, HUD, Indicators)
 */
function switchActiveSymbol(symObj) {
  if (!symObj) return;
  console.log(`🔄 Switching active symbol to: ${symObj.name} (${symObj.symbol})`);
  
  currentActiveSymbol = symObj;
  activeContract = symObj.symbol;

  // Toggle GEX lines only for Index Futures
  // 與 GEX_SUPPORTED_SYMBOLS 同一份清單（2026-10-06：原清單漏了 MTX＝微台分頁，切過去 GEX 會被關掉）
  const isIndexFutures = GEX_SUPPORTED_SYMBOLS.includes(symObj.symbol);
  indicatorConfig.gex = isIndexFutures;

  // Update Left HUD & Header
  renderLeftPanel();

  // Highlight contract tab if matches
  const contractBtns = document.querySelectorAll('.contract-tab');
  contractBtns.forEach(btn => {
    const code = btn.getAttribute('data-contract');
    // 只比對代號本身：個股 2330 不該讓「台積期 CDF」分頁亮起（2026-10-07 實測）
    if (code === symObj.symbol) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // 個股（不在 klines_cache 的 12 檔內）沒有分K：停在分K週期會是一片空白，自動切到日K
  if (!klinesCacheData?.assets?.[symObj.symbol] && !['1D', '1W', '1Mth'].includes(currentTf)) {
    const _btn = document.querySelector('.btn-tf[data-tf="1D"]');
    if (_btn) { _btn.click(); resetPriceAutoScale(); return; }   // 按鈕會自己重畫圖表
  }
  // Re-generate and render charts
  renderChartData();
  // 換商品時價格範圍差很多（4 萬點 vs 50 元），把使用者手動拖過的 Y 軸重設回自動縮放
  resetPriceAutoScale();
}

/**
 * 11. Multi-Factor Quant Screener Modal & Engine
 */
function initQuantScreenerModal() {
  const modal = document.getElementById('screener-modal');
  const openBtn = document.getElementById('btn-open-screener');
  const closeBtn = document.getElementById('btn-close-screener');
  const scanBtn = document.getElementById('btn-run-screener-scan');
  const resetBtn = document.getElementById('btn-reset-screener-filters');
  const presetBtns = document.querySelectorAll('.preset-chip');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('show');
      runBirdQuantScreener();
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener('click', () => modal.classList.remove('show'));
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('show');
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      document.querySelectorAll('.screener-filter-deck input[type="checkbox"]').forEach(cb => cb.checked = false);
      document.getElementById('sc-rocket-s').checked = true;
      document.getElementById('sc-grade-s').checked = true;
      runBirdQuantScreener();
    });
  }

  if (scanBtn) {
    scanBtn.addEventListener('click', () => {
      runBirdQuantScreener();
    });
  }

  // Presets
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const p = btn.getAttribute('data-preset');
      document.querySelectorAll('.screener-filter-deck input[type="checkbox"]').forEach(cb => cb.checked = false);
      
      if (p === 'rocket_s') {
        document.getElementById('sc-rocket-s').checked = true;
        document.getElementById('sc-grade-s').checked = true;
      } else if (p === 'it_adopt') {
        document.getElementById('sc-it-adopt').checked = true;
        document.getElementById('sc-grade-a').checked = true;
      } else if (p === 'bird_bottom') {
        document.getElementById('sc-bird-s').checked = true;
        document.getElementById('sc-demark-turn').checked = true;
      } else if (p === 'restart_turbo') {
        document.getElementById('sc-restart-s').checked = true;
        document.getElementById('sc-5k-break').checked = true;
      } else if (p === 'macd_flip') {
        document.getElementById('sc-macd-flip').checked = true;
        document.getElementById('sc-vol-spike').checked = true;
      }
      runBirdQuantScreener();
    });
  });
}

function runBirdQuantScreener() {
  const tbody = document.getElementById('screener-results-tbody');
  const countEl = document.getElementById('screener-match-count');
  if (!tbody) return;

  const defaultUniverse = [
    { symbol: '2330', name: '台積電', category: '半導體', market: 'TWSE', has_futures: true, futures_code: 'CDF' },
    { symbol: '2317', name: '鴻海', category: '電子代工', market: 'TWSE', has_futures: true, futures_code: 'DHF' },
    { symbol: '2454', name: '聯發科', category: 'IC設計', market: 'TWSE', has_futures: true, futures_code: 'DVF' },
    { symbol: '2382', name: '廣達', category: 'AI伺服器', market: 'TWSE', has_futures: true, futures_code: 'IJF' },
    { symbol: '2308', name: '台達電', category: '電源綠能', market: 'TWSE', has_futures: true, futures_code: 'DLF' },
    { symbol: '3231', name: '緯創', category: 'AI代工', market: 'TWSE', has_futures: true, futures_code: 'MSF' },
    { symbol: '6669', name: '緯穎', category: '雲端伺服器', market: 'TWSE', has_futures: true, futures_code: 'OVF' },
    { symbol: '2603', name: '長榮', category: '航運', market: 'TWSE', has_futures: true, futures_code: 'CZF' },
    { symbol: '2609', name: '陽明', category: '航運', market: 'TWSE', has_futures: true, futures_code: 'DKF' },
    { symbol: '3008', name: '大立光', category: '光學鏡頭', market: 'TWSE', has_futures: true, futures_code: 'PLF' },
    { symbol: '3037', name: '欣興', category: '載板ABF', market: 'TWSE', has_futures: true, futures_code: 'NSF' },
    { symbol: '3661', name: '世芯-KY', category: 'ASIC設計', market: 'TWSE', has_futures: true, futures_code: 'RHF' },
    { symbol: '3443', name: '創意', category: 'ASIC設計', market: 'TWSE', has_futures: true, futures_code: 'OEF' },
    { symbol: '2881', name: '富邦金', category: '金融金控', market: 'TWSE', has_futures: true, futures_code: 'FAF' },
    { symbol: '2882', name: '國泰金', category: '金融金控', market: 'TWSE', has_futures: true, futures_code: 'FBF' },
    { symbol: '2356', name: '英業達', category: 'AI伺服器', market: 'TWSE', has_futures: true, futures_code: 'IKF' },
    { symbol: '2379', name: '瑞昱', category: '網通晶片', market: 'TWSE', has_futures: true, futures_code: 'RNF' },
    { symbol: '2618', name: '長榮航', category: '航空觀光', market: 'TWSE', has_futures: true, futures_code: 'HSF' },
    { symbol: '2610', name: '華航', category: '航空觀光', market: 'TWSE', has_futures: true, futures_code: 'HPF' },
    { symbol: '1519', name: '華城', category: '重電綠能', market: 'TWSE', has_futures: true, futures_code: 'TFF' },
    { symbol: '1513', name: '中興電', category: '重電綠能', market: 'TWSE', has_futures: true, futures_code: 'STF' },
    { symbol: '8069', name: '元太', category: '電子紙', market: 'TPEx', has_futures: true, futures_code: 'PUF' },
    { symbol: '3293', name: '鈊象', category: '遊戲IP', market: 'TPEx', has_futures: true, futures_code: 'PEF' },
    { symbol: '6488', name: '環球晶', category: '矽晶圓', market: 'TPEx', has_futures: true, futures_code: 'OWF' },
    { symbol: '3131', name: '弘塑', category: 'CoWoS設備', market: 'TPEx', has_futures: true, futures_code: 'PTF' },
    { symbol: '3583', name: '辛耘', category: 'CoWoS設備', market: 'TWSE', has_futures: true, futures_code: 'QFF' },
    { symbol: '0050', name: '元大台灣50', category: 'ETF指數', market: 'TWSE', has_futures: true, futures_code: 'NYF' },
    { symbol: '00631L', name: '元大台灣50正2', category: '槓桿ETF', market: 'TWSE', has_futures: true, futures_code: 'QAF' }
  ];

  if (!symbolsUniverse || symbolsUniverse.length === 0) {
    symbolsUniverse = defaultUniverse;
  }

  tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 20px; color: var(--primary-accent);">⚡ 正在掃描全市場 1,380+ 檔標的量化指標中...</td></tr>`;

  // Read filter checkboxes
  const fRocketS = document.getElementById('sc-rocket-s')?.checked;
  const fBirdS = document.getElementById('sc-bird-s')?.checked;
  const fRestartS = document.getElementById('sc-restart-s')?.checked;
  const fRestartN = document.getElementById('sc-restart-n')?.checked;
  const fRocketW = document.getElementById('sc-rocket-w')?.checked;
  const fBirdN = document.getElementById('sc-bird-n')?.checked;
  const fMacdFlip = document.getElementById('sc-macd-flip')?.checked;
  const fMacdGold = document.getElementById('sc-macd-gold')?.checked;
  const fMacdGrow = document.getElementById('sc-macd-grow')?.checked;
  const fGradeS = document.getElementById('sc-grade-s')?.checked;
  const fGradeA = document.getElementById('sc-grade-a')?.checked;
  const fDemark = document.getElementById('sc-demark-turn')?.checked;
  const f5k = document.getElementById('sc-5k-break')?.checked;
  const fCciExtreme = document.getElementById('sc-cci-extreme')?.checked;
  const fVol = document.getElementById('sc-vol-spike')?.checked;
  const fItAdopt = document.getElementById('sc-it-adopt')?.checked;
  const fChipBull = document.getElementById('sc-chip-bull')?.checked;

  const activeFiltersCount = [fRocketS, fBirdS, fRestartS, fRestartN, fRocketW, fBirdN, fMacdFlip, fMacdGold, fMacdGrow, fGradeS, fGradeA, fDemark, f5k, fCciExtreme, fVol, fItAdopt, fChipBull].filter(Boolean).length;

  setTimeout(() => {
    const results = [];
    // Real per-symbol technical signals from data/screener_cache.json (built by
    // scripts/build_screener_cache.py off real TWSE/TPEx daily OHLCV) — replaces the
    // previous hash-of-ticker-string generator that fabricated every flag below regardless
    // of the actual market. A symbol missing from this cache, or explicitly marked
    // history_unavailable (no real price history TWSE/TPEx would give up), is skipped
    // rather than shown with an invented signal.
    const realScreenerMap = {};
    if (screenerCacheData && Array.isArray(screenerCacheData.symbols)) {
      screenerCacheData.symbols.forEach(s => { realScreenerMap[s.symbol] = s; });
    }

    symbolsUniverse.forEach(item => {
      const real = realScreenerMap[item.symbol];
      if (!real || real.history_unavailable) return; // no real signal to show — don't invent one

      const sigList = real.signals || [];
      const hasRocketS = sigList.includes('🚀 強火箭');
      const hasBirdS = sigList.includes('🐦 強力藍鳥');
      const hasRestartS = sigList.includes('🛸 強力再啟'); // real 動能鳥 is_restart_strong
      const hasRestartN = sigList.includes('⚡ 動能再啟'); // real 動能鳥 is_restart_normal
      const hasRocketW = sigList.includes('✈️ 火箭'); // real 動能鳥 is_weak_rocket; NOT the heuristic '✈️ 噴射機'
      const hasBirdN = sigList.includes('🐣 藍鳥'); // real 動能鳥 is_normal_bird; NOT the heuristic '🥚 帶殼鳥'
      const isMacdFlip = real.macd_state === 'MACD 柱狀體翻紅';
      const isMacdGold = real.macd_state === '零軸上金叉' || real.macd_state === 'MACD 水下金叉';
      // Real dual-layer MACD / swing-CCI signals (scripts/build_screener_cache.py's
      // the screener back end, ported from the user's own Pine) — isMacdGrow/hasCciExtreme replace two checkboxes that existed in
      // this filter panel but were never wired to any real field before.
      const isMacdGrow = !!real.macd_hist_growing;
      const hasCciExtreme = !!real.cci_signal;
      const isGradeS = real.grade === 'S';
      const isGradeA = real.grade === 'A';
      const hasDemark = real.demark_state && real.demark_state !== '無';
      const has5k = real.k5_state === '5K 創高突破';
      const hasVol = (real.volume_status || '').includes('爆量');
      // Real per-stock 投信認養 (trust net-buying 3+ consecutive trading days) / 籌碼偏多
      // (三大法人合計 net-positive on 2+ of the last 3 trading days), from
      // data/stock_institutional_history.json via scripts/build_screener_cache.py's
      // compute_inst_flags() — replaces the previous always-false stub.
      const hasItAdopt = !!real.it_adopted;
      const hasChipBull = !!real.chip_bull;

      let score = 0;
      if (fRocketS && hasRocketS) score++;
      if (fBirdS && hasBirdS) score++;
      if (fRestartS && hasRestartS) score++;
      if (fRestartN && hasRestartN) score++;
      if (fRocketW && hasRocketW) score++;
      if (fBirdN && hasBirdN) score++;
      if (fMacdFlip && isMacdFlip) score++;
      if (fMacdGold && isMacdGold) score++;
      if (fMacdGrow && isMacdGrow) score++;
      if (fGradeS && isGradeS) score++;
      if (fGradeA && isGradeA) score++;
      if (fDemark && hasDemark) score++;
      if (f5k && has5k) score++;
      if (fCciExtreme && hasCciExtreme) score++;
      if (fVol && hasVol) score++;
      if (fItAdopt && hasItAdopt) score++;
      if (fChipBull && hasChipBull) score++;

      // Match criteria: if no filters, show all; otherwise must match majority of selected
      const isMatch = (activeFiltersCount === 0) || (score >= Math.max(1, Math.ceil(activeFiltersCount * 0.4)));

      if (isMatch) {
        const price = real.price;
        const changePct = real.pct_change;

        const sigs = sigList.length ? sigList.slice(0, 2) : ['⚖️ 無明顯訊號'];

        results.push({
          item,
          price,
          changePct,
          signals: sigs.join(' '),
          grade: isGradeS ? 'S 強噴' : (isGradeA ? 'A 強勢' : (real.grade ? `${real.grade} 級` : 'B 多頭')),
          score,
          macdState: real.macd_state,
          cciSignal: real.cci_signal
        });
      }
    });

    // Sort by score descending
    results.sort((a, b) => b.score - a.score || b.changePct - a.changePct);

    if (countEl) countEl.innerText = results.length;

    if (results.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 24px; color: var(--text-muted);">無完全符合所有堆疊條件的標的，建議適度放寬條件篩選。</td></tr>`;
      return;
    }

    tbody.innerHTML = results.slice(0, 50).map(r => {
      const sign = r.changePct >= 0 ? '+' : '';
      const col = r.changePct >= 0 ? 'var(--call-color)' : 'var(--put-color)';
      const gradeClass = r.grade.includes('S') ? 'strength-badge-s' : 'signal-badge-chip';

      // Real dual-layer MACD / swing-CCI state for this cell — previously this column showed a fake
      // "🟢 紅柱擴張" / "🟡 震盪整理" derived purely from today's price direction, unrelated
      // to any MACD/CCI data at all. cci_signal (rarer, more actionable) takes priority over
      // the MACD color state when both are present.
      let macdCell, macdColor;
      if (r.cciSignal) {
        macdCell = r.cciSignal;
        macdColor = r.cciSignal.startsWith('🔴') ? '#ff5252' : '#4fc3f7';
      } else if (r.macdState === '零軸上金叉') {
        macdCell = '🔴 零軸上金叉'; macdColor = '#ff5252';
      } else if (r.macdState === 'MACD 水下金叉') {
        macdCell = '🔵 水下金叉(領先)'; macdColor = '#4fc3f7';
      } else if (r.macdState === 'MACD 柱狀體翻紅') {
        macdCell = '🟠 柱狀翻紅'; macdColor = '#ffb74d';
      } else {
        macdCell = '⚪ 死叉觀望'; macdColor = '#888';
      }

      return `
        <tr>
          <td><strong style="color: var(--primary-accent);">${r.item.symbol}</strong></td>
          <td style="font-weight: 600;">${r.item.name}</td>
          <td><span class="search-tag-market">${r.item.market}・${r.item.category}</span></td>
          <td style="font-weight: 700;">$${r.price.toLocaleString()}</td>
          <td style="color: ${col}; font-weight: 700;">${sign}${r.changePct.toFixed(2)}%</td>
          <td><span class="signal-badge-chip">${r.signals}</span></td>
          <td><span class="${gradeClass}">${r.grade}</span></td>
          <td style="font-size: 0.72rem; color: ${macdColor};">${macdCell}</td>
          <td>
            <button class="btn-load-screener-stock" data-sym="${r.item.symbol}">載入圖表</button>
          </td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.btn-load-screener-stock').forEach(btn => {
      btn.addEventListener('click', () => {
        const sym = btn.getAttribute('data-sym');
        const target = symbolsUniverse.find(s => s.symbol === sym) || defaultUniverse.find(s => s.symbol === sym);
        if (target) {
          switchActiveSymbol(target);
          document.getElementById('screener-modal')?.classList.remove('show');
        }
      });
    });

  }, 120);
}


// ================================================================
// 大戶散戶動能指標 (Big Player vs Retail Momentum)
// 資料來源：台灣期交所 OpenAPI - 三大法人總表 (每日)
// 邏輯：外資/投信/自營 各自的多空淨額口數 = 大戶方向
//       三大法人合計 vs 全市場 = 散戶方向（反推）
// ================================================================

let momentumCache = null; // { date, data, timestamp }

async function loadMomentumData(forceRefresh = false) {
  const loadingEl = document.getElementById('momentum-loading');
  const contentEl = document.getElementById('momentum-content');
  const dateEl = document.getElementById('momentum-date');

  // 若 5 分鐘內已有快取，直接渲染（非強制刷新）
  if (!forceRefresh && momentumCache && (Date.now() - momentumCache.timestamp < 300000)) {
    renderMomentumData(momentumCache.data);
    return;
  }

  if (loadingEl) { loadingEl.style.display = 'flex'; }
  if (contentEl) { contentEl.style.display = 'none'; }

  // 1. Try local momentum_data.json first
  try {
    let localRes = await fetch('../data/momentum_data.json?t=' + Date.now()).catch(() => null);
    if (localRes && localRes.ok) {
      const json = await localRes.json();
      const result = {
        foreign: { tradingNet: json.institutions.foreign.trading_net, oiNet: json.institutions.foreign.oi_net },
        trust: { tradingNet: json.institutions.it.trading_net, oiNet: json.institutions.it.oi_net },
        dealer: { tradingNet: json.institutions.dealer.trading_net, oiNet: json.institutions.dealer.oi_net },
        total: {
          tradingNet: json.institutions.foreign.trading_net + json.institutions.it.trading_net + json.institutions.dealer.trading_net,
          oiNet: json.institutions.foreign.oi_net + json.institutions.it.oi_net + json.institutions.dealer.oi_net
        },
        retail: json.retail,
        history_5d: json.history_5d,
        date: json.date || ''
      };
      momentumCache = { date: result.date, data: result, timestamp: Date.now() };
      if (dateEl) dateEl.textContent = formatMomentumDate(result.date);
      renderMomentumData(result);
      return;
    }
  } catch (e) {
    // Proceed to OpenAPI
  }

  try {
    // 期交所 API 回傳 CSV 格式（非 JSON）
    const generalRes = await fetch('https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersGeneralBytheDate');
    if (!generalRes.ok) throw new Error(`API Error: ${generalRes.status}`);
    
    const csvText = await generalRes.text();
    const generalData = parseMomentumCSV(csvText);

    if (!generalData || generalData.length === 0) {
      throw new Error('期交所 API 未返回資料（可能今日休市）');
    }

    const parsed = parseMajorInstitutionalData(generalData);
    const futData = [];
    const txVolume = getTXVolume(futData);
    const result = { ...parsed, txVolume, date: parsed.date || (generalData[0] ? generalData[0]['日期'] : '') || '--' };
    
    momentumCache = { date: result.date, data: result, timestamp: Date.now() };
    if (dateEl) dateEl.textContent = formatMomentumDate(result.date);
    renderMomentumData(result);

  } catch (err) {
    if (loadingEl) {
      loadingEl.innerHTML = `<span style="color:#EF5350;">❌ ${err.message}</span>`;
    }
    console.error('[Momentum] Error:', err);
  }
}

// CSV 解析器：將期交所 CSV 轉為物件陣列
function parseMomentumCSV(csvText) {
  // 移除 BOM 和空白
  const cleaned = csvText.replace(/^\uFEFF/, '').trim();
  const lines = cleaned.split('\n').map(l => l.trim()).filter(l => l);
  if (lines.length < 2) return [];
  const headers = lines[0].split(',');
  return lines.slice(1).map(line => {
    const vals = line.split(',');
    const obj = {};
    headers.forEach((h, i) => { obj[h.trim()] = (vals[i] || '').trim(); });
    return obj;
  });
}

function parseMajorInstitutionalData(data) {
  // 三大法人身份別識別（期交所 CSV 返回中文欄位）
  // 欄位：身份別、多空交易口數淨額、多空未平倉口數淨額
  const result = {
    foreign:  { tradingNet: 0, oiNet: 0 }, // 外資
    trust:    { tradingNet: 0, oiNet: 0 }, // 投信
    dealer:   { tradingNet: 0, oiNet: 0 }, // 自營
  };

  for (const row of data) {
    const item = (row['身份別'] || row['Item'] || '').trim();
    const tradingNet = parseInt((row['多空交易口數淨額'] || row['TradingVolume(Net)'] || '0').replace(/,/g, '')) || 0;
    const oiNet = parseInt((row['多空未平倉口數淨額'] || row['OpenInterest(Net)'] || '0').replace(/,/g, '')) || 0;

    if (item.includes('外資')) {
      result.foreign.tradingNet += tradingNet;
      result.foreign.oiNet += oiNet;
    } else if (item.includes('投信')) {
      result.trust.tradingNet += tradingNet;
      result.trust.oiNet += oiNet;
    } else if (item.includes('自營')) {
      result.dealer.tradingNet += tradingNet;
      result.dealer.oiNet += oiNet;
    }
  }

  // 合計
  result.total = {
    tradingNet: result.foreign.tradingNet + result.trust.tradingNet + result.dealer.tradingNet,
    oiNet: result.foreign.oiNet + result.trust.oiNet + result.dealer.oiNet
  };

  // 取得日期
  result.date = (data[0] || {})['日期'] || (data[0] || {})['Date'] || '';

  return result;
}

function getTXVolume(futData) {
  if (!Array.isArray(futData)) return 0;
  const tx = futData.find(r => (r['ContractCode'] || r['ProductCode'] || '').includes('TX') && 
                                (r['ContractMonth'] || '').length === 6);
  if (!tx) return 0;
  return parseInt((tx['TradingVolume'] || '0').replace(/,/g, '')) || 0;
}

function renderMomentumData(d) {
  const loadingEl = document.getElementById('momentum-loading');
  const contentEl = document.getElementById('momentum-content');

  if (loadingEl) loadingEl.style.display = 'none';
  if (contentEl) contentEl.style.display = 'flex';
  contentEl.style.flexDirection = 'column';
  contentEl.style.gap = '10px';

  // 計算最大值（用於比例縮放）
  const maxAbs = Math.max(
    Math.abs(d.foreign.tradingNet),
    Math.abs(d.trust.tradingNet),
    Math.abs(d.dealer.tradingNet),
    Math.abs(d.total.tradingNet),
    1
  );

  renderMomentumBar('foreign', d.foreign.tradingNet, maxAbs);
  renderMomentumBar('trust',   d.trust.tradingNet,   maxAbs);
  renderMomentumBar('dealer',  d.dealer.tradingNet,  maxAbs);
  renderMomentumBar('total',   d.total.tradingNet,   maxAbs * 1.5);

  // 未平倉淨額（留倉方向）
  setOiCard('moi-foreign', d.foreign.oiNet);
  setOiCard('moi-trust',   d.trust.oiNet);
  setOiCard('moi-dealer',  d.dealer.oiNet);
  setOiCard('moi-total',   d.total.oiNet);

  // 訊號解讀
  updateMomentumSignal(d);
}

function renderMomentumBar(id, value, maxAbs) {
  const bar = document.getElementById(`mbar-${id}`);
  const val = document.getElementById(`mval-${id}`);
  if (!bar || !val) return;

  const pct = Math.min(Math.abs(value) / maxAbs * 50, 50); // 最多 50% 寬度（中心為 50%）
  bar.className = 'mrow-bar ' + (value > 0 ? 'positive' : value < 0 ? 'negative' : 'zero');
  bar.style.width = value === 0 ? '2px' : `${pct}%`;

  const sign = value > 0 ? '+' : '';
  val.textContent = `${sign}${value.toLocaleString()}`;
  val.style.color = value > 0 ? '#26A69A' : value < 0 ? '#EF5350' : 'var(--text-muted)';
}

function setOiCard(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  const sign = value > 0 ? '+' : '';
  el.textContent = `${sign}${value.toLocaleString()}`;
  el.style.color = value > 0 ? '#26A69A' : value < 0 ? '#EF5350' : 'var(--text-muted)';
}

function updateMomentumSignal(d) {
  const icon = document.getElementById('momentum-signal-icon');
  const text = document.getElementById('momentum-signal-text');
  const signalEl = document.getElementById('momentum-signal');
  if (!icon || !text || !signalEl) return;

  const net = d.total.tradingNet;
  const oiNet = d.total.oiNet;

  let signalIcon, signalText, borderColor;

  if (net > 2000 || (net > 500 && oiNet > 1000)) {
    signalIcon = '🐂';
    signalText = `三大法人強力做多：當日交易淨多 ${net.toLocaleString()} 口，留倉淨多 ${oiNet.toLocaleString()} 口。大戶明顯站多頭。`;
    borderColor = '#26A69A';
  } else if (net < -2000 || (net < -500 && oiNet < -1000)) {
    signalIcon = '🐻';
    signalText = `三大法人強力做空：當日交易淨空 ${Math.abs(net).toLocaleString()} 口，留倉淨空 ${Math.abs(oiNet).toLocaleString()} 口。大戶傾向放空。`;
    borderColor = '#EF5350';
  } else if (Math.abs(net) < 200) {
    signalIcon = '😴';
    signalText = `三大法人觀望：當日交易幾乎中性（${net > 0 ? '+' : ''}${net.toLocaleString()} 口）。市場缺乏方向性資金驅動。`;
    borderColor = '#FFEB3B';
  } else if (net > 0) {
    signalIcon = '📈';
    signalText = `三大法人偏多：當日交易淨多 ${net.toLocaleString()} 口。留倉方向：${oiNet > 0 ? '淨多' : '淨空'} ${Math.abs(oiNet).toLocaleString()} 口。`;
    borderColor = '#26A69A';
  } else {
    signalIcon = '📉';
    signalText = `三大法人偏空：當日交易淨空 ${Math.abs(net).toLocaleString()} 口。留倉方向：${oiNet > 0 ? '淨多' : '淨空'} ${Math.abs(oiNet).toLocaleString()} 口。`;
    borderColor = '#EF5350';
  }

  icon.textContent = signalIcon;
  text.textContent = signalText;
  signalEl.style.borderLeftColor = borderColor;
}

function formatMomentumDate(dateStr) {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  return `${dateStr.slice(0,4)}/${dateStr.slice(4,6)}/${dateStr.slice(6,8)}`;
}

// Global cached screener and real quotes data
let screenerCacheData = null;
let realQuotesData = null;

/**
 * 6. Load Real Quotes & Screener Cache Data
 */
async function loadScreenerAndRealQuotesData() {
  try {
    const [scResp, rqResp] = await Promise.all([
      fetch('../data/screener_cache.json').catch(() => null),
      fetch('../data/tw_quotes_latest.json').catch(() => null)
    ]);

    if (scResp && scResp.ok) {
      screenerCacheData = await scResp.json();
    }
    if (rqResp && rqResp.ok) {
      const parsed = await rqResp.json();
      realQuotesData = parsed.quotes || {};
    }

    renderPointContributionHUD();
  } catch (err) {
    console.warn('[Data Load] Screener cache or real quotes fetch warning:', err);
  }
}

/**
 * 7. Render Top Weighted Index Point Contribution HUD
 */
function renderPointContributionHUD() {
  const container = document.getElementById('point-contribution-list');
  if (!container) return;

  const topWeights = [
    { symbol: '2330', name: '台積電', weightPts: 8.2 },
    { symbol: '2317', name: '鴻海',   weightPts: 0.92 },
    { symbol: '2454', name: '聯發科', weightPts: 0.71 },
    { symbol: '2881', name: '富邦金', weightPts: 0.45 },
    { symbol: '2882', name: '國泰金', weightPts: 0.38 },
    { symbol: '2308', name: '台達電', weightPts: 0.40 },
    { symbol: '2382', name: '廣達',   weightPts: 0.35 },
    { symbol: '1605', name: '華新',   weightPts: 0.12 }
  ];

  let html = '';
  topWeights.forEach(item => {
    const q = (realQuotesData && realQuotesData[item.symbol]) ? realQuotesData[item.symbol] : null;
    const change = q ? (q.change || 0) : (item.symbol === '1605' ? -0.5 : 5.0);
    const price = q ? (q.close || 0) : (item.symbol === '1605' ? 37.90 : 1045);
    const pts = (change * item.weightPts).toFixed(1);
    const isUp = change >= 0;
    const color = isUp ? 'var(--call-color)' : 'var(--put-color)';

    html += `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 3px 6px; background: rgba(255,255,255,0.03); border-radius: 4px; border-left: 2px solid ${color};">
        <div>
          <span style="font-weight: 700; color: var(--text-muted);">${item.symbol}</span>
          <span style="margin-left: 4px; font-weight: 600;">${item.name}</span>
          <span style="font-size: 0.7rem; color: #94a3b8; margin-left: 4px;">$${price}</span>
        </div>
        <div style="text-align: right;">
          <span style="color: ${color}; font-weight: 700;">${isUp ? '+' : ''}${pts} 點</span>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

/**
 * 8. Global Smart Floating Tooltips (Prevents Out-of-Bounds & Truncation)
 */
function initGlobalSmartTooltips() {
  let tooltip = document.getElementById('global-smart-tooltip');
  if (!tooltip) {
    tooltip = document.createElement('div');
    tooltip.id = 'global-smart-tooltip';
    tooltip.style.display = 'none';
    document.body.appendChild(tooltip);
  }

  document.addEventListener('mouseover', (e) => {
    const el = e.target.closest('[data-tooltip]');
    if (!el) return;
    
    const text = el.getAttribute('data-tooltip');
    if (!text) return;
    
    tooltip.innerText = text;
    tooltip.style.display = 'block';
    tooltip.style.opacity = '1';
    
    const rect = el.getBoundingClientRect();
    const pad = 8;
    
    let left = rect.left + (rect.width / 2) - 130;
    let top = rect.bottom + pad;
    
    const ttRect = tooltip.getBoundingClientRect();
    
    // Bounds clamping
    if (left < 10) left = 10;
    if (left + ttRect.width > window.innerWidth - 10) {
      left = window.innerWidth - ttRect.width - 10;
    }
    
    // Flip to above if overflowing bottom
    if (top + ttRect.height > window.innerHeight - 10) {
      top = rect.top - ttRect.height - pad;
      if (top < 10) top = 10;
    }
    
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  });

  document.addEventListener('mouseout', (e) => {
    const el = e.target.closest('[data-tooltip]');
    if (el) {
      tooltip.style.display = 'none';
      tooltip.style.opacity = '0';
    }
  });

  document.addEventListener('click', () => {
    tooltip.style.display = 'none';
    tooltip.style.opacity = '0';
  });
}

/**
 * 9. Real-Time Fubon API Live Price Stream (Polling Gateway)
 */
let lastTxfPrice = null;

// 2026-09-17: an https page (the deployed GitHub Pages site) fetching http://localhost is
// blocked by Chrome's Private Network Access policy (confirmed via browser testing on the main
// dashboard's equivalent code) — that fetch can sit pending rather than reject, which without a
// timeout would silently starve this tier forever. Falls back to TAIFEX's public MIS endpoint
// (same one the main dashboard's app.js already uses) for TAIEX/TXF when the local Fubon
// gateway is unreachable, instead of permanently showing "盤後休市" even during live trading.
// 連不到就暫停一陣子再試：本機閘道 60 秒、期交所 MIS 5 分鐘（線上網站上 MIS 會被 CORS 擋，不必每 3 秒撞一次）。
let _localGwRetryAt = 0;
let _misRetryAt = 0;
let _workerQuoteRetryAt = 0;
async function fetchFubonOrPublicFallback() {
  if (Date.now() >= _localGwRetryAt) try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);
    const resp = await fetch(`${GATEWAY_BASE}/api/live_tick`, { signal: controller.signal });
    clearTimeout(timeout);
    if (resp.ok) {
      const data = await resp.json();
      if (data) return { data, source: 'fubon' };
    }
  } catch (e) {
    // Local gateway not running, blocked, or timed out — fall through to the public fallback.
    _localGwRetryAt = Date.now() + 60000;
  }

  // 第二來源：私有 Cloudflare Worker 代抓期交所／證交所（手機直連期交所會被 CORS 擋）。Worker 沒部署新版或連不到時退避 60 秒。
  if (Date.now() >= _workerQuoteRetryAt) try {
    const wr = await fetch(`${ADX_MTF_API}?indicator=quote`);
    if (wr.ok) {
      const q = await wr.json();
      if (q && (q.txf || q.taiex || q.otc)) return { data: q, source: 'worker' };
    }
    _workerQuoteRetryAt = Date.now() + 60000;
  } catch (e) {
    _workerQuoteRetryAt = Date.now() + 60000;
  }

  if (Date.now() >= _misRetryAt) try {
    // 05:00–08:45 沒有盤，期交所此時回的是舊夜盤資料，不可當即時價；夜盤判斷也改用台北時間而非瀏覽器本機時區。
    if (!isTaifexSessionOpenNow()) return { data: null, source: null };
    const nowH = taipeiHourNow();
    const isNightSession = (nowH >= 15 || nowH < 5);
    const misRes = await fetch('https://mis.taifex.com.tw/futures/api/getQuoteList', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ MarketType: isNightSession ? '1' : '0', SymbolType: 'F' })
    });
    if (misRes.ok) {
      const misData = await misRes.json();
      const quoteList = (misData.RtData && misData.RtData.QuoteList) ? misData.RtData.QuoteList : [];
      const txItem = quoteList.find(q => q.SymbolID && q.SymbolID.startsWith('TX') && q.CLastPrice && parseFloat(q.CLastPrice) > 0);
      if (txItem) {
        const price = parseFloat(txItem.CLastPrice);
        const change = parseFloat(txItem.NChangeVal || 0);
        const pct = parseFloat(txItem.NChangeRate || 0);
        return { data: { txf: { price, change, pct } }, source: 'mis' };
      }
    }
  } catch (e) {
    // Public fallback also unreachable — genuinely nothing to show.
    _misRetryAt = Date.now() + 300000;
  }
  return { data: null, source: null };
}

// 手機等連不到即時來源的裝置：每 60 秒重抓一次 CI 更新的 gex_data.json，資料有更新時刷新畫面報價，不必手動重新整理。
let _delayedQuoteCheckAt = 0;
async function refreshDelayedQuote() {
  if (Date.now() < _delayedQuoteCheckAt) return;
  _delayedQuoteCheckAt = Date.now() + 60000;
  try {
    const res = await fetch('../data/gex_data.json?t=' + Date.now());
    if (!res.ok) return;
    const fresh = await res.json();
    if (fresh && fresh.last_updated_time && (!gexData || fresh.last_updated_time !== gexData.last_updated_time)) {
      gexData = fresh;
      renderLeftPanel();
    }
  } catch (e) { /* 網路暫時不通，下一輪再試 */ }
}

function taipeiHourNow() {
  return parseInt(new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Taipei', hour: '2-digit', hour12: false }).format(new Date()), 10) % 24;
}

// 台北時間現在是否在期交所交易時段（日盤 08:45–13:45、夜盤 15:00–隔日 05:00，週一至週五開盤；不含國定假日）。
function isTaifexSessionOpenNow() {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Taipei', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date());
  const get = t => parts.find(x => x.type === t).value;
  const wd = get('weekday');
  const mins = (parseInt(get('hour'), 10) % 24) * 60 + parseInt(get('minute'), 10);
  const weekend = wd === 'Sat' || wd === 'Sun';
  const day = !weekend && mins >= 8 * 60 + 45 && mins < 13 * 60 + 45;
  const nightEve = !weekend && mins >= 15 * 60;
  const nightMorn = wd !== 'Sun' && wd !== 'Mon' && mins < 5 * 60;
  return day || nightEve || nightMorn;
}

// 2026-10-07 實測：開盤後主圖停在夜盤最後一根、不跟即時報價走（圖只吃 klines_cache.json，富邦分K排程收盤後才補）。
// 現在用真實的 /api/live_tick 台指期成交價推進「最後一根」，換到新週期時自動開新K棒。只用真實報價，不補、不造：
// 開盤價＝本頁面第一次看到該根的成交價（頁面在該根中途才開時，開／高／低只涵蓋「看到之後」，圖上用黃色小字誠實標明）。
const LIVE_BAR_SECONDS = { '1M': 60, '3M': 180, '5M': 300, '15M': 900, '30M': 1800, '1H': 3600 };
let liveBar = null;   // { tf, time, open, high, low, close, partial }
function applyLiveTickToChart(price) {
  if (!candleSeries || !(price > 0)) return;
  if ((currentActiveSymbol?.symbol || 'TXF') !== 'TXF') return;
  const step = LIVE_BAR_SECONDS[currentTf];
  if (!step) { setLiveBarNotice(''); return; }      // 4H／日／週／月K 的分段規則有盤別邊界，不在前端硬湊
  const cached = candleSeries.data();
  const last = cached && cached.length ? cached[cached.length - 1] : null;
  if (!last) return;
  const bucket = Math.floor(Date.now() / 1000 / step) * step;
  if (last.time > bucket) return;                    // 圖上已有比現在更新的資料，不動
  if (last.time === bucket) {
    // 該根已在快取內（或上一輪即時推進建立的）：只往真實價格方向擴張高低、更新收盤
    const bar = { time: bucket, open: last.open, high: Math.max(last.high, price), low: Math.min(last.low, price), close: price };
    candleSeries.update(bar);
    liveBar = { ...bar, tf: currentTf, partial: liveBar && liveBar.time === bucket ? liveBar.partial : false };
  } else {
    // 新的一根：開盤＝第一筆看到的成交價
    const bar = { time: bucket, open: price, high: price, low: price, close: price };
    candleSeries.update(bar);
    liveBar = { ...bar, tf: currentTf, partial: true };
  }
  legendLastCandle = { time: liveBar.time, open: liveBar.open, high: liveBar.high, low: liveBar.low, close: liveBar.close };
  setLiveBarNotice(liveBar.partial
    ? `⏱ 即時K棒：自 ${new Date(Date.now()).toLocaleTimeString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false, hour: '2-digit', minute: '2-digit' })} 起累積（開／高／低可能不含此前走勢）；副圖指標待收盤K線更新`
    : '');
}
function setLiveBarNotice(text) {
  let n = document.getElementById('live-bar-notice');
  const pane = document.getElementById('main-chart-pane');
  if (!pane) return;
  if (!n) {
    n = document.createElement('div');
    n.id = 'live-bar-notice';
    n.style.cssText = 'position:absolute;bottom:26px;left:8px;z-index:20;padding:2px 8px;border-radius:6px;background:rgba(13,17,23,0.8);color:#ffd700;font-size:0.68rem;pointer-events:none;';
    if (getComputedStyle(pane).position === 'static') pane.style.position = 'relative';
    pane.appendChild(n);
  }
  n.style.display = text ? 'block' : 'none';
  n.textContent = text || '';
}

function initFubonLivePriceStream() {
  // Check if trading hours & real server active
  setInterval(async () => {
    try {
      const { data, source } = await fetchFubonOrPublicFallback();

      const statusTag = document.getElementById('fubon-status-tag');

      // 🔴 盤後休市或無即時伺服器串流時：嚴禁產生隨機假走步跳動！保持定案結算價！
      if (!data) {
        if (statusTag) {
          // 交易時段內抓不到即時價，不能謊稱休市：如實顯示「無即時數據」（AGENTS.md 紅線 6）。
          const liveHours = isTaifexSessionOpenNow();
          const dataTime = gexData && gexData.last_updated_time ? gexData.last_updated_time : '';
          statusTag.innerHTML = liveHours
            ? '⚪ 無即時數據' + (dataTime ? '・畫面報價為 ' + dataTime + ' 的資料（非即時）' : '')
            : '🟡 盤後休市 (定案結算價)';
          if (liveHours) refreshDelayedQuote();
          statusTag.style.borderColor = liveHours ? '#8b95a5' : '#ffd700';
          statusTag.style.color = liveHours ? '#8b95a5' : '#ffd700';
        }
        return;
      }

      // 1. TAIEX 加權指數
      if (data.taiex) {
        const valEl = document.getElementById('top-val-taiex');
        const chgEl = document.getElementById('top-chg-taiex');
        if (valEl) valEl.innerText = data.taiex.price.toLocaleString();
        if (chgEl) {
          const isUp = data.taiex.change >= 0;
          const sign = isUp ? '+' : '';
          chgEl.innerText = `${sign}${data.taiex.change} (${sign}${data.taiex.pct}%)`;
          chgEl.style.color = isUp ? 'var(--call-color)' : 'var(--put-color)';
        }
      }

      // 2. OTC 櫃買指數
      if (data.otc) {
        const valEl = document.getElementById('top-val-otc');
        const chgEl = document.getElementById('top-chg-otc');
        if (valEl) valEl.innerText = data.otc.price.toLocaleString();
        if (chgEl) {
          const isUp = data.otc.change >= 0;
          const sign = isUp ? '+' : '';
          chgEl.innerText = `${sign}${data.otc.change} (${sign}${data.otc.pct}%)`;
          chgEl.style.color = isUp ? 'var(--call-color)' : 'var(--put-color)';
        }
      }

      // 3. 台指期 (TXF)
      if (data.txf) {
        const valEl = document.getElementById('top-val-txf');
        const chgEl = document.getElementById('top-chg-txf');
        const leftMainP = document.getElementById('left-main-price');

        if (valEl) valEl.innerText = data.txf.price.toLocaleString();
        // 只在交易時段、且這筆報價夠新（有時間戳就檢查；MIS 備援沒有時間戳）時推進K棒，避免休市後拿舊價開新棒
        const _tickFresh = typeof data.txf.ts === 'number' ? (Date.now() / 1000 - data.txf.ts) < 20 : true;
        if (isTaifexSessionOpenNow() && _tickFresh) applyLiveTickToChart(data.txf.price);
        if (leftMainP && (!currentActiveSymbol || currentActiveSymbol.symbol === 'TXF')) {
          leftMainP.innerText = data.txf.price.toLocaleString();
          if (lastTxfPrice !== null && lastTxfPrice !== data.txf.price) {
            leftMainP.style.transform = 'scale(1.04)';
            setTimeout(() => { leftMainP.style.transform = 'scale(1.0)'; }, 250);
          }
          lastTxfPrice = data.txf.price;
          liveTxf = { price: data.txf.price, at: Date.now() };
          // 價格即時更新時，下方的漲跌點數／漲跌幅也要同步用即時報價的數字；以前只更新價格，漲跌停在頁面載入時用雲端資料檔算的
          // 舊值（例如價格 48,685 旁邊卻顯示 -32／-0.07%，實際是 +355／+0.73%）。2026-10-01 稽核發現。
          const dEl = document.getElementById('left-price-diff');
          const pcEl = document.getElementById('left-price-pct');
          if (dEl && pcEl && typeof data.txf.change === 'number') {
            const up = data.txf.change >= 0;
            const sg = up ? '+' : '';
            dEl.innerText = `${sg}${data.txf.change}`;
            pcEl.innerText = `(${sg}${data.txf.pct}%)`;
            const col = up ? 'var(--call-color)' : 'var(--put-color)';
            dEl.style.color = col; pcEl.style.color = col; leftMainP.style.color = col;
          }
          if (gexData && gexAdviceInputs().ok) {
            refreshGexDistances(data.txf.price, gexData.call_wall_strike, gexData.zero_gamma_level, gexData.put_wall_strike, gexData.max_pain_strike);
          }
        }

        if (chgEl) {
          const isUp = data.txf.change >= 0;
          const sign = isUp ? '+' : '';
          chgEl.innerText = `${sign}${data.txf.change} (${sign}${data.txf.pct}%)`;
          chgEl.style.color = isUp ? 'var(--call-color)' : 'var(--put-color)';
        }
      }

      // 4. Live Left Macro Risk HUD Pulsing (same macro_events_radar nesting fix as above)
      if (data.macro) {
        liveMacro = { ...data.macro, at: Date.now() };
        updateMacroRiskHUD(gexData?.macro_events_radar?.macro_risk_dashboard || null, data.macro);
      }

      if (statusTag) {
        if (YAHOO_SOURCE_SYMBOLS.has(currentActiveSymbol?.symbol)) {
          // 原油／黃金／美元指數／美債不是富邦資料（富邦 API 沒有海外期貨），照實標示來源
          statusTag.innerHTML = '🌐 Yahoo Finance（非富邦，可能延遲）';
          statusTag.style.borderColor = 'var(--primary-accent)';
          statusTag.style.color = 'var(--primary-accent)';
        } else if (source === 'fubon') {
          statusTag.innerHTML = '🟢 富邦 Neo API (Live)';
          statusTag.style.borderColor = '#00e676';
          statusTag.style.color = '#00e676';
        } else if (source === 'worker') {
          statusTag.innerHTML = '🌐 期交所／證交所 (Worker 轉發，約 3 秒延遲)';
          statusTag.style.borderColor = 'var(--primary-accent)';
          statusTag.style.color = 'var(--primary-accent)';
        } else {
          statusTag.innerHTML = '🌐 期交所 MIS (備援行情)';
          statusTag.style.borderColor = 'var(--primary-accent)';
          statusTag.style.color = 'var(--primary-accent)';
        }
      }

    } catch (e) {
      // Quiet fail fallback
    }
  }, 3000);
}

/**
 * 10. Overseas contract tab tooltip (CL Crude Oil, US10Y Yield, DXY Dollar Index)
 *
 * ⚠️ 2026-09-17: 名稱跟原本的用途不符——這支函式從建立以來就只有設定滑鼠提示文字裡的結算價，
 * 完全沒有真的抓取這三個標的的即時報價（沒有fetch、沒有setInterval）。CL/US10Y/DXY 目前
 * 唯一的真實數據來源是 gexData.macro_events_radar.macro_risk_dashboard（後端 fetch_and_
 * calc_vision.py 抓的，每次頁面重整才會更新一次），還沒有前端即時輪詢的版本。保留原本行為
 * （只設定提示文字），沒有假裝加上即時性；真正做即時輪詢是後續待辦，不在這次範圍內。
 */
function initOverseasLiveTickStream() {
  const clTab = document.querySelector('.contract-tab[data-contract="CL"]');
  if (clTab) {
    clTab.title = '紐約輕原油期貨（Yahoo 來源，非富邦；可能延遲）';  // was a hard-coded "結算" price that never updated
  }
}

// Auto init data preloading & live price stream
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    loadScreenerAndRealQuotesData();
    initFubonLivePriceStream();
    initOverseasLiveTickStream();
  }, 1000);
});







/**
 * Y 軸自動縮放：重新開啟所有圖表右側價格軸的 autoScale（使用者手動拖曳 Y 軸會關掉它），
 * 並讓 K 線適應螢幕。換商品與右下角「自動」按鈕共用。
 */
function resetPriceAutoScale() {
  [mainChart, subChart1, subChart2, subChart3, subChart4].forEach(ch => {
    if (!ch) return;
    try { ch.priceScale('right').applyOptions({ autoScale: true }); } catch (e) { /* 軸不存在就略過 */ }
  });
  if (mainChart) {
    try { mainChart.timeScale().fitContent(); } catch (e) { /* 尚無資料 */ }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-auto-fit');
  if (btn) btn.addEventListener('click', resetPriceAutoScale);
});
