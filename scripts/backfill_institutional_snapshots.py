"""
backfill_institutional_snapshots.py - Seeds data/institutional_snapshots.json (the 5-day
institutional matrix's T-1..T-4 store) for trading days the CI never persisted.

Why this exists: until v64.4 the GitHub Actions job never `git add`-ed the snapshot files, so
every day's real institutional row written on the ephemeral runner vanished. scripts/
backfill_snapshots.py only refills session_snapshots.json (spot/txf/GEX) and does not touch
institutional data. Every underlying fetcher in fetch_and_calc_vision.py already accepts an
explicit historical date, so this script just replays exactly what generate_gex_payload() does
for T-0, but for a past date.

Honesty rules (same as the live pipeline, AGENTS.md redline #6):
  - A day is written ONLY if every source for that session came back genuinely live for that
    exact date. Anything missing -> the day is skipped and reported, never partially filled,
    never borrowed from another day.
  - write_institutional_snapshot()'s duplicate guard stays on (refuses byte-identical days).
  - Existing keys are left alone unless --overwrite is given.
  - INST_RETAIL keys are NOT backfilled: the retail-sentiment page has no date parameter.

Usage:
  python scripts/backfill_institutional_snapshots.py --dry-run            # show what is missing
  python scripts/backfill_institutional_snapshots.py --days 10            # write missing days
  python scripts/backfill_institutional_snapshots.py --dates 2026-09-24 --verify
      # re-fetch a date that already has a live-captured snapshot and diff it (mapping check)
"""
import argparse
import datetime
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetch_and_calc_vision as eng  # noqa: E402
from backfill_snapshots import get_past_tw_trading_days  # noqa: E402

# Keep in sync with _INST_DAY_FIELDS / _INST_NIGHT_FIELDS in generate_gex_payload().
DAY_FIELDS = [
    "top5_net", "top10_net", "top5_spec_net", "top10_spec_net",
    "lt_near", "lt_far", "lt_total",
    "opt_lt_call_top5_net", "opt_lt_call_top10_net", "opt_lt_call_top5_spec_net", "opt_lt_call_top10_spec_net",
    "opt_lt_call_week", "opt_lt_call_total",
    "opt_lt_put_top5_net", "opt_lt_put_top10_net", "opt_lt_put_top5_spec_net", "opt_lt_put_top10_spec_net",
    "opt_lt_put_week", "opt_lt_put_total",
    "foreign_fut_net", "trust_fut_net", "itrust_fut_net", "dealer_fut_net",
    "foreign_stock_net", "trust_stock_net", "itrust_stock_net", "dealer_stock_net", "total_stock_net",
    "foreign_opt_net", "trust_opt_net", "itrust_opt_net", "dealer_opt_net",
    "foreign_opt_call_net", "foreign_opt_put_net",
    "trust_opt_call_net", "trust_opt_put_net",
    "dealer_opt_call_net", "dealer_opt_put_net",
    "pc_ratio",
]
NIGHT_FIELDS = ["foreign_tx", "foreign_tx_amt", "foreign_mtx", "foreign_micro", "dealer_tx", "dealer_tx_amt"]


def _safe_sum(a, b):
    return round(a + b, 2) if (a is not None and b is not None) else None


def build_day_row(d, pc_map):
    """Returns (row, reason). row is None when any source was not genuinely live for date d."""
    slash = d.strftime("%Y/%m/%d")
    opt = eng.fetch_official_taifex_options_matrix(target_date=slash)
    lt = eng.fetch_official_taifex_large_trader(target_date=slash)
    opt_lt = eng.fetch_official_taifex_large_trader_options(target_date=slash)
    fut = eng.fetch_official_taifex_futures_institutional_oi(target_date=slash)
    stock = eng.fetch_twse_institutional_stock_trading(target_date=d.strftime("%Y%m%d"))
    pc = pc_map.get(f"{d.year}/{d.month}/{d.day}")

    missing = [name for name, v in (("options_matrix", opt), ("large_trader_fut", lt),
                                    ("large_trader_opt", opt_lt), ("futures_inst_oi", fut),
                                    ("twse_stock_trading", stock))
               if not v or not v.get("is_live", False)]
    if pc is None:
        missing.append("pc_ratio")
    if missing:
        return None, "not live: " + ", ".join(missing)

    row = {
        "top5_net": lt.get("top5_net"), "top10_net": lt.get("top10_net"),
        "top5_spec_net": lt.get("top5_spec_net"), "top10_spec_net": lt.get("top10_spec_net"),
        "lt_near": lt.get("near"), "lt_far": lt.get("far"), "lt_total": lt.get("total"),
        "opt_lt_call_top5_net": opt_lt.get("call", {}).get("top5_net"),
        "opt_lt_call_top10_net": opt_lt.get("call", {}).get("top10_net"),
        "opt_lt_call_top5_spec_net": opt_lt.get("call", {}).get("top5_spec_net"),
        "opt_lt_call_top10_spec_net": opt_lt.get("call", {}).get("top10_spec_net"),
        "opt_lt_call_week": opt_lt.get("call", {}).get("week"),
        "opt_lt_call_total": opt_lt.get("call", {}).get("total"),
        "opt_lt_put_top5_net": opt_lt.get("put", {}).get("top5_net"),
        "opt_lt_put_top10_net": opt_lt.get("put", {}).get("top10_net"),
        "opt_lt_put_top5_spec_net": opt_lt.get("put", {}).get("top5_spec_net"),
        "opt_lt_put_top10_spec_net": opt_lt.get("put", {}).get("top10_spec_net"),
        "opt_lt_put_week": opt_lt.get("put", {}).get("week"),
        "opt_lt_put_total": opt_lt.get("put", {}).get("total"),
        "foreign_fut_net": fut.get("foreign"),
        "trust_fut_net": fut.get("trust"), "itrust_fut_net": fut.get("trust"), "dealer_fut_net": fut.get("dealer"),
        "foreign_stock_net": stock.get("foreign_stock_net"),
        "trust_stock_net": stock.get("trust_stock_net"),
        "itrust_stock_net": stock.get("trust_stock_net"),
        "dealer_stock_net": stock.get("dealer_stock_net"),
        "total_stock_net": stock.get("total_stock_net"),
        "foreign_opt_net": _safe_sum(opt["foreign"]["call_net_amt"], opt["foreign"]["put_net_amt"]),
        "trust_opt_net": _safe_sum(opt["trust"]["call_net_amt"], opt["trust"]["put_net_amt"]),
        "itrust_opt_net": _safe_sum(opt["trust"]["call_net_amt"], opt["trust"]["put_net_amt"]),
        "dealer_opt_net": _safe_sum(opt["dealer"]["call_net_amt"], opt["dealer"]["put_net_amt"]),
        "foreign_opt_call_net": opt["foreign"]["call_net_amt"],
        "foreign_opt_put_net": opt["foreign"]["put_net_amt"],
        "trust_opt_call_net": opt["trust"]["call_net_amt"],
        "trust_opt_put_net": opt["trust"]["put_net_amt"],
        "dealer_opt_call_net": opt["dealer"]["call_net_amt"],
        "dealer_opt_put_net": opt["dealer"]["put_net_amt"],
        "pc_ratio": pc,
    }
    return {f: row[f] for f in DAY_FIELDS}, "ok"


def build_night_row(d):
    n = eng.fetch_taifex_night_institutional_trading(target_date=d)
    if not n or not n.get("is_live", False):
        return None, "not live: night_institutional"
    row = {
        "foreign_tx": n["tx_foreign_net_vol"], "foreign_tx_amt": n["tx_foreign_net_amt"],
        "foreign_mtx": n["mini_foreign_net_vol"], "foreign_micro": n["micro_foreign_net_vol"],
        "dealer_tx": n["tx_dealer_net_vol"], "dealer_tx_amt": n["tx_dealer_net_amt"],
    }
    return {f: row[f] for f in NIGHT_FIELDS}, "ok"


def _strip(d):
    return {k: v for k, v in d.items() if k not in ("written_at", "date", "has_snapshot")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10, help="look back this many trading days")
    ap.add_argument("--dates", nargs="*", help="explicit ISO dates (overrides --days)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="never write; diff a fresh historical fetch against the stored snapshot")
    args = ap.parse_args()

    if args.dates:
        dates = [datetime.date.fromisoformat(x) for x in args.dates]
    else:
        dates = get_past_tw_trading_days(args.days)
    dates = sorted(dates)

    snaps = eng.load_institutional_snapshots()
    pc_map = eng.fetch_official_taifex_pc_ratio() if not args.dry_run else {}
    written, skipped, failed = [], [], []

    for d in dates:
        iso = d.isoformat()
        for session, key in (("DAY", f"{iso}_INST_DAY"), ("NIGHT", f"{iso}_INST_NIGHT")):
            exists = key in snaps
            if args.dry_run:
                print(f"{key}: {'exists' if exists else 'MISSING'}")
                continue
            if exists and not (args.overwrite or args.verify):
                skipped.append(key)
                continue
            row, reason = build_day_row(d, pc_map) if session == "DAY" else build_night_row(d)
            if row is None:
                failed.append((key, reason))
                print(f"[SKIP] {key}: {reason}")
                continue
            if args.verify:
                if not exists:
                    print(f"[VERIFY] {key}: no stored snapshot to compare")
                    continue
                stored, diffs = _strip(snaps[key]), []
                for f in row:
                    if stored.get(f) != row[f]:
                        diffs.append((f, stored.get(f), row[f]))
                print(f"[VERIFY] {key}: {'IDENTICAL' if not diffs else f'{len(diffs)} field(s) differ'}")
                for f, a, b in diffs:
                    print(f"    {f}: stored={a!r} refetched={b!r}")
                continue
            res = eng.write_institutional_snapshot(iso, session, row)
            (written if res else failed).append(key if res else (key, "duplicate guard refused"))
            print(f"[{'WRITE' if res else 'SKIP'}] {key}")

    if not args.dry_run and not args.verify:
        print(f"\nwritten={len(written)} skipped_existing={len(skipped)} failed={len(failed)}")
        for k, r in failed:
            print(f"  - {k}: {r}")


if __name__ == "__main__":
    main()
