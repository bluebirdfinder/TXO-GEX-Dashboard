import os

app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.js")

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace renderHotMoneyDigest call
old_hot_money_code = """  // Hot Money Digest Panel
  try {
    const hotMoneyPanelEl = document.getElementById('hot-money-express-panel');
    if (hotMoneyPanelEl && gexData.hot_money_digest && gexData.hot_money_digest.hot_money_summary_html) {
      hotMoneyPanelEl.innerHTML = gexData.hot_money_digest.hot_money_summary_html;
    }
  } catch (hotMoneyErr) {
    console.error('Hot money panel error:', hotMoneyErr);
  }"""

new_hot_money_code = """  // Hot Money Digest Panel
  try { renderHotMoneyDigest(); } catch (hotMoneyErr) { console.error('Hot money panel error:', hotMoneyErr); }"""

if old_hot_money_code in content:
    content = content.replace(old_hot_money_code, new_hot_money_code)

# Add renderHotMoneyDigest function
render_hot_money_func = """
function renderHotMoneyDigest() {
  const hotMoneyPanelEl = document.getElementById('hot-money-express-panel');
  if (!hotMoneyPanelEl || !gexData.hot_money_digest) return;

  const hm = gexData.hot_money_digest;
  let html = hm.hot_money_summary_html || '';

  if (hm.fx_5day_history) {
    const fxHist = hm.fx_5day_history;
    const usdtwdHist = fxHist.usdtwd || [];
    const dxyHist = fxHist.dxy || [];
    const usdjpyHist = fxHist.usdjpy || [];

    let tableRows = '';
    const dates = usdtwdHist.map(h => h.date);

    for (let i = 0; i < dates.length; i++) {
      const d = dates[i];
      const twdItem = usdtwdHist[i] || {};
      const dxyItem = dxyHist[i] || {};
      const jpyItem = usdjpyHist[i] || {};

      const twdChgClass = twdItem.change < 0 ? 'tag-bull' : (twdItem.change > 0 ? 'tag-bear' : '');
      const dxyChgClass = dxyItem.change > 0 ? 'tag-bull' : (dxyItem.change < 0 ? 'tag-bear' : '');
      const jpyChgClass = jpyItem.change > 0 ? 'tag-bear' : (jpyItem.change < 0 ? 'tag-bull' : '');

      tableRows += `
        <tr>
          <td><strong>${d}</strong></td>
          <td><code>${twdItem.price !== undefined ? twdItem.price : '-'}</code></td>
          <td class="${twdChgClass}"><strong>${twdItem.change >= 0 ? '+' : ''}${twdItem.change || 0} (${twdItem.pct >= 0 ? '+' : ''}${twdItem.pct || 0}%)</strong></td>
          <td><code>${dxyItem.price !== undefined ? dxyItem.price : '-'}</code></td>
          <td class="${dxyChgClass}"><strong>${dxyItem.change >= 0 ? '+' : ''}${dxyItem.change || 0} (${dxyItem.pct >= 0 ? '+' : ''}${dxyItem.pct || 0}%)</strong></td>
          <td><code>${jpyItem.price !== undefined ? jpyItem.price : '-'}</code></td>
          <td class="${jpyChgClass}"><strong>${jpyItem.change >= 0 ? '+' : ''}${jpyItem.change || 0} (${jpyItem.pct >= 0 ? '+' : ''}${jpyItem.pct || 0}%)</strong></td>
        </tr>
      `;
    }

    html += `
      <div style="margin-top: 14px; border-top: 1px solid var(--panel-border); padding-top: 12px;">
        <h4 style="font-size: 0.88rem; color: var(--gold-accent); margin-bottom: 8px;">🌐 近 5 日主要匯率與國際資金流向歷程 (Daily Exchange Rates & Trends)</h4>
        <div style="overflow-x: auto;">
          <table class="matrix-table" style="text-align: center;">
            <thead>
              <tr style="background: #18202d;">
                <th>日期</th>
                <th>美金/台幣 (USD/TWD)</th>
                <th>單日漲跌 (升貶值)</th>
                <th>美元指數 (DXY)</th>
                <th>DXY 變動 %</th>
                <th>美元/日圓 (USD/JPY)</th>
                <th>日圓 變動 %</th>
              </tr>
            </thead>
            <tbody>
              ${tableRows}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  hotMoneyPanelEl.innerHTML = html;
}
"""

if "function renderHotMoneyDigest()" not in content:
    content += "\n" + render_hot_money_func

# Patch populateNightTrading for 5-day night history table
old_night_end = """  const nSumEl = document.getElementById('night-trading-summary');
  if (nSumEl) {
    const defaultSum = "💡 <strong>夜盤籌碼白話解讀</strong>：外資大台夜盤僅微變 -7 口（外資無慌亂砍單），且在小台與微台大舉買超 +7,594 口吸收散戶籌碼，外資防守意圖強烈。";
    nSumEl.innerHTML = nightTrading.night_summary_text || defaultSum;
  }"""

new_night_end = """  const nSumEl = document.getElementById('night-trading-summary');
  if (nSumEl) {
    const defaultSum = "💡 <strong>夜盤籌碼白話解讀</strong>：外資大台夜盤變動 -153 口（約 -1.42 億 TWD），籌碼結構維繫中性姿態。";
    nSumEl.innerHTML = nightTrading.night_summary_text || defaultSum;
  }

  const nightHistContainer = document.getElementById('night-trading-5day-container');
  if (nightHistContainer && gexData.night_institutional_5day_history) {
    const nh = gexData.night_institutional_5day_history;
    const rowsHtml = nh.map(item => `
      <tr>
        <td><strong>${item.date}</strong></td>
        <td class="${item.foreign_tx >= 0 ? 'tag-bull' : 'tag-bear'}"><strong>${item.foreign_tx >= 0 ? '+' : ''}${item.foreign_tx.toLocaleString()} 口</strong></td>
        <td style="color: var(--gold-accent);">${item.foreign_amt >= 0 ? '+' : ''}${item.foreign_amt} 億</td>
        <td class="${item.mini_foreign >= 0 ? 'tag-bull' : 'tag-bear'}">${item.mini_foreign >= 0 ? '+' : ''}${item.mini_foreign.toLocaleString()} 口</td>
        <td class="${item.micro_foreign >= 0 ? 'tag-bull' : 'tag-bear'}">${item.micro_foreign >= 0 ? '+' : ''}${item.micro_foreign.toLocaleString()} 口</td>
        <td class="${item.dealer_tx >= 0 ? 'tag-bull' : 'tag-bear'}">${item.dealer_tx >= 0 ? '+' : ''}${item.dealer_tx.toLocaleString()} 口</td>
      </tr>
    `).join('');

    nightHistContainer.innerHTML = `
      <h4 style="font-size: 0.88rem; color: var(--primary-accent); margin: 14px 0 8px 0;">🌙 近 5 日三大法人夜盤交易籌碼歷程矩陣</h4>
      <div style="overflow-x: auto;">
        <table class="matrix-table" style="text-align: center;">
          <thead>
            <tr style="background: #18202d;">
              <th>日期</th>
              <th>外資夜盤 TX 淨口數</th>
              <th>外資夜盤 TX 契約金額</th>
              <th>外資夜盤小台 (MTX)</th>
              <th>外資夜盤微台 (Micro)</th>
              <th>自營商夜盤 TX 淨口數</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  }"""

if old_night_end in content:
    content = content.replace(old_night_end, new_night_end)

# Patch populateStockFutures for basis & category filters
old_stock_func_body = """  tbody.innerHTML = list.map(stk => {
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
  }).join('');"""

new_stock_func_body = """  if (filterCat && filterCat.value === 'top10') {
    list = list.filter(stk => stk.is_top10_buy);
  }

  tbody.innerHTML = list.map(stk => {
    const trendBadge = stk.trend === 'Bull' 
      ? '<span class="badge-bull">▲ Bull (多)</span>' 
      : '<span class="badge-bear">▼ Bear (空)</span>';

    const catTag = `<span style="background: rgba(0,210,255,0.1); color: var(--primary-accent); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">${stk.category || '個股期貨'}</span>`;
    const changeClass = stk.change_pct >= 0 ? 'tag-bull' : 'tag-bear';
    const changeSign = stk.change_pct >= 0 ? '+' : '';

    const basisVal = stk.basis !== undefined ? stk.basis : 0.0;
    const basisBadge = basisVal >= 0 
      ? `<span class="tag-bull" style="font-weight: bold;">+${basisVal} (🔴 正價差)</span>`
      : `<span class="tag-bear" style="font-weight: bold;">${basisVal} (🟢 逆價差)</span>`;

    const futPriceDisplay = stk.fut_price ? stk.fut_price.toLocaleString() : stk.spot_price.toLocaleString();

    return `
      <tr>
        <td><strong>${stk.code}</strong></td>
        <td>${stk.name} ${stk.is_top10_buy ? '<span style="background: rgba(255,215,0,0.15); color: var(--gold-accent); padding: 1px 5px; border-radius: 4px; font-size: 0.72rem;">🔥 法人買超</span>' : ''}</td>
        <td>${catTag}</td>
        <td>${trendBadge}</td>
        <td><strong>${stk.spot_price.toLocaleString()}</strong></td>
        <td><strong>${futPriceDisplay}</strong></td>
        <td>${basisBadge}</td>
        <td class="${changeClass}"><strong>${changeSign}${stk.change_pct}%</strong></td>
        <td>${stk.volume ? stk.volume.toLocaleString() : '-'} 口</td>
        <td class="${stk.foreign_net >= 0 ? 'tag-bull' : 'tag-bear'}">${stk.foreign_net >= 0 ? '+' : ''}${stk.foreign_net} 口</td>
        <td class="${stk.dealer_net >= 0 ? 'tag-bull' : 'tag-bear'}">${stk.dealer_net >= 0 ? '+' : ''}${stk.dealer_net} 口</td>
        <td>${stk.has_night ? '🌙 <span style="color: var(--call-color)">有夜盤</span>' : '⚪ 無夜盤'}</td>
      </tr>
    `;
  }).join('');"""

if old_stock_func_body in content:
    content = content.replace(old_stock_func_body, new_stock_func_body)

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] Successfully patched app.js")
