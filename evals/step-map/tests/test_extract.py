#!/usr/bin/env python3
"""Red-first tests for the GARS step-map extractor (evals/step-map/extract.py).

Every expected value is grounded in a file and line at the pinned commit, and each test
re-reads that line (`cited`) so the expectation cannot drift away from its source.
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
        self.assertEqual(X.exit_codes("Exit non-zero → reply T5"), [1, 2, 3])

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

    def test_pilot_create_exit_3(self):
        self.assertEqual(self.unhandled(S00, "stage00_register.create"), [3])

    def test_pilot_link_exit_2_and_also_3(self):
        # Pilot: "link exit 2". The extractor also finds exit 3 (stage00_register.py:500).
        self.assertEqual(self.unhandled(S00, "stage00_register.link"), [2, 3])

    def test_pilot_finalize_exit_2(self):
        self.assertEqual(self.unhandled(S00, "stage00_register.finalize"), [2])

    def test_inspect_fully_handled(self):
        self.assertEqual(self.unhandled(S00, "stage00_register.inspect"), [])

    def test_branch_before_a_call_belongs_to_the_previous_call(self):
        # 00:219 "6. Exit 0 → take its assay_ids" answers step 4's `assays --select`.
        sites = [s for s in self.contract(S00)["call_sites"] if s["step"] == "4"]
        self.assertEqual(len(sites), 1)
        self.assertIn(0, sites[0]["handled"])
        self.assertIn(2, sites[0]["handled"])

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

    def test_sample_id_pattern_variant_refused_where_intended(self):
        cited(self, S00, 242, "`inspect` with `--sample-id-pattern '<their answer as a regex with named groups")
        e = self.flag(S00, "10", "--sample-id-pattern")
        self.assertEqual((e["target_tool"], e["target_step"]), ("stage00_register.inspect", "9"))
        g = e["guard"]
        self.assertEqual(g["intended"], "fresh_declared")
        self.assertIs(g["allowed_where_intended"], False)

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


class ReachabilityTests(Base):
    def site(self, path, step, tool):
        hits = [s for s in self.contract(path)["call_sites"] if s["step"] == step and s["tool"] == tool]
        self.assertEqual(len(hits), 1)
        return hits[0]

    def test_check_mode_cannot_emit_the_writers_gate(self):
        # stage01_samplesheet.py:1069-1073 returns before the blocked branch (1085) in --check.
        cited(self, REG01, 1069, "if args.check:")
        cited(self, REG01, 1085, "return emit(result, EXIT_NEEDS_CONFIRM)")
        self.assertEqual(self.site(S01, "3", "stage01_samplesheet")["emitted"], [0, 1, 3])
        self.assertEqual(self.site(S01, "9", "stage01_samplesheet")["emitted"], [0, 1, 2, 3])

    def test_assays_without_select_cannot_refuse(self):
        cited(self, REG00, 296, "if args.select is None:")
        self.assertEqual(self.site(S00, "3", "stage00_register.assays")["emitted"], [0, 3])

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

    def test_every_seen_command_is_accounted_for(self):
        acc = self.result["summary"]["command_accounting"]
        self.assertEqual(acc["seen"], acc["mapped"] + acc["unregistered"] + acc["uninstantiable"])
        self.assertGreater(acc["seen"], 0)


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


class AccountingTests(Base):
    def test_placeholder_accounting(self):
        acc = self.result["summary"]["placeholder_accounting"]
        self.assertEqual(acc["seen"], sum(acc["by_binding"].values()))
        self.assertGreater(acc["by_binding"].get("unbound", 0), 0)

    def test_summary_counts_are_derived(self):
        s = self.result["summary"]
        self.assertEqual(s["contracts"], 14)
        self.assertEqual(s["exits"]["emitted"], sum(len(cs["emitted"]) for c in self.result["contracts"]
                                                    for cs in c["call_sites"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
