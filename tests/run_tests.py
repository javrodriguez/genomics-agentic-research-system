#!/usr/bin/env python3
"""Tests for the GARS deterministic core.

Run:  python3 tests/run_tests.py            (from the repo root)

Runs on stock python 3.6.8, stdlib only -- the same interpreter contract as the `_system/`
helpers themselves (decision 0011), so the suite runs anywhere the helpers run, with no conda.

What is covered, and why (decision 0023):
- every `_system/` helper, through its real CLI, in a throwaway workspace built per run;
- determinism: stage 01's emitted artifacts are byte-identical across runs -- the property
  that justified moving artifact generation into code at all;
- the guard hook's allow/deny matrix (decision 0022) -- each deny is an action no contract
  instructs, each allow is a step a contract does instruct;
- the contract lint and script<->contract vocabulary drift check (tests/check_contracts.py).

The temp workspace COPIES `_system/`, `_references/` and `_templates/` rather than symlinking
them: `workspace.workspace_root()` resolves symlinks, and a symlinked copy would write into the
real repository's `projects/`.
"""

import csv
import gzip
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GARS = REPO / "gars"

sys.path.insert(0, str(GARS / "_system"))
import workspace  # noqa: E402 -- the single source of truth for the pipeline pins


def needs_pipeline(assay):
    """Skip when the assay's pinned nf-core checkout is absent from this machine.

    Off-cluster there is no $GARS_PIPELINES tree, preflight rightly refuses, and the tests
    that need `check` to PASS cannot run -- they skip as environment failures rather than
    fail, which is the behaviour the README documents for a cluster-less checkout. The pin
    names come from workspace.PIPELINES, never restated here."""
    key = workspace.PIPELINES[assay]
    root = Path(os.environ.get("GARS_PIPELINES")
                or str(Path.home() / "install" / "nf-core-pipelines"))
    checkout = root / key.replace("nf-core-", "")
    return unittest.skipUnless(
        checkout.is_dir(), "environment: no pinned checkout at %s" % checkout)


def run(script, args, cwd, env_extra=None, stdin_data=None):
    """Run a _system/ helper (or any command list) and return (exit_code, parsed_json_or_None, raw)."""
    if isinstance(script, (str, Path)):
        cmd = [sys.executable, str(script)] + list(args)
    else:
        cmd = list(script) + list(args)
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env,
                          input=stdin_data.encode() if stdin_data else None)
    out = proc.stdout.decode("utf-8", "replace")
    try:
        payload = json.loads(out) if out.strip() else None
    except ValueError:
        payload = None
    return proc.returncode, payload, out + proc.stderr.decode("utf-8", "replace")


def write_fastq_gz(path, reads=3):
    """A tiny but structurally valid gzipped FASTQ."""
    lines = []
    for i in range(reads):
        lines += ["@read%d" % i, "ACGTACGT", "+", "IIIIIIII"]
    with gzip.open(str(path), "wt") as fh:
        fh.write("\n".join(lines) + "\n")


class WorkspaceFixture(unittest.TestCase):
    """A throwaway workspace with two paired-end samples, driven through stages 00 and 01
    exactly as the contracts drive them. Class-level so the chain builds once."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-test-"))
        cls.ws = cls.tmp / "gars"
        cls.ws.mkdir()
        for d in ("_system", "_references", "_templates"):
            shutil.copytree(str(GARS / d), str(cls.ws / d))
        (cls.ws / "projects").mkdir()
        # raw data: 2 samples x 1 lane, paired-end, bcl2fastq names
        cls.src = cls.tmp / "seqrun"
        cls.src.mkdir()
        for s in ("TUMOR1_S1", "TUMOR2_S2", "CTRL1_S3", "CTRL2_S4"):
            for r in ("R1", "R2"):
                write_fastq_gz(cls.src / ("%s_L001_%s_001.fastq.gz" % (s, r)))
        (cls.src / "notes.txt").write_text("not a fastq\n")
        cls.reg = cls.ws / "_system" / "stage00_register.py"
        cls.sheet = cls.ws / "_system" / "stage01_samplesheet.py"
        cls.project = cls.ws / "projects" / "tall-test"

    @classmethod
    def tearDownClass(cls):
        # files.csv is 0444; make the tree deletable first
        for root, dirs, files in os.walk(str(cls.tmp)):
            for f in files:
                p = os.path.join(root, f)
                try:
                    os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
                except OSError:
                    pass
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    # -- stage 00 ---------------------------------------------------------------------------

    def test_00_assay_menu_and_selection(self):
        code, res, _ = run(self.reg, ["assays"], self.ws)
        self.assertEqual(code, 0)
        self.assertTrue(any(r["assay_id"] == "rnaseq_bulk" for r in res["assays"]))
        code, res, _ = run(self.reg, ["assays", "--select", "Bulk RNA-seq"], self.ws)
        self.assertEqual(code, 0)
        self.assertEqual(res["assay_ids"], ["rnaseq_bulk"])
        # an unsupported assay is refused, not guessed
        code, res, _ = run(self.reg, ["assays", "--select", "single-cell ATAC"], self.ws)
        self.assertEqual(code, 2)

    def test_01_create_seeds_config(self):
        code, res, raw = run(self.reg, ["create", "--title", "tall-test",
                                        "--assays", "rnaseq_bulk"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertTrue((self.project / "_config" / "rnaseq_bulk.yaml").is_file())
        self.assertTrue((self.project / "_config" / "nextflow.slurm.config").is_file())
        self.assertTrue((self.project / "HISTORY.md").is_file())
        text = (self.project / "_config" / "rnaseq_bulk.yaml").read_text()
        self.assertIn("<REQUIRED>", text)

    def test_02_inspect_derives_units(self):
        code, res, raw = run(self.reg, ["inspect", "--assay", "rnaseq_bulk",
                                        "--source", str(self.src)], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(res["layout"], "paired-end")
        self.assertEqual(res["sample_ids"], ["CTRL1", "CTRL2", "TUMOR1", "TUMOR2"])
        self.assertIn("notes.txt", res["excluded_examples"])

    def test_03_link_and_finalize(self):
        code, _, raw = run(self.reg, ["link", "--project", "projects/tall-test",
                                      "--assay", "rnaseq_bulk", "--source", str(self.src)],
                           self.ws)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(self.reg, ["finalize", "--project", "projects/tall-test"], self.ws)
        self.assertEqual(code, 0, raw)
        files_csv = self.project / "00_data" / "rnaseq_bulk" / "files.csv"
        samples_csv = self.project / "00_data" / "rnaseq_bulk" / "samples.csv"
        self.assertTrue(files_csv.is_file())
        self.assertTrue(samples_csv.is_file())
        # machine ownership is enforced, not advised (decision 0018)
        self.assertEqual(stat.S_IMODE(files_csv.stat().st_mode), 0o444)

    def test_04_finalize_preserves_filled_design(self):
        samples_csv = self.project / "00_data" / "rnaseq_bulk" / "samples.csv"
        with samples_csv.open() as fh:
            rows = list(csv.reader(fh))
        head = rows[0]
        for r in rows[1:]:
            sid = r[head.index("sample_id")]
            r[head.index("condition")] = "MT" if sid.startswith("TUMOR") else "WT"
            r[head.index("group")] = "G1" if sid.endswith("1") else "G2"
            r[head.index("replicate")] = "1" if sid.endswith("1") else "2"
        with samples_csv.open("w", newline="") as fh:
            csv.writer(fh).writerows(rows)
        before = samples_csv.read_bytes()
        code, res, raw = run(self.reg, ["finalize", "--project", "projects/tall-test"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(samples_csv.read_bytes(), before,
                         "finalize must never overwrite a user-filled samples.csv (0017)")

    # -- stage 01 ---------------------------------------------------------------------------

    def test_05_samplesheet_check_then_write(self):
        code, res, raw = run(self.sheet, ["--project", "projects/tall-test", "--check"], self.ws)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(self.sheet, ["--project", "projects/tall-test"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("history_entry", res)
        self.assertIn("Model: ", res["history_entry"])
        sheet = self.project / "01_samplesheets" / "rnaseq_bulk_samplesheet.csv"
        design = self.project / "01_samplesheets" / "rnaseq_bulk_design.csv"
        self.assertTrue(sheet.is_file() and design.is_file())
        # paths stay inside the project and do not dereference symlinks (08-19 defect)
        with sheet.open() as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            self.assertIn("/projects/tall-test/00_data/", row["fastq_1"])

    def test_06_samplesheets_are_deterministic(self):
        sheet = self.project / "01_samplesheets" / "rnaseq_bulk_samplesheet.csv"
        design = self.project / "01_samplesheets" / "rnaseq_bulk_design.csv"
        a = sheet.read_bytes(), design.read_bytes()
        code, _, raw = run(self.sheet, ["--project", "projects/tall-test", "--force"], self.ws)
        self.assertEqual(code, 0, raw)
        b = sheet.read_bytes(), design.read_bytes()
        self.assertEqual(a, b, "same design must emit byte-identical artifacts (0011)")

    def test_07_hand_edited_files_csv_is_caught(self):
        files_csv = self.project / "00_data" / "rnaseq_bulk" / "files.csv"
        os.chmod(str(files_csv), 0o644)
        rows = files_csv.read_text().splitlines()
        files_csv.write_text("\n".join(rows[:-1]) + "\n")   # drop one unit
        os.chmod(str(files_csv), 0o444)
        code, res, raw = run(self.sheet, ["--project", "projects/tall-test",
                                          "--check"], self.ws)
        self.assertEqual(code, 1, raw)
        checks = [f["check"] for a in res["assays"].values() for f in a.get("failures", [])]
        self.assertIn("registry", checks)
        # restore
        code, _, raw = run(self.reg, ["finalize", "--project", "projects/tall-test"], self.ws)
        self.assertEqual(code, 0, raw)
        code, _, raw = run(self.sheet, ["--project", "projects/tall-test", "--force"], self.ws)
        self.assertEqual(code, 0, raw)

    def test_08_model_flag_lands_in_history(self):
        code, res, raw = run(self.sheet, ["--project", "projects/tall-test", "--force",
                                          "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("Model: claude-test-1", res["history_entry"])

    # -- configure --------------------------------------------------------------------------

    def test_09_configure_menus(self):
        cfg = self.ws / "_system" / "configure.py"
        code, res, raw = run(cfg, ["genomes"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertTrue(any("GRCh38" in g["id"] for g in res["genomes"]))
        code, res, raw = run(cfg, ["contrasts", "--project", "projects/tall-test",
                                   "--assay", "rnaseq_bulk"], self.ws)
        self.assertEqual(code, 0, raw)
        # levels come from the design actually on disk
        self.assertEqual(set(res["levels"]), {"MT", "WT"})
        self.assertTrue(all(p["testable"] for p in res["contrasts"]))

    def test_10_configure_apply_dry_run(self):
        cfg = self.ws / "_system" / "configure.py"
        code, res, raw = run(cfg, ["genomes"], self.ws)
        entry = res["genomes"][0]
        if not (entry["fasta_readable"] and entry["gtf_readable"]):
            # the registry points at the cluster's reference tree; off-cluster `apply`
            # rightly refuses, so this is an environment failure, not a defect
            self.skipTest("environment: registry reference %s not on this machine"
                          % entry["id"])
        gid = entry["id"]
        code, res, raw = run(cfg, ["apply", "--project", "projects/tall-test",
                                   "--assay", "rnaseq_bulk", "--genome", gid,
                                   "--contrast", "condition,MT,WT", "--dry-run"], self.ws)
        self.assertEqual(code, 0, raw)
        yaml_text = (self.project / "_config" / "rnaseq_bulk.yaml").read_text()
        self.assertIn("<REQUIRED>", yaml_text)  # dry run wrote nothing

    # -- resolve_artifact -------------------------------------------------------------------

    def test_11_resolver_prefers_native_and_gates_on_status(self):
        res_py = self.ws / "_system" / "resolve_artifact.py"
        sub = self.project / "02_bioinformatics" / "rnaseq_bulk" / "01_nfcore-rnaseq-wrapper"
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "OUTPUTS.tsv").write_text(
            "# type\trole\tpath\ncounts_gene\tnative\tresults/counts.tsv\n")
        (sub / "results").mkdir(exist_ok=True)
        (sub / "results" / "counts.tsv").write_text("gene_id\ts1\ng1\t1\n")
        # no STATUS yet -> not resolvable
        code, res, raw = run(res_py, ["--project", "projects/tall-test",
                                      "--assay", "rnaseq_bulk", "--type", "counts_gene"],
                             self.ws)
        self.assertNotEqual(code, 0, "must not resolve from an incomplete sub-stage")
        (sub / "STATUS").write_text("COMPLETE 2026-08-24T00:00:00\n")
        code, res, raw = run(res_py, ["--project", "projects/tall-test",
                                      "--assay", "rnaseq_bulk", "--type", "counts_gene"],
                             self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("counts.tsv", res["resolved"]["counts_gene"]["resolved"])

    # -- adapt_counts -----------------------------------------------------------------------

    def test_12_adapt_counts_renames_and_verifies(self):
        adapt = self.ws / "_system" / "adapt_counts.py"
        srcm = self.tmp / "gene_counts.tsv"
        with srcm.open("w") as fh:
            fh.write("gene_id\tgene_name\tS1\tS2\n")
            fh.write("ENSG01\tTP53\t10.4\t3.0\n")
            fh.write("ENSG02\tMYC\t0\t7.9\n")
        outdir = self.tmp / "adapted"
        outdir.mkdir(exist_ok=True)
        code, res, raw = run(adapt, ["--counts", str(srcm), "--out", str(outdir)], self.ws)
        self.assertEqual(code, 0, raw)
        header = (outdir / "counts_gene.tsv").read_text().splitlines()[0].split("\t")
        self.assertEqual(header[0], "gene",
                         "identifier column must be named 'gene' (decisions 0010/0021)")
        self.assertNotIn("gene_name", header)

    # -- stage 03 ---------------------------------------------------------------------------

    def test_12a_stage03_gates(self):
        """create -> draft -> approve -> execute -> verify, with both gates exercised."""
        s3 = self.ws / "_system" / "stage03_analysis.py"
        # create allocates 01_<slug> and a skeleton
        code, res, raw = run(s3, ["create", "--project", "projects/tall-test",
                                  "--slug", "PCA of Samples!!"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(res["analysis"], "01_pca-of-samples")
        adir = self.project / "03_custom_analysis" / "01_pca-of-samples"
        plan = adir / "PLAN.md"
        self.assertIn("<FILL:", plan.read_text())

        # gate 1: approve refuses a skeleton
        code, res, raw = run(s3, ["approve", "--project", "projects/tall-test",
                                  "--analysis", "01_pca-of-samples"], self.ws)
        self.assertEqual(code, 2, raw)
        self.assertTrue(any("skeleton" in b for b in res["blocked"]))

        # draft the plan; include one invalid type to prove the vocabulary is closed
        plan.write_text("""# Analysis plan: pca-of-samples

Status: DRAFT

## Goal
PCA of the count matrix to check sample clustering.

## Inputs
| Artifact type | Resolved from | Path |
|---|---|---|
| counts_gene | 01_nfcore-rnaseq-wrapper | results/counts.tsv |

## Method
1. Load the matrix; log-transform; PCA via scikit-learn (gars-bio).

## Outputs
| File | Type | Description |
|---|---|---|
| results/pca.csv | table | PC coordinates per sample |
| results/pca.png | picture | scatter of PC1 vs PC2 |

## Execution
Login node; seconds; kilobytes.
""")
        code, res, raw = run(s3, ["approve", "--project", "projects/tall-test",
                                  "--analysis", "01_pca-of-samples"], self.ws)
        self.assertEqual(code, 2, raw)
        self.assertTrue(any("picture" in b and "closed" in b for b in res["blocked"]))
        # ...and the missing venue line is caught in the same pass (decision 0027)
        self.assertTrue(any("Runs:" in b for b in res["blocked"]))

        # fix the type; venue gate: bare login-node is refused, the opt-in marker is required
        plan.write_text(plan.read_text().replace("| picture |", "| figure |"))
        plan.write_text(plan.read_text().replace("Login node; seconds; kilobytes.",
                                                 "Runs: login-node\nSeconds; kilobytes."))
        code, res, raw = run(s3, ["approve", "--project", "projects/tall-test",
                                  "--analysis", "01_pca-of-samples"], self.ws)
        self.assertEqual(code, 2, raw)
        self.assertTrue(any("not a recognised venue" in b for b in res["blocked"]))

        # the explicit user request is the only accepted login-node form
        plan.write_text(plan.read_text().replace("Runs: login-node",
                                                 "Runs: login-node (user-requested)"))
        code, res, raw = run(s3, ["approve", "--project", "projects/tall-test",
                                  "--analysis", "01_pca-of-samples"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("Status: APPROVED", plan.read_text())

        # gate 2: verify refuses while outputs are missing
        code, res, raw = run(s3, ["verify", "--project", "projects/tall-test",
                                  "--analysis", "01_pca-of-samples"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertEqual(sorted(res["missing"]), ["results/pca.csv", "results/pca.png"])

        # "execute", then verify completes and registers
        (adir / "results" / "pca.csv").write_text("sample,PC1,PC2\nTUMOR1,1,2\n")
        (adir / "results" / "pca.png").write_bytes(b"\x89PNG fake")
        code, res, raw = run(s3, ["verify", "--project", "projects/tall-test",
                                  "--analysis", "01_pca-of-samples",
                                  "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("Model: claude-test-1", res["history_entry"])
        self.assertIn("COMPLETE", (adir / "STATUS").read_text())
        outputs = (adir / "OUTPUTS.tsv").read_text()
        self.assertIn("table\tnative\tresults/pca.csv", outputs)

    def test_12b_stage03_verify_requires_approval(self):
        s3 = self.ws / "_system" / "stage03_analysis.py"
        code, res, raw = run(s3, ["create", "--project", "projects/tall-test",
                                  "--slug", "never-approved"], self.ws)
        self.assertEqual(code, 0, raw)
        name = res["analysis"]
        self.assertTrue(name.startswith("02_"), name)   # numbering advances
        code, res, raw = run(s3, ["verify", "--project", "projects/tall-test",
                                  "--analysis", name], self.ws)
        self.assertEqual(code, 2, raw)
        self.assertIn("not approved", res["error"])

    # -- integrity --------------------------------------------------------------------------

    def test_13_integrity_catches_truncation(self):
        sys.path.insert(0, str(self.ws / "_system"))
        try:
            import integrity
            good = self.src / "TUMOR1_S1_L001_R1_001.fastq.gz"
            self.assertIsNone(integrity.check_one(good, mode="full"))
            bad = self.tmp / "trunc.fastq.gz"
            bad.write_bytes(good.read_bytes()[:-5])
            problem = integrity.check_one(bad, mode="full")
            self.assertIsNotNone(problem, "a truncated gz must be reported")
            # quick mode deliberately does NOT catch truncation (decision 0013)
            self.assertIsNone(integrity.check_one(bad, mode="quick"))
        finally:
            sys.path.remove(str(self.ws / "_system"))
            sys.modules.pop("integrity", None)

    # -- workspace --------------------------------------------------------------------------

    def test_14_atomic_open_and_version(self):
        sys.path.insert(0, str(self.ws / "_system"))
        try:
            import workspace as w
            self.assertNotEqual(w.template_version(self.ws), "unknown")
            target = self.tmp / "atomic.txt"
            with w.atomic_open(target) as fh:
                fh.write("complete\n")
            self.assertEqual(target.read_text(), "complete\n")
            self.assertFalse((self.tmp / "atomic.txt.tmp").exists())
        finally:
            sys.path.remove(str(self.ws / "_system"))
            sys.modules.pop("workspace", None)


class AtacseqWrapperTests(unittest.TestCase):
    """Wrapper #1 (decision 0028): the whole atacseq_bulk path offline — stage 00 accepts the
    assay, stage 01 emits its format, configure fills the peaks decisions from the genome, and
    the wrapper's check/prepare/collect gates behave. The genome registry is rewritten to
    fixture paths so no test ever reads the real references or writes the real cache."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-atac-"))
        cls.ws = cls.tmp / "gars"
        cls.ws.mkdir()
        for d in ("_system", "_references", "_templates"):
            shutil.copytree(str(GARS / d), str(cls.ws / d))
        (cls.ws / "projects").mkdir()
        # fixture genome: tiny readable fasta/gtf, temp cache root
        cls.refs = cls.tmp / "refs"
        (cls.refs / "derived").mkdir(parents=True)
        (cls.refs / "genome.fa.gz").write_bytes(gzip.compress(b">chr1\nACGT\n"))
        (cls.refs / "genome.gtf.gz").write_bytes(gzip.compress(b"chr1\tx\tgene\n"))
        reg = cls.ws / "_references" / "genomes.md"
        text = reg.read_text()
        header = text[:text.index("| GRCh38 |")]
        reg.write_text(header +
                       "| TESTG | Test species | T1 | fixture | %s | %s | %s | MT | 12345 |\n"
                       % (cls.refs / "genome.fa.gz", cls.refs / "genome.gtf.gz",
                          cls.refs / "derived"))
        # raw data: 2 samples, paired-end
        cls.src = cls.tmp / "seqrun"
        cls.src.mkdir()
        for s in ("ATAC1_S1", "ATAC2_S2"):
            for r in ("R1", "R2"):
                write_fastq_gz(cls.src / ("%s_L001_%s_001.fastq.gz" % (s, r)))
        cls.reg_py = cls.ws / "_system" / "stage00_register.py"
        cls.sheet_py = cls.ws / "_system" / "stage01_samplesheet.py"
        cls.cfg_py = cls.ws / "_system" / "configure.py"
        cls.wrap = cls.ws / "_system" / "wrappers" / "nfcore-atacseq-wrapper" \
            / "nfcore_atacseq_wrapper.py"
        cls.project = cls.ws / "projects" / "atac-test"
        cls.substage = cls.project / "02_bioinformatics" / "atacseq_bulk" \
            / "01_nfcore-atacseq-wrapper"

    tearDownClass = classmethod(lambda cls: WorkspaceFixture.tearDownClass.__func__(cls))

    def test_00_chain_to_samplesheet(self):
        code, res, raw = run(self.reg_py, ["assays", "--select", "ATAC-seq (bulk)"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(res["assay_ids"], ["atacseq_bulk"])
        code, res, raw = run(self.reg_py, ["create", "--title", "atac-test",
                                           "--assays", "atacseq_bulk"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("_config/atacseq_bulk.yaml", res["config_seeded"])
        code, _, raw = run(self.reg_py, ["link", "--project", "projects/atac-test",
                                         "--assay", "atacseq_bulk", "--source", str(self.src)],
                           self.ws)
        self.assertEqual(code, 0, raw)
        code, _, raw = run(self.reg_py, ["finalize", "--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 0, raw)
        samples_csv = self.project / "00_data" / "atacseq_bulk" / "samples.csv"
        with samples_csv.open() as fh:
            rows = list(csv.reader(fh))
        head = rows[0]
        for i, r in enumerate(rows[1:], 1):
            cond = "KO" if i == 1 else "WT"
            r[head.index("condition")] = cond
            r[head.index("group")] = cond
            r[head.index("replicate")] = "1"
        with samples_csv.open("w", newline="") as fh:
            csv.writer(fh).writerows(rows)
        code, res, raw = run(self.sheet_py, ["--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 0, raw)
        sheet = self.project / "01_samplesheets" / "atacseq_bulk_samplesheet.csv"
        lines = sheet.read_text().splitlines()
        self.assertEqual(lines[0], "sample,fastq_1,fastq_2,replicate",
                         "the emitted format is the assay's own, not the RNA layout")
        emitted = sorted(l.split(",")[0] for l in lines[1:])
        self.assertEqual(emitted, ["KO", "WT"],
                         "sample is the GROUP (0035) -- the pipeline's checker demands it")

    def test_00b_group_semantics_laws_refuse_early(self):
        # Non-contiguous replicate ids within a group die at stage 01, not in Slurm (0035).
        samples_csv = self.project / "00_data" / "atacseq_bulk" / "samples.csv"
        with samples_csv.open() as fh:
            rows = list(csv.reader(fh))
        head = rows[0]
        for r in rows[1:]:
            r[head.index("group")] = "G1"
            r[head.index("replicate")] = "2"  # both rep 2: duplicate AND non-contiguous
        with samples_csv.open("w", newline="") as fh:
            csv.writer(fh).writerows(rows)
        code, res, raw = run(self.sheet_py, ["--project", "projects/atac-test", "--check"],
                             self.ws)
        self.assertEqual(code, 1, raw)
        msgs = " ".join(f["detail"] for a in res["assays"].values()
                        for f in a.get("failures", []))
        self.assertIn("1..N", msgs)
        self.assertIn("must be unique", msgs)
        # a non-numeric replicate is refused at stage 01, not an hour into a Slurm job
        for i, r in enumerate(rows[1:], 1):
            r[head.index("replicate")] = "one" if i == 1 else "1"
        with samples_csv.open("w", newline="") as fh:
            csv.writer(fh).writerows(rows)
        code, res, raw = run(self.sheet_py, ["--project", "projects/atac-test", "--check"],
                             self.ws)
        self.assertEqual(code, 1, raw)
        msgs = " ".join(f["detail"] for a in res["assays"].values()
                        for f in a.get("failures", []))
        self.assertIn("positive integer", msgs)
        # restore the good design for the tests that follow
        for i, r in enumerate(rows[1:], 1):
            cond = "KO" if i == 1 else "WT"
            r[head.index("condition")] = cond
            r[head.index("group")] = cond
            r[head.index("replicate")] = "1"
        with samples_csv.open("w", newline="") as fh:
            csv.writer(fh).writerows(rows)
        code, _, raw = run(self.sheet_py, ["--project", "projects/atac-test", "--force"],
                           self.ws)
        self.assertEqual(code, 0, raw)

    def test_01_check_refuses_unfilled_config(self):
        code, res, raw = run(self.wrap, ["check", "--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("config_unfilled", [f["check"] for f in res["failures"]])

    def test_02_configure_fills_peaks_decisions(self):
        code, res, raw = run(self.cfg_py, ["peaks"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual([e["value"] for e in res["peak_types"]], ["narrow", "broad"])
        code, res, raw = run(self.cfg_py, ["genomes", "--assay", "atacseq_bulk"], self.ws)
        self.assertEqual(code, 0, raw)
        g = res["genomes"][0]
        self.assertTrue(g["derived_dir"].endswith("nf-core-atacseq-2.1.2"),
                        "the cache root must be keyed by the assay's pinned pipeline")
        # apply without the peaks decision is refused, not defaulted
        code, res, raw = run(self.cfg_py, ["apply", "--project", "projects/atac-test",
                                           "--assay", "atacseq_bulk", "--genome", "01"], self.ws)
        self.assertEqual(code, 3, raw)
        code, res, raw = run(self.cfg_py, ["apply", "--project", "projects/atac-test",
                                           "--assay", "atacseq_bulk", "--genome", "01",
                                           "--peaks-type", "narrow"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(res["still_unfilled"], [])
        cfg = (self.project / "_config" / "atacseq_bulk.yaml").read_text()
        self.assertIn("macs_gsize: 12345", cfg)
        self.assertIn("mito_name: MT", cfg)

    @needs_pipeline("atacseq_bulk")
    def test_03_prepare_is_deterministic(self):
        code, res, raw = run(self.wrap, ["check", "--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(self.wrap, ["prepare", "--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(res["params"]["narrow_peak"], "true")
        self.assertEqual(res["params"]["save_reference"], "true",
                         "empty keyed cache means the first run builds and publishes indices")
        a = ((self.substage / "params.yaml").read_bytes(),
             (self.substage / "submit.sh").read_bytes())
        code, _, raw = run(self.wrap, ["prepare", "--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 0, raw)
        b = ((self.substage / "params.yaml").read_bytes(),
             (self.substage / "submit.sh").read_bytes())
        self.assertEqual(a, b, "same inputs must produce byte-identical artifacts (0011)")
        submit = (self.substage / "submit.sh").read_text()
        for needle in ("#SBATCH --partition=", "gars-env.sh", "-resume",
                       ".gars_run_complete", "-params-file", "-profile apptainer"):
            self.assertIn(needle, submit)

    def _fake_results(self, samples, include_in_counts=None):
        ml = self.substage / "run" / "results" / "bwa" / "merged_library"
        peaks = ml / "macs2" / "narrow_peak"
        (peaks / "consensus").mkdir(parents=True, exist_ok=True)
        (ml / "bigwig").mkdir(parents=True, exist_ok=True)
        (self.substage / "run" / "results" / "multiqc" / "narrow_peak").mkdir(
            parents=True, exist_ok=True)
        for s in samples:
            (peaks / ("%s_REP1_peaks.narrowPeak" % s)).write_text("chr1\t1\t2\n")
            (ml / "bigwig" / ("%s_REP1.bigWig" % s)).write_text("bw")
            (ml / ("%s_REP1.mLb.clN.sorted.bam" % s)).write_text("bam")
        cols = "\t".join("%s_REP1.bam" % s for s in (include_in_counts or samples))
        (peaks / "consensus" / "consensus_peaks.mLb.clN.bed").write_text("chr1\t1\t2\tp1\n")
        (peaks / "consensus" / "consensus_peaks.mLb.clN.featureCounts.txt").write_text(
            "# fc\nGeneid\tChr\tStart\tEnd\tStrand\tLength\t%s\np1\tchr1\t1\t2\t+\t2\t1\t1\n" % cols)
        (self.substage / "run" / "results" / "multiqc" / "narrow_peak"
         / "multiqc_report.html").write_text("<html>ok</html>")

    def test_04_collect_gates(self):
        # before completion: refused
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 2, raw)
        # content gate: a sample missing from the count matrix header is caught
        self._fake_results(["KO", "WT"], include_in_counts=["KO"])
        (self.substage / "run" / ".gars_run_complete").write_text("now\n")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("counts_peaks", [f["check"] for f in res["failures"]])
        # full tree: passes, registers, stamps
        self._fake_results(["KO", "WT"])
        # fake built indices so the derived cache is harvested
        built = self.substage / "run" / "results" / "genome" / "index" / "bwa"
        built.mkdir(parents=True, exist_ok=True)
        (built / "genome.amb").write_text("idx")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/atac-test",
                                         "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("Model: claude-test-1", res["history_entry"])
        self.assertEqual(res["derived_cache"]["action"], "populated")
        keyed = self.refs / "derived" / "nf-core-atacseq-2.1.2"
        self.assertTrue((keyed / "bwa" / "genome.amb").is_file())
        self.assertTrue((keyed / "PROVENANCE").is_file())
        outputs = (self.substage / "OUTPUTS.tsv").read_text()
        for typ in ("peaks", "peaks_consensus", "counts_peaks", "bigwig",
                    "bam_genome", "qc_multiqc"):
            self.assertIn(typ + "\tnative\t", outputs)
        self.assertIn("COMPLETE", (self.substage / "STATUS").read_text())


class RnaseqGarsWrapperTests(unittest.TestCase):
    """The rnaseq migration (decision 0029): the gars nfcore-rnaseq-wrapper and rnaseq-de
    wrappers behave on a fixture project — including the gates that motivated the migration
    (the anonymous-gene content check, the half-built-cache refusal)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-rnaseqw-"))
        cls.ws = cls.tmp / "gars"
        cls.ws.mkdir()
        for d in ("_system", "_references", "_templates"):
            shutil.copytree(str(GARS / d), str(cls.ws / d))
        (cls.ws / "projects").mkdir()
        cls.project = cls.ws / "projects" / "rna-test"
        (cls.project / "_config").mkdir(parents=True)
        (cls.project / "01_samplesheets").mkdir()
        # fixture reference + raw files
        cls.refs = cls.tmp / "refs"
        cls.refs.mkdir()
        (cls.refs / "genome.fa.gz").write_bytes(gzip.compress(b">chr1\nACGT\n"))
        (cls.refs / "genome.gtf.gz").write_bytes(gzip.compress(b"chr1\tx\tgene\n"))
        fq = cls.tmp / "reads.fastq.gz"
        write_fastq_gz(fq)
        (cls.project / "_config" / "rnaseq_bulk.yaml").write_text(
            "strandedness: auto\n"
            "reference:\n  fasta: %s\n  gtf: %s\n  derived_dir: %s\n"
            "aligner: star_salmon\n"
            "compute:\n  partition: cpu_medium\n  time: \"1:00:00\"\n  cpus: 4\n"
            "  mem: 32G\n  work_dir: /gpfs/scratch/test\n"
            "de:\n  formula: \"~ condition\"\n  contrast: \"condition,MT,WT\"\n"
            % (cls.refs / "genome.fa.gz", cls.refs / "genome.gtf.gz", cls.refs / "cache"))
        (cls.project / "_config" / "nextflow.slurm.config").write_text(
            "process { queue = 'x' }\n")
        rows = ["sample,fastq_1,fastq_2,strandedness"]
        design = ["sample_id,condition,group,replicate"]
        for i, cond in enumerate(("MT", "MT", "WT", "WT"), 1):
            rows.append("S%d,%s,%s,auto" % (i, fq, fq))
            design.append("S%d,%s,G1,%d" % (i, cond, i))
        (cls.project / "01_samplesheets" / "rnaseq_bulk_samplesheet.csv").write_text(
            "\n".join(rows) + "\n")
        (cls.project / "01_samplesheets" / "rnaseq_bulk_design.csv").write_text(
            "\n".join(design) + "\n")
        counts = ["gene_id\tgene_name\tS1\tS2\tS3\tS4"]
        for g in range(1, 6):
            counts.append("ENSG%04d\tGENE%d\t%d\t%d\t%d\t%d"
                          % (g, g, g * 2, g * 3, g * 5, g * 7))
        cls.counts_native = cls.tmp / "salmon.merged.gene_counts_length_scaled.tsv"
        cls.counts_native.write_text("\n".join(counts) + "\n")
        cls.wrap = cls.ws / "_system" / "wrappers" / "nfcore-rnaseq-wrapper" \
            / "nfcore_rnaseq_wrapper.py"
        cls.de = cls.ws / "_system" / "wrappers" / "rnaseq-de" / "rnaseq_de.py"
        cls.substage = cls.project / "02_bioinformatics" / "rnaseq_bulk" \
            / "01_nfcore-rnaseq-wrapper"
        cls.de_substage = cls.project / "02_bioinformatics" / "rnaseq_bulk" / "02_rnaseq-de"

    tearDownClass = classmethod(lambda cls: WorkspaceFixture.tearDownClass.__func__(cls))

    @needs_pipeline("rnaseq_bulk")
    def test_00_check_and_prepare(self):
        code, res, raw = run(self.wrap, ["check", "--project", "projects/rna-test"], self.ws)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(self.wrap, ["prepare", "--project", "projects/rna-test"], self.ws)
        self.assertEqual(code, 0, raw)
        # empty derived cache -> first run builds and publishes
        self.assertEqual(res["params"].get("save_reference"), "true")
        a = ((self.substage / "params.yaml").read_bytes(),
             (self.substage / "submit.sh").read_bytes())
        code, _, raw = run(self.wrap, ["prepare", "--project", "projects/rna-test"], self.ws)
        self.assertEqual(code, 0, raw)
        b = ((self.substage / "params.yaml").read_bytes(),
             (self.substage / "submit.sh").read_bytes())
        self.assertEqual(a, b, "same inputs must produce byte-identical artifacts (0011)")

    @needs_pipeline("rnaseq_bulk")
    def test_01_half_built_cache_is_refused(self):
        star = self.refs / "cache" / "index" / "star"
        star.mkdir(parents=True)
        (star / "SA").write_text("index-without-parameters-file")
        code, res, raw = run(self.wrap, ["check", "--project", "projects/rna-test"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertTrue(any("genomeParameters" in f["detail"] for f in res["failures"]))
        (star / "genomeParameters.txt").write_text("versionGenome 2.7.4a")
        (self.refs / "cache" / "index" / "salmon").mkdir()
        (self.refs / "cache" / "index" / "salmon" / "info.json").write_text("{}")
        (self.refs / "cache" / "genome.transcripts.fa").write_text(">t\nACGT\n")
        code, res, raw = run(self.wrap, ["prepare", "--project", "projects/rna-test"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("star_index", res["params"], "a complete cache is consumed, not rebuilt")
        self.assertNotIn("save_reference", res["params"])

    def test_02_collect_gates_on_content(self):
        # the complete keyed cache test_01 leaves behind -- built here too, idempotently,
        # so this test stands alone when test_01 skips off-cluster
        star = self.refs / "cache" / "index" / "star"
        star.mkdir(parents=True, exist_ok=True)
        (star / "SA").write_text("index")
        (star / "genomeParameters.txt").write_text("versionGenome 2.7.4a")
        salmon = self.refs / "cache" / "index" / "salmon"
        salmon.mkdir(exist_ok=True)
        (salmon / "info.json").write_text("{}")
        (self.refs / "cache" / "genome.transcripts.fa").write_text(">t\nACGT\n")
        adir = self.substage / "run" / "results" / "star_salmon"
        adir.mkdir(parents=True, exist_ok=True)
        (self.substage / "run" / ".gars_run_complete").write_text("now\n")
        # counts matrix missing one sample column -> caught
        (adir / "salmon.merged.gene_counts_length_scaled.tsv").write_text(
            "gene_id\tgene_name\tS1\tS2\tS3\ng1\tG1\t1\t2\t3\n")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/rna-test"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("counts_gene", [f["check"] for f in res["failures"]])
        # full tree
        (adir / "salmon.merged.gene_counts_length_scaled.tsv").write_text(
            "gene_id\tgene_name\tS1\tS2\tS3\tS4\ng1\tG1\t1\t2\t3\t4\n")
        (adir / "salmon.merged.transcript_counts.tsv").write_text("tx\n")
        (adir / "salmon.merged.gene_tpm.tsv").write_text("tpm\n")
        (adir / "S1.markdup.sorted.bam").write_text("bam")
        mq = self.substage / "run" / "results" / "multiqc" / "star_salmon"
        mq.mkdir(parents=True, exist_ok=True)
        (mq / "multiqc_report.html").write_text("<html>ok</html>")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/rna-test",
                                         "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("Model: claude-test-1", res["history_entry"])
        self.assertEqual(res["derived_cache"]["action"], "reused")
        self.assertIn("counts_gene\tnative\t",
                      (self.substage / "OUTPUTS.tsv").read_text())

    def test_03_de_check_refusals(self):
        design = self.project / "01_samplesheets" / "rnaseq_bulk_design.csv"
        # under-sampled contrast level
        bad = self.tmp / "bad_design.csv"
        bad.write_text("sample_id,condition,group,replicate\nS1,MT,G1,1\nS3,WT,G1,1\n"
                       "S4,WT,G1,2\n")
        code, res, raw = run(self.de, ["check", "--project", "projects/rna-test",
                                       "--counts", str(self.counts_native),
                                       "--design", str(bad)], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertTrue(any(f["check"] == "design" and "at least 2" in f["detail"]
                            for f in res["failures"]))
        # good design passes
        code, res, raw = run(self.de, ["check", "--project", "projects/rna-test",
                                       "--counts", str(self.counts_native),
                                       "--design", str(design)], self.ws)
        self.assertEqual(code, 0, raw)

    def test_04_de_prepare_and_collect(self):
        design = self.project / "01_samplesheets" / "rnaseq_bulk_design.csv"
        code, res, raw = run(self.de, ["prepare", "--project", "projects/rna-test",
                                       "--counts", str(self.counts_native),
                                       "--design", str(design)], self.ws)
        self.assertEqual(code, 0, raw)
        script = self.de_substage / "scripts" / "run_de.py"
        import ast as _ast
        _ast.parse(script.read_text())   # the generated analysis is valid python
        self.assertIn("condition,MT,WT", res["contrast"] + ",")
        submit = (self.de_substage / "submit.sh").read_text()
        self.assertIn("adapt_counts.py", submit)
        self.assertIn("$GARS_PY", submit)
        # absolute inputs frozen into the script (the validation-job defect)
        self.assertIn("COUNTS = '/", script.read_text())

        # collect refuses before completion
        code, res, raw = run(self.de, ["collect", "--project", "projects/rna-test"], self.ws)
        self.assertEqual(code, 2, raw)
        # fake outputs; the anonymous-gene gate first
        run_dir = self.de_substage / "run"
        (run_dir / "tables").mkdir(parents=True, exist_ok=True)
        (run_dir / "figures").mkdir(exist_ok=True)
        (self.de_substage / "adapted").mkdir(exist_ok=True)
        (run_dir / ".gars_run_complete").write_text("now\n")
        (run_dir / "tables" / "de_results.csv").write_text(
            "gene,baseMean,log2FoldChange,pvalue,padj\n,1,2,0.1,0.2\n")
        (run_dir / "tables" / "normalized_counts.csv").write_text(
            "gene,S1,S2,S3,S4\ng1,1,2,3,4\n")
        for f in ("pca.png", "volcano.png", "ma_plot.png"):
            (run_dir / "figures" / f).write_text("png")
        (run_dir / "report.md").write_text("# report\n")
        (self.de_substage / "adapted" / "counts_gene.tsv").write_text("gene\tS1\ng\t1\n")
        (self.de_substage / "adapted" / "gene_id_to_name.tsv").write_text(
            "gene_id\tgene_name\ng\tG\n")
        code, res, raw = run(self.de, ["collect", "--project", "projects/rna-test"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertTrue(any("anonymous" in f["detail"] for f in res["failures"]),
                        "an empty gene identifier must be caught (0010)")
        (run_dir / "tables" / "de_results.csv").write_text(
            "gene,baseMean,log2FoldChange,pvalue,padj\ng1,1,2,0.1,0.2\n")
        code, res, raw = run(self.de, ["collect", "--project", "projects/rna-test",
                                       "--model", "claude-test-1",
                                       "--counts-from", "01_nfcore-rnaseq-wrapper"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("Model: claude-test-1", res["history_entry"])
        self.assertIn("01_nfcore-rnaseq-wrapper", res["history_entry"])
        outputs = (self.de_substage / "OUTPUTS.tsv").read_text()
        self.assertIn("counts_gene\tadapted\t", outputs)
        self.assertIn("de_results\tnative\t", outputs)


class ChipFamilyAndMethylTests(unittest.TestCase):
    """Wrappers #3-#5 (decision 0031) and the assay-aware design table (0030): chipseq's
    antibody/control columns with derived control_replicate, cutandrun's group-shaped sheet
    with group-referent controls, methylseq's minimal chain — each through the real CLIs."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-chipfam-"))
        cls.ws = cls.tmp / "gars"
        cls.ws.mkdir()
        for d in ("_system", "_references", "_templates"):
            shutil.copytree(str(GARS / d), str(cls.ws / d))
        (cls.ws / "projects").mkdir()
        cls.refs = cls.tmp / "refs"
        (cls.refs / "derived").mkdir(parents=True)
        (cls.refs / "genome.fa.gz").write_bytes(gzip.compress(b">chr1\nACGT\n"))
        (cls.refs / "genome.gtf.gz").write_bytes(gzip.compress(b"chr1\tx\tgene\n"))
        cls.spikein = cls.tmp / "spikein.fa"
        cls.spikein.write_text(">ecoli\nACGT\n")
        cls.spikein_bt2 = cls.tmp / "spikein_bt2"
        cls.spikein_bt2.mkdir()
        (cls.spikein_bt2 / "genome.1.bt2").write_text("idx")
        reg = cls.ws / "_references" / "genomes.md"
        text = reg.read_text()
        header = text[:text.index("| GRCh38 |")]
        reg.write_text(header +
                       "| TESTG | Test species | T1 | fixture | %s | %s | %s | MT | 12345 |\n"
                       % (cls.refs / "genome.fa.gz", cls.refs / "genome.gtf.gz",
                          cls.refs / "derived"))
        cls.src = cls.tmp / "seqrun"
        cls.src.mkdir()
        for s in ("CHIP1_S1", "CHIP2_S2", "INPUT1_S3", "CNR1_S4", "CNR2_S5", "IGG1_S6",
                  "METH1_S7", "METH2_S8"):
            for r in ("R1", "R2"):
                write_fastq_gz(cls.src / ("%s_L001_%s_001.fastq.gz" % (s, r)))
        cls.reg_py = cls.ws / "_system" / "stage00_register.py"
        cls.sheet_py = cls.ws / "_system" / "stage01_samplesheet.py"
        cls.cfg_py = cls.ws / "_system" / "configure.py"

    tearDownClass = classmethod(lambda cls: WorkspaceFixture.tearDownClass.__func__(cls))

    def _mk_project(self, title, assay):
        for argv in (["create", "--title", title, "--assays", assay],
                     ["link", "--project", "projects/" + title, "--assay", assay,
                      "--source", str(self.src)],
                     ["finalize", "--project", "projects/" + title]):
            code, res, raw = run(self.reg_py, argv, self.ws)
            self.assertEqual(code, 0, raw)
        return self.ws / "projects" / title

    def _fill_design(self, project, assay, fill):
        scsv = project / "00_data" / assay / "samples.csv"
        with scsv.open() as fh:
            rows = list(csv.reader(fh))
        head = rows[0]
        kept = [rows[0]]
        for r in rows[1:]:
            d = dict(zip(head, r))
            if d["sample_id"] in fill:
                d.update(fill[d["sample_id"]])
                kept.append([d.get(c, "") for c in head])
        with scsv.open("w", newline="") as fh:
            csv.writer(fh).writerows(kept)
        return head

    # ----- chipseq ------------------------------------------------------------------------

    def test_00_chipseq_design_and_emission(self):
        project = self._mk_project("chip-test", "chipseq_bulk")
        head = (project / "00_data" / "chipseq_bulk" / "samples.csv"
                ).read_text().splitlines()[0]
        self.assertEqual(head, "sample_id,condition,group,replicate,antibody,control",
                         "stage 00 writes the assay's design columns (0030)")
        fill = {
            "CHIP1": {"condition": "KO", "group": "IP_KO", "replicate": "1",
                      "antibody": "H3K27ac", "control": "INPUT1"},
            "CHIP2": {"condition": "WT", "group": "IP_WT", "replicate": "1",
                      "antibody": "H3K27ac", "control": "NOSUCH"},
            "INPUT1": {"condition": "KO", "group": "INPUT_KO", "replicate": "1"},
        }
        self._fill_design(project, "chipseq_bulk", fill)
        code, res, raw = run(self.sheet_py, ["--project", "projects/chip-test",
                                             "--check", "--confirm-exclusions"], self.ws)
        self.assertEqual(code, 1, raw)
        checks = [f["check"] for a in res["assays"].values() for f in a.get("failures", [])]
        self.assertIn("referential_integrity", checks,
                      "a control that is not a sample_id must be caught")
        # fix the dangling control, emit, and check the derived control_replicate
        fill["CHIP2"]["control"] = "INPUT1"
        self._fill_design(project, "chipseq_bulk", fill)
        code, res, raw = run(self.sheet_py, ["--project", "projects/chip-test",
                                             "--confirm-exclusions"], self.ws)
        self.assertEqual(code, 0, raw)
        sheet = (project / "01_samplesheets" / "chipseq_bulk_samplesheet.csv"
                 ).read_text().splitlines()
        self.assertEqual(sheet[0],
                         "sample,fastq_1,fastq_2,replicate,antibody,control,control_replicate")
        by_sample = {l.split(",")[0]: l.split(",") for l in sheet[1:]}
        self.assertEqual(sorted(by_sample), ["INPUT_KO", "IP_KO", "IP_WT"],
                         "sample is the GROUP (0035)")
        self.assertEqual(by_sample["IP_KO"][5], "INPUT_KO",
                         "control is the control's GROUP, translated from the design's "
                         "sample_id pointer (0035)")
        self.assertEqual(by_sample["IP_KO"][6], "1",
                         "control_replicate is derived from the control's design row")
        self.assertEqual(by_sample["INPUT_KO"][5], "", "a control row has no control")
        # 0035's homogeneity law: an IP sharing its input's group is refused at stage 01
        fill["CHIP1"]["group"] = "INPUT_KO"
        self._fill_design(project, "chipseq_bulk", fill)
        code, res, raw = run(self.sheet_py, ["--project", "projects/chip-test",
                                             "--check", "--confirm-exclusions"], self.ws)
        self.assertEqual(code, 1, raw)
        msgs = " ".join(f["detail"] for a in res["assays"].values()
                        for f in a.get("failures", []))
        self.assertIn("antibody", msgs)
        fill["CHIP1"]["group"] = "IP_KO"
        self._fill_design(project, "chipseq_bulk", fill)
        code, _, raw = run(self.sheet_py, ["--project", "projects/chip-test",
                                           "--confirm-exclusions", "--force"], self.ws)
        self.assertEqual(code, 0, raw)

    @needs_pipeline("chipseq_bulk")
    def test_01_chipseq_wrapper(self):
        wrap = self.ws / "_system" / "wrappers" / "nfcore-chipseq-wrapper" \
            / "nfcore_chipseq_wrapper.py"
        code, res, raw = run(self.cfg_py, ["apply", "--project", "projects/chip-test",
                                           "--assay", "chipseq_bulk", "--genome", "01",
                                           "--peaks-type", "narrow"], self.ws)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(wrap, ["check", "--project", "projects/chip-test"], self.ws)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(wrap, ["prepare", "--project", "projects/chip-test"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(res["params"]["macs_gsize"], "12345")
        substage = self.ws / "projects" / "chip-test" / "02_bioinformatics" / "chipseq_bulk" \
            / "01_nfcore-chipseq-wrapper"
        ml = substage / "run" / "results" / "bwa" / "merged_library"
        ab = ml / "macs3" / "narrow_peak" / "consensus" / "H3K27ac"
        ab.mkdir(parents=True)
        (ml / "macs3" / "narrow_peak" / "IP_KO_REP1_peaks.narrowPeak").write_text("chr1\t1\t2\n")
        (ab / "H3K27ac.consensus_peaks.bed").write_text("chr1\t1\t2\tp1\n")
        (ab / "H3K27ac.consensus_peaks.featureCounts.txt").write_text(
            "# fc\nGeneid\tChr\tStart\tEnd\tStrand\tLength\tIP_KO_REP1.bam\tIP_WT_REP1.bam\tINPUT_KO_REP1.bam\np1\tchr1\t1\t2\t+\t2\t1\t1\t1\n")
        (ml / "bigwig").mkdir()
        (ml / "bigwig" / "IP_KO_REP1.bigWig").write_text("bw")
        (ml / "IP_KO_REP1.mLb.clN.sorted.bam").write_text("bam")
        mq = substage / "run" / "results" / "multiqc" / "narrow_peak"
        mq.mkdir(parents=True)
        (mq / "multiqc_report.html").write_text("<html>ok</html>")
        (substage / "run" / ".gars_run_complete").write_text("now\n")
        code, res, raw = run(wrap, ["collect", "--project", "projects/chip-test",
                                    "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("IPs: 2", res["history_entry"])
        self.assertIn("peaks_consensus\tnative\t",
                      (substage / "OUTPUTS.tsv").read_text())

    # ----- cutandrun ----------------------------------------------------------------------

    @needs_pipeline("cutandrun")
    def test_02_cutandrun_chain(self):
        project = self._mk_project("cnr-test", "cutandrun")
        head = (project / "00_data" / "cutandrun" / "samples.csv").read_text().splitlines()[0]
        self.assertEqual(head, "sample_id,condition,group,replicate,control")
        fill = {
            "CNR1": {"condition": "KO", "group": "h3k4me3", "replicate": "1",
                     "control": "igg"},
            "CNR2": {"condition": "KO", "group": "h3k4me3", "replicate": "2",
                     "control": "igg"},
            "IGG1": {"condition": "KO", "group": "igg", "replicate": "1"},
        }
        self._fill_design(project, "cutandrun", fill)
        code, res, raw = run(self.sheet_py, ["--project", "projects/cnr-test",
                                             "--confirm-exclusions"], self.ws)
        self.assertEqual(code, 0, raw)
        sheet = (project / "01_samplesheets" / "cutandrun_samplesheet.csv"
                 ).read_text().splitlines()
        self.assertEqual(sheet[0], "group,replicate,fastq_1,fastq_2,control",
                         "the cutandrun sheet is group-shaped")
        code, res, raw = run(self.cfg_py, ["apply", "--project", "projects/cnr-test",
                                           "--assay", "cutandrun", "--genome", "01"], self.ws)
        self.assertEqual(code, 0, raw)
        cfg = (project / "_config" / "cutandrun.yaml").read_text()
        self.assertIn("mito_name: MT", cfg)
        wrap = self.ws / "_system" / "wrappers" / "nfcore-cutandrun-wrapper" \
            / "nfcore_cutandrun_wrapper.py"
        # fixture spike-in path
        cfgp = project / "_config" / "cutandrun.yaml"
        cfgp.write_text(cfgp.read_text().replace(
            "/gpfs/data/sequence/references/iGenomes/Escherichia_coli_K_12_MG1655/NCBI/2001-10-15/Sequence/WholeGenomeFasta/genome.fa",
            str(self.spikein)))
        self.assertIn("gene_heatmaps", cfgp.read_text(),
                      "the seeded config carries the 0038 qc surface")
        # 0036 red case first: an index dir without genome.1.bt2 is refused BY NAME --
        # asserted on the failure list, not the exit code, so it holds off-cluster too
        code, res, raw = run(wrap, ["check", "--project", "projects/cnr-test"], self.ws)
        self.assertIn("spikein_bowtie2", [f["check"] for f in res.get("failures", [])], raw)
        cfgp.write_text(cfgp.read_text().replace(
            "/gpfs/data/sequence/references/iGenomes/Escherichia_coli_K_12_MG1655/NCBI/2001-10-15/Sequence/Bowtie2Index",
            str(self.spikein_bt2)))
        code, res, raw = run(wrap, ["check", "--project", "projects/cnr-test"], self.ws)
        self.assertNotIn("spikein_bowtie2", [f["check"] for f in (res or {}).get("failures", [])],
                         raw)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(wrap, ["prepare", "--project", "projects/cnr-test"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(res["params"]["peakcaller"], "seacr")
        self.assertEqual(res["params"]["spikein_bowtie2"], str(self.spikein_bt2))
        substage = project / "02_bioinformatics" / "cutandrun" / "01_nfcore-cutandrun-wrapper"
        r = substage / "run" / "results"
        (r / "02_alignment" / "bowtie2" / "target" / "markdup").mkdir(parents=True)
        (r / "02_alignment" / "bowtie2" / "target" / "markdup" / "CNR1.bam").write_text("b")
        (r / "03_peak_calling" / "03_bed_to_bigwig").mkdir(parents=True)
        (r / "03_peak_calling" / "03_bed_to_bigwig" / "h3k4me3_R1.bigWig").write_text("bw")
        (r / "03_peak_calling" / "04_called_peaks").mkdir()
        (r / "03_peak_calling" / "04_called_peaks" / "h3k4me3_R1.seacr.peaks.stringent.bed"
         ).write_text("chr1\t1\t2\n")
        (r / "03_peak_calling" / "05_consensus_peaks").mkdir()
        (r / "03_peak_calling" / "05_consensus_peaks" / "h3k4me3.consensus.peaks.bed"
         ).write_text("chr1\t1\t2\n")
        (r / "04_reporting" / "multiqc").mkdir(parents=True)
        (r / "04_reporting" / "multiqc" / "multiqc_report.html").write_text("<html>ok</html>")
        (substage / "run" / ".gars_run_complete").write_text("now\n")
        code, res, raw = run(wrap, ["collect", "--project", "projects/cnr-test",
                                    "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("targets: 1", res["history_entry"])

    # ----- methylseq ----------------------------------------------------------------------

    @needs_pipeline("methylseq")
    def test_03_methylseq_chain(self):
        project = self._mk_project("meth-test", "methylseq")
        fill = {"METH1": {"condition": "A", "group": "G1", "replicate": "1"},
                "METH2": {"condition": "B", "group": "G1", "replicate": "1"}}
        self._fill_design(project, "methylseq", fill)
        code, res, raw = run(self.sheet_py, ["--project", "projects/meth-test",
                                             "--confirm-exclusions"], self.ws)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(self.cfg_py, ["apply", "--project", "projects/meth-test",
                                           "--assay", "methylseq", "--genome", "01"], self.ws)
        self.assertEqual(code, 0, raw)
        wrap = self.ws / "_system" / "wrappers" / "nfcore-methylseq-wrapper" \
            / "nfcore_methylseq_wrapper.py"
        code, res, raw = run(wrap, ["check", "--project", "projects/meth-test"], self.ws)
        self.assertEqual(code, 0, raw)
        code, res, raw = run(wrap, ["prepare", "--project", "projects/meth-test"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertNotIn("gtf", res["params"], "bisulfite alignment uses no annotation")
        substage = project / "02_bioinformatics" / "methylseq" / "01_nfcore-methylseq-wrapper"
        b = substage / "run" / "results" / "bismark"
        (b / "methylation_coverage").mkdir(parents=True)
        # one sample missing -> content gate catches it
        (b / "methylation_coverage" / "METH1.bismark.cov.gz").write_text("cov")
        (b / "methylation_calls").mkdir()
        (b / "methylation_calls" / "CpG_context_METH1.txt.gz").write_text("c")
        (b / "bedGraph").mkdir()
        (b / "bedGraph" / "METH1.bedGraph.gz").write_text("bg")
        mq = substage / "run" / "results" / "multiqc"
        mq.mkdir(parents=True)
        (mq / "multiqc_report.html").write_text("<html>ok</html>")
        (substage / "run" / ".gars_run_complete").write_text("now\n")
        code, res, raw = run(wrap, ["collect", "--project", "projects/meth-test"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("methylation_coverage", [f["check"] for f in res["failures"]])
        (b / "methylation_coverage" / "METH2.bismark.cov.gz").write_text("cov")
        code, res, raw = run(wrap, ["collect", "--project", "projects/meth-test",
                                    "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("methylation_coverage\tnative\t",
                      (substage / "OUTPUTS.tsv").read_text())


class ProjectStateTests(unittest.TestCase):
    """The catch-up render (decision 0033): derived from the filesystem, writes nothing,
    and says the things a returning session needs -- unmade decisions, STATUS, artifacts,
    history. Own throwaway workspace so it proves the render against a real stage-00 chain."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-test-state-"))
        cls.ws = cls.tmp / "gars"
        cls.ws.mkdir()
        for d in ("_system", "_references", "_templates"):
            shutil.copytree(str(GARS / d), str(cls.ws / d))
        (cls.ws / "projects").mkdir()
        cls.src = cls.tmp / "seqrun"
        cls.src.mkdir()
        for s in ("A1_S1", "A2_S2"):
            for r in ("R1", "R2"):
                write_fastq_gz(cls.src / ("%s_L001_%s_001.fastq.gz" % (s, r)))
        reg = cls.ws / "_system" / "stage00_register.py"
        for args in (["create", "--title", "state-test", "--assays", "rnaseq_bulk"],
                     ["link", "--project", "projects/state-test", "--assay", "rnaseq_bulk",
                      "--source", str(cls.src)],
                     ["finalize", "--project", "projects/state-test"]):
            code, _, raw = run(reg, args, cls.ws)
            assert code == 0, raw
        cls.state = cls.ws / "_system" / "project_state.py"
        cls.project = cls.ws / "projects" / "state-test"

    @classmethod
    def tearDownClass(cls):
        for root, dirs, files in os.walk(str(cls.tmp)):
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
                except OSError:
                    pass
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def _tree_snapshot(self):
        snap = {}
        for root, dirs, files in os.walk(str(self.ws)):
            for f in files:
                fp = os.path.join(root, f)
                st = os.stat(fp)
                snap[fp] = (st.st_size, st.st_mtime_ns)
        return snap

    def test_00_render_names_the_unmade_decisions(self):
        code, _, raw = run(self.state, [], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("state-test", raw)
        self.assertIn("config decisions still unmade:", raw)
        self.assertIn("formula", raw)             # the seeded <REQUIRED> keys surface by name
        self.assertIn("fasta", raw)               # (bare keys -- configure.py's own idiom)
        self.assertIn("stage 02: not started", raw)
        self.assertIn("### history", raw)          # stage 00 already appended entries

    def test_01_status_is_the_only_authority_and_artifacts_render(self):
        sub = self.project / "02_bioinformatics" / "rnaseq_bulk" / "01_nfcore-rnaseq-wrapper"
        sub.mkdir(parents=True)
        (sub / "STATUS").write_text("COMPLETE 2026-08-27T00:00:00Z\n")
        (sub / "OUTPUTS.tsv").write_text(
            "type\trole\tpath\ncounts_gene\tnative\trun/results/x.tsv\n")
        code, _, raw = run(self.state, [], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("01_nfcore-rnaseq-wrapper: COMPLETE", raw)
        self.assertIn("artifacts: counts_gene", raw)

    def test_02_render_writes_nothing_and_is_deterministic(self):
        before = self._tree_snapshot()
        code1, _, raw1 = run(self.state, [], self.ws)
        code2, _, raw2 = run(self.state, [], self.ws)
        after = self._tree_snapshot()
        self.assertEqual(code1, 0)
        self.assertEqual(raw1, raw2)               # byte-identical across runs
        self.assertEqual(before, after)            # a render, not a record

    def test_03_single_project_flag(self):
        code, _, raw = run(self.state, ["--project", "projects/state-test"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("state-test", raw)
        code, _, _ = run(self.state, ["--project", "projects/nope"], self.ws)
        self.assertEqual(code, 2)


class SubmitShPairingTests(unittest.TestCase):
    """Decision 0034: legacy-era pipelines get NXF_SYNTAX_PARSER=v1 in their generated
    submit.sh; rnaseq (strict-clean, validated) stays byte-identical without it. Unit-level
    against write_submit_sh directly, so it runs where no pinned checkout exists."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(GARS / "_system"))
        import wrapperlib  # noqa: F401
        cls.wl = wrapperlib
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-test-pairing-"))
        cls.cfg = {"compute.partition": "cpu_medium", "compute.time": "1:00:00",
                   "compute.cpus": "4", "compute.mem": "8G"}

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(GARS / "_system"))
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def _submit_for(self, assay):
        sub = self.tmp / assay
        sub.mkdir(exist_ok=True)
        self.wl.write_submit_sh(sub, self.tmp, self.cfg, "proj", assay, "echo body")
        return (sub / "submit.sh").read_text()

    def test_00_legacy_assays_export_v1(self):
        for assay in ("atacseq_bulk", "chipseq_bulk", "cutandrun", "methylseq"):
            script = self._submit_for(assay)
            self.assertIn("export NXF_SYNTAX_PARSER=v1", script, assay)
            self.assertIn("Decision 0034", script, assay)

    def test_01_rnaseq_stays_strict(self):
        script = self._submit_for("rnaseq_bulk")
        self.assertNotIn("NXF_SYNTAX_PARSER", script)

    def test_02_guard_survives_injection(self):
        script = self._submit_for("atacseq_bulk")
        self.assertIn(".gars_run_complete", script)     # requeue guard intact
        self.assertIn("RESUME=", script)                # resume branch intact
        self.assertIn('source "$WS/_system/gars-env.sh"', script)


class ModulePatchStateTests(unittest.TestCase):
    """Decision 0037: a pin may carry one recorded patch, and CONTENT is the authority --
    the detector reads the module file, so a regressed checkout (re-clone) is caught again."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(GARS / "_system"))
        import wrapperlib
        cls.wl = wrapperlib
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-test-patchstate-"))
        cls.rel = "modules/local/for_patch/trimgalore/main.nf"
        (cls.tmp / "modules/local/for_patch/trimgalore").mkdir(parents=True)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(GARS / "_system"))
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def _state(self, content):
        (self.tmp / self.rel).write_text(content)
        return self.wl.module_patch_state(self.tmp, self.rel,
                                          "optional true", "optional: true")

    def test_states(self):
        self.assertEqual(self._state("emit: html optional true\n"), "legacy")
        self.assertEqual(self._state("emit: html, optional: true\n"), "patched")
        self.assertEqual(self._state("no options here\n"), "absent")
        (self.tmp / self.rel).unlink()
        self.assertEqual(self.wl.module_patch_state(self.tmp, self.rel,
                                                    "optional true", "optional: true"),
                         "absent")

    def test_patch_file_ships_and_matches_the_detector(self):
        patch = GARS / "_references" / "patches" / "cutandrun-3.2.2-trimgalore-dsl.patch"
        text = patch.read_text()
        self.assertIn("-    tuple val(meta), path(\"*.html\"), emit: html optional true", text)
        self.assertIn("+    tuple val(meta), path(\"*.html\"), emit: html, optional: true", text)
        self.assertIn("git apply", text)


class CheckRunDirRefreshTests(unittest.TestCase):
    """Decision 0038: --resume-refresh opens the populated-run gate ONLY for a terminally
    FAILED run with Nextflow state in place -- a params-change-then-resume, never a bypass."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(GARS / "_system"))
        import wrapperlib
        cls.wl = wrapperlib
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-test-refresh-"))

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(GARS / "_system"))
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def _substage(self, name, status=None, nextflow=False, populated=True):
        sub = self.tmp / name
        (sub / "run").mkdir(parents=True)
        if populated:
            (sub / "run" / "boot.log").write_text("log")
        if nextflow:
            (sub / "run" / ".nextflow").mkdir()
        if status:
            (sub / "STATUS").write_text(status)
        return sub

    def _fails(self, sub, refresh):
        fails = []
        self.wl.check_run_dir(sub, fails, resume_refresh=refresh)
        return [f["check"] for f in fails]

    def test_gate(self):
        ok = self._substage("ok", status="FAILED 2026-08-28 oom", nextflow=True)
        self.assertEqual(self._fails(ok, True), [], "FAILED + .nextflow -> refresh allowed")
        self.assertEqual(self._fails(ok, False), ["output_dir"],
                         "without the flag the gate still refuses")
        no_state = self._substage("nostate", status="FAILED 2026-08-28 oom", nextflow=False)
        self.assertEqual(self._fails(no_state, True), ["output_dir"],
                         "no Nextflow state -> nothing to resume -> refused")
        running = self._substage("running", status="SUBMITTED 123", nextflow=True)
        self.assertEqual(self._fails(running, True), ["output_dir"],
                         "not terminally FAILED -> refused")

    def test_hint_names_the_road(self):
        sub = self._substage("hint", status="FAILED x", nextflow=True)
        fails = []
        self.wl.check_run_dir(sub, fails, resume_refresh=False)
        self.assertIn("--resume-refresh", fails[0]["detail"])


class GuardHookTests(unittest.TestCase):
    """The mechanical scope boundaries (decision 0022). Every deny is an action no contract
    instructs; every allow is a step some contract does instruct."""

    HOOK = GARS / "_system" / "guard_hook.py"

    def call(self, tool, tool_input):
        payload = json.dumps({"tool_name": tool, "tool_input": tool_input,
                              "cwd": str(GARS)})
        code, _, raw = run([sys.executable, str(self.HOOK)], [], GARS,
                           env_extra={"CLAUDE_PROJECT_DIR": str(GARS)},
                           stdin_data=payload)
        return code, raw

    def assertDenied(self, tool, tool_input):
        code, raw = self.call(tool, tool_input)
        self.assertEqual(code, 2, "expected deny: %r %r\n%s" % (tool, tool_input, raw))
        self.assertIn("Blocked", raw)

    def assertAllowed(self, tool, tool_input):
        code, raw = self.call(tool, tool_input)
        self.assertEqual(code, 0, "expected allow: %r %r\n%s" % (tool, tool_input, raw))

    def test_denies(self):
        self.assertDenied("Edit", {"file_path": "00_initialize_project/CONTEXT.md"})
        self.assertDenied("Write", {"file_path": "_system/stage00_register.py"})
        self.assertDenied("Edit", {"file_path": "_references/genomes.md"})
        self.assertDenied("Write", {"file_path": ".claude/settings.json"})
        self.assertDenied("Edit", {"file_path": "CLAUDE.md"})
        self.assertDenied("Write", {"file_path": "projects/p/00_data/rnaseq_bulk/files.csv"})
        self.assertDenied("Edit", {"file_path": "projects/p/01_samplesheets/x_samplesheet.csv"})
        self.assertDenied("Write", {"file_path": "projects/_index.md"})
        self.assertDenied("Bash", {"command": "pip install pandas"})
        self.assertDenied("Bash", {"command": "conda install -y numpy"})
        self.assertDenied("Bash", {"command": "chmod +w projects/p/00_data/a/files.csv"})
        self.assertDenied("Bash", {"command": "rm projects/p/00_data/a/files.csv"})
        self.assertDenied("Bash", {"command": "echo x > _system/new.py"})
        self.assertDenied("Bash", {"command": "sed -i s/a/b/ _references/genomes.md"})
        self.assertDenied("Bash", {"command": "cp hack.py _system/hack.py"})

    def test_allows(self):
        self.assertAllowed("Edit", {"file_path": "projects/p/00_data/rnaseq_bulk/samples.csv"})
        self.assertAllowed("Write", {"file_path": "projects/p/_config/rnaseq_bulk.yaml"})
        self.assertAllowed("Write",
                           {"file_path": "projects/p/02_bioinformatics/a/01_x/OUTPUTS.tsv"})
        self.assertAllowed("Write", {"file_path": "projects/p/HISTORY.md"})
        self.assertAllowed("Bash", {"command": "python3 _system/stage00_register.py assays"})
        self.assertAllowed("Bash",
                           {"command": "python3 _system/stage01_samplesheet.py "
                                       "--project projects/p --check > /tmp/res.json"})
        self.assertAllowed("Bash", {"command": "cat _references/genomes.md"})
        self.assertAllowed("Bash", {"command": "bash _system/build_projects_index.sh"})
        self.assertAllowed("Bash", {"command": "sbatch projects/p/02_bioinformatics/a/01_x/submit.sh"})
        self.assertAllowed("Read", {"file_path": "_references/genomes.md"})


class ContractLintTests(unittest.TestCase):
    """The static half of the compliance story: structure and vocabulary cannot drift."""

    def test_check_contracts_passes(self):
        code, _, raw = run([sys.executable, str(REPO / "tests" / "check_contracts.py")],
                           [], REPO)
        self.assertEqual(code, 0, raw)


class SkillAuthoringTests(unittest.TestCase):
    """create-bioinformatics-skill: the method is only real if it describes the wrappers we
    already trust, and only useful if breaking a rule actually goes red."""

    TOOL = GARS / "_system" / "authoring" / "create_bioinformatics_skill.py"
    WRAPPERS = GARS / "_system" / "wrappers"

    SPEC = {
        "assay_id": "demo_assay",
        "assay_label": "Demo assay",
        "wrapper_name": "demo-wrapper",
        "substage": "01_demo-wrapper",
        "pipeline": "nf-core/demo",
        "pipeline_version": "1.0.0",
        "samplesheet_header": ["sample", "fastq_1", "fastq_2"],
        "required_config_keys": ["reference.fasta", "compute.partition", "compute.work_dir"],
        "artifacts": [
            {"type": "counts_gene", "path": "run/results/counts.tsv", "content_gate": True},
            {"type": "qc_multiqc", "path": "run/results/multiqc/multiqc_report.html"},
        ],
    }

    def _conform(self, target):
        return run(self.TOOL, ["conform", str(target)], REPO)

    def test_00_every_existing_wrapper_conforms(self):
        """The standard is derived from these six. A rule that fails one is a wrong rule."""
        code, payload, raw = self._conform(self.WRAPPERS)
        self.assertEqual(code, 0, raw)
        self.assertTrue(payload["ok"], payload.get("failures"))
        self.assertGreaterEqual(payload["checked"], 6, raw)

    def test_01_conform_catches_each_violation(self):
        """Mutation coverage: every rule must go red when deliberately broken.

        Without this the linter could pass everything and prove nothing. One rule originally
        tested a substring and a rename slipped past it -- hence the --model case here."""
        src_dir = self.WRAPPERS / "nfcore-atacseq-wrapper"
        module_name = "nfcore_atacseq_wrapper.py"
        mutations = [
            ("derived_pin", lambda s: re.sub(r"^PIPELINE_VERSION = .*",
                                             'PIPELINE_VERSION = "2.1.2"', s, flags=re.M)),
            ("wrapperlib", lambda s: s.replace("import wrapperlib as wl", "import json as wl")),
            ("registry", lambda s: s.replace("OUTPUTS.tsv", "OUTPUTSX.tsv")),
            ("provenance", lambda s: s.replace('"--model"', '"--modelx"')),
            ("verbs", lambda s: s.replace("def cmd_collect", "def cmd_collectx")),
            ("atomic_writes", lambda s: s.replace("atomic_open", "plain_open")),
            ("stdlib_only", lambda s: s.replace("import argparse",
                                                "import argparse\nimport pandas")),
            ("identity", lambda s: re.sub(r"^ASSAY = .*", "X = 1", s, flags=re.M)),
            ("py36", lambda s: s.replace('"no such project: %s" % project',
                                         'f"no such project"')),
        ]
        for check, mutate in mutations:
            tmp = Path(tempfile.mkdtemp())
            try:
                dest = tmp / src_dir.name
                shutil.copytree(str(src_dir), str(dest))
                target = dest / module_name
                target.write_text(mutate(target.read_text(encoding="utf-8")), encoding="utf-8")
                code, payload, raw = self._conform(dest)
                self.assertEqual(code, 1, "%s: linter stayed green\n%s" % (check, raw))
                caught = set(f["check"] for f in payload["failures"])
                self.assertIn(check, caught,
                              "%s: expected that check to fire, got %s" % (check, sorted(caught)))
            finally:
                shutil.rmtree(str(tmp), ignore_errors=True)

    def test_02_two_modules_and_missing_skill_md_are_caught(self):
        src_dir = self.WRAPPERS / "nfcore-atacseq-wrapper"
        tmp = Path(tempfile.mkdtemp())
        try:
            dest = tmp / src_dir.name
            shutil.copytree(str(src_dir), str(dest))
            (dest / "second_module.py").write_text("x = 1\n", encoding="utf-8")
            _, payload, raw = self._conform(dest)
            self.assertIn("one_module", set(f["check"] for f in payload["failures"]), raw)

            (dest / "second_module.py").unlink()
            (dest / "SKILL.md").unlink()
            _, payload, raw = self._conform(dest)
            self.assertIn("skill_md", set(f["check"] for f in payload["failures"]), raw)
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)

    def test_03_scaffold_output_conforms_and_compiles(self):
        """The round trip: what the method generates must satisfy the method."""
        tmp = Path(tempfile.mkdtemp())
        try:
            spec = tmp / "spec.json"
            spec.write_text(json.dumps(self.SPEC), encoding="utf-8")
            out = tmp / "wrappers"
            code, payload, raw = run(self.TOOL,
                                     ["scaffold", "--spec", str(spec), "--out", str(out)], REPO)
            self.assertEqual(code, 0, raw)
            self.assertTrue(payload["ok"], raw)
            self.assertIn("workspace.PIPELINES", payload["registry_rows"])

            generated = out / "demo-wrapper" / "demo_wrapper.py"
            self.assertTrue(generated.is_file(), raw)
            compile(generated.read_text(encoding="utf-8"), str(generated), "exec")

            code, payload, raw = self._conform(out / "demo-wrapper")
            self.assertEqual(code, 0, raw)
            self.assertTrue(payload["ok"], payload.get("failures"))
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)

    def test_04_scaffold_refuses_to_overwrite(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            spec = tmp / "spec.json"
            spec.write_text(json.dumps(self.SPEC), encoding="utf-8")
            out = tmp / "wrappers"
            run(self.TOOL, ["scaffold", "--spec", str(spec), "--out", str(out)], REPO)
            code, payload, raw = run(self.TOOL,
                                     ["scaffold", "--spec", str(spec), "--out", str(out)], REPO)
            self.assertEqual(code, 2, raw)
            self.assertIn("refusing to overwrite", payload["error"])
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)

    def test_05_spec_without_a_content_gate_is_refused(self):
        """P2 enforced at spec time: an existence-only gate is how a silent defect ships."""
        tmp = Path(tempfile.mkdtemp())
        try:
            spec_data = json.loads(json.dumps(self.SPEC))
            for art in spec_data["artifacts"]:
                art.pop("content_gate", None)
            spec = tmp / "spec.json"
            spec.write_text(json.dumps(spec_data), encoding="utf-8")
            code, payload, raw = run(self.TOOL, ["scaffold", "--spec", str(spec),
                                                 "--out", str(tmp / "w")], REPO)
            self.assertEqual(code, 1, raw)
            self.assertIn("content_gate",
                          " ".join(f["detail"] for f in payload["failures"]))
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)


class ScrnaseqWrapperTests(unittest.TestCase):
    """Wrapper #6 (decision 0039): the single-cell chain, and the two facts that memory would
    have got wrong -- `sample` is the sample id here, and an unsupported protocol must be
    refused rather than passed to the aligner verbatim."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-scrna-"))
        cls.ws = cls.tmp / "gars"
        cls.ws.mkdir()
        for d in ("_system", "_references", "_templates"):
            shutil.copytree(str(GARS / d), str(cls.ws / d))
        (cls.ws / "projects").mkdir()
        cls.refs = cls.tmp / "refs"
        (cls.refs / "derived").mkdir(parents=True)
        (cls.refs / "genome.fa.gz").write_bytes(gzip.compress(b">chr1\nACGT\n"))
        (cls.refs / "genome.gtf.gz").write_bytes(gzip.compress(b"chr1\tx\tgene\n"))
        reg = cls.ws / "_references" / "genomes.md"
        text = reg.read_text()
        header = text[:text.index("| GRCh38 |")]
        reg.write_text(header +
                       "| TESTG | Test species | T1 | fixture | %s | %s | %s | MT | 12345 |\n"
                       % (cls.refs / "genome.fa.gz", cls.refs / "genome.gtf.gz",
                          cls.refs / "derived"))
        cls.src = cls.tmp / "seqrun"
        cls.src.mkdir()
        for s in ("SC1_S1", "SC2_S2"):
            for r in ("R1", "R2"):
                write_fastq_gz(cls.src / ("%s_L001_%s_001.fastq.gz" % (s, r)))
        cls.reg_py = cls.ws / "_system" / "stage00_register.py"
        cls.sheet_py = cls.ws / "_system" / "stage01_samplesheet.py"
        cls.cfg_py = cls.ws / "_system" / "configure.py"
        cls.wrap = (cls.ws / "_system" / "wrappers" / "nfcore-scrnaseq-wrapper"
                    / "nfcore_scrnaseq_wrapper.py")

    tearDownClass = classmethod(lambda cls: WorkspaceFixture.tearDownClass.__func__(cls))

    def _project(self, title):
        for argv in (["create", "--title", title, "--assays", "scrnaseq"],
                     ["link", "--project", "projects/" + title, "--assay", "scrnaseq",
                      "--source", str(self.src)],
                     ["finalize", "--project", "projects/" + title]):
            code, res, raw = run(self.reg_py, argv, self.ws)
            self.assertEqual(code, 0, raw)
        project = self.ws / "projects" / title
        scsv = project / "00_data" / "scrnaseq" / "samples.csv"
        with scsv.open() as fh:
            rows = list(csv.reader(fh))
        head = rows[0]
        out = [head]
        fill = {"SC1": {"condition": "A", "group": "G1", "replicate": "1"},
                "SC2": {"condition": "B", "group": "G2", "replicate": "1"}}
        for r in rows[1:]:
            d = dict(zip(head, r))
            if d["sample_id"] in fill:
                d.update(fill[d["sample_id"]])
                out.append([d.get(c, "") for c in head])
        with scsv.open("w", newline="") as fh:
            csv.writer(fh).writerows(out)
        code, res, raw = run(self.sheet_py, ["--project", "projects/" + title,
                                             "--confirm-exclusions"], self.ws)
        self.assertEqual(code, 0, raw)
        return project

    def test_00_samplesheet_sample_column_is_the_sample_id(self):
        """The opposite of the ATAC/ChIP sheets (0035). Getting this backwards would merge
        replicates into one barcode space, silently."""
        project = self._project("sc-ids")
        sheet = (project / "01_samplesheets" / "scrnaseq_samplesheet.csv"
                 ).read_text().splitlines()
        self.assertEqual(sheet[0], "sample,fastq_1,fastq_2")
        ids = [l.split(",")[0] for l in sheet[1:] if l.strip()]
        self.assertEqual(sorted(ids), ["SC1", "SC2"],
                         "each sample is its own row; no grouping")

    def test_01_protocol_menu_filters_by_aligner(self):
        code, res, raw = run(self.cfg_py, ["protocols", "--aligner", "simpleaf"], self.ws)
        self.assertEqual(code, 0, raw)
        values = [e["value"] for e in res["protocols"]]
        self.assertIn("10XV3", values)
        self.assertNotIn("smartseq", values,
                         "simpleaf does not support smartseq (assets/protocols.json)")
        code, res, raw = run(self.cfg_py, ["protocols", "--aligner", "star"], self.ws)
        self.assertIn("smartseq", [e["value"] for e in res["protocols"]])
        self.assertNotIn("auto", [e["value"] for e in res["protocols"]],
                         "auto is cellranger-only and must never be offered")

    def test_02_apply_refuses_an_incompatible_pair(self):
        project = self._project("sc-badpair")
        code, res, raw = run(self.cfg_py,
                             ["apply", "--project", "projects/sc-badpair",
                              "--assay", "scrnaseq", "--genome", "01",
                              "--protocol", "smartseq", "--aligner", "simpleaf"], self.ws)
        # configure.py is a menu helper and carries its own narrower code set --
        # EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 3, with no EXIT_FAILURE. A refusal here
        # is 1, not the wrappers' 2.
        self.assertEqual(code, 1, raw)
        self.assertIn("not supported by aligner", res["error"])
        self.assertIn("<REQUIRED",
                      (project / "_config" / "scrnaseq.yaml").read_text(),
                      "a refused apply writes nothing")

    def test_03_check_refuses_an_unsupported_protocol(self):
        """The wrapper's own gate, independent of the menu: the pipeline would pass an
        unrecognised protocol to the aligner verbatim and produce a wrong matrix."""
        project = self._project("sc-badproto")
        code, res, raw = run(self.cfg_py,
                             ["apply", "--project", "projects/sc-badproto",
                              "--assay", "scrnaseq", "--genome", "01",
                              "--protocol", "10XV3", "--aligner", "simpleaf"], self.ws)
        self.assertEqual(code, 0, raw)
        cfg = project / "_config" / "scrnaseq.yaml"
        cfg.write_text(cfg.read_text().replace("protocol: 10XV3", "protocol: auto"))
        code, res, raw = run(self.wrap, ["check", "--project", "projects/sc-badproto"],
                             self.ws)
        self.assertEqual(code, 1, raw)
        details = " ".join(f["detail"] for f in res["failures"])
        if "no pinned checkout" in details:
            self.skipTest("environment: no pinned scrnaseq checkout; protocol matrix "
                          "is read from it")
        self.assertIn("auto", details)
        self.assertIn("verbatim", details,
                      "the refusal must say WHY a wrong protocol is dangerous")

    def test_04_lanes_repeat_a_sample_id_but_a_repeated_fastq_does_not(self):
        """A multi-lane sample legitimately repeats its id -- files.csv is keyed
        (sample_id, lane) and nf-core concatenates by meta.id. An earlier version of this
        check refused duplicate ids outright, which would have rejected every multi-lane 10x
        run; nf-core's own test samplesheet has Sample_Y on two lanes. What is really wrong
        is the same FASTQ twice, which double-counts reads into the same barcodes."""
        project = self._project("sc-lanes")
        sheet = project / "01_samplesheets" / "scrnaseq_samplesheet.csv"
        lines = sheet.read_text().splitlines()
        first = lines[1].split(",")

        # same sample id, DIFFERENT read files == a second lane. Must be accepted.
        lane2 = [first[0], first[1].replace("_L001_", "_L002_"),
                 first[2].replace("_L001_", "_L002_")]
        for src, dst in ((first[1], lane2[1]), (first[2], lane2[2])):
            shutil.copyfile(str(project / src) if not os.path.isabs(src) else src,
                            str(project / dst) if not os.path.isabs(dst) else dst)
        sheet.write_text("\n".join(lines + [",".join(lane2)]) + "\n")
        code, res, raw = run(self.wrap, ["check", "--project", "projects/sc-lanes"], self.ws)
        sheet_fails = [f for f in (res.get("failures") or [])
                       if f["check"] == "samplesheet"]
        self.assertEqual(sheet_fails, [], "a second lane must not be refused: %s" % raw)

        # the SAME fastq pair twice == double counting. Must be refused.
        sheet.write_text("\n".join(lines + [lines[1]]) + "\n")
        code, res, raw = run(self.wrap, ["check", "--project", "projects/sc-lanes"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("samplesheet", [f["check"] for f in res["failures"]])
        self.assertIn("listed twice", " ".join(f["detail"] for f in res["failures"]))

    def test_05_collect_gates_on_every_sample(self):
        """The content gate: a sample lost to a failed process must not vanish into a
        combined matrix built from fewer samples (decision 0010)."""
        project = self._project("sc-collect")
        code, res, raw = run(self.cfg_py,
                             ["apply", "--project", "projects/sc-collect",
                              "--assay", "scrnaseq", "--genome", "01",
                              "--protocol", "10XV3", "--aligner", "simpleaf"], self.ws)
        self.assertEqual(code, 0, raw)
        substage = (project / "02_bioinformatics" / "scrnaseq"
                    / "01_nfcore-scrnaseq-wrapper")
        mtx = substage / "run" / "results" / "simpleaf" / "mtx_conversions"
        (mtx / "SC1").mkdir(parents=True)
        (mtx / "SC1" / "SC1_filtered_matrix.h5ad").write_text("h5")
        (mtx / "combined_filtered_matrix.h5ad").write_text("h5")
        mq = substage / "run" / "results" / "multiqc"
        mq.mkdir(parents=True)
        (mq / "multiqc_report.html").write_text("<html>ok</html>")
        (substage / "run" / ".gars_run_complete").write_text("now\n")

        code, res, raw = run(self.wrap, ["collect", "--project", "projects/sc-collect"],
                             self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("h5ad", [f["check"] for f in res["failures"]])
        self.assertIn("SC2", " ".join(f["detail"] for f in res["failures"]),
                      "the gate must name the missing sample")

        (mtx / "SC2").mkdir()
        (mtx / "SC2" / "SC2_filtered_matrix.h5ad").write_text("h5")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/sc-collect",
                                         "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertIn("h5ad\tnative\t", (substage / "OUTPUTS.tsv").read_text())
        self.assertIn("COMPLETE", (substage / "STATUS").read_text())
        self.assertIn("claude-test-1", res["history_entry"])

    def test_06_the_raw_matrix_is_never_substituted_for_the_filtered_one(self):
        """The real tree carries BOTH combined_filtered_matrix.h5ad and
        combined_raw_matrix.h5ad. An earlier gate globbed combined_*.h5ad and took the first
        non-empty match, so a filtered matrix that failed to write meant the RAW one was
        published under the same artifact type -- ~90x the barcodes, nearly all ambient, no
        error. Found by truncating the filtered matrix in a real pipeline output; the
        original offline test missed it because its faked tree had only one combined file.
        This fixture therefore mirrors the real shape."""
        project = self._project("sc-rawsub")
        code, res, raw = run(self.cfg_py,
                             ["apply", "--project", "projects/sc-rawsub",
                              "--assay", "scrnaseq", "--genome", "01",
                              "--protocol", "10XV3", "--aligner", "simpleaf"], self.ws)
        self.assertEqual(code, 0, raw)
        substage = (project / "02_bioinformatics" / "scrnaseq"
                    / "01_nfcore-scrnaseq-wrapper")
        mtx = substage / "run" / "results" / "simpleaf" / "mtx_conversions"
        for s in ("SC1", "SC2"):
            (mtx / s).mkdir(parents=True)
            (mtx / s / ("%s_filtered_matrix.h5ad" % s)).write_text("h5")
        # both combined matrices, as the pipeline really writes them
        (mtx / "combined_raw_matrix.h5ad").write_text("RAW" * 100)
        (mtx / "combined_filtered_matrix.h5ad").write_text("FILTERED")
        mq = substage / "run" / "results" / "multiqc"
        mq.mkdir(parents=True)
        (mq / "multiqc_report.html").write_text("<html>ok</html>")
        (substage / "run" / ".gars_run_complete").write_text("now\n")

        code, res, raw = run(self.wrap, ["collect", "--project", "projects/sc-rawsub",
                                         "--model", "m"], self.ws)
        self.assertEqual(code, 0, raw)
        published = [o["path"] for o in res["outputs"] if o["type"] == "h5ad"]
        self.assertEqual(len(published), 1, raw)
        self.assertTrue(published[0].endswith("combined_filtered_matrix.h5ad"),
                        "must publish the filtered matrix, got %r" % published[0])

        # the filtered matrix goes missing; the raw one is still there and must NOT be used
        (mtx / "combined_filtered_matrix.h5ad").unlink()
        (substage / "OUTPUTS.tsv").unlink()
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/sc-rawsub"],
                             self.ws)
        self.assertEqual(code, 1, raw)
        detail = " ".join(f["detail"] for f in res["failures"])
        self.assertIn("combined_filtered_matrix.h5ad", detail)
        self.assertNotIn("combined_raw_matrix.h5ad",
                         str([o.get("path") for o in res.get("outputs", [])]),
                         "the raw matrix must never be published in its place")

    def test_07_empty_combined_matrix_is_refused(self):
        """A zero-byte artifact is a failed run that looks like a successful one."""
        project = self._project("sc-empty")
        code, res, raw = run(self.cfg_py,
                             ["apply", "--project", "projects/sc-empty",
                              "--assay", "scrnaseq", "--genome", "01",
                              "--protocol", "10XV3", "--aligner", "simpleaf"], self.ws)
        self.assertEqual(code, 0, raw)
        substage = (project / "02_bioinformatics" / "scrnaseq"
                    / "01_nfcore-scrnaseq-wrapper")
        mtx = substage / "run" / "results" / "simpleaf" / "mtx_conversions"
        for s in ("SC1", "SC2"):
            (mtx / s).mkdir(parents=True)
            (mtx / s / ("%s_filtered_matrix.h5ad" % s)).write_text("h5")
        (mtx / "combined_filtered_matrix.h5ad").write_text("")     # zero bytes
        mq = substage / "run" / "results" / "multiqc"
        mq.mkdir(parents=True)
        (mq / "multiqc_report.html").write_text("<html>ok</html>")
        (substage / "run" / ".gars_run_complete").write_text("now\n")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/sc-empty"],
                             self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("combined", " ".join(f["detail"] for f in res["failures"]))


class CommitPinTests(unittest.TestCase):
    """A pipeline with no usable release is pinned to a commit, and verified as one.

    nf-core/spatialvi's only tag (v0.1.0, 2023-03-31) sits 1,014 commits behind dev and
    predates most of the current pipeline. `git describe --tags` on such a checkout returns
    `0.1.0-1014-gccdfb48` -- a fact about the nearest ancestor tag, not about the pin -- so a
    commit pin is verified with rev-parse instead."""

    def test_00_tag_pins_and_commit_pins_are_told_apart(self):
        sys.path.insert(0, str(GARS / "_system"))
        import wrapperlib as wl
        for tag in ("2.1.2", "4.2.0", "3.26.0", "0.1.0", "dev", "abc"):
            self.assertFalse(wl.is_commit_pin(tag), "%r is a tag, not a commit" % tag)
        for sha in ("ccdfb48", "ccdfb48659aa8298bb5ed8d7c986651a99e04e7c", "deadbeef"):
            self.assertTrue(wl.is_commit_pin(sha), "%r is a commit" % sha)

    def test_01_every_shipped_pin_is_still_a_tag_pin(self):
        """The six existing assays must be unaffected by commit-pin support."""
        sys.path.insert(0, str(GARS / "_system"))
        import wrapperlib as wl
        for assay, key in sorted(workspace.PIPELINES.items()):
            version = key.rsplit("-", 1)[1]
            if assay == "spatialvi":
                continue
            self.assertFalse(wl.is_commit_pin(version),
                             "%s is pinned to %r, which reads as a commit" % (assay, version))

    def test_02_a_missing_commit_pinned_checkout_says_commit_not_tag(self):
        sys.path.insert(0, str(GARS / "_system"))
        import wrapperlib as wl
        tmp = Path(tempfile.mkdtemp())
        try:
            fails = []
            saved = dict(workspace.PIPELINES)
            workspace.PIPELINES["_probe"] = "nf-core-probe-ccdfb48"
            os.environ["GARS_PIPELINES"] = str(tmp)
            try:
                wl.check_pipeline("_probe", fails)
            finally:
                workspace.PIPELINES.clear()
                workspace.PIPELINES.update(saved)
                os.environ.pop("GARS_PIPELINES", None)
            self.assertTrue(fails)
            self.assertIn("commit ccdfb48", fails[0]["detail"])
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)


class SpatialviTests(unittest.TestCase):
    """Wrapper #7 (decision 0039) and the `sample_dir` input kind it required.

    Spatial is the first assay whose unit of input is a DIRECTORY -- a Space Ranger output
    tree someone else produced -- rather than FASTQ pairs. That needed a per-input-kind
    files.csv header in the deterministic core, which every other assay depends on, so the
    fastq path is asserted unchanged here as well."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-spatial-"))
        cls.ws = cls.tmp / "gars"
        cls.ws.mkdir()
        for d in ("_system", "_references", "_templates"):
            shutil.copytree(str(GARS / d), str(cls.ws / d))
        (cls.ws / "projects").mkdir()
        cls.src = cls.tmp / "spaceranger_runs"
        cls.src.mkdir()
        for name in ("BrainA", "BrainB"):
            outs = cls.src / name / "outs"
            (outs / "spatial").mkdir(parents=True)
            (outs / "filtered_feature_bc_matrix.h5").write_bytes(b"h5\x00" * 200)
        cls.reg_py = cls.ws / "_system" / "stage00_register.py"
        cls.sheet_py = cls.ws / "_system" / "stage01_samplesheet.py"
        cls.wrap = (cls.ws / "_system" / "wrappers" / "nfcore-spatialvi-wrapper"
                    / "nfcore_spatialvi_wrapper.py")

    tearDownClass = classmethod(lambda cls: WorkspaceFixture.tearDownClass.__func__(cls))

    def _project(self, title, source=None):
        for argv in (["create", "--title", title, "--assays", "spatialvi"],
                     ["link", "--project", "projects/" + title, "--assay", "spatialvi",
                      "--source", str(source or self.src)],
                     ["finalize", "--project", "projects/" + title]):
            code, res, raw = run(self.reg_py, argv, self.ws)
            self.assertEqual(code, 0, raw)
        project = self.ws / "projects" / title
        scsv = project / "00_data" / "spatialvi" / "samples.csv"
        with scsv.open() as fh:
            rows = list(csv.reader(fh))
        head = rows[0]
        out = [head]
        for i, r in enumerate(rows[1:]):
            d = dict(zip(head, r))
            d.update({"condition": "tumour" if i == 0 else "normal",
                      "group": "G%d" % (i + 1), "replicate": "1"})
            out.append([d.get(c, "") for c in head])
        with scsv.open("w", newline="") as fh:
            csv.writer(fh).writerows(out)
        code, res, raw = run(self.sheet_py, ["--project", "projects/" + title,
                                             "--confirm-exclusions"], self.ws)
        self.assertEqual(code, 0, raw)
        return project

    def test_00_input_kind_is_per_assay_and_fastq_is_unchanged(self):
        sys.path.insert(0, str(GARS / "_system"))
        import workspace as w
        self.assertEqual(w.input_kind("spatialvi"), "sample_dir")
        for assay in ("rnaseq_bulk", "atacseq_bulk", "chipseq_bulk", "cutandrun",
                      "methylseq", "scrnaseq"):
            self.assertEqual(w.input_kind(assay), "fastq",
                             "%s must keep the FASTQ input kind" % assay)
            self.assertEqual(w.files_header(assay),
                             ["sample_id", "lane", "fastq_1", "fastq_2"])
        self.assertEqual(w.files_header("spatialvi"), ["sample_id", "spaceranger_dir"])

    def test_01_stage00_registers_directories(self):
        project = self._project("spat-reg")
        files = (project / "00_data" / "spatialvi" / "files.csv").read_text()
        self.assertIn("sample_id,spaceranger_dir", files)
        self.assertNotIn("fastq_1", files)
        raw = project / "00_data" / "spatialvi" / "raw"
        for name in ("BrainA", "BrainB"):
            link = raw / name
            self.assertTrue(link.is_symlink(), "%s should be a symlink" % name)
            self.assertTrue(link.is_dir(), "%s should resolve to a directory" % name)

    def test_02_stage01_emits_two_columns_with_absolute_paths(self):
        project = self._project("spat-sheet")
        sheet = (project / "01_samplesheets" / "spatialvi_samplesheet.csv"
                 ).read_text().splitlines()
        self.assertEqual(sheet[0], "sample,spaceranger_dir")
        self.assertEqual(len(sheet) - 1, 2)
        for line in sheet[1:]:
            sample, path = line.split(",")
            self.assertTrue(Path(path).is_absolute(), "path must be absolute: %r" % path)
            # abspath, not resolve: the sheet must point at the project's own symlink so the
            # project's registration of its data is not bypassed.
            self.assertIn("00_data/spatialvi/raw", path)

    def test_03_a_directory_that_is_not_a_spaceranger_run_is_refused(self):
        """Pointing at the wrong level of the tree is the easy mistake, and the pipeline's own
        error for it arrives an hour into a Slurm job."""
        bad = self.tmp / "wrong_level"
        (bad / "SampleZ").mkdir(parents=True)      # no outs/, no *.h5
        project = self._project("spat-wrong", source=bad)
        cfg = project / "_config" / "spatialvi.yaml"
        cfg.write_text(cfg.read_text().replace("<REQUIRED", "# <REQUIRED"))
        code, res, raw = run(self.wrap, ["check", "--project", "projects/spat-wrong"], self.ws)
        self.assertEqual(code, 1, raw)
        detail = " ".join(f["detail"] for f in res["failures"])
        self.assertIn("outs/", detail)

    def test_04_collect_gates_per_sample_and_never_takes_the_raw_h5ad(self):
        """The scrnaseq raw-for-filtered defect, avoided by construction: <sample>-raw.h5ad
        sits beside <sample>.h5ad and is a different object."""
        project = self._project("spat-collect")
        substage = (project / "02_bioinformatics" / "spatialvi"
                    / "01_nfcore-spatialvi-wrapper")
        results = substage / "run" / "results"
        for s in ("BrainA", "BrainB"):
            (results / s / "data").mkdir(parents=True)
            (results / s / "reports").mkdir(parents=True)
            (results / s / "reports" / ("report-%s.html" % s)).write_text("<html>r</html>")
        # BrainA processed; BrainB has ONLY the raw object
        (results / "BrainA" / "data" / "BrainA.h5ad").write_text("processed")
        (results / "BrainB" / "data" / "BrainB-raw.h5ad").write_text("raw only")
        mq = results / "multiqc"
        mq.mkdir(parents=True)
        (mq / "multiqc_report.html").write_text("<html>ok</html>")
        (substage / "run" / ".gars_run_complete").write_text("now\n")

        code, res, raw = run(self.wrap, ["collect", "--project", "projects/spat-collect"],
                             self.ws)
        self.assertEqual(code, 1, raw)
        detail = " ".join(f["detail"] for f in res["failures"])
        self.assertIn("BrainB", detail)
        self.assertIn("-raw.h5ad", detail,
                      "the refusal must say the raw object was seen and not used")
        self.assertFalse((substage / "OUTPUTS.tsv").exists())

        (results / "BrainB" / "data" / "BrainB.h5ad").write_text("processed")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/spat-collect",
                                         "--model", "claude-test-1"], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(sorted(res["samples"]), ["BrainA", "BrainB"])
        types = sorted(o["type"] for o in res["outputs"])
        self.assertEqual(types, ["h5ad", "qc_multiqc", "report"])
        self.assertEqual(len(res["per_sample"]), 2)
        self.assertIn("COMMIT pin", res["history_entry"],
                      "the entry must say the pin is a commit, not imply a release")

    def test_05_a_missing_report_is_refused(self):
        project = self._project("spat-noreport")
        substage = (project / "02_bioinformatics" / "spatialvi"
                    / "01_nfcore-spatialvi-wrapper")
        results = substage / "run" / "results"
        for s in ("BrainA", "BrainB"):
            (results / s / "data").mkdir(parents=True)
            (results / s / "data" / ("%s.h5ad" % s)).write_text("processed")
        (results / "BrainA" / "reports").mkdir(parents=True)
        (results / "BrainA" / "reports" / "report-BrainA.html").write_text("<html>r</html>")
        mq = results / "multiqc"
        mq.mkdir(parents=True)
        (mq / "multiqc_report.html").write_text("<html>ok</html>")
        (substage / "run" / ".gars_run_complete").write_text("now\n")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/spat-noreport"],
                             self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("report", [f["check"] for f in res["failures"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
