#!/usr/bin/env python3
"""Render a project's state as a catch-up — derived, never recorded (decision 0033).

The project CONTEXT.md's rule stands: state is not recorded anywhere, it is derivable from
the filesystem. This script IS that derivation, run on demand — the per-project sibling of
`build_projects_index.sh`, with the narrative a returning session needs: how far each assay
got (STATUS is the only authority), which scientific decisions are still unmade (the
`<REQUIRED` markers), what the last HISTORY.md entries say, and what artifacts are
registered. It writes nothing, so it can never drift from the truth it renders.

A closed project (decision 0107, as `guard_hook.py` judges it) renders as its name, its class
label and each stage 02 sub-stage's STATUS, and nothing else (decision 0151): the hook prints
this into a hosted model's context, which 0107 keeps a closed project's data out of.

Run:  python3 _system/project_state.py                    # every project
      python3 _system/project_state.py --project projects/<name>
      python3 _system/project_state.py --last 5           # more HISTORY entries
      python3 _system/project_state.py --closed-list [ws] # `<name><TAB><label>` per closed project

Stock python >=3.6, stdlib only, read-only.
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard_hook  # noqa: E402  (0107's closed judgement: imported, never copied)
import workspace  # noqa: E402

HISTORY_DEFAULT = 3
# A project name the `<name>\t<label>` list cannot carry is never written (decision 0151).
UNPRINTABLE = "(unprintable project name)"


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
    headers = []
    fenced = False
    for line in p.read_text(encoding="utf-8").splitlines():
        # HISTORY.md's own header carries the entry FORMAT inside a fenced block, and that
        # example line starts with "## " like a real entry does. Counting it told every
        # project it had one more entry than it has, and printed the placeholder as though
        # it had happened -- on the one surface whose whole claim is that it reports what
        # the project actually recorded.
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced and line.startswith("## "):
            headers.append(line[3:].strip())
    return len(headers), headers


def printable(name):
    """False for a name holding a control character (below 0x20, or 0x7f): such a name could
    split a list record or a render line, so it is shown as UNPRINTABLE, closed (0151)."""
    return not any(ord(c) < 0x20 or ord(c) == 0x7f for c in name)


def closed_labels(ws):
    """{name: class label} for every project of `ws` the guard judges closed. The one function
    the render and `build_projects_index.sh` (through --closed-list) share (decision 0151)."""
    return dict((name, label) for name, label, _ in guard_hook.closed_projects(str(ws)))


def _status_value_pattern():
    """A STATUS first line wrapperlib.write_status can produce: a state word (`:reason` only
    on FAILED), then its UTC timestamp, with a job id between them only after SUBMITTED or
    RUNNING; a bare state word is also read (decision 0151). The states and the named
    reasons come from wrapperlib; EXIT_<n> and the two job-id states are literals inside
    write_status, which exposes no name for them."""
    import wrapperlib
    states = "|".join(re.escape(s) for s in wrapperlib.STATUS_STATES)
    reasons = "|".join(re.escape(r) for r in wrapperlib.FAILURE_REASONS) + "|EXIT_[0-9]+"
    stamp = r" [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    return re.compile(r"(?:(?:%s|FAILED:(?:%s))(?:%s)?|(?:SUBMITTED|RUNNING) [0-9]+%s)\Z"
                      % (states, reasons, stamp, stamp))


def _closed_status_line(project, sub):
    """A closed project's STATUS, read only as 0107 leaves it readable: a regular file at its
    own path, never through a symlink. Anything else raises, and the project renders its
    heading alone. A first line the STATUS writer could not have produced prints
    `unrecognized`."""
    p = sub / "STATUS"
    if not os.path.lexists(str(p)):
        return "NOT_STARTED"
    own = os.path.join(os.path.realpath(str(project)), "02_bioinformatics",
                       sub.parent.name, sub.name, "STATUS")
    if os.path.realpath(str(p)) != own:
        raise OSError("STATUS is not the sub-stage's own file")
    for line in guard_hook._regular_text(str(p)).splitlines():
        if line.strip():
            return line.strip() if _status_value_pattern().match(line.strip()) else "unrecognized"
    return "NOT_STARTED"


def render_closed(project, label):
    """A closed project: its name, its label, and one line per stage 02 sub-stage. A name
    that is not printable is its heading alone."""
    if not printable(project.name):
        return ["## %s — closed (unclassified)" % UNPRINTABLE]
    head = "## %s — closed (%s)" % (project.name, label)
    lines = []
    try:
        stage2 = project / "02_bioinformatics"
        assays = sorted(d for d in stage2.iterdir() if d.is_dir()) if stage2.is_dir() else []
        for assay in assays:
            for sub in sorted(d for d in assay.iterdir() if d.is_dir()):
                lines.append("- %s: %s" % (sub.name, _closed_status_line(project, sub)))
    except Exception:  # never an exception's text: it can name what the project holds
        return [head]
    return [head] + lines


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
    ap.add_argument("--closed-list", nargs="?", const="", metavar="WORKSPACE",
                    help="print `<name>\\t<label>` per closed project of WORKSPACE (default: this "
                         "one) and nothing else; read by build_projects_index.sh")
    args = ap.parse_args()

    ws = workspace.workspace_root(__file__)
    if args.closed_list is not None:
        for name, label in sorted(closed_labels(args.closed_list or ws).items()):
            if printable(name):  # the index closes an unprintable name itself
                print("%s\t%s" % (name, label))
        return 0

    out = ["# Project state — derived from the filesystem, authority: STATUS + HISTORY.md",
           "(template %s · generated by _system/project_state.py; a render, not a record)"
           % workspace.template_version(ws), ""]

    if args.project:
        # Named and judged by its entry, unresolved, as the full render names it: a symlinked
        # entry of projects/ is that entry (decision 0151).
        projects = [Path(os.path.abspath(args.project))]
        if not projects[0].is_dir():
            print("no such project directory: %s" % args.project, file=sys.stderr)
            return 2
        # Judged in its own workspace when it sits in one; a project the guard cannot judge
        # is closed (decision 0151).
        home = projects[0].parent
        try:
            closed = closed_labels(home.parent) if home.name == "projects" else {}
            if (projects[0].name not in closed
                    and not guard_hook.project_is_public(str(projects[0]))):
                closed[projects[0].name] = "unclassified"
        except Exception:
            closed = None
    else:
        root = ws / "projects"
        projects = sorted(d for d in root.iterdir()
                          if d.is_dir() and not d.name.startswith("_")) if root.is_dir() else []
        if not projects:
            out.append("(no projects yet)")
        try:
            closed = closed_labels(ws)
        except Exception:
            closed = None  # the guard cannot judge: every project is closed

    for p in projects:
        if closed is None or p.name in closed or not printable(p.name):
            # .get: an unprintable name the guard judged public is not in `closed` (0151).
            out.extend(render_closed(p, (closed or {}).get(p.name, "unclassified")))
            out.append("")
            continue
        try:
            out.extend(render_project(p, args.last))
        except Exception as exc:  # a broken project must not hide the others' state
            out.append("## %s — render failed: %s" % (p.name, exc))
        out.append("")
    print("\n".join(out).rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
