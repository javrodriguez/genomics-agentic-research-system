#!/usr/bin/env python3
"""The walk register and the review register's usage (Gap Study round 4, lane w7d, wave 7 piece P3).

The plan's CP6 (lines 868-893) makes every pre-freeze walk a rehearsal: graded, never counted, committed with its
reason. walk_register.py is the machine-checked list of those walks: every folder under rehearsals/ is registered,
every registered walk has its folder, and every entry is well formed and says it is not counted. With no walk run,
the register is empty and --check passes on empty by saying "0 walks" out loud, never silently.

review_kit/rounds.py was copied from round 3 identical, so its usage lines named evals/gap-study-3/; the plan's
CP6 VALIDATE command runs evals/gap-study-4/review_kit/rounds.py, and the usage now names round 4's paths.

Synthetic rehearsal folders in temporary directories, the committed prereg-draft.json and tasks/*.json, read only;
no walk, model, network, container or take.

--mutant NAME compiles one altered walk_register.py (or one altered rounds.py text) in memory in setUpModule.
--witnesses runs every registered mutant in its own process and requires its bound method to fail by an
AssertionError carrying its clause token (rule B; collateral is listed, not credited).
"""
from __future__ import annotations

import contextlib
import os
import io
import json
import re
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import study  # noqa: E402

SOURCE = HERE / "walk_register.py"
ROUNDS = HERE / "review_kit" / "rounds.py"
SELECTED = None
wr = None


def rounds_text() -> str:
    """The accessor the usage test reads rounds.py through (the witness swaps what it returns)."""
    return ROUNDS.read_text()


def mutants():
    """name -> (clause, file, old text, new text). Each weakens one guard; old must occur exactly once."""
    return {
        # an unregistered walk folder admitted
        "unregistered-admitted": ("R1.unregistered", "walk_register.py",
                                  "problems.append(f\"rehearsals/{name}/ is a walk folder the register does not list",
                                  "(f\"rehearsals/{name}/ is a walk folder the register does not list"),
        # a stray top-level file admitted
        "stray-file-admitted": ("R1.unregistered", "walk_register.py",
                                "problems.append(f\"rehearsals/{name} is a file beside the register",
                                "(f\"rehearsals/{name} is a file beside the register"),
        # a registered walk with no folder admitted
        "missing-folder-admitted": ("R2.folder", "walk_register.py",
                                    "problems.append(f\"walk {walk!r} is registered and rehearsals/{walk}/ does not exist",
                                    "(f\"walk {walk!r} is registered and rehearsals/{walk}/ does not exist"),
        # a registered walk whose folder holds no file admitted
        "empty-folder-admitted": ("R2.folder", "walk_register.py",
                                  "problems.append(f\"walk {walk!r} is registered and rehearsals/{walk}/ holds no file",
                                  "(f\"walk {walk!r} is registered and rehearsals/{walk}/ holds no file"),
        # a malformed entry admitted: the field set is not checked
        "fields-unchecked": ("R3.malformed", "walk_register.py",
                             "    if set(entry) != set(FIELDS):", "    if False:"),
        # a walk recorded as counted admitted
        "counted-admitted": ("R3.malformed", "walk_register.py",
                             "    if entry[\"counted\"] is not False:", "    if False:"),
        # a walk naming a task the design does not have admitted
        "design-unchecked": ("R3.malformed", "walk_register.py",
                             "out.append(f\"{where}: task {task!r} is not a task",
                             "(f\"{where}: task {task!r} is not a task"),
        # an empty register passes silently, without saying it registered 0 walks
        "silent-empty": ("R4.empty", "walk_register.py",
                         "print(f\"ok, having registered 0 walks: ", "print(f\"ok: "),
        # W7D-R1-1: a registered walk's folder looked up by path, which ignores case on APFS
        "folder-by-path": ("R5.case", "walk_register.py",
                           "folder = names.get(walk)", "folder = base / walk if (base / walk).exists() else None"),
        # W7D-R1-1: two ids that differ only by case admitted
        "case-collision-admitted": ("R5.case", "walk_register.py",
                                    "problems.append(f\"walk entry {i}: walk {walk!r} and {seen_fold[folded]!r} differ only by case",
                                    "(f\"walk entry {i}: walk {walk!r} and {seen_fold[folded]!r} differ only by case"),
        # W7D-R1-2: a symlink counted as a walk's file
        "symlink-file-admitted": ("R6.symlink", "walk_register.py",
                                  "p.is_file() and not p.is_symlink()", "p.is_file()"),
        # W7D-R1-4: a symlinked walk folder admitted as the walk's folder
        "symlink-folder-admitted": ("R6.symlink", "walk_register.py",
                                    "if folder is None or folder.is_symlink() or not folder.is_dir():",
                                    "if folder is None or not folder.is_dir():"),
        # W7D-R1-2: a register.json that is a symlink admitted
        "register-symlink-admitted": ("R6.symlink", "walk_register.py",
                                      "    if reg.is_symlink():", "    if False:"),
        # W7D-R1-3: duplicate keys read as the last one
        "duplicate-keys-admitted": ("R7.dupkey", "walk_register.py",
                                    # the register read (4e0d64ac added a second hook, on the rechecks history read)
                                    "doc = json.loads(text, object_pairs_hook=no_duplicate_keys)",
                                    "doc = json.loads(text, object_pairs_hook=dict)"),
        # W7D-R1-4: one id registered twice admitted
        "duplicate-id-admitted": ("R3.malformed", "walk_register.py",
                                  "problems.append(f\"walk entry {i}: walk {walk!r} is registered twice",
                                  "(f\"walk entry {i}: walk {walk!r} is registered twice"),
        # W7D-R1-4: the walk id's one-segment shape unchecked
        "walk-id-unchecked": ("R3.malformed", "walk_register.py",
                              "    if not WALK_ID.fullmatch(entry[\"walk\"]):", "    if False:"),
        # W7D-R1-6: schema compared by value, so true and 1.0 pass
        "schema-by-value": ("R8.nits", "walk_register.py",
                            # 4e0d64ac: the int-type clause moved into top_keys (schema 1 or 2)
                            "        if type(schema) is int else ()", "        if True else ()"),
        # W7D-R1-6: a reason of format characters only admitted
        "reason-format-admitted": ("R8.nits", "walk_register.py",
                                   "unicodedata.category(c) == \"Cf\"", "False"),
        # W7D-R1-6: an unreadable register raises instead of a FAIL line
        "unreadable-raises": ("R8.nits", "walk_register.py",
                              "    except OSError as exc:\n        return [f\"rehearsals/{REGISTER_NAME} cannot be read",
                              "    except KeyError as exc:\n        return [f\"rehearsals/{REGISTER_NAME} cannot be read"),
        # round 3's path back in rounds.py's usage
        "round3-usage": ("U1.usage", "rounds.py",
                         "python3 evals/gap-study-4/review_kit/rounds.py --check",
                         "python3 evals/gap-study-3/review_kit/rounds.py --check"),
    }


def load_register(source: str):
    mod = types.ModuleType("walk_register")
    mod.__file__ = str(SOURCE)
    exec(compile(source, str(SOURCE), "exec"), mod.__dict__)
    return mod


def setUpModule():
    global wr, rounds_text
    source = SOURCE.read_text()
    if SELECTED is not None:
        _, where, old, new = mutants()[SELECTED]
        if where == "walk_register.py":
            assert source.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {source.count(old)} times"
            source = source.replace(old, new)
        else:
            text = ROUNDS.read_text()
            assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
            mutated = text.replace(old, new)
            rounds_text = lambda: mutated  # noqa: E731
    wr = load_register(source)


def a_walk(**over):
    """A well-formed entry built from the committed draft: its first task, that task's first half and wording, and
    arm A's smallest model."""
    design = json.loads((HERE / "prereg-draft.json").read_text())
    task = design["tasks"][0]["id"]
    halves = list(json.loads((HERE / "tasks" / f"{task}.json").read_text())["halves"])
    entry = {"walk": "w-0001", "task": task, "half": halves[0], "wording": design["tasks"][0]["wordings"][0],
             "arm": "A", "model": design["models"]["A"][-1],
             "reason": "synthetic: every wording of every task on the smallest model (plan CP6)", "counted": False}
    entry.update(over)
    return entry


@contextlib.contextmanager
def case_blind(base: Path):
    """Simulate APFS's case-blind lookup under `base` on any filesystem (athena's ext4 is case-sensitive).

    A path query (exists, is_dir, is_file, is_symlink, rglob) on a path under `base` whose exact name is not listed
    is answered for the one listed entry that matches it by case. iterdir() is left exact, as on APFS, where a listing
    keeps each entry's own name. The real listing is read with os.listdir, never through the patched methods."""
    from unittest import mock
    root = Path(base)

    def canonical(path):
        try:
            parts = Path(path).relative_to(root).parts
        except ValueError:
            return path
        here = root
        for part in parts:
            try:
                listed = os.listdir(here)
            except OSError:
                return path
            if part not in listed:
                match = [n for n in listed if n.casefold() == part.casefold()]
                if len(match) != 1:
                    return path
                part = match[0]
            here = here / part
        return here

    def folding(original):
        def method(self, *args, **kwargs):
            return original(canonical(self), *args, **kwargs)
        return method

    with contextlib.ExitStack() as stack:
        for name in ("exists", "is_dir", "is_file", "is_symlink", "rglob"):
            stack.enter_context(mock.patch.object(Path, name, folding(getattr(Path, name))))
        yield


class Rig:
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="w7d-"))
        self.base = self.tmp / "rehearsals"
        self.base.mkdir()
        (self.base / "README.md").write_text("synthetic\n")

    def register(self, walks, **top):
        doc = {"schema": 1, "walks": walks}
        doc.update(top)
        (self.base / "register.json").write_text(json.dumps(doc, indent=2) + "\n")

    def folder(self, name, with_file=True):
        d = self.base / name
        d.mkdir()
        if with_file:
            (d / "driver-ledger.json").write_text("{}\n")
        return d

    def check(self):
        return wr.check(self.base)

    def close(self):
        shutil.rmtree(self.tmp)


class TheRegister(unittest.TestCase):
    def setUp(self):
        self.rig = Rig()

    def tearDown(self):
        self.rig.close()

    def test_unregistered_walk_folder_fails(self):
        self.rig.register([])
        self.rig.folder("w-0001")
        problems, n = self.rig.check()
        self.assertTrue(any("w-0001" in p and "does not list" in p for p in problems), "R1.unregistered")
        self.assertEqual(n, 0, "R1.unregistered")
        # one registered, one not: only the second is named
        self.rig.register([a_walk()])
        self.rig.folder("w-0002")
        problems, n = self.rig.check()
        self.assertEqual([p for p in problems if "does not list" in p and "w-0002" in p], problems, "R1.unregistered")
        self.assertEqual(len(problems), 1, "R1.unregistered")
        # a stray file beside the register is not a walk and is refused, never skipped
        shutil.rmtree(self.rig.base / "w-0002")
        (self.rig.base / "notes.txt").write_text("x\n")
        problems, _ = self.rig.check()
        self.assertTrue(any("notes.txt" in p and "beside the register" in p for p in problems), "R1.unregistered")

    def test_registered_walk_without_its_folder_fails(self):
        self.rig.register([a_walk()])
        problems, _ = self.rig.check()
        self.assertTrue(any("w-0001" in p and "does not exist" in p for p in problems), "R2.folder")
        # a folder with no file in it is a folder git does not keep: refused as well
        self.rig.folder("w-0001", with_file=False)
        problems, _ = self.rig.check()
        self.assertTrue(any("w-0001" in p and "holds no file" in p for p in problems), "R2.folder")
        # with a file, the same register is clean
        (self.rig.base / "w-0001" / "driver-ledger.json").write_text("{}\n")
        problems, n = self.rig.check()
        self.assertEqual((problems, n), ([], 1), "R2.folder")

    def test_malformed_entry_fails(self):
        cases = {
            "missing reason": {k: v for k, v in a_walk().items() if k != "reason"},
            "extra key": dict(a_walk(), score=1),
            "empty reason": a_walk(reason="   "),
            "counted": a_walk(counted=True),
            "counted as a string": a_walk(counted="false"),
            "two segments": a_walk(walk="a/b"),
            "unknown task": a_walk(task="no-such-task"),
            "unknown half": a_walk(half="control"),
            "unknown wording": a_walk(wording="w9"),
            "unknown arm": a_walk(arm="Z"),
            "model of another arm": a_walk(model="gpt-6-luna"),
            "not an object": ["w-0001"],
        }
        for what, entry in cases.items():
            with self.subTest(case=what):
                rig = Rig()
                try:
                    rig.register([entry])
                    rig.folder("w-0001")
                    problems, _ = rig.check()
                    self.assertTrue(any(p.startswith("walk entry 0") for p in problems),
                                    f"R3.malformed {what}: {problems}")
                finally:
                    rig.close()
        # duplicate walk ids, a wrong schema, an unknown top-level key, and a register that is not JSON
        self.rig.register([a_walk(), a_walk()])
        self.rig.folder("w-0001")
        self.assertTrue(any("twice" in p for p in self.rig.check()[0]), "R3.malformed")
        self.rig.register([a_walk()], schema=2)
        self.assertTrue(any("schema" in p for p in self.rig.check()[0]), "R3.malformed")
        self.rig.register([a_walk()], extra=True)
        self.assertTrue(any("top-level" in p for p in self.rig.check()[0]), "R3.malformed")
        (self.rig.base / "register.json").write_text("{not json\n")
        self.assertTrue(any("not JSON" in p for p in self.rig.check()[0]), "R3.malformed")
        # the well-formed entry is clean, on arm C's optional model too
        self.rig.register([a_walk(), a_walk(walk="w-0002", arm="C", model="claude-fable-5-1")])
        self.rig.folder("w-0002")
        self.assertEqual(self.rig.check(), ([], 2), "R3.malformed")

    def test_empty_register_says_zero_walks(self):
        self.rig.register([])
        self.assertEqual(self.rig.check(), ([], 0), "R4.empty")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = wr.main(["--check", "--base", str(self.rig.base)])
        self.assertEqual(code, 0, "R4.empty")
        self.assertRegex(out.getvalue(), r"(?m)^ok, having registered 0 walks: ", "R4.empty")
        # a missing register is not an empty one
        (self.rig.base / "register.json").unlink()
        self.assertTrue(any("register.json" in p and "missing" in p for p in self.rig.check()[0]), "R4.empty")
        # the committed register (lane freeze-gates-fix, glitch-f1's ruling (2), 21 Oct 2026): registered since the
        # walks were merged, so --check passes saying how many it registered, the count read from register.json's own
        # list, never the empty sentence
        committed = json.loads((HERE / "rehearsals" / "register.json").read_text())["walks"]
        self.assertTrue(committed, "R4.empty")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = wr.main(["--check"])
        self.assertEqual(code, 0, "R4.empty")
        self.assertRegex(out.getvalue(), rf"(?m)^ok: {len(committed)} registered walk\(s\), each with its folder, "
                                         r"none counted$", "R4.empty")
        self.assertNotRegex(out.getvalue(), r"registered 0 walks", "R4.empty")


class TheRegisterFold(unittest.TestCase):
    """Review round 1 (W7D-R1-1 to R1-4, R1-6), ruling W7D-close-1."""

    def setUp(self):
        self.rig = Rig()

    def tearDown(self):
        reg = self.rig.base / "register.json"
        if reg.exists() and not reg.is_symlink():
            os.chmod(reg, 0o600)
        self.rig.close()

    def test_folders_match_by_exact_name(self):
        # W7D-R1-1: "W-1" registered, "w-1/" on disk: the Mac's case-blind filesystem must not make them one
        self.rig.register([a_walk(walk="W-1")])
        self.rig.folder("w-1")
        # Leg 1, the real filesystem: on APFS (case-blind) this alone catches a path lookup; on a case-sensitive
        # filesystem (athena's ext4) a path lookup also misses "W-1", so this leg cannot tell the two apart there.
        problems, _ = self.rig.check()
        self.assertTrue(any("'W-1'" in p and "does not exist" in p for p in problems), f"R5.case {problems}")
        self.assertTrue(any("rehearsals/w-1/" in p and "does not list" in p for p in problems), f"R5.case {problems}")
        # Leg 2, a case-blind lookup simulated on every filesystem (athena run on 22b320be): path queries under the
        # rig resolve a name by case, as APFS does, while the directory listing keeps its exact names. A path lookup
        # then finds "W-1"; the exact-name match must still refuse it.
        with case_blind(self.rig.base):
            self.assertTrue((self.rig.base / "W-1").is_dir() and (self.rig.base / "W-1").exists(),
                            "the case-blind simulation is not armed")
            self.assertEqual(sorted(p.name for p in self.rig.base.iterdir()), ["README.md", "register.json", "w-1"],
                             "the case-blind simulation changed the listing")
            problems, _ = self.rig.check()
        self.assertTrue(any("'W-1'" in p and "does not exist" in p for p in problems), f"R5.case (case-blind) {problems}")
        self.assertTrue(any("rehearsals/w-1/" in p and "does not list" in p for p in problems),
                        f"R5.case (case-blind) {problems}")
        # two ids that differ only by case are refused, folder or not
        self.rig.register([a_walk(walk="w-1"), a_walk(walk="W-1")])
        problems, _ = self.rig.check()
        self.assertTrue(any("differ only by case" in p for p in problems), f"R5.case {problems}")

    def test_symlinks_are_not_walk_records(self):
        outside = self.rig.tmp / "outside"
        outside.mkdir()
        (outside / "x.json").write_text("{}\n")
        # a walk folder holding only a symlink to a file holds no file
        self.rig.register([a_walk()])
        (self.rig.base / "w-0001").mkdir()
        os.symlink(outside / "x.json", self.rig.base / "w-0001" / "x.json")
        problems, _ = self.rig.check()
        self.assertTrue(any("'w-0001'" in p and "holds no file" in p for p in problems), f"R6.symlink {problems}")
        shutil.rmtree(self.rig.base / "w-0001")
        # a walk folder that is a symlink to a folder is not the walk's folder
        os.symlink(outside, self.rig.base / "w-0001")
        problems, _ = self.rig.check()
        self.assertTrue(any("'w-0001'" in p and "does not exist as a folder" in p for p in problems),
                        f"R6.symlink {problems}")
        (self.rig.base / "w-0001").unlink()
        # a register.json that is a symlink is refused, whatever it points at
        (outside / "r.json").write_text(json.dumps({"schema": 1, "walks": []}))
        (self.rig.base / "register.json").unlink()
        os.symlink(outside / "r.json", self.rig.base / "register.json")
        problems, _ = self.rig.check()
        self.assertTrue(any("register.json" in p and "symlink" in p for p in problems), f"R6.symlink {problems}")

    def test_duplicate_keys_are_refused(self):
        self.rig.folder("w-0001")
        entry = json.dumps(a_walk(counted=True))[:-1] + ', "counted": false}'
        (self.rig.base / "register.json").write_text('{"schema": 1, "walks": [' + entry + ']}')
        problems, _ = self.rig.check()
        self.assertTrue(any("duplicate key 'counted'" in p for p in problems), f"R7.dupkey {problems}")
        (self.rig.base / "register.json").write_text('{"schema": 1, "walks": [], "walks": []}')
        problems, _ = self.rig.check()
        self.assertTrue(any("duplicate key 'walks'" in p for p in problems), f"R7.dupkey {problems}")

    def test_review_nits(self):
        # schema: an int, never true or 1.0
        for raw in ('{"schema": true, "walks": []}', '{"schema": 1.0, "walks": []}'):
            (self.rig.base / "register.json").write_text(raw)
            self.assertTrue(any("schema" in p for p in self.rig.check()[0]), f"R8.nits {raw}")
        # a reason of spaces and format characters only is empty
        self.rig.folder("w-0001")
        for reason in ("\u200b", "\u00a0", "\u200b \u2060\ufeff"):
            self.rig.register([a_walk(reason=reason)])
            self.assertTrue(any("reason" in p for p in self.rig.check()[0]), f"R8.nits {reason!r}")
        # an unreadable register is a FAIL line, never a traceback
        self.rig.register([])
        os.chmod(self.rig.base / "register.json", 0)
        if os.access(self.rig.base / "register.json", os.R_OK):
            self.skipTest("running as a user who reads mode-0 files")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = wr.main(["--check", "--base", str(self.rig.base)])
        self.assertEqual(code, 1, "R8.nits")
        self.assertRegex(out.getvalue(), r"(?m)^FAIL rehearsals/register\.json cannot be read", "R8.nits")


class RoundsUsage(unittest.TestCase):
    def test_usage_names_round_4_paths(self):
        text = rounds_text()
        doc = text.split('"""', 2)[1]
        usage = [ln.strip() for ln in doc.splitlines() if ln.strip().startswith("python3 ")]
        self.assertEqual(len(usage), 5, "U1.usage")
        want = f"python3 {study.STUDY_REL}/review_kit/rounds.py "
        self.assertEqual([u for u in usage if not u.startswith(want)], [], "U1.usage")
        self.assertNotIn("gap-study-3", text, "U1.usage")
        self.assertEqual(study.STUDY_REL, "evals/gap-study-4", "U1.usage")
        # the CP6 VALIDATE command (plan line 893) is one of the usage lines, verbatim
        self.assertIn("python3 evals/gap-study-4/review_kit/rounds.py --check", usage[-1], "U1.usage")


BOUND = {"R1.unregistered": "TheRegister.test_unregistered_walk_folder_fails",
         "R2.folder": "TheRegister.test_registered_walk_without_its_folder_fails",
         "R3.malformed": "TheRegister.test_malformed_entry_fails",
         "R4.empty": "TheRegister.test_empty_register_says_zero_walks",
         "R5.case": "TheRegisterFold.test_folders_match_by_exact_name",
         "R6.symlink": "TheRegisterFold.test_symlinks_are_not_walk_records",
         "R7.dupkey": "TheRegisterFold.test_duplicate_keys_are_refused",
         "R8.nits": "TheRegisterFold.test_review_nits",
         "U1.usage": "RoundsUsage.test_usage_names_round_4_paths"}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _, _) in mutants().items()}


def run_witnesses():
    import subprocess
    red = 0
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_rehearsals witnesses", [sys.executable, "-B", "-W", "ignore",
                                    str(Path(__file__).resolve())], timeout=300, tag="test_rehearsals")
    for name, (method, clause) in sorted(WITNESSES.items()):
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name],
                             capture_output=True, text=True, timeout=300)
        record = re.findall(r"^test_rehearsals outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr, re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w:.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and method in outcome["failures"] and method not in outcome["errors"] \
            and method not in outcome["skipped"]
        passed = attributed and clean and got.returncode != 0
        other = {k: sorted(t for t in outcome[k] if t != method) for k in outcome} if outcome else {}
        note = "collateral: " + (", ".join(f"{k} {v}" for k, v in other.items() if v) or "none")
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}; {note}", flush=True)
        if not passed:
            print(got.stdout + got.stderr, flush=True)
            return 1
        red += 1
    print(f"test_rehearsals witnesses: {red}/{len(WITNESSES)} red; registry {len(WITNESSES)}", flush=True)
    return 0


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses())
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_rehearsals: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_rehearsals outcomes: " + json.dumps({"failures": ids(result.failures),
                                                     "errors": ids(result.errors),
                                                     "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
