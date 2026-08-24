#!/usr/bin/env python3
"""Reshape an nf-core count matrix into the form `rnaseq-de` actually accepts.

The two skills declare each other as chaining partners and their formats do not meet. This is the
adaptation layer that makes the handoff work, and it lives here rather than in a heredoc inside a
generated `submit.sh` because it has one job with one correct answer -- and because the version
that lived in a heredoc omitted the rename below and produced 22,783 anonymous genes.

Three reshapes, and the third is the one that bites:

1. `gene_name` is dropped. `rnaseq-de` coerces every column after the first to numeric, so a text
   column raises `Count matrix contains non-numeric entries`. The mapping is preserved separately
   so results can be annotated afterwards.
2. Counts are rounded to integers. nf-core emits length-scaled floats; DESeq2 wants counts.
3. **The identifier column is renamed to `gene`.** This is not cosmetic. The skill does
   `results_df.reset_index().rename(columns={"index": "gene"})`, which assumes an *unnamed* index.
   Given `gene_id`, `reset_index()` yields a column called `gene_id`, the rename matches nothing,
   and the identifier is then dropped from the output column selection -- **with no error**. The
   result is a complete, plausible differential-expression table in which every gene is anonymous.
   It surfaced only because a later line crashed on `row.gene`; without that crash it would have
   looked publishable. See docs/decisions/0010-skill-chaining-defects-and-adaptation.md.

Adaptation may only reshape: rename columns, drop non-essential columns, change numeric type. It
may never filter rows, alter values, or aggregate -- that is analysis, and belongs in a sub-stage's
Process where it is recorded in HISTORY.md.

Stdlib only. Exit codes: 0 ok / 1 the input is not the expected shape / 3 usage.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workspace as ws          # noqa: E402

ID_COLUMN = "gene"              # what rnaseq-de requires. Do not change without reading above.
EXIT_OK, EXIT_BAD_INPUT, EXIT_USAGE = 0, 1, 3


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--counts", required=True, help="native matrix from 02.01")
    ap.add_argument("--out", required=True, help="this sub-stage's adapted/ directory")
    ap.add_argument("--id-column", default="gene_id")
    ap.add_argument("--name-column", default="gene_name")
    args = ap.parse_args(argv)

    result = {"command": "adapt_counts", "ok": False, "source": args.counts}
    src = Path(args.counts)
    if not src.is_file():
        result["error"] = "count matrix not found: %s" % src
        return emit(result, EXIT_USAGE)

    with src.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            result["error"] = "count matrix is empty"
            return emit(result, EXIT_BAD_INPUT)
        if args.id_column not in header:
            result["error"] = ("no %r column in the matrix header (%s); this is not the nf-core "
                               "shape this adaptation expects"
                               % (args.id_column, ", ".join(header[:5])))
            return emit(result, EXIT_BAD_INPUT)
        gi = header.index(args.id_column)
        gn = header.index(args.name_column) if args.name_column in header else None
        sample_cols = [i for i in range(len(header)) if i != gi and i != gn]

        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        rows = 0
        nonint = 0
        with ws.atomic_open(out / "counts_gene.tsv") as fc, \
                ws.atomic_open(out / "gene_id_to_name.tsv") as fm:
            wc = csv.writer(fc, delimiter="\t", lineterminator="\n")
            wm = csv.writer(fm, delimiter="\t", lineterminator="\n")
            # The rename happens here and nowhere else.
            wc.writerow([ID_COLUMN] + [header[i] for i in sample_cols])
            wm.writerow([args.id_column, args.name_column])
            for row in reader:
                if not row:
                    continue
                counts = []
                for i in sample_cols:
                    v = row[i]
                    try:
                        counts.append(str(int(round(float(v)))))
                    except ValueError:
                        nonint += 1
                        counts.append(v)
                wc.writerow([row[gi]] + counts)
                if gn is not None:
                    wm.writerow([row[gi], row[gn]])
                rows += 1

    if nonint:
        result["error"] = ("%d value(s) in the count columns are not numeric; the matrix is not "
                           "the expected shape" % nonint)
        return emit(result, EXIT_BAD_INPUT)

    # Verify what was written, rather than assuming the write did what the code says.
    back = (out / "counts_gene.tsv").read_text(encoding="utf-8").splitlines()
    written_header = back[0].split("\t") if back else []
    if not written_header or written_header[0] != ID_COLUMN:
        result["error"] = ("adapted matrix header starts with %r, not %r -- rnaseq-de would drop "
                           "the identifier silently"
                           % (written_header[0] if written_header else "", ID_COLUMN))
        return emit(result, EXIT_BAD_INPUT)
    if len(back) - 1 != rows:
        result["error"] = "wrote %d rows but read back %d" % (rows, len(back) - 1)
        return emit(result, EXIT_BAD_INPUT)

    result.update({"ok": True, "rows": rows, "samples": len(sample_cols),
                   "id_column": ID_COLUMN, "renamed_from": args.id_column,
                   "counts": str(out / "counts_gene.tsv"),
                   "id_map": str(out / "gene_id_to_name.tsv")})
    return emit(result, EXIT_OK)


if __name__ == "__main__":
    sys.exit(main())
