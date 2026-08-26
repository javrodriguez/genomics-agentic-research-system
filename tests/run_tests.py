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
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GARS = REPO / "gars"


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
        gid = res["genomes"][0]["id"]
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
            r[head.index("condition")] = "KO" if i == 1 else "WT"
            r[head.index("group")] = "G1"
            r[head.index("replicate")] = str(i)
        with samples_csv.open("w", newline="") as fh:
            csv.writer(fh).writerows(rows)
        code, res, raw = run(self.sheet_py, ["--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 0, raw)
        sheet = self.project / "01_samplesheets" / "atacseq_bulk_samplesheet.csv"
        self.assertEqual(sheet.read_text().splitlines()[0], "sample,fastq_1,fastq_2,replicate",
                         "the emitted format is the assay's own, not the RNA layout")

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
        self._fake_results(["ATAC1", "ATAC2"], include_in_counts=["ATAC1"])
        (self.substage / "run" / ".gars_run_complete").write_text("now\n")
        code, res, raw = run(self.wrap, ["collect", "--project", "projects/atac-test"], self.ws)
        self.assertEqual(code, 1, raw)
        self.assertIn("counts_peaks", [f["check"] for f in res["failures"]])
        # full tree: passes, registers, stamps
        self._fake_results(["ATAC1", "ATAC2"])
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
