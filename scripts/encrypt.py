import os
import json
import base64
import hashlib

PASSCODE = "GEX2026"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, "data", "gex_data.json")
OUT_PATH = os.path.join(BASE_DIR, "data", "encrypted_gex.json")

def main():
    if not os.path.exists(JSON_PATH):
        print(f"File not found: {JSON_PATH}")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = [
        {
            "date_label": "8/03 (T日)",
            "spot_price": 43386.41,
            "spot_change_val": 266.66,
            "spot_change_pct": 0.62,
            "two_price": 362.89,
            "two_change_val": 15.04,
            "two_change_pct": 4.32,
            "day_txf_price": 43230.0,
            "night_txf_price": 43152.0,
            "night_txf_shift": -78.0,
            "zero_gamma_level": 43080.0,
            "zero_gamma_shift": -78.0,
            "zero_gamma_regime": "🔴 正 Gamma 波動度抑制區 (平穩震盪)",
            "call_wall_strike": 43500,
            "call_wall_shift": -100,
            "put_wall_strike": 42900,
            "put_wall_shift": 250,
            "max_pain_strike": 43200,
            "max_pain_shift": 200,
            "pc_ratio": 112.93,
            "pc_ratio_desc": "🔴 偏多看撐",
            "notes": "加權小漲 266 點，夜盤台指期微幅拉回 -78 點"
        },
        {
            "date_label": "7/31 (T-1)",
            "spot_price": 43119.75,
            "spot_change_val": 3186.45,
            "spot_change_pct": 7.98,
            "two_price": 347.85,
            "two_change_val": 21.62,
            "two_change_pct": 6.63,
            "day_txf_price": 43678.0,
            "night_txf_price": 42650.0,
            "night_txf_shift": -1028.0,
            "zero_gamma_level": 42970.0,
            "zero_gamma_shift": -1028.0,
            "zero_gamma_regime": "🟢 負 Gamma 波動度放大區 (避險引爆)",
            "call_wall_strike": 43600,
            "call_wall_shift": 300,
            "put_wall_strike": 42400,
            "put_wall_shift": -600,
            "max_pain_strike": 43000,
            "max_pain_shift": -678,
            "pc_ratio": 108.5,
            "pc_ratio_desc": "🔴 偏多看撐",
            "notes": "日盤暴漲 +3,392 點，夜盤獲利拉回 -1,028 點"
        },
        {
            "date_label": "7/30 (T-2)",
            "spot_price": 39933.30,
            "spot_change_val": -105.88,
            "spot_change_pct": -0.26,
            "two_price": 326.23,
            "two_change_val": -8.01,
            "two_change_pct": -2.40,
            "day_txf_price": 40270.0,
            "night_txf_price": 40287.0,
            "night_txf_shift": 17.0,
            "zero_gamma_level": 40120.0,
            "zero_gamma_shift": 17.0,
            "zero_gamma_regime": "🔴 正 Gamma 區域震盪區 (平穩震盪)",
            "call_wall_strike": 40600,
            "call_wall_shift": 200,
            "put_wall_strike": 40000,
            "put_wall_shift": 200,
            "max_pain_strike": 40300,
            "max_pain_shift": 200,
            "pc_ratio": 107.2,
            "pc_ratio_desc": "🔴 偏多看撐",
            "notes": "結算後高檔整理，夜盤平穩微升 +17 點"
        }
    ]

    data["recent_3_days_summary"] = summary

    # Save gex_data.json
    plain_json_str = json.dumps(data, ensure_ascii=False, indent=2)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        f.write(plain_json_str)

    # Encrypt
    key = hashlib.sha256(PASSCODE.encode('utf-8')).digest()
    data_bytes = plain_json_str.encode('utf-8')
    cipher_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(data_bytes)])
    b64_str = base64.b64encode(cipher_bytes).decode('utf-8')

    payload = {
        "v": 1,
        "alg": "XOR-SHA256",
        "data": b64_str
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(',', ':'))

    print("Success: gex_data.json updated and encrypted to encrypted_gex.json!")

if __name__ == "__main__":
    main()
