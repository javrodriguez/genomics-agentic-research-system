#!/usr/bin/env python3
"""Per-call usage, vendor prices, printed total_cost_usd, and elapsed wall time.

The round's per-call correction supersedes the copied reader's refusal to read
harness dollar figures. Repeated fragments of one call count once; conflicting
fragments refuse. Prices are supplied in a dated table, never embedded here.
The normalized call list is cost-calls.json; build_draft supplies price_table in
the pre-registration. Drivers must supply call IDs, usage and timestamps from
their vendor records. Missing measurements remain unmeasured, never zero.

Round caps cover vendor-read spend since the round began, across all months.
walk_gate and month_turn_allowed are pure functions; the driver owns invoking
them before a take. No account lookup, price lookup or human ruling is inferred.
"""
from __future__ import annotations
import argparse
import calendar
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import batch
import prereg

CAPS = {"openai": Decimal(260), "google": Decimal(140)}
TOTAL_CAP = Decimal(400)
STOP_FOR_WORD = "stop for Javier's word"
PROCEED = "within round caps"
CLASSES = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
CALLS = HERE / "cost-calls.json"
PAGE = HERE / "COSTS.md"


def amount(value):
    if isinstance(value, bool):
        raise ValueError("amount must be a nonnegative finite number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("invalid amount") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("amount must be a nonnegative finite number")
    return result


def utc(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if not isinstance(result, datetime) or result.tzinfo is None:
        raise ValueError("an aware UTC clock is required")
    return result.astimezone(timezone.utc)


def require_price_date(table):
    try:
        date.fromisoformat(table["as_of"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("a dated price table is required") from exc


def unique_calls(calls):
    seen = {}
    for call in calls:
        key = (call.get("vendor"), call.get("call_id"))
        if not all(isinstance(x, str) and x.strip() for x in key):
            raise ValueError("vendor and call_id are required")
        if key in seen and seen[key] != call:
            raise ValueError("conflicting records of one call")
        seen[key] = call
    return list(seen.values())


def account(calls, price_table):
    require_price_date(price_table)
    calls = unique_calls(calls)
    usage = dict.fromkeys(CLASSES, 0)
    priced = Decimal(0)
    printed = Decimal(0)
    usage_complete = printed_complete = bool(calls)
    starts, ends = [], []
    wall_complete = bool(calls)
    vendors = {}
    for call in calls:
        if batch.agent_problems(call):
            raise ValueError("call requires model and agent with harness and version")
        if not isinstance(call.get("model"), str) or not call["model"].strip():
            raise ValueError("call requires model")
        vendor = call["vendor"]
        subtotal = vendors.setdefault(vendor, {"calls": 0, "total_cost_usd": Decimal(0), "priced_cost_usd": Decimal(0)})
        subtotal["calls"] += 1
        try:
            prices = price_table["vendors"][vendor][call["model"]]
        except KeyError as exc:
            raise ValueError("dated price table lacks vendor/model") from exc
        raw = call.get("usage")
        if raw is None:
            usage_complete = False
            subtotal["priced_cost_usd"] = None
        else:
            if not isinstance(raw, dict) or not raw or set(raw) - set(CLASSES):
                raise ValueError("usage has unknown or missing token classes")
            cost = Decimal(0)
            for kind, count in raw.items():
                if type(count) is not int or count < 0 or kind not in prices:
                    raise ValueError("token count or supplied price is missing/invalid")
                usage[kind] += count
                cost += Decimal(count) * amount(prices[kind]) / 1000000
            priced += cost
            if subtotal["priced_cost_usd"] is not None:
                subtotal["priced_cost_usd"] += cost
        if call.get("total_cost_usd") is None:
            printed_complete = False
            subtotal["total_cost_usd"] = None
        else:
            value = amount(call["total_cost_usd"])
            printed += value
            if subtotal["total_cost_usd"] is not None:
                subtotal["total_cost_usd"] += value
        if call.get("started_at") is None or call.get("ended_at") is None:
            wall_complete = False
        else:
            start, end = utc(call["started_at"]), utc(call["ended_at"])
            if end < start:
                raise ValueError("negative call duration")
            starts.append(start); ends.append(end)
    return {"calls": len(calls), "measured": usage_complete,
            "usage": usage if usage_complete else None,
            "total_cost_usd": printed if printed_complete else None,
            "priced_cost_usd": priced if usage_complete else None,
            "wall_seconds": (max(ends) - min(starts)).total_seconds() if wall_complete else None,
            "vendors": vendors, "price_date": price_table.get("as_of")}


def spent_since(spend, start):
    totals = dict.fromkeys(CAPS, Decimal(0))
    start = utc(start)
    for record in spend:
        if record["vendor"] not in CAPS:
            raise ValueError("unknown capped vendor")
        if utc(record["at"]) >= start:
            totals[record["vendor"]] += amount(record["usd"])
    return totals


def over_cap(totals):
    return sum(totals.values()) > TOTAL_CAP or any(totals[v] > CAPS[v] for v in CAPS)


def walk_gate(walks, spend, start):
    spent = spent_since(spend, start)
    projected = spent.copy()
    for walk in walks:
        if batch.agent_problems(walk) or not walk.get("model"):
            raise ValueError("walk requires model and agent")
        vendor, n = walk["vendor"], walk["tries_left"]
        if vendor not in CAPS or type(n) is not int or n < 0:
            raise ValueError("walk vendor or remaining tries invalid")
        projected[vendor] += amount(walk["cost_per_try"]) * n
    return {"decision": STOP_FOR_WORD if over_cap(projected) else PROCEED,
            "remaining": {v: CAPS[v] - spent[v] for v in CAPS}, "projected": projected}


def month_turn_allowed(arm, now, trimmed):
    if arm not in ("O", "G"):
        return True
    now = utc(now)
    # A dated release is needed for the current month, and for the coming month
    # once its 23:30 hold has started. It cannot be inferred from elapsed time.
    year, month = now.year, now.month
    if now.day == calendar.monthrange(year, month)[1] and (now.hour, now.minute) >= (23, 30):
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    wanted = f"{year:04d}-{month:02d}"
    if not isinstance(trimmed, dict) or set(trimmed) != {"kind", "by", "month", "at", "figures"}:
        return False
    if trimmed["kind"] != "caps trimmed" or trimmed["by"] != "Javier" or trimmed["month"] != wanted:
        return False
    try:
        if utc(trimmed["at"]) > now or set(trimmed["figures"]) != set(CAPS):
            return False
        return all(amount(trimmed["figures"][v]) <= CAPS[v] for v in CAPS)
    except (KeyError, TypeError, ValueError):
        return False


def render(derived):
    return "# Costs\n\n" + json.dumps(derived, indent=2, sort_keys=True, default=str) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        calls = json.loads(CALLS.read_text()) if CALLS.exists() else []
        if not isinstance(calls, list):
            raise ValueError("cost calls must be a list")
        if not calls:
            print("costs: no takes; no cost measured or written")
            return 0
        value = render(account(calls, prereg.require_frozen("publishing per-call costs")["price_table"]))
        if args.write:
            PAGE.write_text(value)
        elif args.check and (not PAGE.exists() or PAGE.read_text() != value):
            raise ValueError("COSTS.md differs from per-call accounting")
        elif not args.check:
            print(value, end="")
        print(f"costs: {len(unique_calls(calls))} calls checked")
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"costs: REFUSE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
