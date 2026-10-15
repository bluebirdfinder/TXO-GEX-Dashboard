"""掃描 trading room/brain/ 下所有 .md，依標題切段，輸出 manifest.json（幕僚鳥檢索用）。"""
import json, re, pathlib
root = pathlib.Path(__file__).parent / "brain"
chunks = []
for p in sorted(root.rglob("*.md")):
    if p.name == "README.md":
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    parts = re.split(r"(?m)^(?=#{1,3} )", text)
    for part in parts:
        part = part.strip()
        if len(part) < 40:
            continue
        title = part.splitlines()[0].lstrip("# ").strip()
        # 過長的段再切
        for i in range(0, len(part), 1800):
            chunks.append({"src": p.name, "title": title, "text": part[i:i + 1800]})
(root / "manifest.json").write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
print(f"{len(chunks)} chunks -> {root / 'manifest.json'}")
