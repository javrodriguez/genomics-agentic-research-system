#!/usr/bin/env python3
"""Lane vendor-admission T4 P5: the walk road of a vendor walk (lane-reports/vendor-T4-PLAN.md v4, sections 6 and 9;
glitch-b5 round 13, Sun 18 Oct 2026).

  P5-now      pending_walk.checker_standing judges a walk against the digest in force for its harness, read from its
              driver ledger's agent.harness: a codex or gemini walk checked under its merged digest counts, and one
              checked under the Claude-only digest reads stale; a claude-code walk, a bare folder with no ledger, an
              unreadable ledger and a harness checker_for does not admit all read checker_constants_sha256(), as
              before (arm C byte for byte), so a vendor walk misread on that fallback reads stale, never current.
  P5-counts   walk_regrade.nudge_count_problems and agent_summary_problems read a vendor walk's committed counts with
              the vendor side's readings (0 nudges; no Agent call and the CLI's own nested CLI calls), never Claude
              Code's readers; a forged count is named; with no harness they read as before.
  P5-check    walk_regrade's --check road (regrade_problems) on a committed vendor walk hands each check.json's
              re-derivation the walk's own harness: a vendor walk whose check.json records the nested CLI call its
              CLI ran passes, and one that records none is named.
  P5-witness  pending_walk.py and walk_regrade.py compiled in memory with a vendor walk read as current under the
              Claude-only digest, the counts read with Claude Code's readers, and the --check road dropping the
              harness: each goes red.

Fakes and synthetic strings only, inside test_box_integration's process guard with test_drive_loop's checker world,
in scratch folders and one scratch git repository: no take, model, vendor, network, Docker, credential or holdout.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
HERE = TESTS.parent
for p in (HERE, TESTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import test_box_integration as tbi  # noqa: E402
import test_checker_body as tcb  # noqa: E402
import test_vendor_body as tvb  # noqa: E402
import test_vendor_entries as tve  # noqa: E402

HARNESSES = tuple(tvb.VENDORS)
WALK = "w-0001"
world = tve.world
NESTED = "claude -p hello"                     # TEST DATA: a nested agent CLI the vendor's shell runs


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def module_with(name: str, edits=()) -> types.ModuleType:
    """`name`.py with `edits` applied, compiled in memory as its own module (never written to disk)."""
    src = (HERE / f"{name}.py").read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise AssertionError(f"the anchor occurs {src.count(old)} times in {name}.py: {old[:60]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(f"{name}_p5_witness")
    mod.__file__ = str(HERE / f"{name}.py")
    exec(compile(src, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


def summary(nested: int) -> dict:
    return {"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0},
            "nested_cli_calls": nested}


def check_doc(digest: str, nested: int = 0) -> dict:
    """walk_runner.check_record's document of a checked walk, every count present."""
    return {"walk": WALK, "checked": True, "checker_reasons": [], "events": {"outside_reach": 0}, "route": "graded",
            "route_refused": None, "checker_constants_sha256": digest, "no_output_nudges": 0, **summary(nested)}


def walk_folder(base: Path, ledger, digest: str) -> None:
    w = base / WALK
    w.mkdir(parents=True)
    (w / "grade.json").write_text(json.dumps({"graded": True, "row": {}, "grade": {}}))
    (w / "check.json").write_text(json.dumps(check_doc(digest)))
    if ledger is not None:
        (w / "driver-ledger.json").write_text(ledger if isinstance(ledger, str) else json.dumps(ledger))


# ---- P5-now ---------------------------------------------------------------------------------------------------------
def now_problems(pw, ct) -> list:
    out = []
    claude = ct.checker_constants_sha256()
    cases = []
    for h in HARNESSES:
        merged = ct.vendor_checker_constants_sha256(h)
        cases += [(f"a {h} walk under its merged digest", {"agent": {"harness": h}}, merged, None),
                  (f"a {h} walk under the Claude-only digest", {"agent": {"harness": h}}, claude, "stale"),
                  (f"a claude-code walk under the {h} digest", {"agent": {"harness": "claude-code"}}, merged, "stale"),
                  (f"an unreadable ledger under the {h} digest", "{not json", merged, "stale")]
    cases += [("a claude-code walk under the Claude-only digest", {"agent": {"harness": "claude-code"}}, claude, None),
              ("a bare folder with no ledger", None, claude, None),
              ("an unreadable ledger", "{not json", claude, None),
              ("a ledger with no agent", {"walk": WALK}, claude, None),
              ("a harness checker_for does not admit", {"agent": {"harness": "synthetic-harness"}}, claude, None)]
    for name, ledger, digest, want in cases:
        with tempfile.TemporaryDirectory(dir=tcb.SCRATCH) as tmp:
            walk_folder(Path(tmp), ledger, digest)
            got = pw.checker_standing(tmp, WALK)
            cov = pw.coverage_status(tmp, WALK)
        ok = got is None if want is None else isinstance(got, str) and got.startswith(want)
        if not ok or cov != got:
            out.append(f"{name}: checker_standing {got!r}, coverage_status {cov!r}, not {want!r}")
    return out


# ---- P5-counts ------------------------------------------------------------------------------------------------------
def counts_problems(wr, ct) -> list:
    out = []
    for h in HARNESSES:
        t = tve.take_for(ct, h, "walk")
        path = t.build(tvb.tool_command(NESTED))
        claude_readers = []

        def refuse(name):
            def read(*a, **k):
                claude_readers.append(name)
                raise AssertionError(f"{name} read a {h} walk")
            return read
        with mock.patch.object(ct, "no_output_nudges", refuse("no_output_nudges")), \
                mock.patch.object(ct, "agent_summary", refuse("agent_summary")):
            cases = {"the vendor side's counts": (check_doc("x", nested=1), 0),
                     "a forged nudge count": (dict(check_doc("x", nested=1), no_output_nudges=1), 1),
                     "a forged nested CLI count": (check_doc("x", nested=0), 1)}
            for name, (doc, want) in cases.items():
                try:
                    got = wr.nudge_count_problems(doc, path, h) + wr.agent_summary_problems(doc, path, h)
                except AssertionError as e:
                    got = [f"raised: {e}"]
                if len(got) != want or any(g.startswith("raised") for g in got):
                    out.append(f"{h} {name}: {got}")
        if claude_readers:
            out.append(f"{h}: Claude Code's readers read the vendor walk: {claude_readers}")
        # with no harness the readers are Claude Code's, as before (their own suites bind what they read)
        seen = []
        with mock.patch.object(ct, "no_output_nudges", lambda p: seen.append("nudges") or 0), \
                mock.patch.object(ct, "agent_summary", lambda p: seen.append("agents") or summary(1)):
            if wr.nudge_count_problems(check_doc("x", 1), path) + wr.agent_summary_problems(check_doc("x", 1), path):
                out.append(f"{h}: with no harness the counts did not read Claude Code's readers' values")
        if seen != ["nudges", "agents"]:
            out.append(f"{h}: with no harness the readers called were {seen}")
    return out


# ---- P5-check -------------------------------------------------------------------------------------------------------
def git(root, *args):
    got = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if got.returncode != 0:
        raise AssertionError(got.stderr)
    return got.stdout


def committed_walk(ct, harness, nested_recorded: int) -> Path:
    """A scratch repository whose study/rehearsals/<walk>/ holds a vendor walk folder (test_vendor_body's Take, its
    turn 2 running one nested CLI) and a check.json recording `nested_recorded` nested CLI calls; returns the study."""
    import mode_binding
    root = Path(tempfile.mkdtemp(dir=tcb.SCRATCH))
    git(root, "init", "-q")
    study = root / "study"
    t = tve.take_for(ct, harness, "walk")
    path = t.build(tvb.tool_command(NESTED))
    dst = study / mode_binding.WALKS_DIR / WALK
    dst.mkdir(parents=True)
    for f in path.parent.rglob("*"):
        if f.is_file():
            (dst / f.relative_to(path.parent)).parent.mkdir(parents=True, exist_ok=True)
            (dst / f.relative_to(path.parent)).write_bytes(f.read_bytes())
    led = json.loads((dst / "driver-ledger.json").read_text())
    led["agent"] = {"harness": harness, "version": tvb.VERSIONS[harness]}
    (dst / "driver-ledger.json").write_text(json.dumps(led))
    (dst / "check.json").write_text(json.dumps(check_doc("x", nested=nested_recorded)))
    git(root, "add", "-A")
    git(root, "-c", "user.name=synthetic", "-c", "user.email=synthetic@example.invalid", "commit", "-q", "-m", "walk")
    return study


def check_problems(wr, ct) -> list:
    out = []
    for h in HARNESSES:
        with mock.patch.object(ct, "no_output_nudges", lambda p: 0), \
                mock.patch.object(ct, "agent_summary", lambda p: summary(0)):     # Claude Code's reading: no nested call
            got = wr.regrade_problems(committed_walk(ct, h, 1))
            if got:
                out.append(f"{h}: an honest vendor walk's check.json is named: {got}")
            got = wr.regrade_problems(committed_walk(ct, h, 0))
            if len(got) != 1 or "nested_cli_calls" not in got[0]:
                out.append(f"{h}: a vendor walk's check.json recording no nested CLI call: {got}")
    return out


class P5WalkRoad(unittest.TestCase):
    def test_p5_the_digest_in_force_is_the_walks_harnesss(self):
        import pending_walk
        with world() as ct:
            self.assertEqual(now_problems(pending_walk, ct), [])

    def test_p5_a_vendor_walks_counts_are_the_vendor_sides(self):
        import walk_regrade
        with world() as ct:
            self.assertEqual(counts_problems(walk_regrade, ct), [])

    def test_p5_the_check_road_reads_the_walks_harness(self):
        import walk_regrade
        with world() as ct:
            self.assertEqual(check_problems(walk_regrade, ct), [])


# ---- the witnesses --------------------------------------------------------------------------------------------------
P5_WALK_WITNESSES = {
    "a vendor walk read as current under the Claude-only digest": ("pending_walk", (
        "    if harness in check_take.VENDOR_CHECKER_CONSTANTS and harness in check_take.CHECKER_ENTRIES:\n"
        "        return check_take.vendor_checker_constants_sha256(harness)\n", ""), now_problems),
    "the counts read with Claude Code's readers": ("walk_regrade", (
        "    return harness in ct.VENDOR_CHECKER_CONSTANTS and harness in ct.CHECKER_ENTRIES\n",
        "    return False\n"), counts_problems),
    "the check road dropping the harness": ("walk_regrade", (
        "            out += [f\"walk {parts[0]!r}: {p}\" for p in nudge_count_problems(check, path, harness)]\n"
        "            out += [f\"walk {parts[0]!r}: {p}\" for p in agent_summary_problems(check, path, harness)]",
        "            out += [f\"walk {parts[0]!r}: {p}\" for p in nudge_count_problems(check, path)]\n"
        "            out += [f\"walk {parts[0]!r}: {p}\" for p in agent_summary_problems(check, path)]"),
        check_problems),
}


class P5WalkWitnesses(unittest.TestCase):
    def test_p5_walk_witness_each_guard_dropped_goes_red(self):
        import importlib
        for name, (module, edit, check) in P5_WALK_WITNESSES.items():
            with self.subTest(witness=name), world() as ct:
                real = importlib.import_module(module)
                self.assertEqual(check(real, ct), [], f"{name}: its check is red on {module}.py")
                mutant = module_with(module, (edit,))
                with mock.patch.dict(sys.modules, {module: mutant}):
                    self.assertNotEqual(check(mutant, ct), [], f"witness {name} stayed green")


if __name__ == "__main__":
    unittest.main()
