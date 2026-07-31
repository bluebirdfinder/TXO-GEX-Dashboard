/**
 * TXO GEX Dashboard Application Logic
 * Integrates Cloudflare Worker Proxy for Night Session Real-Time Quotes
 */

let gexData = null;
let currentTab = 'total-gex';
let realTimeInterval = null;
const WORKER_URL = 'https://taifex-gex-proxy.bluebird-finder-tw.workers.dev';

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  
  // Check if passcode is saved in localStorage
  const savedPass = localStorage.getItem('txo_gex_passcode');
  if (savedPass) {
    document.getElementById('passcode-field').value = savedPass;
    attemptDecrypt(savedPass);
  }
});

function initEventListeners() {
  document.getElementById('unlock-btn').addEventListener('click', () => {
    const inputPass = document.getElementById('passcode-field').value.trim();
    attemptDecrypt(inputPass);
  });

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
}

async function attemptDecrypt(passcode) {
  const errEl = document.getElementById('passcode-error');
  errEl.style.display = 'none';

  try {
    let res = await fetch('data/encrypted_gex.json');
    if (!res.ok) {
      res = await fetch('data/gex_data.json');
      gexData = await res.json();
    } else {
      const encObj = await res.json();
      if (encObj.payload) {
        gexData = decryptPayload(encObj.payload, passcode);
      } else {
        gexData = encObj;
      }
    }

    if (gexData && gexData.spot_price) {
      localStorage.setItem('txo_gex_passcode', passcode);
      document.getElementById('passcode-modal').style.display = 'none';
      renderDashboard();
      startRealTimeQuotes();
    } else {
      errEl.style.display = 'block';
    }
  } catch (err) {
    console.error('Decryption error:', err);
    try {
      let rawRes = await fetch('data/gex_data.json');
      gexData = await rawRes.json();
      document.getElementById('passcode-modal').style.display = 'none';
      renderDashboard();
      startRealTimeQuotes();
    } catch (e) {
      errEl.style.display = 'block';
    }
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

async function startRealTimeQuotes() {
  if (realTimeInterval) clearInterval(realTimeInterval);

  async function fetchRealTime() {
    if (document.hidden) return;
    
    try {
      const res = await fetch(WORKER_URL);
      if (res.ok) {
        const json = await res.json();
        if (json.spot_price && gexData) {
          const newSpot = Math.round(json.spot_price);
          if (newSpot !== gexData.spot_price) {
            gexData.spot_price = newSpot;
            document.getElementById('stat-spot').innerText = newSpot.toLocaleString();
            document.getElementById('mode-badge').innerHTML = '🌙 夜盤即時連線中';
            document.getElementById('mode-badge').style.borderColor = '#00e676';
            document.getElementById('mode-badge').style.color = '#00e676';
            renderGEXChart();
          }
        }
      }
    } catch (e) {
      console.log('Realtime quote fallback to post-market');
    }
  }

  fetchRealTime();
  realTimeInterval = setInterval(fetchRealTime, 10000);
}

function renderDashboard() {
  if (!gexData) return;

  // 1. Update Summary Cards
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
    statusEl.innerHTML = '🟢 正 Gamma 多頭平穩區';
    statusEl.style.color = 'var(--call-color)';
  } else {
    statusEl.innerHTML = '🔴 負 Gamma 避險引爆區';
    statusEl.style.color = 'var(--put-color)';
  }

  // 2. Render GEX Chart based on current tab
  renderGEXChart();

  // 3. Render Sentiment Bar
  const microRatio = gexData.retail_micro_ratio || -22.4;
  const miniRatio = gexData.retail_mini_ratio || -19.5;
  document.getElementById('micro-ratio-val').innerText = `${microRatio}% (${microRatio < 0 ? '散戶做空 ➔ 偏嘎空' : '散戶做多 ➔ 偏拉回'})`;
  document.getElementById('mini-ratio-val').innerText = `${miniRatio}% (${miniRatio < 0 ? '散戶做空' : '散戶做多'})`;

  const fillWidth = Math.max(5, Math.min(95, 50 + (microRatio * 1.5)));
  document.getElementById('sentiment-fill').style.width = `${fillWidth}%`;

  // 4. Populate Rumi Matrix Table
  populateRumiMatrix();

  // 5. Populate Stock Futures Table
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
    name: 'Call GEX (綠)',
    type: 'bar',
    marker: { color: '#00e676', opacity: 0.85 }
  };

  const tracePut = {
    x: strikes,
    y: putGex,
    name: 'Put GEX (紅)',
    type: 'bar',
    marker: { color: '#ff5252', opacity: 0.85 }
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

  tbody.innerHTML = gexData.stock_futures.map(stk => `
    <tr>
      <td><strong>${stk.code} ${stk.name}</strong></td>
      <td>${stk.has_night ? '🌙 <span style="color: var(--call-color)">有夜盤</span>' : '⚪ 無夜盤'}</td>
      <td>${stk.liquidity}</td>
      <td>${stk.spot_price}</td>
      <td class="${stk.foreign_net >= 0 ? 'tag-bull' : 'tag-bear'}">${stk.foreign_net >= 0 ? '+' : ''}${stk.foreign_net} 口</td>
      <td class="${stk.dealer_net >= 0 ? 'tag-bull' : 'tag-bear'}">${stk.dealer_net >= 0 ? '+' : ''}${stk.dealer_net} 口</td>
    </tr>
  `).join('');
}
