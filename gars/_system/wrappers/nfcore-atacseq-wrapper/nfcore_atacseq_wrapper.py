#!/usr/bin/env python3
"""GARS-authored wrapper for nf-core/atacseq 2.1.2 — wrapper #1 of the assay expansion.

The same behavioral contract as the ClawBio wrappers, in the `_system/` idiom (decision 0028):
one file, JSON on stdout, exit codes 0 ok / 1 failure / 2 refused / 3 usage, deterministic
artifacts written by code. The machinery every wrapper shares — config parsing, checkout
verification, the generated `submit.sh` with the requeue guard, the atomic cache harvest —
lives in `_system/wrapperlib.py`; what is atacseq-specific here is the parameter translation
and the exit-gate paths.

Subcommands, in run order (the sub-stage contract orchestrates; this computes):

  check    preflight. Validates config, samplesheet, pipeline checkout, executor config and
           output directory. Writes preflight/check_result.json. Exit 1 lists every failure.
  prepare  re-validates, then writes params.yaml, submit.sh and the reproducibility bundle.
           Deterministic: same inputs, same bytes.
  collect  the exit gate after the Slurm job finishes: every sample must appear in the
           consensus count-matrix header (content, not existence — decision 0010). Writes
           OUTPUTS.tsv and STATUS, harvests the aligner index into the derived cache, returns
           the history entry (template version + model, decision 0024) to append verbatim.

Runs on stock python 3.6.8, stdlib only. Nextflow/java are needed only inside submit.sh.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

# .../<workspace>/_system/wrappers/nfcore-atacseq-wrapper/<this file>
# parents: [0]=the wrapper dir, [1]=wrappers, [2]=_system, [3]=the workspace root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import workspace as ws          # noqa: E402
import wrapperlib as wl         # noqa: E402
from wrapperlib import (EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE,   # noqa: E402
                        emit, fail)

WORKSPACE = Path(__file__).resolve().parents[3]

ASSAY = "atacseq_bulk"
SUBSTAGE = "01_nfcore-atacseq-wrapper"
PIPELINE_VERSION = ws.PIPELINES[ASSAY].rsplit("-", 1)[1]

ALIGNERS = ("bwa", "bowtie2", "chromap", "star")
INDEX_PARAM = {"bwa": "bwa_index", "bowtie2": "bowtie2_index",
               "chromap": "chromap_index", "star": "star_index"}
PEAK_TYPES = ("narrow", "broad")
SAMPLESHEET_HEADER = ["sample", "fastq_1", "fastq_2", "replicate"]

REQUIRED_KEYS = ("reference.fasta", "reference.gtf", "reference.mito_name",
                 "peaks.type", "peaks.macs_gsize", "compute.partition", "compute.time",
                 "compute.cpus", "compute.mem", "compute.work_dir")


def paths_for(project):
    return {"substage": project / "02_bioinformatics" / ASSAY / SUBSTAGE,
            "config": project / "_config" / ("%s.yaml" % ASSAY),
            "samplesheet": project / "01_samplesheets" / ("%s_samplesheet.csv" % ASSAY),
            # the descriptor names which nextflow config this venue pairs with (0039)
            "executor_config": wl.ex.nextflow_config_path(project)
            or project / "_config" / "nextflow.slurm.config"}


def run_checks(project):
    """Everything that must be true before a job may be submitted."""
    fails = []
    paths = paths_for(project)
    cfg = {}
    if not paths["config"].is_file():
        fails.append(fail("preconditions", "no config at _config/%s.yaml" % ASSAY))
    else:
        cfg = wl.read_config(paths["config"])
        wl.check_config_common(cfg, REQUIRED_KEYS, fails)
        blacklist = cfg.get("reference.blacklist")
        if blacklist and not os.access(blacklist, os.R_OK):
            fails.append(fail("config", "reference.blacklist is not readable: %s" % blacklist))
        aligner = cfg.get("aligner", "bwa")
        if aligner not in ALIGNERS:
            fails.append(fail("config", "aligner %r is not one of %s"
                              % (aligner, "|".join(ALIGNERS))))
        ptype = cfg.get("peaks.type", "")
        if ptype and "<REQUIRED" not in ptype and ptype not in PEAK_TYPES:
            fails.append(fail("config", "peaks.type %r is not narrow|broad" % ptype))
        gsize = cfg.get("peaks.macs_gsize", "")
        if gsize and "<REQUIRED" not in gsize and not gsize.isdigit():
            fails.append(fail("config", "peaks.macs_gsize %r is not an integer" % gsize))

    wl.check_samplesheet(paths["samplesheet"], SAMPLESHEET_HEADER, fails)
    if paths["samplesheet"].is_file():
        for i, line in enumerate(
                paths["samplesheet"].read_text(encoding="utf-8").splitlines()[1:], start=2):
            row = line.split(",")
            if len(row) > 3 and row[3] and not row[3].isdigit():
                fails.append(fail("samplesheet",
                                  "row %d: replicate %r is not an integer" % (i, row[3])))
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
                   "wrapper": "nfcore-atacseq-wrapper"}, fh, indent=2, sort_keys=True)
    result["wrote"] = str((preflight / "check_result.json").relative_to(project))
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


def build_params(cfg, paths):
    """The audited translation of _config/<assay>.yaml into pipeline parameters.

    Every key the pipeline receives is listed here — the agent never composes one.
    """
    aligner = cfg.get("aligner", "bwa")
    params = [
        ("input", str(paths["samplesheet"].resolve())),
        ("outdir", str((paths["substage"] / "run" / "results").resolve())),
        ("fasta", cfg["reference.fasta"]),
        ("gtf", cfg["reference.gtf"]),
        ("mito_name", cfg["reference.mito_name"]),
        ("aligner", aligner),
        ("macs_gsize", cfg["peaks.macs_gsize"]),
    ]
    if cfg["peaks.type"] == "narrow":
        params.append(("narrow_peak", "true"))
    if cfg.get("reference.blacklist"):
        params.append(("blacklist", cfg["reference.blacklist"]))
    derived = cfg.get("reference.derived_dir")
    if derived:
        index_dir = Path(derived) / aligner
        if index_dir.is_dir() and any(index_dir.iterdir()):
            params.append((INDEX_PARAM[aligner], str(index_dir)))
        else:
            # First run for this pipeline version: build and publish the indices so collect
            # can harvest them into the cache (mirrors the rnaseq cache discipline, 0009).
            params.append(("save_reference", "true"))
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
    # The venue decides the container story: this cluster's descriptor says apptainer,
    # AWS Batch supplies each process's container itself and wants no -profile at all.
    profile = wl.ex.nextflow_profile(project)
    profile_line = '    -profile %s \\\n' % profile if profile else ""
    body = """nextflow run "{checkout}" \\
{profile_line}    -c "{executor_config}" \\
    -params-file "{substage}/params.yaml" \\
    -work-dir "{work_dir}" \\
    $RESUME""".format(checkout=paths["checkout"], profile_line=profile_line,
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
    aligner = cfg.get("aligner", "bwa")
    ptype = cfg.get("peaks.type", "narrow")
    peak_dirname = "%s_peak" % ptype
    peak_suffix = ".narrowPeak" if ptype == "narrow" else ".broadPeak"
    results = substage / "run" / "results"
    ml = results / aligner / "merged_library"
    samples = wl.samplesheet_samples(paths["samplesheet"])
    fails = []

    peaks_dir = ml / "macs2" / peak_dirname
    peak_files = sorted(peaks_dir.glob("*" + peak_suffix)) if peaks_dir.is_dir() else []
    if not peak_files:
        fails.append(fail("peaks", "no *%s under %s" % (peak_suffix, peaks_dir)))

    consensus_dir = peaks_dir / "consensus"
    consensus_bed = sorted(consensus_dir.glob("*.bed")) if consensus_dir.is_dir() else []
    if not consensus_bed:
        fails.append(fail("peaks_consensus", "no consensus *.bed under %s" % consensus_dir))
    counts = sorted(consensus_dir.glob("*.featureCounts.txt")) if consensus_dir.is_dir() else []
    if not counts:
        fails.append(fail("counts_peaks", "no *.featureCounts.txt under %s" % consensus_dir))
    else:
        # Content, not existence: every GROUP_REPn must appear in the count-matrix header
        # (0035: the sample column is the group, so checking bare groups would let a lost
        # replicate hide behind its group's surviving one).
        header = ""
        for line in counts[0].read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("#"):
                header = line
                break
        expected = wl.samplesheet_group_rep_tokens(paths["samplesheet"])
        missing = [t for t in expected if t not in header]
        if missing:
            fails.append(fail("counts_peaks",
                              "%s lacks column(s) for: %s -- a replicate lost to a "
                              "failed process disappears here and nowhere downstream"
                              % (counts[0].name, ", ".join(missing))))

    bigwig_dir = ml / "bigwig"
    bigwigs = sorted(bigwig_dir.glob("*.bigWig")) if bigwig_dir.is_dir() else []
    if not bigwigs:
        fails.append(fail("bigwig", "no *.bigWig under %s" % bigwig_dir))

    bams = sorted(ml.glob("*.sorted.bam")) if ml.is_dir() else []
    if not bams:
        fails.append(fail("bam_genome", "no merged-library *.sorted.bam under %s" % ml))

    multiqc = results / "multiqc" / peak_dirname / "multiqc_report.html"
    if not multiqc.is_file() or multiqc.stat().st_size == 0:
        fails.append(fail("qc_multiqc", "missing or empty %s" % multiqc))

    if fails:
        result["failures"] = fails
        return emit(result, EXIT_FAILURE)

    rel = lambda p: str(p.relative_to(substage))  # noqa: E731
    outputs = [("peaks", rel(peaks_dir)), ("peaks_consensus", rel(consensus_bed[0])),
               ("counts_peaks", rel(counts[0])), ("bigwig", rel(bigwig_dir)),
               ("bam_genome", rel(ml)), ("qc_multiqc", rel(multiqc))]
    with ws.atomic_open(substage / "OUTPUTS.tsv") as fh:
        fh.write("# type\trole\tpath\n")
        for typ, path in outputs:
            fh.write("%s\tnative\t%s\n" % (typ, path))

    action = wl.harvest_cache(cfg.get("reference.derived_dir"), aligner,
                              results / "genome" / "index" / aligner,
                              ["pipeline: nf-core/atacseq %s" % PIPELINE_VERSION,
                               "fasta: %s" % cfg.get("reference.fasta"),
                               "gtf: %s" % cfg.get("reference.gtf"),
                               "built_by_substage: %s" % SUBSTAGE])
    result["derived_cache"] = {"configured": bool(cfg.get("reference.derived_dir")),
                               "action": action}

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
        "Pipeline: nf-core/atacseq %s (local checkout), aligner %s, %s peaks"
        % (PIPELINE_VERSION, aligner, ptype),
        "Samples: %d (%s)" % (len(samples), ", ".join(samples)),
        "Derived cache: %s" % action,
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
