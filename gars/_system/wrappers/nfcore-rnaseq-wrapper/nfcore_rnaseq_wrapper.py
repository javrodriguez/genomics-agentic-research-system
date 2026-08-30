#!/usr/bin/env python3
"""GARS-authored wrapper for nf-core/rnaseq 3.26.0 — the ClawBio path's replacement.

Wrapper #2 in the 0028 idiom (see `nfcore-atacseq-wrapper`, the template): one file on
`_system/wrapperlib.py`, JSON on stdout, exit codes 0/1/2/3, deterministic artifacts. This
retires the ClawBio `nfcore-rnaseq-wrapper` skill from the critical path (decision 0029) —
the deprecated procedure is preserved beside the sub-stage contract until a live run under
this wrapper passes the switchover criteria in DEVELOPMENT.md.

What this wrapper fixes relative to the ClawBio path, each a recorded defect or limitation:
- `submit.sh` is generated with the requeue guard baked in, never agent-written;
- crash recovery is Nextflow's native `-resume` (the manifest-gated replay could not
  continue a crashed run);
- the version check is `git describe --tags` against `workspace.PIPELINES`, with no
  `_MANIFEST_VERSION_RE` lookbehind bug to reason around;
- the derived-reference cache is read AND populated by code (`collect` harvests atomically),
  where the old contract had the agent copy directories by hand at step 14.

The cache layout matches the one already populated at
`<derived>/index/{star,salmon}` + `<derived>/genome.transcripts.fa`, so the existing
59 GB `nf-core-rnaseq-3.26.0` cache is consumed as-is.

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

ASSAY = "rnaseq_bulk"
SUBSTAGE = "01_nfcore-rnaseq-wrapper"
PIPELINE_VERSION = ws.PIPELINES[ASSAY].rsplit("-", 1)[1]

ALIGNERS = ("star_salmon", "star_rsem", "hisat2", "bowtie2_salmon")
SAMPLESHEET_HEADER = ["sample", "fastq_1", "fastq_2", "strandedness"]

REQUIRED_KEYS = ("reference.fasta", "reference.gtf", "compute.partition", "compute.time",
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
        aligner = cfg.get("aligner", "star_salmon")
        if aligner not in ALIGNERS:
            fails.append(fail("config", "aligner %r is not one of %s"
                              % (aligner, "|".join(ALIGNERS))))
        derived = cfg.get("reference.derived_dir")
        if derived and aligner == "star_salmon":
            star = Path(derived) / "index" / "star"
            if star.is_dir() and not (star / "genomeParameters.txt").is_file():
                # Never reuse a prebuilt aligner index blindly: STAR refuses an index built
                # by an incompatible version, and the parameters file is where the version
                # lives (decision 0009).
                fails.append(fail("config",
                                  "%s exists but has no genomeParameters.txt; the cache is "
                                  "damaged or half-built -- do not reuse it" % star))

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
                   "wrapper": "nfcore-rnaseq-wrapper (gars)"}, fh, indent=2, sort_keys=True)
    result["wrote"] = str((preflight / "check_result.json").relative_to(project))
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


def build_params(cfg, paths):
    """The audited translation of _config/<assay>.yaml into pipeline parameters."""
    aligner = cfg.get("aligner", "star_salmon")
    params = [
        ("input", str(paths["samplesheet"].resolve())),
        ("outdir", str((paths["substage"] / "run" / "results").resolve())),
        ("fasta", cfg["reference.fasta"]),
        ("gtf", cfg["reference.gtf"]),
        ("aligner", aligner),
    ]
    derived = cfg.get("reference.derived_dir")
    if derived and aligner == "star_salmon":
        d = Path(derived)
        star, salmon, tfa = d / "index" / "star", d / "index" / "salmon", \
            d / "genome.transcripts.fa"
        if star.is_dir() and salmon.is_dir() and tfa.is_file():
            params += [("star_index", str(star)), ("salmon_index", str(salmon)),
                       ("transcript_fasta", str(tfa))]
        else:
            # First run for this pipeline version: build and publish so collect harvests.
            params.append(("save_reference", "true"))
    elif derived:
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
    aligner = cfg.get("aligner", "star_salmon")
    results = substage / "run" / "results"
    adir = results / aligner
    samples = wl.samplesheet_samples(paths["samplesheet"])
    fails = []

    counts = adir / "salmon.merged.gene_counts_length_scaled.tsv"
    if not counts.is_file() or counts.stat().st_size == 0:
        fails.append(fail("counts_gene", "missing or empty %s" % counts))
    else:
        # Content, not existence: every sample must be a column of the merged matrix.
        header = counts.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        missing = [s for s in samples if s not in header]
        if missing:
            fails.append(fail("counts_gene",
                              "%s lacks column(s) for sample(s): %s -- a sample lost to a "
                              "failed process disappears here and nowhere downstream"
                              % (counts.name, ", ".join(missing))))

    tx_counts = adir / "salmon.merged.transcript_counts.tsv"
    if not tx_counts.is_file():
        fails.append(fail("counts_transcript", "missing %s" % tx_counts))
    tpm = adir / "salmon.merged.gene_tpm.tsv"
    if not tpm.is_file():
        fails.append(fail("tpm_gene", "missing %s" % tpm))
    bams = sorted(adir.glob("*.sorted.bam")) if adir.is_dir() else []
    if not bams:
        fails.append(fail("bam_genome", "no *.sorted.bam under %s" % adir))
    multiqc = results / "multiqc" / aligner / "multiqc_report.html"
    if not multiqc.is_file() or multiqc.stat().st_size == 0:
        fails.append(fail("qc_multiqc", "missing or empty %s" % multiqc))

    if fails:
        result["failures"] = fails
        return emit(result, EXIT_FAILURE)

    rel = lambda p: str(p.relative_to(substage))  # noqa: E731
    outputs = [("counts_gene", rel(counts)), ("counts_transcript", rel(tx_counts)),
               ("tpm_gene", rel(tpm)), ("bam_genome", rel(adir)),
               ("qc_multiqc", rel(multiqc))]
    with ws.atomic_open(substage / "OUTPUTS.tsv") as fh:
        fh.write("# type\trole\tpath\n")
        for typ, path in outputs:
            fh.write("%s\tnative\t%s\n" % (typ, path))

    # The whole published genome dir is the cache unit here (index/ + transcripts fasta +
    # filtered annotation), matching the layout the existing 59 GB cache already has.
    action = "none"
    derived = cfg.get("reference.derived_dir")
    if derived:
        d = Path(derived)
        if (d / "index").is_dir():
            action = "reused"
        else:
            built = results / "genome"
            action = wl.harvest_cache(
                str(d.parent), d.name, built,
                ["pipeline: nf-core/rnaseq %s" % PIPELINE_VERSION,
                 "fasta: %s" % cfg.get("reference.fasta"),
                 "gtf: %s" % cfg.get("reference.gtf"),
                 "built_by_substage: %s" % SUBSTAGE],
                provenance_in_target=True)
    result["derived_cache"] = {"configured": bool(derived), "action": action}

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
        "Pipeline: nf-core/rnaseq %s (local checkout, gars wrapper), aligner %s"
        % (PIPELINE_VERSION, aligner),
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
