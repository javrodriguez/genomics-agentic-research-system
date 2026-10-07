#!/usr/bin/env python3
"""harness_bookkeeping.py: one entry per harness, grounded in round 3's files, refusing every unknown name.

The `claude-code` entry is re-derived here from the two lines of the identical copy `drive.py` that say where
Claude Code writes its session file, and checked against round 3's pre-registration key
`run_location.excluded_from_the_run_tree` (read alone, at round 3's done commit). The second harness is a test-only
`fake-second` entry with its own made-up home folder. Every check is also run against an in-memory mutant and must
go red.
"""

from __future__ import annotations

import ast
import dataclasses
import fnmatch
import json
import os
import re
import subprocess
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import harness_bookkeeping as hb  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
DRIVE = os.path.join(HERE, "drive.py")
# Round 3's done commit (copy_manifest.SOURCE_COMMIT), where its pre-registration is read.
ROUND3 = "e2979b3143081824aadea73523ec41af30c1ddb1"
# The Claude Code adapter's name, typed once here as the thing the table is checked against (interface 8).
ADAPTER_NAME = "claude-code"

FAKE = "fake-second"
FAKE_ENTRY = hb.Entry(home_paths=(".fake2/state/**",), grounds=("test-only",), not_excluded=())
TABLE = dict(hb.TABLE, **{FAKE: FAKE_ENTRY})


def drive_line(n: int) -> str:
    with open(DRIVE, encoding="utf-8") as fh:
        return fh.read().splitlines()[n - 1]


def derived_session_pattern() -> str:
    """drive.py:241-242: base = (CLAUDE_CONFIG_DIR or ~/.claude) / "projects"; glob(f"*/{session_id}.jsonl"). With
    CLAUDE_CONFIG_DIR unset, home-relative: .claude/projects/*/<id>.jsonl, the id any name."""
    base, glob = drive_line(241), drive_line(242)
    m1 = re.fullmatch(r'\s*base = Path\(os\.environ\.get\("CLAUDE_CONFIG_DIR"\) or \(Path\.home\(\) / "([^"]+)"\)\) / "([^"]+)"',
                      base)
    m2 = re.fullmatch(r'\s*hits = sorted\(base\.glob\(f"([^"]+)/\{session_id\}\.jsonl"\)\)', glob)
    if not (m1 and m2):
        raise AssertionError("drive.py:241-242 is not the session_file glob this entry is grounded in")
    return f"{m1.group(1)}/{m1.group(2)}/{m2.group(1)}/*.jsonl"


def isolation_env() -> dict:
    line = drive_line(170)
    assert line.startswith("ISOLATION_ENV = "), line
    return ast.literal_eval(line.split("=", 1)[1].strip())


def round3_excluded_from_run_tree() -> list:
    """Round 3's pre-registration key run_location.excluded_from_the_run_tree, that key alone."""
    shown = subprocess.run(["git", "-C", REPO, "show", f"{ROUND3}:evals/gap-study-3/prereg.json"],
                           capture_output=True, check=True)
    return [e["path"] for e in json.loads(shown.stdout)["run_location"]["excluded_from_the_run_tree"]]


def grounding_problems(table: dict) -> list:
    out = []
    e = table.get(ADAPTER_NAME)
    if e is None:
        return [f"no {ADAPTER_NAME} entry"]
    if e.home_paths != (derived_session_pattern(),):
        out.append(f"home_paths {e.home_paths} are not exactly the session file drive.py:241-242 names")
    env = isolation_env()
    if "CLAUDE_CONFIG_DIR" in env:
        out.append("drive.py:170 sets CLAUDE_CONFIG_DIR: the home-relative default no longer holds")
    # kept in: the run tree's own folders, round 3's run-tree exclusions, the disabled auto-memory folder
    kept = [".tmp/x", "data/staging/x"] + [p + "/x" for p in round3_excluded_from_run_tree()] + \
           [p for p in round3_excluded_from_run_tree()] + [".claude/projects/-x/memory/MEMORY.md"]
    for p in kept:
        if any(hb.matches(pat, p) for pat in e.home_paths):
            out.append(f"{p} is excluded, and round 3's files ground no such exclusion")
    return out


def refusal_problems(entry_fn) -> list:
    out = []
    for name in (None, "", "codex-cli", FAKE, "Claude-Code", 0):
        try:
            entry_fn(name)
            out.append(f"{name!r} was given an entry")
        except hb.UnknownHarness:
            pass
    return out


class TheTable(unittest.TestCase):

    def test_one_real_entry_named_as_the_adapter(self):
        self.assertEqual(hb.CLAUDE_CODE, ADAPTER_NAME)
        self.assertEqual(sorted(hb.TABLE), [ADAPTER_NAME])
        self.assertEqual(hb.check_table(), [])

    def test_grounded_in_round3_files(self):
        self.assertEqual(derived_session_pattern(), ".claude/projects/*/*.jsonl")
        self.assertEqual(isolation_env(), {"ENABLE_CLAUDEAI_MCP_SERVERS": "false", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})
        self.assertEqual(grounding_problems(hb.TABLE), [])

    def test_grounding_check_can_fail(self):
        for extra in (".claude/**", ".tmp/**", "evals/**", ".claude/projects/**"):
            e = dataclasses.replace(hb.TABLE[ADAPTER_NAME], home_paths=(hb.TABLE[ADAPTER_NAME].home_paths[0], extra))
            with self.subTest(extra=extra):
                self.assertNotEqual(grounding_problems({ADAPTER_NAME: e}), [])
        e = dataclasses.replace(hb.TABLE[ADAPTER_NAME], home_paths=(".claude/**",))
        self.assertNotEqual(grounding_problems({ADAPTER_NAME: e}), [])
        self.assertNotEqual(grounding_problems({}), [])

    def test_round3_run_tree_exclusions_are_read(self):
        paths = round3_excluded_from_run_tree()
        self.assertIn("evals", paths)
        self.assertTrue(all(isinstance(p, str) and p for p in paths))

    def test_check_table_can_fail(self):
        base = hb.TABLE[ADAPTER_NAME]
        bad = {
            "empty paths": {ADAPTER_NAME: dataclasses.replace(base, home_paths=())},
            "absolute": {ADAPTER_NAME: dataclasses.replace(base, home_paths=("/root/.claude/**",))},
            "dotdot": {ADAPTER_NAME: dataclasses.replace(base, home_paths=("../run/**",))},
            "everything": {ADAPTER_NAME: dataclasses.replace(base, home_paths=("**",))},
            "no grounds": {ADAPTER_NAME: dataclasses.replace(base, grounds=())},
            "bad not_excluded": {ADAPTER_NAME: dataclasses.replace(base, not_excluded=(("x",),))},
            "no claude-code": {FAKE: FAKE_ENTRY},
            "not an entry": {ADAPTER_NAME: {"home_paths": ("x",)}},
            "empty": {},
        }
        for what, table in bad.items():
            with self.subTest(what=what):
                self.assertNotEqual(hb.check_table(table), [])
        self.assertEqual(hb.check_table(TABLE), [])

    def test_cli_check(self):
        out = subprocess.run([sys.executable, "-B", os.path.join(HERE, "harness_bookkeeping.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        with mock.patch.object(hb, "TABLE", {}):
            self.assertEqual(hb.main(["--check"]), 1)


class Refusal(unittest.TestCase):

    def test_unknown_names_are_refused_never_defaulted(self):
        self.assertEqual(refusal_problems(hb.entry), [])
        self.assertIs(hb.entry(FAKE, TABLE), FAKE_ENTRY)

    def test_refusal_check_can_fail(self):
        def defaulting(name, table=None):   # mutant: an unknown name falls back to Claude Code's entry
            t = hb.TABLE if table is None else table
            return t.get(name, t[hb.CLAUDE_CODE])
        self.assertNotEqual(refusal_problems(defaulting), [])
        with mock.patch.object(hb, "entry", defaulting):
            self.assertTrue(hb.excluded("codex-cli", ".claude/projects/a/b.jsonl"))


class Matching(unittest.TestCase):

    CASES = [
        (".claude/projects/*/*.jsonl", ".claude/projects/-run/abc.jsonl", True),
        (".claude/projects/*/*.jsonl", ".claude/projects/abc.jsonl", False),
        (".claude/projects/*/*.jsonl", ".claude/projects/a/b/c.jsonl", False),
        (".claude/projects/*/*.jsonl", ".claude/projects/a/memory/MEMORY.md", False),
        ("**/__pycache__/**", "gars/_system/__pycache__/x.pyc", True),
        ("**/__pycache__/**", "__pycache__/x.pyc", True),
        ("**/__pycache__/**", "gars/__pycache__x/y", False),
        (".fake2/state/**", ".fake2/state/a/b", True),
        (".fake2/state/**", ".fake2/statex/a", False),
    ]

    def problems(self, match) -> list:
        return [c for c in self.CASES if match(c[0], c[1]) != c[2]]

    def test_segments(self):
        self.assertEqual(self.problems(hb.matches), [])

    def test_segment_check_can_fail(self):
        self.assertNotEqual(self.problems(fnmatch.fnmatchcase), [])   # mutant: `*` crosses `/`


class Seam(unittest.TestCase):

    def seam_problems(self, excluded) -> list:
        out = []
        if not excluded(FAKE, ".fake2/state/turns.log", TABLE):
            out.append("fake-second's own bookkeeping is not excluded under it")
        if not excluded(hb.CLAUDE_CODE, ".claude/projects/-run/a.jsonl", TABLE):
            out.append("Claude Code's session file is not excluded under it")
        if excluded(FAKE, ".claude/projects/-run/a.jsonl", TABLE):
            out.append("under fake-second, Claude Code's folder is excluded")
        if excluded(hb.CLAUDE_CODE, ".fake2/state/turns.log", TABLE):
            out.append("under claude-code, fake-second's folder is excluded")
        return out

    def test_each_harness_excludes_its_own_paths_only(self):
        self.assertEqual(self.seam_problems(hb.excluded), [])

    def test_mutant_one_merged_list_goes_red(self):
        def merged(name, path, table=None):
            hb.entry(name, table)
            return any(hb.matches(p, path) for e in (table or hb.TABLE).values() for p in e.home_paths)
        self.assertNotEqual(self.seam_problems(merged), [])

    def test_no_grader_types_a_harness(self):
        graders = os.path.join(HERE, "graders")
        found = {}
        for name in sorted(os.listdir(graders)):
            if name.endswith(".py"):
                with open(os.path.join(graders, name), encoding="utf-8") as fh:
                    hits = typed_harness(fh.read())
                if hits:
                    found[name] = hits
        self.assertEqual(found, {})
        self.assertNotEqual(typed_harness('X = "' + ADAPTER_NAME + '"'), [])   # the scan fires on a known positive


def typed_harness(src: str) -> list:
    """Every harness name or home folder of the table (test entry included) typed in `src`."""
    hits = [n for n in TABLE if n in src]
    hits += [p.split("/")[0] for e in TABLE.values() for p in e.home_paths if p.split("/")[0] in src]
    return sorted(set(hits))


if __name__ == "__main__":
    unittest.main(verbosity=2)
