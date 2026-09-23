---
date: 2026-09-22
status: standing
kind: defect
touches:
  - gars/_system/hooks/pre-commit
  - gars/_system/hooks/pre-push
  - gars/tests/test_hooks_records.py
  - scripts/release_check.py
  - tests/test_release_check.py
  - README.md
  - DEVELOPMENT.md
  - docs/implementation/row_11_change_report.md
symptoms:
  - local Git replacement hides a dangling staged citation
  - local Git replacement makes a same-session committed review pass
  - terminal restore FAIL correction displays an earlier PASS
---
# Row 11 raw Git and terminal restore addendum to 0061

## Context

Independent review R11-01 and R11-02 rejected the producer's initial enforcement
claims. Record 0061 and the earlier report remain historical bytes: their
unqualified reconstructible-snapshot and R-165 PASS claims did not hold when local
Git replacement objects supplied substitute contents. The restore adapter also
ignored row 5's final FAIL correction when its timestamp equaled the earlier PASS.
This addendum corrects implementation under existing owner rulings, without a new
schema, threshold, citation population, legacy cutoff or evidence policy.

## Decision

Every Git operation in the citation and trailer readers uses the command-line
`--no-replace-objects` setting. This includes index blobs, outgoing history,
adoption discovery, commit messages, ancestry, tree paths and evidence blobs.
Adoption discovery excludes `refs/replace/*` from its all-ref traversal: these
refs are substitution metadata, not additional adoption history. Ordinary local
refs and detached outgoing tips still participate. The later committed evidence
snapshot requirement and all independent hook vetoes remain in effect.

Restore selection orders by invocation timestamp, then append order. The terminal
row for the latest timestamp supplies the status and final RTO. This consumes the
append-only correction semantics established by records 0046 and 0047; a later
appended older invocation does not displace the latest invocation. The four-field
CSV still cannot establish venue, off-machine provenance or independent canary
provenance. Those limitations remain unmeasured and release eligibility refuses.

The measured citation count remains `citations: 288/288 resolve` in this round;
new fault strings are assembled without adding literal counted citations to the
source population. The frozen specification is unchanged.

## Test

`python3 gars/tests/test_hooks_records.py` invokes the shipped hooks in disposable
repositories with replacement blobs and commits. The new staged-citation and
same-session-review tests failed against the preceding implementation; history
replacement subtests also failed their original-enforcement assertions. They
cover adoption, changed paths, trailer contents and outgoing ancestry. Scanner
and miniature suite controls still run; the scanner is deterministic in these
new tests, not evidence of real secret detection.

`python3 tests/test_release_check.py` includes an actual CLI regression using
same-timestamp PASS/FAIL records and a subsequently appended older record. It
failed against the earlier adapter and checks final RTO/status, byte verification
and continued tag refusal. The change report records final command results,
whole-suite execution and inherited real-scanner checks.

## Status

standing; corrective implementation subject to independent review and owner
approval. Genuine Bench evidence for the final producer commit, later committed
evidence, full release eligibility and the separate-study merge hold remain open.

## Date

2026-09-22

_Renumbered at merge, 2026-09-22: this record was written as 0059 on its branch and takes 0062 on main, because the row-5 fix and rows 15, 4, 11 and 12 numbered their decisions independently (merge order: row-5 fix, 15, 4, 11, 12). Its number, link targets and the numbers of other rows' records it cites are the only edits; branch-time number notes are left as written._
