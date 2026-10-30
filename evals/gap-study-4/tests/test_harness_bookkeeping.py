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
        # B21-2 (glitch-26, lane vendor-b21): codex and gemini are promoted beside claude-code; this was [ADAPTER_NAME]
        self.assertEqual(hb.CLAUDE_CODE, ADAPTER_NAME)
        self.assertEqual(sorted(hb.TABLE), sorted((ADAPTER_NAME,) + CANDIDATE_NAMES))
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
    """Every harness name or home folder of the table (test entry included) typed in `src`. A folder spelled with a
    leading dot is not a hit where it reads as an attribute (an identifier, `)` or `]` right before it): R4-4's
    `.home/**` is otherwise found in endstate's `self.home` and `take.home`, which type no folder."""
    hits = [n for n in TABLE if n in src]
    for folder in {p.split("/")[0] for e in TABLE.values() for p in e.home_paths + e.run_tree_paths}:
        if folder.startswith("."):
            if re.search(r"(?<![A-Za-z0-9_)\]])" + re.escape(folder), src):
                hits.append(folder)
        elif folder in src:
            hits.append(folder)
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
    """codex_adapter.py:44: the rollout is `$CODEX_HOME/sessions/.../rollout-*.jsonl` (`...`: any folders); and
    box/run_take.py:68, 169-171: CODEX_HOME is the config mount (HOME is the run tree's .home since R-H5), so the
    pattern is relative to the config mount."""
    m = re.fullmatch(r"\s*rollout\s+`\$CODEX_HOME/([^`]+)`, copied out host-side by the driver and handed over by",
                     source_line(CODEX_ADAPTER, 44))
    if not m:
        raise AssertionError("codex_adapter.py:44 is not the rollout line this candidate is grounded in")
    if source_line(RUN_TAKE, 68) != 'CONFIG_MOUNT = "/opt/cfg"':
        raise AssertionError("box/run_take.py:68 is not CONFIG_MOUNT")
    row = " ".join(source_line(RUN_TAKE, n) for n in (169, 170, 171))
    if 'CODEX: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME' not in row or '"CODEX_HOME": CONFIG_MOUNT}' not in row:
        raise AssertionError("box/run_take.py:169-171 no longer sets CODEX_HOME to the config mount and HOME to the "
                             "run tree's home")
    return m.group(1).replace("/.../", "/**/")


def derived_gemini_pattern() -> str:
    """native_snapshot.py:20: under exactly <home>/.gemini/tmp/*/chats; :13: filename = session-<...>.jsonl; :9 and
    box/run_take.py:172-174: <home> is $GEMINI_CLI_HOME, the config mount (HOME is the run tree's .home since R-H5)."""
    folder = re.fullmatch(r"gemini_session_file reads directory names only, under exactly <home>/(\S+), never a "
                          r"file's content and", source_line(NATIVE_SNAPSHOT, 20))
    name = re.fullmatch(r"\s*filename\s+= (session-)<.*>(\.jsonl),", source_line(NATIVE_SNAPSHOT, 13))
    home = re.fullmatch(r"\s*homedir\(\)\s+= \$GEMINI_CLI_HOME when set", source_line(NATIVE_SNAPSHOT, 9))
    if not (folder and name and home):
        raise AssertionError("native_snapshot.py:9, 13, 20 are not the lines this candidate is grounded in")
    row = " ".join(source_line(RUN_TAKE, n) for n in (172, 173, 174))
    if 'GEMINI: {"PATH": TAKE_PATH, "HOME": RUN_TREE_HOME' not in row or '"GEMINI_CLI_HOME": CONFIG_MOUNT' not in row:
        raise AssertionError("box/run_take.py:172-174 no longer sets GEMINI_CLI_HOME to the config mount and HOME to "
                             "the run tree's home")
    return f"{folder.group(1)}/{name.group(1)}*{name.group(2)}"


def run_tree_tmp_name() -> str:
    """box/run_take.py:93 and 153: TMPDIR, TMP and TEMP point at <run tree>/.tmp."""
    m = re.fullmatch(r'RUN_TREE_TMPDIR = "([^"]+)"', source_line(RUN_TAKE, 93))
    if not m or not source_line(RUN_TAKE, 153).startswith('RUN_TREE_TMP = "<run tree>/' + m.group(1) + '"'):
        raise AssertionError("box/run_take.py:93 and 153 are not the run tree's temporary folder")
    return m.group(1)


def run_tree_home_name() -> str:
    """box/run_take.py's RUN_TREE_HOMEDIR and its RUN_TREE_HOME marker (R-H5, glitch-26, 19 Oct 2026): arm O's and
    arm G's HOME is <run tree>/<that name>."""
    with open(RUN_TAKE, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    names = [m.group(1) for m in (re.fullmatch(r'RUN_TREE_HOMEDIR = "([^"]+)"', x) for x in lines) if m]
    if len(names) != 1 or sum(x.startswith(f'RUN_TREE_HOME = "<run tree>/{names[0]}"') for x in lines) != 1:
        raise AssertionError("box/run_take.py names no one RUN_TREE_HOMEDIR and its RUN_TREE_HOME marker")
    return names[0]


# (path, excluded?) under each candidate: its native session file only, nothing else of the home or the run tree.
CANDIDATE_PATHS = {
    "codex": [("sessions/2026/10/14/rollout-2026-10-14T05-00-00-00000000-0000-7000-8000-0000000000c1.jsonl", True),
              ("sessions/2026/10/14/notes.txt", False), ("sessions/2026/10/14/rollout-x.jsonl.zst", False),
              ("auth.json", False), ("config.toml", False), ("history.jsonl", False), ("log/codex-tui.log", False),
              (".tmp/x", False), (".home/.cache/x", False), ("rollout-x.jsonl", False),
              ("other/sessions/rollout-x.jsonl", False)],
    "gemini": [(".gemini/tmp/abc/chats/session-2026-10-14T05-00-1a2b3c4d.jsonl", True),
               (".gemini/tmp/abc/chats/1a2b3c4d/sub-1.jsonl", False), (".gemini/tmp/abc/logs.json", False),
               (".gemini/settings.json", False), (".gemini/tmp/abc/chats/notes.txt", False),
               (".gemini/tmp/chats/session-x.jsonl", False), (".tmp/x", False), (".home/.cache/x", False),
               ("session-x.jsonl", False)],
}


# (run-tree path, excluded?) under each candidate (R4-4): the agent's HOME and everything below it, nothing else.
RUN_TREE_PATHS = [(".home/.cache/pip/x", True), (".home/.conda/envs/e/bin/python", True), (".home/.bashrc", True),
                  (".homes/x", False), ("home/x", False), (".tmp/x", False), ("data/x.csv", False),
                  ("results/.home/x", False), (".git/config", False)]


def candidate_problems(table: dict) -> list:
    """Each candidate is exactly its derived pattern, its grounds quote what they rest on, its run tree excludes the
    agent's HOME alone (R4-4: <run tree>/.home/**, snapshotted but not graded; the rest of the run tree unmeasured),
    it names .tmp/ as kept in, and it excludes its native session file and nothing else listed."""
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
        # R4-4 (glitch-26, lane vendor-b11 round 4): the agent's HOME is inside the run tree, snapshotted, not graded
        home_tree = (run_tree_home_name() + "/**",)
        if e.run_tree_paths != home_tree:
            out.append(f"{name}: run_tree_paths {e.run_tree_paths} are not exactly {home_tree} (R4-4 and B21-7; 18 "
                       f"real walks show no other run-tree furniture)")
        grounds = " ".join(e.grounds)
        # B21-2 and B21-7 (glitch-26, lane vendor-b21): each grounds line names its walks and its pinned source lines
        for need in ({"codex": ["codex_adapter.py:44", "`$CODEX_HOME/sessions/.../rollout-*.jsonl`",
                                "box/run_take.py:68", '"CODEX_HOME": CONFIG_MOUNT', "092d3acd",
                                "rollout/src/recorder.rs:1739-1762", "rollout/src/rollout_file_name.rs:62-73",
                                "rollout/src/lib.rs:86", "12 of 12 codex walks", "w-o7 to w-o17, w-o45",
                                "(w-o15, w-o16, w-o17, w-o45)"],
                      "gemini": ["native_snapshot.py:20", "<home>/.gemini/tmp/*/chats", "native_snapshot.py:13",
                                 "native_snapshot.py:16-18", "assumed, not source-shown", "box/run_take.py:68",
                                 '"GEMINI_CLI_HOME": CONFIG_MOUNT', "chunk-NR7L3FXV.js", "[C] 286708-286730",
                                 "5 of 6 gemini walks", "w-g1, w-g3, w-g5, w-g7, w-g9, w-g11", "(w-g11)"]}[name]
                     + ["R4-4", "B21-7", "box/sidecar.py", "rests on that ruling, not on measured furniture",
                        "nothing appears under it in any snapshot",
                        "no run-tree furniture of its own beyond COMMON_EXCLUSIONS"]):
            if need not in grounds:
                out.append(f"{name}: the grounds do not say {need!r}")
        if "unmeasured until a real walk" in grounds:
            out.append(f"{name}: the grounds still say the run tree is unmeasured (B21 measured it)")
        if not any(path == tmp + "/" for path, _ in e.not_excluded):
            out.append(f"{name}: not_excluded does not name {tmp}/ (box/run_take.py:93, 153)")
        # R4-4: the agent's HOME (R-H5's .home) is excluded from grading now, so it is no longer named as kept in
        if any(path == run_tree_home_name() + "/" for path, _ in e.not_excluded):
            out.append(f"{name}: not_excluded still names {run_tree_home_name()}/, which R4-4 excludes")
        for path, want in CANDIDATE_PATHS[name]:
            if any(hb.matches(p, path) for p in e.home_paths) != want:
                out.append(f"{name}: {path} is {'not ' if want else ''}excluded")
        for path, want in RUN_TREE_PATHS:
            if any(hb.matches(p, path) for p in e.run_tree_paths) != want:
                out.append(f"{name}: run tree {path} is {'not ' if want else ''}excluded")
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


class HomeExclusion(unittest.TestCase):
    """R4-4 (glitch-26, lane vendor-b11 round 4), each way through the end-state grader's own is_excluded: under arms
    O's and G's candidates <run tree>/.home/** is excluded (the agent HOME is inside the run tree: snapshotted, not
    graded); under arm A's entry, untouched, it is not (arm A's HOME is outside the run tree)."""

    def excluded(self, harness, rel, table):
        from graders import endstate
        ev = mock.Mock(run_tree="/srv/w/t", harness=harness, _table=table, home=None)
        return endstate.Evidence.is_excluded(ev, f"/srv/w/t/{rel}")

    def test_arms_o_and_g_exclude_the_agent_home_and_arm_a_does_not(self):
        table = hb.TABLE                                   # B21-2: the production table, vendors promoted
        for rel, want in RUN_TREE_PATHS:
            for name in CANDIDATE_NAMES:
                with self.subTest(harness=name, path=rel):
                    self.assertEqual(self.excluded(name, rel, table), want)
            with self.subTest(harness=ADAPTER_NAME, path=rel):
                self.assertFalse(self.excluded(ADAPTER_NAME, rel, table))
        self.assertEqual(hb.TABLE[ADAPTER_NAME].run_tree_paths, (), "R4-4: arm A's entry moved")

    def test_a_vendor_candidate_without_the_home_exclusion_grades_it(self):
        for name in CANDIDATE_NAMES:
            e = dataclasses.replace(hb.TABLE[name], run_tree_paths=())
            table = dict(hb.TABLE, **{name: e})
            with self.subTest(harness=name):
                self.assertFalse(self.excluded(name, ".home/.conda/envs/e/bin/python", table))


def vendor_entries() -> dict:
    """B21-2: the two promoted entries, read from the production TABLE (KeyError before the promotion)."""
    return {name: hb.TABLE[name] for name in CANDIDATE_NAMES}


class VendorEntries(unittest.TestCase):
    """Lane vendor-b21 (glitch-26's B21-2, Tue 20 Oct 2026; was VendorCandidates, lane vendor-admission T2): Codex's
    and Gemini's entries are in TABLE, exactly the four measured and grounded patterns, and VENDOR_CANDIDATES is
    gone (one source of truth), so production Evidence.load admits both."""

    def test_entries_are_in_the_table_and_the_candidates_are_gone(self):
        self.assertFalse(hasattr(hb, "VENDOR_CANDIDATES"), "B21-2: VENDOR_CANDIDATES still beside the table")
        self.assertEqual(sorted(hb.TABLE), sorted((ADAPTER_NAME,) + CANDIDATE_NAMES))
        for name in CANDIDATE_NAMES:
            self.assertIs(hb.entry(name), hb.TABLE[name])

    def test_production_evidence_admits_a_vendor_take(self):
        from graders import endstate
        for name in CANDIDATE_NAMES:
            take = {"kind": "take", "model": "synthetic-model", "agent": {"harness": name, "version": "0.0.1"},
                    "run_tree": "", "home": None}
            self.assertEqual(endstate.agent_of(take), (name, "0.0.1"))

    def test_each_entry_passes_check_table(self):
        self.assertEqual(hb.check_table(), [])
        for name, e in vendor_entries().items():
            self.assertEqual(hb.check_table({ADAPTER_NAME: hb.TABLE[ADAPTER_NAME], name: e}), [], name)

    def test_each_entry_is_grounded_in_its_source_lines(self):
        self.assertEqual(derived_codex_pattern(), "sessions/**/rollout-*.jsonl")
        self.assertEqual(derived_gemini_pattern(), ".gemini/tmp/*/chats/session-*.jsonl")
        self.assertEqual(run_tree_tmp_name(), ".tmp")
        self.assertEqual(candidate_problems(vendor_entries()), [])

    def test_a_widened_or_moved_entry_goes_red(self):
        entries = vendor_entries()
        widened = {"codex": ("sessions/**", "**/rollout-*.jsonl", "sessions/**/*.jsonl", "sessions/**/rollout-*",
                             "*/**/rollout-*.jsonl", "sessions/**/rollout-*.jsonl*"),
                   "gemini": (".gemini/**", ".gemini/tmp/**/session-*.jsonl", ".gemini/tmp/*/chats/*.jsonl",
                              ".gemini/tmp/*/*/session-*.jsonl", ".gemini/tmp/*/chats/**", ".gemini/*/*/chats/session-*")}
        for name, patterns in widened.items():
            for pattern in patterns:
                for home in ((pattern,), (entries[name].home_paths[0], pattern)):
                    with self.subTest(name=name, home=home):
                        e = dataclasses.replace(entries[name], home_paths=home)
                        self.assertNotEqual(candidate_problems(dict(entries, **{name: e})), [])
        for name in CANDIDATE_NAMES:
            base = entries[name]
            for what, e in {"a guessed run tree": dataclasses.replace(base, run_tree_paths=(".tmp/**",)),
                            "no grounds": dataclasses.replace(base, grounds=("TEST DATA",)),
                            ".tmp/ dropped": dataclasses.replace(base, not_excluded=()),
                            # R4-4 and B21-7: the agent's HOME excluded from grading, exactly
                            ".home/** dropped": dataclasses.replace(base, run_tree_paths=()),
                            ".home/** widened": dataclasses.replace(base, run_tree_paths=(".home/**", ".tmp/**")),
                            ".home/** narrowed": dataclasses.replace(base, run_tree_paths=(".home/*",)),
                            ".home/ still kept in": dataclasses.replace(base, not_excluded=base.not_excluded + (
                                (".home/", "kept in"),)),
                            # B21: the old candidate wording, unmeasured, goes red
                            "still unmeasured": dataclasses.replace(base, grounds=base.grounds + (
                                "the rest of the run tree: unmeasured until a real walk",))}.items():
                with self.subTest(name=name, what=what):
                    self.assertNotEqual(candidate_problems(dict(entries, **{name: e})), [])
        self.assertNotEqual(candidate_problems({"codex": entries["codex"]}), [])

    def test_no_task_path_is_hidden_under_an_entry(self):
        self.assertEqual(candidate_conflicts(vendor_entries()), [])
        e = dataclasses.replace(hb.TABLE["codex"], run_tree_paths=("data/**",))   # mutant: a guess
        self.assertNotEqual(candidate_conflicts(dict(vendor_entries(), codex=e)), [])

    def test_check_task_check_8_on_the_production_table(self):
        # the consumer that iterates TABLE (tasks/check_task.py check 8), run with no table: every harness, every task
        self.assertEqual(candidate_conflicts({}), [])

    def test_no_grader_types_a_vendor(self):
        graders = os.path.join(HERE, "graders")
        found = {}
        with mock.patch.dict(TABLE, vendor_entries()):
            for name in sorted(os.listdir(graders)):
                if name.endswith(".py"):
                    with open(os.path.join(graders, name), encoding="utf-8") as fh:
                        hits = typed_harness(fh.read())
                    if hits:
                        found[name] = hits
            # R4-4: the agent HOME typed as a path is found; an attribute named home is not
            self.assertEqual(typed_harness('X = "/srv/w/t/.home/x"'), [".home"])
            self.assertEqual(typed_harness("X = take.home or self.home or f(a).home or b[0].home"), [])
            for typed in ('X = "codex"', 'X = "gemini"', 'X = "sessions/"', 'X = ".gemini/"'):
                self.assertNotEqual(typed_harness(typed), [], typed)   # the scan fires on each known positive
        self.assertEqual(found, {})

if __name__ == "__main__":
    unittest.main(verbosity=2)
