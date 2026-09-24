---
date: 2026-09-24
status: standing
kind: decision
touches:
  - gars/_system/claims/emit_report.py
  - gars/_system/claims/evidence_check.py
  - gars/_system/resolve_citation.py
  - gars/_system/integrity.py
  - gars/_system/stage01_samplesheet.py
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/00_initialize_project/CONTEXT.md
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
symptoms:
  - row 8 step A adds and changes code and contracts under the protected prefix gars/ with no owner approval record
  - 0101 leaves 0104 for the approval of step A's protected changes at merge; the owner delegated it on 23 September 2026
---
# Row 8, step A: approval of its protected changes, under the owner's delegation

Addendum to [0101](0101-row-8-defect-catalogue-and-detectors.md), which stays byte-identical.
Every path this record touches is under a protected prefix (§9.3, R-094), so its change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows row 9's [0073](0073-row-9-delegated-approval-of-protected-additions.md) and row 7's [0079](0079-row-7-delegated-approval-of-protected-additions.md).
The files themselves arrive with step A's merge; this commit adds this record, [0103](0103-row-8-seals-and-sealed-measurement.md), the six sealed ledger rows and the regenerated decision index.

## Context

Row 8's step A (the defect catalogue; spec §18 line 397) was built on its own branch from public main `dc6b803` by a producer (Codex) running as one unprivileged OS account, and reviewed by fresh-context reviewers (Claude Opus 5.5) running as a second, separate unprivileged OS account on the same node, through an unattended queue runner.
Every decision in the row's specification is labelled in 0101 and its addenda as the lane's, under the owner's delegation.
The step took nine producer commits, `e367a41` to `945dcee`.
Round 1's commit failed the runner's path scan on one false alarm (a literal tilde in an R design formula); a retry round removed the typed character and a later round restored the inherited lines that the retry's wording had caught by mistake (that wording was the lane's, not the producer's).
Reviews: C1 REJECT (ten findings), then re-reviews D1, D2 and D3 APPROVE WITH CHANGES (four, two and one MINOR), E1 APPROVE WITH CHANGES (two MINOR, one NOTE), and the final scoped review F1 APPROVE WITH CHANGES (one MINOR, two NOTEs), whose MINOR is accepted under the delegation as a named, fail-closed residual (0103).
The final review's SHA-256 is `1d5b0b1809c52fec02d71791292a49483641d6ef4af111081aac99392f97bc6a`; every review of the step is kept outside the repository.
Commit `a8b54e5` was authored and committed under a neutral producer identity (`GARS Producer`, at a reserved invalid domain) instead of the repository's configured identity; it is kept as it is, because the records are append-only and the reviewers graded that sha, and the address leaks nothing; every later round used the repository's identity.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected changes as merged, on 2026-09-24.

1. **New `gars/_system/claims/evidence_check.py`** (catalogue class 7): the preflight that refuses a claims snapshot whose evidence names a missing, outside-the-project or changed artifact (`evidence_missing`, `evidence_hash_mismatch`), and routes each DOI-bearing source through the citation resolver.
2. **New `gars/_system/claims/emit_report.py`**: the one supported emission path, which runs the preflight in-process on one snapshot and only then row 7's unchanged renderer as a subprocess, writing no report on a refusal.
3. **New `gars/_system/resolve_citation.py`** (class 9, the DOI half of R-125): Crossref first, the DOI handle API on a 404, `citation_unresolved` only when both say not found, and any network error, 429 or 5xx `citation_unverifiable`; the command-line tools always use the live lookup, and replay is in-process only.
4. **`gars/_system/integrity.py`** (class 6, an R-042 change listed in 0101): under `full`, a FASTQ record-structure check for plain and gzip FASTQ; `quick` and `skip` are unchanged.
5. **`gars/_system/stage01_samplesheet.py`** (classes 3, 4 and 5): the sex/age rule (`confounded_condition` for a perfectly confounded `sex`; the `covariate_imbalance` DEGRADE flag at the pre-committed thresholds), the pseudoreplication refusal (R-145), and the swapped-label check against `library_index`, each an R-042 entry in 0101.
6. **`gars/_system/wrappers/rnaseq-de/rnaseq_de.py`** (class 8): the collect gate's `uncorrected_pvalues` refusal and its `check-table` diagnostic, an R-042 change with its named expectation change in `tests/run_tests.py`.
7. **The stage 00 and 01 contracts and the rnaseq-de sub-stage contract**: the schema block the detectors read and the new failure codes.

## What this does not close

Copied from 0101 and 0103:

- §17's sealed ≥ 9/10 over all ten classes; sealed plants for classes 3, 7 and 9; `external_human_seal`, so every public catch-rate cell stays `unmeasured`.
- PMID and the literature role's wiring of R-125; report emission other than through `emit_report.py` (direct renderer calls, stage 03 and the pilot flow) stays unguarded.
- R-069 artifact liveness beyond claim evidence; any detector for class 10 (Hi-C); the pilot-1 measurement.
- The DOI detection residuals named in 0103 (a fail-closed false refusal for clean references pairing a registered DOI with an ordinary `10.`, including ruling 7's two clean controls flipped to must-refuse; further spellings of the short-DOI shape; the stale anchor in `benchmarks/defects/red_on_fault.py`), carried to a follow-up lane that must land before a real pilot report is rendered.
- Execution on Python 3.6.8 and on the cluster is not evidenced.
- Step B (0100's data route, the venue policy and the backend bench) is a separate job and a separate approval.

## Test

Glitch verified the step independently on the owner's workstation, each evidence run alone on it:

- At the reviewed head `945dcee`: the suite in its three documented modes, `Ran 491 tests`, `OK` with 13, 75 and 106 skips; contracts, counts, harness and pre-registration checks clean; red at the parent and green at the head; six re-planted faults red then green; gitleaks 0 findings; the sealed measurement (0103).
- At this merge's tree: `Ran 533 tests` in each of the three documented modes, with 13, 75 and 106 skips (the README's figures); contracts, counts, harness and pre-registration checks clean; no temp or container leak.
  The only reds were one or two subprocess timeouts per mode inside row 9's `tests/test_review_faults_faults.py` (its per-case cap is 180 seconds; mode A `external input leak accepted`; mode B `answer interval shifted` and `absent reserved id leaks`; mode C `answer interval shifted`), on a workstation whose container VM was then 2 GB and busy.
  That module builds every case from a git archive of its own fixed base and reads nothing row 8 adds, and the files it reads are byte-identical between main `5ba82c6` and this merge; run alone afterwards with a 9.73 GiB, 8-CPU container VM it passed at both (`Ran 1 test`, `OK`; 802 seconds at `5ba82c6`, 1003 seconds at this merge).
  So the reds are that module's timing margin under load, not a change made by row 8; its margin is reported to row 9.

## Status

Standing. Approval of step A's protected changes only; it does not claim the row's exit.

## Date

2026-09-24
