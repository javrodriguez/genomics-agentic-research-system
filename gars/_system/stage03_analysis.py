#!/usr/bin/env python3
"""Stage 03 helper: the deterministic rails a plan-gated custom analysis runs on.

The analysis itself is bespoke -- that is the point of stage 03, and the one place agent
judgment is supposed to live (decision 0026). What is NOT bespoke is the machinery around it:
directory allocation, the plan's approval gate, output verification, registry rows, the
history entry. Those have one correct answer each, so they are code (decision 0011).

Subcommands, in the order a run uses them:

  create   allocate 03_custom_analysis/<NN_slug>/ with scripts/, results/ and a PLAN.md
           skeleton whose <FILL: ...> markers say what the drafted plan must contain.
  approve  the human gate, made durable. Refuses while the plan still carries skeleton
           markers, has no Outputs rows, or names an artifact type outside the closed
           vocabulary; otherwise stamps `Status: APPROVED <date>` into PLAN.md. Run it only
           after the user has said yes to the plan file -- the flag records the approval,
           it never substitutes for it.
  verify   the exit gate. Refuses if the plan is not approved; checks every output the plan
           declared exists and is non-empty; writes OUTPUTS.tsv (all rows `native`) and
           STATUS, and returns the history_entry to append verbatim.

Exit codes, like every stage helper: 0 ok, 1 failure, 2 refused (a gate), 3 usage.
Runs on stock python 3.6.8, stdlib only.
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace as ws          # noqa: E402

EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2, 3

STAGE_DIR = "03_custom_analysis"
FILL = "<FILL:"

PLAN_SKELETON = """# Analysis plan: {slug}

Status: DRAFT

An analysis runs only after a person has read this file and approved it. Edit anything;
approval is what freezes it. After approval the plan is the record of intent -- change of
mind means a new analysis, not a quiet edit.

## Goal
<FILL: what question this analysis answers, in the user's words. One paragraph.>

## Inputs
Artifact types resolve through each sub-stage's OUTPUTS.tsv at execution time; the paths
below are what they resolve to today.

| Artifact type | Resolved from | Path |
|---|---|---|
<FILL: one row per input, from _system/resolve_artifact.py>

## Method
<FILL: numbered steps. Name every tool and parameter; name the conda environment
(gars-bio unless stated); say which steps run where. No step may modify an input in place.>

## Outputs
Types come from the closed vocabulary in _references/artifact_types.md.

| File | Type | Description |
|---|---|---|
<FILL: one row per output. Paths relative to this analysis directory, e.g. results/x.csv>

## Execution
<FILL: login node or sbatch, expected wall time, expected size. Anything beyond a few
CPU-minutes or a few GB is sbatch work -- the login node's cgroup kills whatever is running,
not whatever is at fault.>
"""


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


def read_vocabulary(workspace):
    """The closed artifact-type vocabulary, from the first table in artifact_types.md."""
    path = Path(workspace) / "_references" / "artifact_types.md"
    if not path.is_file():
        return [], "missing %s" % path
    types = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Type |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip("|").split("|")]
            m = re.match(r"^`([a-z0-9_]+)`$", cells[0]) if cells else None
            if m:
                types.append(m.group(1))
    if not types:
        return [], "no types parsed from %s" % path
    return types, None


def sanitize_slug(slug):
    s = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    return s


def stage_root(project):
    return Path(project) / STAGE_DIR


def find_analysis(project, name):
    d = stage_root(project) / name
    return d if d.is_dir() else None


def parse_outputs_table(plan_text):
    """Rows of the ## Outputs table: (file, type, description). Skips FILL markers."""
    rows = []
    section = re.search(r"^## Outputs\n(.*?)(?=^## |\Z)", plan_text, re.S | re.M)
    if not section:
        return rows
    for line in section.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---") or FILL in line:
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] not in ("File", ""):
            rows.append((cells[0], cells[1], cells[2] if len(cells) > 2 else ""))
    return rows


# --- create ------------------------------------------------------------------------------------

def cmd_create(args, workspace):
    result = {"command": "create", "ok": False}
    project = Path(args.project)
    if not project.is_dir():
        result["error"] = "no such project: %s" % project
        return emit(result, EXIT_USAGE)

    slug = sanitize_slug(args.slug)
    if not slug:
        result["error"] = "slug %r sanitizes to nothing; give a short kebab-case name" % args.slug
        return emit(result, EXIT_USAGE)
    result["slug"] = slug

    root = stage_root(project)
    root.mkdir(exist_ok=True)
    existing = sorted(d.name for d in root.iterdir() if d.is_dir() and re.match(r"^\d\d_", d.name))
    n = 1 + max([int(d[:2]) for d in existing] or [0])
    name = "%02d_%s" % (n, slug)
    adir = root / name
    adir.mkdir()
    (adir / "scripts").mkdir()
    (adir / "results").mkdir()
    with ws.atomic_open(adir / "PLAN.md", newline=None) as fh:
        fh.write(PLAN_SKELETON.format(slug=slug))

    result.update({"ok": True, "analysis": name,
                   "dir": str(adir.relative_to(project)),
                   "plan": str((adir / "PLAN.md").relative_to(project)),
                   "existing_analyses": existing,
                   "template_version": ws.template_version(workspace)})
    return emit(result, EXIT_OK)


# --- approve -----------------------------------------------------------------------------------

def cmd_approve(args, workspace):
    result = {"command": "approve", "ok": False, "analysis": args.analysis, "blocked": []}
    project = Path(args.project)
    adir = find_analysis(project, args.analysis)
    if adir is None:
        result["error"] = "no analysis %r under %s" % (args.analysis, stage_root(project))
        return emit(result, EXIT_USAGE)
    plan_path = adir / "PLAN.md"
    if not plan_path.is_file():
        result["error"] = "PLAN.md is missing"
        return emit(result, EXIT_USAGE)
    text = plan_path.read_text(encoding="utf-8")

    if "Status: APPROVED" in text:
        result["ok"] = True
        result["already_approved"] = True
        return emit(result, EXIT_OK)

    n_fill = text.count(FILL)
    if n_fill:
        result["blocked"].append("the plan still carries %d skeleton marker(s) (%s ...>); "
                                 "it is not a plan yet" % (n_fill, FILL))
    outputs = parse_outputs_table(text)
    if not outputs:
        result["blocked"].append("the Outputs table declares nothing; an analysis that "
                                 "declares no outputs cannot be verified")
    vocab, err = read_vocabulary(workspace)
    if err:
        result["error"] = err
        return emit(result, EXIT_FAILURE)
    for fname, ftype, _ in outputs:
        if ftype not in vocab:
            result["blocked"].append("output %r has type %r, which is not in the closed "
                                     "vocabulary (_references/artifact_types.md); closed "
                                     "means closed -- ask for the vocabulary to be extended "
                                     "rather than inventing a type" % (fname, ftype))
        if os.path.isabs(fname) or fname.startswith(".."):
            result["blocked"].append("output %r must be a relative path inside the analysis "
                                     "directory" % fname)
    if "Status: DRAFT" not in text:
        result["blocked"].append("PLAN.md has no `Status: DRAFT` line to promote")

    if result["blocked"]:
        return emit(result, EXIT_REFUSED)

    stamp = "Status: APPROVED %s" % (args.date or datetime.date.today().isoformat())
    with ws.atomic_open(plan_path, newline=None) as fh:
        fh.write(text.replace("Status: DRAFT", stamp, 1))
    result.update({"ok": True, "outputs_declared": len(outputs), "status": stamp})
    return emit(result, EXIT_OK)


# --- verify ------------------------------------------------------------------------------------

def cmd_verify(args, workspace):
    result = {"command": "verify", "ok": False, "analysis": args.analysis,
              "missing": [], "empty": []}
    project = Path(args.project)
    adir = find_analysis(project, args.analysis)
    if adir is None:
        result["error"] = "no analysis %r under %s" % (args.analysis, stage_root(project))
        return emit(result, EXIT_USAGE)
    text = (adir / "PLAN.md").read_text(encoding="utf-8")

    m = re.search(r"^Status: APPROVED( .*)?$", text, re.M)
    if not m:
        result["error"] = ("PLAN.md is not approved; the analysis must not have run. If it "
                           "did, that is the failure to report -- do not approve after the "
                           "fact.")
        return emit(result, EXIT_REFUSED)

    outputs = parse_outputs_table(text)
    if not outputs:
        result["error"] = "the approved plan declares no outputs; nothing to verify"
        return emit(result, EXIT_FAILURE)

    for fname, ftype, _ in outputs:
        p = adir / fname
        if not p.is_file():
            result["missing"].append(fname)
        elif p.stat().st_size == 0:
            result["empty"].append(fname)
    if result["missing"] or result["empty"]:
        return emit(result, EXIT_FAILURE)

    with ws.atomic_open(adir / "OUTPUTS.tsv") as fh:
        fh.write("# type\trole\tpath\n")
        for fname, ftype, _ in outputs:
            fh.write("%s\tnative\t%s\n" % (ftype, fname))

    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with ws.atomic_open(adir / "STATUS") as fh:
        fh.write("COMPLETE %s\n" % now)

    version = ws.template_version(workspace)
    model = args.model or "unknown"
    goal = re.search(r"^## Goal\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    goal_line = " ".join(goal.group(1).split())[:200] if goal else ""
    entry = "\n".join([
        "## <ISO-8601 date> — 03_custom_analysis/%s — analysis complete" % args.analysis,
        "",
        "Template version: %s" % version,
        "Model: %s" % model,
        "Plan: %s/%s/PLAN.md (approved%s)" % (STAGE_DIR, args.analysis, m.group(1) or ""),
        "Goal: %s" % goal_line,
        "Outputs: " + ", ".join("`%s` (%s)" % (f, t) for f, t, _ in outputs),
    ])
    result.update({"ok": True, "outputs": [{"path": f, "type": t} for f, t, _ in outputs],
                   "template_version": version, "model": model, "history_entry": entry})
    return emit(result, EXIT_OK)


# --- main --------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", type=Path, default=None)
    sub = ap.add_subparsers(dest="cmd")

    c = sub.add_parser("create", help="allocate an analysis directory with a PLAN.md skeleton")
    c.add_argument("--project", required=True)
    c.add_argument("--slug", required=True, help="short kebab-case name for the analysis")

    a = sub.add_parser("approve", help="record the user's approval of PLAN.md (the human gate)")
    a.add_argument("--project", required=True)
    a.add_argument("--analysis", required=True, help="the NN_slug directory name")
    a.add_argument("--date", default=None)

    v = sub.add_parser("verify", help="exit gate: outputs exist -> OUTPUTS.tsv, STATUS, history")
    v.add_argument("--project", required=True)
    v.add_argument("--analysis", required=True)
    v.add_argument("--model", default="unknown",
                   help="the exact model id of the agent executing this stage (decision 0024)")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help(sys.stderr)
        return EXIT_USAGE
    workspace = args.workspace or ws.workspace_root(__file__)
    return {"create": cmd_create, "approve": cmd_approve,
            "verify": cmd_verify}[args.cmd](args, workspace)


if __name__ == "__main__":
    sys.exit(main())
