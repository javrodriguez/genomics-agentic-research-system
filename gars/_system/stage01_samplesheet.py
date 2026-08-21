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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import integrity            # noqa: E402  -- one home for the integrity rule
import workspace as ws     # noqa: E402  -- one home for the template version

RAW_SUFFIXES = (".fastq.gz", ".fq.gz", ".fastq", ".fq")
STRANDEDNESS_VALUES = {"auto", "forward", "reverse", "unstranded"}
SAMPLES_HEADER = ["sample_id", "condition", "group", "replicate"]
FILES_HEADER = ["sample_id", "lane", "fastq_1", "fastq_2"]

# --- samplesheet formats ------------------------------------------------------------------------
# One entry per Assay ID. The samplesheet is whatever the assay's upstream pipeline requires, so
# this is a per-assay fact and must not be shared: `strandedness` is RNA-only, and ChIP-family
# assays need a `control` column that RNA has no use for.
#
# Each column names where its value comes from:
#   sample_id | lane | fastq_1 | fastq_2   a column of files.csv (paths are made absolute)
#   config:<key>                           a top-level key of _config/<Assay ID>.yaml
#   design:<col>                           a column of that sample's samples.csv row
#
# Adding an assay is a row here plus, if it needs one, a validator in CONFIG_RULES -- not a change
# to any function below. An assay with no entry is REFUSED: emitting the RNA layout for an assay
# whose pipeline does not want it produces a samplesheet that validates upstream and means
# something else.
#
# Only rnaseq_bulk is registered, because it is the only assay in the assay map. The four planned
# wrappers (atacseq, chipseq, cutandrun, methylseq) each add an entry when their upstream
# samplesheet contract has been read from that pipeline's own schema -- never guessed from memory.
FORMATS = {
    "rnaseq_bulk": {
        "status": "active",
        "source": "nf-core/rnaseq 3.26.0",
        "columns": [
            ("sample", "sample_id"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
            ("strandedness", "config:strandedness"),
        ],
    },
    # --- planned -------------------------------------------------------------------------------
    # Columns below were read from each pipeline's own assets/schema_input.json at the pinned
    # version on 2026-08-19, not reconstructed from memory. They are `planned`: stage 01 refuses
    # them, because no wrapper exists and none has ever been exercised. Promoting one to `active`
    # is part of building its wrapper -- together with adding the assay to the assay map, which is
    # what actually gates a project being created for it.
    "atacseq_bulk": {
        "status": "planned",
        "source": "nf-core/atacseq 2.1.2 assets/schema_input.json",
        "columns": [
            ("sample", "sample_id"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
            ("replicate", "design:replicate"),
        ],
    },
    "chipseq_bulk": {
        "status": "planned",
        "source": "nf-core/chipseq 2.1.0 assets/schema_input.json",
        # `antibody` and `control` are optional in the schema but not optional biologically --
        # without them the pipeline cannot call peaks against an input. Both need columns
        # samples.csv does not yet carry, which stage 01 reports rather than emitting blank.
        "columns": [
            ("sample", "sample_id"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
            ("replicate", "design:replicate"),
            ("antibody", "design:antibody"),
            ("control", "design:control"),
        ],
    },
    "cutandrun": {
        "status": "planned",
        "source": "nf-core/cutandrun 3.2.2 assets/schema_input.json",
        # Note the different shape: `group` rather than `sample`, and `control` is REQUIRED by the
        # schema. The control points at the IgG sample, where chipseq's points at input chromatin
        # -- same column, different biological referent, which is why validation stays per-assay.
        "columns": [
            ("group", "design:group"),
            ("replicate", "design:replicate"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
            ("control", "design:control"),
        ],
    },
    "methylseq": {
        "status": "planned",
        "source": "nf-core/methylseq 4.2.0 assets/schema_input.json",
        "columns": [
            ("sample", "sample_id"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
        ],
    },
}

# Allowed values and defaults for any `config:` column above, keyed by config key.
CONFIG_RULES = {
    "strandedness": {"values": STRANDEDNESS_VALUES, "default": "auto"},
}

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


def config_columns(fmt):
    """The config keys an assay's samplesheet needs, in column order."""
    return [src.split(":", 1)[1] for _, src in fmt if src.startswith("config:")]


def read_config_scalar(config_path, key):
    """Extract a top-level `<key>:` scalar. Returns (value, error).

    Deliberately narrow: matches only a zero-indent key, so the same name nested under some other
    mapping is not picked up by accident. Absent file or absent key -> the rule's default.
    """
    rule = CONFIG_RULES.get(key, {})
    default = rule.get("default", "")
    if not config_path.is_file():
        return default, None
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, "cannot read %s: %s" % (config_path.name, exc)

    match = None
    for line in text.splitlines():
        m = re.match(r"^%s:\s*(.*)$" % re.escape(key), line)
        if m:
            match = m.group(1)
    if match is None:
        return default, None

    value = match.split("#", 1)[0].strip().strip("\"'")
    if not value:
        return default, None
    allowed = rule.get("values")
    if allowed and value not in allowed:
        return None, ("%s: %r in %s is not one of %s"
                      % (key, value, config_path.name, sorted(allowed)))
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

    spec = FORMATS.get(assay)
    if spec is None:
        active = sorted(a for a, s in FORMATS.items() if s["status"] == "active")
        return {**out, "fatal": True, "failures": [fail(
            "unsupported_assay",
            "no samplesheet format is registered for %r. Active: %s. An assay's samplesheet is "
            "its pipeline's contract and is never inherited from another assay."
            % (assay, ", ".join(active) or "none"))]}
    if spec["status"] != "active":
        return {**out, "fatal": True, "failures": [fail(
            "unsupported_assay",
            "the samplesheet format for %r is registered as %r, read from %s but never exercised. "
            "No wrapper exists for it. Promoting it to active is part of building that wrapper."
            % (assay, spec["status"], spec["source"]))]}
    fmt = spec["columns"]

    data_dir = project / "00_data" / assay
    samples, err = read_csv(data_dir / "samples.csv")
    if err:
        return {**out, "failures": [fail("preconditions", err)], "fatal": True}
    files, err = read_csv(data_dir / "files.csv")
    if err:
        return {**out, "failures": [fail("preconditions", err)], "fatal": True}

    # files.csv is machine-owned and derived from raw/. Nothing re-checked it against raw/ after
    # stage 00 wrote it, so a truncated or edited registry was consumed as truth: one project had
    # files.csv accounting for 40 of 152 linked FASTQs, and stage 01 reported 10 samples with no
    # error because a truncated CSV is still internally consistent. raw/ is the authority.
    raw_dir = data_dir / "raw"
    if raw_dir.is_dir():
        on_disk = {p.name for p in raw_dir.iterdir() if p.name.endswith(RAW_SUFFIXES)}
        listed = set()
        for row in files["rows"]:
            for col in ("fastq_1", "fastq_2"):
                if row.get(col):
                    listed.add(row[col].rsplit("/", 1)[-1])
        unaccounted = on_disk - listed
        vanished = listed - on_disk
        if unaccounted:
            fails.append(fail("registry", "files.csv accounts for %d of %d files in "
                                          "00_data/%s/raw/; %d are unaccounted for (e.g. %s). "
                                          "files.csv is machine-owned and derived from raw/, so "
                                          "this means it is damaged or stale -- regenerate it by "
                                          "re-running stage 00's finalize. Do not treat the "
                                          "missing samples as an intentional exclusion."
                              % (len(listed), len(on_disk), assay, len(unaccounted),
                                 ", ".join(sorted(unaccounted)[:3]))))
        if vanished:
            fails.append(fail("registry", "files.csv names %d file(s) that are no longer in "
                                          "00_data/%s/raw/ (e.g. %s); raw data has been removed "
                                          "since registration"
                              % (len(vanished), assay, ", ".join(sorted(vanished)[:3]))))

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

    # -- config-sourced columns
    config_values = {}
    for key in config_columns(fmt):
        value, err = read_config_scalar(project / "_config" / ("%s.yaml" % assay), key)
        if err:
            fails.append(fail("config", err))
        else:
            config_values[key] = value

    incl_file_rows = [r for r in files["rows"] if r["sample_id"] in included]

    # The cost of verifying what will actually be analysed -- not what was registered. Stage 00
    # links everything the user pointed at; the subset is only known here, after exclusions.
    incl_paths, incl_bytes = [], 0
    for r in incl_file_rows:
        for col in ("fastq_1", "fastq_2"):
            if r.get(col):
                p = project / r[col]
                incl_paths.append((r[col], p))
                if p.is_file():
                    incl_bytes += p.stat().st_size

    design_by_id = {r["sample_id"]: r for r in incl_rows}
    for _, src in fmt:
        if src.startswith("design:"):
            col = src.split(":", 1)[1]
            if col not in SAMPLES_HEADER:
                fails.append(fail("config", "samplesheet format for %s needs a %r column in "
                                            "samples.csv, which stage 00 does not write"
                                            % (assay, col)))

    out["counts"] = {
        # "total" is what stage 00 ingested, not what samples.csv lists -- otherwise an
        # exclusion would report "5 of 5" and hide the very thing the user is confirming.
        "samples_total": len(file_ids),
        "samples_included": len(included),
        "samplesheet_rows": len(incl_file_rows),
        "design_rows": len(incl_rows),
        "groups": len(groups),
        "layout": layout,
        "columns": [c for c, _ in fmt],
        "included_bytes": incl_bytes,
        "included_gb": round(incl_bytes / 1e9, 1),
        "full_check_estimate_min": integrity.estimate_minutes(incl_bytes),
        "full_check_needs_scheduling": integrity.needs_scheduling(incl_bytes),
    }
    out["counts"].update(config_values)
    out["_incl_paths"] = incl_paths
    out["_included"] = included
    out["_incl_file_rows"] = incl_file_rows
    out["_incl_design_rows"] = incl_rows
    out["_format"] = fmt
    out["_config_values"] = config_values
    out["_design_by_id"] = design_by_id
    out["fatal"] = False
    return out


# --- writing -----------------------------------------------------------------------------------

def write_assay(project, assay, res):
    """Write the samplesheet and design table. Returns (paths, gate_failures)."""
    sheet_dir = project / "01_samplesheets"
    sheet_dir.mkdir(exist_ok=True)
    sheet = sheet_dir / f"{assay}_samplesheet.csv"
    design = sheet_dir / f"{assay}_design.csv"

    fmt = res["_format"]
    with ws.atomic_open(sheet) as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow([c for c, _ in fmt])
        for row in res["_incl_file_rows"]:
            out = []
            for _, src in fmt:
                if src in ("fastq_1", "fastq_2"):
                    # abspath, NOT Path.resolve(). resolve() follows symlinks, and
                    # 00_data/<assay>/raw/ is entirely symlinks -- so it would write the original
                    # sequencing-run path into the samplesheet and bypass the project's own
                    # registration of its data. The samplesheet must point at the project, which
                    # is why 02.01 warns that moving a project invalidates it.
                    out.append(os.path.abspath(project / row[src]) if row.get(src) else "")
                elif src.startswith("config:"):
                    out.append(res["_config_values"].get(src.split(":", 1)[1], ""))
                elif src.startswith("design:"):
                    d = res["_design_by_id"].get(row["sample_id"], {})
                    out.append(d.get(src.split(":", 1)[1], ""))
                else:
                    out.append(row.get(src, ""))
            w.writerow(out)

    with ws.atomic_open(design) as fh:
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


def history_entry(assays, results, wrote, verify="none", version="unknown"):
    lines = ["## <ISO-8601 date> — 01_prepare_samplesheets — samplesheets emitted", "",
             # Not only stage 00 stamps this. A workspace can be upgraded between stages, and the
             # per-stage stamp is the only record that this stage ran under a different contract
             # than the one that created the project.
             "Template version: %s" % version,
             "Deep file-integrity verification: `%s`" % verify, ""]
    for assay in assays:
        c = results[assay]["counts"]
        excl = results[assay]["exclusions"]
        extra = "".join(", %s `%s`" % (k, c[k]) for k in sorted(c)
                        if k not in ("samples_included", "samples_total", "groups", "layout",
                                     "samplesheet_rows", "design_rows", "columns"))
        lines.append(
            "- **%s**: %d of %d samples, %d group(s), %s%s. Columns `%s`. "
            "Wrote %d samplesheet rows and %d design rows."
            % (assay, c["samples_included"], c["samples_total"], c["groups"], c["layout"], extra,
               ",".join(c["columns"]), c["samplesheet_rows"], c["design_rows"]))
        if excl:
            lines.append("  Excluded (raw data and files.csv left untouched): "
                         + ", ".join(e["sample_id"] for e in excl))
    lines += ["", "Files written: " + ", ".join(wrote)]
    return "\n".join(lines)


# --- main --------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path,
                    help="path to projects/<project_title>/ (not needed with --list-formats)")
    ap.add_argument("--check", action="store_true",
                    help="validate only; write nothing")
    ap.add_argument("--confirm-exclusions", action="store_true",
                    help="the user has confirmed the excluded samples (contract template T7)")
    ap.add_argument("--force", action="store_true",
                    help="the user has confirmed overwriting existing samplesheets (T5)")
    ap.add_argument("--list-formats", action="store_true",
                    help="print the registered per-assay samplesheet formats and exit")
    ap.add_argument("--verify-integrity", choices=("none", "full"), default="none",
                    help="none (default): trust the files; stage 00 already checked that every "
                         "link resolves and carries gzip magic. full: decompress every INCLUDED "
                         "file before emitting the samplesheet -- the last cheap moment to catch "
                         "a truncated FASTQ. Above ~10 GB submit this with sbatch; it is not "
                         "login-node work.")
    args = ap.parse_args(argv)

    if args.list_formats:
        return emit({"ok": True,
                     "formats": {a: {"status": s["status"], "source": s["source"],
                                     "columns": [{"column": c, "from": src}
                                                 for c, src in s["columns"]]}
                                 for a, s in sorted(FORMATS.items())},
                     "config_rules": {k: {"values": sorted(v["values"]), "default": v["default"]}
                                      for k, v in sorted(CONFIG_RULES.items())}}, EXIT_OK)

    if args.project is None:
        ap.error("--project is required")
    project = args.project
    result = {"ok": False, "mode": "check" if args.check else "write",
              "project": str(project), "assays": {}, "wrote": [],
              "verify_integrity": args.verify_integrity,
              "template_version": ws.template_version(ws.workspace_root(__file__))}

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

    if args.verify_integrity == "full":
        for assay, res in results.items():
            problems = integrity.check_many(res["_incl_paths"], "full")
            for rel, problem in problems:
                # result["assays"][assay] is a shallow copy of res, so this list is the SAME
                # object -- appending to both duplicated every finding.
                res["failures"].append(fail("integrity", "%s %s" % (rel, problem)))
        if any(r["failures"] for r in results.values()):
            return emit(result, EXIT_FAILURES)

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
    result["history_entry"] = history_entry(assays, results, result["wrote"],
                                            args.verify_integrity,
                                            result["template_version"])
    return emit(result, EXIT_OK)


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
