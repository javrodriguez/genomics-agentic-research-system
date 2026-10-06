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
A sweep armed with the real values read at harvest (buckets, account ids also in the dddd-dddd-dddd form, approval actors, the user name that ran harvest, the original prefixes) refuses any survivor, any unmasked storage URI, any 12-digit id bounded by non-hex characters unless it lies inside a decimal number's fraction (after the point, before any exponent), and any sha256 of a file that holds a masked value.
An output whose recorded sha256 would be printed while its bytes hold a bucket, account id, approver or user name is refused, since that hash would confirm the value offline; a gzip or BGZF member is searched in its decompressed stream too.
**No `presence` member's sha256 is published**, whatever its bytes hold: `presence` compares no hash, and a byte search cannot see inside every compressed kind, so `outputs.tsv` and the records print `withheld`, the digest joins the sweep's oracle set, and a `presence` member never ships in `outputs/small/`; a `presence` member that holds a user name or approver still refuses.
**A directory output that holds a withheld member withholds its own tree hash**, because that hash is a public function of the member list printed beside it.
**An output member that harvest did not read** (over 5 MB without `--copy-large`) refuses render, so no unread member's sha256 is ever printed.
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
- The last review of the hash-oracle rules (6 October 2026, round 3, no MAJOR) left five gaps, none shown on real inputs: hashes printed but never vetted (`software_versions` digests and the free-text evidence of the tolerances file), a CRLF HISTORY.md, the dashed account form outside the member check, an unarmed 12-digit id inside a hashed member that does not ship, and zip, xz or bz2 members searched raw.
- The re-runs are the repository's own; no independent re-run by another person has happened.

## Test

`gars/tests/test_package_run.py` builds each world with GARS's own record writers and drives harvest, render, verify, compare and rerun.sh (with stand-ins for docker, java, curl and nextflow).
Mutation runs on 5 October 2026: 32 of 32 mutants killed, among them URI masking off, the actor printed, a label dropped or relabelled `recorded at run`, an absent digest guessed, each refusal skipped, a member skipped, presence counted as a match, a presence output dropped from N, a masked file's hash printed, the oracle sweep off, the rerun.sh checksum and machine gates off, and each verify cross-link off.
Mutation runs on 6 October 2026 for the hash-oracle rules, each on a byte backup restored and sha-verified: 21 of 21 mutants killed at `c614a39e` (20 at `70983396`, and the bare-bucket rule's mutant once a stage-03 world pinned it), among them a presence hash printed, a tree hash kept over a withheld member, an unread member's hash printed, a gzip member searched raw, each oracle addition dropped, the decimal exemption widened to an integer part, an exponent or any dotted token, and verify accepting a printed presence hash, a kept tree hash or an edit to the first of two duplicate rows.

## The exemplar

`reproduction/yeast-atac/package/` is one real GARS run: nf-core/atacseq 2.1.2 on the yeast R64-1-1 fixture through GARS's stage 00-02 wrappers at public GARS `0f602ea0`, with no model step (`agent_model: none`), on the launch pad's AWS Batch road (6 October 2026, pad lifetime 5, 187 Batch jobs), harvested on the run's machine before teardown by `package_run.py` at lane commit `a56f0b48`.
It was rendered from that harvest at lane commit `70983396`: package sha256 `ab2b9f45ff8d6df03a78f8f8dd199f9f5554c54a8605344891494bd87f504830`, rendered twice byte-identical.
An earlier render of the same harvest (`15e294bb…`) came from code left uncommitted by an earlier session of the build lane, and is superseded; the two differ only by hashes the reviewed code withholds, with `rerun.sh`, `compare.py`, the inputs, params and environment byte-identical.
The run's two driver faults found on the machine (stage 00 seeds the design at `finalize`; the job submission prints its JSON over several lines) were fixed with a red test each before the run that completed (`9ff50222`, `a56f0b48`).

## Status

Draft on the build branch `lane/repro-package`; finalised with the exemplar at slice S5 and the delegated approval of its protected additions (0282).

## Date

2026-10-05
