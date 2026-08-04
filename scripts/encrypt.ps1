$keyString = "GEX2026"
$jsonPath = "data/gex_data.json"
$outPath = "data/encrypted_gex.json"

$rawText = [System.IO.File]::ReadAllText((Resolve-Path $jsonPath), [System.Text.Encoding]::UTF8)

$keyBytes = [System.Text.Encoding]::UTF8.GetBytes($keyString)
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$derivedKey = $sha256.ComputeHash($keyBytes)

$dataBytes = [System.Text.Encoding]::UTF8.GetBytes($rawText)
$encryptedBytes = New-Object byte[] $dataBytes.Length

for ($i = 0; $i -lt $dataBytes.Length; $i++) {
    $encryptedBytes[$i] = $dataBytes[$i] -bxor $derivedKey[$i % $derivedKey.Length]
}

$base64 = [Convert]::ToBase64String($encryptedBytes)
$payload = @{
    v = 1
    alg = "XOR-SHA256"
    data = $base64
} | ConvertTo-Json -Compress

[System.IO.File]::WriteAllText((Resolve-Path $outPath), $payload, [System.Text.Encoding]::UTF8)
Write-Host "Re-encrypted successfully!"
