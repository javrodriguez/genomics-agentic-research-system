---
date: 2026-09-30
status: standing
kind: decision
touches:
  - gars/_system/wrapperlib.py
  - gars/_system/executorlib.py
  - gars/_templates/config/nextflow.awsbatch.config
symptoms:
  - follow-up 0251 changes gars/_system/ and adds a file under gars/_templates/ with no owner approval record
---
# AWS Batch executor template 0251: approval of its protected change, under the owner's delegation

Addendum to [0251](0251-awsbatch-executor-template.md), which stays byte-identical.
The files this record approves are protected (`gars/_system/` and `gars/_templates/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0171](0171-executor-env-0170-delegated-approval-of-protected-change.md).
The lane's coordinator also asked for a slot for the owner's own yes, recorded below only in his words.

## The owner's yes (EMPTY until he types it)

> OWNER'S WORDS: NOT YET GIVEN. This slot is filled only with the owner's own typed words, quoted verbatim, never paraphrased and never written by the lane.
>
> - Words (verbatim): _(empty)_
> - Typed at (from `date`, with timezone): _(empty)_
> - Candidate sha he approved: _(empty)_

Until the slot is filled, nothing in this record is the owner's approval, and the candidate is not pushed; every public GARS push is the owner's own hands (the coordinator's ruling R1 of 30 Sep 2026).

## Context

Follow-up 0251 lets `check_groovy` compare a project's executor config with the protected template its descriptor names, adds the AWS Batch template, and fences the name so the file checked is the file passed with `-c`.
The lane's coordinator (glitch-14, writing under the owner's standing delegation and not in the owner's words) ruled option (b) on 30 Sep 2026 at 01:45 EDT, reserved records 0251 to 0255 for this lane, and put the smoke ceremony after Wave 1's priority on the build Mac ends, Thu 1 Oct 2026 16:00.
It was built on branch `gars-awsbatch-template` from public main `37a8d94` in a `--no-local` lane clone with no remote, under the repository's noreply identity, red-first:
`8b2c0cf` (the template, the fixture and the new test module, red at `37a8d94`'s code), `1fee9e6` (the fix), and the records commit that adds 0251, this record, the index and the counts.
Review: a fresh-context reviewer grades the branch; its verdict and the review file's sha256 are recorded at the landing, below, and the review itself stays outside the repository.

## Decision

The following protected changes are approved under the owner's 23 September 2026 delegation, as they stand at the branch head, subject to the owner's yes in the slot above.

1. **`gars/_templates/config/nextflow.awsbatch.config`** (new): the grammar 0251 item 1 describes; four single-quoted site values (`queue`, the `goal` job-tag value, `aws.region`, `aws.batch.cliPath`); sha256 `e096d48f3b804eba42b240ab8c9ba5d25627fbf19629c2545b43786f267b8506`.
2. **`gars/_system/wrapperlib.py`**: `check_executor_config`'s `_config/` fence and its passing of the descriptor's name; `EXECUTOR_TEMPLATES`, `EXECUTOR_TEMPLATE_NAME` and `executor_template()`; `check_groovy`'s `template_name` parameter (default the slurm template) and its use of `executor_template`; the two comments and the docstring sentence. Every other line is as at `37a8d94`.
3. **`gars/_system/executorlib.py`**: in `validate`, the bare-file-name rule for `nextflow_config` and its comment. Every other line is as at `37a8d94`.

Outside the protected prefixes, recorded for completeness: the new `gars/tests/test_executor_templates.py` and its fixture, 0251, this record, the index, and the README and DEVELOPMENT counts.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0251, the double-quoted `errorStrategy` outcomes (a departure from the 3 Sep form, with its reason in 0251), the fixed clamp, the trace block without `report` and `timeline`, and the `executorlib.validate` rule (an addition to the coordinator's ruling, which named `check_groovy`; without it an absolute name into another project's `_config/` would be refused by no layer that sees the requesting project's descriptor).

## What this does not close

- 0251's R1 to R5.
- The demo's generator still writes the 3 Sep shape, which this template refuses; its own lane matches it to the template sha256 above.
- The smoke ceremony (row 14) for this `_system/` landing is not yet run; it runs at the final merge.

## Test

On the branch (macOS, Python 3.13.2, `TMPDIR` in the lane's folder):

- `gars/tests/test_executor_templates.py`: at `37a8d94`'s code with the template in place, `FAILED (failures=19, errors=1)` over tests 01 to 10; at `1fee9e6`, `Ran 11 tests`, `OK`.
- `tests/run_tests.py ExecutorSeamTests`: `Ran 22 tests`, `OK` (`test_09` unchanged).
- `tests/check_counts.py`: 1208 clean at `37a8d94`, 1219 clean with this change's documents.
- `tests/check_contracts.py`: 14 contracts clean.
- The full suite and the mutation proof: recorded at the landing (below).

## At the landing (PENDING: written by the lane executor at the final merge)

- The merge sha, its first parent (public main at the time) and its trailers.
- The full suite at the merge, with its skip figures, and the Fresh-clone gate against the records commit's README.
- The smoke delta: the record, `smoke.py score`'s verdict, and `audit_trailers.py`'s line for the merge.
- The review's verdict and the review file's sha256.
- The secret and privacy sweep over the outgoing range.

## Status

Standing once the owner's slot is filled. Approval of follow-up 0251's protected change only.

## Date

2026-09-30
