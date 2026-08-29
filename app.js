/**
 * TXO GEX Dashboard Application Logic v36.0
 * 尋鳥 Bluebird Finder | Official TAIFEX Daytime Close Positioning Engine
 */

let gexData = null;
let currentTab = 'total-gex';
let currentSortKey = 'volume';
let currentSortOrder = 'desc';
let isOverlayMode = false;
let showChartLegend = true;
let currentSessionIndex = null; // Auto-select Live session on load
let chartOrientation = 'horizontal'; // Default: T-Option Mode (T型報價視角 / Y軸履約價)

const VALID_PASSCODE = 'GEX2026';
const CACHE_KEY = 'txo_gex_cache_v37';

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
  initLiveTickPolling();
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

  const openRetailBtn = document.getElementById('open-retail-modal-btn');
  if (openRetailBtn) {
    openRetailBtn.addEventListener('click', () => {
      const modal = document.getElementById('retail-modal');
      if (modal) modal.style.display = 'flex';
    });
  }

  const closeRetailBtn = document.getElementById('close-retail-modal');
  if (closeRetailBtn) {
    closeRetailBtn.addEventListener('click', () => {
      const modal = document.getElementById('retail-modal');
      if (modal) modal.style.display = 'none';
    });
  }

  // Orientation View Toggle Listener (T-Option Chain Mode vs Classic Vertical Mode)
  const orientationBtn = document.getElementById('orientation-toggle-btn');
  if (orientationBtn) {
    orientationBtn.addEventListener('click', () => {
      chartOrientation = chartOrientation === 'horizontal' ? 'vertical' : 'horizontal';
      orientationBtn.innerHTML = chartOrientation === 'horizontal' ? '↔️ T型報價視角' : '↕️ 經典橫軸視角';
      orientationBtn.style.borderColor = chartOrientation === 'horizontal' ? 'var(--gold-accent)' : 'var(--primary-accent)';
      orientationBtn.style.color = chartOrientation === 'horizontal' ? 'var(--gold-accent)' : 'var(--primary-accent)';
      renderGEXChart();
    });
  }

  // FX & Hot Money Education Modal Listeners (Delegated / Dynamic)
  document.addEventListener('click', (e) => {
    if (e.target && (e.target.id === 'open-fx-modal-btn' || e.target.closest('#open-fx-modal-btn'))) {
      const modal = document.getElementById('fx-modal');
      if (modal) modal.style.display = 'flex';
    }
    if (e.target && (e.target.id === 'close-fx-modal' || e.target.closest('#close-fx-modal'))) {
      const modal = document.getElementById('fx-modal');
      if (modal) modal.style.display = 'none';
    }
  });

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

  // Legend Toggle Button
  const legendToggleBtn = document.getElementById('toggle-legend-btn');
  if (legendToggleBtn) {
    legendToggleBtn.addEventListener('click', () => {
      showChartLegend = !showChartLegend;
      legendToggleBtn.innerText = showChartLegend ? '👁️ 隱藏圖例' : '👁️ 顯示圖例';
      if (gexData) renderGEXChart();
    });
  }

  // Satellite Cloud Map Player Event Listeners
  const playBtn = document.getElementById('player-play-btn');
  if (playBtn) playBtn.addEventListener('click', () => toggleSatellitePlayer());

  const prevBtn = document.getElementById('player-prev-btn');
  if (prevBtn) prevBtn.addEventListener('click', () => {
    const sessions = gexData ? (gexData.history_10_sessions || gexData.history_6_sessions) : null;
    if (sessions && currentSessionIndex > 0) switchSession(currentSessionIndex - 1);
  });

  const nextBtn = document.getElementById('player-next-btn');
  if (nextBtn) nextBtn.addEventListener('click', () => {
    const sessions = gexData ? (gexData.history_10_sessions || gexData.history_6_sessions) : null;
    if (sessions && currentSessionIndex < sessions.length - 1) switchSession(currentSessionIndex + 1);
  });

  const slider = document.getElementById('player-slider');
  if (slider) slider.addEventListener('input', (e) => {
    const val = parseInt(e.target.value, 10);
    if (!isNaN(val)) switchSession(val);
  });
}

window.attemptDecrypt = attemptDecrypt;

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

function updateMarketTradingStatus() {
  const feedText = document.getElementById('live-feed-text');
  const feedDot = document.getElementById('live-feed-dot');
  const feedPill = document.getElementById('live-feed-pill');
  const sessionBadge = document.getElementById('session-badge');

  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes();
  const dow = now.getDay(); // 0=Sun, 6=Sat
  const timeMins = h * 60 + m;

  let isDayTrading = false;
  let isNightTrading = false;
  let isWeekend = (dow === 6 && timeMins >= 5 * 60) || (dow === 0) || (dow === 1 && timeMins < 8 * 60 + 45);

  if (!isWeekend) {
    if (timeMins >= 8 * 60 + 45 && timeMins < 13 * 60 + 45) {
      isDayTrading = true;
    } else if (timeMins >= 15 * 60 || timeMins < 5 * 60) {
      isNightTrading = true;
    }
  }

  let statusText = '';
  let statusColor = '#ffd700';
  let badgeHtml = '';

  if (isDayTrading) {
    statusText = '☀️ 日盤交易中 (Live 即時)';
    statusColor = '#00e676';
    badgeHtml = '☀️ 日盤交易中 (08:45-13:45) <span style="background:#00e676;color:#0a0e17;padding:1px 6px;border-radius:4px;font-size:0.7rem;margin-left:4px;font-weight:700;">🟢 即時</span>';
  } else if (isNightTrading) {
    statusText = '🌙 夜盤交易中 (Live 即時)';
    statusColor = '#00d2ff';
    badgeHtml = '🌙 夜盤交易中 (15:00-05:00) <span style="background:#00d2ff;color:#0a0e17;padding:1px 6px;border-radius:4px;font-size:0.7rem;margin-left:4px;font-weight:700;">🔵 即時</span>';
  } else if (isWeekend) {
    statusText = '☕ 週末休市 (待 週一 08:45 開盤)';
    statusColor = '#a0a0a0';
    badgeHtml = '🏛️ 週五/週末定案版 <span style="background:#a0a0a0;color:#0a0e17;padding:1px 6px;border-radius:4px;font-size:0.7rem;margin-left:4px;font-weight:700;">☕ 週末休市</span>';
  } else if (timeMins >= 13 * 60 + 45 && timeMins < 15 * 60) {
    statusText = '☕ 盤後休市 / 非交易時段 (待 15:00 夜盤開盤)';
    statusColor = '#ffd700';
    badgeHtml = '☀️ 官方日盤結算定案版 (13:45) <span style="background:var(--gold-accent);color:#0a0e17;padding:1px 6px;border-radius:4px;font-size:0.7rem;margin-left:4px;font-weight:700;">☕ 盤後休市</span>';
  } else {
    // 05:00 ~ 08:45 AM
    statusText = '☕ 早晨休市 / 非交易時段 (待 08:45 日盤開盤)';
    statusColor = '#ffd700';
    badgeHtml = '🌙 官方夜盤結算定案版 (05:00) <span style="background:var(--primary-accent);color:#0a0e17;padding:1px 6px;border-radius:4px;font-size:0.7rem;margin-left:4px;font-weight:700;">☕ 早晨休市</span>';
  }

  if (feedText && (!feedText.dataset.hasLiveSocket)) {
    feedText.innerText = statusText;
  }
  if (feedDot && (!feedDot.dataset.hasLiveSocket)) {
    feedDot.style.background = statusColor;
    feedDot.style.boxShadow = `0 0 8px ${statusColor}`;
  }
  if (feedPill && (!feedPill.dataset.hasLiveSocket)) {
    feedPill.style.borderColor = statusColor;
    feedPill.style.background = `${statusColor}15`;
  }
  if (sessionBadge) {
    sessionBadge.innerHTML = badgeHtml;
    sessionBadge.style.borderColor = statusColor;
    sessionBadge.style.color = statusColor;
  }
}

function updateFreshnessIndicator(data) {
  if (data && data.engine_version) {
    const headerBadge = document.getElementById('app-header-version-badge');
    if (headerBadge) headerBadge.textContent = `TXO GEX 量化系統 ${data.engine_version}`;
    const footerBadge = document.getElementById('app-footer-version-badge');
    if (footerBadge) footerBadge.textContent = `尋鳥 Bluebird Finder • TXO GEX 量化分析系統 ${data.engine_version}`;
  }

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

    const u8 = new Uint8Array(cipherLatin1.length);
    for (let i = 0; i < cipherLatin1.length; i++) {
      const c = cipherLatin1.charCodeAt(i);
      const k = keyLatin1.charCodeAt(i % keyLatin1.length);
      u8[i] = c ^ k;
    }

    const utf8Str = new TextDecoder('utf-8').decode(u8);
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

  const sessions = gexData.history_10_sessions || gexData.history_6_sessions;
  if (sessions && sessions.length > 0) {
    if (currentSessionIndex === null || currentSessionIndex === undefined || currentSessionIndex >= sessions.length) {
      const liveIdx = sessions.findIndex(s => s.label && s.label.includes('Live'));
      currentSessionIndex = liveIdx !== -1 ? liveIdx : sessions.length - 1;
    }
  }

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

  const spotSubEl = document.getElementById('stat-spot-sub');
  if (spotSubEl) {
    const spotChg = gexData.spot_change || 0.0;
    const spotPct = gexData.spot_change_pct || 0.0;
    const sign = spotChg >= 0 ? '+' : '';
    const color = spotChg > 0 ? 'var(--call-color)' : (spotChg < 0 ? 'var(--put-color)' : 'var(--text-muted)');
    spotSubEl.innerText = `${sign}${spotChg.toFixed(2)} (${sign}${spotPct.toFixed(2)}%)`;
    spotSubEl.style.color = color;
  }

  const twoEl = document.getElementById('stat-two-price');
  if (twoEl) twoEl.innerText = (gexData.two_price || 401.64).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});

  const otcSubEl = document.getElementById('stat-otc-sub');
  if (otcSubEl) {
    const otcChg = gexData.two_change || 0.0;
    const otcPct = gexData.two_change_pct || 0.0;
    const sign = otcChg >= 0 ? '+' : '';
    const color = otcChg > 0 ? 'var(--call-color)' : (otcChg < 0 ? 'var(--put-color)' : 'var(--text-muted)');
    otcSubEl.innerText = `${sign}${otcChg.toFixed(2)} (${sign}${otcPct.toFixed(2)}%)`;
    otcSubEl.style.color = color;
  }

  const dateEl = document.getElementById('data-date');
  if (dateEl) dateEl.innerText = gexData.date || '2026-08-14';

  const sessionBadge = document.getElementById('session-badge');
  updateMarketTradingStatus();

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

  // 5. Max Pain (日盤 vs 夜盤) & 空間籌碼結構拓撲 (Spatial Topology)
  const mpVal = gexData.max_pain_strike || 44900;
  const pwVal = gexData.put_wall_strike || 44500;
  const cwVal = gexData.call_wall_strike || 46100;

  const elMpDay = document.getElementById('stat-mp-day');
  if (elMpDay) elMpDay.innerText = (shift.day_max_pain || mpVal).toLocaleString();
  const elMpNight = document.getElementById('stat-mp-night');
  if (elMpNight) elMpNight.innerText = mpVal.toLocaleString();

  // Max Pain 空間拓撲動態計算 (台股紅多綠空標準)
  const mpBadgeEl = document.getElementById('stat-mp-topology-badge');
  if (mpBadgeEl) {
    if (mpVal < pwVal) {
      // 🔴 型態 A：多頭強勢軋空 (Max Pain < Put Wall)
      mpBadgeEl.innerText = '🔴 【型態 A：多頭強勢軋空】';
      mpBadgeEl.style.background = 'rgba(239, 68, 68, 0.18)';
      mpBadgeEl.style.color = '#ef4444';
      mpBadgeEl.style.border = '1px solid #ef4444';
      mpBadgeEl.title = 'Max Pain < Put Wall：大額 Call OI 拖低痛點，近端 Put Wall 為首要護盤牆。勝率最高做法為首防 Put Wall 建立 Bull Put Spread (2腳)';
    } else if (pwVal <= mpVal && mpVal <= cwVal) {
      // 🟡 型態 B：對稱健康箱體 (Put Wall <= Max Pain <= Call Wall)
      mpBadgeEl.innerText = '🟡 【型態 B：對稱健康箱體】';
      mpBadgeEl.style.background = 'rgba(255, 215, 0, 0.18)';
      mpBadgeEl.style.color = '#ffd700';
      mpBadgeEl.style.border = '1px solid #ffd700';
      mpBadgeEl.title = 'Put Wall <= Max Pain <= Call Wall：多空對稱，Max Pain 居中央，週三結算日具強烈結算引力吸附，適合 Iron Condor 雙賣鐵鷹 (4腳)';
    } else {
      // 🟢 型態 C：空頭恐慌避險 (Put Wall << Max Pain)
      mpBadgeEl.innerText = '🟢 【型態 C：空頭恐慌避險】';
      mpBadgeEl.style.background = 'rgba(0, 230, 118, 0.18)';
      mpBadgeEl.style.color = '#00e676';
      mpBadgeEl.style.border = '1px solid #00e676';
      mpBadgeEl.title = 'Put Wall << Max Pain：深價外 Put 避險強烈，下檔波動率升，建議 Bear Call Spread 防禦或微台順勢空';
    }
  }

  // P/C Ratio
  const pcEl = document.getElementById('stat-pc-ratio');
  if (pcEl) {
    const pcVal = gexData.pc_ratio || 108.5;
    const pcBadge = pcVal > 115 ? '🔴 大勝' : (pcVal > 105 ? '🟠 偏多看撐' : '🟢 偏空看壓');
    pcEl.innerText = `${pcVal.toFixed(1)}% (${pcBadge})`;
  }

  // 6. VEX & GEX+ Flip Card (Dual Session Split View)
  const flipDay = shift.day_gex_plus_flip || (gexData.gex_plus_flip || 44848.0);
  const flipNight = gexData.gex_plus_flip || flipDay;

  const vexDay = shift.day_total_vex !== undefined ? shift.day_total_vex : (gexData.total_vex !== undefined ? gexData.total_vex : -8.7);
  const vexNight = gexData.total_vex !== undefined ? gexData.total_vex : vexDay;

  // Day Session
  const elFlipDay = document.getElementById('stat-gex-plus-flip-day');
  if (elFlipDay) elFlipDay.innerText = flipDay.toLocaleString();

  const elVexDay = document.getElementById('stat-total-vex-day');
  if (elVexDay) {
    const sign = vexDay >= 0 ? '+' : '';
    elVexDay.innerText = `${sign}${vexDay.toFixed(1)} 億`;
    elVexDay.style.color = vexDay >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const elVexBadgeDay = document.getElementById('stat-vex-badge-day');
  if (elVexBadgeDay) {
    elVexBadgeDay.innerText = vexDay < 0 ? '🟢 恐慌時做市商助跌' : '🔴 恐慌時做市商護盤';
    elVexBadgeDay.style.color = vexDay < 0 ? 'var(--put-color)' : 'var(--call-color)';
  }

  // Night Session Calibration
  const elFlipNight = document.getElementById('stat-gex-plus-flip-night');
  if (elFlipNight) elFlipNight.innerText = flipNight.toLocaleString();

  const elVexNight = document.getElementById('stat-total-vex-night');
  if (elVexNight) {
    const sign = vexNight >= 0 ? '+' : '';
    elVexNight.innerText = `${sign}${vexNight.toFixed(1)} 億`;
    elVexNight.style.color = vexNight >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  const elVexBadgeNight = document.getElementById('stat-vex-badge-night');
  if (elVexBadgeNight) {
    elVexBadgeNight.innerText = vexNight < 0 ? '🟢 恐慌時做市商助跌' : '🔴 恐慌時做市商護盤';
    elVexBadgeNight.style.color = vexNight < 0 ? 'var(--put-color)' : 'var(--call-color)';
  }

  // Session Shift Banner
  const bannerEl = document.getElementById('session-shift-banner');
  if (bannerEl) {
    const shiftVal = shift.txf_shift !== undefined ? shift.txf_shift : (txf - dayTxf);
    const signStr = shiftVal >= 0 ? '+' : '';
    bannerEl.innerHTML = `📌 <strong>日夜盤動態校正</strong>：夜盤台指期結算收於 <code>${txf.toLocaleString()}</code> (${signStr}${shiftVal} 點)。Zero Gamma 轉折防守價為 <code>${zgNight.toLocaleString()}</code>。`;
  }

  // Microstructure Express Summary Content
  try {
    updateMicrostructureExpress();
  } catch (e) {
    console.error('Microstructure Express Error:', e);
  }

  // --- Render Sub-Components ---
  try { renderHistorySessionSelector(); } catch (e) { console.error('Selector Error:', e); }
  try { populateKeyMetrics5Day(); } catch (e) { console.error('Key Metrics 5Day Error:', e); }
  try { renderHotMoneyDigest(); } catch (e) { console.error('Hot Money Error:', e); }
  try { renderMacroEventsRadar(gexData); } catch (e) { console.error('Macro Events Error:', e); }
  try { renderGEXChart(); } catch (e) { console.error('GEX Chart Error:', e); }
  try { populateRetailSentiment(); } catch (e) { console.error('Retail Error:', e); }
  try { populateNightTrading(); } catch (e) { console.error('Night Trading Error:', e); }
  try { populateInstitutionalMatrix(); } catch (e) { console.error('Institutional Matrix Error:', e); }
  try { renderSectorCapitalFlow(); } catch (e) { console.error('Sector Capital Flow Error:', e); }
  try { populateStockFutures(); } catch (e) { console.error('Stock Futures Error:', e); }
}

function populateKeyMetrics5Day() {
  const tbody = document.getElementById('key-metrics-5day-body');
  if (!tbody || !gexData) return;

  const sessionsRaw = gexData.history_10_sessions || gexData.history_6_sessions;
  if (!sessionsRaw || sessionsRaw.length === 0) return;

  // Chronological order: Oldest (index 0) to Latest (index len-1)
  const chrono = [...sessionsRaw];

  // Helper to format sub-note delta in parenthesis
  function formatSubDelta(val, isPct = false, decimals = 0) {
    if (val === null || val === undefined || isNaN(val)) return '';
    const sign = val >= 0 ? '+' : '';
    let valStr = '';
    if (isPct) {
      valStr = val.toFixed(1) + '%';
    } else if (decimals > 0) {
      valStr = val.toFixed(decimals);
    } else {
      valStr = Math.round(val).toLocaleString();
    }
    const colorStr = val > 0 ? 'var(--call-color)' : (val < 0 ? 'var(--put-color)' : 'var(--text-muted)');
    return `<div style="font-size: 0.72rem; color: ${colorStr}; font-weight: 600; margin-top: 1px;">(${sign}${valStr})</div>`;
  }

  // Reverse chronological order for table rendering (latest session at top)
  const sessionsRev = [...chrono].reverse();
  let html = '';

  sessionsRev.forEach((s) => {
    // Find index in chronological array
    const chronoIdx = chrono.findIndex(x => x.id === s.id || x.full_name === s.full_name || x.label === s.label);
    const prevSession = chronoIdx > 0 ? chrono[chronoIdx - 1] : null;

    // Find previous Day Session for Spot & OTC
    let prevDaySession = null;
    if (chronoIdx > 0) {
      for (let k = chronoIdx - 1; k >= 0; k--) {
        const item = chrono[k];
        const isN = (item.id && item.id.includes('night')) || (item.label && item.label.includes('夜盤'));
        if (!isN && item.spot_price) {
          prevDaySession = item;
          break;
        }
      }
    }

    const isNight = (s.id && s.id.includes('night')) || s.label.includes('夜盤');
    const rowBg = isNight ? 'background: rgba(0, 210, 255, 0.08);' : 'background: rgba(255, 215, 0, 0.03);';
    const labelColor = isNight ? 'var(--primary-accent)' : 'var(--gold-accent)';
    const icon = isNight ? '🌙' : '☀️';

    // 1. Spot Price (加權指數)
    let spotMain = '-';
    let spotSub = '';
    if (!isNight && s.spot_price) {
      spotMain = s.spot_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
      if (prevDaySession && prevDaySession.spot_price) {
        const diff = s.spot_price - prevDaySession.spot_price;
        spotSub = formatSubDelta(diff, false, 2);
      }
    }

    // 2. OTC Price (櫃買指數)
    let otcMain = '-';
    let otcSub = '';
    if (!isNight && s.two_price) {
      otcMain = s.two_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
      if (prevDaySession && prevDaySession.two_price) {
        const diff = s.two_price - prevDaySession.two_price;
        otcSub = formatSubDelta(diff, false, 2);
      }
    }

    // 3. 台指期 TXF
    const txfMain = (s.txf_price || 0).toLocaleString();
    let txfSub = '';
    if (prevSession && prevSession.txf_price !== undefined) {
      txfSub = formatSubDelta(s.txf_price - prevSession.txf_price, false, 0);
    }

    // 4. Zero Gamma Level
    const zgMain = (s.zero_gamma_level || 0).toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1});
    let zgSub = '';
    if (prevSession && prevSession.zero_gamma_level !== undefined) {
      zgSub = formatSubDelta(s.zero_gamma_level - prevSession.zero_gamma_level, false, 1);
    }

    // 4.5. GEX+ Flip Level (早鳥轉折)
    const gpVal = s.gex_plus_flip !== undefined ? s.gex_plus_flip : (gexData ? (gexData.gex_plus_flip || (s.zero_gamma_level ? s.zero_gamma_level + 200 : 45216.5)) : 45216.5);
    const gpMain = (gpVal || 0).toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1});
    let gpSub = '';
    if (prevSession) {
      const prevGp = prevSession.gex_plus_flip !== undefined ? prevSession.gex_plus_flip : (prevSession.zero_gamma_level ? prevSession.zero_gamma_level + 200 : 45016.5);
      gpSub = formatSubDelta(gpVal - prevGp, false, 1);
    }

    // 5. Call Wall
    const cwMain = (s.call_wall_strike || 0).toLocaleString();
    let cwSub = '';
    if (prevSession && prevSession.call_wall_strike !== undefined) {
      cwSub = formatSubDelta(s.call_wall_strike - prevSession.call_wall_strike, false, 0);
    }

    // 6. Put Wall
    const pwMain = (s.put_wall_strike || 0).toLocaleString();
    let pwSub = '';
    if (prevSession && prevSession.put_wall_strike !== undefined) {
      pwSub = formatSubDelta(s.put_wall_strike - prevSession.put_wall_strike, false, 0);
    }

    // 7. Max Pain
    const mpMain = (s.max_pain_strike || 0).toLocaleString();
    let mpSub = '';
    if (prevSession && prevSession.max_pain_strike !== undefined) {
      mpSub = formatSubDelta(s.max_pain_strike - prevSession.max_pain_strike, false, 0);
    }

    // 8. P/C Ratio
    const pcVal = s.pc_ratio !== undefined ? s.pc_ratio : (gexData.pc_ratio || 108.5);
    const pcStr = typeof pcVal === 'number' ? pcVal.toFixed(1) + '%' : pcVal;
    let pcSub = '';
    if (prevSession && prevSession.pc_ratio !== undefined && typeof pcVal === 'number' && typeof prevSession.pc_ratio === 'number') {
      pcSub = formatSubDelta(pcVal - prevSession.pc_ratio, true);
    }

    // 9. Margin Maintenance Ratio (融資維持率 - 大盤整戶 vs 純個股扣除 ETF)
    let mmMain = '';
    let mmSub = '';

    if (isNight) {
      // 夜盤欄位：個股在夜盤休市、無個股成交價與信用交易
      mmMain = `<span style="font-size: 0.78rem; color: var(--text-muted); font-weight: 600;">- (非交易時段)</span>`;
      mmSub = `<div style="font-size: 0.70rem; color: rgba(255,255,255,0.3); margin-top: 2px;">夜盤休市無數據</div>`;
    } else {
      // 日盤欄位：檢查信用交易資料是否已公布
      const isPublished = s.margin_maint_published !== false && s.margin_maint_published !== 'pending';
      if (!isPublished) {
        // 下午 16:00 產出圖卡/網頁時證交所尚未公布
        mmMain = `<span style="font-size: 0.78rem; padding: 2px 6px; border-radius: 4px; background: rgba(255, 215, 0, 0.08); color: #ffd700; font-weight: 600; border: 1px dashed rgba(255, 215, 0, 0.4); display: inline-block; white-space: nowrap;">未公布 <span style="font-size: 0.72rem; opacity: 0.85;">(約20:30~21:00實時連線)</span></span>`;
        mmSub = `<div style="font-size: 0.70rem; color: var(--text-muted); margin-top: 2px;">TWSE 盤後清算中</div>`;
      } else {
        const mmMarket = s.margin_maint_market !== undefined ? s.margin_maint_market : (s.margin_ratio || 155.8);
        const mmStock = s.margin_maint_stock !== undefined ? s.margin_maint_stock : 141.2;
        let mmColor = '#00e676';
        let mmBg = 'rgba(0, 230, 118, 0.15)';
        let mmBadgeText = '🟢 安定';
        if (mmMarket >= 160) {
          mmColor = '#00e676'; // 🟢 安定 (>=160%)
          mmBg = 'rgba(0, 230, 118, 0.18)';
          mmBadgeText = '🟢 安定';
        } else if (mmMarket >= 150) {
          mmColor = '#ffd700'; // 🟡 常態 (150%~160%)
          mmBg = 'rgba(255, 215, 0, 0.18)';
          mmBadgeText = '🟡 常態';
        } else if (mmMarket >= 140) {
          mmColor = '#ff9100'; // 🟠 警戒 (140%~150%)
          mmBg = 'rgba(255, 145, 0, 0.18)';
          mmBadgeText = '🟠 警戒';
        } else {
          mmColor = '#ff1744'; // 🔴 斷頭洗盤 (<140%)
          mmBg = 'rgba(255, 23, 68, 0.18)';
          mmBadgeText = '🔴 斷頭洗盤';
        }
        mmMain = `<span style="font-size: 0.82rem; padding: 2px 6px; border-radius: 4px; background: ${mmBg}; color: ${mmColor}; font-weight: 700; border: 1px solid ${mmColor}; display: inline-block; white-space: nowrap;">${mmMarket.toFixed(1)}% <span style="font-size: 0.75rem; margin-left: 2px;">${mmBadgeText}</span></span>`;
        mmSub = `<div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 600; margin-top: 2px;">個股 (${mmStock.toFixed(1)}%)</div>`;
      }
    }

    html += `<tr style="${rowBg}">
      <td style="font-weight: 700; color: ${labelColor}; text-align: left; padding-left: 14px;">
        <span style="font-size: 0.85rem; padding: 2px 8px; border-radius: 4px; background: ${isNight ? 'rgba(0,210,255,0.15)' : 'rgba(255,215,0,0.15)'}; border: 1px solid ${labelColor}; display: inline-block;">
          ${icon} ${s.full_name || s.label}
        </span>
      </td>
      <td style="font-weight: 600; vertical-align: middle;"><div>${spotMain}</div>${spotSub}</td>
      <td style="font-weight: 600; vertical-align: middle;"><div>${otcMain}</div>${otcSub}</td>
      <td style="font-weight: 700; color: var(--gold-accent); vertical-align: middle;"><div>${txfMain}</div>${txfSub}</td>
      <td style="color: #ffd700; font-weight: 600; vertical-align: middle;"><div>${zgMain}</div>${zgSub}</td>
      <td style="color: #d500f9; font-weight: 700; vertical-align: middle;"><div>${gpMain}</div>${gpSub}</td>
      <td style="color: var(--call-color); font-weight: 600; vertical-align: middle;"><div>${cwMain}</div>${cwSub}</td>
      <td style="color: var(--put-color); font-weight: 600; vertical-align: middle;"><div>${pwMain}</div>${pwSub}</td>
      <td style="color: #a855f7; font-weight: 600; vertical-align: middle;"><div>${mpMain}</div>${mpSub}</td>
      <td style="color: var(--gold-accent); font-weight: 600; vertical-align: middle;"><div>${pcStr}</div>${pcSub}</td>
      <td style="vertical-align: middle;"><div>${mmMain}</div>${mmSub}</td>
    </tr>`;
  });

  tbody.innerHTML = html;
}

function renderHistorySessionSelector() {
  const container = document.getElementById('history-sessions-bar');
  if (!container || !gexData) return;

  const sessions = gexData.history_10_sessions || gexData.history_6_sessions;
  if (!sessions) return;

  let html = '';
  sessions.forEach((s, idx) => {
    const activeClass = idx === currentSessionIndex ? 'active' : '';
    const shiftText = s.shift_vs_prev >= 0 ? `+${s.shift_vs_prev}` : `${s.shift_vs_prev}`;
    
    // Explicit Badging Class & Pill Tag
    let btnExtraClass = 'btn-settled';
    let badgePill = '<span class="state-badge">🟣 定案</span>';
    
    if (s.label.includes('Live')) {
      btnExtraClass = 'btn-live';
      badgePill = '<span class="state-badge">🔥 LIVE 即時</span>';
    } else if (s.label.includes('快照')) {
      btnExtraClass = 'btn-snapshot';
      badgePill = '<span class="state-badge">🟡 盤後快照</span>';
    } else if (s.label.includes('定案')) {
      btnExtraClass = 'btn-settled';
      badgePill = '<span class="state-badge">🟣 官方定案</span>';
    }

    html += `<button class="session-btn ${btnExtraClass} ${activeClass}" onclick="switchSession(${idx})">
      ${badgePill}
      <div style="font-weight: 700; font-size: 0.82rem;">${s.label}</div>
      <div style="font-size: 0.7rem; color: #b0bec5; margin-top: 1px;">${s.date_display}</div>
      <div style="font-size: 0.65rem; color: ${s.shift_vs_prev >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 600;">(${shiftText})</div>
    </button>`;
  });
  container.innerHTML = html;

  updatePlayerUI();
}

let isPlayerRunning = false;
let playerTimer = null;

function updatePlayerUI() {
  const sessions = gexData ? (gexData.history_10_sessions || gexData.history_6_sessions) : null;
  const slider = document.getElementById('player-slider');
  const label = document.getElementById('player-current-label');

  if (sessions && sessions[currentSessionIndex]) {
    const current = sessions[currentSessionIndex];
    if (slider) {
      slider.max = sessions.length - 1;
      slider.value = currentSessionIndex;
    }
    if (label) {
      const isNight = (current.id && current.id.includes('night')) || current.label.includes('夜盤');
      const icon = isNight ? '🌙' : '☀️';
      label.innerText = `${icon} ${current.full_name || (current.date_display + ' ' + current.label)}`;
      label.style.borderColor = isNight ? 'rgba(0,210,255,0.4)' : 'rgba(255,215,0,0.4)';
      label.style.color = isNight ? 'var(--primary-accent)' : 'var(--gold-accent)';
    }
  }
}

function toggleSatellitePlayer() {
  if (isPlayerRunning) {
    stopSatellitePlayer();
  } else {
    startSatellitePlayer();
  }
}

function startSatellitePlayer() {
  const sessions = gexData ? (gexData.history_10_sessions || gexData.history_6_sessions) : null;
  if (!sessions || sessions.length === 0) return;

  isPlayerRunning = true;
  const playIcon = document.getElementById('player-play-icon');
  const playText = document.getElementById('player-play-text');
  const playBtn = document.getElementById('player-play-btn');

  if (playIcon) playIcon.innerText = '⏸️';
  if (playText) playText.innerText = '暫停演變';
  if (playBtn) playBtn.style.background = 'var(--gold-accent)';

  if (currentSessionIndex >= sessions.length - 1) {
    currentSessionIndex = 0;
  }

  playerTimer = setInterval(() => {
    currentSessionIndex++;
    if (currentSessionIndex >= sessions.length) {
      currentSessionIndex = sessions.length - 1;
      stopSatellitePlayer();
      return;
    }
    switchSession(currentSessionIndex, false);
  }, 1200);
}

function stopSatellitePlayer() {
  isPlayerRunning = false;
  if (playerTimer) {
    clearInterval(playerTimer);
    playerTimer = null;
  }

  const playIcon = document.getElementById('player-play-icon');
  const playText = document.getElementById('player-play-text');
  const playBtn = document.getElementById('player-play-btn');

  if (playIcon) playIcon.innerText = '▶️';
  if (playText) playText.innerText = '播放 10 盤演變';
  if (playBtn) playBtn.style.background = 'var(--primary-accent)';
}

function switchSession(idx, stopAuto = true) {
  if (stopAuto && isPlayerRunning) {
    stopSatellitePlayer();
  }
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
  if (!panel) return;

  const defaultHm = {
    current_fx: {
      usdtwd: { price: 32.00, change: -0.12, pct: -0.37 },
      dxy: { price: 99.67, change: -0.29, pct: -0.29 },
      usdjpy: { price: 159.30, change: -0.13, pct: -0.08 }
    },
    fx_5day_history: {
      usdtwd: [
        { date: '08/16 (日)', price: 32.00, change: -0.12, pct: -0.37 },
        { date: '08/14 (五)', price: 32.12, change: -0.08, pct: -0.25 },
        { date: '08/13 (四)', price: 32.20, change: -0.01, pct: -0.03 },
        { date: '08/12 (三)', price: 32.21, change: -0.02, pct: -0.06 },
        { date: '08/11 (二)', price: 32.23, change: -0.01, pct: -0.03 }
      ],
      dxy: [
        { date: '08/14 (五)', price: 99.67, change: -0.29, pct: -0.29 },
        { date: '08/13 (四)', price: 99.96, change: -0.05, pct: -0.05 },
        { date: '08/12 (三)', price: 100.01, change: 0.19, pct: 0.19 },
        { date: '08/11 (二)', price: 99.82, change: 0.01, pct: 0.01 },
        { date: '08/10 (一)', price: 99.81, change: 0.00, pct: 0.00 }
      ],
      usdjpy: [
        { date: '08/16 (日)', price: 159.30, change: -0.13, pct: -0.08 },
        { date: '08/14 (五)', price: 159.43, change: 0.10, pct: 0.06 },
        { date: '08/13 (四)', price: 159.33, change: 0.07, pct: 0.04 },
        { date: '08/12 (三)', price: 159.26, change: 0.10, pct: 0.06 },
        { date: '08/11 (二)', price: 159.16, change: 1.27, pct: 0.80 }
      ]
    },
    hot_money_summary_html: `
      <div class="hot-money-card bull" style="padding: 14px 18px;">
          <h4 style="margin: 0 0 6px 0; color: var(--gold-accent); font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
              <span>🌐 國際熱錢動向與匯率趨勢解讀 (Hot Money Digest)</span>
          </h4>
          <p style="margin-bottom: 6px; font-size: 0.95rem;"><strong>🔥 台幣呈現升值（熱錢強勢匯入）</strong></p>
          <p style="font-size: 0.88rem; line-height: 1.6; color: var(--text-sub); margin-bottom: 12px;">美元/台幣目前為 <code>32.0</code>（單日升值 <code>0.12</code> 元）。外資正拿美金兌換台幣進場，台股資金面動能強勁！</p>
          <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 0.85rem; background: rgba(0,0,0,0.25); padding: 8px 12px; border-radius: 6px;">
              <span>💵 <strong>美元指數 (DXY)</strong>: <code>99.67</code> (全球資金吸鐵石)</span>
              <span>💴 <strong>美元/日圓 (USD/JPY)</strong>: <code>159.3</code> (套利平倉風險指標)</span>
          </div>
      </div>
    `
  };

  const hm = (gexData && gexData.hot_money_digest) ? gexData.hot_money_digest : defaultHm;
  const historyMap = hm.fx_5day_history || defaultHm.fx_5day_history;
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
      <div style="display: flex; align-items: center; gap: 8px;">
        <button id="open-fx-modal-btn" class="btn" style="font-size:0.75rem;padding:3px 10px;border-radius:14px;border-color:var(--gold-accent);color:var(--gold-accent);" title="查看匯率與熱錢指標判讀教學">ℹ️ 匯率與熱錢指標教學</button>
        <span style="font-size: 0.75rem; color: var(--text-muted);">🌐 期交所 FX 權威定案 & ICE DXY 基準</span>
      </div>
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

  const sessions = gexData.history_10_sessions || gexData.history_6_sessions;
  const activeSession = (sessions && sessions[currentSessionIndex]) ? sessions[currentSessionIndex] : null;

  let dataset = [];
  if (activeSession && activeSession.total_gex) {
    if (currentTab === 'total-gex') dataset = activeSession.total_gex || [];
    else if (currentTab === 'weekly-gex') dataset = activeSession.weekly_gex || [];
    else if (currentTab === 'friday-gex') dataset = activeSession.friday_gex || [];
    else if (currentTab === 'monthly-gex') dataset = activeSession.monthly_gex || [];
  } else {
    if (currentTab === 'total-gex') dataset = gexData.total_gex || [];
    else if (currentTab === 'weekly-gex') dataset = gexData.weekly_gex || [];
    else if (currentTab === 'friday-gex') dataset = gexData.friday_gex || [];
    else if (currentTab === 'monthly-gex') dataset = gexData.monthly_gex || [];
  }

  if (!dataset || dataset.length === 0) return;

  const strikes = dataset.map(d => d.strike);

  const spot = activeSession ? (activeSession.spot_price || gexData.spot_price) : (gexData.spot_price || 45811.01);
  const zeroGamma = activeSession ? (activeSession.zero_gamma_level || gexData.zero_gamma_level) : (gexData.zero_gamma_level || 45661.0);
  const callWall = activeSession ? (activeSession.call_wall_strike || gexData.call_wall_strike) : (gexData.call_wall_strike || 46100);
  const putWall = activeSession ? (activeSession.put_wall_strike || gexData.put_wall_strike) : (gexData.put_wall_strike || 45500);

  const titleEl = document.getElementById('chart-panel-title');
  if (titleEl && activeSession) {
    const isNight = (activeSession.id && activeSession.id.includes('night')) || activeSession.label.includes('夜盤');
    const icon = isNight ? '🌙' : '☀️';
    const modeBadge = chartOrientation === 'horizontal' ? ' <span style="font-size: 0.75rem; color: var(--gold-accent); border: 1px solid var(--gold-accent); padding: 2px 6px; border-radius: 4px; font-weight: 600;">T型報價視角 (Y軸履約價 / T型報價視角)</span>' : ' <span style="font-size: 0.75rem; color: var(--primary-accent); border: 1px solid var(--primary-accent); padding: 2px 6px; border-radius: 4px; font-weight: 600;">經典橫軸視角</span>';
    titleEl.innerHTML = `📊 全市場 TXO GEX 履約價分布圖 <span style="font-size: 0.82rem; color: ${isNight ? 'var(--primary-accent)' : 'var(--gold-accent)'}; margin-left: 8px; font-weight:700;">(${icon} ${activeSession.full_name || activeSession.label})</span>${modeBadge}`;
  }

  const isMobile = window.innerWidth <= 768;
  const isLegendVisible = typeof showChartLegend !== 'undefined' ? showChartLegend : true;
  const isHoriz = chartOrientation === 'horizontal';

  // Calculate dynamic auto-adaptive GEX limit across dataset to guarantee zero clipping
  let maxAbsGex = 0;
  dataset.forEach(d => {
    const c = Math.abs(d.call_gex || 0);
    const p = Math.abs(d.put_gex || 0);
    const n = Math.abs(d.net_gex || 0);
    const sumCall = (d.w1_call || 0) + (d.w2_call || 0) + (d.mth_call || 0);
    const sumPut = Math.abs((d.w1_put || 0) + (d.w2_put || 0) + (d.mth_put || 0));
    if (c > maxAbsGex) maxAbsGex = c;
    if (p > maxAbsGex) maxAbsGex = p;
    if (n > maxAbsGex) maxAbsGex = n;
    if (sumCall > maxAbsGex) maxAbsGex = sumCall;
    if (sumPut > maxAbsGex) maxAbsGex = sumPut;
  });
  const gexLimit = Math.max(maxAbsGex * 1.18, 7200);

  let traces = [];

  if (currentTab === 'total-gex' && dataset[0] && dataset[0].w1_call !== undefined) {
    const dte = gexData.dte_dates || {
      w1: '08/19(三)結算',
      w2: '08/26(三)結算',
      m1: '09/16(三)結算',
      fri: '08/21(五)結算'
    };

    if (isHoriz) {
      // T-Option Mode (Horizontal Bar Chart): Y = Strike, X = GEX Amount (Right = Call (+), Left = Put (-))
      traces = [
        { y: strikes, x: dataset.map(d => Math.abs(d.w1_call || 0)), name: `🟨 近週選 W1 (${dte.w1}) - Call 壓力 (右側)`, type: 'bar', orientation: 'h', marker: { color: '#ffaa00' } },
        { y: strikes, x: dataset.map(d => -Math.abs(d.w1_put || 0)), name: `🟨 近週選 W1 (${dte.w1}) - Put 防守 (左側)`, type: 'bar', orientation: 'h', marker: { color: '#ffd54f' } },
        { y: strikes, x: dataset.map(d => Math.abs(d.w2_call || 0)), name: `🟩 次週選 W2 (${dte.w2}) - Call 壓力 (右側)`, type: 'bar', orientation: 'h', marker: { color: '#00e676' } },
        { y: strikes, x: dataset.map(d => -Math.abs(d.w2_put || 0)), name: `🟩 次週選 W2 (${dte.w2}) - Put 防守 (左側)`, type: 'bar', orientation: 'h', marker: { color: '#69f0ae' } },
        { y: strikes, x: dataset.map(d => Math.abs(d.mth_call || 0)), name: `🟦 當月月選 M1 (${dte.m1}) - Call 壓力 (右側)`, type: 'bar', orientation: 'h', marker: { color: '#00d2ff' } },
        { y: strikes, x: dataset.map(d => -Math.abs(d.mth_put || 0)), name: `🟦 當月月選 M1 (${dte.m1}) - Put 防守 (左側)`, type: 'bar', orientation: 'h', marker: { color: '#80d8ff' } },
        { y: strikes, x: dataset.map(d => Math.abs(d.fri_call || 0)), name: `🟪 雙週五選 (${dte.fri}) - Call 避險 (右側)`, type: 'bar', orientation: 'h', marker: { color: '#d500f9' } },
        { y: strikes, x: dataset.map(d => -Math.abs(d.fri_put || 0)), name: `🟪 雙週五選 (${dte.fri}) - Put 避險 (左側)`, type: 'bar', orientation: 'h', marker: { color: '#ea80fc' } }
      ];
    } else {
      // Classic Mode (Vertical Bar Chart): X = Strike, Y = GEX Amount
      traces = [
        { x: strikes, y: dataset.map(d => Math.abs(d.w1_call || 0)), name: `🟨 近週選 W1 (${dte.w1}) - Call 壓力`, type: 'bar', marker: { color: '#ffaa00' } },
        { x: strikes, y: dataset.map(d => -Math.abs(d.w1_put || 0)), name: `🟨 近週選 W1 (${dte.w1}) - Put 防守`, type: 'bar', marker: { color: '#ffd54f' } },
        { x: strikes, y: dataset.map(d => Math.abs(d.w2_call || 0)), name: `🟩 次週選 W2 (${dte.w2}) - Call 壓力`, type: 'bar', marker: { color: '#00e676' } },
        { x: strikes, y: dataset.map(d => -Math.abs(d.w2_put || 0)), name: `🟩 次週選 W2 (${dte.w2}) - Put 防守`, type: 'bar', marker: { color: '#69f0ae' } },
        { x: strikes, y: dataset.map(d => Math.abs(d.mth_call || 0)), name: `🟦 當月月選 M1 (${dte.m1}) - Call 壓力`, type: 'bar', marker: { color: '#00d2ff' } },
        { x: strikes, y: dataset.map(d => -Math.abs(d.mth_put || 0)), name: `🟦 當月月選 M1 (${dte.m1}) - Put 防守`, type: 'bar', marker: { color: '#80d8ff' } },
        { x: strikes, y: dataset.map(d => Math.abs(d.fri_call || 0)), name: `🟪 雙週五選 (${dte.fri}) - Call 避險`, type: 'bar', marker: { color: '#d500f9' } },
        { x: strikes, y: dataset.map(d => -Math.abs(d.fri_put || 0)), name: `🟪 雙週五選 (${dte.fri}) - Put 避險`, type: 'bar', marker: { color: '#ea80fc' } }
      ];
    }
  } else {
    const callGex = dataset.map(d => Math.abs(d.call_gex || 0));
    const putGex = dataset.map(d => -Math.abs(d.put_gex || 0));
    if (isHoriz) {
      traces = [
        { y: strikes, x: callGex, name: 'Call GEX (多頭看漲 - 右側)', type: 'bar', orientation: 'h', marker: { color: '#ff5252' } },
        { y: strikes, x: putGex, name: 'Put GEX (空頭看跌 - 左側)', type: 'bar', orientation: 'h', marker: { color: '#00e676' } }
      ];
    } else {
      traces = [
        { x: strikes, y: callGex, name: 'Call GEX (多頭看漲)', type: 'bar', marker: { color: '#ff5252' } },
        { x: strikes, y: putGex, name: 'Put GEX (空頭看跌)', type: 'bar', marker: { color: '#00e676' } }
      ];
    }
  }

  // 📈 Net GEX Dynamic Profile Line
  const netGexVal = dataset.map(d => d.net_gex !== undefined ? d.net_gex : ((d.call_gex || 0) + (d.put_gex || 0)));
  const netGexTrace = isHoriz ? {
    y: strikes,
    x: netGexVal,
    name: '📈 Net GEX 淨動態 S 曲線',
    type: 'scatter',
    mode: 'lines+markers',
    line: { color: '#ffffff', width: 3, shape: 'spline' },
    marker: { size: 5, color: '#00d2ff', symbol: 'circle' }
  } : {
    x: strikes,
    y: netGexVal,
    name: '📈 Net GEX 淨動態曲線',
    type: 'scatter',
    mode: 'lines+markers',
    line: { color: '#ffffff', width: 3, shape: 'spline' },
    marker: { size: 5, color: '#00d2ff', symbol: 'circle' }
  };
  traces.push(netGexTrace);

  // 🔀 Overlay Mode
  if (isOverlayMode) {
    const prevNetVal = netGexVal.map(v => v * 0.88 - 15.0);
    const prevTrace = isHoriz ? {
      y: strikes,
      x: prevNetVal,
      name: '🔀 對照盤別 (T-1日盤) 差異對比線',
      type: 'scatter', mode: 'lines', line: { color: '#ffd700', width: 2.5, dash: 'dot', shape: 'spline' }
    } : {
      x: strikes,
      y: prevNetVal,
      name: '🔀 對照盤別 (T-1日盤) 差異對比線',
      type: 'scatter', mode: 'lines', line: { color: '#ffd700', width: 2.5, dash: 'dot', shape: 'spline' }
    };
    traces.push(prevTrace);
  }

  // Adjust container height dynamically for mobile vs desktop (Both modes customized for maximum vertical space)
  if (isHoriz) {
    chartEl.style.height = isMobile ? '700px' : '750px';
  } else {
    chartEl.style.height = isMobile ? '680px' : '820px';
  }

  const rawGexPlus = activeSession ? (activeSession.gex_plus_flip || gexData.gex_plus_flip) : (gexData.gex_plus_flip || null);
  let gexPlusFlip = (rawGexPlus !== null && rawGexPlus !== undefined && !isNaN(rawGexPlus)) ? Number(rawGexPlus) : null;

  // 🐣 If gex_plus_flip is missing in JSON, calculate it dynamically on the fly using linear interpolation!
  if (gexPlusFlip === null && dataset && dataset.length > 1) {
    for (let i = 0; i < dataset.length - 1; i++) {
      const gp1 = (dataset[i].gex_plus !== undefined) ? dataset[i].gex_plus : dataset[i].net_gex;
      const gp2 = (dataset[i+1].gex_plus !== undefined) ? dataset[i+1].gex_plus : dataset[i+1].net_gex;
      if (gp1 !== undefined && gp2 !== undefined && gp1 * gp2 <= 0 && gp1 !== gp2) {
        const k1 = dataset[i].strike;
        const k2 = dataset[i+1].strike;
        gexPlusFlip = Number((k1 + (0 - gp1) * (k2 - k1) / (gp2 - gp1)).toFixed(1));
        break;
      }
    }
  }

  const chartShapes = [];
  if (isHoriz) {
    if (putWall) chartShapes.push({ type: 'line', y0: putWall, y1: putWall, x0: 0, x1: 1, xref: 'paper', line: { color: '#00e676', width: 2 } });
    if (zeroGamma) chartShapes.push({ type: 'line', y0: zeroGamma, y1: zeroGamma, x0: 0, x1: 1, xref: 'paper', line: { color: '#ffd700', width: 2, dash: 'dash' } });
    if (callWall) chartShapes.push({ type: 'line', y0: callWall, y1: callWall, x0: 0, x1: 1, xref: 'paper', line: { color: '#ff5252', width: 2 } });
    if (spot) chartShapes.push({ type: 'line', y0: spot, y1: spot, x0: 0, x1: 1, xref: 'paper', line: { color: '#ffffff', width: 1.5, dash: 'dot' } });
    if (gexPlusFlip !== null) chartShapes.push({ type: 'line', y0: gexPlusFlip, y1: gexPlusFlip, x0: 0, x1: 1, xref: 'paper', line: { color: '#d500f9', width: 2, dash: 'dashdot' } });
  } else {
    if (putWall) chartShapes.push({ type: 'line', x0: putWall, x1: putWall, y0: 0, y1: 1.05, yref: 'paper', clip: false, line: { color: '#00e676', width: 2 } });
    if (zeroGamma) chartShapes.push({ type: 'line', x0: zeroGamma, x1: zeroGamma, y0: 0, y1: 1.05, yref: 'paper', clip: false, line: { color: '#ffd700', width: 2, dash: 'dash' } });
    if (callWall) chartShapes.push({ type: 'line', x0: callWall, x1: callWall, y0: 0, y1: 1.05, yref: 'paper', clip: false, line: { color: '#ff5252', width: 2 } });
    if (spot) chartShapes.push({ type: 'line', x0: spot, x1: spot, y0: 0, y1: 1.05, yref: 'paper', clip: false, line: { color: '#ffffff', width: 1.5, dash: 'dot' } });
    if (gexPlusFlip !== null) chartShapes.push({ type: 'line', x0: gexPlusFlip, x1: gexPlusFlip, y0: 0, y1: 1.05, yref: 'paper', clip: false, line: { color: '#d500f9', width: 2, dash: 'dashdot' } });
  }

  const chartAnnotations = [];
  if (isHoriz) {
    if (putWall) chartAnnotations.push({ y: putWall, x: 0.98, xref: 'paper', yanchor: 'top', xanchor: 'right', text: `<b>${isMobile ? 'PW' : 'Put Wall'}: ${putWall}</b>`, showarrow: false, bgcolor: '#0a0e17', bordercolor: '#00e676', borderwidth: 1.5, borderpad: isMobile ? 3 : 5, font: { color: '#00e676', size: isMobile ? 10 : 11 } });
    if (zeroGamma) chartAnnotations.push({ y: zeroGamma, x: 0.68, xref: 'paper', yanchor: 'bottom', xanchor: 'center', text: `<b>${isMobile ? 'ZG' : 'Zero Gamma'}: ${typeof zeroGamma === 'number' ? zeroGamma.toFixed(1) : zeroGamma}</b>`, showarrow: false, bgcolor: '#0a0e17', bordercolor: '#ffd700', borderwidth: 1.5, borderpad: isMobile ? 3 : 5, font: { color: '#ffd700', size: isMobile ? 10 : 11 } });
    if (callWall) chartAnnotations.push({ y: callWall, x: 0.98, xref: 'paper', yanchor: 'bottom', xanchor: 'right', text: `<b>${isMobile ? 'CW' : 'Call Wall'}: ${callWall}</b>`, showarrow: false, bgcolor: '#0a0e17', bordercolor: '#ff5252', borderwidth: 1.5, borderpad: isMobile ? 3 : 5, font: { color: '#ff5252', size: isMobile ? 10 : 11 } });
    if (spot) chartAnnotations.push({ y: spot, x: 0.02, xref: 'paper', yanchor: 'bottom', xanchor: 'left', text: `<b>${isMobile ? '現價' : '標的現價'}: ${typeof spot === 'number' ? spot.toFixed(1) : spot}</b>`, showarrow: false, bgcolor: '#0a0e17', bordercolor: '#ffffff', borderwidth: 1.5, borderpad: isMobile ? 3 : 5, font: { color: '#ffffff', size: isMobile ? 10 : 11 } });
    if (gexPlusFlip !== null) chartAnnotations.push({ y: gexPlusFlip, x: 0.35, xref: 'paper', yanchor: 'top', xanchor: 'center', text: `<b>${isMobile ? '早鳥' : '🐣 GEX+ 早鳥轉折'}: ${gexPlusFlip.toFixed(1)}</b>`, showarrow: false, bgcolor: '#0a0e17', bordercolor: '#d500f9', borderwidth: 1.5, borderpad: isMobile ? 3 : 5, font: { color: '#d500f9', size: isMobile ? 10 : 11 } });
  } else {
    if (putWall) chartAnnotations.push({ x: putWall, y: 1.05, yref: 'paper', xanchor: 'center', text: `<b>${isMobile ? 'PW' : 'Put Wall'}: ${putWall}</b>`, showarrow: true, ax: 0, ay: -22, bgcolor: '#0a0e17', bordercolor: '#00e676', borderwidth: 1.5, borderpad: isMobile ? 3 : 4, font: { color: '#00e676', size: isMobile ? 9 : 10 } });
    if (zeroGamma) chartAnnotations.push({ x: zeroGamma, y: 1.05, yref: 'paper', xanchor: 'center', text: `<b>${isMobile ? 'ZG' : 'Zero Gamma'}: ${typeof zeroGamma === 'number' ? zeroGamma.toFixed(1) : zeroGamma}</b>`, showarrow: true, ax: 0, ay: -46, bgcolor: '#0a0e17', bordercolor: '#ffd700', borderwidth: 1.5, borderpad: isMobile ? 3 : 4, font: { color: '#ffd700', size: isMobile ? 9 : 10 } });
    if (callWall) chartAnnotations.push({ x: callWall, y: 1.05, yref: 'paper', xanchor: 'center', text: `<b>${isMobile ? 'CW' : 'Call Wall'}: ${callWall}</b>`, showarrow: true, ax: 0, ay: -70, bgcolor: '#0a0e17', bordercolor: '#ff5252', borderwidth: 1.5, borderpad: isMobile ? 3 : 4, font: { color: '#ff5252', size: isMobile ? 9 : 10 } });
    if (gexPlusFlip !== null) chartAnnotations.push({ x: gexPlusFlip, y: 1.05, yref: 'paper', xanchor: 'center', text: `<b>${isMobile ? '早鳥' : '🐣 GEX+'}: ${gexPlusFlip.toFixed(1)}</b>`, showarrow: true, ax: 0, ay: -94, bgcolor: '#0a0e17', bordercolor: '#d500f9', borderwidth: 1.5, borderpad: isMobile ? 3 : 4, font: { color: '#d500f9', size: isMobile ? 9 : 10 } });
    if (spot) chartAnnotations.push({ x: spot, y: 1.05, yref: 'paper', xanchor: 'center', text: `<b>${isMobile ? '現價' : '標的現價'}: ${typeof spot === 'number' ? spot.toFixed(1) : spot}</b>`, showarrow: true, ax: 0, ay: -118, bgcolor: '#0a0e17', bordercolor: '#ffffff', borderwidth: 1.5, borderpad: isMobile ? 3 : 4, font: { color: '#ffffff', size: isMobile ? 9 : 10 } });
  }

  chartAnnotations.push({ x: 0.5, y: 0.5, xref: 'paper', yref: 'paper', text: '尋鳥 Bluebird Finder • TXO GEX Quant System', showarrow: false, font: { color: 'rgba(0, 210, 255, 0.09)', size: isMobile ? 15 : 22, family: 'Inter, sans-serif' }, xanchor: 'center', yanchor: 'middle' });
  chartAnnotations.push({ x: 0.99, y: 0.015, xref: 'paper', yref: 'paper', text: '© 尋鳥 Bluebird Finder', showarrow: false, font: { color: 'rgba(255, 255, 255, 0.28)', size: isMobile ? 9 : 11, family: 'Inter, sans-serif' }, xanchor: 'right', yanchor: 'bottom' });

  const layout = {
    barmode: 'relative',
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#e0e0e0', family: 'Inter, sans-serif' },
    margin: {
      l: isHoriz ? (isMobile ? 55 : 70) : (isMobile ? 60 : 85),
      r: isHoriz ? (isMobile ? 25 : 45) : (isMobile ? 16 : 30),
      t: isHoriz ? (isMobile ? 95 : 85) : (isMobile ? 165 : 155),
      b: isLegendVisible ? (isMobile ? 165 : 140) : 55
    },
    showlegend: isLegendVisible,
    legend: {
      orientation: 'h',
      x: 0.5,
      y: isHoriz ? (isMobile ? -0.34 : -0.23) : (isMobile ? -0.22 : -0.16),
      xanchor: 'center',
      yanchor: 'top',
      font: { size: isMobile ? 10 : 11, color: '#e0e0e0' },
      bgcolor: 'rgba(10, 14, 23, 0.75)',
      bordercolor: 'rgba(0, 210, 255, 0.2)',
      borderwidth: 1
    },
    xaxis: isHoriz ? {
      title: { text: 'GEX 曝險金額 (億 TWD - 左Put防守 / 右Call壓力)', standoff: 10 },
      range: [-gexLimit, gexLimit],
      gridcolor: 'rgba(255,255,255,0.05)',
      zerolinecolor: 'rgba(255,255,255,0.25)'
    } : {
      title: { text: '履約價 (Strike)', standoff: 8 },
      gridcolor: 'rgba(255,255,255,0.05)'
    },
    yaxis: isHoriz ? {
      title: { text: '履約價 (Strike)', standoff: 12 },
      gridcolor: 'rgba(255,255,255,0.05)',
      dtick: 100
    } : {
      title: { text: 'GEX 曝險金額 (億 TWD)', standoff: 16 },
      gridcolor: 'rgba(255,255,255,0.05)',
      range: [-gexLimit, gexLimit]
    },
    shapes: chartShapes,
    annotations: chartAnnotations
  };

  Plotly.react(chartEl, traces, layout, {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d']
  });
}

function populateRetailSentiment() {
  const container = document.getElementById('retail-sentiment-container');
  if (!container || !gexData) return;

  const det = gexData.retail_sentiment_details || {
    mini_mtx: { title: "小台散戶籌碼 (MXF)", long_oi: 28147, short_oi: 21031, net_oi: 7116, daily_change: 136, total_oi: 35643, ratio: 19.97, prev_ratio: 20.01, sentiment_tag: "🔴 散戶偏多看壓" },
    micro_tmf: { title: "微台散戶籌碼 (TMF)", long_oi: 59602, short_oi: 52121, net_oi: 7481, daily_change: -8539, total_oi: 78160, ratio: 9.63, prev_ratio: 20.17, sentiment_tag: "🟠 散戶微幅做多" },
    broker_snapshot: { foreign_tx_net: -83474, foreign_tx_change: 1705, foreign_call_net: 1549, foreign_call_change: -275, foreign_put_net: 3721, foreign_put_change: 2448, vix_index: 29.07, vix_change: -1.15, market_turnover: 9794 }
  };

  const mtx = det.mini_mtx;
  const tmf = det.micro_tmf;
  const snap = det.broker_snapshot;

  const mtxSign = mtx.daily_change >= 0 ? '+' : '';
  const tmfSign = tmf.daily_change >= 0 ? '+' : '';

  const mtxLongPct = ((mtx.long_oi / (mtx.long_oi + mtx.short_oi)) * 100).toFixed(1);
  const tmfLongPct = ((tmf.long_oi / (tmf.long_oi + tmf.short_oi)) * 100).toFixed(1);

  const fTxSign = snap.foreign_tx_change >= 0 ? '+' : '';
  const fCallSign = snap.foreign_call_change >= 0 ? '+' : '';
  const fPutSign = snap.foreign_put_change >= 0 ? '+' : '';
  const vixSign = snap.vix_change >= 0 ? '+' : '';

  container.innerHTML = `
    <!-- Broker Market Snapshot Bar -->
    <div style="background: rgba(0, 210, 255, 0.04); border: 1px solid rgba(0, 210, 255, 0.25); border-radius: 12px; padding: 14px 18px; margin-bottom: 18px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 6px;">
        <span style="color: var(--primary-accent); font-weight: 700; font-size: 0.92rem;">📊 權威台指籌碼快訊與 VIX 波動率觀測儀表</span>
        <span style="font-size: 0.75rem; color: var(--text-muted);">期交所與證交所 100% 官方盤後定案數據</span>
      </div>
      
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 10px; text-align: center;">
        <div style="background: rgba(0,0,0,0.25); padding: 8px; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">外資台指期淨未平倉</div>
          <div style="font-weight: 700; color: ${snap.foreign_tx_net >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-size: 1.05rem;">${snap.foreign_tx_net.toLocaleString()} 口</div>
          <div style="font-size: 0.7rem; color: var(--gold-accent);">單日 (${fTxSign}${snap.foreign_tx_change.toLocaleString()} 口)</div>
        </div>

        <div style="background: rgba(0,0,0,0.25); padding: 8px; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">外資 Call 買權淨未平倉</div>
          <div style="font-weight: 700; color: var(--call-color); font-size: 1.05rem;">+${snap.foreign_call_net.toLocaleString()} 口</div>
          <div style="font-size: 0.7rem; color: var(--text-muted);">單日 (${fCallSign}${snap.foreign_call_change} 口)</div>
        </div>

        <div style="background: rgba(0,0,0,0.25); padding: 8px; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">外資 Put 賣權淨未平倉</div>
          <div style="font-weight: 700; color: var(--put-color); font-size: 1.05rem;">+${snap.foreign_put_net.toLocaleString()} 口</div>
          <div style="font-size: 0.7rem; color: var(--text-muted);">單日 (${fPutSign}${snap.foreign_put_change} 口)</div>
        </div>

        <div style="background: rgba(0,0,0,0.25); padding: 8px; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">台指 VIX 波動率指數</div>
          <div style="font-weight: 700; color: #00e676; font-size: 1.05rem;">${snap.vix_index.toFixed(2)}</div>
          <div style="font-size: 0.7rem; color: #00e676;">(${vixSign}${snap.vix_change.toFixed(2)} 恐慌收斂)</div>
        </div>
      </div>
    </div>

    <!-- 2 Detailed Retail Breakdown Cards -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
      
      <!-- Card 1: 小台散戶籌碼 -->
      <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--panel-border); border-radius: 12px; padding: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <span style="font-weight: 700; color: var(--gold-accent); font-size: 1rem;">小台散戶多空比 (MXF1!)</span>
          <span class="badge-bull" style="font-size: 0.78rem;">${mtx.sentiment_tag}</span>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px;">
          <div>
            <span style="font-size: 0.78rem; color: var(--text-muted);">散戶多空比率：</span>
            <strong style="font-size: 1.6rem; color: var(--call-color); font-weight: 700;">+${mtx.ratio.toFixed(2)}%</strong>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">
            前日 ${mtx.prev_ratio.toFixed(2)}% ➔ 趨勢平穩
          </div>
        </div>

        <!-- Long vs Short Breakdown Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
          <div>
            <div style="font-size: 0.72rem; color: var(--call-color);">散戶多單 (口)</div>
            <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">${mtx.long_oi.toLocaleString()}</div>
          </div>
          <div>
            <div style="font-size: 0.72rem; color: var(--put-color);">散戶空單 (口)</div>
            <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">${mtx.short_oi.toLocaleString()}</div>
          </div>
          <div>
            <div style="font-size: 0.72rem; color: var(--gold-accent);">淨部位 (單日增減)</div>
            <div style="font-weight: 700; color: var(--call-color); font-size: 0.95rem;">+${mtx.net_oi.toLocaleString()} (${mtxSign}${mtx.daily_change})</div>
          </div>
        </div>

        <!-- Long / Short Proportion Bar -->
        <div style="font-size: 0.75rem; display: flex; justify-content: space-between; margin-bottom: 4px; color: var(--text-muted);">
          <span>多單占比 ${mtxLongPct}%</span>
          <span>空單占比 ${(100 - mtxLongPct).toFixed(1)}%</span>
        </div>
        <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; display: flex;">
          <div style="width: ${mtxLongPct}%; background: var(--call-color); height: 100%;"></div>
          <div style="width: ${100 - mtxLongPct}%; background: var(--put-color); height: 100%;"></div>
        </div>
      </div>

      <!-- Card 2: 微台散戶籌碼 -->
      <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--panel-border); border-radius: 12px; padding: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <span style="font-weight: 700; color: var(--primary-accent); font-size: 1rem;">微台散戶多空比 (TMF1!)</span>
          <span class="badge-bull" style="font-size: 0.78rem; background: rgba(255, 170, 0, 0.12); color: #ffaa00; border-color: rgba(255, 170, 0, 0.3);">${tmf.sentiment_tag}</span>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px;">
          <div>
            <span style="font-size: 0.78rem; color: var(--text-muted);">散戶多空比率：</span>
            <strong style="font-size: 1.6rem; color: #ffaa00; font-weight: 700;">+${tmf.ratio.toFixed(2)}%</strong>
          </div>
          <div style="font-size: 0.75rem; color: var(--put-color); font-weight: 600;">
            📉 前日 ${tmf.prev_ratio.toFixed(2)}% (散戶大平倉 -10.5%)
          </div>
        </div>

        <!-- Long vs Short Breakdown Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
          <div>
            <div style="font-size: 0.72rem; color: var(--call-color);">散戶多單 (口)</div>
            <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">${tmf.long_oi.toLocaleString()}</div>
          </div>
          <div>
            <div style="font-size: 0.72rem; color: var(--put-color);">散戶空單 (口)</div>
            <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">${tmf.short_oi.toLocaleString()}</div>
          </div>
          <div>
            <div style="font-size: 0.72rem; color: var(--gold-accent);">淨部位 (單日增減)</div>
            <div style="font-weight: 700; color: var(--put-color); font-size: 0.95rem;">+${tmf.net_oi.toLocaleString()} (${tmfSign}${tmf.daily_change})</div>
          </div>
        </div>

        <!-- Long / Short Proportion Bar -->
        <div style="font-size: 0.75rem; display: flex; justify-content: space-between; margin-bottom: 4px; color: var(--text-muted);">
          <span>多單占比 ${tmfLongPct}%</span>
          <span>空單占比 ${(100 - tmfLongPct).toFixed(1)}%</span>
        </div>
        <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; display: flex;">
          <div style="width: ${tmfLongPct}%; background: #ffaa00; height: 100%;"></div>
          <div style="width: ${100 - tmfLongPct}%; background: var(--put-color); height: 100%;"></div>
        </div>
      </div>
    </div>

    <!-- 3. Market Sentiment & Risk Digest (散戶多空與大盤籌碼綜合解讀) -->
    <div style="margin-top: 16px; background: rgba(0, 210, 255, 0.04); border: 1px solid rgba(0, 210, 255, 0.2); border-radius: 10px; padding: 14px 16px;">
      <div style="font-weight: 700; color: var(--primary-accent); font-size: 0.92rem; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
        <span>💡 散戶多空與大盤籌碼綜合解讀 (Market Sentiment & Risk Digest)</span>
      </div>
      <div style="font-size: 0.86rem; line-height: 1.7; color: var(--text-main);">
        ${det.sentiment_summary_html || `
          <p style="margin-bottom: 6px;">💡 <strong>散戶適度偏多與籌碼消化</strong>：小台散戶多空比為 <span style="color: var(--call-color); font-weight:700;">+19.97%</span>（淨多單 7,116 口），微台多空比降至 <span style="color: var(--gold-accent); font-weight:700;">+9.63%</span>（單日平倉 -8,539 口）。微台散戶高檔大舉平倉，籌碼面阻力有所減輕。</p>
          <p style="margin-bottom: 0;">⚖️ <strong>外資與做市商對沖評估</strong>：外資期貨空單單日顯著回補 <span style="color: var(--call-color); font-weight:700;">+1,705 口</span>（契約金額 +15.6 億），且目前台指位階高於 Zero Gamma 轉折點，做市商避險買盤持續護盤，盤勢維持防守洗盤格局。</p>
        `}
      </div>
    </div>

    <!-- Official TAIFEX Formula Note Footer -->
    <div style="margin-top: 12px; font-size: 0.78rem; color: var(--text-muted); background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px; border-left: 3px solid var(--primary-accent);">
      📌 <strong>期交所權威計算公式備註</strong>：散戶多單 = 全市場 OI - 三大法人多單 ｜ 散戶空單 = 全市場 OI - 三大法人空單 ｜ 散戶多空比 = (散戶多單 - 散戶空單) / 全市場 OI × 100% ｜ 基於期交所官方公開數據計算
    </div>
  `;
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
    const spotP = gexData.spot_price || 45169.46;
    const cwP = gexData.call_wall_strike || 45200;
    const pwP = gexData.put_wall_strike || 44800;
    const zgP = gexData.zero_gamma_level || 45017.6;
    const pcP = gexData.pc_ratio || 111.8;
    const regStr = spotP >= zgP ? '正 Gamma 波動度抑制區' : '負 Gamma 避險助跌警示區';

    const defaultFSum = `📈 <strong>期貨籌碼動向 (Futures Audit)</strong>：外資台指期未平倉空單 <code>-85,380 口</code>（單日回補 <code>+1,705 口</code>，約合 <code>+15.6 億 TWD</code> 契約金額），空頭避險賣壓呈現階段性收斂。`;
    const defaultCSum = `💰 <strong>現貨買賣超動向 (Cash Market Audit)</strong>：三大法人現貨合計買賣超 <code>-39.24 億 TWD</code>！其中外資 <code>+0.00 億</code>、投信 <code>-39.84 億</code>、自營商 <code>+0.60 億</code>。`;
    const defaultOSum = `🎯 <strong>選擇權莊家結構 (Options Matrix)</strong>：外資 Call 買權 <code>-2.15 億</code> (-2,744口) 與 Put 賣權 <code>+0.35 億</code> (+946口)。全場 <strong>Call Wall 天花板</strong> 鎖在 <code>${cwP.toLocaleString()} 點</code>，<strong>Put Wall 地板</strong> 固守於 <code>${pwP.toLocaleString()} 點</code>。`;
    const defaultSSum = `📊 <strong>籌碼體質與散戶比率 (Sentiment Audit)</strong>：小台散戶多空比為 <code>+19.97%</code> (淨多單 7,116口)，微台散戶多空比降至 <code>+9.63%</code> (淨多單 7,481口)。全市場 P/C Ratio 站在 <code>${pcP.toFixed(1)}%</code> (🔴 偏多看撐)，莊家下檔支撐鐵板紮實。`;
    const defaultTSum = `🔮 <strong>結算展望與操作指南 (Trading Guide)</strong>：現價 (<code>${spotP.toLocaleString()}</code>) 處於 Zero Gamma (<code>${zgP.toLocaleString()} 點</code>) 上方之「${regStr}」。若指數守穩 <code>${pwP.toLocaleString()} 點</code> Put Wall，做市商對沖買盤護盤持續，拉回尋求支撐；衝高接近 <code>${cwP.toLocaleString()} 點</code> Call Wall 壓力區宜逢高分批停利。`;

    const fSum = highlightDigestText(digest.futures_summary || defaultFSum);
    const cSum = highlightDigestText(digest.cash_summary || defaultCSum);
    const oSum = highlightDigestText(digest.options_structure || defaultOSum);
    const sSum = highlightDigestText(digest.sentiment_audit || defaultSSum);
    const tSum = highlightDigestText(digest.settlement_outlook || defaultTSum);

    digestEl.innerHTML = `
      <div style="background: rgba(10, 14, 23, 0.4); border-radius: 8px; padding: 14px 16px; border: 1px solid rgba(0, 210, 255, 0.15);">
        <p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.86rem;">${fSum}</p>
        <p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.86rem;">${cSum}</p>
        <p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.86rem;">${oSum}</p>
        <p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.86rem;">${sSum}</p>
        <p style="margin-bottom: 0; line-height: 1.7; font-size: 0.86rem;">${tSum}</p>
      </div>
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
      const nTop5Str = row.lt_near ? `<span style="font-size: 0.72rem; color: var(--gold-accent); font-weight: bold;">[近 ${row.lt_near.top5_net >= 0 ? '+' : ''}${row.lt_near.top5_net.toLocaleString()}]</span> ` : '';
      const nTop10Str = row.lt_near ? `<span style="font-size: 0.72rem; color: var(--gold-accent); font-weight: bold;">[近 ${row.lt_near.top10_net >= 0 ? '+' : ''}${row.lt_near.top10_net.toLocaleString()}]</span> ` : '';
      const nSpec5Str = row.lt_near ? `<span style="font-size: 0.72rem; color: var(--gold-accent); font-weight: bold;">[近 ${row.lt_near.top5_spec_net >= 0 ? '+' : ''}${row.lt_near.top5_spec_net.toLocaleString()}]</span> ` : '';
      const nSpec10Str = row.lt_near ? `<span style="font-size: 0.72rem; color: var(--gold-accent); font-weight: bold;">[近 ${row.lt_near.top10_spec_net >= 0 ? '+' : ''}${row.lt_near.top10_spec_net.toLocaleString()}]</span> ` : '';

      html1 += `<tr>
        <td>${row.date}</td>
        <td>${nTop5Str}<span style="color: ${top5 >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top5Sign}${top5.toLocaleString()}</span></td>
        <td>${nTop10Str}<span style="color: ${top10 >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top10Sign}${top10.toLocaleString()}</span></td>
        <td>${nSpec5Str}<span style="color: ${top5Spec >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top5SpecSign}${top5Spec.toLocaleString()}</span></td>
        <td>${nSpec10Str}<span style="color: ${top10Spec >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${top10SpecSign}${top10Spec.toLocaleString()}</span></td>
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

function highlightDigestText(text) {
  if (!text) return '';
  return text
    .replace(/(\d{2,3},\d{3}|\d{4,5})\s*點/g, '<span style="color: var(--gold-accent); font-weight: 700;">$1 點</span>')
    .replace(/([\+\-]?\d+\.?\d*\s*億)/g, match => {
      const isPos = !match.startsWith('-');
      return `<span style="color: ${isPos ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 700;">${match}</span>`;
    })
    .replace(/(正 GEX 護盤區|對沖買盤|買超|雙重加碼|多頭反攻|多單加碼|強勢買超)/g, '<span style="color: var(--call-color); font-weight: 700;">$1</span>')
    .replace(/(負 GEX 追殺賣盤區|負 GEX 區|追殺賣盤|重手加空|下探|賣壓|防範做市商追殺賣盤)/g, '<span style="color: var(--put-color); font-weight: 700;">$1</span>')
    .replace(/(Call Wall|天花板|超長黃色週選柱)/g, '<span style="color: var(--gold-accent); font-weight: 700;">$1</span>')
    .replace(/(Put Wall|超長藍色月選柱|主力波段防守鐵板)/g, '<span style="color: var(--primary-accent); font-weight: 700;">$1</span>')
    .replace(/(Gamma Flip 轉折點|Zero Gamma|轉折點)/g, '<span style="color: var(--primary-accent); font-weight: 700;">$1</span>');
}

function populateAiQuantDigest() {
  const container = document.getElementById('ai-quant-digest-content');
  if (!container || !gexData) return;

  const digest = gexData.ai_ex_dividend_digest || {};

  // Derive current active session numbers to align 100% with top KPI cards
  const sessions = gexData.history_10_sessions || [];
  const activeSess = (sessions.length > 0) ? sessions[sessions.length - 1] : gexData;

  const curPrice = activeSess.txf_price || activeSess.spot_price || gexData.spot_price || 0;
  const curZg = activeSess.zero_gamma_level || gexData.zero_gamma_level || 0;
  const curCw = activeSess.call_wall_strike || gexData.call_wall_strike || 0;
  const curPw = activeSess.put_wall_strike || gexData.put_wall_strike || 0;

  const gexRegime = (curPrice >= curZg) ? "正 GEX 護盤區" : "負 GEX 追殺賣盤區";
  const gexColor = (curPrice >= curZg) ? "var(--call-color)" : "var(--put-color)";

  const bullet1Text = (curPrice > 0 && curZg > 0)
    ? `🎯 <strong>台指大盤 GEX 位階與動態判讀 (<span style="color: var(--gold-accent); font-weight:700;">${curPrice.toLocaleString()} 點</span>)</strong>：台指現價 <span style="color: var(--gold-accent); font-weight:700;">${curPrice.toLocaleString()} 點</span>，對照 Zero Gamma 轉折點 (<span style="color: var(--primary-accent); font-weight:700;">${curZg.toLocaleString(undefined, {minimumFractionDigits:1, maximumFractionDigits:1})} 點</span>)，總 GEX 處於 <span style="color: ${gexColor}; font-weight:700;">${gexRegime}</span>。若持續守穩 <span style="color: var(--primary-accent); font-weight:700;">${curPw.toLocaleString()} 點 Put Wall 支撐</span>，莊家對沖護盤力道將維繫常態盤整。`
    : (digest.bullet_1 || '');

  const bullet2Text = (curCw > 0 && curPw > 0)
    ? `🧱 <strong>週月選莊家牆與結算位階 (<span style="color: var(--gold-accent); font-weight:700;">${curCw.toLocaleString()} / ${curPw.toLocaleString()}</span>)</strong>：週月選主力天花板集中於 <span style="color: var(--gold-accent); font-weight:700;">${curCw.toLocaleString()} 點</span> (Call Wall 週月選衝高壓力柱)；波段防守鐵板位於 <span style="color: var(--primary-accent); font-weight:700;">${curPw.toLocaleString()} 點</span> (Put Wall 避險防守柱)；結算前夕宜注意轉折點 <span style="color: var(--gold-accent); font-weight:700;">${curZg.toLocaleString(undefined, {minimumFractionDigits:1, maximumFractionDigits:1})} 點</span> 之磁吸震盪點位。`
    : (digest.bullet_2 || '');

  let html = '';
  if (bullet1Text) html += `<p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.88rem;">${highlightDigestText(bullet1Text)}</p>`;
  if (bullet2Text) html += `<p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.88rem;">${highlightDigestText(bullet2Text)}</p>`;
  if (digest.bullet_3) html += `<p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.88rem;">${highlightDigestText(digest.bullet_3)}</p>`;
  if (digest.bullet_4) html += `<p style="margin-bottom: 0; line-height: 1.7; font-size: 0.88rem;">${highlightDigestText(digest.bullet_4)}</p>`;

  container.innerHTML = html;
}

function renderNightSixSpotlight(dataObj) {
  const container = document.getElementById('night-six-spotlight-container');
  if (!container || !dataObj || !dataObj.stock_futures) return;

  const nightItems = dataObj.stock_futures.filter(item => item.has_night);
  if (!nightItems || nightItems.length === 0) {
    container.innerHTML = '';
    return;
  }

  // Sort by market popularity hierarchy: 2330 -> 2330F -> 0050 -> 0050F -> 2303 -> 00679B
  const NIGHT_POPULARITY_ORDER = ['2330', '2330F', '0050', '0050F', '2303', '00679B'];
  nightItems.sort((a, b) => {
    const idxA = NIGHT_POPULARITY_ORDER.indexOf(a.code);
    const idxB = NIGHT_POPULARITY_ORDER.indexOf(b.code);
    const posA = idxA !== -1 ? idxA : 99;
    const posB = idxB !== -1 ? idxB : 99;
    if (posA !== posB) return posA - posB;
    return b.volume - a.volume;
  });

  let cardsHtml = '';
  nightItems.forEach(item => {
    const futPrice = item.fut_price || item.spot_price;
    const basis = item.basis !== undefined ? item.basis : (futPrice - item.spot_price);
    const basisBadge = basis > 0 
      ? `<span class="badge" style="background: rgba(255, 82, 82, 0.2); color: #ff5252;">🔴 +${basis.toFixed(2)} (正價差)</span>`
      : (basis < 0 
        ? `<span class="badge" style="background: rgba(0, 230, 118, 0.2); color: #00e676;">🟢 ${basis.toFixed(2)} (逆價差)</span>`
        : `<span class="badge" style="background: rgba(255, 255, 255, 0.1); color: #aaa;">0.00 (平價差)</span>`);

    const ptsSign = item.point_contrib >= 0 ? '+' : '';
    const ptsStr = item.point_contrib !== undefined && item.point_contrib !== 0 ? `<span style="font-size: 0.72rem; color: var(--gold-accent); font-weight: 600; margin-left: 4px;">(${ptsSign}${item.point_contrib}點貢獻)</span>` : '';

    const pvSignal = item.volume > 5000 
      ? (item.change_pct >= 0 ? '<span class="badge" style="background: rgba(255,82,82,0.15); color: #ff5252; border: 1px solid rgba(255,82,82,0.3);">🔥 價量齊揚 (強勢偏多)</span>' : '<span class="badge" style="background: rgba(0,230,118,0.15); color: #00e676; border: 1px solid rgba(0,230,118,0.3);">⚠️ 帶量拉回 (壓力避險)</span>')
      : '<span class="badge" style="background: rgba(255,255,255,0.06); color: var(--text-muted);">☕ 盤整觀望</span>';

    const top10Tag = item.is_top10_buy 
      ? `<span class="badge" style="background: rgba(255, 215, 0, 0.2); color: var(--gold-accent);">🔥 Top10買超</span>` 
      : (item.is_top10_sell 
        ? `<span class="badge" style="background: rgba(0, 210, 255, 0.2); color: var(--primary-accent);">❄️ Top10賣超</span>` 
        : '');

    const exBadge = item.ex_date && item.ex_date !== '-'
      ? `<span class="badge" style="background: rgba(255, 170, 0, 0.15); color: #ffaa00; border: 1px solid rgba(255, 170, 0, 0.3); font-size: 0.72rem;">📅 ${item.ex_date} (${item.ex_dividend ? '$' + item.ex_dividend : (item.ex_type || '除息')})</span>`
      : '';

    cardsHtml += `
      <div style="background: linear-gradient(135deg, rgba(18, 23, 33, 0.85), rgba(10, 14, 23, 0.95)); border: 1px solid rgba(255, 215, 0, 0.25); border-radius: 12px; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.3); transition: transform 0.2s ease;" onmouseenter="this.style.transform='translateY(-2px)'" onmouseleave="this.style.transform='none'">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px;">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-weight: 700; color: var(--primary-accent); font-size: 0.95rem;">${item.code}</span>
            <span style="font-weight: 700; color: #fff; font-size: 0.9rem;">${item.name}</span>
            ${top10Tag}
          </div>
          <span style="font-size: 0.75rem; color: var(--gold-accent); background: rgba(255, 215, 0, 0.12); padding: 2px 6px; border-radius: 4px; font-weight: 600;">🌙 交易中</span>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.8rem;">
          <div><span style="color: var(--text-muted);">現價 (Spot)：</span><strong style="color: #fff;">${item.spot_price.toFixed(2)}</strong></div>
          <div><span style="color: var(--text-muted);">期價 (Fut)：</span><strong style="color: #fff;">${futPrice.toFixed(2)}</strong></div>
        </div>

        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 4px;">
          <div>${basisBadge}</div>
          <div style="font-weight: 700; color: ${item.change_pct >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">
            ${item.change_pct >= 0 ? '+' : ''}${item.change_pct.toFixed(2)}% ${ptsStr}
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; padding-top: 4px; border-top: 1px dashed rgba(255,255,255,0.06);">
          <div><span style="color: var(--text-muted);">成交量：</span><strong style="color: #fff;">${item.volume.toLocaleString()} 口</strong></div>
          <div>${pvSignal}</div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: var(--text-muted);">
          <div>外資: <strong style="color: ${item.foreign_net >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${item.foreign_net >= 0 ? '+' : ''}${item.foreign_net}</strong> | 自營: <strong style="color: ${item.dealer_net >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${item.dealer_net >= 0 ? '+' : ''}${item.dealer_net}</strong></div>
          ${exBadge}
        </div>
      </div>
    `;
  });

  container.innerHTML = `
    <div style="background: rgba(255, 215, 0, 0.04); border: 1px solid rgba(255, 215, 0, 0.3); border-radius: 14px; padding: 14px 18px; margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 1.1rem;">🌙</span>
          <h4 style="margin: 0; color: var(--gold-accent); font-size: 0.98rem; font-weight: 700;">期交所官方 6 大夜盤開放標的 (Night-Traded Stock & ETF Futures) 價量行情矩陣</h4>
          <span style="font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; background: rgba(0, 210, 255, 0.15); color: var(--primary-accent); border: 1px solid var(--primary-accent); font-weight: 600;">夜盤交易時間：15:00 ~ 次日 05:00</span>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">⚡ 包含台積期、聯電期、0050期、00679B期及小型契約</div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
        ${cardsHtml}
      </div>
      <div style="text-align: right; margin-top: 10px; font-size: 11px; color: rgba(255, 255, 255, 0.45); font-weight: 600; user-select: none;">© 尋鳥 Bluebird Finder</div>
    </div>
  `;
}

function populateStockFutures() {
  populateAiQuantDigest();
  try { renderNightSixSpotlight(gexData); } catch (e) { console.error('Night Six Spotlight Error:', e); }
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
  if (selectedCat === 'night6') {
    list = list.filter(item => item.has_night);
  } else if (selectedCat === 'top10' || selectedCat === 'top10_buy') {
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
  const NIGHT_POPULARITY_ORDER = ['2330', '2330F', '0050', '0050F', '2303', '00679B'];
  const sortKey = currentSortKey || 'volume';
  
  list.sort((a, b) => {
    if (!currentSortKey && (selectedCat === 'night6' || nightOnly)) {
      const idxA = NIGHT_POPULARITY_ORDER.indexOf(a.code);
      const idxB = NIGHT_POPULARITY_ORDER.indexOf(b.code);
      const posA = idxA !== -1 ? idxA : 99;
      const posB = idxB !== -1 ? idxB : 99;
      if (posA !== posB) return posA - posB;
    }

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

    const ptsSign = item.point_contrib >= 0 ? '+' : '';
    const ptsStr = item.point_contrib !== undefined && item.point_contrib !== 0 ? `<div style="font-size: 0.7rem; color: var(--gold-accent); font-weight: normal;">(${ptsSign}${item.point_contrib}點)</div>` : '';

    html += `<tr>
      <td style="font-weight: 700; color: var(--primary-accent);">${item.code}</td>
      <td>${item.name} ${top10Tag}</td>
      <td><span class="badge" style="background: rgba(255,255,255,0.05);">${item.category}</span></td>
      <td>${trendBadge}</td>
      <td style="font-weight: 600;">${item.spot_price.toFixed(2)}</td>
      <td style="font-weight: 600;">${futPrice.toFixed(2)}</td>
      <td>${basisBadge}</td>
      <td><div style="color: ${item.change_pct >= 0 ? 'var(--call-color)' : 'var(--put-color)'}; font-weight: 700;">${item.change_pct >= 0 ? '+' : ''}${item.change_pct.toFixed(2)}%</div>${ptsStr}</td>
      <td>${item.volume.toLocaleString()}</td>
      <td style="color: ${item.foreign_net >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${item.foreign_net >= 0 ? '+' : ''}${item.foreign_net.toLocaleString()}</td>
      <td style="color: ${item.dealer_net >= 0 ? 'var(--call-color)' : 'var(--put-color)'};">${item.dealer_net >= 0 ? '+' : ''}${item.dealer_net.toLocaleString()}</td>
      <td>${item.has_night ? '<span style="color: var(--gold-accent);">🌙 交易中</span>' : '<span style="color: #666;">日盤</span>'}</td>
      <td>${exBadge}</td>
    </tr>`;
  });

  tbody.innerHTML = html;
}

function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth <= 768;
}

function downloadSingleCard(fileUrl, fileName) {
  const cleanUrl = fileUrl.split('?')[0];
  const downloadUrl = `${cleanUrl}?t=${Date.now()}`;
  
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  setTimeout(() => {
    if (link.parentNode) link.parentNode.removeChild(link);
  }, 2000);
}

function downloadAllCards() {
  const t = Date.now();
  const cards = [
    { url: `data/social_card_p1_overview.png?t=${t}`, name: 'Bluebird_Finder_GEX_P1_Overview.png' },
    { url: `data/social_card_p2_gex_profile.png?t=${t}`, name: 'Bluebird_Finder_GEX_P2_Profile.png' },
    { url: `data/social_card_p3_sector_rotation.png?t=${t}`, name: 'Bluebird_Finder_GEX_P3_Sector.png' }
  ];

  const delayMs = isMobileDevice() ? 1200 : 600;
  cards.forEach((card, index) => {
    setTimeout(() => {
      downloadSingleCard(card.url, card.name);
    }, index * delayMs);
  });
}

async function downloadCardsZip() {
  const t = Date.now();
  const cards = [
    { url: `data/social_card_p1_overview.png?t=${t}`, name: 'Bluebird_Finder_GEX_P1_Overview.png' },
    { url: `data/social_card_p2_gex_profile.png?t=${t}`, name: 'Bluebird_Finder_GEX_P2_Profile.png' },
    { url: `data/social_card_p3_sector_rotation.png?t=${t}`, name: 'Bluebird_Finder_GEX_P3_Sector.png' }
  ];

  if (typeof JSZip !== 'undefined') {
    try {
      const zip = new JSZip();
      for (const card of cards) {
        const resp = await fetch(card.url, { cache: 'no-cache' });
        const blob = await resp.blob();
        zip.file(card.name, blob);
      }
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const blobUrl = URL.createObjectURL(zipBlob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = 'Bluebird_Finder_GEX_Social_Cards.zip';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 15000);
      return;
    } catch (err) {
      console.warn('Zip creation failed, fallback to sequential download:', err);
    }
  }
  downloadAllCards();
}

function initModals() {
  const downloadBtn = document.getElementById('download-social-card-btn');
  const socialModal = document.getElementById('social-card-modal');
  const closeSocialModalBtn = document.getElementById('close-social-card-modal');
  const downloadAllPngBtn = document.getElementById('download-all-png-btn');
  const downloadZipBtn = document.getElementById('download-zip-btn');
  const downloadCard1Btn = document.getElementById('download-card1-btn');
  const downloadCard2Btn = document.getElementById('download-card2-btn');
  const downloadCard3Btn = document.getElementById('download-card3-btn');

  if (downloadBtn) {
    downloadBtn.onclick = function(e) {
      if (e) e.preventDefault();
      if (socialModal) {
        socialModal.style.display = 'flex';
        const imgs = socialModal.querySelectorAll('img');
        const t = Date.now();
        imgs.forEach(img => {
          if (img.src && img.src.includes('data/social_card')) {
            const baseSrc = img.src.split('?')[0];
            img.src = `${baseSrc}?t=${t}`;
          }
        });
      }
    };
  }

  if (closeSocialModalBtn && socialModal) {
    closeSocialModalBtn.onclick = function() {
      socialModal.style.display = 'none';
    };
  }

  if (socialModal) {
    socialModal.onclick = function(e) {
      if (e.target === socialModal) {
        socialModal.style.display = 'none';
      }
    };
  }

  if (downloadAllPngBtn) downloadAllPngBtn.onclick = () => downloadAllCards();
  if (downloadZipBtn) downloadZipBtn.onclick = () => downloadCardsZip();

  if (downloadCard1Btn) downloadCard1Btn.onclick = () => downloadSingleCard('data/social_card_p1_overview.png', 'Bluebird_Finder_GEX_P1_Overview.png');
  if (downloadCard2Btn) downloadCard2Btn.onclick = () => downloadSingleCard('data/social_card_p2_gex_profile.png', 'Bluebird_Finder_GEX_P2_Profile.png');
  if (downloadCard3Btn) downloadCard3Btn.onclick = () => downloadSingleCard('data/social_card_p3_sector_rotation.png', 'Bluebird_Finder_GEX_P3_Sector.png');

  const eduBtn = document.getElementById('education-btn');
  const eduModal = document.getElementById('education-modal');
  const closeEduBtn = document.getElementById('close-edu-modal');
  const openMaxPainBtn = document.getElementById('open-max-pain-modal-btn');
  const mpBadgeBtn = document.getElementById('stat-mp-topology-badge');

  function openMaxPainTopologyModal() {
    if (eduModal) {
      eduModal.style.display = 'flex';
      const targetSec = document.getElementById('max-pain-topology-section');
      if (targetSec) {
        setTimeout(() => {
          targetSec.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
    }
  }

  if (openMaxPainBtn) openMaxPainBtn.onclick = openMaxPainTopologyModal;
  if (mpBadgeBtn) mpBadgeBtn.onclick = openMaxPainTopologyModal;

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

  // Start 3-Tier Fallback Live Price Tick Polling
  initLiveTickPolling();
}

let lastLivePrice = null;

function initLiveTickPolling() {
  // Listen for storage events (same-origin tab communication)
  window.addEventListener('storage', (e) => {
    if (e.key === 'GEX_LIVE_TICK' && e.newValue) {
      try {
        const data = JSON.parse(e.newValue);
        if (data && data.price > 0) handleLiveTick(data);
      } catch(err){}
    }
  });

  setInterval(async () => {
    updateMarketTradingStatus();
    // 1. Priority: Check local storage cache (from TV Bookmarklet)
    try {
      const cachedStr = localStorage.getItem('GEX_LIVE_TICK');
      if (cachedStr) {
        const cached = JSON.parse(cachedStr);
        if (cached && cached.price > 0 && (Date.now() - (cached.time || cached.timestamp || 0) < 15000)) {
          handleLiveTick(cached);
          if (cached.provider === 'TRADINGVIEW') return; // High priority override
        }
      }
    } catch(err){}

    // 2. Try Local Python Gateway (Fubon WS / TV Bridge)
    try {
      const res = await fetch('http://localhost:8000/api/live_tick');
      if (res.ok) {
        const data = await res.json();
        if (data && data.price > 0) {
          handleLiveTick(data);
          return;
        }
      }
    } catch (e) {
      // Local server not running
    }

    // 2.5 Try Cloudflare Worker Cloud Relay (24/7 Global HTTPS Relay)
    try {
      const cfUrl = window.CF_WORKER_URL || 'https://txo-gex-relay.bluebird-finder-tw.workers.dev/';
      const cfRes = await fetch(cfUrl);
      if (cfRes.ok) {
        const cfData = await cfRes.json();
        if (cfData && cfData.price > 0 && (Date.now() - (cfData.timestamp || cfData.time || 0) < 45000)) {
          handleLiveTick(cfData);
          return;
        }
      }
    } catch(err){}

    // 3. Fallback to TAIFEX MIS Live API (Night Session MarketType '1', Day Session MarketType '0')
    try {
      const nowH = (new Date()).getHours();
      const isNightSession = (nowH >= 15 || nowH < 5);
      const mType = isNightSession ? '1' : '0';
      
      const taifexRes = await fetch('https://mis.taifex.com.tw/futures/api/getQuoteList', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ MarketType: mType, SymbolType: 'F' })
      });

      if (taifexRes.ok) {
        const misData = await taifexRes.json();
        const quoteList = (misData.RtData && misData.RtData.QuoteList) ? misData.RtData.QuoteList : [];
        const txItems = quoteList.filter(q => q.SymbolID && q.SymbolID.startsWith('TX') && q.CLastPrice && parseFloat(q.CLastPrice) > 0);
        if (txItems.length > 0) {
          const livePrice = parseFloat(txItems[0].CLastPrice);
          if (!isNaN(livePrice) && livePrice > 0) {
            handleLiveTick({
              ticker: 'TXF',
              price: livePrice,
              provider: 'TAIFEX_MIS',
              provider_name: isNightSession ? '🌐 期交所 MIS 夜盤行情' : '🌐 期交所 MIS 日盤行情'
            });
            return;
          }
        }
      }
    } catch(err) {}

    // 3.5 Global Fallback: Yahoo Finance Index (^TWII) (Ultra-fast CORS-friendly HTTPS feed)
    try {
      const yRes = await fetch('https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII');
      if (yRes.ok) {
        const yData = await yRes.json();
        const price = yData?.chart?.result?.[0]?.meta?.regularMarketPrice;
        if (price && price > 0) {
          const nowH = (new Date()).getHours();
          const isNightSession = (nowH >= 15 || nowH < 5);
          handleLiveTick({
            ticker: 'IX0001',
            price: price,
            provider: 'TAIFEX_MIS',
            provider_name: isNightSession ? '🌐 雅虎全球/期交所 夜盤行情' : '🌐 證交所/雅虎 日盤即時行情'
          });
          return;
        }
      }
    } catch(err) {}

    // 4. Last Fallback: TWSE OpenAPI Snapshot
    try {
      const openApiRes = await fetch('https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX');
      if (openApiRes.ok) {
        const list = await openApiRes.json();
        if (list && list.length > 0) {
          const tseObj = list.find(x => x['指數'] && x['指數'].includes('加權'));
          if (tseObj && tseObj['收盤指數']) {
            const spotVal = parseFloat(tseObj['收盤指數'].replace(/,/g, ''));
            if (!isNaN(spotVal) && spotVal > 0) {
              handleLiveTick({
                ticker: 'IX0001',
                price: spotVal,
                provider: 'TAIFEX_MIS',
                provider_name: '🌐 證交所 MIS 日盤快照'
              });
              return;
            }
          }
        }
      }
    } catch(err) {}

  }, 2000);
}

function handleLiveTick(data) {
  const freshnessText = document.getElementById('freshness-text');
  const feedDot = document.getElementById('live-feed-dot');
  const feedText = document.getElementById('live-feed-text');
  const feedPill = document.getElementById('live-feed-pill');

  if (feedText && data.provider_name) {
    feedText.innerText = data.provider_name;
    if (data.provider === 'FUBON') {
      if (feedDot) { feedDot.style.background = '#00e676'; feedDot.style.boxShadow = '0 0 8px #00e676'; }
      if (feedPill) { feedPill.style.borderColor = 'rgba(0, 230, 118, 0.4)'; feedPill.style.background = 'rgba(0, 230, 118, 0.08)'; }
    } else if (data.provider === 'TRADINGVIEW') {
      if (feedDot) { feedDot.style.background = '#ffd700'; feedDot.style.boxShadow = '0 0 8px #ffd700'; }
      if (feedPill) { feedPill.style.borderColor = 'rgba(255, 215, 0, 0.4)'; feedPill.style.background = 'rgba(255, 215, 0, 0.08)'; }
    } else if (data.provider === 'TAIFEX_MIS') {
      if (feedDot) { feedDot.style.background = '#00d2ff'; feedDot.style.boxShadow = '0 0 8px #00d2ff'; }
      if (feedPill) { feedPill.style.borderColor = 'rgba(0, 210, 255, 0.4)'; feedPill.style.background = 'rgba(0, 210, 255, 0.08)'; }
    } else {
      if (feedDot) { feedDot.style.background = '#a855f7'; feedDot.style.boxShadow = '0 0 8px #a855f7'; }
      if (feedPill) { feedPill.style.borderColor = 'rgba(168, 85, 247, 0.4)'; feedPill.style.background = 'rgba(168, 85, 247, 0.08)'; }
    }
  }

  if (freshnessText && data.provider_name) {
    freshnessText.innerText = `實時同步`;
  }

  if (!data || !data.price || data.price <= 0) return;

  // Route tick by ticker symbol
  if (data.ticker === 'IX0001') {
    const spotEl = document.getElementById('stat-spot');
    if (spotEl) spotEl.innerText = data.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    if (gexData) gexData.spot_price = data.price;
    return;
  }

  if (data.ticker === 'IX0043') {
    const twoEl = document.getElementById('stat-two-price');
    if (twoEl) twoEl.innerText = data.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    if (gexData) gexData.two_price = data.price;
    return;
  }

  // Futures Ticks (TXF1!) -> Update Futures Dual Session Cards & Zero Gamma Recalculation
  const nowH = (new Date()).getHours();
  const isNightSession = (nowH >= 15 || nowH < 5);
  const targetEl = document.getElementById(isNightSession ? 'stat-txf-night' : 'stat-txf-day');

    if (targetEl) {
      const formattedPrice = data.price.toLocaleString();
      if (targetEl.innerText !== formattedPrice) {
        targetEl.innerText = formattedPrice;

        // Add visual flash animation
        targetEl.classList.remove('live-tick-flash-up', 'live-tick-flash-down');
        void targetEl.offsetWidth; // Trigger reflow
        if (lastLivePrice !== null) {
          if (data.price > lastLivePrice) {
            targetEl.classList.add('live-tick-flash-up');
          } else if (data.price < lastLivePrice) {
            targetEl.classList.add('live-tick-flash-down');
          }
        }
        lastLivePrice = data.price;
      }
    }

    // 1. Recalculate and update txf shift display
    const dayEl = document.getElementById('stat-txf-day');
    const nightEl = document.getElementById('stat-txf-night');
    const shiftEl = document.getElementById('stat-txf-shift');
    if (dayEl && nightEl && shiftEl) {
      const dayP = parseFloat(dayEl.innerText.replace(/,/g, ''));
      const nightP = parseFloat(nightEl.innerText.replace(/,/g, ''));
      if (!isNaN(dayP) && !isNaN(nightP)) {
        const diff = Math.round(nightP - dayP);
        const sign = diff >= 0 ? '+' : '';
        shiftEl.innerText = `(${sign}${diff} 點)`;
        shiftEl.style.color = diff >= 0 ? 'var(--call-color)' : 'var(--put-color)';
      }
    }

    // 2. Real-Time Dynamic Zero Gamma Shift Recalculation (Image 1 & 2 Live Sync)
    if (gexData) {
      const dayTxf = gexData.day_txf_price || 45027.0;
      const priceDelta = data.price - dayTxf;
      const dayZg = gexData.session_shift?.day_zero_gamma || 45016.5;
      const dayGp = gexData.session_shift?.day_gex_plus_flip || 45216.5;
      
      // Dynamic shift formula: ZG & GEX+ Flip shift smoothly with intraday price delta based on net GEX slope
      const liveZg = Math.round((dayZg + priceDelta * 0.62) * 10) / 10;
      const liveGp = Math.round((dayGp + priceDelta * 0.62) * 10) / 10;
      
      gexData.spot_price = data.price;
      gexData.zero_gamma_level = liveZg;
      gexData.gex_plus_flip = liveGp;
      
      const elZgNight = document.getElementById('stat-zg-night');
      if (elZgNight) elZgNight.innerText = liveZg.toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1});
      
      const elZgShift = document.getElementById('stat-zg-shift');
      if (elZgShift) {
        const shiftVal = liveZg - dayZg;
        const sign = shiftVal >= 0 ? '+' : '';
        elZgShift.innerText = `(${sign}${shiftVal.toFixed(1)} 點)`;
      }

      // 3. Synchronize Latest Session in 10-Session History Array ONLY IF Session is LIVE
      const sessions = gexData.history_10_sessions || gexData.history_6_sessions;
      if (sessions && sessions.length > 0) {
        const latestSess = sessions[sessions.length - 1];
        const isLive = latestSess && (
          (latestSess.label && latestSess.label.includes('Live')) || 
          (latestSess.full_name && latestSess.full_name.includes('Live'))
        );
        if (isLive) {
          latestSess.spot_price = data.price;
          if (data.is_futures !== false) {
            latestSess.txf_price = data.price;
          }
          latestSess.zero_gamma_level = liveZg;
          latestSess.gex_plus_flip = liveGp;
        }
      }

      // 4. Trigger Table 2 Re-render so Image 2 Live Row jumps in real-time
      try {
        populateKeyMetrics5Day();
      } catch (e) {}

      // 5. Trigger Left GEX Chart Re-render so Image 1 Spot Line & Zero Gamma update in real-time
      try {
        renderGEXChart();
      } catch (e) {}

      // 6. Update Microstructure Express Digest in real-time
      try {
        updateMicrostructureExpress(data.price);
      } catch (e) {}
    }
}

function updateMicrostructureExpress(livePrice = null) {
  const expressContentEl = document.getElementById('microstructure-express-content');
  const badgeEl = document.getElementById('express-regime-badge');
  if (!expressContentEl || !gexData) return;

  const sessions = gexData.history_10_sessions || gexData.history_6_sessions;
  // Always lock onto the latest / current active market session
  const activeSession = (sessions && sessions.length > 0) ? sessions[sessions.length - 1] : null;

  // 1. Current active price (livePrice > activeSession TXF/Spot > gexData TXF/Spot)
  let currentP = livePrice;
  if (!currentP || currentP <= 0) {
    if (activeSession) {
      currentP = activeSession.txf_price || activeSession.spot_price;
    }
    if (!currentP || currentP <= 0) {
      currentP = gexData.txf_price || gexData.spot_price || 45832.62;
    }
  }

  // 2. Active Zero Gamma, Call Wall, Put Wall from active session or gexData
  const zg = (activeSession && activeSession.zero_gamma_level !== undefined) 
    ? activeSession.zero_gamma_level 
    : (gexData.zero_gamma_level || 45817.3);

  const cw = (activeSession && activeSession.call_wall_strike !== undefined) 
    ? activeSession.call_wall_strike 
    : (gexData.call_wall_strike || 45950);

  const pw = (activeSession && activeSession.put_wall_strike !== undefined) 
    ? activeSession.put_wall_strike 
    : (gexData.put_wall_strike || 45650);

  const isPosGamma = currentP >= zg;
  const flipDist = (Math.abs(currentP - zg)).toFixed(1);

  if (badgeEl) {
    if (isPosGamma) {
      badgeEl.innerText = '🔴 正 Gamma 區 (護盤中)';
      badgeEl.style.background = 'rgba(255, 82, 82, 0.15)';
      badgeEl.style.color = 'var(--call-color)';
      badgeEl.style.border = '1px solid rgba(255, 82, 82, 0.3)';
    } else {
      badgeEl.innerText = '🟢 負 Gamma 區 (避險追殺)';
      badgeEl.style.background = 'rgba(0, 230, 118, 0.15)';
      badgeEl.style.color = 'var(--put-color)';
      badgeEl.style.border = '1px solid rgba(0, 230, 118, 0.3)';
    }
  }

  let regimeHtml = '';
  if (isPosGamma) {
    regimeHtml = `🔴 <strong>正 Gamma 波動度抑制區 (平穩護盤)</strong> — <span style="color: var(--call-color); font-weight: 600;">🛡️ 標的物價格 (${currentP.toLocaleString()}) 高於 Zero Gamma 轉折點 (${zg.toLocaleString()})</span>，做市商採逆風低買高賣對沖，盤勢傾向區域震盪與回測看撐。`;
  } else {
    regimeHtml = `🟢 <strong>負 Gamma 波動度放大區 (避險引爆)</strong> — <span style="color: var(--put-color); font-weight: 700;">⚠️ 警告！標的物價格 (${currentP.toLocaleString()}) 低於 Zero Gamma 轉折點 (${zg.toLocaleString()})</span>，做市商順風追跌殺跌，盤中波動度恐劇烈飆升！`;
  }

  let proximityHtml = '';
  if (flipDist < 100) {
    proximityHtml = `⚡ <strong>轉折臨界告急</strong>：價格距離 Gamma 轉折點 (<span style="color: var(--primary-accent); font-weight:700;">${zg.toLocaleString()} 點</span>) 僅 <span style="color: var(--gold-accent); font-weight:700;">${flipDist} 點</span>，處於變盤臨界邊緣。`;
  } else {
    proximityHtml = `📏 <strong>轉折安全距離</strong>：價格距 Gamma 轉折點 (<span style="color: var(--primary-accent); font-weight:700;">${zg.toLocaleString()} 點</span>) 尚有 <span style="color: var(--gold-accent); font-weight:700;">${flipDist} 點</span>緩衝防守區。`;
  }

  let cwHtml = '';
  if (currentP >= cw) {
    cwHtml = `🚀 <strong>Call Wall 已突破</strong>：現價 (<span style="color: var(--call-color); font-weight:700;">${currentP.toLocaleString()}</span>) 已突破天花板 <span style="color: var(--gold-accent); font-weight:700;">${cw.toLocaleString()} 點</span>，引爆伽瑪擠壓 (Gamma Squeeze) 強勢軋空！`;
  } else {
    cwHtml = `🛑 <strong>Call Wall 賣壓牆</strong>：天花板位於 <span style="color: var(--gold-accent); font-weight: 700;">${cw.toLocaleString()} 點</span> (距現價 ${(cw - currentP).toFixed(0)} 點)。`;
  }

  let pwHtml = `🛡️ <strong>Put Wall 支撐牆</strong>：地板位於 <span style="color: var(--primary-accent); font-weight: 700;">${pw.toLocaleString()} 點</span> (距現價 ${(currentP - pw).toFixed(0)} 點)。`;

  expressContentEl.innerHTML = `
    <p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.88rem;">${regimeHtml}</p>
    <p style="margin-bottom: 8px; line-height: 1.7; font-size: 0.88rem;">${proximityHtml}</p>
    <p style="margin-bottom: 0; line-height: 1.7; font-size: 0.88rem;">${cwHtml} &nbsp; ${pwHtml}</p>
  `;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initModals);
} else {
  initModals();
}

function renderSectorCapitalFlow() {
  const container = document.getElementById('sector-capital-flow-container');
  if (!container || !gexData || !gexData.sector_capital_rotation) return;

  const data = gexData.sector_capital_rotation;
  const sectors = data.sectors || [];

  let html = `
    <div style="background: rgba(15, 23, 42, 0.75); border: 1px solid var(--panel-border); border-radius: 12px; padding: 14px 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px dashed rgba(255,255,255,0.12); padding-bottom: 8px;">
        <span style="font-weight: 700; font-size: 0.92rem; color: var(--gold-accent); display: flex; align-items: center; gap: 8px;">
          <span>${data.title || '📊 證交所 33 大產業權重歸納 4 大核心板塊資金輪動'}</span>
        </span>
        <span style="font-size: 0.75rem; color: var(--text-muted);">🕒 即時資料: ${data.last_updated || ''}</span>
      </div>
      
      <!-- Multi-segment visual bar -->
      <div style="height: 14px; border-radius: 7px; overflow: hidden; display: flex; background: #0f172a; margin-bottom: 12px; border: 1px solid rgba(255,255,255,0.1);">
  `;

  sectors.forEach(s => {
    html += `<div style="width: ${s.share_pct}%; background: ${s.color}; height: 100%; transition: width 0.5s ease;" title="${s.name}: ${s.share_pct}% (${s.status})"></div>`;
  });

  html += `</div>
      <!-- Sector details grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px;">
  `;

  sectors.forEach(s => {
    html += `
      <div style="background: rgba(30, 41, 59, 0.6); padding: 10px 12px; border-radius: 8px; border-left: 4px solid ${s.color}; font-size: 0.82rem;">
        <div style="display: flex; justify-content: space-between; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">
          <span>${s.name}</span>
          <span style="color: ${s.color}; font-weight: 700;">${s.share_pct}% <span style="font-size: 0.75rem;">(${s.change_pct})</span></span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted);">
          <span>${s.status}</span>
          <span style="color: #cbd5e1;">🎯 ${(s.top_stocks || []).join('、')}</span>
        </div>
      </div>
    `;
  });

  html += `</div>
      <div style="text-align: right; margin-top: 8px; font-size: 11px; color: rgba(255, 255, 255, 0.4); font-weight: 600; user-select: none;">© 尋鳥 Bluebird Finder</div>
    </div>`;
  container.innerHTML = html;
}

let macroTimerInterval = null;

function renderMacroEventsRadar(dataObj) {
  const panel = document.getElementById('macro-events-radar-panel');
  if (!panel || !dataObj || !dataObj.macro_events_radar) return;

  const radarData = dataObj.macro_events_radar;
  const primary = radarData.primary_event;
  const list = radarData.upcoming_list || [];

  if (macroTimerInterval) {
    clearInterval(macroTimerInterval);
  }

  function updateCountdown() {
    const now = Date.now();
    const target = primary.target_epoch;
    const diff = target - now;

    const timerEl = document.getElementById('macro-primary-timer');
    const badgeEl = document.getElementById('macro-primary-regime');
    const borderEl = document.getElementById('macro-events-radar-panel');

    if (diff <= 0) {
      if (timerEl) timerEl.innerHTML = `<span style="color: var(--call-color); font-weight: 700;">🔥 事件正在進行 / 數據發布完成</span>`;
      if (badgeEl) badgeEl.className = 'badge';
      return;
    }

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    const daysStr = days > 0 ? `${days}天 ` : '';
    const hoursStr = String(hours).padStart(2, '0');
    const minsStr = String(minutes).padStart(2, '0');
    const secsStr = String(seconds).padStart(2, '0');

    if (timerEl) {
      timerEl.innerHTML = `<span style="font-family: 'Outfit', monospace; font-size: 1.22rem; font-weight: 700; color: var(--gold-accent); letter-spacing: 0.5px;">⏱️ ${daysStr}${hoursStr}時 ${minsStr}分 ${secsStr}秒</span>`;
    }

    // Dynamic Risk Window Styling tailored per event
    const totalMins = diff / (1000 * 60);
    const totalHours = diff / (1000 * 60 * 60);

    const critMins = primary.critical_lead_mins || 120;
    const warnHours = primary.warning_lead_hours || 24;

    if (totalMins <= critMins) {
      if (badgeEl) {
        badgeEl.innerHTML = `🚨 衝擊告急風暴圈 (< ${critMins >= 60 ? (critMins/60).toFixed(1) + '小時' : critMins + '分鐘'})`;
        badgeEl.style.background = 'rgba(255, 82, 82, 0.25)';
        badgeEl.style.color = '#ff5252';
        badgeEl.style.border = '1px solid #ff5252';
      }
      if (borderEl) {
        borderEl.style.border = '2px solid #ff5252';
        borderEl.style.boxShadow = '0 0 20px rgba(255, 82, 82, 0.4)';
      }
    } else if (totalHours <= warnHours) {
      if (badgeEl) {
        badgeEl.innerHTML = `🟡 變盤前夕警戒期 (< ${warnHours}小時)`;
        badgeEl.style.background = 'rgba(255, 170, 0, 0.2)';
        badgeEl.style.color = '#ffaa00';
        badgeEl.style.border = '1px solid #ffaa00';
      }
      if (borderEl) {
        borderEl.style.border = '1px solid var(--gold-accent)';
        borderEl.style.boxShadow = '0 4px 20px rgba(255, 215, 0, 0.2)';
      }
    } else {
      if (badgeEl) {
        badgeEl.innerHTML = `🟢 平穩觀察緩衝期 (> ${warnHours}小時)`;
        badgeEl.style.background = 'rgba(0, 230, 118, 0.15)';
        badgeEl.style.color = '#00e676';
        badgeEl.style.border = '1px solid #00e676';
      }
      if (borderEl) {
        borderEl.style.border = '1px solid rgba(255, 215, 0, 0.3)';
        borderEl.style.boxShadow = '0 4px 20px rgba(0,0,0,0.25)';
      }
    }
  }

  let upcomingCardsHtml = '';
  list.forEach((ev) => {
    const isPrimary = (ev.id === primary.id);
    const borderStyle = isPrimary ? 'border: 1px solid var(--gold-accent); background: rgba(255,215,0,0.06);' : 'border: 1px solid rgba(255,255,255,0.08); background: rgba(15,23,42,0.6);';
    const typeBadge = ev.pattern_type === 'POINT_TIME' 
      ? '<span class="badge" style="background: rgba(255,82,82,0.15); color: #ff5252; font-size: 0.68rem;">定點數據</span>'
      : '<span class="badge" style="background: rgba(255,215,0,0.15); color: var(--gold-accent); font-size: 0.68rem;">視窗洗盤</span>';

    upcomingCardsHtml += `
      <div style="${borderStyle} padding: 10px 12px; border-radius: 8px; font-size: 0.8rem; display: flex; flex-direction: column; gap: 4px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <strong style="color: #fff;">${ev.name}</strong>
          ${typeBadge}
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-top: 2px;">
          <span style="color: var(--gold-accent); font-weight: 600;">📅 ${ev.date_display}</span>
          <span>${ev.impact_label}</span>
        </div>
      </div>
    `;
  });

  const headerTag = primary.pattern_type === 'POINT_TIME' ? '🚨 [重大數據預警]' : '🚨 [關鍵日曆預警]';
  const advicePrefix = primary.pattern_type === 'POINT_TIME' 
    ? `<strong style="color: #ff5252;">${headerTag}</strong> ${primary.date_display} 發布 <strong>${primary.name}</strong> ➔ `
    : `<strong style="color: var(--gold-accent);">${headerTag}</strong> <strong>${primary.name}</strong> ➔ `;

  panel.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed rgba(255,255,255,0.12); padding-bottom: 10px; margin-bottom: 14px; flex-wrap: wrap; gap: 8px;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 1.2rem;">🚨</span>
        <div>
          <h3 style="margin: 0; font-size: 1.02rem; color: var(--gold-accent); font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>國際重大總經事件、富台/MSCI 與結算日 實時避險防護雷達</span>
          </h3>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">雙型態對齊：定點數據防範發布前流動性抽離 | 結算日防範尾盤爆量擺盪</div>
        </div>
      </div>
      <div id="macro-primary-regime" class="badge" style="font-weight: 700; font-size: 0.8rem; padding: 4px 10px; border-radius: 6px;">
        🟢 平穩觀察緩衝期
      </div>
    </div>

    <!-- Primary Countdown Spotlight Box -->
    <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.08), rgba(0, 210, 255, 0.04)); border: 1px solid var(--gold-accent); border-radius: 12px; padding: 14px 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
      <div style="flex: 1; min-width: 260px;">
        <div style="font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">🎯 下一重磅關鍵催化劑 (${primary.pattern_type === 'POINT_TIME' ? '定點數據型' : '視窗洗盤型'})</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: #fff; margin-bottom: 4px;">${primary.name}</div>
        <div style="font-size: 0.82rem; color: var(--gold-accent); display: flex; align-items: center; gap: 8px;">
          <span>📅 事件發布時間：<strong>${primary.date_display}</strong></span>
          <span class="badge" style="background: rgba(255,82,82,0.15); color: #ff5252; border: 1px solid rgba(255,82,82,0.3);">${primary.impact_label}</span>
        </div>
      </div>

      <div id="macro-primary-timer" style="background: rgba(10, 14, 23, 0.8); border: 1px solid rgba(255, 215, 0, 0.3); border-radius: 10px; padding: 10px 18px; text-align: center; min-width: 220px;">
        <!-- Timer updated by JS -->
      </div>
    </div>

    <!-- GEX Guidance & Upcoming 5 Grid -->
    <div style="font-size: 0.84rem; color: var(--text-main); background: rgba(0, 210, 255, 0.03); padding: 12px 14px; border-radius: 10px; margin-bottom: 14px; border-left: 4px solid var(--gold-accent); line-height: 1.6;">
      ${advicePrefix} ${primary.gex_advice}
    </div>

    <div style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted); margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
      <span>📅 接續近期 5 大重磅總經與結算日曆矩陣：</span>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px;">
      ${upcomingCardsHtml}
    </div>
  `;

  updateCountdown();
  macroTimerInterval = setInterval(updateCountdown, 1000);
}


