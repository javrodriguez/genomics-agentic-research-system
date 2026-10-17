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
FAKE_ENTRY = hb.Entry(home_paths=(".fake2/state/**",), run_tree_paths=(".fake2-run/**",), grounds=("test-only",),
                      not_excluded=())
TABLE = dict(hb.TABLE, **{FAKE: FAKE_ENTRY})
# W2A1-7: what the grounds and the docstring say about an inherited CLAUDE_CONFIG_DIR, which round 3's lines leave open.
CONFIG_DIR_OPEN = "whether an inherited one passes through is open (CP2)"


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
    # W2A1-6: round 3's files ground no run-tree bookkeeping for Claude Code; CP2 measures one (open question 2)
    if e.run_tree_paths != ():
        out.append(f"run_tree_paths {e.run_tree_paths}: round 3's files ground none for this harness")
    return out


def config_dir_claim_problems(doc: str, grounds: tuple) -> list:
    """W2A1-7: drive.py:170 sets no CLAUDE_CONFIG_DIR (bound by isolation_env below); whether an inherited one passes
    through was not read, so neither the docstring nor the grounds may say the home-relative default holds."""
    out = []
    for what, text in (("docstring", " ".join(doc.split())), ("grounds", " ".join(" ".join(grounds).split()))):
        if "default holds" in text:
            out.append(f"the {what} says the home-relative default holds")
        if CONFIG_DIR_OPEN not in text:
            out.append(f"the {what} does not leave an inherited CLAUDE_CONFIG_DIR open")
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
        e = dataclasses.replace(hb.TABLE[ADAPTER_NAME], run_tree_paths=(".tmp/**",))
        self.assertNotEqual(grounding_problems({ADAPTER_NAME: e}), [])

    def test_an_inherited_config_dir_is_left_open(self):
        self.assertEqual(config_dir_claim_problems(hb.__doc__, hb.TABLE[ADAPTER_NAME].grounds), [])
        # the round 1 wording, as a mutant, goes red
        old_doc = ("Round 3's session environment (drive.py:158-186) sets no CLAUDE_CONFIG_DIR, so the home-relative "
                   "default holds.")
        old_grounds = ("evals/gap-study-4/drive.py:158-186: the session's environment sets no CLAUDE_CONFIG_DIR",)
        self.assertNotEqual(config_dir_claim_problems(old_doc, old_grounds), [])

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
            "run tree absolute": {ADAPTER_NAME: dataclasses.replace(base, run_tree_paths=("/tmp/**",))},
            "run tree everything": {ADAPTER_NAME: dataclasses.replace(base, run_tree_paths=("**",))},
            "run tree not a tuple": {ADAPTER_NAME: dataclasses.replace(base, run_tree_paths=[".tmp/**"])},
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

    def seam_problems(self, excluded, run_tree_excluded) -> list:
        out = []
        if not excluded(FAKE, ".fake2/state/turns.log", TABLE):
            out.append("fake-second's own bookkeeping is not excluded under it")
        if not excluded(hb.CLAUDE_CODE, ".claude/projects/-run/a.jsonl", TABLE):
            out.append("Claude Code's session file is not excluded under it")
        if excluded(FAKE, ".claude/projects/-run/a.jsonl", TABLE):
            out.append("under fake-second, Claude Code's folder is excluded")
        if excluded(hb.CLAUDE_CODE, ".fake2/state/turns.log", TABLE):
            out.append("under claude-code, fake-second's folder is excluded")
        # W2A1-6: the run-tree list is per harness too
        if not run_tree_excluded(FAKE, ".fake2-run/turns.cache", TABLE):
            out.append("fake-second's own run-tree bookkeeping is not excluded under it")
        if run_tree_excluded(hb.CLAUDE_CODE, ".fake2-run/turns.cache", TABLE):
            out.append("under claude-code, fake-second's run-tree folder is excluded")
        return out

    def test_each_harness_excludes_its_own_paths_only(self):
        self.assertEqual(self.seam_problems(hb.excluded, hb.run_tree_excluded), [])

    def test_mutant_one_merged_list_goes_red(self):
        def merged(name, path, table=None):
            hb.entry(name, table)
            return any(hb.matches(p, path) for e in (table or hb.TABLE).values() for p in e.home_paths)

        def merged_run_tree(name, path, table=None):
            hb.entry(name, table)
            return any(hb.matches(p, path) for e in (table or hb.TABLE).values() for p in e.run_tree_paths)
        self.assertNotEqual(self.seam_problems(merged, hb.run_tree_excluded), [])
        self.assertNotEqual(self.seam_problems(hb.excluded, merged_run_tree), [])

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
    hits += [p.split("/")[0] for e in TABLE.values() for p in e.home_paths + e.run_tree_paths
             if p.split("/")[0] in src]
    return sorted(set(hits))



# ---- lane vendor-admission T2 (glitch-b5, 16 Oct 2026): vendor bookkeeping candidates, beside TABLE, never in it ----
CODEX_ADAPTER = os.path.join(HERE, "codex_adapter.py")
NATIVE_SNAPSHOT = os.path.join(HERE, "native_snapshot.py")
RUN_TAKE = os.path.join(HERE, "box", "run_take.py")
CANDIDATE_NAMES = ("codex", "gemini")


def source_line(path: str, n: int) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()[n - 1]


def derived_codex_pattern() -> str:
    """codex_adapter.py:41: the rollout is `$CODEX_HOME/sessions/.../rollout-*.jsonl` (`...`: any folders); and
    box/run_take.py:68, 160-162: CODEX_HOME is the config mount, which is also HOME, so the pattern is home-relative."""
    m = re.fullmatch(r"\s*rollout\s+`\$CODEX_HOME/([^`]+)`, copied out host-side by the driver and handed over by",
                     source_line(CODEX_ADAPTER, 41))
    if not m:
        raise AssertionError("codex_adapter.py:41 is not the rollout line this candidate is grounded in")
    if source_line(RUN_TAKE, 68) != 'CONFIG_MOUNT = "/opt/cfg"':
        raise AssertionError("box/run_take.py:68 is not CONFIG_MOUNT")
    row = " ".join(source_line(RUN_TAKE, n) for n in (160, 161, 162))
    if 'CODEX: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT' not in row or '"CODEX_HOME": CONFIG_MOUNT}' not in row:
        raise AssertionError("box/run_take.py:160-162 no longer sets CODEX_HOME and HOME to the config mount")
    return m.group(1).replace("/.../", "/**/")


def derived_gemini_pattern() -> str:
    """native_snapshot.py:20: under exactly <home>/.gemini/tmp/*/chats; :13: filename = session-<...>.jsonl; :9 and
    box/run_take.py:163-165: <home> is $GEMINI_CLI_HOME, the config mount, which is also HOME."""
    folder = re.fullmatch(r"gemini_session_file reads directory names only, under exactly <home>/(\S+), never a "
                          r"file's content and", source_line(NATIVE_SNAPSHOT, 20))
    name = re.fullmatch(r"\s*filename\s+= (session-)<.*>(\.jsonl),", source_line(NATIVE_SNAPSHOT, 13))
    home = re.fullmatch(r"\s*homedir\(\)\s+= \$GEMINI_CLI_HOME when set", source_line(NATIVE_SNAPSHOT, 9))
    if not (folder and name and home):
        raise AssertionError("native_snapshot.py:9, 13, 20 are not the lines this candidate is grounded in")
    row = " ".join(source_line(RUN_TAKE, n) for n in (163, 164, 165))
    if 'GEMINI: {"PATH": TAKE_PATH, "HOME": CONFIG_MOUNT' not in row or '"GEMINI_CLI_HOME": CONFIG_MOUNT' not in row:
        raise AssertionError("box/run_take.py:163-165 no longer sets GEMINI_CLI_HOME and HOME to the config mount")
    return f"{folder.group(1)}/{name.group(1)}*{name.group(2)}"


def run_tree_tmp_name() -> str:
    """box/run_take.py:93 and 152: TMPDIR, TMP and TEMP point at <run tree>/.tmp."""
    m = re.fullmatch(r'RUN_TREE_TMPDIR = "([^"]+)"', source_line(RUN_TAKE, 93))
    if not m or not source_line(RUN_TAKE, 152).startswith('RUN_TREE_TMP = "<run tree>/' + m.group(1) + '"'):
        raise AssertionError("box/run_take.py:93 and 152 are not the run tree's temporary folder")
    return m.group(1)


# (path, excluded?) under each candidate: its native session file only, nothing else of the home or the run tree.
CANDIDATE_PATHS = {
    "codex": [("sessions/2026/10/14/rollout-2026-10-14T05-00-00-00000000-0000-7000-8000-0000000000c1.jsonl", True),
              ("sessions/2026/10/14/notes.txt", False), ("sessions/2026/10/14/rollout-x.jsonl.zst", False),
              ("auth.json", False), ("config.toml", False), ("history.jsonl", False), ("log/codex-tui.log", False),
              (".tmp/x", False), ("rollout-x.jsonl", False), ("other/sessions/rollout-x.jsonl", False)],
    "gemini": [(".gemini/tmp/abc/chats/session-2026-10-14T05-00-1a2b3c4d.jsonl", True),
               (".gemini/tmp/abc/chats/1a2b3c4d/sub-1.jsonl", False), (".gemini/tmp/abc/logs.json", False),
               (".gemini/settings.json", False), (".gemini/tmp/abc/chats/notes.txt", False),
               (".gemini/tmp/chats/session-x.jsonl", False), (".tmp/x", False), ("session-x.jsonl", False)],
}


def candidate_problems(table: dict) -> list:
    """Each candidate is exactly its derived pattern, its grounds quote what they rest on, its run tree is unmeasured
    (empty), it names .tmp/ as kept in, and it excludes its native session file and nothing else listed."""
    out = []
    derived = {"codex": derived_codex_pattern(), "gemini": derived_gemini_pattern()}
    tmp = run_tree_tmp_name()
    if sorted(table) != sorted(CANDIDATE_NAMES):
        out.append(f"the candidates are {sorted(table)}, not {sorted(CANDIDATE_NAMES)}")
    for name in CANDIDATE_NAMES:
        e = table.get(name)
        if e is None:
            continue
        if e.home_paths != (derived[name],):
            out.append(f"{name}: home_paths {e.home_paths} are not exactly the derived {derived[name]!r}")
        if e.run_tree_paths != ():
            out.append(f"{name}: run_tree_paths {e.run_tree_paths}: unmeasured until a real walk")
        grounds = " ".join(e.grounds)
        for need in ({"codex": ["codex_adapter.py:41", "`$CODEX_HOME/sessions/.../rollout-*.jsonl`",
                                "box/run_take.py:68", '"CODEX_HOME": CONFIG_MOUNT'],
                      "gemini": ["native_snapshot.py:20", "<home>/.gemini/tmp/*/chats", "native_snapshot.py:13",
                                 "native_snapshot.py:16-18", "assumed, not source-shown", "box/run_take.py:68",
                                 '"GEMINI_CLI_HOME": CONFIG_MOUNT']}[name] + ["unmeasured until a real walk"]):
            if need not in grounds:
                out.append(f"{name}: the grounds do not say {need!r}")
        if not any(path == tmp + "/" for path, _ in e.not_excluded):
            out.append(f"{name}: not_excluded does not name {tmp}/ (box/run_take.py:93, 152)")
        for path, want in CANDIDATE_PATHS[name]:
            if any(hb.matches(p, path) for p in e.home_paths) != want:
                out.append(f"{name}: {path} is {'not ' if want else ''}excluded")
    return out


def candidate_conflicts(candidates: dict) -> list:
    """endstate.exclusion_conflicts for every task under each candidate, through check_task's check 8."""
    sys.path.insert(0, os.path.join(HERE, "tasks"))
    try:
        import check_task as ct
    finally:
        sys.path.remove(os.path.join(HERE, "tasks"))
    out = []
    table = dict(hb.TABLE, **candidates)
    for task_id in ct.task_ids():
        bad, task, doc = ct.check_1_schema(task_id)
        if bad:
            out.append(f"{task_id}: {bad}")
            continue
        out += [f"{task_id}: {x}" for x in ct.check_8_exclusions(task, doc, table=table)]
    return out


class VendorCandidates(unittest.TestCase):
    """Lane vendor-admission T2: hb.VENDOR_CANDIDATES holds Codex's and Gemini's bookkeeping candidates, grounded and
    checked, and never promoted: TABLE stays claude-code alone, so production Evidence.load still refuses both."""

    def test_candidates_are_beside_the_table_never_in_it(self):
        self.assertEqual(sorted(hb.VENDOR_CANDIDATES), sorted(CANDIDATE_NAMES))
        self.assertEqual(sorted(hb.TABLE), [ADAPTER_NAME])
        for name in CANDIDATE_NAMES:
            with self.assertRaises(hb.UnknownHarness):
                hb.entry(name)

    def test_production_evidence_still_refuses_a_vendor_take(self):
        from graders import endstate
        for name in CANDIDATE_NAMES:
            take = {"kind": "take", "model": "synthetic-model", "agent": {"harness": name, "version": "0.0.1"},
                    "run_tree": "", "home": None}
            with self.assertRaises(endstate.EvidenceError) as cm:
                endstate.agent_of(take)
            self.assertIn("has no bookkeeping entry", str(cm.exception))

    def test_each_candidate_passes_check_table(self):
        self.assertEqual(hb.check_table(dict(hb.TABLE, **hb.VENDOR_CANDIDATES)), [])
        for name, e in hb.VENDOR_CANDIDATES.items():
            self.assertEqual(hb.check_table({ADAPTER_NAME: hb.TABLE[ADAPTER_NAME], name: e}), [], name)

    def test_each_candidate_is_grounded_in_its_source_lines(self):
        self.assertEqual(derived_codex_pattern(), "sessions/**/rollout-*.jsonl")
        self.assertEqual(derived_gemini_pattern(), ".gemini/tmp/*/chats/session-*.jsonl")
        self.assertEqual(run_tree_tmp_name(), ".tmp")
        self.assertEqual(candidate_problems(hb.VENDOR_CANDIDATES), [])

    def test_a_widened_or_moved_candidate_goes_red(self):
        widened = {"codex": ("sessions/**", "**/rollout-*.jsonl", "sessions/**/*.jsonl", "sessions/**/rollout-*",
                             "*/**/rollout-*.jsonl", "sessions/**/rollout-*.jsonl*"),
                   "gemini": (".gemini/**", ".gemini/tmp/**/session-*.jsonl", ".gemini/tmp/*/chats/*.jsonl",
                              ".gemini/tmp/*/*/session-*.jsonl", ".gemini/tmp/*/chats/**", ".gemini/*/*/chats/session-*")}
        for name, patterns in widened.items():
            for pattern in patterns:
                for home in ((pattern,), (hb.VENDOR_CANDIDATES[name].home_paths[0], pattern)):
                    with self.subTest(name=name, home=home):
                        e = dataclasses.replace(hb.VENDOR_CANDIDATES[name], home_paths=home)
                        self.assertNotEqual(candidate_problems(dict(hb.VENDOR_CANDIDATES, **{name: e})), [])
        for name in CANDIDATE_NAMES:
            base = hb.VENDOR_CANDIDATES[name]
            for what, e in {"a guessed run tree": dataclasses.replace(base, run_tree_paths=(".tmp/**",)),
                            "no grounds": dataclasses.replace(base, grounds=("TEST DATA",)),
                            ".tmp/ dropped": dataclasses.replace(base, not_excluded=())}.items():
                with self.subTest(name=name, what=what):
                    self.assertNotEqual(candidate_problems(dict(hb.VENDOR_CANDIDATES, **{name: e})), [])
        self.assertNotEqual(candidate_problems({"codex": hb.VENDOR_CANDIDATES["codex"]}), [])

    def test_no_task_path_is_hidden_under_a_candidate(self):
        self.assertEqual(candidate_conflicts(hb.VENDOR_CANDIDATES), [])
        e = dataclasses.replace(hb.VENDOR_CANDIDATES["codex"], run_tree_paths=("data/**",))   # mutant: a guess
        self.assertNotEqual(candidate_conflicts(dict(hb.VENDOR_CANDIDATES, codex=e)), [])

    def test_no_grader_types_a_candidate(self):
        graders = os.path.join(HERE, "graders")
        found = {}
        with mock.patch.dict(TABLE, hb.VENDOR_CANDIDATES):
            for name in sorted(os.listdir(graders)):
                if name.endswith(".py"):
                    with open(os.path.join(graders, name), encoding="utf-8") as fh:
                        hits = typed_harness(fh.read())
                    if hits:
                        found[name] = hits
            for typed in ('X = "codex"', 'X = "gemini"', 'X = "sessions/"', 'X = ".gemini/"'):
                self.assertNotEqual(typed_harness(typed), [], typed)   # the scan fires on each known positive
        self.assertEqual(found, {})

if __name__ == "__main__":
    unittest.main(verbosity=2)
