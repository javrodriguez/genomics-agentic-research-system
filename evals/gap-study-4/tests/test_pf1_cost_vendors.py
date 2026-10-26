#!/usr/bin/env python3
"""Lane pf1-cost-vendors: cost-calls.json assembled for every arm (cost_calls.py), and the cost statement that says so.

    python3 -B -W ignore evals/gap-study-4/tests/test_pf1_cost_vendors.py

Each case is one check returning its problems (empty when it holds). The fixtures are committed walk records, copied
read-only into a temporary take folder (takes/<slot>/<attempt>/); no committed record is edited, and the cases that
need a broken record break only their temporary copy. The expected values are derived here with plain json, never
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
      with no result stats), w-g13 (a tokens record with no model): each one unmeasured call; and a tokens record
      with tool-use prompt tokens has usage None.
  V7  arm A: the ledger's cost calls unchanged (walk w001); a ledger cost of None is one unmeasured call.
  V8  assemble: every committed outcome once, in commit order, rulings skipped; no turn ran is no call; streams with no
      ledger are one unmeasured call; the assembly is accounted by costs.account across the three vendors.
  V9  the statement: the old "no step assembles" line is gone, each ASSEMBLY_BUILT line is a built line, the remaining
      not-built items are named, and the draft carries costs.cost_statement of its variants.
  V10 cost_calls.main: --write then --check holds; a changed cost-calls.json is refused.
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
    """A read-only copy of a committed walk laid out as takes/<slot>/<attempt>/ under a temporary root."""
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
        rows = [row_of("w-o47", 1), row_of("w001", 2), dict(row_of("w001", 3)), row_of("w-o46", 4),
                row_of("w-o46", 4, 2)]
        from graders import labels4
        # slot 4's attempt 1 has a ruling and no outcome: a ruling is never an outcome, so its calls are not assembled
        history = [{"slot": 2, "attempt": 1}, {"slot": 1, "attempt": 1}, {"slot": 3, "attempt": 1},
                   {"slot": 2, "attempt": 1}, {"kind": labels4.RULING, "slot": 4, "attempt": 1},
                   {"slot": 4, "attempt": 2}]
        got = cc.assemble(rows, history, root=root)
        a = [c["call_id"] for c in ledger_of("w001")["cost"]["calls"]]
        o = [p["response_id"] for p in records_of("w-o47")]
        slot, attempt = 4, 2
        want_ids = a + o + [f"takes/{slot}/{attempt}/unmeasured/gpt-6.1-sol"]
        if [c["call_id"] for c in got] != want_ids:
            out.append(f"V8: assembled {len(got)} calls, not the {len(want_ids)} of the outcomes once each in order")
        acct = costs.account(got, PRICES, VARIANTS)
        if set(acct["vendors"]) != {"anthropic", "openai"} or acct["vendors"]["openai"]["priced_cost_usd"] is not None:
            out.append(f"V8: the account's vendors {acct['vendors']}")
        if acct["vendors"]["anthropic"]["priced_cost_usd"] is None:
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
                   "tool-use prompt tokens are not priced", "service_tier is not read"):
        if not any(ln.startswith(costs.NOT_BUILT + ": ") and needle in ln for ln in lines):
            out.append(f"V9: no not-built line names {needle!r}")
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


CASES = {"V1": v1_codex_mapping, "V2": v2_codex_all_walks, "V3": v3_codex_priced, "V4": v4_codex_incomplete,
         "V5": v5_gemini_mapping, "V6": v6_gemini_incomplete, "V7": v7_claude, "V8": v8_assemble,
         "V9": v9_statement, "V10": v10_main}


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
