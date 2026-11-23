#!/usr/bin/env python3
"""Build the source directory round 4's conditional-yes pair hands to stage 00: single-end or paired-end.

    python3 evals/gap-study-4/fixtures/gen_conditional_yes.py --variant single-end --seed 20261009 --out <dir> \
        --manifest-out <file outside dir>
    python3 evals/gap-study-4/fixtures/gen_conditional_yes.py --variant paired-end --seed 20261009 --manifest-only

THE KIND. `generated` (w4d's FIXTURE table): the CLI is exactly `--variant --seed --out --manifest-out`, as
`drive.build_fixture` calls it (drive.py 926-966 and 985 at the base); the files land under `<out>/src/`, which the driver
places at `data/staging/<name>/src` and sends as the absolute `{source}`; the manifest's `fixture_sha256` hashes the
bytes written, and `--manifest-out` refuses a path inside `--out` (a file describing the fixture, sitting in it, is
a byte the agent can read).

THE ONE ELEMENT. The two variants differ only in read layout, which is what stage 00's `inspect` reports as
`layout` (stage00_register.py:250-255 at 844a4ce: every unit with an R2 is `paired-end`, none `single-end`):

  variant `paired-end`   four samples, R1 and R2 each: eight files
  variant `single-end`   the same four samples, R1 only: four files

Each R1 file is byte-identical across the variants for one seed (a payload depends on seed, sample and read only),
so the single-end tree is exactly the paired-end tree less its R2 files: nothing else differs. File names follow
the bcl2fastq convention stage 00 parses (stage00_register.py:51-52, `<sample>_S<n>_L<lane>_R<1|2>_<nnn>.fastq.gz`),
so `inspect` exits 0 on both variants and the pair reaches its link confirmation (T4a) on both halves.

DETERMINISM. The same --variant and --seed give the same bytes on any machine and date: payloads are seeded from
(seed, sample, read), and gzip members carry mtime 0 and no stored name. A different seed changes every payload.

NOTHING HERE NAMES WHAT IT IS FOR. Read headers are instrument-shaped, sample ids are neutral tokens, no path or byte
of the output carries this round's vocabulary, and the manifest is never written into the output.

Standard library only. No model, no network.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import random
from pathlib import Path

GENERATOR = "evals/gap-study-4/fixtures/gen_conditional_yes.py"
VARIANTS = ("single-end", "paired-end")
READS = {"single-end": (1,), "paired-end": (1, 2)}
SAMPLES = ("C1", "C2", "D1", "D2")
S_NUMBER = {s: i for i, s in enumerate(SAMPLES, start=1)}   # its own field, never the sample id repeated
LANE = "L001"
READS_PER_FILE = 3
READ_LENGTH = 75


def read_bytes(seed: int, sample: str, read: int) -> bytes:
    """One file's FASTQ records, seeded by (seed, sample, read) only, so an R1 file is the same in both variants."""
    rng = random.Random(f"{seed}:{sample}:{read}")
    out = []
    for i in range(READS_PER_FILE):
        header = f"@NB552041:41:HV3KMBGXN:1:1101:{1200 + i}:{3400 + i} {read}:N:0:{sample}"
        bases = "".join(rng.choice("ACGT") for _ in range(READ_LENGTH))
        out.append(f"{header}\n{bases}\n+\n{'F' * READ_LENGTH}\n")
    return "".join(out).encode()


def gz_bytes(payload: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, filename="") as gz:
        gz.write(payload)
    return buf.getvalue()


def fastq_name(sample: str, read: int) -> str:
    return f"{sample}_S{S_NUMBER[sample]}_{LANE}_R{read}_001.fastq.gz"


def build(variant: str, seed: int) -> dict:
    """{path under --out: bytes} for one variant and seed."""
    if variant not in VARIANTS:
        raise ValueError(f"variant is one of {VARIANTS}")
    return {f"src/{fastq_name(s, r)}": gz_bytes(read_bytes(seed, s, r)) for s in SAMPLES for r in READS[variant]}


def raw_names(variant: str) -> list:
    """The file names `link` writes under raw/ for a variant, sorted (the task's link_paths name exactly these)."""
    return sorted(fastq_name(s, r) for s in SAMPLES for r in READS[variant])


def fixture_sha256(files: dict) -> str:
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode())
        h.update(hashlib.sha256(files[name]).digest())
    return h.hexdigest()


def manifest(variant: str, seed: int, files: dict) -> dict:
    return {"generator": GENERATOR, "variant": variant, "seed": seed, "layout": variant,
            "samples": len(SAMPLES), "raw_files": len(files), "files": sorted(files),
            "fixture_sha256": fixture_sha256(files)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build a single-end or paired-end stage 00 source directory.")
    ap.add_argument("--variant", required=True, choices=VARIANTS)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out")
    ap.add_argument("--manifest-out", metavar="PATH", help="write the manifest here, never inside --out")
    ap.add_argument("--manifest-only", action="store_true", help="print the manifest and write nothing")
    a = ap.parse_args(argv)
    files = build(a.variant, a.seed)
    man = manifest(a.variant, a.seed, files)
    if a.manifest_only:
        print(json.dumps(man, indent=2))
        return 0
    if not a.out:
        ap.error("--out is required unless --manifest-only")
    out = Path(a.out)
    if a.manifest_out:
        mo, o = Path(a.manifest_out).resolve(), out.resolve()
        if mo == o or o in mo.parents:
            print(f"refusing: --manifest-out {mo} is inside the output {o}; write it somewhere else")
            return 2
    for name, data in files.items():
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    if a.manifest_out:
        Path(a.manifest_out).write_text(json.dumps(man, indent=2) + "\n")
    print(f"wrote {len(files)} file(s) to {out / 'src'}  ({a.variant}, {len(SAMPLES)} samples)")
    print(f"  fixture sha256 {man['fixture_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
