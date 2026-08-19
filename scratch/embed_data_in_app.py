import os
import json

app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.js")
gex_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gex_data.json")

with open(gex_path, "r", encoding="utf-8") as f:
    gex_obj = json.load(f)

json_str = json.dumps(gex_obj, ensure_ascii=False, indent=2)

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace getFallbackData in app.js
new_fallback_func = f"""function getFallbackData() {{
  return {json_str};
}}"""

# Find where function getFallbackData begins and ends
start_idx = content.find("function getFallbackData()")
if start_idx != -1:
    # Find matching brace
    brace_count = 0
    end_idx = -1
    for i in range(start_idx, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break
    if end_idx != -1:
        content = content[:start_idx] + new_fallback_func + content[end_idx:]

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] Successfully embedded full gex_data.json into app.js getFallbackData()")
