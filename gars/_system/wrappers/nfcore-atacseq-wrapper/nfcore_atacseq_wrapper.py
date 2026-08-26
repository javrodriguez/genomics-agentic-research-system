#!/usr/bin/env python3
"""GARS-authored wrapper for nf-core/atacseq 2.1.2 — wrapper #1 of the assay expansion.

This is not a copy of the ClawBio wrapper architecture; it is the same *behavioral contract*
in the `_system/` idiom (decision 0028): one stdlib file, JSON on stdout, exit codes
0 ok / 1 failure / 2 refused / 3 usage, deterministic artifacts written by code. What carries
over from 02.01's hard-won lessons is behavior, not module layout:

- preflight before submission, writing `preflight/check_result.json` to its own directory;
- the pipeline is always the pinned LOCAL checkout ($GARS_PIPELINES), never a remote
  `nf-core/atacseq` — remote resolution goes through the GitHub REST API, rate-capped at 60
  requests/hour across this cluster's shared outbound IP;
- `--profile apptainer`, `-work-dir` on scratch, the executor config with no `params` block;
- `submit.sh` is GENERATED HERE, not written by the agent — deterministic artifacts are
  code's job (decision 0011). It carries the requeue guard: this cluster has `Requeue=1`, and
  a preempted job re-runs the script, which then adds `-resume`. Unlike the ClawBio wrapper's
  manifest-gated replay, plain Nextflow `-resume` genuinely continues a crashed or preempted
  run from its work directory — that limitation was ClawBio's, and does not carry over;
- the exit gate checks CONTENT, not existence: every sample must appear in the consensus
  count matrix header, because a file-exists gate once passed a DE table whose gene column
  had been silently dropped (decision 0010).

Subcommands, in run order (the sub-stage contract orchestrates; this computes):

  check    preflight. Validates config, samplesheet, pipeline checkout, executor config and
           output directory. Writes preflight/check_result.json. Exit 1 lists every failure.
  prepare  re-validates, then writes params.yaml, submit.sh and the reproducibility bundle
           (commands.sh, manifest.json). Deterministic: same inputs, same bytes.
  collect  the exit gate, after the Slurm job finishes. Verifies the declared outputs against
           the samplesheet, writes OUTPUTS.tsv and STATUS, harvests the derived-reference
           cache if configured and absent, and returns the history entry to append verbatim.

Runs on stock python 3.6.8, stdlib only. Nextflow/java are needed only inside submit.sh.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# .../<workspace>/_system/wrappers/nfcore-atacseq-wrapper/<this file>
# parents: [0]=the wrapper dir, [1]=wrappers, [2]=_system, [3]=the workspace root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import workspace as ws          # noqa: E402

WORKSPACE = Path(__file__).resolve().parents[3]

ASSAY = "atacseq_bulk"
SUBSTAGE = "01_nfcore-atacseq-wrapper"
PIPELINE_KEY = ws.PIPELINES[ASSAY]                      # nf-core-atacseq-2.1.2
PIPELINE_VERSION = PIPELINE_KEY.rsplit("-", 1)[1]       # 2.1.2
CHECKOUT_NAME = PIPELINE_KEY.replace("nf-core-", "")    # atacseq-2.1.2

ALIGNERS = ("bwa", "bowtie2", "chromap", "star")
INDEX_PARAM = {"bwa": "bwa_index", "bowtie2": "bowtie2_index",
               "chromap": "chromap_index", "star": "star_index"}
PEAK_TYPES = ("narrow", "broad")
SAMPLESHEET_HEADER = ["sample", "fastq_1", "fastq_2", "replicate"]

EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2, 3


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


def fail(check, detail):
    return {"check": check, "detail": detail}


# --- config ------------------------------------------------------------------------------------

def read_config(path):
    """The seeded two-level config, as a flat dict ('reference.fasta', 'aligner', ...).

    A narrow parser for a template we own, not arbitrary YAML — the same trade stage 01 makes
    (decision 0011): stdlib-only means no YAML library, and the template's shape is fixed.
    """
    values, section = {}, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        # Inline comments: the template writes `aligner: bwa   # bwa | bowtie2 | ...`. No
        # template value contains a bare ` #`, so splitting there is safe -- and <REQUIRED: ...>
        # markers survive because they carry no comment.
        raw = re.split(r"\s+#", raw, 1)[0]
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$", raw)
        if m:  # top level
            key, val = m.group(1), m.group(2)
            if val:
                values[key] = val.strip('"').strip("'")
                section = None
            else:
                section = key
            continue
        m = re.match(r"^  ([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$", raw)
        if m and section:
            values["%s.%s" % (section, m.group(1))] = m.group(2).strip('"').strip("'")
    return values


def sha256(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- the checks (shared by check and prepare) --------------------------------------------------

def run_checks(project):
    """Everything that must be true before a job may be submitted."""
    fails = []
    substage = project / "02_bioinformatics" / ASSAY / SUBSTAGE
    cfg_path = project / "_config" / ("%s.yaml" % ASSAY)
    sheet_path = project / "01_samplesheets" / ("%s_samplesheet.csv" % ASSAY)
    exec_cfg = project / "_config" / "nextflow.slurm.config"

    cfg = {}
    if not cfg_path.is_file():
        fails.append(fail("preconditions", "no config at _config/%s.yaml" % ASSAY))
    else:
        cfg = read_config(cfg_path)
        unfilled = sorted(k for k, v in cfg.items() if "<REQUIRED" in v)
        if unfilled:
            fails.append(fail("config_unfilled",
                              "still marked <REQUIRED>: %s -- complete them from the stage 02 "
                              "menus" % ", ".join(unfilled)))
        for key in ("reference.fasta", "reference.gtf", "reference.mito_name",
                    "peaks.type", "peaks.macs_gsize", "compute.partition", "compute.time",
                    "compute.cpus", "compute.mem", "compute.work_dir"):
            if key not in cfg:
                fails.append(fail("config", "missing key %s" % key))
        if cfg.get("reference.genome"):
            fails.append(fail("config", "reference.genome is not supported here: the iGenomes "
                                        "GRCh38 route has no biotype attribute and a menu-chosen "
                                        "fasta+gtf pair is the verified path. Remove the key."))
        for key in ("reference.fasta", "reference.gtf"):
            v = cfg.get(key)
            if v and "<REQUIRED" not in v and not os.access(v, os.R_OK):
                fails.append(fail("config", "%s is not readable: %s" % (key, v)))
        blacklist = cfg.get("reference.blacklist")
        if blacklist and not os.access(blacklist, os.R_OK):
            fails.append(fail("config", "reference.blacklist is not readable: %s" % blacklist))
        aligner = cfg.get("aligner", "bwa")
        if aligner not in ALIGNERS:
            fails.append(fail("config", "aligner %r is not one of %s" % (aligner, "|".join(ALIGNERS))))
        ptype = cfg.get("peaks.type", "")
        if ptype and "<REQUIRED" not in ptype and ptype not in PEAK_TYPES:
            fails.append(fail("config", "peaks.type %r is not narrow|broad" % ptype))
        gsize = cfg.get("peaks.macs_gsize", "")
        if gsize and "<REQUIRED" not in gsize and not gsize.isdigit():
            fails.append(fail("config", "peaks.macs_gsize %r is not an integer" % gsize))
        work_dir = cfg.get("compute.work_dir", "")
        if work_dir and not os.path.isabs(work_dir):
            fails.append(fail("config", "compute.work_dir must be an absolute scratch path, "
                                        "got %r" % work_dir))

    if not sheet_path.is_file():
        fails.append(fail("preconditions",
                          "no samplesheet at 01_samplesheets/%s_samplesheet.csv -- run stage 01"
                          % ASSAY))
    else:
        lines = sheet_path.read_text(encoding="utf-8").splitlines()
        header = lines[0].split(",") if lines else []
        if header != SAMPLESHEET_HEADER:
            fails.append(fail("samplesheet", "header is %s, expected %s -- stage 01 owns this "
                                             "file; re-run it rather than editing"
                              % (",".join(header), ",".join(SAMPLESHEET_HEADER))))
        else:
            for i, line in enumerate(lines[1:], start=2):
                row = line.split(",")
                for col in (1, 2):
                    if len(row) > col and row[col] and not os.path.isfile(row[col]):
                        fails.append(fail("samplesheet",
                                          "row %d: %s does not resolve -- the project may have "
                                          "moved; re-run stage 01" % (i, row[col])))
                if len(row) > 3 and not row[3].isdigit():
                    fails.append(fail("samplesheet",
                                      "row %d: replicate %r is not an integer" % (i, row[3])))

    # $GARS_PIPELINES is gars-env.sh's export; the fallback matches its default so `check`
    # works from a bare shell too.
    checkout = Path(os.environ["GARS_PIPELINES"]) / CHECKOUT_NAME \
        if os.environ.get("GARS_PIPELINES") else \
        Path.home() / "install" / "nf-core-pipelines" / CHECKOUT_NAME
    if not checkout.is_dir():
        fails.append(fail("pipeline", "no pinned checkout at %s -- clone nf-core/atacseq over "
                                      "the git protocol and check out tag %s"
                          % (checkout, PIPELINE_VERSION)))
    else:
        try:
            described = subprocess.run(["git", "-C", str(checkout), "describe", "--tags"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tag = described.stdout.decode().strip()
            if described.returncode != 0 or tag != PIPELINE_VERSION:
                fails.append(fail("pipeline", "checkout at %s describes as %r, expected %s -- "
                                              "verify the tag before trusting it"
                                  % (checkout, tag or "unknown", PIPELINE_VERSION)))
        except OSError as exc:
            fails.append(fail("pipeline", "cannot verify checkout tag: %s" % exc))

    if not exec_cfg.is_file():
        fails.append(fail("preconditions", "no _config/nextflow.slurm.config -- stage 00 seeds it"))
    elif re.search(r"^\s*params\s*[{.]", exec_cfg.read_text(encoding="utf-8"), re.M):
        fails.append(fail("executor_config",
                          "nextflow.slurm.config contains a params block; executor and process "
                          "settings are the permitted use -- pipeline parameters go through "
                          "params.yaml so the audited surface cannot be bypassed"))

    run_dir = substage / "run"
    if run_dir.is_dir() and any(run_dir.iterdir()) \
            and not (run_dir / ".gars_run_complete").is_file():
        fails.append(fail("output_dir",
                          "run/ is populated but carries no completion marker: a previous run "
                          "crashed or is still running. Nothing is deleted automatically -- "
                          "check STATUS and Slurm before moving it aside."))

    return fails, cfg, {"substage": substage, "config": cfg_path, "samplesheet": sheet_path,
                        "executor_config": exec_cfg, "checkout": checkout}


def samplesheet_samples(sheet_path):
    lines = sheet_path.read_text(encoding="utf-8").splitlines()
    return sorted({l.split(",")[0] for l in lines[1:] if l.strip()})


# --- check -------------------------------------------------------------------------------------

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
        json.dump({"ok": result["ok"], "failures": fails, "pipeline": PIPELINE_KEY,
                   "wrapper": "nfcore-atacseq-wrapper"}, fh, indent=2, sort_keys=True)
    result["wrote"] = str((preflight / "check_result.json").relative_to(project))
    return emit(result, EXIT_OK if result["ok"] else EXIT_FAILURE)


# --- prepare -----------------------------------------------------------------------------------

def build_params(cfg, paths, project):
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
            # can harvest them into the cache (mirrors 02.01 step 14).
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
    wrote = []

    params = build_params(cfg, paths, project)
    with ws.atomic_open(substage / "params.yaml") as fh:
        fh.write("# Generated by nfcore-atacseq-wrapper prepare. Do not hand-edit: the audited\n"
                 "# parameter surface is _config/%s.yaml; change that and re-run prepare.\n"
                 % ASSAY)
        for key, value in params:
            fh.write("%s: %s\n" % (key, json.dumps(value) if " " in str(value) else value))
    wrote.append("params.yaml")

    work_dir = "%s/%s-%s" % (cfg["compute.work_dir"].rstrip("/"), project.resolve().name, ASSAY)
    submit = """#!/bin/bash
#SBATCH --job-name={project}-{assay}
#SBATCH --partition={partition}
#SBATCH --time={time}
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={mem}
#SBATCH --output={substage}/logs/slurm-%j.out
#SBATCH --error={substage}/logs/slurm-%j.err
# Generated by nfcore-atacseq-wrapper prepare. Regenerate with prepare; do not hand-edit.
# Slurm snapshots this script at submission: editing it never affects a queued job.
set -euo pipefail

WS="{workspace}"
source "$WS/_system/gars-env.sh"

cd "{substage}"
mkdir -p run
cd run

# Requeue guard: this cluster has Requeue=1, so a preempted job re-runs this script.
# - completion marker present -> nothing to do; exit cleanly instead of re-running the pipeline.
# - a Nextflow session exists  -> a previous attempt crashed or was preempted; native -resume
#   continues it from the work directory. (The ClawBio wrapper's manifest-gated resume could
#   not do this; plain Nextflow can, which is one reason this wrapper runs it directly.)
if [ -f .gars_run_complete ]; then
    echo "[guard] run already complete ($(cat .gars_run_complete)); nothing to do"
    exit 0
fi
RESUME=""
if [ -d .nextflow ]; then
    RESUME="-resume"
    echo "[guard] previous Nextflow session found; resuming"
fi

nextflow run "{checkout}" \\
    -profile apptainer \\
    -c "{executor_config}" \\
    -params-file "{substage}/params.yaml" \\
    -work-dir "{work_dir}" \\
    $RESUME

date -Is > .gars_run_complete
echo "[wrapper] pipeline complete"
""".format(project=project.resolve().name, assay=ASSAY,
           partition=cfg["compute.partition"], time=cfg["compute.time"],
           cpus=cfg["compute.cpus"], mem=cfg["compute.mem"],
           substage=str(substage.resolve()), workspace=str(WORKSPACE),
           checkout=str(paths["checkout"]),
           executor_config=str(paths["executor_config"].resolve()),
           work_dir=work_dir)
    with ws.atomic_open(substage / "submit.sh") as fh:
        fh.write(submit)
    os.chmod(str(substage / "submit.sh"), 0o755)
    wrote.append("submit.sh")

    repro = substage / "reproducibility"
    repro.mkdir(exist_ok=True)
    try:
        commit = subprocess.run(["git", "-C", str(paths["checkout"]), "rev-parse", "HEAD"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE
                                ).stdout.decode().strip()
    except OSError:
        commit = "unknown"
    with ws.atomic_open(repro / "manifest.json") as fh:
        json.dump({"pipeline": "nf-core/atacseq", "version": PIPELINE_VERSION,
                   "pipeline_commit": commit, "checkout": str(paths["checkout"]),
                   "samplesheet_sha256": sha256(paths["samplesheet"]),
                   "config_sha256": sha256(paths["config"]),
                   "params": dict(build_params(cfg, paths, project)),
                   "template_version": ws.template_version(WORKSPACE),
                   "wrapper": "nfcore-atacseq-wrapper"},
                  fh, indent=2, sort_keys=True)
    with ws.atomic_open(repro / "commands.sh") as fh:
        fh.write("# The exact submission this sub-stage makes:\n"
                 "sbatch %s/submit.sh\n" % substage.resolve())
    wrote += ["reproducibility/manifest.json", "reproducibility/commands.sh"]

    result.update({"ok": True, "wrote": wrote, "params": dict(params),
                   "submit": str((substage / "submit.sh").resolve()),
                   "samples": samplesheet_samples(paths["samplesheet"])})
    return emit(result, EXIT_OK)


# --- collect -----------------------------------------------------------------------------------

def cmd_collect(args):
    project = Path(args.project)
    result = {"command": "collect", "ok": False, "assay": ASSAY, "failures": []}
    if not project.is_dir():
        result["error"] = "no such project: %s" % project
        return emit(result, EXIT_USAGE)
    substage = project / "02_bioinformatics" / ASSAY / SUBSTAGE
    cfg_path = project / "_config" / ("%s.yaml" % ASSAY)
    sheet = project / "01_samplesheets" / ("%s_samplesheet.csv" % ASSAY)
    if not (substage / "run" / ".gars_run_complete").is_file():
        result["error"] = ("run/.gars_run_complete is absent: the pipeline has not finished "
                           "(or crashed before the marker). Check Slurm and the logs; collect "
                           "gates on completion, it does not wait for it.")
        return emit(result, EXIT_REFUSED)

    cfg = read_config(cfg_path)
    aligner = cfg.get("aligner", "bwa")
    ptype = cfg.get("peaks.type", "narrow")
    peak_dirname = "%s_peak" % ptype
    peak_suffix = ".narrowPeak" if ptype == "narrow" else ".broadPeak"
    results = substage / "run" / "results"
    ml = results / aligner / "merged_library"
    samples = samplesheet_samples(sheet)
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
        # Content, not existence: every sample must appear in the count-matrix header.
        header = ""
        for line in counts[0].read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("#"):
                header = line
                break
        missing = [s for s in samples if s not in header]
        if missing:
            fails.append(fail("counts_peaks",
                              "%s lacks column(s) for sample(s): %s -- a sample lost to a "
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

    cache = {"configured": bool(cfg.get("reference.derived_dir")), "action": "none"}
    derived = cfg.get("reference.derived_dir")
    if derived:
        target = Path(derived) / aligner
        built = results / "genome" / "index" / aligner
        if target.is_dir() and any(target.iterdir()):
            cache["action"] = "reused"
        elif built.is_dir() and any(built.iterdir()):
            # Atomic publish: the cache is shared across projects and two runs may finish at
            # once. Temp sibling on the same filesystem, then rename into place (decision 0009).
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = tempfile.mkdtemp(prefix=".%s-incoming-" % aligner, dir=str(target.parent))
            shutil.copytree(str(built), os.path.join(tmp, aligner))
            try:
                os.rename(os.path.join(tmp, aligner), str(target))
                cache["action"] = "populated"
                with ws.atomic_open(target.parent / "PROVENANCE") as fh:
                    fh.write("pipeline: nf-core/atacseq %s\nfasta: %s\ngtf: %s\n"
                             "built_by_substage: %s\n"
                             % (PIPELINE_VERSION, cfg.get("reference.fasta"),
                                cfg.get("reference.gtf"), SUBSTAGE))
            except OSError:
                cache["action"] = "reused"      # another run won the race; theirs is fine
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    result["derived_cache"] = cache

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
        "Derived cache: %s" % cache["action"],
        "Outputs: " + ", ".join("`%s`" % t for t, _ in outputs),
    ])
    result.update({"ok": True, "outputs": [{"type": t, "path": p} for t, p in outputs],
                   "samples": samples, "template_version": version, "model": model,
                   "history_entry": entry})
    return emit(result, EXIT_OK)


# --- main --------------------------------------------------------------------------------------

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
