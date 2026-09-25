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

## Review round B1 fixes

2026-09-24. Producer build evidence for the continuation of round 1 at `31e48da`.
Ruling 0134 and the Continuation B instructions are the lane's under the owner's
standing delegation of 23 September 2026; no sentence in those rulings is the owner's.
This section records implementation and verification, not a decision, change report or approval.
Glitch remains responsible for decision records and the change report.

Ruling 0134 now satisfies a bound number anywhere inside a parsed identifier and
continues chaining from that identifier's end. F2 uses the ASCII `[0-9A-Za-z]`
class in both walks. The marker pattern and the no-identifier path are unchanged.
The added cases extend existing methods, so the suite count remains 536.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| Ruling 0134: suffix number bound inside a parsed DOI | `gars/_system/resolve_citation.py`, `gars/tests/test_emit_report.py`, `benchmarks/defects/red_on_fault.py` | `EmitReportTests.test_doi_clean_reference_corpus` | Red first at round 1, then green; red-on-fault seen: yes, `bound number inside a parsed identifier counted` restores the start-only condition. The clean case emits with its exact request list; its trailing ` 10/fake` twin refuses and preserves absent/existing output. |
| F2: ASCII alphanumeric class in both walks | Same three files | `EmitReportTests.test_doi_fabricated_beside_verified` | Red first at round 1, then green; red-on-fault seen: yes, new `separator walks use Unicode alphanumerics` restores Unicode behavior in both walks. `chr(233)` covers the separator walk in both reference orders and the chaining walk. All 392 generated forms and existing assertions remain. |
| F3: inherited residual-prose comment | `gars/tests/test_emit_report.py` | Full gate's `EmitReportTests.test_doi_reference_forms`; byte comparison of inherited comments | Green; red-on-fault seen: no for this comment-only addition. Added one line naming the lane's 0130 and 0131 decisions immediately after the unchanged inherited comments. |
| F1, F4, F5: no code or historical-log change requested | This appended build-log section only | Review disposition and append-only byte comparison | Addressed below; red-on-fault seen: no, no behavior change. |

F1: No change; a bare date immediately after a URL-form DOI remains a known false refusal under the specified chaining rule.
F4: No change; 536 is the collection count, not a new macOS measurement, as round 1 already disclosed.
F5: No change; the build log is append-only, and the earlier scratch-folder wording remains preserved.

### Red-first and green evidence

`python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_clean_reference_corpus`
ran with the new ruling 0134 case while production was byte-identical to round 1's
`31e48da`, and then after the span-containment fix:
```text
Ran 1 test in 24.459s
FAILED (failures=1)
Ran 1 test in 24.122s
OK
```
`python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_fabricated_beside_verified`
ran in a disposable scratch twin with the new F2 cases and the resolver taken by
`git show 31e48da:gars/_system/resolve_citation.py`, then in the source tree after the ASCII fix:
```text
Ran 1 test in 0.697s
FAILED (failures=3)
Ran 1 test in 0.614s
OK
```
The subsequent full gate below covers both changes together.
All commands ran from the repository root with `TMPDIR`, `TEMP` and `TMP` set to
the job's scratch folder. Red-first logs and complete gate logs are retained there
under `b1/`. The synthetic 200-ok transport and recorded replay establish protocol
behavior only; no live DOI lookup was made.

The first full gate found only a documentation-citation error in the added F3
comment: the checker treated 0130 as a dangling repository citation.
Its summary was:
```text
Ran 536 tests in 408.501s
FAILED (failures=1, skipped=79)
```
The supplied lane decisions are not repository decision files in this checkout.
The new comment now explicitly names the lane's 0130 and 0131 decisions; inherited
comments, the citation checker and its tests remain unchanged. The targeted command
`python3 -u tests/test_decision_links_resolve.py DecisionLinksTests.test_repository_citations_resolve`
then printed:
```text
citations: 301/301 resolve
Ran 1 test in 0.110s
OK
```

### GATE

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`
(one suite at a time; database classes skipped, verified elsewhere).
```text
collected 283 tests from tests
collected 253 tests from gars/tests
Ran 536 tests in 386.887s
OK (skipped=79)
```
`python3 tests/check_contracts.py`
```text
14 contracts clean: sections, wait points, vocabulary.
```
`python3 tests/check_counts.py`
```text
suite: 536 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```
`python3 -u tests/test_planted_defects.py DevelopmentCatalogueTests`
```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
Ran 13 tests in 4.368s
OK
```
`TMPDIR=<the job's scratch folder> python3 -u benchmarks/defects/red_on_fault.py`
```text
red-on-fault: 53/53
```

The first campaign ended `red-on-fault: 52/53`: the inherited
`markers inside a parsed identifier counted` fault survived. Under ruling 0134,
its old examples could now satisfy the numbers inside their spans even when the
marker-skip was removed. The clean corpus now also includes the bare synthetic
identifier containing that marker followed by `; 10/fake`. The internal marker
must be ignored, leaving the outside number unbound; the mutant incorrectly
chains from the internal marker and refuses. This adds a behavioral witness,
without weakening an assertion or changing production to fit the fault.
The strengthened clean-corpus command then printed `Ran 1 test in 24.256s`
and `OK` before the complete campaign was rerun.
The intermediate full gate before adding this witness had already printed
`Ran 536 tests in 392.230s` and `OK (skipped=79)`; the final gate above was rerun
with the strengthened corpus.

The campaign total is **43 + 10 = 53**: eight faults from round 1 and two from B1.
The added F2 fault is `separator walks use Unicode alphanumerics`; it changes the
shared walk class to Unicode alphanumerics and turns the fabricated-beside-verified
guard red. The 0134 fault restores start-only satisfaction and turns the new clean
case red. Every inherited fault remains red, including the four required faults
on `EmitReportTests.test_doi_reference_forms`. Only anchors were adjusted for the
span lookup and ASCII chaining implementation; no production edit was made to fit
an anchor. Before making its twin, the campaign printed 28 DOI/EVIDENCE anchor
counts and required 1 for each. All were 1. The two added faults printed:
```text
anchor count: bound number inside a parsed identifier counted: 1
anchor count: separator walks use Unicode alphanumerics: 1
RED: bound number inside a parsed identifier counted
RED: separator walks use Unicode alphanumerics
red-on-fault: 53/53
```

Structural and compatibility checks:
```text
inherited mentions_doi, resolve and protected files: byte-identical; DOI regex and legacy predicate: unique
review unchanged; inherited residual comments preserved; build log append-only
Python 3.6 syntax: parsed 3 changed files
```
The review file remains untracked and unchanged (SHA-256
`92cc6894592ebf7a618a142730d813f7b087fce8cce577af10f2c14177a19248`).
The no-DOI residual-prose half, marker pattern, inherited `mentions_doi` body,
`resolve()`, evidence checker and emitter remain unchanged. No prior log bytes
were edited, and no decision or change-report record was written by the producer.

### Residual gaps still open

No live network DOI resolution or capture, actual Python 3.6 execution, cluster
execution or database execution was verified here. Database classes were skipped
under the requested gate and are verified elsewhere. No spent sealed measurement
was run or promoted. The existing broader short-DOI, PMID/literature, relevance,
stage-03/pilot emission, public catch-rate and other 0103 residuals remain outside
this lane. F1's bare-date chaining refusal remains as specified. Independent
review of B1, protected-change approval and merge remain outside this producer run.

Ruling 0134 and F2/F3 are fixed; F1/F4/F5 are closed by the requested no-change responses; no findings wait on a ruling.

## Owner rulings needed

None.


## Review round C1 fixes

2026-09-25. Producer build evidence continuing `40941de` on the DOI false-refusal
branch. The C1 Unicode-walk ruling is Glitch's under the owner's standing delegation
of 23 September 2026; no ruling sentence is the owner's. This section records
implementation and verification only. Glitch writes decisions and the change report.

Both walks now use `UNICODE_ALNUM_PATTERN = r"[^\W_]"`: Unicode letters and digits
stop the separator walk after a marker's token and the chaining walk after a parsed
identifier. The marker regex and numeric leading boundaries remain ASCII and
byte-identical. The lane's ruling 0134 span-containment behavior is unchanged.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F1: Unicode words must stop both walks | `gars/_system/resolve_citation.py`, `gars/tests/test_emit_report.py`, `benchmarks/defects/red_on_fault.py` | `EmitReportTests.test_doi_clean_reference_corpus`, `EmitReportTests.test_doi_fabricated_beside_verified` | Seven clean cases red at `40941de`, then both tests green. Red-on-fault seen: yes, `separator walks use ASCII alphanumerics` restores the ASCII class and turns the clean corpus red. The 392-form refusal guard and chained-list assertions remain. |
| F2: campaign count | This appended build-log section | Complete mutation campaign | No behavior change for this note; red-on-fault seen: yes, 53/53 (43 + 10), including the replacement ASCII-walk fault. |
| F3: historical expectation-table line numbers | This appended build-log section | Append-only byte comparison | No historical edit; red-on-fault seen: no, documentation disposition only. Tests are named below without shifting line references. |

F2: No change; the campaign remains 43 + 10, with `separator walks use ASCII alphanumerics` replacing B1's Unicode fault alongside `bound number inside a parsed identifier counted`; Glitch's change report owns the count record.
F3: No change; the append-only historical table retains its original line numbers, and Glitch's change report can cite `EmitReportTests.test_doi_reference_forms` by name.

### Expectation changes

Each row below moves a B1 case from `test_doi_fabricated_beside_verified` to
`test_doi_clean_reference_corpus`. `REAL` denotes `generator.REAL_DOI`; `\u00e9`
is the character built with the inherited `chr(233)` expression in these tests.

| Reference | Old expectation | C1 expectation | Reason |
|---|---|---|---|
| `doi: \u00e910/abcfake; doi:REAL` | Refuse `citation_unverifiable` | Emit; exactly one recorded Crossref request for REAL | The Unicode letter stops the marker separator walk before the number. |
| `doi:REAL; doi: \u00e910/abcfake` | Refuse `citation_unverifiable` | Emit; exactly one recorded Crossref request for REAL | The Unicode letter stops the marker separator walk in the reverse reference order. |
| `doi:REAL; \u00e9 10/abcfake` | Refuse `citation_unverifiable` | Emit; exactly one recorded Crossref request for REAL | The Unicode letter stops chaining after the parsed DOI. |

### Red-first and green evidence

Before the production fix, the resolver was verified byte-identical to
`git show 40941de:gars/_system/resolve_citation.py`. The four references named in
B1 F1 (Chinese, Cyrillic, Japanese and Greek), written with Unicode escapes and
the recorded real DOI, and the three moved cases all failed through emission:

`python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_clean_reference_corpus`
```text
Ran 1 test in 24.287s
FAILED (failures=7)
```
All seven failed subtests are recorded in the job scratch folder's `c1/red-first.log`.
After the fix:

`python3 -u gars/tests/test_emit_report.py EmitReportTests.test_doi_clean_reference_corpus EmitReportTests.test_doi_fabricated_beside_verified`
```text
Ran 2 tests in 25.087s
OK
```
Every new clean reference requires emission and exactly one recorded Crossref
request for the real DOI. The existing internal-marker and ruling 0134 cases,
including the malformed trailing-number refusal, are retained.

### GATE

All commands ran from the repository root, one suite at a time, with `TMPDIR`,
`TEMP` and `TMP` set to the job's scratch folder. Complete logs are under `c1/`
there. Replay fixtures and recording transports establish protocol behavior only.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`
(one suite at a time; database classes skipped, verified elsewhere).
```text
collected 283 tests from tests
collected 253 tests from gars/tests
Ran 536 tests in 386.994s
OK (skipped=79)
```

`python3 tests/check_contracts.py`
```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`
```text
suite: 536 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 -u tests/test_planted_defects.py DevelopmentCatalogueTests`
```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
Ran 13 tests in 4.380s
OK
```

`TMPDIR=<the job's scratch folder> python3 -u benchmarks/defects/red_on_fault.py`
```text
red-on-fault: 53/53
```

The campaign remains **43 + 10 = 53**. Before creating its disposable twin, it
printed all 28 DOI/EVIDENCE anchor counts and required exactly 1 for each; all
were 1. The replacement fault changes the shared Unicode class to `[0-9A-Za-z]`
and runs `EmitReportTests.test_doi_clean_reference_corpus`. The inherited
separator-walk fault was re-anchored to the renamed constant, with no production
change made to fit an anchor. All four required legacy faults still turn
`EmitReportTests.test_doi_reference_forms` red.

```text
anchor count: separator walks use ASCII alphanumerics: 1
RED: bound number inside a parsed identifier counted
RED: separator walks use ASCII alphanumerics
red-on-fault: 53/53
```

Structural checks preserve the inherited `mentions_doi` lines, their order and
indentation, its single inserted early return, `resolve()`, the unique DOI regex
and the unique legacy predicate. The protected files are byte-identical to the
base. The no-identifier path, brace handling and residual-prose controls are
unchanged. Three changed Python files parse with Python 3.6 syntax. The B1
review remains untracked and unchanged, and the build log retains every earlier
byte. Only the resolver, emission tests, mutation driver and this build log change.

### Residual gaps still open

No live network DOI resolution or capture, actual Python 3.6 execution, cluster
execution or database execution was verified here. Database classes were skipped
under the requested gate and are verified elsewhere. No spent sealed measurement
was run or promoted. The known bare-date chaining refusal and broader short-DOI,
PMID/literature, relevance, stage-03/pilot emission and public catch-rate residuals
remain outside this lane. Independent C1 review, protected-change approval and
merge remain outside this producer run. Glitch's decisions and change report
remain Glitch's records; the producer has not written or approved them.

F1 is closed by the supplied C1 ruling and verified fix; F2 and F3 are closed by the requested no-change responses; no findings wait on a ruling.

## Owner rulings needed

None.
