import json, sys

sys.stdout.reconfigure(encoding='utf-8')

with open("data/gex_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Keys in gex_data.json:")
for k in data.keys():
    val = data[k]
    if isinstance(val, list):
        print(f" - {k}: list of {len(val)} items")
    elif isinstance(val, dict):
        print(f" - {k}: dict with keys {list(val.keys())[:5]}")
    else:
        print(f" - {k}: {type(val).__name__} = {val}")
