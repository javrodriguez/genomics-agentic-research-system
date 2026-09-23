---
date: 2026-09-22
status: standing
kind: decision
touches:
  - docs/decisions/0057-row-15-provisional-owner-rulings.md
  - docs/decisions/0059-row-4-provisional-rulings.md
  - gars/tests/test_pre_push.py
  - gars/tests/test_secret_containment.py
  - gars/_system/tools/policy.py
  - gars/_system/tools/registry.json
  - README.md
  - DEVELOPMENT.md
symptoms:
  - a ruling applied while the owner was away still reads "provisional, to be confirmed by the owner" after he confirmed it
---
# The owner confirms the eight provisional rulings of rows 15 and 4

Addendum to [0057](0057-row-15-provisional-owner-rulings.md) and [0059](0059-row-4-provisional-rulings.md), which stay as written.

## Context

Rows 15 and 4 were built and reviewed overnight on 21–22 September 2026 while the owner was away.
Eight of their open questions were answered with the recommended option and applied as **provisional
rulings, to be confirmed by the owner**: two in [0057](0057-row-15-provisional-owner-rulings.md) and
five in [0059](0059-row-4-provisional-rulings.md), plus the choice of reviewer for row 4. Both records
say the owner confirms or reverses each ruling afterwards, in a later dated record. This is that record.
[0060](0060-row-4-owner-approval-of-protected-changes.md), the owner's approval of row 4's protected
changes, already says in its Context that he confirmed all eight; this record states the confirmation
for both rows and names each ruling.

## Decision

The owner confirmed all eight rulings as his own on the morning of 22 September 2026, unchanged. The
labels are the ones the rulings were put to him under.

Row 15 ([0057](0057-row-15-provisional-owner-rulings.md)):

1. **1A, R15-03:** the narrow repair of the disposable fixture set-up in `gars/tests/test_pre_push.py`
   (scanner configuration, valid scratch Git objects, a deterministic stand-in scanner), every
   assertion, stdin check and veto kept.
2. **2A, D-17:** sinks 7–9 are the generated job script (`submit.sh` / `commands.sh`), the
   reproducibility manifest and the Git index (staged blob bytes).

Row 4 ([0059](0059-row-4-provisional-rulings.md), its rulings 1 to 5 in order):

3. **3A:** the approval store lives outside the workspace, with a UTC expiry.
4. **4A:** the named updates to existing characterization tests and pins.
5. **5A:** collect re-hashes its inputs in all ten wrappers.
6. **6A:** contracts spell registered paths literally.
7. **7A:** `cancel` is refused until row 12 supplies it (row 12 has since supplied it, 0063).
8. **8A:** Claude Code reviews row 4 while Codex refuses the brief, as its round-3 review was run.

Nothing is reversed. The living documents stop calling these rulings provisional; the earlier records
keep their wording, because decision records are append-only.

## What this does not close

- Every limit 0057 and 0059 name stays open: full R-096 agent containment and the
  exfiltration-instructed task, the injection fixture's 20/20, and the reviewer as a separate OS user
  (R-093).
- The confirmation is the owner's word, relayed from the aegis programme record of 22 September 2026;
  it is not a review.

## Test

`python3 tests/run_tests.py` is unchanged by this record. The checks that bind it are the ones that
bind any record: `python3 -c "import runpy; print(runpy.run_path('gars/_system/hooks/pre-commit')['decision_links']('.'))"`
prints `True` with every citation resolving, and `bash docs/decisions/build_index.sh` lists this record.
A living document that still calls one of the eight rulings provisional is the fault this record removes:
`git grep -n "to be confirmed by the owner" -- README.md DEVELOPMENT.md` prints nothing.

## Status

standing. It confirms the rulings; it does not approve anything the rulings did not already cover.

## Date

2026-09-22
