"""
Bluebird Finder Social Infographic Generator v46.0 (IG & Threads Carousel Optimized)
===================================================================================
100% Original Brand Design for Bluebird Finder Quant Labs (尋鳥台指期權量化實驗室)
Generates high-resolution 4:5 vertical (1080x1350 px) IG carousel multi-card sets.
Zero third-party IP copycats. Clean, modern, high-contrast dark quant aesthetic.
"""

import os
import sys
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Enable UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Try setting fonts for Traditional Chinese support
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DFKai-SB', 'SimHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

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
    
    gex_list = data.get("total_gex") or []
    sector_data = data.get("sector_capital_rotation") or {}
    sectors = sector_data.get("sectors") or []

    strikes = [item["strike"] for item in gex_list]
    net_gex = [item.get("net_gex", 0) for item in gex_list]
    vex_vals = [item.get("vex", 0) for item in gex_list]

    # Filter strikes around spot +- 2000
    sub_indices = [i for i, k in enumerate(strikes) if abs(k - spot_p) <= 2000]
    if sub_indices:
        sub_strikes = [strikes[i] for i in sub_indices]
        sub_gex = [net_gex[i] for i in sub_indices]
        sub_vex = [vex_vals[i] for i in sub_indices]
    else:
        sub_strikes = strikes[:30]
        sub_gex = net_gex[:30]
        sub_vex = vex_vals[:30]

    os.makedirs(output_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # CARD 1: 4:5 Vertical Main Digest (IG Carousel Card 1)
    # -------------------------------------------------------------------------
    fig1 = plt.figure(figsize=(9, 11.25), dpi=120, facecolor='#0b0f19') # 1080x1350 px
    ax1 = fig1.add_axes([0, 0, 1, 1], facecolor='#0b0f19')
    ax1.axis('off')

    # Top Brand Header Box
    header_rect = patches.FancyBboxPatch((0.05, 0.88), 0.90, 0.08, boxstyle="round,pad=0.01",
                                         fc='#111827', ec='#00f2fe', lw=1.5)
    ax1.add_patch(header_rect)
    ax1.text(0.5, 0.935, "尋鳥 BLUEBIRD FINDER • 期權量化快報", fontsize=17, fontweight='bold', color='#ffffff', ha='center', va='center')
    ax1.text(0.5, 0.898, f"{session_name}  |  更新時間: {date_str}", fontsize=11, color='#00f2fe', ha='center', va='center')

    # Main Metrics Grid Cards
    # Card A: Spot Price
    card_a = patches.FancyBboxPatch((0.05, 0.72), 0.43, 0.14, boxstyle="round,pad=0.01", fc='#1e293b', ec='#38bdf8', lw=1.2)
    ax1.add_patch(card_a)
    ax1.text(0.08, 0.825, "🎯 台指現貨結算價", fontsize=11, color='#94a3b8', va='center')
    ax1.text(0.08, 0.765, f"${spot_p:,.1f}", fontsize=22, fontweight='bold', color='#ffd700', va='center')

    # Card B: Zero Gamma / GEX Flip
    card_b = patches.FancyBboxPatch((0.52, 0.72), 0.43, 0.14, boxstyle="round,pad=0.01", fc='#1e293b', ec='#a855f7', lw=1.2)
    ax1.add_patch(card_b)
    ax1.text(0.55, 0.825, "⚖️ Zero Gamma 轉折點", fontsize=11, color='#94a3b8', va='center')
    ax1.text(0.55, 0.765, f"${zero_gamma:,.1f}", fontsize=22, fontweight='bold', color='#a855f7', va='center')

    # Call Wall & Put Wall Banners
    wall_rect = patches.FancyBboxPatch((0.05, 0.58), 0.90, 0.12, boxstyle="round,pad=0.01", fc='#0f172a', ec='#ffd700', lw=1.5)
    ax1.add_patch(wall_rect)
    ax1.text(0.08, 0.66, "🧱 莊家天花板 (Call Wall)", fontsize=11, color='#ff4d4f', va='center', fontweight='bold')
    ax1.text(0.08, 0.61, f"${call_wall:,.0f} 點 (壓力強固)", fontsize=16, color='#ffffff', va='center', fontweight='bold')

    ax1.text(0.55, 0.66, "🛋️ 莊家地板牆 (Put Wall)", fontsize=11, color='#26a69a', va='center', fontweight='bold')
    ax1.text(0.55, 0.61, f"${put_wall:,.0f} 點 (鐵板防守)", fontsize=16, color='#ffffff', va='center', fontweight='bold')

    # Quant Exposure Summary
    quant_rect = patches.FancyBboxPatch((0.05, 0.30), 0.90, 0.26, boxstyle="round,pad=0.01", fc='#111827', ec='#334155', lw=1.2)
    ax1.add_patch(quant_rect)
    
    gex_tag = "🔴 正 GEX 護盤區 (波動壓縮)" if total_gex >= 0 else "🟢 負 GEX 追殺區 (波動放大)"
    vex_tag = "🟢 負 VEX (恐慌做市商助跌)" if total_vex < 0 else "🔴 正 VEX (做市商買盤護盤)"

    quant_text = (
        f"📊 做市商三大動態曝光指標 (GEX / VEX / GEX+)\n"
        f"─────────────────────────────────────\n"
        f"• 淨 Gamma 曝險 (Total GEX):   {total_gex:+.1f} 億  ({gex_tag})\n"
        f"• 恐慌敏感曝險 (Total VEX):   {total_vex:+.1f} 億  ({vex_tag})\n"
        f"• 恐慌加權總合 (Total GEX+):  {total_gex_plus:+.1f} 億\n"
        f"• GEX+ 提前轉折臨界點:         ${gex_plus_flip:,.0f} 點\n\n"
        f"💡 量化解讀: 現價高於 Zero Gamma，多頭防守對沖盤尚在；\n"
        f"   若跌破 ${put_wall:,.0f} 則宜防範負 Gamma 追殺賣盤。"
    )
    ax1.text(0.08, 0.52, quant_text, fontsize=11, color='#f8fafc', va='top', ha='left', linespacing=1.45)

    # Footer Watermark
    footer_rect = patches.FancyBboxPatch((0.05, 0.05), 0.90, 0.22, boxstyle="round,pad=0.01", fc='#0f172a', ec='#00f2fe', lw=1.0)
    ax1.add_patch(footer_rect)
    
    sec_preview = "、".join([s.get('name', '').split('與')[0] for s in sectors[:4]])
    footer_text = (
        f"🦅 尋鳥 Bluebird Finder Quant Labs 專屬量化報告 [1/3]\n"
        f"─────────────────────────────────────\n"
        f"🔥 今日 8 大動態資金輪動熱點: {sec_preview}...\n"
        f"👉 向左滑動查看 [全履約價 GEX 柱狀圖] 與 [8 大板塊即時張力]\n"
        f"⚠️ 本報告由尋鳥量化引擎自動繪製，僅供盯盤參考，非投資建議。"
    )
    ax1.text(0.08, 0.24, footer_text, fontsize=10.5, color='#cbd5e1', va='top', ha='left', linespacing=1.4)

    card1_path = os.path.join(output_dir, "social_card_p1_overview.png")
    fig1.savefig(card1_path, facecolor=fig1.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig1)

    # -------------------------------------------------------------------------
    # CARD 2: 4:5 Vertical GEX & VEX Strikes Profile Chart (IG Carousel Card 2)
    # -------------------------------------------------------------------------
    fig2 = plt.figure(figsize=(9, 11.25), dpi=120, facecolor='#0b0f19')
    
    # Subplot 1: GEX Strike Profile
    ax2_1 = fig2.add_subplot(2, 1, 1, facecolor='#111827')
    colors1 = ['#ff4d4f' if v >= 0 else '#26a69a' for v in sub_gex]
    ax2_1.bar(sub_strikes, sub_gex, width=35, color=colors1, alpha=0.85, edgecolor='none')
    ax2_1.axvline(spot_p, color='#00d2ff', linestyle='--', linewidth=2.0, label=f'現貨 {spot_p:,.0f}')
    ax2_1.axvline(zero_gamma, color='#a855f7', linestyle=':', linewidth=2.0, label=f'Zero Gamma {zero_gamma:,.0f}')
    ax2_1.axvline(call_wall, color='#ff4d4f', linestyle='-', linewidth=1.5, label=f'Call Wall {call_wall:,.0f}')
    ax2_1.axvline(put_wall, color='#26a69a', linestyle='-', linewidth=1.5, label=f'Put Wall {put_wall:,.0f}')
    ax2_1.set_title("台指做市商 GEX 各履約價佈局 (🔴正=護盤牆 / 🟢負=助跌)", fontsize=12, color='#ffffff', pad=10, fontweight='bold')
    ax2_1.set_xlabel("履約價 (Strike Price)", fontsize=10, color='#94a3b8')
    ax2_1.set_ylabel("Net GEX (億NT$/1%)", fontsize=10, color='#94a3b8')
    ax2_1.tick_params(colors='#94a3b8', labelsize=9)
    ax2_1.grid(True, linestyle=':', alpha=0.25, color='#475569')
    ax2_1.legend(loc='upper left', fontsize=9, facecolor='#1e293b', edgecolor='#334155', labelcolor='#ffffff')

    # Subplot 2: VEX Strike Profile
    ax2_2 = fig2.add_subplot(2, 1, 2, facecolor='#111827')
    colors2 = ['#ff4d4f' if v >= 0 else '#26a69a' for v in sub_vex]
    ax2_2.bar(sub_strikes, sub_vex, width=35, color=colors2, alpha=0.85, edgecolor='none')
    ax2_2.axvline(spot_p, color='#00d2ff', linestyle='--', linewidth=2.0, label=f'現貨 {spot_p:,.0f}')
    ax2_2.set_title("台指做市商 VEX 恐慌波動曝險 (🟢負值=恐慌急殺助跌)", fontsize=12, color='#ffffff', pad=10, fontweight='bold')
    ax2_2.set_xlabel("履約價 (Strike Price)", fontsize=10, color='#94a3b8')
    ax2_2.set_ylabel("VEX (億NT$/vol)", fontsize=10, color='#94a3b8')
    ax2_2.tick_params(colors='#94a3b8', labelsize=9)
    ax2_2.grid(True, linestyle=':', alpha=0.25, color='#475569')
    ax2_2.legend(loc='upper right', fontsize=9, facecolor='#1e293b', edgecolor='#334155', labelcolor='#ffffff')

    plt.tight_layout(pad=3.0)
    card2_path = os.path.join(output_dir, "social_card_p2_gex_profile.png")
    fig2.savefig(card2_path, facecolor=fig2.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig2)

    # -------------------------------------------------------------------------
    # CARD 3: 4:5 Vertical 8-Sector Capital Rotation Matrix (IG Carousel Card 3)
    # -------------------------------------------------------------------------
    fig3 = plt.figure(figsize=(9, 11.25), dpi=120, facecolor='#0b0f19')
    ax3 = fig3.add_axes([0, 0, 1, 1], facecolor='#0b0f19')
    ax3.axis('off')

    # Card 3 Header
    sec_header = patches.FancyBboxPatch((0.05, 0.88), 0.90, 0.08, boxstyle="round,pad=0.01",
                                         fc='#111827', ec='#ffd700', lw=1.5)
    ax3.add_patch(sec_header)
    ax3.text(0.5, 0.935, "📊 證交所 33 大產業歸納 8 大精準主題資金輪動", fontsize=16, fontweight='bold', color='#ffffff', ha='center', va='center')
    ax3.text(0.5, 0.898, f"即時板塊資金熱度與代表性個股期  •  {date_str}", fontsize=11, color='#ffd700', ha='center', va='center')

    # Render 8 Sector Cards in 2 Columns x 4 Rows
    row_count = 4
    col_count = 2
    card_w = 0.43
    card_h = 0.17
    
    for idx, s in enumerate(sectors[:8]):
        r = idx // col_count
        c = idx % col_count
        
        x = 0.05 + c * 0.47
        y = 0.67 - r * 0.19
        
        sec_color = s.get('color', '#38bdf8')
        if 'call-color' in sec_color or '#ff' in sec_color: sec_color = '#ff4d4f'
        elif 'put-color' in sec_color or '#26' in sec_color: sec_color = '#26a69a'
        elif 'gold' in sec_color: sec_color = '#ffd700'

        card_box = patches.FancyBboxPatch((x, y), card_w, card_h, boxstyle="round,pad=0.01",
                                           fc='#1e293b', ec=sec_color, lw=1.5)
        ax3.add_patch(card_box)

        # Sector Text
        s_name = s.get('name', '板塊')
        s_chg = s.get('change_pct', '0.0%')
        s_stat = s.get('status', '平穩')
        s_stocks = "、".join(s.get('top_stocks', [])[:3])

        ax3.text(x + 0.03, y + card_h - 0.035, s_name, fontsize=11, fontweight='bold', color='#ffffff', va='center')
        ax3.text(x + card_w - 0.03, y + card_h - 0.035, f"{s_chg}", fontsize=12, fontweight='bold', color=sec_color, ha='right', va='center')
        
        ax3.text(x + 0.03, y + 0.07, f"{s_stat}", fontsize=9.5, color='#cbd5e1', va='center')
        ax3.text(x + 0.03, y + 0.03, f"🎯 標的: {s_stocks}", fontsize=9.0, color='#94a3b8', va='center')

    # Card 3 Footer Watermark
    c3_footer = patches.FancyBboxPatch((0.05, 0.04), 0.90, 0.06, boxstyle="round,pad=0.01", fc='#0f172a', ec='#334155', lw=1.0)
    ax3.add_patch(c3_footer)
    ax3.text(0.5, 0.07, "© 尋鳥 Bluebird Finder Quant Labs  •  獨立量化品牌  •  盤後/盤中精準掃描", fontsize=10, color='#94a3b8', ha='center', va='center')

    card3_path = os.path.join(output_dir, "social_card_p3_sector_rotation.png")
    fig3.savefig(card3_path, facecolor=fig3.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig3)

    # Save default card1 as social_card_latest.png for backward compatibility
    latest_path = os.path.join(output_dir, "social_card_latest.png")
    import shutil
    shutil.copyfile(card1_path, latest_path)

    print(f"[OK] Generated Bluebird Finder IG 4:5 Carousel Card Set (3 Cards):")
    print(f"  - Card 1 (Overview): {card1_path}")
    print(f"  - Card 2 (GEX/VEX Profile): {card2_path}")
    print(f"  - Card 3 (8-Sector Rotation): {card3_path}")
    return True

if __name__ == "__main__":
    generate_bluebird_social_card()
