# DOI false-refusal lane: change report

Written by Glitch under the owner's standing delegation of 23 September 2026; no sentence in this report is the owner's.
The lane closes the fail-closed false refusal [0103](../decisions/0103-row-8-seals-and-sealed-measurement.md) carried from row 8 step A.
Its decisions are [0130](../decisions/0130-doi-marker-binds-its-number.md) (the rule), [0131](../decisions/0131-doi-unbound-number-beside-verified-doi.md) (the measured change of outcome and the residuals), [0133](../decisions/0133-doi-lane-ruling-unbound-number-class.md) and [0134](../decisions/0134-doi-lane-rulings-after-round-1.md) (lane rulings), and [0132](../decisions/0132-doi-lane-delegated-approval-of-protected-changes.md) (the approval).
The producer's own evidence, round by round, is the [build log](doi_false_refusal_build_log.md); this report is the lane's account of it.
Everything here is development evidence; nothing changes a catch-rate cell.

## How it was built

Base: public main `ef5c8af`.
Producer: Codex, one unprivileged OS account; reviewers: fresh-context Claude Opus 5.5, a second, separate unprivileged OS account; an unattended queue runner between them.

| Round | Commit(s) | Review | Verdict |
|---|---|---|---|
| 1 | `ead7645` (tests, red first), `78fe7f8` (fix), `31e48da` (mutation proof) | round 1 | APPROVE, five NOTEs |
| B1 | `40941de` (ruling 0134; review 1's NOTEs) | round B1 | APPROVE WITH CHANGES, one MINOR, two NOTEs |
| C1 | `c047cf6` (review B1's MINOR) | round C1 | APPROVE, one NOTE |

Every commit is authored and committed under the repository's own identity; every producer and reviewer session's path scan read 0 hits.

## Requirement → change → acceptance test → result

| Requirement | Changed files | Acceptance test | Result (red-on-fault seen) |
|---|---|---|---|
| A clean reference with a registered DOI and an ordinary `10.`/`10/` elsewhere emits (0103's residual; R-125's DOI half) | `gars/_system/resolve_citation.py`, `gars/tests/test_emit_report.py` | `EmitReportTests.test_doi_clean_reference_corpus` | red at `ef5c8af`'s resolver with the lane's tests in place (`FAILED (failures=928)`), green at `c047cf6`; yes: `own prefix not consumed`, `identifier path falls back to the anywhere rule`, `separator walk crosses letters`, `bound number inside a parsed identifier counted`, `markers inside a parsed identifier counted`, `separator walks use ASCII alphanumerics` |
| Every fabricated form the base refused still refuses, alone and beside a verified DOI | `gars/tests/test_emit_report.py` | `EmitReportTests.test_doi_fabricated_beside_verified`, `EmitReportTests.test_doi_reference_forms` | green at both (a guard: the base refused every form too); yes: `every bound number satisfied`, `chaining removed`, `new rule applied on the no-identifier path` |
| A BibTeX `doi = {…},` field resolves the bare DOI | `gars/_system/resolve_citation.py` | the brace closer cases in `test_doi_reference_forms` and the corpus | yes: `brace removed from the closer set`, `unmatched DOI closing bracket retained` |
| The marker set is not widened, and its two copies cannot drift | `gars/tests/test_citation_resolution.py` | `CitationResolutionTests.test_marker_pattern_constant` | green |
| The no-identifier path and the inherited lines of `mentions_doi` are unchanged | `gars/_system/resolve_citation.py` | range check over lines 42-59 at `ef5c8af`; the no-identifier refusals in `test_doi_reference_forms` | `lines 18, present in order 18`, one inserted line (`if identifiers: return _has_unbound_doi_number(reference)`); yes: `malformed DOI marker ignored`, `author Doi treated as DOI marker`, `short-form DOI marker ignored` |
| The mutation campaign runs to its end (0103's stale anchor) | `benchmarks/defects/red_on_fault.py` | the campaign | `red-on-fault: 53/53`, 28 DOI and evidence anchors each found exactly once (43 inherited, three re-anchored and one kept; ten added) |
| No outcome changes outside the accepted class | none | the differential sweep (0131) | `cases 427764, flips 86453 (in class 22014, BibTeX 64439, other 0)`; `dois()` differences only a trailing unmatched `}` dropped (84932) |

## Expectation changes

| Test | Old | New | Reason |
|---|---|---|---|
| `EmitReportTests.test_doi_reference_forms`, residual-prose control with a DOI (title) | refuse `citation_unverifiable`, two recorded requests | emit, exactly one recorded request | 0130: the page number is not bound by a marker; restores ruling 7's clean control (0103) |
| `EmitReportTests.test_doi_reference_forms`, residual-prose control with a DOI (journal) | refuse `citation_unverifiable`, two recorded requests | emit, exactly one recorded request | the same |
| `README.md` and `DEVELOPMENT.md` suite counts | 533 (lane branch); 612 (merge) | 536 (lane branch); 615 (merge) | three new test methods; on the lane branch a collection count only (review 1 F4); at the merge, README's 13-skip figure is the merge candidate's macOS run below |
| Round B1's three non-ASCII-letter guard cases (added and moved inside the lane) | refuse (round B1) | emit beside the real DOI (round C1) | 0134 ruling 2: a word in any script stops a walk |

The producer's own table cites line numbers that the round B1 comment line moved by one (review B1 F3); the tests are named here instead.

## Evidence (Glitch, each run alone on its machine)

On the build node's owner account (not an agent account), from a bundle of the lane branch in a fresh folder outside every agent account, solo on the host (2026-09-25 01:04:37 to 01:20:36 America/New_York; Python 3.13.5; no container runtime used), at `c047cf6`:

- `python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_clean_reference_corpus` with `ef5c8af`'s resolver put in place: `FAILED (failures=928)`; `EmitReportTests.test_doi_fabricated_beside_verified` there: `OK`.
- `python3 -u gars/tests/test_emit_report.py`: `Ran 12 tests`, `OK`; `python3 -u gars/tests/test_citation_resolution.py`: `Ran 6 tests`, `OK (skipped=1)` (the live DOI test).
- `GARS_TEST_NO_CONTAINER=1 python3 -u tests/run_tests.py` with `TMPDIR`, `TEMP` and `TMP` set: `Ran 536 tests`, `OK (skipped=79)`; with `TMPDIR` unset and `TEMP`/`TMP` set: `Ran 536 tests`, `OK (skipped=106)`.
- `python3 tests/check_contracts.py`: `14 contracts clean: sections, wait points, vocabulary.`; `python3 tests/check_counts.py`: `clean — every current claim matches the suite`; `python3 tests/test_decision_links_resolve.py`: `citations: 301/301 resolve`.
- `python3 -u tests/test_planted_defects.py DevelopmentCatalogueTests`: `false flags (producer-authored clean projects): 0/10`, `graded 19 of 19 development projects seen`, `OK`.
- `python3 -u benchmarks/defects/red_on_fault.py`: 53 `RED` lines, `red-on-fault: 53/53`.
- The range check and the differential sweep above; the differential's output file hashes `61682abfe8c1dddff9411df3cd1971c5166e2ea1bf92978ce063d2895ee3ce05`.
- The clone was clean afterwards; the mode with `TMPDIR` set left three `gars-mutation-logs-*` folders in its own temp folder, which an earlier lane's run on the same host also shows (not a change made here).

At the merge candidate `3b189bc` (the lane merged with `--no-ff` onto public main `ba31539`, after row 6 and row 9's cd-placement follow-up; the only conflicts were the suite-count claims, resolved to 612 + 3 = 615; `.github/workflows` is identical between `ef5c8af` and `ba31539`, and CI and Fresh clone were green on `ba31539` before the push):

- On the owner's workstation, alone under the lane's reservation, with Docker answering and row 5's scratch folder set as CI sets it (2026-09-25 03:35:58 to 04:21:04; macOS, Python 3.8.2, Docker 20.10.10 with 9.7 GiB and 8 CPUs): `python3 -u tests/run_tests.py`: `Ran 615 tests`, `OK (skipped=13)`; containers and volumes unchanged; the clone clean afterwards.
  One caveat, named: a process `python3 tests/run_tests.py` not started by this run (another session's) was seen once at 04:15:09 and was gone 30 seconds later; the run's result is the one expected.
  An earlier run at `c047cf6` without row 5's scratch folder (the cold-clone shape) read `Ran 536 tests`, `OK (skipped=75)`.
- On the build node's owner account (not an agent account), from a bundle of the candidate, alone (03:56:29 to 04:13:15; process snapshots at the start, between the modes, after them and at the end show no other test run on any account): `GARS_TEST_NO_CONTAINER=1 python3 -u tests/run_tests.py` with `TMPDIR` set: `Ran 615 tests`, `OK (skipped=79)`; with `TMPDIR` unset: `Ran 615 tests`, `OK (skipped=106)`; contracts clean; counts clean; `citations: 347/347 resolve`; `false flags (producer-authored clean projects): 0/10`; `gars/tests/test_emit_report.py` `Ran 12 tests`, `OK`.

## Hours

About six hours of wall clock from the kit (22:30, 24 September 2026) to the landing (about 04:30, 25 September), about half of it waiting on other lanes' landings and machines; producer and reviewer time on subscriptions, $0 metered.

## Residual gaps, each NOT met

- The accepted class of [0133](../decisions/0133-doi-lane-ruling-unbound-number-class.md): with a parsed DOI present, a fabricated `10.`/`10/` number no marker binds emits.
- 0103's same-DOI-shape spellings, and a bare `10/…` with no marker.
- Fail-closed false refusals left in place: a number joined to a verified DOI by punctuation or spaces alone chains and refuses (a bare date right after a URL-form DOI included); a marker's own token continues through letters.
- `doi:pending` beside a real DOI emits; a second explicit malformed marker beside a real DOI is not refused.
- No committed test pins the ASCII leading number boundary beside a verified DOI (review C1's NOTE): a later lane adds one glued case, such as the real DOI beside `doi:` + `é10/abcfake`, to `test_doi_fabricated_beside_verified`.
- The inherited comment above the residual-prose block still describes the old refusal; one added line after it names 0130 and 0131.
- Execution on Python 3.6.8 and on the cluster; live DOI resolution; PMID and the literature role's wiring of R-125; emission other than through `emit_report.py`.

## Owner rulings needed

None.
