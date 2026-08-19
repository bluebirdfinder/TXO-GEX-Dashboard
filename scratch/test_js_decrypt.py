import base64
import hashlib
import json

passcode = "GEX2026"
key = hashlib.sha256(passcode.encode('utf-8')).digest()

with open("data/encrypted_gex.json", "r", encoding="utf-8") as f:
    enc_obj = json.load(f)

payload_b64 = enc_obj['payload']
cipher_bytes = base64.b64decode(payload_b64)
plain_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(cipher_bytes)])
plain_json = plain_bytes.decode('utf-8')

data = json.loads(plain_json)
print("Decrypted successfully! Version:", data.get('engine_version'), "Day TX:", data.get('day_txf_price'), "Night TX:", data.get('night_txf_price'))
