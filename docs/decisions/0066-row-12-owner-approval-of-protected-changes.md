---
date: 2026-09-22
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/_system/tools/registry.json
  - gars/_templates/config/executor.yaml
  - gars/02_bioinformatics/CONTEXT.md
  - gars/03_custom_analysis/CONTEXT.md
  - gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md
  - gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md
symptoms:
  - row 12's guard, settings, registry and template changes are protected paths with no owner approval record
  - merge ruling 8 of 0063 requires that record as a separate owner commit at merge
---
# Row 12: the owner's approval of its protected changes

Addendum to [0063](0063-row-12-lifecycle-status-writer.md), [0064](0064-row-12-review-addendum.md) and [0065](0065-row-12-corrected-inputs-addendum.md), which stay byte-identical apart from the status line the owner set under ruling 4A.
Every file this record touches is a protected path (R-094, spec §9.3), so their approval is the owner's own commit with this record as its approval record, in the shape of row 4's [0060](0060-row-4-owner-approval-of-protected-changes.md).
The changes themselves arrived with row 12's merge; this commit adds only this record and the regenerated decision index.

## Context

Row 12 (the lifecycle status writer) was built on its own branch and merged onto main on 22 September 2026, after Gap Study round 3's done commit.
Its ruling 8, given by the owner and quoted verbatim in 0063, keeps the protected-path approval out of the producer's hands: "The owner's approval record is still required for the row-12 guard, settings.json and registry changes, as a separate owner commit at merge in the shape of row 4's 0056. Never claim it."
0056 is 0060 after the merge's renumbering.
The row's final independent review (Claude Code, fresh context, round 4 on `b8be4eb`) was APPROVE WITH CHANGES with four MINOR findings and no BLOCKER or MAJOR; its SHA-256 is `91acbbf2f3480502c5d21e3ffd3d213c963d335d3591a2a035d90d26401c9938`, and it is kept outside the repository.
Rounds 1 and 2 were REJECT; round 3 was APPROVE WITH CHANGES.

## Decision

The owner approves the following protected changes as merged, on 22 September 2026.

1. **The guard makes lifecycle evidence code-owned (0063 ruling 13A, R-151).** `guard_hook.py` adds eleven read-only patterns under `projects/`: STATUS and its lock, the submission and local-job records, the run-complete marker, the local exit file, the reproducibility manifest, `submit.sh` and `params.yaml` of stage 02.
   A write to STATUS is refused with the typed `executorlib.py status` call named in the message.
   Every read-only match is now case-insensitive, so `status`, `FILES.CSV` and `plan.MD.approved` are refused like their canonical spellings.
2. **Settings mirror the guard.** `.claude/settings.json` adds the same eleven paths as `Edit` and `Write` denies, 22 lines.
3. **The registry supplies cancel (0063 ruling 4).** `status` records its side effect, the scheduler-derived STATUS refresh.
   `cancel` is no longer unavailable: the producer role moves from `needs-approval` to `allow`, the reviewer stays `refuse`, and the executor itself refuses a job older than one hour unless an approval record in the R-073 shape names that job id and backend.
   Both entries move to version 1.1.0.
4. **The executor template keeps scheduler reasons (0063 ruling 7).** `executor.yaml` reads `State,ExitCode` in parsable form, adds `cancel_argv` (`scancel`) and `start_argv` (the scheduler's start time), and maps CANCELLED, TIMEOUT, NODE_FAIL and OUT_OF_MEMORY to their own states instead of a bare FAILED; the normaliser that bridged the old template is removed in the same change.
5. **The stage contracts use the typed calls (0063 rulings 2, 6 and 13A).** The agent never writes STATUS; the four inherited raw `sbatch` lines are typed `executor.submit` calls; step 8 of the seven stage-01 contracts follows the VALIDATING and collect-failure states.

## What this does not close

- **The stage-03 run marker is agent-writable (review round 4, MINOR-4).** The guard protects `02_bioinformatics/*/run/.gars_run_complete` only, so a session can write `03_custom_analysis/<slug>/run/.gars_run_complete` and pass stage 03's `verify` gate without running anything; 0063's word "execution-created" claims more than the guard enforces.
- **Cancel does not ask the scheduler first (MINOR-2).** A job that finished after the last poll is treated as live: on the local backend SIGTERM goes to a recorded PID that may by then belong to another process, and CANCELLED overwrites a completion the exit file and marker already prove.
  This record approves the producer's `allow` on cancel with that gap known.
- Three guards are not pinned by a red test (MINOR-1), and two contracts describe states nothing produces or omit ones code writes (MINOR-3).
- The review could not verify real `sacct` or `scancel` output, the Slurm path of R-076, Python 3.6.8, the harness's permission-glob semantics for `settings.json`, or the reviewer as a separate OS user.
- Row 12's exit is NOT met as a whole: ambiguous submission recovery (ruling 9), published benchmark pins (ruling 10) and live scheduler acceptance remain open, as 0063-0065 state.
- A review in a fresh context on the same machine and OS user is `independent_context`, not `external_human_seal`.

## Test

The full checks ran at the merge head `4a76154`, with every protected change this record approves in place, on 22 September 2026:
`python3 tests/run_tests.py` in the three CI suite modes printed `Ran 397 tests` and `OK` in each (skipped 11, 55 and 86; `canary: 0/9` in modes A and B); `python3 tests/check_contracts.py`: `14 contracts clean`; `python3 tests/check_counts.py`: 397, `enforced=3`, clean; the harness `Ran 44 tests`, `OK`; the pre-registration check clean with `graded=1`.
This record changes no code; with it placed and `bash docs/decisions/build_index.sh` re-run, row 11's record checker (`decision_links` in `gars/_system/hooks/pre-commit`) accepts every record and prints `citations: 292/292 resolve`, and the contracts and counts checks stay clean.
Row 12's own acceptance and red-on-fault evidence is in [its change report](../implementation/row_12_change_report.md) and was reproduced by the round 4 review (nineteen plants, seven probe families, three suite runs).

## Status

standing

## Date

2026-09-22
