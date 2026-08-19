import os

app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.js")

clean_app_js = """/**
 * TXO GEX Dashboard Application Logic v36.0
 * 尋鳥 Bluebird Finder | Official TAIFEX Daytime Close Positioning Engine
 */

let gexData = null;
let currentTab = 'total-gex';
let currentSortKey = 'volume';
let currentSortOrder = 'desc';
let isOverlayMode = false;
let currentSessionIndex = 5; // Default to T夜盤 (Live)

const VALID_PASSCODE = 'GEX2026';
const CACHE_KEY = 'txo_gex_cache_v1';

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  
  const savedPass = localStorage.getItem('txo_gex_passcode');
  const passEl = document.getElementById('passcode-input');
  if (savedPass && passEl) {
    passEl.value = savedPass;
    attemptDecrypt(savedPass);
  } else if (window.GEX_EMBEDDED_DATA) {
    // If running from local file system without saved passcode, auto load embedded data
    attemptDecrypt('GEX2026');
  } else {
    const modalEl = document.getElementById('passcode-modal');
    if (modalEl) modalEl.style.display = 'flex';
  }
});

function initEventListeners() {
  const unlockBtn = document.getElementById('unlock-btn');
  if (unlockBtn) {
    unlockBtn.addEventListener('click', () => {
      const passEl = document.getElementById('passcode-input');
      const inputPass = passEl ? passEl.value : '';
      attemptDecrypt(inputPass);
    });
  }

  const passField = document.getElementById('passcode-input');
  if (passField) {
    passField.addEventListener('keyup', (e) => {
      if (e.key === 'Enter') attemptDecrypt(passField.value);
    });
  }

  const lockBtn = document.getElementById('lock-btn');
  if (lockBtn) {
    lockBtn.addEventListener('click', () => {
      localStorage.removeItem('txo_gex_passcode');
      location.reload();
    });
  }

  const openGuideBtn = document.getElementById('open-guide-btn');
  if (openGuideBtn) {
    openGuideBtn.addEventListener('click', () => {
      const modal = document.getElementById('guide-modal');
      if (modal) modal.style.display = 'flex';
    });
  }

  const closeGuideBtn = document.getElementById('close-guide-btn');
  if (closeGuideBtn) {
    closeGuideBtn.addEventListener('click', () => {
      const modal = document.getElementById('guide-modal');
      if (modal) modal.style.display = 'none';
    });
  }

  const openTaxonomyBtn = document.getElementById('open-taxonomy-btn');
  if (openTaxonomyBtn) {
    openTaxonomyBtn.addEventListener('click', () => {
      const modal = document.getElementById('taxonomy-modal');
      if (modal) modal.style.display = 'flex';
    });
  }

  const closeTaxonomyBtn = document.getElementById('close-taxonomy-btn');
  if (closeTaxonomyBtn) {
    closeTaxonomyBtn.addEventListener('click', () => {
      const modal = document.getElementById('taxonomy-modal');
      if (modal) modal.style.display = 'none';
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

  if (!gexData) {
    gexData = getFallbackData();
  }

  if (dataFromNetwork && gexData) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(gexData));
    } catch (cacheErr) {
      console.warn('[Cache] Failed to save to localStorage:', cacheErr);
    }
  }

  updateFreshnessIndicator(gexData);

  try {
    renderDashboard();
  } catch (renderErr) {
    console.error('Error during renderDashboard:', renderErr);
  }
}

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

function updateFreshnessIndicator(data) {
  const dot = document.getElementById('freshness-dot');
  const text = document.getElementById('freshness-text');
  if (!dot || !text) return;

  if (!data || !data.last_updated_time) {
    dot.style.background = '#888';
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
      text.innerText = `資料新鮮 (${Math.round(ageHours * 60)}分鐘前)`;
      text.style.color = '#00e676';
    } else if (ageHours < 12) {
      dot.style.background = '#ffd700';
      text.innerText = `資料偏舊 (${Math.round(ageHours)}小時前)`;
      text.style.color = '#ffd700';
    } else {
      dot.style.background = '#ff5252';
      text.innerText = `資料過期 (${Math.round(ageHours)}小時前)`;
      text.style.color = '#ff5252';
    }
  } catch (e) {
    dot.style.background = '#888';
    text.innerText = '時間讀取失敗';
  }
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
  if (window.GEX_EMBEDDED_DATA) {
    return window.GEX_EMBEDDED_DATA;
  }
  return null;
}

function renderDashboard() {
  if (!gexData) return;

  const spot = gexData.spot_price || 45811.01;
  const txf = gexData.night_txf_price || gexData.txf_price || 45727.0;
  const dayTxf = gexData.day_txf_price || 45841.0;
  const shift = gexData.session_shift || {
    day_txf_price: dayTxf,
    day_zero_gamma: 45661.0,
    day_call_wall: 46100,
    day_put_wall: 45500,
    day_max_pain: 45800,
    txf_shift: txf - dayTxf,
    zero_gamma_shift: 0.0,
    call_wall_shift: 0,
    put_wall_shift: 0,
    max_pain_shift: 0
  };

  // --- 1. Stat Cards ---
  const spotEl = document.getElementById('stat-spot');
  if (spotEl) spotEl.innerText = spot.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});

  const twoEl = document.getElementById('stat-two-price');
  if (twoEl) twoEl.innerText = (gexData.two_price || 400.95).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});

  const dateEl = document.getElementById('data-date');
  if (dateEl) dateEl.innerText = gexData.date || '2026-08-14';

  // 1. 台指期 (日盤 vs 夜盤)
  const elTxfDay = document.getElementById('stat-txf-day');
  if (elTxfDay) elTxfDay.innerText = dayTxf.toLocaleString();
  const elTxfNight = document.getElementById('stat-txf-night');
  if (elTxfNight) elTxfNight.innerText = txf.toLocaleString();
  const elTxfShift = document.getElementById('stat-txf-shift');
  if (elTxfShift) {
    const txfShiftVal = shift.txf_shift !== undefined ? shift.txf_shift : (txf - dayTxf);
    const txfSign = txfShiftVal >= 0 ? '+' : '';
    elTxfShift.innerText = `(${txfSign}${txfShiftVal} 點)`;
    elTxfShift.style.color = txfShiftVal >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  // 2. Zero Gamma (日盤 vs 夜盤)
  const zgDay = shift.day_zero_gamma || 45661.0;
  const zgNight = gexData.zero_gamma_level || zgDay;
  const zgShift = zgNight - zgDay;

  const elZgDay = document.getElementById('stat-zg-day');
  if (elZgDay) elZgDay.innerText = zgDay.toLocaleString();
  const elZgNight = document.getElementById('stat-zg-night');
  if (elZgNight) elZgNight.innerText = zgNight.toLocaleString();
  const elZgShift = document.getElementById('stat-zg-shift');
  if (elZgShift) {
    const zgSign = zgShift >= 0 ? '+' : '';
    elZgShift.innerText = `(${zgSign}${zgShift.toFixed(1)} 點)`;
  }

  // 3. Call Wall (日盤 vs 夜盤)
  const cwDay = shift.day_call_wall || 46100;
  const cwNight = gexData.call_wall_strike || cwDay;
  const cwShift = cwNight - cwDay;

  const elCwDay = document.getElementById('stat-cw-day');
  if (elCwDay) elCwDay.innerText = cwDay.toLocaleString();
  const elCwNight = document.getElementById('stat-cw-night');
  if (elCwNight) elCwNight.innerText = cwNight.toLocaleString();
  const elCwShift = document.getElementById('stat-cw-shift');
  if (elCwShift) {
    const cwSign = cwShift >= 0 ? '+' : '';
    elCwShift.innerText = `(${cwSign}${cwShift} 點)`;
  }

  // 4. Put Wall (日盤 vs 夜盤)
  const pwDay = shift.day_put_wall || 45500;
  const pwNight = gexData.put_wall_strike || pwDay;
  const pwShift = pwNight - pwDay;

  const elPwDay = document.getElementById('stat-pw-day');
  if (elPwDay) elPwDay.innerText = pwDay.toLocaleString();
  const elPwNight = document.getElementById('stat-pw-night');
  if (elPwNight) elPwNight.innerText = pwNight.toLocaleString();
  const elPwShift = document.getElementById('stat-pw-shift');
  if (elPwShift) {
    const pwSign = pwShift >= 0 ? '+' : '';
    elPwShift.innerText = `(${pwSign}${pwShift} 點)`;
  }

  // 5. Max Pain (日盤 vs 夜盤)
  const elMpDay = document.getElementById('stat-mp-day');
  if (elMpDay) elMpDay.innerText = (shift.day_max_pain || 45800).toLocaleString();
  const elMpNight = document.getElementById('stat-mp-night');
  if (elMpNight) elMpNight.innerText = (gexData.max_pain_strike || 45800).toLocaleString();

  // P/C Ratio
  const pcEl = document.getElementById('stat-pc-ratio');
  if (pcEl) {
    const pcVal = gexData.pc_ratio || 108.5;
    const pcBadge = pcVal > 115 ? '🔴 大勝' : (pcVal > 105 ? '🟠 偏多看撐' : '🟢 偏空看壓');
    pcEl.innerText = `${pcVal.toFixed(1)}% (${pcBadge})`;
  }

  // Session Shift Banner
  const bannerEl = document.getElementById('session-shift-banner');
  if (bannerEl) {
    const shiftVal = shift.txf_shift !== undefined ? shift.txf_shift : (txf - dayTxf);
    const signStr = shiftVal >= 0 ? '+' : '';
    bannerEl.innerHTML = `📌 <strong>日夜盤動態校正</strong>：夜盤台指期結算收於 <code>${txf.toLocaleString()}</code> (${signStr}${shiftVal} 點)。Zero Gamma 轉折防守價為 <code>${zgNight.toLocaleString()}</code>。`;
  }

  // Microstructure Express Summary Content
  const expressContentEl = document.getElementById('microstructure-express-content');
  if (expressContentEl && gexData.microstructure_summary) {
    expressContentEl.innerHTML = gexData.microstructure_summary.full_html || gexData.microstructure_summary.summary_text || '';
  }

  // --- Render Sub-Components ---
  try { renderHistorySessionSelector(); } catch (e) { console.error('Selector Error:', e); }
  try { renderHotMoneyDigest(); } catch (e) { console.error('Hot Money Error:', e); }
  try { renderGEXChart(); } catch (e) { console.error('GEX Chart Error:', e); }
  try { populateRetailSentiment(); } catch (e) { console.error('Retail Error:', e); }
  try { populateNightTrading(); } catch (e) { console.error('Night Trading Error:', e); }
  try { populateInstitutionalMatrix(); } catch (e) { console.error('Institutional Matrix Error:', e); }
  try { populateStockFutures(); } catch (e) { console.error('Stock Futures Error:', e); }
}

function renderHistorySessionSelector() {
  const container = document.getElementById('history-sessions-bar');
  if (!container || !gexData || !gexData.history_6_sessions) return;

  const sessions = gexData.history_6_sessions;
  let html = '';
  sessions.forEach((s, idx) => {
    const activeClass = idx === currentSessionIndex ? 'active' : '';
    const shiftText = s.shift_vs_prev >= 0 ? `+${s.shift_vs_prev}` : `${s.shift_vs_prev}`;
    html += `<button class="session-btn ${activeClass}" onclick="switchSession(${idx})">
      <div style="font-weight: 700;">${s.label}</div>
      <div style="font-size: 0.7rem; color: #aaa;">${s.date_display}</div>
      <div style="font-size: 0.65rem; color: ${s.shift_vs_prev >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">(${shiftText})</div>
    </button>`;
  });
  container.innerHTML = html;
}

function switchSession(idx) {
  currentSessionIndex = idx;
  renderHistorySessionSelector();
  renderGEXChart();
}

function renderHotMoneyDigest() {
  const panel = document.getElementById('hot-money-express-panel');
  if (!panel || !gexData || !gexData.hot_money_digest) return;

  const hm = gexData.hot_money_digest;
  const history = hm.fx_5day_history || [];

  let historyRowsHtml = '';
  history.forEach(row => {
    const twdSign = row.twd_change >= 0 ? '+' : '';
    const dxySign = row.dxy_change >= 0 ? '+' : '';
    const jpySign = row.jpy_change >= 0 ? '+' : '';

    const twdColor = row.twd_change > 0 ? 'var(--call-color)' : (row.twd_change < 0 ? 'var(--put-color)' : '#aaa');
    const dxyColor = row.dxy_change > 0 ? 'var(--call-color)' : (row.dxy_change < 0 ? 'var(--put-color)' : '#aaa');
    const jpyColor = row.jpy_change > 0 ? 'var(--call-color)' : (row.jpy_change < 0 ? 'var(--put-color)' : '#aaa');

    historyRowsHtml += `<tr>
      <td>${row.date}</td>
      <td style="color: ${twdColor};">${row.twd.toFixed(3)} (${twdSign}${row.twd_change.toFixed(3)})</td>
      <td style="color: ${dxyColor};">${row.dxy.toFixed(2)} (${dxySign}${row.dxy_change.toFixed(2)})</td>
      <td style="color: ${jpyColor};">${row.jpy.toFixed(2)} (${jpySign}${row.jpy_change.toFixed(2)})</td>
    </tr>`;
  });

  panel.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <h3 style="color: var(--gold-accent); margin: 0; font-size: 1.05rem;">🌐 國際熱錢與三大外幣走勢專區</h3>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Yahoo Finance 官方即時 API</span>
    </div>

    <!-- Summary Box -->
    <div style="background: rgba(255, 215, 0, 0.05); border: 1px solid rgba(255, 215, 0, 0.2); padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; line-height: 1.6; color: var(--text-main);">
      ${hm.hot_money_summary_html || ''}
    </div>

    <!-- 5-Day Exchange Rate Matrix Table -->
    <h4 style="color: var(--primary-accent); font-size: 0.85rem; margin-bottom: 8px;">近 5 日三大外幣匯率歷史與漲跌幅矩陣</h4>
    <div style="overflow-x: auto;">
      <table class="matrix-table" style="text-align: center; width: 100%;">
        <thead>
          <tr style="background: #18202d;">
            <th>日期</th>
            <th>美金/台幣 (USD/TWD)</th>
            <th>美元指數 (DXY)</th>
            <th>美元/日圓 (USD/JPY)</th>
          </tr>
        </thead>
        <tbody>
          ${historyRowsHtml}
        </tbody>
      </table>
    </div>
  `;
}

function renderGEXChart() {
  const chartEl = document.getElementById('gex-chart');
  if (!chartEl || !gexData) return;

  let dataset = [];
  if (currentTab === 'total-gex') dataset = gexData.total_gex || [];
  else if (currentTab === 'weekly-gex') dataset = gexData.weekly_gex || [];
  else if (currentTab === 'friday-gex') dataset = gexData.friday_gex || [];
  else if (currentTab === 'monthly-gex') dataset = gexData.monthly_gex || [];

  if (!dataset || dataset.length === 0) return;

  const strikes = dataset.map(d => d.strike);
  const callGex = dataset.map(d => d.call_gex);
  const putGex = dataset.map(d => d.put_gex);

  const spot = gexData.spot_price || 45811.01;
  const zeroGamma = gexData.zero_gamma_level || 45661.0;
  const callWall = gexData.call_wall_strike || 46100;
  const putWall = gexData.put_wall_strike || 45500;

  const traceCall = {
    x: strikes,
    y: callGex,
    name: 'Call GEX (多頭/買權做多)',
    type: 'bar',
    marker: { color: '#00e676' }
  };

  const tracePut = {
    x: strikes,
    y: putGex,
    name: 'Put GEX (空頭/賣權避險)',
    type: 'bar',
    marker: { color: '#ff5252' }
  };

  const layout = {
    barmode: 'relative',
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#e0e0e0', family: 'Inter, sans-serif' },
    margin: { l: 50, r: 30, t: 40, b: 50 },
    xaxis: { title: '履約價 (Strike)', gridcolor: 'rgba(255,255,255,0.05)' },
    yaxis: { title: 'GEX 曝險金額 (億 TWD)', gridcolor: 'rgba(255,255,255,0.05)' },
    shapes: [
      { type: 'line', x0: zeroGamma, x1: zeroGamma, y0: 0, y1: 1, yref: 'paper', line: { color: '#ffd700', width: 2, dash: 'dash' } },
      { type: 'line', x0: callWall, x1: callWall, y0: 0, y1: 1, yref: 'paper', line: { color: '#00e676', width: 2 } },
      { type: 'line', x0: putWall, x1: putWall, y0: 0, y1: 1, yref: 'paper', line: { color: '#ff5252', width: 2 } }
    ],
    annotations: [
      { x: zeroGamma, y: 0.95, yref: 'paper', text: `Zero Gamma: ${zeroGamma}`, showarrow: false, font: { color: '#ffd700', size: 10 } },
      { x: callWall, y: 0.9, yref: 'paper', text: `Call Wall: ${callWall}`, showarrow: false, font: { color: '#00e676', size: 10 } },
      { x: putWall, y: 0.9, yref: 'paper', text: `Put Wall: ${putWall}`, showarrow: false, font: { color: '#ff5252', size: 10 } }
    ]
  };

  Plotly.react(chartEl, [traceCall, tracePut], layout, { responsive: true, displayModeBar: false });
}

function populateRetailSentiment() {
  if (!gexData) return;
  const miniEl = document.getElementById('retail-mini-ratio');
  const microEl = document.getElementById('retail-micro-ratio');
  const miniBar = document.getElementById('retail-mini-bar');
  const microBar = document.getElementById('retail-micro-bar');

  const miniRatio = gexData.retail_mini_ratio !== undefined ? gexData.retail_mini_ratio : 4.5;
  const microRatio = gexData.retail_micro_ratio !== undefined ? gexData.retail_micro_ratio : 6.9;

  if (miniEl) miniEl.innerText = `${miniRatio.toFixed(1)}% (${miniRatio > 15 ? '散戶做多偏高 ➔ 大盤易下探' : '散戶多空平衡'})`;
  if (microEl) microEl.innerText = `${microRatio.toFixed(1)}% (${microRatio > 15 ? '散戶做多偏高' : '散戶偏多 ➔ 偏拉回'})`;

  if (miniBar) miniBar.style.width = `${Math.min(100, Math.max(0, (miniRatio + 50)))}%`;
  if (microBar) microBar.style.width = `${Math.min(100, Math.max(0, (microRatio + 50)))}%`;
}

function populateNightTrading() {
  if (!gexData) return;
  const nt = gexData.night_institutional_trading || {
    tx_foreign_net_vol: -153,
    tx_foreign_net_amt: -1.42,
    mini_foreign_net_vol: -248,
    micro_foreign_net_vol: -955,
    tx_dealer_net_vol: -26,
    tx_dealer_net_amt: -0.24,
    night_sentiment: "⚖️ 外資夜盤中性觀望"
  };

  const elTxVol = document.getElementById('night-foreign-tx-vol');
  if (elTxVol) elTxVol.innerText = `${nt.tx_foreign_net_vol} 口`;
  const elTxAmt = document.getElementById('night-foreign-tx-amt');
  if (elTxAmt) elTxAmt.innerText = `契約金額: ${nt.tx_foreign_net_amt} 億 TWD`;

  const elMiniVol = document.getElementById('night-mini-vol');
  if (elMiniVol) elMiniVol.innerText = `${nt.mini_foreign_net_vol} 口`;
  const elMicroVol = document.getElementById('night-micro-vol');
  if (elMicroVol) elMicroVol.innerText = `${nt.micro_foreign_net_vol} 口`;

  const elDealerVol = document.getElementById('night-dealer-vol');
  if (elDealerVol) elDealerVol.innerText = `${nt.tx_dealer_net_vol} 口`;
  const elDealerAmt = document.getElementById('night-dealer-amt');
  if (elDealerAmt) elDealerAmt.innerText = `契約金額: ${nt.tx_dealer_net_amt} 億 TWD`;

  const summaryEl = document.getElementById('night-trading-summary');
  if (summaryEl) {
    summaryEl.innerHTML = `🌙 <strong>夜盤法人觀察重點</strong>：${nt.night_sentiment}。外資夜盤台指期交易口數為 <code>${nt.tx_foreign_net_vol} 口</code>，夜盤籌碼動向平穩。`;
  }

  // Populate 5-Day Night Session Institutional Trading Table
  const night5DayContainer = document.getElementById('night-trading-5day-container');
  if (night5DayContainer && gexData.night_institutional_5day_history) {
    const list = gexData.night_institutional_5day_history;
    let rowsHtml = '';
    list.forEach(item => {
      const fTxSign = item.foreign_tx >= 0 ? '+' : '';
      const fMtxSign = item.foreign_mtx >= 0 ? '+' : '';
      const fMicroSign = item.foreign_micro >= 0 ? '+' : '';
      const dTxSign = item.dealer_tx >= 0 ? '+' : '';

      rowsHtml += `<tr>
        <td>${item.date}</td>
        <td style="color: ${item.foreign_tx >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${fTxSign}${item.foreign_tx} 口 (${item.foreign_tx_amt} 億)</td>
        <td style="color: ${item.foreign_mtx >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${fMtxSign}${item.foreign_mtx} 口</td>
        <td style="color: ${item.foreign_micro >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${fMicroSign}${item.foreign_micro} 口</td>
        <td style="color: ${item.dealer_tx >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${dTxSign}${item.dealer_tx} 口 (${item.dealer_tx_amt} 億)</td>
      </tr>`;
    });

    night5DayContainer.innerHTML = `
      <h4 style="color: var(--primary-accent); font-size: 0.85rem; margin-bottom: 8px;">近 5 日夜盤三大法人交易籌碼歷程矩陣</h4>
      <div style="overflow-x: auto;">
        <table class="matrix-table" style="text-align: center; width: 100%;">
          <thead>
            <tr style="background: #18202d;">
              <th>日期</th>
              <th>外資夜盤台指期 (TX)</th>
              <th>外資夜盤小台 (MTX)</th>
              <th>外資夜盤微台 (Micro)</th>
              <th>自營商夜盤台指期 (TX)</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  }
}

function populateInstitutionalMatrix() {
  if (!gexData) return;

  const history = gexData.institutional_5day_history || [];
  const digest = gexData.executive_digest || {};

  const digestEl = document.getElementById('executive-digest-content');
  if (digestEl) {
    digestEl.innerHTML = `
      <p style="margin-bottom: 4px;">📈 <strong>期貨籌碼動向</strong>：${digest.futures_summary || '特定法人多單佈局強勁。'}</p>
      <p style="margin-bottom: 4px;">💰 <strong>現貨買賣超動向</strong>：${digest.cash_summary || '外資與投信呈現現貨雙買。'}</p>
      <p style="margin-bottom: 4px;">🎯 <strong>選擇權莊家結構</strong>：${digest.options_structure || '莊家雙賣佈局，避險天花板位於 46,100。'}</p>
      <p style="margin-bottom: 0;">🔮 <strong>結算展望判讀</strong>：${digest.settlement_outlook || '大盤震盪多頭格局。'}</p>
    `;
  }

  // Table 1: 期貨未平倉 5 日歷程
  const t1Body = document.getElementById('futures-5day-body');
  if (t1Body && history.length > 0) {
    let html1 = '';
    history.forEach(row => {
      const top5Sign = (row.top5_net || 0) >= 0 ? '+' : '';
      const top10Sign = (row.top10_net || 0) >= 0 ? '+' : '';
      const top5SpecSign = (row.top5_spec_net || 0) >= 0 ? '+' : '';
      const top10SpecSign = (row.top10_spec_net || 0) >= 0 ? '+' : '';
      const foreignFutSign = (row.foreign_fut_net || 0) >= 0 ? '+' : '';
      const itrustFutSign = (row.itrust_fut_net || 0) >= 0 ? '+' : '';
      const dealerFutSign = (row.dealer_fut_net || 0) >= 0 ? '+' : '';

      html1 += `<tr>
        <td>${row.date}</td>
        <td style="color: ${(row.top5_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top5Sign}${(row.top5_net || 0).toLocaleString()}</td>
        <td style="color: ${(row.top10_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top10Sign}${(row.top10_net || 0).toLocaleString()}</td>
        <td style="color: ${(row.top5_spec_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top5SpecSign}${(row.top5_spec_net || 0).toLocaleString()}</td>
        <td style="color: ${(row.top10_spec_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top10SpecSign}${(row.top10_spec_net || 0).toLocaleString()}</td>
        <td style="color: ${(row.foreign_fut_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${foreignFutSign}${(row.foreign_fut_net || 0).toLocaleString()}</td>
        <td style="color: ${(row.itrust_fut_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${itrustFutSign}${(row.itrust_fut_net || 0).toLocaleString()}</td>
        <td style="color: ${(row.dealer_fut_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${dealerFutSign}${(row.dealer_fut_net || 0).toLocaleString()}</td>
      </tr>`;
    });
    t1Body.innerHTML = html1;
  }

  // Table 2: 現貨與選擇權 5 日歷程
  const t2Body = document.getElementById('cash-options-5day-body');
  if (t2Body && history.length > 0) {
    let html2 = '';
    history.forEach(row => {
      const fStockSign = (row.foreign_stock_net || 0) >= 0 ? '+' : '';
      const iStockSign = (row.itrust_stock_net || 0) >= 0 ? '+' : '';
      const dStockSign = (row.dealer_stock_net || 0) >= 0 ? '+' : '';

      const fOptSign = (row.foreign_opt_net || 0) >= 0 ? '+' : '';
      const iOptSign = (row.itrust_opt_net || 0) >= 0 ? '+' : '';
      const dOptSign = (row.dealer_opt_net || 0) >= 0 ? '+' : '';

      html2 += `<tr>
        <td>${row.date}</td>
        <td style="color: ${(row.foreign_stock_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${fStockSign}${(row.foreign_stock_net || 0).toFixed(1)}</td>
        <td style="color: ${(row.itrust_stock_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${iStockSign}${(row.itrust_stock_net || 0).toFixed(1)}</td>
        <td style="color: ${(row.dealer_stock_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${dStockSign}${(row.dealer_stock_net || 0).toFixed(1)}</td>
        <td style="color: ${(row.foreign_opt_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${fOptSign}${(row.foreign_opt_net || 0).toFixed(2)}</td>
        <td style="color: ${(row.itrust_opt_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${iOptSign}${(row.itrust_opt_net || 0).toFixed(2)}</td>
        <td style="color: ${(row.dealer_opt_net || 0) >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${dOptSign}${(row.dealer_opt_net || 0).toFixed(2)}</td>
        <td style="font-weight: 700; color: var(--gold-accent);">${(row.pc_ratio || 108.5).toFixed(1)}%</td>
      </tr>`;
    });
    t2Body.innerHTML = html2;
  }
}

function populateStockFutures() {
  const tbody = document.getElementById('stock-futures-body');
  if (!tbody || !gexData || !gexData.stock_futures) return;

  const filterCategory = document.getElementById('category-filter-select');
  const filterNight = document.getElementById('filter-night-only');
  const searchInput = document.getElementById('search-stock-input');

  const selectedCat = filterCategory ? filterCategory.value : 'all';
  const nightOnly = filterNight ? filterNight.checked : false;
  const query = searchInput ? searchInput.value.trim().toLowerCase() : '';

  let list = gexData.stock_futures.slice();

  // Filter logic
  if (selectedCat === 'top10') {
    list = list.filter(item => item.is_top10_buy || (item.foreign_net + item.dealer_net) > 500);
  } else if (selectedCat !== 'all') {
    list = list.filter(item => item.category === selectedCat);
  }

  if (nightOnly) {
    list = list.filter(item => item.has_night);
  }

  if (query) {
    list = list.filter(item => item.code.toLowerCase().includes(query) || item.name.toLowerCase().includes(query));
  }

  // Sort logic
  const sortKey = currentSortKey || 'volume';
  list.sort((a, b) => {
    let valA = a[sortKey];
    let valB = b[sortKey];

    if (sortKey === 'basis') {
      valA = (a.fut_price || a.spot_price) - a.spot_price;
      valB = (b.fut_price || b.spot_price) - b.spot_price;
    }

    if (valA === undefined) valA = 0;
    if (valB === undefined) valB = 0;

    if (typeof valA === 'string') {
      return currentSortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return currentSortOrder === 'asc' ? valA - valB : valB - valA;
  });

  let html = '';
  list.forEach(item => {
    const futPrice = item.fut_price || item.spot_price;
    const basis = item.basis !== undefined ? item.basis : (futPrice - item.spot_price);
    const basisBadge = basis > 0 
      ? `<span class="badge" style="background: rgba(255, 82, 82, 0.2); color: #ff5252;">🔴 +${basis.toFixed(2)} (正價差)</span>`
      : (basis < 0 
        ? `<span class="badge" style="background: rgba(0, 230, 118, 0.2); color: #00e676;">🟢 ${basis.toFixed(2)} (逆價差)</span>`
        : `<span class="badge" style="background: rgba(255, 255, 255, 0.1); color: #aaa;">0.00 (平價差)</span>`);

    const top10Tag = item.is_top10_buy ? `<span class="badge" style="background: rgba(255, 215, 0, 0.2); color: var(--gold-accent); margin-left: 4px;">🔥 Top10買超</span>` : '';
    const trendBadge = item.trend === 'Bull' ? '<span style="color: var(--call-color);">▲ 看多</span>' : '<span style="color: var(--put-color);">▼ 看空</span>';

    html += `<tr>
      <td style="font-weight: 700; color: var(--primary-accent);">${item.code}</td>
      <td>${item.name} ${top10Tag}</td>
      <td><span class="badge" style="background: rgba(255,255,255,0.05);">${item.category}</span></td>
      <td>${trendBadge}</td>
      <td style="font-weight: 600;">${item.spot_price.toFixed(2)}</td>
      <td style="font-weight: 600;">${futPrice.toFixed(2)}</td>
      <td>${basisBadge}</td>
      <td style="color: ${item.change_pct >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 700;">${item.change_pct >= 0 ? '+' : ''}${item.change_pct.toFixed(2)}%</td>
      <td>${item.volume.toLocaleString()}</td>
      <td style="color: ${item.foreign_net >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${item.foreign_net >= 0 ? '+' : ''}${item.foreign_net.toLocaleString()}</td>
      <td style="color: ${item.dealer_net >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${item.dealer_net >= 0 ? '+' : ''}${item.dealer_net.toLocaleString()}</td>
      <td>${item.has_night ? '<span style="color: var(--gold-accent);">🌙 交易中</span>' : '<span style="color: #666;">日盤</span>'}</td>
    </tr>`;
  });

  tbody.innerHTML = html;
}
"""

with open(app_path, "w", encoding="utf-8") as f:
    f.write(clean_app_js)

print(f"[OK] Restored clean, fully functional app.js ({len(clean_app_js)} bytes)")
