#!/usr/bin/env python3
"""Stage 00 — create a project and register its raw data.

The deterministic core of `00_initialize_project`. The contract orchestrates; this computes.
See docs/decisions/0011-deterministic-artifacts-in-stages-00-01.md for why.

This script decides what is TRUE. It never prompts, never links without being told the user
confirmed, and never invents a sample ID it cannot derive. The agent decides what to say and
when to stop.

Stdlib only, and verified on stock python 3.6.8: stages 00 and 01 must run with no conda
environment, unlike stage 02.

The four subcommands are the contract's own phases, so a conversation turn sits between each:

    assays    steps 3-6    offer the supported assays; resolve a selection -> backs T3
    create    step  7      sanitize the title, validate assays, copy the stamp
    inspect   step  9      read-only scan of one source directory   -> backs T4a
    link      step  12     symlink one assay's raw files            -> backs T4b
    finalize  steps 14-19  metadata, placeholders, exit gate        -> backs T6 / T9

Every subcommand emits a single JSON object on stdout. Exit codes:

    0  ok
    1  failure; report and stop (T9)
    2  refused; the JSON's `template` field names which reply to send (T5 / T7 / T8)
    3  usage or precondition error

Note on cost: `finalize` defaults to `--integrity quick` -- resolves, non-empty, gzip magic --
because at this stage EVERY registered file would be verified, including the ones the user is
about to exclude at the 00 -> 01 gate. Deep verification of the files that will actually be
analysed belongs to stage 01, which is the first moment the included subset exists. `--integrity
full` is still available here and still honest about what it did: the mode is stamped into the
project's HISTORY.md, never assumed.
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import integrity            # noqa: E402  -- one home for the integrity rule
import workspace as ws     # noqa: E402  -- one home for the template version

RAW_SUFFIXES = (".fastq.gz", ".fq.gz", ".fastq", ".fq")
FILES_HEADER = ["sample_id", "lane", "fastq_1", "fastq_2"]
BCL2FASTQ = re.compile(r"^(?P<sample>.+?)_S\d+_(?:L(?P<lane>\d+)_)?R(?P<read>[12])_\d+\."
                       r"(?:fastq|fq)(?:\.gz)?$")

EXIT_OK, EXIT_FAILURE, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2, 3


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


# --- shared -------------------------------------------------------------------------------------

def sanitize_title(title):
    """Contract: keep [A-Za-z0-9_-]; space -> _; drop the rest; collapse _; strip leading/trailing
    _ and -."""
    s = title.replace(" ", "_")
    s = "".join(c for c in s if re.match(r"[A-Za-z0-9_-]", c))
    s = re.sub(r"_+", "_", s)
    return s.strip("_-")


def read_assay_map(workspace):
    """Parse the Assay / Assay ID columns of the FIRST table headed `| Assay | Assay ID |`.

    Binding to that header matters: the file holds a second table (Skill requirements) whose
    first two columns are Skill / Python. Reading every pipe-prefixed line accepted `rnaseq-de`
    as an assay and created a directory named `(unpinned)` from the Python column.
    """
    path = workspace / "_references" / "assay_stage_skill_map.md"
    if not path.is_file():
        return None, "assay map not found at %s" % path

    catalog, in_table = {}, False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break          # the table ended; never read past it
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if not in_table:
            if cells[0] == "Assay" and cells[1] == "Assay ID":
                in_table = True
            continue
        if set("".join(cells[:2])) <= set("-: "):
            continue           # the header separator row
        name, aid = cells[0], cells[1]
        entry = catalog.setdefault(aid, {"assay": name, "substages": []})
        # One row per sub-stage, in the order the map lists them -- that order IS the pipeline.
        if len(cells) >= 5 and cells[3]:
            entry["substages"].append({"substage": cells[3], "skill": cells[4]})

    if not catalog:
        return None, "assay map has no table headed `| Assay | Assay ID |`"
    return catalog, None


def catalog_names(catalog):
    """{assay_id: display name} -- what the matching and placeholder code needs."""
    return {aid: e["assay"] for aid, e in catalog.items()}


def menu(catalog):
    """The offer list. Numbers are PRESENTATION ONLY.

    They are assigned from a deterministic sort of the Assay IDs and are regenerated on every
    call, so the numbering handed out is always the numbering `--select` resolves against. They
    are never written to disk, never recorded in HISTORY.md, and never used as a directory name:
    add an assay and `02` becomes a different thing, so a persisted number would silently rot.
    The Assay ID is the durable identifier and the only one that leaves this function.
    """
    return [{"n": "%02d" % i, "assay": catalog[aid]["assay"], "assay_id": aid,
             "substages": catalog[aid]["substages"]}
            for i, aid in enumerate(sorted(catalog), start=1)]


def normalize_assay(text):
    """Case-fold and drop every non-alphanumeric character.

    `rnaseq-bulk`, `rnaseq_bulk`, `RNAseq Bulk` and `rnaseq bulk` all normalise to `rnaseqbulk`;
    `Bulk RNA-seq` and `bulk rna seq` both to `bulkrnaseq`. This is normalisation, NOT fuzzy
    matching -- no edit distance, no substring, no stemming. Two different assays cannot collide
    unless their names differ only in punctuation, which `resolve_assays` refuses outright rather
    than guessing between.

    The strict version of this rejected `rnaseq-bulk` -- one character away from the Assay ID it
    obviously meant -- and told the user only that "Bulk RNA-seq" was supported, without ever
    showing the ID. Refusing a punctuation variant is not safety, it is a dead end.
    """
    return "".join(c for c in text.lower() if c.isalnum())


def resolve_assays(requested, assay_map):
    """Match each request against the Assay column or the Assay ID column, after normalisation.

    Returns one entry per request. An unmatched request is reported, never resolved to a
    neighbour: the point of refusing is that a wrong assay silently creates the wrong pipeline.
    """
    index = {}
    for aid, name in assay_map.items():
        for form in (aid, name):
            index.setdefault(normalize_assay(form), set()).add(aid)

    out = []
    for req in requested:
        key = normalize_assay(req)
        hits = index.get(key, set())
        if len(hits) == 1:
            out.append({"requested": req, "assay_id": sorted(hits)[0], "supported": True})
        elif len(hits) > 1:
            out.append({"requested": req, "assay_id": None, "supported": False,
                        "ambiguous_between": sorted(hits),
                        "note": "matches more than one assay; name it by Assay ID"})
        else:
            out.append({"requested": req, "assay_id": None, "supported": False})
    return out


def template_version(workspace):
    return ws.template_version(workspace)


# A Space Ranger output tree may arrive as a directory or as a tarball of one; the pipeline
# accepts either (spatialvi docs/usage.md).
SAMPLE_DIR_SUFFIXES = (".tar.gz", ".tgz")


def find_raw(source, kind="fastq"):
    """Raw input at the TOP LEVEL only. Never descends -- the contract forbids searching.

    `fastq`: files with an NGS suffix. `sample_dir`: one directory (or tarball of one) per
    sample, which is how spatial data arrives -- there are no FASTQs to see.
    """
    raw, other = [], []
    for p in sorted(source.iterdir()):
        if kind == "sample_dir":
            is_input = p.is_dir() or p.name.endswith(SAMPLE_DIR_SUFFIXES)
        else:
            if not p.is_file() and not p.is_symlink():
                continue
            is_input = p.name.endswith(RAW_SUFFIXES)
        (raw if is_input else other).append(p.name)
    return raw, other


def derive_units(filenames, pattern=None, kind="fastq"):
    """Group filenames into (sample_id, lane) units.

    Returns (units, layout, problems). `pattern` overrides the bcl2fastq convention and must
    provide named groups `sample` and `read`, optionally `lane` -- it is how the contract feeds
    back an answer the user gave when filenames do not match the convention.

    For `sample_dir` there is nothing to parse and nothing to pair: each entry IS a sample, its
    id is the entry name with any tarball suffix removed, and the layout is reported as
    `sample-dir` so callers never apply a pairing rule that has no meaning here.
    """
    if kind == "sample_dir":
        units, problems = {}, []
        for name in filenames:
            sample = name
            for suffix in SAMPLE_DIR_SUFFIXES:
                if sample.endswith(suffix):
                    sample = sample[:-len(suffix)]
                    break
            if not sample:
                problems.append(name)
                continue
            if (sample, "") in units:
                problems.append(name)
                continue
            units[(sample, "")] = {"dir": name}
        return ({}, None, problems) if problems else (units, "sample-dir", [])

    rx = re.compile(pattern) if pattern else BCL2FASTQ
    units, problems = {}, []
    for name in filenames:
        m = rx.match(name)
        if not m:
            problems.append(name)
            continue
        gd = m.groupdict()
        sample = gd.get("sample")
        lane = gd.get("lane") or ""
        read = gd.get("read") or "1"
        if not sample:
            problems.append(name)
            continue
        lane = "L%s" % lane if lane and not lane.startswith("L") else lane
        units.setdefault((sample, lane), {})[read] = name

    if problems:
        return {}, None, problems

    r2 = [u for u in units.values() if "2" in u]
    if len(r2) == len(units):
        layout = "paired-end"
    elif not r2:
        layout = "single-end"
    else:
        layout = "mixed"
    return units, layout, []


def units_to_rows(units, assay_id, kind="fastq"):
    """Rows for files.csv, shaped by the assay's input kind (workspace.FILES_HEADERS)."""
    rows = []
    base = "00_data/%s/raw/" % assay_id
    if kind == "sample_dir":
        for (sample, _) in sorted(units):
            rows.append([sample, base + units[(sample, "")]["dir"]])
        return rows
    for (sample, lane) in sorted(units):
        reads = units[(sample, lane)]
        rows.append([sample, lane,
                     base + reads["1"] if "1" in reads else "",
                     base + reads["2"] if "2" in reads else ""])
    return rows


# --- assays ---

def cmd_assays(args, workspace):
    """Offer the supported assays, and resolve a selection back to Assay IDs.

    Two modes, one source of truth. Without --select it returns the menu the agent renders; with
    --select it resolves what the user picked. Both derive from the same `menu()` call, so the
    numbering offered cannot drift from the numbering accepted.

    A selection may name a number (`01`), an Assay ID, or a display name -- whatever the user
    typed. Everything resolves to Assay IDs, and only Assay IDs are returned.
    """
    result = {"command": "assays", "ok": False}
    catalog, err = read_assay_map(workspace)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)

    offered = menu(catalog)
    result["assays"] = offered

    if args.select is None:
        result["ok"] = True
        return emit(result, EXIT_OK)

    by_n = {e["n"]: e for e in offered}
    by_n.update({e["n"].lstrip("0"): e for e in offered})   # accept `1` as well as `01`
    names = catalog_names(catalog)

    def look_up(tok):
        hit = by_n.get(tok)
        if hit is not None:
            return hit
        # Not a menu number -- fall back to name/ID matching, so a user who typed the assay
        # instead of picking a number is not punished for it.
        match = resolve_assays([tok], names)[0]
        if not match["supported"]:
            return None
        return next((e for e in offered if e["assay_id"] == match["assay_id"]), None)

    def try_split(tokens):
        hits, bad = [], []
        for tok in tokens:
            hit = look_up(tok)
            if hit is None:
                bad.append(tok)
            elif hit["assay_id"] not in [h["assay_id"] for h in hits]:
                hits.append(hit)
        return hits, bad

    # Commas first, because the prompt asks for a comma-separated list and an assay NAME may
    # contain spaces -- splitting "Bulk RNA-seq" on whitespace tore it into two invalid tokens.
    # Only if that fails completely, and there were no commas, retry on whitespace so that
    # "01 02" still works.
    result["selected"], result["invalid"] = [], []
    comma_tokens = [t.strip() for t in args.select.split(",") if t.strip()]
    if not comma_tokens:
        result["assay_ids"] = []
        result["error"] = "empty selection"
        result["template"] = "T3"
        return emit(result, EXIT_REFUSED)

    selected, invalid = try_split(comma_tokens)
    if invalid and "," not in args.select:
        ws_selected, ws_invalid = try_split(args.select.split())
        if not ws_invalid:
            selected, invalid = ws_selected, ws_invalid

    result["selected"] = selected
    result["invalid"] = invalid
    # The only thing the caller should pass onward. Numbers stop here.
    result["assay_ids"] = [s["assay_id"] for s in selected]
    if invalid or not selected:
        result["template"] = "T3"
        result["error"] = ("could not resolve: %s" % ", ".join(invalid)) if invalid \
            else "nothing selected"
        return emit(result, EXIT_REFUSED)

    result["ok"] = True
    return emit(result, EXIT_OK)


# --- create -------------------------------------------------------------------------------------

def _build_project(stamp, project, supported, workspace, title):
    """The stamp, each assay's raw/ and the seeded _config/ at `project`; the seeded names."""
    import shutil
    shutil.copytree(str(stamp), str(project))
    for aid in supported:
        (project / "00_data" / aid / "raw").mkdir(parents=True, exist_ok=True)

    # Seed _config/ so the user never authors a config from a blank file. Everything derivable is
    # filled in; the scientific decisions are left marked <REQUIRED>, because no stage substitutes
    # a value for them. Making those decisions is the user's; authoring YAML from a 91-line schema
    # is not, and a user reasonably asked why they had to.
    seeded = []
    config_src = workspace / "_templates" / "config"
    scratch = os.environ.get("GARS_SCRATCH",
                             "/gpfs/scratch/%s/gars-work" % os.environ.get("USER", "USER"))
    # compute.mem comes from the venue's own table (0293), for the venue the descriptor this
    # project is seeded with names; absent, that is Slurm, as `load` treats an absent descriptor.
    import executorlib as ex
    import venue_policy as policy
    descriptor = config_src / "executor.yaml"
    name = (ex.parse_descriptor(descriptor.read_text(encoding="utf-8")).get("name")
            if descriptor.is_file() else None) or "slurm"
    venue = ex.venue_of({"name": name})
    for aid in supported:
        src = config_src / (aid + ".yaml")
        if src.is_file():
            # One dict per assay: the seeded memory differs by assay.
            values = {"{{project_title}}": title, "{{work_dir}}": "%s/%s" % (scratch, title)}
            if policy.seeded_mem(venue, aid):
                values["{{mem}}"] = policy.seeded_mem(venue, aid)
            text = src.read_text(encoding="utf-8")
            for k, v in values.items():
                text = text.replace(k, v)
            (project / "_config" / (aid + ".yaml")).write_text(text, encoding="utf-8")
            seeded.append("_config/" + aid + ".yaml")
    # The Nextflow executor config and the scheduler descriptor (decision 0039) are seeded
    # together: one says how Nextflow submits each process, the other how GARS submits the
    # job that runs Nextflow. A project that deletes the descriptor gets Slurm's built-in
    # defaults, so the pair stays optional-by-deletion rather than fragile.
    for name in ("nextflow.slurm.config", "executor.yaml"):
        src = config_src / name
        if src.is_file() and supported:
            shutil.copy2(str(src), str(project / "_config" / name))
            seeded.append("_config/" + name)
    return seeded


def cmd_create(args, workspace):
    result = {"command": "create", "ok": False}
    title = sanitize_title(args.title)
    result["title"] = args.title
    result["sanitized_title"] = title
    if not title:
        result["error"] = "the title sanitizes to an empty string"
        return emit(result, EXIT_USAGE)

    project = workspace / "projects" / title
    result["project"] = str(project)
    if project.exists():
        result["template"] = "T7"
        result["error"] = "projects/%s/ already exists; nothing was created or modified" % title
        return emit(result, EXIT_REFUSED)

    catalog, err = read_assay_map(workspace)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)
    assay_map = catalog_names(catalog)

    validation = resolve_assays(args.assays, assay_map)
    result["assays"] = validation
    # Both forms, because either is accepted and the ID is what users tend to type.
    result["supported_assays"] = [{"assay": name, "assay_id": aid}
                                  for aid, name in sorted(assay_map.items())]
    supported = [v["assay_id"] for v in validation if v["supported"]]
    if not supported:
        result["template"] = "T8"
        result["error"] = "none of the requested assays are supported; no project was created"
        return emit(result, EXIT_REFUSED)

    stamp = workspace / "_templates" / "project"
    if not stamp.is_dir():
        result["error"] = "project stamp not found at %s" % stamp
        return emit(result, EXIT_USAGE)

    # Built in a sibling no project scan reads as a project (a dot name: titles never start with
    # one), then renamed into place, so a fault leaves no half project behind (0295).
    import shutil
    import tempfile
    project.parent.mkdir(parents=True, exist_ok=True)    # as copytree made it before
    building = Path(tempfile.mkdtemp(prefix="." + title + "-", dir=str(project.parent)))
    try:
        os.rmdir(str(building))     # the name is reserved; copytree makes it with the stamp's mode
        seeded = _build_project(stamp, building, supported, workspace, title)
        if project.exists():
            raise FileExistsError("projects/%s/ appeared while it was being built" % title)
        os.rename(str(building), str(project))
    except BaseException:
        shutil.rmtree(str(building), ignore_errors=True)
        raise
    result["config_seeded"] = seeded

    result["created"] = supported
    result["template_version"] = template_version(workspace)
    result["ok"] = True
    return emit(result, EXIT_OK)


# --- inspect ------------------------------------------------------------------------------------

def cmd_inspect(args, workspace):
    """Read-only. Writes nothing, so the agent can show counts and ask before any link exists."""
    result = {"command": "inspect", "ok": False, "assay_id": args.assay, "source": args.source}
    source = Path(args.source)
    if not source.is_dir():
        result["template"] = "T5"
        result["error"] = "not a directory: %s" % source
        return emit(result, EXIT_REFUSED)

    kind = ws.input_kind(args.assay)
    result["input_kind"] = kind
    raw, other = find_raw(source, kind)
    result["raw_file_count"] = len(raw)
    result["excluded_file_count"] = len(other)
    result["excluded_examples"] = other[:5]
    if not raw:
        result["template"] = "T5"
        result["error"] = ("no per-sample directories at the top level of %s" % source
                           if kind == "sample_dir"
                           else "no raw NGS files at the top level of %s" % source)
        return emit(result, EXIT_REFUSED)

    units, layout, problems = derive_units(raw, args.sample_id_pattern, kind)
    if problems:
        result["template"] = "T5"
        result["error"] = ("cannot derive sample IDs: %d entr%s do not match the expected "
                           "convention" % (len(problems), "y" if len(problems) == 1 else "ies"))
        result["unmatched_examples"] = problems[:5]
        result["convention"] = ("<sample>/ or <sample>.tar.gz, one per sample"
                                if kind == "sample_dir"
                                else "<sample>_S<n>[_L<lane>]_R<1|2>_<nnn>.fastq.gz")
        return emit(result, EXIT_REFUSED)
    if layout == "mixed":
        result["template"] = "T5"
        result["error"] = "mixed/incomplete pairing: some sample-lane units have no R2"
        result["unpaired"] = ["%s %s" % k for k, v in sorted(units.items()) if "2" not in v][:10]
        return emit(result, EXIT_REFUSED)

    result["sample_ids"] = sorted({s for s, _ in units})
    result["sample_count"] = len(result["sample_ids"])
    result["sample_lane_units"] = len(units)
    result["layout"] = layout
    # So the agent can state the cost of a full integrity check without computing it itself.
    total = sum((source / n).stat().st_size for n in raw if (source / n).is_file())
    if kind == "sample_dir":
        total = sum(f.stat().st_size
                    for n in raw for f in (source / n).rglob("*") if f.is_file()) or total
    result["total_bytes"] = total
    result["total_gb"] = round(total / 1e9, 1)
    result["full_check_estimate_min"] = max(1, int(round(total / 130e6 / 60)))
    result["ok"] = True
    return emit(result, EXIT_OK)


# --- the sample-name pattern each assay was linked with (S00-onepattern, 0314) ------------------

#: Project-relative; empty for the bcl2fastq convention. Absent for an assay linked before 0314.
PATTERN_RECORD = "00_data/%s/sample_id_pattern.txt"


def pattern_record(project, assay):
    return Path(project) / (PATTERN_RECORD % assay)


def recorded_pattern(project, assay):
    """(True, pattern or None) from the assay's record; (False, None) when it has none."""
    path = pattern_record(project, assay)
    if not path.is_file():
        return False, None
    return True, path.read_text(encoding="utf-8").rstrip("\n") or None


def describe_pattern(pattern):
    return "the pattern %r" % pattern if pattern else "the bcl2fastq convention"


# --- link ---------------------------------------------------------------------------------------

def cmd_link(args, workspace):
    result = {"command": "link", "ok": False, "assay_id": args.assay, "source": args.source}
    project = Path(args.project)
    raw_dir = project / "00_data" / args.assay / "raw"
    if not raw_dir.is_dir():
        result["error"] = "no raw/ directory at %s; run create first" % raw_dir
        return emit(result, EXIT_USAGE)

    source = Path(args.source)
    kind = ws.input_kind(args.assay)
    raw, _ = find_raw(source, kind)
    if not raw:
        result["template"] = "T5"
        result["error"] = ("no per-sample directories at the top level of %s" % source
                           if kind == "sample_dir"
                           else "no raw NGS files at the top level of %s" % source)
        return emit(result, EXIT_REFUSED)

    # The pattern this assay's inspect used is read again here, before any link exists, and
    # recorded beside raw/ so finalize derives this assay's names with it and never another
    # assay's (S00-onepattern, 0314).
    pattern = getattr(args, "sample_id_pattern", None)
    try:
        units, layout, problems = derive_units(raw, pattern, kind)
    except re.error as exc:
        result["error"] = "--sample-id-pattern is not a valid regex: %s" % exc
        return emit(result, EXIT_USAGE)
    if problems:
        result["template"] = "T5"
        result["error"] = ("cannot derive sample IDs: %d entr%s do not match %s; link with the "
                           "pattern this assay's inspect used"
                           % (len(problems), "y" if len(problems) == 1 else "ies",
                              describe_pattern(pattern)))
        result["unmatched_examples"] = problems[:5]
        return emit(result, EXIT_REFUSED)
    if layout == "mixed":
        result["template"] = "T5"
        result["error"] = "mixed/incomplete pairing: some sample-lane units have no R2"
        return emit(result, EXIT_REFUSED)

    existing = list(raw_dir.iterdir())
    if existing and not args.force:
        result["error"] = ("%s already holds %d entries; refusing to re-link. Stage 00 never "
                           "narrows an existing project." % (raw_dir, len(existing)))
        return emit(result, EXIT_FAILURE)

    linked, broken = [], []
    for name in raw:
        dest = raw_dir / name
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        os.symlink(str((source / name).resolve()), str(dest))
        # A sample_dir link points at a directory, which is not is_file(). What matters either
        # way is that the link resolves to something that exists.
        (linked if dest.exists() else broken).append(name)

    result["linked"] = len(linked)
    result["broken"] = broken
    if broken:
        result["error"] = "%d symlink(s) do not resolve" % len(broken)
        return emit(result, EXIT_FAILURE)
    with ws.atomic_open(pattern_record(project, args.assay), mode=ws.MACHINE_OWNED_MODE) as fh:
        fh.write(pattern + "\n" if pattern else "")
    result["pattern_record"] = str(PATTERN_RECORD % args.assay)
    result["ok"] = True
    return emit(result, EXIT_OK)


# --- finalize -----------------------------------------------------------------------------------

DATASET_BASE_FIELDS = ['data_class', 'purpose', 'agreement_ref', 'input_data_location']
DATASET_ROUTE_FIELDS = ['permitted_backends', 'provider_exposure', 'retention', 'expiry']


def dataset_values(project, base, permitted_backends=None, expiry=None):
    """Validate immutable registration before any finalize writes."""
    import executorlib as ex
    import venue_policy as policy
    path = Path(project) / '00_data/dataset.tsv'
    registered = None
    if path.exists():
        try:
            with path.open(encoding='utf-8', newline='') as handle:
                rows = list(csv.DictReader(handle, delimiter='\t'))
            registered = rows[0] if len(rows) == 1 else {}
        except (OSError, ValueError, UnicodeError):
            registered = {}
        if {key: registered.get(key) for key in DATASET_BASE_FIELDS} != base:
            raise ValueError('dataset_classification_locked: existing dataset row differs')
    if base['data_class'] == 'identifiable':
        raise ValueError('class_not_permitted: identifiable has no route')
    if ex.venue_of(ex.LOCAL) == 'homelab' and base['data_class'] != 'public':
        raise ValueError('storage_venue_not_permitted: homelab storage is public only')
    route = policy.routes()[base['data_class']]
    permitted = policy.narrowed(base['data_class'], permitted_backends)
    if expiry is None:
        expiry = 'none'
    if expiry != 'none':
        try:
            policy.expiry_date(expiry)
        except ValueError:
            raise ValueError('dataset_expired: expiry must be YYYY-MM-DD')
    elif base['data_class'] == 'deidentified_under_agreement':
        raise ValueError('dataset_expired: agreement expiry required')
    row = dict(base, permitted_backends=permitted, provider_exposure=route['provider_exposure'],
               retention=route['retention_rule'], expiry=expiry)
    if registered is not None and set(registered) != set(DATASET_BASE_FIELDS) and registered != row:
        raise ValueError('dataset_classification_locked: existing dataset route differs')
    return row


def write_dataset_record(project, row):
    """Finalize's writer; bench also uses it only in a newly created public/fixture project."""
    path = Path(project) / '00_data/dataset.tsv'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open(encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            rows = list(reader)
        if rows == [row]:
            return
        if (reader.fieldnames != DATASET_BASE_FIELDS or len(rows) != 1 or
                rows[0] != {key: row[key] for key in DATASET_BASE_FIELDS}):
            raise ValueError('dataset_classification_locked: existing dataset row differs')
        # Sanctioned row-6 migration preserves each existing serialized field byte.
        import io
        suffix = io.StringIO()
        writer = csv.DictWriter(suffix, fieldnames=DATASET_ROUTE_FIELDS, delimiter='\t',
                                lineterminator='\n', extrasaction='ignore')
        writer.writeheader(); writer.writerow(row)
        header, body = path.read_bytes().split(b'\n', 1)
        old = [header + b'\n', body]
        new = suffix.getvalue().encode('utf-8').splitlines(keepends=True)
        with ws.atomic_open(path, mode=ws.MACHINE_OWNED_MODE) as handle:
            for prefix, extra in zip(old, new):
                handle.write((prefix.rstrip(b'\r\n') + b'\t' + extra).decode('utf-8'))
        return
    with ws.atomic_open(path, mode=ws.MACHINE_OWNED_MODE) as handle:
        writer = csv.DictWriter(handle, fieldnames=DATASET_BASE_FIELDS + DATASET_ROUTE_FIELDS,
                                delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerow(row)


def registered_purpose(path):
    """The purpose of an existing one-row dataset record, or None."""
    try:
        with Path(path).open(encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle, delimiter='\t'))
    except (OSError, ValueError, UnicodeError):
        return None
    return rows[0].get('purpose') if len(rows) == 1 else None


def declared_purpose(workspace, project):
    """fixture or internal when data_sources.tsv settles it, else None (2a, 0321).

    Settled only when the file reads cleanly (header source, data_class, declared_by and an
    optional fourth column use; every row three cells, or four under that header; each use
    cell test, analysis or empty), every linked raw entry lies inside a declared source, and all those sources carry
    the same non-empty use. Finalize checks the header, the cell counts and the use cell only,
    not the guard's row rules (hunk G1 is the guard's reading of the file); the agent's finalize
    passes the guard first, the person's own does not.
    """
    import venue_policy as policy
    header = ["source", "data_class", "declared_by"]
    try:
        text = (Path(workspace) / "data_sources.tsv").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    if "\r" in text:
        return None
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[0].split("\t") not in (header, header + ["use"]):
        return None
    width = len(lines[0].split("\t"))
    sources = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) not in (3, width):
            return None
        use = cells[3] if len(cells) == 4 else ""
        if use not in ("", "test", "analysis"):
            return None
        sources.append((os.path.realpath(cells[0]), use))
    uses = set()
    entries = sorted((Path(project) / "00_data").glob("*/raw/*"))
    for entry in entries:
        real = os.path.realpath(str(entry))
        inside = [use for source, use in sources
                  if real == source or real.startswith(source.rstrip(os.sep) + os.sep)]
        if not inside:
            return None
        uses.update(inside)
    if not entries or len(uses) != 1 or "" in uses:
        return None
    use = uses.pop()
    return [p for p, u in policy.USE_OF_PURPOSE.items() if u == use][0]


def cmd_finalize(args, workspace):
    import venue_policy as policy
    result = {"command": "finalize", "ok": False, "assays": {}, "failures": []}
    project = Path(args.project)
    if not project.is_dir():
        result["failures"].append("project does not exist: %s" % project)
        return emit(result, EXIT_USAGE)

    if args.data_class not in ("public", "deidentified_under_agreement", "identifiable"):
        result["failures"].append("data_class_required: --data-class must name a registered class")
        return emit(result, EXIT_REFUSED)
    # 2a (0321): the person's own data_sources.tsv may settle test or analysis; else T4c asks.
    declared = declared_purpose(workspace, project) if args.data_class == "public" else None
    if args.purpose is None and declared is not None:
        args.purpose = declared
    elif args.purpose in policy.REGISTRABLE_PURPOSES and declared not in (None, args.purpose):
        result["failures"].append(
            "purpose_disagrees: data_sources.tsv declares this data %s (--purpose %s); leave "
            "--purpose out" % (policy.USE_OF_PURPOSE[declared], declared))
        return emit(result, EXIT_REFUSED)
    if args.purpose is None:
        result["failures"].append(
            "purpose_required: data_sources.tsv does not settle test or analysis for this data; "
            "ask the person (T4c)")
        result["template"] = "T4c"
        return emit(result, EXIT_REFUSED)
    if args.purpose not in policy.PURPOSES:
        result["failures"].append("purpose_required: --purpose must name a registered purpose")
        return emit(result, EXIT_REFUSED)
    if not args.agreement_ref or args.agreement_ref.strip().lower() in ("", "unknown", "todo", "null"):
        result["failures"].append("agreement_ref_required: name an agreement or use none")
        return emit(result, EXIT_REFUSED)
    dataset_path = project / "00_data/dataset.tsv"
    # 1c (0321): a legacy purpose is read only in a row that already carries it.
    if args.purpose in policy.LEGACY_PURPOSES and \
            registered_purpose(dataset_path) != args.purpose:
        result["failures"].append(
            "purpose_legacy: %s is read only in a row that already carries it; a new "
            "registration is fixture (test) or internal (analysis)" % args.purpose)
        return emit(result, EXIT_REFUSED)
    dataset = {"data_class": args.data_class, "purpose": args.purpose,
               "agreement_ref": args.agreement_ref,
               "input_data_location": json.dumps(sorted({str(p.resolve()) for p in
                   (project / "00_data").glob("*/raw/*")}), separators=(",", ":"))}
    try:
        dataset = dataset_values(project, dataset, getattr(args, 'permitted_backends', None),
                                 getattr(args, 'expiry', None))
    except ValueError as exc:
        result["failures"].append(str(exc))
        return emit(result, EXIT_REFUSED)
    result["data"] = policy.data_line(dataset["data_class"], dataset["purpose"])

    catalog, err = read_assay_map(workspace)
    if err:
        result["failures"].append(err)
        return emit(result, EXIT_USAGE)
    assay_map = catalog_names(catalog)

    data_root = project / "00_data"
    assays = sorted(d.name for d in data_root.iterdir() if d.is_dir())
    if not assays:
        result["failures"].append("no assay directories under 00_data/")
        return emit(result, EXIT_USAGE)

    # Each assay's names come from the pattern its own link recorded; a finalize flag that
    # disagrees with a record is refused before anything is written. An assay with no record
    # (linked before 0314) takes the flag, as it always did.
    patterns = {}
    for aid in assays:
        has, recorded = recorded_pattern(project, aid)
        if has and args.sample_id_pattern is not None and args.sample_id_pattern != recorded:
            result["failures"].append(
                "%s: --sample-id-pattern %r disagrees with %s, which its link recorded in %s; "
                "finalize reads each assay's own record, so leave the flag out"
                % (aid, args.sample_id_pattern, describe_pattern(recorded), PATTERN_RECORD % aid))
        patterns[aid] = recorded if has else args.sample_id_pattern
    if result["failures"]:
        return emit(result, EXIT_REFUSED)

    version = template_version(workspace)
    model = ws.history_model(workspace, args.model)
    created = args.date or datetime.date.today().isoformat()
    per_assay = {}

    for aid in assays:
        raw_dir = data_root / aid / "raw"
        names = sorted(p.name for p in raw_dir.iterdir()) if raw_dir.is_dir() else []
        if not names:
            result["failures"].append("%s: raw/ is empty" % aid)
            continue

        kind = ws.input_kind(aid)
        units, layout, problems = derive_units(names, patterns[aid], kind)
        if problems:
            result["failures"].append("%s: %d linked entr%s do not match the convention"
                                      % (aid, len(problems),
                                         "y" if len(problems) == 1 else "ies"))
            continue
        if layout == "mixed":
            result["failures"].append("%s: pairing is incomplete" % aid)
            continue

        # Source path is DERIVED from the symlinks, not remembered -- the filesystem is the state.
        sources = sorted({os.path.dirname(os.readlink(str(raw_dir / n)))
                          for n in names if (raw_dir / n).is_symlink()})

        rows = units_to_rows(units, aid, kind)
        with ws.atomic_open(data_root / aid / "files.csv",
                            mode=ws.MACHINE_OWNED_MODE) as fh:
            fh.write("# generated by stage 00 — do not edit\n")
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(ws.files_header(aid))
            for r in rows:
                w.writerow(r)

        # files.csv is machine-owned and is always regenerated from raw/.
        # samples.csv is NOT: it is the user's file, and re-running finalize must never destroy a
        # design they have filled in, or an exclusion they expressed by deleting rows. It is
        # written once, on creation, and preserved thereafter. A sample present in raw/ but absent
        # from samples.csv is an exclusion, which is stage 01's business to confirm -- not a gap
        # for this stage to silently fill back in.
        sample_ids = sorted({s for s, _ in units})
        samples_csv = data_root / aid / "samples.csv"
        if samples_csv.exists():
            samples_state = "preserved"
        else:
            samples_state = "created"
            with ws.atomic_open(samples_csv) as fh:
                w = csv.writer(fh, lineterminator="\n")
                w.writerow(ws.design_columns(aid))
                for sid in sample_ids:
                    w.writerow([sid, "", "", ""])

        per_assay[aid] = {"display": assay_map.get(aid, aid), "files": len(names),
                          "samples": len(sample_ids), "units": len(units), "layout": layout,
                          "sources": sources, "samples_csv": samples_state}
        result["assays"][aid] = {k: v for k, v in per_assay[aid].items()}

    if result["failures"]:
        return emit(result, EXIT_FAILURE)

    # -- placeholders
    assay_table = ["| Assay | Assay ID | Data directory | Files | Samples |", "|---|---|---|---|---|"]
    source_rows = ["| Assay ID | Source path | Files linked |", "|---|---|---|"]
    for aid in assays:
        m = per_assay[aid]
        assay_table.append("| %s | %s | `00_data/%s/` | %d | %d |"
                           % (m["display"], aid, aid, m["files"], m["samples"]))
        source_rows.append("| %s | %s | %d |"
                           % (aid, ", ".join("`%s`" % s for s in m["sources"]) or "unknown",
                              m["files"]))

    values = {"{{project_title}}": project.name, "{{created}}": created,
              "{{template_version}}": version, "{{assay_table}}": "\n".join(assay_table),
              "{{source_paths}}": "\n".join(source_rows),
              "{{integrity}}": args.integrity,
              "{{model}}": model}
    for fname in ("CONTEXT.md", "HISTORY.md"):
        p = project / fname
        if not p.is_file():
            result["failures"].append("%s is missing; was the stamp copied?" % fname)
            continue
        text = p.read_text(encoding="utf-8")
        for k, v in values.items():
            text = text.replace(k, v)
        with ws.atomic_open(p, newline=None) as fh:
            fh.write(text)

    # -- exit gate (step 19)
    gate, checked = [], 0
    for fname in ("CONTEXT.md", "HISTORY.md"):
        if not (project / fname).is_file():
            gate.append("%s does not exist" % fname)
    if not (project / "_config").is_dir():
        gate.append("_config/ does not exist")

    unsubstituted = sorted(str(p.relative_to(project)) for p in project.rglob("*")
                           if p.is_file() and p.suffix == ".md" and "{{" in p.read_text(
                               encoding="utf-8", errors="ignore"))
    if unsubstituted:
        gate.append("unsubstituted placeholder remains in: %s" % ", ".join(unsubstituted))

    for aid in assays:
        f_csv, s_csv = data_root / aid / "files.csv", data_root / aid / "samples.csv"
        frows = [r for r in csv.DictReader(
            [l for l in f_csv.read_text(encoding="utf-8").splitlines() if not l.startswith("#")])]
        srows = list(csv.DictReader(s_csv.read_text(encoding="utf-8").splitlines()))
        if not frows:
            gate.append("%s: files.csv is empty" % aid)
        if not srows:
            gate.append("%s: samples.csv is empty" % aid)
        if per_assay[aid]["samples_csv"] == "created" and \
                len({r["sample_id"] for r in frows}) != len(srows):
            gate.append("%s: %d distinct sample_id in files.csv but %d rows in samples.csv"
                        % (aid, len({r["sample_id"] for r in frows}), len(srows)))
        extra = {r["sample_id"] for r in srows} - {r["sample_id"] for r in frows}
        if extra:
            gate.append("%s: samples.csv names %d sample(s) with no rows in files.csv: %s"
                        % (aid, len(extra), ", ".join(sorted(extra)[:5])))
        if any(not r["sample_id"] for r in frows + srows):
            gate.append("%s: a row has an empty sample_id" % aid)
        if ws.input_kind(aid) == "sample_dir":
            # No pairing to check and nothing to checksum: the unit of input is a directory,
            # and hashing a Space Ranger tree would be checking someone else's output rather
            # than the files GARS registered. What CAN go wrong is a link that resolves to
            # nothing, so that is what is checked.
            for r in frows:
                rel = r.get("spaceranger_dir", "")
                if not rel:
                    gate.append("%s: a row has an empty spaceranger_dir" % aid)
                elif not (project / rel).exists():
                    gate.append("%s: %s does not resolve" % (aid, rel))
            continue
        if per_assay[aid]["layout"] == "paired-end" and any(not r["fastq_2"] for r in frows):
            gate.append("%s: pairing is incomplete in files.csv" % aid)
        to_check = [(r[col], project / r[col])
                    for r in frows for col in ("fastq_1", "fastq_2") if r[col]]
        checked += len(to_check)
        for rel, problem in integrity.check_many(to_check, args.integrity):
            gate.append("%s: %s %s" % (aid, rel, problem))

    if gate:
        result["failures"] = gate
        result["template"] = "T9"
        return emit(result, EXIT_FAILURE)

    write_dataset_record(project, dataset)

    result["template_version"] = version
    result["model"] = model
    result["created"] = created
    result["integrity"] = {"mode": args.integrity,
                           "files_checked": checked}
    result["ok"] = True
    return emit(result, EXIT_OK)


# --- main ---------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent.parent,
                    help="workspace root (default: the parent of _system/)")
    sub = ap.add_subparsers(dest="cmd")

    a = sub.add_parser("assays", help="offer the supported assays; resolve a selection")
    a.add_argument("--select", default=None,
                   help="comma-separated menu numbers, Assay IDs or names; omit to just list")

    c = sub.add_parser("create", help="sanitize the title, validate assays, copy the stamp")
    c.add_argument("--title", required=True)
    c.add_argument("--assays", required=True, nargs="+",
                   help="assay names or Assay IDs, as the user gave them")

    i = sub.add_parser("inspect", help="read-only scan of one source directory")
    i.add_argument("--assay", required=True)
    i.add_argument("--source", required=True)
    i.add_argument("--sample-id-pattern", default=None,
                   help="regex with named groups sample/read[/lane], when filenames do not match "
                        "the bcl2fastq convention and the user has said how to read them")

    l = sub.add_parser("link", help="symlink one assay's raw files")
    l.add_argument("--project", required=True)
    l.add_argument("--assay", required=True)
    l.add_argument("--source", required=True)
    l.add_argument("--force", action="store_true", help="re-link a populated raw/ (never routine)")
    l.add_argument("--sample-id-pattern", default=None,
                   help="the pattern this assay's inspect used; recorded beside raw/ for "
                        "finalize (0314)")

    f = sub.add_parser("finalize", help="metadata, placeholders, exit gate")
    f.add_argument("--project", required=True)
    f.add_argument("--data-class", default=None)
    f.add_argument("--purpose", default=None)
    f.add_argument("--agreement-ref", default="none")
    f.add_argument("--permitted-backends", default=None)
    f.add_argument("--expiry", default=None)
    f.add_argument("--date", default=None, help="creation date; defaults to today")
    f.add_argument("--sample-id-pattern", default=None,
                   help="only for an assay linked before 0314; any other assay uses the "
                        "pattern its link recorded, and a different value is refused")
    f.add_argument("--model", default=None,
                   help="ignored, kept so the pinned registry still validates: the model comes from the harness's session start (decision 0303); `none` alone is honoured, for a scripted run with no model-mediated step")
    f.add_argument("--integrity", choices=("full", "quick", "skip"), default="quick",
                   help="quick (default): resolves, non-empty, gzip magic. full: additionally "
                        "decompress every .gz -- O(data), and at this stage it would verify every "
                        "registered file including ones the user is about to exclude. skip: "
                        "resolution and non-emptiness only.")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help(sys.stderr)
        return EXIT_USAGE
    return {"assays": cmd_assays, "create": cmd_create, "inspect": cmd_inspect,
            "link": cmd_link, "finalize": cmd_finalize}[args.cmd](args, args.workspace)


if __name__ == "__main__":
    sys.exit(main())
