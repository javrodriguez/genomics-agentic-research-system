#!/usr/bin/env python3
"""The review kit, ported to round 4 (Gap Study round 4, lane review-kit-port).

The kit was copied from round 3 identical: BRIEF.md named gap-study-3 throughout and had the reviewer run
test_round3.py, why.md described round 3's purpose, blindness.py's markers named round 3, and launch.py's usage named
evals/gap-study-3/. The freeze-path plan (section 4, "Before round 1") and glitch-f1's rulings (F5) ask for the port,
a threat model stated in the brief, a structural brief with no list of ways around a rule, the vendor arms in scope,
and a reviewer that runs only light checks and reads the remote runner's outputs of the heavy gates.

  K1.port      the kit's files point at round 4: the bytes under review, every command path, the usage lines; no
               round 3 battery; why.md names no study folder
  K2.markers   blindness.py's markers lead with round 4's names and keep every earlier one
  K3.nested    no marker word occurs in a CLAUDE.md this repository tracks (the harness attaches nested ones)
  K4.brief     the brief keeps what the kit's code reads (the {N} and {PREVIOUS} slots, both ruling lines), states
               the threat model, hands in athena/ for every heavy gate of freeze_rehearsal.py, names the three legs,
               and uses the stop rule's classes
  K5.light     every light command the brief names exists and takes the flag the brief gives it, and none of them is
               a heavy gate
  K6.public    the brief, why.md and the operator notes carry no absolute path and name no person, by
               commit_review.py's own patterns
  K7.model     the reviewer is claude-opus-5-5 and the review commit's co-author line says so; no Fable anywhere in
               the kit's code (glitch-f1's fold 1: the agent-engine policy, and the plan's fresh Opus reviewers)
  K8.athena    build_kit.py takes athena/ itself (--athena, required) and copies it into the kit folder before any
               row can hash it: regular files only, flat, none empty, each naming the commit the clone is at
               (glitch-f1's fold 2)
  K9.smoke     the operator notes require a one-turn skills smoke before round 1 and say what it must show: only
               names on the written list of the client's built-in skills, effort medium, and the environment names
  K10.env      the reviewer's environment is built from an explicit allowlist, never the driver's or the caller's:
               a planted CLAUDE_*/CLAUDE_CODE_* name or any other unlisted name never reaches it, and launch.py
               records the names (never the values) it passed
  K11.effort   launch and resume both pass --effort medium (OD56: Opus 5.5 at medium for reviewers)
  K12.producer review_kit/athena_outputs.py writes one file per gate with its own command and commit lines, masks
               by named rules, and its files pass build_kit's athena/ check
  K13.battery  athena_outputs.py --run-checks-from takes the remote suite's parallel battery as the run_checks gate:
               the copy must open with its own `battery commit <the head> jobs <N>` line and close with the commit's
               own summary line, once and last; the gate's exit is the commit's own run_checks.verdict of that line;
               a link, a missing file, a file inside the repository, another commit, a second or a misplaced
               summary line is refused before any file is written. The README names python3.12 for every step and
               the suite road for step 1
  K14.workflow launch and resume both pass `--disallowedTools Workflow`, so the reviewer cannot start the client's
               bundled workflows (deep-research among them); the README's smoke requires the init record to list
               no Workflow tool, and names the probe that measured the skills question
  K15.sidechains blindness.py also reads every sidechain session the reviewer's session spawned (found through
               the Agent tool results and the client's subagents/ folder; a session file nothing launched is read
               too, and a launched agent with no file is named). Each sub-agent's loaded context gets the same
               markers and its tool inputs the same absolute-path scan. A marker hit in a hand-back is explained
               only when its text is in a file that was in the review folder at launch and that the reviewer did
               not write, and in that sub-agent's own tool traffic; an operator marker is never explained, there
               or anywhere. Writes outside the folder are listed in their own section

Folds of glitch-f1's rulings on the first hand-back (Wed 21 Oct 2026): K7, K8 and K9 were written red first.
Folds of the review of c41b7d50 (REVIEW-review-kit-port-c41b7d5.md, glitch-f1's rulings): K10, K11, K12 and the
tightened K8 (a commit line, not the sha anywhere; no dotfile, absolute home path, person or operator marker; the
half-built folder removed) and K9 (the built-in list, effort, environment names) were written red first.

Lane prefreeze-road (the Lane-orchestrator's ruling of Sat 24 Oct 2026, under Javier's standing delegation, after the
pre-freeze round's remote outputs came back with environment reds): K13 was written red first. K14 (the
Lane-orchestrator's ruling 2 on the lane's hand-back, the same day) was written red first.
Lane blindness-sidechains (the Lane-orchestrator's ruling of Sat 24 Oct 2026, under Javier's standing delegation,
after the pre-freeze round 1 record read 45 UNEXPLAINED hits, every one in a sub-agent hand-back): K15 was written red
first.
The folds of the review of 5a6dc21 (VERDICT CHANGES, the Lane-orchestrator's rulings the same day): SidechainFolds,
twelve more K15 tests, were written red first at 5a6dc21.

Reads committed files only; no model, network, container or take. Interpreter state (sys.modules, sys.path,
os.environ, cwd) is left as found.

--witnesses runs every mutant in this process: each swaps one file's text as the tests read it, and requires its
bound test to fail by an AssertionError carrying its clause token.
"""
from __future__ import annotations

import hashlib
import atexit  # noqa: F401  (TemporaryDirectory's weakref.finalize imports it lazily; loaded here so no test adds a module)
import importlib.util
import json
import locale  # noqa: F401  (subprocess's text mode imports it lazily; loaded here so no test adds a module)
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
KIT = HERE / "review_kit"
REPO = HERE.parent.parent
FILES = {"brief": KIT / "BRIEF.md", "why": KIT / "why.md", "blindness": KIT / "blindness.py",
         "launch": KIT / "launch.py", "rehearsal": HERE / "freeze_rehearsal.py",
         "rounds": KIT / "rounds.py", "commit_review": KIT / "commit_review.py", "build_kit": KIT / "build_kit.py", "readme": KIT / "README.md",
         "producer": KIT / "athena_outputs.py"}
MUTATED: dict[str, str] = {}

ROUND3_MARKERS = ("gars-eval-v4", "gap-study-3", "round 3", "gars-eval-v3", "gap-study-2", "round 2",
                  "gars-haiku-prestudy", "haiku-prestudy", "Waiting on Javier", "glitch-mem", "SOUL.md",
                  "north star", "MEMORY.md")
# The gates the reviewer reads from athena/ and must never run here (F5: the Mac is under the suite's disk floor).
HEAVY = ("test_round4.py", "run_checks.py", "tests/test_box_integration.py", "tests/test_pipeline.py",
         "run.py", "walk_regrade.py", "fixture_walk.py", "freeze_rehearsal.py", "drive.py", "walk_runner.py")


def text(key: str) -> str:
    """The accessor every test reads a kit file through (a witness swaps what it returns)."""
    return MUTATED[key] if key in MUTATED else FILES[key].read_text()


def load_isolated(path: Path, name: str, src: str | None = None):
    """Execute a kit module by path (or a witness's mutated text of it, compiled under the same path, so its HERE and
    its siblings resolve as the real file's do) and give interpreter state back exactly as found."""
    saved_path, saved_mods = list(sys.path), set(sys.modules)
    try:
        if src is None:
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        else:
            mod = types.ModuleType(name)
            mod.__file__ = str(path)
            exec(compile(src, str(path), "exec"), mod.__dict__)
        return mod
    finally:
        sys.path[:] = saved_path
        for m in set(sys.modules) - saved_mods:
            del sys.modules[m]


def markers_of(src: str) -> list[str]:
    block = re.search(r"^MARKERS = \[\n(.*?)^\]", src, re.M | re.S)
    assert block, "K2.markers: no MARKERS list"
    return re.findall(r'\(\s*"[^"]*",\s*"([^"]*)"\s*\)', block.group(1))


def text_of_def(src: str, name: str) -> str:
    """The text of one top-level function of a kit file."""
    m = re.search(rf"^def {name}\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
    assert m, f"K15.sidechains: no def {name}"
    return m.group(0)


def usage_lines(src: str) -> list[str]:
    return [ln.strip() for ln in src.split('"""')[1].splitlines() if ln.strip().startswith("python3 ")]


class Port(unittest.TestCase):
    def test_the_bytes_under_review_are_round_4s(self):
        b = text("brief")
        self.assertIn("a copy of `study/evals/gap-study-4/prereg-draft.json`", b, "K1.port")
        self.assertIn("diff prereg.json study/evals/gap-study-4/prereg-draft.json", b, "K1.port")
        self.assertIn("This round is `study/evals/gap-study-4/`", b, "K1.port")

    def test_every_command_path_is_round_4s(self):
        b = text("brief")
        paths = re.findall(r"evals/(gap-study[-\w]*|haiku-prestudy)/[\w/]+\.py", b)
        self.assertTrue(paths, "K1.port: the brief names no command path")
        self.assertEqual(sorted(set(paths)), ["gap-study-4"], "K1.port")
        self.assertNotIn("test_round3.py", b, "K1.port")

    def test_the_usage_lines_are_round_4s(self):
        for key in ("launch", "blindness"):
            lines = usage_lines(text(key))
            self.assertTrue(lines, f"K1.port: {key}.py has no usage line")
            for ln in lines:
                self.assertIn(f"python3 evals/gap-study-4/review_kit/{key}.py ", ln, "K1.port")

    def test_why_names_no_study_folder_or_round(self):
        w = text("why")
        self.assertIsNone(re.search(r"gap-study|haiku-prestudy|round \d|gars-eval", w), "K1.port")


class Markers(unittest.TestCase):
    def test_round_4_leads_and_every_earlier_marker_stays(self):
        ms = markers_of(text("blindness"))
        self.assertEqual(ms[:3], ["gap-study-4", "round 4", "gap4"], "K2.markers")
        for m in ROUND3_MARKERS:
            self.assertIn(m, ms, "K2.markers")
        self.assertIn("lane-orchestrator", ms, "K2.markers")

    def test_no_marker_occurs_in_a_tracked_claude_md(self):
        ms = markers_of(text("blindness"))
        listed = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"], capture_output=True, check=True)
        names = [n for n in listed.stdout.decode().split("\0") if n.endswith("CLAUDE.md")]
        self.assertTrue(names, "K3.nested: no tracked CLAUDE.md found, so this check measured nothing")
        hits = [(n, m) for n in names for m in ms if m.lower() in (REPO / n).read_text(errors="replace").lower()]
        self.assertEqual(hits, [], "K3.nested")


class Brief(unittest.TestCase):
    def test_the_slots_and_ruling_lines_the_kit_reads_are_kept(self):
        b = text("brief")
        for slot in ("prefreeze-{N}.md", "{PREVIOUS}"):
            self.assertIn(slot, b, "K4.brief")
        for line in ("`**Ruling: DO FREEZE.**`", "`**Ruling: DO NOT FREEZE.**`"):
            self.assertIn(line, b, "K4.brief")
        self.assertIn("Line 1, exactly: `prereg.json sha256: <the hex digest from step 1>`", b, "K4.brief")

    def test_the_threat_model_is_stated(self):
        b = text("brief")
        self.assertIn("## The threat model this review is ruled against", b, "K4.brief")
        section = b.split("## The threat model this review is ruled against", 1)[1].split("\n## ", 1)[0]
        for part in ("**The operator, after the takes exist**", "**The agent under test, during a take**",
                     "Not in scope"):
            self.assertIn(part, section, "K4.brief")

    def test_every_heavy_gate_of_the_rehearsal_is_handed_in(self):
        b = text("brief")
        self.assertIn("`athena/`", b, "K4.brief")
        rehearsal = text("rehearsal")
        named = set(re.findall(r'\("([\w/]+\.py)"', rehearsal.split("COMMANDS = (", 1)[1].split("\n\n", 1)[0]))
        walks = set(re.findall(r'\("([\w/]+\.py)"', rehearsal.split("WALK_COMMANDS = (", 1)[1].split("\n)", 1)[0]))
        self.assertTrue(walks, "K4.brief: no walk gate read from freeze_rehearsal.py")
        step3 = b.split("3. **The heavy gates are read, not run.**", 1)[1].split("\n4. ", 1)[0]
        self.assertIn("freeze_rehearsal.py`'s `COMMANDS`", step3, "K4.brief")
        for gate in sorted(walks | {g for g in named if g.startswith("tests/")} | {"run_checks.py", "freeze.py"}):
            self.assertIn(gate, step3, f"K4.brief: {gate}")

    def test_every_draft_key_the_brief_names_exists(self):
        draft = json.loads((HERE / "prereg-draft.json").read_text())
        b = text("brief")
        keys = re.findall(r"`([a-z_]+)`", b.split("the per-harness draft keys (", 1)[1].split(")", 1)[0])
        step9 = b.split("9. **Is the outcome decidable by code", 1)[1].split("\n10. ", 1)[0]
        keys += re.findall(r"the draft's ((?:`[a-z_]+`(?:, | and )?)+)", step9) and \
            re.findall(r"`([a-z_]+)`", re.search(r"the draft's ((?:`[a-z_]+`(?:, | and )?)+)", step9).group(1))
        self.assertIn("views", keys, "K4.brief: step 9 names no draft key")
        for k in keys:
            self.assertIn(k, draft, f"K4.brief: the brief names `{k}`, which the draft does not hold")

    def test_the_three_legs_and_the_stop_rule_classes(self):
        b = text("brief")
        self.assertIn("freeze.unrecorded_shapes_problem", b, "K4.brief")
        self.assertIn("MAJOR, MINOR or NIT", b, "K4.brief")
        self.assertIn("Rule DO FREEZE only when your table holds no MAJOR.", b, "K4.brief")
        self.assertNotIn("BLOCKER, SHOULD or NIT", b, "K4.brief")


class Light(unittest.TestCase):
    def test_every_light_command_exists_and_takes_its_flag(self):
        b = text("brief")
        step4 = b.split("4. **The light checks are run.**", 1)[1].split("\n5. ", 1)[0]
        listed = re.findall(r"evals/gap-study-4/([\w/]+\.py)( --\w+)?", step4)
        listed += [(m, f) for m, f in re.findall(r"`([\w/]+\.py)( --\w+)?`", step4) if "/" not in m]
        self.assertGreaterEqual(len(listed), 20, "K5.light: fewer light commands than the brief should name")
        run_part = step4.split("Do not run", 1)[0]
        for module, flag in listed:
            src = HERE / module
            self.assertTrue(src.is_file(), f"K5.light: {module}")
            if flag:
                self.assertIn(f'"{flag.strip()}"', src.read_text(), f"K5.light: {module}{flag}")
            if f"{module}{flag}" in run_part:
                self.assertNotIn(module, HEAVY, f"K5.light: {module} is a heavy gate")


class Public(unittest.TestCase):
    def test_no_absolute_path_and_no_person(self):
        cr = load_isolated(KIT / "commit_review.py", "review_kit_commit_review_for_test")
        for key in ("brief", "why", "readme"):
            t = text(key)
            self.assertIsNone(cr.ABS_PATH.search(t), f"K6.public: {key}")
            self.assertIsNone(cr.PERSON.search(t), f"K6.public: {key}")


class Model(unittest.TestCase):
    def test_the_reviewer_is_opus_5_5(self):
        launch = text("launch")
        self.assertIsNotNone(re.search(r'^MODEL = "claude-opus-5-5"$', launch, re.M), "K7.model")
        self.assertIn('"--model", MODEL', launch, "K7.model")
        self.assertIn("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", text("commit_review"), "K7.model")
        for key in ("launch", "commit_review", "build_kit", "blindness"):
            self.assertIsNone(re.search(r"fable", text(key), re.I), f"K7.model: {key}")


def build_kit_module():
    """build_kit.py as the tests read it: the file, or a witness's mutated text, executed in isolation."""
    return load_isolated(FILES["build_kit"], "review_kit_build_kit_for_test", MUTATED.get("build_kit"))


class Athena(unittest.TestCase):
    HEAD = "0123456789abcdef0123456789abcdef01234567"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src = self.root / "outputs"
        self.src.mkdir()
        self.dest = self.root / "kit"
        self.dest.mkdir()
        self.bk = build_kit_module()

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name: str, body: str) -> None:
        (self.src / name).write_text(body)

    def good(self, extra: str = "") -> str:
        return f"command: run_checks.py\ncommit: {self.HEAD}\nexit: 0\n{extra}run_checks: 9 of 9 commands passed\n"

    def test_the_outputs_are_copied_in(self):
        self.put("01-run_checks.txt", self.good("ran evals/gap-study-4/test_round4.py\n"))
        self.put("02-freeze-check.txt", self.good())
        problems, copied = self.bk.copy_athena(self.src, self.dest, self.HEAD)
        self.assertEqual(problems, [], "K8.athena")
        self.assertEqual(sorted(copied), ["01-run_checks.txt", "02-freeze-check.txt"], "K8.athena")
        for name in copied:
            self.assertEqual((self.dest / "athena" / name).read_bytes(), (self.src / name).read_bytes(), "K8.athena")

    def test_what_cannot_be_evidence_at_this_commit_is_refused(self):
        cases = {
            "missing": lambda: None,
            "empty folder": lambda: None,
            "other commit line": lambda: self.put("a.txt", self.good().replace(f"commit: {self.HEAD}",
                                                  "commit: " + "f" * 40) + f"mentions {self.HEAD}\n"),
            "no commit line": lambda: self.put("a.txt", f"command: x\nsha {self.HEAD}\n"),
            "empty file": lambda: self.put("a.txt", ""),
            "nested folder": lambda: ((self.src / "sub").mkdir(), self.put("sub/b.txt", self.good())),
            "link": lambda: (self.put("real.txt", self.good()), os.symlink(self.src / "real.txt", self.src / "l.txt")),
            "dotfile": lambda: self.put(".hidden.txt", self.good()),
            "home path": lambda: self.put("a.txt", self.good("log at /home/athena/run/x.log\n")),
            "person": lambda: self.put("a.txt", self.good("signed javier\n")),
            "operator marker": lambda: self.put("a.txt", self.good("run id gap4-t5-x\n")),
        }
        for case, arrange in cases.items():
            with self.subTest(case=case):
                for p in sorted(self.src.rglob("*"), reverse=True):
                    p.unlink() if (p.is_file() or p.is_symlink()) else p.rmdir()
                for p in sorted(self.src.glob(".*")):
                    p.unlink()
                shutil_rm(self.dest / "athena")
                arrange()
                src = self.root / "absent" if case == "missing" else self.src
                problems, copied = self.bk.copy_athena(src, self.dest, self.HEAD)
                self.assertTrue(problems, f"K8.athena: {case} was accepted")
                self.assertFalse((self.dest / "athena").exists(), f"K8.athena: {case} left a partial athena/")

    def test_main_requires_the_outputs_and_cleans_a_half_built_folder(self):
        src = text("build_kit")
        self.assertIsNotNone(re.search(r'add_argument\("--athena",[^)]*required=True', src), "K8.athena")
        main = src.split("def main()", 1)[1]
        self.assertLess(main.index("copy_athena("), main.index("folder.mkdir("), "K8.athena: checked after the folder exists")
        second = main.split("problems, copied = copy_athena(athena, folder, head)", 1)[1].split("return 2", 1)[0]
        self.assertIn("shutil.rmtree(folder)", second, "K8.athena: a refused second check leaves a half-built folder")


class Env(unittest.TestCase):
    PLANTED = {"CLAUDE_EFFORT": "max", "CLAUDE_CODE_SESSION_ID": "x", "CLAUDE_CODE_CHILD_SESSION": "1",
               "CLAUDE_CODE_MESSAGING_SOCKET": "sock", "CLAUDE_CODE_MESSAGING_TOKEN": "tok", "CLAUDECODE": "1",
               "CLAUDE_CONFIG_DIR": "elsewhere", "ANTHROPIC_API_KEY": "k", "SOME_OTHER_NAME": "v"}

    def launch(self):
        return load_launch()

    def test_the_environment_is_an_allowlist(self):
        lk = self.launch()
        caller = {"PATH": "/bin", "HOME": "/h", "LANG": "C.UTF-8", **self.PLANTED}
        env = lk.env_for(caller)
        for name in self.PLANTED:
            self.assertNotIn(name, env, f"K10.env: {name} reached the reviewer")
        self.assertEqual(env["PATH"], "/bin", "K10.env")
        self.assertEqual(env["HOME"], "/h", "K10.env")
        for k, v in lk.REVIEWER_ENV.items():
            self.assertEqual(env.get(k), v, "K10.env")
        self.assertTrue(set(env) <= set(lk.ALLOWED_ENV) | set(lk.REVIEWER_ENV), f"K10.env: {sorted(env)}")
        for name, why in lk.ALLOWED_ENV.items():
            self.assertTrue(why.strip(), f"K10.env: {name} has no reason")
            self.assertFalse(name.startswith("CLAUDE"), f"K10.env: {name} is a client session name")

    def test_the_driver_environment_is_never_used(self):
        self.assertNotIn("child_env", text("launch"), "K10.env")
        self.assertNotIn("as round 3's did", text("launch"), "K10.env")

    def test_the_names_passed_are_recorded_without_values(self):
        lk = self.launch()
        with tempfile.TemporaryDirectory() as d:
            lk.record_env_names(Path(d), {"PATH": "/secret/bin", "HOME": "/h"})
            got = (Path(d) / "env-names.txt").read_text()
        self.assertEqual(got, "HOME\nPATH\n", "K10.env")


class Effort(unittest.TestCase):
    def test_launch_and_resume_pass_effort_medium(self):
        lk = load_launch()
        drive = types.SimpleNamespace(ISOLATION_FLAGS=("--setting-sources", "project,local"))
        for argv in (lk.argv_for("id", drive), lk.resume_argv_for("id", drive)):
            i = argv.index("--effort") if "--effort" in argv else -1
            self.assertGreaterEqual(i, 0, "K11.effort: no --effort")
            self.assertEqual(argv[i + 1], "medium", "K11.effort")
            self.assertEqual(argv[argv.index("--model") + 1], "claude-opus-5-5", "K11.effort")


class Workflow(unittest.TestCase):
    def test_launch_and_resume_disallow_the_workflow_tool(self):
        lk = load_launch()
        drive = types.SimpleNamespace(ISOLATION_FLAGS=("--setting-sources", "project,local"))
        for argv in (lk.argv_for("id", drive), lk.resume_argv_for("id", drive)):
            self.assertIn("--disallowedTools", argv, "K14.workflow: no --disallowedTools")
            self.assertEqual(argv[argv.index("--disallowedTools") + 1], "Workflow", "K14.workflow")
            self.assertTrue(argv[argv.index("--disallowedTools") + 2].startswith("--"),
                            "K14.workflow: the disallow list holds Workflow alone")

    def test_the_smoke_checks_the_tool_list_and_cites_the_probe(self):
        section = text("readme").split("## Before round 1: the skills smoke", 1)[1].split("\n## ", 1)[0]
        self.assertIn("lists no `Workflow` tool", section, "K14.workflow: the smoke reads the tool list")
        self.assertNotIn("has not been measured", section, "K14.workflow: the probe measured it")
        self.assertIn("e02da1fd-a604-4570-91f5-ed48a7b5faa4", section, "K14.workflow: the probe is named")


class Folder(unittest.TestCase):
    def test_launch_refuses_a_folder_without_athena_or_commit(self):
        lk = load_launch()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "kit"
            (f / "study").mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(f / "study")], check=True)
            (f / "BRIEF.md").write_text("x")
            bad = lk.folder_problems(f)
            self.assertTrue(any("athena" in b for b in bad), f"K10.env: {bad}")
            self.assertTrue(any("COMMIT" in b for b in bad), f"K10.env: {bad}")
            (f / "athena").mkdir()
            (f / "athena" / "a.txt").write_text("x")
            (f / "COMMIT").write_text("0" * 40 + "\n")
            self.assertEqual(lk.folder_problems(f), [], "K10.env")


class Producer(unittest.TestCase):
    HEAD = "0123456789abcdef0123456789abcdef01234567"

    def test_each_file_carries_its_lines_and_passes_the_kit_check(self):
        pr = load_isolated(FILES["producer"], "review_kit_athena_outputs_for_test", MUTATED.get("producer"))
        bk = build_kit_module()
        with tempfile.TemporaryDirectory() as d:
            out, repo, home = Path(d) / "out", Path(d) / "repo", Path(d)
            out.mkdir()
            body = (f"ok in {repo}/evals/gap-study-4/x.py\nlog {home}/run.log by javier\n"
                    "run id gap4-t5 and lane-orchestrator\nlast line\n")
            name = pr.write_output(out, 3, "copy_manifest.py --check", self.HEAD, 0, body, repo, home)
            got = (out / name).read_text()
            lines = got.splitlines()
            self.assertEqual(lines[0], "command: copy_manifest.py --check", "K12.producer")
            self.assertEqual(lines[1], f"commit: {self.HEAD}", "K12.producer")
            self.assertEqual(lines[2], "exit: 0", "K12.producer")
            self.assertIn("evals/gap-study-4/x.py", got, "K12.producer: the study's own folder name is kept")
            self.assertTrue(got.rstrip().endswith("last line"), "K12.producer")
            problems, copied = bk.copy_athena(out, Path(d), self.HEAD)
            self.assertEqual(problems, [], "K12.producer")
            self.assertEqual(copied, [name], "K12.producer")

    def test_the_producer_runs_every_gate(self):
        src = text("producer")
        for must in ("freeze_rehearsal.COMMANDS", "unrecorded_shapes_problem", '"run_checks.py"',
                     '("freeze.py", "--check")', "owed_step", "status", "--porcelain"):
            self.assertIn(must, src, f"K12.producer: {must}")
        self.assertIn("athena_outputs.py", text("readme"), "K12.producer: the README names it")


class Battery(unittest.TestCase):
    HEAD = "0123456789abcdef0123456789abcdef01234567"
    PASS3 = ("PASS [test_round4] exit 0 in 9.0s: python3 -W ignore evals/gap-study-4/test_round4.py\n"
             "    test_round4: 9 run, 0 skipped, 0 expected failures\n"
             "PASS [a.txt:1] exit 0 in 0.1s: true\nPASS [a.txt:2] exit 0 in 0.1s: true\n"
             "athena-suite: battery tree unchanged\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pr = load_isolated(FILES["producer"], "review_kit_athena_outputs_for_battery", MUTATED.get("producer"))
        self.rc = load_isolated(HERE / "run_checks.py", "run_checks_for_battery_test")
        # a three-command battery: the copies below count it whole (review MINOR-1: a count that is not the commit's
        # whole battery is refused)
        self.rc.commands = lambda: [("test_round4", "t"), ("a.txt:1", "true")]
        self.rc.file_problems = lambda: [("b.TXT", "not a lane checks file")]     # whole = 2 commands + 1 problem

    def tearDown(self):
        self.tmp.cleanup()

    def copy(self, body: str, head: str | None = None, jobs: int = 24, name: str = "battery.out") -> Path:
        p = self.root / name
        p.write_text(f"athena-suite: battery commit {head or self.HEAD} jobs {jobs}\n" + body)
        return p

    def test_the_battery_copy_is_the_run_checks_gate(self):
        for body, code in ((self.PASS3 + "run_checks: 3 of 3 commands passed\n", 0),
                           (self.PASS3.replace("PASS [a.txt:2] exit 0", "FAIL [a.txt:2] exit 1")
                            + "run_checks: 2 of 3 commands passed\n", 1)):
            with self.subTest(code=code):
                why, gate = self.pr.battery_gate(self.copy(body), self.HEAD, self.rc, REPO)
                self.assertIsNone(why, f"K13.battery: {why}")
                label, got, out = gate
                self.assertEqual(got, code, "K13.battery: the exit is the commit's own verdict of its summary line")
                self.assertTrue(label.startswith("run_checks.py"), f"K13.battery: {label}")
                self.assertIn("24 at a time", label, "K13.battery: the label says how the lines ran")
                self.assertEqual(out.splitlines()[-1], body.splitlines()[-1], "K13.battery: the summary, verbatim, last")
                self.assertNotIn("battery commit", out, "K13.battery: the binding line is not gate output")
                self.assertIn("PASS [a.txt:1]", out, "K13.battery")

    def test_a_copy_that_cannot_be_bound_to_this_head_is_refused(self):
        good = self.PASS3 + "run_checks: 3 of 3 commands passed\n"
        # a well-formed copy inside a stand-in repository (the temporary folder), so only that rule can refuse it
        inside = self.copy(good, name="inside.out")
        link = self.root / "l.out"
        os.symlink(self.copy(good, name="real.out"), link)
        (self.root / "nohead.out").write_text(good)
        (self.root / "nojobs.out").write_text(f"athena-suite: battery commit {self.HEAD}\n" + good)
        cases = {
            "missing": self.root / "absent.out",
            "a link": link,
            "inside the repository": inside,
            # an existing well-formed copy, named relative to the working folder (closure review m3)
            "a relative path": Path(os.path.relpath(self.copy(good, name="rel.out"))),
            "the commands without the file problems": self.copy(self.PASS3.replace("PASS [a.txt:2] exit 0 in 0.1s: true\n", "")
                                                                + "run_checks: 2 of 2 commands passed\n", name="two-only.out"),
            "a tree line not just before the summary": self.copy(
                "athena-suite: battery tree unchanged\n" + self.PASS3.replace("athena-suite: battery tree unchanged\n", "")
                + "run_checks: 3 of 3 commands passed\n", name="tree-early.out"),
            "not this battery's count": self.copy(self.PASS3 + "run_checks: 4 of 4 commands passed\n", name="four.out"),
            "no tree line": self.copy(self.PASS3.replace("athena-suite: battery tree unchanged\n", "")
                                      + "run_checks: 3 of 3 commands passed\n", name="notree.out"),
            "a changed tree": self.copy(self.PASS3.replace("battery tree unchanged", "battery tree changed: 1 entr(ies) differ")
                                        + "run_checks: 3 of 3 commands passed\n", name="changed.out"),
            "another commit": self.copy(good, head="f" * 40, name="other.out"),
            "no binding line": self.root / "nohead.out",
            "a binding line without jobs": self.root / "nojobs.out",
            "no summary line": self.copy(self.PASS3, name="nosum.out"),
            "two summary lines": self.copy("run_checks: 3 of 3 commands passed\n" + good, name="two.out"),
            "summary not last": self.copy(good + "later\n", name="notlast.out"),
            "a summary of nothing": self.copy("run_checks: 0 of 0 commands passed\n", name="zero.out"),
        }
        for case, path in cases.items():
            with self.subTest(case=case):
                why, gate = self.pr.battery_gate(path, self.HEAD, self.rc,
                                                 self.root if case == "inside the repository" else REPO)
                self.assertTrue(why, f"K13.battery: {case} was taken as the gate")
                self.assertIsNone(gate, f"K13.battery: {case}")

    def test_main_checks_the_copy_before_any_file_is_written(self):
        src = text("producer")
        self.assertIn('ap.add_argument("--run-checks-from"', src, "K13.battery")
        main = src.split("def main()", 1)[1]
        self.assertLess(main.index("battery_gate("), main.index("out.mkdir("), "K13.battery: checked before writing")

    def test_the_readme_names_the_interpreter_and_the_suite_road(self):
        r = text("readme")
        order = r.split("## A round, in order", 1)[1].split("\n## ", 1)[0]
        bare = re.findall(r"`python3 [^`]*`", order)
        self.assertEqual(bare, [], f"K13.battery: a step names a bare python3: {bare}")
        for n in range(2, 7):
            step = re.search(rf"^{n}\. .*$", order, re.M)
            self.assertIsNotNone(step, f"K13.battery: no step {n}")
            self.assertIn("`python3.12 evals/gap-study-4/review_kit/", step.group(0), f"K13.battery: step {n}")
        first = re.search(r"^1\. .*$", order, re.M)
        self.assertIsNotNone(first, "K13.battery: no step 1")
        for must in ("python3.12", "athena_suite.py run", "--kind gars-gap4", "--outputs", "--jobs 24", "fetch"):
            self.assertIn(must, first.group(0), f"K13.battery: step 1 names {must}")


def load_launch():
    return load_isolated(FILES["launch"], "review_kit_launch_for_test", MUTATED.get("launch"))








def shutil_rm(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)


class Smoke(unittest.TestCase):
    def test_the_operator_notes_require_the_skills_smoke(self):
        r = text("readme")
        self.assertIn("## Before round 1: the skills smoke", r, "K9.smoke")
        section = r.split("## Before round 1: the skills smoke", 1)[1].split("\n## ", 1)[0]
        for must in ("one turn", "launch.py", "blindness.py", "skill", "UNEXPLAINED", "lane-orchestrator",
                     "does not open", "env-names.txt", "`effort`", "`medium`"):
            self.assertIn(must, section, f"K9.smoke: {must}")
        builtin = re.search(r"^BUILT-IN SKILLS: (.+)$", section, re.M)
        self.assertIsNotNone(builtin, "K9.smoke: no written list of the client's built-in skills")
        names = [n.strip(" `") for n in builtin.group(1).split(",")]
        self.assertEqual(len(names), 13, f"K9.smoke: {names}")
        self.assertNotIn("lane-orchestrator-runtime", names, "K9.smoke")
        self.assertIn("prefreeze-3", section, "K9.smoke: how the list was obtained")
        self.assertIn("only names on that list", section, "K9.smoke: default deny")


def load_blindness():
    return load_isolated(FILES["blindness"], "blindness_under_test", MUTATED.get("blindness"))


class Sidechains(unittest.TestCase):
    """K15.sidechains: the reviewer's sub-agents are read, and a hand-back is explained only by the folder it was given.

    One fixture: a reviewer session that launches three sub-agents (and a fourth session file nothing launched), each
    a sidechain session file in the client's own layout, `<session>/subagents/agent-<id>.jsonl` with its meta file.
    """

    SID = "11111111-2222-5333-8444-555555555555"
    NOTES = ("The battery for gap-study-3 ran inside its own box; see evals/gap-study-2/a.py for the older one.\n"
             "The pre-study, haiku-prestudy, is frozen.\n"
             "A comment that names the lane-orchestrator.\n")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name).resolve()
        self.projects = root / "projects"
        self.folder = root / "pfr-k15" / "round9"
        study = self.folder / "study" / "evals"
        (study / "gap-study-2").mkdir(parents=True)
        (study / "notes.md").write_text(self.NOTES)
        (study / "gap-study-2" / "a.py").write_text("x = 1\n")
        side = self.folder.parent / "round9-launch"
        side.mkdir()
        (side / "SESSION").write_text(self.SID + "\n")
        (side / "folder-at-launch.txt").write_text("study\n")
        F = str(self.folder)
        notes = F + "/study/evals/notes.md"
        proj = self.projects / "-k15"
        sub = proj / self.SID / "subagents"
        sub.mkdir(parents=True)

        def att(kind, **kw):
            return {"type": "attachment", "attachment": {"type": kind, **kw}}

        def call(tid, name, inp):
            return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": name,
                                                                  "input": inp}]}}

        def result(tid, body, tur=None):
            rec = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                                            "content": [{"type": "text", "text": body}]}]}}
            if tur is not None:
                rec["toolUseResult"] = tur
            return rec

        def handback(aid, body):
            return (f'Another Claude session sent a message:\n<agent-message from="{aid}">\n[Subagent hand-back] '
                    f"{body}\n</agent-message>")

        skills = att("skill_listing", content="- dataviz: charts\n- run: launch the app\n")
        reviewer = [att("environment", snapshot={"workingDirectory": F}), skills,
                    att("total_tokens_reminder", content=f"cwd {F} names lane-orchestrator here")]
        for tid, aid in (("toolu_A", "aaa"), ("toolu_B", "bbb"), ("toolu_C", "ccc"), ("toolu_D", "ddd")):
            reviewer.append(call(tid, "Agent", {"description": "d", "subagent_type": "general-purpose",
                                                "prompt": f"Read only under {F}."}))
            # ddd's launch names its agent in the result text only, as the client's own text does.
            reviewer.append(result(tid, f"Async agent launched successfully.\nagentId: {aid} (internal ID)",
                                   None if aid == "ddd" else {"agentId": aid, "status": "async_launched"}))
        # fff runs in the foreground: its report comes back as the Agent tool's own result.
        reviewer.append(call("toolu_F", "Agent", {"description": "d", "prompt": "p"}))
        reviewer.append(result("toolu_F", "Done: the gap4 notes.", {"agentId": "fff", "status": "completed"}))
        said = "the hand-back said round 2's goal id gars-eval-v3\n"
        (self.folder / "study" / "review-notes.md").write_text(said)
        (self.folder / "report.md").write_text(said)
        reviewer.append(call("toolu_W", "Write", {"file_path": F + "/study/review-notes.md", "content": said}))
        # A hand-back delivered as a user message (aaa), and one delivered as a queued_command attachment (bbb).
        reviewer.append({"type": "user", "message": {"content": handback(
            "aaa", "The battery for gap-study-3 ran inside its own box. The haiku-prestudy is frozen. "
                   "Compare /Users/someone/other/evals/gap-study-2/a.py with it.")}})
        queued = att("queued_command", commandMode="prompt", prompt=handback(
            "bbb", "round 2's goal id gars-eval-v3 sets the old floor."))
        queued["attachment"]["origin"] = {"from": "bbb", "body": "round 2's goal id gars-eval-v3 sets the old floor."}
        queued["rendered"] = [{"content": "<system-reminder>\n" + queued["attachment"]["prompt"] + "\n</system-reminder>"}]
        reviewer.append(queued)
        reviewer.append({"type": "user", "message": {"content": handback(
            "ccc", "A comment that names the lane-orchestrator.")}})
        reviewer.append({"type": "user", "message": {"content": handback(
            "eee", "Per gap-study-3, nothing else.")}})
        self.write(proj / f"{self.SID}.jsonl", reviewer)
        # Every file of the folder is older than the launch stamp, so the rules under test here (the launch listing
        # and the sessions' own writes) are the only ones that exclude a file.
        stamp = 1_700_000_000
        os.utime(side / "folder-at-launch.txt", (stamp, stamp))
        for p in self.folder.rglob("*"):
            if p.is_file():
                os.utime(p, (stamp - 90, stamp - 90))

        side_a = [{"type": "user", "isSidechain": True, "agentId": "aaa", "message": {"content": "brief"}}, skills,
                  call("t1", "Read", {"file_path": notes}), result("t1", self.NOTES.split("\n")[0]),
                  call("t2", "Bash", {"command": "mkdir -p /tmp/cmrev && cat > /tmp/cmrev/v.py <<'EOF'\nx\nEOF"}),
                  result("t2", "")]
        side_b = [{"type": "user", "isSidechain": True, "agentId": "bbb", "message": {"content": "brief"}}, skills,
                  att("nested_memory", path="/Users/someone/OrgOS/CLAUDE.md", content="notes"),
                  call("t3", "Bash", {"command": "cat /Users/someone/elsewhere/x.txt"}),
                  result("t3", "round 2's goal id gars-eval-v3 sets the old floor.")]
        side_c = [{"type": "user", "isSidechain": True, "agentId": "ccc", "message": {"content": "brief"}},
                  att("skill_listing", content="- dataviz: charts\n- lane-orchestrator: the operator's skill\n"),
                  call("t4", "Read", {"file_path": notes}), result("t4", self.NOTES)]
        side_x = [{"type": "user", "isSidechain": True, "agentId": "xxx", "message": {"content": "brief"}},
                  att("total_tokens_reminder", content="the north star")]
        side_f = [{"type": "user", "isSidechain": True, "agentId": "fff", "message": {"content": "brief"}}]
        for aid, recs, tid in (("aaa", side_a, "toolu_A"), ("bbb", side_b, "toolu_B"), ("ccc", side_c, "toolu_C"),
                               ("xxx", side_x, "toolu_X"), ("fff", side_f, "toolu_F")):
            self.write(sub / f"agent-{aid}.jsonl", recs)
            (sub / f"agent-{aid}.meta.json").write_text(json.dumps({"agentType": "general-purpose",
                                                                    "toolUseId": tid}))

    def tearDown(self):
        self._tmp.cleanup()

    @staticmethod
    def write(path: Path, recs: list[dict]) -> None:
        path.write_text("".join(json.dumps(r) + "\n" for r in recs))

    def analysed(self):
        b = load_blindness()
        return b, b.analyse(self.folder, self.SID, self.projects)

    def row(self, table, label):
        rows = [r for r in table if r["label"] == label]
        self.assertEqual(len(rows), 1, f"K15.sidechains: {label} rows {len(rows)}")
        return rows[0]

    def test_every_sidechain_is_found_and_one_nothing_launched_is_still_read(self):
        _, a = self.analysed()
        self.assertEqual(sorted(a["sidechains"]), ["aaa", "bbb", "ccc", "fff", "xxx"], "K15.sidechains")
        self.assertEqual(a["missing"], ["ddd"], "K15.sidechains: a launched agent with no session file")
        self.assertEqual(a["unlaunched"], ["xxx"], "K15.sidechains: a session file nothing launched")
        side = self.row(a["side_table"], "the operator's objective line")
        self.assertEqual(side["un"], 1, "K15.sidechains: the unlaunched session's context is scanned")

    def test_a_handback_hit_traced_to_a_folder_file_the_subagent_read_is_explained(self):
        _, a = self.analysed()
        row = self.row(a["handback_table"], "round 3's folder name")
        self.assertEqual((row["total"], row["traced"], row["un"]), (2, 1, 1), f"K15.sidechains: {row}")

    def test_a_handback_hit_not_traced_is_unexplained(self):
        _, a = self.analysed()
        # In the folder but never read by aaa; read by bbb outside the folder and in no folder file; traced only
        # through an absolute path outside the folder (aaa); from an agent with no sidechain session (eee).
        pre = self.row(a["handback_table"], "the pre-study's folder name")
        self.assertEqual((pre["traced"], pre["un"]), (0, 1), f"K15.sidechains: not read there {pre}")
        goal = self.row(a["handback_table"], "round 2's goal id")
        self.assertEqual((goal["total"], goal["traced"], goal["un"]), (1, 0, 1),
                         f"K15.sidechains: one message, read once {goal}")
        old = self.row(a["handback_table"], "round 2's folder name")
        self.assertEqual((old["traced"], old["un"]), (0, 1), f"K15.sidechains: an outside absolute path {old}")
        quotes = "\n".join(q for _, q in a["handback_quotes"])
        self.assertIn("gars-eval-v3", quotes, "K15.sidechains: an UNEXPLAINED hit is quoted")
        self.assertTrue(all(len(q) <= 120 for _, q in a["handback_quotes"]), "K15.sidechains: quotes are capped")

    def test_the_reviewers_own_writes_are_never_the_folder_it_was_given(self):
        # Both files quote gars-eval-v3: one the reviewer wrote inside a folder it was handed, one that was not in
        # the folder at launch. Neither is the folder the reviewer was given, so neither can trace a hit.
        _, a = self.analysed()
        self.assertNotIn(str(self.folder / "study" / "review-notes.md"), a["corpus_files"], "K15.sidechains: written")
        self.assertNotIn(str(self.folder / "report.md"), a["corpus_files"], "K15.sidechains: not there at launch")
        self.assertIn(str(self.folder / "study" / "evals" / "notes.md"), a["corpus_files"], "K15.sidechains")

    def test_an_operator_marker_is_never_explained(self):
        _, a = self.analysed()
        hb = self.row(a["handback_table"], "the operator's coordinating session")
        self.assertEqual((hb["total"], hb["traced"], hb["un"]), (1, 0, 1), f"K15.sidechains: hand-back {hb}")
        own = self.row(a["table"], "the operator's coordinating session")
        self.assertEqual((own["fp"], own["un"]), (0, 1), f"K15.sidechains: beside the folder path {own}")
        side = self.row(a["side_table"], "the operator's coordinating session")
        self.assertEqual(side["un"], 1, f"K15.sidechains: a sub-agent's skill listing {side}")
        orgos = self.row(a["side_table"], "the operator's list system")
        self.assertEqual(orgos["un"], 1, f"K15.sidechains: {orgos}")

    def test_handbacks_are_read_whichever_record_carries_them(self):
        _, a = self.analysed()
        self.assertEqual(sorted(a["handbacks"]), ["aaa", "bbb", "ccc", "eee", "fff"], "K15.sidechains")
        sync = self.row(a["handback_table"], "the round's shorthand")
        self.assertEqual((sync["total"], sync["un"]), (1, 1), f"K15.sidechains: a foreground result {sync}")
        reviewer_ctx = self.row(a["table"], "round 2's goal id")
        self.assertEqual(reviewer_ctx["total"], 0, "K15.sidechains: a hand-back is not counted twice")

    def test_paths_outside_and_writes_outside_are_listed_per_session(self):
        b, a = self.analysed()
        self.assertTrue(any("/tmp/cmrev" in p for p in a["side_outside"]["aaa"]), "K15.sidechains")
        self.assertTrue(any("elsewhere" in p for p in a["side_outside"]["bbb"]), "K15.sidechains")
        self.assertEqual(sorted(a["writes"]), ["aaa"], f"K15.sidechains: {a['writes']}")
        self.assertTrue(all(p.startswith("/tmp/cmrev") for p in a["writes"]["aaa"]), "K15.sidechains")
        out = b.render(a, self.folder)
        self.assertIn("Writes outside the folder", out, "K15.sidechains")
        self.assertNotIn(str(self.folder), out, "K15.sidechains: the folder is masked")

    def test_the_isolation_the_records_show(self):
        _, a = self.analysed()
        iso = a["isolation"]
        self.assertEqual(iso["aaa"]["skills_as_reviewer"], True, "K15.sidechains")
        self.assertEqual(iso["ccc"]["skills_as_reviewer"], False, "K15.sidechains")
        self.assertEqual(iso["bbb"]["memory_outside"], 1, "K15.sidechains")
        self.assertEqual(iso["aaa"]["workflow"] + iso["aaa"]["mcp"], 0, "K15.sidechains")


def _att(kind, **kw):
    return {"type": "attachment", "attachment": {"type": kind, **kw}}


def _call(tid, name, inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def _result(tid, body, tur=None):
    rec = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                                    "content": [{"type": "text", "text": body}]}]}}
    if tur is not None:
        rec["toolUseResult"] = tur
    return rec


def _hb(aid, body):
    return {"type": "user", "message": {"content": f'Another Claude session sent a message:\n<agent-message from="{aid}">'
                                                   f"\n[Subagent hand-back] {body}\n</agent-message>"}}


def _launch(tid, aid):
    return [_call(tid, "Agent", {"prompt": "p"}),
            _result(tid, f"Async agent launched successfully.\nagentId: {aid}", {"agentId": aid, "status": "async_launched"})]


def _side(aid, recs):
    return [{"type": "user", "isSidechain": True, "agentId": aid, "message": {"content": "brief"}}] + recs


class SidechainFolds(unittest.TestCase):
    """K15.sidechains, the folds of the review of 5a6dc21 (REVIEW-blindness-sidechains-5a6dc21.md, the
    Lane-orchestrator's rulings of Sat 24 Oct 2026): one small fixture per finding, `@F` standing for the folder."""

    SID = "11111111-2222-5333-8444-666666666666"

    def run_case(self, files, reviewer, sides, newer=(), manifest=None, register=None):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            folder = root / "pfr" / "round9"
            (folder / "study").mkdir(parents=True)
            launch_side = folder.parent / "round9-launch"
            launch_side.mkdir()
            listing = launch_side / "folder-at-launch.txt"
            listing.write_text("study\n")
            stamp = 1_700_000_000
            os.utime(listing, (stamp, stamp))
            for rel, body in files.items():
                p = folder / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body)
                when = stamp + 90 if rel in newer else stamp - 90
                os.utime(p, (when, when))
            if manifest is not None:
                (launch_side / "folder-manifest.txt").write_text(
                    "".join(f"{hashlib.sha256(body.encode()).hexdigest()}  {rel}\n" for rel, body in manifest.items()))
            F = str(folder)
            proj = root / "projects" / "-k15b"
            sub = proj / self.SID / "subagents"
            sub.mkdir(parents=True)

            def fix(recs):
                return "".join(json.dumps(r).replace("@F", F) + "\n" for r in recs)
            (proj / f"{self.SID}.jsonl").write_text(fix(reviewer))
            for aid, recs in sides.items():
                (sub / f"agent-{aid}.jsonl").write_text(fix(recs))
            b = load_blindness()
            if register is not None:
                (root / "rounds.json").write_text(json.dumps({"rows": register}))
                b.REGISTER = root / "rounds.json"
            a = b.analyse(folder, self.SID, root / "projects")
            a["rendered"] = b.render(a, folder)
            return a

    def hb_row(self, a, label):
        rows = {r["label"]: (r["total"], r["traced"], r["un"]) for r in a["handback_table"]}
        return rows[label]

    def test_a_path_tail_that_drops_the_marker_explains_nothing(self):
        a = self.run_case({"study/evals/gap-study-4/tests/test_x.py": "x=1\n"},
                          _launch("tA", "aaa") + [_hb("aaa", "see evals/gap-study-3/tests/test_x.py for the old one")],
                          {"aaa": _side("aaa", [_call("t1", "Bash", {"command": "find @F/study -name '*.py'"}),
                                                _result("t1", "@F/study/evals/gap-study-4/tests/test_x.py")])})
        self.assertEqual(self.hb_row(a, "round 3's folder name"), (1, 0, 1), "K15.sidechains: tail without the marker")

    def test_a_file_a_shell_command_wrote_inside_the_folder_is_not_the_folder(self):
        a = self.run_case({"study/readme.md": "hello\n", "study/scratch.md": "the floor is gars-eval-v3's\n"},
                          _launch("tA", "aaa") + [_hb("aaa", "the floor is gars-eval-v3's")],
                          {"aaa": _side("aaa", [_call("t1", "Bash", {"command": "cat > @F/study/scratch.md <<'EOF'\nx\nEOF"}),
                                                _result("t1", ""),
                                                _call("t2", "Read", {"file_path": "@F/study/scratch.md"}),
                                                _result("t2", "the floor is gars-eval-v3's")])})
        self.assertEqual(self.hb_row(a, "round 2's goal id"), (1, 0, 1), "K15.sidechains: a shell write inside")

    def test_a_file_newer_than_the_launch_stamp_is_not_the_folder(self):
        a = self.run_case({"study/readme.md": "hello\n", "study/late.md": "the floor is gars-eval-v3's\n"},
                          _launch("tA", "aaa") + [_hb("aaa", "the floor is gars-eval-v3's")],
                          {"aaa": _side("aaa", [_call("t2", "Read", {"file_path": "@F/study/late.md"}),
                                                _result("t2", "the floor is gars-eval-v3's")])},
                          newer=("study/late.md",))
        self.assertEqual(self.hb_row(a, "round 2's goal id"), (1, 0, 1), "K15.sidechains: newer than the stamp")
        self.assertIn("launch stamp", a["corpus_rule"], "K15.sidechains: the rule that ran is named")
        self.assertIn("launch stamp", a["rendered"], "K15.sidechains: the rule that ran is printed")

    def test_with_a_manifest_only_its_unchanged_files_are_the_folder(self):
        files = {"study/kept.md": "the haiku-prestudy is frozen\n", "study/changed.md": "gars-eval-v3 floor\n",
                 "study/unlisted.md": "round 2's floor\n"}
        manifest = {"study/kept.md": files["study/kept.md"], "study/changed.md": "something else\n"}
        reads = [_call("t1", "Bash", {"command": "cat study/*.md"}), _result("t1", "".join(files.values()))]
        a = self.run_case(files, _launch("tA", "aaa") + [_hb("aaa", "the haiku-prestudy; gars-eval-v3 floor; round 2's floor")],
                          {"aaa": _side("aaa", reads)}, manifest=manifest)
        self.assertEqual(self.hb_row(a, "the pre-study's folder name"), (1, 1, 0), "K15.sidechains: a listed file")
        self.assertEqual(self.hb_row(a, "round 2's goal id"), (1, 0, 1), "K15.sidechains: changed since launch")
        self.assertEqual(self.hb_row(a, "round 2's name"), (1, 0, 1), "K15.sidechains: not listed at launch")
        self.assertIn("manifest", a["corpus_rule"], "K15.sidechains: the rule that ran is named")
        self.assertIn("NO round row", a["corpus_rule"], "K15.sidechains: a manifest no row hashed binds nothing")
        text = "".join(f"{hashlib.sha256(body.encode()).hexdigest()}  {rel}\n" for rel, body in manifest.items())
        b = load_blindness()
        a = self.run_case(files, _launch("tA", "aaa"), {"aaa": _side("aaa", [])}, manifest=manifest,
                          register=[{"n": 7, "input_sha256": b.manifest_digest(text)}])
        self.assertIn("input_sha256 of round row 7", a["corpus_rule"], "K15.sidechains: the row it binds")

    def test_a_report_read_through_another_tool_is_a_handback_once(self):
        rev = (_launch("tA", "aaa") + _launch("tB", "bbb")
               + [_call("tO", "TaskOutput", {"task_id": "aaa"}),
                  _result("tO", "report: gars-eval-v3 floor, per the lane-orchestrator"),
                  _call("tC", "Bash", {"command": "cat /private/tmp/claude-501/x/tasks/bbb.output"}),
                  _result("tC", "report: the haiku-prestudy is frozen"),
                  # ccc was never launched here and has no session: only its output file's name says whose it is.
                  _call("tD", "Read", {"file_path": "/private/tmp/claude-501/x/tasks/ccc.output"}),
                  _result("tD", "report: round 2's floor")])
        a = self.run_case({"study/r.md": "gars-eval-v3 floor; the haiku-prestudy is frozen\n"}, rev,
                          {"aaa": _side("aaa", []), "bbb": _side("bbb", [])})
        self.assertEqual(self.hb_row(a, "round 2's goal id"), (1, 0, 1), "K15.sidechains: TaskOutput")
        self.assertEqual(self.hb_row(a, "the operator's coordinating session"), (1, 0, 1), "K15.sidechains")
        self.assertEqual(self.hb_row(a, "the pre-study's folder name"), (1, 0, 1), "K15.sidechains: the output file")
        self.assertEqual(self.hb_row(a, "round 2's name"), (1, 0, 1), "K15.sidechains: an unlaunched agent's file")
        self.assertEqual(sorted(a["handbacks"]), ["aaa", "bbb", "ccc"], "K15.sidechains")

    def test_an_agent_result_with_no_agent_id_is_listed_and_unexplained(self):
        a = self.run_case({"study/r.md": "gars-eval-v3 sets the floor\n"},
                          [_call("tF", "Agent", {"prompt": "p"}),
                           _result("tF", "Done: gars-eval-v3 sets the floor; the lane-orchestrator said so.")], {})
        self.assertEqual(a["noid"], ["tF"], "K15.sidechains: listed")
        self.assertEqual(self.hb_row(a, "round 2's goal id"), (1, 0, 1), "K15.sidechains: never dropped")
        self.assertEqual(self.hb_row(a, "the operator's coordinating session"), (1, 0, 1), "K15.sidechains")
        self.assertIn("Agent results that name no agent: 1", a["rendered"], "K15.sidechains: in section 2")

    def test_what_a_subagent_typed_is_not_what_it_read(self):
        a = self.run_case({"study/r.md": "gars-eval-v3 floor\n"},
                          _launch("tA", "aaa") + [_hb("aaa", "gars-eval-v3 floor")],
                          {"aaa": _side("aaa", [_call("t1", "Bash", {"command": "echo gars-eval-v3 > /dev/null"}),
                                                _result("t1", "")])})
        self.assertEqual(self.hb_row(a, "round 2's goal id"), (1, 0, 1), "K15.sidechains: its own input")

    def nested(self, child_session: bool):
        sides = {"aaa": _side("aaa", _launch("tN", "nnn") + [_hb("nnn", "gars-eval-v3 floor")])}
        if child_session:
            sides["nnn"] = _side("nnn", [_call("t1", "Read", {"file_path": "@F/study/r.md"}),
                                         _result("t1", "gars-eval-v3 floor")])
        return self.run_case({"study/r.md": "gars-eval-v3 floor\n"},
                             _launch("tA", "aaa") + [_hb("aaa", "child said gars-eval-v3 floor")], sides)

    def test_a_relayed_nested_handback_traces_through_the_nested_session(self):
        self.assertEqual(self.hb_row(self.nested(True), "round 2's goal id"), (2, 2, 0), "K15.sidechains: relayed")
        a = self.nested(False)
        self.assertEqual(self.hb_row(a, "round 2's goal id"), (2, 0, 2), "K15.sidechains: nested session missing")
        self.assertEqual(a["missing"], ["nnn"], "K15.sidechains")

    def test_a_record_kept_twice_is_read_once(self):
        dup = [{"uuid": "u-1", **_att("total_tokens_reminder", content="the north star")}]
        a = self.run_case({"study/r.md": "x\n"},
                          _launch("tA", "aaa") + [dict(r, isSidechain=True, agentId="aaa") for r in dup],
                          {"aaa": _side("aaa", dup)})
        side = {r["label"]: r["un"] for r in a["side_table"]}
        self.assertEqual(side["the operator's objective line"], 1, "K15.sidechains: inline and in its file")
        bare = [_att("total_tokens_reminder", content="the north star")]
        a = self.run_case({"study/r.md": "x\n"},
                          _launch("tA", "aaa") + [dict(r, isSidechain=True, agentId="aaa") for r in bare],
                          {"aaa": _side("aaa", bare)})
        side = {r["label"]: r["un"] for r in a["side_table"]}
        self.assertEqual(side["the operator's objective line"], 1, "K15.sidechains: the same record with no uuid")
        a = self.run_case({"study/r.md": "x\n"}, _launch("tA", "aaa"), {"aaa": _side("aaa", dup + dup)})
        side = {r["label"]: r["un"] for r in a["side_table"]}
        self.assertEqual(side["the operator's objective line"], 1, "K15.sidechains: one uuid twice in one file")
        text = ('Another Claude session sent a message:\n<agent-message from="aaa">\n[Subagent hand-back] '
                "gars-eval-v3 floor\n</agent-message>")
        q = _att("queued_command", commandMode="prompt", prompt=text)
        q["rendered"] = [{"content": "<system-reminder>shown: " + text.replace("\n", " ") + "</system-reminder>"}]
        a = self.run_case({"study/r.md": "x\n"}, _launch("tA", "aaa") + [q], {"aaa": _side("aaa", [])})
        self.assertEqual(self.hb_row(a, "round 2's goal id")[0], 1, "K15.sidechains: a reflowed rendered form")

    def test_task_notifications_are_listed_apart_from_reports(self):
        note = {"type": "user", "message": {"content": "<task-notification>\n<task-id>aaa</task-id>\n<status>completed"
                                                       "</status>\n<result>not repeated here</result>"}}
        a = self.run_case({"study/r.md": "x\n"}, _launch("tA", "aaa") + [_hb("aaa", "done"), note],
                          {"aaa": _side("aaa", [])})
        self.assertEqual((len(a["reports"]), len(a["notifications"])), (1, 1), "K15.sidechains")
        self.assertIn("hand-backs carrying a report: 1", a["rendered"], "K15.sidechains")
        self.assertIn("Task notifications, listed apart: 1", a["rendered"], "K15.sidechains")

    def test_a_hit_only_in_the_brief_traces_through_what_its_author_read(self):
        brief = "Review evals/gap-study-3 and the haiku-prestudy, gars-eval-v3, and the lane-orchestrator."
        rev = [_call("tA", "Agent", {"prompt": brief}),
               _result("tA", "Async agent launched successfully.\nagentId: aaa", {"agentId": "aaa", "status": "async_launched"}),
               _call("tR", "Bash", {"command": "cat notes"}), _result("tR", "the haiku-prestudy notes; round 2 floor"),
               _hb("aaa", "see evals/gap-study-3 and the haiku-prestudy; gars-eval-v3 is the floor; the "
                          "lane-orchestrator; round 2 too; gap4.")]
        a = self.run_case({"study/evals/gap-study-3/x.py": "gap4\n"}, rev, {"aaa": _side("aaa", [])})
        rows = {r["label"]: (r["total"], r["brief"], r["un"]) for r in a["handback_table"]}
        self.assertEqual(rows["round 3's folder name"], (1, 1, 0), "K15.sidechains: in the brief and the folder")
        self.assertEqual(rows["the pre-study's folder name"], (1, 0, 1),
                         "K15.sidechains: in the brief, read by its author outside the folder: no cover")
        self.assertEqual(rows["round 2's goal id"], (1, 0, 1), "K15.sidechains: in the brief, explained for no one")
        self.assertEqual(rows["the operator's coordinating session"], (1, 0, 1), "K15.sidechains: operator")
        self.assertEqual(rows["round 2's name"], (1, 0, 1), "K15.sidechains: read by the author, not in the brief")
        self.assertEqual(rows["the round's shorthand"], (1, 0, 1), "K15.sidechains: in the folder, not in the brief")
        self.assertRegex(a["rendered"], r"traced, direct +traced via brief +UNEXPLAINED", "K15.sidechains: printed apart")

    def test_the_sources_of_a_copy_are_not_written(self):
        files = {"study/src.md": "the haiku-prestudy is frozen\n", "study/dst.md": "gars-eval-v3 floor\n"}
        reads = [_call("t1", "Bash", {"command": "cp @F/study/src.md /tmp/out/ && cp /tmp/x @F/study/dst.md"}),
                 _result("t1", ""),
                 _call("t2", "Bash", {"command": "cat @F/study/src.md @F/study/dst.md"}),
                 _result("t2", "".join(files.values()))]
        a = self.run_case(files, _launch("tA", "aaa") + [_hb("aaa", "the haiku-prestudy is frozen; gars-eval-v3 floor")],
                          {"aaa": _side("aaa", reads)})
        self.assertEqual(self.hb_row(a, "the pre-study's folder name"), (1, 1, 0), "K15.sidechains: a copy's source")
        self.assertEqual(self.hb_row(a, "round 2's goal id"), (1, 0, 1), "K15.sidechains: a copy's destination")
        run = {"study/run.py": "print('the haiku-prestudy is frozen')\n"}
        a = self.run_case(run, _launch("tA", "aaa") + [_hb("aaa", "the haiku-prestudy is frozen")],
                          {"aaa": _side("aaa", [_call("t1", "Bash", {"command": "python3 @F/study/run.py > /tmp/o.txt"}),
                                                _result("t1", ""),
                                                _call("t2", "Read", {"file_path": "@F/study/run.py"}),
                                                _result("t2", run["study/run.py"])])})
        self.assertEqual(self.hb_row(a, "the pre-study's folder name"), (1, 1, 0), "K15.sidechains: the program a redirect runs")
        self.assertEqual(a["writes"].get("aaa"), ["/tmp/o.txt"], "K15.sidechains: the redirect's target")
        a = self.run_case({"study/r.md": "x\n"}, _launch("tA", "aaa"),
                          {"aaa": _side("aaa", [_call("t1", "Bash", {"command": "cd /tmp/scr && cat > d.py <<'EOF'\nx\nEOF"}),
                                                _result("t1", "")])})
        self.assertEqual(a["writes"].get("aaa"), ["/tmp/scr/d.py"], "K15.sidechains: a write where a cd left it")

    def test_the_docstring_states_the_shared_study_word_limit(self):
        doc = " ".join(text("blindness").split('"""')[1].split())
        self.assertIn("A study word is traced by its word alone", doc, "K15.sidechains")

    def test_a_relative_write_into_the_folder_takes_its_target_out(self):
        files = {f"study/{n}": "the floor is gars-eval-v3's\n" for n in
                 ("x1.md", "x2.md", "x3.md", "brain.md", "y.md", "sub/a.md", "t/b.md", "keep.md")}
        steps = ["cd @F/study && cat > x1.md <<'EOF'\nthe floor\nEOF",
                 "cd @F/study && echo hi | tee x2.md",
                 "cat > x3.md",
                 "cd @F/study && cp -p /tmp/brain.md .",
                 "cd @F && cp -p /tmp/y.md study/y.md",
                 "cd @F/study && rsync -a /tmp/src/ sub/",
                 "cd @F/study/t && tar -xf /tmp/a.tar",
                 'grep -n "x> . y" keep.md 2>/dev/null | head -3']
        recs = []
        for i, cmd in enumerate(steps):
            rec = _call(f"t{i}", "Bash", {"command": cmd})
            rec["cwd"] = "@F/study"
            recs += [rec, _result(f"t{i}", "")]
        a = self.run_case(files, _launch("tA", "aaa"), {"aaa": _side("aaa", recs)})
        kept = {p.split("/round9/study/", 1)[1] for p in a["corpus_files"]}
        for gone in ("x1.md", "x2.md", "x3.md", "brain.md", "y.md", "sub/a.md", "t/b.md"):
            self.assertNotIn(gone, kept, f"K15.sidechains: a relative write into the folder ({gone})")
        self.assertIn("keep.md", kept, "K15.sidechains: a file nothing wrote stays")

    def test_section_6_reads_out_arguments_extractions_and_every_redirect(self):
        files = {"study/a.tar": "x\n"}
        steps = ["python3 /tmp/w.py --out /tmp/res.json > /tmp/log.txt", "cd /tmp/w && tar -xf @F/study/a.tar",
                 "cat /tmp/a &> /tmp/b", "echo x >> /tmp/c", "grep -o foo /tmp/d",
                 "cat > /tmp/h.txt <<'EOF'\nif a > b: pass\nEOF", "cd /tmp/m;\ntouch n.txt"]
        recs = []
        for i, cmd in enumerate(steps):
            rec = _call(f"t{i}", "Bash", {"command": cmd})
            rec["cwd"] = "/tmp/g"
            recs += [rec, _result(f"t{i}", "")]
        a = self.run_case(files, _launch("tA", "aaa"), {"aaa": _side("aaa", recs)})
        self.assertEqual(a["writes"].get("aaa"), ["/tmp/b", "/tmp/c", "/tmp/h.txt", "/tmp/log.txt", "/tmp/m/n.txt",
                                                  "/tmp/res.json", "/tmp/w"],
                         "K15.sidechains: section 6's writes")
        self.assertTrue(any(p.endswith("/study/a.tar") for p in a["corpus_files"]), "K15.sidechains: an archive is read")

    def test_the_manifest_is_written_before_the_row_is_hashed(self):
        rounds = load_isolated(FILES["rounds"], "review_kit_rounds_for_test", MUTATED.get("rounds"))
        lk = load_launch()
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            folder = root / "f"
            (folder / "study" / ".git").mkdir(parents=True)
            (folder / "BRIEF.md").write_text("b\n")
            (folder / "study" / "x.py").write_text("x\n")
            (folder / "study" / ".git" / "HEAD").write_text("ref\n")
            listing = rounds.write_manifest(folder)
            side = root / "f-launch"
            self.assertEqual((side / "folder-manifest.txt").read_text(), listing, "K15.sidechains: written beside it")
            # The row's digest, as round 3's folder_sha256 computed it, must not move.
            h = hashlib.sha256()
            for rel, body in (("BRIEF.md", b"b\n"), ("study/x.py", b"x\n")):
                h.update(rel.encode() + b"\0" + hashlib.sha256(body).digest())
            self.assertEqual(rounds.folder_sha256(folder), h.hexdigest(), "K15.sidechains: the row digest is unchanged")
            self.assertEqual(rounds.manifest_digest(listing), h.hexdigest(), "K15.sidechains: the manifest reproduces it")
            self.assertEqual(load_blindness().manifest_digest(listing), h.hexdigest(), "K15.sidechains: blindness reads it")
            self.assertEqual(lk.manifest_problems(folder, side, rounds), [], "K15.sidechains: an unchanged folder")
            (folder / "study" / "x.py").write_text("changed\n")
            self.assertEqual(len(lk.manifest_problems(folder, side, rounds)), 1, "K15.sidechains: a changed folder")
            (side / "folder-manifest.txt").unlink()
            self.assertEqual(len(lk.manifest_problems(folder, side, rounds)), 1, "K15.sidechains: no manifest")
        add = text_of_def(text("rounds"), "add")
        self.assertIn("    manifest = write_manifest(folder)\n", add, "K15.sidechains: --add writes it")
        self.assertIn('"input_sha256": manifest_digest(manifest),', add, "K15.sidechains: the row hashes it")
        main = text_of_def(text("launch"), "main")
        self.assertIn("    stale = manifest_problems(folder, side, load_rounds())\n", main, "K15.sidechains: launch checks it")
        self.assertLess(main.index("manifest_problems(folder, side, load_rounds())"), main.index('(side / "SESSION")'),
                        "K15.sidechains: the launch checks it before the session")


def mutants():
    """name -> (test id, clause, file key, old, new). Each weakens one property; old occurs exactly once."""
    return {
        "brief-round3-bytes": ("Port.test_the_bytes_under_review_are_round_4s", "K1.port", "brief",
                               "a copy of `study/evals/gap-study-4/prereg-draft.json`",
                               "a copy of `study/evals/gap-study-3/prereg-draft.json`"),
        "brief-round3-command": ("Port.test_every_command_path_is_round_4s", "K1.port", "brief",
                                 "`python3 evals/gap-study-4/prereg.py --status`",
                                 "`python3 evals/gap-study-3/prereg.py --status`"),
        "launch-round3-usage": ("Port.test_the_usage_lines_are_round_4s", "K1.port", "launch",
                                "python3 evals/gap-study-4/review_kit/launch.py <review folder> [<session id>]",
                                "python3 evals/gap-study-3/review_kit/launch.py <review folder> [<session id>]"),
        "why-names-round": ("Port.test_why_names_no_study_folder_or_round", "K1.port", "why",
                            "So this round is a new instrument", "So round 4 is a new instrument"),
        "marker-dropped": ("Markers.test_round_4_leads_and_every_earlier_marker_stays", "K2.markers", "blindness",
                           '    ("round 3\'s folder name", "gap-study-3"),\n', ""),
        "marker-in-claude-md": ("Markers.test_no_marker_occurs_in_a_tracked_claude_md", "K3.nested", "blindness",
                                '    ("the operator\'s list system", "OrgOS"),\n',
                                '    ("the operator\'s list system", "OrgOS"),\n    ("x", "README"),\n'),
        "no-threat-model": ("Brief.test_the_threat_model_is_stated", "K4.brief", "brief",
                            "**The agent under test, during a take**", "The agent under test"),
        "walk-gate-dropped": ("Brief.test_every_heavy_gate_of_the_rehearsal_is_handed_in", "K4.brief", "brief",
                              ", `run.py --walks --check` and `walk_regrade.py --check`)", ")"),
        "round3-classes": ("Brief.test_the_three_legs_and_the_stop_rule_classes", "K4.brief", "brief",
                           "MAJOR, MINOR or NIT", "BLOCKER, SHOULD or NIT"),
        "heavy-run-here": ("Light.test_every_light_command_exists_and_takes_its_flag", "K5.light", "brief",
                           "   - `python3 evals/gap-study-4/prereg.py --status`\n",
                           "   - `python3 evals/gap-study-4/prereg.py --status`\n"
                           "   - `python3 evals/gap-study-4/run.py --check`\n"),
        "model-fable": ("Model.test_the_reviewer_is_opus_5_5", "K7.model", "launch",
                        'MODEL = "claude-opus-5-5"', 'MODEL = "claude-fable-5-1"'),
        "coauthor-fable": ("Model.test_the_reviewer_is_opus_5_5", "K7.model", "commit_review",
                           "Co-Authored-By: Claude Opus 5.5", "Co-Authored-By: Claude Fable 5.1"),
        "athena-other-commit": ("Athena.test_what_cannot_be_evidence_at_this_commit_is_refused", "K8.athena",
                                "build_kit", "if f\"commit: {head}\" not in body.splitlines():", "if False:"),
        "athena-dotfile": ("Athena.test_what_cannot_be_evidence_at_this_commit_is_refused", "K8.athena",
                           "build_kit", 'if p.name.startswith("."):', "if False:"),
        "athena-marker": ("Athena.test_what_cannot_be_evidence_at_this_commit_is_refused", "K8.athena",
                          "build_kit", "for m in athena_markers():", "for m in ():"),
        "athena-half-built": ("Athena.test_main_requires_the_outputs_and_cleans_a_half_built_folder", "K8.athena",
                              "build_kit", "        shutil.rmtree(folder)\n", ""),
        "env-inherited": ("Env.test_the_environment_is_an_allowlist", "K10.env", "launch",
                          "    env = {k: source[k] for k in ALLOWED_ENV if k in source}",
                          "    env = dict(source)"),
        "env-values-recorded": ("Env.test_the_names_passed_are_recorded_without_values", "K10.env", "launch",
                                '"".join(f"{k}\\n" for k in sorted(env))',
                                '"".join(f"{k}={v}\\n" for k, v in sorted(env.items()))'),
        "no-athena-check": ("Folder.test_launch_refuses_a_folder_without_athena_or_commit", "K10.env", "launch",
                            'if not (folder / "athena").is_dir() or not any((folder / "athena").iterdir()):',
                            "if False:"),
        "effort-dropped-on-resume": ("Effort.test_launch_and_resume_pass_effort_medium", "K11.effort", "launch",
                                     '"none", *drive.ISOLATION_FLAGS, *DISALLOW, "--effort", EFFORT,',
                                     '"none", *drive.ISOLATION_FLAGS, *DISALLOW,'),
        "producer-no-commit-line": ("Producer.test_each_file_carries_its_lines_and_passes_the_kit_check",
                                    "K12.producer", "producer", 'f"commit: {head}\\n"', 'f"sha: {head}\\n"'),
        "battery-other-commit": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                                 "producer", "if m.group(1) != head:", "if False:"),
        "battery-summary-anywhere": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused",
                                     "K13.battery", "producer", "if len(closing) != 1 or closing[0] != len(lines) - 1:",
                                     "if not closing:"),
        "battery-exit-forced": ("Battery.test_the_battery_copy_is_the_run_checks_gate", "K13.battery", "producer",
                                "code = run_checks.verdict(k, n)", "code = 0"),
        "battery-inside-repo": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                                "producer", "if path.resolve().is_relative_to(repo.resolve()):", "if False:"),
        "battery-any-count": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                              "producer", "    if n != whole:\n", "    if False:\n"),
        "battery-relative-taken": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                                   "producer", "if not path.is_absolute():", "if False:"),
        "battery-count-commands-only": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused",
                                        "K13.battery", "producer",
                                        "whole = len(run_checks.commands()) + len(run_checks.file_problems())",
                                        "whole = len(run_checks.commands())"),
        "battery-tree-anywhere": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                                  "producer", "if len(lines) < 2 or lines[-2] != TREE_UNCHANGED:",
                                  "if TREE_UNCHANGED not in lines:"),
        "battery-tree-ignored": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                                 "producer", "if len(lines) < 2 or lines[-2] != TREE_UNCHANGED:", "if False:"),
        "battery-link-taken": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                               "producer", "if path.is_symlink() or not path.is_file():", "if not path.exists():"),
        "workflow-allowed": ("Workflow.test_launch_and_resume_disallow_the_workflow_tool", "K14.workflow", "launch",
                             '*drive.ISOLATION_FLAGS, *DISALLOW, "--effort", EFFORT, "--output-format", "stream-json",\n'
                             '            "--verbose", "--session-id", session_id]',
                             '*drive.ISOLATION_FLAGS, "--effort", EFFORT, "--output-format", "stream-json",\n'
                             '            "--verbose", "--session-id", session_id]'),
        "smoke-tools-unread": ("Workflow.test_the_smoke_checks_the_tool_list_and_cites_the_probe", "K14.workflow",
                               "readme", "lists no `Workflow` tool", "lists its tools"),
        "readme-bare-python": ("Battery.test_the_readme_names_the_interpreter_and_the_suite_road", "K13.battery",
                               "readme", "2. Build the folder outside the Brain and this repository: `python3.12 ",
                               "2. Build the folder outside the Brain and this repository: `python3 "),
        "builtin-list-dropped": ("Smoke.test_the_operator_notes_require_the_skills_smoke", "K9.smoke", "readme",
                                 "BUILT-IN SKILLS: ", "Built-in skills: "),
        "brief-outcomes-key": ("Brief.test_every_draft_key_the_brief_names_exists", "K4.brief", "brief",
                               "Read the draft's `views`, `routes` and `stop_taxonomy`",
                               "Read the draft's `outcomes`, `routes` and `stop_taxonomy`"),
        "athena-optional": ("Athena.test_main_requires_the_outputs_and_cleans_a_half_built_folder", "K8.athena", "build_kit",
                            'ap.add_argument("--athena", type=Path, required=True)',
                            'ap.add_argument("--athena", type=Path, required=False)'),
        "smoke-dropped": ("Smoke.test_the_operator_notes_require_the_skills_smoke", "K9.smoke", "readme",
                          "## Before round 1: the skills smoke", "## Before round 1"),
        "person-named": ("Public.test_no_absolute_path_and_no_person", "K6.public", "why",
                         "The adversarial reader's first lens is this page.",
                         "The adversarial reader's first lens is this page, written for Javier."),
        "sidechains-unread": ("Sidechains.test_every_sidechain_is_found_and_one_nothing_launched_is_still_read", "K15.sidechains", "blindness",
                '    for f in sorted((main.parent / main.stem / "subagents").glob("agent-*.jsonl")):',
                '    for f in []:'),
        "unlaunched-ignored": ("Sidechains.test_every_sidechain_is_found_and_one_nothing_launched_is_still_read", "K15.sidechains", "blindness",
                '"unlaunched": sorted(set(side) - launched)',
                '"unlaunched": []'),
        "launch-text-unread": ("Sidechains.test_every_sidechain_is_found_and_one_nothing_launched_is_still_read", "K15.sidechains", "blindness",
                'aid = str(tur.get("agentId") or (m.group(1) if m else ""))',
                'aid = str(tur.get("agentId") or "")'),
        "side-context-unscanned": ("Sidechains.test_every_sidechain_is_found_and_one_nothing_launched_is_still_read", "K15.sidechains", "blindness",
                '    side_ctx = [line for s in side.values() for line in s.ctx]',
                '    side_ctx = []'),
        "handback-folder-only": ("Sidechains.test_a_handback_hit_not_traced_is_unexplained", "K15.sidechains", "blindness",
                'any(c in in_folder and read_there(h["aid"], c, side)',
                'any(c in in_folder'),
        "handback-read-only": ("Sidechains.test_a_handback_hit_not_traced_is_unexplained", "K15.sidechains", "blindness",
                'any(c in in_folder and read_there(h["aid"], c, side)',
                'any(read_there(h["aid"], c, side)'),
        "outside-path-traced": ("Sidechains.test_a_handback_hit_not_traced_is_unexplained", "K15.sidechains", "blindness",
                '        else:\n            return []\n',
                '        else:\n            pass\n'),
        "quotes-uncapped": ("Sidechains.test_a_handback_hit_not_traced_is_unexplained", "K15.sidechains", "blindness",
                'mask(h["quote"], str(folder))[:120])',
                'mask(h["quote"], str(folder)))'),
        "launch-listing-ignored": ("Sidechains.test_the_reviewers_own_writes_are_never_the_folder_it_was_given", "K15.sidechains", "blindness",
                'tops = ([folder / n for n in listing.read_text().split("\\n") if n.strip()] if listing.is_file()\n            else sorted(folder.iterdir()))',
                'tops = sorted(folder.iterdir())'),
        "operator-traced": ("Sidechains.test_an_operator_marker_is_never_explained", "K15.sidechains", "blindness",
                '        if h["op"]:\n            h["via"] = None\n        elif any(',
                '        if False:\n            h["via"] = None\n        elif any('),
        "operator-beside-folder": ("Sidechains.test_an_operator_marker_is_never_explained", "K15.sidechains", "blindness",
                '            if operator:\n                un += 1\n            elif kind',
                '            if False:\n                un += 1\n            elif kind'),
        "operator-rows-off": ("Sidechains.test_an_operator_marker_is_never_explained", "K15.sidechains", "blindness",
                '[(label, w, w in OPERATOR) for',
                '[(label, w, False) for'),
        "handback-user-unread": ("Sidechains.test_handbacks_are_read_whichever_record_carries_them", "K15.sidechains", "blindness",
                '                    elif b.get("type") == "text":',
                '                    elif False:'),
        "handback-queued-twice": ("Sidechains.test_handbacks_are_read_whichever_record_carries_them", "K15.sidechains", "blindness",
                '                        self.handbacks.append((hb[0], shown, hb[1]))\n                        continue\n',
                '                        self.handbacks.append((hb[0], shown, hb[1]))\n'),
        "handback-sync-unread": ("Sidechains.test_handbacks_are_read_whichever_record_carries_them", "K15.sidechains", "blindness",
                'if tur.get("status") != "async_launched" and "Async agent launched" not in body:',
                'if False:'),
        "side-paths-unscanned": ("Sidechains.test_paths_outside_and_writes_outside_are_listed_per_session", "K15.sidechains", "blindness",
                '"side_outside": {aid: outside_paths(s, folder) for aid, s in side.items()},',
                '"side_outside": {aid: set() for aid in side},'),
        "writes-section-dropped": ("Sidechains.test_paths_outside_and_writes_outside_are_listed_per_session", "K15.sidechains", "blindness",
                'f"6. Writes outside the folder: {n_w}',
                'f"6. Outside: {n_w}'),
        "isolation-skills-assumed": ("Sidechains.test_the_isolation_the_records_show", "K15.sidechains", "blindness",
                '"skills_as_reviewer": None if s.skills is None else set(s.skills) == skills',
                '"skills_as_reviewer": True'),
        "queued-read-twice": ("Sidechains.test_a_handback_hit_not_traced_is_unexplained", "K15.sidechains", "blindness",
                '                    if squash(text) not in squash(shown):\n', '                    if True:\n'),
        "tail-keeps-dropped-marker": ("SidechainFolds.test_a_path_tail_that_drops_the_marker_explains_nothing", "K15.sidechains", "blindness",
                '    return [c for c in [ext] + tails if marker in c]',
                '    return [ext] + tails'),
        "mtime-ignored": ("SidechainFolds.test_a_file_newer_than_the_launch_stamp_is_not_the_folder", "K15.sidechains", "blindness",
                '    newer = [p for p in files if stamp is not None and p.stat().st_mtime_ns > stamp]',
                '    newer = []'),
        "rule-unprinted": ("SidechainFolds.test_a_file_newer_than_the_launch_stamp_is_not_the_folder", "K15.sidechains", "blindness",
                '            f"   The folder as it stood at launch: {a[\'corpus_rule\']}.", "",\n',
                '            "",\n'),
        "manifest-ignored": ("SidechainFolds.test_with_a_manifest_only_its_unchanged_files_are_the_folder", "K15.sidechains", "blindness",
                '    if manifest.is_file():',
                '    if False:'),
        "manifest-hash-unchecked": ("SidechainFolds.test_with_a_manifest_only_its_unchanged_files_are_the_folder", "K15.sidechains", "blindness",
                '            if hashlib.sha256(p.read_bytes()).hexdigest() == sha:',
                '            if True:'),
        "taskoutput-unread": ("SidechainFolds.test_a_report_read_through_another_tool_is_a_handback_once", "K15.sidechains", "blindness",
                'aid = (out or named or [None])[0]',
                'aid = (out or [None])[0]'),
        "output-file-unread": ("SidechainFolds.test_a_report_read_through_another_tool_is_a_handback_once", "K15.sidechains", "blindness",
                'aid = (out or named or [None])[0]',
                'aid = (named or [None])[0]'),
        "noid-dropped": ("SidechainFolds.test_an_agent_result_with_no_agent_id_is_listed_and_unexplained", "K15.sidechains", "blindness",
                '            self.handbacks.append((f"(no agent id, {tid})", body, "report"))\n',
                ''),
        "noid-unlisted": ("SidechainFolds.test_an_agent_result_with_no_agent_id_is_listed_and_unexplained", "K15.sidechains", "blindness",
                '"noid": [t for s in sessions for t in s.noid],',
                '"noid": [],'),
        "inputs-read": ("SidechainFolds.test_what_a_subagent_typed_is_not_what_it_read", "K15.sidechains", "blindness",
                '        self.traffic = "\\n".join(self.results).lower()',
                '        self.traffic = "\\n".join(self.results + self.inputs).lower()'),
        "nested-unfollowed": ("SidechainFolds.test_a_relayed_nested_handback_traces_through_the_nested_session", "K15.sidechains", "blindness",
                '    return any(c in text.lower() and read_there(child, c, side, seen | {aid}) for child, text, _ in s.handbacks)',
                '    return False'),
        "nested-missing-explains": ("SidechainFolds.test_a_relayed_nested_handback_traces_through_the_nested_session", "K15.sidechains", "blindness",
                '    if aid in seen or aid not in side:\n        return False\n',
                '    if aid in seen:\n        return False\n    if aid not in side:\n        return True\n'),
        "record-no-uuid-twice": ("SidechainFolds.test_a_record_kept_twice_is_read_once", "K15.sidechains", "blindness",
                '        inline[aid] = [x for x in lines if bare(x) not in in_file]',
                '        inline[aid] = lines'),
        "record-read-twice": ("SidechainFolds.test_a_record_kept_twice_is_read_once", "K15.sidechains", "blindness",
                '            if key and key in seen:\n                continue\n',
                '            if False:\n                continue\n'),
        "reflow-read-twice": ("SidechainFolds.test_a_record_kept_twice_is_read_once", "K15.sidechains", "blindness",
                '                    if squash(text) not in squash(shown):\n',
                '                    if text not in shown:\n'),
        "shared-word-unstated": ("SidechainFolds.test_the_docstring_states_the_shared_study_word_limit", "K15.sidechains", "blindness",
                'reports. A study word is traced by\nits word alone',
                'reports.\nIts word alone'),
        "notification-as-report": ("SidechainFolds.test_task_notifications_are_listed_apart_from_reports", "K15.sidechains", "blindness",
                '    return (m.group(1), "notification") if m else None',
                '    return (m.group(1), "report") if m else None'),
        "section-4-counts-notifications": ("SidechainFolds.test_task_notifications_are_listed_apart_from_reports", "K15.sidechains", "blindness",
                'f"4. Sub-agent hand-backs carrying a report: {len(a[\'reports\'])}',
                'f"4. Sub-agent hand-backs carrying a report: {len(a[\'reports\']) + len(a[\'notifications\'])}'),
        "brief-route-off": ("SidechainFolds.test_a_hit_only_in_the_brief_traces_through_what_its_author_read", "K15.sidechains", "blindness",
                '        elif h["aid"] in briefs and any(',
                '        elif False and any('),
        "brief-unprinted": ("SidechainFolds.test_a_hit_only_in_the_brief_traces_through_what_its_author_read", "K15.sidechains", "blindness",
                "{'traced via brief':>17}",
                "{'via':>17}"),
        "written-in-corpus": ("Sidechains.test_the_reviewers_own_writes_are_never_the_folder_it_was_given", "K15.sidechains", "blindness",
                '    by_write = [p for p in files if p not in newer_set and written_over(p, written)]',
                '    by_write = []'),
        "shell-writes-unread": ("Sidechains.test_paths_outside_and_writes_outside_are_listed_per_session", "K15.sidechains", "blindness",
                '                for t, is_dir in shell_targets(words, redirected):',
                '                for t, is_dir in []:'),
        "shell-write-inside-kept": ("SidechainFolds.test_a_file_a_shell_command_wrote_inside_the_folder_is_not_the_folder", "K15.sidechains", "blindness",
                '            if is_dir is not None:\n                self.written_inside.add(',
                '            if False:\n                self.written_inside.add('),
        "manifest-after-row": ("SidechainFolds.test_the_manifest_is_written_before_the_row_is_hashed", "K15.sidechains", "rounds",
                '"input_sha256": manifest_digest(manifest),',
                '"input_sha256": folder_sha256(folder),'),
        "manifest-keeps-git": ("SidechainFolds.test_the_manifest_is_written_before_the_row_is_hashed", "K15.sidechains", "rounds",
                '        if rel == "study/.git" or rel.startswith("study/.git/"):\n            continue\n',
                ''),
        "manifest-digest-differs": ("SidechainFolds.test_the_manifest_is_written_before_the_row_is_hashed", "K15.sidechains", "rounds",
                '        h.update(b"\\0")\n',
                ''),
        "launch-manifest-unchecked": ("SidechainFolds.test_the_manifest_is_written_before_the_row_is_hashed", "K15.sidechains", "launch",
                '    stale = manifest_problems(folder, side, load_rounds())\n',
                '    stale = []\n'),
        "launch-stale-taken": ("SidechainFolds.test_the_manifest_is_written_before_the_row_is_hashed", "K15.sidechains", "launch",
                '    if rounds.manifest_text(folder) != m.read_text():',
                '    if False:'),
        "row-binding-unread": ("SidechainFolds.test_with_a_manifest_only_its_unchanged_files_are_the_folder", "K15.sidechains", "blindness",
                'rows = [r["n"] for r in register_rows() if r.get("input_sha256") == digest]',
                'rows = [r["n"] for r in register_rows()]'),
        "brief-author-read-counts": ("SidechainFolds.test_a_hit_only_in_the_brief_traces_through_what_its_author_read", "K15.sidechains", "blindness",
                'any(c in briefs[h["aid"]][1] and c in in_folder for c in cs)',
                'any(c in briefs[h["aid"]][1] and (c in in_folder or c in briefs[h["aid"]][0].traffic) for c in cs)'),
        "brief-corpus-ignored": ("SidechainFolds.test_a_hit_only_in_the_brief_traces_through_what_its_author_read", "K15.sidechains", "blindness",
                'any(c in briefs[h["aid"]][1] and c in in_folder for c in cs)',
                'any(c in briefs[h["aid"]][1] and False for c in cs)'),
        "brief-not-required": ("SidechainFolds.test_a_hit_only_in_the_brief_traces_through_what_its_author_read", "K15.sidechains", "blindness",
                'any(c in briefs[h["aid"]][1] and c in in_folder for c in cs)',
                'any(c in in_folder for c in cs)'),
        "copy-sources-written": ("SidechainFolds.test_the_sources_of_a_copy_are_not_written", "K15.sidechains", "blindness",
                '            out += [(dest.rstrip("/") + "/" + os.path.basename(src.rstrip("/")), True) for src in plain[:-1]]',
                '            out += [(a, True) for a in plain]'),
        "cd-write-unseen": ("SidechainFolds.test_the_sources_of_a_copy_are_not_written", "K15.sidechains", "blindness",
                '                if words[:1] in (["cd"], ["pushd"]):',
                '                if False:'),
        "redirect-runs-written": ("SidechainFolds.test_the_sources_of_a_copy_are_not_written", "K15.sidechains", "blindness",
                '    if verb not in READERS:\n',
                '    out += [(w, False) for w in words if w.startswith("/")]\n    if verb not in READERS:\n'),
        "record-cwd-ignored": ("SidechainFolds.test_a_relative_write_into_the_folder_takes_its_target_out", "K15.sidechains", "blindness",
                'self.note_writes(name, inp, folder, rec.get("cwd"))',
                'self.note_writes(name, inp, folder)'),
        "relative-inside-dropped": ("SidechainFolds.test_a_relative_write_into_the_folder_takes_its_target_out", "K15.sidechains", "blindness",
                '        p = t if t.startswith("/") else (os.path.normpath(os.path.join(cwd, t)) if cwd else None)',
                '        p = t if t.startswith("/") else None'),
        "folder-target-keeps-files": ("SidechainFolds.test_a_relative_write_into_the_folder_takes_its_target_out", "K15.sidechains", "blindness",
                '    return str(r) in written or any(str(q) in written for q in r.parents)',
                '    return str(r) in written'),
        "tee-missed": ("SidechainFolds.test_a_relative_write_into_the_folder_takes_its_target_out", "K15.sidechains", "blindness",
                '    elif verb in ("tee", "touch"):\n        out += [(a, False) for a in plain]\n',
                '    elif verb in ("tee", "touch"):\n        pass\n'),
        "rsync-missed": ("SidechainFolds.test_a_relative_write_into_the_folder_takes_its_target_out", "K15.sidechains", "blindness",
                '    elif verb == "rsync" and len(plain) >= 2:\n        out.append((plain[-1], True))\n',
                '    elif verb == "rsync" and len(plain) >= 2:\n        pass\n'),
        "tar-missed": ("SidechainFolds.test_section_6_reads_out_arguments_extractions_and_every_redirect", "K15.sidechains", "blindness",
                '        out.append((args[args.index("-C") + 1] if "-C" in args[:-1] else ".", True))',
                '        pass'),
        "out-arg-missed": ("SidechainFolds.test_section_6_reads_out_arguments_extractions_and_every_redirect", "K15.sidechains", "blindness",
                '            if a in ("-o", "--out", "--output") and i + 1 < len(args):',
                '            if False:'),
        "reader-o-taken": ("SidechainFolds.test_section_6_reads_out_arguments_extractions_and_every_redirect", "K15.sidechains", "blindness",
                '    if verb not in READERS:\n',
                '    if True:\n'),
        "amp-redirect-missed": ("SidechainFolds.test_section_6_reads_out_arguments_extractions_and_every_redirect", "K15.sidechains", "blindness",
                'REDIRECTS = {">", ">>", "&>", "&>>", ">|"}',
                'REDIRECTS = {">", ">>", ">|"}'),
        "append-redirect-missed": ("SidechainFolds.test_section_6_reads_out_arguments_extractions_and_every_redirect", "K15.sidechains", "blindness",
                'REDIRECTS = {">", ">>", "&>", "&>>", ">|"}',
                'REDIRECTS = {">", "&>", "&>>", ">|"}'),
        "heredoc-body-read": ("SidechainFolds.test_section_6_reads_out_arguments_extractions_and_every_redirect", "K15.sidechains", "blindness",
                '    lex = shlex.shlex(HEREDOC.sub(r"\\1", cmd), posix=True',
                '    lex = shlex.shlex(cmd, posix=True'),
        "quote-blind-steps": ("SidechainFolds.test_a_relative_write_into_the_folder_takes_its_target_out", "K15.sidechains", "blindness",
                '        tokens = list(lex)\n',
                '        tokens = HEREDOC.sub(r"\\1", cmd).replace("|", " | ").replace(">", " > ").split()\n'),
        "merged-breaks-missed": ("SidechainFolds.test_section_6_reads_out_arguments_extractions_and_every_redirect", "K15.sidechains", "blindness",
                '        if t in STEP_BREAKS or (t and set(t) <= set("();|&\\n")):',
                '        if t in STEP_BREAKS:'),
        "isolation-memory-ignored": ("Sidechains.test_the_isolation_the_records_show", "K15.sidechains", "blindness",
                '                    self.memory_outside += 1',
                '                    pass'),
    }


def run_witnesses() -> int:
    red = 0
    table = mutants()
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    MUTATED.clear()
    base = unittest.TestResult()
    for test_id in sorted({entry[0] for entry in table.values()}):
        cls, meth = test_id.split(".")
        globals()[cls](meth).run(base)
    mutation_baseline.require_no_lines("test_review_kit witnesses",
                                       [f"{kind} {t.id()}" for kind, pairs in (("FAIL", base.failures),
                                        ("ERROR", base.errors)) for t, _ in pairs])
    for name, (test_id, clause, key, old, new) in table.items():
        src = FILES[key].read_text()
        if src.count(old) != 1:
            print(f"witness {name}: FAIL; its old text occurs {src.count(old)} times in {FILES[key].name}")
            continue
        MUTATED[key] = src.replace(old, new)
        try:
            cls, meth = test_id.split(".")
            result = unittest.TestResult()
            globals()[cls](meth).run(result)
        finally:
            MUTATED.clear()
        failed = [f for _, f in result.failures if "AssertionError" in f and clause in f]
        ok = bool(failed) and not result.errors
        red += ok
        print(f"witness {name} -> {test_id} {clause}: {'RED' if ok else 'FAIL'}", flush=True)
    print(f"test_review_kit witnesses: {red}/{len(table)} red; registry {len(table)}", flush=True)
    return 0 if red == len(table) else 1


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses())
    unittest.main(verbosity=1)
