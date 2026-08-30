#!/usr/bin/env python3
"""GARS-authored wrapper for nf-core/methylseq 4.2.0 — wrapper #5 (decision 0031).

Same behavioral contract as the atacseq template (decision 0028), on `_system/wrapperlib.py`.
Methylseq-specific facts, each read from the pinned checkout rather than remembered:

- bisulfite alignment needs the FASTA only — no annotation, no peaks, no contrast;
- the quantitative deliverable is per-sample cytosine coverage
  (`bismark/methylation_coverage/<sample>.bismark.cov.gz`), plus context-split calls and
  bedGraph tracks; the exit gate checks a coverage file exists for EVERY sample;
- MultiQC publishes at `multiqc/` (no peak-type subdirectory);
- no plain-human Bismark index exists on this cluster (verified 2026-08-14), so the first run
  builds one — the longest first-run of any assay. No derived cache yet: the first live run
  establishes the published index layout worth harvesting.

Runs on stock python 3.6.8, stdlib only. Nextflow/java are needed only inside submit.sh.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import workspace as ws          # noqa: E402
import wrapperlib as wl         # noqa: E402
from wrapperlib import (EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE,   # noqa: E402
                        emit, fail)

WORKSPACE = Path(__file__).resolve().parents[3]

ASSAY = "methylseq"
SUBSTAGE = "01_nfcore-methylseq-wrapper"
PIPELINE_VERSION = ws.PIPELINES[ASSAY].rsplit("-", 1)[1]

ALIGNERS = ("bismark", "bismark_hisat", "bwameth", "bwamem")
SAMPLESHEET_HEADER = ["sample", "fastq_1", "fastq_2"]

REQUIRED_KEYS = ("reference.fasta", "compute.partition", "compute.time",
                 "compute.cpus", "compute.mem", "compute.work_dir")


def paths_for(project):
    return {"substage": project / "02_bioinformatics" / ASSAY / SUBSTAGE,
            "config": project / "_config" / ("%s.yaml" % ASSAY),
            "samplesheet": project / "01_samplesheets" / ("%s_samplesheet.csv" % ASSAY),
            # the descriptor names which nextflow config this venue pairs with (0039)
            "executor_config": wl.ex.nextflow_config_path(project)
            or project / "_config" / "nextflow.slurm.config"}


def run_checks(project):
    fails = []
    paths = paths_for(project)
    cfg = {}
    if not paths["config"].is_file():
        fails.append(fail("preconditions", "no config at _config/%s.yaml" % ASSAY))
    else:
        cfg = wl.read_config(paths["config"])
        wl.check_config_common(cfg, REQUIRED_KEYS, fails)
        aligner = cfg.get("aligner", "bismark")
        if aligner not in ALIGNERS:
            fails.append(fail("config", "aligner %r is not one of %s"
                              % (aligner, "|".join(ALIGNERS))))
    wl.check_samplesheet(paths["samplesheet"], SAMPLESHEET_HEADER, fails)
    paths["checkout"] = wl.check_pipeline(ASSAY, fails)
    wl.check_executor_config(paths["executor_config"], fails)
    wl.check_run_dir(paths["substage"], fails)
    return fails, cfg, paths


def cmd_check(args):
    project = Path(args.project)
    result = {"command": "check", "ok": False, "assay": ASSAY, "failures": []}
    if not project.is_dir():
        result["error"] = "no such project: %s" % project
        return emit(result, EXIT_USAGE)
    fails, cfg, paths = run_checks(project)
    result["failures"] = fails
    result["ok"] = not fails
    preflight = paths["substage"] / "preflight"
    preflight.mkdir(parents=True, exist_ok=True)
    with ws.atomic_open(preflight / "check_result.json") as fh:
        json.dump({"ok": result["ok"], "failures": fails, "pipeline": ws.PIPELINES[ASSAY],
                   "wrapper": "nfcore-methylseq-wrapper"}, fh, indent=2, sort_keys=True)
    result["wrote"] = str((preflight / "check_result.json").relative_to(project))
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


def build_params(cfg, paths):
    """The audited translation of _config/<assay>.yaml into pipeline parameters."""
    return [
        ("input", str(paths["samplesheet"].resolve())),
        ("outdir", str((paths["substage"] / "run" / "results").resolve())),
        ("fasta", cfg["reference.fasta"]),
        ("aligner", cfg.get("aligner", "bismark")),
    ]


def cmd_prepare(args):
    project = Path(args.project)
    result = {"command": "prepare", "ok": False, "assay": ASSAY, "failures": []}
    if not project.is_dir():
        result["error"] = "no such project: %s" % project
        return emit(result, EXIT_USAGE)
    fails, cfg, paths = run_checks(project)
    if fails:
        result["failures"] = fails
        result["error"] = "preflight failed; nothing written. Run `check` for the same detail."
        return emit(result, EXIT_FAILURE)

    substage = paths["substage"]
    substage.mkdir(parents=True, exist_ok=True)
    (substage / "logs").mkdir(exist_ok=True)

    params = build_params(cfg, paths)
    wl.write_params_yaml(substage, ASSAY, params)

    work_dir = "%s/%s-%s" % (cfg["compute.work_dir"].rstrip("/"),
                             project.resolve().name, ASSAY)
    body = """nextflow run "{checkout}" \\
    -profile apptainer \\
    -c "{executor_config}" \\
    -params-file "{substage}/params.yaml" \\
    -work-dir "{work_dir}" \\
    $RESUME""".format(checkout=paths["checkout"],
                      executor_config=paths["executor_config"].resolve(),
                      substage=substage.resolve(), work_dir=work_dir)
    wl.write_submit_sh(substage, WORKSPACE, cfg, project.resolve().name, ASSAY, body)
    wl.write_reproducibility(substage, ASSAY, paths["checkout"],
                             {"samplesheet": paths["samplesheet"], "config": paths["config"]},
                             params)

    result.update({"ok": True,
                   "wrote": ["params.yaml", "submit.sh", "reproducibility/manifest.json",
                             "reproducibility/commands.sh"],
                   "params": dict(params),
                   "submit": str((substage / "submit.sh").resolve()),
                   "samples": wl.samplesheet_samples(paths["samplesheet"])})
    return emit(result, EXIT_OK)


def cmd_collect(args):
    project = Path(args.project)
    result = {"command": "collect", "ok": False, "assay": ASSAY, "failures": []}
    if not project.is_dir():
        result["error"] = "no such project: %s" % project
        return emit(result, EXIT_USAGE)
    paths = paths_for(project)
    substage = paths["substage"]
    if not (substage / "run" / ".gars_run_complete").is_file():
        result["error"] = ("run/.gars_run_complete is absent: the pipeline has not finished "
                           "(or crashed before the marker). Check Slurm and the logs; collect "
                           "gates on completion, it does not wait for it.")
        return emit(result, EXIT_REFUSED)

    cfg = wl.read_config(paths["config"])
    aligner = cfg.get("aligner", "bismark")
    results = substage / "run" / "results"
    aligner_dir = results / ("bismark" if aligner.startswith("bismark") else aligner)
    samples = wl.samplesheet_samples(paths["samplesheet"])
    fails = []

    coverage_dir = aligner_dir / "methylation_coverage"
    covs = sorted(coverage_dir.glob("*.cov.gz")) if coverage_dir.is_dir() else []
    if not covs:
        fails.append(fail("methylation_coverage", "no *.cov.gz under %s" % coverage_dir))
    else:
        # Content, not existence: every sample must have a coverage file.
        names = " ".join(p.name for p in covs)
        missing = [s for s in samples if s not in names]
        if missing:
            fails.append(fail("methylation_coverage",
                              "no coverage file for sample(s): %s -- a sample lost to a "
                              "failed process disappears here and nowhere downstream"
                              % ", ".join(missing)))

    calls_dir = aligner_dir / "methylation_calls"
    if not (calls_dir.is_dir() and any(calls_dir.iterdir())):
        fails.append(fail("methylation_calls", "nothing under %s" % calls_dir))
    bedgraph_dir = aligner_dir / "bedGraph"
    if not (bedgraph_dir.is_dir() and any(bedgraph_dir.iterdir())):
        fails.append(fail("bedgraph", "nothing under %s" % bedgraph_dir))
    multiqc = results / "multiqc" / "multiqc_report.html"
    if not multiqc.is_file() or multiqc.stat().st_size == 0:
        fails.append(fail("qc_multiqc", "missing or empty %s" % multiqc))

    if fails:
        result["failures"] = fails
        return emit(result, EXIT_FAILURE)

    rel = lambda p: str(p.relative_to(substage))  # noqa: E731
    outputs = [("methylation_coverage", rel(coverage_dir)),
               ("methylation_calls", rel(calls_dir)),
               ("bedgraph", rel(bedgraph_dir)),
               ("qc_multiqc", rel(multiqc))]
    with ws.atomic_open(substage / "OUTPUTS.tsv") as fh:
        fh.write("# type\trole\tpath\n")
        for typ, path in outputs:
            fh.write("%s\tnative\t%s\n" % (typ, path))

    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with ws.atomic_open(substage / "STATUS") as fh:
        fh.write("COMPLETE %s\n" % now)

    version = ws.template_version(WORKSPACE)
    model = args.model or "unknown"
    entry = "\n".join([
        "## <ISO-8601 date> — 02_bioinformatics/%s/%s — pipeline complete" % (ASSAY, SUBSTAGE),
        "",
        "Template version: %s" % version,
        "Model: %s" % model,
        "Pipeline: nf-core/methylseq %s (local checkout), aligner %s"
        % (PIPELINE_VERSION, aligner),
        "Samples: %d (%s)" % (len(samples), ", ".join(samples)),
        "Outputs: " + ", ".join("`%s`" % t for t, _ in outputs),
    ])
    result.update({"ok": True, "outputs": [{"type": t, "path": p} for t, p in outputs],
                   "samples": samples, "template_version": version, "model": model,
                   "history_entry": entry})
    return emit(result, EXIT_OK)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    for name, needs_model in (("check", False), ("prepare", False), ("collect", True)):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        if needs_model:
            p.add_argument("--model", default="unknown",
                           help="the exact model id of the agent executing this sub-stage "
                                "(decision 0024)")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help(sys.stderr)
        return EXIT_USAGE
    return {"check": cmd_check, "prepare": cmd_prepare, "collect": cmd_collect}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
