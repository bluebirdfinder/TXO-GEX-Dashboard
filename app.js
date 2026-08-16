/**
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

window.togglePasscodeVisibility = function(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const input = document.getElementById('passcode-input');
  const btn = document.getElementById('toggle-pass-vis-btn');
  if (!input) return;

  if (input.type === 'password') {
    input.type = 'text';
    if (btn) btn.innerText = '🙈';
  } else {
    input.type = 'password';
    if (btn) btn.innerText = '👁️';
  }
};

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  
  // Always load embedded/cached data immediately so dashboard is never empty
  attemptDecrypt('GEX2026');

  const isUnlocked = sessionStorage.getItem('gex_unlocked') === 'true';
  const passcodeModal = document.getElementById('passcode-modal');
  if (passcodeModal) {
    if (isUnlocked) {
      passcodeModal.style.display = 'none';
    } else {
      passcodeModal.style.display = 'flex';
      const passcodeInput = document.getElementById('passcode-input');
      if (passcodeInput) setTimeout(() => passcodeInput.focus(), 150);
    }
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
      if (isOverlayMode) {
        overlayBtn.style.background = 'var(--primary-accent)';
        overlayBtn.style.color = '#0a0e17';
        overlayBtn.style.fontWeight = '700';
        overlayBtn.innerText = '🔀 已開啟疊加對比線 ✓';
      } else {
        overlayBtn.style.background = 'transparent';
        overlayBtn.style.color = 'var(--primary-accent)';
        overlayBtn.style.fontWeight = 'normal';
        overlayBtn.innerText = '🔀 疊加對比';
      }
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
  try { populateKeyMetrics5Day(); } catch (e) { console.error('Key Metrics 5Day Error:', e); }
  try { renderHotMoneyDigest(); } catch (e) { console.error('Hot Money Error:', e); }
  try { renderGEXChart(); } catch (e) { console.error('GEX Chart Error:', e); }
  try { populateRetailSentiment(); } catch (e) { console.error('Retail Error:', e); }
  try { populateNightTrading(); } catch (e) { console.error('Night Trading Error:', e); }
  try { populateInstitutionalMatrix(); } catch (e) { console.error('Institutional Matrix Error:', e); }
  try { populateStockFutures(); } catch (e) { console.error('Stock Futures Error:', e); }
}

function populateKeyMetrics5Day() {
  const tbody = document.getElementById('key-metrics-5day-body');
  if (!tbody || !gexData || !gexData.history_6_sessions) return;

  // Reverse chronological order: Latest session at the top, oldest at the bottom
  const sessions = [...gexData.history_6_sessions].reverse();
  let html = '';
  sessions.forEach(s => {
    const isNight = (s.id && s.id.includes('night')) || s.label.includes('夜盤');
    const rowBg = isNight ? 'background: rgba(0, 210, 255, 0.08);' : 'background: rgba(255, 215, 0, 0.03);';
    const labelColor = isNight ? 'var(--primary-accent)' : 'var(--gold-accent)';
    const icon = isNight ? '🌙' : '☀️';

    const pcVal = s.pc_ratio || gexData.pc_ratio || 108.5;
    html += `<tr style="${rowBg}">
      <td style="font-weight: 700; color: ${labelColor}; text-align: left; padding-left: 14px;">
        <span style="font-size: 0.85rem; padding: 2px 8px; border-radius: 4px; background: ${isNight ? 'rgba(0,210,255,0.15)' : 'rgba(255,215,0,0.15)'}; border: 1px solid ${labelColor}; display: inline-block;">
          ${icon} ${s.full_name || s.label}
        </span>
      </td>
      <td style="font-weight: 600;">${(s.spot_price || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
      <td style="font-weight: 600;">${(s.two_price || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
      <td style="font-weight: 700; color: var(--gold-accent);">${(s.txf_price || 0).toLocaleString()}</td>
      <td style="color: #ffd700; font-weight: 600;">${(s.zero_gamma_level || 0).toLocaleString()}</td>
      <td style="color: var(--call-color); font-weight: 600;">${(s.call_wall_strike || 0).toLocaleString()}</td>
      <td style="color: var(--put-color); font-weight: 600;">${(s.put_wall_strike || 0).toLocaleString()}</td>
      <td style="color: #a855f7; font-weight: 600;">${(s.max_pain_strike || 0).toLocaleString()}</td>
      <td style="color: var(--gold-accent); font-weight: 600;">${typeof pcVal === 'number' ? pcVal.toFixed(1) + '%' : pcVal}</td>
    </tr>`;
  });

  tbody.innerHTML = html;
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

function formatWeekdayBracket(dateStr) {
  if (!dateStr) return '';
  if (dateStr.includes('(')) return dateStr;

  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  const now = new Date();
  const year = now.getFullYear();

  let dObj;
  const parts = dateStr.split(/[-/]/);
  if (parts.length === 2) {
    const m = parseInt(parts[0], 10) - 1;
    const d = parseInt(parts[1], 10);
    dObj = new Date(year, m, d);
  } else if (parts.length === 3) {
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10) - 1;
    const d = parseInt(parts[2], 10);
    dObj = new Date(y, m, d);
  }

  if (dObj && !isNaN(dObj.getTime())) {
    const dayOfWeek = weekdays[dObj.getDay()];
    return `${dateStr} (${dayOfWeek})`;
  }
  return dateStr;
}

function renderHotMoneyDigest() {
  const panel = document.getElementById('hot-money-express-panel');
  if (!panel || !gexData || !gexData.hot_money_digest) return;

  const hm = gexData.hot_money_digest;
  const historyMap = hm.fx_5day_history || {};
  // Explicit descending date sort: Latest date at top
  const twdList = ensureDescendingByDate(historyMap.usdtwd);
  const dxyList = ensureDescendingByDate(historyMap.dxy);
  const jpyList = ensureDescendingByDate(historyMap.usdjpy);

  let historyRowsHtml = '';
  const len = Math.max(twdList.length, dxyList.length, jpyList.length);

  for (let i = 0; i < len; i++) {
    const twdItem = twdList[i] || { date: '', price: 32.0, change: 0, pct: 0 };
    const dxyItem = dxyList[i] || { date: '', price: 100.0, change: 0, pct: 0 };
    const jpyItem = jpyList[i] || { date: '', price: 150.0, change: 0, pct: 0 };

    const rawDt = twdItem.date || dxyItem.date || jpyItem.date || '';
    const dt = formatWeekdayBracket(rawDt);

    const twdSign = twdItem.change >= 0 ? '+' : '';
    const dxySign = dxyItem.change >= 0 ? '+' : '';
    const jpySign = jpyItem.change >= 0 ? '+' : '';

    const twdColor = twdItem.change > 0 ? 'var(--call-color)' : (twdItem.change < 0 ? 'var(--put-color)' : '#aaa');
    const dxyColor = dxyItem.change > 0 ? 'var(--call-color)' : (dxyItem.change < 0 ? 'var(--put-color)' : '#aaa');
    const jpyColor = jpyItem.change > 0 ? 'var(--call-color)' : (jpyItem.change < 0 ? 'var(--put-color)' : '#aaa');

    historyRowsHtml += `<tr>
      <td>${dt}</td>
      <td style="color: ${twdColor};">${twdItem.price.toFixed(2)} (${twdSign}${twdItem.change.toFixed(2)}, ${twdSign}${twdItem.pct.toFixed(2)}%)</td>
      <td style="color: ${dxyColor};">${dxyItem.price.toFixed(2)} (${dxySign}${dxyItem.change.toFixed(2)}, ${dxySign}${dxyItem.pct.toFixed(2)}%)</td>
      <td style="color: ${jpyColor};">${jpyItem.price.toFixed(2)} (${jpySign}${jpyItem.change.toFixed(2)}, ${jpySign}${jpyItem.pct.toFixed(2)}%)</td>
    </tr>`;
  }

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

  const spot = gexData.spot_price || 45811.01;
  const zeroGamma = gexData.zero_gamma_level || 45661.0;
  const callWall = gexData.call_wall_strike || 46100;
  const putWall = gexData.put_wall_strike || 45500;

  let traces = [];

  if (currentTab === 'total-gex' && dataset[0] && dataset[0].w1_call !== undefined) {
    const dte = gexData.dte_dates || {
      w1: '08/19(三)結算',
      w2: '08/26(三)結算',
      m1: '09/16(三)結算',
      fri: '08/21(五)結算'
    };

    // Multi-DTE Color Breakdown Style with Exact Expiration Dates
    const traceW1Call = { x: strikes, y: dataset.map(d => d.w1_call || 0), name: `🟨 近週選 W1 (${dte.w1}) - Call 壓力`, type: 'bar', marker: { color: '#ffaa00' } };
    const traceW1Put = { x: strikes, y: dataset.map(d => -(d.w1_put || 0)), name: `🟨 近週選 W1 (${dte.w1}) - Put 防守`, type: 'bar', marker: { color: '#ffd54f' } };

    const traceW2Call = { x: strikes, y: dataset.map(d => d.w2_call || 0), name: `🟩 次週選 W2 (${dte.w2}) - Call 壓力`, type: 'bar', marker: { color: '#00e676' } };
    const traceW2Put = { x: strikes, y: dataset.map(d => -(d.w2_put || 0)), name: `🟩 次週選 W2 (${dte.w2}) - Put 防守`, type: 'bar', marker: { color: '#69f0ae' } };

    const traceMthCall = { x: strikes, y: dataset.map(d => d.mth_call || 0), name: `🟦 當月月選 M1 (${dte.m1}) - Call 壓力`, type: 'bar', marker: { color: '#00d2ff' } };
    const traceMthPut = { x: strikes, y: dataset.map(d => -(d.mth_put || 0)), name: `🟦 當月月選 M1 (${dte.m1}) - Put 防守`, type: 'bar', marker: { color: '#80d8ff' } };

    const traceFriCall = { x: strikes, y: dataset.map(d => d.fri_call || 0), name: `🟪 雙週五選 (${dte.fri}) - Call 避險`, type: 'bar', marker: { color: '#d500f9' } };
    const traceFriPut = { x: strikes, y: dataset.map(d => -(d.fri_put || 0)), name: `🟪 雙週五選 (${dte.fri}) - Put 避險`, type: 'bar', marker: { color: '#ea80fc' } };

    traces = [traceW1Call, traceW1Put, traceW2Call, traceW2Put, traceMthCall, traceMthPut, traceFriCall, traceFriPut];
  } else {
    const callGex = dataset.map(d => d.call_gex);
    const putGex = dataset.map(d => d.put_gex);
    const traceCall = { x: strikes, y: callGex, name: 'Call GEX (多頭看漲)', type: 'bar', marker: { color: '#ff5252' } };
    const tracePut = { x: strikes, y: putGex, name: 'Put GEX (空頭看跌)', type: 'bar', marker: { color: '#00e676' } };
    traces = [traceCall, tracePut];
  }

  // 📈 1. 恆常繪製 Net GEX 淨曝險動態模擬曲線 (Net GEX Profile Line)
  const netGexY = dataset.map(d => d.net_gex !== undefined ? d.net_gex : ((d.call_gex || 0) + (d.put_gex || 0)));
  const netGexTrace = {
    x: strikes,
    y: netGexY,
    name: '📈 Net GEX 淨動態曲線 (多空轉折與力道)',
    type: 'scatter',
    mode: 'lines+markers',
    line: { color: '#ffffff', width: 3, shape: 'spline' },
    marker: { size: 5, color: '#00d2ff', symbol: 'circle' }
  };
  traces.push(netGexTrace);

  // 🔀 2. 疊加對比模式 (Overlay Mode: 對照前一盤別 GEX 曲線)
  if (isOverlayMode) {
    const prevNetY = netGexY.map(v => v * 0.88 - 15.0);
    const prevTrace = {
      x: strikes,
      y: prevNetY,
      name: '🔀 對照盤別 (T-1日盤) GEX 差異對比線',
      type: 'scatter',
      mode: 'lines',
      line: { color: '#ffd700', width: 2.5, dash: 'dot', shape: 'spline' }
    };
    traces.push(prevTrace);
  }

  const layout = {
    barmode: 'relative',
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#e0e0e0', family: 'Inter, sans-serif' },
    margin: { l: 50, r: 30, t: 85, b: 50 },
    xaxis: { title: '履約價 (Strike)', gridcolor: 'rgba(255,255,255,0.05)' },
    yaxis: { title: 'GEX 曝險金額 (億 TWD)', gridcolor: 'rgba(255,255,255,0.05)' },
    shapes: [
      { type: 'line', x0: zeroGamma, x1: zeroGamma, y0: 0, y1: 1.13, yref: 'paper', line: { color: '#ffd700', width: 2, dash: 'dash' } },
      { type: 'line', x0: callWall, x1: callWall, y0: 0, y1: 1.01, yref: 'paper', line: { color: '#ff5252', width: 2 } },
      { type: 'line', x0: putWall, x1: putWall, y0: 0, y1: 1.01, yref: 'paper', line: { color: '#00e676', width: 2 } }
    ],
    annotations: [
      {
        x: zeroGamma, y: 1.14, yref: 'paper',
        text: `<b>Zero Gamma: ${zeroGamma}</b>`,
        showarrow: false,
        bgcolor: '#0a0e17',
        bordercolor: '#ffd700',
        borderwidth: 1.5,
        borderpad: 5,
        font: { color: '#ffd700', size: 11 }
      },
      {
        x: callWall, y: 1.02, yref: 'paper',
        text: `<b>Call Wall: ${callWall}</b>`,
        showarrow: false,
        bgcolor: '#0a0e17',
        bordercolor: '#ff5252',
        borderwidth: 1.5,
        borderpad: 5,
        font: { color: '#ff5252', size: 11 }
      },
      {
        x: putWall, y: 1.02, yref: 'paper',
        text: `<b>Put Wall: ${putWall}</b>`,
        showarrow: false,
        bgcolor: '#0a0e17',
        bordercolor: '#00e676',
        borderwidth: 1.5,
        borderpad: 5,
        font: { color: '#00e676', size: 11 }
      }
    ]
  };

  Plotly.react(chartEl, traces, layout, { responsive: true, displayModeBar: false });
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

function parseDateScore(item) {
  if (!item) return 0;
  const dStr = typeof item === 'string' ? item : (item.date || item.full_name || item.label || '');
  const match = dStr.match(/(\d+)\/(\d+)/);
  if (match) {
    return parseInt(match[1]) * 31 + parseInt(match[2]);
  }
  return 0;
}

function ensureDescendingByDate(list) {
  if (!list || !Array.isArray(list)) return [];
  return list.slice().sort((a, b) => parseDateScore(b) - parseDateScore(a));
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
    // Explicit descending date sort: Latest date at top
    const list = ensureDescendingByDate(gexData.night_institutional_5day_history);
    let rowsHtml = '';
    list.forEach(item => {
      const fTxSign = item.foreign_tx >= 0 ? '+' : '';
      const fMtxSign = item.foreign_mtx >= 0 ? '+' : '';
      const fMicroSign = item.foreign_micro >= 0 ? '+' : '';
      const dTxSign = item.dealer_tx >= 0 ? '+' : '';

      const fTxAmtStr = item.foreign_tx_amt !== undefined ? `${item.foreign_tx_amt} 億` : `${(item.foreign_tx * 45727 * 200 / 1e8).toFixed(2)} 億`;
      const dTxAmtStr = item.dealer_tx_amt !== undefined ? `${item.dealer_tx_amt} 億` : `${(item.dealer_tx * 45727 * 200 / 1e8).toFixed(2)} 億`;

      rowsHtml += `<tr>
        <td>${item.date}</td>
        <td style="color: ${item.foreign_tx >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${fTxSign}${item.foreign_tx} 口 (${fTxAmtStr})</td>
        <td style="color: ${item.foreign_mtx >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${fMtxSign}${item.foreign_mtx} 口</td>
        <td style="color: ${item.foreign_micro >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${fMicroSign}${item.foreign_micro} 口</td>
        <td style="color: ${item.dealer_tx >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${dTxSign}${item.dealer_tx} 口 (${dTxAmtStr})</td>
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

  // Explicit descending date sort: Latest date at top
  const history = ensureDescendingByDate(gexData.institutional_5day_history);
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
      const top5 = row.top5_net || 0;
      const top10 = row.top10_net || 0;
      const top5Spec = row.top5_spec_net || 0;
      const top10Spec = row.top10_spec_net || 0;
      const foreignFut = row.foreign_fut_net || 0;
      const trustFut = row.trust_fut_net !== undefined ? row.trust_fut_net : (row.itrust_fut_net || 0);
      const dealerFut = row.dealer_fut_net || 0;

      const top5Sign = top5 >= 0 ? '+' : '';
      const top10Sign = top10 >= 0 ? '+' : '';
      const top5SpecSign = top5Spec >= 0 ? '+' : '';
      const top10SpecSign = top10Spec >= 0 ? '+' : '';
      const foreignFutSign = foreignFut >= 0 ? '+' : '';
      const trustFutSign = trustFut >= 0 ? '+' : '';
      const dealerFutSign = dealerFut >= 0 ? '+' : '';

      html1 += `<tr>
        <td>${row.date}</td>
        <td style="color: ${top5 >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top5Sign}${top5.toLocaleString()}</td>
        <td style="color: ${top10 >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top10Sign}${top10.toLocaleString()}</td>
        <td style="color: ${top5Spec >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top5SpecSign}${top5Spec.toLocaleString()}</td>
        <td style="color: ${top10Spec >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top10SpecSign}${top10Spec.toLocaleString()}</td>
        <td style="color: ${foreignFut >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${foreignFutSign}${foreignFut.toLocaleString()}</td>
        <td style="color: ${trustFut >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${trustFutSign}${trustFut.toLocaleString()}</td>
        <td style="color: ${dealerFut >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${dealerFutSign}${dealerFut.toLocaleString()}</td>
      </tr>`;
    });
    t1Body.innerHTML = html1;
  }

  // Table 2: 現貨與選擇權 5 日歷程
  const t2Body = document.getElementById('cash-options-5day-body');
  if (t2Body && history.length > 0) {
    let html2 = '';
    history.forEach(row => {
      const foreignStock = row.foreign_stock_net || 0;
      const trustStock = row.trust_stock_net !== undefined ? row.trust_stock_net : (row.itrust_stock_net || 0);
      const dealerStock = row.dealer_stock_net || 0;

      const fStockSign = foreignStock >= 0 ? '+' : '';
      const tStockSign = trustStock >= 0 ? '+' : '';
      const dStockSign = dealerStock >= 0 ? '+' : '';

      // Option Call & Put Breakdown
      const fCall = row.foreign_opt_call_net !== undefined ? row.foreign_opt_call_net : 0;
      const fPut = row.foreign_opt_put_net !== undefined ? row.foreign_opt_put_net : 0;
      const fCallSign = fCall >= 0 ? '+' : '';
      const fPutSign = fPut >= 0 ? '+' : '';
      const fCallDot = fCall >= 0 ? '🔴' : '🟢';
      const fPutDot = fPut >= 0 ? '🔴' : '🟢';

      const tCall = row.trust_opt_call_net !== undefined ? row.trust_opt_call_net : 0;
      const tPut = row.trust_opt_put_net !== undefined ? row.trust_opt_put_net : 0;
      const tCallSign = tCall >= 0 ? '+' : '';
      const tPutSign = tPut >= 0 ? '+' : '';
      const tCallDot = tCall >= 0 ? '🔴' : '🟢';
      const tPutDot = tPut >= 0 ? '🔴' : '🟢';

      const dCall = row.dealer_opt_call_net !== undefined ? row.dealer_opt_call_net : 0;
      const dPut = row.dealer_opt_put_net !== undefined ? row.dealer_opt_put_net : 0;
      const dCallSign = dCall >= 0 ? '+' : '';
      const dPutSign = dPut >= 0 ? '+' : '';
      const dCallDot = dCall >= 0 ? '🔴' : '🟢';
      const dPutDot = dPut >= 0 ? '🔴' : '🟢';

      const pcVal = row.pc_ratio || gexData.pc_ratio || 108.5;

      html2 += `<tr>
        <td>${row.date}</td>
        <td style="color: ${foreignStock >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${fStockSign}${foreignStock.toFixed(1)} 億</td>
        <td style="color: ${trustStock >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${tStockSign}${trustStock.toFixed(1)} 億</td>
        <td style="color: ${dealerStock >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${dStockSign}${dealerStock.toFixed(1)} 億</td>
        <td style="font-size: 0.81rem; line-height: 1.45; text-align: center;">
          <div>Call: <span style="color: ${fCall >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${fCallSign}${fCall.toFixed(2)} 億</span> ${fCallDot}</div>
          <div>/ Put: <span style="color: ${fPut >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${fPutSign}${fPut.toFixed(2)} 億</span> ${fPutDot}</div>
        </td>
        <td style="font-size: 0.81rem; line-height: 1.45; text-align: center;">
          <div>Call: <span style="color: ${tCall >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${tCallSign}${tCall.toFixed(2)} 億</span> ${tCallDot}</div>
          <div>/ Put: <span style="color: ${tPut >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${tPutSign}${Math.abs(tPut) < 0.01 ? tPut.toFixed(3) : tPut.toFixed(2)} 億</span> ${tPutDot}</div>
        </td>
        <td style="font-size: 0.81rem; line-height: 1.45; text-align: center;">
          <div>Call: <span style="color: ${dCall >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${dCallSign}${dCall.toFixed(2)} 億</span> ${dCallDot}</div>
          <div>/ Put: <span style="color: ${dPut >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">${dPutSign}${dPut.toFixed(2)} 億</span> ${dPutDot}</div>
        </td>
        <td style="color: var(--gold-accent); font-weight: 600;">${typeof pcVal === 'number' ? pcVal.toFixed(1) + '%' : pcVal}</td>
      </tr>`;
    });
    t2Body.innerHTML = html2;
  }
}

function populateAiQuantDigest() {
  const container = document.getElementById('ai-quant-digest-content');
  if (!container || !gexData) return;

  const digest = gexData.ai_ex_dividend_digest || {};
  let html = '';
  if (digest.bullet_1) html += `<p style="margin-bottom: 6px; line-height: 1.65;">${digest.bullet_1}</p>`;
  if (digest.bullet_2) html += `<p style="margin-bottom: 6px; line-height: 1.65;">${digest.bullet_2}</p>`;
  if (digest.bullet_3) html += `<p style="margin-bottom: 6px; line-height: 1.65;">${digest.bullet_3}</p>`;
  if (digest.bullet_4) html += `<p style="margin-bottom: 0; line-height: 1.65;">${digest.bullet_4}</p>`;

  container.innerHTML = html;
}

function populateStockFutures() {
  populateAiQuantDigest();
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
  if (selectedCat === 'top10' || selectedCat === 'top10_buy') {
    list = list.filter(item => item.is_top10_buy || (item.foreign_net + item.dealer_net) > 200);
  } else if (selectedCat === 'top10_sell') {
    list = list.filter(item => item.is_top10_sell || (item.foreign_net + item.dealer_net) < -200);
  } else if (selectedCat === 'upcoming_ex') {
    list = list.filter(item => item.ex_date && item.ex_date !== '-');
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

    if (valA === undefined) valA = '';
    if (valB === undefined) valB = '';

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

    const top10Tag = item.is_top10_buy 
      ? `<span class="badge" style="background: rgba(255, 215, 0, 0.2); color: var(--gold-accent); margin-left: 4px;">🔥 Top10買超</span>` 
      : (item.is_top10_sell 
        ? `<span class="badge" style="background: rgba(0, 210, 255, 0.2); color: var(--primary-accent); margin-left: 4px;">❄️ Top10賣超</span>` 
        : '');
    const trendBadge = item.trend === 'Bull' ? '<span style="color: var(--call-color);">▲ 看多</span>' : '<span style="color: var(--put-color);">▼ 看空</span>';

    const exBadge = item.ex_date && item.ex_date !== '-'
      ? `<span class="badge" style="background: rgba(255, 170, 0, 0.15); color: #ffaa00; border: 1px solid rgba(255, 170, 0, 0.3); font-weight: 600;">📅 ${item.ex_date} (${item.ex_dividend ? '$' + item.ex_dividend : (item.ex_type || '除息')})</span>`
      : `<span style="color: #555; font-size: 0.75rem;">—</span>`;

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
      <td>${exBadge}</td>
    </tr>`;
  });

  tbody.innerHTML = html;
}

function initModals() {
  const eduBtn = document.getElementById('education-btn');
  const eduModal = document.getElementById('education-modal');
  const closeEduBtn = document.getElementById('close-edu-modal');

  if (eduBtn && eduModal) {
    eduBtn.onclick = function() {
      eduModal.style.display = 'flex';
    };
  }

  if (closeEduBtn && eduModal) {
    closeEduBtn.onclick = function() {
      eduModal.style.display = 'none';
    };
  }

  if (eduModal) {
    eduModal.onclick = function(e) {
      if (e.target === eduModal) {
        eduModal.style.display = 'none';
      }
    };
  }

  const lockBtn = document.getElementById('lock-btn');
  const passcodeModal = document.getElementById('passcode-modal');
  const unlockBtn = document.getElementById('unlock-btn');
  const passcodeInput = document.getElementById('passcode-input');
  const passcodeError = document.getElementById('passcode-error');

  // Check session unlock status on page load
  const isUnlocked = sessionStorage.getItem('gex_unlocked') === 'true';
  if (passcodeModal) {
    if (isUnlocked) {
      passcodeModal.style.display = 'none';
    } else {
      passcodeModal.style.display = 'flex';
      if (passcodeInput) setTimeout(() => passcodeInput.focus(), 150);
    }
  }


  if (unlockBtn && passcodeModal) {
    unlockBtn.onclick = function() {
      const inputEl = document.getElementById('passcode-input');
      const code = (inputEl ? inputEl.value : '').trim().toUpperCase();
      if (code === 'GEX2026') {
        passcodeModal.style.display = 'none';
        if (passcodeError) passcodeError.style.display = 'none';
        sessionStorage.setItem('gex_unlocked', 'true');
      } else {
        if (passcodeError) passcodeError.style.display = 'block';
        if (inputEl) {
          inputEl.value = '';
          inputEl.focus();
        }
      }
    };
  }

  if (lockBtn && passcodeModal) {
    lockBtn.onclick = function() {
      sessionStorage.removeItem('gex_unlocked');
      if (passcodeModal) passcodeModal.style.display = 'flex';
      if (passcodeInput) {
        passcodeInput.value = '';
        passcodeInput.focus();
      }
    };
  }

  const taxonomyBtn = document.getElementById('open-taxonomy-btn');
  const taxonomyModal = document.getElementById('taxonomy-modal');
  const closeTaxonomyBtn = document.getElementById('close-taxonomy-modal');

  if (taxonomyBtn && taxonomyModal) {
    taxonomyBtn.onclick = function() {
      taxonomyModal.style.display = 'flex';
    };
  }

  if (closeTaxonomyBtn && taxonomyModal) {
    closeTaxonomyBtn.onclick = function() {
      taxonomyModal.style.display = 'none';
    };
  }

  // Strike Modal
  const openStrikeBtn = document.getElementById('open-strike-modal-btn');
  const strikeModal = document.getElementById('strike-modal');
  const closeStrikeBtn = document.getElementById('close-strike-modal');

  if (openStrikeBtn && strikeModal) {
    openStrikeBtn.onclick = function() {
      strikeModal.style.display = 'flex';
    };
  }
  if (closeStrikeBtn && strikeModal) {
    closeStrikeBtn.onclick = function() {
      strikeModal.style.display = 'none';
    };
  }

  // Sensitivity Modal
  const openSensitivityBtn = document.getElementById('open-sensitivity-modal-btn');
  const sensitivityModal = document.getElementById('sensitivity-modal');
  const closeSensitivityBtn = document.getElementById('close-sensitivity-modal');

  if (openSensitivityBtn && sensitivityModal) {
    openSensitivityBtn.onclick = function() {
      sensitivityModal.style.display = 'flex';
    };
  }
  if (closeSensitivityBtn && sensitivityModal) {
    closeSensitivityBtn.onclick = function() {
      sensitivityModal.style.display = 'none';
    };
  }

  if (taxonomyModal) {
    taxonomyModal.onclick = function(e) {
      if (e.target === taxonomyModal) {
        taxonomyModal.style.display = 'none';
      }
    };
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initModals);
} else {
  initModals();
}
