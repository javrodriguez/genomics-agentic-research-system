#!/usr/bin/env python3
"""The no-visible-output nudge: a NAMED DEPARTURE, one record shape read as harness furniture (glitch-b5's ruling 3,
16 Oct 2026; CP6 walk w053, Haiku, held on its transcript line 107).

The facts (a static read of the pinned 2.1.296 binary, sha256 24972e3b..., and of 2.1.267 and 2.1.280, never run):
when a model response ends with stop_reason end_turn or stop_sequence, is not an API error and carries no text block
with visible text, the query loop writes a user record {isMeta: true, turnCompanion: true} whose content is exactly
CC_NO_OUTPUT_NUDGE_TEXT, drops the empty response and asks the model again. A guard allows it once per model round and
is reset after each tool round. No env or setting gates it. Round 3's versions carry the same path, and round 3's 64
transcripts carry no isMeta record at all.

  N-admit      the w053-shaped record (type user, isMeta true, turnCompanion true, content exactly the string) reads
               as one harness event, raw type user:no-visible-output-nudge; it is never an operator line, so the
               take's operator lines and turn count are unchanged.
  N-refuse     near misses refuse in the view: turnCompanion missing, false or a string; isMeta false; trailing or
               leading whitespace; a changed string; content as a list of blocks; an assistant record; an origin; an
               isApiErrorMessage key; a sidechain.
  N-checker    check_take.user_text_records reads the admitted record as the harness's text only where the
               pre-registration names the kind (meta_kinds); round 3's list and a wakeup-only list read it as an
               operator line, as before; the two readers agree (no readers-disagree). A near miss carrying a leak
               word is read as an operator line, so the operator leak check still reads it: only the exact string
               is set apart.
  N-count      check_take.no_output_nudges counts the admitted records of a transcript; near misses are not counted.
  N-record     walk_runner.check_record writes the count as check.json's no_output_nudges (None when the checker did
               not run); pending_walk and walk_regrade read check.json with or without the key (files written before
               this ruling lack it), and refuse a value that is not a count.
  N-strict     review r6 MINOR 2 (glitch-b5, 16 Oct 2026): a checked walk's count is never null. check_record refuses
               to write anything but an int >= 0 when the checker ran, and walk_runner holds such a walk; pending_walk
               reads a check.json under the constants in force without a count as unreadable (null only under older
               constants, or when the checker did not run); walk_regrade recomputes check_take's count from the
               committed transcript, in --check and in a recheck, and names a forged count.
  N-constant   CHECKER_CONSTANTS' meta_kinds names both kinds.
  N-draft      the draft names the departure with its facts.
  N-witness    each clause dropped in memory turns a check red.

Synthetic fixtures only.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import transcript_view as tv  # noqa: E402

ct = tx = None


def setUpModule():
    global ct, tx
    saved = list(sys.path)
    import check_take as ct
    import transcript as tx
    sys.path[:] = saved


CC = tv.ROUND3_HARNESS
TEXT = "[Your previous response had no visible output. Please continue and produce a user-visible response.]"
OP = {"type": "user", "message": {"role": "user", "content": "Run stage 00 of the pipeline for project demo."}}
SAID = {"type": "assistant", "message": {"model": "m", "content": [{"type": "text", "text": "Done."}]}}
DROP = object()


def nudge(content=TEXT, **over):
    r = {"type": "user", "isMeta": True, "turnCompanion": True, "isSidechain": False,
         "message": {"role": "user", "content": content}, "promptId": "p-1", "uuid": "u-1",
         "timestamp": "2026-10-16T04:00:00.000Z"}
    for k, v in over.items():
        if v is DROP:
            r.pop(k, None)
        else:
            r[k] = v
    return r


def lines(*recs):
    return [json.dumps(r) for r in recs]


NEAR = {
    "turnCompanion missing": nudge(turnCompanion=DROP),
    "turnCompanion false": nudge(turnCompanion=False),
    "turnCompanion a string": nudge(turnCompanion="true"),
    "isMeta false": nudge(isMeta=False),
    "isMeta a string": nudge(isMeta="true"),
    "trailing whitespace": nudge(TEXT + " "),
    "a trailing newline": nudge(TEXT + "\n"),
    "leading whitespace": nudge(" " + TEXT),
    "a changed string": nudge(TEXT.replace("visible output", "output")),
    "without the brackets": nudge(TEXT[1:-1]),
    "content as blocks": nudge([{"type": "text", "text": TEXT}]),
    "an assistant record": dict(nudge(), type="assistant"),
    "an origin": nudge(origin={"kind": "task-notification"}),
    "an isApiErrorMessage key": nudge(isApiErrorMessage=False),
    "a sidechain": nudge(isSidechain=True),
}


def admit_problems(view=tv) -> list:
    out = []
    recs = (OP, nudge(), SAID)
    try:
        evs = view.events(CC, lines(*recs))
    except view.ViewError as e:
        return [f"N-admit: refused: {e}"]
    harness = [e for e in evs if e.kind == view.HARNESS]
    if [e.text for e in harness] != [TEXT]:
        out.append(f"N-admit: harness texts {[e.text for e in harness]!r}")
    if view.operator_lines(evs) != [OP["message"]["content"]]:
        out.append(f"N-admit: operator lines {view.operator_lines(evs)!r}")
    if max(e.turn for e in evs) != 1:
        out.append("N-admit: the nudge started a turn")
    if view.harness_types(CC, lines(*recs)) != {"user:no-visible-output-nudge": 1}:
        out.append(f"N-admit: raw types {view.harness_types(CC, lines(*recs))}")
    if getattr(view, "CC_NO_OUTPUT_NUDGE_TEXT", None) != TEXT:
        out.append("N-admit: the view's string is not the binary's")
    return out


def refuse_problems(view=tv) -> list:
    out = []
    for name, rec in NEAR.items():
        try:
            view.events(CC, lines(OP, rec))
            out.append(f"N-refuse: admitted: {name}")
        except view.ViewError:
            pass
    return out


def pre(meta):
    h = copy.deepcopy(ct.CHECKER_CONSTANTS["harness_delivered_user_records"])
    if meta is None:
        h.pop("meta_kinds", None)
    else:
        h["meta_kinds"] = list(meta)
    return {"harness_delivered_user_records": h}


def record_reader(recs, meta, mod=None):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "transcript.jsonl"
        p.write_text("\n".join(lines(*recs)) + "\n")
        got = (mod or ct).user_text_records(p, pre(meta))
        n_user = sum(1 for t in tx.load(p)["turns"] if t["role"] == "user" and t["text"].strip())
    return got + (n_user,)


def checker_problems(mod=None) -> list:
    out = []
    both = [tv.CC_SCHEDULED_WAKEUP, tv.CC_NO_OUTPUT_NUDGE]
    ops, harness, unknown, n = record_reader((OP, nudge(), SAID), both, mod)
    if (ops, harness, unknown) != ([OP["message"]["content"]], [TEXT], []):
        out.append(f"N-checker named: {(ops, harness, unknown)}")
    if n != len(ops) + len(harness) + len(unknown):
        out.append(f"N-checker: the readers disagree ({n} against {len(ops) + len(harness) + len(unknown)})")
    for name, meta in (("round 3's list", None), ("a wakeup-only list", [tv.CC_SCHEDULED_WAKEUP])):
        ops, harness, _, _ = record_reader((OP, nudge(), SAID), meta, mod)
        if (len(ops), harness) != (2, []):
            out.append(f"N-checker {name}: {(ops, harness)}")
    near = nudge(TEXT + " evaluation")
    ops, harness, _, _ = record_reader((OP, near, SAID), both, mod)
    if near["message"]["content"] not in ops or harness:
        out.append(f"N-checker: a near miss carrying a leak word is not an operator line: {(ops, harness)}")
    return out


def count_problems(mod=None) -> list:
    mod = mod or ct
    out = []
    for name, recs, want in (("two", (OP, nudge(), SAID, nudge()), 2), ("none", (OP, SAID), 0),
                             ("near misses only", (OP, *NEAR.values()), 0)):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "transcript.jsonl"
            p.write_text("\n".join(lines(*recs)) + "\n")
            got = mod.no_output_nudges(p)
        if got != want or type(got) is not int:
            out.append(f"N-count {name}: {got!r}, not {want}")
    return out


def record_problems() -> list:
    import pending_walk
    import walk_regrade
    import walk_runner
    out = []
    route = lambda records, table: {"route": "rehearsal"}  # noqa: E731
    args = ("w001", {"checker_reasons": [], "events": {"outside_reach": 0}}, {}, route)
    doc = walk_runner.check_record(*args, checked=True, constants_sha256="ab" * 32, no_output_nudges=2,
                                   agent_summary={"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0})
    if doc.get("no_output_nudges") != 2:
        out.append(f"N-record: check.json carries {doc.get('no_output_nudges')!r}")
    if walk_runner.check_record(*args, checked=False, no_output_nudges=2).get("no_output_nudges", "absent") is not None:
        out.append("N-record: an unchecked walk carries a count")
    legacy = {k: v for k, v in doc.items() if k not in ("no_output_nudges", "agent_calls", "subagents",
                                                        "nested_cli_calls")}
    nudge_only = {k: v for k, v in doc.items() if k not in ("agent_calls", "subagents", "nested_cli_calls")}
    pair_only = {k: v for k, v in doc.items() if k != "nested_cli_calls"}                   # before W-3b
    for name, d, ok in (("the new shape", doc, True), ("a file written before the ruling", legacy, True),
                        ("a file written before the Agent ruling", nudge_only, True),
                        ("a file written before W-3b", pair_only, True),
                        ("a null count", dict(doc, no_output_nudges=None), True),
                        ("a boolean count", dict(doc, no_output_nudges=True), False),
                        ("a negative count", dict(doc, no_output_nudges=-1), False),
                        ("a string count", dict(doc, no_output_nudges="2"), False),
                        ("another extra key", dict(doc, extra=1), False)):
        if pending_walk.check_keys_ok(d) is not ok:
            out.append(f"N-record pending_walk {name}: {not ok}")
        try:
            walk_regrade._check_fields(d, "check.json")
            read = True
        except walk_regrade.RegradeRefused:
            read = False
        if read is not ok:
            out.append(f"N-record walk_regrade {name}: {'read' if read else 'refused'}")
    return out


ABSENT = object()


def strict_problems(walk_runner=None, pending_walk=None, walk_regrade=None) -> list:
    import pending_walk as pw
    import walk_regrade as wg
    import walk_runner as wr
    wr, pw, wg = walk_runner or wr, pending_walk or pw, walk_regrade or wg
    out = []
    route = lambda records, table: {"route": "rehearsal"}  # noqa: E731
    args = ("w001", {"checker_reasons": [], "events": {"outside_reach": 0}}, {}, route)
    for bad in (None, True, -1, "1", 1.0):
        try:
            wr.check_record(*args, checked=True, constants_sha256="ab" * 32, no_output_nudges=bad,
                            agent_summary={"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0})
            out.append(f"N-strict: check_record wrote {bad!r} for a walk the checker ran on")
        except ValueError:
            pass
    for bad in (None, True, False, -1, "1", 1.0):
        if pw.valid_nudge_count(bad):
            out.append(f"N-strict: {bad!r} reads as a count")
    if wr.check_record(*args, checked=False, no_output_nudges=None)["no_output_nudges"] is not None:
        out.append("N-strict: an unchecked walk carries a count")
    now = ct.checker_constants_sha256()
    for name, count, digest, want in (("a count under the constants in force", 0, now, None),
                                      ("null under the constants in force", None, now, "check unreadable"),
                                      ("no key under the constants in force", ABSENT, now, "check unreadable"),
                                      ("null under older constants", None, "cd" * 32, "stale"),
                                      ("no key under older constants", ABSENT, "cd" * 32, "stale")):
        doc = {"walk": "w001", "checked": True, "checker_reasons": [], "events": {"outside_reach": 0},
               "route": "rehearsal", "route_refused": None, "checker_constants_sha256": digest,
               "no_output_nudges": count, "agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0}
        if count is ABSENT:                         # a check.json written before either ruling
            for k in ("no_output_nudges", "agent_calls", "subagents", "nested_cli_calls"):
                del doc[k]
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "w001").mkdir()
            (Path(d) / "w001" / "check.json").write_text(json.dumps(doc))
            got = pw.checker_standing(d, "w001")
        if not (got is None if want is None else isinstance(got, str) and got.startswith(want)):
            out.append(f"N-strict standing, {name}: {got!r}")
    # review r7 MINOR 2: a check.json under older constants with a null count, rechecked under the constants in force,
    # counts only once the recheck carries a count (the reviewer's rc.py, its recheck mocked)
    old_doc = {"walk": "w001", "checked": True, "checker_reasons": [], "events": {"outside_reach": 0},
               "route": "rehearsal", "route_refused": None, "checker_constants_sha256": "cd" * 32,
               "no_output_nudges": None}
    for name, latest, want in (("a recheck without a count", {"checker_reasons": [], "checker_constants_sha256": now},
                                "check unreadable"),
                               ("a recheck with a null count", {"checker_reasons": [], "checker_constants_sha256": now,
                                                                "no_output_nudges": None}, "check unreadable"),
                               ("a recheck carrying the count", {"checker_reasons": [], "checker_constants_sha256": now,
                                                                 "no_output_nudges": 0, "agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0}, None)):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "w001").mkdir()
            (Path(d) / "w001" / "check.json").write_text(json.dumps(old_doc))
            with mock.patch.object(pw, "latest_recheck", lambda b, w, latest=latest: latest):
                got = pw.checker_standing(d, "w001")
        if not (got is None if want is None else isinstance(got, str) and got.startswith(want)):
            out.append(f"N-strict rechecked, {name}: {got!r}")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "transcript.jsonl"
        p.write_text("\n".join(lines(OP, nudge(), SAID)) + "\n")
        for name, count, named in (("the true count", 1, False), ("a forged count", 3, True),
                                   ("a forged zero", 0, True), ("null", None, False)):
            got = wg.nudge_count_problems({"no_output_nudges": count}, p)
            if bool(got) is not named:
                out.append(f"N-strict re-derivation, {name}: {got}")
    import ast
    tree = ast.parse(Path(wg.__file__).read_text())
    for fn in ("regrade_problems", "recheck_doc"):
        body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn)
        if "nudge_count_problems" not in {c.func.id for c in ast.walk(body)
                                          if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}:
            out.append(f"N-strict: walk_regrade.{fn} does not recompute the count")
    tree = ast.parse(Path(wr.__file__).read_text())
    body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_one")
    if "valid_nudge_count" not in {c.func.attr for c in ast.walk(body) if isinstance(c, ast.Call)
                                   and isinstance(c.func, ast.Attribute)}:
        out.append("N-strict: walk_runner._run_one does not hold a walk whose checker gave no count")
    return out


def source_mutant(mod, old: str, new: str):
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times in {mod.__file__}: {old!r}")
    m = types.ModuleType(mod.__name__ + "_mutant")
    m.__file__ = mod.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


VIEW_MUTANTS = (
    ("type", 'rec.get("type") == "user" and rec.get("isMeta") is True', 'rec.get("isMeta") is True'),
    ("isMeta", 'and rec.get("isMeta") is True\n', "\n"),
    ("turnCompanion", 'rec.get("turnCompanion") is True', "True"),
    ("turnCompanion-truthy", 'rec.get("turnCompanion") is True', 'bool(rec.get("turnCompanion"))'),
    ("sender keys", ' or any(k in rec for k in ("isApiErrorMessage", "origin"))', ""),
    ("exact string", 'msg.get("content") == CC_NO_OUTPUT_NUDGE_TEXT', 'str(msg.get("content")).strip() == CC_NO_OUTPUT_NUDGE_TEXT.strip()'),
    ("the admission", "        if flagged and is_no_output_nudge(r):\n", "        if False:\n"),
    ("sidechain", 'if rec.get("isSidechain") is True or any(', "if any("),
)
CHECKER_MUTANTS = (
    ("ungated", "        if self.nudge and transcript_view.is_no_output_nudge(rec):",
     "        if transcript_view.is_no_output_nudge(rec):"),
    ("not the harness's text", "            harness.append(rec[\"message\"][\"content\"])\n            return True\n"
     "        if self.admit", "            return True\n        if self.admit"),
    ("gate on the wakeup kind", "transcript_view.CC_NO_OUTPUT_NUDGE in meta)", "transcript_view.CC_SCHEDULED_WAKEUP in meta)"),
)
STRICT_MUTANTS = (
    ("check_record writes null", "walk_runner",
     "    if checked is True and not pending_walk.valid_nudge_count(no_output_nudges):", "    if False:"),
    ("a bool is a count", "pending_walk", "type(n) is int and n >= 0", "isinstance(n, int) and n >= 0"),
    ("standing reads null", "pending_walk", '== now and not valid_nudge_count(eff_nudges):', "== now and False:"),
    ("forged count read", "walk_regrade", "    if got != want:", "    if False:"),
    ("the recheck's count unread", "pending_walk", "        eff_nudges = latest.get(CHECK_NUDGE_KEY)\n",
     "        eff_nudges = nudges\n"),
)
COUNT_MUTANTS = (
    ("count any isMeta user record", "if transcript_view.is_no_output_nudge(rec))",
     "if isinstance(rec, dict) and rec.get(\"isMeta\") is True)"),
)


class TheNoOutputNudge(unittest.TestCase):
    def test_n_admit(self):
        self.assertEqual(admit_problems(), [])

    def test_n_refuse(self):
        self.assertEqual(refuse_problems(), [])

    def test_n_checker(self):
        self.assertEqual(checker_problems(), [])

    def test_n_count(self):
        self.assertEqual(count_problems(), [])

    def test_n_record(self):
        self.assertEqual(record_problems(), [])

    def test_n_strict(self):
        self.assertEqual(strict_problems(), [])

    def test_n_constant(self):
        self.assertEqual(ct.CHECKER_CONSTANTS["harness_delivered_user_records"],
                         {"origin_kinds": [tv.CC_TASK_NOTIFICATION],
                          "meta_kinds": [tv.CC_SCHEDULED_WAKEUP, tv.CC_NO_OUTPUT_NUDGE]})
        self.assertIs(ct.transcript_view.is_no_output_nudge, tv.is_no_output_nudge)

    def test_n_draft(self):
        draft = json.loads((HERE / "prereg-draft.json").read_text())
        (dep,) = [d for d in draft["harness_furniture_ruling"]["departures"] if d["of"] == tv.CC_NO_OUTPUT_NUDGE]
        for word in ("Claude Code 2.1.296", TEXT, "isMeta", "turnCompanion", "end_turn or stop_sequence",
                     "no text block with visible text", "at most once per model round", "reset after each tool round",
                     "no switch", "2.1.267", "2.1.280", "round 3's 64 transcripts", "no isMeta record",
                     "w053", "RULED 16 Oct (glitch-b5)", "named departure", "harness furniture",
                     "never an operator line", "check.json", "no_output_nudges",
                     "224269128", "207900138", "188247583", "205033400", "24972e3b",
                     "never written without a count", "re-derives the count from the committed transcript"):
            self.assertIn(word, dep["text"])
        r = draft["checker_constants_ruling"]
        (meta,) = [e for e in r["departures"] if e["constant"] == "harness_delivered_user_records.meta_kinds"]
        self.assertIn("no-visible-output-nudge", meta["text"])

    def test_n_witnesses(self):
        for name, old, new in VIEW_MUTANTS:
            with self.subTest(view=name):
                m = source_mutant(tv, old, new)
                try:
                    got = admit_problems(m) + refuse_problems(m)
                    # review r6 note: the view refuses a sidechain record before the predicate runs, so a clause the
                    # view never reaches is held by check_take's readers, which call the same predicate
                    with mock.patch.object(ct.transcript_view, "is_no_output_nudge", m.is_no_output_nudge):
                        got += count_problems() + checker_problems()
                except Exception as e:  # noqa: BLE001 - a mutant that crashes the reader is red too
                    got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS view {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        for name, old, new in CHECKER_MUTANTS:
            with self.subTest(checker=name):
                got = checker_problems(source_mutant(ct, old, new))
                print(f"\nWITNESS checker {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        for name, mod, old, new in STRICT_MUTANTS:
            with self.subTest(strict=name):
                import pending_walk
                import walk_regrade
                import walk_runner
                mods = {"walk_runner": walk_runner, "pending_walk": pending_walk, "walk_regrade": walk_regrade}
                m = source_mutant(mods[mod], old, new)
                if mod == "walk_regrade":
                    m.RegradeRefused = walk_regrade.RegradeRefused
                got = strict_problems(**{mod: m})
                print(f"\nWITNESS strict {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        for name, old, new in COUNT_MUTANTS:
            with self.subTest(count=name):
                got = count_problems(source_mutant(ct, old, new))
                print(f"\nWITNESS count {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)


if __name__ == "__main__":
    unittest.main()
