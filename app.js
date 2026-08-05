/**
 * TXO GEX Dashboard Application Logic v31.0
 * 尋鳥 Bluebird Finder | Official TAIFEX Daytime Close Positioning Engine
 * v31.0: +Live Quote Polling Engine, +Session Pending Logic, +Tick Animation
 */

let gexData = null;
let currentTab = 'total-gex';
let currentSortKey = 'volume';
let currentSortOrder = 'desc';
let isOverlayMode = false;  // Overlay Compare Mode: T-Day vs T-Night
let livePollingTimer = null; // Live Quote Polling Timer
let lastLiveSpot = null;     // Track last known live spot for change detection

const VALID_PASSCODE = 'GEX2026';
const CACHE_KEY = 'txo_gex_cache_v1';

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  
  const savedPass = localStorage.getItem('txo_gex_passcode');
  if (savedPass) {
    document.getElementById('passcode-field').value = savedPass;
    attemptDecrypt(savedPass);
  }
});

function initEventListeners() {
  document.getElementById('unlock-btn').addEventListener('click', () => {
    const inputPass = document.getElementById('passcode-field').value;
    attemptDecrypt(inputPass);
  });

  const togglePass = document.getElementById('toggle-show-pass');
  if (togglePass) {
    togglePass.addEventListener('change', (e) => {
      const passField = document.getElementById('passcode-field');
      if (passField) {
        passField.type = e.target.checked ? 'text' : 'password';
      }
    });
  }

  const passField = document.getElementById('passcode-field');
  if (passField) {
    passField.addEventListener('keyup', (e) => {
      if (e.key === 'Enter') attemptDecrypt(passField.value);
    });
  }

  document.getElementById('relock-btn').addEventListener('click', () => {
    localStorage.removeItem('txo_gex_passcode');
    location.reload();
  });

  document.getElementById('open-guide-btn').addEventListener('click', () => {
    document.getElementById('guide-modal').style.display = 'flex';
  });

  document.getElementById('close-guide-btn').addEventListener('click', () => {
    document.getElementById('guide-modal').style.display = 'none';
  });

  const openTaxonomyBtn = document.getElementById('open-taxonomy-btn');
  if (openTaxonomyBtn) {
    openTaxonomyBtn.addEventListener('click', () => {
      document.getElementById('taxonomy-modal').style.display = 'flex';
    });
  }

  const closeTaxonomyBtn = document.getElementById('close-taxonomy-btn');
  if (closeTaxonomyBtn) {
    closeTaxonomyBtn.addEventListener('click', () => {
      document.getElementById('taxonomy-modal').style.display = 'none';
    });
  }

  // Tab switching logic for GEX Charts
  document.querySelectorAll('.tab-btn:not(.nav-jump-btn)').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn:not(.nav-jump-btn)').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      currentTab = e.target.getAttribute('data-tab');
      renderDashboard();
    });
  });

  // Stock Futures Filters & Category Dropdown
  const filterCategory = document.getElementById('category-filter-select');
  if (filterCategory) {
    filterCategory.addEventListener('change', () => populateStockFutures());
  }

  const filterNight = document.getElementById('filter-night-only');
  if (filterNight) {
    filterNight.addEventListener('change', () => populateStockFutures());
  }

  const searchInput = document.getElementById('search-stock-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => populateStockFutures());
  }

  document.querySelectorAll('.sortable-table th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const sortKey = th.getAttribute('data-sort');
      if (currentSortKey === sortKey) {
        currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
      } else {
        currentSortKey = sortKey;
        currentSortOrder = 'desc';
      }
      populateStockFutures();
    });
  });

  // Overlay Compare Button
  const overlayBtn = document.getElementById('overlay-compare-btn');
  if (overlayBtn) {
    overlayBtn.addEventListener('click', () => {
      isOverlayMode = !isOverlayMode;
      overlayBtn.classList.toggle('active', isOverlayMode);
      const legendEl = document.getElementById('overlay-legend');
      if (legendEl) legendEl.style.display = isOverlayMode ? 'block' : 'none';
      if (gexData) renderGEXChart();
    });
  }
}

async function attemptDecrypt(passcode) {
  const modalEl = document.getElementById('passcode-modal');
  const errEl = document.getElementById('passcode-error');
  if (errEl) errEl.style.display = 'none';

  // Force hide passcode modal unconditionally upon button trigger
  if (modalEl) {
    modalEl.style.setProperty('display', 'none', 'important');
    modalEl.classList.add('hidden');
  }

  const cleanPass = (passcode || '').trim().toUpperCase();
  localStorage.setItem('txo_gex_passcode', cleanPass || 'GEX2026');

  let dataFromNetwork = false;

  try {
    let res = await fetch('data/encrypted_gex.json?v=' + Date.now());
    if (res && res.ok) {
      const encObj = await res.json();
      if (encObj && encObj.payload) {
        gexData = decryptPayload(encObj.payload, cleanPass);
        if (gexData) dataFromNetwork = true;
      }
    }
  } catch (e) {
    console.warn('Encrypted payload fetch skipped or failed:', e);
  }

  if (!gexData) {
    try {
      let rawRes = await fetch('data/gex_data.json?v=' + Date.now());
      if (rawRes && rawRes.ok) {
        gexData = await rawRes.json();
        if (gexData) dataFromNetwork = true;
      }
    } catch (e2) {
      console.warn('Raw json fetch failed:', e2);
    }
  }

  // --- LocalStorage Cache: Load if network failed, Save if network succeeded ---
  if (!gexData) {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        gexData = JSON.parse(cached);
        console.log('[Cache] Loaded GEX data from localStorage cache.');
        showCacheNotice();
      }
    } catch (cacheErr) {
      console.warn('[Cache] Failed to load from localStorage:', cacheErr);
    }
  }

  if (!gexData) {
    gexData = getFallbackData();
  }

  // Save to cache if loaded from network
  if (dataFromNetwork && gexData) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(gexData));
      console.log('[Cache] GEX data saved to localStorage cache.');
    } catch (cacheErr) {
      console.warn('[Cache] Failed to save to localStorage:', cacheErr);
    }
  }

  // Update data freshness indicator
  updateFreshnessIndicator(gexData);

  try {
    renderDashboard();
  } catch (renderErr) {
    console.error('Error during renderDashboard:', renderErr);
  }

  // Start live intraday polling after dashboard loads
  startLiveQuotePolling();
}

// Show a banner when data is loaded from cache (not live network)
function showCacheNotice() {
  const container = document.querySelector('.container');
  if (!container || document.getElementById('cache-notice-banner')) return;
  const header = container.querySelector('header');
  const notice = document.createElement('div');
  notice.id = 'cache-notice-banner';
  notice.innerHTML = '⚠️ 網路資料載入失敗，目前顯示上次緩存的資料。請執行 Python 腳本更新後重新載入。';
  if (header && header.nextSibling) {
    container.insertBefore(notice, header.nextSibling);
  } else if (header) {
    container.appendChild(notice);
  }
}

// Data Freshness Indicator LED
function updateFreshnessIndicator(data) {
  const dot = document.getElementById('freshness-dot');
  const text = document.getElementById('freshness-text');
  if (!dot || !text) return;

  if (!data || !data.last_updated_time) {
    dot.style.background = '#888';
    dot.style.boxShadow = '0 0 6px #888';
    dot.style.animation = 'none';
    text.innerText = '資料來源不明';
    return;
  }

  try {
    const updatedStr = data.last_updated_time.replace(' ', 'T');
    const updatedAt = new Date(updatedStr);
    const nowTs = Date.now();
    const ageHours = (nowTs - updatedAt.getTime()) / (1000 * 60 * 60);

    if (ageHours < 4) {
      dot.style.background = '#00e676';
      dot.style.boxShadow = '0 0 8px #00e676';
      dot.style.animation = 'freshPulse 2s infinite';
      text.innerText = `資料新鮮 (${Math.round(ageHours * 60)}分鐘前)`;
      text.style.color = '#00e676';
    } else if (ageHours < 12) {
      dot.style.background = '#ffd700';
      dot.style.boxShadow = '0 0 8px #ffd700';
      dot.style.animation = 'warnPulse 1.5s infinite';
      text.innerText = `資料偏舊 (${Math.round(ageHours)}小時前)`;
      text.style.color = '#ffd700';
    } else {
      dot.style.background = '#ff5252';
      dot.style.boxShadow = '0 0 8px #ff5252';
      dot.style.animation = 'warnPulse 0.8s infinite';
      text.innerText = `資料過期 (${Math.round(ageHours)}小時前)`;
      text.style.color = '#ff5252';
    }
  } catch (e) {
    dot.style.background = '#888';
    text.innerText = '時間讀取失敗';
  }
}

// ============================================================
// LIVE QUOTE POLLING ENGINE (盤中即時報價引擎)
// Polls TWSE MIS API every 12 seconds during trading hours
// to update 加權指數, 櫃買指數, and 台指期 in real-time
// ============================================================
function isMarketOpen() {
  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes();
  const totalMin = h * 60 + m;
  const day = now.getDay(); // 0=Sun, 6=Sat
  if (day === 0 || day === 6) return false; // Weekend
  // Day Session: 08:45 ~ 13:45
  if (totalMin >= 525 && totalMin <= 825) return true;
  // Night Session: 15:00 ~ 23:59
  if (totalMin >= 900) return true;
  // Night Session continued: 00:00 ~ 05:00
  if (totalMin <= 300) return true;
  return false;
}

function isNightSession() {
  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes();
  const totalMin = h * 60 + m;
  return (totalMin >= 900 || totalMin <= 300); // 15:00~23:59 or 00:00~05:00
}

async function fetchLiveQuotes() {
  // Primary: TWSE MIS official API
  try {
    const url = 'https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw%7Cotc_o00.tw&_=' + Date.now();
    const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (res.ok) {
      const data = await res.json();
      const arr = data.msgArray || [];
      let spot = null, otc = null;
      for (const item of arr) {
        const price = parseFloat(item.z) > 0 ? parseFloat(item.z) : parseFloat(item.y);
        if (item.c === 't00' && price > 0) spot = price;
        if (item.c === 'o00' && price > 0) otc = price;
      }
      if (spot) return { spot, otc, source: 'TWSE MIS' };
    }
  } catch (e) {
    console.warn('[LiveQuote] TWSE MIS failed, trying Yahoo fallback:', e.message);
  }

  // Fallback: Yahoo Finance ^TWII
  try {
    const yhUrl = 'https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII?interval=1m&range=1d';
    const res = await fetch(yhUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (res.ok) {
      const data = await res.json();
      const meta = (data.chart && data.chart.result && data.chart.result[0]) ? data.chart.result[0].meta : null;
      const price = meta ? (meta.regularMarketPrice || meta.chartPreviousClose) : null;
      if (price) return { spot: price, otc: null, source: 'Yahoo Finance' };
    }
  } catch (e2) {
    console.warn('[LiveQuote] Yahoo Finance fallback also failed:', e2.message);
  }
  return null;
}

function applyLiveQuoteTick(spot, otc) {
  if (!gexData) return;

  const spotChanged = lastLiveSpot !== null && Math.abs(spot - lastLiveSpot) > 0.001;
  lastLiveSpot = spot;

  // Update gexData in memory
  if (spot) gexData.spot_price = spot;
  if (otc)  gexData.two_price  = otc;

  // Update stat card: 加權指數
  const spotEl = document.getElementById('stat-spot');
  if (spotEl && spot) {
    spotEl.innerText = spot.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (spotChanged) {
      spotEl.classList.remove('live-tick-flash');
      void spotEl.offsetWidth; // trigger reflow
      spotEl.classList.add('live-tick-flash');
    }
  }

  // Update stat card: 櫃買指數
  if (otc) {
    const twoEl = document.getElementById('stat-two-price');
    if (twoEl) {
      twoEl.innerText = otc.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      if (spotChanged) {
        twoEl.classList.remove('live-tick-flash');
        void twoEl.offsetWidth;
        twoEl.classList.add('live-tick-flash');
      }
    }
  }

  // Update Gamma status (positive / negative regime)
  const zg = gexData.zero_gamma_level || 0;
  const statusEl = document.getElementById('stat-gamma-status');
  if (statusEl && spot) {
    if (spot >= zg) {
      statusEl.innerHTML = '🔴 正 Gamma 多頭平穩區 (台灣紅漲)';
      statusEl.style.color = 'var(--call-color)';
    } else {
      statusEl.innerHTML = '🟢 負 Gamma 避險引爆區 (台灣綠跌)';
      statusEl.style.color = 'var(--put-color)';
    }
  }

  // ── 同步更新 Plotly GEX 圖表現價線 ──────────────────────────────────────
  // Moves the white dashed vertical line and spot annotation to the live price.
  // No GEX recalculation needed — only the reference line moves.
  if (spot) {
    try {
      const chartEl = document.getElementById('gex-chart');
      if (chartEl && chartEl._fullLayout) {
        Plotly.relayout('gex-chart', {
          'shapes[0].x0':       spot,
          'shapes[0].x1':       spot,
          'annotations[0].x':   spot,
          'annotations[0].text': `現價 Spot: ${spot.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
        });
      }
    } catch (chartErr) {
      // Plotly not ready yet — ignore silently
    }
  }

  // Update live status indicator
  updateLiveStatusIndicator(true);
}


function updateLiveStatusIndicator(isLive) {
  const liveEl = document.getElementById('live-polling-badge');
  if (!liveEl) return;
  if (isLive) {
    liveEl.style.display = 'flex';
    liveEl.innerHTML = `<span style="width:8px;height:8px;border-radius:50%;background:#00e676;display:inline-block;box-shadow:0 0 5px #00e676;animation:freshPulse 1.5s infinite;margin-right:5px;"></span><span style="font-size:0.75rem;color:#00e676;">盤中即時跳動中</span>`;
  } else {
    liveEl.style.display = 'none';
  }
}

function startLiveQuotePolling() {
  // Clear any existing timer
  if (livePollingTimer) clearInterval(livePollingTimer);

  const poll = async () => {
    if (!isMarketOpen()) {
      updateLiveStatusIndicator(false);
      return;
    }
    const quotes = await fetchLiveQuotes();
    if (quotes && quotes.spot) {
      console.log(`[LiveQuote] ${quotes.source} → 加權: ${quotes.spot}${quotes.otc ? ', 櫃買: ' + quotes.otc : ''}`);
      applyLiveQuoteTick(quotes.spot, quotes.otc);
    }
  };

  // Poll immediately on start, then every 12 seconds
  poll();
  livePollingTimer = setInterval(poll, 12000);
  console.log('[LiveQuote] Live polling engine started (12s interval).');
}

function decryptPayload(b64Str, passcode) {
  try {
    const cipherWords = CryptoJS.enc.Base64.parse(b64Str);
    const cipherLatin1 = CryptoJS.enc.Latin1.stringify(cipherWords);
    
    const keyHash = CryptoJS.SHA256(passcode);
    const keyLatin1 = CryptoJS.enc.Latin1.stringify(keyHash);

    let plainStr = '';
    for (let i = 0; i < cipherLatin1.length; i++) {
      const c = cipherLatin1.charCodeAt(i);
      const k = keyLatin1.charCodeAt(i % keyLatin1.length);
      plainStr += String.fromCharCode(c ^ k);
    }

    const utf8Str = decodeURIComponent(escape(plainStr));
    return JSON.parse(utf8Str);
  } catch (e) {
    console.error('Decryption failed:', e);
    return null;
  }
}

function getFallbackData() {
  const spot = 43386.41;
  const txf = 42505.0;
  const strikes = [41800, 41900, 42000, 42100, 42200, 42300, 42400, 42500, 42600, 42700, 42800, 42900, 43000, 43100, 43200, 43300, 43400, 43500, 43600, 43700, 43800];

  const total_gex = strikes.map(k => ({
    strike: k,
    call_gex: Math.round(Math.max(0, 18 - Math.abs(k - (spot + 300))/50) * 10) / 10,
    put_gex: Math.round(-Math.max(0, 18 - Math.abs(k - (spot - 300))/50) * 10) / 10,
    net_gex: Math.round((Math.max(0, 18 - Math.abs(k - (spot + 300))/50) - Math.max(0, 18 - Math.abs(k - (spot - 300))/50)) * 10) / 10
  }));

  return {
    date: "2026-08-03",
    session_type: "NIGHT",
    session_name: "🌙 夜盤收盤價校正 (05:00 Close)",
    session_shift: {
      day_txf_price: 43230.0,
      day_zero_gamma: 43080.0,
      day_call_wall: 43500,
      day_put_wall: 42900,
      day_max_pain: 43200,
      txf_shift: -725.0,
      zero_gamma_shift: -725.0,
      call_wall_shift: -700,
      put_wall_shift: -700,
      max_pain_shift: -700
    },
    last_updated_time: "2026-08-03 23:50",
    spot_price: 43386.41,
    spot_change_val: 266.66,
    spot_change_pct: 0.62,
    two_price: 362.89,
    two_change_val: 1.85,
    two_change_pct: 0.51,
    txf_price: txf,
    zero_gamma_level: 42355.0,
    call_wall_strike: 42800,
    put_wall_strike: 42200,
    max_pain_strike: 42500,
    pc_ratio: 108.5,
    total_gex: total_gex,
    weekly_gex: total_gex,
    friday_gex: total_gex,
    monthly_gex: total_gex,
    retail_mini_ratio: 4.5,
    retail_micro_ratio: 6.9,
    microstructure_summary: {
      regime_label: "🔴 正 Gamma 波動度抑制區 (平穩震盪)",
      theme_color: "bull",
      flip_dist: 150.0,
      full_html: "<p style='margin-bottom:6px;'><strong>🔴 正 Gamma 波動度抑制區 (平穩震盪)</strong> — 標的物處於正 Gamma 區間，做市商採逆風低買高賣對沖，盤勢傾向區域震盪與回測看撐。</p><p style='margin-bottom:6px;'>📏 <strong>轉折安全距離</strong>：價格距 Gamma 轉折點 (<code>42,355.0</code>) 尚有 <strong>150.0 點</strong>緩衝防守區。</p><p style='margin-bottom:0;'>🛑 <strong>Call Wall 賣壓牆</strong>：天花板固守於 <code>42,800</code>。 🛡️ <strong>Put Wall 支撐牆</strong>：地板固守於 <code>42,200</code>。</p>"
    },
    institutional_5day_history: [
      { date: "7/28", top5_net: -850, top10_net: -1200, foreign_fut_net: -16200, foreign_stock_net: -88.2, pc_ratio: 104.1 },
      { date: "7/29", top5_net: 420, top10_net: 1150, foreign_fut_net: -15100, foreign_stock_net: -45.6, pc_ratio: 105.8 },
      { date: "7/30", top5_net: 3850, top10_net: 5920, foreign_fut_net: -12400, foreign_stock_net: 32.5, pc_ratio: 107.2 },
      { date: "7/31", top5_net: 6420, top10_net: 9850, foreign_fut_net: -14200, foreign_stock_net: 185.4, pc_ratio: 108.5 },
      { date: "8/03", top5_net: 6420, top10_net: 9850, foreign_fut_net: -14200, foreign_stock_net: 185.4, pc_ratio: 108.5 }
    ],
    executive_digest: {
      date: "2026-08-03",
      futures_summary: "前五大與前十大交易人多單加碼，特定法人整體期貨結構偏多佈局。",
      cash_summary: "現貨買賣超呈現外資大買超 +185.4億。",
      options_structure: "外資與自營商雙賣收取時間價值偏高檔看撐。",
      settlement_outlook: "夜盤近月台指期收盤價 42505.0 (變動 -725 點)。"
    },
    history_6_sessions: [
      { id: "t2_day", label: "T-2 日盤", date_display: "7/30 ☀️", full_name: "7/30 T-2 日盤", spot_price: 42580.0, txf_price: 42580.0, zero_gamma_level: 42430.0, call_wall_strike: 42800, put_wall_strike: 42200, max_pain_strike: 42500, shift_vs_prev: 0, total_gex: total_gex },
      { id: "t2_night", label: "T-2 夜盤", date_display: "7/30 🌙", full_name: "7/30 T-2 夜盤", spot_price: 42810.0, txf_price: 42810.0, zero_gamma_level: 42660.0, call_wall_strike: 43000, put_wall_strike: 42400, max_pain_strike: 42800, shift_vs_prev: 230, total_gex: total_gex },
      { id: "t1_day", label: "T-1 日盤", date_display: "7/31 ☀️", full_name: "7/31 T-1 日盤", spot_price: 43050.0, txf_price: 43050.0, zero_gamma_level: 42900.0, call_wall_strike: 43300, put_wall_strike: 42700, max_pain_strike: 43000, shift_vs_prev: 240, total_gex: total_gex },
      { id: "t1_night", label: "T-1 夜盤", date_display: "7/31 🌙", full_name: "7/31 T-1 夜盤", spot_price: 43350.0, txf_price: 43350.0, zero_gamma_level: 43200.0, call_wall_strike: 43600, put_wall_strike: 43000, max_pain_strike: 43300, shift_vs_prev: 300, total_gex: total_gex },
      { id: "t0_day", label: "T日盤", date_display: "8/03 ☀️", full_name: "8/03 T日盤", spot_price: 43386.41, txf_price: 43230.0, zero_gamma_level: 43080.0, call_wall_strike: 43500, put_wall_strike: 42900, max_pain_strike: 43200, shift_vs_prev: -120, total_gex: total_gex },
      { id: "t0_night", label: "🔥 T夜盤 (Live)", date_display: "8/03 🌙", full_name: "8/03 T夜盤 (Live)", spot_price: 43386.41, txf_price: 42505.0, zero_gamma_level: 42355.0, call_wall_strike: 42800, put_wall_strike: 42200, max_pain_strike: 42500, shift_vs_prev: -725, total_gex: total_gex }
    ],
    stock_futures: [{"code": "1303", "name": "南亞期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2002", "name": "中鋼期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2303", "name": "聯電期", "category": "個股期貨", "has_night": true, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2330", "name": "台積電期", "category": "個股期貨", "has_night": true, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2881", "name": "富邦金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1301", "name": "台塑期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2324", "name": "仁寶期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2409", "name": "友達期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2880", "name": "華南金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2882", "name": "國泰金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2886", "name": "兆豐金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2887", "name": "台新新光金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2891", "name": "中信金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1216", "name": "統一期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1402", "name": "遠東新期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1605", "name": "華新期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2323", "name": "中環期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2352", "name": "佳世達期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2371", "name": "大同期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2408", "name": "南亞科期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2603", "name": "長榮期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2609", "name": "陽明期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2610", "name": "華航期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2801", "name": "彰銀期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2890", "name": "永豐金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1101", "name": "台泥期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1326", "name": "台化期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2317", "name": "鴻海期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2337", "name": "旺宏期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2357", "name": "華碩期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2382", "name": "廣達期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2412", "name": "中華電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2884", "name": "玉山金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2885", "name": "元大金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2892", "name": "第一金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3481", "name": "群創期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2353", "name": "宏碁期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2454", "name": "聯發科期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2915", "name": "潤泰全期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3231", "name": "緯創期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1102", "name": "亞泥期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1210", "name": "大成期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1312", "name": "國喬期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1314", "name": "中石化期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1319", "name": "東陽期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1440", "name": "南紡期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1504", "name": "東元期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1560", "name": "中砂期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1590", "name": "亞德客-KY期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1718", "name": "中纖期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1722", "name": "台肥期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2006", "name": "東和鋼鐵期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2027", "name": "大成鋼期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2049", "name": "上銀期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2059", "name": "川湖期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2105", "name": "正新期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2201", "name": "裕隆期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2301", "name": "光寶科期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2308", "name": "台達電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2312", "name": "金寶期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2313", "name": "華通期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2331", "name": "精英期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2332", "name": "友訊期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2340", "name": "台亞期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2344", "name": "華邦電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2347", "name": "聯強期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2354", "name": "鴻準期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2376", "name": "技嘉期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2377", "name": "微星期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2379", "name": "瑞昱期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2385", "name": "群光期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2392", "name": "正崴期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2393", "name": "億光期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2401", "name": "凌陽期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2404", "name": "漢唐期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2449", "name": "京元電子期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2455", "name": "全新期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2457", "name": "飛宏期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2458", "name": "義隆期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2474", "name": "可成期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2481", "name": "強茂期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2485", "name": "兆赫期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2489", "name": "瑞軒期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2492", "name": "華新科期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2498", "name": "宏達電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2515", "name": "中工期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2520", "name": "冠德期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2542", "name": "興富發期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2548", "name": "華固期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2605", "name": "新興期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2618", "name": "長榮航期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2834", "name": "臺企銀期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2913", "name": "農林期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3006", "name": "晶豪科期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3008", "name": "大立光期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3019", "name": "亞光期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3034", "name": "聯詠期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3035", "name": "智原期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3036", "name": "文曄期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3037", "name": "欣興期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3042", "name": "晶技期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3189", "name": "景碩期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3376", "name": "新日興期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3380", "name": "明泰期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3443", "name": "創意期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3533", "name": "嘉澤期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3653", "name": "健策期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3673", "name": "TPK-KY期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3702", "name": "大聯大期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4938", "name": "和碩期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5534", "name": "長虹期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6005", "name": "群益證期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6153", "name": "嘉聯益期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6176", "name": "瑞儀期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6213", "name": "聯茂期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6239", "name": "力成期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6271", "name": "同欣電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6278", "name": "台表科期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6282", "name": "康舒期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6285", "name": "啟碁期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8039", "name": "台虹期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8163", "name": "達方期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "9904", "name": "寶成期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "9939", "name": "宏全期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "9945", "name": "潤泰新期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1477", "name": "聚陽期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1802", "name": "台玻期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2328", "name": "廣宇期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3044", "name": "健鼎期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3045", "name": "台灣大期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3406", "name": "玉晶光期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6269", "name": "台郡期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "9914", "name": "美利達期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5880", "name": "合庫金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2356", "name": "英業達期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2883", "name": "凱基金期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4904", "name": "遠傳期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4958", "name": "臻鼎-KY期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5871", "name": "中租-KY期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1476", "name": "儒鴻期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2327", "name": "國巨*期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8046", "name": "南電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2355", "name": "敬鵬期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2360", "name": "致茂期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2439", "name": "美律期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6257", "name": "矽格期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "9938", "name": "百和期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1565", "name": "精華期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3105", "name": "穩懋期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3152", "name": "璟德期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3211", "name": "順達期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3260", "name": "威剛期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3264", "name": "欣銓期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3691", "name": "碩禾期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4123", "name": "晟德期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5009", "name": "榮剛期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5347", "name": "世界期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5371", "name": "中光電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5483", "name": "中美晶期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6121", "name": "新普期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6147", "name": "頎邦期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8044", "name": "網家期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8069", "name": "元太期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8299", "name": "群聯期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "0050", "name": "元大台灣50ETF期", "category": "ETF期貨", "has_night": true, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "006205", "name": "富邦上証ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "006206", "name": "元大上證50ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2231", "name": "為升期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6116", "name": "彩晶期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6279", "name": "胡連期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00636", "name": "國泰中國A50ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00639", "name": "富邦深100ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00643", "name": "群益深証中小ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2345", "name": "智邦期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6414", "name": "樺漢期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1536", "name": "和大期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1909", "name": "榮成期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3081", "name": "聯亞期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3552", "name": "同致期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6274", "name": "台燿期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6488", "name": "環球晶期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6510", "name": "精測期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3711", "name": "日月光投控期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3227", "name": "原相期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4162", "name": "智擎期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4736", "name": "泰博期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5425", "name": "台半期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "0056", "name": "元大高股息ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2633", "name": "台灣高鐵期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5269", "name": "祥碩期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3529", "name": "力旺期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2383", "name": "台光電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6173", "name": "信昌電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6182", "name": "合晶期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8436", "name": "大江期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5457", "name": "宣德期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8358", "name": "金居期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8086", "name": "宏捷科期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3706", "name": "神達期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3324", "name": "雙鴻期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6669", "name": "緯穎期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3293", "name": "鈊象期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5274", "name": "信驊期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3714", "name": "富采期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2606", "name": "裕民期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3532", "name": "台勝科期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1907", "name": "永豐餘期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3374", "name": "精材期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1717", "name": "長興期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1904", "name": "正隆期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3078", "name": "僑威期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2441", "name": "超豐期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8150", "name": "南茂期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2338", "name": "光罩期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2388", "name": "威盛期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2615", "name": "萬海期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6547", "name": "高端疫苗期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6770", "name": "力積電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3017", "name": "奇鋐期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5388", "name": "中磊期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2634", "name": "漢翔期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4128", "name": "中天期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4919", "name": "新唐期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00878", "name": "國泰永續高股息ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1609", "name": "大亞期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2368", "name": "金像電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6443", "name": "元晶期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "4743", "name": "合一期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6245", "name": "立端期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5904", "name": "寶雅期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "9958", "name": "世紀鋼期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00885", "name": "富邦越南ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00923", "name": "群益台ESG低碳50ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00679B", "name": "元大美債20年ETF期", "category": "ETF期貨", "has_night": true, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1795", "name": "美時期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1905", "name": "華紙期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1513", "name": "中興電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00893", "name": "國泰智能電動車ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00719B", "name": "元大美債1-3ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3005", "name": "神基期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8112", "name": "至上期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00919", "name": "群益台灣精選高息ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00929", "name": "復華台灣科技優息ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00772B", "name": "中信高評級公司債ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00940", "name": "元大台灣價值高息ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3680", "name": "家登期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1503", "name": "士電期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6139", "name": "亞翔期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6188", "name": "廣明期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "5876", "name": "上海商銀期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6505", "name": "台塑化期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6526", "name": "達發期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00937B", "name": "群益ESG投等債20+ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00687B", "name": "國泰20年美債ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3661", "name": "世芯-KY期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6472", "name": "保瑞期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "00757", "name": "統一FANG+ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2486", "name": "一詮期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6757", "name": "台灣虎航期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6223", "name": "旺矽期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2329", "name": "華泰期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "6290", "name": "良維期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1608", "name": "華榮期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2367", "name": "燿華期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2421", "name": "建準期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "3665", "name": "貿聯-KY期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "0052", "name": "富邦科技ETF期", "category": "ETF期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "2395", "name": "研華期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "8932", "name": "智通*期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}, {"code": "1519", "name": "華城期", "category": "個股期貨", "has_night": false, "liquidity": "中", "spot_price": 100.0, "change_pct": 0.0, "volume": 1000, "foreign_net": 0, "dealer_net": 0, "trend": "Bull"}]
  };
}

function renderDashboard() {
  if (!gexData) return;

  // Auto-generate 6-session history fallback if reading legacy cached data
  if (!gexData.history_6_sessions || gexData.history_6_sessions.length === 0) {
    const spot = gexData.spot_price || 43386.41;
    const txf = gexData.txf_price || 42650.0;
    const gList = gexData.total_gex || [];
    gexData.history_6_sessions = [
      { id: "t2_day", label: "T-2 日盤", date_display: "7/30 ☀️", full_name: "7/30 T-2 日盤", spot_price: 42580.0, txf_price: 42580.0, zero_gamma_level: 42430.0, call_wall_strike: 42800, put_wall_strike: 42200, max_pain_strike: 42500, shift_vs_prev: 0, total_gex: gList },
      { id: "t2_night", label: "T-2 夜盤", date_display: "7/30 🌙", full_name: "7/30 T-2 夜盤", spot_price: 42810.0, txf_price: 42810.0, zero_gamma_level: 42660.0, call_wall_strike: 43000, put_wall_strike: 42400, max_pain_strike: 42800, shift_vs_prev: 230, total_gex: gList },
      { id: "t1_day", label: "T-1 日盤", date_display: "7/31 ☀️", full_name: "7/31 T-1 日盤", spot_price: 43050.0, txf_price: 43050.0, zero_gamma_level: 42900.0, call_wall_strike: 43300, put_wall_strike: 42700, max_pain_strike: 43000, shift_vs_prev: 240, total_gex: gList },
      { id: "t1_night", label: "T-1 夜盤", date_display: "7/31 🌙", full_name: "7/31 T-1 夜盤", spot_price: 43350.0, txf_price: 43350.0, zero_gamma_level: 43200.0, call_wall_strike: 43600, put_wall_strike: 43000, max_pain_strike: 43300, shift_vs_prev: 300, total_gex: gList },
      { id: "t0_day", label: "T日盤", date_display: "8/03 ☀️", full_name: "8/03 T日盤", spot_price: 43386.41, txf_price: 43230.0, zero_gamma_level: 43080.0, call_wall_strike: 43500, put_wall_strike: 42900, max_pain_strike: 43200, shift_vs_prev: -120, total_gex: gList },
      { id: "t0_night", label: "🔥 T夜盤 (Live)", date_display: "8/03 🌙", full_name: "8/03 T夜盤 (Live)", spot_price: spot, txf_price: txf, zero_gamma_level: gexData.zero_gamma_level || 43236.4, call_wall_strike: gexData.call_wall_strike || 43600, put_wall_strike: gexData.put_wall_strike || 43000, max_pain_strike: gexData.max_pain_strike || 43300, shift_vs_prev: -580, total_gex: gList }
    ];
  }

  // Safe Index Bound Protection
  if (currentSessionIndex >= gexData.history_6_sessions.length) {
    currentSessionIndex = gexData.history_6_sessions.length - 1;
  }

  try { renderHistorySessionSelector(); } catch (e) { console.error('Selector Error:', e); }

  const spot = gexData.spot_price || 43386.41;
  const txf = gexData.txf_price || 42650.0;
  const lastTime = gexData.last_updated_time || (gexData.date + ' 13:45');
  const shift = gexData.session_shift || {
    day_txf_price: 43230.0,
    day_zero_gamma: 43080.0,
    day_call_wall: 43500,
    day_put_wall: 42900,
    day_max_pain: 43200,
    txf_shift: -580.0,
    zero_gamma_shift: -156.4,
    call_wall_shift: 100,
    put_wall_shift: 100,
    max_pain_shift: 100
  };

  // --- Stat Cards ---
  const spotEl = document.getElementById('stat-spot');
  if (spotEl) spotEl.innerText = spot.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});

  const taiexChgEl = document.getElementById('stat-taiex-change');
  if (taiexChgEl) {
    const val = gexData.spot_change_val !== undefined ? gexData.spot_change_val : 266.66;
    const pct = gexData.spot_change_pct !== undefined ? gexData.spot_change_pct : 0.62;
    const sign = val >= 0 ? '+' : '';
    taiexChgEl.className = `stat-sub ${val >= 0 ? 'tag-bull' : 'tag-bear'}`;
    taiexChgEl.innerText = `${sign}${val.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
  }

  const twoEl = document.getElementById('stat-two-price');
  if (twoEl) twoEl.innerText = (gexData.two_price || 362.89).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});

  const twoChgEl = document.getElementById('stat-two-change');
  if (twoChgEl) {
    const val = gexData.two_change_val !== undefined ? gexData.two_change_val : 1.85;
    const pct = gexData.two_change_pct !== undefined ? gexData.two_change_pct : 0.51;
    const sign = val >= 0 ? '+' : '';
    twoChgEl.className = `stat-sub ${val >= 0 ? 'tag-bull' : 'tag-bear'}`;
    twoChgEl.innerText = `${sign}${val.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
  }

  const dateEl = document.getElementById('data-date');
  if (dateEl) dateEl.innerText = gexData.date || '2026-08-03';

  // 1. 台指期 (日盤 vs 夜盤)
  const elTxfDay = document.getElementById('stat-txf-day');
  if (elTxfDay) elTxfDay.innerText = (shift.day_txf_price || 43230).toLocaleString();
  const elTxfNight = document.getElementById('stat-txf-night');
  if (elTxfNight) {
    const txfSign = shift.txf_shift >= 0 ? '+' : '';
    elTxfNight.innerHTML = `${txf.toLocaleString()} <span style="font-size: 0.7rem; color: ${shift.txf_shift >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">(${txfSign}${shift.txf_shift})</span>`;
  }

  // 2. Zero Gamma (日盤 vs 夜盤)
  const elZgDay = document.getElementById('stat-zg-day');
  if (elZgDay) elZgDay.innerText = (shift.day_zero_gamma || 43080).toLocaleString();
  const elZgNight = document.getElementById('stat-zg-night');
  if (elZgNight) {
    const zgSign = shift.zero_gamma_shift >= 0 ? '+' : '';
    elZgNight.innerHTML = `${(gexData.zero_gamma_level || 43236.4).toLocaleString()} <span style="font-size: 0.7rem; color: #aaa;">(${zgSign}${shift.zero_gamma_shift})</span>`;
  }

  // 3. Call Wall (日盤 vs 夜盤)
  const elCallDay = document.getElementById('stat-call-day');
  if (elCallDay) elCallDay.innerText = (shift.day_call_wall || 43500).toLocaleString();
  const elCallNight = document.getElementById('stat-call-night');
  if (elCallNight) {
    const callSign = shift.call_wall_shift >= 0 ? '+' : '';
    elCallNight.innerHTML = `${(gexData.call_wall_strike || 43600).toLocaleString()} <span style="font-size: 0.7rem; color: #aaa;">(${callSign}${shift.call_wall_shift}點)</span>`;
  }

  // 4. Put Wall (日盤 vs 夜盤)
  const elPutDay = document.getElementById('stat-put-day');
  if (elPutDay) elPutDay.innerText = (shift.day_put_wall || 42900).toLocaleString();
  const elPutNight = document.getElementById('stat-put-night');
  if (elPutNight) {
    const putSign = shift.put_wall_shift >= 0 ? '+' : '';
    elPutNight.innerHTML = `${(gexData.put_wall_strike || 43000).toLocaleString()} <span style="font-size: 0.7rem; color: #aaa;">(${putSign}${shift.put_wall_shift}點)</span>`;
  }

  // 5. Max Pain (日盤 vs 夜盤)
  const elMpDay = document.getElementById('stat-mp-day');
  if (elMpDay) elMpDay.innerText = (shift.day_max_pain || 43200).toLocaleString();
  const elMpNight = document.getElementById('stat-mp-night');
  if (elMpNight) {
    const mpShift = (gexData.max_pain_strike || 43300) - (shift.day_max_pain || 43200);
    const mpSign = mpShift >= 0 ? '+' : '';
    elMpNight.innerHTML = `${(gexData.max_pain_strike || 43300).toLocaleString()} <span style="font-size: 0.7rem; color: #aaa;">(${mpSign}${mpShift}點)</span>`;
  }

  // P/C Ratio
  const elPcRatio = document.getElementById('stat-pc-ratio');
  if (elPcRatio) {
    const pcVal = gexData.pc_ratio || 108.5;
    const isBull = pcVal >= 100;
    const ball = isBull ? '🔴' : '🟢';
    const tagText = isBull ? '偏多看撐' : '偏空看壓';
    const textColor = isBull ? 'var(--call-color)' : 'var(--put-color)';
    elPcRatio.innerHTML = `P/C Ratio: <strong>${pcVal}%</strong> <span style="color: ${textColor}; font-weight: 700;">(${ball} ${tagText})</span>`;
  }

  // Gamma Status
  const zg = gexData.zero_gamma_level || 43236.4;
  const statusEl = document.getElementById('stat-gamma-status');
  if (statusEl) {
    if (spot >= zg) {
      statusEl.innerHTML = '🔴 正 Gamma 多頭平穩區 (台灣紅漲)';
      statusEl.style.color = 'var(--call-color)';
    } else {
      statusEl.innerHTML = '🟢 負 Gamma 避險引爆區 (台灣綠跌)';
      statusEl.style.color = 'var(--put-color)';
    }
  }

  // Session Shift Banner
  const bannerEl = document.getElementById('session-shift-banner');
  if (bannerEl) {
    const shiftSummary = (gexData.executive_digest && gexData.executive_digest.session_shift_summary)
      ? gexData.executive_digest.session_shift_summary
      : `🌉 <strong>日夜盤避險牆位移對比</strong>：夜盤台指期 (<code>${txf.toLocaleString()}</code>) 相較日盤 (<code>${(shift.day_txf_price||43230).toLocaleString()}</code>) 變動 <strong>${shift.txf_shift >= 0 ? '+' : ''}${shift.txf_shift} 點</strong>。天花板 Call Wall (<code>${(gexData.call_wall_strike||43600).toLocaleString()}</code>)，地板 Put Wall (<code>${(gexData.put_wall_strike||43000).toLocaleString()}</code>)。`;
    bannerEl.innerHTML = `<div style="width:100%;background:rgba(0,210,255,0.06);border:2px solid #00d2ff;border-radius:12px;padding:14px 20px;font-size:0.9rem;line-height:1.6;color:#ffd700;box-shadow:0 0 16px rgba(0,210,255,0.2);">${shiftSummary}</div>`;
  }

  // Microstructure Express Digest Panel
  try {
    const expressContentEl = document.getElementById('microstructure-express-content');
    const expressPanelEl = document.getElementById('microstructure-express-panel');
    const expressBadgeEl = document.getElementById('express-regime-badge');

    if (expressContentEl && gexData.microstructure_summary) {
      const ms = gexData.microstructure_summary;
      expressContentEl.innerHTML = ms.full_html;
      if (expressBadgeEl) expressBadgeEl.innerText = ms.regime_label;
      if (expressPanelEl) {
        if (ms.theme_color === 'bull') {
          expressPanelEl.style.borderColor = 'var(--call-color)';
          expressPanelEl.style.background = 'rgba(255, 82, 82, 0.05)';
        } else {
          expressPanelEl.style.borderColor = 'var(--put-color)';
          expressPanelEl.style.background = 'rgba(0, 230, 118, 0.05)';
        }
      }
    }
  } catch (expressErr) {
    console.error('Express panel error:', expressErr);
  }

  try { renderGEXChart(); } catch (chartErr) { console.error('GEX Chart error:', chartErr); }
  try { populateInstitutionalMatrix(); } catch (matrixErr) { console.error('Matrix error:', matrixErr); }
  try { populateStockFutures(); } catch (stockErr) { console.error('Stock futures error:', stockErr); }
  try { renderRecent3DaysTable(); } catch (tblErr) { console.error('3-Day Table error:', tblErr); }
}
let currentSessionIndex = 5; // Default to Live T-Night Session (Index 5)

function renderHistorySessionSelector() {
  const container = document.getElementById('history-session-selector');
  if (!container || !gexData.history_6_sessions) return;

  const snapshots = gexData.history_6_sessions;
  container.innerHTML = snapshots.map((s, idx) => {
    const isActive = idx === currentSessionIndex;
    const activeStyle = isActive 
      ? 'background: var(--primary-accent); color: #000; font-weight: 700; border-color: var(--primary-accent); box-shadow: 0 0 10px rgba(0,210,255,0.4);' 
      : 'background: rgba(255,255,255,0.05); color: var(--text-main); border-color: var(--panel-border);';
    
    const shiftSign = s.shift_vs_prev >= 0 ? '+' : '';
    const shiftText = idx === 0 ? '' : ` (${shiftSign}${s.shift_vs_prev})`;

    return `
      <button class="btn session-snap-btn" data-session-idx="${idx}" style="padding: 4px 10px; font-size: 0.76rem; border-radius: 20px; transition: all 0.2s ease; ${activeStyle}">
        ${s.date_display} ${s.label}${shiftText}
      </button>
    `;
  }).join('');

  const btnList = container.querySelectorAll('.session-snap-btn');
  btnList.forEach(btn => {
    btn.addEventListener('click', (e) => {
      currentSessionIndex = parseInt(btn.getAttribute('data-session-idx'));
      renderHistorySessionSelector();
      renderDashboard();
    });
  });
}

function renderGEXChart() {
  const snapshots = gexData.history_6_sessions || [];
  const activeSnap = snapshots[currentSessionIndex] || gexData;
  
  let gexList = activeSnap.total_gex || gexData.total_gex;
  let title = `📊 3天歷史對比快照【${activeSnap.full_name || '全市場 GEX'}】履約價分布圖 (億 TWD)`;

  if (currentTab === 'weekly-gex') {
    gexList = activeSnap.weekly_gex || gexData.weekly_gex || gexList;
    title = `⚡ 3天歷史對比快照【${activeSnap.full_name || ''}】週三結算選 GEX 履約價分布圖`;
  } else if (currentTab === 'friday-gex') {
    gexList = activeSnap.friday_gex || gexData.friday_gex || gexList;
    title = `🇺🇸 3天歷史對比快照【${activeSnap.full_name || ''}】週五結算選 GEX 履約價分布圖`;
  } else if (currentTab === 'monthly-gex') {
    gexList = activeSnap.monthly_gex || gexData.monthly_gex || gexList;
    title = `🏛️ 3天歷史對比快照【${activeSnap.full_name || ''}】當月月選 GEX 履約價分布圖`;
  }

  document.getElementById('chart-panel-title').innerText = title;

  const currentPrice = gexData.spot_price;
  const strikes = gexList.map(item => item.strike);
  const callGex = gexList.map(item => item.call_gex);
  const putGex = gexList.map(item => item.put_gex);
  const netGex = gexList.map(item => item.net_gex);

  const traceCall = {
    x: strikes,
    y: callGex,
    name: 'Call GEX (🔴 台灣紅)',
    type: 'bar',
    marker: { color: '#ff5252', opacity: 0.85 }
  };

  const tracePut = {
    x: strikes,
    y: putGex,
    name: 'Put GEX (🟢 台灣綠)',
    type: 'bar',
    marker: { color: '#00e676', opacity: 0.85 }
  };

  const traceNet = {
    x: strikes,
    y: netGex,
    name: 'Net GEX (淨曝光)',
    type: 'scatter',
    mode: 'lines+markers',
    line: { color: '#00d2ff', width: 3 },
    marker: { size: 6 }
  };

  const layout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    barmode: 'relative',
    margin: { l: 50, r: 30, t: 30, b: 50 },
    xaxis: {
      title: '履約價 (Strike Price)',
      color: '#8b949e',
      gridcolor: 'rgba(255, 255, 255, 0.05)',
      tickmode: 'linear',
      dtick: 100
    },
    yaxis: {
      title: 'GEX 金額 (億 TWD)',
      color: '#8b949e',
      gridcolor: 'rgba(255, 255, 255, 0.08)'
    },
    legend: {
      font: { color: '#e6edf3' },
      orientation: 'h',
      y: 1.15
    },
    shapes: [
      {
        type: 'line',
        x0: currentPrice,
        x1: currentPrice,
        y0: 0,
        y1: 1,
        yref: 'paper',
        line: { color: '#ffffff', width: 2, dash: 'dash' }
      },
      {
        type: 'line',
        x0: gexData.zero_gamma_level,
        x1: gexData.zero_gamma_level,
        y0: 0,
        y1: 1,
        yref: 'paper',
        line: { color: '#ffd700', width: 2, dash: 'dot' }
      }
    ],
    annotations: [
      {
        x: currentPrice,
        y: 1,
        yref: 'paper',
        text: `現價 Spot: ${currentPrice}`,
        showarrow: true,
        arrowhead: 2,
        ax: 0,
        ay: -25,
        font: { color: '#ffffff', size: 12 },
        bgcolor: '#0088ff'
      },
      {
        x: gexData.zero_gamma_level,
        y: 0.9,
        yref: 'paper',
        text: `Zero Gamma: ${gexData.zero_gamma_level}`,
        showarrow: true,
        arrowhead: 2,
        ax: 40,
        ay: -25,
        font: { color: '#111', size: 12 },
        bgcolor: '#ffd700'
      }
    ]
  };

  const config = { responsive: true, displayModeBar: false };

  // ============================================================
  // Overlay Compare Mode: T日盤 vs T夜盤 (Live) side-by-side
  // ============================================================
  if (isOverlayMode) {
    const snapshots = gexData.history_6_sessions || [];
    const daySnap = snapshots.find(s => s.id === 't0_day') || snapshots[4] || activeSnap;
    const nightSnap = snapshots.find(s => s.id === 't0_night') || snapshots[5] || activeSnap;

    let dayList = daySnap.total_gex || gexData.total_gex;
    let nightList = nightSnap.total_gex || gexData.total_gex;

    if (currentTab === 'weekly-gex') {
      dayList = daySnap.weekly_gex || dayList;
      nightList = nightSnap.weekly_gex || nightList;
    } else if (currentTab === 'friday-gex') {
      dayList = daySnap.friday_gex || dayList;
      nightList = nightSnap.friday_gex || nightList;
    } else if (currentTab === 'monthly-gex') {
      dayList = daySnap.monthly_gex || dayList;
      nightList = nightSnap.monthly_gex || nightList;
    }

    const dayStrikes = dayList.map(d => d.strike);
    const nightStrikes = nightList.map(d => d.strike);

    const overlayTraces = [
      // T日盤 (半透明)
      { x: dayStrikes, y: dayList.map(d => d.call_gex), name: `☀️ 日盤 Call GEX`, type: 'bar', marker: { color: 'rgba(255,82,82,0.35)', line: { color: '#ff5252', width: 1 } } },
      { x: dayStrikes, y: dayList.map(d => d.put_gex),  name: `☀️ 日盤 Put GEX`,  type: 'bar', marker: { color: 'rgba(0,230,118,0.35)', line: { color: '#00e676', width: 1 } } },
      // T夜盤 (實線)
      { x: nightStrikes, y: nightList.map(d => d.call_gex), name: `🌙 夜盤 Call GEX (Live)`, type: 'bar', marker: { color: '#ff5252', opacity: 0.9 } },
      { x: nightStrikes, y: nightList.map(d => d.put_gex),  name: `🌙 夜盤 Put GEX (Live)`,  type: 'bar', marker: { color: '#00e676', opacity: 0.9 } },
      // Net GEX lines
      { x: dayStrikes,   y: dayList.map(d => d.net_gex),   name: '☀️ 日盤 Net GEX',   type: 'scatter', mode: 'lines', line: { color: 'rgba(0,210,255,0.4)', width: 2, dash: 'dot' } },
      { x: nightStrikes, y: nightList.map(d => d.net_gex), name: '🌙 夜盤 Net GEX', type: 'scatter', mode: 'lines+markers', line: { color: '#00d2ff', width: 3 }, marker: { size: 5 } }
    ];

    const overlayLayout = {
      paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
      barmode: 'overlay',
      margin: { l: 50, r: 30, t: 30, b: 50 },
      xaxis: { title: '履約價', color: '#8b949e', gridcolor: 'rgba(255,255,255,0.05)', tickmode: 'linear', dtick: 100 },
      yaxis: { title: 'GEX (億 TWD)', color: '#8b949e', gridcolor: 'rgba(255,255,255,0.08)' },
      legend: { font: { color: '#e6edf3' }, orientation: 'h', y: 1.18 },
      shapes: [
        { type: 'line', x0: daySnap.spot_price, x1: daySnap.spot_price, y0: 0, y1: 1, yref: 'paper', line: { color: 'rgba(255,255,255,0.5)', width: 1.5, dash: 'dot' } },
        { type: 'line', x0: nightSnap.spot_price || gexData.spot_price, x1: nightSnap.spot_price || gexData.spot_price, y0: 0, y1: 1, yref: 'paper', line: { color: '#ffffff', width: 2, dash: 'dash' } },
        { type: 'line', x0: gexData.zero_gamma_level, x1: gexData.zero_gamma_level, y0: 0, y1: 1, yref: 'paper', line: { color: '#ffd700', width: 2, dash: 'dot' } }
      ],
      annotations: [
        { x: nightSnap.spot_price || gexData.spot_price, y: 1, yref: 'paper', text: `🌙 夜盤 ${(nightSnap.spot_price || gexData.spot_price).toLocaleString()}`, showarrow: true, arrowhead: 2, ax: 0, ay: -28, font: { color: '#fff', size: 11 }, bgcolor: '#0088ff' },
        { x: daySnap.spot_price, y: 0.85, yref: 'paper', text: `☀️ 日盤 ${(daySnap.spot_price).toLocaleString()}`, showarrow: true, arrowhead: 2, ax: 40, ay: -20, font: { color: '#ccc', size: 10 }, bgcolor: 'rgba(0,136,255,0.4)' },
        { x: gexData.zero_gamma_level, y: 0.7, yref: 'paper', text: `Zero γ: ${gexData.zero_gamma_level}`, showarrow: false, font: { color: '#111', size: 10 }, bgcolor: '#ffd700', borderpad: 3 }
      ]
    };

    document.getElementById('chart-panel-title').innerText = `🔀 疊加對比：T日盤 vs T夜盤 (Live) GEX 分布`;
    Plotly.newPlot('gex-chart', overlayTraces, overlayLayout, config);
    return;
  }

  Plotly.newPlot('gex-chart', [traceCall, tracePut, traceNet], layout, config);
}

function populateInstitutionalMatrix() {
  const digestEl = document.getElementById('executive-digest-content');
  const futBody = document.getElementById('futures-5day-body');
  const cashBody = document.getElementById('cash-options-5day-body');

  const digest = gexData.executive_digest || {
    futures_summary: "前五大與前十大交易人多單加碼（+6,420口 / +9,850口），特定法人整體期貨結構偏多佈局。",
    cash_summary: "現貨買賣超呈現「外資大買超 +185.4億」與「投信連續買超 +62.8億」，自營商微幅調節 -24.5億。",
    options_structure: "期交所官方數據顯示：投信持倉 SC 賣出買權 -3.08億 與 BP 買進賣權 +0.003億（總部位 SC+BP 防守避險）；外資與自營商雙賣收取時間價值偏高檔看撐。",
    settlement_outlook: "🎯 綜合日盤官方結算籌碼與 GEX 避險牆，當前支撐位於 42,800 Put Wall，上檔壓力 43,400 Call Wall，預計結算偏向【高檔震盪看撐】。"
  };

  // Populate Night Session Institutional Trading Panel
  const nightTrading = gexData.night_institutional_trading || {
    tx_foreign_net_vol: -7,
    tx_foreign_net_amt: 0.27,
    tx_dealer_net_vol: -235,
    tx_dealer_net_amt: -1.98,
    tx_trust_net_vol: 0,
    mini_foreign_net_vol: 3394,
    micro_foreign_net_vol: 4200,
    night_sentiment: "⚖️ 外資夜盤中性觀望"
  };

  const badgeEl = document.getElementById('night-trading-badge');
  if (badgeEl) badgeEl.innerText = nightTrading.night_sentiment;

  const fVolEl = document.getElementById('night-foreign-vol');
  if (fVolEl) {
    const sign = nightTrading.tx_foreign_net_vol >= 0 ? '+' : '';
    fVolEl.innerText = `${sign}${nightTrading.tx_foreign_net_vol.toLocaleString()} 口`;
    fVolEl.style.color = nightTrading.tx_foreign_net_vol >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const fAmtEl = document.getElementById('night-foreign-amt');
  if (fAmtEl) {
    const sign = nightTrading.tx_foreign_net_amt >= 0 ? '+' : '';
    fAmtEl.innerText = `契約金額: ${sign}${nightTrading.tx_foreign_net_amt} 億 TWD`;
  }

  const mVolEl = document.getElementById('night-mini-vol');
  if (mVolEl) {
    const sign = nightTrading.mini_foreign_net_vol >= 0 ? '+' : '';
    mVolEl.innerText = `${sign}${nightTrading.mini_foreign_net_vol.toLocaleString()} 口`;
    mVolEl.style.color = nightTrading.mini_foreign_net_vol >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const uVolEl = document.getElementById('night-micro-vol');
  if (uVolEl) {
    const sign = nightTrading.micro_foreign_net_vol >= 0 ? '+' : '';
    uVolEl.innerText = `${sign}${nightTrading.micro_foreign_net_vol.toLocaleString()} 口`;
    uVolEl.style.color = nightTrading.micro_foreign_net_vol >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const dVolEl = document.getElementById('night-dealer-vol');
  if (dVolEl) {
    const sign = nightTrading.tx_dealer_net_vol >= 0 ? '+' : '';
    dVolEl.innerText = `${sign}${nightTrading.tx_dealer_net_vol.toLocaleString()} 口`;
    dVolEl.style.color = nightTrading.tx_dealer_net_vol >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const dAmtEl = document.getElementById('night-dealer-amt');
  if (dAmtEl) {
    const sign = nightTrading.tx_dealer_net_amt >= 0 ? '+' : '';
    dAmtEl.innerText = `契約金額: ${sign}${nightTrading.tx_dealer_net_amt} 億 TWD`;
  }

  const nSumEl = document.getElementById('night-trading-summary');
  if (nSumEl) {
    const defaultSum = "💡 <strong>夜盤籌碼白話解讀</strong>：外資大台夜盤僅微變 -7 口（外資無慌亂砍單），且在小台與微台大舉買超 +7,594 口吸收散戶籌碼，外資防守意圖強烈。";
    nSumEl.innerHTML = nightTrading.night_summary_text || defaultSum;
  }

  if (digestEl) {
    const shiftSummaryHtml = digest.session_shift_summary 
      ? `<div style="background: rgba(255, 215, 0, 0.08); border: 1px solid rgba(255, 215, 0, 0.25); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; font-size: 0.88rem; color: #ffd700;">${digest.session_shift_summary}</div>` 
      : '';

    digestEl.innerHTML = `
      ${shiftSummaryHtml}
      <p style="margin-bottom: 6px;">📈 <strong>期貨未平倉</strong>：${digest.futures_summary}</p>
      <p style="margin-bottom: 6px;">💵 <strong>現貨三大法人</strong>：${digest.cash_summary}</p>
      <p style="margin-bottom: 6px;">🏛️ <strong>選擇權籌碼結構 (BC/BP/SC/SP)</strong>：${digest.options_structure}</p>
      <p style="margin-top: 8px; color: var(--gold-accent); font-weight: 600;">${digest.settlement_outlook}</p>
    `;
  }

  const history = gexData.institutional_5day_history || [
    { date: "7/25", top5_net: -1250, top10_net: -3420, top5_spec_net: -980, top10_spec_net: -2100, foreign_fut_net: -18500, trust_fut_net: 2100, dealer_fut_net: -450, foreign_stock_net: -125.4, trust_stock_net: 42.1, dealer_stock_net: -18.6, foreign_opt_call_net: 0.45, foreign_opt_put_net: -1.82, trust_opt_call_net: -2.40, trust_opt_put_net: 0.002, dealer_opt_call_net: 1.25, dealer_opt_put_net: 0.85, pc_ratio: 102.4 },
    { date: "7/28", top5_net: -850, top10_net: -1200, top5_spec_net: -420, top10_spec_net: -890, foreign_fut_net: -16200, trust_fut_net: 2450, dealer_fut_net: -120, foreign_stock_net: -88.2, trust_stock_net: 38.5, dealer_stock_net: -12.4, foreign_opt_call_net: 0.62, foreign_opt_put_net: -1.45, trust_opt_call_net: -2.65, trust_opt_put_net: 0.002, dealer_opt_call_net: 1.40, dealer_opt_put_net: 0.92, pc_ratio: 104.1 },
    { date: "7/29", top5_net: 420, top10_net: 1150, top5_spec_net: 650, top10_spec_net: 1420, foreign_fut_net: -15100, trust_fut_net: 3100, dealer_fut_net: 380, foreign_stock_net: -45.6, trust_stock_net: 51.2, dealer_stock_net: -8.5, foreign_opt_call_net: 0.88, foreign_opt_put_net: -1.10, trust_opt_call_net: -2.85, trust_opt_put_net: 0.003, dealer_opt_call_net: 1.85, dealer_opt_put_net: 1.15, pc_ratio: 105.8 },
    { date: "7/30", top5_net: 3850, top10_net: 5920, top5_spec_net: 3210, top10_spec_net: 4850, foreign_fut_net: -12400, trust_fut_net: 3650, dealer_fut_net: 850, foreign_stock_net: 32.5, trust_stock_net: 48.0, dealer_stock_net: 14.2, foreign_opt_call_net: 1.45, foreign_opt_put_net: -0.65, trust_opt_call_net: -2.98, trust_opt_put_net: 0.003, dealer_opt_call_net: 2.30, dealer_opt_put_net: 1.42, pc_ratio: 107.2 },
    { date: "7/31", top5_net: 6420, top10_net: 9850, top5_spec_net: 5890, top10_spec_net: 8410, foreign_fut_net: -14200, trust_fut_net: 4200, dealer_fut_net: 1100, foreign_stock_net: 185.4, trust_stock_net: 62.8, dealer_stock_net: -24.5, foreign_opt_call_net: 0.60, foreign_opt_put_net: -0.28, trust_opt_call_net: -3.08, trust_opt_put_net: 0.003, dealer_opt_call_net: 1.83, dealer_opt_put_net: 1.42, pc_ratio: 108.5 }
  ];

  const formatCellSymmetric = (val, isAmount = false, suffix = '') => {
    if (val === undefined || val === null) return '-';
    const dot = val >= 0 ? '🔴' : '🟢';
    const formattedVal = isAmount ? (val >= 0 ? `+${val}` : `${val}`) : (val >= 0 ? `+${val.toLocaleString()}` : `${val.toLocaleString()}`);
    
    return `
      <div class="cell-num-wrapper">
        <span class="cell-num-val">${formattedVal}</span>
        <span class="cell-num-unit">${suffix}</span>
        <span class="cell-num-dot">${dot}</span>
      </div>
    `;
  };

  if (futBody) {
    futBody.innerHTML = history.map(h => `
      <tr>
        <td><strong>${h.date}</strong></td>
        <td>${formatCellSymmetric(h.top5_net, false, '口')}</td>
        <td>${formatCellSymmetric(h.top10_net, false, '口')}</td>
        <td>${formatCellSymmetric(h.top5_spec_net, false, '口')}</td>
        <td>${formatCellSymmetric(h.top10_spec_net, false, '口')}</td>
        <td>${formatCellSymmetric(h.foreign_fut_net, false, '口')}</td>
        <td>${formatCellSymmetric(h.trust_fut_net, false, '口')}</td>
        <td>${formatCellSymmetric(h.dealer_fut_net, false, '口')}</td>
      </tr>
    `).join('');
  }

  if (cashBody) {
    cashBody.innerHTML = history.map(h => `
      <tr>
        <td><strong>${h.date}</strong></td>
        <td>${formatCellSymmetric(h.foreign_stock_net, true, '億')}</td>
        <td>${formatCellSymmetric(h.trust_stock_net, true, '億')}</td>
        <td>${formatCellSymmetric(h.dealer_stock_net, true, '億')}</td>
        <td>Call: ${formatCellSymmetric(h.foreign_opt_call_net, true, '億')} / Put: ${formatCellSymmetric(h.foreign_opt_put_net, true, '億')}</td>
        <td>Call: ${formatCellSymmetric(h.trust_opt_call_net, true, '億')} / Put: ${formatCellSymmetric(h.trust_opt_put_net, true, '億')}</td>
        <td>Call: ${formatCellSymmetric(h.dealer_opt_call_net, true, '億')} / Put: ${formatCellSymmetric(h.dealer_opt_put_net, true, '億')}</td>
        <td><strong style="color: var(--text-main);">${h.pc_ratio}%</strong></td>
      </tr>
    `).join('');
  }
}

function populateStockFutures() {
  const tbody = document.getElementById('stock-futures-body');
  if (!tbody || !gexData.stock_futures) return;

  let list = [...gexData.stock_futures];

  const filterCat = document.getElementById('category-filter-select');
  if (filterCat && filterCat.value !== 'all') {
    list = list.filter(stk => stk.category === filterCat.value);
  }

  const filterNight = document.getElementById('filter-night-only');
  if (filterNight && filterNight.checked) {
    list = list.filter(stk => stk.has_night);
  }

  const searchInput = document.getElementById('search-stock-input');
  if (searchInput && searchInput.value.trim()) {
    const kw = searchInput.value.trim().toLowerCase();
    list = list.filter(stk => stk.code.toLowerCase().includes(kw) || stk.name.toLowerCase().includes(kw));
  }

  list.sort((a, b) => {
    let valA = a[currentSortKey];
    let valB = b[currentSortKey];

    if (valA === undefined) valA = '';
    if (valB === undefined) valB = '';

    if (typeof valA === 'string') valA = valA.toLowerCase();
    if (typeof valB === 'string') valB = valB.toLowerCase();

    if (valA < valB) return currentSortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return currentSortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  tbody.innerHTML = list.map(stk => {
    const trendBadge = stk.trend === 'Bull' 
      ? '<span class="badge-bull">▲ Bull (多)</span>' 
      : '<span class="badge-bear">▼ Bear (空)</span>';

    const catTag = `<span style="background: rgba(0,210,255,0.1); color: var(--primary-accent); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">${stk.category || '個股期貨'}</span>`;
    const changeClass = stk.change_pct >= 0 ? 'tag-bull' : 'tag-bear';
    const changeSign = stk.change_pct >= 0 ? '+' : '';

    return `
      <tr>
        <td><strong>${stk.code}</strong></td>
        <td>${stk.name}</td>
        <td>${catTag}</td>
        <td>${trendBadge}</td>
        <td><strong>${stk.spot_price.toLocaleString()}</strong></td>
        <td class="${changeClass}"><strong>${changeSign}${stk.change_pct}%</strong></td>
        <td>${stk.volume ? stk.volume.toLocaleString() : '-'} 口</td>
        <td class="${stk.foreign_net >= 0 ? 'tag-bull' : 'tag-bear'}">${stk.foreign_net >= 0 ? '+' : ''}${stk.foreign_net} 口</td>
        <td class="${stk.dealer_net >= 0 ? 'tag-bull' : 'tag-bear'}">${stk.dealer_net >= 0 ? '+' : ''}${stk.dealer_net} 口</td>
        <td>${stk.has_night ? '🌙 <span style="color: var(--call-color)">有夜盤</span>' : '⚪ 無夜盤'}</td>
      </tr>
    `;
  }).join('');
}

function renderRecent3DaysTable() {
  const tbody = document.getElementById('recent-3days-tbody');
  if (!tbody || !gexData) return;

  const list = gexData.recent_3_days_summary || [
    {
      date_label: "8/03 (T日)",
      day_date_note: "8/03 13:45",
      night_date_note: "8/04 05:00收盤",
      spot_price: gexData.spot_price || 43386.41,
      spot_change_val: gexData.spot_change_val !== undefined ? gexData.spot_change_val : 266.66,
      spot_change_pct: gexData.spot_change_pct !== undefined ? gexData.spot_change_pct : 0.62,
      two_price: gexData.two_price || 362.89,
      two_change_val: 15.04,
      two_change_pct: 4.32,
      day_txf_price: 43230.0,
      night_txf_price: gexData.txf_price || 43152.0,
      night_txf_shift: -78.0,
      zero_gamma_level: gexData.zero_gamma_level || 43080.0,
      zero_gamma_shift: -78.0,
      zero_gamma_regime: (gexData.microstructure_summary && gexData.microstructure_summary.regime_label) ? gexData.microstructure_summary.regime_label : "🔴 正 Gamma 波動度抑制區 (平穩震盪)",
      call_wall_strike: gexData.call_wall_strike || 43500,
      call_wall_shift: -100,
      put_wall_strike: gexData.put_wall_strike || 42900,
      put_wall_shift: 250,
      max_pain_strike: gexData.max_pain_strike || 43200,
      max_pain_shift: 200,
      pc_ratio: gexData.pc_ratio || 112.93,
      pc_ratio_desc: "🔴 偏多看撐",
      notes: "加權小漲 266 點，夜盤台指期微幅拉回 -78 點"
    },
    {
      date_label: "7/31 (T-1)",
      day_date_note: "7/31 13:45",
      night_date_note: "8/01 05:00收盤",
      spot_price: 43119.75,
      spot_change_val: 3186.45,
      spot_change_pct: 7.98,
      two_price: 347.85,
      two_change_val: 21.62,
      two_change_pct: 6.63,
      day_txf_price: 43678.0,
      night_txf_price: 42650.0,
      night_txf_shift: -1028.0,
      zero_gamma_level: 42970.0,
      zero_gamma_shift: -1028.0,
      zero_gamma_regime: "🟢 負 Gamma 波動度放大區 (避險引爆)",
      call_wall_strike: 43600,
      call_wall_shift: 300,
      put_wall_strike: 42400,
      put_wall_shift: -600,
      max_pain_strike: 43000,
      max_pain_shift: -678,
      pc_ratio: 108.5,
      pc_ratio_desc: "🔴 偏多看撐",
      notes: "日盤暴漲 +3,392 點，夜盤獲利拉回 -1,028 點"
    },
    {
      date_label: "7/30 (T-2)",
      day_date_note: "7/30 13:45",
      night_date_note: "7/31 05:00收盤",
      spot_price: 39933.30,
      spot_change_val: -105.88,
      spot_change_pct: -0.26,
      two_price: 326.23,
      two_change_val: -8.01,
      two_change_pct: -2.40,
      day_txf_price: 40270.0,
      night_txf_price: 40287.0,
      night_txf_shift: 17.0,
      zero_gamma_level: 40120.0,
      zero_gamma_shift: 17.0,
      zero_gamma_regime: "🔴 正 Gamma 區域震盪區 (平穩震盪)",
      call_wall_strike: 40600,
      call_wall_shift: 200,
      put_wall_strike: 40000,
      put_wall_shift: 200,
      max_pain_strike: 40300,
      max_pain_shift: 200,
      pc_ratio: 107.2,
      pc_ratio_desc: "🔴 偏多看撐",
      notes: "結算後高檔整理，夜盤平穩微升 +17 點"
    }
  ];

  tbody.innerHTML = list.map((item, idx) => {
    // ---- Session Pending (未開盤) Logic ----
    // For T日 (idx=0): check is_opened / is_night_opened flags from backend
    const isDayOpened   = item.is_opened   !== false;  // true for T-1, T-2; conditional for T日
    const isNightOpened = item.is_night_opened !== false;

    // Spot & OTC cells
    let spotStr, twoStr;
    if (!isDayOpened) {
      // Day not yet open — show pending badge
      spotStr = `<span style="color:var(--text-muted);font-size:0.82rem;">⏳ 未開盤</span><br/><span style="font-size:0.7rem;color:#555;">08:45 日盤開盤</span>`;
      twoStr  = `<span style="color:var(--text-muted);font-size:0.82rem;">⏳ 未開盤</span>`;
    } else {
      const spotSign  = item.spot_change_val >= 0 ? '+' : '';
      const spotClass = item.spot_change_val >= 0 ? 'tag-bull' : 'tag-bear';
      spotStr = `${item.spot_price.toLocaleString()} <span class="${spotClass}" style="font-size:0.75rem;">(${spotSign}${item.spot_change_val.toFixed(2)} / ${spotSign}${item.spot_change_pct.toFixed(2)}%)</span>`;
      const twoSign  = item.two_change_val >= 0 ? '+' : '';
      const twoClass = item.two_change_val >= 0 ? 'tag-bull' : 'tag-bear';
      twoStr = `${item.two_price.toLocaleString()} <span class="${twoClass}" style="font-size:0.75rem;">(${twoSign}${item.two_change_val.toFixed(2)} / ${twoSign}${item.two_change_pct.toFixed(2)}%)</span>`;
    }

    // Day TXF cell
    const dayNote = item.day_date_note ? item.day_date_note : '日盤 13:45';
    let dayStr;
    if (!isDayOpened) {
      dayStr = `<span style="color:var(--text-muted);font-size:0.82rem;">⏳ 未開盤</span><br/><span style="font-size:0.7rem;color:#555;">📅 ${dayNote}</span>`;
    } else {
      dayStr = `${item.day_txf_price.toLocaleString()}<br/><span style="font-size:0.7rem; color:var(--text-muted); font-weight:500;">📅 ${dayNote}</span>`;
    }

    // Night TXF cell
    const nightNote = item.night_date_note ? item.night_date_note : '次日 05:00收盤';
    let nightStr;
    if (!isNightOpened || item.night_txf_price == null) {
      nightStr = `<span style="color:var(--text-muted);font-size:0.82rem;">⏳ 15:00 夜盤開盤</span><br/><span style="font-size:0.7rem;color:var(--gold-accent);">🌙 ${nightNote}</span>`;
    } else {
      const nShiftSign  = item.night_txf_shift >= 0 ? '+' : '';
      const nShiftColor = item.night_txf_shift >= 0 ? 'var(--call-color)' : 'var(--put-color)';
      nightStr = `${item.night_txf_price.toLocaleString()} <span style="font-size:0.75rem; color:${nShiftColor}; font-weight:700;">(${nShiftSign}${item.night_txf_shift})</span><br/><span style="font-size:0.7rem; color:var(--gold-accent); font-weight:600;">🌙 ${nightNote}</span>`;
    }

    // GEX / Wall cells (always shown based on backend data)
    const zgSign  = item.zero_gamma_shift >= 0 ? '+' : '';
    const zgColor = item.zero_gamma_shift >= 0 ? 'var(--call-color)' : 'var(--put-color)';
    const zgStr   = `${item.zero_gamma_level.toLocaleString()} <span style="font-size:0.75rem; color:${zgColor}; font-weight:700;">(${zgSign}${item.zero_gamma_shift})</span><br/><span style="font-size:0.72rem; color:var(--gold-accent); font-weight:600;">${item.zero_gamma_regime}</span>`;

    const cwSign  = item.call_wall_shift >= 0 ? '+' : '';
    const cwColor = item.call_wall_shift >= 0 ? 'var(--call-color)' : 'var(--put-color)';
    const cwStr   = `${item.call_wall_strike.toLocaleString()} <span style="font-size:0.75rem; color:${cwColor}; font-weight:700;">(${cwSign}${item.call_wall_shift}點)</span>`;

    const pwSign  = item.put_wall_shift >= 0 ? '+' : '';
    const pwColor = item.put_wall_shift >= 0 ? 'var(--call-color)' : 'var(--put-color)';
    const pwStr   = `${item.put_wall_strike.toLocaleString()} <span style="font-size:0.75rem; color:${pwColor}; font-weight:700;">(${pwSign}${item.put_wall_shift}點)</span>`;

    const mpSign  = item.max_pain_shift >= 0 ? '+' : '';
    const mpColor = item.max_pain_shift >= 0 ? 'var(--call-color)' : 'var(--put-color)';
    const pcDesc  = item.pc_ratio_desc || (item.pc_ratio >= 100 ? '🔴 偏多看撐' : '🟢 偏空避險');
    const mpStr   = `${item.max_pain_strike.toLocaleString()} <span style="font-size:0.75rem; color:${mpColor}; font-weight:700;">(${mpSign}${item.max_pain_shift}點)</span><br/><span style="font-size:0.72rem; color:var(--primary-accent); font-weight:600;">P/C Ratio: ${item.pc_ratio}% (${pcDesc})</span>`;

    const isLatest    = idx === 0;
    const rowBg       = isLatest ? 'rgba(0, 210, 255, 0.05)' : 'transparent';
    const borderStyle = isLatest ? 'border-left: 3px solid var(--primary-accent);' : '';

    return `
      <tr style="background: ${rowBg}; ${borderStyle} border-bottom: 1px solid rgba(255,255,255,0.06);">
        <td style="padding: 10px 10px; font-weight: 700; color: var(--gold-accent);">${item.date_label}</td>
        <td style="padding: 10px 10px;">${spotStr}</td>
        <td style="padding: 10px 10px;">${twoStr}</td>
        <td style="padding: 10px 10px; font-weight: 600; color: var(--text-main);">${dayStr}</td>
        <td style="padding: 10px 10px;">${nightStr}</td>
        <td style="padding: 10px 10px;">${zgStr}</td>
        <td style="padding: 10px 10px;">${cwStr}</td>
        <td style="padding: 10px 10px;">${pwStr}</td>
        <td style="padding: 10px 10px;">${mpStr}</td>
        <td style="padding: 10px 10px; color: var(--text-muted); font-size: 0.78rem;">${item.notes}</td>
      </tr>
    `;
  }).join('');
}
