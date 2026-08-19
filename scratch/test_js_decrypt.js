const fs = require('fs');

// Simple CryptoJS SHA256 + XOR implementation for Node
const crypto = require('crypto');

function decryptPayload(b64Str, passcode) {
  try {
    const cipherBytes = Buffer.from(b64Str, 'base64');
    const key = crypto.createHash('sha256').update(passcode).digest();
    
    const decryptedBytes = Buffer.alloc(cipherBytes.length);
    for (let i = 0; i < cipherBytes.length; i++) {
      decryptedBytes[i] = cipherBytes[i] ^ key[i % key.length];
    }
    
    const jsonStr = decryptedBytes.toString('utf-8');
    return JSON.parse(jsonStr);
  } catch (e) {
    console.error("Node Decryption Err:", e);
    return null;
  }
}

const encObj = JSON.parse(fs.readFileSync('data/encrypted_gex.json', 'utf-8'));
const data = decryptPayload(encObj.payload, "GEX2026");
if (data) {
  console.log("[OK] JS/Node Decryption SUCCESS! Day TX:", data.day_txf_price, "Night TX:", data.night_txf_price);
} else {
  console.log("[FAIL] JS/Node Decryption FAILED");
}
