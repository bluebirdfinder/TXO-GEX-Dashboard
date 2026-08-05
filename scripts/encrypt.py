"""
encrypt.py — Pure Encryption-Only Script
=========================================
This script ONLY reads the existing gex_data.json (produced by fetch_and_calc.py)
and re-encrypts it to encrypted_gex.json.

It does NOT modify any data fields. All data generation is handled
exclusively by fetch_and_calc.py to avoid overwriting dynamic content.
"""
import os
import json
import base64
import hashlib

PASSCODE = "GEX2026"
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, "data", "gex_data.json")
OUT_PATH  = os.path.join(BASE_DIR, "data", "encrypted_gex.json")

def main():
    if not os.path.exists(JSON_PATH):
        print(f"[ERROR] File not found: {JSON_PATH}")
        print("        Please run fetch_and_calc.py first to generate gex_data.json")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        plain_json_str = f.read()

    # Validate JSON is parseable before encrypting
    try:
        data = json.loads(plain_json_str)
        print(f"[OK] Loaded gex_data.json — date={data.get('date','?')}, session={data.get('session_type','?')}")
    except json.JSONDecodeError as e:
        print(f"[ERROR] gex_data.json is not valid JSON: {e}")
        return

    # XOR-SHA256 encryption (key = SHA256(passcode), XOR each byte)
    key = hashlib.sha256(PASSCODE.encode("utf-8")).digest()
    data_bytes   = plain_json_str.encode("utf-8")
    cipher_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(data_bytes)])
    b64_str      = base64.b64encode(cipher_bytes).decode("utf-8")

    payload = {
        "status":    "encrypted",
        "algorithm": "XOR-SHA256",
        "payload":   b64_str
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))

    print(f"[OK] Encrypted payload saved to: {OUT_PATH}")
    print(f"     Plaintext size: {len(data_bytes):,} bytes → Encrypted: {len(b64_str):,} chars (base64)")

if __name__ == "__main__":
    main()
