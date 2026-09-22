---
date: 2026-09-21
status: standing
kind: defect
touches:
  - gars/_system/hooks/pre-commit
  - gars/_system/hooks/pre-push
  - gars/tests/secret_support.py
  - gars/tests/test_hooks_gitleaks.py
  - gars/tests/test_secret_containment.py
  - README.md
  - DEVELOPMENT.md
  - docs/implementation/row_15_change_report.md
symptoms:
  - NUL-containing or -diff blobs pass a textual secrets scan
  - encoded assignment logs report zero contaminated sinks
  - current collection count substituted into historical platform evidence
---
# Row 15 review round 2 addendum to 0052

The owner requires inherited content at `c934f6d` to remain untouched as inherited,
out-of-scope content; its presence is not a defect. Implementation documents are living;
decisions, reviews, assessments and earlier report sections remain append-only.
Number 0053 remains reserved for the sibling row; no sibling file is changed.

## Scan completeness

Decision 0052's textual scan missed blobs that Git suppresses as binary, including
an ordinary text file assigned `-diff`. Both hooks now inspect Git's NUL-delimited
numstat before invoking the scanner and refuse any binary entry. The refusal
covers **clean binary files too**: these hooks cannot certify omitted content.
This is the review's allowed fail-closed alternative to scanning actual blobs.
No binary content is silently accepted based on the textual scanner's exit zero.

Pre-commit checks the index diff, independently of unstaged candidate contents.
Pre-push checks every outgoing revision in each accepted range, including root
and merge diffs. Disabling rename detection keeps numstat records independent and
exposes renames as deletion/addition pairs. A secret subsequently removed from the
pushed tip still refuses. New remote refs retain the conservative reachable-history
scope; binary history can therefore refuse a new-ref push even if its tip is clean.
Git query failures and timeouts refuse. Prior hooks and the whole-suite gate retain
their independent vetoes and still execute. No bypass setting is added.

Real gitleaks regressions plant both NUL-prefixed canaries and a staged `-diff`
attribute, exercise both production hook entry points, and reproduce the bypass
when only the new guard is disabled in a disposable copy. No actual push is used.
This gate addresses Git's binary/attribute suppression; it does not establish
universal secret detection, arbitrary archive decoding or live agent containment.

## Encoded assignments

The bounded test decoder treats `=` as padding at the end of a base64 token,
rather than accepting it anywhere inside a token. Assignment keys no longer join
the encoded value. Hex, base64, nested encoding, quoted values and unquoted log
assignments are exercised. Five decoded layers remain the limit. Actual scratch
log plants must report the logs sink, and their zero-sink assertions fail.

## Evidence correction and unresolved scope

The September 17 measurement remains 236 tests with 28 skips. September 21's
current collection and execution are separately dated in README and DEVELOPMENT;
the existing count guard classifies the older measurement with its documented
historical-count marker. No guard or threshold is weakened. The earlier report's
claim that all three count-only edits were accurate is corrected by the appended
round-2 section, without rewriting its history.

R15-03 is stopped at the recorded new-module scope boundary: the review requests
configuration, real Git objects and a deterministic scanner in row 3's disposable
fixture setup, preserving all assertions. The owner has not authorized that edit.
The full-suite failures remain failures, not an accepted alternative to green.
The change report records the requested scope ruling and all residual gaps.
