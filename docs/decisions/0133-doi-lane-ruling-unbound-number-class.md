---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/resolve_citation.py
  - gars/tests/test_emit_report.py
symptoms:
  - with a verified DOI present, a 10/ or 10. token that no DOI marker points at no longer refuses the report
---
# DOI lane ruling: the unbound-number class is the exact complement of binding

Addendum to [0130](0130-doi-marker-binds-its-number.md), which stays byte-identical.
A lane ruling, decided and recorded by Glitch under the owner's standing delegation of 23 September 2026 (review round 1 of the lane's plan, finding F2); no sentence in this record is the owner's.

## Context

0130's rule refuses a reference with a parsed DOI only when a DOI marker binds a number outside every parsed identifier.
A plan review showed the class of references that therefore emit is wider than the first wording (a bare markerless `10/…` beside a verified DOI): it also holds a bare unparseable `10.NNN/…` and a marker followed by a word and then a number (`doi:<DOI>; DOI pending 10/fake`).
The lane had to accept the whole class, narrow it, or give up the fix.

## Decision

The accepted class is stated as the exact complement of binding: with at least one parsed DOI present, any `10.` or `10/` number outside every parsed identifier that is not bound by a marker, through the marker's own whitespace-free token plus a run of non-alphanumeric characters, emits.
Its three fabricated shapes, one example each, all beside a parsed DOI: `doi:<DOI> and 10/fake`; `doi:<DOI> and 10.123/fake`; `doi:<DOI>; DOI pending 10/fake`.
After [0134](0134-doi-lane-rulings-after-round-1.md), "alphanumeric" in the walk means a Unicode letter or digit, so a word in any script stops a walk (`doi: <DOI> doi: é10/abcfake` emits).

Reason: the class cannot be excluded without re-breaking the case this lane exists to fix; the third shape is the same shape as `Title mentions DOI; pages 10. Registered reference: <DOI>`, a clean reference.
With no parsed DOI the path is unchanged and every shape above still refuses, so the class opens only beside a DOI that is itself resolved against Crossref and the DOI handle API.
This supersedes the narrower wording the lane accepted earlier the same day under the same delegation (a bare `10/` beside a verified DOI only); that acceptance is not cited as covering this class.

## What this does not close

- A fabricated DOI in the accepted class is not caught; detecting unmarked or word-separated DOI claims would need a different signal than adjacency (for example a registry lookup of every `10.NNNN/` token), which no lane has specified.
- The residuals [0131](0131-doi-unbound-number-beside-verified-doi.md) names.

## Test

The lane's differential sweep ([0131](0131-doi-unbound-number-beside-verified-doi.md)) classifies every changed outcome with an independent oracle; any flip outside this class counts as `other`, and the recorded run has `other 0`.
`EmitReportTests.test_doi_fabricated_beside_verified` pins the bound side (every generated separator form beside the real DOI refuses); the emitting cases beside the real DOI pin the unbound side.

## Status

Standing. A lane ruling under the owner's delegation; the protected-change approval is [0132](0132-doi-lane-delegated-approval-of-protected-changes.md).

## Date

2026-09-25
