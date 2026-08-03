import json, re

file_path = r"C:\Users\TWLaiAl\.gemini\antigravity-ide\brain\9955a3f7-9880-4ba8-a2a9-b1c8ddba53a5\.system_generated\steps\666\content.md"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    raw = f.read()

# Decode unicode escapes like \u4e00
def decode_unicode(match):
    try:
        return match.group(0).encode('utf-8').decode('unicode-escape')
    except Exception:
        return match.group(0)

# Replace all \uXXXX
decoded_text = re.sub(r'\\u[0-9a-fA-F]{4}', decode_unicode, raw)

# Search for readable Chinese characters now
c_matches = re.findall(r'[\u4e00-\u9fa5]{2,}[^\x00-\x1f\n\r\"]*', decoded_text)
unique_m = []
seen = set()
for m in c_matches:
    c = m.strip()
    if c not in seen and len(c) > 6:
        seen.add(c)
        unique_m.append(c)

print(f"Decoded Chinese Chunks Count: {len(unique_m)}")
for idx, s in enumerate(unique_m):
    print(f"--- Chunk {idx+1} ---")
    print(s[:300])
