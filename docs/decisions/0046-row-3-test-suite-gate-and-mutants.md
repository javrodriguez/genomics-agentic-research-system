---
date: 2026-09-15
status: standing
kind: decision
touches:
  - gars/tests/
  - gars/_system/hooks/
  - tests/run_tests.py
  - evals/mutate.py
  - evals/mutants.md
  - evals/MUTANTS-INTERFACE.md
  - docs/implementation/row_3_change_report.md
symptoms:
  - pre-push gate passes with an empty test tree
  - a text-only mutant is counted as killed
  - mutation run leaves tree bytes changed
---
# Row 3 test suite, pre-push gate and sealed mutation interface

## Context

R-164 (§16.3; §18 Row 3) names a suite under `gars/tests/`, a whole-suite pre-push gate,
and ten independently sealed semantic mutants. Decision 0023's existing unittest suite
lives in `tests/run_tests.py`; `check_counts.py` asks unittest's loader for its count.
The gap assessment Row 3 and review m-9 distinguish offline tests from environment skips.
Seven nf-core wrappers and three downstream wrappers exist. Resume lives in the generated
`wrapperlib.write_submit_sh` guard and uses `executorlib`'s existing submit/status seam.

Number note: 0043, 0044 and 0045 live on other branches and are not in this history. This
record uses 0046 to avoid collisions at merge.

## Decision

Add the four named Row 3 modules and gate/mutation/fault tests under `gars/tests/`. Retain
all existing tests in place. Extend the runner with unittest's `load_tests` protocol, used
by both execution and counting; discover `test_*.py` in both trees and refuse either empty
tree. Root embedded tests count toward `tests/`. Discovery/import errors fail the run. An explicit `TMPDIR` is used without
Python's silent fallback to another temporary directory.
Record the first failure in execution order, including subtests, for the mutation record.
Do not add `test_stage01_design.py`: Row 1 already supplies it under `tests/` on another
branch. Final suite placement across the two trees is **pending owner ruling at merge**;
this row does not move Row 1's work or decide that question.

The guard tests characterize its shipped allows/denies, including unreadable stdin and the
still-allowed bypass switches. No guard/library/wrapper behavior changes. Prepare tests
exercise the shared deterministic artifact writers for every pipeline pin. Resume tests
execute the generated guard using the real local executor and a tiny deterministic body:
interruption preserves prior work, resume adds the remaining effect, completed reentry
adds nothing. This is not proof of real Nextflow's cache behavior or submission deduplication.
Contract tests enumerate all wrappers from the tree, inspect their associated eight-section
contract and exercise each verb's structured refusal on a missing project. They print the
nf-core found/expected ratio and total wrapper count.

**Hook inspection and owner ruling.** This clone has only `.git/hooks/*.sample`, no
`core.hooksPath`, no active gitleaks pre-push, and no `guard_hook.py` installer. The guard
is configured in `gars/.claude/settings.json` as a harness PreToolUse command. The owner
explicitly authorized using Git's existing hook directory, preserving/chaining any existing
pre-push and replaying stdin to both. The installer follows Git's configured `core.hooksPath`
when present, otherwise its existing hook directory; it does not introduce a second setting.
An existing pre-push becomes `pre-push.gars-previous` in the same directory. Both gates run,
even when one fails; both receive the original stdin and the previous hook also receives
Git's arguments. Either veto refuses. Collisions are refused; repeated installation preserves
the saved hook. No hook is installed in this source clone. Scratch clones and direct script
calls prove the integration using a gitleaks stand-in; gitleaks installation remains later work.

`evals/MUTANTS-INTERFACE.md` is a standalone source-only handoff. A separate context creates
and freezes ten independent diffs with requirement IDs and read-only behavioral witnesses.
The runner requires a clean source checkout, checks an intact baseline, applies each diff in scratch, rejects unchanged Python
syntax/unchanged observations as ineffective, runs both test trees, records kill/survival
and first failure, and restores the scratch tree with a hash assertion. It also asserts the
source tree stayed byte-identical (Git metadata excluded). A witness is necessary because a
changed string or failing structural assertion alone does not prove a semantic fault. The
sealer/reviewer must judge witness meaning; the runner cannot prove semantic equivalence.
Unmeasured and ineffective results cannot satisfy the threshold. The ten record slots remain
unsealed. Producer-visible planted controls prove runner mechanics only, never the score.

## What this does not close

- **NOT met:** the ten sealed mutants and ≥ 8/10 killed; no set exists in this context.
- **NOT met:** `external_human_seal` for public claims.
- **NOT met:** R-165 trailers (Row 11), R-166 Linux integration (later work).
- **NOT met:** §9.2 role-profile/credential enforcement; the program's separate-checkout
  review practice (R-162) is retained, but this producer does not review or approve itself.
- **NOT met:** live gitleaks coexistence in this clone, whose gitleaks hook is absent;
  composition is proven with a stand-in. Bypass-switch denies remain later policy work.
- **Pending owner merge ruling:** final location of Row 1 and Row 3 suites. Both trees run now.
- **Standing owner ruling:** merge only after the separate study's done commit. Its source
  controls may go red because this row necessarily adds under `gars/` and `evals/`; do not
  modify that study, its graders/fixtures, or `.github/` to conceal the difference.

## Test

`python3 tests/run_tests.py`; `python3 tests/check_contracts.py`;
`python3 tests/check_counts.py`; `python3 evals/test_harness.py`;
`python3 evals/check_results.py --controls --lexicon`;
`python3 -m unittest discover -s gars/tests -p test_pre_push.py -v`.
The change report records exact summary lines and the observed seven red-on-fault controls.
No push is used to test a hook. Mutation report without a set prints `unmeasured`;
`--require` refuses. No trailer, Linux runner or release check is introduced.

## Status

standing; repo-side implementation subject to independent review; Row 3 exit NOT met

## Date

2026-09-15
