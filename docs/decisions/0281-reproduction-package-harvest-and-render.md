---
date: 2026-10-05
status: standing # draft until the landing: the exemplar and its passes 1, 2 and 3 are in
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

The owner approved the reproduction package plan on 5 October 2026 in his own typed words: "A1 B1 C2", taking the plan's three recommended options, and "gars-repro yes".
The design below is the plan's (the plan is the owner's private working document and is not published), built under that approval; every other ruling here is the builders' or the coordinating session's, made under his delegation, never the owner's own words.

## Context

A GARS run records its commit, its pipeline commit, its parameters, its software versions and the sha256 of every output (the stage 02 manifest, graded by `manifest_check.py`).
Nothing turned that record into something a reader could re-run: the records sit on the machine that ran, hold absolute paths and a bucket name that carries the cloud account id, and name no input URL.
A short-lived cloud box also loses its records at teardown (the 4 October take), so whatever is checked must be checked before `down`.

## Decision

**Two steps.**
`package_run.py harvest` runs on the run's machine before teardown.
It re-checks every recorded hash with GARS's own checks, read-only: `manifest_check.grade` (complete, with one tested exception, group 4, container digests, absent), `wrapperlib.verify_output_manifest`, the recomputed input key, `params.yaml` read back against the recorded params, the pipeline checkout at the recorded commit with no tracked change, a clean GARS clone, `data_class` public, and for a stage 03 analysis `render_methods.check_approval` and the script and launcher sha256 bound at submit (no scheduler poll).
It copies the records, the stage trees and output members up to 5 MB (all of them with `--copy-large`), and hashes every input the samplesheet names, into a private folder that is never published.
`package_run.py render` is pure: it reads only the harvest, named files at the recorded GARS commit by `git show`, the exemplar's own files beside the package (the commit-pinned sources, the comparison entries and, when given, the errata), and its own checkout's Methods renderer and package templates, which `code/GARS.txt` binds by the render commit; it adds no timestamp and renders byte-identically.

**Labels.**
Every table value's source cell starts with one of six labels, enforced when a table is written: `recorded at run` (a named record field; only these attest the run), `computed at harvest`, `supplied at packaging from <source>` (a named file at a pinned commit, or one of the exemplar's own files, shipped in the package), `computed at packaging from <source>` (a normalised form, or a recorded value whose path the package replaced), `not recorded by the run`, or `withheld`.
A field the run did not record reads "not recorded", with a PROVENANCE line naming it; nothing is filled from today's environment.
The enforcement checks the label's opening words only; some cells use a label more loosely than PROVENANCE defines it (the default comparison mode, the render commit and the clone status), a gap named below.

**What never ships.**
One mask map per package replaces the run's absolute path prefixes (both spellings), storage URIs (`s3://<BUCKET>/<key>`) and account ids, and lists only placeholders and counts.
A sweep armed with the real values read at harvest (buckets, account ids also in the dddd-dddd-dddd form, approval actors, the user names the run's own records carry in home paths (stock cloud logins excepted), the original prefixes) refuses any survivor, any unmasked storage URI, any 12-digit id bounded by non-hex characters unless it lies inside a decimal number's fraction (after the point, before any exponent), and any sha256 of a run record that holds a masked value.
An output whose recorded sha256 would be printed while its bytes hold a bucket, account id, approver or user name is refused, since that hash would confirm the value offline; a gzip or BGZF member is searched in its decompressed stream too.
An output that holds only a path is not refused: a result table holding a path is left out of `outputs/small/`, but its recorded sha256 is still printed.
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

- Container digests are not recorded at run (G1); images are pinned by tag (the owner's choice C2), and recording digests at run is left to a later change.
- A stage 03 analysis records no output sha256 or environment (G2), and its re-run is not automated.
- The exemplar review's second round left gaps (6 October 2026, none loosening a check): REPRODUCE's measured disk figure is written into every package, not only this one; some cells use a label more loosely than PROVENANCE defines it; a printed hash is not checked for a path (measured on this exemplar: none of its 154 printed hashes covers a file holding one). Each changes the package's bytes, so each waits for the next package.
- The last review of the hash-oracle rules (6 October 2026, round 3, no MAJOR) left five gaps, none shown on real inputs: hashes printed but never vetted (`software_versions` digests and the free-text evidence of the tolerances file), a CRLF HISTORY.md, the dashed account form outside the member check, an unarmed 12-digit id inside a hashed member that does not ship, and zip, xz or bz2 members searched raw.
- The re-runs are the repository's own; no independent re-run by another person has happened.

## Test

`gars/tests/test_package_run.py` builds each world with GARS's own record writers and drives harvest, render, verify, compare and rerun.sh (with stand-ins for docker, java, curl and nextflow).
Mutation runs on 5 October 2026, every mutant killed, 84 on `package_run.py` and the package scripts by the end of the day (32 once verify, rerun and compare were built, 66 after the harvest reviews, 84 with the early probe's comparison entries), among them URI masking off, the actor printed, a label dropped or relabelled `recorded at run`, an absent digest guessed, each refusal skipped, a member skipped, presence counted as a match, a presence output dropped from N, a masked file's hash printed, the oracle sweep off, the rerun.sh checksum and machine gates off, and each verify cross-link off.
Mutation runs on 6 October 2026 for the hash-oracle rules, each on a byte backup restored and sha-verified: 21 of 21 mutants killed at `c614a39e` (20 at `70983396`, and the bare-bucket rule's mutant once a stage-03 world pinned it), among them a presence hash printed, a tree hash kept over a withheld member, an unread member's hash printed, a gzip member searched raw, each oracle addition dropped, the decimal exemption widened to an integer part, an exponent or any dotted token, and verify accepting a printed presence hash, a kept tree hash or an edit to the first of two duplicate rows.

## The exemplar

`reproduction/yeast-atac/package/` is one real GARS run: nf-core/atacseq 2.1.2 on the yeast R64-1-1 fixture through GARS's stage 00-02 wrappers at public GARS `0f602ea0`, with no model step (`agent_model: none`), its pipeline steps run on AWS Batch from the launch pad, a short-lived cloud workstation (6 October 2026, 187 Batch jobs), harvested on the run's machine before teardown by `package_run.py` at build-branch commit `a56f0b48`.
It was rendered from that harvest at build-branch commit `f1dc0931`, which `code/GARS.txt` names as the render commit, with the exemplar's errata file `reproduction/yeast-atac/package-errata.json`: package sha256 `f5964ecee48730b533458db313667b597a7c0e09df27020e8ba6da07cae85811`, rendered twice byte-identical.
Four earlier renders of the same harvest are superseded, and every render carries the same re-run commands (`rerun.sh`, `env/rerun.config`, the inputs, references and params are byte-identical across all five): `15e294bb…`, from code an earlier session of the builders left uncommitted, and `ab2b9f45…`, from the reviewed hash-oracle rules at `70983396`, which differs from `15e294bb` only by withheld hashes; `65737e4a…` differs from `ab2b9f45` only in labels, documentation and the offline `verify.py` and `compare.py` (the exemplar review's round 1), `6993f8a7…` from `65737e4a` only in the offline `verify.py` and `compare.py` and the named render commit (round 2's two check-loosening MINORs), and `f5964ece` from `6993f8a7` only by the errata file, its "Corrections" section in PROVENANCE.md, the offline `verify.py` that cross-checks it, and the render commit; `outputs/outputs.tsv` and `compare.py` are byte-identical.
**Errata.** A cause stated in the frozen tolerances file is corrected, never edited, through a separate file beside the package that `render --errata` ships as `outputs/package-errata.json` and prints under "Corrections": each correction names only members a finding or entry names, and changes no mode, member or count; `verify.py` checks that cross-link offline.
The run's two driver faults found on the machine (stage 00 seeds the design at `finalize`; the job submission prints its JSON over several lines) were fixed with a red test each before the run that completed (`9ff50222`, `a56f0b48`).

## Status

Draft on the build branch `lane/repro-package`; the exemplar and its re-runs are in; finalised at the landing, with the delegated approval of its protected additions (0282).

## Date

2026-10-05
