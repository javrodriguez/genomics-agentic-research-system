#!/usr/bin/env python3
"""GARS-authored wrapper for nf-core/cutandrun 3.2.2 — wrapper #4 (decision 0031).

Same behavioral contract as the atacseq template (decision 0028), on `_system/wrapperlib.py`.
CUT&RUN-specific facts, each read from the pinned checkout rather than remembered:

- signal is calibrated against a **spike-in genome** (E. coli K12 by convention); the config
  carries `spikein.fasta` from the local iGenomes mirror as a presented default;
- the samplesheet is group-shaped: `group,replicate,fastq_1,fastq_2,control`, and `control`
  names the IgG **group**, not a sample (decision 0030);
- output layout is numbered (from the pipeline's own `conf/modules.config`):
  BAMs at `02_alignment/<aligner>/target/markdup/`, bigwigs at
  `03_peak_calling/03_bed_to_bigwig/`, peaks at `03_peak_calling/04_called_peaks/`,
  consensus at `03_peak_calling/05_consensus_peaks/`, MultiQC at `04_reporting/multiqc/`;
- `peakcaller` (seacr|macs2), `normalisation` and `use_control` are presented defaults in the
  seeded config — shown before anything runs, changed only by the user;
- no derived-index cache yet: the pipeline builds bowtie2 + spike-in indices per run. First
  live run establishes whether a cache layout is worth adding.

Runs on stock python 3.6.8, stdlib only. Nextflow/java are needed only inside submit.sh.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import workspace as ws          # noqa: E402
import wrapperlib as wl         # noqa: E402
from wrapperlib import (EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE,   # noqa: E402
                        emit, fail)

WORKSPACE = Path(__file__).resolve().parents[3]

ASSAY = "cutandrun"
SUBSTAGE = "01_nfcore-cutandrun-wrapper"
PIPELINE_VERSION = ws.PIPELINES[ASSAY].rsplit("-", 1)[1]

PEAKCALLERS = ("seacr", "macs2")
NORMALISATION = ("Spikein", "RPKM", "CPM", "BPM", "None")
SAMPLESHEET_HEADER = ["group", "replicate", "fastq_1", "fastq_2", "control"]

REQUIRED_KEYS = ("reference.fasta", "reference.gtf", "reference.mito_name", "spikein.fasta",
                 "peaks.peakcaller", "peaks.normalisation", "compute.partition",
                 "compute.time", "compute.cpus", "compute.mem", "compute.work_dir")


def paths_for(project):
    return {"substage": project / "02_bioinformatics" / ASSAY / SUBSTAGE,
            "config": project / "_config" / ("%s.yaml" % ASSAY),
            "samplesheet": project / "01_samplesheets" / ("%s_samplesheet.csv" % ASSAY),
            "executor_config": project / "_config" / "nextflow.slurm.config"}


def run_checks(project):
    fails = []
    paths = paths_for(project)
    cfg = {}
    if not paths["config"].is_file():
        fails.append(fail("preconditions", "no config at _config/%s.yaml" % ASSAY))
    else:
        cfg = wl.read_config(paths["config"])
        wl.check_config_common(cfg, REQUIRED_KEYS, fails)
        spikein = cfg.get("spikein.fasta")
        if spikein and "<REQUIRED" not in spikein and not os.access(spikein, os.R_OK):
            fails.append(fail("config", "spikein.fasta is not readable: %s -- CUT&RUN "
                                        "normalisation needs the spike-in genome" % spikein))
        pc = cfg.get("peaks.peakcaller", "")
        if pc and pc not in PEAKCALLERS:
            fails.append(fail("config", "peaks.peakcaller %r is not seacr|macs2" % pc))
        norm = cfg.get("peaks.normalisation", "")
        if norm and norm not in NORMALISATION:
            fails.append(fail("config", "peaks.normalisation %r is not one of %s"
                              % (norm, "|".join(NORMALISATION))))
        blacklist = cfg.get("reference.blacklist")
        if blacklist and not os.access(blacklist, os.R_OK):
            fails.append(fail("config", "reference.blacklist is not readable: %s" % blacklist))

    # fastq paths sit at columns 2 and 3 in the group-shaped sheet
    wl.check_samplesheet(paths["samplesheet"], SAMPLESHEET_HEADER, fails,
                         path_columns=(2, 3))
    if paths["samplesheet"].is_file() and cfg.get("peaks.use_control", "true") == "true":
        lines = paths["samplesheet"].read_text(encoding="utf-8").splitlines()[1:]
        rows = [l.split(",") for l in lines if l.strip()]
        controls = {r[0] for r in rows if len(r) > 4 and not r[4]}
        targets = [r for r in rows if len(r) > 4 and r[4]]
        if rows and not targets:
            fails.append(fail("samplesheet",
                              "no row names a control group: with use_control true, every "
                              "target group must point at its IgG group. Fill `control` in "
                              "samples.csv and re-run stage 01."))
        for r in targets:
            if r[4] not in controls:
                fails.append(fail("samplesheet",
                                  "group %s names control %r, which is not a control group in "
                                  "this samplesheet (a control row has an empty `control`)"
                                  % (r[0], r[4])))
    checkout = wl.check_pipeline(ASSAY, fails)
    wl.check_executor_config(paths["executor_config"], fails)
    wl.check_run_dir(paths["substage"], fails)
    paths["checkout"] = checkout
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
                   "wrapper": "nfcore-cutandrun-wrapper"}, fh, indent=2, sort_keys=True)
    result["wrote"] = str((preflight / "check_result.json").relative_to(project))
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


def build_params(cfg, paths):
    """The audited translation of _config/<assay>.yaml into pipeline parameters."""
    params = [
        ("input", str(paths["samplesheet"].resolve())),
        ("outdir", str((paths["substage"] / "run" / "results").resolve())),
        ("fasta", cfg["reference.fasta"]),
        ("gtf", cfg["reference.gtf"]),
        ("mito_name", cfg["reference.mito_name"]),
        ("spikein_fasta", cfg["spikein.fasta"]),
        ("peakcaller", cfg["peaks.peakcaller"]),
        ("normalisation_mode", cfg["peaks.normalisation"]),
        ("use_control", cfg.get("peaks.use_control", "true")),
    ]
    if cfg.get("reference.blacklist"):
        params.append(("blacklist", cfg["reference.blacklist"]))
    return params


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
                   "groups": wl.samplesheet_samples(paths["samplesheet"], column=0)})
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
    aligner = "bowtie2"      # the pipeline's only aligner at this version
    results = substage / "run" / "results"
    lines = paths["samplesheet"].read_text(encoding="utf-8").splitlines()[1:]
    rows = [l.split(",") for l in lines if l.strip()]
    groups = sorted({r[0] for r in rows})
    target_groups = sorted({r[0] for r in rows if len(r) > 4 and r[4]})
    fails = []

    bam_dir = results / "02_alignment" / aligner / "target" / "markdup"
    if not (bam_dir.is_dir() and any(bam_dir.glob("*.bam"))):
        fails.append(fail("bam_genome", "no *.bam under %s" % bam_dir))

    bigwig_dir = results / "03_peak_calling" / "03_bed_to_bigwig"
    if not (bigwig_dir.is_dir() and any(bigwig_dir.glob("*.bigWig"))):
        fails.append(fail("bigwig", "no *.bigWig under %s" % bigwig_dir))

    peaks_dir = results / "03_peak_calling" / "04_called_peaks"
    peak_files = sorted(peaks_dir.glob("**/*.bed")) if peaks_dir.is_dir() else []
    if not peak_files:
        fails.append(fail("peaks", "no called-peak *.bed under %s" % peaks_dir))
    else:
        # Content, not existence: every target group must have a peak file.
        names = " ".join(p.name for p in peak_files)
        missing = [g for g in target_groups if g not in names]
        if missing:
            fails.append(fail("peaks",
                              "no called-peak file for target group(s): %s -- a group lost to "
                              "a failed process disappears here and nowhere downstream"
                              % ", ".join(missing)))

    consensus_dir = results / "03_peak_calling" / "05_consensus_peaks"
    consensus = sorted(consensus_dir.glob("*.bed")) if consensus_dir.is_dir() else []
    if not consensus:
        fails.append(fail("peaks_consensus", "no consensus *.bed under %s" % consensus_dir))

    multiqc = results / "04_reporting" / "multiqc" / "multiqc_report.html"
    if not multiqc.is_file() or multiqc.stat().st_size == 0:
        fails.append(fail("qc_multiqc", "missing or empty %s" % multiqc))

    if fails:
        result["failures"] = fails
        return emit(result, EXIT_FAILURE)

    rel = lambda p: str(p.relative_to(substage))  # noqa: E731
    outputs = [("peaks", rel(peaks_dir)), ("peaks_consensus", rel(consensus[0])),
               ("bigwig", rel(bigwig_dir)), ("bam_genome", rel(bam_dir)),
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
        "Pipeline: nf-core/cutandrun %s (local checkout), %s peaks, %s normalisation"
        % (PIPELINE_VERSION, cfg.get("peaks.peakcaller", "seacr"),
           cfg.get("peaks.normalisation", "Spikein")),
        "Groups: %d (%s), of which targets: %d" % (len(groups), ", ".join(groups),
                                                   len(target_groups)),
        "Outputs: " + ", ".join("`%s`" % t for t, _ in outputs),
    ])
    result.update({"ok": True, "outputs": [{"type": t, "path": p} for t, p in outputs],
                   "groups": groups, "template_version": version, "model": model,
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
