import json, sys

sys.stdout.reconfigure(encoding='utf-8')

with open("data/gex_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

inst_5day = data.get("institutional_5day_history", [])
print(f"Found {len(inst_5day)} rows in institutional_5day_history:")
for row in inst_5day:
    print("Date:", row.get("date"))
    print("  Foreign Opt:", row.get("foreign_opt_call_net"), row.get("foreign_opt_put_net"), row.get("foreign_opt_net"))
    print("  Trust Opt:", row.get("trust_opt_call_net"), row.get("trust_opt_put_net"), row.get("trust_opt_net"))
    print("  Dealer Opt:", row.get("dealer_opt_call_net"), row.get("dealer_opt_put_net"), row.get("dealer_opt_net"))
