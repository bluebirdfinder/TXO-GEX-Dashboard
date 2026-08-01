/**
 * TXO GEX Dashboard Application Logic v29.0
 * 尋鳥 Bluebird Finder | Official TAIFEX Daytime Close Positioning Engine
 */

let gexData = null;
let currentTab = 'total-gex';
let currentSortKey = 'volume';
let currentSortOrder = 'desc';

const VALID_PASSCODE = 'GEX2026';

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
}

async function attemptDecrypt(passcode) {
  const errEl = document.getElementById('passcode-error');
  errEl.style.display = 'none';

  const cleanPass = (passcode || '').trim().toUpperCase();

  if (cleanPass !== VALID_PASSCODE) {
    errEl.style.display = 'block';
    return;
  }

  try {
    let res = await fetch('data/encrypted_gex.json?v=' + Date.now());
    if (res.ok) {
      const encObj = await res.json();
      if (encObj.payload) {
        gexData = decryptPayload(encObj.payload, passcode);
      }
    }
    
    if (!gexData) {
      let rawRes = await fetch('data/gex_data.json?v=' + Date.now());
      if (rawRes.ok) {
        gexData = await rawRes.json();
      }
    }

    if (!gexData) {
      gexData = getFallbackData();
    }

    if (gexData && gexData.spot_price) {
      localStorage.setItem('txo_gex_passcode', cleanPass);
      document.getElementById('passcode-modal').style.display = 'none';
      renderDashboard();
      return;
    }
  } catch (err) {
    console.error('Decryption error:', err);
    gexData = getFallbackData();
    if (gexData) {
      localStorage.setItem('txo_gex_passcode', cleanPass);
      document.getElementById('passcode-modal').style.display = 'none';
      renderDashboard();
      return;
    }
  }

  errEl.style.display = 'block';
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
  const spot = 43119.75;
  const strikes = [];
  for (let i = -15; i <= 15; i++) strikes.push(Math.round(spot/50)*50 + i * 50);

  const total_gex = strikes.map(k => ({
    strike: k,
    call_gex: Math.round(Math.max(0, 18 - Math.abs(k - (spot + 300))/50) * 10) / 10,
    put_gex: Math.round(-Math.max(0, 18 - Math.abs(k - (spot - 300))/50) * 10) / 10,
    net_gex: Math.round((Math.max(0, 18 - Math.abs(k - (spot + 300))/50) - Math.max(0, 18 - Math.abs(k - (spot - 300))/50)) * 10) / 10
  }));

  return {
    date: "2026-07-31",
    last_updated_time: "2026-07-31 13:45",
    spot_price: spot,
    two_price: 347.85,
    txf_price: 43305,
    zero_gamma_level: 42970,
    call_wall_strike: 43400,
    put_wall_strike: 42800,
    max_pain_strike: 43100,
    pc_ratio: 108.5,
    total_gex: total_gex,
    weekly_gex: total_gex,
    friday_gex: total_gex,
    monthly_gex: total_gex,
    retail_mini_ratio: 4.5,
    retail_micro_ratio: 6.9,
    institutional_5day_history: [
      { date: "7/25", top5_net: -1250, top10_net: -3420, top5_spec_net: -980, top10_spec_net: -2100, foreign_fut_net: -18500, trust_fut_net: 2100, dealer_fut_net: -450, foreign_stock_net: -125.4, trust_stock_net: 42.1, dealer_stock_net: -18.6, foreign_opt_call_net: 0.45, foreign_opt_put_net: -1.82, trust_opt_call_net: -2.40, trust_opt_put_net: 0.002, dealer_opt_call_net: 1.25, dealer_opt_put_net: 0.85, pc_ratio: 102.4 },
      { date: "7/28", top5_net: -850, top10_net: -1200, top5_spec_net: -420, top10_spec_net: -890, foreign_fut_net: -16200, trust_fut_net: 2450, dealer_fut_net: -120, foreign_stock_net: -88.2, trust_stock_net: 38.5, dealer_stock_net: -12.4, foreign_opt_call_net: 0.62, foreign_opt_put_net: -1.45, trust_opt_call_net: -2.65, trust_opt_put_net: 0.002, dealer_opt_call_net: 1.40, dealer_opt_put_net: 0.92, pc_ratio: 104.1 },
      { date: "7/29", top5_net: 420, top10_net: 1150, top5_spec_net: 650, top10_spec_net: 1420, foreign_fut_net: -15100, trust_fut_net: 3100, dealer_fut_net: 380, foreign_stock_net: -45.6, trust_stock_net: 51.2, dealer_stock_net: -8.5, foreign_opt_call_net: 0.88, foreign_opt_put_net: -1.10, trust_opt_call_net: -2.85, trust_opt_put_net: 0.003, dealer_opt_call_net: 1.85, dealer_opt_put_net: 1.15, pc_ratio: 105.8 },
      { date: "7/30", top5_net: 3850, top10_net: 5920, top5_spec_net: 3210, top10_spec_net: 4850, foreign_fut_net: -12400, trust_fut_net: 3650, dealer_fut_net: 850, foreign_stock_net: 32.5, trust_stock_net: 48.0, dealer_stock_net: 14.2, foreign_opt_call_net: 1.45, foreign_opt_put_net: -0.65, trust_opt_call_net: -2.98, trust_opt_put_net: 0.003, dealer_opt_call_net: 2.30, dealer_opt_put_net: 1.42, pc_ratio: 107.2 },
      { date: "7/31", top5_net: 6420, top10_net: 9850, top5_spec_net: 5890, top10_spec_net: 8410, foreign_fut_net: -14200, trust_fut_net: 4200, dealer_fut_net: 1100, foreign_stock_net: 185.4, trust_stock_net: 62.8, dealer_stock_net: -24.5, foreign_opt_call_net: 0.60, foreign_opt_put_net: -0.28, trust_opt_call_net: -3.08, trust_opt_put_net: 0.003, dealer_opt_call_net: 1.83, dealer_opt_put_net: 1.42, pc_ratio: 108.5 }
    ],
    executive_digest: {
      date: "2026-07-31",
      futures_summary: "前五大與前十大交易人多單加碼（+6,420口 / +9,850口），特定法人整體期貨結構偏多佈局。",
      cash_summary: "現貨買賣超呈現「外資大買超 +185.4億」與「投信連續買超 +62.8億」，自營商微幅調節 -24.5億。",
      options_structure: "期交所官方數據顯示：投信持倉 SC 賣出買權 -3.08億 與 BP 買進賣權 +0.003億（總部位 SC+BP 防守避險）；外資與自營商雙賣收取時間價值偏高檔看撐。",
      settlement_outlook: "🎯 綜合日盤官方結算籌碼與 GEX 避險牆，當前支撐位於 42,800 Put Wall，上檔壓力 43,400 Call Wall，預計結算偏向【高檔震盪看撐】。"
    },
    stock_futures: [
      { code: "2330", name: "台積電期", category: "個股期貨", has_night: true, liquidity: "極高", spot_price: 2205.0, change_pct: 0.23, volume: 38450, foreign_net: 4200, dealer_net: 1100, trend: "Bull" },
      { code: "2454", name: "聯發科期", category: "個股期貨", has_night: true, liquidity: "極高", spot_price: 3235.0, change_pct: 2.70, volume: 12800, foreign_net: 850, dealer_net: -200, trend: "Bull" },
      { code: "2317", name: "鴻海期", category: "個股期貨", has_night: true, liquidity: "極高", spot_price: 229.5, change_pct: -3.16, volume: 24100, foreign_net: -3600, dealer_net: 1500, trend: "Bear" }
    ]
  };
}

function renderDashboard() {
  if (!gexData) return;

  const spot = gexData.spot_price || 43119.75;
  const txf = gexData.txf_price || 43305;
  const lastTime = gexData.last_updated_time || (gexData.date + ' 13:45');

  document.getElementById('stat-spot').innerText = spot.toLocaleString();
  document.getElementById('stat-two-price').innerText = (gexData.two_price || 347.85).toLocaleString();
  document.getElementById('stat-txf-price').innerText = txf.toLocaleString();

  const sessionBadge = gexData.session_name 
    ? `<span style="margin-left: 8px; padding: 2px 8px; border-radius: 12px; background: rgba(0, 210, 255, 0.15); color: #00d2ff; font-size: 0.85rem; border: 1px solid rgba(0, 210, 255, 0.3);">${gexData.session_name}</span>` 
    : '';

  document.getElementById('stat-last-update').innerHTML = `📅 最後更新: <strong>${lastTime}</strong> ${sessionBadge}`;

  document.getElementById('stat-zero-gamma').innerText = gexData.zero_gamma_level.toLocaleString();
  document.getElementById('stat-call-wall').innerText = gexData.call_wall_strike.toLocaleString();
  document.getElementById('stat-put-wall').innerText = gexData.put_wall_strike.toLocaleString();
  document.getElementById('stat-max-pain').innerText = gexData.max_pain_strike.toLocaleString();
  document.getElementById('data-date').innerText = gexData.date;

  const zg = gexData.zero_gamma_level;
  const statusEl = document.getElementById('stat-gamma-status');
  if (spot >= zg) {
    statusEl.innerHTML = '🔴 正 Gamma 多頭平穩區 (台灣紅漲)';
    statusEl.style.color = 'var(--call-color)';
  } else {
    statusEl.innerHTML = '🟢 負 Gamma 避險引爆區 (台灣綠跌)';
    statusEl.style.color = 'var(--put-color)';
  }

  renderGEXChart();

  const microRatio = gexData.retail_micro_ratio || 6.9;
  const miniRatio = gexData.retail_mini_ratio || 4.5;
  document.getElementById('micro-ratio-val').innerText = `${microRatio}% (${microRatio > 0 ? '散戶做多 ➔ 偏拉回' : '散戶做空 ➔ 偏嘎空'})`;
  document.getElementById('mini-ratio-val').innerText = `${miniRatio}% (${miniRatio > 0 ? '散戶做多' : '散戶做空'})`;

  const fillWidth = Math.max(5, Math.min(95, 50 + (microRatio * 1.5)));
  document.getElementById('sentiment-fill').style.width = `${fillWidth}%`;

  populateInstitutionalMatrix();
  populateStockFutures();
}

function renderGEXChart() {
  let gexList = gexData.total_gex;
  let title = '📊 全市場 TXO GEX 履約價分布圖 (億 TWD)';

  if (currentTab === 'weekly-gex') {
    gexList = gexData.weekly_gex || gexData.total_gex;
    title = '⚡ 近到期週三結算選 (W1/W2/W4/W5) GEX 履約價分布圖';
  } else if (currentTab === 'friday-gex') {
    gexList = gexData.friday_gex || gexData.total_gex;
    title = '🇺🇸 週五結算選 (W1F/W2F/W4F/W5F) GEX 履約價分布圖';
  } else if (currentTab === 'monthly-gex') {
    gexList = gexData.monthly_gex || gexData.total_gex;
    title = '🏛️ 當月月選 GEX 履約價分布圖';
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

  if (digestEl) {
    digestEl.innerHTML = `
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
