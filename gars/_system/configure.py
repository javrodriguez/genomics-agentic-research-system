#!/usr/bin/env python3
"""Complete a project's `_config/<Assay ID>.yaml` from closed menus, not free text.

Stage 00 seeds the config with everything derivable filled and the scientific decisions marked
`<REQUIRED>`. This resolves those, by offering choices rather than asking the user to type paths
and level names:

    genomes    the registered references            -> fills fasta + gtf + derived_dir together
    contrasts  the levels actually in the design     -> fills de.contrast, direction included
    formulas   formulas from the design's own columns -> fills de.formula (apply --formula <n>)
    apply      validate the selections and write     -> prints the resulting file
    declare    stage 01's declarations, as menus      -> writes one top-level key + HISTORY line

`apply --dry-run` prints the would-be file and records its sha256 (`_config/.<assay>.dry_run.json`);
`apply` without it writes only those exact bytes, so a write cannot carry a setting the user was
not shown (R-confirm, decision 0302); the record also carries the sha256 of the file the dry run
read, so a file changed since, by an edit or by that record's own write, needs a new dry run (0304).

The point is not convenience. A FASTA typed by hand can be paired with a mismatched GTF, and a
contrast typed by hand can name a level that does not exist in the design -- both produce a
confident wrong answer or a failure hours in. Selecting from a closed set makes those unreachable.

`de.formula` defaults to `~ condition`, the simplest model the design table supports. That is a
*presented* default, not a silent one: `apply` prints it and the contract requires the agent to
show the file before anything runs. A batch effect needs `~ batch + condition`, and only the user
knows that.

Menu numbers are presentation-only, as in `stage00_register.py assays`: they are regenerated on
every call and resolved in the same call, so nothing positional reaches disk.

Stdlib only; runs before any conda environment is needed.

Exit codes: 0 ok / 1 refused or invalid / 3 usage.
"""

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workspace as ws          # noqa: E402

EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 3
DEFAULT_FORMULA = "~ condition"
MIN_SAMPLES_PER_LEVEL = 2       # a level with one sample cannot be tested


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


# --- genome registry ----------------------------------------------------------------------------

def read_genomes(workspace):
    """Parse the identity table and the separate ID-keyed hash table."""
    path = Path(workspace) / "_references" / "genomes.md"
    if not path.is_file():
        return None, "genome registry not found at %s" % path
    rows, in_table = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not in_table:
            if cells[:2] == ["ID", "Species"]:
                in_table = True
            continue
        if set("".join(cells[:2])) <= set("-: "):
            continue
        if len(cells) < 6:
            continue
        rows.append({"id": cells[0], "species": cells[1], "build": cells[2], "source": cells[3],
                     "fasta": cells[4], "gtf": cells[5],
                     # The registry stores the cache ROOT; the per-assay pipeline key is
                     # appended at menu time, because an index cache is only valid for the
                     # pipeline version that built it (see genomes.md).
                     "cache_root": cells[6] if len(cells) > 6 and cells[6] else None,
                     "mito_name": cells[7] if len(cells) > 7 and cells[7] else None,
                     "macs_gsize": cells[8] if len(cells) > 8 and cells[8] else None})
    if not rows:
        return None, "genome registry has no table headed `| ID | Species |`"
    hashes = {}
    in_hashes = False
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells == ["ID", "Annotation release", "fasta_sha256", "gtf_sha256"]:
            in_hashes = True
            continue
        if in_hashes and not line.strip().startswith("|"):
            in_hashes = False
        if in_hashes and len(cells) == 4 and set(cells[0]) - set("-: "):
            hashes[cells[0]] = dict(zip(("annotation_release", "fasta_sha256", "gtf_sha256"), cells[1:]))
    for row in rows:
        row.update(hashes.get(row["id"], {}))
    return rows, None


def genome_menu(rows, assay=None):
    """The menu, optionally keyed to one assay's pinned pipeline for the cache column.

    `derived_dir` is only computable when the assay is known: the registry stores a cache
    root, and root/<pipeline key> is the directory that pipeline's indices live in. Without
    an assay the menu still renders, with no cache claim."""
    key = ws.PIPELINES.get(assay) if assay else None
    out = []
    for i, r in enumerate(sorted(rows, key=lambda x: x["id"]), start=1):
        entry = dict(r)
        entry["n"] = "%02d" % i
        # Report readability now rather than failing hours into a run.
        entry["fasta_readable"] = os.access(r["fasta"], os.R_OK)
        entry["gtf_readable"] = os.access(r["gtf"], os.R_OK)
        if key and r["cache_root"]:
            entry["derived_dir"] = os.path.join(r["cache_root"], key)
            entry["cached_indices"] = os.path.isdir(entry["derived_dir"])
        else:
            entry["derived_dir"] = None
            entry["cached_indices"] = False
        out.append(entry)
    return out


# --- contrasts from the design the user actually wrote -------------------------------------------

def read_design(project, assay):
    """Levels present in the emitted design table, with their sample counts."""
    path = Path(project) / "01_samplesheets" / ("%s_design.csv" % assay)
    if not path.is_file():
        return None, ("no design table at %s -- run 01_prepare_samplesheets first" %
                      path.relative_to(Path(project).parent.parent)
                      if False else "no design table at 01_samplesheets/%s_design.csv; "
                                    "run 01_prepare_samplesheets first" % assay)
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        return None, "design table is empty"
    return rows, None


def contrast_menu(rows, factor="condition"):
    """Every ordered pair of levels, so direction is chosen rather than assumed."""
    counts = {}
    for r in rows:
        counts.setdefault(r.get(factor, ""), []).append(r["sample_id"])
    levels = sorted(k for k in counts if k)
    pairs, n = [], 0
    for a in levels:
        for b in levels:
            if a == b:
                continue
            n += 1
            testable = (len(counts[a]) >= MIN_SAMPLES_PER_LEVEL and
                        len(counts[b]) >= MIN_SAMPLES_PER_LEVEL)
            pairs.append({
                "n": "%02d" % n, "factor": factor, "numerator": a, "denominator": b,
                "spec": "%s,%s,%s" % (factor, a, b),
                "meaning": "%s relative to %s -- positive log2FC means higher in %s" % (a, b, a),
                "n_numerator": len(counts[a]), "n_denominator": len(counts[b]),
                "testable": testable,
            })
    return levels, {k: len(v) for k, v in counts.items() if k}, pairs


def formula_menu(rows, assay, factor="condition"):
    """The condition alone, then the condition adjusted for each other design column that varies
    (R-formula, 0315). A column nested in the factor cannot be separated from it, so it is
    shown `estimable: false` with the reason, never as a choice."""
    fixed = set(ws.design_columns(assay)) | {factor}
    menu = [{"formula": "~ %s" % factor, "meaning": "%s only" % factor, "terms": [factor],
             "estimable": True}]
    for column in [c for c in rows[0] if c not in fixed]:
        values = [r.get(column, "") for r in rows]
        if len({v for v in values if v}) < 2:
            continue                    # one value (or none) adjusts for nothing
        meaning = ("%s, paired by %s" if column == "subject" else "%s, adjusted for %s") % (
            factor, column)
        entry = {"formula": "~ %s + %s" % (column, factor), "meaning": meaning,
                 "terms": [column, factor], "estimable": True}
        blank = [r["sample_id"] for r in rows if not r.get(column, "")]
        levels = {}
        for r in rows:
            levels.setdefault(r.get(column, ""), set()).add(r.get(factor, ""))
        if blank:
            entry.update(estimable=False, reason="%s is blank for %s" % (column, ", ".join(blank)))
        elif all(len(f) < 2 for f in levels.values()):
            entry.update(estimable=False,
                         reason="every %s value occurs under one %s only, so %s cannot be "
                                "separated from %s" % (column, factor, column, factor))
        menu.append(entry)
    for n, entry in enumerate(menu, start=1):
        entry["n"] = "%02d" % n
    return menu


def cmd_formulas(args, workspace):
    result = {"command": "formulas", "ok": False, "assay": args.assay, "factor": args.factor}
    if ASSAY_DECISIONS.get(args.assay) != "de":
        result["error"] = "assay %s has no de block, so no design formula" % args.assay
        return emit(result, EXIT_USAGE)
    rows, err = read_design(args.project, args.assay)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)
    result.update({"ok": True, "formulas": formula_menu(rows, args.assay, args.factor),
                   "default_formula": DEFAULT_FORMULA,
                   "other": "a formula typed instead is checked term by term and written with "
                            "a warning that it was not chosen from this menu"})
    return emit(result, EXIT_OK)


# --- writing --------------------------------------------------------------------------------------

def set_yaml_scalar(text, key, value, indent=""):
    """Replace `key:` at a given indent. The config is a template we own, not arbitrary YAML."""
    pattern = re.compile(r"^%s%s:.*$" % (re.escape(indent), re.escape(key)), re.M)
    if not pattern.search(text):
        return text, False
    return pattern.sub("%s%s: %s" % (indent, key, value), text, count=1), True


def cmd_genomes(args, workspace):
    rows, err = read_genomes(workspace)
    if err:
        return emit({"command": "genomes", "ok": False, "error": err}, EXIT_USAGE)
    menu = genome_menu(rows, getattr(args, "assay", None))
    result = {"command": "genomes", "ok": True, "genomes": menu}
    if args.select is None:
        return emit(result, EXIT_OK)
    hit = resolve_genome(menu, args.select)
    if hit is None:
        result["ok"] = False
        result["error"] = "could not resolve %r; reply with a menu number or a genome ID" % args.select
        return emit(result, EXIT_REFUSED)
    result["selected"] = hit
    result["genome_id"] = hit["id"]
    return emit(result, EXIT_OK)


def resolve_genome(menu, token):
    token = token.strip()
    for e in menu:
        if token in (e["n"], e["n"].lstrip("0"), e["id"]) or token.lower() == e["id"].lower():
            return e
    return None


def cmd_contrasts(args, workspace):
    result = {"command": "contrasts", "ok": False, "assay": args.assay, "factor": args.factor}
    rows, err = read_design(args.project, args.assay)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)
    levels, counts, pairs = contrast_menu(rows, args.factor)
    result.update({"levels": levels, "samples_per_level": counts, "contrasts": pairs,
                   "default_formula": DEFAULT_FORMULA})
    if len(levels) < 2:
        result["error"] = ("the design has %d level(s) of %r (%s); a contrast needs two. Fix "
                           "00_data/%s/samples.csv and re-run stage 01."
                           % (len(levels), args.factor, ", ".join(levels) or "none", args.assay))
        return emit(result, EXIT_REFUSED)
    result["ok"] = True
    return emit(result, EXIT_OK)


# --- peak type: a closed menu of two ------------------------------------------------------------

PEAK_TYPES = [
    {"n": "01", "value": "narrow",
     "meaning": "point-source peaks -- the conventional choice for ATAC open chromatin and "
                "transcription-factor binding"},
    {"n": "02", "value": "broad",
     "meaning": "domain-scale enrichment -- suits dispersed signal such as broad histone marks"},
]


# --- library chemistry: a closed menu, per aligner ------------------------------------------------

# The chemistries nf-core/scrnaseq names in assets/protocols.json, restricted to the three
# aligners GARS offers. `auto` is deliberately absent: it is valid only for the cellranger
# aligners, which need the proprietary binary. The danger this menu removes is specific -- the
# pipeline passes an UNRECOGNISED protocol to the aligner verbatim rather than rejecting it, so
# a typed value that is merely wrong runs and produces a scrambled matrix (decision 0020: a
# decision whose wrong value is silent comes from a menu, never free text).
PROTOCOLS = [
    {"n": "01", "value": "10XV3",
     "meaning": "10x Genomics 3' v3 -- the most common current chemistry",
     "aligners": ["simpleaf", "star", "kallisto"]},
    {"n": "02", "value": "10XV2",
     "meaning": "10x Genomics 3' v2 -- common for libraries made before ~2020",
     "aligners": ["simpleaf", "star", "kallisto"]},
    {"n": "03", "value": "10XV4",
     "meaning": "10x Genomics 3' v4 (GEM-X)",
     "aligners": ["simpleaf", "star", "kallisto"]},
    {"n": "04", "value": "10XV1",
     "meaning": "10x Genomics 3' v1 -- rare; the original chemistry",
     "aligners": ["simpleaf", "star", "kallisto"]},
    {"n": "05", "value": "dropseq",
     "meaning": "Drop-seq",
     "aligners": ["simpleaf", "star", "kallisto"]},
    {"n": "06", "value": "smartseq",
     "meaning": "Smart-seq3 -- NOT supported by simpleaf; choose star or kallisto",
     "aligners": ["star", "kallisto"]},
]


def cmd_protocols(args, workspace):
    """The library-chemistry menu. Closed, and filterable by aligner so an incompatible pair
    is never offered in the first place."""
    entries = PROTOCOLS
    if args.aligner:
        entries = [e for e in PROTOCOLS if args.aligner in e["aligners"]]
    result = {"command": "protocols", "ok": True, "protocols": entries}
    if args.aligner:
        result["aligner"] = args.aligner
    if args.select is None:
        return emit(result, EXIT_OK)
    tok = args.select.strip()
    for e in entries:
        if tok.lower() in (e["n"], e["n"].lstrip("0")) or tok.upper() == e["value"].upper():
            result["selected"] = e
            result["protocol"] = e["value"]
            return emit(result, EXIT_OK)
    result["ok"] = False
    result["error"] = ("could not resolve protocol %r; a menu number or one of %s"
                       % (args.select, ", ".join(e["value"] for e in entries)))
    return emit(result, EXIT_REFUSED)


def cmd_peaks(args, workspace):
    """The peak-type menu. Static and closed on purpose: MACS2 has exactly these two modes,
    and the choice changes what a 'peak' means scientifically -- so it is selected, never
    defaulted (decision 0020)."""
    result = {"command": "peaks", "ok": True, "peak_types": PEAK_TYPES}
    if args.select is None:
        return emit(result, EXIT_OK)
    tok = args.select.strip().lower()
    for e in PEAK_TYPES:
        if tok in (e["n"], e["n"].lstrip("0"), e["value"]):
            result["selected"] = e
            result["peak_type"] = e["value"]
            return emit(result, EXIT_OK)
    result["ok"] = False
    result["error"] = "could not resolve %r; reply with a menu number, `narrow` or `broad`" % args.select
    return emit(result, EXIT_REFUSED)


# Which decisions `apply` completes, per assay. The seeded config's <REQUIRED> keys and this
# table must agree -- check_contracts.py's drift check keeps the contract prose honest, and
# the `still_unfilled` scan below catches a key neither the template nor this table covers.
ASSAY_DECISIONS = {
    "rnaseq_bulk": "de",        # genome + de.formula + de.contrast
    "atacseq_bulk": "peaks",    # genome + peaks.type (macs_gsize and mito_name come with the genome)
    "chipseq_bulk": "peaks",    # same decisions as ATAC (its template carries no mito_name key)
    "cutandrun": "genome",      # genome only; peakcaller/normalisation are presented defaults
    "methylseq": "genome",      # genome only (fasta; no annotation, no peaks)
    "scrnaseq": "protocol",    # genome + library chemistry (the aligner has a real default)
}


# --- the dry run the user saw (R-confirm) ----------------------------------------------------------

SELECTION_KEYS = ("genome", "contrast", "formula", "peaks_type", "protocol", "aligner")


def dry_run_record(assay):
    """Project-relative path of the record `apply --dry-run` keeps for one assay."""
    return Path("_config") / (".%s.dry_run.json" % assay)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def selections(result):
    return dict((k, result[k]) for k in SELECTION_KEYS if k in result)


def read_dry_run(record, assay):
    """The record exactly as `apply --dry-run` writes it, or None: any other shape is no record."""
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("assay") != assay:
        return None
    sha, shown = data.get("sha256"), data.get("selections")
    for value in (sha, data.get("read_sha256")):
        if not (isinstance(value, str) and re.match(r"[0-9a-f]{64}\Z", value)):
            return None
    if not (isinstance(shown, dict) and all(isinstance(k, str) and isinstance(v, str)
                                            for k, v in shown.items())):
        return None
    return data


def describe(shown):
    return ", ".join("%s %s" % (k, shown[k]) for k in SELECTION_KEYS if k in shown) or "none"


def unmatched_dry_run(record, assay, text, shown, read):
    """Why this write is not the dry run the user was shown, or None when it is, byte for byte.

    The record holds the sha256 of the text the dry run would have written, so a write with other
    selections cannot pass as the one confirmed in T9; and the sha256 of the config file the dry
    run read, so a file changed since (an edit, or this record's own write) needs a new dry run:
    a record is single-use after a write, as the stage 01 check record is (0300).
    """
    data = read_dry_run(record, assay)
    if data is None:
        return ("no dry run is recorded for %s: run this apply with --dry-run, show its "
                "config_preview, and write only after the reply `write`" % assay)
    if data["read_sha256"] != sha256_text(read):
        return ("_config/%s.yaml changed since the dry run was shown (it was edited, or that "
                "dry run was already written); run the dry run again and show it before writing"
                % assay)
    if data["sha256"] == sha256_text(text):
        return None
    if data["selections"] != shown:
        return ("this write differs from the dry run shown: the dry run had %s; this write has "
                "%s. Run the dry run with the settings the user chose and show it again"
                % (describe(data["selections"]), describe(shown)))
    return ("_config/%s.yaml changed since the dry run was shown (same settings: %s); run the "
            "dry run again and show it before writing" % (assay, describe(shown)))


def cmd_apply(args, workspace):
    result = {"command": "apply", "ok": False, "assay": args.assay}
    shape = ASSAY_DECISIONS.get(args.assay)
    if shape is None:
        result["error"] = ("no config decisions are registered for assay %r; known: %s"
                           % (args.assay, ", ".join(sorted(ASSAY_DECISIONS))))
        return emit(result, EXIT_USAGE)

    cfg = Path(args.project) / "_config" / ("%s.yaml" % args.assay)
    if not cfg.is_file():
        result["error"] = "no config at _config/%s.yaml; stage 00 seeds it at project creation" % args.assay
        return emit(result, EXIT_USAGE)

    rows, err = read_genomes(workspace)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)
    genome = resolve_genome(genome_menu(rows, args.assay), args.genome)
    if genome is None:
        result["error"] = "could not resolve genome %r" % args.genome
        return emit(result, EXIT_REFUSED)
    for label, path in (("fasta", genome["fasta"]), ("gtf", genome["gtf"])):
        if not os.access(path, os.R_OK):
            result["error"] = "%s for %s is not readable: %s" % (label, genome["id"], path)
            return emit(result, EXIT_REFUSED)

    updates = [("fasta", genome["fasta"], "  "), ("gtf", genome["gtf"], "  ")]

    if shape == "genome":
        # No second decision: the genome sets everything. mito_name travels with it where the
        # assay's template carries the key (set_yaml_scalar no-ops where it does not).
        if genome.get("mito_name"):
            updates.append(("mito_name", genome["mito_name"], "  "))

    elif shape == "de":
        if not args.contrast:
            result["error"] = "assay %s needs --contrast (see `configure.py contrasts`)" % args.assay
            return emit(result, EXIT_USAGE)
        design, err = read_design(args.project, args.assay)
        if err:
            result["error"] = err
            return emit(result, EXIT_USAGE)
        levels, counts, pairs = contrast_menu(design, args.factor)
        chosen = None
        for pair in pairs:
            if args.contrast.strip() in (pair["n"], pair["n"].lstrip("0"), pair["spec"]):
                chosen = pair
                break
        if chosen is None:
            result["error"] = ("could not resolve contrast %r. Choose a menu number, or give "
                               "factor,numerator,denominator using levels that exist: %s"
                               % (args.contrast, ", ".join(levels)))
            result["contrasts"] = pairs
            return emit(result, EXIT_REFUSED)
        if not chosen["testable"]:
            result["error"] = ("%s has %d sample(s) and %s has %d; each level needs at least %d to be "
                               "tested. Add samples in 00_data/%s/samples.csv and re-run stage 01."
                               % (chosen["numerator"], chosen["n_numerator"], chosen["denominator"],
                                  chosen["n_denominator"], MIN_SAMPLES_PER_LEVEL, args.assay))
            return emit(result, EXIT_REFUSED)

        # A menu number selects a formula built from the design (0315); anything else typed
        # is checked term by term and carries a warning that it was not chosen.
        formulas = formula_menu(design, args.assay, args.factor)
        token = (args.formula or DEFAULT_FORMULA).strip()
        picked = next((f for f in formulas if token in (f["n"], f["n"].lstrip("0"))), None)
        if picked is not None and not picked["estimable"]:
            result["error"] = "formula %s (%s) is not estimable: %s" % (
                picked["n"], picked["formula"], picked["reason"])
            result["formulas"] = formulas
            return emit(result, EXIT_REFUSED)
        formula = picked["formula"] if picked else token
        for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula):
            if term not in design[0]:
                result["error"] = ("formula term %r is not a column of the design table (%s)"
                                   % (term, ", ".join(design[0])))
                return emit(result, EXIT_REFUSED)
            stuck = next((f for f in formulas if not f["estimable"] and term in f["terms"]
                          and term != args.factor), None)
            if stuck is not None:
                result["error"] = "formula term %r is not estimable: %s" % (term, stuck["reason"])
                result["formulas"] = formulas
                return emit(result, EXIT_REFUSED)
        if args.formula is not None and picked is None:
            result["formula_warning"] = ("formula %r was typed, not chosen from `configure.py "
                                         "formulas`; T9 shows it as typed" % formula)
        updates += [("formula", '"%s"' % formula, "  "),
                    ("contrast", '"%s"' % chosen["spec"], "  ")]
        result.update({"contrast": chosen["spec"], "contrast_meaning": chosen["meaning"],
                       "formula": formula})

    elif shape == "peaks":
        if not args.peaks_type:
            result["error"] = "assay %s needs --peaks-type (see `configure.py peaks`)" % args.assay
            return emit(result, EXIT_USAGE)
        tok = args.peaks_type.strip().lower()
        chosen = next((e for e in PEAK_TYPES
                       if tok in (e["n"], e["n"].lstrip("0"), e["value"])), None)
        if chosen is None:
            result["error"] = ("could not resolve peak type %r; a menu number, `narrow` or "
                               "`broad`" % args.peaks_type)
            return emit(result, EXIT_REFUSED)
        # These two travel with the genome, never typed: a wrong mito name silently filters
        # nothing, and a wrong gsize shifts every peak call.
        for fact in ("mito_name", "macs_gsize"):
            if not genome.get(fact):
                result["error"] = ("the genome registry has no %s for %s; add the column value "
                                   "in _references/genomes.md before using this assay"
                                   % (fact, genome["id"]))
                return emit(result, EXIT_REFUSED)
        updates += [("type", chosen["value"], "  "),
                    ("macs_gsize", genome["macs_gsize"], "  "),
                    ("mito_name", genome["mito_name"], "  ")]
        result.update({"peaks_type": chosen["value"], "peaks_meaning": chosen["meaning"],
                       "macs_gsize": genome["macs_gsize"], "mito_name": genome["mito_name"]})

    elif shape == "protocol":
        if not args.protocol:
            result["error"] = ("assay %s needs --protocol (see `configure.py protocols`)"
                               % args.assay)
            return emit(result, EXIT_USAGE)
        aligner = (args.aligner or "simpleaf").strip()
        tok = args.protocol.strip()
        chosen = next((e for e in PROTOCOLS
                       if tok.lower() in (e["n"], e["n"].lstrip("0"))
                       or tok.upper() == e["value"].upper()), None)
        if chosen is None:
            result["error"] = ("could not resolve protocol %r; a menu number or one of %s"
                               % (args.protocol, ", ".join(e["value"] for e in PROTOCOLS)))
            return emit(result, EXIT_REFUSED)
        if aligner not in chosen["aligners"]:
            # Refused here as well as in the wrapper's preflight, because the pipeline would
            # pass an unsupported protocol to the aligner verbatim and produce a wrong matrix
            # rather than an error.
            result["error"] = ("protocol %s is not supported by aligner %s (supports: %s). "
                               "Choose another aligner, or a protocol that aligner supports."
                               % (chosen["value"], aligner, ", ".join(chosen["aligners"])))
            return emit(result, EXIT_REFUSED)
        # Both sit at the top level of the scrnaseq template, hence the empty indent.
        updates += [("protocol", chosen["value"], ""), ("aligner", aligner, "")]
        result.update({"protocol": chosen["value"], "protocol_meaning": chosen["meaning"],
                       "aligner": aligner})

    text = read = cfg.read_text(encoding="utf-8")
    for key in ("fasta_sha256", "gtf_sha256"):
        value = genome.get(key, "UNKNOWN")
        text, replaced = set_yaml_scalar(text, key, value, "  ")
        if not replaced:
            text = re.sub(r"^reference:\s*$", "reference:\n  %s: %s" % (key, value),
                          text, count=1, flags=re.M)
    applied = {}
    for key, value, indent in updates:
        text, ok = set_yaml_scalar(text, key, value, indent)
        applied[key] = ok
    if genome["derived_dir"]:
        # The cache line ships commented out; uncomment it rather than appending a duplicate.
        # The path is written even when the keyed directory does not exist yet: the wrapper
        # passes --save-reference on the first run and harvests the built indices into it.
        # An assay whose template carries no cache line (cutandrun, methylseq) is reported
        # honestly as not-applied.
        text, n = re.subn(r"^\s*#\s*derived_dir:.*$", "  derived_dir: %s" % genome["derived_dir"],
                          text, count=1, flags=re.M)
        applied["derived_dir"] = bool(n)

    remaining = [l.split(":", 1)[0].strip() for l in text.splitlines()
                 if "<REQUIRED" in l and not l.lstrip().startswith("#")]
    result.update({"genome": genome["id"], "derived_dir": genome["derived_dir"],
                   "applied": applied, "still_unfilled": remaining})
    if remaining:
        result["error"] = "keys still marked <REQUIRED> after applying: %s" % ", ".join(remaining)
        return emit(result, EXIT_REFUSED)

    shown = selections(result)
    record = Path(args.project) / dry_run_record(args.assay)
    if args.dry_run:
        with ws.atomic_open(record) as fh:
            json.dump({"assay": args.assay, "sha256": sha256_text(text),
                       "read_sha256": sha256_text(read), "selections": shown},
                      fh, indent=2, sort_keys=True)
            fh.write("\n")
        result["ok"] = True
        result["dry_run"] = True
        result["config_preview"] = text
        return emit(result, EXIT_OK)

    refusal = unmatched_dry_run(record, args.assay, text, shown, read)
    if refusal:
        result["error"] = refusal
        return emit(result, EXIT_REFUSED)

    with ws.atomic_open(cfg, newline=None) as fh:
        fh.write(text)
    result["ok"] = True
    result["wrote"] = "_config/%s.yaml" % args.assay
    result["config"] = cfg.read_text(encoding="utf-8")
    return emit(result, EXIT_OK)


# --- stage 01's declarations: closed menus, written by this script (S01-declare, 0313) ----------

# What each value means, in the order offered. The values are stage 01's own (CONFIG_RULES in
# stage01_samplesheet.py), and a test keeps the two sets equal. A declaration the user volunteers
# in their own words ("the libraries are dUTP") is answered with this menu, never written as typed:
# a strandedness or replication unit that is merely wrong runs and gives a confident wrong answer.
DECLARATION_MENUS = {
    "strandedness": [
        ("reverse", "read 1 is antisense to the transcript -- dUTP-based kits such as Illumina "
                    "TruSeq Stranded and NEBNext Ultra II Directional"),
        ("forward", "read 1 is sense to the transcript -- e.g. ligation-based kits"),
        ("unstranded", "the strand is not kept -- e.g. TruSeq non-stranded"),
        ("auto", "let nf-core infer it from the reads; an unstranded library then reads as a "
                 "strandedness warning (pending D-24)"),
    ],
    "unit_of_replication": [
        ("sample", "each sample is an independent biological replicate"),
        ("subject", "samples from one donor, patient or model are not independent; the "
                    "subject column is the unit (it must be filled)"),
        ("cell_pseudobulk", "cells aggregated per sample into pseudobulk profiles"),
    ],
    "paired": [
        ("paired", "the same subject appears in more than one condition (e.g. before and after) "
                   "and the model pairs them"),
        ("unpaired", "no subject appears in more than one condition"),
    ],
}
#: The keys stage 01 checks, per assay, in the order T9 shows them.
DECLARATION_KEYS = {
    "rnaseq_bulk": ["strandedness", "unit_of_replication", "reference_release", "paired"],
    "atacseq_bulk": ["unit_of_replication", "reference_release", "paired"],
}
#: `paired` may stay undeclared (no pairing); the others stop stage 01 until declared.
OPTIONAL_DECLARATIONS = ("paired",)


def declaration_menu(key, workspace):
    """[(value, meaning)] for one key, or (None, error). The release comes from the registry."""
    if key != "reference_release":
        return DECLARATION_MENUS[key], None
    rows, err = read_genomes(workspace)
    if err:
        return None, err
    menu = []
    for r in sorted(rows, key=lambda x: x["id"]):
        release = r.get("annotation_release") or r["source"]
        menu.append(("%s %s" % (r["id"], release) if release else r["id"],
                     "%s %s, %s" % (r["species"], r["build"], r["source"])))
    return menu, None


def numbered(menu):
    return [{"n": "%02d" % i, "value": v, "meaning": m} for i, (v, m) in enumerate(menu, start=1)]


def declared_value(text, key):
    """The last zero-indent `key:` scalar, as stage 01 reads it; '' when undeclared."""
    found = None
    for line in text.splitlines():
        m = re.match(r"^%s:\s*(.*)$" % re.escape(key), line)
        if m:
            found = m.group(1)
    value = (found or "").split("#", 1)[0].strip().strip("\"'")
    if not value or value.lower() in ("null", "~") or value.startswith("<REQUIRED"):
        return ""
    return value


def set_declaration(text, key, value):
    """Every zero-indent `key:` line becomes `key: value`; a missing key is added after the
    stage 01 block (the reference_release line), else at the end. Other lines are kept."""
    line = "%s: %s" % (key, value)
    pattern = re.compile(r"^%s:.*$" % re.escape(key), re.M)
    if pattern.search(text):
        return pattern.sub(lambda _: line, text)
    anchor = re.search(r"^reference_release:.*$", text, re.M)
    if anchor:
        return text[:anchor.end()] + "\n" + line + text[anchor.end():]
    return text + ("" if text.endswith("\n") or not text else "\n") + line + "\n"


def cmd_declare(args, workspace):
    result = {"command": "declare", "ok": False, "assay": args.assay}
    keys = DECLARATION_KEYS.get(args.assay)
    if keys is None:
        result["error"] = ("stage 01 takes no declarations for assay %r; it does for %s"
                           % (args.assay, ", ".join(sorted(DECLARATION_KEYS))))
        return emit(result, EXIT_USAGE)
    project = Path(args.project)
    cfg = project / "_config" / ("%s.yaml" % args.assay)
    if not cfg.is_file():
        result["error"] = "no config at _config/%s.yaml; stage 00 seeds it at project creation" % args.assay
        return emit(result, EXIT_USAGE)
    text = cfg.read_text(encoding="utf-8")

    if args.key is None:
        if args.select is not None:
            result["error"] = "--select needs --key: one declaration at a time"
            return emit(result, EXIT_USAGE)
        listed = [{"key": k, "value": declared_value(text, k),
                   "optional": k in OPTIONAL_DECLARATIONS} for k in keys]
        result.update({"ok": True, "keys": listed,
                       "undeclared": [e["key"] for e in listed
                                      if not e["value"] and not e["optional"]]})
        return emit(result, EXIT_OK)

    result["key"] = args.key
    if args.key not in keys:
        result["error"] = ("assay %s does not declare %s; its declarations: %s"
                           % (args.assay, args.key, ", ".join(keys)))
        return emit(result, EXIT_USAGE)
    menu, err = declaration_menu(args.key, workspace)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)
    result["options"] = numbered(menu)
    result["current"] = declared_value(text, args.key)
    if args.select is None:
        result["ok"] = True
        return emit(result, EXIT_OK)

    token = args.select.strip()
    chosen = next((o for o in result["options"]
                   if token in (o["n"], o["n"].lstrip("0"), o["value"])), None)
    if chosen is None:
        result["error"] = ("%r is not on the %s menu; reply with a menu number (1-%d). A value in "
                           "other words is answered with this menu, never written as typed."
                           % (args.select, args.key, len(result["options"])))
        return emit(result, EXIT_REFUSED)

    updated = set_declaration(text, args.key, chosen["value"])
    entry = "%s %s %s: %s; chosen from the configure.py declare menu, option %s" % (
        datetime.date.today().isoformat(), args.assay, args.key, chosen["value"], chosen["n"])
    history = project / "HISTORY.md"
    before = history.read_text(encoding="utf-8") if history.is_file() else ""
    with ws.atomic_open(cfg, newline=None) as fh:
        fh.write(updated)
    with ws.atomic_open(history, newline=None) as fh:
        fh.write(before + ("" if before.endswith("\n") or not before else "\n") + entry + "\n")
    result.update({"ok": True, "value": chosen["value"], "meaning": chosen["meaning"],
                   "selected": chosen["n"], "wrote": "_config/%s.yaml" % args.assay,
                   "history_entry": entry})
    return emit(result, EXIT_OK)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workspace", type=Path, default=None)
    sub = ap.add_subparsers(dest="cmd")

    g = sub.add_parser("genomes", help="list registered references; resolve a selection")
    g.add_argument("--select", default=None)
    g.add_argument("--assay", default=None,
                   help="key the derived-cache column to this assay's pinned pipeline")

    pk = sub.add_parser("peaks", help="the closed peak-type menu (narrow | broad)")
    pk.add_argument("--select", default=None)

    pr = sub.add_parser("protocols", help="the closed library-chemistry menu")
    pr.add_argument("--select", default=None)
    pr.add_argument("--aligner", default=None,
                    help="show only chemistries this aligner supports")

    c = sub.add_parser("contrasts", help="levels present in the design, as ordered pairs")
    c.add_argument("--project", required=True)
    c.add_argument("--assay", required=True)
    c.add_argument("--factor", default="condition")

    fm = sub.add_parser("formulas", help="design formulas built from the design's own columns")
    fm.add_argument("--project", required=True)
    fm.add_argument("--assay", required=True)
    fm.add_argument("--factor", default="condition")

    a = sub.add_parser("apply", help="validate the selections and write the config")
    a.add_argument("--project", required=True)
    a.add_argument("--assay", required=True)
    a.add_argument("--genome", required=True, help="menu number or genome ID")
    a.add_argument("--protocol", default=None,
                   help="library chemistry (see `configure.py protocols`)")
    a.add_argument("--aligner", default=None,
                   help="scrnaseq quantifier: simpleaf | star | kallisto "
                        "(default simpleaf)")
    a.add_argument("--contrast", default=None,
                   help="menu number or factor,num,denom (assays with a de block)")
    a.add_argument("--peaks-type", default=None,
                   help="menu number, `narrow` or `broad` (assays with a peaks block)")
    a.add_argument("--formula", default=None,
                   help="menu number from `formulas`, or a typed formula (written with a "
                        "warning); default: %s" % DEFAULT_FORMULA)
    a.add_argument("--factor", default="condition")
    a.add_argument("--dry-run", action="store_true",
                   help="show the result and record it; the config is written only by a later "
                        "apply whose result equals it")

    d = sub.add_parser("declare", help="stage 01's declarations as numbered menus; write one")
    d.add_argument("--project", required=True)
    d.add_argument("--assay", required=True)
    d.add_argument("--key", default=None,
                   choices=sorted({k for keys in DECLARATION_KEYS.values() for k in keys}),
                   help="the declaration to show or write; omit to list them")
    d.add_argument("--select", default=None, help="menu number of the value to write")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help(sys.stderr)
        return EXIT_USAGE
    workspace = args.workspace or ws.workspace_root(__file__)
    return {"genomes": cmd_genomes, "contrasts": cmd_contrasts, "peaks": cmd_peaks,
            "protocols": cmd_protocols, "declare": cmd_declare, "formulas": cmd_formulas,
            "apply": cmd_apply}[args.cmd](args, workspace)


if __name__ == "__main__":
    sys.exit(main())
