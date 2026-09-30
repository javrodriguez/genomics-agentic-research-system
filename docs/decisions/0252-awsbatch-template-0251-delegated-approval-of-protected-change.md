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
# Security fix and AWS Batch executor template 0251: approval of its protected change, under the owner's delegation

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

Follow-up 0251 is a security fix (the disclosed pre-existing finding in 0251: text hidden after a `//` inside a double-quoted string passed the executor-config check on public main since row 6's landing), and it lets `check_groovy` compare a project's executor config with the protected template its descriptor names, adds the AWS Batch template, and fences the name so the file checked is the file passed with `-c`.
The lane's coordinator (glitch-14, writing under the owner's standing delegation and not in the owner's words) ruled option (b) on 30 Sep 2026 at 01:45 EDT, reserved records 0251 to 0255 for this lane, and put the smoke ceremony after Wave 1's priority on the build Mac ends, Thu 1 Oct 2026 16:00.
It was built on branch `gars-awsbatch-template` from public main `37a8d94` in a `--no-local` lane clone with no remote, under the repository's noreply identity, red-first:
`8b2c0cf` (the template, the fixture and the new test module, red at `37a8d94`'s code), `1fee9e6` (the fix), the records commit that adds 0251, this record, the index and the counts, a wording fix to 0251, and the answer to review r1 (CHANGES, 1 MAJOR, 3 MINOR: tests 12 and 13 red first, then the fix, recorded in 0251 item 4), the trace fields `native_id` and `exit` (test 14 red first, F-L3-3), the answer to review r2 (CHANGES, 2 MAJOR, 3 NOTE: tests 15 and 16 red first, then the fix, recorded in 0251 item 4, with R6 and R7 recorded), and the coordinator's render ruling of 30 Sep 2026 (exact render equality for the Batch config: tests red first, then the slotted template and the render check, 0251 item 5, with R8 recorded).
Review: a fresh-context reviewer grades the branch; its verdict and the review file's sha256 are recorded at the landing, below, and the review itself stays outside the repository.

## Decision

The following protected changes are approved under the owner's 23 September 2026 delegation, as they stand at the branch head, subject to the owner's yes in the slot above.

1. **`gars/_templates/config/nextflow.awsbatch.config`** (new): the file 0251 items 1 and 5 describe; three slots (`queue`, the `goal` job-tag value, `region`), every other byte fixed, the cliPath included; a Batch config is admitted only as its exact rendering; sha256 `b8f64f35410b60bcb63f240e73b373997431f92c92dcfbba5cb5e5a7b0c78ac0` (the trace fields carry `native_id` and `exit`, F-L3-3; the slots per the coordinator's render ruling of 30 Sep 2026).
2. **`gars/_system/wrapperlib.py`**: `check_executor_config`'s `_config/` fence, moved before the descriptor is read, the project bound to the passed file's `_config/` parent instead of a walk up (review r1, L5-R1-3), and its passing of the descriptor's name; `EXECUTOR_TEMPLATES`, `EXECUTOR_TEMPLATE_NAME` and `executor_template()`; `check_groovy`'s `template_name` parameter (default the slurm template) and its use of `executor_template`; `check_groovy`'s `shape`, rewritten after reviews r1 and r2 as a lexer as strict as Groovy's (strings read before comments, each double-quoted string byte for byte, identifiers, numbers, operators and line ends compared; L5-R1-1, L5-R1-2, L5-R2-1), with `GROOVY_TOKEN` and `GROOVY_COMMENT_END`, and the config read as bytes; `check_executor_config` checking the passed fallback file when the descriptor names no config (L5-R2-2); `EXECUTOR_RENDER_SLOTS`, `EXECUTOR_SLOT`, `rendered_slots` and `check_rendering`, and `check_groovy`'s route of a rendered template's name to them (the render ruling, 0251 item 5); `execution_evidence`'s `execution_config_rendered` record; the comments and the docstring sentence. Every other line is as at `37a8d94`.
3. **`gars/_system/executorlib.py`**: in `validate`, the bare-file-name rule for `nextflow_config` and its comment, and the refusal of a blank `nextflow_config` on a backend whose built-in names one (L5-R2-2). Every other line is as at `37a8d94`.

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
- Review r1: tests 12 and 13 at `2a144e1`'s code, `Ran 13 tests`, `FAILED (failures=15)`, each an admission where a refusal is due; after the fix, `Ran 13 tests`, `OK`; `test_policy_attacks.py` `Ran 19 tests`, `OK`; the slurm trace-grammar test `OK`.
- F-L3-3: test 14 at `a36c96e`, `Ran 14 tests`, `FAILED (failures=1)` on the fields pin; with the fields added, `Ran 14 tests`, `OK`; ExecutorSeamTests `Ran 22 tests`, `OK`; the slurm trace-grammar test `OK`.
- Review r2: tests 15 and 16 at `eab4710`'s code, `Ran 16 tests`, `FAILED (failures=10)`, each an admission where a refusal is due; after the fix, `Ran 16 tests`, `OK`; ExecutorSeamTests `Ran 22 tests`, `OK`; `test_policy_attacks.py` `Ran 19 tests`, `OK`; the slurm trace-grammar test `OK`.
- Render ruling: at `ce06969`'s code with the new tests and fixture, `Ran 17 tests`, `FAILED (failures=19, errors=1)`; with the slotted template and the render check, `Ran 17 tests`, `OK`; ExecutorSeamTests `Ran 22 tests`, `OK`; `test_policy_attacks.py` `Ran 19 tests`, `OK`; the slurm trace-grammar test `OK`.
- `tests/run_tests.py ExecutorSeamTests`: `Ran 22 tests`, `OK` (`test_09` unchanged).
- `tests/check_counts.py`: 1208 clean at `37a8d94`, 1225 clean with this change's documents (1219 before review r1's two tests, 1221 before test 14, 1222 before review r2's two tests, 1224 before test 17).
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
