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

Folds of glitch-f1's rulings on the first hand-back (Wed 21 Oct 2026): K7, K8 and K9 were written red first.
Folds of the review of c41b7d50 (REVIEW-review-kit-port-c41b7d5.md, glitch-f1's rulings): K10, K11, K12 and the
tightened K8 (a commit line, not the sha anywhere; no dotfile, absolute home path, person or operator marker; the
half-built folder removed) and K9 (the built-in list, effort, environment names) were written red first.

Lane prefreeze-road (the Lane-orchestrator's ruling of Sat 24 Oct 2026, under Javier's standing delegation, after the
pre-freeze round's remote outputs came back with environment reds): K13 was written red first.

Reads committed files only; no model, network, container or take. Interpreter state (sys.modules, sys.path,
os.environ, cwd) is left as found.

--witnesses runs every mutant in this process: each swaps one file's text as the tests read it, and requires its
bound test to fail by an AssertionError carrying its clause token.
"""
from __future__ import annotations

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
         "commit_review": KIT / "commit_review.py", "build_kit": KIT / "build_kit.py", "readme": KIT / "README.md",
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
        inside = REPO / "evals" / "gap-study-4" / "no-such-battery-copy.out"
        link = self.root / "l.out"
        os.symlink(self.copy(good, name="real.out"), link)
        (self.root / "nohead.out").write_text(good)
        (self.root / "nojobs.out").write_text(f"athena-suite: battery commit {self.HEAD}\n" + good)
        cases = {
            "missing": self.root / "absent.out",
            "a link": link,
            "inside the repository": inside,
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
                why, gate = self.pr.battery_gate(path, self.HEAD, self.rc, REPO)
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
                                     '"none", *drive.ISOLATION_FLAGS, "--effort", EFFORT,',
                                     '"none", *drive.ISOLATION_FLAGS,'),
        "producer-no-commit-line": ("Producer.test_each_file_carries_its_lines_and_passes_the_kit_check",
                                    "K12.producer", "producer", 'f"commit: {head}\\n"', 'f"sha: {head}\\n"'),
        "battery-other-commit": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                                 "producer", "if m.group(1) != head:", "if False:"),
        "battery-summary-anywhere": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused",
                                     "K13.battery", "producer", "if len(closing) != 1 or closing[0] != len(lines) - 1:",
                                     "if not closing:"),
        "battery-exit-forced": ("Battery.test_the_battery_copy_is_the_run_checks_gate", "K13.battery", "producer",
                                "code = run_checks.verdict(k, n)", "code = 0"),
        "battery-link-taken": ("Battery.test_a_copy_that_cannot_be_bound_to_this_head_is_refused", "K13.battery",
                               "producer", "if path.is_symlink() or not path.is_file():", "if not path.exists():"),
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
    }


def run_witnesses() -> int:
    red = 0
    table = mutants()
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
