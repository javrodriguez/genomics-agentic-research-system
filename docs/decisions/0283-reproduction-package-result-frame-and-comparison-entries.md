---
date: 2026-10-05
status: standing # draft until S5: the frame and the rules below are frozen at S0; the entries wait for S2b and pass 1
kind: decision
touches:
  - gars/_system/claims/package_run.py
  - reproduction/yeast-atac/package/compare.py
  - reproduction/yeast-atac/package/outputs/package-tolerances.json
  - reproduction/yeast-atac/README.md
symptoms:
  - two AWS Batch runs of the yeast ATAC fixture matched byte for byte on 2 of 6 outputs (rung 3, 2 Oct 2026), unattributed
  - a package that promised byte-identical outputs would fail on its first honest re-run
---
# The reproduction package's result frame and comparison entries, frozen before any result exists

The owner approved the reproduction package plan on 5 October 2026 (he typed "A1 B1 C2" in the Row-orchestrator window, and "gars-repro yes" in a terminal session, OrgOS T65).
The frame and the rules below are the plan's own (Brain `plans/gars-reproduction-package.md`, section 8), frozen here at slice S0 by the build lane under that approval.
No other sentence in this record is the owner's.

## Context

The package's verify step compares a fresh re-run against the recorded outputs and prints one result line.
GARS's own measurement says byte-identical outputs are not the expected case: in rung 3 (2 Oct 2026) two AWS Batch runs of the same ATAC fixture matched byte for byte on only 2 of 6 outputs, with narrowPeak, consensus featureCounts, the merged BAM and MultiQC differing (`gars-demo-v2/docs/launchpad-evidence/rung3-results/cross-model-check.json`, private).
So the line's frame, its counting rule and the rule for moving an output away from exact comparison are fixed here, before any re-run of the exemplar exists, so a partial match is published as measured.

## Decision

**The result frame (both units, frozen):**

> of N outputs (n files), M matched exactly, K within the stated tolerance, P present but not byte-comparable, F differ (causes in PROVENANCE.md)

N counts the run's recorded outputs; n counts their members (files).
Nested directory outputs are compared member by member against the manifest's `members` and each member is counted once, by member path.

**The rollup, so every output lands in exactly one count (M + K + P + F = N):**

- M: every member is in mode `exact` and matches.
- K: every member matches under a mode other than `presence`, and at least one member is not `exact`.
- P: at least one member is in mode `presence`, and no member fails.
- F: at least one member fails.

`presence` (the file exists and is non-empty) is never counted as a match.

**The modes.**
`exact` (sha256) is the default for every member, and `presence` exists from the first build.
A further mode is added only when a probe reads a cause for it from the bytes: `bam_body` (md5 of the alignment records with the header removed, sorted by coordinate and name), `sorted_table` (rows sorted, comment lines carrying dates or paths removed, then exact), `numeric` (named columns within an absolute and a relative threshold, whose bounds are frozen in this record at S2b).
These are the package's own modes, declared in its `compare.py`; they are not 0097's, and `scripts/rerun_check.py` and `_references/tolerances.yaml` are not touched.

**The entry rule.**
A member moves from `exact` to another mode only with a cause read from its bytes and a second run showing the same class of difference.
Each entry in `outputs/package-tolerances.json` carries the cause, the evidence and an `origin`: `S2b-preregistered` (the early probe, re-run against re-run on one machine type) or `pass-1` (the first re-run of the exemplar against its Batch record); PROVENANCE.md and the landing README count the two origins apart.
A member with no entry by pass 1 stays `exact`.
A difference in peak calls or counts beyond a small numeric threshold is a finding, never an entry.

**When the claim passes disagree.**
"Agree" means passes 2 and 3 produce identical member tables, member by member, in mode and in match.
A member on which they disagree counts in F with the cause "unstable between re-runs on the same machine type"; both tables go into the landing README, and that is the shipped line.
A pass that fails to finish for infrastructure reasons is re-run once; if no claim pass finishes by Tue 13 Oct 2026, the landing README reads "not yet re-run" and the owner decides at result approval whether to land now or after the freeze.

**Go/no-go, Tue 13 Oct 2026.**
The measured result is what ships, whatever F is; the owner sees the actual line at result approval and decides whether it goes public.

**What "reproduced" means here.**
Only the result line's counts, for one fixture run, never "GARS is reproducible"; no public frame maps it to an ACM badge, and no public frame calls the re-run independent.

**Verify's exit codes.**
`verify.py --against <rerun dir>` exits 0 only when M + K = N, 2 when F > 0, and 3 when F = 0 and P > 0.

## Entries

Pending S2b (the early probe, two plain nf-core/atacseq 2.1.2 runs of the yeast fixture under the recorded clamp) and pass 1.
Each entry is appended here with its member path, mode, cause, evidence and origin, and the numeric bounds if any.

## What this does not close

- The entries themselves, and any numeric bound, until S2b and pass 1 have run.
- Independence: every pass is run by the repository's own machinery, never by another person.

## Test

`gars/tests/test_package_run.py` (slice S1) holds the rollup and the exit codes: a `presence` member counted in M or K, a `presence` output dropped from N, or a skipped member must each make a test fail (mutation-checked).

## Status

Draft, on the build branch `lane/repro-package`; the frame and rules are frozen, the entries are open, and the record is finalised with the exemplar at slice S5.

## Date

2026-10-05
