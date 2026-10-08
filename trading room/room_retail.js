/**
 * room_retail.js - 左側欄「散戶淨部位」卡片（小台／微台，官方盤後資料）。
 *
 * 公式（2026-10-07 以台新盤後日報 7 個交易日逐日對照，7/7 完全吻合）：
 *   散戶淨未平倉 = −（外資 + 自營商 + 投信 的淨未平倉）＝全市場多方 OI − 三大法人多方 OI 後的多空差。
 * 這就是台新「逆勢籌碼指標」（小台）與富邦「小台／微台多空指標」的分子。資料由 scripts/fetch_and_calc_vision.py
 * 的 fetch_official_taifex_retail_sentiment() 每日盤後寫入 gex_data.json（retail_sentiment_details）與
 * institutional_snapshots.json（*_INST_RETAIL），本檔只讀取、不計算、不編造：沒有資料就明講「尚未取得」。
 *
 * 這是每日一個數字的盤後籌碼，不是盤中走勢；OP666「散戶走勢」的盤中算法目前未知，這裡不冒充它。
 */
(function () {
  'use strict';

  const fmt = (v) => (typeof v === 'number' && isFinite(v)) ? (v > 0 ? '+' : '') + v.toLocaleString() : '—';
  const clr = (v) => (typeof v !== 'number') ? 'var(--text-muted)' : (v >= 0 ? 'var(--call-color, #ef5350)' : 'var(--put-color, #26a69a)');

  async function loadHistory() {
    try {
      const res = await fetch('../data/institutional_snapshots.json?t=' + Date.now());
      if (!res.ok) return [];
      const snaps = await res.json();
      return Object.keys(snaps).filter(k => k.endsWith('_INST_RETAIL')).sort().slice(-7).map(k => ({
        date: k.slice(5, 10).replace('-', '/'),
        mtx: snaps[k].mtx_net_oi,
        tmf: snaps[k].tmf_net_oi
      }));
    } catch (e) { return []; }
  }

  function box(title, d) {
    if (!d) return `<div style="flex:1;opacity:.6;font-size:.7rem">${title}<br>—</div>`;
    return `<div style="flex:1;min-width:0">
      <div style="font-size:.68rem;color:var(--text-muted)">${title}</div>
      <div style="font-weight:700;font-size:1rem;color:${clr(d.net_oi)}">${fmt(d.net_oi)} 口</div>
      <div style="font-size:.66rem;color:var(--gold-accent,#ffd700)">單日 ${fmt(d.daily_change)}　多空比 ${typeof d.ratio === 'number' ? (d.ratio > 0 ? '+' : '') + d.ratio.toFixed(2) + '%' : '—'}</div>
    </div>`;
  }

  async function render() {
    const host = document.getElementById('macro-risk-hud');
    if (!host) return;
    let el = document.getElementById('retail-net-card');
    if (!el) {
      el = document.createElement('div');
      el.id = 'retail-net-card';
      el.className = 'left-section';
      el.style.cssText = 'border-bottom:1px solid var(--panel-border);padding:8px 10px;';
      host.after(el);
    }
    const det = (typeof gexData !== 'undefined' && gexData) ? gexData.retail_sentiment_details : null;
    if (!det || !det.mini_mtx || !det.micro_tmf) {
      el.innerHTML = '<div style="font-size:.74rem;color:var(--text-muted)">🧑‍🤝‍🧑 散戶淨部位：⚪ 資料尚未取得（不顯示舊數字）</div>';
      return;
    }
    // 多空能量（台新日報公式，10 個交易日逐日吻合）= 3 × 外資小台淨未平倉；佔比 = 2 × 外資小台淨 ÷ 小台總未平倉。為何乘 3 不明，僅照公式呈現。
    const bs = det.broker_snapshot || {};
    const fm = bs.foreign_mtx_net;
    const energy = (typeof fm === 'number') ? 3 * fm : null;
    const energyChg = (typeof bs.foreign_mtx_change === 'number') ? 3 * bs.foreign_mtx_change : null;
    const totOi = det.mini_mtx.total_oi;
    const energyPct = (energy !== null && typeof totOi === 'number' && totOi > 0) ? (2 * fm / totOi * 100) : null;
    const energyHtml = (energy === null)
      ? '<div style="margin-top:6px;font-size:.66rem;color:var(--text-muted)">多空能量：⚪ 外資小台淨未平倉尚未取得</div>'
      : `<div style="margin-top:6px;padding-top:5px;border-top:1px dashed var(--panel-border)">
          <div style="font-size:.68rem;color:var(--text-muted)" title="自製公式：3 × 外資小台淨未平倉（與台新日報逐日吻合）；非台新官方數字">多空能量（外資小台，自製公式）</div>
          <div style="font-weight:700;font-size:1rem;color:${clr(energy)}">${fmt(energy)}</div>
          <div style="font-size:.66rem;color:var(--gold-accent,#ffd700)">單日 ${fmt(energyChg)}　佔比 ${energyPct !== null ? (energyPct > 0 ? '+' : '') + energyPct.toFixed(2) + '%' : '—'}</div>
        </div>`;
    const hist = await loadHistory();
    const rows = hist.map(h => `<tr><td>${h.date}</td><td style="text-align:right;color:${clr(h.mtx)}">${fmt(h.mtx)}</td><td style="text-align:right;color:${clr(h.tmf)}">${fmt(h.tmf)}</td></tr>`).join('');
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
        <span style="font-weight:700;color:var(--gold-accent,#ffd700);font-size:.78rem">🧑‍🤝‍🧑 散戶淨部位（盤後官方）</span>
        <span style="font-size:.6rem;color:var(--text-muted)" title="散戶淨未平倉 = −(外資+自營商+投信)，期交所盤後公布；一天一個數字，非盤中走勢">?</span>
      </div>
      <div style="display:flex;gap:8px">${box('小台', det.mini_mtx)}${box('微台', det.micro_tmf)}</div>
      ${energyHtml}
      ${rows ? `<table style="width:100%;margin-top:6px;font-size:.64rem;color:var(--text-muted);border-collapse:collapse">
        <tr><th style="text-align:left;font-weight:400">日期</th><th style="text-align:right;font-weight:400">小台</th><th style="text-align:right;font-weight:400">微台</th></tr>${rows}</table>` : ''}`;
  }

  function whenReady(tries) {
    if (document.getElementById('macro-risk-hud') && typeof gexData !== 'undefined' && gexData) { render(); return; }
    if (tries > 150) return;
    setTimeout(() => whenReady(tries + 1), 200);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => whenReady(0));
  else whenReady(0);
})();
