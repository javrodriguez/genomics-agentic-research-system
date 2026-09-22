---
date: 2026-09-22
status: standing
kind: decision
touches:
  - gars/tests/test_pre_push.py
  - gars/tests/test_secret_containment.py
  - README.md
  - DEVELOPMENT.md
  - docs/implementation/row_15_change_report.md
symptoms:
  - pre-push clean-pass fixtures omit scanner configuration and valid Git objects
  - D-17 sink identities remain recorded as defaults pending an owner ruling
---
# Row 15 provisional owner rulings: addendum to 0052 and 0054

## Context

The owner instructed the program to proceed with its recommended options while
away, with each ruling to be confirmed or reversed afterwards. This dated
addendum records that authority for review round 4; earlier decisions, reviews,
assessments and change-report sections remain unchanged. Number 0053 belongs
to row 4 on another branch and remains out of scope.

## Decision

### R15-03, option A

**provisional ruling, to be confirmed by the owner** — attributed to **the owner**.

The narrow repair to `gars/tests/test_pre_push.py` is authorised: repair only the
affected disposable fixture setup by supplying the required scanner configuration,
valid scratch Git objects in place of the fake object ID, and a deterministic
stand-in scanner on PATH. Preserve every existing assertion, stdin check and veto
behaviour in meaning. List each changed line and its reason in the round 4 change
report. The whole suite must end OK in this run. This ruling resolves the stopped
scope question recorded in 0052/0054 for this repair; it does not authorise other
row 3 changes or any row 4 change.

### D-17, option A

**provisional ruling, to be confirmed by the owner** — attributed to **the owner**.

The three extra sinks are confirmed provisionally as:

7. Generated job script: `submit.sh` / `reproducibility/commands.sh`.
8. Reproducibility manifest.
9. Git index: staged blob bytes, as defined in 0052.

The living documents use these identities now. Earlier records retain their
historical wording. This confirms the sink identities provisionally; it does not
establish full R-096 containment, a live exfiltration-instructed agent task,
credential isolation or job-runtime containment. The owner may confirm or reverse
each provisional ruling in a subsequent dated record.

## Test-that-proves-it

`python3 gars/tests/test_pre_push.py` exercises the repaired fixtures with all
existing clean acceptance, stdin, argument, installer, empty-suite and veto checks.
`python3 tests/run_tests.py` must finish OK; no assertion, threshold, scanner guard
or protected tree may be weakened to obtain green. The change report records the
line-by-line fixture changes, fault controls and exact runner summaries.
`python3 gars/tests/test_secret_containment.py` exercises the existing nine sink
identities, including their positive controls; its repository-side scope stands.

## Status

standing; both rulings provisional, to be confirmed by the owner.
The separate study merge hold and all unmeasured full-containment limits stand.

## Date

2026-09-22
