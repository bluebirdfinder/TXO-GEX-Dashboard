import json, re, os
path = "result.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
stats = {}
for m in data.get("messages", []):
    if m.get("type") != "message": continue
    text = ""
    if isinstance(m.get("text"), list):
        for p in m["text"]:
            if isinstance(p, str): text += p
            elif isinstance(p, dict): text += p.get("text", "")
    else: text = str(m.get("text", ""))
    if "5K" not in text: continue
    tf_match = re.search(r"\(([^)]+)\)", text)
    tf = tf_match.group(1) if tf_match else "Unknown"
    if tf not in stats: stats[tf] = {"trades":0, "wins":0, "profit":0.0}
    p_match = re.findall(r"[\d.]+", text)
    # The prices are usually the 1st and 2nd or 3rd numbers
    # Better: look for numbers after the labels
    p_match = re.findall(r":([\d.]+)", text)
    if len(p_match) >= 2:
        en, ex = float(p_match[0]), float(p_match[1])
        # Multiplier
        mult = 1.0
        if "BTC" in text: mult = 0.1
        elif "ETH" in text: mult = 1.0
        elif "NQ" in text: mult = 2.0
        elif "ES" in text: mult = 5.0
        elif "GC" in text: mult = 10.0
        elif "CL" in text: mult = 10.0
        elif "TX" in text: mult = 10.0
        # Direction
        # Use unicode for 'Short' (空) or 'Long' (多)
        is_short = "\u7a7a" in text
        diff = en - ex if is_short else ex - en
        p = diff * mult
        stats[tf]["trades"] += 1
        stats[tf]["profit"] += p
        if p > 0: stats[tf]["wins"] += 1
for tf, s in stats.items():
    wr = (s["wins"]/s["trades"]*100) if s["trades"] > 0 else 0
    print(f"{tf} | {s['trades']} trades | WinRate: {wr:.1f}% | Profit: {s['profit']:.2f}")
