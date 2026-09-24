#!/usr/bin/env python3
"""Stage 01 — validate the experimental design and emit workflow-ready samplesheets.

The deterministic core of `01_prepare_samplesheets`. The contract orchestrates; this computes.
See docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md for why.

This script decides what is TRUE. It never prompts, never proceeds past a gate on its own, and
never writes unless told which gate the user cleared. The agent decides what to say and when to
stop.

Stdlib only, on purpose: stages 00 and 01 must run with no conda environment (unlike stage 02).
The consequence is that `_config/<assay>.yaml` is read by a narrow top-level regex for the top-level
scalars this stage needs, not by a YAML parser.

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
import gzip
from collections import Counter
from statistics import median
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import integrity            # noqa: E402  -- one home for the integrity rule
import workspace as ws     # noqa: E402  -- one home for the template version

# Pre-committed in decision 0101; never tuned to a run.
SEX_PROPORTION_THRESHOLD = 0.5
AGE_MEDIAN_THRESHOLD = 10

RAW_SUFFIXES = (".fastq.gz", ".fq.gz", ".fastq", ".fq")
STRANDEDNESS_VALUES = {"auto", "forward", "reverse", "unstranded"}
# The base design columns; the full set is per-assay via ws.design_columns() (decision 0030).
SAMPLES_HEADER = ws.BASE_DESIGN_COLUMNS


def path_column(assay):
    """The emitted samplesheet column carrying the input path, per input kind.

    The exit gate checks that this column is present, absolute and inside the project. It was
    hardcoded to `fastq_1` while every assay was FASTQ-shaped; a directory assay carries the
    path in `spaceranger_dir` instead, and a gate that checked the wrong column would have
    passed a samplesheet whose paths were all blank."""
    return "spaceranger_dir" if ws.input_kind(assay) == "sample_dir" else "fastq_1"
# The FASTQ-assay header. It is no longer the only one -- an assay whose unit of input is a
# directory carries its own (workspace.FILES_HEADERS), so the expected header is looked up per
# assay rather than assumed. Kept as a name because the comment block below cites it.
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
# All five assays are registered and active (decisions 0028, 0031); each entry's columns were
# read from its pipeline's own assets/schema_input.json at the pinned version -- never guessed
# from memory. A future assay adds an entry the same way, together with its wrapper.
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
    # --- the wrapper-backed assays (0028, 0031) ------------------------------------------------
    "atacseq_bulk": {
        # Promoted 2026-08-25 with wrapper #1; SEMANTICS corrected 2026-08-28 (decision 0035,
        # found by live run 26863963): the pipeline's `sample` column is the GROUP -- rows
        # repeat it per biological replicate, and its checker enforces replicate ids 1..N
        # within each. Emitting sample_id made every replicate its own group. Control columns
        # exist in the schema but are for ChIP-style designs and stay out of the ATAC emitter.
        "status": "active",
        "source": "nf-core/atacseq 2.1.2 assets/schema_input.json + bin/check_samplesheet.py",
        "columns": [
            ("sample", "design:group"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
            ("replicate", "design:replicate"),
        ],
    },
    "chipseq_bulk": {
        # Promoted 2026-08-25 with wrapper #3 (decision 0031). samples.csv carries antibody
        # and control for this assay (decision 0030); control_replicate is DERIVED -- the
        # replicate of the referenced control sample -- because a value a script can compute
        # is never typed by a user (decision 0011).
        # SEMANTICS corrected 2026-08-28 (decision 0035): `sample` is the GROUP, and the
        # samplesheet's `control` names the control's GROUP (matched with control_replicate) --
        # the design's `control` still points at a sample_id (0030), and the emitter translates
        # it to that row's group. A group must be antibody-homogeneous: IP and input can no
        # longer share one (corrects 0030's shared-group clause; see 0035).
        "status": "active",
        "source": "nf-core/chipseq 2.1.0 assets/schema_input.json + bin/check_samplesheet.py",
        "columns": [
            ("sample", "design:group"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
            ("replicate", "design:replicate"),
            ("antibody", "design:antibody"),
            ("control", "lookup:control_group"),
            ("control_replicate", "lookup:control_replicate"),
        ],
    },
    "cutandrun": {
        # Promoted 2026-08-25 with wrapper #4 (decision 0031). `control` names the IgG GROUP,
        # not a sample_id (decision 0030) -- nf-core/cutandrun matches target rows to control
        # rows by group.
        "status": "active",
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
        # Promoted 2026-08-25 with wrapper #5 (decision 0031).
        "status": "active",
        "source": "nf-core/methylseq 4.2.0 assets/schema_input.json",
        "columns": [
            ("sample", "sample_id"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
        ],
    },
    "spatialvi": {
        # Promoted 2026-08-29 with wrapper #7 (decision 0040). Read from the pinned checkout's
        # assets/schema_input.json + docs/usage.md at commit ccdfb48.
        #
        # This is the DOWNSTREAM mode: the input is a Space Ranger output directory per sample,
        # already produced by whoever ran the instrument. The raw mode would have GARS run
        # Space Ranger itself, which needs the proprietary 10x binary, 64 GB, 8 threads and
        # supports human and mouse only -- the same exclusion already made for the cellranger
        # aligners in scrnaseq.
        #
        # Two columns, and the second is a DIRECTORY. That is why this assay's files.csv
        # carries a different header (workspace.FILES_HEADERS): a directory in a column named
        # `fastq_1` would have been a smaller change and a lie.
        "status": "active",
        "source": "nf-core/spatialvi ccdfb48 assets/schema_input.json + docs/usage.md",
        "columns": [
            ("sample", "sample_id"),
            ("spaceranger_dir", "spaceranger_dir"),
        ],
    },
    "scrnaseq": {
        # Promoted 2026-08-29 with wrapper #6 (decision 0040). Read from the pinned
        # checkout's assets/schema_input.json: `sample` carries meta: ["id"], so it is the
        # SAMPLE ID -- not the group. This is the opposite of the ATAC/ChIP-family sheets
        # (decision 0035), where `sample` is the group and rows repeat per replicate;
        # emitting a group here would silently merge replicates into one barcode space.
        # `fastq_barcode`, `expected_cells`, `seq_center`, `sample_type` and `feature_type`
        # are optional in the schema and are deliberately not emitted: none is derivable
        # from the design table, and an unfilled optional column is worse than an absent one.
        "status": "active",
        "source": "nf-core/scrnaseq 4.2.0 assets/schema_input.json",
        "columns": [
            ("sample", "sample_id"),
            ("fastq_1", "fastq_1"),
            ("fastq_2", "fastq_2"),
        ],
    },
}

# Allowed values and defaults for any `config:` column above, keyed by config key.
CONFIG_RULES = {
    "strandedness": {"values": STRANDEDNESS_VALUES, "default": ""},
    "unit_of_replication": {"values": {"sample", "subject", "cell_pseudobulk"}, "default": ""},
    "paired": {"values": {"paired", "unpaired"}, "default": ""},
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
        row = {(k.strip().lower() if k else k): (v.strip() if isinstance(v, str) else v)
               for k, v in row.items()}
        row["_n"] = lineno
        rows.append(row)
    return {"rows": rows, "fields": [f.strip().lower() for f in reader.fieldnames],
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
    if not value or value.lower() in ("null", chr(126)) or value.startswith("<REQUIRED"):
        return default, None
    allowed = rule.get("values")
    if allowed and value not in allowed:
        return None, ("%s: %r in %s is not one of %s"
                      % (key, value, config_path.name, sorted(allowed)))
    return value, None


def declaration_record(project, assay):
    """Record config origin by comparison with the stage-00 seed, not inferred authorship."""
    config = project / "_config" / (assay + ".yaml")
    seed = Path(__file__).resolve().parent.parent / "_templates/config" / (assay + ".yaml")
    history = project / "HISTORY.md"
    lines = history.read_text(encoding="utf-8").splitlines() if history.is_file() else []
    entries = {}
    keys = ["unit_of_replication", "reference_release", "paired"]
    if assay == "rnaseq_bulk":
        keys.append("strandedness")
    for key in keys:
        value, _ = read_config_scalar(config, key)
        def raw_scalar(path):
            matches = re.findall(r"^" + key + r":[ \t]*([^\n]*)", path.read_text(encoding="utf-8"), re.M) if path.is_file() else []
            return matches[-1].split("#", 1)[0].strip().strip("\"'") if matches else None
        raw, seeded = raw_scalar(config), raw_scalar(seed)
        provenance = ("seeded_default" if seeded is not None and raw == seeded else
                      "declared_in_config") if raw is not None else "absent"
        # HISTORY format: optional prefix ending in horizontal whitespace,
        # key: value, then a semicolon-delimited comment or end of line.
        # Compare the whole scalar: punctuation is part of a release value.
        pattern = re.compile(r"(?:^|[ \t])" + re.escape(key) + r":[ \t]*" +
                             re.escape(value) + r"[ \t]*(?:;|$)") if value else None
        history_ref = next(("HISTORY.md:%d: %s" % (n, line)
                            for n, line in reversed(list(enumerate(lines, 1)))
                            if pattern and pattern.search(line)), None)
        entries[key] = {"value": value, "provenance": provenance, "history_ref": history_ref}
    return entries


# --- validation --------------------------------------------------------------------------------

def fail(check, detail):
    return {"check": check, "detail": detail}


def validate_assay(project, assay):
    """Run every check the contract defines for one assay.

    Returns a dict with failures, exclusions, counts, and the resolved rows needed to write.
    """
    out = {"failures": [], "exclusions": [], "counts": {}}
    fails = out["failures"]
    checks = []
    checkpoint = [None, 0]

    def begin(name):
        if checkpoint[0] is not None:
            findings = fails[checkpoint[1]:]
            checks.append({"check": checkpoint[0], "outcome": "fail" if findings else "pass",
                           "failures": list(findings)})
        checkpoint[:] = [name, len(fails)]

    begin("inputs")

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

    begin("registry")
    # files.csv is machine-owned and derived from raw/. Nothing re-checked it against raw/ after
    # stage 00 wrote it, so a truncated or edited registry was consumed as truth: one project had
    # files.csv accounting for 40 of 152 linked FASTQs, and stage 01 reported 10 samples with no
    # error because a truncated CSV is still internally consistent. raw/ is the authority.
    raw_dir = data_dir / "raw"
    kind = ws.input_kind(assay)
    if raw_dir.is_dir():
        # The same reconciliation for both input kinds -- raw/ is the authority -- but the
        # unit differs: FASTQ files for a fastq assay, per-sample directories (or tarballs of
        # one) for a sample_dir assay, which is how spatial data arrives.
        if kind == "sample_dir":
            on_disk = {p.name for p in raw_dir.iterdir()
                       if p.is_dir() or p.name.endswith((".tar.gz", ".tgz"))}
            cols = ("spaceranger_dir",)
        else:
            on_disk = {p.name for p in raw_dir.iterdir() if p.name.endswith(RAW_SUFFIXES)}
            cols = ("fastq_1", "fastq_2")
        listed = set()
        for row in files["rows"]:
            for col in cols:
                if row.get(col):
                    listed.add(row[col].rsplit("/", 1)[-1])
        unaccounted = on_disk - listed
        vanished = listed - on_disk
        if unaccounted:
            fails.append(fail("registry",
                              "files.csv accounts for %d of the %d files in 00_data/%s/raw/; %d "
                              "are unaccounted for (e.g. %s).\n"
                              "files.csv is stage 00's record of everything registered -- it is "
                              "not how a cohort is narrowed, and editing it is not the way to "
                              "select samples.\n"
                              "To analyse a subset, delete rows from samples.csv ONLY. Stage 01 "
                              "then reports the dropped samples as exclusions and asks you to "
                              "confirm them, and the raw data stays linked so the choice is "
                              "reversible.\n"
                              "To fix this now: re-run stage 00's `finalize`. It rebuilds "
                              "files.csv from raw/ and does NOT touch samples.csv, so a design "
                              "you have already filled in is preserved."
                              % (len(listed), len(on_disk), assay, len(unaccounted),
                                 ", ".join(sorted(unaccounted)[:3]))))
        if vanished:
            fails.append(fail("registry", "files.csv names %d file(s) that are no longer in "
                                          "00_data/%s/raw/ (e.g. %s); raw data has been removed "
                                          "since registration"
                              % (len(vanished), assay, ", ".join(sorted(vanished)[:3]))))

    begin("header")
    header = ws.design_columns(assay)
    for name, got, want in (("samples.csv", samples["fields"], header),
                            ("files.csv", files["fields"], ws.files_header(assay))):
        # R-072: batch is a design covariate, not a sample identifier. Preserve it
        # through emission; subject follows owner ruling 0043. Other roles remain unspecified.
        if name == "samples.csv" and assay in ("rnaseq_bulk", "atacseq_bulk"):
            want = header + got[len(header):]
            if len(got) != len(set(got)):
                want = header
        if got != want:
            fails.append(fail("header", f"{name} header is {got}, expected {want}"))
    if fails:
        return {**out, "fatal": True}

    begin("complete_design")
    # -- complete design row. The BASE columns must be filled; an assay's extra columns may be
    # blank at this grain -- a ChIP input or an IgG sample legitimately has no `control` of its
    # own. What a non-blank `control` must do is resolve (below); whether every target sample
    # HAS one is the assay wrapper's check, against its own pipeline's semantics (decision 0030).
    for row in samples["rows"]:
        blank = [c for c in SAMPLES_HEADER if not row.get(c)]
        if blank:
            fails.append(fail("incomplete_design",
                              f"samples.csv line {row['_n']}: blank {', '.join(blank)}"))
    if "control" in header:
        # Same column shape, different biological referent (decision 0030): chipseq's control
        # names the input-chromatin SAMPLE, cutandrun's names the IgG GROUP.
        referent = "group" if assay == "cutandrun" else "sample_id"
        valid = {r[referent] for r in samples["rows"] if r.get(referent)}
        for row in samples["rows"]:
            ctrl = row.get("control", "")
            if ctrl and ctrl not in valid:
                fails.append(fail("referential_integrity",
                                  f"samples.csv line {row['_n']}: control {ctrl!r} is not a "
                                  f"{referent} in this design"))

    begin("duplicate_sample_id")
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

    begin("input_units_layout_paths")
    # -- duplicate input units, and the layout. Both are per input kind: a fastq assay's unit
    # is (sample_id, lane) and its layout is a pairing question; a sample_dir assay's unit is
    # the sample itself, there is no lane and no pairing, and the input is a DIRECTORY -- so
    # is_file() would reject every valid row.
    if kind == "sample_dir":
        seen = {}
        for row in files["rows"]:
            sid = row["sample_id"]
            if sid in seen:
                fails.append(fail("invalid_design",
                                  f"sample_id {sid!r} appears on files.csv lines "
                                  f"{seen[sid]} and {row['_n']}; one directory per sample"))
            else:
                seen[sid] = row["_n"]
        layout = "sample-dir"
        for row in files["rows"]:
            rel = row.get("spaceranger_dir")
            if not rel:
                fails.append(fail("invalid_design",
                                  f"files.csv line {row['_n']}: spaceranger_dir is blank"))
                continue
            target = project / rel
            if not target.is_dir() and not target.is_file():
                fails.append(fail("unresolvable_path",
                                  f"files.csv line {row['_n']}: spaceranger_dir {rel!r} does "
                                  "not resolve to a directory or archive"))
    else:
        seen_fl = {}
        for row in files["rows"]:
            key = (row["sample_id"], row["lane"])
            if key in seen_fl:
                fails.append(fail("invalid_design",
                                  f"(sample_id, lane) {key} appears on files.csv lines "
                                  f"{seen_fl[key]} and {row['_n']}"))
            else:
                seen_fl[key] = row["_n"]

        has_r2 = [bool(row.get("fastq_2")) for row in files["rows"]]
        if all(has_r2):
            layout = "paired-end"
        elif not any(has_r2):
            layout = "single-end"
        else:
            layout = "mixed"
            missing = [str(r["_n"]) for r in files["rows"] if not r.get("fastq_2")]
            fails.append(fail("invalid_design",
                              "files.csv mixes paired-end and single-end rows; fastq_2 is "
                              f"blank on line(s) {', '.join(missing)}"))

        for row in files["rows"]:
            for col in ("fastq_1", "fastq_2"):
                rel = row.get(col)
                if not rel:
                    continue
                target = project / rel
                if not target.is_file():
                    fails.append(fail("unresolvable_path",
                                      f"files.csv line {row['_n']}: {col} {rel!r} does not "
                                      "resolve to a readable file"))

    begin("referential_integrity")
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
    declarations = {}
    if assay in ("rnaseq_bulk", "atacseq_bulk"):
        for key in ("unit_of_replication", "reference_release", "paired"):
            begin(key + "_declaration")
            value, err = read_config_scalar(project / "_config" / (assay + ".yaml"), key)
            declarations[key] = value
            if err:
                fails.append(fail("config", err))
            elif not value and key != "paired":
                fails.append(fail(key + "_undeclared", key + " must be declared in _config/" + assay + ".yaml"))
        begin("subject_requirement")
        if declarations["unit_of_replication"] == "subject" and "subject" not in samples["fields"]:
            fails.append(fail("subject_undeclared", "unit_of_replication subject requires a subject column"))
        if "subject" in samples["fields"]:
            begin("subject_nesting")
            subjects = {}
            for row in incl_rows:
                if not row.get("subject"):
                    fails.append(fail("subject_undeclared", "subject is blank for " + row["sample_id"]))
                else:
                    subjects.setdefault(row["subject"], set()).add(row["condition"])
            for subject, conditions in sorted(subjects.items()):
                if len(conditions) > 1 and declarations["paired"] != "paired":
                    fails.append(fail("subject_nesting", "subject %r appears in more than one condition; declare paired: paired for a paired design" % subject))
    out["design_check"] = {**declarations, "checks": []}
    if assay in ("rnaseq_bulk", "atacseq_bulk"):
        out["design_check"]["declarations"] = declaration_record(project, assay)
        if declarations["paired"] == "paired" and out["design_check"]["declarations"]["paired"]["history_ref"] is None:
            out["design_check"]["provenance_warning"] = "paired declared without a HISTORY entry quoting the user"
    if assay in ("rnaseq_bulk", "atacseq_bulk") and "batch" in samples["fields"]:
        begin("batch_confounding")
        by_batch = {}
        for row in incl_rows:
            if not row.get("batch"):
                fails.append(fail("incomplete_design", "batch is blank for " + row["sample_id"]))
            by_batch.setdefault(row.get("batch", ""), set()).add(row["condition"])
        if (len({r["condition"] for r in incl_rows}) > 1 and by_batch
                and all(len(levels) == 1 for levels in by_batch.values())):
            fails.append(fail("confounded_condition",
                              "batch perfectly confounded with condition; batch cannot "
                              "be separated from the condition effect (R-072)"))
    # Row 8 optional metadata checks. IDs and lanes never increase replication.
    if assay in ("rnaseq_bulk", "atacseq_bulk"):
        arms = {}
        for row in incl_rows:
            arms.setdefault(row["condition"], []).append(row)
        if "cell_barcode" in samples["fields"]:
            begin("cell_replication")
            fails.append(fail("pseudoreplication", "cell-level rows have no registered pseudobulk path"))
        unit = ("subject" if "subject" in samples["fields"] else
                "biological_unit" if "biological_unit" in samples["fields"] else None)
        if unit:
            begin("biological_replication")
            if any(len(rows) >= 2 and len({r.get(unit, "") for r in rows}) < 2
                   for rows in arms.values()):
                fails.append(fail("pseudoreplication", "fewer than two independent biological units in an arm"))
        covariates = {}
        flags = []
        if "sex" in samples["fields"]:
            known = {arm: [r["sex"] for r in rows if r.get("sex") in ("F", "M")]
                     for arm, rows in arms.items()}
            sets = [set(values) for values in known.values()]
            confounded = (len(sets) > 1 and all(len(v) == 1 for v in sets)
                          and len(set(next(iter(v)) for v in sets)) == len(sets))
            covariates["sex"] = "checked" if any(known.values()) else "not_checkable"
            if confounded:
                begin("sex_confounding")
                fails.append(fail("confounded_condition", "sex perfectly confounded with condition"))
            else:
                proportions = [float(v.count("F")) / len(v) for v in known.values() if v]
                if proportions and max(proportions) - min(proportions) >= SEX_PROPORTION_THRESHOLD:
                    flags.append({"check": "covariate_imbalance", "disposition": "DEGRADE",
                                  "detail": "sex: female proportion differs by at least 0.5"})
        if "age" in samples["fields"]:
            ages = []
            for rows in arms.values():
                values = [float(r["age"]) for r in rows if r.get("age")]
                if values:
                    ages.append(median(values))
            covariates["age"] = "checked" if ages else "not_checkable"
            if ages and max(ages) - min(ages) >= AGE_MEDIAN_THRESHOLD:
                flags.append({"check": "covariate_imbalance", "disposition": "DEGRADE",
                              "detail": "age: arm medians differ by at least 10 years"})
        if covariates:
            out["design_check"]["covariates"] = covariates
            out["design_check"]["flags"] = flags

    # Keep unavailable label checking explicit in CLI JSON, including column absence.
    out["sample_label_check"] = {"outcome": "not_checkable"}
    if "library_index" in samples["fields"]:
        mismatched, checkable = 0, True
        for sample in incl_rows:
            indexes = Counter()
            for row in files["rows"]:
                if row["sample_id"] != sample["sample_id"]:
                    continue
                for col in ("fastq_1", "fastq_2"):
                    if not row.get(col):
                        continue
                    path = project / row[col]
                    try:
                        opener = gzip.open if str(path).endswith(".gz") else open
                        with opener(str(path), "rb") as fh:
                            for _ in range(1000):
                                header = fh.readline()
                                if not header:
                                    break
                                rest = [fh.readline() for _ in range(3)]
                                parts = header.decode("ascii", errors="replace").strip().split()
                                if (len(parts) != 2 or len(parts[0].split(":")) != 7
                                        or not re.fullmatch(r"[12]:[YN]:[0-9]+:[ACGTN]+(?:\+[ACGTN]+)?", parts[1])):
                                    checkable = False
                                    continue
                                indexes[parts[1].rsplit(":", 1)[1]] += 1
                    except (OSError, EOFError):
                        checkable = False
            if not indexes:
                checkable = False
            elif indexes.most_common(1)[0][0] != sample.get("library_index"):
                mismatched += 1
        if mismatched:
            begin("sample_label_check")
            fails.append(fail("sample_label_mismatch",
                              "sample_label_mismatch: %d mismatched samples" % mismatched))
            out["sample_label_check"]["outcome"] = "fail"
        elif checkable:
            out["sample_label_check"]["outcome"] = "pass"

    if assay == "atacseq_bulk":
        begin("atac_replication")
        levels = {}
        for row in incl_rows:
            levels.setdefault(row["condition"], set()).add(row["sample_id"])
        for level, ids in sorted(levels.items()):
            if len(ids) < 2:
                fails.append(fail("insufficient_biological_replicates",
                                  "condition %r has %d biological sample(s); at least 2 "
                                  "per level required (R-143)" % (level, len(ids))))
    begin("group_and_replicate_design")
    out["_design_fields"] = samples["fields"]
    groups = {}
    for row in incl_rows:
        groups.setdefault(row["group"], []).append(row)
    # Group SIZE matters only where groups feed a statistical comparison. For rnaseq that is
    # the DE stage; for cutandrun a group IS the pipeline's sample unit and a one-sample group
    # (an IgG control) is normal; ChIP/methyl groups are organisational only; ATAC has a condition floor above.
    if assay == "rnaseq_bulk":
        for gname, grows in sorted(groups.items()):
            distinct = {r["sample_id"] for r in grows}
            if len(distinct) < 2:
                fails.append(fail("invalid_design",
                                  f"group {gname!r} contains {len(distinct)} sample; a group "
                                  "of one cannot be tested for differential expression"))
    # Replicate identity is per-assay. For the group-as-sample assays (0035: atacseq, chipseq,
    # cutandrun -- the pipeline's `sample`/`group` column IS the group, and its checker demands
    # replicate ids exactly 1..N within each), (group, replicate) must be unique outright and
    # contiguous from 1, and a chipseq group must be antibody-homogeneous: IP and input can no
    # longer share a group (corrects 0030's shared-group clause -- under group emission they
    # would merge into one pipeline sample). Enforced HERE so the refusal lands at stage 01,
    # not an hour into a Slurm job. Other assays keep the 0030 key.
    if assay in ("atacseq_bulk", "chipseq_bulk", "cutandrun"):
        for row in incl_rows:
            r = str(row["replicate"])
            if not (r and all("0" <= ch <= "9" for ch in r) and int(r) > 0):
                fails.append(fail("invalid_design",
                                  f"sample {row['sample_id']!r}: replicate {r!r} is not a "
                                  "positive integer -- the pipeline's checker requires "
                                  "integer replicate ids (0035)"))
        reps = {}
        for row in incl_rows:
            key = (row["group"], row["replicate"])
            if key in reps:
                fails.append(fail("invalid_design",
                                  f"replicate {row['replicate']!r} repeats within group "
                                  f"{row['group']!r} for samples {reps[key]!r} and "
                                  f"{row['sample_id']!r} -- the pipeline's sample unit is the "
                                  "group, so (group, replicate) must be unique (0035)"))
            else:
                reps[key] = row["sample_id"]
        for gname, grows in sorted(groups.items()):
            ids = sorted({int(r["replicate"]) for r in grows if str(r["replicate"]).isdigit()})
            if ids and (ids[0] != 1 or ids[-1] != len(ids)):
                fails.append(fail("invalid_design",
                                  f"group {gname!r} has replicate ids {ids}; the pipeline "
                                  "requires exactly 1..N within each group (0035)"))
        if assay == "chipseq_bulk":
            for gname, grows in sorted(groups.items()):
                abs_ = {r.get("antibody", "") for r in grows}
                if len(abs_) > 1:
                    fails.append(fail("invalid_design",
                                      f"group {gname!r} mixes antibody values {sorted(abs_)}; "
                                      "a group is one pipeline sample, so IP and input need "
                                      "their own groups (0035, corrects 0030)"))
    else:
        identity_extras = [c for c in ws.design_columns(assay)
                           if c not in ("sample_id", "condition", "group", "replicate",
                                        "control")]
        reps = {}
        for row in incl_rows:
            key = tuple([row["group"], row["condition"], row["replicate"]]
                        + [row.get(c, "") for c in identity_extras])
            if key in reps and reps[key] != row["sample_id"]:
                fails.append(fail("invalid_design",
                                  f"replicate {row['replicate']!r} repeats within group "
                                  f"{row['group']!r} / condition {row['condition']!r} for "
                                  f"samples {reps[key]!r} and {row['sample_id']!r}"
                                  + (f" (same {'/'.join(identity_extras)})"
                                     if identity_extras else "")))
            else:
                reps[key] = row["sample_id"]

    begin("samplesheet_config")
    # -- config-sourced columns
    config_values = {}
    for key in config_columns(fmt):
        value, err = read_config_scalar(project / "_config" / ("%s.yaml" % assay), key)
        if err:
            fails.append(fail("config", err))
        elif key == "strandedness" and not value:
            fails.append(fail("strandedness_undeclared",
                              "RNA strandedness must be declared in _config/%s.yaml; "
                              "explicit auto remains accepted pending D-24" % assay))
        else:
            config_values[key] = value

    incl_file_rows = [r for r in files["rows"] if r["sample_id"] in included]

    # The cost of verifying what will actually be analysed -- not what was registered. Stage 00
    # links everything the user pointed at; the subset is only known here, after exclusions.
    incl_paths, incl_bytes = [], 0
    size_cols = ("spaceranger_dir",) if kind == "sample_dir" else ("fastq_1", "fastq_2")
    for r in incl_file_rows:
        for col in size_cols:
            if r.get(col):
                p = project / r[col]
                incl_paths.append((r[col], p))
                if p.is_file():
                    incl_bytes += p.stat().st_size
                elif p.is_dir():
                    # A Space Ranger tree: size is the sum of what is in it. Reported so the
                    # integrity estimate stays honest rather than showing 0 GB.
                    incl_bytes += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

    begin("format_sources")
    design_by_id = {r["sample_id"]: r for r in incl_rows}
    for _, src in fmt:
        if src.startswith("design:"):
            col = src.split(":", 1)[1]
            if col not in ws.design_columns(assay):
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

    # Which scientific decisions the user has still not made. Stage 00 seeds _config/ with every
    # derivable value filled and the rest marked <REQUIRED>, so an unfilled marker is a decision
    # outstanding -- not an error here (stage 02 needs them, this stage does not), but the thing
    # to name in the handoff instead of pointing at a 91-line schema.
    cfg = project / "_config" / (assay + ".yaml")
    unfilled = []
    if cfg.is_file():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            if "<REQUIRED" in line and not line.lstrip().startswith("#"):
                unfilled.append(line.split(":", 1)[0].strip())
    out["config_unfilled"] = unfilled
    out["_incl_paths"] = incl_paths
    out["_included"] = included
    out["_incl_file_rows"] = incl_file_rows
    out["_incl_design_rows"] = incl_rows
    out["_format"] = fmt
    out["_config_values"] = config_values
    out["_design_by_id"] = design_by_id
    begin(None)
    out["design_check"]["checks"] = checks
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
                if src in ("fastq_1", "fastq_2", "spaceranger_dir"):
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
                elif src == "lookup:control_replicate":
                    # Derived, never typed: the replicate of the design row this row's
                    # control points at. Blank when the row has no control (it IS one).
                    d = res["_design_by_id"].get(row["sample_id"], {})
                    ctrl = d.get("control", "")
                    out.append(res["_design_by_id"].get(ctrl, {}).get("replicate", "")
                               if ctrl else "")
                elif src == "lookup:control_group":
                    # Derived (0035): the pipeline matches controls by GROUP + replicate, the
                    # design points at a sample_id -- emit the referenced row's group.
                    d = res["_design_by_id"].get(row["sample_id"], {})
                    ctrl = d.get("control", "")
                    out.append(res["_design_by_id"].get(ctrl, {}).get("group", "")
                               if ctrl else "")
                else:
                    out.append(row.get(src, ""))
            w.writerow(out)

    with ws.atomic_open(design) as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(res["_design_fields"])
        for row in res["_incl_design_rows"]:
            w.writerow([row.get(c, "") for c in res["_design_fields"]])

    record = sheet_dir / f"{assay}_design_check.json"
    with ws.atomic_open(record) as fh:
        json.dump(res["design_check"], fh, indent=2, sort_keys=True)
        fh.write("\n")

    # Exit gate: re-read what was written. Checks content, not existence -- a file-exists check
    # passes happily on a table with the wrong rows in it (decision 0010).
    gate = []
    try:
        if json.loads(record.read_text(encoding="utf-8")) != res["design_check"]:
            gate.append(fail("exit_gate", record.name + " does not match the design-check result"))
    except (OSError, ValueError) as exc:
        gate.append(fail("exit_gate", record.name + ": " + str(exc)))
    pathcol = path_column(assay)
    back_sheet, err = read_csv(sheet)
    if err:
        gate.append(fail("exit_gate", err))
    elif len(back_sheet["rows"]) != res["counts"]["samplesheet_rows"]:
        gate.append(fail("exit_gate", f"{sheet.name} has {len(back_sheet['rows'])} rows, "
                                      f"expected {res['counts']['samplesheet_rows']}"))
    elif any(not r[pathcol] or not Path(r[pathcol]).is_absolute()
             for r in back_sheet["rows"]):
        gate.append(fail("exit_gate",
                         f"{sheet.name} contains a blank or non-absolute {pathcol}"))
    else:
        proj_abs = os.path.abspath(project)
        outside = [r[pathcol] for r in back_sheet["rows"]
                   if not os.path.abspath(r[pathcol]).startswith(proj_abs + os.sep)]
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

    return [str(sheet.relative_to(project)), str(design.relative_to(project)), str(record.relative_to(project))], gate


def history_entry(assays, results, wrote, verify="none", version="unknown",
                  model="unknown"):
    lines = ["## <ISO-8601 date> — 01_prepare_samplesheets — samplesheets emitted", "",
             # Not only stage 00 stamps this. A workspace can be upgraded between stages, and the
             # per-stage stamp is the only record that this stage ran under a different contract
             # than the one that created the project.
             "Template version: %s" % version,
             # The model is part of the toolchain: the same contract executed by a different
             # interpreter is a different run. `unknown` is an honest value (decision 0024).
             "Model: %s" % (model or "unknown"),
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
    ap.add_argument("--model", default="unknown",
                    help="the exact model id of the agent executing this stage; recorded in the "
                         "HISTORY.md entry beside the template version (decision 0024)")
    ap.add_argument("--verify-integrity", choices=("none", "full"), default="none",
                    help="none (default): trust the files; stage 00 already checked that every "
                         "link resolves and carries gzip magic. full: decompress every INCLUDED "
                         "file before emitting the samplesheet -- the last cheap moment to catch "
                         "a truncated FASTQ. Above " + chr(126) + "10 GB submit this with sbatch; it is not "
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
                          project / "01_samplesheets" / f"{a}_design.csv",
                          project / "01_samplesheets" / f"{a}_design_check.json")
                if p.is_file()]

    if args.verify_integrity == "full":
        for assay, res in results.items():
            problems = integrity.check_many(res["_incl_paths"], "full")
            res["design_check"]["checks"].append({"check": "integrity",
                "outcome": "fail" if problems else "pass",
                "failures": [fail("integrity", "%s %s" % p) for p in problems]})
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
                                            result["template_version"], args.model)
    return emit(result, EXIT_OK)


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
