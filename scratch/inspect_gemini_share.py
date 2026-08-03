file_path = r"C:\Users\TWLaiAl\.gemini\antigravity-ide\brain\9955a3f7-9880-4ba8-a2a9-b1c8ddba53a5\.system_generated\steps\666\content.md"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

print("File size:", len(text))
# Print occurrences of 'gemini' or 'share' or payload variables
import re
print("Matches for WIZ_global_data or similar:")
for m in re.finditer(r'AF_initDataCallback\s*\(({.*?})\);', text, re.DOTALL):
    print("Found AF_initDataCallback chunk, len:", len(m.group(1)))
    print(m.group(1)[:200])

print("\nSearching for any string containing 'Kpn5RMgUQdVv':")
for m in re.finditer(r'.{0,100}Kpn5RMgUQdVv.{0,200}', text):
    print(m.group(0))
