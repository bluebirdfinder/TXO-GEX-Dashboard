import re

with open('index.html', 'r', encoding='utf-8') as f:
    html_text = f.read()

with open('app.js', 'r', encoding='utf-8') as f:
    js_text = f.read()

# Extract all IDs in HTML
html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_text))

# Extract all document.getElementById in JS
js_get_ids = set(re.findall(r'document\.getElementById\s*\(\s*["\']([^"\']+)["\']\s*\)', js_text))

missing_ids = js_get_ids - html_ids
print('Total IDs in HTML:', len(html_ids))
print('Total getElementById in JS:', len(js_get_ids))
print('Missing IDs in HTML (JS queries but HTML lacks):', missing_ids)
