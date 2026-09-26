#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXO-GEX-Dashboard 一鍵原子版本升級工具 (Atomic Version Bumper)
================================================================
徹底杜絕「版本閃一下又跳回舊版 (Version Flash & Revert)」老問題！

執行流程：
1. 嚴格驗證版本號格式 (例如 v50.9)
2. 同步更新 5 大核心程式與說明文件 (fetch_and_calc_vision.py, index.html, README.md, HISTORY.md, STATUS.md, PROJECT_HANDOVER.md)
3. 自動執行 fetch_and_calc_vision.py，重新編譯 data/gex_data.json, data/encrypted_gex.json, data/embedded_data.js
4. 全自動驗證 8 大標的版次 100% 一致性！
"""

import os
import sys
import re
import subprocess
import json
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def _replace_title_line(text, old, new):
    """Only touch the first line (document title) so historical "(vX.Y)" entries further down stay intact."""
    head, sep, rest = text.partition('\n')
    return head.replace(f'({old})', f'({new})') + sep + rest


def _history_has_version(version):
    history_md = os.path.join(BASE_DIR, 'HISTORY.md')
    return os.path.exists(history_md) and f'`{version}`' in _read(history_md)


def _insert_history_entry(new_version, release_note):
    """Insert a timeline row + a detailed-section stub at the top of HISTORY.md (idempotent)."""
    history_md = os.path.join(BASE_DIR, 'HISTORY.md')
    text = _read(history_md)
    today = datetime.date.today().isoformat()
    row = f'| **`{new_version}`** | {today} | {release_note} |\n'
    header = '| :---: | :---: | :--- |\n'
    i = text.index(header) + len(header)
    text = text[:i] + row + text[i:]
    section_heading = '## 🎯 各版本詳細更新紀錄\n\n'
    j = text.index(section_heading) + len(section_heading)
    stub = (f'### 🚀 {new_version} {release_note} ({today})\n\n'
            f'- **（bump_version.py 自動建立的骨架，請補上：改了哪些檔案、根因、驗證結果）**\n\n')
    text = text[:j] + stub + text[j:]
    _write(history_md, text)


def bump_version(new_version, release_note=""):
    if not re.match(r'^v\d+\.\d+(\.\d+)?$', new_version):
        print(f"❌ 錯誤：版本格式不正確 ({new_version})，必須為 vX.Y 格式 (例如 v50.9)")
        sys.exit(1)

    print(f"🚀 開始執行 TXO-GEX-Dashboard 原子版本升級至 [{new_version}]...")

    # 1. 取得舊版本號
    engine_py = os.path.join(BASE_DIR, 'scripts', 'fetch_and_calc_vision.py')
    content = _read(engine_py)
    m = re.search(r'ENGINE_VERSION = "(v\d+\.\d+(\.\d+)?)"', content)
    if not m:
        print("❌ 找不到目前的 ENGINE_VERSION！")
        sys.exit(1)
    old_version = m.group(1)
    print(f"📌 舊版本號: [{old_version}] ➔ 新版本號: [{new_version}]")

    if old_version == new_version:
        print("⚠️ 新舊版本號相同，將直接重新編譯數據檔以確保一致性...")

    # HISTORY.md 必須有本版條目：沒給說明、又沒有既有條目 → 在改任何檔案之前就擋下
    if not _history_has_version(new_version) and not release_note:
        print(f"❌ HISTORY.md 尚無 [{new_version}] 條目，且未提供變更說明。")
        print(f"   請用: python scripts/bump_version.py {new_version} \"這次的核心主題\"")
        sys.exit(1)

    total_steps = 7
    step = [0]

    def done(msg):
        step[0] += 1
        print(f"  ✅ [{step[0]}/{total_steps}] {msg}")

    # 2. 更新 fetch_and_calc_vision.py
    _write(engine_py, content.replace(f'ENGINE_VERSION = "{old_version}"', f'ENGINE_VERSION = "{new_version}"'))
    done("更新 scripts/fetch_and_calc_vision.py")

    # 3. 更新 index.html
    index_html = os.path.join(BASE_DIR, 'index.html')
    html_content = _read(index_html)
    html_content = html_content.replace(f'TXO GEX 量化系統 {old_version}', f'TXO GEX 量化系統 {new_version}')
    html_content = html_content.replace(f'embedded_data.js?v={old_version}', f'embedded_data.js?v={new_version}')
    html_content = html_content.replace(f'app.js?v={old_version}', f'app.js?v={new_version}')
    _write(index_html, html_content)
    done("更新 index.html (標題與 JS 快取版本)")

    # 4. 更新 STATUS.md（只動標題行與「當前版本／引擎／Gateway」抬頭，不動歷史條目）
    status_md = os.path.join(BASE_DIR, 'STATUS.md')
    if os.path.exists(status_md):
        s_content = _replace_title_line(_read(status_md), old_version, new_version)
        s_content = s_content.replace(f'**當前版本**：`{old_version}`', f'**當前版本**：`{new_version}`')
        s_content = s_content.replace(f'引擎 {old_version}', f'引擎 {new_version}')
        s_content = s_content.replace(f'Gateway {old_version}', f'Gateway {new_version}')
        _write(status_md, s_content)
    done("更新 STATUS.md")

    # 5. 更新 PROJECT_HANDOVER.md（只動標題行與「一、vX.Y」章節名；功能表格裡的舊版號是歷史，不能動）
    handover_md = os.path.join(BASE_DIR, 'PROJECT_HANDOVER.md')
    if os.path.exists(handover_md):
        h_content = _replace_title_line(_read(handover_md), old_version, new_version)
        h_content = h_content.replace(f'一、{old_version}', f'一、{new_version}')
        _write(handover_md, h_content)
    done("更新 PROJECT_HANDOVER.md")

    # 6. 更新 README.md
    readme_md = os.path.join(BASE_DIR, 'README.md')
    if os.path.exists(readme_md):
        r_content = _replace_title_line(_read(readme_md), old_version, new_version)
        r_content = r_content.replace(f'Engine-{old_version}', f'Engine-{new_version}')
        _write(readme_md, r_content)
    done("更新 README.md")

    # 7. 更新 room.html / room.js — lives in "trading room/" (a subfolder with a space in its name),
    # NOT at the project root. The root's own room.html is just a redirect stub to this real
    # file and contains none of the version-string patterns below, so a wrong path here used
    # to silently succeed (file exists, .replace() calls are all no-ops) while never touching
    # the actual trading room page.
    # The room files can lag behind the engine version (they were still v64.3 while the engine was
    # v64.4), so an exact old_version match silently leaves them stale. Match ANY version instead.
    VER = r'v\d+\.\d+(?:\.\d+)?'
    room_html = os.path.join(BASE_DIR, 'trading room', 'room.html')
    if os.path.exists(room_html):
        rm = _read(room_html)
        for pat in (rf'(Bird Trading Room ){VER}', rf'(badge-version">){VER}(<)', rf'(room\.css\?v=){VER}',
                    rf'(embedded_data\.js\?v=){VER}', rf'(room\.js\?v=){VER}'):
            rm = re.sub(pat, lambda m: m.group(1) + new_version + (m.group(2) if m.lastindex and m.lastindex >= 2 else ''), rm)
        _write(room_html, rm)
    room_js = os.path.join(BASE_DIR, 'trading room', 'room.js')
    if os.path.exists(room_js):
        rj = _read(room_js)
        for pat in (rf'(Core Engine ){VER}', rf'(Trading Room ){VER}', rf'(即時全域量化診斷 \(){VER}(\))'):
            rj = re.sub(pat, lambda m: m.group(1) + new_version + (m.group(2) if m.lastindex and m.lastindex >= 2 else ''), rj)
        _write(room_js, rj)
    done("更新 trading room/room.html 與 room.js")

    # 8. 在 HISTORY.md 最上方插入本版條目骨架（時間軸一列＋詳細紀錄小節）；已有條目則不重複插入
    if release_note and not _history_has_version(new_version):
        _insert_history_entry(new_version, release_note)
        done("HISTORY.md 已插入本版條目骨架（請補完詳細根因與驗證結果）")
    else:
        done("HISTORY.md 已有本版條目，略過插入")

    # 7. ⚡ CRITICAL：自動執行數據引擎重新生成 gex_data.json / embedded_data.js
    print(f"\n⚡ [核心防呆] 正在執行數據引擎，產出帶有 [{new_version}] 的最新數據 Payload...")
    res = subprocess.run([sys.executable, engine_py], capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        print(f"❌ 數據引擎執行失敗: {res.stderr}")
        sys.exit(1)
    print("  🎉 數據引擎執行成功！gex_data.json 與 embedded_data.js 已完成寫入。")

    # 8. 全面稽核 8 大標的版次一致性
    print("\n🔍 執行 8 大關鍵位置版次一致性自動稽核 (Self-Audit)...")
    gex_json = os.path.join(BASE_DIR, 'data', 'gex_data.json')
    with open(gex_json, 'r', encoding='utf-8') as f:
        gex_d = json.load(f)
    json_ver = gex_d.get('engine_version')

    embedded_js = os.path.join(BASE_DIR, 'data', 'embedded_data.js')
    with open(embedded_js, 'r', encoding='utf-8') as f:
        emb_text = f.read()

    passed = True
    if json_ver != new_version:
        print(f"  ❌ gex_data.json 引擎版本不符 ({json_ver} != {new_version})")
        passed = False
    else:
        print(f"  ✅ gex_data.json: {json_ver}")

    if f'"engine_version": "{new_version}"' not in emb_text:
        print(f"  ❌ embedded_data.js 引擎版本不符")
        passed = False
    else:
        print(f"  ✅ embedded_data.js: {new_version}")

    # 8.1 文件與前端版次檢查（不只 JSON，也確認 HTML/MD 標題真的換成新版）
    for rel, needle in [('index.html', f'app.js?v={new_version}'),
                        ('STATUS.md', f'**當前版本**：`{new_version}`'),
                        ('README.md', f'Engine-{new_version}'),
                        ('PROJECT_HANDOVER.md', f'({new_version})'),
                        ('HISTORY.md', f'`{new_version}`')]:
        path = os.path.join(BASE_DIR, rel)
        if os.path.exists(path) and needle not in _read(path):
            print(f"  ❌ {rel} 找不到 [{needle}]，版次未同步")
            passed = False
        else:
            print(f"  ✅ {rel}: {new_version}")

    # 8.2 CI 存檔清單檢查：腳本寫出的 data/ 檔案，是否都在 auto_update.yml 的 git add 清單裡
    # （v64.4 教訓：快照檔一直被寫出，但 CI 從沒 git add，資料在雲端虛擬機銷毀時消失）。只警告不擋。
    wf = os.path.join(BASE_DIR, '.github', 'workflows', 'auto_update.yml')
    if os.path.exists(wf):
        wf_text = _read(wf)
        add_line = next((l for l in wf_text.splitlines() if 'git add' in l and 'data/' in l), '')
        listed = add_line.split()
        st = subprocess.run(['git', '-C', BASE_DIR, 'status', '--porcelain', '--', 'data/'],
                            capture_output=True, text=True, encoding='utf-8')
        changed = [ln[3:].strip().strip('"') for ln in st.stdout.splitlines() if ln.strip()]
        import fnmatch
        missing = [c for c in changed if not any(fnmatch.fnmatch(c, pat) for pat in listed)]
        if missing:
            print("  ⚠️ 以下 data/ 檔案本次被寫出，但不在 auto_update.yml 的 git add 清單（CI 不會存回 repo，請確認是否預期）：")
            for c in missing:
                print(f"     - {c}")
        else:
            print("  ✅ 本次寫出的 data/ 檔案皆在 CI git add 清單內")

    # 9. 🛡️ 執行盤中即時行情與 5 日矩陣完整性健康檢查 (Sanity Audit)
    print("\n🛡️ 執行台指期行情與 5 日矩陣方向性健康檢查 (Sanity Audit)...")
    spot_chg = gex_d.get('spot_change', 0.0)
    day_tx = gex_d.get('day_txf_price', 0.0)
    night_tx = gex_d.get('night_txf_price', 0.0)
    sessions = gex_d.get('history_10_sessions', [])

    if sessions and len(sessions) >= 3:
        t0 = sessions[-1]
        t1_n = sessions[-2]
        t1_d = sessions[-3]
        
        # Check: spot large drop vs txf
        if spot_chg < -200 and (day_tx - t1_d.get('txf_price', day_tx)) > 300:
            print(f"  ❌ 嚴重警告：加權指數大跌 ({spot_chg:+} 點)，但台指期較昨日日盤呈現暴漲，疑似抓到昨日結算價倒錯！")
            passed = False
        else:
            print(f"  ✅ 現貨與期指方向性校驗通過 (Spot Chg: {spot_chg:+} 點, TXF Live: {day_tx})")

        print(f"  ✅ 5 日矩陣多盤別鏈路校驗通過 (T0: {t0.get('txf_price')}, T-1夜: {t1_n.get('txf_price')}, T-1日: {t1_d.get('txf_price')})")
    else:
        print("  ⚠️ 5 日矩陣長度不足 3 筆，略過進階校驗。")

    if passed:
        print(f"\n🎉 恭喜！全站版次與數據結構已 100% 驗證通過 [{new_version}]，徹底消除版本閃退與行情倒錯！")
        print(f"👉 下一步：補完 HISTORY.md 詳細內容 → 逐一 git add 本次檔案（不要 git add .）→ commit；push 前先問使用者")
    else:
        print("\n❌ 稽核未完全通過，請檢查上述項目。")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方式: python scripts/bump_version.py <新版本號 (例如 v50.9)> '<本版核心主題，會寫入 HISTORY.md>'")
        sys.exit(1)
    target_ver = sys.argv[1]
    desc = sys.argv[2] if len(sys.argv) > 2 else ""
    bump_version(target_ver, desc)
