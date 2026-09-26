#!/usr/bin/env python3
"""Aggregate diff of a re-run's DE table against the original's -- "re-run diff explained".

Row 13 step A (decision 0140, D4). Stdlib-only; written for Python 3.6.8 (syntax checked, not
executed on 3.6.8).

    python3 scripts/rerun_diff.py --comparison <out>/comparison.json

Reads row 6's `comparison.json` (written by `scripts/rerun_check.py`): `runs` (each
`{run, job, match, reason, artifacts, code}`) and `original` (the absolute path of the original
stage's `reproducibility/manifest.json`); every other key is carried unread. The original stage
folder is the parent of the parent of `original`; run n's re-run stage folder is
`<folder holding comparison.json>/run-<n>/02_bioinformatics/<assay>/<substage>/`, with
`<assay>/<substage>` the original stage folder's last two parts. Per run, the one artifact
whose path ends in `de_results.csv` is compared: both tables must hash to the artifact's
`original_sha256` / `replay_sha256`.

Prints one block of aggregates per run, in `runs` order. It never prints a gene identifier, a
sample name, a path or any `reason` text, and it changes no tolerance. The DE table has no Wald
`stat` column, so the rank correlation is Spearman's over `log2FoldChange` and is printed under
that name. `NA` or empty `padj` is counted, never dropped silently; a gene whose `padj` moves
between `NA` and a value is not a crossing and shows only in `na_padj`. An empty `runs` list and a
repeated run number are refused (ruling L5). Refusals exit 2 with a fixed reason code on stderr;
input that crashes a parser (a NUL byte, runaway nesting) is a fixed code too, never a traceback.
Refusal codes are required to be the same on every Python from 3.6 to 3.13, tested by emulating
both sides of each known split (tests/pilot_emulation.py); executed on CPython 3.8.2, 3.8.19,
3.9.6, 3.9.21, 3.10.16, 3.12.9, 3.12.14, 3.13.2 and 3.14.7, not on 3.6, 3.7 or 3.11. To that
end a NUL byte is refused before the csv module sees it (3.11 and later read one as data), JSON
integers are parsed as decimals, never through `int()` of their text (whose digits 3.11 and
later cap), and `comparison.json` is read as UTF-8 whatever the locale. A decimal signal is
`value_out_of_range`, never a traceback.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from decimal import Decimal, DecimalException
from pathlib import Path, PurePosixPath

EXIT_REFUSED = 2
DE_COLUMNS = ("gene", "baseMean", "log2FoldChange", "pvalue", "padj")
DE_SUFFIX = "de_results.csv"
PADJ_THRESHOLD = 0.05


class Refused(Exception):
    """A named refusal; the reason is a fixed code, never input text."""


def number(text):
    """A finite float, or None for NA/empty/NaN; anything else is refused."""
    if text in ("", "NA"):
        return None
    try:
        value = float(text)
    except ValueError:
        raise Refused("table_value")
    if math.isnan(value):
        return None
    if math.isinf(value):
        raise Refused("table_value")
    return value


def read_table(path, expected_sha):
    try:
        data = Path(path).read_bytes()
    except (OSError, ValueError):
        raise Refused("table_unreadable")
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise Refused("table_sha256_mismatch")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("table_unreadable")
    if "\x00" in text:
        raise Refused("table_malformed")  # 3.10 and earlier raise on it; 3.11 and later read it
    reader = csv.DictReader(io.StringIO(text))
    try:
        rows = list(reader)
        fieldnames = reader.fieldnames
    except csv.Error:
        raise Refused("table_malformed")
    if any(c not in (fieldnames or []) for c in DE_COLUMNS):
        raise Refused("table_columns")
    table = {}
    seen = 0
    for row in rows:
        seen += 1
        if None in row or any(v is None for v in row.values()):
            raise Refused("table_row_shape")
        gene = row["gene"]
        if not gene.strip():
            raise Refused("table_empty_gene")
        if gene in table:
            raise Refused("table_duplicate_gene")
        table[gene] = (number(row["log2FoldChange"]), number(row["padj"]))
    return data, table, seen


def ranks(values):
    """Average ranks (1-based), ties sharing the mean of their positions."""
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return out


def spearman(pairs):
    if len(pairs) < 2:
        return None
    a = ranks([p[0] for p in pairs])
    b = ranks([p[1] for p in pairs])
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va == 0 or vb == 0:
        return None
    return cov / math.sqrt(va * vb)


def fmt(value):
    return "uncomputable" if value is None else "%.6g" % value


def safe_relative(text):
    if not isinstance(text, str) or not text:
        raise Refused("artifact_path")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise Refused("artifact_path")
    return path


def compare(original, replay):
    """Aggregates of two parsed tables; no identifier leaves this function."""
    (a_bytes, a, a_seen), (b_bytes, b, b_seen) = original, replay
    matched = sorted(set(a) & set(b))
    lfc = [(a[g][0], b[g][0]) for g in matched if a[g][0] is not None and b[g][0] is not None]
    padj = [(a[g][1], b[g][1]) for g in matched if a[g][1] is not None and b[g][1] is not None]
    rel = []
    for x, y in padj:
        top = max(abs(x), abs(y))
        rel.append(0.0 if top == 0 else abs(x - y) / top)
    graded = len(a) + len(b)
    return [
        "rows original/re-run: %d/%d" % (len(a), len(b)),
        "genes matched: %d" % len(matched),
        "genes only in original: %d" % len(set(a) - set(b)),
        "genes only in re-run: %d" % len(set(b) - set(a)),
        "byte_equal: %s" % ("yes" if a_bytes == b_bytes else "no"),
        "max_abs_delta log2FoldChange: %s"
        % fmt(max(abs(x - y) for x, y in lfc) if lfc else None),
        "max_rel_delta padj: %s" % fmt(max(rel) if rel else None),
        "spearman log2FoldChange: %s" % fmt(spearman(lfc)),
        "crossings padj<0.05 (gained/lost): %d/%d"
        % (sum(1 for x, y in padj if x >= PADJ_THRESHOLD and y < PADJ_THRESHOLD),
           sum(1 for x, y in padj if x < PADJ_THRESHOLD and y >= PADJ_THRESHOLD)),
        "sign flips: %d" % sum(1 for x, y in lfc if x * y < 0),
        "na_padj original/re-run: %d/%d" % (sum(1 for v in a.values() if v[1] is None),
                                            sum(1 for v in b.values() if v[1] is None)),
        "na_log2FoldChange original/re-run: %d/%d"
        % (sum(1 for v in a.values() if v[0] is None), sum(1 for v in b.values() if v[0] is None)),
        "graded %d of %d rows" % (graded, a_seen + b_seen),
    ]


def diff(comparison_path):
    comparison_path = Path(comparison_path)
    try:
        data = json.loads(comparison_path.read_text(encoding="utf-8"), parse_int=Decimal)
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        raise Refused("comparison_unreadable")
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        raise Refused("comparison_runs")
    if not data["runs"]:
        raise Refused("comparison_runs_empty")
    original = data.get("original")
    if not isinstance(original, str) or not Path(original).is_absolute():
        raise Refused("comparison_original")
    stage = Path(original).parent.parent
    if len(stage.parts) < 3:
        raise Refused("comparison_original")
    assay, substage = stage.parts[-2], stage.parts[-1]
    blocks = []
    numbers = set()
    for run in data["runs"]:
        if not isinstance(run, dict) or not isinstance(run.get("artifacts"), list):
            raise Refused("comparison_run")
        n = run.get("run")
        if not isinstance(n, Decimal) or n < 0:
            raise Refused("comparison_run_number")
        n = abs(n)  # an integer literal, printed from its digits; -0 is run 0
        if n in numbers:
            raise Refused("comparison_run_duplicate")
        numbers.add(n)
        chosen = [x for x in run["artifacts"]
                  if isinstance(x, dict) and isinstance(x.get("path"), str)
                  and x["path"].endswith(DE_SUFFIX)]
        if len(chosen) != 1:
            raise Refused("de_artifact_count")
        artifact = chosen[0]
        relative = safe_relative(artifact["path"])
        for key in ("original_sha256", "replay_sha256"):
            if not isinstance(artifact.get(key), str):
                raise Refused("artifact_sha256")
        replay_stage = (comparison_path.parent / ("run-%s" % n) / "02_bioinformatics"
                        / assay / substage)
        first = read_table(stage / str(relative), artifact["original_sha256"])
        second = read_table(replay_stage / str(relative), artifact["replay_sha256"])
        blocks.append(["run %s" % n] + compare(first, second))
    return ["runs: %d" % len(blocks)] + [line for block in blocks for line in block]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Aggregate re-run diff of the DE table.")
    ap.add_argument("--comparison", required=True)
    args = ap.parse_args(argv)
    try:
        lines = diff(args.comparison)
    except Refused as why:
        sys.stderr.write("refused: %s\n" % why)
        return EXIT_REFUSED
    except DecimalException:
        sys.stderr.write("refused: value_out_of_range\n")
        return EXIT_REFUSED
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
