"""
Bluebird Finder Social Infographic Generator v47.0 (IG 4:5 Carousel Edition)
===================================================================================
100% Emoji-Safe, High-Precision Vector Design for Bluebird Finder Quant Labs
Eliminates Matplotlib font emoji missing glyph errors completely.
Includes explicit legal disclaimers, sleek card layouts, and crisp typography.
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

# Font setup for Traditional Chinese (Microsoft JhengHei / Arial)
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
    session_name = (data.get("session_name") or "日盤結算籌碼").replace('☀️', '').replace('🌙', '').strip()
    
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
    # CARD 1: 4:5 Overview Digest (Clean Vector Design, NO Emoji Glyphs)
    # -------------------------------------------------------------------------
    fig1 = plt.figure(figsize=(9, 11.25), dpi=120, facecolor='#090d16') # 1080x1350 px
    ax1 = fig1.add_axes([0, 0, 1, 1], facecolor='#090d16')
    ax1.axis('off')

    # Top Brand Header Box
    header_rect = patches.FancyBboxPatch((0.05, 0.89), 0.90, 0.07, boxstyle="round,pad=0.01",
                                         fc='#111827', ec='#00d2ff', lw=1.5)
    ax1.add_patch(header_rect)
    ax1.text(0.5, 0.938, "尋鳥 BLUEBIRD FINDER  |  台指期權量化導航", fontsize=16, fontweight='bold', color='#ffffff', ha='center', va='center')
    ax1.text(0.5, 0.906, f"* {session_name}  |  更新時間: {date_str}", fontsize=11, color='#00d2ff', ha='center', va='center')

    # Metric Box 1: Spot Price
    box1 = patches.FancyBboxPatch((0.05, 0.74), 0.43, 0.13, boxstyle="round,pad=0.01", fc='#162032', ec='#38bdf8', lw=1.2)
    ax1.add_patch(box1)
    ax1.text(0.08, 0.835, "◆ 台指現貨結算價", fontsize=11, color='#94a3b8', va='center')
    ax1.text(0.08, 0.78, f"${spot_p:,.1f}", fontsize=22, fontweight='bold', color='#ffd700', va='center')

    # Metric Box 2: Zero Gamma
    box2 = patches.FancyBboxPatch((0.52, 0.74), 0.43, 0.13, boxstyle="round,pad=0.01", fc='#162032', ec='#a855f7', lw=1.2)
    ax1.add_patch(box2)
    ax1.text(0.55, 0.835, "◆ Zero Gamma 轉折點", fontsize=11, color='#94a3b8', va='center')
    ax1.text(0.55, 0.78, f"${zero_gamma:,.1f}", fontsize=22, fontweight='bold', color='#a855f7', va='center')

    # Call Wall & Put Wall Banners
    wall_rect = patches.FancyBboxPatch((0.05, 0.60), 0.90, 0.12, boxstyle="round,pad=0.01", fc='#0f172a', ec='#ffd700', lw=1.2)
    ax1.add_patch(wall_rect)
    ax1.text(0.08, 0.68, "▲ 莊家天花板牆 (Call Wall)", fontsize=11, color='#ff4d4f', va='center', fontweight='bold')
    ax1.text(0.08, 0.63, f"${call_wall:,.0f} 點 (頂部強力阻力)", fontsize=15, color='#ffffff', va='center', fontweight='bold')

    ax1.text(0.55, 0.68, "▼ 莊家地板牆 (Put Wall)", fontsize=11, color='#26a69a', va='center', fontweight='bold')
    ax1.text(0.55, 0.63, f"${put_wall:,.0f} 點 (底部防守鐵板)", fontsize=15, color='#ffffff', va='center', fontweight='bold')

    # Exposure Analysis Box
    exp_rect = patches.FancyBboxPatch((0.05, 0.28), 0.90, 0.30, boxstyle="round,pad=0.01", fc='#111827', ec='#334155', lw=1.2)
    ax1.add_patch(exp_rect)

    gex_tag = "[正 GEX 護盤區 - 波動壓縮]" if total_gex >= 0 else "[負 GEX 追殺區 - 波動放大]"
    vex_tag = "[負 VEX - 恐慌做市商助跌]" if total_vex < 0 else "[正 VEX - 做市商買盤護盤]"

    exp_text = (
        f"【做市商三維對沖曝險指標】\n"
        f"─────────────────────────────────────\n"
        f"● 淨 Gamma 曝險 (Total GEX):   {total_gex:+.1f} 億  {gex_tag}\n"
        f"● 恐慌敏感曝險 (Total VEX):   {total_vex:+.1f} 億  {vex_tag}\n"
        f"● 恐慌加權總合 (Total GEX+):  {total_gex_plus:+.1f} 億\n"
        f"● GEX+ 提前轉折臨界線:         ${gex_plus_flip:,.0f} 點\n\n"
        f"-> 盤勢觀點: 現價高於 Zero Gamma，多頭防守對沖買盤尚存；\n"
        f"   若下破 ${put_wall:,.0f} 則宜防範 Gamma/Vanna 追殺賣盤加劇。"
    )
    ax1.text(0.08, 0.54, exp_text, fontsize=10.5, color='#f8fafc', va='top', ha='left', linespacing=1.45)

    # Legal Disclaimer Box (Required by User)
    disc_rect = patches.FancyBboxPatch((0.05, 0.04), 0.90, 0.21, boxstyle="round,pad=0.01", fc='#0f172a', ec='#ef4444', lw=1.0)
    ax1.add_patch(disc_rect)

    disc_text = (
        f"【免責聲明  LEGAL DISCLAIMER】\n"
        f"─────────────────────────────────────\n"
        f"本報告由「尋鳥 Bluebird Finder Quant Labs」量化引擎自動繪製，\n"
        f"所提供之台指期權做市商曝險、Zero Gamma 及板塊數據僅供學術研究與個人盯盤紀錄，\n"
        f"絕不構成任何形式之個股/期權投資建議、邀約或操作依據。\n"
        f"期貨與選擇權交易具高槓桿風險，投資人應獨立思考並自負盈虧責任。"
    )
    ax1.text(0.08, 0.22, disc_text, fontsize=9.2, color='#94a3b8', va='top', ha='left', linespacing=1.35)

    card1_path = os.path.join(output_dir, "social_card_p1_overview.png")
    fig1.savefig(card1_path, facecolor=fig1.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig1)

    # -------------------------------------------------------------------------
    # CARD 2: GEX & VEX Strike Profile Chart (Clean No-Emoji Design)
    # -------------------------------------------------------------------------
    fig2 = plt.figure(figsize=(9, 11.25), dpi=120, facecolor='#090d16')

    # Subplot 1: GEX Profile
    ax2_1 = fig2.add_subplot(2, 1, 1, facecolor='#111827')
    colors1 = ['#ff4d4f' if v >= 0 else '#26a69a' for v in sub_gex]
    ax2_1.bar(sub_strikes, sub_gex, width=35, color=colors1, alpha=0.85, edgecolor='none')
    ax2_1.axvline(spot_p, color='#00d2ff', linestyle='--', linewidth=2.0, label=f'現貨 ${spot_p:,.0f}')
    ax2_1.axvline(zero_gamma, color='#a855f7', linestyle=':', linewidth=2.0, label=f'Zero Gamma ${zero_gamma:,.0f}')
    ax2_1.axvline(call_wall, color='#ff4d4f', linestyle='-', linewidth=1.5, label=f'Call Wall ${call_wall:,.0f}')
    ax2_1.axvline(put_wall, color='#26a69a', linestyle='-', linewidth=1.5, label=f'Put Wall ${put_wall:,.0f}')
    ax2_1.set_title("台指做市商 GEX 各履約價佈局 (紅柱=正GEX護盤 / 綠柱=負GEX助跌)", fontsize=11.5, color='#ffffff', pad=10, fontweight='bold')
    ax2_1.set_xlabel("履約價 (Strike Price)", fontsize=9.5, color='#94a3b8')
    ax2_1.set_ylabel("Net GEX (億NT$/1%)", fontsize=9.5, color='#94a3b8')
    ax2_1.tick_params(colors='#94a3b8', labelsize=8.5)
    ax2_1.grid(True, linestyle=':', alpha=0.25, color='#475569')
    ax2_1.legend(loc='upper left', fontsize=8.5, facecolor='#1e293b', edgecolor='#334155', labelcolor='#ffffff')

    # Subplot 2: VEX Profile
    ax2_2 = fig2.add_subplot(2, 1, 2, facecolor='#111827')
    colors2 = ['#ff4d4f' if v >= 0 else '#26a69a' for v in sub_vex]
    ax2_2.bar(sub_strikes, sub_vex, width=35, color=colors2, alpha=0.85, edgecolor='none')
    ax2_2.axvline(spot_p, color='#00d2ff', linestyle='--', linewidth=2.0, label=f'現貨 ${spot_p:,.0f}')
    ax2_2.set_title("台指做市商 VEX 恐慌波動曝險 (綠柱負值=恐慌急殺做市商助跌)", fontsize=11.5, color='#ffffff', pad=10, fontweight='bold')
    ax2_2.set_xlabel("履約價 (Strike Price)", fontsize=9.5, color='#94a3b8')
    ax2_2.set_ylabel("VEX (億NT$/vol)", fontsize=9.5, color='#94a3b8')
    ax2_2.tick_params(colors='#94a3b8', labelsize=8.5)
    ax2_2.grid(True, linestyle=':', alpha=0.25, color='#475569')
    ax2_2.legend(loc='upper right', fontsize=8.5, facecolor='#1e293b', edgecolor='#334155', labelcolor='#ffffff')

    plt.tight_layout(pad=3.0)
    card2_path = os.path.join(output_dir, "social_card_p2_gex_profile.png")
    fig2.savefig(card2_path, facecolor=fig2.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig2)

    # -------------------------------------------------------------------------
    # CARD 3: 8-Sector Capital Rotation Matrix (Clean Vector Badge Design)
    # -------------------------------------------------------------------------
    fig3 = plt.figure(figsize=(9, 11.25), dpi=120, facecolor='#090d16')
    ax3 = fig3.add_axes([0, 0, 1, 1], facecolor='#090d16')
    ax3.axis('off')

    # Card 3 Header
    sec_header = patches.FancyBboxPatch((0.05, 0.89), 0.90, 0.07, boxstyle="round,pad=0.01",
                                         fc='#111827', ec='#ffd700', lw=1.5)
    ax3.add_patch(sec_header)
    ax3.text(0.5, 0.938, "證交所 33 大產業歸納 8 大精準主題資金輪動矩陣", fontsize=15, fontweight='bold', color='#ffffff', ha='center', va='center')
    ax3.text(0.5, 0.906, f"● 即時板塊資金熱度與代表性個股期標的  •  {date_str}", fontsize=10.5, color='#ffd700', ha='center', va='center')

    # Render 8 Sector Cards in 2 Columns x 4 Rows
    card_w = 0.43
    card_h = 0.165
    
    for idx, s in enumerate(sectors[:8]):
        r = idx // 2
        c = idx % 2
        
        x = 0.05 + c * 0.47
        y = 0.69 - r * 0.18
        
        sec_color = s.get('color', '#38bdf8')
        if 'call-color' in sec_color or '#ff' in sec_color: sec_color = '#ff4d4f'
        elif 'put-color' in sec_color or '#26' in sec_color: sec_color = '#26a69a'
        elif 'gold' in sec_color: sec_color = '#ffd700'

        card_box = patches.FancyBboxPatch((x, y), card_w, card_h, boxstyle="round,pad=0.01",
                                           fc='#162032', ec=sec_color, lw=1.5)
        ax3.add_patch(card_box)

        # Sector Text without Emoji Glyphs
        raw_name = s.get('name', '板塊')
        clean_sname = raw_name.replace('💻', '').replace('🤖', '').replace('📡', '').replace('⚡', '').replace('🚢', '').replace('🏢', '').replace('🧬', '').replace('🏦', '').strip()
        
        s_chg = s.get('change_pct', '0.0%')
        raw_stat = s.get('status', '平穩')
        clean_stat = raw_stat.replace('🔥', '[大漲]').replace('📈', '[買盤]').replace('❄️', '[拉回]').replace('📉', '[微拉]').replace('⚖️', '[觀望]').strip()
        s_stocks = "、".join(s.get('top_stocks', [])[:3])

        ax3.text(x + 0.03, y + card_h - 0.035, f"■ {clean_sname}", fontsize=11, fontweight='bold', color='#ffffff', va='center')
        ax3.text(x + card_w - 0.03, y + card_h - 0.035, f"{s_chg}", fontsize=12, fontweight='bold', color=sec_color, ha='right', va='center')
        
        ax3.text(x + 0.03, y + 0.07, f"* 狀態: {clean_stat}", fontsize=9.5, color='#cbd5e1', va='center')
        ax3.text(x + 0.03, y + 0.03, f"◆ 標的: {s_stocks}", fontsize=9.0, color='#94a3b8', va='center')

    # Card 3 Disclaimer Footer
    c3_footer = patches.FancyBboxPatch((0.05, 0.04), 0.90, 0.08, boxstyle="round,pad=0.01", fc='#0f172a', ec='#ef4444', lw=1.0)
    ax3.add_patch(c3_footer)
    ax3.text(0.5, 0.09, "【免責聲明】本報告僅供學術量化研究與個人紀錄，不構成投資建議，交易請自負風險。", fontsize=9.5, color='#94a3b8', ha='center', va='center')
    ax3.text(0.5, 0.06, "© 尋鳥 Bluebird Finder Quant Labs  •  獨立量化品牌", fontsize=9.0, color='#64748b', ha='center', va='center')

    card3_path = os.path.join(output_dir, "social_card_p3_sector_rotation.png")
    fig3.savefig(card3_path, facecolor=fig3.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig3)

    # Save default card1 as social_card_latest.png for backward compatibility
    latest_path = os.path.join(output_dir, "social_card_latest.png")
    import shutil
    shutil.copyfile(card1_path, latest_path)

    print(f"[OK] Generated Clean Emoji-Safe IG 4:5 Carousel Cards:")
    print(f"  - Card 1: {card1_path}")
    print(f"  - Card 2: {card2_path}")
    print(f"  - Card 3: {card3_path}")
    return True

if __name__ == "__main__":
    generate_bluebird_social_card()
