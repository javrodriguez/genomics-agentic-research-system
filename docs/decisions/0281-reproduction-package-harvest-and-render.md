---
date: 2026-10-05
status: standing # draft until S5: the design is built and tested; the exemplar and the landing are open
kind: decision
touches:
  - gars/_system/claims/package_run.py
  - gars/_system/claims/package/verify.py
  - gars/_system/claims/package/compare.py
  - gars/_system/claims/package/rerun.sh
  - gars/tests/test_package_run.py
  - gars/tests/fixtures/package/
  - reproduction/yeast-atac/
symptoms:
  - a GARS run has a record but no package a stranger can re-run and check
  - a reproducibility claim nobody can check in minutes is not evidence
---
# A reproduction package per run: harvest on the run's machine, render anywhere, verify offline

The owner approved the reproduction package plan on 5 October 2026 (he typed "A1 B1 C2" in the Row-orchestrator window, and "gars-repro yes" in a terminal session, OrgOS T65).
The design below is the plan's (Brain `plans/gars-reproduction-package.md`), built by the lane under that approval; every other ruling here is the lane's or the Row-orchestrator's, never the owner's.

## Context

A GARS run records its commit, its pipeline commit, its parameters, its software versions and the sha256 of every output (the stage 02 manifest, graded by `manifest_check.py`).
Nothing turned that record into something a reader could re-run: the records sit on the machine that ran, hold absolute paths and a bucket name that carries the cloud account id, and name no input URL.
A short-lived cloud box also loses its records at teardown (the 4 October take), so whatever is checked must be checked before `down`.

## Decision

**Two steps.**
`package_run.py harvest` runs on the run's machine before teardown.
It re-checks every recorded hash with GARS's own checks, read-only: `manifest_check.grade` (complete, with one tested exception, group 4, container digests, absent), `wrapperlib.verify_output_manifest`, the recomputed input key, `params.yaml` read back against the recorded params, the pipeline checkout at the recorded commit with no tracked change, a clean GARS clone, `data_class` public, and for a stage 03 analysis `render_methods.check_approval` and the script and launcher sha256 bound at submit (no scheduler poll).
It copies the records, the stage trees and output members up to 5 MB (all of them with `--copy-large`), and hashes every input the samplesheet names, into a private folder that is never published.
`package_run.py render` is pure: it reads only the harvest, named files at the recorded GARS commit by `git show`, and two lane files (the commit-pinned sources and the comparison entries); it adds no timestamp and renders byte-identically.

**Three labels.**
Every table value carries `recorded at run` (a named record field; only these attest the run), `computed at harvest`, or `supplied at packaging from <repository>@<commit>:<path>`.
A field the run did not record reads "not recorded", with a PROVENANCE line naming it; nothing is filled from today's environment.

**What never ships.**
One mask map per package replaces the run's absolute path prefixes (both spellings), storage URIs (`s3://<BUCKET>/<key>`) and account ids, and lists only placeholders and counts.
A sweep armed with the real values read at harvest (buckets, account ids, approval actors, the user name that ran harvest, the original prefixes) refuses any survivor, any unmasked storage URI, any 12-digit id bounded by non-hex characters, and any sha256 of a file that holds a masked value.
An output whose recorded sha256 would be printed while its bytes hold a bucket, account id, approver or user name is refused, since that hash would confirm the value offline.
The records ship as allowlisted fields; the hashes of files holding masked values are cited by field name, with the true reason.
The approval record's actor and plan path are read for binding and never printed.
gitleaks runs with `gars/.gitleaks.toml` over the folder before it is written.

**Verify and compare.**
The package's own `verify.py` (standard library, offline) checks every file against `SHA256SUMS`, the cross-links between its tables, records and METHODS.md, and the landing README's digest when one sits beside the package.
Its `compare.py` compares a re-run member by member under the package's declared modes and rollup (decision 0283), not GARS's `rerun_check.py`, which stays untouched.
`rerun.sh` pins each pipeline by commit and each process by the image tag the trace recorded, refuses a machine under 4 CPUs or about 16 GB and any checksum mismatch before a pipeline starts, and does not automate a stage 03 re-run in this version.

**METHODS.md** is the Methods renderer's own output for the same records (decision 0236, with the journal paragraph of decision 0276), called, never re-implemented.

## What this does not close

- Container digests are not recorded at run (G1); images are pinned by tag (the owner's choice C2), and recording digests at run belongs with the MS21 follow-ups.
- A stage 03 analysis records no output sha256 or environment (G2), and its re-run is not automated.
- A member over 5 MB not harvested with `--copy-large` is not read for masked values; PROVENANCE names each one.
- The re-runs are the repository's own; no independent re-run by another person has happened.

## Test

`gars/tests/test_package_run.py` builds each world with GARS's own record writers and drives harvest, render, verify, compare and rerun.sh (with stand-ins for docker, java, curl and nextflow).
Mutation runs on 5 October 2026: 32 of 32 mutants killed, among them URI masking off, the actor printed, a label dropped or relabelled `recorded at run`, an absent digest guessed, each refusal skipped, a member skipped, presence counted as a match, a presence output dropped from N, a masked file's hash printed, the oracle sweep off, the rerun.sh checksum and machine gates off, and each verify cross-link off.

## Status

Draft on the build branch `lane/repro-package`; finalised with the exemplar at slice S5 and the delegated approval of its protected additions.

## Date

2026-10-05
