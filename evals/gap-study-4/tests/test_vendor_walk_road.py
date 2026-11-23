#!/usr/bin/env python3
"""Lane vendor-admission T4 P5: the walk road of a vendor walk (lane-reports/vendor-T4-PLAN.md v4, sections 6 and 9;
glitch-b5 round 13, Sun 18 Oct 2026).

  P5-now      pending_walk.checker_standing judges a walk against the digest in force for its harness, read from its
              driver ledger's agent.harness: a codex or gemini walk checked under its merged digest counts, and one
              checked under the Claude-only digest reads stale; a claude-code walk, a bare folder with no ledger, an
              unreadable ledger, a harness checker_for does not admit and one that is not a string (review e-71a2b94
              NIT 1: never a TypeError) all read checker_constants_sha256(), as before (arm C byte for byte), so a
              vendor walk misread on that fallback reads stale, never current.
  P5-counts   walk_regrade.nudge_count_problems and agent_summary_problems read a vendor walk's committed counts with
              the vendor side's readings (0 nudges; no Agent call and the CLI's own nested CLI calls), never Claude
              Code's readers; a forged count is named; with no harness they read as before.
  P5-check    walk_regrade's --check road (regrade_problems) on a committed vendor walk hands each check.json's
              re-derivation the walk's own harness: a vendor walk whose check.json records the nested CLI call its
              CLI ran passes, and one that records none is named.
  R-9         review 10ac86f MAJOR 1, plan section 6 (a)-(d), on test_pending_codex_walk's committed pending codex walk
              with its reader registered and a verified graded-true regrade: with no checker reading it is not
              counted ("pending: regraded, no checker reading under the constants in force"); a vendor recheck
              through checker_for (its entry's body stood in, the vendor rows being PENDING) under the merged
              constants, superseding the pending check.json with no reasons and no digest, and carrying the vendor
              side's counts, does not count with a constant-bound reason and counts with none; walk_regrade's --check
              re-derives it and names one the checker no longer reads; a recheck under the Claude-only digest reads
              stale. Its three mutants (the pending branch counting on "graded" alone, RECHECK_HARNESSES left
              Claude-only, the recheck reading the ledger's pending cross-check) and two of the pending road's rules
              (constant-bound reasons admitted, the digest unchecked) each go red. The claude-code coverage witness is
              every existing coverage suite unchanged (test_walk_plan, test_walk_recheck, test_recheck_coverage,
              test_checker_constants, test_no_output_nudge, test_nested_agent) and test_pending_walk's, whose
              Gemini pending walk moves by R-9.
  P5-witness  pending_walk.py and walk_regrade.py compiled in memory with a vendor walk read as current under the
              Claude-only digest, the counts read with Claude Code's readers, and the --check road dropping the
              harness: each goes red.

Fakes and synthetic strings only, inside test_box_integration's process guard with test_drive_loop's checker world,
in scratch folders and one scratch git repository: no take, model, vendor, network, Docker, credential or holdout.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import subprocess
import sys
import tempfile
import time
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
              ("a harness checker_for does not admit", {"agent": {"harness": "synthetic-harness"}}, claude, None),
              # round 14, review e-71a2b94 NIT 1: a harness that is not a string reads as no harness, never TypeError
              ("a harness that is a list", {"agent": {"harness": ["codex"]}}, claude, None),
              ("a harness that is a list under the codex digest", {"agent": {"harness": ["codex"]}},
               ct.vendor_checker_constants_sha256("codex"), "stale")]
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


# ---- R-9's road (plan v4 section 6 (a)-(d); review 10ac86f MAJOR 1) --------------------------------------------------
MACHINE = {"home": "/synthetic-home", "checkout": "/synthetic-checkout", "temp_root": "/synthetic-tmp"}   # TEST DATA


def vendor_design_for(ct):
    """A vendor view for the recheck, built by walk_regrade.production_design's own producer (check_take.design_view,
    then check_take.checker_view, so the vendor block through vendor_view) with one stand-in: the routing table pins no
    codex profile until CP5 registers one, so the pin is the row's harness and model with no permission mode (design_view
    then writes no pinned mode). Merge lane L6c: built from design_view, the view carries the pre-registration's
    leak_words and leak_context_excusals, which the digest writer now binds (view_design_values); a view built from
    CHECKER_CONSTANTS alone carried neither and recorded a digest the reader never holds."""
    def design_for(row, run_tree):
        pin = {"harness": row["agent"]["harness"], "model": row["model"]}
        return ct.checker_view(ct.design_view(row, pin=pin, run_tree=run_tree))
    return design_for


@contextlib.contextmanager
def vendor_entry(ct, reasons, seen):
    """check4_walk_vendor's body stood in by `reasons` (the vendor rows are PENDING, so a real reading always carries
    constant-bound reasons); checker_for, _vendor_entry, _vendor_side and drive.take_checker stay real. `seen` collects
    each call's design digest."""
    import routing
    ids = routing.load_table()["checker_reasons_become_events"]["ids"]

    def stand_in(path, task, half, walk, *, wording_script, arm, design, table=None):
        seen.append(ct.vendor_design_constants_sha256(design))
        return {"reasons": list(reasons), "problems": [], "events": dict.fromkeys(ids, 0), "outside_reach": 0}
    with mock.patch.object(ct, "check4_walk_vendor", stand_in):
        yield


def enveloped_pending_walk(test):
    """test_pending_codex_walk's road with its reader registered on walk-g1, the acceptance walk, and a second pending
    codex walk, walk-g2, driven and committed by the same road (WalkDriver, walk_runner.run_walks, WalkRepo): since T4
    edit B (glitch-b5 round 14; review e-71a2b94 finding 1) the drive writes its host turn envelopes
    (transcript.jsonl, vendor_record_binding's schema 1), so the recheck road reads walk-g2 as the drive left it, never
    a hand copy with envelopes added. The recheck is not made on walk-g1: a later commit touching the acceptance walk's
    folder that is not its regrade refuses the registration."""
    import test_pending_codex_walk as tpcw
    import test_pending_walk as tpw
    import walk_runner
    road = tpcw.codex_road(test)
    if road.lease is not None:                # one lease per walk, as walk_builders places it: a fresh one for walk-g2
        import test_walk_builders as twb
        import walk_builders
        home = tbi.SCRATCH / f"lease-{road.root.name}-g2"
        home.mkdir(mode=0o700)
        road.lease = walk_builders.CodexLeaseRoad(str(twb.lease_file(home)), walk_s=twb.RIG_WALK_S,
                                                  clock=time.time)
    road.rig.box.turn_n = 0                   # walk-g2's own session: its rollout grows from its first turn
    with tbi.spying(road.rig.spy):
        got = walk_runner.run_walks(road.driver, road.repo, [{"row": dict(road.row, walk="walk-g2", slot="walk-g2"),
                                                              "reason": road.reason}])
    test.assertEqual(got[0]["state"], "pending-native-reader", got)
    road.accept()
    return road, "walk-g2"


def r9_problems(test, pw, wr, ct) -> list:
    """R-9's red-first test on one committed pending codex walk (test_pending_codex_walk's road), its reader
    registered and its regrade verified and committed."""
    import run
    import test_pending_codex_walk as tpcw
    import test_pending_walk as tpw
    out = []
    road, walk = enveloped_pending_walk(test)
    base, study = road.study / "rehearsals", road.study
    secrets = dict(secrets=lambda: [("token", tbi.TOKEN)], rules_scanner=lambda paths: [])
    merged = ct.vendor_checker_constants_sha256("codex")
    with mock.patch.object(run, "grade_walk_folder", tpw.stand_in_grade), \
            mock.patch.object(wr, "production_design", vendor_design_for(ct)):
        wr.write_regrade(walk, study)
        wr.commit_regrade(walk, study, **secrets)
        got = pw.coverage_status(base, walk)
        if got != "pending: regraded, no checker reading under the constants in force":
            out.append(f"a verified graded-true regrade and no checker reading: coverage {got!r}")
        for n, reasons, want in ((1, ["constant-binding"], "constant-bound checker reason: constant-binding"),
                                 (2, [], None)):
            seen = []
            try:
                with vendor_entry(ct, reasons, seen):
                    path = wr.write_recheck(walk, study, machine=MACHINE)
                    wr.commit_recheck(walk, n, study, **secrets)
            except Exception as e:  # noqa: BLE001 - a refused recheck is this test's failure, named
                out.append(f"recheck {n} ({reasons}) refused: {type(e).__name__}: {e}")
                return out
            doc = json.loads(path.read_text())
            want_was = ({"file": "check.json", "checker_constants_sha256": None, "checker_reasons": []} if n == 1
                        else {"file": "recheck-1.json", "checker_constants_sha256": merged,
                              "checker_reasons": ["constant-binding"]})
            if (doc["supersedes"], doc["was"], doc["checker_constants_sha256"], doc["checker_reasons"], seen) != \
                    (want_was["file"], want_was, merged, reasons, [merged]):
                out.append(f"recheck {n}: {doc['supersedes']}, {doc['was']}, {doc['checker_constants_sha256']}, "
                           f"{doc['checker_reasons']}, entry digests {seen}")
            if (doc["no_output_nudges"], doc["agent_calls"], doc["nested_cli_calls"]) != (0, 0, 0):
                out.append(f"recheck {n}: the vendor side's counts are not in it: {doc}")
            got = pw.coverage_status(base, walk)
            if got != want:
                out.append(f"recheck {n} with reasons {reasons}: coverage {got!r}, not {want!r}")
        # (d): walk_regrade --check re-derives the vendor recheck, and names one the checker no longer reads
        with vendor_entry(ct, [], []):
            got = wr.regrade_problems(study)
            if got:
                out.append(f"an honest vendor recheck does not re-derive: {got}")
        with vendor_entry(ct, ["readers-disagree"], []):
            got = wr.regrade_problems(study)
            if not any("recheck-2.json differs from re-deriving it" in g for g in got):
                out.append(f"a vendor recheck the checker no longer reads is not named: {got}")
        # a recheck under the Claude-only digest (written by hand: the vendor side never records it) never counts
        import walk_register
        folder = base / walk
        doc = dict(json.loads((folder / "recheck-2.json").read_text()), n=3, supersedes="recheck-2.json",
                   checker_constants_sha256=ct.checker_constants_sha256())
        raw = wr.regrade_bytes(doc)
        (folder / "recheck-3.json").write_bytes(raw)
        reg = json.loads((base / walk_register.REGISTER_NAME).read_text())
        reg["rechecks"].append({"walk": walk, "file": "recheck-3.json", "n": 3,
                                "checker_constants_sha256": doc["checker_constants_sha256"],
                                "sha256": hashlib.sha256(raw).hexdigest()})
        (base / walk_register.REGISTER_NAME).write_text(json.dumps(reg, indent=2) + "\n")
        tpw.git(road.root, "add", "-A")                       # committed, so the registration reads a clean tree
        tpw.git(road.root, "commit", "-q", "-m", wr.RECHECK_SUBJECT)
        got = pw.coverage_status(base, walk)
        if not (isinstance(got, str) and got.startswith("stale")):
            out.append(f"a recheck under the Claude-only digest: coverage {got!r}")
    return out


class R9Road(unittest.TestCase):
    def test_r9_a_pending_vendor_walk_counts_only_through_a_vendor_recheck(self):
        import pending_walk
        import walk_regrade
        with world() as ct:
            self.assertEqual(r9_problems(self, pending_walk, walk_regrade, ct), [])


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
# R-9's three mutants (plan v4 section 6) and two of the pending road's rules
R9_WITNESSES = {
    "the pending branch counting on graded alone": ("pending_walk", (
        "        return checker_standing(base, walk, pending=True, strict=strict) if state == \"graded\" "
        "else \"regrade refused\" \\\n",   # strict: lane pf1-walk-cover-strict (OD131)
        "        return None if state == \"graded\" else \"regrade refused\" \\\n")),
    "RECHECK_HARNESSES left Claude-only": ("walk_regrade", (
        "RECHECK_HARNESSES = (\"claude-code\", \"codex\", \"gemini\")", "RECHECK_HARNESSES = (\"claude-code\",)")),
    "the recheck reading the ledger's pending cross_check": ("walk_regrade", (
        "            check_ledger = dict(ledger, cross_check=_verified_regrade_cross(",
        "            check_ledger = dict(ledger, synthetic=_verified_regrade_cross(")),
    "the pending road's constant-bound reasons admitted": ("pending_walk", (
        "    bound = [r for r in reasons if r in check_take.CONSTANT_BOUND_REASONS]\n",
        "    bound = []\n")),
    "the pending road's digest unchecked": ("pending_walk", (
        "    if latest.get(\"checker_constants_sha256\") != now:\n", "    if False:\n")),
}


class R9Witnesses(unittest.TestCase):
    def test_r9_witness_each_mutant_goes_red(self):
        import importlib
        for name, (module, edit) in R9_WITNESSES.items():
            with self.subTest(witness=name), world() as ct:
                mutant = module_with(module, (edit,))
                mods = {m: importlib.import_module(m) for m in ("pending_walk", "walk_regrade")}
                mods[module] = mutant
                with mock.patch.dict(sys.modules, {module: mutant}):
                    got = r9_problems(self, mods["pending_walk"], mods["walk_regrade"], ct)
                self.assertNotEqual(got, [], f"witness {name} stayed green")


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
