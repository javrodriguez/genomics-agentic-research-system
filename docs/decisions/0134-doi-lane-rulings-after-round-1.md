---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/resolve_citation.py
  - gars/tests/test_emit_report.py
  - benchmarks/defects/red_on_fault.py
symptoms:
  - a verified DOI glued to a preceding word inside a marker's token, whose suffix carries -10., is refused citation_unverifiable
  - a clean reference written in a non-Latin script (a Russian, Chinese, Japanese or Greek access date or page range after the DOI) is refused citation_unverifiable
---
# DOI lane rulings after round 1: a number inside an identifier is satisfied, and the walk's letters are Unicode

Addendum to [0130](0130-doi-marker-binds-its-number.md), which stays byte-identical.
Lane rulings, decided and recorded by Glitch under the owner's standing delegation of 23 September 2026; no sentence in this record is the owner's.
This is the number the lane's plan held for a fix-round or stop-and-rule outcome.

## Context

The plan's rule, as first specified, satisfied a bound number only when it was the start of a parsed identifier.
Before the producer's first round finished, Glitch ran the lane's differential sweep over a prototype of that rule and found one class of changed outcome outside the accepted class: 242 references the base emitted and the rule refused, all one shape, a verified DOI glued to a preceding word inside a marker's own token (`doi:doi10.1000.10/synthetic-doi-10.5`).
The walk cannot bind the identifier's own start (a letter precedes it), so it binds the `-10.` inside the identifier's suffix, which is not a span start; the producer's round 1 behaved exactly as the prototype (the sweep outputs are byte-identical).
Round 1's independent review approved it with five NOTEs, one of which (F2) observed that the walks used Unicode `str.isalnum()` while the number boundary uses ASCII; the lane first ruled the walks ASCII (round B1), and round B1's review then showed that the ASCII class refuses clean references written in non-Latin scripts again (MINOR F1), which round 1 had emitted.

## Decision

1. **A number inside an identifier is satisfied.** A bound number that lies inside a parsed identifier, at its start or anywhere within its span, is satisfied, and chaining continues from that identifier's end (0130 items 2 and 3 read this way). The reason is item 1's own: the base never saw anything inside a removed identifier, a marker or a number.
2. **The walk's alphanumeric class is Unicode letters and digits** (the regular-expression class `[^\W_]`), in both the separator walk after a marker's token and the chaining walk after an identifier, so a word in any script stops a walk. The marker pattern and every number's leading boundary stay ASCII, exactly as row 8 wrote them. The round B1 ASCII ruling is withdrawn; its three non-ASCII-letter guard cases now assert emission beside the real DOI (the accepted class of [0133](0133-doi-lane-ruling-unbound-number-class.md)).
3. **A second fix round.** The lane's plan allowed one fix round, after which remaining MINORs become named residuals; the lane ran a second (round C1) because the MINOR was introduced by the lane's own ruling and re-created the false-refusal class the lane closes, and its fix was one character class.

## What this does not close

- The residuals [0131](0131-doi-unbound-number-beside-verified-doi.md) names.
- A letter in any script now stops a walk, so a fabricated number glued to a non-Latin letter after a marker (`doi: é10/abcfake`) emits beside a verified DOI, inside the accepted class.

## Test

- Ruling 1: a clean-corpus case (`doi:doi` + `10.1000.10/synthetic-doi-10.5`, resolved by the 200-ok recording transport) emits with its exact request list, red at round 1's head; its twin with ` 10/fake` after the identifier refuses; the fault `bound number inside a parsed identifier counted` turns it red.
- Ruling 2: review B1's four non-Latin clean references emit with their exact request lists, red at round B1's head; the fault `separator walks use ASCII alphanumerics` turns the clean corpus red.
- The differential sweep over the final head reads `other 0` ([0131](0131-doi-unbound-number-beside-verified-doi.md)).

## Status

Standing. Lane rulings under the owner's delegation; the protected-change approval is [0132](0132-doi-lane-delegated-approval-of-protected-changes.md).

## Date

2026-09-25
