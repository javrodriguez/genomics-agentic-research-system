#!/usr/bin/env python3
"""The 25 pre-ruling walks are the isolation denial guard's expected refusals (glitch-b5's ruling 4, Sat 17 Oct 2026,
under Javier's delegation).

The denial guard (check_take.denied_tool_problems, glitch-6b's isolation ruling of 15 Oct 2026) applies to takes after
that ruling. The 25 CP6 walks committed before it (walk records 197658fe, branch walk/w-l4F8UdYQ: arm A practice
walks, never the measured run) ran without the denials, so the guard refuses every one. They are recorded here as its
expected refusals and are not regraded as failures.

  P-record    tests/fixtures/pre-ruling-walks-20261015.json names exactly the 25 walks, each with its walk commit, the
              sha256 of every committed file the guard reads, and its expected refusal: the guard's own output, every
              line [harness-condition-violated].
  P-replay    each walk, rebuilt from the record's reduced files, refuses under the guard in force exactly as recorded.
  P-scope     the draft's walk_scope names ruling 4 and this test: the walks are not rechecked and not regraded as
              failures; every line reruns under the new ship head.
  P-witness   a guard that no longer refuses, or a record whose expected refusal is changed, turns P-replay red.

The reduced files keep what the guard reads (a launch journal whole except its -p prompt, elided with its sha256; a
turn stream's init records; the transcript's deferred_tools_delta attachments). When the record was made the guard's
output on the committed files equalled its output on the reduced ones for all 25.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import build_draft  # noqa: E402
import check_take as ct  # noqa: E402

RECORD = HERE / "tests" / "fixtures" / "pre-ruling-walks-20261015.json"
SOURCE_COMMIT = "197658fe8d826fb19d50fd3f346309e039dee9e8"
PRE_RULING_WALKS = ("w001", "w002", "w003", "w004", "w005", "w008", "w009", "w010", "w011", "w012", "w015", "w016",
                    "w017", "w018", "w019", "w022", "w023", "w024", "w025", "w026", "w027", "w028", "w029", "w030",
                    "w031")
HCV = f"[{ct.HARNESS_CONDITION_VIOLATED}] "


def load_record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def rebuild(walk: dict, into: Path) -> Path:
    """The walk's reduced files written as a walk folder; returns its transcript path."""
    into.mkdir(parents=True)
    for name, f in walk["files"].items():
        if name.endswith(".launch.json"):
            (into / name).write_text(json.dumps(f["kept"]), encoding="utf-8")
        else:
            (into / name).write_text("".join(json.dumps(r) + "\n" for r in f["kept"]), encoding="utf-8")
    return into / "transcript.jsonl"


def record_problems(record: dict) -> list[str]:
    """P-record: the record's shape and its binding to the committed walks."""
    p = []
    if record.get("source", {}).get("commit") != SOURCE_COMMIT:
        p.append(f"source commit {record.get('source', {}).get('commit')!r}, not {SOURCE_COMMIT}")
    walks = record.get("walks", {})
    if tuple(walks) != PRE_RULING_WALKS:
        p.append(f"walks {list(walks)}, not the 25 pre-ruling walks")
    for w, v in walks.items():
        if not (isinstance(v.get("walk_commit"), str) and len(v["walk_commit"]) == 40):
            p.append(f"{w}: no walk commit")
        if "transcript.jsonl" not in v.get("files", {}) or not any(n.endswith(".launch.json") for n in v["files"]):
            p.append(f"{w}: the transcript or a launch journal is missing")
        for name, f in v.get("files", {}).items():
            if not (isinstance(f.get("sha256"), str) and len(f["sha256"]) == 64):
                p.append(f"{w}/{name}: no committed sha256")
        lines = v.get("expected_refusal")
        if not lines or not all(isinstance(x, str) and x.startswith(HCV) for x in lines):
            p.append(f"{w}: the expected refusal is not a non-empty list of [harness-condition-violated] lines")
    return p


def replay_problems(record: dict, guard=None) -> list[str]:
    """P-replay: the guard in force, on each rebuilt walk, gives exactly the recorded refusal."""
    guard = guard or ct.denied_tool_problems
    p = []
    with tempfile.TemporaryDirectory() as tmp:
        for w, v in record["walks"].items():
            got = guard(rebuild(v, Path(tmp) / w))
            if not got:
                p.append(f"{w}: the guard does not refuse it")
            elif got != v["expected_refusal"]:
                p.append(f"{w}: the guard's refusal differs from the recorded one: {got}")
    return p


SCOPE_WORDS = ("glitch-b5's ruling 4", "17 Oct 2026", "expected refusals", "not regraded as failures",
               "tests/test_pre_ruling_walks.py", "not rechecked", "new ship head")


def draft_scope() -> str:
    """The committed draft's walk_scope (harness_furniture_ruling), as build_draft.py builds it."""
    return json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))["harness_furniture_ruling"]["walk_scope"]


def scope_problems(scope: str) -> list[str]:
    """P-scope: the draft names ruling 4 and this test."""
    return [f"walk_scope lacks {w!r}" for w in SCOPE_WORDS if w not in scope]


class TestPreRulingWalks(unittest.TestCase):

    def test_the_record_names_the_25_walks(self):
        record = load_record()
        self.assertEqual(record_problems(record), [])
        self.assertEqual(len(record["walks"]), 25)

    def test_each_walk_is_an_expected_refusal_under_the_guard(self):
        self.assertEqual(replay_problems(load_record()), [])

    def test_the_draft_scopes_them_out_of_the_recheck(self):
        self.assertEqual(scope_problems(draft_scope()), [])


class TestWitnesses(unittest.TestCase):
    """P-witness: each check can go red."""

    def test_a_guard_that_does_not_refuse(self):
        self.assertNotEqual(replay_problems(load_record(), guard=lambda path: []), [])

    def test_a_guard_that_drops_the_init_clause(self):
        def no_inits(path):
            return [x for x in ct.denied_tool_problems(path) if "init offers" not in x]
        self.assertNotEqual(replay_problems(load_record(), guard=no_inits), [])

    def test_a_changed_expected_refusal(self):
        record = load_record()
        record["walks"]["w001"]["expected_refusal"] = record["walks"]["w001"]["expected_refusal"][:-1]
        self.assertNotEqual(replay_problems(record), [])

    def test_a_record_off_its_walks(self):
        for edit in (lambda r: r["walks"].pop("w031"), lambda r: r["source"].__setitem__("commit", "0" * 40),
                     lambda r: r["walks"]["w001"].__setitem__("expected_refusal", ["something else"]),
                     lambda r: r["walks"]["w001"]["files"]["transcript.jsonl"].pop("sha256")):
            record = copy.deepcopy(load_record())
            edit(record)
            self.assertNotEqual(record_problems(record), [])

    def test_a_scope_without_the_ruling(self):
        scope = draft_scope()
        for w in SCOPE_WORDS:
            self.assertNotEqual(scope_problems(scope.replace(w, "")), [], w)

    def test_the_draft_is_build_drafts(self):
        built = build_draft.build()["harness_furniture_ruling"]["walk_scope"]
        self.assertEqual(built, draft_scope())


if __name__ == "__main__":
    unittest.main()
