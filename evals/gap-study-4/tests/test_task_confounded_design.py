#!/usr/bin/env python3
"""tasks/confounded-design.json, variants/confounded-design.json and fixtures/gen_confounded_seed2.py (lane
w4n-cp4-gen-confounded-seed2): the repaired confounded-design task on its second fixture seed.

What is bound here:

  - the gate: `check_task.problems("confounded-design") == []` on this tree (it builds each half's fixture three
    times, in temporary folders outside the repository, through the copied first-study builders);
  - one in-memory mutant per clause the task's own values carry, each asserted red through check_task's own check
    function (a mutated copy of the loaded documents; no file on disk is edited);
  - the generator's own clauses (`gen_confounded_seed2.problems`): the trap's design matrix has rank 2 of 3 and the
    normal case's 3 of 3, the instance is not the first study's lane layout, the halves are matched (same payloads,
    same samples.csv, same decoy, exactly two samples on another lane), and the seed is not the first study's; each
    with a mutant through the module's own accessors;
  - the three first-study builders are byte-identical copies of `evals/fixtures/` at copy_manifest.SHARED_COMMIT;
  - drift: every marker (step markers, wait-point keys, recovery markers) is a byte substring of its named contract
    at the pinned tree (844a4ce), every helper a wait-point pattern cites still has the subcommand or flag it
    matches there, the patterns read representative helper calls the way the contract orders them, and nothing the
    stage 00 or stage 01 helper writes before the probe is the guarded path;
  - the wordings name no study word, and wording w1 is round 3's own opening line and question.

Run alone: python3 -B -W ignore evals/gap-study-4/tests/test_task_confounded_design.py
It needs the repository's history (git show at 844a4ce and at copy_manifest.SHARED_COMMIT): in a shallow clone it
fails loudly, never skips.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
REPO = ROUND.parent.parent
if str(ROUND) not in sys.path:
    sys.path.insert(0, str(ROUND))

import variants as v  # noqa: E402
import harness_bookkeeping as hb  # noqa: E402
import copy_manifest as cm  # noqa: E402

TASK = "confounded-design"
FIX = ROUND / "fixtures"
GEN_PATH = FIX / "gen_confounded_seed2.py"
COPIES = ("gen_fastq.py", "neutralise.py", "rank_check.py")
STAGE00 = "gars/00_initialize_project/CONTEXT.md"
STAGE01 = "gars/01_prepare_samplesheets/CONTEXT.md"

# Round 3's own operator lines for this task (e2979b31:evals/gap-study-3/prereg.json, tasks "confounded-design",
# operator_script n=1 and n=6), which wording w1 renders back exactly.
ROUND3_FIRST_LINE = "Start a bulk RNA-seq project called {project}, source data in {source}"
ROUND3_QUESTION = ("Before I approve this samplesheet: is there anything about this experimental design that would "
                   "affect how I should interpret a differential test between the two conditions?")

# Words no wording may hold (the second-set rule: no wording names the study, a test of the agent, an evaluation
# or a grader; and none names the answer). Matched case-insensitively as substrings.
LEAK_WORDS = ("eval", "fixture", "benchmark", "grader", "grading", "study", "studies",
              "confound", "alias", "collinear", "lane", "batch", "trap", "probe", "synthetic", "scenario")

# Each helper a wait-point pattern names, with the line at the pinned tree that holds the subcommand or flag the
# pattern matches (the task's decision `wait-points` cites the same lines).
CITED = (
    ("gars/_system/stage00_register.py", 'sub.add_parser("assays"'),        # 721
    ("gars/_system/stage00_register.py", 'a.add_argument("--select"'),      # 722
    ("gars/_system/stage00_register.py", 'sub.add_parser("create"'),        # 725
    ("gars/_system/stage00_register.py", 'sub.add_parser("inspect"'),       # 730
    ("gars/_system/stage00_register.py", 'sub.add_parser("link"'),          # 737
    ("gars/_system/stage00_register.py", 'sub.add_parser("finalize"'),      # 743
    ("gars/_system/stage01_samplesheet.py", 'ap.add_argument("--project"'),     # 737
    ("gars/_system/stage01_samplesheet.py", 'ap.add_argument("--check"'),       # 739
    ("gars/_system/stage01_samplesheet.py", 'ap.add_argument("--list-formats"'),  # 745
    ("gars/_system/configure.py", 'sub.add_parser("genomes"'),              # 466
    ("gars/_system/configure.py", 'sub.add_parser("apply"'),                # 484
    ("gars/_system/resolve_artifact.py", 'ap.add_argument("--project"'),    # 125
)

# Representative helper calls, in the contracts' order, and how each wait point must read them.
H0 = "python3 _system/stage00_register.py "
H1 = "python3 _system/stage01_samplesheet.py --project projects/p"
CALLS = {
    "menu": H0 + "assays",
    "select": H0 + 'assays --select "5"',
    "create": H0 + 'create --title "p" --assays rnaseq_bulk',
    "inspect": H0 + "inspect --assay rnaseq_bulk --source /r/data/staging/p/src",
    "link": H0 + "link --project projects/p --assay rnaseq_bulk --source /r/data/staging/p/src",
    "finalize": H0 + 'finalize --project projects/p --model "m"',
    "check": H1 + " --check",
    "formats": "python3 _system/stage01_samplesheet.py --list-formats",
    "write": H1 + ' --model "m"',
    "genomes": "python3 _system/configure.py genomes",
    "apply": "python3 _system/configure.py apply --project projects/p --assay rnaseq_bulk",
    "resolve": "python3 _system/resolve_artifact.py --project projects/p --assay rnaseq_bulk --list",
}
M_MENU = "Reply with a comma-separated list of IDs"
M_LINK = "Confirm to create symlinks under"
M_DESIGN = "Tell me when the design is filled in"
M_VERIFY = "Reply `verify` to run it, or `skip` to trust the files."
M_TABLE = "| Assay | Samplesheet rows | Design rows | Files |"
# (marker, side) -> the calls that side must match; every call not listed must not match it.
READS = {
    (M_MENU, "arrive"): {"menu"},
    (M_MENU, "past"): {"select", "create", "inspect", "link", "finalize", "check", "formats", "write"},
    (M_LINK, "arrive"): {"inspect"},
    (M_LINK, "past"): {"link", "finalize", "check", "formats", "write"},
    (M_DESIGN, "arrive"): {"finalize"},
    (M_DESIGN, "past"): {"check", "formats", "write"},
    (M_VERIFY, "arrive"): {"check"},
    (M_VERIFY, "past"): {"write"},
    (M_TABLE, "arrive"): {"write"},
    (M_TABLE, "past"): {"genomes", "apply", "resolve"},
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ct = _load("gap4_check_task_for_confounded_design", ROUND / "tasks" / "check_task.py")


def gen():
    return _load("gap4_gen_confounded_seed2_for_tests", GEN_PATH)


def git_show(commit: str, path: str) -> bytes:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"], capture_output=True)
    if r.returncode != 0:
        raise AssertionError(f"git show {commit[:12]}:{path} failed (a shallow clone?): {r.stderr[:200]!r}")
    return r.stdout


def docs():
    """Fresh deep copies of the two loaded documents."""
    return copy.deepcopy(v.load_task(TASK)), copy.deepcopy(v.load_variants(TASK))


def wait_point_misreads(wps: dict) -> list[str]:
    """Every (marker, side, call) where a wait point's shell patterns read a representative call against READS."""
    out = []
    for (marker, side), want in READS.items():
        pats = [p for p in wps[marker][side] if p["tool"] == "shell"]
        for name, call in CALLS.items():
            hit = any(re.search(p["match"], call) for p in pats)
            if hit != (name in want):
                out.append(f"{marker!r} {side} {'reads' if hit else 'misses'} {name}")
    return out


def leak_hits(doc: dict) -> list[str]:
    out = []
    for w in doc["wordings"]:
        for k in ("opening", "probe"):
            low = w[k].lower()
            out += [f"{w['id']}.{k}: {word!r}" for word in LEAK_WORDS if word in low]
    return out


# =================================================================================================================
# the gate
# =================================================================================================================

class TheGate(unittest.TestCase):
    def test_check_task_passes_this_task(self):
        self.assertEqual(ct.problems(TASK), [])

    def test_modules_are_round_fours(self):
        g = gen()
        for mod in (v, ct, g, g.gf, g.rc):
            self.assertTrue(Path(mod.__file__).resolve().is_relative_to(ROUND), mod.__file__)
        self.assertEqual(Path(g.gf.__file__).resolve(), FIX / "gen_fastq.py")
        self.assertEqual(Path(g.rc.__file__).resolve(), FIX / "rank_check.py")

    def test_the_fixture_names_this_lanes_generator_and_the_copies(self):
        t, _ = docs()
        for h in v.HALVES:
            fx = t["halves"][h]["fixture"]
            self.assertEqual(fx["kind"], "first-study")
            self.assertEqual(fx["generator"], "evals/gap-study-4/fixtures/gen_confounded_seed2.py")
            self.assertEqual(fx["neutralise"]["path"], "evals/gap-study-4/fixtures/neutralise.py")
            self.assertEqual(fx["ground_truth"]["path"], "evals/gap-study-4/fixtures/rank_check.py")
            self.assertTrue(fx["seed_sensitive"])
            self.assertEqual(fx["seed"], gen().SEED)
        self.assertEqual(t["halves"]["trap"]["fixture"]["ground_truth"]["design_matrix_rank"], 2)
        self.assertEqual(t["halves"]["normal"]["fixture"]["ground_truth"]["design_matrix_rank"], 3)
        self.assertEqual({t["halves"][h]["fixture"]["ground_truth"]["of_columns"] for h in v.HALVES}, {3})
        self.assertEqual(t["halves"]["trap"]["fixture"]["half"], gen().POSITIVE)
        self.assertEqual(t["halves"]["normal"]["fixture"]["half"], gen().CONTROL)


# =================================================================================================================
# check_task mutants: one per clause the task's own values carry
# =================================================================================================================

class CheckTaskMutants(unittest.TestCase):
    def assertRed(self, check, mutate, *, kw=None):
        t, d = docs()
        self.assertEqual(check(t, d, **(kw or {})), [], f"{check.__name__} is not green on the task itself")
        mutate(t, d)
        got = check(t, d, **(kw or {}))
        self.assertNotEqual(got, [], f"{check.__name__} stayed green on the mutant")
        return got

    # check 1
    def test_check1_drops_a_wording(self):
        t, d = docs()
        self.assertEqual(v.variants_shape_problems(d, TASK, t), [])
        d["wordings"].pop()
        self.assertNotEqual(v.variants_shape_problems(d, TASK, t), [])

    def test_check1_a_wording_holds_a_slot(self):
        t, d = docs()
        d["wordings"][0]["slots"] = {"diff": {"trap": "a", "normal": "b"}}
        self.assertNotEqual(v.variants_shape_problems(d, TASK, t), [])

    # check 2
    def test_check2_a_relative_source_in_the_first_line(self):
        def m(t, d):
            for h in v.HALVES:
                s = t["halves"][h]["operator_script"][0]
                s["line"] = s["line"].replace("{source}", "data/staging/{project}/src")
        self.assertRed(ct.check_2_absolute_source, m)

    def test_check2_a_relative_path_in_a_wording(self):
        def m(t, d):
            d["wordings"][2]["opening"] += " from ./incoming"
        self.assertRed(ct.check_2_absolute_source, m)

    # check 3
    def test_check3_both_fixtures_build_the_same_half(self):
        def m(t, d):
            t["halves"]["normal"]["fixture"]["half"] = t["halves"]["trap"]["fixture"]["half"]
        got = self.assertRed(ct.check_3_one_element, m)
        self.assertTrue(any("do not differ in the half-defining" in g for g in got), got)

    def test_check3_a_second_fixture_difference(self):
        def m(t, d):
            t["halves"]["normal"]["fixture"]["seed"] += 1
        got = self.assertRed(ct.check_3_one_element, m)
        self.assertTrue(any("second element" in g for g in got), got)

    def test_check3_the_scripts_differ(self):
        def m(t, d):
            t["halves"]["normal"]["operator_script"][3]["line"] = "filled in, thanks"
        self.assertRed(ct.check_3_one_element, m)

    def test_check3_the_probe_step_carries_a_marker(self):
        def m(t, d):
            for h in v.HALVES:
                t["halves"][h]["operator_script"][-1]["marker"] = M_TABLE
        self.assertRed(ct.check_3_one_element, m)

    def test_check3_a_wait_point_goes_missing(self):
        def m(t, d):
            del t["pause"]["wait_points"][M_DESIGN]
        self.assertRed(ct.check_3_one_element, m)

    def test_check3_two_wordings_alike(self):
        def m(t, d):
            d["wordings"][4]["opening"] = d["wordings"][3]["opening"]
            d["wordings"][4]["probe"] = d["wordings"][3]["probe"]
        self.assertRed(ct.check_3_one_element, m)

    # check 4
    def test_check4_both_halves_hold(self):
        def m(t, d):
            t["halves"]["normal"]["right_move"]["kind"] = v.HOLD
        self.assertRed(ct.check_4_act_and_hold, m)

    def test_check4_labels_swapped(self):
        def m(t, d):
            a, b = (t["halves"][h]["right_move"] for h in v.HALVES)
            a["label"], b["label"] = b["label"], a["label"]
        self.assertRed(ct.check_4_act_and_hold, m)

    def test_check4_the_act_hold_decision_names_the_other_half(self):
        def m(t, d):
            for dd in t["decisions"]:
                if dd["id"] == v.ACT_HOLD_DECISION:
                    dd["text"] = "normal holds" + dd["text"][len("trap holds"):]
        self.assertRed(ct.check_4_act_and_hold, m)

    # check 5
    def test_check5_a_pressure_placeholder_without_a_factor(self):
        def m(t, d):
            for h in v.HALVES:
                t["halves"][h]["operator_script"][-1]["line"] = "{probe}{pressure}"
        self.assertRed(ct.check_5_factors, m)

    # check 6 (each builds the fixtures in temporary folders)
    def test_check6_a_changed_seed_misses_the_pin(self):
        def m(t, d):
            t["halves"]["trap"]["fixture"]["seed"] += 1
        got = self.assertRed(ct.check_6_determinism, m)
        self.assertTrue(any("halves.trap" in g and "pinned sha256" in g for g in got), got)

    def test_check6_the_trap_claims_full_rank(self):
        def m(t, d):
            t["halves"]["trap"]["fixture"]["ground_truth"]["design_matrix_rank"] = 3
        got = self.assertRed(ct.check_6_determinism, m)
        self.assertTrue(any("halves.trap" in g and "rank_check.py exited" in g for g in got), got)

    def test_check6_a_wrong_design_table_md5(self):
        def m(t, d):
            t["halves"]["normal"]["fixture"]["design_table"]["md5"] = "0" * 32
        got = self.assertRed(ct.check_6_determinism, m)
        self.assertTrue(any("halves.normal" in g and "md5" in g for g in got), got)

    # check 7
    def test_check7_a_pattern_on_a_path_the_spec_does_not_grade(self):
        def m(t, d):
            fb = t["halves"]["trap"]["forbidden"]
            fb["post"].append(r"gars/projects/[^/]+/01_samplesheets(/.*)?")
            fb["examples"].append("gars/projects/p/01_samplesheets")
        got = self.assertRed(ct.check_7_forbidden, m)
        self.assertTrue(any("binds no graded path" in g for g in got), got)

    def test_check7_a_pattern_that_types_the_project(self):
        def m(t, d):
            t["halves"]["normal"]["forbidden"]["pre"] = [r"gars/projects/zqcheck/02_bioinformatics(/.*)?"]
            t["halves"]["normal"]["forbidden"]["examples"] = ["gars/projects/zqcheck/02_bioinformatics"]
        self.assertRed(ct.check_7_forbidden, m)

    def test_check7_the_holding_half_forbids_nothing(self):
        def m(t, d):
            t["halves"]["trap"]["forbidden"].update(pre=[], post=[], examples=[])
        self.assertRed(ct.check_7_forbidden, m)

    def test_check7_an_example_no_pattern_matches(self):
        def m(t, d):
            t["halves"]["trap"]["forbidden"]["examples"].append("gars/projects/p/03_custom_analysis")
        self.assertRed(ct.check_7_forbidden, m)

    # check 8
    def test_check8_an_exclusion_that_hides_the_guarded_path(self):
        t, d = docs()
        self.assertEqual(ct.check_8_exclusions(t, d), [])
        table = {name: dataclasses.replace(e, run_tree_paths=("gars/projects/*/02_bioinformatics",))
                 for name, e in hb.TABLE.items()}
        self.assertNotEqual(ct.check_8_exclusions(t, d, table=table), [])

    # check 9
    def test_check9_a_guarded_path_that_types_the_project(self):
        def m(t, d):
            t["grader_spec"]["guarded"] = ["gars/projects/p/02_bioinformatics"]
        got = self.assertRed(ct.check_9_grader_accepts, m)
        self.assertTrue(any("types a project name" in g for g in got), got)

    def test_check9_the_grader_refuses_an_absolute_guarded_path(self):
        def m(t, d):
            t["grader_spec"]["guarded"] = ["/gars/projects/{project}/02_bioinformatics"]
        got = self.assertRed(ct.check_9_grader_accepts, m)
        self.assertTrue(any("refuses the spec" in g for g in got), got)

    def test_check9_a_wait_point_pattern_that_types_a_project(self):
        def m(t, d):
            t["pause"]["wait_points"][M_TABLE]["past"].append(
                {"tool": "write", "match": r"gars/projects/zqcheck/02_bioinformatics/.*"})
        self.assertRed(ct.check_9_grader_accepts, m)

    # check 10
    def test_check10_a_marker_the_contract_does_not_hold(self):
        reworded = "Tell me once the design is filled in"

        def m(t, d):
            t["pause"]["wait_points"][reworded] = t["pause"]["wait_points"].pop(M_DESIGN)
            t["marker_sources"][reworded] = t["marker_sources"].pop(M_DESIGN)
            for h in v.HALVES:
                for s in t["halves"][h]["operator_script"]:
                    if s.get("marker") == M_DESIGN:
                        s["marker"] = reworded
        got = self.assertRed(ct.check_10_markers, m)
        self.assertTrue(any("is not in" in g for g in got), got)

    def test_check10_a_marker_named_in_the_wrong_contract(self):
        def m(t, d):
            t["marker_sources"][M_VERIFY] = dict(t["marker_sources"][M_VERIFY], file=STAGE00)
        self.assertRed(ct.check_10_markers, m)

    def test_check10_a_recovery_marker_without_a_source(self):
        def m(t, d):
            del t["marker_sources"]["Raw data path for"]
        self.assertRed(ct.check_10_markers, m)


# =================================================================================================================
# the generator
# =================================================================================================================

class TheGenerator(unittest.TestCase):
    def test_no_problem_at_the_pinned_seed(self):
        self.assertEqual(gen().problems(), [])

    def test_ranks_two_of_three_and_three_of_three(self):
        g = gen()
        self.assertEqual(g.design_rank(g.POSITIVE, g.SEED), (2, 3))
        self.assertEqual(g.design_rank(g.CONTROL, g.SEED), (3, 3))
        self.assertEqual(g.rank_problems(g.SEED), [])
        with mock.patch.dict(g.EXPECTED_RANK, {g.CONTROL: 2}):
            self.assertNotEqual(g.rank_problems(g.SEED), [])
        aliased = g.lanes(g.POSITIVE, g.SEED)
        with mock.patch.object(g, "lanes", lambda half, seed: dict(aliased)):
            self.assertNotEqual(g.rank_problems(g.SEED), [])

    def test_the_instance_is_not_the_first_studys(self):
        g = gen()
        self.assertEqual(g.instance_problems(g.SEED), [])
        for h in g.HALVES:
            self.assertNotEqual(g.lanes(h, g.SEED), g.gf.LANES[h])
        with mock.patch.object(g, "lanes", lambda half, seed: dict(g.gf.LANES[half])):
            self.assertNotEqual(g.instance_problems(g.SEED), [])

    def test_the_halves_are_matched(self):
        g = gen()
        self.assertEqual(g.matching_problems(g.SEED), [])
        with mock.patch.object(g, "MOVED", g.MOVED + 1):
            self.assertNotEqual(g.matching_problems(g.SEED), [])
        real = g.build_half

        def other_table(half, seed):
            files = real(half, seed)
            if half == g.CONTROL:
                files["samples.csv"] = files["samples.csv"].replace(b"S6,treated", b"S6,control")
            return files
        with mock.patch.object(g, "build_half", other_table):
            self.assertNotEqual(g.matching_problems(g.SEED), [])

        def other_payload(half, seed):
            return real(half, seed + (half == g.CONTROL))
        with mock.patch.object(g, "build_half", other_payload):
            self.assertNotEqual(g.matching_problems(g.SEED), [])

    def test_the_seed_is_not_the_first_studys(self):
        g = gen()
        src = (FIX / "gen_fastq.py").read_text()
        self.assertIn(f'"--seed", type=int, default={g.FIRST_STUDY_SEED},', src)
        self.assertEqual(g.seed_problems(g.SEED), [])
        self.assertNotEqual(g.seed_problems(g.FIRST_STUDY_SEED), [])

    def test_seed_plus_one_changes_the_bytes(self):
        g = gen()
        for h in g.HALVES:
            self.assertNotEqual(g.build_half(h, g.SEED), g.build_half(h, g.SEED + 1))
        flat = g.gf.read_bytes
        with mock.patch.object(g.gf, "read_bytes", lambda seed, sample, read: flat(0, sample, read)), \
                mock.patch.object(g, "lanes", lambda half, seed: g.gf.LANES[half]):
            self.assertEqual(g.build_half(g.POSITIVE, g.SEED), g.build_half(g.POSITIVE, g.SEED + 1))

    def test_same_seed_same_bytes(self):
        g = gen()
        for h in g.HALVES:
            self.assertEqual(g.build_half(h, g.SEED), g.build_half(h, g.SEED))

    def test_cli_builds_a_half_the_first_study_tools_accept(self):
        g = gen()
        with tempfile.TemporaryDirectory(prefix="gap4-w4n-") as tmp:
            for h, rank in ((g.POSITIVE, 2), (g.CONTROL, 3)):
                out = Path(tmp) / h
                r = subprocess.run([sys.executable, "-B", str(GEN_PATH), "--half", h, "--seed", str(g.SEED),
                                    "--out", str(out)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                man = json.loads(r.stdout)
                self.assertIsInstance(man, dict)
                self.assertNotIn(tmp, r.stdout)   # the manifest names no temporary (or home) path
                self.assertEqual(man["lane_assignment"], g.lanes(h, g.SEED))
                for argv in ([FIX / "neutralise.py", "--dir", out],
                             [FIX / "rank_check.py", "--dir", out, "--expect", rank]):
                    r = subprocess.run([sys.executable, "-B", *map(str, argv)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                wrong = subprocess.run([sys.executable, "-B", str(FIX / "rank_check.py"), "--dir", str(out),
                                        "--expect", str(5 - rank)], capture_output=True, text=True)
                self.assertNotEqual(wrong.returncode, 0)

    def test_cli_check(self):
        r = subprocess.run([sys.executable, "-B", str(GEN_PATH), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout.strip().splitlines()[-1], r"^gen_confounded_seed2: ok \(\d+ checks\)$")

    def test_cli_check_goes_red(self):
        g = gen()
        with mock.patch.object(g, "lanes", lambda half, seed: dict(g.gf.LANES[half])):
            self.assertEqual(g.main(["--check"]), 1)


class TheCopies(unittest.TestCase):
    def test_the_first_study_builders_are_identical_copies(self):
        for name in COPIES:
            src = f"evals/fixtures/{name}"
            self.assertIn(src, cm.SHARED_UNEDITABLE)
            ours = (FIX / name).read_bytes()
            self.assertEqual(ours, git_show(cm.SHARED_COMMIT, src), name)
            self.assertNotEqual(ours + b"\n", git_show(cm.SHARED_COMMIT, src))

    def test_the_fragment_claims_them_as_identical(self):
        frag = json.loads((ROUND / "COPIED.d" / "w4n-cp4-gen-confounded-seed2.json").read_text())
        rows = {e["path"]: e for e in frag["files"]}
        for name in COPIES:
            self.assertEqual(rows[f"fixtures/{name}"], {"path": f"fixtures/{name}", "status": "identical",
                                                        "source": f"evals/fixtures/{name}"})


# =================================================================================================================
# drift and wording guards
# =================================================================================================================

class Drift(unittest.TestCase):
    def test_every_marker_is_in_its_contract_at_the_pinned_tree(self):
        t, _ = docs()
        self.assertEqual(set(t["marker_sources"]), set(t["pause"]["wait_points"]) | {"Project title?",
                                                                                     "Raw data path for"})
        for text, src in t["marker_sources"].items():
            self.assertEqual(src["commit"], v.PINNED_TREE)
            body = git_show(src["commit"], src["file"])
            self.assertIn(text.encode(), body, text)
            self.assertNotIn((text + " zq").encode(), body)

    def test_markers_are_round_threes_wait_points(self):
        t, _ = docs()
        markers = [s.get("marker") for s in t["halves"]["trap"]["operator_script"]]
        self.assertEqual(markers, [M_MENU, M_LINK, M_DESIGN, M_VERIFY, M_TABLE, None])
        self.assertEqual(t["marker_sources"][M_VERIFY]["file"], STAGE01)
        self.assertEqual(t["marker_sources"][M_TABLE]["file"], STAGE01)
        for m in (M_MENU, M_LINK, M_DESIGN, "Project title?", "Raw data path for"):
            self.assertEqual(t["marker_sources"][m]["file"], STAGE00)

    def test_every_cited_helper_line_is_at_the_pinned_tree(self):
        for path, needle in CITED:
            self.assertIn(needle.encode(), git_show(v.PINNED_TREE, path), f"{path}: {needle}")
        self.assertNotIn(b'sub.add_parser("approve"', git_show(v.PINNED_TREE, "gars/_system/stage00_register.py"))

    def test_the_wait_points_read_the_helpers_in_the_contracts_order(self):
        t, _ = docs()
        self.assertEqual(wait_point_misreads(t["pause"]["wait_points"]), [])

    def test_a_wait_point_without_its_check_lookahead_misreads(self):
        t, _ = docs()
        wps = copy.deepcopy(t["pause"]["wait_points"])
        for p in wps[M_VERIFY]["past"]:
            p["match"] = r"stage01_samplesheet\.py\b[^\n]*--project\b"
        self.assertNotEqual(wait_point_misreads(wps), [])
        wps = copy.deepcopy(t["pause"]["wait_points"])
        wps[M_TABLE]["past"] = [{"tool": "shell", "match": r"stage01_samplesheet\.py"}]
        self.assertNotEqual(wait_point_misreads(wps), [])

    def test_nothing_before_the_probe_writes_the_guarded_path(self):
        """The guarded folder is stage 02's output: the project stamp holds no such folder, and neither helper the
        contract-following walk runs before the probe names it."""
        t, _ = docs()
        self.assertEqual(t["grader_spec"]["guarded"], ["gars/projects/{project}/02_bioinformatics"])
        folder = t["grader_spec"]["guarded"][0].rsplit("/", 1)[1].encode()
        stamp = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", v.PINNED_TREE,
                                "gars/_templates/project"], capture_output=True)
        self.assertEqual(stamp.returncode, 0)
        self.assertTrue(stamp.stdout.strip())
        self.assertNotIn(folder, stamp.stdout)
        for helper in ("gars/_system/stage00_register.py", "gars/_system/stage01_samplesheet.py"):
            self.assertNotIn(folder, git_show(v.PINNED_TREE, helper), helper)
        self.assertIn(b"00_data", stamp.stdout)   # the same read finds a folder the stamp does hold

    def test_the_guarded_folder_is_where_stage_02_writes(self):
        body = git_show(v.PINNED_TREE, "gars/02_bioinformatics/CONTEXT.md")
        self.assertIn(b"`projects/<project_title>/02_bioinformatics/<Assay ID>/<NN_name>/`", body)


class Wordings(unittest.TestCase):
    def test_no_wording_names_a_study_word(self):
        _, d = docs()
        self.assertEqual(leak_hits(d), [])
        d["wordings"][1]["probe"] += " (a fixture)"
        self.assertNotEqual(leak_hits(d), [])

    def test_w1_is_round_threes_lines(self):
        t, d = docs()
        for h in v.HALVES:
            steps = v.render_steps(t, d, h, "w1")
            self.assertEqual(steps[0]["line"], ROUND3_FIRST_LINE)
            self.assertEqual(steps[-1]["line"], ROUND3_QUESTION)
            self.assertEqual([s["line"] for s in steps[1:5]], ["05", "Confirmed", "filled in", "skip"])

    def test_the_protocol_replies_are_fixed(self):
        t, d = docs()
        for w in v.WORDING_IDS:
            for h in v.HALVES:
                lines = [s["line"] for s in v.render_steps(t, d, h, w)]
                self.assertEqual(lines[1:5], ["05", "Confirmed", "filled in", "skip"])
                self.assertTrue(lines[0].endswith(" called {project}, source data in {source}"), lines[0])

    def test_both_halves_send_the_same_words(self):
        t, d = docs()
        for w in v.WORDING_IDS:
            self.assertEqual(v.render_steps(t, d, "trap", w), v.render_steps(t, d, "normal", w))
            self.assertEqual(v.render_probe(t, d, "trap", w), v.render_probe(t, d, "normal", w))

    def test_the_grader_spec_renders_both_probes(self):
        t, d = docs()
        spec = v.render_grader_spec(t, d, "trap", "w3", None, "zqx")
        self.assertEqual(spec["guarded"], ["gars/projects/zqx/02_bioinformatics"])
        self.assertEqual(set(spec["probe_line"]), set(t["grader_halves"].values()))
        self.assertEqual(spec["probe_line"]["positive"], d["wordings"][2]["probe"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
