#!/usr/bin/env python3
"""The OD57 agreement corpus through the harness twin (lane vendor-b24, glitch-26's rulings B24-2).

tests/fixtures/od57-agreement/cases.json (built by corpus.py beside it) holds one synthetic record set per read shape
and the verdict, line by line, that both scanners must give it; the aegis door runs a byte copy of the same JSON in its
own lane. Here every case runs through box/scan_record.scan with its arm's read shapes (the drive's own: the adapters'
READ_SHAPES, which are box/od57_shapes's) and a fake rules scanner that flags generic-api-key on every line holding the
ruled line's first 40 characters, and on every line holding a planted second key (the probe's witness).

RED ALONE: each refusal witness of the B24 rules has one guard that refuses it; RED_ALONE names that guard as an edit to
one function of box/od57_rule, and with only that edit made the case's refused lines must be admitted (so the witness
is not hollow, and no other guard holds it).
"""

from __future__ import annotations

import base64
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

sys.dont_write_bytecode = True
STUDY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, STUDY)

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "od57_corpus", os.path.join(STUDY, "tests", "fixtures", "od57-agreement", "corpus.py"))
od57_corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(od57_corpus)
from box import scan_record as sr  # noqa: E402
import gemini_adapter  # noqa: E402
import codex_adapter  # noqa: E402

ENV_DOC = os.path.join(os.path.dirname(STUDY), "..", "gars", "_references", "environment.md")

def second_key() -> str:
    """Round 3 (glitch-26's R3-4): a second key that a real gitleaks 8.30 flags as generic-api-key, built here at run
    time from a fixed phrase (never a real key; test_the_second_key_is_a_real_finding proves the flag)."""
    v = re.sub("[^A-Za-z0-9]", "", base64.b64encode(hashlib.sha256(b"vendor-b24 planted second key, round 3")
                                                     .digest()).decode())[:32]
    return "api_key = " + v


SECOND = second_key()
SECRETS = [("token", "FAKEVALUE-0123456789abcdef-PLANTED"), ("key", "FAKEKEY-fedcba9876543210-PLANTED-TOO")]
RULE = "generic-api-key"


def _line() -> str:
    with open(ENV_DOC, "rb") as fh:
        return fh.read().split(b"\n")[174].decode()


def _fill(node, text):
    if isinstance(node, str):
        return node.replace(od57_corpus.PLACEHOLDER, text).replace(od57_corpus.SECOND_PLACEHOLDER, SECOND)
    if isinstance(node, list):
        return [_fill(v, text) for v in node]
    if isinstance(node, dict):
        return {k: _fill(v, text) for k, v in node.items()}
    return node


class Scanner:
    def __init__(self, head):
        self.head = head.encode()

    def __call__(self, paths):
        out = []
        for p in paths:
            with open(p, "rb") as fh:
                for n, line in enumerate(fh.read().split(b"\n"), 1):
                    if self.head in line or SECOND.encode() in line:
                        out.append({"path": p, "line": n, "rule": RULE})
        return out


def shapes(family):
    return {"g": gemini_adapter.READ_SHAPES, "o": codex_adapter.READ_SHAPES, "c": ()}[family]


def real_gitleaks():
    """The pinned gitleaks where it is (athena), else GAP4_GITLEAKS, else gitleaks on PATH; None names the gap."""
    from box import rules_scanner as rs
    for b in (rs.GITLEAKS_PATH, os.environ.get("GAP4_GITLEAKS"), shutil.which("gitleaks")):
        if b and os.path.isfile(b) and os.access(b, os.X_OK):
            return b
    return None


class RealScanner:
    """The rules scanner the drive builds, run directly (rules_scanner.scan_argv, its own empty ignore file): the door
    runs this corpus with a real gitleaks, so the twin must give the same verdicts with one too."""

    def __init__(self, binary, work):
        self.binary, self.work, self.n = binary, work, 0
        self.ignore = os.path.join(work, "no-rulings.gitleaksignore")
        open(self.ignore, "wb").close()

    def __call__(self, paths):
        from box import rules_scanner as rs
        out = []
        for p in paths:
            self.n += 1
            rep = os.path.join(self.work, f"report-{self.n}.json")
            subprocess.run(rs.scan_argv(self.binary, p, rep, self.ignore), cwd=self.work, check=True,
                           capture_output=True, timeout=120)
            with open(rep) as fh:
                out += [{"path": p, "line": f["StartLine"], "rule": f["RuleID"]} for f in json.load(fh) or []]
        return out


def run_case(c, text, tmp, scanner=None):
    p = os.path.join(tmp, f"{c['name']}.jsonl")
    with open(p, "wb") as fh:
        fh.write(b"".join(json.dumps(r, ensure_ascii=False).encode() + b"\n" for r in _fill(c["records"], text)))
    r = sr.scan([(p, c["kind"])], SECRETS, rules_scanner=scanner or Scanner(text[:40]),
                read_shapes=shapes(c["family"]))
    # the verdict is per line: a real gitleaks reports one finding per match, so a line can carry two
    return sorted({x["line"] for x in r["ruled"]}), sorted({x["line"] for x in r["refused"]})


def _mutant(fn_name, *edits):
    """box/od57_rule.<fn_name> rebuilt from its source with each (old, new) edit applied once, as a mock patch."""
    from box import od57_rule
    src = textwrap.dedent(inspect.getsource(getattr(od57_rule, fn_name)))
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"mutant edit {old!r} matches {src.count(old)} times in {fn_name}")
        src = src.replace(old, new)
    ns = dict(vars(od57_rule))
    exec(compile(src, f"{fn_name}_mutant", "exec"), ns)
    return mock.patch.object(od57_rule, fn_name, ns[fn_name])


# case -> (function of box/od57_rule, its one guard's edit): with only that edit, the refused lines are admitted
RED_ALONE = {
    "g-grep-auto-one-outside": ("_grep_window", ('cl = 50 if', 'cl = 51 if')),
    "g-grep-auto-three-outside": ("_grep_window", ('else 15', 'else 16')),
    "g-grep-explicit-outside": ("_grep_window", ('ctx = args.get("context", 0)', 'ctx = args.get("context", 0) + 1')),
    "g-grep-explicit-after-outside": ("_grep_window", ('after = args.get("after", ctx)',
                                                       'after = args.get("after", ctx) + 1')),
    "g-grep-four-matches-no-auto": ("_grep_window", ("1 <= len(matches) <= 3", "1 <= len(matches) <= 4")),
    "g-grep-names-only": ("_grep_args_ok", ('_GREP_ARGS', '_GREP_ARGS + ("names_only",)')),
    "g-grep-other-header": ("_grep_line", ("if not _grep_names_doc(", "if False and not _grep_names_doc(")),
    "g-grep-other-header-context": ("_grep_line", ("if not _grep_names_doc(", "if False and not _grep_names_doc(")),
    "g-grep-forged-block": ("_grep_line", ("if not any(_attests(m, text) for m in docs):",
                                           "if False:")),
    "g-grep-wrong-number": ("_grep_ruled_number", ("return 175", "return 176")),
    "g-grep-display-other-path": ("_abs_doc", ("return isinstance(p, str)", "return True or isinstance(p, str)")),
    "g-grep-dotdot-header": ("_resolves_to_doc", ('if ".." in p.split("/"):', "if False:")),
    "g-grep-pattern-line": ("ruled_text", ("        return None\n    return found", "        pass\n    return found")),
    "g-grep-path-key": ("_grep_args_ok", ('_GREP_ARGS', '_GREP_ARGS + ("path",)')),
    "t1-gemini-write-then-read": ("ruled_text", ("if writes is not None and writes <= line:", "if False:")),
    "t1-gemini-replace-then-grep": ("ruled_text", ("if writes is not None and writes <= line:", "if False:")),
    "t1-claude-edit-then-read": ("ruled_text", ("if writes is not None and writes <= line:", "if False:")),
    "t1-codex-file-change-then-cat": ("ruled_text", ("if writes is not None and writes <= line:", "if False:")),
    "t2-h-several": ("_grep_spec", ("if len(ops) != 1:", "if len(ops) < 1:")),
    "t2-other-label": ("_labelled_line", ("if not _resolves_to_doc(label, spec[\"cwd\"]):", "if False:")),
    "t2-label-wrong-number": ("_labelled_line", ('number = "175"', 'number = "176"')),
    "t2-label-outside-run-tree": ("_resolves_to_doc", ("return _DOC_ABS.fullmatch(n) is not None",
                                                       "return n.endswith('/' + _RULED_GIT_PATH)")),
    "t2-label-flag": ("_grep_parse", ('if t.startswith("--"):', 'if t.startswith("--label="):\n            i += 1\n'
                                                                '            continue\n        if t.startswith("--"):')),
    "t2-unlabelled-other-only": ("_grep_spec", ("if not _resolves_to_doc(ops[0], cwd):", "if False:")),
    "t2-cat-two": ("_cat_spec", ("if len(ops) != 1", "if len(ops) < 1")),
    "t2-then-cat-other": ("_filter_ok", ("return not rest", "return True")),
    "t2-filter-with-file": ("_filter_ok", ("return not rest", "return True")),
    "t2-codex-c-flag": None,          # a shapes datum (the stream's flags), not a function: test_the_c_flag_is_data
    "c-read-other": ("_claude_tool", ('return "read" if _resolves_to_doc(', 'return "read" if True or _resolves_to_doc(')),
    "c-grep-dir": ("_claude_tool", ('return "grep" if _resolves_to_doc(', 'return "grep" if True or _resolves_to_doc(')),
    "c-grep-other-file": ("_claude_tool", ('return "grep" if _resolves_to_doc(',
                                           'return "grep" if True or _resolves_to_doc(')),
    # round 3 (R3-1 to R3-3)
    "c-read-dotdot": ("_claude_tool", ('return "read" if _resolves_to_doc(', 'return "read" if True or _resolves_to_doc(')),
    "c-read-lookalike-tmp": ("_claude_tool", ('return "read" if _resolves_to_doc(',
                                              'return "read" if True or _resolves_to_doc(')),
    "c-read-relative-lookalike": ("_claude_tool", ('return "read" if _resolves_to_doc(',
                                                   'return "read" if True or _resolves_to_doc(')),
    "c-grep-dotdot": ("_claude_tool", ('return "grep" if _resolves_to_doc(', 'return "grep" if True or _resolves_to_doc(')),
    "g-read-file-dotdot": ("_reads_doc", ("return dict(tool) if _resolves_to_doc(arg) else None", "return dict(tool)")),
    "g-grep-lookalike-tree": ("_resolves_to_doc", ("return _DOC_ABS.fullmatch(n) is not None",
                                                   "return n.endswith('/' + _RULED_GIT_PATH)")),
    "t2-rgrep-newline-filename": ("_grep_spec", ("if labelled and recursive:", "if False:")),
    "t2-rgrep-newline-filename-gemini": ("_grep_spec", ("if labelled and recursive:", "if False:")),
    "t2-glob-operand": ("_grep_spec", ('if labelled and any(c in op for op in ops for c in "*?["):', "if False:")),
    "t1-write-dot-segment": ("_may_name_doc", ("n = posixpath.normpath(p)", "n = p")),
    "t1-claude-write-doubleslash": ("_may_name_doc", ("n = posixpath.normpath(p)", "n = p")),
}


class Corpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _line()
        with open(od57_corpus.JSON_PATH, "rb") as fh:
            cls.raw = fh.read()
        cls.cases = json.loads(cls.raw)["cases"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_the_json_is_the_builder_s_output(self):
        self.assertEqual(self.raw, od57_corpus.dump(od57_corpus.build()))
        self.assertNotIn(self.text[:40].encode(), self.raw)          # the ruled line never sits in the corpus
        self.assertEqual(hashlib.sha256(self.text.encode()).hexdigest(), sr.RULED_LINES[0]["sha256"])

    def test_every_flagged_line_has_one_verdict(self):
        for c in self.cases:
            with self.subTest(c["name"]):
                flagged = [i for i, r in enumerate(c["records"], 1)
                           if od57_corpus.PLACEHOLDER in json.dumps(r, ensure_ascii=False)
                           or od57_corpus.SECOND_PLACEHOLDER in json.dumps(r)]
                self.assertEqual(sorted(c["admit"] + c["refuse"]), flagged)

    def test_every_case_gets_its_verdict(self):
        for c in self.cases:
            with self.subTest(c["name"]):
                self.assertEqual(run_case(c, self.text, self.tmp.name), (c["admit"], c["refuse"]), c["why"])

    def test_the_corpus_under_real_gitleaks(self):
        """R3-4: every case gets its verdict with a real gitleaks too (a missing binary is a named failure)."""
        binary = real_gitleaks()
        self.assertIsNotNone(binary, "no gitleaks binary: set GAP4_GITLEAKS (named failure, never a skip)")
        for c in self.cases:
            with self.subTest(c["name"]):
                work = tempfile.mkdtemp(dir=self.tmp.name)
                self.assertEqual(run_case(c, self.text, self.tmp.name, RealScanner(binary, work)),
                                 (c["admit"], c["refuse"]), c["why"])

    def test_the_second_key_is_a_real_finding(self):
        """R3-4: the planted second key is a finding of a real gitleaks's generic-api-key rule, alone on a line."""
        binary = real_gitleaks()
        self.assertIsNotNone(binary, "no gitleaks binary: set GAP4_GITLEAKS (named failure, never a skip)")
        work = tempfile.mkdtemp(dir=self.tmp.name)
        p = os.path.join(work, "second.jsonl")
        with open(p, "w") as fh:
            fh.write(json.dumps({"output": f"L176: {SECOND}"}) + "\n")
        self.assertEqual([(f["line"], f["rule"]) for f in RealScanner(binary, work)([p])], [(1, RULE)])

    def test_the_twin_runs_the_shared_rule(self):
        from box import od57_rule, od57_shapes
        self.assertIs(sr.RULED_LINES, od57_rule.RULED_LINES)
        self.assertIs(gemini_adapter.READ_SHAPES, od57_shapes.GEMINI)
        self.assertIs(codex_adapter.READ_SHAPES, od57_shapes.CODEX)

    def test_each_witness_goes_red_alone(self):
        names = {c["name"]: c for c in self.cases}
        for name, spec in RED_ALONE.items():
            c = names[name]
            self.assertTrue(c["refuse"] and not c["admit"], name)
            if spec is None:
                continue
            fn, edit = spec
            with self.subTest(name), _mutant(fn, edit):
                self.assertEqual(run_case(c, self.text, self.tmp.name), (c["refuse"], []), f"{name} under {fn}")

    def test_the_c_flag_is_data(self):
        c = {x["name"]: x for x in self.cases}["t2-codex-c-flag"]
        from box import od57_shapes
        wrap = od57_shapes.CODEX[0]["tools"]["shell"]
        self.assertEqual(wrap["flags"], ("-lc",))
        with mock.patch.dict(wrap, {"flags": ("-lc", "-c")}):
            self.assertEqual(run_case(c, self.text, self.tmp.name), (c["refuse"], []))

    def test_the_second_key_is_the_probe_s(self):
        c = {x["name"]: x for x in self.cases}["g-grep-second-key"]
        blind = lambda paths: [f for f in Scanner(self.text[:40])(paths)            # noqa: E731
                               if not os.path.basename(f["path"]).startswith(c["name"])]
        p = os.path.join(self.tmp.name, f"{c['name']}.jsonl")
        with open(p, "wb") as fh:
            fh.write(b"".join(json.dumps(r, ensure_ascii=False).encode() + b"\n"
                              for r in _fill(c["records"], self.text)))
        calls = []

        def scanner(paths):
            calls.append(paths)
            return Scanner(self.text[:40])(paths) if len(calls) == 1 else blind(paths)
        r = sr.scan([(p, "session")], SECRETS, rules_scanner=scanner, read_shapes=shapes("g"))
        self.assertEqual(sorted(x["line"] for x in r["ruled"]), c["refuse"])          # a blind probe admits it


if __name__ == "__main__":
    unittest.main(verbosity=2)
