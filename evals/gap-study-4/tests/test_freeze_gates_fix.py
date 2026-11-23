#!/usr/bin/env python3
"""Lane freeze-gates-fix (Gap Study round 4; glitch-f1's ruling (2), Wed 21 Oct 2026, under Javier's standing
delegation; lane-reports/freeze-gates-fix-LANE.md): two of the walk gates read the records the committed walks carry.

  F2-runtree fixture_walk.run_tree_of reads the ledger's cwd where drive.py's own road wrote one, else the run tree
             every turn's launch journal records (turn-N.jsonl.launch.json cwd), only when all the journals name one
             absolute folder and that folder is named for the ledger's project; a walk naming paths under it is clean,
             and journals that disagree, name another project's folder or are absent leave its paths unplaced.
             Witnesses: ledger-only (the journals unread, the red this lane fixes), project-unbound (any one folder the
             journals agree on is taken as the run tree).
  F3-nested  walk_regrade.agent_summary_problems compares only the fields the walk's checker version wrote: a
             check.json without the key nested_cli_calls passes when the walk folder's derived count is 0 and is named
             when it is not; a key present with null still compares and is named. Witnesses: absent-key-compared (the
             red this lane fixes), absent-key-unbound (an absent key passes whatever the derived count).

  F4-exception (S8, glitch-f1's ruling 1 on the hand-back) fixture_walk's recorded per-walk exception applies only to
             its walk and path while every transcript line naming the path is a recorded line with its recorded bytes
             and command; it is reported in replay's recorded_exceptions; one that matches no committed transcript is
             named by stale_exception_problems; an exception never excuses a study (leak) path. Witnesses:
             exception-unbound (the line's bytes unchecked), stale-silent (a stale exception never named),
             exception-excuses-leak (S10). F2 also refuses a linked journal: witness linked-journal-read (S10).

Synthetic folders in temporary directories only: no walk record, model, network, container or credential.
check_take.agent_summary is replaced for the duration of one call by mock.patch.object, restored on exit. No module
is added to or replaced in sys.modules beyond the study modules a plain import adds; a witness module is compiled in
memory and never registered.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
_PATH = list(sys.path)                 # restored below: fixture_walk's own import inserts entries
sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402
import fixture_walk as fw  # noqa: E402
import walk_regrade as wg  # noqa: E402

sys.path[:] = _PATH


def guarded(prefix):
    def wrap(fn):
        def check(mod):
            try:
                return fn(mod, prefix)
            except Exception as e:  # noqa: BLE001
                return [f"ERROR {prefix}: {type(e).__name__}: {str(e)[:240]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


OPERATOR_LINE = json.dumps({"type": "user", "message": {"content": "go"}})   # lane fold3/m1: one operator turn


def walk_folder(root: Path, name: str, *, ledger: dict, journals: dict, said: str) -> Path:
    """rehearsals/<name>/ with a driver ledger, launch journals {turn: cwd or raw text}, and a transcript whose one
    assistant line names `said`."""
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "driver-ledger.json").write_text(json.dumps(ledger))
    for k, cwd in journals.items():
        link = isinstance(cwd, str) and cwd.startswith("LINK:")
        cwd = cwd.removeprefix("LINK:") if link else cwd
        text = cwd if isinstance(cwd, str) and cwd.startswith("RAW:") else json.dumps(
            {"schema": 1, "harness": "claude-code", "argv": ["claude", "-p", "x"], "cwd": cwd})
        if link:
            (root / f"{name}-journal-{k}.json").write_text(text)
            (folder / f"turn-{k}.jsonl.launch.json").symlink_to(root / f"{name}-journal-{k}.json")
        else:
            (folder / f"turn-{k}.jsonl.launch.json").write_text(text.removeprefix("RAW:"))
    rec = {"type": "assistant", "message": {"content": [{"type": "text", "text": f"I read {said} next."}]}}
    # lane fold3/m1 (review of 1cb4ee64, MINOR 1a): a walk read with no turn is unread, so the rig's walk has one
    (folder / "transcript.jsonl").write_text(json.dumps(rec) + "\n" + OPERATOR_LINE + "\n")
    return folder / "transcript.jsonl"


@guarded("F2-runtree")
def f2_runtree(mod, p):
    out = []
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        tree, other = "/tmp/run-0a1b2c3d", "/tmp/run-99999999"
        path = tree + "/gars/CLAUDE.md"
        cases = {
            # name: (ledger, journals, run tree wanted, verdict wanted)
            "the ledger's cwd (drive.py's road)": ({"cwd": tree, "project": "run-0a1b2c3d"}, {}, tree, "clean"),
            "every journal names the project's folder": ({"project": "run-0a1b2c3d"}, {1: tree, 2: tree, 3: tree},
                                                         tree, "clean"),
            "journals disagree": ({"project": "run-0a1b2c3d"}, {1: tree, 2: other}, None, "unplaced"),
            "the journals name another project's folder": ({"project": "run-0a1b2c3d"}, {1: other}, None,
                                                           "unplaced"),
            "the ledger names no project": ({}, {1: tree}, None, "unplaced"),
            "no journal": ({"project": "run-0a1b2c3d"}, {}, None, "unplaced"),
            "a journal that is not JSON": ({"project": "run-0a1b2c3d"}, {1: tree, 2: "RAW:{not json"}, None,
                                           "unplaced"),
            "a relative journal cwd": ({"project": "run-0a1b2c3d"}, {1: "run-0a1b2c3d"}, None, "unplaced"),
            # S10 (review m2, J4): a linked journal is no record, even one naming the same folder
            "a symlinked journal": ({"project": "run-0a1b2c3d"}, {1: tree, 2: "LINK:" + tree}, None, "unplaced"),
        }
        for i, (what, (ledger, journals, want_tree, want_verdict)) in enumerate(cases.items()):
            t = walk_folder(root, f"w{i:03d}", ledger=ledger, journals=journals, said=path)
            got = mod.run_tree_of(t)
            if got != want_tree:
                out.append(f"{p}: {what}: run tree {got!r}, wanted {want_tree!r}")
            verdict = mod.replay(t)["verdict"]
            if verdict != want_verdict:
                out.append(f"{p}: {what}: verdict {verdict!r}, wanted {want_verdict!r}")
    return out


@guarded("F4-exception")
def f4_exception(mod, p):
    import hashlib
    out = []
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        tree, scratch = "/tmp/run-0a1b2c3d", "/tmp/synthetic-scratch.log"
        cmd = f"python3 stage.py 2>&1 | tee {scratch}"

        def walk(name, extra_line=False, edited=False):
            folder = root / name
            folder.mkdir()
            (folder / "driver-ledger.json").write_text(json.dumps({"project": "run-0a1b2c3d"}))
            (folder / "turn-1.jsonl.launch.json").write_text(json.dumps({"cwd": tree}))
            recs = [{"type": "assistant", "message": {"content": [{"type": "text", "text": f"I read {tree}/gars/x."}]}},
                    {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash",
                                                                   "input": {"command": cmd}}]}}]
            if extra_line:
                recs.append({"type": "assistant", "message": {"content": [{"type": "text", "text": f"cat {scratch}"}]}})
            lines = [json.dumps(r) for r in recs] + [OPERATOR_LINE]     # lane fold3/m1: one operator turn, last
            sha = hashlib.sha256(lines[1].encode()).hexdigest()
            if edited:
                lines[1] = lines[1].replace('"id": "t1"', '"id": "t2"')     # the bytes, not the command
            (folder / "transcript.jsonl").write_text("\n".join(lines) + "\n")
            return folder / "transcript.jsonl", sha

        cases = {"the recorded line": ("w901", {}, "excepted"),
                 "the path named on a second line": ("w902", {"extra_line": True}, "unplaced"),
                 "the recorded line's bytes edited": ("w903", {"edited": True}, "unplaced"),
                 "another walk": ("w904", {}, "unplaced")}
        for what, (name, kw, want) in cases.items():
            t, sha = walk(name, **kw)
            exc = {"walk": name if what != "another walk" else "w999", "path": scratch, "lines": {2: sha},
                   "command": cmd, "reason": "synthetic", "ruling": "synthetic"}
            with mock.patch.object(mod, "RECORDED_EXCEPTIONS", (exc,)):
                rec = mod.replay(t)
                stale = mod.stale_exception_problems([t])
            if rec["verdict"] != want:
                out.append(f"{p}: {what}: verdict {rec['verdict']!r}, wanted {want!r}")
            if want == "excepted" and [e["path"] for e in rec.get("recorded_exceptions", [])] != [scratch]:
                out.append(f"{p}: {what}: the exception is not reported: {rec.get('recorded_exceptions')}")
            if bool(stale) != (want != "excepted"):
                out.append(f"{p}: {what}: stale_exception_problems gave {stale}")
        # S10 (review m2, R4): a recorded exception never excuses a path inside the study; the walk still leaks
        leak = str(mod.REPO / "evals" / "gap-study-4" / "prereg-draft.json")
        folder = root / "w905"
        folder.mkdir()
        (folder / "driver-ledger.json").write_text(json.dumps({"project": "run-0a1b2c3d"}))
        (folder / "turn-1.jsonl.launch.json").write_text(json.dumps({"cwd": tree}))
        line = json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": f"cat {leak} now"}]}})
        (folder / "transcript.jsonl").write_text(line + "\n" + OPERATOR_LINE + "\n")
        exc = {"walk": "w905", "path": leak, "lines": {1: hashlib.sha256(line.encode()).hexdigest()},
               "command": f"cat {leak}", "reason": "synthetic", "ruling": "synthetic"}
        with mock.patch.object(mod, "RECORDED_EXCEPTIONS", (exc,)):
            rec = mod.replay(folder / "transcript.jsonl")
        if rec["verdict"] != "leaks" or rec.get("recorded_exceptions"):
            out.append(f"{p}: an exception naming a study path: verdict {rec['verdict']!r}, "
                       f"exceptions {rec.get('recorded_exceptions')}")
    return out


SUB = {"calls": [], "models": [], "stream_file_differences": 0}


@guarded("F3-nested")
def f3_nested(mod, p):
    out = []
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / "transcript.jsonl"
        t.write_text("")
        cases = {
            # name: (check.json fields, derived summary, named?)
            "no key, derived 0": ({"agent_calls": 0, "subagents": SUB}, {"agent_calls": 0, "subagents": SUB,
                                                                          "nested_cli_calls": 0}, False),
            "no key, derived 2": ({"agent_calls": 0, "subagents": SUB}, {"agent_calls": 0, "subagents": SUB,
                                                                          "nested_cli_calls": 2}, True),
            "no key, derived 0, agent_calls forged": ({"agent_calls": 3, "subagents": SUB},
                                                      {"agent_calls": 0, "subagents": SUB, "nested_cli_calls": 0},
                                                      True),
            "key 0, derived 0": ({"agent_calls": 0, "subagents": SUB, "nested_cli_calls": 0},
                                 {"agent_calls": 0, "subagents": SUB, "nested_cli_calls": 0}, False),
            "key 0, derived 1": ({"agent_calls": 0, "subagents": SUB, "nested_cli_calls": 0},
                                 {"agent_calls": 0, "subagents": SUB, "nested_cli_calls": 1}, True),
            "key null, derived 0": ({"agent_calls": 0, "subagents": SUB, "nested_cli_calls": None},
                                    {"agent_calls": 0, "subagents": SUB, "nested_cli_calls": 0}, True),
        }
        for what, (check, derived, named) in cases.items():
            with mock.patch.object(ct, "agent_summary", lambda path, derived=derived: dict(derived)):
                got = mod.agent_summary_problems(dict(check, walk="w001"), t)
            if bool(got) != named:
                out.append(f"{p}: {what}: {'named' if got else 'passed'} ({got})")
            if what == "no key, derived 2" and got and "nested" not in got[0]:
                out.append(f"{p}: {what}: the problem does not name nested_cli_calls: {got}")
    return out


class TestFreezeGatesFix(unittest.TestCase):
    def test_f2_the_claude_walks_run_tree_from_their_launch_journals(self):
        self.assertEqual(f2_runtree(fw), [])

    def test_f3_only_the_fields_the_checker_version_wrote(self):
        self.assertEqual(f3_nested(wg), [])

    def test_f4_a_recorded_per_walk_exception_is_bound_and_printed(self):
        self.assertEqual(f4_exception(fw), [])

    def test_f4_the_committed_exceptions_are_w023s_w142s_and_w158s(self):
        # lane prefreeze-road (the Lane-orchestrator's ruling 1, 24 Oct 2026): the two placeholder exceptions join w023's;
        # lane gap-rewalk-fix (glitch-45, 27 Oct 2026): the rewalk merge's five, two in w023's class, three in w142's
        # lane fold3/m1 (glitch-45, fold3 brief): the vendor walks' entries follow these eight; tests/test_fold3_m1.py
        # binds them
        self.assertEqual([(e["walk"], e["path"], sorted(e["lines"])) for e in fw.RECORDED_EXCEPTIONS[:8]],
                         [("w023", "/tmp/finalize.log", [74]), ("w142", "/home/<user", [11, 86]),
                          ("w158", "/home/<user", [11, 49]),
                          ("w172", "/tmp/run-e680031a-finalize.json", [86, 93, 94]),
                          ("w194", "/tmp/s01.json", [69]),
                          ("w179", "/home/<user", [11, 57]), ("w180", "/home/<user", [11, 86]),
                          ("w198", "/home/<user", [11, 41])], "F4-exception")


class WitnessNotPerformed(AssertionError):
    pass


def witness_module(real: types.ModuleType, edits: tuple) -> types.ModuleType:
    with open(real.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(real.__name__ + "_fgf_witness")
    mod.__file__ = real.__file__
    path, modules = list(sys.path), set(sys.modules)
    try:
        exec(compile(src, real.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.path[:] = path             # the module's own top-level sys.path.insert, undone
        for name in set(sys.modules) - modules:     # S14: an import the compile re-registered (a module an
            del sys.modules[name]                   # earlier test dropped), undone, so no second copy stays
    return mod


WITNESSES = {
    "ledger-only": (fw, (("    project = doc.get(\"project\")\n    if not isinstance(project, str) or not project:",
                          "    project = None\n    if not isinstance(project, str) or not project:"),),
                    f2_runtree, "F2-runtree"),
    "project-unbound": (fw, (("    return tree if PurePosixPath(os.path.normpath(tree)).name == project else None",
                              "    return tree"),), f2_runtree, "F2-runtree"),
    "absent-key-compared": (wg, (("    if \"nested_cli_calls\" not in check:\n        derived = dict(derived)",
                                  "    if False:\n        derived = dict(derived)"),
                                 ("    if \"nested_cli_calls\" in check:\n        recorded[\"nested_cli_calls\"]",
                                  "    if True:\n        recorded[\"nested_cli_calls\"]")), f3_nested, "F3-nested"),
    "exception-unbound": (fw, (("            if hashlib.sha256(raw).hexdigest() != sha:",
                                "            if False and hashlib.sha256(raw).hexdigest() != sha:"),),
                          f4_exception, "F4-exception"),
    # S10 (the lane review's survivors R4 and J4)
    "exception-excuses-leak": (fw, (('if r["kind"] == "elsewhere" and (exc :=',
                                     'if r["kind"] in ("elsewhere", "study") and (exc :='),), f4_exception,
                               "F4-exception"),
    "linked-journal-read": (fw, (("        if p.is_symlink() or not p.is_file():", "        if not p.is_file():"),),
                            f2_runtree, "F2-runtree"),
    "stale-silent": (fw, (("            out.append(f\"the recorded exception for {exc['walk']}",
                           "            0 and out.append(f\"the recorded exception for {exc['walk']}"),),
                     f4_exception, "F4-exception"),
    "absent-key-unbound": (wg, (("        if nested != 0:\n            out.append(",
                                 "        if False:\n            out.append("),), f3_nested, "F3-nested"),
}


class TestWitnesses(unittest.TestCase):
    def kill(self, name):
        real, edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(real), [], f"{name}: the bound check is not green on {Path(real.__file__).name}")
        modules_before = set(sys.modules)
        got = check(witness_module(real, edits))
        self.assertEqual(set(sys.modules) - modules_before, set(), f"{name}: the witness registered a module")
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        print(f"\nWITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
              f"{len(errors)} errors)", end=" ", file=sys.stderr, flush=True)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_ledger_only(self):
        self.kill("ledger-only")

    def test_witness_project_unbound(self):
        self.kill("project-unbound")

    def test_witness_absent_key_compared(self):
        self.kill("absent-key-compared")

    def test_witness_absent_key_unbound(self):
        self.kill("absent-key-unbound")

    def test_witness_exception_unbound(self):
        self.kill("exception-unbound")

    def test_witness_stale_silent(self):
        self.kill("stale-silent")

    def test_witness_exception_excuses_leak(self):
        self.kill("exception-excuses-leak")

    def test_witness_linked_journal_read(self):
        self.kill("linked-journal-read")

    def test_the_witnesses_are_named(self):
        self.assertEqual(sorted(WITNESSES), ["absent-key-compared", "absent-key-unbound", "exception-excuses-leak",
                                             "exception-unbound", "ledger-only", "linked-journal-read",
                                             "project-unbound", "stale-silent"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
