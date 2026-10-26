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
  V7  arm A: the ledger's cost calls unchanged (walk w001); a ledger cost of None is one unmeasured call.
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
MUTANTS: each weakens one rule in memory, and the case it names must then report a problem. Stdlib only.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
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
    if n != 38:
        out.append(f"V2: {n} committed arm O walks, not 38")
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
    if len(recs) != 305 or cached < 1:
        out.append(f"V11: {len(recs)} records, {cached} with cached tokens (the walks hold 305, most cached)")
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
    reach a split; no recorded call writes to the cache (0 of 305), so the 12h bound is priced on none and every
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


CASES = {"V1": v1_codex_mapping, "V2": v2_codex_all_walks, "V3": v3_codex_priced, "V4": v4_codex_incomplete,
         "V5": v5_gemini_mapping, "V6": v6_gemini_incomplete, "V7": v7_claude, "V8": v8_assemble,
         "V9": v9_statement, "V10": v10_main, "V11": v11_codex_prompt_once, "V12": v12_codex_rules_on_records,
         "V13": v13_codex_cache_writes}


# ---- the mutants ----------------------------------------------------------------------------------------------------
def _whole_input(u):
    got = _REAL_CODEX_USAGE(u)
    return dict(got, input_tokens=u["input_tokens"])


def _no_thoughts(t):
    got = _REAL_GEMINI_USAGE(t)
    return None if got is None else dict(got, output_tokens=t["output"])


_REAL_CODEX_USAGE, _REAL_GEMINI_USAGE = cc.codex_usage, cc.gemini_usage
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
