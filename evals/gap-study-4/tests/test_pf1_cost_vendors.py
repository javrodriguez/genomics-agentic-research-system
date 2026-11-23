#!/usr/bin/env python3
"""Lane pf1-cost-vendors: cost-calls.json assembled for every arm (cost_calls.py), and the cost statement that says so.

    python3 -B -W ignore evals/gap-study-4/tests/test_pf1_cost_vendors.py

Each case is one check returning its problems (empty when it holds). The fixtures are committed walk records, read in
place or copied into a temporary, writable take folder (takes/<slot>/<attempt>/); no committed record is written
(test_no_committed_record_changed holds it), and the cases that need a broken record break only their temporary copy.
The expected values are derived here with plain json, never
through cost_calls' helpers, and prices are read from the approved table's own rows by their variant names.
  V1  arm O mapping on walk w-o46 (gpt-6.1-sol, three resumed turns): one call per token_usage_record, call id its
      response id, usage input less cached and written, cache read cached, cache write written, output output, the
      vendor's counts kept as recorded, the unrecorded fields named and None.
  V2  every committed arm O walk assembles complete, its calls summing to its last turn.completed total.
  V3  arm O priced on walk w-o47 (gpt-6-luna) at the table's standard short-context rows, with arm O's label.
  V4  arm O incompleteness: a record removed, a running total or a printed turn total off by one, a turn.completed
      removed, a reroute, changed snapshot bytes: each copy
      assembles as one unmeasured call, and its vendor's priced total reads unmeasured.
  V5  arm G mapping on walk w-g30 (gemini-3.5-flash-lite, complete): input less cached, output plus thoughts, cache
      read cached, no cache write class.
  V6  arm G incompleteness: walk w-g21 (its session file records fewer tokens than its result stats), w-g24 (a turn
      with no result stats), w-g13 (a tokens record with no model): each one unmeasured call; on copies of w-g30, a
      call's thoughts off by one (with its total, so only the stats' total_tokens can tell) and a call with tool-use
      prompt tokens: each one unmeasured call (review aa4394c MAJOR-1 and NIT-1).
  V7  arm A: the ledger's cost calls unchanged (walk w001, no sub-agent); a ledger cost of None is one unmeasured
      call.
  V8  assemble: every committed outcome once, in commit order, rulings skipped; a take whose outcome says its drive
      never started (drive_started False) and that holds nothing is no call; one whose outcome does not say so, with
      no folder or no streams, is one unmeasured call (review MINOR-2); streams with no ledger are one unmeasured
      call; the assembly is accounted by costs.account across the three vendors.
  V9  the statement: the old "no step assembles" line is gone, each ASSEMBLY_BUILT line is a built line, the remaining
      not-built items are named, the round-wide and arm G consequences are said, and its arm G walk count is what
      the walks give; the draft carries costs.cost_statement of its variants.
  V10 cost_calls.main: --write then --check holds; a changed cost-calls.json is refused.
  V11 the closure review's observation 1 on the records: Codex's cached tokens are a part of its input_tokens
      (total_tokens is input + output on every recorded call), so each call's mapped prompt is its input_tokens once.
  V12 the closure review's observation 2: test_pf1_cost_step's C1 and C2/C3 rules on recorded Codex usage.
  V13 review MAJOR-2: synthetic Codex usages with cache writes (no recorded call writes), in the pinned source's own
      test shape (cached 40, written 60, the input their sum) and with fresh input too: mapped and priced by hand.
  Lane gap-subagent-cost (28 Oct 2026, glitch-45's ruling (b) on the D8 claude-code read's findings 1, 2 and 4):
  V14 arm A with a sub-agent (w255, w260): the ledger's calls unchanged, then one call per sub-agent call id with its
      last fragment's counts and split, derived here by plain json; priced, the CLI's own printed session total.
  V15 the committed arm A walks: 277 of 277 measured and reconciled per model to their last modelUsage, the ones with
      no sub-agent file unchanged, and the statement's counts are these.
  V16 the fragment rule on rewritten copies of w255 (sha256 rebound; modelUsage moved where a mutant would keep the
      change): an unchanged rewrite stays measured; each break of the rule is one unmeasured call.
  V17 the sub-agent file's binding: sha256, an unnamed file, a missing file, a path outside subagents/, a call id twice.
  V18 the reconciliation: off by one token, the sub-agent file gone (the finding's undercount), no modelUsage with a
      sub-agent file, another model's modelUsage; with neither modelUsage nor sub-agent file, as before this lane.
  V19 the statement's arm A figures and the two limitation lines (findings 2 and 4), each figure derived from records.
MUTANTS: each weakens one rule in memory, and the case it names must then report a problem. Stdlib only.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_draft as b  # noqa: E402
import cost_calls as cc  # noqa: E402
import costs  # noqa: E402

WALKS = HERE / "rehearsals"
TABLE = json.loads((REPO / b.PRICE_TABLE_FILE).read_bytes())
DRAFT = json.loads((HERE / "prereg-draft.json").read_text())
PRICES, VARIANTS = DRAFT["price_table"], DRAFT["price_variants"]
MTOK = Decimal(1000000)
OLD_LINE = "No step assembles cost-calls.json"


def row_price(vendor, model, token_class, variant):
    (got,) = [r["price_usd"] for r in TABLE["rows"]
              if (r["vendor"], r["model"], r["token_class"], r["variant"]) == (vendor, model, token_class, variant)]
    return Decimal(got)


def jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").split("\n") if x.strip()]


def ledger_of(walk):
    return json.loads((WALKS / walk / "driver-ledger.json").read_text())


def row_of(walk, slot=1, attempt=1):
    led = ledger_of(walk)
    return {"slot": slot, "attempt": attempt, "agent": led["agent"], "model": led["model_requested"]}


@contextlib.contextmanager
def take_copy(walk, slot=1, attempt=1):
    """A writable copy of a committed walk laid out as takes/<slot>/<attempt>/ under a temporary root."""
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / "takes" / str(slot) / str(attempt)
        shutil.copytree(WALKS / walk, dst)
        yield Path(tmp), dst


def last_snapshot(walk):
    return WALKS / walk / "session" / ledger_of(walk)["native_snapshots"][-1]["file"]


def records_of(walk):
    return [r["payload"] for r in jsonl(last_snapshot(walk)) if r.get("type") == "token_usage_record"]


def last_turn_completed(walk):
    led = ledger_of(walk)
    got = [r["usage"] for r in jsonl(WALKS / walk / led["streams"][-1]) if r.get("type") == "turn.completed"]
    return got[-1]


def unmeasured_only(calls, vendor):
    return len(calls) == 1 and calls[0]["usage"] is None and calls[0]["vendor"] == vendor and cc.UNMEASURED in calls[0]


# ---- the cases ------------------------------------------------------------------------------------------------------
def v1_codex_mapping():
    out = []
    calls = cc.take_calls(WALKS / "w-o46", row_of("w-o46"))
    recs = records_of("w-o46")
    if len(calls) != len(recs) or not recs:
        return [f"V1: {len(calls)} calls for {len(recs)} token_usage_record lines"]
    for c, p in zip(calls, recs):
        u = p["usage"]
        want = {"input_tokens": u["input_tokens"] - u["cached_input_tokens"] - u["cache_write_input_tokens"],
                "output_tokens": u["output_tokens"], "cache_read_input_tokens": u["cached_input_tokens"],
                "cache_creation_input_tokens": u["cache_write_input_tokens"]}
        if c["usage"] != want:
            out.append(f"V1: {p['response_id']}: usage {c['usage']} is not {want}")
        if c["call_id"] != p["response_id"] or c["model"] != "gpt-6.1-sol" or c["vendor"] != "openai":
            out.append(f"V1: {p['response_id']}: id, model or vendor {c['call_id']} {c['model']} {c['vendor']}")
        if c["recorded"] != u:
            out.append(f"V1: {p['response_id']}: the recorded counts are not the vendor's")
        if any(c[k] is not None for k in ("total_cost_usd", "started_at", "ended_at", "cache_write_durations")):
            out.append(f"V1: {p['response_id']}: an unrecorded field is not None")
        if c["unrecorded"] != list(cc.UNRECORDED["openai"]) or c["agent"] != ledger_of("w-o46")["agent"]:
            out.append(f"V1: {p['response_id']}: unrecorded or agent wrong")
        if not set(cc.CALL_KEYS) <= set(c):
            out.append(f"V1: {p['response_id']}: not costs.py's call shape")
    return out


def v2_codex_all_walks():
    out, n = [], 0
    for walk in sorted(p.name for p in WALKS.glob("w-o*")):
        n += 1
        calls = cc.take_calls(WALKS / walk, row_of(walk))
        if any(c["usage"] is None for c in calls):
            out.append(f"V2: {walk} is unmeasured: {calls[0].get(cc.UNMEASURED)}")
            continue
        total = {}
        for c in calls:
            for k, v in c["recorded"].items():
                total[k] = total.get(k, 0) + v
        want = last_turn_completed(walk)
        if {k: total.get(k) for k in want} != want or len(calls) != len(records_of(walk)):
            out.append(f"V2: {walk}: the calls do not sum to the last turn.completed")
    if n != 74:                                  # lane gap-rewalk-fix: 38 + the rewalk merge's 36 arm O walks
        out.append(f"V2: {n} committed arm O walks, not 74")
    return out


def v3_codex_priced():
    calls = cc.take_calls(WALKS / "w-o47", row_of("w-o47"))
    got = costs.account(calls, PRICES, VARIANTS)
    v = "Standard, short context (<=272K input tokens)"
    want = Decimal(0)
    for p in records_of("w-o47"):                             # the vendor's counts, mapped here by hand
        u = p["usage"]
        for k, n in (("input_tokens", u["input_tokens"] - u["cached_input_tokens"] - u["cache_write_input_tokens"]),
                     ("output_tokens", u["output_tokens"]), ("cache_read_input_tokens", u["cached_input_tokens"])):
            want += Decimal(n) * row_price("openai", "gpt-6-luna", k, v) / MTOK
        if u["cache_write_input_tokens"]:
            return ["V3: w-o47 records cache writes; this case prices none"]
    out = []
    if not calls or got["priced_cost_usd"] != want:
        out.append(f"V3: priced {got['priced_cost_usd']} is not {want}")
    if got["vendors"]["openai"].get("label") != TABLE["arm_o_label"]:
        out.append("V3: the arm O subtotal lacks its label")
    return out


def _rebind(folder):
    led = json.loads((folder / "driver-ledger.json").read_text())
    ref = led["native_snapshots"][-1]
    ref["sha256"] = hashlib.sha256((folder / "session" / ref["file"]).read_bytes()).hexdigest()
    (folder / "driver-ledger.json").write_text(json.dumps(led))


def v4_codex_incomplete():
    out = []

    def drop_record(folder):
        snap = folder / "session" / json.loads((folder / "driver-ledger.json").read_text())["native_snapshots"][-1][
            "file"]
        lines = snap.read_text(encoding="utf-8").split("\n")
        k = [i for i, x in enumerate(lines) if '"token_usage_record"' in x][1]
        snap.write_text("\n".join(lines[:k] + lines[k + 1:]), encoding="utf-8")
        _rebind(folder)

    def drop_last_record(folder):
        snap = folder / "session" / json.loads((folder / "driver-ledger.json").read_text())["native_snapshots"][-1][
            "file"]
        lines = snap.read_text(encoding="utf-8").split("\n")
        k = [i for i, x in enumerate(lines) if '"token_usage_record"' in x][-1]
        snap.write_text("\n".join(lines[:k] + lines[k + 1:]), encoding="utf-8")
        _rebind(folder)

    def drop_completed(folder):
        p = folder / "turn-2.jsonl"
        p.write_text("".join(x + "\n" for x in p.read_text().split("\n") if x.strip() and "turn.completed" not in x))

    def reroute(folder):
        led = json.loads((folder / "driver-ledger.json").read_text())
        led["served_model"][1] = {"value": "gpt-6-luna", "source": "stream-reroute"}
        (folder / "driver-ledger.json").write_text(json.dumps(led))

    def change_bytes(folder):
        snap = folder / "session" / json.loads((folder / "driver-ledger.json").read_text())["native_snapshots"][-1][
            "file"]
        snap.write_bytes(snap.read_bytes() + b"\n")

    def running_off(folder):                     # a record's running total off by one, every count still summing
        snap = folder / "session" / json.loads((folder / "driver-ledger.json").read_text())["native_snapshots"][-1][
            "file"]
        lines = snap.read_text(encoding="utf-8").split("\n")
        k = [i for i, x in enumerate(lines) if '"token_usage_record"' in x][1]
        rec = json.loads(lines[k])
        rec["payload"]["thread_token_usage"]["output_tokens"] += 1
        lines[k] = json.dumps(rec)
        snap.write_text("\n".join(lines), encoding="utf-8")
        _rebind(folder)

    def printed_off(folder):                     # turn 2's printed total off by one, the records untouched
        p = folder / "turn-2.jsonl"
        recs = [json.loads(x) for x in p.read_text().split("\n") if x.strip()]
        for r in recs:
            if r.get("type") == "turn.completed":
                r["usage"]["output_tokens"] += 1
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))

    for name, broke in (("a record removed", drop_record), ("the last record removed", drop_last_record),
                        ("a running total off", running_off), ("a printed turn total off", printed_off),
                        ("turn 2's turn.completed removed", drop_completed), ("a reroute", reroute),
                        ("changed snapshot bytes", change_bytes)):
        with take_copy("w-o46") as (_, folder):
            broke(folder)
            calls = cc.take_calls(folder, row_of("w-o46"))
            if not unmeasured_only(calls, "openai"):
                out.append(f"V4: {name}: not one unmeasured call ({len(calls)} calls)")
                continue
            slot = attempt = 1
            want = f"takes/{slot}/{attempt}/unmeasured/gpt-6.1-sol"
            if calls[0]["model"] != "gpt-6.1-sol" or calls[0]["call_id"] != want:
                out.append(f"V4: {name}: the unmeasured call's model or id")
            got = costs.account(calls, PRICES, VARIANTS)
            if got["priced_cost_usd"] is not None or got["vendors"]["openai"]["priced_cost_usd"] is not None:
                out.append(f"V4: {name}: a priced total was read")
    return out


def v5_gemini_mapping():
    out = []
    calls = cc.take_calls(WALKS / "w-g30", row_of("w-g30"))
    tokens = {}
    for r in jsonl(last_snapshot("w-g30")):                  # plain json: the last tokens written for each id
        if r.get("type") == "gemini" and r.get("tokens") is not None:
            tokens[r["id"]] = (r["tokens"], r.get("model"))
    if not calls or len(calls) != len(tokens):
        return [f"V5: {len(calls)} calls for {len(tokens)} gemini messages with tokens"]
    for c in calls:
        t, model = tokens[c["call_id"]]
        want = {"input_tokens": t["input"] - t["cached"], "output_tokens": t["output"] + t["thoughts"],
                "cache_read_input_tokens": t["cached"]}
        if c["usage"] != want or c["model"] != model or c["vendor"] != "google" or c["recorded"] != t:
            out.append(f"V5: {c['call_id']}: {c['usage']} is not {want}")
    got = costs.account(calls, PRICES, VARIANTS)
    v = "Standard"
    want = Decimal(0)
    for c in calls:
        for k in c["usage"]:
            (p,) = [r["price_usd"] for r in TABLE["rows"] if (r["vendor"], r["model"], r["token_class"]) == (
                "google", "gemini-3.5-flash-lite", k) and r["variant"].startswith(v)]
            want += Decimal(c["usage"][k]) * Decimal(p) / MTOK
    if got["priced_cost_usd"] != want:
        out.append(f"V5: priced {got['priced_cost_usd']} is not {want}")
    if any(costs.WRITE in c["usage"] for c in calls):
        out.append("V5: a Gemini call carries a cache-write class Gemini does not record")
    return out


def _bump_gemini_tokens(folder, bump):
    """On a take copy: add `bump` to every record of the first gemini message with tokens in the last snapshot (the
    session file is an append log, so a message can be written more than once), then rebind the ledger's sha256."""
    snap = folder / "session" / json.loads((folder / "driver-ledger.json").read_text())["native_snapshots"][-1]["file"]
    recs = [json.loads(x) for x in snap.read_text(encoding="utf-8").split("\n") if x.strip()]
    (target,) = [r["id"] for r in recs if r.get("type") == "gemini" and r.get("tokens")][:1]
    for r in recs:
        if r.get("id") == target and r.get("tokens"):
            for k, v in bump.items():
                r["tokens"][k] += v
    snap.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
    _rebind(folder)


def v6_gemini_incomplete():
    out = []
    for walk, why in (("w-g21", "are not the result stats'"), ("w-g24", "holds no result stats"),
                      ("w-g13", "records tokens and no model")):
        calls = cc.take_calls(WALKS / walk, row_of(walk))
        if not unmeasured_only(calls, "google") or why not in calls[0][cc.UNMEASURED]:
            out.append(f"V6: {walk} is not one unmeasured call saying {why!r}: {calls[:1]}")
            continue
        got = costs.account(calls, PRICES, VARIANTS)
        if got["vendors"]["google"]["priced_cost_usd"] is not None:
            out.append(f"V6: {walk}: a priced Gemini total was read")
    for name, bump in (("a call's thoughts off by one", {"thoughts": 1, "total": 1}),
                       # five thought tokens recorded as tool-use tokens instead: every total still agrees with the
                       # stats, so only the unpriced tool-use tokens can make the take unmeasured
                       ("a call with tool-use prompt tokens", {"thoughts": -5, "tool": 5})):
        with take_copy("w-g30") as (_, folder):
            _bump_gemini_tokens(folder, bump)
            calls = cc.take_calls(folder, row_of("w-g30"))
            if not unmeasured_only(calls, "google"):
                out.append(f"V6: w-g30 with {name} is not one unmeasured call ({len(calls)} calls)")
    t = {"input": 120, "output": 5, "cached": 40, "thoughts": 3, "tool": 7, "total": 135}
    if cc.gemini_usage(t) is not None:
        out.append("V6: tool-use prompt tokens were priced")
    t["tool"] = 0
    t["total"] = 128
    if cc.gemini_usage(t) != {"input_tokens": 80, "output_tokens": 8, "cache_read_input_tokens": 40}:
        out.append(f"V6: gemini_usage {cc.gemini_usage(t)}")
    return out


def v7_claude():
    out = []
    led = ledger_of("w001")
    calls = cc.take_calls(WALKS / "w001", row_of("w001"))
    if calls != led["cost"]["calls"] or not calls:
        out.append("V7: arm A's calls are not the ledger's cost calls")
    with take_copy("w001") as (_, folder):
        led["cost"] = None
        (folder / "driver-ledger.json").write_text(json.dumps(led))
        calls = cc.take_calls(folder, row_of("w001"))
        if not unmeasured_only(calls, "anthropic") or calls[0]["model"] != led["model_requested"]:
            out.append("V7: a ledger cost of None is not one unmeasured call")
    return out


def v8_assemble():
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for slot, walk in ((1, "w-o47"), (2, "w001"), (4, "w-o46")):
            shutil.copytree(WALKS / walk, root / "takes" / str(slot) / "1")
        (root / "takes" / "3" / "1").mkdir(parents=True)                 # a take refused before any turn ran
        shutil.copytree(WALKS / "w-o46", root / "takes" / "4" / "2")
        (root / "takes" / "4" / "2" / "driver-ledger.json").unlink()      # streams, no ledger
        (root / "takes" / "6" / "1").mkdir(parents=True)                 # a started take whose folder holds nothing
        rows = [row_of("w-o47", 1), row_of("w001", 2), dict(row_of("w001", 3)), row_of("w-o46", 4),
                row_of("w-o46", 4, 2), row_of("w-o47", 5), row_of("w001", 6)]
        from graders import labels4
        # slot 4's attempt 1 has a ruling and no outcome: a ruling is never an outcome, so its calls are not assembled;
        # slot 3 never reached its drive (drive_started False); slot 5 has no folder and slot 6 an empty one, and
        # neither outcome says its drive never started
        history = [{"slot": 2, "attempt": 1, "drive_started": True}, {"slot": 1, "attempt": 1},
                   {"slot": 3, "attempt": 1, "drive_started": False},
                   {"slot": 2, "attempt": 1}, {"kind": labels4.RULING, "slot": 4, "attempt": 1},
                   {"slot": 4, "attempt": 2}, {"slot": 5, "attempt": 1, "drive_started": True},
                   {"slot": 6, "attempt": 1}]
        got = cc.assemble(rows, history, root=root)
        a = [c["call_id"] for c in ledger_of("w001")["cost"]["calls"]]
        o = [p["response_id"] for p in records_of("w-o47")]
        un = [f"takes/{s}/{k}/unmeasured/{m}" for s, k, m in ((4, 2, "gpt-6.1-sol"), (5, 1, "gpt-6-luna"),
                                                             (6, 1, ledger_of("w001")["model_requested"]))]
        want_ids = a + o + un
        if [c["call_id"] for c in got] != want_ids:
            out.append(f"V8: assembled {len(got)} calls, not the {len(want_ids)} of the outcomes once each in order")
        acct = costs.account(got, PRICES, VARIANTS)
        if set(acct["vendors"]) != {"anthropic", "openai"} or acct["vendors"]["openai"]["priced_cost_usd"] is not None:
            out.append(f"V8: the account's vendors {acct['vendors']}")
        if acct["priced_cost_usd"] is not None or acct["usage"] is not None:
            out.append("V8: one unmeasured call left the round-wide total measured")
        for c in got:
            if cc.UNMEASURED in c and (c.get("recorded", 0) is not None or "usage" not in c.get("unrecorded", ())):
                out.append(f"V8: unmeasured call {c['call_id']} does not carry recorded None and its unrecorded")
        clean = cc.assemble(rows[:3], history[:4], root=root)
        if costs.account(clean, PRICES, VARIANTS)["vendors"]["anthropic"]["priced_cost_usd"] is None:
            out.append("V8: arm A's priced total was lost")
    return out


def v9_statement():
    out = []
    lines = costs.cost_statement(VARIANTS)
    if any(OLD_LINE in ln for ln in lines):
        out.append("V9: the statement still says no step assembles cost-calls.json")
    for line in costs.ASSEMBLY_BUILT:
        if f"built: {line}" not in lines:
            out.append(f"V9: the statement lacks the built line {line[:40]!r}")
    for needle in ("drive.py writes a driver ledger cost for claude-code takes only",
                   "tool-use prompt tokens are not priced", "service_tier is not read",
                   "not priced per take from its result stats"):
        if not any(ln.startswith(costs.NOT_BUILT + ": ") and needle in ln for ln in lines):
            out.append(f"V9: no not-built line names {needle!r}")
    walks = sorted(p.name for p in WALKS.glob("w-g*"))
    unread = [w for w in walks if any(cc.UNMEASURED in c for c in cc.take_calls(WALKS / w, row_of(w)))]
    for needle in ("checked together through the total", "round-wide usage and priced total",
                   f"{len(unread)} of {len(walks)} committed arm G walks", "codex-api/src/sse/responses.rs:128-143",
                   "no recorded call writes to the cache"):
        if not any(ln.startswith("built: ") and needle in ln for ln in lines):
            out.append(f"V9: no built line says {needle!r}")
    if (len(unread), len(walks)) != (32, 36):
        out.append(f"V9: {len(unread)} of {len(walks)} arm G walks unmeasured, not the 32 of 36 this case expects")
    if any("are not checked" in ln for ln in lines):
        out.append("V9: the statement still says Gemini's thoughts are not checked")
    if DRAFT.get("cost_statement") != costs.cost_statement(DRAFT.get("price_variants")):
        out.append("V9: the draft's cost_statement is not costs.cost_statement of its price_variants")
    return out


def v10_main():
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copytree(WALKS / "w-o47", root / "takes" / "1" / "1")
        calls = root / "cost-calls.json"
        rows, history = [row_of("w-o47")], [{"slot": 1, "attempt": 1}]
        real = cc.assemble
        with mock.patch.object(cc, "CALLS", calls), mock.patch("takes.load_rows", return_value=rows), \
                mock.patch("takes.read_history", return_value=history), \
                mock.patch("takes._git_at", return_value=""), \
                mock.patch.object(cc, "assemble", lambda r, h: real(r, h, root=root)), \
                contextlib.redirect_stdout(io.StringIO()):
            if cc.main(["--write"]) != 0 or cc.main(["--check"]) != 0:
                out.append("V10: --write then --check does not hold")
            if json.loads(calls.read_text()) != cc.take_calls(root / "takes" / "1" / "1", rows[0]):
                out.append("V10: the written cost-calls.json is not the take's calls")
            calls.write_text(calls.read_text().replace('"gpt-6-luna"', '"gpt-6.1-sol"', 1))
            if cc.main(["--check"]) != 1:
                out.append("V10: a changed cost-calls.json was not refused")
    return out


def all_codex_records():
    """(walk, token_usage_record payload) of every committed arm O walk, read with plain json."""
    return [(walk, p) for walk in sorted(x.name for x in WALKS.glob("w-o*")) for p in records_of(walk)]


def v11_codex_prompt_once():
    """The closure review's observation 1, settled on the records: every recorded Codex call's total_tokens is its
    input_tokens plus its output_tokens, while most calls record cached tokens too, so cached_input_tokens is a part of
    input_tokens, never an addend. Each call's mapped prompt (costs.prompt_tokens) is its recorded input_tokens, once.
    Walk w-o46's first call: input 13197, cached 9600, output 97, total 13294 = 13197 + 97; summed as is, the prompt
    would read 22797."""
    out, cached = [], 0
    recs = all_codex_records()
    for walk, p in recs:
        u = p["usage"]
        cached += u["cached_input_tokens"] > 0
        if u["total_tokens"] != u["input_tokens"] + u["output_tokens"]:
            out.append(f"V11: {walk} {p['response_id']}: total_tokens is not input + output")
    if len(recs) != 589 or cached < 1:           # lane gap-rewalk-fix: 305 + the rewalk's 284; 549 of 589 cached
        out.append(f"V11: {len(recs)} records, {cached} with cached tokens (the walks hold 589, most cached)")
    by_id = {c["call_id"]: c for walk in sorted({w for w, _ in recs})
             for c in cc.take_calls(WALKS / walk, row_of(walk))}
    for walk, p in recs:
        if costs.prompt_tokens(by_id[p["response_id"]]["usage"]) != p["usage"]["input_tokens"]:
            out.append(f"V11: {walk} {p['response_id']}: the mapped prompt is not the recorded input_tokens")
    first = records_of("w-o46")[0]
    u, c = first["usage"], by_id[first["response_id"]]
    seen = (u["input_tokens"], u["cached_input_tokens"], u["output_tokens"], u["total_tokens"])
    if seen != (13197, 9600, 97, 13294) or costs.prompt_tokens(c["usage"]) != 13197 \
            or c["usage"]["input_tokens"] != 3597:
        out.append(f"V11: w-o46's first call reads {u} and maps to {c['usage']}")
    return out


def v12_codex_rules_on_records():
    """test_pf1_cost_step's C1 and C2/C3 rules on recorded Codex usage (the closure review's observation 2).
    C1: every recorded call is priced at its model's standard short-context rows, unflagged, by hand from the table's
    rows (no recorded call reaches 272000: the largest prompt is w-o22's 56170). The long-context branch is reached on a
    recorded usage object that is over the threshold: w-o46's last token_usage_record's thread_token_usage (the
    thread's running total, a real Codex usage, not one call), prompt 308120, which must be priced at the long rows and
    flagged; read double, its prompt would be 587288. C2/C3: Codex records no write duration, so no recorded call can
    reach a split; no recorded call writes to the cache (0 of 589), so the 12h bound is priced on none and every
    recorded call's cache_write note is None."""
    out, largest = [], (0, None)
    recs = all_codex_records()
    by_id = {c["call_id"]: (w, c) for w in sorted({w for w, _ in recs}) for c in cc.take_calls(WALKS / w, row_of(w))}
    for walk, p in recs:
        w, c = by_id[p["response_id"]]
        got = costs.price_call(c, PRICES["vendors"]["openai"][c["model"]], VARIANTS)
        u = p["usage"]
        want = (Decimal(u["input_tokens"] - u["cached_input_tokens"]) * row_price("openai", c["model"], "input_tokens",
                                                                                    SHORT_ROW)
                + Decimal(u["cached_input_tokens"]) * row_price("openai", c["model"], "cache_read_input_tokens",
                                                                SHORT_ROW)
                + Decimal(u["output_tokens"]) * row_price("openai", c["model"], "output_tokens", SHORT_ROW)) / MTOK
        if got["priced_cost_usd"] != want or got["flags"] or got["cache_write"] is not None:
            out.append(f"V12: {walk} {p['response_id']}: {got['priced_cost_usd']} {got['flags']}, rows give {want}")
        if u["cache_write_input_tokens"]:
            out.append(f"V12: {walk} records a cache write; this case says none does")
        largest = max(largest, (u["input_tokens"], walk))
    if largest != (56170, "w-o22"):
        out.append(f"V12: the largest recorded prompt is {largest}")
    t = records_of("w-o46")[-1]["thread_token_usage"]
    usage = cc.codex_usage(t)
    big = {"vendor": "openai", "call_id": "w-o46-thread-total", "model": "gpt-6.1-sol", "usage": usage,
           "cache_write_durations": None}
    got = costs.price_call(big, PRICES["vendors"]["openai"]["gpt-6.1-sol"], VARIANTS)
    long_row = "Standard, long context (>272K input tokens)"
    want = (Decimal(usage["input_tokens"]) * row_price("openai", "gpt-6.1-sol", "input_tokens", long_row)
            + Decimal(usage["cache_read_input_tokens"]) * row_price("openai", "gpt-6.1-sol", "cache_read_input_tokens",
                                                                    long_row)
            + Decimal(usage["output_tokens"]) * row_price("openai", "gpt-6.1-sol", "output_tokens", long_row)) / MTOK
    if t["input_tokens"] != 308120 or got["prompt_tokens"] != 308120 or got["priced_cost_usd"] != want \
            or len(got["flags"]) != 1:
        out.append(f"V12: w-o46's thread total {t} priced {got}, long rows give {want}")
    return out


SHORT_ROW = "Standard, short context (<=272K input tokens)"


def v13_codex_cache_writes():
    """Review MAJOR-2: no recorded Codex call writes to the cache, so the written class is pinned on synthetic usages.
    The first is the pinned source's own test shape (codex-api/src/sse/responses.rs:846-870): cached 40, written 60,
    an input that is exactly their sum, output 10 with reasoning 5, total input + output. The second adds 25 fresh
    input tokens. Each is mapped and priced here by hand at gpt-6.1-sol's standard short-context rows, the writes at
    the 12h row (no duration recorded: the stated bound), and its record says so."""
    out, m = [], "gpt-6.1-sol"
    cached, written, fresh_extra = 40, 60, 25
    for fresh in (0, fresh_extra):
        inp = fresh + cached + written
        u = {"input_tokens": inp, "cached_input_tokens": cached, "cache_write_input_tokens": written,
             "output_tokens": 10, "reasoning_output_tokens": 5, "total_tokens": inp + 10}
        got = cc.codex_usage(u)
        want = {"input_tokens": fresh, "output_tokens": 10, "cache_read_input_tokens": cached,
                "cache_creation_input_tokens": written}
        if got != want:
            out.append(f"V13: fresh {fresh}: mapped {got}, not {want}")
            continue
        if costs.prompt_tokens(got) != inp:
            out.append(f"V13: fresh {fresh}: the prompt is {costs.prompt_tokens(got)}, not the recorded {inp}")
        one = {"vendor": "openai", "call_id": f"synthetic-{fresh}", "model": m, "usage": got,
               "cache_write_durations": None}
        priced = costs.price_call(one, PRICES["vendors"]["openai"][m], VARIANTS)
        hand = (Decimal(fresh) * row_price("openai", m, "input_tokens", SHORT_ROW)
                + Decimal(cached) * row_price("openai", m, "cache_read_input_tokens", SHORT_ROW)
                + Decimal(written) * row_price("openai", m, "cache_creation_input_tokens", SHORT_ROW + " 12h write")
                + Decimal(10) * row_price("openai", m, "output_tokens", SHORT_ROW)) / MTOK
        if priced["priced_cost_usd"] != hand or "12h row" not in (priced["cache_write"] or ""):
            out.append(f"V13: fresh {fresh}: priced {priced['priced_cost_usd']} {priced['cache_write']!r}, "
                       f"the rows give {hand}")
    try:
        cc.codex_usage({"input_tokens": 50, "cached_input_tokens": 40, "cache_write_input_tokens": 60,
                        "output_tokens": 1, "reasoning_output_tokens": 0, "total_tokens": 51})
        out.append("V13: cached plus written over the input was mapped")
    except cc.CostUnread:
        pass
    return out


# ---- lane gap-subagent-cost (28 Oct 2026): arm A sub-agent calls, the fragment rule, the reconciliation ------------
def sub_entry(led):
    (e,) = [e for e in led["subagents"] if e["file"].endswith(".jsonl")]
    return e


def derived_sub_calls(walk):
    """By plain json: a sub-agent file's calls, one per (message.id, requestId), the last fragment's counts and split."""
    by, order, records = {}, [], 0
    for r in jsonl(WALKS / walk / sub_entry(ledger_of(walk))["file"]):
        if r.get("type") != "assistant" or not isinstance((r.get("message") or {}).get("usage"), dict):
            continue
        records += 1
        k = (r["message"]["id"], r["requestId"])
        if k not in by:
            order.append(k)
        by[k] = r["message"]
    out = []
    for k in order:
        u = by[k]["usage"]
        out.append((f"{k[0]}/{k[1]}", by[k]["model"], {c: u[c] for c in costs.CLASSES},
                    {"5m": u["cache_creation"]["ephemeral_5m_input_tokens"],
                     "1h": u["cache_creation"]["ephemeral_1h_input_tokens"]}))
    return out, records


def model_usage_sums(led):
    """By plain json: the last non-None modelUsage of a ledger, per model, in costs.CLASSES."""
    mu = [t["model_usage"] for t in led["cost"]["turns"] if t.get("model_usage") is not None][-1]
    names = {"input_tokens": "inputTokens", "output_tokens": "outputTokens",
             "cache_read_input_tokens": "cacheReadInputTokens", "cache_creation_input_tokens": "cacheCreationInputTokens"}
    return {m: {c: e[n] for c, n in names.items()} for m, e in mu.items()}


def sums_of(calls):
    out = {}
    for c in calls:
        s = out.setdefault(c["model"], dict.fromkeys(costs.CLASSES, 0))
        for k in costs.CLASSES:
            s[k] += c["usage"][k]
    return out


EIGHT = Decimal("0.00000001")


def v14_claude_subagents():
    """w255 and w260: the ledger's calls unchanged, then the sub-agent file's calls (last fragment, its own split),
    and the priced total is the CLI's own printed session total."""
    out = []
    for walk, n_main, n_all, cli in (("w255", 20, 40, "0.24809395"), ("w260", 5, 34, "0.19266300")):
        led = ledger_of(walk)
        calls = cc.take_calls(WALKS / walk, row_of(walk))
        if any(cc.UNMEASURED in c for c in calls):
            out.append(f"V14: {walk} is unmeasured: {calls[0].get(cc.UNMEASURED)}")
            continue
        want, records = derived_sub_calls(walk)
        main, sub = calls[:len(led["cost"]["calls"])], calls[len(led["cost"]["calls"]):]
        if main != led["cost"]["calls"]:
            out.append(f"V14: {walk}: the ledger's calls are not first and unchanged")
        if [(c["call_id"], c["model"], c["usage"], c["cache_write_durations"]) for c in sub] != want:
            out.append(f"V14: {walk}: the sub-agent calls are not one per call id with the last fragment's counts and "
                       f"split")
        if (len(main), len(calls)) != (n_main, n_all) or records <= len(want):
            out.append(f"V14: {walk}: {len(main)} and {len(calls)} calls from {records} records")
        for c in sub:
            if (c["vendor"], c["agent"], c["total_cost_usd"], c["subagent"]) != (
                    "anthropic", led["agent"], None, sub_entry(led)["agent_id"]):
                out.append(f"V14: {walk}: sub-agent call {c['call_id']} vendor, agent, printed cost or subagent wrong")
                break
        printed = Decimal(str(led["cost"]["turns"][-1]["total_cost_usd"])).quantize(EIGHT)
        priced = costs.account(calls, PRICES, VARIANTS)["priced_cost_usd"]
        if priced is None or priced.quantize(EIGHT) != printed or str(printed) != cli:
            out.append(f"V14: {walk}: priced {priced} is not the CLI's printed {printed} ({cli})")
    return out


def v15_claude_all_walks():
    """Every committed arm A walk assembles measured and its calls sum, per model and class, to its last modelUsage; a
    walk without a sub-agent file assembles its ledger's calls unchanged; the statement's counts are these."""
    out, n, recon, with_sub = [], 0, 0, []
    for path in sorted(WALKS.glob("*/driver-ledger.json")):
        led = json.loads(path.read_text())
        if led["agent"]["harness"] != "claude-code":
            continue
        n += 1
        walk = path.parent.name
        calls = cc.take_calls(path.parent, row_of(walk))
        if any(cc.UNMEASURED in c for c in calls):
            out.append(f"V15: {walk} is unmeasured: {calls[0].get(cc.UNMEASURED)}")
            continue
        if sums_of(calls) == model_usage_sums(led):
            recon += 1
        else:
            out.append(f"V15: {walk}: its calls do not sum to its last modelUsage")
        if led.get("subagents"):
            with_sub.append(walk)
        elif calls != led["cost"]["calls"]:
            out.append(f"V15: {walk}: a walk with no sub-agent file did not assemble its ledger's calls unchanged")
    if (n, recon, with_sub) != (277, 277, ["w255", "w260"]):
        out.append(f"V15: {recon} of {n} arm A walks reconcile, sub-agent walks {with_sub}")
    lines = costs.cost_statement(VARIANTS)
    for needle in (f"{len(with_sub)} of {n} committed arm A walks hold a sub-agent file",
                   f"{recon} of {n} committed arm A walks reconcile"):
        if not any(ln.startswith("built: ") and needle in ln for ln in lines):
            out.append(f"V15: no built line says {needle!r}")
    return out


def _rewrite_sub(folder, change):
    """Rewrite a take copy's sub-agent file record by record (`change` edits the list in place), then rebind its
    sha256 in the ledger, so only the rule under test can refuse it."""
    led = json.loads((folder / "driver-ledger.json").read_text())
    e = sub_entry(led)
    recs = jsonl(folder / e["file"])
    change(recs, led)
    raw = ("\n".join(json.dumps(r) for r in recs) + "\n").encode("utf-8")
    (folder / e["file"]).write_bytes(raw)
    e["sha256"] = hashlib.sha256(raw).hexdigest()
    (folder / "driver-ledger.json").write_text(json.dumps(led))


def _fragments(recs):
    """{(id, requestId): [indexes of its assistant records with usage]} of a sub-agent file's records."""
    out = {}
    for i, r in enumerate(recs):
        if r.get("type") == "assistant" and isinstance((r.get("message") or {}).get("usage"), dict):
            out.setdefault((r["message"]["id"], r["requestId"]), []).append(i)
    return out


def _last_mu(led):
    return [t for t in led["cost"]["turns"] if t.get("model_usage") is not None][-1]["model_usage"]


def _with_copy(walk, change):
    with take_copy(walk) as (_, folder):
        change(folder)
        return cc.take_calls(folder, row_of(walk))


def v16_fragment_rule():
    """The fragment rule on copies of w255, each break isolated (the sha256 rebound, and where a mutant would keep a
    changed last fragment, the modelUsage moved with it): an unchanged rewrite stays measured; output decreasing, an
    earlier fragment's input, cache-read or cache-write count, model or 5m and 1h split differing, each make one
    unmeasured call. (A cache-write count that differs also breaks its split, so it is refused twice over and has no
    mutant of its own.)"""
    out = []
    in_place = cc.take_calls(WALKS / "w255", row_of("w255"))
    same = _with_copy("w255", lambda f: _rewrite_sub(f, lambda recs, led: None))
    if same != in_place or any(cc.UNMEASURED in c for c in same):
        out.append("V16: an unchanged rewrite of the sub-agent file did not assemble as the walk does")

    def multi(recs):
        return [ix for ix in _fragments(recs).values() if len(ix) >= 2 and
                recs[ix[-1]]["message"]["usage"]["output_tokens"] > recs[ix[0]]["message"]["usage"]["output_tokens"]][0]

    def output_decreases(recs, led):
        ix = multi(recs)
        last = recs[ix[-1]]["message"]["usage"]
        drop = last["output_tokens"] - recs[ix[-2]]["message"]["usage"]["output_tokens"] + 1
        last["output_tokens"] -= drop
        _last_mu(led)[recs[ix[-1]]["message"]["model"]]["outputTokens"] -= drop

    def earlier_differs(key):
        def change(recs, led):
            recs[multi(recs)[0]]["message"]["usage"][key] += 1
        return change

    def earlier_model(recs, led):
        recs[multi(recs)[0]]["message"]["model"] = "claude-sonnet-5-5"

    def earlier_split(recs, led):                      # the count kept, one token moved from one duration to the other
        (ix,) = [ix for ix in _fragments(recs).values() if len(ix) >= 2 and
                 recs[ix[0]]["message"]["usage"]["cache_creation"]["ephemeral_5m_input_tokens"] > 0][:1]
        cw = recs[ix[0]]["message"]["usage"]["cache_creation"]
        cw["ephemeral_5m_input_tokens"] -= 1
        cw["ephemeral_1h_input_tokens"] += 1

    for name, change in (("output decreasing", output_decreases),
                         ("an earlier input count differing", earlier_differs("input_tokens")),
                         ("an earlier cache-read count differing", earlier_differs("cache_read_input_tokens")),
                         ("an earlier cache-write count differing", earlier_differs("cache_creation_input_tokens")),
                         ("an earlier model differing", earlier_model),
                         ("an earlier 5m and 1h split differing", earlier_split)):
        calls = _with_copy("w255", lambda f, c=change: _rewrite_sub(f, c))
        if not unmeasured_only(calls, "anthropic"):
            out.append(f"V16: {name} was not one unmeasured call")
    return out


def _nest(folder):
    """Move a take copy's sub-agent files one folder down (subagents/nested/), the ledger's paths with them."""
    led = json.loads((folder / "driver-ledger.json").read_text())
    (folder / "subagents" / "nested").mkdir()
    for e in led["subagents"]:
        name = e["file"].split("/")[-1]
        (folder / e["file"]).rename(folder / "subagents" / "nested" / name)
        e["file"] = f"subagents/nested/{name}"
    (folder / "driver-ledger.json").write_text(json.dumps(led))


def v17_sub_binding():
    """The sub-agent file's binding, on copies of w255: the files nested one folder down (drive.py's
    subagents/**/agent-<id>.jsonl, review edb48b6 MINOR 3) assemble as the walk does; a byte changed with the sha256
    left, an unnamed second file (beside it or nested), a file not named agent-<id>.jsonl, a named file missing, a
    file named outside subagents/, and a main-session call repeated in the sub-agent file (its modelUsage moved with
    it, so only the repeat can refuse it): each one unmeasured call."""
    out = []

    def touched(folder):
        e = sub_entry(json.loads((folder / "driver-ledger.json").read_text()))
        with open(folder / e["file"], "ab") as fh:
            fh.write(b"\n")

    def extra(folder):
        e = sub_entry(json.loads((folder / "driver-ledger.json").read_text()))
        shutil.copy(folder / e["file"], folder / "subagents" / "agent-unnamed.jsonl")

    def missing(folder):
        e = sub_entry(json.loads((folder / "driver-ledger.json").read_text()))
        (folder / e["file"]).unlink()

    def outside(folder):
        led = json.loads((folder / "driver-ledger.json").read_text())
        e = sub_entry(led)
        shutil.copy(folder / e["file"], folder / "agent-outside.jsonl")
        (folder / e["file"]).unlink()
        e["file"] = "subagents/../agent-outside.jsonl"
        (folder / "driver-ledger.json").write_text(json.dumps(led))

    def repeated(recs, led):
        c = led["cost"]["calls"][0]
        mid, rid = c["call_id"].split("/")
        u = dict(c["usage"], cache_creation={"ephemeral_5m_input_tokens": c["cache_write_durations"]["5m"],
                                             "ephemeral_1h_input_tokens": c["cache_write_durations"]["1h"]})
        recs.append({"type": "assistant", "requestId": rid, "message": {"id": mid, "model": c["model"], "usage": u}})
        mu = _last_mu(led)[c["model"]]
        for k, n in (("input_tokens", "inputTokens"), ("output_tokens", "outputTokens"),
                     ("cache_read_input_tokens", "cacheReadInputTokens"),
                     ("cache_creation_input_tokens", "cacheCreationInputTokens")):
            mu[n] += c["usage"][k]

    def nested_extra(folder):
        e = sub_entry(json.loads((folder / "driver-ledger.json").read_text()))
        (folder / "subagents" / "deep").mkdir()
        shutil.copy(folder / e["file"], folder / "subagents" / "deep" / "agent-unnamed.jsonl")

    def bad_name(folder):
        led = json.loads((folder / "driver-ledger.json").read_text())
        e = sub_entry(led)
        (folder / e["file"]).rename(folder / "subagents" / "other.jsonl")
        e["file"] = "subagents/other.jsonl"
        (folder / "driver-ledger.json").write_text(json.dumps(led))

    in_place = cc.take_calls(WALKS / "w255", row_of("w255"))
    nested = _with_copy("w255", _nest)
    if nested != in_place:
        out.append("V17: a sub-agent file nested below subagents/, as drive.py copies it, did not assemble as the walk")
    for name, change in (("a byte changed, the sha256 left", touched), ("an unnamed second file", extra),
                         ("an unnamed file nested below subagents/", nested_extra),
                         ("a file not named agent-<id>.jsonl", bad_name),
                         ("a named file missing", missing), ("a file named outside subagents/", outside),
                         ("a main call repeated in the sub-agent file", lambda f: _rewrite_sub(f, repeated))):
        calls = _with_copy("w255", change)
        if not unmeasured_only(calls, "anthropic"):
            out.append(f"V17: {name} was not one unmeasured call")
    return out


def _inject_agent_call(folder):
    """Add an Agent tool_use to a take copy's main session file (no sub-agent file copied)."""
    path = folder / "transcript.jsonl"
    lines = path.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        r = json.loads(line) if line.strip() else None
        if isinstance(r, dict) and r.get("type") == "assistant" and isinstance(r["message"].get("content"), list):
            r["message"]["content"].append({"type": "tool_use", "id": "toolu_injected", "name": "Agent",
                                            "input": {"description": "x", "prompt": "x"}})
            lines[i] = json.dumps(r)
            break
    path.write_text("\n".join(lines), encoding="utf-8")


def v18_reconcile():
    """DELEGATION and RECONCILE on copies (review edb48b6 MAJOR 1, glitch-45's option (c)). A delegating take goes
    unmeasured when its last modelUsage is off by one input token, when it has no modelUsage, when its calls are under
    another model's modelUsage, when its last turn is cut (no modelUsage; an earlier turn's remains), when its sub-agent
    file is gone while its session still calls Agent (the finding's undercount), and when w001's session is given an
    Agent tool_use with no file copied. A take that did not delegate prices its ledger's calls as before: w177 with its
    last turn cut (probe P5), w001 off by one, w001 with no modelUsage."""
    out = []

    def ledger_edit(edit):
        def change(folder):
            led = json.loads((folder / "driver-ledger.json").read_text())
            edit(led, folder)
            (folder / "driver-ledger.json").write_text(json.dumps(led))
        return change

    def off_by_one(led, folder):
        mu = _last_mu(led)
        mu[sorted(mu)[0]]["inputTokens"] += 1

    def sub_gone(led, folder):
        shutil.rmtree(folder / "subagents")
        led["subagents"] = []

    def no_model_usage(led, folder):
        for t in led["cost"]["turns"]:
            t["model_usage"] = None

    def other_model(led, folder):
        mu = _last_mu(led)
        (m,) = list(mu)
        mu["claude-sonnet-5-5" if m != "claude-sonnet-5-5" else "claude-opus-5-5"] = mu.pop(m)

    def cut_last(led, folder):
        led["cost"]["turns"][-1]["model_usage"] = None

    for name, walk, change in (("w255 off by one input token", "w255", ledger_edit(off_by_one)),
                               ("w255 with no modelUsage", "w255", ledger_edit(no_model_usage)),
                               ("w255 under another model's modelUsage", "w255", ledger_edit(other_model)),
                               ("w255 with its last turn cut", "w255", ledger_edit(cut_last)),
                               ("w255 with its sub-agent file gone", "w255", ledger_edit(sub_gone)),
                               ("w001 calling Agent with no sub-agent file", "w001", _inject_agent_call)):
        calls = _with_copy(walk, change)
        if not unmeasured_only(calls, "anthropic"):
            out.append(f"V18: {name} was not one unmeasured call")
    if [t.get("model_usage") is not None for t in ledger_of("w255")["cost"]["turns"]][:-1] != [True]:
        out.append("V18: w255's cut witness needs its earlier turn's modelUsage")
    for name, walk, change in (("w177 with its last turn cut", "w177", ledger_edit(cut_last)),
                               ("w001 off by one input token", "w001", ledger_edit(off_by_one)),
                               ("w001 with no modelUsage", "w001", ledger_edit(no_model_usage))):
        calls = _with_copy(walk, change)
        if calls != ledger_of(walk)["cost"]["calls"] or not calls:
            out.append(f"V18: {name} (no delegation) did not assemble its ledger's calls unchanged")
        elif costs.account(calls, PRICES, VARIANTS)["priced_cost_usd"] is None:
            out.append(f"V18: {name} (no delegation) is not priced")
    return out


def v20_api_errors_and_bindings():
    """API-error records in a sub-agent file are the harness's, skipped as session_calls skips them (review edb48b6
    NIT 6): a w255 copy given one record of each kind (the camel-case flag, the adapter's is_api_error_message flag, the
    synthetic model), each with a usage, assembles as the walk does. And the names cost_calls spells are the checker's:
    SUBAGENT_FILE is drive.SUBAGENT_FILE, AGENT_TOOL is check_take.AGENT_TOOL and transcript_view's one DELEGATE tool."""
    out = []
    in_place = cc.take_calls(WALKS / "w255", row_of("w255"))
    usage = {"input_tokens": 7, "output_tokens": 7, "cache_read_input_tokens": 7, "cache_creation_input_tokens": 0}
    haiku = "claude-haiku-4-5-20251001"
    for name, rec in (("isApiErrorMessage", {"isApiErrorMessage": True, "message": {"model": haiku}}),
                      ("is_api_error_message", {"is_api_error_message": True,
                                                "message": {"model": haiku}}),
                      ("the synthetic model", {"message": {"model": "<synthetic>"}})):
        def change(recs, led, rec=rec):
            r = {"type": "assistant", "requestId": f"req_api_{len(recs)}", **rec}
            r["message"] = dict(rec["message"], id=f"msg_api_{len(recs)}", usage=dict(usage), content=[])
            recs.append(r)
        calls = _with_copy("w255", lambda f, c=change: _rewrite_sub(f, c))
        if calls != in_place:
            out.append(f"V20: an API-error record ({name}) changed the assembly")
    import check_take
    import drive
    import transcript_view
    if cc.SUBAGENT_FILE.pattern != drive.SUBAGENT_FILE.pattern:
        out.append("V20: cost_calls.SUBAGENT_FILE is not drive.SUBAGENT_FILE")
    delegate = [k for k, v in transcript_view.CC_TOOLS.items() if v[0] == transcript_view.DELEGATE]
    if cc.AGENT_TOOL != check_take.AGENT_TOOL or delegate != [cc.AGENT_TOOL]:
        out.append(f"V20: cost_calls.AGENT_TOOL is not check_take.AGENT_TOOL and the one DELEGATE tool {delegate}")
    return out


def v19_statement_and_limitations():
    """The statement's arm A figures and the two limitation lines (findings 2 and 4) are what the records give."""
    out = []
    lines = costs.cost_statement(VARIANTS)
    five = Decimal("0.00001")
    got = {}
    for walk in ("w255", "w260"):
        led = ledger_of(walk)
        got[walk] = (costs.account(cc.take_calls(WALKS / walk, row_of(walk)), PRICES, VARIANTS)["priced_cost_usd"],
                     costs.account(led["cost"]["calls"], PRICES, VARIANTS)["priced_cost_usd"])
    for needle in (f"${got['w255'][0].quantize(five)} and ${got['w260'][0].quantize(five)}",
                   f"${got['w255'][1].quantize(five)} and ${got['w260'][1].quantize(five)}",
                   "sub-agent file the take copied", "the last fragment is kept", "never priced from a partial sum",
                   "the session's running total", "a cut or timed-out turn included",
                   "makes arm A's priced total, and with it the round-wide usage and priced total, read unmeasured",
                   "subagents/**/agent-<id>.jsonl", "is priced as recorded and is not reconciled",
                   "which claude_code_adapter.py lines 47-48 do not say"):
        if not any(ln.startswith("built: ") and needle in ln for ln in lines):
            out.append(f"V19: no built line says {needle!r}")
    d = b.build()
    by = {e["name"]: e for e in d["round_4_limitations"]}
    run = by.get("arm A turn cost is a running total", {})
    think = by.get("arm A thinking is not observable", {})
    led = ledger_of("w177")
    four = [Decimal(str(t["total_cost_usd"])).quantize(Decimal("0.0001")) for t in led["cost"]["turns"]]
    states = [(i, r["totalCostUSD"]) for i, r in enumerate(jsonl(WALKS / "w177" / "transcript.jsonl"), 1)
              if r.get("type") == "cost-state"]
    if [s for _, s in states] != [t["total_cost_usd"] for t in led["cost"]["turns"]]:
        out.append("V19: w177's per-turn totals are not its session's cost-state running totals")
    if f"store {four[0]}, {four[1]}, {four[2]} and {four[3]}" not in run.get("text", ""):
        out.append("V19: the running-total limitation does not carry w177's four figures")
    if "cost-state lines " + ", ".join(str(i) for i, _ in states[:-1]) + f" and {states[-1][0]}" not in run.get(
            "source", ""):
        out.append("V19: the running-total limitation does not cite w177's cost-state lines")
    ad = (HERE / "claude_code_adapter.py").read_text().split("\n")
    if "`total_cost_usd` is the turn's own result record's" not in ad[46] or "printed figure" not in ad[47]:
        out.append("V19: claude_code_adapter.py lines 47-48 do not hold the docstring the limitation cites")
    if '"total_cost_usd": res.get("total_cost_usd")' not in ad[964]:
        out.append("V19: claude_code_adapter.py line 965 is not cost_record's per-turn total")
    walks = blocks = empty = 0
    nonempty = []
    for path in sorted(WALKS.glob("*/driver-ledger.json")):
        if json.loads(path.read_text())["agent"]["harness"] != "claude-code":
            continue
        walks += 1
        for i, r in enumerate(jsonl(path.parent / "transcript.jsonl"), 1):
            content = (r.get("message") or {}).get("content") if r.get("type") == "assistant" else None
            for blk in content if isinstance(content, list) else ():
                if isinstance(blk, dict) and blk.get("type") == "thinking":
                    blocks += 1
                    if (blk.get("thinking") or "").strip():
                        nonempty.append(f"{path.parent.name} line {i}")
                    else:
                        empty += 1
    if f"{empty:,} of the {blocks:,} thinking blocks in the {walks} committed arm A walks" not in think.get("text", ""):
        out.append(f"V19: the thinking limitation does not say {empty:,} of the {blocks:,} in the {walks} walks")
    if f"the {len(nonempty)} others" not in think.get("text", "") or ", ".join(nonempty[:-1]) not in think.get(
            "source", "") or nonempty[-1] not in think.get("source", ""):
        out.append(f"V19: the thinking limitation does not name the non-empty blocks {nonempty}")
    if f"reads almost no reasoning for arm A (those {len(nonempty)} short notes in {blocks:,} blocks)" not in think.get(
            "text", ""):
        out.append("V19: the thinking limitation does not say it reads almost no reasoning")
    if "which the adapter's docstring (lines 47-48) does not say" not in run.get("text", ""):
        out.append("V19: the running-total limitation overreads the docstring")
    if "published as not observable, never as 0" not in think.get("text", ""):
        out.append("V19: the thinking limitation does not say not observable, never 0")
    aw = (HERE / "graders" / "awareness.py").read_text().split("\n")
    if "reasoning_matches" not in aw[12] or "AGENT_REASONING" not in aw[170] or "reasoning_matches" not in aw[173]:
        out.append("V19: graders/awareness.py lines 13, 171 and 174 do not hold what the limitation cites")
    if "for arm A it is not observable" not in d["run_tree_residual"]["round_4"]["awareness_caveat"]:
        out.append("V19: the awareness caveat does not say arm A's reasoning is not observable")
    return out


CASES = {"V1": v1_codex_mapping, "V2": v2_codex_all_walks, "V3": v3_codex_priced, "V4": v4_codex_incomplete,
         "V5": v5_gemini_mapping, "V6": v6_gemini_incomplete, "V7": v7_claude, "V8": v8_assemble,
         "V9": v9_statement, "V10": v10_main, "V11": v11_codex_prompt_once, "V12": v12_codex_rules_on_records,
         "V13": v13_codex_cache_writes, "V14": v14_claude_subagents, "V15": v15_claude_all_walks,
         "V16": v16_fragment_rule, "V17": v17_sub_binding, "V18": v18_reconcile, "V19": v19_statement_and_limitations,
         "V20": v20_api_errors_and_bindings}


# ---- the mutants ----------------------------------------------------------------------------------------------------
def _whole_input(u):
    got = _REAL_CODEX_USAGE(u)
    return dict(got, input_tokens=u["input_tokens"])


def _no_thoughts(t):
    got = _REAL_GEMINI_USAGE(t)
    return None if got is None else dict(got, output_tokens=t["output"])


_REAL_CODEX_USAGE, _REAL_GEMINI_USAGE = cc.codex_usage, cc.gemini_usage
_REAL_SUB_FILE_CALLS, _REAL_RECONCILE, _REAL_FRAGMENT_HOLDS = cc.subagent_file_calls, cc.reconcile, cc.fragment_holds
_REAL_ADMITTED = cc.admitted_path


def _keep_first(text, agent, agent_id, name):
    """Mutant: the first fragment of each sub-agent call kept, not the last."""
    seen, keep = set(), []
    for line in text.split("\n"):
        r = json.loads(line) if line.strip() else None
        if isinstance(r, dict) and r.get("type") == "assistant" and isinstance((r.get("message") or {}).get("usage"),
                                                                             dict):
            k = (r["message"].get("id"), r.get("requestId"))
            if k in seen:
                continue
            seen.add(k)
        keep.append(line)
    return _REAL_SUB_FILE_CALLS("\n".join(keep), agent, agent_id, name)


def _holds_without(part):
    """Mutant: the fragment rule with one of its parts (output, model, split) left out."""
    def holds(kept, new):
        if part == "output":
            new = dict(new, usage=dict(new["usage"], output_tokens=kept["usage"]["output_tokens"]))
        elif part == "model":
            new = dict(new, model=kept["model"])
        elif part == "split":
            new = dict(new, cache_write_durations=kept["cache_write_durations"])
        return _REAL_FRAGMENT_HOLDS(kept, new)
    return holds
_OLD_ITEMS = costs.NOT_BUILT_ITEMS[:4] + (
    "No step assembles cost-calls.json: an arm A take records its calls in its driver ledger's cost "
    "(claude_code_adapter.cost_record), and an arm O or arm G take records none (drive.py writes a cost for "
    "claude-code takes only), so no Codex or Gemini call reaches this accounting.",)

MUTANTS = {
    "codex-input-whole": ("V1", lambda: mock.patch.object(cc, "codex_usage", _whole_input)),
    "codex-input-whole-priced": ("V3", lambda: mock.patch.object(cc, "codex_usage", _whole_input)),
    "codex-running-unchecked": ("V4", lambda: mock.patch.object(cc, "running_totals_hold", lambda *a: True)),
    "codex-turn-total-unchecked": ("V4", lambda: mock.patch.object(cc, "turn_total_holds", lambda *a: True)),
    "codex-reroute-ignored": ("V4", lambda: mock.patch.object(cc, "reroute_problem", lambda ledger: None)),
    "codex-totals-cumulative-misread": ("V2", lambda: mock.patch.object(cc, "_add", lambda total, u: dict(u))),
    "gemini-thoughts-dropped": ("V5", lambda: mock.patch.object(cc, "gemini_usage", _no_thoughts)),
    "gemini-stats-unchecked": ("V6", lambda: mock.patch.object(cc, "stats_agree", lambda *a: True)),
    "gemini-tool-priced": ("V6", lambda: mock.patch.object(cc, "gemini_usage", lambda t: _REAL_GEMINI_USAGE(
        dict(t, tool=0)))),
    "unmeasured-as-zero": ("V4", lambda: mock.patch.object(cc, "unmeasured", lambda vendor, key, model, agent, why: {
        "vendor": vendor, "call_id": f"{key}/x", "model": model, "agent": dict(agent),
        "usage": {"input_tokens": 0}, "total_cost_usd": None, "started_at": None, "ended_at": None,
        cc.UNMEASURED: why})),
    "claude-none-dropped": ("V7", lambda: mock.patch.object(cc, "unmeasured", lambda *a: {"vendor": "x", "usage": 1})),
    "outcomes-twice": ("V8", lambda: mock.patch.object(cc, "outcome_keys", lambda h: [
        (o["slot"], o["attempt"]) for o in h if "kind" not in o])),
    "rulings-read-as-outcomes": ("V8", lambda: mock.patch.object(cc, "outcome_keys", lambda h: list(dict.fromkeys(
        (o["slot"], o["attempt"]) for o in h)))),
    "statement-old-line": ("V9", lambda: mock.patch.object(costs, "NOT_BUILT_ITEMS", _OLD_ITEMS)),
    "statement-no-assembly": ("V9", lambda: mock.patch.object(costs, "ASSEMBLY_BUILT", ())),
    "main-unchecked": ("V10", lambda: mock.patch.object(cc, "render", lambda calls: "[]\n")),
    "codex-cached-counted-twice": ("V11", lambda: mock.patch.object(cc, "codex_usage", _whole_input)),
    "codex-cached-twice-priced": ("V12", lambda: mock.patch.object(cc, "codex_usage", _whole_input)),
    "long-context-ignored": ("V12", lambda: mock.patch.object(costs, "tier_for", lambda v, m, u, p, var: (
        p, var["cache_write"].get(v, {}).get(m), None))),
    # review aa4394c's folds
    "codex-written-counted-twice": ("V13", lambda: mock.patch.object(cc, "codex_usage", lambda u: dict(
        _REAL_CODEX_USAGE(u), input_tokens=u["input_tokens"] - u["cached_input_tokens"]))),
    "codex-written-as-cache-read": ("V13", lambda: mock.patch.object(cc, "codex_usage", lambda u: dict(
        _REAL_CODEX_USAGE(u), cache_read_input_tokens=u["cached_input_tokens"] + u["cache_write_input_tokens"],
        cache_creation_input_tokens=0))),
    "gemini-total-unchecked": ("V6", lambda: mock.patch.object(cc, "GEMINI_CHECKED", tuple(
        p for p in cc.GEMINI_CHECKED if p[0] != "total"))),
    "gemini-tool-call-kept": ("V6", lambda: mock.patch.object(cc, "unpriced_problem", lambda calls: None)),
    "drive-started-ignored": ("V8", lambda: mock.patch.object(cc, "drive_may_have_started", lambda outcome: False)),
    # lane gap-subagent-cost (28 Oct 2026): one per rule of the arm A sub-agent assembly
    "sub-agent-calls-dropped": ("V14", lambda: mock.patch.object(cc, "subagent_calls", lambda f, led: ([], []))),
    "sub-agent-dropped-every-walk": ("V15", lambda: mock.patch.object(cc, "subagent_calls", lambda f, led: ([], []))),
    "fragment-first-kept": ("V14", lambda: mock.patch.object(cc, "subagent_file_calls", _keep_first)),
    "split-not-read": ("V14", lambda: mock.patch.object(cc.claude_code_adapter, "cache_write_split",
                                                         lambda usage, counts: None)),
    "fragment-output-may-decrease": ("V16", lambda: mock.patch.object(cc, "fragment_holds", _holds_without("output"))),
    "fragment-input-unchecked": ("V16", lambda: mock.patch.object(cc, "FRAGMENT_FIXED", tuple(
        k for k in cc.FRAGMENT_FIXED if k != "input_tokens"))),
    "fragment-cache-read-unchecked": ("V16", lambda: mock.patch.object(cc, "FRAGMENT_FIXED", tuple(
        k for k in cc.FRAGMENT_FIXED if k != "cache_read_input_tokens"))),
    "fragment-model-unchecked": ("V16", lambda: mock.patch.object(cc, "fragment_holds", _holds_without("model"))),
    "fragment-split-unchecked": ("V16", lambda: mock.patch.object(cc, "fragment_holds", _holds_without("split"))),
    "sub-sha-unchecked": ("V17", lambda: mock.patch.object(cc, "bytes_bound", lambda raw, entry: True)),
    "sub-unnamed-file-ignored": ("V17", lambda: mock.patch.object(cc, "files_match", lambda folder, named: True)),
    "call-id-twice": ("V17", lambda: mock.patch.object(cc, "ids_once", lambda calls: True)),
    "reconcile-skipped": ("V18", lambda: mock.patch.object(cc, "reconcile", lambda calls, turns, has_sub: None)),
    "reconcile-sub-without-model-usage": ("V18", lambda: mock.patch.object(
        cc, "reconcile", lambda calls, turns, has_sub: _REAL_RECONCILE(calls, turns, has_sub=False))),
    "reconcile-models-pooled": ("V18", lambda: mock.patch.object(cc, "model_key", lambda model: "*")),
    "statement-no-sub-agent-lines": ("V19", lambda: mock.patch.object(costs, "ASSEMBLY_BUILT",
                                                                     costs.ASSEMBLY_BUILT[:5])),
    # review edb48b6's folds
    "every-take-reconciled": ("V18", lambda: mock.patch.object(cc, "delegates", lambda named, on_disk, tool: True)),
    "agent-tool-ignored": ("V18", lambda: mock.patch.object(cc, "agent_called", lambda folder, ledger: False)),
    "agent-without-file-passes": ("V18", lambda: mock.patch.object(cc, "file_missing", lambda tool, files: False)),
    "nested-refused": ("V17", lambda: mock.patch.object(cc, "admitted_path", lambda rel: len(rel.split("/")) == 2 and (
        _REAL_ADMITTED(rel)))),
    "nested-unnamed-ignored": ("V17", lambda: mock.patch.object(cc, "subagent_files", lambda folder: sorted(
        f"subagents/{q.name}" for q in (folder / "subagents").glob("*.jsonl")) if (folder / "subagents").is_dir()
        else [])),
    "name-unchecked": ("V17", lambda: mock.patch.object(cc, "SUBAGENT_FILE", re.compile(r".*\.jsonl"))),
    "api-errors-counted": ("V20", lambda: mock.patch.object(cc, "api_error", lambda rec: False)),
    "adapter-api-error-half-dropped": ("V20", lambda: mock.patch.object(cc.claude_code_adapter, "_is_api_error",
                                                                         lambda rec: False)),
    "limitations-dropped": ("V19", lambda: mock.patch.object(b, "ROUND_4_LIMITATIONS", b.ROUND_4_LIMITATIONS[:8])),
}


def run_case(name):
    try:
        return CASES[name]()
    except Exception as e:                       # a case that raises is a problem, never a pass
        return [f"{name}: raised {type(e).__name__}: {e}"]


class TheCases(unittest.TestCase):
    def test_every_case_holds(self):
        for name in CASES:
            with self.subTest(case=name):
                self.assertEqual(run_case(name), [], name)

    def test_no_committed_record_changed(self):
        """The cases read the committed walks and never write them: their bytes equal HEAD's."""
        import subprocess
        got = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", str(WALKS)],
                             capture_output=True, text=True)
        self.assertEqual((got.returncode, got.stdout), (0, ""))


class TheMutants(unittest.TestCase):
    def test_every_mutant_turns_its_case_red(self):
        self.assertEqual({case for case, _ in MUTANTS.values()} - set(CASES), set())
        for name, (case, patch) in MUTANTS.items():
            with self.subTest(mutant=name):
                with patch():
                    self.assertTrue(run_case(case), f"mutant {name} left {case} green")

    def test_no_mutant_leaks(self):
        for name in CASES:
            self.assertEqual(run_case(name), [], f"{name} after the mutants")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    n = result.testsRun
    print(f"test_pf1_cost_vendors: {n} run, {len(result.failures)} failures, {len(result.errors)} errors")
    sys.exit(0 if result.wasSuccessful() else 1)
