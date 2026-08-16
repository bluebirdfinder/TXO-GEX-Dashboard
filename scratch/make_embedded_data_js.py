import os
import json

gex_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gex_data.json")
embedded_js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "embedded_data.js")

with open(gex_path, "r", encoding="utf-8") as f:
    gex_obj = json.load(f)

json_str = json.dumps(gex_obj, ensure_ascii=False)

js_content = f"window.GEX_EMBEDDED_DATA = {json_str};\n"

with open(embedded_js_path, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"[OK] Created data/embedded_data.js ({len(js_content)} bytes)")
