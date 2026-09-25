---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/resolve_citation.py
  - gars/tests/test_emit_report.py
  - gars/tests/test_citation_resolution.py
  - benchmarks/defects/red_on_fault.py
  - docs/ledger.csv
  - docs/implementation/doi_false_refusal_change_report.md
symptoms:
  - a clean reference with a registered DOI and an ordinary 10. or 10/ elsewhere (Epub date, volume, pages, access date) is refused citation_unverifiable
  - a BibTeX doi = {10.x/y}, field resolves the identifier with its closing brace and is refused citation_unresolved
---
# A DOI marker binds the number it points at

Addendum to [0101](0101-row-8-defect-catalogue-and-detectors.md) and [0103](0103-row-8-seals-and-sealed-measurement.md), which stay byte-identical.
Decided and recorded by Glitch under the owner's standing delegation of 23 September 2026; no sentence in this record is the owner's.

## Context

Row 8 step A's residual-text rule (`mentions_doi` at `ef5c8af`) removes every parsed DOI from an evidence reference, then refuses `citation_unverifiable` when a `doi` marker and any `10.` or `10/` token remain anywhere.
It fails closed on clean references, because the marker left behind is usually the removed DOI's own prefix (`doi:`, `https://doi.org/`) and ordinary bibliographic numbers then supply the numeric token: `Smith J. Nature. 2011;472:1-5. doi: <DOI>. Epub 2011 Apr 10.` was refused.
Row 8's final review raised it (F1, MINOR), and 0103 carried it as a named residual that must close before a real pilot report is rendered.
Separately, `dois()` stripped an unmatched `)` or `]` but kept an unmatched `}`, so a BibTeX `doi = {<DOI>},` field was looked up with the brace and refused `citation_unresolved`.

## Decision

One general rule: a DOI marker claims the number it points at.

1. **Binding.** A marker (the pattern row 8 already uses, unchanged, now also the module constant `MARKER_PATTERN`) binds the first `10.` or `10/` number reached from the marker's end through the rest of the marker's own whitespace-free token and then a run of characters that are not Unicode letters or digits ([0134](0134-doi-lane-rulings-after-round-1.md) ruling 2; the marker and the number's leading boundary stay ASCII); the number's leading boundary is evaluated on the text after the marker, so the attached `DOI10/x` form still binds.
   A marker whose match starts inside a parsed identifier is ignored, as the base, which removed identifiers first, never saw it.
2. **Chaining.** When a bound number lies inside a parsed identifier, the walk continues from that identifier's end across characters that are not Unicode letters or digits only, and a number reached that way is also bound (a DOI list after one marker).
3. **Own identifier satisfied.** A bound number that lies inside a parsed identifier, at its start or anywhere within its span, is satisfied: the marker was that DOI's own prefix ([0134](0134-doi-lane-rulings-after-round-1.md) widened this from the start only).
4. **Refusal.** With at least one parsed identifier, a reference refuses `citation_unverifiable` only when some marker binds a number outside every parsed identifier.
5. **No-identifier path unchanged, by construction.** When `dois()` parses nothing, `mentions_doi` returns exactly what it returned at `ef5c8af`: one early return is inserted after `identifiers = dois(reference)`, and every inherited line of the function stays present verbatim, in order, at its indentation.
6. **Unmatched `}`.** `dois()` strips a trailing `}` exactly as it strips `)` and `]`: only when the identifier holds more `}` than `{`.

The DOI regular expression now lives once, in `DOI_PATTERN`, used only by the span helper `_doi_spans`, from which `dois()` is derived, so the identifier list and the spans cannot drift.
The rule is structural (adjacency over one character class and span identity against parsed identifiers); it enumerates no separator, citation style or date format, and the marker pattern is not widened.

Why not apply adjacency with no parsed identifier as well: that would flip four refusals the suite asserts (a title or journal mentioning DOI with a page number and no identifier, a number before the marker, and the no-DOI half of the residual-prose controls); with nothing registered to verify, the fail-closed floor there costs no clean reference that has a DOI.

## What this does not close

- The class [0131](0131-doi-unbound-number-beside-verified-doi.md) accepts: with a parsed DOI present, a `10.` or `10/` number that no marker binds emits.
- 0103's same-DOI-shape spellings (`DOIs: 10/…`, `shortdoi 10/…`, `D.O.I. 10/…`, percent-encoded, `doi 10 / …`), and a bare `10/…` with no marker.
- The fail-closed residuals 0131 names (a number joined to a verified DOI by punctuation or spaces alone chains and refuses, a bare date after a URL-form DOI included; a marker's own token continues through letters).
- PMID and the literature role's wiring of R-125, relevance of a real DOI, and report emission other than through `emit_report.py`.
- Execution on Python 3.6.8 and on the cluster; live DOI resolution (the recorded replay is the test surface).

## Test

- `gars/tests/test_emit_report.py` `EmitReportTests.test_doi_clean_reference_corpus`: PubMed/NLM, Vancouver, APA 7, BibTeX and Harvard shells, each DOI form, the four ordinary numbers before and after the DOI, author and title words `Doi`, internal-marker suffixes and 0134's glued case, each emitting with its exact Crossref request list; red with `ef5c8af`'s resolver in place (`FAILED (failures=928)` with the lane's final tests).
- `EmitReportTests.test_doi_fabricated_beside_verified`: the 392 generated separator forms beside the recorded real DOI in both orders, and chained lists, each refusing; green with `ef5c8af`'s resolver too (a guard).
- `EmitReportTests.test_doi_reference_forms`: every no-identifier refusal unchanged; the residual-prose controls' with-DOI half now emits with exactly one recorded request.
- `gars/tests/test_citation_resolution.py` `test_marker_pattern_constant`: the literal `pattern` line inside `mentions_doi` equals `MARKER_PATTERN`.
- `benchmarks/defects/red_on_fault.py`: 43 inherited faults (three DOI anchors re-anchored, one kept) plus ten new ones, each red on its named test; `red-on-fault: 53/53`.

## Status

Standing. Implementation of the rule; the protected-change approval is [0132](0132-doi-lane-delegated-approval-of-protected-changes.md).

## Date

2026-09-25
