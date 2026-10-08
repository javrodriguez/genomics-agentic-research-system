#!/usr/bin/env python3
"""Red-first tests for the GARS step-map extractor (evals/step-map/extract.py).

Every expectation about the sources is grounded in a file and line at the pinned commit, and
the test re-reads that line (`cited`) so the expectation cannot drift away from its source.
Tests of the extractor's own mechanics run on synthetic modules (FakeSource), not on GARS.
The pilot's stage 00-01 facts (glitch-mem research note, 7 Oct 2026) are the first oracle.

Run alone, from the repository root:  python3 evals/step-map/tests/test_extract.py
The extractor under test can be swapped (the mutant runner does this) with
STEPMAP_EXTRACT=<path to a copy of extract.py>.

Standard library only. Reads the repository through `git show`; writes only to a temp dir.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PIN = "a626cdc2"
EXTRACT = Path(os.environ.get("STEPMAP_EXTRACT", str(HERE.parent / "extract.py")))


def load_extractor():
    spec = importlib.util.spec_from_file_location("stepmap_extract", str(EXTRACT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


X = load_extractor()


def show(path):
    return subprocess.run(["git", "-C", str(REPO), "show", "%s:%s" % (PIN, path)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                          universal_newlines=True).stdout


def cited(test, path, line, needle):
    """Bind an expectation to its source: line `line` of `path` at the pin contains `needle`."""
    lines = show(path).split("\n")
    test.assertGreaterEqual(len(lines), line, "%s has no line %d" % (path, line))
    test.assertIn(needle, lines[line - 1], "%s:%d does not say %r" % (path, line, needle))


S00 = "gars/00_initialize_project/CONTEXT.md"
S01 = "gars/01_prepare_samplesheets/CONTEXT.md"
S02 = "gars/02_bioinformatics/CONTEXT.md"
S03 = "gars/03_custom_analysis/CONTEXT.md"
RNA01 = "gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md"
RNADE = "gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md"
SCC = "gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md"
REG00 = "gars/_system/stage00_register.py"
REG01 = "gars/_system/stage01_samplesheet.py"
WLIB = "gars/_system/wrapperlib.py"
EXL = "gars/_system/executorlib.py"
GUARD = "gars/_system/guard_hook.py"
POLICY = "gars/_system/tools/policy.py"

EXPECTED_CONTRACTS = [
    S00, S01, S02,
    "gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md",
    "gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md",
    "gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md",
    "gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md",
    RNA01, RNADE,
    "gars/02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md",
    "gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md",
    "gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md",
    SCC, S03,
]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = X.Source(str(REPO), PIN)
        if not hasattr(Base, "_result"):
            Base._result = X.extract(cls.src)
        cls.result = Base._result

    def contract(self, path):
        for c in self.result["contracts"]:
            if c["path"] == path:
                return c
        self.fail("contract %s missing from the extraction" % path)

    def step(self, path, n):
        for s in self.contract(path)["steps"]:
            if s["n"] == n:
                return s
        self.fail("step %s of %s missing" % (n, path))


class PinTests(Base):
    def test_reads_the_pinned_blob_not_the_worktree(self):
        blob = subprocess.run(["git", "-C", str(REPO), "rev-parse", "%s:%s" % (PIN, S00)],
                              stdout=subprocess.PIPE, check=True,
                              universal_newlines=True).stdout.strip()
        self.assertEqual(self.contract(S00)["blob"], blob)
        self.assertTrue(self.result["sha"].startswith(PIN))

    def test_gars_tree_unchanged_against_the_pin(self):
        """The lane adds files under evals/step-map/ only; gars/ must not differ from the pin."""
        diff = subprocess.run(["git", "-C", str(REPO), "diff", "--stat", PIN, "--", "gars/"],
                              stdout=subprocess.PIPE, check=True, universal_newlines=True).stdout
        self.assertEqual(diff, "")


class PublishedFactsTests(Base):
    @unittest.skipIf(os.environ.get("STEPMAP_NO_SNAPSHOT") == "1",
                     "mutant run: the snapshot fails on any output change, so it never counts")
    def test_committed_facts_equal_a_fresh_extraction(self):
        """The facts under evals/step-map/facts/ are re-derived and diffed byte for byte."""
        published = HERE.parent / "facts"
        tmp = tempfile.mkdtemp(prefix="stepmap-facts-")
        try:
            X.write(self.result, tmp)
            fresh = sorted(os.listdir(tmp))
            self.assertEqual(sorted(os.listdir(str(published))), fresh)
            for name in fresh:
                with open(os.path.join(tmp, name), "rb") as a, open(str(published / name), "rb") as b:
                    self.assertEqual(a.read(), b.read(), "facts/%s differs from a fresh extraction" % name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ContractDiscoveryTests(Base):
    def test_fourteen_contracts(self):
        self.assertEqual(sorted(c["path"] for c in self.result["contracts"]),
                         sorted(EXPECTED_CONTRACTS))

    def test_142_numbered_steps(self):
        # The method note: "142 numbered process steps in 14 contracts".
        for path, line, needle in ((S00, 280, "17. Exit 0 → reply T6"),
                                   (S01, 301, "14. Reply T4 using `wrote`"),
                                   (S02, 179, "10. Read `02_bioinformatics/<Assay ID>/<NN_name>/CONTEXT.md`"),
                                   (S03, 157, "10. Exit 0 → append the returned `history_entry`"),
                                   (RNADE, 127, "9. Exit 0 → `collect` has written `OUTPUTS.tsv`"),
                                   (SCC, 147, "9. Exit 0 → append its `history_entry`")):
            cited(self, path, line, needle)
        counts = {c["path"]: len(c["steps"]) for c in self.result["contracts"]}
        self.assertEqual(counts[S00], 17)   # 00:195-280, steps 1..17
        self.assertEqual(counts[S01], 14)   # 01:248-304, steps 1..14
        self.assertEqual(counts[S02], 11)   # 02:121-180, 1..10 plus 3a
        self.assertEqual(counts[S03], 10)   # 03:114-158
        for path in EXPECTED_CONTRACTS[3:13]:
            self.assertEqual(counts[path], 9, path)
        self.assertEqual(sum(counts.values()), 142)
        self.assertEqual(self.result["summary"]["steps"], 142)

    def test_lettered_substep_3a(self):
        cited(self, S02, 126, "3a. **Complete the config before routing anything.**")
        s = self.step(S02, "3a")
        self.assertEqual(s["start"], 126)
        self.assertEqual(s["end"], 153)

    def test_pilot_covered_31_steps(self):
        self.assertEqual(len(self.contract(S00)["steps"]) + len(self.contract(S01)["steps"]), 31)

    def test_fence_aware_sections(self):
        # SCC:229 is a "## " line inside a fenced block (the history_entry shape), not a section.
        cited(self, SCC, 229, "## <ISO-8601 date>")
        names = [s["name"] for s in self.contract(SCC)["sections"]]
        self.assertNotIn("<ISO-8601 date> — 02_bioinformatics/spatialvi/02_spatial-cluster-count "
                         "— cluster count complete", names)
        self.assertEqual(names, ["Purpose", "Inputs", "Scope Boundaries", "Definitions",
                                 "Process", "Response Format", "OUTPUT", "Human check"])

    def test_numbered_line_inside_a_fence_is_not_a_step(self):
        text = ("# x\n## Process\n1. Run:\n\n   ```bash\n2. not a step\n   ```\n2. Reply T1.\n"
                "## Response Format\n")
        doc = X.parse_markdown(text)
        self.assertEqual([s["n"] for s in X.parse_steps(doc)], ["1", "2"])

    def test_no_process_section_is_a_finding_not_a_pass(self):
        res = X.extract_text("gars/09_fake/CONTEXT.md", "# x\n## Purpose\nnothing\n", self.src)
        self.assertEqual(res["steps"], [])
        self.assertIn("no_process_steps", [f["kind"] for f in res["findings"]])


class StepTests(Base):
    def test_step_spans(self):
        cited(self, S00, 219, "6. Exit 0 → take its **`assay_ids`**. Create the project:")
        s = self.step(S00, "6")
        self.assertEqual((s["start"], s["end"]), (219, 227))

    def test_fenced_call_maps_to_registry_tool(self):
        cited(self, S00, 222, "python3 _system/stage00_register.py create --title")
        calls = self.step(S00, "6")["calls"]
        self.assertEqual([c["tool"] for c in calls], ["stage00_register.create"])
        self.assertEqual(calls[0]["line"], 222)
        self.assertEqual(calls[0]["kind"], "fenced")

    def test_inline_call_with_workspace_prefix(self):
        cited(self, RNA01, 97, "5. Submit with `python3 <workspace>/_system/executorlib.py submit")
        calls = self.step(RNA01, "5")["calls"]
        self.assertEqual([c["tool"] for c in calls], ["executor.submit"])

    def test_prose_wrapper_call(self):
        cited(self, RNA01, 91, "3. Run the wrapper's `check`.")
        calls = self.step(RNA01, "3")["calls"]
        self.assertEqual([c["tool"] for c in calls], ["nfcore_rnaseq_wrapper.check"])
        self.assertEqual(calls[0]["kind"], "prose")

    def test_templates_referenced(self):
        cited(self, S01, 293, "10. Exit 2 → a gate you believed cleared was not. Reply T5 or T7")
        self.assertEqual(self.step(S01, "10")["templates"], ["T5", "T7"])


class ExitMentionTests(Base):
    def test_exit_or(self):
        cited(self, S00, 277, "16. Exit 1 or 3 → reply T9")
        self.assertEqual(X.exit_codes("16. Exit 1 or 3 → reply T9"), [1, 3])

    def test_exit_non_zero(self):
        cited(self, RNADE, 110, "Exit non-zero → reply T5")
        self.assertEqual(X.exit_codes("Exit non-zero → reply T5"), [X.NONZERO])

    def test_non_zero_covers_only_the_codes_the_call_emits(self):
        # rnaseq-de step 3's resolver emits 0, 1 and 3 (resolve_artifact.py:138-166): "Exit
        # non-zero" there handles 1 and 3, not a 2 the helper never emits.
        cited(self, "gars/_system/resolve_artifact.py", 31, "EXIT_OK, EXIT_UNRESOLVED, EXIT_USAGE = 0, 1, 3")
        site = [s for s in self.contract(RNADE)["call_sites"] if s["step"] == "3"][0]
        self.assertEqual(site["emitted"], [0, 1, 3])
        self.assertEqual(site["handled"], [1, 3])

    def test_lowercase_parenthesised(self):
        cited(self, S03, 132, "report that it refused (exit 2)")
        self.assertEqual(X.exit_codes("report that it refused (exit 2), ask"), [2])

    def test_no_exit_words(self):
        self.assertEqual(X.exit_codes("Reply T1."), [])


class HelperExitTests(Base):
    def sites(self, tool):
        return self.result["helpers"][tool]["exits"]

    def test_create_emits(self):
        cited(self, REG00, 366, "return emit(result, EXIT_USAGE)")
        cited(self, REG00, 373, "return emit(result, EXIT_REFUSED)")
        cited(self, REG00, 390, "return emit(result, EXIT_REFUSED)")
        sites = self.sites("stage00_register.create")
        self.assertEqual(sorted(int(c) for c in sites), [0, 2, 3])
        self.assertIn("%s:366" % REG00, [s["at"] for s in sites["3"]])
        self.assertIn("%s:390" % REG00, [s["at"] for s in sites["2"]])

    def test_link_emits(self):
        cited(self, REG00, 500, "return emit(result, EXIT_USAGE)")
        cited(self, REG00, 510, "return emit(result, EXIT_REFUSED)")
        cited(self, REG00, 516, "return emit(result, EXIT_FAILURE)")
        self.assertEqual(sorted(int(c) for c in self.sites("stage00_register.link")), [0, 1, 2, 3])

    def test_finalize_emits(self):
        cited(self, REG00, 621, "return emit(result, EXIT_REFUSED)")
        sites = self.sites("stage00_register.finalize")
        self.assertEqual(sorted(int(c) for c in sites), [0, 1, 2, 3])
        self.assertIn("%s:621" % REG00, [s["at"] for s in sites["2"]])

    def test_argparse_usage_exit_is_2(self):
        # argparse's error() exits 2 with no JSON, colliding with the documented "2 refused".
        cited(self, REG00, 859, "args = ap.parse_args(argv)")
        argp = [s for s in self.sites("stage00_register.inspect")["2"] if s["how"] == "argparse"]
        self.assertEqual([s["at"] for s in argp], ["%s:859" % REG00])

    def test_configure_refused_is_1(self):
        cited(self, "gars/_system/configure.py", 40, "EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 3")
        sites = self.sites("configure.apply")
        self.assertIn("1", sites)
        self.assertNotIn("2", [c for c in sites if any(s["how"] != "argparse" for s in sites[c])])

    def test_wrapper_prepare_refuses_through_wrapperlib(self):
        cited(self, WLIB, 925, "raise SystemExit(emit({'command': 'prepare'")
        cited(self, "gars/_system/wrappers/rnaseq-de/rnaseq_de.py", 318, "wl.write_reproducibility(")
        sites = self.sites("rnaseq_de.prepare")
        hit = [s for s in sites.get("2", []) if s["at"] == "%s:925" % WLIB]
        self.assertEqual(len(hit), 1)
        # The site carries the condition guarding it, so reachability can be judged.
        self.assertIn("downstream-v2", hit[0]["condition"])

    def test_wrapper_collect_parametric_failure(self):
        cited(self, WLIB, 224, "return emit(result, code)")
        sites = self.sites("nfcore_rnaseq_wrapper.collect")
        self.assertIn("%s:224" % WLIB, [s["at"] for s in sites["1"]])
        self.assertIn("%s:189" % WLIB, [s["at"] for s in sites["2"]])
        self.assertIn("%s:185" % WLIB, [s["at"] for s in sites["3"]])

    def test_executor_submit_and_status(self):
        cited(self, EXL, 1395, "return emit(result, EXIT_REFUSED)")
        cited(self, EXL, 1448, "return emit(result, EXIT_FAILURE)")
        self.assertEqual(sorted(int(c) for c in self.sites("executor.submit")), [0, 1, 2])
        status = self.sites("executor.status")
        self.assertIn("%s:1448" % EXL, [s["at"] for s in status["1"]])
        # 1457's `return EXIT_USAGE` is the fall-through for an unknown command, not status's.
        self.assertNotIn("%s:1457" % EXL, [s["at"] for c in status for s in status[c]])


class UnhandledExitTests(Base):
    def unhandled(self, path, tool):
        out = set()
        for site in self.contract(path)["call_sites"]:
            if site["tool"] == tool:
                out |= set(site["unhandled"])
        return sorted(out)

    def site_of(self, path, step, tool):
        hits = [s for s in self.contract(path)["call_sites"] if s["step"] == step and s["tool"] == tool]
        self.assertEqual(len(hits), 1)
        return hits[0]

    def test_stage_exit_table_is_handling(self):
        """Stage 00's Definitions table decides the branch for its script's codes (00:173-180):
        exit 3 replies T9, and exit 2 replies whatever the JSON's template field names."""
        cited(self, S00, 173, "These, and not your reading of its output, determine the branch")
        cited(self, S00, 179, "| 2 | refused; its `template` field names the reply | T5 / T7 / T8 |")
        cited(self, S00, 180, "| 3 | usage or precondition error | T9 |")
        table = self.contract(S00)["exit_table"]
        self.assertEqual(table["source"], "%s:175" % S00)
        self.assertEqual(table["script"], "_system/stage00_register.py")
        self.assertEqual(table["codes"]["3"]["reply"], "T9")
        self.assertIs(table["codes"]["2"]["needs_template_field"], True)
        create = self.site_of(S00, "6", "stage00_register.create")
        self.assertEqual(create["by_table"], {"3": "T9"})
        self.assertEqual(create["unhandled"], [])

    def test_pilot_create_exit_3_is_routed_by_the_table(self):
        # The pilot's "create exit 3 has no branch" does not hold: the table sends it to T9.
        cited(self, REG00, 366, "return emit(result, EXIT_USAGE)")
        self.assertEqual(self.unhandled(S00, "stage00_register.create"), [])

    def test_pilot_link_exit_2_is_routed_by_its_template_field(self):
        # link's exit 2 sets template T5 (stage00_register.py:506) before emitting (510), so the
        # table routes it; exit 3 goes to T9 by the table.
        cited(self, REG00, 506, 'result["template"] = "T5"')
        cited(self, REG00, 510, "return emit(result, EXIT_REFUSED)")
        site = self.site_of(S00, "12", "stage00_register.link")
        self.assertEqual(site["by_table"], {"2": "template field", "3": "T9"})
        self.assertEqual(site["unhandled"], [])

    def test_pilot_finalize_exit_2_holds(self):
        # finalize's refusals set no template field (stage00_register.py:620-621), so the
        # table's exit-2 row names no reply for them.
        cited(self, REG00, 620, 'result["failures"].append("data_class_required')
        cited(self, REG00, 621, "return emit(result, EXIT_REFUSED)")
        cited(self, S00, 277, "16. Exit 1 or 3 → reply T9")
        self.assertEqual(self.unhandled(S00, "stage00_register.finalize"), [2])
        site = self.site_of(S00, "15", "stage00_register.finalize")
        self.assertNotIn("2", site["by_table"])

    def test_stage01_table_covers_the_writers_exit_3(self):
        cited(self, S01, 212, "| 3 | preconditions not met | T6 |")
        site = self.site_of(S01, "9", "stage01_samplesheet")
        self.assertEqual(site["by_table"].get("3"), "T6")
        self.assertEqual(site["unhandled"], [])

    def test_a_sentence_naming_codes_without_replies_is_not_handling(self):
        cited(self, RNA01, 56, "2 refused (a gate), 3 usage. Branch on them")
        self.assertIsNone(self.contract(RNA01)["exit_table"])
        self.assertEqual([s["line"] for s in self.contract(RNA01)["exit_rules_without_reply"]], [55])

    def test_inspect_fully_handled(self):
        cited(self, S00, 240, "10. Exit 2 → reply T5")
        sites = [s for s in self.contract(S00)["call_sites"] if s["tool"] == "stage00_register.inspect"]
        self.assertEqual([s["step"] for s in sites], ["9"])   # the re-run is a branch action
        self.assertEqual(sites[0]["unhandled"], [])
        self.assertEqual([b["kind"] for b in sites[0]["branch_calls"]], ["prose-rerun"])

    def test_branch_before_a_call_belongs_to_the_previous_call(self):
        # 00:219 "6. Exit 0 → take its assay_ids" answers step 4's `assays --select`.
        sites = [s for s in self.contract(S00)["call_sites"] if s["step"] == "4"]
        self.assertEqual(len(sites), 1)
        self.assertIn(0, sites[0]["handled"])
        self.assertIn(2, sites[0]["handled"])

    def test_user_reported_exit_is_not_a_branch_on_the_agents_call(self):
        # 03:131-132: the user runs approve in their own terminal; "(exit 2)" is theirs.
        cited(self, S03, 132, "report that it refused (exit 2)")
        create = [s for s in self.contract(S03)["call_sites"] if s["tool"] == "stage03_analysis.create"]
        self.assertEqual(len(create), 1)
        self.assertEqual(create[0]["handled"], [])
        actors = [m["actor"] for m in self.step(S03, "6")["exit_mentions"]]
        self.assertEqual(actors, ["user"])

    def test_and_condition_decided_by_the_flags(self):
        # stage03_analysis.py:488-490 refuses only when --workspace is given; the contract's
        # create has none, so create cannot exit 2 from there.
        cited(self, "gars/_system/stage03_analysis.py", 488,
              "if args.workspace is not None and args.workspace.resolve() != Path(workspace).resolve():")
        create = [s for s in self.contract(S03)["call_sites"] if s["tool"] == "stage03_analysis.create"]
        self.assertEqual(create[0]["emitted"], [0, 3])

    def test_submit_has_no_branch_in_wrapper_contracts(self):
        cited(self, RNA01, 98, "It prints one JSON object; `job_id` is the field. Capture it.")
        self.assertEqual(self.unhandled(RNA01, "executor.submit"), [1, 2])

    def test_rnaseq_de_prepare_refusal_unhandled(self):
        cited(self, RNADE, 64, "`design_not_canonical`: prepare refuses (exit 2)")
        self.assertIn(2, self.unhandled(RNADE, "rnaseq_de.prepare"))


class ProseFlagTests(Base):
    def flag(self, path, step, flag):
        hits = [e for e in self.contract(path)["prose_flags"] if e["step"] == step and e["flag"] == flag]
        self.assertTrue(hits, "no %s flag at step %s of %s" % (flag, step, path))
        return hits[0]

    def test_pilot_writer_command_omits_verify_flag(self):
        # 01:283 requires `--verify-integrity full` when step 8 was accepted; the step's own
        # command (01:286) does not carry it.
        cited(self, S01, 283, "`--verify-integrity full` only if step 8 was accepted")
        cited(self, S01, 286, '--model "<model id>" [--confirm-exclusions] [--force]')
        e = self.flag(S01, "9", "--verify-integrity")
        self.assertIs(e["in_command"], False)
        self.assertEqual(e["target_tool"], "stage01_samplesheet")
        # the bracketed optional flags are part of the command
        self.assertIs(self.flag(S01, "9", "--confirm-exclusions")["in_command"], True)
        self.assertIs(self.flag(S01, "9", "--force")["in_command"], True)

    def test_rerun_with_the_pattern_is_a_call_and_is_refused(self):
        cited(self, S00, 241, "re-run")
        cited(self, S00, 242, "`inspect` with `--sample-id-pattern '<their answer as a regex with named groups")
        calls = [c for c in self.step(S00, "10")["calls"] if c["tool"]]
        self.assertEqual([(c["tool"], c["kind"]) for c in calls],
                         [("stage00_register.inspect", "prose-rerun")])
        self.assertIn("--sample-id-pattern", calls[0]["command"])
        g = calls[0]["guard"]
        self.assertEqual(g["intended"], "fresh_declared")
        self.assertIs(g["allowed_where_intended"], False)
        self.assertIs(self.flag(S00, "10", "--sample-id-pattern")["in_command"], True)
        refused = {(r["contract"], r["step"], r["kind"]) for r in
                   self.result["summary"]["guard"]["refused_where_intended"]}
        self.assertIn(("00_initialize_project", "10", "prose-rerun"), refused)
        self.assertIn(("00_initialize_project", "15", "flag-variant"), refused)

    def test_flag_attaches_to_the_call_before_it_not_a_branch_call(self):
        # 02.02:122-123: `--counts-from` modifies collect; status calls sit inside exit branches.
        cited(self, RNADE, 123, "(decision 0024) and `--counts-from <the sub-stage the resolver named>`")
        e = self.flag(RNADE, "8", "--counts-from")
        self.assertEqual(e["target_tool"], "rnaseq_de.collect")
        self.assertIs(e["in_command"], True)

    def test_prohibited_flag(self):
        cited(self, S00, 252, "Never add `--force`.")
        e = self.flag(S00, "12", "--force")
        self.assertIs(e["prohibited"], True)
        self.assertIs(e["guard"]["allowed_where_intended"], False)
        listed = [(r["step"], r["flag"]) for r in self.result["summary"]["guard"]["prohibited_flags"]]
        self.assertEqual(listed, [("12", "--force")])

    def test_descriptive_mention_of_a_default(self):
        cited(self, S00, 275, "It runs `--integrity quick` by default")
        e = [f for f in self.contract(S00)["prose_flags"] if f["step"] == "15" and f["line"] == 275]
        self.assertIs(e[0]["descriptive"], True)


class ReachabilityTests(Base):
    def site(self, path, step, tool):
        hits = [s for s in self.contract(path)["call_sites"] if s["step"] == step and s["tool"] == tool]
        self.assertEqual(len(hits), 1)
        return hits[0]

    def test_nfcore_prepare_exit_2_is_ruled_out_with_evidence(self):
        cited(self, WLIB, 917, "manifest['key_formula'] = ('stage01-v1' if (substage / 'params.yaml').is_file()")
        cited(self, "gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py", 152,
              "wl.write_params_yaml(substage, ASSAY, params)")
        cited(self, "gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py", 170,
              '{"samplesheet": paths["samplesheet"], "config": paths["config"]}')
        site = self.site(RNA01, "4", "nfcore_rnaseq_wrapper.prepare")
        self.assertEqual(site["emitted"], [0, 1, 3])
        self.assertEqual(site["ruled_out"], {"2": [{"at": "%s:925" % WLIB, "ruling": "prepare-stage01-v1"}]})
        # downstream-v2 callers keep the real exit 2
        self.assertIn(2, self.site(RNADE, "5", "rnaseq_de.prepare")["emitted"])
        self.assertEqual(self.result["summary"]["rulings"]["void"], [])

    def test_a_ruling_is_void_when_its_evidence_changes(self):
        class Edited(X.Source):
            def text(self, path):
                body = super().text(path)
                if path == WLIB:
                    lines = body.split("\n")
                    lines[917] = lines[917].replace("'samplesheet' in inputs and ", "")
                    body = "\n".join(lines)
                return body
        holding, void = X.check_rulings(Edited(str(REPO), PIN))
        self.assertEqual(holding, [])
        self.assertEqual(void[0]["lines"], ["%s:918" % WLIB])

    def test_ruling_evidence_is_whole_lines(self):
        """Re-indenting a cited line (here moving params.yaml's write out of its function) voids
        the ruling, though every substring still matches."""
        class Shifted(X.Source):
            def text(self, path):
                body = super().text(path)
                if path == WLIB:
                    lines = body.split("\n")
                    lines[797] = lines[797].lstrip()
                    body = "\n".join(lines)
                return body
        holding, void = X.check_rulings(Shifted(str(REPO), PIN))
        self.assertEqual(holding, [])
        self.assertIn("%s:798" % WLIB, void[0]["lines"])

    def test_ruling_cites_the_atomic_write(self):
        cited(self, "gars/_system/workspace.py", 130, "os.replace(str(tmp), str(path))")
        ev = self.result["summary"]["rulings"]["holding"][0]["evidence"]
        self.assertIn("gars/_system/workspace.py:130", ev)

    def test_check_mode_cannot_emit_the_writers_gate(self):
        # stage01_samplesheet.py:1069-1073 returns before the blocked branch (1085) in --check.
        cited(self, REG01, 1069, "if args.check:")
        cited(self, REG01, 1085, "return emit(result, EXIT_NEEDS_CONFIRM)")
        self.assertEqual(self.site(S01, "3", "stage01_samplesheet")["emitted"], [0, 1, 3])
        self.assertEqual(self.site(S01, "9", "stage01_samplesheet")["emitted"], [0, 1, 2, 3])

    def test_assays_without_select_cannot_refuse(self):
        cited(self, REG00, 296, "if args.select is None:")
        self.assertEqual(self.site(S00, "3", "stage00_register.assays")["emitted"], [0, 3])

    def test_rerun_without_dry_run_is_a_call(self):
        cited(self, S02, 148, "Reply T9 showing what it would write and **wait for confirmation**. On confirmation, re-run")
        cited(self, S02, 149, "without `--dry-run`. Exit 1 → report its `error` and return to T8")
        calls = [c for c in self.step(S02, "3a")["calls"] if c["kind"] == "prose-rerun"]
        self.assertEqual([c["tool"] for c in calls], ["configure.apply"])
        self.assertNotIn("--dry-run", calls[0]["command"])
        sites = [s for s in self.contract(S02)["call_sites"]
                 if s["step"] == "3a" and s["tool"] == "configure.apply"]
        self.assertEqual(len(sites), 2)   # the dry run and the confirmed write are two calls
        dry, write = sites
        self.assertIn("--dry-run", dry["command"])
        self.assertNotIn("--dry-run", write["command"])
        # the contract's "Exit 1 -> report its error" follows the re-run sentence
        self.assertEqual(write["handled"], [1])
        self.assertEqual(write["unhandled"], [3])
        self.assertEqual(dry["handled"], [])
        self.assertEqual(dry["branch_calls"], [])

    def test_branch_calls_are_declared_not_graded(self):
        site = self.site(RNADE, "8", "rnaseq_de.collect")
        self.assertTrue(site["branch_calls"])
        for b in site["branch_calls"]:
            self.assertIs(b["graded"], False)
            self.assertEqual(b["emitted"], [0, 1, 2])
        acc = self.result["summary"]["exits"]
        self.assertGreater(acc["branch_calls"], 0)
        self.assertGreater(acc["branch_call_codes_not_graded"], 0)

    def test_status_inside_an_exit_branch_opens_no_region(self):
        # 02.02:122-126: "Exit 2 -> ... call status ..., Exit 1 -> ... call status" both answer
        # collect; the status calls are branch actions.
        cited(self, RNADE, 124, "run did not complete: call `python3 <workspace>/_system/executorlib.py status")
        site = self.site(RNADE, "8", "rnaseq_de.collect")
        self.assertEqual(site["handled"], [0, 1, 2])
        self.assertEqual([b["tool"] for b in site["branch_calls"]], ["executor.status"] * 2)
        self.assertEqual([s["tool"] for s in self.contract(RNADE)["call_sites"]
                          if s["step"] == "8"], ["rnaseq_de.collect"])

    def test_prose_handling_recorded(self):
        cited(self, S03, 145, "If approval is absent, changed or expired, reply T3 with the refusal and stop")
        site = self.site(S03, "7", "executor.submit")
        self.assertEqual(site["unhandled"], [1, 2])
        self.assertTrue(any(p.startswith("If approval is absent") for p in site["prose_handling"]))


class BackingTests(Base):
    def test_status_table_is_filled_from_files_the_agent_reads(self):
        cited(self, S02, 155, "5. Read each sub-stage's STATUS file")
        self.assertEqual(self.contract(S02)["templates"]["T2"]["backing_tools"], [])

    def test_completion_template_backed_by_collect(self):
        t6 = self.contract(SCC)["templates"]["T6"]
        self.assertEqual(t6["backing_tools"], ["spatial_cluster_count.collect"])

    def test_start_template_has_no_source(self):
        t1 = self.contract(RNA01)["templates"]["T1"]
        self.assertEqual(t1["backing_tools"], [])
        self.assertIn("no_source", [p["binding"] for p in t1["placeholders"]])


class TemplateTests(Base):
    def test_stage00_templates(self):
        cited(self, S00, 335, "**T4a — Path inspected, awaiting confirmation**")
        t = self.contract(S00)["templates"]
        self.assertEqual(sorted(t), sorted(["T1", "T3", "T3b", "T4a", "T4b", "T5", "T6", "T7",
                                            "T8", "T9"]))
        self.assertEqual(t["T4a"]["line"], 335)

    def test_accept_tokens(self):
        cited(self, S01, 408, "Reply `verify` to run it, or `skip` to trust the files.")
        cited(self, S01, 383, "Confirm to overwrite, or reply `cancel` to stop.")
        cited(self, S00, 360, "or reply `skip` to omit this assay.")
        t01 = self.contract(S01)["templates"]
        self.assertEqual(t01["T8"]["accept_tokens"], ["verify", "skip"])
        self.assertEqual(t01["T5"]["accept_tokens"], ["cancel"])
        self.assertEqual(t01["T7"]["accept_tokens"], ["cancel"])
        self.assertEqual(self.contract(S00)["templates"]["T5"]["accept_tokens"], ["skip"])
        # The pilot: "Only verify, skip and cancel are fixed answers."
        self.assertEqual(sorted(self.result["summary"]["accept_tokens"]),
                         ["cancel", "skip", "verify"])

    def test_ask_kinds(self):
        t00 = self.contract(S00)["templates"]
        self.assertEqual(t00["T1"]["ask"], "question")
        self.assertEqual(t00["T4a"]["ask"], "gate")
        self.assertEqual(t00["T4a"]["accept_tokens"], [])
        self.assertEqual(self.contract(S03)["templates"]["T3"]["ask"], None)
        self.assertEqual(t00["T6"]["ask"], "handoff")

    def test_pilot_t4a_read_counts_unbound(self):
        cited(self, S00, 338, "Raw NGS files: <n> (<n> R1 / <n> R2, <layout>)")
        unbound = [p["label"] for p in self.contract(S00)["templates"]["T4a"]["unbound"]]
        self.assertEqual(sorted(unbound), ["r1", "r2"])

    def test_named_keys_bound(self):
        cited(self, REG01, 820, '"included_gb": round(incl_bytes / 1e9, 1),')
        t8 = self.contract(S01)["templates"]["T8"]
        self.assertEqual(t8["unbound"], [])
        bound = [p["text"] for p in t8["placeholders"] if p["binding"] == "key"]
        self.assertIn("<included_gb>", bound)
        self.assertIn("<full_check_estimate_min>", bound)

    def test_vocabulary_is_the_called_subcommands_not_the_modules(self):
        # 03:186 "Outputs: <n> declared": the only matching key, outputs_declared, is written by
        # approve (stage03_analysis.py:372), the user's command, not by create.
        cited(self, "gars/_system/stage03_analysis.py", 372, "outputs_declared")
        cited(self, S03, 186, "Outputs: <n> declared")
        t2 = self.contract(S03)["templates"]["T2"]
        bindings = {p["line"]: p["binding"] for p in t2["placeholders"] if p["text"] == "<n>"}
        self.assertEqual(bindings, {185: "unbound", 186: "unbound"})

    def test_labels_with_digits_and_table_rows_are_graded(self):
        cited(self, RNADE, 200, "Genes tested: <n> | Significant at padj < 0.05: <n>")
        t6 = [p for p in self.contract(RNADE)["templates"]["T6"]["placeholders"] if p["text"] == "<n>"]
        self.assertEqual([(p["binding"], p.get("key")) for p in t6],
                         [("label", "genes_tested"), ("unbound", None)])
        scqc = "gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md"
        cited(self, scqc, 164, "| Cells in | <n> |")
        cited(self, scqc, 165, "| Cells after QC | <n> |")
        rows = {p["line"]: (p["binding"], p.get("key")) for p in
                self.contract(scqc)["templates"]["T6"]["placeholders"] if p["text"] == "<n>"}
        self.assertNotEqual(rows[164][0], "label")       # n_cells_in is in summary.json only
        self.assertNotEqual(rows[165][0], "label")       # a per-sample dict, not a count
        cited(self, scqc, 116, "Thresholds: min_genes <n> | min_cells <n> | max_mito <n>% | HVG <n>")
        t1 = [p["binding"] for p in self.contract(scqc)["templates"]["T1"]["placeholders"]
              if p["line"] == 116]
        self.assertEqual(t1, ["no_source"] * 4)

    def test_a_per_sample_dict_is_not_a_count(self):
        # result["cells_after_qc"] is `summary.get("cells_after_qc") or {}`, one entry per sample
        # (scrna_qc_cluster.py:461, 490), so "Cells after QC: <n>" has no count behind it.
        cited(self, "gars/_system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py", 461,
              'after = summary.get("cells_after_qc") or {}')
        scqc = "gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md"
        cited(self, scqc, 165, "| Cells after QC | <n> |")
        row = [p for p in self.contract(scqc)["templates"]["T6"]["placeholders"] if p["line"] == 165]
        self.assertNotEqual(row[0]["binding"], "label")

    def test_sanitized_title_unbound_before_create(self):
        cited(self, S00, 305, "Project title: <raw> -> directory <sanitized>")
        t = self.contract(S00)["templates"]
        self.assertEqual([p["binding"] for p in t["T3"]["placeholders"] if p["text"] == "<sanitized>"],
                         ["unbound"])
        self.assertEqual([p.get("key") for p in t["T7"]["placeholders"] if p["text"] == "<sanitized>"],
                         ["sanitized_title"])

    def test_counts_bind_only_to_keys_the_result_carries(self):
        cut = "gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md"
        cited(self, cut, 201, "Groups: <n> (targets: <n>)")
        row = [p for p in self.contract(cut)["templates"]["T6"]["placeholders"] if p["line"] == 201]
        self.assertEqual(row[1]["binding"], "unbound")
        cited(self, S01, 413, "<n> sample(s) have raw data but no row in samples.csv")
        t7 = [p for p in self.contract(S01)["templates"]["T7"]["placeholders"] if p["line"] == 413]
        self.assertEqual(t7[0]["binding"], "unbound")
        cited(self, S00, 369, "| <Assay ID> | <n> | <n> | <path> |")
        t6 = [p for p in self.contract(S00)["templates"]["T6"]["placeholders"] if p["line"] == 369]
        self.assertEqual((t6[2]["binding"], t6[2].get("key")), ("label", "samples"))
        spv = "gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md"
        cited(self, spv, 184, "Samples: <n> | Pipeline:")
        s6 = [p for p in self.contract(spv)["templates"]["T6"]["placeholders"] if p["line"] == 184]
        self.assertEqual((s6[0]["binding"], s6[0].get("key")), ("label", "samples"))

    def test_dynamic_config_keys_reach_the_counts(self):
        # config_values[key] (stage01_samplesheet.py:779) takes its keys from the `config:` columns
        # of FORMATS (245) and joins counts at 824.
        cited(self, REG01, 779, "config_values[key] = value")
        cited(self, REG01, 824, 'out["counts"].update(config_values)')
        t2 = [p for p in self.contract(S01)["templates"]["T2"]["placeholders"]
              if p["text"] == "<strandedness>"]
        self.assertEqual((t2[0]["binding"], t2[0].get("label")), ("key", "strandedness"))

    def test_flow_vocabulary_excludes_keys_that_never_reach_the_result(self):
        voc = X.flow_vocabulary(X.HelperIndex(self.src), X.load_registry(self.src),
                                ["nfcore_cutandrun_wrapper.collect"])
        self.assertNotIn("target", voc)      # a symlink field in output_evidence, never emitted
        self.assertIn("failures", voc)

    def test_unexplained_dynamic_keys_make_absence_unknown(self):
        """Where the backing flow writes keys computed at run time that no key domain explains, a
        missing key is reported as unknown, never as unbound."""
        for c in self.result["contracts"]:
            for t in c["templates"].values():
                if t["dynamic_key_sites"]:
                    self.assertNotIn("unbound", [p["binding"] for p in t["placeholders"]],
                                     "%s %s" % (c["id"], t["id"]))
        t4a = self.contract(S00)["templates"]["T4a"]
        self.assertEqual(t4a["dynamic_key_sites"], [])
        self.assertEqual(sorted(p["label"] for p in t4a["unbound"]), ["r1", "r2"])
        # not vacuous on published data: the executor descriptor's run-time keys
        # (executorlib.py:205) reach status's flow through a whole-dict read, an
        # over-approximation the limits name (status emits none of them), so rnaseq-de's T2
        # carries the site; the binding rule itself is checked with a synthetic missing key
        cited(self, EXL, 205, "values[key] = _strip_value(rest)")
        t2 = self.contract(RNADE)["templates"]["T2"]
        self.assertIn("%s:205" % EXL, t2["dynamic_key_sites"])
        voc = X.flow_vocabulary(X.HelperIndex(self.src), X.load_registry(self.src),
                                ["executor.status"])
        self.assertIn("%s:205" % EXL, voc.dynamic)
        self.assertEqual(X.bind_placeholder("<nokey>", "x <nokey>", voc)["binding"], "unknown")

    def test_a_loop_key_resolves_from_the_loop_around_the_write(self):
        """stage01_samplesheet.py:779 writes config_values[key] inside `for key in
        config_columns(fmt)` (770), not inside the literal loop at 535 that also binds `key`."""
        import ast
        cited(self, REG01, 535, 'for key in ("unit_of_replication", "reference_release", "paired"):')
        cited(self, REG01, 770, "for key in config_columns(fmt):")
        code = ("def f(x, y, z, w, g, rows):\n"
                "    for key in ('a', 'b'):\n"
                "        x[key] = 1\n"
                "    for key in g():\n"
                "        y[key] = 2\n"
                "    for key, v in [('p', 1), ('q', 2)]:\n"
                "        z[key] = v\n"
                "    for key in ('c',):\n"
                "        key = g()\n"
                "        w[key] = 3\n"
                "    ks = [('m', 1)]\n"
                "    ks += [('n', 2)]\n"
                "    for key, v in ks:\n"
                "        x[key] = v\n")
        flow = X.Flow(self.src, X.HelperIndex(self.src))
        flow._nodes = X.pruned_nodes(ast.parse(code).body[0].body, None)
        def at(line):
            node = next(n for n in flow._nodes if isinstance(n, ast.Assign) and n.lineno == line
                        and isinstance(n.targets[0], ast.Subscript))
            return flow.resolve_dynamic(node.targets[0].slice, line)
        self.assertEqual(at(3), {"a", "b"})
        self.assertIsNone(at(5))
        self.assertEqual(at(7), {"p", "q"})
        self.assertIsNone(at(10))
        self.assertEqual(at(14), {"m", "n"})
        voc = X.flow_vocabulary(X.HelperIndex(self.src), X.load_registry(self.src),
                                ["stage01_samplesheet"])
        self.assertEqual(voc.dynamic, set())        # 779 is explained by its key domain
        self.assertIn("unknown", voc["strandedness"])

    def test_a_tuple_key_is_not_a_json_key(self):
        """units[(sample, "")] (stage00_register.py:226) cannot be emitted as JSON (json.dumps
        refuses tuple keys and nothing under gars/ passes skipkeys), so it is not a key site."""
        cited(self, REG00, 226, 'units[(sample, "")] = {"dir": name}')
        idx = X.HelperIndex(self.src)
        self.assertFalse(idx.skipkeys)
        voc = X.flow_vocabulary(idx, X.load_registry(self.src), ["stage00_register.inspect"])
        self.assertEqual(voc.dynamic, set())

    def test_item_key_rulings_explain_only_while_their_evidence_holds(self):
        cited(self, REG00, 705, 'per_assay[aid] = {"display": assay_map.get(aid, aid)')
        reg = X.load_registry(self.src)
        voc = X.flow_vocabulary(X.HelperIndex(self.src), reg, ["stage00_register.finalize"])
        self.assertEqual(voc.dynamic, set())
        self.assertEqual(X.check_key_rulings(self.src), [])

        class Edited(X.Source):
            def text(self, path):
                body = super().text(path)
                if path == REG00:
                    lines = body.split("\n")
                    lines[655] = lines[655].replace("for aid in assays:", "for aid in other:")
                    body = "\n".join(lines)
                return body
        edited = Edited(str(REPO), PIN)
        voc = X.flow_vocabulary(X.HelperIndex(edited), reg, ["stage00_register.finalize"])
        self.assertEqual(voc.dynamic, {"%s:705" % REG00})
        self.assertEqual(X.bind_placeholder("<nokey>", "x <nokey>", voc)["binding"], "unknown")
        self.assertEqual(X.check_key_rulings(edited),
                         [{"kind": "item_keys_void", "ruling": "stage00-per-assay",
                           "lines": ["%s:656" % REG00]}])

    def test_key_check_is_not_vacuous(self):
        vocab = X.key_vocabulary(self.src, ["_system/stage01_samplesheet.py"])
        self.assertIn("included_gb", vocab)
        self.assertNotIn("included_gbx", vocab)
        verdict = X.bind_placeholder("<included_gbx>", "Data: <included_gbx> GB", vocab)
        self.assertEqual(verdict["binding"], "unbound")


class CommandTests(Base):
    def test_unregistered_commands_in_process(self):
        cited(self, S01, 280, "true, submit the step-9 command with `sbatch` instead of running it inline.")
        cited(self, S01, 299, "`<ISO-8601 date>` with today's date.")
        names = sorted(self.result["summary"]["unregistered_in_process"])
        self.assertEqual(names, ["date", "sbatch"])

    def test_sbatch_at_stage01_step8(self):
        unreg = [c for c in self.step(S01, "8")["calls"] if c["tool"] is None]
        self.assertEqual([c["executable"] for c in unreg], ["sbatch"])

    def test_unknown_placeholder_is_reported_not_guessed(self):
        minimal, maximal, missing = X.instantiate(
            'python3 _system/x.py run --project projects/<title> [--extra <unknown thing>]')
        self.assertEqual(minimal, "python3 _system/x.py run --project projects/{project}")
        self.assertEqual(missing, ["<unknown thing>"])
        self.assertIn("--extra <unknown thing>", maximal)

    def test_commands_recounted_independently(self):
        """The test's own count of command-shaped text in every Process section (fenced lines and
        backtick spans that start with an executable, prose wrapper verbs, 're-run' phrases,
        "today's date") equals the calls the extractor found."""
        import re as _re
        execs = {"python3", "python", "bash", "sh", "sbatch", "squeue", "scancel", "sacct", "date",
                 "git", "source", "conda", "mamba", "pip", "pip3", "nextflow", "rm", "mv", "cp",
                 "ls", "cat", "head", "tail", "grep", "rg", "find", "wc", "stat", "shasum"}
        total = 0
        for path in EXPECTED_CONTRACTS:
            lines = show(path).split("\n")
            start = next(i for i, l in enumerate(lines) if l.startswith("## Process"))
            end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
            body, prose_parts, inside, pending = lines[start + 1:end], [], False, ""
            for l in body:
                if l.lstrip().startswith("```"):
                    inside = not inside
                    continue
                if inside:
                    s = l.strip()
                    if s.endswith("\\"):
                        pending += s[:-1] + " "
                        continue
                    s = pending + s
                    pending = ""
                    if s and s.split()[0] in execs:
                        total += 1
                    continue
                prose_parts.append(l.strip())
            text = " ".join(prose_parts)
            total += sum(1 for m in _re.finditer(r"`([^`]+)`", text) if m.group(1).split()[0] in execs)
            total += len(_re.findall(r"today's date", text))
            total += len(_re.findall(r"\bre-run (?:`\w+`|without `--)", text))
            if "wrappers/" in show(path) and path not in (S00, S01, S02, S03):
                total += len(_re.findall(r"\b[Rr]un (?:the wrapper's )?`(?:check|prepare|collect|summary)`", text))
        self.assertEqual(self.result["summary"]["command_accounting"]["seen"], total)


class GuardTests(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp = tempfile.mkdtemp(prefix="stepmap-guard-")
        cls.guard = X.GuardHarness(cls.src, cls.tmp)

    @classmethod
    def tearDownClass(cls):
        cls.guard.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_sample_id_pattern_refused(self):
        # policy.py:246 refuses a quoted ; | & < > outside file tools; a named group needs < >.
        cited(self, POLICY, 246, "if quoted_operator and (not tokens or tokens[0] not in filesystem):")
        cmd = ("python3 _system/stage00_register.py inspect --assay rnaseq_bulk --source {source} "
               "--sample-id-pattern '(?P<sample>[A-Za-z0-9]+)_R(?P<read>[12]).fastq.gz'")
        d = self.guard.bash("fresh_declared", cmd)
        self.assertIs(d["allow"], False, d["reason"])
        self.assertIn("quoted operator", d["reason"])
        d = self.guard.bash("fresh_declared", cmd.split(" --sample-id-pattern")[0])
        self.assertIs(d["allow"], True, d["reason"])

    def test_inspect_needs_a_declared_source(self):
        cited(self, GUARD, 849, "stage 00 %s prints file and sample names into the prompt")
        d = self.guard.bash("fresh", "python3 _system/stage00_register.py inspect --assay "
                                     "rnaseq_bulk --source {source}")
        self.assertIs(d["allow"], False, d["reason"])

    def test_agent_cannot_classify_public(self):
        cited(self, GUARD, 719, "classifying data is the owner's")
        d = self.guard.bash("fresh", "python3 _system/stage00_register.py finalize --project "
                                     "projects/{project} --data-class public --purpose fixture "
                                     "--agreement-ref none --model claude-opus-5-5")
        self.assertIs(d["allow"], False, d["reason"])
        self.assertIn("classifying data is the owner's", d["reason"])

    def test_stage01_closed_vs_public(self):
        cmd = "python3 _system/stage01_samplesheet.py --project projects/{project} --check"
        self.assertIs(self.guard.bash("public", cmd)["allow"], True)
        self.assertIs(self.guard.bash("closed", cmd)["allow"], False)

    def test_sbatch_refused(self):
        d = self.guard.bash("public", "sbatch projects/{project}/run.sh")
        self.assertIs(d["allow"], False, d["reason"])
        self.assertIn("not registered", d["reason"])

    def test_history_append_closed_vs_public(self):
        self.assertIs(self.guard.edit("public", "projects/{project}/HISTORY.md")["allow"], True)
        self.assertIs(self.guard.edit("closed", "projects/{project}/HISTORY.md")["allow"], False)

    def test_guard_matrix_present_for_every_mapped_call(self):
        missing, checked = [], 0
        for c in self.result["contracts"]:
            for s in c["steps"]:
                for call in s["calls"]:
                    if call["tool"]:
                        checked += 1
                        if not call.get("guard"):
                            missing.append((c["path"], s["n"], call["command"]))
        self.assertEqual(missing, [])
        self.assertGreaterEqual(checked, 60)   # non-vacuity: an empty walk is not coverage


class SpanTests(unittest.TestCase):
    """span_accounting compares two independent counts; each must be able to disagree."""

    def run_doc(self, body):
        text = "# x\n## Process\n" + body + "\n## Response Format\n"
        doc = X.parse_markdown(text)
        step = X.parse_steps(doc)[0]
        prose_text, offsets = X.prose(doc, step["start"], step["end"])
        calls, _ = X.step_calls(doc, step, [], (None, None))
        return X.span_accounting(doc, step, prose_text, calls)

    def test_clean_step_is_consistent(self):
        s = self.run_doc("1. Run `python3 _system/x.py go --a b` and reply `T1`.")
        self.assertIs(s["consistent"], True)

    def test_odd_backtick_is_caught(self):
        s = self.run_doc("1. Run `python3 _system/x.py go and reply `T1`.")
        self.assertIs(s["consistent"], False)

    def test_helper_named_outside_backticks_is_caught(self):
        s = self.run_doc("1. Run python3 _system/x.py go, then reply `T1`.")
        self.assertIs(s["consistent"], False)


class FileActionTests(Base):
    def actions(self, path, n):
        return [(a["tool"], a["path"]) for a in self.step(path, n)["file_actions"]]

    def test_history_appends(self):
        cited(self, S01, 298, "13. Append the script's `history_entry` to the project's `HISTORY.md` **verbatim**")
        self.assertEqual(self.actions(S01, "13"), [("Edit", "projects/{project}/HISTORY.md")])
        cited(self, RNA01, 111, "9. Exit 0 → `collect` has written `OUTPUTS.tsv` and `STATUS COMPLETE`. Append its")
        self.assertEqual(self.actions(RNA01, "9"), [("Edit", "projects/{project}/HISTORY.md")])

    def test_reads_and_writes(self):
        cited(self, S02, 155, "5. Read each sub-stage's STATUS file")
        self.assertEqual(self.actions(S02, "5"), [("Read", "{substage_dir}/STATUS")])
        cited(self, S02, 124, "3. Check preconditions: `01_samplesheets/<Assay ID>_samplesheet.csv` and `_design.csv` exist")
        self.assertEqual(self.actions(S02, "3"),
                         [("Read", "projects/{project}/01_samplesheets/{assay}_samplesheet.csv")])
        cited(self, S03, 135, "7. Execute the approved plan literally: write its scripts under `scripts/`")
        self.assertIn(("Write", "projects/{project}/03_custom_analysis/01_qc-look/scripts/run.sh"),
                      self.actions(S03, "7"))
        cited(self, S01, 249, "2. Resolve the project directory from the title. Read each assay config")
        self.assertEqual(self.actions(S01, "2")[:2],
                         [("Read", "projects/{project}/_config/{assay}.yaml"),
                          ("Edit", "projects/{project}/_config/{assay}.yaml")])

    def test_history_append_refused_on_a_closed_project(self):
        a = self.step(S01, "13")["file_actions"][0]
        self.assertIs(a["guard"]["public"]["allow"], True)
        self.assertIs(a["guard"]["closed"]["allow"], False)

    def test_finalize_graded_for_every_class(self):
        cited(self, S00, 58, "Finalize requires `--data-class` (`public`, `deidentified_under_agreement`, or")
        call = [c for c in self.step(S00, "15")["calls"] if c["tool"]][0]
        forms = call["guard"]["forms"]
        self.assertIs(forms["minimal"]["decisions"]["fresh_declared"]["allow"], True)
        for value in ("deidentified_under_agreement", "identifiable"):
            self.assertIs(forms["class=" + value]["decisions"]["fresh_declared"]["allow"], False)


class Mechanics(unittest.TestCase):
    """The walker's own rules, on synthetic modules (no GARS file exercises them at the pin)."""

    class FakeSource:
        def __init__(self, files):
            self.files = files

        def text(self, path):
            return self.files[path]

        def exists(self, path):
            return path in self.files

    MOD = """
import argparse, sys
EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2, 3
def emit(result, code):
    return code
def failure(result, code=EXIT_FAILURE):
    return emit(result, code)
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=None)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.workspace is not None and args.workspace != ".":
        return emit({}, EXIT_REFUSED)
    if args.check:
        return emit({}, EXIT_OK)
    return failure({})
"""

    def exits(self, words):
        src = self.FakeSource({"gars/_system/fake.py": self.MOD})
        index = X.HelperIndex(src)
        tool = {"name": "fake", "argv": ["python3", "_system/fake.py"]}
        return X.helper_exits(src, index, tool, words)[0]

    FLOW = """
def emit(result, code):
    return code
def wrap(rows):
    return [dict(r) for r in rows]
def pair():
    return {"kept": 1}, {"dropped": 2}
def main(argv=None):
    rows = [{"deep": 1}]
    menu = wrap(rows)
    a, b = pair()
    return emit({"menu": menu, "first": a}, 0)
"""

    def flow_keys(self):
        src = self.FakeSource({"gars/_system/flow.py": self.FLOW})
        index = X.HelperIndex(src)
        return X.flow_vocabulary(index, [{"name": "flow", "argv": ["python3", "_system/flow.py"]}],
                                 ["flow"], src)

    def test_a_callees_parameter_flows_back_to_the_callers_argument(self):
        self.assertIn("deep", self.flow_keys())

    def test_only_the_kept_tuple_position_flows(self):
        keys = self.flow_keys()
        self.assertIn("kept", keys)
        self.assertNotIn("dropped", keys)

    def test_default_exit_code_is_resolved(self):
        codes = self.exits(["python3", "_system/fake.py"])
        self.assertIn("1", codes)              # failure(result) with code defaulting to EXIT_FAILURE
        self.assertNotIn("None", codes)

    def test_and_or_pruned_by_flags(self):
        self.assertNotIn("2", {c for c, s in self.exits(["python3", "_system/fake.py"]).items()
                               if any(x["how"] != "argparse" for x in s)})
        with_ws = self.exits(["python3", "_system/fake.py", "--workspace", "w"])
        self.assertIn("2", {c for c, s in with_ws.items() if any(x["how"] != "argparse" for x in s)})

    def test_flag_branch_stops_the_block(self):
        codes = self.exits(["python3", "_system/fake.py", "--check"])
        self.assertEqual(sorted(c for c, s in codes.items() if any(x["how"] != "argparse" for x in s)),
                         ["0"])


class AccountingTests(Base):
    def test_graded_means_checked_against_keys(self):
        acc = self.result["summary"]["placeholder_accounting"]
        graded = sum(acc["by_binding"].get(b, 0) for b in ("key", "label", "unbound"))
        self.assertEqual(acc["graded"], graded)

    def test_placeholders_recounted_independently(self):
        """The test's own count of <...> placeholders inside the first fence after each bold
        template heading equals the placeholders the extractor graded or declined to grade."""
        import re as _re
        total = 0
        for path in EXPECTED_CONTRACTS:
            lines = show(path).split("\n")
            i, in_rf = 0, False
            while i < len(lines):
                if lines[i].startswith("## "):
                    in_rf = lines[i].startswith("## Response Format")
                if in_rf and _re.match(r"^\*\*T\d+[a-z]? [—–-] ", lines[i]):
                    j = i + 1
                    while not lines[j].lstrip().startswith("```"):
                        j += 1
                    k = j + 1
                    while not lines[k].lstrip().startswith("```"):
                        total += len(_re.findall(r"<[^<>\n]+>", lines[k]))
                        k += 1
                    i = k
                i += 1
        acc = self.result["summary"]["placeholder_accounting"]
        self.assertEqual(acc["seen"], total)
        self.assertGreater(acc["by_binding"].get("unbound", 0), 0)

    def test_spans_counted_independently(self):
        """Backticks counted in the raw lines equal the spans the prose parser classified, and
        every command-shaped span became a call: a dropped line or span shows here."""
        spans = self.result["summary"]["span_accounting"]
        self.assertEqual(spans["inconsistent_steps"], [])
        self.assertEqual(spans["raw_backtick_pairs"], spans["seen"])
        self.assertGreater(spans["seen"], 400)
        self.assertEqual(self.step(S00, "10")["spans"]["by_class"].get("subcommand"), 1)

    def test_handled_codes_that_no_helper_emits_are_published(self):
        """A contract may branch on a code its helper never emits; the summary says how many."""
        s = self.result["summary"]["exits"]
        self.assertIn("handled_not_emitted", s)
        self.assertLessEqual(s["handled_and_emitted"], s["handled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
