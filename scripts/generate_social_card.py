"""
Bluebird Finder Social Infographic Card Generator v45.0 (IG & Threads Optimized)
===================================================================================
100% Original Brand Design for Bluebird Finder Quant Labs (尋鳥台指期權量化實驗室)
Generates high-resolution (2000x2000 PNG) 4-panel social media share cards.
Zero third-party IP references.
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

def generate_bluebird_social_card(gex_data_path=None, output_path=None):
    if gex_data_path is None:
        gex_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gex_data.json")
    if output_path is None:
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "social_card_latest.png")

    if not os.path.exists(gex_data_path):
        print(f"[Error] GEX data path not found: {gex_data_path}")
        return False

    with open(gex_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    spot_p = data.get("spot_price") or data.get("txf_price") or 44934.0
    zero_gamma = data.get("zero_gamma_level") or 44778.0
    gex_plus_flip = data.get("gex_plus_flip") or 44848.0
    total_gex = data.get("total_gex_val") or 19.4
    total_vex = data.get("total_vex") or -8.7
    total_gex_plus = data.get("total_gex_plus") or 10.7
    call_wall = data.get("call_wall_strike") or 46100
    put_wall = data.get("put_wall_strike") or 44500
    date_str = data.get("date") or data.get("last_updated") or "2026-08-21"

    gex_list = data.get("total_gex") or []
    if not gex_list:
        print("[Warning] No total_gex list found in JSON.")
        return False

    strikes = [item["strike"] for item in gex_list]
    net_gex = [item.get("net_gex", 0) for item in gex_list]
    vex_vals = [item.get("vex", 0) for item in gex_list]

    # Filter strikes within range of spot +- 3000
    sub_indices = [i for i, k in enumerate(strikes) if abs(k - spot_p) <= 3000]
    if sub_indices:
        sub_strikes = [strikes[i] for i in sub_indices]
        sub_gex = [net_gex[i] for i in sub_indices]
        sub_vex = [vex_vals[i] for i in sub_indices]
    else:
        sub_strikes = strikes
        sub_gex = net_gex
        sub_vex = vex_vals

    # Canvas setup (2000x2000 dark cyan/gold themed figure)
    fig = plt.figure(figsize=(12, 12), dpi=160, facecolor='#0a0e17')
    
    # Title Banner Area
    fig.suptitle("尋鳥 Bluebird Finder  •  台指造市商曝險地圖", 
                 fontsize=22, fontweight='bold', color='#ffffff', y=0.96)
    fig.text(0.5, 0.932, f"TXO GEX / VEX / GEX+  |  資料日期: {date_str}  |  現貨價格: ${spot_p:,.0f}", 
             fontsize=12, color='#00d2ff', ha='center')

    # Grid 1: GEX Profile (Top Left)
    ax1 = fig.add_subplot(2, 2, 1, facecolor='#111827')
    # Taiwan Standard Color Palette: Red (#ff4d4f) for positive, Green (#26a69a) for negative
    colors1 = ['#ff4d4f' if v >= 0 else '#26a69a' for v in sub_gex]
    ax1.bar(sub_strikes, sub_gex, width=35, color=colors1, alpha=0.85, edgecolor='none')
    ax1.axvline(spot_p, color='#00d2ff', linestyle='--', linewidth=1.8, label=f'現貨 {spot_p:,.0f}')
    ax1.axvline(zero_gamma, color='#ffd700', linestyle=':', linewidth=1.8, label=f'Zero Gamma {zero_gamma:,.0f}')
    ax1.set_title("台指 GEX 各履約價 (🔴正=護盤平穩 / 🟢負=助跌爆發)", fontsize=11, color='#e2e8f0', pad=10)
    ax1.set_xlabel("履約價", fontsize=9, color='#94a3b8')
    ax1.set_ylabel("GEX (億NT$/1%)", fontsize=9, color='#94a3b8')
    ax1.tick_params(colors='#94a3b8', labelsize=8)
    ax1.grid(True, linestyle=':', alpha=0.2, color='#475569')
    ax1.legend(loc='upper left', fontsize=8, facecolor='#1e293b', edgecolor='#334155', labelcolor='#ffffff')

    # Grid 2: VEX Profile (Top Right)
    ax2 = fig.add_subplot(2, 2, 2, facecolor='#111827')
    # Taiwan Standard Color Palette: Red (#ff4d4f) for positive VEX, Green (#26a69a) for negative VEX
    colors2 = ['#ff4d4f' if v >= 0 else '#26a69a' for v in sub_vex]
    ax2.bar(sub_strikes, sub_vex, width=35, color=colors2, alpha=0.85, edgecolor='none')
    ax2.axvline(spot_p, color='#00d2ff', linestyle='--', linewidth=1.8, label=f'現貨 {spot_p:,.0f}')
    ax2.set_title("台指 VEX 恐慌曝險 (🟢負值=恐慌助跌 / 🔴正值=護盤支撐)", fontsize=11, color='#e2e8f0', pad=10)
    ax2.set_xlabel("履約價", fontsize=9, color='#94a3b8')
    ax2.set_ylabel("VEX (億NT$/vol點)", fontsize=9, color='#94a3b8')
    ax2.tick_params(colors='#94a3b8', labelsize=8)
    ax2.grid(True, linestyle=':', alpha=0.2, color='#475569')
    ax2.legend(loc='upper right', fontsize=8, facecolor='#1e293b', edgecolor='#334155', labelcolor='#ffffff')

    # Grid 3: GEX vs GEX+ Curve (Bottom Left)
    ax3 = fig.add_subplot(2, 2, 3, facecolor='#111827')
    sim_x = [spot_p - 4000 + i * 100 for i in range(81)]
    sim_gex = [100 * math.tanh((x - zero_gamma) / 1200) for x in sim_x]
    sim_gex_plus = [100 * math.tanh((x - gex_plus_flip) / 1200) for x in sim_x]
    ax3.plot(sim_x, sim_gex, color='#38bdf8', linewidth=2.0, label='純 GEX 曲線')
    ax3.plot(sim_x, sim_gex_plus, color='#a855f7', linewidth=2.0, linestyle='-', label='GEX+ (含Vanna恐慌)')
    ax3.axhline(0, color='#64748b', linestyle='-', linewidth=0.8)
    ax3.axvline(spot_p, color='#00d2ff', linestyle='--', linewidth=1.5, label=f'現貨 {spot_p:,.0f}')
    ax3.axvline(gex_plus_flip, color='#ffd700', linestyle=':', linewidth=1.5, label=f'GEX+ Flip {gex_plus_flip:,.0f}')
    ax3.set_title("台指 GEX vs GEX+ 模擬曝光曲線", fontsize=11, color='#e2e8f0', pad=10)
    ax3.set_xlabel("假設指數點位", fontsize=9, color='#94a3b8')
    ax3.set_ylabel("曝險金額 (億NT$/1%)", fontsize=9, color='#94a3b8')
    ax3.tick_params(colors='#94a3b8', labelsize=8)
    ax3.grid(True, linestyle=':', alpha=0.2, color='#475569')
    ax3.legend(loc='lower right', fontsize=8, facecolor='#1e293b', edgecolor='#334155', labelcolor='#ffffff')

    # Grid 4: Summary Card & Watermark (Bottom Right)
    ax4 = fig.add_subplot(2, 2, 4, facecolor='#111827')
    ax4.axis('off')

    # Background card frame
    rect = patches.FancyBboxPatch((0.02, 0.02), 0.96, 0.96, boxstyle="round,pad=0.03", 
                                fc='#1e293b', ec='#3b82f6', lw=1.5, alpha=0.9)
    ax4.add_patch(rect)

    vex_status = "🟢 負➔恐慌時做市商助跌 (注意急殺)" if total_vex < 0 else "🔴 正➔恐慌時做市商護盤 (買盤支撐)"
    diff_flip = round(gex_plus_flip - zero_gamma, 1)
    early_bird_str = f"提前 {abs(diff_flip)} 點預警" if diff_flip > 0 else f"延後 {abs(diff_flip)} 點防守"

    summary_text = (
        f"🦅 尋鳥台指量化籌碼摘要\n"
        f"─────────────────────────\n"
        f"• 現貨點位 (S):   ${spot_p:,.0f}\n"
        f"• Zero Gamma:     ${zero_gamma:,.0f} (純價格轉折線)\n"
        f"• GEX+ Flip:      ${gex_plus_flip:,.0f} ({early_bird_str})\n\n"
        f"• 總 GEX 曝險:    {total_gex:+.1f} 億 (壓抑波動)\n"
        f"• 總 VEX 恐慌:    {total_vex:+.1f} 億 ({vex_status})\n"
        f"• 總 GEX+ 合成:   {total_gex_plus:+.1f} 億 (整體淨防守力)\n\n"
        f"🧱 做市商天花板牆 (Call Wall): ${call_wall:,.0f}\n"
        f"🛋️ 做市商護盤地板牆 (Put Wall): ${put_wall:,.0f}\n"
        f"─────────────────────────\n"
        f"© 尋鳥 Bluebird Finder Quant Labs\n"
        f"非投資建議  •  僅供量化研究與個人盯盤"
    )

    ax4.text(0.08, 0.92, summary_text, fontsize=9.5, color='#f8fafc',
             va='top', ha='left', fontfamily='Microsoft JhengHei', linespacing=1.4)

    plt.tight_layout(rect=[0, 0.02, 1, 0.93])
    
    # Save image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig)
    print(f"[OK] Generated Bluebird Finder Social Card: {output_path}")
    return True

if __name__ == "__main__":
    generate_bluebird_social_card()
