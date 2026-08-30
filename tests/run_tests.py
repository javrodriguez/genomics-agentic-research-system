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
import shutil
import stat
import subprocess
import sys
import tempfile
import time
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


class ExecutorSeamTests(unittest.TestCase):
    """Decision 0039: the scheduler is a workspace setting, not a spelling in generated bytes.

    The load-bearing property is that a cluster notices nothing: with no `_config/executor.yaml`
    the generated `submit.sh` is byte-identical to what this system produced before the seam
    existed, pinned here against fixtures captured from the pre-seam code.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(GARS / "_system"))
        import executorlib
        import wrapperlib
        cls.ex = executorlib
        cls.wl = wrapperlib
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-test-executor-"))
        cls.cfg = {"compute.partition": "cpu_medium", "compute.time": "1:00:00",
                   "compute.cpus": "4", "compute.mem": "8G"}
        cls.fixtures = Path(__file__).resolve().parent / "fixtures"

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(GARS / "_system"))
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def _project(self, name, descriptor_text=None):
        """A throwaway project dir owning `_config/`, optionally with a descriptor in it."""
        project = self.tmp / name
        (project / "_config").mkdir(parents=True, exist_ok=True)
        if descriptor_text is not None:
            (project / "_config" / "executor.yaml").write_text(descriptor_text,
                                                               encoding="utf-8")
        return project

    def _submit_sh(self, project, assay, body="echo body"):
        sub = project / "02_bioinformatics" / assay / ("01_%s-wrapper" % assay)
        sub.mkdir(parents=True, exist_ok=True)
        self.wl.write_submit_sh(sub, project, self.cfg, "proj", assay, body)
        return sub, (sub / "submit.sh").read_text()

    # -- the property that lets a cluster upgrade without noticing -------------------------

    def test_00_slurm_default_is_byte_identical(self):
        """No descriptor -> the pre-seam bytes, exactly. Fixtures were captured by running
        the pre-change `write_submit_sh`; paths are tokenised because they are absolute."""
        project = self._project("no-descriptor")
        for assay in ("rnaseq_bulk", "atacseq_bulk"):
            sub, script = self._submit_sh(project, assay)
            script = script.replace(str(sub.resolve()), "{{SUBSTAGE}}") \
                           .replace(str(project), "{{WORKSPACE}}")
            golden = (self.fixtures / ("submit_sh_%s.golden" % assay)).read_text()
            self.assertEqual(script, golden, "%s submit.sh drifted from the pre-seam bytes"
                             % assay)

    def test_01_shipped_template_resolves_to_the_builtin(self):
        """The seeded `executor.yaml` and the built-in Slurm descriptor must not drift apart:
        a project that keeps the seeded file and one that deletes it get the same scheduler."""
        text = (GARS / "_templates" / "config" / "executor.yaml").read_text(encoding="utf-8")
        parsed = self.ex.parse_descriptor(text)
        for key, value in self.ex.SLURM.items():
            if key == "submit_note":
                continue        # prose, carried by the built-in only
            self.assertEqual(parsed.get(key), value, "template drifted on %r" % key)
        self.assertEqual(self.ex.validate(parsed), [])

    def test_02_stage_00_seeds_the_descriptor(self):
        self.assertIn("executor.yaml",
                      (GARS / "_system" / "stage00_register.py").read_text(encoding="utf-8"))
        self.assertTrue((GARS / "_templates" / "config" / "executor.yaml").is_file())

    # -- a descriptor actually steers the generated bytes ----------------------------------

    def test_03_descriptor_replaces_the_directives_block(self):
        project = self._project("batchy", """name: awsbatch
directives:
  - "# job: {project}-{assay} on {partition} ({cpus} cpu / {mem})"
submit_argv:
  - aws
  - batch
  - submit-job
  - "{script}"
job_id_regex: "\\\"jobId\\\": \\\"([-a-z0-9]+)\\\""
status_argv:
  - aws
  - batch
  - describe-jobs
  - "{job_id}"
status_map:
  SUBMITTED: PENDING
  RUNNABLE: PENDING
  RUNNING: RUNNING
  SUCCEEDED: COMPLETED
  FAILED: FAILED
nextflow_config: nextflow.awsbatch.config
""")
        _, script = self._submit_sh(project, "rnaseq_bulk")
        self.assertNotIn("#SBATCH", script)
        self.assertIn("# job: proj-rnaseq_bulk on cpu_medium (4 cpu / 8G)", script)
        # the requeue guard and the environment are the wrapper's, not the scheduler's
        self.assertIn(".gars_run_complete", script)
        self.assertIn('source "$WS/_system/gars-env.sh"', script)
        # ...and the one Slurm-specific sentence went with the Slurm descriptor
        self.assertNotIn("Slurm snapshots", script)

    def test_04_reproducibility_records_the_real_submission(self):
        project = self._project("repro", "name: slurm\n")
        sub, _ = self._submit_sh(project, "rnaseq_bulk")
        self.wl.write_reproducibility(sub, "rnaseq_bulk", sub, {}, [])
        commands = (sub / "reproducibility" / "commands.sh").read_text()
        self.assertIn("sbatch %s/submit.sh" % sub.resolve(), commands)

    # -- the local backend: a real submit -> status walk with no cluster --------------------

    def test_05_local_backend_walks_submit_to_completed(self):
        project = self._project("local-ok", "name: local\n")
        script = project / "job.sh"
        script.write_text("#!/bin/bash\nsleep 1\necho done\n")
        os.chmod(str(script), 0o755)
        job_id, detail = self.ex.submit(project, script)
        self.assertIsNone(detail)
        self.assertTrue(job_id.isdigit(), job_id)
        seen = set()
        for _ in range(120):
            state, err = self.ex.status(project, job_id)
            self.assertIsNone(err)
            seen.add(state)
            if state in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.25)
        self.assertIn("RUNNING", seen)
        self.assertEqual(state, "COMPLETED")

    def test_06_local_backend_reports_a_failure_as_failed(self):
        project = self._project("local-bad", "name: local\n")
        script = project / "job.sh"
        script.write_text("#!/bin/bash\nexit 3\n")
        job_id, _ = self.ex.submit(project, script)
        for _ in range(120):
            state, _ = self.ex.status(project, job_id)
            if state in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.25)
        self.assertEqual(state, "FAILED")

    def test_07_local_generated_script_carries_no_scheduler_directives(self):
        project = self._project("local-gen", "name: local\n")
        _, script = self._submit_sh(project, "rnaseq_bulk")
        self.assertNotIn("#SBATCH", script)
        self.assertIn("Executor: local", script)

    def test_07b_literal_braces_in_a_descriptor_survive(self):
        """The smoke's first real catch (2026-08-29): the awsbatch submit argv carries a
        JSON --container-overrides element, and str.format read {"command": ...} as a
        placeholder and crashed at submit time. The descriptor is data, not a template
        language -- only the documented tokens substitute."""
        d = {
            "name": "awsbatch",
            "submit_argv": ["aws", "batch", "submit-job", "--container-overrides",
                            '{"command":["bash","{script}"]}'],
            "status_argv": ["aws", "batch", "describe-jobs", "--jobs", "{job_id}"],
            "directives": ['# literal {"json": true} stays; {project} substitutes'],
        }
        argv = self.ex.submit_argv(d, "/tmp/x.sh")
        self.assertEqual(argv[-1], '{"command":["bash","/tmp/x.sh"]}')
        argv = self.ex.status_argv(d, "job-123")
        self.assertEqual(argv[-1], "job-123")
        lines = self.ex.header_lines(None, {}, "proj", "assay", "/tmp", descriptor=d)
        self.assertEqual(lines, ['# literal {"json": true} stays; proj substitutes'])

    def test_07c_an_uncompilable_regex_is_refused_by_name(self):
        """The smoke's second catch: a shell-escaped quote truncated by the verbatim quote
        rule left job_id_regex as a lone backslash, and submit raised a raw PatternError.
        The promise is refusal by name, never a traceback."""
        d = {"name": "custom", "submit_argv": ["echo", "{script}"],
             "status_argv": ["true", "{job_id}"],
             "job_id_regex": "\\", "status_map": {"R": "RUNNING"}}
        problems = self.ex.validate(d)
        self.assertTrue(any("does not compile" in x for x in problems), problems)
        # submit really runs (echo exists and succeeds), so the failure reached IS the
        # regex path -- not an absent binary standing in for it.
        job_id, detail = self.ex.submit(Path("/tmp"), "/tmp/x.sh", descriptor=d)
        self.assertIsNone(job_id)
        self.assertIn("does not compile", detail)

    # -- a broken descriptor is refused by name, never guessed at ---------------------------

    def test_08_descriptor_problems_surface_as_named_failures(self):
        """These are the failures `check` reports: preflight calls `check_executor_config`,
        so asserting on it directly runs everywhere, including off-cluster where no pinned
        pipeline checkout exists and `check` itself cannot reach PASS."""
        project = self._project("broken", """name: pbs
directives:
  - "#PBS -N {project}-{nonsense}"
submit_argv:
  - qsub
status_argv:
  - qstat
status_map:
  R: BUSY
""")
        (project / "_config" / "nextflow.slurm.config").write_text("process { }\n")
        fails = []
        self.wl.check_executor_config(project / "_config" / "nextflow.slurm.config", fails)
        joined = " | ".join(f["detail"] for f in fails)
        self.assertIn("{nonsense}", joined)
        self.assertIn("{script}", joined)          # submit_argv never names the script
        self.assertIn("{job_id}", joined)          # status_argv never names the job
        self.assertIn("job_id_regex", joined)
        self.assertIn("BUSY", joined)              # outside the closed state vocabulary
        self.assertTrue(all(f["check"] == "executor_config" for f in fails), fails)

    def test_09_the_descriptor_names_which_nextflow_config_is_demanded(self):
        project = self._project("nxf", """name: awsbatch
directives:
  - "# job {project}"
submit_argv:
  - aws
  - "{script}"
job_id_regex: "(.+)"
status_argv:
  - aws
  - "{job_id}"
status_map:
  RUNNING: RUNNING
nextflow_config: nextflow.awsbatch.config
""")
        fails = []
        self.wl.check_executor_config(project / "_config" / "nextflow.slurm.config", fails)
        self.assertEqual([f["detail"] for f in fails],
                         ["no _config/nextflow.awsbatch.config -- stage 00 seeds it"])
        (project / "_config" / "nextflow.awsbatch.config").write_text("process { }\n")
        fails = []
        self.wl.check_executor_config(project / "_config" / "nextflow.slurm.config", fails)
        self.assertEqual(fails, [])

    def test_10_a_params_block_is_still_refused(self):
        project = self._project("params")
        (project / "_config" / "nextflow.slurm.config").write_text(
            "params {\n  foo = 1\n}\n")
        fails = []
        self.wl.check_executor_config(project / "_config" / "nextflow.slurm.config", fails)
        self.assertEqual(len(fails), 1)
        self.assertIn("params block", fails[0]["detail"])


class Stage03VenueGridTests(unittest.TestCase):
    """The venue vocabulary after 0039: `batch` is the venue, `sbatch` is its Slurm-era
    spelling, and every plan already written on the cluster still approves."""

    PLAN = """# Analysis plan: venue-grid

Status: DRAFT

## Goal
A one-line plan whose only interesting property is its venue.

## Inputs
| Artifact type | Resolved from | Path |
|---|---|---|
| counts_gene | 01_nfcore-rnaseq-wrapper | results/counts.tsv |

## Method
1. Load the matrix (gars-bio).

## Outputs
| File | Type | Description |
|---|---|---|
| results/out.csv | table | one row per sample |

## Execution
%s
Seconds; kilobytes.
"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="gars-test-venue-"))
        cls.ws = cls.tmp / "gars"
        cls.ws.mkdir()
        for d in ("_system", "_references", "_templates"):
            shutil.copytree(str(GARS / d), str(cls.ws / d))
        cls.project = cls.ws / "projects" / "venue-test"
        cls.project.mkdir(parents=True)
        cls.s3 = cls.ws / "_system" / "stage03_analysis.py"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def _approve_with(self, venue_line, slug):
        code, res, raw = run(self.s3, ["create", "--project", "projects/venue-test",
                                       "--slug", slug], self.ws)
        self.assertEqual(code, 0, raw)
        adir = self.project / "03_custom_analysis" / res["analysis"]
        (adir / "PLAN.md").write_text(self.PLAN % venue_line)
        return run(self.s3, ["approve", "--project", "projects/venue-test",
                             "--analysis", res["analysis"]], self.ws)

    def test_00_the_skeleton_now_says_batch(self):
        code, res, raw = run(self.s3, ["create", "--project", "projects/venue-test",
                                       "--slug", "skeleton-check"], self.ws)
        self.assertEqual(code, 0, raw)
        text = (self.project / "03_custom_analysis" / res["analysis"] / "PLAN.md").read_text()
        self.assertIn("Runs: batch", text)
        self.assertIn("decision 0039", text)

    def test_01_accepted_venues(self):
        for venue in ("Runs: batch", "Runs: sbatch",
                      "Runs: login-node (user-requested)"):
            code, res, raw = self._approve_with(venue, "accept-" + venue.split()[-1].strip("()"))
            self.assertEqual(code, 0, "%s was refused: %s" % (venue, raw))
            self.assertTrue(res["ok"])

    def test_02_refused_venues(self):
        for venue, slug in (("Runs: login-node", "bare-login"),
                            ("Runs: awsbatch", "garbage")):
            code, res, raw = self._approve_with(venue, slug)
            self.assertEqual(code, 2, raw)
            self.assertTrue(any("not a recognised venue" in b for b in res["blocked"]), raw)

    def test_03_a_missing_runs_line_is_still_refused(self):
        code, res, raw = self._approve_with("Login node; seconds.", "no-runs-line")
        self.assertEqual(code, 2, raw)
        self.assertTrue(any("Runs:" in b for b in res["blocked"]), raw)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
