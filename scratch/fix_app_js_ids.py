import os

app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.js")

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace stat card binding logic in renderDashboard
old_stat_code = """  // 1. 台指期 (日盤 vs 夜盤)
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
  }"""

new_stat_code = """  // 1. 台指期 (日盤 vs 夜盤)
  const dayTxf = gexData.day_txf_price || shift.day_txf_price || 45841;
  const nightTxf = gexData.night_txf_price || gexData.txf_price || 45727;
  const txfShift = gexData.session_shift ? gexData.session_shift.txf_shift : (nightTxf - dayTxf);

  const elTxfDay = document.getElementById('stat-txf-day');
  if (elTxfDay) elTxfDay.innerText = dayTxf.toLocaleString();
  const elTxfNight = document.getElementById('stat-txf-night');
  if (elTxfNight) elTxfNight.innerText = nightTxf.toLocaleString();
  const elTxfShift = document.getElementById('stat-txf-shift');
  if (elTxfShift) {
    const txfSign = txfShift >= 0 ? '+' : '';
    elTxfShift.innerText = `(${txfSign}${txfShift} 點)`;
    elTxfShift.style.color = txfShift >= 0 ? 'var(--call-color)' : 'var(--put-color)';
  }

  // 2. Zero Gamma (日盤 vs 夜盤)
  const zgDay = shift.day_zero_gamma || round(spot - 150, 1);
  const zgNight = gexData.zero_gamma_level || zgDay;
  const zgShift = round(zgNight - zgDay, 1);

  const elZgDay = document.getElementById('stat-zg-day');
  if (elZgDay) elZgDay.innerText = zgDay.toLocaleString();
  const elZgNight = document.getElementById('stat-zg-night');
  if (elZgNight) elZgNight.innerText = zgNight.toLocaleString();
  const elZgShift = document.getElementById('stat-zg-shift');
  if (elZgShift) {
    const zgSign = zgShift >= 0 ? '+' : '';
    elZgShift.innerText = `(${zgSign}${zgShift} 點)`;
  }

  // 3. Call Wall (日盤 vs 夜盤)
  const cwDay = shift.day_call_wall || (round(spot / 100) * 100 + 300);
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
  const pwDay = shift.day_put_wall || (round(spot / 100) * 100 - 300);
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
  }"""

if old_stat_code in content:
    content = content.replace(old_stat_code, new_stat_code)

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] Fixed stat card element ID bindings in app.js")
