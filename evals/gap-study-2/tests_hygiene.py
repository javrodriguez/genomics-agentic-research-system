#!/usr/bin/env python3
"""Round 1's process lessons, as guards (CP2): loaded by test_harness.py, run by name like any class there.

    python3 evals/gap-study-2/test_harness.py EveryHeadReaderIsListed
    python3 evals/gap-study-2/test_harness.py TheChecklistNamedTestsExist
    python3 evals/gap-study-2/test_harness.py EveryDoneLineMutationIsRegistered
    python3 evals/gap-study-2/test_harness.py EveryNotApplicableIsEvaluated

WHY EACH ONE EXISTS (the plan's structural lessons).

  5. Round 1's checklist named tests that did not exist (Ruling 30). The draft now lists them in
     `checklist_named_tests`, and a name counts as present only when it loads the way the runner loads it.
  6. Round 1's not-applicable reasons were sentences, and they went stale (amendment 4). They are predicates
     over the battery's sandbox now, and the battery fails the day one returns None.
  7. Round 1's `HEAD:gars` readers went red when gars/ moved (Ruling 38). Every place the code names HEAD is
     inventoried in the draft's `head_readers`; a reader that can read another commit takes `--at <sha>`.
 12. A guard closed in a test was dead at its call site (Ruling 26). So every guard here is also driven end to
     end, through the CLI or the loader a real run uses, and each has a call-site mutation in
     mutations_hygiene.py.

No model, no network, stdlib only. Every end-to-end test runs in a throwaway copy of the study.
"""

from __future__ import annotations

import ast
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import types
import unittest
from pathlib import Path

import prereg
import test_harness as th

HERE = th.HERE
REPO = th.REPO


def _env(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k != th.POISON_ENV}
    env.update(extra)
    return env


def _py(script: Path, *args: str, cwd: Path, **env: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                          cwd=str(cwd), env=_env(**env))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    r = _git(root, "commit", "-q", "--allow-empty", "-m", message)
    if r.returncode != 0:
        raise AssertionError(f"the scratch commit failed: {r.stderr.strip()}")
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _edit_json(path: Path, edit) -> None:
    d = json.loads(path.read_text())
    edit(d)
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def _mutations():
    import mutations
    return mutations


# ======================================================================================= lesson 7: HEAD readers
#
# THE PATTERN IS GIT'S REVISION GRAMMAR, NOT A LIST OF SPELLINGS. A reader names HEAD the way git parses a
# revision: `HEAD` or `@`, optionally stepped back with ~ or ^, optionally followed by `:<path>`, optionally at
# the end of a `..` range. The spellings in this tree when this was written were "HEAD", "HEAD:gars",
# f"HEAD:{path}", f"{since}..HEAD" and a shell script's `@`, and each is an instance of the grammar, not an
# entry in it. In Python the unit is a WHOLE string literal, because git takes each argument as one literal
# (an f-string's replacement fields read as `{}`); prose in a docstring or a message is never a whole revision,
# so "HEAD carries gars tree" is not a reader and "HEAD:gars" is. In a shell script the unit is a word outside
# a comment, stripped of the quoting and substitution around it.

HEAD_REVISION = re.compile(r"^(?:\S*?\.\.\.?)?(?:HEAD|@)(?:[~^]\d*)*(?::\S*)?$")
CODE_SUFFIXES = (".py", ".sh")


def python_head_refs(source: str) -> list[tuple[int, str]]:
    tree = ast.parse(source)
    inner = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr):
            text = "".join(v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else "{}"
                           for v in n.values)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in inner:
            text = n.value
        else:
            continue
        if HEAD_REVISION.match(text):
            out.append((n.lineno, text))
    return sorted(out)


def shell_head_refs(source: str) -> list[tuple[int, str]]:
    out = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        code = re.split(r"(?:^|\s)#", line, maxsplit=1)[0]
        for word in code.split():
            # Quoting and substitution brackets come off; `$` stays on, because `$@` is the shell's arguments,
            # not a revision (measured: T's clean_clone_battery.sh passes "$@" to env -i).
            w = word.strip("\"'`();|&<>")
            if HEAD_REVISION.match(w):
                out.append((lineno, w))
    return out


def code_files(root: Path):
    """Every .py and .sh file under `root`; the attempt, walk and results folders hold records, not code."""
    records = set(th.LIVE_STATE)
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = sorted(n for n in dirnames if n != "__pycache__" and (d / n) not in records)
        for name in sorted(filenames):
            if name.endswith(CODE_SUFFIXES):
                yield d / name


def head_refs(root: Path) -> list[dict]:
    found = []
    for f in code_files(root):
        text = f.read_text(errors="replace")
        refs = python_head_refs(text) if f.suffix == ".py" else shell_head_refs(text)
        found += [{"file": f.relative_to(root).as_posix(), "line": ln, "ref": ref} for ln, ref in refs]
    return found


def head_reader_problems(found: list[dict], inventory) -> list[str]:
    readers = inventory.get("readers") if isinstance(inventory, dict) else None
    if not isinstance(readers, list) or not readers:
        return ["the draft's head_readers.readers is missing or empty, so no reader is accounted for"]
    problems: list[str] = []
    listed: collections.Counter = collections.Counter()
    for e in readers:
        if not (isinstance(e, dict) and {"file", "ref", "count", "reads", "at"} <= set(e)
                and isinstance(e["count"], int) and e["count"] > 0):
            problems.append(f"a head_readers entry is not {{file, ref, count > 0, reads, at}}: {e!r}")
            continue
        key = (e["file"], e["ref"])
        if key in listed:
            problems.append(f"{key[0]} {key[1]!r} is listed twice; one entry carries the count")
        listed[key] += e["count"]
    seen = collections.Counter((x["file"], x["ref"]) for x in found)
    for key in sorted(set(seen) | set(listed)):
        if seen[key] > listed[key]:
            lines = [x["line"] for x in found if (x["file"], x["ref"]) == key]
            problems.append(f"{key[0]} names {key[1]!r} {seen[key]} time(s) (lines {lines}) and head_readers "
                            f"lists {listed[key]}: an unlisted HEAD reader")
        elif seen[key] < listed[key]:
            problems.append(f"head_readers lists {key[0]} {key[1]!r} {listed[key]} time(s) and the code names it "
                            f"{seen[key]}: the inventory is stale")
    return problems


class EveryHeadReaderIsListed(unittest.TestCase):
    """Structural lesson 7: every place this study's code names HEAD is in the draft's inventory, and no more."""

    def test_the_grammar_sees_every_spelling_and_no_prose(self):
        src = '\n'.join([
            'a = ["git", "rev-parse", "HEAD"]',
            'b = ("rev-parse", "HEAD:gars")',
            'c = f"HEAD:{path}"',
            'd = f"{since}..HEAD"',
            'e = "HEAD~1"',
            'f = "@"',
            '"""A docstring that reads HEAD:gars. and HEAD"""',
            'g = f"refusing: {at} carries gars tree"',
            'h = "HEAD carries gars tree"',
            'i = "user.email=t@t"',
            'j = "FIRST_STUDY_HEADING"',
        ])
        self.assertEqual([r for _, r in python_head_refs(src)],
                         ["HEAD", "HEAD:gars", "HEAD:{}", "{}..HEAD", "HEAD~1", "@"])
        sh = ('SHA="$(git -C "$CLONE" rev-parse --verify @)"\n# git rev-parse HEAD\necho HEADLINE\n'
              'run_clean() { env -i HOME="$TMP" "$@"; }\n')
        self.assertEqual(shell_head_refs(sh), [(1, "@")])

    def test_every_head_read_in_the_study_is_listed(self):
        found = head_refs(HERE)
        self.assertGreater(len(found), 5, "the scan found almost nothing; that is not a measurement")
        self.assertEqual(head_reader_problems(found, prereg.load().get("head_readers")), [])

    def test_a_reader_the_inventory_does_not_list_is_refused(self):
        found = head_refs(HERE)
        planted = found + [{"file": "takes.py", "line": 999, "ref": "HEAD~1"}]
        got = head_reader_problems(planted, prereg.load().get("head_readers"))
        self.assertTrue(any("takes.py names 'HEAD~1'" in p and "unlisted" in p for p in got), got)
        stale = [x for x in found if x["file"] != "lint_language.py"]
        self.assertTrue(any("stale" in p for p in head_reader_problems(stale, prereg.load().get("head_readers"))))

    def test_the_readers_this_checkpoint_gave_an_at_say_so(self):
        entries = {e["file"]: e for e in prereg.load()["head_readers"]["readers"] if e["at"] == "--at <sha>"}
        for f in ("check_results.py", "drive.py", "lint_language.py"):
            self.assertIn(f, entries, f"{f} is listed without --at")
            self.assertIn('"--at"', (HERE / f).read_text(), f"{f} is listed with --at and has no such option")


class TheHeadReadersTakeAnAt(unittest.TestCase):
    """Each production reader given `--at <sha>`, driven through its CLI on a repository the test builds, where
    HEAD and the named commit differ."""

    def test_check_results_reads_the_gars_tree_at_the_commit_it_is_given(self):
        root, dest = th.study_copy(self, git=True)
        pinned = _commit(root, "nothing moves")
        (root / "gars" / "CLAUDE.md").write_text("the system under test, moved\n")
        _commit(root, "gars moves")
        r = _py(dest / "check_results.py", "--ledger", cwd=root)
        self.assertEqual(r.returncode, 1, r.stdout[-1500:] + r.stderr[-800:])
        self.assertIn("HEAD carries gars tree", r.stdout)
        r = _py(dest / "check_results.py", "--ledger", "--at", pinned, cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-800:])
        self.assertNotIn("carries gars tree", r.stdout)

    def test_lint_language_scans_bodies_up_to_the_commit_it_is_given(self):
        root, dest = th.study_copy(self, git=True)
        since = _commit(root, "the scan starts here")
        (dest / "notes.md").write_text("x\n")
        clean = _commit(root, "take: a clean body")
        (dest / "notes.md").write_text("y\n")
        _commit(root, "take: a robust result")
        r = _py(dest / "lint_language.py", "--commits-since", since, cwd=root)
        self.assertEqual(r.returncode, 1, r.stdout[-1500:])
        r = _py(dest / "lint_language.py", "--commits-since", since, "--at", clean, cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:])
        self.assertIn("clean", r.stdout)

    def test_drive_checks_the_gars_tree_at_the_commit_it_is_given(self):
        """A take row, frozen file and a filled slot, so the driver stops at the slot check right after the tree
        check and never builds a checkout; `claude` is also off the PATH, so no model can be reached."""
        root, dest = th.study_copy(self, git=True)
        shutil.copy2(dest / "prereg-draft.json", dest / "prereg.json")
        rows = [{"task": "scope-read", "half": "positive", "model": "claude-opus-5", "take": 1, "order_index": 0,
                 "fixture_sha": "x", "environment_class": "claude-subscription-headless"}]
        (dest / "takes.json").write_text(json.dumps({"role": "test", "rows": rows}, indent=2) + "\n")
        pinned = _commit(root, "take: row 0")
        (root / "gars" / "CLAUDE.md").write_text("the system under test, moved\n")
        _commit(root, "gars moves")
        (dest / "transcripts" / "scope-read" / "positive" / "claude-opus-5" / "1").mkdir(parents=True)
        argv = ("--task", "scope-read", "--half", "positive", "--row", "0")
        r = _py(dest / "drive.py", *argv, cwd=root, PATH=os.defpath)
        self.assertEqual(r.returncode, 2, r.stdout[-1500:] + r.stderr[-800:])
        self.assertIn("refusing: HEAD carries gars tree", r.stdout)
        r = _py(dest / "drive.py", *argv, "--at", pinned, cwd=root, PATH=os.defpath)
        self.assertEqual(r.returncode, 2, r.stdout[-1500:] + r.stderr[-800:])
        self.assertNotIn("carries gars tree", r.stdout)
        self.assertIn("already holds a graded take", r.stdout)


# ======================================================================================= lesson 5: named tests

def loaded_names(names: list[str], module) -> tuple[list[str], list[str]]:
    """(the names that load through loadTestsFromNames against `module`, one problem per name that does not).

    The runner's own call. Since Python 3.5 a name that does not resolve does NOT raise: it comes back as a
    _FailedTest that errors when run, and the loader records it in `errors`. Counting test cases would count
    it as present, so the loader's errors are read instead.
    """
    present, problems = [], []
    for name in names:
        loader = unittest.TestLoader()
        try:
            suite = loader.loadTestsFromNames([name], module)
        except Exception as exc:
            problems.append(f"{name}: does not load by name ({exc!r})")
            continue
        if loader.errors or suite.countTestCases() == 0:
            problems.append(f"{name}: does not load by name, so a checklist line naming it runs nothing")
            continue
        present.append(name)
    return present, problems


def checklist_problems(pre: dict, module) -> list[str]:
    named = pre.get("checklist_named_tests")
    pending = pre.get("checklist_named_tests_pending")
    problems: list[str] = []
    if not isinstance(named, list) or not named or not all(isinstance(n, str) for n in named):
        problems.append("checklist_named_tests is missing, empty or not a list of class names")
        named = []
    if not isinstance(pending, dict):
        problems.append("checklist_named_tests_pending is not a map of class name to the checkpoint that creates it")
        pending = {}
    for name in named:
        if name in pending:
            problems.append(f"{name}: listed both as present and as pending")
    problems += loaded_names([n for n in named if n not in pending], module)[1]
    for name, spec in pending.items():
        if not (isinstance(spec, dict) and re.fullmatch(r"CP\d+", str(spec.get("checkpoint", "")))):
            problems.append(f"{name}: a pending name carries the checkpoint that creates it (CP<n>), got {spec!r}")
        if loaded_names([name], module)[0]:
            problems.append(f"{name}: listed as pending and it loads now; move it into checklist_named_tests")
    return problems


class TheChecklistNamedTestsExist(unittest.TestCase):
    """Structural lesson 5: every test the checklist names loads by name; a pending name never counts as present."""

    def test_every_named_test_loads_by_name(self):
        pre = prereg.load()
        self.assertEqual(checklist_problems(pre, th), [])
        present, _ = loaded_names(pre["checklist_named_tests"], th)
        for want in ("TwoMinuteRead", "NoRateNoBannedWord"):
            self.assertIn(want, present)

    def test_a_name_that_does_not_resolve_is_not_present(self):
        present, problems = loaded_names(["TwoMinuteRead", "NoSuchClassAnywhere"], th)
        self.assertEqual(present, ["TwoMinuteRead"])
        self.assertTrue(any("NoSuchClassAnywhere" in p for p in problems))
        got = checklist_problems({"checklist_named_tests": ["NoSuchClassAnywhere"],
                                  "checklist_named_tests_pending": {}}, th)
        self.assertTrue(any("NoSuchClassAnywhere" in p for p in got), got)

    def test_a_pending_name_never_counts_as_present(self):
        pre = {"checklist_named_tests": ["TwoMinuteRead"],
               "checklist_named_tests_pending": {"NoSuchClassYet": {"checkpoint": "CP3", "module": "tests_x.py"}}}
        self.assertEqual(checklist_problems(pre, th), [])
        self.assertNotIn("NoSuchClassYet", loaded_names(pre["checklist_named_tests"], th)[0])
        pre["checklist_named_tests"].append("NoSuchClassYet")
        self.assertTrue(any("both as present and as pending" in p for p in checklist_problems(pre, th)))

    def test_a_pending_name_that_exists_must_move_and_needs_its_checkpoint(self):
        got = checklist_problems({"checklist_named_tests": ["NoRateNoBannedWord"],
                                  "checklist_named_tests_pending": {"TwoMinuteRead": {"checkpoint": "CP3"},
                                                                    "NoSuchClassYet": {}}}, th)
        self.assertTrue(any("TwoMinuteRead" in p and "move it" in p for p in got), got)
        self.assertTrue(any("NoSuchClassYet" in p and "checkpoint" in p for p in got), got)


# ======================================================================================= done-line 12

def done_line_problems(pre: dict, muts) -> list[str]:
    mapping = pre.get("done_line_12_mutations")
    pending = pre.get("done_line_12_mutations_pending")
    problems: list[str] = []
    if not isinstance(mapping, dict) or not mapping:
        return ["done_line_12_mutations is missing or empty"]
    if not isinstance(pending, dict):
        problems.append("done_line_12_mutations_pending is not a map of phrase to {name, checkpoint}")
        pending = {}
    registered = collections.Counter(fn.__name__ for _, fn, _ in muts.MUTATIONS)
    listed = {name: predicate for name, predicate in muts.NOT_APPLICABLE}
    for phrase, name in mapping.items():
        if not isinstance(name, str):
            problems.append(f"{phrase!r}: the battery entry is {name!r}, not a name")
        elif registered[name] == 1:
            continue
        elif registered[name] > 1:
            problems.append(f"{phrase!r} -> {name}: registered {registered[name]} times")
        elif name in listed and callable(listed[name]):
            continue
        else:
            problems.append(f"{phrase!r} -> {name}: no battery entry by that name, neither a registered mutation "
                            f"nor a not-applicable entry with a predicate")
    for phrase, spec in pending.items():
        if phrase in mapping:
            problems.append(f"{phrase!r}: mapped and pending at once")
        if not (isinstance(spec, dict) and isinstance(spec.get("name"), str)
                and re.fullmatch(r"CP\d+", str(spec.get("checkpoint", "")))):
            problems.append(f"{phrase!r}: a pending entry is {{name, checkpoint CP<n>}}, got {spec!r}")
            continue
        if registered[spec["name"]] or spec["name"] in listed:
            problems.append(f"{phrase!r} -> {spec['name']}: pending and registered now; move it into "
                            f"done_line_12_mutations")
    return problems


class EveryDoneLineMutationIsRegistered(unittest.TestCase):
    """Done-line 12's map: every phrase names a battery entry that runs, or one whose predicate is evaluated."""

    def test_every_mapped_mutation_is_in_the_battery(self):
        pre = prereg.load()
        self.assertGreaterEqual(len(pre["done_line_12_mutations"]), 12)
        self.assertEqual(done_line_problems(pre, _mutations()), [])

    def test_an_unregistered_or_pending_name_is_refused(self):
        muts = _mutations()
        got = done_line_problems({"done_line_12_mutations": {"a phrase": "m_no_such_mutation"},
                                  "done_line_12_mutations_pending": {
                                      "later": {"name": "m_fourth_graded_take", "checkpoint": "CP3"}}}, muts)
        self.assertTrue(any("m_no_such_mutation" in p for p in got), got)
        self.assertTrue(any("m_fourth_graded_take" in p and "move it" in p for p in got), got)

    def test_a_not_applicable_entry_counts_only_with_a_predicate(self):
        fake = types.SimpleNamespace(MUTATIONS=[], NOT_APPLICABLE=[("an entry", lambda s: "why"),
                                                                   ("a sentence", "why")])
        pre = {"done_line_12_mutations": {"x": "an entry", "y": "a sentence"}, "done_line_12_mutations_pending": {}}
        got = done_line_problems(pre, fake)
        self.assertEqual(len(got), 1, got)
        self.assertIn("a sentence", got[0])


# ======================================================================================= lesson 6: predicates

def _sandbox(test: unittest.TestCase) -> types.SimpleNamespace:
    root, dest = th.study_copy(test)
    return types.SimpleNamespace(root=root, study=dest)


def _set_carried_pin(d):
    for t in d["tasks"]:
        for h in ("positive", "control"):
            fx = (t.get(h) or {}).get("fixture") or {}
            if fx.get("kind") == "first-study":
                fx["tree_sha256_name_invariant"] = "0" * 64


# For each not-applicable entry mutations.py defines: the change to the sandbox that makes its condition false.
# An entry added without one here fails the test, so no predicate is added that nobody has watched return None.
FLIPS = {
    "a local transcript with no server log":
        lambda s: (_edit_json(s.study / "prereg-draft.json", lambda d: d.__setitem__("local_models", [])), s)[1],
    "a copied fixture whose origin no longer resolves":
        lambda s: types.SimpleNamespace(study=s.study, root=s.root / "workspaces" / "repo"),
    "a carried fixture whose tree hash differs from the freeze":
        lambda s: (_edit_json(s.study / "prereg-draft.json", _set_carried_pin), s)[1],
}


class EveryNotApplicableIsEvaluated(unittest.TestCase):
    """Structural lesson 6: a not-applicable reason is what a predicate returns while its condition holds, and
    None the moment it does not; the battery fails on None."""

    def test_every_entry_is_a_predicate_returning_a_reason_on_this_tree(self):
        muts = _mutations()
        self.assertTrue(muts.NOT_APPLICABLE, "no not-applicable entry; nothing to evaluate")
        s = _sandbox(self)
        listed, problems = muts.evaluate_not_applicable(s)
        self.assertEqual(problems, [])
        self.assertEqual([n for n, _ in listed], [n for n, _ in muts.NOT_APPLICABLE])

    def test_each_predicate_returns_none_once_its_condition_no_longer_holds(self):
        muts = _mutations()
        own = [(n, p) for n, p in muts.NOT_APPLICABLE if getattr(p, "__module__", None) == muts.__name__]
        self.assertTrue(own)
        for name, predicate in own:
            self.assertIn(name, FLIPS, f"{name}: no flip in this test, so its predicate was never seen returning None")
            s = _sandbox(self)
            why = predicate(s)
            self.assertIsInstance(why, str, f"{name}: no reason on the unflipped tree")
            self.assertTrue(why.strip())
            self.assertIsNone(predicate(FLIPS[name](s)), f"{name}: still returns its reason with the condition gone")

    def test_the_evaluation_fails_on_none_on_a_raise_and_on_a_non_reason(self):
        muts = _mutations()
        saved = list(muts.NOT_APPLICABLE)
        self.addCleanup(muts.NOT_APPLICABLE.__setitem__, slice(None), saved)

        def boom(s):
            raise OSError("no such file")

        muts.NOT_APPLICABLE[:] = [("applies now", lambda s: None), ("raises", boom), ("says nothing", lambda s: " "),
                                  ("still waiting", lambda s: "the condition holds")]
        listed, problems = muts.evaluate_not_applicable(_sandbox(self))
        self.assertEqual(listed, [("still waiting", "the condition holds")])
        self.assertEqual(len(problems), 3, problems)
        self.assertTrue(any("applies now" in p and "APPLIES" in p for p in problems))


class TheNotApplicableCliEvaluates(unittest.TestCase):
    """`mutations.py --not-applicable`, end to end in a copy of the study, with a topic module planted there: the
    same registry and evaluation the battery runs."""

    PROBE = "mutations_zz_probe.py"

    def plant(self, dest: Path, body: str) -> None:
        (dest / self.PROBE).write_text("from pathlib import Path\n" + body)

    def test_a_reason_while_the_condition_holds_and_a_failure_once_it_does_not(self):
        root, dest = th.study_copy(self)
        self.plant(dest, 'NOT_APPLICABLE = [("a probe entry", lambda s: None if (s.study / "probe-applies").exists() '
                         'else "the probe file is absent")]\n')
        r = _py(dest / "mutations.py", "--not-applicable", cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertRegex(r.stdout, r"n/a\s+a probe entry\s+the probe file is absent")
        (dest / "probe-applies").write_text("")
        r = _py(dest / "mutations.py", "--not-applicable", cwd=root)
        self.assertEqual(r.returncode, 1, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertIn("a probe entry: its predicate returned None, so the mutation APPLIES now", r.stdout)

    def test_a_sentence_where_a_predicate_belongs_is_refused_on_import(self):
        root, dest = th.study_copy(self)
        self.plant(dest, 'NOT_APPLICABLE = [("a probe entry", "a sentence that can go stale")]\n')
        r = _py(dest / "mutations.py", "--not-applicable", cwd=root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is not (name, predicate)", r.stderr)


# ======================================================================================= the loader

class TheTopicTestModulesAreLoaded(unittest.TestCase):
    """The tests_*.py loader, driven through the runner in a copy of the study."""

    def plant(self, dest: Path, name: str, body: str) -> None:
        (dest / name).write_text("import unittest\n" + body)

    def test_a_topic_class_runs_by_name_and_with_the_whole_suite(self):
        present, problems = loaded_names(["EveryHeadReaderIsListed", "TheChecklistNamedTestsExist"], th)
        self.assertEqual(problems, [])
        self.assertIn("EveryHeadReaderIsListed", th.LOADED_TEST_CLASSES)
        self.assertTrue(any(m.startswith("tests_hygiene.py") for m in th.LOADED_TEST_MODULES))
        root, dest = th.study_copy(self)
        self.plant(dest, "tests_zz_probe.py",
                   "class AProbeClassLoadsByName(unittest.TestCase):\n    def test_it(self):\n        pass\n")
        r = _py(dest / "test_harness.py", "AProbeClassLoadsByName", cwd=root)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertRegex(r.stderr, r"Ran 1 test\b")

    def test_a_name_already_defined_fails_the_run(self):
        root, dest = th.study_copy(self)
        self.plant(dest, "tests_zz_probe.py",
                   "class TwoMinuteRead(unittest.TestCase):\n    def test_it(self):\n        pass\n")
        r = _py(dest / "test_harness.py", "TwoMinuteRead", cwd=root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("'TwoMinuteRead' is already defined", r.stderr)

    def test_a_module_that_raises_or_defines_nothing_fails_the_run(self):
        root, dest = th.study_copy(self)
        self.plant(dest, "tests_zz_probe.py", "raise ImportError('a broken topic module')\n")
        r = _py(dest / "test_harness.py", "TwoMinuteRead", cwd=root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tests_zz_probe.py: raised on import", r.stderr)
        self.plant(dest, "tests_zz_probe.py", "X = 1\n")
        r = _py(dest / "test_harness.py", "TwoMinuteRead", cwd=root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tests_zz_probe.py: defines no unittest.TestCase", r.stderr)


class TheHygieneGuardsRunByName(unittest.TestCase):
    """Lesson 12 for the three draft-data guards: each run by name through the runner, in a copy whose draft or
    code carries the defect, goes red naming it; and green in the unedited copy."""

    def run_guard(self, root: Path, dest: Path, name: str) -> subprocess.CompletedProcess:
        return _py(dest / "test_harness.py", name, cwd=root)

    def test_each_guard_is_green_on_the_unedited_copy(self):
        root, dest = th.study_copy(self)
        for name in ("EveryHeadReaderIsListed", "TheChecklistNamedTestsExist", "EveryDoneLineMutationIsRegistered"):
            r = self.run_guard(root, dest, name)
            self.assertEqual(r.returncode, 0, f"{name}: {r.stderr[-2000:]}")

    def test_an_unlisted_reader_in_the_code(self):
        root, dest = th.study_copy(self)
        with (dest / "takes.py").open("a") as fh:
            fh.write('\n_PLANTED = ["git", "rev-parse", "HEAD~2"]\n')
        r = self.run_guard(root, dest, "EveryHeadReaderIsListed")
        self.assertEqual(r.returncode, 1, r.stderr[-2000:])
        self.assertIn("takes.py names 'HEAD~2'", r.stderr)

    def test_a_named_test_that_does_not_exist(self):
        root, dest = th.study_copy(self)
        _edit_json(dest / "prereg-draft.json", lambda d: d["checklist_named_tests"].append("NoSuchClassAnywhere"))
        r = self.run_guard(root, dest, "TheChecklistNamedTestsExist")
        self.assertEqual(r.returncode, 1, r.stderr[-2000:])
        self.assertIn("NoSuchClassAnywhere", r.stderr)

    def test_a_done_line_phrase_naming_no_battery_entry(self):
        root, dest = th.study_copy(self)
        _edit_json(dest / "prereg-draft.json",
                   lambda d: d["done_line_12_mutations"].__setitem__("a planted phrase", "m_no_such_mutation"))
        r = self.run_guard(root, dest, "EveryDoneLineMutationIsRegistered")
        self.assertEqual(r.returncode, 1, r.stderr[-2000:])
        self.assertIn("m_no_such_mutation", r.stderr)


# ======================================================================================= done-line 12: the runner

class ARehearsalIsNeverGradedAsATake(unittest.TestCase):
    """Done-line 12, "a rehearsal counted as a take": run.py end to end, in a frozen copy of the study, on a
    graded-take fixture (a transcript and the driver ledger beside it, where graded takes are read) whose ledger
    records a rehearsal. The same fixture recording a graded take is graded, so the refusal is the only thing
    that differs."""

    TASK, HALF, MODEL = "scope-read", "positive", "claude-opus-5"

    def study_with(self, attempt_kind: str, outcome: str) -> tuple[Path, Path]:
        # ROUND 2, CP3: a repository, because run.py binds a graded take's environment record to the commit that
        # introduced its row and reads that from the ledger's history; with no row committed it binds none.
        root, dest = th.study_copy(self, git=True)
        shutil.copy2(dest / "prereg-draft.json", dest / "prereg.json")
        half = next(t for t in json.loads((dest / "prereg.json").read_text())["tasks"]
                    if t["id"] == self.TASK)[self.HALF]
        sid, project = "00000000-0000-5000-8000-0000000000a1", "run-0a1b2c3d"
        step = half["operator_script"][0]
        recs = [{"type": "user", "sessionId": sid, "message": {"role": "user", "content": step["line"].format(
                    project=project, source=f"data/staging/{project}/src")}},
                {"type": "assistant", "sessionId": sid,
                 "message": {"role": "assistant", "model": self.MODEL, "stop_reason": "end_turn",
                             "content": [{"type": "text", "text": step["marker"]}]}}]
        d = dest / "transcripts" / self.TASK / self.HALF / self.MODEL / "1"
        d.mkdir(parents=True)
        (d / "transcript.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        led = {"kind": "take", "session_id": sid, "task": self.TASK, "half": self.HALF, "model_requested": self.MODEL,
               "outcome": outcome, "first_agent_turn": True,
               "turns": [{"n": step["n"]}], "attempt": {"kind": attempt_kind, "reasons": []},
               "published": {"sha256_after": hashlib.sha256((d / "transcript.jsonl").read_bytes()).hexdigest()}}
        # ROUND 2, CP3: the environment record the driver writes before the first turn, so the only thing that
        # differs between the two fixtures is still the attempt kind the ledger records.
        (d / "driver-ledger.json").write_text(json.dumps(th.bind_environment_record(d, led)))
        return root, dest

    def test_the_same_fixture_recording_a_graded_take_is_graded(self):
        root, dest = self.study_with("graded", "complete")
        r = _py(dest / "run.py", "--task", self.TASK, cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-1500:])
        res = json.loads((dest / "results" / f"{self.TASK}.json").read_text())
        self.assertEqual(len(res["cells"][self.MODEL][self.HALF]["labels"]), 1)

    def test_a_rehearsal_where_graded_takes_are_read_is_refused(self):
        root, dest = self.study_with("rehearsal", "REHEARSAL — the take checker refused it: [operator-lines]")
        r = _py(dest / "run.py", "--task", self.TASK, cwd=root)
        self.assertNotEqual(r.returncode, 0, r.stdout[-1500:])
        self.assertIn("holds an attempt that is not a graded take", r.stderr)
        self.assertFalse((dest / "results" / f"{self.TASK}.json").exists(), "a rehearsal was graded into results")
