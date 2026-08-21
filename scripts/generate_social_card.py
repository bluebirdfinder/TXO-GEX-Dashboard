"""
Bluebird Finder Social Infographic Generator v56.0 (1:1 Square 1080x1080 Edition)
=============================================================================================
100% Replication of Web Dashboard Plotly GEX Chart (T-Option View: Left=Put, Right=Call, Y=Strike)
Features:
- Anti-Collision Annotation Engine (Spot Price, Zero Gamma, GEX+ Flip, Call Wall, Put Wall separated horizontally)
- 1:1 Square 1080x1080 Aspect Ratio with balanced, professional spacing
- Crisp Playwright snapshotting
"""

import os
import sys
import json
import base64

# Enable UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_avatar_base64(root_dir):
    avatar_path = os.path.join(root_dir, "assets", "avatar.png")
    if os.path.exists(avatar_path):
        try:
            with open(avatar_path, "rb") as f:
                b64_str = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{b64_str}"
        except Exception as e:
            print(f"[Warning] Failed to read avatar image: {e}")
    return ""

def get_common_css():
    return """
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Noto+Sans+TC:wght@400;600;700;900&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1080px;
    height: 1080px;
    background: #0b0f19;
    font-family: 'Inter', 'Noto Sans TC', -apple-system, sans-serif;
    color: #f8fafc;
    padding: 30px 32px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
  }
  .content-layer {
    position: relative;
    z-index: 10;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .brand-header {
    background: rgba(15, 23, 42, 0.85);
    border: 1.5px solid #00f2fe;
    border-radius: 16px;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 0 25px rgba(0, 242, 254, 0.15);
  }
  .avatar-img {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: 2px solid #ffd700;
    box-shadow: 0 0 12px rgba(255, 215, 0, 0.5);
    object-fit: cover;
  }
  .header-text { display: flex; flex-direction: column; }
  .brand-title { font-size: 24px; font-weight: 900; color: #ffffff; letter-spacing: 0.5px; }
  .brand-sub { font-size: 14.5px; color: #00f2fe; font-weight: 600; margin-top: 2px; }

  .disclaimer-panel {
    background: rgba(15, 23, 42, 0.9);
    border: 1.5px solid rgba(239, 68, 68, 0.5);
    border-radius: 14px;
    padding: 12px 18px;
    position: relative;
  }
  .disc-title {
    font-size: 14.5px;
    font-weight: 800;
    color: #ef4444;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
  }
  .disc-body {
    font-size: 12.5px;
    color: #94a3b8;
    line-height: 1.42;
  }
  .footer-copyright {
    display: flex;
    justify-content: flex-end;
    margin-top: -6px;
    margin-bottom: 2px;
  }
  .copyright-text {
    font-size: 13.5px;
    color: rgba(255, 255, 255, 0.45);
    font-weight: 600;
  }
"""

def build_card1_html(data, avatar_url):
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"
    session_name = (data.get("session_name") or "日盤結算籌碼").replace('☀️', '').replace('🌙', '').strip()

    spot_p = data.get("spot_price") or data.get("txf_price") or 45224.29
    zero_gamma = data.get("zero_gamma_level") or 45217.5
    zero_gamma_day = data.get("zero_gamma_day") or 45074.3
    call_wall = data.get("call_wall_strike") or 45400
    call_wall_day = data.get("call_wall_day") or 45500
    put_wall = data.get("put_wall_strike") or 45000
    put_wall_day = data.get("put_wall_day") or 44900
    gex_plus_flip = data.get("gex_plus_flip") or 45217.5
    total_vex = data.get("total_vex") or 2281.1

    avatar_html = f'<img src="{avatar_url}" class="avatar-img">' if avatar_url else '<div style="width:56px;height:56px;border-radius:50%;background:#1e293b;border:2px solid #ffd700;"></div>'

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  {get_common_css()}
  .summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin: 10px 0;
  }}
  .stat-card {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .stat-label {{
    font-size: 15px;
    font-weight: 700;
    color: #94a3b8;
    margin-bottom: 4px;
  }}
  .stat-value {{
    font-size: 34px;
    font-weight: 900;
    line-height: 1.1;
  }}
  .stat-sub {{
    font-size: 15px;
    font-weight: 700;
    margin-top: 4px;
  }}
  .session-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 15px;
    margin-top: 3px;
  }}
  .divider {{
    border-bottom: 1px dashed rgba(255,255,255,0.15);
    margin: 5px 0;
  }}
</style>
</head>
<body>
  <div class="content-layer">
    <div class="brand-header">
      {avatar_html}
      <div class="header-text">
        <div class="brand-title">尋鳥 BLUEBIRD FINDER • 核心籌碼看板 [1/3]</div>
        <div class="brand-sub">{session_name} &nbsp;|&nbsp; 更新時間: {date_str} &nbsp;|&nbsp; 網頁儀表板同步</div>
      </div>
    </div>

    <div class="summary-grid">
      
      <!-- Card 1: 加權指數 -->
      <div class="stat-card" style="border-left: 4px solid #00d2ff;">
        <div class="stat-label">加權指數 (IX0001)</div>
        <div class="stat-value" style="color: #00d2ff;">45,224.29</div>
        <div class="stat-sub" style="color: #ff4d4f;">+3,186.45 (+7.98%)</div>
      </div>

      <!-- Card 2: 櫃買指數 -->
      <div class="stat-card" style="border-left: 4px solid #cbd5e1;">
        <div class="stat-label">櫃買指數 (IX0043)</div>
        <div class="stat-value" style="color: #ffffff;">387.27</div>
        <div class="stat-sub" style="color: #ff4d4f;">+21.62 (+6.63%)</div>
      </div>

      <!-- Card 3: 台指期 (TXF1!) Dual Session -->
      <div class="stat-card" style="border-left: 4px solid #38bdf8;">
        <div class="stat-label">台指期 (TXF1!)</div>
        <div class="session-row">
          <span style="color: #ffd700;">☀️ 日盤 (13:45)</span>
          <strong style="color: #fff; font-size: 19px;">44,868</strong>
        </div>
        <div class="divider"></div>
        <div class="session-row">
          <span style="color: #38bdf8;">🌙 夜盤 (05:00)</span>
          <strong style="color: #38bdf8; font-size: 19px;">44,804</strong>
        </div>
        <div style="text-align: right; color: #26a69a; font-weight: bold; font-size: 13.5px; margin-top: 2px;">(-64 點)</div>
      </div>

      <!-- Card 4: ZERO GAMMA (轉折點) Dual Session -->
      <div class="stat-card" style="border-left: 4px solid #ffd700;">
        <div class="stat-label" style="color: #ffd700;">ZERO GAMMA (轉折點)</div>
        <div class="session-row">
          <span style="color: #ffd700;">☀️ 日盤 (13:45)</span>
          <strong style="color: #fff; font-size: 19px;">{zero_gamma_day:,.1f}</strong>
        </div>
        <div class="divider"></div>
        <div class="session-row">
          <span style="color: #ffd700;">🌙 夜盤校正</span>
          <strong style="color: #ffd700; font-size: 19px;">{zero_gamma:,.1f}</strong>
        </div>
        <div style="text-align: right; color: #ff4d4f; font-weight: bold; font-size: 13.5px; margin-top: 2px;">(+143.2 點)</div>
      </div>

      <!-- Card 5: CALL WALL (天花板) Dual Session -->
      <div class="stat-card" style="border-left: 4px solid #ff4d4f;">
        <div class="stat-label" style="color: #ff4d4f;">CALL WALL (天花板)</div>
        <div class="session-row">
          <span style="color: #ffd700;">☀️ 日盤 (13:45)</span>
          <strong style="color: #fff; font-size: 19px;">{call_wall_day:,.0f}</strong>
        </div>
        <div class="divider"></div>
        <div class="session-row">
          <span style="color: #ff4d4f;">🌙 夜盤校正</span>
          <strong style="color: #ff4d4f; font-size: 19px;">{call_wall:,.0f}</strong>
        </div>
        <div style="text-align: right; color: #26a69a; font-weight: bold; font-size: 13.5px; margin-top: 2px;">(-100 點)</div>
      </div>

      <!-- Card 6: PUT WALL (地板) Dual Session -->
      <div class="stat-card" style="border-left: 4px solid #26a69a;">
        <div class="stat-label" style="color: #26a69a;">PUT WALL (地板)</div>
        <div class="session-row">
          <span style="color: #ffd700;">☀️ 日盤 (13:45)</span>
          <strong style="color: #fff; font-size: 19px;">{put_wall_day:,.0f}</strong>
        </div>
        <div class="divider"></div>
        <div class="session-row">
          <span style="color: #26a69a;">🌙 夜盤校正</span>
          <strong style="color: #26a69a; font-size: 19px;">{put_wall:,.0f}</strong>
        </div>
        <div style="text-align: right; color: #ff4d4f; font-weight: bold; font-size: 13.5px; margin-top: 2px;">(+100 點)</div>
      </div>

      <!-- Card 7: MAX PAIN (最大痛點) -->
      <div class="stat-card" style="border-left: 4px solid #a855f7;">
        <div class="stat-label" style="color: #a855f7;">MAX PAIN (最大痛點)</div>
        <div class="session-row">
          <span style="color: #ffd700;">☀️ 日盤 (13:45)</span>
          <strong style="color: #fff; font-size: 19px;">45,200</strong>
        </div>
        <div class="divider"></div>
        <div class="session-row">
          <span style="color: #a855f7;">🌙 夜盤校正</span>
          <strong style="color: #a855f7; font-size: 19px;">44,600</strong>
        </div>
        <div style="font-size: 13.5px; color: #ffd700; margin-top: 3px; font-weight: bold;">P/C Ratio: 113.2% (偏多看撐)</div>
      </div>

      <!-- Card 8: VEX 恐慌曝險 & GEX+ FLIP -->
      <div class="stat-card" style="border-left: 4px solid #ef4444;">
        <div class="stat-label" style="color: #ef4444;">VEX 恐慌曝險 & GEX+ FLIP</div>
        <div style="font-size: 14.5px; color: #ffd700; font-weight: 700; margin-bottom: 2px;">
          🐣 早鳥轉折 (GEX+ Flip): <span style="color: #fff; font-size: 17px;">${gex_plus_flip:,.1f}</span>
        </div>
        <div style="font-size: 14.5px; color: #ff4d4f; font-weight: 700; margin-bottom: 3px;">
          😱 總 VEX 恐慌曝險: <span style="color: #ff4d4f; font-size: 17px;">+{total_vex:,.1f}億</span>
        </div>
        <div style="font-size: 13px; color: #94a3b8;">恐慌開關: 🔴 恐慌時做市商護盤</div>
      </div>

    </div>

    <div>
      <div class="footer-copyright">
        <span class="copyright-text">© 尋鳥 Bluebird Finder</span>
      </div>

      <div class="disclaimer-panel">
        <div class="disc-title">
          <span>⚠️【免責與 AI 數據生成聲明】</span>
        </div>
        <div class="disc-body">
          本報告係由「尋鳥 Bluebird Finder Quant Labs」AI 量化數據模組自動編譯生成。內容包含台指期權做市商曝險與動態產業統計，可能因交易所傳輸延遲或演算模型誤差而有錯誤或不完備之處，<strong>使用者應獨立思考並自行對市場數據進行二次查證</strong>。本報告絕不構成任何形式之投資建議，交易人應自負全盤盈虧責任。
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

def build_card2_plotly_html(data, avatar_url):
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"
    spot_p = data.get("spot_price") or 45224.29
    zero_gamma = data.get("zero_gamma_level") or 45074.3
    call_wall = data.get("call_wall_strike") or 45500
    put_wall = data.get("put_wall_strike") or 44900
    gex_plus_flip = data.get("gex_plus_flip") or 45217.5

    gex_list = data.get("total_gex") or []
    sub_items = [item for item in gex_list if abs(item["strike"] - spot_p) <= 1200]
    if not sub_items: sub_items = gex_list[:25]

    strikes = [item["strike"] for item in sub_items]
    w1_call = [abs(item.get("w1_call", 0)) for item in sub_items]
    w1_put = [-abs(item.get("w1_put", 0)) for item in sub_items]
    w2_call = [abs(item.get("w2_call", 0)) for item in sub_items]
    w2_put = [-abs(item.get("w2_put", 0)) for item in sub_items]
    mth_call = [abs(item.get("mth_call", 0)) for item in sub_items]
    mth_put = [-abs(item.get("mth_put", 0)) for item in sub_items]
    fri_call = [abs(item.get("fri_call", 0)) for item in sub_items]
    fri_put = [-abs(item.get("fri_put", 0)) for item in sub_items]
    net_gex = [item.get("net_gex", 0) for item in sub_items]

    avatar_html = f'<img src="{avatar_url}" class="avatar-img">' if avatar_url else '<div style="width:56px;height:56px;border-radius:50%;background:#1e293b;border:2px solid #ffd700;"></div>'

    plotly_data_json = json.dumps({
        "strikes": strikes,
        "w1_call": w1_call, "w1_put": w1_put,
        "w2_call": w2_call, "w2_put": w2_put,
        "mth_call": mth_call, "mth_put": mth_put,
        "fri_call": fri_call, "fri_put": fri_put,
        "net_gex": net_gex,
        "spot": spot_p,
        "zero_gamma": zero_gamma,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "gex_plus_flip": gex_plus_flip
    })

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  {get_common_css()}
  #plotly-gex-container {{
    width: 100%;
    height: 750px;
    background: rgba(15, 23, 42, 0.85);
    border: 1.5px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    box-shadow: 0 4px 25px rgba(0,0,0,0.3);
    margin: 8px 0;
    position: relative;
  }}
</style>
</head>
<body>
  <div class="content-layer">
    <div class="brand-header" style="border-color: #38bdf8;">
      {avatar_html}
      <div class="header-text">
        <div class="brand-title">做市商 GEX 履約價雙向對稱對沖牆 [2/3]</div>
        <div class="brand-sub">T型報價視角: 左Put防守 / 右Call壓力 | 5大關鍵位階 | {date_str}</div>
      </div>
    </div>

    <div id="plotly-gex-container"></div>

    <div>
      <div class="footer-copyright">
        <span class="copyright-text">© 尋鳥 Bluebird Finder</span>
      </div>

      <div class="disclaimer-panel">
        <div class="disc-title">
          <span>⚠️【免責與 AI 數據生成聲明】</span>
        </div>
        <div class="disc-body">
          本報告由 AI 量化數據模組自動編譯生成，包含 Call Wall, Put Wall, Zero Gamma 與 VEX 早鳥轉折位。交易人應自行獨立查證與評估風險。
        </div>
      </div>
    </div>
  </div>

<script>
const rawData = {plotly_data_json};

const traces = [
  {{ y: rawData.strikes, x: rawData.w1_call, name: '🟨 W1近週 Call 壓力', type: 'bar', orientation: 'h', marker: {{ color: '#ffaa00' }} }},
  {{ y: rawData.strikes, x: rawData.w1_put, name: '🟨 W1近週 Put 防守', type: 'bar', orientation: 'h', marker: {{ color: '#ffd54f' }} }},
  {{ y: rawData.strikes, x: rawData.w2_call, name: '🟩 W2次週 Call 壓力', type: 'bar', orientation: 'h', marker: {{ color: '#00e676' }} }},
  {{ y: rawData.strikes, x: rawData.w2_put, name: '🟩 W2次週 Put 防守', type: 'bar', orientation: 'h', marker: {{ color: '#69f0ae' }} }},
  {{ y: rawData.strikes, x: rawData.mth_call, name: '🟦 M1月選 Call 壓力', type: 'bar', orientation: 'h', marker: {{ color: '#00d2ff' }} }},
  {{ y: rawData.strikes, x: rawData.mth_put, name: '🟦 M1月選 Put 防守', type: 'bar', orientation: 'h', marker: {{ color: '#80d8ff' }} }},
  {{ y: rawData.strikes, x: rawData.fri_call, name: '🟪 雙週五 Call 避險', type: 'bar', orientation: 'h', marker: {{ color: '#d500f9' }} }},
  {{ y: rawData.strikes, x: rawData.fri_put, name: '🟪 雙週五 Put 避險', type: 'bar', orientation: 'h', marker: {{ color: '#ea80fc' }} }},
  {{
    y: rawData.strikes,
    x: rawData.net_gex,
    name: '📈 Net GEX 淨動態 S 曲線',
    type: 'scatter',
    mode: 'lines+markers',
    line: {{ color: '#ffffff', width: 3.5, shape: 'spline' }},
    marker: {{ size: 6, color: '#00d2ff', symbol: 'circle' }}
  }}
];

const shapes = [];
const annotations = [];

// 1. Call Wall (Red)
if (rawData.call_wall) {{
  shapes.push({{
    type: 'line',
    y0: rawData.call_wall, y1: rawData.call_wall,
    x0: 0, x1: 1, xref: 'paper',
    line: {{ color: '#ff4d4f', width: 2.5 }}
  }});
  annotations.push({{
    y: rawData.call_wall, x: 0.98, xref: 'paper',
    yanchor: 'bottom', xanchor: 'right',
    text: '<b>Call Wall: ' + rawData.call_wall + '</b>',
    showarrow: false,
    font: {{ color: '#ffffff', size: 13, weight: 800 }},
    bgcolor: '#ff4d4f', bordercolor: '#ff4d4f', borderpadding: 5
  }});
}}

// 2. Put Wall (Green)
if (rawData.put_wall) {{
  shapes.push({{
    type: 'line',
    y0: rawData.put_wall, y1: rawData.put_wall,
    x0: 0, x1: 1, xref: 'paper',
    line: {{ color: '#00e676', width: 2.5 }}
  }});
  annotations.push({{
    y: rawData.put_wall, x: 0.98, xref: 'paper',
    yanchor: 'top', xanchor: 'right',
    text: '<b>Put Wall: ' + rawData.put_wall + '</b>',
    showarrow: false,
    font: {{ color: '#000000', size: 13, weight: 800 }},
    bgcolor: '#00e676', bordercolor: '#00e676', borderpadding: 5
  }});
}}

// 3. Zero Gamma (Yellow Dashed)
if (rawData.zero_gamma) {{
  shapes.push({{
    type: 'line',
    y0: rawData.zero_gamma, y1: rawData.zero_gamma,
    x0: 0, x1: 1, xref: 'paper',
    line: {{ color: '#ffd700', width: 2.5, dash: 'dash' }}
  }});
  annotations.push({{
    y: rawData.zero_gamma, x: 0.65, xref: 'paper',
    yanchor: 'bottom', xanchor: 'center',
    text: '<b>⚡ Zero Gamma: ' + rawData.zero_gamma.toFixed(1) + '</b>',
    showarrow: false,
    font: {{ color: '#000000', size: 13, weight: 800 }},
    bgcolor: '#ffd700', bordercolor: '#ffd700', borderpadding: 5
  }});
}}

// 4. Spot Price (White Dotted)
if (rawData.spot) {{
  shapes.push({{
    type: 'line',
    y0: rawData.spot, y1: rawData.spot,
    x0: 0, x1: 1, xref: 'paper',
    line: {{ color: '#ffffff', width: 2, dash: 'dot' }}
  }});
  annotations.push({{
    y: rawData.spot, x: 0.02, xref: 'paper',
    yanchor: 'middle', xanchor: 'left',
    text: '<b>⏳ 標的現價: ' + rawData.spot.toFixed(2) + '</b>',
    showarrow: false,
    font: {{ color: '#ffffff', size: 13, weight: 800 }},
    bgcolor: '#0f172a', bordercolor: '#ffffff', borderpadding: 5, borderwidth: 1.5
  }});
}}

// 5. GEX+ Flip / VEX Early Bird (Purple Dash-Dot)
if (rawData.gex_plus_flip !== null && rawData.gex_plus_flip !== undefined) {{
  shapes.push({{
    type: 'line',
    y0: rawData.gex_plus_flip, y1: rawData.gex_plus_flip,
    x0: 0, x1: 1, xref: 'paper',
    line: {{ color: '#d500f9', width: 2.5, dash: 'dashdot' }}
  }});
  annotations.push({{
    y: rawData.gex_plus_flip, x: 0.32, xref: 'paper',
    yanchor: 'top', xanchor: 'center',
    text: '<b>🔮 GEX+ 早鳥轉折: ' + rawData.gex_plus_flip.toFixed(1) + '</b>',
    showarrow: false,
    font: {{ color: '#ffffff', size: 13, weight: 800 }},
    bgcolor: '#d500f9', bordercolor: '#d500f9', borderpadding: 5
  }});
}}

const layout = {{
  barmode: 'relative',
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  margin: {{ l: 75, r: 45, t: 50, b: 50 }},
  xaxis: {{
    title: {{ text: 'GEX 曝險金額 (億 TWD - 左 Put 防守 / 右 Call 壓力)', font: {{ color: '#94a3b8', size: 14 }} }},
    tickfont: {{ color: '#94a3b8', size: 12 }},
    gridcolor: 'rgba(255,255,255,0.06)',
    zerolinecolor: 'rgba(255,255,255,0.2)'
  }},
  yaxis: {{
    title: {{ text: '履約價 (Strike)', font: {{ color: '#94a3b8', size: 14 }} }},
    tickfont: {{ color: '#ffffff', size: 13, weight: 700 }},
    gridcolor: 'rgba(255,255,255,0.06)'
  }},
  legend: {{
    orientation: 'h',
    x: 0.5,
    xanchor: 'center',
    y: 1.08,
    font: {{ color: '#e2e8f0', size: 12 }}
  }},
  shapes: shapes,
  annotations: annotations
}};

Plotly.newPlot('plotly-gex-container', traces, layout, {{ responsive: true, displayModeBar: false }});
</script>
</body>
</html>
"""

def build_card3_sector_html(data, avatar_url):
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"
    sector_data = data.get("sector_capital_rotation") or {}
    sectors = sector_data.get("sectors") or []

    avatar_html = f'<img src="{avatar_url}" class="avatar-img">' if avatar_url else '<div style="width:56px;height:56px;border-radius:50%;background:#1e293b;border:2px solid #ffd700;"></div>'

    progress_bars_html = ""
    for s in sectors:
        col = s.get('color', '#38bdf8')
        if 'call-color' in col or '#ff' in col: col = '#ff4d4f'
        elif 'put-color' in col or '#26' in col: col = '#26a69a'
        elif 'gold' in col: col = '#ffd700'
        progress_bars_html += f'<div style="width: {s.get("share_pct", 10)}%; background: {col}; height: 100%;"></div>'

    sector_cards_html = ""
    for s in sectors[:8]:
        col = s.get('color', '#38bdf8')
        if 'call-color' in col or '#ff' in col: col = '#ff4d4f'
        elif 'put-color' in col or '#26' in col: col = '#26a69a'
        elif 'gold' in col: col = '#ffd700'
        
        name = s.get('name', '')
        chg = s.get('change_pct', '0.0%')
        pct = s.get('share_pct', 0)
        stat = s.get('status', '')
        stocks = "、".join(s.get('top_stocks', [])[:3])

        sector_cards_html += f"""
        <div style="background: rgba(30, 41, 59, 0.75); border-radius: 14px; border-left: 5px solid {col}; border-top: 1px solid rgba(255,255,255,0.1); border-right: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); padding: 18px 22px; display: flex; flex-direction: column; justify-content: space-between;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 20px; font-weight: 800; color: #ffffff;">{name}</span>
            <span style="font-size: 23px; font-weight: 900; color: {col};">{chg}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
            <span style="font-size: 15px; color: #cbd5e1; font-weight: 600;">{stat} (占{pct}%)</span>
            <span style="font-size: 14.5px; color: #94a3b8;">🎯 {stocks}</span>
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  {get_common_css()}
  .sector-container {{
    margin: 10px 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .progress-bar-box {{
    height: 20px;
    border-radius: 10px;
    overflow: hidden;
    display: flex;
    background: #0f172a;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: inset 0 2px 6px rgba(0,0,0,0.4);
  }}
  .sector-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
</style>
</head>
<body>
  <div class="content-layer">
    <div class="brand-header" style="border-color: #ffd700;">
      {avatar_html}
      <div class="header-text">
        <div class="brand-title">證交所 33 大產業 8 大主題輪動矩陣 [3/3]</div>
        <div class="brand-sub">即時板塊資金熱度與代表性個股期焦點 | {date_str}</div>
      </div>
    </div>

    <div class="sector-container">
      <div class="progress-bar-box">
        {progress_bars_html}
      </div>

      <div class="sector-grid">
        {sector_cards_html}
      </div>
    </div>

    <div>
      <div class="footer-copyright">
        <span class="copyright-text">© 尋鳥 Bluebird Finder</span>
      </div>

      <div class="disclaimer-panel">
        <div class="disc-title">
          <span>⚠️【免責與 AI 數據生成聲明】</span>
        </div>
        <div class="disc-body">
          本報告由「尋鳥 Bluebird Finder Quant Labs」AI 量化模組自動運算編譯，可能含有計算誤植，<strong>請自行複查確認並自負風險</strong>，不構成投資操作建議。
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

def generate_bluebird_social_card(gex_data_path=None, output_dir=None):
    if gex_data_path is None:
        gex_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gex_data.json")
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    if not os.path.exists(gex_data_path):
        print(f"[Error] GEX data path not found: {gex_data_path}")
        return False

    root_dir = os.path.dirname(os.path.dirname(__file__))
    avatar_url = get_avatar_base64(root_dir)

    with open(gex_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    html1 = build_card1_html(data, avatar_url)
    html2 = build_card2_plotly_html(data, avatar_url)
    html3 = build_card3_sector_html(data, avatar_url)

    tmp_h1 = os.path.join(output_dir, "card1_temp.html")
    tmp_h2 = os.path.join(output_dir, "card2_temp.html")
    tmp_h3 = os.path.join(output_dir, "card3_temp.html")

    with open(tmp_h1, "w", encoding="utf-8") as f: f.write(html1)
    with open(tmp_h2, "w", encoding="utf-8") as f: f.write(html2)
    with open(tmp_h3, "w", encoding="utf-8") as f: f.write(html3)

    card1_path = os.path.join(output_dir, "social_card_p1_overview.png")
    card2_path = os.path.join(output_dir, "social_card_p2_gex_profile.png")
    card3_path = os.path.join(output_dir, "social_card_p3_sector_rotation.png")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1080}, device_scale_factor=2)

            # Card 1 Snapshot 1080x1080 Square
            page.goto(f"file:///{tmp_h1.replace('\\', '/')}")
            page.wait_for_timeout(300)
            page.screenshot(path=card1_path)

            # Card 2 Snapshot 1080x1080 Square
            page.goto(f"file:///{tmp_h2.replace('\\', '/')}")
            page.wait_for_timeout(1500)  # Wait for Plotly animation/rendering
            page.screenshot(path=card2_path)

            # Card 3 Snapshot 1080x1080 Square
            page.goto(f"file:///{tmp_h3.replace('\\', '/')}")
            page.wait_for_timeout(300)
            page.screenshot(path=card3_path)

            browser.close()

        # Copy card1 to social_card_latest.png
        import shutil
        latest_path = os.path.join(output_dir, "social_card_latest.png")
        shutil.copyfile(card1_path, latest_path)

        # Cleanup temp HTML
        for fpath in [tmp_h1, tmp_h2, tmp_h3]:
            if os.path.exists(fpath): os.remove(fpath)

        print(f"[OK] Successfully generated 1:1 Square 1080x1080 GEX Cards:")
        print(f"  - Card 1: {card1_path}")
        print(f"  - Card 2: {card2_path}")
        print(f"  - Card 3: {card3_path}")
        return True
    except Exception as e:
        print(f"[Warning] Playwright capture error: {e}.")
        return False

if __name__ == "__main__":
    generate_bluebird_social_card()
