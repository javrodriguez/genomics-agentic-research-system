#!/usr/bin/env python3
"""Upgrade a workspace's template layer from a newer GARS checkout, leaving projects untouched.

A workspace is a *copy* of `gars/`, not a clone: it has no `.git` and no remote, so `git pull` in
the source repository does not reach it. That freeze is deliberate -- stage 00 stamps the template
version into every project so results can name the contracts that produced them, and contracts
must not change silently underneath a running analysis. But freezing without an upgrade path is
half a design: a fixed bug never reaches an existing workspace.

This is the other half. The split it relies on is the factory/product split the workspace is
already built around:

    template layer (replaced)   stage contracts, _references/, _system/, _templates/,
                                CLAUDE.md, CONTEXT.md    -- the factory, identical in every copy
    work (never touched)        projects/                -- the product, unique to this workspace

Nothing in the template layer holds per-project state, and nothing in `projects/` is needed to
interpret a contract, so the two can be swapped independently.

**Upgrading changes the contracts under existing projects.** That is legitimate -- a bug fix
should reach them -- but it must be recorded, or a project's `CONTEXT.md` will name one version
while a later stage ran under another. So this appends a note to every project's `HISTORY.md`,
and every stage stamps its own version as it runs (see `_system/workspace.py`).

Usage
-----
    python3 _system/upgrade.py --source /path/to/gars-repo            # dry run: what would change
    python3 _system/upgrade.py --source /path/to/gars-repo --apply    # do it

Exit codes: 0 ok (or nothing to do) / 1 refused / 3 usage.
"""

import argparse
import datetime
import filecmp
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace as ws          # noqa: E402

# Replaced wholesale. Everything here is factory: identical in every workspace of a given version.
TEMPLATE_DIRS = ("_references", "_system", "_templates")
TEMPLATE_FILES = ("CLAUDE.md", "CONTEXT.md")
# Stage contract directories are discovered, not listed, so a new stage is picked up automatically.
STAGE_PREFIXES = tuple("%02d_" % n for n in range(100))

NEVER_TOUCH = ("projects",)

EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 3


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


def resolve_source(source):
    """Accept either a GARS repo checkout or a template directory directly."""
    source = Path(source).resolve()
    if (source / "_references" / "VERSION").is_file():
        return source, None
    if (source / "gars" / "_references" / "VERSION").is_file():
        return source / "gars", None
    return None, ("%s is neither a GARS template directory nor a repo containing one "
                  "(no _references/VERSION found)" % source)


def template_members(root):
    """Every path in the template layer of `root`, relative to it."""
    members = []
    for name in TEMPLATE_FILES:
        if (root / name).is_file():
            members.append(name)
    for name in TEMPLATE_DIRS:
        if (root / name).is_dir():
            members.append(name)
    for child in sorted(root.iterdir()):
        if child.is_dir() and child.name.startswith(STAGE_PREFIXES):
            members.append(child.name)
    return members


def differs(a, b):
    """True when a and b are not identical files/trees."""
    if a.is_dir() != b.is_dir():
        return True
    if a.is_file():
        return not filecmp.cmp(str(a), str(b), shallow=False)
    cmp = filecmp.dircmp(str(a), str(b))
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return True
    for sub in cmp.common_dirs:
        if differs(a / sub, b / sub):
            return True
    return False


def project_versions(workspace):
    """What each existing project records as the version that created it."""
    out = {}
    projects = workspace / "projects"
    if not projects.is_dir():
        return out
    for p in sorted(projects.iterdir()):
        if not p.is_dir() or p.name.startswith("_"):
            continue
        ctx = p / "CONTEXT.md"
        version = "unknown"
        if ctx.is_file():
            for line in ctx.read_text(encoding="utf-8").splitlines():
                if line.startswith("| Template version |"):
                    version = line.split("|")[2].strip()
                    break
        out[p.name] = version
    return out


def cmd_status(workspace, marker, source_arg):
    """Is this workspace behind its source? Informational: never writes, never fails on absence.

    A workspace is made with `cp -r`, which records nothing, so the source is only known once
    `--set-source` or `--apply` has run. Saying so plainly beats guessing at a path.
    """
    result = {"command": "status", "ok": True, "workspace": str(workspace),
              "version": ws.template_version(workspace),
              "source": marker.get("source"), "source_version": None, "state": None}

    chosen = source_arg or marker.get("source")
    if not chosen:
        result["state"] = "unknown"
        result["note"] = ("this workspace does not record where it was copied from; run "
                          "`upgrade.py --source <repo> --set-source` once to record it")
        return emit(result, EXIT_OK)

    source, err = resolve_source(chosen)
    if err:
        result["state"] = "unreachable"
        result["note"] = err
        return emit(result, EXIT_OK)

    result["source"] = str(source)
    result["source_version"] = ws.template_version(source)
    result["state"] = ws.compare_versions(result["version"], result["source_version"])
    result["note"] = {
        "same": "up to date",
        "behind": "a newer template is available; see `upgrade.py --source <repo>`",
        "ahead": "this workspace is NEWER than its source -- check the source is the right one",
        "differs": "versions are not comparable; inspect both before upgrading",
    }[result["state"]]
    return emit(result, EXIT_OK)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", default=None,
                    help="a GARS repo checkout, or a gars/ template directory. Optional with "
                         "--status, which falls back to the source recorded in .gars-workspace")
    ap.add_argument("--status", action="store_true",
                    help="report this workspace's version against its source, and exit")
    ap.add_argument("--set-source", action="store_true",
                    help="record --source in .gars-workspace without upgrading")
    ap.add_argument("--workspace", default=None,
                    help="workspace to upgrade (default: the one this script lives in)")
    ap.add_argument("--apply", action="store_true",
                    help="perform the upgrade; without it this is a dry run")
    ap.add_argument("--date", default=None)
    args = ap.parse_args(argv)

    workspace = Path(args.workspace).resolve() if args.workspace \
        else ws.workspace_root(__file__)
    marker = ws.read_marker(workspace)

    if args.status:
        return cmd_status(workspace, marker, args.source)

    if not args.source:
        return emit({"command": "upgrade", "ok": False,
                     "error": "--source is required (or use --status)"}, EXIT_USAGE)

    result = {"command": "upgrade", "ok": False, "workspace": str(workspace),
              "applied": bool(args.apply)}

    source, err = resolve_source(args.source)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)
    if source == workspace:
        result["error"] = "source and workspace are the same directory"
        return emit(result, EXIT_USAGE)
    result["source"] = str(source)

    if args.set_source:
        data = ws.write_marker(workspace, source=str(source),
                               recorded=args.date or datetime.date.today().isoformat())
        return emit({"command": "upgrade", "ok": True, "workspace": str(workspace),
                     "note": "source recorded; nothing was upgraded", "marker": data}, EXIT_OK)

    result["from_version"] = ws.template_version(workspace)
    result["to_version"] = ws.template_version(source)
    result["projects"] = project_versions(workspace)

    members = template_members(source)
    changed, added = [], []
    for name in members:
        src, dst = source / name, workspace / name
        if not dst.exists():
            added.append(name)
        elif differs(src, dst):
            changed.append(name)
    # Present in the workspace but gone from the source: report, never delete. A stage removed
    # upstream may still be the one that produced an existing project's results.
    stale = [n for n in template_members(workspace) if not (source / n).exists()]

    result["changed"] = changed
    result["added"] = added
    result["removed_upstream_kept_here"] = stale
    # Directories only. `_index.md` and `.gitkeep` are not projects, and listing them as
    # "untouched" implied a guarantee about files this command does regenerate.
    result["projects_untouched"] = sorted(result["projects"])

    if not changed and not added:
        result["ok"] = True
        result["note"] = "workspace template layer already matches the source"
        return emit(result, EXIT_OK)

    if not args.apply:
        result["ok"] = True
        result["note"] = "dry run -- re-run with --apply to perform the upgrade"
        return emit(result, EXIT_OK)

    for name in changed + added:
        src, dst = source / name, workspace / name
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(str(dst))
            else:
                dst.unlink()
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))

    # Record it against every project, so a later reader can see that the contracts moved.
    date = args.date or datetime.date.today().isoformat()
    noted = []
    for name in result["projects"]:
        h = workspace / "projects" / name / "HISTORY.md"
        if not h.is_file():
            continue
        h.write_text(h.read_text(encoding="utf-8").rstrip() + "\n\n" + "\n".join([
            "## %s — workspace upgraded — template %s -> %s" % (date, result["from_version"],
                                                                result["to_version"]),
            "",
            "The contracts under this project were replaced from `%s`. Nothing in this project "
            "was modified." % source,
            "Stages that already ran did so under %s; stages that run from now on will stamp "
            "their own version." % result["from_version"],
        ]) + "\n", encoding="utf-8")
        noted.append(name)
    result["history_noted"] = noted
    # Remember where this came from, so `--status` can answer without being told again.
    result["marker"] = ws.write_marker(workspace, source=str(source), last_upgrade=date,
                                       last_upgrade_to=result["to_version"])
    result["ok"] = True
    return emit(result, EXIT_OK)


if __name__ == "__main__":
    sys.exit(main())
