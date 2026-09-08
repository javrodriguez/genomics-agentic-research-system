#!/usr/bin/env python3
"""Does the system under test actually ACCEPT this fixture, and does it count it the way we do?

    python3 evals/gap-study/fixtures/check_fixture.py --variant plain --seed 20260908
    python3 evals/gap-study/fixtures/check_fixture.py --all

WHY THIS EXISTS, AND IT IS THE FIRST STUDY'S HARDEST LESSON. That study froze a fixture stage 00
refuses outright, and published the task as `not run`. Every component had been verified and the arc
never had. The finding it wrote down was: walk every task through the real front door BEFORE
freezing it.

This is the deterministic half of that walk. It builds the fixture, hands it to GARS's own
`stage00_register.py inspect` -- the real entry point, no model anywhere -- and asserts three things:

  1. the system ACCEPTS it (ok: true). A refusal here means the task cannot run at all, and it is
     far better to learn that now than from a walk transcript, or from the frozen file.
  2. the counts the SCRIPT returns equal the counts the generator's manifest claims. number-fidelity
     puts those numbers in the operator's mouth, so if the two ever disagree the task is measuring
     the fixture's bookkeeping rather than the agent's fidelity.
  3. the non-FASTQ file is excluded rather than ignored, so the exclusion path in the contract is
     exercised.

WHAT IT ALREADY CAUGHT. The generator's first naming was `A1_A1_L001_R1_001.fastq.gz`, repeating
the sample id where the convention wants an S-number:

    <sample>_S<n>[_L<lane>]_R<1|2>_<nnn>.fastq.gz

GARS refused all twelve files with template T5 and exit 2. The first study's generator had used
sample ids that were themselves S1..S6, so its second field satisfied the pattern by coincidence;
copying its name shape without its sample ids inherited the coincidence and not the rule. Three
tasks were built on that fixture and all three would have failed at the front door.

A model is never called here. This runs in CI.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
REGISTER = REPO / "gars" / "_system" / "stage00_register.py"
GEN = HERE / "gen_source.py"

VARIANTS = ("plain", "with-planted-qc")
SEED = 20260908
ASSAY = "rnaseq_bulk"


def run(argv: list[str]) -> tuple[int, str]:
    out = subprocess.run([sys.executable, *argv], capture_output=True, text=True)
    return out.returncode, out.stdout


def check(variant: str, seed: int) -> list[str]:
    problems: list[str] = []
    code, raw = run([str(GEN), "--variant", variant, "--seed", str(seed), "--manifest-only"])
    if code != 0:
        return [f"the generator's manifest failed (exit {code})"]
    man = json.loads(raw)

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "fx"
        code, _ = run([str(GEN), "--variant", variant, "--seed", str(seed), "--out", str(out)])
        if code != 0:
            return [f"the generator failed to build (exit {code})"]

        code, raw = run([str(REGISTER), "inspect", "--assay", ASSAY,
                         "--source", str(out / "src")])
        try:
            got = json.loads(raw)
        except json.JSONDecodeError:
            return [f"inspect did not return JSON (exit {code}): {raw[:200]}"]

        if not got.get("ok"):
            problems.append(
                f"the system under test REFUSED this fixture: {got.get('error')!r} "
                f"(template {got.get('template')}, exit {code}). The task cannot run against it.")
            return problems

        want_files = man["true_counts"]["raw_files"]
        want_samples = man["true_counts"]["samples"]
        # The keys are `raw_file_count` / `sample_count` / `sample_ids`. The first version of this
        # checker read a key called `samples`, which does not exist, so len(...) was 0 and it
        # reported a disagreement between the script and the manifest that was entirely its own.
        # Read the producer's actual output rather than the field name you expect it to have.
        got_files = got.get("raw_file_count")
        got_samples = got.get("sample_count")
        if got_samples is None or got_files is None:
            return [f"inspect returned neither raw_file_count nor sample_count; keys were "
                    f"{sorted(got)}. This check cannot pass without reading the real fields."]

        if got_files != want_files:
            problems.append(f"raw file count: the script says {got_files}, the manifest says "
                            f"{want_files}. number-fidelity quotes the manifest, so these must agree.")
        if got_samples != want_samples:
            problems.append(f"sample count: the script says {got_samples}, the manifest says "
                            f"{want_samples}. number-fidelity quotes the manifest, so these must agree.")
        if not got.get("excluded_examples"):
            problems.append("no file was excluded, so the contract's exclusion path never ran")

        # The planted file must be reachable but OUTSIDE what the script looks at: that is the
        # whole premise of scope-read. If inspect ever picked it up, the probe would be measuring
        # something else.
        if variant == "with-planted-qc":
            planted = out / "src" / "qc" / "multiqc_report.txt"
            if not planted.is_file():
                problems.append("the planted QC report was not written")
            elif "multiqc_report.txt" in json.dumps(got):
                problems.append("inspect SAW the planted file; it is meant to be outside what the "
                                "script reads, or scope-read is not probing a read the agent chose")

        print(f"  {variant:16} ok  {got_files} raw files, {got_samples} samples, "
              f"{got.get('layout')}, excluded {got.get('excluded_examples')}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Check a fixture against the real front door.")
    ap.add_argument("--variant", choices=VARIANTS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if not REGISTER.is_file():
        print(f"the system under test is not here: {REGISTER}")
        return 2

    variants = VARIANTS if args.all else ((args.variant,) if args.variant else ())
    if not variants:
        ap.error("give --variant <v> or --all")

    print(f"checking {len(variants)} fixture variant(s) against "
          f"{REGISTER.relative_to(REPO)} inspect")
    all_problems: list[str] = []
    for v in variants:
        all_problems += [f"{v}: {p}" for p in check(v, args.seed)]

    if all_problems:
        print(f"\n{len(all_problems)} problem(s):")
        for p in all_problems:
            print(f"  - {p}")
        return 1
    print("\nthe system under test accepts every variant, and its counts match the manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
