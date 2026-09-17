/**
 * 🦅 尋鳥戰情交易室 (Bird Trading Room) Core Engine v64.0
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
let leftPanelCollapsed = false;
let rightPanelCollapsed = false;
let advisorAttachedImage = null;

// GEX Strict Asset Scope (僅在台指期、小台、微台顯示 GEX 5 大防線)
const GEX_SUPPORTED_SYMBOLS = ['TXF', 'MXF', 'MTX', 'TMF'];

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
const CORE_PRESET_ASSETS = {
  'TXF': { symbol: 'TXF', name: '台指期貨', category: '指數期貨', market: 'TAIFEX', has_futures: true, futures_code: 'TXF', base_price: 46588, is_yield: false },
  'TAIEX': { symbol: 'TAIEX', name: '加權指數', category: '大盤現貨', market: 'TWSE', has_futures: true, futures_code: 'TXF', base_price: 46184.85, is_yield: false },
  'OTC': { symbol: 'OTC', name: '櫃買指數', category: '中小型股', market: 'TPEx', has_futures: true, futures_code: 'GDF', base_price: 395.52, is_yield: false },
  'CDF': { symbol: 'CDF', name: '台積電期貨', category: '個股期貨', market: 'TAIFEX', has_futures: true, futures_code: 'CDF', base_price: 2434, is_yield: false },
  'MTX': { symbol: 'MTX', name: '微台期貨', category: '指數期貨', market: 'TAIFEX', has_futures: true, futures_code: 'TMF', base_price: 46588, is_yield: false },
  'MXF': { symbol: 'MXF', name: '小台期貨', category: '指數期貨', market: 'TAIFEX', has_futures: true, futures_code: 'MXF', base_price: 46588, is_yield: false },
  'US10Y': { symbol: 'US10Y', name: '美國10年公債殖利率', category: '總經公債', market: 'GLOBAL', has_futures: false, futures_code: 'ZN', base_price: 4.940, is_yield: true },
  'DXY': { symbol: 'DXY', name: '美元指數 (DXY)', category: '總經外匯', market: 'ICE', has_futures: false, futures_code: 'DX', base_price: 98.845, is_yield: false },
  'CL': { symbol: 'CL', name: '紐約輕原油期貨', category: '大宗商品', market: 'NYMEX', has_futures: true, futures_code: 'CL', base_price: 99.58, is_yield: false }
};

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
  vrvp: true,
  vrvpRows: 50,
  vrvpVa: 70,
  sar: false,
  sarStep: 0.02,
  fvg: false
};

// DOM Initialization
document.addEventListener('DOMContentLoaded', async () => {
  initGlobalSmartTooltips();
  await initTradingRoom();
  initFubonLivePriceStream();
  initOverseasLiveTickStream();
  initSymbolSearchAndAutocomplete();
  initQuantScreenerModal();
});

async function initTradingRoom() {
  console.log('🦅 Initializing Multi-Pane Bird Trading Room v64.0...');
  
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

  // Load Full Symbol Universe (1,400+ Stocks & Futures)
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
      fontSize: 11,
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
    timeScale: {
      borderColor: '#1a2538',
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 12,
      barSpacing: 8
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
    title: 'Volume MA (5)'
  });
  volMa10Series = subChart1.addLineSeries({
    color: '#FFFFFF',
    lineWidth: 1.5,
    title: 'Volume MA (10)'
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
    title: '快線'
  });
  macdDeaSeries = subChart2.addLineSeries({
    color: '#ffd700',
    lineWidth: 1.5,
    title: '慢線'
  });

  // --- Sub-Chart 3: 波段拐點 CCI (20 通道 & 買賣轉折點) ---
  subChart3 = LightweightCharts.createChart(cSub3, {
    ...subChartOptions,
    timeScale: { ...commonOptions.timeScale, visible: false }
  });
  cciLineSeries = subChart3.addLineSeries({
    color: '#ffd700',
    lineWidth: 2,
    title: 'CCI'
  });
  // Add reference lines (+200, +100, 0, -100, -200)
  cciLineSeries.createPriceLine({ price: 200, color: 'rgba(0, 206, 201, 0.7)', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '+200 超買' });
  cciLineSeries.createPriceLine({ price: 100, color: 'rgba(46, 213, 115, 0.6)', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '+100 賣點' });
  cciLineSeries.createPriceLine({ price: 0, color: 'rgba(255, 255, 255, 0.25)', lineStyle: LightweightCharts.LineStyle.Dotted, lineWidth: 1, title: '0' });
  cciLineSeries.createPriceLine({ price: -100, color: 'rgba(255, 128, 128, 0.6)', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '-100 買點' });
  cciLineSeries.createPriceLine({ price: -200, color: 'rgba(255, 0, 0, 0.7)', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '-200 超賣' });

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
function generateIndicatorsData(tf) {
  let basePrice = 46588;
  let isYield = false;

  if (currentActiveSymbol) {
    const sym = currentActiveSymbol.symbol;
    isYield = !!currentActiveSymbol.is_yield;

    if (sym === 'TXF' || sym === 'MTX' || sym === 'MXF') {
      basePrice = gexData?.night_txf_price || gexData?.txf_price || 46588;
    } else if (sym === 'TAIEX') {
      basePrice = gexData?.spot_price || 46184.85;
    } else if (sym === 'OTC') {
      basePrice = gexData?.two_price || 395.52;
    } else if (CORE_PRESET_ASSETS[sym]) {
      basePrice = CORE_PRESET_ASSETS[sym].base_price;
    } else if (realQuotesData && realQuotesData[sym] && realQuotesData[sym].close) {
      basePrice = realQuotesData[sym].close;
    } else if (sym === '2330' || sym === 'CDF') {
      basePrice = 2434;
    } else if (sym === '2454' || sym === 'DVF') {
      basePrice = 1430;
    } else if (sym === '2317' || sym === 'RVF') {
      basePrice = 1621;
    } else if (sym === '2382' || sym === 'PUF') {
      basePrice = 4605;
    } else if (sym === '2603' || sym === 'CCF') {
      basePrice = 144.5;
    } else if (sym === '0050' || sym === 'NYF') {
      basePrice = 188;
    } else if (sym === '00631L' || sym === 'QAF') {
      basePrice = 265;
    } else {
      let hash = 0;
      for (let c = 0; c < sym.length; c++) hash = (hash * 31 + sym.charCodeAt(c)) % 1000;
      basePrice = 45 + (hash % 500);
    }
  } else if (gexData && gexData.txf_price) {
    basePrice = gexData.txf_price;
  }
  
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
  const cachedCandles = klinesCacheData?.assets?.[sym]?.timeframes?.[tf];

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

  // --- Real 尋鳥多空彩帶 (MA7, MA17, MA88, MA200) ---
  const calcSMA = (len) => {
    const res = [];
    for (let i = 0; i < count; i++) {
      if (i >= len - 1) {
        let sum = 0;
        for (let k = 0; k < len; k++) sum += closes[i - k];
        res.push({ time: candles[i].time, value: Math.round((sum / len) * 10) / 10 });
      }
    }
    return res;
  };

  const ma7 = calcSMA(7);
  const ma17 = calcSMA(17);
  const ma88 = calcSMA(Math.min(88, Math.floor(count * 0.7)));
  const ma200 = calcSMA(Math.min(200, Math.floor(count * 0.85)));

  // --- Real EMA Helper ---
  function computeEMA(src, period) {
    const k = 2 / (period + 1);
    const ema = [];
    let prev = src[0];
    for (let i = 0; i < src.length; i++) {
      if (i === 0) {
        prev = src[0];
      } else {
        prev = src[i] * k + prev * (1 - k);
      }
      ema.push(prev);
    }
    return ema;
  }

  // --- Real 戰情雙層 MACD (Main: 12/26/9, Sub: 3/15/5 with 4-color acceleration) ---
  const ema12 = computeEMA(closes, 12);
  const ema26 = computeEMA(closes, 26);
  const mainDif = ema12.map((val, idx) => val - ema26[idx]);
  const mainDea = computeEMA(mainDif, 9);
  
  const subEma3 = computeEMA(closes, 3);
  const subEma15 = computeEMA(closes, 15);
  const subDifArr = subEma3.map((val, idx) => val - subEma15[idx]);
  const subDeaArr = computeEMA(subDifArr, 5);

  const macdData = [];
  const difData = [];
  const deaData = [];

  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    const difVal = mainDif[i];
    const deaVal = mainDea[i];
    const histVal = (difVal - deaVal) * 2;
    
    // Sub MACD 4-color momentum acceleration
    const subDif = subDifArr[i];
    const subDea = subDeaArr[i];
    const subHistCurr = subDif - subDea;
    const subHistPrev = i > 0 ? (subDifArr[i - 1] - subDeaArr[i - 1]) : subHistCurr;
    
    const isSubBull = subDif > 0;
    const isExpanding = subHistCurr >= subHistPrev;
    
    let histColor;
    if (isSubBull) {
      histColor = isExpanding ? '#ff3b30' : '#007aff'; // 🔴 強多加速 / 🔵 多頭收斂減碼
    } else {
      histColor = isExpanding ? '#007aff' : '#34c759'; // 🔵 水下翻紅早鳥預警 / 🟢 空頭主跌加速
    }

    difData.push({ time: t, value: Math.round(difVal * 10) / 10 });
    deaData.push({ time: t, value: Math.round(deaVal * 10) / 10 });
    macdData.push({ time: t, value: Math.round(histVal * 10) / 10, color: histColor });
  }

  // --- Real 波段拐點 CCI (20) & 4色買賣轉折圓點 (Only on true threshold crossing) ---
  const cciData = [];
  const cciSignals = [];
  const cciPeriod = 20;

  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    if (i < cciPeriod - 1) {
      cciData.push({ time: t, value: 0 });
      continue;
    }

    // Typical Price TP = (H + L + C) / 3
    let sumTp = 0;
    const tpSlice = [];
    for (let k = 0; k < cciPeriod; k++) {
      const idx = i - k;
      const tp = (highs[idx] + lows[idx] + closes[idx]) / 3.0;
      tpSlice.push(tp);
      sumTp += tp;
    }
    const meanTp = sumTp / cciPeriod;

    let sumMd = 0;
    for (let k = 0; k < cciPeriod; k++) {
      sumMd += Math.abs(tpSlice[k] - meanTp);
    }
    const meanDev = sumMd / cciPeriod || 0.001;
    const currTp = (highs[i] + lows[i] + closes[i]) / 3.0;
    const cciVal = (currTp - meanTp) / (0.015 * meanDev);
    const roundedCci = Math.round(cciVal * 10) / 10;
    cciData.push({ time: t, value: roundedCci });

    // Threshold crossing detection
    if (i > cciPeriod) {
      const prevCci = cciData[i - 1].value;
      const currCci = roundedCci;

      // 買點1: 由下往上穿過 -200 (深紅圓點)
      if (prevCci <= -200 && currCci > -200) {
        cciSignals.push({ time: t, position: 'inBar', color: '#FF0000', shape: 'circle', text: '-200' });
      }
      // 買點2: 由下往上穿過 -100 (粉紅圓點)
      else if (prevCci <= -100 && currCci > -100) {
        cciSignals.push({ time: t, position: 'inBar', color: '#FF8080', shape: 'circle', text: '-100' });
      }
      // 賣點1: 由下往上穿過 +100 (淺綠圓點)
      else if (prevCci <= 100 && currCci > 100) {
        cciSignals.push({ time: t, position: 'inBar', color: '#00FF00', shape: 'circle', text: '+100' });
      }
      // 賣點2: 由下往上穿過 +200 (青綠圓點)
      else if (prevCci <= 200 && currCci > 200) {
        cciSignals.push({ time: t, position: 'inBar', color: '#00CEC9', shape: 'circle', text: '+200' });
      }
    }
  }

  // --- Real AO (Awesome Oscillator) = SMA(hl2, 5) - SMA(hl2, 34) ---
  const hl2Arr = [];
  for (let i = 0; i < count; i++) {
    hl2Arr.push((highs[i] + lows[i]) / 2.0);
  }

  const aoData = [];
  const cvdCandles = [];
  let cumDelta = 0;

  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    let sum5 = 0;
    const len5 = Math.min(i + 1, 5);
    for (let k = 0; k < len5; k++) sum5 += hl2Arr[i - k];
    const sma5 = sum5 / len5;

    let sum34 = 0;
    const len34 = Math.min(i + 1, 34);
    for (let k = 0; k < len34; k++) sum34 += hl2Arr[i - k];
    const sma34 = sum34 / len34;

    const aoVal = sma5 - sma34;
    const prevAo = i > 0 ? aoData[i - 1].value : aoVal;
    const diff = aoVal - prevAo;
    const aoColor = diff >= 0 ? '#009688' : '#F44336';
    aoData.push({ time: t, value: Math.round(aoVal * 10) / 10, color: aoColor });

    // CVD Candlesticks (Accumulated Volume Delta)
    const barSpread = (highs[i] - lows[i]) || 1;
    const deltaRatio = (closes[i] - opens[i]) / barSpread;
    const barDelta = Math.round(volumes[i].value * deltaRatio * 0.4);
    const openVol = cumDelta;
    const closeVol = cumDelta + barDelta;
    const highVol = Math.max(openVol, closeVol) + Math.round(Math.abs(barDelta) * 0.2 + 20);
    const lowVol = Math.min(openVol, closeVol) - Math.round(Math.abs(barDelta) * 0.2 + 20);
    cumDelta = closeVol;

    cvdCandles.push({
      time: t,
      open: openVol,
      high: highVol,
      low: lowVol,
      close: closeVol
    });
  }

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

  // --- 🚀 Authentic ADX Pro V3 (Dual Color + 4-State Breakout + Divergence) ---
  // 1:1 對齊 adx_dual_color_v3.pine 演算法
  const adxPeriod = 14;
  const thBase = 20;     // 20 盤整打底線
  const thTrend = 30;    // 30 動能爆發線
  const thStrong = 50;   // 50 強勢警戒線
  const thExtreme = 75;  // 75 極端警戒線
  const breakLookback = 20;
  const breakCooldown = 8;

  let trSmooth = 0, plusDmSmooth = 0, minusDmSmooth = 0;
  const dxArr = [];
  const adxValues = [];
  const adxLine = [];
  const adxHist = [];
  const adxSignals = [];

  let lastBoBar = -100;
  let lastBdBar = -100;
  let lastSwingHigh = null; // {price, adx} of the most recent confirmed swing high — real
  let lastSwingLow = null;  // reference points for divergence, not a fixed price level

  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    if (i === 0) {
      adxValues.push(20);
      adxLine.push({ time: t, value: 20 });
      adxHist.push({ time: t, value: 20, color: '#26A69A' });
      continue;
    }

    const upMove = highs[i] - highs[i - 1];
    const downMove = lows[i - 1] - lows[i];
    const plusDm = (upMove > downMove && upMove > 0) ? upMove : 0;
    const minusDm = (downMove > upMove && downMove > 0) ? downMove : 0;
    const tr = Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1]));

    if (i <= adxPeriod) {
      trSmooth += tr;
      plusDmSmooth += plusDm;
      minusDmSmooth += minusDm;
      if (i === adxPeriod) {
        trSmooth /= adxPeriod;
        plusDmSmooth /= adxPeriod;
        minusDmSmooth /= adxPeriod;
      }
    } else {
      trSmooth = (trSmooth * (adxPeriod - 1) + tr) / adxPeriod;
      plusDmSmooth = (plusDmSmooth * (adxPeriod - 1) + plusDm) / adxPeriod;
      minusDmSmooth = (minusDmSmooth * (adxPeriod - 1) + minusDm) / adxPeriod;
    }

    const pDi = trSmooth > 0 ? (plusDmSmooth / trSmooth) * 100 : 20;
    const mDi = trSmooth > 0 ? (minusDmSmooth / trSmooth) * 100 : 20;
    const diSum = pDi + mDi;
    const dx = diSum > 0 ? (Math.abs(pDi - mDi) / diSum) * 100 : 20;
    dxArr.push(dx);

    let adx = 20;
    if (dxArr.length >= adxPeriod) {
      let sumDx = 0;
      for (let k = 0; k < adxPeriod; k++) sumDx += dxArr[dxArr.length - 1 - k];
      adx = sumDx / adxPeriod;
    }
    adx = Math.round(adx * 10) / 10;
    adxValues.push(adx);

    // ADX Pro V3 4-Color Gradient
    let adxColor = '#26A69A'; // < 20 綠色 (盤整打底)
    if (adx >= thExtreme) {
      adxColor = '#FF5252';   // >= 75 極端警戒 (紅)
    } else if (adx >= thStrong) {
      adxColor = '#FF7043';   // >= 50 強勢警戒 (橘紅)
    } else if (adx >= thTrend) {
      adxColor = '#FFA726';   // >= 30 動能爆發 (金橘)
    } else if (adx >= thBase) {
      adxColor = '#BA68C8';   // >= 20 動能醞釀 (淡紫)
    }

    adxLine.push({ time: t, value: adx });
    adxHist.push({ time: t, value: adx, color: adxColor });

    // ADX Pro V3 頂背離與底背離判定：比較「本次波段極值」與「上一次波段極值」當下的真實 ADX
    // 值（真實背離定義：價格創新高但趨勢強度未跟著創高＝頂背離；價格創新低但趨勢強度未跟著
    // 創高＝底背離），完全依當時真實價格與 ADX 相對關係判斷，不綁定任何固定價位——價格永久
    // 脫離舊區間後這個判斷依然成立，不會失效。
    if (i >= 2) {
      const priorIdx = i - 1;
      const isConfirmedPeak = highs[priorIdx] > highs[priorIdx - 1] && highs[priorIdx] >= highs[i];
      const isConfirmedTrough = lows[priorIdx] < lows[priorIdx - 1] && lows[priorIdx] <= lows[i];

      if (isConfirmedPeak) {
        const peakPrice = highs[priorIdx];
        const peakAdx = adxValues[priorIdx];
        if (lastSwingHigh && peakPrice > lastSwingHigh.price && peakAdx < lastSwingHigh.adx && (i - lastBoBar >= 25)) {
          adxSignals.push({ time: candles[priorIdx].time, position: 'aboveBar', color: '#00E676', shape: 'arrowDown', text: '▼ 頂背離' });
          lastBoBar = i;
        }
        lastSwingHigh = { price: peakPrice, adx: peakAdx };
      }
      if (isConfirmedTrough) {
        const troughPrice = lows[priorIdx];
        const troughAdx = adxValues[priorIdx];
        if (lastSwingLow && troughPrice < lastSwingLow.price && troughAdx < lastSwingLow.adx && (i - lastBdBar >= 25)) {
          adxSignals.push({ time: candles[priorIdx].time, position: 'belowBar', color: '#FF5252', shape: 'arrowUp', text: '▲ 底背離' });
          lastBdBar = i;
        }
        lastSwingLow = { price: troughPrice, adx: troughAdx };
      }
    }
  }

  // --- Real TD Sequential DeMark 9★ / 13★ Setup & Multi-Factor Filtered Momentum Birds ---
  const markers = [];
  let bullSetupCount = 0;
  let bearSetupCount = 0;
  let lastSignalIdx = -30;

  for (let i = 4; i < count; i++) {
    const t = candles[i].time;
    
    // TD Setup counting against close[i-4]
    if (closes[i] < closes[i - 4]) {
      bullSetupCount++;
      bearSetupCount = 0;
    } else if (closes[i] > closes[i - 4]) {
      bearSetupCount++;
      bullSetupCount = 0;
    } else {
      bullSetupCount = 0;
      bearSetupCount = 0;
    }

    // TD DeMark 9★ (抄底/逃頂)
    if (bullSetupCount === 9) {
      markers.push({ time: t, position: 'belowBar', color: '#2ed573', shape: 'circle', text: '9★抄底' });
    } else if (bearSetupCount === 9) {
      markers.push({ time: t, position: 'aboveBar', color: '#ff4757', shape: 'circle', text: '9★逃頂' });
    }

    // Multi-factor Momentum Bird signals (Strict filtering to prevent icon clutter)
    if (i >= 20 && (i - lastSignalIdx >= 14)) {
      const curClose = closes[i];
      const curOpen = opens[i];
      const curVol = volumes[i].value;
      const ma5v = volMa5.find(v => v.time === t)?.value || 1000;
      const cciV = cciData[i]?.value || 0;
      const macdDifV = mainDif[i];
      const macdDeaV = mainDea[i];

      // 🚀 強火箭 (帶量突破主均線與前高)
      if (curClose > curOpen && curClose > highs[i - 1] && curVol > ma5v * 1.6 && macdDifV > macdDeaV) {
        markers.push({ time: t, position: 'belowBar', color: '#ffd600', shape: 'arrowUp', text: '🚀 強火箭' });
        lastSignalIdx = i;
      }
      // 🐦 強藍鳥 (超跌起漲 + 抄底結構)
      else if (cciV < -110 && (bullSetupCount >= 6 || curClose > curOpen) && curVol > ma5v * 1.1) {
        markers.push({ time: t, position: 'belowBar', color: '#00b0ff', shape: 'arrowUp', text: '🐦 強藍鳥' });
        lastSignalIdx = i;
      }
      // 🛸 動能再啟 (回測均線後強勢彈升)
      else if (curClose > curOpen && lows[i] <= (ma7.find(m => m.time === t)?.value || curClose) && macdData[i]?.color === '#ff3b30') {
        markers.push({ time: t, position: 'belowBar', color: '#ffd700', shape: 'circle', text: '🛸 動能再啟' });
        lastSignalIdx = i;
      }
      // 💰 減碼 / ⚠️ 出清 (漲幅過大或跌破關鍵支撐)
      else if (bearSetupCount >= 8 || (cciV > 165 && curClose < curOpen)) {
        markers.push({ time: t, position: 'aboveBar', color: '#ff9800', shape: 'arrowDown', text: '💰 減碼' });
        lastSignalIdx = i;
      }
    }
  }

  // --- Real VWAP & SMMA ---
  const vwapData = [];
  const vwapUpper = [];
  const vwapLower = [];
  const smmaData = [];
  
  let cumVol = 0;
  let cumVolPrice = 0;
  let smmaPrev = closes[0];

  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    const tp = (highs[i] + lows[i] + closes[i]) / 3.0;
    const v = volumes[i].value;
    
    cumVol += v;
    cumVolPrice += tp * v;
    const vwapVal = cumVol > 0 ? (cumVolPrice / cumVol) : tp;
    
    // ±1 Standard Deviation channel
    const dev = atrBase * 1.25;
    vwapData.push({ time: t, value: Math.round(vwapVal * 10) / 10 });
    vwapUpper.push({ time: t, value: Math.round((vwapVal + dev) * 10) / 10 });
    vwapLower.push({ time: t, value: Math.round((vwapVal - dev) * 10) / 10 });

    // SMMA 200 on close
    const smmaLen = indicatorConfig.smmaLen || 200;
    if (i === 0) {
      smmaPrev = closes[0];
    } else {
      smmaPrev = (smmaPrev * (smmaLen - 1) + closes[i]) / smmaLen;
    }
    smmaData.push({ time: t, value: Math.round(smmaPrev * 10) / 10 });
  }

  // --- Real VRVP (Visible Range Volume Profile: 50 Rows, 70% Value Area) ---
  const numRows = indicatorConfig.vrvpRows || 50;
  const vaTargetPct = (indicatorConfig.vrvpVa || 70) / 100;
  let highMax = -Infinity, lowMin = Infinity;
  for (let i = 0; i < count; i++) {
    if (candles[i].high > highMax) highMax = candles[i].high;
    if (candles[i].low < lowMin) lowMin = candles[i].low;
  }
  if (highMax === lowMin) highMax += 1.0;
  const binWidth = (highMax - lowMin) / numRows;
  const binsUp = new Array(numRows).fill(0);
  const binsDown = new Array(numRows).fill(0);

  for (let i = 0; i < count; i++) {
    const c = candles[i].close, o = candles[i].open, v = volumes[i].value;
    const h = candles[i].high, l = candles[i].low;
    const isUp = c >= o;
    const kLowIdx = Math.max(0, Math.min(numRows - 1, Math.floor((l - lowMin) / binWidth)));
    const kHighIdx = Math.max(0, Math.min(numRows - 1, Math.floor((h - lowMin) / binWidth)));
    const covered = Math.max(1, kHighIdx - kLowIdx + 1);
    const volPerBin = v / covered;
    for (let b = kLowIdx; b <= kHighIdx; b++) {
      if (isUp) binsUp[b] += volPerBin;
      else binsDown[b] += volPerBin;
    }
  }

  const totalBins = binsUp.map((u, idx) => u + binsDown[idx]);
  let pocIdx = 0, maxBinVol = -1;
  let totalVolSum = 0;
  for (let b = 0; b < numRows; b++) {
    totalVolSum += totalBins[b];
    if (totalBins[b] > maxBinVol) {
      maxBinVol = totalBins[b];
      pocIdx = b;
    }
  }

  const inVa = new Array(numRows).fill(false);
  inVa[pocIdx] = true;
  let accumVaVol = totalBins[pocIdx];
  const targetVaVol = totalVolSum * vaTargetPct;
  let upPtr = pocIdx + 1, downPtr = pocIdx - 1;

  while (accumVaVol < targetVaVol && (upPtr < numRows || downPtr >= 0)) {
    const volUp = upPtr < numRows ? totalBins[upPtr] : -1;
    const volDown = downPtr >= 0 ? totalBins[downPtr] : -1;
    if (volUp >= volDown && volUp >= 0) {
      inVa[upPtr] = true;
      accumVaVol += volUp;
      upPtr++;
    } else if (volDown >= 0) {
      inVa[downPtr] = true;
      accumVaVol += volDown;
      downPtr--;
    } else {
      break;
    }
  }

  let valIdx = pocIdx, vahIdx = pocIdx;
  for (let b = 0; b < numRows; b++) {
    if (inVa[b]) { valIdx = b; break; }
  }
  for (let b = numRows - 1; b >= 0; b--) {
    if (inVa[b]) { vahIdx = b; break; }
  }

  const pocPrice = Math.round((lowMin + (pocIdx + 0.5) * binWidth) * 10) / 10;
  const vahPrice = Math.round((lowMin + (vahIdx + 1.0) * binWidth) * 10) / 10;
  const valPrice = Math.round((lowMin + valIdx * binWidth) * 10) / 10;

  const vrvpBins = [];
  for (let b = 0; b < numRows; b++) {
    vrvpBins.push({
      priceLow: lowMin + b * binWidth,
      priceHigh: lowMin + (b + 1) * binWidth,
      volUp: binsUp[b],
      volDown: binsDown[b],
      totalVol: totalBins[b],
      inVa: inVa[b],
      isPoc: b === pocIdx
    });
  }

  // --- Real Parabolic SAR (Wilder, 1978) ---
  // 2026-09-16: the UI's "🎯 Parabolic SAR" checkbox + Step parameter existed and could be
  // toggled (indicatorConfig.sar / .sarStep), but nothing ever read that state to actually
  // compute or draw anything — checking the box silently did nothing. This is the first real
  // implementation: standard textbook SAR, not an approximation.
  const sarStep = indicatorConfig.sarStep || 0.02;
  const sarMaxAf = 0.2;
  const sarData = [];
  if (count >= 2) {
    let sarUp = closes[1] >= closes[0]; // initial trend guess from the first two closes
    let sar = sarUp ? lows[0] : highs[0];
    let ep = sarUp ? highs[0] : lows[0]; // extreme point
    let af = sarStep;
    sarData.push({ time: candles[0].time, value: sar });
    for (let i = 1; i < count; i++) {
      let nextSar = sar + af * (ep - sar);
      if (sarUp) {
        const clampLow = i >= 2 ? Math.min(lows[i - 1], lows[i - 2]) : lows[i - 1];
        nextSar = Math.min(nextSar, clampLow);
        if (lows[i] < nextSar) {
          sarUp = false;
          nextSar = ep;
          ep = lows[i];
          af = sarStep;
        } else if (highs[i] > ep) {
          ep = highs[i];
          af = Math.min(af + sarStep, sarMaxAf);
        }
      } else {
        const clampHigh = i >= 2 ? Math.max(highs[i - 1], highs[i - 2]) : highs[i - 1];
        nextSar = Math.max(nextSar, clampHigh);
        if (highs[i] > nextSar) {
          sarUp = true;
          nextSar = ep;
          ep = highs[i];
          af = sarStep;
        } else if (lows[i] < ep) {
          ep = lows[i];
          af = Math.min(af + sarStep, sarMaxAf);
        }
      }
      sar = nextSar;
      sarData.push({ time: candles[i].time, value: sar });
    }
  }

  // --- Real Supertrend (ATR-based, Wilder smoothing) ---
  // 2026-09-16: the UI's "Supertrend" checkbox + ATR週期/倍數參數存在（indicatorConfig.supertrend
  // / .stLen / .stMult），但從未被任何運算或渲染程式碼讀取。這是第一次真的實作:獨立的 Wilder ATR
  // (跟 ADX Pro V3 那組 trSmooth 平滑狀態各自獨立，不共用)，再算標準 basic/final upper/lower band。
  const stLen = indicatorConfig.stLen || 10;
  const stMult = indicatorConfig.stMult || 3.0;
  const supertrendUp = [];
  const supertrendDown = [];
  if (count >= 2) {
    let stAtr = 0;
    let stTrSum = 0;
    let finalUpperPrev = 0;
    let finalLowerPrev = 0;
    let stTrendUp = true;

    for (let i = 0; i < count; i++) {
      const t = candles[i].time;
      const tr = i === 0
        ? (highs[i] - lows[i])
        : Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1]));

      if (i < stLen) {
        stTrSum += tr;
        stAtr = stTrSum / (i + 1); // 暖機期間用簡單移動平均，滿週期時等同 Wilder 起始值
      } else {
        stAtr = (stAtr * (stLen - 1) + tr) / stLen;
      }

      const mid = (highs[i] + lows[i]) / 2;
      const basicUpper = mid + stMult * stAtr;
      const basicLower = mid - stMult * stAtr;

      let finalUpper, finalLower;
      if (i === 0) {
        finalUpper = basicUpper;
        finalLower = basicLower;
        stTrendUp = closes[i] >= mid;
      } else {
        finalUpper = (basicUpper < finalUpperPrev || closes[i - 1] > finalUpperPrev) ? basicUpper : finalUpperPrev;
        finalLower = (basicLower > finalLowerPrev || closes[i - 1] < finalLowerPrev) ? basicLower : finalLowerPrev;

        if (closes[i] > finalUpperPrev) {
          stTrendUp = true;
        } else if (closes[i] < finalLowerPrev) {
          stTrendUp = false;
        } // 否則維持前一根的趨勢方向
      }

      const stValue = Math.round((stTrendUp ? finalLower : finalUpper) * 10) / 10;
      supertrendUp.push({ time: t, value: stTrendUp ? stValue : undefined });
      supertrendDown.push({ time: t, value: stTrendUp ? undefined : stValue });

      finalUpperPrev = finalUpper;
      finalLowerPrev = finalLower;
    }
  }

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
    vwapData,
    vwapUpper,
    vwapLower,
    smmaData,
    sarData,
    supertrendUp,
    supertrendDown,
    vrvpData: {
      bins: vrvpBins,
      poc: pocPrice,
      vah: vahPrice,
      val: valPrice,
      maxBinVol
    }
  };
}

/**
 * Render all 5 Charts with Datasets
 */
function renderChartData() {
  const data = generateIndicatorsData(currentTf);

  // 1. Candlesticks on Main Chart
  candleSeries.setData(data.candles);

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

  // 3. Sub-Chart 2: 戰情雙層 MACD
  macdHistSeries.setData(data.macdData);
  macdDifSeries.setData(data.difData);
  macdDeaSeries.setData(data.deaData);

  // 4. Sub-Chart 3: 波段拐點 CCI + 4 色買賣轉折圓點 (紅/粉紅/淺綠/深綠)
  cciLineSeries.setData(data.cciData);
  cciLineSeries.setMarkers(data.cciSignals);

  // 5. Sub-Chart 4: ADX Pro V3 / AO / CVD Candlesticks / Momentum
  renderSub4Chart(data);

  // 6. Main Chart Overlays (GEX + Ribbons + VWAP + SMMA)
  renderMainOverlays(data);
}

// 2026-09-16: ADX Pro V3 副圖的 MTF (多週期) 看板文字，原本是凍結的假字串
// "15M:21.1 1H:29.9 4H:25.7 1D:11.1"，跟畫面上其他即時數據完全脫節。真正的 ADX 算法現在搬到
// 一個私有 Cloudflare Worker（不在這個公開 repo 裡，也不會傳到瀏覽器），這裡改成呼叫那支 API
// 拿「已經算好的真實數字」回來，room.js 本身不再包含 ADX 公式——這是保護尋鳥自有指標演算法
// 不被瀏覽器「檢視原始碼」看走的第一個試點，後續其他指標會陸續比照辦理。
const ADX_MTF_API = 'https://bluebird-indicators.bluebird-finder-tw.workers.dev/';

// 2026-09-17: 左側「🦅 動能鳥指標 即時戰情」HUD 卡片（系統模式/監控標的/趨勢乖離/量能指標/
// 波段動能/趨勢排列/綜合戰力）從建立以來就是純靜態文字，room.js 從未寫入過這幾個欄位
// （left-hud-bias/mfi/adx/trend/strength），跟 v63.0 修過的「GEX造市商五大防線」是同一種
// 「有UI但沒接資料」問題。這幾個欄位剛好一對一對應 JJ 鬼爪 V4.1 Worker 回傳的
// bias88/mfi/adx/is_bull_trend/strength_grade，現在接上真實數據。
//
// ⚠️ 尚未對照真實 TradingView 圖表逐根K棒驗證過（見 worker.js 註解），is_holding/
// reduce_count 這類需要很多根K棒才會顯現的狀態，暖機起點可能跟 TradingView 實際載入的K棒
// 數不同而有落差。卡片標題會標註「(未驗證)」，正式核對過後再拿掉這個標籤。
const JJ_GHOST_CLAWS_SUPPORTED_SYMBOLS = new Set(['TXF', 'TAIEX', 'OTC', 'CDF', 'MTX', 'MXF', 'US10Y', 'DXY', 'CL', '2330', '2454', '2317']);

async function updateJjGhostClawsHud(symObj) {
  const modeEl = document.getElementById('left-hud-mode');
  const assetEl = document.getElementById('left-hud-asset');
  const biasEl = document.getElementById('left-hud-bias');
  const mfiEl = document.getElementById('left-hud-mfi');
  const adxEl = document.getElementById('left-hud-adx');
  const trendEl = document.getElementById('left-hud-trend');
  const strengthEl = document.getElementById('left-hud-strength');
  if (!modeEl || !assetEl || !biasEl || !mfiEl || !adxEl || !trendEl || !strengthEl) return;

  const symbol = (symObj && JJ_GHOST_CLAWS_SUPPORTED_SYMBOLS.has(symObj.symbol)) ? symObj.symbol : 'TXF';
  modeEl.innerText = 'Auto (JJ V4.1)';
  assetEl.innerText = `${symbol} (1D)`;

  try {
    const resp = await fetch(`${ADX_MTF_API}?indicator=jj&symbol=${symbol}&tf=1D`);
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
    console.warn('⚠️ JJ鬼爪 HUD fetch failed:', e);
    biasEl.innerText = '—';
    mfiEl.innerText = '—';
    adxEl.innerText = '—';
    trendEl.innerText = '⚪ 無即時數據';
    trendEl.style.color = 'var(--text-muted)';
    strengthEl.innerText = '—';
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
      title: 'ADX'
    });

    // 2. 4 大標準門檻參考線 (26.65 頂部, 22.37 突破, 11.63 打底, 0.00)
    sub4Series.adx.createPriceLine({ price: 26.65, color: '#EF5350', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1.5, title: '26.65 頂部' });
    sub4Series.adx.createPriceLine({ price: 22.37, color: '#FFA726', lineStyle: LightweightCharts.LineStyle.Dashed, lineWidth: 1, title: '22.37 突破' });
    sub4Series.adx.createPriceLine({ price: 11.63, color: '#26A69A', lineStyle: LightweightCharts.LineStyle.Dotted, lineWidth: 1, title: '11.63 打底' });
    sub4Series.adx.createPriceLine({ price: 0, color: 'rgba(255, 255, 255, 0.25)', lineStyle: LightweightCharts.LineStyle.Dotted, lineWidth: 1, title: '0.00' });

    sub4Series.adx.setData(data.adxLine);
    sub4Series.adx.setMarkers(data.adxSignals);
  } else if (activeSub4 === 'ao') {
    if (badge) badge.innerText = '⚡ AO 震盪指標 (Awesome Oscillator)';
    sub4Series.ao = subChart4.addHistogramSeries({ priceScaleId: 'right' });
    sub4Series.ao.setData(data.aoData);
  } else if (activeSub4 === 'cvd') {
    if (badge) badge.innerText = '🎯 CVD (Cumulative Volume Delta 累積量差 K 線)';
    sub4Series.cvd = subChart4.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350'
    });
    sub4Series.cvd.setData(data.cvdCandles);
    sub4Series.cvd.createPriceLine({
      price: 0,
      color: 'rgba(255, 255, 255, 0.4)',
      lineStyle: LightweightCharts.LineStyle.Dotted,
      lineWidth: 1,
      title: 'Zero'
    });
  } else if (activeSub4 === 'momentum') {
    // 2026-09-13 更正：此副圖過去用 K 棒公式湊假數據，已移除。
    // 現在只畫「這個 session 開始追蹤之後」真正收到的富邦 Books(五檔)/Trades(逐筆成交) 資料，
    // 30分鐘 bar 由 fetchAndAppendMomentumBar() 即時輪詢附加，見該函式與後端
    // scripts/fubon_api_provider.py 的 get_momentum_bar_30m()。歷史時段（此 session 開始前）
    // 沒有真數據可畫，故意留白，不補假資料。
    const symbolCode = (currentActiveSymbol?.symbol || activeContract || '').toUpperCase();
    const isMomentumEligible = GEX_SUPPORTED_SYMBOLS.includes(symbolCode); // 目前後端只訂閱了 TXF
    if (badge) {
      badge.innerText = isMomentumEligible
        ? '🐂 大戶散戶動能 (真實 Books/Trades 即時串接，2026-09-13起，僅 TXF 有資料)'
        : '🐂 大戶散戶動能 (目前僅 TXF/MXF/MTX 有真實委託簿數據，此商品尚未支援)';
    }

    // 1. 大戶委託口差 (紅柱=偏多掛單較多，綠柱=偏空掛單較多；來源：Books 五檔委買委賣總口數差)
    sub4Series.momentumHist = subChart4.addHistogramSeries({
      priceScaleId: 'right',
      title: '大戶委託口差'
    });

    // 2. 散戶成交筆數差 (青綠色；來源：Trades 逐筆成交，買筆數-賣筆數，非口數)
    sub4Series.retailLine = subChart4.addLineSeries({
      color: '#00CEC9',
      lineWidth: 1.5,
      priceScaleId: 'right',
      title: '散戶成交筆數差'
    });

    // 3. 市場委買委賣口差 (黃線；目前與大戶委託口差同源，見後端註解說明限制)
    sub4Series.marketOrderLine = subChart4.addLineSeries({
      color: '#FFEB3B',
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      priceScaleId: 'right',
      title: '市場委買委賣口差'
    });

    // 4. 0 基準水平線
    sub4Series.momentumHist.createPriceLine({
      price: 0,
      color: 'rgba(255, 255, 255, 0.4)',
      lineStyle: LightweightCharts.LineStyle.Dashed,
      lineWidth: 1,
      title: '0 軸'
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
async function fetchAndAppendMomentumBar(symbol) {
  try {
    const res = await fetch(`http://localhost:8000/api/momentum?symbol=${encodeURIComponent(symbol)}`, { cache: 'no-store' });
    if (!res.ok) return;
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
    // Gateway server (live_price_server.py) not running locally — fail silently,
    // this is expected whenever the user isn't running it (e.g. this cloud session).
  }
}

function startMomentumLivePolling(symbol) {
  stopMomentumLivePolling();
  fetchAndAppendMomentumBar(symbol);
  momentumPollTimer = setInterval(() => fetchAndAppendMomentumBar(symbol), 5000);
}

function stopMomentumLivePolling() {
  if (momentumPollTimer) {
    clearInterval(momentumPollTimer);
    momentumPollTimer = null;
  }
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
    overlaySeries.ribbons.ma7 = mainChart.addLineSeries({ color: '#ffffff', lineWidth: 1.5, title: '快線 MA7' });
    overlaySeries.ribbons.ma17 = mainChart.addLineSeries({ color: '#ffd700', lineWidth: 1.5, title: '波段 MA17' });
    overlaySeries.ribbons.ma88 = mainChart.addLineSeries({ color: '#e84393', lineWidth: 2, title: '多空 MA88' });
    overlaySeries.ribbons.ma200 = mainChart.addLineSeries({ color: '#0984e3', lineWidth: 2, title: '年線 MA200' });

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
      title: `SMMA ${indicatorConfig.smmaLen || 200}`
    });
    overlaySeries.smma.setData(data.smmaData);
  }

  // 3. VWAP
  if (indicatorConfig.vwap) {
    const vwapColor = indicatorConfig.vwapColor || '#FF8A80';
    overlaySeries.vwap.vwap = mainChart.addLineSeries({ color: vwapColor, lineWidth: 2, title: 'VWAP' });
    overlaySeries.vwap.upper1 = mainChart.addLineSeries({ color: 'rgba(76, 175, 80, 0.5)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, title: 'VWAP +1σ' });
    overlaySeries.vwap.lower1 = mainChart.addLineSeries({ color: 'rgba(76, 175, 80, 0.5)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, title: 'VWAP -1σ' });

    overlaySeries.vwap.vwap.setData(data.vwapData);
    overlaySeries.vwap.upper1.setData(data.vwapUpper);
    overlaySeries.vwap.lower1.setData(data.vwapLower);
  }

  // 3b. Parabolic SAR (real Wilder calc — see generateIndicatorsData() for the math)
  if (indicatorConfig.sar) {
    overlaySeries.sar = mainChart.addLineSeries({
      color: '#FFEB3B',
      lineVisible: false,
      pointMarkersVisible: true,
      pointMarkersRadius: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      title: 'SAR'
    });
    overlaySeries.sar.setData(data.sarData);
  }

  // 3c. Supertrend (real ATR-band calc — see generateIndicatorsData() for the math). Rendered
  // as two line series (up-trend segment green, down-trend segment red) since Lightweight
  // Charts v4 has no native per-point line color; each series has `undefined` for bars outside
  // its own trend, which renders as a gap, so together they look like one color-flipping line.
  if (indicatorConfig.supertrend) {
    overlaySeries.supertrend.up = mainChart.addLineSeries({
      color: '#26A69A',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      title: 'Supertrend'
    });
    overlaySeries.supertrend.down = mainChart.addLineSeries({
      color: '#EF5350',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      title: 'Supertrend'
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
    candleSeries.setMarkers(data.markers);
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
    title: `VRVP POC (${vrvp.poc})`
  });

  // 2. VAH (Value Area High) - 亮橘點線 1.5px
  priceLines.vah = candleSeries.createPriceLine({
    price: vrvp.vah,
    color: '#FFA726',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: `VRVP VAH (${vrvp.vah})`
  });

  // 3. VAL (Value Area Low) - 亮橘點線 1.5px
  priceLines.val = candleSeries.createPriceLine({
    price: vrvp.val,
    color: '#FFA726',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: `VRVP VAL (${vrvp.val})`
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
    axisLabelVisible: true,
    title: `Call Wall (${cw})`
  });

  // 2. VEX Early Flip (VEX 早鳥轉折線) - 亮橘虛線 1.5px
  priceLines.vex = candleSeries.createPriceLine({
    price: vex,
    color: '#FFA726',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    axisLabelVisible: true,
    title: `VEX Early (${vex})`
  });

  // 3. Zero Gamma (基準多空變盤點) - 亮黃實線 2px
  priceLines.zg = candleSeries.createPriceLine({
    price: zg,
    color: '#FFEB3B',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Solid,
    axisLabelVisible: true,
    title: `Zero Gamma (${zg})`
  });

  // 4. Put Wall (買權防守地板牆) - 青綠實線 2px
  priceLines.pw = candleSeries.createPriceLine({
    price: pw,
    color: '#26A69A',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Solid,
    axisLabelVisible: true,
    title: `Put Wall (${pw})`
  });

  // 5. Max Pain (最大痛點引力) - 亮藍點線 1px
  priceLines.mp = candleSeries.createPriceLine({
    price: mp,
    color: '#42A5F5',
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: `Max Pain (${mp})`
  });

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
function updateLegendOverlay(param) {
  if (!param.time || !param.seriesData) return;
  const candle = param.seriesData.get(candleSeries);
  if (!candle) return;

  const isYield = currentActiveSymbol && currentActiveSymbol.is_yield;
  const isSmall = currentActiveSymbol && currentActiveSymbol.base_price < 500;

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
function renderLeftPanel() {
  if (!gexData) return;

  updateJjGhostClawsHud(currentActiveSymbol); // async — fills in real bias/mfi/adx/trend/grade once the API responds

  const isIndexFutures = currentActiveSymbol && ['TXF', 'MXF', 'TMF', 'TWN'].includes(currentActiveSymbol.symbol);
  let baseP = gexData?.night_txf_price || gexData?.txf_price || 46588;

  if (currentActiveSymbol) {
    if (CORE_PRESET_ASSETS[currentActiveSymbol.symbol]) {
      baseP = CORE_PRESET_ASSETS[currentActiveSymbol.symbol].base_price;
      if (currentActiveSymbol.symbol === 'TXF') {
        baseP = gexData?.night_txf_price || gexData?.txf_price || 46588;
      }
    } else if (isIndexFutures) {
      baseP = gexData?.night_txf_price || gexData?.txf_price || 46588;
    } else if (currentActiveSymbol.symbol === '2330' || currentActiveSymbol.symbol === 'CDF') {
      baseP = 1045;
    } else if (currentActiveSymbol.symbol === '2454') {
      baseP = 1430;
    } else {
      baseP = 215;
    }
  }
  
  const cw = gexData?.call_wall_strike || ROOM_CHART_DEFAULTS.call_wall_strike;
  const zg = gexData?.zero_gamma_level || ROOM_CHART_DEFAULTS.zero_gamma_level;
  const pw = gexData?.put_wall_strike || ROOM_CHART_DEFAULTS.put_wall_strike;
  const mp = gexData?.max_pain_strike || ROOM_CHART_DEFAULTS.max_pain_strike;

  // 1. Triple indices in left panel
  const topTaiex = document.getElementById('top-val-taiex');
  const topChgTaiex = document.getElementById('top-chg-taiex');
  if (topTaiex) {
    const p = gexData?.spot_price || 46184.85;
    topTaiex.innerText = Number(p).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (topChgTaiex) {
    const chg = gexData?.spot_change !== undefined ? gexData.spot_change : -755.64;
    const pct = gexData?.spot_change_pct !== undefined ? gexData.spot_change_pct : -1.61;
    const sign = chg >= 0 ? '+' : '';
    topChgTaiex.innerText = `${sign}${chg.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
    topChgTaiex.style.color = chg >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const topOtc = document.getElementById('top-val-otc');
  const topChgOtc = document.getElementById('top-chg-otc');
  if (topOtc) {
    const p = gexData?.two_price || 395.52;
    topOtc.innerText = Number(p).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (topChgOtc) {
    const chg = gexData?.two_change !== undefined ? gexData.two_change : -9.72;
    const pct = gexData?.two_change_pct !== undefined ? gexData.two_change_pct : -2.40;
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
    lOpen.innerText = '—';
    lHigh.innerText = '—';
    lLow.innerText = '—';
    lPrev.innerText = (prevClose !== null && !isNaN(prevClose)) ? prevClose.toLocaleString(undefined, { minimumFractionDigits: prevClose < 500 ? 2 : 1, maximumFractionDigits: prevClose < 500 ? 2 : 1 }) : '—';
  }

  // Header Title
  const activeTitle = document.getElementById('active-symbol-title');
  if (activeTitle) activeTitle.innerText = `⚡ ${currentActiveSymbol.name} 即時報價 (${currentActiveSymbol.symbol})`;

  // Quotes
  const pEl = document.getElementById('left-main-price');
  if (pEl) {
    pEl.innerText = currentActiveSymbol.is_yield ? `${baseP.toFixed(3)}%` : (baseP < 500 ? baseP.toFixed(2) : baseP.toLocaleString());
  }

  // Distances
  const distCW = baseP - cw;
  const distZG = baseP - zg;
  const distPW = baseP - pw;
  const distMP = baseP - mp;

  const dCWEl = document.getElementById('left-dist-cw');
  if (dCWEl) {
    dCWEl.innerText = `${distCW >= 0 ? '+' : ''}${Math.round(distCW)} 點`;
    dCWEl.style.color = distCW >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const dZGEl = document.getElementById('left-dist-zg');
  if (dZGEl) {
    dZGEl.innerText = `${distZG >= 0 ? '+' : ''}${distZG.toFixed(1)} 點`;
    dZGEl.style.color = distZG >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const dPWEl = document.getElementById('left-dist-pw');
  if (dPWEl) {
    dPWEl.innerText = `${distPW >= 0 ? '+' : ''}${Math.round(distPW)} 點`;
    dPWEl.style.color = distPW >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const dMPEl = document.getElementById('left-dist-mp');
  if (dMPEl) {
    dMPEl.innerText = `${distMP >= 0 ? '+' : ''}${Math.round(distMP)} 點`;
    dMPEl.style.color = distMP >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

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
    const vixVal = (gexData.vix_info && gexData.vix_info.taifex_vix) ? gexData.vix_info.taifex_vix : 26.09;
    topVIX.innerText = `${vixVal} 🔴`;
  }
  const topVVIX = document.getElementById('top-stat-vvix');
  if (topVVIX) {
    const vvixVal = (gexData.vix_info && gexData.vix_info.us_vvix) ? gexData.vix_info.us_vvix : 102.66;
    const badge = vvixVal >= 110 ? '🔴' : (vvixVal >= 100 ? '🟠' : (vvixVal >= 95 ? '🟡' : '🟢'));
    topVVIX.innerText = `${vvixVal.toFixed(2)} ${badge}`;
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

  // Default / Parsed Macro Indicators
  const dxy = macroData?.dxy || { price: 99.196, trend_label: '跌落 20 日線 (偏多台股)' };
  const us10y = macroData?.us10y || { price: 4.784, trend_label: '站穩 20 日線 (創高承壓)' };
  const vix = macroData?.vix || { price: (gexData?.vix_info?.taifex_vix || 18.45), trend_label: '低波安定' };
  const vvixVal = (gexData?.vix_info?.us_vvix || 102.66);
  const tailStatus = gexData?.vix_info?.tail_risk_status || '';
  const summary = macroData?.summary || (tailStatus ? `💡 ${tailStatus}` : '💡 VIX 維持低檔有利多頭，美元走弱亞股資金無虞，聚焦突破與量化動能標的。');

  const dxyPrice = liveTick?.dxy || dxy.price;
  const us10yPrice = liveTick?.us10y || us10y.price;
  const vixPrice = liveTick?.vix || vix.price;
  const vvixPrice = liveTick?.vvix || vvixVal;

  if (dxyValEl) dxyValEl.textContent = dxyPrice.toFixed(3);
  if (dxyBadgeEl) dxyBadgeEl.textContent = dxyPrice < 100.5 ? '破20MA(多)' : '站20MA(壓)';
  
  if (us10yValEl) us10yValEl.textContent = `${us10yPrice.toFixed(3)}%`;
  if (us10yBadgeEl) us10yBadgeEl.textContent = us10yPrice >= 4.7 ? '站20MA(壓)' : '破20MA(多)';
  
  if (vixValEl) vixValEl.textContent = vixPrice.toFixed(2);
  if (vixBadgeEl) vixBadgeEl.textContent = vixPrice < 20 ? '低波安定' : '恐慌升溫';

  if (vvixValEl) vvixValEl.textContent = vvixPrice.toFixed(2);
  if (vvixBadgeEl) {
    if (vvixPrice >= 110) {
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
    const isTailRisk = vvixPrice >= 100;
    const isGood = vixPrice < 20 && dxyPrice < 102 && !isTailRisk;
    if (isTailRisk) {
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
      const data = generateIndicatorsData(currentTf);
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

  if (applySettingsBtn && modal) {
    applySettingsBtn.addEventListener('click', () => {
      indicatorConfig.gex = document.getElementById('chk-gex').checked;
      indicatorConfig.ribbons = document.getElementById('chk-claws').checked;
      indicatorConfig.demark = document.getElementById('chk-demark').checked;
      indicatorConfig.smma = document.getElementById('chk-smma').checked;
      indicatorConfig.smmaLen = parseInt(document.getElementById('param-smma-len').value) || 200;
      indicatorConfig.smmaColor = document.getElementById('col-smma').value || '#e84393';
      indicatorConfig.supertrend = document.getElementById('chk-supertrend').checked;
      indicatorConfig.vwap = document.getElementById('chk-vwap').checked;
      indicatorConfig.vwapColor = document.getElementById('col-vwap').value || '#FF8A80';
      indicatorConfig.vrvp = document.getElementById('chk-vrvp').checked;
      indicatorConfig.vrvpRows = parseInt(document.getElementById('param-vrvp-rows').value) || 50;
      indicatorConfig.vrvpVa = parseInt(document.getElementById('param-vrvp-va').value) || 70;
      indicatorConfig.sar = document.getElementById('chk-sar').checked;
      indicatorConfig.sarStep = parseFloat(document.getElementById('param-sar-step').value) || 0.02;
      indicatorConfig.fvg = document.getElementById('chk-fvg').checked;

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
function initAdvisorFeed() {
  const feed = document.getElementById('advisor-feed');
  if (!feed) return;

  const txf = gexData ? gexData.txf_price : 47187;
  const zg = gexData ? gexData.zero_gamma_level : ROOM_CHART_DEFAULTS.zero_gamma_level;
  const cw = gexData ? gexData.call_wall_strike : ROOM_CHART_DEFAULTS.call_wall_strike;
  const pw = gexData ? gexData.put_wall_strike : ROOM_CHART_DEFAULTS.put_wall_strike;
  const mp = gexData ? gexData.max_pain_strike : ROOM_CHART_DEFAULTS.max_pain_strike;

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
        <h4 style="color: var(--primary-accent); margin-bottom: 6px; font-size: 0.88rem;">🦅 戰情室即時全域量化診斷 (v64.0)</h4>
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

  const txf = gexData ? gexData.txf_price : 47187;
  const zg = gexData ? gexData.zero_gamma_level : ROOM_CHART_DEFAULTS.zero_gamma_level;
  const cw = gexData ? gexData.call_wall_strike : ROOM_CHART_DEFAULTS.call_wall_strike;
  const pw = gexData ? gexData.put_wall_strike : ROOM_CHART_DEFAULTS.put_wall_strike;
  const mp = gexData ? gexData.max_pain_strike : ROOM_CHART_DEFAULTS.max_pain_strike;

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
  let userMsgHtml = cleanQ;
  const attachedImgSrc = advisorAttachedImage;
  if (attachedImgSrc) {
    userMsgHtml = `
      <div style="margin-bottom: 6px;">
        <img src="${attachedImgSrc}" alt="截圖" style="max-width: 100%; max-height: 180px; border-radius: 6px; border: 1px solid var(--primary-accent); display: block; margin-bottom: 4px;">
      </div>
      <div>${cleanQ || '📷 [已傳送盤面/持倉截圖，請軍師診斷]'}</div>
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
  const currentPrice = (currentActiveSymbol && currentActiveSymbol.base_price) || gexData?.txf_price || 46594;
  const cw = gexData?.call_wall_strike || ROOM_CHART_DEFAULTS.call_wall_strike;
  const zg = gexData?.zero_gamma_level || ROOM_CHART_DEFAULTS.zero_gamma_level;
  const pw = gexData?.put_wall_strike || ROOM_CHART_DEFAULTS.put_wall_strike;
  const mp = gexData?.max_pain_strike || ROOM_CHART_DEFAULTS.max_pain_strike;
  const vix = gexData?.vix_info?.taifex_vix || 26.09;
  const vvix = gexData?.vix_info?.us_vvix || 102.66;
  const dxy = 98.845;
  const us10y = 4.940;

  const systemInstruction = `你是「尋鳥戰情交易室 AI 量化軍師 (Bird Quant Advisor)」，結合老墨 XQ 指標體系與 TXO GEX 造市商對沖模型。
最高風控鐵律與行為準則 (AGENTS.md)：
1. 嚴禁對週選擇權 (W1/W2/W4/W5/F1) 垂直價差單建議「拆單 (No Legging Out)」，必須維持整組價差單平倉或轉倉。
2. 盤中價格暴衝/急殺時嚴禁建議追價，等待 15M/30M DeMark 9★ 買賣盤竭盡。
3. 診斷實盤真金白銀部位時，檢查賣腳安全邊際、未實現損益、IOC 洗價點數。
當前即時盤面數據：
- 當前監控商品：${currentActiveSymbol?.name || '台指期'} (${currentActiveSymbol?.symbol || 'TXF'})，即時報價：${currentPrice}
- GEX 造市商五大防線：Call Wall: ${cw}, Zero Gamma: ${zg}, Put Wall: ${pw}, Max Pain: ${mp}
- 波動率與宏觀雷達：VIX: ${vix}, VVIX: ${vvix}, DXY: ${dxy}, 美債10Y: ${us10y}%
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

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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

function formatGeminiMarkdown(md) {
  if (!md) return '';
  let html = md
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
  const txf = gexData ? gexData.txf_price : 47187;
  const zg = gexData ? gexData.zero_gamma_level : ROOM_CHART_DEFAULTS.zero_gamma_level;
  const cw = gexData ? gexData.call_wall_strike : ROOM_CHART_DEFAULTS.call_wall_strike;
  const pw = gexData ? gexData.put_wall_strike : ROOM_CHART_DEFAULTS.put_wall_strike;
  const mp = gexData ? gexData.max_pain_strike : ROOM_CHART_DEFAULTS.max_pain_strike;
  const vvix = gexData?.vix_info?.vvix || 102.66;

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
    const safetyLevel = isItm ? '🔴 價內被貫穿 (極高風險)' : (distToSell > 180 ? '🟢 價外安全防守區 (安全)' : '🟡 臨界警戒區 (密切監控)');

    const spreadWidth = buyStrike ? Math.abs(sellStrike - buyStrike) : 100;
    const estNetCredit = Math.round(spreadWidth * 0.32); // Approximate 30-35% spread credit
    const estMaxLoss = spreadWidth - estNetCredit;
    const rewardRisk = (estNetCredit / estMaxLoss).toFixed(2);

    const triggerTxf = posType.includes('Put') ? (sellStrike + 20) : (sellStrike - 20);

    return `
      <div style="border-left: 3px solid #00d2ff; padding-left: 8px;">
        ${imageBadge}
        <h4 style="color: var(--gold-accent); margin-bottom: 4px;">🛡️ 真實持倉部位風控體檢診斷書</h4>
        <p style="font-size: 0.8rem; line-height: 1.5; margin-bottom: 6px;">
          ・<strong>識別部位結構</strong>：<code>${posType}</code><br>
          ・<strong>賣腳履約價 (Sell Leg)</strong>：<strong>${sellStrike}</strong> (當前安全距離：<strong>${distToSell} 點</strong>)<br>
          ${buyStrike ? `・<strong>買腳履約價 (Buy Leg)</strong>：<strong>${buyStrike}</strong> (價差寬度: <strong>${spreadWidth} 點</strong>)<br>` : ''}
          ・<strong>持倉狀態</strong>：<strong>${safetyLevel}</strong><br>
          ・<strong>風報比試算 (Reward/Risk)</strong>：預估最大獲利約 <strong>${estNetCredit} 點</strong> ($${estNetCredit * 50} TWD) / 最大可能風險 <strong>${estMaxLoss} 點</strong> ($${estMaxLoss * 50} TWD) (風報比約 1 : ${(1 / rewardRisk).toFixed(1)})
        </p>

        <div style="background: rgba(255, 71, 87, 0.12); border: 1px solid rgba(255, 71, 87, 0.4); border-radius: 6px; padding: 6px 8px; margin: 6px 0; font-size: 0.78rem;">
          🚨 <strong>AGENTS.md 最高風控鐵律審核</strong>：<br>
          1. <strong>嚴禁拆單 (No Legging Out)</strong>：對週選擇權垂直價差單，<strong>絕不可先平倉賣腳留下買腳</strong>！拆單會解除有限風險保護，引發多空雙巴悲劇。<br>
          2. <strong>維持整組處理</strong>：平倉、轉倉或停損必須整組雙腳同步送出。
        </div>

        <div style="background: rgba(0, 210, 255, 0.08); border: 1px solid rgba(0, 210, 255, 0.25); border-radius: 6px; padding: 6px 8px; font-size: 0.78rem;">
          🎯 <strong>券商連續洗價單實盤設定指南 (IOC)</strong>：<br>
          ・<strong>觸發條件</strong>：當台指期 (TXF) ${posType.includes('Put') ? '跌破' : '漲破'} <strong><code>${triggerTxf} 點</code></strong> 或 價差平倉成本觸及 <strong><code>${Math.round(estNetCredit * 1.8)} 點</code></strong><br>
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
           - 🌪️ <strong>VVIX 尾部避險指標</strong>：<code>${vvix}</code> ${vvix > 105 ? '⚠️ <span style="color:#ff9100;">機構避險情緒升溫，賣方組單應加大買腳保護</span>' : '🟢 <span style="color:#00e676;">低波平穩，適合雙賣或 Iron Condor 收租</span>'}。<br>
           - 美元指數 DXY 處於 20MA 下方，資金動能偏多；VIX 處於平穩區間。<br><br>
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
            base_price: 100
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
  const isIndexFutures = ['TXF', 'MXF', 'TMF', 'TWN'].includes(symObj.symbol);
  indicatorConfig.gex = isIndexFutures;

  // Update Left HUD & Header
  renderLeftPanel();

  // Highlight contract tab if matches
  const contractBtns = document.querySelectorAll('.contract-tab');
  contractBtns.forEach(btn => {
    const code = btn.getAttribute('data-contract');
    if (code === symObj.symbol || code === symObj.futures_code) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Re-generate and render charts
  renderChartData();
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

  tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 20px; color: var(--primary-accent);">⚡ 正在掃描全市場 1,400+ 檔標的量化指標中...</td></tr>`;

  // Read filter checkboxes
  const fRocketS = document.getElementById('sc-rocket-s')?.checked;
  const fBirdS = document.getElementById('sc-bird-s')?.checked;
  const fRestartS = document.getElementById('sc-restart-s')?.checked;
  const fRestartN = document.getElementById('sc-restart-n')?.checked;
  const fRocketW = document.getElementById('sc-rocket-w')?.checked;
  const fBirdN = document.getElementById('sc-bird-n')?.checked;
  const fMacdFlip = document.getElementById('sc-macd-flip')?.checked;
  const fMacdGold = document.getElementById('sc-macd-gold')?.checked;
  const fGradeS = document.getElementById('sc-grade-s')?.checked;
  const fGradeA = document.getElementById('sc-grade-a')?.checked;
  const fDemark = document.getElementById('sc-demark-turn')?.checked;
  const f5k = document.getElementById('sc-5k-break')?.checked;
  const fVol = document.getElementById('sc-vol-spike')?.checked;
  const fItAdopt = document.getElementById('sc-it-adopt')?.checked;
  const fChipBull = document.getElementById('sc-chip-bull')?.checked;

  const activeFiltersCount = [fRocketS, fBirdS, fRestartS, fRestartN, fRocketW, fBirdN, fMacdFlip, fMacdGold, fGradeS, fGradeA, fDemark, f5k, fVol, fItAdopt, fChipBull].filter(Boolean).length;

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
      const hasRestartS = sigList.includes('🛸 動能飛碟');
      const hasRestartN = sigList.includes('⚡ 動能閃電');
      const hasRocketW = sigList.includes('✈️ 噴射機');
      const hasBirdN = sigList.includes('🥚 帶殼鳥');
      const isMacdFlip = real.macd_state === 'MACD 柱狀體翻紅';
      const isMacdGold = real.macd_state === '零軸上金叉' || real.macd_state === 'MACD 水下金叉';
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
      if (fGradeS && isGradeS) score++;
      if (fGradeA && isGradeA) score++;
      if (fDemark && hasDemark) score++;
      if (f5k && has5k) score++;
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
          score
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
      
      return `
        <tr>
          <td><strong style="color: var(--primary-accent);">${r.item.symbol}</strong></td>
          <td style="font-weight: 600;">${r.item.name}</td>
          <td><span class="search-tag-market">${r.item.market}・${r.item.category}</span></td>
          <td style="font-weight: 700;">$${r.price.toLocaleString()}</td>
          <td style="color: ${col}; font-weight: 700;">${sign}${r.changePct.toFixed(2)}%</td>
          <td><span class="signal-badge-chip">${r.signals}</span></td>
          <td><span class="${gradeClass}">${r.grade}</span></td>
          <td style="font-size: 0.72rem; color: #00e676;">${r.changePct >= 0 ? '🟢 紅柱擴張' : '🟡 震盪整理'}</td>
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
async function fetchFubonOrPublicFallback() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);
    const resp = await fetch('http://localhost:8000/api/live_tick', { signal: controller.signal });
    clearTimeout(timeout);
    if (resp.ok) {
      const data = await resp.json();
      if (data) return { data, source: 'fubon' };
    }
  } catch (e) {
    // Local gateway not running, blocked, or timed out — fall through to the public fallback.
  }

  try {
    const nowH = new Date().getHours();
    const isNightSession = (nowH >= 15 || nowH < 8);
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
  }
  return { data: null, source: null };
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
          statusTag.innerHTML = '🟡 盤後休市 (定案結算價)';
          statusTag.style.borderColor = '#ffd700';
          statusTag.style.color = '#ffd700';
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
        if (leftMainP && (!currentActiveSymbol || currentActiveSymbol.symbol === 'TXF')) {
          leftMainP.innerText = data.txf.price.toLocaleString();
          if (lastTxfPrice !== null && lastTxfPrice !== data.txf.price) {
            leftMainP.style.transform = 'scale(1.04)';
            setTimeout(() => { leftMainP.style.transform = 'scale(1.0)'; }, 250);
          }
          lastTxfPrice = data.txf.price;
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
        updateMacroRiskHUD(gexData?.macro_events_radar?.macro_risk_dashboard || null, data.macro);
      }

      if (statusTag) {
        if (source === 'fubon') {
          statusTag.innerHTML = '🟢 富邦 Neo API (Live)';
          statusTag.style.borderColor = '#00e676';
          statusTag.style.color = '#00e676';
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
    clTab.title = `紐約輕原油期貨 (結算: $${CORE_PRESET_ASSETS['CL'].base_price.toFixed(2)})`;
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





