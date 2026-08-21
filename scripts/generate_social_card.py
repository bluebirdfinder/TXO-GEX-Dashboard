"""
Bluebird Finder Social Infographic Generator v48.0 (Playwright Web-Native 4:5 IG Edition)
===========================================================================================
100% Web Dashboard Design System Sync.
Renders HTML/CSS matching the exact front-end UI of TXO GEX Dashboard using Playwright.
Generates 3 high-resolution 4:5 vertical IG carousel cards (1080x1350 px) with native emojis,
glassmorphism cards, and explicit legal disclaimers.
"""

import os
import sys
import json
import time

# Enable UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def build_card1_html(data):
    spot_p = data.get("spot_price") or data.get("txf_price") or 45160.0
    zero_gamma = data.get("zero_gamma_level") or 45217.0
    gex_plus_flip = data.get("gex_plus_flip") or (zero_gamma - 50)
    total_gex = data.get("total_gex_val") or 8.5
    total_vex = data.get("total_vex") or -6.2
    total_gex_plus = data.get("total_gex_plus") or 2.3
    call_wall = data.get("call_wall_strike") or 45400
    put_wall = data.get("put_wall_strike") or 45000
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"
    session_name = data.get("session_name") or "☀️ 日盤結算籌碼"

    gex_tag = "🔴 正 GEX 護盤區 (波動壓縮)" if total_gex >= 0 else "🟢 負 GEX 追殺區 (波動放大)"
    vex_tag = "🟢 負 VEX (恐慌做市商助跌)" if total_vex < 0 else "🔴 正 VEX (做市商買盤護盤)"

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Noto+Sans+TC:wght@400;600;700;900&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1080px;
    height: 1350px;
    background: #090d16;
    font-family: 'Inter', 'Noto Sans TC', -apple-system, sans-serif;
    color: #f8fafc;
    padding: 40px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .brand-header {{
    background: rgba(15, 23, 42, 0.85);
    border: 1.5px solid #00f2fe;
    border-radius: 16px;
    padding: 24px 32px;
    text-align: center;
    box-shadow: 0 0 25px rgba(0, 242, 254, 0.15);
  }}
  .brand-title {{
    font-size: 32px;
    font-weight: 900;
    letter-spacing: 1px;
    color: #ffffff;
    margin-bottom: 6px;
  }}
  .brand-sub {{
    font-size: 18px;
    color: #00f2fe;
    font-weight: 600;
  }}
  .metrics-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }}
  .metric-card {{
    background: rgba(30, 41, 59, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
  }}
  .metric-label {{
    font-size: 18px;
    color: #94a3b8;
    margin-bottom: 8px;
    font-weight: 600;
  }}
  .metric-value {{
    font-size: 42px;
    font-weight: 800;
    color: #ffd700;
  }}
  .wall-panel {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid #ffd700;
    border-radius: 16px;
    padding: 26px 32px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }}
  .wall-box {{
    display: flex;
    flex-direction: column;
  }}
  .wall-title {{
    font-size: 19px;
    font-weight: 700;
    margin-bottom: 6px;
  }}
  .wall-val {{
    font-size: 34px;
    font-weight: 900;
    color: #ffffff;
  }}
  .exposure-panel {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    padding: 28px 32px;
    box-shadow: 0 4px 25px rgba(0,0,0,0.3);
  }}
  .exp-title {{
    font-size: 22px;
    font-weight: 800;
    color: #ffd700;
    margin-bottom: 16px;
    border-bottom: 1px dashed rgba(255,255,255,0.15);
    padding-bottom: 10px;
  }}
  .exp-row {{
    font-size: 20px;
    margin-bottom: 12px;
    line-height: 1.5;
    color: #e2e8f0;
  }}
  .disclaimer-panel {{
    background: rgba(15, 23, 42, 0.9);
    border: 1px solid rgba(239, 68, 68, 0.5);
    border-radius: 14px;
    padding: 20px 24px;
  }}
  .disc-title {{
    font-size: 17px;
    font-weight: 800;
    color: #ef4444;
    margin-bottom: 6px;
  }}
  .disc-body {{
    font-size: 14.5px;
    color: #94a3b8;
    line-height: 1.5;
  }}
</style>
</head>
<body>
  <div class="brand-header">
    <div class="brand-title">🦅 尋鳥 BLUEBIRD FINDER • 期權量化快報</div>
    <div class="brand-sub">{session_name} &nbsp;|&nbsp; 更新時間: {date_str}</div>
  </div>

  <div class="metrics-grid">
    <div class="metric-card" style="border-left: 5px solid #38bdf8;">
      <div class="metric-label">🎯 台指現貨結算價</div>
      <div class="metric-value" style="color: #ffd700;">${spot_p:,.1f}</div>
    </div>
    <div class="metric-card" style="border-left: 5px solid #a855f7;">
      <div class="metric-label">⚖️ Zero Gamma 轉折點</div>
      <div class="metric-value" style="color: #a855f7;">${zero_gamma:,.1f}</div>
    </div>
  </div>

  <div class="wall-panel">
    <div class="wall-box">
      <div class="wall-title" style="color: #ff4d4f;">🧱 莊家天花板 (Call Wall)</div>
      <div class="wall-val">${call_wall:,.0f} <span style="font-size: 17px; color: #ff4d4f; font-weight: 600;">(壓力強固)</span></div>
    </div>
    <div class="wall-box">
      <div class="wall-title" style="color: #26a69a;">🛋️ 莊家地板牆 (Put Wall)</div>
      <div class="wall-val">${put_wall:,.0f} <span style="font-size: 17px; color: #26a69a; font-weight: 600;">(防守鐵板)</span></div>
    </div>
  </div>

  <div class="exposure-panel">
    <div class="exp-title">📊 做市商三大動態曝光指標 (GEX / VEX / GEX+)</div>
    <div class="exp-row">• 淨 Gamma 曝險 (Total GEX): &nbsp;<strong style="color:#00f2fe;">{total_gex:+.1f} 億</strong> &nbsp;<span style="font-size: 17px; color: #94a3b8;">({gex_tag})</span></div>
    <div class="exp-row">• 恐慌敏感曝險 (Total VEX): &nbsp;<strong style="color:#26a69a;">{total_vex:+.1f} 億</strong> &nbsp;<span style="font-size: 17px; color: #94a3b8;">({vex_tag})</span></div>
    <div class="exp-row">• 恐慌加權總合 (Total GEX+): &nbsp;<strong style="color:#ffd700;">{total_gex_plus:+.1f} 億</strong></div>
    <div class="exp-row">• GEX+ 提前轉折臨界點: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<strong style="color:#a855f7;">${gex_plus_flip:,.0f} 點</strong></div>
  </div>

  <div class="disclaimer-panel">
    <div class="disc-title">⚠️【免責聲明  LEGAL DISCLAIMER】</div>
    <div class="disc-body">
      本報告由「尋鳥 Bluebird Finder Quant Labs」量化引擎自動繪製，所提供之台指期權做市商曝險與動態數據僅供學術研究與個人盯盤紀錄，絕不構成任何形式之投資建議、邀約或操作依據。期貨與選擇權交易具高風險，投資人應獨立思考並自負盈虧。
    </div>
  </div>
</body>
</html>
"""

def build_card3_sector_html(data):
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"
    sector_data = data.get("sector_capital_rotation") or {}
    sectors = sector_data.get("sectors") or []

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
        <div style="background: rgba(30, 41, 59, 0.75); border-radius: 12px; border-left: 5px solid {col}; border-top: 1px solid rgba(255,255,255,0.1); border-right: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); padding: 18px 20px; display: flex; flex-direction: column; justify-content: space-between;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 20px; font-weight: 800; color: #ffffff;">{name}</span>
            <span style="font-size: 22px; font-weight: 900; color: {col};">{chg}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Noto+Sans+TC:wght@400;600;700;900&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1080px;
    height: 1350px;
    background: #090d16;
    font-family: 'Inter', 'Noto Sans TC', -apple-system, sans-serif;
    color: #f8fafc;
    padding: 40px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .brand-header {{
    background: rgba(15, 23, 42, 0.85);
    border: 1.5px solid #ffd700;
    border-radius: 16px;
    padding: 24px 32px;
    text-align: center;
    box-shadow: 0 0 25px rgba(255, 215, 0, 0.15);
  }}
  .brand-title {{
    font-size: 30px;
    font-weight: 900;
    color: #ffffff;
    margin-bottom: 6px;
  }}
  .brand-sub {{
    font-size: 17px;
    color: #ffd700;
    font-weight: 600;
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
  .sector-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  .disclaimer-panel {{
    background: rgba(15, 23, 42, 0.9);
    border: 1px solid rgba(239, 68, 68, 0.5);
    border-radius: 14px;
    padding: 18px 24px;
  }}
  .disc-title {{
    font-size: 16px;
    font-weight: 800;
    color: #ef4444;
    margin-bottom: 4px;
  }}
  .disc-body {{
    font-size: 14px;
    color: #94a3b8;
    line-height: 1.45;
  }}
</style>
</head>
<body>
  <div class="brand-header">
    <div class="brand-title">📊 證交所 33 大產業歸納 8 大精準主題資金輪動矩陣</div>
    <div class="brand-sub">即時板塊資金熱度與代表性個股期  |  更新時間: {date_str}</div>
  </div>

  <div class="progress-bar-box">
    {progress_bars_html}
  </div>

  <div class="sector-grid">
    {sector_cards_html}
  </div>

  <div class="disclaimer-panel">
    <div class="disc-title">⚠️【免責聲明  LEGAL DISCLAIMER】</div>
    <div class="disc-body">
      本報告由「尋鳥 Bluebird Finder Quant Labs」量化引擎自動繪製，所提供之產業板塊資金輪動數據僅供學術研究與個人盯盤紀錄，絕不構成任何形式之投資建議。交易請獨立思考並自負風險。
    </div>
  </div>
</body>
</html>
"""

def build_card2_strikes_html(data):
    spot_p = data.get("spot_price") or data.get("txf_price") or 45160.0
    zero_gamma = data.get("zero_gamma_level") or 45217.0
    call_wall = data.get("call_wall_strike") or 45400
    put_wall = data.get("put_wall_strike") or 45000
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"
    
    gex_list = data.get("total_gex") or []
    strikes = [item["strike"] for item in gex_list]
    net_gex = [item.get("net_gex", 0) for item in gex_list]

    # Filter strikes within spot +- 1500
    sub_items = [item for item in gex_list if abs(item["strike"] - spot_p) <= 1500]
    if not sub_items: sub_items = gex_list[:20]

    max_val = max([abs(item.get("net_gex", 0)) for item in sub_items] + [10.0])

    bars_html = ""
    for item in sub_items:
        stk = item["strike"]
        val = item.get("net_gex", 0)
        pct = min(100, int(abs(val) / max_val * 100))
        color = "#ff4d4f" if val >= 0 else "#26a69a"
        
        badge = ""
        if stk == call_wall: badge = '<span style="background: #ff4d4f; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 6px;">Call Wall</span>'
        elif stk == put_wall: badge = '<span style="background: #26a69a; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 6px;">Put Wall</span>'
        elif abs(stk - spot_p) <= 25: badge = '<span style="background: #38bdf8; color: #000; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 6px;">現貨位階</span>'
        elif abs(stk - zero_gamma) <= 25: badge = '<span style="background: #a855f7; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 6px;">Zero Gamma</span>'

        bars_html += f"""
        <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 8px;">
          <div style="width: 130px; font-size: 16px; font-weight: 700; color: #f8fafc; text-align: right;">{stk} {badge}</div>
          <div style="flex: 1; height: 18px; background: rgba(255,255,255,0.05); border-radius: 9px; overflow: hidden; display: flex; align-items: center;">
            <div style="width: {pct}%; background: {color}; height: 100%; border-radius: 9px;"></div>
          </div>
          <div style="width: 80px; font-size: 15px; fontweight: 800; color: {color}; text-align: left;">{val:+.1f} 億</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Noto+Sans+TC:wght@400;600;700;900&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1080px;
    height: 1350px;
    background: #090d16;
    font-family: 'Inter', 'Noto Sans TC', -apple-system, sans-serif;
    color: #f8fafc;
    padding: 40px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .brand-header {{
    background: rgba(15, 23, 42, 0.85);
    border: 1.5px solid #38bdf8;
    border-radius: 16px;
    padding: 24px 32px;
    text-align: center;
    box-shadow: 0 0 25px rgba(56, 189, 248, 0.15);
  }}
  .brand-title {{
    font-size: 30px;
    font-weight: 900;
    color: #ffffff;
    margin-bottom: 6px;
  }}
  .brand-sub {{
    font-size: 17px;
    color: #38bdf8;
    font-weight: 600;
  }}
  .chart-box {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 4px 25px rgba(0,0,0,0.3);
  }}
  .disclaimer-panel {{
    background: rgba(15, 23, 42, 0.9);
    border: 1px solid rgba(239, 68, 68, 0.5);
    border-radius: 14px;
    padding: 18px 24px;
  }}
  .disc-title {{
    font-size: 16px;
    font-weight: 800;
    color: #ef4444;
    margin-bottom: 4px;
  }}
  .disc-body {{
    font-size: 14px;
    color: #94a3b8;
    line-height: 1.45;
  }}
</style>
</head>
<body>
  <div class="brand-header">
    <div class="brand-title">📈 台指做市商 GEX 各履約價動態防守牆</div>
    <div class="brand-sub">紅柱 = 正 GEX (莊家護盤防守)  |  綠柱 = 負 GEX (做市商助跌)  |  {date_str}</div>
  </div>

  <div class="chart-box">
    {bars_html}
  </div>

  <div class="disclaimer-panel">
    <div class="disc-title">⚠️【免責聲明  LEGAL DISCLAIMER】</div>
    <div class="disc-body">
      本報告由「尋鳥 Bluebird Finder Quant Labs」量化引擎自動繪製，所提供之台指期權做市商曝險與數據僅供學術研究與個人紀錄，絕不構成任何投資建議。交易請自負風險。
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

    with open(gex_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    html1 = build_card1_html(data)
    html2 = build_card2_strikes_html(data)
    html3 = build_card3_sector_html(data)

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

        print(f"[OK] Successfully rendered 3 Web-Native IG 4:5 Cards via Playwright:")
        print(f"  - Card 1 (Overview): {card1_path}")
        print(f"  - Card 2 (GEX Strike Wall): {card2_path}")
        print(f"  - Card 3 (8-Sector Rotation): {card3_path}")
        return True
    except Exception as e:
        print(f"[Warning] Playwright capture error: {e}.")
        return False

if __name__ == "__main__":
    generate_bluebird_social_card()
