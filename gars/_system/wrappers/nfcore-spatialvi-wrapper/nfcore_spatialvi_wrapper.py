#!/usr/bin/env python3
"""GARS-authored wrapper for nf-core/spatialvi @ ccdfb48 — the spatial transcriptomics assay.

Scaffolded by `_system/authoring/create_bioinformatics_skill.py` and completed by hand where
judgment is genuine (decision 0040). The behavioural contract is decision 0028: one file, JSON
on stdout, exit codes 0 ok / 1 failure / 2 refused / 3 usage, deterministic artifacts written
by code.

Three things make this assay different from the six before it, all read from the pinned
checkout rather than remembered:

  * **The pin is a COMMIT, not a tag.** spatialvi's only tag is v0.1.0 (2023-03-31), which
    `git describe` places 1,014 commits behind `dev` — it predates Visium HD and most of the
    current pipeline. `wrapperlib.check_pipeline` verifies a commit pin with `rev-parse`.
  * **The input is a DIRECTORY per sample**, not FASTQ pairs: a Space Ranger output tree that
    someone else already produced. GARS registers those directories through the `sample_dir`
    input kind (`workspace.INPUT_KINDS`), so this assay's `files.csv` carries
    `sample_id, spaceranger_dir`.
  * **Space Ranger is not run here.** The raw mode needs 10x's proprietary binary, a licence
    acceptance, 64 GB and 8 threads, and supports human and mouse only — the same exclusion
    already made for the cellranger aligners in scrnaseq.

Subcommands, in run order (the sub-stage contract orchestrates; this computes):

  check    preflight. Config, samplesheet, every Space Ranger directory resolvable, pinned
           checkout commit, executor config, output directory.
  prepare  re-validates, then writes params.yaml, submit.sh and the reproducibility bundle.
  collect  the exit gate: every sample must have its own PROCESSED AnnData and report.

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

ASSAY = "spatialvi"
SUBSTAGE = "01_nfcore-spatialvi-wrapper"
PIPELINE_VERSION = ws.PIPELINES[ASSAY].rsplit("-", 1)[1]

SAMPLESHEET_HEADER = ["sample", "spaceranger_dir"]

# Visium HD bin sizes, from the pipeline's own nextflow_schema.json enum. A closed menu because
# the bin size defines what a "spot" IS -- every count, cluster and spatially variable gene
# downstream depends on it (decision 0020).
HD_BIN_SIZES = ("2", "8", "16")

REQUIRED_KEYS = ("hd_bin_size", "qc.min_counts", "qc.min_genes", "qc.min_spots",
                 "qc.mito_threshold", "cluster_resolution",
                 "compute.partition", "compute.time", "compute.cpus", "compute.mem",
                 "compute.work_dir")

# The per-sample file names, from docs/output.md at the pin. The PROCESSED AnnData is
# `<sample>.h5ad`; `<sample>-raw.h5ad` sits beside it and is a different object.
#
# A `*.h5ad` glob would match both, and the scrnaseq wrapper shipped exactly that mistake --
# there a truncated filtered matrix meant the raw one was published silently in its place. The
# names are therefore built explicitly here, and the raw file is never a fallback.
def processed_h5ad(results, sample):
    return results / sample / "data" / ("%s.h5ad" % sample)


def raw_h5ad(results, sample):
    return results / sample / "data" / ("%s-raw.h5ad" % sample)


def sample_report(results, sample):
    return results / sample / "reports" / ("report-%s.html" % sample)


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
    checkout = wl.check_pipeline(ASSAY, fails)

    if not paths["config"].is_file():
        fails.append(fail("preconditions", "no config at _config/%s.yaml" % ASSAY))
    else:
        cfg = wl.read_config(paths["config"])
        wl.check_config_common(cfg, REQUIRED_KEYS, fails)

        bin_size = str(cfg.get("hd_bin_size", "")).strip()
        if bin_size and "<REQUIRED" not in bin_size and bin_size not in HD_BIN_SIZES:
            fails.append(fail("config",
                              "hd_bin_size %r is not one of %s (Visium HD bin sizes, in "
                              "microns)" % (bin_size, "|".join(HD_BIN_SIZES))))

        for key in ("qc.min_counts", "qc.min_genes", "qc.min_spots"):
            val = str(cfg.get(key, "")).strip()
            if val and "<REQUIRED" not in val and not val.isdigit():
                fails.append(fail("config", "%s %r is not a non-negative integer"
                                  % (key, val)))
        for key in ("qc.mito_threshold", "cluster_resolution"):
            val = str(cfg.get(key, "")).strip()
            if val and "<REQUIRED" not in val:
                try:
                    float(val)
                except ValueError:
                    fails.append(fail("config", "%s %r is not a number" % (key, val)))

    # The samplesheet's second column is a DIRECTORY (or a tarball of one), so the usual
    # readable-file check does not apply. wrapperlib's check_samplesheet verifies paths in
    # columns 1 and 2 as files; here column 1 is the directory, so it is checked below instead.
    wl.check_samplesheet(paths["samplesheet"], SAMPLESHEET_HEADER, fails, path_columns=())
    if paths["samplesheet"].is_file():
        rows = [l.split(",") for l in
                paths["samplesheet"].read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
        seen = {}
        for i, row in enumerate(rows, start=2):
            if len(row) < 2 or not row[1]:
                fails.append(fail("samplesheet", "row %d: spaceranger_dir is blank" % i))
                continue
            sample, target = row[0], Path(row[1])
            if sample in seen:
                fails.append(fail("samplesheet",
                                  "sample %r appears on rows %d and %d -- spatial registers one "
                                  "Space Ranger directory per sample, and there are no lanes "
                                  "to repeat" % (sample, seen[sample], i)))
            else:
                seen[sample] = i
            if not target.exists():
                fails.append(fail("samplesheet",
                                  "row %d: %s does not exist" % (i, target)))
            elif target.is_dir() and not any(target.glob("*.h5")):
                # The pipeline reads the OUTS level directly: raw_feature_bc_matrix.h5 beside
                # spatial/. An earlier version of this check ACCEPTED a directory that merely
                # held outs/ -- and the run then died in SDATA_READ_VISIUM twenty-five minutes
                # of queue later, looking for the .h5 at the level it was given (tierb-spatial
                # run 26928674). Pointing one level too high is the easy mistake, so it is
                # refused here, with the exact directory to use.
                if (target / "outs").is_dir():
                    fails.append(fail("samplesheet",
                                      "row %d: %s holds an outs/ directory but no matrices at "
                                      "its own level -- the pipeline reads the outs level "
                                      "directly (raw_feature_bc_matrix.h5 beside spatial/). "
                                      "Point spaceranger_dir at %s/outs instead."
                                      % (i, target, target)))
                else:
                    fails.append(fail("samplesheet",
                                      "row %d: %s has no *.h5 and no outs/ -- point "
                                      "spaceranger_dir at a Space Ranger outs directory (or "
                                      "a .tar.gz of one)" % (i, target)))

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
                   "wrapper": "nfcore-spatialvi-wrapper"}, fh, indent=2, sort_keys=True)
    result["wrote"] = str((preflight / "check_result.json").relative_to(project))
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


def build_params(cfg, paths):
    """The audited translation of _config/spatialvi.yaml into pipeline parameters.

    No reference genome: in downstream mode alignment already happened inside Space Ranger,
    against whatever reference it was given. Naming one here would imply a control GARS does
    not have.
    """
    return [
        ("input", str(paths["samplesheet"].resolve())),
        ("outdir", str((paths["substage"] / "run" / "results").resolve())),
        ("hd_bin_size", cfg["hd_bin_size"]),
        ("qc_min_counts", cfg["qc.min_counts"]),
        ("qc_min_genes", cfg["qc.min_genes"]),
        ("qc_min_spots", cfg["qc.min_spots"]),
        ("qc_mito_threshold", cfg["qc.mito_threshold"]),
        ("cluster_resolution", cfg["cluster_resolution"]),
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
                           "(or crashed before the marker). collect gates on completion, it "
                           "does not wait for it.")
        return emit(result, EXIT_REFUSED)

    results = substage / "run" / "results"
    samples = wl.samplesheet_samples(paths["samplesheet"])
    fails = []

    # --- the exit gate: content, not existence (decision 0010) --------------------------------
    # Every sample must carry its own PROCESSED AnnData and its own report. A sample whose
    # analysis failed leaves the others looking complete, and nothing downstream would notice.
    # The processed file is named exactly; `<sample>-raw.h5ad` beside it is never accepted in
    # its place (the scrnaseq raw-for-filtered defect, avoided here by construction).
    missing_h5ad, missing_report, raw_only = [], [], []
    for sample in samples:
        proc = processed_h5ad(results, sample)
        if not proc.is_file() or proc.stat().st_size == 0:
            missing_h5ad.append(sample)
            if raw_h5ad(results, sample).is_file():
                raw_only.append(sample)
        rep = sample_report(results, sample)
        if not rep.is_file() or rep.stat().st_size == 0:
            missing_report.append(sample)

    if missing_h5ad:
        detail = ("no processed <sample>.h5ad under %s for: %s"
                  % (results, ", ".join(missing_h5ad)))
        if raw_only:
            detail += ("; %s HAS a -raw.h5ad, which is the pre-analysis object and is never "
                       "substituted for the processed one" % ", ".join(raw_only))
        fails.append(fail("h5ad", detail))
    if missing_report:
        fails.append(fail("report", "no per-sample report under %s for: %s"
                          % (results, ", ".join(missing_report))))

    multiqc = results / "multiqc" / "multiqc_report.html"
    if not multiqc.is_file() or multiqc.stat().st_size == 0:
        fails.append(fail("qc_multiqc", "missing or empty %s" % multiqc))

    if fails:
        result["failures"] = fails
        return emit(result, EXIT_FAILURE)

    rel = lambda p: str(p.relative_to(substage))  # noqa: E731
    # `h5ad` and `report` are directory-valued: spatial writes them per sample, under
    # <sample>/data/ and <sample>/reports/, so the SET is the artifact and a consumer globs
    # inside it (artifact_types.md permits this for inherently per-sample sets). The exact
    # per-sample paths are also returned below, so a reader never has to guess the pattern.
    outputs = [("h5ad", rel(results)), ("report", rel(results)),
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
    cfg = wl.read_config(paths["config"])
    entry = "\n".join([
        "## <ISO-8601 date> — 02_bioinformatics/%s/%s — pipeline complete" % (ASSAY, SUBSTAGE),
        "",
        "Template version: %s" % version,
        "Model: %s" % model,
        "Pipeline: nf-core/spatialvi %s (local checkout, COMMIT pin — this pipeline has no "
        "current release)" % PIPELINE_VERSION,
        "Mode: downstream (Space Ranger output consumed as given; not re-run)",
        "Filtering: min_counts %s, min_genes %s, mito %s%%"
        % (cfg.get("qc.min_counts"), cfg.get("qc.min_genes"), cfg.get("qc.mito_threshold")),
        "Samples: %d (%s)" % (len(samples), ", ".join(samples)),
        "Outputs: " + ", ".join("`%s`" % t for t, _ in outputs),
    ])
    result.update({"ok": True,
                   "outputs": [{"type": t, "path": p} for t, p in outputs],
                   "per_sample": [{"sample": s,
                                   "h5ad": rel(processed_h5ad(results, s)),
                                   "report": rel(sample_report(results, s))}
                                  for s in samples],
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
