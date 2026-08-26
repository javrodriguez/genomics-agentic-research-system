#!/usr/bin/env python3
"""GARS-authored wrapper for nf-core/chipseq 2.1.0 — wrapper #3 (decision 0031).

Same behavioral contract as the atacseq template (decision 0028), on `_system/wrapperlib.py`.
ChIP-specific facts, each read from the pinned checkout rather than remembered:

- peaks are called per IP against its declared control by **MACS3**, published under
  `<aligner>/merged_library/macs3/<peak_type>/`;
- the consensus set is **per antibody**: `.../consensus/<ANTIBODY>/` — the exit gate globs
  across antibody subdirectories;
- the samplesheet carries `antibody,control,control_replicate`; stage 01 derives
  `control_replicate` from the design (decision 0030), and rows with an antibody are the IPs;
- the pipeline has no `mito_name` parameter (unlike ATAC).

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

ASSAY = "chipseq_bulk"
SUBSTAGE = "01_nfcore-chipseq-wrapper"
PIPELINE_VERSION = ws.PIPELINES[ASSAY].rsplit("-", 1)[1]

ALIGNERS = ("bwa", "bowtie2", "chromap", "star")
INDEX_PARAM = {"bwa": "bwa_index", "bowtie2": "bowtie2_index",
               "chromap": "chromap_index", "star": "star_index"}
PEAK_TYPES = ("narrow", "broad")
SAMPLESHEET_HEADER = ["sample", "fastq_1", "fastq_2", "replicate", "antibody", "control",
                      "control_replicate"]

REQUIRED_KEYS = ("reference.fasta", "reference.gtf", "peaks.type", "peaks.macs_gsize",
                 "compute.partition", "compute.time", "compute.cpus", "compute.mem",
                 "compute.work_dir")


def paths_for(project):
    return {"substage": project / "02_bioinformatics" / ASSAY / SUBSTAGE,
            "config": project / "_config" / ("%s.yaml" % ASSAY),
            "samplesheet": project / "01_samplesheets" / ("%s_samplesheet.csv" % ASSAY),
            "executor_config": project / "_config" / "nextflow.slurm.config"}


def sheet_rows(sheet_path):
    lines = sheet_path.read_text(encoding="utf-8").splitlines()
    head = lines[0].split(",") if lines else []
    return [dict(zip(head, l.split(","))) for l in lines[1:] if l.strip()]


def run_checks(project):
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
        rows = sheet_rows(paths["samplesheet"])
        ips = [r for r in rows if r.get("antibody")]
        if rows and not ips:
            fails.append(fail("samplesheet",
                              "no row carries an antibody: every row is a control, so there "
                              "is nothing to call peaks on. Fill `antibody` (and `control`) "
                              "in samples.csv for the IP samples and re-run stage 01."))
        for r in ips:
            if not r.get("control"):
                fails.append(fail("samplesheet",
                                  "IP sample %s has an antibody but no control -- "
                                  "nf-core/chipseq calls peaks against the declared input. "
                                  "Fill `control` in samples.csv and re-run stage 01."
                                  % r.get("sample", "?")))
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
                   "wrapper": "nfcore-chipseq-wrapper"}, fh, indent=2, sort_keys=True)
    result["wrote"] = str((preflight / "check_result.json").relative_to(project))
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


def build_params(cfg, paths):
    """The audited translation of _config/<assay>.yaml into pipeline parameters."""
    aligner = cfg.get("aligner", "bwa")
    params = [
        ("input", str(paths["samplesheet"].resolve())),
        ("outdir", str((paths["substage"] / "run" / "results").resolve())),
        ("fasta", cfg["reference.fasta"]),
        ("gtf", cfg["reference.gtf"]),
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
    aligner = cfg.get("aligner", "bwa")
    ptype = cfg.get("peaks.type", "narrow")
    peak_dirname = "%s_peak" % ptype
    peak_suffix = ".narrowPeak" if ptype == "narrow" else ".broadPeak"
    results = substage / "run" / "results"
    ml = results / aligner / "merged_library"
    rows = sheet_rows(paths["samplesheet"])
    samples = sorted({r["sample"] for r in rows})
    ip_samples = sorted({r["sample"] for r in rows if r.get("antibody")})
    fails = []

    # nf-core/chipseq 2.1.0 calls peaks with MACS3 (its docs' output layout), not MACS2.
    peaks_dir = ml / "macs3" / peak_dirname
    peak_files = sorted(peaks_dir.glob("*" + peak_suffix)) if peaks_dir.is_dir() else []
    if not peak_files:
        fails.append(fail("peaks", "no *%s under %s" % (peak_suffix, peaks_dir)))

    # Consensus is per antibody: consensus/<ANTIBODY>/
    consensus_root = peaks_dir / "consensus"
    consensus_bed = sorted(consensus_root.glob("*/[!.]*.bed")) if consensus_root.is_dir() else []
    if not consensus_bed:
        fails.append(fail("peaks_consensus",
                          "no consensus */*.bed under %s" % consensus_root))
    counts = sorted(consensus_root.glob("*/*.featureCounts.txt")) \
        if consensus_root.is_dir() else []
    if not counts:
        fails.append(fail("counts_peaks", "no */*.featureCounts.txt under %s" % consensus_root))
    else:
        # Content, not existence: every IP sample must appear in some antibody's count matrix.
        headers = ""
        for c in counts:
            for line in c.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.startswith("#"):
                    headers += line + "\n"
                    break
        missing = [s for s in ip_samples if s not in headers]
        if missing:
            fails.append(fail("counts_peaks",
                              "no consensus count matrix carries IP sample(s): %s -- a sample "
                              "lost to a failed process disappears here and nowhere downstream"
                              % ", ".join(missing)))

    bigwig_dir = ml / "bigwig"
    if not (bigwig_dir.is_dir() and any(bigwig_dir.glob("*.bigWig"))):
        fails.append(fail("bigwig", "no *.bigWig under %s" % bigwig_dir))
    if not (ml.is_dir() and any(ml.glob("*.sorted.bam"))):
        fails.append(fail("bam_genome", "no merged-library *.sorted.bam under %s" % ml))
    multiqc = results / "multiqc" / peak_dirname / "multiqc_report.html"
    if not multiqc.is_file() or multiqc.stat().st_size == 0:
        fails.append(fail("qc_multiqc", "missing or empty %s" % multiqc))

    if fails:
        result["failures"] = fails
        return emit(result, EXIT_FAILURE)

    rel = lambda p: str(p.relative_to(substage))  # noqa: E731
    outputs = [("peaks", rel(peaks_dir)), ("peaks_consensus", rel(consensus_root)),
               ("counts_peaks", rel(counts[0])), ("bigwig", rel(bigwig_dir)),
               ("bam_genome", rel(ml)), ("qc_multiqc", rel(multiqc))]
    with ws.atomic_open(substage / "OUTPUTS.tsv") as fh:
        fh.write("# type\trole\tpath\n")
        for typ, path in outputs:
            fh.write("%s\tnative\t%s\n" % (typ, path))

    action = wl.harvest_cache(cfg.get("reference.derived_dir"), aligner,
                              results / "genome" / "index" / aligner,
                              ["pipeline: nf-core/chipseq %s" % PIPELINE_VERSION,
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
        "Pipeline: nf-core/chipseq %s (local checkout), aligner %s, %s peaks"
        % (PIPELINE_VERSION, aligner, ptype),
        "Samples: %d (%s), of which IPs: %d" % (len(samples), ", ".join(samples),
                                                len(ip_samples)),
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
