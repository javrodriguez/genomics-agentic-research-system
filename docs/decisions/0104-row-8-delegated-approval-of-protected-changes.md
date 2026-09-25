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

## Addendum, 2026-09-25: step B's protected changes, under the owner's delegation

Written by Glitch under the owner's standing delegation of 23 Sep 2026; no sentence in it is the owner's.
The record above stays byte-identical; this addendum approves row 8's step B (the data route, the venue policy and the backend bench; spec §18 line 397), which merges after it.

### Context

Step B was built on its own branch from a seed commit that adds [0100](0100-row-8-data-handling.md) on public main `452fe33` (rows 6 and 7 and step A merged), by a producer (Codex) running as one unprivileged OS account, and reviewed by fresh-context reviewers (Claude Opus 5.5) running as a second, separate unprivileged OS account, through the unattended queue runner, which checked that every producer commit carries the repository's configured identity.
The step took three producer commits after the seed, `efbe369`, `633778a` and `433b41e`.
Round 1's commit failed the runner's path scan on one false alarm (a relative glob whose folder segment shares its name with a top-level system folder) and raised one ruling; the retry round rewrote the flagged strings and answered the ruling.
Review B1 was a REJECT (one BLOCKER: with the homelab marker present, manifest group 11 refused the venue the re-pointed derivation records); its step also failed on two path-scan false alarms of the reviewer's own, so the lane carried the review into the producer's clone by hand, hash-checked.
Review C1 on `433b41e` was APPROVE WITH CHANGES with one NOTE and nothing else; its SHA-256 is `198c1d210dd274dafd8d6ae7b3783a4cce91f96c9a358b8c4e849990582d5d5f`, and every review of the step is kept outside the repository.

### Decision

Glitch, under the owner's delegation, approves step B's protected changes as merged:

1. **New `gars/_system/venue_policy.py` and new `gars/_references/data_policy.tsv`**: 0100's route table, machine-readable, and the policy that refuses a submission whose class, venue and purpose the table does not permit, before any record, launcher or scheduler call.
2. **`gars/_system/executorlib.py`**: `venue_of` (the homelab venue of the built-in `local` descriptor on a host carrying the machine-owned marker, whose path is a module constant), the two call sites in the stage 02 and stage 03 submit paths, and the `venue` key in submission records.
3. **`gars/_system/stage00_register.py`** and **`gars/_system/tools/registry.json`** (finalize's entry only): the dataset record's `permitted_backends`, `provider_exposure`, `retention` and `expiry` columns, narrowing only, and the refusals at finalize (`identifiable`, a missing expiry for `deidentified_under_agreement`, non-public data on a homelab-marked host).
4. **`gars/_system/wrapperlib.py`**: group 11's venue derived through `venue_of`, and, by the delegated ruling on the step's first raised question, two recorded manifest facts, `expiry` and `permitted_backends` ("the manifest gains two recorded facts; none removed").
5. **`gars/_system/manifest_check.py`** and **`gars/_references/manifest_schema.json`**: the checker and schema know the two new facts; and group 11 accepts exactly the three backend and venue pairs the re-pointed derivation records (`local`/`local`, `local`/`homelab`, `slurm`/`slurm`), no wider.
   **Ratification, answering review C1's NOTE.** Review C1 noted that 0102's addendum cites the ruling on the two recorded facts as the authority for the venue-pair edit, which that ruling did not cover. The venue-pair edit is ratified here, under the owner's delegation, as in-spec: step B's deliverable 10 requires the suite to pass with the homelab marker present and absent, and without the edit every manifest prepared on a marked host fails group 11. This ratification is the authority for that edit; 0102 stays byte-identical.
6. **The stage 00, 02 and 03 contracts**: the new failure codes.

Row 6's reproduction replay (`scripts/rerun_check.py`, not a protected path) now passes the recorded expiry and permitted backends and refuses, with `manifest_predates_expiry_recording`, a `deidentified_under_agreement` manifest prepared before those facts were recorded; without that change every re-run of such data would have reported a false non-reproduction, as reproduced below.

### What this does not close

Copied from 0102:

- The homelab and Slurm bench rows, and the local one: `backend rows: 0/3`; each row arrives later from its venue, bound to its evidence.
- R-193's priced unit economics (the rows are `unmetered` inputs); per-sample cost of real FASTQ analyses; `cloud`.
- R-061 and the enforcement of "only `public` enters a hosted-model prompt" (0100); the second backup destination; any institutional agreement.
- The venue is inferred from the descriptor that executes, not attested by the host; a session with sudo on the homelab can create the marker.
- A process outside the guarded session, or one that deletes and rewrites `00_data/dataset.tsv`, is not stopped by the guard (row 6's residual).

### Test

Glitch verified the step independently, each evidence run alone on its host:

- At the reviewed head `433b41e`, on the build node's owner account from a fresh clone of a bundle, with the temporary folder outside the clone: the suite in modes B and C, `Ran 610 tests`, `OK` with 79 and 106 skips; contracts, counts, harness and pre-registration checks clean; `data route recorded: 3/3`; `backend rows: 0/3 ()`; no temporary-file leak; no other test process on the host.
- The catalogue's development line is unchanged from step A (0103, clause 1, line 1): `planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)`, false flags 0/10, graded 19 of 19; the one class not caught is the Hi-C placeholder, class 10, by design, and step B's diff does not touch `benchmarks/defects/` or `tests/test_planted_defects.py`.
- The new test modules fail at the seed (import errors naming `gars/_system/venue_policy.py`, `gars/_references/data_policy.tsv` and `scripts/backend_bench.py`) and pass at the head.
- With step B's code but the seed's replay, row 6's reproduction check reports `reproduction: 0/2` with `dataset finalize failed: … dataset_expired: agreement expiry required`; with step B's replay it passes.
- Six mutations re-planted in a disposable clone each turned their named tests red and passed again once the bytes were restored: either submit path skipping the policy, the FASTQ exemption widened, the old-manifest refusal removed, the homelab marker read from an environment variable, and the 8 GiB boundary moved.
- gitleaks over `452fe33..433b41e` under the push door's ruleset and under `gars/.gitleaks.toml`: 0 findings; no canary; no account, host, address or home path in any added line or commit metadata.
- At this merge's tree (`19599ba`, step B merged onto main `57f9cc5`): `Ran 660 tests` in each documented mode, `OK` with 13 skips (mode A, on the owner's workstation with the container runtime answering), 79 (mode B) and 106 (mode C, both on the build node's owner account from a fresh clone of a bundle); canary 0 of 9 in modes A and B; contracts, counts and pre-registration checks clean; `evals/test_harness.py` `Ran 44 tests`, `OK`; row 6's `test_manifest_groups` and `test_rerun_check` green; `data route recorded: 3/3`; `backend rows: 0/3 ()`; no temporary-file or container leak.
  Two items of the lane's own checking script were corrected, not the repository: its harness step had run on the workstation's Python 3.8, which lacks string and syntax-tree functions the harness uses (under Python 3.12 the harness passes), and its pinned expectation for row 6's reproduction self-test still read the old `(fixture, local)` label, which step B changed to `(fixture, stub slurm)` as named in 0102 and the change report, with the result unchanged at `reproduction 2/2`.

### Status

Standing. Approval of step B's protected changes only; it does not claim the row's exit.

### Date

2026-09-25
