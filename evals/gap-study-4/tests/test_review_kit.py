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
  K9.smoke     the operator notes require a one-turn skills smoke before round 1 and say what it must show

Folds of glitch-f1's rulings on the first hand-back (Wed 21 Oct 2026): K7, K8 and K9 were written red first.

Reads committed files only; no model, network, container or take. Interpreter state (sys.modules, sys.path,
os.environ, cwd) is left as found.

--witnesses runs every mutant in this process: each swaps one file's text as the tests read it, and requires its
bound test to fail by an AssertionError carrying its clause token.
"""
from __future__ import annotations

import atexit  # noqa: F401  (TemporaryDirectory's weakref.finalize imports it lazily; loaded here so no test adds a module)
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
KIT = HERE / "review_kit"
REPO = HERE.parent.parent
FILES = {"brief": KIT / "BRIEF.md", "why": KIT / "why.md", "blindness": KIT / "blindness.py",
         "launch": KIT / "launch.py", "rehearsal": HERE / "freeze_rehearsal.py",
         "commit_review": KIT / "commit_review.py", "build_kit": KIT / "build_kit.py", "readme": KIT / "README.md"}
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


def load_isolated(path: Path, name: str):
    """Execute a kit module by path and give interpreter state back exactly as found."""
    saved_path, saved_mods = list(sys.path), set(sys.modules)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
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
    if "build_kit" not in MUTATED:
        return load_isolated(FILES["build_kit"], "review_kit_build_kit_for_test")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "build_kit.py"
        p.write_text(MUTATED["build_kit"])
        saved = list(sys.path)
        sys.path.insert(0, str(HERE))
        try:
            return load_isolated(p, "review_kit_build_kit_mutant")
        finally:
            sys.path[:] = saved


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

    def test_the_outputs_are_copied_in(self):
        self.put("run_checks.txt", f"command: run_checks.py\ncommit: {self.HEAD}\nrun_checks: 9 of 9 commands passed\n")
        self.put("freeze-check.txt", f"commit {self.HEAD}\nfreeze: 531 owned paths checked\n")
        problems, copied = self.bk.copy_athena(self.src, self.dest, self.HEAD)
        self.assertEqual(problems, [], "K8.athena")
        self.assertEqual(sorted(copied), ["freeze-check.txt", "run_checks.txt"], "K8.athena")
        for name in copied:
            self.assertEqual((self.dest / "athena" / name).read_bytes(), (self.src / name).read_bytes(), "K8.athena")

    def test_what_cannot_be_evidence_at_this_commit_is_refused(self):
        cases = {
            "missing": lambda: None,
            "empty folder": lambda: None,
            "other commit": lambda: self.put("a.txt", "commit " + "f" * 40 + "\nok\n"),
            "empty file": lambda: self.put("a.txt", ""),
            "nested folder": lambda: ((self.src / "sub").mkdir(), self.put("sub/b.txt", self.HEAD)),
            "link": lambda: (self.put("real.txt", self.HEAD), os.symlink(self.src / "real.txt", self.src / "l.txt")),
        }
        for case, arrange in cases.items():
            with self.subTest(case=case):
                for p in sorted(self.src.rglob("*"), reverse=True):
                    p.unlink() if (p.is_file() or p.is_symlink()) else p.rmdir()
                shutil_rm(self.dest / "athena")
                arrange()
                src = self.root / "absent" if case == "missing" else self.src
                problems, copied = self.bk.copy_athena(src, self.dest, self.HEAD)
                self.assertTrue(problems, f"K8.athena: {case} was accepted")
                self.assertFalse((self.dest / "athena").exists(), f"K8.athena: {case} left a partial athena/")

    def test_main_requires_the_outputs(self):
        src = text("build_kit")
        self.assertIsNotNone(re.search(r'add_argument\("--athena",[^)]*required=True', src), "K8.athena")
        main = src.split("def main()", 1)[1]
        self.assertLess(main.index("copy_athena("), main.index("folder.mkdir("), "K8.athena: checked after the folder exists")


def shutil_rm(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)


class Smoke(unittest.TestCase):
    def test_the_operator_notes_require_the_skills_smoke(self):
        r = text("readme")
        self.assertIn("## Before round 1: the skills smoke", r, "K9.smoke")
        section = r.split("## Before round 1: the skills smoke", 1)[1].split("\n## ", 1)[0]
        for must in ("one turn", "launch.py", "blindness.py", "skill", "UNEXPLAINED", "lane-orchestrator",
                     "does not open"):
            self.assertIn(must, section, f"K9.smoke: {must}")


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
                                "build_kit", "if head not in body:", "if False:"),
        "athena-optional": ("Athena.test_main_requires_the_outputs", "K8.athena", "build_kit",
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
