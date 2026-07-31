/**
 * TXO GEX Dashboard Application Logic v11.0
 * 3-Second High-Speed Live Spot Quote & Dynamic GEX Re-render Engine
 */

let gexData = null;
let currentTab = 'total-gex';
let realTimeInterval = null;
let currentSortKey = 'volume';
let currentSortOrder = 'desc';

const VALID_PASSCODE = 'GEX2026';
const WORKER_URL = 'https://taifex-gex-proxy.bluebird-finder-tw.workers.dev';

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

  // Tab switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
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
      startRealTimeQuotes();
      return;
    }
  } catch (err) {
    console.error('Decryption error:', err);
    gexData = getFallbackData();
    if (gexData) {
      localStorage.setItem('txo_gex_passcode', cleanPass);
      document.getElementById('passcode-modal').style.display = 'none';
      renderDashboard();
      startRealTimeQuotes();
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
  const spot = 43120;
  const strikes = [];
  for (let i = -15; i <= 15; i++) strikes.push(spot + i * 50);

  const total_gex = strikes.map(k => ({
    strike: k,
    call_gex: Math.round(Math.max(0, 18 - Math.abs(k - (spot + 300))/50) * 10) / 10,
    put_gex: Math.round(-Math.max(0, 18 - Math.abs(k - (spot - 300))/50) * 10) / 10,
    net_gex: Math.round((Math.max(0, 18 - Math.abs(k - (spot + 300))/50) - Math.max(0, 18 - Math.abs(k - (spot - 300))/50)) * 10) / 10
  }));

  return {
    date: new Date().toISOString().split('T')[0],
    spot_price: spot,
    zero_gamma_level: spot - 150,
    call_wall_strike: spot + 300,
    put_wall_strike: spot - 300,
    max_pain_strike: spot,
    pc_ratio: 108.5,
    total_gex: total_gex,
    weekly_gex: total_gex,
    monthly_gex: total_gex,
    retail_mini_ratio: -19.5,
    retail_micro_ratio: -22.4,
    rumi_matrix: {
      top5_traders: "多單加碼 🔴",
      top10_traders: "空翻多 🔴 (偏多)",
      foreign_futures: "多單加碼 / 空單減碼 🔴",
      trust_futures: "多單加碼 🔴",
      foreign_options: "總部位 BP > BC (差額收窄)",
      dealer_options: "Call/Put 相當 (偏向看撐)",
      settlement_prediction: `偏往上結算 🎯 (目標天花板: ${spot + 300})`
    },
    stock_futures: [
      { code: "2330", name: "台積電期", category: "個股期貨", has_night: true, liquidity: "極高", spot_price: 2425.0, change_pct: 2.15, volume: 38450, foreign_net: 4200, dealer_net: 1100, trend: "Bull" },
      { code: "2454", name: "聯發科期", category: "個股期貨", has_night: true, liquidity: "極高", spot_price: 3555.0, change_pct: 1.42, volume: 12800, foreign_net: 850, dealer_net: -200, trend: "Bull" },
      { code: "2317", name: "鴻海期", category: "個股期貨", has_night: true, liquidity: "極高", spot_price: 215.0, change_pct: -0.46, volume: 24100, foreign_net: 6100, dealer_net: 1500, trend: "Bear" },
      { code: "2382", name: "廣達期", category: "個股期貨", has_night: true, liquidity: "高", spot_price: 275.0, change_pct: 0.92, volume: 16800, foreign_net: 980, dealer_net: 320, trend: "Bull" },
      { code: "3231", name: "緯創期", category: "個股期貨", has_night: true, liquidity: "高", spot_price: 108.0, change_pct: 1.12, volume: 21500, foreign_net: 1500, dealer_net: -100, trend: "Bull" },
      { code: "3037", name: "欣興期", category: "個股期貨", has_night: true, liquidity: "高", spot_price: 787.0, change_pct: -1.25, volume: 15200, foreign_net: -1400, dealer_net: 320, trend: "Bear" },
      { code: "2383", name: "台光電期", category: "個股期貨", has_night: true, liquidity: "高", spot_price: 4745.0, change_pct: 3.82, volume: 9450, foreign_net: 1820, dealer_net: 410, trend: "Bull" },
      { code: "6669", name: "緯穎期", category: "個股期貨", has_night: true, liquidity: "高", spot_price: 5390.0, change_pct: 2.65, volume: 4100, foreign_net: 650, dealer_net: 180, trend: "Bull" },
      { code: "3017", name: "奇鋐期", category: "個股期貨", has_night: true, liquidity: "高", spot_price: 2320.0, change_pct: 1.75, volume: 11400, foreign_net: 1250, dealer_net: 240, trend: "Bull" },
      { code: "2303", name: "聯電期", category: "個股期貨", has_night: true, liquidity: "極高", spot_price: 121.0, change_pct: -0.82, volume: 45100, foreign_net: -2800, dealer_net: 640, trend: "Bear" },
      { code: "2330F", name: "小型台積電期", category: "小型個股期貨", has_night: true, liquidity: "極高", spot_price: 2425.0, change_pct: 2.15, volume: 19200, foreign_net: 1200, dealer_net: 350, trend: "Bull" },
      { code: "0050", name: "元大台灣50期", category: "ETF期貨", has_night: true, liquidity: "極高", spot_price: 198.5, change_pct: 1.80, volume: 52100, foreign_net: 12500, dealer_net: 3400, trend: "Bull" },
      { code: "0050F", name: "小型台灣50期", category: "小型ETF期貨", has_night: true, liquidity: "高", spot_price: 198.5, change_pct: 1.80, volume: 14200, foreign_net: 2100, dealer_net: 850, trend: "Bull" }
    ]
  };
}

async function startRealTimeQuotes() {
  if (realTimeInterval) clearInterval(realTimeInterval);

  const badgeEl = document.getElementById('mode-badge');
  if (badgeEl) {
    badgeEl.innerHTML = '🌙 夜盤即時連線中';
    badgeEl.style.borderColor = '#ff5252';
    badgeEl.style.color = '#ff5252';
  }

  async function fetchRealTime() {
    if (document.hidden) return;
    
    try {
      const res = await fetch(WORKER_URL + '?t=' + Date.now());
      if (res.ok) {
        const json = await res.json();
        if (json.spot_price && gexData) {
          const newSpot = Math.round(json.spot_price);
          // If spot price updates, re-render chart dynamically!
          if (Math.abs(newSpot - gexData.spot_price) >= 1) {
            gexData.spot_price = newSpot;
            document.getElementById('stat-spot').innerText = newSpot.toLocaleString();
            renderDashboard();
          }
        }
      }
    } catch (e) {
      console.log('Realtime quote fallback to post-market');
    }
  }

  fetchRealTime();
  // High-speed 3-second live quote polling & dynamic re-rendering!
  realTimeInterval = setInterval(fetchRealTime, 3000);
}

function renderDashboard() {
  if (!gexData) return;

  document.getElementById('stat-spot').innerText = gexData.spot_price.toLocaleString();
  document.getElementById('stat-zero-gamma').innerText = gexData.zero_gamma_level.toLocaleString();
  document.getElementById('stat-call-wall').innerText = gexData.call_wall_strike.toLocaleString();
  document.getElementById('stat-put-wall').innerText = gexData.put_wall_strike.toLocaleString();
  document.getElementById('stat-max-pain').innerText = gexData.max_pain_strike.toLocaleString();
  document.getElementById('stat-pc-ratio').innerText = `P/C Ratio: ${gexData.pc_ratio}%`;
  document.getElementById('data-date').innerText = gexData.date;

  const spot = gexData.spot_price;
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

  const microRatio = gexData.retail_micro_ratio || -22.4;
  const miniRatio = gexData.retail_mini_ratio || -19.5;
  document.getElementById('micro-ratio-val').innerText = `${microRatio}% (${microRatio < 0 ? '散戶死做空 ➔ 偏嘎空' : '散戶死做多 ➔ 偏拉回'})`;
  document.getElementById('mini-ratio-val').innerText = `${miniRatio}% (${miniRatio < 0 ? '散戶死做空' : '散戶死做多'})`;

  const fillWidth = Math.max(5, Math.min(95, 50 + (microRatio * 1.5)));
  document.getElementById('sentiment-fill').style.width = `${fillWidth}%`;

  populateRumiMatrix();
  populateStockFutures();
}

function renderGEXChart() {
  let gexList = gexData.total_gex;
  let title = '📊 全市場 TXO GEX 履約價分布圖 (億 TWD)';

  if (currentTab === 'weekly-gex') {
    gexList = gexData.weekly_gex;
    title = '⚡ 近到期週選 (W1/W2/W4/W5) GEX 履約價分布圖';
  } else if (currentTab === 'monthly-gex') {
    gexList = gexData.monthly_gex;
    title = '🏛️ 當月月選 GEX 履約價分布圖';
  }

  document.getElementById('chart-panel-title').innerText = title;

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
        x0: gexData.spot_price,
        x1: gexData.spot_price,
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
        x: gexData.spot_price,
        y: 1,
        yref: 'paper',
        text: `現價 Spot: ${gexData.spot_price}`,
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

function populateRumiMatrix() {
  const tbody = document.getElementById('matrix-body');
  if (!tbody || !gexData.rumi_matrix) return;

  const m = gexData.rumi_matrix;
  tbody.innerHTML = `
    <tr>
      <td><strong>前五大交易人期貨</strong></td>
      <td class="tag-bull">${m.top5_traders}</td>
      <td>前五大主力交易人部位變動方向</td>
    </tr>
    <tr>
      <td><strong>前十大交易人期貨</strong></td>
      <td class="tag-bull">${m.top10_traders}</td>
      <td>前十大交易人整體多空翻轉訊號</td>
    </tr>
    <tr>
      <td><strong>外資期貨部位</strong></td>
      <td class="tag-bull">${m.foreign_futures}</td>
      <td>外資期貨今日淨增減口數趨勢</td>
    </tr>
    <tr>
      <td><strong>投信期貨部位</strong></td>
      <td class="tag-neutral">${m.trust_futures}</td>
      <td>投信避險與多單調配狀況</td>
    </tr>
    <tr>
      <td><strong>外資選擇權組合</strong></td>
      <td class="tag-neutral">${m.foreign_options}</td>
      <td>外資 Buy Call vs Buy Put 口數與金額差</td>
    </tr>
    <tr>
      <td><strong>自營商 (造市商) 選擇權</strong></td>
      <td class="tag-bull">${m.dealer_options}</td>
      <td>自營商主要賣壓與支撐牆建立方向</td>
    </tr>
    <tr style="background: rgba(0, 210, 255, 0.08);">
      <td><strong>🎯 結算 OP 方向智慧預估</strong></td>
      <td style="color: var(--gold-accent); font-weight: 700;">${m.settlement_prediction}</td>
      <td>綜合 GEX 磁吸牆與法人選擇權籌碼推論</td>
    </tr>
  `;
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
      ? '<span style="background: rgba(255,82,82,0.15); color: var(--call-color); padding: 3px 8px; border-radius: 6px; font-weight: bold;">▲ Bull (🔴 多)</span>' 
      : '<span style="background: rgba(0,230,118,0.15); color: var(--put-color); padding: 3px 8px; border-radius: 6px; font-weight: bold;">▼ Bear (🟢 空)</span>';

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
