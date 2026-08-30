#!/usr/bin/env python3
"""Shared machinery for the GARS-authored pipeline wrappers (decisions 0012, 0028).

A wrapper is one file under `_system/wrappers/<name>/`; what varies per assay is its params
builder, its exit-gate paths and its config template. Everything an assay does NOT get to vary
lives here, so wrappers #2..#4 are diffs of #1 rather than copies — and so a fix to the
requeue guard or the cache harvest lands in every wrapper at once.

Runs on stock python 3.6.8, stdlib only, like every `_system/` helper.
"""

import hashlib
import json
import pathlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import executorlib as ex        # noqa: E402
import workspace as ws          # noqa: E402

EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2, 3


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


def fail(check, detail):
    return {"check": check, "detail": detail}


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


def pipeline_checkout(assay):
    """The pinned local checkout for an assay's pipeline, from workspace.PIPELINES.

    Local, never remote: resolving a remote nf-core/<pipeline> goes through the GitHub REST
    API, rate-capped at 60 requests/hour across this cluster's shared outbound IP.
    """
    key = ws.PIPELINES[assay]
    name = key.replace("nf-core-", "")
    root = Path(os.environ["GARS_PIPELINES"]) if os.environ.get("GARS_PIPELINES") \
        else Path.home() / "install" / "nf-core-pipelines"
    return root / name, key.rsplit("-", 1)[1]


def is_commit_pin(version):
    """True when a pin names a commit rather than a release tag.

    Some pipelines have no usable release. nf-core/spatialvi's only tag, v0.1.0, is from
    2023-03-31 and sits 1,014 commits behind `dev` -- it predates Visium HD support and most
    of the current pipeline, so pinning it would be pinning the wrong science. The honest
    alternative is a commit, said out loud rather than dressed up as a version.

    A tag pin looks like `2.1.2` or `4.2.0`; a commit pin is a bare hex abbreviation.
    """
    return (7 <= len(version) <= 40
            and all(c in "0123456789abcdef" for c in version.lower()))


def check_pipeline(assay, fails):
    """The checkout exists and reports the pinned version — verified independently, never
    assumed (the 02.01 lesson: a version-override flag is only known to be misfiring after the
    checkout is verified some other way).

    A tag pin is verified with `git describe --tags`; a commit pin (see is_commit_pin) with
    `git rev-parse HEAD`, because `describe` on a detached commit returns a
    `<tag>-<n>-g<sha>` string that is a fact about the nearest ancestor tag, not about the pin.
    """
    checkout, version = pipeline_checkout(assay)
    commit_pin = is_commit_pin(version)
    if not checkout.is_dir():
        fails.append(fail("pipeline", "no pinned checkout at %s -- clone the pipeline over "
                                      "the git protocol and check out %s %s"
                          % (checkout, "commit" if commit_pin else "tag", version)))
        return checkout

    if commit_pin:
        try:
            rev = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            head = rev.stdout.decode().strip()
            if rev.returncode != 0 or not head.startswith(version):
                fails.append(fail("pipeline",
                                  "checkout at %s is at commit %r, expected %s -- this "
                                  "pipeline is pinned to a commit because it has no current "
                                  "release; verify it before trusting it"
                                  % (checkout, head or "unknown", version)))
        except OSError as exc:
            fails.append(fail("pipeline", "cannot verify checkout commit: %s" % exc))
        return checkout

    try:
        described = subprocess.run(["git", "-C", str(checkout), "describe", "--tags"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tag = described.stdout.decode().strip()
        if described.returncode != 0 or tag != version:
            fails.append(fail("pipeline", "checkout at %s describes as %r, expected %s -- "
                                          "verify the tag before trusting it"
                              % (checkout, tag or "unknown", version)))
    except OSError as exc:
        fails.append(fail("pipeline", "cannot verify checkout tag: %s" % exc))
    return checkout


def check_executor_config(exec_cfg, fails):
    """Both halves of "how does this run here": the scheduler descriptor (0039) and the
    Nextflow executor config it names.

    The descriptor decides WHICH nextflow config is demanded, so a site on another scheduler
    is not asked for a file named after Slurm. With no descriptor present the answer is
    `nextflow.slurm.config`, exactly as before the seam existed.
    """
    project = ex.config_root_for(Path(exec_cfg).parent)
    descriptor = ex.load(project)
    for problem in ex.validate(descriptor):
        fails.append(fail("executor_config", "_config/%s: %s" % (ex.DESCRIPTOR_NAME, problem)))
    wanted = descriptor.get("nextflow_config") or ""
    if not wanted:
        return                      # a backend that pairs with no nextflow config demands none
    path = Path(exec_cfg)
    if path.name != wanted:
        path = path.parent / wanted
    if not path.is_file():
        fails.append(fail("preconditions", "no _config/%s -- stage 00 seeds it" % wanted))
    elif re.search(r"^\s*params\s*[{.]", path.read_text(encoding="utf-8"), re.M):
        fails.append(fail("executor_config",
                          "%s contains a params block; executor and process "
                          "settings are the permitted use -- pipeline parameters go through "
                          "params.yaml so the audited surface cannot be bypassed" % wanted))


def check_run_dir(substage, fails, resume_refresh=False):
    run_dir = substage / "run"
    if run_dir.is_dir() and any(run_dir.iterdir()) \
            and not (run_dir / ".gars_run_complete").is_file():
        if resume_refresh:
            # Decision 0038: a deliberate params-change-then-resume. Allowed ONLY when the
            # previous run is terminally FAILED and Nextflow state exists for -resume to use.
            status = substage / "STATUS"
            failed = status.is_file() and \
                status.read_text(encoding="utf-8").lstrip().startswith("FAILED")
            if failed and (run_dir / ".nextflow").is_dir():
                return
            fails.append(fail("output_dir",
                              "--resume-refresh applies only to a terminally FAILED run with "
                              "Nextflow state in place (STATUS says FAILED and run/.nextflow "
                              "exists); neither holds here (0038)."))
            return
        hint = ""
        if (run_dir / ".nextflow").is_dir():
            hint = (" A FAILED run with Nextflow state can be re-prepared in place with "
                    "prepare --resume-refresh for a params-change-then-resume (0038).")
        fails.append(fail("output_dir",
                          "run/ is populated but carries no completion marker: a previous run "
                          "crashed or is still running. Nothing is deleted automatically -- "
                          "check STATUS and Slurm before moving it aside." + hint))


def check_config_common(cfg, required_keys, fails):
    """<REQUIRED> markers, required keys, readable reference files, sane work_dir."""
    unfilled = sorted(k for k, v in cfg.items() if "<REQUIRED" in v)
    if unfilled:
        fails.append(fail("config_unfilled",
                          "still marked <REQUIRED>: %s -- complete them from the stage 02 "
                          "menus" % ", ".join(unfilled)))
    for key in required_keys:
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
    work_dir = cfg.get("compute.work_dir", "")
    # A remote URI (s3://... on AWS Batch) is as absolute as a path gets; isabs() just
    # cannot know that. The refusal is only for RELATIVE paths, which silently resolve
    # against whatever directory the job happens to start in.
    if work_dir and not os.path.isabs(work_dir) and "://" not in work_dir:
        fails.append(fail("config", "compute.work_dir must be an absolute scratch path "
                                    "or a remote URI (e.g. s3://...), got %r" % work_dir))


def check_samplesheet(sheet_path, expected_header, fails, path_columns=(1, 2)):
    if not sheet_path.is_file():
        fails.append(fail("preconditions",
                          "no samplesheet at 01_samplesheets/%s -- run stage 01"
                          % sheet_path.name))
        return
    lines = sheet_path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",") if lines else []
    if header != list(expected_header):
        fails.append(fail("samplesheet", "header is %s, expected %s -- stage 01 owns this "
                                         "file; re-run it rather than editing"
                          % (",".join(header), ",".join(expected_header))))
        return
    for i, line in enumerate(lines[1:], start=2):
        row = line.split(",")
        for col in path_columns:
            if len(row) > col and row[col] and not os.path.isfile(row[col]):
                fails.append(fail("samplesheet",
                                  "row %d: %s does not resolve -- the project may have moved; "
                                  "re-run stage 01" % (i, row[col])))


def module_patch_state(checkout, relpath, legacy_needle, patched_needle):
    """Is a recorded pin patch applied (decision 0037)? -> 'patched' | 'legacy' | 'absent'.
    Content is the authority: a checkout that regressed (re-clone, git checkout .) reads
    legacy again and the preflight refusal comes back with the apply command."""
    p = pathlib.Path(checkout) / relpath
    if not p.is_file():
        return "absent"
    text = p.read_text(encoding="utf-8", errors="replace")
    if legacy_needle in text:
        return "legacy"
    if patched_needle in text:
        return "patched"
    return "absent"


def samplesheet_group_rep_tokens(sheet_path, sample_col=0, rep_col=3, require_col=None):
    """`<GROUP>_REP<N>` per samplesheet row (0035) -- the naming nf-core's merged-library
    outputs use. Exit gates check these rather than bare group names, so a lost replicate
    cannot hide behind its group's surviving one. `require_col`: only rows with that column
    non-empty (chipseq's IP rows)."""
    toks = set()
    for line in sheet_path.read_text(encoding="utf-8").splitlines()[1:]:
        if line.strip():
            c = line.split(",")
            if require_col is not None and not c[require_col]:
                continue
            toks.add("%s_REP%s" % (c[sample_col], c[rep_col]))
    return sorted(toks)


def samplesheet_samples(sheet_path, column=0):
    lines = sheet_path.read_text(encoding="utf-8").splitlines()
    return sorted({l.split(",")[column] for l in lines[1:] if l.strip()})


def write_submit_sh(substage, workspace_root, cfg, project_name, assay, body):
    """The batch script: directives from compute.*, the environment, the requeue guard,
    then the wrapper-specific body. Generated, never agent-written (decision 0011).

    The directives block comes from the workspace's executor descriptor (decision 0039), so
    the same generator serves Slurm, AWS Batch or anything else a site configures. With no
    descriptor the block is Slurm's, byte for byte -- pinned by a golden-bytes test.

    The guard: this cluster has Requeue=1, so a preempted job re-runs this script.
    - completion marker present -> exit cleanly instead of re-running the pipeline;
    - a Nextflow session exists -> a previous attempt crashed or was preempted; native
      `-resume` continues it from the work directory. (The ClawBio wrapper's manifest-gated
      resume could not do this; plain Nextflow can — decision 0028.)
    """
    descriptor = ex.load(ex.config_root_for(substage))
    directives = "".join(
        line + "\n" for line in
        ex.header_lines(None, cfg, project_name, assay, substage, descriptor=descriptor))
    script = """#!/bin/bash
{directives}# Generated by the {assay} wrapper's prepare. Regenerate with prepare; do not hand-edit.
# {submit_note}
set -euo pipefail

WS="{workspace}"
source "$WS/_system/gars-env.sh"
{parser_pairing}
cd "{substage}"
mkdir -p run logs
cd run

if [ -f .gars_run_complete ]; then
    echo "[guard] run already complete ($(cat .gars_run_complete)); nothing to do"
    exit 0
fi
RESUME=""
if [ -d .nextflow ]; then
    RESUME="-resume"
    echo "[guard] previous Nextflow session found; resuming"
fi

{body}

date '+%Y-%m-%dT%H:%M:%S%z' > .gars_run_complete
echo "[wrapper] run complete"
""".format(assay=assay, directives=directives, submit_note=ex.submit_note(descriptor),
           substage=str(substage.resolve()), workspace=str(workspace_root), body=body,
           parser_pairing=(
               "# Decision 0034: this pipeline's config predates the strict parser; the v1\n"
               "# parser is the recorded pairing while nextflow stays pinned (gars-nxf lockfile).\n"
               "export NXF_SYNTAX_PARSER=v1\n"
               if assay in ws.NEXTFLOW_LEGACY_PARSER else ""))
    with ws.atomic_open(substage / "submit.sh") as fh:
        fh.write(script)
    os.chmod(str(substage / "submit.sh"), 0o755)


def write_params_yaml(substage, assay, params):
    with ws.atomic_open(substage / "params.yaml") as fh:
        fh.write("# Generated by the %s wrapper's prepare. Do not hand-edit: the audited\n"
                 "# parameter surface is _config/%s.yaml; change that and re-run prepare.\n"
                 % (assay, assay))
        for key, value in params:
            fh.write("%s: %s\n" % (key, json.dumps(value) if " " in str(value) else value))


def write_reproducibility(substage, assay, checkout, inputs, params):
    """manifest.json (checksums, pipeline commit) + commands.sh. Deterministic bytes."""
    repro = substage / "reproducibility"
    repro.mkdir(exist_ok=True)
    try:
        commit = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE
                                ).stdout.decode().strip()
    except OSError:
        commit = "unknown"
    manifest = {"wrapper": assay, "pipeline_commit": commit, "checkout": str(checkout),
                "params": dict(params),
                "template_version": ws.template_version(Path(__file__).resolve().parents[1])}
    for label, path in inputs.items():
        manifest["%s_sha256" % label] = sha256(path)
    with ws.atomic_open(repro / "manifest.json") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    submit_sh = substage.resolve() / "submit.sh"
    with ws.atomic_open(repro / "commands.sh") as fh:
        fh.write("# The exact submission this sub-stage makes:\n"
                 "%s\n" % ex.submit_command(ex.config_root_for(substage), submit_sh))


def harvest_cache(derived_dir, subdir_name, built_dir, provenance_lines,
                  provenance_in_target=False):
    """Atomically publish built indices into the shared derived-reference cache.

    Temp sibling on the same filesystem, then rename into place (decision 0009): the cache is
    shared across projects and two runs may finish at once. Never overwrites a populated
    cache; losing the race is fine, the winner's copy is equivalent.
    Returns 'reused' | 'populated' | 'none'.
    """
    if not derived_dir:
        return "none"
    target = Path(derived_dir) / subdir_name
    if target.is_dir() and any(target.iterdir()):
        return "reused"
    if not (built_dir.is_dir() and any(built_dir.iterdir())):
        return "none"
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=".%s-incoming-" % subdir_name, dir=str(target.parent))
    shutil.copytree(str(built_dir), os.path.join(tmp, subdir_name))
    try:
        os.rename(os.path.join(tmp, subdir_name), str(target))
        # PROVENANCE sits beside the harvested content: inside the target when the target IS
        # the version-keyed cache dir (rnaseq harvests the whole genome dir), beside it when
        # the target is one component of it (atacseq harvests one aligner's index).
        pv = target if provenance_in_target else target.parent
        with ws.atomic_open(pv / "PROVENANCE") as fh:
            fh.write("".join(line + "\n" for line in provenance_lines))
        return "populated"
    except OSError:
        return "reused"      # another run won the race; theirs is fine
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
