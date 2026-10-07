---
date: 2026-10-05
status: standing # draft until the landing: the frame, rules and entries are frozen; passes 1, 2 and 3 are in
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

The owner approved the reproduction package plan on 5 October 2026 in his own typed words: "A1 B1 C2", taking the plan's three recommended options, and "gars-repro yes".
The frame and the rules below are the plan's own (its section 8; the plan is the owner's private working document and is not published), frozen here before any result existed, under that approval.
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
A further mode is added only when a probe reads a cause for it from the bytes: `bam_body` (md5 of the alignment records with the header removed, sorted by coordinate and name), `sorted_table` (rows sorted, comment lines carrying dates or paths removed, then exact), `numeric` (named columns within an absolute and a relative threshold, whose bounds are frozen in this record from the early probe).
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

Frozen 5 October 2026 from the early probe (the origin `S2b-preregistered` names it), before the exemplar ran, under the coordinating session's rulings of the same day (made under the owner's delegation, not his own words).
The early probe ran plain nf-core/atacseq 2.1.2 (commit `1a1dbe52ffbd82256c941a032b0e22abbd925b8a`) twice on one fresh m5.xlarge cloud machine, local executor in Docker, with the recorded clamp: 651 files compared, 342 equal, 309 different.
Every BAM, BAM index, bigWig and narrowPeak file, and the SAF and consensus BED files, were byte-identical across the two runs.
The sha256 values of this record's evidence files (the probe's results tarball here; the passes' artifacts and the re-judgment below) are hashes of the owner's held evidence, published now so the files can be checked when they are released.
The evidence is the probe's results tarball, sha256 `919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0`.

**Two modes added beyond the three named above, both ruled on 5 October 2026:**
`column_matched_table` (a featureCounts table, compared exactly after its columns are matched by sample name) and `sign_aligned_numeric` (a PCA table, compared per sample after each component's sign is aligned, every value within an absolute 1e-9).
The bound 1e-9 is frozen here; the measured difference was about 1e-15.
`bam_body` and `numeric` were not needed: no BAM and no numeric table other than the PCA differed.
Each mode applies only to the file kinds its definition names (`compare.py`'s `kind_allows`), and a member of any other kind fails rather than matches.

**The entries file** is `reproduction/yeast-atac/package-tolerances.json`, sha256 `9f5dddb143e953cb008a2a60f713c281816b42f60bf370508432349913ce536c` at this freeze: 10 entries naming 96 recorded members, every one origin `S2b-preregistered`, each with its cause read from the bytes:
- `presence`: the PDFs, whose only difference is their embedded creation time; the DESeq2 plots PDF, which draws the PCA with its arbitrary component sign; the gzip files (some named `.tab`), whose header carries the write time and whose decompressed rows come in completion order; the serialized R objects, built from the counts with sample columns in completion order; the MultiQC report, which embeds its generation time and the launch folder.
- `sorted_table`: rows in completion order (no line dropped); Picard metrics, dropping exactly the lines matching `^# Started on: `; ataqv JSON, dropping exactly the lines matching `^\s*"timestamp": "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",?$`.
- `column_matched_table`: the consensus featureCounts table and its summary.
- `sign_aligned_numeric`: the DESeq2 PCA tables.

**Findings, counted as differing (F), never entries:**
- nf-core/atacseq 2.1.2's HOMER peak annotation is not deterministic: for a peak equally near two genes it names one or the other between runs (for example YOL103W-A or YOL103W-B), because `genome/genes.bed` lists tied genes in a different order each run. Six annotation files under the recorded outputs carry it, so every output that holds them (the peaks folder and the merged-library tree) counts as differing.
- The DESeq2 sample-distance tables hold the same distances with samples in completion order; no mode is declared for them, so they count as differing too.

The expected result for a re-run that behaves as the early probe did, before any pass: of 6 outputs, the bigWig folder and the consensus BED match exactly (M = 2), the counts table within the stated tolerance (K = 1), the MultiQC report present but not byte-comparable (P = 1), and the peaks folder and merged-library tree differ (F = 2), causes in PROVENANCE.md.
Pass 1 compares against the AWS Batch record, a different machine type, so its own differences may add `pass-1` entries, each counted apart.

**Erratum, 6 October 2026 (the exemplar review's first round; the entries file and the frame above are unchanged):**
- `column_matched_table` also drops the table's `#` comment lines (featureCounts' program and command line) before comparing, and `sign_aligned_numeric` compares a PCA table's numbers only, not its header row or `#` comment lines; the shipped PROVENANCE.md declares both.
- A file a re-run holds inside a recorded directory output that the run did not record counts that output as differing (F), beside the four rollup rules above.
- "Six annotation files" above are five annotatePeaks tables and the plots PDF drawn from them; that PDF also embeds a creation date, so its difference is not shown to be HOMER's alone. The package's own PROVENANCE carries this correction under "Corrections", from the file `reproduction/yeast-atac/package-errata.json` beside the package (decision 0281).
- A match under a normalising mode is reported as `match after <mode>`, apart from a byte-identical `match`, so no member tally can conflate the two.

## Pass 1

Run 6 October 2026 on a fresh m5.xlarge cloud machine (4 vCPU, 16,550,289,408 bytes of memory for Docker, no container image cached), by the package's own `rerun.sh` and `verify.py --against`, against the exemplar's AWS Batch record: `rerun.sh` exit 0 in 2026 seconds.
**Result: of 6 outputs (209 files), 2 matched exactly, 1 within the stated tolerance, 1 present but not byte-comparable, 2 differ (causes in PROVENANCE.md)**, the expected result above.
Members: 105 byte-identical, 39 equal after their declared normalisation (37 `sorted_table`, 2 `column_matched_table`), 2 within 1e-9 after sign alignment (the PCA), 55 present (`presence`), 8 differ; the 8 are exactly the two findings above (the HOMER annotation files and the plots PDF drawn from them; the two sample-distance tables).
No `pass-1` entry was needed: every member that did not match exactly is covered by an `S2b-preregistered` entry or a finding.
Pass 1 ran against an earlier render of the same harvest, with the same re-run commands; it is **re-judged** offline against the package of record (`f5964ece…`, decision 0281) by that package's own `verify.py --against` over pass 1's re-run folder, and reads the same line (exit 2; the re-judgment's output and member table are the artifact `rejudge-f5964ece.tgz`, sha256 `d4d33c4d0acc78c640c36e1cc7de09e6ca81e3cf5c98ce17ae2c0281ac21f87c`).
A cold-cache pass raised the machine's root-disk use by 15.02 GB (container images included); the re-run folder held 0.90 GB.

## Passes 2 and 3 (the claim passes)

Run 6 and 7 October 2026 after the exemplar review's last round, on the package of record (`f5964ece…`, decision 0281), each on its own fresh m5.xlarge cloud machine (4 vCPU, 16,550,252,544 and 16,550,240,256 bytes of memory for Docker; no container image cached), by the package's own `rerun.sh` and `verify.py --against --table-out`: `rerun.sh` exit 0 in 2034 and 2111 seconds.
**Both read: of 6 outputs (209 files), 2 matched exactly, 1 within the stated tolerance, 1 present but not byte-comparable, 2 differ (causes in PROVENANCE.md).**
**They agree** under the rule above: the two member tables are identical, member by member, in mode and in result (209 members, none disagreeing), and equal pass 1's re-judgment: 105 byte-identical, 37 after `sorted_table`, 2 after `column_matched_table`, 2 within 1e-9 after sign alignment, 55 present, 8 differ (the two findings).
`reproduction/yeast-atac/README.md` is `package_run.py rerun-note`'s rendering of the two pass artifacts (`repro-pass2.tgz`, sha256 `6769d3187d866dbf7835141ee5536ab1faaa0d7836510f0fb0cfe1380d701587`; `repro-pass3.tgz`, sha256 `7613fd7bcd1240abd50752e5a370ff2efa3a30f668d87a6d994c1fc54d255c2d`).
Root-disk use rose by 15.05 GB and 15.02 GB over each pass's start.

## What this does not close

- Independence: every pass is run by the repository's own machinery, never by another person.

## Test

`gars/tests/test_package_run.py` holds the rollup and the exit codes: a `presence` member counted in M or K, a `presence` output dropped from N, or a skipped member must each make a test fail (mutation-checked).

## Status

Draft, on the build branch `lane/repro-package`; the frame, rules and entries are frozen and passes 1, 2 and 3 are in; finalised with the landing.

## Date

2026-10-05
