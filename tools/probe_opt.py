import json, urllib.request, ssl, sys
from collections import Counter
ctx = ssl.create_default_context()
mt = sys.argv[1] if len(sys.argv) > 1 else "1"
p = {"MarketType": mt, "SymbolType": "O", "KindID": "1", "CID": "TXO", "ExpireMonth": "", "RowSize": "全部", "PageNo": "", "SortColumn": "", "AscDesc": "A"}
r = urllib.request.Request("https://mis.taifex.com.tw/futures/api/getQuoteList", data=json.dumps(p, ensure_ascii=False).encode(), headers={"Content-Type": "application/json;charset=UTF-8", "User-Agent": "Mozilla/5.0"})
d = json.loads(urllib.request.urlopen(r, context=ctx, timeout=15).read().decode())
q = d["RtData"]["QuoteList"]
print(len(q))
print(json.dumps(q[0], ensure_ascii=False))
print(Counter(x["SymbolID"][:3] for x in q))
print([x["SymbolID"] for x in q[:6]])
