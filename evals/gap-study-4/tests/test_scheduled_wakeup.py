#!/usr/bin/env python3
"""The scheduled-wakeup kind: a harness-delivered user record, admitted by one shared predicate in both readers.

glitch-6b's ruling of 15 Oct 2026 (CP6 rehearsal walk w006, Haiku, approval-scope normal w1, HELD). The agent called
ScheduleWakeup (delaySeconds 10) in turn 2; Claude Code 2.1.296 kept `claude -p` alive and re-delivered the agent's
own wakeup prompt 68 s later as a user record (transcript line 111) carrying isMeta true, turnOrigin "scheduled",
promptSource "system", no `origin` key, and string content byte-equal (sha256 c50d1115aaef...) to the earlier
ScheduleWakeup call's `prompt` input and to the queue-operation enqueue at line 109. Both readers refused it: the
transcript view refuses any isMeta record, and check_take.user_text_records counted it as a third operator line
(`operator-lines`, harness-error).

The ruling admits exactly that record as `scheduled-wakeup` and nothing else carrying isMeta. Every fixture here is
synthetic: no byte of w006's transcript is copied in.

  W-admit      a w006-shaped take: the view reads the wakeup as a harness event (`user:scheduled-wakeup`), its two
               operator lines stay two, and check_take's record reader puts the wakeup with the harness's texts and
               counts the two scripted operator lines; the transcript reader agrees on the count (readers-disagree).
  W-refuse     each near miss is refused by the view and, as before the ruling, read as an operator line by
               check_take: no earlier ScheduleWakeup prompt, the call after the record, a prompt changed by one
               byte, an extra `origin` key, turnOrigin not "scheduled", promptSource not "system", isMeta "true" (a
               string), isMeta false, content a list of blocks, a second record re-using one consumed prompt, an
               isApiErrorMessage key, a sidechain record, a record whose type is not user, a prompt armed by a
               sidechain or API-error assistant record, and the caveat record.
  W-consume    the consumption rule: each ScheduleWakeup call arms its prompt once; an admitted wakeup consumes the
               earliest unconsumed equal prompt, so two calls with one prompt admit two wakeups and a third is refused.
  W-gate       check_take admits the kind only where the pre-registration names it (meta_kinds): round 3's list,
               without it, reads the record as an operator line exactly as before.
  W-witness    every clause of the predicate, the consumption and check_take's use of it, dropped one at a time in
               an in-memory mutant, turns a named check red.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
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
PROMPT = "Check whether the background job finished and continue with stage 01."   # synthetic, not w006's text
OP1 = "Run stage 00 of the pipeline for project demo."
OP2 = "Now summarise what you found."


def op(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def call(prompt=PROMPT, ref="toolu_w1", **flags):
    return dict({"type": "assistant", "message": {"model": "claude-haiku-4-5-20251001", "content": [
        {"type": "tool_use", "id": ref, "name": "ScheduleWakeup",
         "input": {"delaySeconds": 10, "reason": "wait for the job", "prompt": prompt}}]}}, **flags)


def result(ref="toolu_w1", **extra):
    return {"type": "user", "message": {"content": [dict({"type": "tool_result", "tool_use_id": ref,
                                                           "content": "Wakeup scheduled."}, **extra)]}}


def wakeup(content=PROMPT, **change):
    r = {"type": "user", "isMeta": True, "turnOrigin": "scheduled", "promptSource": "system",
         "message": {"role": "user", "content": content}}
    for k, v in change.items():
        if v is DROP:
            r.pop(k, None)
        else:
            r[k] = v
    return r


DROP = object()


def say(text):
    return {"type": "assistant", "message": {"model": "claude-haiku-4-5-20251001",
                                             "content": [{"type": "text", "text": text}]}}


def enqueue(content=PROMPT):
    return {"type": "queue-operation", "operation": "enqueue", "content": content}


def take(*middle):
    """A w006-shaped take: the operator's first line, the agent's turn (its wakeup call), `middle`, the second line."""
    return [op(OP1), call(), result(), say("Waiting for the job."), *middle, say("Stage 01 done."), op(OP2),
            say("Summary.")]


W006 = take(enqueue(), wakeup())

# Each near miss: (name, records). Every one must be refused by the view and read as an operator line by check_take.
NEAR = {
    "no earlier ScheduleWakeup prompt": [op(OP1), say("x"), enqueue(), wakeup(), op(OP2)],
    "the call comes after the record": [op(OP1), wakeup(), call(), result(), op(OP2)],
    "the prompt changed by one byte": take(wakeup(PROMPT[:-1] + ",")),
    "an extra origin key": take(wakeup(origin={"kind": "hook"})),
    "turnOrigin not scheduled": take(wakeup(turnOrigin="sdk")),
    "turnOrigin missing": take(wakeup(turnOrigin=DROP)),
    "promptSource not system": take(wakeup(promptSource="sdk")),
    "isMeta the string true": take(wakeup(isMeta="true")),
    "isMeta false": take(wakeup(isMeta=False)),
    "content a list of blocks": take(wakeup(message={"role": "user",
                                                     "content": [{"type": "text", "text": PROMPT}]})),
    "a second record re-using one consumed prompt": take(wakeup(), wakeup()),
    "an isApiErrorMessage key": take(wakeup(isApiErrorMessage=False)),
    "a sidechain record": take(wakeup(isSidechain=True)),
    "a record whose type is not user": take(wakeup(type="assistant")),
    "the caveat record": take({"type": "user", "isMeta": True, "message": {"content": "Caveat: the messages"}}),
    # review F (15 Oct 2026): an errored call scheduled nothing; a --resume repeat of one call arms it once
    "the call's result is an error": [op(OP1), call(), result(is_error=True), wakeup(), op(OP2)],
    "a call with no result yet": [op(OP1), call(), wakeup(), result(), op(OP2)],
    "the call's result in a sidechain record": [op(OP1), call(), dict(result(), isSidechain=True), wakeup(), op(OP2)],
    "the call's result in a meta record": [op(OP1), call(), dict(result(), isMeta=True), wakeup(), op(OP2)],
    "a resumed transcript repeats the call and its result": [op(OP1), call(), result(), call(), result(), wakeup(),
                                                             wakeup(), op(OP2)],
}
ALLOWED = {"a second record re-using one consumed prompt": 1,
           "a resumed transcript repeats the call and its result": 1}
# The prompt must be armed by a genuine main-thread agent call: these arm nothing (check_take only; the view refuses
# the arming record itself).
NOT_ARMED = {
    "armed by a sidechain call": [op(OP1), call(isSidechain=True), result(), wakeup(), op(OP2)],
    "armed by an API-error record": [op(OP1), call(isApiErrorMessage=True), result(), wakeup(), op(OP2)],
    "armed by a meta record": [op(OP1), call(isMeta=True), result(), wakeup(), op(OP2)],
    "armed by a synthetic record": [op(OP1), dict(call(), message=dict(call()["message"], model="<synthetic>")),
                                    result(), wakeup(), op(OP2)],
    "armed by another tool's prompt": [op(OP1), {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_t", "name": "Task", "input": {"prompt": PROMPT}}]}}, result("toolu_t"),
        wakeup(), op(OP2)],
}


def source_mutant(mod, old: str, new: str):
    """An in-memory copy of `mod` with `old` (occurring exactly once) replaced by `new`. Registered in sys.modules
    while it executes, because the view's dataclasses resolve their module there; removed afterwards."""
    import types
    src = Path(mod.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"the mutation site occurs {src.count(old)} times in {mod.__file__}: {old!r}")
    m = types.ModuleType(mod.__name__ + "_mutant")
    m.__file__ = mod.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), mod.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


def lines(recs):
    return [json.dumps(r) for r in recs]


def pre(meta=True):
    h = copy.deepcopy(ct.CHECKER_CONSTANTS["harness_delivered_user_records"])
    if not meta:
        h.pop("meta_kinds", None)
    return {"harness_delivered_user_records": h}


def record_reader(recs, meta=True, mod=None):
    """check_take.user_text_records over `recs` written to a file: (ops, harness, unknown, transcript reader count)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "transcript.jsonl"
        p.write_text("\n".join(lines(recs)) + "\n")
        got = (mod or ct).user_text_records(p, pre(meta))
        n_user = sum(1 for t in tx.load(p)["turns"] if t["role"] == "user" and t["text"].strip())
    return got + (n_user,)


def view_admits(recs, view=tv) -> bool:
    try:
        view.events(CC, lines(recs))
    except view.ViewError:
        return False
    return True


# ---- the checks (each returns its problems; a witness shows each can fail) ----------------------------------------

def admit_problems(view=tv, mod=None) -> list[str]:
    out = []
    try:
        evs = view.events(CC, lines(W006))
    except view.ViewError as e:
        return [f"W-admit: the view refused the w006-shaped take: {e}"]
    if tv.operator_lines(evs) != [OP1, OP2]:
        out.append(f"W-admit: the view's operator lines are {tv.operator_lines(evs)!r}, not the scripted two")
    if view.harness_types(CC, lines(W006)).get("user:" + tv.CC_SCHEDULED_WAKEUP) != 1:
        out.append("W-admit: the view does not count one user:scheduled-wakeup harness record")
    wake = [e for e in evs if e.kind == tv.HARNESS and e.text == PROMPT]
    if len(wake) != 2:                       # the enqueue and the wakeup: both the harness's, neither an operator's
        out.append(f"W-admit: {len(wake)} harness events carry the prompt, not 2")
    ops, harness, unknown, n_user = record_reader(W006, mod=mod)
    if ops != [OP1, OP2]:
        out.append(f"W-admit: check_take counts {len(ops)} operator line(s), not the scripted 2")
    if harness != [PROMPT] or unknown:
        out.append(f"W-admit: check_take's harness texts are {harness!r}, unknown {unknown!r}")
    if n_user != len(ops) + len(harness) + len(unknown):
        out.append("W-admit: the transcript reader and the record reader disagree (readers-disagree)")
    return out


def refuse_problems(view=tv, mod=None) -> list[str]:
    """Every near miss is refused by the view; check_take reads it exactly as the reader did before the ruling (its
    gate off: every origin-less user text an operator line), except the wakeups it admits, which must be exactly the
    ones the case allows (one, for the second record re-using a consumed prompt; none otherwise)."""
    out = []
    for name, recs in list(NEAR.items()) + list(NOT_ARMED.items()):
        allowed = ALLOWED.get(name, 0)
        if name in NEAR and view_admits(recs, view):
            out.append(f"W-refuse: the view admitted: {name}")
        before = record_reader(recs, meta=False, mod=mod)[0]
        ops, harness, unknown, n_user = record_reader(recs, mod=mod)
        if len(harness) != allowed or sorted(ops + harness) != sorted(before):
            out.append(f"W-refuse: check_take admitted {len(harness)} wakeup(s), allowed {allowed}: {name}")
    return out


def consume_problems(view=tv, mod=None) -> list[str]:
    out = []
    two = [op(OP1), call(ref="toolu_a"), result("toolu_a"), call(ref="toolu_b"), result("toolu_b"), wakeup(),
           wakeup(), op(OP2)]
    if not view_admits(two, view):
        out.append("W-consume: two calls with one prompt did not admit two wakeups in the view")
    ops, harness, _, _ = record_reader(two, mod=mod)
    if harness != [PROMPT, PROMPT] or ops != [OP1, OP2]:
        out.append("W-consume: two calls with one prompt did not admit two wakeups in check_take")
    three = two[:-1] + [wakeup(), op(OP2)]
    if view_admits(three, view):
        out.append("W-consume: a third wakeup on two calls was admitted by the view")
    ops, harness, _, _ = record_reader(three, mod=mod)
    if len(harness) != 2 or len(ops) != 3:
        out.append("W-consume: a third wakeup on two calls was admitted by check_take")
    return out


def predicate_problems(view=tv) -> list[str]:
    """The predicate on its own, whatever `armed` holds: content that is not a string is never a wakeup, even where an
    equal non-string sits in `armed` (the readers only ever arm strings, so through them this clause is implied by
    membership; this binds it directly)."""
    blocks = [{"type": "text", "text": PROMPT}]
    if view.is_scheduled_wakeup(wakeup(message={"role": "user", "content": blocks}), [blocks]):
        return ["W-predicate: a wakeup whose content is a list of blocks was admitted"]
    return []


def all_problems(view=tv, mod=None) -> list[str]:
    return (admit_problems(view, mod) + refuse_problems(view, mod) + consume_problems(view, mod)
            + predicate_problems(view))


class TheAdmitRule(unittest.TestCase):
    def test_the_w006_shaped_take_is_read_with_two_operator_lines(self):
        self.assertEqual(admit_problems(), [])

    def test_every_near_miss_is_refused_as_before(self):
        self.assertEqual(refuse_problems(), [])

    def test_the_consumption_rule(self):
        self.assertEqual(consume_problems(), [])

    def test_round_3s_list_reads_the_record_as_an_operator_line(self):
        ops, harness, unknown, _ = record_reader(W006, meta=False)
        self.assertEqual((len(ops), harness, unknown), (3, [], []))

    def test_the_predicate_needs_string_content(self):
        self.assertEqual(predicate_problems(), [])

    def test_both_readers_hold_the_one_predicate(self):
        self.assertEqual(tv.CC_SCHEDULED_WAKEUP, "scheduled-wakeup")
        self.assertIs(ct.transcript_view.is_scheduled_wakeup, tv.is_scheduled_wakeup)
        self.assertIs(ct.transcript_view.ScheduledWakeups, tv.ScheduledWakeups)

    def test_the_constant_names_the_kind(self):
        self.assertEqual(ct.CHECKER_CONSTANTS["harness_delivered_user_records"],
                         {"origin_kinds": [tv.CC_TASK_NOTIFICATION],      # + glitch-b5's ruling 3 (w053)
                          "meta_kinds": [tv.CC_SCHEDULED_WAKEUP, tv.CC_NO_OUTPUT_NUDGE]})


# Each clause of the predicate, the consumption, the arming filters, and check_take's use: (name, module, old, new).
VIEW_MUTANTS = (
    ("type", 'rec.get("type") != "user"', "False"),
    ("isMeta", 'rec.get("isMeta") is not True', "False"),
    ("isMeta-truthy", 'rec.get("isMeta") is not True', 'not rec.get("isMeta")'),
    ("turnOrigin", 'rec.get("turnOrigin") != CC_WAKEUP_TURN_ORIGIN', "False"),
    ("promptSource", 'rec.get("promptSource") != CC_WAKEUP_PROMPT_SOURCE', "False"),
    ("no-origin", '"origin" in rec', "False"),
    ("no-api-error", 'any(k in rec for k in CC_WAKEUP_ABSENT_KEYS)', "False"),
    ("not-sidechain", 'rec.get("isSidechain") is True:\n        return False\n    msg', "False:\n        return False\n    msg"),
    ("content-str", "not isinstance(content, str)", "False"),
    ("armed", "return content in armed", "return True"),
    ("consumed", "self.armed.remove(rec[\"message\"][\"content\"])", "pass"),
    ("needs-result", "self.waiting[ref] = prompt", "self.armed.append(prompt)"),
    ("result-not-error", "if not errored:", "if True:"),
    ("once-per-id", "if ref not in self.done and ref not in self.waiting:", "if True:"),
    ("result-genuine", "    if not _genuine_result_record(rec):\n        return []\n", ""),
    ("arm-by-name", 'b.get("name") == CC_WAKEUP_TOOL', "True"),
    ("arm-genuine", "if not _genuine_agent_record(rec):", "if False:"),
)


class TheWitnesses(unittest.TestCase):
    def test_each_clause_dropped_goes_red(self):
        self.assertEqual(all_problems(), [])
        for name, old, new in VIEW_MUTANTS:
            with self.subTest(clause=name):
                m = source_mutant(tv, old, new)
                with mock.patch.object(ct, "transcript_view", m):
                    try:
                        got = all_problems(m)
                    except Exception as e:  # noqa: BLE001 - a mutant that crashes a reader is red too
                        got = [f"raised {type(e).__name__}: {e}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({len(got)}: {got[:1]})",
                      end=" ", file=sys.stderr, flush=True)
                self.assertTrue(got, name)

    def test_check_take_dropping_the_admit_goes_red(self):
        m = source_mutant(ct, "if self.admit and self.seen.admit(rec):", "if False:")
        got = admit_problems(mod=m)
        print(f"\nWITNESS check_take-admit: {'red' if got else 'NOT KILLED'}", end=" ", file=sys.stderr)
        self.assertTrue(got)

    def test_check_take_dropping_the_arming_goes_red(self):
        m = source_mutant(ct, "self.seen.note(rec)", "None")
        got = admit_problems(mod=m)
        print(f"\nWITNESS check_take-note: {'red' if got else 'NOT KILLED'}", end=" ", file=sys.stderr)
        self.assertTrue(got)

    def test_check_take_dropping_the_gate_goes_red(self):
        m = source_mutant(ct, "return _Wakeups(transcript_view.CC_SCHEDULED_WAKEUP in meta, ",   # ruling 3: two gates
                         "return _Wakeups(True, ")
        ops, harness, _, _ = record_reader(W006, meta=False, mod=m)
        print(f"\nWITNESS check_take-gate: {'red' if len(ops) != 3 else 'NOT KILLED'}", end=" ", file=sys.stderr)
        self.assertNotEqual(len(ops), 3)


if __name__ == "__main__":
    unittest.main()
