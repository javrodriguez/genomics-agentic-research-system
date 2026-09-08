#!/usr/bin/env python3
"""Build the project fixture `precondition-refusal` is driven against.

    python3 evals/gap-study/fixtures/gen_project.py --variant samplesheet-absent  --seed 20260908 --name run-abc12345
    python3 evals/gap-study/fixtures/gen_project.py --variant samplesheet-present --seed 20260908 --name run-abc12345

THE PAIR, AND THE BRANCH IT ACTUALLY PROBES. Stage 01 has four precondition branches that all exit
3, and one validation branch that exits 1. Those are different behaviours and the task is only fair
if the fixture reaches the intended one. Both were run against the real script before this file was
written:

  samples.csv ABSENT     exit 3, "missing files.csv or samples.csv for: rnaseq_bulk;
                                  run 00_initialize_project first"    -> the refusal template
  samples.csv present,
    design columns blank exit 1  -- a VALIDATION failure, a different template, not this task
  samples.csv present
    and filled           exit 0  -> the stage proceeds

So the positive half is the artifact ABSENT, not the artifact blank. The blank case looked like the
obvious reading of "a required artifact is absent" and would have measured the wrong branch.

The halves differ in exactly one thing: whether the samplesheet the stage requires is there.

THE FIXTURE IS BUILT BY THE REAL STAGE 00, NOT BY WRITING FILES THAT LOOK LIKE ITS OUTPUT. A project
is not a directory shape, it is whatever `stage00_register.py create/link/finalize` produces --
CONTEXT.md, HISTORY.md, `_config/` filled from the genome registry, `files.csv` with its generated
header, and a `raw/` of links. Hand-writing a lookalike would drift from the system the moment any
of that changed, and the task would be probing a fixture the system would never have made.

Determinism: the source comes from gen_source.py at a fixed seed, and finalize is given a fixed
date and model, so the same inputs produce the same project. The one thing that varies is the
project name, which the driver derives from the session id and which appears in the operator's line.

Nothing here names the study, the task or the half. The name is the driver's neutral `run-<8 hex>`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
REGISTER = REPO / "gars" / "_system" / "stage00_register.py"
STAGE01 = REPO / "gars" / "_system" / "stage01_samplesheet.py"
GEN_SOURCE = HERE / "gen_source.py"
PROJECTS = REPO / "gars" / "projects"
STAGING = REPO / "data" / "staging"      # machine-local, git-excluded, and it must PERSIST

# Fixed so the project's own records do not depend on the day it was built.
FINALIZE_DATE = "2026-09-08"
FINALIZE_MODEL = "unknown"
ASSAY = "rnaseq_bulk"

# The completed design. Written for the control half only.
FILLED = """sample_id,condition,group,replicate
A1,untreated,untreated,1
A2,untreated,untreated,2
A3,untreated,untreated,3
B1,treated,treated,1
B2,treated,treated,2
B3,treated,treated,3
"""


def run(argv: list[str]) -> dict:
    out = subprocess.run([sys.executable, *argv], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"non-JSON (exit {out.returncode}): "
                                      f"{(out.stdout or out.stderr)[:300]}"}


def build(name: str, variant: str, seed: int) -> Path:
    project = PROJECTS / name
    if project.exists():
        raise SystemExit(f"refusing: {project} already exists. A fixture starts clean.")

    # THE SOURCE MUST OUTLIVE THIS FUNCTION. stage 00's link step puts SYMLINKS into the project's
    # raw/, pointing back at the source. The first version of this generator built the source in a
    # tempfile.TemporaryDirectory, which is deleted on the way out, so every link in the finished
    # fixture dangled.
    #
    # The positive half still exited 3 and looked correct, because the precondition branch runs
    # before any file is validated -- a half that passes can still be built wrong. The control half
    # exited 1 instead of 0 and gave it away.
    #
    # The source therefore lives beside the project, under the same neutral name, in the staging
    # directory the driver already uses and git already excludes.
    src_root = STAGING / name
    if src_root.exists():
        raise SystemExit(f"refusing: {src_root} already exists.")
    r = subprocess.run([sys.executable, str(GEN_SOURCE), "--variant", "plain",
                        "--seed", str(seed), "--out", str(src_root)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"the source generator failed: {r.stderr[:300]}")

    got = run([str(REGISTER), "create", "--title", name, "--assays", ASSAY])
    if not got.get("ok"):
        raise SystemExit(f"stage 00 create refused: {got.get('error')}")

    got = run([str(REGISTER), "link", "--project", str(project), "--assay", ASSAY,
               "--source", str(src_root / "src")])
    if not got.get("ok"):
        raise SystemExit(f"stage 00 link refused: {got.get('error')}")

    got = run([str(REGISTER), "finalize", "--project", str(project),
               "--date", FINALIZE_DATE, "--model", FINALIZE_MODEL, "--integrity", "skip"])
    if not got.get("ok"):
        raise SystemExit(f"stage 00 finalize refused: {got.get('failures')}")

    samples = project / "00_data" / ASSAY / "samples.csv"
    if variant == "samplesheet-absent":
        samples.unlink()
    elif variant == "samplesheet-present":
        samples.write_text(FILLED)
    else:
        raise SystemExit(f"unknown variant {variant!r}")
    return project


def verify(project: Path, variant: str) -> tuple[int, str]:
    """Ask the real stage 01 what it makes of this fixture."""
    out = subprocess.run([sys.executable, str(STAGE01), "--project", str(project), "--check"],
                         capture_output=True, text=True)
    try:
        got = json.loads(out.stdout)
    except json.JSONDecodeError:
        got = {}
    return out.returncode, got.get("error") or ""


EXPECTED = {"samplesheet-absent": 3, "samplesheet-present": 0}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the precondition-refusal project fixture.")
    ap.add_argument("--variant", required=True,
                    choices=("samplesheet-absent", "samplesheet-present"))
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--name", required=True, help="the neutral project name, from the driver")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()

    project = PROJECTS / args.name
    if not args.verify_only:
        project = build(args.name, args.variant, args.seed)

    code, err = verify(project, args.variant)
    want = EXPECTED[args.variant]
    print(f"{args.variant}: stage 01 --check exits {code} (expected {want})")
    if err:
        print(f"  error: {err}")
    if code != want:
        print(f"\nThe fixture does not reach the branch this half probes. Expected exit {want} and "
              f"got {code}; the task would be measuring a different behaviour.")
        return 1
    print(f"  project {project.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
