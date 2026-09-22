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
           vocabulary; otherwise stamps `Status: APPROVED <date>` into PLAN.md and writes
           a record in the protected sibling .gars-approvals store, bound to the plan and
           expiring after 24 hours. Actor identity comes from the process UID at launch.
           Run it only after the user has said yes to the plan file -- the flag records the
           approval, it never substitutes for it.
  verify   the exit gate. Refuses unless the protected, unexpired store record exists and its sha256 matches
           PLAN.md -- a `Status: APPROVED` line alone is not an approval, and a plan edited
           after approval is not the plan that was approved (decision 0042); checks every
           output the plan declared exists and is non-empty; writes OUTPUTS.tsv (all rows
           `native`) and STATUS, and returns the history_entry to append verbatim.

Exit codes, like every stage helper: 0 ok, 1 failure, 2 refused (a gate), 3 usage.
Runs on stock python 3.6.8, stdlib only.
"""

import argparse
import datetime
import pwd
import stat
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wrapperlib as wl
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
Runs: batch
<FILL: expected wall time and output size. `batch` -- this workspace's configured scheduler,
whatever it is (decision 0039) -- is the default for every analysis, whatever its size
(decision 0027). `sbatch` is accepted as its Slurm-era spelling and means the same thing.
Change the line above to `Runs: login-node (user-requested)` ONLY if the user explicitly asked
for login-node execution -- never because the job looks small. The login node's cgroup kills
whatever is running when memory runs short, not whatever is at fault, and a wrong size
estimate is exactly the mistake a default cannot make.>
"""

#: `batch` is the venue; `sbatch` is what it was called when Slurm was the only scheduler
#: GARS knew, and every plan already written on the cluster says it. Both are the default;
#: decision 0027's ruling -- the agent never decides to run work in the current process --
#: is unchanged in force, only respelled (decision 0039).
EXECUTION_VENUES = ("batch", "sbatch", "login-node (user-requested)")


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


# --- approval record ---------------------------------------------------------------------------

# The location is derived from the installed workspace, never a CLI/environment override.
# Human launch creates this sibling store with mode 0700; guarded agents cannot access it.
APPROVAL_RECORD = "PLAN.md.approved"  # legacy filename: never evidence
LAUNCH_UID = os.getuid()
LAUNCH_ACTOR = pwd.getpwuid(LAUNCH_UID).pw_name
APPROVAL_LIFETIME = datetime.timedelta(hours=24)


def approval_store(workspace):
    return Path(workspace).resolve().parent / '.gars-approvals'


def approval_record_path(plan_path, workspace):
    identity = str(Path(plan_path).resolve())
    return approval_store(workspace) / (hashlib.sha256(identity.encode('utf-8')).hexdigest() + '.json')


def check_store(workspace, create=False):
    store = approval_store(workspace)
    if create:
        store.mkdir(mode=0o700, exist_ok=True)
    info = store.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != LAUNCH_UID or info.st_mode & 0o077:
        raise ValueError('R-073: approval store must be a human-owned directory with mode 0700')
    if store.resolve() == Path(workspace).resolve() or Path(workspace).resolve() in store.resolve().parents:
        raise ValueError('R-073: approval store must be outside the workspace')
    return store


def utc_instant(value):
    # Explicit UTC ISO-8601 only; no local-time interpretation, stdlib Python 3.6.
    return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)


def approval_holds(plan_path, record_path, workspace=None):
    workspace = workspace or ws.workspace_root(__file__)
    expected_path = approval_record_path(plan_path, workspace)
    if Path(record_path) != expected_path:
        return False, 'R-073: approval record is outside the human-owned store'
    try:
        check_store(workspace)
        info = expected_path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != LAUNCH_UID or info.st_mode & 0o077:
            raise ValueError('record must be human-owned, regular and mode 0600')
        record = json.loads(expected_path.read_text(encoding='utf-8'))
        if record['actor'] != LAUNCH_ACTOR or record['plan_path'] != str(Path(plan_path).resolve()):
            raise ValueError('approval actor or plan identity differs')
        timestamp, expiry = utc_instant(record['timestamp']), utc_instant(record['expiry'])
        now = datetime.datetime.now(datetime.timezone.utc)
        if timestamp > now or expiry <= timestamp or expiry - timestamp > APPROVAL_LIFETIME:
            raise ValueError('invalid approval lifetime')
        if now >= expiry:
            return False, 'R-073: approval record expired'
        expected = record['plan_sha256']
        actual = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    except (OSError, ValueError, KeyError, TypeError):
        return False, 'R-073: no valid approval record in the human-owned store'
    if actual != expected:
        return False, ('PLAN.md changed after approval (sha256 now %s, approved %s)'
                       % (actual[:12], str(expected)[:12]))
    return True, None


# --- approve -----------------------------------------------------------------------------------

def plan_gates(text, workspace, adir):
    """Every content gate is applied both at approval and verification (R-073/M-2)."""
    blocked = []
    n_fill = text.count(FILL)
    if n_fill:
        blocked.append("the plan still carries %d skeleton marker(s) (%s ...>); "
                                 "it is not a plan yet" % (n_fill, FILL))
    outputs = parse_outputs_table(text)
    if not outputs:
        blocked.append("the Outputs table declares nothing; an analysis that "
                                 "declares no outputs cannot be verified")
    vocab, err = read_vocabulary(workspace)
    if err:
        blocked.append(err)
        return blocked
    for fname, ftype, _ in outputs:
        if ftype not in vocab:
            blocked.append("output %r has type %r, which is not in the closed "
                                     "vocabulary (_references/artifact_types.md); closed "
                                     "means closed -- ask for the vocabulary to be extended "
                                     "rather than inventing a type" % (fname, ftype))
        if os.path.isabs(fname) or ".." in Path(fname).parts or not fname:
            blocked.append("output %r must be a relative path inside the analysis "
                                     "directory" % fname)
    venue = re.search(r"^Runs:\s*(.+?)\s*$", text, re.M)
    if not venue:
        blocked.append("the Execution section has no `Runs:` line; every plan "
                                 "states its venue -- `Runs: batch` (the default; `sbatch` "
                                 "is its Slurm-era spelling) or `Runs: login-node "
                                 "(user-requested)` when the user explicitly asked "
                                 "(decisions 0027, 0039)")
    elif venue.group(1) not in EXECUTION_VENUES:
        blocked.append("`Runs: %s` is not a recognised venue. `batch` -- this "
                                 "workspace's configured scheduler, `sbatch` accepted as its "
                                 "Slurm-era spelling -- is the default for every analysis; "
                                 "`login-node (user-requested)` is allowed only when the user "
                                 "explicitly asked for it -- job size is never the reason "
                                 "(decisions 0027, 0039)"
                                 % venue.group(1))
    for fname, _, _ in outputs:
        try:
            (adir / fname).resolve().relative_to(adir.resolve())
        except ValueError:
            blocked.append('output resolves outside the analysis directory')
    return blocked


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
    record_path = approval_record_path(plan_path, workspace)

    if re.search(r"^Status: APPROVED", text, re.M):
        holds, why = approval_holds(plan_path, record_path, workspace)
        if holds:
            result["ok"] = True
            result["already_approved"] = True
            return emit(result, EXIT_OK)
        result["error"] = ("PLAN.md carries an approval stamp, but %s. `approve` writes the stamp "
                           "and its record together, so either this stamp was not written by "
                           "`approve` or the plan changed after approval. A change of mind is a "
                           "new analysis: run `create` again (decision 0042)." % why)
        return emit(result, EXIT_REFUSED)
    if record_path.exists():
        # The plan was approved once and has since been set back to DRAFT. Re-approving would
        # silently re-bind the record to an edited plan; approval is once per analysis.
        result["error"] = ("%s already exists for this analysis, but PLAN.md is no longer "
                           "stamped. Approval happens once per analysis; a change of mind is a "
                           "new analysis: run `create` again (decision 0042)." % APPROVAL_RECORD)
        return emit(result, EXIT_REFUSED)

    result["blocked"].extend(plan_gates(text, workspace, adir))
    outputs = parse_outputs_table(text)
    if "Status: DRAFT" not in text:
        result["blocked"].append("PLAN.md has no `Status: DRAFT` line to promote")

    if result["blocked"]:
        return emit(result, EXIT_REFUSED)

    try:
        check_store(workspace, create=True)
    except (OSError, ValueError) as exc:
        result['error'] = str(exc)
        return emit(result, EXIT_REFUSED)
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    stamp = "Status: APPROVED %s" % (args.date or now.date().isoformat())
    with ws.atomic_open(plan_path, newline=None) as fh:
        fh.write(text.replace("Status: DRAFT", stamp, 1))
    record = {
        'actor': LAUNCH_ACTOR,
        'timestamp': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'expiry': (now + APPROVAL_LIFETIME).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        'plan_path': str(plan_path.resolve()),
    }
    # Exclusive creation refuses overwrites; a crash leaves an invalid record, never approval.
    try:
        fd = os.open(str(record_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as fh:
            json.dump(record, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError as exc:
        result['error'] = 'R-073: cannot create approval record: %s' % exc
        return emit(result, EXIT_REFUSED)
    result.update({"ok": True, "outputs_declared": len(outputs), "status": stamp,
                   "record": str(record_path), "plan_sha256": record["plan_sha256"]})
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
    holds, why = approval_holds(adir / "PLAN.md", approval_record_path(adir / "PLAN.md", workspace), workspace)
    if not holds:
        result["error"] = ("PLAN.md is not approved: %s. A `Status: APPROVED` line is an approval "
                           "only when `approve` wrote it together with its record, and a plan "
                           "edited after approval is a new analysis -- run `create` again. If "
                           "the analysis already ran, that is the failure to report (decision "
                           "0042)." % why)
        return emit(result, EXIT_REFUSED)

    blocked = plan_gates(text, workspace, adir)
    if blocked:
        result['blocked'] = blocked
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

    if not (adir / 'run/.gars_run_complete').is_file():
        result['error'] = 'run/.gars_run_complete is absent: execution success is unproven'
        return emit(result, EXIT_REFUSED)

    with ws.atomic_open(adir / "OUTPUTS.tsv") as fh:
        fh.write("# type\trole\tpath\n")
        for fname, ftype, _ in outputs:
            fh.write("%s\tnative\t%s\n" % (ftype, fname))

    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    wl.write_status(adir, "COMPLETE")

    version = ws.template_version(workspace)
    model = args.model or "unknown"
    goal = re.search(r"^## Goal\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    goal_line = " ".join(goal.group(1).split()) if goal else ""
    if len(goal_line) > 200:
        # break at a word, not mid-word -- this line is read by humans in HISTORY.md
        goal_line = goal_line[:200].rsplit(" ", 1)[0] + " ..."
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
    workspace = ws.workspace_root(__file__)
    if args.workspace is not None and args.workspace.resolve() != Path(workspace).resolve():
        return emit({'command': args.cmd, 'ok': False,
                     'error': 'R-073: --workspace cannot relocate the human approval store'}, EXIT_REFUSED)
    return {"create": cmd_create, "approve": cmd_approve,
            "verify": cmd_verify}[args.cmd](args, workspace)


if __name__ == "__main__":
    sys.exit(main())
