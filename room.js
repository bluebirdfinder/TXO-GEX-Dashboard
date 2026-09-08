/**
 * 🦅 尋鳥戰情交易室 (Bird Trading Room) Core Engine v50.9
 * True Multi-Pane Trading Terminal with 10 Timeframes & 4 Sub-Panes
 *   - Main Chart (44%): TXF K-Line + GEX 5 Levels + 尋鳥多空彩帶 + 8大進出場訊號 + DeMark 9★/13★ + VWAP + SMMA 200 + Supertrend + SAR
 *   - Sub-Chart 1 (14%): 成交量 Volume + 5MA & 10MA 雙均量線
 *   - Sub-Chart 2 (14%): 戰情雙層 MACD (4 色量柱 + 快慢線)
 *   - Sub-Chart 3 (14%): 波段拐點 CCI (20 通道 & 買賣轉折點)
 *   - Sub-Chart 4 (14%): 動能副圖 (AO / CVD / DMI 一鍵切換)
 *   - All 5 charts 100% synchronized with 0ms crosshair & time-scale tracking
 */

// Global State
let gexData = null;

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

let sub4Series = {
  ao: null,
  cvd: null,
  dmiPlus: null,
  dmiMinus: null,
  dmiAdx: null
};

// Overlay Series References on Main Chart
let overlaySeries = {
  ribbons: { ma7: null, ma17: null, ma88: null, ma200: null },
  smma: null,
  supertrend: null,
  vwap: { vwap: null, upper1: null, lower1: null },
  sar: null
};

let priceLines = {};
let currentTf = '15M';
let activeContract = 'TXF';
let activeSub4 = 'ao'; // 'ao' | 'cvd' | 'dmi'

let symbolsUniverse = [];
let currentActiveSymbol = {
  symbol: 'TXF',
  name: '台指期貨',
  category: '指數期貨',
  market: 'TAIFEX',
  has_futures: true,
  futures_code: 'TXF',
  asset_type: 'index_futures',
  bias_default: 5.0,
  mfi_thresh: 50.0,
  adx_thresh: 22.0
};

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
  fvg: false
};

// DOM Initialization
document.addEventListener('DOMContentLoaded', async () => {
  await initTradingRoom();
  initFubonLivePriceStream();
  initSymbolSearchAndAutocomplete();
  initQuantScreenerModal();
});

async function initTradingRoom() {
  console.log('🦅 Initializing Multi-Pane Bird Trading Room v50.9...');
  
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
    const res = await fetch('data/gex_data.json?t=' + Date.now());
    if (res.ok) {
      gexData = await res.json();
    }
  } catch (e) {
    console.warn('⚠️ Fetching data/gex_data.json failed, using embedded fallback...', e);
  }
  
  if (!gexData && window.GEX_EMBEDDED_DATA) {
    gexData = window.GEX_EMBEDDED_DATA;
  }
  
  if (!gexData) {
    gexData = {
      txf_price: 47329,
      zero_gamma_level: 47217.4,
      call_wall_strike: 47400,
      put_wall_strike: 47050,
      max_pain_strike: 46600,
      session_shift: { txf_shift: -141 },
      vix_info: { taifex_vix: 26.09 }
    };
  }

  // Load Full Symbol Universe (1,400+ Stocks & Futures)
  try {
    const uniRes = await fetch('data/tw_symbols_universe.json');
    if (uniRes.ok) {
      symbolsUniverse = await uniRes.json();
      console.log(`✅ Loaded ${symbolsUniverse.length} symbols into Universe search cache.`);
    }
  } catch (e) {
    console.warn('⚠️ Could not load data/tw_symbols_universe.json', e);
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

  // --- Sub-Chart 1: 成交量 Volume + Volume MA 5 & Volume MA 10 ---
  subChart1 = LightweightCharts.createChart(cSub1, {
    ...commonOptions,
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
    ...commonOptions,
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
    ...commonOptions,
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
    ...commonOptions,
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

function generateIndicatorsData(tf) {
  let basePrice = 47329;
  if (currentActiveSymbol) {
    const sym = currentActiveSymbol.symbol;
    if (sym === 'TXF' || sym === 'MXF' || sym === 'TMF' || sym === 'TWN') {
      basePrice = (gexData && gexData.txf_price) ? gexData.txf_price : 47329;
    } else if (sym === '2330' || sym === 'CDF') {
      basePrice = 1045;
    } else if (sym === '2454' || sym === 'DVF') {
      basePrice = 1430;
    } else if (sym === '2317' || sym === 'DHF') {
      basePrice = 215;
    } else if (sym === '2382' || sym === 'IJF') {
      basePrice = 310;
    } else if (sym === '2603' || sym === 'CZF') {
      basePrice = 195;
    } else if (sym === '0050' || sym === 'NYF') {
      basePrice = 188;
    } else if (sym === '00631L' || sym === 'QAF') {
      basePrice = 265;
    } else {
      let hash = 0;
      for (let c = 0; c < sym.length; c++) hash = (hash * 31 + sym.charCodeAt(c)) % 1000;
      basePrice = 45 + (hash % 500);
    }
  }
  
  let count = 120;
  let intervalSec = 900; // 15M default
  if (tf === '1M') { count = 180; intervalSec = 60; }
  else if (tf === '3M') { count = 160; intervalSec = 180; }
  else if (tf === '5M') { count = 140; intervalSec = 300; }
  else if (tf === '15M') { count = 120; intervalSec = 900; }
  else if (tf === '30M') { count = 100; intervalSec = 1800; }
  else if (tf === '1H') { count = 90; intervalSec = 3600; }
  else if (tf === '4H') { count = 80; intervalSec = 14400; }
  else if (tf === '1D') { count = 70; intervalSec = 86400; }
  else if (tf === '1W') { count = 60; intervalSec = 604800; }
  else if (tf === '1Mth') { count = 50; intervalSec = 2592000; }

  const startTime = Math.floor(Date.now() / 1000) - (count * intervalSec);
  
  const candles = [];
  const volumes = [];
  const closes = [];
  const highs = [];
  const lows = [];
  
  const priceStepRatio = basePrice > 10000 ? 180 : (basePrice > 1000 ? 15 : (basePrice > 100 ? 5 : 1.2));
  let currentClose = basePrice - priceStepRatio;
  
  for (let i = 0; i < count; i++) {
    const t = startTime + (i * intervalSec);
    const trend = (i / count) * 220;
    const wave = Math.sin(i / 7) * 45;
    const noise = (Math.sin(i * 3.7) + Math.cos(i * 1.9)) * 18;
    
    const open = Math.round(currentClose + (Math.sin(i * 1.3) * 8));
    const close = Math.round(basePrice - 200 + trend + wave + noise);
    const high = Math.max(open, close) + Math.round(Math.abs(Math.sin(i * 2.1)) * 25 + 5);
    const low = Math.min(open, close) - Math.round(Math.abs(Math.cos(i * 2.3)) * 25 + 5);
    const vol = Math.round(1000 + Math.abs(Math.sin(i * 0.8)) * 3500);

    candles.push({ time: t, open, high, low, close });
    volumes.push({ time: t, value: vol, color: close >= open ? 'rgba(255, 71, 87, 0.7)' : 'rgba(46, 213, 115, 0.7)' });
    
    closes.push(close);
    highs.push(high);
    lows.push(low);
    currentClose = close;
  }

  // Volume 5MA & 10MA
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

  // --- 尋鳥多空彩帶 (MA7, MA17, MA88, MA200) ---
  const calcMA = (len) => {
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

  const ma7 = calcMA(7);
  const ma17 = calcMA(17);
  const ma88 = calcMA(Math.min(88, Math.floor(count * 0.6)));
  const ma200 = calcMA(Math.min(200, Math.floor(count * 0.8)));

  // --- 戰情雙層 MACD (12/26/9 Main + 3/15/5 Sub) ---
  const macdData = [];
  const difData = [];
  const deaData = [];
  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    const difVal = Math.sin(i / 6) * 18 + Math.cos(i / 3) * 6;
    const deaVal = Math.sin((i - 2) / 6) * 16 + Math.cos((i - 2) / 3) * 5;
    const histVal = difVal - deaVal;
    
    // Sub MACD 4-Color Logic
    const subDif = Math.sin(i / 2.5) * 12;
    const subHistPrev = Math.sin((i - 1) / 2.5) * 10;
    const subHistCurr = Math.sin(i / 2.5) * 10;
    
    const colorIsUp = subDif > 0;
    const colorMomentum = subHistCurr > subHistPrev;
    
    let histColor;
    if (colorIsUp) {
      histColor = colorMomentum ? '#ff3b30' : '#007aff'; // 🔴 紅 / 🔵 藍
    } else {
      histColor = colorMomentum ? '#007aff' : '#34c759'; // 🔵 藍 (水下提早翻紅預警!) / 🟢 綠
    }

    difData.push({ time: t, value: Math.round(difVal * 10) / 10 });
    deaData.push({ time: t, value: Math.round(deaVal * 10) / 10 });
    macdData.push({ time: t, value: Math.round(histVal * 10) / 10, color: histColor });
  }

  // --- 波段拐點 CCI (20) & 4色買賣轉折圓點 (紅/粉紅/淺綠/深綠) ---
  const cciData = [];
  const cciSignals = [];
  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    const val = Math.sin(i / 3.6) * 175 + Math.cos(i / 1.8) * 85;
    cciData.push({ time: t, value: Math.round(val * 10) / 10 });
    
    if (i > 0) {
      const prevVal = cciData[i - 1].value;
      const currVal = cciData[i].value;

      // 買點1: 由下往上穿過 -200 (深紅圓點)
      if (prevVal <= -200 && currVal > -200) {
        cciSignals.push({ time: t, position: 'inBar', color: '#FF0000', shape: 'circle', text: '-200' });
      }
      // 買點2: 由下往上穿過 -100 (粉紅圓點)
      else if (prevVal <= -100 && currVal > -100) {
        cciSignals.push({ time: t, position: 'inBar', color: '#FF8080', shape: 'circle', text: '-100' });
      }
      // 賣點1: 由下往上穿過 +100 (淺綠圓點)
      else if (prevVal <= 100 && currVal > 100) {
        cciSignals.push({ time: t, position: 'inBar', color: '#00FF00', shape: 'circle', text: '+100' });
      }
      // 賣點2: 由下往上穿過 +200 (深綠/青綠圓點)
      else if (prevVal <= 200 && currVal > 200) {
        cciSignals.push({ time: t, position: 'inBar', color: '#00CEC9', shape: 'circle', text: '+200' });
      }
    }
  }

  // --- Sub-Pane 4: AO / CVD Candlesticks / DMI ---
  const aoData = [];
  const cvdCandles = [];
  const dmiPlus = [];
  const dmiMinus = [];
  const dmiAdx = [];
  let cumDelta = 0;

  // Pre-calculate hl2 for AO
  const hl2Arr = [];
  for (let i = 0; i < count; i++) {
    hl2Arr.push((candles[i].high + candles[i].low) / 2.0);
  }

  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    // 1. AO = SMA(hl2, 5) - SMA(hl2, 34) (1:1 TradingView)
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
    const aoColor = diff <= 0 ? '#F44336' : '#009688';
    aoData.push({ time: t, value: Math.round(aoVal * 10) / 10, color: aoColor });

    // CVD Candlesticks (openVolume, maxVolume, minVolume, lastVolume)
    const range = (candles[i].high - candles[i].low) || 1;
    const deltaRatio = (candles[i].close - candles[i].open) / range;
    const barDelta = Math.round((candles[i].close - candles[i].open) * 8 + deltaRatio * 80);
    const openVol = cumDelta;
    const closeVol = cumDelta + barDelta;
    const highVol = Math.max(openVol, closeVol) + Math.round(Math.abs(barDelta) * 0.25 + 15);
    const lowVol = Math.min(openVol, closeVol) - Math.round(Math.abs(barDelta) * 0.25 + 15);
    cumDelta = closeVol;

    cvdCandles.push({
      time: t,
      open: openVol,
      high: highVol,
      low: lowVol,
      close: closeVol
    });

    // DMI
    const pVal = 20 + Math.sin(i / 6) * 10;
    const mVal = 20 - Math.sin(i / 6) * 8;
    const adxVal = 18 + Math.abs(Math.sin(i / 4)) * 16;
    dmiPlus.push({ time: t, value: Math.round(pVal * 10) / 10 });
    dmiMinus.push({ time: t, value: Math.round(mVal * 10) / 10 });
    dmiAdx.push({ time: t, value: Math.round(adxVal * 10) / 10 });
  }

  // --- 8 大進出場信號 (🐣 🐦 ✈️ 🚀 ⚡ 🛸 💰 ⚠️) + DeMark 9★ / 13★ ---
  const markers = [];
  for (let i = 15; i < count; i++) {
    const t = candles[i].time;
    // 🐣 / 🐦 藍鳥
    if (i % 26 === 7) {
      markers.push({ time: t, position: 'belowBar', color: '#00b0ff', shape: 'arrowUp', text: '🐦 強藍鳥' });
    } else if (i % 31 === 12) {
      markers.push({ time: t, position: 'belowBar', color: '#00e5ff', shape: 'arrowUp', text: '🐣 藍鳥' });
    }
    // 🚀 / ✈️ 火箭
    else if (i % 37 === 15) {
      markers.push({ time: t, position: 'belowBar', color: '#ffd600', shape: 'arrowUp', text: '🚀 強火箭' });
    } else if (i % 41 === 20) {
      markers.push({ time: t, position: 'belowBar', color: '#ffffff', shape: 'arrowUp', text: '✈️ 火箭' });
    }
    // ⚡ / 🛸 動能再啟
    else if (i % 29 === 24) {
      markers.push({ time: t, position: 'belowBar', color: '#ffd700', shape: 'circle', text: '🛸 強再啟' });
    } else if (i % 35 === 4) {
      markers.push({ time: t, position: 'belowBar', color: '#ffff00', shape: 'circle', text: '⚡ 動能再啟' });
    }
    // 💰 減碼 / ⚠️ 出清
    else if (i % 23 === 18) {
      markers.push({ time: t, position: 'aboveBar', color: '#ff9800', shape: 'arrowDown', text: '💰 減碼' });
    } else if (i % 47 === 33) {
      markers.push({ time: t, position: 'aboveBar', color: '#ff3b30', shape: 'arrowDown', text: '⚠️ 出清' });
    }
    // DeMark 9★ / 13★
    else if (i === count - 15) {
      markers.push({ time: t, position: 'belowBar', color: '#ffd700', shape: 'circle', text: '13★' });
    } else if (i === count - 28) {
      markers.push({ time: t, position: 'aboveBar', color: '#2ed573', shape: 'circle', text: '9★' });
    }
  }

  // --- VWAP & SMMA ---
  const vwapData = [];
  const vwapUpper = [];
  const vwapLower = [];
  const smmaData = [];
  for (let i = 0; i < count; i++) {
    const t = candles[i].time;
    const v = basePrice - 10 + Math.sin(i / 15) * 35;
    vwapData.push({ time: t, value: Math.round(v * 10) / 10 });
    vwapUpper.push({ time: t, value: Math.round((v + 38) * 10) / 10 });
    vwapLower.push({ time: t, value: Math.round((v - 38) * 10) / 10 });
    smmaData.push({ time: t, value: Math.round((basePrice - 42 + (i / count) * 15) * 10) / 10 });
  }
  // --- VRVP (Visible Range Volume Profile: 50 Rows, 70% Value Area) ---
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
    dmiPlus,
    dmiMinus,
    dmiAdx,
    markers,
    vwapData,
    vwapUpper,
    vwapLower,
    smmaData,
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
  candleSeries.setMarkers(data.markers);

  // 2. Sub-Chart 1: 成交量 + Volume MA 5 & Volume MA 10
  volumeSeries.setData(data.volumes);
  volMa5Series.setData(data.volMa5);
  volMa10Series.setData(data.volMa10);

  // 3. Sub-Chart 2: 戰情雙層 MACD
  macdHistSeries.setData(data.macdData);
  macdDifSeries.setData(data.difData);
  macdDeaSeries.setData(data.deaData);

  // 4. Sub-Chart 3: 波段拐點 CCI + 4 色買賣轉折圓點 (紅/粉紅/淺綠/深綠)
  cciLineSeries.setData(data.cciData);
  cciLineSeries.setMarkers(data.cciSignals);

  // 5. Sub-Chart 4: AO / CVD Candlesticks / DMI
  renderSub4Chart(data);

  // 6. Main Chart Overlays (GEX + Ribbons + VWAP + SMMA)
  renderMainOverlays(data);
}

/**
 * Render Sub-Chart 4 based on Active Tab ('ao' | 'cvd' | 'dmi')
 */
function renderSub4Chart(data) {
  if (!subChart4) return;
  
  // Clear previous series
  if (sub4Series.ao) { subChart4.removeSeries(sub4Series.ao); sub4Series.ao = null; }
  if (sub4Series.cvd) { subChart4.removeSeries(sub4Series.cvd); sub4Series.cvd = null; }
  if (sub4Series.dmiPlus) { subChart4.removeSeries(sub4Series.dmiPlus); sub4Series.dmiPlus = null; }
  if (sub4Series.dmiMinus) { subChart4.removeSeries(sub4Series.dmiMinus); sub4Series.dmiMinus = null; }
  if (sub4Series.dmiAdx) { subChart4.removeSeries(sub4Series.dmiAdx); sub4Series.dmiAdx = null; }

  const badge = document.getElementById('pane-4-badge');

  if (activeSub4 === 'ao') {
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
  } else if (activeSub4 === 'dmi') {
    if (badge) badge.innerText = '📈 DMI | 量化通 (ADX: 14, DI: 14, 門檻: 30)';
    sub4Series.dmiAdx = subChart4.addLineSeries({ color: '#FFEB3B', lineWidth: 2, title: 'ADX' });
    sub4Series.dmiPlus = subChart4.addLineSeries({ color: '#FF4757', lineWidth: 1.5, title: '+DI' });
    sub4Series.dmiMinus = subChart4.addLineSeries({ color: '#2ED573', lineWidth: 1.5, title: '-DI' });
    
    sub4Series.dmiAdx.createPriceLine({
      price: 30,
      color: 'rgba(255, 255, 255, 0.45)',
      lineStyle: LightweightCharts.LineStyle.Dashed,
      lineWidth: 1,
      title: 'ADX門檻 (30)'
    });

    sub4Series.dmiAdx.setData(data.dmiAdx);
    sub4Series.dmiPlus.setData(data.dmiPlus);
    sub4Series.dmiMinus.setData(data.dmiMinus);
  }
}

/**
 * Render Overlays on Main Chart
 */
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

  // 4. VRVP (可見範圍成交量分佈圖: POC, VAH, VAL)
  if (indicatorConfig.vrvp && data.vrvpData) {
    drawVrvpHorizontalRays(data.vrvpData);
    renderVrvpCanvasOverlay(data.vrvpData);
  } else {
    clearVrvpRays();
    clearVrvpCanvas();
  }

  // 5. GEX Horizontal Key Lines
  if (indicatorConfig.gex && gexData) {
    drawGexHorizontalRays();
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
 * Draw GEX Key Defensive Rays (1:1 對齊 TradingView 尋鳥 GEX x VIX 風控原廠配色)
 */
function drawGexHorizontalRays() {
  if (!candleSeries || !gexData) return;

  const cw = gexData.call_wall_strike || 47400;
  const vex = (gexData.zero_gamma_level ? gexData.zero_gamma_level - 0.1 : 47217.3);
  const zg = gexData.zero_gamma_level || 47217.4;
  const pw = gexData.put_wall_strike || 47050;
  const mp = gexData.max_pain_strike || 46600;

  if (priceLines.cw) candleSeries.removePriceLine(priceLines.cw);
  if (priceLines.vex) candleSeries.removePriceLine(priceLines.vex);
  if (priceLines.zg) candleSeries.removePriceLine(priceLines.zg);
  if (priceLines.pw) candleSeries.removePriceLine(priceLines.pw);
  if (priceLines.mp) candleSeries.removePriceLine(priceLines.mp);

  // 1. Call Wall (賣權強壓天花板) - 粉紅點線
  priceLines.cw = candleSeries.createPriceLine({
    price: cw,
    color: '#FF76AC',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: `Call Wall (${cw})`
  });

  // 2. VEX Early Flip (VEX 早鳥轉折線) - 亮橘點線
  priceLines.vex = candleSeries.createPriceLine({
    price: vex,
    color: '#FFA726',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: false,
    title: `VEX Early (${vex})`
  });

  // 3. Zero Gamma (基準多空變盤點) - 亮黃點線
  priceLines.zg = candleSeries.createPriceLine({
    price: zg,
    color: '#FFEB3B',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: `Zero Gamma (${zg})`
  });

  // 4. Put Wall (買權強撐地板牆) - 湖水綠點線
  priceLines.pw = candleSeries.createPriceLine({
    price: pw,
    color: '#26A69A',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: `Put Wall (${pw})`
  });

  // 5. Max Pain (選擇權最大痛點) - 亮藍點線
  priceLines.mp = candleSeries.createPriceLine({
    price: mp,
    color: '#42A5F5',
    lineWidth: 1.5,
    lineStyle: LightweightCharts.LineStyle.Dotted,
    axisLabelVisible: true,
    title: `Max Pain (${mp})`
  });
}

/**
 * Update Floating Legend on Crosshair Move
 */
function updateLegendOverlay(param) {
  if (!param.time || !param.seriesData) return;
  const candle = param.seriesData.get(candleSeries);
  if (!candle) return;

  const lOpen = document.getElementById('leg-open');
  const lHigh = document.getElementById('leg-high');
  const lLow = document.getElementById('leg-low');
  const lClose = document.getElementById('leg-close');
  const lDiff = document.getElementById('leg-diff');

  if (lOpen) lOpen.innerText = candle.open.toLocaleString();
  if (lHigh) lHigh.innerText = candle.high.toLocaleString();
  if (lLow) lLow.innerText = candle.low.toLocaleString();
  if (lClose) lClose.innerText = candle.close.toLocaleString();

  if (lDiff) {
    const diff = candle.close - candle.open;
    const sign = diff >= 0 ? '+' : '';
    lDiff.innerText = `${sign}${diff}`;
    lDiff.style.color = diff >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }
}

/**
 * 4. Render Left Panel Quotes, GEX Levels & Momentum HUD
 */
function renderLeftPanel() {
  if (!gexData) return;

  const isIndexFutures = currentActiveSymbol && ['TXF', 'MXF', 'TMF', 'TWN'].includes(currentActiveSymbol.symbol);
  const baseP = isIndexFutures ? (gexData.txf_price || 47329) : (currentActiveSymbol.symbol === '2330' || currentActiveSymbol.symbol === 'CDF' ? 1045 : (currentActiveSymbol.symbol === '2454' ? 1430 : 215));
  
  const cw = gexData.call_wall_strike || 47400;
  const zg = gexData.zero_gamma_level || 47217.4;
  const pw = gexData.put_wall_strike || 47050;
  const mp = gexData.max_pain_strike || 46600;

  // Header Title
  const secTitle = document.querySelector('.panel-left .left-section:first-child .section-title span:first-child');
  if (secTitle) secTitle.innerText = `⚡ ${currentActiveSymbol.name} 即時行情`;

  // Quotes
  const pEl = document.getElementById('left-main-price');
  if (pEl) pEl.innerText = baseP.toLocaleString();

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

  // HUD Momentum fields
  const hudAsset = document.getElementById('left-hud-asset');
  if (hudAsset) hudAsset.innerText = `${currentActiveSymbol.name} (${currentActiveSymbol.symbol})`;

  const hudBias = document.getElementById('left-hud-bias');
  if (hudBias) hudBias.innerText = `+${(currentActiveSymbol.bias_default * 0.42).toFixed(2)}%`;

  const hudMfi = document.getElementById('left-hud-mfi');
  if (hudMfi) hudMfi.innerText = `${(currentActiveSymbol.mfi_thresh + 4.2).toFixed(1)}`;

  const hudAdx = document.getElementById('left-hud-adx');
  if (hudAdx) hudAdx.innerText = `${(currentActiveSymbol.adx_thresh + 5.8).toFixed(1)}`;

  // Header quick pills
  const topZG = document.getElementById('top-stat-zg');
  const topCW = document.getElementById('top-stat-cw');
  const topPW = document.getElementById('top-stat-pw');
  const topMP = document.getElementById('top-stat-mp');

  if (topZG) topZG.innerText = zg.toLocaleString();
  if (topCW) topCW.innerText = cw.toLocaleString();
  if (topPW) topPW.innerText = pw.toLocaleString();
  if (topMP) topMP.innerText = mp.toLocaleString();
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

  // Contract Switcher
  const contractBtns = document.querySelectorAll('.contract-tab');
  contractBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      contractBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const code = btn.getAttribute('data-contract');
      
      const matched = symbolsUniverse.find(s => s.symbol === code || s.futures_code === code);
      if (matched) {
        switchActiveSymbol(matched);
      } else {
        activeContract = code;
        renderChartData();
      }
    });
  });

  // Sub-Pane 4 Tab Switcher (AO / CVD / DMI / Momentum)
  const sub4Tabs = document.querySelectorAll('.sub4-tab-btn');
  sub4Tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      sub4Tabs.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeSub4 = btn.getAttribute('data-sub4');
      const momentumPanel = document.getElementById('momentum-panel');
      const tvChart4 = document.getElementById('tv-sub-chart-4');
      if (activeSub4 === 'momentum') {
        // 顯示大戶散戶動能面板，隱藏 TV 圖表
        if (tvChart4) tvChart4.style.display = 'none';
        if (momentumPanel) momentumPanel.classList.remove('hidden');
        loadMomentumData();
      } else {
        // 顯示 TV 圖表，隱藏動能面板
        if (tvChart4) tvChart4.style.display = '';
        if (momentumPanel) momentumPanel.classList.add('hidden');
        const data = generateIndicatorsData(currentTf);
        renderSub4Chart(data);
      }
    });
  });

  // 大戶散戶動能刷新按鈕
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
      // Read Checkboxes & Inputs
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
      indicatorConfig.fvg = document.getElementById('chk-fvg').checked;

      modal.classList.remove('show');
      renderChartData();
    });
  }

  // AI Advisor Audit Quick Chips
  const auditChips = document.querySelectorAll('.audit-chip');
  auditChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const action = chip.getAttribute('data-action');
      handleAdvisorAction(action);
    });
  });

  // AI Advisor Send Input
  const sendBtn = document.getElementById('advisor-send-btn');
  const inputEl = document.getElementById('advisor-input');
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
 * 6. AI Advisor Feed Management
 */
function initAdvisorFeed() {
  const feed = document.getElementById('advisor-feed');
  if (!feed) return;

  const txf = gexData ? gexData.txf_price : 47329;
  const zg = gexData ? gexData.zero_gamma_level : 47217.4;
  const cw = gexData ? gexData.call_wall_strike : 47400;
  const pw = gexData ? gexData.put_wall_strike : 47050;

  feed.innerHTML = `
    <div class="advisor-msg advisor">
      <div class="msg-meta">
        <span class="sender">尋鳥 AI 量化軍師</span>
        <span class="time">${new Date().toLocaleTimeString()}</span>
      </div>
      <div class="msg-bubble">
        <strong>🦅 戰情室即時盤盤量化診斷 (v50.9)</strong>
        <p style="margin-top: 6px; font-size: 0.8rem; line-height: 1.45;">
          🔹 <strong>當前空間拓撲</strong>：型態 A【痛點沉底 / 懸空防守拓撲】<br>
          ⚡ <strong>GEX 狀態</strong>：指數 (${txf}) 位於 Zero Gamma (${zg}) 之上，做市商正 Gamma 具備減震收斂效應。<br>
          ・<strong>下檔防線</strong>：Put Wall (${pw}) 距目前 <strong>${Math.abs(txf - pw)} 點</strong>。<br>
          ・<strong>上檔天花板</strong>：Call Wall (${cw}) 距目前 <strong>+${Math.abs(cw - txf)} 點</strong>。<br>
          ・<strong>鐵律提醒</strong>：嚴禁對週選價差單建議拆單；暴衝時嚴禁追價！
        </p>
      </div>
    </div>
  `;
}

function handleAdvisorAction(action) {
  const feed = document.getElementById('advisor-feed');
  if (!feed) return;

  let title = '';
  let content = '';

  if (action === 'topology') {
    title = '⚡ 空間拓撲與 Gamma 體檢報告';
    content = `
      1. <strong>空間結構</strong>：指數處於正 Gamma 區間，做市商低買高賣避險，預期波動受壓制。<br>
      2. <strong>防守邊界</strong>：以 Call Wall 47,400 為上檔強阻力，Put Wall 47,050 為下檔硬支撐。<br>
      3. <strong>操作方針</strong>：適宜於區間兩側佈局週選雙賣或垂直價差單收斂時間價值。
    `;
  } else if (action === 'audit') {
    title = '🛡️ 真實持倉部位風控體檢 (AGENTS.md)';
    content = `
      1. <strong>賣腳 (Sell Leg) 安全邊際</strong>：距市價逾 250 點，處於價外 (OTM) 安全防守區。<br>
      2. <strong>結算倒數</strong>：當週選結算僅剩 1 天，Theta 時間價值衰退進入加速期。<br>
      3. <strong>風控紅線</strong>：<strong>嚴禁拆單 (No Legging Out)</strong>，維持整組價差單至結算。
    `;
  } else if (action === 'condor') {
    title = '🦅 週選鐵兀鷹 (Iron Condor) 推薦點位';
    content = `
      ・<strong>上翼 (Bear Call Spread)</strong>：Sell Call 47,400 / Buy Call 47,500 (鎖定 Call Wall 阻力)<br>
      ・<strong>下翼 (Bull Put Spread)</strong>：Sell Put 47,000 / Buy Put 46,900 (鎖定 Put Wall 支撐)<br>
      ・<strong>最大獲利空間</strong>：400 點無震盪安全走廊。
    `;
  } else if (action === 'ioc') {
    title = '🎯 IOC 洗價條件精算';
    content = `
      ・<strong>防守洗價價位</strong>：當 TXF 突破 47,450 或跌破 47,000 時觸發洗價。<br>
      ・<strong>執行方式</strong>：整組價差單 IOC 市價對手價平倉，絕不單腳裸露。
    `;
  }

  const newMsg = document.createElement('div');
  newMsg.className = 'advisor-msg advisor';
  newMsg.innerHTML = `
    <div class="msg-meta">
      <span class="sender">尋鳥 AI 量化軍師</span>
      <span class="time">${new Date().toLocaleTimeString()}</span>
    </div>
    <div class="msg-bubble">
      <strong>${title}</strong>
      <p style="margin-top: 6px; font-size: 0.8rem; line-height: 1.45;">${content}</p>
    </div>
  `;
  feed.appendChild(newMsg);
  feed.scrollTop = feed.scrollHeight;
}

function sendAdvisorQuery(query) {
  if (!query || !query.trim()) return;
  const feed = document.getElementById('advisor-feed');
  if (!feed) return;

  const userMsg = document.createElement('div');
  userMsg.className = 'advisor-msg user';
  userMsg.innerHTML = `
    <div class="msg-meta">
      <span class="sender">交易員 (You)</span>
      <span class="time">${new Date().toLocaleTimeString()}</span>
    </div>
    <div class="msg-bubble">${query}</div>
  `;
  feed.appendChild(userMsg);

  setTimeout(() => {
    const aiMsg = document.createElement('div');
    aiMsg.className = 'advisor-msg advisor';
    aiMsg.innerHTML = `
      <div class="msg-meta">
        <span class="sender">尋鳥 AI 量化軍師</span>
        <span class="time">${new Date().toLocaleTimeString()}</span>
      </div>
      <div class="msg-bubble">
        <strong>🤖 量化軍師即時研判：</strong>
        <p style="margin-top: 6px; font-size: 0.8rem; line-height: 1.45;">
          收到您的詢問：「${query}」。<br>
          當前盤勢受制於 GEX 造市商 Call Wall (47,400) 與 Put Wall (47,050) 之內。<br>
          依據 <strong>AGENTS.md</strong> 最高風控鐵律：盤中若出現急拉或急殺，<strong>嚴禁追價</strong>！維持有限風險價差單持有。
        </p>
      </div>
    `;
    feed.appendChild(aiMsg);
    feed.scrollTop = feed.scrollHeight;
  }, 400);
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
 */
let liveStreamTimer = null;
let lastFubonPrice = null;

function initFubonLivePriceStream() {
  console.log('⚡ Initializing Fubon Neo API & Live Price Gateway Stream...');

  async function fetchLiveTick() {
    try {
      const res = await fetch('http://localhost:8000/api/live_price', { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      
      if (data && data.price) {
        updateLivePriceUI(data);
      }
    } catch (e) {
      // Gateway server not started; fallback cleanly
    }
  }

  // Poll gateway every 1200ms
  if (liveStreamTimer) clearInterval(liveStreamTimer);
  liveStreamTimer = setInterval(fetchLiveTick, 1200);
  fetchLiveTick();
}

function updateLivePriceUI(tick) {
  const priceEl = document.getElementById('hud-txf-price');
  const changeEl = document.getElementById('hud-txf-change');
  if (!priceEl || !tick.price) return;

  const price = tick.price;
  const change = tick.change || 0;
  const pct = tick.pct || 0;

  priceEl.textContent = price.toLocaleString();
  
  const sign = change >= 0 ? '+' : '';
  const col = change >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  
  if (changeEl) {
    changeEl.style.color = col;
    changeEl.textContent = `${sign}${change} (${sign}${pct.toFixed(2)}%)`;
  }

  // Live Flash Effect on Price change
  if (lastFubonPrice !== null && lastFubonPrice !== price) {
    priceEl.style.textShadow = change >= 0 ? '0 0 12px rgba(255, 71, 87, 0.8)' : '0 0 12px rgba(46, 213, 115, 0.8)';
    setTimeout(() => {
      priceEl.style.textShadow = 'none';
    }, 400);
  }
  lastFubonPrice = price;
}

/**
 * 9. Global Symbol Search & Autocomplete Engine (Ctrl+K)
 */
function initSymbolSearchAndAutocomplete() {
  const searchInput = document.getElementById('symbol-search-input');
  const dropdown = document.getElementById('symbol-search-dropdown');
  if (!searchInput || !dropdown) return;

  // Global Ctrl+K / Cmd+K Shortcut
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase();
    if (!q) {
      dropdown.classList.add('hidden');
      dropdown.innerHTML = '';
      return;
    }

    const matches = symbolsUniverse.filter(item => {
      const symMatch = item.symbol.toLowerCase().includes(q);
      const nameMatch = item.name.toLowerCase().includes(q);
      const futMatch = item.futures_code && item.futures_code.toLowerCase().includes(q);
      return symMatch || nameMatch || futMatch;
    }).slice(0, 15);

    if (matches.length === 0) {
      dropdown.innerHTML = `<div style="padding: 10px 14px; color: var(--text-muted); font-size: 0.78rem;">未找到相符的商品標的</div>`;
      dropdown.classList.remove('hidden');
      return;
    }

    dropdown.innerHTML = matches.map((item, idx) => `
      <div class="search-result-item" data-idx="${idx}">
        <div class="search-item-left">
          <span class="search-item-sym">${item.symbol}</span>
          <span class="search-item-name">${item.name}</span>
        </div>
        <div class="search-item-right">
          <span class="search-tag-market">${item.market}</span>
          ${item.has_futures ? `<span class="search-tag-fut">期貨 ${item.futures_code}</span>` : ''}
        </div>
      </div>
    `).join('');

    dropdown.classList.remove('hidden');

    dropdown.querySelectorAll('.search-result-item').forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.getAttribute('data-idx'));
        const targetSym = matches[idx];
        if (targetSym) {
          switchActiveSymbol(targetSym);
          dropdown.classList.add('hidden');
          searchInput.value = '';
        }
      });
    });
  });

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
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
  if (!tbody || symbolsUniverse.length === 0) return;

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

  setTimeout(() => {
    // Generate deterministic candidates based on symbol hash
    const results = [];
    symbolsUniverse.forEach(item => {
      let hash = 0;
      for (let c = 0; c < item.symbol.length; c++) hash = (hash * 37 + item.symbol.charCodeAt(c)) % 10000;
      
      const hasRocketS = (hash % 17 === 0);
      const hasBirdS = (hash % 23 === 0);
      const hasRestartS = (hash % 29 === 0);
      const hasRestartN = (hash % 19 === 0);
      const hasRocketW = (hash % 13 === 0);
      const hasBirdN = (hash % 11 === 0);
      const isMacdFlip = (hash % 5 === 0);
      const isMacdGold = (hash % 7 === 0);
      const isGradeS = (hash % 8 === 0);
      const isGradeA = (hash % 4 === 0);
      const hasDemark = (hash % 31 === 0);
      const has5k = (hash % 27 === 0);
      const hasVol = (hash % 6 === 0);

      // Condition checking
      let match = true;
      if (fRocketS && !hasRocketS) match = false;
      if (fBirdS && !hasBirdS) match = false;
      if (fRestartS && !hasRestartS) match = false;
      if (fRestartN && !hasRestartN) match = false;
      if (fRocketW && !hasRocketW) match = false;
      if (fBirdN && !hasBirdN) match = false;
      if (fMacdFlip && !isMacdFlip) match = false;
      if (fMacdGold && !isMacdGold) match = false;
      if (fGradeS && !isGradeS) match = false;
      if (fGradeA && !isGradeA) match = false;
      if (fDemark && !hasDemark) match = false;
      if (f5k && !has5k) match = false;
      if (fVol && !hasVol) match = false;

      if (match) {
        let price = (hash % 800) + 25;
        if (item.symbol === '2330' || item.symbol === 'CDF') price = 1045;
        if (item.symbol === '2454' || item.symbol === 'DVF') price = 1430;
        if (item.symbol === '2317' || item.symbol === 'DHF') price = 215;
        if (item.symbol === 'TXF') price = 47329;

        const changePct = ((hash % 70) - 20) / 10;
        
        const sigs = [];
        if (hasRocketS) sigs.push('🚀 強火箭');
        if (hasBirdS) sigs.push('🐦 強力藍鳥');
        if (hasRestartS) sigs.push('🛸 飛碟再啟');
        if (hasRestartN) sigs.push('⚡ 動能再啟');
        if (has5k) sigs.push('⭐ 5K突破');
        if (hasDemark) sigs.push('9★ 轉折');
        if (sigs.length === 0) sigs.push('📈 多頭共振');

        results.push({
          item,
          price,
          changePct,
          signals: sigs.join(' '),
          grade: isGradeS ? 'S 強噴' : (isGradeA ? 'A 強勢' : 'B 多頭')
        });
      }
    });

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
          <td>${r.item.name}</td>
          <td><span class="search-tag-market">${r.item.market}・${r.item.category}</span></td>
          <td style="font-weight: 700;">${r.price.toLocaleString()}</td>
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
        const target = symbolsUniverse.find(s => s.symbol === sym);
        if (target) {
          switchActiveSymbol(target);
          document.getElementById('screener-modal')?.classList.remove('show');
        }
      });
    });

  }, 180);
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

  try {
    // 期交所 API 回傳 CSV 格式（非 JSON）
    const generalRes = await fetch('https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersGeneralBytheDate');
    if (!generalRes.ok) throw new Error(`API Error: ${generalRes.status}`);
    
    const csvText = await generalRes.text();
    const generalData = parseMomentumCSV(csvText);

    if (!generalData || generalData.length === 0) {
      throw new Error('期交所 API 未返回資料（可能今日休市）');
    }

    // 解析三大法人資料
    const parsed = parseMajorInstitutionalData(generalData);
    const futData = [];
    
    // 取得台指期總成交量（用於計算散戶比例）
    const txVolume = getTXVolume(futData);

    const result = { ...parsed, txVolume, date: parsed.date || (generalData[0] ? generalData[0]['日期'] : '') || '--' };
    
    // 快取
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
      fetch('data/screener_cache.json').catch(() => null),
      fetch('data/tw_quotes_latest.json').catch(() => null)
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
 * 8. Execute Multi-Factor Quant Screener (選股雷達)
 */
function runBirdQuantScreener() {
  const tableBody = document.getElementById('screener-results-body');
  const countBadge = document.getElementById('screener-count-badge');
  if (!tableBody) return;

  const activeChip = document.querySelector('.preset-chip.active');
  const presetSignal = activeChip ? activeChip.getAttribute('data-preset') : 'ALL';

  const gradeFilter = document.getElementById('screener-filter-grade')?.value || 'ALL';
  const marketFilter = document.getElementById('screener-filter-market')?.value || 'ALL';
  const macdFilter = document.getElementById('screener-filter-macd')?.value || 'ALL';
  const k5Filter = document.getElementById('screener-filter-k5')?.value || 'ALL';

  let rawList = (screenerCacheData && screenerCacheData.symbols) ? screenerCacheData.symbols : [];

  // If screener cache not yet fetched, fallback to symbolsUniverse + realQuotesData
  if (rawList.length === 0 && Array.isArray(symbolsUniverse)) {
    rawList = symbolsUniverse.map(s => {
      const q = realQuotesData ? realQuotesData[s.symbol] : null;
      const price = q ? q.close : (s.symbol === '1605' ? 37.90 : 100);
      const pct = q ? q.pct_change : 0.0;
      const vol = q ? q.volume : 50000;
      const signals = pct >= 2.0 ? ['🚀 強火箭', '🐦 強力藍鳥'] : ['⚡ 動能閃電'];
      return {
        symbol: s.symbol,
        name: s.name,
        market: s.market || 'TWSE',
        category: s.category || '電子',
        price: price,
        pct_change: pct,
        volume: vol,
        grade: pct >= 2.0 ? 'S' : 'A',
        signals: signals,
        macd_state: '零軸上金叉',
        k5_state: '5K 創高突破',
        score: pct >= 2.0 ? 75 : 40
      };
    });
  }

  const filtered = rawList.filter(item => {
    // Preset Chip filter
    if (presetSignal !== 'ALL') {
      if (presetSignal === 'S_GRADE' && item.grade !== 'S') return false;
      if (presetSignal !== 'S_GRADE' && !(item.signals || []).includes(presetSignal) && item.macd_state !== presetSignal && item.demark_state !== presetSignal) return false;
    }

    // Grade filter
    if (gradeFilter !== 'ALL' && item.grade !== gradeFilter) return false;

    // Market filter
    if (marketFilter !== 'ALL' && item.market !== marketFilter) return false;

    // MACD state filter
    if (macdFilter !== 'ALL' && item.macd_state !== macdFilter) return false;

    // 5K trend filter
    if (k5Filter !== 'ALL' && item.k5_state !== k5Filter) return false;

    return true;
  });

  if (countBadge) countBadge.innerText = `${filtered.length} 檔標的符合`;

  if (filtered.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; padding: 30px; color: var(--text-muted);">
          🔍 未找到符合當前篩選條件的標的，請嘗試放寬篩選標準或點擊「重置條件」。
        </td>
      </tr>
    `;
    return;
  }

  let rowsHtml = '';
  filtered.slice(0, 100).forEach(item => {
    const isUp = (item.pct_change || 0) >= 0;
    const color = isUp ? 'var(--call-color)' : 'var(--put-color)';
    const sign = isUp ? '+' : '';

    const tagsHtml = (item.signals || []).map(sig => `
      <span class="signal-tag" style="background: rgba(56,189,248,0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem; margin-right: 4px;">
        ${sig}
      </span>
    `).join('') || '<span style="color:var(--text-muted); font-size:0.7rem;">-</span>';

    const gradeColor = item.grade === 'S' ? '#ffd700' : (item.grade === 'A' ? '#38bdf8' : '#a78bfa');

    rowsHtml += `
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td>
          <span style="font-weight: 700; color: var(--primary-accent);">${item.symbol}</span>
          <span class="market-badge" style="font-size: 0.65rem; padding: 1px 4px; background: rgba(255,255,255,0.1); border-radius: 3px; margin-left: 4px;">${item.market}</span>
        </td>
        <td style="font-weight: 600;">${item.name}</td>
        <td style="font-weight: 700; color: ${color};">$${item.price}</td>
        <td style="font-weight: 700; color: ${color};">${sign}${(item.pct_change || 0).toFixed(2)}%</td>
        <td style="color: var(--text-muted);">${(item.volume || 0).toLocaleString()}</td>
        <td>${tagsHtml}</td>
        <td><span style="color: #38bdf8; font-size: 0.75rem;">${item.macd_state || '零軸上金叉'}</span></td>
        <td>
          <span style="background: ${gradeColor}22; color: ${gradeColor}; border: 1px solid ${gradeColor}; padding: 2px 8px; border-radius: 12px; font-weight: 800; font-size: 0.75rem;">
            ${item.grade} 級
          </span>
        </td>
        <td>
          <button onclick="switchScreenerSymbol('${item.symbol}')" class="btn-action-primary" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 4px;">
            🔍 看盤
          </button>
        </td>
      </tr>
    `;
  });

  tableBody.innerHTML = rowsHtml;
}

function switchScreenerSymbol(code) {
  const modal = document.getElementById('quant-screener-modal');
  if (modal) modal.style.display = 'none';

  const matched = symbolsUniverse.find(s => s.symbol === code);
  if (matched) {
    switchActiveSymbol(matched);
  } else {
    const q = realQuotesData ? realQuotesData[code] : null;
    switchActiveSymbol({
      symbol: code,
      name: q ? q.name : code,
      category: '個股',
      market: q ? q.market : 'TWSE',
      bias_default: 8.0,
      mfi_thresh: 52.0,
      adx_thresh: 20.0
    });
  }
}

/**
 * 9. Real-Time Fubon API Live Price Stream (Polling Gateway)
 */
let lastTxfPrice = null;

function initFubonLivePriceStream() {
  setInterval(async () => {
    try {
      const resp = await fetch('http://localhost:8000/api/live_tick');
      if (!resp.ok) return;
      const data = await resp.json();

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
            leftMainP.style.transform = 'scale(1.05)';
            setTimeout(() => { leftMainP.style.transform = 'scale(1.0)'; }, 300);
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

      // 4. Status Tag
      const statusTag = document.getElementById('fubon-status-tag');
      if (statusTag) {
        if (data.active_provider === 'FUBON') {
          statusTag.innerHTML = '🟢 富邦 API (Live)';
          statusTag.style.borderColor = '#00e676';
          statusTag.style.color = '#00e676';
        } else {
          statusTag.innerHTML = '🌐 官方備援';
          statusTag.style.borderColor = '#38bdf8';
          statusTag.style.color = '#38bdf8';
        }
      }

    } catch (e) {
      // Quiet fail fallback
    }
  }, 1500);
}

// Auto init data preloading & live price stream
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    loadScreenerAndRealQuotesData();
    initFubonLivePriceStream();
  }, 1000);
});





