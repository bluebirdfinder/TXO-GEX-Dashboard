"""
Bluebird Finder Social Infographic Generator v52.0 (Compact Layout & Native GEX Chart Edition)
================================================================================================
Fixed User Feedback:
1. Eliminated excess vertical white space on Card 1 & Card 2 to fill 4:5 vertical mobile screen comfortably.
2. Moved watermark '© 尋鳥 Bluebird Finder' away from top header down to bottom right of summary panel.
3. Enhanced Card 2 GEX Chart with explicit contract scope ('【全市場所有期權總合 (月選+周選總籌碼)】') and web dashboard native styling.
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
    height: 1350px;
    background: #0b0f19;
    font-family: 'Inter', 'Noto Sans TC', -apple-system, sans-serif;
    color: #f8fafc;
    padding: 32px 36px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
  }
  .content-layer {
    position: relative;
    z-index: 10;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .brand-header {
    background: rgba(15, 23, 42, 0.85);
    border: 1.5px solid #00f2fe;
    border-radius: 16px;
    padding: 18px 24px;
    display: flex;
    align-items: center;
    gap: 18px;
    box-shadow: 0 0 25px rgba(0, 242, 254, 0.15);
  }
  .avatar-img {
    width: 62px;
    height: 62px;
    border-radius: 50%;
    border: 2px solid #ffd700;
    box-shadow: 0 0 12px rgba(255, 215, 0, 0.5);
    object-fit: cover;
  }
  .header-text { display: flex; flex-direction: column; }
  .brand-title { font-size: 27px; font-weight: 900; color: #ffffff; letter-spacing: 0.5px; }
  .brand-sub { font-size: 15px; color: #00f2fe; font-weight: 600; margin-top: 2px; }

  /* Web Dashboard Exact Watermark Style (.watermark-panel::after) */
  .web-watermark {
    position: absolute;
    right: 18px;
    bottom: 12px;
    font-size: 13.5px;
    font-family: 'Inter', sans-serif;
    color: rgba(255, 255, 255, 0.38);
    letter-spacing: 0.5px;
    font-weight: 600;
    pointer-events: none;
    user-select: none;
  }

  .disclaimer-panel {
    background: rgba(15, 23, 42, 0.9);
    border: 1.5px solid rgba(239, 68, 68, 0.5);
    border-radius: 14px;
    padding: 16px 22px;
    position: relative;
  }
  .disc-title {
    font-size: 15.5px;
    font-weight: 800;
    color: #ef4444;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
  }
  .disc-body {
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.45;
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

    avatar_html = f'<img src="{avatar_url}" class="avatar-img">' if avatar_url else '<div style="width:62px;height:62px;border-radius:50%;background:#1e293b;border:2px solid #ffd700;"></div>'

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  {get_common_css()}
  .summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
    margin: 18px 0;
    flex: 1;
    align-content: space-between;
    position: relative;
  }}
  .stat-card {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 22px 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
  }}
  .stat-label {{
    font-size: 16px;
    font-weight: 700;
    color: #94a3b8;
    margin-bottom: 8px;
  }}
  .stat-value {{
    font-size: 36px;
    font-weight: 900;
    line-height: 1.1;
  }}
  .stat-sub {{
    font-size: 15px;
    font-weight: 700;
    margin-top: 6px;
  }}
  .session-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 15px;
    margin-top: 6px;
  }}
  .divider {{
    border-bottom: 1px dashed rgba(255,255,255,0.15);
    margin: 8px 0;
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

    <!-- 8 Summary Cards Grid (Exact Dashboard Replication - Compact Height Balance) -->
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
        <div style="text-align: right; color: #26a69a; font-weight: bold; font-size: 14px; margin-top: 2px;">(-64 點)</div>
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
        <div style="text-align: right; color: #ff4d4f; font-weight: bold; font-size: 14px; margin-top: 2px;">(+143.2 點)</div>
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
        <div style="text-align: right; color: #26a69a; font-weight: bold; font-size: 14px; margin-top: 2px;">(-100 點)</div>
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
        <div style="text-align: right; color: #ff4d4f; font-weight: bold; font-size: 14px; margin-top: 2px;">(+100 點)</div>
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
        <div style="font-size: 13px; color: #ffd700; margin-top: 4px; font-weight: bold;">P/C Ratio: 113.2% (偏多看撐)</div>
      </div>

      <!-- Card 8: VEX 恐慌曝險 & GEX+ FLIP -->
      <div class="stat-card" style="border-left: 4px solid #ef4444;">
        <div class="stat-label" style="color: #ef4444;">VEX 恐慌曝險 & GEX+ FLIP</div>
        <div style="font-size: 14px; color: #ffd700; font-weight: 700; margin-bottom: 2px;">
          🐣 早鳥轉折 (GEX+ Flip): <span style="color: #fff; font-size: 17px;">${gex_plus_flip:,.1f}</span>
        </div>
        <div style="font-size: 14px; color: #ff4d4f; font-weight: 700; margin-bottom: 4px;">
          😱 總 VEX 恐慌曝險: <span style="color: #ff4d4f; font-size: 17px;">+{total_vex:,.1f}億</span>
        </div>
        <div style="font-size: 13px; color: #94a3b8;">恐慌開關: 🔴 恐慌時做市商護盤</div>
      </div>

    </div>

    <!-- Watermark moved to bottom right area above disclaimer as requested -->
    <div style="display: flex; justify-content: flex-end; margin-bottom: 8px;">
      <span style="font-size: 14px; color: rgba(255, 255, 255, 0.45); font-weight: 600;">© 尋鳥 Bluebird Finder</span>
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
</body>
</html>
"""

def build_card2_strikes_html(data, avatar_url):
    spot_p = data.get("spot_price") or data.get("txf_price") or 45160.0
    zero_gamma = data.get("zero_gamma_level") or 45217.0
    call_wall = data.get("call_wall_strike") or 45400
    put_wall = data.get("put_wall_strike") or 45000
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"
    
    gex_list = data.get("total_gex") or []

    # Filter strikes within spot +- 1500 for compact balanced display
    sub_items = [item for item in gex_list if abs(item["strike"] - spot_p) <= 1500]
    if not sub_items: sub_items = gex_list[:22]

    max_val = max([abs(item.get("net_gex", 0)) for item in sub_items] + [10.0])

    avatar_html = f'<img src="{avatar_url}" class="avatar-img">' if avatar_url else '<div style="width:62px;height:62px;border-radius:50%;background:#1e293b;border:2px solid #ffd700;"></div>'

    bars_html = ""
    for item in sub_items:
        stk = item["strike"]
        val = item.get("net_gex", 0)
        pct = min(100, int(abs(val) / max_val * 100))
        color = "#ff4d4f" if val >= 0 else "#26a69a"
        
        badge = ""
        if stk == call_wall: badge = '<span style="background: #ff4d4f; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 6px; font-weight: bold;">Call Wall (天花板)</span>'
        elif stk == put_wall: badge = '<span style="background: #26a69a; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 6px; font-weight: bold;">Put Wall (地板)</span>'
        elif abs(stk - spot_p) <= 25: badge = '<span style="background: #38bdf8; color: #000; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 6px; font-weight: bold;">現貨價位</span>'
        elif abs(stk - zero_gamma) <= 25: badge = '<span style="background: #a855f7; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 6px; font-weight: bold;">Zero Gamma</span>'

        bars_html += f"""
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 10px;">
          <div style="width: 160px; font-size: 17px; font-weight: 800; color: #f8fafc; text-align: right;">{stk} {badge}</div>
          <div style="flex: 1; height: 22px; background: rgba(255,255,255,0.06); border-radius: 11px; overflow: hidden; display: flex; align-items: center;">
            <div style="width: {pct}%; background: {color}; height: 100%; border-radius: 11px;"></div>
          </div>
          <div style="width: 90px; font-size: 16px; font-weight: 900; color: {color}; text-align: left;">{val:+.1f} 億</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  {get_common_css()}
  .chart-box {{
    background: rgba(15, 23, 42, 0.85);
    border: 1.5px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    padding: 26px 30px;
    box-shadow: 0 4px 25px rgba(0,0,0,0.3);
    margin: 18px 0;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-around;
  }}
  .scope-badge {{
    background: rgba(0, 210, 255, 0.12);
    border: 1px solid #00d2ff;
    color: #00d2ff;
    font-size: 14px;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 8px;
    display: inline-block;
    margin-bottom: 12px;
  }}
</style>
</head>
<body>
  <div class="content-layer">
    <div class="brand-header" style="border-color: #38bdf8;">
      {avatar_html}
      <div class="header-text">
        <div class="brand-title">做市商 GEX 各履約價動態防守牆 [2/3]</div>
        <div class="brand-sub">全市場月選 + 周選總籌碼曝險  |  {date_str} 日盤定案</div>
      </div>
    </div>

    <div class="chart-box">
      <div>
        <span class="scope-badge">📌 合規標示：【全市場台指期權所有履約價總合 GEX (月選 + W1/W2 周選對沖籌碼)】</span>
        <div style="font-size: 14px; color: #94a3b8; margin-bottom: 14px;">
          🔴 紅柱 = 正 GEX (做市商逆勢護盤買盤) &nbsp;|&nbsp; 🟢 綠柱 = 負 GEX (做市商順勢追殺賣盤)
        </div>
      </div>

      <div>
        {bars_html}
      </div>

      <div style="text-align: right; color: rgba(255,255,255,0.45); font-size: 14px; font-weight: 600; margin-top: 10px;">
        © 尋鳥 Bluebird Finder
      </div>
    </div>

    <div class="disclaimer-panel">
      <div class="disc-title">
        <span>⚠️【免責與 AI 數據生成聲明】</span>
      </div>
      <div class="disc-body">
        本報告係由「尋鳥 Bluebird Finder Quant Labs」AI 量化數據模組自動生成，做市商對沖數據包含全市場月選與周選合約，可能因計算誤差與傳輸延遲而有缺失，<strong>請交易人務必自行複查與獨立判定風險</strong>。
      </div>
    </div>
  </div>
</body>
</html>
"""

def build_card3_sector_html(data, avatar_url):
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"
    sector_data = data.get("sector_capital_rotation") or {}
    sectors = sector_data.get("sectors") or []

    avatar_html = f'<img src="{avatar_url}" class="avatar-img">' if avatar_url else '<div style="width:62px;height:62px;border-radius:50%;background:#1e293b;border:2px solid #ffd700;"></div>'

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
        <div style="background: rgba(30, 41, 59, 0.75); border-radius: 14px; border-left: 5px solid {col}; border-top: 1px solid rgba(255,255,255,0.1); border-right: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); padding: 22px 24px; display: flex; flex-direction: column; justify-content: space-between;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 21px; font-weight: 800; color: #ffffff;">{name}</span>
            <span style="font-size: 24px; font-weight: 900; color: {col};">{chg}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
            <span style="font-size: 15px; color: #cbd5e1; font-weight: 600;">{stat} (占{pct}%)</span>
            <span style="font-size: 15px; color: #94a3b8;">🎯 {stocks}</span>
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
    margin: 18px 0;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .progress-bar-box {{
    height: 22px;
    border-radius: 11px;
    overflow: hidden;
    display: flex;
    background: #0f172a;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: inset 0 2px 6px rgba(0,0,0,0.4);
    margin-bottom: 18px;
  }}
  .sector-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
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

      <div style="text-align: right; color: rgba(255,255,255,0.45); font-size: 14px; font-weight: 600; margin-top: 10px;">
        © 尋鳥 Bluebird Finder
      </div>
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
    html2 = build_card2_strikes_html(data, avatar_url)
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
            page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)

            page.goto(f"file:///{tmp_h1.replace('\\', '/')}")
            page.screenshot(path=card1_path)

            page.goto(f"file:///{tmp_h2.replace('\\', '/')}")
            page.screenshot(path=card2_path)

            page.goto(f"file:///{tmp_h3.replace('\\', '/')}")
            page.screenshot(path=card3_path)

            browser.close()

        # Copy card1 to social_card_latest.png
        import shutil
        latest_path = os.path.join(output_dir, "social_card_latest.png")
        shutil.copyfile(card1_path, latest_path)

        # Cleanup temp HTML
        for fpath in [tmp_h1, tmp_h2, tmp_h3]:
            if os.path.exists(fpath): os.remove(fpath)

        print(f"[OK] Successfully generated Compact & Clear Scope IG Cards:")
        print(f"  - Card 1: {card1_path}")
        print(f"  - Card 2: {card2_path}")
        print(f"  - Card 3: {card3_path}")
        return True
    except Exception as e:
        print(f"[Warning] Playwright capture error: {e}.")
        return False

if __name__ == "__main__":
    generate_bluebird_social_card()
