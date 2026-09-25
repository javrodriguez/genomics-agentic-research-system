# DOI false-refusal build log

This is producer build evidence for the delegated DOI lane, not a decision record or approval.
Glitch writes the decision records and change report under the supplied delegation.
The starting production commit is `ef5c8af47553ef590070cab535c8d848141b7c79`.
All Python commands set `TMPDIR`, `TEMP` and `TMP` to the job scratch twin `../gars-doilane-scratch`.
Replay responses are synthetic protocol fixtures and establish protocol behavior only.

## Red-first evidence

Stage 1 is `ead7645`, containing only tests and the count claims required by those tests.
Production remained byte-identical to `ef5c8af` at that commit.
`python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_clean_reference_corpus` printed `Ran 1 test in 1.593s` and `FAILED (failures=921)` at stage 1.
`python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_fabricated_beside_verified` printed `Ran 1 test in 0.601s` and `OK` at stage 1.
With the fix, the same clean-corpus command printed `Ran 1 test in 24.029s` and `OK`.
With the fix, the same guard command printed `Ran 1 test in 0.623s` and `OK`.
The clean corpus covers five citation styles, eight DOI forms, four ordinary numeric contexts in both positions, and author/title Doi variants, plus internal-marker suffixes with a recording 200-ok transport.
The shared separator generator retains all 392 generated forms in the original no-identifier sweep and tests each beside the recorded real DOI in both orders, with chained-list guards.
Unmatched brace cases and balanced braces in suffixes extend the existing closer guards.
The marker-constant test reads the inherited literal pattern line with `inspect.getsource`.

## Expectation changes

| Test | File and line | Old | New | Reason |
|---|---|---|---|---|
| `test_doi_reference_forms`, title residual with DOI | `gars/tests/test_emit_report.py:145` | `citation_unverifiable`, two Crossref requests through refusal checks | Emit, exactly one recorded Crossref request | Title prose separates the marker from the page number; the registered DOI resolves |
| `test_doi_reference_forms`, journal residual with DOI | `gars/tests/test_emit_report.py:145` | `citation_unverifiable`, two Crossref requests through refusal checks | Emit, exactly one recorded Crossref request | Journal prose separates the marker from the page number; the registered DOI resolves |
| Count guard, current suite claim | `README.md:322` | 533 | 536 | Three new test methods |
| Count guard, current suite claim | `DEVELOPMENT.md:148` | 533 | 536 | Three new test methods |
| Count guard, runner count | `DEVELOPMENT.md:167` | 533 | 536 | Three new test methods |

The no-DOI half of both residual-prose controls remains unchanged and refuses.
The count edits update the current collection count only; inherited host measurements are not new measurements in this lane.

## Structural verification

`inherited mentions_doi and resolve: byte-identical; DOI regex and legacy predicate: unique`
The comparison removes only the inserted early-return line from `mentions_doi` before comparing it with the base.

## Gate evidence

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py` (one suite at a time; database classes skipped, verified elsewhere).
```text
collected 283 tests from tests
collected 253 tests from gars/tests
Ran 536 tests in 386.397s
OK (skipped=79)
```
`python3 tests/check_contracts.py`.
```text
14 contracts clean: sections, wait points, vocabulary.
```
`python3 tests/check_counts.py`.
```text
suite: 536 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```
`git diff --stat ef5c8af -- gars/_system/claims .github evals docs/decisions` printed nothing.

## What was not verified

No live network DOI resolution or capture was run.
No spent sealed catalogue measurement was run or promoted.
Actual execution on Python 3.6 and cluster execution remain unverified here.
Database classes are excluded by the requested gate and are verified elsewhere.
The broader short-DOI spellings, PMID/literature wiring, relevance checking, stage-03/pilot emission wiring, public catch-rate claims, and other residuals in 0103 remain outside this lane.
Independent review, protected-change approval, and merge remain outstanding.

## Owner rulings needed

None.
