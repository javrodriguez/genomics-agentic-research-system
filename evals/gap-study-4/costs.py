#!/usr/bin/env python3
"""Per-call usage, vendor prices, printed total_cost_usd, and elapsed wall time.

The round's per-call correction supersedes the copied reader's refusal to read
harness dollar figures. Repeated fragments of one call count once; conflicting
fragments refuse. Prices are supplied in a dated table, never embedded here.
wall_seconds is the first-start to last-end span, including overlap and gaps.
The normalized call list is cost-calls.json; build_draft supplies price_table in
the pre-registration. Drivers must supply call IDs, usage and timestamps from
their vendor records. Missing measurements remain unmeasured, never zero.
cost_calls.py assembles cost-calls.json from the committed takes, every arm (lane pf1-cost-vendors).

THE PRICE VARIANTS (lane pf1-l4-close, Sun 25 Oct 2026; the lane orchestrator's rulings on review
REVIEW-pf1-l4-close-291b357, M1 and m5: build what the approved price table's page promised). The pre-registration's
price_variants, which build_draft derives from the approved table's own rows, carry what the four prices per model
cannot: per model, the cache-write row of each duration, and the over-threshold rows of a model the table prices by
prompt length (arm O's long context over 272K input tokens; claude-haiku-5-5 over 100,000 prompt tokens), with each
vendor's "API-equivalent, not billed" label. With them, account() prices each call on its own (price_call): a prompt
over its model's threshold (the three input classes together) is priced at the over-threshold rows and flagged; cache
writes are split by the duration the call records (cache_write_durations) and each part priced at its own row, and an
unrecorded split is priced at the longer duration's row, the stated conservative bound, and said so in the call's
record; every arm A and arm O priced cost carries its label. cost_statement() writes, from the variants, what is built
and, labelled NOT_BUILT, what the table cannot support. Without variants account() prices as it did before.

Round caps cover vendor-read spend since the round began, across all months.
walk_gate and month_turn_allowed are pure functions; batch.Batch invokes them before each wave is registered (lane w7c),
month_turn_allowed again before each paid launch. No account lookup, price lookup or human ruling is inferred.
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
import study

# Javier's "gcap-220 yes" (decision OD107, ask gcap-220, Thu 22 Oct 2026 14:43:19Z): Google 220 so a later go of the
# deferred arm G runs exactly as registered; OpenAI 180 (arm O runs on the Codex subscription and spends nothing); the
# 400 total unchanged. Before: OpenAI 260, Google 140.
CAPS = {"openai": Decimal(180), "google": Decimal(220)}
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


# ---- the price variants (lane pf1-l4-close; see THE PRICE VARIANTS above) -----------------------------------------
# The cache-write durations each vendor's rows price (the approved table's 5m and 1h, 30m and 12h writes), and the
# longer one, which the four prices per model hold as the conservative bound (the table's lead rulings 1 and 2).
CACHE_DURATIONS = {"anthropic": ("5m", "1h"), "openai": ("30m", "12h")}
BOUND_DURATION = {"anthropic": "1h", "openai": "12h"}
BOUND_RULING = {"anthropic": "the price table's lead ruling 1", "openai": "the price table's lead ruling 2"}
WRITE = "cache_creation_input_tokens"
INPUT_CLASSES = ("input_tokens", "cache_read_input_tokens", WRITE)
LABEL_PREFIX = "API-equivalent, not billed"
VARIANT_KEYS = ("source", "labels", "cache_write", "over")
OVER_KEYS = ("over_prompt_tokens", "threshold_words", "reading", "prices", "cache_write", "flag")
NOT_BUILT = "not built in round 4"
# What the approved table's rows and follow-ups name and this step does not do, each said as what the code does.
NOT_BUILT_ITEMS = (
    "Codex's service_tier is not read, so every Codex call is priced at the table's Standard rows and never at its "
    "Fast, Ultrafast, Flex or Batch rows (the table's follow-up on the tier).",
    "Claude Code's speed and inference_geo are not read, so every Claude call is priced at the standard rows and never "
    "at the table's fast-mode rows.",
    "Google's hourly cache storage is not priced: it stays outside the per-token schema (the table's lead ruling 3 and "
    "its residual).",
    "A Gemini run on or after 1 Jan 2027 is not re-priced: gemini-3.8-flash is priced at the table's price through 31 "
    "Dec 2026, and re-reading Google's page on the run day, then publishing a re-pricing as a declared deviation, needs "
    "that day's page (the table's lead ruling 5 and its follow-ups on the Gemini run day).",
    "drive.py writes a driver ledger cost for claude-code takes only: an arm O or arm G take's ledger cost stays None, "
    "and its calls are read from the take's retained records when cost-calls.json is assembled (cost_calls.py), not "
    "by the driver (drive.py is a reader source both acceptance records bind).",
    "Gemini's tool-use prompt tokens are not priced: the approved table names no row for them, so a Gemini take with "
    "a call that records any is assembled as one unmeasured call (cost_calls.unpriced_problem).",
    "Arm G is not priced per take from its result stats: a take whose session file records fewer calls than its "
    "stats count stays unmeasured (pricing it from the stats is a scope that goes to Javier with arm G's go).",
)
# Lane pf1-cost-vendors (26 Oct 2026): what cost_calls.py builds, said as what it does; cost_statement carries each.
ASSEMBLY_BUILT = (
    "cost-calls.json is assembled by cost_calls.py from every committed outcome's take folder: an arm A take's calls "
    "are its driver ledger's cost calls and the calls of each sub-agent file the take copied; an arm O take's calls "
    "are its last retained rollout's token_usage_record lines, one per response id; an arm G take's calls are its "
    "replayed session file's gemini messages that record tokens",
    "an arm O call's usage is mapped from the Responses API's counts: input is input less cached and written, cache "
    "read is cached, cache write is written, output is output; that cached input and reasoning are parts of input "
    "and output is what every recorded call shows (its total is its input plus its output); that written input is a "
    "part of input is read from the pinned source alone (openai/codex 092d3acd, "
    "codex-api/src/sse/responses.rs:128-143 and its test at :846-870), because no recorded call writes to the cache; "
    "Codex records no write duration, so its writes are priced at the 12h row, the stated bound",
    "an arm G call's usage is mapped from the session file's tokens: input is input less cached, cache read is cached, "
    "output is output plus thoughts (priced at the output row, which Google's page says includes thinking tokens); "
    "Gemini records no cache write",
    "a take whose calls cannot all be read, or checked against the totals its turn streams print (Codex's thread "
    "totals; Gemini's result stats, per model, on input, output, cached and total, so thoughts and tool-use tokens "
    "are checked together through the total, never apart), is assembled as one unmeasured call; one unmeasured call "
    "makes its vendor's priced total and the round-wide usage and priced total read unmeasured, never a partial sum",
    "on 26 Oct 2026, 32 of 36 committed arm G walks assemble as unmeasured (their session files record fewer calls "
    "than their result stats count), so arm G's priced total, and with it the round-wide total, will most likely "
    "publish as unmeasured if arm G runs",
    # Lane gap-subagent-cost (28 Oct 2026, glitch-45's ruling (b) on the D8 claude-code read's finding 1, and its
    # rulings on review edb48b6: MAJOR 1 option (c), MINOR 2 and MINOR 3).
    "an arm A take delegated when a sub-agent file was copied or its main session file holds an Agent tool call; a "
    "take that did not delegate is priced from its driver ledger's calls alone, as before, a cut or timed-out turn "
    "included",
    "a delegating arm A take's sub-agent calls are read from each sub-agent file the take copied "
    "(subagents/**/agent-<id>.jsonl, at any depth as drive.py copies it), its bytes bound by the driver ledger's "
    "sha256, because Claude Code's driver ledger records the main session file's calls alone; that file writes one "
    "call as several fragments whose output count grows, so a call is read once per message id and request id, its "
    "fragments must agree on the model, the input, cache-read and cache-write counts and the 5m and 1h write split, "
    "output may never decrease, and the last fragment is kept; any other shape makes the take one unmeasured call",
    "a delegating arm A take's calls, the main session's and its sub-agents' together, must sum per model and token "
    "class to the modelUsage the CLI prints in the last turn that prints one (the session's running total, its "
    "sub-agents included); a delegating take whose calls do not (a cut or timed-out last turn included), that has no "
    "modelUsage, or whose session calls Agent with no sub-agent file copied, is assembled as one unmeasured call, never "
    "priced from a partial sum, and that one call makes arm A's priced total, and with it the round-wide usage and "
    "priced total, read unmeasured",
    "the 5m and 1h cache-write split each arm A call records is priced as recorded and is not reconciled: modelUsage "
    "prints no split, and its own costUSD is not used as a check, because the CLI's built-in prices may differ from the "
    "frozen price table",
    "on 28 Oct 2026, 2 of 277 committed arm A walks hold a sub-agent file (w255 and w260, both Haiku 4.5 on "
    "plan-gate); with their sub-agent calls they price to $0.24809 and $0.19266, the CLI's own printed session totals, "
    "against $0.14670 and $0.05474 from their main sessions alone; 277 of 277 committed arm A walks reconcile",
    "an arm A turn's total_cost_usd in the driver ledger is the session's running total as the CLI prints it, not "
    "that turn's own, which claude_code_adapter.py lines 47-48 do not say (that file is checker code and is not "
    "edited before the freeze); no step adds it up and no call carries it, so arm A's printed total reads unmeasured "
    "and only the priced total is published",
)


def _price_map(value, what):
    if not isinstance(value, dict) or set(value) != set(CLASSES):
        raise ValueError(f"{what} prices every token class {CLASSES}")
    for price in value.values():
        amount(price)


def _write_map(value, vendor, what):
    if not isinstance(value, dict) or set(value) != set(CACHE_DURATIONS[vendor]):
        raise ValueError(f"{what} prices each cache-write duration {CACHE_DURATIONS[vendor]}")
    for price in value.values():
        amount(price)


def validate_variants(variants, price_table):
    """The variants' closed shape, and their agreement with the four prices per model: every anthropic and openai model
    of the table has a cache-write row per duration, the longer duration's being the table's cache-write price (the
    stated bound); each over-threshold entry is a positive token count with its rows; each of the two labels opens
    with LABEL_PREFIX. Raises ValueError."""
    require_price_date(price_table)
    if not isinstance(variants, dict) or set(variants) != set(VARIANT_KEYS):
        raise ValueError(f"price variants hold exactly {VARIANT_KEYS}")
    labels = variants["labels"]
    if not isinstance(labels, dict) or set(labels) != set(CACHE_DURATIONS) or not all(
            isinstance(v, str) and v.startswith(LABEL_PREFIX) for v in labels.values()):
        raise ValueError(f"price variants label {sorted(CACHE_DURATIONS)}, each opening {LABEL_PREFIX!r}")
    for vendor in CACHE_DURATIONS:
        for model, prices in price_table["vendors"].get(vendor, {}).items():
            writes = (variants["cache_write"].get(vendor) or {}).get(model)
            _write_map(writes, vendor, f"{vendor}/{model}")
            if WRITE in prices and amount(writes[BOUND_DURATION[vendor]]) != amount(prices[WRITE]):
                raise ValueError(f"{vendor}/{model}: the table's cache-write price is not its {BOUND_DURATION[vendor]} "
                                 f"row, the stated bound")
    for vendor, models in variants["over"].items():
        for model, over in models.items():
            if model not in price_table["vendors"].get(vendor, {}):
                raise ValueError(f"{vendor}/{model}: an over-threshold entry for a model the table does not price")
            if not isinstance(over, dict) or set(over) != set(OVER_KEYS):
                raise ValueError(f"{vendor}/{model}: an over-threshold entry holds exactly {OVER_KEYS}")
            if type(over["over_prompt_tokens"]) is not int or over["over_prompt_tokens"] <= 0:
                raise ValueError(f"{vendor}/{model}: the threshold is a positive token count")
            if not all(isinstance(over[k], str) and over[k] for k in ("threshold_words", "reading", "flag")):
                raise ValueError(f"{vendor}/{model}: the threshold's words, reading and flag are text")
            _price_map(over["prices"], f"{vendor}/{model} over its threshold")
            _write_map(over["cache_write"], vendor, f"{vendor}/{model} over its threshold")


def prompt_tokens(usage):
    """A call's prompt length: its three input classes together (the classes are disjoint)."""
    return sum(usage.get(c, 0) for c in INPUT_CLASSES)


def tier_for(vendor, model, usage, prices, variants):
    """(the prices, the cache-write rows, the flag or None) one call is priced at: its model's over-threshold rows when
    it has them and the call's prompt is over the threshold, else the four prices and the standard cache-write rows."""
    over = variants["over"].get(vendor, {}).get(model)
    if over is not None and prompt_tokens(usage) > over["over_prompt_tokens"]:
        return over["prices"], over["cache_write"], over["flag"]
    return prices, variants["cache_write"].get(vendor, {}).get(model), None


def cache_write_cost(vendor, call, count, prices, writes):
    """(cost, note) of a call's cache writes: split by the durations the call records (cache_write_durations, which
    must name the vendor's durations and sum to its cache writes), each part at its own row; with no recorded split,
    the whole at the longer duration's row, the stated bound, and the note says so. A vendor with no duration rows
    (google) prices them at the table's cache-write price, with no note."""
    if not count:
        return Decimal(0), None
    if writes is None:
        return Decimal(count) * amount(prices[WRITE]) / 1000000, None
    durations, split = CACHE_DURATIONS[vendor], call.get("cache_write_durations")
    if split is None:
        bound = BOUND_DURATION[vendor]
        return (Decimal(count) * amount(writes[bound]) / 1000000,
                f"duration not recorded: all {count} cache-write tokens priced at the {bound} row, the stated "
                f"conservative bound ({BOUND_RULING[vendor]})")
    if (not isinstance(split, dict) or set(split) != set(durations)
            or not all(type(v) is int and v >= 0 for v in split.values()) or sum(split.values()) != count):
        raise ValueError(f"a recorded cache-write split names exactly {durations} and sums to the call's {count} "
                         f"cache-write tokens")
    cost = Decimal(0)
    for d in durations:
        cost += Decimal(split[d]) * amount(writes[d]) / 1000000
    return cost, "split by recorded duration: " + ", ".join(f"{split[d]} at the {d} row" for d in durations)


def label_for(vendor, variants):
    return variants["labels"].get(vendor)


def price_call(call, prices, variants):
    """One measured call priced on its own: {vendor, call_id, model, prompt_tokens, priced_cost_usd, flags,
    cache_write, label (anthropic and openai)}."""
    usage, vendor = call["usage"], call["vendor"]
    tier, writes, flag = tier_for(vendor, call["model"], usage, prices, variants)
    cost = Decimal(0)
    for kind, count in usage.items():
        if kind != WRITE:
            cost += Decimal(count) * amount(tier[kind]) / 1000000
    wcost, note = cache_write_cost(vendor, call, usage.get(WRITE, 0), tier, writes)
    out = {"vendor": vendor, "call_id": call["call_id"], "model": call["model"], "prompt_tokens": prompt_tokens(usage),
           "priced_cost_usd": cost + wcost, "flags": [flag] if flag else [], "cache_write": note}
    label = label_for(vendor, variants)
    if label is not None:
        out["label"] = label
    return out


def cost_statement(variants):
    """The cost page's statement, generated from the variants: each built rule, then each NOT_BUILT item."""
    lines = []
    for vendor in sorted(variants["over"]):
        for model, over in sorted(variants["over"][vendor].items()):
            lines.append(f"built: a {model} call whose prompt (its input, cache-read and cache-write tokens together) "
                         f"is over {over['over_prompt_tokens']} tokens is priced at the table's {over['threshold_words']} "
                         f"rows and its record flagged \"{over['flag']}\"; {over['reading']}")
    for vendor in sorted(CACHE_DURATIONS):
        a, b = CACHE_DURATIONS[vendor]
        lines.append(f"built: each {vendor} call's cache writes are priced at the {a} and {b} rows by the durations it "
                     f"records; with none recorded, all at the {BOUND_DURATION[vendor]} row, the stated conservative "
                     f"bound ({BOUND_RULING[vendor]}), and the call's record says so")
    for vendor, label in sorted(variants["labels"].items()):
        lines.append(f"built: every {vendor} priced cost carries the label \"{label}\"")
    lines += [f"built: {line}" for line in ASSEMBLY_BUILT]
    return lines + [f"{NOT_BUILT}: {item}" for item in NOT_BUILT_ITEMS]


def account(calls, price_table, variants=None):
    require_price_date(price_table)
    calls = unique_calls(calls)
    usage = dict.fromkeys(CLASSES, 0)
    priced = Decimal(0)
    printed = Decimal(0)
    usage_complete = printed_complete = bool(calls)
    starts, ends = [], []
    wall_complete = bool(calls)
    vendors = {}
    if variants is not None:
        validate_variants(variants, price_table)
    priced_calls = []
    for call in calls:
        if batch.agent_problems(call):
            raise ValueError("call requires model and agent with harness and version")
        if not isinstance(call.get("model"), str) or not call["model"].strip():
            raise ValueError("call requires model")
        vendor = call["vendor"]
        subtotal = vendors.setdefault(vendor, {"calls": 0, "total_cost_usd": Decimal(0), "priced_cost_usd": Decimal(0)})
        if variants is not None and label_for(vendor, variants) is not None:
            subtotal["label"] = label_for(vendor, variants)
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
            if variants is not None:              # lane pf1-l4-close: the call priced on its own, at its rows
                one = price_call(call, prices, variants)
                cost = one["priced_cost_usd"]
                priced_calls.append(one)
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
    out = {"calls": len(calls), "measured": usage_complete,
           "usage": usage if usage_complete else None,
           "total_cost_usd": printed if printed_complete else None,
           "priced_cost_usd": priced if usage_complete else None,
           "wall_seconds": (max(ends) - min(starts)).total_seconds() if wall_complete else None,
           "vendors": vendors, "price_date": price_table.get("as_of")}
    if variants is not None:                      # lane pf1-l4-close: each measured call's own record
        out["calls_priced"] = priced_calls
    return out


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
    # W5B2-3: unknown arms fail closed. O and G are the ruled vendor arms,
    # independent of which arms the active design has admitted so far.
    if arm not in study.ARMS:
        return False
    if arm not in ("O", "G"):
        return True
    now = utc(now)
    # Only the last day's 23:30 UTC window requires a next-month release.
    # Outside that window no current-month record is required (W5B1-3).
    year, month = now.year, now.month
    if now.day != calendar.monthrange(year, month)[1] or (now.hour, now.minute) < (23, 30):
        return True  # outside the month-turn hold
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


def render(derived, statement=None):
    """COSTS.md: the statement's lines (cost_statement), when given, then the accounting."""
    head = "".join(f"- {line}\n" for line in statement) + "\n" if statement else ""
    return "# Costs\n\n" + head + json.dumps(derived, indent=2, sort_keys=True, default=str) + "\n"


def frozen_inputs(pre):
    """(price_table, price_variants) of the frozen pre-registration, the variants validated against the table; refuses
    a pre-registration without variants (lane pf1-l4-close), so no cost page is written at the four prices alone."""
    variants = pre.get("price_variants")
    if variants is None:
        raise ValueError("the frozen pre-registration carries no price_variants, which the cost step prices by")
    validate_variants(variants, pre["price_table"])
    return pre["price_table"], variants


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
        table, variants = frozen_inputs(prereg.require_frozen("publishing per-call costs"))
        value = render(account(calls, table, variants), cost_statement(variants))
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
