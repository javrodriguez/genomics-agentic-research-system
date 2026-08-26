#!/usr/bin/env python3
"""Complete a project's `_config/<Assay ID>.yaml` from closed menus, not free text.

Stage 00 seeds the config with everything derivable filled and the scientific decisions marked
`<REQUIRED>`. This resolves those, by offering choices rather than asking the user to type paths
and level names:

    genomes    the registered references            -> fills fasta + gtf + derived_dir together
    contrasts  the levels actually in the design     -> fills de.contrast, direction included
    apply      validate the selections and write     -> prints the resulting file

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
    """Parse the single table in _references/genomes.md."""
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
}


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

    if shape == "de":
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

        formula = args.formula or DEFAULT_FORMULA
        for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula):
            if term not in design[0]:
                result["error"] = ("formula term %r is not a column of the design table (%s)"
                                   % (term, ", ".join(design[0])))
                return emit(result, EXIT_REFUSED)
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

    text = cfg.read_text(encoding="utf-8")
    applied = {}
    for key, value, indent in updates:
        text, ok = set_yaml_scalar(text, key, value, indent)
        applied[key] = ok
    if genome["derived_dir"]:
        # The cache line ships commented out; uncomment it rather than appending a duplicate.
        # The path is written even when the keyed directory does not exist yet: the wrapper
        # passes --save-reference on the first run and harvests the built indices into it.
        text = re.sub(r"^\s*#\s*derived_dir:.*$", "  derived_dir: %s" % genome["derived_dir"],
                      text, count=1, flags=re.M)
        applied["derived_dir"] = True

    remaining = [l.split(":", 1)[0].strip() for l in text.splitlines()
                 if "<REQUIRED" in l and not l.lstrip().startswith("#")]
    result.update({"genome": genome["id"], "derived_dir": genome["derived_dir"],
                   "applied": applied, "still_unfilled": remaining})
    if remaining:
        result["error"] = "keys still marked <REQUIRED> after applying: %s" % ", ".join(remaining)
        return emit(result, EXIT_REFUSED)

    if args.dry_run:
        result["ok"] = True
        result["dry_run"] = True
        result["config_preview"] = text
        return emit(result, EXIT_OK)

    with ws.atomic_open(cfg, newline=None) as fh:
        fh.write(text)
    result["ok"] = True
    result["wrote"] = "_config/%s.yaml" % args.assay
    result["config"] = cfg.read_text(encoding="utf-8")
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

    c = sub.add_parser("contrasts", help="levels present in the design, as ordered pairs")
    c.add_argument("--project", required=True)
    c.add_argument("--assay", required=True)
    c.add_argument("--factor", default="condition")

    a = sub.add_parser("apply", help="validate the selections and write the config")
    a.add_argument("--project", required=True)
    a.add_argument("--assay", required=True)
    a.add_argument("--genome", required=True, help="menu number or genome ID")
    a.add_argument("--contrast", default=None,
                   help="menu number or factor,num,denom (assays with a de block)")
    a.add_argument("--peaks-type", default=None,
                   help="menu number, `narrow` or `broad` (assays with a peaks block)")
    a.add_argument("--formula", default=None, help="default: %s" % DEFAULT_FORMULA)
    a.add_argument("--factor", default="condition")
    a.add_argument("--dry-run", action="store_true", help="show the result without writing")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help(sys.stderr)
        return EXIT_USAGE
    workspace = args.workspace or ws.workspace_root(__file__)
    return {"genomes": cmd_genomes, "contrasts": cmd_contrasts, "peaks": cmd_peaks,
            "apply": cmd_apply}[args.cmd](args, workspace)


if __name__ == "__main__":
    sys.exit(main())
