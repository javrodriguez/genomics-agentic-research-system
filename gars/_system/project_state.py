#!/usr/bin/env python3
"""Render a project's state as a catch-up — derived, never recorded (decision 0033).

The project CONTEXT.md's rule stands: state is not recorded anywhere, it is derivable from
the filesystem. This script IS that derivation, run on demand — the per-project sibling of
`build_projects_index.sh`, with the narrative a returning session needs: how far each assay
got (STATUS is the only authority), which scientific decisions are still unmade (the
`<REQUIRED` markers), what the last HISTORY.md entries say, and what artifacts are
registered. It writes nothing, so it can never drift from the truth it renders.

Run:  python3 _system/project_state.py                    # every project
      python3 _system/project_state.py --project projects/<name>
      python3 _system/project_state.py --last 5           # more HISTORY entries

Stock python >=3.6, stdlib only, read-only.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace  # noqa: E402

HISTORY_DEFAULT = 3


def _context_field(project, field):
    """A `| Field | value |` row from the project CONTEXT.md, or None."""
    ctx = project / "CONTEXT.md"
    if not ctx.is_file():
        return None
    for line in ctx.read_text(encoding="utf-8").splitlines():
        if line.startswith("| %s | " % field) and line.rstrip().endswith("|"):
            value = line.split("|")[2].strip()
            if value and "{{" not in value:
                return value
    return None


def _status_line(sub):
    """The first line of a sub-stage's STATUS — the only authority on completion."""
    p = sub / "STATUS"
    if not p.is_file():
        return "NOT_STARTED"
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            return line.strip()
    return "NOT_STARTED"


def _outputs_types(sub):
    """The artifact types a sub-stage registered, in OUTPUTS.tsv order."""
    p = sub / "OUTPUTS.tsv"
    if not p.is_file():
        return []
    types = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue          # the "# type\tpath\t..." header is a comment, not an artifact
        cells = line.split("\t")
        if len(cells) >= 3 and cells[0] and cells[0] != "type":
            types.append(cells[0])
    return types


def _config_unfilled(project, assay):
    """Keys still marked <REQUIRED> in this assay's config — the stage 01/02 idiom."""
    cfg = project / "_config" / (assay + ".yaml")
    if not cfg.is_file():
        return None  # distinct from []: no config at all
    unfilled = []
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if "<REQUIRED" in line and not line.lstrip().startswith("#"):
            unfilled.append(line.split(":")[0].strip())
    return unfilled


def _history_entries(project):
    """(total, [entry header lines]) from the append-only HISTORY.md."""
    p = project / "HISTORY.md"
    if not p.is_file():
        return 0, []
    headers = [l[3:].strip() for l in p.read_text(encoding="utf-8").splitlines()
               if l.startswith("## ")]
    return len(headers), headers


def render_project(project, last):
    out = []
    name = project.name
    version = _context_field(project, "Template version") or "?"
    created = _context_field(project, "Created")
    head = "## %s — template %s" % (name, version)
    if created:
        head += " — created %s" % created
    out.append(head)

    data = project / "00_data"
    assays = sorted(d.name for d in data.iterdir() if d.is_dir()) if data.is_dir() else []
    if not assays:
        out.append("- no assay directories yet (stage 00 has not linked data)")

    for assay in assays:
        samples = data / assay / "samples.csv"
        if not samples.is_file():
            design = "missing"
        else:
            rows = [r for r in samples.read_text(encoding="utf-8").splitlines()[1:] if r.strip()]
            filled = any(len(r.split(",")) > 1 and any(c.strip() for c in r.split(",")[1:])
                         for r in rows)
            design = "filled (%d samples)" % len(rows) if filled else "incomplete"
        sheet = "yes" if (project / "01_samplesheets" / (assay + "_samplesheet.csv")).is_file() else "no"
        out.append("### %s — design %s · samplesheet %s" % (assay, design, sheet))

        unfilled = _config_unfilled(project, assay)
        if unfilled is None:
            out.append("- config: not seeded")
        elif unfilled:
            out.append("- config decisions still unmade: " + ", ".join(unfilled))
        else:
            out.append("- config: complete")

        stage2 = project / "02_bioinformatics" / assay
        subs = sorted(d for d in stage2.iterdir() if d.is_dir()) if stage2.is_dir() else []
        for sub in subs:
            line = "- %s: %s" % (sub.name, _status_line(sub))
            types = _outputs_types(sub)
            if types:
                line += " · artifacts: " + ", ".join(types)
            out.append(line)
        if not subs:
            out.append("- stage 02: not started")

    stage3 = project / "03_custom_analysis"
    analyses = sorted(d for d in stage3.iterdir() if d.is_dir()) if stage3.is_dir() else []
    if analyses:
        out.append("### custom analyses")
        for a in analyses:
            out.append("- %s: %s" % (a.name, _status_line(a)))

    total, headers = _history_entries(project)
    if total:
        out.append("### history — %d entries, last %d:" % (total, min(last, total)))
        for h in headers[-last:]:
            out.append("- " + h)
    else:
        out.append("### history — no entries yet")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", help="one project directory (relative to cwd or absolute)")
    ap.add_argument("--last", type=int, default=HISTORY_DEFAULT,
                    help="HISTORY.md entries to show per project (default %d)" % HISTORY_DEFAULT)
    args = ap.parse_args()

    ws = workspace.workspace_root(__file__)
    out = ["# Project state — derived from the filesystem, authority: STATUS + HISTORY.md",
           "(template %s · generated by _system/project_state.py; a render, not a record)"
           % workspace.template_version(ws), ""]

    if args.project:
        projects = [Path(args.project).resolve()]
        if not projects[0].is_dir():
            print("no such project directory: %s" % args.project, file=sys.stderr)
            return 2
    else:
        root = ws / "projects"
        projects = sorted(d for d in root.iterdir()
                          if d.is_dir() and not d.name.startswith("_")) if root.is_dir() else []
        if not projects:
            out.append("(no projects yet)")

    for p in projects:
        try:
            out.extend(render_project(p, args.last))
        except Exception as exc:  # a broken project must not hide the others' state
            out.append("## %s — render failed: %s" % (p.name, exc))
        out.append("")
    print("\n".join(out).rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
