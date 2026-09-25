---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/resolve_citation.py
  - gars/tests/test_emit_report.py
  - gars/tests/test_citation_resolution.py
symptoms:
  - the DOI false-refusal lane changes code and tests under the protected prefix gars/ with no owner approval record
---
# DOI false-refusal lane: approval of its protected changes, under the owner's delegation

Addendum to [0130](0130-doi-marker-binds-its-number.md), which stays byte-identical.
Every path this record touches is under a protected prefix (§9.3, R-094), so its change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows row 8's [0104](0104-row-8-delegated-approval-of-protected-changes.md).

## Context

The lane closes the fail-closed false refusal [0103](0103-row-8-seals-and-sealed-measurement.md) carried from row 8 step A: a clean reference with a registered DOI and an ordinary `10.` or `10/` elsewhere was refused `citation_unverifiable`, and a BibTeX `doi = {…},` field was refused `citation_unresolved`.
It was built on its own branch from public main `ef5c8af` by a producer (Codex) running as one unprivileged OS account, and reviewed by fresh-context reviewers (Claude Opus 5.5) running as a second, separate unprivileged OS account on the same node, through an unattended queue runner.
Every decision in its specification is labelled in 0130, 0131, 0133 and 0134 as the lane's, under the owner's delegation.
The lane took five producer commits, `ead7645` to `c047cf6`, each authored and committed under the repository's own identity.
Reviews: round 1 APPROVE (five NOTEs), round B1 APPROVE WITH CHANGES (one MINOR, caused by the lane's own continuation-B ruling, and two NOTEs), and round C1 APPROVE (one NOTE, carried in 0131 as a residual).
The final review's SHA-256 is `f9e459e47f412a196a0f15882dd655811fc24637f0daf2c5c70e75162d15193a`; every review of the lane is kept outside the repository.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected changes as merged, on 2026-09-25.

1. **`gars/_system/resolve_citation.py`**: the DOI regular expression moved once into `DOI_PATTERN`, used only by the span helper `_doi_spans`, from which `dois()` is derived; `MARKER_PATTERN`, `UNICODE_ALNUM_PATTERN` and `_has_unbound_doi_number` implement 0130's binding rule as 0134 reads it; `dois()` strips an unmatched trailing `}`; `mentions_doi` gains one early return for the parsed-identifier path, and every inherited line of it stays verbatim, in order; `resolve()`, `doi()`, the live transport and the command line are unchanged.
2. **`gars/tests/test_emit_report.py`**: the clean-reference corpus, the fabricated-beside-verified guard with the shared 392-form generator, the brace closer cases, and the residual-prose controls' with-DOI half changed from refuse to emit (the expectation change 0131 records).
3. **`gars/tests/test_citation_resolution.py`**: the marker-constant test.

Outside the protected prefix, and recorded here for completeness: `benchmarks/defects/red_on_fault.py` (three DOI anchors re-anchored, one kept, ten faults added), the suite count in `README.md` and `DEVELOPMENT.md` (533 to 536 on the lane branch, a collection count only, review 1 F4; 612 to 615 at the merge, where README's skip figure is the merge candidate's macOS run in the change report), and the producer's build log `docs/implementation/doi_false_refusal_build_log.md`.

## What this does not close

- Every residual [0131](0131-doi-unbound-number-beside-verified-doi.md) names, the accepted class of [0133](0133-doi-lane-ruling-unbound-number-class.md) among them.
- PMID and the literature role's wiring of R-125; report emission other than through `emit_report.py`.
- Execution on Python 3.6.8 and on the cluster; live DOI resolution.

## Test

Glitch verified the lane independently on the owner's workstation and on the build node's owner account, each evidence run alone on its machine; the lines are in the lane's [change report](../implementation/doi_false_refusal_change_report.md).

## Status

Standing. Approval of the lane's protected changes only.

## Date

2026-09-25
