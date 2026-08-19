#!/usr/bin/env python3
"""Stage 01 — validate the experimental design and emit workflow-ready samplesheets.

The deterministic core of `01_prepare_samplesheets`. The contract orchestrates; this computes.
See docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md for why.

This script decides what is TRUE. It never prompts, never proceeds past a gate on its own, and
never writes unless told which gate the user cleared. The agent decides what to say and when to
stop.

Stdlib only, on purpose: stages 00 and 01 must run with no conda environment (unlike stage 02).
The consequence is that `_config/<assay>.yaml` is read by a narrow top-level regex for the single
key this stage needs, not by a YAML parser.

Usage
-----
    python3 _system/stage01_samplesheet.py --project <dir> --check
    python3 _system/stage01_samplesheet.py --project <dir> [--confirm-exclusions] [--force]

Emits a single JSON object on stdout. Exit codes:

    0  ok            checked clean, or written
    1  failures      validation failed; nothing written
    2  needs_confirm exclusions present without --confirm-exclusions, or existing
                     samplesheets without --force. Nothing written.
    3  preconditions project or required inputs missing
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

STRANDEDNESS_VALUES = {"auto", "forward", "reverse", "unstranded"}
SAMPLES_HEADER = ["sample_id", "condition", "group", "replicate"]
FILES_HEADER = ["sample_id", "lane", "fastq_1", "fastq_2"]

EXIT_OK, EXIT_FAILURES, EXIT_NEEDS_CONFIRM, EXIT_PRECONDITIONS = 0, 1, 2, 3


# --- reading -----------------------------------------------------------------------------------

def read_csv(path):
    """Read a GARS metadata CSV. Comment lines (files.csv line 1) are skipped.

    Returns (rows, error). Each row carries `_n`, its 1-based line number in the file, so a
    failure can name the line the user must open.
    """
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        return None, f"cannot read {path.name}: {exc}"

    kept = [(i + 1, ln) for i, ln in enumerate(lines) if not ln.lstrip().startswith("#")]
    if not kept:
        return None, f"{path.name} is empty"

    reader = csv.DictReader([ln for _, ln in kept])
    if reader.fieldnames is None:
        return None, f"{path.name} has no header"
    header_line = kept[0][0]
    rows = []
    for row, (lineno, _) in zip(reader, kept[1:]):
        row = {(k.strip() if k else k): (v.strip() if isinstance(v, str) else v)
               for k, v in row.items()}
        row["_n"] = lineno
        rows.append(row)
    return {"rows": rows, "fields": [f.strip() for f in reader.fieldnames],
            "header_line": header_line}, None


def read_strandedness(config_path):
    """Extract the top-level `strandedness:` scalar. Returns (value, error).

    Deliberately narrow: matches only a zero-indent key, so a `strandedness` nested under some
    other mapping is not picked up by accident. Absent file or absent key -> 'auto'.
    """
    if not config_path.is_file():
        return "auto", None
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read {config_path.name}: {exc}"

    match = None
    for line in text.splitlines():
        m = re.match(r"^strandedness:\s*(.*)$", line)
        if m:
            match = m.group(1)
    if match is None:
        return "auto", None

    value = match.split("#", 1)[0].strip().strip("\"'")
    if not value:
        return "auto", None
    if value not in STRANDEDNESS_VALUES:
        return None, (f"strandedness: {value!r} in {config_path.name} is not one of "
                      f"{sorted(STRANDEDNESS_VALUES)}")
    return value, None


# --- validation --------------------------------------------------------------------------------

def fail(check, detail):
    return {"check": check, "detail": detail}


def validate_assay(project, assay):
    """Run every check the contract defines for one assay.

    Returns a dict with failures, exclusions, counts, and the resolved rows needed to write.
    """
    out = {"failures": [], "exclusions": [], "counts": {}}
    fails = out["failures"]

    data_dir = project / "00_data" / assay
    samples, err = read_csv(data_dir / "samples.csv")
    if err:
        return {**out, "failures": [fail("preconditions", err)], "fatal": True}
    files, err = read_csv(data_dir / "files.csv")
    if err:
        return {**out, "failures": [fail("preconditions", err)], "fatal": True}

    for name, got, want in (("samples.csv", samples["fields"], SAMPLES_HEADER),
                            ("files.csv", files["fields"], FILES_HEADER)):
        if got != want:
            fails.append(fail("header", f"{name} header is {got}, expected {want}"))
    if fails:
        return {**out, "fatal": True}

    # -- complete design row
    for row in samples["rows"]:
        blank = [c for c in SAMPLES_HEADER if not row.get(c)]
        if blank:
            fails.append(fail("incomplete_design",
                              f"samples.csv line {row['_n']}: blank {', '.join(blank)}"))

    # -- duplicate sample_id
    seen = {}
    for row in samples["rows"]:
        sid = row["sample_id"]
        if sid and sid in seen:
            fails.append(fail("invalid_design",
                              f"sample_id {sid!r} appears on samples.csv lines "
                              f"{seen[sid]} and {row['_n']}"))
        elif sid:
            seen[sid] = row["_n"]

    # -- duplicate (sample_id, lane)
    seen_fl = {}
    for row in files["rows"]:
        key = (row["sample_id"], row["lane"])
        if key in seen_fl:
            fails.append(fail("invalid_design",
                              f"(sample_id, lane) {key} appears on files.csv lines "
                              f"{seen_fl[key]} and {row['_n']}"))
        else:
            seen_fl[key] = row["_n"]

    # -- layout, then resolvable file rows
    has_r2 = [bool(row.get("fastq_2")) for row in files["rows"]]
    if all(has_r2):
        layout = "paired-end"
    elif not any(has_r2):
        layout = "single-end"
    else:
        layout = "mixed"
        missing = [str(r["_n"]) for r in files["rows"] if not r.get("fastq_2")]
        fails.append(fail("invalid_design",
                          "files.csv mixes paired-end and single-end rows; fastq_2 is blank on "
                          f"line(s) {', '.join(missing)}"))

    for row in files["rows"]:
        for col in ("fastq_1", "fastq_2"):
            rel = row.get(col)
            if not rel:
                continue
            target = project / rel
            if not target.is_file():
                fails.append(fail("unresolvable_path",
                                  f"files.csv line {row['_n']}: {col} {rel!r} does not resolve "
                                  "to a readable file"))

    # -- referential integrity
    sample_ids = [r["sample_id"] for r in samples["rows"] if r["sample_id"]]
    file_ids = {r["sample_id"] for r in files["rows"]}
    for sid in sample_ids:
        if sid not in file_ids:
            fails.append(fail("referential_integrity",
                              f"sample_id {sid!r} is in samples.csv but has no rows in files.csv"))
    included = [s for s in sample_ids if s in file_ids]
    for sid in sorted(file_ids - set(sample_ids)):
        out["exclusions"].append(
            {"sample_id": sid,
             "file_rows": sum(1 for r in files["rows"] if r["sample_id"] == sid)})

    # -- valid design, over included samples only
    incl_rows = [r for r in samples["rows"] if r["sample_id"] in included]
    groups = {}
    for row in incl_rows:
        groups.setdefault(row["group"], []).append(row)
    for gname, grows in sorted(groups.items()):
        distinct = {r["sample_id"] for r in grows}
        if len(distinct) < 2:
            fails.append(fail("invalid_design",
                              f"group {gname!r} contains {len(distinct)} sample; a group of one "
                              "cannot be tested for differential expression"))
    reps = {}
    for row in incl_rows:
        key = (row["group"], row["condition"], row["replicate"])
        if key in reps and reps[key] != row["sample_id"]:
            fails.append(fail("invalid_design",
                              f"replicate {row['replicate']!r} repeats within group "
                              f"{row['group']!r} / condition {row['condition']!r} for samples "
                              f"{reps[key]!r} and {row['sample_id']!r}"))
        else:
            reps[key] = row["sample_id"]

    # -- strandedness
    strandedness, err = read_strandedness(project / "_config" / f"{assay}.yaml")
    if err:
        fails.append(fail("config", err))

    incl_file_rows = [r for r in files["rows"] if r["sample_id"] in included]
    out["counts"] = {
        # "total" is what stage 00 ingested, not what samples.csv lists -- otherwise an
        # exclusion would report "5 of 5" and hide the very thing the user is confirming.
        "samples_total": len(file_ids),
        "samples_included": len(included),
        "samplesheet_rows": len(incl_file_rows),
        "design_rows": len(incl_rows),
        "groups": len(groups),
        "layout": layout,
        "strandedness": strandedness,
    }
    out["_included"] = included
    out["_incl_file_rows"] = incl_file_rows
    out["_incl_design_rows"] = incl_rows
    out["_strandedness"] = strandedness
    out["fatal"] = False
    return out


# --- writing -----------------------------------------------------------------------------------

def write_assay(project, assay, res):
    """Write the samplesheet and design table. Returns (paths, gate_failures)."""
    sheet_dir = project / "01_samplesheets"
    sheet_dir.mkdir(exist_ok=True)
    sheet = sheet_dir / f"{assay}_samplesheet.csv"
    design = sheet_dir / f"{assay}_design.csv"

    with sheet.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["sample", "fastq_1", "fastq_2", "strandedness"])
        for row in res["_incl_file_rows"]:
            # abspath, NOT Path.resolve(). resolve() follows symlinks, and 00_data/<assay>/raw/
            # is entirely symlinks -- so it would write the original sequencing-run path into
            # the samplesheet and bypass the project's own registration of its data. The
            # samplesheet must point at the project, which is why 02.01 warns that moving a
            # project invalidates it.
            r1 = os.path.abspath(project / row["fastq_1"])
            r2 = os.path.abspath(project / row["fastq_2"]) if row.get("fastq_2") else ""
            w.writerow([row["sample_id"], r1, r2, res["_strandedness"]])

    with design.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(SAMPLES_HEADER)
        for row in res["_incl_design_rows"]:
            w.writerow([row[c] for c in SAMPLES_HEADER])

    # Exit gate: re-read what was written. Checks content, not existence -- a file-exists check
    # passes happily on a table with the wrong rows in it (decision 0010).
    gate = []
    back_sheet, err = read_csv(sheet)
    if err:
        gate.append(fail("exit_gate", err))
    elif len(back_sheet["rows"]) != res["counts"]["samplesheet_rows"]:
        gate.append(fail("exit_gate", f"{sheet.name} has {len(back_sheet['rows'])} rows, "
                                      f"expected {res['counts']['samplesheet_rows']}"))
    elif any(not r["fastq_1"] or not Path(r["fastq_1"]).is_absolute()
             for r in back_sheet["rows"]):
        gate.append(fail("exit_gate", f"{sheet.name} contains a blank or non-absolute fastq_1"))
    else:
        proj_abs = os.path.abspath(project)
        outside = [r["fastq_1"] for r in back_sheet["rows"]
                   if not os.path.abspath(r["fastq_1"]).startswith(proj_abs + os.sep)]
        if outside:
            gate.append(fail("exit_gate",
                             f"{sheet.name} points outside the project (symlinks were followed): "
                             + outside[0]))

    back_design, err = read_csv(design)
    if err:
        gate.append(fail("exit_gate", err))
    elif len(back_design["rows"]) != res["counts"]["design_rows"]:
        gate.append(fail("exit_gate", f"{design.name} has {len(back_design['rows'])} rows, "
                                      f"expected {res['counts']['design_rows']}"))
    elif {r["sample_id"] for r in back_design["rows"]} != set(res["_included"]):
        gate.append(fail("exit_gate", f"{design.name} sample_id set does not match the "
                                      "included samples"))

    return [str(sheet.relative_to(project)), str(design.relative_to(project))], gate


def history_entry(assays, results, wrote):
    lines = ["## <ISO-8601 date> — 01_prepare_samplesheets — samplesheets emitted", ""]
    for assay in assays:
        c = results[assay]["counts"]
        excl = results[assay]["exclusions"]
        lines.append(
            f"- **{assay}**: {c['samples_included']} of {c['samples_total']} samples, "
            f"{c['groups']} group(s), {c['layout']}, strandedness `{c['strandedness']}`. "
            f"Wrote {c['samplesheet_rows']} samplesheet rows and {c['design_rows']} design rows.")
        if excl:
            lines.append("  Excluded (raw data and files.csv left untouched): "
                         + ", ".join(e["sample_id"] for e in excl))
    lines += ["", "Files written: " + ", ".join(wrote)]
    return "\n".join(lines)


# --- main --------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True, type=Path,
                    help="path to projects/<project_title>/")
    ap.add_argument("--check", action="store_true",
                    help="validate only; write nothing")
    ap.add_argument("--confirm-exclusions", action="store_true",
                    help="the user has confirmed the excluded samples (contract template T7)")
    ap.add_argument("--force", action="store_true",
                    help="the user has confirmed overwriting existing samplesheets (T5)")
    args = ap.parse_args(argv)

    project = args.project
    result = {"ok": False, "mode": "check" if args.check else "write",
              "project": str(project), "assays": {}, "wrote": []}

    if not project.is_dir():
        result["error"] = f"project directory does not exist: {project}"
        return emit(result, EXIT_PRECONDITIONS)

    data_root = project / "00_data"
    if not data_root.is_dir():
        result["error"] = "00_data/ does not exist; run 00_initialize_project first"
        return emit(result, EXIT_PRECONDITIONS)

    assays = sorted(d.name for d in data_root.iterdir() if d.is_dir())
    if not assays:
        result["error"] = "no assay directories under 00_data/"
        return emit(result, EXIT_PRECONDITIONS)

    missing = [a for a in assays
               if not (data_root / a / "files.csv").is_file()
               or not (data_root / a / "samples.csv").is_file()]
    if missing:
        result["error"] = ("missing files.csv or samples.csv for: " + ", ".join(missing)
                           + "; run 00_initialize_project first")
        result["assays_found"] = assays
        return emit(result, EXIT_PRECONDITIONS)

    results = {a: validate_assay(project, a) for a in assays}
    for assay, res in results.items():
        result["assays"][assay] = {k: v for k, v in res.items() if not k.startswith("_")}

    if any(res["failures"] for res in results.values()):
        return emit(result, EXIT_FAILURES)

    exclusions = {a: r["exclusions"] for a, r in results.items() if r["exclusions"]}
    existing = [p.name for a in assays
                for p in (project / "01_samplesheets" / f"{a}_samplesheet.csv",
                          project / "01_samplesheets" / f"{a}_design.csv")
                if p.is_file()]

    if args.check:
        result["ok"] = True
        result["exclusions_pending"] = bool(exclusions)
        result["existing_outputs"] = existing
        return emit(result, EXIT_OK)

    blocked = []
    if exclusions and not args.confirm_exclusions:
        blocked.append("exclusions present; re-run with --confirm-exclusions once the user has "
                       "confirmed (template T7)")
    if existing and not args.force:
        blocked.append("01_samplesheets/ already contains " + ", ".join(existing)
                       + "; re-run with --force once the user has confirmed (template T5)")
    if blocked:
        result["blocked"] = blocked
        result["existing_outputs"] = existing
        return emit(result, EXIT_NEEDS_CONFIRM)

    gate_failures = []
    for assay in assays:
        paths, gate = write_assay(project, assay, results[assay])
        result["wrote"].extend(paths)
        if gate:
            result["assays"][assay]["failures"].extend(gate)
            gate_failures.extend(gate)

    if gate_failures:
        return emit(result, EXIT_FAILURES)

    result["ok"] = True
    result["history_entry"] = history_entry(assays, results, result["wrote"])
    return emit(result, EXIT_OK)


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
