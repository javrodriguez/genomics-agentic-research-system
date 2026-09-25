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

Stage 2 is `78fe7f8`, containing the production fix and the build log.

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

## Mutation proof

Stage 3 retains every inherited fault, repairs the three specified anchors, leaves the subdivision anchor unchanged, and adds the eight specified faults.
`TMPDIR=<the job's scratch folder> python3 -u benchmarks/defects/red_on_fault.py` used the scratch twin named above, with `TEMP` and `TMP` set there as well.
Before creating the disposable twin, the campaign printed `source.count(old)` for every DOI or EVIDENCE fault and required exactly 1 for each.
The complete printed counts and per-fault results follow.

```text
anchor count: evidence hash not compared: 1
anchor count: absolute evidence accepted: 1
anchor count: Crossref 404 alone unresolved: 1
anchor count: network error resolved: 1
anchor count: environment replay switch: 1
anchor count: suppressed replay option: 1
anchor count: DOI tokens restricted to whole reference: 1
anchor count: malformed DOI marker ignored: 1
anchor count: malformed evidence accepted: 1
anchor count: subdivided DOI prefix ignored: 1
anchor count: unmatched DOI closing bracket retained: 1
anchor count: author Doi treated as DOI marker: 1
anchor count: short-form DOI marker ignored: 1
anchor count: noninteger evidence id accepted: 1
anchor count: arbitrary evidence kind accepted: 1
anchor count: arbitrary evidence relation accepted: 1
anchor count: extra evidence keys accepted: 1
anchor count: extra evidence parent keys accepted: 1
anchor count: own prefix not consumed: 1
anchor count: identifier path falls back to the anywhere rule: 1
anchor count: every bound number satisfied: 1
anchor count: chaining removed: 1
anchor count: separator walk crosses letters: 1
anchor count: new rule applied on the no-identifier path: 1
anchor count: brace removed from the closer set: 1
anchor count: markers inside a parsed identifier counted: 1
RED: sex confounding removed
RED: imbalance threshold 0.9
RED: cell pseudoreplication removed
RED: subject count removed
RED: index comparison inverted
RED: not_checkable counted pass
RED: evidence hash not compared
RED: absolute evidence accepted
RED: padj below pvalue allowed
RED: BH recompute removed
RED: Crossref 404 alone unresolved
RED: network error resolved
RED: unparseable plant skipped
RED: unmapped folded into class
RED: Hi-C denominator removed
RED: truncated plain FASTQ passes
RED: gzip-valid record truncation passes
RED: report written before preflight
RED: sealed stdout leaked
RED: invalid_design mapped without family
RED: BH tolerance 1e-6
RED: environment replay switch
RED: suppressed replay option
RED: DOI tokens restricted to whole reference
RED: malformed DOI marker ignored
RED: malformed evidence accepted
RED: subdivided DOI prefix ignored
RED: unmatched DOI closing bracket retained
RED: author Doi treated as DOI marker
RED: short-form DOI marker ignored
RED: noninteger evidence id accepted
RED: arbitrary evidence kind accepted
RED: arbitrary evidence relation accepted
RED: extra evidence keys accepted
RED: extra evidence parent keys accepted
RED: erroring clean plant counted clean
RED: padj without pvalue allowed
RED: invalid sex treated unknown
RED: invalid age allowed
RED: class 2 detail ignored
RED: class 3 detail ignored
RED: graded verdict dropped
RED: renderer receives from-db
RED: own prefix not consumed
RED: identifier path falls back to the anywhere rule
RED: every bound number satisfied
RED: chaining removed
RED: separator walk crosses letters
RED: new rule applied on the no-identifier path
RED: brace removed from the closer set
RED: markers inside a parsed identifier counted
red-on-fault: 51/51
```

`python3 -u tests/test_planted_defects.py DevelopmentCatalogueTests`.
```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
Ran 13 tests in 4.384s
OK
```
`python3 -c "import ast,sys; [ast.parse(open(p).read(), feature_version=(3, 6)) for p in sys.argv[1:]]; print('parsed', len(sys.argv) - 1)" gars/_system/resolve_citation.py gars/tests/test_emit_report.py gars/tests/test_citation_resolution.py benchmarks/defects/red_on_fault.py` covered every changed Python file.
```text
parsed 4
```
The final stage changes only the mutation driver and this log; production and test bytes remain those verified by the full gate.

## Final-commit evidence

At the final stage commit, `python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_clean_reference_corpus` has summary `OK` (one test).
At the final stage commit, `python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_fabricated_beside_verified` has summary `OK` (one test).
`git diff --stat ef5c8af -- gars/_system/claims .github evals docs/decisions` printed nothing again.

## What was not verified

No live network DOI resolution or capture was run.
No spent sealed catalogue measurement was run or promoted.
Actual execution on Python 3.6 and cluster execution remain unverified here.
Database classes are excluded by the requested gate and are verified elsewhere.
The broader short-DOI spellings, PMID/literature wiring, relevance checking, stage-03/pilot emission wiring, public catch-rate claims, and other residuals in 0103 remain outside this lane.
Independent review, protected-change approval, and merge remain outstanding.

## Owner rulings needed

None.
