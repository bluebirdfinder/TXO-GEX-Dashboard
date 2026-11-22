#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""專案地圖產生器（只讀、純標準函式庫、不執行任何被掃描的程式）。

用途：掃描專案，找出「誰 import 誰、誰呼叫誰、誰讀／寫哪個資料檔」，
產出 docs/PROJECT_MAP.md（給 AI 先讀，省得每次重新探索），
並能用 --impact 立刻查「改這個檔會連帶影響誰」。

用法：
  python tools/build_project_map.py                 重新產生 docs/PROJECT_MAP.md
  python tools/build_project_map.py --impact gex_v2.py   查改動影響範圍（檔名或路徑片段）
  python tools/build_project_map.py --stdout        只印出、不寫檔

限制（務必知道）：
  * 讀／寫是用關鍵字「推測」的，不是執行後的真實結果。
  * 動態組出來的檔名（例如 f"{symbol}_cache.json"）抓不到。
  * 只看檔案與資料層級，看不到函式內部的呼叫細節。
"""
import argparse
import ast
import collections
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---- 掃描範圍（要改範圍只改這裡）-------------------------------------------
CODE_DIRS = ["scripts", "tools", ".github/workflows", "cloudflare", "trading room", "config"]
ROOT_CODE_GLOBS = ["*.js", "*.html", "*.bat", "*.toml"]
ROOT_DATA_GLOBS = ["*.json"]
DATA_DIR = "data"
CODE_EXT = {".py", ".ps1", ".bat", ".sh", ".js", ".html", ".yml", ".yaml", ".toml"}
DATA_EXT = {".json", ".jsonl", ".csv", ".js", ".png", ".jpg", ".txt"}
SKIP_PARTS = {"__pycache__", "node_modules", ".git", "scratch", "log", ".venv", "venv", "backups"}
OUT_FILE = ROOT / "docs" / "PROJECT_MAP.md"

W_RE = re.compile(
    r"""['"](?:w|wb|a|ab|w\+|wt|at)['"]|write_text|write_bytes|json\.dump\(|\.to_json|\.to_csv|"""
    r"""\.save\(|\.write\(|shutil\.(?:copy|move)|os\.(?:replace|rename)|Out-File|Set-Content|"""
    r"""Add-Content|writeFile"""
)
R_RE = re.compile(
    r"json\.load|read_text|read_bytes|read_csv|\.read\(|Get-Content|ConvertFrom-Json|readFile|fetch\("
)
OPEN_RE = re.compile(r"open\(|exists\(|isfile")
COMMENT_START = ("#", "//", "REM ", "rem ", "::", "*", "<!--")
TOKEN_RE = re.compile(r"[^\s\"'`=:,()<>\[\]{}|;$\\/?&#+*]+")

ENV_PATTERNS = [
    re.compile(r"os\.environ(?:\.get)?\(\s*['\"](\w+)['\"]"),
    re.compile(r"os\.getenv\(\s*['\"](\w+)['\"]"),
    re.compile(r"os\.environ\[\s*['\"](\w+)['\"]"),
    re.compile(r"\$env:(\w+)"),
    re.compile(r"secrets\.(\w+)"),
    re.compile(r"\benv\.([A-Z][A-Z0-9_]{2,})"),
]


def rel(p):
    return p.relative_to(ROOT).as_posix()


def read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---- 1. 收集節點 -----------------------------------------------------------
def collect():
    nodes = {}  # id -> {"kind": "code"|"data", "path": Path, "dir": bool}

    def add(p, kind, is_dir=False):
        nid = rel(p) + ("/" if is_dir else "")
        nodes.setdefault(nid, {"kind": kind, "path": p, "dir": is_dir})

    for d in CODE_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or set(p.relative_to(ROOT).parts) & SKIP_PARTS:
                continue
            suf = p.suffix.lower()
            if d == "trading room" and suf in {".json", ".jsonl", ".csv"}:
                add(p, "data")
            elif suf in CODE_EXT:
                add(p, "code")
    for g in ROOT_CODE_GLOBS:
        for p in sorted(ROOT.glob(g)):
            if not p.name.startswith("HANDOFF"):  # 交接文件不是專案程式
                add(p, "code")
    nodes.pop(rel(Path(__file__).resolve()), None)  # 掃描器自己不列入
    for g in ROOT_DATA_GLOBS:
        for p in sorted(ROOT.glob(g)):
            add(p, "data")
    data_dir = ROOT / DATA_DIR
    if data_dir.exists():
        for p in sorted(data_dir.iterdir()):
            if p.is_dir():
                add(p, "data", True)
            elif p.suffix.lower() in DATA_EXT:
                add(p, "data")
    return nodes


def build_index(nodes):
    idx = collections.defaultdict(list)
    for nid, n in nodes.items():
        idx[n["path"].name].append(nid)
    return idx


# ---- 2. 分析每個檔案 -------------------------------------------------------
def detect_mode(lines, lineno, var_names):
    """推測這個資料檔引用是讀、寫還是只是提到。回傳 set。"""
    ctx = list(lines[max(0, lineno - 3): lineno + 2])
    for v in var_names:
        pat = re.compile(r"\b" + re.escape(v) + r"\b")
        ctx += [l for l in lines if pat.search(l)]
    text = "\n".join(ctx)
    modes = set()
    if W_RE.search(text):
        modes.add("write")
    if R_RE.search(text):
        modes.add("read")
    if not modes:
        modes.add("read" if OPEN_RE.search(text) else "ref")
    return modes


def analyze_python(nid, src, nodes, idx, py_stems):
    refs = []  # (target_id, kind)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return analyze_text(nid, src, nodes, idx)
    lines = src.splitlines()

    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = ([node.module] if node.module else []) + [a.name for a in node.names]
        for name in names:
            for part in name.split("."):
                for t in py_stems.get(part, []):
                    if t != nid:
                        refs.append((t, "import"))

    doc_consts = {
        id(n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
    }
    seen = set()

    def handle(const, var_names):
        s = const.value
        if not isinstance(s, str) or len(s) > 300 or id(const) in doc_consts or id(const) in seen:
            return
        seen.add(id(const))
        for part in re.split(r"[\\/\s\"'?&#+*]+", s):
            part = part.strip(".,")
            if len(part) < 3 or part not in idx:
                continue
            for t in idx[part]:
                if t == nid:
                    continue
                if nodes[t]["kind"] == "code":
                    refs.append((t, "call"))
                else:
                    for m in detect_mode(lines, const.lineno, var_names):
                        refs.append((t, m))

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            vs = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for c in ast.walk(node.value):
                if isinstance(c, ast.Constant):
                    handle(c, vs)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            handle(node, [])
    return refs


def analyze_text(nid, src, nodes, idx):
    refs = []
    for line in src.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_START):
            continue
        is_git_add = stripped.startswith("git add")
        for tok in TOKEN_RE.findall(line):
            tok = tok.strip(".,")
            if len(tok) < 3 or tok not in idx:
                continue
            for t in idx[tok]:
                if t == nid:
                    continue
                if nodes[t]["kind"] == "code":
                    refs.append((t, "call"))
                elif is_git_add:
                    continue  # 工作流程只是「提交」成品，真正的寫入者是產生它的腳本，不列入依賴
                else:
                    modes = set()
                    if W_RE.search(line):
                        modes.add("write")
                    if R_RE.search(line):
                        modes.add("read")
                    refs.extend((t, m) for m in (modes or {"ref"}))
    return refs


def purpose(path, src):
    if path.suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(src))
            if doc:
                return doc.strip().splitlines()[0][:70]
        except SyntaxError:
            pass
    for line in src.splitlines()[:25]:
        s = line.strip()
        if not s or s.startswith("#!") or "coding" in s[:20] or s.startswith(("<!DOCTYPE", "<html", "<head", "@echo")):
            continue
        if s.startswith(("#", "//", "REM ", "::", "/*", "*")) or s.startswith("name:"):
            return s.lstrip("#/*: ").replace("name:", "").strip()[:70]
        if s.startswith("<title>"):
            return re.sub(r"</?title>", "", s)[:70]
    return ""


def env_vars(src):
    found = set()
    for pat in ENV_PATTERNS:
        found.update(pat.findall(src))
    return sorted(found)


# ---- 3. 組圖與影響範圍 -----------------------------------------------------
def build_graph():
    nodes = collect()
    idx = build_index(nodes)
    py_stems = collections.defaultdict(list)
    for nid, n in nodes.items():
        if n["kind"] == "code" and n["path"].suffix == ".py":
            py_stems[n["path"].stem].append(nid)

    info = {}
    depends = collections.defaultdict(set)  # A -> A 依賴的對象
    for nid, n in nodes.items():
        if n["kind"] != "code":
            continue
        src = read(n["path"])
        if n["path"].suffix == ".py":
            refs = analyze_python(nid, src, nodes, idx, py_stems)
        else:
            refs = analyze_text(nid, src, nodes, idx)
        rec = {"import": set(), "call": set(), "read": set(), "write": set(), "ref": set()}
        for t, k in refs:
            rec[k].add(t)
        if n["path"].name.startswith(("test_", "debug_", "probe_")):
            # 測試／探測腳本常用同名假資料，不當作正式的資料寫入者，避免影響範圍被灌水
            rec["ref"] |= rec["write"]
            rec["write"] = set()
        rec["ref"] -= rec["read"] | rec["write"]
        info[nid] = {
            "lines": src.count("\n") + 1,
            "purpose": purpose(n["path"], src),
            "env": env_vars(src),
            "rec": rec,
            "src": src,
        }
        for t in rec["import"] | rec["call"] | rec["read"] | rec["ref"]:
            depends[nid].add(t)
        for t in rec["write"]:  # 資料檔「依賴」寫它的程式
            depends[t].add(nid)

    rev = collections.defaultdict(set)
    for a, bs in depends.items():
        for b in bs:
            rev[b].add(a)
    return nodes, info, depends, rev


def impact(target, rev):
    """回傳 {節點: 距離}，距離 1 = 直接受影響。"""
    dist, frontier, d = {}, {target}, 0
    while frontier:
        d += 1
        nxt = set()
        for x in frontier:
            for y in rev.get(x, ()):
                if y != target and y not in dist:
                    dist[y] = d
                    nxt.add(y)
        frontier = nxt
    return dist


def short(nid):
    return nid.rstrip("/").split("/")[-1]


def fmt(items, n=8):
    items = sorted(set(items))
    if not items:
        return "—"
    s = "、".join(short(i) for i in items[:n])
    return s + (f" …+{len(items) - n}" if len(items) > n else "")


# ---- 4. 輸出 ---------------------------------------------------------------
def dom_check():
    idx_html, app_js = ROOT / "index.html", ROOT / "app.js"
    if not (idx_html.exists() and app_js.exists()):
        return None
    html, js = read(idx_html), read(app_js)
    defined = set(re.findall(r"""\bid=["']([^"']+)["']""", html))
    used = set(re.findall(r"""getElementById\(\s*['"]([^'"]+)['"]""", js))
    used |= set(re.findall(r"""querySelector\(\s*['"]#([\w-]+)['"]""", js))
    return sorted(used - defined), len(used)


def render(nodes, info, depends, rev):
    code = {k: v for k, v in nodes.items() if v["kind"] == "code"}
    data = {k: v for k, v in nodes.items() if v["kind"] == "data"}
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        head = "?"
    out = []
    w = out.append
    w("# PROJECT_MAP（自動產生，請勿手改）")
    w("")
    w(f"> 產生時間 {datetime.datetime.now():%Y-%m-%d %H:%M}｜git HEAD `{head}`｜"
      f"程式檔 {len(code)} 個、資料檔 {len(data)} 個")
    w("> 重新產生：`python tools/build_project_map.py`｜查影響範圍：`python tools/build_project_map.py --impact <檔名>`")
    w("> **限制**：讀／寫是用關鍵字推測；動態組出的檔名抓不到；只到檔案層級。"
      "改動前仍要打開檔案確認，這份是「先看哪裡」的索引，不是真相。")
    w("")

    # 入口
    w("## 1. 入口與排程（什麼東西會自己跑、跑了會呼叫誰）")
    w("")
    w("| 入口 | 排程／說明 | 直接呼叫 |")
    w("|---|---|---|")
    for nid, i in sorted(info.items()):
        p = nodes[nid]["path"]
        calls = [t for t in i["rec"]["call"] if nodes[t]["kind"] == "code"]
        if p.suffix in {".yml", ".yaml"}:
            crons = re.findall(r"cron:\s*'([^']+)'\s*(?:#\s*(.*))?", i["src"])
            desc = "；".join(f"`{c}` {t.strip()[:28]}" for c, t in crons[:3])
            if len(crons) > 3:
                desc += f" …共 {len(crons)} 個時間點"
            w(f"| `{nid}` | {desc or '—'} | {fmt(calls, 12)} |")
        elif p.suffix in {".bat", ".ps1", ".sh"} and calls:
            w(f"| `{nid}` | {i['purpose'] or '—'} | {fmt(calls, 12)} |")
    w("")

    # 資料流向
    w("## 2. 資料檔流向（改資料格式前先看誰讀它）")
    w("")
    w("| 資料檔 | 誰寫入（推測） | 誰讀取（推測） |")
    w("|---|---|---|")
    orphan_data = []
    for nid in sorted(data):
        writers = [a for a in depends.get(nid, ()) if nodes[a]["kind"] == "code"]
        readers = [a for a in rev.get(nid, ()) if a not in writers]
        if not writers and not readers:
            orphan_data.append(nid)
            continue
        w(f"| `{short(nid)}` | {fmt(writers, 6)} | {fmt(readers, 8)} |")
    w("")

    # 程式反查
    w("## 3. 程式檔反查（改這個檔，誰會受影響）")
    w("")
    w("「近距影響」= 2 層內（直接＋再一手，含透過資料檔傳遞）依賴它的程式檔數；更遠的關聯太弱不計。逐一展開用 `--impact`。")
    w("")
    w("| 檔案 | 行數 | 用途 | 被誰用（直接） | 近距影響 | 讀 | 寫 | 環境變數／Secrets |")
    w("|---|---|---|---|---|---|---|---|")
    standalone = []
    for nid in sorted(info):
        i, rec = info[nid], info[nid]["rec"]
        direct = [a for a in rev.get(nid, ()) if nodes[a]["kind"] == "code"]
        closure = [k for k, d in impact(nid, rev).items() if d <= 2 and nodes[k]["kind"] == "code"]
        outgoing = rec["import"] | rec["call"] | rec["read"] | rec["write"] | rec["ref"]
        if not direct and not outgoing and not closure:
            standalone.append(nid)
            continue
        w(f"| `{nid}` | {i['lines']} | {i['purpose'] or '—'} | {fmt(direct, 6)} | {len(closure)} | "
          f"{fmt(rec['read'] | rec['ref'], 5)} | {fmt(rec['write'], 5)} | {', '.join(i['env'][:5]) or '—'} |")
    w("")

    # 孤兒
    w("## 4. 沒有被任何地方引用的檔案（手動執行、測試或可能已廢棄）")
    w("")
    w("程式：" + (fmt(standalone, 60) if standalone else "—"))
    w("")
    w("資料：" + (fmt(orphan_data, 60) if orphan_data else "—"))
    w("")

    # DOM
    res = dom_check()
    if res:
        missing, total = res
        w("## 5. 前端一致性：app.js 用到但 index.html 找不到的 DOM id")
        w("")
        w(f"app.js 引用 {total} 個 id；靜態對照找不到：" +
          (("、".join(f"`{m}`" for m in missing[:40]) + ("…" if len(missing) > 40 else "")) if missing else "無")
          + "。（動態產生的元素會誤報，需人工確認。）")
        w("")
    return "\n".join(out) + "\n"


def cmd_impact(query, nodes, info, rev):
    q = query.replace("\\", "/").lower()
    hits = [n for n in nodes if q == n.lower() or q == short(n).lower()] or \
           [n for n in nodes if q in n.lower()]
    if not hits:
        print(f"找不到符合「{query}」的檔案。")
        return 1
    for h in hits[:5]:
        dist = impact(h, rev)
        print(f"\n=== 改動 {h} 會影響 ===")
        if not dist:
            print("（沒有任何已知的依賴者；可能是入口腳本，或引用是動態組出的）")
            continue
        deeper = [k for k, v in dist.items() if v > 3]
        for d in sorted(x for x in set(dist.values()) if x <= 3):
            lv = [k for k, v in dist.items() if v == d]
            label = "直接" if d == 1 else f"第 {d} 層（間接）"
            print(f"[{label}]")
            print("  程式：" + fmt([k for k in lv if nodes[k]["kind"] == "code"], 40))
            dd = [k for k in lv if nodes[k]["kind"] == "data"]
            if dd:
                print("  資料：" + fmt(dd, 40))
        if deeper:
            print(f"[更深層] 另有 {len(deeper)} 個檔案（多半是透過資料檔層層傳遞，關聯越來越弱，略）")
        if h in info and info[h]["env"]:
            print("  它用到的環境變數：" + ", ".join(info[h]["env"]))
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="專案地圖產生器（只讀）")
    ap.add_argument("--impact", help="查某檔案的改動影響範圍（檔名或路徑片段）")
    ap.add_argument("--stdout", action="store_true", help="只印出，不寫檔")
    args = ap.parse_args()

    nodes, info, depends, rev = build_graph()
    if args.impact:
        return cmd_impact(args.impact, nodes, info, rev)
    text = render(nodes, info, depends, rev)
    if args.stdout:
        print(text)
    else:
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(text, encoding="utf-8")
        print(f"已寫入 {rel(OUT_FILE)}（{len(text):,} 字元，約 {len(text) // 2:,} token 以內）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
