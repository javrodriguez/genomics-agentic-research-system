---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/resolve_citation.py
  - gars/tests/test_emit_report.py
symptoms:
  - a reference that 0103's rule refused now emits because the 10. or 10/ number in it is not bound by a DOI marker
---
# DOI lane: the one expected change of outcome, measured, and the residuals

Addendum to [0130](0130-doi-marker-binds-its-number.md) and [0103](0103-row-8-seals-and-sealed-measurement.md), which stay byte-identical.
Decided and recorded by Glitch under the owner's standing delegation of 23 September 2026; no sentence in this record is the owner's.

## Context

0130 changes which references refuse `citation_unverifiable`.
Its purpose is a set of changes from refuse to emit (clean references with a registered DOI); the risk is any other change, above all a fabricated DOI that used to refuse and now emits.
This record states the accepted class, measures every changed outcome against it, and names what stays open.

## Decision

The accepted class, ruled in [0133](0133-doi-lane-ruling-unbound-number-class.md) as the exact complement of binding: with at least one parsed DOI present, any `10.` or `10/` number outside every parsed identifier that is not bound by a marker, through the marker's own whitespace-free token plus a run of non-alphanumeric characters (after [0134](0134-doi-lane-rulings-after-round-1.md), alphanumeric means a Unicode letter or digit), emits.
One example of each fabricated shape it holds, beside `doi:10.1038/x`: `doi:10.1038/x and 10/fake`; `doi:10.1038/x and 10.123/fake`; `doi:10.1038/x; DOI pending 10/fake`.

0103's bare-`10/` residual is re-stated to cover it: a bare `10/…` or unparseable `10.NNN/…` with no marker bound to it is not checked, alone or beside a verified DOI.
0103's line naming the clean-reference false refusal (a registered DOI with an ordinary `10.` or `10/` elsewhere) is closed by 0130, and the two ruling 7 clean controls the row 8 producer flipped to must-refuse are restored: their with-DOI half emits with exactly one recorded Crossref request; the no-DOI half still refuses.

### The measurement (development evidence)

A differential sweep, a stdlib script kept outside the repository, loads `gars/_system/resolve_citation.py` at `ef5c8af` and at the lane's head `c047cf6` as two modules and compares the verdict each gives the emitter, `refuse(r) = mentions_doi(r) or any(i not in RESOLVABLE for i in dois(r))`, with `RESOLVABLE` the recorded real DOI and the synthetic `10.1000.10/synthetic-doi-10.5`.
Its corpus is an exhaustive small grammar: fifteen tokens (`doi`, `DOI`, `doi:`, `DOI-`, `doi_`, `x_doi=`, `https://doi.org/`, `pages`, `Doi`, `10/fake`, `10.123/fake`, `10.`, the real DOI, the real DOI with a trailing `}`, the synthetic DOI) and six joiners (none, space, `; `, `, `, newline, ` = {`), every sequence of one to three tokens with every joiner in every gap, every sequence of four tokens with one joiner repeated, then the 392 generated separator forms alone and beside the real DOI, row 8's review references, the lane's clean shapes, and seven non-Latin or non-ASCII-letter references.
Every change from refuse to emit is classified by an oracle that shares no code with the head: it is in class only if deleting every `10.` or `10/` token outside the base's parsed identifiers (a token stops where a parsed identifier starts) makes the base emit, and no deleted token lies in, or only non-alphanumeric characters away from, a marker's whitespace-free token on its left.
A change whose parsed identifiers differ between base and head is counted as BibTeX; every such difference must be a trailing unmatched `}` dropped.
Everything else, including every change from emit to refuse, is `other`.

The recorded run at `c047cf6`:

```
cases 427764, flips 86453 (in class 22014, BibTeX 64439, other 0)
dois() differences: brace 84932
61682abfe8c1dddff9411df3cd1971c5166e2ea1bf92978ce063d2895ee3ce05  (sha256 of the sweep's output file)
```

The same sweep over the rule as first specified found 242 changes from emit to refuse outside the class; they are the subject of 0134's first ruling, and the output at round 1's head was byte-identical to a prototype of that rule's.

## What this does not close

- The accepted class above: a fabricated DOI in it is not caught.
- 0103's same-DOI-shape spellings (`DOIs: 10/…`, `shortdoi 10/…`, `D.O.I. 10/…`, a percent-encoded `doi%3A10%2F…`, `doi 10 / …`).
- Fail-closed residuals, each a false refusal the lane leaves in place:
  - a number joined to a verified DOI by punctuation or spaces alone is chained and refuses (`doi:10.1038/x, 10/03/2020` with no word between; a bare date right after a URL-form DOI, round 1 review F1);
  - a marker's own whitespace-free token continues through letters, so `Journal of Doi-Studies 10.` binds and refuses.
- `doi:pending` beside a real DOI emits (the lane's ruling 3); a second explicit malformed marker beside a real DOI is not refused.
- The sweep's grammar is small by design; it is development evidence, not a sealed measurement, and nothing here changes a catch-rate cell.

## Test

The sweep above (outside the repository, re-runnable from its recorded command), and the committed tests 0130 names.

## Status

Standing. Records a measured change of outcome and the lane's residuals; the rulings are [0133](0133-doi-lane-ruling-unbound-number-class.md) and [0134](0134-doi-lane-rulings-after-round-1.md); the approval is [0132](0132-doi-lane-delegated-approval-of-protected-changes.md).

## Date

2026-09-25
