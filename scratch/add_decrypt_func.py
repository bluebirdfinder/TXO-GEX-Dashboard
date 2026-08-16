import os

app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.js")

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

decrypt_func = """
function decryptPayload(b64Str, passcode) {
  try {
    const raw = CryptoJS.enc.Base64.parse(b64Str);
    const key = CryptoJS.SHA256(passcode);
    const rawWords = raw.words;
    const keyWords = key.words;

    const decryptedWords = [];
    for (let i = 0; i < raw.sigBytes; i++) {
      const bByte = (rawWords[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff;
      const kByte = (keyWords[(i % 32) >>> 2] >>> (24 - ((i % 32) % 4) * 8)) & 0xff;
      const xorByte = bByte ^ kByte;

      const wordIdx = i >>> 2;
      if (decryptedWords[wordIdx] === undefined) decryptedWords[wordIdx] = 0;
      decryptedWords[wordIdx] |= (xorByte << (24 - (i % 4) * 8));
    }

    const decryptedWordArray = CryptoJS.lib.WordArray.create(decryptedWords, raw.sigBytes);
    const jsonStr = CryptoJS.enc.Utf8.stringify(decryptedWordArray);
    return JSON.parse(jsonStr);
  } catch (e) {
    console.error('Decryption failed:', e);
    return null;
  }
}
"""

if "function decryptPayload" not in content:
    content = decrypt_func + "\n" + content

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] Added decryptPayload function to app.js")
