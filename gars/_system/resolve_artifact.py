#!/usr/bin/env python3
"""Resolve a sub-stage's inputs by artifact type, from the OUTPUTS.tsv of completed sub-stages.

The deterministic core of stage 02's router step 9. Extends
docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md to the one remaining place where a
contract asked the agent to perform a search: "resolve an artifact from the OUTPUTS.tsv of
completed sub-stages" is a lookup with a defined tie-break, not a judgment.

The resolution rule, from _references/artifact_types.md, restated once here as code:

    search the OUTPUTS.tsv of COMPLETED sub-stages in REVERSE sub-stage order and take the first
    `native` match, unless a contract explicitly asks for an `adapted` artifact it produced
    itself. If no match exists, STOP and report -- never regenerate.

Stdlib only; stage 02's router runs before any skill is invoked.

Usage
-----
    resolve_artifact.py --project <dir> --assay <id> --type counts_gene
    resolve_artifact.py --project <dir> --assay <id> --consumes counts_gene design
    resolve_artifact.py --project <dir> --assay <id> --list

Exit codes: 0 resolved / 1 a required type is unresolvable / 3 usage.
"""

import argparse
import json
import sys
from pathlib import Path

EXIT_OK, EXIT_UNRESOLVED, EXIT_USAGE = 0, 1, 3

# Types stage 01 produces, which live outside any sub-stage's OUTPUTS.tsv.
STAGE01 = {"samplesheet": "01_samplesheets/{assay}_samplesheet.csv",
           "design": "01_samplesheets/{assay}_design.csv"}


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


def read_outputs(path):
    """Parse an OUTPUTS.tsv. Comment lines are skipped; malformed rows are reported, not ignored."""
    rows, problems = [], []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = line.split("\t")
        if len(cells) != 3:
            problems.append("%s line %d: expected 3 tab-separated columns, found %d"
                            % (path.name, n, len(cells)))
            continue
        typ, role, rel = (c.strip() for c in cells)
        if role not in ("native", "adapted"):
            problems.append("%s line %d: role %r is not native or adapted" % (path.name, n, role))
            continue
        rows.append({"type": typ, "role": role, "path": rel})
    return rows, problems


def substage_state(d):
    """STATUS is the only authority on completion -- never infer it from output files existing."""
    s = d / "STATUS"
    if not s.is_file():
        return "NOT_STARTED"
    for line in s.read_text(encoding="utf-8").splitlines():
        if line.strip():
            return line.split()[0]
    return "NOT_STARTED"


def collect(project, assay):
    """Every declared artifact, newest sub-stage first. Only COMPLETE sub-stages contribute."""
    base = project / "02_bioinformatics" / assay
    entries, problems, skipped = [], [], []
    if base.is_dir():
        for d in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
            state = substage_state(d)
            if state != "COMPLETE":
                skipped.append({"substage": d.name, "state": state})
                continue
            out = d / "OUTPUTS.tsv"
            if not out.is_file():
                problems.append("%s is COMPLETE but has no OUTPUTS.tsv" % d.name)
                continue
            rows, probs = read_outputs(out)
            problems.extend(probs)
            for r in rows:
                entries.append({**r, "substage": d.name,
                                "resolved": str((d / r["path"]).relative_to(project))})
    return entries, problems, skipped


def resolve(project, assay, wanted, entries, prefer_adapted_from=None):
    """One type -> one artifact, or None with a reason."""
    if wanted in STAGE01:
        rel = STAGE01[wanted].format(assay=assay)
        if (project / rel).is_file():
            return {"type": wanted, "role": "native", "substage": "01_prepare_samplesheets",
                    "resolved": rel, "exists": True}, None
        return None, "stage 01 has not produced %s (%s is missing)" % (wanted, rel)

    if prefer_adapted_from:
        for e in entries:
            if e["type"] == wanted and e["role"] == "adapted" \
                    and e["substage"] == prefer_adapted_from:
                return {**e, "exists": (project / e["resolved"]).exists()}, None

    for e in entries:
        if e["type"] == wanted and e["role"] == "native":
            return {**e, "exists": (project / e["resolved"]).exists()}, None

    adapted = [e for e in entries if e["type"] == wanted]
    if adapted:
        return None, ("only `adapted` artifacts of type %r exist (from %s). Resolution prefers "
                      "`native`; an adaptation is reshaped for one consumer's parser and is not "
                      "authoritative." % (wanted, ", ".join(sorted(e["substage"] for e in adapted))))
    return None, "no completed sub-stage declares an artifact of type %r" % wanted


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--assay", required=True)
    ap.add_argument("--type", help="resolve one type")
    ap.add_argument("--consumes", nargs="*", help="require all of these types (router step 9)")
    ap.add_argument("--list", action="store_true", help="list every declared artifact")
    ap.add_argument("--prefer-adapted-from",
                    help="sub-stage whose own `adapted` artifact its contract asks for")
    args = ap.parse_args(argv)

    if not args.project.is_dir():
        return emit({"ok": False, "error": "no such project: %s" % args.project}, EXIT_USAGE)
    if not (args.type or args.consumes is not None or args.list):
        return emit({"ok": False, "error": "give one of --type, --consumes or --list"}, EXIT_USAGE)

    entries, problems, skipped = collect(args.project, args.assay)
    result = {"ok": False, "assay": args.assay, "problems": problems,
              "skipped_substages": skipped}

    if args.list:
        result["artifacts"] = entries
        result["ok"] = not problems
        return emit(result, EXIT_OK if result["ok"] else EXIT_UNRESOLVED)

    wanted = args.consumes if args.consumes is not None else [args.type]
    resolved, missing = {}, {}
    for w in wanted:
        hit, why = resolve(args.project, args.assay, w, entries, args.prefer_adapted_from)
        if hit:
            resolved[w] = hit
        else:
            missing[w] = why

    result["resolved"] = resolved
    result["missing"] = missing
    absent = {t: h["resolved"] for t, h in resolved.items() if not h.get("exists")}
    if absent:
        result["declared_but_absent"] = absent
    result["ok"] = not missing and not absent and not problems
    return emit(result, EXIT_OK if result["ok"] else EXIT_UNRESOLVED)


if __name__ == "__main__":
    sys.exit(main())
