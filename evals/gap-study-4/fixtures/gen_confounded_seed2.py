#!/usr/bin/env python3
"""The second seed of the first study's matched fixture pair, for round 4's task `confounded-design`.

    python3 evals/gap-study-4/fixtures/gen_confounded_seed2.py --half positive --seed <seed> --out <staging>
    python3 evals/gap-study-4/fixtures/gen_confounded_seed2.py --half control  --seed <seed> --out <staging>
    python3 evals/gap-study-4/fixtures/gen_confounded_seed2.py --check      this module's own clauses, at SEED

WHAT IT BUILDS. The first study's pair, rebuilt from a second seed with the first study's own builder, `gen_fastq.py`
(an identical copy beside this file, loaded by path, never edited): the same six samples, the same frozen
samples.csv (md5 4f11b01178e3b6baedc2b12634e6dc0a, on both halves), the same non-FASTQ run sheet, twelve gzipped
FASTQs of three reads each written by gen_fastq's own `read_bytes`, `gzip_bytes` and `fastq_filename`. The layout
it writes is gen_fastq's: `<out>/src/<12 FASTQs + the run sheet>` and `<out>/samples.csv`, and its stdout is one
JSON manifest. The driver then runs the identical copies of `neutralise.py --dir` and `rank_check.py --dir
--expect` on it (the `first-study` fixture kind: drive.py 780-830 at 62181cbe; check_task.py `_build`).

WHAT THE SEED CHANGES (this lane's decision `seed-2-instance`, recorded in tasks/confounded-design.json):

  - the read bytes, through gen_fastq.read_bytes(seed, sample, read), exactly as a new seed changes them there;
  - which lane each sample's files name. gen_fastq fixes one layout per half (positive: S1-S3 on L001, S4-S6 on
    L002; control: S3 and S4 swapped). A second seed that kept those layouts would hand the agent the first study's
    file names byte for byte, so here the seed draws (DRAW_KEY) which lane holds the control group on the positive
    half, and which control sample and which treated sample trade lanes on the control half. The positive half
    stays a perfect alias (rank 2 of 3); the control half stays crossed, three samples per lane (rank 3 of 3).

WHAT STAYS MATCHED, by construction and re-checked by `matching_problems`: the payloads do not depend on the lane
(gen_fastq's own property), so the multiset of payload hashes is identical across the halves; samples.csv and the run
sheet are identical; and the halves differ in exactly MOVED samples' lane tokens, the two that trade lanes.

THE CLAUSES (`problems(seed)`, also `--check`; each its own function, so a test mutates one through the module's own
accessors):

  rank_problems      the design matrix [1 | condition | lane] has rank EXPECTED_RANK[half] of 3 on each half,
                     computed by the identical copy of rank_check.py (its `design_matrix` and `rank`, exact
                     arithmetic over fractions)
  instance_problems  neither half's lane layout is gen_fastq's (the first study's) layout
  matching_problems  same payload multiset, same samples.csv, same run sheet, exactly MOVED samples moved
  seed_problems      the seed is not the first study's (FIRST_STUDY_SEED, gen_fastq's default)

Determinism: the same --half and --seed write byte-identical files on any machine and date (gen_fastq's gzip
convention: mtime 0, no stored name). The manifest names no output path, so no temporary or home folder reaches a
ledger. Standard library only; no model, no network.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    """A first-study builder, loaded by path from its identical copy beside this file; refused from anywhere else."""
    path = HERE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if Path(mod.__file__).resolve().parent != HERE:
        raise ImportError(f"{filename} loaded from {mod.__file__}, not from {HERE}")
    return mod


gf = _load("gap4_seed2_gen_fastq", "gen_fastq.py")
rc = _load("gap4_seed2_rank_check", "rank_check.py")

POSITIVE, CONTROL = "positive", "control"
HALVES = (POSITIVE, CONTROL)
SEED = 20261009
FIRST_STUDY_SEED = 20260905
DRAW_KEY = "gap4|confounded-design|seed-2|lanes|%d"
LANE_PAIR = ("L001", "L002")
EXPECTED_RANK = {POSITIVE: 2, CONTROL: 3}
OF_COLUMNS = 3
MOVED = 2


def design_rows() -> list[dict]:
    """The frozen samples.csv, parsed (gen_fastq.SAMPLES_CSV_BYTES)."""
    return list(csv.DictReader(io.StringIO(gf.SAMPLES_CSV_BYTES.decode("ascii"))))


def groups() -> tuple[list, list]:
    """(control samples, treated samples), in the table's order."""
    rows = design_rows()
    conds = sorted({r["condition"] for r in rows})
    return ([r["sample_id"] for r in rows if r["condition"] == conds[0]],
            [r["sample_id"] for r in rows if r["condition"] == conds[1]])


def draw(seed: int) -> tuple:
    """(lane of the control group, the control sample that moves, the treated sample that moves), from the seed."""
    rng = random.Random(DRAW_KEY % seed)
    ctrl, trt = groups()
    first = rng.choice(LANE_PAIR)
    return first, rng.choice(ctrl), rng.choice(trt)


def lanes(half: str, seed: int) -> dict:
    """sample -> lane. positive: the control group on one lane, the treated group on the other (an alias);
    control: the same, with one control and one treated sample trading lanes (crossed)."""
    if half not in HALVES:
        raise ValueError(f"half is one of {HALVES}")
    first, moved_c, moved_t = draw(seed)
    second = LANE_PAIR[1 - LANE_PAIR.index(first)]
    ctrl, trt = groups()
    out = {s: first for s in ctrl}
    out.update({s: second for s in trt})
    if half == CONTROL:
        out[moved_c], out[moved_t] = second, first
    return {s: out[s] for s in gf.SAMPLES}


def build_half(half: str, seed: int) -> dict:
    """{relative path: bytes} for one half, through gen_fastq's own builders. Nothing is written here."""
    lane = lanes(half, seed)
    files = {}
    for sample in gf.SAMPLES:
        for read in (1, 2):
            name = gf.fastq_filename(sample, lane[sample], read)
            files["src/" + name] = gf.gzip_bytes(gf.read_bytes(seed, sample, read))
    files["src/" + gf.DECOY_NAME] = gf.DECOY_BYTES
    files["samples.csv"] = gf.SAMPLES_CSV_BYTES
    return files


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def payload_multiset(files: dict) -> list:
    return sorted(_sha(b) for p, b in files.items() if p.endswith(".fastq.gz"))


def manifest(half: str, seed: int, files: dict) -> dict:
    """The JSON printed on stdout (drive.py reads `payload_multiset_sha256` and `samples_csv_md5` from it)."""
    return {
        "generator": "evals/gap-study-4/fixtures/gen_confounded_seed2.py",
        "builder": "evals/gap-study-4/fixtures/gen_fastq.py",
        "half": half,
        "seed": seed,
        "lane_assignment": lanes(half, seed),
        "samples_csv_md5": hashlib.md5(files["samples.csv"]).hexdigest(),
        "payload_multiset_sha256": _sha("\n".join(payload_multiset(files)).encode("ascii")),
        "files": [{"path": p, "bytes": len(files[p]), "sha256": _sha(files[p])} for p in sorted(files)],
    }


def design_rank(half: str, seed: int) -> tuple:
    """(rank, columns) of [1 | condition | lane], by rank_check's own design_matrix and exact rank."""
    matrix, _labels, _conds, _lanes = rc.design_matrix(design_rows(), lanes(half, seed))
    return rc.rank(matrix), len(matrix[0])


# ---- the clauses --------------------------------------------------------------------------------------------------

def rank_problems(seed: int) -> list:
    out = []
    for h in HALVES:
        got = design_rank(h, seed)
        if got != (EXPECTED_RANK[h], OF_COLUMNS):
            out.append(f"the {h} half's design has rank {got[0]} of {got[1]}, not {EXPECTED_RANK[h]} of {OF_COLUMNS}")
    return out


def instance_problems(seed: int) -> list:
    return [f"the {h} half's lane layout is the first study's" for h in HALVES if lanes(h, seed) == gf.LANES[h]]


def matching_problems(seed: int) -> list:
    out = []
    a, b = build_half(POSITIVE, seed), build_half(CONTROL, seed)
    if payload_multiset(a) != payload_multiset(b):
        out.append("the halves' payload multisets differ")
    for p in ("samples.csv", "src/" + gf.DECOY_NAME):
        if a.get(p) != b.get(p):
            out.append(f"the halves' {p} differ")
    la, lb = lanes(POSITIVE, seed), lanes(CONTROL, seed)
    moved = sorted(s for s in gf.SAMPLES if la[s] != lb[s])
    if len(moved) != MOVED:
        out.append(f"the halves differ in {len(moved)} samples' lanes ({moved}), not {MOVED}")
    if hashlib.md5(gf.SAMPLES_CSV_BYTES).hexdigest() != gf.SAMPLES_CSV_MD5:
        out.append("samples.csv is no longer the first study's frozen table")
    return out


def seed_problems(seed: int) -> list:
    return ["the seed is the first study's"] if seed == FIRST_STUDY_SEED else []


CLAUSES = (rank_problems, instance_problems, matching_problems, seed_problems)


def problems(seed: int = SEED) -> list:
    out = []
    for clause in CLAUSES:
        out += clause(seed)
    return out


# ---- the command line (the first-study kind's: --half --seed --out) ------------------------------------------------

def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--check"]:
        bad = problems()
        for b in bad:
            print(f"gen_confounded_seed2: {b}")
        if bad:
            return 1
        print(f"gen_confounded_seed2: ok ({len(CLAUSES)} checks)")
        return 0
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--half", required=True, choices=HALVES)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    if hashlib.md5(gf.SAMPLES_CSV_BYTES).hexdigest() != gf.SAMPLES_CSV_MD5:
        print("samples.csv is no longer the first study's frozen table; the halves are not matched", file=sys.stderr)
        return 1
    files = build_half(args.half, args.seed)
    gf.write_files(args.out, files)
    json.dump(manifest(args.half, args.seed, files), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
