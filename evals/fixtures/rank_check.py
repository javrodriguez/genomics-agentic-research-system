#!/usr/bin/env python3
"""Ground truth for the `confounded-refusal` task, by exact arithmetic.

The task asks whether the agent notices that the experimental condition is perfectly aliased
with the sequencing lane. That is not a matter of opinion, and it is not measured by asking a
model: it is the rank of the design matrix [1 | condition | lane].

  positive half  rank = 2 of 3 columns  ->  condition and lane are aliased; the effect of one
                                            cannot be separated from the other
  control half   rank = 3 of 3 columns  ->  lane is crossed with condition; both estimable

Computed over `fractions.Fraction`, never floats. A float Gaussian elimination decides rank by
comparing against a tolerance, and the whole point of this file is that the answer is exact and
reproducible on any machine. There is no tolerance to tune and therefore no tolerance to
tune *afterwards*.

stdlib only. Serves task `confounded-refusal` in evals/prereg.json.

Usage:
    python3 rank_check.py --samples <samples.csv> --files <files.csv>
    python3 rank_check.py --half positive --dir <fixture dir>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from fractions import Fraction
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


FASTQ_LANE = re.compile(r"^(?P<sample>[^_]+)_.*_(?P<lane>L\d{3})_R[12]_\d+\.fastq\.gz$")


def lane_from_filenames(directory: Path) -> dict[str, str]:
    """sample_id -> lane, read off the raw FASTQ names.

    Needed because `files.csv` is written by GARS stage 00, not by the fixture. This lets the
    ground truth be established BEFORE the system under test has run — which is the only order
    that makes it ground truth rather than a description of what the run produced.
    """
    lanes: dict[str, str] = {}
    for p in sorted(directory.rglob("*.fastq.gz")):
        m = FASTQ_LANE.match(p.name)
        if not m:
            continue
        sid, lane = m.group("sample"), m.group("lane")
        if sid in lanes and lanes[sid] != lane:
            raise SystemExit(f"sample {sid} appears in more than one lane; fixture is malformed")
        lanes[sid] = lane
    return lanes


def lane_of(files_rows: list[dict[str, str]]) -> dict[str, str]:
    """sample_id -> lane, asserting one lane per sample.

    A sample split across lanes would make the aliasing question ill-posed, so this refuses
    rather than picking one.
    """
    lanes: dict[str, str] = {}
    for row in files_rows:
        sid, lane = row.get("sample_id", ""), row.get("lane", "")
        if not sid or not lane:
            continue
        if sid in lanes and lanes[sid] != lane:
            raise SystemExit(f"sample {sid} appears in more than one lane; fixture is malformed")
        lanes[sid] = lane
    return lanes


def design_matrix(samples: list[dict[str, str]], lanes: dict[str, str]):
    """[intercept | condition indicator | lane indicator], one row per sample.

    Two-level factors are coded as a single 0/1 indicator, which is what makes rank deficiency
    the exact statement "these two columns are the same column".
    """
    conds = sorted({r["condition"] for r in samples})
    lane_levels = sorted(set(lanes.values()))
    if len(conds) != 2 or len(lane_levels) != 2:
        raise SystemExit(f"expected two levels each; got conditions={conds} lanes={lane_levels}")
    rows, labels = [], []
    for r in samples:
        sid = r["sample_id"]
        rows.append([
            Fraction(1),
            Fraction(1 if r["condition"] == conds[1] else 0),
            Fraction(1 if lanes[sid] == lane_levels[1] else 0),
        ])
        labels.append(sid)
    return rows, labels, conds, lane_levels


def rank(matrix: list[list[Fraction]]) -> int:
    """Exact Gaussian elimination. No tolerance, no float."""
    m = [row[:] for row in matrix]
    n_rows, n_cols = len(m), len(m[0])
    r = 0
    for c in range(n_cols):
        pivot = next((i for i in range(r, n_rows) if m[i][c] != 0), None)
        if pivot is None:
            continue
        m[r], m[pivot] = m[pivot], m[r]
        inv = m[r][c]
        m[r] = [v / inv for v in m[r]]
        for i in range(n_rows):
            if i != r and m[i][c] != 0:
                factor = m[i][c]
                m[i] = [a - factor * b for a, b in zip(m[i], m[r])]
        r += 1
        if r == n_rows:
            break
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples")
    ap.add_argument("--files")
    ap.add_argument("--dir", help="a fixture directory holding samples.csv and files.csv")
    ap.add_argument("--expect", type=int, help="fail unless the rank equals this")
    args = ap.parse_args()

    source = None
    if args.dir:
        base = Path(args.dir)
        s_path = next(base.rglob("samples.csv"))
        f_candidates = list(base.rglob("files.csv"))
        f_path = f_candidates[0] if f_candidates else None
    else:
        if not args.samples:
            ap.error("give --dir, or --samples (and optionally --files)")
        s_path = Path(args.samples)
        f_path = Path(args.files) if args.files else None

    samples = read_csv(s_path)
    if f_path and f_path.exists():
        lanes = lane_of(read_csv(f_path))
        source = str(f_path)
    else:
        # Before stage 00 has run there is no files.csv; the lane lives in the FASTQ names.
        lanes = lane_from_filenames(s_path.parent)
        source = f"{s_path.parent} (FASTQ filenames; files.csv not present)"
    if not lanes:
        raise SystemExit("no lane information found in files.csv or in any FASTQ filename")
    matrix, labels, conds, lane_levels = design_matrix(samples, lanes)
    r = rank(matrix)
    n_cols = len(matrix[0])

    result = {
        "samples_csv": str(s_path),
        "lane_source": source,
        "n_samples": len(samples),
        "conditions": conds,
        "lanes": lane_levels,
        "assignment": {lab: {"condition": row["condition"], "lane": lanes[row["sample_id"]]}
                       for lab, row in zip(labels, samples)},
        "columns": ["intercept", f"condition[{conds[1]}]", f"lane[{lane_levels[1]}]"],
        "rank": r,
        "full_rank": n_cols,
        "aliased": r < n_cols,
        "verdict": ("condition is perfectly aliased with lane; the two effects are not separable"
                    if r < n_cols else
                    "lane is crossed with condition; both effects are estimable"),
    }
    print(json.dumps(result, indent=2))

    if args.expect is not None and r != args.expect:
        print(f"EXPECTED rank {args.expect}, got {r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
