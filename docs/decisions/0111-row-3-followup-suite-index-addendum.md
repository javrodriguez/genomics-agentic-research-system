---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/tests/test_r164_collect_gates.py
  - gars/tests/test_r164_writer_recovery.py
symptoms:
  - a row 3 follow-up test module is missing from every record's touches, so the index cannot find its record
---
# Row 3 follow-up: index addendum for the test modules added after 0087's first round

This record exists only so the decision index can find the two R-164 test modules the row 3 follow-up added after [0087](0087-row-3-followup-suite-strengthening.md)'s first round: `test_r164_collect_gates.py` (review round 2) and `test_r164_writer_recovery.py` (review round 4).
0087 and its dated addenda remain the record of the work, its reasons and its evidence; 0087's bytes were not edited, and its frontmatter still lists only the first round's modules.
The number is the plan's reserved spare, written on the lane's ruling under the owner's standing delegation of 23 Sep 2026.

## Addendum, 2026-09-25: the sections the record check requires (round 5)

The bytes above are unchanged. They lacked the five sections `gars/_system/hooks/pre-commit` requires of a record dated on or after 2026-09-22, so `tests/test_decision_links_resolve.py` failed on `167e7db` (`REFUSED (docs/decisions/0111-row-3-followup-suite-index-addendum.md: new record missing Context)`). No pre-commit hook was installed in the build checkout, so the commit went through. The sections follow, and they restate the text above.

## Context

The decision index finds a record by the paths in its `touches`. Review rounds 2 and 4 of the row 3 follow-up added `gars/tests/test_r164_collect_gates.py` and `gars/tests/test_r164_writer_recovery.py`. [0087](0087-row-3-followup-suite-strengthening.md)'s frontmatter does not list them, and a record's frontmatter is never edited.

## Decision

This record names the two modules in its `touches`, so the index can find them. 0087 and its dated addenda remain the record of the work. The number is the plan's reserved spare, used on the lane's ruling under the owner's standing delegation of 23 Sep 2026.

## Test

`bash docs/decisions/build_index.sh` lists both modules against this record, and `python3 tests/test_decision_links_resolve.py` accepts this record.

## Status

Standing.

## Date

2026-09-25
