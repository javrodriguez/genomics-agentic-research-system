# Reproduce

## Prerequisites

- Docker, with at least 4 CPUs and about 16 GB of memory available to it.
- Java, curl, python3 and the Nextflow launcher (`nextflow`) on PATH; rerun.sh pins the Nextflow version the run recorded (code/pipelines.tsv).
- About 16 GB of free disk: a pass with no container image cached used 15.02 GB, images included.

## Re-run

`bash rerun.sh --out <empty folder>`

It downloads every input and reference file from the URL the package names, and refuses before any pipeline starts if a checksum differs, saying which file and where its checksum came from.

## Verify

`python3 verify.py --against <that folder>`

Each recorded output is compared member by member and lands in one count: M matched exactly, K within the stated tolerance, P present but not byte-comparable, F differ.
The exit code is 0 when every output matched (M + K = N), 2 when any output differs, and 3 when none differs but some are presence-only.

## On a mismatch

Write the member table with `python3 verify.py --against <that folder> --table-out <table folder>` (members.tsv names each member's mode and result) and read it beside the comparison entries in PROVENANCE.md; a member that differs with no entry is a finding about this package, not a failure of your machine.
