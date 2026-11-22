/**
 * room_panels.js - 面板（Layout Presets）：像 TradingView 一樣存多組版面，一鍵切換。
 *
 * 一個面板記住：標的、時間框架、指標勾選與參數、副圖分頁、SMC 開關、左右欄收合。
 * 面板之間沒有「專屬標的」的限制：任何面板都可以看任何商品、掛任何指標（例如面板 2 也可以看台指期）。
 * 儲存位置只在使用者自己的瀏覽器（localStorage，不需登入；換裝置要重設），和指標顏色偏好同一做法。
 * 顏色偏好（IND_COLOR_KEYS）是全域偏好，不跟著面板走。
 *
 * 依賴 room.js 的全域變數與函式：indicatorConfig、currentTf、currentActiveSymbol、activeSub4、smcEnabled、
 * leftPanelCollapsed、rightPanelCollapsed、CORE_PRESET_ASSETS、symbolsUniverse、switchActiveSymbol、toggleSmcOverlay。
 * 必須在 room.js 之後載入。
 */
(function () {
  'use strict';

  const STORE_KEY = 'txo_room_panels_v1';
  const MAX_PANELS = 8;
  const PREF_KEYS = ['swStyle', 'swWidth'];   // 強弱關價的線型與粗細是個人偏好（和顏色一樣），不跟著面板走

  // 指標設定視窗裡「欄位 id → indicatorConfig 鍵」。套用面板後要把欄位同步成面板的值，
  // 否則下次按「儲存並立即套用」會把欄位裡的舊值寫回去。
  const MODAL_CHECKS = {
    'chk-gex': 'gex', 'chk-ribbons': 'ribbons', 'chk-demark': 'demark', 'chk-smma': 'smma',
    'chk-supertrend': 'supertrend', 'chk-vwap': 'vwap', 'chk-vrvp': 'vrvp', 'chk-sar': 'sar', 'chk-fvg': 'fvg', 'chk-sw': 'swLevels'
  };
  const MODAL_VALUES = {
    'param-smma-len': 'smmaLen', 'param-vrvp-rows': 'vrvpRows', 'param-vrvp-va': 'vrvpVa',
    'param-sar-step': 'sarStep', 'param-st-len': 'stLen', 'param-st-mult': 'stMult'
  };

  let store = null;   // { active: id, panels: [{ id, name, state }] }

  function readStore() {
    try {
      const s = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
      if (s && Array.isArray(s.panels) && s.panels.length) return s;
    } catch (e) { /* storage blocked or corrupted: fall through to seeding */ }
    return null;
  }
  function writeStore() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(store)); } catch (e) { /* ignore */ }
  }

  function captureState() {
    const ind = {};
    Object.keys(indicatorConfig).forEach(k => { if (!IND_COLOR_KEYS.includes(k) && !PREF_KEYS.includes(k)) ind[k] = indicatorConfig[k]; });
    return {
      symbol: currentActiveSymbol ? currentActiveSymbol.symbol : 'TXF',
      tf: currentTf,
      indicators: ind,
      sub4: activeSub4,
      smc: !!smcEnabled,
      leftCollapsed: !!leftPanelCollapsed,
      rightCollapsed: !!rightPanelCollapsed
    };
  }

  function findSymbolObj(code) {
    if (CORE_PRESET_ASSETS[code]) return CORE_PRESET_ASSETS[code];
    return (symbolsUniverse || []).find(s => s.symbol === code || s.futures_code === code) || null;
  }

  function syncIndicatorModal() {
    Object.keys(MODAL_CHECKS).forEach(id => {
      const el = document.getElementById(id);
      if (el) el.checked = !!indicatorConfig[MODAL_CHECKS[id]];
    });
    Object.keys(MODAL_VALUES).forEach(id => {
      const el = document.getElementById(id);
      const v = indicatorConfig[MODAL_VALUES[id]];
      if (el && v !== undefined && v !== null) el.value = v;
    });
  }

  function applyState(st) {
    if (!st) return;
    // 1) 指標設定（不含顏色）
    Object.keys(st.indicators || {}).forEach(k => {
      if (k in indicatorConfig && !IND_COLOR_KEYS.includes(k) && !PREF_KEYS.includes(k)) indicatorConfig[k] = st.indicators[k];
    });
    syncIndicatorModal();

    // 2) SMC 開關
    if (typeof smcEnabled !== 'undefined' && !!st.smc !== !!smcEnabled) toggleSmcOverlay();

    // 3) 副圖分頁
    if (st.sub4 && st.sub4 !== activeSub4) {
      const b = document.querySelector('.sub4-tab-btn[data-sub4="' + st.sub4 + '"]');
      if (b) b.click();
    }

    // 4) 左右欄收合（按鈕會自己切換狀態並重算圖表尺寸）
    if (!!st.leftCollapsed !== !!leftPanelCollapsed) { const b = document.getElementById('btn-toggle-left-panel'); if (b) b.click(); }
    if (!!st.rightCollapsed !== !!rightPanelCollapsed) { const b = document.getElementById('btn-toggle-right-panel'); if (b) b.click(); }

    // 5) 時間框架（先設，再換標的時一次重畫；不用 click 以免畫兩次）
    if (st.tf) {
      currentTf = st.tf;
      document.querySelectorAll('.btn-tf').forEach(b => b.classList.toggle('active', b.getAttribute('data-tf') === st.tf));
    }

    // 6) 標的（switchActiveSymbol 會重畫圖表；GEX 防線依標的自動開關，這是 room.js 既有規則，面板不覆蓋）
    const obj = findSymbolObj(st.symbol);
    if (obj) switchActiveSymbol(obj);
    else if (typeof renderChartData === 'function') renderChartData();
    syncIndicatorModal();   // switchActiveSymbol 會依標的改 gex，欄位要跟著
  }

  // ---------- UI ----------
  function injectStyle() {
    const css = `
      .room-panel-bar{display:flex;align-items:center;gap:4px;flex-wrap:nowrap;overflow-x:auto;max-width:100%}
      .room-panel-tab{background:rgba(255,255,255,.05);border:1px solid var(--panel-border,#2a3550);color:#aab4c8;
        padding:3px 10px;border-radius:5px;font-size:.74rem;cursor:pointer;white-space:nowrap;font-family:inherit}
      .room-panel-tab:hover{background:rgba(255,255,255,.1)}
      .room-panel-tab.active{background:rgba(255,215,0,.14);border-color:#ffd700;color:#ffd700;font-weight:700}
      .room-panel-act{background:transparent;border:1px solid var(--panel-border,#2a3550);color:#aab4c8;
        padding:3px 7px;border-radius:5px;font-size:.74rem;cursor:pointer;font-family:inherit}
      .room-panel-act:hover{color:#fff;border-color:#8aa0c8}`;
    const el = document.createElement('style');
    el.textContent = css;
    document.head.appendChild(el);
  }

  function render() {
    const bar = document.getElementById('room-panel-bar');
    if (!bar) return;
    bar.innerHTML = '';
    store.panels.forEach(p => {
      const b = document.createElement('button');
      b.className = 'room-panel-tab' + (p.id === store.active ? ' active' : '');
      b.textContent = p.name;
      b.title = '切換到「' + p.name + '」面板（雙擊改名）';
      b.addEventListener('click', () => switchPanel(p.id));
      b.addEventListener('dblclick', () => renamePanel(p.id));
      bar.appendChild(b);
    });
    const mk = (txt, title, fn) => {
      const b = document.createElement('button');
      b.className = 'room-panel-act'; b.textContent = txt; b.title = title;
      b.addEventListener('click', fn); bar.appendChild(b);
    };
    mk('💾', '把目前的標的、週期、指標、副圖與左右欄狀態存進這個面板', saveActive);
    mk('＋', '用目前狀態新增一個面板', addPanel);
    mk('✕', '刪除目前面板（至少保留一個）', deleteActive);
  }

  function switchPanel(id) {
    const p = store.panels.find(x => x.id === id);
    if (!p) return;
    store.active = id;
    writeStore();
    render();
    applyState(p.state);
  }
  function saveActive() {
    const p = store.panels.find(x => x.id === store.active);
    if (!p) return;
    p.state = captureState();
    writeStore();
    const btn = document.querySelector('#room-panel-bar .room-panel-act');
    if (btn) { const old = btn.textContent; btn.textContent = '✅'; setTimeout(() => { btn.textContent = old; }, 900); }
  }
  function addPanel() {
    if (store.panels.length >= MAX_PANELS) { alert('面板最多 ' + MAX_PANELS + ' 個，請先刪除不用的。'); return; }
    const name = (prompt('新面板名稱（會存下目前的標的、週期、指標與副圖）：', '面板 ' + (store.panels.length + 1)) || '').trim();
    if (!name) return;
    const id = 'p' + Date.now().toString(36);
    store.panels.push({ id, name: name.slice(0, 12), state: captureState() });
    store.active = id;
    writeStore();
    render();
  }
  function renamePanel(id) {
    const p = store.panels.find(x => x.id === id);
    if (!p) return;
    const name = (prompt('面板名稱：', p.name) || '').trim();
    if (!name) return;
    p.name = name.slice(0, 12);
    writeStore();
    render();
  }
  function deleteActive() {
    if (store.panels.length <= 1) { alert('至少要保留一個面板。'); return; }
    const p = store.panels.find(x => x.id === store.active);
    if (!p || !confirm('刪除面板「' + p.name + '」？')) return;
    store.panels = store.panels.filter(x => x.id !== p.id);
    store.active = store.panels[0].id;
    writeStore();
    render();
    applyState(store.panels[0].state);
  }

  function seedStore() {
    // 第一次使用：把「目前畫面」存成面板 1；面板 2 是個股期貨日K的起始版型。兩個都可以自己改、自己存。
    const cur = captureState();
    const stockInd = Object.assign({}, cur.indicators, { gex: false });
    return {
      active: 'p1',
      panels: [
        { id: 'p1', name: '台指期＋選擇權', state: cur },
        { id: 'p2', name: '個股／個股期', state: Object.assign({}, cur, { symbol: 'CDF', tf: '1D', indicators: stockInd }) }
      ]
    };
  }

  function boot() {
    injectStyle();
    const host = document.querySelector('.header-center');
    if (!host) return;
    const bar = document.createElement('div');
    bar.id = 'room-panel-bar';
    bar.className = 'room-panel-bar';
    host.appendChild(bar);

    const saved = readStore();
    store = saved || seedStore();
    if (!saved) writeStore();
    render();
    // 有存過就還原上次使用的面板；第一次使用維持原本畫面不動
    if (saved) {
      const p = store.panels.find(x => x.id === store.active) || store.panels[0];
      store.active = p.id;
      applyState(p.state);
    }
  }

  // room.js 在 DOMContentLoaded 後非同步初始化（載入資料、建圖表、綁事件）。等它完成再接上面板。
  function whenReady(tries) {
    const ready = typeof candleSeries !== 'undefined' && candleSeries &&
      document.querySelector('.btn-tf') && document.getElementById('apply-indicator-settings-btn');
    if (ready) { boot(); return; }
    if (tries > 150) { console.warn('room_panels: room.js 初始化逾時，面板功能未啟用'); return; }
    setTimeout(() => whenReady(tries + 1), 200);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => whenReady(0));
  else whenReady(0);
})();
