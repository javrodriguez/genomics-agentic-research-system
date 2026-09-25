# Row 10 science review harness — round 1

**Partial implementation; construction and measurement are blocked.** Two
contradictions in the supplied lane contract are reproduced below. No requirement
has been weakened to hide them. This round does not claim the harness complete
or row 10's exit. No model has been run against any case.

The governing scope rulings in record 0135 are **Glitch's decisions under the
owner's standing delegation**, never the owner's words. The producer account is
record 0136. Records 0135 and all base decision records are unchanged; 0137–0139
are reserved and unwritten. No review file was supplied for round 1.

## Delivered and stopped work

| Item | Implemented | Not implemented or not verified |
|---|---|---|
| 2 | Private row 9 imports, same-object contracts, stub audit, both import orders in one interpreter | Two-launcher comparison awaits a science launcher |
| 3 | Exactly ten science classes, definitions, other admitted in findings | P01, P02, C01, C02 and their statistical rationales; no producer or sealed case authored |
| 4–6 | Concrete witness that required manifest bytes fail the required sweep | Bases, complete INTERFACE/layout map, gates and builder; no passing construction or sweep-zero claim |
| 7 | Schema document with only the permitted enum/envelope differences; full remaining-tree drift check | Operational validation adapter, blocked by code-only prompt pin |
| 8 | Resume-only choice recorded from 0135 R10-5a | Launcher, stub two-phase integration, phase-B audit/session/usage-limit acceptance |
| 9 | Imported field matcher, any-of wrapper, path pre-normalisation, repo-prefix rejection, shared alarms and ratios | Scorer, denominator/invalid/repeat/first-run/publication integration |
| 10 | Prompt from the prescribed scientific requirements and case layout | No case execution or prompt tuning |
| 11 | Existing release script rendered DoD; no evidence values promoted | Science run reader awaits an operational run-file producer |
| 12 | Independent contract module and seven mutation controls | Remaining builder, gate, adapter, launcher, scoring and masking integration requirements |
| 13 | Count claims updated from suite collection; short DEVELOPMENT paragraph | Mode A and macOS remeasurement unavailable |

The blocked construction includes its case publication and sealer handoff. A
partial handoff without fixed base trees and verified gate integration is not
represented as the standalone INTERFACE that a sealer may rely on. Empty sealed
slots are recorded in SEALS.md. No C03 or other reserved case is supplied.

The schema inherits row 9's title and prompt_path pin unchanged, as the exact
drift contract requires. Its phases use JSON Schema cardinality and prefixItems
for exactly A then B and A-only notes_sha256; row 9's limited validator does not
implement those array keywords. A future authorized adapter must enforce the
phase shape as well as its science validity rules. The present schema document
is not claimed to establish operational science-record acceptance.

No existing test, guard or red-on-fault entry changed. No existing expectation
was made wrong by this change, so there are no old/new expectation rows to report.
The README evidence row is unchanged. The DoD renderer produced unchanged bytes.

## Verification

Python is 3.13.5; evaluation checks use a runtime newer than 3.9. No network,
remote, push, pull request, merge or approval is performed. Scratch logs and
disposable copies use the scratch twin. For nested subprocesses, its environment
value must be resolved at runtime, keeping relative literals in commands:

```sh
row10_scratch="$(realpath ../gars-row-10-scratch)"
export TMPDIR="$row10_scratch" TEMP="$row10_scratch" TMP="$row10_scratch"
```

Mode C unsets TMPDIR while keeping TEMP and TMP set to that folder.
The first mode-B attempt used a relative TMPDIR. The existing lifecycle fault
runner changes its child process working directory, and its support module
assigns that relative value directly to tempfile.tempdir. Child temporary-folder
creation then raised FileNotFoundError instead of reaching the expected mutation
assertion. Its superseded full-suite summary was:

```text
Ran 694 tests in 482.341s
FAILED (failures=59, skipped=79)
```

No test was changed to repair this setup error. With runtime-resolved scratch,
`python3 gars/tests/test_lifecycle_faults.py` confirmed the correction:

```text
Ran 1 test in 18.207s
OK
```

Final full-suite results, with the scratch folder resolved at runtime:

| Command and mode | Verbatim summary |
|---|---|
| `python3 tests/run_tests.py`, B: TMPDIR, TEMP and TMP set | `Ran 694 tests in 565.300s`; `OK (skipped=79)` |
| `python3 tests/run_tests.py`, C: TMPDIR unset, TEMP and TMP set | `Ran 694 tests in 559.056s`; `OK (skipped=106)` |

The other required summaries are:

| Command | Verbatim summary |
|---|---|
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/check_counts.py` | `suite: 694 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 37.925s`; `OK` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` |
| `python3 scripts/release_check.py` | `DoD cells regenerated: 13/13` |
| `python3 tests/test_bio_faults_core.py` | `Ran 12 tests in 0.053s`; `OK`; `wall time: 0.101 s; exit 0` |
| `python3 tests/test_bio_faults_faults.py` | `Ran 1 test in 0.719s`; `OK`; `wall time: 0.748 s; exit 0` |
| Python grammar check | `Python feature_version=(3, 6): 4/4 new Python files parse` |

Both new modules are below 120 seconds individually in mode B. Seven science
mutation witnesses printed `science fault red:` after unchanged controls passed.
The initial count check correctly refused the old 681 claims; the documents
were updated to the loader's 694 without changing the checker.

The generated reviewer row reads exactly:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The repository pre-commit hook was invoked on the staged additions:

```text
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 363/363 resolve
pre-commit: REFUSED
hook exit: 1
```

The secret scan is NOT verified; no scanner was installed, substituted or bypassed.
The required manual hook check remains refused. Scope verification found no
out-of-lane tracked changes and confirmed every base decision record's bytes.

The builder invocation was attempted with repository defaults and an output in
scratch; Python exited 2 because bio_build_cases.py is not implemented. Case
count, per-case gates and sweep hits are **not measured**, not zero. There are
no new fixtures over which to claim a fixture secret scan. The repository hook
was separately attempted on the staged additions; its result is recorded above.

Mode A needs Docker, which this account cannot reach. Native Python 3.6,
macOS cold-clone execution, cluster execution, deployment sandbox efficacy,
independent scientific audit, protected approval and merge-result CI remain
unverified. Science measurement, sealed slots and repeat remain later work.

## Owner rulings needed

1. **Code-only prompt path in the inherited schema (item 7).**
   `evals/review-faults/schema/review_record.schema.json` pins
   `envelope.reviewer.prompt_path` to
   `gars/_references/prompts/review_faults_code.md`. The specified science
   path is rejected by row 9's validate, and item 7 permits no change to this
   enum. Even rewriting only the adapter's view to the code path would fail
   row 9's prompt-path comparison against the required science manifest.
   `ContractTests.test_prompt_schema_conflict_witness` reproduces this.
   Options: (a) authorize the additional science schema enum change and an
   explicit prompt-path adapter rule that verifies science path/hash before
   projecting both record and manifest to the code path; (b) change row 9's
   code-only schema pin in a separate authorized lane, then inherit that
   revised contract without restating its validity rules. Record validity,
   launch, scoring and their release integration are stopped pending this
   choice, as item 7 explicitly directs.

2. **Required manifest bytes fail the literal sweep (item 6).**
   The required key `harness_commit` contains `harness`; the required science
   prompt path contains `fault`. Both are case-sensitive substrings forbidden
   in every public manifest byte. These are added manifest bytes, not unchanged
   base lines; no row 9 item-15 exemption resolves it.
   `ContractTests.test_manifest_sweep_conflict_witness` reproduces both hits.
   Options: (a) authorize narrowly named exemptions for these fixed,
   case-independent manifest key/value bytes, with every case-derived byte
   still swept; (b) revise the manifest field/path contract so the public
   manifest can avoid those tokens. Construction and the dependent case/base
   handoff are stopped; no exemption, encoding trick or weakened sweep is used.
