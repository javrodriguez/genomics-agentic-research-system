#!/usr/bin/env python3
"""A stand-in for the GARS stage 00 register, for TheFixtureNamesNoPathOutsideTheRunTree only.

It does the one thing the real script does that this test is about, and nothing else: `create` makes
<workspace>/projects/<title>/, `link` records the --source path it was handed, absolutely, in CONTEXT.md and
HISTORY.md and points one raw/ link per file at it, and `finalize` writes the samples table. The real script
was measured doing exactly that on 13 September 2026 (two file lines and twelve link targets per project).

It exists so the test runs where the real workspace does not: the mutation sandbox copies gars/_system only.
The real stage 00 is built against in the same class, wherever the workspace is complete.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def emit(result: dict, code: int) -> int:
    print(json.dumps(result))
    return code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent.parent)
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("create")
    c.add_argument("--title", required=True)
    c.add_argument("--assays", nargs="+", required=True)
    link = sub.add_parser("link")
    link.add_argument("--project", required=True)
    link.add_argument("--assay", required=True)
    link.add_argument("--source", required=True)
    f = sub.add_parser("finalize")
    f.add_argument("--project", required=True)
    f.add_argument("--date")
    f.add_argument("--model")
    f.add_argument("--integrity")
    args = ap.parse_args()

    if args.cmd == "create":
        project = args.workspace / "projects" / args.title
        if project.exists():
            return emit({"ok": False, "error": "already exists"}, 3)
        project.mkdir(parents=True)
        (project / "CONTEXT.md").write_text(f"# {args.title}\n")
        (project / "HISTORY.md").write_text("# History\n")
        return emit({"ok": True, "project": str(project)}, 0)
    if args.cmd == "link":
        project, source = Path(args.project), Path(args.source)
        if not project.is_dir() or not source.is_dir():
            return emit({"ok": False, "error": "no such project or source"}, 3)
        raw = project / "00_data" / args.assay / "raw"
        raw.mkdir(parents=True)
        files = sorted(p for p in source.iterdir() if p.name.endswith(".fastq.gz"))
        for p in files:
            (raw / p.name).symlink_to(p)
        row = f"| {args.assay} | `{source}` | {len(files)} |\n"
        for name in ("CONTEXT.md", "HISTORY.md"):
            with (project / name).open("a") as fh:
                fh.write(row)
        return emit({"ok": True, "linked": len(files)}, 0)
    if args.cmd == "finalize":
        project = Path(args.project)
        for data in (project / "00_data").iterdir():
            (data / "samples.csv").write_text("sample_id,condition\n")
        return emit({"ok": True}, 0)
    return emit({"ok": False, "error": "no command"}, 2)


if __name__ == "__main__":
    sys.exit(main())
