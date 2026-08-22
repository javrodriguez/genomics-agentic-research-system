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
                     "derived_dir": cells[6] if len(cells) > 6 and cells[6] else None})
    if not rows:
        return None, "genome registry has no table headed `| ID | Species |`"
    return rows, None


def genome_menu(rows):
    out = []
    for i, r in enumerate(sorted(rows, key=lambda x: x["id"]), start=1):
        entry = dict(r)
        entry["n"] = "%02d" % i
        # Report readability now rather than failing hours into a run.
        entry["fasta_readable"] = os.access(r["fasta"], os.R_OK)
        entry["gtf_readable"] = os.access(r["gtf"], os.R_OK)
        entry["cached_indices"] = bool(r["derived_dir"] and os.path.isdir(r["derived_dir"]))
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
    menu = genome_menu(rows)
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


def cmd_apply(args, workspace):
    result = {"command": "apply", "ok": False, "assay": args.assay}
    cfg = Path(args.project) / "_config" / ("%s.yaml" % args.assay)
    if not cfg.is_file():
        result["error"] = "no config at _config/%s.yaml; stage 00 seeds it at project creation" % args.assay
        return emit(result, EXIT_USAGE)

    rows, err = read_genomes(workspace)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)
    genome = resolve_genome(genome_menu(rows), args.genome)
    if genome is None:
        result["error"] = "could not resolve genome %r" % args.genome
        return emit(result, EXIT_REFUSED)
    for label, p in (("fasta", genome["fasta"]), ("gtf", genome["gtf"])):
        if not os.access(p, os.R_OK):
            result["error"] = "%s for %s is not readable: %s" % (label, genome["id"], p)
            return emit(result, EXIT_REFUSED)

    design, err = read_design(args.project, args.assay)
    if err:
        result["error"] = err
        return emit(result, EXIT_USAGE)
    levels, counts, pairs = contrast_menu(design, args.factor)
    chosen = None
    for p in pairs:
        if args.contrast.strip() in (p["n"], p["n"].lstrip("0"), p["spec"]):
            chosen = p
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

    text = cfg.read_text(encoding="utf-8")
    applied = {}
    for key, value, indent in (("fasta", genome["fasta"], "  "),
                               ("gtf", genome["gtf"], "  "),
                               ("formula", '"%s"' % formula, "  "),
                               ("contrast", '"%s"' % chosen["spec"], "  ")):
        text, ok = set_yaml_scalar(text, key, value, indent)
        applied[key] = ok
    if genome["derived_dir"]:
        # The cache line ships commented out; uncomment it rather than appending a duplicate.
        text = re.sub(r"^\s*#\s*derived_dir:.*$", "  derived_dir: %s" % genome["derived_dir"],
                      text, count=1, flags=re.M)
        applied["derived_dir"] = True

    remaining = [l.split(":", 1)[0].strip() for l in text.splitlines()
                 if "<REQUIRED" in l and not l.lstrip().startswith("#")]
    result.update({"genome": genome["id"], "contrast": chosen["spec"],
                   "contrast_meaning": chosen["meaning"], "formula": formula,
                   "derived_dir": genome["derived_dir"], "applied": applied,
                   "still_unfilled": remaining})
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

    c = sub.add_parser("contrasts", help="levels present in the design, as ordered pairs")
    c.add_argument("--project", required=True)
    c.add_argument("--assay", required=True)
    c.add_argument("--factor", default="condition")

    a = sub.add_parser("apply", help="validate the selections and write the config")
    a.add_argument("--project", required=True)
    a.add_argument("--assay", required=True)
    a.add_argument("--genome", required=True, help="menu number or genome ID")
    a.add_argument("--contrast", required=True, help="menu number or factor,num,denom")
    a.add_argument("--formula", default=None, help="default: %s" % DEFAULT_FORMULA)
    a.add_argument("--factor", default="condition")
    a.add_argument("--dry-run", action="store_true", help="show the result without writing")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help(sys.stderr)
        return EXIT_USAGE
    workspace = args.workspace or ws.workspace_root(__file__)
    return {"genomes": cmd_genomes, "contrasts": cmd_contrasts,
            "apply": cmd_apply}[args.cmd](args, workspace)


if __name__ == "__main__":
    sys.exit(main())
