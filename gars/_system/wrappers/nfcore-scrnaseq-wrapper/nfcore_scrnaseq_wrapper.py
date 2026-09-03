#!/usr/bin/env python3
"""GARS-authored wrapper for nf-core/scrnaseq 4.2.0 — the single-cell assay.

Scaffolded by `_system/authoring/create_bioinformatics_skill.py` and completed by hand where
judgment is genuine (decision 0040). The behavioural contract is decision 0028: one file, JSON
on stdout, exit codes 0 ok / 1 failure / 2 refused / 3 usage, deterministic artifacts written
by code. Shared machinery is `_system/wrapperlib.py`; what is scrnaseq-specific here is the
parameter translation, the protocol/aligner compatibility gate, and the exit gate.

Every column, parameter and output path below was read from the pinned checkout —
`assets/schema_input.json`, `assets/protocols.json`, `nextflow_schema.json` and
`conf/modules.config` — never remembered (the 0031 discipline). Two facts that memory would
have got wrong:

  * scrnaseq's samplesheet `sample` column carries `meta: ["id"]` — it IS the sample id, not
    the group. That is the opposite of atacseq/chipseq (decision 0035), where `sample` is the
    group and rows repeat per replicate. Emitting group here would silently merge replicates.
  * `protocol: auto` is valid ONLY for the cellranger aligners. The pipeline's own defaults
    (`simpleaf` + `auto`) are therefore an invalid pair, and an unknown protocol is passed to
    the aligner *verbatim* rather than rejected — so the mistake produces a confidently wrong
    run, not an error. `check` refuses the pair, reading the matrix from the checkout itself.

Subcommands, in run order (the sub-stage contract orchestrates; this computes):

  check    preflight. Config, samplesheet, protocol/aligner compatibility, pinned checkout,
           executor config, output directory. Writes preflight/check_result.json.
  prepare  re-validates, then writes params.yaml, submit.sh and the reproducibility bundle.
  collect  the exit gate: every sample must have its own converted matrix, and the combined
           matrix and MultiQC report must be real. Writes OUTPUTS.tsv and STATUS.

Runs on stock python 3.6.8, stdlib only. Nextflow/java are needed only inside submit.sh.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

# .../<workspace>/_system/wrappers/nfcore-scrnaseq-wrapper/<this file>
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import workspace as ws          # noqa: E402
import wrapperlib as wl         # noqa: E402
from wrapperlib import (EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE,   # noqa: E402
                        emit, fail)

WORKSPACE = Path(__file__).resolve().parents[3]

ASSAY = "scrnaseq"
SUBSTAGE = "01_nfcore-scrnaseq-wrapper"
PIPELINE_VERSION = ws.PIPELINES[ASSAY].rsplit("-", 1)[1]

# The three aligners GARS offers. nf-core/scrnaseq also supports `cellranger`,
# `cellrangerarc` and `cellrangermulti`; all three require the proprietary Cell Ranger
# binary, which cannot be distributed in a container and needs a per-site licence
# acceptance. They are deliberately out of the menu rather than silently failing at run time
# — a fourth option that cannot run on the cluster is worse than three that can.
ALIGNERS = ("simpleaf", "star", "kallisto")

# Per-aligner index parameter, for reusing a derived index out of the cache (0009).
INDEX_PARAM = {"simpleaf": "simpleaf_index", "star": "star_index",
               "kallisto": "kallisto_index"}

# The one matrix this sub-stage publishes. nf-core writes both a filtered and a raw combined
# matrix; `filtered` is the analysis-ready object (empty droplets removed) and is what a
# consumer of the `h5ad` artifact type means. The raw matrix is deliberately NOT registered --
# two `native` rows of one type would leave a consumer unable to tell which is which
# (artifact_types.md), and the two differ by ~90x in barcode count.
COMBINED_MATRIX = "combined_filtered_matrix.h5ad"

# `sample` is the sample id here (meta: ["id"]), not a group. `expected_cells` is optional in
# the pipeline's schema and stage 01 does not emit it; adding it is a stage-01 change.
SAMPLESHEET_HEADER = ["sample", "fastq_1", "fastq_2"]

REQUIRED_KEYS = ("reference.fasta", "reference.gtf", "protocol", "aligner",
                 "compute.partition", "compute.time", "compute.cpus", "compute.mem",
                 "compute.work_dir")


def paths_for(project):
    return {"substage": project / "02_bioinformatics" / ASSAY / SUBSTAGE,
            "config": project / "_config" / ("%s.yaml" % ASSAY),
            "samplesheet": project / "01_samplesheets" / ("%s_samplesheet.csv" % ASSAY),
            # the descriptor names which nextflow config this venue pairs with (0039)
            "executor_config": wl.ex.nextflow_config_path(project)
            or project / "_config" / "nextflow.slurm.config"}


def supported_protocols(checkout, aligner):
    """The aligner's protocol set, read from the pinned checkout's own protocols.json.

    Deliberately not a hardcoded table: the matrix belongs to the pipeline, so reading it from
    the checkout means the wrapper cannot disagree with the version it is pinned to. Returns
    None when the file is unreadable, and the caller then skips the check rather than
    inventing a verdict.
    """
    if checkout is None:
        return None
    try:
        data = json.loads((Path(checkout) / "assets" / "protocols.json")
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entry = data.get(aligner)
    return sorted(entry.keys()) if isinstance(entry, dict) else None


def run_checks(project):
    """Everything that must be true before a job may be submitted."""
    fails = []
    paths = paths_for(project)
    cfg = {}
    checkout = wl.check_pipeline(ASSAY, fails)

    if not paths["config"].is_file():
        fails.append(fail("preconditions", "no config at _config/%s.yaml" % ASSAY))
    else:
        cfg = wl.read_config(paths["config"])
        wl.check_config_common(cfg, REQUIRED_KEYS, fails)

        aligner = cfg.get("aligner", "")
        if aligner and "<REQUIRED" not in aligner and aligner not in ALIGNERS:
            fails.append(fail("config",
                              "aligner %r is not one of %s. The cellranger aligners are "
                              "deliberately unsupported: they need the proprietary Cell "
                              "Ranger binary and a licence acceptance."
                              % (aligner, "|".join(ALIGNERS))))

        protocol = cfg.get("protocol", "")
        if (protocol and "<REQUIRED" not in protocol
                and aligner in ALIGNERS):
            allowed = supported_protocols(checkout, aligner)
            if allowed is not None and protocol not in allowed:
                # The important refusal. An unknown protocol is passed to the aligner
                # VERBATIM by the pipeline (docs/usage.md), so a wrong value here does not
                # error -- it produces a confident, wrong run. `auto` is the live trap: it is
                # the pipeline's own default and is valid only for the cellranger aligners.
                extra = ""
                if protocol == "auto":
                    extra = (" `auto` is only valid for the cellranger aligners, which GARS "
                             "does not offer; name the chemistry explicitly.")
                fails.append(fail("config",
                                  "protocol %r is not supported by aligner %r (supported: "
                                  "%s). nf-core/scrnaseq passes an unrecognised protocol to "
                                  "the aligner verbatim, so this would run and produce wrong "
                                  "results rather than fail.%s"
                                  % (protocol, aligner, "|".join(allowed), extra)))

    wl.check_samplesheet(paths["samplesheet"], SAMPLESHEET_HEADER, fails)
    if paths["samplesheet"].is_file():
        # A repeated sample id is CORRECT here: a sample sequenced across lanes gets one row
        # per lane and the pipeline concatenates them by meta.id. GARS models this directly --
        # files.csv is keyed (sample_id, lane) -- and stage 01 emits 3 rows for 2 samples when
        # one has two lanes, verified against a real two-lane fixture. nf-core's own test
        # samplesheet has exactly this shape (Sample_Y on L001 and L002).
        #
        # An earlier version of this check refused duplicate ids outright and would have
        # rejected every multi-lane run -- the common case for 10x. What is genuinely wrong is
        # the SAME FASTQ listed twice, which double-counts those reads into the same cell
        # barcodes with no error anywhere downstream.
        rows = [l.split(",") for l in
                paths["samplesheet"].read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
        pairs = [(r[0], r[1]) for r in rows if len(r) > 1]
        dupes = sorted({p for p in pairs if pairs.count(p) > 1})
        if dupes:
            fails.append(fail("samplesheet",
                              "the same FASTQ is listed twice for a sample: %s -- lanes are "
                              "expected to repeat a sample id, but a repeated read file "
                              "double-counts those reads into the same barcodes silently"
                              % ", ".join("%s -> %s" % (s, Path(f).name) for s, f in dupes)))

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
                   "wrapper": "nfcore-scrnaseq-wrapper"}, fh, indent=2, sort_keys=True)
    result["wrote"] = str((preflight / "check_result.json").relative_to(project))
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


def test_profile_params(cfg, keys):
    """The optional `pipeline:` section -- the pipeline's OWN test-profile switches, audited.

    A miniaturised input breaks steps a real library never trips: preseq cannot extrapolate a
    100k-read subsample, cellbender does not work on a tiny dataset. The pipelines' test
    profiles skip those steps; a user of small public fixtures needs the same switch, on the
    audited surface rather than a stray -c config (which check_executor_config refuses). Each
    key is named here, translated only when the yaml says `true`, and is never a scientific
    decision -- those stay in their own sections.
    """
    out = []
    for key in keys:
        if str(cfg.get("pipeline.%s" % key, "false")).strip().lower() == "true":
            out.append((key, "true"))
    return out


def build_params(cfg, paths):
    """The audited translation of _config/scrnaseq.yaml into pipeline parameters.

    Every key the pipeline receives is listed here — the agent never composes one.
    """
    aligner = cfg.get("aligner", "simpleaf")
    params = [
        ("input", str(paths["samplesheet"].resolve())),
        ("outdir", str((paths["substage"] / "run" / "results").resolve())),
        ("fasta", cfg["reference.fasta"]),
        ("gtf", cfg["reference.gtf"]),
        ("aligner", aligner),
        ("protocol", cfg["protocol"]),
        # iGenomes is an AWS-hosted default that would silently download; GARS always names
        # its own reference (0006).
        ("igenomes_ignore", "true"),
    ]
    derived = cfg.get("reference.derived_dir")
    if derived:
        index_dir = Path(derived) / aligner
        if index_dir.is_dir() and any(index_dir.iterdir()):
            params.append((INDEX_PARAM[aligner], str(index_dir)))
        else:
            # First run for this pipeline version: build and publish the index so collect can
            # harvest it into the cache (mirrors the atacseq/rnaseq discipline, 0009).
            params.append(("save_reference", "true"))
    params.extend(test_profile_params(cfg, ("skip_cellbender", "skip_qcatch")))
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
    aligner = cfg.get("aligner", "simpleaf")
    results = substage / "run" / "results"
    mtx = results / aligner / "mtx_conversions"
    samples = wl.samplesheet_samples(paths["samplesheet"])
    fails = []

    # --- the exit gate: content, not existence (decision 0010) -------------------------------
    # A .h5ad is HDF5 and this wrapper is stdlib-only, so its cell counts cannot be read from
    # here. The strongest check available without leaving the interpreter contract is the
    # per-sample SET: every sample in the samplesheet must have produced its own converted
    # matrix. A sample lost to a failed process disappears exactly here and nowhere
    # downstream -- the combined matrix would simply be built from fewer samples, silently.
    # Cell-level sanity belongs to the downstream analysis sub-stage, which runs under
    # gars-bio and can open the file.
    missing = []
    for sample in samples:
        per_sample = mtx / sample
        found = sorted(per_sample.glob("*.h5ad")) if per_sample.is_dir() else []
        if not found:
            missing.append(sample)
    if missing:
        fails.append(fail("h5ad",
                          "no converted matrix under %s for sample(s): %s -- a sample lost to "
                          "a failed process disappears here and nowhere downstream"
                          % (mtx, ", ".join(missing))))

    # The published matrix is named exactly, and there is NO fallback.
    #
    # This gate originally globbed `combined_*.h5ad` and took the first non-empty match. The
    # real pipeline writes TWO combined matrices -- combined_filtered_matrix.h5ad (1.3 MB in
    # the test run) and combined_raw_matrix.h5ad (114 MB, every empty droplet included). Under
    # the glob, a filtered matrix that failed to write meant the RAW one was published in its
    # place, under the same artifact type, with no error: a downstream analysis would have
    # silently received ~90x the barcodes, most of them ambient. Caught by running the real
    # pipeline and truncating the filtered matrix; the offline test missed it because a faked
    # tree had only one combined file.
    combined_file = mtx / COMBINED_MATRIX
    if not combined_file.is_file():
        fails.append(fail("h5ad",
                          "no %s under %s -- the raw matrix is never substituted for it, "
                          "because raw and filtered are different objects and a consumer "
                          "cannot tell them apart from the artifact type"
                          % (COMBINED_MATRIX, mtx)))
    elif combined_file.stat().st_size == 0:
        fails.append(fail("h5ad", "%s is zero bytes" % combined_file))

    multiqc = results / "multiqc" / "multiqc_report.html"
    if not multiqc.is_file() or multiqc.stat().st_size == 0:
        fails.append(fail("qc_multiqc", "missing or empty %s" % multiqc))

    if fails:
        result["failures"] = fails
        return emit(result, EXIT_FAILURE)

    rel = lambda p: str(p.relative_to(substage))  # noqa: E731
    outputs = [("h5ad", rel(combined_file)), ("qc_multiqc", rel(multiqc))]
    with ws.atomic_open(substage / "OUTPUTS.tsv") as fh:
        fh.write("# type\trole\tpath\n")
        for typ, path in outputs:
            fh.write("%s\tnative\t%s\n" % (typ, path))

    action = wl.harvest_cache(cfg.get("reference.derived_dir"), aligner,
                              results / "reference_genome" / "index" / aligner,
                              ["pipeline: nf-core/scrnaseq %s" % PIPELINE_VERSION,
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
        "Pipeline: nf-core/scrnaseq %s (local checkout), aligner %s, protocol %s"
        % (PIPELINE_VERSION, aligner, cfg.get("protocol")),
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
